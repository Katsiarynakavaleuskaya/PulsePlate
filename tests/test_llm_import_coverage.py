"""Targeted coverage tests for llm provider selector."""

from __future__ import annotations

import importlib
import os
import types
from importlib import reload
from unittest.mock import Mock, patch

import pytest

import llm


def _llm_live() -> types.ModuleType:
    """Canonical ``llm`` module (matches ``sys.modules``).

    Some tests delete and re-import ``llm``; a module-level ``import llm`` can
    become stale so ``importlib.reload`` raises ImportError (wrong object vs
    ``sys.modules['llm']``).
    """

    return importlib.import_module("llm")


@pytest.fixture(autouse=True)
def _llm_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")


class TestImportFallbacks:
    def test_perplexity_import_exception_coverage(self) -> None:
        global llm

        llm_mod = _llm_live()
        original_import_module = importlib.import_module
        with patch("importlib.import_module") as mock_import:

            def import_side_effect(name: str, package: str | None = None):
                if name == "providers.perplexity":
                    raise ImportError("No module named providers.perplexity")
                return original_import_module(name, package)

            mock_import.side_effect = import_side_effect
            reload(llm_mod)
            assert llm_mod.PerplexityProvider is None
            assert hasattr(llm_mod, "PerplexityLiteProvider")

        # Use reload(importlib.import_module("llm")) so repo AST policy can resolve the
        # target (forbid obfuscated reload(call()) patterns); _llm_live() is still the
        # runtime-safe accessor when tests evict sys.modules["llm"].
        llm = reload(importlib.import_module("llm"))

    @pytest.mark.asyncio
    async def test_perplexity_lite_provider_generate_coverage(self) -> None:
        llm_mod = _llm_live()
        provider = llm_mod.PerplexityLiteProvider()
        assert provider.name == "perplexity"
        result = await provider.generate("test input")
        assert result.startswith("[perplexity-lite] ")
        assert result.endswith("test input")


class TestGetProviderEdgeCases:
    def test_get_provider_with_pico(self) -> None:
        with patch.dict(os.environ, {"LLM_PROVIDER": "pico"}, clear=False):
            assert llm.get_provider() is None

    def test_get_provider_ollama_with_exception_coverage(self) -> None:
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
            with patch.object(llm, "OllamaProvider") as mock_ollama:
                mock_ollama.side_effect = [TypeError("keyword error"), Exception("creation failed")]
                provider = llm.get_provider()
                assert provider is not None
                assert provider.name == "ollama"
                assert mock_ollama.call_count == 2

    @patch("llm.PerplexityProvider")
    def test_perplexity_provider_keyword_exception_fallback(
        self, mock_perplexity_class: Mock
    ) -> None:
        mock_perplexity_class.side_effect = TypeError("unexpected keyword")
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "perplexity", "PERPLEXITY_API_KEY": "dummy"},
            clear=False,
        ):
            provider = llm.get_provider()
            assert provider is not None
            assert provider.name == "perplexity"
            assert mock_perplexity_class.call_count == 1

    def test_get_provider_perplexity_without_real_provider(self) -> None:
        with patch.dict(os.environ, {"LLM_PROVIDER": "perplexity"}, clear=False):
            with patch.object(llm, "PerplexityProvider", None):
                provider = llm.get_provider()
                assert provider is not None
                assert provider.name == "perplexity"


class TestEnvironmentVariableEdgeCases:
    def test_empty_string_values(self) -> None:
        empty_values = ["", " ", "\t", "\n", "\r\n", "  \t\n  "]
        for empty_val in empty_values:
            with patch.dict(os.environ, {"LLM_PROVIDER": empty_val}, clear=False):
                assert llm.get_provider() is None

    def test_case_variations(self) -> None:
        stub_variations = ["stub", "STUB", "Stub", "StUb", "sTuB"]
        for variation in stub_variations:
            with patch.dict(os.environ, {"LLM_PROVIDER": variation}, clear=False):
                provider = llm.get_provider()
                assert provider is not None
                assert provider.name == "stub"

        perplexity_variations = ["perplexity", "PERPLEXITY", "Perplexity", "PeRpLeXiTy"]
        for variation in perplexity_variations:
            with patch.dict(os.environ, {"LLM_PROVIDER": variation}, clear=False):
                provider = llm.get_provider()
                assert provider is not None
                assert provider.name == "perplexity"

    def test_special_none_values(self) -> None:
        none_values = ["none", "NONE", "None", "no", "NO", "No"]
        for none_val in none_values:
            with patch.dict(os.environ, {"LLM_PROVIDER": none_val}, clear=False):
                assert llm.get_provider() is None
