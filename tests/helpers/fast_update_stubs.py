from __future__ import annotations

from collections.abc import Callable
import sys
from typing import Any, Protocol


class SchedulerLike(Protocol):
    async def force_update(self, source: str | None = None) -> dict[str, Any]: ...


def make_scheduler_stub(usda_result: Any = None) -> SchedulerLike:
    """
    Return a scheduler-like object with async force_update.
    Matches legacy_app.get_update_scheduler seam used in tests.
    """

    class _SchedulerStub:
        async def force_update(self, source: str | None = None) -> dict[str, Any]:
            _ = source
            if usda_result is not None:
                return {"usda": usda_result}
            return {"usda": {"ok": True, "status": "stubbed"}}

    return _SchedulerStub()


def patch_app_get_update_scheduler(monkeypatch: Any, app_module: Any, scheduler: object) -> None:
    """
    Patch scheduler seam for force-update tests.
    Applies override to both `app` facade and `legacy_app` where endpoint resolves runtime getter.
    """

    async def _fake_get_update_scheduler() -> object:
        return scheduler

    monkeypatch.setattr(app_module, "get_update_scheduler", _fake_get_update_scheduler)
    try:
        import legacy_app as legacy_app_mod
    except ModuleNotFoundError:
        return
    monkeypatch.setattr(
        legacy_app_mod, "get_update_scheduler", _fake_get_update_scheduler, raising=False
    )


def patch_background_update_callables(
    monkeypatch: Any,
    *,
    start: object | None = None,
    stop: object | None = None,
) -> None:
    """
    Patch background update callables across facade and legacy aliases.
    Applies the same callable to `app`, `legacy_app`, and `app_module`.
    """

    import app as app_module
    import legacy_app as legacy_app_mod

    modules: list[Any] = [app_module, legacy_app_mod, sys.modules.get("app_module")]
    seen: set[int] = set()
    for module in modules:
        if module is None:
            continue
        module_id = id(module)
        if module_id in seen:
            continue
        seen.add(module_id)
        if start is not None:
            monkeypatch.setattr(module, "start_background_updates", start, raising=False)
        if stop is not None:
            monkeypatch.setattr(module, "stop_background_updates", stop, raising=False)


def patch_background_update_scheduler_targets(
    monkeypatch: Any,
    *,
    start: object | None = None,
    stop: object | None = None,
) -> None:
    """
    Patch scheduler backend targets across facade and legacy aliases.
    Keeps wrapper tests stable when resolver precedence changes between aliases.
    """

    import app as app_module
    import legacy_app as legacy_app_mod

    modules: list[Any] = [app_module, legacy_app_mod, sys.modules.get("app_module")]
    seen: set[int] = set()
    for module in modules:
        if module is None:
            continue
        module_id = id(module)
        if module_id in seen:
            continue
        seen.add(module_id)
        if start is not None:
            monkeypatch.setattr(module, "_scheduler_start_background_updates", start, raising=False)
        if stop is not None:
            monkeypatch.setattr(module, "_scheduler_stop_background_updates", stop, raising=False)


def patch_unified_db_common_foods_fast(monkeypatch: Any) -> None:
    """
    Patch UnifiedFoodDatabase.get_common_foods_database to return a tiny DB fast.
    Keeps method async and avoids IO/cache work.
    """
    from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

    async def _fast_common_foods(self: UnifiedFoodDatabase) -> dict[str, UnifiedFoodItem]:
        return {
            "oats": UnifiedFoodItem(
                name="oats",
                nutrients_per_100g={"protein_g": 13.0, "fat_g": 7.0, "carbs_g": 66.0},
                cost_per_100g=0.5,
                tags=["grain"],
                availability_regions=["US", "EU"],
                source="stub",
                source_id="oats_stub",
                category="grains",
            ),
            "rice": UnifiedFoodItem(
                name="rice",
                nutrients_per_100g={"protein_g": 2.7, "fat_g": 0.3, "carbs_g": 28.0},
                cost_per_100g=0.3,
                tags=["grain"],
                availability_regions=["US", "EU"],
                source="stub",
                source_id="rice_stub",
                category="grains",
            ),
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
