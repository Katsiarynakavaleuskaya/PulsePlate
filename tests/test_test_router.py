"""Tests for the test router endpoints."""

import importlib
import os
import sys
from datetime import datetime
from typing import Iterator, cast
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_app() -> FastAPI:
    """Reload app module to respect current environment variables."""
    module_name = "app"
    if module_name in sys.modules:
        del sys.modules[module_name]

    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        pytest.fail(
            f"Failed to import module '{module_name}': {e}. "
            f"Check import-time side effects and ensure all dependencies are available. "
            f"Environment: APP_ENV={os.environ.get('APP_ENV', 'not set')}"
        )
    except Exception as e:
        pytest.fail(
            f"Unexpected error importing module '{module_name}': {type(e).__name__}: {e}. "
            f"Check import-time side effects and module initialization. "
            f"Environment: APP_ENV={os.environ.get('APP_ENV', 'not set')}"
        )

    if not hasattr(module, "app"):
        raise AttributeError(
            f"Module '{module_name}' does not have 'app' attribute after import. "
            f"This may indicate an import-time failure or missing initialization. "
            f"Check import-time side effects and ensure the module initializes 'app' correctly."
        )

    return cast(FastAPI, module.app)


@pytest.fixture
def mock_env_staging() -> Iterator[None]:
    """Mock environment to staging for test router inclusion."""
    with patch.dict(os.environ, {"APP_ENV": "staging"}):
        yield


@pytest.fixture
def mock_env_production() -> Iterator[None]:
    """Mock environment to production to exclude test router."""
    with patch.dict(os.environ, {"APP_ENV": "production"}):
        yield


@pytest.fixture
def staging_client(mock_env_staging: Iterator[None]) -> TestClient:
    """Return a TestClient with a freshly reloaded app module for staging environment."""
    return TestClient(_load_app())


@pytest.fixture
def production_client(mock_env_production: Iterator[None]) -> TestClient:
    """Return a TestClient with a freshly reloaded app module for production environment."""
    return TestClient(_load_app())


def test_rate_limit_endpoint(staging_client: TestClient) -> None:
    """Test the rate limit endpoint returns expected response."""
    response = staging_client.post("/api/v1/test/rate-limit")

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


def test_health_endpoint(staging_client: TestClient) -> None:
    """Test the health check endpoint."""
    response = staging_client.get("/api/v1/test/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["message"] == "Test endpoints are operational"
    assert "timestamp" in data

    # Check custom header
    assert "x-test-timestamp" in response.headers


def test_echo_endpoint(staging_client: TestClient) -> None:
    """Test the echo endpoint returns sent data."""
    test_data = {"test_key": "test_value", "nested": {"key": "value"}, "array": [1, 2, 3]}

    response = staging_client.post("/api/v1/test/echo", json=test_data)

    assert response.status_code == 200
    data = response.json()

    assert "echo" in data
    assert data["echo"] == test_data

    assert "metadata" in data
    assert data["metadata"]["endpoint"] == "echo"
    assert "timestamp" in data["metadata"]

    # Check custom header
    assert "x-test-timestamp" in response.headers


def test_rate_limit_with_cf_ray_header(staging_client: TestClient) -> None:
    """Test rate limit endpoint captures Cloudflare ray ID."""
    cf_ray_id = "test-cf-ray-123"
    response = staging_client.post("/api/v1/test/rate-limit", headers={"cf-ray": cf_ray_id})

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == cf_ray_id


def test_rate_limit_with_request_id_header(staging_client: TestClient) -> None:
    """Test rate limit endpoint captures generic request ID."""
    request_id = "test-request-456"
    response = staging_client.post("/api/v1/test/rate-limit", headers={"x-request-id": request_id})

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == request_id


def test_test_router_not_available_in_production(production_client: TestClient) -> None:
    """Test that test endpoints are not available in production."""
    # Test endpoints should return 404 in production
    response = production_client.post("/api/v1/test/rate-limit")
    assert response.status_code == 404

    response = production_client.get("/api/v1/test/health")
    assert response.status_code == 404

    response = production_client.post("/api/v1/test/echo", json={"test": "data"})
    assert response.status_code == 404
