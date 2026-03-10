"""Tests for the test router endpoints."""

import pytest
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
import os


def _import_fresh_app() -> FastAPI:
    """Import FastAPI app after ensuring env-based wiring is re-evaluated.

    RU: Перезагружаем legacy_app, чтобы он перечитал env и заново настроил wiring.
    EN: Reload legacy_app so it re-reads env and rebuilds router wiring.
    """
    # IMPORTANT:
    # `legacy_app` decides whether to include the test router at import time, based on env.
    # In CI, it may already be imported under a different APP_ENV/ENABLE_TEST_ROUTES state.
    # Reloading re-reads env and re-wires routers without mutating sys.modules.
    import importlib

    import legacy_app

    importlib.reload(legacy_app)

    app = legacy_app.app  # canonical app instance after env-driven wiring

    # Fail fast with a clear message if staging claims test routes should exist but doesn't.
    runtime_env = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "local").strip().lower()
    if runtime_env == "staging" and os.getenv("ENABLE_TEST_ROUTES") == "1":
        has_test_routes = any(
            getattr(route, "path", "").startswith("/api/v1/test/")
            for route in getattr(app, "routes", [])
        )
        assert has_test_routes, (
            "Test router routes are missing after legacy_app reload. "
            "runtime_env="
            f"{runtime_env}, APP_ENV={os.getenv('APP_ENV')}, "
            f"ENVIRONMENT={os.getenv('ENVIRONMENT')}, "
            f"ENABLE_TEST_ROUTES={os.getenv('ENABLE_TEST_ROUTES')}"
        )

    return app


@pytest.fixture
def mock_env_staging(monkeypatch: pytest.MonkeyPatch):
    """Mock environment to staging for test router inclusion.

    Note: Staging requires ENABLE_TEST_ROUTES=1 to include test endpoints
    for security (staging may be externally accessible).
    """
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("ENABLE_TEST_ROUTES", "1")
    yield


@pytest.fixture
def mock_env_production(monkeypatch: pytest.MonkeyPatch):
    """Mock environment to production to exclude test router."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    yield


@pytest.fixture
def mock_env_staging_disabled(monkeypatch: pytest.MonkeyPatch):
    """Mock environment to staging without explicit enable flag.

    RU: В staging тестовые ручки должны быть выключены по умолчанию.
    EN: In staging, test endpoints must be disabled by default.
    """
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.delenv("ENABLE_TEST_ROUTES", raising=False)
    yield


def test_rate_limit_endpoint(mock_env_staging):
    """Test the rate limit endpoint returns expected response."""
    app = _import_fresh_app()

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
    app = _import_fresh_app()

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
    app = _import_fresh_app()

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


@pytest.mark.xdist_group(name="rate_limit")
def test_rate_limit_with_cf_ray_header(mock_env_staging):
    """Test rate limit endpoint captures Cloudflare ray ID."""
    app = _import_fresh_app()

    client = TestClient(app)

    cf_ray_id = "test-cf-ray-123"
    response = client.post("/api/v1/test/rate-limit", headers={"cf-ray": cf_ray_id})

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == cf_ray_id


def test_rate_limit_with_request_id_header(mock_env_staging):
    """Test rate limit endpoint captures generic request ID."""
    app = _import_fresh_app()

    client = TestClient(app)

    request_id = "test-request-456"
    response = client.post("/api/v1/test/rate-limit", headers={"x-request-id": request_id})

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == request_id


def test_test_router_not_available_in_production(mock_env_production):
    """Test that test endpoints are not available in production."""
    app = _import_fresh_app()

    client = TestClient(app)

    # Test endpoints should return 404 in production
    response = client.post("/api/v1/test/rate-limit")
    assert response.status_code == 404

    response = client.get("/api/v1/test/health")
    assert response.status_code == 404

    response = client.post("/api/v1/test/echo", json={"test": "data"})
    assert response.status_code == 404


def test_test_router_not_available_in_staging_by_default(mock_env_staging_disabled):
    """Test that test endpoints are not available in staging unless explicitly enabled."""
    app = _import_fresh_app()
    client = TestClient(app)

    response = client.get("/api/v1/test/health")
    assert response.status_code == 404
