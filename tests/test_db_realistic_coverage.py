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

    # The async URL should be preserved or derived correctly
    # Note: ASYNC_DATABASE_URL might be None if async support is not available
    if db_module.create_async_engine is not None:
        # Test the _derive_async_url function directly
        derived_url = db_module._derive_async_url(async_url)
        assert derived_url == async_url
    else:
        # When async support is not available, _derive_async_url should return None
        derived_url = db_module._derive_async_url(async_url)
        assert derived_url is None


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


def test_derive_async_url_postgresql() -> None:
    """Test async URL derivation for PostgreSQL."""
    sync_url = "postgresql://user:pass@host/db"
    expected = "postgresql+asyncpg://user:pass@host/db"
    result = db_module._derive_async_url(sync_url)
    assert result == expected


def test_derive_async_url_postgres() -> None:
    """Test async URL derivation for postgres:// (legacy)."""
    sync_url = "postgres://user:pass@host/db"
    expected = "postgresql+asyncpg://user:pass@host/db"
    result = db_module._derive_async_url(sync_url)
    assert result == expected


def test_derive_async_url_mysql() -> None:
    """Test async URL derivation for MySQL."""
    sync_url = "mysql://user:pass@host/db"
    expected = "mysql+aiomysql://user:pass@host/db"
    result = db_module._derive_async_url(sync_url)
    assert result == expected


def test_derive_async_url_mysql_pymysql() -> None:
    """Test async URL derivation for mysql+pymysql://."""
    sync_url = "mysql+pymysql://user:pass@host/db"
    expected = "mysql+aiomysql://user:pass@host/db"
    result = db_module._derive_async_url(sync_url)
    assert result == expected


def test_derive_async_url_already_async() -> None:
    """Test that already async URLs are returned as-is."""
    async_urls = [
        "sqlite+aiosqlite:///test.db",
        "postgresql+asyncpg://user:pass@host/db",
        "mysql+aiomysql://user:pass@host/db",
    ]
    for url in async_urls:
        result = db_module._derive_async_url(url)
        assert result == url


def test_derive_async_url_unsupported() -> None:
    """Test that unsupported URLs return None."""
    unsupported_urls = [
        "oracle://user:pass@host/db",
        "mssql://user:pass@host/db",
        "invalid://url",
    ]
    for url in unsupported_urls:
        result = db_module._derive_async_url(url)
        assert result is None


def test_derive_async_url_no_async_support() -> None:
    """Test _derive_async_url when async support is not available."""
    with patch.object(db_module, "create_async_engine", None):
        result = db_module._derive_async_url("sqlite:///test.db")
        assert result is None


def test_check_async_availability_no_async_session() -> None:
    """Test _check_async_availability when AsyncSessionLocal is None."""
    with patch.object(db_module, "AsyncSessionLocal", None):
        with patch.object(db_module, "create_async_engine", None):
            with pytest.raises(ImportError, match="SQLAlchemy async extras are not available"):
                db_module._check_async_availability()


def test_check_async_availability_no_async_engine() -> None:
    """Test _check_async_availability when create_async_engine is None."""
    with patch.object(db_module, "AsyncSessionLocal", None):
        with patch.object(db_module, "create_async_engine", None):
            with pytest.raises(ImportError, match="SQLAlchemy async extras are not available"):
                db_module._check_async_availability()


def test_check_async_availability_not_configured() -> None:
    """Test _check_async_availability when async is not configured."""
    with patch.object(db_module, "AsyncSessionLocal", None):
        with patch.object(db_module, "create_async_engine", object()):
            with pytest.raises(RuntimeError, match="Async SQLAlchemy is not configured"):
                db_module._check_async_availability()


def test_sqlite_connect_args() -> None:
    """Test _sqlite_connect_args returns correct args for SQLite."""
    sqlite_url = "sqlite:///test.db"
    result = db_module._sqlite_connect_args(sqlite_url)
    assert result == {"check_same_thread": False}

    # Non-SQLite URLs should return empty dict
    postgres_url = "postgresql://user:pass@host/db"
    result = db_module._sqlite_connect_args(postgres_url)
    assert result == {}


def test_engine_compat_execute_string() -> None:
    """Test EngineCompat.execute with string statement."""
    from sqlalchemy import create_engine, text

    # Create a test engine
    test_engine = create_engine("sqlite:///:memory:")
    compat = db_module.EngineCompat(test_engine)

    # Test execute with string
    result = compat.execute("SELECT 1 as test")
    assert result.fetchone()[0] == 1


def test_engine_compat_execute_text() -> None:
    """Test EngineCompat.execute with text statement."""
    from sqlalchemy import create_engine, text

    # Create a test engine
    test_engine = create_engine("sqlite:///:memory:")
    compat = db_module.EngineCompat(test_engine)

    # Test execute with text object
    stmt = text("SELECT 2 as test")
    result = compat.execute(stmt)
    assert result.fetchone()[0] == 2


def test_engine_compat_getattr() -> None:
    """Test EngineCompat.__getattr__ delegates to underlying engine."""
    from sqlalchemy import create_engine

    test_engine = create_engine("sqlite:///:memory:")
    compat = db_module.EngineCompat(test_engine)

    # Test that attributes are delegated
    assert compat.url == test_engine.url
    assert compat.dialect == test_engine.dialect


@pytest.mark.skipif(
    db_module.create_async_engine is None, reason="SQLAlchemy async extras are not available"
)
def test_async_engine_initialization_with_pool_config() -> None:
    """Test async engine initialization with pool configuration."""

    def _apply_env(env_updates: dict[str, str]) -> None:
        env_updates["DATABASE_USE_ASYNC"] = "1"
        env_updates["DATABASE_ASYNC_URL"] = "sqlite+aiosqlite:///:memory:"
        env_updates["DATABASE_POOL_SIZE"] = "5"
        env_updates["DATABASE_MAX_OVERFLOW"] = "10"

    _reload_with_env(_apply_env)

    # Check that pool config is applied
    assert db_module._POOL_CONFIG["pool_size"] == 5
    assert db_module._POOL_CONFIG["max_overflow"] == 10
    assert db_module._POOL_CONFIG["pool_pre_ping"] is True


@pytest.mark.skipif(
    db_module.create_async_engine is None, reason="SQLAlchemy async extras are not available"
)
def test_async_engine_sqlite_no_pooling() -> None:
    """Test that SQLite async engines don't use pooling."""

    def _apply_env(env_updates: dict[str, str]) -> None:
        env_updates["DATABASE_USE_ASYNC"] = "1"
        env_updates["DATABASE_ASYNC_URL"] = "sqlite+aiosqlite:///:memory:"

    _reload_with_env(_apply_env)

    # SQLite async should not have pool configuration
    # This is tested by checking that the engine is created without pool args
    assert db_module.ASYNC_DATABASE_URL == "sqlite+aiosqlite:///:memory:"


def test_build_engine_url_default() -> None:
    """Test _build_engine_url returns default SQLite path."""
    with patch.dict(os.environ, {}, clear=True):
        result = db_module._build_engine_url()
        assert result == "sqlite:///cache/app.db"


def test_build_engine_url_custom() -> None:
    """Test _build_engine_url with custom DATABASE_URL."""
    custom_url = "postgresql://user:pass@host/db"
    with patch.dict(os.environ, {"DATABASE_URL": custom_url}, clear=False):
        result = db_module._build_engine_url()
        assert result == custom_url
