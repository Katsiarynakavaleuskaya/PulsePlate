"""Focused helpers and fallback tests for canonical Plate ownership."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import pytest

from app.schemas.premium_contracts import PlateRequest, PlateResponse, VisualShape
from app.services import pro_nutrition_plate as plate_service
from app.services.pro_nutrition_plate import PlateServiceDependencies
from core.targets import FIBER_MIN_G, UserProfile


class _TargetMacros:
    protein_g = 120
    fat_g = 60
    carbs_g = 180
    fiber_g: object = 28


class _Targets:
    kcal_daily = 2200
    macros = _TargetMacros()


def _empty_micros(
    _meals: list[dict[str, Any]],
) -> dict[str, float]:
    return {}


@pytest.fixture
def premium_plate_fallback_setup() -> dict[str, Any]:
    """Return immutable dependencies for the documented backend fallback."""

    called: dict[str, bool] = {}

    def fake_build_targets(_profile: UserProfile) -> Any:
        called["value"] = True
        return _Targets()

    request = PlateRequest(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity="moderate",
        goal="maintain",
        diet_flags=set(),
    )
    dependencies = PlateServiceDependencies(
        make_plate=None,
        calculate_all_bmr=None,
        calculate_all_tdee=None,
        build_nutrition_targets=fake_build_targets,
        aggregate_day_micronutrients=_empty_micros,
    )
    return {
        "request": request,
        "dependencies": dependencies,
        "called": called,
    }


def _run_fallback(setup: dict[str, Any]) -> PlateResponse:
    return asyncio.run(
        plate_service.generate_plate_response(
            setup["request"],
            dependencies=setup["dependencies"],
        )
    )


def _fallback_dependencies(
    targets_builder: Callable[[UserProfile], Any] | None,
) -> PlateServiceDependencies:
    return PlateServiceDependencies(
        make_plate=None,
        calculate_all_bmr=None,
        calculate_all_tdee=None,
        build_nutrition_targets=targets_builder,
        aggregate_day_micronutrients=_empty_micros,
    )


def test_convert_db_nutrients_to_alias_format() -> None:
    result = plate_service._convert_db_nutrients_to_alias_format(
        {"Fe_mg": 2.5, "Ca_mg": 10, "custom": 1.5}
    )

    assert result["iron_mg"] == 2.5
    assert result["calcium_mg"] == 10.0
    assert result["custom"] == 1.5


def test_api_premium_plate_fallback_calls_build_targets(
    premium_plate_fallback_setup: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    response = _run_fallback(premium_plate_fallback_setup)

    assert isinstance(response, PlateResponse)
    assert premium_plate_fallback_setup["called"] == {"value": True}


def test_api_premium_plate_fallback_response_structure(
    premium_plate_fallback_setup: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    response = _run_fallback(premium_plate_fallback_setup)

    assert isinstance(response, PlateResponse)
    assert response.kcal == 2200
    assert response.macros == {
        "protein_g": 120,
        "fat_g": 60,
        "carbs_g": 180,
        "fiber_g": 28,
    }


def test_api_premium_plate_fallback_portions_layout_and_meals(
    premium_plate_fallback_setup: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    response = _run_fallback(premium_plate_fallback_setup)

    assert set(response.portions) == {
        "protein_palm",
        "carb_cups",
        "veg_cups",
        "fat_thumbs",
    }
    assert all(value >= 0 for value in response.portions.values())
    assert len(response.layout) == 6
    assert all(isinstance(shape, VisualShape) for shape in response.layout)
    assert all(0 <= shape.fraction <= 1 for shape in response.layout)
    assert [meal["title"] for meal in response.meals] == [
        "Breakfast",
        "Lunch",
        "Dinner",
    ]
    assert all(
        isinstance(meal["kcal"], int) and 0 < meal["kcal"] < response.kcal
        for meal in response.meals
    )
    assert response.day_micros == {}
    assert response.meals_per_day == 3


def test_api_premium_plate_fallback_handles_target_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def failing_targets(_profile: UserProfile) -> Any:
        raise ValueError("boom")

    request = PlateRequest(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity="moderate",
        goal="maintain",
    )
    response = asyncio.run(
        plate_service.generate_plate_response(
            request,
            dependencies=_fallback_dependencies(failing_targets),
        )
    )

    assert response.kcal == 2400
    assert response.macros == {
        "protein_g": 128,
        "fat_g": 72,
        "carbs_g": 310,
        "fiber_g": int(FIBER_MIN_G),
    }


def test_api_premium_plate_fallback_handles_unexpected_target_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def failing_targets(_profile: UserProfile) -> Any:
        raise RuntimeError("private target backend payload")

    request = PlateRequest(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity="moderate",
        goal="maintain",
    )

    response = asyncio.run(
        plate_service.generate_plate_response(
            request,
            dependencies=_fallback_dependencies(failing_targets),
        )
    )

    assert isinstance(response, PlateResponse)
    assert response.kcal == 2400
    assert response.macros == {
        "protein_g": 128,
        "fat_g": 72,
        "carbs_g": 310,
        "fiber_g": int(FIBER_MIN_G),
    }
    assert "private target backend payload" not in response.model_dump_json()


def test_api_premium_plate_fallback_discards_partial_non_finite_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    class NonFiniteMacros:
        protein_g = float("inf")
        fat_g = 60
        carbs_g = 180
        fiber_g = 30

    class NonFiniteTargets:
        kcal_daily = 1800
        macros = NonFiniteMacros()

    def non_finite_targets(_profile: UserProfile) -> Any:
        return NonFiniteTargets()

    request = PlateRequest(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity="moderate",
        goal="maintain",
    )

    response = asyncio.run(
        plate_service.generate_plate_response(
            request,
            dependencies=_fallback_dependencies(non_finite_targets),
        )
    )

    assert isinstance(response, PlateResponse)
    assert response.kcal == 2400
    assert response.macros == {
        "protein_g": 128,
        "fat_g": 72,
        "carbs_g": 310,
        "fiber_g": int(FIBER_MIN_G),
    }
    assert "Infinity" not in response.model_dump_json()


def test_api_premium_plate_fallback_invalid_fiber_converts_to_min(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    class InvalidFiberMacros:
        protein_g = 120
        fat_g = 60
        carbs_g = 180
        fiber_g = "oops"

    class InvalidFiberTargets:
        kcal_daily = 2400
        macros = InvalidFiberMacros()

    def bad_targets(_profile: UserProfile) -> Any:
        return InvalidFiberTargets()

    request = PlateRequest(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity="moderate",
        goal="maintain",
    )
    response = asyncio.run(
        plate_service.generate_plate_response(
            request,
            dependencies=_fallback_dependencies(bad_targets),
        )
    )

    assert response.kcal == 2400
    assert response.macros == {
        "protein_g": 120,
        "fat_g": 60,
        "carbs_g": 180,
        "fiber_g": int(FIBER_MIN_G),
    }
