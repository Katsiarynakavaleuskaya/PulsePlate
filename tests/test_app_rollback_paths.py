#!/usr/bin/env python3
import pytest
from fastapi import HTTPException

import app as app_mod


@pytest.mark.asyncio
async def test_rollback_scheduler_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    class DummyScheduler:
        pass

    async def fake_scheduler() -> DummyScheduler:
        called["hit"] = True
        raise RuntimeError("boom")

    monkeypatch.setitem(
        app_mod.rollback_database.__globals__, "get_update_scheduler", fake_scheduler
    )

    with pytest.raises(HTTPException) as exc:
        await app_mod.rollback_database("usda", "v1")
    assert called
    assert exc.value.status_code == 500
    assert "could not get scheduler" in exc.value.detail


@pytest.mark.asyncio
async def test_rollback_no_update_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyScheduler:
        update_manager = None

    async def fake_scheduler() -> DummyScheduler:
        return DummyScheduler()

    monkeypatch.setitem(
        app_mod.rollback_database.__globals__, "get_update_scheduler", fake_scheduler
    )
    resp = await app_mod.rollback_database("usda", "v1")
    assert resp == {"message": "No update manager available; nothing to rollback"}


@pytest.mark.asyncio
async def test_rollback_no_rollback_fn(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyManager:
        pass

    class DummyScheduler:
        update_manager = DummyManager()

    async def fake_scheduler() -> DummyScheduler:
        return DummyScheduler()

    monkeypatch.setitem(
        app_mod.rollback_database.__globals__, "get_update_scheduler", fake_scheduler
    )
    resp = await app_mod.rollback_database("usda", "v1")
    assert resp == {"message": "Rollback operation not supported by update manager"}


@pytest.mark.asyncio
async def test_rollback_raises_inside_method(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyManager:
        async def rollback_database(self, source, target_version):
            raise RuntimeError("boom")

    class DummyScheduler:
        update_manager = DummyManager()

    async def fake_scheduler() -> DummyScheduler:
        return DummyScheduler()

    monkeypatch.setitem(
        app_mod.rollback_database.__globals__, "get_update_scheduler", fake_scheduler
    )
    with pytest.raises(HTTPException) as exc:
        await app_mod.rollback_database("usda", "v1")
    assert exc.value.status_code == 500
    assert "Rollback operation failed" in exc.value.detail
