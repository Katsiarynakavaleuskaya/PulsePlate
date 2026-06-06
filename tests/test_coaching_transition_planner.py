"""Tests for the internal FitChef coaching transition planner v1."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import NutritionEvent
from app.schemas.user_coaching_state import (
    AdherenceSnapshot,
    MarkovCoachingTransitionPlanV1,
    MarkovScenarioProbability,
    PromptSafeMarkovTransitionContext,
    RecentBehaviorSnapshot,
    UserCoachingStateV1,
)
from app.services import coaching_state_builder as builder_module
from app.services.coaching_state_builder import build_user_coaching_state
from app.services.coaching_transition_planner import (
    build_markov_coaching_transition_plan,
    to_prompt_safe_markov_context,
)
from core.models import AnalyzerStateModel, User

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXED_NOW = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _state(
    *,
    adherence: AdherenceSnapshot | None = None,
    recent_behavior: RecentBehaviorSnapshot | None = None,
    available_scenarios: tuple[str, ...] = (
        "mascot_insight",
        "weekly_reflection",
        "slip_support",
        "distortion_simulator",
        "identity_loop_mapper",
    ),
) -> UserCoachingStateV1:
    return UserCoachingStateV1.model_validate(
        {
            "user_id": 92_001,
            "assembled_at": FIXED_NOW,
            "adherence": adherence or AdherenceSnapshot(),
            "recent_behavior": recent_behavior or RecentBehaviorSnapshot(),
            "available_scenarios": available_scenarios,
        }
    )


def _reset_subjects(session: Session, *user_ids: int) -> None:
    session.execute(delete(NutritionEvent).where(NutritionEvent.subject_id.in_(user_ids)))
    session.execute(delete(AnalyzerStateModel).where(AnalyzerStateModel.user_id.in_(user_ids)))
    session.execute(delete(User).where(User.id.in_(user_ids)))
    for user_id in user_ids:
        session.add(
            User(
                id=user_id,
                email=f"transition-planner-{user_id}@example.test",
                name=f"Transition Planner {user_id}",
            )
        )


def _event(
    *,
    user_id: int,
    day: date,
    event_type: str,
    client_event_id: str,
) -> NutritionEvent:
    source = "day_close" if event_type == "day_closed" else "meal_log"
    return NutritionEvent(
        subject_id=user_id,
        day=day,
        source=source,
        event_type=event_type,
        client_event_id=client_event_id,
        payload={"free_text": "raw transition planner fixture text"},
        created_at=FIXED_NOW.replace(tzinfo=None),
    )


def test_markov_transition_schemas_are_frozen_strict_and_default_safe() -> None:
    probability = MarkovScenarioProbability(
        rank=1,
        scenario="mascot_insight",
        probability=1.0,
        reasons=("cold_start_default", "default_prior_not_observed_slip"),
    )
    plan = MarkovCoachingTransitionPlanV1(
        transition_state="cold_start_default",
        available_scenarios=("mascot_insight",),
        ranked_scenarios=(probability,),
        recommended_scenario="mascot_insight",
        confidence=0.35,
        reasons=("cold_start_default", "default_prior_not_observed_slip"),
    )

    assert plan.plan_version == "markov_transition_v1"
    assert plan.source_state_version == "v1"
    assert plan.safety_labels == (
        "wellness_only",
        "non_diagnostic",
        "service_only",
        "no_raw_user_text",
        "deterministic_policy",
    )

    with pytest.raises(ValidationError):
        MarkovScenarioProbability.model_validate(
            {
                "rank": 1,
                "scenario": "mascot_insight",
                "probability": 1.2,
            }
        )
    with pytest.raises(ValidationError):
        MarkovCoachingTransitionPlanV1.model_validate(
            {
                "transition_state": "cold_start_default",
                "available_scenarios": ("mascot_insight",),
                "confidence": 0.35,
                "extra_field": True,
            }
        )
    with pytest.raises(ValidationError):
        setattr(plan, "confidence", 0.1)


def test_default_prior_does_not_escalate_to_slip_support() -> None:
    state = _state(available_scenarios=("slip_support", "mascot_insight"))

    plan = build_markov_coaching_transition_plan(state)

    assert plan.transition_state == "cold_start_default"
    assert plan.recommended_scenario == "mascot_insight"
    assert plan.ranked_scenarios[0].scenario == "mascot_insight"
    assert "slip_support" not in {ranked.scenario for ranked in plan.ranked_scenarios}
    assert "default_prior_not_observed_slip" in plan.reasons
    assert plan.confidence == pytest.approx(0.35)


def test_cold_start_does_not_fallback_to_mascot_when_not_allowed() -> None:
    state = _state(available_scenarios=("slip_support", "mascot_insight"))

    plan = build_markov_coaching_transition_plan(
        state,
        allowed_scenarios=("slip_support",),
    )

    assert plan.transition_state == "cold_start_default"
    assert plan.available_scenarios == ("slip_support",)
    assert plan.ranked_scenarios == ()
    assert plan.recommended_scenario is None
    assert plan.confidence == 0.0
    assert "scenario_unavailable" in plan.reasons


@pytest.mark.parametrize(
    ("adherence", "behavior", "expected_reason"),
    [
        (
            AdherenceSnapshot(n=0, needs_more_data=True),
            RecentBehaviorSnapshot(slip_like_count_7d=1, scanned_event_count=1),
            "observed_slip_like_behavior",
        ),
        (
            AdherenceSnapshot(n=0, needs_more_data=True),
            RecentBehaviorSnapshot(
                slip_count_7d=1,
                slip_like_count_7d=1,
                scanned_event_count=1,
            ),
            "explicit_slip_event",
        ),
        (
            AdherenceSnapshot(
                alpha=9.0,
                beta=1.0,
                n=10,
                risk_slip=0.8,
                confidence=0.85,
                needs_more_data=False,
            ),
            RecentBehaviorSnapshot(scanned_event_count=1),
            "observed_high_risk_adherence",
        ),
    ],
)
def test_slip_evidence_ranks_slip_support_when_available(
    adherence: AdherenceSnapshot,
    behavior: RecentBehaviorSnapshot,
    expected_reason: str,
) -> None:
    state = _state(adherence=adherence, recent_behavior=behavior)

    plan = build_markov_coaching_transition_plan(state)

    assert plan.transition_state == "slip_support_needed"
    assert plan.recommended_scenario == "slip_support"
    assert plan.ranked_scenarios[0].scenario == "slip_support"
    assert expected_reason in plan.reasons


def test_day_close_ranks_weekly_reflection_without_slip_evidence() -> None:
    state = _state(
        adherence=AdherenceSnapshot(
            alpha=2.0,
            beta=8.0,
            n=10,
            risk_slip=0.2,
            confidence=0.85,
            needs_more_data=False,
        ),
        recent_behavior=RecentBehaviorSnapshot(
            day_closed_count_7d=2,
            scanned_event_count=2,
        ),
    )

    plan = build_markov_coaching_transition_plan(state)

    assert plan.transition_state == "weekly_reflection_due"
    assert plan.recommended_scenario == "weekly_reflection"
    assert plan.ranked_scenarios[0].scenario == "weekly_reflection"
    assert "day_close_observed" in plan.reasons


def test_steady_state_default_is_covered_without_slip_or_day_close() -> None:
    state = _state(
        adherence=AdherenceSnapshot(
            alpha=2.0,
            beta=8.0,
            n=10,
            risk_slip=0.2,
            confidence=0.85,
            needs_more_data=False,
        ),
        recent_behavior=RecentBehaviorSnapshot(
            meal_logged_count_7d=2,
            scanned_event_count=2,
        ),
    )

    plan = build_markov_coaching_transition_plan(state)

    assert plan.transition_state == "steady_state_default"
    assert plan.recommended_scenario == "mascot_insight"
    assert plan.confidence == pytest.approx(0.5)


def test_scenario_filtering_and_empty_available_scenarios_degrade() -> None:
    state = _state(
        recent_behavior=RecentBehaviorSnapshot(slip_count_7d=1, slip_like_count_7d=1),
    )

    full = build_markov_coaching_transition_plan(state)
    filtered = build_markov_coaching_transition_plan(
        state,
        allowed_scenarios=("weekly_reflection", "mascot_insight"),
    )
    assert filtered.recommended_scenario == "weekly_reflection"
    assert "slip_support" not in {ranked.scenario for ranked in filtered.ranked_scenarios}
    assert "scenario_unavailable" in filtered.reasons
    assert filtered.confidence < full.confidence

    empty = build_markov_coaching_transition_plan(state, allowed_scenarios=())
    assert empty.transition_state == "no_recommendation_available"
    assert empty.available_scenarios == ()
    assert empty.ranked_scenarios == ()
    assert empty.recommended_scenario is None
    assert empty.confidence == 0.0
    assert "no_available_scenarios" in empty.reasons


def test_probability_normalization_and_deterministic_tie_break() -> None:
    state = _state(
        adherence=AdherenceSnapshot(n=3, needs_more_data=False, risk_slip=0.2),
        recent_behavior=RecentBehaviorSnapshot(
            day_closed_count_7d=1,
            scanned_event_count=1,
        ),
        available_scenarios=(
            "identity_loop_mapper",
            "distortion_simulator",
            "weekly_reflection",
        ),
    )

    plan = build_markov_coaching_transition_plan(
        state,
        allowed_scenarios=("identity_loop_mapper", "distortion_simulator"),
    )

    assert [ranked.scenario for ranked in plan.ranked_scenarios] == [
        "distortion_simulator",
        "identity_loop_mapper",
    ]
    assert sum(ranked.probability for ranked in plan.ranked_scenarios) == pytest.approx(1.0)
    assert [ranked.rank for ranked in plan.ranked_scenarios] == [1, 2]


def test_caller_injected_derived_state_cannot_steer_transition_plan() -> None:
    state = _state(
        recent_behavior=RecentBehaviorSnapshot(
            slip_count_7d=1,
            slip_like_count_7d=1,
            scanned_event_count=1,
        ),
    )
    tampered_state = state.model_copy(
        update={
            "coaching_urgency": 0.0,
            "next_recommended_scenario": "mascot_insight",
            "degrade_reasons": ("caller_injected",),
        }
    )

    plan = build_markov_coaching_transition_plan(tampered_state)

    assert plan.recommended_scenario == "slip_support"
    assert "caller_injected" not in json.dumps(plan.model_dump(mode="json"))


def test_transition_plan_schema_rejects_impossible_rank_or_probability_shapes() -> None:
    valid_probability = MarkovScenarioProbability(
        rank=1,
        scenario="mascot_insight",
        probability=1.0,
    )
    with pytest.raises(ValidationError, match="probabilities must sum"):
        MarkovCoachingTransitionPlanV1(
            transition_state="steady_state_default",
            available_scenarios=("mascot_insight", "weekly_reflection"),
            ranked_scenarios=(
                MarkovScenarioProbability(
                    rank=1,
                    scenario="mascot_insight",
                    probability=0.6,
                ),
                MarkovScenarioProbability(
                    rank=2,
                    scenario="weekly_reflection",
                    probability=0.3,
                ),
            ),
            confidence=0.5,
        )
    with pytest.raises(ValidationError, match="consecutive"):
        MarkovCoachingTransitionPlanV1(
            transition_state="steady_state_default",
            available_scenarios=("mascot_insight",),
            ranked_scenarios=(valid_probability.model_copy(update={"rank": 2}),),
            confidence=0.5,
        )


def test_transition_plan_schema_rejects_non_policy_ranked_distribution() -> None:
    with pytest.raises(ValidationError, match="fixed transition policy"):
        MarkovCoachingTransitionPlanV1(
            transition_state="slip_support_needed",
            available_scenarios=("mascot_insight", "slip_support"),
            ranked_scenarios=(
                MarkovScenarioProbability(
                    rank=1,
                    scenario="slip_support",
                    probability=1.0,
                    reasons=("observed_slip_like_behavior",),
                ),
            ),
            confidence=0.78,
            reasons=("observed_slip_like_behavior",),
        )

    with pytest.raises(ValidationError, match="fixed transition policy"):
        PromptSafeMarkovTransitionContext(
            transition_state="steady_state_default",
            recommended_scenario="mascot_insight",
            ranked_scenarios=(
                MarkovScenarioProbability(
                    rank=1,
                    scenario="mascot_insight",
                    probability=0.9,
                    reasons=(),
                ),
                MarkovScenarioProbability(
                    rank=2,
                    scenario="weekly_reflection",
                    probability=0.1,
                    reasons=(),
                ),
            ),
            confidence=0.5,
        )

    with pytest.raises(ValidationError, match="fixed transition policy"):
        PromptSafeMarkovTransitionContext(
            transition_state="slip_support_needed",
            recommended_scenario="slip_support",
            ranked_scenarios=(
                MarkovScenarioProbability(
                    rank=1,
                    scenario="slip_support",
                    probability=0.5,
                    reasons=("observed_slip_like_behavior",),
                ),
                MarkovScenarioProbability(
                    rank=2,
                    scenario="mascot_insight",
                    probability=0.5,
                    reasons=("observed_slip_like_behavior",),
                ),
            ),
            confidence=0.78,
            reasons=("observed_slip_like_behavior",),
        )


def test_transition_plan_schema_allows_empty_policy_when_primary_is_unavailable() -> None:
    plan = MarkovCoachingTransitionPlanV1(
        transition_state="cold_start_default",
        available_scenarios=("slip_support",),
        ranked_scenarios=(),
        recommended_scenario="slip_support",
        confidence=0.99,
        reasons=(
            "cold_start_default",
            "default_prior_not_observed_slip",
            "scenario_unavailable",
        ),
    )

    assert plan.ranked_scenarios == ()
    assert plan.recommended_scenario is None
    assert plan.confidence == 0.0


def test_markov_schemas_require_scenario_unavailable_for_fallback_rankings() -> None:
    fallback_probability = MarkovScenarioProbability(
        rank=1,
        scenario="mascot_insight",
        probability=1.0,
        reasons=("observed_slip_like_behavior",),
    )
    with pytest.raises(ValidationError, match="scenario_unavailable"):
        MarkovCoachingTransitionPlanV1(
            transition_state="slip_support_needed",
            available_scenarios=("mascot_insight",),
            ranked_scenarios=(fallback_probability,),
            confidence=0.78,
            reasons=("observed_slip_like_behavior",),
        )

    accepted_plan = MarkovCoachingTransitionPlanV1(
        transition_state="slip_support_needed",
        available_scenarios=("mascot_insight",),
        ranked_scenarios=(
            fallback_probability.model_copy(
                update={
                    "reasons": ("observed_slip_like_behavior", "scenario_unavailable"),
                }
            ),
        ),
        confidence=0.78,
        reasons=("observed_slip_like_behavior", "scenario_unavailable"),
    )
    assert accepted_plan.recommended_scenario == "mascot_insight"
    assert accepted_plan.confidence == pytest.approx(0.53)

    with pytest.raises(ValidationError, match="scenario_unavailable"):
        PromptSafeMarkovTransitionContext(
            transition_state="slip_support_needed",
            recommended_scenario="mascot_insight",
            ranked_scenarios=(fallback_probability,),
            confidence=0.78,
            reasons=("observed_slip_like_behavior",),
        )


def test_transition_plan_schema_requires_no_recommendation_state_for_empty_allowlist() -> None:
    with pytest.raises(ValidationError, match="no available scenarios"):
        MarkovCoachingTransitionPlanV1(
            transition_state="cold_start_default",
            available_scenarios=(),
            ranked_scenarios=(),
            confidence=0.0,
            reasons=("cold_start_default", "default_prior_not_observed_slip"),
        )

    with pytest.raises(ValidationError, match="no available scenarios"):
        MarkovCoachingTransitionPlanV1(
            transition_state="no_recommendation_available",
            available_scenarios=("mascot_insight",),
            ranked_scenarios=(),
            confidence=0.0,
            reasons=("no_available_scenarios",),
        )


def test_markov_transition_schemas_reject_reason_mismatches() -> None:
    reason_cases = (
        ("cold_start_default", "mascot_insight", ("cold_start_default",)),
        (
            "cold_start_default",
            "mascot_insight",
            (
                "cold_start_default",
                "default_prior_not_observed_slip",
                "explicit_slip_event",
            ),
        ),
        ("slip_support_needed", "slip_support", ()),
        (
            "slip_support_needed",
            "slip_support",
            ("explicit_slip_event", "cold_start_default"),
        ),
        ("weekly_reflection_due", "weekly_reflection", ()),
        (
            "weekly_reflection_due",
            "weekly_reflection",
            ("day_close_observed", "explicit_slip_event"),
        ),
        ("steady_state_default", "mascot_insight", ("explicit_slip_event",)),
    )

    for transition_state, scenario, reasons in reason_cases:
        with pytest.raises(ValidationError, match="transition_state"):
            PromptSafeMarkovTransitionContext.model_validate(
                {
                    "transition_state": transition_state,
                    "recommended_scenario": scenario,
                    "ranked_scenarios": (
                        {
                            "rank": 1,
                            "scenario": scenario,
                            "probability": 1.0,
                            "reasons": reasons,
                        },
                    ),
                    "confidence": 0.99,
                    "reasons": reasons,
                }
            )

    with pytest.raises(ValidationError, match="transition_state"):
        PromptSafeMarkovTransitionContext(
            transition_state="no_recommendation_available",
            recommended_scenario=None,
            ranked_scenarios=(),
            confidence=0.0,
        )


def test_transition_plan_schema_rejects_ranked_reason_mismatch() -> None:
    with pytest.raises(ValidationError, match="plan reasons"):
        MarkovCoachingTransitionPlanV1(
            transition_state="cold_start_default",
            available_scenarios=("mascot_insight",),
            ranked_scenarios=(
                MarkovScenarioProbability(
                    rank=1,
                    scenario="mascot_insight",
                    probability=1.0,
                    reasons=("cold_start_default",),
                ),
            ),
            confidence=0.35,
            reasons=("cold_start_default", "default_prior_not_observed_slip"),
        )


def test_transition_plan_schema_rejects_unavailable_ranked_scenarios() -> None:
    unavailable_probability = MarkovScenarioProbability(
        rank=1,
        scenario="slip_support",
        probability=1.0,
    )

    with pytest.raises(ValidationError, match="available_scenarios"):
        MarkovCoachingTransitionPlanV1(
            transition_state="slip_support_needed",
            available_scenarios=("mascot_insight",),
            ranked_scenarios=(unavailable_probability,),
            confidence=0.5,
        )

    with pytest.raises(ValidationError, match="available_scenarios"):
        MarkovCoachingTransitionPlanV1(
            transition_state="no_recommendation_available",
            available_scenarios=(),
            ranked_scenarios=(unavailable_probability,),
            confidence=0.5,
        )


def test_prompt_safe_markov_context_rejects_transition_state_steering() -> None:
    state = _state(available_scenarios=("mascot_insight", "slip_support"))
    plan = build_markov_coaching_transition_plan(state)
    tampered_plan = plan.model_copy(
        update={
            "ranked_scenarios": (
                MarkovScenarioProbability(
                    rank=1,
                    scenario="slip_support",
                    probability=1.0,
                ),
            ),
            "recommended_scenario": "slip_support",
            "confidence": 0.99,
        }
    )

    assert plan.transition_state == "cold_start_default"
    assert plan.recommended_scenario == "mascot_insight"
    with pytest.raises(ValidationError, match="transition_state"):
        to_prompt_safe_markov_context(tampered_plan)

    self_consistent_tampered_plan = plan.model_copy(
        update={
            "transition_state": "slip_support_needed",
            "ranked_scenarios": (
                MarkovScenarioProbability(
                    rank=1,
                    scenario="slip_support",
                    probability=1.0,
                    reasons=plan.reasons,
                ),
            ),
            "recommended_scenario": "slip_support",
            "confidence": 0.99,
        }
    )
    with pytest.raises(ValidationError, match="fixed transition policy|plan reasons"):
        to_prompt_safe_markov_context(self_consistent_tampered_plan)

    with pytest.raises(ValidationError, match="transition_state"):
        PromptSafeMarkovTransitionContext(
            transition_state="cold_start_default",
            recommended_scenario="slip_support",
            ranked_scenarios=(
                MarkovScenarioProbability(
                    rank=1,
                    scenario="slip_support",
                    probability=1.0,
                ),
            ),
            confidence=0.99,
        )


def test_capped_or_degraded_behavior_lowers_confidence_and_adds_reason() -> None:
    base_state = _state(
        recent_behavior=RecentBehaviorSnapshot(
            slip_count_7d=1,
            slip_like_count_7d=1,
            scanned_event_count=1,
        ),
    )
    degraded_state = _state(
        adherence=AdherenceSnapshot(source_status="invalid_degraded"),
        recent_behavior=RecentBehaviorSnapshot(
            slip_count_7d=1,
            slip_like_count_7d=1,
            scanned_event_count=1,
            events_capped=True,
        ),
    )

    base_plan = build_markov_coaching_transition_plan(base_state)
    degraded_plan = build_markov_coaching_transition_plan(degraded_state)

    assert degraded_plan.confidence < base_plan.confidence
    assert "recent_behavior_capped" in degraded_plan.reasons
    assert "adherence_state_invalid_degraded" in degraded_plan.reasons


def test_prompt_safe_markov_context_excludes_sensitive_and_unsafe_fields() -> None:
    state = _state(
        adherence=AdherenceSnapshot(
            alpha=9.0,
            beta=1.0,
            n=10,
            risk_slip=0.8,
            confidence=0.85,
            needs_more_data=False,
        ),
        recent_behavior=RecentBehaviorSnapshot(
            slip_count_7d=1,
            slip_like_count_7d=1,
            scanned_event_count=1,
            last_slip_at=FIXED_NOW,
        ),
    )
    plan = build_markov_coaching_transition_plan(state)

    context = to_prompt_safe_markov_context(plan)

    context_json = json.dumps(context.model_dump(mode="json"), sort_keys=True).lower()
    for forbidden in (
        "user_id",
        "analyzer_key",
        "alpha",
        "beta",
        "last_",
        "email",
        "client_event_id",
        "client-secret",
        "api_key",
        "medical",
        "therapy",
        "diagnosis",
        "treatment",
    ):
        assert forbidden not in context_json
    assert "non_diagnostic" in context_json
    assert context.recommended_scenario == "slip_support"


def test_prompt_safe_markov_context_recovers_tampered_plan_derived_fields() -> None:
    state = _state(
        recent_behavior=RecentBehaviorSnapshot(
            slip_count_7d=1,
            slip_like_count_7d=1,
            scanned_event_count=1,
        ),
    )
    plan = build_markov_coaching_transition_plan(state)
    tampered_plan = plan.model_copy(
        update={
            "recommended_scenario": "mascot_insight",
            "confidence": 0.99,
            "safety_labels": (),
        }
    )

    context = to_prompt_safe_markov_context(tampered_plan)

    assert context.recommended_scenario == "slip_support"
    assert context.safety_labels == plan.safety_labels
    assert context.confidence == plan.confidence


def test_planner_integrates_with_build_user_coaching_state(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = 92_002
    monkeypatch.setattr(builder_module, "_now_utc", lambda: FIXED_NOW)
    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id)
        session.add(
            _event(
                user_id=user_id,
                day=FIXED_NOW.date(),
                event_type="slip",
                client_event_id="planner-slip-1",
            )
        )

    with configure_sqlite_database.session_scope() as session:
        state = build_user_coaching_state(user_id=user_id, session=session)
        plan = build_markov_coaching_transition_plan(state)

    assert state.recent_behavior.slip_like_count_7d == 1
    assert state.available_scenarios == ("mascot_insight",)
    assert plan.recommended_scenario == "mascot_insight"
    assert "observed_slip_like_behavior" in plan.reasons
    assert "scenario_unavailable" in plan.reasons
    assert "raw transition planner fixture text" not in json.dumps(plan.model_dump(mode="json"))


def test_planner_service_has_no_public_runtime_write_or_cache_imports() -> None:
    planner_text = (REPO_ROOT / "app/services/coaching_transition_planner.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "APIRouter",
        "FastAPI",
        "legacy_app",
        "fitchef_runtime",
        "core.rag",
        "from providers",
        "import providers",
        "get_provider",
        "Redis",
        "sqlalchemy",
        "Session",
        "session.",
        "record_event(",
        "upsert_state(",
        "update_if_version_matches(",
        "commit(",
        "flush(",
        "semantic_cache",
    ):
        assert forbidden not in planner_text
