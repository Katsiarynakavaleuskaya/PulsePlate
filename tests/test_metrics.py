"""Tests for Prometheus metrics endpoint and middleware.

RU: Тесты для Prometheus metrics endpoint и middleware.
EN: Tests for Prometheus metrics endpoint and middleware.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from prometheus_client import CONTENT_TYPE_LATEST

import app


@pytest.fixture
def client() -> TestClient:
    """Test client for metrics tests."""
    return TestClient(app.app)


def _metric_value(text: str, *, method: str, route: str, status: str) -> float:
    """Extract metric value for specific labelset from Prometheus text format.

    Args:
        text: Prometheus exposition format text
        method: HTTP method (e.g., "GET", "POST")
        route: Route template (e.g., "/api/v1/bmi/calculate")
        status: HTTP status code (e.g., "200", "404")

    Returns:
        Metric value (0.0 if not found)
    """
    # Example line:
    # http_requests_total{method="GET",route="/api/v1/bmi/calculate",status="200"} 3.0
    pattern = re.compile(
        rf'^http_requests_total\{{[^}}]*method="{re.escape(method)}"[^}}]*route="{re.escape(route)}"[^}}]*status="{re.escape(status)}"[^}}]*\}}\s+(?P<val>[0-9.]+)\s*$',
        re.MULTILINE,
    )
    match = pattern.search(text)
    if match:
        return float(match.group("val"))
    return 0.0


def test_metrics_endpoint_format(client: TestClient) -> None:
    """Test /metrics returns Prometheus exposition format.

    RU: Проверяет, что /metrics возвращает формат Prometheus.
    EN: Verifies /metrics returns Prometheus exposition format.
    """
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    # Prometheus format version may be in content-type or body
    content_type = response.headers.get("content-type", "")
    assert "text/plain" in content_type

    content = response.text
    # Should contain at least some Prometheus metrics
    assert "python_info" in content or "process_" in content or "http_requests_total" in content


def test_metrics_increments_on_request(client: TestClient) -> None:
    """Test that HTTP metrics are collected and exposed.

    RU: Проверяет, что HTTP метрики собираются и отдаются.
    EN: Verifies HTTP metrics are collected and exposed.
    """
    # Get baseline metrics
    before = client.get("/metrics").text

    # Make a request to a non-excluded endpoint
    response = client.post(
        "/api/v1/bmi/calculate",
        json={"weight_kg": 70, "height_cm": 175, "lang": "en", "sex": "female", "age": 30},
    )
    assert response.status_code == 200

    # Get metrics after request
    after = client.get("/metrics").text

    # Verify counter increased
    v0 = _metric_value(before, method="POST", route="/api/v1/bmi/calculate", status="200")
    v1 = _metric_value(after, method="POST", route="/api/v1/bmi/calculate", status="200")
    assert v1 >= v0 + 1, f"Expected counter to increase: {v0} -> {v1}"

    # Verify histogram samples are also present
    assert "http_request_duration_seconds" in after, "Histogram metric should be present"


def test_metrics_excludes_health_endpoints(client: TestClient) -> None:
    """Test that /health and /ready are excluded from metrics.

    RU: Проверяет, что /health и /ready исключены из метрик.
    EN: Verifies /health and /ready are excluded from metrics.
    """
    # Make requests to excluded endpoints
    client.get("/health")
    client.get("/ready")
    # /health/db may return 200 or 503 depending on DB availability
    health_db_response = client.get("/health/db")
    assert health_db_response.status_code in (200, 503)

    # Get metrics after requests
    metrics = client.get("/metrics").text

    # Excluded endpoints should not appear as route label values
    # This is a stronger check than before/after comparison: we verify no series exist
    assert 'route="/metrics"' not in metrics, "Excluded /metrics should not appear in route labels"
    assert 'route="/health"' not in metrics, "Excluded /health should not appear in route labels"
    assert 'route="/ready"' not in metrics, "Excluded /ready should not appear in route labels"
    assert (
        'route="/health/db"' not in metrics
    ), "Excluded /health/db should not appear in route labels"


def test_metrics_includes_route_template(client: TestClient) -> None:
    """Test that metrics include route template (not raw path).

    RU: Проверяет, что метрики содержат route template, а не raw path.
    EN: Verifies metrics include route template, not raw path.
    """
    # Make a request with query params to verify route template (not raw path)
    response = client.post(
        "/api/v1/bmi/calculate?foo=bar&baz=qux",
        json={"weight_kg": 70, "height_cm": 175, "lang": "en", "sex": "female", "age": 30},
    )
    assert response.status_code == 200

    metrics_text = client.get("/metrics").text

    # Verify route label for specific labelset (method + route + status) doesn't contain query params
    # Pattern: http_requests_total{method="POST",route="/api/v1/bmi/calculate",status="200"} ...
    # Extract route value from the specific series we care about
    labelset_pattern = re.compile(
        r'http_requests_total\{[^}]*method="POST"[^}]*route="([^"]+)"[^}]*status="200"[^}]*\}'
    )
    match = labelset_pattern.search(metrics_text)
    assert (
        match is not None
    ), "Expected series with method=POST, route=/api/v1/bmi/calculate, status=200"

    route_value = match.group(1)
    assert route_value == "/api/v1/bmi/calculate", f"Route should be template, got: {route_value}"
    assert "?" not in route_value, f"Route label should not contain query params: {route_value}"

    # Global guard: ensure no route label contains query params anywhere
    route_label_pattern = re.compile(r'route="([^"]+)"')
    all_routes = route_label_pattern.findall(metrics_text)
    for route in all_routes:
        assert "?" not in route, f"Route label should not contain query params: {route}"


def test_metrics_content_type(client: TestClient) -> None:
    """Test /metrics returns correct Content-Type header.

    RU: Проверяет правильный Content-Type для /metrics.
    EN: Verifies correct Content-Type for /metrics.
    """
    response = client.get("/metrics")
    assert response.status_code == 200
    # Content-Type must match prometheus_client.CONTENT_TYPE_LATEST exactly
    assert response.headers["content-type"] == CONTENT_TYPE_LATEST
    # Prometheus format should have # HELP or # TYPE comments
    assert "# HELP" in response.text or "# TYPE" in response.text


def test_metrics_hidden_from_openapi(client: TestClient) -> None:
    """Test /metrics is not in OpenAPI schema.

    RU: Проверяет, что /metrics не в OpenAPI схеме.
    EN: Verifies /metrics is not in OpenAPI schema.
    """
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})
    # /metrics should not be in OpenAPI paths (include_in_schema=False)
    assert "/metrics" not in paths
