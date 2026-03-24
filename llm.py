# llm.py
# RU: Безопасный селектор LLM-провайдера для /insight.
# EN: Safe LLM provider selector for the /insight endpoint.

from __future__ import annotations

import importlib
import logging
import os
from typing import Optional, cast

from core.time_utils import isoformat_utc
from providers import ProviderBase

logger = logging.getLogger(__name__)
_PLACEHOLDER_API_KEYS = {
    "__replace_me__",
    "paste_your_real_key_here",
    "changeme",
    "your_api_key_here",
}


def _load_optional_provider(module_name: str, class_name: str) -> type[ProviderBase] | None:
    """RU: Безопасно импортирует optional provider class.
    EN: Safely imports an optional provider class.
    """
    try:
        module = importlib.import_module(module_name)
        return cast(type[ProviderBase] | None, getattr(module, class_name, None))
    except Exception:
        return None


class OllamaLiteProvider(ProviderBase):
    """Lightweight fallback implementation that never uses the network.

    Returns local/placeholder responses instead of making actual API calls.
    """

    name = "ollama"

    def __init__(
        self,
        endpoint: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout_s: Optional[float] = None,
    ) -> None:
        # RU: Параметры игнорируются, так как это легковесный fallback без сети
        # EN: Parameters are ignored as this is a lightweight fallback without network
        pass

    async def generate(self, text: str) -> str:
        return f"[ollama-lite] {text}"


class PerplexityLiteProvider(ProviderBase):
    """Lightweight fallback implementation that never uses the network."""

    name = "perplexity"

    async def generate(self, text: str) -> str:
        return f"[perplexity-lite] {text}"


# Опциональные импорты — модуль должен грузиться даже без внешних либ
OllamaProvider = _load_optional_provider("providers.ollama", "OllamaProvider")
PerplexityProvider = _load_optional_provider("providers.perplexity", "PerplexityProvider")
PicoProvider = _load_optional_provider("providers.pico", "PicoProvider")


class StubProvider(ProviderBase):
    name = "stub"

    async def generate(self, text: str) -> str:
        # RU: простая заглушка, чтобы не было сетевых вызовов
        # EN: simple stub to avoid any network calls
        dt = isoformat_utc()
        return f"[stub @ {dt}] Insight: {text}"


def get_provider():
    """Возвращает провайдер по переменной окружения LLM_PROVIDER.

    Если переменная пустая/неизвестная — возвращает None
    (а не Ollama по умолчанию)."""
    val = (os.getenv("LLM_PROVIDER") or "").strip().lower()

    if val in {"", "none", "no"}:
        return None

    if val == "stub":
        return StubProvider()

    if val == "ollama":
        if OllamaProvider is not None:
            endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
            model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
            # малый таймаут, чтобы даже при misconfig не висеть
            # EN: Parse timeout with error handling for invalid env var values
            # RU: Парсим таймаут с обработкой ошибок для невалидных значений env var
            raw_timeout = os.getenv("OLLAMA_TIMEOUT", "1.5")
            try:
                timeout_s = float(raw_timeout)
            except ValueError as e:
                timeout_s = 1.5
                logger.warning("Invalid OLLAMA_TIMEOUT '%s', defaulting to 1.5: %s", raw_timeout, e)
            try:
                return OllamaProvider(endpoint=endpoint, model=model, timeout_s=timeout_s)
            except Exception:
                # Fallback to positional args if keyword args fail (консистентно с GrokProvider)
                try:
                    return OllamaProvider(endpoint, model)
                except Exception:
                    # If both fail, return lite provider
                    return OllamaLiteProvider()
        else:
            # Fallback when real provider unavailable
            return OllamaLiteProvider()

    if val == "perplexity":
        if PerplexityProvider is not None:
            api_key = os.getenv("PERPLEXITY_API_KEY", "")
            model = os.getenv("PERPLEXITY_MODEL", "sonar")
            endpoint = os.getenv("PERPLEXITY_ENDPOINT", "https://api.perplexity.ai")

            normalized_api_key = api_key.strip()
            if not normalized_api_key or normalized_api_key.lower() in _PLACEHOLDER_API_KEYS:
                return PerplexityLiteProvider()

            try:
                # Perplexity uses OpenAI-compatible init signature; we keep a single
                # constructor path (no positional retry) to avoid silently masking
                # schema/auth mistakes and to fail-closed into lite fallback.
                return PerplexityProvider(
                    endpoint=endpoint, api_key=normalized_api_key, model=model
                )
            except Exception:
                return PerplexityLiteProvider()
        else:
            return PerplexityLiteProvider()

    # неизвестное значение — считаем, что провайдера нет
    return None
