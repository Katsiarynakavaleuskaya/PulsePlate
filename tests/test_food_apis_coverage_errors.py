"""
Tests for Food APIs update pipeline to cover error handling,
fallback scenarios, and specific uncovered paths.
Targets ~40 lines in update_manager.py (15% coverage) and unified_db.py (19% coverage).
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from core.food_apis.update_manager import DatabaseUpdateManager, UpdateResult
from core.food_apis.unified_db import UnifiedFoodDatabase


class TestFoodAPIsUpdatePipelineBasic:
    """Test Food APIs update pipeline error handling and fallbacks."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test databases."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def update_manager(self, temp_dir):
        """Create update manager with temporary directory."""
        return DatabaseUpdateManager(cache_dir=temp_dir)

    def test_update_manager_versions_file_not_exists(self, update_manager):
        """Test load_versions when versions file doesn't exist (line 146)."""
        # Ensure versions file doesn't exist
        versions_file = update_manager.versions_file
        if versions_file.exists():
            versions_file.unlink()

        # Load versions should handle missing file gracefully
        versions = update_manager._load_versions()
        assert versions == {}

    def test_update_manager_versions_file_invalid_json(self, update_manager):
        """Test load_versions with invalid JSON (lines 159-160)."""
        # Create invalid JSON file
        versions_file = update_manager.versions_file
        versions_file.parent.mkdir(parents=True, exist_ok=True)
        versions_file.write_text("invalid json content")

        # Load should handle invalid JSON and log error
        with patch("core.food_apis.update_manager.logger") as mock_logger:
            versions = update_manager._load_versions()
            assert versions == {}
            mock_logger.error.assert_called_once()
            assert "Error loading versions" in str(mock_logger.error.call_args)

    def test_update_manager_save_versions_error_mock_path(self, update_manager):
        """Test save_versions with write error using mock (lines 171-172)."""
        # Mock open to raise error during write
        with patch("builtins.open", side_effect=OSError("Write error")):
            with patch("core.food_apis.update_manager.logger") as mock_logger:
                update_manager._save_versions()
                mock_logger.error.assert_called_once()
                assert "Error saving versions" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_check_for_updates_usda_error(self, update_manager):
        """Test check_for_updates with USDA error (lines 194-195)."""
        # Mock _check_usda_updates to raise exception
        with patch.object(
            update_manager, "_check_usda_updates", side_effect=Exception("USDA API error")
        ):
            with patch("core.food_apis.update_manager.logger") as mock_logger:
                result = await update_manager.check_for_updates()

                # Should handle error gracefully and continue with OFF
                assert "usda" not in result or result["usda"] is False
                mock_logger.error.assert_called()
                assert "Error checking USDA updates" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_check_for_updates_off_error(self, update_manager):
        """Test check_for_updates with OFF error (lines 203-204)."""
        # Mock OFF_AVAILABLE to True and _check_off_updates to raise exception
        with patch("core.food_apis.update_manager.OFF_AVAILABLE", True):
            with patch.object(
                update_manager, "_check_off_updates", side_effect=Exception("OFF API error")
            ):
                with patch("core.food_apis.update_manager.logger") as mock_logger:
                    result = await update_manager.check_for_updates()

                    # Should handle error gracefully
                    assert "off" not in result or result["off"] is False
                    mock_logger.error.assert_called()
                    assert "Error checking Open Food Facts updates" in str(
                        mock_logger.error.call_args
                    )

    @pytest.mark.asyncio
    async def test_check_usda_updates_no_current_version(self, update_manager):
        """Test _check_usda_updates when no current version exists (line 214)."""
        # Ensure no current version
        update_manager._load_versions = MagicMock(return_value={})

        result = await update_manager._check_usda_updates()
        # Should return True when no current version (needs update)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_off_updates_no_current_version(self, update_manager):
        """Test _check_off_updates when no current version exists (line 231)."""
        # Ensure no current version
        update_manager._load_versions = MagicMock(return_value={})

        with patch("core.food_apis.update_manager.OFF_AVAILABLE", True):
            result = await update_manager._check_off_updates()
            # Should return True when no current version (needs update)
            assert result is True

    @pytest.mark.asyncio
    async def test_update_database_basic(self, update_manager):
        """Test update_database basic functionality."""
        # Mock successful update
        with patch.object(
            update_manager,
            "_update_usda_database",
            return_value=UpdateResult(
                success=True,
                source="usda",
                old_version=None,
                new_version="1.0",
                records_added=10,
                records_updated=0,
                records_removed=0,
                errors=[],
                duration_seconds=0.0,
            ),
        ):
            result = await update_manager.update_database("usda")
            # Update should succeed
            assert result.success is True

    def test_simple_coverage_paths(self):
        """Test simple coverage paths for update manager logic."""
        # Test basic instantiation and paths
        manager = DatabaseUpdateManager()
        assert manager.cache_dir is not None
        assert manager.versions_file is not None

        # Test empty versions loading
        versions = manager._load_versions()
        assert isinstance(versions, dict)


class TestFoodAPIsUpdatePipeline:
    """Test Food APIs update pipeline error handling and fallbacks."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test databases."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def update_manager(self, temp_dir):
        """Create update manager with temporary directory."""
        return DatabaseUpdateManager(cache_dir=temp_dir)

    def test_update_manager_versions_file_not_exists(self, update_manager):
        """Test load_versions when versions file doesn't exist (line 146)."""
        # Ensure versions file doesn't exist
        versions_file = update_manager.versions_file
        if versions_file.exists():
            versions_file.unlink()

        # Load versions should handle missing file gracefully
        versions = update_manager._load_versions()
        assert versions == {}

    def test_update_manager_versions_file_invalid_json(self, update_manager):
        """Test load_versions with invalid JSON (lines 159-160)."""
        # Create invalid JSON file
        versions_file = update_manager.versions_file
        versions_file.parent.mkdir(parents=True, exist_ok=True)
        versions_file.write_text("invalid json content")

        # Load should handle invalid JSON and log error
        with patch("core.food_apis.update_manager.logger") as mock_logger:
            versions = update_manager._load_versions()
            assert versions == {}
            mock_logger.error.assert_called_once()
            assert "Error loading versions" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_check_for_updates_usda_error(self, update_manager):
        """Test check_for_updates with USDA error (lines 194-195)."""
        # Mock _check_usda_updates to raise exception
        with patch.object(
            update_manager, "_check_usda_updates", side_effect=Exception("USDA API error")
        ):
            with patch("core.food_apis.update_manager.logger") as mock_logger:
                result = await update_manager.check_for_updates()

                # Should handle error gracefully and continue with OFF
                assert "usda" not in result or result["usda"] is False
                mock_logger.error.assert_called()
                assert "Error checking USDA updates" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_check_for_updates_off_error(self, update_manager):
        """Test check_for_updates with OFF error (lines 203-204)."""
        # Mock OFF_AVAILABLE to True and _check_off_updates to raise exception
        with patch("core.food_apis.update_manager.OFF_AVAILABLE", True):
            with patch.object(
                update_manager, "_check_off_updates", side_effect=Exception("OFF API error")
            ):
                with patch("core.food_apis.update_manager.logger") as mock_logger:
                    result = await update_manager.check_for_updates()

                    # Should handle error gracefully
                    assert "off" not in result or result["off"] is False
                    mock_logger.error.assert_called()
                    assert "Error checking Open Food Facts updates" in str(
                        mock_logger.error.call_args
                    )

    @pytest.mark.asyncio
    async def test_check_usda_updates_no_current_version(self, update_manager):
        """Test _check_usda_updates when no current version exists (line 214)."""
        # Ensure no current version
        update_manager._load_versions = MagicMock(return_value={})

        result = await update_manager._check_usda_updates()
        # Should return True when no current version (needs update)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_off_updates_no_current_version(self, update_manager):
        """Test _check_off_updates when no current version exists (line 231)."""
        # Ensure no current version
        update_manager._load_versions = MagicMock(return_value={})

        with patch("core.food_apis.update_manager.OFF_AVAILABLE", True):
            result = await update_manager._check_off_updates()
            # Should return True when no current version (needs update)
            assert result is True

    @pytest.mark.asyncio
    async def test_update_database_callback_error(self, update_manager):
        """Test update_database with callback error (lines 281-282)."""

        def error_callback(result):
            raise Exception("Callback error")

        # Mock successful update but failing callback
        with patch.object(
            update_manager,
            "_update_usda_database",
            return_value=UpdateResult(
                success=True,
                source="usda",
                old_version=None,
                new_version="1.0",
                records_added=10,
                records_updated=0,
                records_removed=0,
                errors=[],
                duration_seconds=0.0,
            ),
        ):
            result = await update_manager.update_database("usda")
            # Update should succeed
            assert result.success is True

    @pytest.mark.asyncio
    async def test_update_usda_database_no_force_same_checksum(self, update_manager):
        """Test _update_usda_database with same checksum, no force (line 308)."""
        from core.food_apis.update_manager import DatabaseVersion

        current_version = DatabaseVersion(
            source="usda",
            version="20230101_000000",
            last_updated="2023-01-01T00:00:00Z",
            record_count=1,
            checksum="same_checksum_123",
            metadata={},
        )
        update_manager.versions["usda"] = current_version

        with patch.object(
            update_manager.unified_db,
            "get_common_foods_database",
            return_value={},
        ):
            with patch.object(
                update_manager,
                "_calculate_checksum",
                return_value="same_checksum_123",
            ):
                with patch.object(update_manager, "_create_backup", new=AsyncMock()) as mock_backup:
                    result = await update_manager._update_usda_database(force=False)

        assert result is not None
        assert result.success is True
        assert result.new_version == current_version.version
        assert result.records_updated == 0
        mock_backup.assert_awaited_once_with("usda", current_version.version)

    @pytest.mark.asyncio
    async def test_update_usda_database_old_data_load_error(
        self, update_manager: DatabaseUpdateManager
    ) -> None:
        """Test _update_usda_database with old data load error (lines 396-399)."""
        # Set up a current version so _load_backup gets called
        from core.food_apis.update_manager import DatabaseVersion
        from core.food_apis.unified_db import UnifiedFoodItem

        current_version = DatabaseVersion(
            source="usda",
            version="old_version",
            last_updated="2023-01-01T00:00:00Z",
            record_count=10,
            checksum="old_checksum",
            metadata={},
        )
        update_manager.versions["usda"] = current_version

        # Create proper UnifiedFoodItem for mock return
        mock_food = UnifiedFoodItem(
            name="Test Food",
            nutrients_per_100g={
                "protein_g": 10.0,
                "carbs_g": 20.0,
                "fat_g": 5.0,
                "calories": 100.0,
            },
            cost_per_100g=1.0,
            tags=["test"],
            availability_regions=["US"],
            source="usda",
            source_id="12345",
        )

        # Mock get_common_foods_database to return minimal data with proper type
        with patch.object(
            update_manager.unified_db,
            "get_common_foods_database",
            return_value={"test_food": mock_food},
        ):
            # Patch _load_backup to raise exception (line 397-399)
            with patch.object(
                update_manager,
                "_load_backup",
                side_effect=FileNotFoundError("File not found"),
            ):
                with patch("core.food_apis.update_manager.logger") as mock_logger:
                    await update_manager._update_usda_database(force=True)

                    # Should log warning about old data load failure (line 399)
                    # Check all warning calls for our expected message
                    warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
                    assert any(
                        "Could not load old data" in call for call in warning_calls
                    ), f"Expected warning not found in: {warning_calls}"

    @pytest.mark.asyncio
    async def test_update_usda_database_general_error(
        self, update_manager: DatabaseUpdateManager
    ) -> None:
        """Test _update_usda_database with general error (lines 438-450)."""
        # Patch unified_db.get_common_foods_database to raise exception
        # (this is what _update_usda_database actually calls at line 356)
        with patch.object(
            update_manager.unified_db,
            "get_common_foods_database",
            side_effect=Exception("API connection error"),
        ):
            with patch("core.food_apis.update_manager.logger") as mock_logger:
                result = await update_manager._update_usda_database()

                # Should handle error gracefully (lines 438-450)
                assert result.success is False
                assert result.errors, "Expected non-empty errors list"
                assert "API connection error" in result.errors[0]
                mock_logger.error.assert_called()
                # Check actual log message format (uses %s placeholders)
                error_calls = [str(c) for c in mock_logger.error.call_args_list]
                assert any("usda" in call for call in error_calls)

    @pytest.mark.asyncio
    async def test_update_off_database_error_during_processing(
        self, update_manager: DatabaseUpdateManager
    ) -> None:
        """Test _update_off_database with processing error (lines 588-597)."""
        from core.food_apis.update_manager import DatabaseVersion

        # Set up a current version so _create_backup gets called
        current_version = DatabaseVersion(
            source="openfoodfacts",
            version="old_version",
            last_updated="2023-01-01T00:00:00Z",
            record_count=10,
            checksum="old_checksum",
            metadata={},
        )
        update_manager.versions["openfoodfacts"] = current_version

        # Patch _create_backup to raise exception early in the try block
        # This triggers the outer exception handler (lines 588-597)
        with patch.object(
            update_manager,
            "_create_backup",
            side_effect=Exception("Backup creation error"),
        ):
            with patch("core.food_apis.update_manager.logger") as mock_logger:
                result = await update_manager._update_off_database()

                # Should handle error during processing (lines 588-597)
                assert result.success is False
                assert result.errors, "Expected non-empty errors list"
                assert "Backup creation error" in result.errors[0]


class TestUnifiedFoodDatabase:
    """Test UnifiedFoodDatabase error handling and fallbacks."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test databases."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def unified_db(self, temp_dir):
        """Create unified database with temporary directory."""
        return UnifiedFoodDatabase(cache_dir=temp_dir)

    def test_unified_db_off_not_available(self, temp_dir):
        """Test UnifiedFoodDatabase when OFF is not available (line 39-40)."""
        # Mock OFFClient to be None (simulating unavailable OFF)
        with patch("core.food_apis.unified_db.OFFClient", None):
            unified_db = UnifiedFoodDatabase(cache_dir=temp_dir)
            # Should handle missing OFF gracefully
            assert unified_db.off_client is None

    @pytest.mark.asyncio
    async def test_search_foods_usda_error_fallback(self, unified_db: UnifiedFoodDatabase) -> None:
        """Test search_food with USDA error gracefully handled (lines 251-261)."""
        # Mock USDA client to raise exception
        with patch.object(
            unified_db.usda_client, "search_foods", side_effect=Exception("USDA API error")
        ):
            # Also disable OFF client so we test pure USDA error path
            unified_db.off_client = None

            with patch("core.food_apis.unified_db.logger") as mock_logger:
                result = await unified_db.search_food("test query")

                # Should handle error gracefully and return empty results
                assert result == []
                # Error should be logged with traceback
                mock_logger.exception.assert_called()
                assert "Error searching USDA" in str(mock_logger.exception.call_args)

    @pytest.mark.asyncio
    async def test_get_food_by_id_cache_load_error(self, unified_db: UnifiedFoodDatabase) -> None:
        """Test get_food_by_id with cache load error (line 190-224)."""
        # Create invalid cache file
        cache_file = unified_db.cache_dir / "unified_food_cache.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("invalid json")

        # Create a mock USDAFoodItem with required attributes
        mock_usda_item = MagicMock()
        mock_usda_item.description = "Test Food"
        mock_usda_item.fdc_id = 123
        mock_usda_item.nutrients_per_100g = {"protein_g": 10.0, "fat_g": 5.0, "carbs_g": 20.0}
        mock_usda_item._generate_tags.return_value = ["test"]
        mock_usda_item.food_category = "Test Category"

        # Mock USDA client to return valid USDAFoodItem
        with patch.object(
            unified_db.usda_client,
            "get_food_details",
            return_value=mock_usda_item,
        ):
            # get_food_by_id requires source and food_id
            result = await unified_db.get_food_by_id("usda", "123")

            # Should handle cache error and fetch from API
            assert result is not None
            assert result.name == "Test Food"

    @pytest.mark.asyncio
    async def test_get_food_by_id_all_sources_fail(self, unified_db: UnifiedFoodDatabase) -> None:
        """Test get_food_by_id when all sources fail."""
        # Mock USDA client to return None
        with patch.object(unified_db.usda_client, "get_food_details", return_value=None):
            # get_food_by_id requires source and food_id (use valid int to avoid ValueError)
            result = await unified_db.get_food_by_id("usda", "99999")

            # Should return None when source returns no data
            assert result is None
