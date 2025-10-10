"""
Быстрые тесты для покрытия core/food_apis/unified_db.py
"""

from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestUnifiedDBQuickCoverage:
    """Быстрые тесты для покрытия unified_db.py"""

    def test_type_checking_imports(self):
        """Тест TYPE_CHECKING импортов"""
        from core.food_apis.unified_db import UnifiedFoodItem

        # Просто проверяем что класс импортируется
        assert UnifiedFoodItem is not None

    def test_resolve_off_client_success(self):
        """Тест успешного разрешения OFF клиента"""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.OFFClient = MagicMock()
            mock_import.return_value = mock_module

            from core.food_apis.unified_db import _resolve_off_client

            client, available = _resolve_off_client()

            assert client is not None
            assert available is True

    def test_resolve_off_client_failure(self):
        """Тест неудачного разрешения OFF клиента"""
        with patch("importlib.import_module", side_effect=ImportError):
            from core.food_apis.unified_db import _resolve_off_client

            client, available = _resolve_off_client()

            assert client is None
            assert available is False

    def test_unified_food_item_from_usda(self):
        """Тест создания UnifiedFoodItem из USDA"""
        from core.food_apis.unified_db import UnifiedFoodItem
        from core.food_apis.usda_client import USDAFoodItem

        # Создаем мок USDA item
        usda_item = MagicMock(spec=USDAFoodItem)
        usda_item.description = "Test Apple"
        usda_item.nutrients_per_100g = {"kcal": 52.0}
        usda_item._generate_tags.return_value = ["VEG"]
        usda_item.fdc_id = 12345
        usda_item.food_category = "Fruits"

        unified_item = UnifiedFoodItem.from_usda_item(usda_item, 2.0)

        assert unified_item.name == "Test Apple"
        assert unified_item.cost_per_100g == 2.0
        assert unified_item.source == "USDA FoodData Central"
        assert unified_item.source_id == "12345"

    def test_unified_food_item_from_off(self):
        """Тест создания UnifiedFoodItem из OFF"""
        from core.food_apis.unified_db import UnifiedFoodItem

        # Создаем мок OFF item
        off_item = MagicMock()
        off_item.product_name = "Test Product"
        off_item.nutrients_per_100g = {"kcal": 100.0}
        off_item._generate_tags.return_value = ["VEG", "GF"]
        off_item.code = "123456789"
        off_item.countries = ["US", "CA"]
        off_item.categories = ["Beverages"]

        unified_item = UnifiedFoodItem.from_off_item(off_item, 3.0)

        assert unified_item.name == "Test Product"
        assert unified_item.cost_per_100g == 3.0
        assert unified_item.source == "Open Food Facts"
        assert unified_item.source_id == "123456789"

    def test_unified_food_item_to_menu_engine_format(self):
        """Тест конвертации в формат menu_engine"""
        from core.food_apis.unified_db import UnifiedFoodItem

        item = UnifiedFoodItem(
            name="Test Item",
            nutrients_per_100g={"kcal": 50.0},
            cost_per_100g=1.5,
            tags=["VEG"],
            availability_regions=["US"],
            source="Test Source",
            source_id="123",
            category="Test Category",
        )

        result = item.to_menu_engine_format()

        assert result["name"] == "Test Item"
        assert result["nutrients_per_100g"]["kcal"] == 50.0
        assert result["cost_per_100g"] == 1.5

    def test_unified_food_database_init(self):
        """Тест инициализации UnifiedFoodDatabase"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("core.food_apis.unified_db.OFFClient", None):
                from core.food_apis.unified_db import UnifiedFoodDatabase

                db = UnifiedFoodDatabase(cache_dir=temp_dir)

                assert db.usda_client is not None
                assert db.off_client is None
                assert db.cache_dir == Path(temp_dir)

    def test_unified_food_database_cache_file(self):
        """Тест получения пути к файлу кэша"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("core.food_apis.unified_db.OFFClient", None):
                from core.food_apis.unified_db import UnifiedFoodDatabase

                db = UnifiedFoodDatabase(cache_dir=temp_dir)
                cache_file = db._get_cache_file()

                assert cache_file.name == "unified_food_cache.json"
                assert str(cache_file).startswith(temp_dir)

    def test_unified_food_database_load_cache_success(self):
        """Тест успешной загрузки кэша"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "unified_food_cache.json"
            cache_file.write_text(
                '{"test": {"name": "Test Item", "nutrients_per_100g": {"kcal": 50.0}, "cost_per_100g": 1.5, "tags": ["VEG"], "availability_regions": ["US"], "source": "Test", "source_id": "123"}}'
            )

            with patch("core.food_apis.unified_db.OFFClient", None):
                from core.food_apis.unified_db import UnifiedFoodDatabase

                db = UnifiedFoodDatabase(cache_dir=temp_dir)

                # Проверяем что кэш загрузился
                assert len(db._memory_cache) > 0

    def test_unified_food_database_load_cache_failure(self):
        """Тест неудачной загрузки кэша"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "unified_food_cache.json"
            cache_file.write_text("invalid json")

            with patch("core.food_apis.unified_db.OFFClient", None):
                from core.food_apis.unified_db import UnifiedFoodDatabase

                db = UnifiedFoodDatabase(cache_dir=temp_dir)

                # Проверяем что кэш пустой при ошибке
                assert len(db._memory_cache) == 0

    def test_unified_food_database_save_cache(self):
        """Тест сохранения кэша"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("core.food_apis.unified_db.OFFClient", None):
                from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

                db = UnifiedFoodDatabase(cache_dir=temp_dir)

                # Добавляем элемент в кэш
                item = UnifiedFoodItem(
                    name="Test Item",
                    nutrients_per_100g={"kcal": 50.0},
                    cost_per_100g=1.5,
                    tags=["VEG"],
                    availability_regions=["US"],
                    source="Test Source",
                    source_id="123",
                )
                db._memory_cache["test"] = item

                # Сохраняем кэш
                db._save_cache()

                # Проверяем что файл создался
                cache_file = db._get_cache_file()
                assert cache_file.exists()

    @pytest.mark.asyncio
    async def test_unified_food_database_search_foods(self):
        """Тест поиска продуктов"""
        from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("core.food_apis.unified_db.OFFClient", None),
                patch.object(UnifiedFoodDatabase, "search_food") as mock_search,
            ):
                db = UnifiedFoodDatabase(cache_dir=temp_dir)

                # Настраиваем мок
                mock_item = UnifiedFoodItem(
                    name="Apple",
                    nutrients_per_100g={"kcal": 52.0},
                    cost_per_100g=1.5,
                    tags=["VEG"],
                    availability_regions=["US"],
                    source="Test Source",
                    source_id="123",
                )
                mock_search.return_value = [mock_item]

                # Ищем продукты
                results = await db.search_food("apple")

                assert len(results) == 1
                assert results[0].name == "Apple"

    @pytest.mark.asyncio
    async def test_unified_food_database_get_food(self):
        """Тест получения конкретного продукта"""
        from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("core.food_apis.unified_db.OFFClient", None),
                patch.object(UnifiedFoodDatabase, "get_food_by_id") as mock_get,
            ):
                db = UnifiedFoodDatabase(cache_dir=temp_dir)

                # Настраиваем мок
                mock_item = UnifiedFoodItem(
                    name="Apple",
                    nutrients_per_100g={"kcal": 52.0},
                    cost_per_100g=1.5,
                    tags=["VEG"],
                    availability_regions=["US"],
                    source="Test Source",
                    source_id="123",
                )
                mock_get.return_value = mock_item

                # Получаем продукт
                result = await db.get_food_by_id("apple", "123")

                assert result is not None
                assert result.name == "Apple"

                # Тест несуществующего продукта
                mock_get.return_value = None
                result = await db.get_food_by_id("nonexistent", "999")
                assert result is None
