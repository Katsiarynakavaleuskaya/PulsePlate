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

_EXPECTED_ROUTE_SPECS = (
    *app_main._SHOPPING_LIST_PRO_ROUTE_SPECS,
    *app_main._SHOPLIST_DAY_ROUTE_SPECS,
)
_EXPECTED_ROUTE_KEYS = {
    (path, method) for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS
}
_EXPECTED_ROUTE_PATHS = {path for path, _method in _EXPECTED_ROUTE_KEYS}
_EXPECTED_ENDPOINT_MODULES = {
    ("/api/v1/pro/meal/shopping-list", "POST"): "app.routers.shopping_list_pro",
    ("/api/v1/pro/shoplist/day", "GET"): "app.routers.shoplist_day",
}


def _shopping_list_routes(target_app: FastAPI) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if is_api_route_candidate(route) and route_path(route) in _EXPECTED_ROUTE_PATHS
    ]


def _registered_route_counts(target_app: FastAPI) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for route in _shopping_list_routes(target_app):
        for method in route_methods(route):
            key = (route_path(route), method)
            if key in _EXPECTED_ROUTE_KEYS:
                counts[key] += 1
    return counts


def _shopping_list_route(target_app: FastAPI, path: str, method: str) -> object:
    matches = [
        route
        for route in _shopping_list_routes(target_app)
        if route_path(route) == path and method in route_methods(route)
    ]
    assert len(matches) == 1
    return matches[0]


def _source_route(path: str, method: str) -> APIRoute:
    for router in (app_main.shopping_list_pro_router, app_main.shoplist_day_router):
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            if str(route.path) == path and method in (route.methods or set()):
                return route
    raise AssertionError(f"missing source route: {method} {path}")


def _clone_endpoint_without_dependency(
    source_endpoint: Callable[..., object],
) -> Callable[..., object]:
    async def _endpoint_without_dependency() -> dict[str, str]:
        return {"status": "stub"}

    _endpoint_without_dependency.__module__ = source_endpoint.__module__
    _endpoint_without_dependency.__qualname__ = source_endpoint.__qualname__
    return _endpoint_without_dependency


def _assert_shopping_list_routes_registered_once(target_app: FastAPI) -> None:
    counts = _registered_route_counts(target_app)
    assert set(counts) == _EXPECTED_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _shopping_list_route(target_app, path, method)
        assert route_include_in_schema(route) is include_in_schema
        endpoint = route_endpoint(route)
        assert getattr(endpoint, "__module__", None) == _EXPECTED_ENDPOINT_MODULES[(path, method)]
        assert route_has_dependency_call(route, app_main.require_pro_tier)


def test_empty_app_registers_all_shopping_list_routes_once() -> None:
    target_app = FastAPI()

    app_main._include_shopping_list_routers_if_needed(target_app)

    _assert_shopping_list_routes_registered_once(target_app)


def test_bootstrapped_app_registers_all_shopping_list_routes_once() -> None:
    _assert_shopping_list_routes_registered_once(app_main.app)


def test_shopping_list_registration_is_idempotent() -> None:
    target_app = FastAPI()

    app_main._include_shopping_list_routers_if_needed(target_app)
    app_main._include_shopping_list_routers_if_needed(target_app)

    _assert_shopping_list_routes_registered_once(target_app)


def test_shopping_list_members_assert_tier_dependency() -> None:
    members = {
        (member.path, member.method): member for member in app_main._shopping_list_route_members()
    }

    assert set(members) == _EXPECTED_ROUTE_KEYS
    for member in members.values():
        assert member.required_dependencies == (app_main.require_pro_tier,)


def test_shopping_list_source_routers_keep_tier_guard() -> None:
    for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _source_route(path, method)

        assert route_has_dependency_call(route, app_main.require_pro_tier)


def test_shopping_list_router_source_specs_match_current_visibility() -> None:
    route_specs: set[tuple[str, str, bool]] = set()
    for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _source_route(path, method)
        route_specs.add((str(route.path), method, route.include_in_schema))

    assert route_specs == set(_EXPECTED_ROUTE_SPECS)


def test_shopping_list_registration_rejects_partial_existing_family() -> None:
    target_app = FastAPI()
    path, method, include_in_schema = _EXPECTED_ROUTE_SPECS[0]

    async def _partial_shopping_list_route() -> dict[str, str]:
        return {"status": "partial"}

    target_app.add_api_route(
        path,
        _partial_shopping_list_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(RuntimeError, match="Partial shopping list route registration detected"):
        app_main._include_shopping_list_routers_if_needed(target_app)


def test_shopping_list_registration_rejects_duplicate_method_path() -> None:
    target_app = FastAPI()
    app_main._include_shopping_list_routers_if_needed(target_app)
    path, method, include_in_schema = _EXPECTED_ROUTE_SPECS[0]

    async def _duplicate_shopping_list_route() -> dict[str, str]:
        return {"status": "duplicate"}

    target_app.add_api_route(
        path,
        _duplicate_shopping_list_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different shopping list handler",
    ):
        app_main._include_shopping_list_routers_if_needed(target_app)


def test_shopping_list_registration_rejects_foreign_handlers() -> None:
    target_app = FastAPI()

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:

        async def _foreign_shopping_list_route(
            current_route_path: str = path,
        ) -> dict[str, str]:
            return {"path": current_route_path}

        target_app.add_api_route(
            path,
            _foreign_shopping_list_route,
            methods=[method],
            include_in_schema=include_in_schema,
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different shopping list handler",
    ):
        app_main._include_shopping_list_routers_if_needed(target_app)


def test_shopping_list_registration_rejects_existing_wrong_method() -> None:
    target_app = FastAPI()

    async def _wrong_method_shopping_list_route() -> dict[str, str]:
        return {"status": "wrong-method"}

    target_app.add_api_route(
        "/api/v1/pro/meal/shopping-list",
        _wrong_method_shopping_list_route,
        methods=["PUT"],
    )

    with pytest.raises(RuntimeError, match="Partial shopping list route registration detected"):
        app_main._include_shopping_list_routers_if_needed(target_app)


def test_shopping_list_registration_rejects_visibility_drift() -> None:
    target_app = FastAPI()
    app_main._include_shopping_list_routers_if_needed(target_app)
    path, method, _include_in_schema = _EXPECTED_ROUTE_SPECS[0]
    route = _shopping_list_route(target_app, path, method)
    setattr(route, "include_in_schema", False)

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve shopping list OpenAPI visibility",
    ):
        app_main._include_shopping_list_routers_if_needed(target_app)


@pytest.mark.parametrize("missing_key", sorted(_EXPECTED_ROUTE_KEYS))
def test_shopping_list_registration_rejects_missing_require_pro_tier(
    missing_key: tuple[str, str],
) -> None:
    target_app = FastAPI()

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        source_endpoint = _source_route(path, method).endpoint
        endpoint = (
            _clone_endpoint_without_dependency(source_endpoint)
            if (path, method) == missing_key
            else source_endpoint
        )
        dependencies = [] if (path, method) == missing_key else [Depends(app_main.require_pro_tier)]
        target_app.add_api_route(
            path,
            endpoint,
            methods=[method],
            include_in_schema=include_in_schema,
            dependencies=dependencies,
        )

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve shopping list required dependency",
    ):
        app_main._include_shopping_list_routers_if_needed(target_app)
