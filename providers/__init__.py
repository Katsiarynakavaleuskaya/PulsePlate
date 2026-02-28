from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    # EmbeddingProvider is re-exported for type annotations only.
    # Use `from providers.embeddings import EmbeddingProvider` at runtime.
    from providers.embeddings import EmbeddingProvider as EmbeddingProvider  # noqa: F401


class ProviderBase(Protocol):
    """Базовый интерфейс для всех LLM-провайдеров."""

    name: str

    async def generate(self, text: str) -> str:
        raise NotImplementedError("Provider must implement .generate(text)")


# Note: EmbeddingProvider is TYPE_CHECKING-only export.
# Runtime star-imports should not rely on it.
__all__ = ["ProviderBase"]
