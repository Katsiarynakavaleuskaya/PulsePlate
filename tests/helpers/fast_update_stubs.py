from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Protocol, TypeVar, cast


class SchedulerLike(Protocol):
    async def force_update(self, source: str | None = None) -> dict[str, Any]: ...


PersistedVersionStoreTarget = TypeVar("PersistedVersionStoreTarget")


def add_persisted_version_store_stub(
    update_manager: PersistedVersionStoreTarget,
    tmp_path: Path,
) -> PersistedVersionStoreTarget:
    """Add the persisted-version surface required by leased rollback tests."""

    versions_file = tmp_path / "database_versions.json"
    assert not versions_file.exists()

    versions: dict[str, Any] = {}
    persisted_store = cast(Any, update_manager)
    persisted_store.versions_file = versions_file
    persisted_store.versions = versions

    def _load_versions() -> dict[str, Any]:
        """Return the stable in-memory versions mapping for this fixture."""

        return versions

    persisted_store._load_versions = _load_versions
    return update_manager


def make_scheduler_stub(usda_result: Any = None) -> SchedulerLike:
    """
    Return a scheduler-like object with async force_update.
    Matches the scheduler object consumed by admin_operations tests.
    """

    class _SchedulerStub:
        async def force_update(self, source: str | None = None) -> dict[str, Any]:
            _ = source
            if usda_result is not None:
                return {"usda": usda_result}
            return {
                "usda": SimpleNamespace(
                    success=True,
                    old_version="1.0",
                    new_version="1.1",
                    records_added=1,
                    records_updated=0,
                    records_removed=0,
                    duration_seconds=0.01,
                    errors=[],
                )
            }

    return _SchedulerStub()


def patch_admin_get_update_scheduler(monkeypatch: Any, scheduler: object) -> None:
    """Patch the canonical admin-service consumer binding."""

    from app.services import admin_operations

    async def _fake_get_update_scheduler() -> object:
        return scheduler

    monkeypatch.setattr(
        admin_operations,
        "get_update_scheduler",
        _fake_get_update_scheduler,
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
