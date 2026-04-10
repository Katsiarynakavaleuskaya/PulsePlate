"""Canonical TestClient factory for tests.

Ensures all tests use app.main:app (canonical entrypoint with observability bootstrap).
Prevents bypassing /metrics registration, middleware, and lifespan wiring.
"""

from __future__ import annotations

import inspect
import os
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient


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
    for route in app_instance.routes:
        if not isinstance(route, APIRoute):
            continue
        endpoint = getattr(route, "endpoint", None)
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

    for route in app_instance.routes:
        if not isinstance(route, APIRoute):
            continue
        endpoint = getattr(route, "endpoint", None)
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
    return TestClient(app.main.app, **kwargs)
