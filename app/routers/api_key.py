from __future__ import annotations

import logging
import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from core.utils import resolve_attr

# Shared API key header for all routers
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

logger = logging.getLogger(__name__)
_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})
_DEVELOPER_LIKE_ENVS = frozenset({"local", "dev", "development", "test", "testing", "ci"})


def _is_truthy(value: str | None) -> bool:
    """Return whether a raw environment value is truthy."""

    return (value or "").strip().lower() in _TRUTHY_ENV_VALUES


def _get_runtime_env_name() -> str:
    """Return the canonical runtime environment label without importing settings."""

    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    runtime_env = (os.getenv("ENVIRONMENT") or "").strip().lower()
    if app_env in {"production", "prod", "staging"}:
        return app_env
    if runtime_env:
        return runtime_env
    if app_env:
        return app_env
    return "local"


def _is_explicit_developer_env() -> bool:
    """Mirror the repo's explicit developer-env semantics without settings import."""

    return _get_runtime_env_name() in _DEVELOPER_LIKE_ENVS


def validate_app_api_key(api_key: str | None) -> str:
    """Validate an app-level API key without importing legacy bootstrap surfaces."""

    api_key_value = api_key or ""
    dev_mode = _is_explicit_developer_env() and _is_truthy(os.getenv("ALLOW_DEV_API_KEY", "true"))
    if expected := os.getenv("API_KEY"):
        if secrets.compare_digest(api_key_value, expected):
            return api_key_value
        allow_normalize = dev_mode and _is_truthy(os.getenv("ALLOW_DEV_API_KEY_NORMALIZE"))
        if (
            allow_normalize
            and api_key_value
            and secrets.compare_digest(api_key_value.replace("-", "_"), expected.replace("-", "_"))
        ):
            return expected
        raise HTTPException(status_code=403, detail="Invalid API Key")

    if _is_truthy(os.getenv("API_KEY_REQUIRED")):
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
        logger.exception("App API key validation failed")
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
