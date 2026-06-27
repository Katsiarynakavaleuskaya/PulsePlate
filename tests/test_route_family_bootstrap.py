from __future__ import annotations

from collections.abc import Sequence

import pytest
from fastapi import APIRouter, Depends, FastAPI, WebSocket

from app.bootstrap.route_family import (
    RouteMemberContract,
    _family_routes,
    ensure_route_family_registered,
    route_member_contracts_from_router,
    route_has_dependency_call,
    same_callable_by_module_and_qualname,
)


async def _api_key_dependency() -> str:
    return "ok"


async def _member_dependency() -> None:
    return None


_MEMBERS = (
    RouteMemberContract(
        path="/api/v1/static-family/a",
        method="GET",
        include_in_schema=True,
        required_status_codes=frozenset({429}),
        required_dependencies=(_api_key_dependency,),
    ),
    RouteMemberContract(
        path="/api/v1/static-family/b",
        method="POST",
        include_in_schema=False,
        required_status_codes=frozenset({429}),
        required_dependencies=(_api_key_dependency, _member_dependency),
    ),
)


def _family_routers(
    *,
    omit: frozenset[str] | None = None,
    method_overrides: dict[str, str] | None = None,
    include_overrides: dict[str, bool] | None = None,
    include_429: bool = True,
    include_unexpected: bool = False,
    include_websocket: bool = False,
    combined_methods_path: str | None = None,
) -> tuple[APIRouter, APIRouter]:
    route_a = APIRouter()
    route_b = APIRouter()
    routers = {
        "/api/v1/static-family/a": route_a,
        "/api/v1/static-family/b": route_b,
    }
    method_override_map = method_overrides or {}
    include_override_map = include_overrides or {}
    omit_set = omit or frozenset()

    for member in _MEMBERS:
        if member.path in omit_set:
            continue

        async def _handler(path: str = member.path) -> dict[str, str]:
            return {"path": path}

        route_methods = [method_override_map.get(member.path, member.method)]
        if combined_methods_path == member.path:
            route_methods.append("DELETE")
        dependencies = [Depends(_member_dependency)] if member.path.endswith("/b") else []
        routers[member.path].add_api_route(
            member.path,
            _handler,
            methods=route_methods,
            include_in_schema=include_override_map.get(member.path, member.include_in_schema),
            responses={429: {"description": "rate limit"}} if include_429 else {},
            dependencies=dependencies,
        )

    if include_unexpected:

        async def _unexpected() -> dict[str, str]:
            return {"path": "unexpected"}

        route_a.get("/api/v1/static-family/unexpected")(_unexpected)

    if include_websocket:

        async def _websocket(websocket: WebSocket) -> None:
            await websocket.close()

        route_a.websocket("/api/v1/static-family/ws")(_websocket)

    return route_a, route_b


def _ensure(
    app: FastAPI,
    routers: Sequence[APIRouter],
) -> None:
    ensure_route_family_registered(
        app,
        family_name="Static family",
        routers=routers,
        members=_MEMBERS,
        registration_dependencies=(Depends(_api_key_dependency),),
    )


def _matching_routes(app: FastAPI, member: RouteMemberContract) -> list[object]:
    return [
        route
        for route in _family_routes(app, {member.path})
        if member.method in (getattr(route, "methods", None) or set())
    ]


def test_route_member_contract_defaults_are_immutable_empty_collections() -> None:
    member = RouteMemberContract(
        path="/api/v1/static-family/defaults",
        method="get",
        include_in_schema=True,
    )

    assert member.method == "GET"
    assert member.required_status_codes == frozenset()
    assert member.required_dependencies == ()


def test_static_route_family_rejects_duplicate_member_contracts() -> None:
    duplicate_members = (
        RouteMemberContract(
            path="/api/v1/static-family/a",
            method="GET",
            include_in_schema=True,
        ),
        RouteMemberContract(
            path="/api/v1/static-family/a",
            method="GET",
            include_in_schema=True,
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        ensure_route_family_registered(
            FastAPI(),
            family_name="Static family",
            routers=(),
            members=duplicate_members,
        )


def test_static_route_family_rejects_empty_member_contracts() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        ensure_route_family_registered(
            FastAPI(),
            family_name="Static family",
            routers=(),
            members=(),
        )


def test_static_route_family_rejects_non_http_source_routes() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        _ensure(FastAPI(), _family_routers(include_websocket=True))


def test_static_route_family_contract_builder_ignores_fastapi_included_router_marker() -> None:
    child_router = APIRouter()

    async def _child_handler() -> dict[str, str]:
        return {"status": "ok"}

    child_router.get("/api/v1/static-family/child")(_child_handler)
    parent_router = APIRouter()
    parent_router.include_router(child_router)

    assert any(type(route).__name__ == "_IncludedRouter" for route in parent_router.routes)

    assert route_member_contracts_from_router("Static family", parent_router) == (
        RouteMemberContract(
            path="/api/v1/static-family/child",
            method="GET",
            include_in_schema=True,
        ),
    )


def test_static_route_family_registration_is_idempotent() -> None:
    app = FastAPI()

    _ensure(app, _family_routers())
    _ensure(app, _family_routers())

    for member in _MEMBERS:
        routes = _matching_routes(app, member)
        assert len(routes) == 1
        route = routes[0]
        assert getattr(route, "include_in_schema", True) is member.include_in_schema
        assert 429 in (getattr(route, "responses", None) or {})
        assert route_has_dependency_call(route, _api_key_dependency)
        for dependency in member.required_dependencies:
            assert route_has_dependency_call(route, dependency)


def test_static_route_family_rejects_unexpected_source_route() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        _ensure(FastAPI(), _family_routers(include_unexpected=True))


def test_static_route_family_rejects_missing_source_member() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        _ensure(FastAPI(), _family_routers(omit=frozenset({"/api/v1/static-family/b"})))


def test_static_route_family_rejects_source_combined_methods() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        _ensure(
            FastAPI(),
            _family_routers(combined_methods_path="/api/v1/static-family/a"),
        )


def test_static_route_family_rejects_source_visibility_drift() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not preserve OpenAPI visibility",
    ):
        _ensure(
            FastAPI(),
            _family_routers(include_overrides={"/api/v1/static-family/a": False}),
        )


def test_static_route_family_rejects_source_429_drift() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not preserve 429 response metadata",
    ):
        _ensure(FastAPI(), _family_routers(include_429=False))


def test_static_route_family_rejects_partial_existing_family() -> None:
    app = FastAPI()
    route_a, _route_b = _family_routers()
    app.include_router(route_a, dependencies=[Depends(_api_key_dependency)])

    with pytest.raises(
        RuntimeError,
        match="Partial static family route registration detected",
    ):
        _ensure(app, _family_routers())


def test_static_route_family_rejects_existing_foreign_handlers() -> None:
    app = FastAPI()

    for member in _MEMBERS:

        async def _foreign_handler(path: str = member.path) -> dict[str, str]:
            return {"path": path}

        dependencies = [Depends(_api_key_dependency)]
        if member.path.endswith("/b"):
            dependencies.append(Depends(_member_dependency))
        app.add_api_route(
            member.path,
            _foreign_handler,
            methods=[member.method],
            include_in_schema=member.include_in_schema,
            responses={429: {"description": "rate limit"}},
            dependencies=dependencies,
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different static family handler",
    ):
        _ensure(app, _family_routers())


def test_static_route_family_rejects_existing_missing_required_dependency() -> None:
    app = FastAPI()
    route_a, route_b = _family_routers()
    app.include_router(route_a)
    app.include_router(route_b)

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve static family required dependency",
    ):
        _ensure(app, _family_routers())


def test_dependency_detection_walks_nested_dependencies() -> None:
    app = FastAPI()

    async def _outer_dependency(
        _guard: str = Depends(_api_key_dependency),
    ) -> None:
        return None

    async def _nested_probe() -> dict[str, str]:
        return {"status": "nested"}

    app.add_api_route(
        "/api/v1/static-family/nested",
        _nested_probe,
        methods=["GET"],
        dependencies=[Depends(_outer_dependency)],
    )
    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/static-family/nested"
    )

    assert route_has_dependency_call(route, _api_key_dependency)


def test_callable_matcher_uses_module_and_qualname_after_identity() -> None:
    async def _expected() -> None:
        return None

    async def _equivalent() -> None:
        return None

    _equivalent.__module__ = _expected.__module__
    _equivalent.__qualname__ = _expected.__qualname__

    assert same_callable_by_module_and_qualname(_expected, _expected)
    assert same_callable_by_module_and_qualname(_equivalent, _expected)
    assert not same_callable_by_module_and_qualname(None, _expected)
