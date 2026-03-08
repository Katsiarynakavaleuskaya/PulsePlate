"""
Tests for core.food_apis.unified_db module - unified food database

RU: Тесты для модуля унифицированной базы данных продуктов.
EN: Tests for unified food database module.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.food_apis.unified_db import (
    UnifiedFoodDatabase,
    UnifiedFoodItem,
    get_unified_food_db,
    search_foods_unified,
)
from core.food_apis.usda_client import USDAFoodItem


class TestUnifiedFoodItemDataClass:
    """Test UnifiedFoodItem dataclass."""

    def test_unified_food_item_creation(self):
        """Test UnifiedFoodItem creation."""
        item = UnifiedFoodItem(
            name="Chicken Breast",
            nutrients_per_100g={"protein": 25.0, "calories": 150.0},
            cost_per_100g=3.50,
            tags=["protein", "meat"],
            availability_regions=["US", "EU"],
            source="USDA",
            source_id="12345",
            category="Poultry",
        )

        assert item.name == "Chicken Breast"
        assert item.nutrients_per_100g["protein"] == 25.0
        assert item.cost_per_100g == 3.50
        assert item.tags == ["protein", "meat"]
        assert item.availability_regions == ["US", "EU"]
        assert item.source == "USDA"
        assert item.source_id == "12345"
        assert item.category == "Poultry"

    def test_unified_food_item_optional_category(self):
        """Test UnifiedFoodItem with optional category."""
        item = UnifiedFoodItem(
            name="Unknown Food",
            nutrients_per_100g={"calories": 100.0},
            cost_per_100g=1.0,
            tags=[],
            availability_regions=["US"],
            source="Test",
            source_id="test",
        )

        assert item.category is None


class TestUnifiedFoodItemConversions:
    """Test UnifiedFoodItem conversion methods."""

    def test_from_usda_item(self):
        """Test conversion from USDA item with macronutrient defaults."""
        # Create mock USDA item with partial nutrients (missing carbs_g)
        usda_item = USDAFoodItem(
            fdc_id=12345,
            description="Chicken, broilers or fryers, breast, meat only, cooked, roasted",
            food_category="Poultry Products",
            nutrients_per_100g={"protein_g": 31.0, "kcal": 165.0, "fat_g": 3.6},
            data_type="Foundation",
            publication_date="2019-04-01",
        )

        # Mock the _generate_tags method
        with patch.object(usda_item, "_generate_tags", return_value=["protein", "meat"]):
            unified_item = UnifiedFoodItem.from_usda_item(usda_item, estimated_cost=4.0)

        assert (
            unified_item.name == "Chicken, broilers or fryers, breast, meat only, cooked, roasted"
        )
        # Check that defaults were added for missing macros
        assert unified_item.nutrients_per_100g["protein_g"] == 31.0
        assert unified_item.nutrients_per_100g["fat_g"] == 3.6
        assert unified_item.nutrients_per_100g["carbs_g"] == 0.0  # Default added
        assert unified_item.nutrients_per_100g["kcal"] == 165.0
        assert unified_item.cost_per_100g == 4.0
        assert unified_item.tags == ["protein", "meat"]
        assert unified_item.availability_regions == ["US", "BY", "RU"]
        assert unified_item.source == "USDA FoodData Central"
        assert unified_item.source_id == "12345"
        assert unified_item.category == "Poultry Products"

    @patch("core.food_apis.unified_db.OFF_AVAILABLE", True)
    def test_from_off_item(self):
        """Test conversion from Open Food Facts item with macronutrient defaults."""
        # Create mock OFF item with partial nutrients (missing fat_g and carbs_g)
        mock_off_item = MagicMock()
        mock_off_item.product_name = "Greek Yogurt"
        mock_off_item.nutrients_per_100g = {"protein_g": 10.0, "kcal": 59.0}
        mock_off_item._generate_tags.return_value = ["dairy", "protein"]
        mock_off_item.countries = ["US", "Canada"]
        mock_off_item.code = "1234567890123"
        mock_off_item.categories = ["Dairy products", "Fermented dairy products"]

        unified_item = UnifiedFoodItem.from_off_item(mock_off_item, estimated_cost=2.5)

        assert unified_item.name == "Greek Yogurt"
        # Check that defaults were added for missing macros
        assert unified_item.nutrients_per_100g["protein_g"] == 10.0
        assert unified_item.nutrients_per_100g["fat_g"] == 0.0  # Default added
        assert unified_item.nutrients_per_100g["carbs_g"] == 0.0  # Default added
        assert unified_item.nutrients_per_100g["kcal"] == 59.0
        assert unified_item.cost_per_100g == 2.5
        assert unified_item.tags == ["dairy", "protein"]
        assert unified_item.availability_regions == ["US", "Canada"]
        assert unified_item.source == "Open Food Facts"
        assert unified_item.source_id == "1234567890123"
        assert unified_item.category == "Dairy products"

    @patch("core.food_apis.unified_db.OFF_AVAILABLE", True)
    def test_from_off_item_no_categories(self):
        """Test conversion from OFF item with no categories."""
        mock_off_item = MagicMock()
        mock_off_item.product_name = "Unknown Product"
        mock_off_item.nutrients_per_100g = {"calories": 100.0}
        mock_off_item._generate_tags.return_value = []
        mock_off_item.countries = ["US"]
        mock_off_item.code = "123"
        mock_off_item.categories = []  # Empty categories

        unified_item = UnifiedFoodItem.from_off_item(mock_off_item)

        assert unified_item.category is None

    def test_to_menu_engine_format(self):
        """Test conversion to menu engine format."""
        item = UnifiedFoodItem(
            name="Test Food",
            nutrients_per_100g={"protein": 20.0},
            cost_per_100g=1.5,
            tags=["test"],
            availability_regions=["US"],
            source="Test Source",
            source_id="test123",
            category="Test Category",
        )

        result = item.to_menu_engine_format()

        expected = {
            "name": "Test Food",
            "nutrients_per_100g": {"protein": 20.0},
            "cost_per_100g": 1.5,
            "tags": ["test"],
            "availability_regions": ["US"],
            "source": "Test Source",
            "source_id": "test123",
            "category": "Test Category",
        }

        assert result == expected


class TestUnifiedFoodDatabaseBasics:
    """Test basic UnifiedFoodDatabase functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @patch("core.food_apis.unified_db.OFFClient")
    def test_database_initialization(self, mock_off_client, temp_cache_dir):
        """Test database initialization."""
        # Mock OFF client constructor
        mock_off_instance = MagicMock()
        mock_off_client.return_value = mock_off_instance

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)

        assert db.usda_client is not None
        assert db.cache_dir == Path(temp_cache_dir)
        assert db.cache_dir.exists()
        assert isinstance(db._memory_cache, dict)

    def test_database_initialization_no_cache_dir(self):
        """Test database initialization without cache directory."""
        db = UnifiedFoodDatabase()

        assert db.cache_dir == Path("cache/food_db")
        assert isinstance(db._memory_cache, dict)

    def test_get_cache_file(self, temp_cache_dir):
        """Test cache file path generation."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)

        cache_file = db._get_cache_file()

        assert cache_file == Path(temp_cache_dir) / "unified_food_cache.json"

    def test_save_and_load_cache(self, temp_cache_dir):
        """Test cache save and load functionality."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)

        # Add item to memory cache
        test_item = UnifiedFoodItem(
            name="Test Food",
            nutrients_per_100g={"calories": 100.0},
            cost_per_100g=1.0,
            tags=["test"],
            availability_regions=["US"],
            source="Test",
            source_id="test123",
        )

        db._memory_cache["test_key"] = test_item

        # Save cache
        db._save_cache()

        # Check cache file exists
        cache_file = db._get_cache_file()
        assert cache_file.exists()

        # Create new database instance and load cache
        db2 = UnifiedFoodDatabase(cache_dir=temp_cache_dir)

        # Check item was loaded
        assert "test_key" in db2._memory_cache
        loaded_item = db2._memory_cache["test_key"]
        assert loaded_item.name == "Test Food"
        assert loaded_item.nutrients_per_100g == {"calories": 100.0}

    def test_load_cache_invalid_file(self, temp_cache_dir):
        """Test loading cache with invalid JSON file."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)

        # Create invalid JSON file
        cache_file = db._get_cache_file()
        with open(cache_file, "w") as f:
            f.write("invalid json content")

        # Should not crash, should handle gracefully
        db._load_cache()

        assert isinstance(db._memory_cache, dict)

    def test_load_cache_nonexistent_file(self, temp_cache_dir):
        """Test loading cache when file doesn't exist."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)

        # Should not crash when cache file doesn't exist
        db._load_cache()

        assert isinstance(db._memory_cache, dict)


class TestUnifiedFoodDatabaseSearch:
    """Test search functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_usda_client(self):
        """Create mock USDA client."""
        mock_client = AsyncMock()

        # Mock search results
        mock_usda_item = USDAFoodItem(
            fdc_id=12345,
            description="Chicken breast, cooked",
            food_category="Poultry",
            nutrients_per_100g={"protein": 25.0, "calories": 150.0},
            data_type="Foundation",
            publication_date="2019-04-01",
        )

        with patch.object(mock_usda_item, "_generate_tags", return_value=["protein", "meat"]):
            mock_client.search_foods.return_value = [mock_usda_item]
            mock_client.get_food_details.return_value = mock_usda_item

        return mock_client

    @pytest.fixture
    def mock_off_client(self):
        """Create mock OFF client."""
        mock_client = AsyncMock()

        # Mock search results
        mock_off_item = MagicMock()
        mock_off_item.product_name = "Greek Yogurt"
        mock_off_item.nutrients_per_100g = {"protein": 10.0, "calories": 59.0}
        mock_off_item._generate_tags.return_value = ["dairy"]
        mock_off_item.countries = ["US"]
        mock_off_item.code = "123456"
        mock_off_item.categories = ["Dairy"]

        mock_client.search_products.return_value = [mock_off_item]
        mock_client.get_product_details.return_value = mock_off_item

        return mock_client

    @pytest.mark.asyncio
    async def test_search_food_usda_preferred(self, temp_cache_dir, mock_usda_client):
        """Test food search with USDA preferred."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_client
        db.off_client = None

        results = await db.search_food("chicken breast", prefer_source="usda")

        assert len(results) == 1
        assert results[0].name == "Chicken breast, cooked"
        assert results[0].source == "USDA FoodData Central"

        # Check cache was updated
        cache_key = "search_chicken breast"
        assert cache_key in db._memory_cache

    @pytest.mark.asyncio
    @patch("core.food_apis.unified_db.OFFClient")
    async def test_search_food_off_preferred(
        self, mock_off_class, temp_cache_dir, mock_usda_client, mock_off_client
    ):
        """Test food search with Open Food Facts preferred."""
        # Set up OFF client mock
        mock_off_class.return_value = mock_off_client

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_client
        db.off_client = mock_off_client

        results = await db.search_food("yogurt", prefer_source="openfoodfacts")

        assert len(results) == 1
        assert results[0].name == "Greek Yogurt"
        assert results[0].source == "Open Food Facts"

    @pytest.mark.asyncio
    @patch("core.food_apis.unified_db.OFFClient")
    async def test_search_food_fallback_to_off(
        self, mock_off_class, temp_cache_dir, mock_off_client
    ):
        """Test search fallback to OFF when USDA returns no results."""
        # Set up empty USDA results
        mock_usda_empty = AsyncMock()
        mock_usda_empty.search_foods.return_value = []

        # Set up OFF client mock
        mock_off_class.return_value = mock_off_client

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_empty
        db.off_client = mock_off_client

        results = await db.search_food("unknown food", prefer_source="usda")

        assert len(results) == 1
        assert results[0].source == "Open Food Facts"

    @pytest.mark.asyncio
    async def test_search_food_cached_result(self, temp_cache_dir):
        """Test search returns cached result."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.off_client = None

        # Add cached item
        cached_item = UnifiedFoodItem(
            name="Cached Food",
            nutrients_per_100g={"calories": 100.0},
            cost_per_100g=1.0,
            tags=["test"],
            availability_regions=["US"],
            source="Cache",
            source_id="cached",
        )

        cache_key = "search_cached food"
        db._memory_cache[cache_key] = cached_item

        results = await db.search_food("cached food")

        assert len(results) == 1
        assert results[0].name == "Cached Food"
        assert results[0].source == "Cache"

    @pytest.mark.asyncio
    async def test_search_food_no_results(self, temp_cache_dir):
        """Test search with no results from any source."""
        # Mock empty results
        mock_usda_empty = AsyncMock()
        mock_usda_empty.search_foods.return_value = []

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_empty
        db.off_client = None  # No OFF client

        results = await db.search_food("nonexistent food")

        assert results == []


class TestUnifiedFoodDatabaseGetById:
    """Test get food by ID functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.mark.asyncio
    async def test_get_food_by_id_usda(self, temp_cache_dir):
        """Test getting USDA food by ID."""
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
            mock_usda_client.get_food_details.return_value = mock_usda_item

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda_client
        db.off_client = None

        result = await db.get_food_by_id("usda", "12345")

        assert result is not None
        assert result.name == "Test Food"
        assert result.source == "USDA FoodData Central"
        assert result.source_id == "12345"

        # Check cache was updated
        cache_key = "usda_12345"
        assert cache_key in db._memory_cache

    @pytest.mark.asyncio
    @patch("core.food_apis.unified_db.OFFClient")
    async def test_get_food_by_id_off(self, mock_off_class, temp_cache_dir):
        """Test getting OFF food by ID."""
        # Mock OFF client
        mock_off_client = AsyncMock()
        mock_off_item = MagicMock()
        mock_off_item.product_name = "OFF Product"
        mock_off_item.nutrients_per_100g = {"calories": 200.0}
        mock_off_item._generate_tags.return_value = ["test"]
        mock_off_item.countries = ["US"]
        mock_off_item.code = "123456"
        mock_off_item.categories = ["Test"]

        mock_off_client.get_product_details.return_value = mock_off_item
        mock_off_class.return_value = mock_off_client

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.off_client = mock_off_client

        result = await db.get_food_by_id("openfoodfacts", "123456")

        assert result is not None
        assert result.name == "OFF Product"
        assert result.source == "Open Food Facts"
        assert result.source_id == "123456"

    @pytest.mark.asyncio
    async def test_get_food_by_id_cached(self, temp_cache_dir):
        """Test getting food by ID from cache."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)

        # Add cached item
        cached_item = UnifiedFoodItem(
            name="Cached Food",
            nutrients_per_100g={"calories": 100.0},
            cost_per_100g=1.0,
            tags=["test"],
            availability_regions=["US"],
            source="Cache",
            source_id="cached123",
        )

        cache_key = "usda_cached123"
        db._memory_cache[cache_key] = cached_item

        result = await db.get_food_by_id("usda", "cached123")

        assert result is not None
        assert result.name == "Cached Food"
        assert result.source == "Cache"

    @pytest.mark.asyncio
    async def test_get_food_by_id_invalid_usda_id(self, temp_cache_dir):
        """Test getting USDA food with invalid ID."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)

        result = await db.get_food_by_id("usda", "invalid_id")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_food_by_id_unknown_source(self, temp_cache_dir):
        """Test getting food with unknown source."""
        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)

        result = await db.get_food_by_id("unknown_source", "123")

        assert result is None


class TestUnifiedFoodDatabaseClose:
    """Test database cleanup."""

    @pytest.mark.asyncio
    async def test_close_database(self):
        """Test closing database and clients."""
        # Mock clients
        mock_usda_client = AsyncMock()
        mock_off_client = AsyncMock()

        db = UnifiedFoodDatabase()
        db.usda_client = mock_usda_client
        db.off_client = mock_off_client

        await db.close()

        mock_usda_client.close.assert_called_once()
        mock_off_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_database_no_off_client(self):
        """Test closing database without OFF client."""
        mock_usda_client = AsyncMock()

        db = UnifiedFoodDatabase()
        db.usda_client = mock_usda_client
        db.off_client = None

        # Should not crash when OFF client is None
        await db.close()

        mock_usda_client.close.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions."""

    @pytest.mark.asyncio
    @patch("core.food_apis.unified_db.get_unified_food_db")
    async def test_search_foods_unified(self, mock_get_db):
        """Test unified search function."""
        # Mock database
        mock_db = AsyncMock()
        mock_item = UnifiedFoodItem(
            name="Test Food",
            nutrients_per_100g={"calories": 100.0},
            cost_per_100g=1.0,
            tags=["test"],
            availability_regions=["US"],
            source="Test",
            source_id="test123",
        )

        mock_db.search_food.return_value = [mock_item]
        mock_get_db.return_value = mock_db

        results = await search_foods_unified("test query", max_results=5)

        assert len(results) == 1
        assert results[0]["name"] == "Test Food"
        assert results[0]["nutrients_per_100g"] == {"calories": 100.0}

        mock_db.search_food.assert_called_once_with("test query")

    @pytest.mark.asyncio
    @patch("core.food_apis.unified_db._unified_db_instance", None)
    async def test_get_unified_food_db_new_instance(self):
        """Test getting new unified database instance."""
        db = await get_unified_food_db()

        assert db is not None
        assert isinstance(db, UnifiedFoodDatabase)

        # Second call should return same instance
        db2 = await get_unified_food_db()
        assert db is db2
