# -*- coding: utf-8 -*-
"""
Tests for Health, Metrics and Root endpoints in main.py

RU: Тесты для health, metrics и root эндпоинтов
EN: Tests for health, metrics and root endpoints

These are "easy coverage" tests that cover basic monitoring endpoints.
"""

from fastapi.testclient import TestClient

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
