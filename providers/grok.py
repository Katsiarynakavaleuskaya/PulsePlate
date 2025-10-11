from openai import AsyncOpenAI


# Try importing new exception classes (openai >= 1.0)
try:
    from openai import (
        APIConnectionError,
        APIStatusError,
        APITimeoutError,
        RateLimitError,
    )
except ImportError:
    # Fallback for older openai versions
    APITimeoutError = TimeoutError
    APIConnectionError = ConnectionError

    class RateLimitError(Exception):  # type: ignore[no-redef]
        """Fallback for rate limit errors on older SDKs."""

        pass

    class APIStatusError(Exception):  # type: ignore[no-redef]
        """Fallback for older openai SDK versions."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args)
            self.status_code = kwargs.get("status_code", 500)


from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


def is_transient_exception(exc: BaseException) -> bool:
    """
    Определяет, является ли исключение временным и требует повтора.

    Retry только для:
    - timeouts (APITimeoutError)
    - connection errors (APIConnectionError)
    - rate limits 429 (RateLimitError)
    - server errors 5xx (APIStatusError с кодом 500-599)

    НЕ retry для:
    - authentication 401
    - permission 403
    - client errors 400, 404 и др.
    """
    # OpenAI SDK специфичные transient errors
    if isinstance(exc, APITimeoutError | APIConnectionError | RateLimitError):
        return True

    # Проверяем HTTP status код для APIStatusError
    if isinstance(exc, APIStatusError):
        status_code: int = exc.status_code
        # Retry только для server errors (500-599) и rate limit (429)
        return status_code == 429 or (500 <= status_code < 600)

    return False


class GrokProvider:
    """
    Минималистичный провайдер к x.ai (Grok) через совместимый OpenAI SDK.
    Совместим с вызовом из llm.py:
        GrokProvider(endpoint=..., model=..., api_key=...)
    """

    name = "grok"

    def __init__(self, endpoint: str, model: str, api_key: str, timeout: float | None = 30.0):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key = api_key
        # создаём асинхронного клиента (OpenAI совместимый эндпоинт у x.ai)
        self.client = AsyncOpenAI(base_url=self.endpoint, api_key=self.api_key)
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception(is_transient_exception),
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
            return (content or "").strip()
        except Exception as e:
            if is_transient_exception(e):
                raise
            raise RuntimeError(f"Grok error: {type(e).__name__}: {e}") from e
