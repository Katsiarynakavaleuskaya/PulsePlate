"""Acquire and release the process-wide food-search strategy adapter."""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from enum import Enum
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


@dataclass(frozen=True, slots=True, eq=False)
class FoodSearchLifecycleLease:
    """Opaque capability proving ownership of the process-wide search adapter."""

    def __repr__(self) -> str:
        return "<FoodSearchLifecycleLease>"


class _FoodSearchLifecyclePhase(Enum):
    RESERVED = "reserved"
    ACTIVE = "active"
    RELEASING = "releasing"


@dataclass(slots=True)
class _ActiveFoodSearchLifecycle:
    lease: FoodSearchLifecycleLease
    app: FastAPI
    phase: _FoodSearchLifecyclePhase
    strategy: str | None = None
    previous_adapter: food_store.FoodSearchBackend | None = None
    installed_adapter: food_store.FoodSearchBackend | None = None
    client: httpx.Client | None = None
    shutdown_event: threading.Event | None = None


_FOOD_SEARCH_LIFECYCLE_LOCK = threading.Lock()
_ACTIVE_FOOD_SEARCH_LIFECYCLE: _ActiveFoodSearchLifecycle | None = None


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


def _build_meili_http_client() -> httpx.Client:
    """Create a pooled :class:`httpx.Client` for Meilisearch (bootstrap-owned)."""

    return httpx.Client(
        limits=httpx.Limits(
            max_connections=MEILI_HTTP_MAX_CONNECTIONS,
            max_keepalive_connections=MEILI_HTTP_MAX_KEEPALIVE_CONNECTIONS,
        ),
        timeout=httpx.Timeout(MEILI_HTTP_CLIENT_DEFAULT_TIMEOUT_SECONDS),
    )


def _clear_owned_app_state(app: FastAPI, lease: FoodSearchLifecycleLease) -> None:
    if getattr(app.state, "_food_search_lifecycle_lease", None) is not lease:
        return
    for attribute in (
        "meili_http_client",
        "meili_http_shutdown_event",
        "food_search_strategy",
        "_food_search_lifecycle_lease",
    ):
        if hasattr(app.state, attribute):
            delattr(app.state, attribute)


def _release_reservation(
    active: _ActiveFoodSearchLifecycle,
) -> None:
    global _ACTIVE_FOOD_SEARCH_LIFECYCLE
    with _FOOD_SEARCH_LIFECYCLE_LOCK:
        if _ACTIVE_FOOD_SEARCH_LIFECYCLE is active:
            _ACTIVE_FOOD_SEARCH_LIFECYCLE = None


def configure_food_search_backend(app: FastAPI) -> FoodSearchLifecycleLease:
    """Acquire the process-wide search strategy for one application lifespan."""

    global _ACTIVE_FOOD_SEARCH_LIFECYCLE
    lease = FoodSearchLifecycleLease()
    active = _ActiveFoodSearchLifecycle(
        lease=lease,
        app=app,
        phase=_FoodSearchLifecyclePhase.RESERVED,
    )
    with _FOOD_SEARCH_LIFECYCLE_LOCK:
        if _ACTIVE_FOOD_SEARCH_LIFECYCLE is not None:
            raise RuntimeError("Food search lifecycle is already active.")
        if getattr(app.state, "_food_search_lifecycle_lease", None) is not None:
            raise RuntimeError("Application already owns food search resources.")
        _ACTIVE_FOOD_SEARCH_LIFECYCLE = active

    strategy = food_store.get_search_backend_strategy()
    meili_url = (os.getenv("MEILI_URL") or "").strip()
    if strategy != "baseline_fts" and not meili_url:
        strategy = "baseline_fts"

    previous_adapter = food_store.get_registered_strategy_search_backend_adapter()
    shutdown_event: threading.Event | None = None
    pooled_client: httpx.Client | None = None
    adapter: food_store.FoodSearchBackend | None = None
    adapter_committed = False
    try:
        if strategy != "baseline_fts":
            shutdown_event = threading.Event()
            pooled_client = _build_meili_http_client()
            transport = make_pooled_httpx_transport(
                pooled_client,
                shutdown_event=shutdown_event,
            )
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

        if not food_store.compare_and_swap_strategy_search_backend_adapter(
            previous_adapter,
            adapter,
        ):
            raise RuntimeError("Food search adapter ownership changed during startup.")
        adapter_committed = True

        app.state._food_search_lifecycle_lease = lease
        app.state.food_search_strategy = strategy
        if shutdown_event is not None:
            app.state.meili_http_shutdown_event = shutdown_event
        if pooled_client is not None:
            app.state.meili_http_client = pooled_client

        with _FOOD_SEARCH_LIFECYCLE_LOCK:
            if _ACTIVE_FOOD_SEARCH_LIFECYCLE is not active:
                raise RuntimeError("Food search lifecycle reservation was lost.")
            active.strategy = strategy
            active.previous_adapter = previous_adapter
            active.installed_adapter = adapter
            active.client = pooled_client
            active.shutdown_event = shutdown_event
            active.phase = _FoodSearchLifecyclePhase.ACTIVE
        return lease
    except BaseException:
        if shutdown_event is not None:
            try:
                shutdown_event.set()
            except Exception:
                logger.warning("Meili rollback shutdown signal failed", exc_info=True)
        if adapter_committed:
            try:
                food_store.compare_and_swap_strategy_search_backend_adapter(
                    adapter,
                    previous_adapter,
                )
            except Exception:
                logger.warning("Food search rollback adapter reset failed", exc_info=True)
        try:
            _clear_owned_app_state(app, lease)
        except Exception:
            logger.warning("Food search rollback app-state cleanup failed", exc_info=True)
        if pooled_client is not None:
            try:
                pooled_client.close()
            except Exception:
                logger.warning("Meili HTTP client rollback close failed", exc_info=True)
        _release_reservation(active)
        raise


def dispose_food_search_backend(
    app: FastAPI,
    lease: FoodSearchLifecycleLease,
) -> None:
    """Release resources only when ``lease`` owns the process-wide adapter."""

    global _ACTIVE_FOOD_SEARCH_LIFECYCLE
    with _FOOD_SEARCH_LIFECYCLE_LOCK:
        active = _ACTIVE_FOOD_SEARCH_LIFECYCLE
        if active is None:
            return
        if active.lease is not lease or active.app is not app:
            raise RuntimeError("Food search lifecycle is owned by another application.")
        if active.phase is _FoodSearchLifecyclePhase.RELEASING:
            return
        active.phase = _FoodSearchLifecyclePhase.RELEASING
        shutdown_event = active.shutdown_event
        client = active.client
        installed_adapter = active.installed_adapter
        previous_adapter = active.previous_adapter

    try:
        if shutdown_event is not None:
            try:
                shutdown_event.set()
            except Exception:
                logger.warning("Meili shutdown signal failed", exc_info=True)
        try:
            adapter_restored = food_store.compare_and_swap_strategy_search_backend_adapter(
                installed_adapter,
                previous_adapter,
            )
        except Exception:
            logger.warning("Food search adapter reset failed", exc_info=True)
        else:
            if not adapter_restored:
                logger.warning("Food search adapter ownership changed before shutdown")
        if client is not None:
            try:
                client.close()
            except Exception:
                logger.warning("Meili HTTP client close failed", exc_info=True)
        try:
            _clear_owned_app_state(app, lease)
        except Exception:
            logger.warning("Food search app-state cleanup failed", exc_info=True)
    finally:
        with _FOOD_SEARCH_LIFECYCLE_LOCK:
            if _ACTIVE_FOOD_SEARCH_LIFECYCLE is active:
                _ACTIVE_FOOD_SEARCH_LIFECYCLE = None
