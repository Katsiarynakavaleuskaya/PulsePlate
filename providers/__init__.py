from __future__ import annotations


class ProviderBase:
    """Базовый интерфейс для всех LLM-провайдеров."""

    name: str = "base"

    def generate(self, text: str) -> str:
        raise NotImplementedError("Provider must implement .generate(text)")


__all__ = ["ProviderBase"]
