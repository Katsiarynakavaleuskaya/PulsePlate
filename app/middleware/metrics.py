"""Prometheus metrics middleware for HTTP request instrumentation.

RU: Middleware для сбора метрик Prometheus по HTTP-запросам.
EN: Middleware for collecting Prometheus metrics on HTTP requests.

Metrics collected:
- http_requests_total{method, route, status}: Total request count
- http_request_duration_seconds{method, route, status}: Request latency histogram

Excluded paths: /metrics, /health, /ready, /health/db (to avoid noise)
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from time import perf_counter
from typing import Any, Protocol, cast

from fastapi import Request
from fastapi.routing import APIRoute
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

# Always defined (even if Prometheus is unavailable)
EXCLUDED_ROUTE_TEMPLATES: set[str] = {"/metrics", "/health", "/ready", "/health/db"}


class _CounterChild(Protocol):
    def inc(self, amount: float = 1.0) -> None: ...


class _Counter(Protocol):
    def labels(self, *, method: str, route: str, status: str) -> _CounterChild: ...


class _HistogramChild(Protocol):
    def observe(self, amount: float) -> None: ...


class _Histogram(Protocol):
    def labels(self, *, method: str, route: str, status: str) -> _HistogramChild: ...


@dataclass(frozen=True)
class _Metrics:
    requests_total: _Counter
    request_duration_seconds: _Histogram


def _import_prometheus() -> tuple[Any, Any]:
    prometheus_client = import_module("prometheus_client")
    return prometheus_client.Counter, prometheus_client.Histogram


def _build_metrics() -> _Metrics | None:
    try:
        Counter, Histogram = _import_prometheus()
    except ImportError:
        return None

    requests_total: _Counter = cast(
        _Counter,
        Counter(
            "http_requests_total",
            "Total number of HTTP requests",
            labelnames=("method", "route", "status"),
        ),
    )

    request_duration_seconds: _Histogram = cast(
        _Histogram,
        Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            labelnames=("method", "route", "status"),
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
        ),
    )

    return _Metrics(
        requests_total=requests_total, request_duration_seconds=request_duration_seconds
    )


PROMETHEUS_METRICS: _Metrics | None = _build_metrics()


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

    If multiple routes point to the same endpoint (e.g., alias/legacy routes),
    chooses the most specific (longest) route template to ensure consistency.

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
    routes = getattr(router, "routes", None)
    if routes is None:
        return "unknown"

    # Collect all candidate routes for this endpoint
    candidates: list[str] = []
    for r in routes or []:
        if not isinstance(r, APIRoute):
            continue
        # Match by endpoint function identity (most reliable for nested routers)
        if getattr(r, "endpoint", None) is endpoint:
            path = getattr(r, "path", None)
            if isinstance(path, str) and path and path.startswith("/"):
                candidates.append(path)

    if not candidates:
        return "unknown"

    # Choose the most specific (longest) template
    # This ensures that if both /api/v1/bmi and /api/v1/bmi/calculate point to the same
    # endpoint, we always use the more specific /api/v1/bmi/calculate
    return max(candidates, key=len)


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
    metrics = PROMETHEUS_METRICS
    if metrics is None:
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
        route_norm = _normalized_path(route)

        # Late exclusion: covers trailing slash / mounting / router behaviors
        # Normalize template before compare to handle trailing slashes consistently
        if route_norm not in EXCLUDED_ROUTE_TEMPLATES and route_norm != "unknown":
            elapsed = perf_counter() - start
            metrics.requests_total.labels(method=method, route=route_norm, status=status).inc()
            metrics.request_duration_seconds.labels(
                method=method, route=route_norm, status=status
            ).observe(elapsed)
