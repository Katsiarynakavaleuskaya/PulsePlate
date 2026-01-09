"""Prometheus metrics middleware for HTTP request instrumentation.

RU: Middleware для сбора метрик Prometheus по HTTP-запросам.
EN: Middleware for collecting Prometheus metrics on HTTP requests.

Metrics collected:
- http_requests_total{method, route, status}: Total request count
- http_request_duration_seconds{method, route, status}: Request latency histogram

Excluded paths: /metrics, /health, /ready, /health/db (to avoid noise)
"""

from __future__ import annotations

from time import perf_counter

from fastapi import Request
from fastapi.routing import APIRoute
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

# Always defined (even if Prometheus is unavailable)
EXCLUDED_ROUTE_TEMPLATES: set[str] = {"/metrics", "/health", "/ready", "/health/db"}

# Graceful degradation: metrics become no-op if prometheus_client is unavailable
try:
    from prometheus_client import Counter, Histogram

    HTTP_REQUESTS_TOTAL: Counter = Counter(
        "http_requests_total",
        "Total number of HTTP requests",
        labelnames=("method", "route", "status"),
    )

    HTTP_REQUEST_DURATION_SECONDS: Histogram = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        labelnames=("method", "route", "status"),
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    )
except ImportError:
    # Metrics unavailable: middleware becomes no-op (does not crash startup)
    HTTP_REQUESTS_TOTAL = None  # type: ignore[assignment]
    HTTP_REQUEST_DURATION_SECONDS = None  # type: ignore[assignment]


def _normalized_path(path: str) -> str:
    """Normalize path by removing trailing slash (except root).

    Args:
        path: Raw request path

    Returns:
        Normalized path (e.g., "/health/" -> "/health")
    """
    if path != "/" and path.endswith("/"):
        return path[:-1]
    return path


def _excluded_by_path(request: Request) -> bool:
    """Check if request should be excluded from metrics collection (early fast-path).

    Uses normalized path (before route resolution) to handle trailing slashes.
    This is a fast-path check before routing; late exclusion by route template
    happens in finally block after route is resolved.

    Args:
        request: FastAPI request object

    Returns:
        True if request should be excluded from metrics
    """
    path = _normalized_path(request.url.path)
    return path in EXCLUDED_ROUTE_TEMPLATES


def _route_template(request: Request) -> str:
    """Extract route template (not raw path) to avoid high cardinality.

    Must be called AFTER call_next (when route is resolved by router).
    Uses endpoint mapping to find the exact APIRoute path (not router prefix).

    Args:
        request: FastAPI request object (after route resolution)

    Returns:
        Route template path (e.g., "/api/v1/bmi/calculate") or "unknown"
    """
    # Get the endpoint handler function from scope
    endpoint = request.scope.get("endpoint")
    if endpoint is None:
        return "unknown"

    # Find the APIRoute that matches this endpoint
    router = getattr(request.app, "router", None)
    if router is None or not hasattr(router, "routes"):
        return "unknown"

    for r in router.routes or []:
        if not isinstance(r, APIRoute):
            continue
        # Match by endpoint function identity (most reliable for nested routers)
        if getattr(r, "endpoint", None) is endpoint:
            path = getattr(r, "path", None)
            if isinstance(path, str) and path and path.startswith("/"):
                return path

    # Route unavailable → return "unknown"
    # Forbidden: do NOT use request.url.path as fallback for non-excluded requests
    return "unknown"


async def metrics_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Collect Prometheus metrics for HTTP requests.

    If metrics are unavailable (prometheus_client not installed), middleware becomes no-op.

    Args:
        request: FastAPI request
        call_next: Next middleware/handler (Starlette RequestResponseEndpoint)

    Returns:
        Response from downstream
    """
    # If metrics are unavailable, behave as no-op (graceful degradation)
    if HTTP_REQUESTS_TOTAL is None or HTTP_REQUEST_DURATION_SECONDS is None:
        return await call_next(request)

    # Fast path: skip obvious noise early (before timer)
    if _excluded_by_path(request):
        return await call_next(request)

    start = perf_counter()
    method = request.method

    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    except Exception:
        # Unhandled exception -> 500
        status = "500"
        raise
    finally:
        # Route extraction: AFTER call_next (when route is resolved by router)
        # Route is reliably available only after downstream routing ran
        route = _route_template(request)

        # Late exclusion: covers trailing slash / mounting / router behaviors
        # If route is excluded or unavailable, skip metrics collection
        if route not in EXCLUDED_ROUTE_TEMPLATES and route != "unknown":
            elapsed = perf_counter() - start
            HTTP_REQUESTS_TOTAL.labels(method=method, route=route, status=status).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, route=route, status=status).observe(
                elapsed
            )
