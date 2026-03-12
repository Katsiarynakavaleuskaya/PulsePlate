from __future__ import annotations

from collections.abc import Callable
import importlib
import sys
from types import ModuleType
from typing import Any, Protocol


class SchedulerLike(Protocol):
    async def force_update(self, source: str | None = None) -> dict[str, Any]: ...


BackgroundUpdateCallable = Callable[..., Any]


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


def _iter_background_modules() -> tuple[ModuleType, ...]:
    """Return unique module aliases consulted by background update resolvers."""

    import app as app_module

    modules: list[ModuleType] = [app_module]
    try:
        legacy_app_mod = importlib.import_module("legacy_app")
    except ModuleNotFoundError as exc:
        if exc.name != "legacy_app":
            raise
        legacy_app_mod = None
    if isinstance(legacy_app_mod, ModuleType):
        modules.append(legacy_app_mod)
    app_module_alias = sys.modules.get("app_module")
    if isinstance(app_module_alias, ModuleType):
        modules.append(app_module_alias)

    unique_modules: list[ModuleType] = []
    seen: set[int] = set()
    for module in modules:
        module_id = id(module)
        if module_id in seen:
            continue
        seen.add(module_id)
        unique_modules.append(module)
    return tuple(unique_modules)


def _patch_background_module_attr(
    monkeypatch: Any,
    module: ModuleType,
    attr_name: str,
    value: BackgroundUpdateCallable,
) -> None:
    """Patch app facade via module dict and legacy aliases via setattr cleanup."""

    if module.__name__ == "app":
        monkeypatch.setitem(module.__dict__, attr_name, value)
        return
    monkeypatch.setattr(module, attr_name, value, raising=False)


def patch_background_update_callables(
    monkeypatch: Any,
    *,
    start: BackgroundUpdateCallable | None = None,
    stop: BackgroundUpdateCallable | None = None,
) -> None:
    """
    Patch background update callables across facade and legacy aliases.
    Applies the same callable to `app`, `legacy_app`, and `app_module`.
    """
    for module in _iter_background_modules():
        if start is not None:
            _patch_background_module_attr(monkeypatch, module, "start_background_updates", start)
        if stop is not None:
            _patch_background_module_attr(monkeypatch, module, "stop_background_updates", stop)


def patch_background_update_scheduler_targets(
    monkeypatch: Any,
    *,
    start: BackgroundUpdateCallable | None = None,
    stop: BackgroundUpdateCallable | None = None,
) -> None:
    """
    Patch scheduler backend targets across facade and legacy aliases.
    Keeps wrapper tests stable when resolver precedence changes between aliases.
    """
    for module in _iter_background_modules():
        if start is not None:
            _patch_background_module_attr(
                monkeypatch, module, "_scheduler_start_background_updates", start
            )
        if stop is not None:
            _patch_background_module_attr(
                monkeypatch, module, "_scheduler_stop_background_updates", stop
            )


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
