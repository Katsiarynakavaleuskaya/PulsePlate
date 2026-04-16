"""Deterministic intervention triggers for planning-flow monetization hints."""

from __future__ import annotations

from app.schemas.intervention import NextBestAction


def build_post_bmi_next_action(*, bmi: float | None) -> NextBestAction | None:
    """Suggest the next step after successful BMI calculation."""
    if bmi is None:
        return None
    return NextBestAction(
        type="unlock_targets",
        recommended_surface="/api/v1/pro/nutrition/targets",
        recommended_tier="PRO",
        trigger_reason="post_bmi",
        why_now="You have baseline body metrics; nutrition targets are the next planning step.",
    )


def build_targets_next_action(*, kcal_daily: int | None) -> NextBestAction | None:
    """Suggest the next step after WHO targets are available."""
    if kcal_daily is None:
        return None
    return NextBestAction(
        type="open_daily_plate",
        recommended_surface="/api/v1/pro/nutrition/daily",
        recommended_tier="PRO",
        trigger_reason="targets_ready",
        why_now="Targets are ready; daily plate view helps apply them meal by meal.",
    )


def build_weekly_plan_next_action(*, daily_menu_count: int | None) -> NextBestAction | None:
    """Suggest the next step after weekly meal plan generation."""
    if not daily_menu_count:
        return None
    return NextBestAction(
        type="upgrade_for_export",
        recommended_surface="/api/v1/export/pdf",
        recommended_tier="VIP",
        trigger_reason="weekly_plan_ready",
        why_now="Your weekly plan is ready; exporting helps execute and share it consistently.",
    )
