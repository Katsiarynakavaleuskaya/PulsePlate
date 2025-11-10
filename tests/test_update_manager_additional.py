from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Dict

import pytest

from core.food_apis.unified_db import UnifiedFoodItem
from core.food_apis.update_manager import DatabaseUpdateManager


@pytest.fixture
def manager(tmp_path, monkeypatch: pytest.MonkeyPatch) -> DatabaseUpdateManager:
    class DummyOFFClient:
        async def close(self) -> None:
            return None

    monkeypatch.setattr("core.food_apis.update_manager.OFFClient", lambda: DummyOFFClient())
    monkeypatch.setattr("core.food_apis.update_manager.USDAClient", lambda: SimpleNamespace())
    monkeypatch.setattr(
        "core.food_apis.update_manager.UnifiedFoodDatabase", lambda path: SimpleNamespace()
    )
    mgr = DatabaseUpdateManager(cache_dir=tmp_path)
    yield mgr
    if mgr.off_client is not None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(mgr.off_client.close())
        finally:
            loop.close()


@pytest.mark.asyncio
async def test_actual_record_count_from_csv(manager: DatabaseUpdateManager, tmp_path: Path) -> None:
    csv_path = tmp_path / "products.csv"
    csv_path.write_text("name\nfoo\nbar\n", encoding="utf-8")
    manager.cache_dir = manager.cache_dir.__class__(tmp_path)

    count = await manager._get_actual_record_count("openfoodfacts")
    assert count == 2


@pytest.mark.asyncio
async def test_actual_record_count_from_jsonl(
    manager: DatabaseUpdateManager, tmp_path: Path
) -> None:
    jsonl_path = tmp_path / "products.jsonl"
    jsonl_path.write_text('{"name": "foo"}\n{"name": "bar"}\n', encoding="utf-8")
    manager.cache_dir = manager.cache_dir.__class__(tmp_path)

    count = await manager._get_actual_record_count("openfoodfacts")
    assert count == 2


@pytest.mark.asyncio
async def test_actual_record_count_handles_exception(
    manager: DatabaseUpdateManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        manager,
        "_find_off_export_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    result = await manager._get_actual_record_count("openfoodfacts")
    assert result == 0


@pytest.mark.asyncio
async def test_cache_data_for_checksum_json_errors(
    manager: DatabaseUpdateManager, tmp_path: Path
) -> None:
    jsonl_path = tmp_path / "products.jsonl"
    jsonl_path.write_text('{"name": "valid"}\n{bad json}\n', encoding="utf-8")
    manager.cache_dir = manager.cache_dir.__class__(tmp_path)

    data = await manager._get_cache_data_for_checksum("openfoodfacts")
    assert "valid" in data


@pytest.mark.asyncio
async def test_cache_data_for_checksum_csv(manager: DatabaseUpdateManager, tmp_path: Path) -> None:
    csv_path = tmp_path / "products.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name"])
        writer.writeheader()
        writer.writerow({"name": "apple"})
    manager.cache_dir = manager.cache_dir.__class__(tmp_path)

    data = await manager._get_cache_data_for_checksum("openfoodfacts")
    assert "apple" in data


@pytest.mark.asyncio
async def test_validated_record_count_warns_when_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = DatabaseUpdateManager(cache_dir=":memory:")

    async def fake_count(source: str) -> int:
        return 0

    async def fake_cache(source: str) -> Dict[str, Dict]:
        return {}

    monkeypatch.setattr(manager, "_get_actual_record_count", fake_count)
    monkeypatch.setattr(manager, "_get_cache_data_for_checksum", fake_cache)
    foods = {
        "foo": UnifiedFoodItem(
            name="foo",
            nutrients_per_100g={},
            cost_per_100g=1.0,
            tags=[],
            availability_regions=[],
            source="test",
            source_id="foo",
            category="default",
        )
    }
    count, checksum = await manager._get_validated_record_count_and_checksum("openfoodfacts", foods)
    assert count == len(foods)
    assert isinstance(checksum, str)
    await manager.off_client.close()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_load_backup_handles_invalid_entries(
    manager: DatabaseUpdateManager, tmp_path: Path
) -> None:
    manager.cache_dir = manager.cache_dir.__class__(tmp_path)
    backup_file = tmp_path / "openfoodfacts_backup_v1.json"
    backup_file.write_text(json.dumps({"invalid": {"bad": "data"}}), encoding="utf-8")
    result = await manager._load_backup("openfoodfacts", "v1")
    assert result == {}


def test_food_to_dict_dataclass_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = DatabaseUpdateManager(cache_dir=":memory:")
    food = SimpleNamespace()

    def fake_is_dataclass(obj):
        raise TypeError("fail")

    monkeypatch.setattr("core.food_apis.update_manager.is_dataclass", fake_is_dataclass)
    result = manager._food_to_dict(food)
    assert result["name"] == "unknown"


def test_food_to_dict_conversion_method_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = DatabaseUpdateManager(cache_dir=":memory:")

    class WithToDict:
        def to_dict(self):
            raise ValueError("boom")

    result = manager._food_to_dict(WithToDict())
    assert result["name"] == "unknown"
