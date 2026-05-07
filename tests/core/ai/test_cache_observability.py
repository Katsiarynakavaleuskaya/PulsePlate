from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from core.ai.cache_observability import (
    EXPECTED_ACTION_FALLBACK,
    EXPECTED_ACTION_SAFE_HIT,
    REASON_ADMISSION_BLOCKED,
    REASON_BLOCKED_SURFACE,
    REASON_CONTEXT_LEAKAGE,
    REASON_KILL_SWITCH_DISABLED,
    REASON_MODEL_MISMATCH,
    REASON_POLICY_MISMATCH,
    REASON_STALE_SOURCE,
    CacheLookupAuditEvent,
    CacheStopRules,
    FalseHitHarnessCase,
    JsonValue,
    KillSwitchSnapshot,
    build_cache_lookup_audit_event,
    compute_cache_observability_metrics,
    evaluate_cache_stop_rules,
    evaluate_false_hit_case,
    evaluate_false_hit_harness,
    to_stable_mapping,
)
from core.ai.exact_fuzzy_cache import (
    ExactFuzzyCacheLookupRequest,
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
        metadata=metadata or {"case": case_id},
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
    assert evaluation.is_false_hit is True
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
    assert dict(case.metadata) == {"tags": ["safe", "changed"]}


def test_module_has_no_forbidden_imports_or_nondeterministic_calls() -> None:
    assert_no_forbidden_semantic_cache_imports(MODULE)
    assert_no_forbidden_semantic_cache_calls(MODULE)


def test_import_guard_rejects_runtime_cache_modules(tmp_path: Path) -> None:
    unsafe = tmp_path / "unsafe_cache_import.py"
    unsafe.write_text("import core.ai.cache_runtime\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="core.ai.cache_runtime"):
        assert_no_forbidden_semantic_cache_imports(unsafe)


def test_sc_g3_is_not_exported_from_core_ai_facade() -> None:
    init_path = REPO_ROOT / "core" / "ai" / "__init__.py"
    assert "cache_observability" not in init_path.read_text(encoding="utf-8")
