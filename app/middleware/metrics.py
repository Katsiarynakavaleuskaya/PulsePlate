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
from prometheus_client import Counter, Histogram
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response
from starlette.routing import Match

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
    For nested routers with prefix, route.path may return only the prefix.
    We need to find the most specific (endpoint-level) route path.

    Args:
        request: FastAPI request object (after route resolution)

    Returns:
        Route template path (e.g., "/api/v1/bmi/calculate") or "unknown"
    """
    route = request.scope.get("route")
    if route is not None:
        path = getattr(route, "path", None)
        if isinstance(path, str) and path:
            # For nested routers, route.path may be just the prefix (e.g., "/api/v1/bmi")
            # Try to find the most specific route that matched
            matched_path = path
            # Check if there's a more specific route (endpoint-level, not just router prefix)
            # Always use request.app (never module-level app) to avoid NameError/scope issues
            router = getattr(request.app, "router", None)
            if router is None or not hasattr(router, "routes"):
                return matched_path

            best_path = matched_path
            best_depth = matched_path.count("/")

            for r in router.routes or []:
                if not hasattr(r, "path") or not hasattr(r, "matches"):
                    continue
                try:
                    match, _ = r.matches(request.scope)
                    if match != Match.FULL:
                        continue

                    r_path = getattr(r, "path", None)
                    if not isinstance(r_path, str) or not r_path or not r_path.startswith("/"):
                        continue

                    # Prefer the most specific endpoint-level path (by depth, not length)
                    r_depth = r_path.count("/")
                    if r_depth > best_depth:
                        best_path = r_path
                        best_depth = r_depth
                except Exception:
                    continue

            return best_path
    # Route unavailable → return "unknown"
    # Forbidden: do NOT use request.url.path as fallback for non-excluded requests
    return "unknown"


async def metrics_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Collect Prometheus metrics for HTTP requests.

    Args:
        request: FastAPI request
        call_next: Next middleware/handler (Starlette RequestResponseEndpoint)

    Returns:
        Response from downstream
    """
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
