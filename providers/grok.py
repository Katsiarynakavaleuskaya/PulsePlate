from typing import Optional

import httpx
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)


class GrokError(RuntimeError):
    """Grok provider error."""

    def __init__(self, original_error: Exception) -> None:
        super().__init__(f"Grok error: {type(original_error).__name__}: {original_error}")
        self.original_error = original_error


def is_transient_error(exception: Exception) -> bool:
    """
    Определяет, является ли ошибка временной/транзиентной и стоит ли её повторить.

    Args:
        exception: Исключение для проверки

    Returns:
        True если ошибка транзиентная и стоит повторить запрос
    """
    # Don't retry system-level exceptions (KeyboardInterrupt, SystemExit, etc.)
    if not isinstance(exception, Exception):
        return False

    # Unwrap chained exceptions to get the original underlying exception
    original_exception = exception
    seen: set[int] = set()
    while isinstance(original_exception, Exception) and id(original_exception) not in seen:
        seen.add(id(original_exception))
        next_exception = getattr(original_exception, "__cause__", None)
        if next_exception is not None:
            original_exception = next_exception
            continue
        next_exception = getattr(original_exception, "__context__", None)
        if next_exception is not None:
            original_exception = next_exception
            continue
        break
    # Network/connection errors - всегда транзиентные
    if isinstance(
        original_exception,
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

    # Check HTTP status codes for OpenAI SDK errors
    if hasattr(original_exception, "response"):
        response = getattr(original_exception, "response", None)
        if response and hasattr(response, "status_code"):
            status_code = getattr(response, "status_code", None)
            # 5xx - server errors (transient)
            # 429 - rate limiting (transient)
            # 408 - timeout (transient)
            if status_code and (status_code in (408, 429) or 500 <= status_code < 600):
                return True

    # Check error string representation for transient keywords
    error_str = str(original_exception).lower()
    transient_keywords = {
        "timeout",
        "connection",
        "network",
        "unavailable",
        "temporary",
        "retry",
        "rate limit",
        "throttle",
    }
    return any(keyword in error_str for keyword in transient_keywords)


class GrokProvider:
    """
    Minimal provider for x.ai (Grok) via compatible OpenAI SDK.
    Sovmestim s vyzovom iz llm.py:
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
            raise GrokError(e) from e
