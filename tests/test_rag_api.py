"""
Tests for RAG API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_rag_stats_endpoint_success(client, monkeypatch) -> None:
    # Mock environment variable
    monkeypatch.setenv("FEATURE_RAG", "1")

    response = client.get("/api/v1/rag/stats", headers={"X-API-Key": "test_key"})
    assert response.status_code == 200

    data = response.json()
    assert "enabled" in data
    assert "stats" in data
    assert data["enabled"] is True


def test_rag_stats_endpoint_import_error(client, monkeypatch) -> None:
    # Mock environment variable
    monkeypatch.setenv("FEATURE_RAG", "1")

    # Patch the import to raise ImportError
    import sys

    original_modules = sys.modules.copy()

    # Remove any cached imports
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith("core.rag")]
    for mod in modules_to_remove:
        del sys.modules[mod]

    def mock_import(name, *args, **kwargs):
        if name == "core.rag.simple_rag":
            raise ImportError("No module named 'core.rag'")
        return original_import(name, *args, **kwargs)

    original_import = __builtins__["__import__"]
    __builtins__["__import__"] = mock_import

    try:
        response = client.get("/api/v1/rag/stats", headers={"X-API-Key": "test_key"})
        assert response.status_code in (500, 503)
        data = response.json()
        assert "error" in data or "detail" in data
    finally:
        # Restore original import
        __builtins__["__import__"] = original_import
        sys.modules.update(original_modules)


def test_rag_stats_endpoint_disabled(client) -> None:
    response = client.get("/api/v1/rag/stats", headers={"X-API-Key": "test_key"})
    assert response.status_code == 200

    data = response.json()
    assert data["enabled"] is False


def test_rag_toggle_endpoint_success(client) -> None:
    response = client.post(
        "/api/v1/rag/toggle", json={"enabled": True}, headers={"X-API-Key": "test_key"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["enabled"] is True


def test_rag_toggle_endpoint_invalid_data(client) -> None:
    response = client.post(
        "/api/v1/rag/toggle",
        json={"enabled": "not_a_boolean"},
        headers={"X-API-Key": "test_key"},
    )
    assert response.status_code == 422  # Pydantic returns 422 for validation errors


def test_rag_toggle_endpoint_missing_enabled(client) -> None:
    response = client.post("/api/v1/rag/toggle", json={}, headers={"X-API-Key": "test_key"})
    assert response.status_code == 422  # Pydantic validation error


def test_rag_toggle_endpoint_unauthorized(client) -> None:
    response = client.post("/api/v1/rag/toggle", json={"enabled": True})
    assert response.status_code == 403  # API key validation returns 403


def test_rag_stats_endpoint_unauthorized(client) -> None:
    response = client.get("/api/v1/rag/stats")
    assert response.status_code == 403  # API key validation returns 403


def test_rag_toggle_override_persistence(client) -> None:
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

    # Reset override to avoid affecting other tests
    import app

    app._rag_enabled_override = None
