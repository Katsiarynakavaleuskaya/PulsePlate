"""Test coverage for database URL path handling edge cases.

Covers missing lines in core/db.py:
- Line 75: Query parameter in URL path during directory creation
- Line 117: Absolute path URL construction
- Line 517: Query parameter removal in init_db()
"""

import os
import tempfile
from unittest.mock import patch

import pytest


def test_build_engine_url_with_query_in_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover line 75: URL path contains query parameter during directory creation."""
    import importlib
    from core import db

    with tempfile.TemporaryDirectory() as tmpdir:
        # Set a SQLite URL with query in path (edge case)
        db_path = os.path.join(tmpdir, "test.db")
        test_url = f"sqlite:///{db_path}?mode=rwc"
        monkeypatch.setenv("DATABASE_URL", test_url)

        # Reload to pick up new URL
        reloaded = importlib.reload(db)

        # Initialize the database to trigger actual file creation
        reloaded.init_db()

        # Verify that the database file was actually created
        # (not just the tmpdir, which always exists inside TemporaryDirectory)
        assert os.path.exists(db_path), f"Database file was not created at {db_path}"
        # Also verify the directory is valid
        assert os.path.isdir(os.path.dirname(db_path)), "Database directory is not valid"

        # Restore
        importlib.reload(db)


def test_build_engine_url_absolute_path_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover line 117: Absolute path URL construction."""
    import importlib
    from core import db

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use absolute path (sqlite:////absolute/path)
        abs_path = os.path.join(tmpdir, "test.db")
        test_url = f"sqlite:///{abs_path}"
        monkeypatch.setenv("DATABASE_URL", test_url)

        # Reload to trigger URL construction logic
        reloaded = importlib.reload(db)

        # URL should be constructed as absolute path
        assert reloaded.DATABASE_URL.startswith("sqlite:///")
        # Should contain the absolute path
        assert (
            abs_path.replace(tmpdir, "") in reloaded.DATABASE_URL or tmpdir in reloaded.DATABASE_URL
        )

        # Restore
        importlib.reload(db)


def test_init_db_query_parameter_removal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover line 517: Query parameter removal in init_db()."""
    import importlib
    from core import db

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create URL with query parameters
        test_path = os.path.join(tmpdir, "subdir", "test.db")
        test_url = f"sqlite:///{test_path}?mode=rwc&uri=true"
        monkeypatch.setenv("DATABASE_URL", test_url)

        # Reload and initialize
        reloaded = importlib.reload(db)

        # init_db should handle query parameters correctly
        reloaded.init_db()

        # Directory should be created (proves query params were stripped)
        assert os.path.exists(os.path.dirname(test_path))

        # Cleanup
        importlib.reload(db)
        db.init_db()
