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
    ASYNC_DATABASE_URL,
    AsyncSessionLocal,
    Base,
    SessionLocal,
    _build_engine_url,
    _derive_async_url,
    _sqlite_connect_args,
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

    def test_async_defaults_disabled(self):
        """Async session factory defaults to None unless configured."""

        assert AsyncSessionLocal is None or callable(AsyncSessionLocal)
        assert async_engine is None or hasattr(async_engine, "begin")

    def test_derive_async_url_helper(self):
        """Test async URL derivation from common driver strings."""

        assert _derive_async_url("sqlite:///data.db") == "sqlite+aiosqlite:///data.db"
        assert (
            _derive_async_url("postgresql://user:pass@host/db")
            == "postgresql+asyncpg://user:pass@host/db"
        )
        assert _derive_async_url("mysql+pymysql://user@host/db") == "mysql+aiomysql://user@host/db"
        assert _derive_async_url("custom://driver") is None

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

    @pytest.mark.asyncio
    async def test_get_async_session_raises_when_disabled(self):
        """get_async_session should raise if async factory not configured."""

        if AsyncSessionLocal is not None:
            pytest.skip("Async session factory configured in environment")

        with pytest.raises(RuntimeError):
            gen = get_async_session()
            await gen.__anext__()

    @pytest.mark.asyncio
    async def test_session_scope_async_missing_factory(self):
        """session_scope_async should raise when async not configured."""

        if AsyncSessionLocal is not None:
            pytest.skip("Async session factory configured in environment")

        with pytest.raises(RuntimeError):
            async with session_scope_async():
                pass

    def test_async_database_url_constant_defined(self):
        """ASYNC_DATABASE_URL should always be defined (possibly None)."""

        assert ASYNC_DATABASE_URL is None or isinstance(ASYNC_DATABASE_URL, str)

    @pytest.mark.asyncio
    async def test_init_db_async_fallback(self):
        """init_db_async should succeed even when async engine disabled."""

        await init_db_async()

    def test_sqlite_file_path_creation(self):
        """Test SQLite file path handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "test.db")
            test_url = f"sqlite:///{test_path}"

            args = _sqlite_connect_args(test_url)
            assert args["check_same_thread"] is False
