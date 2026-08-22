"""Contract tests for additive structured FitChef schemas."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

import app.services.fitchef_claim_evidence_assurance as assurance_service
from app.schemas.fitchef import (
    FitChefClarificationV1,
    FitChefDistortionFieldAssuranceAssessmentV1,
    FitChefDistortionSimulatorInput,
    FitChefDistortionSimulatorResult,
    FitChefDistortionSimulatorTaskEnvelope,
    FitChefFieldAssuranceRecordV1,
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
    FitChefSupportHandoffActionV1,
    FitChefSupportHandoffRequest,
    FitChefSupportHandoffResponse,
    FitChefSupportNeed,
    FitChefVipCoachingErrorResponse,
    FitChefWeeklyReflectionResponse,
)
from app.services.fitchef_claim_evidence_assurance import (
    FitChefSourceOccurrenceV1,
    FitChefSourceSnapshotV1,
    build_distortion_field_assurance_assessment,
    build_distortion_field_assurance_unavailable,
    build_fitchef_source_items,
    freeze_fitchef_source_snapshot,
)
from app.services.fitchef_support_handoff import build_fitchef_support_handoff
from core.evidence.fingerprints import JsonValue


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
        claim_evidence_assessment=build_distortion_field_assurance_unavailable(
            reason_code="assessment_unavailable"
        ),
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
    assert "claim_evidence_assessment" not in distortion_result.model_dump()
    assert distortion_result.claim_evidence_assessment.assessed_field_count == 6
    assert FitChefDistortionSimulatorResult.model_fields["claim_evidence_assessment"].is_required()
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
    ("support_need", "target_surface"),
    (
        ("daily_structure", "pro_daily_plate"),
        ("weekly_structure", "pro_weekly_plan"),
    ),
)
def test_support_handoff_contract_and_service_are_exact(
    support_need: FitChefSupportNeed,
    target_surface: str,
) -> None:
    """The pure selector returns one immutable descriptor for each closed need."""

    request = FitChefSupportHandoffRequest(support_need=support_need)
    response = build_fitchef_support_handoff(support_need=request.support_need)

    assert response.model_dump(mode="json") == {
        "schema_version": "fitchef_support_handoff.v1",
        "scenario": "support_handoff",
        "support_need": support_need,
        "action": {
            "action_type": "handoff_to_product_surface",
            "target_surface": target_surface,
        },
        "user_confirmation_required": True,
        "execution_authority": False,
        "plan_mutation_authority": False,
        "used_llm": False,
        "wellness_boundary": "wellness_planning_only",
    }
    assert response.user_confirmation_required is True
    assert response.execution_authority is False
    assert response.plan_mutation_authority is False
    assert response.used_llm is False

    explicit_response = FitChefSupportHandoffResponse.model_validate(
        {
            "schema_version": "fitchef_support_handoff.v1",
            "scenario": "support_handoff",
            "support_need": support_need,
            "action": {
                "action_type": "handoff_to_product_surface",
                "target_surface": target_surface,
            },
            "user_confirmation_required": True,
            "execution_authority": False,
            "plan_mutation_authority": False,
            "used_llm": False,
            "wellness_boundary": "wellness_planning_only",
        }
    )
    assert explicit_response.user_confirmation_required is True
    assert explicit_response.execution_authority is False
    assert explicit_response.plan_mutation_authority is False
    assert explicit_response.used_llm is False

    with pytest.raises(ValidationError):
        request.support_need = "weekly_structure"
    with pytest.raises(ValidationError):
        response.action.target_surface = "pro_daily_plate"


def test_support_handoff_models_reject_extras_and_impossible_values() -> None:
    """Frozen DTOs fail closed on open-world fields and impossible direct input."""

    with pytest.raises(ValidationError):
        FitChefSupportHandoffRequest.model_validate(
            {"support_need": "daily_structure", "history": []}
        )
    with pytest.raises(ValidationError):
        FitChefSupportHandoffActionV1.model_validate(
            {
                "action_type": "navigate",
                "target_surface": "pro_daily_plate",
            }
        )
    with pytest.raises(ValidationError):
        FitChefSupportHandoffResponse.model_validate(
            {
                "support_need": "daily_structure",
                "action": {
                    "action_type": "handoff_to_product_surface",
                    "target_surface": "pro_daily_plate",
                },
                "message": "free text is forbidden",
            }
        )

    impossible_need = cast(FitChefSupportNeed, "unsupported")
    with pytest.raises(ValueError, match="unsupported FitChef support need"):
        build_fitchef_support_handoff(support_need=impossible_need)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    (
        ("user_confirmation_required", False),
        ("user_confirmation_required", 0),
        ("user_confirmation_required", 1),
        ("user_confirmation_required", "true"),
        ("user_confirmation_required", None),
        ("execution_authority", True),
        ("execution_authority", 0),
        ("execution_authority", 1),
        ("execution_authority", "false"),
        ("execution_authority", None),
        ("plan_mutation_authority", True),
        ("plan_mutation_authority", 0),
        ("plan_mutation_authority", 1),
        ("plan_mutation_authority", "false"),
        ("plan_mutation_authority", None),
        ("used_llm", True),
        ("used_llm", 0),
        ("used_llm", 1),
        ("used_llm", "false"),
        ("used_llm", None),
    ),
)
def test_support_handoff_response_rejects_non_exact_boolean_values(
    field_name: str,
    invalid_value: object,
) -> None:
    """Identity validators reject opposite, numeric, string, and null booleans."""

    payload: dict[str, object] = {
        "support_need": "daily_structure",
        "action": {
            "action_type": "handoff_to_product_surface",
            "target_surface": "pro_daily_plate",
        },
        field_name: invalid_value,
    }
    with pytest.raises(ValidationError):
        FitChefSupportHandoffResponse.model_validate(payload)


def test_support_handoff_service_import_boundary_is_pure() -> None:
    """The selector imports only its frozen schema and no execution subsystem."""

    service_path = Path("app/services/fitchef_support_handoff.py")
    tree = ast.parse(service_path.read_text(encoding="utf-8"))
    direct_imports = [node for node in ast.walk(tree) if isinstance(node, ast.Import)]
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert direct_imports == []
    assert imported_modules == {"__future__", "app.schemas.fitchef_coaching"}


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


def _field_assurance_snapshot() -> FitChefSourceSnapshotV1:
    return freeze_fitchef_source_snapshot(
        (
            FitChefSourceOccurrenceV1(
                ordinal=0,
                chunk_id="contract-source",
                file="docs/cbt/contract.md",
                content="Sanitized contract context.",
                preview="Contract preview",
                score=0.88,
            ),
        )
    )


def _field_assurance_assessment() -> FitChefDistortionFieldAssuranceAssessmentV1:
    snapshot = _field_assurance_snapshot()
    return build_distortion_field_assurance_assessment(
        snapshot,
        result_sources=build_fitchef_source_items(snapshot),
    )


def test_field_assurance_records_reject_every_semantic_widening() -> None:
    """The CI-selected contract suite executes every negative record boundary."""

    assessment = _field_assurance_assessment()
    request_record = assessment.records[0].model_dump(mode="python")
    balanced_record = assessment.records[4].model_dump(mode="python")
    action_record = assessment.records[5].model_dump(mode="python")
    candidate_ref = assessment.records[4].candidate_source_refs[0]
    invalid_records = (
        {**request_record, "adjudicated_support_status": "supported"},
        {**request_record, "conflict_adjudicated": True},
        {**balanced_record, "candidate_source_refs": (candidate_ref, candidate_ref)},
        {**balanced_record, "candidate_source_refs": ("sha256:" + "g" * 64,)},
        {**request_record, "claim_type": "recommendation"},
        {**balanced_record, "claim_type": "inference"},
        {**action_record, "claim_type": "inference"},
        {
            **request_record,
            "assurance_state": "not_evidence_bearing",
            "reason_codes": ("not_evidence_bearing",),
        },
        {**request_record, "reason_codes": ("candidate_sources_missing",)},
        {**request_record, "candidate_source_refs": (candidate_ref,)},
        {
            **balanced_record,
            "assurance_state": "evidence_link_missing",
            "reason_codes": ("candidate_sources_missing",),
        },
        {**balanced_record, "candidate_source_refs": ()},
    )

    for payload in invalid_records:
        with pytest.raises(ValidationError):
            FitChefFieldAssuranceRecordV1.model_validate(payload)


def test_field_assurance_assessment_rejects_aggregate_and_availability_drift() -> None:
    """The CI-selected contract suite exercises aggregate and availability invariants."""

    assessment = _field_assurance_assessment()
    payload = assessment.model_dump(mode="python")
    invalid_aggregates = (
        {**payload, "source_snapshot_fingerprint": "sha256:" + "g" * 64},
        {**payload, "request_context_only_count": True},
        {**payload, "public_response_authority": True},
        {**payload, "records": tuple(reversed(assessment.records))},
        {**payload, "request_context_only_count": 3},
        {**payload, "assessed_field_count": 5},
        {**payload, "evidence_sensitive_field_count": 0},
        {**payload, "support_claimed_count": 1},
    )
    for invalid_payload in invalid_aggregates:
        with pytest.raises(ValidationError):
            FitChefDistortionFieldAssuranceAssessmentV1.model_validate(invalid_payload)

    unavailable = build_distortion_field_assurance_unavailable(reason_code="assessment_unavailable")
    unavailable_payload = unavailable.model_dump(mode="python")
    partial_payload = {
        **unavailable_payload,
        "records": (assessment.records[0], *unavailable.records[1:]),
        "request_context_only_count": 1,
        "assessment_unavailable_count": 5,
    }
    with pytest.raises(ValidationError):
        FitChefDistortionFieldAssuranceAssessmentV1.model_validate(partial_payload)

    alternate_reason = FitChefFieldAssuranceRecordV1.model_validate(
        {
            **unavailable.records[0].model_dump(mode="python"),
            "reason_codes": ("snapshot_fingerprint_unavailable",),
        }
    )
    mixed_reason_payload = {
        **unavailable_payload,
        "records": (alternate_reason, *unavailable.records[1:]),
    }
    with pytest.raises(ValidationError):
        FitChefDistortionFieldAssuranceAssessmentV1.model_validate(mixed_reason_payload)

    fingerprint_parity_payload = {
        **unavailable_payload,
        "source_snapshot_fingerprint": assessment.source_snapshot_fingerprint,
    }
    with pytest.raises(ValidationError):
        FitChefDistortionFieldAssuranceAssessmentV1.model_validate(fingerprint_parity_payload)


def test_field_assurance_builder_fails_closed_for_every_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CI-selected suite covers ordinal, projection, result, and digest failures."""

    with pytest.raises(ValueError, match="contiguous and zero-based"):
        freeze_fitchef_source_snapshot(
            (
                FitChefSourceOccurrenceV1(
                    ordinal=1,
                    chunk_id="invalid-ordinal",
                    file="docs/cbt/invalid.md",
                    content="Sanitized invalid context.",
                    preview="Invalid preview",
                    score=0.5,
                ),
            )
        )

    snapshot = _field_assurance_snapshot()
    sources = build_fitchef_source_items(snapshot)
    drifted_snapshot = replace(snapshot, projection=())
    projection_mismatch = build_distortion_field_assurance_assessment(
        drifted_snapshot,
        result_sources=sources,
    )
    result_mismatch = build_distortion_field_assurance_assessment(
        snapshot,
        result_sources=[sources[0].model_copy(update={"preview": "Drifted preview"})],
    )
    for mismatch in (projection_mismatch, result_mismatch):
        assert mismatch.records[4].assurance_state == "source_snapshot_mismatch"
        assert mismatch.records[4].candidate_source_refs == ()

    real_fingerprint_payload = assurance_service.fingerprint_payload

    def _raise_fingerprint_error(_payload: JsonValue) -> str:
        raise RuntimeError("deterministic fingerprint failure")

    monkeypatch.setattr(
        assurance_service,
        "fingerprint_payload",
        _raise_fingerprint_error,
    )
    recomputation_unavailable = build_distortion_field_assurance_assessment(
        snapshot,
        result_sources=sources,
    )
    assert recomputation_unavailable.assessment_unavailable_count == 6

    def _fail_occurrence_ref(payload: JsonValue) -> str:
        if (
            isinstance(payload, dict)
            and payload.get("schema_version") == "fitchef_source_occurrence_ref.v1"
        ):
            raise RuntimeError("deterministic occurrence-ref failure")
        return real_fingerprint_payload(payload)

    monkeypatch.setattr(
        assurance_service,
        "fingerprint_payload",
        _fail_occurrence_ref,
    )
    occurrence_ref_unavailable = build_distortion_field_assurance_assessment(
        snapshot,
        result_sources=sources,
    )
    assert occurrence_ref_unavailable.assessment_unavailable_count == 6
