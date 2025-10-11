"""Additional coverage tests for core.db helper utilities."""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
from typing import Any

import pytest
from sqlalchemy.exc import InvalidRequestError, SQLAlchemyError

import core.db as db


class _FakeResult:
    pass


class _DummyConnection:
    def __init__(self, *, commit_exception: BaseException | None = None) -> None:
        self._commit_exception = commit_exception
        self.executed = False
        self.committed = False

    def __enter__(self) -> _DummyConnection:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, stmt, *args, **kwargs) -> _FakeResult:  # noqa: ANN001
        self.executed = True
        return _FakeResult()

    def commit(self) -> None:
        self.committed = True
        if self._commit_exception:
            raise self._commit_exception


def _patch_engine_connect(monkeypatch: pytest.MonkeyPatch, connection: _DummyConnection) -> None:
    """Patch the raw engine to return the provided dummy connection."""

    class _FakeEngine:
        def connect(self) -> _DummyConnection:
            return connection

    monkeypatch.setattr(db, "_RAW_ENGINE", _FakeEngine())
    monkeypatch.setattr(db, "engine", db.EngineCompat(db._RAW_ENGINE))


def test_engine_compat_handles_invalid_request(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    """EngineCompat must ignore InvalidRequestError raised on commit."""
    conn = _DummyConnection(commit_exception=InvalidRequestError("no tx", ""))
    _patch_engine_connect(monkeypatch, conn)
    caplog.set_level("DEBUG", logger=db.logger.name)

    result = db.engine.execute("SELECT 1")
    assert isinstance(result, _FakeResult)
    assert conn.executed is True
    assert "Commit skipped for non-transactional statement" in caplog.text


def test_engine_compat_logs_unexpected_commit_error(
    monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    """Unexpected commit exceptions should be logged at warning level."""
    conn = _DummyConnection(commit_exception=ValueError("failure"))
    _patch_engine_connect(monkeypatch, conn)
    caplog.set_level("WARNING", logger=db.logger.name)

    result = db.engine.execute("SELECT 1")
    assert isinstance(result, _FakeResult)
    assert "Unexpected commit failure" in caplog.text


def test_check_async_availability_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """When async extras are missing, ImportError should be raised."""
    with ExitStack():
        monkeypatch.setattr(db, "AsyncSessionLocal", None)
        monkeypatch.setattr(db, "create_async_engine", None)

        with pytest.raises(ImportError):
            db._check_async_availability()


def test_check_async_availability_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """When async engine exists but not configured, raise RuntimeError."""
    monkeypatch.setattr(db, "AsyncSessionLocal", None)
    monkeypatch.setattr(db, "create_async_engine", object())

    with pytest.raises(RuntimeError):
        db._check_async_availability()


class _DummyAsyncSession:
    def __init__(self, *, commit_exception: BaseException | None = None) -> None:
        self.closed = False
        self.committed = False
        self._commit_exception = commit_exception

    async def commit(self) -> None:
        self.committed = True
        if self._commit_exception:
            raise self._commit_exception

    async def rollback(self) -> None:
        self.committed = False

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_get_async_session_yields_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that get_async_session yields and closes sessions."""
    dummy_session = _DummyAsyncSession()

    async def _session_factory() -> _DummyAsyncSession:  # noqa: ANN202
        return dummy_session

    monkeypatch.setattr(db, "AsyncSessionLocal", lambda: dummy_session)
    monkeypatch.setattr(db, "create_async_engine", object())

    async for session in db.get_async_session():
        assert session is dummy_session
    assert dummy_session.closed is True


@pytest.mark.asyncio
async def test_session_scope_async_handles_commit_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """session_scope_async should rollback on commit errors."""
    error_session = _DummyAsyncSession(commit_exception=ValueError("commit failed"))
    monkeypatch.setattr(db, "AsyncSessionLocal", lambda: error_session)
    monkeypatch.setattr(db, "create_async_engine", object())

    with pytest.raises(ValueError):
        async with db.session_scope_async():
            pass
    assert error_session.closed is True


def test_legacy_aliases_call_init_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy init helpers should delegate to init_db."""
    called = {"count": 0}

    def fake_init_db() -> None:
        called["count"] += 1

    monkeypatch.setattr(db, "init_db", fake_init_db)

    db.create_tables()
    db.init_database()
    assert called["count"] == 2


def test_async_engine_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reloading the module with async enabled should configure async session maker."""
    import importlib

    import sqlalchemy.ext.asyncio as sa_async

    created: dict[str, Any] = {}

    def fake_create_async_engine(url: str, **kwargs: Any) -> str:
        created["url"] = url
        created["engine_kwargs"] = kwargs
        return "fake-engine"

    def fake_async_sessionmaker(**kwargs: Any) -> str:
        created["session_kwargs"] = kwargs
        return "fake-sessionmaker"

    monkeypatch.setattr(sa_async, "create_async_engine", fake_create_async_engine)
    monkeypatch.setattr(sa_async, "async_sessionmaker", fake_async_sessionmaker)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tests.db")
    monkeypatch.setenv("DATABASE_USE_ASYNC", "1")
    monkeypatch.setenv("DATABASE_POOL_SIZE", "3")
    monkeypatch.setenv("DATABASE_MAX_OVERFLOW", "2")

    module = importlib.reload(db)
    assert created["url"].startswith("sqlite+aiosqlite")
    assert created["session_kwargs"]["bind"] == "fake-engine"

    # Cleanup: disable async and reload module to restore defaults
    monkeypatch.delenv("DATABASE_USE_ASYNC", raising=False)
    module = importlib.reload(module)
