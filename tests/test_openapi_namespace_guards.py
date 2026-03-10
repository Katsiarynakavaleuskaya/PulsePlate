from __future__ import annotations

from typing import Iterable

from app.main import app

ALLOWED_PREFIXES: tuple[str, ...] = (
    "/api/v1/billing/",
    "/api/v1/bmi/",
    "/api/v1/insight/",
    "/api/v1/pro/",
    "/api/v1/vip/",
)
ALLOWED_EXACT: frozenset[str] = frozenset({"/api/v1/bmi", "/api/v1/insight"})
# Legacy WS path is kept at runtime but should NOT appear in OpenAPI schema
# (WebSocket endpoints are not included in OpenAPI by default)
LEGACY_DENY_PREFIXES: tuple[str, ...] = (
    "/api/v1/foods",
    "/api/v1/restaurants",
    "/api/v1/users",
)


def _openapi_paths() -> list[str]:
    schema = app.openapi()
    raw_paths = schema.get("paths", {})
    return sorted(str(path) for path in raw_paths.keys())


def _runtime_paths() -> set[str]:
    return {str(getattr(route, "path", "")) for route in app.routes}


def _is_allowed_path(path: str) -> bool:
    if path in ALLOWED_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def _pick_prefixed(paths: Iterable[str], prefixes: tuple[str, ...]) -> list[str]:
    return sorted(path for path in paths if any(path.startswith(prefix) for prefix in prefixes))


def test_openapi_paths_use_only_allowed_namespaces() -> None:
    paths = _openapi_paths()
    disallowed = sorted(path for path in paths if not _is_allowed_path(path))
    assert disallowed == [], f"OpenAPI contains disallowed namespaces: {disallowed}"


def test_openapi_does_not_leak_legacy_food_or_restaurant_surface() -> None:
    paths = _openapi_paths()
    leaked = _pick_prefixed(paths, LEGACY_DENY_PREFIXES)
    assert leaked == [], f"legacy surface leaked into schema: {leaked}"


def test_runtime_keeps_legacy_routes_and_ws_for_transition_window() -> None:
    runtime_paths = _runtime_paths()
    # Legacy WS path (deprecated, kept for transition)
    assert "/ws" in runtime_paths
    # Canonical PRO WS path
    assert "/api/v1/pro/ws" in runtime_paths
    # Legacy food/restaurant routes (hidden from schema, kept at runtime)
    assert "/api/v1/foods" in runtime_paths
    assert "/api/v1/restaurants/search" in runtime_paths
    # Users CRUD remains registered for internal callers but is hidden from public schema
    assert "/api/v1/users" in runtime_paths
    assert "/api/v1/users/{user_id}" in runtime_paths


def test_users_routes_are_hidden_from_schema_at_registration_level() -> None:
    users_routes = [
        route for route in app.routes if str(getattr(route, "path", "")).startswith("/api/v1/users")
    ]

    assert users_routes, "users routes should remain registered at runtime"
    assert all(
        getattr(route, "include_in_schema", True) is False for route in users_routes
    ), "users routes must stay hidden from public schema"


def test_openapi_tags_and_description_do_not_advertise_users_surface() -> None:
    """Canonical public OpenAPI copy must not advertise internalized users CRUD."""
    schema = app.openapi()

    tag_names = {str(tag.get("name", "")).lower() for tag in schema.get("tags", [])}
    description = str(schema.get("info", {}).get("description", "")).lower()

    assert "users" not in tag_names
    assert "user management" not in description


def test_ws_routes_not_in_openapi_schema() -> None:
    """WebSocket endpoints must not appear in the OpenAPI schema."""
    paths = set(_openapi_paths())
    ws_routes = {"/ws", "/api/v1/pro/ws"}
    leaked = ws_routes & paths
    assert not leaked, f"WS routes leaked into OpenAPI schema: {sorted(leaked)}"
