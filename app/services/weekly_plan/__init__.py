# -*- coding: utf-8 -*-
"""
Weekly plan service utilities.

This module provides shared utilities for weekly plan endpoints:
- Safe call wrapper for error handling
- Unified error envelope format
"""

from app.services.weekly_plan.safety import (
    safe_call,
    weekly_plan_error_envelope,
)

__all__ = [
    "safe_call",
    "weekly_plan_error_envelope",
]
