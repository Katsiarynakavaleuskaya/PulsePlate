"""Public FitChef coaching schemas.

RU: Публичные схемы для FitChef mascot/coaching endpoints.
EN: Public schemas for FitChef mascot/coaching endpoints.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.fitchef import (
    FitChefClarificationV1,
    FitChefWeeklyReflectionResponseState,
)

FitChefSupportNeed = Literal["daily_structure", "weekly_structure"]
FitChefSupportTargetSurface = Literal["pro_daily_plate", "pro_weekly_plan"]


class FitChefSupportHandoffRequest(BaseModel):
    """Closed request contract for deterministic FitChef support routing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    support_need: FitChefSupportNeed


class FitChefSupportHandoffActionV1(BaseModel):
    """Descriptor-only action pointing at one canonical product surface."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    action_type: Literal["handoff_to_product_surface"] = "handoff_to_product_surface"
    target_surface: FitChefSupportTargetSurface


class FitChefSupportHandoffResponse(BaseModel):
    """Frozen non-executing response for the FitChef support handoff."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["fitchef_support_handoff.v1"] = "fitchef_support_handoff.v1"
    scenario: Literal["support_handoff"] = "support_handoff"
    support_need: FitChefSupportNeed
    action: FitChefSupportHandoffActionV1
    user_confirmation_required: Literal[True] = True
    execution_authority: Literal[False] = False
    plan_mutation_authority: Literal[False] = False
    used_llm: Literal[False] = False
    wellness_boundary: Literal["wellness_planning_only"] = "wellness_planning_only"

    @field_validator("user_confirmation_required", mode="before")
    @classmethod
    def require_exact_true(cls, value: object) -> object:
        """Reject numeric truthy values before Literal coercion."""

        if value is not True:
            raise ValueError("user_confirmation_required must be exactly true")
        return value

    @field_validator(
        "execution_authority",
        "plan_mutation_authority",
        "used_llm",
        mode="before",
    )
    @classmethod
    def require_exact_false(cls, value: object) -> object:
        """Reject numeric falsey values before Literal coercion."""

        if value is not False:
            raise ValueError("handoff authority flags must be exactly false")
        return value


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

    @field_validator("situation", "automatic_thought", "emotion", "goal")
    @classmethod
    def validate_not_blank(cls, value: str | None) -> str | None:
        """RU: Отклоняем blank/whitespace значения после trim.
        EN: Reject blank or whitespace-only values after stripping.
        """

        if value is None:
            return None
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("value must not be blank")
        return stripped_value


class FitChefIdentityLoopMapperRequest(BaseModel):
    """Identity-loop mapper request payload."""

    goal: str = Field(..., min_length=1, max_length=200)
    recent_pattern: str = Field(..., min_length=1, max_length=500)
    self_talk: str = Field(..., min_length=1, max_length=500)
    trigger_context: str | None = Field(default=None, max_length=200)

    @field_validator("goal", "recent_pattern", "self_talk", "trigger_context")
    @classmethod
    def validate_not_blank(cls, value: str | None) -> str | None:
        """RU: Отклоняем blank/whitespace значения после trim.
        EN: Reject blank or whitespace-only values after stripping.
        """

        if value is None:
            return None
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("value must not be blank")
        return stripped_value


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


class FitChefVipCoachingErrorResponse(BaseModel):
    """VIP FitChef error envelope preserving frozen VIP aliases."""

    status: Literal["error"] = Field(...)
    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    detail: str = Field(..., min_length=1)
    error: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_frozen_aliases(self) -> "FitChefVipCoachingErrorResponse":
        """Keep frozen VIP aliases stable across generated clients."""

        if self.detail != self.message or self.error != self.code:
            raise ValueError("VIP error aliases must mirror message/code")
        return self


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
    response_state: FitChefWeeklyReflectionResponseState = "generated"
    clarification: FitChefClarificationV1 | None = None


class FitChefSlipSupportResponse(FitChefCoachingResponseBase):
    """Public slip-support response envelope."""

    scenario: Literal["slip_support"] = Field(...)
