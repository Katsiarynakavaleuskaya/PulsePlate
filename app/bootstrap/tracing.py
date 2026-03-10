"""Tracing bootstrap for the primary FastAPI app.

RU: Bootstrap tracing для основного FastAPI app.
EN: Tracing bootstrap for the primary FastAPI app.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.middleware.metrics import _route_template
from app.telemetry.genai import bind_request_id, new_request_id, request_span, reset_request_id
from app.telemetry.setup import ensure_tracing_initialized

logger = logging.getLogger(__name__)


async def tracing_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Create a best-effort root request span with low-cardinality route metadata."""

    request_id = request.headers.get("x-request-id") or new_request_id()
    token = bind_request_id(request_id)

    try:
        try:
            ensure_tracing_initialized()
        except Exception:
            logger.debug(
                "Tracing initialization skipped due to configuration/backend failure", exc_info=True
            )
        with request_span(request.method, request_id) as span:
            try:
                response = await call_next(request)
            except Exception as exc:
                route = _route_template(request)
                try:
                    span.update_name(f"HTTP {request.method} {route}")
                    span.set_attribute("http.response.status_code", 500)
                    span.set_attribute("http.route", route)
                    span.record_exception(exc)
                except Exception:
                    logger.debug("Tracing error-path finalization failed", exc_info=True)
                raise
            route = _route_template(request)
            try:
                span.update_name(f"HTTP {request.method} {route}")
                span.set_attribute("http.response.status_code", response.status_code)
                span.set_attribute("http.route", route)
            except Exception:
                logger.debug("Tracing response finalization failed", exc_info=True)
            return response
    finally:
        reset_request_id(token)


def register_tracing(app: FastAPI) -> None:
    """Register tracing middleware on the canonical app instance."""

    can_mutate = getattr(app, "middleware_stack", None) is None
    has_middleware = any(
        mw.cls is BaseHTTPMiddleware
        and (getattr(mw, "options", None) or getattr(mw, "kwargs", None) or {}).get("dispatch")
        is tracing_middleware
        for mw in getattr(app, "user_middleware", None) or []
    )
    if not has_middleware and can_mutate:
        app.middleware("http")(tracing_middleware)


__all__ = ["register_tracing", "tracing_middleware"]
