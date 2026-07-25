"""Deterministic contract tests for canonical premium BMR ownership."""

from __future__ import annotations

import ast
import asyncio
from collections.abc import Callable
from dataclasses import FrozenInstanceError
import logging
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app import app
from app.http_error_details import (
    BMR_CALCULATION_FAILED_DETAIL,
    BMR_CALCULATION_MODULE_UNAVAILABLE_DETAIL,
    INVALID_BMR_INPUT_DETAIL,
    PREMIUM_BMR_FEATURE_UNAVAILABLE_DETAIL,
)
from app.schemas.bmr import BMRRequest, BMRRequestLegacy
from app.services import pro_nutrition_bmr as bmr_service
from app.services.pro_nutrition_bmr import BMRDependencies, calculate_bmr_response

_REPO_ROOT = Path(__file__).resolve().parents[1]
_VALID_PAYLOAD: dict[str, Any] = {
    "weight_kg": 70,
    "height_cm": 175,
    "age": 30,
    "sex": "male",
    "activity": "moderate",
    "lang": "en",
}
_EXPECTED_RESPONSE = {
    "bmr": {"mifflin": 1648.8, "harris": 1701.9},
    "tdee": {"mifflin": 2556.0, "harris": 2638.0},
    "activity_level": "Moderate activity",
    "recommended_intake": {
        "maintenance": 2556.0,
        "weight_loss": 2044.8000000000002,
        "weight_gain": 3067.2,
    },
    "formulas_used": ["mifflin", "harris"],
    "notes": [],
}


@pytest.fixture(autouse=True)
def _configure_bmr_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _request(
    model: type[BMRRequest] | type[BMRRequestLegacy] = BMRRequest,
    **overrides: Any,
) -> BMRRequest | BMRRequestLegacy:
    return model.model_validate({**_VALID_PAYLOAD, **overrides})


def _dependencies(
    *,
    bmr_results: object = None,
    tdee_results: object = None,
) -> BMRDependencies:
    effective_bmr_results = (
        {"mifflin": 1648.8, "harris": 1701.9} if bmr_results is None else bmr_results
    )
    effective_tdee_results = (
        {"mifflin": 2556.0, "harris": 2638.0} if tdee_results is None else tdee_results
    )

    def _calculate_bmr(
        _weight: float,
        _height: float,
        _age: int,
        _sex: str,
        _bodyfat: float | None,
    ) -> object:
        return effective_bmr_results

    def _calculate_tdee(
        _bmr_results: dict[str, float],
        _activity: str,
    ) -> object:
        return effective_tdee_results

    return BMRDependencies(
        calculate_all_bmr=_calculate_bmr,
        calculate_all_tdee=_calculate_tdee,
    )


@pytest.mark.parametrize("model", [BMRRequest, BMRRequestLegacy])
@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("weight_kg", 0),
        ("weight_kg", -1),
        ("weight_kg", float("nan")),
        ("weight_kg", float("inf")),
        ("weight_kg", float("-inf")),
        ("weight_kg", True),
        ("weight_kg", 10**400),
        ("weight_kg", "1e400"),
        ("height_cm", 0),
        ("height_cm", -1),
        ("height_cm", float("nan")),
        ("height_cm", float("inf")),
        ("height_cm", float("-inf")),
        ("height_cm", False),
        ("height_cm", 10**400),
        ("height_cm", "1e400"),
        ("age", 0),
        ("age", 121),
        ("age", float("nan")),
        ("age", float("inf")),
        ("age", float("-inf")),
        ("age", True),
        ("bodyfat", 0),
        ("bodyfat", -1),
        ("bodyfat", 50.0001),
        ("bodyfat", float("nan")),
        ("bodyfat", float("inf")),
        ("bodyfat", float("-inf")),
        ("bodyfat", True),
        ("bodyfat", 10**400),
        ("bodyfat", "1e400"),
    ],
)
def test_bmr_request_models_reject_invalid_numeric_values(
    model: type[BMRRequest] | type[BMRRequestLegacy],
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate({**_VALID_PAYLOAD, field_name: value})


@pytest.mark.parametrize("model", [BMRRequest, BMRRequestLegacy])
@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"age": 1, "bodyfat": None}, (1, None, 70.0, 175.0)),
        ({"age": 120, "bodyfat": 50}, (120, 50.0, 70.0, 175.0)),
        (
            {"age": "30", "weight_kg": "70.5", "height_cm": "175.5"},
            (30, None, 70.5, 175.5),
        ),
        ({"bodyfat": "0.000001"}, (30, 0.000001, 70.0, 175.0)),
    ],
)
def test_bmr_request_models_preserve_valid_boundaries_and_numeric_strings(
    model: type[BMRRequest] | type[BMRRequestLegacy],
    overrides: dict[str, object],
    expected: tuple[int, float | None, float, float],
) -> None:
    request = model.model_validate({**_VALID_PAYLOAD, **overrides})

    assert request.age == expected[0]
    assert request.bodyfat == expected[1]
    assert request.weight_kg == expected[2]
    assert request.height_cm == expected[3]


@pytest.mark.parametrize("model", [BMRRequest, BMRRequestLegacy])
def test_bmr_request_model_schema_matches_core_boundaries(
    model: type[BMRRequest] | type[BMRRequestLegacy],
) -> None:
    properties = model.model_json_schema()["properties"]
    age_schema = properties["age"]
    bodyfat_schema = properties["bodyfat"]["anyOf"][0]

    assert age_schema["minimum"] == 1
    assert age_schema["maximum"] == 120
    assert bodyfat_schema["exclusiveMinimum"] == 0
    assert bodyfat_schema["maximum"] == 50


def test_bmr_dependencies_are_frozen_and_slotted() -> None:
    dependencies = _dependencies()

    assert not hasattr(dependencies, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(dependencies, "calculate_all_bmr", None)


def test_service_preserves_exact_response_and_localization_contract() -> None:
    response = asyncio.run(calculate_bmr_response(_request()))

    assert response.model_dump() == _EXPECTED_RESPONSE

    russian_response = asyncio.run(
        calculate_bmr_response(_request(bodyfat=15, lang="ru"))
    ).model_dump()
    assert russian_response["bmr"] == {
        "mifflin": 1648.8,
        "harris": 1701.9,
        "katch": 1655.2,
    }
    assert russian_response["tdee"] == {
        "mifflin": 2556.0,
        "harris": 2638.0,
        "katch": 2566.0,
    }
    assert russian_response["activity_level"] == "Умеренная активность"
    assert russian_response["notes"] == [
        "Использована формула Katch-McArdle (требует процент жира)"
    ]


@pytest.mark.parametrize(
    ("lang", "activity", "expected_activity_level"),
    [
        ("en", "sedentary", "Sedentary"),
        ("en", "light", "Light activity"),
        ("en", "moderate", "Moderate activity"),
        ("en", "active", "Active"),
        ("en", "very_active", "Very active"),
        ("ru", "sedentary", "Малоподвижный"),
        ("ru", "light", "Легкая активность"),
        ("ru", "moderate", "Умеренная активность"),
        ("ru", "active", "Активный"),
        ("ru", "very_active", "Очень активный"),
        ("es", "sedentary", "Sedentario"),
        ("es", "light", "Actividad ligera"),
        ("es", "moderate", "Actividad moderada"),
        ("es", "active", "Activo"),
        ("es", "very_active", "Muy activo"),
    ],
)
def test_service_preserves_all_activity_and_locale_labels(
    lang: str,
    activity: str,
    expected_activity_level: str,
) -> None:
    response = asyncio.run(calculate_bmr_response(_request(lang=lang, activity=activity)))

    assert response.activity_level == expected_activity_level


def test_service_resolves_direct_core_calculators_per_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tdee_inputs: list[dict[str, float]] = []

    def _first_bmr(
        _weight: float,
        _height: float,
        _age: int,
        _sex: str,
        _bodyfat: float | None,
    ) -> dict[str, float]:
        return {"mifflin": 1000.0, "harris": 1100.0}

    def _second_bmr(
        _weight: float,
        _height: float,
        _age: int,
        _sex: str,
        _bodyfat: float | None,
    ) -> dict[str, float]:
        return {"mifflin": 1200.0, "harris": 1300.0}

    def _calculate_tdee(
        bmr_results: dict[str, float],
        _activity: str,
    ) -> dict[str, float]:
        tdee_inputs.append(bmr_results)
        return {formula: value * 1.2 for formula, value in bmr_results.items()}

    monkeypatch.setattr(bmr_service.nutrition_bmr, "calculate_all_bmr", _first_bmr)
    monkeypatch.setattr(
        bmr_service.nutrition_bmr,
        "calculate_all_tdee",
        _calculate_tdee,
    )
    first = asyncio.run(calculate_bmr_response(_request()))

    monkeypatch.setattr(bmr_service.nutrition_bmr, "calculate_all_bmr", _second_bmr)
    second = asyncio.run(calculate_bmr_response(_request()))

    assert first.bmr == {"mifflin": 1000.0, "harris": 1100.0}
    assert second.bmr == {"mifflin": 1200.0, "harris": 1300.0}
    assert tdee_inputs == [
        {"mifflin": 1000.0, "harris": 1100.0},
        {"mifflin": 1200.0, "harris": 1300.0},
    ]


def test_feature_flag_short_circuits_before_calculators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _calculate_bmr(
        _weight: float,
        _height: float,
        _age: int,
        _sex: str,
        _bodyfat: float | None,
    ) -> dict[str, float]:
        calls.append("bmr")
        return {"mifflin": 1000.0}

    monkeypatch.delenv("FEATURE_PREMIUM_NUTRITION")
    dependencies = BMRDependencies(
        calculate_all_bmr=_calculate_bmr,
        calculate_all_tdee=lambda _results, _activity: {"mifflin": 1200.0},
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(calculate_bmr_response(_request(), dependencies=dependencies))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == PREMIUM_BMR_FEATURE_UNAVAILABLE_DETAIL
    assert calls == []


@pytest.mark.parametrize(
    "dependencies",
    [
        BMRDependencies(calculate_all_bmr=None, calculate_all_tdee=lambda _r, _a: {}),
        BMRDependencies(
            calculate_all_bmr=lambda _w, _h, _a, _s, _b: {},
            calculate_all_tdee=None,
        ),
        BMRDependencies(
            calculate_all_bmr=cast(Any, object()),
            calculate_all_tdee=lambda _r, _a: {},
        ),
        BMRDependencies(
            calculate_all_bmr=lambda _w, _h, _a, _s, _b: {},
            calculate_all_tdee=cast(Any, object()),
        ),
    ],
)
def test_missing_dependencies_fail_closed_with_stable_503(
    dependencies: BMRDependencies,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(calculate_bmr_response(_request(), dependencies=dependencies))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == BMR_CALCULATION_MODULE_UNAVAILABLE_DETAIL


def test_calculator_import_error_fails_closed_with_stable_503() -> None:
    def _raise_import_error(
        _weight: float,
        _height: float,
        _age: int,
        _sex: str,
        _bodyfat: float | None,
    ) -> object:
        raise ImportError("private import path")

    dependencies = BMRDependencies(
        calculate_all_bmr=_raise_import_error,
        calculate_all_tdee=lambda _results, _activity: {"mifflin": 1200.0},
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(calculate_bmr_response(_request(), dependencies=dependencies))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == BMR_CALCULATION_MODULE_UNAVAILABLE_DETAIL
    assert "private import path" not in str(exc_info.value.detail)


@pytest.mark.parametrize(
    "invalid_map",
    [
        [],
        {},
        MappingProxyType({"mifflin": 1000.0}),
        {1: 1000.0},
        {"": 1000.0},
        {"   ": 1000.0},
        {"mifflin": True},
        {"mifflin": "1000"},
        {"mifflin": object()},
        {"mifflin": float("nan")},
        {"mifflin": float("inf")},
        {"mifflin": float("-inf")},
        {"mifflin": 0},
        {"mifflin": -1},
    ],
)
def test_malformed_bmr_maps_fail_closed_with_generic_500(
    invalid_map: object,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            calculate_bmr_response(
                _request(),
                dependencies=_dependencies(bmr_results=invalid_map),
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == BMR_CALCULATION_FAILED_DETAIL


@pytest.mark.parametrize(
    "invalid_map",
    [
        [],
        {},
        MappingProxyType({"mifflin": 2000.0}),
        {1: 2000.0},
        {"": 2000.0},
        {"mifflin": False},
        {"mifflin": "2000"},
        {"mifflin": float("nan")},
        {"mifflin": float("inf")},
        {"mifflin": float("-inf")},
        {"mifflin": 0},
        {"mifflin": -1},
    ],
)
def test_malformed_tdee_maps_fail_closed_with_generic_500(
    invalid_map: object,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            calculate_bmr_response(
                _request(),
                dependencies=_dependencies(tdee_results=invalid_map),
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == BMR_CALCULATION_FAILED_DETAIL


@pytest.mark.parametrize(
    ("bmr_request", "dependencies"),
    [
        (
            _request(),
            _dependencies(
                bmr_results={"harris": 1701.9},
                tdee_results={"harris": 2638.0},
            ),
        ),
        (
            _request(bodyfat=15),
            _dependencies(),
        ),
        (
            _request(),
            _dependencies(tdee_results={"mifflin": 2556.0}),
        ),
        (
            _request(),
            _dependencies(
                bmr_results={"mifflin": 1648.8},
                tdee_results={"mifflin": 2556.0},
            ),
        ),
        (
            _request(),
            _dependencies(
                bmr_results={"mifflin": 1648.8, "harris": 1701.9, "extra": 1.0},
                tdee_results={"mifflin": 2556.0, "harris": 2638.0, "extra": 2.0},
            ),
        ),
        (
            _request(),
            _dependencies(
                bmr_results={"mifflin": 1648.8, "harris": 1701.9, "katch": 1655.2},
                tdee_results={"mifflin": 2556.0, "harris": 2638.0, "katch": 2566.0},
            ),
        ),
    ],
)
def test_result_key_contract_failures_return_generic_500(
    bmr_request: BMRRequest | BMRRequestLegacy,
    dependencies: BMRDependencies,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(calculate_bmr_response(bmr_request, dependencies=dependencies))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == BMR_CALCULATION_FAILED_DETAIL


def test_domain_value_error_is_sanitized_to_generic_400(
    caplog: pytest.LogCaptureFixture,
) -> None:
    internal_detail = "provider-internal-domain-detail"

    def _raise_value_error(
        _weight: float,
        _height: float,
        _age: int,
        _sex: str,
        _bodyfat: float | None,
    ) -> object:
        raise ValueError(internal_detail)

    caplog.set_level(logging.INFO, logger=bmr_service.__name__)
    dependencies = BMRDependencies(
        calculate_all_bmr=_raise_value_error,
        calculate_all_tdee=lambda _results, _activity: {"mifflin": 1200.0},
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(calculate_bmr_response(_request(), dependencies=dependencies))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == INVALID_BMR_INPUT_DETAIL
    assert internal_detail not in str(exc_info.value.detail)
    assert internal_detail not in caplog.text


def test_unexpected_error_is_logged_and_sanitized_to_generic_500(
    caplog: pytest.LogCaptureFixture,
) -> None:
    internal_detail = "provider-internal-unexpected-detail"

    def _raise_runtime_error(
        _weight: float,
        _height: float,
        _age: int,
        _sex: str,
        _bodyfat: float | None,
    ) -> object:
        raise RuntimeError(internal_detail)

    caplog.set_level(logging.ERROR, logger=bmr_service.__name__)
    dependencies = BMRDependencies(
        calculate_all_bmr=_raise_runtime_error,
        calculate_all_tdee=lambda _results, _activity: {"mifflin": 1200.0},
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(calculate_bmr_response(_request(), dependencies=dependencies))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == BMR_CALCULATION_FAILED_DETAIL
    assert internal_detail not in str(exc_info.value.detail)
    error_records = [
        record
        for record in caplog.records
        if record.name == bmr_service.__name__ and record.levelno == logging.ERROR
    ]
    assert len(error_records) == 1
    assert error_records[0].getMessage() == "Premium BMR calculation failed"
    assert error_records[0].exc_info is not None


@pytest.mark.parametrize(
    ("path", "headers"),
    [
        ("/api/v1/premium/bmr", {"X-API-Key": "test_key"}),
        ("/premium_bmr", {}),
    ],
)
@pytest.mark.parametrize(
    ("failure_kind", "expected_status", "expected_detail"),
    [
        ("domain", 400, INVALID_BMR_INPUT_DETAIL),
        ("malformed", 500, BMR_CALCULATION_FAILED_DETAIL),
        ("unexpected", 500, BMR_CALCULATION_FAILED_DETAIL),
        ("missing", 503, BMR_CALCULATION_MODULE_UNAVAILABLE_DETAIL),
        ("import", 503, BMR_CALCULATION_MODULE_UNAVAILABLE_DETAIL),
    ],
)
def test_bmr_routes_preserve_exact_calculation_error_contracts(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    headers: dict[str, str],
    failure_kind: str,
    expected_status: int,
    expected_detail: str,
) -> None:
    def _raise_value_error(
        _weight: float,
        _height: float,
        _age: int,
        _sex: str,
        _bodyfat: float | None,
    ) -> object:
        raise ValueError("private domain detail")

    def _raise_runtime_error(
        _weight: float,
        _height: float,
        _age: int,
        _sex: str,
        _bodyfat: float | None,
    ) -> object:
        raise RuntimeError("private runtime detail")

    def _raise_import_error(
        _weight: float,
        _height: float,
        _age: int,
        _sex: str,
        _bodyfat: float | None,
    ) -> object:
        raise ImportError("private import detail")

    def _valid_tdee(
        _results: dict[str, float],
        _activity: str,
    ) -> dict[str, float]:
        return {"mifflin": 2556.0, "harris": 2638.0}

    if failure_kind == "domain":
        dependencies = BMRDependencies(_raise_value_error, _valid_tdee)
    elif failure_kind == "malformed":
        dependencies = BMRDependencies(
            lambda _w, _h, _a, _s, _b: {"mifflin": True, "harris": 1701.9},
            _valid_tdee,
        )
    elif failure_kind == "unexpected":
        dependencies = BMRDependencies(_raise_runtime_error, _valid_tdee)
    elif failure_kind == "missing":
        dependencies = BMRDependencies(None, _valid_tdee)
    else:
        dependencies = BMRDependencies(_raise_import_error, _valid_tdee)

    monkeypatch.setattr(bmr_service, "_resolve_dependencies", lambda: dependencies)

    response = client.post(path, json=_VALID_PAYLOAD, headers=headers)

    assert response.status_code == expected_status
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": expected_detail}


def test_both_routes_preserve_the_exact_success_contract(client: TestClient) -> None:
    protected = client.post(
        "/api/v1/premium/bmr",
        json=_VALID_PAYLOAD,
        headers={"X-API-Key": "test_key"},
    )
    public_alias = client.post("/premium_bmr", json=_VALID_PAYLOAD)

    assert protected.status_code == 200
    assert public_alias.status_code == 200
    assert protected.headers["content-type"].startswith("application/json")
    assert public_alias.headers["content-type"].startswith("application/json")
    assert protected.json() == _EXPECTED_RESPONSE
    assert public_alias.json() == _EXPECTED_RESPONSE


def test_protected_route_retains_api_key_dependency(client: TestClient) -> None:
    missing = client.post("/api/v1/premium/bmr", json=_VALID_PAYLOAD)
    invalid = client.post(
        "/api/v1/premium/bmr",
        json=_VALID_PAYLOAD,
        headers={"X-API-Key": "invalid"},
    )

    assert missing.status_code == 403
    assert invalid.status_code == 403


def test_protected_route_auth_precedes_feature_availability(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FEATURE_PREMIUM_NUTRITION")

    missing = client.post("/api/v1/premium/bmr", json=_VALID_PAYLOAD)
    invalid = client.post(
        "/api/v1/premium/bmr",
        json=_VALID_PAYLOAD,
        headers={"X-API-Key": "invalid"},
    )

    assert missing.status_code == 403
    assert invalid.status_code == 403


@pytest.mark.parametrize(
    ("path", "headers"),
    [
        ("/api/v1/premium/bmr", {"X-API-Key": "test_key"}),
        ("/premium_bmr", {}),
    ],
)
@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("weight_kg", 10**400),
        ("weight_kg", "1e400"),
        ("height_cm", 10**400),
        ("height_cm", "1e400"),
        ("bodyfat", 10**400),
        ("bodyfat", "1e400"),
    ],
)
def test_bmr_routes_reject_overflowing_measurements_as_schema_error(
    client: TestClient,
    path: str,
    headers: dict[str, str],
    field_name: str,
    value: object,
) -> None:
    response = client.post(
        path,
        json={**_VALID_PAYLOAD, field_name: value},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize(
    ("path", "headers"),
    [
        ("/api/v1/premium/bmr", {"X-API-Key": "test_key"}),
        ("/premium_bmr", {}),
    ],
)
def test_bmr_routes_accept_numeric_strings(
    client: TestClient,
    path: str,
    headers: dict[str, str],
) -> None:
    response = client.post(
        path,
        json={
            **_VALID_PAYLOAD,
            "weight_kg": "70.5",
            "height_cm": "175.5",
            "age": "30",
            "bodyfat": "15",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["formulas_used"] == ["mifflin", "harris", "katch"]
    assert set(body["bmr"]) == {"mifflin", "harris", "katch"}


def test_public_alias_remains_public(client: TestClient) -> None:
    response = client.post("/premium_bmr", json=_VALID_PAYLOAD)

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("path", "headers"),
    [
        ("/api/v1/premium/bmr", {"X-API-Key": "test_key"}),
        ("/premium_bmr", {}),
    ],
)
def test_feature_disabled_returns_exact_503_on_both_routes(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    headers: dict[str, str],
) -> None:
    monkeypatch.delenv("FEATURE_PREMIUM_NUTRITION")

    response = client.post(path, json=_VALID_PAYLOAD, headers=headers)

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": PREMIUM_BMR_FEATURE_UNAVAILABLE_DETAIL}


def test_static_ownership_has_no_legacy_handler_or_dynamic_wrapper_rail() -> None:
    legacy_path = _REPO_ROOT / "legacy_app.py"
    router_path = _REPO_ROOT / "app/routers/legacy_premium_nutrition.py"
    service_path = _REPO_ROOT / "app/services/pro_nutrition_bmr.py"
    wrapper_path = _REPO_ROOT / "app/utils/nutrition_wrappers.py"

    legacy_tree = ast.parse(legacy_path.read_text(encoding="utf-8"))
    legacy_function_names = {
        node.name
        for node in legacy_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    legacy_source = legacy_path.read_text(encoding="utf-8")
    router_source = router_path.read_text(encoding="utf-8")
    service_source = service_path.read_text(encoding="utf-8")

    assert "api_premium_bmr" not in legacy_function_names
    assert "premium_bmr_legacy" not in legacy_function_names
    assert "_BASELINE_CALCULATE_ALL_BMR" not in legacy_source
    assert "_calculate_all_bmr_wrapper" not in legacy_source
    assert "nutrition_wrappers" not in legacy_source
    assert "legacy_app" not in router_source
    assert "calculate_bmr_response" in router_source
    assert not wrapper_path.exists()
    for forbidden in (
        "_ValidatedBMRInput",
        "_positive_finite_number",
        "_validate_effective_request",
        "_VALID_SEXES",
        "_VALID_ACTIVITIES",
        "_VALID_LANGUAGES",
        "sys.modules",
        "MagicMock",
        '"stub"',
        "nutrition_wrappers",
        "facade",
        "registry",
    ):
        assert forbidden not in service_source


def test_bmr_rejects_invalid_sex_at_core_boundary() -> None:
    from typing import cast

    from core.bmr import Sex, bmr_harris, bmr_mifflin

    with pytest.raises(ValueError, match=r"sex must be 'male' or 'female'"):
        bmr_mifflin(weight=70, height=175, age=30, sex=cast(Sex, "unknown"))
    with pytest.raises(ValueError, match=r"sex must be 'male' or 'female'"):
        bmr_harris(weight=70, height=175, age=30, sex=cast(Sex, "UNKNOWN"))
