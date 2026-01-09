"""
Targeted tests for app.py endpoints (lines 1383-1401) to reach 97% coverage.

Covers:
- /api/v1/health endpoint
- /metrics endpoint (Prometheus)
- /privacy endpoint
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
        """/metrics returns error when Prometheus client not available."""
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
        assert "Prometheus client not available" in data["error"]

    def test_privacy_endpoint_structure(self, client: TestClient) -> None:
        """/privacy returns complete privacy policy structure."""
        response = client.get("/privacy")
        assert response.status_code == 200
        data: dict[str, Any] = response.json()

        # Verify top-level keys
        assert "privacy_policy" in data
        assert "data_collection" in data
        assert "data_retention" in data
        assert "data_classification" in data
        assert "contact" in data
        assert "gdpr_compliance" in data

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

    def test_privacy_endpoint_retention_days(self, client: TestClient) -> None:
        """/privacy includes retention period from log retention manager."""
        response = client.get("/privacy")
        assert response.status_code == 200
        data = response.json()

        # Check that retention_period_days is a number
        retention_days = data["data_collection"]["pseudonymous_identifiers"][
            "retention_period_days"
        ]
        assert isinstance(retention_days, int)
        assert retention_days >= 0

        # Verify it's mentioned in data_retention string
        assert str(retention_days) in data["data_retention"]
