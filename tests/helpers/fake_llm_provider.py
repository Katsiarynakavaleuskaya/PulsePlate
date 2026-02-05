"""Deterministic fake LLM provider for tests (no network).

RU: Детерминированный fake LLM provider для тестов (без сети).
EN: Deterministic fake LLM provider for tests (no network).
"""

from __future__ import annotations


class FakeLLMProvider:
    """Deterministic provider stub used in tests."""

    name: str = "fake-llm"

    async def generate(self, prompt_text: str) -> str:
        # RU: Детерминированный ответ, без сети/SDK.
        # EN: Deterministic response, no network/SDK.
        return "ok"
