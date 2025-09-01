# -*- coding: utf-8 -*-
"""Изолированные юнит‑тесты для провайдеров: grok, ollama, pico.
Все сетевые вызовы замещаются фейковыми клиентами; ретраи не ждут времени,
т.к. мы обращаемся к __wrapped__ при необходимости.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from typing import Any, Dict

import httpx
import pytest

# ---------------- GrokProvider -----------------


def test_grok_generate_success(monkeypatch):

    class _Msg:
        def __init__(self, content: str):
            self.content = content

    class _Choice:
        def __init__(self, content: str):
            self.message = _Msg(content)

    class _Result:
        def __init__(self, content: str):
            self.choices = [_Choice(content)]

    class _FakeChat:
        async def create(self, *a, **kw):  # noqa: D401
            return _Result("  hello  ")

    class _FakeClient:
        def __init__(self, *a, **kw):
            self.chat = types.SimpleNamespace(completions=_FakeChat())

    openai_fake = types.ModuleType("openai")
    openai_fake.AsyncOpenAI = _FakeClient
    monkeypatch.setitem(sys.modules, "openai", openai_fake)
    # гарантируем, что модуль grok увидит наш openai
    if "providers.grok" in sys.modules:
        grok_mod = importlib.reload(sys.modules["providers.grok"])  # type: ignore[arg-type]
    else:
        from providers import grok as grok_mod  # type: ignore

    p = grok_mod.GrokProvider(endpoint="http://x", model="m", api_key="k")
    loop = asyncio.new_event_loop()
    try:
        out = loop.run_until_complete(p.generate("test"))
    finally:
        loop.close()
    assert out == "hello"  # content.strip()


def test_grok_generate_error_wrapped(monkeypatch):

    class _FakeChat:
        async def create(self, *a, **kw):
            raise RuntimeError("boom")

    class _FakeClient:
        def __init__(self, *a, **kw):
            self.chat = types.SimpleNamespace(completions=_FakeChat())

    openai_fake = types.ModuleType("openai")
    openai_fake.AsyncOpenAI = _FakeClient
    monkeypatch.setitem(sys.modules, "openai", openai_fake)
    if "providers.grok" in sys.modules:
        grok_mod = importlib.reload(sys.modules["providers.grok"])  # type: ignore[arg-type]
    else:
        from providers import grok as grok_mod  # type: ignore

    p = grok_mod.GrokProvider(endpoint="http://x", model="m", api_key="k")
    with pytest.raises(RuntimeError) as ei:
        # обходим декоратор retry
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                p.generate.__wrapped__(p, "oops")  # type: ignore[attr-defined]
            )
        finally:
            loop.close()
    assert "Grok error:" in str(ei.value)


# ---------------- OllamaProvider -----------------


class _FakeResp:
    def __init__(self, status_code: int, data: Dict[str, Any] | None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):  # noqa: D401
        return self._data


class _FakeAsyncClient:
    def __init__(self, chat_payload: Dict[str, Any] | None, gen_payload: Dict[str, Any] | None):
        self._chat_payload = chat_payload
        self._gen_payload = gen_payload

    async def __aenter__(self):  # noqa: D401
        return self

    async def __aexit__(self, *a):  # noqa: D401
        return False

    async def post(self, url: str, *a, **kw):  # noqa: D401
        if url.endswith("/api/chat"):
            return _FakeResp(200, self._chat_payload)
        if url.endswith("/api/generate"):
            return _FakeResp(200, self._gen_payload)
        return _FakeResp(404, {})


def test_ollama_chat_success(monkeypatch):
    from providers import ollama as ollama_mod

    def _factory(*a, **kw):
        return _FakeAsyncClient(chat_payload={"message": {"content": "hi"}}, gen_payload=None)

    monkeypatch.setattr(ollama_mod.httpx, "AsyncClient", _factory)

    p = ollama_mod.OllamaProvider(endpoint="http://localhost:11434", model="m")
    loop = asyncio.new_event_loop()
    try:
        out = loop.run_until_complete(p.generate("text"))
    finally:
        loop.close()
    assert out == "hi"


def test_ollama_generate_fallback_success(monkeypatch):
    from providers import ollama as ollama_mod

    def _factory(*a, **kw):
        # chat -> None, generate -> returns response
        return _FakeAsyncClient(chat_payload={"message": {"content": ""}}, gen_payload={"response": "ok"})

    monkeypatch.setattr(ollama_mod.httpx, "AsyncClient", _factory)

    p = ollama_mod.OllamaProvider(endpoint="http://localhost:11434", model="m")
    loop = asyncio.new_event_loop()
    try:
        out = loop.run_until_complete(p.generate("text"))
    finally:
        loop.close()
    assert out == "ok"


def test_ollama_unavailable_wrapped(monkeypatch):
    from providers import ollama as ollama_mod

    def _factory(*a, **kw):
        return _FakeAsyncClient(chat_payload={}, gen_payload={})

    monkeypatch.setattr(ollama_mod.httpx, "AsyncClient", _factory)

    p = ollama_mod.OllamaProvider(endpoint="http://localhost:11434", model="m")
    with pytest.raises(RuntimeError):
        # обойти retries
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                p.generate.__wrapped__(p, "text")  # type: ignore[attr-defined]
            )
        finally:
            loop.close()


def test_ollama_request_error_wrapped(monkeypatch):
    from providers import ollama as ollama_mod

    class _ErrClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            raise httpx.RequestError("boom")

    monkeypatch.setattr(ollama_mod.httpx, "AsyncClient", lambda *a, **kw: _ErrClient())

    p = ollama_mod.OllamaProvider(endpoint="http://localhost:11434", model="m")
    with pytest.raises(RuntimeError) as ei:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                p.generate.__wrapped__(p, "text")  # type: ignore[attr-defined]
            )
        finally:
            loop.close()
    assert "ollama_unavailable" in str(ei.value)


def test_ollama_timeout_env_default(monkeypatch):
    from providers import ollama as ollama_mod
    monkeypatch.setenv("OLLAMA_TIMEOUT", "not-a-float")
    p = ollama_mod.OllamaProvider(endpoint="http://localhost:11434", model="m")
    assert abs(p.timeout_s - 1.5) < 1e-6


# ---------------- PicoProvider -----------------


def _await_or_value(x):
    if asyncio.iscoroutine(x):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(x)
        finally:
            loop.close()
    return x


def test_pico_generate_variants(monkeypatch):
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
            pass

        def post(self, path: str, *a, **kw):
            # возвращаем разные совместимые структуры
            if path.endswith("/api/chat"):
                return _Resp({"message": {"content": " ok "}})
            raise AssertionError("unexpected path")

    monkeypatch.setattr(pico_mod.httpx, "Client", _Client)
    p = pico_mod.PicoProvider(endpoint="http://x")
    out = _await_or_value(p.generate("t"))
    assert out == "ok"


def test_pico_generate_http_error(monkeypatch):
    from providers import pico as pico_mod

    class _Resp:
        def raise_for_status(self):
            raise httpx.HTTPStatusError("bad", request=None, response=None)

        def json(self):  # pragma: no cover - не будет вызван
            return {}

    class _Client:
        def __init__(self, *a, **kw):
            pass

        def post(self, *a, **kw):
            return _Resp()

    monkeypatch.setattr(pico_mod.httpx, "Client", _Client)
    p = pico_mod.PicoProvider(endpoint="http://x")
    with pytest.raises(RuntimeError) as ei:
        _await_or_value(p.generate("t"))
    assert "Pico error:" in str(ei.value)


def test_ollama_helpers_non_200(monkeypatch):
    from providers import ollama as ollama_mod

    class _ClientNon200:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url: str, *a, **kw):
            return _FakeResp(500, {})

    monkeypatch.setattr(ollama_mod.httpx, "AsyncClient", lambda *a, **kw: _ClientNon200())
    p = ollama_mod.OllamaProvider(endpoint="http://x", model="m")
    loop = asyncio.new_event_loop()
    try:
        c = _ClientNon200()
        assert loop.run_until_complete(p._chat(c, "t")) is None
        assert loop.run_until_complete(p._generate(c, "t")) is None
    finally:
        loop.close()


def test_pico_generate_choices_and_response_and_else(monkeypatch):
    from providers import pico as pico_mod

    class _Resp2:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class _Client2:
        def __init__(self, *a, **kw):
            self.data = {"choices": [{"message": {"content": " A "}}]}

        def post(self, *a, **kw):
            return _Resp2(self.data)

    monkeypatch.setattr(pico_mod.httpx, "Client", _Client2)
    p = pico_mod.PicoProvider(endpoint="http://x")
    out = _await_or_value(p.generate("t"))
    assert out == "A"
    p.client.data = {"response": " B "}  # type: ignore[attr-defined]
    out = _await_or_value(p.generate("t"))
    assert out == "B"
    p.client.data = {"unknown": 1}  # type: ignore[attr-defined]
    out = _await_or_value(p.generate("t"))
    assert out == "{'unknown': 1}"
