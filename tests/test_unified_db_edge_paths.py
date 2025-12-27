"""
Targeted edge-case tests for core.food_apis.unified_db to boost coverage.

Covers:
- OFF module import failure branch at module import time
- Memory cache fast paths for search and get by id
- Invalid USDA ID (ValueError path)
"""

import tempfile
from unittest.mock import AsyncMock

import pytest


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
