"""FastAPI route-table compatibility helpers."""

from __future__ import annotations

from collections.abc import Iterable

from fastapi.routing import APIRoute


def is_fastapi_included_router_marker(route: object) -> bool:
    route_type = type(route)
    return route_type.__module__ == "fastapi.routing" and route_type.__name__ == "_IncludedRouter"


def iter_effective_route_candidates(routes: Iterable[object]) -> Iterable[object]:
    for route in routes:
        if is_fastapi_included_router_marker(route):
            effective_route_contexts = getattr(route, "effective_route_contexts", None)
            if callable(effective_route_contexts):
                yield from effective_route_contexts()
                continue
        yield route


def is_api_route_candidate(route: object) -> bool:
    return isinstance(getattr(route, "original_route", route), APIRoute)


def route_path(route: object) -> str:
    path = getattr(route, "path", None)
    if path:
        return str(path)
    starlette_route = getattr(route, "starlette_route", None)
    path = getattr(starlette_route, "path", None)
    if path:
        return str(path)
    original_route = getattr(route, "original_route", None)
    path = getattr(original_route, "path", None)
    return str(path) if path is not None else ""


def route_endpoint(route: object) -> object:
    return getattr(route, "endpoint", None)


def route_include_in_schema(route: object) -> bool:
    return bool(getattr(route, "include_in_schema", True))


def route_responses(route: object) -> dict[object, object]:
    responses = getattr(route, "responses", None)
    return responses if isinstance(responses, dict) else {}


def route_methods(route: object) -> frozenset[str]:
    return frozenset(str(method).upper() for method in (getattr(route, "methods", None) or set()))
