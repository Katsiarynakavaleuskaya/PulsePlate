"""
Simple tests for Food APIs update pipeline handling.
Target uncovered lines in update_manager.py and unified_db.py.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from core.food_apis.update_manager import DatabaseUpdateManager, UpdateResult


class TestFoodAPIsSimple:
    """Simple tests for Food APIs error paths."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create update manager."""
        return DatabaseUpdateManager(cache_dir=temp_dir)

    def test_versions_file_not_exists(self, manager):
        """Test load_versions when file doesn't exist (line 146)."""
        if manager.versions_file.exists():
            manager.versions_file.unlink()

        versions = manager._load_versions()
        assert versions == {}

    def test_versions_file_invalid_json(self, manager):
        """Test load_versions with invalid JSON (lines 159-160)."""
        manager.versions_file.parent.mkdir(parents=True, exist_ok=True)
        manager.versions_file.write_text("invalid json")

        with patch("core.food_apis.update_manager.logger") as mock_logger:
            versions = manager._load_versions()
            assert versions == {}
            mock_logger.error.assert_called_once()

    def test_save_versions_error(self, manager):
        """Test save_versions with write error (lines 171-172)."""
        with patch("builtins.open", side_effect=OSError("Write error")):
            with patch("core.food_apis.update_manager.logger") as mock_logger:
                manager._save_versions()
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_usda_updates_no_version(self, manager):
        """Test _check_usda_updates when no current version (line 214)."""
        manager._load_versions = MagicMock(return_value={})
        result = await manager._check_usda_updates()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_off_updates_no_version(self, manager):
        """Test _check_off_updates when no current version (line 231)."""
        manager._load_versions = MagicMock(return_value={})
        with patch("core.food_apis.update_manager.OFF_AVAILABLE", True):
            result = await manager._check_off_updates()
            assert result is True

    @pytest.mark.asyncio
    async def test_check_for_updates_usda_error(self, manager):
        """Test check_for_updates with USDA error (lines 194-195)."""
        with patch.object(manager, "_check_usda_updates", side_effect=Exception("USDA error")):
            with patch("core.food_apis.update_manager.logger") as mock_logger:
                result = await manager.check_for_updates()
                assert "usda" not in result or result["usda"] is False
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_check_for_updates_off_error(self, manager):
        """Test check_for_updates with OFF error (lines 203-204)."""
        with patch("core.food_apis.update_manager.OFF_AVAILABLE", True):
            with patch.object(manager, "_check_off_updates", side_effect=Exception("OFF error")):
                with patch("core.food_apis.update_manager.logger") as mock_logger:
                    result = await manager.check_for_updates()
                    assert "off" not in result or result["off"] is False
                    mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_update_database_callback_error(self, manager):
        """Test update_database with callback error (lines 281-282)."""

        def error_callback(result):
            raise Exception("Callback error")

        # Add the error callback
        manager.add_update_callback(error_callback)

        update_result = UpdateResult(
            success=True,
            source="usda",
            old_version=None,
            new_version="1.0",
            records_added=10,
            records_updated=0,
            records_removed=0,
            errors=[],
            duration_seconds=0.0,
        )

        with patch.object(manager, "_update_usda_database", return_value=update_result):
            with patch("core.food_apis.update_manager.logger") as mock_logger:
                result = await manager.update_database("usda")
                assert result.success is True
                mock_logger.error.assert_called()
