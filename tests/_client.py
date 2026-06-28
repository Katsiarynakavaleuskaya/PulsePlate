"""Canonical TestClient factory for tests.

Ensures all tests use app.main:app (canonical entrypoint with observability bootstrap).
Prevents bypassing /metrics registration, middleware, and lifespan wiring.
"""

from __future__ import annotations

import inspect
import os
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_endpoint,
)


def _disable_limiter_instance(limiter_instance: object) -> None:
    """Reset and disable a limiter-like instance when it exposes the expected API."""
    reset_limiter = getattr(limiter_instance, "reset", None)
    if callable(reset_limiter):
        reset_limiter()

    if hasattr(limiter_instance, "enabled"):
        limiter_instance.enabled = False


def disable_rate_limiting_for_test_app(app_instance: FastAPI) -> None:
    """Force shared and app-bound rate limiters off for default test clients."""
    if os.getenv("RATE_LIMITING_IN_TESTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return

    from app.security import rate_limit as rate_limit_mod

    shared_limiter = getattr(rate_limit_mod, "limiter", None)
    if shared_limiter is not None:
        _disable_limiter_instance(shared_limiter)

    limiter_on_state = getattr(app_instance.state, "limiter", None)
    if limiter_on_state is not None:
        _disable_limiter_instance(limiter_on_state)

    # RU: Некоторые reload-тесты оставляют limiter, захваченный декоратором маршрута.
    # EN: Reload-heavy tests can leave a route decorator bound to a stale limiter instance.
    seen_limiters: set[int] = set()
    for route in iter_effective_route_candidates(app_instance.routes):
        if not is_api_route_candidate(route):
            continue
        endpoint = route_endpoint(route)
        if endpoint is None or not callable(endpoint):
            continue
        closure_nonlocals = inspect.getclosurevars(endpoint).nonlocals
        for captured in closure_nonlocals.values():
            if not hasattr(captured, "reset") and not hasattr(captured, "enabled"):
                continue
            limiter_id = id(captured)
            if limiter_id in seen_limiters:
                continue
            seen_limiters.add(limiter_id)
            _disable_limiter_instance(captured)


def override_rate_limit_identity_for_test_app(
    app_instance: FastAPI,
    *,
    limiter_key: str,
    monkeypatch: Any,
) -> None:
    """Pin route-level limiter identity to a deterministic key for one test app.

    RU: Принудительно задаёт единый limiter key и отключает auto-check для теста.
    EN: Forces a stable limiter key and disables auto-check for deterministic tests.
    """

    limiter_candidates = [
        getattr(app_instance.state, "limiter", None),
    ]

    from app.security import rate_limit as rate_limit_mod

    limiter_candidates.append(getattr(rate_limit_mod, "limiter", None))

    for limiter in limiter_candidates:
        if limiter is None:
            continue
        monkeypatch.setattr(
            limiter,
            "_key_func",
            lambda request, key=limiter_key: key,
            raising=False,
        )
        monkeypatch.setattr(limiter, "_auto_check", False, raising=False)
        monkeypatch.setattr(
            limiter,
            "_check_request_limit",
            lambda *args, **kwargs: None,
            raising=False,
        )

    for route in iter_effective_route_candidates(app_instance.routes):
        if not is_api_route_candidate(route):
            continue
        endpoint = route_endpoint(route)
        if endpoint is None or not callable(endpoint):
            continue
        closure_nonlocals = inspect.getclosurevars(endpoint).nonlocals
        for captured in closure_nonlocals.values():
            if not hasattr(captured, "_key_func"):
                continue
            monkeypatch.setattr(
                captured,
                "_key_func",
                lambda request, key=limiter_key: key,
                raising=False,
            )
            monkeypatch.setattr(captured, "_auto_check", False, raising=False)
            monkeypatch.setattr(
                captured,
                "_check_request_limit",
                lambda *args, **kwargs: None,
                raising=False,
            )


class MetricsAwareTestClient(TestClient):
    """TestClient that auto-adds the test API key for implicit `/metrics` probes."""

    auto_metrics_api_key = True

    def request(self, method: str, url: str | object, *args: Any, **kwargs: Any):  # type: ignore[override]
        headers = dict(kwargs.get("headers") or {})
        path = urlparse(str(url)).path or str(url)
        has_explicit_api_key = any(key.lower() == "x-api-key" for key in headers)
        if (
            getattr(self, "auto_metrics_api_key", True)
            and path == "/metrics"
            and not has_explicit_api_key
        ):
            headers["X-API-Key"] = os.getenv("API_KEY", "test_key")
            kwargs["headers"] = headers
        return super().request(method, url, *args, **kwargs)


def make_test_client(app_instance: FastAPI, **kwargs: Any) -> MetricsAwareTestClient:
    """Create the canonical metrics-aware test client."""

    return MetricsAwareTestClient(app_instance, **kwargs)


def get_client(**kwargs: Any) -> TestClient:
    """Create TestClient with canonical entrypoint (app.main:app).

    Always uses app.main.app (bootstrap-enabled) to ensure:
    - /metrics endpoint is registered
    - Observability middleware is active
    - Lifespan events are properly wired

    Args:
        **kwargs: Pass-through arguments to TestClient
                  (e.g., raise_server_exceptions=False, headers={...})

    Returns:
        TestClient instance configured with canonical entrypoint.

    Example:
        >>> client = get_client()
        >>> response = client.get("/metrics")
        >>> assert response.status_code == 200

    IMPORTANT: Import app.main inside function (not module-level) to ensure
    pytest_configure sets TESTING=true before app initialization.
    """
    # Import inside function to respect pytest_configure TESTING env setup
    import app.main

    disable_rate_limiting_for_test_app(app.main.app)
    return make_test_client(app.main.app, **kwargs)
