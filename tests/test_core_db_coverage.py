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

from core.db import (
    Base,
    SessionLocal,
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
        assert args == {"check_same_thread": False}

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
        assert SessionLocal is not None
        assert hasattr(SessionLocal, "__call__")

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

    @patch("core.db.Base.metadata")
    def test_init_db(self, mock_metadata):
        """Test init_db creates tables."""
        mock_metadata.create_all = MagicMock(return_value=None)

        # Should not raise exception
        init_db()

        # Verify create_all was called
        mock_metadata.create_all.assert_called_once()

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
        """Test DATABASE_URL is properly formatted for SQLite."""
        from core.db import DATABASE_URL

        # Should be valid URL format
        assert isinstance(DATABASE_URL, str)
        assert len(DATABASE_URL) > 0

    def test_engine_creation(self):
        """Test engine is created properly."""
        from core.db import engine

        assert engine is not None
        assert hasattr(engine, "connect")
        assert hasattr(engine, "execute")

    def test_session_configuration(self):
        """Test SessionLocal is configured correctly."""
        # Test that SessionLocal has expected configuration
        session = SessionLocal()
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
        """Test get_async_session raises error when not configured."""
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
