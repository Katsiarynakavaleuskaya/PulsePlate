"""Creative research pilot schemas.

RU: Схемы для internal-only creative research pilot.
EN: Schemas for the internal-only creative research pilot.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.fitchef import FitChefExecutionMode, FitChefQuotaState


class CreativeResearchPilotRequest(BaseModel):
    """Request payload for the internal creative research pilot."""

    prompt_seed: str = Field(..., min_length=1, max_length=500)
    reference_corpus: list[str] = Field(default_factory=list, max_length=6)
    candidate_count: int = Field(default=4, ge=1, le=6)

    @field_validator("prompt_seed")
    @classmethod
    def _validate_prompt_seed_not_blank(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("prompt_seed must not be blank")
        return stripped_value

    @field_validator("reference_corpus")
    @classmethod
    def _validate_reference_corpus_items(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if len(normalized) != len(value):
            raise ValueError("reference_corpus items must not be blank")
        if any(len(item) > 500 for item in normalized):
            raise ValueError("reference_corpus items must be <= 500 chars")
        return normalized


class CreativeResearchPilotInput(BaseModel):
    """Internal task input for the creative research pilot runtime."""

    prompt_seed: str = Field(..., min_length=1, max_length=500)
    reference_corpus: list[str] = Field(default_factory=list, max_length=6)
    candidate_count: int = Field(..., ge=1, le=6)
    api_key: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)


class CreativeResearchPilotTaskEnvelope(BaseModel):
    """Internal task envelope for the creative research pilot."""

    agent_id: Literal["creative-research-pilot"] = "creative-research-pilot"
    task_class: Literal["creative_research"] = "creative_research"
    mode: FitChefExecutionMode
    tool_budget: int = Field(default=1, ge=1, le=1)
    input: CreativeResearchPilotInput


class CreativeResearchPilotScorecard(BaseModel):
    """Per-candidate deterministic scorecard."""

    originality: int = Field(..., ge=0, le=5)
    flexibility: int = Field(..., ge=0, le=5)
    mechanism_specificity: int = Field(..., ge=0, le=5)
    groundedness: int = Field(..., ge=0, le=5)
    falsifiability: int = Field(..., ge=0, le=5)
    wellness_safety: int = Field(..., ge=0, le=5)
    hallucination_risk: int = Field(..., ge=0, le=5)


class CreativeResearchPilotCandidate(BaseModel):
    """Public candidate envelope returned by the pilot route."""

    candidate_id: str
    claim: str
    mechanism: str
    evidence_needed: str
    falsifier: str
    confidence: Literal["low", "medium", "high", "unknown"]
    known_risks: list[str]
    wellness_boundary: str
    output_class: Literal[
        "mechanistic_hypothesis",
        "experimental_proposal",
        "anomaly_explanation_candidate",
        "creative_ideation",
    ]
    reference_overlap: float = Field(..., ge=0.0, le=1.0)
    peer_overlap: float = Field(..., ge=0.0, le=1.0)
    negative_controls_triggered: list[str]
    scorecard: CreativeResearchPilotScorecard
    promotion_decision: Literal["promote", "defer", "discard"]
    presentation_label: str | None = None


class CreativeResearchPilotSummary(BaseModel):
    """Aggregate counts returned by the pilot."""

    candidate_count: int = Field(..., ge=0)
    promote: int = Field(..., ge=0)
    defer: int = Field(..., ge=0)
    discard: int = Field(..., ge=0)


class CreativeResearchPilotBudgetState(BaseModel):
    """Bounded pilot budget state returned to internal callers."""

    max_branches: int = Field(..., ge=1)
    max_total_llm_calls: int = Field(..., ge=1)
    max_recursive_depth: int = Field(..., ge=0)
    max_retrieval_hops: int = Field(..., ge=0)
    llm_calls_used: int = Field(..., ge=0)
    retrieval_hops_used: int = Field(..., ge=0)


class CreativeResearchPilotErrorResponse(BaseModel):
    """Stable JSON detail envelope for pilot errors."""

    detail: str = Field(..., min_length=1)


class CreativeResearchPilotResult(BaseModel):
    """Internal/public response contract for the hidden pilot endpoint."""

    schema_version: Literal["1.0"] = "1.0"
    bundle_id: str
    task_class: Literal["creative_research"] = "creative_research"
    phase: Literal["verification"] = "verification"
    mode: FitChefExecutionMode
    prompt_seed: str
    quota_state: FitChefQuotaState
    transparency_notice_id: str
    wellness_boundary: str
    budget_state: CreativeResearchPilotBudgetState
    summary: CreativeResearchPilotSummary
    candidates: list[CreativeResearchPilotCandidate]
