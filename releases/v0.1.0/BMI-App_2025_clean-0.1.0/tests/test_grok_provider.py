# -*- coding: utf-8 -*-
"""Tests for GrokProvider."""

import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Mock the openai import to avoid dependency issues
with patch.dict("sys.modules", {"openai": MagicMock()}):
    from providers.grok import GrokProvider


@pytest.mark.asyncio
async def test_grok_provider_initialization():
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


@pytest.mark.asyncio
async def test_grok_provider_initialization_with_timeout():
    """Test GrokProvider initialization with custom timeout."""
    endpoint = "https://api.x.ai/v1"
    model = "grok-4-latest"
    api_key = "test-key"
    timeout = 60.0

    provider = GrokProvider(endpoint=endpoint, model=model, api_key=api_key, timeout=timeout)

    assert provider.timeout == timeout


@pytest.mark.asyncio
async def test_grok_provider_generate_success():
    """Test successful generation with GrokProvider."""
    with patch("providers.grok.OpenAI") as mock_openai:
        # Setup mock response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Test response"
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        provider = GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-4-latest", api_key="test-key"
        )

        # Mock the run_in_executor call directly
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_in_executor = AsyncMock(return_value=mock_response)
            mock_loop.return_value = mock_loop_instance

            result = await provider.generate("Test input")

            assert result == "Test response"
            mock_client.chat.completions.create.assert_called_once_with(
                model="grok-4-latest",
                messages=[{"role": "user", "content": "Test input"}],
                timeout=30.0,
            )


@pytest.mark.asyncio
async def test_grok_provider_generate_exception():
    """Test exception handling in GrokProvider."""
    with patch("providers.grok.OpenAI") as mock_openai:
        # Setup mock to raise an exception
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client

        provider = GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-4-latest", api_key="test-key"
        )

        # Mock the run_in_executor call to raise exception
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_in_executor = AsyncMock(side_effect=Exception("API Error"))
            mock_loop.return_value = mock_loop_instance

            with pytest.raises(RuntimeError, match="Grok error: Exception: API Error"):
                await provider.generate("Test input")


@pytest.mark.asyncio
async def test_grok_provider_invalid_response():
    """Test handling of invalid response structure."""
    with patch("providers.grok.OpenAI") as mock_openai:
        # Setup mock response with invalid structure
        mock_response = MagicMock()
        mock_response.choices = []  # Empty choices
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        provider = GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-4-latest", api_key="test-key"
        )

        # Mock the run_in_executor call
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_in_executor = AsyncMock(return_value=mock_response)
            mock_loop.return_value = mock_loop_instance

            with pytest.raises(RuntimeError, match="Invalid response: no choices found"):
                await provider.generate("Test input")


@pytest.mark.asyncio
async def test_grok_provider_non_string_content():
    """Test handling of non-string content in response."""
    with patch("providers.grok.OpenAI") as mock_openai:
        # Setup mock response with non-string content
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = 123  # Non-string content
        mock_response.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        provider = GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-4-latest", api_key="test-key"
        )

        # Mock the run_in_executor call
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_in_executor = AsyncMock(return_value=mock_response)
            mock_loop.return_value = mock_loop_instance

            with pytest.raises(RuntimeError, match="Invalid response: expected string content"):
                await provider.generate("Test input")
