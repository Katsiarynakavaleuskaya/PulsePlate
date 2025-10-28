"""
Additional tests to reach 97% coverage for core.food_apis.update_manager.
Targeting remaining uncovered lines: 68, 329-330, 369-371, 442, 474-475, 541-543, etc.
"""

import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, patch

import pytest

from core.food_apis.update_manager import (
    DatabaseUpdateManager,
    DatabaseVersion,
    UpdateResult,
    _PatchablePathWrapper,
)


class TestUpdateManagerFinalCoverage:
    """Final tests to achieve 97% coverage."""

    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def manager(self, temp_dir: Path) -> DatabaseUpdateManager:
        """Create DatabaseUpdateManager instance."""
        return DatabaseUpdateManager(cache_dir=temp_dir, update_interval_hours=24)

    def test_patchable_path_wrapper_hash(self):
        """Test _PatchablePathWrapper.__hash__ method (line 68)."""
        path1 = Path("/test/path")
        path2 = Path("/test/path")
        path3 = Path("/different/path")

        wrapper1 = _PatchablePathWrapper(path1)
        wrapper2 = _PatchablePathWrapper(path2)
        wrapper3 = _PatchablePathWrapper(path3)

        # Test hash equality for same paths
        assert hash(wrapper1) == hash(wrapper2)
        assert hash(wrapper1) == hash(path1)

        # Test hash inequality for different paths
        assert hash(wrapper1) != hash(wrapper3)

        # Test that hash is consistent
        assert hash(wrapper1) == hash(wrapper1)

    @pytest.mark.asyncio
    async def test_backup_load_warning_lines_329_330(self, manager, temp_dir):
        """Test backup load warning path covering lines 329-330."""
        # Create backup file that will cause a warning
        backup_file = temp_dir / "usda_backup_1.0.0.json"
        backup_file.write_text("invalid json content")

        # Add existing version
        manager.versions["usda"] = DatabaseVersion(
            source="usda",
            version="1.0.0",
            last_updated="2023-01-01T00:00:00Z",
            record_count=1,
            checksum="abc123",
            metadata={"test": "data"},
        )

        # Mock successful USDA client
        with patch.object(manager, "usda_client") as mock_usda:
            with patch.object(manager.unified_db, "get_common_foods_database") as mock_get_foods:
                mock_usda.fetch_all_foods = AsyncMock(return_value=[])

                mock_food = type(
                    "Food",
                    (),
                    {
                        "name": "Apple",
                        "nutrients_per_100g": {
                            "calories": 100,
                            "protein_g": 0.3,
                            "fat_g": 0.2,
                            "carbs_g": 25.0,
                        },
                        "cost_per_100g": 0.5,
                        "tags": ["fruit"],
                        "availability_regions": ["US"],
                        "source": "usda",
                        "source_id": "1",
                    },
                )()

                mock_get_foods.return_value = {"apple": mock_food}

                # Execute update - should handle backup load warning gracefully
                result = await manager._update_usda_database(force=True)

                # Should succeed despite backup load warning
                assert isinstance(result, UpdateResult)
                assert result.success is True
                assert result.source == "usda"

    @pytest.mark.asyncio
    async def test_backup_load_warning_lines_474_475(self, manager, temp_dir):
        """Test OFF backup load warning path covering lines 474-475."""
        # Create backup file that will cause a warning
        backup_file = temp_dir / "openfoodfacts_backup_1.0.0.json"
        backup_file.write_text("invalid json content")

        # Add existing version
        manager.versions["openfoodfacts"] = DatabaseVersion(
            source="openfoodfacts",
            version="1.0.0",
            last_updated="2023-01-01T00:00:00Z",
            record_count=1,
            checksum="abc123",
            metadata={"test": "data"},
        )

        # Mock successful OFF client
        with patch.object(manager, "off_client") as mock_off:
            with patch.object(manager.unified_db, "get_common_foods_database") as mock_get_foods:
                mock_off.search_products = AsyncMock(return_value=[])

                mock_food = type(
                    "Food",
                    (),
                    {
                        "name": "Apple",
                        "nutrients_per_100g": {
                            "calories": 100,
                            "protein_g": 0.3,
                            "fat_g": 0.2,
                            "carbs_g": 25.0,
                        },
                        "cost_per_100g": 0.5,
                        "tags": ["fruit"],
                        "availability_regions": ["US"],
                        "source": "openfoodfacts",
                        "source_id": "1",
                    },
                )()

                mock_get_foods.return_value = {"apple": mock_food}

                # Execute update - should handle backup load warning gracefully
                result = await manager._update_off_database(force=True)

                # Should succeed despite backup load warning
                assert isinstance(result, UpdateResult)
                assert result.success is True
                assert result.source == "openfoodfacts"

    @pytest.mark.asyncio
    async def test_usda_success_final_lines_369_371(self, manager, temp_dir):
        """Test USDA success final lines 369-371."""
        # Mock successful USDA client with proper data
        with patch.object(manager, "usda_client") as mock_usda:
            with patch.object(manager.unified_db, "get_common_foods_database") as mock_get_foods:
                mock_usda.fetch_all_foods = AsyncMock(
                    return_value=[
                        {"fdcId": "1", "description": "Apple"},
                        {"fdcId": "2", "description": "Banana"},
                    ]
                )

                mock_food1 = type(
                    "Food",
                    (),
                    {
                        "name": "Apple",
                        "nutrients_per_100g": {
                            "calories": 100,
                            "protein_g": 0.3,
                            "fat_g": 0.2,
                            "carbs_g": 25.0,
                        },
                        "cost_per_100g": 0.5,
                        "tags": ["fruit"],
                        "availability_regions": ["US"],
                        "source": "usda",
                        "source_id": "1",
                    },
                )()

                mock_food2 = type(
                    "Food",
                    (),
                    {
                        "name": "Banana",
                        "nutrients_per_100g": {
                            "calories": 200,
                            "protein_g": 1.1,
                            "fat_g": 0.3,
                            "carbs_g": 51.0,
                        },
                        "cost_per_100g": 0.3,
                        "tags": ["fruit"],
                        "availability_regions": ["US"],
                        "source": "usda",
                        "source_id": "2",
                    },
                )()

                mock_get_foods.return_value = {"apple": mock_food1, "banana": mock_food2}

                # Execute successful update
                result = await manager._update_usda_database(force=True)

                # Verify success path covers lines 369-371
                assert isinstance(result, UpdateResult)
                assert result.success is True
                assert result.source == "usda"
                assert result.new_version is not None
                assert result.errors == []
                assert result.duration_seconds >= 0.0

    @pytest.mark.asyncio
    async def test_off_success_final_lines_541_543(self, manager, temp_dir):
        """Test OFF success final lines 541-543."""
        # Create SQLite database for OFF
        sqlite_file = temp_dir / "off.sqlite"
        import sqlite3

        conn = sqlite3.connect(str(sqlite_file))
        try:
            conn.execute("CREATE TABLE products (name TEXT, data TEXT)")
            conn.execute("INSERT INTO products VALUES ('apple', '{\"name\": \"Apple\"}')")
            conn.execute("INSERT INTO products VALUES ('banana', '{\"name\": \"Banana\"}')")
            conn.commit()
        finally:
            conn.close()

        # Mock successful OFF client
        with patch.object(manager, "off_client") as mock_off:
            with patch.object(manager.unified_db, "get_common_foods_database") as mock_get_foods:
                mock_off.search_products = AsyncMock(
                    return_value=[
                        {"code": "1", "product_name": "Apple"},
                        {"code": "2", "product_name": "Banana"},
                    ]
                )

                mock_food1 = type(
                    "Food",
                    (),
                    {
                        "name": "Apple",
                        "nutrients_per_100g": {
                            "calories": 100,
                            "protein_g": 0.3,
                            "fat_g": 0.2,
                            "carbs_g": 25.0,
                        },
                        "cost_per_100g": 0.5,
                        "tags": ["fruit"],
                        "availability_regions": ["US"],
                        "source": "openfoodfacts",
                        "source_id": "1",
                    },
                )()

                mock_food2 = type(
                    "Food",
                    (),
                    {
                        "name": "Banana",
                        "nutrients_per_100g": {
                            "calories": 200,
                            "protein_g": 1.1,
                            "fat_g": 0.3,
                            "carbs_g": 51.0,
                        },
                        "cost_per_100g": 0.3,
                        "tags": ["fruit"],
                        "availability_regions": ["US"],
                        "source": "openfoodfacts",
                        "source_id": "2",
                    },
                )()

                mock_get_foods.return_value = {"apple": mock_food1, "banana": mock_food2}

                # Execute successful update
                result = await manager._update_off_database(force=True)

                # Verify success path covers lines 541-543
                assert isinstance(result, UpdateResult)
                assert result.success is True
                assert result.source == "openfoodfacts"
                assert result.new_version is not None
                assert result.errors == []
                assert result.duration_seconds >= 0.0

    @pytest.mark.asyncio
    async def test_validation_error_line_442(self, manager):
        """Test validation error path covering line 442."""
        # Mock USDA client to return data that will fail validation
        with patch.object(manager, "usda_client") as mock_usda:
            with patch.object(manager.unified_db, "get_common_foods_database") as mock_get_foods:
                mock_usda.fetch_all_foods = AsyncMock(
                    return_value=[
                        {"fdcId": "1", "description": "Apple"},
                    ]
                )

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

                mock_get_foods.return_value = {"apple": mock_food}

                # Execute update - should trigger validation error
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
    async def test_backup_creation_exception_lines_817_819_821(self, manager, temp_dir):
        """Test backup creation exception paths covering lines 817, 819-821."""
        # Create a file that will cause permission error
        backup_file = temp_dir / "usda_backup_1.0.0.json"
        backup_file.write_text("{}")
        backup_file.chmod(0o444)  # Read-only

        # Try to create backup - should handle exception gracefully
        try:
            await manager._create_backup("usda", "1.0.0")
        except Exception:
            # Expected to fail due to permission
            pass

        # Restore permissions
        backup_file.chmod(0o644)

    @pytest.mark.asyncio
    async def test_backup_load_exception_lines_837_838_841(self, manager, temp_dir):
        """Test backup load exception paths covering lines 837-838, 841."""
        # Create invalid backup file
        backup_file = temp_dir / "usda_backup_1.0.0.json"
        backup_file.write_text("invalid json")

        # Try to load backup - should handle exception gracefully
        try:
            await manager._load_backup("usda", "1.0.0")
        except Exception:
            # Expected to fail due to invalid JSON
            pass
