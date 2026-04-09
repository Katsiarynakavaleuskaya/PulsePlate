# llm.py
# RU: Безопасный селектор LLM-провайдера для /insight.
# EN: Safe LLM provider selector for the /insight endpoint.

from __future__ import annotations

import importlib
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any, Optional, cast

from core.time_utils import isoformat_utc
from providers import ProviderBase

logger = logging.getLogger(__name__)
_PLACEHOLDER_API_KEYS = {
    "__replace_me__",
    "paste_your_real_key_here",
    "changeme",
    "your_api_key_here",
}
_DEFAULT_OLLAMA_TIMEOUT = 1.5
_MIN_OLLAMA_TIMEOUT = 0.1


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


def _normalized_llm_provider() -> str:
    """Return normalized LLM provider value from env."""

    return (os.getenv("LLM_PROVIDER") or "").strip().lower()


def _parse_ollama_timeout() -> float:
    """Parse Ollama timeout from env with safe fallback."""

    raw_timeout = os.getenv("OLLAMA_TIMEOUT", str(_DEFAULT_OLLAMA_TIMEOUT))
    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        logger.warning(
            "Invalid OLLAMA_TIMEOUT '%s', defaulting to %.1f: %s",
            raw_timeout,
            _DEFAULT_OLLAMA_TIMEOUT,
            exc,
        )
        return _DEFAULT_OLLAMA_TIMEOUT

    if timeout < _MIN_OLLAMA_TIMEOUT:
        logger.warning(
            "OLLAMA_TIMEOUT '%s' below minimum %.1f; defaulting to %.1f",
            raw_timeout,
            _MIN_OLLAMA_TIMEOUT,
            _DEFAULT_OLLAMA_TIMEOUT,
        )
        return _DEFAULT_OLLAMA_TIMEOUT

    return timeout


def _build_stub_provider() -> ProviderBase:
    """Return terminal local stub provider."""

    return StubProvider()


def _build_ollama_family_provider() -> ProviderBase:
    """Return Ollama-family provider with current real-or-lite semantics."""

    if OllamaProvider is not None:
        ollama_provider_cls: Any = OllamaProvider
        endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        timeout_s = _parse_ollama_timeout()
        try:
            return cast(
                ProviderBase,
                ollama_provider_cls(
                    endpoint=endpoint,
                    model=model,
                    timeout_s=timeout_s,
                ),
            )
        except Exception:
            # RU: Сохраняем старый positional retry для совместимости с legacy ctor seams.
            # EN: Preserve legacy positional retry for constructor compatibility seams.
            try:
                return cast(ProviderBase, ollama_provider_cls(endpoint, model))
            except Exception:
                return OllamaLiteProvider()

    return OllamaLiteProvider()


def _build_perplexity_family_provider() -> ProviderBase:
    """Return Perplexity-family provider with current real-or-lite semantics."""

    if PerplexityProvider is not None:
        perplexity_provider_cls: Any = PerplexityProvider
        api_key = os.getenv("PERPLEXITY_API_KEY", "")
        model = os.getenv("PERPLEXITY_MODEL", "sonar")
        endpoint = os.getenv("PERPLEXITY_ENDPOINT", "https://api.perplexity.ai")

        normalized_api_key = api_key.strip()
        if not normalized_api_key or normalized_api_key.lower() in _PLACEHOLDER_API_KEYS:
            return PerplexityLiteProvider()

        try:
            return cast(
                ProviderBase,
                perplexity_provider_cls(
                    endpoint=endpoint,
                    api_key=normalized_api_key,
                    model=model,
                ),
            )
        except Exception:
            return PerplexityLiteProvider()

    return PerplexityLiteProvider()


def _provider_chain_names(provider_value: str) -> list[str]:
    """Return deterministic fallback order for readiness visibility."""

    if provider_value == "perplexity":
        return ["perplexity", "ollama", "stub"]
    if provider_value == "ollama":
        return ["ollama", "stub"]
    if provider_value == "stub":
        return ["stub"]
    return []


def _decorate_provider_with_fallback(
    *,
    provider: ProviderBase,
    primary_name: str,
    fallback_builders: list[tuple[str, Callable[[], ProviderBase]]],
) -> ProviderBase:
    """Attach deterministic fallback to the provider while preserving its public identity."""

    original_generate = provider.generate
    fallback_cache: dict[str, ProviderBase] = {}

    setattr(provider, "active_provider_name", getattr(provider, "name", primary_name))
    setattr(provider, "primary_provider_name", primary_name)
    setattr(
        provider,
        "fallback_order",
        [primary_name, *[provider_name for provider_name, _ in fallback_builders]],
    )

    async def _generate_with_fallback(text: str) -> str:
        last_error: Exception | None = None
        provider_attempts: list[tuple[str, Callable[[str], Awaitable[str]], ProviderBase]] = [
            (
                primary_name,
                original_generate,
                provider,
            )
        ]

        for provider_name, builder in fallback_builders:
            fallback_provider = fallback_cache.get(provider_name)
            if fallback_provider is None:
                try:
                    fallback_provider = builder()
                except Exception as exc:
                    logger.warning(
                        "Insight fallback builder '%s' failed; skipping provider",
                        provider_name,
                        exc_info=exc,
                    )
                    continue
                fallback_cache[provider_name] = fallback_provider
            provider_attempts.append(
                (
                    provider_name,
                    fallback_provider.generate,
                    fallback_provider,
                )
            )

        for provider_name, generate_fn, candidate_provider in provider_attempts:
            try:
                result = await generate_fn(text)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Insight provider '%s' failed, falling back to next provider",
                    provider_name,
                    exc_info=exc,
                )
                continue

            setattr(
                provider,
                "active_provider_name",
                str(getattr(candidate_provider, "name", provider_name)),
            )
            setattr(
                provider,
                "name",
                str(getattr(candidate_provider, "name", provider_name)),
            )
            return result

        if last_error is None:  # pragma: no cover
            raise RuntimeError("Insight fallback chain is empty")
        raise last_error

    setattr(provider, "generate", _generate_with_fallback)
    return provider


def get_insight_runtime_readiness() -> dict[str, object]:
    """Return safe readiness metadata for the insight runtime."""

    provider_value = _normalized_llm_provider()
    fallback_order = _provider_chain_names(provider_value)
    supported_primary = provider_value if fallback_order else None
    echo_mode_provider = "stub" if provider_value == "stub" else None

    return {
        "feature_enabled": (os.getenv("FEATURE_INSIGHT", "false").strip().lower())
        in {"1", "true", "on", "yes"},
        "primary_provider": supported_primary,
        "fallback_order": fallback_order,
        "echo_mode_provider": echo_mode_provider,
    }


def get_provider() -> ProviderBase | None:
    """Возвращает провайдер по переменной окружения LLM_PROVIDER.

    Если переменная пустая/неизвестная — возвращает None
    (а не implicit stub)."""
    val = _normalized_llm_provider()

    if val in {"", "none", "no"}:
        return None

    if val == "stub":
        return _build_stub_provider()

    if val == "ollama":
        return _build_ollama_family_provider()

    if val == "perplexity":
        return _build_perplexity_family_provider()

    # неизвестное значение — считаем, что провайдера нет
    return None


def get_insight_provider() -> ProviderBase | None:
    """Return insight-specific provider with deterministic runtime fallback chain."""

    val = _normalized_llm_provider()

    if val in {"", "none", "no"}:
        return None

    if val == "stub":
        return _build_stub_provider()

    if val == "ollama":
        return _decorate_provider_with_fallback(
            provider=_build_ollama_family_provider(),
            primary_name="ollama",
            fallback_builders=[
                ("stub", _build_stub_provider),
            ],
        )

    if val == "perplexity":
        return _decorate_provider_with_fallback(
            provider=_build_perplexity_family_provider(),
            primary_name="perplexity",
            fallback_builders=[
                ("ollama", _build_ollama_family_provider),
                ("stub", _build_stub_provider),
            ],
        )

    # неизвестное значение — считаем, что провайдера нет
    return None
