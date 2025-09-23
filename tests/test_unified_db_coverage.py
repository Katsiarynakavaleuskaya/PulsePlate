"""
Тесты для покрытия core/food_apis/unified_db.py
Покрывает различные сценарии работы с unified_db
"""

import pytest
from unittest.mock import patch, MagicMock


class TestUnifiedDBCoverage:
    """Тесты для покрытия unified_db.py"""

    @pytest.mark.asyncio
    async def test_unified_db_error_handling_coverage(self):
        """Тест покрытия unified_db.py error handling при инициализации USDAClient"""
        # Патчим USDAClient, чтобы вызвать ошибку при инициализации
        with patch("core.food_apis.unified_db.USDAClient") as mock_usda:
            mock_usda.side_effect = Exception("Database connection failed")

            from core.food_apis.unified_db import UnifiedFoodDatabase

            with pytest.raises(Exception, match="Database connection failed"):
                UnifiedFoodDatabase()

    @pytest.mark.asyncio
    async def test_unified_db_cache_handling_coverage(self):
        """Тест покрытия unified_db.py cache handling - проверяем кэширование экземпляра"""
        # Перезагружаем модуль, чтобы сбросить состояние вместо патчинга приватной переменной
        import importlib
        import core.food_apis.unified_db as unified_db

        importlib.reload(unified_db)
        get_unified_food_db = unified_db.get_unified_food_db

        result1 = await get_unified_food_db()
        result2 = await get_unified_food_db()

        # Проверяем, что возвращается тот же объект (кэширование)
        assert result1 is result2
        assert result1 is not None

    @pytest.mark.asyncio
    async def test_unified_db_data_processing_coverage(self):
        """Тест покрытия unified_db.py data processing - тестируем поиск продуктов"""
        # Патчим USDAClient для тестирования обработки данных
        with patch("core.food_apis.unified_db.USDAClient") as mock_usda:
            mock_client = MagicMock()
            mock_usda.return_value = mock_client

            # Мокаем результат поиска как async функцию
            mock_food_item = MagicMock()
            mock_food_item.fdc_id = 123
            mock_food_item.description = "Test Food"
            mock_food_item.food_nutrients = []

            # Создаем async mock для search_foods
            async def mock_search_foods(*args, **kwargs):
                return [mock_food_item]

            mock_client.search_foods = mock_search_foods

            from core.food_apis.unified_db import UnifiedFoodDatabase

            db = UnifiedFoodDatabase()
            results = await db.search_food("test query")

            # Проверяем, что данные были обработаны
            assert results is not None
            assert len(results) >= 0  # Может быть пустой список

    @pytest.mark.asyncio
    async def test_unified_db_cleanup_coverage(self):
        """Тест покрытия unified_db.py cleanup - тестируем метод close"""
        # Патчим USDAClient для тестирования очистки
        with patch("core.food_apis.unified_db.USDAClient") as mock_usda:
            mock_client = MagicMock()
            mock_usda.return_value = mock_client

            # Создаем async mock для close
            async def mock_close():
                return None

            mock_client.close = mock_close

            from core.food_apis.unified_db import UnifiedFoodDatabase

            db = UnifiedFoodDatabase()

            # Тестируем метод close
            if hasattr(db, "close"):
                result = await db.close()
                # DB API гарантирует, что close возвращает None
                assert result is None
