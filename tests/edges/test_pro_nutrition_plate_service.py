"""Deterministic contract tests for canonical PRO Plate ownership."""

from __future__ import annotations

import ast
import asyncio
from decimal import Decimal
from numbers import Number
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import core.bmr as nutrition_bmr
import core.plate as nutrition_plate
import core.recommendations as nutrition_recommendations
import legacy_app
from app.http_error_details import (
    ENHANCED_PLATE_GENERATION_FAILED_DETAIL,
    INVALID_PREMIUM_PLATE_INPUT_DETAIL,
)
from app.schemas.premium_contracts import (
    PlateRequest,
    PlateResponse,
    WHOTargetsRequest,
)
from app.services import pro_nutrition_plate
from app.services.pro_nutrition_plate import (
    PLATE_FEATURE_UNAVAILABLE_DETAIL,
    PlateServiceDependencies,
    generate_plate_response,
)
from app.services.pro_nutrition_targets import WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL
from core.data_sanitizer import MissingOptionalDependencyError

_REPO_ROOT = Path(__file__).resolve().parents[2]


class _ExplodingNumber(Number):
    """Numeric dependency value that cannot be converted to float."""

    def __float__(self) -> float:
        raise OverflowError("private numeric overflow")


class _ExplodingMeasurement:
    """Request measurement with a controlled conversion failure."""

    def __init__(self, error: type[Exception]) -> None:
        self._error = error

    def __float__(self) -> float:
        raise self._error("private measurement conversion failure")


def _request() -> PlateRequest:
    return PlateRequest(
        sex="female",
        age=34,
        height_cm=168,
        weight_kg=60,
        activity="light",
        goal="maintain",
        life_stage="adult",
        lang="en",
    )


async def _empty_micros(
    _meals: list[dict[str, Any]],
) -> dict[str, float]:
    return {}


def _valid_generated_plate(**_kwargs: object) -> dict[str, Any]:
    return {
        "kcal": 2000,
        "macros": {
            "protein_g": 110,
            "fat_g": 60,
            "carbs_g": 240,
            "fiber_g": 25,
        },
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 2.0,
            "carb_cups": 2.0,
            "veg_cups": 3.0,
        },
        "layout": [
            {
                "kind": "plate_sector",
                "fraction": 1.0,
                "label": "Plate",
                "tooltip": "Plate",
            }
        ],
        "meals": [],
        "meals_per_day": 3,
    }


def _valid_generated_plate_with_meal(**_kwargs: object) -> dict[str, Any]:
    payload = _valid_generated_plate()
    payload["meals"] = [
        {
            "title": "Meal",
            "kcal": 500,
            "protein_g": 30,
            "fat_g": 15,
            "carbs_g": 60,
            "fiber_g": 8,
        }
    ]
    return payload


def _real_dependencies() -> PlateServiceDependencies:
    return PlateServiceDependencies(
        make_plate=nutrition_plate.make_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=nutrition_recommendations.build_nutrition_targets,
        aggregate_day_micronutrients=_empty_micros,
    )


def _dependencies_with_generator(
    generator: pro_nutrition_plate.PlateGenerator | None,
) -> PlateServiceDependencies:
    return PlateServiceDependencies(
        make_plate=generator,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=nutrition_recommendations.build_nutrition_targets,
        aggregate_day_micronutrients=_empty_micros,
    )


def test_generate_plate_response_real_core_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The production-shaped core path returns the stable bounded contract."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    response = asyncio.run(generate_plate_response(_request(), dependencies=_real_dependencies()))

    assert isinstance(response, PlateResponse)
    assert 1200 <= response.kcal <= 5000
    assert response.meals_per_day == 3
    assert len(response.layout) == 6
    assert set(response.macros) >= {
        "protein_g",
        "fat_g",
        "carbs_g",
        "fiber_g",
    }
    assert response.macros["fiber_g"] >= 25


def test_plate_alignment_passes_and_service_honors_resolved_targets_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = SimpleNamespace(
        kcal_daily=2250,
        macros=SimpleNamespace(
            protein_g=120,
            fat_g=70,
            carbs_g=280,
            fiber_g=30,
        ),
        water_ml_daily=2200,
        micros=SimpleNamespace(
            get_priority_nutrients=lambda: {
                "iron_mg": 18.0,
                "calcium_mg": 1000.0,
            }
        ),
        activity=SimpleNamespace(
            moderate_aerobic_min=150,
            strength_sessions=2,
            steps_daily=8000,
        ),
        calculation_date="2026-07-20",
    )
    resolved_calls: list[object] = []
    resolved_builders: list[object] = []

    def _resolved_builder(profile: object) -> object:
        resolved_calls.append(profile)
        return target

    def _unexpected_canonical_builder(_profile: object) -> object:
        raise AssertionError("Plate override must not use the canonical default builder")

    def _generate_with_observation(
        request: WHOTargetsRequest,
        *,
        allow_backend_fallback: bool = True,
        targets_builder: pro_nutrition_plate.TargetsBuilder | None = None,
    ) -> object:
        resolved_builders.append(targets_builder)
        return pro_nutrition_plate.generate_who_targets_response(
            request,
            allow_backend_fallback=allow_backend_fallback,
            targets_builder=targets_builder,
        )

    monkeypatch.setattr(
        nutrition_recommendations,
        "build_nutrition_targets",
        _unexpected_canonical_builder,
    )
    monkeypatch.setattr(
        nutrition_recommendations,
        "validate_targets_safety",
        lambda _targets: [],
    )
    request = PlateRequest(
        sex="female",
        age=34,
        height_cm=168,
        weight_kg=62,
        activity="light",
        goal="maintain",
        life_stage="adult",
        lang="en",
    )

    macros, kcal, aligned = pro_nutrition_plate.align_macros_with_targets(
        request,
        {
            "macros": {
                "protein_g": 80,
                "fat_g": 50,
                "carbs_g": 200,
                "fiber_g": 20,
            }
        },
        targets_builder=_resolved_builder,
        targets_response_factory=_generate_with_observation,
    )

    assert resolved_builders == [_resolved_builder]
    assert len(resolved_calls) == 1
    assert macros == {
        "protein_g": 120,
        "fat_g": 70,
        "carbs_g": 280,
        "fiber_g": 30,
    }
    assert kcal == 2250
    assert aligned is True


@pytest.mark.parametrize(
    ("invalid_macro", "invalid_value"),
    [
        pytest.param("protein_g", -1, id="protein-below-minimum"),
        pytest.param("protein_g", 501, id="protein-above-maximum"),
        pytest.param("fat_g", -1, id="fat-below-minimum"),
        pytest.param("fat_g", 301, id="fat-above-maximum"),
        pytest.param("carbs_g", -1, id="carbs-below-minimum"),
        pytest.param("carbs_g", 1001, id="carbs-above-maximum"),
        pytest.param("fiber_g", -1, id="fiber-below-minimum"),
        pytest.param("fiber_g", 101, id="fiber-above-maximum"),
        pytest.param("protein_g", float("inf"), id="protein-non-finite"),
        pytest.param("protein_g", True, id="protein-boolean"),
        pytest.param("protein_g", "120", id="protein-numeric-string"),
        pytest.param("protein_g", 120.5, id="protein-fractional-float"),
        pytest.param("protein_g", 120.0, id="protein-integral-float"),
        pytest.param("protein_g", Decimal("120"), id="protein-decimal"),
    ],
)
def test_plate_alignment_preserves_generated_macro_when_target_is_invalid(
    invalid_macro: str,
    invalid_value: object,
) -> None:
    """Invalid target macros preserve safe values while valid fields align."""

    generated_macros = {
        "protein_g": 90,
        "fat_g": 55,
        "carbs_g": 220,
        "fiber_g": 20,
    }
    target_macros: dict[str, object] = {
        "protein_g": 120,
        "fat_g": 70,
        "carbs_g": 250,
        "fiber_g": 30,
    }
    target_macros[invalid_macro] = invalid_value

    def _response_factory(
        _request: WHOTargetsRequest,
        *,
        allow_backend_fallback: bool = True,
        targets_builder: pro_nutrition_plate.TargetsBuilder | None = None,
    ) -> object:
        assert allow_backend_fallback is True
        assert callable(targets_builder)
        return SimpleNamespace(
            kcal_daily=2100,
            macros=target_macros,
        )

    macros, kcal, aligned = pro_nutrition_plate.align_macros_with_targets(
        _request(),
        {"macros": generated_macros},
        targets_builder=lambda _profile: object(),
        targets_response_factory=_response_factory,
    )

    expected_macros = {
        "protein_g": 120,
        "fat_g": 70,
        "carbs_g": 250,
        "fiber_g": 30,
    }
    expected_macros[invalid_macro] = generated_macros[invalid_macro]
    assert macros == expected_macros
    assert kcal == 2100
    assert aligned is True


@pytest.mark.parametrize(
    ("warnings", "expected_macros", "expected_kcal", "expected_aligned"),
    [
        pytest.param(
            [{"code": "safety", "message": "Unsafe target combination"}],
            {
                "protein_g": 90,
                "fat_g": 55,
                "carbs_g": 220,
                "fiber_g": 20,
            },
            None,
            False,
            id="safety-warning-preserves-generated",
        ),
        pytest.param(
            [{"code": "life_stage", "message": "Use age-appropriate references"}],
            {
                "protein_g": 120,
                "fat_g": 70,
                "carbs_g": 250,
                "fiber_g": 30,
            },
            2100,
            True,
            id="non-safety-warning-aligns",
        ),
    ],
)
def test_plate_alignment_rejects_only_safety_warned_targets(
    warnings: list[dict[str, str]],
    expected_macros: dict[str, int],
    expected_kcal: int | None,
    expected_aligned: bool,
) -> None:
    """Safety warnings reject target copying without blocking safe warnings."""

    generated_macros = {
        "protein_g": 90,
        "fat_g": 55,
        "carbs_g": 220,
        "fiber_g": 20,
    }

    def _response_factory(*_args: object, **_kwargs: object) -> object:
        return SimpleNamespace(
            kcal_daily=2100,
            macros={
                "protein_g": 120,
                "fat_g": 70,
                "carbs_g": 250,
                "fiber_g": 30,
            },
            warnings=warnings,
        )

    macros, kcal, aligned = pro_nutrition_plate.align_macros_with_targets(
        _request(),
        {"macros": generated_macros},
        targets_builder=lambda _profile: object(),
        targets_response_factory=_response_factory,
    )

    assert macros == expected_macros
    assert kcal == expected_kcal
    assert aligned is expected_aligned


def test_fallback_rejects_safety_warned_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Safety warnings keep the bounded heuristic instead of copying targets."""

    target = SimpleNamespace(
        kcal_daily=2100,
        macros=SimpleNamespace(
            protein_g=120,
            fat_g=70,
            carbs_g=250,
            fiber_g=30,
        ),
    )
    monkeypatch.setattr(
        pro_nutrition_plate,
        "validate_targets_safety_warnings",
        lambda _targets: ["Unsafe target combination"],
    )

    response = pro_nutrition_plate.build_fallback_plate(
        _request(),
        targets_builder=lambda _profile: target,
    )

    assert response.kcal == 1980
    assert response.macros == {
        "protein_g": 96,
        "fat_g": 54,
        "carbs_g": 278,
        "fiber_g": 25,
    }


def test_fallback_propagates_target_safety_validator_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validator execution failures remain fail-closed in fallback mode."""

    def _reject_targets(_targets: object) -> list[str]:
        raise HTTPException(
            status_code=500,
            detail=WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL,
        )

    monkeypatch.setattr(
        pro_nutrition_plate,
        "validate_targets_safety_warnings",
        _reject_targets,
    )

    with pytest.raises(HTTPException) as exc_info:
        pro_nutrition_plate.build_fallback_plate(
            _request(),
            targets_builder=lambda _profile: object(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        pytest.param("kcal_daily", float("inf"), id="kcal-infinity"),
        pytest.param("protein_g", None, id="protein-none"),
        pytest.param("protein_g", -1, id="protein-below-minimum"),
        pytest.param("protein_g", 501, id="protein-above-maximum"),
        pytest.param("protein_g", True, id="protein-boolean"),
        pytest.param("fat_g", "invalid", id="fat-string"),
        pytest.param("fat_g", -1, id="fat-below-minimum"),
        pytest.param("fat_g", 301, id="fat-above-maximum"),
        pytest.param("fat_g", True, id="fat-boolean"),
        pytest.param("carbs_g", float("nan"), id="carbs-nan"),
        pytest.param("carbs_g", -1, id="carbs-below-minimum"),
        pytest.param("carbs_g", 1001, id="carbs-above-maximum"),
        pytest.param("carbs_g", True, id="carbs-boolean"),
    ],
)
def test_fallback_uses_bounded_heuristic_for_invalid_target_values(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid_value: object,
) -> None:
    """Malformed canonical target values cannot break the last-resort response."""

    values: dict[str, object] = {
        "kcal_daily": 2100,
        "protein_g": 120,
        "fat_g": 70,
        "carbs_g": 250,
    }
    values[field] = invalid_value
    target = SimpleNamespace(
        kcal_daily=values["kcal_daily"],
        macros=SimpleNamespace(
            protein_g=values["protein_g"],
            fat_g=values["fat_g"],
            carbs_g=values["carbs_g"],
            fiber_g=30,
        ),
        validate_consistency=lambda: True,
    )
    monkeypatch.setattr(
        pro_nutrition_plate,
        "validate_targets_safety_warnings",
        lambda _targets: None,
    )

    response = pro_nutrition_plate.build_fallback_plate(
        _request(),
        targets_builder=lambda _profile: target,
    )

    assert response.kcal == 1980
    assert response.macros == {
        "protein_g": 96,
        "fat_g": 54,
        "carbs_g": 278,
        "fiber_g": 25,
    }


@pytest.mark.parametrize(
    "invalid_fiber",
    [
        pytest.param(-1, id="below-minimum"),
        pytest.param(101, id="above-maximum"),
        pytest.param(True, id="boolean"),
        pytest.param("30", id="numeric-string"),
    ],
)
def test_fallback_replaces_invalid_target_fiber_with_canonical_minimum(
    monkeypatch: pytest.MonkeyPatch,
    invalid_fiber: object,
) -> None:
    """Invalid target fiber cannot escape into the fallback response."""

    target = SimpleNamespace(
        kcal_daily=2100,
        macros=SimpleNamespace(
            protein_g=120,
            fat_g=70,
            carbs_g=250,
            fiber_g=invalid_fiber,
        ),
        validate_consistency=lambda: True,
    )
    monkeypatch.setattr(
        pro_nutrition_plate,
        "validate_targets_safety_warnings",
        lambda _targets: None,
    )

    response = pro_nutrition_plate.build_fallback_plate(
        _request(),
        targets_builder=lambda _profile: target,
    )

    assert response.kcal == 2100
    assert response.macros == {
        "protein_g": 120,
        "fat_g": 70,
        "carbs_g": 250,
        "fiber_g": 25,
    }


def test_plate_alignment_propagates_canonical_target_safety_failure() -> None:
    """The canonical Plate owner preserves the target-safety failure."""

    def _builder(_profile: object) -> object:
        return object()

    def _reject_unsafe_targets(*_args: object, **_kwargs: object) -> object:
        raise HTTPException(
            status_code=500,
            detail=WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL,
        )

    plate_data = {
        "macros": {
            "protein_g": 80,
            "fat_g": 50,
            "carbs_g": 200,
            "fiber_g": 25,
        }
    }

    with pytest.raises(HTTPException) as exc_info:
        pro_nutrition_plate.align_macros_with_targets(
            _request(),
            plate_data,
            targets_builder=_builder,
            targets_response_factory=_reject_unsafe_targets,
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL


def test_generate_plate_response_documented_backend_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unavailable calculation backends retain the exact deterministic formula."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "1")
    dependencies = PlateServiceDependencies(
        make_plate=None,
        calculate_all_bmr=None,
        calculate_all_tdee=None,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_empty_micros,
    )

    response = asyncio.run(generate_plate_response(_request(), dependencies=dependencies))

    assert response.kcal == 1980
    assert response.macros == {
        "protein_g": 96,
        "fat_g": 54,
        "carbs_g": 278,
        "fiber_g": 25,
    }
    assert response.portions == {
        "protein_palm": 3.8,
        "carb_cups": 7.0,
        "veg_cups": 3.0,
        "fat_thumbs": 3.9,
    }
    assert [meal["title"] for meal in response.meals] == [
        "Breakfast",
        "Lunch",
        "Dinner",
    ]


def test_generate_plate_response_feature_flag_is_exact_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FEATURE_PREMIUM_NUTRITION", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(generate_plate_response(_request(), dependencies=_real_dependencies()))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == PLATE_FEATURE_UNAVAILABLE_DETAIL


def test_generate_plate_response_value_error_is_safe_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "on")

    def _reject_plate(**_kwargs: object) -> dict[str, Any]:
        raise ValueError("private profile fragment /srv/pulseplate/plate.py")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generate_plate_response(
                _request(),
                dependencies=_dependencies_with_generator(_reject_plate),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == INVALID_PREMIUM_PLATE_INPUT_DETAIL
    assert "/srv/pulseplate/plate.py" not in str(exc_info.value.detail)


def test_generate_plate_response_unexpected_error_is_safe_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "yes")

    def _crash_plate(**_kwargs: object) -> dict[str, Any]:
        raise RuntimeError("provider token and /private/trace")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generate_plate_response(
                _request(),
                dependencies=_dependencies_with_generator(_crash_plate),
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == ENHANCED_PLATE_GENERATION_FAILED_DETAIL
    assert "provider token" not in str(exc_info.value.detail)


@pytest.mark.parametrize(
    ("dependency", "calculation_output"),
    [
        pytest.param("bmr", {"mifflin": float("nan")}, id="bmr-non-finite"),
        pytest.param("bmr", {"mifflin": 0.0}, id="bmr-zero"),
        pytest.param("bmr", {"mifflin": -1.0}, id="bmr-negative"),
        pytest.param("bmr", [], id="bmr-malformed-shape"),
        pytest.param("tdee", {"mifflin": float("inf")}, id="tdee-non-finite"),
        pytest.param("tdee", {"mifflin": 0.0}, id="tdee-zero"),
        pytest.param("tdee", {"mifflin": -1.0}, id="tdee-negative"),
        pytest.param("tdee", {"mifflin": "2200"}, id="tdee-malformed-value"),
        pytest.param("tdee", {"harris": 2200.0}, id="tdee-missing-selected-formula"),
    ],
)
def test_generate_plate_response_rejects_invalid_calculation_dependency_output(
    monkeypatch: pytest.MonkeyPatch,
    dependency: str,
    calculation_output: object,
) -> None:
    """Malformed BMR/TDEE output fails closed before Plate generation."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")
    make_plate_calls: list[dict[str, object]] = []

    def _calculate_bmr(*_args: object, **_kwargs: object) -> Any:
        if dependency == "bmr":
            return calculation_output
        return {"mifflin": 1600.0}

    def _calculate_tdee(*_args: object, **_kwargs: object) -> Any:
        if dependency == "tdee":
            return calculation_output
        return {"mifflin": 2200.0}

    def _make_plate(**kwargs: object) -> dict[str, Any]:
        make_plate_calls.append(kwargs)
        return _valid_generated_plate()

    dependencies = PlateServiceDependencies(
        make_plate=_make_plate,
        calculate_all_bmr=_calculate_bmr,
        calculate_all_tdee=_calculate_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_empty_micros,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(generate_plate_response(_request(), dependencies=dependencies))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == ENHANCED_PLATE_GENERATION_FAILED_DETAIL
    assert make_plate_calls == []
    assert "mifflin" not in str(exc_info.value.detail).casefold()


def test_generate_plate_response_rejects_non_positive_canonical_bmr_as_client_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Schema-valid inputs outside the canonical BMR domain return a safe 400."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")
    make_plate_calls: list[dict[str, object]] = []

    def _make_plate(**kwargs: object) -> dict[str, Any]:
        make_plate_calls.append(kwargs)
        return _valid_generated_plate()

    request_payload = _request().model_dump()
    request_payload.update({"age": 100, "height_cm": 1.0, "weight_kg": 1.0})
    request = PlateRequest.model_validate(request_payload)
    dependencies = PlateServiceDependencies(
        make_plate=_make_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_empty_micros,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(generate_plate_response(request, dependencies=dependencies))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == INVALID_PREMIUM_PLATE_INPUT_DETAIL
    assert make_plate_calls == []


@pytest.mark.parametrize(
    "non_finite_value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        "NaN",
        "Infinity",
        "-Infinity",
        "1e309",
        -0.01,
        100000.01,
    ],
    ids=[
        "float-nan",
        "float-positive-infinity",
        "float-negative-infinity",
        "decimal-nan",
        "decimal-positive-infinity",
        "decimal-negative-infinity",
        "string-nan",
        "string-positive-infinity",
        "string-negative-infinity",
        "string-exponent-overflow",
        "negative-finite",
        "above-canonical-maximum",
    ],
)
@pytest.mark.parametrize(
    "async_output",
    [False, True],
    ids=["sync-aggregator", "async-aggregator"],
)
def test_generate_plate_response_rejects_non_finite_micronutrient_dependency_output(
    monkeypatch: pytest.MonkeyPatch,
    non_finite_value: Any,
    async_output: bool,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _sync_aggregator(
        _meals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {"private_dependency_nutrient": non_finite_value}

    async def _async_aggregator(
        _meals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {"private_dependency_nutrient": non_finite_value}

    dependencies = PlateServiceDependencies(
        make_plate=_valid_generated_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=(_async_aggregator if async_output else _sync_aggregator),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generate_plate_response(
                _request(),
                dependencies=dependencies,
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == ENHANCED_PLATE_GENERATION_FAILED_DETAIL
    detail = str(exc_info.value.detail).casefold()
    assert "private_dependency_nutrient" not in detail
    if isinstance(non_finite_value, str):
        assert non_finite_value.casefold() not in detail


def test_generate_plate_response_returns_honest_empty_micronutrients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing recipe evidence stays empty instead of receiving fabricated values."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")
    monkeypatch.setattr(
        pro_nutrition_plate.recipe_store,
        "search_recipes",
        lambda *_args, **_kwargs: [],
    )
    dependencies = PlateServiceDependencies(
        make_plate=_valid_generated_plate_with_meal,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=pro_nutrition_plate._aggregate_day_micronutrients,
    )

    response = asyncio.run(generate_plate_response(_request(), dependencies=dependencies))

    assert response.day_micros == {}
    assert response.meals[0]["micros"] == {}


def test_generate_plate_response_fails_closed_on_malformed_recipe_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed recipe evidence becomes a generic non-leaking server failure."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")
    monkeypatch.setattr(
        pro_nutrition_plate.recipe_store,
        "search_recipes",
        lambda *_args, **_kwargs: [{"recipe_id": "recipe-1"}],
    )
    monkeypatch.setattr(
        pro_nutrition_plate.recipe_store,
        "get_recipe",
        lambda *_args, **_kwargs: {"ingredients_json": "private malformed provider payload"},
    )
    dependencies = PlateServiceDependencies(
        make_plate=_valid_generated_plate_with_meal,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=pro_nutrition_plate._aggregate_day_micronutrients,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(generate_plate_response(_request(), dependencies=dependencies))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == ENHANCED_PLATE_GENERATION_FAILED_DETAIL
    assert "private malformed provider payload" not in str(exc_info.value.detail)


@pytest.mark.parametrize(
    "non_finite_value",
    [float("nan"), Decimal("NaN"), Decimal("Infinity")],
    ids=["float-nan", "decimal-nan", "decimal-infinity"],
)
def test_generate_plate_response_rejects_non_finite_nested_meal_output(
    monkeypatch: pytest.MonkeyPatch,
    non_finite_value: Any,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _nested_non_finite_plate(**_kwargs: object) -> dict[str, Any]:
        payload = _valid_generated_plate()
        payload["meals"] = [
            {
                "title": "Meal",
                "dependency_metadata": {
                    "private_nested_nutrient": non_finite_value,
                },
            }
        ]
        return payload

    dependencies = PlateServiceDependencies(
        make_plate=_nested_non_finite_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_empty_micros,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generate_plate_response(
                _request(),
                dependencies=dependencies,
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == ENHANCED_PLATE_GENERATION_FAILED_DETAIL
    assert "private_nested_nutrient" not in str(exc_info.value.detail)


@pytest.mark.parametrize(
    ("response_field", "non_finite_value"),
    [
        pytest.param("portions", float("nan"), id="portions-nan"),
        pytest.param("portions", float("inf"), id="portions-infinity"),
        pytest.param("layout", float("nan"), id="layout-nan"),
        pytest.param("layout", float("inf"), id="layout-infinity"),
    ],
)
def test_generate_plate_response_rejects_non_finite_response_bound_output(
    monkeypatch: pytest.MonkeyPatch,
    response_field: str,
    non_finite_value: float,
) -> None:
    """Response-bound Plate dependency values fail closed before serialization."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _non_finite_plate(**_kwargs: object) -> dict[str, Any]:
        payload = _valid_generated_plate()
        if response_field == "portions":
            payload["portions"]["protein_palm"] = non_finite_value
        else:
            payload["layout"][0]["fraction"] = non_finite_value
        return payload

    dependencies = PlateServiceDependencies(
        make_plate=_non_finite_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_empty_micros,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generate_plate_response(
                _request(),
                dependencies=dependencies,
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == ENHANCED_PLATE_GENERATION_FAILED_DETAIL
    assert response_field not in str(exc_info.value.detail)


@pytest.mark.parametrize(
    "response_field",
    [
        pytest.param("portions", id="portions-boolean"),
        pytest.param("meal_micros", id="meal-micros-boolean"),
    ],
)
def test_generate_plate_response_rejects_boolean_response_bound_output(
    monkeypatch: pytest.MonkeyPatch,
    response_field: str,
) -> None:
    """Boolean provider values cannot masquerade as numeric Plate output."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _boolean_plate(**_kwargs: object) -> dict[str, Any]:
        payload = _valid_generated_plate_with_meal()
        if response_field == "portions":
            payload["portions"]["protein_palm"] = True
        else:
            payload["meals"][0]["micros"] = {"iron_mg": True}
        return payload

    dependencies = PlateServiceDependencies(
        make_plate=_boolean_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_empty_micros,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(generate_plate_response(_request(), dependencies=dependencies))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == ENHANCED_PLATE_GENERATION_FAILED_DETAIL
    assert response_field not in str(exc_info.value.detail)


@pytest.mark.parametrize(
    "invalid_numeric",
    [
        pytest.param(None, id="none"),
        pytest.param(object(), id="object"),
        pytest.param([], id="list"),
    ],
)
def test_generate_plate_response_rejects_non_numeric_response_bound_output(
    monkeypatch: pytest.MonkeyPatch,
    invalid_numeric: object,
) -> None:
    """Malformed provider values cannot be replaced by a fabricated fiber minimum."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _invalid_plate(**_kwargs: object) -> dict[str, Any]:
        payload = _valid_generated_plate()
        payload["macros"]["fiber_g"] = invalid_numeric
        return payload

    dependencies = PlateServiceDependencies(
        make_plate=_invalid_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_empty_micros,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(generate_plate_response(_request(), dependencies=dependencies))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == ENHANCED_PLATE_GENERATION_FAILED_DETAIL
    assert "fiber" not in str(exc_info.value.detail).casefold()


@pytest.mark.parametrize(
    "container_case",
    [
        pytest.param("mappingproxy-macros", id="mappingproxy-macros"),
        pytest.param("mappingproxy-portions", id="mappingproxy-portions"),
        pytest.param("tuple-layout", id="tuple-layout"),
        pytest.param("tuple-meals", id="tuple-meals"),
    ],
)
def test_generate_plate_response_rejects_coercible_numeric_containers(
    monkeypatch: pytest.MonkeyPatch,
    container_case: str,
) -> None:
    """Pydantic-coercible containers cannot bypass raw dependency validation."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _coercible_plate(**_kwargs: object) -> dict[str, Any]:
        payload = _valid_generated_plate_with_meal()
        if container_case == "mappingproxy-macros":
            macros = dict(payload["macros"])
            macros["fiber_g"] = True
            payload["macros"] = MappingProxyType(macros)
        elif container_case == "mappingproxy-portions":
            portions = dict(payload["portions"])
            portions["protein_palm"] = "3.2"
            payload["portions"] = MappingProxyType(portions)
        elif container_case == "tuple-layout":
            layout = [dict(item) for item in payload["layout"]]
            layout[0]["fraction"] = "0.35"
            payload["layout"] = tuple(layout)
        else:
            meals = [dict(meal) for meal in payload["meals"]]
            meals[0]["kcal"] = "500"
            payload["meals"] = tuple(meals)
        return payload

    dependencies = PlateServiceDependencies(
        make_plate=_coercible_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_empty_micros,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(generate_plate_response(_request(), dependencies=dependencies))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == ENHANCED_PLATE_GENERATION_FAILED_DETAIL
    assert container_case not in str(exc_info.value.detail)


@pytest.mark.parametrize("response_field", ["portions", "layout"])
@pytest.mark.parametrize(
    "numeric_token",
    [
        pytest.param("2.0", id="finite"),
        pytest.param("NaN", id="nan"),
        pytest.param("Infinity", id="infinity"),
        pytest.param("-Infinity", id="negative-infinity"),
        pytest.param("+nAn", id="case-and-sign-nan"),
        pytest.param(" -InFiNiTy ", id="whitespace-case-and-sign-infinity"),
        pytest.param("1e309", id="exponent-overflow"),
    ],
)
def test_generate_plate_response_rejects_numeric_string_response_bound_output(
    monkeypatch: pytest.MonkeyPatch,
    response_field: str,
    numeric_token: str,
) -> None:
    """Numeric strings fail closed before response coercion."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _non_finite_plate(**_kwargs: object) -> dict[str, Any]:
        payload = _valid_generated_plate()
        if response_field == "portions":
            payload["portions"]["protein_palm"] = numeric_token
        else:
            payload["layout"][0]["fraction"] = numeric_token
        return payload

    dependencies = PlateServiceDependencies(
        make_plate=_non_finite_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_empty_micros,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generate_plate_response(
                _request(),
                dependencies=dependencies,
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == ENHANCED_PLATE_GENERATION_FAILED_DETAIL
    detail = str(exc_info.value.detail).casefold()
    assert "nan" not in detail
    assert "infinity" not in detail
    assert numeric_token.strip().casefold() not in detail


def test_generate_plate_response_allows_exact_numeric_tokens_in_text_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact numeric-looking tokens remain valid in schema-defined text fields."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _text_token_plate(**_kwargs: object) -> dict[str, Any]:
        payload = _valid_generated_plate()
        payload["layout"][0]["label"] = "Infinity"
        payload["layout"][0]["tooltip"] = "NaN"
        payload["meals"] = [
            {
                "title": "Inf",
                "kcal": 500,
                "protein_g": 30,
                "fat_g": 15,
                "carbs_g": 60,
                "fiber_g": 8,
                "micros": {"iron_mg": 1.0},
            }
        ]
        return payload

    dependencies = PlateServiceDependencies(
        make_plate=_text_token_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_empty_micros,
    )

    response = asyncio.run(
        generate_plate_response(
            _request(),
            dependencies=dependencies,
        )
    )

    assert response.layout[0].label == "Infinity"
    assert response.layout[0].tooltip == "NaN"
    assert response.meals[0]["title"] == "Inf"


@pytest.mark.parametrize(
    "non_finite_value",
    [float("nan"), float("inf"), float("-inf")],
    ids=["nan", "positive-infinity", "negative-infinity"],
)
@pytest.mark.parametrize("source_field", ["grams", "per_g"])
def test_generate_plate_response_rejects_non_finite_ingredient_db_measurements(
    monkeypatch: pytest.MonkeyPatch,
    non_finite_value: float,
    source_field: str,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _db_food(_food_id: str) -> dict[str, float]:
        return {
            "per_g": (non_finite_value if source_field == "per_g" else 100.0),
            "Fe_mg": 1.0,
        }

    async def _db_aggregator(
        _meals: list[dict[str, Any]],
    ) -> dict[str, float]:
        return await pro_nutrition_plate._aggregate_meal_micronutrients(
            [
                {
                    "food_id": "db-food",
                    "grams": (non_finite_value if source_field == "grams" else 100.0),
                }
            ],
            meal_title="Meal",
        )

    monkeypatch.setattr(pro_nutrition_plate, "get_food", _db_food)
    dependencies = PlateServiceDependencies(
        make_plate=_valid_generated_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_db_aggregator,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generate_plate_response(
                _request(),
                dependencies=dependencies,
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == ENHANCED_PLATE_GENERATION_FAILED_DETAIL
    assert source_field not in str(exc_info.value.detail)


def test_generate_plate_response_missing_nh3_is_exact_424(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _missing_nh3(_data: dict[str, Any]) -> dict[str, Any]:
        raise MissingOptionalDependencyError("nh3", "private dependency trace")

    monkeypatch.setattr(
        pro_nutrition_plate,
        "sanity_filter_plate_data",
        _missing_nh3,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(generate_plate_response(_request(), dependencies=_real_dependencies()))

    assert exc_info.value.status_code == 424
    assert exc_info.value.detail == {
        "error": "missing_dependency",
        "dependency": "nh3",
        "message": (
            "HTML sanitization library (nh3) is required for premium " "plate sanitization."
        ),
        "action": "Install server dependency: python -m pip install nh3",
    }


@pytest.mark.parametrize("error", [OverflowError, TypeError, ValueError])
def test_plate_request_rejects_unconvertible_measurements(
    error: type[Exception],
) -> None:
    """All measurement conversion failures remain deterministic schema errors."""

    payload = _request().model_dump()
    payload["height_cm"] = _ExplodingMeasurement(error)

    with pytest.raises(ValidationError):
        PlateRequest.model_validate(payload)


@pytest.mark.parametrize("field_name", ["height_cm", "weight_kg"])
def test_plate_request_rejects_boolean_measurements(field_name: str) -> None:
    """Boolean JSON values must not be coerced into physical measurements."""

    payload = _request().model_dump()
    payload[field_name] = True

    with pytest.raises(ValidationError, match="measurement must be numeric"):
        PlateRequest.model_validate(payload)


def test_numeric_dependency_helpers_reject_conversion_and_shape_failures() -> None:
    """Low-level validators fail closed on malformed provider objects."""

    with pytest.raises(pro_nutrition_plate._InvalidPlateCalculationOutputError):
        pro_nutrition_plate._validate_calculation_mapping({"mifflin": _ExplodingNumber()})
    pro_nutrition_plate._ensure_finite_dependency_output(True)
    pro_nutrition_plate._ensure_finite_dependency_output("display text")
    with pytest.raises(pro_nutrition_plate._NonFinitePlateDependencyOutputError):
        pro_nutrition_plate._ensure_finite_dependency_output(_ExplodingNumber())
    with pytest.raises(pro_nutrition_plate._NonFinitePlateDependencyOutputError):
        pro_nutrition_plate._ensure_finite_numeric_value("12.5")
    with pytest.raises(pro_nutrition_plate._NonFinitePlateDependencyOutputError):
        pro_nutrition_plate._ensure_finite_numeric_value(None)
    with pytest.raises(pro_nutrition_plate._NonFinitePlateDependencyOutputError):
        pro_nutrition_plate._ensure_finite_numeric_value(object())
    with pytest.raises(pro_nutrition_plate._NonFinitePlateDependencyOutputError):
        pro_nutrition_plate._ensure_finite_plate_response_output("not a mapping")
    malformed_meals = _valid_generated_plate()
    malformed_meals["meals"] = ["not a meal mapping"]
    with pytest.raises(pro_nutrition_plate._NonFinitePlateDependencyOutputError):
        pro_nutrition_plate._ensure_finite_plate_response_output(malformed_meals)


def test_micronutrient_helpers_reject_malformed_provider_values() -> None:
    """Micronutrient adapters reject non-mappings and conversion overflows."""

    with pytest.raises(pro_nutrition_plate._InvalidPlateMicronutrientOutputError):
        pro_nutrition_plate._validated_micronutrient_mapping([])
    with pytest.raises(pro_nutrition_plate._InvalidPlateMicronutrientOutputError):
        pro_nutrition_plate._validated_micronutrient_mapping({"iron_mg": _ExplodingNumber()})
    with pytest.raises(pro_nutrition_plate._NonFinitePlateDependencyOutputError):
        pro_nutrition_plate._convert_db_nutrients_to_alias_format({"Fe_mg": _ExplodingNumber()})


@pytest.mark.parametrize(
    ("grams", "food", "expected_error"),
    [
        pytest.param(
            _ExplodingNumber(),
            {"per_g": 100.0, "Fe_mg": 1.0},
            pro_nutrition_plate._NonFinitePlateDependencyOutputError,
            id="grams-overflow",
        ),
        pytest.param(
            -1.0,
            {"per_g": 100.0, "Fe_mg": 1.0},
            pro_nutrition_plate._InvalidPlateMicronutrientOutputError,
            id="negative-grams",
        ),
        pytest.param(
            100.0,
            {"per_g": _ExplodingNumber(), "Fe_mg": 1.0},
            pro_nutrition_plate._NonFinitePlateDependencyOutputError,
            id="serving-basis-overflow",
        ),
        pytest.param(
            100.0,
            {"per_g": 100.0, "Fe_mg": _ExplodingNumber()},
            pro_nutrition_plate._NonFinitePlateDependencyOutputError,
            id="nutrient-overflow",
        ),
    ],
)
def test_meal_micronutrient_aggregation_rejects_invalid_measurements(
    monkeypatch: pytest.MonkeyPatch,
    grams: object,
    food: dict[str, object],
    expected_error: type[Exception],
) -> None:
    """Persisted ingredient measurements are validated before arithmetic."""

    monkeypatch.setattr(pro_nutrition_plate, "get_food", lambda _food_id: food)

    with pytest.raises(expected_error):
        asyncio.run(
            pro_nutrition_plate._aggregate_meal_micronutrients(
                [{"food_id": "food-1", "grams": grams}],
                meal_title="Meal",
            )
        )


@pytest.mark.parametrize(
    "ingredients_json",
    [
        pytest.param('[{"grams": 100}]', id="missing-food-id"),
        pytest.param('["invalid"]', id="invalid-entry-shape"),
    ],
)
def test_recipe_ingredient_provider_rejects_malformed_entries(
    monkeypatch: pytest.MonkeyPatch,
    ingredients_json: str,
) -> None:
    """Recipe fallback rejects entries that cannot identify a food and amount."""

    monkeypatch.setattr(
        pro_nutrition_plate.recipe_store,
        "search_recipes",
        lambda _title, limit: [{"recipe_id": "recipe-1"}],
    )
    monkeypatch.setattr(
        pro_nutrition_plate.recipe_store,
        "get_recipe",
        lambda _recipe_id: {"ingredients_json": ingredients_json},
    )

    with pytest.raises(pro_nutrition_plate._InvalidPlateMicronutrientOutputError):
        pro_nutrition_plate._get_recipe_ingredients_for_meal("Meal")


def test_recipe_and_day_aggregation_handle_missing_optional_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Absent recipe evidence stays empty and malformed meal containers are ignored."""

    monkeypatch.setattr(
        pro_nutrition_plate.recipe_store,
        "search_recipes",
        lambda _title, limit: [{"recipe_id": "recipe-1"}],
    )
    monkeypatch.setattr(
        pro_nutrition_plate.recipe_store,
        "get_recipe",
        lambda _recipe_id: {"ingredients_json": None},
    )
    assert pro_nutrition_plate._get_recipe_ingredients_for_meal("Meal") == []

    monkeypatch.setattr(
        pro_nutrition_plate,
        "_get_recipe_ingredients_for_meal",
        lambda _title: [],
    )
    day_micros = asyncio.run(
        pro_nutrition_plate._aggregate_day_micronutrients(
            [{"title": "Meal", "ingredients": "invalid"}]
        )
    )
    assert day_micros == {}


def test_macro_helpers_cover_invalid_and_bounded_high_weight_inputs() -> None:
    """Macro calculation rejects malformed values and scales oversized profiles."""

    assert pro_nutrition_plate._macros_to_kcal({"protein_g": object()}) is None
    protein_g, fat_g, carbs_g = pro_nutrition_plate.calculate_heuristic_macros(
        1200,
        1000,
    )
    assert protein_g >= 0
    assert fat_g >= 0
    assert carbs_g >= 1
    assert protein_g * 4 + fat_g * 9 + carbs_g * 4 <= 1204


def test_gain_fallback_uses_default_surplus() -> None:
    """The documented gain fallback remains bounded without an explicit surplus."""

    request = _request().model_copy(update={"goal": "gain", "surplus_pct": None})
    response = pro_nutrition_plate.build_fallback_plate(request)
    assert 1200 <= response.kcal <= 2400
    assert response.macros["protein_g"] > 0


def test_fallback_scales_high_weight_macros_after_kcal_clamp() -> None:
    """Accepted high weights cannot escape the bounded fallback macro budget."""

    request = _request().model_copy(update={"weight_kg": 400.0})

    response = pro_nutrition_plate.build_fallback_plate(request)

    assert response.kcal == 2400
    for macro_name in ("protein_g", "fat_g", "carbs_g"):
        minimum, maximum = pro_nutrition_plate.PLATE_MACRO_RANGES[macro_name]
        assert minimum <= response.macros[macro_name] <= maximum
    macro_kcal = (
        response.macros["protein_g"] * 4
        + response.macros["fat_g"] * 9
        + response.macros["carbs_g"] * 4
    )
    assert macro_kcal <= response.kcal + 4


def test_alignment_handles_missing_invalid_and_unexpected_target_outputs() -> None:
    """Injected target adapters cannot silently corrupt generated macro output."""

    plate_data = {"macros": {"protein_g": 90, "fat_g": 55}}

    def _unexpected_factory(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("private target adapter failure")

    with pytest.raises(RuntimeError, match="private target adapter failure"):
        pro_nutrition_plate.align_macros_with_targets(
            _request(),
            plate_data,
            targets_builder=lambda _profile: object(),
            targets_response_factory=_unexpected_factory,
        )

    def _partial_factory(*_args: object, **_kwargs: object) -> object:
        return SimpleNamespace(
            kcal_daily="invalid",
            macros={"protein_g": 100, "fat_g": None},
        )

    macros, kcal, aligned = pro_nutrition_plate.align_macros_with_targets(
        _request(),
        plate_data,
        targets_builder=lambda _profile: object(),
        targets_response_factory=_partial_factory,
    )
    assert macros == {"protein_g": 100, "fat_g": 55}
    assert kcal is None
    assert aligned is True


@pytest.mark.parametrize(
    "error",
    [
        ModuleNotFoundError("No module named 'nh3'", name="nh3"),
        ImportError("No module named nh3"),
    ],
)
def test_missing_nh3_detection_handles_import_error_variants(error: Exception) -> None:
    """Both Python import error shapes map to the stable dependency envelope."""

    assert pro_nutrition_plate._is_missing_nh3_error(error) is True


def test_generate_plate_response_handles_invalid_response_numbers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raw numeric strings fail closed while aligned invalid fiber stays bounded."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _invalid_kcal_plate(**_kwargs: object) -> dict[str, Any]:
        payload = _valid_generated_plate()
        payload["kcal"] = "invalid"
        return payload

    kcal_dependencies = PlateServiceDependencies(
        make_plate=_invalid_kcal_plate,
        calculate_all_bmr=nutrition_bmr.calculate_all_bmr,
        calculate_all_tdee=nutrition_bmr.calculate_all_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_empty_micros,
    )
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(generate_plate_response(_request(), dependencies=kcal_dependencies))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == ENHANCED_PLATE_GENERATION_FAILED_DETAIL

    monkeypatch.setattr(
        pro_nutrition_plate,
        "align_macros_with_targets",
        lambda *_args, **_kwargs: (
            {
                "protein_g": 100,
                "fat_g": 60,
                "carbs_g": 200,
                "fiber_g": "invalid",
            },
            2000,
            True,
        ),
    )
    fiber_response = asyncio.run(
        generate_plate_response(_request(), dependencies=_real_dependencies())
    )
    assert fiber_response.macros["fiber_g"] == int(round(pro_nutrition_plate.FIBER_MIN_G))


def test_value_error_caused_by_missing_nh3_is_exact_424(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A wrapped sanitizer dependency failure retains the stable 424 contract."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _wrapped_missing_nh3(_data: dict[str, Any]) -> dict[str, Any]:
        try:
            raise MissingOptionalDependencyError("nh3", "private dependency trace")
        except MissingOptionalDependencyError as exc:
            raise ValueError("private validation wrapper") from exc

    monkeypatch.setattr(
        pro_nutrition_plate,
        "sanitize_plate_data",
        _wrapped_missing_nh3,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(generate_plate_response(_request(), dependencies=_real_dependencies()))
    assert exc_info.value.status_code == 424
    assert exc_info.value.detail["dependency"] == "nh3"


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/services/pro_nutrition_plate.py",
        "app/routers/pro_nutrition_contracts.py",
    ],
)
def test_canonical_plate_runtime_has_no_legacy_imports(relative_path: str) -> None:
    """Canonical Plate owners must not regain the legacy reverse dependency."""

    source = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert "legacy_app" not in imported_modules
    assert all(not name.startswith("legacy_app.") for name in imported_modules)


def test_retained_plate_handler_has_no_legacy_imports() -> None:
    """Unrelated BMR shims do not weaken retained Plate ownership."""

    source = (_REPO_ROOT / "app/routers/legacy_premium_nutrition.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    handler = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "api_premium_plate"
    )

    assert all(
        not (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and (node.module == "legacy_app" or node.module.startswith("legacy_app."))
        )
        for node in ast.walk(handler)
    )


def test_retained_legacy_plate_helpers_are_exact_canonical_aliases() -> None:
    """Retained helper exports cannot become a second runtime owner."""

    assert legacy_app.calculate_heuristic_macros is pro_nutrition_plate.calculate_heuristic_macros
    assert (
        legacy_app._aggregate_day_micronutrients
        is pro_nutrition_plate._aggregate_day_micronutrients
    )
