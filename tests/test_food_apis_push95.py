# -*- coding: utf-8 -*-
"""Push core.food_apis coverage to 95%+ with extra edges."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch


def test_usda_fooditem_to_menu_format():
    from core.food_apis.usda_client import USDAFoodItem

    item = USDAFoodItem(
        fdc_id=10,
        description="Spinach raw",
        food_category="Vegetables",
        nutrients_per_100g={"protein_g": 3.0, "fat_g": 0.4, "carbs_g": 3.6},
        data_type="SR Legacy",
        publication_date=None,
    )
    d = item.to_menu_engine_format()
    assert d["name"].startswith("Spinach")
    assert d["fdc_id"] == 10


def test_usda_client_parse_exception_branch():
    from core.food_apis.usda_client import USDAClient

    c = USDAClient(api_key="X")
    # Break internal mapping to trigger exception path
    c.nutrient_mapping = None  # type: ignore[assignment]
    bad = {
        "fdcId": 1,
        "description": "x",
        "foodNutrients": [{"nutrientId": 1003, "value": 1.0}],
    }
    assert c._parse_food_item(bad) is None


def test_usda_common_foods_database():
    from core.food_apis.usda_client import (
        USDAClient,
        USDAFoodItem,
        get_common_foods_database,
    )

    async def _search(self, q: str, page_size: int = 5):
        return [
            USDAFoodItem(
                fdc_id=1,
                description=q,
                food_category=None,
                nutrients_per_100g={"protein_g": 1.0, "fat_g": 1.0, "carbs_g": 1.0},
                data_type="SR Legacy",
                publication_date=None,
            )
        ]

    loop = asyncio.new_event_loop()
    try:
        with patch.object(USDAClient, "search_foods", _search), patch(
            "core.food_apis.usda_client.asyncio.sleep", new=AsyncMock()
        ):
            out = loop.run_until_complete(get_common_foods_database())
        assert out and isinstance(next(iter(out.values())), USDAFoodItem)
    finally:
        loop.close()


def test_unified_db_common_cache_error_and_save_error(tmp_path: Path):
    from core.food_apis.unified_db import UnifiedFoodDatabase

    cache_dir = tmp_path / "cdb"
    cache_dir.mkdir(parents=True, exist_ok=True)
    # Write broken cache file to trigger load error (202-203)
    (cache_dir / "common_foods.json").write_text("{ broken json")

    db = UnifiedFoodDatabase(str(cache_dir))

    async def _search_food(q):
        return []

    loop = asyncio.new_event_loop()
    try:
        # Patch search to avoid network and patch open to fail on save (252-253)
        with patch.object(db, "search_food", _search_food), patch(
            "core.food_apis.unified_db.asyncio.sleep", new=AsyncMock()
        ), patch("builtins.open", side_effect=OSError("fail")):
            res = loop.run_until_complete(db.get_common_foods_database())
        assert isinstance(res, dict)
    finally:
        loop.run_until_complete(db.close())
        loop.close()


def test_unified_search_foods_unified(tmp_path: Path):
    from core.food_apis.unified_db import search_foods_unified

    async def _get_db():
        class _DB:
            async def search_food(self, q: str):
                from core.food_apis.unified_db import UnifiedFoodItem

                return [
                    UnifiedFoodItem(
                        name="X",
                        nutrients_per_100g={
                            "protein_g": 1.0,
                            "fat_g": 1.0,
                            "carbs_g": 1.0,
                        },
                        cost_per_100g=1.0,
                        tags=["VEG"],
                        availability_regions=["US"],
                        source="USDA FoodData Central",
                        source_id="1",
                        category=None,
                    )
                ]

        return _DB()

    loop = asyncio.new_event_loop()
    with patch("core.food_apis.unified_db.get_unified_food_db", _get_db):
        out = loop.run_until_complete(search_foods_unified("x"))
    assert out and isinstance(out[0], dict)
    loop.close()


def test_update_manager_more_edges(tmp_path: Path):
    from core.food_apis.update_manager import (
        DatabaseUpdateManager,
        DatabaseVersion,
        run_scheduled_update,
    )

    m = DatabaseUpdateManager(cache_dir=str(tmp_path / "m"), update_interval_hours=0)
    loop = asyncio.new_event_loop()

    # check_for_updates success assignment (145)
    m._check_usda_updates = AsyncMock(return_value=True)  # type: ignore[attr-defined]
    updates = loop.run_until_complete(m.check_for_updates())
    assert updates.get("usda") is True

    # _check_usda_updates True branch (170)
    m.versions["usda"] = DatabaseVersion(
        source="usda",
        version="v0",
        last_updated="2020-01-01T00:00:00",
        record_count=0,
        checksum="x",
        metadata={},
    )
    ok = loop.run_until_complete(m._check_usda_updates())
    assert ok is True

    # Update callbacks exception path (208-209)
    m.unified_db.get_common_foods_database = AsyncMock(return_value={})  # type: ignore[assignment]

    def _bad_cb(res):
        raise RuntimeError("cb")

    m.update_callbacks = [_bad_cb]
    _ = loop.run_until_complete(m.update_database("usda"))

    # _load_backup warning path (266-269)
    from core.food_apis.update_manager import DatabaseVersion as DV

    m.versions["usda"] = DV(
        source="usda",
        version="v1",
        last_updated="2020-01-01T00:00:00",
        record_count=0,
        checksum="x",
        metadata={},
    )
    m.unified_db.get_common_foods_database = AsyncMock(return_value={})  # type: ignore[assignment]
    m._load_backup = AsyncMock(side_effect=RuntimeError("x"))  # type: ignore[attr-defined]
    _ = loop.run_until_complete(m.update_database("usda", force=True))

    # _cleanup_old_backups exception path (374-380)
    with patch("pathlib.Path.glob", side_effect=OSError("x")):
        loop.run_until_complete(m._cleanup_old_backups("usda"))

    # run_scheduled_update else branch (497)
    m.check_for_updates = AsyncMock(return_value={"usda": False})  # type: ignore[assignment]
    empty = loop.run_until_complete(run_scheduled_update(m))
    assert isinstance(empty, dict)

    loop.run_until_complete(m.close())
    loop.close()


def test_scheduler_remaining_edges():
    import core.food_apis.scheduler as sched_mod
    from core.food_apis.scheduler import (
        DatabaseUpdateScheduler,
        start_background_updates,
        stop_background_updates,
    )

    # 109-110: ensure CancelledError branch by cancelling a sleeping task
    loop = asyncio.new_event_loop()
    s = DatabaseUpdateScheduler(update_interval_hours=0)
    # Replace background task with a long sleep so cancel triggers CancelledError
    s.is_running = True
    s._update_task = loop.create_task(asyncio.sleep(3600))  # type: ignore[attr-defined]
    loop.run_until_complete(s.stop())

    # 164-165: _run_update_check exception path
    s2 = DatabaseUpdateScheduler(update_interval_hours=0)
    s2.update_manager = AsyncMock()
    s2.update_manager.check_for_updates = AsyncMock(side_effect=RuntimeError("x"))
    loop.run_until_complete(s2._run_update_check())

    # 186-188: _run_source_update exception path
    s2.update_manager.update_database = AsyncMock(side_effect=RuntimeError("x"))
    loop.run_until_complete(s2._run_source_update("usda"))

    # 278-281: start_background_updates hitting start
    class _Sched:
        def __init__(self):
            self.is_running = False

        async def start(self):
            self.is_running = True

    with patch.object(
        sched_mod, "get_update_scheduler", new=AsyncMock(return_value=_Sched())
    ):
        loop.run_until_complete(start_background_updates(update_interval_hours=2))

    # 290-292: stop_background_updates path
    class _Sched2:
        def __init__(self):
            self.is_running = True

        async def stop(self):
            self.is_running = False

    sched_mod._scheduler_instance = _Sched2()  # type: ignore[attr-defined]
    loop.run_until_complete(stop_background_updates())
    loop.close()
