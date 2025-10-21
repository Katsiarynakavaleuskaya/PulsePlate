"""
Combined basic app tests: import, VIP integration, and package spec.
"""

import sys
from fastapi import FastAPI

import app
import pytest


class TestAppImport:
    """Test basic app import and structure."""

    def test_app_import(self):
        """Test that app.py can be imported."""
        assert app is not None
        assert hasattr(app, "app")  # FastAPI app instance
        assert app.app is not None
        assert isinstance(app.app, FastAPI)

    def test_app_endpoints(self):
        """Test that app has expected endpoints."""
        # Just check that the app has some routes
        assert hasattr(app.app, "routes")
        assert len(app.app.routes) > 0


class TestAppVIPIntegration:
    """Test VIP module integration."""

    @pytest.mark.usefixtures("test_environment")
    def test_app_vip_integration_success(self):
        """Verify that VIP routes register successfully when the module is enabled."""
        # Since VIP module is currently working, test that it's properly integrated
        fastapi_app = app.app

        # The app should be created and standard routes present
        paths = {
            getattr(route, "path", None) or getattr(route, "path_format", "")
            for route in fastapi_app.routes
        }
        # Check for specific health endpoint path based on API design
        assert "/health" in paths

        # VIP routes should be present since VIP module is enabled
        vip_paths = {p for p in paths if "/vip/" in p}
        assert vip_paths, "VIP routes should be registered when the module is enabled"


class TestAppPackageSpec:
    """Test app package specification and proxy behavior."""

    def test_app_package_spec_proxy_name(self):
        """Test that app package spec has correct name."""
        import app as apppkg

        # Accessing __spec__.name should not crash and should be 'app'
        spec = apppkg.__spec__
        assert spec is not None
        assert spec.name == "app"

    def test_app_package_spec_proxy_rebinds_sys_modules(self, monkeypatch):
        """Test that accessing spec triggers proxy and rebinds sys.modules."""
        import app as apppkg

        # Replace sys.modules['app'] with a placeholder to simulate external mutation
        monkeypatch.setitem(sys.modules, "app", object())
        # Accessing name should trigger proxy and rebind sys.modules['app'] back to module
        spec = apppkg.__spec__
        assert spec is not None, "apppkg.__spec__ should not be None"
        assert spec.name == "app", f"Expected spec.name to be 'app', got {spec.name}"
        assert sys.modules["app"] is apppkg, "sys.modules['app'] should be bound to apppkg"

    def test_app_getattr_passes_through_and_raises_attribute_error(self):
        """Test that __getattr__ delegates and raises AttributeError for missing symbols."""
        import app as apppkg

        # __getattr__ should delegate to underlying module and raise on missing
        with pytest.raises(AttributeError):
            getattr(apppkg, "__definitely_missing_symbol__")  # noqa: B009
