import pytest

import llm


@pytest.mark.asyncio
async def test_lite_providers_generate_text() -> None:
    """Validate that lite providers generate expected text output and integration behavior."""
    grok = llm.GrokLiteProvider()
    ollama = llm.OllamaLiteProvider()

    assert await grok.generate("hello") == "[grok-lite] hello"
    assert await ollama.generate("hello") == "[ollama-lite] hello"
