"""Bootstrap request telemetry middleware on the canonical FastAPI app."""

from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.request_telemetry import InMemorySpanRecorder, request_telemetry_middleware
from app.telemetry import telemetry_recorder_maxlen


def register_request_telemetry(app: FastAPI) -> None:
    """Register best-effort request telemetry middleware on the primary app."""

    can_mutate = getattr(app, "middleware_stack", None) is None
    has_middleware = any(
        mw.cls is BaseHTTPMiddleware
        and (getattr(mw, "options", None) or getattr(mw, "kwargs", None) or {}).get("dispatch")
        is request_telemetry_middleware
        for mw in getattr(app, "user_middleware", None) or []
    )
    if not hasattr(app.state, "request_telemetry_recorder"):
        app.state.request_telemetry_recorder = InMemorySpanRecorder(
            maxlen=telemetry_recorder_maxlen()
        )
    if not has_middleware and can_mutate:
        app.middleware("http")(request_telemetry_middleware)
