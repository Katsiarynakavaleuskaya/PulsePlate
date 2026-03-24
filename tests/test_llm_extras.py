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
    res = llm._with_name(obj, "any")
    assert res is obj


def test_get_provider_stub_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "stub")

    provider = llm.get_provider()

    assert provider is not None
    assert getattr(provider, "name", "") == "stub"


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


def test_get_provider_perplexity_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    class _PerplexityProvider:
        name = "perplexity"

        def __init__(self, endpoint: str, model: str, api_key: str, /) -> None:
            self.endpoint = endpoint
            self.model = model
            self.api_key = api_key

        async def generate(self, text: str) -> str:
            return text

    monkeypatch.setattr(llm, "PerplexityProvider", _PerplexityProvider)
    monkeypatch.setenv("LLM_PROVIDER", "perplexity")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-key")
    monkeypatch.setenv("PERPLEXITY_MODEL", "sonar-pro")
    monkeypatch.setenv("PERPLEXITY_ENDPOINT", "https://api.perplexity.ai")

    provider = llm.get_provider()

    assert provider is not None
    assert getattr(provider, "name", "") == "perplexity"


def test_get_provider_perplexity_without_api_key_uses_lite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "perplexity")
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.setattr(llm, "PerplexityProvider", None)

    provider = llm.get_provider()

    assert provider is not None
    assert isinstance(provider, llm.PerplexityLiteProvider)
    assert getattr(provider, "name", "") == "perplexity"
