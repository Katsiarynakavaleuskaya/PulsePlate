from __future__ import annotations

from collections import Counter

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import app.main as app_main
from app.bootstrap.route_family import route_has_dependency_call
from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_include_in_schema,
    route_methods,
    route_path,
)
from app.routers.api_key import require_app_api_key
from app.utils.feature_flags import is_business_module_enabled

_EXPECTED_BUSINESS_ROUTE_KEYS = {
    (path, method) for path, method, _include_in_schema in app_main._BUSINESS_ROUTE_SPECS
}
_EXPECTED_BUSINESS_ROUTE_PATHS = {path for path, _method in _EXPECTED_BUSINESS_ROUTE_KEYS}


@pytest.fixture(autouse=True)
def _clear_business_route_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BUSINESS_MODULE_ENABLED", raising=False)


def _set_business_flag(monkeypatch: pytest.MonkeyPatch, raw: str | None) -> None:
    if raw is None:
        monkeypatch.delenv("BUSINESS_MODULE_ENABLED", raising=False)
        return
    monkeypatch.setenv("BUSINESS_MODULE_ENABLED", raw)


def _business_routes(target_app: FastAPI) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if is_api_route_candidate(route) and route_path(route) in _EXPECTED_BUSINESS_ROUTE_PATHS
    ]


def _registered_business_route_counts(target_app: FastAPI) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for route in _business_routes(target_app):
        for method in route_methods(route):
            key = (route_path(route), method)
            if key in _EXPECTED_BUSINESS_ROUTE_KEYS:
                counts[key] += 1
    return counts


def _business_route(target_app: FastAPI, path: str, method: str) -> object:
    matches = [
        route
        for route in _business_routes(target_app)
        if route_path(route) == path and method in route_methods(route)
    ]
    assert len(matches) == 1
    return matches[0]


def _assert_business_routes_registered_once(target_app: FastAPI) -> None:
    counts = _registered_business_route_counts(target_app)
    assert set(counts) == _EXPECTED_BUSINESS_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())

    analyze_route = _business_route(target_app, "/api/v1/business/analyze", "POST")
    status_route = _business_route(target_app, "/api/v1/business/status", "GET")
    assert route_has_dependency_call(analyze_route, require_app_api_key)
    assert not route_has_dependency_call(status_route, require_app_api_key)


@pytest.mark.parametrize(
    ("raw_value", "expected_enabled"),
    [
        (None, False),
        ("", False),
        ("false", False),
        ("0", False),
        ("no", False),
        ("off", False),
        ("true", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        (" TRUE ", True),
    ],
)
def test_business_route_registration_env_matrix(
    monkeypatch: pytest.MonkeyPatch,
    raw_value: str | None,
    expected_enabled: bool,
) -> None:
    _set_business_flag(monkeypatch, raw_value)
    target_app = FastAPI()

    assert is_business_module_enabled() is expected_enabled

    app_main._include_business_router_if_enabled(target_app)

    if expected_enabled:
        _assert_business_routes_registered_once(target_app)
    else:
        assert _business_routes(target_app) == []


def test_business_route_registration_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "true")
    target_app = FastAPI()

    app_main._include_business_router_if_enabled(target_app)
    app_main._include_business_router_if_enabled(target_app)

    _assert_business_routes_registered_once(target_app)


def test_business_router_source_specs_match_current_visibility() -> None:
    route_specs: set[tuple[str, str, bool]] = set()
    for route in app_main.business_router.routes:
        assert isinstance(route, APIRoute)
        for method in route.methods or set():
            key = (str(route.path), str(method).upper())
            if key in _EXPECTED_BUSINESS_ROUTE_KEYS:
                route_specs.add((str(route.path), str(method).upper(), route.include_in_schema))

    assert route_specs == set(app_main._BUSINESS_ROUTE_SPECS)


def test_business_registration_rejects_partial_existing_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "true")
    target_app = FastAPI()
    path, method, include_in_schema = app_main._BUSINESS_ROUTE_SPECS[0]

    async def _partial_business_route() -> dict[str, str]:
        return {"status": "partial"}

    target_app.add_api_route(
        path,
        _partial_business_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(RuntimeError, match="Partial business route registration detected"):
        app_main._include_business_router_if_enabled(target_app)


def test_business_registration_rejects_existing_wrong_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "true")
    target_app = FastAPI()

    async def _wrong_method_business_route() -> dict[str, str]:
        return {"status": "wrong-method"}

    target_app.add_api_route(
        "/api/v1/business/analyze",
        _wrong_method_business_route,
        methods=["PUT"],
    )

    with pytest.raises(RuntimeError, match="Partial business route registration detected"):
        app_main._include_business_router_if_enabled(target_app)


def test_business_registration_rejects_foreign_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "true")
    target_app = FastAPI()

    for spec_path, method, include_in_schema in app_main._BUSINESS_ROUTE_SPECS:

        async def _foreign_business_route(current_route_path: str = spec_path) -> dict[str, str]:
            return {"path": current_route_path}

        target_app.add_api_route(
            spec_path,
            _foreign_business_route,
            methods=[method],
            include_in_schema=include_in_schema,
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different business handler",
    ):
        app_main._include_business_router_if_enabled(target_app)


def test_business_registration_rejects_source_visibility_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "true")
    source_route = next(iter(app_main.business_router.routes))
    assert isinstance(source_route, APIRoute)
    monkeypatch.setattr(source_route, "include_in_schema", False)

    with pytest.raises(RuntimeError, match="Business router does not preserve OpenAPI visibility"):
        app_main._include_business_router_if_enabled(FastAPI())


def test_business_analyze_keeps_api_key_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "yes")
    target_app = FastAPI()

    app_main._include_business_router_if_enabled(target_app)

    analyze_route = _business_route(target_app, "/api/v1/business/analyze", "POST")
    assert route_has_dependency_call(analyze_route, require_app_api_key)


def test_business_status_remains_unauthenticated_and_reflects_request_time_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "on")
    target_app = FastAPI()
    app_main._include_business_router_if_enabled(target_app)
    client = TestClient(target_app)

    response = client.get("/api/v1/business/status")
    assert response.status_code == 200
    assert response.json() == {"enabled": True, "module": "business_analysis"}

    monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "false")
    response = client.get("/api/v1/business/status")
    assert response.status_code == 200
    assert response.json() == {"enabled": False, "module": "business_analysis"}


def test_enabled_business_routes_stay_hidden_from_public_openapi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "true")

    app_main.ensure_canonical_app_bootstrap(app_main.app)
    app_main.app.openapi_schema = None

    paths = set(app_main.app.openapi().get("paths", {}))

    assert paths.isdisjoint(_EXPECTED_BUSINESS_ROUTE_PATHS)
