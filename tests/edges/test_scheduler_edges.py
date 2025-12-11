import asyncio
from typing import Any, Callable, NoReturn

import pytest


@pytest.mark.asyncio
async def test_scheduler_update_loop_error_branch(monkeypatch: pytest.MonkeyPatch):
    from core.food_apis.scheduler import DatabaseUpdateScheduler

    sched = DatabaseUpdateScheduler(update_interval_hours=1)
    sched.is_running = True

    # Make _should_check_for_updates raise to hit except in _update_loop
    def throw_error(_: Any) -> NoReturn:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        sched,
        "_should_check_for_updates",
        throw_error,
    )

    # Make asyncio.sleep return immediately
    async def fast_sleep(_: float) -> None:  # noqa: D401
        # Stop after first loop iteration
        sched.is_running = False
        return None

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    await sched._update_loop()


def test_scheduler_signal_handler_invocation(monkeypatch: pytest.MonkeyPatch):
    from core.food_apis import scheduler as schedmod
    from core.food_apis.scheduler import DatabaseUpdateScheduler

    captured: dict[str, Callable[..., Any]] = {}

    def fake_signal(sig: Any, handler: Callable[..., Any]):  # noqa: D401
        captured[str(sig)] = handler
        return None

    monkeypatch.setattr(schedmod.signal, "signal", fake_signal)

    # Intercept create_task to avoid running real stop
    created = {}

    def fake_create_task(coro: Any) -> None:  # noqa: D401
        created["task"] = coro
        # Close coroutine to avoid unawaited warnings without running it
        if hasattr(coro, "close"):
            coro.close()
        return None

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    # Instantiation sets up handler and registers it
    _ = DatabaseUpdateScheduler(update_interval_hours=1)

    # Call captured handler to execute handler body and cover lines
    handler = next(iter(captured.values()))
    handler(15, None)  # signum, frame
    assert "task" in created
