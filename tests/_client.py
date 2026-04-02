"""Canonical TestClient factory for tests.

Ensures all tests use app.main:app (canonical entrypoint with observability bootstrap).
Prevents bypassing /metrics registration, middleware, and lifespan wiring.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient


def disable_rate_limiting_for_test_app(app_instance: FastAPI) -> None:
    """Force shared and app-bound rate limiters off for test clients."""
    from app.security import rate_limit as rate_limit_mod

    shared_limiter = getattr(rate_limit_mod, "limiter", None)
    if shared_limiter is not None:
        shared_limiter.enabled = False

    limiter_on_state = getattr(app_instance.state, "limiter", None)
    if limiter_on_state is not None:
        limiter_on_state.enabled = False


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
