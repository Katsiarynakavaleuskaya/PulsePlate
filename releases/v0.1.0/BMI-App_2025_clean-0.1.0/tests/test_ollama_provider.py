# -*- coding: utf-8 -*-
"""Tests for OllamaProvider."""

import pytest
from unittest.mock import patch, MagicMock

# Mock httpx to avoid dependency issues
with patch.dict("sys.modules", {"httpx": MagicMock()}):
    from providers.ollama import OllamaProvider


def test_ollama_provider_initialization():
    """Test OllamaProvider initialization."""
    provider = OllamaProvider()

    assert provider.name == "ollama"
    assert provider.endpoint == "http://localhost:11434"
    assert provider.model == "llama3.1:8b"
    assert provider.timeout_s == 120.0


def test_ollama_provider_initialization_custom():
    """Test OllamaProvider initialization with custom parameters."""
    endpoint = "http://custom-host:11434"
    model = "custom-model"
    timeout = 60.0

    provider = OllamaProvider(endpoint=endpoint, model=model, timeout_s=timeout)

    assert provider.name == "ollama"
    assert provider.endpoint == endpoint
    assert provider.model == model
    assert provider.timeout_s == timeout


def test_ollama_provider_generate_chat_success():
    """Test successful generation using /api/chat endpoint."""
    with patch("providers.ollama.httpx.Client") as mock_httpx:
        # Setup mock response for /api/chat
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "Test chat response"}}
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        provider = OllamaProvider()
        result = provider.generate("Test input")

        assert result == "Test chat response"
        mock_client.post.assert_called_once_with(
            "http://localhost:11434/api/chat",
            json={
                "model": "llama3.1:8b",
                "messages": [{"role": "user", "content": "Test input"}],
                "stream": False,
            },
            headers={"Content-Type": "application/json"},
        )


def test_ollama_provider_generate_fallback_to_generate():
    """Test fallback to /api/generate when /api/chat fails."""
    with patch("providers.ollama.httpx.Client") as mock_httpx:
        # Setup mock responses - first call fails, second succeeds
        mock_chat_response = MagicMock()
        mock_chat_response.status_code = 500  # Simulate failure

        mock_generate_response = MagicMock()
        mock_generate_response.status_code = 200
        mock_generate_response.json.return_value = {"response": "Test generate response"}

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = [mock_chat_response, mock_generate_response]
        mock_httpx.return_value = mock_client

        provider = OllamaProvider()
        result = provider.generate("Test input")

        assert result == "Test generate response"
        assert mock_client.post.call_count == 2


def test_ollama_provider_generate_both_endpoints_fail():
    """Test exception when both endpoints fail."""
    with patch("providers.ollama.httpx.Client") as mock_httpx:
        # Setup mock to raise exceptions
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = Exception("Network error")
        mock_httpx.return_value = mock_client

        provider = OllamaProvider()

        with pytest.raises(RuntimeError, match="Ollama error: Exception: Network error"):
            provider.generate("Test input")


def test_ollama_provider_generate_empty_response():
    """Test handling of empty response from /api/generate."""
    with patch("providers.ollama.httpx.Client") as mock_httpx:
        # Setup mock responses - chat fails, generate returns empty
        mock_chat_response = MagicMock()
        mock_chat_response.status_code = 500

        mock_generate_response = MagicMock()
        mock_generate_response.status_code = 200
        mock_generate_response.json.return_value = {"response": ""}

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = [mock_chat_response, mock_generate_response]
        mock_httpx.return_value = mock_client

        provider = OllamaProvider()

        with pytest.raises(RuntimeError, match="Empty response from /api/generate"):
            provider.generate("Test input")
