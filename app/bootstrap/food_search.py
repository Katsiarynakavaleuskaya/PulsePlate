"""Bootstrap optional search strategy adapters."""

from __future__ import annotations

import os
from typing import cast

from fastapi import FastAPI

from app.services import food_store
from app.services.search_meili import MeiliSearchBackend, ShadowSearchBackend

DEFAULT_MEILI_TIMEOUT_SECONDS = 2.0
DEFAULT_MEILI_INDEX_NAME = "foods"


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


def register_food_search_backend(app: FastAPI) -> None:
    """Register optional search backend strategy without changing API routes."""

    strategy = food_store.get_search_backend_strategy()
    if strategy == "baseline_fts":
        food_store.reset_strategy_search_backend_adapter()
        app.state.food_search_strategy = strategy
        return

    meili_url = (os.getenv("MEILI_URL") or "").strip()
    if not meili_url:
        food_store.reset_strategy_search_backend_adapter()
        app.state.food_search_strategy = "baseline_fts"
        return

    meili_backend = MeiliSearchBackend(
        base_url=meili_url,
        index_name=_safe_index_name(os.getenv("MEILI_FOODS_INDEX")),
        api_key=(os.getenv("MEILI_KEY") or "").strip() or None,
        timeout_seconds=_safe_timeout_seconds(os.getenv("MEILI_TIMEOUT_SECONDS")),
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
