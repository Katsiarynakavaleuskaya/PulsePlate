"""Deterministic contract tests for canonical PRO Plate ownership."""

from __future__ import annotations

import ast
import asyncio
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

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
from core.data_sanitizer import MissingOptionalDependencyError

_REPO_ROOT = Path(__file__).resolve().parents[1]


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


@pytest.mark.parametrize("response_field", ["portions", "layout"])
@pytest.mark.parametrize(
    "non_finite_token",
    [
        pytest.param("NaN", id="nan"),
        pytest.param("Infinity", id="infinity"),
        pytest.param("-Infinity", id="negative-infinity"),
        pytest.param("+nAn", id="case-and-sign-nan"),
        pytest.param(" -InFiNiTy ", id="whitespace-case-and-sign-infinity"),
        pytest.param("1e309", id="exponent-overflow"),
    ],
)
def test_generate_plate_response_rejects_non_finite_string_response_bound_output(
    monkeypatch: pytest.MonkeyPatch,
    response_field: str,
    non_finite_token: str,
) -> None:
    """Non-finite numeric strings fail closed before response coercion."""

    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def _non_finite_plate(**_kwargs: object) -> dict[str, Any]:
        payload = _valid_generated_plate()
        if response_field == "portions":
            payload["portions"]["protein_palm"] = non_finite_token
        else:
            payload["layout"][0]["fraction"] = non_finite_token
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
    assert non_finite_token.strip().casefold() not in detail


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


def test_legacy_plate_exports_are_exact_canonical_aliases() -> None:
    """Direct compatibility imports cannot become a second runtime owner."""

    assert legacy_app._compute_premium_plate is generate_plate_response
    assert legacy_app.api_premium_plate is generate_plate_response
    assert legacy_app.calculate_heuristic_macros is pro_nutrition_plate.calculate_heuristic_macros
    assert (
        legacy_app._aggregate_day_micronutrients
        is pro_nutrition_plate._aggregate_day_micronutrients
    )
