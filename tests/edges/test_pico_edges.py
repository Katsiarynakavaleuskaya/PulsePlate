from typing import Any, Dict


def _await_or_value(x):
    import asyncio

    if asyncio.iscoroutine(x):
        return asyncio.run(x)
    return x


def test_pico_response_branch(monkeypatch):
    from providers import pico as pico_mod

    class _Resp:
        def __init__(self, data: Dict[str, Any]):
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class _Client:
        def __init__(self, *a, **kw):
            self.data = {"response": " Z "}

        def post(self, *a, **kw):
            return _Resp(self.data)

    monkeypatch.setattr(pico_mod.httpx, "Client", _Client)
    p = pico_mod.PicoProvider(endpoint="http://x")
    out = _await_or_value(p.generate("t"))
    assert out == "Z"


def test_pico_else_fallback_branch(monkeypatch):
    from providers import pico as pico_mod

    class _Resp:
        def __init__(self, data: Any):
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class _Client:
        def __init__(self, *a, **kw):
            self.data = ["unknown"]

        def post(self, *a, **kw):
            return _Resp(self.data)

    monkeypatch.setattr(pico_mod.httpx, "Client", _Client)
    p = pico_mod.PicoProvider(endpoint="http://x")
    out = _await_or_value(p.generate("t"))
    assert out == "['unknown']"
