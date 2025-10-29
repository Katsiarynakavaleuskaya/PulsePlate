"""
Simple tests for core/llm_enhanced.py to improve coverage.
"""

import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from core.llm_enhanced import EnhancedLLMProvider, LLMResponse, ResponseFormat


class TestEnhancedLLMProvider:
    """Test EnhancedLLMProvider basic functionality."""

    def test_init(self) -> None:
        """Test initialization."""
        mock_provider = Mock()
        provider = EnhancedLLMProvider(mock_provider)
        assert provider.base_provider == mock_provider

    def test_llm_response_to_dict(self):
        """Test LLMResponse to_dict method."""
        response = LLMResponse(
            content="test",
            format=ResponseFormat.JSON,
            is_valid=True,
            error_message=None,
            metadata={"key": "value"},
        )
        result = response.to_dict()
        assert result["content"] == "test"
        assert result["format"] == "json"
        assert result["is_valid"] is True
        assert result["metadata"] == {"key": "value"}

    def test_llm_response_to_dict_no_metadata(self):
        """Test LLMResponse to_dict with no metadata."""
        response = LLMResponse(
            content="test", format=ResponseFormat.TEXT, is_valid=False, error_message="error"
        )
        result = response.to_dict()
        assert result["metadata"] == {}

    @pytest.mark.asyncio
    async def test_generate_structured_success(self):
        """Test successful structured generation."""
        mock_provider = Mock()
        mock_provider.generate = AsyncMock(return_value='{"result": "Generated text"}')

        provider = EnhancedLLMProvider(mock_provider)
        result = await provider.generate_structured("test prompt")

        assert result.content == '{"result": "Generated text"}'
        assert result.format == ResponseFormat.JSON
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_generate_structured_error(self):
        """Test structured generation with error."""
        mock_provider = Mock()
        mock_provider.generate = AsyncMock(side_effect=Exception("Test error"))

        provider = EnhancedLLMProvider(mock_provider)
        result = await provider.generate_structured("test prompt")

        assert result.content == ""
        assert result.format == ResponseFormat.JSON
        assert result.is_valid is False
        assert "Test error" in result.error_message

    @pytest.mark.asyncio
    async def test_generate_structured_json_success(self):
        """Test successful structured JSON generation."""
        mock_provider = Mock()
        mock_provider.generate = AsyncMock(
            return_value='{"key": "value", "type": "object", "required": ["key"]}'
        )

        provider = EnhancedLLMProvider(mock_provider)
        result = await provider.generate_structured(
            "test prompt", ResponseFormat.JSON, {"type": "object"}
        )

        # Проверим, что содержимое содержит ожидаемые поля
        content = json.loads(result.content)
        assert content["key"] == "value"
        assert content["type"] == "object"
        assert result.format == ResponseFormat.JSON
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_generate_structured_invalid_json(self):
        """Test structured generation with invalid JSON."""
        mock_provider = Mock()
        mock_provider.generate = AsyncMock(return_value="invalid json")

        provider = EnhancedLLMProvider(mock_provider)
        result = await provider.generate_structured(
            "test prompt", ResponseFormat.JSON, {"type": "object"}
        )

        assert result.content == "invalid json"
        assert result.format == ResponseFormat.JSON
        assert result.is_valid is False
        assert "JSON" in result.error_message

    @pytest.mark.asyncio
    async def test_generate_structured_error_retry(self):
        """Test structured generation with error and retry."""
        mock_provider = Mock()
        mock_provider.generate = AsyncMock(side_effect=Exception("Test error"))

        provider = EnhancedLLMProvider(mock_provider)
        result = await provider.generate_structured(
            "test prompt", ResponseFormat.JSON, {"type": "object"}
        )

        assert result.content == ""
        assert result.format == ResponseFormat.JSON
        assert result.is_valid is False
        assert "Test error" in result.error_message

    def test_response_format_values(self):
        """Test ResponseFormat enum values."""
        assert ResponseFormat.JSON.value == "json"
        assert ResponseFormat.TEXT.value == "text"
        assert ResponseFormat.STRUCTURED.value == "structured"
