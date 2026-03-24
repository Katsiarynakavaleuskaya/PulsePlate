import pytest

import llm


@pytest.mark.asyncio
async def test_lite_providers_generate_text() -> None:
    """Validate that lite providers generate expected text output and integration behavior."""
    perplexity = llm.PerplexityLiteProvider()
    ollama = llm.OllamaLiteProvider()

    assert await perplexity.generate("hello") == "[perplexity-lite] hello"
    assert await ollama.generate("hello") == "[ollama-lite] hello"


@pytest.mark.asyncio
async def test_lite_providers_empty_string() -> None:
    """Test that empty string input is handled correctly."""
    perplexity = llm.PerplexityLiteProvider()
    ollama = llm.OllamaLiteProvider()

    assert await perplexity.generate("") == "[perplexity-lite] "
    assert await ollama.generate("") == "[ollama-lite] "


@pytest.mark.asyncio
async def test_lite_providers_invalid_input_types() -> None:
    """Test that invalid input types are handled gracefully."""
    perplexity = llm.PerplexityLiteProvider()
    ollama = llm.OllamaLiteProvider()

    # Lite providers accept any input and return formatted string
    # They don't raise TypeError, they convert to string
    result_perplexity_none = await perplexity.generate(None)  # type: ignore[arg-type]
    assert isinstance(result_perplexity_none, str)
    assert "[perplexity-lite]" in result_perplexity_none

    result_ollama_none = await ollama.generate(None)  # type: ignore[arg-type]
    assert isinstance(result_ollama_none, str)
    assert "[ollama-lite]" in result_ollama_none

    result_perplexity_int = await perplexity.generate(123)  # type: ignore[arg-type]
    assert isinstance(result_perplexity_int, str)
    assert "123" in result_perplexity_int

    result_ollama_int = await ollama.generate(123)  # type: ignore[arg-type]
    assert isinstance(result_ollama_int, str)
    assert "123" in result_ollama_int


@pytest.mark.asyncio
async def test_lite_providers_special_characters_and_long_string() -> None:
    """Test that special characters and very long strings are handled correctly."""
    perplexity = llm.PerplexityLiteProvider()
    ollama = llm.OllamaLiteProvider()

    # Test special characters
    special_input = "Hello! @#$%^&*()[]{}|\\:;\"'<>?/~`"
    assert await perplexity.generate(special_input) == f"[perplexity-lite] {special_input}"
    assert await ollama.generate(special_input) == f"[ollama-lite] {special_input}"

    # Test very long string
    long_input = "a" * 10000
    assert await perplexity.generate(long_input) == f"[perplexity-lite] {long_input}"
    assert await ollama.generate(long_input) == f"[ollama-lite] {long_input}"


@pytest.mark.asyncio
async def test_get_provider_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the get_provider() factory function returns correct provider instances."""
    # Test perplexity provider
    monkeypatch.setenv("LLM_PROVIDER", "perplexity")
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    perplexity_provider = llm.get_provider()
    assert perplexity_provider is not None
    assert hasattr(perplexity_provider, "generate")
    result = await perplexity_provider.generate("test")
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
