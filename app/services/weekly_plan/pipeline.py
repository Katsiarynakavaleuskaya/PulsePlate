# -*- coding: utf-8 -*-
"""
RU: Pipeline логика для weekly plan (generation + postprocess).
EN: Pipeline logic for weekly plan (generation + postprocess).

This module encapsulates the pipeline ordering contract:
- Generation stage runs first
- If generation returns error envelope, postprocess is skipped
- Postprocess stage runs only if generation succeeded
"""

from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

from app.services.weekly_plan.safety import safe_call

T = TypeVar("T")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def _safe_truncated_repr(value: Any, *, limit: int = 1000) -> str:  # noqa: ANN401
    try:
        text = repr(value)
    except Exception as exc:  # pragma: no cover
        return f"<repr failed: {type(exc).__name__}>"
    if len(text) <= limit:
        return text
    return text[:limit]


def run_weekly_pipeline_guarded(
    generation_fn: Callable[..., T],
    postprocess_fn: Callable[[dict[str, Any]], R],
    generation_kwargs: dict[str, Any],
    postprocess_kwargs: dict[str, Any] | None = None,
    *,
    generation_map_error: Callable[[Exception], tuple[str, str]] | None = None,
    generation_default_code: str = "weekly_generation_failed",
    postprocess_map_error: Callable[[Exception], tuple[str, str]] | None = None,
    postprocess_default_code: str = "weekly_postprocess_failed",
    generation_debug_ctx: dict[str, Any] | None = None,
    postprocess_debug_ctx: dict[str, Any] | None = None,
) -> T | R | dict[str, Any]:
    """
    RU: Выполняет pipeline weekly plan с защитой порядка стадий.
    EN: Execute weekly plan pipeline with stage ordering protection.

    Pipeline contract:
    1. Generation stage runs first
    2. If generation returns error envelope, postprocess is skipped
    3. Postprocess stage runs only if generation succeeded

    Args:
        generation_fn: Function to call for generation stage
        postprocess_fn: Function to call for postprocess stage (only if generation succeeds)
        generation_kwargs: Keyword arguments for generation_fn (required)
        postprocess_kwargs: Keyword arguments for postprocess_fn
        generation_map_error: Error mapper for generation stage
        generation_default_code: Default error code for generation
        postprocess_map_error: Error mapper for postprocess stage
        postprocess_default_code: Default error code for postprocess
        generation_debug_ctx: Debug context for generation
        postprocess_debug_ctx: Debug context for postprocess

    Returns:
        Either generation result (if generation fails with error envelope),
        or postprocess result (if generation succeeds and postprocess completes),
        or postprocess error envelope (if postprocess fails)
    """
    postprocess_kwargs = postprocess_kwargs or {}

    # Stage 1: Generation
    result = safe_call(
        generation_fn,
        map_error=generation_map_error,
        default_code=generation_default_code,
        stage="generation",
        debug_ctx=generation_debug_ctx,
        **generation_kwargs,
    )

    # Guard: if generation returned error envelope, skip postprocess
    if isinstance(result, dict) and result.get("status") == "error":
        # Return error envelope as-is (no mutation)
        return result

    # Stage 2: Postprocess (only if generation succeeded)
    week = result

    # week is guaranteed to be T (not error envelope) at this point
    # For weekly plan, T is always dict[str, Any]
    if not isinstance(week, dict):
        # This should not happen for weekly plan, but handle gracefully
        logger.error(
            "Weekly pipeline generation returned non-dict: type=%s repr=%s",
            type(week).__name__,
            _safe_truncated_repr(week),
        )
        raise TypeError(f"Expected dict from generation, got {type(week)}")

    # Wrap postprocess_fn call
    def _postprocess_wrapper() -> R:
        return postprocess_fn(week)

    dto: R | dict[str, Any] = safe_call(
        _postprocess_wrapper,
        map_error=postprocess_map_error,
        default_code=postprocess_default_code,
        stage="postprocess",
        debug_ctx=postprocess_debug_ctx,
    )

    # safe_call returns either R or error envelope dict
    return dto
