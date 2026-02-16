from __future__ import annotations

from contextlib import suppress
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any


def _default_force_update_result() -> object:
    """Return attribute-shaped result compatible with force-update response formatter."""
    return SimpleNamespace(
        success=True,
        old_version="stub-old",
        new_version="stub-new",
        records_added=0,
        records_updated=0,
        records_removed=0,
        duration_seconds=0.0,
        errors=[],
    )


def make_scheduler_stub(usda_result: Any = None) -> object:
    """
    Return a scheduler-like object with async force_update.
    Matches legacy_app.get_update_scheduler seam used in tests.
    """

    class _SchedulerStub:
        async def force_update(self, source: str | None = None) -> dict[str, Any]:
            _ = source
            source_result = (
                usda_result if usda_result is not None else _default_force_update_result()
            )
            return {"usda": source_result}

    return _SchedulerStub()


def patch_app_get_update_scheduler(monkeypatch: Any, app_module: Any, scheduler: object) -> None:
    """
    Patch scheduler seam for force-update tests.
    Applies override to both `app` facade and `legacy_app` where endpoint resolves runtime getter.
    """

    async def _fake_get_update_scheduler() -> object:
        return scheduler

    monkeypatch.setattr(app_module, "get_update_scheduler", _fake_get_update_scheduler)
    with suppress(Exception):
        import legacy_app as legacy_app_mod

        monkeypatch.setattr(legacy_app_mod, "get_update_scheduler", _fake_get_update_scheduler)


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
    monkeypatch: Any,
    *,
    load: Callable[..., Any] | None = None,
    save: Callable[..., Any] | None = None,
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
