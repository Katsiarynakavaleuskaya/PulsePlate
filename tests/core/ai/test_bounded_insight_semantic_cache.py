from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from core.ai.bounded_insight_semantic_cache import (
    DECISION_EXPERIMENT_ELIGIBLE,
    DECISION_FALLBACK,
    REASON_ADMISSION_BLOCKED,
    REASON_BLOCKED_SURFACE,
    REASON_CONTEXT_MISMATCH,
    REASON_ENVIRONMENT_FLAG_DISABLED,
    REASON_EVIDENCE_LINKAGE_MISSING,
    REASON_EVIDENCE_LINKAGE_MISMATCH,
    REASON_EXPERIMENT_ELIGIBLE,
    REASON_KILL_SWITCH_DISABLED,
    REASON_LOOKUP_MISS,
    REASON_MODEL_MISMATCH,
    REASON_POLICY_MISMATCH,
    REASON_PROVIDER_MISMATCH,
    REASON_REQUEST_DISABLED,
    REASON_REQUEST_NOT_OPTED_IN,
    REASON_RESPONSE_FINGERPRINT_MISMATCH,
    REASON_RUNTIME_FLAG_DISABLED,
    REASON_SOURCE_FINGERPRINT_MISMATCH,
    REASON_STOP_RULE_BLOCKED,
    REASON_TRANSPARENCY_NOTICE_MISMATCH,
    REASON_UNSUPPORTED_SURFACE,
    REASON_USER_TIER_MISMATCH,
    BoundedInsightExperimentCandidate,
    BoundedInsightExperimentDecision,
    BoundedInsightExperimentFlags,
    BoundedInsightExperimentRequest,
    JsonValue,
    evaluate_bounded_insight_experiment,
    to_stable_mapping,
)
from core.ai.cache_observability import (
    EXPECTED_ACTION_SAFE_HIT,
    CacheLookupAuditEvent,
    CacheObservabilityMetrics,
    CacheStopDecision,
    CacheStopRules,
    FalseHitHarnessCase,
    FalseHitHarnessEvaluation,
    KillSwitchSnapshot,
    build_cache_lookup_audit_event,
    compute_cache_observability_metrics,
    evaluate_cache_stop_rules,
    evaluate_false_hit_case,
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
MODULE = REPO_ROOT / "core" / "ai" / "bounded_insight_semantic_cache.py"
PRODUCED_AT = "2026-05-08T12:00:00Z"


def _record() -> ExactFuzzyCacheRecord:
    lineage = build_exact_fuzzy_lineage(
        eval_event_ids=("eval:bounded:1",),
        admission_decision_id="admission:bounded:1",
        promotion_ids=("promotion:bounded:1",),
        replay_entry_ids=("replay:bounded:1",),
        source_fingerprints=("sha256:source-a", "sha256:source-b"),
        policy_version="semantic-cache-sc-g4-v1",
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


def _lookup_request(raw_query: str = "Plan protein breakfast") -> ExactFuzzyCacheLookupRequest:
    return ExactFuzzyCacheLookupRequest(
        surface="insight",
        raw_query=raw_query,
        context_fingerprint="sha256:context",
        source_fingerprints=("sha256:source-a", "sha256:source-b"),
        policy_version="semantic-cache-sc-g4-v1",
        provider_key="provider:test",
        model_key="model:test",
        user_tier="pro",
        transparency_notice_id="notice:insight:v1",
    )


def _policy() -> ExactFuzzyMatchPolicy:
    return ExactFuzzyMatchPolicy(
        policy_version="semantic-cache-sc-g4-v1",
        token_jaccard_min_bps=5000,
        sequence_ratio_min_bps=5000,
        max_token_count_delta=1,
    )


def _request(
    *,
    surface: str = "insight",
    request_fingerprint: str = "cache-request:bounded",
    context_fingerprint: str = "sha256:context",
    source_fingerprints: tuple[str, ...] = ("sha256:source-a", "sha256:source-b"),
    policy_version: str = "semantic-cache-sc-g4-v1",
    provider_key: str = "provider:test",
    model_key: str = "model:test",
    user_tier: str = "pro",
    transparency_notice_id: str = "notice:insight:v1",
    eval_event_ids: tuple[str, ...] = ("eval:bounded:1",),
    admission_decision_id: str | None = "admission:bounded:1",
    promotion_ids: tuple[str, ...] = ("promotion:bounded:1",),
    replay_entry_ids: tuple[str, ...] = ("replay:bounded:1",),
    safety_flags: tuple[str, ...] = ("wellness-only",),
    metadata: Mapping[str, JsonValue] | None = None,
) -> BoundedInsightExperimentRequest:
    return BoundedInsightExperimentRequest(
        surface=surface,
        request_fingerprint=request_fingerprint,
        context_fingerprint=context_fingerprint,
        source_fingerprints=source_fingerprints,
        policy_version=policy_version,
        provider_key=provider_key,
        model_key=model_key,
        user_tier=user_tier,
        transparency_notice_id=transparency_notice_id,
        eval_event_ids=eval_event_ids,
        admission_decision_id=admission_decision_id,
        promotion_ids=promotion_ids,
        replay_entry_ids=replay_entry_ids,
        safety_flags=safety_flags,
        metadata={"scope": "sc-g4"} if metadata is None else metadata,
    )


def _flags(
    *,
    environment_enabled: bool = True,
    runtime_enabled: bool = True,
    request_opt_in: bool = True,
    request_disable: bool = False,
    kill_switch_snapshot: KillSwitchSnapshot | None = None,
) -> BoundedInsightExperimentFlags:
    return BoundedInsightExperimentFlags(
        environment_enabled=environment_enabled,
        runtime_enabled=runtime_enabled,
        request_opt_in=request_opt_in,
        request_disable=request_disable,
        kill_switch_snapshot=(
            KillSwitchSnapshot(True, True, False, False)
            if kill_switch_snapshot is None
            else kill_switch_snapshot
        ),
    )


def _candidate(
    *,
    lookup_request: ExactFuzzyCacheLookupRequest | None = None,
    lookup_result: ExactFuzzyCacheLookupResult | None = None,
    record: ExactFuzzyCacheRecord | None = None,
    audit_event: CacheLookupAuditEvent | None = None,
    false_hit_evaluation: FalseHitHarnessEvaluation | None = None,
    metrics: CacheObservabilityMetrics | None = None,
    stop_decision: CacheStopDecision | None = None,
    response_fingerprint: str | None = None,
    blocked_surface: bool = False,
    admission_allowed: bool = True,
    metadata: Mapping[str, JsonValue] | None = None,
) -> BoundedInsightExperimentCandidate:
    record = _record() if record is None else record
    lookup_request = _lookup_request() if lookup_request is None else lookup_request
    lookup_result = (
        match_exact_fuzzy_records(
            request=lookup_request,
            candidate_records=(record,),
            policy=_policy(),
        )
        if lookup_result is None
        else lookup_result
    )
    audit_event = (
        build_cache_lookup_audit_event(
            request=lookup_request,
            lookup_result=lookup_result,
            candidate_record=record if lookup_result.decision == "hit" else None,
            produced_at=PRODUCED_AT,
            metadata={"scope": "sc-g4"},
        )
        if audit_event is None
        else audit_event
    )
    false_hit_case = FalseHitHarnessCase(
        case_id="case:bounded",
        risk_class="exact_duplicate_hit",
        audit_event=audit_event,
        expected_action=EXPECTED_ACTION_SAFE_HIT,
        fresh_response_fingerprint=record.response_fingerprint,
        current_source_fingerprints=record.lineage.source_fingerprints,
        current_policy_version=record.lineage.policy_version,
        current_model_key=record.model_key,
        current_user_tier=record.user_tier,
        current_context_fingerprint=record.context_fingerprint,
        admission_allowed=True,
        blocked_surface=False,
        negative_control=False,
        metadata={"scope": "sc-g4"},
    )
    evaluation = (
        evaluate_false_hit_case(case=false_hit_case, produced_at=PRODUCED_AT)
        if false_hit_evaluation is None
        else false_hit_evaluation
    )
    metrics = (
        compute_cache_observability_metrics(
            evaluations=(evaluation,),
            produced_at=PRODUCED_AT,
        )
        if metrics is None
        else metrics
    )
    stop_decision = (
        evaluate_cache_stop_rules(
            metrics=metrics,
            stop_rules=CacheStopRules(
                policy_version="semantic-cache-sc-g4-v1",
                max_false_hit_rate_bps=0,
                max_stale_answer_rate_bps=0,
                max_policy_mismatch_hits=0,
                max_model_mismatch_hits=0,
                max_context_leakage_hits=0,
                allow_blocked_surface_hits=False,
            ),
            produced_at=PRODUCED_AT,
        )
        if stop_decision is None
        else stop_decision
    )
    return BoundedInsightExperimentCandidate(
        lookup_request=lookup_request,
        lookup_result=lookup_result,
        record=record,
        audit_event=audit_event,
        false_hit_evaluation=evaluation,
        metrics=metrics,
        stop_decision=stop_decision,
        response_fingerprint=(
            record.response_fingerprint if response_fingerprint is None else response_fingerprint
        ),
        blocked_surface=blocked_surface,
        admission_allowed=admission_allowed,
        metadata={"scope": "sc-g4"} if metadata is None else metadata,
    )


def _decision(
    *,
    flags: BoundedInsightExperimentFlags | None = None,
    request: BoundedInsightExperimentRequest | None = None,
    candidate: BoundedInsightExperimentCandidate | None = None,
) -> BoundedInsightExperimentDecision:
    return evaluate_bounded_insight_experiment(
        flags=_flags() if flags is None else flags,
        request=_request() if request is None else request,
        candidate=_candidate() if candidate is None else candidate,
    )


def test_experiment_eligible_requires_all_flags_and_safe_candidate() -> None:
    decision = _decision()

    assert decision.decision == DECISION_EXPERIMENT_ELIGIBLE
    assert decision.reason_codes == (REASON_EXPERIMENT_ELIGIBLE,)
    assert decision.candidate_record_id == _record().record_id
    assert decision.response_fingerprint == "sha256:response"
    assert dict(to_stable_mapping(decision))["metadata"] == {
        "decision_scope": "metadata_only",
        "serves_cached_payload": False,
    }


@pytest.mark.parametrize(
    ("flags", "reason"),
    [
        (_flags(environment_enabled=False), REASON_ENVIRONMENT_FLAG_DISABLED),
        (_flags(runtime_enabled=False), REASON_RUNTIME_FLAG_DISABLED),
        (_flags(request_opt_in=False), REASON_REQUEST_NOT_OPTED_IN),
        (_flags(request_disable=True), REASON_REQUEST_DISABLED),
        (
            _flags(kill_switch_snapshot=KillSwitchSnapshot(True, True, False, True)),
            REASON_KILL_SWITCH_DISABLED,
        ),
    ],
)
def test_flags_default_off_and_fail_closed(
    flags: BoundedInsightExperimentFlags,
    reason: str,
) -> None:
    decision = _decision(flags=flags)

    assert decision.decision == DECISION_FALLBACK
    assert reason in decision.reason_codes


def test_missing_candidate_and_lookup_miss_fallback() -> None:
    missing = evaluate_bounded_insight_experiment(
        flags=_flags(),
        request=_request(),
        candidate=None,
    )

    assert missing.decision == DECISION_FALLBACK
    assert "candidate_missing" in missing.reason_codes

    lookup_request = _lookup_request("different query")
    lookup_result = match_exact_fuzzy_records(
        request=lookup_request,
        candidate_records=(),
        policy=_policy(),
    )
    miss_candidate = _candidate(
        lookup_request=lookup_request,
        lookup_result=lookup_result,
        audit_event=build_cache_lookup_audit_event(
            request=lookup_request,
            lookup_result=lookup_result,
            candidate_record=None,
            produced_at=PRODUCED_AT,
            metadata={"scope": "sc-g4"},
        ),
    )
    miss = _decision(candidate=miss_candidate)

    assert miss.decision == DECISION_FALLBACK
    assert REASON_LOOKUP_MISS in miss.reason_codes


@pytest.mark.parametrize(
    ("experiment_request", "reason"),
    [
        (_request(surface="settings"), REASON_UNSUPPORTED_SURFACE),
        (
            _request(source_fingerprints=("sha256:source-a", "sha256:source-next")),
            REASON_SOURCE_FINGERPRINT_MISMATCH,
        ),
        (_request(policy_version="semantic-cache-sc-g4-v2"), REASON_POLICY_MISMATCH),
        (_request(provider_key="provider:next"), REASON_PROVIDER_MISMATCH),
        (_request(model_key="model:next"), REASON_MODEL_MISMATCH),
        (_request(context_fingerprint="sha256:context-next"), REASON_CONTEXT_MISMATCH),
        (_request(user_tier="free"), REASON_USER_TIER_MISMATCH),
        (
            _request(transparency_notice_id="notice:insight:v2"),
            REASON_TRANSPARENCY_NOTICE_MISMATCH,
        ),
    ],
)
def test_partition_and_surface_mismatches_fallback(
    experiment_request: BoundedInsightExperimentRequest,
    reason: str,
) -> None:
    decision = _decision(request=experiment_request)

    assert decision.decision == DECISION_FALLBACK
    assert reason in decision.reason_codes


@pytest.mark.parametrize(
    ("audit_event", "reason"),
    [
        (
            replace(_candidate().audit_event, source_fingerprints=("sha256:source-a",)),
            REASON_SOURCE_FINGERPRINT_MISMATCH,
        ),
        (
            replace(_candidate().audit_event, policy_version="semantic-cache-sc-g4-v2"),
            REASON_POLICY_MISMATCH,
        ),
        (replace(_candidate().audit_event, provider_key="provider:next"), REASON_PROVIDER_MISMATCH),
        (replace(_candidate().audit_event, model_key="model:next"), REASON_MODEL_MISMATCH),
        (
            replace(_candidate().audit_event, context_fingerprint="sha256:context-next"),
            REASON_CONTEXT_MISMATCH,
        ),
        (replace(_candidate().audit_event, user_tier="free"), REASON_USER_TIER_MISMATCH),
        (
            replace(_candidate().audit_event, transparency_notice_id="notice:insight:v2"),
            REASON_TRANSPARENCY_NOTICE_MISMATCH,
        ),
    ],
)
def test_audit_event_partition_mismatches_fallback(
    audit_event: CacheLookupAuditEvent,
    reason: str,
) -> None:
    decision = _decision(candidate=_candidate(audit_event=audit_event))

    assert decision.decision == DECISION_FALLBACK
    assert reason in decision.reason_codes


def test_response_fingerprint_admission_stop_and_blocked_surface_fallback() -> None:
    response_mismatch = _decision(
        candidate=_candidate(response_fingerprint="sha256:other-response")
    )
    assert response_mismatch.decision == DECISION_FALLBACK
    assert REASON_RESPONSE_FINGERPRINT_MISMATCH in response_mismatch.reason_codes

    admission_blocked = _decision(candidate=_candidate(admission_allowed=False))
    assert admission_blocked.decision == DECISION_FALLBACK
    assert REASON_ADMISSION_BLOCKED in admission_blocked.reason_codes

    blocked_surface = _decision(candidate=_candidate(blocked_surface=True))
    assert blocked_surface.decision == DECISION_FALLBACK
    assert REASON_BLOCKED_SURFACE in blocked_surface.reason_codes

    stop_decision = replace(_candidate().stop_decision, stop_serving=True, rollback_required=True)
    stop_blocked = _decision(candidate=_candidate(stop_decision=stop_decision))
    assert stop_blocked.decision == DECISION_FALLBACK
    assert REASON_STOP_RULE_BLOCKED in stop_blocked.reason_codes


def test_missing_evidence_linkage_fallback() -> None:
    for request in (
        _request(admission_decision_id=None),
        _request(promotion_ids=()),
        _request(replay_entry_ids=()),
    ):
        decision = _decision(request=request)

        assert decision.decision == DECISION_FALLBACK
        assert REASON_EVIDENCE_LINKAGE_MISSING in decision.reason_codes

    record = create_exact_fuzzy_cache_record(
        surface="insight",
        raw_query="Plan protein breakfast",
        context_fingerprint="sha256:context",
        provider_key="provider:test",
        model_key="model:test",
        user_tier="pro",
        transparency_notice_id="notice:insight:v1",
        lineage=build_exact_fuzzy_lineage(
            eval_event_ids=("eval:bounded:1",),
            admission_decision_id=None,
            promotion_ids=("promotion:bounded:1",),
            replay_entry_ids=("replay:bounded:1",),
            source_fingerprints=("sha256:source-a", "sha256:source-b"),
            policy_version="semantic-cache-sc-g4-v1",
        ),
        response_fingerprint="sha256:response",
        safety_flags=("wellness-only",),
    )
    decision = _decision(candidate=_candidate(record=record))
    assert decision.decision == DECISION_FALLBACK
    assert REASON_EVIDENCE_LINKAGE_MISSING in decision.reason_codes

    missing_replay_record = create_exact_fuzzy_cache_record(
        surface="insight",
        raw_query="Plan protein breakfast",
        context_fingerprint="sha256:context",
        provider_key="provider:test",
        model_key="model:test",
        user_tier="pro",
        transparency_notice_id="notice:insight:v1",
        lineage=build_exact_fuzzy_lineage(
            eval_event_ids=("eval:bounded:1",),
            admission_decision_id="admission:bounded:1",
            promotion_ids=("promotion:bounded:1",),
            replay_entry_ids=(),
            source_fingerprints=("sha256:source-a", "sha256:source-b"),
            policy_version="semantic-cache-sc-g4-v1",
        ),
        response_fingerprint="sha256:response",
        safety_flags=("wellness-only",),
    )
    decision = _decision(candidate=_candidate(record=missing_replay_record))
    assert decision.decision == DECISION_FALLBACK
    assert REASON_EVIDENCE_LINKAGE_MISSING in decision.reason_codes


@pytest.mark.parametrize(
    "record",
    [
        replace(
            _record(),
            lineage=replace(_record().lineage, eval_event_ids=("eval:bounded:other",)),
        ),
        replace(
            _record(), lineage=replace(_record().lineage, admission_decision_id="admission:other")
        ),
        replace(
            _record(),
            lineage=replace(_record().lineage, promotion_ids=("promotion:bounded:other",)),
        ),
        replace(
            _record(),
            lineage=replace(_record().lineage, replay_entry_ids=("replay:bounded:other",)),
        ),
    ],
)
def test_record_evidence_graph_id_mismatches_fallback(record: ExactFuzzyCacheRecord) -> None:
    decision = _decision(candidate=_candidate(record=record))

    assert decision.decision == DECISION_FALLBACK
    assert REASON_EVIDENCE_LINKAGE_MISMATCH in decision.reason_codes


@pytest.mark.parametrize(
    "audit_event",
    [
        replace(_candidate().audit_event, eval_event_ids=("eval:bounded:other",)),
        replace(_candidate().audit_event, admission_decision_id="admission:other"),
        replace(_candidate().audit_event, promotion_ids=("promotion:bounded:other",)),
        replace(_candidate().audit_event, replay_entry_ids=("replay:bounded:other",)),
    ],
)
def test_audit_event_evidence_graph_id_mismatches_fallback(
    audit_event: CacheLookupAuditEvent,
) -> None:
    decision = _decision(candidate=_candidate(audit_event=audit_event))

    assert decision.decision == DECISION_FALLBACK
    assert REASON_EVIDENCE_LINKAGE_MISMATCH in decision.reason_codes


def test_decision_identity_and_serialization_are_deterministic_and_safe() -> None:
    first = _decision()
    second = _decision()

    assert first.decision_id == second.decision_id
    assert to_stable_mapping(first) == to_stable_mapping(second)
    serialized = json.dumps(dict(to_stable_mapping(first)), sort_keys=True)
    assert "Plan protein breakfast" not in serialized
    assert "raw_query" not in serialized
    assert "normalized_query" not in serialized
    assert "raw_prompt" not in serialized
    with pytest.raises(ValueError, match="unsupported stable mapping"):
        to_stable_mapping({"not": "a contract"})


def test_metadata_is_defensively_copied_and_raw_payloads_are_rejected() -> None:
    metadata: dict[str, JsonValue] = {"labels": ["sc-g4"]}
    request = _request(metadata=metadata)
    metadata["labels"] = ["mutated"]

    assert request.metadata["labels"] == ["sc-g4"]
    for unsafe in (
        {"raw_prompt": "never"},
        {"note": "cache raw response"},
        {"authorization": "Basic abc"},
        {"artifact": "/tmp/cache.txt"},
        {"healthkit": "steps"},
    ):
        with pytest.raises(ValueError, match="unsafe metadata"):
            _request(metadata=unsafe)


def test_contracts_reject_invalid_types() -> None:
    with pytest.raises(ValueError, match="kill_switch_snapshot must be KillSwitchSnapshot"):
        _flags(kill_switch_snapshot=cast(KillSwitchSnapshot, "not-kill-switch"))
    base = _candidate()
    with pytest.raises(ValueError, match="lookup_request must be ExactFuzzyCacheLookupRequest"):
        BoundedInsightExperimentCandidate(
            lookup_request=cast(ExactFuzzyCacheLookupRequest, "not-request"),
            lookup_result=base.lookup_result,
            record=base.record,
            audit_event=base.audit_event,
            false_hit_evaluation=base.false_hit_evaluation,
            metrics=base.metrics,
            stop_decision=base.stop_decision,
            response_fingerprint=base.response_fingerprint,
            blocked_surface=False,
            admission_allowed=True,
            metadata={},
        )
    with pytest.raises(ValueError, match="lookup_result must be ExactFuzzyCacheLookupResult"):
        BoundedInsightExperimentCandidate(
            lookup_request=base.lookup_request,
            lookup_result=cast(ExactFuzzyCacheLookupResult, "not-result"),
            record=base.record,
            audit_event=base.audit_event,
            false_hit_evaluation=base.false_hit_evaluation,
            metrics=base.metrics,
            stop_decision=base.stop_decision,
            response_fingerprint=base.response_fingerprint,
            blocked_surface=False,
            admission_allowed=True,
            metadata={},
        )
    with pytest.raises(ValueError, match="record must be ExactFuzzyCacheRecord"):
        BoundedInsightExperimentCandidate(
            lookup_request=base.lookup_request,
            lookup_result=base.lookup_result,
            record=cast(ExactFuzzyCacheRecord, "not-record"),
            audit_event=base.audit_event,
            false_hit_evaluation=base.false_hit_evaluation,
            metrics=base.metrics,
            stop_decision=base.stop_decision,
            response_fingerprint=base.response_fingerprint,
            blocked_surface=False,
            admission_allowed=True,
            metadata={},
        )


def test_module_has_no_forbidden_imports_or_nondeterministic_calls() -> None:
    assert_no_forbidden_semantic_cache_imports(MODULE)
    assert_no_forbidden_semantic_cache_calls(MODULE)


def test_sc_g4_is_not_exported_from_core_ai_facade() -> None:
    init_path = REPO_ROOT / "core" / "ai" / "__init__.py"
    content = init_path.read_text(encoding="utf-8")

    assert "bounded_insight_semantic_cache" not in content
    assert "BoundedInsight" not in content
