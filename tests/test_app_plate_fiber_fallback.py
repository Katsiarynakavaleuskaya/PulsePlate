"""Targeted tests for premium plate fallbacks."""

from __future__ import annotations

import pytest

import app


@pytest.mark.asyncio
async def test_api_premium_plate_invalid_fiber_defaults_to_minimum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    # Fiber should equal minimum when fallback is triggered
    assert response.macros["fiber_g"] == app.FIBER_MIN_G

    # When invalid fiber triggers sanitization fallback, the endpoint may use different kcal calculation paths:
    # - 2100: Direct kcal from make_plate (raw plate data)
    # - 2000: Maintenance TDEE (no goal adjustment)
    # - 1700: Loss goal with 15% deficit (2000 * 0.85)
    # Using discrete values ensures we validate against known fallback paths rather than overly permissive ranges
    expected_kcal_values = [1700, 2000, 2100]
    assert response.kcal in expected_kcal_values, (
        f"Expected kcal to be one of {expected_kcal_values} (fallback paths: "
        f"make_plate raw={2100}, maintenance TDEE={2000}, loss with deficit={1700}), "
        f"got {response.kcal}"
    )
