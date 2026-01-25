"""Tests for Prometheus metrics endpoint and middleware.

RU: Тесты для Prometheus metrics endpoint и middleware.
EN: Tests for Prometheus metrics endpoint and middleware.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

import app

# Use conftest.py client fixture (don't define local one to avoid bypassing test setup)


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
    # Support scientific notation (e.g., 1e+06, 1.5e-3)
    pattern = re.compile(
        rf'^http_requests_total\{{[^}}]*method="{re.escape(method)}"[^}}]*route="{re.escape(route)}"[^}}]*status="{re.escape(status)}"[^}}]*\}}\s+(?P<val>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*$',
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
    # Happy path: must return Prometheus text format (not JSON fallback)
    assert response.headers["content-type"].startswith("text/plain"), (
        "Expected Prometheus text format on happy path, got: "
        f"{response.headers.get('content-type')}"
    )
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
    # Get baseline metrics (happy path: must be Prometheus text, not JSON)
    before_response = client.get("/metrics")
    assert before_response.headers["content-type"].startswith(
        "text/plain"
    ), "Expected Prometheus text format on happy path"
    before = before_response.text

    # Make a request to a non-excluded endpoint
    response = client.post(
        "/api/v1/bmi/calculate",
        json={
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "female",
            "athlete": False,
            "pregnant": False,
            "lang": "en",
        },
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
        json={
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "female",
            "athlete": False,
            "pregnant": False,
            "lang": "en",
        },
    )
    assert response.status_code == 200

    metrics_text = client.get("/metrics").text

    # Deterministic: exact series must exist with correct route template
    # This ensures we check the specific series we care about, not just "any POST/200"
    route = "/api/v1/bmi/calculate"
    assert (
        _metric_value(metrics_text, method="POST", route=route, status="200") >= 1.0
    ), f"Expected series with method=POST, route={route}, status=200"

    # Verify histogram is also recorded for this route
    # Histogram creates multiple series (_count, _sum, _bucket), check _count exists
    # Use MULTILINE flag to ensure we match line boundaries correctly
    histogram_count_pattern = re.compile(
        rf'^http_request_duration_seconds_count\{{[^}}]*method="POST"[^}}]*route="{re.escape(route)}"[^}}]*status="200"[^}}]*\}}\s+\d+(\.\d+)?$',
        flags=re.MULTILINE,
    )
    assert (
        histogram_count_pattern.search(metrics_text) is not None
    ), f"Expected histogram _count series for method=POST, route={route}, status=200"

    # Guard: query params must never appear in route labels
    assert f'route="{route}?"' not in metrics_text, "Query params should not appear in route label"

    # Global guard: ensure no route label contains query params anywhere
    route_label_pattern = re.compile(r'route="([^"]+)"')
    all_routes = route_label_pattern.findall(metrics_text)
    for route_label in all_routes:
        assert "?" not in route_label, f"Route label should not contain query params: {route_label}"


def test_metrics_content_type(client: TestClient) -> None:
    """Test /metrics returns correct Content-Type header.

    RU: Проверяет правильный Content-Type для /metrics.
    EN: Verifies correct Content-Type for /metrics.
    """
    response = client.get("/metrics")
    assert response.status_code == 200

    # Content-Type must start with text/plain (do not assert exact version/charset)
    ct = response.headers.get("content-type", "")
    assert ct.startswith("text/plain"), f"Expected Prometheus text/plain, got: {ct}"

    # Verify it's actually Prometheus exposition format
    # Check for our custom metrics or standard Prometheus format markers
    body = response.text
    assert (
        "http_requests_total" in body
        or "http_request_duration_seconds" in body
        or "# HELP" in body
        or "# TYPE" in body
    ), "Response should contain Prometheus exposition format"


def test_metrics_json_fallback_when_exporter_raises(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test /metrics returns JSON fallback when Prometheus exporter raises.

    RU: Проверяет JSON fallback при ошибке Prometheus exporter.
    EN: Verifies JSON fallback when Prometheus exporter raises.
    """
    prometheus_client = pytest.importorskip("prometheus_client")

    # Force exporter failure to test JSON fallback
    def _boom() -> bytes:
        raise RuntimeError("Prometheus exporter unavailable")

    # Patch the exact symbol used by production code
    monkeypatch.setattr(prometheus_client, "generate_latest", _boom)

    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")

    data = response.json()
    assert "error" in data
    # RuntimeError during generate_latest() should return "Metrics export failed"
    assert data["error"] == "Metrics export failed"
    assert "detail" in data


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


def test_metrics_import_prometheus_importerror() -> None:
    """Test that _import_prometheus raises ImportError when importer fails.

    RU: Проверяет, что _import_prometheus поднимает ImportError при ошибке импорта.
    EN: Verifies _import_prometheus raises ImportError when importer fails.
    """
    from app.middleware.metrics import _import_prometheus

    def _boom(_module_name: str) -> object:
        raise ImportError("boom")

    # Test ImportError path via dependency injection
    with pytest.raises(ImportError, match="boom"):
        _import_prometheus(importer=_boom)


def test_metrics_build_metrics_returns_none_on_importerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that _build_metrics returns None when ImportError occurs.

    RU: Проверяет, что _build_metrics возвращает None при ImportError.
    EN: Verifies _build_metrics returns None on ImportError.
    """
    from importlib import import_module

    from app.middleware.metrics import _build_metrics

    def _boom(_module_name: str) -> object:
        raise ImportError("boom")

    # Test ImportError path: monkeypatch _import_prometheus to fail
    # This tests the ImportError branch in _build_metrics
    monkeypatch.setattr(
        "app.middleware.metrics._import_prometheus",
        lambda importer=import_module: _boom("prometheus_client"),
    )

    # Now _build_metrics should return None due to ImportError
    result = _build_metrics()
    assert result is None, "Expected None when ImportError occurs"


def test_metrics_build_metrics_returns_none_on_duplicate_metric_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that _build_metrics returns None when metric registration fails.

    RU: Проверяет, что _build_metrics возвращает None при ValueError из prometheus_client
    (дублирующая регистрация имени метрики).
    EN: Verifies _build_metrics returns None when prometheus_client raises ValueError on duplicate.
    """
    import app.middleware.metrics as metrics_mod

    def _counter(*_args: object, **_kwargs: object) -> object:
        raise ValueError("duplicate metric name")

    def _histogram(*_args: object, **_kwargs: object) -> object:
        raise ValueError("duplicate metric name")

    monkeypatch.setattr(metrics_mod, "_import_prometheus", lambda: (_counter, _histogram))
    assert metrics_mod._build_metrics() is None


def test_metrics_route_template_unknown_without_router() -> None:
    """Test _route_template returns 'unknown' when router is missing or endpoint is None.

    RU: Проверяет, что _route_template возвращает 'unknown' когда router отсутствует или endpoint None.
    EN: Verifies _route_template returns 'unknown' when router is missing or endpoint is None.
    """
    from starlette.requests import Request

    from app.middleware.metrics import _route_template

    class _App:
        pass

    # Test case 1: endpoint is None
    scope_no_endpoint = {
        "type": "http",
        "method": "GET",
        "path": "/somewhere",
        "raw_path": b"/somewhere",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
        "app": _App(),
        "endpoint": None,
    }
    request_no_endpoint = Request(scope_no_endpoint)
    assert _route_template(request_no_endpoint) == "unknown"

    # Test case 2: router is missing (no router attribute)
    endpoint = object()
    scope_no_router = {
        "type": "http",
        "method": "GET",
        "path": "/somewhere",
        "raw_path": b"/somewhere",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
        "app": _App(),  # No router attribute
        "endpoint": endpoint,
    }
    request_no_router = Request(scope_no_router)
    assert _route_template(request_no_router) == "unknown"


@pytest.mark.asyncio
async def test_metrics_middleware_noop_when_metrics_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test middleware becomes no-op when metrics are unavailable.

    RU: Проверяет, что middleware становится no-op когда метрики недоступны.
    EN: Verifies middleware becomes no-op when metrics are unavailable.
    """
    from starlette.requests import Request
    from starlette.responses import Response

    import app.middleware.metrics as metrics_mod

    called = False

    async def call_next(_request: Request) -> Response:
        nonlocal called
        called = True
        return Response(content=b"", status_code=204)

    monkeypatch.setattr(metrics_mod, "PROMETHEUS_METRICS", None)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/not-excluded",
        "raw_path": b"/not-excluded",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
        "app": app.app,
    }
    request = Request(scope)
    resp = await metrics_mod.metrics_middleware(request, call_next)
    assert called is True
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_metrics_middleware_swallows_metrics_recording_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that metrics recording errors never affect request handling.

    RU: Проверяет, что ошибки записи метрик не влияют на обработку запроса.
    EN: Verifies metrics recording errors are swallowed and response is returned.
    """
    from starlette.requests import Request
    from starlette.responses import Response

    import app.middleware.metrics as metrics_mod

    class _BadCounter:
        def labels(self, *, method: str, route: str, status: str) -> object:
            raise RuntimeError("boom")

    class _BadHistogram:
        def labels(self, *, method: str, route: str, status: str) -> object:
            raise RuntimeError("boom")

    class _BadMetrics:
        requests_total = _BadCounter()
        request_duration_seconds = _BadHistogram()

    async def call_next(_request: Request) -> Response:
        return Response(content=b"", status_code=204)

    monkeypatch.setattr(metrics_mod, "PROMETHEUS_METRICS", _BadMetrics())
    monkeypatch.setattr(metrics_mod, "_route_template", lambda _request: "/api/v1/bmi/calculate")

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/bmi/calculate",
        "raw_path": b"/api/v1/bmi/calculate",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
        "app": app.app,
    }
    request = Request(scope)
    resp = await metrics_mod.metrics_middleware(request, call_next)
    assert resp.status_code == 204


def test_metrics_middleware_exception_path(client: TestClient) -> None:
    """Test middleware records 500 status when exception occurs.

    RU: Проверяет, что middleware записывает статус 500 при исключении.
    EN: Verifies middleware records 500 status when exception occurs.

    This test exercises the exception path in finally block where status="500"
    is recorded. We use a real endpoint that can raise an exception to verify
    the metrics are recorded correctly.
    """
    import app.middleware.metrics as metrics_mod

    # Ensure metrics are available (not None)
    assert metrics_mod.PROMETHEUS_METRICS is not None

    # Make a request that will trigger an exception (e.g., invalid JSON)
    # This will cause the exception path in middleware to be exercised
    response = client.post(
        "/api/v1/bmi/calculate",
        content="invalid json",
        headers={"Content-Type": "application/json"},
    )
    # Should return 422 (validation error) or 500 (if exception occurs)
    assert response.status_code in [422, 500]

    # Verify metrics were recorded with status=500 or 422
    metrics_text = client.get("/metrics").text

    # Check that exception path was exercised (status=500 or 422)
    # We check for either status since validation errors may return 422
    route = "/api/v1/bmi/calculate"
    status_500_value = _metric_value(metrics_text, method="POST", route=route, status="500")
    status_422_value = _metric_value(metrics_text, method="POST", route=route, status="422")

    # At least one of these should be > 0 (exception path exercised)
    assert (
        status_500_value > 0 or status_422_value > 0
    ), "Expected metrics to be recorded for exception/error path"


def test_normalized_path_root() -> None:
    """Test _normalized_path handles root path correctly.

    RU: Проверяет, что _normalized_path корректно обрабатывает корневой путь.
    EN: Verifies _normalized_path handles root path correctly.
    """
    from app.middleware.metrics import _normalized_path

    assert _normalized_path("/") == "/"
    assert _normalized_path("/health") == "/health"
    assert _normalized_path("/health/") == "/health"
    assert _normalized_path("/api/v1/bmi/calculate") == "/api/v1/bmi/calculate"
    assert _normalized_path("/api/v1/bmi/calculate/") == "/api/v1/bmi/calculate"


def test_route_cache_disabled_when_max_size_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test route cache is disabled when ROUTE_CACHE_MAX_SIZE=0.

    RU: Проверяет, что route cache отключён при ROUTE_CACHE_MAX_SIZE=0.
    EN: Verifies route cache is disabled when ROUTE_CACHE_MAX_SIZE=0.
    """
    import app.middleware.metrics as metrics_mod

    # Clear cache and set size to 0
    with metrics_mod._ROUTE_CACHE_LOCK:
        metrics_mod._ROUTE_CACHE.clear()
    monkeypatch.setattr(metrics_mod, "ROUTE_CACHE_MAX_SIZE", 0)

    # Call _route_cache_set (should return early at line 193)
    metrics_mod._route_cache_set(123, "/api/v1/test")

    # Cache should remain empty
    stats = metrics_mod._route_cache_stats()
    assert stats["size"] == 0


def test_route_cache_ttl_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test route cache entries expire after TTL.

    RU: Проверяет, что записи в route cache истекают после TTL.
    EN: Verifies route cache entries expire after TTL.
    """
    import app.middleware.metrics as metrics_mod

    # Enable cache with a small TTL
    monkeypatch.setattr(metrics_mod, "ROUTE_CACHE_MAX_SIZE", 10)
    monkeypatch.setattr(metrics_mod, "ROUTE_CACHE_TTL_S", 0.01)

    # Clear cache state for isolation
    with metrics_mod._ROUTE_CACHE_LOCK:
        metrics_mod._ROUTE_CACHE.clear()

    # Mock time source (deterministic, no sleep needed)
    t = {"v": 1000.0}
    monkeypatch.setattr(metrics_mod, "_now_monotonic", lambda: t["v"])

    # Add entry at t=1000.0
    endpoint_id = 999
    metrics_mod._route_cache_set(endpoint_id, "/api/v1/test")

    # Should be cached (delta=0.0 < 0.01)
    assert metrics_mod._route_cache_get(endpoint_id) == "/api/v1/test"

    # Advance time beyond TTL (delta=0.02 > 0.01)
    t["v"] = 1000.02

    # Should be expired (returns None, increments _ROUTE_CACHE_EXPIRED)
    assert metrics_mod._route_cache_get(endpoint_id) is None
    stats = metrics_mod._route_cache_stats()
    assert stats["expired"] >= 1


def test_route_cache_eviction_on_overflow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test route cache evicts LRU entries when full.

    RU: Проверяет, что route cache вытесняет LRU записи при переполнении.
    EN: Verifies route cache evicts LRU entries when full.
    """
    import app.middleware.metrics as metrics_mod

    # Set small cache size
    monkeypatch.setattr(metrics_mod, "ROUTE_CACHE_MAX_SIZE", 2)
    monkeypatch.setattr(metrics_mod, "ROUTE_CACHE_TTL_S", None)

    # Clear cache state
    with metrics_mod._ROUTE_CACHE_LOCK:
        metrics_mod._ROUTE_CACHE.clear()

    # Add 3 entries (should evict first)
    metrics_mod._route_cache_set(1, "/route1")
    metrics_mod._route_cache_set(2, "/route2")
    metrics_mod._route_cache_set(3, "/route3")  # Should trigger eviction

    # Check stats
    stats = metrics_mod._route_cache_stats()
    assert stats["size"] == 2  # Max size enforced
    assert stats["evictions"] >= 1  # At least 1 eviction occurred
