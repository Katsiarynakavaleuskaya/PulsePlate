"""Guards for test-client limiter neutralization seams."""

import os

from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app as app_mod
from tests._client import disable_rate_limiting_for_test_app, get_client, open_test_client


def test_get_client_disables_shared_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard: canonical get_client() must keep shared limiter disabled in tests."""
    if os.getenv("RATE_LIMITING_IN_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Dedicated rate-limit suites opt in via RATE_LIMITING_IN_TESTS=true")

    import app.main
    from app.security import rate_limit as rate_limit_mod

    shared_limiter = getattr(rate_limit_mod, "limiter", None)
    if shared_limiter is not None:
        monkeypatch.setattr(shared_limiter, "enabled", True)

    limiter_on_state = getattr(app.main.app.state, "limiter", None)
    if limiter_on_state is not None:
        monkeypatch.setattr(limiter_on_state, "enabled", True)

    with get_client() as client:
        limiter_on_state = getattr(client.app.state, "limiter", None)
        assert limiter_on_state is None or getattr(limiter_on_state, "enabled", False) is False

        assert shared_limiter is None or getattr(shared_limiter, "enabled", False) is False


def test_disable_rate_limiting_helper_covers_app_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard: direct app client seams must also disable shared limiter in tests."""
    if os.getenv("RATE_LIMITING_IN_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Dedicated rate-limit suites opt in via RATE_LIMITING_IN_TESTS=true")

    from app.security import rate_limit as rate_limit_mod

    app_instance = cast(FastAPI, app_mod.app)
    shared_limiter = getattr(rate_limit_mod, "limiter", None)
    if shared_limiter is not None:
        monkeypatch.setattr(shared_limiter, "enabled", True)

    limiter_on_state = getattr(app_instance.state, "limiter", None)
    if limiter_on_state is not None:
        monkeypatch.setattr(limiter_on_state, "enabled", True)

    disable_rate_limiting_for_test_app(app_instance)

    with TestClient(app_instance) as client:
        assert limiter_on_state is None or getattr(limiter_on_state, "enabled", False) is False

        assert shared_limiter is None or getattr(shared_limiter, "enabled", False) is False


def test_app_fixture_defers_limiter_ownership_to_managed_client(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard: app lookup is zero-touch; managed client restores poisoned toggles."""
    if os.getenv("RATE_LIMITING_IN_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Dedicated rate-limit suites opt in via RATE_LIMITING_IN_TESTS=true")

    import app.main
    from app.security import rate_limit as rate_limit_mod

    shared_limiter = getattr(rate_limit_mod, "limiter", None)
    limiter_on_state = getattr(app.main.app.state, "limiter", None)

    if shared_limiter is not None:
        monkeypatch.setattr(shared_limiter, "enabled", True)
    if limiter_on_state is not None:
        monkeypatch.setattr(limiter_on_state, "enabled", True)

    app_instance = request.getfixturevalue("app")

    assert app_instance is app.main.app
    assert shared_limiter is None or shared_limiter.enabled is True
    assert limiter_on_state is None or limiter_on_state.enabled is True

    with open_test_client(app_instance):
        assert shared_limiter is None or shared_limiter.enabled is False
        assert limiter_on_state is None or limiter_on_state.enabled is False

    assert shared_limiter is None or shared_limiter.enabled is True
    assert limiter_on_state is None or limiter_on_state.enabled is True


def test_test_client_fixture_disables_poisoned_singleton_limiter(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard: shared app test-client fixture must neutralize poisoned limiters."""
    if os.getenv("RATE_LIMITING_IN_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Dedicated rate-limit suites opt in via RATE_LIMITING_IN_TESTS=true")

    import app.main
    from app.security import rate_limit as rate_limit_mod

    shared_limiter = getattr(rate_limit_mod, "limiter", None)
    limiter_on_state = getattr(app.main.app.state, "limiter", None)

    if shared_limiter is not None:
        monkeypatch.setattr(shared_limiter, "enabled", True)
    if limiter_on_state is not None:
        monkeypatch.setattr(limiter_on_state, "enabled", True)

    client = request.getfixturevalue("test_client")

    assert isinstance(client.app, FastAPI)
    assert shared_limiter is None or getattr(shared_limiter, "enabled", False) is False
    assert (
        getattr(client.app.state, "limiter", None) is None
        or getattr(client.app.state.limiter, "enabled", False) is False
    )


def test_disable_rate_limiting_helper_respects_explicit_test_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard: helper must not disable dedicated 429 suites that opt in explicitly."""
    from app.security import rate_limit as rate_limit_mod

    monkeypatch.setenv("RATE_LIMITING_IN_TESTS", "true")

    app_instance = cast(FastAPI, app_mod.app)
    shared_limiter = getattr(rate_limit_mod, "limiter", None)
    limiter_on_state = getattr(app_instance.state, "limiter", None)
    original_shared_enabled = getattr(shared_limiter, "enabled", None)
    original_app_enabled = getattr(limiter_on_state, "enabled", None)

    if shared_limiter is not None:
        shared_limiter.enabled = True
    if limiter_on_state is not None:
        limiter_on_state.enabled = True

    try:
        disable_rate_limiting_for_test_app(app_instance)

        assert shared_limiter is None or getattr(shared_limiter, "enabled", False) is True
        assert limiter_on_state is None or getattr(limiter_on_state, "enabled", False) is True
    finally:
        if shared_limiter is not None:
            shared_limiter.enabled = cast(bool, original_shared_enabled)
        if limiter_on_state is not None:
            limiter_on_state.enabled = cast(bool, original_app_enabled)
