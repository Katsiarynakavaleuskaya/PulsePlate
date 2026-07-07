from __future__ import annotations

from collections import Counter
from collections.abc import Callable

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import app.main as app_main
from app.bootstrap.route_family import route_has_dependency_call
from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_endpoint,
    route_include_in_schema,
    route_methods,
    route_path,
)

_EXPECTED_ROUTE_SPECS = app_main._LEGACY_PREMIUM_WEEKLY_PLAN_ROUTE_SPECS
_EXPECTED_ROUTE_KEYS = {
    (path, method) for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS
}
_EXPECTED_ROUTE_PATHS = {path for path, _method in _EXPECTED_ROUTE_KEYS}
_EXPECTED_ENDPOINT_MODULE = "app.routers.legacy_premium_weekly_plan"
_EXPECTED_ENDPOINTS = {
    ("/api/v1/premium/plan/week", "POST"): "api_weekly_menu",
}
_RESPONSE_MODELS = {
    ("/api/v1/premium/plan/week", "POST"): app_main._legacy_module.WeeklyMenuResponse,
}
_WEEKLY_PLAN_PATH = "/api/v1/premium/plan/week"
_WEEKLY_PLAN_METHOD = "POST"


def _assert_same_response_model(actual: object, expected: object) -> None:
    assert getattr(actual, "__module__", None) == getattr(expected, "__module__", None)
    assert getattr(actual, "__qualname__", None) == getattr(expected, "__qualname__", None)


def _all_api_paths(target_app: FastAPI) -> set[str]:
    return {
        route_path(route)
        for route in iter_effective_route_candidates(target_app.routes)
        if is_api_route_candidate(route)
    }


def _weekly_plan_routes(target_app: FastAPI) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if is_api_route_candidate(route) and route_path(route) in _EXPECTED_ROUTE_PATHS
    ]


def _registered_route_counts(target_app: FastAPI) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for route in _weekly_plan_routes(target_app):
        for method in route_methods(route):
            key = (route_path(route), method)
            if key in _EXPECTED_ROUTE_KEYS:
                counts[key] += 1
    return counts


def _weekly_plan_route(target_app: FastAPI, path: str, method: str) -> object:
    matches = [
        route
        for route in _weekly_plan_routes(target_app)
        if route_path(route) == path and method in route_methods(route)
    ]
    route_summaries = [
        f"{route_path(route)}:{sorted(route_methods(route))}:{route_endpoint(route).__module__}"
        for route in matches
    ]
    assert len(matches) == 1, (
        f"expected exactly one legacy premium weekly-plan route for {method} {path}; "
        f"found {len(matches)}: {route_summaries}"
    )
    return matches[0]


def _source_route(path: str, method: str) -> object:
    for route in app_main.legacy_premium_weekly_plan_router.routes:
        if not is_api_route_candidate(route):
            continue
        if str(route.path) == path and method in (route.methods or set()):
            return route
    raise AssertionError(f"missing source route: {method} {path}")


def _clone_endpoint_with_matching_identity(
    source_endpoint: Callable[..., object],
    dependency: Callable[..., object] | None,
) -> Callable[..., object]:
    if dependency is None:

        async def _endpoint_without_dependency() -> dict[str, str]:
            return {"status": "stub"}

        endpoint = _endpoint_without_dependency
    else:

        async def _endpoint_with_dependency(
            _dependency_result: object = Depends(dependency),
        ) -> dict[str, str]:
            return {"status": "stub"}

        endpoint = _endpoint_with_dependency

    endpoint.__module__ = source_endpoint.__module__
    endpoint.__name__ = source_endpoint.__name__
    endpoint.__qualname__ = source_endpoint.__qualname__
    return endpoint


def _assert_weekly_plan_route_registered_once(target_app: FastAPI) -> None:
    counts = _registered_route_counts(target_app)
    assert set(counts) == _EXPECTED_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())

    present_order: list[tuple[str, str]] = []
    for route in _weekly_plan_routes(target_app):
        for method in sorted(route_methods(route)):
            key = (route_path(route), method)
            if key in _EXPECTED_ROUTE_KEYS:
                present_order.append(key)
    assert tuple(present_order) == tuple(
        (path, method) for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS
    )

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _weekly_plan_route(target_app, path, method)
        key = (path, method)
        assert route_include_in_schema(route) is include_in_schema
        endpoint = route_endpoint(route)
        assert getattr(endpoint, "__module__", None) == _EXPECTED_ENDPOINT_MODULE
        assert getattr(endpoint, "__name__", None) == _EXPECTED_ENDPOINTS[key]
        _assert_same_response_model(route.response_model, _RESPONSE_MODELS[key])
        assert bool(route.deprecated) is True
        assert route_has_dependency_call(route, app_main._legacy_module._get_api_key_dynamic)


def test_empty_app_registers_legacy_premium_weekly_plan_route_once() -> None:
    target_app = FastAPI()

    app_main._include_legacy_premium_weekly_plan_router_if_needed(target_app)

    _assert_weekly_plan_route_registered_once(target_app)


def test_bootstrapped_app_registers_legacy_premium_weekly_plan_route_once() -> None:
    _assert_weekly_plan_route_registered_once(app_main.app)


def test_legacy_premium_weekly_plan_registration_is_idempotent() -> None:
    target_app = FastAPI()

    app_main._include_legacy_premium_weekly_plan_router_if_needed(target_app)
    app_main._include_legacy_premium_weekly_plan_router_if_needed(target_app)

    _assert_weekly_plan_route_registered_once(target_app)


def test_legacy_premium_weekly_plan_route_members_encode_api_key_dependency() -> None:
    members = {
        (member.path, member.method): member
        for member in app_main._legacy_premium_weekly_plan_route_members(
            app_main._legacy_module._get_api_key_dynamic
        )
    }

    assert set(members) == _EXPECTED_ROUTE_KEYS
    assert members[(_WEEKLY_PLAN_PATH, _WEEKLY_PLAN_METHOD)].required_dependencies == (
        app_main._legacy_module._get_api_key_dynamic,
    )


def test_legacy_premium_weekly_plan_source_route_preserves_metadata() -> None:
    route = _source_route(_WEEKLY_PLAN_PATH, _WEEKLY_PLAN_METHOD)

    assert route_include_in_schema(route) is False
    _assert_same_response_model(route.response_model, app_main._legacy_module.WeeklyMenuResponse)
    assert bool(route.deprecated) is True
    assert route_has_dependency_call(route, app_main._legacy_module._get_api_key_dynamic)


def test_legacy_premium_weekly_plan_public_openapi_path_remains_hidden() -> None:
    schema = app_main.app.openapi()
    paths = {str(path) for path in schema.get("paths", {})}

    assert _WEEKLY_PLAN_PATH not in paths


def test_legacy_premium_weekly_plan_requires_legacy_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "weekly-plan-secret")
    monkeypatch.setenv("VIP_MODULE_ENABLED", "false")
    client = TestClient(app_main.app)
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168.0,
        "weight_kg": 62.0,
        "activity": "moderate",
        "goal": "maintain",
        "diet_flags": [],
        "lang": "en",
    }

    missing_key = client.post(_WEEKLY_PLAN_PATH, json=payload)
    invalid_key = client.post(
        _WEEKLY_PLAN_PATH,
        json=payload,
        headers={"X-API-Key": "wrong-key"},
    )
    accepted_key = client.post(
        _WEEKLY_PLAN_PATH,
        json=payload,
        headers={"X-API-Key": "weekly-plan-secret"},
    )

    assert missing_key.status_code == 403
    assert invalid_key.status_code == 403
    assert accepted_key.status_code == 503
    assert accepted_key.json()["detail"] == "VIP module is disabled"


def test_legacy_premium_weekly_plan_registration_does_not_absorb_other_weekly_routes() -> None:
    target_app = FastAPI()

    app_main._include_legacy_premium_weekly_plan_router_if_needed(target_app)

    registered_paths = _all_api_paths(target_app)
    assert _WEEKLY_PLAN_PATH in registered_paths
    assert "/api/v1/premium/plan/week-flexible" not in registered_paths
    assert "/api/v1/pro/meal/weekly" not in registered_paths


def test_legacy_premium_weekly_plan_registration_rejects_missing_api_key_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main._legacy_module, "_get_api_key_dynamic", None)

    with pytest.raises(
        RuntimeError,
        match="Legacy premium weekly-plan API key dependency is unavailable",
    ):
        app_main._include_legacy_premium_weekly_plan_router_if_needed(FastAPI())


def test_legacy_premium_weekly_plan_registration_rejects_partial_existing_family() -> None:
    target_app = FastAPI()

    async def _partial_weekly_plan_route() -> dict[str, str]:
        return {"status": "partial"}

    target_app.add_api_route(
        _WEEKLY_PLAN_PATH,
        _partial_weekly_plan_route,
        methods=["GET"],
        include_in_schema=False,
    )

    with pytest.raises(
        RuntimeError,
        match="Partial legacy premium weekly-plan route registration detected",
    ):
        app_main._include_legacy_premium_weekly_plan_router_if_needed(target_app)


def test_legacy_premium_weekly_plan_registration_rejects_duplicate_method_path() -> None:
    target_app = FastAPI()
    app_main._include_legacy_premium_weekly_plan_router_if_needed(target_app)

    async def _duplicate_weekly_plan_route() -> dict[str, str]:
        return {"status": "duplicate"}

    target_app.add_api_route(
        _WEEKLY_PLAN_PATH,
        _duplicate_weekly_plan_route,
        methods=[_WEEKLY_PLAN_METHOD],
        include_in_schema=False,
    )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different legacy premium weekly-plan handler",
    ):
        app_main._include_legacy_premium_weekly_plan_router_if_needed(target_app)


def test_legacy_premium_weekly_plan_registration_rejects_foreign_handler() -> None:
    target_app = FastAPI()

    async def _foreign_weekly_plan_route() -> dict[str, str]:
        return {"status": "foreign"}

    target_app.add_api_route(
        _WEEKLY_PLAN_PATH,
        _foreign_weekly_plan_route,
        methods=[_WEEKLY_PLAN_METHOD],
        include_in_schema=False,
    )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different legacy premium weekly-plan handler",
    ):
        app_main._include_legacy_premium_weekly_plan_router_if_needed(target_app)


def test_legacy_premium_weekly_plan_registration_rejects_openapi_visibility_drift() -> None:
    target_app = FastAPI()
    source = _source_route(_WEEKLY_PLAN_PATH, _WEEKLY_PLAN_METHOD)
    endpoint = _clone_endpoint_with_matching_identity(
        route_endpoint(source),
        app_main._legacy_module._get_api_key_dynamic,
    )
    target_app.add_api_route(
        _WEEKLY_PLAN_PATH,
        endpoint,
        methods=[_WEEKLY_PLAN_METHOD],
        include_in_schema=True,
        dependencies=[Depends(app_main._legacy_module._get_api_key_dynamic)],
    )

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve legacy premium weekly-plan OpenAPI visibility",
    ):
        app_main._include_legacy_premium_weekly_plan_router_if_needed(target_app)


def test_legacy_premium_weekly_plan_registration_rejects_missing_api_key_dependency() -> None:
    target_app = FastAPI()
    source = _source_route(_WEEKLY_PLAN_PATH, _WEEKLY_PLAN_METHOD)
    endpoint = _clone_endpoint_with_matching_identity(route_endpoint(source), None)
    target_app.add_api_route(
        _WEEKLY_PLAN_PATH,
        endpoint,
        methods=[_WEEKLY_PLAN_METHOD],
        include_in_schema=False,
    )

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve legacy premium weekly-plan required dependency",
    ):
        app_main._include_legacy_premium_weekly_plan_router_if_needed(target_app)


def test_legacy_premium_weekly_plan_registration_accepts_reloaded_canonical_handler() -> None:
    target_app = FastAPI()
    source = _source_route(_WEEKLY_PLAN_PATH, _WEEKLY_PLAN_METHOD)
    endpoint = _clone_endpoint_with_matching_identity(
        route_endpoint(source),
        app_main._legacy_module._get_api_key_dynamic,
    )
    target_app.add_api_route(
        _WEEKLY_PLAN_PATH,
        endpoint,
        methods=[_WEEKLY_PLAN_METHOD],
        response_model=app_main._legacy_module.WeeklyMenuResponse,
        include_in_schema=False,
        deprecated=True,
        dependencies=[Depends(app_main._legacy_module._get_api_key_dynamic)],
    )

    app_main._include_legacy_premium_weekly_plan_router_if_needed(target_app)

    _assert_weekly_plan_route_registered_once(target_app)
