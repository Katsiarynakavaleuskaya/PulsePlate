"""Tests for the test router endpoints."""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os


@pytest.fixture
def mock_env_staging():
    """Mock environment to staging for test router inclusion."""
    with patch.dict(os.environ, {"APP_ENV": "staging"}):
        yield


@pytest.fixture
def mock_env_production():
    """Mock environment to production to exclude test router."""
    with patch.dict(os.environ, {"APP_ENV": "production"}):
        yield


def test_rate_limit_endpoint(mock_env_staging):
    """Test the rate limit endpoint returns expected response."""
    # Import app after setting environment
    from app import app

    client = TestClient(app)

    response = client.post("/api/v1/test/rate-limit")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["message"] == "Rate limit test endpoint"
    assert "timestamp" in data

    # Check timestamp is valid ISO format
    timestamp = datetime.fromisoformat(data["timestamp"])
    assert timestamp is not None

    # Check custom headers
    assert "x-test-timestamp" in response.headers
    assert "x-test-endpoint" in response.headers
    assert response.headers["x-test-endpoint"] == "rate-limit"


def test_health_endpoint(mock_env_staging):
    """Test the health check endpoint."""
    from app import app

    client = TestClient(app)

    response = client.get("/api/v1/test/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["message"] == "Test endpoints are operational"
    assert "timestamp" in data

    # Check custom header
    assert "x-test-timestamp" in response.headers


def test_echo_endpoint(mock_env_staging):
    """Test the echo endpoint returns sent data."""
    from app import app

    client = TestClient(app)

    test_data = {"test_key": "test_value", "nested": {"key": "value"}, "array": [1, 2, 3]}

    response = client.post("/api/v1/test/echo", json=test_data)

    assert response.status_code == 200
    data = response.json()

    assert "echo" in data
    assert data["echo"] == test_data

    assert "metadata" in data
    assert data["metadata"]["endpoint"] == "echo"
    assert "timestamp" in data["metadata"]

    # Check custom header
    assert "x-test-timestamp" in response.headers


def test_rate_limit_with_cf_ray_header(mock_env_staging):
    """Test rate limit endpoint captures Cloudflare ray ID."""
    from app import app

    client = TestClient(app)

    cf_ray_id = "test-cf-ray-123"
    response = client.post("/api/v1/test/rate-limit", headers={"cf-ray": cf_ray_id})

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == cf_ray_id


def test_rate_limit_with_request_id_header(mock_env_staging):
    """Test rate limit endpoint captures generic request ID."""
    from app import app

    client = TestClient(app)

    request_id = "test-request-456"
    response = client.post("/api/v1/test/rate-limit", headers={"x-request-id": request_id})

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == request_id


def test_test_router_not_available_in_production(mock_env_production):
    """Test that test endpoints are not available in production."""
    # Need to reimport app after environment change
    import importlib
    import sys

    # Remove app from cache to force reimport with new env
    if "app" in sys.modules:
        del sys.modules["app"]

    from app import app

    client = TestClient(app)

    # Test endpoints should return 404 in production
    response = client.post("/api/v1/test/rate-limit")
    assert response.status_code == 404

    response = client.get("/api/v1/test/health")
    assert response.status_code == 404

    response = client.post("/api/v1/test/echo", json={"test": "data"})
    assert response.status_code == 404
