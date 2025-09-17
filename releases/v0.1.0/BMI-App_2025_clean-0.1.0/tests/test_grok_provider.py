# -*- coding: utf-8 -*-
"""Tests for GrokProvider."""

import pytest
from unittest.mock import patch, MagicMock

# Mock the openai import to avoid dependency issues
with patch.dict("sys.modules", {"openai": MagicMock()}):
    from providers.grok import GrokProvider


def test_grok_provider_initialization():
    """Test GrokProvider initialization."""
    endpoint = "https://api.x.ai/v1"
    model = "grok-4-latest"
    api_key = "test-key"

    provider = GrokProvider(endpoint=endpoint, model=model, api_key=api_key)

    assert provider.name == "grok"
    assert provider.endpoint == endpoint
    assert provider.model == model
    assert provider.api_key == api_key
    assert provider.timeout == 30.0


def test_grok_provider_initialization_with_timeout():
    """Test GrokProvider initialization with custom timeout."""
    endpoint = "https://api.x.ai/v1"
    model = "grok-4-latest"
    api_key = "test-key"
    timeout = 60.0

    provider = GrokProvider(endpoint=endpoint, model=model, api_key=api_key, timeout=timeout)

    assert provider.timeout == timeout


def test_grok_provider_generate_success():
    """Test successful generation with GrokProvider."""
    with patch("providers.grok.OpenAI") as mock_openai:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        provider = GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-4-latest", api_key="test-key"
        )

        result = provider.generate("Test input")

        assert result == "Test response"
        mock_client.chat.completions.create.assert_called_once_with(
            model="grok-4-latest",
            messages=[{"role": "user", "content": "Test input"}],
            timeout=30.0,
        )


def test_grok_provider_generate_exception():
    """Test exception handling in GrokProvider."""
    with patch("providers.grok.OpenAI") as mock_openai:
        # Setup mock to raise an exception
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client

        provider = GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-4-latest", api_key="test-key"
        )

        with pytest.raises(RuntimeError, match="Grok error: Exception: API Error"):
            provider.generate("Test input")
