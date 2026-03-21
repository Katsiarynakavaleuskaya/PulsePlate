"""Contract tests for additive structured FitChef schemas."""

from __future__ import annotations

from app.schemas.fitchef import (
    FitChefDistortionSimulatorInput,
    FitChefDistortionSimulatorResult,
    FitChefDistortionSimulatorTaskEnvelope,
    FitChefIdentityLoopMapperInput,
    FitChefIdentityLoopMapperResult,
    FitChefIdentityLoopMapperTaskEnvelope,
    FitChefIdentityLoopValue,
    FitChefSourceItem,
)
from app.schemas.fitchef_coaching import (
    FitChefCoachingSourceItem,
    FitChefDistortionSimulatorRequest,
    FitChefDistortionSimulatorResponse,
    FitChefIdentityLoopMapperRequest,
    FitChefIdentityLoopMapperResponse,
    FitChefIdentityLoopView,
)


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
