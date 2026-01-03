# -*- coding: utf-8 -*-
"""
Safe call utilities for weekly plan endpoints.

Provides:
- safe_call: wrapper for error handling with unified envelope
- weekly_plan_error_envelope: unified error response format
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, TypeVar

from fastapi import HTTPException

T = TypeVar("T")


def _is_production() -> bool:
    """Check if running in production environment."""
    return os.getenv("APP_ENV", "").lower() == "production"


def weekly_plan_error_envelope(
    code: str,
    detail: str,
    *,
    stage: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Unified error envelope for weekly plan endpoints.

    Args:
        code: Error code (e.g., "validation_error", "generation_failed")
        detail: Human-readable error message
        stage: Optional pipeline stage where error occurred (e.g., "validation", "generation")
        extra: Optional additional fields

    Returns:
        Error envelope dict with status, code, message, detail, error (legacy alias)

    Contract:
        - status: "error"
        - code: machine-readable error code
        - message: same as detail (for backward compatibility)
        - detail: human-readable message
        - error: same as code (legacy alias)
        - stage: optional pipeline stage
        - extra fields merged in
    """
    envelope: dict[str, Any] = {
        "status": "error",
        "code": code,
        "message": detail,  # Backward compatibility
        "detail": detail,
        "error": code,  # Legacy alias
    }
    if stage is not None:
        envelope["stage"] = stage
    if extra:
        envelope.update(extra)
    return envelope


def safe_call(
    fn: Callable[..., T],
    *,
    map_error: Callable[[Exception], tuple[str, str]] | None = None,
    default_code: str = "operation_failed",
    stage: str | None = None,
    debug_ctx: dict[str, Any] | None = None,
) -> T | dict[str, Any]:
    """
    Safely call a function and return either result or error envelope.

    Args:
        fn: Function to call (will be called with no arguments)
        map_error: Optional function to map exception to (code, detail) tuple
        default_code: Default error code if map_error is None or doesn't handle exception
        stage: Optional pipeline stage name for error envelope
        debug_ctx: Optional debug context (not included in production responses)

    Returns:
        Either the function result (type T) or error envelope dict

    Raises:
        HTTPException: If exception is HTTPException (preserves FastAPI contract)

    Example:
        ```python
        result = safe_call(
            lambda: make_weekly_menu(**kwargs),
            map_error=lambda e: ("generation_failed", "Failed to generate plan"),
            stage="generation",
        )
        if isinstance(result, dict) and result.get("status") == "error":
            return result  # Error envelope
        # Use result as T
        ```
    """
    try:
        return fn()
    except HTTPException:
        # Preserve FastAPI contract exceptions
        raise
    except Exception as exc:
        logging.exception("safe_call failed", extra=debug_ctx or {})
        # Do not include exception details in responses (CodeQL: info exposure)
        # In production, never expose exception details
        is_prod = _is_production()
        if map_error is not None:
            try:
                code, detail = map_error(exc)
                # Production safety: ensure detail never contains exception details
                if is_prod and (str(exc) in detail or type(exc).__name__ in detail):
                    detail = "Operation failed"
            except Exception:
                # map_error itself failed, use defaults
                code = default_code
                detail = "Operation failed"
        else:
            code = default_code
            detail = "Operation failed"

        # Production safety: never include debug_ctx in production responses
        response_extra = None if is_prod else debug_ctx
        return weekly_plan_error_envelope(
            code=code, detail=detail, stage=stage, extra=response_extra
        )
