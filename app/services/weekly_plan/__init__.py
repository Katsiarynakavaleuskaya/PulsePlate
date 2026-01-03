# -*- coding: utf-8 -*-
"""
Weekly plan service utilities.

This module provides shared utilities for weekly plan endpoints:
- Safe call wrapper for error handling
- Unified error envelope format
- Hooks interface for pipeline events (no-op by default)
"""

from __future__ import annotations

from app.services.weekly_plan.hooks import (
    NULL_WEEKLY_PLAN_HOOK,
    NullWeeklyPlanHook,
    WeeklyPlanEvent,
    WeeklyPlanHook,
)
from app.services.weekly_plan.pipeline import run_weekly_pipeline_guarded
from app.services.weekly_plan.safety import safe_call, weekly_plan_error_envelope

__all__ = [
    "safe_call",
    "weekly_plan_error_envelope",
    "run_weekly_pipeline_guarded",
    "WeeklyPlanEvent",
    "WeeklyPlanHook",
    "NullWeeklyPlanHook",
    "NULL_WEEKLY_PLAN_HOOK",
]
