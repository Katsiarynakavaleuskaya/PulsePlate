from typing import Optional

from openai import OpenAI


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
        # создаём клиента (OpenAI совместимый эндпоинт у x.ai)
        self.client = OpenAI(base_url=self.endpoint, api_key=self.api_key)
        self.timeout = timeout

    def generate(self, text: str) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": text}],
                timeout=self.timeout,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            # Пробрасываем понятную ошибку наверх — FastAPI вернёт 500 с этим текстом
            raise RuntimeError(f"Grok error: {type(e).__name__}: {e}")
