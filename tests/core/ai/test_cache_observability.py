from __future__ import annotations

import json
from collections.abc import Mapping, MutableMapping
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

import core.ai.cache_observability as cache_observability
from core.ai.cache_observability import (
    EXPECTED_ACTION_FALLBACK,
    EXPECTED_ACTION_SAFE_HIT,
    REASON_ADMISSION_BLOCKED,
    REASON_BLOCKED_SURFACE,
    REASON_CONTEXT_LEAKAGE,
    REASON_KILL_SWITCH_DISABLED,
    REASON_MODEL_MISMATCH,
    REASON_POLICY_MISMATCH,
    REASON_RESPONSE_FINGERPRINT_MISMATCH,
    REASON_STALE_SOURCE,
    CacheLookupAuditEvent,
    CacheObservabilityMetrics,
    CacheStopDecision,
    CacheStopRules,
    FalseHitHarnessEvaluation,
    FalseHitHarnessCase,
    JsonValue,
    KillSwitchSnapshot,
    TokenEconomyEstimate,
    build_cache_lookup_audit_event,
    build_token_economy_estimate,
    compute_cache_observability_metrics,
    evaluate_cache_stop_rules,
    evaluate_false_hit_case,
    evaluate_false_hit_harness,
    to_stable_mapping,
)
from core.ai.exact_fuzzy_cache import (
    ExactFuzzyCacheLookupRequest,
    ExactFuzzyCacheLookupResult,
    ExactFuzzyCacheRecord,
    ExactFuzzyMatchPolicy,
    build_exact_fuzzy_lineage,
    create_exact_fuzzy_cache_record,
    match_exact_fuzzy_records,
)
from tests.helpers.semantic_cache_import_guard import (
    assert_no_forbidden_semantic_cache_calls,
    assert_no_forbidden_semantic_cache_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = REPO_ROOT / "core" / "ai" / "cache_observability.py"
PRODUCED_AT = "2026-05-07T12:00:00Z"
SafeMetadata = Mapping[str, JsonValue]


def _record() -> ExactFuzzyCacheRecord:
    lineage = build_exact_fuzzy_lineage(
        eval_event_ids=("eval:2", "eval:1"),
        admission_decision_id="admission:1",
        promotion_ids=("promotion:1",),
        replay_entry_ids=("replay:1",),
        source_fingerprints=("sha256:source-b", "sha256:source-a"),
        policy_version="semantic-cache-sc-g3-v1",
    )
    return create_exact_fuzzy_cache_record(
        surface="insight",
        raw_query="Plan protein breakfast",
        context_fingerprint="sha256:context",
        provider_key="provider:test",
        model_key="model:test",
        user_tier="pro",
        transparency_notice_id="notice:insight:v1",
        lineage=lineage,
        response_fingerprint="sha256:response",
        safety_flags=("wellness-only",),
    )


def _request(raw_query: str = "Plan protein breakfast") -> ExactFuzzyCacheLookupRequest:
    return ExactFuzzyCacheLookupRequest(
        surface="insight",
        raw_query=raw_query,
        context_fingerprint="sha256:context",
        source_fingerprints=("sha256:source-a", "sha256:source-b"),
        policy_version="semantic-cache-sc-g3-v1",
        provider_key="provider:test",
        model_key="model:test",
        user_tier="pro",
        transparency_notice_id="notice:insight:v1",
    )


def _policy() -> ExactFuzzyMatchPolicy:
    return ExactFuzzyMatchPolicy(
        policy_version="semantic-cache-sc-g3-v1",
        token_jaccard_min_bps=5000,
        sequence_ratio_min_bps=5000,
        max_token_count_delta=1,
    )


def _audit_event(raw_query: str = "Plan protein breakfast") -> CacheLookupAuditEvent:
    record = _record()
    result = match_exact_fuzzy_records(
        request=_request(raw_query),
        candidate_records=(record,),
        policy=_policy(),
    )
    return build_cache_lookup_audit_event(
        request=_request(raw_query),
        lookup_result=result,
        candidate_record=record,
        produced_at=PRODUCED_AT,
        metadata={"review": "sc-g3"},
    )


def _miss_audit_event() -> CacheLookupAuditEvent:
    result = match_exact_fuzzy_records(
        request=_request("unmatched query"),
        candidate_records=(),
        policy=_policy(),
    )
    return build_cache_lookup_audit_event(
        request=_request("unmatched query"),
        lookup_result=result,
        candidate_record=None,
        produced_at=PRODUCED_AT,
        metadata={"review": "sc-g3"},
    )


def _case(
    *,
    case_id: str = "case:1",
    expected_action: str = EXPECTED_ACTION_SAFE_HIT,
    risk_class: str = "exact_duplicate_hit",
    current_source_fingerprints: tuple[str, ...] = ("sha256:source-a", "sha256:source-b"),
    current_policy_version: str = "semantic-cache-sc-g3-v1",
    current_model_key: str = "model:test",
    current_user_tier: str = "pro",
    current_context_fingerprint: str = "sha256:context",
    admission_allowed: bool = True,
    blocked_surface: bool = False,
    negative_control: bool = False,
    fresh_response_fingerprint: str | None = "sha256:response",
    metadata: SafeMetadata | None = None,
) -> FalseHitHarnessCase:
    return FalseHitHarnessCase(
        case_id=case_id,
        risk_class=risk_class,
        audit_event=_audit_event(),
        expected_action=expected_action,
        fresh_response_fingerprint=fresh_response_fingerprint,
        current_source_fingerprints=current_source_fingerprints,
        current_policy_version=current_policy_version,
        current_model_key=current_model_key,
        current_user_tier=current_user_tier,
        current_context_fingerprint=current_context_fingerprint,
        admission_allowed=admission_allowed,
        blocked_surface=blocked_surface,
        negative_control=negative_control,
        metadata={"case": case_id} if metadata is None else metadata,
    )


def test_deterministic_audit_event_id_and_stable_mapping() -> None:
    first = _audit_event("Plan protein breakfast")
    second = _audit_event("Plan protein breakfast")

    assert first.audit_event_id == second.audit_event_id
    assert first.idempotency_key == second.idempotency_key
    assert to_stable_mapping(first) == to_stable_mapping(second)


def test_distinct_fuzzy_queries_have_distinct_audit_identity() -> None:
    first = _audit_event("Plan protein breakfast")
    reordered = _audit_event("breakfast protein plan")

    assert first.candidate_record_id == reordered.candidate_record_id
    assert first.match_mode == "exact"
    assert reordered.match_mode == "fuzzy_reordered_tokens"
    assert first.request_fingerprint != reordered.request_fingerprint
    assert first.audit_event_id != reordered.audit_event_id
    assert first.idempotency_key != reordered.idempotency_key


def test_audit_serialization_excludes_raw_query_prompt_response() -> None:
    raw_query = "Plan protein breakfast!!!"
    audit = _audit_event(raw_query)
    serialized = json.dumps(dict(to_stable_mapping(audit)), sort_keys=True)

    assert raw_query not in serialized
    assert "normalized_query" not in serialized
    assert "Plan protein breakfast" not in serialized
    assert "raw_query" not in serialized


@pytest.mark.parametrize(
    ("candidate_record_id", "candidate_response_fingerprint", "match_mode", "expected"),
    [
        (None, "sha256:response", "exact", "candidate_record_id"),
        ("record:1", None, "exact", "candidate_response_fingerprint"),
        ("record:1", "sha256:response", None, "match_mode"),
    ],
)
def test_hit_audit_event_requires_candidate_fields(
    candidate_record_id: str | None,
    candidate_response_fingerprint: str | None,
    match_mode: str | None,
    expected: str,
) -> None:
    audit = _audit_event()
    with pytest.raises(ValueError, match=expected):
        CacheLookupAuditEvent(
            audit_event_id="audit:malformed",
            idempotency_key="idempotency:malformed",
            surface=audit.surface,
            request_fingerprint=audit.request_fingerprint,
            candidate_record_id=candidate_record_id,
            candidate_response_fingerprint=candidate_response_fingerprint,
            lookup_decision="hit",
            match_mode=match_mode,
            policy_version=audit.policy_version,
            provider_key=audit.provider_key,
            model_key=audit.model_key,
            user_tier=audit.user_tier,
            context_fingerprint=audit.context_fingerprint,
            transparency_notice_id=audit.transparency_notice_id,
            source_fingerprints=audit.source_fingerprints,
            eval_event_ids=audit.eval_event_ids,
            admission_decision_id=audit.admission_decision_id,
            promotion_ids=audit.promotion_ids,
            replay_entry_ids=audit.replay_entry_ids,
            reason_codes=("candidate_hit",),
            produced_at=PRODUCED_AT,
            metadata={},
        )


def test_miss_audit_event_rejects_candidate_fields() -> None:
    audit = _miss_audit_event()

    with pytest.raises(ValueError, match="miss audit events must not carry candidate fields"):
        CacheLookupAuditEvent(
            audit_event_id="audit:miss",
            idempotency_key="idempotency:miss",
            surface=audit.surface,
            request_fingerprint=audit.request_fingerprint,
            candidate_record_id="record:unexpected",
            candidate_response_fingerprint=None,
            lookup_decision=audit.lookup_decision,
            match_mode=None,
            policy_version=audit.policy_version,
            provider_key=audit.provider_key,
            model_key=audit.model_key,
            user_tier=audit.user_tier,
            context_fingerprint=audit.context_fingerprint,
            transparency_notice_id=audit.transparency_notice_id,
            source_fingerprints=audit.source_fingerprints,
            eval_event_ids=audit.eval_event_ids,
            admission_decision_id=audit.admission_decision_id,
            promotion_ids=audit.promotion_ids,
            replay_entry_ids=audit.replay_entry_ids,
            reason_codes=audit.reason_codes,
            produced_at=PRODUCED_AT,
            metadata={},
        )


def test_miss_audit_event_rejects_hit_like_match_mode() -> None:
    audit = _miss_audit_event()

    with pytest.raises(ValueError, match="miss audit events must not carry match_mode"):
        CacheLookupAuditEvent(
            audit_event_id="audit:miss-mode",
            idempotency_key="idempotency:miss-mode",
            surface=audit.surface,
            request_fingerprint=audit.request_fingerprint,
            candidate_record_id=None,
            candidate_response_fingerprint=None,
            lookup_decision=audit.lookup_decision,
            match_mode="exact",
            policy_version=audit.policy_version,
            provider_key=audit.provider_key,
            model_key=audit.model_key,
            user_tier=audit.user_tier,
            context_fingerprint=audit.context_fingerprint,
            transparency_notice_id=audit.transparency_notice_id,
            source_fingerprints=audit.source_fingerprints,
            eval_event_ids=audit.eval_event_ids,
            admission_decision_id=audit.admission_decision_id,
            promotion_ids=audit.promotion_ids,
            replay_entry_ids=audit.replay_entry_ids,
            reason_codes=audit.reason_codes,
            produced_at=PRODUCED_AT,
            metadata={},
        )


def test_build_audit_event_rejects_mismatched_or_malformed_inputs() -> None:
    result = match_exact_fuzzy_records(
        request=_request(),
        candidate_records=(_record(),),
        policy=_policy(),
    )

    with pytest.raises(ValueError, match="candidate_record is required"):
        build_cache_lookup_audit_event(
            request=_request(),
            lookup_result=result,
            candidate_record=None,
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="candidate_record must be omitted"):
        build_cache_lookup_audit_event(
            request=_request("missing"),
            lookup_result=match_exact_fuzzy_records(
                request=_request("missing"),
                candidate_records=(),
                policy=_policy(),
            ),
            candidate_record=_record(),
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="must match"):
        build_cache_lookup_audit_event(
            request=_request(),
            lookup_result=result,
            candidate_record=replace(_record(), record_id="cache-record:mismatch"),
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="request must be ExactFuzzyCacheLookupRequest"):
        build_cache_lookup_audit_event(
            request=cast(ExactFuzzyCacheLookupRequest, "not-request"),
            lookup_result=result,
            candidate_record=_record(),
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="lookup_result must be ExactFuzzyCacheLookupResult"):
        build_cache_lookup_audit_event(
            request=_request(),
            lookup_result=cast(ExactFuzzyCacheLookupResult, "not-result"),
            candidate_record=_record(),
            produced_at=PRODUCED_AT,
        )


def test_case_and_evaluation_contracts_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="unsupported risk_class"):
        _case(risk_class="semantic_runtime_hit")
    with pytest.raises(ValueError, match="unsupported expected_action"):
        _case(expected_action="serve")
    with pytest.raises(ValueError, match="audit_event must be CacheLookupAuditEvent"):
        FalseHitHarnessCase(
            case_id="case:bad-audit",
            risk_class="blocked_surface_hit",
            audit_event=cast(CacheLookupAuditEvent, "not-audit"),
            expected_action=EXPECTED_ACTION_FALLBACK,
            fresh_response_fingerprint=None,
            current_source_fingerprints=("sha256:source-a",),
            current_policy_version="semantic-cache-sc-g3-v1",
            current_model_key="model:test",
            current_user_tier="pro",
            current_context_fingerprint="sha256:context",
            admission_allowed=False,
            blocked_surface=True,
            negative_control=True,
            metadata={},
        )
    with pytest.raises(ValueError, match="unsupported outcome_class"):
        FalseHitHarnessEvaluation(
            evaluation_id="eval:bad",
            case_id="case:bad",
            allowed=False,
            outcome_class="serve",
            is_false_hit=False,
            reason_codes=("candidate_miss",),
            blocking_reasons=(),
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="case must be FalseHitHarnessCase"):
        evaluate_false_hit_case(case=cast(FalseHitHarnessCase, "not-case"), produced_at=PRODUCED_AT)


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        (
            _case(
                risk_class="stale_source_hit",
                current_source_fingerprints=("sha256:source-a", "sha256:source-new"),
            ),
            REASON_STALE_SOURCE,
        ),
        (
            _case(
                risk_class="policy_version_mismatch_hit",
                current_policy_version="semantic-cache-sc-g3-v2",
            ),
            REASON_POLICY_MISMATCH,
        ),
        (
            _case(risk_class="model_version_mismatch_hit", current_model_key="model:next"),
            REASON_MODEL_MISMATCH,
        ),
        (
            _case(risk_class="user_context_leakage_hit", current_user_tier="free"),
            REASON_CONTEXT_LEAKAGE,
        ),
        (
            _case(risk_class="admission_blocked_hit", admission_allowed=False),
            REASON_ADMISSION_BLOCKED,
        ),
        (
            _case(risk_class="blocked_surface_hit", blocked_surface=True),
            REASON_BLOCKED_SURFACE,
        ),
    ],
)
def test_false_hit_evaluation_blocks_required_risk_classes(
    case: FalseHitHarnessCase,
    reason: str,
) -> None:
    evaluation = evaluate_false_hit_case(case=case, produced_at=PRODUCED_AT)

    assert evaluation.allowed is False
    assert evaluation.is_false_hit is True
    assert evaluation.outcome_class == "false_hit"
    assert reason in evaluation.blocking_reasons


def test_response_fingerprint_mismatch_blocks_candidate_hit() -> None:
    evaluation = evaluate_false_hit_case(
        case=_case(
            risk_class="semantic_false_positive",
            fresh_response_fingerprint="sha256:fresh-response",
        ),
        produced_at=PRODUCED_AT,
    )

    assert evaluation.allowed is False
    assert evaluation.is_false_hit is True
    assert REASON_RESPONSE_FINGERPRINT_MISMATCH in evaluation.blocking_reasons


def test_candidate_miss_with_fallback_action_remains_fallback() -> None:
    case = FalseHitHarnessCase(
        case_id="case:miss",
        risk_class="semantic_false_positive",
        audit_event=_miss_audit_event(),
        expected_action=EXPECTED_ACTION_FALLBACK,
        fresh_response_fingerprint=None,
        current_source_fingerprints=("sha256:source-a", "sha256:source-b"),
        current_policy_version="semantic-cache-sc-g3-v1",
        current_model_key="model:test",
        current_user_tier="pro",
        current_context_fingerprint="sha256:context",
        admission_allowed=True,
        blocked_surface=False,
        negative_control=True,
        metadata={"case": "miss"},
    )

    evaluation = evaluate_false_hit_case(case=case, produced_at=PRODUCED_AT)

    assert evaluation.allowed is False
    assert evaluation.is_false_hit is False
    assert evaluation.outcome_class == "fallback"


def test_negative_control_blocks_safe_hit_even_if_expected_safe() -> None:
    evaluation = evaluate_false_hit_case(
        case=_case(
            case_id="case:negative-safe",
            risk_class="semantic_false_positive",
            expected_action=EXPECTED_ACTION_SAFE_HIT,
            negative_control=True,
        ),
        produced_at=PRODUCED_AT,
    )

    assert evaluation.allowed is False
    assert evaluation.is_false_hit is True
    assert evaluation.outcome_class == "false_hit"
    assert "fallback_required" in evaluation.blocking_reasons


def test_negative_control_case_ordering_is_deterministic() -> None:
    cases = (
        _case(
            case_id="case:z",
            risk_class="semantic_false_positive",
            expected_action=EXPECTED_ACTION_FALLBACK,
            negative_control=True,
        ),
        _case(case_id="case:a", risk_class="normalized_fuzzy_hit"),
    )

    evaluations = evaluate_false_hit_harness(cases=cases, produced_at=PRODUCED_AT)

    assert tuple(item.case_id for item in evaluations) == ("case:a", "case:z")
    assert evaluations[1].is_false_hit is True


def test_metrics_snapshot_counts_and_basis_point_rates() -> None:
    evaluations = (
        evaluate_false_hit_case(case=_case(case_id="case:safe"), produced_at=PRODUCED_AT),
        evaluate_false_hit_case(
            case=_case(
                case_id="case:stale",
                risk_class="stale_source_hit",
                current_source_fingerprints=("sha256:source-a", "sha256:source-new"),
            ),
            produced_at=PRODUCED_AT,
        ),
    )

    metrics = compute_cache_observability_metrics(
        evaluations=evaluations,
        produced_at=PRODUCED_AT,
        latency_saved_ms=(40, 10, 30, 20),
        provider_calls_avoided_count=1,
        cost_saved_microunits=250,
    )

    assert metrics.eligible_request_count == 2
    assert metrics.candidate_hit_count == 2
    assert metrics.safe_hit_count == 1
    assert metrics.false_hit_count == 1
    assert metrics.eligible_hit_rate_bps == 10000
    assert metrics.false_hit_rate_bps == 5000
    assert metrics.cache_precision_proxy_bps == 5000
    assert metrics.stale_answer_rate_bps == 5000
    assert metrics.latency_saved_p50_ms == 20
    assert metrics.latency_saved_p95_ms == 40


def test_zero_denominator_rates_are_deterministic_zero() -> None:
    metrics = compute_cache_observability_metrics(evaluations=(), produced_at=PRODUCED_AT)

    assert metrics.eligible_request_count == 0
    assert metrics.eligible_hit_rate_bps == 0
    assert metrics.false_hit_rate_bps == 0
    assert metrics.cache_precision_proxy_bps == 0


def test_token_economy_estimate_is_deterministic_and_metadata_only() -> None:
    first = build_token_economy_estimate(
        surface="orchestration",
        route_type="review",
        provider_label="gpt-family",
        model_label="frontier",
        token_estimate_version="heuristic-tokens-v1",
        prompt_input_chars=1200,
        prompt_output_chars=300,
        prompt_input_tokens_estimate=300,
        prompt_output_tokens_estimate=75,
        baseline_context_tokens_estimate=900,
        candidate_context_tokens_estimate=600,
        tokens_saved_estimate=300,
        orchestration_fanout_multiplier=4,
        provider_calls_avoided_count=0,
        cost_saved_microunits=0,
        cost_estimate_policy_version="not-billing-truth-v1",
        currency_code="XXX",
        reason_codes=("metadata_recorded", "gate_closed"),
        produced_at=PRODUCED_AT,
        metadata={"estimate": "heuristic"},
    )
    second = build_token_economy_estimate(
        surface="orchestration",
        route_type="review",
        provider_label="gpt-family",
        model_label="frontier",
        token_estimate_version="heuristic-tokens-v1",
        prompt_input_chars=1200,
        prompt_output_chars=300,
        prompt_input_tokens_estimate=300,
        prompt_output_tokens_estimate=75,
        baseline_context_tokens_estimate=900,
        candidate_context_tokens_estimate=600,
        tokens_saved_estimate=300,
        orchestration_fanout_multiplier=4,
        provider_calls_avoided_count=0,
        cost_saved_microunits=0,
        cost_estimate_policy_version="not-billing-truth-v1",
        currency_code="XXX",
        reason_codes=("gate_closed", "metadata_recorded"),
        produced_at=PRODUCED_AT,
        metadata={"estimate": "heuristic"},
    )

    assert first.estimate_id == second.estimate_id
    serialized = json.dumps(dict(to_stable_mapping(first)), sort_keys=True)
    assert "private prompt text" not in serialized
    assert "tokens_saved_estimate" in serialized
    assert "cost_saved_microunits" in serialized
    assert first.cost_saved_microunits == 0
    assert first.tokens_saved_estimate == 300


def test_token_economy_estimate_identity_includes_material_estimate_fields() -> None:
    baseline = build_token_economy_estimate(
        surface="orchestration",
        route_type="review",
        provider_label="gpt-family",
        model_label="frontier",
        token_estimate_version="heuristic-tokens-v1",
        prompt_input_chars=1200,
        prompt_output_chars=300,
        prompt_input_tokens_estimate=300,
        prompt_output_tokens_estimate=75,
        baseline_context_tokens_estimate=900,
        candidate_context_tokens_estimate=600,
        tokens_saved_estimate=300,
        orchestration_fanout_multiplier=4,
        provider_calls_avoided_count=0,
        cost_saved_microunits=0,
        cost_estimate_policy_version="not-billing-truth-v1",
        currency_code="XXX",
        reason_codes=("metadata_recorded", "gate_closed"),
        produced_at=PRODUCED_AT,
        metadata={},
    )
    materially_different = build_token_economy_estimate(
        surface="orchestration",
        route_type="review",
        provider_label="gpt-family",
        model_label="frontier",
        token_estimate_version="heuristic-tokens-v1",
        prompt_input_chars=1201,
        prompt_output_chars=301,
        prompt_input_tokens_estimate=301,
        prompt_output_tokens_estimate=76,
        baseline_context_tokens_estimate=901,
        candidate_context_tokens_estimate=601,
        tokens_saved_estimate=300,
        orchestration_fanout_multiplier=5,
        provider_calls_avoided_count=1,
        cost_saved_microunits=1,
        cost_estimate_policy_version="not-billing-truth-v1",
        currency_code="XXX",
        reason_codes=("gate_closed", "metadata_recorded"),
        produced_at=PRODUCED_AT,
        metadata={},
    )

    assert baseline.estimate_id != materially_different.estimate_id


def test_token_economy_estimate_hashes_normalized_reason_codes() -> None:
    baseline = build_token_economy_estimate(
        surface="orchestration",
        route_type="review",
        provider_label="gpt-family",
        model_label="frontier",
        token_estimate_version="heuristic-tokens-v1",
        prompt_input_chars=1200,
        prompt_output_chars=300,
        prompt_input_tokens_estimate=300,
        prompt_output_tokens_estimate=75,
        baseline_context_tokens_estimate=900,
        candidate_context_tokens_estimate=600,
        tokens_saved_estimate=300,
        orchestration_fanout_multiplier=4,
        provider_calls_avoided_count=0,
        cost_saved_microunits=0,
        cost_estimate_policy_version="not-billing-truth-v1",
        currency_code="XXX",
        reason_codes=("metadata_recorded", "gate_closed"),
        produced_at=PRODUCED_AT,
        metadata={},
    )
    normalized = build_token_economy_estimate(
        surface=" orchestration ",
        route_type=" review ",
        provider_label=" gpt-family ",
        model_label=" frontier ",
        token_estimate_version=" heuristic-tokens-v1 ",
        prompt_input_chars=1200,
        prompt_output_chars=300,
        prompt_input_tokens_estimate=300,
        prompt_output_tokens_estimate=75,
        baseline_context_tokens_estimate=900,
        candidate_context_tokens_estimate=600,
        tokens_saved_estimate=300,
        orchestration_fanout_multiplier=4,
        provider_calls_avoided_count=0,
        cost_saved_microunits=0,
        cost_estimate_policy_version=" not-billing-truth-v1 ",
        currency_code=" XXX ",
        reason_codes=(" gate_closed ", " metadata_recorded "),
        produced_at=PRODUCED_AT,
        metadata={},
    )

    assert baseline.reason_codes == normalized.reason_codes
    assert baseline.estimate_id == normalized.estimate_id


def test_token_economy_estimate_metadata_is_deep_frozen_after_validation() -> None:
    estimate = build_token_economy_estimate(
        surface="orchestration",
        route_type="review",
        provider_label="gpt-family",
        model_label="frontier",
        token_estimate_version="heuristic-tokens-v1",
        prompt_input_chars=1200,
        prompt_output_chars=300,
        prompt_input_tokens_estimate=300,
        prompt_output_tokens_estimate=75,
        baseline_context_tokens_estimate=900,
        candidate_context_tokens_estimate=600,
        tokens_saved_estimate=300,
        orchestration_fanout_multiplier=4,
        provider_calls_avoided_count=0,
        cost_saved_microunits=0,
        cost_estimate_policy_version="not-billing-truth-v1",
        currency_code="XXX",
        reason_codes=("metadata_recorded", "gate_closed"),
        produced_at=PRODUCED_AT,
        metadata={"nested": {"safe": ["label"]}},
    )
    nested = cast(MutableMapping[str, JsonValue], estimate.metadata["nested"])
    safe_values = cast(list[JsonValue], nested["safe"])

    with pytest.raises(TypeError):
        nested["raw_prompt"] = "unsafe"
    with pytest.raises(AttributeError):
        safe_values.append("/Users/private/path")

    assert dict(to_stable_mapping(estimate))["metadata"] == {
        "nested": {"safe": ["label"]},
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"provider_label": "provider_payload"},
        {"model_label": "/Users/model"},
        {"tokens_saved_estimate": -1},
        {"prompt_input_tokens_estimate": cast(int, 1.2)},
        {"cost_saved_microunits": -1},
        {"currency_code": "US D"},
        {"reason_codes": ()},
        {"metadata": {"nested": {"raw_response": "unsafe"}}},
        {"metadata": {"provider_payload": "unsafe"}},
        {"metadata": {"path": "file:///tmp/raw.txt"}},
    ],
)
def test_token_economy_estimate_fails_closed_for_unsafe_inputs(
    kwargs: dict[str, object],
) -> None:
    payload: dict[str, object] = {
        "surface": "orchestration",
        "route_type": "review",
        "provider_label": "gpt-family",
        "model_label": "frontier",
        "token_estimate_version": "heuristic-tokens-v1",
        "prompt_input_chars": 1200,
        "prompt_output_chars": 300,
        "prompt_input_tokens_estimate": 300,
        "prompt_output_tokens_estimate": 75,
        "baseline_context_tokens_estimate": 900,
        "candidate_context_tokens_estimate": 600,
        "tokens_saved_estimate": 300,
        "orchestration_fanout_multiplier": 4,
        "provider_calls_avoided_count": 0,
        "cost_saved_microunits": 0,
        "cost_estimate_policy_version": "not-billing-truth-v1",
        "currency_code": "XXX",
        "reason_codes": ("metadata_recorded", "gate_closed"),
        "produced_at": PRODUCED_AT,
        "metadata": {},
    }
    payload.update(kwargs)

    with pytest.raises(ValueError):
        build_token_economy_estimate(**payload)


def test_token_economy_estimate_constructor_rejects_bool_fields() -> None:
    with pytest.raises(ValueError, match="must be an integer"):
        TokenEconomyEstimate(
            estimate_id="token-economy:bad",
            surface="orchestration",
            route_type="review",
            provider_label="gpt-family",
            model_label="frontier",
            token_estimate_version="heuristic-tokens-v1",
            prompt_input_chars=cast(int, True),
            prompt_output_chars=0,
            prompt_input_tokens_estimate=0,
            prompt_output_tokens_estimate=0,
            baseline_context_tokens_estimate=0,
            candidate_context_tokens_estimate=0,
            tokens_saved_estimate=0,
            orchestration_fanout_multiplier=0,
            provider_calls_avoided_count=0,
            cost_saved_microunits=0,
            cost_estimate_policy_version="not-billing-truth-v1",
            currency_code="XXX",
            reason_codes=("metadata_recorded",),
            produced_at=PRODUCED_AT,
            metadata={},
        )


def test_stop_rule_triggers_rollback_on_threshold_breach() -> None:
    evaluation = evaluate_false_hit_case(
        case=_case(
            risk_class="stale_source_hit",
            current_source_fingerprints=("sha256:source-a", "sha256:source-new"),
        ),
        produced_at=PRODUCED_AT,
    )
    metrics = compute_cache_observability_metrics(
        evaluations=(evaluation,),
        produced_at=PRODUCED_AT,
    )
    decision = evaluate_cache_stop_rules(
        metrics=metrics,
        stop_rules=CacheStopRules(
            policy_version="semantic-cache-sc-g3-v1",
            max_false_hit_rate_bps=0,
            max_stale_answer_rate_bps=0,
            max_policy_mismatch_hits=0,
            max_model_mismatch_hits=0,
            max_context_leakage_hits=0,
            allow_blocked_surface_hits=False,
        ),
        produced_at=PRODUCED_AT,
    )

    assert decision.stop_serving is True
    assert decision.rollback_required is True
    assert "false_hit_rate_threshold_breached" in decision.reason_codes
    assert "stale_answer_rate_threshold_breached" in decision.reason_codes


def test_stop_rules_cover_policy_model_context_blocked_surface_and_clear_paths() -> None:
    evaluations = (
        evaluate_false_hit_case(
            case=_case(
                risk_class="policy_version_mismatch_hit", current_policy_version="policy:v2"
            ),
            produced_at=PRODUCED_AT,
        ),
        evaluate_false_hit_case(
            case=_case(risk_class="model_version_mismatch_hit", current_model_key="model:next"),
            produced_at=PRODUCED_AT,
        ),
        evaluate_false_hit_case(
            case=_case(
                risk_class="user_context_leakage_hit", current_context_fingerprint="ctx:next"
            ),
            produced_at=PRODUCED_AT,
        ),
        evaluate_false_hit_case(
            case=_case(risk_class="blocked_surface_hit", blocked_surface=True),
            produced_at=PRODUCED_AT,
        ),
    )
    metrics = compute_cache_observability_metrics(evaluations=evaluations, produced_at=PRODUCED_AT)
    decision = evaluate_cache_stop_rules(
        metrics=metrics,
        stop_rules=CacheStopRules(
            policy_version="semantic-cache-sc-g3-v1",
            max_false_hit_rate_bps=10000,
            max_stale_answer_rate_bps=10000,
            max_policy_mismatch_hits=0,
            max_model_mismatch_hits=0,
            max_context_leakage_hits=0,
            allow_blocked_surface_hits=False,
        ),
        produced_at=PRODUCED_AT,
    )

    assert "policy_mismatch_hit_threshold_breached" in decision.reason_codes
    assert "model_mismatch_hit_threshold_breached" in decision.reason_codes
    assert "context_leakage_hit_threshold_breached" in decision.reason_codes
    assert "blocked_surface_hit_detected" in decision.reason_codes

    clear = evaluate_cache_stop_rules(
        metrics=compute_cache_observability_metrics(
            evaluations=(evaluate_false_hit_case(case=_case(), produced_at=PRODUCED_AT),),
            produced_at=PRODUCED_AT,
        ),
        stop_rules=CacheStopRules(
            policy_version="semantic-cache-sc-g3-v1",
            max_false_hit_rate_bps=10000,
            max_stale_answer_rate_bps=10000,
            max_policy_mismatch_hits=0,
            max_model_mismatch_hits=0,
            max_context_leakage_hits=0,
            allow_blocked_surface_hits=False,
        ),
        produced_at=PRODUCED_AT,
    )
    assert clear.stop_serving is False
    assert clear.rollback_required is False
    assert clear.reason_codes == ("stop_rules_clear",)


def test_kill_switch_snapshot_disables_hypothetical_serving() -> None:
    evaluation = evaluate_false_hit_case(
        case=_case(),
        produced_at=PRODUCED_AT,
        kill_switch_snapshot=KillSwitchSnapshot(
            environment_enabled=False,
            runtime_enabled=True,
            request_disabled=False,
            bypass_forced=False,
        ),
    )

    assert evaluation.allowed is False
    assert evaluation.is_false_hit is False
    assert evaluation.outcome_class == "fallback"
    assert REASON_KILL_SWITCH_DISABLED in evaluation.blocking_reasons


def test_non_finite_and_invalid_numeric_inputs_fail_closed() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        build_cache_lookup_audit_event(
            request=_request(),
            lookup_result=match_exact_fuzzy_records(
                request=_request(),
                candidate_records=(_record(),),
                policy=_policy(),
            ),
            candidate_record=_record(),
            produced_at=PRODUCED_AT,
            metadata={"score": float("nan")},
        )
    with pytest.raises(ValueError, match="non-negative"):
        compute_cache_observability_metrics(
            evaluations=(),
            produced_at=PRODUCED_AT,
            latency_saved_ms=(-1,),
        )


def test_metrics_and_stop_contracts_reject_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="between 0 and 10000"):
        CacheObservabilityMetrics(
            metrics_id="metrics:bad",
            eligible_request_count=1,
            candidate_hit_count=1,
            safe_hit_count=1,
            false_hit_count=0,
            fallback_count=0,
            bypass_count=0,
            kill_switch_disabled_count=0,
            admission_blocked_hit_count=0,
            stale_source_hit_count=0,
            policy_mismatch_hit_count=0,
            model_mismatch_hit_count=0,
            context_leakage_hit_count=0,
            blocked_surface_hit_count=0,
            eligible_hit_rate_bps=10001,
            served_hit_rate_bps=10000,
            false_hit_rate_bps=0,
            cache_precision_proxy_bps=10000,
            stale_answer_rate_bps=0,
            fallback_rate_bps=0,
            bypass_rate_bps=0,
            latency_saved_p50_ms=0,
            latency_saved_p95_ms=0,
            provider_calls_avoided_count=0,
            cost_saved_microunits=0,
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="must be bool"):
        CacheStopRules(
            policy_version="semantic-cache-sc-g3-v1",
            max_false_hit_rate_bps=0,
            max_stale_answer_rate_bps=0,
            max_policy_mismatch_hits=0,
            max_model_mismatch_hits=0,
            max_context_leakage_hits=0,
            allow_blocked_surface_hits=cast(bool, "false"),
        )
    with pytest.raises(ValueError, match="must be bool"):
        CacheStopDecision(
            decision_id="decision:bad",
            stop_serving=cast(bool, "true"),
            rollback_required=True,
            reason_codes=("rollback",),
            produced_at=PRODUCED_AT,
        )
    metrics = compute_cache_observability_metrics(evaluations=(), produced_at=PRODUCED_AT)
    rules = CacheStopRules(
        policy_version="semantic-cache-sc-g3-v1",
        max_false_hit_rate_bps=0,
        max_stale_answer_rate_bps=0,
        max_policy_mismatch_hits=0,
        max_model_mismatch_hits=0,
        max_context_leakage_hits=0,
        allow_blocked_surface_hits=False,
    )
    with pytest.raises(ValueError, match="metrics must be CacheObservabilityMetrics"):
        evaluate_cache_stop_rules(
            metrics=cast(CacheObservabilityMetrics, "not-metrics"),
            stop_rules=rules,
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="stop_rules must be CacheStopRules"):
        evaluate_cache_stop_rules(
            metrics=metrics,
            stop_rules=cast(CacheStopRules, "not-rules"),
            produced_at=PRODUCED_AT,
        )


def test_unsafe_metadata_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsafe metadata"):
        build_cache_lookup_audit_event(
            request=_request(),
            lookup_result=match_exact_fuzzy_records(
                request=_request(),
                candidate_records=(_record(),),
                policy=_policy(),
            ),
            candidate_record=_record(),
            produced_at=PRODUCED_AT,
            metadata={"raw_prompt": "cache this prompt"},
        )
    with pytest.raises(ValueError, match="unsafe metadata"):
        FalseHitHarnessCase(
            case_id="case:unsafe",
            risk_class="blocked_surface_hit",
            audit_event=_audit_event(),
            expected_action=EXPECTED_ACTION_FALLBACK,
            fresh_response_fingerprint=None,
            current_source_fingerprints=("sha256:source-a", "sha256:source-b"),
            current_policy_version="semantic-cache-sc-g3-v1",
            current_model_key="model:test",
            current_user_tier="pro",
            current_context_fingerprint="sha256:context",
            admission_allowed=False,
            blocked_surface=True,
            negative_control=True,
            metadata={"artifact": "/tmp/raw-response.txt"},
        )
    for metadata in (
        {"authorization": "Basic abc"},
        {"header": "Bearer secret"},
        {"api-key": "sk-test"},
        {"github": "ghs_header.payload.signature"},
        {"github": "ghs_header-payload.signature-with-hyphen"},
        {"github": "github_pat_header.payload-signature"},
        {"cookie": "session=abc"},
        {"contact": "user@example.com"},
        {"phone": "+1 555 123 4567"},
    ):
        with pytest.raises(ValueError, match="unsafe metadata"):
            build_cache_lookup_audit_event(
                request=_request(),
                lookup_result=match_exact_fuzzy_records(
                    request=_request(),
                    candidate_records=(_record(),),
                    policy=_policy(),
                ),
                candidate_record=_record(),
                produced_at=PRODUCED_AT,
                metadata=metadata,
            )


def test_metadata_accepts_safe_nested_json_and_rejects_bad_shapes() -> None:
    audit = build_cache_lookup_audit_event(
        request=_request(),
        lookup_result=match_exact_fuzzy_records(
            request=_request(),
            candidate_records=(_record(),),
            policy=_policy(),
        ),
        candidate_record=_record(),
        produced_at=PRODUCED_AT,
        metadata=cast(SafeMetadata, {"safe": ("tag",), "count": 1, "ratio": 0.5, "enabled": True}),
    )
    assert dict(to_stable_mapping(audit))["metadata"] == {
        "count": 1,
        "enabled": True,
        "ratio": 0.5,
        "safe": ["tag"],
    }
    with pytest.raises(ValueError, match="unsupported value"):
        build_cache_lookup_audit_event(
            request=_request(),
            lookup_result=match_exact_fuzzy_records(
                request=_request(),
                candidate_records=(_record(),),
                policy=_policy(),
            ),
            candidate_record=_record(),
            produced_at=PRODUCED_AT,
            metadata=cast(SafeMetadata, {"bad": object()}),
        )
    with pytest.raises(ValueError, match="metadata must be a mapping"):
        FalseHitHarnessCase(
            case_id="case:metadata-shape",
            risk_class="blocked_surface_hit",
            audit_event=_audit_event(),
            expected_action=EXPECTED_ACTION_FALLBACK,
            fresh_response_fingerprint=None,
            current_source_fingerprints=("sha256:source-a",),
            current_policy_version="semantic-cache-sc-g3-v1",
            current_model_key="model:test",
            current_user_tier="pro",
            current_context_fingerprint="sha256:context",
            admission_allowed=False,
            blocked_surface=True,
            negative_control=True,
            metadata=cast(SafeMetadata, ["bad"]),
        )


def test_low_level_validators_fail_closed_through_contracts() -> None:
    with pytest.raises(ValueError, match="reason_codes must be non-empty"):
        CacheStopDecision(
            decision_id="decision:empty-reasons",
            stop_serving=False,
            rollback_required=False,
            reason_codes=(),
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="duplicate entries"):
        CacheStopDecision(
            decision_id="decision:duplicate",
            stop_serving=False,
            rollback_required=False,
            reason_codes=("same", "same"),
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="must be non-empty"):
        CacheStopDecision(
            decision_id=" ",
            stop_serving=False,
            rollback_required=False,
            reason_codes=("clear",),
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="must not contain whitespace"):
        CacheStopDecision(
            decision_id="decision:has space",
            stop_serving=False,
            rollback_required=False,
            reason_codes=("clear",),
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="unsupported characters"):
        CacheStopDecision(
            decision_id="decision:bad!",
            stop_serving=False,
            rollback_required=False,
            reason_codes=("clear",),
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="produced_at"):
        CacheStopDecision(
            decision_id="decision:bad-time",
            stop_serving=False,
            rollback_required=False,
            reason_codes=("clear",),
            produced_at="2026-05-07",
        )
    with pytest.raises(ValueError, match="must be an integer"):
        CacheObservabilityMetrics(
            metrics_id="metrics:bad-count",
            eligible_request_count=cast(int, 1.2),
            candidate_hit_count=0,
            safe_hit_count=0,
            false_hit_count=0,
            fallback_count=0,
            bypass_count=0,
            kill_switch_disabled_count=0,
            admission_blocked_hit_count=0,
            stale_source_hit_count=0,
            policy_mismatch_hit_count=0,
            model_mismatch_hit_count=0,
            context_leakage_hit_count=0,
            blocked_surface_hit_count=0,
            eligible_hit_rate_bps=0,
            served_hit_rate_bps=0,
            false_hit_rate_bps=0,
            cache_precision_proxy_bps=0,
            stale_answer_rate_bps=0,
            fallback_rate_bps=0,
            bypass_rate_bps=0,
            latency_saved_p50_ms=0,
            latency_saved_p95_ms=0,
            provider_calls_avoided_count=0,
            cost_saved_microunits=0,
            produced_at=PRODUCED_AT,
        )
    with pytest.raises(ValueError, match="unsupported percentile"):
        cache_observability._percentile_ms((1, 2, 3), 99)


def test_caller_owned_containers_are_defensively_copied() -> None:
    tags: list[JsonValue] = ["safe"]
    metadata: dict[str, JsonValue] = {"tags": tags}
    audit = build_cache_lookup_audit_event(
        request=_request(),
        lookup_result=match_exact_fuzzy_records(
            request=_request(),
            candidate_records=(_record(),),
            policy=_policy(),
        ),
        candidate_record=_record(),
        produced_at=PRODUCED_AT,
        metadata=metadata,
    )
    tags.append("changed")

    assert dict(to_stable_mapping(audit))["metadata"] == {"tags": ["safe"]}
    case = _case(case_id="case:copy", metadata=metadata)
    tags.append("changed-again")
    assert dict(case.metadata) == {"tags": ("safe", "changed")}
    with pytest.raises(AttributeError):
        cast(list[JsonValue], case.metadata["tags"]).append("unsafe")


def test_stable_mapping_covers_all_contract_shapes_and_rejects_unknowns() -> None:
    evaluation = evaluate_false_hit_case(case=_case(), produced_at=PRODUCED_AT)
    metrics = compute_cache_observability_metrics(
        evaluations=(evaluation,), produced_at=PRODUCED_AT
    )
    decision = evaluate_cache_stop_rules(
        metrics=metrics,
        stop_rules=CacheStopRules(
            policy_version="semantic-cache-sc-g3-v1",
            max_false_hit_rate_bps=10000,
            max_stale_answer_rate_bps=10000,
            max_policy_mismatch_hits=0,
            max_model_mismatch_hits=0,
            max_context_leakage_hits=0,
            allow_blocked_surface_hits=False,
        ),
        produced_at=PRODUCED_AT,
    )

    assert dict(to_stable_mapping(evaluation))["evaluation_id"] == evaluation.evaluation_id
    assert dict(to_stable_mapping(metrics))["metrics_id"] == metrics.metrics_id
    assert (
        dict(
            to_stable_mapping(
                build_token_economy_estimate(
                    surface="orchestration",
                    route_type="review",
                    provider_label="gpt-family",
                    model_label="frontier",
                    token_estimate_version="heuristic-tokens-v1",
                    prompt_input_chars=0,
                    prompt_output_chars=0,
                    prompt_input_tokens_estimate=0,
                    prompt_output_tokens_estimate=0,
                    baseline_context_tokens_estimate=0,
                    candidate_context_tokens_estimate=0,
                    tokens_saved_estimate=0,
                    orchestration_fanout_multiplier=0,
                    provider_calls_avoided_count=0,
                    cost_saved_microunits=0,
                    cost_estimate_policy_version="not-billing-truth-v1",
                    currency_code="XXX",
                    reason_codes=("metadata_recorded",),
                    produced_at=PRODUCED_AT,
                )
            )
        )["tokens_saved_estimate"]
        == 0
    )
    assert dict(to_stable_mapping(decision))["decision_id"] == decision.decision_id
    assert dict(to_stable_mapping(KillSwitchSnapshot(True, True, False, False))) == {
        "bypass_forced": False,
        "environment_enabled": True,
        "request_disabled": False,
        "runtime_enabled": True,
    }
    with pytest.raises(ValueError, match="unsupported stable mapping"):
        to_stable_mapping({"not": "a contract"})


def test_module_has_no_forbidden_imports_or_nondeterministic_calls() -> None:
    assert_no_forbidden_semantic_cache_imports(MODULE)
    assert_no_forbidden_semantic_cache_calls(MODULE)


def test_import_guard_rejects_runtime_cache_modules(tmp_path: Path) -> None:
    unsafe = tmp_path / "unsafe_cache_import.py"
    unsafe.write_text("import core.ai.cache_runtime\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="core.ai.cache_runtime"):
        assert_no_forbidden_semantic_cache_imports(unsafe)


def test_import_guard_allows_sc_g2_qualified_symbols(tmp_path: Path) -> None:
    source = tmp_path / "allowed_sc_g2_import.py"
    source.write_text(
        "from core.ai.exact_fuzzy_cache import create_exact_fuzzy_cache_record\n",
        encoding="utf-8",
    )

    assert_no_forbidden_semantic_cache_imports(source)


def test_sc_g3_is_not_exported_from_core_ai_facade() -> None:
    init_path = REPO_ROOT / "core" / "ai" / "__init__.py"
    assert "cache_observability" not in init_path.read_text(encoding="utf-8")
