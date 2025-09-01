# llm.py
# RU: Безопасный селектор LLM-провайдера для /insight.
# EN: Safe LLM provider selector for the /insight endpoint.

from __future__ import annotations

import os
from datetime import datetime, timezone

from providers import ProviderBase

# Опциональные импорты — модуль должен грузиться даже без внешних либ
try:
    from providers.grok import GrokProvider  # xAI
except Exception:
    GrokProvider = None  # type: ignore
    # Lightweight fallback so tests can run without external deps
    class GrokLiteProvider:  # type: ignore
        name = "grok"

        def __init__(self, *args, **kwargs):
            pass

        async def generate(self, text: str) -> str:
            return f"[grok-lite] {text}"

try:
    from providers.ollama import OllamaProvider  # локальные/совместимые
except Exception:
    OllamaProvider = None  # type: ignore

try:
    from providers.pico import PicoProvider  # если у тебя есть этот файл
except Exception:
    PicoProvider = None  # type: ignore


class StubProvider(ProviderBase):
    name = "stub"

    async def generate(self, text: str) -> str:
        # RU: простая заглушка, чтобы не было сетевых вызовов
        # EN: simple stub to avoid any network calls
        dt = datetime.now(timezone.utc).isoformat()
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

    if val == "grok":
        if GrokProvider:
            # пример: можно пробросить ключ и модель через env
            api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY") or ""
            model = os.getenv("GROK_MODEL", "grok-4-latest")
            endpoint = os.getenv("GROK_ENDPOINT", "https://api.x.ai/v1")
            return GrokProvider(endpoint=endpoint, api_key=api_key, model=model)
        # Fallback when real provider unavailable
        return GrokLiteProvider()

    if val == "ollama" and OllamaProvider:
        endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        # малый таймаут, чтобы даже при misconfig не висеть
        timeout_s = float(os.getenv("OLLAMA_TIMEOUT", "5"))
        return OllamaProvider(
            endpoint=endpoint,
            model=model,
            timeout_s=timeout_s
        )

    # неизвестное значение — считаем, что провайдера нет
    return None

