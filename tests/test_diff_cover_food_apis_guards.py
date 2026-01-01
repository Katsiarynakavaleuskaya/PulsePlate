from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from typing import Callable, cast
from unittest.mock import AsyncMock

import pytest

from core.food_apis.openfoodfacts_client import OFFClient
from core.food_apis.scheduler import DatabaseUpdateScheduler
from core.food_apis.usda_client import USDAClient
from core.test_guards import EXTERNAL_HTTP_BLOCKED_IN_TESTS_MESSAGE


@pytest.mark.asyncio
async def test_openfoodfacts_product_details_network_blocked_logs_debug(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    caplog.set_level(logging.DEBUG)

    client = OFFClient()
    monkeypatch.setattr(
        client.client,
        "get",
        AsyncMock(
            side_effect=AssertionError("External HTTP blocked in tests: GET https://example")
        ),
    )

    out = await client.get_product_details("1234567890")
    assert out is None
    assert any(
        "OFF product details blocked in tests" in record.getMessage() for record in caplog.records
    )
    await client.close()


@pytest.mark.asyncio
async def test_usda_food_details_network_blocked_logs_debug(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    caplog.set_level(logging.DEBUG)

    client = USDAClient(api_key="demo")
    monkeypatch.setattr(
        client.client,
        "get",
        AsyncMock(
            side_effect=AssertionError("External HTTP blocked in tests: GET https://example")
        ),
    )

    out = await client.get_food_details(123)
    assert out is None
    assert any(
        EXTERNAL_HTTP_BLOCKED_IN_TESTS_MESSAGE in record.getMessage()
        and "USDA food details" in record.getMessage()
        for record in caplog.records
    )
    await client.close()


def test_scheduler_defines_signal_handler_when_not_test_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.food_apis.scheduler as scheduler

    handlers: dict[int, Callable[[int, object], None]] = {}

    def fake_signal(signum: int, handler: object) -> None:
        handlers[signum] = cast(Callable[[int, object], None], handler)

    monkeypatch.setattr(scheduler, "is_test_runtime", lambda: False)
    monkeypatch.setattr(
        scheduler.threading, "current_thread", lambda: scheduler.threading.main_thread()
    )
    monkeypatch.setattr(scheduler.signal, "signal", fake_signal)

    instance = DatabaseUpdateScheduler(update_interval_hours=1)

    assert scheduler.signal.SIGTERM in handlers
    assert scheduler.signal.SIGINT in handlers
    assert all(callable(handler) for handler in handlers.values())

    handler = handlers[scheduler.signal.SIGTERM]

    created_tasks: list[object] = []

    def fake_create_task(coro: object) -> object:
        if hasattr(coro, "close"):
            coro.close()
        created_tasks.append(object())
        return created_tasks[-1]

    class RunningLoop:
        def is_closed(self) -> bool:
            return False

        def is_running(self) -> bool:
            return True

        def call_soon_threadsafe(self, callback: Callable[[], None]) -> None:
            callback()

    instance._loop = cast(asyncio.AbstractEventLoop, RunningLoop())
    monkeypatch.setattr(scheduler.asyncio, "create_task", fake_create_task)

    handler(scheduler.signal.SIGTERM, None)
    assert created_tasks, "Expected shutdown task to be scheduled via loop.call_soon_threadsafe()"


def test_scheduler_signal_handler_warns_when_loop_missing(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import core.food_apis.scheduler as scheduler

    handlers: dict[int, Callable[[int, object], None]] = {}

    def fake_signal(signum: int, handler: object) -> None:
        handlers[signum] = cast(Callable[[int, object], None], handler)

    monkeypatch.setattr(scheduler, "is_test_runtime", lambda: False)
    monkeypatch.setattr(
        scheduler.threading, "current_thread", lambda: scheduler.threading.main_thread()
    )
    monkeypatch.setattr(scheduler.signal, "signal", fake_signal)

    instance = DatabaseUpdateScheduler(update_interval_hours=1)
    instance._loop = None

    caplog.set_level(logging.INFO)
    handlers[scheduler.signal.SIGTERM](scheduler.signal.SIGTERM, None)

    assert any(
        "no running event loop is available" in record.getMessage() for record in caplog.records
    )


def test_scheduler_signal_handler_logs_when_threadsafe_schedule_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import core.food_apis.scheduler as scheduler

    handlers: dict[int, Callable[[int, object], None]] = {}

    def fake_signal(signum: int, handler: object) -> None:
        handlers[signum] = cast(Callable[[int, object], None], handler)

    monkeypatch.setattr(scheduler, "is_test_runtime", lambda: False)
    monkeypatch.setattr(
        scheduler.threading, "current_thread", lambda: scheduler.threading.main_thread()
    )
    monkeypatch.setattr(scheduler.signal, "signal", fake_signal)

    instance = DatabaseUpdateScheduler(update_interval_hours=1)

    class ExplodingLoop:
        def is_closed(self) -> bool:
            return False

        def is_running(self) -> bool:
            return True

        def call_soon_threadsafe(self, callback: Callable[[], None]) -> None:
            raise RuntimeError("boom")

    instance._loop = cast(asyncio.AbstractEventLoop, ExplodingLoop())

    caplog.set_level(logging.INFO)
    handlers[scheduler.signal.SIGTERM](scheduler.signal.SIGTERM, None)

    assert any(
        "Could not schedule scheduler shutdown task" in record.getMessage()
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_usda_client_close_swallows_event_loop_closed_runtime_error(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    caplog.set_level(logging.DEBUG)

    client = USDAClient(api_key="demo")
    real_http_client = client.client
    try:
        monkeypatch.setattr(
            client,
            "client",
            SimpleNamespace(aclose=AsyncMock(side_effect=RuntimeError("Event loop is closed"))),
        )

        await client.close()
        assert any(
            "RuntimeError during USDA client close (event loop closed)" in record.getMessage()
            for record in caplog.records
        )
    finally:
        await real_http_client.aclose()


@pytest.mark.asyncio
async def test_usda_client_close_raises_unexpected_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = USDAClient(api_key="demo")
    real_http_client = client.client
    try:
        monkeypatch.setattr(
            client,
            "client",
            SimpleNamespace(aclose=AsyncMock(side_effect=RuntimeError("boom"))),
        )

        with pytest.raises(RuntimeError, match="boom"):
            await client.close()
    finally:
        await real_http_client.aclose()
