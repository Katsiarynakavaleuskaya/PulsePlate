"""Internal User Coaching State v1 schemas.

This module defines a backend-owned sufficient-state snapshot for future
FitChef personalization. It is deliberately internal: no public route, OpenAPI
surface, client contract, prompt injection, or persistence is defined here.
"""

from __future__ import annotations

from datetime import date, datetime
import re
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

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
MarkovOrchestrationDecisionStatus = Literal[
    "shadow_disabled",
    "no_intervention",
    "no_recommendation",
    "degraded",
    "ready",
]
MarkovOrchestrationDegradeReason = Literal[
    "feature_gate_disabled",
    "no_recommendation_available",
    "planner_unavailable",
    "scenario_unavailable",
    "no_available_scenarios",
    "recent_behavior_capped",
    "adherence_state_invalid_degraded",
]
CoachingGoalStatus = Literal[
    "active",
    "paused",
    "withdrawn",
    "superseded",
    "unavailable",
]
CoachingGoalSource = Literal["user_confirmed", "unavailable"]
CoachingGoalDataStatus = Literal["confirmed", "unavailable", "invalid_degraded"]
NoInterventionReason = Literal[
    "goal_unavailable",
    "goal_invalid_degraded",
    "goal_paused",
    "goal_withdrawn",
    "goal_superseded",
]
_OPAQUE_GOAL_REF_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"
_OPAQUE_GOAL_REF_RE = re.compile(_OPAQUE_GOAL_REF_PATTERN, flags=re.ASCII)
OpaqueGoalRef = Annotated[
    str,
    StringConstraints(
        strict=True,
        pattern=_OPAQUE_GOAL_REF_PATTERN,
    ),
]


def _is_valid_opaque_goal_ref(value: object) -> bool:
    return type(value) is str and _OPAQUE_GOAL_REF_RE.fullmatch(value) is not None


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
MARKOV_TRANSITION_PRIMARY_SCENARIO_BY_STATE: dict[
    FitChefTransitionState,
    FitChefCoachingScenario | None,
] = {
    "cold_start_default": "mascot_insight",
    "steady_state_default": "mascot_insight",
    "slip_support_needed": "slip_support",
    "weekly_reflection_due": "weekly_reflection",
    "no_recommendation_available": None,
}
MARKOV_TRANSITION_SCENARIO_TIEBREAK: tuple[FitChefCoachingScenario, ...] = (
    "mascot_insight",
    "weekly_reflection",
    "slip_support",
    "distortion_simulator",
    "identity_loop_mapper",
)
_MARKOV_TRANSITION_SCENARIO_ORDER = {
    scenario: index for index, scenario in enumerate(MARKOV_TRANSITION_SCENARIO_TIEBREAK)
}
MARKOV_TRANSITION_SCENARIO_WEIGHTS_BY_STATE: dict[
    FitChefTransitionState,
    dict[FitChefCoachingScenario, float],
] = {
    "cold_start_default": {
        "mascot_insight": 1.0,
    },
    "steady_state_default": {
        "mascot_insight": 0.55,
        "weekly_reflection": 0.2,
        "distortion_simulator": 0.1,
        "identity_loop_mapper": 0.1,
        "slip_support": 0.05,
    },
    "slip_support_needed": {
        "slip_support": 0.72,
        "weekly_reflection": 0.12,
        "mascot_insight": 0.1,
        "distortion_simulator": 0.03,
        "identity_loop_mapper": 0.03,
    },
    "weekly_reflection_due": {
        "weekly_reflection": 0.65,
        "mascot_insight": 0.2,
        "distortion_simulator": 0.05,
        "identity_loop_mapper": 0.05,
        "slip_support": 0.05,
    },
    "no_recommendation_available": {},
}
MARKOV_TRANSITION_SCENARIOS_BY_STATE: dict[
    FitChefTransitionState,
    tuple[FitChefCoachingScenario, ...],
] = {
    transition_state: tuple(weights)
    for transition_state, weights in MARKOV_TRANSITION_SCENARIO_WEIGHTS_BY_STATE.items()
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


class CoachingGoalAuthoritySnapshotV1(BaseModel):
    """Versioned goal-authority lifecycle metadata without goal content."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_version: Literal["coaching_goal_authority_v1"] = "coaching_goal_authority_v1"
    status: CoachingGoalStatus = "unavailable"
    source: CoachingGoalSource = "unavailable"
    data_status: CoachingGoalDataStatus = "unavailable"
    goal_ref: OpaqueGoalRef | None = None
    goal_version_ref: OpaqueGoalRef | None = None
    supersedes_ref: OpaqueGoalRef | None = None
    superseded_by_ref: OpaqueGoalRef | None = None
    correction_ref: OpaqueGoalRef | None = None

    @field_validator(
        "goal_ref",
        "goal_version_ref",
        "supersedes_ref",
        "superseded_by_ref",
        "correction_ref",
        mode="before",
    )
    @classmethod
    def _require_builtin_ref_string(cls, value: object) -> object:
        if value is not None and not _is_valid_opaque_goal_ref(value):
            raise ValueError("goal authority refs must match the canonical opaque grammar")
        return value

    @model_validator(mode="after")
    def _validate_lifecycle(self) -> "CoachingGoalAuthoritySnapshotV1":
        refs = (
            self.goal_ref,
            self.goal_version_ref,
            self.supersedes_ref,
            self.superseded_by_ref,
            self.correction_ref,
        )

        if self.status == "unavailable":
            if self.source != "unavailable":
                raise ValueError("unavailable goal must use unavailable source")
            if self.data_status not in {"unavailable", "invalid_degraded"}:
                raise ValueError("unavailable goal must use unavailable or invalid_degraded data")
            if any(ref is not None for ref in refs):
                raise ValueError("unavailable goal must not include refs")
        else:
            if self.source != "user_confirmed" or self.data_status != "confirmed":
                raise ValueError("known goal lifecycle requires user_confirmed confirmed data")
            if self.goal_ref is None or self.goal_version_ref is None:
                raise ValueError("known goal lifecycle requires goal and version refs")
            if self.status == "superseded":
                if self.superseded_by_ref is None:
                    raise ValueError("superseded goal requires a successor ref")
            elif self.superseded_by_ref is not None:
                raise ValueError("non-superseded goal must not include a successor ref")

        if self.goal_version_ref is not None:
            if self.supersedes_ref == self.goal_version_ref:
                raise ValueError("goal version must not supersede itself")
            if self.superseded_by_ref == self.goal_version_ref:
                raise ValueError("goal version must not be superseded by itself")
        if (
            self.supersedes_ref is not None
            and self.superseded_by_ref is not None
            and self.supersedes_ref == self.superseded_by_ref
        ):
            raise ValueError("predecessor and successor refs must differ")
        return self

    def _has_valid_lifecycle(self) -> bool:
        try:
            CoachingGoalAuthoritySnapshotV1.model_validate(
                {
                    "snapshot_version": self.snapshot_version,
                    "status": self.status,
                    "source": self.source,
                    "data_status": self.data_status,
                    "goal_ref": self.goal_ref,
                    "goal_version_ref": self.goal_version_ref,
                    "supersedes_ref": self.supersedes_ref,
                    "superseded_by_ref": self.superseded_by_ref,
                    "correction_ref": self.correction_ref,
                }
            )
        except ValidationError:
            return False
        return True

    @property
    def has_active_authority(self) -> bool:
        """Return authority only for the one validated active lifecycle state."""

        return (
            self._has_valid_lifecycle()
            and self.status == "active"
            and self.source == "user_confirmed"
            and self.data_status == "confirmed"
            and _is_valid_opaque_goal_ref(self.goal_ref)
            and _is_valid_opaque_goal_ref(self.goal_version_ref)
        )

    @property
    def no_intervention_reason(self) -> NoInterventionReason | None:
        """Return the exact abstention reason for a validated non-active goal."""

        if not self._has_valid_lifecycle():
            raise ValueError("goal snapshot has no valid no_intervention mapping")
        if self.status == "active":
            return None
        if self.status == "unavailable":
            if self.data_status == "invalid_degraded":
                return "goal_invalid_degraded"
            return "goal_unavailable"
        if self.status == "paused":
            return "goal_paused"
        if self.status == "withdrawn":
            return "goal_withdrawn"
        if self.status == "superseded":
            return "goal_superseded"
        raise ValueError("goal snapshot has no valid no_intervention mapping")


class UserCoachingStateV1(BaseModel):
    """Internal immutable coaching state, derived from backend truth only."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: int = Field(..., ge=1)
    state_version: Literal["v1"] = "v1"
    assembled_at: datetime
    profile: ProfileSignalSnapshot = Field(default_factory=ProfileSignalSnapshot)
    goal: CoachingGoalAuthoritySnapshotV1 = Field(default_factory=CoachingGoalAuthoritySnapshotV1)
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
        if self.goal.has_active_authority:
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


class PromptSafeGoalAuthorityContext(BaseModel):
    """Allowlisted goal lifecycle categories without identifiers or content."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: CoachingGoalStatus
    source: CoachingGoalSource
    data_status: CoachingGoalDataStatus
    has_active_authority: bool = False

    @model_validator(mode="before")
    @classmethod
    def _discard_caller_derived_authority(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        cleaned.pop("has_active_authority", None)
        return cleaned

    @model_validator(mode="after")
    def _recompute_authority(self) -> "PromptSafeGoalAuthorityContext":
        if self.status == "unavailable":
            if self.source != "unavailable":
                raise ValueError("unavailable goal context must use unavailable source")
            if self.data_status not in {"unavailable", "invalid_degraded"}:
                raise ValueError("unavailable goal context has invalid data status")
        elif self.source != "user_confirmed" or self.data_status != "confirmed":
            raise ValueError("known goal context requires user_confirmed confirmed data")

        has_active_authority = (
            self.status == "active"
            and self.source == "user_confirmed"
            and self.data_status == "confirmed"
        )
        object.__setattr__(self, "has_active_authority", has_active_authority)
        return self


class PromptSafeCoachingContext(BaseModel):
    """Static allowlist projection for future prompt-safe use."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state_version: Literal["v1"] = "v1"
    adherence: PromptSafeAdherenceContext
    recent_behavior: PromptSafeRecentBehaviorContext
    profile: PromptSafeProfileSignalContext
    goal: PromptSafeGoalAuthorityContext
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


def _expected_markov_ranked_policy(
    *,
    transition_state: FitChefTransitionState,
    available_scenarios: tuple[FitChefCoachingScenario, ...],
) -> tuple[tuple[FitChefCoachingScenario, float], ...]:
    weights = MARKOV_TRANSITION_SCENARIO_WEIGHTS_BY_STATE[transition_state]
    weighted = [
        (scenario, weights.get(scenario, 0.0))
        for scenario in MARKOV_TRANSITION_SCENARIO_TIEBREAK
        if scenario in available_scenarios and weights.get(scenario, 0.0) > 0.0
    ]
    total = sum(weight for _, weight in weighted)
    if total <= 0.0:
        return ()

    ranked = sorted(
        ((scenario, weight / total) for scenario, weight in weighted),
        key=lambda item: (-item[1], _MARKOV_TRANSITION_SCENARIO_ORDER[item[0]]),
    )
    probabilities = [round(probability, 4) for _, probability in ranked]
    probabilities[0] = round(max(0.0, min(probabilities[0] + (1.0 - sum(probabilities)), 1.0)), 4)
    return tuple((scenario, probabilities[index]) for index, (scenario, _) in enumerate(ranked))


def _expected_markov_ranked_subset_policy(
    *,
    transition_state: FitChefTransitionState,
    ranked_scenarios: tuple[MarkovScenarioProbability, ...],
) -> tuple[tuple[FitChefCoachingScenario, float], ...]:
    scenarios = tuple(ranked.scenario for ranked in ranked_scenarios)
    return _expected_markov_ranked_policy(
        transition_state=transition_state,
        available_scenarios=scenarios,
    )


def _validate_markov_transition_reasons(
    *,
    transition_state: FitChefTransitionState,
    reasons: tuple[FitChefTransitionReason, ...],
) -> None:
    reason_set = set(reasons)
    slip_reasons = {
        "observed_slip_like_behavior",
        "explicit_slip_event",
        "observed_high_risk_adherence",
    }
    cold_reasons = {"cold_start_default", "default_prior_not_observed_slip"}

    if transition_state == "cold_start_default":
        if not cold_reasons.issubset(reason_set):
            raise ValueError("reasons must match transition_state")
        if reason_set & (slip_reasons | {"day_close_observed", "no_available_scenarios"}):
            raise ValueError("reasons must match transition_state")
    elif transition_state == "slip_support_needed":
        if not (reason_set & slip_reasons):
            raise ValueError("reasons must match transition_state")
        if reason_set & (cold_reasons | {"day_close_observed", "no_available_scenarios"}):
            raise ValueError("reasons must match transition_state")
    elif transition_state == "weekly_reflection_due":
        if "day_close_observed" not in reason_set:
            raise ValueError("reasons must match transition_state")
        if reason_set & (slip_reasons | cold_reasons | {"no_available_scenarios"}):
            raise ValueError("reasons must match transition_state")
    elif transition_state == "steady_state_default":
        if reason_set & (
            slip_reasons | cold_reasons | {"day_close_observed", "no_available_scenarios"}
        ):
            raise ValueError("reasons must match transition_state")
    elif "no_available_scenarios" not in reason_set:
        raise ValueError("reasons must match transition_state")


def _validate_markov_ranked_scenarios(
    *,
    transition_state: FitChefTransitionState,
    ranked_scenarios: tuple[MarkovScenarioProbability, ...],
    available_scenarios: tuple[FitChefCoachingScenario, ...] | None = None,
    reasons: tuple[FitChefTransitionReason, ...],
) -> None:
    expected_ranks = tuple(range(1, len(ranked_scenarios) + 1))
    actual_ranks = tuple(ranked.rank for ranked in ranked_scenarios)
    if actual_ranks != expected_ranks:
        raise ValueError("ranked_scenarios ranks must be consecutive from 1")

    if available_scenarios is not None and not available_scenarios:
        if transition_state != "no_recommendation_available":
            raise ValueError("transition_state must match no available scenarios")
    if (
        available_scenarios is not None
        and available_scenarios
        and transition_state == "no_recommendation_available"
    ):
        raise ValueError("transition_state must match no available scenarios")

    if ranked_scenarios and available_scenarios is not None:
        unavailable_scenarios = tuple(
            ranked.scenario
            for ranked in ranked_scenarios
            if ranked.scenario not in available_scenarios
        )
        if unavailable_scenarios:
            raise ValueError("ranked_scenarios must be limited to available_scenarios")

    if ranked_scenarios:
        impossible_scenarios = tuple(
            ranked.scenario
            for ranked in ranked_scenarios
            if ranked.scenario not in MARKOV_TRANSITION_SCENARIOS_BY_STATE[transition_state]
        )
        if impossible_scenarios:
            raise ValueError("ranked_scenarios must be valid for transition_state")
        total_probability = round(sum(ranked.probability for ranked in ranked_scenarios), 4)
        if total_probability != 1.0:
            raise ValueError("ranked_scenarios probabilities must sum to 1.0")

    if available_scenarios is not None:
        expected_policy = _expected_markov_ranked_policy(
            transition_state=transition_state,
            available_scenarios=available_scenarios,
        )
        actual_policy = tuple((ranked.scenario, ranked.probability) for ranked in ranked_scenarios)
        if actual_policy != expected_policy:
            raise ValueError("ranked_scenarios must match fixed transition policy")
    else:
        expected_policy = _expected_markov_ranked_subset_policy(
            transition_state=transition_state,
            ranked_scenarios=ranked_scenarios,
        )
        actual_policy = tuple((ranked.scenario, ranked.probability) for ranked in ranked_scenarios)
        if actual_policy != expected_policy:
            raise ValueError("ranked_scenarios must match fixed transition policy")
    _validate_markov_transition_reasons(transition_state=transition_state, reasons=reasons)
    primary_scenario = MARKOV_TRANSITION_PRIMARY_SCENARIO_BY_STATE[transition_state]
    primary_unavailable = False
    if primary_scenario is not None and available_scenarios is not None:
        primary_unavailable = (
            bool(available_scenarios) and primary_scenario not in available_scenarios
        )
    elif primary_scenario is not None and ranked_scenarios:
        primary_unavailable = ranked_scenarios[0].scenario != primary_scenario
    if primary_unavailable and "scenario_unavailable" not in reasons:
        raise ValueError("reasons must include scenario_unavailable for fallback scenarios")
    if not ranked_scenarios:
        return
    if any(ranked.reasons != reasons for ranked in ranked_scenarios):
        raise ValueError("ranked_scenarios reasons must match plan reasons")


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
        _validate_markov_ranked_scenarios(
            transition_state=self.transition_state,
            ranked_scenarios=ranked_scenarios,
            available_scenarios=self.available_scenarios,
            reasons=self.reasons,
        )
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
        _validate_markov_ranked_scenarios(
            transition_state=self.transition_state,
            ranked_scenarios=ranked_scenarios,
            reasons=self.reasons,
        )
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


class MarkovCoachingOrchestrationTraceV1(BaseModel):
    """Non-PII shadow decision trace for the internal Markov adapter."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_version: Literal["markov_orchestration_trace_v1"] = "markov_orchestration_trace_v1"
    adapter_version: Literal["markov_orchestration_adapter_v1"] = "markov_orchestration_adapter_v1"
    source_state_version: Literal["v1"] = "v1"
    planner_version: Literal["markov_transition_v1"] | None = None
    decision_status: MarkovOrchestrationDecisionStatus
    transition_state: FitChefTransitionState | None = None
    recommended_scenario: FitChefCoachingScenario | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ranked_scenario_count: int = Field(default=0, ge=0)
    available_scenario_count: int = Field(default=0, ge=0)
    state_degraded: bool = False
    planner_degraded: bool = False
    degrade_reasons: tuple[MarkovOrchestrationDegradeReason, ...] = ()
    no_intervention_reason: NoInterventionReason | None = None
    safety_labels: tuple[FitChefTransitionSafetyLabel, ...] = MARKOV_TRANSITION_SAFETY_LABELS

    @model_validator(mode="after")
    def _recompute_trace_safety_labels(self) -> "MarkovCoachingOrchestrationTraceV1":
        degrade_reasons = tuple(dict.fromkeys(self.degrade_reasons))
        object.__setattr__(self, "safety_labels", MARKOV_TRANSITION_SAFETY_LABELS)
        object.__setattr__(self, "degrade_reasons", degrade_reasons)

        if self.decision_status == "no_intervention":
            if self.no_intervention_reason is None:
                raise ValueError("no_intervention trace requires an exact reason")
            if self.planner_version is not None or self.transition_state is not None:
                raise ValueError("no_intervention trace must not include planner state")
            if self.recommended_scenario is not None or self.confidence != 0.0:
                raise ValueError("no_intervention trace must not include a recommendation")
            if self.ranked_scenario_count != 0 or self.available_scenario_count != 0:
                raise ValueError("no_intervention trace must use zero unevaluated counts")
            if self.state_degraded or self.planner_degraded or degrade_reasons:
                raise ValueError("no_intervention trace must not be degraded")
        elif self.no_intervention_reason is not None:
            raise ValueError("no_intervention_reason is exclusive to no_intervention")
        return self


class MarkovCoachingOrchestrationResultV1(BaseModel):
    """Internal shadow-only adapter result.

    The full state and plan remain internal explainability artifacts. Only
    prompt_safe_context is eligible for future prompt-facing call sites.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    result_version: Literal["markov_orchestration_result_v1"] = "markov_orchestration_result_v1"
    coaching_state: UserCoachingStateV1
    transition_plan: MarkovCoachingTransitionPlanV1 | None = None
    prompt_safe_context: PromptSafeMarkovTransitionContext | None = None
    decision_trace: MarkovCoachingOrchestrationTraceV1

    @model_validator(mode="after")
    def _validate_shadow_boundaries(self) -> "MarkovCoachingOrchestrationResultV1":
        trace = self.decision_trace
        has_active_authority = self.coaching_state.goal.has_active_authority
        if trace.decision_status == "shadow_disabled":
            if self.transition_plan is not None or self.prompt_safe_context is not None:
                raise ValueError("shadow_disabled result must not include plan or context")
            if "feature_gate_disabled" not in trace.degrade_reasons:
                raise ValueError("shadow_disabled trace must include feature gate reason")
        if trace.decision_status == "no_intervention":
            expected_reason = self.coaching_state.goal.no_intervention_reason
            if has_active_authority or expected_reason is None:
                raise ValueError("no_intervention result requires a non-active goal")
            if trace.no_intervention_reason != expected_reason:
                raise ValueError("no_intervention reason must match coaching goal")
            if self.transition_plan is not None or self.prompt_safe_context is not None:
                raise ValueError("no_intervention result must not include plan or context")
        if trace.decision_status in {"ready", "degraded", "no_recommendation"}:
            if not has_active_authority:
                raise ValueError("planner decisions require active goal authority")
        if trace.decision_status in {"ready", "degraded"}:
            if self.transition_plan is None or self.prompt_safe_context is None:
                raise ValueError("ready or degraded result requires plan and context")
        if trace.decision_status == "ready":
            if trace.state_degraded or trace.planner_degraded or trace.degrade_reasons:
                raise ValueError("ready result must not be degraded")
        if trace.decision_status == "degraded":
            if not (trace.state_degraded or trace.planner_degraded or trace.degrade_reasons):
                raise ValueError("degraded result must include degraded evidence")
        if trace.decision_status == "no_recommendation":
            if self.prompt_safe_context is not None:
                raise ValueError("no_recommendation result must not include prompt_safe_context")
            if (
                self.transition_plan is not None
                and self.transition_plan.recommended_scenario is not None
            ):
                raise ValueError("no_recommendation result must not include recommendation")
        if self.prompt_safe_context is not None and self.transition_plan is None:
            raise ValueError("prompt_safe_context requires transition_plan")
        if self.transition_plan is not None:
            plan = self.transition_plan
            if trace.planner_version != plan.plan_version:
                raise ValueError("trace planner_version must match transition_plan")
            if trace.transition_state != plan.transition_state:
                raise ValueError("trace transition_state must match transition_plan")
            if trace.recommended_scenario != plan.recommended_scenario:
                raise ValueError("trace recommended_scenario must match transition_plan")
            if trace.confidence != plan.confidence:
                raise ValueError("trace confidence must match transition_plan")
            if trace.ranked_scenario_count != len(plan.ranked_scenarios):
                raise ValueError("trace ranked count must match transition_plan")
            if trace.available_scenario_count != len(plan.available_scenarios):
                raise ValueError("trace available count must match transition_plan")
            if self.prompt_safe_context is not None:
                context = self.prompt_safe_context
                if context.plan_version != plan.plan_version:
                    raise ValueError("prompt_safe_context plan_version must match transition_plan")
                if context.source_state_version != plan.source_state_version:
                    raise ValueError(
                        "prompt_safe_context source_state_version must match transition_plan"
                    )
                if context.transition_state != plan.transition_state:
                    raise ValueError(
                        "prompt_safe_context transition_state must match transition_plan"
                    )
                if context.recommended_scenario != plan.recommended_scenario:
                    raise ValueError(
                        "prompt_safe_context recommended_scenario must match transition_plan"
                    )
                if context.ranked_scenarios != plan.ranked_scenarios:
                    raise ValueError(
                        "prompt_safe_context ranked_scenarios must match transition_plan"
                    )
                if context.confidence != plan.confidence:
                    raise ValueError("prompt_safe_context confidence must match transition_plan")
                if context.reasons != plan.reasons:
                    raise ValueError("prompt_safe_context reasons must match transition_plan")
                if context.safety_labels != plan.safety_labels:
                    raise ValueError("prompt_safe_context safety_labels must match transition_plan")
        return self


__all__ = [
    "AdherenceSnapshot",
    "CoachingGoalAuthoritySnapshotV1",
    "CoachingGoalDataStatus",
    "CoachingGoalSource",
    "CoachingGoalStatus",
    "FitChefCoachingScenario",
    "FitChefTransitionReason",
    "FitChefTransitionSafetyLabel",
    "FitChefTransitionState",
    "MARKOV_TRANSITION_BASE_CONFIDENCE_BY_STATE",
    "MARKOV_TRANSITION_SAFETY_LABELS",
    "MarkovCoachingOrchestrationResultV1",
    "MarkovCoachingOrchestrationTraceV1",
    "MarkovCoachingTransitionPlanV1",
    "MarkovOrchestrationDecisionStatus",
    "MarkovOrchestrationDegradeReason",
    "MarkovScenarioProbability",
    "NoInterventionReason",
    "OpaqueGoalRef",
    "ProfileSignalSnapshot",
    "PromptSafeAdherenceContext",
    "PromptSafeCoachingContext",
    "PromptSafeGoalAuthorityContext",
    "PromptSafeMarkovTransitionContext",
    "PromptSafeProfileSignalContext",
    "PromptSafeRecentBehaviorContext",
    "RecentBehaviorSnapshot",
    "UserCoachingStateV1",
]
