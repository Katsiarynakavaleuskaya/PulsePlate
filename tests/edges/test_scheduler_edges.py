import asyncio
from typing import Any, Callable

import pytest


@pytest.mark.asyncio
async def test_scheduler_update_loop_error_branch(monkeypatch: pytest.MonkeyPatch):
    from core.food_apis.scheduler import DatabaseUpdateScheduler

    sched = DatabaseUpdateScheduler(update_interval_hours=1)
    sched.is_running = True

    # Make _should_check_for_updates raise to hit except in _update_loop
    monkeypatch.setattr(
        sched,
        "_should_check_for_updates",
        lambda _: iter(()).throw(RuntimeError("boom")),
    )

    # Make asyncio.sleep return immediately
    async def fast_sleep(_: float) -> None:  # noqa: D401
        # Stop after first loop iteration
        sched.is_running = False
        return None

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    await sched._update_loop()


@pytest.mark.asyncio
async def test_scheduler_signal_handler_invocation(monkeypatch: pytest.MonkeyPatch):
    from core.food_apis import scheduler as schedmod
    from core.food_apis.scheduler import DatabaseUpdateScheduler

    captured: dict[str, Callable[..., Any]] = {}

    def fake_signal(sig: Any, handler: Callable[..., Any]):  # noqa: D401
        captured[str(sig)] = handler
        return None

    monkeypatch.setattr(schedmod.signal, "signal", fake_signal)

    # Instantiation sets up handler and registers it
    scheduler = DatabaseUpdateScheduler(update_interval_hours=1)

    # Use a real asyncio.Task so stop() treats it as cancellable
    async def pending_task() -> None:
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            raise

    scheduler._update_task = asyncio.create_task(pending_task())
    scheduler.is_running = True
    handler = next(iter(captured.values()))

    handler(15, None)  # signum, frame

    # Allow scheduled shutdown task to run
    await asyncio.sleep(0)
    if scheduler._shutdown_task:
        await scheduler._shutdown_task

    assert scheduler.is_running is False
    assert scheduler._update_task is None or scheduler._update_task.done()
