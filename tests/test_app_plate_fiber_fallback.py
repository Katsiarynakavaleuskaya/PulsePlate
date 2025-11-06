"""Targeted tests for premium plate fallbacks."""

from __future__ import annotations

import pytest

import app


@pytest.mark.asyncio
async def test_api_premium_plate_invalid_fiber_defaults_to_minimum(monkeypatch: pytest.MonkeyPatch):
    """Ensure invalid fiber values fall back to the minimum requirement."""

    def fake_make_plate(**_: object) -> dict[str, object]:
        return {
            "macros": {
                "protein_g": 110,
                "fat_g": 50,
                "carbs_g": 220,
                "fiber_g": "not-a-number",
            },
            "layout": [
                {
                    "kind": "plate_sector",
                    "fraction": 0.5,
                    "label": "Veg",
                    "tooltip": "Vegetables",
                }
            ],
            "meals": [],
            "kcal": 2100,
            "portions": {
                "protein_palm": 2.0,
                "carb_cups": 2.0,
                "veg_cups": 3.0,
                "fat_thumbs": 2.0,
            },
            "meals_per_day": 3,
        }

    def fake_calculate_all_bmr(*_: object, **__: object) -> dict[str, float]:
        return {"mifflin": 1550.0}

    def fake_calculate_all_tdee(_bmr_results: dict[str, float], _activity: str) -> dict[str, float]:
        return {"mifflin": 2000.0}

    async def fake_aggregate_day_micronutrients(
        _meals: list[dict[str, object]],
    ) -> dict[str, float]:
        return {"fiber_g": 18.0}

    monkeypatch.setattr(app, "make_plate", fake_make_plate, raising=False)
    monkeypatch.setattr(app, "calculate_all_bmr", fake_calculate_all_bmr, raising=False)
    monkeypatch.setattr(app, "calculate_all_tdee", fake_calculate_all_tdee, raising=False)
    monkeypatch.setattr(
        app, "_aggregate_day_micronutrients", fake_aggregate_day_micronutrients, raising=False
    )
    monkeypatch.setattr(app, "build_nutrition_targets", None, raising=False)

    request = app.PlateRequest(
        sex="female",
        age=32,
        height_cm=168,
        weight_kg=68,
        activity="moderate",
        goal="loss",
        deficit_pct=None,
        surplus_pct=None,
        bodyfat=None,
        diet_flags=None,
    )

    response = await app.api_premium_plate(request)

    assert response.macros["fiber_g"] == app.FIBER_MIN_G
    assert response.kcal > 0
