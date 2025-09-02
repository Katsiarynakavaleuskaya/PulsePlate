"""
Basic tests to improve coverage for food_apis modules.
These tests focus on exercising the main functions to quickly improve coverage percentages.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Test unified_db module
class TestUnifiedFoodDatabase:
    """Basic tests for UnifiedFoodDatabase to improve coverage."""

    @patch('core.food_apis.unified_db.USDAClient')
    def test_unified_food_database_init(self, mock_usda_class):
        """Test basic initialization."""
        from core.food_apis.unified_db import UnifiedFoodDatabase

        mock_usda_instance = MagicMock()
        mock_usda_class.return_value = mock_usda_instance

        with tempfile.TemporaryDirectory() as temp_dir:
            db = UnifiedFoodDatabase(cache_dir=temp_dir)
            assert db.cache_dir.exists()
            assert isinstance(db._memory_cache, dict)

    @patch('core.food_apis.unified_db.USDAClient')
    def test_unified_food_database_cache_operations(self, mock_usda_class):
        """Test cache loading and saving."""
        from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

        mock_usda_instance = MagicMock()
        mock_usda_class.return_value = mock_usda_instance

        with tempfile.TemporaryDirectory() as temp_dir:
            db = UnifiedFoodDatabase(cache_dir=temp_dir)

            # Test saving cache
            test_item = UnifiedFoodItem(
                name="Test Food",
                nutrients_per_100g={"protein_g": 20},
                cost_per_100g=1.0,
                tags=["test"],
                availability_regions=["US"],
                source="test",
                source_id="123"
            )
            db._memory_cache["test"] = test_item
            db._save_cache()

            # Test loading cache
            db2 = UnifiedFoodDatabase(cache_dir=temp_dir)
            assert "test" in db2._memory_cache

    @pytest.mark.asyncio
    @patch('core.food_apis.unified_db.USDAClient')
    async def test_search_food_fallback(self, mock_usda_class):
        """Test food search with fallback."""
        from core.food_apis.unified_db import UnifiedFoodDatabase

        # Mock USDA client to return empty results
        mock_usda_instance = AsyncMock()
        mock_usda_instance.search_foods.return_value = []
        mock_usda_class.return_value = mock_usda_instance

        with tempfile.TemporaryDirectory() as temp_dir:
            db = UnifiedFoodDatabase(cache_dir=temp_dir)
            results = await db.search_food("chicken")

            # Should return some results (fallback data or cached)
            assert isinstance(results, list)


# Test update_manager module
class TestDatabaseUpdateManager:
    """Basic tests for DatabaseUpdateManager to improve coverage."""

    def test_database_update_manager_init(self):
        """Test basic initialization."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)
            assert manager.cache_dir.exists()
            assert isinstance(manager.versions, dict)

    def test_database_version_operations(self):
        """Test database version tracking."""
        from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Test creating version
            version = DatabaseVersion(
                source="test",
                version="1.0",
                last_updated=datetime.now().isoformat(),
                record_count=100,
                checksum="abc123",
                metadata={}
            )

            manager.versions["test"] = version
            manager._save_versions()

            # Test loading versions
            manager2 = DatabaseUpdateManager(cache_dir=temp_dir)
            assert "test" in manager2.versions

    @pytest.mark.asyncio
    async def test_check_for_updates_basic(self):
        """Test basic update checking."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Mock the USDA check to avoid real API calls
            with patch.object(manager, '_check_usda_updates', return_value=True):
                updates = await manager.check_for_updates()
                assert isinstance(updates, dict)
                assert "usda" in updates

    def test_calculate_checksum(self):
        """Test checksum calculation."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            test_data = {"key": "value", "number": 123}
            checksum = manager._calculate_checksum(test_data)

            assert isinstance(checksum, str)
            assert len(checksum) == 64  # SHA256 hex digest


# Test scheduler module
class TestDatabaseUpdateScheduler:
    """Basic tests for DatabaseUpdateScheduler to improve coverage."""

    def test_database_update_scheduler_init(self):
        """Test basic initialization."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler

        scheduler = DatabaseUpdateScheduler(update_interval_hours=1)
        assert scheduler.update_interval.total_seconds() == 3600
        assert scheduler.is_running is False
        assert scheduler._update_task is None

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """Test starting and stopping scheduler."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler

        scheduler = DatabaseUpdateScheduler(update_interval_hours=1)

        # Mock the update manager
        scheduler.update_manager = AsyncMock()

        # Test starting
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = AsyncMock()
            mock_create_task.return_value = mock_task

            await scheduler.start()
            assert scheduler.is_running is True

            # Test stopping
            await scheduler.stop()
            assert scheduler.is_running is False

    def test_should_check_for_updates(self):
        """Test update timing logic."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler

        scheduler = DatabaseUpdateScheduler(update_interval_hours=1)

        # First check should return True
        current_time = datetime.now()
        assert scheduler._should_check_for_updates(current_time) is True

        # Set last check time
        scheduler.last_update_check = current_time

        # Immediate second check should return False
        assert scheduler._should_check_for_updates(current_time) is False

        # Check after interval should return True
        future_time = current_time + timedelta(hours=2)
        assert scheduler._should_check_for_updates(future_time) is True


# Test module-level functions
class TestModuleFunctions:
    """Test standalone module functions to improve coverage."""

    @pytest.mark.asyncio
    async def test_get_unified_food_db(self):
        """Test the get_unified_food_db function."""
        with patch('core.food_apis.unified_db.USDAClient'):
            from core.food_apis.unified_db import get_unified_food_db

            db = await get_unified_food_db()
            assert db is not None

    def test_unified_food_item_conversion(self):
        """Test UnifiedFoodItem conversions."""
        from core.food_apis.unified_db import UnifiedFoodItem

        item = UnifiedFoodItem(
            name="Test Food",
            nutrients_per_100g={"protein_g": 20.0, "fat_g": 5.0},
            cost_per_100g=2.5,
            tags=["test", "protein"],
            availability_regions=["US", "CA"],
            source="test_source",
            source_id="test_123",
            category="Test Category"
        )

        # Test conversion to menu engine format
        menu_format = item.to_menu_engine_format()

        assert menu_format["name"] == "Test Food"
        assert menu_format["nutrients_per_100g"]["protein_g"] == 20.0
        assert menu_format["cost_per_100g"] == 2.5
        assert "test" in menu_format["tags"]
        assert "US" in menu_format["availability_regions"]
        assert menu_format["source"] == "test_source"
        assert menu_format["source_id"] == "test_123"
        assert menu_format["category"] == "Test Category"

    def test_update_result_creation(self):
        """Test UpdateResult creation."""
        from core.food_apis.update_manager import UpdateResult

        result = UpdateResult(
            success=True,
            source="usda",
            old_version="1.0",
            new_version="1.1",
            records_added=50,
            records_updated=25,
            records_removed=5,
            errors=[],
            duration_seconds=45.5
        )

        assert result.success is True
        assert result.source == "usda"
        assert result.records_added == 50
        assert result.duration_seconds == 45.5

    @pytest.mark.asyncio
    async def test_run_source_update_success(self):
        """Test successful source update."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler
        from core.food_apis.update_manager import UpdateResult

        scheduler = DatabaseUpdateScheduler()

        # Mock successful update
        mock_result = UpdateResult(
            success=True, source="test", old_version=None, new_version="1.0",
            records_added=10, records_updated=0, records_removed=0,
            errors=[], duration_seconds=1.0
        )

        scheduler.update_manager = AsyncMock()
        scheduler.update_manager.update_database.return_value = mock_result

        await scheduler._run_source_update("test")

        # Should reset retry count on success
        assert scheduler.retry_counts.get("test", 0) == 0

    @pytest.mark.asyncio
    async def test_run_source_update_failure(self):
        """Test failed source update."""
        from core.food_apis.scheduler import DatabaseUpdateScheduler
        from core.food_apis.update_manager import UpdateResult

        scheduler = DatabaseUpdateScheduler(max_retries=2)

        # Mock failed update
        mock_result = UpdateResult(
            success=False, source="test", old_version=None, new_version=None,
            records_added=0, records_updated=0, records_removed=0,
            errors=["Test error"], duration_seconds=1.0
        )

        scheduler.update_manager = AsyncMock()
        scheduler.update_manager.update_database.return_value = mock_result

        await scheduler._run_source_update("test")

        # Should increment retry count
        assert scheduler.retry_counts.get("test", 0) == 1
