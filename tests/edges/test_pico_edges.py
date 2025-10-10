from collections.abc import Coroutine
from typing import Any, TypeVar, cast

import pytest


T = TypeVar("T")


def _await_or_value(x: T | Coroutine[Any, Any, T]) -> T:
    import asyncio

    return cast(T, asyncio.run(x)) if asyncio.iscoroutine(x) else x


# Shared mock classes for Pico provider testing
class _MockPicoResp:
    """Mock HTTP response for Pico provider tests."""

    def __init__(self, data: dict[str, Any] | list[str]) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any] | list[str]:
        return self._data


class _MockPicoClient:
    """Mock HTTP client for Pico provider tests."""

    def __init__(self, response_data: dict[str, Any] | list[str], *a: Any, **kw: Any) -> None:
        self.data = response_data

    def post(self, *a: Any, **kw: Any) -> _MockPicoResp:
        return _MockPicoResp(self.data)


@pytest.fixture
def mock_pico_client_dict():
    """Fixture providing a mock client that returns dict responses."""

    def _factory(response_data: dict[str, Any]):
        return lambda *a, **kw: _MockPicoClient(response_data, *a, **kw)

    return _factory


@pytest.fixture
def mock_pico_client_list():
    """Fixture providing a mock client that returns list responses."""

    def _factory(response_data: list[str]):
        return lambda *a, **kw: _MockPicoClient(response_data, *a, **kw)

    return _factory


def test_pico_response_branch(
    monkeypatch: pytest.MonkeyPatch,
    mock_pico_client_dict,
) -> None:
    from providers import pico as pico_mod

    client_factory = mock_pico_client_dict({"response": " Z "})
    monkeypatch.setattr(pico_mod.httpx, "Client", client_factory)
    p = pico_mod.PicoProvider(endpoint="http://x")
    out: str = _await_or_value(p.generate("t"))  # type: ignore[arg-type]
    assert out == "Z"


def test_pico_else_fallback_branch(
    monkeypatch: pytest.MonkeyPatch,
    mock_pico_client_list,
) -> None:
    from providers import pico as pico_mod

    client_factory = mock_pico_client_list(["unknown"])
    monkeypatch.setattr(pico_mod.httpx, "Client", client_factory)
    p = pico_mod.PicoProvider(endpoint="http://x")
    out: str = _await_or_value(p.generate("t"))  # type: ignore[arg-type]
    assert out == "['unknown']"
