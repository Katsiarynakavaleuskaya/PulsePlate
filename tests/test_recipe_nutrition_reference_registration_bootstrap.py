from __future__ import annotations

from collections import Counter
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
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
    route_responses,
)
from app.routers import recipes as recipes_module

_EXPECTED_ROUTE_SPECS = (
    *app_main._RECIPES_ROUTE_SPECS,
    *app_main._NUTRITION_RECOMMENDATIONS_ROUTE_SPECS,
)
_EXPECTED_ROUTE_KEYS = {
    (path, method) for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS
}
_EXPECTED_ROUTE_PATHS = {path for path, _method in _EXPECTED_ROUTE_KEYS}
_EXPECTED_ENDPOINTS = {
    ("/api/v1/recipes", "GET"): "list_recipes",
    ("/api/v1/recipes/search", "GET"): "list_recipes_search",
    ("/api/v1/recipes/{recipe_id}", "GET"): "get_recipe",
    ("/api/v1/recipes/preview", "POST"): "recipe_preview",
    ("/api/v1/nutrition/recommendations", "GET"): "get_recommendations",
}
_EXPECTED_ENDPOINT_MODULES = {
    ("/api/v1/recipes", "GET"): "app.routers.recipes",
    ("/api/v1/recipes/search", "GET"): "app.routers.recipes",
    ("/api/v1/recipes/{recipe_id}", "GET"): "app.routers.recipes",
    ("/api/v1/recipes/preview", "POST"): "app.routers.recipes",
    ("/api/v1/nutrition/recommendations", "GET"): ("app.routers.nutrition_recommendations"),
}
_FORBIDDEN_DEPENDENCIES = (
    app_main.require_app_api_key,
    app_main.require_pro_tier,
    app_main.get_current_user,
)


def _recipe_nutrition_reference_routes(target_app: FastAPI) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if is_api_route_candidate(route) and route_path(route) in _EXPECTED_ROUTE_PATHS
    ]


def _registered_route_counts(target_app: FastAPI) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for route in _recipe_nutrition_reference_routes(target_app):
        for method in route_methods(route):
            key = (route_path(route), method)
            if key in _EXPECTED_ROUTE_KEYS:
                counts[key] += 1
    return counts


def _recipe_nutrition_reference_route(target_app: FastAPI, path: str, method: str) -> object:
    matches = [
        route
        for route in _recipe_nutrition_reference_routes(target_app)
        if route_path(route) == path and method in route_methods(route)
    ]
    route_summaries = [
        f"{route_path(route)}:{sorted(route_methods(route))}:{route_endpoint(route).__module__}"
        for route in matches
    ]
    assert len(matches) == 1, (
        f"expected exactly one recipe/nutrition reference route for {method} {path}; "
        f"found {len(matches)}: {route_summaries}"
    )
    return matches[0]


def _source_route(path: str, method: str) -> APIRoute:
    for router in (app_main.recipes_router, app_main.nutrition_recommendations_router):
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            if str(route.path) == path and method in (route.methods or set()):
                return route
    raise AssertionError(f"missing source route: {method} {path}")


def _assert_recipe_nutrition_reference_routes_registered_once(target_app: FastAPI) -> None:
    counts = _registered_route_counts(target_app)
    assert set(counts) == _EXPECTED_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _recipe_nutrition_reference_route(target_app, path, method)
        assert route_include_in_schema(route) is include_in_schema
        assert route_responses(route) == _source_route(path, method).responses
        endpoint = route_endpoint(route)
        assert getattr(endpoint, "__module__", None) == _EXPECTED_ENDPOINT_MODULES[(path, method)]
        assert getattr(endpoint, "__name__", None) == _EXPECTED_ENDPOINTS[(path, method)]
        for dependency in _FORBIDDEN_DEPENDENCIES:
            assert not route_has_dependency_call(route, dependency)


def test_empty_app_registers_all_recipe_nutrition_reference_routes_once() -> None:
    target_app = FastAPI()

    app_main._include_recipe_nutrition_reference_routers_if_needed(target_app)

    _assert_recipe_nutrition_reference_routes_registered_once(target_app)


def test_bootstrapped_app_registers_all_recipe_nutrition_reference_routes_once() -> None:
    _assert_recipe_nutrition_reference_routes_registered_once(app_main.app)


def test_recipe_nutrition_reference_registration_is_idempotent() -> None:
    target_app = FastAPI()

    app_main._include_recipe_nutrition_reference_routers_if_needed(target_app)
    app_main._include_recipe_nutrition_reference_routers_if_needed(target_app)

    _assert_recipe_nutrition_reference_routes_registered_once(target_app)


def test_recipe_nutrition_reference_members_have_no_auth_or_status_contracts() -> None:
    members = {
        (member.path, member.method): member
        for member in app_main._recipe_nutrition_reference_route_members()
    }

    assert set(members) == _EXPECTED_ROUTE_KEYS
    for member in members.values():
        assert member.required_dependencies == ()
        assert member.required_status_codes == frozenset()


def test_recipe_nutrition_reference_router_source_specs_match_current_visibility() -> None:
    route_specs: set[tuple[str, str, bool]] = set()
    for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _source_route(path, method)
        route_specs.add((str(route.path), method, route.include_in_schema))

    assert route_specs == set(_EXPECTED_ROUTE_SPECS)


def test_recipe_nutrition_reference_public_openapi_paths_remain_hidden() -> None:
    schema = app_main.app.openapi()
    paths = {str(path) for path in schema.get("paths", {})}

    leaked_paths = sorted(
        path
        for path in paths
        if path.startswith(("/api/v1/recipes", "/api/v1/nutrition/recommendations"))
    )
    assert leaked_paths == []


def test_recipe_search_alias_remains_reachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        recipes_module.recipe_store,
        "search_recipes",
        lambda query, limit, offset: [],
    )

    response = TestClient(app_main.app).get(
        "/api/v1/recipes/search",
        params={"query": "salad", "limit": 1},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == []


def test_recipe_nutrition_reference_registration_rejects_route_order_drift() -> None:
    target_app = FastAPI()
    drifted_order = (
        ("/api/v1/recipes", "GET", True),
        ("/api/v1/recipes/{recipe_id}", "GET", True),
        ("/api/v1/recipes/search", "GET", True),
        ("/api/v1/recipes/preview", "POST", True),
        ("/api/v1/nutrition/recommendations", "GET", True),
    )

    for path, method, include_in_schema in drifted_order:
        source = _source_route(path, method)
        target_app.add_api_route(
            path,
            route_endpoint(source),
            methods=[method],
            include_in_schema=include_in_schema,
            responses=source.responses,
        )

    with pytest.raises(
        RuntimeError,
        match=(
            "Existing recipe nutrition reference route order does not preserve "
            "source route order"
        ),
    ):
        app_main._include_recipe_nutrition_reference_routers_if_needed(target_app)


def test_recipe_nutrition_reference_registration_rejects_partial_existing_family() -> None:
    target_app = FastAPI()
    path, method, include_in_schema = _EXPECTED_ROUTE_SPECS[0]

    async def _partial_recipe_nutrition_reference_route() -> dict[str, str]:
        return {"status": "partial"}

    target_app.add_api_route(
        path,
        _partial_recipe_nutrition_reference_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(
        RuntimeError,
        match="Partial recipe nutrition reference route registration detected",
    ):
        app_main._include_recipe_nutrition_reference_routers_if_needed(target_app)


def test_recipe_nutrition_reference_registration_rejects_duplicate_method_path() -> None:
    target_app = FastAPI()
    app_main._include_recipe_nutrition_reference_routers_if_needed(target_app)
    path, method, include_in_schema = _EXPECTED_ROUTE_SPECS[0]

    async def _duplicate_recipe_nutrition_reference_route() -> dict[str, str]:
        return {"status": "duplicate"}

    target_app.add_api_route(
        path,
        _duplicate_recipe_nutrition_reference_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different recipe nutrition reference handler",
    ):
        app_main._include_recipe_nutrition_reference_routers_if_needed(target_app)


def test_recipe_nutrition_reference_registration_rejects_foreign_handlers() -> None:
    target_app = FastAPI()

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:

        async def _foreign_recipe_nutrition_reference_route(
            current_route_path: str = path,
        ) -> dict[str, str]:
            return {"path": current_route_path}

        target_app.add_api_route(
            path,
            _foreign_recipe_nutrition_reference_route,
            methods=[method],
            include_in_schema=include_in_schema,
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different recipe nutrition reference handler",
    ):
        app_main._include_recipe_nutrition_reference_routers_if_needed(target_app)


def test_recipe_nutrition_reference_registration_rejects_existing_wrong_method() -> None:
    target_app = FastAPI()

    async def _wrong_method_recipe_nutrition_reference_route() -> dict[str, str]:
        return {"status": "wrong-method"}

    target_app.add_api_route(
        "/api/v1/recipes",
        _wrong_method_recipe_nutrition_reference_route,
        methods=["POST"],
    )

    with pytest.raises(
        RuntimeError,
        match="Partial recipe nutrition reference route registration detected",
    ):
        app_main._include_recipe_nutrition_reference_routers_if_needed(target_app)


def test_recipe_nutrition_reference_registration_rejects_visibility_drift() -> None:
    target_app = FastAPI()
    app_main._include_recipe_nutrition_reference_routers_if_needed(target_app)
    route = _recipe_nutrition_reference_route(target_app, "/api/v1/recipes", "GET")
    setattr(route, "include_in_schema", False)

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve recipe nutrition reference OpenAPI visibility",
    ):
        app_main._include_recipe_nutrition_reference_routers_if_needed(target_app)
