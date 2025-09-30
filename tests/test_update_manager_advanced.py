"""
Additional coverage tests for core.food_apis.update_manager module

RU: Дополнительные тесты для покрытия менеджера обновления баз данных.
EN: Additional coverage tests for database update manager module.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from core.food_apis.update_manager import (
    DatabaseUpdateManager,
    DatabaseVersion,
)
from core.food_apis.unified_db import UnifiedFoodItem


class TestDatabaseUpdateManagerAdditionalCoverage:
    """Additional coverage tests for DatabaseUpdateManager."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_manager(self, temp_cache_dir):
        """Create DatabaseUpdateManager with mocked dependencies."""
        with (
            patch("core.food_apis.update_manager.USDAClient") as mock_usda,
            patch("core.food_apis.update_manager.OFFClient") as mock_off,
            patch("core.food_apis.update_manager.UnifiedFoodDatabase") as mock_db,
            patch("core.food_apis.update_manager.OFF_AVAILABLE", True),
        ):
            # Mock the clients
            mock_usda.return_value = AsyncMock()
            mock_off.return_value = AsyncMock()
            mock_db.return_value = AsyncMock()

            yield DatabaseUpdateManager(
                cache_dir=temp_cache_dir,
                update_interval_hours=24,
                max_rollback_versions=5,
            )

    def test_save_versions_with_error(self, mock_manager):
        """Test saving versions when file write fails."""
        # Mock the file writing to fail
        with patch("builtins.open", side_effect=IOError("Write failed")):
            # Should not raise exception, just log error
            mock_manager._save_versions()
            # Test passes if no exception is raised

    @pytest.mark.asyncio
    async def test_create_backup_success(self, mock_manager):
        """Test creating backup successfully."""
        # Mock unified_db to return some test data
        test_foods = {
            "apple": UnifiedFoodItem(
                name="Apple",
                source="test",
                nutrients_per_100g={"protein_g": 0.3},
                source_id="apple_001",
                cost_per_100g=1.0,
                tags=["fruit"],
                availability_regions=["US"],
            )
        }
        mock_manager.unified_db.get_common_foods_database = AsyncMock(return_value=test_foods)

        await mock_manager._create_backup("usda", "1.0.0")

        # Check if backup file was created
        backup_file = mock_manager.cache_dir / "usda_backup_1.0.0.json"
        assert backup_file.exists()

        # Check backup content
        with open(backup_file, "r") as f:
            backup_data = json.load(f)

        assert "apple" in backup_data
        assert backup_data["apple"]["name"] == "Apple"

    @pytest.mark.asyncio
    async def test_create_backup_with_error(self, mock_manager):
        """Test creating backup when error occurs."""
        # Mock unified_db to raise an error
        mock_manager.unified_db.get_common_foods_database = AsyncMock(
            side_effect=Exception("DB error")
        )

        # Should not raise exception, just log error
        await mock_manager._create_backup("usda", "1.0.0")
        # Test passes if no exception is raised

    @pytest.mark.asyncio
    async def test_load_backup_success(self, mock_manager):
        """Test loading backup successfully."""
        # Create a test backup file
        backup_file = mock_manager.cache_dir / "usda_backup_1.0.0.json"
        test_data = {
            "apple": {
                "name": "Apple",
                "source": "test",
                "nutrients_per_100g": {"protein_g": 0.3},
                "source_id": "apple_001",
                "cost_per_100g": 1.0,
                "tags": ["fruit"],
                "availability_regions": ["US"],
            }
        }

        with open(backup_file, "w") as f:
            json.dump(test_data, f)

        loaded_foods = await mock_manager._load_backup("usda", "1.0.0")

        assert "apple" in loaded_foods
        assert loaded_foods["apple"].name == "Apple"
        assert loaded_foods["apple"].source == "test"

    @pytest.mark.asyncio
    async def test_cleanup_old_backups(self, mock_manager):
        """Test cleaning up old backup files."""
        # Create several backup files with different timestamps
        for i in range(7):  # Create more than max_rollback_versions (5)
            backup_file = mock_manager.cache_dir / f"usda_backup_1.{i}.0.json"
            with open(backup_file, "w") as f:
                json.dump({"test": "data"}, f)

        # Run cleanup
        await mock_manager._cleanup_old_backups("usda")

        # Check that only max_rollback_versions files remain
        backup_files = list(mock_manager.cache_dir.glob("usda_backup_*.json"))
        assert len(backup_files) <= mock_manager.max_rollback_versions

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_with_error(self, mock_manager):
        """Test cleanup when error occurs."""
        # Mock glob to raise an error
        with patch.object(mock_manager.cache_dir, "glob", side_effect=Exception("Glob error")):
            # Should not raise exception, just log error
            await mock_manager._cleanup_old_backups("usda")
            # Test passes if no exception is raised

    @pytest.mark.asyncio
    async def test_rollback_database_success(self, mock_manager):
        """Test successful database rollback."""
        # Create a backup to rollback to
        backup_file = mock_manager.cache_dir / "usda_backup_1.0.0.json"
        test_data = {
            "apple": {
                "name": "Apple",
                "source": "test",
                "nutrients_per_100g": {"protein_g": 0.3},
                "source_id": "apple_001",
                "cost_per_100g": 1.0,
                "tags": ["fruit"],
                "availability_regions": ["US"],
            }
        }

        with open(backup_file, "w") as f:
            json.dump(test_data, f)

        # Add current version
        mock_manager.versions["usda"] = DatabaseVersion(
            source="usda",
            version="2.0.0",
            last_updated=datetime.now().isoformat(),
            record_count=100,
            checksum="current_checksum",
            metadata={},
        )

        result = await mock_manager.rollback_database("usda", "1.0.0")

        assert result is True
        assert "usda" in mock_manager.versions
        assert "rollback" in mock_manager.versions["usda"].version
        assert mock_manager.versions["usda"].metadata["rolled_back_to"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_rollback_database_with_error(self, mock_manager):
        """Test rollback when error occurs."""
        # No backup file exists, should fail gracefully
        result = await mock_manager.rollback_database("usda", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_for_updates_without_off_client(self, mock_manager):
        """Test checking updates when OFF client is not available."""
        # Disable OFF client
        mock_manager.off_client = None

        # Mock USDA check
        mock_manager._check_usda_updates = AsyncMock(return_value=True)

        result = await mock_manager.check_for_updates()

        assert result["usda"] is True
        # OFF should not be checked when client is None
        assert "openfoodfacts" not in result or result["openfoodfacts"] is False

    @pytest.mark.asyncio
    async def test_update_database_with_callback_error(self, mock_manager):
        """Test update database when callback raises error."""

        # Add a callback that raises an error
        def error_callback(result):
            raise Exception("Callback error")

        mock_manager.add_update_callback(error_callback)

        # Should not crash despite callback error
        result = await mock_manager.update_database("unknown_source")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_update_database_off_source(self, mock_manager):
        """Test updating OpenFoodFacts database."""
        # Mock the OFF client and its methods
        mock_manager.off_client.search_products = AsyncMock(return_value=[])
        mock_manager.unified_db.get_common_foods_database = AsyncMock(return_value={})

        result = await mock_manager.update_database("openfoodfacts")

        # Should succeed even with empty data
        assert result.source == "openfoodfacts"

    @pytest.mark.asyncio
    async def test_update_database_off_not_available(self, temp_cache_dir):
        """Test updating OFF database when OFF is not available."""
        with (
            patch("core.food_apis.update_manager.USDAClient") as mock_usda,
            patch("core.food_apis.update_manager.OFFClient") as mock_off,
            patch("core.food_apis.update_manager.UnifiedFoodDatabase") as mock_db,
            patch("core.food_apis.update_manager.OFF_AVAILABLE", False),
        ):
            mock_usda.return_value = AsyncMock()
            mock_off.return_value = AsyncMock()
            mock_db.return_value = AsyncMock()

            manager = DatabaseUpdateManager(cache_dir=temp_cache_dir)

            result = await manager.update_database("openfoodfacts")

            assert result.success is False
            assert "Unknown source" in result.errors[0]


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_initialization_with_off_not_available(self, temp_cache_dir):
        """Test manager initialization when OFF is not available."""
        with (
            patch("core.food_apis.update_manager.USDAClient") as mock_usda,
            patch("core.food_apis.update_manager.OFFClient") as mock_off,
            patch("core.food_apis.update_manager.UnifiedFoodDatabase") as mock_db,
            patch("core.food_apis.update_manager.OFF_AVAILABLE", False),
        ):
            mock_usda.return_value = AsyncMock()
            mock_off.return_value = AsyncMock()
            mock_db.return_value = AsyncMock()

            manager = DatabaseUpdateManager(cache_dir=temp_cache_dir)

            assert manager.off_client is None

    def test_load_versions_permission_error(self, temp_cache_dir):
        """Test loading versions when permission error occurs."""
        # Create a directory with the same name as versions file
        versions_dir = Path(temp_cache_dir) / "database_versions.json"
        versions_dir.mkdir()

        with (
            patch("core.food_apis.update_manager.USDAClient"),
            patch("core.food_apis.update_manager.OFFClient"),
            patch("core.food_apis.update_manager.UnifiedFoodDatabase"),
        ):
            manager = DatabaseUpdateManager(cache_dir=temp_cache_dir)

            # Should handle error gracefully and return empty dict
            assert manager.versions == {}

    @pytest.mark.asyncio
    async def test_validate_food_data_with_empty_source(self):
        """Test validation with empty source."""
        with (
            patch("core.food_apis.update_manager.USDAClient"),
            patch("core.food_apis.update_manager.OFFClient"),
            patch("core.food_apis.update_manager.UnifiedFoodDatabase"),
        ):
            manager = DatabaseUpdateManager()

            # Create food with empty source
            invalid_food = UnifiedFoodItem(
                name="Test Food",
                source="",  # Empty source
                nutrients_per_100g={"protein_g": 0.3},
                source_id="test_001",
                cost_per_100g=1.0,
                tags=[],
                availability_regions=["US"],
            )

            foods = {"invalid": invalid_food}

            errors = await manager._validate_food_data(foods)
            assert len(errors) > 0
            assert "missing required fields" in errors[0]


class TestAsyncMethods:
    """Test specific async method coverage."""

    @pytest.fixture
    def mock_manager(self):
        """Create manager with mocked dependencies."""
        with (
            patch("core.food_apis.update_manager.USDAClient") as mock_usda,
            patch("core.food_apis.update_manager.OFFClient") as mock_off,
            patch("core.food_apis.update_manager.UnifiedFoodDatabase") as mock_db,
        ):
            mock_usda.return_value = AsyncMock()
            mock_off.return_value = AsyncMock()
            mock_db.return_value = AsyncMock()

            yield DatabaseUpdateManager()

    @pytest.mark.asyncio
    async def test_check_off_updates_recent_update(self, mock_manager):
        """Test checking OFF updates when recent update exists."""
        # Add recent version
        recent_time = datetime.now() - timedelta(hours=1)  # 1 hour ago
        mock_manager.versions["openfoodfacts"] = DatabaseVersion(
            source="openfoodfacts",
            version="1.0.0",
            last_updated=recent_time.isoformat(),
            record_count=50,
            checksum="def456",
            metadata={},
        )

        # Should not need update (interval is 24 hours)
        result = await mock_manager._check_off_updates()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_off_updates_old_update(self, mock_manager):
        """Test checking OFF updates when old update exists."""
        # Add old version
        old_time = datetime.now() - timedelta(hours=48)  # 48 hours ago
        mock_manager.versions["openfoodfacts"] = DatabaseVersion(
            source="openfoodfacts",
            version="1.0.0",
            last_updated=old_time.isoformat(),
            record_count=50,
            checksum="def456",
            metadata={},
        )

        # Should need update (older than 24 hours)
        result = await mock_manager._check_off_updates()
        assert result is True

    @pytest.mark.asyncio
    async def test_update_usda_database_no_force_no_change(self, mock_manager):
        """Test USDA update when data hasn't changed and not forced."""
        # Set up existing version with same checksum as new data
        existing_version = DatabaseVersion(
            source="usda",
            version="1.0.0",
            last_updated="2023-01-01T00:00:00",
            record_count=100,
            checksum="same_checksum",
            metadata={},
        )
        mock_manager.versions["usda"] = existing_version

        # Mock data that would produce same checksum
        test_foods = {"apple": MagicMock()}
        mock_manager.unified_db.get_common_foods_database = AsyncMock(return_value=test_foods)

        # Mock checksum calculation to return same value
        mock_manager._calculate_checksum = MagicMock(return_value="same_checksum")

        result = await mock_manager._update_usda_database(force=False)

        assert result.success is True
        assert result.old_version == "1.0.0"
        assert result.new_version == "1.0.0"  # No change
        assert result.records_added == 0
        assert result.records_updated == 0
        assert result.records_removed == 0


class TestUtilityMethods:
    """Test utility methods for better coverage."""

    @pytest.fixture
    def mock_manager(self):
        """Create manager with mocked dependencies."""
        with (
            patch("core.food_apis.update_manager.USDAClient"),
            patch("core.food_apis.update_manager.OFFClient"),
            patch("core.food_apis.update_manager.UnifiedFoodDatabase"),
        ):
            yield DatabaseUpdateManager()

    def test_generate_food_key_edge_cases(self, mock_manager):
        """Test food key generation with edge cases."""
        # Test with only special characters
        key1 = mock_manager._generate_food_key("!@#$%^&*()")
        assert key1 == ""

        # Test with numbers only
        key2 = mock_manager._generate_food_key("12345")
        assert key2 == "12345"

        # Test with mixed case and accents (if any)
        key3 = mock_manager._generate_food_key("CaFé Latté")
        assert key3 == "caf_latt"  # Simplified expectation

        # Test empty string
        key4 = mock_manager._generate_food_key("")
        assert key4 == ""

        # Test only spaces
        key5 = mock_manager._generate_food_key("   ")
        assert key5 == ""
