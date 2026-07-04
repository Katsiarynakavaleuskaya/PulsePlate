from __future__ import annotations

from collections import Counter
from collections.abc import Callable

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute

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

_EXPECTED_ROUTE_SPECS = app_main._USERS_ROUTE_SPECS
_EXPECTED_ROUTE_KEYS = {
    (path, method) for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS
}
_EXPECTED_ROUTE_PATHS = {path for path, _method in _EXPECTED_ROUTE_KEYS}
_EXPECTED_ENDPOINTS = {
    ("/api/v1/users", "POST"): "create_user",
    ("/api/v1/users", "GET"): "list_users",
    ("/api/v1/users/{user_id}", "GET"): "get_user",
    ("/api/v1/users/{user_id}", "DELETE"): "delete_user",
}
_EXPECTED_ENDPOINT_MODULE = "app.routers.users"


def _users_routes(target_app: FastAPI) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if is_api_route_candidate(route) and route_path(route) in _EXPECTED_ROUTE_PATHS
    ]


def _registered_route_counts(target_app: FastAPI) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for route in _users_routes(target_app):
        for method in route_methods(route):
            key = (route_path(route), method)
            if key in _EXPECTED_ROUTE_KEYS:
                counts[key] += 1
    return counts


def _users_route(target_app: FastAPI, path: str, method: str) -> object:
    matches = [
        route
        for route in _users_routes(target_app)
        if route_path(route) == path and method in route_methods(route)
    ]
    route_summaries = [
        f"{route_path(route)}:{sorted(route_methods(route))}:{route_endpoint(route).__module__}"
        for route in matches
    ]
    assert len(matches) == 1, (
        f"expected exactly one users route for {method} {path}; "
        f"found {len(matches)}: {route_summaries}"
    )
    return matches[0]


def _source_route(path: str, method: str) -> APIRoute:
    for route in app_main.users_router.routes:
        if not isinstance(route, APIRoute):
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
    endpoint.__qualname__ = source_endpoint.__qualname__
    return endpoint


def _assert_users_routes_registered_once(target_app: FastAPI) -> None:
    counts = _registered_route_counts(target_app)
    assert set(counts) == _EXPECTED_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _users_route(target_app, path, method)
        assert route_include_in_schema(route) is include_in_schema
        endpoint = route_endpoint(route)
        assert getattr(endpoint, "__module__", None) == _EXPECTED_ENDPOINT_MODULE
        assert getattr(endpoint, "__name__", None) == _EXPECTED_ENDPOINTS[(path, method)]
        assert route_has_dependency_call(route, app_main._require_users_api_key)


def test_empty_app_registers_all_users_routes_once() -> None:
    target_app = FastAPI()

    app_main._include_users_router_if_needed(target_app)

    _assert_users_routes_registered_once(target_app)


def test_bootstrapped_app_registers_all_users_routes_once() -> None:
    _assert_users_routes_registered_once(app_main.app)


def test_users_registration_is_idempotent() -> None:
    target_app = FastAPI()

    app_main._include_users_router_if_needed(target_app)
    app_main._include_users_router_if_needed(target_app)

    _assert_users_routes_registered_once(target_app)


def test_users_route_members_require_users_api_key() -> None:
    members = {(member.path, member.method): member for member in app_main._users_route_members()}

    assert set(members) == _EXPECTED_ROUTE_KEYS
    for member in members.values():
        assert member.required_dependencies == (app_main._require_users_api_key,)
        assert member.required_status_codes == frozenset()


def test_users_router_source_routes_preserve_api_key_dependency() -> None:
    for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _source_route(path, method)

        assert route_has_dependency_call(route, app_main._require_users_api_key)


def test_users_router_source_specs_match_current_visibility() -> None:
    route_specs: set[tuple[str, str, bool]] = set()
    for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _source_route(path, method)
        route_specs.add((str(route.path), method, route.include_in_schema))

    assert route_specs == set(_EXPECTED_ROUTE_SPECS)


def test_users_public_openapi_paths_remain_hidden() -> None:
    schema = app_main.app.openapi()
    paths = {str(path) for path in schema.get("paths", {})}

    leaked_paths = sorted(path for path in paths if path.startswith("/api/v1/users"))
    assert leaked_paths == []


def test_users_registration_rejects_partial_existing_family() -> None:
    target_app = FastAPI()
    path, method, include_in_schema = _EXPECTED_ROUTE_SPECS[0]

    async def _partial_users_route() -> dict[str, str]:
        return {"status": "partial"}

    target_app.add_api_route(
        path,
        _partial_users_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(RuntimeError, match="Partial users route registration detected"):
        app_main._include_users_router_if_needed(target_app)


def test_users_registration_rejects_duplicate_method_path() -> None:
    target_app = FastAPI()
    app_main._include_users_router_if_needed(target_app)
    path, method, include_in_schema = _EXPECTED_ROUTE_SPECS[0]

    async def _duplicate_users_route() -> dict[str, str]:
        return {"status": "duplicate"}

    target_app.add_api_route(
        path,
        _duplicate_users_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different users handler",
    ):
        app_main._include_users_router_if_needed(target_app)


def test_users_registration_rejects_foreign_handlers() -> None:
    target_app = FastAPI()

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:

        async def _foreign_users_route(current_route_path: str = path) -> dict[str, str]:
            return {"path": current_route_path}

        target_app.add_api_route(
            path,
            _foreign_users_route,
            methods=[method],
            include_in_schema=include_in_schema,
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different users handler",
    ):
        app_main._include_users_router_if_needed(target_app)


def test_users_registration_rejects_existing_wrong_method() -> None:
    target_app = FastAPI()

    async def _wrong_method_users_route() -> dict[str, str]:
        return {"status": "wrong-method"}

    target_app.add_api_route(
        "/api/v1/users/{user_id}",
        _wrong_method_users_route,
        methods=["POST"],
    )

    with pytest.raises(RuntimeError, match="Partial users route registration detected"):
        app_main._include_users_router_if_needed(target_app)


def test_users_registration_rejects_visibility_drift() -> None:
    target_app = FastAPI()
    app_main._include_users_router_if_needed(target_app)
    route = _users_route(target_app, "/api/v1/users", "GET")
    setattr(route, "include_in_schema", True)

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve users OpenAPI visibility",
    ):
        app_main._include_users_router_if_needed(target_app)


@pytest.mark.parametrize("missing_key", sorted(_EXPECTED_ROUTE_KEYS))
def test_users_registration_rejects_missing_required_dependency(
    missing_key: tuple[str, str],
) -> None:
    target_app = FastAPI()

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        source_route = _source_route(path, method)
        source_endpoint = source_route.endpoint
        endpoint = (
            _clone_endpoint_with_matching_identity(source_endpoint, None)
            if (path, method) == missing_key
            else source_endpoint
        )
        dependencies = (
            [] if (path, method) == missing_key else [Depends(app_main._require_users_api_key)]
        )
        target_app.add_api_route(
            path,
            endpoint,
            methods=[method],
            include_in_schema=include_in_schema,
            responses=dict(source_route.responses),
            dependencies=dependencies,
        )

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve users required dependency",
    ):
        app_main._include_users_router_if_needed(target_app)


def test_users_registration_rejects_route_order_drift() -> None:
    target_app = FastAPI()
    drifted_order = (
        ("/api/v1/users", "GET", False),
        ("/api/v1/users", "POST", False),
        ("/api/v1/users/{user_id}", "GET", False),
        ("/api/v1/users/{user_id}", "DELETE", False),
    )

    for path, method, include_in_schema in drifted_order:
        source = _source_route(path, method)
        target_app.add_api_route(
            path,
            route_endpoint(source),
            methods=[method],
            include_in_schema=include_in_schema,
            responses=source.responses,
            dependencies=[Depends(app_main._require_users_api_key)],
        )

    with pytest.raises(
        RuntimeError,
        match="Existing users route order does not preserve source route order",
    ):
        app_main._include_users_router_if_needed(target_app)
