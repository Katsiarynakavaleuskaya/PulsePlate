# llm.py
# RU: Безопасный селектор LLM-провайдера для /insight.
# EN: Safe LLM provider selector for the /insight endpoint.

from __future__ import annotations

import importlib
import os
from typing import Any, Optional, Type, cast

from core.time_utils import isoformat_utc
from providers import ProviderBase


class GrokLiteProvider:  # lightweight fallback that never uses network
    name = "grok"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def generate(self, text: str) -> str:
        return f"[grok-lite] {text}"


def _load_provider(module_name: str, attr: str) -> Optional[Type[ProviderBase]]:
    """Dynamically load provider class, returning None if unavailable."""

    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return None
    try:
        candidate = getattr(module, attr)
    except AttributeError:
        return None

    if isinstance(candidate, type):
        return cast(Type[ProviderBase], candidate)
    return None


GrokProvider = _load_provider("providers.grok", "GrokProvider")
OllamaProvider = _load_provider("providers.ollama", "OllamaProvider")
PicoProvider = _load_provider("providers.pico", "PicoProvider")


class StubProvider(ProviderBase):
    name = "stub"

    async def generate(self, text: str) -> str:
        # RU: простая заглушка, чтобы не было сетевых вызовов
        # EN: simple stub to avoid any network calls
        dt = isoformat_utc()
        return f"[stub @ {dt}] Insight: {text}"


def get_provider() -> Optional[ProviderBase]:
    """Returns provider based on LLM_PROVIDER environment variable.

    If variable is empty/unknown - returns None
    (not Ollama by default)."""
    val = (os.getenv("LLM_PROVIDER") or "").strip().lower()

    if val in {"", "none", "no", "off", "false"}:
        return None

    if val == "stub":
        return StubProvider()

    if val == "grok":
        if GrokProvider is not None:
            provider_cls = cast(Any, GrokProvider)
            # пример: можно пробросить ключ и модель через env
            api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY") or ""
            model = os.getenv("GROK_MODEL", "grok-4-latest")
            endpoint = os.getenv("GROK_ENDPOINT", "https://api.x.ai/v1")
            # If no API key is provided, prefer lightweight fallback to avoid network use
            if not api_key.strip():
                return GrokLiteProvider()
            try:
                return cast(
                    ProviderBase, provider_cls(endpoint=endpoint, api_key=api_key, model=model)
                )
            except (TypeError, ValueError):
                # Fallback to positional args if keyword args fail
                try:
                    return cast(ProviderBase, provider_cls(endpoint, model, api_key))
                except (TypeError, ValueError, RuntimeError):
                    # If both fail, return lite provider
                    return GrokLiteProvider()
        # Fallback when real provider unavailable
        return GrokLiteProvider()

    if val == "pico" and PicoProvider is not None:
        pico_cls = cast(Any, PicoProvider)
        # Only endpoint is required, api_key is optional
        api_key = (os.getenv("PICO_API_KEY") or "").strip() or None
        endpoint = (
            (os.getenv("PICO_ENDPOINT") or os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434"))
            or ""
        ).strip()
        # Optional with sensible default aligned with provider
        model = (os.getenv("PICO_MODEL") or "").strip() or "llama3.1:8b"

        if not endpoint:
            # Missing required configuration → provider not available
            return None

        try:
            return cast(ProviderBase, pico_cls(endpoint=endpoint, model=model, api_key=api_key))
        except (TypeError, ValueError):
            try:
                return cast(ProviderBase, pico_cls(endpoint, model, api_key))
            except (TypeError, ValueError, RuntimeError):
                return None

    if val == "ollama" and OllamaProvider is not None:
        ollama_cls = cast(Any, OllamaProvider)
        endpoint = (os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434") or "").strip()
        model = (os.getenv("OLLAMA_MODEL", "llama3.1:8b") or "").strip()
        # малый таймаут, чтобы даже при misconfig не висеть
        raw_timeout = os.getenv("OLLAMA_TIMEOUT", "5")
        try:
            timeout_s = float(raw_timeout)
        except (TypeError, ValueError):
            timeout_s = 5.0
        try:
            return cast(
                ProviderBase, ollama_cls(endpoint=endpoint, model=model, timeout_s=timeout_s)
            )
        except (TypeError, ValueError):
            # Fallback to positional args if keyword args fail
            try:
                return cast(ProviderBase, ollama_cls(endpoint, model, timeout_s))
            except (TypeError, ValueError, RuntimeError):
                # If both fail, return None
                return None

    # неизвестное значение — считаем, что провайдера нет
    return None
