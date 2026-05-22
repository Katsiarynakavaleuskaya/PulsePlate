"""Bootstrap optional search strategy adapters."""

from __future__ import annotations

import contextlib
import logging
import os
import threading
from collections.abc import AsyncIterator
from typing import cast

import httpx
from fastapi import FastAPI

from app.services import food_store
from app.services.search_meili import (
    MeiliSearchBackend,
    ShadowSearchBackend,
    make_pooled_httpx_transport,
)
from app.utils.feature_flags import _is_truthy

logger = logging.getLogger(__name__)

DEFAULT_MEILI_TIMEOUT_SECONDS = 2.0
DEFAULT_MEILI_INDEX_NAME = "foods"
MEILI_SHOW_PERFORMANCE_DETAILS_ENV = "MEILI_SHOW_PERFORMANCE_DETAILS"
MEILI_HTTP_MAX_CONNECTIONS = 32
MEILI_HTTP_MAX_KEEPALIVE_CONNECTIONS = 16
# httpx default timeout for the pooled client (all phases); per-search timeout still
# comes from ``client.post(..., timeout=timeout_seconds)`` in the transport.
MEILI_HTTP_CLIENT_DEFAULT_TIMEOUT_SECONDS = 5.0


def _safe_timeout_seconds(raw_value: str | None) -> float:
    """Return validated Meili timeout with deterministic fallback."""

    try:
        parsed = float(raw_value or DEFAULT_MEILI_TIMEOUT_SECONDS)
    except (TypeError, ValueError):
        return DEFAULT_MEILI_TIMEOUT_SECONDS
    if parsed <= 0:
        return DEFAULT_MEILI_TIMEOUT_SECONDS
    return parsed


def _safe_index_name(raw_value: str | None) -> str:
    """Return validated Meili index name with deterministic fallback."""

    normalized = (raw_value or "").strip()
    return normalized or DEFAULT_MEILI_INDEX_NAME


def _safe_show_performance_details(raw_value: str | None) -> bool:
    """Return validated Meili performance-details flag with safe default."""

    enabled = _is_truthy(raw_value)
    return bool(enabled)


def _dispose_meili_http_client(app: FastAPI) -> None:
    """Close pooled Meili HTTP client if present."""

    shutdown_event = getattr(app.state, "meili_http_shutdown_event", None)
    if shutdown_event is not None:
        shutdown_event.set()
    client = getattr(app.state, "meili_http_client", None)
    if client is not None:
        try:
            client.close()
        except Exception:
            logger.warning("Meili HTTP client close failed", exc_info=True)
        finally:
            if getattr(app.state, "meili_http_client", None) is client:
                del app.state.meili_http_client
    if (
        shutdown_event is not None
        and getattr(app.state, "meili_http_shutdown_event", None) is shutdown_event
    ):
        del app.state.meili_http_shutdown_event


def dispose_food_search_meili_http_client(app: FastAPI) -> None:
    """Public dispose hook for tests and manual teardown (mirrors shutdown behavior)."""

    _dispose_meili_http_client(app)


def _build_meili_http_client() -> httpx.Client:
    """Create a pooled :class:`httpx.Client` for Meilisearch (bootstrap-owned)."""

    return httpx.Client(
        limits=httpx.Limits(
            max_connections=MEILI_HTTP_MAX_CONNECTIONS,
            max_keepalive_connections=MEILI_HTTP_MAX_KEEPALIVE_CONNECTIONS,
        ),
        timeout=httpx.Timeout(MEILI_HTTP_CLIENT_DEFAULT_TIMEOUT_SECONDS),
    )


def _ensure_meili_http_shutdown_handler(app: FastAPI) -> None:
    """Register a single lifespan shutdown hook to close the pooled Meili client."""

    if getattr(app.state, "_meili_http_shutdown_registered", False):
        return

    original_lifespan = app.router.lifespan_context

    @contextlib.asynccontextmanager
    async def _wrapped_lifespan(app: FastAPI) -> AsyncIterator[None]:
        if original_lifespan is not None:
            async with original_lifespan(app):
                yield
        else:
            yield
        _dispose_meili_http_client(app)

    app.router.lifespan_context = _wrapped_lifespan
    app.state._meili_http_shutdown_registered = True


def register_food_search_backend(app: FastAPI) -> None:
    """Register optional search backend strategy without changing API routes."""

    strategy = food_store.get_search_backend_strategy()
    if strategy == "baseline_fts":
        _dispose_meili_http_client(app)
        food_store.reset_strategy_search_backend_adapter()
        app.state.food_search_strategy = strategy
        return

    meili_url = (os.getenv("MEILI_URL") or "").strip()
    if not meili_url:
        _dispose_meili_http_client(app)
        food_store.reset_strategy_search_backend_adapter()
        app.state.food_search_strategy = "baseline_fts"
        return

    _dispose_meili_http_client(app)
    app.state.meili_http_shutdown_event = threading.Event()
    pooled_client = _build_meili_http_client()
    app.state.meili_http_client = pooled_client
    transport = make_pooled_httpx_transport(
        pooled_client,
        shutdown_event=app.state.meili_http_shutdown_event,
    )
    _ensure_meili_http_shutdown_handler(app)

    meili_backend = MeiliSearchBackend(
        base_url=meili_url,
        index_name=_safe_index_name(os.getenv("MEILI_FOODS_INDEX")),
        api_key=(os.getenv("MEILI_KEY") or "").strip() or None,
        timeout_seconds=_safe_timeout_seconds(os.getenv("MEILI_TIMEOUT_SECONDS")),
        show_performance_details=_safe_show_performance_details(
            os.getenv(MEILI_SHOW_PERFORMANCE_DETAILS_ENV)
        ),
        search_strategy_label=strategy,
        transport=transport,
        fallback_backend=food_store.get_legacy_search_backend(),
    )
    adapter: food_store.FoodSearchBackend
    if strategy == "meili":
        adapter = cast(food_store.FoodSearchBackend, meili_backend)
    else:
        adapter = cast(
            food_store.FoodSearchBackend,
            ShadowSearchBackend(
                baseline_backend=food_store.get_legacy_search_backend(),
                shadow_backend=meili_backend,
            ),
        )
    food_store.register_strategy_search_backend_adapter(adapter)
    app.state.food_search_strategy = strategy
