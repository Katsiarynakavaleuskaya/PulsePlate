from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from core.utils import resolve_attr

# Shared API key header for all routers
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

logger = logging.getLogger(__name__)


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
