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
from app.routers import api_key as canonical_api_key
import legacy_app

REPO_ROOT = Path(__file__).resolve().parents[1]
_RETAINED_LEGACY_EXPORT_ALIAS_SPECS = (
    ("/api/v1/premium/exports/day/{plan_id}.csv", "GET", False),
    ("/api/v1/premium/exports/week/{plan_id}.csv", "GET", False),
)


def _matching_routes(path: str, method: str) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(app_main.app.routes)
        if route_matches_path_method(route, path, method)
    ]


def _is_canonical_api_key_dependency(dependency: object) -> bool:
    callable_dependency = getattr(dependency, "dependency", None)
    return callable_dependency is canonical_api_key._get_api_key_dynamic


def test_legacy_export_alias_routes_are_hidden_shim_owned_and_protected() -> None:
    openapi_paths = app_main.app.openapi().get("paths", {})
    assert app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS == _RETAINED_LEGACY_EXPORT_ALIAS_SPECS

    for path, method, include_in_schema in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS:
        matching_routes = _matching_routes(path, method)

        assert len(matching_routes) == 1
        route = matching_routes[0]
        endpoint = route_endpoint(route)
        assert getattr(endpoint, "__module__", "") == "app.routers.legacy_export_aliases"
        assert route_include_in_schema(route) is include_in_schema
        assert path not in openapi_paths
        assert 429 in route_responses(route)
        assert callable(endpoint)
        assert "request" in inspect.signature(endpoint).parameters
        dependencies = getattr(route, "dependencies", None)
        if dependencies is None:
            dependencies = getattr(getattr(route, "original_route", None), "dependencies", [])
        assert any(_is_canonical_api_key_dependency(dependency) for dependency in dependencies), (
            f"Expected canonical API-key dependency on {method} {path}, "
            f"got {[getattr(dependency, 'dependency', dependency) for dependency in dependencies]}"
        )


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("get", "/api/v1/premium/exports/day/auth.csv", {}),
        ("get", "/api/v1/premium/exports/week/auth.csv", {}),
    ],
)
def test_retained_legacy_export_aliases_reject_missing_api_key(
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
    ],
)
def test_retained_legacy_export_alias_get_routes_delegate_to_current_helper(
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


@pytest.mark.parametrize(
    "gate_env",
    [
        pytest.param({"TESTING": "true"}, id="testing-flag"),
        pytest.param({"DEBUG": "true"}, id="debug-flag"),
        pytest.param({"FEATURE_EXPORTS": "true"}, id="feature-flag"),
        pytest.param({"APP_ENV": "test"}, id="app-env-test"),
        pytest.param({"APP_ENV": "testing"}, id="app-env-testing"),
        pytest.param({"APP_ENV": "ci"}, id="app-env-ci"),
    ],
)
def test_retired_legacy_pdf_aliases_are_absent_with_export_gate_enabled(
    gate_env: dict[str, str],
) -> None:
    code = """
import json
import os
from fastapi.testclient import TestClient
from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_matches_path_method,
)
import app.main as app_main

retained = (
    ("GET", "/api/v1/premium/exports/day/{plan_id}.csv", "/api/v1/premium/exports/day/probe.csv"),
    ("GET", "/api/v1/premium/exports/week/{plan_id}.csv", "/api/v1/premium/exports/week/probe.csv"),
)
retired = (
    ("POST", "/api/v1/export/pdf", "/api/v1/export/pdf"),
    ("GET", "/api/v1/premium/exports/day/{plan_id}.pdf", "/api/v1/premium/exports/day/probe.pdf"),
    ("GET", "/api/v1/premium/exports/week/{plan_id}.pdf", "/api/v1/premium/exports/week/probe.pdf"),
)

def count_routes(method, template):
    return sum(
        1
        for route in iter_effective_route_candidates(app_main.app.routes)
        if is_api_route_candidate(route) and route_matches_path_method(route, template, method)
    )

client = TestClient(app_main.app)
summary = {
    "enabled": app_main._legacy_module.EXPORTS_ENABLED,
    "retained_counts": {},
    "retained_statuses": {},
    "retired_counts": {},
    "retired_statuses": {},
}

for method, template, concrete_path in retained:
    key = f"{method} {template}"
    summary["retained_counts"][key] = count_routes(method, template)
    missing_key_response = client.get(concrete_path)
    valid_key_response = client.get(
        concrete_path,
        headers={"X-API-Key": os.environ["API_KEY"]},
    )
    assert missing_key_response.status_code == 403
    assert valid_key_response.status_code == 200
    summary["retained_statuses"][key] = [
        missing_key_response.status_code,
        valid_key_response.status_code,
    ]

for method, template, concrete_path in retired:
    key = f"{method} {template}"
    summary["retired_counts"][key] = count_routes(method, template)
    for auth_label, headers in (
        ("without-key", {}),
        ("with-valid-key", {"X-API-Key": os.environ["API_KEY"]}),
    ):
        if method == "POST":
            response = client.post(concrete_path, headers=headers, json={"meals": []})
        else:
            response = client.get(concrete_path, headers=headers)
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": "Not Found"}
        summary["retired_statuses"][f"{auth_label}:{key}"] = [
            response.status_code,
            response.json(),
        ]

print(json.dumps(summary, sort_keys=True))
"""
    env = os.environ.copy()
    for key in ("CI", "DEBUG", "ENVIRONMENT", "FEATURE_EXPORTS", "TESTING"):
        env.pop(key, None)
    env["APP_ENV"] = "local"
    env["PYTEST_CURRENT_TEST"] = "skip-dotenv-for-export-retirement-probe"
    env.update(gate_env)

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(result.stdout.strip().splitlines()[-1])
    assert summary["enabled"] is True
    assert summary["retained_counts"] == {
        "GET /api/v1/premium/exports/day/{plan_id}.csv": 1,
        "GET /api/v1/premium/exports/week/{plan_id}.csv": 1,
    }
    assert summary["retained_statuses"] == {
        "GET /api/v1/premium/exports/day/{plan_id}.csv": [403, 200],
        "GET /api/v1/premium/exports/week/{plan_id}.csv": [403, 200],
    }
    assert summary["retired_counts"] == {
        "GET /api/v1/premium/exports/day/{plan_id}.pdf": 0,
        "GET /api/v1/premium/exports/week/{plan_id}.pdf": 0,
        "POST /api/v1/export/pdf": 0,
    }
    assert len(summary["retired_statuses"]) == 6
    assert all(
        result == [404, {"detail": "Not Found"}] for result in summary["retired_statuses"].values()
    )


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
