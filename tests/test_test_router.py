"""Tests for the test router endpoints."""

import json
import os
import subprocess
import sys
import textwrap
from datetime import datetime
from functools import cache
from typing import Any

import pytest

_Scenario = tuple[str, str, str]
_REQUESTS = {
    "rate-limit": ["POST", "/api/v1/test/rate-limit", None, {}],
    "health": ["GET", "/api/v1/test/health", None, {}],
    "echo": [
        "POST",
        "/api/v1/test/echo",
        {"test_key": "test_value", "nested": {"key": "value"}, "array": [1, 2, 3]},
        {},
    ],
    "cf-ray": ["POST", "/api/v1/test/rate-limit", None, {"cf-ray": "test-cf-ray-123"}],
    "request-id": ["POST", "/api/v1/test/rate-limit", None, {"x-request-id": "test-request-456"}],
}


@cache
def _run_fresh_scenario(scenario_key: _Scenario) -> dict[str, dict[str, Any]]:
    """Boot once and exercise every endpoint for one environment scenario."""

    scenario = textwrap.dedent("""
        import json, sys
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        results = {}
        for name, (method, path, body, headers) in json.loads(sys.argv[1]).items():
            response = client.request(method, path, json=body, headers=headers)
            results[name] = {
                "status_code": response.status_code,
                "body": response.json(),
                "headers": dict(response.headers),
            }
        print("TEST_ROUTER_RESULT=" + json.dumps(results, sort_keys=True))
    """)
    environment, app_env, enabled = scenario_key
    env = os.environ.copy()
    for name in ("APP_ENV", "ENVIRONMENT", "ENABLE_TEST_ROUTES"):
        env.pop(name, None)
    if environment:
        env["ENVIRONMENT"] = environment
    if app_env:
        env["APP_ENV"] = app_env
    if enabled:
        env["ENABLE_TEST_ROUTES"] = enabled
    env["PRIVATE_EXPORTS_ENABLED"] = "false"
    completed = subprocess.run(
        [sys.executable, "-c", scenario, json.dumps(_REQUESTS)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result_line = next(
        line for line in completed.stdout.splitlines() if line.startswith("TEST_ROUTER_RESULT=")
    )
    result: dict[str, dict[str, Any]] = json.loads(result_line.removeprefix("TEST_ROUTER_RESULT="))
    return result


def _import_fresh_app() -> _Scenario:
    return (
        os.getenv("ENVIRONMENT", ""),
        os.getenv("APP_ENV", ""),
        os.getenv("ENABLE_TEST_ROUTES", ""),
    )


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.status_code = payload["status_code"]
        self.headers = payload["headers"]
        self._body = payload["body"]

    def json(self) -> Any:
        return self._body


class _FreshProcessClient:
    def __init__(self, scenario_key: _Scenario) -> None:
        self._responses = _run_fresh_scenario(scenario_key)

    def post(
        self, path: str, *, json: object | None = None, headers: dict[str, str] | None = None
    ) -> _Response:
        del json
        key = "echo" if path.endswith("/echo") else "rate-limit"
        if headers and "cf-ray" in headers:
            key = "cf-ray"
        elif headers and "x-request-id" in headers:
            key = "request-id"
        return _Response(self._responses[key])

    def get(self, path: str) -> _Response:
        assert path.endswith("/health")
        return _Response(self._responses["health"])


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

    client = _FreshProcessClient(app)

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

    client = _FreshProcessClient(app)

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

    client = _FreshProcessClient(app)

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

    client = _FreshProcessClient(app)

    cf_ray_id = "test-cf-ray-123"
    response = client.post("/api/v1/test/rate-limit", headers={"cf-ray": cf_ray_id})

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == cf_ray_id


def test_rate_limit_with_request_id_header(mock_env_staging):
    """Test rate limit endpoint captures generic request ID."""
    app = _import_fresh_app()

    client = _FreshProcessClient(app)

    request_id = "test-request-456"
    response = client.post("/api/v1/test/rate-limit", headers={"x-request-id": request_id})

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == request_id


def test_test_router_not_available_in_production(mock_env_production):
    """Test that test endpoints are not available in production."""
    app = _import_fresh_app()

    client = _FreshProcessClient(app)

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
    client = _FreshProcessClient(app)

    response = client.get("/api/v1/test/health")
    assert response.status_code == 404
