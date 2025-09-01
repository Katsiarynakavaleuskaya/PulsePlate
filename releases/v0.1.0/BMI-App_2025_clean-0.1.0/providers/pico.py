from __future__ import annotations

import os

import httpx

from . import ProviderBase


class PicoProvider(ProviderBase):
    name = "pico"

    def __init__(self, endpoint: str | None = None, model: str | None = None, api_key: str | None = None):
        # Pico заявляет совместимость с Ollama REST; по умолчанию тот же порт
        self.endpoint = endpoint or os.getenv("PICO_ENDPOINT", os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434"))
        self.model = model or os.getenv("PICO_MODEL", os.getenv("OLLAMA_MODEL", "llama3.1:8b"))
        self.client = httpx.Client(base_url=self.endpoint, timeout=30.0)

    def generate(self, text: str) -> str:
        try:
            r = self.client.post(
                "/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": text}],
                    "stream": False,
                },
            )
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                if "message" in data and isinstance(data["message"], dict):
                    return (data["message"].get("content") or "").strip()
                if "choices" in data and data["choices"]:
                    return (data["choices"][0]["message"]["content"] or "").strip()
                if "response" in data:
                    return (data["response"] or "").strip()
            return str(data)
        except Exception as e:
            raise RuntimeError(f"Pico error: {type(e).__name__}: {e}")
