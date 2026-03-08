# -*- coding: utf-8 -*-
"""
Combined app endpoint tests: health, monitoring, root, and package shim edges.

RU: Объединенные тесты для app эндпоинтов: health, monitoring, root и package shim edges
EN: Combined tests for app endpoints: health, monitoring, root and package shim edges

These are "easy coverage" tests that cover basic monitoring endpoints and app package behavior.
"""

import os
import sys
from fastapi.testclient import TestClient

import app as apppkg
import pytest


class TestHealthAndMonitoringEndpoints:
    """Test health and monitoring endpoints for easy coverage boost"""

    def test_health_ok(self, client: TestClient) -> None:
        """Test /health endpoint returns status ok"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # Verify new fields exist (version, git_sha, timestamp, environment)
        assert {"version", "git_sha", "timestamp", "environment"}.issubset(data.keys())

    def test_v1_health_ok(self, client: TestClient) -> None:
        """Test /api/v1/health endpoint returns status ok"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # Verify new fields exist (version, git_sha, timestamp, environment)
        assert {"version", "git_sha", "timestamp", "environment"}.issubset(data.keys())

    @pytest.mark.skipif(
        os.getenv("METRICS_ENABLED", "true").lower() != "true",
        reason="Metrics disabled in this build",
    )
    def test_metrics_endpoint(self, client: TestClient) -> None:
        """Test /metrics endpoint - returns Prometheus metrics or error"""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Either Prometheus metrics or error message about unavailable client
        content = response.text
        assert (
            "python_gc_objects_collected_total" in content
            or "Prometheus client not available" in content
        )

    def test_root_page_renders(self, client: TestClient) -> None:
        """Test root / endpoint renders HTML BMI calculator"""
        response = client.get("/")
        assert response.status_code == 200
        content = response.text
        assert "<title" in content
        assert "BMI Calculator" in content
        assert "form" in content.lower()

    def test_favicon_endpoint(self, client: TestClient) -> None:
        """Test /favicon.ico returns 200 OK, 204 No Content, or 404 if not found"""
        response = client.get("/favicon.ico")
        assert response.status_code in [200, 204, 404]  # 200 OK is valid for successful favicon

    def test_privacy_endpoint(self, client: TestClient) -> None:
        """Test /privacy endpoint returns privacy policy"""
        response = client.get("/privacy")
        assert response.status_code == 200
        data = response.json()
        assert "privacy_policy" in data
        assert "data_retention" in data
        assert "contact" in data
        assert "policy_version" in data
        assert "providers" in data
        # Assert structure/keys; avoid brittle exact phrasing
        assert isinstance(data["privacy_policy"], str)


class TestDebugEndpoint:
    """Test debug endpoints for development"""

    def test_debug_env_endpoint(self, client: TestClient) -> None:
        """Test /debug_env returns environment info"""
        response = client.get("/debug_env")
        assert response.status_code == 200
        data = response.json()
        # Should contain meaningful debug information
        assert isinstance(data, dict)
        assert len(data) > 0, "Debug endpoint should return non-empty data"

        # Check for essential debug key categories (flexible assertions)
        debug_keys = set(data.keys())

        # Ensure at least one feature flag exists
        feature_flags = [key for key in debug_keys if key.startswith("FEATURE_")]
        assert len(feature_flags) > 0, "Expected at least one FEATURE_* flag in debug data"

        # Ensure LLM provider configuration exists
        llm_keys = [
            key for key in debug_keys if "PROVIDER" in key or "MODEL" in key or "ENDPOINT" in key
        ]
        assert (
            len(llm_keys) > 0
        ), "Expected at least one LLM-related key (PROVIDER/MODEL/ENDPOINT) in debug data"

        # Ensure insight functionality flag exists
        insight_keys = [key for key in debug_keys if "insight" in key.lower()]
        assert len(insight_keys) > 0, "Expected at least one insight-related key in debug data"


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

    def test_app_package_spec_proxy_attrs_exist(self) -> None:
        """Test that spec proxy attributes are accessible without raising."""
        spec = apppkg.__spec__
        assert spec is not None
        # origin/loader/submodule_search_locations should be accessible without raising
        _ = spec.origin
        _ = spec.loader
        loc = spec.submodule_search_locations or []
        assert isinstance(loc, (list, tuple))

    def test_app_package_all_and_sysmodules_binding(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test __all__ exports and sys.modules binding behavior."""
        # Ensure __all__ exposes app
        exported = getattr(apppkg, "__all__", [])
        assert "app" in exported

        # Verify sys.modules["app"] points to the package
        assert sys.modules.get("app") is apppkg

    def test_app_getattr_missing_raises_attributeerror(self) -> None:
        """Test that getattr raises AttributeError for missing attributes."""
        with pytest.raises(AttributeError):
            getattr(apppkg, "__definitely_missing_attribute__")  # noqa: B009
