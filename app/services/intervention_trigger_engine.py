"""Deterministic intervention triggers for planning-flow monetization hints."""

from __future__ import annotations

import math

from app.schemas.intervention import NextBestAction


def _normalized_finite_number(value: float | int | None) -> float | None:
    """Normalize finite numeric trigger inputs before emitting advisory actions."""
    if value is None or isinstance(value, bool):
        return None
    normalized = float(value)
    if not math.isfinite(normalized):
        return None
    return normalized


def build_post_bmi_next_action(*, bmi: float | None) -> NextBestAction | None:
    """Suggest the next step after successful BMI calculation."""
    normalized_bmi = _normalized_finite_number(bmi)
    if normalized_bmi is None or normalized_bmi <= 0:
        return None
    return NextBestAction(
        type="unlock_targets",
        recommended_surface="pro_targets",
        recommended_tier="PRO",
        trigger_reason="post_bmi",
        why_now="post_bmi_baseline_body_metrics",
    )


def build_targets_next_action(*, kcal_daily: int | None) -> NextBestAction | None:
    """Suggest the next step after WHO targets are available."""
    normalized_kcal_daily = _normalized_finite_number(kcal_daily)
    if normalized_kcal_daily is None or normalized_kcal_daily <= 0:
        return None
    return NextBestAction(
        type="open_daily_plate",
        recommended_surface="pro_daily_plate",
        recommended_tier="PRO",
        trigger_reason="targets_ready",
        why_now="targets_ready_apply_meal_by_meal",
    )


def build_weekly_plan_next_action(*, daily_menu_count: int | None) -> NextBestAction | None:
    """Suggest the next step after weekly meal plan generation."""
    if daily_menu_count is None or isinstance(daily_menu_count, bool) or daily_menu_count <= 0:
        return None
    return NextBestAction(
        type="upgrade_for_export",
        recommended_surface="vip_export",
        recommended_tier="VIP",
        trigger_reason="weekly_plan_ready",
        why_now="weekly_plan_ready_export_and_share",
    )
