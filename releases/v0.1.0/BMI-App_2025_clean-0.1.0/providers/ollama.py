from __future__ import annotations

import httpx

from providers import ProviderBase


class OllamaProvider(ProviderBase):
    """
    Провайдер для локального Ollama (и совместимых серверов).
    Пытается сначала /api/chat, затем /api/generate.
    """
    name = "ollama"

    def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llama3.1:8b", timeout_s: float = 120.0):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout_s = float(timeout_s)

    def generate(self, text: str) -> str:
        try:
            # 1) /api/chat (если доступно)
            with httpx.Client(timeout=self.timeout_s) as c:
                r = c.post(
                    f"{self.endpoint}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": text}
                        ],
                        "stream": False
                    },
                    headers={"Content-Type": "application/json"},
                )
                if r.status_code == 200:
                    data = r.json()
                    # Разные ответы у Ollama-совместимых: попробуем несколько ключей
                    # Оригинальный Ollama stream=False обычно не поддерживает /api/chat стабильно,
                    # поэтому держим fallback ниже.
                    msg = None
                    if isinstance(data, dict):
                        # open-webui совместимки: {"message":{"content":"..."}}
                        msg = (data.get("message") or {}).get("content")
                        if not msg:
                            # некоторые возвращают список choices/msgs
                            msg = data.get("response") or data.get("content")
                    if msg:
                        return str(msg).strip()
                    # Если 200, но пусто — пойдём на /api/generate
                else:
                    r.raise_for_status()
        except Exception:
            # переходим ко 2-му пути ниже
            pass

        # 2) /api/generate (каноничный путь для Ollama)
        try:
            with httpx.Client(timeout=self.timeout_s) as c:
                r = c.post(
                    f"{self.endpoint}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": text,
                        "stream": False,
                    },
                    headers={"Content-Type": "application/json"},
                )
                r.raise_for_status()
                data = r.json()
                resp = data.get("response") or ""
                if str(resp).strip():
                    return str(resp).strip()
                raise RuntimeError("Empty response from /api/generate")
        except Exception as e:
            raise RuntimeError(f"Ollama error: {type(e).__name__}: {e}")
