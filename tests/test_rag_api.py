"""
Tests for RAG API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_rag_stats_endpoint_success(client, monkeypatch):
    # Mock environment variable
    monkeypatch.setenv("FEATURE_RAG", "1")

    response = client.get("/api/v1/rag/stats", headers={"X-API-Key": "test_key"})
    assert response.status_code == 200

    data = response.json()
    assert "enabled" in data
    assert "stats" in data
    assert data["enabled"] is True


def test_rag_stats_endpoint_disabled(client):
    response = client.get("/api/v1/rag/stats", headers={"X-API-Key": "test_key"})
    assert response.status_code == 200

    data = response.json()
    assert data["enabled"] is False


def test_rag_toggle_endpoint_success(client):
    response = client.post(
        "/api/v1/rag/toggle", json={"enabled": True}, headers={"X-API-Key": "test_key"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["enabled"] is True


def test_rag_toggle_endpoint_invalid_data(client):
    response = client.post(
        "/api/v1/rag/toggle",
        json={"enabled": "not_a_boolean"},
        headers={"X-API-Key": "test_key"},
    )
    assert response.status_code == 422  # Pydantic returns 422 for validation errors


def test_rag_toggle_endpoint_missing_enabled(client):
    response = client.post("/api/v1/rag/toggle", json={}, headers={"X-API-Key": "test_key"})
    assert response.status_code == 422  # Pydantic validation error


def test_rag_stats_endpoint_unauthorized(client):
    response = client.get("/api/v1/rag/stats")
    assert response.status_code == 403  # API key validation returns 403


def test_rag_toggle_override_persistence(client):
    """Test that RAG toggle state persists in-memory across requests."""
    # Enable RAG
    response = client.post(
        "/api/v1/rag/toggle", json={"enabled": True}, headers={"X-API-Key": "test_key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["enabled"] is True

    # Check that stats now show enabled (overriding env var)
    response = client.get("/api/v1/rag/stats", headers={"X-API-Key": "test_key"})
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True

    # Disable RAG
    response = client.post(
        "/api/v1/rag/toggle", json={"enabled": False}, headers={"X-API-Key": "test_key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["enabled"] is False

    # Check that stats now show disabled
    response = client.get("/api/v1/rag/stats", headers={"X-API-Key": "test_key"})
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
