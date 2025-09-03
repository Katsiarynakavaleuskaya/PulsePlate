import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core.food_apis.openfoodfacts_client import OFFClient, OFFFoodItem
from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem
from core.food_apis.update_manager import (
    DatabaseUpdateManager,
    DatabaseVersion,
)


def make_off_item(name: str = "Vegetarian Snack") -> OFFFoodItem:
    return OFFFoodItem(
        code="code-1",
        product_name=name,
        categories=["Snacks"],
        nutrients_per_100g={"protein_g": 5.0, "fat_g": 10.0, "carbs_g": 50.0},
        ingredients_text=None,
        brands=None,
        labels=["Vegetarian"],
        countries=["World"],
        packaging=[],
        image_url=None,
        last_modified_t=0,
    )


@pytest.mark.asyncio
async def test_off_item_vegetarian_tag_and_gather_exception(monkeypatch):
    # Cover VEG tag path (line ~77)
    item = make_off_item()
    assert "VEG" in item._generate_tags()

    # Cover get_multiple_products exception -> logger.error path (line ~305)
    client = OFFClient()

    async def ok(_):
        return make_off_item("Ok Product")

    async def boom(_):
        raise RuntimeError("boom")

    # Patch methods on the instance
    monkeypatch.setattr(client, "get_product_details", lambda code: ok(code) if code == "1" else boom(code))
    results = await client.get_multiple_products(["1", "2"])  # one ok, one exception
    assert len(results) == 1 and results[0].product_name == "Ok Product"
    await client.close()


@pytest.mark.asyncio
async def test_unified_db_off_paths_and_exceptions(tmp_path, monkeypatch):
    db = UnifiedFoodDatabase(cache_dir=str(tmp_path))

    # Cover from_off_item constructor path (line ~74)
    u = UnifiedFoodItem.from_off_item(make_off_item())
    assert u.source == "Open Food Facts"

    # Stub OFF client that raises on search_products
    class StubOFF:
        async def search_products(self, *_args, **_kwargs):
            raise RuntimeError("search failed")

        async def get_product_details(self, *_args, **_kwargs):
            raise RuntimeError("details failed")

        async def close(self):
            return None

    db.off_client = StubOFF()

    # Prefer OFF to trigger exception branch (lines ~185-192)
    res = await db.search_food("anything", prefer_source="openfoodfacts")
    assert isinstance(res, list)

    # get_food_by_id OFF branch exception (lines ~224-229)
    res2 = await db.get_food_by_id("openfoodfacts", "X")
    assert res2 is None

    await db.close()


@pytest.mark.asyncio
async def test_update_manager_off_branches(tmp_path, monkeypatch):
    mgr = DatabaseUpdateManager(cache_dir=str(tmp_path), update_interval_hours=1)

    # Force presence of OFF client and an existing version to hit backup path (~358)
    now_iso = datetime.now().isoformat()
    mgr.versions["openfoodfacts"] = DatabaseVersion(
        source="openfoodfacts",
        version="v1",
        last_updated=now_iso,
        record_count=0,
        checksum="abc",
        metadata={},
    )

    # Cover check_for_updates exception branch (~157-159)
    async def raise_off():
        raise RuntimeError("check failed")

    monkeypatch.setattr(mgr, "_check_off_updates", raise_off)
    updates = await mgr.check_for_updates()
    assert "openfoodfacts" in updates and updates["openfoodfacts"] is False

    # Prepare OFF client stub for _update_off_database, including one good result
    class StubOFF2:
        async def search_products(self, term, page_size=5):
            if term == "banana":
                return [make_off_item("Banana Bar")]
            return []

        async def close(self):
            return None

    mgr.off_client = StubOFF2()

    # Relax validation to avoid requiring all nutrients during test
    async def no_errors(_foods):
        return []

    monkeypatch.setattr(mgr, "_validate_food_data", no_errors)

    # Also ensure backup load returns empty to simplify diff calc
    async def load_backup(_s, _v):
        return {}

    monkeypatch.setattr(mgr, "_load_backup", load_backup)

    # Avoid network in backup step
    async def fake_common_db():
        return {}

    monkeypatch.setattr(mgr.unified_db, "get_common_foods_database", fake_common_db)

    result = await mgr._update_off_database(force=True)
    assert result.success is True and result.source == "openfoodfacts"

    # Cover _generate_food_key (~488-491)
    key = mgr._generate_food_key("Spicy Chili & Rice!")
    # Current implementation may keep double underscores when removing punctuation
    assert key == "spicy_chili__rice"

    await mgr.close()


@pytest.mark.asyncio
async def test_off_updates_recent_returns_false(tmp_path):
    # _check_off_updates should return False if last update < update_interval
    mgr = DatabaseUpdateManager(cache_dir=str(tmp_path), update_interval_hours=24)
    now_iso = datetime.now().isoformat()
    mgr.versions["openfoodfacts"] = DatabaseVersion(
        source="openfoodfacts",
        version="v1",
        last_updated=now_iso,
        record_count=0,
        checksum="abc",
        metadata={},
    )
    res = await mgr._check_off_updates()
    assert res is False
    await mgr.close()


@pytest.mark.asyncio
async def test_update_manager_off_conversion_and_backup_warning(tmp_path, monkeypatch):
    mgr = DatabaseUpdateManager(cache_dir=str(tmp_path), update_interval_hours=1)

    # Ensure a current version exists to hit backup and old load logic
    mgr.versions["openfoodfacts"] = DatabaseVersion(
        source="openfoodfacts",
        version="v1",
        last_updated=datetime.now().isoformat(),
        record_count=0,
        checksum="abc",
        metadata={},
    )

    # OFF client returns at least one product to attempt conversion
    class StubOFF3:
        async def search_products(self, *_args, **_kwargs):
            return [make_off_item("Bad Convert")]

        async def close(self):
            return None

    mgr.off_client = StubOFF3()

    # Force from_off_item to raise to trigger logger.warning at conversion
    def _raise_convert(_cls, _off_item):
        raise ValueError("convert fail")

    monkeypatch.setattr(UnifiedFoodItem, "from_off_item", classmethod(_raise_convert))

    # Force _load_backup to raise to trigger logger.warning on loading old data
    async def _raise_backup(_source, _version):
        raise RuntimeError("backup missing")

    monkeypatch.setattr(mgr, "_load_backup", _raise_backup)

    # Avoid network in backup creation during _create_backup
    async def fake_common_db():
        return {}

    monkeypatch.setattr(mgr.unified_db, "get_common_foods_database", fake_common_db)

    # Relax validation to pass with empty unified_foods
    async def no_errors(_foods):
        return []

    monkeypatch.setattr(mgr, "_validate_food_data", no_errors)

    result = await mgr._update_off_database(force=True)
    # Even with warnings, the update can still succeed with forced mode
    assert result.success is True and result.source == "openfoodfacts"
    await mgr.close()


@pytest.mark.asyncio
async def test_off_updates_old_returns_true(tmp_path):
    # When enough time has passed since last update, should return True (line ~195)
    mgr = DatabaseUpdateManager(cache_dir=str(tmp_path), update_interval_hours=24)
    old_iso = (datetime.now() - timedelta(hours=48)).isoformat()
    mgr.versions["openfoodfacts"] = DatabaseVersion(
        source="openfoodfacts",
        version="v0",
        last_updated=old_iso,
        record_count=0,
        checksum="zzz",
        metadata={},
    )
    res = await mgr._check_off_updates()
    assert res is True
    await mgr.close()


@pytest.mark.asyncio
async def test_update_manager_off_nochange_branch(tmp_path, monkeypatch):
    # Hit the "no change" branch (line ~398)
    mgr = DatabaseUpdateManager(cache_dir=str(tmp_path), update_interval_hours=1)
    mgr.versions["openfoodfacts"] = DatabaseVersion(
        source="openfoodfacts",
        version="v1",
        last_updated=(datetime.now() - timedelta(hours=2)).isoformat(),
        record_count=0,
        checksum="same",
        metadata={},
    )

    class StubOFF:
        async def search_products(self, *_args, **_kwargs):
            return []  # empty leads to empty unified_foods
        async def close(self):
            return None

    mgr.off_client = StubOFF()

    # Ensure checksum matches current version
    monkeypatch.setattr(mgr, "_calculate_checksum", lambda data: "same")
    monkeypatch.setattr(mgr, "_validate_food_data", lambda foods: [])
    monkeypatch.setattr(mgr, "_load_backup", lambda s, v: {})
    # Avoid network in backup creation
    monkeypatch.setattr(mgr.unified_db, "get_common_foods_database", lambda: {})

    result = await mgr._update_off_database(force=False)
    assert result.success is True
    assert result.new_version == "v1"  # unchanged
    await mgr.close()


@pytest.mark.asyncio
async def test_update_manager_off_validation_failure(tmp_path, monkeypatch):
    # Force validation failure path (line ~413)
    mgr = DatabaseUpdateManager(cache_dir=str(tmp_path), update_interval_hours=1)
    mgr.versions["openfoodfacts"] = DatabaseVersion(
        source="openfoodfacts",
        version="v1",
        last_updated=(datetime.now() - timedelta(hours=2)).isoformat(),
        record_count=0,
        checksum="old",
        metadata={},
    )

    class StubOFF:
        async def search_products(self, *_args, **_kwargs):
            return [make_off_item("Needs Validation")]  # non-empty
        async def close(self):
            return None

    mgr.off_client = StubOFF()

    # Different checksum to avoid no-change path
    monkeypatch.setattr(mgr, "_calculate_checksum", lambda data: "new")
    # Force validation errors
    async def with_errors(_foods):
        return ["error"]
    monkeypatch.setattr(mgr, "_validate_food_data", with_errors)
    monkeypatch.setattr(mgr, "_load_backup", lambda s, v: {})
    monkeypatch.setattr(mgr.unified_db, "get_common_foods_database", lambda: {})

    result = await mgr._update_off_database(force=False)
    assert result.success is False and result.errors
    await mgr.close()


@pytest.mark.asyncio
async def test_update_manager_off_exception_final(tmp_path, monkeypatch):
    # Cause an exception late to hit the final except block (lines ~471–473)
    mgr = DatabaseUpdateManager(cache_dir=str(tmp_path), update_interval_hours=1)
    mgr.versions["openfoodfacts"] = DatabaseVersion(
        source="openfoodfacts",
        version="v1",
        last_updated=(datetime.now() - timedelta(hours=2)).isoformat(),
        record_count=0,
        checksum="old",
        metadata={},
    )

    class StubOFF:
        async def search_products(self, *_args, **_kwargs):
            return [make_off_item("One Product")]
        async def close(self):
            return None

    mgr.off_client = StubOFF()

    # Different checksum to proceed with update
    monkeypatch.setattr(mgr, "_calculate_checksum", lambda data: "new")
    monkeypatch.setattr(mgr, "_validate_food_data", lambda foods: [])
    monkeypatch.setattr(mgr, "_load_backup", lambda s, v: {})
    monkeypatch.setattr(mgr.unified_db, "get_common_foods_database", lambda: {})
    # Raise when saving versions to land in final except
    monkeypatch.setattr(mgr, "_save_versions", lambda: (_ for _ in ()).throw(RuntimeError("save fail")))

    result = await mgr._update_off_database(force=False)
    assert result.success is False and result.errors
    await mgr.close()


@pytest.mark.asyncio
async def test_update_manager_off_search_warning(tmp_path, monkeypatch):
    # Trigger logger.warning in search loop (lines ~376–377)
    mgr = DatabaseUpdateManager(cache_dir=str(tmp_path), update_interval_hours=1)
    mgr.versions["openfoodfacts"] = DatabaseVersion(
        source="openfoodfacts",
        version="v1",
        last_updated=(datetime.now() - timedelta(hours=2)).isoformat(),
        record_count=0,
        checksum="old",
        metadata={},
    )

    class StubOFF:
        async def search_products(self, term, page_size=5):
            if term == "bread":
                raise RuntimeError("search error")
            return []
        async def close(self):
            return None

    mgr.off_client = StubOFF()

    # Avoid network in backup creation and simplify processing (async stubs)
    async def _fake_common():
        return {}
    async def _no_errors(_foods):
        return []
    async def _empty_backup(_s, _v):
        return {}
    monkeypatch.setattr(mgr.unified_db, "get_common_foods_database", _fake_common)
    monkeypatch.setattr(mgr, "_validate_food_data", _no_errors)
    monkeypatch.setattr(mgr, "_load_backup", _empty_backup)

    result = await mgr._update_off_database(force=True)
    assert result.success is True
    await mgr.close()
