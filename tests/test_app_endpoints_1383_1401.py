"""
Targeted tests for app.py endpoints (lines 1383-1401) to reach 97% coverage.

Covers:
- /api/v1/health endpoint
- /metrics endpoint (Prometheus)
- /privacy endpoint
- /terms endpoint
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient


class TestAppEndpoints1383_1401:
    """Tests for app.py endpoints lines 1383-1401."""

    def test_health_v1_endpoint(self, client: TestClient) -> None:
        """/api/v1/health returns ok status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_metrics_endpoint_prometheus_unavailable(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """/metrics returns error when Prometheus exporter fails at runtime.

        Uses conftest client fixture (canonical entrypoint with observability bootstrap).
        """
        import prometheus_client

        # Force exporter failure to test JSON fallback
        def _boom() -> bytes:
            raise RuntimeError("Prometheus exporter unavailable")

        monkeypatch.setattr(prometheus_client, "generate_latest", _boom)

        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "error" in data
        # RuntimeError during generate_latest() should return "Metrics export failed"
        assert data["error"] == "Metrics export failed"

    def test_metrics_endpoint_prometheus_not_installed(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """/metrics returns error when prometheus_client package is not installed.

        Tests ImportError branch (prometheus_client missing from environment).
        Uses _import_prometheus_client() test seam to simulate ImportError
        without sys.modules manipulation (forbidden by import hygiene guards).
        """
        import app.bootstrap.metrics as m

        def _raise_import_error() -> None:
            raise ImportError("no prometheus_client")

        monkeypatch.setattr(m, "_import_prometheus_client", _raise_import_error)

        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "error" in data
        # ImportError should return "Prometheus client not available"
        assert data["error"] == "Prometheus client not available"

    def test_privacy_endpoint_structure(self, client: TestClient) -> None:
        """/privacy returns complete privacy policy structure."""
        response = client.get("/privacy")
        assert response.status_code == 200
        assert response.headers["content-type"].lower().startswith("application/json")
        data: dict[str, Any] = response.json()

        # Verify top-level keys
        assert "privacy_policy" in data
        assert "data_collection" in data
        assert "data_retention" in data
        assert "data_classification" in data
        assert "contact" in data
        assert "gdpr_compliance" in data
        assert "policy_version" in data
        assert "last_updated" in data
        assert "processing_categories" in data
        assert "providers" in data
        assert "rights" in data
        assert "automated_analysis" in data
        assert "retention_summary" in data

        # Verify data_collection structure
        assert "pseudonymous_identifiers" in data["data_collection"]
        pseudo = data["data_collection"]["pseudonymous_identifiers"]
        assert "type" in pseudo
        assert "purpose" in pseudo
        assert "retention_period_days" in pseudo
        assert "classification" in pseudo
        assert "deletion" in pseudo

        # Verify data_classification structure
        assert "pseudonymous_logs" in data["data_classification"]
        assert "access_control" in data["data_classification"]
        assert "salt_rotation" in data["data_classification"]
        assert isinstance(data["providers"], list)
        assert isinstance(data["processing_categories"], list)
        assert isinstance(data["rights"], list)
        assert isinstance(data["automated_analysis"], list)

    def test_privacy_endpoint_retention_days(self, client: TestClient) -> None:
        """/privacy includes retention period from log retention manager."""
        response = client.get("/privacy")
        assert response.status_code == 200
        assert response.headers["content-type"].lower().startswith("application/json")
        data = response.json()

        # Check that retention_period_days is a number
        retention_days = data["data_collection"]["pseudonymous_identifiers"][
            "retention_period_days"
        ]
        assert isinstance(retention_days, int)
        assert retention_days >= 0

        # Verify it's mentioned in data_retention string
        assert str(retention_days) in data["data_retention"]

    def test_terms_endpoint_structure(self, client: TestClient) -> None:
        """/terms returns canonical legal publication structure."""
        response = client.get("/terms")
        assert response.status_code == 200
        assert response.headers["content-type"].lower().startswith("application/json")
        data: dict[str, Any] = response.json()

        assert "terms_of_use" in data
        assert "service_scope" in data
        assert "billing_and_subscriptions" in data
        assert "acceptable_use" in data
        assert "liability_boundary" in data
        assert "contact" in data
        assert data["effective_date"] == "2026-03-08"

        service_scope = data["service_scope"]
        assert service_scope["category"] == "wellness / nutrition planning / coaching support"
        assert "medical" in service_scope["medical_boundary"].lower()

        billing = data["billing_and_subscriptions"]
        assert "Apple" in billing["ios_app_store"]
        assert "backend" in billing["entitlement_truth"].lower()

    def test_terms_endpoint_keeps_wellness_boundaries(self, client: TestClient) -> None:
        """/terms must preserve non-medical product framing."""
        response = client.get("/terms")
        assert response.status_code == 200
        assert response.headers["content-type"].lower().startswith("application/json")
        data = response.json()

        assert "wellness" in data["terms_of_use"].lower()
        assert "does not provide medical diagnosis" in data["terms_of_use"].lower()
        forbidden = data["acceptable_use"]["forbidden"]
        assert "using the service for medical triage or emergency decisions" in forbidden
