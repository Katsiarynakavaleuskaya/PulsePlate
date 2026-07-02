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
from app.metrics import LEGACY_NUTRITION_DATE_ROUTE_TEMPLATE

_EXPECTED_ROUTE_SPECS = (
    *app_main._BAYES_ADHERENCE_ROUTE_SPECS,
    *app_main._NUTRITION_LOG_ROUTE_SPECS,
    *app_main._LEGACY_NUTRITION_ALIAS_ROUTE_SPECS,
)
_EXPECTED_ROUTE_KEYS = {
    (path, method) for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS
}
_EXPECTED_ROUTE_PATHS = {path for path, _method in _EXPECTED_ROUTE_KEYS}
_STATEFUL_ROUTE_KEYS = {
    (path, method)
    for path, method, _include_in_schema in (
        *app_main._BAYES_ADHERENCE_ROUTE_SPECS,
        *app_main._NUTRITION_LOG_ROUTE_SPECS,
    )
}
_ALIAS_ROUTE_KEY = (LEGACY_NUTRITION_DATE_ROUTE_TEMPLATE, "GET")
_EXPECTED_DEPENDENCIES: dict[tuple[str, str], tuple[Callable[..., object], ...]] = {
    key: (app_main.require_pro_tier, app_main.get_current_user) for key in _STATEFUL_ROUTE_KEYS
}
_EXPECTED_DEPENDENCIES[_ALIAS_ROUTE_KEY] = (app_main.require_pro_tier,)
_EXPECTED_ENDPOINT_MODULES = {
    ("/api/v1/bayes/adherence/event", "POST"): "app.routers.bayes_adherence",
    ("/api/v1/bayes/adherence/risk", "GET"): "app.routers.bayes_adherence",
    ("/api/v1/pro/nutrition/meal-log", "POST"): "app.routers.nutrition_log",
    ("/api/v1/pro/nutrition/day-close", "POST"): "app.routers.nutrition_log",
    _ALIAS_ROUTE_KEY: "app.routers.legacy_nutrition_alias",
}


def _nutrition_state_routes(target_app: FastAPI) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if is_api_route_candidate(route) and route_path(route) in _EXPECTED_ROUTE_PATHS
    ]


def _registered_route_counts(target_app: FastAPI) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for route in _nutrition_state_routes(target_app):
        for method in route_methods(route):
            key = (route_path(route), method)
            if key in _EXPECTED_ROUTE_KEYS:
                counts[key] += 1
    return counts


def _nutrition_state_route(target_app: FastAPI, path: str, method: str) -> object:
    matches = [
        route
        for route in _nutrition_state_routes(target_app)
        if route_path(route) == path and method in route_methods(route)
    ]
    assert len(matches) == 1
    return matches[0]


def _source_route(path: str, method: str) -> APIRoute:
    for router in (
        app_main.bayes_adherence_router,
        app_main.nutrition_log_router,
        app_main.legacy_nutrition_alias_router,
    ):
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            if str(route.path) == path and method in (route.methods or set()):
                return route
    raise AssertionError(f"missing source route: {method} {path}")


def _router_has_top_level_dependency(router: object, dependency: object) -> bool:
    return any(
        getattr(depends_param, "dependency", None) is dependency
        for depends_param in getattr(router, "dependencies", ())
    )


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
            _subject: object = Depends(dependency),
        ) -> dict[str, str]:
            return {"status": "stub"}

        endpoint = _endpoint_with_dependency

    endpoint.__module__ = source_endpoint.__module__
    endpoint.__qualname__ = source_endpoint.__qualname__
    return endpoint


def _assert_nutrition_state_routes_registered_once(target_app: FastAPI) -> None:
    counts = _registered_route_counts(target_app)
    assert set(counts) == _EXPECTED_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _nutrition_state_route(target_app, path, method)
        assert route_include_in_schema(route) is include_in_schema
        endpoint = route_endpoint(route)
        assert getattr(endpoint, "__module__", None) == _EXPECTED_ENDPOINT_MODULES[(path, method)]
        for dependency in _EXPECTED_DEPENDENCIES[(path, method)]:
            assert route_has_dependency_call(route, dependency)

    alias_route = _nutrition_state_route(target_app, *_ALIAS_ROUTE_KEY)
    assert getattr(alias_route, "deprecated", False) is True


def test_empty_app_registers_all_nutrition_state_routes_once() -> None:
    target_app = FastAPI()

    app_main._include_nutrition_state_routers_if_needed(target_app)

    _assert_nutrition_state_routes_registered_once(target_app)


def test_nutrition_state_registration_is_idempotent() -> None:
    target_app = FastAPI()

    app_main._include_nutrition_state_routers_if_needed(target_app)
    app_main._include_nutrition_state_routers_if_needed(target_app)

    _assert_nutrition_state_routes_registered_once(target_app)


def test_nutrition_state_members_assert_tier_and_subject_dependencies() -> None:
    members = {
        (member.path, member.method): member for member in app_main._nutrition_state_route_members()
    }

    assert set(members) == _EXPECTED_ROUTE_KEYS
    for key in _STATEFUL_ROUTE_KEYS:
        assert members[key].required_dependencies == (
            app_main.require_pro_tier,
            app_main.get_current_user,
        )
    assert members[_ALIAS_ROUTE_KEY].required_dependencies == (app_main.require_pro_tier,)


def test_nutrition_state_source_routers_keep_router_level_tier_guard() -> None:
    assert _router_has_top_level_dependency(
        app_main.bayes_adherence_router,
        app_main.require_pro_tier,
    )
    assert _router_has_top_level_dependency(
        app_main.nutrition_log_router,
        app_main.require_pro_tier,
    )


def test_nutrition_state_router_source_specs_match_current_visibility() -> None:
    route_specs: set[tuple[str, str, bool]] = set()
    for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _source_route(path, method)
        route_specs.add((str(route.path), method, route.include_in_schema))

    assert route_specs == set(_EXPECTED_ROUTE_SPECS)


def test_nutrition_state_registration_rejects_partial_existing_family() -> None:
    target_app = FastAPI()
    path, method, include_in_schema = _EXPECTED_ROUTE_SPECS[0]

    async def _partial_nutrition_state_route() -> dict[str, str]:
        return {"status": "partial"}

    target_app.add_api_route(
        path,
        _partial_nutrition_state_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(RuntimeError, match="Partial nutrition state route registration detected"):
        app_main._include_nutrition_state_routers_if_needed(target_app)


def test_nutrition_state_registration_rejects_duplicate_method_path() -> None:
    target_app = FastAPI()
    app_main._include_nutrition_state_routers_if_needed(target_app)
    path, method, include_in_schema = _EXPECTED_ROUTE_SPECS[0]

    async def _duplicate_nutrition_state_route() -> dict[str, str]:
        return {"status": "duplicate"}

    target_app.add_api_route(
        path,
        _duplicate_nutrition_state_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different nutrition state handler",
    ):
        app_main._include_nutrition_state_routers_if_needed(target_app)


def test_nutrition_state_registration_rejects_foreign_handlers() -> None:
    target_app = FastAPI()

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:

        async def _foreign_nutrition_state_route(
            current_route_path: str = path,
        ) -> dict[str, str]:
            return {"path": current_route_path}

        target_app.add_api_route(
            path,
            _foreign_nutrition_state_route,
            methods=[method],
            include_in_schema=include_in_schema,
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different nutrition state handler",
    ):
        app_main._include_nutrition_state_routers_if_needed(target_app)


def test_nutrition_state_registration_rejects_existing_wrong_method() -> None:
    target_app = FastAPI()

    async def _wrong_method_nutrition_state_route() -> dict[str, str]:
        return {"status": "wrong-method"}

    target_app.add_api_route(
        "/api/v1/bayes/adherence/event",
        _wrong_method_nutrition_state_route,
        methods=["PUT"],
    )

    with pytest.raises(RuntimeError, match="Partial nutrition state route registration detected"):
        app_main._include_nutrition_state_routers_if_needed(target_app)


def test_nutrition_state_registration_rejects_visibility_drift() -> None:
    target_app = FastAPI()
    app_main._include_nutrition_state_routers_if_needed(target_app)
    alias_route = _nutrition_state_route(target_app, *_ALIAS_ROUTE_KEY)
    setattr(alias_route, "include_in_schema", True)

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve nutrition state OpenAPI visibility",
    ):
        app_main._include_nutrition_state_routers_if_needed(target_app)


def test_nutrition_state_registration_rejects_missing_require_pro_tier() -> None:
    target_app = FastAPI()

    async def _get_current_user_without_tier() -> object:
        return object()

    _get_current_user_without_tier.__module__ = app_main.get_current_user.__module__
    _get_current_user_without_tier.__qualname__ = app_main.get_current_user.__qualname__

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        source_endpoint = _source_route(path, method).endpoint
        endpoint = (
            _clone_endpoint_with_matching_identity(
                source_endpoint,
                _get_current_user_without_tier,
            )
            if (path, method) in _STATEFUL_ROUTE_KEYS
            else source_endpoint
        )
        target_app.add_api_route(
            path,
            endpoint,
            methods=[method],
            include_in_schema=include_in_schema,
        )

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve nutrition state required dependency",
    ):
        app_main._include_nutrition_state_routers_if_needed(target_app)


def test_nutrition_state_registration_rejects_missing_get_current_user() -> None:
    target_app = FastAPI()
    state_path, state_method = "/api/v1/bayes/adherence/event", "POST"
    source_endpoint = _source_route(state_path, state_method).endpoint

    async def _record_event_without_subject_dependency() -> dict[str, str]:
        return {"status": "missing-subject"}

    _record_event_without_subject_dependency.__module__ = source_endpoint.__module__
    _record_event_without_subject_dependency.__qualname__ = source_endpoint.__qualname__

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        endpoint = (
            _record_event_without_subject_dependency
            if (path, method) == (state_path, state_method)
            else _source_route(path, method).endpoint
        )
        dependencies = (
            [Depends(app_main.require_pro_tier)]
            if (path, method) == (state_path, state_method)
            else []
        )
        target_app.add_api_route(
            path,
            endpoint,
            methods=[method],
            include_in_schema=include_in_schema,
            dependencies=dependencies,
        )

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve nutrition state required dependency",
    ):
        app_main._include_nutrition_state_routers_if_needed(target_app)
