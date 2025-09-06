# -*- coding: utf-8 -*-
"""Extra edge-case coverage for core.food_apis.* modules."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx


def test_unified_db_cache_hits(tmp_path: Path):
    from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

    db = UnifiedFoodDatabase(str(tmp_path / "cache1"))

    # Seed memory cache entries
    key = "search_oats"
    db._memory_cache[key] = UnifiedFoodItem(
        name="Oats",
        nutrients_per_100g={"protein_g": 10, "fat_g": 5, "carbs_g": 20},
        cost_per_100g=1.0,
        tags=["VEG"],
        availability_regions=["US"],
        source="USDA FoodData Central",
        source_id="1",
        category=None,
    )
    # Save cache to disk to cover save
    db._save_cache()

    # Second call to search should hit fast-return path (line 133)
    loop = asyncio.new_event_loop()
    res = loop.run_until_complete(db.search_food("oats"))
    assert res and res[0].name == "Oats"

    # get_by_id cache hit path (line 165)
    db._memory_cache["usda_7"] = db._memory_cache[key]
    item2 = loop.run_until_complete(db.get_food_by_id("usda", "7"))
    assert item2 is not None

    loop.run_until_complete(db.close())
    loop.close()


def test_update_manager_unknown_source_and_save_versions_error(tmp_path: Path):
    from core.food_apis.update_manager import DatabaseUpdateManager

    m = DatabaseUpdateManager(cache_dir=str(tmp_path / "u"), update_interval_hours=0)

    # Unknown source path (189-199)
    loop = asyncio.new_event_loop()
    out = loop.run_until_complete(m.update_database("off"))
    assert out.success is False and "Unknown source" in out.errors[0]

    # _save_versions error path (124)
    with patch("builtins.open", side_effect=OSError("no disk")):
        m._save_versions()

    loop.run_until_complete(m.close())
    loop.close()


def test_update_manager_check_for_updates_error(tmp_path: Path):
    from core.food_apis.update_manager import DatabaseUpdateManager

    m = DatabaseUpdateManager(cache_dir=str(tmp_path / "c"), update_interval_hours=1)
    m._check_usda_updates = AsyncMock(side_effect=RuntimeError("bad"))  # type: ignore[attr-defined]
    loop = asyncio.new_event_loop()
    updates = loop.run_until_complete(m.check_for_updates())
    assert updates.get("usda") is False
    loop.run_until_complete(m.close())
    loop.close()


def test_update_manager_backup_cleanup(tmp_path: Path):
    from core.food_apis.update_manager import DatabaseUpdateManager

    cache = tmp_path / "b"
    cache.mkdir()
    # create fake backup files
    for i in range(8):
        p = cache / f"usda_backup_v{i}.json"
        p.write_text("{}")

    m = DatabaseUpdateManager(
        cache_dir=str(cache), update_interval_hours=0, max_rollback_versions=3
    )
    loop = asyncio.new_event_loop()
    # Remove older backups beyond retention (should not raise)
    loop.run_until_complete(m._cleanup_old_backups("usda"))
    # Ensure only <=3 remaining
    left = list(cache.glob("usda_backup_*.json"))
    assert len(left) <= 3
    loop.run_until_complete(m.close())
    loop.close()


def test_usda_client_error_paths():
    from core.food_apis.usda_client import USDAClient

    class _ErrAC:
        async def aclose(self):
            return None

        async def get(self, *a, **kw):
            raise httpx.RequestError("boom")

        async def post(self, *a, **kw):
            raise httpx.RequestError("boom")

    c = USDAClient(api_key="X")
    c.client = _ErrAC()  # type: ignore[assignment]
    loop = asyncio.new_event_loop()
    assert loop.run_until_complete(c.search_foods("x")) == []
    assert loop.run_until_complete(c.get_food_details(1)) is None
    assert loop.run_until_complete(c.get_multiple_foods([1])) == []
    loop.run_until_complete(c.close())
    loop.close()


def test_scheduler_signal_handlers_and_loop_errors():
    # Patch signal.signal to immediately invoke provided handler to hit lines 66-67
    import core.food_apis.scheduler as sched_mod
    from core.food_apis.scheduler import DatabaseUpdateScheduler

    def fake_signal(sig, handler):
        # Immediately invoke handler (signum, frame)
        try:
            handler(sig, None)
        except Exception:
            pass
        return None

    def fake_create_task(coro):
        # Prevent 'coroutine was never awaited' warnings by closing it
        try:
            coro.close()
        except Exception:
            pass
        return MagicMock()

    with (
        patch.object(sched_mod.signal, "signal", side_effect=fake_signal),
        patch.object(sched_mod.asyncio, "create_task", side_effect=fake_create_task) as mk,
    ):
        s = DatabaseUpdateScheduler(update_interval_hours=0)
        # create_task should be called by handler; also use `s` to satisfy linter
        assert isinstance(s, DatabaseUpdateScheduler)
        assert mk.called

    # Cover stop() early return (line 99)
    loop = asyncio.new_event_loop()
    s2 = DatabaseUpdateScheduler(update_interval_hours=0)
    loop.run_until_complete(s2.stop())  # not running -> return path

    # Cover _update_loop exception branch (134-137)
    s2.is_running = True
    s2._run_update_check = AsyncMock(side_effect=RuntimeError("x"))  # type: ignore[attr-defined]

    async def fast_sleep(_):
        # Stop after first exception path
        s2.is_running = False
        return None

    with patch.object(sched_mod.asyncio, "sleep", side_effect=fast_sleep):
        loop.run_until_complete(s2._update_loop())

    loop.close()
