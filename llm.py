# llm.py
# RU: Безопасный селектор LLM-провайдера для /insight.
# EN: Safe LLM provider selector for the /insight endpoint.

from __future__ import annotations

import os

from core.time_utils import isoformat_utc
from providers import ProviderBase


class GrokLiteProvider:  # lightweight fallback that never uses network
    name = "grok"

    def __init__(self, *args, **kwargs):
        pass

    async def generate(self, text: str) -> str:
        return f"[grok-lite] {text}"


# Опциональные импорты — модуль должен грузиться даже без внешних либ
try:
    from providers.grok import GrokProvider  # xAI
except Exception:
    GrokProvider = None  # type: ignore


try:
    from providers.ollama import OllamaProvider  # локальные/совместимые
except Exception:
    OllamaProvider = None  # type: ignore

try:
    from providers.pico import PicoProvider  # если у тебя есть этот файл
except Exception:
    PicoProvider = None  # type: ignore

try:
    from providers.llmflow import LLMFlowProvider  # LLMFlow service adapter
except Exception:
    LLMFlowProvider = None  # type: ignore


class StubProvider(ProviderBase):
    name = "stub"

    async def generate(self, text: str) -> str:
        # RU: простая заглушка, чтобы не было сетевых вызовов
        # EN: simple stub to avoid any network calls
        dt = isoformat_utc()
        return f"[stub @ {dt}] Insight: {text}"


def get_provider() -> ProviderBase | GrokLiteProvider | None:
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
            except Exception:
                # Fallback to positional args if keyword args fail
                try:
                    return GrokProvider(endpoint, model, api_key)
                except Exception:
                    # If both fail, return lite provider
                    return GrokLiteProvider()
        # Fallback when real provider unavailable
        return GrokLiteProvider()

    if val == "ollama" and OllamaProvider is not None:
        endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        # малый таймаут, чтобы даже при misconfig не висеть
        timeout_s = float(os.getenv("OLLAMA_TIMEOUT", "5"))
        try:
            return OllamaProvider(endpoint=endpoint, model=model, timeout_s=timeout_s)
        except Exception:
            # Fallback to positional args if keyword args fail
            try:
                return OllamaProvider(endpoint, model, timeout_s)
            except Exception:
                # If both fail, return None
                return None

    if val in {"llmflow", "flow"}:
        if LLMFlowProvider is None:
            return None
        endpoint = os.getenv("LLMFLOW_ENDPOINT", "http://127.0.0.1:7070")
        flow_id = (os.getenv("LLMFLOW_FLOW_ID") or "").strip()
        if not flow_id:
            return None
        api_key = (os.getenv("LLMFLOW_API_KEY") or "").strip() or ""
        input_key = (os.getenv("LLMFLOW_INPUT_KEY") or "prompt").strip() or "prompt"
        output_key_env = os.getenv("LLMFLOW_OUTPUT_KEY")
        output_key = output_key_env.strip() if output_key_env and output_key_env.strip() else None
        try:
            timeout = float(os.getenv("LLMFLOW_TIMEOUT", "15"))
        except ValueError:
            timeout = 15.0

        try:
            return LLMFlowProvider(
                endpoint=endpoint,
                flow_id=flow_id,
                api_key=api_key,
                timeout=timeout,
                input_key=input_key,
                output_key=output_key,
            )
        except Exception:
            return None

    # неизвестное значение — считаем, что провайдера нет
    return None
