# -*- coding: utf-8 -*-
"""Tests for LLM module and providers."""

import os
from unittest.mock import patch

import pytest

# Import the modules to test
import llm
from providers import ProviderBase
from providers.stub import StubProvider


def test_stub_provider():
    """Test StubProvider functionality."""
    provider = StubProvider()
    assert provider.name == "stub"

    # Test generate method
    text = "Test input text"
    result = provider.generate(text)
    assert "stub" in result
    assert "Insight:" in result
    assert text[:120] in result


def test_get_provider_stub():
    """Test get_provider returns stub when no other provider is available."""
    # Mock environment to ensure stub is selected
    with patch.dict(os.environ, {"LLM_PROVIDER": "stub"}):
        provider = llm.get_provider()
        assert isinstance(provider, StubProvider)
        assert provider.name == "stub"


def test_get_provider_default():
    """Test get_provider returns stub by default when no provider is configured."""
    # Clear LLM_PROVIDER to test default behavior
    with patch.dict(os.environ, {}, clear=True):
        provider = llm.get_provider()
        assert isinstance(provider, StubProvider)
        assert provider.name == "stub"


def test_get_provider_auto_mode():
    """Test get_provider in auto mode falls back to stub when others fail."""
    with patch.dict(os.environ, {"LLM_PROVIDER": "auto"}):
        provider = llm.get_provider()
        assert isinstance(provider, StubProvider)
        assert provider.name == "stub"


def test_stub_provider_generate():
    """Test the _get_stub function directly."""
    provider = llm._get_stub()
    assert isinstance(provider, StubProvider)
    assert provider.name == "stub"


def test_get_provider_with_invalid_provider():
    """Test get_provider with an invalid provider name."""
    with patch.dict(os.environ, {"LLM_PROVIDER": "invalid"}):
        # Should fall back to stub
        provider = llm.get_provider()
        assert isinstance(provider, StubProvider)
        assert provider.name == "stub"


def test_provider_base_not_implemented():
    """Test that ProviderBase raises NotImplementedError for generate method."""
    base = ProviderBase()
    with pytest.raises(NotImplementedError):
        base.generate("test")


def test_llm_module_imports():
    """Test that llm module can be imported without errors."""
    # This test ensures the module structure is correct
    import llm as llm_module

    assert hasattr(llm_module, "get_provider")
    assert hasattr(llm_module, "StubProvider")
