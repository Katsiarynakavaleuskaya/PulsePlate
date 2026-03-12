from __future__ import annotations

import sys

import pytest

from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem
from tests.helpers import fast_update_stubs
from tests.helpers.fast_update_stubs import make_scheduler_stub, patch_unified_db_common_foods_fast


@pytest.mark.asyncio
async def test_fast_update_stubs_smoke() -> None:
    """Smoke-test helper stubs in a dedicated test module."""
    scheduler = make_scheduler_stub()
    result_default = await scheduler.force_update()
    result_with_source = await scheduler.force_update("usda")
    assert "usda" in result_default
    assert "usda" in result_with_source
    assert result_default["usda"] == {"ok": True, "status": "stubbed"}
    assert result_with_source["usda"] == {"ok": True, "status": "stubbed"}


@pytest.mark.asyncio
async def test_make_scheduler_stub_allows_falsy_payload() -> None:
    """Explicit falsy payload must not be replaced by default stub."""
    scheduler = make_scheduler_stub(usda_result={})
    result = await scheduler.force_update("usda")
    assert result["usda"] == {}


@pytest.mark.asyncio
async def test_patch_unified_db_common_foods_fast_returns_unified_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fast common-foods patch must preserve UnifiedFoodItem return contract."""
    patch_unified_db_common_foods_fast(monkeypatch)
    db = UnifiedFoodDatabase.__new__(UnifiedFoodDatabase)
    foods = await db.get_common_foods_database()
    assert set(foods.keys()) == {"oats", "rice"}
    assert all(isinstance(item, UnifiedFoodItem) for item in foods.values())


def test_iter_background_modules_skips_missing_legacy_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Helper should tolerate missing legacy alias modules during import."""
    original_import_module = fast_update_stubs.importlib.import_module

    def _guarded_import_module(name: str):
        if name == "legacy_app":
            exc = ModuleNotFoundError("legacy_app unavailable in helper test")
            exc.name = "legacy_app"
            raise exc
        return original_import_module(name)

    monkeypatch.delitem(sys.modules, "legacy_app", raising=False)
    monkeypatch.delitem(sys.modules, "app_module", raising=False)
    monkeypatch.setattr(fast_update_stubs.importlib, "import_module", _guarded_import_module)

    modules = fast_update_stubs._iter_background_modules()

    assert any(module.__name__ == "app" for module in modules)
    assert all(module.__name__ != "legacy_app" for module in modules)
