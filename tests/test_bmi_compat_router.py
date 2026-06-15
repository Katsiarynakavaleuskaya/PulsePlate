from __future__ import annotations

import asyncio
import ast
from pathlib import Path
import sys
from typing import Any

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

import app.main as app_main
from app.routers.bmi_compat import BMI_COMPAT_ROUTE_SPECS, router
from app.schemas.bmi_compat import BMIRequest, BMIRequestV1
import app.services.bmi_compat as bmi_compat_service


def _post_routes_for(path: str) -> list[Any]:
    return [
        route
        for route in app_main.app.routes
        if getattr(route, "path", None) == path
        and "POST" in (getattr(route, "methods", None) or set())
    ]


def test_bmi_compat_router_defines_exact_compat_family() -> None:
    route_specs = {
        (
            str(getattr(route, "path", "")),
            "POST",
            bool(getattr(route, "include_in_schema", True)),
        )
        for route in router.routes
        if "POST" in (getattr(route, "methods", None) or set())
    }

    assert route_specs == set(BMI_COMPAT_ROUTE_SPECS)


def test_bmi_compat_routes_have_canonical_owner_and_no_duplicates() -> None:
    expected_names = {
        "/bmi": "bmi_endpoint",
        "/plan": "plan_endpoint",
        "/api/v1/bmi": "bmi_endpoint_v1",
    }
    expected_visibility = {
        path: include_in_schema for path, _method, include_in_schema in BMI_COMPAT_ROUTE_SPECS
    }

    for path, expected_name in expected_names.items():
        matching_routes = _post_routes_for(path)
        assert len(matching_routes) == 1
        route = matching_routes[0]
        assert route.endpoint.__module__ == "app.routers.bmi_compat"
        assert route.endpoint.__name__ == expected_name
        assert getattr(route, "include_in_schema", True) is expected_visibility[path]


def test_bmi_compat_openapi_visibility_is_stable(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    paths = response.json()["paths"]

    assert "/bmi" not in paths
    assert "/plan" not in paths
    assert "/api/v1/bmi" in paths
    post_operation = paths["/api/v1/bmi"]["post"]
    assert post_operation["operationId"] == "bmi_endpoint_v1_api_v1_bmi_post"
    request_schema = post_operation["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema == {"$ref": "#/components/schemas/BMIRequestV1"}


def test_bmi_compat_router_does_not_import_legacy_app() -> None:
    source_path = Path("app/routers/bmi_compat.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))

    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "legacy_app":
                    violations.append(f"import legacy_app at line {node.lineno}")
        elif isinstance(node, ast.ImportFrom) and node.module == "legacy_app":
            violations.append(f"from legacy_app import ... at line {node.lineno}")

    assert violations == []


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/bmi",
            {
                "weight_kg": 70.0,
                "height_m": 1.75,
                "age": 30,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
                "lang": "en",
            },
        ),
        (
            "/plan",
            {
                "weight_kg": 70.0,
                "height_m": 1.75,
                "age": 30,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
                "lang": "en",
            },
        ),
        (
            "/api/v1/bmi",
            {
                "weight_kg": 70.0,
                "height_cm": 175.0,
                "age": 30,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
                "lang": "en",
            },
        ),
    ],
)
@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "bad"}])
def test_bmi_compat_routes_remain_public_with_or_without_bad_api_key(
    client: TestClient,
    path: str,
    payload: dict[str, Any],
    headers: dict[str, str],
) -> None:
    response = client.post(
        path,
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200


def test_bmi_request_normalizes_legacy_aliases_and_visualization_truthy_values() -> None:
    req = BMIRequest.model_validate(
        {
            "weight": "72.5",
            "height": "180",
            "sex": "Mujer",
            "pregnant": "беременная",
            "athlete": "спортсмен",
            "with_visualization": "maybe",
        }
    )

    assert req.weight_kg == 72.5
    assert req.height_m == 1.8
    assert req.gender == "female"
    assert req.pregnant is True
    assert req.athlete is True
    assert req.include_chart is True


@pytest.mark.parametrize(
    ("payload", "expected_include_chart"),
    [
        ({"weight_kg": 70.0, "height_m": 1.75, "with_visualization": "off"}, False),
        ({"weight_kg": 70.0, "height_m": 1.75, "with_visualization": 1}, True),
    ],
)
def test_bmi_request_normalizes_visualization_falsey_and_non_string_values(
    payload: dict[str, Any],
    expected_include_chart: bool,
) -> None:
    req = BMIRequest.model_validate(payload)

    assert req.include_chart is expected_include_chart


@pytest.mark.parametrize(
    "payload",
    [
        {"weight": object(), "height_m": 1.75},
        {"weight_kg": 70.0, "height": object()},
    ],
)
def test_bmi_request_alias_conversion_failures_fall_through_to_validation(
    payload: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        BMIRequest.model_validate(payload)


def test_bmi_request_accepts_existing_model_instance() -> None:
    req = BMIRequest(weight_kg=70.0, height_m=1.75)

    assert BMIRequest.model_validate(req) is req


@pytest.mark.parametrize(
    "payload",
    [
        {"weight_kg": 70.0, "height_m": 1.75, "gender": "robot"},
        {"weight_kg": 20.0, "height_m": 2.0},
        {"weight_kg": 300.0, "height_m": 1.5},
    ],
)
def test_bmi_request_rejects_invalid_gender_and_unrealistic_bmi(
    payload: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        BMIRequest.model_validate(payload)


def test_bmi_request_v1_rejects_low_bmi_and_accepts_existing_model_instance() -> None:
    with pytest.raises(ValidationError):
        BMIRequestV1.model_validate({"weight_kg": 20.0, "height_cm": 200.0})

    req = BMIRequestV1(weight_kg=70.0, height_cm=175.0)

    assert BMIRequestV1.model_validate(req) is req


def test_visualization_fails_closed_when_matplotlib_flag_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = {"bmi": 22.5}
    req = BMIRequest(weight_kg=70.0, height_m=1.75, include_chart=True)
    monkeypatch.setattr(sys.modules["app"], "MATPLOTLIB_AVAILABLE", False, raising=False)

    bmi_compat_service.add_visualization_if_requested(result, req)

    assert result["visualization"] == {
        "error": "Visualization not available - matplotlib not installed",
        "available": False,
    }


@pytest.mark.parametrize(
    ("viz_result", "expected"),
    [
        ({"available": True, "image": "encoded"}, {"available": True, "image": "encoded"}),
        (
            {"available": False},
            {
                "error": "Visualization not available - generation failed",
                "available": False,
            },
        ),
    ],
)
def test_visualization_uses_resolved_generator_and_preserves_failure_shape(
    monkeypatch: pytest.MonkeyPatch,
    viz_result: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    result = {"bmi": 22.5}
    req = BMIRequest(weight_kg=70.0, height_m=1.75, include_chart=True)

    def _fake_visualization(**_: Any) -> dict[str, Any]:
        return viz_result

    monkeypatch.setattr(bmi_compat_service, "MATPLOTLIB_AVAILABLE", True)
    monkeypatch.setattr(sys.modules["app"], "MATPLOTLIB_AVAILABLE", True, raising=False)
    monkeypatch.setattr(
        bmi_compat_service,
        "resolve_attr",
        lambda *_args, **_kwargs: _fake_visualization,
    )

    bmi_compat_service.add_visualization_if_requested(result, req)

    assert result["visualization"] == expected


def test_localized_legacy_result_preserves_pregnancy_note() -> None:
    result = bmi_compat_service._localized_legacy_bmi_result(
        {
            "bmi": 24.0,
            "category": "normal",
            "group": "pregnant",
            "notes": [],
            "interpretation": "ignored",
        },
        lang="en",
    )

    assert result["note"]
    assert result["group"] == "pregnant"


def test_plan_endpoint_preserves_pregnant_russian_premium_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_bmi_handler(_: dict[str, Any]) -> dict[str, Any]:
        return {"bmi": 24.0, "group": "pregnant", "category": "normal"}

    monkeypatch.setattr(bmi_compat_service, "bmi_calculate_handler", _fake_bmi_handler)

    result = asyncio.run(
        bmi_compat_service.plan_endpoint(
            BMIRequest(
                weight_kg=70.0,
                height_m=1.75,
                gender="female",
                pregnant=True,
                premium=True,
                lang="ru",
            )
        )
    )

    assert result["category"] is None
    assert result["premium_reco"]
    assert result["summary"] == "Персональный план (MVP)"


def test_plan_endpoint_preserves_english_premium_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_bmi_handler(_: dict[str, Any]) -> dict[str, Any]:
        return {"bmi": 24.0, "group": "general", "category": "normal"}

    monkeypatch.setattr(bmi_compat_service, "bmi_calculate_handler", _fake_bmi_handler)

    result = asyncio.run(
        bmi_compat_service.plan_endpoint(
            BMIRequest(weight_kg=70.0, height_m=1.75, premium=True, lang="en")
        )
    )

    assert result["category"] == "Normal weight"
    assert result["premium_reco"]
    assert result["summary"] == "Personal plan (MVP)"
