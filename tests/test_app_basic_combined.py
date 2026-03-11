"""
Combined basic app tests: import, VIP integration, and package spec.
"""

import importlib
import sys
from fastapi import FastAPI

import app
import pytest


class TestAppImport:
    """Test basic app import and structure."""

    def test_app_import(self) -> None:
        """Test that app.py can be imported."""
        assert app is not None
        assert hasattr(app, "app")  # FastAPI app instance
        assert app.app is not None
        assert isinstance(app.app, FastAPI)

    def test_app_endpoints(self) -> None:
        """Test that app has expected endpoints."""
        # Just check that the app has some routes
        assert app.app is not None
        assert hasattr(app.app, "routes")
        assert app.app.routes is not None
        assert len(app.app.routes) > 0

    def test_app_package_exposes_canonical_bootstrapped_routes(self) -> None:
        """`import app` must expose additive routes registered in app.main."""
        additive_paths = {
            "/api/v1/billing/apple/verify-receipt",
            "/api/v1/feedback/rag",
            "/api/v1/pro/cbt/insight",
            "/ws",
        }
        package_paths = {
            getattr(route, "path", None) or getattr(route, "path_format", "")
            for route in app.app.routes
        }
        from app.main import app as main_app

        main_paths = {
            getattr(route, "path", None) or getattr(route, "path_format", "")
            for route in main_app.routes
        }

        assert additive_paths.issubset(package_paths)
        assert additive_paths.issubset(main_paths)

    def test_app_package_keeps_legacy_app_identity(self) -> None:
        """The package shim must preserve the underlying legacy FastAPI object."""
        from app.main import app as main_app

        legacy_module = importlib.import_module("legacy_app")

        assert app.app is legacy_module.app
        assert app.app is main_app

    def test_app_package_rehydrates_bootstrap_after_legacy_app_swap(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Facade access must reapply additive bootstrap when legacy_app.app changes."""
        import app.main as main_module

        legacy_module = importlib.import_module("legacy_app")

        original_main_app = main_module.app
        replacement_app = FastAPI()
        monkeypatch.setattr(main_module, "app", original_main_app)
        monkeypatch.setattr(legacy_module, "app", replacement_app)

        package_app = app.app
        route_paths = {
            getattr(route, "path", None) or getattr(route, "path_format", "")
            for route in package_app.routes
        }

        assert package_app is replacement_app
        assert main_module.app is replacement_app
        assert "/api/v1/billing/apple/verify-receipt" in route_paths
        assert "/api/v1/feedback/rag" in route_paths
        assert "/api/v1/pro/cbt/insight" in route_paths
        assert "/ws" in route_paths


class TestAppVIPIntegration:
    """Test VIP module integration."""

    @pytest.mark.usefixtures("test_environment")
    def test_app_vip_integration_success(self) -> None:
        """Verify that VIP routes register successfully when the module is enabled."""
        # Since VIP module is currently working, test that it's properly integrated
        fastapi_app = app.app
        assert fastapi_app is not None

        # The app should be created and standard routes present
        paths = {
            getattr(route, "path", None) or getattr(route, "path_format", "")
            for route in fastapi_app.routes
        }
        # Check for health endpoint (both unversioned and versioned)
        assert "/health" in paths or "/api/v1/health" in paths

        # VIP routes should be present since VIP module is enabled
        vip_paths = {p for p in paths if p is not None and "/vip/" in p}
        assert vip_paths, "VIP routes should be registered when the module is enabled"


class TestAppPackageSpec:
    """Test app package specification and proxy behavior."""

    def test_app_package_spec_proxy_name(self) -> None:
        """Test that app package spec has correct name."""
        import app as apppkg

        # Accessing __spec__.name should not crash and should be 'app'
        spec = apppkg.__spec__
        assert spec is not None
        assert spec.name == "app"

    def test_app_package_sysmodules_binding(self) -> None:
        """Test that sys.modules['app'] is correctly bound."""
        import app as apppkg

        assert sys.modules.get("app") is apppkg
        spec = apppkg.__spec__
        assert spec is not None, "apppkg.__spec__ should not be None"
        assert spec.name == "app", f"Expected spec.name to be 'app', got {spec.name}"

    def test_app_getattr_passes_through_and_raises_attribute_error(self) -> None:
        """Test that __getattr__ delegates and raises AttributeError for missing symbols."""
        import app as apppkg

        # __getattr__ should delegate to underlying module and raise on missing
        with pytest.raises(AttributeError):
            getattr(apppkg, "__definitely_missing_symbol__")  # noqa: B009
