# -*- coding: utf-8 -*-
"""
Combined app endpoint tests: health, monitoring, root, and package shim edges.

RU: Объединенные тесты для app эндпоинтов: health, monitoring, root и package shim edges
EN: Combined tests for app endpoints: health, monitoring, root and package shim edges

These are "easy coverage" tests that cover basic monitoring endpoints and app package behavior.
"""

import sys
from fastapi.testclient import TestClient

import app as apppkg
import pytest


class TestHealthAndMonitoringEndpoints:
    """Test health and monitoring endpoints for easy coverage boost"""

    def test_health_ok(self, test_client):
        """Test /health endpoint returns status ok"""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_v1_health_ok(self, test_client):
        """Test /api/v1/health endpoint returns status ok"""
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_metrics_endpoint(self, test_client):
        """Test /metrics endpoint - returns Prometheus metrics or error"""
        response = test_client.get("/metrics")
        assert response.status_code == 200
        # Either Prometheus metrics or error message about unavailable client
        content = response.text
        assert (
            "python_gc_objects_collected_total" in content
            or "Prometheus client not available" in content
        )

    def test_root_page_renders(self, test_client):
        """Test root / endpoint renders HTML BMI calculator"""
        response = test_client.get("/")
        assert response.status_code == 200
        content = response.text
        assert "<title" in content
        assert "BMI Calculator" in content
        assert "form" in content.lower()

    def test_favicon_endpoint(self, test_client):
        """Test /favicon.ico returns 204 No Content"""
        response = test_client.get("/favicon.ico")
        assert response.status_code == 204

    def test_privacy_endpoint(self, test_client):
        """Test /privacy endpoint returns privacy policy"""
        response = test_client.get("/privacy")
        assert response.status_code == 200
        data = response.json()
        assert "privacy_policy" in data
        assert "data_retention" in data
        assert "contact" in data
        assert "No personal data is stored" in data["privacy_policy"]


class TestDebugEndpoint:
    """Test debug endpoints for development"""

    def test_debug_env_endpoint(self, test_client):
        """Test /debug_env returns environment info"""
        response = test_client.get("/debug_env")
        assert response.status_code == 200
        data = response.json()
        # Should contain some environment information
        assert isinstance(data, dict)


class TestAppPackageShimEdges:
    """Test app package shim (__init__.py): passthrough attr and spec proxy name."""

    def test_app_package_spec_proxy_and_getattr_passthrough(self):
        """Test that accessing __spec__.name returns 'app' and keeps module bound."""
        # Accessing __spec__.name returns 'app' and keeps module bound
        spec = getattr(apppkg, "__spec__")
        name = getattr(spec, "name", None)
        assert name == "app"

        # getattr passthrough for an attribute via underlying module
        setattr(apppkg._mod, "_tmp_attr", "value")
        try:
            assert getattr(apppkg, "_tmp_attr") == "value"
        finally:
            delattr(apppkg._mod, "_tmp_attr")

    def test_app_package_spec_proxy_attrs_exist(self):
        """Test that spec proxy attributes are accessible without raising."""
        spec = getattr(apppkg, "__spec__")
        # origin/loader/submodule_search_locations should be accessible without raising
        _ = getattr(spec, "origin", None)
        _ = getattr(spec, "loader", None)
        loc = getattr(spec, "submodule_search_locations", [])
        assert isinstance(loc, (list, tuple))

    def test_app_package_all_and_sysmodules_binding(self, monkeypatch):
        """Test __all__ exports and sys.modules binding behavior."""
        # Ensure __all__ exposes app
        exported = getattr(apppkg, "__all__", [])
        assert "app" in exported

        # Break binding and verify spec.name rebinds sys.modules['app'] to this module
        monkeypatch.setitem(sys.modules, "app", object())
        spec = getattr(apppkg, "__spec__")
        _ = getattr(spec, "name")
        assert sys.modules.get("app") is apppkg

    def test_app_getattr_missing_raises_attributeerror(self):
        """Test that getattr raises AttributeError for missing attributes."""
        try:
            getattr(apppkg, "__definitely_missing_attribute__")
            raised = False
        except AttributeError:
            raised = True
        assert raised
