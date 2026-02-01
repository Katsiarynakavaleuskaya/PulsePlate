"""Rate limiting configuration for expensive endpoints.

RU: Конфигурация rate-limiting для дорогих endpoints (LLM, exports).
EN: Rate limiting configuration for expensive endpoints (LLM, exports).

This module provides:
- SlowAPI Limiter instance (optional dependency)
- 429 JSON handler
- FastAPI wiring helper
"""

from __future__ import annotations

import functools
import logging
import os
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from fastapi import Request
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

# Rate limit defaults (override via env vars)
RATE_LIMIT_INSIGHT = os.getenv("RATE_LIMIT_INSIGHT", "10/minute")
RATE_LIMIT_EXPORTS = os.getenv("RATE_LIMIT_EXPORTS", "20/minute")

# OpenAPI response spec for 429
RATE_LIMIT_429_RESPONSES: dict[int | str, dict[str, Any]] = {
    429: {"description": "Rate limit exceeded"}
}


def rate_limit_client_key(request: Request) -> str:
    """Return pseudonymous client key for rate limiting.

    RU: Возвращает псевдонимизированный ключ клиента для rate-limiting.
    EN: Returns pseudonymous client key for rate limiting.

    This function is used as key_func for SlowAPI Limiter.
    For compatibility and privacy, we reuse the existing core fingerprint helper.

    Args:
        request: FastAPI request object

    Returns:
        Pseudonymous fingerprint (hashed, privacy-friendly)
    """
    from core.fingerprint_security import _client_fingerprint

    return _client_fingerprint(request) or "unknown"


# Lazy import of SlowAPI (optional dependency in runtime)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    # Create limiter instance
    limiter = Limiter(key_func=rate_limit_client_key)

except ImportError:
    # SlowAPI not available - create no-op stubs
    limiter = None  # type: ignore[assignment]
    RateLimitExceeded = None  # type: ignore[assignment,misc]
    SlowAPIMiddleware = None  # type: ignore[assignment,misc]
    _rate_limit_exceeded_handler = None  # type: ignore[assignment]


def _rate_limit_exceeded_json_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return JSON error envelope for 429 rate limit exceeded.

    RU: Возвращает JSON-конверт для 429 (лимит превышен).
    EN: Returns JSON error envelope for 429 (rate limit exceeded).

    Uses standard FastAPI error contract: {"detail": "..."}
    """
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
    )


def wire_rate_limiting(app: FastAPI) -> None:
    """Wire rate limiting into FastAPI app.

    RU: Подключает rate-limiting в FastAPI приложение.
    EN: Wires rate limiting into FastAPI application.

    This function:
    - Attaches limiter to app.state
    - Registers 429 exception handler
    - Adds SlowAPIMiddleware

    If SlowAPI is not available, this is a no-op (graceful degradation).

    Args:
        app: FastAPI application instance
    """
    if limiter is None:
        logger.warning("SlowAPI not available; rate limiting disabled")
        return

    # Attach limiter to app state
    app.state.limiter = limiter

    # Register 429 handler
    if RateLimitExceeded is not None:
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_json_handler)

    # Add middleware
    if SlowAPIMiddleware is not None:
        app.add_middleware(SlowAPIMiddleware)

    logger.info("Rate limiting enabled (slowapi)")


F = TypeVar("F", bound=Callable[..., Any])


def limit_if_available(rate: str) -> Callable[[F], F]:
    """Conditional rate limit decorator (no-op if limiter is None).

    RU: Условный декоратор rate-limit (no-op если limiter недоступен).
    EN: Conditional rate limit decorator (no-op if limiter is unavailable).

    This allows endpoints to use @limit_if_available(...) without breaking
    when SlowAPI is not installed.

    Args:
        rate: Rate limit string (e.g., "10/minute")

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        if limiter is not None:
            # Apply real slowapi limit
            return limiter.limit(rate)(func)  # type: ignore[return-value]
        # No-op: return function unchanged
        return func

    return decorator


__all__ = [
    "limiter",
    "rate_limit_client_key",
    "wire_rate_limiting",
    "limit_if_available",
    "RATE_LIMIT_INSIGHT",
    "RATE_LIMIT_EXPORTS",
    "RATE_LIMIT_429_RESPONSES",
]
