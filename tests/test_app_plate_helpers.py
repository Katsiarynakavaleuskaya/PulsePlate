from types import ModuleType, SimpleNamespace
from typing import Any

import sys

import pytest

import app


def test_convert_db_nutrients_to_alias_format():
    data = {"Fe_mg": 2.5, "Ca_mg": 10, "custom": 1.5, "unused": None}
    result = app._convert_db_nutrients_to_alias_format(data)
    assert result["iron_mg"] == 2.5
    assert result["calcium_mg"] == 10.0
    # Custom keys should be preserved
    assert result["custom"] == 1.5
    # None values should default to 0.0
    assert result["unused"] == 0.0


@pytest.mark.asyncio
async def test_api_premium_plate_fallback_aligns_targets(monkeypatch):
    """Ensure fallback path aligns macros when backends are unavailable."""

    original_resolve = app.resolve_attr

    def fake_resolve(name: str, default: Any = None, candidates: Any = None) -> Any:
        if name in {"make_plate", "calculate_all_bmr", "calculate_all_tdee"}:
            return None
        return original_resolve(name, default, candidates)

    monkeypatch.setattr(app, "resolve_attr", fake_resolve)

    class DummyTargets:
        def __init__(self) -> None:
            class Macros:
                protein_g = 120
                fat_g = 60
                carbs_g = 180
                fiber_g = 28

            self.kcal_daily = 2200
            self.macros = Macros()

    fake_module = ModuleType("core.targets")

    class DummyProfile:
        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    fake_module.UserProfile = DummyProfile
    monkeypatch.setitem(sys.modules, "core.targets", fake_module)

    called: dict[str, bool] = {}

    def fake_build_targets(profile: Any) -> DummyTargets:
        called["value"] = True
        return DummyTargets()

    monkeypatch.setattr(app, "build_nutrition_targets", fake_build_targets)

    request = app.PlateRequest(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity="moderate",
        goal="maintain",
        deficit_pct=None,
        surplus_pct=None,
        bodyfat=None,
        diet_flags=set(),
        life_stage="adult",
        lang="en",
    )

    response = await app.api_premium_plate(request)
    assert isinstance(response, app.PlateResponse)
    assert called.get("value") is True
