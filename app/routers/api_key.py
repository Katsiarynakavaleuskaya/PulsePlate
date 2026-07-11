from __future__ import annotations

import logging
import os
import secrets
import sys
import threading

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from settings import is_explicit_developer_env, is_truthy_env_var

from core.utils import resolve_attr

# Shared API key header for all routers
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

logger = logging.getLogger(__name__)
_LENIENT_MODE_WARNING = (
    "Lenient API key mode enabled - for development only, provides no real security"
)
_lenient_mode_warning_logged = False
_lenient_mode_warning_lock = threading.Lock()


def _warn_lenient_mode_once() -> None:
    """Log the development-only API-key warning at most once per process."""

    global _lenient_mode_warning_logged
    if _lenient_mode_warning_logged:
        return
    with _lenient_mode_warning_lock:
        if _lenient_mode_warning_logged:
            return
        logger.warning(_LENIENT_MODE_WARNING)
        _lenient_mode_warning_logged = True


def _reset_lenient_mode_warning_for_tests() -> None:
    """Reset process-local warning state for deterministic focused tests."""

    global _lenient_mode_warning_logged
    with _lenient_mode_warning_lock:
        _lenient_mode_warning_logged = False


def get_api_key(api_key: str | None = Depends(api_key_header)) -> str:
    """Validate the historical app-client API-key compatibility contract."""

    api_key_value = api_key or ""
    dev_mode = is_explicit_developer_env() and is_truthy_env_var(
        "ALLOW_DEV_API_KEY", default="true"
    )
    if dev_mode:
        _warn_lenient_mode_once()

    if expected := os.getenv("API_KEY"):
        if secrets.compare_digest(api_key_value, expected):
            return api_key_value
        allow_normalize = dev_mode and is_truthy_env_var("ALLOW_DEV_API_KEY_NORMALIZE")
        if (
            allow_normalize
            and api_key_value
            and secrets.compare_digest(api_key_value.replace("-", "_"), expected.replace("-", "_"))
        ):
            return expected
        raise HTTPException(status_code=403, detail="Invalid API Key")

    if is_truthy_env_var("API_KEY_REQUIRED"):
        raise HTTPException(status_code=403, detail="API key required but not configured")
    if not dev_mode:
        raise HTTPException(status_code=403, detail="API key required but not configured")
    if not api_key_value:
        raise HTTPException(status_code=403, detail="Missing API Key")

    token = api_key_value.strip()
    forbidden_tokens = {"invalid", "invalid_key", "wrong", "bad", "null"}
    if len(token) < 4 or token.lower() in forbidden_tokens:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return token


def _get_api_key_dynamic(api_key: str | None = Depends(api_key_header)) -> str:
    """Resolve the compatibility guard at request time without legacy ownership."""

    app_package = sys.modules.get("app")
    guard = getattr(app_package, "get_api_key", get_api_key)
    if not callable(guard):
        logger.error("Authentication dependency is unavailable")
        raise HTTPException(status_code=500, detail="Authentication service error")
    try:
        result = guard(api_key)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Authentication dependency failed with unexpected exception type %s",
            type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="Authentication service error") from exc
    if not isinstance(result, str) or not result.strip():
        logger.error("Authentication dependency returned an invalid string result")
        raise HTTPException(status_code=500, detail="Authentication service error")
    return result


def validate_app_api_key(api_key: str | None) -> str:
    """Validate an app-level API key without importing legacy bootstrap surfaces."""

    api_key_value = api_key or ""
    dev_mode = is_explicit_developer_env() and is_truthy_env_var(
        "ALLOW_DEV_API_KEY", default="true"
    )
    if expected := os.getenv("API_KEY"):
        if secrets.compare_digest(api_key_value, expected):
            return api_key_value
        allow_normalize = dev_mode and is_truthy_env_var("ALLOW_DEV_API_KEY_NORMALIZE")
        if (
            allow_normalize
            and api_key_value
            and secrets.compare_digest(api_key_value.replace("-", "_"), expected.replace("-", "_"))
        ):
            return expected
        raise HTTPException(status_code=403, detail="Invalid API Key")

    if is_truthy_env_var("API_KEY_REQUIRED"):
        raise HTTPException(status_code=403, detail="API key required but not configured")

    raise HTTPException(status_code=403, detail="API key required but not configured")


def require_app_api_key(api_key: str | None = Depends(api_key_header)) -> str:
    """Validate app-level API key access for protected routes."""

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing API Key",
        )

    app_get_api_key = resolve_attr("get_api_key", None)
    if not callable(app_get_api_key):
        logger.error(
            "App API key validation unavailable: 'get_api_key' could not be resolved "
            "to a callable (check settings / environment configuration)"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key validation unavailable",
        )
    try:
        result = app_get_api_key(api_key)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error(
            "App API key validation failed with unexpected exception type %s",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key validation unavailable",
        ) from exc
    if not isinstance(result, str):
        logger.error("App API key guard returned non-string result")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key validation unavailable",
        )
    return result
