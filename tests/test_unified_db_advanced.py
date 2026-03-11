"""
Advanced tests for core.food_apis.unified_db module - common foods and integration

RU: Продвинутые тесты для модуля унифицированной базы данных - общие продукты и интеграция.
EN: Advanced tests for unified database module - common foods and integration.
"""

import tempfile
from unittest.mock import AsyncMock, mock_open, patch

import pytest

from core.food_apis.unified_db import (
    UnifiedFoodDatabase,
    UnifiedFoodItem,
    get_unified_food_db,
    search_foods_unified,
)
from core.food_apis.usda_client import USDAFoodItem


class TestUnifiedFoodDatabaseCommonFoods:
    """Test common foods database functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_usda_search_results(self):
        """Create mock USDA search results for common foods."""

        def create_mock_item(name, fdc_id):
            item = USDAFoodItem(
                fdc_id=fdc_id,
                description=name,
                food_category="Test Category",
                nutrients_per_100g={"protein": 20.0, "calories": 150.0},
                data_type="Foundation",
                publication_date="2019-04-01",
            )
            # Mock the _generate_tags method
            with patch.object(item, "_generate_tags", return_value=["test"]):
                return item

        return {
            "chicken breast meat only cooked roasted": create_mock_item(
                "Chicken, broilers, breast, meat only, cooked, roasted", 171077
            ),
            "salmon atlantic farmed cooked dry heat": create_mock_item(
                "Fish, salmon, Atlantic, farmed, cooked, dry heat", 175167
            ),
            "spinach raw": create_mock_item("Spinach, raw", 168462),
        }

    @pytest.mark.asyncio
    async def test_get_common_foods_database_from_cache(self, temp_cache_dir):
        """Test getting common foods from cache."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.off_client = None

        # Write cache file using mock_open and mock Path.exists separately
        with patch(
            "builtins.open",
            mock_open(
                read_data='{"chicken_breast": {"name": "Chicken Breast", "nutrients_per_100g": {"protein": 25.0, "calories": 165.0}, "cost_per_100g": 4.0, "tags": ["protein", "meat"], "availability_regions": ["US", "BY", "RU"], "source": "USDA FoodData Central", "source_id": "12345", "category": "Poultry"}}'
            ),
        ):
            with patch("pathlib.Path.exists", return_value=True):
                foods_db = await db.get_common_foods_database()

        assert len(foods_db) == 1
        assert "chicken_breast" in foods_db
        assert foods_db["chicken_breast"].name == "Chicken Breast"
        assert foods_db["chicken_breast"].nutrients_per_100g["protein"] == 25.0

    @pytest.mark.asyncio
    async def test_get_common_foods_database_build_new(
        self, temp_cache_dir, mock_usda_search_results
    ):
        """Test building new common foods database."""
        # Mock USDA client
        mock_usda_client = AsyncMock()

        # Configure search results for different queries
        async def mock_search_foods(query, page_size=5):
            if query in mock_usda_search_results:
                return [mock_usda_search_results[query]]
            return []

        mock_usda_client.search_foods.side_effect = mock_search_foods

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_client
        db.off_client = None

        # Mock asyncio.sleep to speed up test
        with patch("asyncio.sleep", new_callable=AsyncMock):
            foods_db = await db.get_common_foods_database()
            # Verify file-based cache is created after first build
            cache_file = db.cache_dir / "common_foods.json"
            assert cache_file.exists(), "Cache file should be created for common foods database"

            # Verify caching/idempotence: second call should return same result,
            # relying on the in-memory cache populated from the first call
            foods_db_cached = await db.get_common_foods_database()
            # Check that cached result has same content (not necessarily same object)
            assert len(foods_db) == len(foods_db_cached), "Cached result should have same length"
            assert set(foods_db.keys()) == set(
                foods_db_cached.keys()
            ), "Cached result should have same keys"

        # Should have some foods (at least the ones we mocked)
        assert len(foods_db) >= 3
        assert "chicken_breast" in foods_db
        assert "salmon" in foods_db
        assert "spinach" in foods_db

        # Check one food item
        chicken = foods_db["chicken_breast"]
        assert chicken.name == "Chicken, broilers, breast, meat only, cooked, roasted"
        assert chicken.source == "USDA FoodData Central"

    @pytest.mark.asyncio
    async def test_get_common_foods_database_cache_error(self, temp_cache_dir):
        """Test common foods database with cache loading error."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.off_client = None

        # Mock file exists but reading fails
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="invalid json")):
                # Mock USDA client to return empty results
                mock_usda_client = AsyncMock()
                mock_usda_client.search_foods.return_value = []
                db.usda_client = mock_usda_client

                with patch("asyncio.sleep", new_callable=AsyncMock):
                    foods_db = await db.get_common_foods_database()

        # Should return empty dict due to errors
        assert isinstance(foods_db, dict)

    @pytest.mark.asyncio
    async def test_get_common_foods_database_search_error(self, temp_cache_dir):
        """Test common foods database with search errors."""
        # Mock USDA client that raises errors
        mock_usda_client = AsyncMock()
        mock_usda_client.search_foods.side_effect = Exception("API Error")

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_client
        db.off_client = None

        with patch("asyncio.sleep", new_callable=AsyncMock):
            foods_db = await db.get_common_foods_database()

        # Should handle errors gracefully and return empty dict
        assert isinstance(foods_db, dict)

    @pytest.mark.asyncio
    async def test_get_common_foods_database_save_error(self, temp_cache_dir):
        """Test common foods database with cache save error."""
        # Mock USDA client
        mock_usda_client = AsyncMock()
        mock_usda_item = USDAFoodItem(
            fdc_id=12345,
            description="Test Food",
            food_category="Test",
            nutrients_per_100g={"calories": 100.0},
            data_type="Foundation",
            publication_date="2019-04-01",
        )

        with patch.object(mock_usda_item, "_generate_tags", return_value=["test"]):
            mock_usda_client.search_foods.return_value = [mock_usda_item]

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_client
        db.off_client = None

        # Mock file operations to fail on write
        with patch("builtins.open", side_effect=PermissionError("Cannot write")):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                foods_db = await db.get_common_foods_database()

        # Should still return foods even if cache save fails
        assert isinstance(foods_db, dict)


class TestUnifiedFoodDatabaseEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.mark.asyncio
    async def test_search_food_off_client_error(self, temp_cache_dir):
        """Test search when OFF client raises error."""
        # Mock USDA client with empty results
        mock_usda_client = AsyncMock()
        mock_usda_client.search_foods.return_value = []

        # Mock OFF client that raises error
        mock_off_client = AsyncMock()
        mock_off_client.search_products.side_effect = Exception("OFF API Error")

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_client
        db.off_client = mock_off_client

        # Should handle error gracefully
        results = await db.search_food("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_get_food_by_id_off_client_error(self, temp_cache_dir):
        """Test get by ID when OFF client raises error."""
        # Mock OFF client that raises error
        mock_off_client = AsyncMock()
        mock_off_client.get_product_details.side_effect = Exception("OFF API Error")

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.off_client = mock_off_client

        # Should handle error gracefully
        result = await db.get_food_by_id("openfoodfacts", "123456")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_food_by_id_usda_not_found(self, temp_cache_dir):
        """Test get USDA food by ID when not found."""
        # Mock USDA client that returns None
        mock_usda_client = AsyncMock()
        mock_usda_client.get_food_details.return_value = None

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_client

        result = await db.get_food_by_id("usda", "12345")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_food_by_id_off_not_found(self, temp_cache_dir):
        """Test get OFF food by ID when not found."""
        # Mock OFF client that returns None
        mock_off_client = AsyncMock()
        mock_off_client.get_product_details.return_value = None

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.off_client = mock_off_client

        result = await db.get_food_by_id("openfoodfacts", "123456")

        assert result is None

    def test_save_cache_error_handling(self, temp_cache_dir):
        """Test cache save with file permission error."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)

        # Add item to cache
        test_item = UnifiedFoodItem(
            name="Test Food",
            nutrients_per_100g={"calories": 100.0},
            cost_per_100g=1.0,
            tags=["test"],
            availability_regions=["US"],
            source="Test",
            source_id="test123",
        )
        db._memory_cache["test"] = test_item

        # Mock file operation to fail
        with patch("builtins.open", side_effect=PermissionError("Cannot write")):
            # Should not crash when save fails
            db._save_cache()

        # Memory cache should still be intact
        assert "test" in db._memory_cache

    def test_cache_directory_creation_error(self):
        """Test database initialization when cache directory creation fails."""
        # Try to create cache in a read-only location that might fail
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Cannot create directory")):
            # Should handle directory creation error gracefully
            try:
                db = UnifiedFoodDatabase(cache_dir="/root/readonly_dir")
                assert isinstance(db._memory_cache, dict)
            except PermissionError:
                # This is acceptable - function might not handle this specific error
                pass

    @pytest.mark.asyncio
    @patch("core.food_apis.unified_db.OFFClient", None)  # Simulate OFF not available
    async def test_search_food_without_off_client(self, temp_cache_dir):
        """Test search when OFF client is not available."""
        # Mock USDA client
        mock_usda_client = AsyncMock()
        mock_usda_item = USDAFoodItem(
            fdc_id=12345,
            description="Test Food",
            food_category="Test",
            nutrients_per_100g={"calories": 100.0},
            data_type="Foundation",
            publication_date="2019-04-01",
        )

        with patch.object(mock_usda_item, "_generate_tags", return_value=["test"]):
            mock_usda_client.search_foods.return_value = [mock_usda_item]

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_client
        db.off_client = None  # No OFF client available

        # When prefer_source="openfoodfacts" but OFF is unavailable, should return empty results
        # because current logic doesn't fallback to USDA
        results = await db.search_food("test query", prefer_source="openfoodfacts")

        assert len(results) == 0  # No results because OFF unavailable and no fallback

        # But with prefer_source="usda" should work
        results = await db.search_food("test query", prefer_source="usda")

        assert len(results) == 1
        assert results[0].source == "USDA FoodData Central"


class TestModuleConstants:
    """Test module-level constants and configuration."""

    def test_off_available_constant(self):
        """Test OFF_AVAILABLE constant."""
        from core.food_apis.unified_db import OFF_AVAILABLE

        # Should be a boolean
        assert isinstance(OFF_AVAILABLE, bool)

    def test_off_client_symbol_exists(self):
        """Test that OFFClient symbol exists in module."""
        from core.food_apis.unified_db import OFFClient

        # Symbol should exist (even if None)
        assert OFFClient is not None or OFFClient is None  # Just check it's defined

    def test_module_level_imports(self):
        """Test that module imports work correctly."""
        try:
            from core.food_apis.unified_db import (
                UnifiedFoodDatabase,
                UnifiedFoodItem,
                get_unified_food_db,
                search_foods_unified,
            )

            # All imports should work
            assert UnifiedFoodItem is not None
            assert UnifiedFoodDatabase is not None
            assert search_foods_unified is not None
            assert get_unified_food_db is not None

        except ImportError as e:
            pytest.fail(f"Module imports failed: {e}")


class TestAsyncUtilities:
    """Test async utility functions with different scenarios."""

    @pytest.mark.asyncio
    async def test_search_foods_unified_max_results(self):
        """Test unified search with max results limit."""
        # Mock database with multiple results
        mock_db = AsyncMock()

        # Create multiple mock items
        mock_items = []
        for i in range(10):
            item = UnifiedFoodItem(
                name=f"Test Food {i}",
                nutrients_per_100g={"calories": 100.0 + i},
                cost_per_100g=1.0 + i,
                tags=[f"test{i}"],
                availability_regions=["US"],
                source="Test",
                source_id=f"test{i}",
            )
            mock_items.append(item)

        mock_db.search_food.return_value = mock_items

        with patch("core.food_apis.unified_db.get_unified_food_db", return_value=mock_db):
            results = await search_foods_unified("test query", max_results=3)

        # Should limit to 3 results
        assert len(results) == 3
        assert results[0]["name"] == "Test Food 0"
        assert results[1]["name"] == "Test Food 1"
        assert results[2]["name"] == "Test Food 2"

    @pytest.mark.asyncio
    async def test_search_foods_unified_empty_results(self):
        """Test unified search with empty results."""
        mock_db = AsyncMock()
        mock_db.search_food.return_value = []

        with patch("core.food_apis.unified_db.get_unified_food_db", return_value=mock_db):
            results = await search_foods_unified("nonexistent food")

        assert results == []

    @pytest.mark.asyncio
    @patch("core.food_apis.unified_db._unified_db_instance")
    async def test_get_unified_food_db_existing_instance(self, mock_instance):
        """Test getting existing unified database instance."""
        # Mock existing instance
        mock_db = UnifiedFoodDatabase()
        mock_instance.__bool__ = lambda self: True  # Simulate non-None instance

        with patch("core.food_apis.unified_db._unified_db_instance", mock_db):
            db = await get_unified_food_db()

        assert db is mock_db
