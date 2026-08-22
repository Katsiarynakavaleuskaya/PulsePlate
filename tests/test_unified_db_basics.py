"""
Tests for core.food_apis.unified_db module - unified food database

RU: Тесты для модуля унифицированной базы данных продуктов.
EN: Tests for unified food database module.
"""

import asyncio
from collections.abc import Iterator
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import core.food_apis.unified_db as unified_db_module
from core.food_apis.unified_db import (
    UnifiedFoodDatabase,
    UnifiedFoodItem,
    get_unified_food_db,
    search_foods_unified,
)
from core.food_apis.usda_client import USDAFoodItem
from core.off_nutrition.bridge import (
    merge_wire_nutrition_sources,
    nutrition_inputs_from_unified_wire,
)


def _replace_registered_unified_food(
    replacement: UnifiedFoodDatabase | None,
) -> UnifiedFoodDatabase | None:
    observed = unified_db_module._read_unified_db_instance()
    replaced, current = unified_db_module._compare_exchange_unified_db_instance(
        observed,
        replacement,
    )
    assert replaced
    assert current is replacement
    return observed


@pytest.fixture(autouse=True)
def _restore_unified_food_register() -> Iterator[None]:
    read_register = unified_db_module._read_unified_db_instance
    compare_exchange = unified_db_module._compare_exchange_unified_db_instance
    original = read_register()
    yield
    current = read_register()
    restored, observed = compare_exchange(
        current,
        original,
    )
    assert restored
    assert observed is original


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
        """USDA conversion preserves only supplied resolver-backed nutrients."""
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
        assert unified_item.nutrients_per_100g["protein_g"] == 31.0
        assert unified_item.nutrients_per_100g["fat_g"] == 3.6
        assert "carbs_g" not in unified_item.nutrients_per_100g
        assert unified_item.nutrients_per_100g["kcal"] == 165.0
        assert unified_item.cost_per_100g == 4.0
        assert unified_item.tags == ["protein", "meat"]
        assert unified_item.availability_regions == ["US", "BY", "RU"]
        assert unified_item.source == "USDA FoodData Central"
        assert unified_item.source_id == "12345"
        assert unified_item.category == "Poultry Products"
        assert "carbs_g" not in unified_item.nutrition_provenance
        assert "carbs_g" not in unified_item.nutrition_nutrient_confidence
        assert unified_item.nutrition_provenance.get("protein_g") == "usda"
        assert unified_item.nutrition_confidence == 0.7
        reconstructed_inputs = nutrition_inputs_from_unified_wire(
            nutrition_inputs_wire=unified_item.nutrition_inputs,
            nutrients_per_100g=unified_item.nutrients_per_100g,
            fallback_source="usda",
            record_id=unified_item.source_id,
        )
        reconstructed = merge_wire_nutrition_sources(
            primary_inputs=reconstructed_inputs,
            secondary_inputs=[],
            nutrient_keys=sorted(unified_item.nutrients_per_100g),
        )
        assert dict(reconstructed.nutrients) == unified_item.nutrients_per_100g
        assert dict(reconstructed.provenance) == unified_item.nutrition_provenance
        assert dict(reconstructed.nutrient_confidence) == unified_item.nutrition_nutrient_confidence
        assert reconstructed.confidence == unified_item.nutrition_confidence

    @patch("core.food_apis.unified_db.OFF_AVAILABLE", True)
    def test_from_off_item(self):
        """Legacy flat OFF conversion preserves only explicit estimate nutrients."""
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
        assert unified_item.nutrients_per_100g["protein_g"] == 10.0
        assert "fat_g" not in unified_item.nutrients_per_100g
        assert "carbs_g" not in unified_item.nutrients_per_100g
        assert "fat_g" not in unified_item.nutrition_provenance
        assert "carbs_g" not in unified_item.nutrition_provenance
        assert "fat_g" not in unified_item.nutrition_nutrient_confidence
        assert "carbs_g" not in unified_item.nutrition_nutrient_confidence
        assert unified_item.nutrients_per_100g["kcal"] == 59.0
        assert unified_item.cost_per_100g == 2.5
        assert unified_item.tags == ["dairy", "protein"]
        assert unified_item.availability_regions == ["US", "Canada"]
        assert unified_item.source == "Open Food Facts"
        assert unified_item.source_id == "1234567890123"
        assert unified_item.category == "Dairy products"
        reconstructed_inputs = nutrition_inputs_from_unified_wire(
            nutrition_inputs_wire=unified_item.nutrition_inputs,
            nutrients_per_100g=unified_item.nutrients_per_100g,
            fallback_source="estimate",
            record_id=unified_item.source_id,
        )
        reconstructed = merge_wire_nutrition_sources(
            primary_inputs=reconstructed_inputs,
            secondary_inputs=[],
            nutrient_keys=sorted(unified_item.nutrients_per_100g),
        )
        assert dict(reconstructed.nutrients) == unified_item.nutrients_per_100g
        assert dict(reconstructed.provenance) == unified_item.nutrition_provenance
        assert dict(reconstructed.nutrient_confidence) == unified_item.nutrition_nutrient_confidence
        assert reconstructed.confidence == unified_item.nutrition_confidence

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

    def test_from_usda_and_off_merge_usda_wins_on_shared_macro(self) -> None:
        """USDA protein_g should beat OFF estimate when both provide the same key."""
        usda_item = USDAFoodItem(
            fdc_id=9001,
            description="Chicken merge row",
            food_category="Poultry",
            nutrients_per_100g={"protein_g": 31.0, "kcal": 165.0},
            data_type="Foundation",
            publication_date="2019-04-01",
        )
        with patch.object(usda_item, "_generate_tags", return_value=["meat"]):
            usda_u = UnifiedFoodItem.from_usda_item(usda_item)

        mock_off = MagicMock()
        mock_off.product_name = "Branded chicken"
        mock_off.nutrients_per_100g = {"protein_g": 10.0, "fiber_g": 3.0}
        mock_off._generate_tags.return_value = ["branded"]
        mock_off.countries = ["US"]
        mock_off.code = "9998887776665"
        mock_off.categories = ["Meat"]
        off_u = UnifiedFoodItem.from_off_item(mock_off)

        merged = UnifiedFoodItem.from_usda_and_off_merge(usda_u, off_u)
        assert merged.nutrients_per_100g["protein_g"] == 31.0
        assert merged.nutrients_per_100g.get("fiber_g") == 3.0
        assert "merged" in merged.source.lower()
        assert merged.nutrition_provenance.get("protein_g") == "usda"
        assert merged.nutrition_provenance.get("fiber_g") == "estimate"


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

    @pytest.mark.asyncio
    async def test_search_food_usda_pref_merges_top_hit_with_off(self, temp_cache_dir) -> None:
        """With prefer_source=usda, top USDA hit is enriched via OFF + resolver."""
        mock_usda = AsyncMock()
        usda_item = USDAFoodItem(
            fdc_id=4242,
            description="Resolver merge chicken",
            food_category="Poultry",
            nutrients_per_100g={"protein_g": 31.0, "kcal": 165.0},
            data_type="Foundation",
            publication_date="2019-04-01",
        )
        with patch.object(usda_item, "_generate_tags", return_value=["meat"]):
            mock_usda.search_foods.return_value = [usda_item]

        mock_off = AsyncMock()
        off_item = MagicMock()
        off_item.product_name = "Branded chicken"
        off_item.nutrients_per_100g = {"protein_g": 10.0, "fiber_g": 3.0}
        off_item._generate_tags.return_value = ["branded"]
        off_item.countries = ["US"]
        off_item.code = "1112223334445"
        off_item.categories = ["Meat"]
        mock_off.search_products.return_value = [off_item]

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda
        db.off_client = mock_off

        results = await db.search_food("resolver merge chicken", prefer_source="usda")
        assert len(results) >= 1
        top = results[0]
        assert "merged" in top.source.lower()
        assert top.nutrients_per_100g["protein_g"] == 31.0
        assert top.nutrients_per_100g.get("fiber_g") == 3.0
        mock_off.search_products.assert_awaited()

    @pytest.mark.asyncio
    async def test_search_food_usda_pref_merge_skips_when_off_raises(
        self, temp_cache_dir, caplog
    ) -> None:
        """Merge block must swallow OFF errors and keep plain USDA row."""
        import logging

        mock_usda = AsyncMock()
        usda_item = USDAFoodItem(
            fdc_id=777,
            description="Plain USDA row",
            food_category="Poultry",
            nutrients_per_100g={"protein_g": 20.0},
            data_type="Foundation",
            publication_date="2019-04-01",
        )
        with patch.object(usda_item, "_generate_tags", return_value=["meat"]):
            mock_usda.search_foods.return_value = [usda_item]

        mock_off = AsyncMock()
        mock_off.search_products.side_effect = RuntimeError("off unavailable")

        db = UnifiedFoodDatabase(cache_dir=temp_cache_dir)
        db.usda_client = mock_usda
        db.off_client = mock_off

        caplog.set_level(logging.DEBUG, logger="core.food_apis.unified_db")
        results = await db.search_food("plain usda merge skip", prefer_source="usda")
        assert len(results) == 1
        assert results[0].source == "USDA FoodData Central"
        assert "skipping USDA+OFF" in caplog.text
        assert "search_plain usda merge skip" not in db._memory_cache  # noqa: SLF001

        off_item = MagicMock()
        off_item.product_name = "Branded retry"
        off_item.nutrients_per_100g = {"fiber_g": 2.0}
        off_item._generate_tags.return_value = ["branded"]
        off_item.countries = ["US"]
        off_item.code = "9998887776665"
        off_item.categories = ["Meat"]
        mock_off.search_products.side_effect = None
        mock_off.search_products.return_value = [off_item]

        caplog.clear()
        merged_results = await db.search_food("plain usda merge skip", prefer_source="usda")
        assert len(merged_results) == 1
        top = merged_results[0]
        assert "merged" in top.source.lower()
        assert top.nutrients_per_100g.get("fiber_g") == 2.0
        assert mock_off.search_products.await_count == 2


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
    async def test_get_unified_food_db_new_instance(self):
        """Test getting new unified database instance."""
        _replace_registered_unified_food(None)
        db = await get_unified_food_db()

        assert db is not None
        assert isinstance(db, UnifiedFoodDatabase)

        # Second call should return same instance
        db2 = await get_unified_food_db()
        assert db is db2

        cleared, observed = unified_db_module._compare_exchange_unified_db_instance(db, None)
        assert cleared
        assert observed is None
        await db.close()


class _EqualRegisterCandidate:
    def __init__(self, identity: str) -> None:
        self.identity = identity

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _EqualRegisterCandidate) and self.identity == other.identity


class _RaceCandidate:
    def __init__(self, name: str, close_error: BaseException | None = None) -> None:
        self.name = name
        self.close_error = close_error
        self.close_calls = 0
        self.usda_client = self
        self.off_client = None

    async def close(self) -> None:
        assert not unified_db_module._unified_db_instance_lock.locked()
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


def test_unified_food_register_compare_exchange_uses_identity() -> None:
    _replace_registered_unified_food(None)
    first = cast(UnifiedFoodDatabase, _EqualRegisterCandidate("same"))
    equal_but_distinct = cast(UnifiedFoodDatabase, _EqualRegisterCandidate("same"))
    assert first == equal_but_distinct
    assert first is not equal_but_distinct

    published, observed = unified_db_module._compare_exchange_unified_db_instance(None, first)
    assert published
    assert observed is first

    replaced, observed = unified_db_module._compare_exchange_unified_db_instance(
        equal_but_distinct,
        None,
    )
    assert not replaced
    assert observed is first
    assert unified_db_module._read_unified_db_instance() is first

    replaced, observed = unified_db_module._compare_exchange_unified_db_instance(
        first,
        equal_but_distinct,
    )
    assert replaced
    assert observed is equal_but_distinct


@pytest.mark.parametrize("replacement_first", [True, False])
def test_unified_food_register_clear_preserves_identity_order(
    replacement_first: bool,
) -> None:
    _replace_registered_unified_food(None)
    managed = cast(UnifiedFoodDatabase, _EqualRegisterCandidate("managed"))
    replacement = cast(UnifiedFoodDatabase, _EqualRegisterCandidate("replacement"))
    assert unified_db_module._compare_exchange_unified_db_instance(None, managed)[0]

    if replacement_first:
        assert unified_db_module._compare_exchange_unified_db_instance(
            managed,
            replacement,
        )[0]
        cleared, observed = unified_db_module._compare_exchange_unified_db_instance(
            managed,
            None,
        )
        assert not cleared
        assert observed is replacement
    else:
        assert unified_db_module._compare_exchange_unified_db_instance(managed, None)[0]
        assert unified_db_module._compare_exchange_unified_db_instance(
            None,
            replacement,
        )[0]

    assert unified_db_module._read_unified_db_instance() is replacement


def test_close_unified_food_clients_bounds_unique_sync_and_awaitable_clients() -> None:
    events: list[str] = []

    class _SyncClient:
        def close(self) -> None:
            events.append("sync")

    class _AsyncClient:
        async def close(self) -> None:
            events.append("async")

    sync_client = _SyncClient()
    async_client = _AsyncClient()
    asyncio.run(
        unified_db_module.close_unified_food_clients(
            SimpleNamespace(
                usda_client=sync_client,
                off_client=async_client,
                unrelated_client=_SyncClient(),
            )
        )
    )
    assert events == ["sync", "async"]

    events.clear()
    asyncio.run(
        unified_db_module.close_unified_food_clients(
            SimpleNamespace(usda_client=sync_client, off_client=sync_client)
        )
    )
    assert events == ["sync"]
    asyncio.run(
        unified_db_module.close_unified_food_clients(
            SimpleNamespace(usda_client=None, off_client=SimpleNamespace(close=None))
        )
    )
    asyncio.run(unified_db_module.close_unified_food_clients(SimpleNamespace()))


def test_close_unified_food_clients_attribute_failure_still_attempts_other_client() -> None:
    events: list[str] = []

    class _OffClient:
        def close(self) -> None:
            events.append("off")

    class _AttributeFailure:
        off_client = _OffClient()

        @property
        def usda_client(self) -> object:
            raise RuntimeError("raw-attribute-error")

    with pytest.raises(
        unified_db_module.UnifiedFoodClientCleanupError,
        match=f"^{unified_db_module.UNIFIED_FOOD_CLEANUP_ERROR_MESSAGE}$",
    ) as exc_info:
        asyncio.run(unified_db_module.close_unified_food_clients(_AttributeFailure()))
    assert events == ["off"]
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None


@pytest.mark.parametrize(
    ("first_signal", "second_signal", "expected_type"),
    [
        ("ordinary", "cancel", asyncio.CancelledError),
        ("cancel", "ordinary", asyncio.CancelledError),
        ("cancel", "keyboard", KeyboardInterrupt),
        ("keyboard", "cancel", KeyboardInterrupt),
        ("ordinary", "system", SystemExit),
        ("system", "ordinary", SystemExit),
        ("ordinary", "generator", GeneratorExit),
        ("generator", "ordinary", GeneratorExit),
    ],
)
def test_close_unified_food_clients_signal_precedence_is_order_independent(
    first_signal: str,
    second_signal: str,
    expected_type: type[BaseException],
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _error(signal: str) -> BaseException:
        if signal == "ordinary":
            return RuntimeError("raw-ordinary")
        if signal == "cancel":
            return asyncio.CancelledError("raw-cancel")
        if signal == "keyboard":
            return KeyboardInterrupt("raw-keyboard")
        if signal == "system":
            return SystemExit("raw-system-code")
        return GeneratorExit("raw-generator")

    class _SignalClient:
        def __init__(self, error: BaseException) -> None:
            self.error = error

        async def close(self) -> None:
            raise self.error

    instance = SimpleNamespace(
        usda_client=_SignalClient(_error(first_signal)),
        off_client=_SignalClient(_error(second_signal)),
    )
    with pytest.raises(expected_type) as exc_info:
        asyncio.run(unified_db_module.close_unified_food_clients(instance))

    top = exc_info.value
    assert top.__context__ is None
    assert "raw-" not in str(top)
    if isinstance(top, asyncio.CancelledError):
        assert str(top) == unified_db_module.UNIFIED_FOOD_CLEANUP_CANCELLED_MESSAGE
        assert isinstance(top.__cause__, unified_db_module.UnifiedFoodClientCleanupError)
    elif isinstance(top, SystemExit):
        assert top.code == 1
        assert isinstance(top.__cause__, unified_db_module.UnifiedFoodClientCleanupError)
    elif isinstance(top, (KeyboardInterrupt, GeneratorExit)):
        assert str(top) == ""
        if "ordinary" in {first_signal, second_signal}:
            assert isinstance(top.__cause__, unified_db_module.UnifiedFoodClientCleanupError)
        else:
            assert isinstance(top.__cause__, asyncio.CancelledError)
            assert str(top.__cause__) == unified_db_module.UNIFIED_FOOD_CLEANUP_CANCELLED_MESSAGE
    cause = top.__cause__
    while cause is not None:
        assert cause.__context__ is None
        assert "raw-" not in str(cause)
        cause = cause.__cause__
    assert caplog.records == []


@pytest.mark.parametrize(
    ("raw_code", "expected_code"),
    [(None, None), (7, 7), (True, 1), ("private-code", 1)],
)
def test_close_unified_food_clients_sanitizes_system_exit_code(
    raw_code: object,
    expected_code: int | None,
) -> None:
    class _SystemExitClient:
        async def close(self) -> None:
            raise SystemExit(raw_code)

    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(
            unified_db_module.close_unified_food_clients(
                SimpleNamespace(usda_client=_SystemExitClient(), off_client=None)
            )
        )
    assert exc_info.value.code == expected_code
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None


@pytest.mark.parametrize(("first_code", "second_code"), [(3, 4), (4, 3)])
def test_close_unified_food_clients_preserves_first_within_process_tier(
    first_code: int,
    second_code: int,
) -> None:
    class _SystemExitClient:
        def __init__(self, code: int) -> None:
            self.code = code

        async def close(self) -> None:
            raise SystemExit(self.code)

    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(
            unified_db_module.close_unified_food_clients(
                SimpleNamespace(
                    usda_client=_SystemExitClient(first_code),
                    off_client=_SystemExitClient(second_code),
                )
            )
        )
    assert exc_info.value.code == first_code


def test_close_unified_food_clients_ordinary_error_is_fixed_from_none() -> None:
    class _OrdinaryClient:
        async def close(self) -> None:
            raise RuntimeError("raw-private-error")

    with pytest.raises(
        unified_db_module.UnifiedFoodClientCleanupError,
        match=f"^{unified_db_module.UNIFIED_FOOD_CLEANUP_ERROR_MESSAGE}$",
    ) as exc_info:
        asyncio.run(
            unified_db_module.close_unified_food_clients(
                SimpleNamespace(usda_client=_OrdinaryClient(), off_client=None)
            )
        )
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None


@pytest.mark.parametrize("winner_name", ["first", "second"])
@pytest.mark.parametrize("loser_fails", [False, True])
def test_get_unified_food_db_concurrent_publish_closes_loser_outside_lock(
    monkeypatch: pytest.MonkeyPatch,
    winner_name: str,
    loser_fails: bool,
) -> None:
    _replace_registered_unified_food(None)
    construction_barrier = threading.Barrier(2)
    winner_published = threading.Event()
    result_lock = threading.Lock()
    candidates: dict[str, _RaceCandidate] = {}
    results: list[UnifiedFoodDatabase] = []
    errors: list[BaseException] = []
    real_compare_exchange = unified_db_module._compare_exchange_unified_db_instance

    def _new_candidate(_cls: type[UnifiedFoodDatabase]) -> _RaceCandidate:
        name = threading.current_thread().name
        close_error = (
            RuntimeError("raw-loser-close") if loser_fails and name != winner_name else None
        )
        candidate = _RaceCandidate(name, close_error)
        with result_lock:
            candidates[name] = candidate
        return candidate

    def _initialize_candidate(_candidate: object) -> None:
        construction_barrier.wait(timeout=2)

    def _ordered_compare_exchange(
        expected: UnifiedFoodDatabase | None,
        replacement: UnifiedFoodDatabase | None,
    ) -> tuple[bool, UnifiedFoodDatabase | None]:
        name = threading.current_thread().name
        if expected is None and replacement is not None and name in {"first", "second"}:
            if name == winner_name:
                result = real_compare_exchange(expected, replacement)
                winner_published.set()
                return result
            assert winner_published.wait(timeout=2)
        return real_compare_exchange(expected, replacement)

    def _worker() -> None:
        try:
            result = asyncio.run(unified_db_module.get_unified_food_db())
            with result_lock:
                results.append(result)
        except BaseException as exc:
            with result_lock:
                errors.append(exc)

    class _CandidateDatabase:
        @staticmethod
        def __new__(cls: type[object]) -> _RaceCandidate:
            return _new_candidate(cast(type[UnifiedFoodDatabase], cls))

        def __init__(self) -> None:
            _initialize_candidate(self)

    monkeypatch.setattr(unified_db_module, "UnifiedFoodDatabase", _CandidateDatabase)
    monkeypatch.setattr(
        unified_db_module,
        "_compare_exchange_unified_db_instance",
        _ordered_compare_exchange,
    )
    workers = [
        threading.Thread(target=_worker, name="first"),
        threading.Thread(target=_worker, name="second"),
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=2)

    assert not any(worker.is_alive() for worker in workers)
    winner = candidates[winner_name]
    loser_name = "second" if winner_name == "first" else "first"
    loser = candidates[loser_name]
    if loser_fails:
        assert results == [winner]
        assert len(errors) == 1
        assert isinstance(errors[0], unified_db_module.UnifiedFoodClientCleanupError)
        assert str(errors[0]) == unified_db_module.UNIFIED_FOOD_CLEANUP_ERROR_MESSAGE
        assert errors[0].__cause__ is None
        assert errors[0].__context__ is None
    else:
        assert errors == []
        assert results == [winner, winner]
    assert winner.close_calls == 0
    assert loser.close_calls == 1
    assert unified_db_module._read_unified_db_instance() is winner

    cleared, _observed = real_compare_exchange(
        cast(UnifiedFoodDatabase, winner),
        None,
    )
    assert cleared
    asyncio.run(winner.close())


@pytest.mark.asyncio
async def test_get_unified_food_db_loser_cleanup_cancellation_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _replace_registered_unified_food(None)
    close_started = asyncio.Event()
    winner = _RaceCandidate("winner")

    class _BlockingCandidate(_RaceCandidate):
        async def close(self) -> None:
            assert not unified_db_module._unified_db_instance_lock.locked()
            self.close_calls += 1
            close_started.set()
            await asyncio.Event().wait()

    candidate = _BlockingCandidate("loser")
    real_compare_exchange = unified_db_module._compare_exchange_unified_db_instance

    def _lose_publish(
        expected: UnifiedFoodDatabase | None,
        replacement: UnifiedFoodDatabase | None,
    ) -> tuple[bool, UnifiedFoodDatabase | None]:
        del replacement
        published, _observed = real_compare_exchange(
            expected,
            cast(UnifiedFoodDatabase, winner),
        )
        assert published
        return False, cast(UnifiedFoodDatabase, winner)

    class _BlockingDatabase:
        @staticmethod
        def __new__(_cls: type[object]) -> _BlockingCandidate:
            return candidate

        def __init__(self) -> None:
            pass

    monkeypatch.setattr(unified_db_module, "UnifiedFoodDatabase", _BlockingDatabase)
    monkeypatch.setattr(
        unified_db_module,
        "_compare_exchange_unified_db_instance",
        _lose_publish,
    )
    getter_task = asyncio.create_task(unified_db_module.get_unified_food_db())
    await close_started.wait()
    getter_task.cancel()
    with pytest.raises(
        asyncio.CancelledError,
        match=f"^{unified_db_module.UNIFIED_FOOD_CLEANUP_CANCELLED_MESSAGE}$",
    ) as cancellation_exc:
        await getter_task

    assert candidate.close_calls == 1
    assert cancellation_exc.value.__cause__ is None
    assert cancellation_exc.value.__context__ is None
    assert unified_db_module._read_unified_db_instance() is winner
    cleared, _observed = real_compare_exchange(
        cast(UnifiedFoodDatabase, winner),
        None,
    )
    assert cleared
    await winner.close()


@pytest.mark.asyncio
async def test_get_unified_food_db_partial_initialization_uses_cleanup_algebra(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _replace_registered_unified_food(None)
    candidate = _RaceCandidate("partial", RuntimeError("raw-cleanup-error"))

    def _fail_initialization(_candidate: object) -> None:
        raise RuntimeError("raw-initialization-error")

    class _PartialDatabase:
        @staticmethod
        def __new__(_cls: type[object]) -> _RaceCandidate:
            return candidate

        def __init__(self) -> None:
            _fail_initialization(self)

    monkeypatch.setattr(unified_db_module, "UnifiedFoodDatabase", _PartialDatabase)
    with pytest.raises(
        RuntimeError,
        match=f"^{unified_db_module.UNIFIED_FOOD_INITIALIZATION_ERROR_MESSAGE}$",
    ) as exc_info:
        await unified_db_module.get_unified_food_db()

    assert candidate.close_calls == 1
    assert unified_db_module._read_unified_db_instance() is None
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None
    assert "raw-" not in caplog.text
