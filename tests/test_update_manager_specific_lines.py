"""
Targeted tests for specific uncovered lines to reach 97% coverage.
"""

import json
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from contextlib import suppress

from core.food_apis.update_manager import (
    DatabaseUpdateManager,
    DatabaseVersion,
    UpdateResult,
)


class TestUpdateManagerSpecificLines:
    """Tests targeting specific uncovered lines."""

    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def manager(self, temp_dir: Path) -> DatabaseUpdateManager:
        """Create DatabaseUpdateManager instance."""
        return DatabaseUpdateManager(cache_dir=temp_dir, update_interval_hours=24)

    @pytest.mark.asyncio
    async def test_backup_load_exception_logging_lines_329_330(self, manager) -> None:
        """Test backup load exception logging covering lines 329-330."""
        # Add existing version
        manager.versions["usda"] = DatabaseVersion(
            source="usda",
            version="1.0.0",
            last_updated="2023-01-01T00:00:00Z",
            record_count=1,
            checksum="abc123",
            metadata={"test": "data"},
        )

        # Mock _load_backup to raise exception
        mock_food = MagicMock(
            name="Apple",
            nutrients_per_100g={
                "calories": 100,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 25.0,
            },
            cost_per_100g=0.5,
            tags=["fruit"],
            availability_regions=["US"],
            source="usda",
            source_id="1",
        )

        with patch.object(manager, "_load_backup", side_effect=Exception("Backup file corrupted")):
            with patch.object(manager, "usda_client") as mock_usda:
                with patch.object(
                    manager.unified_db,
                    "get_common_foods_database",
                    new=AsyncMock(return_value={"apple": mock_food}),
                ):
                    mock_usda.fetch_all_foods = AsyncMock(return_value=[])

                    # Execute update - should trigger exception logging
                    result = await manager._update_usda_database(force=True)

                    # Should succeed despite backup load exception
                    assert isinstance(result, UpdateResult)
                    assert result.success is True
                    assert result.source == "usda"

    @pytest.mark.asyncio
    async def test_backup_load_exception_logging_lines_474_475(self, manager) -> None:
        """Test OFF backup load exception logging covering lines 474-475."""
        # Add existing version
        manager.versions["openfoodfacts"] = DatabaseVersion(
            source="openfoodfacts",
            version="1.0.0",
            last_updated="2023-01-01T00:00:00Z",
            record_count=1,
            checksum="abc123",
            metadata={"test": "data"},
        )

        mock_food = MagicMock(
            name="Apple",
            nutrients_per_100g={
                "calories": 100,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 25.0,
            },
            cost_per_100g=0.5,
            tags=["fruit"],
            availability_regions=["US"],
            source="openfoodfacts",
            source_id="1",
        )

        # Mock _load_backup to raise exception
        with patch.object(manager, "_load_backup", side_effect=Exception("Backup file corrupted")):
            with patch.object(manager, "off_client") as mock_off:
                with patch.object(
                    manager.unified_db,
                    "get_common_foods_database",
                    new=AsyncMock(return_value={"apple": mock_food}),
                ):
                    mock_off.search_products = AsyncMock(return_value=[])

                    # Execute update - should trigger exception logging
                    result = await manager._update_off_database(force=True)

                    # Should succeed despite backup load exception
                    assert isinstance(result, UpdateResult)
                    assert result.success is True
                    assert result.source == "openfoodfacts"

    @pytest.mark.asyncio
    async def test_usda_exception_logging_lines_369_371(self, manager) -> None:
        """Test USDA exception logging covering lines 369-371."""
        # Raise from awaited unified_db method to trigger top-level exception handler
        with patch.object(
            manager.unified_db,
            "get_common_foods_database",
            new=AsyncMock(side_effect=Exception("Critical database error")),
        ):
            result = await manager._update_usda_database(force=True)

            # Verify exception handling covers lines 369-371
            assert isinstance(result, UpdateResult)
            assert result.source == "usda"

    @pytest.mark.asyncio
    async def test_off_exception_logging_lines_541_543(self, manager) -> None:
        """Test OFF exception logging covering lines 541-543."""
        # Raise from a later awaited helper to reach top-level exception handling
        with patch.object(
            manager, "_get_actual_record_count", new=AsyncMock(side_effect=Exception("boom"))
        ):
            result = await manager._update_off_database(force=True)

            # Verify exception handling covers lines 541-543
            assert isinstance(result, UpdateResult)
            assert result.source == "openfoodfacts"

    @pytest.mark.asyncio
    async def test_validation_error_logging_line_442(self, manager) -> None:
        """Test validation error logging covering line 442."""
        # Create mock food with missing required nutrients
        mock_food = type(
            "Food",
            (),
            {
                "name": "Apple",
                "nutrients_per_100g": {
                    "calories": 100,
                    # Missing protein_g, fat_g, carbs_g
                },
                "cost_per_100g": 0.5,
                "tags": ["fruit"],
                "availability_regions": ["US"],
                "source": "usda",
                "source_id": "1",
            },
        )()

        # Mock USDA client to return data that will fail validation
        with patch.object(manager, "usda_client") as mock_usda:
            with patch.object(
                manager.unified_db,
                "get_common_foods_database",
                new=AsyncMock(return_value={"apple": mock_food}),
            ):
                mock_usda.fetch_all_foods = AsyncMock(
                    return_value=[
                        {"fdcId": "1", "description": "Apple"},
                    ]
                )

                # Execute update - should trigger validation error logging
                result = await manager._update_usda_database(force=True)

                # Should fail due to validation errors
                assert isinstance(result, UpdateResult)
                assert result.success is False
                assert result.source == "usda"
                assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_cache_data_exception_lines_631_632(self, manager):
        """Test cache data exception paths covering lines 631-632."""
        # Test with invalid source
        result = await manager._get_cache_data_for_checksum("invalid_source")
        assert isinstance(result, dict)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_record_count_exception_lines_688_689(self, manager):
        """Test record count exception paths covering lines 688-689."""
        # Test with invalid source
        result = await manager._get_actual_record_count("invalid_source")
        assert result == 0

    @pytest.mark.asyncio
    async def test_backup_creation_exception_lines_817_819_821(self, manager) -> None:
        """Test backup creation exception paths covering lines 817, 819-821."""
        # Mock file operations to simulate permission error and assert logging
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with patch("core.food_apis.update_manager.logger") as mock_logger:
                result = await manager._create_backup("usda", "1.0.0")
                # Expect error logged with Permission denied
                assert mock_logger.error.called or mock_logger.exception.called
                # Method should not raise; may return None/False depending on implementation
                assert result in (None, False)

    @pytest.mark.asyncio
    async def test_backup_load_exception_lines_837_838_841(self, manager, temp_dir) -> None:
        """Test backup load exception paths covering lines 837-838, 841."""
        # Create invalid backup file
        backup_file = temp_dir / "usda_backup_1.0.0.json"
        backup_file.write_text("invalid json")

        # Test that loading an invalid backup raises json.JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            await manager._load_backup("usda", "1.0.0")
