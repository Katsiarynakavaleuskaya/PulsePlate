from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.food_apis.openfoodfacts_client import OFFClient
from core.food_apis.scheduler import DatabaseUpdateScheduler
from core.food_apis.usda_client import USDAClient


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
        "USDA food details blocked in tests" in record.getMessage() for record in caplog.records
    )


def test_scheduler_defines_signal_handler_when_not_test_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.food_apis.scheduler as scheduler

    called: list[tuple[int, object]] = []

    def fake_signal(signum: int, handler: object) -> None:
        called.append((signum, handler))

    monkeypatch.setattr(scheduler, "is_test_runtime", lambda: False)
    monkeypatch.setattr(
        scheduler.threading, "current_thread", lambda: scheduler.threading.main_thread()
    )
    monkeypatch.setattr(scheduler.signal, "signal", fake_signal)

    DatabaseUpdateScheduler(update_interval_hours=1)

    assert any(signum == scheduler.signal.SIGTERM for signum, _ in called)
    assert any(signum == scheduler.signal.SIGINT for signum, _ in called)
    assert all(callable(handler) for _, handler in called)


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
