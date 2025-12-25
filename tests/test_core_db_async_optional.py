"""Coverage tests for optional async support in core.db."""

from __future__ import annotations

import importlib
import sys

import pytest

import core.db as db_module


def test_core_db_handles_missing_async_support(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test core.db handles missing async support gracefully."""

    original_import = importlib.import_module

    def fake_import(name: str, package: str | None = None):
        if name == "sqlalchemy.ext.asyncio":
            raise ImportError("async extras not installed")
        return original_import(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import)

    # Re-import to test missing async support
    if "core.db" in sys.modules:
        del sys.modules["core.db"]
    import core.db as reloaded_db_module

    assert reloaded_db_module.create_async_engine is None
    assert reloaded_db_module.async_sessionmaker is None

    monkeypatch.undo()


@pytest.mark.asyncio
async def test_get_async_session_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise get_async_session happy path when AsyncSessionLocal is configured."""
    if db_module.create_async_engine is None or db_module.async_sessionmaker is None:
        pytest.skip("sqlalchemy.asyncio not available")

    class DummyAsyncSession:
        def __init__(self) -> None:
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    def factory() -> DummyAsyncSession:
        return DummyAsyncSession()

    # Patch both AsyncSessionLocal and _get_async_engine to return a mock engine
    monkeypatch.setattr(db_module, "AsyncSessionLocal", factory)
    # Mock _get_async_engine to return a fake engine so get_async_session doesn't fail
    fake_engine = type("FakeEngine", (), {})()
    monkeypatch.setattr(db_module, "_get_async_engine", lambda: fake_engine)

    gen = db_module.get_async_session()
    session = await gen.__anext__()
    assert isinstance(session, DummyAsyncSession)
    await gen.aclose()
    assert session.closed is True


@pytest.mark.asyncio
async def test_session_scope_async_commits_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise session_scope_async commit and close behavior."""

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

    # Patch both AsyncSessionLocal and _get_async_engine
    monkeypatch.setattr(db_module, "AsyncSessionLocal", factory)
    fake_engine = type("FakeEngine", (), {})()
    monkeypatch.setattr(db_module, "_get_async_engine", lambda: fake_engine)

    async with db_module.session_scope_async() as session:
        assert isinstance(session, DummyAsyncSession)
        # No explicit commit; context manager should commit on exit

    assert session.committed is True
    assert session.closed is True


@pytest.mark.asyncio
async def test_session_scope_async_rolls_back_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise session_scope_async rollback behavior when an error occurs."""

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

    # Patch both AsyncSessionLocal and _get_async_engine
    monkeypatch.setattr(db_module, "AsyncSessionLocal", factory)
    fake_engine = type("FakeEngine", (), {})()
    monkeypatch.setattr(db_module, "_get_async_engine", lambda: fake_engine)

    with pytest.raises(RuntimeError, match="boom"):
        async with db_module.session_scope_async() as session:
            assert isinstance(session, DummyAsyncSession)
            raise RuntimeError("boom")

    assert session.committed is False
    assert session.rolled_back is True
    assert session.closed is True
