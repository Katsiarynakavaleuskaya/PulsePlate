from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
import pytest

import app.main as app_main
from app.routers.bmi_compat import BMI_COMPAT_ROUTE_SPECS, router


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
