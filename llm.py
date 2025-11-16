# llm.py
# RU: Безопасный селектор LLM-провайдера для /insight.
# EN: Safe LLM provider selector for the /insight endpoint.

from __future__ import annotations

import logging
import os
from typing import Optional

from core.time_utils import isoformat_utc
from providers import ProviderBase

logger = logging.getLogger(__name__)


class GrokLiteProvider(ProviderBase):  # lightweight fallback that never uses network
    name = "grok"

    def __init__(
        self,
        endpoint: str = "",
        model: str = "",
        api_key: str = "",
        timeout: Optional[float] = None,
    ) -> None:
        # RU: Параметры игнорируются, так как это легковесный fallback без сети
        # EN: Parameters are ignored as this is a lightweight fallback without network
        pass

    async def generate(self, text: str) -> str:
        return f"[grok-lite] {text}"


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


# Опциональные импорты — модуль должен грузиться даже без внешних либ
try:
    from providers.grok import GrokProvider as _GrokProvider  # xAI

    GrokProvider: type[_GrokProvider] | None = _GrokProvider
except Exception:
    GrokProvider = None


try:
    from providers.ollama import OllamaProvider as _OllamaProvider  # локальные/совместимые

    OllamaProvider: type[_OllamaProvider] | None = _OllamaProvider
except Exception:
    OllamaProvider = None

try:
    from providers.pico import PicoProvider as _PicoProvider  # если у тебя есть этот файл

    PicoProvider: type[_PicoProvider] | None = _PicoProvider
except Exception:
    PicoProvider = None


class StubProvider(ProviderBase):
    name = "stub"

    async def generate(self, text: str) -> str:
        # RU: простая заглушка, чтобы не было сетевых вызовов
        # EN: simple stub to avoid any network calls
        dt = isoformat_utc()
        return f"[stub @ {dt}] Insight: {text}"


def get_provider() -> ProviderBase | None:
    """Возвращает провайдер по переменной окружения LLM_PROVIDER.

    Если переменная пустая/неизвестная — возвращает None
    (а не Ollama по умолчанию)."""
    val = (os.getenv("LLM_PROVIDER") or "").strip().lower()

    if val in {"", "none", "no"}:
        return None

    if val == "stub":
        return StubProvider()

    if val == "grok":
        if GrokProvider is not None:
            # пример: можно пробросить ключ и модель через env
            api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY") or ""
            model = os.getenv("GROK_MODEL", "grok-4-latest")
            endpoint = os.getenv("GROK_ENDPOINT", "https://api.x.ai/v1")
            # If no API key is provided, prefer lightweight fallback to avoid network use
            if not api_key.strip():
                return GrokLiteProvider()
            try:
                return GrokProvider(endpoint=endpoint, api_key=api_key, model=model)
            except Exception as e:
                logger.debug(
                    "Grok provider init failed with keyword args, falling back to positional args",
                    exc_info=e,
                )
                # Fallback to positional args if keyword args fail
                try:
                    return GrokProvider(endpoint, model, api_key)
                except Exception:
                    logger.exception(
                        "Grok provider init failed with positional args, falling back to lite provider"
                    )
                    # If both fail, return lite provider
                    return GrokLiteProvider()
        else:
            # Fallback when real provider unavailable
            return GrokLiteProvider()

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
            except Exception as e:
                logger.debug(
                    "Ollama provider init failed with keyword args, falling back to positional args",
                    exc_info=e,
                )
                # Fallback to positional args if keyword args fail (консистентно с GrokProvider)
                try:
                    return OllamaProvider(endpoint, model)
                except Exception:
                    logger.exception(
                        "Ollama provider init failed with positional args, falling back to lite provider"
                    )
                    # If both fail, return lite provider
                    return OllamaLiteProvider()
        else:
            # Fallback when real provider unavailable
            return OllamaLiteProvider()

    # неизвестное значение — считаем, что провайдера нет
    return None
