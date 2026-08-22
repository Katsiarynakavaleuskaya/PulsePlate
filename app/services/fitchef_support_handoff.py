"""Deterministic FitChef support-handoff selector."""

from __future__ import annotations

from app.schemas.fitchef_coaching import (
    FitChefSupportHandoffActionV1,
    FitChefSupportHandoffResponse,
    FitChefSupportNeed,
    FitChefSupportTargetSurface,
)


def build_fitchef_support_handoff(
    *,
    support_need: FitChefSupportNeed,
) -> FitChefSupportHandoffResponse:
    """Map one closed support need to one descriptor-only product surface."""

    target_surface: FitChefSupportTargetSurface
    if support_need == "daily_structure":
        target_surface = "pro_daily_plate"
    elif support_need == "weekly_structure":
        target_surface = "pro_weekly_plan"
    else:
        raise ValueError("unsupported FitChef support need")

    return FitChefSupportHandoffResponse(
        support_need=support_need,
        action=FitChefSupportHandoffActionV1(target_surface=target_surface),
    )
