# -*- coding: utf-8 -*-
"""
Combined app endpoint tests: health, monitoring, root, and package shim edges.

RU: Объединенные тесты для app эндпоинтов: health, monitoring, root и package shim edges
EN: Combined tests for app endpoints: health, monitoring, root and package shim edges

These are "easy coverage" tests that cover basic monitoring endpoints and app package behavior.
"""

import asyncio
import os
import sys
from typing import cast
from xml.etree import ElementTree
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import app as apppkg
from app.routers.legal import build_terms_endpoint_payload
from app.bootstrap import public_discovery
from core.compliance import build_privacy_endpoint_payload
import pytest


def _find_route(client: TestClient, path: str, method: str = "GET") -> APIRoute:
    app = cast(FastAPI, client.app)
    matches = [
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path == path
        and method.upper() in (route.methods or set())
    ]
    assert len(matches) == 1
    return matches[0]


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

    def test_health_routes_are_owned_by_canonical_router(self, client: TestClient) -> None:
        """Operational health/readiness routes are served by app.routers.health."""
        for path in ("/health", "/api/v1/health", "/health/db", "/ready"):
            route = _find_route(client, path)
            assert route.endpoint.__module__ == "app.routers.health"

    def test_health_routes_stay_hidden_from_public_openapi(self, client: TestClient) -> None:
        """Health/readiness routes remain runtime-only, not public OpenAPI paths."""
        app = cast(FastAPI, client.app)
        paths = app.openapi()["paths"]

        assert "/health" not in paths
        assert "/api/v1/health" not in paths
        assert "/health/db" not in paths
        assert "/ready" not in paths

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

    def test_root_returns_direct_api_probe(self, client: TestClient) -> None:
        """Test GET / returns JSON when hitting FastAPI directly (Caddy serves SPA at apex)."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["surface"] == "api"

    def test_legacy_bmi_page_renders(self, client: TestClient) -> None:
        """Legacy HTML BMI calculator remains on /legacy/bmi-calculator."""
        response = client.get("/legacy/bmi-calculator")
        assert response.status_code == 200
        content = response.text
        assert "<title" in content
        assert "BMI Calculator" in content
        assert "form" in content.lower()

    def test_sitemap_endpoint_serves_public_routes(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test /sitemap.xml serves the canonical public discovery surface."""
        monkeypatch.delenv("PRODUCTION_DOMAIN", raising=False)

        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/xml")

        sitemap_root = ElementTree.fromstring(response.text)
        namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        loc_values = {
            loc.text
            for loc in sitemap_root.findall("sitemap:url/sitemap:loc", namespace)
            if loc.text is not None
        }
        assert loc_values == {
            "http://testserver/",
            "http://testserver/privacy",
            "http://testserver/terms",
            "http://testserver/legacy/bmi-calculator",
        }

    def test_sitemap_endpoint_prefers_configured_production_domain(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Configured production host wins over direct-origin/testserver hostnames."""
        monkeypatch.setenv("PRODUCTION_DOMAIN", "pulseplate.app")

        response = client.get("/sitemap.xml")

        assert response.status_code == 200
        sitemap_root = ElementTree.fromstring(response.text)
        namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        loc_values = {
            loc.text
            for loc in sitemap_root.findall("sitemap:url/sitemap:loc", namespace)
            if loc.text is not None
        }
        assert loc_values == {
            "https://pulseplate.app/",
            "https://pulseplate.app/privacy",
            "https://pulseplate.app/terms",
            "https://pulseplate.app/legacy/bmi-calculator",
        }

    def test_favicon_endpoint(self, client: TestClient) -> None:
        """Test /favicon.ico returns 200 OK, 204 No Content, or 404 if not found"""
        response = client.get("/favicon.ico")
        assert response.status_code in [200, 204, 404]  # 200 OK is valid for successful favicon

    def test_privacy_endpoint(self, client: TestClient) -> None:
        """Test /privacy endpoint returns canonical legal publication payload."""
        response = client.get("/privacy")
        assert response.status_code == 200
        assert response.headers["content-type"].lower().startswith("application/json")

        assert response.json() == jsonable_encoder(build_privacy_endpoint_payload())

    def test_terms_endpoint(self, client: TestClient) -> None:
        """Test /terms endpoint returns canonical legal publication payload."""
        response = client.get("/terms")
        assert response.status_code == 200
        assert response.headers["content-type"].lower().startswith("application/json")

        assert response.json() == build_terms_endpoint_payload().model_dump()

    def test_legal_routes_are_owned_by_canonical_router(self, client: TestClient) -> None:
        """/privacy and /terms are served by app.routers.legal, not legacy_app."""
        for path in ("/privacy", "/terms"):
            route = _find_route(client, path)
            assert route.endpoint.__module__ == "app.routers.legal"

    def test_legal_routes_stay_hidden_from_public_openapi(self, client: TestClient) -> None:
        """Legal publication routes remain runtime-only, not public OpenAPI paths."""
        app = cast(FastAPI, client.app)
        paths = app.openapi()["paths"]

        assert "/privacy" not in paths
        assert "/terms" not in paths


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


class TestPublicDiscoveryHelpers:
    """Unit coverage for public sitemap helper branches."""

    @staticmethod
    def _request_for_host(host: str, *, scheme: str = "https") -> Request:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": scheme,
            "path": public_discovery.SITEMAP_ROUTE_PATH,
            "raw_path": public_discovery.SITEMAP_ROUTE_PATH.encode("utf-8"),
            "root_path": "",
            "query_string": b"",
            "headers": [(b"host", host.encode("utf-8"))],
            "client": ("127.0.0.1", 12345),
            "server": (host, 443 if scheme == "https" else 80),
        }
        return Request(scope)

    def test_build_public_url_normalizes_base_and_path(self) -> None:
        """Builder normalizes base/path separators before joining URLs."""
        public_url = public_discovery._build_public_url(
            base_url="https://pulseplate.app",
            path="privacy",
        )
        assert public_url == "https://pulseplate.app/privacy"

    def test_build_public_sitemap_xml_escapes_query_values(self) -> None:
        """XML builder escapes query separators and keeps canonical loc entries."""
        sitemap_xml = public_discovery.build_public_sitemap_xml(
            base_url="https://pulseplate.app",
            paths=("privacy", "/terms?utm=summer&ref=share"),
        )

        assert sitemap_xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "<loc>https://pulseplate.app/privacy</loc>" in sitemap_xml
        assert "<loc>https://pulseplate.app/terms?utm=summer&amp;ref=share</loc>" in sitemap_xml

    def test_resolve_public_sitemap_base_url_prefers_sanitized_production_domain(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Configured production domain wins after quote/scheme/trailing-slash cleanup."""
        monkeypatch.setenv(public_discovery.PRODUCTION_DOMAIN_ENV, ' "http://pulseplate.app/" ')

        resolved_base_url = public_discovery.resolve_public_sitemap_base_url(
            self._request_for_host("direct-origin.internal")
        )

        assert resolved_base_url == "https://pulseplate.app"

    def test_resolve_public_sitemap_base_url_falls_back_to_request_host(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Missing production domain falls back to the direct request base URL."""
        monkeypatch.delenv(public_discovery.PRODUCTION_DOMAIN_ENV, raising=False)

        resolved_base_url = public_discovery.resolve_public_sitemap_base_url(
            self._request_for_host("edge.pulseplate.test")
        )

        assert resolved_base_url == "https://edge.pulseplate.test/"

    def test_serve_public_sitemap_returns_xml_response(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Async response helper returns XML with canonical public URLs."""
        monkeypatch.delenv(public_discovery.PRODUCTION_DOMAIN_ENV, raising=False)

        response = asyncio.run(
            public_discovery.serve_public_sitemap(self._request_for_host("edge.pulseplate.test"))
        )

        assert response.media_type == "application/xml"
        body = bytes(response.body)
        assert body.startswith(b'<?xml version="1.0" encoding="UTF-8"?>')
        assert b"https://edge.pulseplate.test/privacy" in body
