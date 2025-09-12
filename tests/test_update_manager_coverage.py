"""
Additional tests to improve coverage for update_manager.py to reach 97%+.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.food_apis.update_manager import (
    DatabaseUpdateManager,
    DatabaseVersion,
    UpdateResult,
)


class TestUpdateManagerCoverage:
    """Additional tests to improve coverage for DatabaseUpdateManager."""

    def test_load_versions_file_not_exists(self):
        """Test _load_versions with non-existent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use a subdirectory that doesn't exist yet
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir) / "nonexistent")
            # Should handle gracefully
            assert isinstance(manager.versions, dict)

    def test_load_versions_invalid_json(self):
        """Test _load_versions with invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Create an invalid versions file
            versions_file = manager.cache_dir / "database_versions.json"
            with open(versions_file, "w") as f:
                f.write("invalid json")

            # Should handle gracefully
            versions = manager._load_versions()
            assert isinstance(versions, dict)

    def test_save_versions_exception(self):
        """Test _save_versions with exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Mock json.dump to raise an exception
            with patch(
                "core.food_apis.update_manager.json.dump",
                side_effect=Exception("Test error"),
            ):
                # Should not crash
                manager._save_versions()

    @pytest.mark.asyncio
    async def test_check_for_updates_usda_exception(self):
        """Test check_for_updates with USDA exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Mock _check_usda_updates to raise an exception
            with patch.object(manager, "_check_usda_updates", side_effect=Exception("Test error")):
                updates = await manager.check_for_updates()
                # Should still return dict with USDA set to False
                assert isinstance(updates, dict)
                assert updates.get("usda") is False

    def test_check_usda_updates_no_current_version(self):
        """Test _check_usda_updates with no current version."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Clear any existing versions
            manager.versions.clear()

            # Should return True when no current version
            result = asyncio.run(manager._check_usda_updates())
            assert result is True

    def test_check_usda_updates_interval_not_passed(self):
        """Test _check_usda_updates when interval has not passed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Add a recent version
            recent_time = (datetime.now() - timedelta(hours=1)).isoformat()
            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated=recent_time,
                record_count=100,
                checksum="abc123",
                metadata={},
            )
            manager.versions["usda"] = version

            # Should return False when interval has not passed
            result = asyncio.run(manager._check_usda_updates())
            assert result is False

    @pytest.mark.asyncio
    async def test_update_database_unknown_source(self):
        """Test update_database with unknown source."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            result = await manager.update_database("unknown_source")

            assert result.success is False
            assert result.source == "unknown_source"
            assert "Unknown source" in result.errors[0]

    @pytest.mark.asyncio
    async def test_update_database_callback_exception(self):
        """Test update_database with callback exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Add a callback that raises an exception
            def bad_callback(result):
                raise Exception("Callback error")

            manager.add_update_callback(bad_callback)

            # Mock _update_usda_database to return a result
            mock_result = UpdateResult(
                success=True,
                source="usda",
                old_version=None,
                new_version="1.0",
                records_added=10,
                records_updated=0,
                records_removed=0,
                errors=[],
                duration_seconds=1.0,
            )
            with patch.object(manager, "_update_usda_database", return_value=mock_result):
                # Should not crash despite callback exception
                result = await manager.update_database("usda")
                assert result.success is True

    @pytest.mark.asyncio
    async def test_update_usda_database_create_backup_exception(self):
        """Test _update_usda_database with backup creation exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Add a version to trigger backup creation
            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated="2023-01-01T10:00:00",
                record_count=100,
                checksum="abc123",
                metadata={},
            )
            manager.versions["usda"] = version

            # Mock _create_backup to raise an exception
            with patch.object(manager, "_create_backup", side_effect=Exception("Backup error")):
                # Mock unified_db.get_common_foods_database
                with patch.object(
                    manager.unified_db,
                    "get_common_foods_database",
                    new_callable=AsyncMock,
                ) as mock_get_foods:
                    mock_get_foods.return_value = {"chicken": MagicMock()}

                    # Should handle the exception and still complete the update
                    result = await manager._update_usda_database()
                    # The result might be success=False due to the error, but should not crash
                    assert isinstance(result, UpdateResult)

    @pytest.mark.asyncio
    async def test_update_usda_database_load_backup_exception(self):
        """Test _update_usda_database with backup load exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Add a version
            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated="2023-01-01T10:00:00",
                record_count=100,
                checksum="old_checksum",
                metadata={},
            )
            manager.versions["usda"] = version

            # Mock unified_db.get_common_foods_database
            with patch.object(
                manager.unified_db, "get_common_foods_database", new_callable=AsyncMock
            ) as mock_get_foods:
                mock_get_foods.return_value = {"chicken": MagicMock()}

                # Mock _load_backup to raise an exception
                with patch.object(manager, "_load_backup", side_effect=Exception("Load error")):
                    # Should handle the exception and still complete the update
                    result = await manager._update_usda_database()
                    assert isinstance(result, UpdateResult)

    @pytest.mark.asyncio
    async def test_update_usda_database_exception(self):
        """Test _update_usda_database with general exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Mock unified_db.get_common_foods_database to raise an exception
            with patch.object(
                manager.unified_db,
                "get_common_foods_database",
                side_effect=Exception("Test error"),
            ):
                # Should handle the exception
                result = await manager._update_usda_database()
                assert result.success is False
                assert len(result.errors) > 0

    def test_validate_food_data_missing_fields(self):
        """Test _validate_food_data with missing required fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Create food item with missing name
            from core.food_apis.unified_db import UnifiedFoodItem

            invalid_food = UnifiedFoodItem(
                name="",  # Missing required field
                nutrients_per_100g={"protein_g": 20.0},
                cost_per_100g=1.0,
                tags=["test"],
                availability_regions=["US"],
                source="test",
                source_id="123",
            )

            foods = {"invalid": invalid_food}
            errors = asyncio.run(manager._validate_food_data(foods))

            assert len(errors) > 0
            assert "missing required fields" in errors[0]

    def test_validate_food_data_missing_nutrients(self):
        """Test _validate_food_data with missing nutrients."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Create food item with missing required nutrients
            from core.food_apis.unified_db import UnifiedFoodItem

            invalid_food = UnifiedFoodItem(
                name="Test Food",
                nutrients_per_100g={},  # Missing required nutrients
                cost_per_100g=1.0,
                tags=["test"],
                availability_regions=["US"],
                source="test",
                source_id="123",
            )

            foods = {"invalid": invalid_food}
            errors = asyncio.run(manager._validate_food_data(foods))

            assert len(errors) > 0
            assert "missing nutrients" in errors[0]

    def test_validate_food_data_negative_values(self):
        """Test _validate_food_data with negative nutrient values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Create food item with negative nutrient values
            from core.food_apis.unified_db import UnifiedFoodItem

            invalid_food = UnifiedFoodItem(
                name="Test Food",
                nutrients_per_100g={
                    "protein_g": -5.0,
                    "fat_g": 2.0,
                    "carbs_g": 3.0,
                },  # Negative value
                cost_per_100g=1.0,
                tags=["test"],
                availability_regions=["US"],
                source="test",
                source_id="123",
            )

            foods = {"invalid": invalid_food}
            errors = asyncio.run(manager._validate_food_data(foods))

            assert len(errors) > 0
            assert "negative" in str(errors[0]).lower()

    def test_validate_food_data_unrealistic_values(self):
        """Test _validate_food_data with unrealistic nutrient values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Create food item with unrealistic nutrient values
            from core.food_apis.unified_db import UnifiedFoodItem

            invalid_food = UnifiedFoodItem(
                name="Test Food",
                nutrients_per_100g={
                    "protein_g": 150.0,
                    "fat_g": 2.0,
                    "carbs_g": 3.0,
                },  # Unrealistic value (>100g per 100g)
                cost_per_100g=1.0,
                tags=["test"],
                availability_regions=["US"],
                source="test",
                source_id="123",
            )

            foods = {"invalid": invalid_food}
            errors = asyncio.run(manager._validate_food_data(foods))

            assert len(errors) > 0
            assert "unrealistic" in str(errors[0]).lower()

    @pytest.mark.asyncio
    async def test_create_backup_exception(self):
        """Test _create_backup with exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Mock unified_db.get_common_foods_database to raise an exception
            with patch.object(
                manager.unified_db,
                "get_common_foods_database",
                side_effect=Exception("Test error"),
            ):
                # Should handle the exception
                await manager._create_backup("usda", "1.0")

    @pytest.mark.asyncio
    async def test_load_backup(self):
        """Test _load_backup method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Create a backup file
            backup_data = {
                "chicken": {
                    "name": "Chicken Breast",
                    "nutrients_per_100g": {"protein_g": 31.0},
                    "cost_per_100g": 2.5,
                    "tags": ["protein"],
                    "availability_regions": ["US"],
                    "source": "USDA",
                    "source_id": "12345",
                    "category": "Meat",
                }
            }

            backup_file = manager.cache_dir / "usda_backup_1.0.json"
            with open(backup_file, "w") as f:
                json.dump(backup_data, f)

            # Should load the backup successfully
            foods = await manager._load_backup("usda", "1.0")
            assert isinstance(foods, dict)
            assert "chicken" in foods
            from core.food_apis.unified_db import UnifiedFoodItem

            assert isinstance(foods["chicken"], UnifiedFoodItem)

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_exception(self):
        """Test _cleanup_old_backups with exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Create a mock backup file
            backup_file = manager.cache_dir / "usda_backup_1.0.json"
            backup_file.touch()

            # Just test that the function doesn't crash when there are files to clean up
            # We'll mock the unlink method on one of the files to raise an exception
            with patch("pathlib.Path.unlink", side_effect=Exception("Test error")):
                # Should handle the exception gracefully
                await manager._cleanup_old_backups("usda")

    @pytest.mark.asyncio
    async def test_rollback_database_exception(self):
        """Test rollback_database with exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Add a version
            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated="2023-01-01T10:00:00",
                record_count=100,
                checksum="abc123",
                metadata={},
            )
            manager.versions["usda"] = version

            # Mock _load_backup to raise an exception
            with patch.object(manager, "_load_backup", side_effect=Exception("Test error")):
                # Should handle the exception
                success = await manager.rollback_database("usda", "1.0")
                assert success is False

    def test_add_update_callback(self):
        """Test add_update_callback method."""
        manager = DatabaseUpdateManager()

        def test_callback(result):
            pass

        # Should add the callback
        manager.add_update_callback(test_callback)
        assert len(manager.update_callbacks) == 1
        assert manager.update_callbacks[0] is test_callback

    def test_get_database_status(self):
        """Test get_database_status method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Add a version
            test_time = (datetime.now() - timedelta(hours=2)).isoformat()
            version = DatabaseVersion(
                source="usda",
                version="1.0",
                last_updated=test_time,
                record_count=100,
                checksum="abc123def456",
                metadata={"test": "data"},
            )
            manager.versions["usda"] = version

            status = manager.get_database_status()

            assert "usda" in status
            db_status = status["usda"]
            assert db_status["version"] == "1.0"
            assert db_status["record_count"] == 100
            assert db_status["checksum"] == "abc123de..."
            assert db_status["metadata"]["test"] == "data"

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Mock clients to track close calls
            manager.usda_client.close = AsyncMock()
            manager.unified_db.close = AsyncMock()

            # Should close both clients
            await manager.close()
            manager.usda_client.close.assert_called_once()
            manager.unified_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_scheduled_update(self):
        """Test run_scheduled_update convenience function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=Path(temp_dir))

            # Mock check_for_updates to return available updates
            manager.check_for_updates = AsyncMock(return_value={"usda": True})

            # Mock update_database to return a result
            mock_result = MagicMock()
            mock_result.success = True
            manager.update_database = AsyncMock(return_value=mock_result)

            # Should run updates for available sources
            from core.food_apis.update_manager import run_scheduled_update

            results = await run_scheduled_update(manager)

            assert "usda" in results
            assert results["usda"].success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
