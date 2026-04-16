"""Intervention trigger DTOs for planning-flow monetization hints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NextBestActionType = Literal["unlock_targets", "open_daily_plate", "upgrade_for_export"]
RecommendedTier = Literal["FREE", "PRO", "VIP"]


class NextBestAction(BaseModel):
    """Server-authored advisory hint for the next product step."""

    model_config = ConfigDict(extra="forbid")

    type: NextBestActionType = Field(
        ...,
        description="Deterministic trigger action type selected by backend rules.",
    )
    recommended_surface: str = Field(
        ...,
        description="Canonical product surface that should be opened next.",
    )
    recommended_tier: RecommendedTier = Field(
        ...,
        description="Advisory target tier for progression copy (not entitlement truth).",
    )
    trigger_reason: str = Field(
        ...,
        description="Machine-readable reason key for why this hint was selected.",
    )
    why_now: str = Field(
        ...,
        description="Concise backend-authored rationale text for current context.",
    )
