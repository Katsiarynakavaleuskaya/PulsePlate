from __future__ import annotations

import asyncio
from typing import Any


def make_scheduler_stub(usda_result: dict[str, Any] | None = None) -> object:
    """
    Return a scheduler-like object with async force_update.
    Matches app.get_update_scheduler seam used in tests.
    """

    class _SchedulerStub:
        async def force_update(self, source: str | None = None) -> dict[str, Any]:
            _ = source
            return {"usda": usda_result or {"ok": True, "status": "stubbed"}}

    return _SchedulerStub()


def patch_app_get_update_scheduler(monkeypatch: Any, app_module: Any, scheduler: object) -> None:
    """Patch app.get_update_scheduler to return provided scheduler."""

    async def _fake_get_update_scheduler() -> object:
        return scheduler

    monkeypatch.setattr(app_module, "get_update_scheduler", _fake_get_update_scheduler)


def patch_unified_db_common_foods_fast(monkeypatch: Any) -> None:
    """
    Patch UnifiedFoodDatabase.get_common_foods_database to return a tiny DB fast.
    Keeps method async and avoids IO/cache work.
    """
    from core.food_apis.unified_db import UnifiedFoodDatabase

    async def _fast_common_foods(self: UnifiedFoodDatabase) -> dict[str, Any]:
        return {
            "oats": {"name": "oats"},
            "rice": {"name": "rice"},
        }

    monkeypatch.setattr(UnifiedFoodDatabase, "get_common_foods_database", _fast_common_foods)


def patch_unified_db_cache_load_save(
    monkeypatch: Any, *, load: Any = None, save: Any = None
) -> None:
    """
    Patch _load_cache/_save_cache for exception-path tests.
    Provide callables or leave None to keep existing behavior.
    """
    from core.food_apis.unified_db import UnifiedFoodDatabase

    if load is not None:
        monkeypatch.setattr(UnifiedFoodDatabase, "_load_cache", load)
    if save is not None:
        monkeypatch.setattr(UnifiedFoodDatabase, "_save_cache", save)


def test_fast_update_stubs_smoke() -> None:
    """Smoke-test helper stubs to satisfy deterministic changed-file hooks."""
    scheduler = make_scheduler_stub()
    assert scheduler is not None
    force_update = getattr(scheduler, "force_update")
    result_default = asyncio.run(force_update())
    result_with_source = asyncio.run(force_update("usda"))
    assert "usda" in result_default
    assert "usda" in result_with_source
