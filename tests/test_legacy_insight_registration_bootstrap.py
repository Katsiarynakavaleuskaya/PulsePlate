from __future__ import annotations

from collections import Counter
from collections.abc import Callable

import pytest
from fastapi import Depends, FastAPI

import app.main as app_main
import legacy_app
from app.bootstrap.route_family import route_has_dependency_call
from app.effective_routes import (
    is_api_route_candidate,
    route_endpoint,
    route_include_in_schema,
    route_methods,
    route_path,
    route_responses,
)
from app.middleware.api_tiers import require_vip_tier
from tests.helpers.route_lookup import (
    all_api_paths,
    family_routes,
    find_single_route,
    registered_route_counts,
)

_EXPECTED_ROUTE_SPECS = app_main._LEGACY_INSIGHT_ROUTE_SPECS
_EXPECTED_ROUTE_KEYS = {
    (path, method) for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS
}
_EXPECTED_ROUTE_PATHS = {path for path, _method in _EXPECTED_ROUTE_KEYS}
_EXPECTED_ENDPOINT_MODULE = "app.routers.legacy_insight"
_EXPECTED_ENDPOINTS = {
    ("/api/v1/insight", "POST"): "insight_v1_route",
    ("/insight", "POST"): "insight_route",
}
_EXPECTED_DEPRECATED = {
    ("/api/v1/insight", "POST"): False,
    ("/insight", "POST"): True,
}
_INSIGHT_V1_PATH = "/api/v1/insight"
_INSIGHT_LEGACY_PATH = "/insight"
_INSIGHT_METHOD = "POST"


def _assert_same_response_model(actual: object, expected: object) -> None:
    assert getattr(actual, "__module__", None) == getattr(expected, "__module__", None)
    assert getattr(actual, "__qualname__", None) == getattr(expected, "__qualname__", None)


def _all_api_paths(target_app: FastAPI) -> set[str]:
    return all_api_paths(target_app)


def _insight_routes(target_app: FastAPI) -> list[object]:
    return family_routes(target_app, _EXPECTED_ROUTE_PATHS)


def _registered_route_counts(target_app: FastAPI) -> Counter[tuple[str, str]]:
    return registered_route_counts(target_app, _EXPECTED_ROUTE_KEYS)


def _insight_route(target_app: FastAPI, path: str, method: str) -> object:
    return find_single_route(target_app, path, method, family_label="legacy insight")


def _source_route(path: str, method: str) -> object:
    for route in app_main.legacy_insight_router.routes:
        if not is_api_route_candidate(route):
            continue
        if route_path(route) == path and method in route_methods(route):
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


def _assert_insight_routes_registered_once(target_app: FastAPI) -> None:
    counts = _registered_route_counts(target_app)
    assert set(counts) == _EXPECTED_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())

    present_order: list[tuple[str, str]] = []
    for route in _insight_routes(target_app):
        for method in sorted(route_methods(route)):
            key = (route_path(route), method)
            if key in _EXPECTED_ROUTE_KEYS:
                present_order.append(key)
    assert tuple(present_order) == tuple(
        (path, method) for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS
    )

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _insight_route(target_app, path, method)
        key = (path, method)
        assert route_include_in_schema(route) is include_in_schema
        endpoint = route_endpoint(route)
        assert getattr(endpoint, "__module__", None) == _EXPECTED_ENDPOINT_MODULE
        assert getattr(endpoint, "__name__", None) == _EXPECTED_ENDPOINTS[key]
        _assert_same_response_model(route.response_model, legacy_app.InsightResponse)
        assert bool(getattr(route, "deprecated", False)) is _EXPECTED_DEPRECATED[key]
        assert 429 in route_responses(route)
        assert route_has_dependency_call(route, require_vip_tier)


def test_empty_app_registers_legacy_insight_routes_once() -> None:
    target_app = FastAPI()

    app_main._include_legacy_insight_router_if_needed(target_app)

    _assert_insight_routes_registered_once(target_app)


def test_bootstrapped_app_registers_legacy_insight_routes_once() -> None:
    _assert_insight_routes_registered_once(app_main.app)


def test_legacy_insight_registration_is_idempotent() -> None:
    target_app = FastAPI()

    app_main._include_legacy_insight_router_if_needed(target_app)
    app_main._include_legacy_insight_router_if_needed(target_app)

    _assert_insight_routes_registered_once(target_app)


def test_legacy_insight_route_members_encode_vip_tier_dependency() -> None:
    members = {
        (member.path, member.method): member for member in app_main._legacy_insight_route_members()
    }

    assert set(members) == _EXPECTED_ROUTE_KEYS
    for key in _EXPECTED_ROUTE_KEYS:
        assert members[key].required_dependencies == (require_vip_tier,)
        assert members[key].required_status_codes == frozenset({429})
        assert members[key].include_in_schema is False


def test_legacy_insight_source_routes_preserve_metadata() -> None:
    for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _source_route(path, method)
        key = (path, method)

        assert route_include_in_schema(route) is False
        _assert_same_response_model(route.response_model, legacy_app.InsightResponse)
        assert bool(getattr(route, "deprecated", False)) is _EXPECTED_DEPRECATED[key]
        assert 429 in route_responses(route)
        assert route_has_dependency_call(route, require_vip_tier)


def test_legacy_insight_public_openapi_paths_remain_hidden() -> None:
    schema = app_main.app.openapi()
    paths = {str(path) for path in schema.get("paths", {})}

    assert _INSIGHT_V1_PATH not in paths
    assert _INSIGHT_LEGACY_PATH not in paths


def test_legacy_insight_registration_does_not_absorb_other_insight_routes() -> None:
    target_app = FastAPI()

    app_main._include_legacy_insight_router_if_needed(target_app)

    registered_paths = _all_api_paths(target_app)
    assert _INSIGHT_V1_PATH in registered_paths
    assert _INSIGHT_LEGACY_PATH in registered_paths
    assert "/api/v1/insight/fitchef" not in registered_paths
    assert "/api/v1/vip/fitchef/insight" not in registered_paths
    assert "/api/v1/pro/cbt/insight" not in registered_paths


def test_legacy_insight_registration_rejects_partial_existing_family() -> None:
    target_app = FastAPI()

    async def _partial_insight_route() -> dict[str, str]:
        return {"status": "partial"}

    target_app.add_api_route(
        _INSIGHT_V1_PATH,
        _partial_insight_route,
        methods=["GET"],
        include_in_schema=False,
    )

    with pytest.raises(
        RuntimeError,
        match="Partial legacy insight route registration detected",
    ):
        app_main._include_legacy_insight_router_if_needed(target_app)


def test_legacy_insight_registration_rejects_duplicate_method_path() -> None:
    target_app = FastAPI()
    app_main._include_legacy_insight_router_if_needed(target_app)

    async def _duplicate_insight_route() -> dict[str, str]:
        return {"status": "duplicate"}

    target_app.add_api_route(
        _INSIGHT_V1_PATH,
        _duplicate_insight_route,
        methods=[_INSIGHT_METHOD],
        include_in_schema=False,
    )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different legacy insight handler",
    ):
        app_main._include_legacy_insight_router_if_needed(target_app)


def test_legacy_insight_registration_rejects_foreign_handler() -> None:
    target_app = FastAPI()

    async def _foreign_insight_route() -> dict[str, str]:
        return {"status": "foreign"}

    target_app.add_api_route(
        _INSIGHT_LEGACY_PATH,
        _foreign_insight_route,
        methods=[_INSIGHT_METHOD],
        include_in_schema=False,
    )

    with pytest.raises(
        RuntimeError,
        match="Partial legacy insight route registration detected",
    ):
        app_main._include_legacy_insight_router_if_needed(target_app)


def test_legacy_insight_registration_rejects_openapi_visibility_drift() -> None:
    target_app = FastAPI()
    for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS:
        source = _source_route(path, method)
        endpoint = _clone_endpoint_with_matching_identity(
            route_endpoint(source),
            require_vip_tier,
        )
        target_app.add_api_route(
            path,
            endpoint,
            methods=[method],
            include_in_schema=True,
            responses={429: {"description": "Rate limit exceeded"}},
            dependencies=[Depends(require_vip_tier)],
        )

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve legacy insight OpenAPI visibility",
    ):
        app_main._include_legacy_insight_router_if_needed(target_app)


def test_legacy_insight_registration_rejects_missing_vip_tier_dependency() -> None:
    target_app = FastAPI()
    for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS:
        source = _source_route(path, method)
        endpoint = _clone_endpoint_with_matching_identity(route_endpoint(source), None)
        target_app.add_api_route(
            path,
            endpoint,
            methods=[method],
            include_in_schema=False,
            responses={429: {"description": "Rate limit exceeded"}},
        )

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve legacy insight required dependency",
    ):
        app_main._include_legacy_insight_router_if_needed(target_app)


def test_legacy_insight_registration_accepts_reloaded_canonical_handlers() -> None:
    target_app = FastAPI()
    for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS:
        source = _source_route(path, method)
        endpoint = _clone_endpoint_with_matching_identity(
            route_endpoint(source),
            require_vip_tier,
        )
        target_app.add_api_route(
            path,
            endpoint,
            methods=[method],
            response_model=legacy_app.InsightResponse,
            include_in_schema=False,
            deprecated=_EXPECTED_DEPRECATED[(path, method)],
            responses={429: {"description": "Rate limit exceeded"}},
            dependencies=[Depends(require_vip_tier)],
        )

    app_main._include_legacy_insight_router_if_needed(target_app)

    _assert_insight_routes_registered_once(target_app)
