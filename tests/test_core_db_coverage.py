# -*- coding: utf-8 -*-
"""
Core DB Tests

RU: Тесты для основных функций базы данных
EN: Tests for core database functionality
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from core.db import (
    Base,
    _RAW_ENGINE,
    _build_engine_url,
    _sqlite_connect_args,
    _derive_async_url,
    async_engine,
    get_async_session,
    get_session,
    init_db,
    init_db_async,
    session_scope,
    session_scope_async,
)

# NOTE: SessionLocal is NOT imported at module level to avoid caching None value
# when reset_db_for_tests() is called. Use dynamic import inside tests instead.


class TestCoreDB:
    """Tests for core database functions."""

    def test_build_engine_url_default(self):
        """Test _build_engine_url with default SQLite path."""
        with patch.dict(os.environ, {}, clear=True):
            url = _build_engine_url()
            assert url.startswith("sqlite:///")
            assert "cache/app.db" in url

    def test_build_engine_url_custom(self):
        """Test _build_engine_url with custom DATABASE_URL."""
        custom_url = "postgresql://user:pass@localhost/testdb"
        with patch.dict(os.environ, {"DATABASE_URL": custom_url}):
            url = _build_engine_url()
            assert url == custom_url

    def test_sqlite_connect_args_sqlite(self):
        """Test _sqlite_connect_args for SQLite URLs."""
        sqlite_url = "sqlite:///test.db"
        args = _sqlite_connect_args(sqlite_url)
        assert args == {"check_same_thread": False, "timeout": 5.0}

    def test_sqlite_connect_args_non_sqlite(self):
        """Test _sqlite_connect_args for non-SQLite URLs."""
        postgres_url = "postgresql://user:pass@localhost/db"
        args = _sqlite_connect_args(postgres_url)
        assert args == {}

    def test_base_class(self):
        """Test Base declarative class."""
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")

    def test_session_local_creation(self):
        """Test SessionLocal sessionmaker creation."""
        # Ensure DB is initialized (SessionLocal may be None if reset_db_for_tests was called)
        from core import db

        if db.SessionLocal is None:
            db.init_db()
        # Use dynamic import to get current value
        from core.db import SessionLocal as current_session_local

        assert current_session_local is not None
        assert hasattr(current_session_local, "__call__")

    def test_get_session_generator(self):
        """Test get_session dependency yields session."""
        session_gen = get_session()
        session = next(session_gen)
        assert session is not None
        assert hasattr(session, "query")
        assert hasattr(session, "commit")

        # Close the session properly
        try:
            next(session_gen)
        except StopIteration:
            pass  # Expected

    def test_session_scope_success(self):
        """Test session_scope context manager success path."""
        with session_scope() as session:
            assert session is not None
            assert hasattr(session, "query")
            assert hasattr(session, "commit")
            # Don't do any actual DB operations

    def test_session_scope_exception(self):
        """Test session_scope context manager exception handling."""
        with pytest.raises(ValueError):
            with session_scope() as session:
                assert session is not None
                # Simulate an error
                raise ValueError("Test error")

    def test_init_db(self):
        """Test init_db creates tables."""
        from core import db
        from sqlalchemy.schema import MetaData

        # RU: Этот тест временно инициализирует DB в памяти и обязан восстановить
        # окружение/глобалы, иначе он ломает API-тесты в xdist (order-dependent).
        # EN: This test temporarily initializes an in-memory DB and must restore
        # env/module globals, otherwise it breaks API tests under xdist.
        original_db_url = os.environ.get("DATABASE_URL")

        # Ensure init_db goes through the "first init" path
        db.reset_db_for_tests()

        try:
            # Patch create_all on MetaData class (Base.metadata is a MetaData instance)
            # This is the canonical way to mock SQLAlchemy 2.x metadata methods
            with patch.object(MetaData, "create_all") as mock_create_all:
                db.init_db("sqlite:///:memory:")
                # Verify create_all was called once
                mock_create_all.assert_called_once()
        finally:
            # RU: Сбросить engine/sessionmaker, чтобы не "утекла" in-memory DB конфигурация.
            # EN: Reset engine/sessionmaker so in-memory DB config cannot leak.
            db.reset_db_for_tests()

            # RU/EN: Restore env and re-init DB using canonical DATABASE_URL from conftest.
            if original_db_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = original_db_url
            # Re-initialize DB for the rest of the suite (session-scoped fixtures won't rerun).
            db.init_db()

    def test_init_db_with_models_import(self):
        """Test init_db imports models correctly."""
        # This tests the lazy import of core.models
        try:
            init_db()
            # Should not raise ImportError
        except ImportError:
            # If models don't exist, that's okay for this test
            pass

    def test_database_url_sqlite_format(self):
        """Test get_database_url() returns properly formatted URL for SQLite."""
        from core.db import get_database_url

        # Should be valid URL format
        database_url = get_database_url()
        assert isinstance(database_url, str)
        assert len(database_url) > 0

    def test_engine_creation(self):
        """Test engine is created properly."""
        from core.db import engine

        assert engine is not None
        assert hasattr(engine, "connect")
        assert hasattr(engine, "execute")

    def test_session_configuration(self):
        """Test SessionLocal is configured correctly."""
        # Ensure DB is initialized
        from core import db

        if db.SessionLocal is None:
            db.init_db()
        # Use dynamic import to get current value
        from core.db import SessionLocal as current_session_local

        # Test that SessionLocal has expected configuration
        session = current_session_local()
        assert session is not None
        session.close()

    def test_session_scope_rollback(self):
        """Test session_scope rolls back on exception."""
        try:
            from sqlalchemy import text as sa_text
        except Exception:

            def sa_text(s):
                return s  # fallback for environments without SQLAlchemy types

        try:
            with session_scope() as session:
                # Force an exception to test rollback
                session.execute(sa_text("INVALID SQL"))
        except Exception:
            # Exception is expected
            pass

    def test_environment_variable_handling(self):
        """Test environment variable handling in URL building."""
        # Test with different environment setups
        test_urls = ["sqlite:///memory:", "postgresql://localhost/test", "mysql://localhost/test"]

        for test_url in test_urls:
            with patch.dict(os.environ, {"DATABASE_URL": test_url}):
                url = _build_engine_url()
                assert url == test_url

    def test_sqlite_file_path_creation(self):
        """Test SQLite file path handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "test.db")
            test_url = f"sqlite:///{test_path}"

            args = _sqlite_connect_args(test_url)
            assert args["check_same_thread"] is False


class TestAsyncDB:
    """Tests for async database functions."""

    def test_derive_async_url_sqlite(self):
        """Test _derive_async_url for SQLite URLs."""
        sqlite_url = "sqlite:///test.db"
        async_url = _derive_async_url(sqlite_url)
        assert async_url == "sqlite+aiosqlite:///test.db"

    def test_derive_async_url_postgresql(self):
        """Test _derive_async_url for PostgreSQL URLs."""
        pg_url = "postgresql://user:pass@localhost/testdb"
        async_url = _derive_async_url(pg_url)
        assert async_url == "postgresql+asyncpg://user:pass@localhost/testdb"

    def test_derive_async_url_mysql(self):
        """Test _derive_async_url for MySQL URLs."""
        mysql_url = "mysql://user:pass@localhost/testdb"
        async_url = _derive_async_url(mysql_url)
        assert async_url == "mysql+aiomysql://user:pass@localhost/testdb"

    def test_derive_async_url_already_async(self):
        """Test _derive_async_url when URL is already async."""
        async_url = "sqlite+aiosqlite:///test.db"
        result = _derive_async_url(async_url)
        assert result == async_url

    def test_derive_async_url_with_support(self):
        """Test _derive_async_url correctly derives URL when async support is available."""
        result = _derive_async_url("sqlite:///test.db")
        assert result == "sqlite+aiosqlite:///test.db"

    def test_async_engine_not_configured(self):
        """Test that async_engine is None when not configured."""
        assert async_engine is None

    @pytest.mark.asyncio
    async def test_get_async_session_not_configured(self):
        """Test get_async_session raises RuntimeError when not configured."""
        with patch("core.db.AsyncSessionLocal", None):
            with pytest.raises(RuntimeError, match="Async SQLAlchemy is not configured"):
                async for _session in get_async_session():
                    break

    @pytest.mark.asyncio
    async def test_session_scope_async_not_configured(self):
        """Test session_scope_async raises error when not configured."""
        with patch("core.db.AsyncSessionLocal", None):
            with pytest.raises(RuntimeError, match="Async SQLAlchemy is not configured"):
                async with session_scope_async():
                    pass

    @pytest.mark.asyncio
    async def test_init_db_async_fallback(self):
        """Test init_db_async falls back to sync init when async not configured."""
        # Should work without raising errors
        await init_db_async()

    def test_derive_async_url_no_async_support(self):
        """Test _derive_async_url handles both async available and not available cases."""
        from core import db

        result = db._derive_async_url("sqlite:///test.db")

        if db.create_async_engine is None:
            # Async support truly not available - should return None
            assert result is None
        else:
            # Async support is available - should convert URL
            assert result == "sqlite+aiosqlite:///test.db"

    def test_execute_sql_method(self):
        """Test execute method on connection."""
        # Ensure DB is initialized
        from core import db

        if db._RAW_ENGINE is None:
            db.init_db()
        # Use dynamic import to get current value
        from core.db import _RAW_ENGINE as current_engine

        # Test with a simple SELECT statement using connection
        with current_engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test_value"))
            # Should return a result object
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_async_session_import_error(self, monkeypatch: pytest.MonkeyPatch):
        """Test get_async_session raises ImportError when async extras not available.

        This test forces the "extras missing" scenario by patching create_async_engine
        and async_sessionmaker to None, simulating an environment where sqlalchemy[asyncio]
        is not installed.
        """
        from core import db

        db.reset_db_for_tests()
        # Force "extras missing" scenario - patch all async-related symbols in core.db
        # This simulates the case where sqlalchemy[asyncio] is not installed
        monkeypatch.setattr(db, "create_async_engine", None, raising=False)
        monkeypatch.setattr(db, "async_sessionmaker", None, raising=False)
        monkeypatch.setattr(db, "AsyncSessionLocal", None, raising=False)
        # Also patch sa_asyncio to None to ensure the check in get_async_session() works
        monkeypatch.setattr(db, "sa_asyncio", None, raising=False)

        # Verify patches are in place
        assert db.create_async_engine is None
        assert db.async_sessionmaker is None

        # Should raise ImportError with message about async extras not being available
        with pytest.raises(ImportError, match=r"SQLAlchemy async extras are not available"):
            async for _session in db.get_async_session():
                pass

    @pytest.mark.asyncio
    async def test_session_scope_async_success(self):
        """Test session_scope_async with successful commit."""
        # This will test the main path if async is configured
        if async_engine is not None:
            async with session_scope_async() as session:
                # Just ensure we can get a session
                assert session is not None

    @pytest.mark.asyncio
    async def test_session_scope_async_rollback(self):
        """Test session_scope_async with exception and rollback."""
        if async_engine is not None:
            with pytest.raises(ValueError):
                async with session_scope_async() as session:
                    # Simulate an error that should trigger rollback
                    raise ValueError("Test rollback")

    @pytest.mark.asyncio
    async def test_init_db_async_with_async_engine(self):
        """Test init_db_async when async engine is available."""
        if async_engine is not None:
            # Should work without raising errors
            await init_db_async()
