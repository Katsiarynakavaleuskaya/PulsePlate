"""Environment and route registration guards.

These tests ensure the test environment is properly configured and critical
routes are registered. They catch import-order and feature-flag issues early.
"""

import os

from fastapi import FastAPI


def test_testing_env_enabled() -> None:
    """Guard: TESTING must be set before legacy_app import."""
    assert os.getenv("TESTING") == "true", "TESTING env var must be 'true' in tests"


def test_export_pdf_route_registered() -> None:
    """Guard: export/pdf route must be registered when TESTING=true."""
    import app

    paths = {r.path for r in app.app.routes}
    assert "/api/v1/export/pdf" in paths, "Export PDF route not registered"


def test_app_is_legacy_instance() -> None:
    """Guard: app.app must be the same instance as legacy_app.app."""
    import app
    import legacy_app

    assert app.app is legacy_app.app, "app.app must be legacy_app.app instance"


def test_rate_limit_bootstrap_disabled_for_canonical_app_import(app: FastAPI) -> None:
    """Guard: canonical app.main bootstrap must not attach active rate limiting in tests."""
    assert not hasattr(app.state, "limiter")

    import app.security.rate_limit as rate_limit

    assert rate_limit._rate_limiting_enabled() is False
    if rate_limit.limiter is not None:
        assert getattr(rate_limit.limiter, "enabled", True) is False
