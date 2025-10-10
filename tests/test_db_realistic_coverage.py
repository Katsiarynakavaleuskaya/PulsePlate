"""Coverage-focused tests for ``core.db`` async URL handling."""

from __future__ import annotations

from collections.abc import Callable
import importlib
import os
from pathlib import Path
from unittest.mock import patch

import pytest

import core.db as db_module


def _reload_with_env(env_builder: Callable[[dict[str, str]], None]) -> None:
    """Reload ``core.db`` under a temporary environment configuration."""
    env_updates: dict[str, str] = {}
    env_builder(env_updates)
    with patch.dict(os.environ, env_updates, clear=False):
        try:
            importlib.reload(db_module)
        except ImportError:
            # Skip reload if module is not available
            pass


def _restore_core_db() -> None:
    """Restore ``core.db`` to its default module state."""
    try:
        importlib.reload(db_module)
    except ImportError:
        # Skip reload if module is not available
        pass


@pytest.fixture(autouse=True)
def _core_db_cleanup():
    """Ensure ``core.db`` is reset after each test case."""
    yield
    _restore_core_db()


@pytest.mark.skipif(
    db_module.create_async_engine is None, reason="SQLAlchemy async extras are not available"
)
@pytest.mark.parametrize(
    "async_url",
    [
        "sqlite+aiosqlite:///tmp/app.db",
        "postgresql+asyncpg://user:pass@host/db",
        "mysql+aiomysql://user:pass@host/db",
    ],
)
def test_async_database_url_preserves_explicit_async_inputs(tmp_path: Path, async_url: str) -> None:
    """Explicitly set async DATABASE_ASYNC_URL should pass through untouched."""

    def _apply_env(env_updates: dict[str, str]) -> None:
        env_updates["DATABASE_USE_ASYNC"] = "1"
        env_updates["DATABASE_ASYNC_URL"] = async_url
        env_updates["DATABASE_URL"] = f"sqlite:///{tmp_path / 'test.db'}"

    _reload_with_env(_apply_env)

    assert db_module.ASYNC_DATABASE_URL == async_url


@pytest.mark.skipif(
    db_module.create_async_engine is None, reason="SQLAlchemy async extras are not available"
)
def test_async_database_url_derives_from_sqlite_url(tmp_path: Path) -> None:
    """SQLite synchronous URLs should be converted to async variants when deriving."""
    sqlite_path = tmp_path / "test.db"
    sync_url = f"sqlite:///{sqlite_path}"
    expected = f"sqlite+aiosqlite:///{sqlite_path}"

    def _apply_env(env_updates: dict[str, str]) -> None:
        env_updates["DATABASE_USE_ASYNC"] = "1"
        env_updates["DATABASE_ASYNC_URL"] = ""
        env_updates["DATABASE_URL"] = sync_url

    _reload_with_env(_apply_env)

    assert db_module.ASYNC_DATABASE_URL == expected


@pytest.mark.skipif(
    db_module.create_async_engine is None, reason="SQLAlchemy async extras are not available"
)
def test_async_database_url_derives_when_flag_enabled(tmp_path: Path) -> None:
    """``ASYNC_DATABASE_URL`` should derive from ``DATABASE_URL`` when async flag is enabled."""
    sqlite_path = tmp_path / "async.db"

    def _apply_env(env_updates: dict[str, str]) -> None:
        env_updates["DATABASE_USE_ASYNC"] = "1"
        env_updates["DATABASE_ASYNC_URL"] = ""
        env_updates["DATABASE_URL"] = f"sqlite:///{sqlite_path}"

    _reload_with_env(_apply_env)

    expected = f"sqlite+aiosqlite:///{sqlite_path}"
    assert db_module.ASYNC_DATABASE_URL == expected
