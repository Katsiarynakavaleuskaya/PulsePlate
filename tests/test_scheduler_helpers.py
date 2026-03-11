from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import asyncio
import types

import pytest

from app import scheduler_helpers


def test_resolve_app_package_import_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_app_package should import the canonical package when aliases are stale."""

    fake_pkg = types.SimpleNamespace(__path__=["/tmp/app"])

    monkeypatch.setattr(
        scheduler_helpers.importlib,
        "import_module",
        lambda name: fake_pkg if name == "app" else None,
    )

    resolved = scheduler_helpers.resolve_app_package(object(), None)
    assert resolved is fake_pkg


def test_resolve_app_package_returns_fallback_when_import_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resolve_app_package should fall back to the original candidate on import failure."""

    stale_pkg = object()

    def _boom(_name: str) -> None:
        raise RuntimeError("import failed")

    monkeypatch.setattr(scheduler_helpers.importlib, "import_module", _boom)

    resolved = scheduler_helpers.resolve_app_package(stale_pkg, None)
    assert resolved is stale_pkg


def test_resolve_scheduler_starter_prefers_pkg_before_alias() -> None:
    """resolve_scheduler_starter should prefer the app package over alias fallbacks."""

    def default_starter(interval: int) -> int:
        return interval

    class PkgAppMod:
        def _scheduler_start_background_updates(self, update_interval_hours: int) -> str:
            return f"pkg_appmod:{update_interval_hours}"

    class Pkg:
        app_module: Any = PkgAppMod()

        def _scheduler_start_background_updates(self, update_interval_hours: int) -> str:
            return f"pkg:{update_interval_hours}"

    class AliasPkg:
        def _scheduler_start_background_updates(self, update_interval_hours: int) -> str:
            return f"alias:{update_interval_hours}"

    # No override in globs, so hierarchy resolution should be used.
    globs: Dict[str, Any] = {}
    starter = scheduler_helpers.resolve_scheduler_starter(Pkg(), AliasPkg(), globs, default_starter)
    result = starter(5)
    # The package wrapper must win so package-level monkeypatching stays stable.
    assert result == "pkg:5"

    # An explicit non-default global override should still win.
    def override_starter(interval: int) -> int:
        return interval * 2

    class EmptyPkg:
        app_module: Any = object()

    globs_override: Dict[str, Any] = {"_scheduler_start_background_updates": override_starter}
    starter_override = scheduler_helpers.resolve_scheduler_starter(
        EmptyPkg(), None, globs_override, default_starter
    )
    assert starter_override is override_starter

    default_only = scheduler_helpers.resolve_scheduler_starter(
        EmptyPkg(), None, {}, default_starter
    )
    assert default_only is default_starter


def test_resolve_stop_callable_prefers_pkg_before_alias() -> None:
    """resolve_stop_callable should prefer the app package over alias fallbacks."""

    def default_stopper() -> str:
        return "default"

    class PkgAppMod:
        def _scheduler_stop_background_updates(self) -> str:
            return "pkg_appmod"

    class Pkg:
        app_module: Any = PkgAppMod()

        def _scheduler_stop_background_updates(self) -> str:
            return "pkg"

    class AliasPkg:
        def _scheduler_stop_background_updates(self) -> str:
            return "alias"

    globs: Dict[str, Any] = {}
    stopper = scheduler_helpers.resolve_stop_callable(Pkg(), AliasPkg(), globs, default_stopper)
    assert stopper() == "pkg"

    def override_stopper() -> str:
        return "override"

    class EmptyPkg:
        app_module: Any = object()

    globs_override: Dict[str, Any] = {"_scheduler_stop_background_updates": override_stopper}
    stopper_override = scheduler_helpers.resolve_stop_callable(
        EmptyPkg(), None, globs_override, default_stopper
    )
    assert stopper_override is override_stopper


class _DummyAwaitable:
    """Custom awaitable that is not a coroutine object."""

    def __init__(self) -> None:
        self._value = "ok"

    def __await__(self):
        async def _inner() -> str:
            return self._value

        return _inner().__await__()


def test_handle_sync_test_mode_awaitable_uses_new_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """handle_sync_test_mode should use a new loop for non-coroutine awaitables."""
    calls: Dict[str, Any] = {}

    def target(update_interval_hours: int) -> _DummyAwaitable:
        calls["arg"] = update_interval_hours
        return _DummyAwaitable()

    # Simulate absence of a running loop.
    def _get_running_loop() -> asyncio.AbstractEventLoop:
        raise RuntimeError("no running loop")

    monkeypatch.setattr(scheduler_helpers.asyncio, "get_running_loop", _get_running_loop)

    class FakeLoop:
        def __init__(self) -> None:
            calls["loop_created"] = True

        def run_until_complete(self, obj: Any) -> None:
            calls["run_until_complete"] = obj

        def close(self) -> None:
            calls["closed"] = True

    def _new_event_loop() -> FakeLoop:
        return FakeLoop()

    monkeypatch.setattr(scheduler_helpers.asyncio, "new_event_loop", _new_event_loop)

    caller_called: List[Any] = []
    scheduler_helpers.handle_sync_test_mode(
        target, update_interval_hours=3, caller_called=caller_called
    )

    assert calls.get("arg") == 3
    assert calls.get("loop_created") is True
    assert "run_until_complete" in calls
    assert calls.get("closed") is True
    assert caller_called == [3]


def test_handle_sync_test_mode_no_interval_appends_stop() -> None:
    """When no interval is provided, 'stop' should be recorded."""
    calls: Dict[str, Any] = {}

    def target() -> str:
        calls["called"] = True
        return "ok"

    caller_called: List[Any] = []
    scheduler_helpers.handle_sync_test_mode(
        target, update_interval_hours=None, caller_called=caller_called
    )

    assert calls.get("called") is True
    assert caller_called == ["stop"]


def test_handle_sync_test_mode_coroutine_with_running_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Awaitable with running loop should use ensure_future."""
    calls: Dict[str, Any] = {}

    async def _coro() -> None:
        calls["coro_started"] = True

    def target(update_interval_hours: int) -> Any:
        calls["arg"] = update_interval_hours
        return _coro()

    created: List[Any] = []

    def _fake_ensure_future(obj: Any) -> None:
        created.append(obj)

    class FakeLoop:
        pass

    def _get_running_loop() -> asyncio.AbstractEventLoop:
        return FakeLoop()  # type: ignore[return-value]

    monkeypatch.setattr(scheduler_helpers.asyncio, "get_running_loop", _get_running_loop)
    monkeypatch.setattr(scheduler_helpers.asyncio, "ensure_future", _fake_ensure_future)

    caller_called: List[Any] = []
    scheduler_helpers.handle_sync_test_mode(
        target, update_interval_hours=5, caller_called=caller_called
    )

    assert calls.get("arg") == 5
    assert created, "Expected ensure_future to be called with coroutine"
    # Avoid 'coroutine was never awaited' warnings in teardown
    for obj in created:
        if hasattr(obj, "close"):
            obj.close()
    assert caller_called == [5]


def test_handle_sync_test_mode_coroutine_uses_asyncio_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Coroutine without running loop should be executed via asyncio.run."""
    calls: Dict[str, Any] = {}

    async def _coro() -> None:
        calls["coro_started"] = True

    def target(update_interval_hours: int) -> Any:
        calls["arg"] = update_interval_hours
        return _coro()

    def _get_running_loop() -> asyncio.AbstractEventLoop:
        raise RuntimeError("no loop")

    run_args: List[Any] = []

    def _fake_run(obj: Any) -> None:
        if hasattr(obj, "close"):
            obj.close()
        run_args.append(obj)

    monkeypatch.setattr(scheduler_helpers.asyncio, "get_running_loop", _get_running_loop)
    monkeypatch.setattr(scheduler_helpers.asyncio, "run", _fake_run)

    caller_called: List[Any] = []
    scheduler_helpers.handle_sync_test_mode(
        target, update_interval_hours=9, caller_called=caller_called
    )

    assert calls.get("arg") == 9
    assert run_args, "Expected asyncio.run to be called with coroutine"
    assert caller_called == [9]


def _sync_starter(update_interval_hours: int) -> int:
    return update_interval_hours


def test_execute_async_starter_no_running_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """execute_async_starter should use asyncio.run when no loop is running."""
    run_calls: Dict[str, Any] = {}

    def _fake_run(arg: Any) -> None:
        run_calls["arg"] = arg

    class _AsyncioShim:
        @staticmethod
        def get_running_loop() -> asyncio.AbstractEventLoop:
            raise RuntimeError("no running loop")

    monkeypatch.setattr(scheduler_helpers.asyncio, "run", _fake_run)

    scheduler_helpers.execute_async_starter(_sync_starter, 7, _AsyncioShim)

    assert run_calls.get("arg") == 7


def test_execute_async_starter_with_running_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """execute_async_starter should create a task on an existing loop."""
    created_tasks: List[types.CoroutineType] = []

    class FakeLoop:
        def create_task(self, coro: types.CoroutineType) -> None:
            created_tasks.append(coro)

    class _AsyncioShim:
        loop = FakeLoop()

        @classmethod
        def get_running_loop(cls) -> asyncio.AbstractEventLoop:
            return cls.loop  # type: ignore[return-value]

    async def starter(update_interval_hours: int) -> int:
        return update_interval_hours

    scheduler_helpers.execute_async_starter(starter, 11, _AsyncioShim)

    assert created_tasks, "Expected create_task to be called with a coroutine"
    # Prevent 'coroutine was never awaited' RuntimeWarnings in test teardown
    for coro in created_tasks:
        coro.close()


def test_safe_stop_with_cleanup_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """safe_stop_with_cleanup should call stopper and suppress warnings."""
    called: Dict[str, bool] = {"stopper_called": False}

    def stopper() -> None:
        called["stopper_called"] = True

    def _fake_run(_: Any) -> None:
        # stopper is called before asyncio.run, so we don't need to invoke it here
        return None

    monkeypatch.setattr(scheduler_helpers.asyncio, "run", _fake_run)

    scheduler_helpers.safe_stop_with_cleanup(stopper)

    assert called["stopper_called"] is True


def test_safe_stop_with_cleanup_suppresses_event_loop_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """safe_stop_with_cleanup should swallow RuntimeError about closed event loop."""

    def stopper() -> None:
        raise RuntimeError("Event loop is closed")

    def _fake_run(_: Callable[[], Any]) -> None:
        # Simulate RuntimeError raised from asyncio.run during cleanup
        raise RuntimeError("Event loop is closed")

    monkeypatch.setattr(scheduler_helpers.asyncio, "run", _fake_run)

    # Should not raise despite RuntimeError inside stopper/run.
    scheduler_helpers.safe_stop_with_cleanup(stopper)


def test_safe_stop_with_cleanup_awaitable_calls_asyncio_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """safe_stop_with_cleanup should call asyncio.run for awaitable stoppers."""
    called: Dict[str, Any] = {}

    async def _coro() -> None:
        called["coro_ran"] = True

    def stopper() -> Any:
        # Return an awaitable object to trigger asyncio.run branch
        called["stopper_called"] = True
        return _coro()

    def _fake_run(obj: Any) -> None:
        # Record the object passed to asyncio.run and close coroutine to avoid warnings
        if hasattr(obj, "close"):
            obj.close()
        called["run_arg"] = obj

    monkeypatch.setattr(scheduler_helpers.asyncio, "run", _fake_run)

    scheduler_helpers.safe_stop_with_cleanup(stopper)

    assert called.get("stopper_called") is True
    # Ensure asyncio.run was invoked with an awaitable
    assert "run_arg" in called
