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

# Core envelope keys that cannot be overridden by extra
_ENVELOPE_CORE_KEYS: frozenset[str] = frozenset(
    {"status", "code", "message", "detail", "error", "stage"}
)

# Reserved logging extra keys (Python logging module reserved)
_RESERVED_LOG_EXTRA_KEYS: frozenset[str] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }
)


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
        extra: Optional additional fields (core keys are ignored to preserve contract)

    Returns:
        Error envelope dict with status, code, message, detail, error (legacy alias)

    Contract:
        - status: "error"
        - code: machine-readable error code
        - message: same as detail (for backward compatibility)
        - detail: human-readable message
        - error: same as code (legacy alias)
        - stage: optional pipeline stage
        - extra fields merged in (core keys filtered out)
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
        # Filter out core keys to prevent contract violation
        safe_extra = {k: v for k, v in extra.items() if k not in _ENVELOPE_CORE_KEYS}
        envelope.update(safe_extra)

    return envelope


def _sanitize_log_extra(extra: dict[str, Any] | None) -> dict[str, Any]:
    """Sanitize logging extra dict to avoid reserved keys and non-serializable values."""
    if not extra:
        return {}

    safe: dict[str, Any] = {}
    for k, v in extra.items():
        if not isinstance(k, str):
            continue
        if k in _RESERVED_LOG_EXTRA_KEYS:
            continue

        # Keep only simple types that logging handlers can safely serialize
        safe[k] = v if isinstance(v, (str, int, float, bool)) or v is None else repr(v)

    return safe


def _log_exception_safely(msg: str, *, exc: Exception, debug_ctx: dict[str, Any] | None) -> None:
    """Log exception safely, ensuring logging failures never mask the original exception."""
    extra = _sanitize_log_extra(debug_ctx)
    try:
        logging.exception(msg, extra=extra or None)
    except Exception:
        # Never mask the original exception with logging failures
        logging.exception("%s (logging extra failed)", msg)


def safe_call(
    fn: Callable[..., T],
    *args: Any,  # noqa: ANN401
    map_error: Callable[[Exception], tuple[str, str]] | None = None,
    default_code: str = "operation_failed",
    stage: str | None = None,
    debug_ctx: dict[str, Any] | None = None,
    **kwargs: Any,  # noqa: ANN401
) -> T | dict[str, Any]:
    """
    Safely call a function and return either result or error envelope.

    Args:
        fn: Function to call
        *args: Positional arguments to pass to fn
        map_error: Optional function to map exception to (code, detail) tuple
        default_code: Default error code if map_error is None or doesn't handle exception
        stage: Optional pipeline stage name for error envelope
        debug_ctx: Optional debug context (not included in production responses)
        **kwargs: Keyword arguments to pass to fn

    Returns:
        Either the function result (type T) or error envelope dict

    Raises:
        HTTPException: If exception is HTTPException (preserves FastAPI contract)

    Example:
        ```python
        result = safe_call(
            build_week,
            targets,
            diet_flags,
            lang,
            fooddb,
            recipedb,
            map_error=lambda e: ("generation_failed", "Failed to generate plan"),
            stage="generation",
        )
        if isinstance(result, dict) and result.get("status") == "error":
            return result  # Error envelope
        # Use result as T
        ```
    """
    try:
        return fn(*args, **kwargs)
    except HTTPException:
        # Preserve FastAPI contract exceptions
        raise
    except Exception as exc:
        _log_exception_safely("safe_call failed", exc=exc, debug_ctx=debug_ctx)
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
