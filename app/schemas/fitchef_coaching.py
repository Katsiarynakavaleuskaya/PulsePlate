"""Public FitChef coaching schemas.

RU: Публичные схемы для FitChef mascot/coaching endpoints.
EN: Public schemas for FitChef mascot/coaching endpoints.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FitChefCoachingRequest(BaseModel):
    """Mascot insight request payload."""

    query: str = Field(..., min_length=1, max_length=500)


class FitChefWeeklyReflectionRequest(BaseModel):
    """Weekly reflection request payload."""

    summary: str = Field(..., min_length=1, max_length=500)
    goal: str | None = Field(default=None, max_length=200)


class FitChefDistortionSimulatorRequest(BaseModel):
    """Distortion-simulator request payload."""

    situation: str = Field(..., min_length=1, max_length=500)
    automatic_thought: str = Field(..., min_length=1, max_length=500)
    emotion: str = Field(..., min_length=1, max_length=120)
    goal: str | None = Field(default=None, max_length=200)


class FitChefIdentityLoopMapperRequest(BaseModel):
    """Identity-loop mapper request payload."""

    goal: str = Field(..., min_length=1, max_length=200)
    recent_pattern: str = Field(..., min_length=1, max_length=500)
    self_talk: str = Field(..., min_length=1, max_length=500)
    trigger_context: str | None = Field(default=None, max_length=200)


class FitChefSlipSupportRequest(BaseModel):
    """Slip-support request payload."""

    event_text: str = Field(..., min_length=1, max_length=500)
    goal: str | None = Field(default=None, max_length=200)

    @field_validator("event_text")
    @classmethod
    def validate_event_text_not_blank(cls, value: str) -> str:
        """RU: Отклоняем пустой после trim текст события.
        EN: Reject whitespace-only slip-support event text early.
        """

        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("event_text must not be blank")
        return stripped_value


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


class FitChefDistortionSimulatorResponse(BaseModel):
    """Public distortion-simulator response envelope."""

    scenario: Literal["distortion_simulator"] = Field(...)
    distortion_labels: list[str] = Field(...)
    why_it_matches: str = Field(..., min_length=1)
    evidence_for: list[str] = Field(...)
    evidence_against: list[str] = Field(...)
    balanced_reframe: str = Field(..., min_length=1)
    next_small_action: str = Field(..., min_length=1)
    sources: list[FitChefCoachingSourceItem] = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    warnings: list[str] = Field(...)
    quota_state: Literal["not_consumed", "consumed"]
    transparency_notice_id: str
    wellness_boundary: str


class FitChefIdentityLoopView(BaseModel):
    """Public identity-loop block."""

    belief: str = Field(..., min_length=1)
    behavior: str = Field(..., min_length=1)
    short_term_reward: str = Field(..., min_length=1)
    long_term_cost: str = Field(..., min_length=1)


class FitChefIdentityLoopMapperResponse(BaseModel):
    """Public identity-loop mapper response envelope."""

    scenario: Literal["identity_loop_mapper"] = Field(...)
    identity_loop: FitChefIdentityLoopView = Field(...)
    identity_shift_statement: str = Field(..., min_length=1)
    replacement_action: str = Field(..., min_length=1)
    repair_if_slip: str = Field(..., min_length=1)
    sources: list[FitChefCoachingSourceItem] = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    warnings: list[str] = Field(...)
    quota_state: Literal["not_consumed", "consumed"]
    transparency_notice_id: str
    wellness_boundary: str


class FitChefMascotInsightResponse(FitChefCoachingResponseBase):
    """Public mascot insight response envelope."""

    scenario: Literal["mascot_insight"] = Field(...)


class FitChefWeeklyReflectionResponse(FitChefCoachingResponseBase):
    """Public weekly reflection response envelope."""

    scenario: Literal["weekly_reflection"] = Field(...)


class FitChefSlipSupportResponse(FitChefCoachingResponseBase):
    """Public slip-support response envelope."""

    scenario: Literal["slip_support"] = Field(...)
