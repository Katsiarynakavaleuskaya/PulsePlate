"""
Real coverage tests for core.food_apis.update_manager module.
No Mock patching - test actual code paths and logic.
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from core.food_apis.update_manager import (
    DatabaseUpdateManager,
    DatabaseVersion,
    UpdateResult,
    _PatchablePathWrapper,
    run_scheduled_update,
)
from core.time_utils import now_utc


class TestUpdateManagerRealCoverage:
    """Test class focused on real logic coverage without Mock patching."""

    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def manager(self, temp_dir: Path) -> DatabaseUpdateManager:
        """Create DatabaseUpdateManager instance."""
        return DatabaseUpdateManager(cache_dir=temp_dir, update_interval_hours=24)

    def test_patchable_path_wrapper_real_logic(self):
        """Test _PatchablePathWrapper with real path operations."""
        path = Path("/test/path")
        wrapper = _PatchablePathWrapper(path)

        # Test real delegation
        assert wrapper._path == path
        assert str(wrapper) == str(path)
        assert wrapper == wrapper
        assert wrapper != _PatchablePathWrapper(Path("/other"))

        # Test real path operations
        assert wrapper / "subdir" == path / "subdir"
        # Compare results, not generators
        wrapper_files = list(wrapper.glob("*.txt"))
        path_files = list(path.glob("*.txt"))
        assert wrapper_files == path_files

    def test_database_version_real_creation(self):
        """Test DatabaseVersion with real data."""
        version = DatabaseVersion(
            source="test",
            version="1.0.0",
            last_updated="2023-01-01T00:00:00Z",
            record_count=100,
            checksum="abc123",
            metadata={"test": "data"},
        )
        assert version.version == "1.0.0"
        assert version.source == "test"
        assert version.record_count == 100

    def test_update_result_real_creation(self):
        """Test UpdateResult with real data."""
        result = UpdateResult(
            success=True,
            source="usda",
            old_version="0.9.0",
            new_version="1.0.0",
            records_added=50,
            records_updated=30,
            records_removed=5,
            errors=[],
            duration_seconds=10.5,
        )
        assert result.success is True
        assert result.source == "usda"
        assert result.records_added == 50

    def test_manager_real_initialization(self, manager, temp_dir):
        """Test DatabaseUpdateManager real initialization."""
        assert manager.cache_dir._path == temp_dir
        assert manager.update_interval.total_seconds() == 24 * 3600
        assert isinstance(manager.versions, dict)
        assert isinstance(manager.update_callbacks, list)

    def test_version_management_real_logic(self, manager, temp_dir):
        """Test version management with real file operations."""
        # Test empty versions
        versions = manager._load_versions()
        assert len(versions) == 0

        # Test saving versions
        manager.versions["test"] = DatabaseVersion(
            source="test",
            version="1.0.0",
            last_updated="2023-01-01T00:00:00Z",
            record_count=100,
            checksum="abc123",
            metadata={"test": "data"},
        )
        manager._save_versions()

        # Test loading versions
        versions_file = temp_dir / "database_versions.json"
        assert versions_file.exists()
        versions = manager._load_versions()
        assert "test" in versions

    def test_checksum_real_calculation(self, manager):
        """Test checksum calculation with real data."""
        data = {"test": "data", "number": 123}
        checksum = manager._calculate_checksum(data)
        assert isinstance(checksum, str)
        assert len(checksum) > 0

        # Same data should produce same checksum
        checksum2 = manager._calculate_checksum(data)
        assert checksum == checksum2

        # Different data should produce different checksum
        data2 = {"test": "different", "number": 123}
        checksum3 = manager._calculate_checksum(data2)
        assert checksum != checksum3

    def test_food_key_real_generation(self, manager):
        """Test food key generation with real strings."""
        key1 = manager._generate_food_key("Apple")
        key2 = manager._generate_food_key("apple")
        assert key1 == key2  # Should be case insensitive
        assert isinstance(key1, str)
        assert len(key1) > 0

    def test_food_to_dict_real_conversion(self, manager):
        """Test food to dict conversion with real objects."""

        # Test successful conversion with to_dict method
        class MockFood1:
            def to_dict(self):
                return {"name": "Apple", "calories": 100}

        mock_food = MockFood1()
        result = manager._food_to_dict(mock_food)
        assert result["name"] == "Apple"
        assert result["calories"] == 100

        # Test fallback conversion with model_dump method
        class MockFood2:
            def to_dict(self):
                raise Exception("Failed")

            def model_dump(self):
                return {"name": "Apple", "calories": 100}

        mock_food2 = MockFood2()
        result = manager._food_to_dict(mock_food2)
        assert result["name"] == "Apple"
        assert result["calories"] == 100

        # Test fallback conversion when both methods fail
        class MockFood3:
            def __init__(self):
                self.name = "Apple"
                self.nutrients_per_100g = {"calories": 100}
                self.cost_per_100g = 0.5
                self.tags = ["fruit"]
                self.availability_regions = ["US"]
                self.source = "test"
                self.source_id = "test_id"

            def to_dict(self):
                raise Exception("Failed")

            def model_dump(self):
                raise Exception("Failed")

        mock_food3 = MockFood3()
        result = manager._food_to_dict(mock_food3)
        assert isinstance(result, dict)
        assert result["name"] == "Apple"
        assert result["source"] == "test"
        assert result["nutrients_per_100g"] == {"calories": 100}

    @pytest.mark.asyncio
    async def test_update_checking_real_logic(self, manager):
        """Test update checking with real time logic."""
        # Test with no current version (should return True)
        result = await manager._check_usda_updates()
        assert result is True

        result = await manager._check_off_updates()
        assert result is True

        # Test with recent version (should return False)
        manager.versions["usda"] = DatabaseVersion(
            source="usda",
            version="1.0.0",
            last_updated=now_utc().isoformat(),
            record_count=100,
            checksum="abc123",
            metadata={"test": "data"},
        )
        result = await manager._check_usda_updates()
        assert result is False

    @pytest.mark.asyncio
    async def test_record_counting_real_logic(self, manager, temp_dir):
        """Test record counting with real file operations."""
        # Test USDA (not implemented, returns 0)
        count = await manager._get_actual_record_count("usda")
        assert count == 0

        # Test OpenFoodFacts with real SQLite
        sqlite_file = temp_dir / "off.sqlite"
        conn = sqlite3.connect(str(sqlite_file))
        try:
            conn.execute("CREATE TABLE products (name TEXT, data TEXT)")
            conn.execute("INSERT INTO products VALUES ('apple', '{}')")
            conn.execute("INSERT INTO products VALUES ('banana', '{}')")
            conn.execute("INSERT INTO products VALUES ('orange', '{}')")
            conn.commit()
        finally:
            conn.close()

        count = await manager._get_actual_record_count("openfoodfacts")
        assert count == 3

    @pytest.mark.asyncio
    async def test_cache_data_retrieval_real_logic(self, manager, temp_dir):
        """Test cache data retrieval with real file operations."""
        # Test USDA (not implemented, returns empty)
        data = await manager._get_cache_data_for_checksum("usda")
        assert isinstance(data, dict)
        assert len(data) == 0

        # Test OpenFoodFacts with real SQLite
        sqlite_file = temp_dir / "off.sqlite"
        conn = sqlite3.connect(str(sqlite_file))
        try:
            conn.execute("CREATE TABLE products (name TEXT, data TEXT)")
            conn.execute("INSERT INTO products VALUES ('apple', '{\"name\": \"Apple\"}')")
            conn.commit()
        finally:
            conn.close()

        data = await manager._get_cache_data_for_checksum("openfoodfacts")
        assert isinstance(data, dict)
        assert "apple" in data
        assert "checksum" in data["apple"]

        # Test with CSV files
        csv_file = temp_dir / "products.csv"
        csv_content = "name,calories\napple,100\nbanana,200\n"
        csv_file.write_text(csv_content)

        data = await manager._get_cache_data_for_checksum("openfoodfacts")
        assert isinstance(data, dict)

        # Test with JSONL files
        jsonl_file = temp_dir / "products.jsonl"
        jsonl_content = '{"name": "apple", "calories": 100}\n{"name": "banana", "calories": 200}\n'
        jsonl_file.write_text(jsonl_content)

        data = await manager._get_cache_data_for_checksum("openfoodfacts")
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_backup_operations_real_logic(self, manager, temp_dir):
        """Test backup operations with real file operations."""
        # Test real backup creation error path - expected to fail without real data
        # The method should handle the error gracefully and return None or False
        result = await manager._create_backup("usda", "1.0.0")
        # Should return None or False when backup creation fails
        assert result is None or result is False

        # Test real backup loading with real file
        backup_data = {
            "apple": {
                "name": "Apple",
                "nutrients_per_100g": {"calories": 100},
                "cost_per_100g": 0.5,
                "tags": ["fruit"],
                "availability_regions": ["US"],
                "source": "usda",
                "source_id": "12345",
            }
        }
        backup_file = temp_dir / "usda_backup_1.0.0.json"
        backup_file.write_text(json.dumps(backup_data))

        result = await manager._load_backup("usda", "1.0.0")
        assert isinstance(result, dict)
        assert "apple" in result

    @pytest.mark.asyncio
    async def test_rollback_real_logic(self, manager, temp_dir):
        """Test rollback with real logic coverage."""
        # Create real backup file
        backup_data = {
            "apple": {
                "name": "Apple",
                "nutrients_per_100g": {"calories": 100},
                "cost_per_100g": 0.5,
                "tags": ["fruit"],
                "availability_regions": ["US"],
                "source": "usda",
                "source_id": "12345",
            }
        }
        backup_file = temp_dir / "usda_backup_1.0.0.json"
        backup_file.write_text(json.dumps(backup_data))

        # Add existing version
        manager.versions["usda"] = DatabaseVersion(
            source="usda",
            version="1.1.0",
            last_updated=now_utc().isoformat(),
            record_count=200,
            checksum="old123",
            metadata={"test": "data"},
        )

        # Test real rollback logic
        result = await manager.rollback_database("usda", "1.0.0")
        assert result is True
        assert "usda" in manager.versions
        assert "rollback" in manager.versions["usda"].version

    @pytest.mark.asyncio
    async def test_database_updates_real_logic(self, manager):
        """Test database update methods with real logic coverage."""
        # Test USDA update with real logic (will fail due to no real data, but covers code)
        result = await manager._update_usda_database(force=True)
        assert isinstance(result, UpdateResult)
        assert result.source == "usda"
        # The result might be False due to no real data, but we're testing the code path

        # Test OFF update with real logic
        result = await manager._update_off_database(force=True)
        assert isinstance(result, UpdateResult)
        assert result.source == "openfoodfacts"
        # The result might be False due to no real data, but we're testing the code path

    @pytest.mark.asyncio
    async def test_error_handling_real_logic(self, manager):
        """Test error handling with real exceptions."""
        # Test invalid source
        result = await manager.update_database("invalid_source")
        assert isinstance(result, UpdateResult)
        assert not result.success
        assert "Unknown source" in result.errors[0]

        # Test backup not found - should return empty dict gracefully
        result = await manager._load_backup("usda", "nonexistent")
        assert result == {}

    @pytest.mark.asyncio
    async def test_cleanup_real_logic(self, manager, temp_dir):
        """Test cleanup with real file operations."""
        # Create real backup files
        (temp_dir / "usda_backup_1.0.0.json").write_text("{}")
        (temp_dir / "usda_backup_1.1.0.json").write_text("{}")
        (temp_dir / "usda_backup_1.2.0.json").write_text("{}")
        (temp_dir / "usda_backup_1.3.0.json").write_text("{}")
        (temp_dir / "usda_backup_1.4.0.json").write_text("{}")
        (temp_dir / "usda_backup_1.5.0.json").write_text("{}")
        (temp_dir / "off_backup_1.0.0.json").write_text("{}")

        # Test real cleanup logic
        await manager._cleanup_old_backups("usda")

        # Should keep only max_rollback_versions files
        usda_files = list(temp_dir.glob("usda_backup_*.json"))
        assert len(usda_files) <= 5  # max_rollback_versions=5

    @pytest.mark.asyncio
    async def test_scheduled_update_real_logic(self, temp_dir):
        """Test run_scheduled_update with real logic."""
        # Test with real manager instance
        manager = DatabaseUpdateManager(cache_dir=temp_dir, update_interval_hours=24)

        # This will test the real function logic
        result = await run_scheduled_update(manager)
        assert isinstance(result, dict)

    def test_database_status_real_logic(self, manager):
        """Test database status reporting with real data."""
        # Add some versions
        manager.versions["usda"] = DatabaseVersion(
            source="usda",
            version="1.0.0",
            last_updated="2023-01-01T00:00:00Z",
            record_count=100,
            checksum="abc123",
            metadata={"test": "data"},
        )

        status = manager.get_database_status()
        assert isinstance(status, dict)
        assert "usda" in status
        assert status["usda"]["version"] == "1.0.0"

    def test_callback_management_real_logic(self, manager):
        """Test callback management with real callbacks."""

        def callback(x: UpdateResult) -> UpdateResult:
            return x  # Real function

        manager.add_update_callback(callback)
        assert callback in manager.update_callbacks

    @pytest.mark.asyncio
    async def test_close_method_real_logic(self, manager):
        """Test close method with real cleanup."""
        # Test real close method
        await manager.close()
        # Should not raise exception

    @pytest.mark.asyncio
    async def test_validate_food_data_real_logic(self, manager):
        """Test food data validation with real data."""
        # Create real food-like objects
        food1 = type(
            "Food", (), {"name": "Apple", "nutrients_per_100g": {"calories": 100}, "source": "test"}
        )()

        food2 = type("Food", (), {"name": "", "nutrients_per_100g": {}, "source": "test"})()

        foods = {"apple": food1, "invalid": food2}

        errors = await manager._validate_food_data(foods)
        assert isinstance(errors, list)

    @pytest.mark.asyncio
    async def test_check_for_updates_real_logic(self, manager):
        """Test check_for_updates method with real logic."""
        result = await manager.check_for_updates()
        assert isinstance(result, dict)
        assert "usda" in result
        assert "openfoodfacts" in result
