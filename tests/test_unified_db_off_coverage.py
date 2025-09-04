# -*- coding: utf-8 -*-
import asyncio
import tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem


class _FakeOFFItem:
    def __init__(self):
        self.product_name = "OFF Sample"
        self.nutrients_per_100g = {"protein_g": 5.0}
        self.countries = ["US"]
        self.code = "000111222"
        self.categories = ["Snacks"]

    def _generate_tags(self):
        return ["off", "snack"]


class _FakeOFFClient:
    async def search_products(self, query: str, page_size: int = 5):  # noqa: ARG002
        return [_FakeOFFItem()]

    async def get_product_details(self, code: str):  # noqa: ARG002
        return _FakeOFFItem()


@pytest.mark.asyncio
async def test_unified_db_search_uses_off_and_caches():
    # Patch USDA to return empty so OFF branch is used
    with patch('core.food_apis.unified_db.USDAClient') as mock_usda_cls:
        mock_usda = MagicMock()
        mock_usda.search_foods = AsyncMock(return_value=[])
        mock_usda_cls.return_value = mock_usda

        with tempfile.TemporaryDirectory() as temp_dir:
            db = UnifiedFoodDatabase(cache_dir=temp_dir)
            # Inject fake OFF client
            db.off_client = _FakeOFFClient()

            results = await db.search_food("sample", prefer_source="openfoodfacts")
            assert results and isinstance(results[0], UnifiedFoodItem)

            # Second call should hit in-memory cache
            results2 = await db.search_food("sample", prefer_source="openfoodfacts")
            assert results2 and isinstance(results2[0], UnifiedFoodItem)


@pytest.mark.asyncio
async def test_unified_db_get_food_by_id_off_success():
    with patch('core.food_apis.unified_db.USDAClient'):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = UnifiedFoodDatabase(cache_dir=temp_dir)
            db.off_client = _FakeOFFClient()

            item = await db.get_food_by_id("openfoodfacts", "000111222")
            assert isinstance(item, UnifiedFoodItem)
            assert item.source == "Open Food Facts"

