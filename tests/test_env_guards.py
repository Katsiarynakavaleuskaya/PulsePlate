"""Environment and route registration guards.

These tests ensure the test environment is properly configured and critical
routes are registered. They catch import-order and feature-flag issues early.
"""

import os


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
