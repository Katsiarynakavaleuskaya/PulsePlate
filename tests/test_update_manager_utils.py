import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from core.food_apis import update_manager


@pytest.mark.asyncio
async def test_maybe_await_handles_coroutine() -> None:
    async def coro():
        return 42

    assert await update_manager._maybe_await(coro()) == 42
    assert await update_manager._maybe_await(7) == 7


def test_food_to_dict_variants() -> None:
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

    # Assert it's a dict with at least one key
    assert isinstance(fallback_result, dict)
    assert len(fallback_result) > 0, "Fallback dict should have at least one key"

    # Assert expected keys from fallback serialization
    expected_keys = {
        "name",
        "nutrients_per_100g",
        "cost_per_100g",
        "tags",
        "availability_regions",
        "source",
        "source_id",
    }
    assert (
        set(fallback_result.keys()) == expected_keys
    ), f"Expected keys {expected_keys}, got {fallback_result.keys()}"

    # Assert expected default values
    assert fallback_result["name"] == "unknown"
    assert fallback_result["nutrients_per_100g"] == {}
    assert fallback_result["cost_per_100g"] == 0.0
    assert fallback_result["tags"] == []
    assert fallback_result["availability_regions"] == []
    assert fallback_result["source"] == "unknown"
    assert fallback_result["source_id"] == "unknown"

    # Assert all values are JSON-serializable
    try:
        json_str = json.dumps(fallback_result)
        assert isinstance(json_str, str), "Should be able to serialize to JSON string"
    except (TypeError, ValueError) as e:
        pytest.fail(f"Fallback dict should be JSON-serializable, but got error: {e}")

    # Test fallback with attributes present
    class FallbackWithAttrs:
        def __init__(self):
            self.name = "test_food"
            self.nutrients_per_100g = {"protein": 10}
            self.cost_per_100g = 2.5
            self.tags = ["organic"]
            self.availability_regions = ["US"]
            self.source = "test_source"
            self.source_id = "test_123"

    fallback_with_attrs = manager._food_to_dict(FallbackWithAttrs())
    assert fallback_with_attrs["name"] == "test_food"
    assert fallback_with_attrs["nutrients_per_100g"] == {"protein": 10}
    assert fallback_with_attrs["cost_per_100g"] == 2.5
    assert fallback_with_attrs["tags"] == ["organic"]
    assert fallback_with_attrs["availability_regions"] == ["US"]
    assert fallback_with_attrs["source"] == "test_source"
    assert fallback_with_attrs["source_id"] == "test_123"

    # Also ensure this is JSON-serializable
    assert json.dumps(fallback_with_attrs) is not None


@pytest.mark.asyncio
async def test_load_backup_foods_filters_entries(tmp_path: Path) -> None:
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
