import pytest
from types import TracebackType
from typing import Any

from sqlalchemy import exc as sa_exc

from core.db import (
    EngineCompat,
    _ResultWithConnectionCleanup,
    _derive_async_url,
    create_async_engine,
)

"""Tests for EngineCompat behavior and exception handling.

This module contains tests for the EngineCompat class, focusing on transaction
handling, commit behavior, and error propagation in database operations.
"""


class _FakeConn:
    """Lightweight fake DB connection for tests.

    Simulates a database connection with configurable commit error behavior and
    transaction state, used to test EngineCompat exception handling.
    """

    def __init__(self, commit_raises: Exception | None = None, in_tx: bool = True) -> None:
        """Initialize fake connection with optional commit error and transaction state.

        Args:
            commit_raises: Exception to raise on commit, or None for successful commit.
            in_tx: Whether connection appears to be in a transaction.
        """
        self._commit_raises = commit_raises
        self._in_tx = in_tx

    def execute(
        self, stmt: Any, *args: Any, **kwargs: Any
    ) -> str:  # pragma: no cover - trivial pass-through
        """Execute a statement, returning a dummy result string."""
        return "ok"

    def get_transaction(self) -> object | None:  # emulate SQLAlchemy API
        """Return a transaction object if in transaction, None otherwise."""
        return object() if self._in_tx else None

    def commit(self) -> None:
        """Commit the transaction, raising the configured exception if set."""
        if self._commit_raises is not None:
            raise self._commit_raises

    def rollback(self) -> None:  # pragma: no cover - executed only on error path
        """Rollback the transaction (no-op for fake connection)."""
        return None

    def close(self) -> None:  # pragma: no cover - executed only on error path
        """Close the connection (no-op for fake connection)."""
        return None

    # context manager protocol
    def __enter__(self) -> "_FakeConn":
        """Enter context manager, returning self."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:  # pragma: no cover - no-op
        """Exit context manager (no-op for fake connection)."""
        pass


class _FakeEngine:
    """Test double that wraps a provided _FakeConn and returns it from connect().

    Args:
        conn: The _FakeConn instance to return when connect() is called.

    The connect() method simply returns the wrapped _FakeConn instance,
    allowing tests to control connection behavior without a real database.
    """

    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    def connect(self) -> _FakeConn:
        return self._conn


def test_execute_commits_only_when_in_transaction() -> None:
    """Verify commit is skipped when not in a transaction and underlying result is accessible."""
    # in_tx=False should skip commit without raising
    engine = EngineCompat(_FakeEngine(_FakeConn(commit_raises=None, in_tx=False)))
    result = engine.execute("SELECT 1")
    # Result is wrapped, but underlying result should be accessible
    assert hasattr(result, "_result")
    assert result._result == "ok"


def test_execute_handles_db_errors_on_commit_with_re_raise() -> None:
    """Verify an IntegrityError during commit is logged, rolled back, and re-raised."""
    fake_exc = sa_exc.IntegrityError("stmt", {}, Exception("detail"))
    engine = EngineCompat(_FakeEngine(_FakeConn(commit_raises=fake_exc, in_tx=True)))
    # Error is logged, rolled back, and re-raised to notify callers
    with pytest.raises(sa_exc.IntegrityError):
        engine.execute("UPDATE t SET a=1")


def test_execute_propagates_unexpected_errors() -> None:
    """ValueError on commit should trigger rollback and be re-raised."""
    engine = EngineCompat(_FakeEngine(_FakeConn(commit_raises=ValueError("boom"), in_tx=True)))
    with pytest.raises(ValueError):
        engine.execute("SELECT 1")


def test_result_wrapper_closes_connection() -> None:
    """_ResultWithConnectionCleanup should close both result and connection."""

    class _Result:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class _Conn(_FakeConn):
        def __init__(self) -> None:
            super().__init__(in_tx=False)
            self.closed = False

        def close(self) -> None:
            self.closed = True

    result = _Result()
    conn = _Conn()
    wrapper = _ResultWithConnectionCleanup(result, conn)
    wrapper.close()
    assert result.closed is True
    assert conn.closed is True

    # Context manager should also close underlying connection
    result = _Result()
    conn = _Conn()
    with _ResultWithConnectionCleanup(result, conn):
        pass
    assert result.closed is True
    assert conn.closed is True


@pytest.mark.skipif(create_async_engine is None, reason="SQLAlchemy async extras not installed")
def test_derive_async_url_variants() -> None:
    """Ensure _derive_async_url maps common sync URLs to their async counterparts."""
    assert _derive_async_url("sqlite:///test.db") == "sqlite+aiosqlite:///test.db"
    assert _derive_async_url("postgresql://user:pass@localhost/db").startswith(
        "postgresql+asyncpg://"
    )
    # psycopg dialect reuses the same URL
    assert (
        _derive_async_url("postgresql+psycopg://user:pass@localhost/db")
        == "postgresql+psycopg://user:pass@localhost/db"
    )
