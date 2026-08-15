"""Tests for the internal FitChef Markov orchestration adapter v1."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import NutritionEvent
from app.schemas.user_coaching_state import (
    AdherenceSnapshot,
    CoachingGoalAuthoritySnapshotV1,
    CoachingGoalDataStatus,
    CoachingGoalStatus,
    FitChefCoachingScenario,
    MarkovCoachingOrchestrationResultV1,
    MarkovCoachingOrchestrationTraceV1,
    NoInterventionReason,
    PromptSafeMarkovTransitionContext,
    RecentBehaviorSnapshot,
    UserCoachingStateV1,
)
from app.services import coaching_markov_orchestration_adapter as adapter_module
from app.services import coaching_state_builder as builder_module
from app.services.coaching_markov_orchestration_adapter import (
    build_markov_coaching_orchestration_result,
    to_prompt_safe_markov_orchestration_context,
)
from app.services.coaching_transition_planner import build_markov_coaching_transition_plan
from core.bayes.adherence_model import AdherenceState
from core.bayes.adherence_service import DEFAULT_ANALYZER_KEY
from core.models import AnalyzerStateModel, User

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXED_NOW = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
ALL_SCENARIOS: tuple[FitChefCoachingScenario, ...] = (
    "mascot_insight",
    "weekly_reflection",
    "slip_support",
    "distortion_simulator",
    "identity_loop_mapper",
)


def _goal(
    status: CoachingGoalStatus = "active",
    *,
    data_status: CoachingGoalDataStatus | None = None,
) -> CoachingGoalAuthoritySnapshotV1:
    if status == "unavailable":
        return CoachingGoalAuthoritySnapshotV1(data_status=data_status or "unavailable")
    return CoachingGoalAuthoritySnapshotV1(
        status=status,
        source="user_confirmed",
        data_status="confirmed",
        goal_ref="goal:adapter-fixture",
        goal_version_ref="goal-version:1",
        superseded_by_ref="goal-version:2" if status == "superseded" else None,
    )


def _reset_subjects(session: Session, *user_ids: int) -> None:
    session.execute(delete(NutritionEvent).where(NutritionEvent.subject_id.in_(user_ids)))
    session.execute(delete(AnalyzerStateModel).where(AnalyzerStateModel.user_id.in_(user_ids)))
    session.execute(delete(User).where(User.id.in_(user_ids)))
    for user_id in user_ids:
        session.add(
            User(
                id=user_id,
                email=f"markov-adapter-{user_id}@example.test",
                name=f"Markov Adapter {user_id}",
            )
        )


def _seed_adherence_state(
    session: Session,
    *,
    user_id: int,
    alpha: float,
    beta: float,
    n: int,
) -> None:
    payload = AdherenceState(
        alpha=alpha,
        beta=beta,
        n=n,
        last_event_at="2026-06-07T10:00:00+00:00",
    ).to_payload()
    session.add(
        AnalyzerStateModel(
            user_id=user_id,
            analyzer_key=DEFAULT_ANALYZER_KEY,
            state_schema_version=1,
            state_version=1,
            payload=payload,
        )
    )


def _event(
    *,
    user_id: int,
    day: date,
    event_type: str,
    client_event_id: str,
    payload: dict[str, object] | None = None,
) -> NutritionEvent:
    return NutritionEvent(
        subject_id=user_id,
        day=day,
        source="day_close" if event_type == "day_closed" else "meal_log",
        event_type=event_type,
        client_event_id=client_event_id,
        payload=payload or {"free_text": "raw adapter fixture text"},
        created_at=FIXED_NOW.replace(tzinfo=None),
    )


def _event_count(session: Session, user_id: int) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(NutritionEvent)
            .where(NutritionEvent.subject_id == user_id)
        )
        or 0
    )


def _analyzer_count(session: Session, user_id: int) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(AnalyzerStateModel)
            .where(AnalyzerStateModel.user_id == user_id)
        )
        or 0
    )


def _state(
    *,
    user_id: int = 93_100,
    adherence: AdherenceSnapshot | None = None,
    recent_behavior: RecentBehaviorSnapshot | None = None,
    goal: CoachingGoalAuthoritySnapshotV1 | None = None,
    available_scenarios: tuple[FitChefCoachingScenario, ...] = ALL_SCENARIOS,
) -> UserCoachingStateV1:
    return UserCoachingStateV1(
        user_id=user_id,
        assembled_at=FIXED_NOW,
        goal=goal if goal is not None else _goal(),
        adherence=adherence or AdherenceSnapshot(),
        recent_behavior=recent_behavior or RecentBehaviorSnapshot(),
        available_scenarios=available_scenarios,
    )


def _install_active_goal_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    original_builder = adapter_module.build_user_coaching_state

    def _build_with_active_goal(
        *,
        user_id: int,
        session: Session,
        analyzer_key: str = DEFAULT_ANALYZER_KEY,
    ) -> UserCoachingStateV1:
        state = original_builder(
            user_id=user_id,
            session=session,
            analyzer_key=analyzer_key,
        )
        payload = state.model_dump(mode="python")
        payload["goal"] = _goal()
        return UserCoachingStateV1.model_validate(payload)

    monkeypatch.setattr(adapter_module, "build_user_coaching_state", _build_with_active_goal)


def _install_static_state_builder(
    monkeypatch: pytest.MonkeyPatch,
    state: UserCoachingStateV1,
) -> None:
    def _build_static_state(
        user_id: int,
        session: Session,
        analyzer_key: str = DEFAULT_ANALYZER_KEY,
    ) -> UserCoachingStateV1:
        del user_id, session, analyzer_key
        return state

    monkeypatch.setattr(adapter_module, "build_user_coaching_state", _build_static_state)


def _safe_json(result: MarkovCoachingOrchestrationResultV1) -> str:
    context = to_prompt_safe_markov_orchestration_context(result)
    return json.dumps(
        {
            "context": context.model_dump(mode="json") if context is not None else None,
            "trace": result.decision_trace.model_dump(mode="json"),
        },
        sort_keys=True,
    )


def test_orchestration_schemas_are_frozen_strict_and_validate_trace_plan_consistency() -> None:
    trace = MarkovCoachingOrchestrationTraceV1(
        decision_status="shadow_disabled",
        degrade_reasons=("feature_gate_disabled",),
        safety_labels=(),
    )

    assert trace.safety_labels == (
        "wellness_only",
        "non_diagnostic",
        "service_only",
        "no_raw_user_text",
        "deterministic_policy",
    )

    with pytest.raises(ValidationError):
        MarkovCoachingOrchestrationTraceV1.model_validate(
            {
                "decision_status": "ready",
                "extra_field": True,
            }
        )
    with pytest.raises(ValidationError):
        setattr(trace, "decision_status", "ready")

    state = _state()
    with pytest.raises(ValidationError, match="shadow_disabled"):
        MarkovCoachingOrchestrationResultV1(
            coaching_state=state,
            transition_plan=None,
            prompt_safe_context=None,
            decision_trace=MarkovCoachingOrchestrationTraceV1(decision_status="shadow_disabled"),
        )


def test_default_cold_start_chain_returns_deliberate_no_intervention(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = 93_001
    monkeypatch.setattr(builder_module, "_now_utc", lambda: FIXED_NOW)
    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id)

    with configure_sqlite_database.session_scope() as session:
        before_events = _event_count(session, user_id)
        before_analyzers = _analyzer_count(session, user_id)
        result = build_markov_coaching_orchestration_result(user_id=user_id, session=session)
        repeated = build_markov_coaching_orchestration_result(user_id=user_id, session=session)
        after_events = _event_count(session, user_id)
        after_analyzers = _analyzer_count(session, user_id)
        assert not session.new
        assert not session.dirty
        assert not session.deleted

    assert result.coaching_state.user_id == user_id
    assert before_events == after_events == 0
    assert before_analyzers == after_analyzers == 0
    assert result.coaching_state.goal == CoachingGoalAuthoritySnapshotV1()
    assert result.transition_plan is None
    assert result.prompt_safe_context is None
    assert result.decision_trace.decision_status == "no_intervention"
    assert result.decision_trace.no_intervention_reason == "goal_unavailable"
    assert result.decision_trace.planner_version is None
    assert result.decision_trace.transition_state is None
    assert result.decision_trace.recommended_scenario is None
    assert result.decision_trace.confidence == 0.0
    assert result.decision_trace.ranked_scenario_count == 0
    assert result.decision_trace.available_scenario_count == 0
    assert result.decision_trace.state_degraded is False
    assert result.decision_trace.planner_degraded is False
    assert result.decision_trace.degrade_reasons == ()
    assert result.decision_trace == repeated.decision_trace

    safe_json = _safe_json(result)
    for forbidden in ("user_id", str(user_id), "assembled_at", "last_", "alpha", "beta"):
        assert forbidden not in safe_json


def test_active_cold_start_preserves_existing_ready_policy(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state(user_id=93_009)
    _install_static_state_builder(monkeypatch, state)

    with configure_sqlite_database.session_scope() as session:
        result = build_markov_coaching_orchestration_result(
            user_id=state.user_id,
            session=session,
        )

    expected_plan = build_markov_coaching_transition_plan(state)
    assert result.transition_plan is not None
    assert result.transition_plan == expected_plan
    assert result.transition_plan.transition_state == "cold_start_default"
    assert result.transition_plan.recommended_scenario == "mascot_insight"
    assert result.prompt_safe_context is not None
    assert result.prompt_safe_context.recommended_scenario == "mascot_insight"
    assert result.decision_trace.decision_status == "ready"
    assert result.decision_trace.no_intervention_reason is None
    assert result.decision_trace.degrade_reasons == ()
    assert "goal" not in result.prompt_safe_context.model_dump(mode="json")
    assert "goal:adapter-fixture" not in _safe_json(result)


def test_slip_and_day_close_rows_flow_through_builder_planner_and_adapter(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slip_user_id = 93_002
    day_close_user_id = 93_003
    monkeypatch.setattr(builder_module, "_now_utc", lambda: FIXED_NOW)
    _install_active_goal_builder(monkeypatch)

    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, slip_user_id, day_close_user_id)
        _seed_adherence_state(session, user_id=slip_user_id, alpha=1.0, beta=9.0, n=10)
        session.add(
            _event(
                user_id=slip_user_id,
                day=FIXED_NOW.date(),
                event_type="slip",
                client_event_id="slip-raw-sentinel",
                payload={
                    "free_text": "raw slip adapter text",
                    "email": "ada@example.com",
                    "api" + "_key": "synthetic-key-like-marker-a",
                },
            )
        )
        session.add(
            _event(
                user_id=day_close_user_id,
                day=FIXED_NOW.date(),
                event_type="day_closed",
                client_event_id="day-close-raw-sentinel",
                payload={"adherence_score": 1.0, "free_text": "raw day close text"},
            )
        )

    with configure_sqlite_database.session_scope() as session:
        before_events = _event_count(session, slip_user_id)
        before_analyzers = _analyzer_count(session, slip_user_id)
        before_analyzer = session.scalar(
            select(AnalyzerStateModel).where(
                AnalyzerStateModel.user_id == slip_user_id,
                AnalyzerStateModel.analyzer_key == DEFAULT_ANALYZER_KEY,
            )
        )
        assert before_analyzer is not None
        before_analyzer_snapshot = (
            before_analyzer.state_version,
            dict(before_analyzer.payload),
        )
        slip_result = build_markov_coaching_orchestration_result(
            user_id=slip_user_id,
            session=session,
        )
        day_close_result = build_markov_coaching_orchestration_result(
            user_id=day_close_user_id,
            session=session,
        )
        after_events = _event_count(session, slip_user_id)
        after_analyzers = _analyzer_count(session, slip_user_id)
        after_analyzer = session.scalar(
            select(AnalyzerStateModel).where(
                AnalyzerStateModel.user_id == slip_user_id,
                AnalyzerStateModel.analyzer_key == DEFAULT_ANALYZER_KEY,
            )
        )
        assert after_analyzer is not None
        after_analyzer_snapshot = (
            after_analyzer.state_version,
            dict(after_analyzer.payload),
        )
        assert not session.new
        assert not session.dirty
        assert not session.deleted

    assert before_events == after_events == 1
    assert before_analyzers == after_analyzers == 1
    assert before_analyzer_snapshot == after_analyzer_snapshot
    assert slip_result.transition_plan is not None
    assert slip_result.transition_plan.transition_state == "slip_support_needed"
    assert slip_result.transition_plan.recommended_scenario == "mascot_insight"
    assert slip_result.decision_trace.decision_status == "degraded"
    assert "scenario_unavailable" in slip_result.decision_trace.degrade_reasons

    assert day_close_result.transition_plan is not None
    assert day_close_result.transition_plan.transition_state == "weekly_reflection_due"
    assert day_close_result.transition_plan.recommended_scenario == "mascot_insight"
    assert day_close_result.decision_trace.decision_status == "degraded"

    safe_json = (_safe_json(slip_result) + _safe_json(day_close_result)).lower()
    for forbidden in (
        "raw slip adapter text",
        "raw day close text",
        "ada@example.com",
        "synthetic-key-like-marker-a",
        "slip-raw-sentinel",
        "day-close-raw-sentinel",
    ):
        assert forbidden not in safe_json


def test_shadow_disabled_prevents_planner_and_prompt_safe_projection(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = 93_004
    monkeypatch.setattr(builder_module, "_now_utc", lambda: FIXED_NOW)

    def _unexpected_planner_call(*args: object, **kwargs: object) -> None:
        raise AssertionError("planner should not run when shadow is disabled")

    monkeypatch.setattr(
        adapter_module,
        "build_markov_coaching_transition_plan",
        _unexpected_planner_call,
    )
    monkeypatch.setattr(
        adapter_module,
        "to_prompt_safe_markov_context",
        _unexpected_planner_call,
    )
    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id)
    with configure_sqlite_database.session_scope() as session:
        result = build_markov_coaching_orchestration_result(
            user_id=user_id,
            session=session,
            shadow_enabled=False,
        )

    assert result.transition_plan is None
    assert result.prompt_safe_context is None
    assert to_prompt_safe_markov_orchestration_context(result) is None
    assert result.decision_trace.decision_status == "shadow_disabled"
    assert result.decision_trace.no_intervention_reason is None
    assert result.decision_trace.degrade_reasons == ("feature_gate_disabled",)


@pytest.mark.parametrize(
    ("goal", "expected_reason"),
    [
        (_goal("unavailable"), "goal_unavailable"),
        (
            _goal("unavailable", data_status="invalid_degraded"),
            "goal_invalid_degraded",
        ),
        (_goal("paused"), "goal_paused"),
        (_goal("withdrawn"), "goal_withdrawn"),
        (_goal("superseded"), "goal_superseded"),
    ],
)
def test_non_active_goal_prevents_planner_and_projection_calls(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
    goal: CoachingGoalAuthoritySnapshotV1,
    expected_reason: NoInterventionReason,
) -> None:
    state = _state(goal=goal)
    calls = {"planner": 0, "projection": 0}

    def _unexpected_planner(*args: object, **kwargs: object) -> None:
        calls["planner"] += 1
        raise AssertionError("planner must not run without active goal authority")

    def _unexpected_projection(*args: object, **kwargs: object) -> None:
        calls["projection"] += 1
        raise AssertionError("projection must not run without active goal authority")

    _install_static_state_builder(monkeypatch, state)
    monkeypatch.setattr(
        adapter_module,
        "build_markov_coaching_transition_plan",
        _unexpected_planner,
    )
    monkeypatch.setattr(
        adapter_module,
        "to_prompt_safe_markov_context",
        _unexpected_projection,
    )

    with configure_sqlite_database.session_scope() as session:
        result = build_markov_coaching_orchestration_result(
            user_id=state.user_id,
            session=session,
        )

    assert calls == {"planner": 0, "projection": 0}
    assert result.transition_plan is None
    assert result.prompt_safe_context is None
    assert to_prompt_safe_markov_orchestration_context(result) is None
    assert result.decision_trace.decision_status == "no_intervention"
    assert result.decision_trace.no_intervention_reason == expected_reason
    assert result.decision_trace.planner_version is None
    assert result.decision_trace.transition_state is None
    assert result.decision_trace.recommended_scenario is None
    assert result.decision_trace.confidence == 0.0
    assert result.decision_trace.ranked_scenario_count == 0
    assert result.decision_trace.available_scenario_count == 0
    assert result.decision_trace.state_degraded is False
    assert result.decision_trace.planner_degraded is False
    assert result.decision_trace.degrade_reasons == ()


@pytest.mark.parametrize(
    "invalid_update",
    [
        {"goal_ref": []},
        {"superseded_by_ref": "goal-version:2"},
        {"supersedes_ref": "goal-version:1"},
        {"correction_ref": "raw goal prose"},
        {"snapshot_version": "coaching_goal_authority_v2"},
    ],
)
def test_forged_active_goal_never_calls_planner_or_projection(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
    invalid_update: dict[str, object],
) -> None:
    state = _state()
    forged_goal = state.goal.model_copy(update=invalid_update)
    forged_state = state.model_copy(update={"goal": forged_goal})
    calls = {"planner": 0, "projection": 0}

    def _unexpected_planner(*args: object, **kwargs: object) -> None:
        calls["planner"] += 1
        raise AssertionError("planner must not run with invalid goal refs")

    def _unexpected_projection(*args: object, **kwargs: object) -> None:
        calls["projection"] += 1
        raise AssertionError("projection must not run with invalid goal refs")

    _install_static_state_builder(monkeypatch, forged_state)
    monkeypatch.setattr(
        adapter_module,
        "build_markov_coaching_transition_plan",
        _unexpected_planner,
    )
    monkeypatch.setattr(
        adapter_module,
        "to_prompt_safe_markov_context",
        _unexpected_projection,
    )

    with configure_sqlite_database.session_scope() as session:
        with pytest.raises(ValueError, match="no valid no_intervention mapping"):
            build_markov_coaching_orchestration_result(
                user_id=forged_state.user_id,
                session=session,
            )

    assert calls == {"planner": 0, "projection": 0}


@pytest.mark.parametrize(
    "trace_payload",
    [
        {"decision_status": "no_intervention"},
        {
            "decision_status": "no_intervention",
            "no_intervention_reason": "goal_unavailable",
            "planner_version": "markov_transition_v1",
        },
        {
            "decision_status": "no_intervention",
            "no_intervention_reason": "goal_unavailable",
            "transition_state": "cold_start_default",
        },
        {
            "decision_status": "no_intervention",
            "no_intervention_reason": "goal_unavailable",
            "recommended_scenario": "mascot_insight",
        },
        {
            "decision_status": "no_intervention",
            "no_intervention_reason": "goal_unavailable",
            "confidence": 0.1,
        },
        {
            "decision_status": "no_intervention",
            "no_intervention_reason": "goal_unavailable",
            "ranked_scenario_count": 1,
        },
        {
            "decision_status": "no_intervention",
            "no_intervention_reason": "goal_unavailable",
            "available_scenario_count": 1,
        },
        {
            "decision_status": "no_intervention",
            "no_intervention_reason": "goal_unavailable",
            "state_degraded": True,
        },
        {
            "decision_status": "no_intervention",
            "no_intervention_reason": "goal_unavailable",
            "planner_degraded": True,
        },
        {
            "decision_status": "no_intervention",
            "no_intervention_reason": "goal_unavailable",
            "degrade_reasons": ("planner_unavailable",),
        },
        {
            "decision_status": "shadow_disabled",
            "no_intervention_reason": "goal_unavailable",
        },
    ],
)
def test_trace_rejects_forged_no_intervention_shapes(
    trace_payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        MarkovCoachingOrchestrationTraceV1.model_validate(trace_payload)


def test_result_cross_binds_no_intervention_reason_and_goal_authority() -> None:
    unavailable_state = _state(goal=_goal("unavailable"))
    valid_trace = MarkovCoachingOrchestrationTraceV1(
        decision_status="no_intervention",
        no_intervention_reason="goal_unavailable",
    )
    valid_result = MarkovCoachingOrchestrationResultV1(
        coaching_state=unavailable_state,
        decision_trace=valid_trace,
    )
    assert valid_result.decision_trace.no_intervention_reason == "goal_unavailable"

    with pytest.raises(ValidationError, match="reason must match coaching goal"):
        MarkovCoachingOrchestrationResultV1(
            coaching_state=unavailable_state,
            decision_trace=MarkovCoachingOrchestrationTraceV1(
                decision_status="no_intervention",
                no_intervention_reason="goal_paused",
            ),
        )
    with pytest.raises(ValidationError, match="requires a non-active goal"):
        MarkovCoachingOrchestrationResultV1(
            coaching_state=_state(goal=_goal()),
            decision_trace=valid_trace,
        )
    with pytest.raises(ValidationError, match="planner decisions require active"):
        MarkovCoachingOrchestrationResultV1(
            coaching_state=unavailable_state,
            decision_trace=MarkovCoachingOrchestrationTraceV1(decision_status="no_recommendation"),
        )


def test_empty_allowed_scenarios_returns_no_recommendation_status(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = 93_005
    monkeypatch.setattr(builder_module, "_now_utc", lambda: FIXED_NOW)
    _install_active_goal_builder(monkeypatch)
    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id)

    with configure_sqlite_database.session_scope() as session:
        result = build_markov_coaching_orchestration_result(
            user_id=user_id,
            session=session,
            allowed_scenarios=(),
        )

    assert result.transition_plan is not None
    assert result.transition_plan.transition_state == "no_recommendation_available"
    assert result.transition_plan.recommended_scenario is None
    assert result.prompt_safe_context is None
    assert result.decision_trace.decision_status == "no_recommendation"
    assert result.decision_trace.degrade_reasons == (
        "no_available_scenarios",
        "no_recommendation_available",
    )


def test_ready_status_uses_existing_prompt_safe_markov_projection(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_state = _state(
        adherence=AdherenceSnapshot(
            alpha=8.0,
            beta=2.0,
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
    _install_static_state_builder(monkeypatch, ready_state)

    with configure_sqlite_database.session_scope() as session:
        result = build_markov_coaching_orchestration_result(
            user_id=ready_state.user_id,
            session=session,
        )

    assert result.transition_plan is not None
    assert result.prompt_safe_context is not None
    assert result.decision_trace.decision_status == "ready"
    assert result.decision_trace.transition_state == "steady_state_default"
    assert result.decision_trace.degrade_reasons == ()
    assert to_prompt_safe_markov_orchestration_context(result) == result.prompt_safe_context

    tampered_result = result.model_copy(
        update={
            "decision_trace": result.decision_trace.model_copy(update={"safety_labels": ()}),
            "prompt_safe_context": result.prompt_safe_context.model_copy(
                update={
                    "recommended_scenario": "slip_support",
                    "confidence": 0.99,
                    "safety_labels": (),
                }
            ),
        }
    )
    recovered = to_prompt_safe_markov_orchestration_context(tampered_result)
    assert recovered == result.prompt_safe_context

    incompatible_context = PromptSafeMarkovTransitionContext(
        transition_state="cold_start_default",
        recommended_scenario="mascot_insight",
        ranked_scenarios=(
            result.transition_plan.ranked_scenarios[0].model_copy(
                update={
                    "probability": 1.0,
                    "reasons": (
                        "cold_start_default",
                        "default_prior_not_observed_slip",
                    ),
                }
            ),
        ),
        confidence=0.35,
        reasons=("cold_start_default", "default_prior_not_observed_slip"),
    )
    mismatched_result = result.model_copy(update={"prompt_safe_context": incompatible_context})
    with pytest.raises(ValidationError, match="prompt_safe_context transition_state"):
        to_prompt_safe_markov_orchestration_context(mismatched_result)

    ready_without_context = result.model_copy(
        update={
            "transition_plan": None,
            "prompt_safe_context": None,
        }
    )
    with pytest.raises(ValidationError, match="ready or degraded"):
        MarkovCoachingOrchestrationResultV1.model_validate(
            ready_without_context.model_dump(mode="python")
        )

    no_recommendation_with_context = result.model_copy(
        update={
            "decision_trace": result.decision_trace.model_copy(
                update={"decision_status": "no_recommendation"}
            ),
        }
    )
    with pytest.raises(ValidationError, match="no_recommendation"):
        to_prompt_safe_markov_orchestration_context(no_recommendation_with_context)

    ready_with_degraded_evidence = result.model_copy(
        update={
            "decision_trace": result.decision_trace.model_copy(
                update={
                    "decision_status": "ready",
                    "state_degraded": True,
                    "planner_degraded": True,
                    "degrade_reasons": ("adherence_state_invalid_degraded",),
                }
            ),
        }
    )
    with pytest.raises(ValidationError, match="ready result must not be degraded"):
        MarkovCoachingOrchestrationResultV1.model_validate(
            ready_with_degraded_evidence.model_dump(mode="python")
        )

    no_recommendation_with_recommended_plan = result.model_copy(
        update={
            "prompt_safe_context": None,
            "decision_trace": result.decision_trace.model_copy(
                update={"decision_status": "no_recommendation"}
            ),
        }
    )
    with pytest.raises(ValidationError, match="no_recommendation result"):
        MarkovCoachingOrchestrationResultV1.model_validate(
            no_recommendation_with_recommended_plan.model_dump(mode="python")
        )


def test_degraded_state_and_recent_behavior_reasons_are_deterministic(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    degraded_state = _state(
        adherence=AdherenceSnapshot(source_status="invalid_degraded"),
        recent_behavior=RecentBehaviorSnapshot(
            slip_count_7d=1,
            slip_like_count_7d=1,
            scanned_event_count=250,
            events_capped=True,
        ),
    )
    _install_static_state_builder(monkeypatch, degraded_state)

    with configure_sqlite_database.session_scope() as session:
        result = build_markov_coaching_orchestration_result(
            user_id=degraded_state.user_id,
            session=session,
        )

    assert result.prompt_safe_context is not None
    assert result.decision_trace.decision_status == "degraded"
    assert result.decision_trace.state_degraded is True
    assert result.decision_trace.planner_degraded is True
    assert result.decision_trace.degrade_reasons == (
        "recent_behavior_capped",
        "adherence_state_invalid_degraded",
    )


def test_prompt_safe_adapter_projection_excludes_identifiers_timestamps_and_claims(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = 93_006
    other_user_id = 93_007
    monkeypatch.setattr(builder_module, "_now_utc", lambda: FIXED_NOW)
    _install_active_goal_builder(monkeypatch)
    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id, other_user_id)
        session.add(
            _event(
                user_id=user_id,
                day=FIXED_NOW.date(),
                event_type="slip",
                client_event_id="client-sensitive-adapter-1",
                payload={
                    "free_text": "Ada Lovelace needs therapy and diagnosis treatment",
                    "email": "ada@example.com",
                    "api" + "_key": "synthetic-key-like-marker-b",
                    "medical_claim": "treat diabetes",
                },
            )
        )
        session.add(
            _event(
                user_id=other_user_id,
                day=FIXED_NOW.date(),
                event_type="slip",
                client_event_id="other-client-sensitive",
                payload={"free_text": "other user raw text"},
            )
        )

    with configure_sqlite_database.session_scope() as session:
        result = build_markov_coaching_orchestration_result(user_id=user_id, session=session)

    assert result.prompt_safe_context is not None
    safe_json = _safe_json(result).lower()
    for forbidden in (
        "user_id",
        str(user_id),
        str(other_user_id),
        "assembled_at",
        "last_",
        "analyzer_key",
        "alpha",
        "beta",
        "client_event_id",
        "client-sensitive-adapter-1",
        "other-client-sensitive",
        "ada lovelace",
        "ada@example.com",
        "synthetic-key-like-marker-b",
        "therapy",
        "diagnosis",
        "treatment",
        "medical_claim",
        "treat diabetes",
        "other user raw text",
    ):
        assert forbidden not in safe_json
    assert "non_diagnostic" in safe_json


def test_planner_fail_closed_trace_does_not_include_raw_exception_text(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = 93_008
    monkeypatch.setattr(builder_module, "_now_utc", lambda: FIXED_NOW)
    _install_active_goal_builder(monkeypatch)

    def _broken_planner(*args: object, **kwargs: object) -> None:
        raise ValueError("raw planner exception with ada@example.com and key-like-marker")

    monkeypatch.setattr(adapter_module, "build_markov_coaching_transition_plan", _broken_planner)
    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id)
    with configure_sqlite_database.session_scope() as session:
        result = build_markov_coaching_orchestration_result(user_id=user_id, session=session)

    assert result.transition_plan is None
    assert result.prompt_safe_context is None
    assert result.decision_trace.decision_status == "no_recommendation"
    assert result.decision_trace.planner_degraded is True
    assert result.decision_trace.degrade_reasons == ("planner_unavailable",)
    trace_json = json.dumps(result.decision_trace.model_dump(mode="json"), sort_keys=True)
    assert "ada@example.com" not in trace_json
    assert "key-like-marker" not in trace_json


def test_adapter_source_stays_service_only_without_runtime_or_write_wiring() -> None:
    adapter_text = (REPO_ROOT / "app/services/coaching_markov_orchestration_adapter.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "APIRouter",
        "FastAPI",
        "legacy_app",
        "fitchef_runtime",
        "core.rag",
        "GraphRAG",
        "from providers",
        "import providers",
        "get_provider",
        "Redis",
        "httpx",
        "requests",
        "semantic_cache",
        "record_event(",
        "upsert_state(",
        "update_if_version_matches(",
        "session.add(",
        "session.commit(",
        "session.flush(",
        "openapi",
    ):
        assert forbidden not in adapter_text


def test_public_route_runtime_and_client_surfaces_do_not_import_adapter() -> None:
    public_paths = [
        REPO_ROOT / "app/main.py",
        REPO_ROOT / "legacy_app.py",
        *sorted((REPO_ROOT / "app/routers").glob("*.py")),
    ]
    public_text = "\n".join(path.read_text(encoding="utf-8") for path in public_paths)

    assert "coaching_markov_orchestration_adapter" not in public_text
    assert "build_markov_coaching_orchestration_result" not in public_text


def test_prompt_safe_projection_accepts_valid_no_context_inputs() -> None:
    disabled_result = MarkovCoachingOrchestrationResultV1(
        coaching_state=_state(),
        transition_plan=None,
        prompt_safe_context=None,
        decision_trace=MarkovCoachingOrchestrationTraceV1(
            decision_status="shadow_disabled",
            degrade_reasons=("feature_gate_disabled",),
        ),
    )

    assert to_prompt_safe_markov_orchestration_context(disabled_result) is None
