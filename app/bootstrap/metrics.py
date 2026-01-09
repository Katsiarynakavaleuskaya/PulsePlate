"""Metrics bootstrap: register Prometheus middleware and /metrics endpoint.

RU: Регистрация Prometheus middleware и /metrics endpoint.
EN: Register Prometheus middleware and /metrics endpoint.

This module must be called from the primary app entrypoint (app/main.py),
not from legacy_app.py, to keep legacy as a thin compatibility proxy.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.metrics import metrics_middleware

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint (exposition format) with JSON fallback.

    Returns Prometheus text format (CONTENT_TYPE_LATEST) when available.
    Falls back to a JSON error envelope if the exporter is unavailable.

    Security: Protected at infrastructure level (ingress ACLs, firewall, private networks).
    Application-level authentication is intentionally NOT enforced to preserve
    testability and backward compatibility.
    """
    try:
        import prometheus_client

        data = prometheus_client.generate_latest()
        return Response(content=data, media_type=prometheus_client.CONTENT_TYPE_LATEST)
    except Exception:
        logger.exception("Prometheus exporter unavailable")
        return JSONResponse(
            status_code=200,
            content={
                "error": "Prometheus client not available",
                "detail": "Prometheus exporter unavailable",
            },
        )


def register_metrics(app: FastAPI) -> None:
    """Register metrics middleware and /metrics endpoint on the primary app.

    NOTE: middleware stack is built in reverse order (last added = outermost).
    This ensures metrics middleware captures all requests/exceptions passing
    through other middleware.

    Args:
        app: FastAPI application instance
    """
    # Starlette forbids adding middleware after the stack is built (first request).
    # In that case, we must skip registration to avoid runtime errors in tests/teardown.
    can_mutate = getattr(app, "middleware_stack", None) is None

    # Register middleware last so it becomes outermost (idempotent).
    has_middleware = any(
        mw.cls is BaseHTTPMiddleware and mw.kwargs.get("dispatch") is metrics_middleware
        for mw in getattr(app, "user_middleware", None) or []
    )
    if not has_middleware and can_mutate:
        app.middleware("http")(metrics_middleware)

    # Register /metrics endpoint (idempotent).
    has_metrics_route = any(
        getattr(r, "path", None) == "/metrics" and "GET" in (getattr(r, "methods", None) or set())
        for r in getattr(app, "routes", None) or []
    )
    if not has_metrics_route and can_mutate:
        app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)
