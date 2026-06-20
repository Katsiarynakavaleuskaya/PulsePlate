"""Shared FastAPI bootstrap guards for exact static route families."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

from fastapi import APIRouter, FastAPI
from fastapi.params import Depends as DependsParam
from fastapi.routing import APIRoute

EndpointMatcher = Callable[[object, object], bool]
RouteKey = tuple[str, str]

_FRAMEWORK_METHODS = frozenset({"HEAD", "OPTIONS"})


def _empty_status_codes() -> frozenset[int]:
    return frozenset()


def _empty_dependencies() -> tuple[Callable[..., object], ...]:
    return ()


@dataclass(frozen=True, slots=True)
class RouteMemberContract:
    """Contract for one static route-family member."""

    path: str
    method: str
    include_in_schema: bool
    required_status_codes: frozenset[int] = field(default_factory=_empty_status_codes)
    required_dependencies: tuple[Callable[..., object], ...] = field(
        default_factory=_empty_dependencies
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", self.method.upper())
        object.__setattr__(self, "required_status_codes", frozenset(self.required_status_codes))
        object.__setattr__(self, "required_dependencies", tuple(self.required_dependencies))


def same_callable_by_module_and_qualname(existing: object, expected: object) -> bool:
    """Match route/dependency callables across FastAPI route cloning."""

    if existing is expected:
        return True
    if not callable(existing) or not callable(expected):
        return False

    existing_module = getattr(existing, "__module__", None)
    expected_module = getattr(expected, "__module__", None)
    existing_qualname = getattr(existing, "__qualname__", None)
    expected_qualname = getattr(expected, "__qualname__", None)
    return bool(
        existing_module
        and expected_module
        and existing_qualname
        and expected_qualname
        and existing_module == expected_module
        and existing_qualname == expected_qualname
    )


def _iter_dependency_calls(dependencies: Iterable[object] | None) -> Iterable[object]:
    for dependency in dependencies if dependencies is not None else ():
        yield getattr(dependency, "call", None)
        yield from _iter_dependency_calls(getattr(dependency, "dependencies", None))


def route_has_dependency_call(
    route: object,
    expected: object,
    *,
    endpoint_matcher: EndpointMatcher = same_callable_by_module_and_qualname,
) -> bool:
    """Return whether a route has a matching dependency call at any depth."""

    dependant = getattr(route, "dependant", None)
    return any(
        endpoint_matcher(call, expected)
        for call in _iter_dependency_calls(getattr(dependant, "dependencies", None))
    )


def ensure_route_family_registered(
    target_app: FastAPI,
    *,
    family_name: str,
    routers: Sequence[APIRouter],
    members: Sequence[RouteMemberContract],
    registration_dependencies: Sequence[DependsParam] = (),
    endpoint_matcher: EndpointMatcher = same_callable_by_module_and_qualname,
) -> None:
    """Register and validate an exact static FastAPI route family."""

    members_by_key = _members_by_key(family_name, members)
    expected_paths = {member.path for member in members_by_key.values()}
    expected_methods_by_path = _expected_methods_by_path(members_by_key.values())
    source_endpoints = _source_endpoints(
        family_name=family_name,
        routers=routers,
        members_by_key=members_by_key,
        expected_paths=expected_paths,
        expected_methods_by_path=expected_methods_by_path,
    )

    family_routes = _family_routes(target_app, expected_paths)
    if not family_routes:
        dependencies = list(registration_dependencies)
        for router in routers:
            target_app.include_router(router, dependencies=dependencies)
        family_routes = _family_routes(target_app, expected_paths)

    _validate_existing_routes(
        family_name=family_name,
        family_routes=family_routes,
        members_by_key=members_by_key,
        expected_paths=expected_paths,
        expected_methods_by_path=expected_methods_by_path,
        source_endpoints=source_endpoints,
        endpoint_matcher=endpoint_matcher,
    )


def _members_by_key(
    family_name: str,
    members: Sequence[RouteMemberContract],
) -> dict[RouteKey, RouteMemberContract]:
    members_by_key: dict[RouteKey, RouteMemberContract] = {}
    for member in members:
        key = (member.path, member.method)
        if key in members_by_key:
            raise RuntimeError(f"{family_name} router does not define the expected route family.")
        members_by_key[key] = member

    if not members_by_key:
        raise RuntimeError(f"{family_name} router does not define the expected route family.")

    return members_by_key


def _expected_methods_by_path(
    members: Iterable[RouteMemberContract],
) -> dict[str, frozenset[str]]:
    methods_by_path: dict[str, set[str]] = {}
    for member in members:
        methods_by_path.setdefault(member.path, set()).add(member.method)
    return {path: frozenset(methods) for path, methods in methods_by_path.items()}


def _source_endpoints(
    *,
    family_name: str,
    routers: Sequence[APIRouter],
    members_by_key: dict[RouteKey, RouteMemberContract],
    expected_paths: set[str],
    expected_methods_by_path: dict[str, frozenset[str]],
) -> dict[RouteKey, object]:
    endpoints: dict[RouteKey, object] = {}
    route_counts: dict[RouteKey, int] = {key: 0 for key in members_by_key}

    for router in routers:
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            path = str(route.path)
            if path not in expected_paths:
                raise RuntimeError(
                    f"{family_name} router does not define the expected route family."
                )

            method = _single_expected_method(
                family_name=family_name,
                path=path,
                methods=_route_methods(route),
                expected_methods_by_path=expected_methods_by_path,
            )
            key = (path, method)
            member = members_by_key[key]
            route_counts[key] += 1
            endpoints[key] = route.endpoint

            if route.include_in_schema is not member.include_in_schema:
                raise RuntimeError(f"{family_name} router does not preserve OpenAPI visibility.")
            for status_code in member.required_status_codes:
                if status_code not in (route.responses or {}):
                    raise RuntimeError(
                        f"{family_name} router does not preserve {status_code} response metadata."
                    )

    if set(endpoints) != set(members_by_key) or any(count != 1 for count in route_counts.values()):
        raise RuntimeError(f"{family_name} router does not define the expected route family.")

    return endpoints


def _route_methods(route: APIRoute) -> frozenset[str]:
    return frozenset(str(method).upper() for method in (route.methods or set()))


def _single_expected_method(
    *,
    family_name: str,
    path: str,
    methods: frozenset[str],
    expected_methods_by_path: dict[str, frozenset[str]],
) -> str:
    matching_methods = methods & expected_methods_by_path[path]
    if len(matching_methods) != 1:
        raise RuntimeError(f"{family_name} router does not define the expected route family.")
    unexpected_methods = methods - matching_methods - _FRAMEWORK_METHODS
    if unexpected_methods:
        raise RuntimeError(f"{family_name} router does not define the expected route family.")
    return next(iter(matching_methods))


def _family_routes(target_app: FastAPI, expected_paths: set[str]) -> list[APIRoute]:
    return [
        route
        for route in target_app.routes
        if isinstance(route, APIRoute) and str(route.path) in expected_paths
    ]


def _validate_existing_routes(
    *,
    family_name: str,
    family_routes: Sequence[APIRoute],
    members_by_key: dict[RouteKey, RouteMemberContract],
    expected_paths: set[str],
    expected_methods_by_path: dict[str, frozenset[str]],
    source_endpoints: dict[RouteKey, object],
    endpoint_matcher: EndpointMatcher,
) -> None:
    present_keys: set[RouteKey] = set()

    for route in family_routes:
        path = str(route.path)
        methods = _route_methods(route)
        matching_methods = methods & expected_methods_by_path[path]
        if len(matching_methods) != 1:
            raise RuntimeError(f"Partial {family_name.lower()} route registration detected.")
        unexpected_methods = methods - matching_methods - _FRAMEWORK_METHODS
        if unexpected_methods:
            raise RuntimeError(f"Partial {family_name.lower()} route registration detected.")
        present_keys.add((path, next(iter(matching_methods))))

    expected_keys = set(members_by_key)
    if present_keys != expected_keys:
        present_paths = {path for path, _method in present_keys}
        existing = ", ".join(sorted(present_paths))
        missing = ", ".join(sorted(expected_paths - present_paths))
        raise RuntimeError(
            f"Partial {family_name.lower()} route registration detected. "
            f"Existing: {existing or '<none>'}; missing: {missing or '<none>'}."
        )

    for key, member in members_by_key.items():
        path, method = key
        matching_routes = [
            route
            for route in family_routes
            if str(route.path) == path and method in _route_methods(route)
        ]
        if len(matching_routes) != 1 or not endpoint_matcher(
            matching_routes[0].endpoint,
            source_endpoints[key],
        ):
            raise RuntimeError(
                f"Duplicate {path} route detected with a different "
                f"{family_name.lower()} handler."
            )

        route = matching_routes[0]
        if route.include_in_schema is not member.include_in_schema:
            raise RuntimeError(
                f"Existing {path} route does not preserve "
                f"{family_name.lower()} OpenAPI visibility."
            )
        for status_code in member.required_status_codes:
            if status_code not in (route.responses or {}):
                raise RuntimeError(
                    f"Existing {path} route does not preserve " f"{status_code} response metadata."
                )
        for dependency in member.required_dependencies:
            if not route_has_dependency_call(
                route,
                dependency,
                endpoint_matcher=endpoint_matcher,
            ):
                raise RuntimeError(
                    f"Existing {path} route does not preserve "
                    f"{family_name.lower()} required dependency."
                )
