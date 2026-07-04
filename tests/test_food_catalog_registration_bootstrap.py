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
    route_responses,
)

_EXPECTED_ROUTE_SPECS = (
    *app_main._FOODS_ROUTE_SPECS,
    *app_main._CATALOG_ROUTE_SPECS,
)
_EXPECTED_ROUTE_KEYS = {
    (path, method) for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS
}
_EXPECTED_ROUTE_PATHS = {path for path, _method in _EXPECTED_ROUTE_KEYS}
_FOODS_ROUTE_KEYS = {
    (path, method) for path, method, _include_in_schema in app_main._FOODS_ROUTE_SPECS
}
_CATALOG_ROUTE_KEYS = {
    (path, method) for path, method, _include_in_schema in app_main._CATALOG_ROUTE_SPECS
}
_BARCODE_ROUTE_KEY = ("/api/v1/foods/barcode/{barcode}", "GET")
_EXPECTED_DEPENDENCIES: dict[tuple[str, str], Callable[..., object]] = {
    **{key: app_main.get_food_store for key in _FOODS_ROUTE_KEYS},
    **{key: app_main.get_catalog_service for key in _CATALOG_ROUTE_KEYS},
}
_EXPECTED_ENDPOINT_MODULES = {
    ("/api/v1/foods", "GET"): "app.routers.foods",
    ("/api/v1/foods/search", "GET"): "app.routers.foods",
    ("/api/v1/foods/{food_id}", "GET"): "app.routers.foods",
    ("/api/v1/foods/barcode/{barcode}", "GET"): "app.routers.foods",
    ("/api/v1/catalog/regions", "GET"): "app.routers.catalog",
    ("/api/v1/catalog/stores", "GET"): "app.routers.catalog",
    ("/api/v1/catalog/search", "GET"): "app.routers.catalog",
}


def _food_catalog_routes(target_app: FastAPI) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if is_api_route_candidate(route) and route_path(route) in _EXPECTED_ROUTE_PATHS
    ]


def _registered_route_counts(target_app: FastAPI) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for route in _food_catalog_routes(target_app):
        for method in route_methods(route):
            key = (route_path(route), method)
            if key in _EXPECTED_ROUTE_KEYS:
                counts[key] += 1
    return counts


def _food_catalog_route(target_app: FastAPI, path: str, method: str) -> object:
    matches = [
        route
        for route in _food_catalog_routes(target_app)
        if route_path(route) == path and method in route_methods(route)
    ]
    route_summaries = [
        f"{route_path(route)}:{sorted(route_methods(route))}:{route_endpoint(route).__module__}"
        for route in matches
    ]
    assert len(matches) == 1, (
        f"expected exactly one food/catalog route for {method} {path}; "
        f"found {len(matches)}: {route_summaries}"
    )
    return matches[0]


def _source_route(path: str, method: str) -> APIRoute:
    for router in (app_main.foods_router, app_main.catalog_router):
        for route in router.routes:
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


def _assert_food_catalog_routes_registered_once(target_app: FastAPI) -> None:
    counts = _registered_route_counts(target_app)
    assert set(counts) == _EXPECTED_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _food_catalog_route(target_app, path, method)
        assert route_include_in_schema(route) is include_in_schema
        endpoint = route_endpoint(route)
        assert getattr(endpoint, "__module__", None) == _EXPECTED_ENDPOINT_MODULES[(path, method)]
        assert route_has_dependency_call(route, _EXPECTED_DEPENDENCIES[(path, method)])

    barcode_route = _food_catalog_route(target_app, *_BARCODE_ROUTE_KEY)
    assert {404, 422}.issubset(route_responses(barcode_route))


def test_empty_app_registers_all_food_catalog_routes_once() -> None:
    target_app = FastAPI()

    app_main._include_food_catalog_routers_if_needed(target_app)

    _assert_food_catalog_routes_registered_once(target_app)


def test_bootstrapped_app_registers_all_food_catalog_routes_once() -> None:
    _assert_food_catalog_routes_registered_once(app_main.app)


def test_food_catalog_registration_is_idempotent() -> None:
    target_app = FastAPI()

    app_main._include_food_catalog_routers_if_needed(target_app)
    app_main._include_food_catalog_routers_if_needed(target_app)

    _assert_food_catalog_routes_registered_once(target_app)


def test_food_catalog_members_assert_dependency_and_status_contracts() -> None:
    members = {
        (member.path, member.method): member for member in app_main._food_catalog_route_members()
    }

    assert set(members) == _EXPECTED_ROUTE_KEYS
    for key in _FOODS_ROUTE_KEYS:
        assert members[key].required_dependencies == (app_main.get_food_store,)
    for key in _CATALOG_ROUTE_KEYS:
        assert members[key].required_dependencies == (app_main.get_catalog_service,)
    assert members[_BARCODE_ROUTE_KEY].required_status_codes == frozenset({404, 422})


def test_food_catalog_source_routers_keep_dependency_contracts() -> None:
    for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _source_route(path, method)

        assert route_has_dependency_call(route, _EXPECTED_DEPENDENCIES[(path, method)])


def test_food_catalog_router_source_specs_match_current_visibility() -> None:
    route_specs: set[tuple[str, str, bool]] = set()
    for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _source_route(path, method)
        route_specs.add((str(route.path), method, route.include_in_schema))

    assert route_specs == set(_EXPECTED_ROUTE_SPECS)


def test_food_catalog_public_openapi_paths_remain_hidden() -> None:
    schema = app_main.app.openapi()
    paths = {str(path) for path in schema.get("paths", {})}

    leaked_paths = sorted(
        path for path in paths if path.startswith(("/api/v1/foods", "/api/v1/catalog"))
    )
    assert leaked_paths == []


def test_food_catalog_registration_rejects_partial_existing_family() -> None:
    target_app = FastAPI()
    path, method, include_in_schema = _EXPECTED_ROUTE_SPECS[0]

    async def _partial_food_catalog_route() -> dict[str, str]:
        return {"status": "partial"}

    target_app.add_api_route(
        path,
        _partial_food_catalog_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(RuntimeError, match="Partial food catalog route registration detected"):
        app_main._include_food_catalog_routers_if_needed(target_app)


def test_food_catalog_registration_rejects_duplicate_method_path() -> None:
    target_app = FastAPI()
    app_main._include_food_catalog_routers_if_needed(target_app)
    path, method, include_in_schema = _EXPECTED_ROUTE_SPECS[0]

    async def _duplicate_food_catalog_route() -> dict[str, str]:
        return {"status": "duplicate"}

    target_app.add_api_route(
        path,
        _duplicate_food_catalog_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different food catalog handler",
    ):
        app_main._include_food_catalog_routers_if_needed(target_app)


def test_food_catalog_registration_rejects_foreign_handlers() -> None:
    target_app = FastAPI()

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:

        async def _foreign_food_catalog_route(
            current_route_path: str = path,
        ) -> dict[str, str]:
            return {"path": current_route_path}

        target_app.add_api_route(
            path,
            _foreign_food_catalog_route,
            methods=[method],
            include_in_schema=include_in_schema,
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different food catalog handler",
    ):
        app_main._include_food_catalog_routers_if_needed(target_app)


def test_food_catalog_registration_rejects_existing_wrong_method() -> None:
    target_app = FastAPI()

    async def _wrong_method_food_catalog_route() -> dict[str, str]:
        return {"status": "wrong-method"}

    target_app.add_api_route(
        "/api/v1/foods",
        _wrong_method_food_catalog_route,
        methods=["POST"],
    )

    with pytest.raises(RuntimeError, match="Partial food catalog route registration detected"):
        app_main._include_food_catalog_routers_if_needed(target_app)


def test_food_catalog_registration_rejects_visibility_drift() -> None:
    target_app = FastAPI()
    app_main._include_food_catalog_routers_if_needed(target_app)
    route = _food_catalog_route(target_app, "/api/v1/foods", "GET")
    setattr(route, "include_in_schema", True)

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve food catalog OpenAPI visibility",
    ):
        app_main._include_food_catalog_routers_if_needed(target_app)


def test_food_catalog_registration_rejects_response_metadata_drift() -> None:
    target_app = FastAPI()

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        source_endpoint = _source_route(path, method).endpoint
        route_kwargs: dict[str, object] = {}
        if (path, method) != _BARCODE_ROUTE_KEY:
            route_kwargs["responses"] = dict(_source_route(path, method).responses)
        target_app.add_api_route(
            path,
            source_endpoint,
            methods=[method],
            include_in_schema=include_in_schema,
            dependencies=[Depends(_EXPECTED_DEPENDENCIES[(path, method)])],
            **route_kwargs,
        )

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve (404|422) response metadata",
    ):
        app_main._include_food_catalog_routers_if_needed(target_app)


@pytest.mark.parametrize("missing_key", sorted(_EXPECTED_ROUTE_KEYS))
def test_food_catalog_registration_rejects_missing_required_dependency(
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
            []
            if (path, method) == missing_key
            else [Depends(_EXPECTED_DEPENDENCIES[(path, method)])]
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
        match="Existing .* route does not preserve food catalog required dependency",
    ):
        app_main._include_food_catalog_routers_if_needed(target_app)
