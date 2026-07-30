"""Deterministic oracles for the managed TestClient lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request
from slowapi import Limiter

from tests._client import open_test_client


class _BodyFailure(RuntimeError):
    """Sentinel raised from inside a managed client body."""


class _StartupFailure(RuntimeError):
    """Sentinel raised by application startup."""


class _ShutdownFailure(RuntimeError):
    """Sentinel raised by application shutdown."""


_LIMITER_POLICY_ATTRIBUTES = (
    "enabled",
    "_key_func",
    "_auto_check",
    "_check_request_limit",
)


def _lifespan_app(
    events: list[str],
    *,
    startup_error: Exception | None = None,
    shutdown_error: Exception | None = None,
) -> FastAPI:
    """Build a tiny app whose lifecycle transitions are directly observable."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        events.append("startup")
        if startup_error is not None:
            raise startup_error
        try:
            yield
        finally:
            events.append("shutdown")
            if shutdown_error is not None:
                raise shutdown_error

    app = FastAPI(lifespan=lifespan)

    @app.get("/probe")
    async def probe() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_open_test_client_runs_startup_and_shutdown_once() -> None:
    events: list[str] = []
    app = _lifespan_app(events)

    with open_test_client(app) as client:
        assert client.get("/probe").status_code == 200
        assert events == ["startup"]

    assert events == ["startup", "shutdown"]
    assert client.portal is None


def test_open_test_client_preserves_body_error_after_shutdown() -> None:
    events: list[str] = []
    body_error = _BodyFailure("body failed")
    app = _lifespan_app(events, shutdown_error=_ShutdownFailure("shutdown failed"))

    with pytest.raises(_BodyFailure) as raised:
        with open_test_client(app):
            raise body_error

    assert raised.value is body_error
    assert isinstance(raised.value.__cause__, _ShutdownFailure)
    assert events == ["startup", "shutdown"]


def test_open_test_client_restores_overrides_after_startup_failure() -> None:
    events: list[str] = []
    app = _lifespan_app(events, startup_error=_StartupFailure("startup failed"))

    async def dependency() -> str:
        return "dependency"

    async def original_override() -> str:
        return "original"

    app.dependency_overrides[dependency] = original_override
    overrides_owner = app.dependency_overrides
    snapshot = dict(overrides_owner)

    with pytest.raises(_StartupFailure):
        with open_test_client(app):
            pytest.fail("startup failure must prevent client body entry")

    assert events == ["startup"]
    assert app.dependency_overrides is overrides_owner
    assert app.dependency_overrides == snapshot


def test_open_test_client_restores_state_after_shutdown_failure() -> None:
    events: list[str] = []
    app = _lifespan_app(events, shutdown_error=_ShutdownFailure("shutdown failed"))

    async def dependency() -> str:
        return "dependency"

    async def original_override() -> str:
        return "original"

    app.dependency_overrides[dependency] = original_override
    snapshot = dict(app.dependency_overrides)

    with pytest.raises(_ShutdownFailure):
        with open_test_client(app) as client:
            assert client.get("/probe").status_code == 200
            app.dependency_overrides.clear()

    assert events == ["startup", "shutdown"]
    assert app.dependency_overrides == snapshot


def test_open_test_client_restores_override_mapping_identity_and_contents() -> None:
    app = _lifespan_app([])

    async def dependency() -> str:
        return "dependency"

    async def original_override() -> str:
        return "original"

    async def replacement_override() -> str:
        return "replacement"

    overrides_owner = app.dependency_overrides
    overrides_owner[dependency] = original_override
    snapshot = dict(overrides_owner)
    replacement = {dependency: replacement_override}

    with open_test_client(app):
        app.dependency_overrides = replacement

    assert app.dependency_overrides is overrides_owner
    assert overrides_owner == snapshot
    assert replacement[dependency] is replacement_override


def _limiter_app(state_limiter: Limiter, route_limiter: Limiter) -> FastAPI:
    app = FastAPI()
    app.state.limiter = state_limiter

    @app.get("/limited")
    @route_limiter.limit("1/minute")
    async def limited(request: Request) -> dict[str, str]:
        del request
        return {"status": "ok"}

    return app


def _limiter_snapshot(limiter: Limiter) -> dict[str, tuple[bool, object]]:
    namespace = vars(limiter)
    return {name: (name in namespace, namespace.get(name)) for name in _LIMITER_POLICY_ATTRIBUTES}


def _assert_exact_limiter_snapshot(
    limiter: Limiter,
    snapshot: dict[str, tuple[bool, object]],
) -> None:
    namespace = vars(limiter)
    for name, (was_owned, value) in snapshot.items():
        assert (name in namespace) is was_owned
        if was_owned:
            assert namespace[name] is value


def test_open_test_client_restores_limiter_policy_and_clears_counters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.security import rate_limit as rate_limit_mod

    def state_key(_request: Request) -> str:
        return "state"

    def route_key(_request: Request) -> str:
        return "route"

    state_limiter = Limiter(key_func=state_key)
    route_limiter = Limiter(key_func=route_key)
    state_limiter.enabled = True
    route_limiter.enabled = True
    vars(state_limiter).pop("_auto_check", None)
    vars(route_limiter).pop("_check_request_limit", None)
    state_snapshot = _limiter_snapshot(state_limiter)
    route_snapshot = _limiter_snapshot(route_limiter)
    state_reset = Mock(wraps=state_limiter.reset)
    route_reset = Mock(wraps=route_limiter.reset)
    monkeypatch.setattr(state_limiter, "reset", state_reset)
    monkeypatch.setattr(route_limiter, "reset", route_reset)

    shared_limiter = rate_limit_mod.limiter
    if shared_limiter is not None:
        monkeypatch.setattr(shared_limiter, "enabled", True)

    app = _limiter_app(state_limiter, route_limiter)
    with open_test_client(app):
        assert state_limiter.enabled is False
        assert route_limiter.enabled is False
        state_limiter.enabled = True
        route_limiter.enabled = True
        state_limiter._key_func = lambda _request: "poisoned-state"
        route_limiter._key_func = lambda _request: "poisoned-route"
        state_limiter._auto_check = False
        route_limiter._check_request_limit = lambda *args, **kwargs: None

    _assert_exact_limiter_snapshot(state_limiter, state_snapshot)
    _assert_exact_limiter_snapshot(route_limiter, route_snapshot)
    assert state_reset.call_count == 2
    assert route_reset.call_count == 2
    assert shared_limiter is None or shared_limiter.enabled is True


def test_open_test_client_rate_limit_opt_in_is_zero_touch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RATE_LIMITING_IN_TESTS", "true")

    def key_func(_request: Request) -> str:
        return "state"

    limiter = Limiter(key_func=key_func)
    limiter.enabled = True
    reset = Mock(wraps=limiter.reset)
    monkeypatch.setattr(limiter, "reset", reset)
    app = FastAPI()
    app.state.limiter = limiter

    with open_test_client(app):
        assert limiter.enabled is True
        assert limiter._key_func is key_func

    assert limiter.enabled is True
    assert limiter._key_func is key_func
    reset.assert_not_called()


def test_explicit_empty_metrics_api_key_is_not_replaced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "auto-key-must-not-be-used")
    app = FastAPI()

    @app.get("/metrics")
    async def metrics(request: Request) -> dict[str, str | None]:
        return {"api_key": request.headers.get("x-api-key")}

    with open_test_client(app) as client:
        response = client.get("/metrics", headers={"X-API-Key": ""})

    assert response.status_code == 200
    assert response.json() == {"api_key": ""}
