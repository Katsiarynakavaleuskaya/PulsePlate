"""Coverage tests for optional async support in core.db."""

from __future__ import annotations

import importlib

import pytest

import core.db as db_module


def test_core_db_handles_missing_async_support(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reload core.db with sqlalchemy.ext.asyncio unavailable and ensure fallbacks are set."""

    original_import = importlib.import_module

    def fake_import(name: str, package: str | None = None):
        if name == "sqlalchemy.ext.asyncio":
            raise ImportError("async extras not installed")
        return original_import(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import)

    reloaded = importlib.reload(db_module)
    assert reloaded.create_async_engine is None
    assert reloaded.async_sessionmaker is None

    monkeypatch.undo()
    importlib.reload(db_module)


@pytest.mark.asyncio
async def test_get_async_session_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise get_async_session happy path when AsyncSessionLocal is configured."""
    # Reload to ensure async symbols are available
    importlib.reload(db_module)

    if db_module.create_async_engine is None or db_module.async_sessionmaker is None:
        pytest.skip("sqlalchemy.asyncio not available")

    class DummyAsyncSession:
        def __init__(self) -> None:
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    def factory() -> DummyAsyncSession:
        return DummyAsyncSession()

    monkeypatch.setattr(db_module, "AsyncSessionLocal", factory)

    gen = db_module.get_async_session()
    session = await gen.__anext__()
    assert isinstance(session, DummyAsyncSession)
    await gen.aclose()
    assert session.closed is True


@pytest.mark.asyncio
async def test_session_scope_async_commits_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise session_scope_async commit and close behavior."""
    importlib.reload(db_module)

    class DummyAsyncSession:
        def __init__(self) -> None:
            self.committed = False
            self.closed = False
            self.rolled_back = False

        async def commit(self) -> None:
            self.committed = True

        async def rollback(self) -> None:
            self.rolled_back = True

        async def close(self) -> None:
            self.closed = True

    def factory() -> DummyAsyncSession:
        return DummyAsyncSession()

    monkeypatch.setattr(db_module, "AsyncSessionLocal", factory)

    async with db_module.session_scope_async() as session:
        assert isinstance(session, DummyAsyncSession)
        # No explicit commit; context manager should commit on exit

    assert session.committed is True
    assert session.closed is True
