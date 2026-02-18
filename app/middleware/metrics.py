"""Prometheus metrics middleware for HTTP request instrumentation.

RU: Middleware для сбора метрик Prometheus по HTTP-запросам.
EN: Middleware for collecting Prometheus metrics on HTTP requests.

Metrics collected:
- http_requests_total{method, route, status}: Total request count
- http_request_duration_seconds{method, route, status}: Request latency histogram

Excluded paths: /metrics, /health, /ready, /health/db (to avoid noise)
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from importlib import import_module
import logging
from threading import Lock
from time import monotonic, perf_counter
from typing import Any, Callable, Protocol, cast

from fastapi import Request
from fastapi.routing import APIRoute
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Always defined (even if Prometheus is unavailable)
EXCLUDED_ROUTE_TEMPLATES: set[str] = {"/metrics", "/health", "/ready", "/health/db"}

# Bounded route cache config.
# Cache key is endpoint_id (id(endpoint)) to avoid holding strong refs to callables.
ROUTE_CACHE_MAX_SIZE: int = 1024
# If set (seconds), cached entries expire after TTL. None = no expiry.
ROUTE_CACHE_TTL_S: float | None = None

# Bounded WS observability labels (low-cardinality contract).
WS_ALLOWED_PATH_LABELS: frozenset[str] = frozenset({"/ws"})
WS_ALLOWED_CLOSE_REASONS: frozenset[str] = frozenset(
    {
        "ws_disabled",
        "auth_required",
        "auth_invalid",
        "text_frame_required",
        "payload_too_large",
        "rate_limited",
        "invalid_json",
        "event_type_not_allowed",
        "unsupported_version",
        "channel_not_allowed",
        "too_many_connections",
        "idle_timeout",
        "none",
        "unknown",
    }
)
WS_ALLOWED_DIRECTIONS: frozenset[str] = frozenset({"in", "out", "unknown"})


class _CounterChild(Protocol):
    def inc(self, amount: float = 1.0) -> None: ...


class _Counter(Protocol):
    def labels(self, *, method: str, route: str, status: str) -> _CounterChild: ...


class _HistogramChild(Protocol):
    def observe(self, amount: float) -> None: ...


class _Histogram(Protocol):
    def labels(self, *, method: str, route: str, status: str) -> _HistogramChild: ...


class _GaugeChild(Protocol):
    def inc(self, amount: float = 1.0) -> None: ...

    def dec(self, amount: float = 1.0) -> None: ...


class _Gauge(Protocol):
    def labels(self, *, path: str) -> _GaugeChild: ...


@dataclass(frozen=True)
class _Metrics:
    requests_total: _Counter
    request_duration_seconds: _Histogram
    ws_connect_total: Any
    ws_messages_total: Any
    ws_active_connections: _Gauge


# Type alias for dependency injection (testability)
_Importer = Callable[[str], Any]


def _import_prometheus(importer: _Importer = import_module) -> tuple[Any, Any]:
    """Import prometheus_client module and return Counter, Histogram classes.

    Args:
        importer: Module importer function (default: importlib.import_module).
                 Allows dependency injection for testing ImportError paths.

    Returns:
        Tuple of (Counter, Histogram) classes from prometheus_client

    Raises:
        ImportError: If prometheus_client module cannot be imported
    """
    prometheus_client = importer("prometheus_client")
    return prometheus_client.Counter, prometheus_client.Histogram


def _build_metrics() -> _Metrics | None:
    """Initialize metrics objects.

    Returns None if prometheus_client is unavailable OR if metric registration fails
    (e.g., module reload causes duplicate names in the default registry).

    Returns:
        _Metrics instance or None if initialization fails
    """
    try:
        Counter, Histogram = _import_prometheus()
        Gauge = cast(Any, import_module("prometheus_client").Gauge)
    except ImportError:
        return None

    # prometheus_client raises ValueError if metric name already registered
    # in the default global REGISTRY (e.g., module reload in tests/dev).
    try:
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

        ws_connect_total: _Counter = cast(
            _Counter,
            Counter(
                "ws_connect_total",
                "Total WS connection outcomes",
                labelnames=("path", "result", "reason"),
            ),
        )
        ws_messages_total: _Counter = cast(
            _Counter,
            Counter(
                "ws_messages_total",
                "Total WS messages by direction",
                labelnames=("path", "direction", "status"),
            ),
        )
        ws_active_connections: _Gauge = cast(
            _Gauge,
            Gauge(
                "ws_active_connections",
                "Current active WS connections",
                labelnames=("path",),
            ),
        )
    except ValueError:
        logger.warning(
            "Duplicate prometheus metric registration in _build_metrics (metrics disabled)",
            exc_info=True,
        )
        return None

    return _Metrics(
        requests_total=requests_total,
        request_duration_seconds=request_duration_seconds,
        ws_connect_total=ws_connect_total,
        ws_messages_total=ws_messages_total,
        ws_active_connections=ws_active_connections,
    )


PROMETHEUS_METRICS: _Metrics | None = _build_metrics()


def _normalize_ws_path(path: str) -> str:
    normalized = _normalized_path(path)
    return normalized if normalized in WS_ALLOWED_PATH_LABELS else "other"


def normalize_ws_close_reason(reason: str) -> str:
    normalized = reason.strip().lower() if reason else "unknown"
    return normalized if normalized in WS_ALLOWED_CLOSE_REASONS else "unknown"


def _normalize_ws_direction(direction: str) -> str:
    normalized = direction.strip().lower() if direction else "unknown"
    return normalized if normalized in WS_ALLOWED_DIRECTIONS else "unknown"


def record_ws_connect(path: str, *, result: str = "accepted", reason: str = "none") -> None:
    metrics = PROMETHEUS_METRICS
    if metrics is None:
        return
    try:
        metrics.ws_connect_total.labels(
            path=_normalize_ws_path(path),
            result=result.strip().lower(),
            reason=normalize_ws_close_reason(reason),
        ).inc()
    except Exception:  # nosec B110 - best-effort observability
        pass


def record_ws_message(path: str, *, direction: str, status: str = "ok") -> None:
    metrics = PROMETHEUS_METRICS
    if metrics is None:
        return
    try:
        metrics.ws_messages_total.labels(
            path=_normalize_ws_path(path),
            direction=_normalize_ws_direction(direction),
            status=status.strip().lower(),
        ).inc()
    except Exception:  # nosec B110 - best-effort observability
        pass


def inc_ws_active_connections(path: str) -> None:
    metrics = PROMETHEUS_METRICS
    if metrics is None:
        return
    try:
        metrics.ws_active_connections.labels(path=_normalize_ws_path(path)).inc()
    except Exception:  # nosec B110 - best-effort observability
        pass


def dec_ws_active_connections(path: str) -> None:
    metrics = PROMETHEUS_METRICS
    if metrics is None:
        return
    try:
        metrics.ws_active_connections.labels(path=_normalize_ws_path(path)).dec()
    except Exception:  # nosec B110 - best-effort observability
        pass


def _normalized_path(path: str) -> str:
    """Normalize path by removing trailing slash (except root).

    Args:
        path: Raw request path

    Returns:
        Normalized path (e.g., "/health/" -> "/health", "/" -> "/")
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


_RouteCacheEntry = tuple[str, float]
_ROUTE_CACHE: "OrderedDict[int, _RouteCacheEntry]" = OrderedDict()
_ROUTE_CACHE_LOCK = Lock()
_ROUTE_CACHE_EVICTIONS: int = 0
_ROUTE_CACHE_EXPIRED: int = 0


def _now_monotonic() -> float:
    """Return current monotonic time (test seam for deterministic TTL tests)."""
    return monotonic()


def _route_cache_get(endpoint_id: int) -> str | None:
    ttl_s = ROUTE_CACHE_TTL_S
    now = _now_monotonic()
    with _ROUTE_CACHE_LOCK:
        entry = _ROUTE_CACHE.get(endpoint_id)
        if entry is None:
            return None
        value, inserted_at = entry
        if ttl_s is not None and (now - inserted_at) > ttl_s:
            global _ROUTE_CACHE_EXPIRED
            _ROUTE_CACHE.pop(endpoint_id, None)
            _ROUTE_CACHE_EXPIRED += 1
            return None

        # Mark as most-recently-used.
        _ROUTE_CACHE.move_to_end(endpoint_id, last=True)
        return value


def _route_cache_set(endpoint_id: int, value: str) -> None:
    max_size = ROUTE_CACHE_MAX_SIZE
    if max_size <= 0:
        return

    now = _now_monotonic()
    with _ROUTE_CACHE_LOCK:
        _ROUTE_CACHE[endpoint_id] = (value, now)
        _ROUTE_CACHE.move_to_end(endpoint_id, last=True)
        if len(_ROUTE_CACHE) > max_size:
            global _ROUTE_CACHE_EVICTIONS
            _ROUTE_CACHE.popitem(last=False)
            _ROUTE_CACHE_EVICTIONS += 1


def _route_cache_stats() -> dict[str, int]:
    """Return internal route-cache stats for debugging/monitoring."""
    with _ROUTE_CACHE_LOCK:
        return {
            "size": len(_ROUTE_CACHE),
            "evictions": _ROUTE_CACHE_EVICTIONS,
            "expired": _ROUTE_CACHE_EXPIRED,
        }


def _route_template(request: Request) -> str:
    """Extract route template (not raw path) to avoid high cardinality.

    Must be called AFTER call_next (when route is resolved by router).
    Uses endpoint mapping to find the exact APIRoute path (not router prefix).

    If multiple routes point to the same endpoint (e.g., alias/legacy routes),
    chooses the most specific (longest) route template to ensure consistency.

    Uses caching to avoid scanning all routes on every request.

    Args:
        request: FastAPI request object (after route resolution)

    Returns:
        Route template path (e.g., "/api/v1/bmi/calculate") or "unknown"
    """
    # Get the endpoint handler function from scope
    endpoint = request.scope.get("endpoint")
    if endpoint is None:
        return "unknown"

    # Check cache first (key is endpoint object id for stability)
    endpoint_id = id(endpoint)
    cached = _route_cache_get(endpoint_id)
    if cached is not None:
        return cached

    # Find the APIRoute that matches this endpoint
    router = getattr(request.app, "router", None)
    routes = getattr(router, "routes", None)
    if routes is None:
        return "unknown"

    # Collect all candidate routes for this endpoint
    candidates: list[str] = []
    for r in routes:
        if not isinstance(r, APIRoute):
            continue
        # Match by endpoint function identity (most reliable for nested routers)
        if getattr(r, "endpoint", None) is endpoint:
            path = getattr(r, "path", None)
            if isinstance(path, str) and path and path.startswith("/"):
                candidates.append(path)

    if not candidates:
        result = "unknown"
    else:
        # Choose the most specific (longest) template
        # This ensures that if both /api/v1/bmi and /api/v1/bmi/calculate point to the same
        # endpoint, we always use the more specific /api/v1/bmi/calculate
        result = max(candidates, key=len)

    # Cache result for future requests
    _route_cache_set(endpoint_id, result)
    return result


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
        if route_norm not in EXCLUDED_ROUTE_TEMPLATES:
            elapsed = perf_counter() - start
            # Metrics must be best-effort only and must never mask/replace the
            # original response/exception from the try-block.
            try:
                metrics.requests_total.labels(method=method, route=route_norm, status=status).inc()
                metrics.request_duration_seconds.labels(
                    method=method, route=route_norm, status=status
                ).observe(elapsed)
            except Exception:  # nosec B110 - metrics are non-critical, silent failure intentional
                # Metrics recording must never affect request handling.
                # Optional: logger.exception("Prometheus metrics recording failed")
                # Rationale: Silent failure is intentional - metrics are non-critical
                # and must not interrupt request processing. This is a known pattern
                # for observability code that should never affect business logic.
                pass
