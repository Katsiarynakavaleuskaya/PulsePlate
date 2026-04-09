# -*- coding: utf-8 -*-
"""
Дополнительные тесты для покрытия llm.py и связанных веток.
"""

from __future__ import annotations

import pytest

import llm


class _FailingPerplexityProvider:
    name = "perplexity"

    def __init__(self, *, endpoint: str, model: str, api_key: str) -> None:
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key

    async def generate(self, text: str) -> str:
        raise RuntimeError("perplexity down")


class _FailingOllamaProvider:
    name = "ollama"

    def __init__(
        self,
        endpoint: str,
        model: str,
        timeout_s: float | None = None,
        /,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.timeout_s = timeout_s

    async def generate(self, text: str) -> str:
        raise RuntimeError("ollama down")


class _FailingPrimaryProvider:
    name = "primary"

    async def generate(self, text: str) -> str:
        raise RuntimeError(f"primary failed: {text}")


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
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://ollama.local:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1:8b")

    provider = llm.get_provider()

    assert provider is not None
    assert isinstance(provider, OllamaProvider)
    assert provider.endpoint == "http://ollama.local:11434"
    assert provider.model == "llama3.1:8b"
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

        def __init__(self, *, endpoint: str, model: str, api_key: str) -> None:
            self.endpoint = endpoint
            self.model = model
            self.api_key = api_key

        async def generate(self, text: str) -> str:
            return text

    monkeypatch.setattr(llm, "PerplexityProvider", _PerplexityProvider)
    monkeypatch.setenv("LLM_PROVIDER", "perplexity")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-key")  # pragma: allowlist secret
    monkeypatch.setenv("PERPLEXITY_MODEL", "sonar-pro")
    monkeypatch.setenv("PERPLEXITY_ENDPOINT", "https://api.perplexity.ai")

    provider = llm.get_provider()

    assert provider is not None
    assert isinstance(provider, _PerplexityProvider)
    assert provider.endpoint == "https://api.perplexity.ai"
    assert provider.model == "sonar-pro"
    assert provider.api_key == "pplx-key"  # pragma: allowlist secret
    assert getattr(provider, "name", "") == "perplexity"


def test_get_provider_perplexity_without_api_key_uses_lite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _PerplexityProvider:
        name = "perplexity"

        def __init__(self, *, endpoint: str, model: str, api_key: str) -> None:
            self.endpoint = endpoint
            self.model = model
            self.api_key = api_key

        async def generate(self, text: str) -> str:
            return text

    monkeypatch.setenv("LLM_PROVIDER", "perplexity")
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.setattr(llm, "PerplexityProvider", _PerplexityProvider)

    provider = llm.get_provider()

    assert provider is not None
    assert isinstance(provider, llm.PerplexityLiteProvider)
    assert getattr(provider, "name", "") == "perplexity"


def test_get_provider_perplexity_placeholder_key_uses_lite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _PerplexityProvider:
        name = "perplexity"

        def __init__(self, *, endpoint: str, model: str, api_key: str) -> None:
            self.endpoint = endpoint
            self.model = model
            self.api_key = api_key

        async def generate(self, text: str) -> str:
            return text

    monkeypatch.setattr(llm, "PerplexityProvider", _PerplexityProvider)
    monkeypatch.setenv("LLM_PROVIDER", "perplexity")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "__replace_me__")

    provider = llm.get_provider()

    assert provider is not None
    assert isinstance(provider, llm.PerplexityLiteProvider)
    assert getattr(provider, "name", "") == "perplexity"


def test_get_insight_runtime_readiness_perplexity_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "perplexity")

    readiness = llm.get_insight_runtime_readiness()

    assert readiness["primary_provider"] == "perplexity"
    assert readiness["fallback_order"] == ["perplexity", "ollama", "stub"]
    assert readiness["feature_enabled"] is False
    assert readiness["echo_mode_provider"] is None


def test_get_insight_runtime_readiness_ollama_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    readiness = llm.get_insight_runtime_readiness()

    assert readiness["primary_provider"] == "ollama"
    assert readiness["fallback_order"] == ["ollama", "stub"]
    assert readiness["feature_enabled"] is False
    assert readiness["echo_mode_provider"] is None


def test_get_insight_runtime_readiness_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "unknown")

    readiness = llm.get_insight_runtime_readiness()

    assert readiness["primary_provider"] is None
    assert readiness["fallback_order"] == []
    assert readiness["feature_enabled"] is False
    assert readiness["echo_mode_provider"] is None


@pytest.mark.asyncio
async def test_get_provider_perplexity_runtime_falls_back_to_ollama_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm, "PerplexityProvider", _FailingPerplexityProvider)
    monkeypatch.setattr(llm, "OllamaProvider", None)
    monkeypatch.setenv("LLM_PROVIDER", "perplexity")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-live-key")  # pragma: allowlist secret

    provider = llm.get_provider()

    assert provider is not None
    assert getattr(provider, "name", "") == "perplexity"
    assert getattr(provider, "fallback_order", []) == ["perplexity", "ollama", "stub"]

    out = await provider.generate("ping")
    assert out == "[ollama-lite] ping"
    assert getattr(provider, "active_provider_name", "") == "ollama"


@pytest.mark.asyncio
async def test_get_provider_perplexity_runtime_falls_back_to_stub_when_chain_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm, "PerplexityProvider", _FailingPerplexityProvider)
    monkeypatch.setattr(llm, "OllamaProvider", _FailingOllamaProvider)
    monkeypatch.setenv("LLM_PROVIDER", "perplexity")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-live-key")  # pragma: allowlist secret

    provider = llm.get_provider()

    assert provider is not None
    out = await provider.generate("ping")
    assert out.startswith("[stub @ ")
    assert "Insight: ping" in out
    assert getattr(provider, "active_provider_name", "") == "stub"


@pytest.mark.asyncio
async def test_decorate_provider_with_fallback_reraises_last_error_without_fallbacks() -> None:
    provider = llm._decorate_provider_with_fallback(
        provider=_FailingPrimaryProvider(),
        primary_name="primary",
        fallback_builders=[],
    )

    with pytest.raises(RuntimeError, match="primary failed: ping"):
        await provider.generate("ping")
