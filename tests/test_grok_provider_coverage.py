"""Comprehensive coverage tests for providers/grok.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from openai import AsyncOpenAI
import pytest

import providers.grok as grok_module


class TestIsTransientException:
    """Test is_transient_exception function for all error types."""

    def test_apitimeout_error_is_transient(self) -> None:
        """Test that APITimeoutError is considered transient."""
        error = grok_module.APITimeoutError("Timeout")
        assert grok_module.is_transient_exception(error) is True

    def test_apiconnection_error_is_transient(self) -> None:
        """Test that APIConnectionError is considered transient."""
        error = grok_module.APIConnectionError("Connection failed")
        assert grok_module.is_transient_exception(error) is True

    def test_other_exceptions_not_transient(self) -> None:
        """Test that other exception types are not considered transient."""
        exceptions = [
            ValueError("Invalid value"),
            RuntimeError("Runtime error"),
            KeyError("Missing key"),
            TypeError("Type error"),
        ]
        for exc in exceptions:
            assert grok_module.is_transient_exception(exc) is False


class TestGrokProvider:
    """Test GrokProvider class functionality."""

    def test_grok_provider_initialization(self) -> None:
        """Test GrokProvider initialization."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key", timeout=30.0
        )

        assert provider.name == "grok"
        assert provider.endpoint == "https://api.x.ai/v1"
        assert provider.model == "grok-beta"
        assert provider.api_key == "test-key"
        assert provider.timeout == 30.0
        assert isinstance(provider.client, AsyncOpenAI)

    def test_grok_provider_endpoint_stripping(self) -> None:
        """Test that endpoint trailing slash is stripped."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1/", model="grok-beta", api_key="test-key"
        )
        assert provider.endpoint == "https://api.x.ai/v1"

    def test_grok_provider_default_timeout(self) -> None:
        """Test that default timeout is set when not provided."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key"
        )
        assert provider.timeout == 30.0

    @pytest.mark.asyncio
    async def test_grok_provider_generate_success(self) -> None:
        """Test successful generation."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key"
        )

        # Mock the client response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"

        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await provider.generate("Test prompt")
        assert result == "Test response"

    @pytest.mark.asyncio
    async def test_grok_provider_generate_empty_content(self) -> None:
        """Test generation with empty content."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key"
        )

        # Mock the client response with None content
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await provider.generate("Test prompt")
        assert result == ""

    @pytest.mark.asyncio
    async def test_grok_provider_generate_whitespace_content(self) -> None:
        """Test generation with whitespace content that gets stripped."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key"
        )

        # Mock the client response with whitespace content
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "  \n  Test response  \n  "

        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await provider.generate("Test prompt")
        assert result == "Test response"

    @pytest.mark.asyncio
    async def test_grok_provider_generate_transient_error_retry(self) -> None:
        """Test that transient errors are retried."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key"
        )

        # Mock the client to raise transient error first, then succeed
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after retry"

        provider.client.chat.completions.create = AsyncMock(
            side_effect=[grok_module.APITimeoutError("Timeout"), mock_response]
        )

        result = await provider.generate("Test prompt")
        assert result == "Success after retry"
        assert provider.client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_grok_provider_generate_generic_exception(self) -> None:
        """Test that generic exceptions are wrapped in RuntimeError."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key"
        )

        # Mock the client to raise generic exception
        provider.client.chat.completions.create = AsyncMock(side_effect=ValueError("Invalid input"))

        with pytest.raises(RuntimeError, match="Grok error: ValueError: Invalid input"):
            await provider.generate("Test prompt")

    @pytest.mark.asyncio
    async def test_grok_provider_generate_max_retries_exceeded(self) -> None:
        """Test that max retries are respected."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key"
        )

        # Mock the client to always raise transient error
        provider.client.chat.completions.create = AsyncMock(
            side_effect=grok_module.APITimeoutError("Request timed out.")
        )

        with pytest.raises(grok_module.APITimeoutError, match="Request timed out."):
            await provider.generate("Test prompt")

    @pytest.mark.asyncio
    async def test_grok_provider_generate_with_custom_timeout(self) -> None:
        """Test generation with custom timeout."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key", timeout=60.0
        )

        # Mock the client response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"

        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.generate("Test prompt")

        # Check that timeout was passed to the client
        provider.client.chat.completions.create.assert_called_once_with(
            model="grok-beta", messages=[{"role": "user", "content": "Test prompt"}], timeout=60.0
        )

    @pytest.mark.asyncio
    async def test_grok_provider_generate_connection_error_retry(self) -> None:
        """Test that connection errors are retried."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key"
        )

        # Mock the client to raise connection error first, then succeed
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after connection error"

        provider.client.chat.completions.create = AsyncMock(
            side_effect=[grok_module.APIConnectionError("Connection failed"), mock_response]
        )

        result = await provider.generate("Test prompt")
        assert result == "Success after connection error"
        assert provider.client.chat.completions.create.call_count == 2
