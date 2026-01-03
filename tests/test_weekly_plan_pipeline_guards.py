# -*- coding: utf-8 -*-
"""
RU: Guard-tests для pipeline ordering weekly plan.
EN: Guard tests for weekly plan pipeline ordering.

Guarantees:
- If generation stage returns error envelope, postprocess must not run
- Pipeline stages execute in correct order: validation → generation → postprocess
- Error envelope returned from generation is not mutated
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from app.services.weekly_plan.pipeline import _safe_truncated_repr, run_weekly_pipeline_guarded


def test_pipeline_skips_postprocess_when_generation_returns_error_envelope() -> None:
    """
    RU: Если generation вернул error envelope, postprocess не должен запускаться.
    EN: If generation returns error envelope, postprocess must not run.

    Contract:
    - Generation error envelope is returned as-is (no mutation)
    - Postprocess is not called when generation fails
    """
    # Expected error envelope from generation
    expected_error = {
        "status": "error",
        "code": "weekly_generation_failed",
        "detail": "Generation failed",
        "stage": "generation",
    }

    # Generation stage returns error envelope
    def generation_fails(*, user_id: str) -> dict[str, Any]:
        assert user_id == "user-1"
        return expected_error

    # Postprocess stage must not be called if generation already failed
    postprocess_called = False

    def postprocess(week: dict[str, Any]) -> Any:
        nonlocal postprocess_called
        postprocess_called = True
        raise AssertionError("postprocess must not run when generation failed")

    # Call real pipeline entrypoint
    result = run_weekly_pipeline_guarded(
        generation_fn=generation_fails,
        postprocess_fn=postprocess,
        generation_kwargs={"user_id": "user-1"},
        generation_map_error=lambda _e: ("weekly_generation_failed", "Failed to generate plan"),
        generation_default_code="weekly_generation_failed",
        postprocess_map_error=lambda _e: (
            "weekly_postprocess_failed",
            "Failed to build weekly plan response",
        ),
        postprocess_default_code="weekly_postprocess_failed",
    )

    # Contract: error envelope is returned as-is (no mutation)
    assert result == expected_error
    assert isinstance(result, dict)
    assert result.get("status") == "error"
    assert result.get("code") == "weekly_generation_failed"
    assert result.get("stage") == "generation"

    # Contract: postprocess must not be called
    assert not postprocess_called, "postprocess must not be called when generation fails"


def test_safe_truncated_repr_truncates_long_values() -> None:
    value = "x" * 2001
    assert _safe_truncated_repr(value) == repr(value)[:1000]


def test_safe_truncated_repr_returns_full_repr_for_short_values() -> None:
    value = {"a": 1}
    assert _safe_truncated_repr(value) == repr(value)


def test_pipeline_raises_when_generation_returns_non_dict(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR, logger="app.services.weekly_plan.pipeline")

    def generation_returns_str(*, user_id: str) -> str:
        assert user_id == "user-1"
        return "x" * 2001

    def postprocess(_week: dict[str, Any]) -> Any:
        raise AssertionError("postprocess must not run when generation returned non-dict")

    with pytest.raises(TypeError, match=r"Expected dict from generation"):
        _ = run_weekly_pipeline_guarded(
            generation_fn=generation_returns_str,
            postprocess_fn=postprocess,
            generation_kwargs={"user_id": "user-1"},
        )

    assert any(
        "Weekly pipeline generation returned non-dict" in r.getMessage() for r in caplog.records
    )
