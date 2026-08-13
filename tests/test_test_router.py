"""Tests for the test router endpoints."""

import json
import os
import subprocess
import sys
import textwrap
from datetime import datetime
from typing import Any

import pytest


def _request_from_fresh_app(
    method: str,
    path: str,
    *,
    json_body: object | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Make one request against a canonical app imported in a fresh process."""

    scenario = textwrap.dedent("""
        import json
        import sys
        from fastapi.testclient import TestClient
        from app.main import app

        request = json.loads(sys.argv[1])
        response = TestClient(app).request(
            request["method"],
            request["path"],
            json=request["json_body"],
            headers=request["headers"],
        )
        try:
            body = response.json()
        except ValueError:
            body = response.text
        print("TEST_ROUTER_RESULT=" + json.dumps({
            "status_code": response.status_code,
            "body": body,
            "headers": dict(response.headers),
        }, sort_keys=True))
        """)
    request = json.dumps(
        {
            "method": method,
            "path": path,
            "json_body": json_body,
            "headers": headers or {},
        }
    )
    env = os.environ.copy()
    env["PRIVATE_EXPORTS_ENABLED"] = "false"
    completed = subprocess.run(
        [sys.executable, "-c", scenario, request],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result_line = next(
        line for line in completed.stdout.splitlines() if line.startswith("TEST_ROUTER_RESULT=")
    )
    result: dict[str, Any] = json.loads(result_line.removeprefix("TEST_ROUTER_RESULT="))
    return result


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
    response = _request_from_fresh_app("POST", "/api/v1/test/rate-limit")

    assert response["status_code"] == 200
    data = response["body"]

    assert data["status"] == "ok"
    assert data["message"] == "Rate limit test endpoint"
    assert "timestamp" in data

    # Check timestamp is valid ISO format
    timestamp = datetime.fromisoformat(data["timestamp"])
    assert timestamp is not None

    # Check custom headers
    assert "x-test-timestamp" in response["headers"]
    assert "x-test-endpoint" in response["headers"]
    assert response["headers"]["x-test-endpoint"] == "rate-limit"


def test_health_endpoint(mock_env_staging):
    """Test the health check endpoint."""
    response = _request_from_fresh_app("GET", "/api/v1/test/health")

    assert response["status_code"] == 200
    data = response["body"]

    assert data["status"] == "healthy"
    assert data["message"] == "Test endpoints are operational"
    assert "timestamp" in data

    # Check custom header
    assert "x-test-timestamp" in response["headers"]


def test_echo_endpoint(mock_env_staging):
    """Test the echo endpoint returns sent data."""
    test_data = {"test_key": "test_value", "nested": {"key": "value"}, "array": [1, 2, 3]}

    response = _request_from_fresh_app("POST", "/api/v1/test/echo", json_body=test_data)

    assert response["status_code"] == 200
    data = response["body"]

    assert "echo" in data
    assert data["echo"] == test_data

    assert "metadata" in data
    assert data["metadata"]["endpoint"] == "echo"
    assert "timestamp" in data["metadata"]

    # Check custom header
    assert "x-test-timestamp" in response["headers"]


@pytest.mark.xdist_group(name="rate_limit")
def test_rate_limit_with_cf_ray_header(mock_env_staging):
    """Test rate limit endpoint captures Cloudflare ray ID."""
    cf_ray_id = "test-cf-ray-123"
    response = _request_from_fresh_app(
        "POST", "/api/v1/test/rate-limit", headers={"cf-ray": cf_ray_id}
    )

    assert response["status_code"] == 200
    data = response["body"]
    assert data["request_id"] == cf_ray_id


def test_rate_limit_with_request_id_header(mock_env_staging):
    """Test rate limit endpoint captures generic request ID."""
    request_id = "test-request-456"
    response = _request_from_fresh_app(
        "POST", "/api/v1/test/rate-limit", headers={"x-request-id": request_id}
    )

    assert response["status_code"] == 200
    data = response["body"]
    assert data["request_id"] == request_id


def test_test_router_not_available_in_production(mock_env_production):
    """Test that test endpoints are not available in production."""
    # Test endpoints should return 404 in production
    response = _request_from_fresh_app("POST", "/api/v1/test/rate-limit")
    assert response["status_code"] == 404

    response = _request_from_fresh_app("GET", "/api/v1/test/health")
    assert response["status_code"] == 404

    response = _request_from_fresh_app("POST", "/api/v1/test/echo", json_body={"test": "data"})
    assert response["status_code"] == 404


def test_test_router_not_available_in_staging_by_default(mock_env_staging_disabled):
    """Test that test endpoints are not available in staging unless explicitly enabled."""
    response = _request_from_fresh_app("GET", "/api/v1/test/health")
    assert response["status_code"] == 404
