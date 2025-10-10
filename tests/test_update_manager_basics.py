"""
Basic tests for core.food_apis.update_manager module

RU: Базовые тесты для модуля менеджера обновления баз данных.
EN: Basic tests for database update manager module.
"""

from datetime import datetime, timedelta
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from core.food_apis.unified_db import UnifiedFoodItem
from core.food_apis.update_manager import (
    DatabaseUpdateManager,
    DatabaseVersion,
    UpdateResult,
    run_scheduled_update,
)


class TestDatabaseVersion:
    """Test DatabaseVersion dataclass."""

    def test_database_version_creation(self):
        """Test creating DatabaseVersion object."""
        version = DatabaseVersion(
            source="test_source",
            version="1.0.0",
            last_updated="2023-01-01T00:00:00",
            record_count=100,
            checksum="abc123",
            metadata={"test": "data"},
        )

        assert version.source == "test_source"
        assert version.version == "1.0.0"
        assert version.record_count == 100
        assert version.checksum == "abc123"
        assert version.metadata["test"] == "data"


class TestUpdateResult:
    """Test UpdateResult dataclass."""

    def test_update_result_creation(self):
        """Test creating UpdateResult object."""
        result = UpdateResult(
            success=True,
            source="test_source",
            old_version="1.0.0",
            new_version="1.1.0",
            records_added=10,
            records_updated=5,
            records_removed=2,
            errors=[],
            duration_seconds=1.5,
        )

        assert result.success is True
        assert result.source == "test_source"
        assert result.old_version == "1.0.0"
        assert result.new_version == "1.1.0"
        assert result.records_added == 10
        assert result.records_updated == 5
        assert result.records_removed == 2
        assert result.errors == []
        assert result.duration_seconds == 1.5


class TestDatabaseUpdateManagerBasics:
    """Test basic functionality of DatabaseUpdateManager."""

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

    def test_manager_initialization(self, temp_cache_dir):
        """Test manager initialization."""
        with (
            patch("core.food_apis.update_manager.USDAClient") as mock_usda,
            patch("core.food_apis.update_manager.OFFClient") as mock_off,
            patch("core.food_apis.update_manager.UnifiedFoodDatabase") as mock_db,
        ):
            mock_usda.return_value = AsyncMock()
            mock_off.return_value = AsyncMock()
            mock_db.return_value = AsyncMock()

            manager = DatabaseUpdateManager(
                cache_dir=temp_cache_dir, update_interval_hours=12, max_rollback_versions=3
            )

            assert manager.cache_dir == Path(temp_cache_dir)
            assert manager.update_interval == timedelta(hours=12)
            assert manager.max_rollback_versions == 3
            assert manager.update_callbacks == []
            assert isinstance(manager.versions, dict)

    def test_load_versions_empty_file(self, mock_manager):
        """Test loading versions when file doesn't exist."""
        # versions_file doesn't exist, should return empty dict
        versions = mock_manager._load_versions()
        assert versions == {}

    def test_load_versions_with_data(self, temp_cache_dir):
        """Test loading versions from existing file."""
        # Create a versions file with test data
        versions_file = Path(temp_cache_dir) / "database_versions.json"
        test_data = {
            "usda": {
                "source": "usda",
                "version": "1.0.0",
                "last_updated": "2023-01-01T00:00:00",
                "record_count": 100,
                "checksum": "abc123",
                "metadata": {},
            }
        }

        with open(versions_file, "w") as f:
            json.dump(test_data, f)

        with (
            patch("core.food_apis.update_manager.USDAClient") as mock_usda,
            patch("core.food_apis.update_manager.OFFClient") as mock_off,
            patch("core.food_apis.update_manager.UnifiedFoodDatabase") as mock_db,
        ):
            mock_usda.return_value = AsyncMock()
            mock_off.return_value = AsyncMock()
            mock_db.return_value = AsyncMock()

            manager = DatabaseUpdateManager(cache_dir=temp_cache_dir)

            assert "usda" in manager.versions
            assert manager.versions["usda"].source == "usda"
            assert manager.versions["usda"].version == "1.0.0"
            assert manager.versions["usda"].record_count == 100

    def test_load_versions_with_invalid_json(self, temp_cache_dir):
        """Test loading versions with invalid JSON file."""
        # Create invalid JSON file
        versions_file = Path(temp_cache_dir) / "database_versions.json"
        with open(versions_file, "w") as f:
            f.write("invalid json content")

        with (
            patch("core.food_apis.update_manager.USDAClient") as mock_usda,
            patch("core.food_apis.update_manager.OFFClient") as mock_off,
            patch("core.food_apis.update_manager.UnifiedFoodDatabase") as mock_db,
        ):
            mock_usda.return_value = AsyncMock()
            mock_off.return_value = AsyncMock()
            mock_db.return_value = AsyncMock()

            manager = DatabaseUpdateManager(cache_dir=temp_cache_dir)

            # Should return empty dict when JSON is invalid
            assert manager.versions == {}

    def test_save_versions(self, mock_manager):
        """Test saving versions to file."""
        # Add test version
        test_version = DatabaseVersion(
            source="test",
            version="1.0.0",
            last_updated="2023-01-01T00:00:00",
            record_count=50,
            checksum="test123",
            metadata={"test": True},
        )

        mock_manager.versions["test"] = test_version
        mock_manager._save_versions()

        # Check if file was created and contains correct data
        assert mock_manager.versions_file.exists()

        with open(mock_manager.versions_file) as f:
            saved_data = json.load(f)

        assert "test" in saved_data
        assert saved_data["test"]["source"] == "test"
        assert saved_data["test"]["version"] == "1.0.0"
        assert saved_data["test"]["record_count"] == 50

    def test_calculate_checksum(self, mock_manager):
        """Test checksum calculation."""
        test_data = {"key1": "value1", "key2": "value2"}
        checksum1 = mock_manager._calculate_checksum(test_data)
        checksum2 = mock_manager._calculate_checksum(test_data)

        # Same data should produce same checksum
        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA256 hex digest length

        # Different data should produce different checksum
        different_data = {"key1": "different_value", "key2": "value2"}
        checksum3 = mock_manager._calculate_checksum(different_data)
        assert checksum1 != checksum3

    def test_generate_food_key(self, mock_manager):
        """Test food key generation."""
        # Test basic conversion
        key1 = mock_manager._generate_food_key("Apple Juice")
        assert key1 == "apple_juice"

        # Test with special characters
        key2 = mock_manager._generate_food_key("Bread & Butter")
        assert key2 == "bread__butter"

        # Test with numbers
        key3 = mock_manager._generate_food_key("Vitamin B12")
        assert key3 == "vitamin_b12"

        # Test with extra spaces
        key4 = mock_manager._generate_food_key("  Greek Yogurt  ")
        assert key4 == "greek_yogurt"

    def test_add_update_callback(self, mock_manager):
        """Test adding update callbacks."""

        def test_callback(result):
            pass

        mock_manager.add_update_callback(test_callback)
        assert len(mock_manager.update_callbacks) == 1
        assert mock_manager.update_callbacks[0] == test_callback

    def test_get_database_status_empty(self, mock_manager):
        """Test getting database status when no versions exist."""
        status = mock_manager.get_database_status()
        assert status == {}

    def test_get_database_status_with_data(self, mock_manager):
        """Test getting database status with existing versions."""
        # Add test version
        test_version = DatabaseVersion(
            source="usda",
            version="1.0.0",
            last_updated=datetime.now().isoformat(),
            record_count=100,
            checksum="abcdef123456789",
            metadata={"type": "test"},
        )

        mock_manager.versions["usda"] = test_version

        status = mock_manager.get_database_status()

        assert "usda" in status
        assert status["usda"]["version"] == "1.0.0"
        assert status["usda"]["record_count"] == 100
        assert status["usda"]["checksum"] == "abcdef12..."  # Truncated
        assert status["usda"]["metadata"]["type"] == "test"
        assert "hours_since_update" in status["usda"]


class TestDatabaseUpdateManagerAsync:
    """Test async functionality of DatabaseUpdateManager."""

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

    @pytest.mark.asyncio
    async def test_check_usda_updates_no_current_version(self, mock_manager):
        """Test checking USDA updates when no current version exists."""
        # No current version - updates should be available
        result = await mock_manager._check_usda_updates()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_usda_updates_recent_update(self, mock_manager):
        """Test checking USDA updates when recent update exists."""
        # Add recent version
        recent_time = datetime.now() - timedelta(hours=1)  # 1 hour ago
        mock_manager.versions["usda"] = DatabaseVersion(
            source="usda",
            version="1.0.0",
            last_updated=recent_time.isoformat(),
            record_count=100,
            checksum="abc123",
            metadata={},
        )

        # Should not need update (interval is 24 hours)
        result = await mock_manager._check_usda_updates()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_usda_updates_old_update(self, mock_manager):
        """Test checking USDA updates when old update exists."""
        # Add old version
        old_time = datetime.now() - timedelta(hours=48)  # 48 hours ago
        mock_manager.versions["usda"] = DatabaseVersion(
            source="usda",
            version="1.0.0",
            last_updated=old_time.isoformat(),
            record_count=100,
            checksum="abc123",
            metadata={},
        )

        # Should need update (older than 24 hours)
        result = await mock_manager._check_usda_updates()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_off_updates_no_current_version(self, mock_manager):
        """Test checking OFF updates when no current version exists."""
        # No current version - updates should be available
        result = await mock_manager._check_off_updates()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_for_updates_success(self, mock_manager):
        """Test checking for updates across all sources."""
        # Mock the private methods
        mock_manager._check_usda_updates = AsyncMock(return_value=True)
        mock_manager._check_off_updates = AsyncMock(return_value=False)

        result = await mock_manager.check_for_updates()

        assert result["usda"] is True
        assert result["openfoodfacts"] is False

    @pytest.mark.asyncio
    async def test_check_for_updates_with_errors(self, mock_manager):
        """Test checking for updates when errors occur."""
        # Mock the private methods to raise exceptions
        mock_manager._check_usda_updates = AsyncMock(side_effect=Exception("USDA error"))
        mock_manager._check_off_updates = AsyncMock(side_effect=Exception("OFF error"))

        result = await mock_manager.check_for_updates()

        # Should handle errors gracefully
        assert result["usda"] is False
        assert result["openfoodfacts"] is False

    @pytest.mark.asyncio
    async def test_update_database_unknown_source(self, mock_manager):
        """Test updating database with unknown source."""
        result = await mock_manager.update_database("unknown_source")

        assert result.success is False
        assert result.source == "unknown_source"
        assert "Unknown source" in result.errors[0]
        assert result.records_added == 0
        assert result.records_updated == 0
        assert result.records_removed == 0

    @pytest.mark.asyncio
    async def test_close(self, mock_manager):
        """Test closing manager connections."""
        await mock_manager.close()

        # Verify all clients were closed
        mock_manager.usda_client.close.assert_called_once()
        mock_manager.off_client.close.assert_called_once()
        mock_manager.unified_db.close.assert_called_once()


class TestScheduledUpdate:
    """Test scheduled update functionality."""

    @pytest.mark.asyncio
    async def test_run_scheduled_update_no_updates(self):
        """Test scheduled update when no updates are available."""
        mock_manager = AsyncMock()
        mock_manager.check_for_updates.return_value = {"usda": False, "openfoodfacts": False}

        results = await run_scheduled_update(mock_manager)

        assert results == {}
        mock_manager.check_for_updates.assert_called_once()
        mock_manager.update_database.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_scheduled_update_with_updates(self):
        """Test scheduled update when updates are available."""
        mock_manager = AsyncMock()
        mock_manager.check_for_updates.return_value = {"usda": True, "openfoodfacts": False}

        # Mock update result
        update_result = UpdateResult(
            success=True,
            source="usda",
            old_version="1.0.0",
            new_version="1.1.0",
            records_added=10,
            records_updated=5,
            records_removed=0,
            errors=[],
            duration_seconds=1.5,
        )
        mock_manager.update_database.return_value = update_result

        results = await run_scheduled_update(mock_manager)

        assert "usda" in results
        assert results["usda"] == update_result
        mock_manager.check_for_updates.assert_called_once()
        mock_manager.update_database.assert_called_once_with("usda")


class TestValidateData:
    """Test data validation functionality."""

    @pytest.fixture
    def mock_manager(self):
        """Create a minimal manager for testing validation."""
        with (
            patch("core.food_apis.update_manager.USDAClient"),
            patch("core.food_apis.update_manager.OFFClient"),
            patch("core.food_apis.update_manager.UnifiedFoodDatabase"),
        ):
            yield DatabaseUpdateManager()

    @pytest.mark.asyncio
    async def test_validate_food_data_valid(self, mock_manager):
        """Test validation with valid food data."""
        # Create valid food item
        valid_food = UnifiedFoodItem(
            name="Apple",
            source="test",
            nutrients_per_100g={"protein_g": 0.3, "fat_g": 0.2, "carbs_g": 13.8, "calories": 52},
            source_id="apple_001",
            cost_per_100g=1.0,
            tags=["fruit"],
            availability_regions=["US"],
        )

        foods = {"apple": valid_food}

        errors = await mock_manager._validate_food_data(foods)
        assert errors == []

    @pytest.mark.asyncio
    async def test_validate_food_data_missing_name(self, mock_manager):
        """Test validation with missing name."""
        invalid_food = UnifiedFoodItem(
            name="",  # Empty name
            source="test",
            nutrients_per_100g={"protein_g": 0.3, "fat_g": 0.2, "carbs_g": 13.8},
            source_id="food_001",
            cost_per_100g=1.0,
            tags=[],
            availability_regions=["US"],
        )

        foods = {"invalid": invalid_food}

        errors = await mock_manager._validate_food_data(foods)
        assert len(errors) > 0
        assert "missing required fields" in errors[0]

    @pytest.mark.asyncio
    async def test_validate_food_data_missing_nutrients(self, mock_manager):
        """Test validation with missing nutrients."""
        food_missing_nutrients = UnifiedFoodItem(
            name="Incomplete Food",
            source="test",
            nutrients_per_100g={
                "protein_g": 0.3,
                # Missing fat_g and carbs_g
            },
            source_id="incomplete_001",
            cost_per_100g=1.0,
            tags=[],
            availability_regions=["US"],
        )

        foods = {"incomplete": food_missing_nutrients}

        errors = await mock_manager._validate_food_data(foods)
        assert len(errors) > 0
        assert "missing nutrients" in errors[0]

    @pytest.mark.asyncio
    async def test_validate_food_data_negative_values(self, mock_manager):
        """Test validation with negative nutrient values."""
        food_negative = UnifiedFoodItem(
            name="Negative Food",
            source="test",
            nutrients_per_100g={"protein_g": -1.0, "fat_g": 0.2, "carbs_g": 13.8},  # Negative value
            source_id="negative_001",
            cost_per_100g=1.0,
            tags=[],
            availability_regions=["US"],
        )

        foods = {"negative": food_negative}

        errors = await mock_manager._validate_food_data(foods)
        assert len(errors) > 0
        assert "negative" in errors[0]

    @pytest.mark.asyncio
    async def test_validate_food_data_unrealistic_values(self, mock_manager):
        """Test validation with unrealistic nutrient values."""
        food_unrealistic = UnifiedFoodItem(
            name="Unrealistic Food",
            source="test",
            nutrients_per_100g={
                "protein_g": 150.0,  # Over 100g per 100g
                "fat_g": 0.2,
                "carbs_g": 13.8,
            },
            source_id="unrealistic_001",
            cost_per_100g=1.0,
            tags=[],
            availability_regions=["US"],
        )

        foods = {"unrealistic": food_unrealistic}

        errors = await mock_manager._validate_food_data(foods)
        assert len(errors) > 0
        assert "unrealistic" in errors[0]
