"""Deterministic Markov-style coaching transition planner v1.

The planner is internal service logic only. It consumes a validated
UserCoachingStateV1 snapshot and returns fixed-policy transition probabilities;
it does not learn, persist, retrieve, or call provider/runtime systems.
"""

from __future__ import annotations

from app.schemas.user_coaching_state import (
    FitChefCoachingScenario,
    FitChefTransitionReason,
    FitChefTransitionState,
    MarkovCoachingTransitionPlanV1,
    MarkovScenarioProbability,
    PromptSafeMarkovTransitionContext,
    UserCoachingStateV1,
)

_SCENARIO_TIEBREAK: tuple[FitChefCoachingScenario, ...] = (
    "mascot_insight",
    "weekly_reflection",
    "slip_support",
    "distortion_simulator",
    "identity_loop_mapper",
)
_SCENARIO_ORDER = {scenario: index for index, scenario in enumerate(_SCENARIO_TIEBREAK)}

_TRANSITION_WEIGHTS: dict[FitChefTransitionState, dict[FitChefCoachingScenario, float]] = {
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

_PRIMARY_SCENARIO_BY_STATE: dict[FitChefTransitionState, FitChefCoachingScenario | None] = {
    "cold_start_default": "mascot_insight",
    "steady_state_default": "mascot_insight",
    "slip_support_needed": "slip_support",
    "weekly_reflection_due": "weekly_reflection",
    "no_recommendation_available": None,
}

_BASE_CONFIDENCE_BY_STATE: dict[FitChefTransitionState, float] = {
    "cold_start_default": 0.35,
    "steady_state_default": 0.5,
    "slip_support_needed": 0.78,
    "weekly_reflection_due": 0.66,
    "no_recommendation_available": 0.0,
}


def _dedupe_scenarios(
    scenarios: tuple[FitChefCoachingScenario, ...],
) -> tuple[FitChefCoachingScenario, ...]:
    return tuple(dict.fromkeys(scenarios))


def _dedupe_reasons(
    reasons: list[FitChefTransitionReason],
) -> tuple[FitChefTransitionReason, ...]:
    return tuple(dict.fromkeys(reasons))


def _revalidated_state(state: UserCoachingStateV1) -> UserCoachingStateV1:
    revalidated: UserCoachingStateV1
    revalidated = UserCoachingStateV1.model_validate(state.model_dump(mode="python"))
    return revalidated


def _available_scenarios(
    state: UserCoachingStateV1,
    allowed_scenarios: tuple[FitChefCoachingScenario, ...] | None,
) -> tuple[FitChefCoachingScenario, ...]:
    state_available = _dedupe_scenarios(state.available_scenarios)
    if allowed_scenarios is None:
        return state_available
    allowed = set(_dedupe_scenarios(allowed_scenarios))
    return tuple(scenario for scenario in state_available if scenario in allowed)


def _has_observed_high_risk_adherence(state: UserCoachingStateV1) -> bool:
    adherence = state.adherence
    return adherence.n > 0 and not adherence.needs_more_data and adherence.risk_slip >= 0.67


def _classify_transition(
    state: UserCoachingStateV1,
) -> tuple[FitChefTransitionState, list[FitChefTransitionReason]]:
    adherence = state.adherence
    behavior = state.recent_behavior
    reasons: list[FitChefTransitionReason] = []

    has_slip_like = behavior.slip_like_count_7d > 0
    has_explicit_slip = behavior.slip_count_7d > 0
    has_observed_high_risk = _has_observed_high_risk_adherence(state)
    if has_slip_like or has_explicit_slip or has_observed_high_risk:
        if has_slip_like:
            reasons.append("observed_slip_like_behavior")
        if has_explicit_slip:
            reasons.append("explicit_slip_event")
        if has_observed_high_risk:
            reasons.append("observed_high_risk_adherence")
        return "slip_support_needed", reasons

    is_cold_start = (
        adherence.needs_more_data and adherence.n == 0 and behavior.scanned_event_count == 0
    )
    if is_cold_start:
        reasons.extend(
            [
                "cold_start_default",
                "default_prior_not_observed_slip",
            ]
        )
        return "cold_start_default", reasons

    if behavior.day_closed_count_7d > 0:
        reasons.append("day_close_observed")
        return "weekly_reflection_due", reasons

    return "steady_state_default", reasons


def _append_context_reasons(
    state: UserCoachingStateV1,
    reasons: list[FitChefTransitionReason],
) -> None:
    behavior = state.recent_behavior
    if behavior.scanned_event_count == 0:
        reasons.append("recent_behavior_unavailable")
    if behavior.events_capped:
        reasons.append("recent_behavior_capped")
    if state.adherence.source_status == "invalid_degraded":
        reasons.append("adherence_state_invalid_degraded")


def _rank_scenarios(
    *,
    transition_state: FitChefTransitionState,
    available_scenarios: tuple[FitChefCoachingScenario, ...],
    reasons: tuple[FitChefTransitionReason, ...],
) -> tuple[MarkovScenarioProbability, ...]:
    weights = _TRANSITION_WEIGHTS[transition_state]
    weighted = [
        (scenario, weights.get(scenario, 0.0))
        for scenario in _SCENARIO_TIEBREAK
        if scenario in available_scenarios and weights.get(scenario, 0.0) > 0.0
    ]
    total = sum(weight for _, weight in weighted)
    if total <= 0.0:
        return ()

    ranked = sorted(
        ((scenario, weight / total) for scenario, weight in weighted),
        key=lambda item: (-item[1], _SCENARIO_ORDER[item[0]]),
    )
    probabilities = [round(probability, 4) for _, probability in ranked]
    probabilities[0] = round(max(0.0, min(probabilities[0] + (1.0 - sum(probabilities)), 1.0)), 4)

    return tuple(
        MarkovScenarioProbability(
            rank=index + 1,
            scenario=scenario,
            probability=probabilities[index],
            reasons=reasons,
        )
        for index, (scenario, _) in enumerate(ranked)
    )


def _confidence(
    *,
    transition_state: FitChefTransitionState,
    state: UserCoachingStateV1,
    has_recommendation: bool,
) -> float:
    if not has_recommendation:
        return 0.0

    value = _BASE_CONFIDENCE_BY_STATE[transition_state]
    if state.recent_behavior.events_capped:
        value -= 0.15
    if state.adherence.source_status == "invalid_degraded":
        value -= 0.2
    return round(max(0.0, min(value, 1.0)), 4)


def build_markov_coaching_transition_plan(
    state: UserCoachingStateV1,
    allowed_scenarios: tuple[FitChefCoachingScenario, ...] | None = None,
) -> MarkovCoachingTransitionPlanV1:
    """Build a fixed-policy transition plan from internal coaching state."""

    safe_state = _revalidated_state(state)
    available = _available_scenarios(safe_state, allowed_scenarios)

    transition_state, reason_list = _classify_transition(safe_state)
    _append_context_reasons(safe_state, reason_list)

    if not available:
        reason_list.append("no_available_scenarios")
        transition_state = "no_recommendation_available"
    else:
        primary = _PRIMARY_SCENARIO_BY_STATE[transition_state]
        if primary is not None and primary not in available:
            reason_list.append("scenario_unavailable")
        if transition_state == "cold_start_default" and "mascot_insight" in available:
            reason_list.append("mascot_fallback_allowed")

    reasons = _dedupe_reasons(reason_list)
    ranked_scenarios = _rank_scenarios(
        transition_state=transition_state,
        available_scenarios=available,
        reasons=reasons,
    )
    recommended_scenario = ranked_scenarios[0].scenario if ranked_scenarios else None

    return MarkovCoachingTransitionPlanV1(
        transition_state=transition_state,
        available_scenarios=available,
        ranked_scenarios=ranked_scenarios,
        recommended_scenario=recommended_scenario,
        confidence=_confidence(
            transition_state=transition_state,
            state=safe_state,
            has_recommendation=recommended_scenario is not None,
        ),
        reasons=reasons,
    )


def to_prompt_safe_markov_context(
    plan: MarkovCoachingTransitionPlanV1,
) -> PromptSafeMarkovTransitionContext:
    """Return the prompt-safe transition subset for future prompt assembly."""

    safe_plan: MarkovCoachingTransitionPlanV1
    safe_plan = MarkovCoachingTransitionPlanV1.model_validate(plan.model_dump(mode="python"))
    return PromptSafeMarkovTransitionContext(
        transition_state=safe_plan.transition_state,
        recommended_scenario=safe_plan.recommended_scenario,
        ranked_scenarios=safe_plan.ranked_scenarios,
        confidence=safe_plan.confidence,
        reasons=safe_plan.reasons,
        safety_labels=safe_plan.safety_labels,
    )


__all__ = [
    "build_markov_coaching_transition_plan",
    "to_prompt_safe_markov_context",
]
