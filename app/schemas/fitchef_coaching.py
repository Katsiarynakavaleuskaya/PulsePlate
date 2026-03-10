"""Public FitChef coaching schemas.

RU: Публичные схемы для FitChef mascot/coaching endpoints.
EN: Public schemas for FitChef mascot/coaching endpoints.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FitChefCoachingRequest(BaseModel):
    """Mascot insight request payload."""

    query: str = Field(..., min_length=1, max_length=500)


class FitChefWeeklyReflectionRequest(BaseModel):
    """Weekly reflection request payload."""

    summary: str = Field(..., min_length=1, max_length=500)
    goal: str | None = Field(default=None, max_length=200)


class FitChefCoachingSourceItem(BaseModel):
    """Public RAG source item for mascot coaching."""

    file: str
    preview: str
    score: float


class FitChefCoachingErrorResponse(BaseModel):
    """Standard JSON detail envelope for FitChef coaching errors."""

    detail: str = Field(..., min_length=1)


class FitChefCoachingResponseBase(BaseModel):
    """Shared public coaching response envelope."""

    message: str = Field(..., min_length=1)
    sources: list[FitChefCoachingSourceItem] = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    warnings: list[str] = Field(...)
    action_items: list[str] = Field(...)
    quota_state: Literal["not_consumed", "consumed"]
    transparency_notice_id: str
    wellness_boundary: str


class FitChefMascotInsightResponse(FitChefCoachingResponseBase):
    """Public mascot insight response envelope."""

    scenario: Literal["mascot_insight"] = Field(...)


class FitChefWeeklyReflectionResponse(FitChefCoachingResponseBase):
    """Public weekly reflection response envelope."""

    scenario: Literal["weekly_reflection"] = Field(...)
