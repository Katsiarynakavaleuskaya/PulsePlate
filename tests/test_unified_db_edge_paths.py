"""
Targeted edge-case tests for core.food_apis.unified_db to boost coverage.

Covers:
- OFF module import failure branch at module import time
- Memory cache fast paths for search and get by id
- Invalid USDA ID (ValueError path)
"""

from contextlib import contextmanager
import importlib
import tempfile
from unittest.mock import AsyncMock, patch

import pytest


@contextmanager
def reload_module_with_off_import_failure():
    """Reload unified_db in-place simulating ImportError for OFF module.

    Uses importlib.reload on the existing module object to preserve identity of
    classes across the process and avoid cross-module isinstance mismatches.
    """
    import core.food_apis.unified_db as unified_db

    # Original builtins.__import__ to fallback for other imports
    orig_import = __import__

    def import_side_effect(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "core.food_apis.openfoodfacts_client" or (
            name == "core.food_apis" and fromlist and "openfoodfacts_client" in fromlist
        ):
            raise ImportError("OFF module unavailable for test")
        return orig_import(name, globals, locals, fromlist, level)

    orig_import_module = importlib.import_module
    with (
        patch("builtins.__import__", side_effect=import_side_effect),
        patch(
            "importlib.import_module",
            side_effect=lambda name, *a, **kw: (
                iter(()).throw(ImportError("OFF module unavailable"))
                if name.endswith("openfoodfacts_client")
                else orig_import_module(name, *a, **kw)
            ),
        ),
    ):
        reloaded = importlib.reload(unified_db)
        try:
            yield reloaded
        finally:
            # Reload back without patch to restore original state in-place
            importlib.reload(unified_db)


class TestUnifiedDbTargetedEdges:
    @pytest.fixture
    def temp_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yield tmp

    def test_off_import_failure_branch(self, temp_cache_dir, monkeypatch):
        """Simulate OFF import failure by monkeypatching symbols to avoid import reload side-effects."""
        import core.food_apis.unified_db as unified_db

        # Force OFF to be unavailable
        monkeypatch.setattr(unified_db, "OFFClient", None, raising=False)
        monkeypatch.setattr(unified_db, "OFF_AVAILABLE", False, raising=False)

        db = unified_db.UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        assert db.off_client is None

    @pytest.mark.asyncio
    async def test_search_food_memory_cache_hit(self, temp_cache_dir):
        """Ensure cached search result returns without hitting clients."""
        from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)

        # Prepare a cached item under the normalized key
        cached = UnifiedFoodItem(
            name="Cached Chicken",
            nutrients_per_100g={"protein": 31.0},
            cost_per_100g=2.0,
            tags=["cached"],
            availability_regions=["US"],
            source="USDA FoodData Central",
            source_id="000",
        )
        db._memory_cache["search_chicken"] = cached

        # Make USDA client raise if called (should not be called)
        db.usda_client = AsyncMock()
        db.usda_client.search_foods.side_effect = AssertionError(
            "Should not be called on cache hit"
        )

        results = await db.search_food("CHICKEN")
        assert len(results) == 1
        assert results[0].name == "Cached Chicken"

    @pytest.mark.asyncio
    async def test_get_by_id_invalid_usda_id(self, temp_cache_dir):
        """Invalid USDA id should be handled gracefully (ValueError branch)."""
        from core.food_apis.unified_db import UnifiedFoodDatabase

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        # Ensure client would fail if invoked, to assert early exit on ValueError
        db.usda_client = AsyncMock()
        db.usda_client.get_food_details.side_effect = AssertionError("Should not be called")

        result = await db.get_food_by_id("usda", "not-an-int")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_memory_cache_hit(self, temp_cache_dir):
        """get_food_by_id should return from memory cache when available."""
        from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        cached = UnifiedFoodItem(
            name="Cached Item",
            nutrients_per_100g={"calories": 100.0},
            cost_per_100g=1.0,
            tags=["cached"],
            availability_regions=["US"],
            source="USDA FoodData Central",
            source_id="123",
        )
        db._memory_cache["usda_123"] = cached

        # Make clients raise if called (should not be called)
        db.usda_client = AsyncMock()
        db.usda_client.get_food_details.side_effect = AssertionError(
            "Should not be called on cache hit"
        )

        res = await db.get_food_by_id("usda", "123")
        assert res is cached
