from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.bootstrap.lifespan as lifespan_module
from app.bootstrap.food_search import FoodSearchLifecycleLease
from app.bootstrap.lifespan import LifespanHooks, _application_lifespan_with_hooks


def _base_hooks(events: list[str]) -> LifespanHooks:
    async def _start(update_interval_hours: int = 24) -> None:
        events.append(f"scheduler-start:{update_interval_hours}")

    async def _stop() -> None:
        events.append("scheduler-stop")

    def _configure(_app: FastAPI) -> FoodSearchLifecycleLease:
        events.append("food-configure")
        return FoodSearchLifecycleLease()

    def _dispose(_app: FastAPI, _lease: FoodSearchLifecycleLease) -> None:
        events.append("food-dispose")

    return LifespanHooks(
        run_startup_guards=lambda _app: events.append("guards"),
        initialize_database=lambda: events.append("database"),
        clear_database_fallback=lambda: events.append("fallback-clear"),
        attempt_database_fallback=lambda _env, _prod, _err: events.append("fallback-attempt"),
        validate_templates=lambda: events.append("templates"),
        configure_food_search=_configure,
        dispose_food_search=_dispose,
        start_background_updates=_start,
        stop_background_updates=_stop,
    )


def _run_lifespan(
    hooks: LifespanHooks,
    *,
    body: Callable[[], Awaitable[None]] | None = None,
) -> None:
    async def _scenario() -> None:
        async with _application_lifespan_with_hooks(FastAPI(), hooks=hooks):
            if body is not None:
                await body()

    asyncio.run(_scenario())


def test_canonical_lifespan_uses_exact_startup_and_cleanup_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    monkeypatch.delenv("DISABLE_BACKGROUND_UPDATES", raising=False)

    async def _body() -> None:
        events.append("body")

    _run_lifespan(_base_hooks(events), body=_body)

    assert events == [
        "guards",
        "database",
        "fallback-clear",
        "templates",
        "food-configure",
        "scheduler-start:24",
        "body",
        "scheduler-stop",
        "food-dispose",
    ]


def test_startup_guard_failure_stops_all_later_work() -> None:
    events: list[str] = []
    hooks = replace(
        _base_hooks(events),
        run_startup_guards=lambda _app: (_ for _ in ()).throw(RuntimeError("guard")),
    )

    with pytest.raises(RuntimeError, match="guard"):
        _run_lifespan(hooks)

    assert events == []


def test_database_failure_delegates_to_public_fallback_without_clearing_state() -> None:
    events: list[str] = []
    database_error = OSError("database unavailable")

    def _initialize() -> None:
        events.append("database")
        raise database_error

    def _fallback(_env: str | None, _prod: bool, error: Exception) -> None:
        assert error is database_error
        events.append("fallback-attempt")

    hooks = replace(
        _base_hooks(events),
        initialize_database=_initialize,
        attempt_database_fallback=_fallback,
    )
    _run_lifespan(hooks)

    assert events[:4] == ["guards", "database", "fallback-attempt", "templates"]
    assert "fallback-clear" not in events


def test_production_database_failure_propagates() -> None:
    events: list[str] = []
    database_error = RuntimeError("production database unavailable")

    def _raise_database_error() -> None:
        raise database_error

    def _reject_fallback(_env: str | None, _prod: bool, error: Exception) -> None:
        raise error

    hooks = replace(
        _base_hooks(events),
        initialize_database=_raise_database_error,
        attempt_database_fallback=_reject_fallback,
    )

    with pytest.raises(RuntimeError, match="production database unavailable"):
        _run_lifespan(hooks)
    assert events == ["guards"]


def test_template_failure_prevents_resource_acquisition() -> None:
    events: list[str] = []
    hooks = replace(
        _base_hooks(events),
        validate_templates=lambda: (_ for _ in ()).throw(RuntimeError("templates")),
    )

    with pytest.raises(RuntimeError, match="templates"):
        _run_lifespan(hooks)

    assert events == ["guards", "database", "fallback-clear"]


def test_food_configuration_failure_prevents_scheduler_start() -> None:
    events: list[str] = []

    def _fail_configure(_app: FastAPI) -> FoodSearchLifecycleLease:
        events.append("food-configure")
        raise RuntimeError("food")

    hooks = replace(_base_hooks(events), configure_food_search=_fail_configure)

    with pytest.raises(RuntimeError, match="food"):
        _run_lifespan(hooks)

    assert events[-1] == "food-configure"
    assert "scheduler-start:24" not in events
    assert "scheduler-stop" not in events


@pytest.mark.parametrize(
    ("testing", "ci", "force", "disable", "should_start"),
    [
        ("true", None, None, None, False),
        (None, "true", None, None, False),
        ("true", None, "true", None, True),
        ("true", None, "true", "true", False),
        (None, None, None, None, True),
    ],
)
def test_scheduler_environment_precedence(
    monkeypatch: pytest.MonkeyPatch,
    testing: str | None,
    ci: str | None,
    force: str | None,
    disable: str | None,
    should_start: bool,
) -> None:
    for name, value in {
        "TESTING": testing,
        "CI": ci,
        "FORCE_BACKGROUND_UPDATES": force,
        "DISABLE_BACKGROUND_UPDATES": disable,
    }.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    events: list[str] = []

    _run_lifespan(_base_hooks(events))

    assert ("scheduler-start:24" in events) is should_start
    assert events[-2:] == ["scheduler-stop", "food-dispose"]


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (None, 10.0),
        ("0.25", 0.25),
        ("60", 60.0),
        ("bad", 10.0),
        ("0", 10.0),
        ("-1", 10.0),
        ("61", 10.0),
        ("nan", 10.0),
        ("inf", 10.0),
        ("-inf", 10.0),
    ],
)
def test_background_timeout_is_finite_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
    raw_value: str | None,
    expected: float,
) -> None:
    if raw_value is None:
        monkeypatch.delenv("BACKGROUND_START_TIMEOUT_SEC", raising=False)
    else:
        monkeypatch.setenv("BACKGROUND_START_TIMEOUT_SEC", raw_value)

    assert lifespan_module._background_start_timeout_seconds() == expected


def test_timeout_cancels_and_drains_start_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cancelled = False

    async def _start(update_interval_hours: int = 24) -> None:
        nonlocal cancelled
        assert update_interval_hours == 24
        try:
            await asyncio.Event().wait()
        finally:
            cancelled = True

    async def _timeout(task: asyncio.Task[None], *, timeout: float) -> None:
        assert timeout == 10.0
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        raise TimeoutError

    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    monkeypatch.setattr(lifespan_module.asyncio, "wait_for", _timeout)
    events: list[str] = []
    hooks = replace(_base_hooks(events), start_background_updates=_start)

    _run_lifespan(hooks)

    assert cancelled is True
    assert events[-2:] == ["scheduler-stop", "food-dispose"]


def test_body_exception_is_not_masked_by_cleanup_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    events: list[str] = []

    async def _stop() -> None:
        events.append("scheduler-stop")
        raise RuntimeError("stop failed")

    def _dispose(_app: FastAPI, _lease: FoodSearchLifecycleLease) -> None:
        events.append("food-dispose")
        raise RuntimeError("dispose failed")

    async def _body() -> None:
        raise ValueError("body failed")

    hooks = replace(
        _base_hooks(events),
        stop_background_updates=_stop,
        dispose_food_search=_dispose,
    )
    with pytest.raises(ValueError, match="body failed"):
        _run_lifespan(hooks, body=_body)

    assert events[-2:] == ["scheduler-stop", "food-dispose"]


def test_stop_cancellation_does_not_mask_body_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    events: list[str] = []

    async def _stop() -> None:
        events.append("scheduler-stop")
        raise asyncio.CancelledError

    async def _body() -> None:
        raise ValueError("body failed")

    hooks = replace(_base_hooks(events), stop_background_updates=_stop)
    with pytest.raises(ValueError, match="body failed"):
        _run_lifespan(hooks, body=_body)

    assert events[-2:] == ["scheduler-stop", "food-dispose"]


def test_body_cancellation_propagates_after_reverse_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    events: list[str] = []

    async def _body() -> None:
        events.append("body")
        raise asyncio.CancelledError("body cancelled")

    with pytest.raises(asyncio.CancelledError, match="body cancelled"):
        _run_lifespan(_base_hooks(events), body=_body)

    assert events[-3:] == ["body", "scheduler-stop", "food-dispose"]


def test_scheduler_start_exception_logs_continues_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    events: list[str] = []

    async def _start(update_interval_hours: int = 24) -> None:
        assert update_interval_hours == 24
        events.append("scheduler-start-failed")
        raise RuntimeError("start failed")

    async def _body() -> None:
        events.append("body")

    hooks = replace(_base_hooks(events), start_background_updates=_start)
    with caplog.at_level("ERROR", logger="app.bootstrap.lifespan"):
        _run_lifespan(hooks, body=_body)

    assert "Failed to start background updates" in caplog.text
    assert events[-4:] == [
        "scheduler-start-failed",
        "body",
        "scheduler-stop",
        "food-dispose",
    ]


@pytest.mark.parametrize("body_raises", [False, True])
def test_legacy_created_app_runs_real_food_search_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    body_raises: bool,
) -> None:
    import app
    import app.bootstrap.food_search as food_search_module
    import app.main as app_main
    import legacy_app
    from app.bootstrap.lifespan import application_lifespan
    from app.services import food_store

    class _PreviousBackend:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            del query, limit, offset
            return []

    class _Client:
        def __init__(self) -> None:
            self.is_closed = False

        def close(self) -> None:
            self.is_closed = True

    previous_backend = _PreviousBackend()
    clients: list[_Client] = []

    def _client_factory() -> _Client:
        client = _Client()
        clients.append(client)
        return client

    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "meili")
    monkeypatch.setenv("MEILI_URL", "http://127.0.0.1:7700")
    monkeypatch.setattr(food_search_module, "_build_meili_http_client", _client_factory)
    food_store.register_strategy_search_backend_adapter(previous_backend)
    try:
        assert app.lifespan is application_lifespan
        assert legacy_app.lifespan is application_lifespan
        assert app.app is legacy_app.app
        assert app_main.app is legacy_app.app

        if body_raises:
            with pytest.raises(RuntimeError, match="body failed"):
                with TestClient(legacy_app.app):
                    assert food_store.get_registered_strategy_search_backend_adapter() is not (
                        previous_backend
                    )
                    assert clients and clients[-1].is_closed is False
                    raise RuntimeError("body failed")
        else:
            with TestClient(legacy_app.app):
                assert food_store.get_registered_strategy_search_backend_adapter() is not (
                    previous_backend
                )
                assert clients and clients[-1].is_closed is False

        assert clients[-1].is_closed is True
        assert getattr(legacy_app.app.state, "meili_http_client", None) is None
        assert getattr(legacy_app.app.state, "meili_http_shutdown_event", None) is None
        assert food_store.get_registered_strategy_search_backend_adapter() is previous_backend
    finally:
        food_store.reset_strategy_search_backend_adapter()
