"""Canonical, fail-closed HTTP middleware stack registration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from app.bootstrap.metrics import (
    _metrics_api_key_guard,
    metrics_endpoint,
    register_metrics,
)
from app.bootstrap.route_family import route_has_dependency_call
from app.bootstrap.telemetry import register_request_telemetry
from app.bootstrap.tracing import register_tracing, tracing_middleware
from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_endpoint,
    route_include_in_schema,
    route_methods,
    route_path,
)
from app.middleware.csp import CSPNonceMiddleware
from app.middleware.metrics import metrics_middleware
from app.middleware.request_telemetry import request_telemetry_middleware
from app.security import rate_limit as rate_limit_module

_METRICS_PATH = "/metrics"
_FRAMEWORK_METHODS = frozenset({"HEAD", "OPTIONS"})
_METRICS_STATE_KEY = "pulseplate_metrics_registered"
_TRACING_STATE_KEY = "pulseplate_tracing_registered"
_TELEMETRY_RECORDER_KEY = "request_telemetry_recorder"


@dataclass(frozen=True, slots=True)
class _HttpStackSnapshot:
    user_middleware: tuple[Any, ...]
    routes: tuple[Any, ...]
    exception_handlers: dict[Any, Any]
    state: dict[str, Any]
    middleware_stack: Any
    rate_limit: Any


def _callable_key(value: object) -> tuple[str, str] | None:
    module = getattr(value, "__module__", None)
    qualname = getattr(value, "__qualname__", None)
    if not isinstance(module, str) or not isinstance(qualname, str):
        return None
    return module, qualname


def _same_callable(existing: object, expected: object) -> bool:
    return existing is expected or (
        _callable_key(existing) is not None and _callable_key(existing) == _callable_key(expected)
    )


def _middleware_options(middleware: object) -> dict[str, Any]:
    options = getattr(middleware, "kwargs", None)
    if not isinstance(options, dict):
        options = getattr(middleware, "options", None)
    return options if isinstance(options, dict) else {}


def _middleware_label(middleware: object) -> str | None:
    middleware_class = getattr(middleware, "cls", None)
    expected_rate_class = rate_limit_module.SlowAPIMiddleware

    if _same_callable(middleware_class, CSPNonceMiddleware):
        return "csp"
    if expected_rate_class is not None and _same_callable(middleware_class, expected_rate_class):
        return "rate_limit"

    class_name = getattr(middleware_class, "__name__", None)
    if class_name == CSPNonceMiddleware.__name__:
        return "foreign_csp"
    if expected_rate_class is not None and class_name == getattr(
        expected_rate_class, "__name__", None
    ):
        return "foreign_rate_limit"

    if not _same_callable(middleware_class, BaseHTTPMiddleware):
        return None

    dispatch = _middleware_options(middleware).get("dispatch")
    owned_dispatches = (
        ("tracing", tracing_middleware),
        ("request_telemetry", request_telemetry_middleware),
        ("metrics", metrics_middleware),
    )
    for label, expected in owned_dispatches:
        if _same_callable(dispatch, expected):
            return label
        if getattr(dispatch, "__name__", None) == getattr(expected, "__name__", None):
            return f"foreign_{label}"
    return None


def _owned_middleware_projection(app: FastAPI) -> tuple[str, ...]:
    return tuple(
        label
        for middleware in app.user_middleware
        if (label := _middleware_label(middleware)) is not None
    )


def _expected_owned_projection() -> tuple[str, ...]:
    projection = ("tracing", "request_telemetry", "metrics", "csp")
    if rate_limit_module.rate_limiting_should_be_wired():
        return (*projection, "rate_limit")
    return projection


def _metrics_routes(app: FastAPI) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(app.routes)
        if is_api_route_candidate(route) and route_path(route) == _METRICS_PATH
    ]


def _metrics_route_is_canonical(app: FastAPI) -> bool:
    routes = _metrics_routes(app)
    if len(routes) != 1:
        return False
    route = routes[0]
    methods = route_methods(route) - _FRAMEWORK_METHODS
    return bool(
        methods == {"GET"}
        and _same_callable(route_endpoint(route), metrics_endpoint)
        and route_include_in_schema(route) is False
        and route_has_dependency_call(
            route,
            _metrics_api_key_guard,
            endpoint_matcher=_same_callable,
        )
    )


def _has_partial_owned_state(app: FastAPI) -> bool:
    return bool(
        _metrics_routes(app)
        or getattr(app.state, _METRICS_STATE_KEY, False)
        or hasattr(app.state, _TELEMETRY_RECORDER_KEY)
        or getattr(app.state, _TRACING_STATE_KEY, False)
        or rate_limit_module._classify_rate_limit_wiring(app) != "none"
    )


def _validate_complete_stack(app: FastAPI, expected: tuple[str, ...]) -> None:
    actual = _owned_middleware_projection(app)
    if actual != expected:
        raise RuntimeError(
            "Canonical HTTP middleware stack is partial, duplicated, foreign, or out of order."
        )
    if not _metrics_route_is_canonical(app):
        raise RuntimeError("Canonical /metrics route ownership is missing or foreign.")
    if not hasattr(app.state, _TELEMETRY_RECORDER_KEY):
        raise RuntimeError("Canonical request telemetry recorder is missing.")

    expected_rate_limit = "rate_limit" in expected
    rate_limit_module.wire_rate_limiting(app)
    rate_limit_state = rate_limit_module._classify_rate_limit_wiring(app)
    if expected_rate_limit and rate_limit_state != "complete":
        raise RuntimeError("Canonical SlowAPI wiring is incomplete.")
    if not expected_rate_limit and rate_limit_state != "none":
        raise RuntimeError("Unexpected SlowAPI wiring is present.")

    setattr(app.state, _METRICS_STATE_KEY, True)
    setattr(app.state, _TRACING_STATE_KEY, True)


def _state_store(app: FastAPI) -> dict[str, Any]:
    state = vars(app.state).get("_state")
    if not isinstance(state, dict):
        raise RuntimeError("FastAPI application state storage is unavailable.")
    return state


def _capture_stack(app: FastAPI) -> _HttpStackSnapshot:
    return _HttpStackSnapshot(
        user_middleware=tuple(app.user_middleware),
        routes=tuple(app.routes),
        exception_handlers=dict(app.exception_handlers),
        state=dict(_state_store(app)),
        middleware_stack=app.middleware_stack,
        rate_limit=rate_limit_module._capture_rate_limit_wiring(app),
    )


def _restore_stack(app: FastAPI, snapshot: _HttpStackSnapshot) -> None:
    app.user_middleware[:] = snapshot.user_middleware
    app.router.routes[:] = snapshot.routes
    app.exception_handlers.clear()
    app.exception_handlers.update(snapshot.exception_handlers)
    state = _state_store(app)
    state.clear()
    state.update(snapshot.state)
    app.middleware_stack = snapshot.middleware_stack
    rate_limit_module._restore_rate_limit_wiring(app, snapshot.rate_limit)


def register_http_middleware_stack(app: FastAPI) -> None:
    """Register or validate PulsePlate's canonical HTTP middleware stack."""

    expected = _expected_owned_projection()
    actual = _owned_middleware_projection(app)

    if actual == expected:
        _validate_complete_stack(app, expected)
        return
    if actual or _has_partial_owned_state(app):
        raise RuntimeError(
            "Canonical HTTP middleware stack is partial, duplicated, foreign, or out of order."
        )
    if app.middleware_stack is not None:
        raise RuntimeError("Cannot register the canonical HTTP stack after startup.")

    snapshot = _capture_stack(app)
    try:
        rate_limit_module.wire_rate_limiting(app)
        app.add_middleware(CSPNonceMiddleware)
        register_metrics(app)
        register_request_telemetry(app)
        register_tracing(app)
        _validate_complete_stack(app, expected)
    except Exception:
        _restore_stack(app, snapshot)
        raise


__all__ = ["register_http_middleware_stack"]
