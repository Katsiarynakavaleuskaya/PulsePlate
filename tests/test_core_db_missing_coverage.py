from __future__ import annotations

import logging
from typing import Any

import pytest
from sqlalchemy import exc as sa_exc

import core.db as db


def test_derive_async_url_returns_none_when_async_support_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(db, "create_async_engine", None, raising=False)
    assert db._derive_async_url("sqlite:///test.db") is None


def test_get_pool_config_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_POOL_SIZE", "7")
    monkeypatch.setenv("DATABASE_MAX_OVERFLOW", "9")
    assert db._get_pool_config() == {"pool_size": 7, "max_overflow": 9, "pool_pre_ping": True}


def test_get_async_database_url_returns_none_when_async_support_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(db, "create_async_engine", None, raising=False)
    monkeypatch.setattr(db, "async_sessionmaker", None, raising=False)
    monkeypatch.setenv("DATABASE_ASYNC_URL", "sqlite+aiosqlite:///:memory:")
    assert db._get_async_database_url() is None


def test_get_async_engine_returns_none_if_support_disappears_mid_init(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db._ASYNC_ENGINE = None
    db.AsyncSessionLocal = None
    db.async_engine = None

    def _fake_async_database_url() -> str:
        monkeypatch.setattr(db, "create_async_engine", None, raising=False)
        monkeypatch.setattr(db, "async_sessionmaker", None, raising=False)
        return "postgresql+asyncpg://user:pass@localhost/db"

    monkeypatch.setattr(db, "_get_async_database_url", _fake_async_database_url)
    assert db._get_async_engine() is None


def test_get_async_engine_disposes_old_engine_and_applies_pool_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _DummySyncEngine:
        def __init__(self) -> None:
            self.disposed = False

        def dispose(self) -> None:
            self.disposed = True

    class _DummyAsyncEngine:
        def __init__(self, url: str) -> None:
            self.url = url
            self.sync_engine = _DummySyncEngine()

    captured: dict[str, Any] = {}

    def _fake_create_async_engine(url: str, **kwargs: Any) -> _DummyAsyncEngine:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return _DummyAsyncEngine(url)

    def _fake_async_sessionmaker(**_kwargs: Any):  # noqa: ANN401 - test stub
        return lambda: "session"

    monkeypatch.setattr(db, "create_async_engine", _fake_create_async_engine, raising=False)
    monkeypatch.setattr(db, "async_sessionmaker", _fake_async_sessionmaker, raising=False)
    monkeypatch.setenv("DATABASE_POOL_SIZE", "3")
    monkeypatch.setenv("DATABASE_MAX_OVERFLOW", "5")
    monkeypatch.setenv("DATABASE_ASYNC_URL", "postgresql+asyncpg://user:pass@localhost/db")

    old_engine = _DummyAsyncEngine("postgresql+asyncpg://user:pass@localhost/old")
    db._ASYNC_ENGINE = old_engine
    db.AsyncSessionLocal = None
    db.async_engine = None

    try:
        new_engine = db._get_async_engine()
        assert new_engine is not None
        assert old_engine.sync_engine.disposed is True
        assert captured["url"] == "postgresql+asyncpg://user:pass@localhost/db"
        assert captured["kwargs"]["pool_size"] == 3
        assert captured["kwargs"]["max_overflow"] == 5
        assert captured["kwargs"]["pool_pre_ping"] is True
        assert callable(db.AsyncSessionLocal)
        assert db.AsyncSessionLocal() == "session"
    finally:
        db._ASYNC_ENGINE = None
        db.AsyncSessionLocal = None
        db.async_engine = None


def test_get_async_engine_dispose_failure_is_logged(
    monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    class _BadSyncEngine:
        def dispose(self) -> None:
            raise RuntimeError("dispose boom")

    class _DummyAsyncEngine:
        def __init__(self, url: str) -> None:
            self.url = url
            self.sync_engine = _BadSyncEngine()

    def _fake_create_async_engine(url: str, **_kwargs: Any) -> _DummyAsyncEngine:
        return _DummyAsyncEngine(url)

    def _fake_async_sessionmaker(**_kwargs: Any):  # noqa: ANN401 - test stub
        return lambda: "session"

    monkeypatch.setattr(db, "create_async_engine", _fake_create_async_engine, raising=False)
    monkeypatch.setattr(db, "async_sessionmaker", _fake_async_sessionmaker, raising=False)
    monkeypatch.setenv("DATABASE_ASYNC_URL", "postgresql+asyncpg://user:pass@localhost/db")

    old_engine = _DummyAsyncEngine("postgresql+asyncpg://user:pass@localhost/old")
    db._ASYNC_ENGINE = old_engine
    db.AsyncSessionLocal = None
    db.async_engine = None

    try:
        with caplog.at_level(logging.DEBUG):
            assert db._get_async_engine() is not None
        assert "Async engine dispose failed" in caplog.text
    finally:
        db._ASYNC_ENGINE = None
        db.AsyncSessionLocal = None
        db.async_engine = None


@pytest.mark.asyncio
async def test_get_async_session_raises_not_available_when_engine_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_ASYNC_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(db, "create_async_engine", object(), raising=False)
    monkeypatch.setattr(db, "async_sessionmaker", object(), raising=False)
    monkeypatch.setattr(db, "_get_async_engine", lambda: None)
    monkeypatch.setattr(db, "AsyncSessionLocal", None, raising=False)

    agen = db.get_async_session()
    with pytest.raises(db.AsyncDBNotAvailable, match="SQLAlchemy async extras are not available"):
        await agen.__anext__()


@pytest.mark.asyncio
async def test_session_scope_async_raises_not_available_when_async_support_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(db, "create_async_engine", None, raising=False)
    monkeypatch.setattr(db, "async_sessionmaker", None, raising=False)

    with pytest.raises(db.AsyncDBNotAvailable, match="SQLAlchemy async extras are not available"):
        async with db.session_scope_async():
            pass


@pytest.mark.asyncio
async def test_session_scope_async_raises_not_available_when_engine_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_ASYNC_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(db, "create_async_engine", object(), raising=False)
    monkeypatch.setattr(db, "async_sessionmaker", object(), raising=False)
    monkeypatch.setattr(db, "_get_async_engine", lambda: None)
    monkeypatch.setattr(db, "AsyncSessionLocal", None, raising=False)

    with pytest.raises(db.AsyncDBNotAvailable, match="SQLAlchemy async extras are not available"):
        async with db.session_scope_async():
            pass


def test_init_db_sets_sessionlocal_when_engine_precreated() -> None:
    db.reset_db_for_tests()
    _ = db._get_raw_engine()
    assert db.SessionLocal is None

    db.init_db()
    assert db.SessionLocal is not None


def test_reset_db_for_tests_handles_dispose_errors(caplog) -> None:
    class _BadEngine:
        def dispose(self) -> None:
            raise RuntimeError("dispose boom")

    db._RAW_ENGINE = _BadEngine()  # type: ignore[assignment]  # force bad engine for coverage
    try:
        with caplog.at_level(logging.DEBUG):
            db.reset_db_for_tests()
        assert "Failed to dispose sync engine during test reset" in caplog.text
    finally:
        db.init_db()


@pytest.mark.asyncio
async def test_init_db_async_runs_with_mock_async_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def _fake_create_all(_bind: Any = None) -> None:  # noqa: ANN401 - test stub
        calls.append("create_all")

    class _DummyConn:
        async def run_sync(self, fn):  # noqa: ANN001, ANN201 - test stub
            fn("bind")

    class _DummyBegin:
        async def __aenter__(self) -> _DummyConn:
            return _DummyConn()

        async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001 - test stub
            return None

    class _DummyAsyncEngine:
        def begin(self) -> _DummyBegin:
            return _DummyBegin()

    monkeypatch.setattr(db, "_get_async_engine", lambda: _DummyAsyncEngine())
    monkeypatch.setattr(db.Base.metadata, "create_all", _fake_create_all)

    await db.init_db_async()
    assert calls == ["create_all"]


def test_finalize_transaction_logs_without_exc_info_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = db.EngineCompat(object())

    class _Conn:
        rollback_called = False

        def get_transaction(self):  # noqa: ANN201 - test stub
            return object()

        def commit(self) -> None:
            raise sa_exc.SQLAlchemyError("db fail")

        def rollback(self) -> None:
            self.rollback_called = True

    conn = _Conn()

    monkeypatch.setenv("ENVIRONMENT", "production")
    logger = logging.getLogger("core.db")
    prev_level = logger.level
    logger.setLevel(logging.INFO)
    try:
        with pytest.raises(sa_exc.SQLAlchemyError):
            engine._finalize_transaction(conn)
    finally:
        logger.setLevel(prev_level)
    assert conn.rollback_called is True
