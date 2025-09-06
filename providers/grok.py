from typing import Optional

from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class GrokProvider:
    """
    Минималистичный провайдер к x.ai (Grok) через совместимый OpenAI SDK.
    Совместим с вызовом из llm.py:
        GrokProvider(endpoint=..., model=..., api_key=...)
    """

    name = "grok"

    def __init__(self, endpoint: str, model: str, api_key: str, timeout: Optional[float] = 30.0):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key = api_key
        # создаём асинхронного клиента (OpenAI совместимый эндпоинт у x.ai)
        self.client = AsyncOpenAI(base_url=self.endpoint, api_key=self.api_key)
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def generate(self, text: str) -> str:
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": text}],
                timeout=self.timeout,
            )
            content = resp.choices[0].message.content
            return content.strip() if content else ""
        except Exception as e:
            # Пробрасываем понятную ошибку наверх
            raise RuntimeError(f"Grok error: {type(e).__name__}: {e}")
