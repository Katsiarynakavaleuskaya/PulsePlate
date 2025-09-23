import asyncio
import os
from pathlib import Path
from typing import Any

import pytest


@pytest.mark.asyncio
async def test_update_manager_check_for_updates_off_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from core.food_apis import update_manager as UM

    cache = tmp_path / "cache"
    cache.mkdir(parents=True, exist_ok=True)

    # OFF unavailable
    monkeypatch.setattr(UM, "OFF_AVAILABLE", False)
    mgr = UM.DatabaseUpdateManager(cache_dir=str(cache), update_interval_hours=24)
    mgr.off_client = None

    # Avoid real checks
    async def no_usda():
        return False

    monkeypatch.setattr(mgr, "_check_usda_updates", no_usda)

    updates = await mgr.check_for_updates()
    # OFF not present when unavailable; USDA False
    assert updates.get("usda") is False
    assert "openfoodfacts" not in updates or updates.get("openfoodfacts") is False


@pytest.mark.asyncio
async def test_update_manager_unknown_source(tmp_path: Path):
    from core.food_apis.update_manager import DatabaseUpdateManager

    cache = tmp_path / "cache"
    mgr = DatabaseUpdateManager(cache_dir=str(cache), update_interval_hours=24)
    res = await mgr.update_database("unknown_source")
    assert res.success is False and "Unknown source" in res.errors[0]


@pytest.mark.asyncio
async def test_cleanup_old_backups_deletes_excess(tmp_path: Path):
    from core.food_apis.update_manager import DatabaseUpdateManager

    cache = tmp_path / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    mgr = DatabaseUpdateManager(cache_dir=str(cache), update_interval_hours=24)
    mgr.max_rollback_versions = 1

    # Create three backup files with increasing mtimes
    files = [cache / f"usda_backup_{i}.json" for i in (1, 2, 3)]
    for idx, f in enumerate(files, start=1):
        f.write_text("{}", encoding="utf-8")
        os.utime(f, (1000 + idx, 1000 + idx))

    await mgr._cleanup_old_backups("usda")
    existing = {p.name for p in cache.glob("usda_backup_*.json")}
    assert existing == {"usda_backup_3.json"}


def test_load_versions_error_path(tmp_path: Path):
    from core.food_apis.update_manager import DatabaseUpdateManager

    cache = tmp_path / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "database_versions.json").write_text("not json", encoding="utf-8")

    mgr = DatabaseUpdateManager(cache_dir=str(cache), update_interval_hours=24)
    assert mgr.versions == {}


def test_save_versions_error_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    import builtins
    from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion

    cache = tmp_path / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    mgr = DatabaseUpdateManager(cache_dir=str(cache), update_interval_hours=24)
    mgr.versions = {
        "usda": DatabaseVersion(
            source="usda",
            version="v1",
            last_updated="2024-01-01T00:00:00Z",
            record_count=0,
            checksum="x",
            metadata={},
        )
    }

    real_open = builtins.open

    def fake_open(path: Any, *args: Any, **kwargs: Any):  # noqa: D401
        if str(path) == str(mgr.versions_file):
            raise RuntimeError("save fail")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    # Should not raise
    mgr._save_versions()
