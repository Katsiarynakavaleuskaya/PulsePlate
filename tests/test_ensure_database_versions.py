"""
Tests for scripts/ensure_database_versions.py

Tests the ensure_database_versions script including error paths for 97% coverage.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest
import importlib.util
import sys

# Import the module under test using importlib
spec = importlib.util.spec_from_file_location(
    "ensure_database_versions",
    Path(__file__).parent.parent / "scripts" / "ensure_database_versions.py",
)
if spec is None or spec.loader is None:
    raise ImportError("Could not load ensure_database_versions module")
ensure_database_versions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ensure_database_versions)
sys.modules["scripts.ensure_database_versions"] = ensure_database_versions

ensure_versions_file = ensure_database_versions.ensure_versions_file
main = ensure_database_versions.main
DEFAULT_META = ensure_database_versions.DEFAULT_META


class TestEnsureDatabaseVersions:
    """Test ensure_database_versions functionality."""

    def test_ensure_versions_file_existing_file(self) -> None:
        """Test that existing file is not overwritten."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "database_versions.json"

            # Create existing file with different content
            existing_content = {"existing": "data"}
            test_path.write_text(json.dumps(existing_content), encoding="utf-8")

            # Call function - should not modify existing file
            ensure_versions_file(test_path)

            # Verify file content unchanged
            result = json.loads(test_path.read_text(encoding="utf-8"))
            assert result == existing_content

    def test_ensure_versions_file_creates_new_file(self) -> None:
        """Test that new file is created with default metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "database_versions.json"

            # Call function
            ensure_versions_file(test_path)

            # Verify file was created with correct content
            assert test_path.exists()
            result = json.loads(test_path.read_text(encoding="utf-8"))
            assert result == DEFAULT_META

    def test_ensure_versions_file_creates_parent_directories(self) -> None:
        """Test that parent directories are created if they don't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "nested" / "deep" / "database_versions.json"

            # Call function
            ensure_versions_file(test_path)

            # Verify file and directories were created
            assert test_path.exists()
            assert test_path.parent.exists()
            result = json.loads(test_path.read_text(encoding="utf-8"))
            assert result == DEFAULT_META

    def test_ensure_versions_file_oserror_on_mkdir(self) -> None:
        """Test OSError handling when mkdir fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "database_versions.json"

            # Mock mkdir to raise OSError
            with patch.object(Path, "mkdir", side_effect=OSError("Permission denied")):
                with pytest.raises(OSError, match="Permission denied"):
                    ensure_versions_file(test_path)

    def test_ensure_versions_file_oserror_on_write(self) -> None:
        """Test OSError handling when write_text fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "database_versions.json"

            # Mock write_text to raise OSError
            with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
                with pytest.raises(OSError, match="Disk full"):
                    ensure_versions_file(test_path)

    def test_ensure_versions_file_permission_error(self) -> None:
        """Test PermissionError handling (subclass of OSError)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "database_versions.json"

            # Mock write_text to raise PermissionError
            with patch.object(Path, "write_text", side_effect=PermissionError("Access denied")):
                with pytest.raises(PermissionError, match="Access denied"):
                    ensure_versions_file(test_path)

    def test_main_success(self) -> None:
        """Test main function success path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the repo root to point to temp directory
            with patch("scripts.ensure_database_versions.Path") as mock_path:
                mock_path.return_value.parents = [Path(temp_dir)]
                mock_path.return_value.resolve.return_value = Path(temp_dir)

                result = main()
                assert result == 0

    def test_main_with_oserror(self) -> None:
        """Test main function with OSError propagation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the repo root to point to temp directory
            with patch("scripts.ensure_database_versions.Path") as mock_path:
                mock_path.return_value.parents = [Path(temp_dir)]
                mock_path.return_value.resolve.return_value = Path(temp_dir)

                # Mock ensure_versions_file to raise OSError
                with patch(
                    "scripts.ensure_database_versions.ensure_versions_file",
                    side_effect=OSError("Mocked error"),
                ):
                    with pytest.raises(OSError, match="Mocked error"):
                        main()

    def test_default_meta_structure(self) -> None:
        """Test that DEFAULT_META has correct structure."""
        assert isinstance(DEFAULT_META, dict)
        assert "openfoodfacts" in DEFAULT_META

        off_data = DEFAULT_META["openfoodfacts"]
        required_fields = [
            "source",
            "version",
            "last_updated",
            "record_count",
            "checksum",
            "metadata",
        ]

        for field in required_fields:
            assert field in off_data, f"Missing required field: {field}"

        assert off_data["source"] == "openfoodfacts"
        assert off_data["version"] == "0.0.1"
        assert off_data["record_count"] == 0
        assert isinstance(off_data["metadata"], dict)

    def test_json_serialization(self) -> None:
        """Test that DEFAULT_META can be serialized to JSON."""
        json_str = json.dumps(DEFAULT_META, ensure_ascii=False, indent=2)
        assert isinstance(json_str, str)

        # Verify it can be deserialized
        parsed = json.loads(json_str)
        assert parsed == DEFAULT_META
