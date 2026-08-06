"""Environment and route registration guards.

These tests ensure the test environment is properly configured and critical
routes are registered. They catch import-order and feature-flag issues early.
"""

import os

from fastapi import FastAPI

from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_matches_path_method,
    route_responses,
)


def test_testing_env_enabled() -> None:
    """Guard: TESTING must be set before legacy_app import."""
    assert os.getenv("TESTING") == "true", "TESTING env var must be 'true' in tests"


def test_export_route_registration_contract() -> None:
    """Guard canonical export route uniqueness and 429 documentation."""
    import app

    routes = [
        route
        for route in iter_effective_route_candidates(app.app.routes)
        if is_api_route_candidate(route)
    ]
    expected_routes = (
        ("POST", "/api/v1/export/sign"),
        ("GET", "/api/v1/plan/week/export.csv"),
        ("GET", "/api/v1/plan/week/export.pdf"),
    )
    for method, path in expected_routes:
        matching_routes = [
            route for route in routes if route_matches_path_method(route, path, method)
        ]
        assert len(matching_routes) == 1
        assert 429 in route_responses(matching_routes[0])


def test_app_is_legacy_instance() -> None:
    """Guard: app.app must be the same instance as legacy_app.app."""
    import app
    import legacy_app

    assert app.app is legacy_app.app, "app.app must be legacy_app.app instance"


def test_rate_limit_bootstrap_disabled_for_canonical_app_import(app: FastAPI) -> None:
    """Guard: canonical app.main bootstrap must not attach active rate limiting in tests."""
    from app.security import rate_limit as rate_limit_mod

    limiter_on_state = getattr(app.state, "limiter", None)
    assert limiter_on_state is None or getattr(limiter_on_state, "enabled", False) is False

    shared_limiter = getattr(rate_limit_mod, "limiter", None)
    assert shared_limiter is None or getattr(shared_limiter, "enabled", False) is False
