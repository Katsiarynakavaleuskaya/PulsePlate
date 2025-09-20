"""Smoke-check the FastAPI app exposes VIP routes when the module is enabled."""


def test_app_vip_integration_success():
    """Verify that VIP routes register successfully when the module is enabled."""
    # Since VIP module is currently working, test that it's properly integrated
    import app

    fastapi_app = getattr(app, "app")

    # The app should be created and standard routes present
    paths = {
        getattr(route, "path", None) or getattr(route, "path_format", "")
        for route in fastapi_app.routes
    }
    assert "/health" in paths or "/api/v1/health" in paths

    # VIP routes should be present since VIP module is enabled
    vip_paths = {p for p in paths if "/vip/" in p}
    assert len(vip_paths) > 0, "VIP routes should be registered when the module is enabled"
