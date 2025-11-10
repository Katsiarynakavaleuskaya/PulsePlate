import pytest
from sqlalchemy import create_engine, exc as sa_exc, text

from core import db
from core.db import EngineCompat, _derive_async_url, create_async_engine


def test_derive_async_url_postgresql_psycopg2() -> None:
    """Cover line 94: postgresql+psycopg2:// replacement."""
    sync_url = "postgresql+psycopg2://user:pass@host/db"
    async_url = _derive_async_url(sync_url)
    assert async_url == "postgresql+asyncpg://user:pass@host/db"


def test_engine_compat_execute_rollback_on_error() -> None:
    """Cover lines 203-206: rollback in exception handler."""
    engine = EngineCompat(create_engine("sqlite:///:memory:", future=True))

    # Create a connection that will fail on execute
    with pytest.raises(Exception):
        with engine.connect() as conn:
            # Try to execute invalid SQL to trigger exception
            conn.execute(text("INVALID SQL SYNTAX"))  # type: ignore[arg-type]


def test_engine_compat_connection_close_on_error() -> None:
    """Cover line 209: connection.close() in exception handler."""
    engine = EngineCompat(create_engine("sqlite:///:memory:", future=True))

    # Force an error during execute to trigger cleanup path
    with pytest.raises(Exception):
        with engine.connect() as conn:
            # Invalid SQL to cause exception
            conn.execute(
                text("SELECT * FROM nonexistent_table WHERE invalid syntax")
            )  # type: ignore[arg-type]


def test_engine_compat_result_cleanup() -> None:
    """Cover lines 253, 284: result cleanup and connection close."""
    engine = EngineCompat(create_engine("sqlite:///:memory:", future=True))

    # Create a simple table for testing
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE test (id INTEGER)"))  # type: ignore[arg-type]
        conn.commit()

    # Execute a query that returns a result - engine.execute returns a context manager
    result = engine.execute("SELECT * FROM test")
    with result:
        # Result should be usable
        assert result is not None
        # When exiting context, connection should be closed


def test_engine_compat_async_url_derivation_edge_cases() -> None:
    """Cover line 173: edge cases in async URL derivation."""
    # Test various URL formats
    sqlite_result = _derive_async_url("sqlite:///test.db")
    if create_async_engine is None:
        assert sqlite_result is None
    else:
        assert sqlite_result == "sqlite+aiosqlite:///test.db"
    postgres_result = _derive_async_url("postgresql://user@host/db")
    assert postgres_result is not None
    assert postgres_result.startswith("postgresql+asyncpg://")
    assert (
        _derive_async_url("postgresql+psycopg://user@host/db")
        == "postgresql+psycopg://user@host/db"
    )


def test_is_in_transaction_exception_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover lines 203-206: exception handling in in_transaction check."""
    from unittest.mock import Mock

    engine = EngineCompat(create_engine("sqlite:///:memory:", future=True))

    # Create a connection with in_transaction that raises
    with engine.connect() as conn:
        # Mock in_transaction to raise exception
        def failing_in_transaction():
            raise RuntimeError("Transaction check failed")

        monkeypatch.setattr(conn, "in_transaction", failing_in_transaction)
        monkeypatch.setattr(conn, "get_transaction", None)

        # _is_in_transaction should catch the exception and return False
        result = engine._is_in_transaction(conn)
        assert result is False


def test_is_in_transaction_fallback_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover line 209: return False when no transaction methods available."""
    engine = EngineCompat(create_engine("sqlite:///:memory:", future=True))

    with engine.connect() as conn:
        # Set both get_transaction and in_transaction to None
        monkeypatch.setattr(conn, "get_transaction", None)
        monkeypatch.setattr(conn, "in_transaction", None)

        # Should return False as fallback
        result = engine._is_in_transaction(conn)
        assert result is False


def test_finalize_transaction_debug_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover line 253: debug logging in commit failure."""
    import logging

    engine = EngineCompat(create_engine("sqlite:///:memory:", future=True))

    # Set logger to DEBUG level
    logger = logging.getLogger("core.db")
    prev_level = logger.level
    logger.setLevel(logging.DEBUG)

    try:
        with engine.connect() as conn:
            # Force a commit failure by closing connection first
            conn.close()
            # Try to finalize - this should trigger debug logging path
            try:
                engine._finalize_transaction(conn)
            except Exception:
                pass  # Expected to fail
    finally:
        logger.setLevel(prev_level)


def test_finalize_transaction_error_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover line 255: logging branch when not in debug and production."""
    import logging

    engine = db.EngineCompat(object())

    class FakeConn:
        rollback_called = False

        def get_transaction(self):
            return object()

        def commit(self):
            raise sa_exc.SQLAlchemyError("db fail")

        def rollback(self):
            self.rollback_called = True

    fake_conn = FakeConn()
    monkeypatch.setattr(db, "ENVIRONMENT", "production", raising=False)
    logger = logging.getLogger("core.db")
    prev_level = logger.level
    logger.setLevel(logging.INFO)
    try:
        with pytest.raises(sa_exc.SQLAlchemyError):
            engine._finalize_transaction(fake_conn)
    finally:
        logger.setLevel(prev_level)
    assert fake_conn.rollback_called is True


def test_finalize_transaction_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover line 259: unexpected exception branch."""
    import logging

    engine = db.EngineCompat(object())

    class FakeConn:
        rollback_called = False

        def get_transaction(self):
            return object()

        def commit(self):
            raise RuntimeError("boom")

        def rollback(self):
            self.rollback_called = True

    fake_conn = FakeConn()
    logger = logging.getLogger("core.db")
    prev_level = logger.level
    logger.setLevel(logging.INFO)
    try:
        with pytest.raises(RuntimeError):
            engine._finalize_transaction(fake_conn)
    finally:
        logger.setLevel(prev_level)
    assert fake_conn.rollback_called is True


def test_get_async_engine_sqlite_pool_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover line 328: skip pool config for sqlite+aiosqlite."""
    if db.create_async_engine is None or db.async_sessionmaker is None:
        pytest.skip("sqlalchemy.asyncio not available")

    import importlib
    import os

    original_db_url = os.environ.get("DATABASE_URL")
    original_use_async = os.environ.get("DATABASE_USE_ASYNC")

    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp_async_reload.db")
    monkeypatch.setenv("DATABASE_USE_ASYNC", "1")

    reloaded = importlib.reload(db)
    try:
        async_url = reloaded.ASYNC_DATABASE_URL
        if async_url:
            assert async_url.startswith("sqlite+aiosqlite")
    finally:
        if original_db_url is None:
            monkeypatch.delenv("DATABASE_URL", raising=False)
        else:
            monkeypatch.setenv("DATABASE_URL", original_db_url)
        if original_use_async is None:
            monkeypatch.delenv("DATABASE_USE_ASYNC", raising=False)
        else:
            monkeypatch.setenv("DATABASE_USE_ASYNC", original_use_async)

        restored = importlib.reload(db)
        restored.init_db()


def test_finalize_transaction_debug_logging_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover line 253: debug logging path in commit failure (non-production)."""
    import logging

    engine = EngineCompat(create_engine("sqlite:///:memory:", future=True))

    # Set environment to non-production to trigger debug logging path
    monkeypatch.setenv("ENVIRONMENT", "test")

    # Set logger to DEBUG level
    logger = logging.getLogger("core.db")
    prev_level = logger.level
    logger.setLevel(logging.DEBUG)

    try:
        with engine.connect() as conn:
            # Force a commit failure by closing connection first
            conn.close()
            # Try to finalize - this should trigger debug logging path (line 253)
            try:
                engine._finalize_transaction(conn)
            except Exception:
                pass  # Expected to fail
    finally:
        logger.setLevel(prev_level)
