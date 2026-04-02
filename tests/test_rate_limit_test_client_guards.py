"""Guards for test-client limiter neutralization seams."""

from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app as app_mod
from tests._client import disable_rate_limiting_for_test_app, get_client


def test_get_client_disables_shared_rate_limiter() -> None:
    """Guard: canonical get_client() must keep shared limiter disabled in tests."""
    import app.main
    from app.security import rate_limit as rate_limit_mod

    shared_limiter = getattr(rate_limit_mod, "limiter", None)
    if shared_limiter is not None:
        shared_limiter.enabled = True

    limiter_on_state = getattr(app.main.app.state, "limiter", None)
    if limiter_on_state is not None:
        limiter_on_state.enabled = True

    with get_client() as client:
        limiter_on_state = getattr(client.app.state, "limiter", None)
        assert limiter_on_state is None or getattr(limiter_on_state, "enabled", False) is False

        assert shared_limiter is None or getattr(shared_limiter, "enabled", False) is False


def test_disable_rate_limiting_helper_covers_app_surface() -> None:
    """Guard: direct app client seams must also disable shared limiter in tests."""
    from app.security import rate_limit as rate_limit_mod

    app_instance = cast(FastAPI, app_mod.app)
    shared_limiter = getattr(rate_limit_mod, "limiter", None)
    if shared_limiter is not None:
        shared_limiter.enabled = True

    limiter_on_state = getattr(app_instance.state, "limiter", None)
    if limiter_on_state is not None:
        limiter_on_state.enabled = True

    disable_rate_limiting_for_test_app(app_instance)

    with TestClient(app_instance) as client:
        assert limiter_on_state is None or getattr(limiter_on_state, "enabled", False) is False

        assert shared_limiter is None or getattr(shared_limiter, "enabled", False) is False
