from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from providers.embeddings import EmbeddingProvider


class ProviderBase(Protocol):
    """Базовый интерфейс для всех LLM-провайдеров."""

    name: str

    async def generate(self, text: str) -> str:
        raise NotImplementedError("Provider must implement .generate(text)")


__all__ = ["ProviderBase", "EmbeddingProvider"]
