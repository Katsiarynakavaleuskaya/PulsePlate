from typing import Any, Dict, TypeVar, Union
from collections.abc import Coroutine

import pytest

T = TypeVar("T")


def _await_or_value(x: Union[T, Coroutine[Any, Any, T]]) -> T:
    import asyncio

    if asyncio.iscoroutine(x):
        return asyncio.run(x)
    return x


def test_pico_response_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    from providers import pico as pico_mod

    class _Resp:
        def __init__(self, data: Dict[str, Any]) -> None:
            self._data = data

        def raise_for_status(self) -> None:
            return None

        def json(self) -> Dict[str, Any]:
            return self._data

    class _Client:
        def __init__(self, *a: Any, **kw: Any) -> None:
            self.data = {"response": " Z "}

        def post(self, *a: Any, **kw: Any) -> _Resp:
            return _Resp(self.data)

    monkeypatch.setattr(pico_mod.httpx, "Client", _Client)
    p = pico_mod.PicoProvider(endpoint="http://x")
    out = _await_or_value(p.generate("t"))
    assert out == "Z"


def test_pico_else_fallback_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    from providers import pico as pico_mod

    class _Resp:
        def __init__(self, data: Any) -> None:
            self._data = data

        def raise_for_status(self) -> None:
            return None

        def json(self) -> Any:
            return self._data

    class _Client:
        def __init__(self, *a: Any, **kw: Any) -> None:
            self.data = ["unknown"]

        def post(self, *a: Any, **kw: Any) -> _Resp:
            return _Resp(self.data)

    monkeypatch.setattr(pico_mod.httpx, "Client", _Client)
    p = pico_mod.PicoProvider(endpoint="http://x")
    out = _await_or_value(p.generate("t"))
    assert out == "['unknown']"
