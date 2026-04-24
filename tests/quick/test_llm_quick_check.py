"""
Quick tests to satisfy CI and provide minimal coverage for llm.get_provider.

These tests avoid external dependencies and network calls by targeting the
"stub" and "none" provider paths, ensuring deterministic behavior.
"""

import importlib
from typing import Any

import pytest


def _reload_llm() -> Any:
    import llm  # local module

    return importlib.reload(llm)


def test_llm_provider_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "none")
    llm = _reload_llm()
    assert llm.get_provider() is None


@pytest.mark.asyncio
async def test_llm_provider_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    llm = _reload_llm()
    provider = llm.get_provider()
    assert provider is not None
    out = await provider.generate("hello")
    assert out.startswith("[stub @ ")
    assert "hello" in out


@pytest.mark.asyncio
async def test_llm_provider_perplexity_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """When LLM_PROVIDER=perplexity without key, use perplexity-lite."""
    monkeypatch.setenv("LLM_PROVIDER", "perplexity")
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    llm = _reload_llm()
    provider = llm.get_provider()
    assert provider is not None
    out = await provider.generate("ping")
    assert out.startswith("[perplexity-lite] ")
    assert "ping" in out
