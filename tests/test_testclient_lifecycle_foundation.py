"""Deterministic oracles for the managed TestClient and opt-in SQLite lifecycle."""

from __future__ import annotations

import os
import stat
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool
from slowapi import Limiter

from tests._client import open_test_client
from tests.conftest import _isolated_sqlite_database_context


class _BodyFailure(RuntimeError):
    """Sentinel raised from inside a managed client body."""


class _StartupFailure(RuntimeError):
    """Sentinel raised by application startup."""


class _ShutdownFailure(RuntimeError):
    """Sentinel raised by application shutdown."""


class _LimiterSetupFailure(RuntimeError):
    """Sentinel raised while the managed client disables a limiter."""


class _LimiterCleanupFailure(RuntimeError):
    """Sentinel raised while the managed client resets limiter counters."""


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
        response = client.get("/probe")
        assert response.status_code == 200
        assert events == ["startup"]

    assert events == ["startup", "shutdown"]
    assert client.portal is None


def test_open_test_client_closes_before_propagating_body_exception() -> None:
    events: list[str] = []
    app = _lifespan_app(events)

    with pytest.raises(_BodyFailure):
        with open_test_client(app):
            raise _BodyFailure("body failed")

    assert events == ["startup", "shutdown"]


def test_open_test_client_preserves_body_exception_when_shutdown_fails() -> None:
    events: list[str] = []
    shutdown_error = _ShutdownFailure("shutdown failed")
    body_error = _BodyFailure("body failed")
    app = _lifespan_app(events, shutdown_error=shutdown_error)

    with pytest.raises(_BodyFailure) as raised:
        with open_test_client(app):
            raise body_error

    assert raised.value is body_error
    assert raised.value.__cause__ is shutdown_error
    assert events == ["startup", "shutdown"]


def test_open_test_client_restores_state_after_startup_exception() -> None:
    events: list[str] = []
    app = _lifespan_app(events, startup_error=_StartupFailure("startup failed"))

    async def dependency() -> str:
        return "dependency"

    async def original_override() -> str:
        return "original"

    app.dependency_overrides[dependency] = original_override
    snapshot = dict(app.dependency_overrides)

    with pytest.raises(_StartupFailure):
        with open_test_client(app):
            pytest.fail("startup failure must prevent client body entry")

    assert events == ["startup"]
    assert app.dependency_overrides == snapshot
    assert app.dependency_overrides[dependency] is original_override


def test_open_test_client_restores_state_after_shutdown_exception() -> None:
    events: list[str] = []
    app = _lifespan_app(events, shutdown_error=_ShutdownFailure("shutdown failed"))

    with pytest.raises(_ShutdownFailure):
        with open_test_client(app) as client:
            assert client.get("/probe").status_code == 200

    assert events == ["startup", "shutdown"]


def test_open_test_client_restores_exact_dependency_overrides() -> None:
    app = _lifespan_app([])

    async def first_dependency() -> str:
        return "first"

    async def second_dependency() -> str:
        return "second"

    async def original_override() -> str:
        return "original"

    async def temporary_override() -> str:
        return "temporary"

    app.dependency_overrides[first_dependency] = original_override
    snapshot = dict(app.dependency_overrides)

    with open_test_client(app):
        app.dependency_overrides.clear()
        app.dependency_overrides[second_dependency] = temporary_override

    assert app.dependency_overrides == snapshot
    assert app.dependency_overrides[first_dependency] is original_override


def test_open_test_client_restores_dependency_override_mapping_identity() -> None:
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
    assert overrides_owner[dependency] is original_override
    assert replacement[dependency] is replacement_override


def _limiter_app(
    state_limiter: Limiter,
    route_limiter: Limiter,
) -> FastAPI:
    app = FastAPI()
    app.state.limiter = state_limiter

    @app.get("/limited")
    @route_limiter.limit("1/minute")
    async def limited(request: Request) -> dict[str, str]:
        del request
        return {"status": "ok"}

    @app.get("/probe")
    async def probe() -> dict[str, str]:
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


def test_open_test_client_restores_limiter_toggles_and_key_policy(
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
    state_reset = Mock(wraps=state_limiter.reset)
    route_reset = Mock(wraps=route_limiter.reset)
    monkeypatch.setattr(state_limiter, "reset", state_reset)
    monkeypatch.setattr(route_limiter, "reset", route_reset)

    shared_limiter = rate_limit_mod.limiter
    if shared_limiter is not None:
        monkeypatch.setattr(shared_limiter, "enabled", True)

    app = _limiter_app(state_limiter, route_limiter)
    with open_test_client(app) as client:
        assert state_limiter.enabled is False
        assert route_limiter.enabled is False
        state_limiter.enabled = True
        route_limiter.enabled = True
        state_limiter._key_func = lambda _request: "poisoned-state"
        route_limiter._key_func = lambda _request: "poisoned-route"
        assert client.get("/probe").status_code == 200

    assert state_limiter.enabled is True
    assert route_limiter.enabled is True
    assert state_limiter._key_func is state_key
    assert route_limiter._key_func is route_key
    assert state_reset.call_count == 2
    assert route_reset.call_count == 2
    assert shared_limiter is None or shared_limiter.enabled is True


def test_open_test_client_restores_all_limiters_after_setup_reset_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.security import rate_limit as rate_limit_mod

    monkeypatch.setattr(rate_limit_mod, "limiter", None)

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
    setup_error = _LimiterSetupFailure("route limiter setup reset failed")
    setup_cleanup_error = _LimiterCleanupFailure("route cleanup reset also failed")
    state_reset = Mock(wraps=state_limiter.reset)
    route_reset_calls = 0

    def route_reset() -> None:
        nonlocal route_reset_calls
        route_reset_calls += 1
        if route_reset_calls == 1:
            route_limiter._key_func = lambda _request: "setup-poison"
            route_limiter._auto_check = False
            route_limiter._check_request_limit = lambda *args, **kwargs: None
            raise setup_error
        if route_reset_calls == 2:
            raise setup_cleanup_error

    monkeypatch.setattr(state_limiter, "reset", state_reset)
    monkeypatch.setattr(route_limiter, "reset", route_reset)
    app = _limiter_app(state_limiter, route_limiter)

    with pytest.raises(_LimiterSetupFailure) as caught:
        with open_test_client(app):
            pytest.fail("setup failure must prevent client body entry")

    assert caught.value is setup_error
    assert caught.value.__cause__ is setup_cleanup_error
    assert state_reset.call_count == 2
    assert route_reset_calls == 2
    _assert_exact_limiter_snapshot(state_limiter, state_snapshot)
    _assert_exact_limiter_snapshot(route_limiter, route_snapshot)


def test_open_test_client_raises_first_cleanup_failure_after_restore_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.security import rate_limit as rate_limit_mod

    monkeypatch.setattr(rate_limit_mod, "limiter", None)

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
    first_cleanup_error = _LimiterCleanupFailure("state cleanup reset failed")
    second_cleanup_error = _LimiterCleanupFailure("route cleanup reset failed")
    state_reset_calls = 0
    route_reset_calls = 0

    def state_reset() -> None:
        nonlocal state_reset_calls
        state_reset_calls += 1
        if state_reset_calls == 2:
            raise first_cleanup_error

    def route_reset() -> None:
        nonlocal route_reset_calls
        route_reset_calls += 1
        if route_reset_calls == 2:
            raise second_cleanup_error

    monkeypatch.setattr(state_limiter, "reset", state_reset)
    monkeypatch.setattr(route_limiter, "reset", route_reset)
    app = _limiter_app(state_limiter, route_limiter)

    with pytest.raises(_LimiterCleanupFailure) as caught:
        with open_test_client(app):
            state_limiter.enabled = True
            route_limiter.enabled = True
            state_limiter._key_func = lambda _request: "body-poison-state"
            route_limiter._key_func = lambda _request: "body-poison-route"
            state_limiter._auto_check = False
            route_limiter._check_request_limit = lambda *args, **kwargs: None

    assert caught.value is first_cleanup_error
    assert caught.value.__cause__ is second_cleanup_error
    assert state_reset_calls == 2
    assert route_reset_calls == 2
    _assert_exact_limiter_snapshot(state_limiter, state_snapshot)
    _assert_exact_limiter_snapshot(route_limiter, route_snapshot)


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
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    monkeypatch.setenv("API_KEY", "metrics-test-key")

    with open_test_client() as client:
        response = client.get("/metrics", headers={"X-API-Key": ""})

    assert response.status_code == 403


def _assert_isolated_database_round(
    tmp_path: Path,
    request: pytest.FixtureRequest,
    marker: str,
) -> None:
    import core.db as core_db

    with _isolated_sqlite_database_context(tmp_path, request) as sqlite_path:
        assert sqlite_path.parent == tmp_path.resolve()
        assert not sqlite_path.is_symlink()
        assert stat.S_IMODE(sqlite_path.stat().st_mode) & 0o077 == 0
        assert ":memory:" not in os.environ["DATABASE_URL"]
        engine = core_db.init_db()
        assert str(engine.url) == os.environ["DATABASE_URL"]
        assert isinstance(engine.pool, NullPool)
        _args, connect_args = engine.dialect.create_connect_args(engine.url)
        assert connect_args["check_same_thread"] is False

        with core_db.session_scope() as session:
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS tc1_isolation_probe "
                    "(id INTEGER PRIMARY KEY, marker TEXT NOT NULL)"
                )
            )
            count_before = session.execute(
                text("SELECT COUNT(*) FROM tc1_isolation_probe")
            ).scalar_one()
            assert count_before == 0
            session.execute(
                text("INSERT INTO tc1_isolation_probe (id, marker) VALUES (1, :marker)"),
                {"marker": marker},
            )

    assert not sqlite_path.exists()


@pytest.mark.parametrize(
    "markers",
    [
        ("forward", "reverse"),
        ("reverse", "forward"),
    ],
)
def test_isolated_sqlite_rounds_reuse_primary_key_without_leakage(
    tmp_path: Path,
    request: pytest.FixtureRequest,
    markers: tuple[str, str],
) -> None:
    for marker in markers:
        _assert_isolated_database_round(tmp_path, request, marker)


def test_isolated_sqlite_restores_exact_database_environment(
    tmp_path: Path,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keys = (
        "DATABASE_URL",
        "TEST_DB_PATH",
        "DB_FALLBACK_URL",
        "DATABASE_ASYNC_URL",
        "DATABASE_USE_ASYNC",
    )
    monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///baseline-fallback.sqlite3")
    monkeypatch.setenv("DATABASE_USE_ASYNC", "0")
    snapshot = {key: (key in os.environ, os.environ.get(key)) for key in keys}

    with _isolated_sqlite_database_context(tmp_path, request):
        assert os.environ["DB_FALLBACK_URL"] == os.environ["DATABASE_URL"]
        assert os.environ["DATABASE_USE_ASYNC"] == "0"
        assert "DATABASE_ASYNC_URL" not in os.environ

    assert {key: (key in os.environ, os.environ.get(key)) for key in keys} == snapshot


def test_isolated_sqlite_fails_closed_when_async_database_is_configured(
    tmp_path: Path,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_ASYNC_URL", "sqlite+aiosqlite:///async-test.sqlite3")

    with pytest.raises(RuntimeError, match="inactive async DB"):
        with _isolated_sqlite_database_context(tmp_path, request):
            pytest.fail("async DB configuration must fail before fixture mutation")


@pytest.mark.parametrize(
    "async_state_attribute",
    ("_ASYNC_ENGINE", "async_engine", "AsyncSessionLocal"),
)
def test_isolated_sqlite_fails_closed_when_async_state_is_active(
    tmp_path: Path,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    async_state_attribute: str,
) -> None:
    import core.db as core_db

    monkeypatch.delenv("DATABASE_ASYNC_URL", raising=False)
    monkeypatch.delenv("DATABASE_USE_ASYNC", raising=False)
    environment_snapshot = {
        key: (key in os.environ, os.environ.get(key))
        for key in (
            "DATABASE_URL",
            "TEST_DB_PATH",
            "DB_FALLBACK_URL",
            "DATABASE_ASYNC_URL",
            "DATABASE_USE_ASYNC",
        )
    }
    initial_tmp_entries = tuple(tmp_path.iterdir())
    monkeypatch.setattr(core_db, async_state_attribute, object())

    with pytest.raises(RuntimeError, match="inactive async DB"):
        with _isolated_sqlite_database_context(tmp_path, request):
            pytest.fail("active async DB state must fail before fixture mutation")

    assert {
        key: (key in os.environ, os.environ.get(key)) for key in environment_snapshot
    } == environment_snapshot
    assert tuple(tmp_path.iterdir()) == initial_tmp_entries


def test_isolated_sqlite_teardown_refuses_replaced_path(
    tmp_path: Path,
    request: pytest.FixtureRequest,
) -> None:
    replacement_target = tmp_path / "foreign.sqlite3"
    replacement_target.touch()

    with pytest.raises(
        RuntimeError,
        match="refusing to delete a replaced isolated SQLite path",
    ):
        with _isolated_sqlite_database_context(tmp_path, request) as sqlite_path:
            sqlite_path.unlink()
            sqlite_path.symlink_to(replacement_target)

    assert sqlite_path.is_symlink()
    assert replacement_target.exists()


def test_isolated_sqlite_teardown_refuses_dangling_symlink(
    tmp_path: Path,
    request: pytest.FixtureRequest,
) -> None:
    missing_target = tmp_path / "missing.sqlite3"

    with pytest.raises(
        RuntimeError,
        match="refusing to delete a replaced isolated SQLite path",
    ):
        with _isolated_sqlite_database_context(tmp_path, request) as sqlite_path:
            sqlite_path.unlink()
            sqlite_path.symlink_to(missing_target)

    assert sqlite_path.is_symlink()
    assert not sqlite_path.exists()


def test_isolated_sqlite_preserves_body_error_when_baseline_reinit_fails(
    tmp_path: Path,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.db as core_db

    original_init_db = core_db.init_db
    body_error = RuntimeError("isolated body failed")
    baseline_error = RuntimeError("baseline reinit failed")
    init_calls = 0

    def flaky_init_db() -> Engine:
        nonlocal init_calls
        init_calls += 1
        if init_calls == 2:
            raise baseline_error
        return original_init_db()

    monkeypatch.setattr(core_db, "init_db", flaky_init_db)
    try:
        with pytest.raises(RuntimeError, match="isolated body failed") as raised:
            with _isolated_sqlite_database_context(tmp_path, request):
                raise body_error

        assert raised.value is body_error
        assert raised.value.__cause__ is baseline_error
    finally:
        monkeypatch.setattr(core_db, "init_db", original_init_db)
        original_init_db()


def test_isolated_test_client_uses_fixture_engine(
    isolated_test_client: TestClient,
    isolated_sqlite_database: Path,
) -> None:
    import core.db as core_db

    assert isolated_sqlite_database.exists()
    assert str(core_db.init_db().url) == os.environ["DATABASE_URL"]
    response = isolated_test_client.get("/health/db")
    assert response.status_code == 200
