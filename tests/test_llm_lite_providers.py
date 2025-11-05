import pytest

import llm


@pytest.mark.asyncio
async def test_lite_providers_generate_text() -> None:
    """Validate that lite providers generate expected text output and integration behavior."""
    grok = llm.GrokLiteProvider()
    ollama = llm.OllamaLiteProvider()

    assert await grok.generate("hello") == "[grok-lite] hello"
    assert await ollama.generate("hello") == "[ollama-lite] hello"


@pytest.mark.asyncio
async def test_lite_providers_empty_string() -> None:
    """Test that empty string input is handled correctly."""
    grok = llm.GrokLiteProvider()
    ollama = llm.OllamaLiteProvider()

    assert await grok.generate("") == "[grok-lite] "
    assert await ollama.generate("") == "[ollama-lite] "


@pytest.mark.asyncio
async def test_lite_providers_invalid_input_types() -> None:
    """Test that invalid input types are handled gracefully."""
    grok = llm.GrokLiteProvider()
    ollama = llm.OllamaLiteProvider()

    # Lite providers accept any input and return formatted string
    # They don't raise TypeError, they convert to string
    result_grok_none = await grok.generate(None)  # type: ignore[arg-type]
    assert isinstance(result_grok_none, str)
    assert "[grok-lite]" in result_grok_none

    result_ollama_none = await ollama.generate(None)  # type: ignore[arg-type]
    assert isinstance(result_ollama_none, str)
    assert "[ollama-lite]" in result_ollama_none

    result_grok_int = await grok.generate(123)  # type: ignore[arg-type]
    assert isinstance(result_grok_int, str)
    assert "123" in result_grok_int

    result_ollama_int = await ollama.generate(123)  # type: ignore[arg-type]
    assert isinstance(result_ollama_int, str)
    assert "123" in result_ollama_int


@pytest.mark.asyncio
async def test_lite_providers_special_characters_and_long_string() -> None:
    """Test that special characters and very long strings are handled correctly."""
    grok = llm.GrokLiteProvider()
    ollama = llm.OllamaLiteProvider()

    # Test special characters
    special_input = "Hello! @#$%^&*()[]{}|\\:;\"'<>?/~`"
    assert await grok.generate(special_input) == f"[grok-lite] {special_input}"
    assert await ollama.generate(special_input) == f"[ollama-lite] {special_input}"

    # Test very long string
    long_input = "a" * 10000
    assert await grok.generate(long_input) == f"[grok-lite] {long_input}"
    assert await ollama.generate(long_input) == f"[ollama-lite] {long_input}"


@pytest.mark.asyncio
async def test_get_provider_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the get_provider() factory function returns correct provider instances."""
    # Test grok provider
    monkeypatch.setenv("LLM_PROVIDER", "grok")
    grok_provider = llm.get_provider()
    assert grok_provider is not None
    # Provider could be GrokLiteProvider or GrokProvider depending on availability
    assert hasattr(grok_provider, "generate")
    result = await grok_provider.generate("test")
    assert isinstance(result, str)
    assert "test" in result

    # Test ollama provider - may return OllamaLiteProvider if OllamaProvider unavailable
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    # Clear any cached provider if needed
    ollama_provider = llm.get_provider()
    assert ollama_provider is not None
    # Provider could be OllamaLiteProvider or OllamaProvider depending on availability
    assert hasattr(ollama_provider, "generate")
    try:
        result = await ollama_provider.generate("test")
        assert isinstance(result, str)
        assert "test" in result
    except RuntimeError as e:
        # If OllamaProvider is unavailable and raises RuntimeError, that's expected
        # The lite provider should handle this gracefully
        if "ollama" in str(e).lower() or "unavailable" in str(e).lower():
            # Try to get lite provider directly
            lite = llm.OllamaLiteProvider()
            result = await lite.generate("test")
            assert isinstance(result, str)
            assert "[ollama-lite]" in result
        else:
            raise
