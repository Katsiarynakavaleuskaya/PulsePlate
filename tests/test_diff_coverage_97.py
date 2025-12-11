"""Tests to achieve 97% diff coverage.

Covers missing lines in:
- core/bayesian_recommendations.py (lines 311, 314, 319)
- core/fingerprint_security.py (lines 57, 63, 66, 72, 75, 79-80)
- core/db.py (lines 75, 117, 517)
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestBayesianRecommendations:
    """Test missing lines in core/bayesian_recommendations.py."""

    def test_get_symptom_key_none_symptom(self) -> None:
        """Test line 311: ValueError when symptom is None."""
        from core.bayesian_recommendations import get_symptom_key

        with pytest.raises(ValueError, match="Symptom cannot be None"):
            get_symptom_key(None)  # type: ignore

    def test_get_symptom_key_non_string_symptom(self) -> None:
        """Test line 314: ValueError when symptom is not a string."""
        from core.bayesian_recommendations import get_symptom_key

        with pytest.raises(ValueError, match="Symptom must be a string"):
            get_symptom_key(123)  # type: ignore

    def test_get_symptom_key_empty_symptom(self) -> None:
        """Test line 319: ValueError when symptom is empty or whitespace."""
        from core.bayesian_recommendations import get_symptom_key

        with pytest.raises(ValueError, match="Symptom cannot be empty or whitespace-only"):
            get_symptom_key("   ")


class TestFingerprintSecurity:
    """Test missing lines in core/fingerprint_security.py."""

    def test_load_salt_file_exists_returns_saved_value(self) -> None:
        """Existing non-empty salt file should be returned directly (line 57)."""
        from core.fingerprint_security import _load_salt_from_file

        with tempfile.TemporaryDirectory() as tmpdir:
            salt_file = Path(tmpdir) / "salt.txt"
            salt_file.parent.mkdir(parents=True, exist_ok=True)
            salt_file.write_text("existing_salt_value")

            result = _load_salt_from_file(salt_file)
            assert result == "existing_salt_value"

    def test_load_salt_file_exists_race_returns_existing_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FileExistsError race with non-empty file should return saved salt (line 57)."""
        from core.fingerprint_security import _load_salt_from_file

        with tempfile.TemporaryDirectory() as tmpdir:
            salt_file = Path(tmpdir) / "race_salt.txt"
            salt_file.parent.mkdir(parents=True, exist_ok=True)
            salt_file.write_text("race_existing_salt")

            original_exists = Path.exists
            original_open = Path.open
            original_read_text = Path.read_text

            def fake_exists(self: Path) -> bool:
                if self == salt_file:
                    return False
                return original_exists(self)

            def fake_open(self: Path, mode: str = "r", *args, **kwargs):
                if self == salt_file and "x" in mode:
                    raise FileExistsError("race")
                return original_open(self, mode, *args, **kwargs)

            def fake_read_text(self: Path, *args, **kwargs):
                if self == salt_file:
                    return "race_existing_salt"
                return original_read_text(self, *args, **kwargs)

            monkeypatch.setattr(Path, "exists", fake_exists)
            monkeypatch.setattr(Path, "open", fake_open)
            monkeypatch.setattr(Path, "read_text", fake_read_text)

            result = _load_salt_from_file(salt_file)
            assert result == "race_existing_salt"

    def test_load_salt_file_exists_race_empty_write_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty file in race path with write failure should still return generated salt (63-66)."""
        from core.fingerprint_security import _load_salt_from_file

        with tempfile.TemporaryDirectory() as tmpdir:
            salt_file = Path(tmpdir) / "race_empty_salt.txt"
            salt_file.parent.mkdir(parents=True, exist_ok=True)
            salt_file.touch()

            original_exists = Path.exists
            original_open = Path.open
            original_read_text = Path.read_text
            original_write_text = Path.write_text

            def fake_exists(self: Path) -> bool:
                if self == salt_file:
                    return False
                return original_exists(self)

            def fake_open(self: Path, mode: str = "r", *args, **kwargs):
                if self == salt_file and "x" in mode:
                    raise FileExistsError("race")
                return original_open(self, mode, *args, **kwargs)

            def fake_read_text(self: Path, *args, **kwargs):
                if self == salt_file:
                    return ""
                return original_read_text(self, *args, **kwargs)

            write_called = {"called": False}

            def fake_write_text(self: Path, data: str, *args, **kwargs):
                if self == salt_file:
                    write_called["called"] = True
                    raise RuntimeError("write failed")
                return original_write_text(self, data, *args, **kwargs)

            monkeypatch.setattr(Path, "exists", fake_exists)
            monkeypatch.setattr(Path, "open", fake_open)
            monkeypatch.setattr(Path, "read_text", fake_read_text)
            monkeypatch.setattr(Path, "write_text", fake_write_text)

            result = _load_salt_from_file(salt_file)
            assert write_called["called"] is True
            assert result is not None
            assert len(result) == 64

    def test_load_salt_file_exists_race_read_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Exceptions during read in race path should be handled (72-75)."""
        from core.fingerprint_security import _load_salt_from_file

        with tempfile.TemporaryDirectory() as tmpdir:
            salt_file = Path(tmpdir) / "race_read_error_salt.txt"
            salt_file.parent.mkdir(parents=True, exist_ok=True)
            salt_file.touch()

            original_exists = Path.exists
            original_open = Path.open
            original_read_text = Path.read_text

            def fake_exists(self: Path) -> bool:
                if self == salt_file:
                    return False
                return original_exists(self)

            def fake_open(self: Path, mode: str = "r", *args, **kwargs):
                if self == salt_file and "x" in mode:
                    raise FileExistsError("race")
                return original_open(self, mode, *args, **kwargs)

            def fake_read_text(self: Path, *args, **kwargs):
                if self == salt_file:
                    raise PermissionError("cannot read")
                return original_read_text(self, *args, **kwargs)

            monkeypatch.setattr(Path, "exists", fake_exists)
            monkeypatch.setattr(Path, "open", fake_open)
            monkeypatch.setattr(Path, "read_text", fake_read_text)

            result = _load_salt_from_file(salt_file)
            assert result is not None
            assert len(result) == 64

    def test_load_salt_final_chmod_os_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Bottom chmod OSError should be ignored (79-80)."""
        from core.fingerprint_security import _load_salt_from_file

        with tempfile.TemporaryDirectory() as tmpdir:
            salt_file = Path(tmpdir) / "chmod_error_salt.txt"

            original_chmod = Path.chmod

            def fake_chmod(self: Path, mode: int) -> None:
                if self == salt_file:
                    raise OSError("no chmod")
                return original_chmod(self, mode)

            with patch.object(Path, "chmod", fake_chmod):
                result = _load_salt_from_file(salt_file)
                assert result is not None
                assert len(result) == 64


class TestDb:
    """Test missing lines in core/db.py."""

    def test_build_engine_url_with_query_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test line 75: Handle database URL with query parameters."""
        # Test SQLite URL with query parameters
        test_url = "sqlite:///test.db?mode=ro&cache=shared"
        monkeypatch.setenv("DATABASE_URL", test_url)

        # Import fresh to get the function with mocked env
        from core.db import _build_engine_url

        # Should parse and handle query parameters correctly
        result = _build_engine_url()
        assert "sqlite:///" in result

    def test_build_engine_url_absolute_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test line 117: Handle absolute SQLite path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use absolute path
            abs_path = os.path.join(tmpdir, "test.db")
            test_url = f"sqlite:///{abs_path}"
            monkeypatch.setenv("DATABASE_URL", test_url)

            # Import fresh to get the function with mocked env
            from core.db import _build_engine_url

            result = _build_engine_url()
            # Should keep absolute path format
            assert "sqlite:///" in result

    def test_init_db_with_query_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test line 517: init_db handles URL with query parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_db_path = os.path.join(tmpdir, "test.db")
            test_url = f"sqlite:///{test_db_path}?mode=rwc"
            monkeypatch.setenv("DATABASE_URL", test_url)

            # Import fresh to get the function with mocked env
            from core.db import init_db

            # Should handle query parameters in URL
            init_db()
            # Verify database was created
            assert os.path.exists(test_db_path)
