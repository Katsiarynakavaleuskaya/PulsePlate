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
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, Literal, TypeVar, cast

from fastapi import Request
from fastapi.responses import JSONResponse
from app.utils.feature_flags import _is_truthy
from pydantic import BaseModel

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


def _rate_limiting_enabled() -> bool:
    """Decide whether rate limiting should be active in this process.

    RU: Решает, должен ли rate-limiting быть активен в этом процессе.
    EN: Decides whether rate limiting should be active in this process.

    Policy:
    - In normal runtime: enabled (if slowapi is installed).
    - In tests (`TESTING=true`): disabled by default to avoid cross-test pollution,
      unless explicitly enabled via `RATE_LIMITING_IN_TESTS=true` in a dedicated suite.
    """
    if _is_truthy(os.getenv("TESTING")) and not _is_truthy(os.getenv("RATE_LIMITING_IN_TESTS")):
        return False
    return True


def rate_limit_insight_value() -> str:
    """Return current insight rate limit string (env-backed)."""
    return os.getenv("RATE_LIMIT_INSIGHT", "10/minute")


def rate_limit_exports_value() -> str:
    """Return current exports rate limit string (env-backed)."""
    return os.getenv("RATE_LIMIT_EXPORTS", "20/minute")


def rate_limit_apple_verify_value() -> str:
    """Return Apple verify rate limit string (env-backed)."""
    return os.getenv("RATE_LIMIT_APPLE_VERIFY", "10/minute")


# Backward-compat names (existing imports expect these).
# NOTE: These are captured at import-time; tests that override env must reload this module.
RATE_LIMIT_INSIGHT = rate_limit_insight_value()
RATE_LIMIT_EXPORTS = rate_limit_exports_value()
RATE_LIMIT_APPLE_VERIFY = rate_limit_apple_verify_value()


class RateLimitErrorResponse(BaseModel):
    """Error response for 429 rate-limit exceeded.

    Matches FastAPI/Starlette HTTPException envelope: {"detail": "..."}.
    """

    detail: str


# OpenAPI response spec for 429
RATE_LIMIT_429_RESPONSES: dict[int | str, dict[str, Any]] = {
    429: {"description": "Rate limit exceeded", "model": RateLimitErrorResponse}
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


@lru_cache(maxsize=32)
def _trusted_proxies_cached(
    env_value: str,
) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network | str, ...]:
    """Cached parsing of TRUSTED_PROXIES entries.

    RU: Кэшированный парсинг TRUSTED_PROXIES.
    EN: Cached parsing of TRUSTED_PROXIES.

    Env values are treated as immutable for the lifetime of the process in runtime.
    In tests, suites that change env must reload this module (canonical pattern).
    """
    return tuple(parse_trusted_proxies(env_value))


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
                return str(cf_ip)
            except ValueError:
                pass

        forwarded_for = request.headers.get("x-forwarded-for", "").strip()
        if forwarded_for:
            forwarded_ips = [ip.strip() for ip in forwarded_for.split(",")]
            if forwarded_ips:
                try:
                    ipaddress.ip_address(forwarded_ips[0])
                    return str(forwarded_ips[0])
                except ValueError:
                    pass

    return str(remote_host)


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

    trusted_entries = list(_trusted_proxies_cached(os.getenv("TRUSTED_PROXIES", "")))
    client_ip = extract_client_ip(request, trusted_entries)
    if not client_ip:
        return "unknown"
    return str(compute_fingerprint(client_ip))


# Lazy import of SlowAPI (optional dependency in runtime)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    # Create limiter instance
    limiter = Limiter(key_func=rate_limit_client_key)
    limiter.enabled = _rate_limiting_enabled()

except ImportError:  # pragma: no cover - optional dependency
    # SlowAPI not available - create no-op stubs
    limiter = None  # type: ignore[assignment]
    RateLimitExceeded = None  # type: ignore[misc,assignment]
    SlowAPIMiddleware = None  # type: ignore[misc,assignment]
    _rate_limit_exceeded_handler = None  # type: ignore[assignment]

_rate_limiting_wired_app_ids: set[int] = set()
_MISSING = object()

RateLimitWiringState = Literal["none", "complete", "partial"]


@dataclass(frozen=True, slots=True)
class _RateLimitWiringSnapshot:
    user_middleware: tuple[Any, ...]
    exception_handlers: dict[Any, Any]
    state_limiter: Any
    receipt_present: bool
    limiter_enabled: Any


def _callable_key(value: object) -> tuple[str, str] | None:
    module = getattr(value, "__module__", None)
    qualname = getattr(value, "__qualname__", None)
    if not isinstance(module, str) or not isinstance(qualname, str):
        return None
    return module, qualname


def _same_callable(existing: object, expected: object) -> bool:
    return existing is expected or (
        _callable_key(existing) is not None and _callable_key(existing) == _callable_key(expected)
    )


def _middleware_class(middleware: object) -> object:
    return getattr(middleware, "cls", None)


def _slowapi_middleware_counts(app: FastAPI) -> tuple[int, int]:
    if SlowAPIMiddleware is None:
        return 0, 0

    expected_name = getattr(SlowAPIMiddleware, "__name__", "SlowAPIMiddleware")
    matching = 0
    foreign_named = 0
    for middleware in app.user_middleware:
        middleware_class = _middleware_class(middleware)
        if _same_callable(middleware_class, SlowAPIMiddleware):
            matching += 1
        elif getattr(middleware_class, "__name__", None) == expected_name:
            foreign_named += 1
    return matching, foreign_named


def _rate_limit_handler_state(app: FastAPI) -> tuple[int, bool, bool]:
    if RateLimitExceeded is None:
        return 0, False, False

    expected_name = getattr(RateLimitExceeded, "__name__", "RateLimitExceeded")
    matching_handlers = [
        handler
        for error_type, handler in app.exception_handlers.items()
        if _same_callable(error_type, RateLimitExceeded)
    ]
    foreign_named = any(
        getattr(error_type, "__name__", None) == expected_name
        and not _same_callable(error_type, RateLimitExceeded)
        for error_type in app.exception_handlers
    )
    exact_handler = len(matching_handlers) == 1 and _same_callable(
        matching_handlers[0], _rate_limit_exceeded_json_handler
    )
    return len(matching_handlers), exact_handler, foreign_named


def _classify_rate_limit_wiring(app: FastAPI) -> RateLimitWiringState:
    state_limiter_present = hasattr(app.state, "limiter")
    state_limiter_exact = state_limiter_present and app.state.limiter is limiter
    handler_count, handler_exact, foreign_handler = _rate_limit_handler_state(app)
    middleware_count, foreign_middleware = _slowapi_middleware_counts(app)
    if not any(
        (
            state_limiter_present,
            handler_count,
            middleware_count,
            foreign_handler,
            foreign_middleware,
        )
    ):
        return "none"

    if (
        state_limiter_exact
        and handler_count == 1
        and handler_exact
        and middleware_count == 1
        and not foreign_handler
        and not foreign_middleware
    ):
        return "complete"
    return "partial"


def _capture_rate_limit_wiring(app: FastAPI) -> _RateLimitWiringSnapshot:
    state_limiter = getattr(app.state, "limiter", _MISSING)
    limiter_enabled = getattr(limiter, "enabled", _MISSING)
    return _RateLimitWiringSnapshot(
        user_middleware=tuple(app.user_middleware),
        exception_handlers=dict(app.exception_handlers),
        state_limiter=state_limiter,
        receipt_present=id(app) in _rate_limiting_wired_app_ids,
        limiter_enabled=limiter_enabled,
    )


def _restore_rate_limit_wiring(app: FastAPI, snapshot: _RateLimitWiringSnapshot) -> None:
    app.user_middleware[:] = snapshot.user_middleware
    app.exception_handlers.clear()
    app.exception_handlers.update(snapshot.exception_handlers)
    if snapshot.state_limiter is _MISSING:
        if hasattr(app.state, "limiter"):
            delattr(app.state, "limiter")
    else:
        app.state.limiter = snapshot.state_limiter

    if snapshot.receipt_present:
        _rate_limiting_wired_app_ids.add(id(app))
    else:
        _rate_limiting_wired_app_ids.discard(id(app))

    if limiter is not None and snapshot.limiter_enabled is not _MISSING:
        limiter.enabled = cast(bool, snapshot.limiter_enabled)


def rate_limiting_should_be_wired() -> bool:
    """Return whether this process expects the optional SlowAPI stack."""

    return limiter is not None and _rate_limiting_enabled()


def _rate_limit_exceeded_json_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return JSON error envelope for 429 rate limit exceeded.

    RU: Возвращает JSON-конверт для 429 (лимит превышен) с i18n.
    EN: Returns JSON error envelope for 429 (rate limit exceeded) with i18n.

    Uses standard FastAPI error contract: {"detail": "..."}
    Language is determined from request state or Accept-Language header.
    """
    from core.i18n import normalize_lang, t

    # Get language from request state (middleware-set) or Accept-Language header
    lang_raw = getattr(getattr(request, "state", None), "lang", None)
    if not lang_raw:
        lang_raw = request.headers.get("accept-language", "en")
    lang = normalize_lang(lang_raw)

    try:
        detail = t(lang, "rate_limit.exceeded")
    except KeyError:
        detail = "Rate limit exceeded"

    if request.url.path == "/api/v1/vip/fitchef/insight":
        from app.contracts.vip_contract import vip_error

        return JSONResponse(
            status_code=429,
            content=vip_error(code="rate_limit_exceeded", message=detail),
        )

    return JSONResponse(
        status_code=429,
        content={"detail": detail},
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
    wiring_state = _classify_rate_limit_wiring(app)
    enabled = _rate_limiting_enabled()

    if wiring_state == "none":
        _rate_limiting_wired_app_ids.discard(id(app))

    if limiter is None:  # pragma: no cover - optional dependency
        if wiring_state != "none":
            raise RuntimeError("Partial SlowAPI rate-limit wiring detected.")
        logger.warning("SlowAPI not available; rate limiting disabled")  # pragma: no cover
        return  # pragma: no cover

    if not enabled:
        if wiring_state != "none":
            raise RuntimeError("SlowAPI rate-limit wiring exists while rate limiting is disabled.")
        limiter.enabled = False
        logger.debug("Rate limiting disabled by environment")
        return

    if RateLimitExceeded is None or SlowAPIMiddleware is None:
        raise RuntimeError("SlowAPI middleware and exception handler are unavailable.")

    if wiring_state == "complete":
        limiter.enabled = True
        _rate_limiting_wired_app_ids.add(id(app))
        return
    if wiring_state == "partial":
        raise RuntimeError("Partial SlowAPI rate-limit wiring detected.")
    if getattr(app, "middleware_stack", None) is not None:
        raise RuntimeError("Cannot wire SlowAPI after the middleware stack is built.")

    snapshot = _capture_rate_limit_wiring(app)
    try:
        limiter.enabled = True
        app.add_middleware(SlowAPIMiddleware)
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_json_handler)
        app.state.limiter = limiter
        _rate_limiting_wired_app_ids.add(id(app))
        if _classify_rate_limit_wiring(app) != "complete":
            raise RuntimeError("SlowAPI rate-limit wiring validation failed.")
    except Exception:
        _restore_rate_limit_wiring(app, snapshot)
        raise

    logger.info("Rate limiting enabled (slowapi)")


def _is_rate_limiting_wired_for_app(app: FastAPI | None) -> bool:
    # app=None is reserved for focused tests/CI that validate the other
    # production invariants with a pre-populated wired-app receipt.
    if app is None:
        return bool(_rate_limiting_wired_app_ids)
    return _classify_rate_limit_wiring(app) == "complete"


def require_rate_limiting_ready_for_production(app: FastAPI | None = None) -> None:
    """Fail closed when production/staging cannot enforce rate limits."""

    from settings import is_production_like_env, is_truthy_env_var

    if not is_production_like_env():
        return
    if is_truthy_env_var("TESTING", "false"):
        raise RuntimeError(
            "TESTING must be false in production/staging environments; "
            "it can disable rate limiting."
        )
    if limiter is None:
        raise RuntimeError("SlowAPI limiter is required in production/staging environments.")
    if RateLimitExceeded is None or SlowAPIMiddleware is None:
        raise RuntimeError(
            "SlowAPI middleware and exception handler are required in "
            "production/staging environments."
        )
    if not _rate_limiting_enabled() or not getattr(limiter, "enabled", True):
        raise RuntimeError("Rate limiting must be enabled in production/staging environments.")
    if not _is_rate_limiting_wired_for_app(app):
        raise RuntimeError(
            "SlowAPI rate limiting must be wired into the FastAPI app before serving "
            "production/staging traffic."
        )


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
        if limiter is not None and getattr(limiter, "enabled", True):
            # Apply real slowapi limit
            return cast(F, limiter.limit(rate)(func))
        # No-op: return function unchanged
        return func

    return decorator


__all__ = [
    "limiter",
    "rate_limit_client_key",
    "wire_rate_limiting",
    "rate_limiting_should_be_wired",
    "limit_if_available",
    "require_rate_limiting_ready_for_production",
    "RATE_LIMIT_429_RESPONSES",
    "RateLimitErrorResponse",
    "RATE_LIMIT_INSIGHT",
    "RATE_LIMIT_EXPORTS",
    "RATE_LIMIT_APPLE_VERIFY",
    "rate_limit_insight_value",
    "rate_limit_exports_value",
    "rate_limit_apple_verify_value",
    "parse_trusted_proxies",
    "is_trusted_proxy",
    "extract_client_ip",
]
