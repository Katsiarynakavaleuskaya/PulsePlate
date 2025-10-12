from typing import Optional

import httpx
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)


def is_transient_error(exception: BaseException) -> bool:
    """
    Определяет, является ли ошибка временной/транзиентной и стоит ли её повторить.

    Args:
        exception: Исключение для проверки

    Returns:
        True если ошибка транзиентная и стоит повторить запрос
    """
    # Network/connection errors - всегда транзиентные
    if isinstance(
        exception,
        (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
            httpx.RemoteProtocolError,
        ),
    ):
        return True

    # Проверяем HTTP статус коды для OpenAI SDK ошибок
    if hasattr(exception, "response"):
        response = getattr(exception, "response", None)
        if response and hasattr(response, "status_code"):
            status_code = getattr(response, "status_code", None)
            # 5xx - серверные ошибки (транзиентные)
            # 429 - rate limiting (транзиентная)
            # 408 - timeout (транзиентная)
            if status_code and (status_code in (408, 429) or 500 <= status_code < 600):
                return True

    # Проверяем строковое представление ошибки на наличие ключевых слов
    error_str = str(exception).lower()
    transient_keywords = [
        "timeout",
        "connection",
        "network",
        "unavailable",
        "temporary",
        "retry",
        "rate limit",
        "throttle",
    ]
    if any(keyword in error_str for keyword in transient_keywords):
        return True

    # Все остальные ошибки (auth, validation, etc.) - не транзиентные
    return False


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
        retry=retry_if_exception(is_transient_error),
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
            return str(content.strip()) if content else ""
        except Exception as e:
            # Пробрасываем понятную ошибку наверх
            raise RuntimeError(f"Grok error: {type(e).__name__}: {e}")
