# -*- coding: utf-8 -*-
"""Тесты для llm.py с полным покрытием."""

import pytest

from llm import get_provider


def test_get_provider_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    provider = get_provider()
    assert provider is not None
    assert hasattr(provider, "generate")
    assert provider.name == "stub"


def test_get_provider_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    provider = get_provider()
    assert provider is not None
    assert hasattr(provider, "generate")
    assert provider.name == "ollama"


def test_get_provider_perplexity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "perplexity")
    provider = get_provider()
    assert provider is not None
    assert hasattr(provider, "generate")
    assert provider.name == "perplexity"


def test_get_provider_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "invalid")
    provider = get_provider()
    assert provider is None


def test_get_provider_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    provider = get_provider()
    assert provider is None
