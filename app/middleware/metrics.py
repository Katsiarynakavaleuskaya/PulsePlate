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
from typing import Callable

from fastapi import Request
from prometheus_client import Counter, Histogram
from starlette.responses import Response

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    labelnames=("method", "route", "status"),
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=("method", "route", "status"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

EXCLUDED_ROUTE_TEMPLATES: set[str] = {"/metrics", "/health", "/ready", "/health/db"}


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


def _route_template(request: Request) -> str:
    """Extract route template (not raw path) to avoid high cardinality.

    Args:
        request: FastAPI request object

    Returns:
        Route template path (e.g., "/api/v1/bmi/calculate") or normalized path as fallback
    """
    route = request.scope.get("route")
    if route is not None:
        path = getattr(route, "path", None)
        if isinstance(path, str) and path:
            return path
    # Fallback: use normalized path (but only for non-excluded paths to avoid cardinality)
    # This handles cases where route is not yet resolved in middleware
    normalized = _normalized_path(request.url.path)
    # Only use raw path if it's not excluded (excluded paths are handled separately)
    if normalized not in EXCLUDED_ROUTE_TEMPLATES:
        # For API routes, try to extract template pattern
        # E.g., "/api/v1/bmi/calculate" stays as-is (no path params)
        return normalized
    return "unknown"


def _is_excluded(request: Request) -> bool:
    """Check if request should be excluded from metrics collection.

    Uses route template first (most reliable), then normalized path as fallback
    to handle trailing slashes, mounting, and redirects.

    Args:
        request: FastAPI request object

    Returns:
        True if request should be excluded from metrics
    """
    route = _route_template(request)
    if route in EXCLUDED_ROUTE_TEMPLATES:
        return True
    # Fallback: handle trailing slash / weird mounting cases
    path = _normalized_path(request.url.path)
    return path in EXCLUDED_ROUTE_TEMPLATES


async def metrics_middleware(
    request: Request, call_next: Callable[[Request], Response]
) -> Response:
    """Collect Prometheus metrics for HTTP requests.

    Args:
        request: FastAPI request
        call_next: Next middleware/handler

    Returns:
        Response from downstream
    """
    if _is_excluded(request):
        return await call_next(request)

    start = perf_counter()
    route = _route_template(request)
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
        elapsed = perf_counter() - start
        HTTP_REQUESTS_TOTAL.labels(method=method, route=route, status=status).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, route=route, status=status).observe(
            elapsed
        )
