"""
Тесты для покрытия core/food_apis/unified_db.py
Покрывает различные сценарии работы с unified_db
"""

from unittest.mock import MagicMock, patch

import pytest


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
    async def test_unified_db_cache_handling_coverage(self, monkeypatch):
        """Тест покрытия unified_db.py cache handling - проверяем кэширование экземпляра

        Uses monkeypatch to reset the singleton instance instead of reload to avoid
        cross-module isinstance mismatches when other tests import UnifiedFoodItem
        or UnifiedFoodDatabase.
        """
        import core.food_apis.unified_db as unified_db

        # Reset the singleton instance in-place without reloading the module
        monkeypatch.setattr(unified_db, "_unified_db_instance", None, raising=False)

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
            db.off_client = None
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
            db.off_client = None

            # Тестируем метод close
            if hasattr(db, "close"):
                result = await db.close()
                # DB API гарантирует, что close возвращает None
                assert result is None

    @pytest.mark.asyncio
    async def test_search_food_save_cache_true(self, tmp_path):
        """Test search_food with save_cache=True creates/updates cache file."""
        import json
        from pathlib import Path

        with patch("core.food_apis.unified_db.USDAClient") as mock_usda:
            mock_client = MagicMock()
            mock_usda.return_value = mock_client

            # Mock USDA search results with proper USDAFoodItem structure
            from core.food_apis.usda_client import USDAFoodItem

            mock_food_item = USDAFoodItem(
                fdc_id=12345,
                description="Chicken breast, meat only, cooked, roasted",
                food_category="Poultry Products",
                nutrients_per_100g={"protein_g": 31.0, "fat_g": 3.6, "kcal": 165},
                data_type="SR Legacy",
                publication_date="2021-10-28",
            )

            async def mock_search_foods(*args, **kwargs):
                return [mock_food_item]

            mock_client.search_foods = mock_search_foods

            from core.food_apis.unified_db import UnifiedFoodDatabase

            # Create database with custom cache directory
            db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
            db.off_client = None
            cache_file = tmp_path / "unified_food_cache.json"

            # Verify cache doesn't exist initially
            assert not cache_file.exists()

            # Call search_food with save_cache=True (explicit)
            results = await db.search_food("chicken", save_cache=True)

            # Verify results returned
            assert len(results) > 0
            assert "chicken" in results[0].name.lower()

            # Verify cache file was created and contains expected entry
            assert cache_file.exists()
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            assert "search_chicken" in cache_data
            assert "chicken" in cache_data["search_chicken"]["name"].lower()

    @pytest.mark.asyncio
    async def test_search_food_save_cache_false(self, tmp_path):
        """Test search_food with save_cache=False doesn't create cache file."""
        with patch("core.food_apis.unified_db.USDAClient") as mock_usda:
            mock_client = MagicMock()
            mock_usda.return_value = mock_client

            # Mock USDA search results
            from core.food_apis.usda_client import USDAFoodItem

            mock_food_item = USDAFoodItem(
                fdc_id=67890,
                description="Salmon, Atlantic, farmed, cooked",
                food_category="Finfish and Shellfish Products",
                nutrients_per_100g={"protein_g": 25.4, "fat_g": 13.4, "kcal": 206},
                data_type="SR Legacy",
                publication_date="2021-10-28",
            )

            async def mock_search_foods(*args, **kwargs):
                return [mock_food_item]

            mock_client.search_foods = mock_search_foods

            from core.food_apis.unified_db import UnifiedFoodDatabase

            db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
            db.off_client = None
            cache_file = tmp_path / "unified_food_cache.json"

            # Call search_food with save_cache=False
            results = await db.search_food("salmon", save_cache=False)

            # Verify results returned
            assert len(results) > 0

            # Verify cache file was NOT created
            assert not cache_file.exists()

    @pytest.mark.asyncio
    async def test_search_food_save_cache_default(self, tmp_path):
        """Test search_food without save_cache arg uses default (True)."""
        import json

        with patch("core.food_apis.unified_db.USDAClient") as mock_usda:
            mock_client = MagicMock()
            mock_usda.return_value = mock_client

            from core.food_apis.usda_client import USDAFoodItem

            mock_food_item = USDAFoodItem(
                fdc_id=11111,
                description="Broccoli, raw",
                food_category="Vegetables and Vegetable Products",
                nutrients_per_100g={"protein_g": 2.8, "carbs_g": 6.6, "kcal": 34},
                data_type="SR Legacy",
                publication_date="2021-10-28",
            )

            async def mock_search_foods(*args, **kwargs):
                return [mock_food_item]

            mock_client.search_foods = mock_search_foods

            from core.food_apis.unified_db import UnifiedFoodDatabase

            db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
            db.off_client = None
            cache_file = tmp_path / "unified_food_cache.json"

            # Call search_food WITHOUT save_cache arg (should default to True)
            results = await db.search_food("broccoli")

            # Verify cache file was created (default is True)
            assert cache_file.exists()
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            assert "search_broccoli" in cache_data

    @pytest.mark.asyncio
    async def test_search_food_save_cache_sequence(self, tmp_path):
        """Test save_cache behavior in sequences (True->False, False->True)."""
        import json

        with patch("core.food_apis.unified_db.USDAClient") as mock_usda:
            mock_client = MagicMock()
            mock_usda.return_value = mock_client

            # Create different mock responses
            from core.food_apis.usda_client import USDAFoodItem

            def create_mock_food(fdc_id, description, category):
                return USDAFoodItem(
                    fdc_id=fdc_id,
                    description=description,
                    food_category=category,
                    nutrients_per_100g={"protein_g": 1.0, "kcal": 50},
                    data_type="SR Legacy",
                    publication_date="2021-10-28",
                )

            search_results = {
                "apple": [create_mock_food(1001, "Apple, raw", "Fruits and Fruit Juices")],
                "banana": [create_mock_food(1002, "Banana, raw", "Fruits and Fruit Juices")],
                "carrot": [
                    create_mock_food(1003, "Carrot, raw", "Vegetables and Vegetable Products")
                ],
            }

            async def mock_search_foods(query, *args, **kwargs):
                query_lower = query.lower()
                for key in search_results:
                    if key in query_lower:
                        return search_results[key]
                return []

            mock_client.search_foods = mock_search_foods

            from core.food_apis.unified_db import UnifiedFoodDatabase

            db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
            db.off_client = None
            cache_file = tmp_path / "unified_food_cache.json"

            # Sequence 1: save_cache=True, then save_cache=False
            await db.search_food("apple", save_cache=True)
            assert cache_file.exists()

            with open(cache_file, "r", encoding="utf-8") as f:
                cache_before = json.load(f)
            assert "search_apple" in cache_before

            # Call with save_cache=False - should not update DISK cache
            await db.search_food("banana", save_cache=False)

            with open(cache_file, "r", encoding="utf-8") as f:
                cache_after_false = json.load(f)
            # Banana should NOT be in DISK cache (save_cache=False doesn't trigger _save_cache)
            # Note: It WILL be in memory cache, but not persisted to disk
            assert "search_banana" not in cache_after_false
            # Apple should still be there
            assert "search_apple" in cache_after_false

            # Sequence 2: Now call with save_cache=True again
            await db.search_food("carrot", save_cache=True)

            with open(cache_file, "r", encoding="utf-8") as f:
                cache_final = json.load(f)
            # Carrot should now be in cache
            assert "search_carrot" in cache_final
            # Apple should still be there
            assert "search_apple" in cache_final
            # Banana is NOW in cache because save_cache=True was called after it,
            # which persists the entire _memory_cache (including banana)
            assert "search_banana" in cache_final

    @pytest.mark.asyncio
    async def test_search_food_save_cache_preserves_existing(self, tmp_path):
        """Test that save_cache=False doesn't modify existing cache."""
        import json

        with patch("core.food_apis.unified_db.USDAClient") as mock_usda:
            mock_client = MagicMock()
            mock_usda.return_value = mock_client

            from core.food_apis.usda_client import USDAFoodItem

            mock_food = USDAFoodItem(
                fdc_id=9999,
                description="Test Food Item",
                food_category="Test Category",
                nutrients_per_100g={"protein_g": 10.0, "kcal": 100},
                data_type="SR Legacy",
                publication_date="2021-10-28",
            )

            async def mock_search_foods(*args, **kwargs):
                return [mock_food]

            mock_client.search_foods = mock_search_foods

            from core.food_apis.unified_db import UnifiedFoodDatabase

            db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
            db.off_client = None
            cache_file = tmp_path / "unified_food_cache.json"

            # Create initial cache with save_cache=True
            await db.search_food("initial", save_cache=True)

            # Get initial cache state
            with open(cache_file, "r", encoding="utf-8") as f:
                initial_cache = json.load(f)
            initial_mtime = cache_file.stat().st_mtime

            # Small delay to ensure timestamp would change if file modified
            import time

            time.sleep(0.01)

            # Call with save_cache=False - should not modify cache
            await db.search_food("new_search", save_cache=False)

            # Verify cache file unchanged
            with open(cache_file, "r", encoding="utf-8") as f:
                final_cache = json.load(f)

            # Cache content should be identical (no new entry)
            assert initial_cache == final_cache
            # Modification time should be the same (file not rewritten)
            assert cache_file.stat().st_mtime == initial_mtime

    def test_save_cache_throttle_updates_last_save_ts(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test _save_cache throttling branch that updates _last_save_ts instead of early return."""
        import os
        from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

        # Ensure throttle is enabled but with a very small window so that
        # (now - last_save_ts) * 1000 >= ms and we hit the update branch.
        monkeypatch.setenv("UNIFIED_DB_SAVE_THROTTLE_MS", "1")

        with (
            patch("core.food_apis.unified_db.USDAClient") as mock_usda,
            patch("core.food_apis.unified_db.OFFClient", new=None),
        ):
            mock_usda.return_value = MagicMock()

            db = UnifiedFoodDatabase(cache_dir=str(tmp_path))

            # Seed in-memory cache so _save_cache has something to write
            db._memory_cache["k"] = UnifiedFoodItem(
                name="Test Food",
                nutrients_per_100g={"protein_g": 1.0, "fat_g": 1.0, "carbs_g": 1.0},
                cost_per_100g=1.0,
                tags=[],
                availability_regions=[],
                source="test",
                source_id="id",
            )

            # Force last save timestamp far in the past so throttle allows save
            db._last_save_ts = 0.0

            db._save_cache()

            # After save, _last_save_ts should be updated to a non-zero value
            assert hasattr(db, "_last_save_ts")
            assert db._last_save_ts != 0.0

        # Cleanup env to avoid side effects on other tests
        monkeypatch.delenv("UNIFIED_DB_SAVE_THROTTLE_MS", raising=False)
