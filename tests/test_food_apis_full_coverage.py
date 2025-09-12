# -*- coding: utf-8 -*-
"""Full coverage tests for core.food_apis modules.

Covers:
- usda_client: parsing variants, success/error paths
- unified_db: cache load/save, search, get by id, common foods
- update_manager: check/update workflows, callbacks, rollback, statuses
- scheduler: start/stop, update loops, force_update, status
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------- USDA Client -----------------


def _usda_food(min_nutrients: bool = True) -> Dict[str, Any]:
    # Construct USDA-like payload with nutrientId mapping and nested nutrient.id
    foods = {
        "fdcId": 123,
        "description": "Chicken breast cooked",
        "dataType": "SR Legacy",
        "publicationDate": "2020-01-01",
        "foodCategory": {"description": "Poultry"},
        "foodNutrients": [],
    }
    # Add nutrients
    if min_nutrients:
        foods["foodNutrients"].extend(
            [
                {"nutrientId": 1003, "value": 31.0},  # protein_g
                {"nutrientId": 1004, "value": 3.6},  # fat_g
                {"nutrientId": 1005, "value": 0.0},  # carbs_g
                {"nutrient": {"id": 1008}, "amount": 165.0},  # kcal via nested
            ]
        )
    else:
        foods["foodNutrients"].append({"nutrientId": 1003, "value": 5.0})
    return foods


def test_usda_client_parse_and_requests():
    from core.food_apis.usda_client import USDAClient

    client = USDAClient(api_key="TEST")

    # Patch internal AsyncClient to control responses
    class _Resp:
        def __init__(self, data: Any):
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class _AC:
        async def aclose(self):
            return None

        async def get(self, url: str, *a, **kw):
            if url.endswith("/foods/search"):
                return _Resp({"foods": [_usda_food(True)]})
            # details
            return _Resp(_usda_food(True))

        async def post(self, url: str, *a, **kw):
            return _Resp([_usda_food(True), _usda_food(True)])

    client.client = _AC()  # type: ignore[assignment]

    # search_foods
    loop = asyncio.new_event_loop()
    try:
        foods = loop.run_until_complete(client.search_foods("chicken", page_size=2))
    finally:
        pass
    assert foods and foods[0].description.startswith("Chicken")

    # get_food_details
    food = loop.run_until_complete(client.get_food_details(123))
    assert food and food.fdc_id == 123

    # get_multiple_foods
    foods2 = loop.run_until_complete(client.get_multiple_foods([1, 2, 3]))
    assert len(foods2) == 2

    # _parse_food_item invalids
    assert client._parse_food_item("not-a-dict") is None  # type: ignore[arg-type]
    assert client._parse_food_item(_usda_food(False)) is None

    loop.run_until_complete(client.close())
    loop.close()


# ---------------- Unified DB -----------------


def test_unified_db_cache_search_get_by_id(tmp_path: Path):
    from core.food_apis.unified_db import UnifiedFoodDatabase
    from core.food_apis.usda_client import USDAFoodItem

    cache_dir = tmp_path / "food_cache"
    db = UnifiedFoodDatabase(str(cache_dir))

    # Patch USDA client methods
    async def _search_foods(q: str, page_size: int = 5):
        return [
            USDAFoodItem(
                fdc_id=1,
                description="Oats",
                food_category="Cereals",
                nutrients_per_100g={"protein_g": 13.0, "fat_g": 7.0, "carbs_g": 69.0},
                data_type="SR Legacy",
                publication_date=None,
            )
        ]

    async def _get_details(fid: int):
        return USDAFoodItem(
            fdc_id=fid,
            description="ItemX",
            food_category=None,
            nutrients_per_100g={"protein_g": 10.0, "fat_g": 5.0, "carbs_g": 20.0},
            data_type="SR Legacy",
            publication_date=None,
        )

    db.usda_client.search_foods = _search_foods  # type: ignore[assignment]
    db.usda_client.get_food_details = _get_details  # type: ignore[assignment]

    # search_food uses cache save path
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(db.search_food("oats"))
    assert r and r[0].name == "Oats"
    # get_food_by_id valid
    item = loop.run_until_complete(db.get_food_by_id("usda", "42"))
    assert item and item.source_id == "42"
    # invalid id path
    assert loop.run_until_complete(db.get_food_by_id("usda", "bad")) is None

    loop.run_until_complete(db.close())
    loop.close()


def test_unified_db_common_foods_cache(tmp_path: Path):
    from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

    cache_dir = tmp_path / "food_common"
    db = UnifiedFoodDatabase(str(cache_dir))

    async def _search_food(q: str):
        return [
            UnifiedFoodItem(
                name=f"{q}-X",
                nutrients_per_100g={"protein_g": 10.0, "fat_g": 5.0, "carbs_g": 20.0},
                cost_per_100g=1.0,
                tags=["VEG"],
                availability_regions=["US"],
                source="USDA FoodData Central",
                source_id="1",
                category=None,
            )
        ]

    # Patch internal search to avoid API
    loop = asyncio.new_event_loop()
    with (
        patch.object(db, "search_food", _search_food),
        patch("core.food_apis.unified_db.asyncio.sleep", new=AsyncMock()),
    ):
        foods_db = loop.run_until_complete(db.get_common_foods_database())
        assert foods_db and isinstance(next(iter(foods_db.values())), UnifiedFoodItem)

    # Second instance should load from cache file
    db2 = UnifiedFoodDatabase(str(cache_dir))
    with patch("core.food_apis.unified_db.asyncio.sleep", new=AsyncMock()):
        foods_db2 = loop.run_until_complete(db2.get_common_foods_database())
    assert foods_db2
    loop.run_until_complete(db.close())
    loop.run_until_complete(db2.close())
    loop.close()


# ---------------- Update Manager -----------------


def _mk_unified_item(name: str) -> Any:
    from core.food_apis.unified_db import UnifiedFoodItem

    return UnifiedFoodItem(
        name=name,
        nutrients_per_100g={"protein_g": 10.0, "fat_g": 5.0, "carbs_g": 20.0},
        cost_per_100g=1.0,
        tags=["VEG"],
        availability_regions=["US"],
        source="USDA FoodData Central",
        source_id="1",
        category=None,
    )


def test_update_manager_update_paths(tmp_path: Path):
    from core.food_apis.update_manager import (
        DatabaseUpdateManager,
        DatabaseVersion,
        run_scheduled_update,
    )

    cache_dir = tmp_path / "upd"
    m = DatabaseUpdateManager(cache_dir=str(cache_dir), update_interval_hours=0)

    # Happy path with changes
    foods = {"oats": _mk_unified_item("Oats")}
    m.unified_db.get_common_foods_database = AsyncMock(return_value=foods)  # type: ignore[assignment]
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(m.update_database("usda"))
    assert r.success and r.new_version

    # No changes path (checksum equal) without force
    dv = m.versions["usda"]
    m.versions["usda"] = DatabaseVersion(
        source="usda",
        version=dv.version,
        last_updated=dv.last_updated,
        record_count=dv.record_count,
        checksum=dv.checksum,
        metadata={},
    )
    r2 = loop.run_until_complete(m.update_database("usda"))
    assert r2.success and r2.new_version == r2.old_version

    # Validation errors path (force to bypass no-change short-circuit)
    m._validate_food_data = AsyncMock(return_value=["bad"])  # type: ignore[attr-defined]
    r3 = loop.run_until_complete(m.update_database("usda", force=True))
    assert r3.success is False and r3.errors

    # Exception path
    m.unified_db.get_common_foods_database = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[assignment]
    r4 = loop.run_until_complete(m.update_database("usda"))
    assert r4.success is False and "boom" in r4.errors[0]

    # Callback coverage
    seen = {}

    def _cb(res):
        seen[res.source] = res.success

    m.update_callbacks.clear()
    m.add_update_callback(_cb)
    m.unified_db.get_common_foods_database = AsyncMock(return_value=foods)  # type: ignore[assignment]
    _ = loop.run_until_complete(m.update_database("usda"))
    assert seen.get("usda") is not None

    # run_scheduled_update: depends on check_for_updates
    m.check_for_updates = AsyncMock(return_value={"usda": True})  # type: ignore[assignment]
    m.update_database = AsyncMock(return_value=r)  # type: ignore[assignment]
    res_map = loop.run_until_complete(run_scheduled_update(m))
    assert "usda" in res_map

    loop.run_until_complete(m.close())
    loop.close()


def test_update_manager_rollback_and_status(tmp_path: Path):
    from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

    cache_dir = tmp_path / "upd2"
    m = DatabaseUpdateManager(cache_dir=str(cache_dir), update_interval_hours=0)
    # Seed a version
    m.versions["usda"] = DatabaseVersion(
        source="usda",
        version="v1",
        last_updated="2020-01-01T00:00:00",
        record_count=1,
        checksum="deadbeef",
        metadata={},
    )

    # Successful rollback
    foods = {"oats": _mk_unified_item("Oats")}
    m._load_backup = AsyncMock(return_value=foods)  # type: ignore[attr-defined]
    loop = asyncio.new_event_loop()
    ok = loop.run_until_complete(m.rollback_database("usda", "v1"))
    assert ok is True

    # Error path
    m._load_backup = AsyncMock(side_effect=RuntimeError("x"))  # type: ignore[attr-defined]
    ok2 = loop.run_until_complete(m.rollback_database("usda", "v1"))
    assert ok2 is False

    # get_database_status
    status = m.get_database_status()
    assert "usda" in status

    loop.run_until_complete(m.close())
    loop.close()


# ---------------- Scheduler -----------------


def test_scheduler_paths():
    from core.food_apis.scheduler import DatabaseUpdateScheduler
    from core.food_apis.update_manager import UpdateResult

    s = DatabaseUpdateScheduler(update_interval_hours=0, max_retries=2)

    # Replace update_manager with controllable mock
    s.update_manager = AsyncMock()
    s.update_manager.check_for_updates = AsyncMock(return_value={"usda": False})
    s.update_manager.update_database = AsyncMock(
        return_value=UpdateResult(
            success=True,
            source="usda",
            old_version=None,
            new_version="v2",
            records_added=1,
            records_updated=0,
            records_removed=0,
            errors=[],
            duration_seconds=0.1,
        )
    )
    s.update_manager.get_database_status = MagicMock(return_value={"usda": {"ok": True}})
    s.update_manager.close = AsyncMock()

    # _should_check_for_updates
    from datetime import datetime

    s.last_update_check = None
    assert s._should_check_for_updates(datetime.now()) is True

    # _run_update_check with no updates
    loop = asyncio.new_event_loop()
    loop.run_until_complete(s._run_update_check())

    # with available update
    s.update_manager.check_for_updates = AsyncMock(return_value={"usda": True})
    loop.run_until_complete(s._run_update_check())
    assert s.update_manager.update_database.await_count >= 1

    # _run_source_update success resets retry count
    loop.run_until_complete(s._run_source_update("usda"))
    assert s.retry_counts.get("usda", 0) == 0

    # Failure then retry count increments
    s.update_manager.update_database = AsyncMock(
        return_value=UpdateResult(
            success=False,
            source="usda",
            old_version=None,
            new_version=None,
            records_added=0,
            records_updated=0,
            records_removed=0,
            errors=["e"],
            duration_seconds=0.1,
        )
    )
    loop.run_until_complete(s._run_source_update("usda"))
    assert s.retry_counts.get("usda", 0) == 1

    # Force exceed max_retries path
    s.retry_counts["usda"] = s.max_retries - 1
    loop.run_until_complete(s._run_source_update("usda"))
    assert s.retry_counts.get("usda", 0) == 0

    # force_update source-specific and None
    s.update_manager.update_database = AsyncMock(
        return_value=UpdateResult(
            success=True,
            source="usda",
            old_version="v1",
            new_version="v2",
            records_added=1,
            records_updated=0,
            records_removed=0,
            errors=[],
            duration_seconds=0.1,
        )
    )
    out1 = loop.run_until_complete(s.force_update("usda"))
    assert "usda" in out1

    s.update_manager.check_for_updates = AsyncMock(return_value={"usda": True, "off": False})
    out2 = loop.run_until_complete(s.force_update(None))
    assert "usda" in out2

    # get_status
    status = s.get_status()
    assert status["scheduler"]["is_running"] is False

    # start/stop
    loop.run_until_complete(s.start())
    # Calling start again should warn and return
    loop.run_until_complete(s.start())
    loop.run_until_complete(s.stop())
    loop.close()
