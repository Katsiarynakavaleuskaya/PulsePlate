from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

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
