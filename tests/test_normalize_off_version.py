"""Tests for scripts/normalize_off_version.py"""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

# Import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import normalize_off_version


@pytest.fixture
def temp_versions_file(tmp_path):
    """Create a temporary versions file for testing."""
    versions_file = tmp_path / "database_versions.json"
    return versions_file


@pytest.fixture
def mock_vers_path(temp_versions_file, monkeypatch):
    """Mock the VERS global variable to use a temp file."""
    monkeypatch.setattr(normalize_off_version, "VERS", temp_versions_file)
    return temp_versions_file


class TestAtomicWriteJson:
    """Tests for _atomic_write_json function."""

    def test_atomic_write_json_creates_file(self, tmp_path):
        """Test that _atomic_write_json creates a new file with correct content."""
        target = tmp_path / "test.json"
        data = {"test": "data", "number": 42}

        normalize_off_version._atomic_write_json(target, data)

        assert target.exists()
        content = json.loads(target.read_text(encoding="utf-8"))
        assert content == data

    def test_atomic_write_json_with_database_versions_dict(self, tmp_path):
        """Test _atomic_write_json with DatabaseVersionsDict type."""
        target = tmp_path / "versions.json"
        data = normalize_off_version.DEFAULT_DATABASE_METADATA

        normalize_off_version._atomic_write_json(target, data)

        assert target.exists()
        content = json.loads(target.read_text(encoding="utf-8"))
        assert "openfoodfacts" in content

    def test_atomic_write_json_creates_parent_directory(self, tmp_path):
        """Test that _atomic_write_json creates parent directories if they don't exist."""
        target = tmp_path / "subdir" / "deep" / "test.json"
        data = {"nested": "path"}

        normalize_off_version._atomic_write_json(target, data)

        assert target.exists()
        assert target.parent.exists()


class TestWriteLogFile:
    """Tests for write_log_file function."""

    def test_write_log_file_creates_log(self, tmp_path, monkeypatch):
        """Test that write_log_file creates a log file with content."""
        monkeypatch.chdir(tmp_path)
        content = "Test log content\nMultiple lines\nWith data"

        log_file = normalize_off_version.write_log_file(content, prefix="test_prefix")

        assert log_file is not None
        assert log_file.exists()
        assert log_file.name.startswith("test_prefix_")
        assert log_file.suffix == ".log"
        assert log_file.read_text(encoding="utf-8") == content

    def test_write_log_file_creates_logs_directory(self, tmp_path, monkeypatch):
        """Test that write_log_file creates the logs directory if it doesn't exist."""
        monkeypatch.chdir(tmp_path)
        content = "Test content"

        log_file = normalize_off_version.write_log_file(content)

        assert log_file is not None
        assert (tmp_path / "logs").exists()
        # log_file is relative path, so check that logs directory was created
        assert log_file.parent.name == "logs"

    def test_write_log_file_with_unicode_content(self, tmp_path, monkeypatch):
        """Test that write_log_file handles unicode content correctly."""
        monkeypatch.chdir(tmp_path)
        content = "Test content with unicode: 你好世界 🎉"

        log_file = normalize_off_version.write_log_file(content)

        assert log_file is not None
        written_content = log_file.read_text(encoding="utf-8")
        assert written_content == content


class TestLogValidationError:
    """Tests for _log_validation_error function."""

    def test_log_validation_error_logs_message(self, tmp_path, monkeypatch, caplog):
        """Test that _log_validation_error logs the error message."""
        monkeypatch.chdir(tmp_path)

        normalize_off_version._log_validation_error(
            error_type="Test Error",
            error_details="Details about error",
            stdout="stdout content",
            stderr="stderr content",
            prefix="test_error",
        )

        assert "Test Error" in caplog.text
        assert "Details about error" in caplog.text

    def test_log_validation_error_truncates_long_output(self, tmp_path, monkeypatch, caplog):
        """Test that _log_validation_error truncates long stdout/stderr."""
        monkeypatch.chdir(tmp_path)
        long_stdout = "x" * 2000
        long_stderr = "y" * 2000

        normalize_off_version._log_validation_error(
            error_type="Long Output Error",
            error_details="Test truncation",
            stdout=long_stdout,
            stderr=long_stderr,
            prefix="test_truncate",
        )

        assert "(truncated, see full log)" in caplog.text


class TestSetVersion:
    """Tests for set_version function."""

    def test_set_version_creates_default_file_if_missing(self, mock_vers_path):
        """Test that set_version creates a default file if it doesn't exist."""
        assert not mock_vers_path.exists()

        normalize_off_version.set_version("1.2.3")

        assert mock_vers_path.exists()
        content = json.loads(mock_vers_path.read_text(encoding="utf-8"))
        assert content["openfoodfacts"]["version"] == "1.2.3"

    def test_set_version_updates_existing_file(self, mock_vers_path):
        """Test that set_version updates an existing file."""
        # Create initial file
        initial_data = {
            "openfoodfacts": {
                "source": "openfoodfacts",
                "version": "0.0.1",
                "last_updated": "2024-01-01",
                "record_count": 100,
                "checksum": "abc123",
                "metadata": {},
            }
        }
        mock_vers_path.write_text(json.dumps(initial_data), encoding="utf-8")

        # Update version
        normalize_off_version.set_version("2.0.0")

        # Verify update
        content = json.loads(mock_vers_path.read_text(encoding="utf-8"))
        assert content["openfoodfacts"]["version"] == "2.0.0"
        # Other fields should be preserved
        assert content["openfoodfacts"]["record_count"] == 100

    def test_set_version_handles_malformed_data(self, mock_vers_path, caplog):
        """Test that set_version handles malformed JSON data gracefully."""
        # Write non-dict data
        mock_vers_path.write_text(json.dumps("not a dict"), encoding="utf-8")

        normalize_off_version.set_version("1.0.0")

        # Should replace with default structure
        content = json.loads(mock_vers_path.read_text(encoding="utf-8"))
        assert isinstance(content, dict)
        assert content["openfoodfacts"]["version"] == "1.0.0"
        assert "non-dict data" in caplog.text

    def test_set_version_handles_missing_openfoodfacts_key(self, mock_vers_path, caplog):
        """Test that set_version handles missing openfoodfacts key."""
        mock_vers_path.write_text(json.dumps({"other_key": "value"}), encoding="utf-8")

        normalize_off_version.set_version("1.0.0")

        content = json.loads(mock_vers_path.read_text(encoding="utf-8"))
        assert "openfoodfacts" in content
        assert content["openfoodfacts"]["version"] == "1.0.0"


class TestValidate:
    """Tests for validate function."""

    @patch("subprocess.run")
    def test_validate_returns_0_on_success(self, mock_run):
        """Test that validate returns 0 when validation succeeds."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"success": true}',
            stderr="",
        )

        result = normalize_off_version.validate()

        assert result == 0
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_validate_returns_1_on_non_zero_returncode(self, mock_run, tmp_path, monkeypatch):
        """Test that validate returns 1 when subprocess returns non-zero."""
        monkeypatch.chdir(tmp_path)
        mock_run.return_value = Mock(
            returncode=1,
            stdout="error output",
            stderr="error details",
        )

        result = normalize_off_version.validate()

        assert result == 1

    @patch("subprocess.run")
    def test_validate_returns_1_on_json_parse_error(self, mock_run, tmp_path, monkeypatch):
        """Test that validate returns 1 when JSON parsing fails."""
        monkeypatch.chdir(tmp_path)
        mock_run.return_value = Mock(
            returncode=0,
            stdout="not valid json",
            stderr="",
        )

        result = normalize_off_version.validate()

        assert result == 1

    @patch("subprocess.run")
    def test_validate_returns_1_when_success_not_true(self, mock_run, tmp_path, monkeypatch):
        """Test that validate returns 1 when success field is not true."""
        monkeypatch.chdir(tmp_path)
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"success": false, "error": "validation failed"}',
            stderr="",
        )

        result = normalize_off_version.validate()

        assert result == 1

    @patch("subprocess.run")
    def test_validate_handles_timeout(self, mock_run):
        """Test that validate handles timeout gracefully."""
        mock_process = Mock()
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=30)
        mock_run.side_effect.process = mock_process

        result = normalize_off_version.validate()

        assert result == 1

    @patch("subprocess.run")
    def test_validate_handles_file_not_found(self, mock_run):
        """Test that validate handles FileNotFoundError."""
        mock_run.side_effect = FileNotFoundError()

        result = normalize_off_version.validate()

        assert result == 1

    @patch("subprocess.run")
    def test_validate_handles_os_error(self, mock_run):
        """Test that validate handles OSError."""
        mock_run.side_effect = OSError("Test error")

        result = normalize_off_version.validate()

        assert result == 1


class TestMain:
    """Tests for main function."""

    @patch("normalize_off_version.validate")
    @patch("normalize_off_version.set_version")
    def test_main_returns_0_on_first_valid_candidate(
        self, mock_set_version, mock_validate, mock_vers_path
    ):
        """Test that main returns 0 when first candidate is valid."""
        mock_validate.return_value = 0

        result = normalize_off_version.main()

        assert result == 0
        mock_set_version.assert_called_once()
        mock_validate.assert_called_once()

    @patch("normalize_off_version.validate")
    @patch("normalize_off_version.set_version")
    def test_main_tries_all_candidates_if_needed(
        self, mock_set_version, mock_validate, mock_vers_path
    ):
        """Test that main tries all candidates until one succeeds."""
        # Make first two candidates fail, third succeed
        mock_validate.side_effect = [1, 1, 0]

        result = normalize_off_version.main()

        assert result == 0
        assert mock_set_version.call_count == 3
        assert mock_validate.call_count == 3

    @patch("normalize_off_version.validate")
    @patch("normalize_off_version.set_version")
    def test_main_returns_2_when_all_candidates_fail(
        self, mock_set_version, mock_validate, mock_vers_path
    ):
        """Test that main returns 2 when all candidates fail."""
        mock_validate.return_value = 1

        result = normalize_off_version.main()

        assert result == 2
        # Should try all candidates
        assert mock_set_version.call_count == len(normalize_off_version.CANDIDATES)

    @patch("normalize_off_version.CANDIDATES", [])
    def test_main_returns_2_when_no_candidates(self, caplog):
        """Test that main returns 2 when CANDIDATES list is empty."""
        result = normalize_off_version.main()

        assert result == 2
        assert "no candidates provided" in caplog.text
