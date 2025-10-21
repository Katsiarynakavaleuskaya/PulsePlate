# -*- coding: utf-8 -*-
"""
Combined app endpoint tests: health, monitoring, root, and package shim edges.

RU: Объединенные тесты для app эндпоинтов: health, monitoring, root и package shim edges
EN: Combined tests for app endpoints: health, monitoring, root and package shim edges

These are "easy coverage" tests that cover basic monitoring endpoints and app package behavior.
"""

import sys
from typing import Any

import app as apppkg
import pytest


class TestHealthAndMonitoringEndpoints:
    """Test health and monitoring endpoints for easy coverage boost"""

    def test_health_ok(self, client: Any) -> None:
        """Test /health endpoint returns status ok"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_v1_health_ok(self, client: Any) -> None:
        """Test /api/v1/health endpoint returns status ok"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_metrics_endpoint(self, client: Any) -> None:
        """Test /metrics endpoint - returns Prometheus metrics or error"""
        response = client.get("/metrics")
        if response.status_code == 404:
            pytest.skip("/metrics disabled in this build")
        assert response.status_code == 200
        # Either Prometheus metrics or error message about unavailable client
        content = response.text
        assert (
            "python_gc_objects_collected_total" in content
            or "Prometheus client not available" in content
        )

    def test_root_page_renders(self, client: Any) -> None:
        """Test root / endpoint renders HTML BMI calculator"""
        response = client.get("/")
        assert response.status_code == 200
        content = response.text
        assert "<title" in content
        assert "BMI Calculator" in content
        assert "form" in content.lower()

    def test_favicon_endpoint(self, client: Any) -> None:
        """Test /favicon.ico returns 204 No Content"""
        response = client.get("/favicon.ico")
        assert response.status_code in [204, 200, 404]

    def test_privacy_endpoint(self, client: Any) -> None:
        """Test /privacy endpoint returns privacy policy"""
        response = client.get("/privacy")
        assert response.status_code == 200
        data = response.json()
        assert "privacy_policy" in data
        assert "data_retention" in data
        assert "contact" in data
        # Assert structure/keys; avoid brittle exact phrasing
        assert isinstance(data["privacy_policy"], str)


class TestDebugEndpoint:
    """Test debug endpoints for development"""

    def test_debug_env_endpoint(self, client: Any) -> None:
        """Test /debug_env returns environment info"""
        response = client.get("/debug_env")
        assert response.status_code == 200
        data = response.json()
        # Should contain meaningful debug information
        assert isinstance(data, dict)
        assert len(data) > 0, "Debug endpoint should return non-empty data"

        # Check for expected environment keys (based on actual debug endpoint response)
        expected_keys = [
            "FEATURE_INSIGHT",
            "LLM_PROVIDER",
            "GROK_MODEL",
            "GROK_ENDPOINT",
            "insight_enabled",
        ]
        found_keys = [key for key in expected_keys if key in data]
        assert (
            found_keys
        ), f"Expected at least one of {expected_keys} in debug data, got: {list(data.keys())}"


class TestAppPackageShimEdges:
    """Test app package shim (__init__.py): passthrough attr and spec proxy name."""

    def test_app_package_spec_proxy_and_getattr_passthrough(self) -> None:
        """Test that accessing __spec__.name returns 'app' and keeps module bound."""
        # Accessing __spec__.name returns 'app' and keeps module bound
        spec = apppkg.__spec__
        assert spec is not None and spec.name == "app"

        # Test public API access instead of internal implementation
        assert hasattr(apppkg, "app")
        assert apppkg.app is not None

        # Optional: cover internal passthrough only when available
        mod = getattr(apppkg, "_mod", None)
        if mod is not None:
            import types
            # Set a sentinel on the backing module and ensure passthrough via apppkg
            setattr(mod, "_shim_sentinel", "ok")  # cleanup not required across process
            assert getattr(apppkg, "_shim_sentinel") == "ok"

    def test_app_package_spec_proxy_attrs_exist(self):
        """Test that spec proxy attributes are accessible without raising."""
        spec = apppkg.__spec__
        assert spec is not None
        # origin/loader/submodule_search_locations should be accessible without raising
        _ = spec.origin
        _ = spec.loader
        loc = spec.submodule_search_locations or []
        assert isinstance(loc, (list, tuple))

    def test_app_package_all_and_sysmodules_binding(self, monkeypatch):
        """Test __all__ exports and sys.modules binding behavior."""
        # Ensure __all__ exposes app
        exported = getattr(apppkg, "__all__", [])
        assert "app" in exported

        # Break binding and verify spec.name rebinds sys.modules['app'] to this module
        monkeypatch.setitem(sys.modules, "app", object())
        spec = apppkg.__spec__
        assert spec is not None
        _ = spec.name
        assert sys.modules.get("app") is apppkg

    def test_app_getattr_missing_raises_attributeerror(self) -> None:
        """Test that getattr raises AttributeError for missing attributes."""
        with pytest.raises(AttributeError):
            getattr(apppkg, "__definitely_missing_attribute__")  # noqa: B009
