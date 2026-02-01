"""Rate limiting configuration for expensive endpoints.

RU: Конфигурация rate-limiting для дорогих endpoints (LLM, exports).
EN: Rate limiting configuration for expensive endpoints (LLM, exports).

This module provides:
- SlowAPI Limiter instance (optional dependency)
- Proxy-aware client key (pseudonymous) with CIDR trusted proxies support
- 429 JSON handler
- FastAPI wiring helper
"""

from __future__ import annotations

import ipaddress
import logging
import os
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast

from fastapi import Request
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


def rate_limit_insight_value() -> str:
    """Return current insight rate limit string (env-backed)."""
    return os.getenv("RATE_LIMIT_INSIGHT", "10/minute")


def rate_limit_exports_value() -> str:
    """Return current exports rate limit string (env-backed)."""
    return os.getenv("RATE_LIMIT_EXPORTS", "20/minute")


# Backward-compat names (existing imports expect these).
# NOTE: These are captured at import-time; tests that override env must reload this module.
RATE_LIMIT_INSIGHT = rate_limit_insight_value()
RATE_LIMIT_EXPORTS = rate_limit_exports_value()

# OpenAPI response spec for 429
RATE_LIMIT_429_RESPONSES: dict[int | str, dict[str, Any]] = {
    429: {"description": "Rate limit exceeded"}
}


def parse_trusted_proxies(
    env_value: str,
) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network | str]:
    """Parse TRUSTED_PROXIES env var into list of networks/hosts.

    RU: Парсит TRUSTED_PROXIES в список сетей/хостов.
    EN: Parses TRUSTED_PROXIES into list of networks/hosts.

    Supports:
    - IP addresses (e.g., "127.0.0.1")
    - CIDR networks (e.g., "172.30.100.0/24")
    - Hostnames (e.g., "caddy")
    """
    result: list[ipaddress.IPv4Network | ipaddress.IPv6Network | str] = []
    for entry in env_value.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            network = ipaddress.ip_network(entry, strict=False)
            result.append(network)
        except ValueError:
            result.append(entry)
    return result


def is_trusted_proxy(
    remote_host: str,
    trusted_entries: list[ipaddress.IPv4Network | ipaddress.IPv6Network | str],
) -> bool:
    """Check if remote_host is in the trusted proxies list (CIDR/IP/hostname)."""
    for entry in trusted_entries:
        if isinstance(entry, str):
            if remote_host == entry:
                return True
            continue
        try:
            remote_ip = ipaddress.ip_address(remote_host)
        except ValueError:
            continue
        if remote_ip in entry:
            return True
    return False


def extract_client_ip(
    request: Request, trusted_entries: list[ipaddress.IPv4Network | ipaddress.IPv6Network | str]
) -> str:
    """Extract client IP from request with proxy-aware header precedence.

    Precedence (only when request comes from a trusted proxy):
    1. CF-Connecting-IP
    2. X-Forwarded-For (first IP)
    3. request.client.host
    """
    remote_host = request.client.host if request.client else ""

    if is_trusted_proxy(remote_host, trusted_entries):
        cf_ip = request.headers.get("cf-connecting-ip", "").strip()
        if cf_ip:
            try:
                ipaddress.ip_address(cf_ip)
                return cf_ip
            except ValueError:
                pass

        forwarded_for = request.headers.get("x-forwarded-for", "").strip()
        if forwarded_for:
            forwarded_ips = [ip.strip() for ip in forwarded_for.split(",")]
            if forwarded_ips:
                try:
                    ipaddress.ip_address(forwarded_ips[0])
                    return forwarded_ips[0]
                except ValueError:
                    pass

    return remote_host


def rate_limit_client_key(request: Request) -> str:
    """Return pseudonymous client key for rate limiting.

    RU: Возвращает псевдонимизированный ключ клиента для rate-limiting.
    EN: Returns pseudonymous client key for rate limiting.

    This function is used as key_func for SlowAPI Limiter.
    Produces a pseudonymous fingerprint (hash), never the raw IP.

    Args:
        request: FastAPI request object

    Returns:
        Pseudonymous fingerprint (hashed, privacy-friendly)
    """
    from core.fingerprint_security import compute_fingerprint

    trusted_entries = parse_trusted_proxies(os.getenv("TRUSTED_PROXIES", ""))
    client_ip = extract_client_ip(request, trusted_entries)
    if not client_ip:
        return "unknown"
    return compute_fingerprint(client_ip)


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


LimitValue = str | Callable[[], str]
F = TypeVar("F", bound=Callable[..., Any])


def limit_if_available(rate: LimitValue) -> Callable[[F], F]:
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
            return cast(F, limiter.limit(rate)(func))
        # No-op: return function unchanged
        return func

    return decorator


__all__ = [
    "limiter",
    "rate_limit_client_key",
    "wire_rate_limiting",
    "limit_if_available",
    "RATE_LIMIT_429_RESPONSES",
    "RATE_LIMIT_INSIGHT",
    "RATE_LIMIT_EXPORTS",
    "rate_limit_insight_value",
    "rate_limit_exports_value",
    "parse_trusted_proxies",
    "is_trusted_proxy",
    "extract_client_ip",
]
