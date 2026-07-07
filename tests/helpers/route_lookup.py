"""Shared route-discovery helpers for route-family test suites.

RU: Общие помощники поиска маршрутов для тестов route-family.
EN: Central path/method route filtering so route-family test suites do not
duplicate the ``iter_effective_route_candidates``-based lookup logic.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from fastapi import FastAPI

from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_endpoint,
    route_methods,
    route_path,
)

RouteKey = tuple[str, str]


def all_api_paths(target_app: FastAPI) -> set[str]:
    """Return every registered API route path on the app."""

    return {
        route_path(route)
        for route in iter_effective_route_candidates(target_app.routes)
        if is_api_route_candidate(route)
    }


def family_routes(target_app: FastAPI, expected_paths: set[str]) -> list[object]:
    """Return API routes whose path belongs to the expected family paths."""

    return [
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if is_api_route_candidate(route) and route_path(route) in expected_paths
    ]


def registered_route_counts(
    target_app: FastAPI,
    expected_keys: Iterable[RouteKey],
) -> Counter[RouteKey]:
    """Count registrations for each expected (path, method) family member."""

    expected = set(expected_keys)
    expected_paths = {path for path, _method in expected}
    counts: Counter[RouteKey] = Counter()
    for route in family_routes(target_app, expected_paths):
        for method in route_methods(route):
            key = (route_path(route), method)
            if key in expected:
                counts[key] += 1
    return counts


def find_single_route(
    target_app: FastAPI,
    path: str,
    method: str,
    *,
    family_label: str = "route",
) -> object:
    """Return exactly one registered route for (path, method) or fail loudly."""

    matches = [
        route for route in family_routes(target_app, {path}) if method in route_methods(route)
    ]
    route_summaries = [
        f"{route_path(route)}:{sorted(route_methods(route))}:{route_endpoint(route).__module__}"
        for route in matches
    ]
    assert len(matches) == 1, (
        f"expected exactly one {family_label} route for {method} {path}; "
        f"found {len(matches)}: {route_summaries}"
    )
    return matches[0]
