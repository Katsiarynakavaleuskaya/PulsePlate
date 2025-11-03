from dataclasses import dataclass
from pathlib import Path

import pytest

from core.food_apis import update_manager


@pytest.mark.asyncio
async def test_maybe_await_handles_coroutine():
    async def coro():
        return 42

    assert await update_manager._maybe_await(coro()) == 42
    assert await update_manager._maybe_await(7) == 7


def test_food_to_dict_variants(monkeypatch):
    @dataclass
    class Foo:
        name: str

    manager = object.__new__(update_manager.DatabaseUpdateManager)
    manager.cache_dir = update_manager._PatchablePathWrapper(Path("."))

    dataclass_instance = Foo("bar")
    assert manager._food_to_dict(dataclass_instance) == {"name": "bar"}

    dict_instance = {"name": "baz"}
    assert manager._food_to_dict(dict_instance) == dict_instance

    class WithToDict:
        def to_dict(self):
            return {"name": "td"}

    assert manager._food_to_dict(WithToDict()) == {"name": "td"}

    class WithModelDump:
        def model_dump(self):
            return {"name": "md"}

    assert manager._food_to_dict(WithModelDump()) == {"name": "md"}

    class Fallback:
        pass

    fallback_result = manager._food_to_dict(Fallback())
    assert isinstance(fallback_result, dict)


@pytest.mark.asyncio
async def test_load_backup_foods_filters_entries(tmp_path):
    manager = object.__new__(update_manager.DatabaseUpdateManager)
    manager.cache_dir = update_manager._PatchablePathWrapper(tmp_path)
    backup = tmp_path / "usda_backup_backup.json"
    backup.write_text(
        """
        {
            "valid": {
                "name": "valid",
                "nutrients_per_100g": {},
                "cost_per_100g": 1.0,
                "tags": [],
                "availability_regions": [],
                "source": "test",
                "source_id": "1"
            },
            "invalid": {
                "name": "missing_fields"
            }
        }
        """,
        encoding="utf-8",
    )

    foods = await manager._load_backup("usda", "backup")
    assert "valid" in foods
    assert "invalid" not in foods
