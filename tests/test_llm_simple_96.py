"""
Simple tests to improve coverage in llm.py for 96%+ coverage.
"""

import os
from unittest.mock import Mock, patch

from llm import get_provider


class TestLlmSimple96:
    """Simple tests to cover missing lines in llm.py for 96%+ coverage."""

    def test_get_provider_grok_keyword_args_fail(self):
        """Test get_provider with PerplexityProvider keyword args failure - line 71-77."""
        with (
            patch("llm.PerplexityProvider") as mock_grok_provider,
            patch("llm.PerplexityLiteProvider") as mock_grok_lite,
            patch.dict(
                os.environ,
                {
                    "LLM_PROVIDER": "perplexity",
                    "PERPLEXITY_ENDPOINT": "http://test",
                    "PERPLEXITY_API_KEY": "test_key",
                    "PERPLEXITY_MODEL": "test_model",
                },
            ),
        ):
            # Mock keyword args failure
            mock_grok_provider.side_effect = [
                TypeError("Keyword args failed"),  # First call fails
                Mock(),  # Second call succeeds
            ]
            mock_lite_provider = Mock()
            mock_grok_lite.return_value = mock_lite_provider

            result = get_provider()

            # Perplexity path currently performs a single constructor attempt.
            assert mock_grok_provider.call_count == 1
            assert result is not None

    def test_get_provider_grok_both_fail(self):
        """Test get_provider with PerplexityProvider both calls fail - line 75-77."""
        with (
            patch("llm.PerplexityProvider") as mock_grok_provider,
            patch("llm.PerplexityLiteProvider") as mock_grok_lite,
            patch.dict(
                os.environ,
                {
                    "LLM_PROVIDER": "perplexity",
                    "PERPLEXITY_ENDPOINT": "http://test",
                    "PERPLEXITY_API_KEY": "test_key",
                    "PERPLEXITY_MODEL": "test_model",
                },
            ),
        ):
            # Mock both calls fail
            mock_grok_provider.side_effect = [
                TypeError("Keyword args failed"),  # First call fails
                Exception("Positional args failed"),  # Second call fails
            ]
            mock_lite_provider = Mock()
            mock_grok_lite.return_value = mock_lite_provider

            result = get_provider()

            # Should fallback to lite provider
            mock_grok_lite.assert_called_once()
            assert result == mock_lite_provider

    def test_get_provider_ollama_keyword_args_fail(self):
        """Test get_provider with OllamaProvider keyword args failure - line 88-92."""
        with (
            patch("llm.OllamaProvider") as mock_ollama_provider,
            patch.dict(
                os.environ,
                {
                    "LLM_PROVIDER": "ollama",
                    "OLLAMA_ENDPOINT": "http://test",
                    "OLLAMA_MODEL": "test_model",
                    "OLLAMA_TIMEOUT": "5",
                },
            ),
        ):
            # Mock keyword args failure, then positional args succeeds
            mock_success_instance = Mock()
            mock_ollama_provider.side_effect = [
                TypeError("Keyword args failed"),  # First call fails
                mock_success_instance,  # Second call succeeds
            ]

            result = get_provider()

            # Should try keyword args first, then positional args
            assert mock_ollama_provider.call_count == 2
            assert result is not None
            assert result == mock_success_instance

    def test_get_provider_ollama_both_fail(self):
        """Test get_provider with OllamaProvider both calls fail - line 90-94."""
        with (
            patch("llm.OllamaProvider") as mock_ollama_provider,
            patch.dict(
                os.environ,
                {
                    "LLM_PROVIDER": "ollama",
                    "OLLAMA_ENDPOINT": "http://test",
                    "OLLAMA_MODEL": "test_model",
                    "OLLAMA_TIMEOUT": "5",
                },
            ),
        ):
            # Mock both calls fail
            mock_ollama_provider.side_effect = [
                TypeError("Keyword args failed"),  # First call fails
                Exception("Positional args failed"),  # Second call fails
            ]

            result = get_provider()

            # Should fallback to OllamaLiteProvider when both fail (консистентно с PerplexityProvider)
            assert result is not None
            assert result.name == "ollama"

    def test_get_provider_ollama_timeout_float_conversion(self):
        """Test get_provider with OllamaProvider timeout float conversion - line 85."""
        with (
            patch("llm.OllamaProvider") as mock_ollama_provider,
            patch.dict(
                os.environ,
                {
                    "LLM_PROVIDER": "ollama",
                    "OLLAMA_ENDPOINT": "http://test",
                    "OLLAMA_MODEL": "test_model",
                    "OLLAMA_TIMEOUT": "10.5",
                },
            ),
        ):
            mock_provider = Mock()
            mock_ollama_provider.return_value = mock_provider

            result = get_provider()

            # Should convert timeout to float
            mock_ollama_provider.assert_called_once_with(
                endpoint="http://test", model="test_model", timeout_s=10.5
            )
            assert result == mock_provider

    def test_get_provider_ollama_default_timeout(self):
        """Test get_provider with OllamaProvider default timeout - line 85."""
        with (
            patch("llm.OllamaProvider") as mock_ollama_provider,
            patch.dict(
                os.environ,
                {
                    "LLM_PROVIDER": "ollama",
                    "OLLAMA_ENDPOINT": "http://test",
                    "OLLAMA_MODEL": "test_model",
                },
                clear=True,
            ),
        ):
            mock_provider = Mock()
            mock_ollama_provider.return_value = mock_provider

            result = get_provider()

            # Should use default timeout of 1.5
            mock_ollama_provider.assert_called_once_with(
                endpoint="http://test", model="test_model", timeout_s=1.5
            )
            assert result == mock_provider

    def test_get_provider_ollama_default_endpoint(self):
        """Test get_provider with OllamaProvider default endpoint - line 82."""
        with (
            patch("llm.OllamaProvider") as mock_ollama_provider,
            patch.dict(
                os.environ,
                {"LLM_PROVIDER": "ollama", "OLLAMA_MODEL": "test_model"},
                clear=True,
            ),
        ):
            mock_provider = Mock()
            mock_ollama_provider.return_value = mock_provider

            result = get_provider()

            # Should use default endpoint
            mock_ollama_provider.assert_called_once_with(
                endpoint="http://localhost:11434", model="test_model", timeout_s=1.5
            )
            assert result == mock_provider

    def test_get_provider_ollama_default_model(self):
        """Test get_provider with OllamaProvider default model - line 83."""
        with (
            patch("llm.OllamaProvider") as mock_ollama_provider,
            patch.dict(
                os.environ,
                {"LLM_PROVIDER": "ollama", "OLLAMA_ENDPOINT": "http://test"},
                clear=True,
            ),
        ):
            mock_provider = Mock()
            mock_ollama_provider.return_value = mock_provider

            result = get_provider()

            # Should use default model
            mock_ollama_provider.assert_called_once_with(
                endpoint="http://test", model="llama3.1:8b", timeout_s=1.5
            )
            assert result == mock_provider

    def test_get_provider_grok_fallback_when_unavailable(self):
        """Test get_provider with PerplexityProvider fallback when unavailable - line 78-79."""
        with (
            patch("llm.PerplexityProvider", None),
            patch("llm.PerplexityLiteProvider") as mock_grok_lite,
            patch.dict(os.environ, {"LLM_PROVIDER": "perplexity"}),
        ):
            mock_lite_provider = Mock()
            mock_grok_lite.return_value = mock_lite_provider

            result = get_provider()

            # Should fallback to lite provider when PerplexityProvider is None
            mock_grok_lite.assert_called_once()
            assert result == mock_lite_provider

    def test_get_provider_ollama_when_unavailable(self):
        """Test get_provider with OllamaProvider when unavailable."""
        with patch("llm.OllamaProvider", None), patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}):
            result = get_provider()

            # Should fallback to OllamaLiteProvider when OllamaProvider is None (consistent with PerplexityProvider)
            assert result is not None
            assert result.name == "ollama"

    def test_get_provider_unknown_provider(self):
        """Test get_provider with unknown provider."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "unknown"}):
            result = get_provider()

            # Should return None for unknown provider
            assert result is None
