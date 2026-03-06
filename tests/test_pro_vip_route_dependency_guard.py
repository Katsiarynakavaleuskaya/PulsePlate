from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.main import app
from app.middleware.api_tiers import require_pro_tier, require_vip_tier
from app.routers.api_key import api_key_header

CANONICAL_PREFIX_GUARD = {
    "/api/v1/pro/": require_pro_tier,
    "/api/v1/vip/": require_vip_tier,
}
LEGACY_HTTP_ALIAS_ALLOWLIST = {
    ("POST", "/api/v1/vip/weekly-plan"),
}


def _load_routes() -> list[APIRoute]:
    return [route for route in app.routes if isinstance(route, APIRoute)]


def _flatten_dependency_calls(route: APIRoute) -> list[Callable[..., Any]]:
    seen: set[int] = set()
    calls: list[Callable[..., Any]] = []

    def visit(dep: Dependant) -> None:
        call = getattr(dep, "call", None)
        if callable(call) and id(call) not in seen:
            seen.add(id(call))
            calls.append(call)
        for child in getattr(dep, "dependencies", []) or []:
            visit(child)

    for dep in getattr(route.dependant, "dependencies", []) or []:
        visit(dep)
    return calls


def _canonical_pro_vip_routes(routes: list[APIRoute]) -> list[APIRoute]:
    canonical: list[APIRoute] = []
    for route in routes:
        if route.deprecated:
            continue
        if (getattr(route, "openapi_extra", None) or {}).get("x-alias-of"):
            continue
        if route.path.startswith("/api/v1/pro/") or route.path.startswith("/api/v1/vip/"):
            canonical.append(route)
    return canonical


def test_canonical_pro_vip_routes_require_expected_tier_dependency() -> None:
    routes = _canonical_pro_vip_routes(_load_routes())
    missing_guards: list[str] = []
    saw_prefixes = {prefix: False for prefix in CANONICAL_PREFIX_GUARD}

    for route in routes:
        for prefix, expected_guard in CANONICAL_PREFIX_GUARD.items():
            if not route.path.startswith(prefix):
                continue
            saw_prefixes[prefix] = True
            flattened_calls = _flatten_dependency_calls(route)
            if expected_guard not in flattened_calls:
                methods = ",".join(sorted(route.methods))
                names = ", ".join(
                    getattr(call, "__name__", type(call).__name__) for call in flattened_calls
                )
                missing_guards.append(
                    f"{methods} {route.path} missing {expected_guard.__name__}; got [{names}]"
                )
            break

    assert all(
        saw_prefixes.values()
    ), f"Expected guarded canonical prefixes missing: {saw_prefixes}"
    assert not missing_guards, "Canonical PRO/VIP route guard drift detected:\n" + "\n".join(
        missing_guards
    )


def test_canonical_vip_routes_keep_api_key_header_dependency() -> None:
    routes = [
        route
        for route in _canonical_pro_vip_routes(_load_routes())
        if route.path.startswith("/api/v1/vip/")
    ]
    missing_header: list[str] = []

    for route in routes:
        flattened_calls = _flatten_dependency_calls(route)
        if api_key_header not in flattened_calls:
            methods = ",".join(sorted(route.methods))
            missing_header.append(f"{methods} {route.path}")

    assert not missing_header, "Canonical VIP routes must keep API key extraction:\n" + "\n".join(
        missing_header
    )


def test_legacy_vip_weekly_plan_alias_is_deprecated_and_not_treated_as_canonical() -> None:
    routes = _load_routes()
    alias_route = next(
        route
        for route in routes
        if route.path == "/api/v1/vip/weekly-plan" and "POST" in route.methods
    )

    flattened_calls = _flatten_dependency_calls(alias_route)

    assert alias_route.deprecated is True
    assert ("POST", alias_route.path) in LEGACY_HTTP_ALIAS_ALLOWLIST
    assert require_vip_tier not in flattened_calls
    assert api_key_header in flattened_calls


def test_legacy_http_alias_allowlist_matches_deprecated_routes() -> None:
    routes = _load_routes()

    for method, path in LEGACY_HTTP_ALIAS_ALLOWLIST:
        matching_routes = [
            route
            for route in routes
            if path in {route.path, getattr(route, "path_format", route.path)}
            and method in (route.methods or set())
            and bool(getattr(route, "deprecated", False))
        ]
        assert matching_routes, (
            f"LEGACY_HTTP_ALIAS_ALLOWLIST entry ({method} {path}) does not map "
            "to any deprecated alias route in the live router table"
        )
