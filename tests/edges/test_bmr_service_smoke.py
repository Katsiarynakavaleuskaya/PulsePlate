"""Critical-smoke coverage for the canonical premium BMR service contract."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
import pytest

from app.http_error_details import (
    BMR_CALCULATION_FAILED_DETAIL,
    BMR_CALCULATION_MODULE_UNAVAILABLE_DETAIL,
    INVALID_BMR_INPUT_DETAIL,
    PREMIUM_BMR_FEATURE_UNAVAILABLE_DETAIL,
)
from app.schemas.bmr import BMRRequest, BMRRequestLegacy
from app.services import pro_nutrition_bmr as bmr_service
from app.services.pro_nutrition_bmr import BMRDependencies, calculate_bmr_response

_VALID_PAYLOAD: dict[str, object] = {
    "weight_kg": 70,
    "height_cm": 175,
    "age": 30,
    "sex": "male",
    "activity": "moderate",
    "lang": "en",
}


@pytest.fixture(autouse=True)
def _enable_premium_bmr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")


def _request(**overrides: object) -> BMRRequest:
    return BMRRequest.model_validate({**_VALID_PAYLOAD, **overrides})


def _dependencies(
    *,
    bmr_results: object = None,
    tdee_results: object = None,
    bmr_error: Exception | None = None,
) -> BMRDependencies:
    effective_bmr = {"mifflin": 1648.8, "harris": 1701.9} if bmr_results is None else bmr_results
    effective_tdee = {"mifflin": 2556.0, "harris": 2638.0} if tdee_results is None else tdee_results

    def _calculate_bmr(
        _weight: float,
        _height: float,
        _age: int,
        _sex: str,
        _bodyfat: float | None,
    ) -> object:
        if bmr_error is not None:
            raise bmr_error
        return effective_bmr

    def _calculate_tdee(
        _bmr_results: dict[str, float],
        _activity: str,
    ) -> object:
        return effective_tdee

    return BMRDependencies(_calculate_bmr, _calculate_tdee)


@pytest.mark.parametrize("model", [BMRRequest, BMRRequestLegacy])
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("weight_kg", True),
        ("weight_kg", 10**400),
        ("height_cm", "not-a-number"),
        ("height_cm", 0),
        ("age", True),
    ],
)
def test_bmr_schema_rejects_unsafe_edge_values(
    model: type[BMRRequest] | type[BMRRequestLegacy],
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate({**_VALID_PAYLOAD, field: value})


def test_bmr_service_resolves_current_core_calculators_and_preserves_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _calculate_bmr(
        _weight: float,
        _height: float,
        _age: int,
        _sex: str,
        bodyfat: float | None,
    ) -> dict[str, float]:
        result = {"mifflin": 1648.8, "harris": 1701.9}
        if bodyfat is not None:
            result["katch"] = 1655.2
        return result

    def _calculate_tdee(
        bmr_results: dict[str, float],
        _activity: str,
    ) -> dict[str, float]:
        return {name: value * 1.55 for name, value in bmr_results.items()}

    monkeypatch.setattr(bmr_service.nutrition_bmr, "calculate_all_bmr", _calculate_bmr)
    monkeypatch.setattr(bmr_service.nutrition_bmr, "calculate_all_tdee", _calculate_tdee)

    response = asyncio.run(calculate_bmr_response(_request()))
    bodyfat_response = asyncio.run(calculate_bmr_response(_request(bodyfat=15, lang="ru")))

    assert response.formulas_used == ["mifflin", "harris"]
    assert response.notes == []
    assert response.activity_level == "Moderate activity"
    assert response.recommended_intake["maintenance"] == int(1648.8 * 1.55)
    assert bodyfat_response.formulas_used == ["mifflin", "harris", "katch"]
    assert bodyfat_response.notes == ["Использована формула Katch-McArdle (требует процент жира)"]


@pytest.mark.parametrize(
    ("bmr_results", "tdee_results"),
    [
        ([], None),
        ({1: 1000.0}, None),
        ({"mifflin": True}, None),
        ({"mifflin": 10**400}, None),
        ({"mifflin": float("inf")}, None),
        ({"mifflin": 1648.8}, {"mifflin": 2556.0, "harris": 2638.0}),
        (
            {"mifflin": 1648.8, "harris": 1701.9},
            {"mifflin": 2556.0},
        ),
    ],
)
def test_bmr_service_rejects_malformed_calculator_contracts(
    bmr_results: object,
    tdee_results: object,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            calculate_bmr_response(
                _request(),
                dependencies=_dependencies(
                    bmr_results=bmr_results,
                    tdee_results=tdee_results,
                ),
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == BMR_CALCULATION_FAILED_DETAIL


def test_bmr_service_fails_closed_when_feature_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FEATURE_PREMIUM_NUTRITION")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(calculate_bmr_response(_request(), dependencies=_dependencies()))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == PREMIUM_BMR_FEATURE_UNAVAILABLE_DETAIL


@pytest.mark.parametrize(
    ("dependencies", "expected_status", "expected_detail"),
    [
        (
            BMRDependencies(None, None),
            503,
            BMR_CALCULATION_MODULE_UNAVAILABLE_DETAIL,
        ),
        (
            _dependencies(bmr_error=ImportError("private import detail")),
            503,
            BMR_CALCULATION_MODULE_UNAVAILABLE_DETAIL,
        ),
        (
            _dependencies(bmr_error=ValueError("private input detail")),
            400,
            INVALID_BMR_INPUT_DETAIL,
        ),
        (
            _dependencies(bmr_error=RuntimeError("private runtime detail")),
            500,
            BMR_CALCULATION_FAILED_DETAIL,
        ),
    ],
)
def test_bmr_service_sanitizes_dependency_failures(
    dependencies: BMRDependencies,
    expected_status: int,
    expected_detail: str,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(calculate_bmr_response(_request(), dependencies=dependencies))

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail == expected_detail


def test_bmr_dependency_resolution_rejects_non_callable_core_exports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bmr_service.nutrition_bmr, "calculate_all_bmr", object())
    monkeypatch.setattr(bmr_service.nutrition_bmr, "calculate_all_tdee", object())

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(calculate_bmr_response(_request()))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == BMR_CALCULATION_MODULE_UNAVAILABLE_DETAIL
