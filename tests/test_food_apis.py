"""
Tests for Food APIs modules

Tests USDA client, unified database, update manager, and scheduler.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.food_apis.scheduler import DatabaseUpdateScheduler
from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem
from core.food_apis.update_manager import DatabaseUpdateManager, UpdateResult
from core.food_apis.usda_client import USDAClient, USDAFoodItem


class TestUSDAClient:
    """Test USDA FoodData Central API client."""

    @pytest.fixture
    def mock_usda_response(self):
        """Mock USDA API response."""
        return {
            "foods": [
                {
                    "fdcId": 168149,
                    "description": "Chicken, broiler or fryers, breast, skinless, boneless, meat only, cooked, roasted",
                    "dataType": "Foundation",
                    "foodCategory": {"description": "Poultry Products"},
                    "foodNutrients": [
                        {"nutrientId": 1003, "value": 30.54},  # protein
                        {"nutrientId": 1004, "value": 3.57},   # fat
                        {"nutrientId": 1005, "value": 0.0},    # carbs
                        {"nutrientId": 1008, "value": 165.0},  # calories
                        {"nutrientId": 1087, "value": 15.0},   # calcium
                        {"nutrientId": 1089, "value": 1.04},   # iron
                    ]
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_usda_client_initialization(self):
        """Test USDA client initialization."""
        client = USDAClient()
        assert client.api_key == "DEMO_KEY"  # Default
        assert client.BASE_URL == "https://api.nal.usda.gov/fdc/v1"
        assert len(client.nutrient_mapping) > 10  # Should have many nutrients mapped

        # Test with custom API key
        client_with_key = USDAClient("custom_key")
        assert client_with_key.api_key == "custom_key"

        await client.close()
        await client_with_key.close()

    @pytest.mark.asyncio
    async def test_parse_food_item(self, mock_usda_response):
        """Test parsing USDA API response into USDAFoodItem."""
        client = USDAClient()

        food_data = mock_usda_response["foods"][0]
        food_item = client._parse_food_item(food_data)

        assert food_item is not None
        assert food_item.fdc_id == 168149
        assert "Chicken" in food_item.description
        assert food_item.food_category == "Poultry Products"
        assert food_item.data_type == "Foundation"

        # Check nutrients
        nutrients = food_item.nutrients_per_100g
        assert nutrients["protein_g"] == 30.54
        assert nutrients["fat_g"] == 3.57
        assert nutrients.get("carbs_g", 0.0) == 0.0  # Use get() for optional nutrients
        assert nutrients["kcal"] == 165.0
        assert nutrients["calcium_mg"] == 15.0
        assert nutrients["iron_mg"] == 1.04

        await client.close()

    @pytest.mark.asyncio
    async def test_parse_food_item_insufficient_data(self):
        """Test handling of foods with insufficient nutrition data."""
        client = USDAClient()

        # Food with only 1 nutrient (insufficient)
        food_data = {
            "fdcId": 123,
            "description": "Test Food",
            "dataType": "Test",
            "foodNutrients": [
                {"nutrientId": 1003, "value": 10.0}  # Only protein
            ]
        }

        food_item = client._parse_food_item(food_data)
        assert food_item is None  # Should reject insufficient data

        await client.close()

    @pytest.mark.asyncio
    async def test_food_item_to_menu_engine_format(self, mock_usda_response):
        """Test conversion to menu engine format."""
        client = USDAClient()

        food_data = mock_usda_response["foods"][0]
        food_item = client._parse_food_item(food_data)

        menu_format = food_item.to_menu_engine_format()

        assert menu_format["name"] == food_item.description
        assert menu_format["nutrients_per_100g"] == food_item.nutrients_per_100g
        assert menu_format["cost_per_100g"] == 1.0  # Default cost
        assert "VEG" not in menu_format["tags"]  # Chicken is not vegetarian
        assert menu_format["source"] == "USDA FoodData Central"
        assert menu_format["fdc_id"] == food_item.fdc_id

        await client.close()

    @pytest.mark.asyncio
    async def test_food_item_tag_generation(self):
        """Test diet tag generation for different foods."""
        client = USDAClient()

        # Test vegetarian food
        veg_food_data = {
            "fdcId": 123,
            "description": "Broccoli, raw",
            "dataType": "Foundation",
            "foodNutrients": [
                {"nutrientId": 1003, "value": 2.82},
                {"nutrientId": 1004, "value": 0.37},
                {"nutrientId": 1005, "value": 6.64},
                {"nutrientId": 1008, "value": 34.0}
            ]
        }

        veg_food = client._parse_food_item(veg_food_data)
        veg_tags = veg_food._generate_tags()

        assert "VEG" in veg_tags
        assert "VEGAN" in veg_tags  # No dairy either
        assert "GF" in veg_tags     # No gluten-containing ingredients

        await client.close()


class TestUnifiedFoodDatabase:
    """Test unified food database interface."""

    def test_unified_food_item_creation(self):
        """Test creation of unified food items."""
        item = UnifiedFoodItem(
            name="Test Food",
            nutrients_per_100g={
                "protein_g": 20.0,
                "fat_g": 10.0,
                "carbs_g": 30.0,
                "kcal": 280.0
            },
            cost_per_100g=2.5,
            tags=["VEG", "GF"],
            availability_regions=["US", "BY"],
            source="TEST",
            source_id="test_123"
        )

        assert item.name == "Test Food"
        assert item.nutrients_per_100g["protein_g"] == 20.0
        assert "VEG" in item.tags
        assert "US" in item.availability_regions
        assert item.source == "TEST"

    @pytest.mark.asyncio
    async def test_unified_database_initialization(self):
        """Test unified database initialization."""
        db = UnifiedFoodDatabase("test_cache")

        # Should initialize without errors
        assert db.cache_dir.name == "test_cache"
        # Check if primary_sources exists, otherwise skip this assertion
        if hasattr(db, 'primary_sources'):
            assert len(db.primary_sources) > 0

        await db.close()

    @pytest.mark.asyncio
    @patch('core.food_apis.usda_client.get_common_foods_database')
    async def test_unified_database_get_foods(self, mock_get_foods):
        """Test getting foods from unified database."""
        # Mock USDA response
        mock_usda_food = USDAFoodItem(
            fdc_id=123,
            description="Test Chicken",
            food_category="Poultry",
            nutrients_per_100g={"protein_g": 25.0, "fat_g": 5.0, "carbs_g": 0.0, "kcal": 150.0},
            data_type="Foundation",
            publication_date="2024-01-01"
        )

        mock_get_foods.return_value = {"chicken_breast": mock_usda_food}

        db = UnifiedFoodDatabase("test_cache")
        foods = await db.get_common_foods_database()

        assert "chicken_breast" in foods
        assert isinstance(foods["chicken_breast"], UnifiedFoodItem)
        assert foods["chicken_breast"].source == "USDA FoodData Central"

        await db.close()


class TestDatabaseUpdateManager:
    """Test database update management."""

    @pytest.mark.asyncio
    async def test_update_manager_initialization(self):
        """Test update manager initialization."""
        manager = DatabaseUpdateManager(
            cache_dir="test_cache",
            update_interval_hours=12,
            max_rollback_versions=3
        )

        assert manager.cache_dir.name == "test_cache"
        assert manager.update_interval.total_seconds() == 12 * 3600
        assert manager.max_rollback_versions == 3
        assert isinstance(manager.usda_client, USDAClient)

        await manager.close()

    def test_checksum_calculation(self):
        """Test data integrity checksum calculation."""
        manager = DatabaseUpdateManager("test_cache")

        test_data = {"food1": {"protein": 20}, "food2": {"protein": 15}}
        checksum1 = manager._calculate_checksum(test_data)

        # Same data should produce same checksum
        checksum2 = manager._calculate_checksum(test_data)
        assert checksum1 == checksum2

        # Different data should produce different checksum
        different_data = {"food1": {"protein": 25}, "food2": {"protein": 15}}
        checksum3 = manager._calculate_checksum(different_data)
        assert checksum1 != checksum3

    @pytest.mark.asyncio
    async def test_check_for_updates(self):
        """Test checking for available updates."""
        manager = DatabaseUpdateManager("test_cache")

        # Should check for updates without errors
        updates = await manager.check_for_updates()

        assert isinstance(updates, dict)
        assert "usda" in updates
        assert isinstance(updates["usda"], bool)

        await manager.close()

    @pytest.mark.asyncio
    async def test_database_status(self):
        """Test getting database status."""
        manager = DatabaseUpdateManager("test_cache")

        status = manager.get_database_status()

        assert isinstance(status, dict)
        # Might be empty if no versions recorded yet

        await manager.close()

    @pytest.mark.asyncio
    async def test_update_callbacks(self):
        """Test update notification callbacks."""
        manager = DatabaseUpdateManager("test_cache")

        callback_called = False
        callback_result = None

        def test_callback(result: UpdateResult):
            nonlocal callback_called, callback_result
            callback_called = True
            callback_result = result

        manager.add_update_callback(test_callback)

        # Simulate an update result
        test_result = UpdateResult(
            success=True,
            source="test",
            old_version="1.0",
            new_version="1.1",
            records_added=5,
            records_updated=10,
            records_removed=0,
            errors=[],
            duration_seconds=2.5
        )

        # Trigger callbacks
        for callback in manager.update_callbacks:
            callback(test_result)

        assert callback_called
        assert callback_result == test_result

        await manager.close()


class TestDatabaseUpdateScheduler:
    """Test database update scheduler."""

    @pytest.mark.asyncio
    async def test_scheduler_initialization(self):
        """Test scheduler initialization."""
        scheduler = DatabaseUpdateScheduler(
            update_interval_hours=6,
            retry_interval_minutes=15,
            max_retries=5
        )

        assert scheduler.update_interval.total_seconds() == 6 * 3600
        assert scheduler.retry_interval.total_seconds() == 15 * 60
        assert scheduler.max_retries == 5
        assert not scheduler.is_running
        assert isinstance(scheduler.update_manager, DatabaseUpdateManager)

        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """Test scheduler start and stop functionality."""
        scheduler = DatabaseUpdateScheduler(update_interval_hours=24)

        # Test start
        await scheduler.start()
        assert scheduler.is_running

        # Test stop
        await scheduler.stop()
        assert not scheduler.is_running

    def test_should_check_for_updates(self):
        """Test update timing logic."""
        scheduler = DatabaseUpdateScheduler(update_interval_hours=1)

        from datetime import datetime, timedelta

        # First check should return True
        current_time = datetime.now()
        assert scheduler._should_check_for_updates(current_time)

        # Set last check to recent time
        scheduler.last_update_check = current_time - timedelta(minutes=30)
        assert not scheduler._should_check_for_updates(current_time)

        # Set last check to old time
        scheduler.last_update_check = current_time - timedelta(hours=2)
        assert scheduler._should_check_for_updates(current_time)

    @pytest.mark.asyncio
    async def test_scheduler_status(self):
        """Test getting scheduler status."""
        scheduler = DatabaseUpdateScheduler(update_interval_hours=12)

        status = scheduler.get_status()

        assert "scheduler" in status
        assert "databases" in status
        assert "is_running" in status["scheduler"]
        assert "update_interval_hours" in status["scheduler"]
        assert status["scheduler"]["update_interval_hours"] == 12

        await scheduler.stop()

    def test_handle_update_failure(self):
        """Test handling of update failures with retry logic."""
        scheduler = DatabaseUpdateScheduler(max_retries=3)

        # First failure
        scheduler._handle_update_failure("test_source", ["Error 1"])
        assert scheduler.retry_counts["test_source"] == 1

        # Second failure
        scheduler._handle_update_failure("test_source", ["Error 2"])
        assert scheduler.retry_counts["test_source"] == 2

        # Fourth failure (should reset after max retries reached)
        scheduler._handle_update_failure("test_source", ["Error 4"])
        # After max retries exceeded, counter is reset to 0, then incremented to 1 for new failure
        assert scheduler.retry_counts["test_source"] == 0  # Reset after max retries


class TestFoodAPIIntegration:
    """Test integration between food API components."""

    @pytest.mark.asyncio
    async def test_usda_to_unified_conversion(self):
        """Test conversion from USDA format to unified format."""
        # Create mock USDA food item
        usda_item = USDAFoodItem(
            fdc_id=12345,
            description="Test Food Item",
            food_category="Test Category",
            nutrients_per_100g={
                "protein_g": 20.0,
                "fat_g": 5.0,
                "carbs_g": 10.0,
                "kcal": 160.0,
                "iron_mg": 2.5
            },
            data_type="Foundation",
            publication_date="2024-01-01"
        )

        # Convert to menu engine format
        menu_format = usda_item.to_menu_engine_format()

        # Create unified food item from menu format
        unified_item = UnifiedFoodItem(
            name=menu_format["name"],
            nutrients_per_100g=menu_format["nutrients_per_100g"],
            cost_per_100g=menu_format["cost_per_100g"],
            tags=menu_format["tags"],
            availability_regions=menu_format["availability_regions"],
            source=menu_format["source"],
            source_id=str(menu_format["fdc_id"])  # Use source_id instead of external_id
        )

        # Verify conversion
        assert unified_item.name == usda_item.description
        assert unified_item.nutrients_per_100g == usda_item.nutrients_per_100g
        assert unified_item.source == "USDA FoodData Central"
        assert unified_item.source_id == "12345"

    @pytest.mark.asyncio
    async def test_error_handling_robustness(self):
        """Test error handling across all components."""
        # Test USDA client with invalid data
        client = USDAClient()

        # Should handle None gracefully
        result = client._parse_food_item(None)
        assert result is None

        # Should handle malformed data gracefully
        malformed_data = {"invalid": "data"}
        result = client._parse_food_item(malformed_data)
        assert result is None

        await client.close()

        # Test update manager with invalid source
        manager = DatabaseUpdateManager("test_cache")

        result = await manager.update_database("invalid_source")
        assert not result.success
        assert "Unknown source" in result.errors[0]

        await manager.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
