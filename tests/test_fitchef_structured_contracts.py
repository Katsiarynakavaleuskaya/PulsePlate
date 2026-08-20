"""Contract tests for additive structured FitChef schemas."""

from __future__ import annotations

import pytest

from app.schemas.fitchef import (
    FitChefClarificationV1,
    FitChefDistortionSimulatorInput,
    FitChefDistortionSimulatorResult,
    FitChefDistortionSimulatorTaskEnvelope,
    FitChefIdentityLoopMapperInput,
    FitChefIdentityLoopMapperResult,
    FitChefIdentityLoopMapperTaskEnvelope,
    FitChefIdentityLoopValue,
    FitChefSourceItem,
    FitChefWeeklyReflectionResult,
)
from app.schemas.fitchef_coaching import (
    FitChefCoachingSourceItem,
    FitChefDistortionSimulatorRequest,
    FitChefDistortionSimulatorResponse,
    FitChefIdentityLoopMapperRequest,
    FitChefIdentityLoopMapperResponse,
    FitChefIdentityLoopView,
    FitChefVipCoachingErrorResponse,
    FitChefWeeklyReflectionResponse,
)


def test_weekly_reflection_clarification_contract_is_fixed_and_immutable() -> None:
    """Clarification accepts exactly one goal field and no mutable extras."""

    clarification = FitChefClarificationV1()

    assert clarification.model_dump(mode="json") == {
        "schema_version": "fitchef_clarification.v1",
        "kind": "missing_required_context",
        "question_id": "weekly_reflection.current_goal",
        "requested_fields": ["goal"],
        "question_count": 1,
    }
    for invalid_fields in ([], ["goal", "goal"], ["goal", "summary"], ["summary"]):
        with pytest.raises(ValueError):
            FitChefClarificationV1.model_validate({"requested_fields": invalid_fields})
    with pytest.raises(ValueError):
        FitChefClarificationV1.model_validate({"unexpected": "field"})
    with pytest.raises(ValueError):
        clarification.question_count = 1


def test_weekly_reflection_response_defaults_remain_additive() -> None:
    """Existing constructors default to the generated response state."""

    internal = FitChefWeeklyReflectionResult(
        message="Keep one dinner pattern that worked.",
        sources=[],
        confidence=0.0,
        warnings=[],
        action_items=[],
        mode="auto-safe",
        quota_state="consumed",
        transparency_notice_id="ai_generated_insight",
        wellness_boundary="Wellness coaching only.",
    )
    public = FitChefWeeklyReflectionResponse(
        message=internal.message,
        scenario="weekly_reflection",
        sources=[],
        confidence=internal.confidence,
        warnings=internal.warnings,
        action_items=internal.action_items,
        quota_state=internal.quota_state,
        transparency_notice_id=internal.transparency_notice_id,
        wellness_boundary=internal.wellness_boundary,
    )

    assert internal.response_state == "generated"
    assert internal.clarification is None
    assert public.response_state == "generated"
    assert public.clarification is None


def test_structured_fitchef_internal_task_envelopes_are_additive() -> None:
    """Internal envelopes should preserve the additive structured task contract."""

    distortion_task = FitChefDistortionSimulatorTaskEnvelope(
        mode="auto-safe",
        input=FitChefDistortionSimulatorInput(
            safe_situation="I ate dessert after dinner",
            safe_automatic_thought="I ruined the whole day",
            safe_emotion="guilt",
            safe_goal="steady dinners",
            api_key="pp_pro_auth_id",  # pragma: allowlist secret
            endpoint="/api/v1/pro/fitchef/explain",
            method="POST",
        ),
    )
    identity_task = FitChefIdentityLoopMapperTaskEnvelope(
        mode="review-required",
        input=FitChefIdentityLoopMapperInput(
            safe_goal="steady dinners",
            safe_recent_pattern="I stop planning dinner after one hard evening",
            safe_self_talk="I am too inconsistent",
            safe_trigger_context="work runs late",
            api_key="pp_vip_auth_id",  # pragma: allowlist secret
            endpoint="/api/v1/vip/fitchef/insight",
            method="POST",
        ),
    )

    assert distortion_task.task_type == "distortion_simulator"
    assert distortion_task.tool_budget == 1
    assert identity_task.task_type == "identity_loop_mapper"
    assert identity_task.input.safe_trigger_context == "work runs late"


def test_structured_fitchef_internal_results_roundtrip() -> None:
    """Internal structured result models should serialize deterministically."""

    source = FitChefSourceItem(
        chunk_id="chunk-1",
        file="docs/cbt/cognitive_restructuring.md",
        preview="All-or-nothing thinking example",
        score=0.91,
    )
    distortion_result = FitChefDistortionSimulatorResult(
        distortion_labels=["all_or_nothing_thinking"],
        why_it_matches="The thought turns one moment into a full-day verdict.",
        evidence_for=["Dessert happened and the guilt feels real."],
        evidence_against=["One dessert does not define the whole day."],
        balanced_reframe="This was one moment, not the whole pattern.",
        next_small_action="Choose one balanced next meal.",
        sources=[source],
        confidence=0.42,
        warnings=["structured_parse_fallback"],
        mode="auto-safe",
        quota_state="consumed",
        transparency_notice_id="fitchef_structured_v1",
        wellness_boundary="Wellness coaching only.",
    )
    identity_result = FitChefIdentityLoopMapperResult(
        identity_loop=FitChefIdentityLoopValue(
            belief="If I slip once, I prove I am inconsistent.",
            behavior="I stop planning after one hard evening.",
            short_term_reward="It reduces pressure in the moment.",
            long_term_cost="It keeps the same dinner spiral repeating.",
        ),
        identity_shift_statement="I can return after one wobble.",
        replacement_action="Plan one default dinner before the trigger window.",
        repair_if_slip="Name the slip and restart at the next meal.",
        sources=[source],
        confidence=0.38,
        warnings=[],
        mode="review-required",
        quota_state="not_consumed",
        transparency_notice_id="fitchef_structured_v1",
        wellness_boundary="Wellness coaching only.",
    )

    assert distortion_result.scenario == "distortion_simulator"
    assert distortion_result.model_dump()["sources"][0]["file"] == source.file
    assert identity_result.scenario == "identity_loop_mapper"
    assert identity_result.model_dump()["identity_loop"]["belief"].startswith("If I slip once")


def test_structured_fitchef_public_request_and_response_contracts() -> None:
    """Public request/response DTOs should preserve the frozen structured contract."""

    distortion_request = FitChefDistortionSimulatorRequest(
        situation="I ate dessert after dinner",
        automatic_thought="I ruined the whole day",
        emotion="guilt",
        goal="steady dinners",
    )
    identity_request = FitChefIdentityLoopMapperRequest(
        goal="steady dinners",
        recent_pattern="I stop planning dinner after one hard evening",
        self_talk="I am too inconsistent",
        trigger_context="work runs late",
    )
    source = FitChefCoachingSourceItem(
        file="docs/cbt/cognitive_restructuring.md",
        preview="All-or-nothing thinking example",
        score=0.91,
    )
    distortion_response = FitChefDistortionSimulatorResponse(
        scenario="distortion_simulator",
        distortion_labels=["all_or_nothing_thinking"],
        why_it_matches="The thought turns one moment into a full-day verdict.",
        evidence_for=["Dessert happened and the guilt feels real."],
        evidence_against=["One dessert does not define the whole day."],
        balanced_reframe="This was one moment, not the whole pattern.",
        next_small_action="Choose one balanced next meal.",
        sources=[source],
        confidence=0.42,
        warnings=[],
        quota_state="consumed",
        transparency_notice_id="fitchef_structured_v1",
        wellness_boundary="Wellness coaching only.",
    )
    identity_response = FitChefIdentityLoopMapperResponse(
        scenario="identity_loop_mapper",
        identity_loop=FitChefIdentityLoopView(
            belief="If I slip once, I prove I am inconsistent.",
            behavior="I stop planning after one hard evening.",
            short_term_reward="It reduces pressure in the moment.",
            long_term_cost="It keeps the same dinner spiral repeating.",
        ),
        identity_shift_statement="I can return after one wobble.",
        replacement_action="Plan one default dinner before the trigger window.",
        repair_if_slip="Name the slip and restart at the next meal.",
        sources=[source],
        confidence=0.38,
        warnings=["delegated"],
        quota_state="not_consumed",
        transparency_notice_id="fitchef_structured_v1",
        wellness_boundary="Wellness coaching only.",
    )

    assert distortion_request.goal == "steady dinners"
    assert identity_request.trigger_context == "work runs late"
    assert distortion_response.model_dump()["scenario"] == "distortion_simulator"
    assert identity_response.model_dump()["scenario"] == "identity_loop_mapper"


@pytest.mark.parametrize(
    ("payload", "field_name"),
    [
        (
            {
                "situation": "   ",
                "automatic_thought": "I ruined the whole day",
                "emotion": "guilt",
                "goal": "steady dinners",
            },
            "situation",
        ),
        (
            {
                "situation": "Dessert after dinner",
                "automatic_thought": "   ",
                "emotion": "guilt",
                "goal": "steady dinners",
            },
            "automatic_thought",
        ),
        (
            {
                "situation": "Dessert after dinner",
                "automatic_thought": "I ruined the whole day",
                "emotion": "   ",
                "goal": "steady dinners",
            },
            "emotion",
        ),
        (
            {
                "situation": "Dessert after dinner",
                "automatic_thought": "I ruined the whole day",
                "emotion": "guilt",
                "goal": "   ",
            },
            "goal",
        ),
    ],
)
def test_distortion_simulator_request_rejects_blank_transport_fields(
    payload: dict[str, str],
    field_name: str,
) -> None:
    """Structured request DTO must fail closed on whitespace-only values."""

    with pytest.raises(ValueError, match="value must not be blank"):
        FitChefDistortionSimulatorRequest(**payload)


@pytest.mark.parametrize(
    ("payload", "field_name"),
    [
        (
            {
                "goal": "   ",
                "recent_pattern": "I stop planning dinner after one hard evening",
                "self_talk": "I am too inconsistent",
                "trigger_context": "work runs late",
            },
            "goal",
        ),
        (
            {
                "goal": "steady dinners",
                "recent_pattern": "   ",
                "self_talk": "I am too inconsistent",
                "trigger_context": "work runs late",
            },
            "recent_pattern",
        ),
        (
            {
                "goal": "steady dinners",
                "recent_pattern": "I stop planning dinner after one hard evening",
                "self_talk": "   ",
                "trigger_context": "work runs late",
            },
            "self_talk",
        ),
        (
            {
                "goal": "steady dinners",
                "recent_pattern": "I stop planning dinner after one hard evening",
                "self_talk": "I am too inconsistent",
                "trigger_context": "   ",
            },
            "trigger_context",
        ),
    ],
)
def test_identity_loop_request_rejects_blank_transport_fields(
    payload: dict[str, str],
    field_name: str,
) -> None:
    """Identity-loop DTO must reject whitespace-only transport strings."""

    with pytest.raises(ValueError, match="value must not be blank"):
        FitChefIdentityLoopMapperRequest(**payload)


def test_vip_error_response_enforces_frozen_aliases() -> None:
    """VIP error aliases must not drift from the frozen public envelope."""

    response = FitChefVipCoachingErrorResponse(
        status="error",
        code="rate_limit_exceeded",
        message="Rate limit exceeded",
        detail="Rate limit exceeded",
        error="rate_limit_exceeded",
    )

    assert response.detail == response.message
    assert response.error == response.code
    with pytest.raises(ValueError, match="VIP error aliases must mirror message/code"):
        FitChefVipCoachingErrorResponse(
            status="error",
            code="rate_limit_exceeded",
            message="Rate limit exceeded",
            detail="generic detail",
            error="rate_limit_exceeded",
        )
    with pytest.raises(ValueError, match="VIP error aliases must mirror message/code"):
        FitChefVipCoachingErrorResponse(
            status="error",
            code="rate_limit_exceeded",
            message="Rate limit exceeded",
            detail="Rate limit exceeded",
            error="different_code",
        )
