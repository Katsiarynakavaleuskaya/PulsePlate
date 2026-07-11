"""Tests for Prometheus metrics endpoint and middleware.

RU: Тесты для Prometheus metrics endpoint и middleware.
EN: Tests for Prometheus metrics endpoint and middleware.
"""

from __future__ import annotations

import asyncio
import re

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app
from app.bootstrap.metrics import register_metrics
from app.effective_routes import iter_effective_route_candidates, route_methods, route_path

# Use conftest.py client fixture (don't define local one to avoid bypassing test setup)


@pytest.fixture(autouse=True)
def _enable_metrics_client_auth(
    request: pytest.FixtureRequest,
) -> None:
    """Exercise `/metrics` happy paths through the real auth dependency."""
    if "client" not in request.fixturenames:
        return
    client = request.getfixturevalue("client")
    client.headers["X-API-Key"] = "test_key"


def _configure_metrics_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set deterministic auth env for guarded `/metrics` route tests."""
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("METRICS_TEST_BYPASS", "false")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("API_KEY_REQUIRED", "true")


def _get_metrics_get_routes(app_instance: FastAPI) -> list[object]:
    """Collect registered GET routes for the canonical /metrics endpoint."""

    return [
        route
        for route in iter_effective_route_candidates(app_instance.routes)
        if route_path(route) == "/metrics" and "GET" in route_methods(route)
    ]


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


def test_metrics_include_food_catalog_route_templates(client: TestClient) -> None:
    """Foods/catalog legacy-registration move must preserve route-template labels."""
    missing_food_id = "missing-food-id-for-metrics"

    food_response = client.get(f"/api/v1/foods/{missing_food_id}?debug_raw_path=true")
    assert food_response.status_code == 404

    catalog_response = client.get(
        "/api/v1/catalog/search",
        params={"q": "ban", "region_id": "ES", "limit": 1, "debug_raw_query": "true"},
    )
    assert catalog_response.status_code == 200

    metrics_text = client.get("/metrics").text

    assert (
        _metric_value(
            metrics_text,
            method="GET",
            route="/api/v1/foods/{food_id}",
            status="404",
        )
        >= 1.0
    )
    assert (
        _metric_value(
            metrics_text,
            method="GET",
            route="/api/v1/catalog/search",
            status="200",
        )
        >= 1.0
    )
    assert missing_food_id not in metrics_text
    assert "debug_raw_path" not in metrics_text
    assert "debug_raw_query" not in metrics_text
    assert 'route="/api/v1/catalog/search?' not in metrics_text


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


def test_register_metrics_adds_route_after_stack_is_built() -> None:
    """Late bootstrap must still restore /metrics without mutating middleware."""
    from starlette.testclient import TestClient as RawTestClient

    app_instance = FastAPI()

    @app_instance.get("/")
    def root() -> dict[str, str]:
        return {"status": "ok"}

    with RawTestClient(app_instance) as client:
        response = client.get("/")
        assert response.status_code == 200

    middleware_stack = getattr(app_instance, "middleware_stack", None)
    assert middleware_stack is not None
    before_user_middleware = len(getattr(app_instance, "user_middleware", []))

    register_metrics(app_instance)

    assert getattr(app_instance, "middleware_stack", None) is middleware_stack
    assert len(_get_metrics_get_routes(app_instance)) == 1
    assert len(getattr(app_instance, "user_middleware", [])) == before_user_middleware

    with RawTestClient(app_instance) as client:
        client.headers["X-API-Key"] = "test_key"
        metrics_response = client.get("/metrics")

    assert metrics_response.status_code == 200


def test_register_metrics_is_idempotent_for_route_registration() -> None:
    """Repeated bootstrap calls must not duplicate the /metrics route."""

    app_instance = FastAPI()

    register_metrics(app_instance)
    register_metrics(app_instance)

    assert len(_get_metrics_get_routes(app_instance)) == 1


def test_register_metrics_is_idempotent_after_stack_is_built() -> None:
    """Repeated late bootstrap must not duplicate the /metrics route."""
    from starlette.testclient import TestClient as RawTestClient

    app_instance = FastAPI()
    register_metrics(app_instance)

    with RawTestClient(app_instance) as client:
        client.headers["X-API-Key"] = "test_key"
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200

        register_metrics(app_instance)
        register_metrics(app_instance)

        assert len(_get_metrics_get_routes(app_instance)) == 1

        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200


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


def test_metrics_route_template_normalizes_trailing_slash_before_cache() -> None:
    from starlette.requests import Request

    from app.middleware.metrics import _route_template

    app_instance = FastAPI()

    @app_instance.get("/api/v1/slash/")
    async def _slash_route() -> dict[str, str]:
        return {"status": "ok"}

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/slash/",
        "raw_path": b"/api/v1/slash/",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
        "app": app_instance,
        "endpoint": _slash_route,
    }
    request = Request(scope)

    assert _route_template(request) == "/api/v1/slash"
    assert _route_template(request) == "/api/v1/slash"


def test_metrics_route_template_cache_is_app_scoped() -> None:
    from starlette.requests import Request

    import app.middleware.metrics as metrics_mod

    with metrics_mod._ROUTE_CACHE_LOCK:
        metrics_mod._ROUTE_CACHE.clear()

    async def _shared_route() -> dict[str, str]:
        return {"status": "ok"}

    first_app = FastAPI()
    second_app = FastAPI()
    first_app.add_api_route("/api/v1/cache/first", _shared_route, methods=["GET"])
    second_app.add_api_route("/api/v1/cache/second", _shared_route, methods=["GET"])

    def _request(app_instance: FastAPI, path: str) -> Request:
        return Request(
            {
                "type": "http",
                "method": "GET",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "headers": [],
                "client": ("testclient", 123),
                "server": ("testserver", 80),
                "scheme": "http",
                "http_version": "1.1",
                "app": app_instance,
                "endpoint": _shared_route,
            }
        )

    assert (
        metrics_mod._route_template(_request(first_app, "/api/v1/cache/first"))
        == "/api/v1/cache/first"
    )
    assert (
        metrics_mod._route_template(_request(second_app, "/api/v1/cache/second"))
        == "/api/v1/cache/second"
    )


def test_metrics_middleware_noop_when_metrics_unavailable(
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
    resp = asyncio.run(metrics_mod.metrics_middleware(request, call_next))
    assert called is True
    assert resp.status_code == 204


def test_metrics_middleware_swallows_metrics_recording_errors(
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
    resp = asyncio.run(metrics_mod.metrics_middleware(request, call_next))
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
    metrics_mod._route_cache_set((1, 123), "/api/v1/test")

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
    cache_key = (1, 999)
    metrics_mod._route_cache_set(cache_key, "/api/v1/test")

    # Should be cached (delta=0.0 < 0.01)
    assert metrics_mod._route_cache_get(cache_key) == "/api/v1/test"

    # Advance time beyond TTL (delta=0.02 > 0.01)
    t["v"] = 1000.02

    # Should be expired (returns None, increments _ROUTE_CACHE_EXPIRED)
    assert metrics_mod._route_cache_get(cache_key) is None
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
    metrics_mod._route_cache_set((1, 1), "/route1")
    metrics_mod._route_cache_set((1, 2), "/route2")
    metrics_mod._route_cache_set((1, 3), "/route3")  # Should trigger eviction

    # Check stats
    stats = metrics_mod._route_cache_stats()
    assert stats["size"] == 2  # Max size enforced
    assert stats["evictions"] >= 1  # At least 1 eviction occurred


def test_ws_observability_helpers_noop_when_metrics_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WS helper functions must be safe no-op when metrics are unavailable."""
    import app.middleware.metrics as metrics_mod

    monkeypatch.setattr(metrics_mod, "PROMETHEUS_METRICS", None)

    metrics_mod.record_ws_connect("/ws")
    metrics_mod.record_ws_message("/ws", direction="in")
    metrics_mod.inc_ws_active_connections("/ws")
    metrics_mod.dec_ws_active_connections("/ws")


def test_record_legacy_alias_hit_swallows_counter_inc_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """record_legacy_alias_hit must swallow Prometheus label/inc failures."""
    import app.metrics as app_metrics

    from app.metrics import LEGACY_NUTRITION_DATE_ROUTE_TEMPLATE as route

    class _BadChild:
        def inc(self, amount: float = 1.0) -> None:
            raise RuntimeError("boom")

    class _BadCounter:
        def labels(self, *, alias_route: str) -> _BadChild:
            assert alias_route == route
            return _BadChild()

    monkeypatch.setattr(app_metrics, "LEGACY_ALIAS_REQUESTS_TOTAL", _BadCounter())
    app_metrics.record_legacy_alias_hit(route)


def test_ws_observability_helpers_swallow_metrics_backend_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WS helper functions must not raise when labels/inc/dec fails."""
    import app.middleware.metrics as metrics_mod

    class _BadCounter:
        def labels(self, **_kwargs: object) -> object:
            raise RuntimeError("boom")

    class _BadGauge:
        def labels(self, **_kwargs: object) -> object:
            raise RuntimeError("boom")

    class _BadMetrics:
        ws_connect_total = _BadCounter()
        ws_messages_total = _BadCounter()
        ws_active_connections = _BadGauge()

    monkeypatch.setattr(metrics_mod, "PROMETHEUS_METRICS", _BadMetrics())

    metrics_mod.record_ws_connect("/ws")
    metrics_mod.record_ws_message("/ws", direction="out")
    metrics_mod.inc_ws_active_connections("/ws")
    metrics_mod.dec_ws_active_connections("/ws")


def test_metrics_guard_requires_api_key_outside_testing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """/metrics guard delegates to the shared API key guard outside test bypass."""
    from app.bootstrap import metrics as metrics_bootstrap

    _configure_metrics_auth_env(monkeypatch)

    assert metrics_bootstrap._metrics_api_key_guard("test_key") == "test_key"


def test_metrics_guard_bypasses_in_testing(monkeypatch: pytest.MonkeyPatch) -> None:
    """/metrics guard bypasses API key only in explicit pytest-scoped test mode."""
    from app.bootstrap import metrics as metrics_bootstrap

    monkeypatch.setenv("METRICS_TEST_BYPASS", "true")
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("APP_ENV", "test")

    assert metrics_bootstrap._metrics_api_key_guard(None) == "testing-bypass"


def test_metrics_guard_ignores_bypass_outside_pytest(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """/metrics guard ignores leaked bypass env outside pytest-scoped execution."""
    from app.bootstrap import metrics as metrics_bootstrap

    _configure_metrics_auth_env(monkeypatch)
    monkeypatch.setenv("METRICS_TEST_BYPASS", "true")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    with caplog.at_level("WARNING", logger="app.bootstrap.metrics"):
        result = metrics_bootstrap._metrics_api_key_guard("test_key")

    assert result == "test_key"
    assert "METRICS_TEST_BYPASS ignored outside explicit pytest test env" in caplog.text


def test_metrics_guard_ignores_bypass_outside_test_env(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """/metrics bypass must not activate in production-like envs even under pytest."""
    from app.bootstrap import metrics as metrics_bootstrap

    _configure_metrics_auth_env(monkeypatch)
    monkeypatch.setenv("METRICS_TEST_BYPASS", "true")

    with caplog.at_level("WARNING", logger="app.bootstrap.metrics"):
        result = metrics_bootstrap._metrics_api_key_guard("test_key")

    assert result == "test_key"
    assert "METRICS_TEST_BYPASS ignored outside explicit pytest test env" in caplog.text


def test_metrics_http_guard_rejects_missing_api_key_when_bypass_disabled(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """/metrics must reject requests without an API key when bypass is disabled."""
    _configure_metrics_auth_env(monkeypatch)
    setattr(client, "auto_metrics_api_key", False)
    client.headers.pop("X-API-Key", None)

    response = client.get("/metrics")

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/json")


def test_metrics_http_guard_allows_valid_api_key_when_bypass_disabled(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """/metrics must keep Prometheus happy path with a valid API key."""
    _configure_metrics_auth_env(monkeypatch)

    response = client.get("/metrics", headers={"X-API-Key": "test_key"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")


def test_metrics_http_guard_rejects_wrong_api_key_when_bypass_disabled(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """/metrics must reject an incorrect API key when bypass is disabled."""
    _configure_metrics_auth_env(monkeypatch)
    setattr(client, "auto_metrics_api_key", False)

    response = client.get("/metrics", headers={"X-API-Key": "wrong"})

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/json")


def test_metrics_shared_api_key_runtime_env_falls_back_to_app_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shared API key helper must honor APP_ENV when ENVIRONMENT is unset."""
    from settings import get_runtime_env_name

    monkeypatch.setenv("APP_ENV", "qa")
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    assert get_runtime_env_name() == "qa"


def test_metrics_shared_api_key_runtime_env_prefers_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shared API key helper must prefer ENVIRONMENT over non-prod APP_ENV."""
    from settings import get_runtime_env_name

    monkeypatch.setenv("APP_ENV", "qa")
    monkeypatch.setenv("ENVIRONMENT", "review")

    assert get_runtime_env_name() == "review"


def test_metrics_shared_api_key_runtime_env_defaults_to_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shared API key helper must default to local when env labels are absent."""
    from settings import get_runtime_env_name

    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    assert get_runtime_env_name() == "local"


def test_metrics_shared_api_key_normalizes_dev_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shared API key helper must preserve normalize-only dev matching."""
    from app.routers import api_key as api_key_mod

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "true")
    monkeypatch.setenv("ALLOW_DEV_API_KEY_NORMALIZE", "true")
    monkeypatch.setenv("API_KEY", "test_key")

    assert api_key_mod.validate_app_api_key("test-key") == "test_key"


def test_metrics_shared_api_key_fails_closed_without_configured_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shared API key helper must reject unconfigured access in all branches."""
    from app.routers import api_key as api_key_mod

    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    with pytest.raises(HTTPException) as required_exc:
        api_key_mod.validate_app_api_key("dev-key")

    assert required_exc.value.status_code == 403
    assert required_exc.value.detail == "API key required but not configured"

    monkeypatch.delenv("API_KEY_REQUIRED", raising=False)

    with pytest.raises(HTTPException) as default_exc:
        api_key_mod.validate_app_api_key("dev-key")

    assert default_exc.value.status_code == 403
    assert default_exc.value.detail == "API key required but not configured"


def test_metrics_guard_bypasses_with_environment_test_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """/metrics bypass must activate for explicit pytest-scoped ENVIRONMENT=test."""
    from app.bootstrap import metrics as metrics_bootstrap

    monkeypatch.setenv("METRICS_TEST_BYPASS", "true")
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "test")

    assert metrics_bootstrap._metrics_api_key_guard(None) == "testing-bypass"


def test_metrics_guard_warns_when_bypass_leaks_in_non_test_environment(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """/metrics bypass must warn and fall back to auth outside test environments."""
    from app.bootstrap import metrics as metrics_bootstrap

    _configure_metrics_auth_env(monkeypatch)
    monkeypatch.setenv("METRICS_TEST_BYPASS", "true")
    monkeypatch.setenv("ENVIRONMENT", "production")

    with caplog.at_level("WARNING", logger="app.bootstrap.metrics"):
        result = metrics_bootstrap._metrics_api_key_guard("test_key")

    assert result == "test_key"
    assert "METRICS_TEST_BYPASS ignored outside explicit pytest test env" in caplog.text
