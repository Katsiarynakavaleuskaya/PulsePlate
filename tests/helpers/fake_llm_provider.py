"""Deterministic fake LLM provider for tests (no network).

RU: Детерминированный fake LLM provider для тестов (без сети).
EN: Deterministic fake LLM provider for tests (no network).

Interface notes:
- Intentionally keeps a minimal surface area, but accepts ``**kwargs`` to reduce
  breakage if the real provider API evolves.
"""

from __future__ import annotations


class FakeLLMProvider:
    """Deterministic provider stub used in tests."""

    name: str = "fake-llm"

    async def generate(self, prompt_text: str, **kwargs: object) -> str:  # noqa: ARG002
        # RU: Детерминированный ответ, без сети/SDK.
        # EN: Deterministic response, no network/SDK.
        return "ok"
