"""Finite retirement contract for the legacy test/demo export aliases."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tests._helpers.api_headers import API_KEY_HEADERS

REPO_ROOT = Path(__file__).resolve().parents[1]

_RETIRED_EXPORT_ROUTES = (
    ("GET", "/api/v1/premium/exports/day/{plan_id}.csv", "/api/v1/premium/exports/day/probe.csv"),
    (
        "GET",
        "/api/v1/premium/exports/week/{plan_id}.csv",
        "/api/v1/premium/exports/week/probe.csv",
    ),
    ("POST", "/api/v1/export/pdf", "/api/v1/export/pdf"),
    ("GET", "/api/v1/premium/exports/day/{plan_id}.pdf", "/api/v1/premium/exports/day/probe.pdf"),
    (
        "GET",
        "/api/v1/premium/exports/week/{plan_id}.pdf",
        "/api/v1/premium/exports/week/probe.pdf",
    ),
)

_CANONICAL_EXPORT_ROUTES = (
    ("POST", "/api/v1/export/sign"),
    ("GET", "/api/v1/plan/week/export.csv"),
    ("GET", "/api/v1/plan/week/export.pdf"),
)


@pytest.mark.parametrize(
    "carrier_env",
    [
        pytest.param({}, id="default-local"),
        pytest.param({"TESTING": "true"}, id="testing-flag"),
        pytest.param({"DEBUG": "true"}, id="debug-flag"),
        pytest.param({"FEATURE_EXPORTS": "true"}, id="retired-feature-flag"),
        pytest.param({"APP_ENV": "test"}, id="app-env-test"),
        pytest.param({"APP_ENV": "testing"}, id="app-env-testing"),
        pytest.param({"APP_ENV": "ci"}, id="app-env-ci"),
    ],
)
def test_legacy_export_aliases_remain_retired_in_fresh_process(
    carrier_env: dict[str, str],
) -> None:
    code = f"""
import importlib.util
import json
import os

from fastapi.testclient import TestClient

from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_matches_path_method,
    route_responses,
)
import app.main as app_main
import legacy_app

retired = {repr(_RETIRED_EXPORT_ROUTES)}
canonical = {repr(_CANONICAL_EXPORT_ROUTES)}
routes = [
    route
    for route in iter_effective_route_candidates(app_main.app.routes)
    if is_api_route_candidate(route)
]


def matching_routes(method, path):
    return [route for route in routes if route_matches_path_method(route, path, method)]


client = TestClient(app_main.app)
openapi_paths = app_main.app.openapi().get("paths", {{}})
retired_counts = {{}}
retired_statuses = {{}}
for method, template, concrete_path in retired:
    route_key = f"{{method}} {{template}}"
    retired_counts[route_key] = len(matching_routes(method, template))
    assert template not in openapi_paths
    for auth_label, headers in (
        ("without-key", {{}}),
        ("with-valid-key", {{"X-API-Key": os.environ["API_KEY"]}}),
    ):
        if method == "POST":
            response = client.post(concrete_path, headers=headers, json={{"meals": []}})
        else:
            response = client.get(concrete_path, headers=headers)
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {{"detail": "Not Found"}}
        retired_statuses[f"{{auth_label}}:{{route_key}}"] = [
            response.status_code,
            response.json(),
        ]

canonical_routes = {{}}
for method, path in canonical:
    route_key = f"{{method}} {{path}}"
    matching = matching_routes(method, path)
    canonical_routes[route_key] = {{
        "count": len(matching),
        "has_429": len(matching) == 1 and 429 in route_responses(matching[0]),
    }}

removed_symbols = {{
    "EXPORTS_ENABLED": hasattr(legacy_app, "EXPORTS_ENABLED"),
    "export_daily_plan_csv": hasattr(legacy_app, "export_daily_plan_csv"),
    "export_weekly_plan_csv": hasattr(legacy_app, "export_weekly_plan_csv"),
    "app_main_route_specs": hasattr(app_main, "_LEGACY_EXPORT_ALIAS_ROUTE_SPECS"),
    "app_main_router": hasattr(app_main, "legacy_export_aliases_router"),
    "app_main_registrar": hasattr(app_main, "_include_legacy_export_alias_router_if_needed"),
}}

print(
    json.dumps(
        {{
            "retired_counts": retired_counts,
            "retired_statuses": retired_statuses,
            "canonical_routes": canonical_routes,
            "removed_symbols": removed_symbols,
            "router_module_present": (
                importlib.util.find_spec("app.routers.legacy_export_aliases") is not None
            ),
        }},
        sort_keys=True,
    )
)
"""
    env = os.environ.copy()
    for key in (
        "APP_ENV",
        "CI",
        "DEBUG",
        "ENVIRONMENT",
        "FEATURE_EXPORTS",
        "TESTING",
    ):
        env.pop(key, None)
    env["APP_ENV"] = "local"
    env["API_KEY"] = API_KEY_HEADERS["X-API-Key"]
    env["PYTEST_CURRENT_TEST"] = "legacy-export-retirement-fresh-process"
    env.update(carrier_env)

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(result.stdout.strip().splitlines()[-1])
    assert summary["retired_counts"] == {
        f"{method} {path}": 0 for method, path, _concrete_path in _RETIRED_EXPORT_ROUTES
    }
    assert len(summary["retired_statuses"]) == len(_RETIRED_EXPORT_ROUTES) * 2
    assert all(
        status == [404, {"detail": "Not Found"}] for status in summary["retired_statuses"].values()
    )
    assert summary["canonical_routes"] == {
        f"{method} {path}": {"count": 1, "has_429": True}
        for method, path in _CANONICAL_EXPORT_ROUTES
    }
    assert summary["removed_symbols"] == {
        "EXPORTS_ENABLED": False,
        "app_main_registrar": False,
        "app_main_route_specs": False,
        "app_main_router": False,
        "export_daily_plan_csv": False,
        "export_weekly_plan_csv": False,
    }
    assert summary["router_module_present"] is False
