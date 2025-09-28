#!/usr/bin/env python3
"""
Test coverage for update_manager.py missing lines.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import json

from core.food_apis.update_manager import DatabaseUpdateManager


class TestUpdateManagerCoverage:
    """Test missing coverage lines in update_manager.py."""

    def test_sqlite_database_count(self):
        """Test SQLite database record counting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            sqlite_file = cache_dir / "off.sqlite"

            # Create mock SQLite database
            import sqlite3

            conn = sqlite3.connect(str(sqlite_file))
            conn.execute("CREATE TABLE products (id INTEGER, name TEXT)")
            conn.execute("INSERT INTO products VALUES (1, 'test1')")
            conn.execute("INSERT INTO products VALUES (2, 'test2')")
            conn.commit()
            conn.close()

            manager = DatabaseUpdateManager()
            count = manager._get_record_count("openfoodfacts", cache_dir)
            assert count == 2

    def test_glob_patterns_file_counting(self):
        """Test glob pattern file counting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            # Create test files
            test_files = [
                "test.openfoodfacts.org.products.csv",
                "test.openfoodfacts.org.products.jsonl",
                "test.openfoodfacts.org.products.ndjson",
                "off_test.jsonl",
            ]

            for filename in test_files:
                file_path = cache_dir / filename
                file_path.write_text("line1\nline2\nline3\n")

            manager = DatabaseUpdateManager()
            count = manager._get_record_count("openfoodfacts", cache_dir)
            assert count == 12  # 3 lines * 4 files

    def test_exception_handling_in_count(self):
        """Test exception handling in record counting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            # Create corrupted SQLite file
            sqlite_file = cache_dir / "off.sqlite"
            sqlite_file.write_text("corrupted data")

            manager = DatabaseUpdateManager()
            count = manager._get_record_count("openfoodfacts", cache_dir)
            assert count == 0  # Should return 0 on exception

    def test_checksum_calculation(self):
        """Test checksum calculation."""
        manager = DatabaseUpdateManager()

        # Test with sample data
        sample_data = {
            "source": "test",
            "version": "1.0.0",
            "record_count": 100,
            "metadata": {"test": "value"},
        }

        checksum = manager._calculate_checksum(sample_data)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex length

    def test_update_metadata_with_existing_data(self):
        """Test updating metadata with existing data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            versions_file = cache_dir / "database_versions.json"

            # Create existing metadata
            existing_data = {
                "openfoodfacts": {
                    "source": "openfoodfacts",
                    "version": "1.0.0",
                    "record_count": 50,
                    "checksum": "old_checksum",
                }
            }
            versions_file.write_text(json.dumps(existing_data))

            manager = DatabaseUpdateManager()

            # Mock the record count method
            with patch.object(manager, "_get_record_count", return_value=100):
                result = manager.update_metadata("openfoodfacts", cache_dir)

                assert result is True

                # Check that file was updated
                updated_data = json.loads(versions_file.read_text())
                assert updated_data["openfoodfacts"]["record_count"] == 100
                assert updated_data["openfoodfacts"]["checksum"] != "old_checksum"

    def test_update_metadata_new_source(self):
        """Test updating metadata for new source."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            versions_file = cache_dir / "database_versions.json"

            # Create empty metadata
            versions_file.write_text("{}")

            manager = DatabaseUpdateManager()

            # Mock the record count method
            with patch.object(manager, "_get_record_count", return_value=200):
                result = manager.update_metadata("usda", cache_dir)

                assert result is True

                # Check that new source was added
                updated_data = json.loads(versions_file.read_text())
                assert "usda" in updated_data
                assert updated_data["usda"]["record_count"] == 200

    def test_update_metadata_file_creation_error(self):
        """Test error handling when file creation fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            # Make cache_dir read-only to cause write error
            cache_dir.chmod(0o444)

            manager = DatabaseUpdateManager()

            with patch.object(manager, "_get_record_count", return_value=100):
                result = manager.update_metadata("test", cache_dir)

                assert result is False

    def test_get_record_count_unsupported_source(self):
        """Test get_record_count with unsupported source."""
        manager = DatabaseUpdateManager()

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            count = manager._get_record_count("unsupported", cache_dir)
            assert count == 0
