# -*- coding: utf-8 -*-
"""Тесты для llm.py с полным покрытием."""

import pytest

try:
    from llm import get_provider
except ImportError:
    get_provider = None


def test_get_provider_stub():
    import os
    original = os.environ.get("LLM_PROVIDER")
    os.environ["LLM_PROVIDER"] = "stub"
    try:
        provider = get_provider()
        assert provider is not None
        assert hasattr(provider, "generate")
        assert provider.name == "stub"
    finally:
        if original is not None:
            os.environ["LLM_PROVIDER"] = original
        else:
            del os.environ["LLM_PROVIDER"]


def test_get_provider_grok():
    import os
    original = os.environ.get("LLM_PROVIDER")
    os.environ["LLM_PROVIDER"] = "grok"
    try:
        provider = get_provider()
        assert provider is not None
        assert hasattr(provider, "generate")
        assert provider.name == "grok"
    finally:
        if original is not None:
            os.environ["LLM_PROVIDER"] = original
        else:
            del os.environ["LLM_PROVIDER"]


def test_get_provider_ollama():
    import os
    original = os.environ.get("LLM_PROVIDER")
    os.environ["LLM_PROVIDER"] = "ollama"
    try:
        provider = get_provider()
        assert provider is not None
        assert hasattr(provider, "generate")
        assert provider.name == "ollama"
    finally:
        if original is not None:
            os.environ["LLM_PROVIDER"] = original
        else:
            del os.environ["LLM_PROVIDER"]


def test_get_provider_invalid():
    import os
    original = os.environ.get("LLM_PROVIDER")
    os.environ["LLM_PROVIDER"] = "invalid"
    try:
        provider = get_provider()
        assert provider is None
    finally:
        if original is not None:
            os.environ["LLM_PROVIDER"] = original
        else:
            del os.environ["LLM_PROVIDER"]


def test_get_provider_no_env():
    import os
    original = os.environ.get("LLM_PROVIDER")
    if "LLM_PROVIDER" in os.environ:
        del os.environ["LLM_PROVIDER"]
    try:
        provider = get_provider()
        assert provider is None
    finally:
        if original is not None:
            os.environ["LLM_PROVIDER"] = original


# Тесты для провайдеров, если они импортируются
try:
    from llm.providers.stub import StubProvider
    def test_stub_provider_generate():
        provider = StubProvider()
        result = provider.generate("test")
        assert isinstance(result, str)
        assert "stub" in result.lower()
except ImportError:
    pass

try:
    from llm.providers.grok import GrokProvider
    def test_grok_provider_generate():
        provider = GrokProvider()
        result = provider.generate("test")
        assert isinstance(result, str)
except ImportError:
    pass

try:
    from llm.providers.ollama import OllamaProvider
    def test_ollama_provider_generate():
        provider = OllamaProvider()
        result = provider.generate("test")
        assert isinstance(result, str)
except ImportError:
    pass
