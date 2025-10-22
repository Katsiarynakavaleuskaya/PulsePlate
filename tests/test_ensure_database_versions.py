"""
Tests for scripts/ensure_database_versions.py

Tests the ensure_database_versions script including error paths for 97% coverage.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import pytest
import sys
import os

# Import the module under test
from scripts.ensure_database_versions import ensure_versions_file, main, DEFAULT_META


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
            temp_path = Path(temp_dir)
            # Create a marker file so repo root discovery succeeds
            (temp_path / ".git").mkdir()

            # Create the expected cache directory structure
            cache_dir = temp_path / "cache" / "food_db"
            cache_dir.mkdir(parents=True)

            # Create a mock script file path that points to our temp directory
            mock_script_path = temp_path / "scripts" / "ensure_database_versions.py"
            mock_script_path.parent.mkdir(parents=True)
            mock_script_path.touch()

            with patch("scripts.ensure_database_versions.__file__", str(mock_script_path)):
                result = main()
                assert result == 0

                # Verify the file was created in the correct location
                versions_file = cache_dir / "database_versions.json"
                assert versions_file.exists()

                # Verify the file has the correct content
                content = json.loads(versions_file.read_text(encoding="utf-8"))
                assert "openfoodfacts" in content
                assert content["openfoodfacts"]["version"] == "0.0.1"
                assert content["openfoodfacts"]["record_count"] == 0

    def test_main_fallback_repo_root(self) -> None:
        """Test fallback to parents[1] when no repo markers are found within depth limit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a deep nested path (>6) under temp_dir with no .git/pyproject.toml
            deep_dir = Path(temp_dir) / "a" / "b" / "c" / "d" / "e" / "f" / "g"
            deep_dir.mkdir(parents=True, exist_ok=True)

            # Patch module __file__ to point into the deep path
            with patch.object(
                sys.modules["scripts.ensure_database_versions"],
                "__file__",
                str(deep_dir / "dummy.py"),
            ):
                # Spy on ensure_versions_file to capture the target path
                with patch("scripts.ensure_database_versions.ensure_versions_file") as mock_ensure:
                    result = main()
                    assert result == 0
                    # Fallback uses parents[1] of the FILE path (dummy.py), not the directory
                    file_parents1 = Path(deep_dir / "dummy.py").resolve().parents[1]
                    expected = file_parents1 / "cache" / "food_db" / "database_versions.json"
                    mock_ensure.assert_called_once()
                    called_path = mock_ensure.call_args[0][0]
                    assert Path(called_path) == expected

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
