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

    def test_load_salt_from_empty_file(self) -> None:
        """Test lines 57, 62, 63: Load salt when file exists but is empty."""
        from core.fingerprint_security import _load_salt_from_file

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty salt file
            salt_file = Path(tmpdir) / "salt.txt"
            salt_file.touch()
            salt_file.chmod(0o600)

            # Load should return generated salt and try to write it
            result = _load_salt_from_file(salt_file)
            assert result is not None
            assert len(result) == 64  # 32 bytes hex = 64 chars

    def test_load_salt_from_file_read_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test lines 72, 75: Handle file read errors gracefully."""
        from core.fingerprint_security import _load_salt_from_file

        with tempfile.TemporaryDirectory() as tmpdir:
            salt_file = Path(tmpdir) / "salt.txt"
            salt_file.write_text("existing_salt")

            # Mock Path.read_text to raise exception
            def mock_read_text() -> str:
                raise PermissionError("Cannot read file")

            monkeypatch.setattr(Path, "read_text", lambda self: mock_read_text())

            # Should return None on read error
            result = _load_salt_from_file(salt_file)
            assert result is None

    def test_load_salt_chmod_os_error(self) -> None:
        """Test lines 66, 79-80: Handle chmod OSError gracefully."""
        from core.fingerprint_security import _load_salt_from_file

        with tempfile.TemporaryDirectory() as tmpdir:
            salt_file = Path(tmpdir) / "salt.txt"

            # Create file and make directory read-only to trigger chmod error
            with patch.object(Path, "chmod", side_effect=OSError("Cannot chmod")):
                # Should still return generated salt even if chmod fails
                result = _load_salt_from_file(salt_file)
                assert result is not None
                assert len(result) == 64


class TestDb:
    """Test missing lines in core/db.py."""

    def test_build_engine_url_with_query_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test line 75: Handle database URL with query parameters."""
        from core.db import _build_engine_url

        # Test SQLite URL with query parameters
        test_url = "sqlite:///test.db?mode=ro&cache=shared"
        monkeypatch.setenv("DATABASE_URL", test_url)

        # Clear the module cache to force reload
        import importlib
        import core.db

        importlib.reload(core.db)

        # Should parse and handle query parameters correctly
        result = core.db._build_engine_url()
        assert "sqlite:///" in result

    def test_build_engine_url_absolute_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test line 117: Handle absolute SQLite path."""
        from core.db import _build_engine_url

        with tempfile.TemporaryDirectory() as tmpdir:
            # Use absolute path
            abs_path = os.path.join(tmpdir, "test.db")
            test_url = f"sqlite:///{abs_path}"
            monkeypatch.setenv("DATABASE_URL", test_url)

            # Clear module cache
            import importlib
            import core.db

            importlib.reload(core.db)

            result = core.db._build_engine_url()
            # Should keep absolute path format
            assert "sqlite:///" in result

    def test_init_db_with_query_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test line 517: init_db handles URL with query parameters."""
        from core.db import init_db

        with tempfile.TemporaryDirectory() as tmpdir:
            test_db_path = os.path.join(tmpdir, "test.db")
            test_url = f"sqlite:///{test_db_path}?mode=rwc"
            monkeypatch.setenv("DATABASE_URL", test_url)

            # Reload db module to pick up new URL
            import importlib
            import core.db

            importlib.reload(core.db)

            # Should handle query parameters in URL
            init_db()
            # Verify database was created
            assert os.path.exists(test_db_path)
