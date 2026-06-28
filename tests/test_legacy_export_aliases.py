from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

from fastapi import Response
from fastapi.testclient import TestClient
import pytest

import app as app_pkg
from app.effective_routes import (
    iter_effective_route_candidates,
    route_endpoint,
    route_include_in_schema,
    route_matches_path_method,
    route_responses,
)
import app.main as app_main
import legacy_app

REPO_ROOT = Path(__file__).resolve().parents[1]


def _matching_routes(path: str, method: str) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(app_main.app.routes)
        if route_matches_path_method(route, path, method)
    ]


def _is_legacy_api_key_dependency(dependency: object) -> bool:
    callable_dependency = getattr(dependency, "dependency", None)
    resolved_module = (
        inspect.getmodule(callable_dependency) if callable(callable_dependency) else None
    )
    return (
        callable(callable_dependency)
        and getattr(resolved_module, "__name__", "") == legacy_app.__name__
        and getattr(callable_dependency, "__name__", "") == "_get_api_key_dynamic"
    )


def test_legacy_export_alias_routes_are_hidden_shim_owned_and_protected() -> None:
    openapi_paths = app_main.app.openapi().get("paths", {})

    for path, method, include_in_schema in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS:
        matching_routes = _matching_routes(path, method)

        assert len(matching_routes) == 1
        route = matching_routes[0]
        endpoint = route_endpoint(route)
        assert getattr(endpoint, "__module__", "") == "app.routers.legacy_export_aliases"
        assert route_include_in_schema(route) is include_in_schema
        assert path not in openapi_paths
        assert 429 in route_responses(route)
        assert "request" in inspect.signature(endpoint).parameters
        dependencies = getattr(route, "dependencies", None)
        if dependencies is None:
            dependencies = getattr(getattr(route, "original_route", None), "dependencies", [])
        assert any(_is_legacy_api_key_dependency(dependency) for dependency in dependencies), (
            f"Expected legacy API-key dependency on {method} {path}, "
            f"got {[getattr(dependency, 'dependency', dependency) for dependency in dependencies]}"
        )


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("get", "/api/v1/premium/exports/day/auth.csv", {}),
        ("get", "/api/v1/premium/exports/week/auth.csv", {}),
        ("get", "/api/v1/premium/exports/day/auth.pdf", {}),
        ("get", "/api/v1/premium/exports/week/auth.pdf", {}),
        ("post", "/api/v1/export/pdf", {"json": {"meals": []}}),
    ],
)
def test_legacy_export_aliases_reject_missing_api_key(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    monkeypatch.setenv("API_KEY", "test_key")
    client = TestClient(app_main.app)

    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 403


def test_legacy_export_alias_daily_csv_preserves_response_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setattr(app_pkg, "to_csv_day", lambda _plan: b"Meal,Food Item\nA,B\n")
    monkeypatch.setattr(legacy_app, "to_csv_day", lambda _plan: b"Meal,Food Item\nA,B\n")
    client = TestClient(app_main.app)

    response = client.get(
        "/api/v1/premium/exports/day/test_plan.csv",
        headers={"X-API-Key": "test_key"},
    )

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/csv")
    assert "daily_plan_test_plan.csv" in response.headers.get("content-disposition", "")
    assert response.content == b"Meal,Food Item\nA,B\n"


@pytest.mark.parametrize(
    ("helper_name", "path", "content"),
    [
        ("export_weekly_plan_csv", "/api/v1/premium/exports/week/test_plan.csv", b"weekly,csv"),
        ("export_daily_plan_pdf", "/api/v1/premium/exports/day/test_plan.pdf", b"%PDF daily"),
        ("export_weekly_plan_pdf", "/api/v1/premium/exports/week/test_plan.pdf", b"%PDF weekly"),
    ],
)
def test_legacy_export_alias_get_routes_delegate_to_current_helper(
    monkeypatch: pytest.MonkeyPatch,
    helper_name: str,
    path: str,
    content: bytes,
) -> None:
    monkeypatch.setenv("API_KEY", "test_key")

    async def _patched_export(_plan_id: str) -> Response:
        return Response(content=content, media_type="application/octet-stream")

    monkeypatch.setattr(legacy_app, helper_name, _patched_export)
    client = TestClient(app_main.app)

    response = client.get(path, headers={"X-API-Key": "test_key"})

    assert response.status_code == 200
    assert response.content == content


def test_legacy_export_alias_generic_pdf_preserves_empty_payload_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "test_key")
    client = TestClient(app_main.app)

    response = client.post(
        "/api/v1/export/pdf",
        headers={"X-API-Key": "test_key"},
        json={},
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "Empty export payload"


def test_legacy_export_alias_route_resolves_rebound_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "test_key")

    async def _patched_export_pdf_generic(_payload: dict[str, object]) -> Response:
        return Response(content=b"%PDF patched", media_type="application/pdf")

    monkeypatch.setattr(legacy_app, "export_pdf_generic", _patched_export_pdf_generic)
    client = TestClient(app_main.app)

    response = client.post(
        "/api/v1/export/pdf",
        headers={"X-API-Key": "test_key"},
        json={"meals": []},
    )

    assert response.status_code == 200
    assert response.content == b"%PDF patched"
    assert response.headers.get("content-type") == "application/pdf"


def test_legacy_export_aliases_absent_when_export_gate_is_disabled() -> None:
    code = """
import json
from app.effective_routes import iter_effective_route_candidates, route_methods, route_path
import app.main as app_main

counts = {}
for path, method, _include in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS:
    counts[f"{method} {path}"] = sum(
        1
        for route in iter_effective_route_candidates(app_main.app.routes)
        if route_path(route) == path and method in route_methods(route)
    )
print(json.dumps({"enabled": app_main._legacy_module.EXPORTS_ENABLED, "counts": counts}))
"""
    env = os.environ.copy()
    for key in ("CI", "DEBUG", "ENVIRONMENT", "FEATURE_EXPORTS", "TESTING"):
        env.pop(key, None)
    env["APP_ENV"] = "local"
    env["PYTEST_CURRENT_TEST"] = "skip-dotenv-for-export-gate-probe"

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload == {
        "enabled": False,
        "counts": {
            f"{method} {path}": 0
            for path, method, _include in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS
        },
    }
