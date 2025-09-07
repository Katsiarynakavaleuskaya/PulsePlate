from __future__ import annotations

import os

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from providers import ProviderBase


class OllamaProvider(ProviderBase):
    """
    RU: Провайдер для локального Ollama (и совместимых).
    Делает короткие запросы и переводит сетевые ошибки в RuntimeError,
    чтобы /insight мог быстро вернуть 503.
    EN: Short timeouts, convert network errors to RuntimeError so the
    /insight endpoint can respond with 503 fast.
    """

    name = "ollama"

    def __init__(
        self,
        endpoint: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout_s: float | None = None,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        # Короткий таймаут; можно переопределить через OLLAMA_TIMEOUT
        if timeout_s is None:
            try:
                timeout_s = float(os.getenv("OLLAMA_TIMEOUT", "1.5"))
            except ValueError:
                timeout_s = 1.5
        self.timeout_s = float(timeout_s)

    async def _chat(self, c: httpx.AsyncClient, text: str) -> str | None:
        r = await c.post(
            f"{self.endpoint}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": text}],
                "stream": False,
            },
            headers={"Content-Type": "application/json"},
            timeout=self.timeout_s,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        # разные совместимые реализации: пробуем несколько ключей
        msg = None
        if isinstance(data, dict):
            # ollama chat: {'message': {'role': 'assistant', 'content': '...'}}
            msg = (
                data.get("message", {}).get("content")
                or data.get("response")
                or data.get("content")
            )
        return msg or None

    async def _generate(self, c: httpx.AsyncClient, text: str) -> str | None:
        r = await c.post(
            f"{self.endpoint}/api/generate",
            json={"model": self.model, "prompt": text, "stream": False},
            headers={"Content-Type": "application/json"},
            timeout=self.timeout_s,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        # generate обычно возвращает {"response": "..."}
        return data.get("response") or data.get("content") or None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RuntimeError),
        reraise=True,
    )
    async def generate(self, text: str) -> str:
        try:
            async with httpx.AsyncClient() as c:
                # 1) пробуем chat
                msg = await self._chat(c, text)
                if msg:
                    return msg
                # 2) fallback на generate
                msg = await self._generate(c, text)
                if msg:
                    return msg
        except (httpx.RequestError, httpx.HTTPStatusError, httpx.TimeoutException) as e:
            # конвертируем сетевую ошибку в контролируемую
            raise RuntimeError("ollama_unavailable") from e

        # если сервер ответил нестандартно или пусто — считаем, что недоступен
        raise RuntimeError("ollama_unavailable")
