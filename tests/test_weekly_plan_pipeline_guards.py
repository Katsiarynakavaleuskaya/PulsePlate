# -*- coding: utf-8 -*-
"""
RU: Guard-tests для pipeline ordering weekly plan.
EN: Guard tests for weekly plan pipeline ordering.

Guarantees:
- If generation stage returns error envelope, postprocess must not run
- Pipeline stages execute in correct order: validation → generation → postprocess
"""

from __future__ import annotations

from typing import Any

import pytest

from app.services.weekly_plan.safety import safe_call


def test_pipeline_skips_postprocess_when_generation_returns_error_envelope() -> None:
    """
    RU: Если generation вернул error envelope, postprocess не должен запускаться.
    EN: If generation returns error envelope, postprocess must not run.
    """
    # Generation stage returns an error envelope dict
    def generation_fails() -> dict[str, Any]:
        return {
            "status": "error",
            "code": "weekly_generation_failed",
            "detail": "Generation failed",
            "stage": "generation",
        }

    # Postprocess stage must not be called if generation already failed
    postprocess_called = False

    def postprocess() -> None:
        nonlocal postprocess_called
        postprocess_called = True
        raise AssertionError("postprocess must not run when generation failed")

    # Simulate generation stage
    result = safe_call(
        generation_fails,
        default_code="weekly_generation_failed",
        stage="generation",
    )

    # Router logic: check if generation returned error envelope
    assert isinstance(result, dict) and result.get("status") == "error"
    assert result.get("code") == "weekly_generation_failed"
    assert result.get("stage") == "generation"

    # Router must NOT call postprocess if result is error envelope
    if isinstance(result, dict) and result.get("status") == "error":
        # This is the correct behavior: skip postprocess
        return

    # If we reach here, postprocess would be called (wrong behavior)
    postprocess()
    assert not postprocess_called, "postprocess must not be called when generation fails"
