# llm.py
# RU: Безопасный селектор LLM-провайдера для /insight.
# EN: Safe LLM provider selector for the /insight endpoint.

from __future__ import annotations

import importlib
import os
from typing import Any, Optional, Type, cast

from core.time_utils import isoformat_utc
from providers import ProviderBase

try:
    from providers.stub import StubProvider as ExternalStubProvider  # type: ignore
except (ModuleNotFoundError, ImportError):
    ExternalStubProvider = None  # type: ignore


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


if ExternalStubProvider is not None:
    StubProvider = ExternalStubProvider  # type: ignore[assignment]
else:

    class StubProvider(ProviderBase):
        name = "stub"

        async def generate(self, text: str) -> str:
            # RU: простая заглушка, чтобы не было сетевых вызовов
            # EN: simple stub to avoid any network calls
            dt = isoformat_utc()
            return f"[stub @ {dt}] Insight: {text}"


def _init_stub_provider() -> Optional[ProviderBase]:
    """Initialize StubProvider."""
    return StubProvider()


def _init_grok_provider() -> ProviderBase:
    """Initialize GrokProvider with fallback to GrokLiteProvider."""

    def _instantiate_with_fallback(
        provider_ctor: Any, *, endpoint: str, model: str, api_key: str
    ) -> Optional[ProviderBase]:
        """Try keyword args first, then positional. Return None on failure."""
        try:
            return cast(
                ProviderBase, provider_ctor(endpoint=endpoint, api_key=api_key, model=model)
            )
        except (TypeError, ValueError):
            try:
                return cast(ProviderBase, provider_ctor(endpoint, model, api_key))
            except (TypeError, ValueError, RuntimeError):
                return None

    if GrokProvider is None:
        return GrokLiteProvider()

    provider_cls = cast(Any, GrokProvider)
    api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY") or ""
    model = os.getenv("GROK_MODEL", "grok-4-latest")
    endpoint = os.getenv("GROK_ENDPOINT", "https://api.x.ai/v1")

    # If no API key is provided, prefer lightweight fallback to avoid network use
    if not api_key.strip():
        return GrokLiteProvider()

    provider = _instantiate_with_fallback(
        provider_cls, endpoint=endpoint, model=model, api_key=api_key
    )
    return provider if provider is not None else GrokLiteProvider()


def _init_pico_provider() -> Optional[ProviderBase]:
    """Initialize PicoProvider."""
    if PicoProvider is None:
        return None

    pico_cls = cast(Any, PicoProvider)
    # Only endpoint is required, api_key is optional
    api_key = (os.getenv("PICO_API_KEY") or "").strip() or None
    endpoint = (
        (os.getenv("PICO_ENDPOINT") or os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")) or ""
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


def _parse_timeout(raw_value: str, default: float = 5.0) -> float:
    """Parse timeout seconds from string, return default on error."""
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return default


def _init_ollama_provider() -> Optional[ProviderBase]:
    """Initialize OllamaProvider."""
    if OllamaProvider is None:
        return None

    ollama_cls = cast(Any, OllamaProvider)
    endpoint = (os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434") or "").strip()
    model = (os.getenv("OLLAMA_MODEL", "llama3.1:8b") or "").strip()
    # малый таймаут, чтобы даже при misconfig не висеть
    timeout_s = _parse_timeout(os.getenv("OLLAMA_TIMEOUT", "5"))

    try:
        return cast(ProviderBase, ollama_cls(endpoint=endpoint, model=model, timeout_s=timeout_s))
    except (TypeError, ValueError):
        # Fallback to positional args if keyword args fail
        try:
            return cast(ProviderBase, ollama_cls(endpoint, model, timeout_s))
        except (TypeError, ValueError, RuntimeError):
            # If both fail, return None
            return None


def get_provider() -> Optional[ProviderBase]:
    """Returns provider based on LLM_PROVIDER environment variable.

    Accepted values:
    - Disabled: "", "none", "no", "off", "false" → returns stub provider
    - Valid providers: "stub", "grok", "pico", "ollama" → returns corresponding provider

    When disabled or unknown values are provided, returns a stub provider (never None).
    The stub provider is a no-op placeholder that avoids network calls and provides
    deterministic responses for testing and fallback scenarios."""
    val = (os.getenv("LLM_PROVIDER") or "").strip().lower()

    if val in {"", "none", "no", "off", "false"}:
        return _init_stub_provider()

    if val == "stub":
        if ExternalStubProvider is not None:
            return ExternalStubProvider()  # type: ignore[call-arg]
        return _init_stub_provider()
    elif val == "grok":
        return _init_grok_provider()
    elif val == "pico":
        return _init_pico_provider()
    elif val == "ollama":
        return _init_ollama_provider()

    # неизвестное значение — безопасно возвращаем заглушку
    return _init_stub_provider()
