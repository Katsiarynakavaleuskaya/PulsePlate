# -*- coding: utf-8 -*-
"""
Дополнительные тесты для покрытия llm.py и связанных веток.
"""

from __future__ import annotations

import pytest

import llm


def test__with_name_handles_attribute_error() -> None:
    # У некоторых веток llm.py нет вспомогательной функции _with_name.
    # Some llm.py revisions do not expose the _with_name helper.
    if not hasattr(llm, "_with_name"):
        assert hasattr(llm, "get_provider")
        return

    class NoAttrs:
        __slots__ = ()

    obj = NoAttrs()
    res = llm._with_name(obj, "any")  # type: ignore[attr-defined]
    assert res is obj


def test_get_provider_stub_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "stub")

    provider = llm.get_provider()

    assert provider is not None
    assert getattr(provider, "name", "") == "stub"


def test_get_provider_grok_env_block_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    class GrokProvider:
        name = "grok"

        def __init__(self, endpoint: str, model: str, api_key: str, /) -> None:
            self.endpoint = endpoint
            self.model = model
            self.api_key = api_key

        async def generate(self, text: str) -> str:
            return text

    monkeypatch.setattr(llm, "GrokProvider", GrokProvider)
    monkeypatch.setenv("GROK_API_KEY", "dummy")
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "grok")

    provider = llm.get_provider()

    assert provider is not None
    assert getattr(provider, "name", "") == "grok"


def test_get_provider_ollama_typeerror_posargs_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class OllamaProvider:
        name = "ollama"

        def __init__(self, endpoint: str, model: str, /) -> None:
            self.endpoint = endpoint
            self.model = model

        async def generate(self, text: str) -> str:
            return text

    monkeypatch.setattr(llm, "OllamaProvider", OllamaProvider)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    provider = llm.get_provider()

    assert provider is not None
    assert getattr(provider, "name", "") == "ollama"


def test_get_provider_ollama_import_error_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm, "OllamaProvider", None)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    provider = llm.get_provider()

    assert provider is not None
    assert isinstance(provider, llm.OllamaLiteProvider)
    assert getattr(provider, "name", "") == "ollama"


def test_get_provider_grok_missing_api_key_triggers_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class GrokProvider:
        name = "grok"

        def __init__(self, *args: object, **kwargs: object) -> None:
            self.args = args
            self.kwargs = kwargs

    monkeypatch.setattr(llm, "GrokProvider", GrokProvider)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "grok")

    provider = llm.get_provider()

    assert provider is not None
    assert isinstance(provider, llm.GrokLiteProvider)
    assert getattr(provider, "name", "") == "grok"
