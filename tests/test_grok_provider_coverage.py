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
        error = grok_module.APIConnectionError(request=MagicMock())
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
        # Client should be initialized (type may vary in test environment)
        assert provider.client is not None

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
            side_effect=[grok_module.APIConnectionError(request=MagicMock()), mock_response]
        )

        result = await provider.generate("Test prompt")
        assert result == "Success after connection error"
        assert provider.client.chat.completions.create.call_count == 2

    def test_rate_limit_error_is_transient(self) -> None:
        """Test that RateLimitError is considered transient."""
        error = grok_module.RateLimitError("Rate limit exceeded")
        assert grok_module.is_transient_exception(error) is True

    def test_api_status_error_429_is_transient(self) -> None:
        """Test that APIStatusError with 429 status is considered transient."""
        error = grok_module.APIStatusError("Rate limit", status_code=429)
        assert grok_module.is_transient_exception(error) is True

    def test_api_status_error_5xx_is_transient(self) -> None:
        """Test that APIStatusError with 5xx status is considered transient."""
        error = grok_module.APIStatusError("Server error", status_code=500)
        assert grok_module.is_transient_exception(error) is True
        error = grok_module.APIStatusError("Server error", status_code=599)
        assert grok_module.is_transient_exception(error) is True

    def test_api_status_error_4xx_not_transient(self) -> None:
        """Test that APIStatusError with 4xx status is not considered transient."""
        error = grok_module.APIStatusError("Client error", status_code=400)
        assert grok_module.is_transient_exception(error) is False
        error = grok_module.APIStatusError("Not found", status_code=404)
        assert grok_module.is_transient_exception(error) is False
        error = grok_module.APIStatusError("Unauthorized", status_code=401)
        assert grok_module.is_transient_exception(error) is False
        error = grok_module.APIStatusError("Forbidden", status_code=403)
        assert grok_module.is_transient_exception(error) is False

    def test_api_status_error_default_status_code(self) -> None:
        """Test that APIStatusError with default status code is considered transient."""
        error = grok_module.APIStatusError("Default error")
        assert grok_module.is_transient_exception(error) is True  # Default is 500

    @pytest.mark.asyncio
    async def test_grok_provider_generate_rate_limit_retry(self) -> None:
        """Test that rate limit errors are retried."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key"
        )

        # Mock the client to raise rate limit error first, then succeed
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after rate limit"

        provider.client.chat.completions.create = AsyncMock(
            side_effect=[grok_module.RateLimitError("Rate limit exceeded"), mock_response]
        )

        result = await provider.generate("Test prompt")
        assert result == "Success after rate limit"
        assert provider.client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_grok_provider_generate_api_status_error_retry(self) -> None:
        """Test that API status errors (5xx) are retried."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key"
        )

        # Mock the client to raise API status error first, then succeed
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after server error"

        provider.client.chat.completions.create = AsyncMock(
            side_effect=[grok_module.APIStatusError("Server error", status_code=500), mock_response]
        )

        result = await provider.generate("Test prompt")
        assert result == "Success after server error"
        assert provider.client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_grok_provider_generate_api_status_error_4xx_no_retry(self) -> None:
        """Test that API status errors (4xx) are not retried."""
        provider = grok_module.GrokProvider(
            endpoint="https://api.x.ai/v1", model="grok-beta", api_key="test-key"
        )

        # Mock the client to raise 4xx API status error
        provider.client.chat.completions.create = AsyncMock(
            side_effect=grok_module.APIStatusError("Bad request", status_code=400)
        )

        with pytest.raises(RuntimeError, match="Grok error: APIStatusError: Bad request"):
            await provider.generate("Test prompt")

        # Should not retry, so only one call
        assert provider.client.chat.completions.create.call_count == 1

    def test_extract_status_code_prefers_response(self) -> None:
        """Validate that response.status_code is used when present."""

        class FakeResponse:
            status_code = 512

        class FakeError(Exception):
            def __init__(self) -> None:
                self.response = FakeResponse()

        error = FakeError()
        assert grok_module._extract_status_code(error) == 512

    def test_extract_status_code_from_body_dict(self) -> None:
        """Validate that body['status'] is used when status_code absent."""

        class FakeError(Exception):
            def __init__(self) -> None:
                self.body = {"status": 503}

        error = FakeError()
        assert grok_module._extract_status_code(error) == 503

    def test_rate_limit_error_fallback_branch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure fallback RateLimitError branch is covered when tuple is empty."""
        original = grok_module._RATE_LIMIT_ERROR_TYPES
        monkeypatch.setattr(grok_module, "_RATE_LIMIT_ERROR_TYPES", ())
        try:
            error = grok_module.RateLimitError()
            assert grok_module.is_transient_exception(error) is True
        finally:
            monkeypatch.setattr(grok_module, "_RATE_LIMIT_ERROR_TYPES", original)

    def test_api_status_error_fallback_branch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure fallback APIStatusError branch works without registered types."""
        original = grok_module._STATUS_ERROR_TYPES
        monkeypatch.setattr(grok_module, "_STATUS_ERROR_TYPES", ())

        class FakeResponse:
            status_code = 502

        try:
            error = grok_module.APIStatusError("Server error", response=FakeResponse())
            assert grok_module.is_transient_exception(error) is True
        finally:
            monkeypatch.setattr(grok_module, "_STATUS_ERROR_TYPES", original)

    def test_api_status_error_preserves_extra_kwargs(self) -> None:
        """The fallback APIStatusError should expose custom kwargs as attributes."""
        error = grok_module.APIStatusError("Server error", request_id="abc123")
        assert getattr(error, "request_id") == "abc123"

    def test_extract_status_code_returns_none_when_absent(self) -> None:
        """Helper should return None when no status information is present."""
        assert grok_module._extract_status_code(Exception()) is None

    def test_status_error_tuple_branch_returns_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure branch handling registered status error types with unknown codes."""

        class DummyStatusError(Exception):
            """Simplified error without status attributes."""

        original = grok_module._STATUS_ERROR_TYPES
        monkeypatch.setattr(grok_module, "_STATUS_ERROR_TYPES", (DummyStatusError,))
        try:
            assert grok_module.is_transient_exception(DummyStatusError()) is False
        finally:
            monkeypatch.setattr(grok_module, "_STATUS_ERROR_TYPES", original)

    def test_api_status_error_missing_status_returns_false(self) -> None:
        """Ensure fallback branch returns False when status code cannot be derived."""
        original = grok_module._STATUS_ERROR_TYPES
        grok_module._STATUS_ERROR_TYPES = ()
        try:
            error = grok_module.APIStatusError("Indeterminate error")
            # Remove status_code attribute to test fallback
            if hasattr(error, "status_code"):
                delattr(error, "status_code")
            if hasattr(error, "response"):
                error.response = None
            if hasattr(error, "body"):
                error.body = None
            assert grok_module.is_transient_exception(error) is False
        finally:
            grok_module._STATUS_ERROR_TYPES = original
