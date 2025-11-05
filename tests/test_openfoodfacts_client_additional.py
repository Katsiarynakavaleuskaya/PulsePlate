from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from core.food_apis.openfoodfacts_client import OFFClient


def test_is_event_loop_closed_running_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OFFClient()

    class FakeLoop:
        def is_closed(self) -> bool:
            return True

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: FakeLoop())
    assert client._is_event_loop_closed(RuntimeError("any"))


def test_is_event_loop_closed_message(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OFFClient()

    def raise_running():
        raise RuntimeError("no running loop")

    def raise_event():
        raise RuntimeError("no loop either")

    monkeypatch.setattr(asyncio, "get_running_loop", raise_running)
    monkeypatch.setattr(asyncio, "get_event_loop", raise_event)
    assert client._is_event_loop_closed(RuntimeError("Event loop is closed"))


@pytest.mark.asyncio
async def test_offclient_close_suppresses_when_loop_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OFFClient()

    async def fake_aclose():
        raise RuntimeError("Event loop is closed")

    client.client = SimpleNamespace(aclose=fake_aclose)
    monkeypatch.setattr(client, "_is_event_loop_closed", lambda error: True)

    await client.close()  # should not raise


@pytest.mark.asyncio
async def test_offclient_close_reraises_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OFFClient()

    async def fake_aclose():
        raise RuntimeError("unexpected failure")

    client.client = SimpleNamespace(aclose=fake_aclose)
    monkeypatch.setattr(client, "_is_event_loop_closed", lambda error: False)

    with pytest.raises(RuntimeError):
        await client.close()
