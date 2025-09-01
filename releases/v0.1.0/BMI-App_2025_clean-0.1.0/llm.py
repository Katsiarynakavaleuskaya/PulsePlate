from __future__ import annotations

import os
from datetime import datetime

from providers import ProviderBase

# Опциональные импорты — чтоб модуль грузился даже без установленных либ
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


class StubProvider(ProviderBase):
    name = "stub"
    def generate(self, text: str) -> str:
        return f"[stub @ {datetime.utcnow().isoformat()}] Insight: {text}"


def _get_stub() -> ProviderBase:
    return StubProvider()


def _get_grok() -> ProviderBase | None:
    if os.getenv("LLM_PROVIDER", "").strip().lower() not in {"grok", ""} and \
       os.getenv("LLM_PROVIDER", "").strip().lower() != "auto":
        # Если явно выбран другой провайдер, не инициализируем grok
        pass
    api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
    model = os.getenv("GROK_MODEL", "grok-4-latest")
    endpoint = os.getenv("GROK_ENDPOINT", "https://api.x.ai/v1")
    if GrokProvider and api_key:
        return GrokProvider(endpoint=endpoint, model=model, api_key=api_key)
    return None


def _get_ollama() -> ProviderBase | None:
    if os.getenv("LLM_PROVIDER", "").strip().lower() not in {"ollama", ""} and \
       os.getenv("LLM_PROVIDER", "").strip().lower() != "auto":
        pass
    endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    timeout_s = float(os.getenv("OLLAMA_TIMEOUT", "120"))
    if OllamaProvider:
        return OllamaProvider(endpoint=endpoint, model=model, timeout_s=timeout_s)
    return None


def _get_pico() -> ProviderBase | None:
    # Pico — Ollama-совместимый; если есть свой провайдер — используем, иначе None
    if os.getenv("LLM_PROVIDER", "").strip().lower() not in {"pico", ""} and \
       os.getenv("LLM_PROVIDER", "").strip().lower() != "auto":
        pass
    endpoint = os.getenv("PICO_ENDPOINT", "http://localhost:11434")
    model = os.getenv("PICO_MODEL", "llama3.1:8b")
    timeout_s = float(os.getenv("PICO_TIMEOUT", "120"))
    if PicoProvider:
        return PicoProvider(endpoint=endpoint, model=model, timeout_s=timeout_s)
    return None


def get_provider() -> ProviderBase:
    """
    Логика выбора:
      - если LLM_PROVIDER задан явно (grok|ollama|pico|stub) — берём его;
      - иначе пытаемся цепочкой grok → ollama → pico;
      - если ничего не взлетело — stub.
    """
    target = os.getenv("LLM_PROVIDER", "").strip().lower()

    order = []
    if target in {"grok", "ollama", "pico", "stub"}:
        order = [target]
    else:
        # auto / пусто
        order = ["grok", "ollama", "pico", "stub"]

    for who in order:
        try:
            if who == "grok":
                p = _get_grok()
                if p:
                    return p
            elif who == "ollama":
                p = _get_ollama()
                if p:
                    return p
            elif who == "pico":
                p = _get_pico()
                if p:
                    return p
            elif who == "stub":
                return _get_stub()
        except Exception as e:
            print(f"[LLM] provider error in {who}: {e}")

    # На всякий — чтобы точно был кто-то
    return _get_stub()
