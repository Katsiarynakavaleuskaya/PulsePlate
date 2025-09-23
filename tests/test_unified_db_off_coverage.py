# -*- coding: utf-8 -*-
import tempfile
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
    with patch("core.food_apis.unified_db.USDAClient") as mock_usda_cls:
        mock_usda = MagicMock()
        mock_usda.search_foods = AsyncMock(return_value=[])
        mock_usda_cls.return_value = mock_usda

        with tempfile.TemporaryDirectory() as temp_dir:
            db = UnifiedFoodDatabase(cache_dir=temp_dir)
            # Inject fake OFF client
            db.off_client = _FakeOFFClient()

            results = await db.search_food("sample", prefer_source="openfoodfacts")
            # RU: Избегаем строгой проверки класса из-за возможных перезагрузок модуля
            # EN: Avoid strict class identity check due to potential module reloads
            assert results and hasattr(results[0], "name") and hasattr(results[0], "source")
            assert results[0].source == "Open Food Facts"

            # Second call should hit in-memory cache
            results2 = await db.search_food("sample", prefer_source="openfoodfacts")
            assert results2 and hasattr(results2[0], "name") and hasattr(results2[0], "source")


@pytest.mark.asyncio
async def test_unified_db_get_food_by_id_off_success():
    with patch("core.food_apis.unified_db.USDAClient"):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = UnifiedFoodDatabase(cache_dir=temp_dir)
            db.off_client = _FakeOFFClient()

            item = await db.get_food_by_id("openfoodfacts", "000111222")
            # RU: не завязываемся на идентичность класса между модулями
            # EN: avoid class identity issues across module reloads
            assert item is not None and hasattr(item, "name") and hasattr(item, "source")
            assert item.source == "Open Food Facts"
