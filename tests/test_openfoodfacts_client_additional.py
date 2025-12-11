from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from core.food_apis.openfoodfacts_client import OFFClient, OFFFoodItem


def test_is_event_loop_closed_running_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OFFClient()

    class FakeLoop:
        def is_closed(self) -> bool:
            return True

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: FakeLoop())
    assert client._is_event_loop_closed(RuntimeError("any"))


def test_is_event_loop_closed_running_loop_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """When running loop is open, helper should return False and avoid fallback."""
    client = OFFClient()

    class FakeLoop:
        def is_closed(self) -> bool:
            return False

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: FakeLoop())
    assert client._is_event_loop_closed(RuntimeError("other error")) is False


def test_is_event_loop_closed_message(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OFFClient()

    def raise_running():
        raise RuntimeError("no running loop")

    def raise_event():
        raise RuntimeError("no loop either")

    monkeypatch.setattr(asyncio, "get_running_loop", raise_running)
    monkeypatch.setattr(asyncio, "get_event_loop", raise_event)
    assert client._is_event_loop_closed(RuntimeError("Event loop is closed"))


def test_is_event_loop_closed_fallback_loop_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fallback get_event_loop() path returning a closed loop should be treated as closed."""
    client = OFFClient()

    class FakeLoop:
        def is_closed(self) -> bool:
            return True

    def raise_running():
        raise RuntimeError("no running loop")

    monkeypatch.setattr(asyncio, "get_running_loop", raise_running)
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: FakeLoop())

    assert client._is_event_loop_closed(RuntimeError("any error")) is True


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


@pytest.mark.asyncio
async def test_get_multiple_products_filters_exceptions_and_none() -> None:
    """get_multiple_products should filter out exceptions and None results."""
    client = OFFClient()

    async def get_details(barcode: str) -> OFFFoodItem | None:
        if barcode == "1":
            return OFFFoodItem(
                code=barcode,
                product_name=f"Product {barcode}",
                categories=[],
                nutrients_per_100g={},
                ingredients_text=None,
                brands=None,
                labels=[],
                countries=["World"],
                packaging=[],
                image_url=None,
                last_modified_t=0,
            )
        if barcode == "2":
            raise RuntimeError(f"boom {barcode}")
        # barcode == "3"
        return None

    client.get_product_details = get_details  # type: ignore[assignment]

    results = await client.get_multiple_products(["1", "2", "3"])
    # Only the valid OFFFoodItem should be returned
    assert len(results) == 1
    assert results[0].code == "1"
