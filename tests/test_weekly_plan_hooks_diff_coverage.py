# -*- coding: utf-8 -*-
"""
RU: Diff-coverage тест для weekly plan hooks interface (no-op).
EN: Diff-coverage test for weekly plan hooks interface (no-op).
"""

from __future__ import annotations

from app.services.weekly_plan.hooks import NULL_WEEKLY_PLAN_HOOK, WeeklyPlanEvent


def test_null_weekly_plan_hook_is_noop() -> None:
    event = WeeklyPlanEvent(
        stage="test",
        code="ok",
        message="noop",
        meta={"k": "v"},
    )
    out_success = NULL_WEEKLY_PLAN_HOOK.on_success(event)
    assert out_success is None

    out_error = NULL_WEEKLY_PLAN_HOOK.on_error(event)
    assert out_error is None
