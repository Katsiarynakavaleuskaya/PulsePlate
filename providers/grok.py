from openai import AsyncOpenAI


try:
    import openai
except ImportError as exc:  # pragma: no cover - openai is a strict dependency
    raise RuntimeError("GrokProvider requires the 'openai' package to be installed") from exc


_OPENAI_TIMEOUT_ERROR = getattr(openai, "APITimeoutError", None)
_OPENAI_CONNECTION_ERROR = getattr(openai, "APIConnectionError", None)
_OPENAI_STATUS_ERROR = getattr(openai, "APIStatusError", None)
_OPENAI_RATE_LIMIT_ERROR = getattr(openai, "RateLimitError", None)


class APITimeoutError(TimeoutError):
    """Friendly timeout error used for testing and compatibility."""

    def __init__(self, message: str = "Request timed out.", request: object | None = None):
        super().__init__(message)
        self.request = request


class APIConnectionError(ConnectionError):
    """Friendly connection error mirroring OpenAI semantics."""

    def __init__(self, message: str = "Connection error.", request: object | None = None):
        super().__init__(message)
        self.request = request


class _FallbackAPIStatusError(Exception):
    """Fallback for OpenAI API status errors with status code semantics."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        http_status: int | None = None,
        response: object | None = None,
        body: object | None = None,
        **kwargs,
    ):
        super().__init__(message)
        resolved_status = status_code if status_code is not None else http_status
        self.status_code = resolved_status if resolved_status is not None else 500
        self.response = response
        self.body = body
        for key, value in kwargs.items():
            setattr(self, key, value)


class APIStatusError(_FallbackAPIStatusError):
    """User-friendly API status error."""


class RateLimitError(_FallbackAPIStatusError):
    """Specific rate limit error (HTTP 429)."""

    def __init__(self, message: str = "Rate limit exceeded.", **kwargs):
        kwargs.setdefault("status_code", 429)
        super().__init__(message, **kwargs)


from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


_TIMEOUT_ERROR_TYPES: tuple[type[BaseException], ...] = tuple(
    cls for cls in (_OPENAI_TIMEOUT_ERROR, APITimeoutError) if isinstance(cls, type)
)
_CONNECTION_ERROR_TYPES: tuple[type[BaseException], ...] = tuple(
    cls for cls in (_OPENAI_CONNECTION_ERROR, APIConnectionError) if isinstance(cls, type)
)
_STATUS_ERROR_TYPES: tuple[type[BaseException], ...] = tuple(
    cls for cls in (_OPENAI_STATUS_ERROR, APIStatusError) if isinstance(cls, type)
)
_RATE_LIMIT_ERROR_TYPES: tuple[type[BaseException], ...] = tuple(
    cls for cls in (_OPENAI_RATE_LIMIT_ERROR, RateLimitError) if isinstance(cls, type)
)


def _extract_status_code(exc: BaseException) -> int | None:
    """Attempt to extract an HTTP status code from an OpenAI-style exception."""

    status = getattr(exc, "status_code", None)
    if status is not None and isinstance(status, int):
        return status

    response = getattr(exc, "response", None)
    if response is not None:
        return getattr(response, "status_code", None)

    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        maybe_status = body.get("status")
        if isinstance(maybe_status, int):
            return maybe_status
    return None


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
    if _TIMEOUT_ERROR_TYPES and isinstance(exc, _TIMEOUT_ERROR_TYPES):
        return True

    if _CONNECTION_ERROR_TYPES and isinstance(exc, _CONNECTION_ERROR_TYPES):
        return True

    if _RATE_LIMIT_ERROR_TYPES and isinstance(exc, _RATE_LIMIT_ERROR_TYPES):
        status_code = _extract_status_code(exc)
        return status_code == 429 if status_code is not None else True

    if _STATUS_ERROR_TYPES and isinstance(exc, _STATUS_ERROR_TYPES):
        status_code = _extract_status_code(exc)
        if status_code is None:
            return False
        # Retry только для server errors (500-599) и rate limit (429)
        return status_code == 429 or (500 <= status_code < 600)

    if isinstance(exc, RateLimitError):
        return True

    # Проверяем HTTP status код для APIStatusError
    if isinstance(exc, APIStatusError):
        status_code = _extract_status_code(exc)
        if status_code is None:
            return False
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
