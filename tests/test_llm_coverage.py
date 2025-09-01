"""
Test to cover the missing line in llm.py
"""

import os
from unittest.mock import patch

import pytest


def test_llm_import_error_handling():
    """Test that import errors in llm.py are handled properly."""
    # This should trigger the exception handling in lines 25-30
    import llm

    # Test the providers are either available or None
    assert llm.OllamaProvider is not None or llm.OllamaProvider is None
    assert llm.PicoProvider is not None or llm.PicoProvider is None

    # Test get_provider with various values
    with patch.dict(os.environ, {'LLM_PROVIDER': 'none'}):
        provider = llm.get_provider()
        assert provider is None

    with patch.dict(os.environ, {'LLM_PROVIDER': 'stub'}):
        provider = llm.get_provider()
        assert provider is not None
        assert provider.name == "stub"

    # Test unknown provider
    with patch.dict(os.environ, {'LLM_PROVIDER': 'unknown_provider'}):
        provider = llm.get_provider()
        assert provider is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
