# -*- coding: utf-8 -*-
"""Tests for PicoProvider."""

import pytest
from unittest.mock import patch, MagicMock

# Mock httpx to avoid dependency issues
with patch.dict("sys.modules", {"httpx": MagicMock()}):
    from providers.pico import PicoProvider


def test_pico_provider_initialization():
    """Test PicoProvider initialization with default values."""
    with patch.dict("os.environ", {}, clear=True):
        provider = PicoProvider()

        assert provider.name == "pico"
        assert provider.endpoint == "http://localhost:11434"
        assert provider.model == "llama3.1:8b"


def test_pico_provider_initialization_with_env_vars():
    """Test PicoProvider initialization with environment variables."""
    with patch.dict(
        "os.environ", {"PICO_ENDPOINT": "http://test-host:11434", "PICO_MODEL": "test-model"}
    ):
        provider = PicoProvider()

        assert provider.name == "pico"
        assert provider.endpoint == "http://test-host:11434"
        assert provider.model == "test-model"


def test_pico_provider_initialization_with_params():
    """Test PicoProvider initialization with explicit parameters."""
    provider = PicoProvider(
        endpoint="http://custom-host:11434", model="custom-model", api_key="test-key"
    )

    assert provider.name == "pico"
    assert provider.endpoint == "http://custom-host:11434"
    assert provider.model == "custom-model"


def test_pico_provider_generate_message_content():
    """Test generation with message content response."""
    with patch("providers.pico.httpx.Client") as mock_httpx:
        # Setup mock response with message content
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "Test message response"}}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        provider = PicoProvider()
        result = provider.generate("Test input")

        assert result == "Test message response"


def test_pico_provider_generate_choices():
    """Test generation with choices response."""
    with patch("providers.pico.httpx.Client") as mock_httpx:
        # Setup mock response with choices
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test choices response"}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        provider = PicoProvider()
        result = provider.generate("Test input")

        assert result == "Test choices response"


def test_pico_provider_generate_response():
    """Test generation with response field."""
    with patch("providers.pico.httpx.Client") as mock_httpx:
        # Setup mock response with response field
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Test response field"}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        provider = PicoProvider()
        result = provider.generate("Test input")

        assert result == "Test response field"


def test_pico_provider_generate_exception():
    """Test exception handling in PicoProvider."""
    with patch("providers.pico.httpx.Client") as mock_httpx:
        # Setup mock to raise an exception
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("API Error")
        mock_httpx.return_value = mock_client

        provider = PicoProvider()

        with pytest.raises(RuntimeError, match="Pico error: Exception: API Error"):
            provider.generate("Test input")
