"""Intervention trigger DTOs for planning-flow monetization hints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NextBestActionType = Literal["unlock_targets", "open_daily_plate", "upgrade_for_export"]
RecommendedTier = Literal["FREE", "PRO", "VIP"]
RecommendedSurface = Literal["pro_targets", "pro_daily_plate", "vip_export"]
TriggerReason = Literal["post_bmi", "targets_ready", "weekly_plan_ready"]
WhyNowKey = Literal[
    "post_bmi_baseline_body_metrics",
    "targets_ready_apply_meal_by_meal",
    "weekly_plan_ready_export_and_share",
]


class NextBestAction(BaseModel):
    """Server-authored advisory hint for the next product step."""

    model_config = ConfigDict(extra="forbid")

    type: NextBestActionType = Field(
        ...,
        description="Deterministic trigger action type selected by backend rules.",
    )
    recommended_surface: RecommendedSurface = Field(
        ...,
        description="Canonical backend-owned product surface slug that should be opened next.",
    )
    recommended_tier: RecommendedTier = Field(
        ...,
        description="Advisory target tier for progression copy (not entitlement truth).",
    )
    trigger_reason: TriggerReason = Field(
        ...,
        description="Stable v1 rule key for why this hint was selected.",
    )
    why_now: WhyNowKey = Field(
        ...,
        description="Stable localization key selected by the deterministic v1 rule set.",
    )
