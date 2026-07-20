"""Targeted tests for canonical premium Plate fiber fallback."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

import core.bmr as nutrition_bmr
from app.schemas.premium_contracts import PlateRequest
from app.services.pro_nutrition_plate import (
    PlateServiceDependencies,
    generate_plate_response,
)
from core.targets import FIBER_MIN_G


def test_api_premium_plate_invalid_fiber_defaults_to_minimum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid generated fiber uses the same minimum and preserves source kcal."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def fake_make_plate(**_: object) -> dict[str, Any]:
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

    async def fake_aggregate_day_micronutrients(
        _meals: list[dict[str, Any]],
    ) -> dict[str, float]:
        return {"fiber_g": 18.0}

    dependencies = PlateServiceDependencies(
        make_plate=fake_make_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=fake_aggregate_day_micronutrients,
    )
    request = PlateRequest(
        sex="female",
        age=32,
        height_cm=168,
        weight_kg=68,
        activity="moderate",
        goal="loss",
    )

    response = asyncio.run(generate_plate_response(request, dependencies=dependencies))

    assert response.macros["fiber_g"] == int(FIBER_MIN_G)
    assert response.kcal == 2100
