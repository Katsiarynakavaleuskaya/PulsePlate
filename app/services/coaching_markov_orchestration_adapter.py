"""Internal shadow adapter for Markov coaching orchestration v1."""

from __future__ import annotations

from typing import cast

from sqlalchemy.orm import Session

from app.schemas.user_coaching_state import (
    FitChefCoachingScenario,
    FitChefTransitionReason,
    MARKOV_TRANSITION_SAFETY_LABELS,
    MarkovCoachingOrchestrationResultV1,
    MarkovCoachingOrchestrationTraceV1,
    MarkovCoachingTransitionPlanV1,
    MarkovOrchestrationDecisionStatus,
    MarkovOrchestrationDegradeReason,
    PromptSafeMarkovTransitionContext,
    UserCoachingStateV1,
)
from app.services.coaching_state_builder import build_user_coaching_state
from app.services.coaching_transition_planner import (
    build_markov_coaching_transition_plan,
    to_prompt_safe_markov_context,
)

STATE_DEGRADED_REASONS: frozenset[MarkovOrchestrationDegradeReason] = frozenset(
    {
        "recent_behavior_capped",
        "adherence_state_invalid_degraded",
    }
)
PLANNER_DEGRADED_REASONS: frozenset[MarkovOrchestrationDegradeReason] = frozenset(
    {
        "planner_unavailable",
        "scenario_unavailable",
        "no_available_scenarios",
        "recent_behavior_capped",
        "adherence_state_invalid_degraded",
    }
)


def _coerce_orchestration_reasons(
    reasons: tuple[str | FitChefTransitionReason, ...],
) -> tuple[MarkovOrchestrationDegradeReason, ...]:
    allowed = (
        STATE_DEGRADED_REASONS
        | PLANNER_DEGRADED_REASONS
        | frozenset(
            {
                "feature_gate_disabled",
                "no_recommendation_available",
                "planner_unavailable",
            }
        )
    )
    coerced = tuple(
        dict.fromkeys(
            cast(MarkovOrchestrationDegradeReason, reason)
            for reason in reasons
            if reason in allowed
        )
    )
    return coerced


def _state_degrade_reasons(
    state: UserCoachingStateV1,
) -> tuple[MarkovOrchestrationDegradeReason, ...]:
    return _coerce_orchestration_reasons(state.degrade_reasons)


def _planner_degrade_reasons(
    plan: MarkovCoachingTransitionPlanV1 | None,
) -> tuple[MarkovOrchestrationDegradeReason, ...]:
    if plan is None:
        return ()
    reasons: list[str | FitChefTransitionReason] = list(plan.reasons)
    if plan.recommended_scenario is None:
        reasons.append("no_recommendation_available")
    return _coerce_orchestration_reasons(tuple(reasons))


def _decision_status(
    *,
    shadow_enabled: bool,
    plan: MarkovCoachingTransitionPlanV1 | None,
    state_degraded: bool,
    planner_degraded: bool,
) -> MarkovOrchestrationDecisionStatus:
    if not shadow_enabled:
        return "shadow_disabled"
    if plan is None or plan.recommended_scenario is None:
        return "no_recommendation"
    if state_degraded or planner_degraded:
        return "degraded"
    return "ready"


def _build_trace(
    *,
    state: UserCoachingStateV1,
    shadow_enabled: bool,
    plan: MarkovCoachingTransitionPlanV1 | None,
    extra_reasons: tuple[MarkovOrchestrationDegradeReason, ...] = (),
) -> MarkovCoachingOrchestrationTraceV1:
    state_reasons = _state_degrade_reasons(state)
    planner_reasons = _planner_degrade_reasons(plan)
    if not shadow_enabled:
        extra_reasons = ("feature_gate_disabled", *extra_reasons)
    reasons = tuple(dict.fromkeys((*state_reasons, *planner_reasons, *extra_reasons)))
    state_degraded = any(reason in STATE_DEGRADED_REASONS for reason in state_reasons)
    planner_degraded = any(reason in PLANNER_DEGRADED_REASONS for reason in reasons)
    status = _decision_status(
        shadow_enabled=shadow_enabled,
        plan=plan,
        state_degraded=state_degraded,
        planner_degraded=planner_degraded,
    )

    return MarkovCoachingOrchestrationTraceV1(
        planner_version=plan.plan_version if plan is not None else None,
        decision_status=status,
        transition_state=plan.transition_state if plan is not None else None,
        recommended_scenario=plan.recommended_scenario if plan is not None else None,
        confidence=plan.confidence if plan is not None else 0.0,
        ranked_scenario_count=len(plan.ranked_scenarios) if plan is not None else 0,
        available_scenario_count=len(plan.available_scenarios) if plan is not None else 0,
        state_degraded=state_degraded,
        planner_degraded=planner_degraded,
        degrade_reasons=reasons,
        safety_labels=MARKOV_TRANSITION_SAFETY_LABELS,
    )


def build_markov_coaching_orchestration_result(
    user_id: int,
    session: Session,
    analyzer_key: str = "v1:adherence",
    allowed_scenarios: tuple[FitChefCoachingScenario, ...] | None = None,
    shadow_enabled: bool = True,
) -> MarkovCoachingOrchestrationResultV1:
    """Build the internal shadow-only Markov coaching orchestration result."""

    state = build_user_coaching_state(
        user_id=user_id,
        session=session,
        analyzer_key=analyzer_key,
    )
    if not shadow_enabled:
        trace = _build_trace(state=state, shadow_enabled=False, plan=None)
        return MarkovCoachingOrchestrationResultV1(
            coaching_state=state,
            transition_plan=None,
            prompt_safe_context=None,
            decision_trace=trace,
        )

    try:
        plan = build_markov_coaching_transition_plan(
            state,
            allowed_scenarios=allowed_scenarios,
        )
        prompt_safe_context = (
            to_prompt_safe_markov_context(plan) if plan.recommended_scenario is not None else None
        )
        trace = _build_trace(state=state, shadow_enabled=True, plan=plan)
    except ValueError:
        plan = None
        prompt_safe_context = None
        trace = _build_trace(
            state=state,
            shadow_enabled=True,
            plan=None,
            extra_reasons=("planner_unavailable",),
        )

    return MarkovCoachingOrchestrationResultV1(
        coaching_state=state,
        transition_plan=plan,
        prompt_safe_context=prompt_safe_context,
        decision_trace=trace,
    )


def to_prompt_safe_markov_orchestration_context(
    result: MarkovCoachingOrchestrationResultV1,
) -> PromptSafeMarkovTransitionContext | None:
    """Return only the prompt-safe Markov context from an adapter result."""

    safe_result: MarkovCoachingOrchestrationResultV1 = (
        MarkovCoachingOrchestrationResultV1.model_validate(result.model_dump(mode="python"))
    )
    if safe_result.decision_trace.decision_status == "shadow_disabled":
        return None
    prompt_safe_context: PromptSafeMarkovTransitionContext | None = safe_result.prompt_safe_context
    return prompt_safe_context


__all__ = [
    "build_markov_coaching_orchestration_result",
    "to_prompt_safe_markov_orchestration_context",
]
