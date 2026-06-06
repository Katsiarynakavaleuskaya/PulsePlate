"""Internal User Coaching State v1 schemas.

This module defines a backend-owned sufficient-state snapshot for future
FitChef personalization. It is deliberately internal: no public route, OpenAPI
surface, client contract, prompt injection, or persistence is defined here.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FitChefCoachingScenario = Literal[
    "mascot_insight",
    "weekly_reflection",
    "slip_support",
    "distortion_simulator",
    "identity_loop_mapper",
]
FitChefTransitionState = Literal[
    "cold_start_default",
    "steady_state_default",
    "slip_support_needed",
    "weekly_reflection_due",
    "no_recommendation_available",
]
FitChefTransitionReason = Literal[
    "cold_start_default",
    "default_prior_not_observed_slip",
    "observed_slip_like_behavior",
    "explicit_slip_event",
    "observed_high_risk_adherence",
    "day_close_observed",
    "mascot_fallback_allowed",
    "scenario_unavailable",
    "no_available_scenarios",
    "recent_behavior_capped",
    "recent_behavior_unavailable",
    "adherence_state_invalid_degraded",
]
FitChefTransitionSafetyLabel = Literal[
    "wellness_only",
    "non_diagnostic",
    "service_only",
    "no_raw_user_text",
    "deterministic_policy",
]
RiskBucket = Literal["low", "moderate", "high"]
ConfidenceBucket = Literal["low", "high"]
MARKOV_TRANSITION_SAFETY_LABELS: tuple[FitChefTransitionSafetyLabel, ...] = (
    "wellness_only",
    "non_diagnostic",
    "service_only",
    "no_raw_user_text",
    "deterministic_policy",
)
MARKOV_TRANSITION_BASE_CONFIDENCE_BY_STATE: dict[FitChefTransitionState, float] = {
    "cold_start_default": 0.35,
    "steady_state_default": 0.5,
    "slip_support_needed": 0.78,
    "weekly_reflection_due": 0.66,
    "no_recommendation_available": 0.0,
}


def _markov_transition_confidence_ceiling(
    *,
    transition_state: FitChefTransitionState,
    reasons: tuple[FitChefTransitionReason, ...],
    has_recommendation: bool,
) -> float:
    if not has_recommendation:
        return 0.0

    value = MARKOV_TRANSITION_BASE_CONFIDENCE_BY_STATE[transition_state]
    if "scenario_unavailable" in reasons:
        value -= 0.25
    if "recent_behavior_capped" in reasons:
        value -= 0.15
    if "adherence_state_invalid_degraded" in reasons:
        value -= 0.2
    return round(max(0.0, min(value, 1.0)), 4)


class AdherenceSnapshot(BaseModel):
    """Internal adherence sufficient-state snapshot."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    analyzer_key: Literal["v1:adherence"] = "v1:adherence"
    alpha: float = Field(default=1.0, gt=0.0)
    beta: float = Field(default=1.0, gt=0.0)
    n: int = Field(default=0, ge=0)
    risk_slip: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.35, ge=0.0, le=1.0)
    needs_more_data: bool = True
    source_status: Literal["default", "loaded", "invalid_degraded"] = "default"


class RecentBehaviorSnapshot(BaseModel):
    """Bounded recent behavior metadata with no raw user text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    window_days: int = Field(default=7, ge=1, le=30)
    meal_logged_count_7d: int = Field(default=0, ge=0)
    slip_count_7d: int = Field(default=0, ge=0)
    partial_count_7d: int = Field(default=0, ge=0)
    day_closed_count_7d: int = Field(default=0, ge=0)
    day_close_slip_count_7d: int = Field(default=0, ge=0)
    slip_like_count_7d: int = Field(default=0, ge=0)
    scanned_event_count: int = Field(default=0, ge=0)
    event_scan_limit: int = Field(default=250, ge=1, le=1000)
    events_capped: bool = False
    last_meal_logged_at: datetime | None = None
    last_slip_at: datetime | None = None
    last_partial_at: datetime | None = None
    last_slip_like_at: datetime | None = None
    last_day_closed_at: datetime | None = None
    last_day_closed_day: date | None = None


class ProfileSignalSnapshot(BaseModel):
    """Explicit unknown slots for profile signals not owned by this PR."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    bmi_value: None = None
    bmi_group: Literal["unknown"] = "unknown"
    goal_profile: None = None
    goal_direction: Literal["unknown"] = "unknown"
    nutrition_profile: None = None
    nutrition_goal: Literal["unknown"] = "unknown"
    data_status: Literal["unavailable"] = "unavailable"
    degrade_reasons: tuple[str, ...] = ("profile_source_unavailable",)


class UserCoachingStateV1(BaseModel):
    """Internal immutable coaching state, derived from backend truth only."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: int = Field(..., ge=1)
    state_version: Literal["v1"] = "v1"
    assembled_at: datetime
    profile: ProfileSignalSnapshot = Field(default_factory=ProfileSignalSnapshot)
    adherence: AdherenceSnapshot = Field(default_factory=AdherenceSnapshot)
    recent_behavior: RecentBehaviorSnapshot = Field(default_factory=RecentBehaviorSnapshot)
    available_scenarios: tuple[FitChefCoachingScenario, ...] = ("mascot_insight",)
    coaching_urgency: float = Field(default=0.0, ge=0.0, le=1.0)
    next_recommended_scenario: FitChefCoachingScenario | None = None
    degrade_reasons: tuple[str, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _discard_caller_derived_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        cleaned.pop("coaching_urgency", None)
        cleaned.pop("next_recommended_scenario", None)
        cleaned.pop("degrade_reasons", None)
        return cleaned

    @model_validator(mode="after")
    def _recompute_derived_fields(self) -> "UserCoachingStateV1":
        """Always recompute derived fields so callers cannot inject decisions."""

        behavior = self.recent_behavior
        urgency = min(self.adherence.risk_slip, 1.0) * 0.5
        urgency += min(behavior.slip_like_count_7d / 7.0, 1.0) * 0.35
        if self.adherence.needs_more_data:
            urgency += 0.15
        computed_urgency = round(max(0.0, min(urgency, 1.0)), 4)

        available = tuple(dict.fromkeys(self.available_scenarios))
        priority: list[FitChefCoachingScenario] = []
        if self.adherence.risk_slip > 0.4 or behavior.slip_like_count_7d > 0:
            priority.append("slip_support")
        if behavior.day_closed_count_7d > 0:
            priority.append("weekly_reflection")
        priority.append("mascot_insight")

        scenario: FitChefCoachingScenario | None = None
        for candidate in priority:
            if candidate in available:
                scenario = candidate
                break

        degrade_reasons = list(self.profile.degrade_reasons)
        if self.adherence.needs_more_data:
            degrade_reasons.append("adherence_needs_more_data")
        if behavior.scanned_event_count == 0:
            degrade_reasons.append("recent_behavior_unavailable")
        if behavior.events_capped:
            degrade_reasons.append("recent_behavior_capped")
        if self.adherence.source_status == "invalid_degraded":
            degrade_reasons.append("adherence_state_invalid_degraded")

        object.__setattr__(self, "available_scenarios", available)
        object.__setattr__(self, "coaching_urgency", computed_urgency)
        object.__setattr__(self, "next_recommended_scenario", scenario)
        object.__setattr__(self, "degrade_reasons", tuple(dict.fromkeys(degrade_reasons)))
        return self


class PromptSafeAdherenceContext(BaseModel):
    """Allowlisted adherence context safe for future prompt assembly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    risk_slip: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    needs_more_data: bool
    observation_count: int = Field(..., ge=0)
    risk_bucket: RiskBucket
    confidence_bucket: ConfidenceBucket


class PromptSafeRecentBehaviorContext(BaseModel):
    """Allowlisted recent behavior context without raw events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    window_days: int = Field(..., ge=1, le=30)
    meal_logged_count_7d: int = Field(..., ge=0)
    slip_like_count_7d: int = Field(..., ge=0)
    day_closed_count_7d: int = Field(..., ge=0)
    has_recent_activity: bool
    has_recent_slip_like: bool
    events_capped: bool


class PromptSafeProfileSignalContext(BaseModel):
    """Allowlisted profile context with explicit unknowns only."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    bmi_value: None = None
    bmi_group: Literal["unknown"] = "unknown"
    goal_profile: None = None
    goal_direction: Literal["unknown"] = "unknown"
    nutrition_profile: None = None
    nutrition_goal: Literal["unknown"] = "unknown"
    data_status: Literal["unavailable"] = "unavailable"


class PromptSafeCoachingContext(BaseModel):
    """Static allowlist projection for future prompt-safe use."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state_version: Literal["v1"] = "v1"
    adherence: PromptSafeAdherenceContext
    recent_behavior: PromptSafeRecentBehaviorContext
    profile: PromptSafeProfileSignalContext
    coaching_urgency: float = Field(..., ge=0.0, le=1.0)
    next_recommended_scenario: FitChefCoachingScenario | None
    safety_labels: tuple[
        Literal["wellness_only", "non_diagnostic", "service_only", "no_raw_user_text"], ...
    ] = (
        "wellness_only",
        "non_diagnostic",
        "service_only",
        "no_raw_user_text",
    )


class MarkovScenarioProbability(BaseModel):
    """Ranked fixed-policy transition probability for one eligible scenario."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rank: int = Field(..., ge=1)
    scenario: FitChefCoachingScenario
    probability: float = Field(..., ge=0.0, le=1.0)
    reasons: tuple[FitChefTransitionReason, ...] = ()


class MarkovCoachingTransitionPlanV1(BaseModel):
    """Internal transition plan derived from UserCoachingStateV1 only."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_version: Literal["markov_transition_v1"] = "markov_transition_v1"
    source_state_version: Literal["v1"] = "v1"
    transition_state: FitChefTransitionState
    available_scenarios: tuple[FitChefCoachingScenario, ...]
    ranked_scenarios: tuple[MarkovScenarioProbability, ...] = ()
    recommended_scenario: FitChefCoachingScenario | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: tuple[FitChefTransitionReason, ...] = ()
    safety_labels: tuple[FitChefTransitionSafetyLabel, ...] = MARKOV_TRANSITION_SAFETY_LABELS

    @model_validator(mode="after")
    def _recompute_prompt_safe_invariants(self) -> "MarkovCoachingTransitionPlanV1":
        """Keep caller-supplied plan mutations from changing derived invariants."""

        ranked_scenarios = self.ranked_scenarios
        expected_ranks = tuple(range(1, len(ranked_scenarios) + 1))
        actual_ranks = tuple(ranked.rank for ranked in ranked_scenarios)
        if actual_ranks != expected_ranks:
            raise ValueError("ranked_scenarios ranks must be consecutive from 1")
        if ranked_scenarios:
            unavailable_scenarios = tuple(
                ranked.scenario
                for ranked in ranked_scenarios
                if ranked.scenario not in self.available_scenarios
            )
            if unavailable_scenarios:
                raise ValueError("ranked_scenarios must be limited to available_scenarios")
            total_probability = round(sum(ranked.probability for ranked in ranked_scenarios), 4)
            if total_probability != 1.0:
                raise ValueError("ranked_scenarios probabilities must sum to 1.0")

        recommended = ranked_scenarios[0].scenario if ranked_scenarios else None
        confidence = _markov_transition_confidence_ceiling(
            transition_state=self.transition_state,
            reasons=self.reasons,
            has_recommendation=recommended is not None,
        )
        object.__setattr__(self, "recommended_scenario", recommended)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "safety_labels", MARKOV_TRANSITION_SAFETY_LABELS)
        return self


class PromptSafeMarkovTransitionContext(BaseModel):
    """Prompt-safe transition projection with no identifiers or raw event data."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_version: Literal["markov_transition_v1"] = "markov_transition_v1"
    source_state_version: Literal["v1"] = "v1"
    transition_state: FitChefTransitionState
    recommended_scenario: FitChefCoachingScenario | None
    ranked_scenarios: tuple[MarkovScenarioProbability, ...] = ()
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: tuple[FitChefTransitionReason, ...] = ()
    safety_labels: tuple[FitChefTransitionSafetyLabel, ...] = MARKOV_TRANSITION_SAFETY_LABELS

    @model_validator(mode="after")
    def _recompute_prompt_safe_invariants(self) -> "PromptSafeMarkovTransitionContext":
        ranked_scenarios = self.ranked_scenarios
        recommended = ranked_scenarios[0].scenario if ranked_scenarios else None
        confidence = _markov_transition_confidence_ceiling(
            transition_state=self.transition_state,
            reasons=self.reasons,
            has_recommendation=recommended is not None,
        )
        object.__setattr__(self, "recommended_scenario", recommended)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "safety_labels", MARKOV_TRANSITION_SAFETY_LABELS)
        return self


__all__ = [
    "AdherenceSnapshot",
    "FitChefCoachingScenario",
    "FitChefTransitionReason",
    "FitChefTransitionSafetyLabel",
    "FitChefTransitionState",
    "MARKOV_TRANSITION_BASE_CONFIDENCE_BY_STATE",
    "MARKOV_TRANSITION_SAFETY_LABELS",
    "MarkovCoachingTransitionPlanV1",
    "MarkovScenarioProbability",
    "ProfileSignalSnapshot",
    "PromptSafeAdherenceContext",
    "PromptSafeCoachingContext",
    "PromptSafeMarkovTransitionContext",
    "PromptSafeProfileSignalContext",
    "PromptSafeRecentBehaviorContext",
    "RecentBehaviorSnapshot",
    "UserCoachingStateV1",
]
