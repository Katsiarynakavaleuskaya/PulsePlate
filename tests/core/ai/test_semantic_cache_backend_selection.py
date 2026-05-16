from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from core.ai.semantic_cache_backend_selection import (
    BACKEND_LABEL_GPTCACHE,
    BACKEND_LABEL_IN_MEMORY,
    BACKEND_LABEL_REDIS,
    DECISION_ELIGIBLE,
    DECISION_INELIGIBLE,
    DECISION_NO_SELECTION,
    DECISION_SELECTED,
    REASON_ADMISSION_BLOCKED_HITS,
    REASON_BLOCKED_SURFACE_HITS,
    REASON_CURRENT_HEAD_CI_MISSING,
    REASON_ELIGIBLE,
    REASON_FALSE_HIT_RATE_EXCEEDED,
    REASON_HUMAN_APPROVAL_MISSING,
    REASON_BACKEND_LABEL_NOT_ALLOWED,
    REASON_CONTEXT_LEAKAGE_EXCEEDED,
    REASON_FRESH_RUNTIME_COMPARISONS_MISSING,
    REASON_MODEL_MISMATCH_EXCEEDED,
    REASON_NEGATIVE_CONTROLS_MISSING,
    REASON_NO_ELIGIBLE_CANDIDATE,
    REASON_POLICY_MISMATCH_EXCEEDED,
    REASON_ROLLBACK_PROOF_MISSING,
    REASON_SC_G2_EVIDENCE_MISSING,
    REASON_SC_G3_EVIDENCE_MISSING,
    REASON_SC_G4_EVIDENCE_MISSING,
    REASON_SELECTED,
    REASON_STALE_ANSWER_RATE_EXCEEDED,
    SemanticCacheBackendCandidate,
    SemanticCacheBackendEvaluationMatrix,
    SemanticCacheBackendRollbackProof,
    SemanticCacheBackendSafetyEvidence,
    SemanticCacheBackendSelectionCriteria,
    SemanticCacheBackendSelectionDecision,
    build_semantic_cache_backend_matrix_id,
    evaluate_semantic_cache_backend_candidate,
    evaluate_semantic_cache_backend_matrix,
    select_semantic_cache_backend,
    to_stable_mapping,
    _backend_rollback_token,
    _ci_proof_parts_match_current_head,
    _ci_proof_suffix_has_unsafe_runtime_scope,
    _normalize_required_runtime_safe_evidence_ids,
    _normalize_required_runtime_safe_tokens,
    _normalize_required_structured_proof_ids,
    _normalize_required_unique_tokens,
    _normalize_unique_tokens,
    _normalize_unique_runtime_safe_tokens,
    _runtime_scope_sequence_matches,
    _validate_decision_id_format,
    _candidate_failure_reasons,
    _validate_evidence_id,
    _validate_git_sha,
    _validate_token,
)
from tests.helpers.semantic_cache_import_guard import (
    assert_no_forbidden_semantic_cache_calls,
    assert_no_forbidden_semantic_cache_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = REPO_ROOT / "core" / "ai" / "semantic_cache_backend_selection.py"


def _evidence(
    *,
    false_hit_rate_bps: int = 0,
    stale_answer_rate_bps: int = 0,
    policy_mismatch_count: int = 0,
    model_mismatch_count: int = 0,
    context_leakage_count: int = 0,
    admission_blocked_hit_count: int = 0,
    blocked_surface_hit_count: int = 0,
    negative_control_count: int = 25,
    fresh_runtime_comparison_count: int = 25,
) -> SemanticCacheBackendSafetyEvidence:
    return SemanticCacheBackendSafetyEvidence(
        evidence_id="evidence:backend:1",
        sc_g2_contract_id="contract:sc-g2",
        sc_g3_contract_id="contract:sc-g3",
        sc_g4_contract_id="contract:sc-g4",
        source_fingerprints=("sha256:source-a", "sha256:source-b"),
        eval_event_ids=("eval:1",),
        admission_decision_id="admission:1",
        promotion_ids=("promotion:1",),
        replay_entry_ids=("replay:1",),
        false_hit_rate_bps=false_hit_rate_bps,
        stale_answer_rate_bps=stale_answer_rate_bps,
        policy_mismatch_count=policy_mismatch_count,
        model_mismatch_count=model_mismatch_count,
        context_leakage_count=context_leakage_count,
        admission_blocked_hit_count=admission_blocked_hit_count,
        blocked_surface_hit_count=blocked_surface_hit_count,
        negative_control_count=negative_control_count,
        fresh_runtime_comparison_count=fresh_runtime_comparison_count,
        evidence_fingerprints=("sha256:evidence",),
        metadata={"scope": "sc-g5"},
    )


def _rollback(
    *,
    backend_token: str = "redis",
    verified: bool = True,
    blast_radius_bps: int = 10,
) -> SemanticCacheBackendRollbackProof:
    return SemanticCacheBackendRollbackProof(
        proof_id=f"rollback:{backend_token}:1",
        kill_switch_proof_id=f"proof:kill-switch:{backend_token}",
        request_bypass_proof_id=f"proof:bypass:{backend_token}",
        no_cache_fallback_proof_id=f"proof:no-cache:{backend_token}",
        purge_invalidation_proof_id=f"proof:purge:{backend_token}",
        disabled_state_test_ids=(f"test:disabled:{backend_token}",),
        stop_rule_replay_ids=(f"replay:stop-rule:{backend_token}",),
        rollback_runbook_id=f"runbook:rollback:{backend_token}",
        blast_radius_bps=blast_radius_bps,
        verified=verified,
        metadata={"scope": "sc-g5"},
    )


def _candidate(
    *,
    candidate_id: str = "candidate:redis",
    backend_label: str = BACKEND_LABEL_REDIS,
    evidence: SemanticCacheBackendSafetyEvidence | None = None,
    rollback: SemanticCacheBackendRollbackProof | None = None,
    current_head_ci_passed: bool = True,
    current_head_ci_proof_id: str | None = "ci:pr-1742:head-d91b58100:run-25914493764",
    human_approval_record_id: str | None = "approval:human:pr-1742",
    latency_saved_p95_ms: int = 100,
    cost_saved_microunits: int = 10,
) -> SemanticCacheBackendCandidate:
    return SemanticCacheBackendCandidate(
        candidate_id=candidate_id,
        backend_label=backend_label,
        backend_version="label:v1",
        policy_version="semantic-cache-sc-g5-v1",
        supported_surfaces=("insight",),
        capability_flags=("label-only", "offline-contract"),
        safety_evidence=_evidence() if evidence is None else evidence,
        rollback_proof=(
            _rollback(backend_token=backend_label.removesuffix("_label").replace("_", "-"))
            if rollback is None
            else rollback
        ),
        latency_saved_p50_ms=50,
        latency_saved_p95_ms=latency_saved_p95_ms,
        provider_calls_avoided_count=5,
        cost_saved_microunits=cost_saved_microunits,
        current_head_ci_passed=current_head_ci_passed,
        current_head_ci_proof_id=current_head_ci_proof_id,
        human_approval_record_id=human_approval_record_id,
        metadata={"scope": "sc-g5"},
    )


def _criteria() -> SemanticCacheBackendSelectionCriteria:
    return SemanticCacheBackendSelectionCriteria(
        policy_version="semantic-cache-sc-g5-v1",
        allowed_backend_labels=(
            BACKEND_LABEL_IN_MEMORY,
            BACKEND_LABEL_REDIS,
            BACKEND_LABEL_GPTCACHE,
        ),
        required_surface="insight",
        max_false_hit_rate_bps=0,
        max_stale_answer_rate_bps=0,
        max_policy_mismatch_count=0,
        max_model_mismatch_count=0,
        max_context_leakage_count=0,
        allow_admission_blocked_hits=False,
        allow_blocked_surface_hits=False,
        min_negative_control_count=10,
        min_fresh_runtime_comparison_count=10,
        require_current_head_ci=True,
        current_head_sha="d91b58100",
        require_human_approval=True,
        runtime_allowed=False,
        implementation_allowed=False,
    )


def test_valid_redis_and_gptcache_labels_are_inert_and_eligible() -> None:
    for label in (BACKEND_LABEL_REDIS, BACKEND_LABEL_GPTCACHE):
        decision = evaluate_semantic_cache_backend_candidate(
            candidate=_candidate(backend_label=label),
            criteria=_criteria(),
        )

        assert decision.decision == DECISION_ELIGIBLE
        assert decision.backend_label == label
        assert decision.runtime_allowed is False
        assert decision.implementation_allowed is False


def test_unknown_blank_path_or_secret_like_backend_labels_fail_closed() -> None:
    for label in ("", "redis", "/tmp/cache", "sk-secret"):
        with pytest.raises(ValueError):
            _candidate(backend_label=label)


def test_safety_failures_hard_block_before_selection() -> None:
    candidate = _candidate(
        evidence=_evidence(
            false_hit_rate_bps=1,
            stale_answer_rate_bps=1,
            admission_blocked_hit_count=1,
        )
    )

    decision = evaluate_semantic_cache_backend_candidate(
        candidate=candidate,
        criteria=_criteria(),
    )

    assert decision.decision == DECISION_INELIGIBLE
    assert REASON_FALSE_HIT_RATE_EXCEEDED in decision.reason_codes
    assert REASON_STALE_ANSWER_RATE_EXCEEDED in decision.reason_codes
    assert REASON_ADMISSION_BLOCKED_HITS in decision.reason_codes


def test_all_safety_threshold_failures_are_reported() -> None:
    decision = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(
            evidence=_evidence(
                policy_mismatch_count=1,
                model_mismatch_count=1,
                context_leakage_count=1,
                blocked_surface_hit_count=1,
                negative_control_count=1,
                fresh_runtime_comparison_count=1,
            ),
            latency_saved_p95_ms=1,
            cost_saved_microunits=1,
        ),
        criteria=_criteria(),
    )

    assert decision.decision == DECISION_INELIGIBLE
    assert REASON_POLICY_MISMATCH_EXCEEDED in decision.reason_codes
    assert REASON_MODEL_MISMATCH_EXCEEDED in decision.reason_codes
    assert REASON_CONTEXT_LEAKAGE_EXCEEDED in decision.reason_codes
    assert REASON_BLOCKED_SURFACE_HITS in decision.reason_codes
    assert REASON_NEGATIVE_CONTROLS_MISSING in decision.reason_codes
    assert REASON_FRESH_RUNTIME_COMPARISONS_MISSING in decision.reason_codes


def test_policy_or_surface_mismatch_blocks_sc_g4_compatibility() -> None:
    policy_mismatch = evaluate_semantic_cache_backend_candidate(
        candidate=replace(_candidate(), policy_version="semantic-cache-sc-g5-other"),
        criteria=_criteria(),
    )
    surface_mismatch = evaluate_semantic_cache_backend_candidate(
        candidate=replace(_candidate(), supported_surfaces=("other",)),
        criteria=_criteria(),
    )

    assert REASON_SC_G4_EVIDENCE_MISSING in policy_mismatch.reason_codes
    assert REASON_SC_G4_EVIDENCE_MISSING in surface_mismatch.reason_codes

    for evidence, expected_reason in (
        (
            replace(_evidence(), sc_g2_contract_id="contract:sc-g2-other"),
            REASON_SC_G2_EVIDENCE_MISSING,
        ),
        (
            replace(_evidence(), sc_g3_contract_id="contract:sc-g3-other"),
            REASON_SC_G3_EVIDENCE_MISSING,
        ),
        (
            replace(_evidence(), sc_g4_contract_id="contract:sc-g4-other"),
            REASON_SC_G4_EVIDENCE_MISSING,
        ),
    ):
        decision = evaluate_semantic_cache_backend_candidate(
            candidate=_candidate(evidence=evidence),
            criteria=_criteria(),
        )

        assert decision.decision == DECISION_INELIGIBLE
        assert expected_reason in decision.reason_codes


def test_policy_and_surface_mismatch_dedupe_sc_g4_reason() -> None:
    decision = evaluate_semantic_cache_backend_candidate(
        candidate=replace(
            _candidate(),
            policy_version="semantic-cache-sc-g5-other",
            supported_surfaces=("other",),
        ),
        criteria=_criteria(),
    )

    assert decision.decision == DECISION_INELIGIBLE
    assert decision.reason_codes.count(REASON_SC_G4_EVIDENCE_MISSING) == 1


def test_rollback_ci_and_human_approval_are_required() -> None:
    candidate = _candidate(
        rollback=_rollback(verified=False),
        current_head_ci_passed=False,
        human_approval_record_id=None,
    )

    decision = evaluate_semantic_cache_backend_candidate(
        candidate=candidate,
        criteria=_criteria(),
    )

    assert decision.decision == DECISION_INELIGIBLE
    assert REASON_ROLLBACK_PROOF_MISSING in decision.reason_codes
    assert REASON_CURRENT_HEAD_CI_MISSING in decision.reason_codes
    assert REASON_HUMAN_APPROVAL_MISSING in decision.reason_codes


def test_rollback_proof_must_match_candidate_backend_label() -> None:
    rollback = replace(
        _rollback(backend_token="redis"),
        kill_switch_proof_id="proof:kill-switch:gptcache",
        request_bypass_proof_id="proof:bypass:gptcache",
        no_cache_fallback_proof_id="proof:no-cache:gptcache",
        purge_invalidation_proof_id="proof:purge:gptcache",
        disabled_state_test_ids=("test:disabled:gptcache",),
        stop_rule_replay_ids=("replay:stop-rule:gptcache",),
        rollback_runbook_id="runbook:rollback:gptcache",
    )
    decision = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(backend_label=BACKEND_LABEL_REDIS, rollback=rollback),
        criteria=_criteria(),
    )

    assert decision.decision == DECISION_INELIGIBLE
    assert REASON_ROLLBACK_PROOF_MISSING in decision.reason_codes


def test_rollback_proof_rejects_ambiguous_multi_backend_ids() -> None:
    rollback = replace(
        _rollback(backend_token="redis"),
        proof_id="rollback:redis:gptcache:1",
        kill_switch_proof_id="proof:kill-switch:redis:gptcache",
        request_bypass_proof_id="proof:bypass:redis:gptcache",
        no_cache_fallback_proof_id="proof:no-cache:redis:gptcache",
        purge_invalidation_proof_id="proof:purge:redis:gptcache",
        disabled_state_test_ids=("test:disabled:redis:gptcache",),
        stop_rule_replay_ids=("replay:stop-rule:redis:gptcache",),
        rollback_runbook_id="runbook:rollback:redis:gptcache",
    )
    decision = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(backend_label=BACKEND_LABEL_REDIS, rollback=rollback),
        criteria=_criteria(),
    )

    assert decision.decision == DECISION_INELIGIBLE
    assert REASON_ROLLBACK_PROOF_MISSING in decision.reason_codes


def test_rollback_proof_requires_structured_machine_ids() -> None:
    for bad_rollback in (
        lambda: replace(_rollback(), proof_id="placeholder"),
        lambda: replace(_rollback(), kill_switch_proof_id="placeholder"),
        lambda: replace(_rollback(), request_bypass_proof_id="placeholder"),
        lambda: replace(_rollback(), no_cache_fallback_proof_id="placeholder"),
        lambda: replace(_rollback(), purge_invalidation_proof_id="placeholder"),
        lambda: replace(_rollback(), disabled_state_test_ids=("placeholder",)),
        lambda: replace(_rollback(), stop_rule_replay_ids=("placeholder",)),
        lambda: replace(_rollback(), rollback_runbook_id="placeholder"),
    ):
        with pytest.raises(ValueError, match="structured proof"):
            bad_rollback()


def test_private_validation_helpers_cover_uncovered_branches() -> None:
    criteria = _criteria()
    replacement = replace(_criteria(), allowed_backend_labels=(BACKEND_LABEL_REDIS,))
    blocked_reason = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(backend_label=BACKEND_LABEL_GPTCACHE), criteria=replacement
    )
    selected = evaluate_semantic_cache_backend_candidate(candidate=_candidate(), criteria=criteria)
    no_selection = select_semantic_cache_backend(
        candidates=(_candidate(evidence=_evidence(false_hit_rate_bps=1)),), criteria=criteria
    )

    with pytest.raises(ValueError, match="criteria must be"):
        build_semantic_cache_backend_matrix_id(
            candidates=(_candidate(),),
            criteria=cast(Any, "bad"),
            final_decision=selected,
        )
    with pytest.raises(ValueError, match="final_decision must match"):
        build_semantic_cache_backend_matrix_id(
            candidates=(_candidate(),),
            criteria=criteria,
            final_decision=cast(Any, no_selection),
        )
    assert REASON_BACKEND_LABEL_NOT_ALLOWED in blocked_reason.reason_codes

    with pytest.raises(ValueError, match="unsupported decision"):
        _validate_decision_id_format(
            "semantic-cache-backend:000000000000000000000001", "bad-decision"
        )
    with pytest.raises(ValueError):
        _validate_decision_id_format("semantic-cache-backend:abcd", DECISION_ELIGIBLE)
    with pytest.raises(ValueError, match="candidate-evaluation decision kind"):
        _validate_decision_id_format(
            "semantic-cache-backend-select:000000000000000000000001",
            DECISION_ELIGIBLE,
        )
    with pytest.raises(ValueError, match="selection decision kind"):
        _validate_decision_id_format(
            "semantic-cache-backend:000000000000000000000001", DECISION_SELECTED
        )
    _validate_decision_id_format(
        "semantic-cache-backend-select:000000000000000000000001",
        DECISION_SELECTED,
    )


def test_private_normalizer_and_scope_helpers_cover_edge_paths() -> None:
    assert (
        _runtime_scope_sequence_matches(tokens=("insight",), index=0, sequence=("other",)) is False
    )
    with pytest.raises(ValueError):
        _normalize_required_unique_tokens("fields", ())
    with pytest.raises(ValueError):
        _normalize_unique_tokens("fields", ["same", "same"])
    with pytest.raises(ValueError):
        _normalize_required_structured_proof_ids("proof_ids", (), prefixes=("proof:",))
    with pytest.raises(ValueError):
        _normalize_required_structured_proof_ids(
            "proof_ids", ("proof:one", "proof:one"), prefixes=("proof:",)
        )
    with pytest.raises(ValueError):
        _normalize_required_runtime_safe_tokens("scopes", ())
    with pytest.raises(ValueError):
        _normalize_required_runtime_safe_tokens("scopes", ("insight", "insight"))
    with pytest.raises(ValueError):
        _normalize_required_runtime_safe_evidence_ids("proof_ids", ())
    with pytest.raises(ValueError):
        _normalize_required_runtime_safe_evidence_ids(
            "proof_ids", ("verification-bundle:ci:current-head:d91b58100:run-25914493764",) * 2
        )

    with pytest.raises(ValueError):
        _validate_token("field", "")
    with pytest.raises(ValueError):
        _validate_git_sha("sha", "ABCdef1")
    with pytest.raises(ValueError):
        _validate_git_sha("sha", "abc")
    with pytest.raises(ValueError):
        _validate_evidence_id("evidence_id", "evidence:raw_prompt")
    with pytest.raises(ValueError):
        _validate_evidence_id("evidence_id", "raw_queries:abc")
    with pytest.raises(ValueError, match="unsupported backend_label"):
        _backend_rollback_token("unsupported")
    with pytest.raises(ValueError, match="contains duplicate entries"):
        _normalize_unique_runtime_safe_tokens("scopes", ("insight", "insight"))
    assert (
        _ci_proof_parts_match_current_head(
            ("ci", "pr-1742", "head-bad", "run-25914493764"),
            "d91b58100",
        )
        is False
    )
    assert (
        _ci_proof_parts_match_current_head(
            ("ci", "build", "head-d91b58100", "run-25914493764"),
            "d91b58100",
        )
        is False
    )
    assert (
        _ci_proof_suffix_has_unsafe_runtime_scope(
            ("ci", "current-head", "d91b58100", "run-25914493764", "safe")
        )
        is False
    )
    assert _ci_proof_suffix_has_unsafe_runtime_scope(("ci", "current-head", "d91b58100")) is False


def test_current_head_ci_check_is_skipped_when_not_required() -> None:
    criteria = _criteria()
    object.__setattr__(criteria, "require_current_head_ci", False)
    candidate = _candidate(current_head_ci_proof_id="ci:current-head:d91b58100:run-25914493764")
    reasons = _candidate_failure_reasons(candidate=candidate, criteria=criteria)
    assert REASON_CURRENT_HEAD_CI_MISSING not in reasons


def test_current_head_ci_requires_auditable_proof_id() -> None:
    decision = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(current_head_ci_passed=True, current_head_ci_proof_id=None),
        criteria=_criteria(),
    )

    assert decision.decision == DECISION_INELIGIBLE
    assert REASON_CURRENT_HEAD_CI_MISSING in decision.reason_codes


def test_current_head_ci_proof_must_match_criteria_head_sha() -> None:
    stale_proof = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(
            current_head_ci_passed=True,
            current_head_ci_proof_id="ci:pr-1742:head-7035cff:run-25518898784",
        ),
        criteria=_criteria(),
    )
    current_proof = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(
            current_head_ci_passed=True,
            current_head_ci_proof_id="ci:pr-1742:head-d91b58100:run-25914493764",
        ),
        criteria=_criteria(),
    )
    natural_current_head_proof = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(
            current_head_ci_passed=True,
            current_head_ci_proof_id="ci:current-head:d91b58100:run-25914493764",
        ),
        criteria=_criteria(),
    )
    bundled_current_proof = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(
            current_head_ci_passed=True,
            current_head_ci_proof_id=(
                "verification-bundle:ci:pr-1742:head-d91b58100:run-25914493764"
            ),
        ),
        criteria=_criteria(),
    )
    db_prefixed_sha_proof = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(
            current_head_ci_passed=True,
            current_head_ci_proof_id="ci:pr-1742:head-db12345:run-25914493764",
        ),
        criteria=replace(_criteria(), current_head_sha="db12345"),
    )

    assert stale_proof.decision == DECISION_INELIGIBLE
    assert REASON_CURRENT_HEAD_CI_MISSING in stale_proof.reason_codes
    assert current_proof.decision == DECISION_ELIGIBLE
    assert natural_current_head_proof.decision == DECISION_ELIGIBLE
    assert bundled_current_proof.decision == DECISION_ELIGIBLE
    assert db_prefixed_sha_proof.decision == DECISION_ELIGIBLE
    for weak_proof in (
        "ci:current-head:d91b58100",
        "ci:current-head:d91b58100:manual",
        "ci:current-head:d91b58100:x",
        "ci:current-head:d91b58100:run-fake",
        "ci:pr-abc:head-d91b58100:run-25914493764",
        "ci:pr-1742:head-d91b58100:manual",
        "verification-bundle:ci:current-head:d91b58100:manual",
        "verification-bundle:ci:note:current-head:d91b58100:manual",
    ):
        with pytest.raises(ValueError, match="current-head CI proof shape"):
            _candidate(current_head_ci_proof_id=weak_proof)


def test_selection_uses_safety_first_then_latency_cost_tiebreakers() -> None:
    safe_slower = _candidate(
        candidate_id="candidate:redis",
        backend_label=BACKEND_LABEL_REDIS,
        latency_saved_p95_ms=80,
        cost_saved_microunits=8,
    )
    safe_faster = _candidate(
        candidate_id="candidate:gptcache",
        backend_label=BACKEND_LABEL_GPTCACHE,
        latency_saved_p95_ms=120,
        cost_saved_microunits=20,
    )

    decision = select_semantic_cache_backend(
        candidates=(safe_slower, safe_faster),
        criteria=_criteria(),
    )

    assert decision.decision == DECISION_SELECTED
    assert decision.reason_codes == (REASON_SELECTED,)
    assert decision.selected_candidate_id == "candidate:gptcache"
    assert decision.selected_backend_label == BACKEND_LABEL_GPTCACHE
    assert decision.rejected_candidate_ids == ("candidate:redis",)


def test_selected_decision_identity_includes_evaluated_comparison_set() -> None:
    winner = _candidate(
        candidate_id="candidate:gptcache",
        backend_label=BACKEND_LABEL_GPTCACHE,
        latency_saved_p95_ms=120,
        cost_saved_microunits=20,
    )
    baseline = select_semantic_cache_backend(
        candidates=(winner,),
        criteria=_criteria(),
    )
    with_rejected_candidate = select_semantic_cache_backend(
        candidates=(
            winner,
            _candidate(
                candidate_id="candidate:redis",
                backend_label=BACKEND_LABEL_REDIS,
                evidence=_evidence(false_hit_rate_bps=1),
            ),
        ),
        criteria=_criteria(),
    )
    with_other_eligible_candidate = select_semantic_cache_backend(
        candidates=(
            winner,
            _candidate(
                candidate_id="candidate:memory",
                backend_label=BACKEND_LABEL_IN_MEMORY,
                latency_saved_p95_ms=80,
                cost_saved_microunits=8,
            ),
        ),
        criteria=_criteria(),
    )

    assert baseline.selected_candidate_id == with_rejected_candidate.selected_candidate_id
    assert baseline.selected_candidate_id == with_other_eligible_candidate.selected_candidate_id
    assert baseline.decision_id != with_rejected_candidate.decision_id
    assert baseline.decision_id != with_other_eligible_candidate.decision_id
    assert with_other_eligible_candidate.rejected_candidate_ids == ("candidate:memory",)


def test_candidate_decision_identity_includes_non_blocking_evidence() -> None:
    baseline = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(evidence=_evidence(negative_control_count=25)),
        criteria=_criteria(),
    )
    evidence_changed = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(evidence=_evidence(negative_control_count=26)),
        criteria=_criteria(),
    )

    assert baseline.decision == DECISION_ELIGIBLE
    assert evidence_changed.decision == DECISION_ELIGIBLE
    assert baseline.decision_id != evidence_changed.decision_id


def test_no_eligible_candidate_fails_closed() -> None:
    decision = select_semantic_cache_backend(
        candidates=(
            _candidate(evidence=_evidence(false_hit_rate_bps=1)),
            _candidate(
                candidate_id="candidate:gptcache",
                backend_label=BACKEND_LABEL_GPTCACHE,
                current_head_ci_passed=False,
            ),
        ),
        criteria=_criteria(),
    )

    assert decision.decision == DECISION_NO_SELECTION
    assert decision.reason_codes == (REASON_NO_ELIGIBLE_CANDIDATE,)
    assert decision.selected_backend_label is None


def test_no_selection_identity_includes_failure_details() -> None:
    first = select_semantic_cache_backend(
        candidates=(_candidate(evidence=_evidence(false_hit_rate_bps=1)),),
        criteria=_criteria(),
    )
    second = select_semantic_cache_backend(
        candidates=(_candidate(evidence=_evidence(stale_answer_rate_bps=1)),),
        criteria=_criteria(),
    )

    assert first.decision == DECISION_NO_SELECTION
    assert second.decision == DECISION_NO_SELECTION
    assert first.rejected_candidate_ids == second.rejected_candidate_ids
    assert first.decision_id != second.decision_id


def test_selector_rejects_duplicate_candidate_ids() -> None:
    candidate = _candidate()

    with pytest.raises(ValueError, match="duplicate candidate_id"):
        select_semantic_cache_backend(candidates=(candidate, candidate), criteria=_criteria())


def test_selector_recomputes_safety_and_ignores_forged_decisions() -> None:
    unsafe = _candidate(
        evidence=_evidence(false_hit_rate_bps=1),
        current_head_ci_passed=False,
        human_approval_record_id=None,
    )
    forged = SemanticCacheBackendSelectionDecision(
        decision_id="semantic-cache-backend:000000000000000000000000",
        decision=DECISION_ELIGIBLE,
        policy_version="semantic-cache-sc-g5-v1",
        selected_candidate_id=None,
        selected_backend_label=None,
        candidate_id=unsafe.candidate_id,
        backend_label=unsafe.backend_label,
        reason_codes=("eligible",),
        rejected_candidate_ids=(),
        runtime_allowed=False,
        implementation_allowed=False,
        metadata={"scope": "forged"},
    )

    assert forged.decision == DECISION_ELIGIBLE
    decision = select_semantic_cache_backend(candidates=(unsafe,), criteria=_criteria())

    assert decision.decision == DECISION_NO_SELECTION
    assert decision.selected_backend_label is None


def test_decision_rejects_non_sc_g5_decision_id() -> None:
    with pytest.raises(ValueError, match="decision_id"):
        SemanticCacheBackendSelectionDecision(
            decision_id="decision:forged",
            decision=DECISION_ELIGIBLE,
            policy_version="semantic-cache-sc-g5-v1",
            selected_candidate_id=None,
            selected_backend_label=None,
            candidate_id="candidate:redis",
            backend_label=BACKEND_LABEL_REDIS,
            reason_codes=(REASON_ELIGIBLE,),
            rejected_candidate_ids=(),
            runtime_allowed=False,
            implementation_allowed=False,
            metadata={"scope": "forged"},
        )
    with pytest.raises(ValueError, match="exactly one SC-G5 prefix"):
        replace(
            evaluate_semantic_cache_backend_candidate(candidate=_candidate(), criteria=_criteria()),
            decision_id="semantic-cache-backend:forged:000000000000000000000000",
        )


def test_matrix_and_mapping_are_deterministic() -> None:
    candidates = (
        _candidate(candidate_id="candidate:redis", backend_label=BACKEND_LABEL_REDIS),
        _candidate(candidate_id="candidate:gptcache", backend_label=BACKEND_LABEL_GPTCACHE),
    )

    first = evaluate_semantic_cache_backend_matrix(candidates=candidates, criteria=_criteria())
    second = evaluate_semantic_cache_backend_matrix(
        candidates=tuple(reversed(candidates)),
        criteria=_criteria(),
    )

    assert first.matrix_id == second.matrix_id
    assert to_stable_mapping(first) == to_stable_mapping(second)


def test_direct_matrix_constructor_canonicalizes_candidate_order() -> None:
    first = _candidate(candidate_id="candidate:redis", backend_label=BACKEND_LABEL_REDIS)
    second = _candidate(candidate_id="candidate:gptcache", backend_label=BACKEND_LABEL_GPTCACHE)
    canonical = evaluate_semantic_cache_backend_matrix(
        candidates=(first, second),
        criteria=_criteria(),
    )

    direct = SemanticCacheBackendEvaluationMatrix(
        matrix_id=canonical.matrix_id,
        policy_version=canonical.policy_version,
        criteria=canonical.criteria,
        candidates=(first, second),
        candidate_decisions=canonical.candidate_decisions,
        final_decision=canonical.final_decision,
    )

    assert direct.candidates == canonical.candidates


def test_matrix_identity_and_mapping_include_evidence_and_threshold_changes() -> None:
    first = evaluate_semantic_cache_backend_matrix(
        candidates=(_candidate(evidence=_evidence(negative_control_count=25)),),
        criteria=replace(_criteria(), min_negative_control_count=10),
    )
    evidence_changed = evaluate_semantic_cache_backend_matrix(
        candidates=(_candidate(evidence=_evidence(negative_control_count=26)),),
        criteria=replace(_criteria(), min_negative_control_count=10),
    )
    criteria_changed = evaluate_semantic_cache_backend_matrix(
        candidates=(_candidate(evidence=_evidence(negative_control_count=25)),),
        criteria=replace(_criteria(), min_negative_control_count=11),
    )

    assert first.matrix_id != evidence_changed.matrix_id
    assert to_stable_mapping(first) != to_stable_mapping(evidence_changed)
    assert first.matrix_id != criteria_changed.matrix_id
    assert to_stable_mapping(first) != to_stable_mapping(criteria_changed)


def test_metadata_rejects_raw_payloads_paths_and_product_truth_sources() -> None:
    unsafe_metadata = (
        {"raw_prompt": "plan"},
        {"raw_queries": "plan"},
        {"safe_key": "raw queries"},
        {"normalized_queries": "plan"},
        {"provider_payload": "payload"},
        {"provider_payloads": "payload"},
        {"provider:payload": "payload"},
        {"safe_key": "provider:payload"},
        {"api:key": "safe-looking"},
        {"private:key": "safe-looking"},
        {"connection:string": "safe-looking"},
        {"local:path": "safe-looking"},
        {"truth": "advisory:wiki"},
        {"truth": "knowledge:graph"},
        {"truth": "local_support_plane"},
        {"truth": "plugin:control-plane"},
        {"truth": "second_source_of_truth"},
        {"safe_key": "fastapi"},
        {"safe_key": "openapi"},
        {"safe_key": "network"},
        {"safe_key": "file-write"},
        {"health_kit_payload": "safe-looking"},
        {"safe_key": "health-kit-derived"},
        {"personalized_coaching_state": "safe-looking"},
        {"safe_key": "coaching_state"},
        {"auth_truth": "safe-looking"},
        {"safe_key": "authentication-truth"},
        {"path": "/tmp/cache"},
        {"truth": "advisory wiki"},
        {"credential": "blocked-value"},
        {"health": "HealthKit symptom"},
        {"access_token": "safe-looking"},
        {"refresh_token": "safe-looking"},
        {"jwt": "safe-looking"},
        {"token_value": "safe-looking"},
        {"pass" + "word": "blocked-value"},
        {"p" + "wd": "blocked-value"},
        {"safe_key": "ghp_test_token"},
        {"safe_key": "github_pat_test_token"},
        {"safe_key": "xoxb-test-token"},
        {"safe_key": "eyJ.test.signature"},
    )
    for metadata in unsafe_metadata:
        with pytest.raises(ValueError):
            replace(_candidate(), metadata=metadata)


def test_metadata_rejects_relative_local_paths() -> None:
    unsafe_metadata = (
        {"local_path": "relative/payload.txt"},
        {"path": "./payload.txt"},
        {"nested": {"path": "../payload.txt"}},
        {"uri": "file:///tmp/cache-evidence.json"},
        {"uri": "FILE:///tmp/cache-evidence.json"},
        {"uri": "uri:file:///tmp/cache-evidence.json"},
        {"uri": "see(/tmp/cache-evidence.json)"},
        {"path": "cache\\payload.json"},
    )

    for metadata in unsafe_metadata:
        with pytest.raises(ValueError):
            replace(_candidate(), metadata=metadata)


def test_nested_metadata_is_defensively_frozen_and_json_safe() -> None:
    candidate = replace(
        _candidate(),
        metadata={
            "nested": {"items": ["safe", 1, 2.5, None, True]},
            "tuple": ("safe", {"inner": "value"}),
        },
    )

    stable = to_stable_mapping(
        evaluate_semantic_cache_backend_matrix(candidates=(candidate,), criteria=_criteria())
    )

    candidate_signatures = stable["candidate_signatures"]
    assert isinstance(candidate_signatures, list)
    candidate_signature = cast(dict[str, object], candidate_signatures[0])
    assert candidate_signature["candidate_id"] == "candidate:redis"


def test_json_metadata_copy_rejects_non_finite_and_unsupported_values() -> None:
    for metadata in ({"value": float("nan")}, {"value": object()}):
        with pytest.raises(ValueError):
            replace(_candidate(), metadata=cast(Any, metadata))
    with pytest.raises(ValueError, match="metadata keys must be strings"):
        replace(_candidate(), metadata=cast(Any, {object(): "value"}))
    with pytest.raises(ValueError, match="metadata must be a mapping"):
        replace(_candidate(), metadata=cast(Any, ["not-a-mapping"]))


def test_criteria_cannot_enable_runtime_or_implementation() -> None:
    with pytest.raises(ValueError):
        replace(_criteria(), runtime_allowed=True)
    with pytest.raises(ValueError):
        replace(_criteria(), implementation_allowed=True)
    with pytest.raises(ValueError, match="CI proof and human approval"):
        replace(_criteria(), require_current_head_ci=False)
    with pytest.raises(ValueError, match="CI proof and human approval"):
        replace(_criteria(), require_human_approval=False)
    with pytest.raises(ValueError, match="zero-tolerance"):
        replace(_criteria(), max_false_hit_rate_bps=1)
    with pytest.raises(ValueError, match="zero-tolerance"):
        replace(_criteria(), max_stale_answer_rate_bps=1)
    with pytest.raises(ValueError, match="zero-tolerance"):
        replace(_criteria(), max_policy_mismatch_count=1)
    with pytest.raises(ValueError, match="zero-tolerance"):
        replace(_criteria(), max_model_mismatch_count=1)
    with pytest.raises(ValueError, match="zero-tolerance"):
        replace(_criteria(), max_context_leakage_count=1)
    with pytest.raises(ValueError, match="zero-tolerance"):
        replace(_criteria(), allow_admission_blocked_hits=True)
    with pytest.raises(ValueError, match="zero-tolerance"):
        replace(_criteria(), allow_blocked_surface_hits=True)
    with pytest.raises(ValueError, match="negative-control floor"):
        replace(_criteria(), min_negative_control_count=0)
    with pytest.raises(ValueError, match="fresh-comparison floor"):
        replace(_criteria(), min_fresh_runtime_comparison_count=0)


def test_type_and_value_validation_fail_closed() -> None:
    with pytest.raises(ValueError, match="safety_evidence"):
        replace(_candidate(), safety_evidence=cast(Any, "bad"))
    with pytest.raises(ValueError, match="rollback_proof"):
        replace(_candidate(), rollback_proof=cast(Any, "bad"))
    with pytest.raises(ValueError, match="unsupported decision"):
        replace(
            evaluate_semantic_cache_backend_candidate(candidate=_candidate(), criteria=_criteria()),
            decision="bad",
        )
    with pytest.raises(ValueError, match="unsupported reason_code"):
        replace(
            evaluate_semantic_cache_backend_candidate(candidate=_candidate(), criteria=_criteria()),
            decision=DECISION_INELIGIBLE,
            reason_codes=("made_up_reason",),
            rejected_candidate_ids=("candidate:redis",),
        )
    with pytest.raises(ValueError, match="runtime and implementation"):
        replace(
            evaluate_semantic_cache_backend_candidate(candidate=_candidate(), criteria=_criteria()),
            runtime_allowed=True,
        )
    with pytest.raises(ValueError, match="candidates"):
        evaluate_semantic_cache_backend_matrix(
            candidates=cast(Any, ("bad",)),
            criteria=_criteria(),
        )
    with pytest.raises(ValueError, match="criteria"):
        evaluate_semantic_cache_backend_candidate(candidate=_candidate(), criteria=cast(Any, "bad"))
    with pytest.raises(ValueError, match="criteria"):
        evaluate_semantic_cache_backend_matrix(candidates=(), criteria=cast(Any, "bad"))
    with pytest.raises(ValueError, match="criteria"):
        select_semantic_cache_backend(candidates=(), criteria=cast(Any, "bad"))
    with pytest.raises(ValueError, match="final_decision"):
        build_semantic_cache_backend_matrix_id(
            candidates=(_candidate(),),
            criteria=_criteria(),
            final_decision=cast(Any, "bad"),
        )
    with pytest.raises(ValueError, match="candidate"):
        evaluate_semantic_cache_backend_candidate(candidate=cast(Any, "bad"), criteria=_criteria())
    with pytest.raises(ValueError, match="unsafe runtime scope"):
        replace(_candidate(), supported_surfaces=("insight", "fastapi"))
    with pytest.raises(ValueError, match="unsafe runtime scope"):
        replace(_candidate(), supported_surfaces=("insight", "fast_api"))
    with pytest.raises(ValueError, match="unsafe runtime scope"):
        replace(_candidate(), supported_surfaces=("insight", "open-api"))
    with pytest.raises(ValueError, match="unsafe runtime scope"):
        replace(_candidate(), capability_flags=("label-only", "provider-call"))


def test_direct_decision_objects_reject_inconsistent_shapes() -> None:
    eligible = evaluate_semantic_cache_backend_candidate(
        candidate=_candidate(), criteria=_criteria()
    )
    selected = select_semantic_cache_backend(candidates=(_candidate(),), criteria=_criteria())

    with pytest.raises(ValueError, match="selected decision shape"):
        replace(selected, selected_candidate_id=None)
    with pytest.raises(ValueError, match="selected decision shape"):
        replace(selected, candidate_id="candidate:redis")
    with pytest.raises(ValueError, match="selected decision shape"):
        replace(selected, rejected_candidate_ids=("candidate:redis",))
    with pytest.raises(ValueError, match="eligible decision shape"):
        replace(eligible, rejected_candidate_ids=("candidate:redis",))
    with pytest.raises(ValueError, match="ineligible decision shape"):
        SemanticCacheBackendSelectionDecision(
            decision_id="semantic-cache-backend:000000000000000000000004",
            decision=DECISION_INELIGIBLE,
            policy_version="semantic-cache-sc-g5-v1",
            selected_candidate_id=None,
            selected_backend_label=None,
            candidate_id="candidate:redis",
            backend_label=BACKEND_LABEL_REDIS,
            reason_codes=(REASON_FALSE_HIT_RATE_EXCEEDED,),
            rejected_candidate_ids=("candidate:gptcache",),
            runtime_allowed=False,
            implementation_allowed=False,
            metadata={"scope": "forged"},
        )
    with pytest.raises(ValueError, match="no-selection decision shape"):
        SemanticCacheBackendSelectionDecision(
            decision_id="semantic-cache-backend-select:000000000000000000000001",
            decision=DECISION_NO_SELECTION,
            policy_version="semantic-cache-sc-g5-v1",
            selected_candidate_id=None,
            selected_backend_label=None,
            candidate_id="candidate:redis",
            backend_label=None,
            reason_codes=(REASON_NO_ELIGIBLE_CANDIDATE,),
            rejected_candidate_ids=("candidate:redis",),
            runtime_allowed=False,
            implementation_allowed=False,
            metadata={"scope": "forged"},
        )


def test_decision_id_prefix_must_match_decision_kind() -> None:
    with pytest.raises(ValueError, match="candidate-evaluation decision kind"):
        replace(
            evaluate_semantic_cache_backend_candidate(candidate=_candidate(), criteria=_criteria()),
            decision_id="semantic-cache-backend-select:000000000000000000000005",
        )
    with pytest.raises(ValueError, match="selection decision kind"):
        replace(
            select_semantic_cache_backend(candidates=(_candidate(),), criteria=_criteria()),
            decision_id="semantic-cache-backend:000000000000000000000006",
        )
    with pytest.raises(ValueError, match="selection decision kind"):
        SemanticCacheBackendSelectionDecision(
            decision_id="semantic-cache-backend:000000000000000000000007",
            decision=DECISION_NO_SELECTION,
            policy_version="semantic-cache-sc-g5-v1",
            selected_candidate_id=None,
            selected_backend_label=None,
            candidate_id=None,
            backend_label=None,
            reason_codes=(REASON_NO_ELIGIBLE_CANDIDATE,),
            rejected_candidate_ids=("candidate:redis",),
            runtime_allowed=False,
            implementation_allowed=False,
            metadata={"scope": "forged"},
        )


def test_matrix_invariants_fail_closed() -> None:
    candidate = _candidate()
    decision = evaluate_semantic_cache_backend_candidate(candidate=candidate, criteria=_criteria())
    matrix = evaluate_semantic_cache_backend_matrix(candidates=(candidate,), criteria=_criteria())
    forged_final = SemanticCacheBackendSelectionDecision(
        decision_id="semantic-cache-backend-select:000000000000000000000002",
        decision=DECISION_SELECTED,
        policy_version="semantic-cache-sc-g5-v1",
        selected_candidate_id=candidate.candidate_id,
        selected_backend_label=candidate.backend_label,
        candidate_id=None,
        backend_label=None,
        reason_codes=(REASON_SELECTED,),
        rejected_candidate_ids=(),
        runtime_allowed=False,
        implementation_allowed=False,
        metadata={"scope": "forged"},
    )

    with pytest.raises(ValueError, match="criteria"):
        replace(matrix, criteria=cast(Any, "bad"))
    with pytest.raises(ValueError, match="policy_version"):
        replace(matrix, policy_version="other")
    with pytest.raises(ValueError, match="duplicate candidate_id"):
        replace(matrix, candidates=(candidate, candidate))
    with pytest.raises(ValueError, match="candidate_decisions"):
        replace(matrix, candidate_decisions=cast(Any, ("bad",)))
    with pytest.raises(ValueError, match="candidate_decisions"):
        replace(matrix, candidate_decisions=(forged_final,))
    with pytest.raises(ValueError, match="final_decision"):
        replace(matrix, final_decision=cast(Any, "bad"))
    with pytest.raises(ValueError, match="final_decision"):
        replace(matrix, final_decision=forged_final)
    with pytest.raises(ValueError, match="matrix_id"):
        replace(matrix, matrix_id="matrix:forged")
    assert decision.decision == DECISION_ELIGIBLE


def test_matrix_constructor_rejects_forged_selected_decision_for_ineligible_candidate() -> None:
    candidate = _candidate(
        evidence=_evidence(false_hit_rate_bps=1),
        current_head_ci_passed=False,
        human_approval_record_id=None,
    )
    candidate_decision = evaluate_semantic_cache_backend_candidate(
        candidate=candidate,
        criteria=_criteria(),
    )
    forged_final = SemanticCacheBackendSelectionDecision(
        decision_id="semantic-cache-backend-select:000000000000000000000003",
        decision=DECISION_SELECTED,
        policy_version="semantic-cache-sc-g5-v1",
        selected_candidate_id=candidate.candidate_id,
        selected_backend_label=candidate.backend_label,
        candidate_id=None,
        backend_label=None,
        reason_codes=(REASON_SELECTED,),
        rejected_candidate_ids=(),
        runtime_allowed=False,
        implementation_allowed=False,
        metadata={"scope": "forged"},
    )

    with pytest.raises(ValueError, match="final_decision"):
        SemanticCacheBackendEvaluationMatrix(
            matrix_id="matrix:forged",
            policy_version="semantic-cache-sc-g5-v1",
            criteria=_criteria(),
            candidates=(candidate,),
            candidate_decisions=(candidate_decision,),
            final_decision=forged_final,
        )


def test_validation_helpers_reject_bad_numbers_and_tokens() -> None:
    with pytest.raises(ValueError, match="integer"):
        replace(_criteria(), max_false_hit_rate_bps=True)
    with pytest.raises(ValueError, match="between"):
        replace(_criteria(), max_false_hit_rate_bps=10001)
    with pytest.raises(ValueError, match="non-negative"):
        replace(_candidate(), latency_saved_p95_ms=-1)
    with pytest.raises(ValueError, match="integer"):
        replace(_candidate(), latency_saved_p95_ms=True)
    with pytest.raises(ValueError, match="must be a string"):
        replace(_candidate(), candidate_id=cast(Any, 123))
    with pytest.raises(ValueError, match="whitespace"):
        replace(_candidate(), candidate_id="candidate bad")
    with pytest.raises(ValueError, match="unsupported characters"):
        replace(_candidate(), candidate_id="candidate$bad")
    with pytest.raises(ValueError, match="unsafe token"):
        replace(_candidate(), candidate_id="sk-secret")
    assert (
        SemanticCacheBackendSafetyEvidence(
            evidence_id="risk-audit",
            sc_g2_contract_id="contract:sc-g2",
            sc_g3_contract_id="contract:sc-g3",
            sc_g4_contract_id="contract:sc-g4",
            source_fingerprints=("sha256:source-a",),
            eval_event_ids=("eval:1",),
            admission_decision_id="admission:1",
            promotion_ids=("promotion:1",),
            replay_entry_ids=("replay:1",),
            false_hit_rate_bps=0,
            stale_answer_rate_bps=0,
            policy_mismatch_count=0,
            model_mismatch_count=0,
            context_leakage_count=0,
            admission_blocked_hit_count=0,
            blocked_surface_hit_count=0,
            negative_control_count=25,
            fresh_runtime_comparison_count=25,
            evidence_fingerprints=("sha256:evidence",),
            metadata={"scope": "sc-g5"},
        ).evidence_id
        == "risk-audit"
    )
    for unsafe_value in (
        "access_token",
        "ghp_test_token",
        "github_pat_test_token",
        "xoxb-test-token",
        "eyJ.test.signature",
        "pass" + "word:blocked-value",
        "p" + "wd:blocked-value",
        "proof:healthkit",
        "proof:health_kit",
        "proof:health-kit",
        "proof:raw_prompt",
        "proof:raw_queries",
        "proof:normalized_queries",
        "proof:raw_model_response",
        "proof:raw-model-response",
        "proof:raw:model:response",
        "proof:account-id-123",
        "proof:billing",
        "proof:legal",
    ):
        with pytest.raises(ValueError, match="unsafe"):
            replace(_candidate(), current_head_ci_proof_id=unsafe_value)
        with pytest.raises(ValueError, match="unsafe"):
            replace(_candidate(), human_approval_record_id=unsafe_value)
    for generic_value in ("foo", "bar", "proof:ci"):
        with pytest.raises(ValueError, match="current-head CI proof shape"):
            replace(_candidate(), current_head_ci_proof_id=generic_value)
        with pytest.raises(ValueError, match="structured proof"):
            replace(_candidate(), human_approval_record_id=generic_value)
    for prefix_only_value in ("ci:current-head:", "verification-bundle:ci:"):
        with pytest.raises(ValueError, match="current-head CI proof shape"):
            replace(_candidate(), current_head_ci_proof_id=prefix_only_value)
    for prefix_only_value in ("approval:human:", "verification-bundle:approval:"):
        with pytest.raises(ValueError, match="proof evidence"):
            replace(_candidate(), human_approval_record_id=prefix_only_value)
    with pytest.raises(ValueError, match="human approval proof shape"):
        replace(_candidate(), human_approval_record_id="approval:human:placeholder")
    for unsafe_proof_token in (
        "raw_prompt",
        "provider_payload",
        "billing",
        "health_kit",
        "local_support_plane",
        "plugin:control-plane",
        "second_source_of_truth",
    ):
        with pytest.raises(ValueError, match="unsafe proof token"):
            replace(_evidence(), source_fingerprints=(unsafe_proof_token,))
        with pytest.raises(ValueError, match="unsafe proof token"):
            replace(_evidence(), eval_event_ids=(unsafe_proof_token,))
        with pytest.raises(ValueError, match="unsafe proof token"):
            replace(_evidence(), evidence_fingerprints=(unsafe_proof_token,))
    for unsafe_runtime_token in (
        "aiohttp",
        "backend-client",
        "dependency-addition",
        "fastapi",
        "fast_api",
        "httpx",
        "insight-route",
        "openapi",
        "open-api",
        "network",
        "requests",
        "route-wiring",
        "runtime-serving",
        "serving-backend",
        "socket",
        "urllib",
        "vector-search",
        "file-write",
    ):
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            replace(_evidence(), source_fingerprints=(unsafe_runtime_token,))
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            replace(_evidence(), eval_event_ids=(unsafe_runtime_token,))
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            replace(_evidence(), promotion_ids=(unsafe_runtime_token,))
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            replace(_evidence(), replay_entry_ids=(unsafe_runtime_token,))
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            replace(_evidence(), evidence_fingerprints=(unsafe_runtime_token,))
    for unsafe_evidence in (
        lambda: replace(_evidence(), sc_g2_contract_id="contract:raw_prompt"),
        lambda: replace(_evidence(), sc_g3_contract_id="contract:provider_payload"),
        lambda: replace(_evidence(), sc_g4_contract_id="contract:raw_model_response"),
        lambda: replace(_evidence(), admission_decision_id="admission:raw_prompt"),
        lambda: replace(_evidence(), evidence_id="evidence:auth:truth"),
        lambda: replace(_evidence(), evidence_id="evidence:local_support_plane"),
        lambda: replace(_evidence(), evidence_id="evidence:plugin:control-plane"),
        lambda: replace(_evidence(), evidence_id="evidence:second_source_of_truth"),
    ):
        with pytest.raises(ValueError, match="unsafe proof token"):
            unsafe_evidence()
    for unsafe_backend_version in ("redis_url", "connection:string", "runtime_config"):
        with pytest.raises(ValueError, match="unsafe proof token"):
            replace(_candidate(), backend_version=unsafe_backend_version)
    for unsafe_backend_version in (
        "fastapi",
        "fastapiv1",
        "fast_apiv1",
        "openapi",
        "open_apiv3",
        "network",
        "networkv1",
        "dbv1",
        "file-write",
        "filewritev2",
        "file_writev2",
        "gptcacheclient",
        "gptcacheclientv2",
        "gptcacheclientsv2",
        "gptcachebackendv1",
        "vector_searchv1",
        "semantic_similarityv2",
        "backend_clientv2",
        "dependency_additionv2",
        "redis_clientv1",
        "gptcache_clientv2",
    ):
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            replace(_candidate(), backend_version=unsafe_backend_version)
    for unsafe_split_runtime_token in ("fast_api", "open-api"):
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            replace(
                _candidate(),
                current_head_ci_proof_id=(
                    f"ci:current-head:d91b58100:run-25914493764:{unsafe_split_runtime_token}"
                ),
            )
        with pytest.raises(ValueError, match="unsafe metadata"):
            replace(_candidate(), metadata={"scope": unsafe_split_runtime_token})
    with pytest.raises(ValueError, match="unsafe metadata"):
        replace(_candidate(), metadata={"scope": "openapiv3"})
    with pytest.raises(ValueError, match="unsafe metadata"):
        replace(_candidate(), metadata={"scope": "dbv1"})
    for unsafe_scalar_evidence_id in (
        lambda: replace(_evidence(), evidence_id="evidence:fastapi"),
        lambda: replace(_evidence(), evidence_id="evidence:fast_api"),
        lambda: replace(_evidence(), evidence_id="evidence:fastapiv1"),
        lambda: replace(_evidence(), evidence_id="evidence:dbv1"),
        lambda: replace(_evidence(), evidence_id="evidence:gptcacheclient"),
        lambda: replace(_evidence(), evidence_id="evidence:gptcacheclientv2"),
        lambda: replace(_evidence(), evidence_id="evidence:gptcachebackendv1"),
        lambda: replace(_evidence(), source_fingerprints=("gptcacheclient",)),
        lambda: replace(_evidence(), source_fingerprints=("gptcacheclientv2",)),
        lambda: replace(_evidence(), source_fingerprints=("gptcachebackendv1",)),
        lambda: replace(_evidence(), sc_g2_contract_id="contract:openapi"),
        lambda: replace(_evidence(), sc_g2_contract_id="contract:open-api"),
        lambda: replace(_evidence(), sc_g2_contract_id="contract:openapiv3"),
        lambda: replace(_evidence(), sc_g3_contract_id="contract:network"),
        lambda: replace(_evidence(), sc_g3_contract_id="contract:networkv1"),
        lambda: replace(_evidence(), sc_g4_contract_id="contract:file-write"),
        lambda: replace(_evidence(), sc_g4_contract_id="contract:filewritev2"),
        lambda: replace(_evidence(), admission_decision_id="admission:provider"),
    ):
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            unsafe_scalar_evidence_id()
    safe_digest = replace(_evidence(), source_fingerprints=("sha256:abdb0000",))
    assert safe_digest.source_fingerprints == ("sha256:abdb0000",)
    safe_db_digest = replace(
        _evidence(),
        source_fingerprints=("sha256:db12345",),
        evidence_fingerprints=("sha256:db12345",),
    )
    assert safe_db_digest.source_fingerprints == ("sha256:db12345",)
    assert safe_db_digest.evidence_fingerprints == ("sha256:db12345",)
    with pytest.raises(ValueError, match="unsafe runtime scope"):
        replace(_evidence(), source_fingerprints=("sha256:dbv1",))
    for unsafe_candidate_id in ("candidate:fastapi", "candidate:openapi", "candidate:network"):
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            replace(_candidate(), candidate_id=unsafe_candidate_id)
    for unsafe_policy_version in (
        "semantic-cache-fastapi-v1",
        "semantic-cache-openapi-v1",
        "semantic-cache-network-v1",
    ):
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            replace(_candidate(), policy_version=unsafe_policy_version)
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            replace(_criteria(), policy_version=unsafe_policy_version)
    for unsafe_required_surface in ("fastapi", "openapi", "network"):
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            replace(_criteria(), required_surface=unsafe_required_surface)
    for unsafe_rollback in (
        lambda: replace(_rollback(), proof_id="rollback:redis:fastapi"),
        lambda: replace(_rollback(), kill_switch_proof_id="proof:kill-switch:redis:network"),
        lambda: replace(_rollback(), stop_rule_replay_ids=("replay:stop-rule:redis:embeddings",)),
    ):
        with pytest.raises(ValueError, match="unsafe runtime scope"):
            unsafe_rollback()
    with pytest.raises(ValueError, match="duplicate"):
        replace(_candidate(), supported_surfaces=("insight", "insight"))
    with pytest.raises(ValueError, match="non-empty"):
        replace(_candidate(), supported_surfaces=())
    with pytest.raises(ValueError, match="bool"):
        replace(_criteria(), require_human_approval=cast(Any, "yes"))
    for bare_string_tuple_field in (
        lambda: replace(_evidence(), source_fingerprints=cast(Any, "abc")),
        lambda: replace(_candidate(), supported_surfaces=cast(Any, "insight")),
        lambda: replace(_rollback(), disabled_state_test_ids=cast(Any, "test-disabled")),
        lambda: replace(
            evaluate_semantic_cache_backend_candidate(candidate=_candidate(), criteria=_criteria()),
            reason_codes=cast(Any, "eligible"),
        ),
    ):
        with pytest.raises(ValueError, match="tuple/list"):
            bare_string_tuple_field()


def test_stable_mapping_rejects_unsupported_value() -> None:
    with pytest.raises(ValueError, match="unsupported stable mapping"):
        to_stable_mapping(object())


def test_matrix_rejects_non_candidate_tuple_item() -> None:
    matrix = evaluate_semantic_cache_backend_matrix(
        candidates=(_candidate(),), criteria=_criteria()
    )

    with pytest.raises(ValueError, match="candidates"):
        replace(matrix, candidates=cast(Any, ("bad",)))


def test_no_core_ai_export_side_door() -> None:
    content = (REPO_ROOT / "core" / "ai" / "__init__.py").read_text(encoding="utf-8")

    assert "semantic_cache_backend_selection" not in content
    assert "SemanticCacheBackend" not in content


def test_core_ai_facade_does_not_eagerly_import_runtime_for_sc_g5() -> None:
    script = """
import importlib
import sys

facade = importlib.import_module("core.ai")
assert "core.ai.insight_runtime" not in sys.modules
assert "core.insight.philosophical_runtime" not in sys.modules

importlib.import_module("core.ai.semantic_cache_backend_selection")
assert "core.ai.insight_runtime" not in sys.modules
assert "core.insight.philosophical_runtime" not in sys.modules

getattr(facade, "prepare_insight_runtime")
assert "core.ai.insight_runtime" in sys.modules
"""

    subprocess.run([sys.executable, "-c", script], cwd=REPO_ROOT, check=True)


def test_module_has_no_forbidden_imports_or_nondeterministic_calls() -> None:
    assert_no_forbidden_semantic_cache_imports(MODULE)
    assert_no_forbidden_semantic_cache_calls(MODULE)


def test_import_guard_rejects_path_constructor_writes(tmp_path: Path) -> None:
    source = tmp_path / "unsafe.py"
    source.write_text(
        "from pathlib import Path\n"
        "Path('payload.txt').write_text('payload')\n"
        "target = Path('payload.bin')\n"
        "target.write_bytes(b'payload')\n"
        "annotated: Path = Path('annotated.txt')\n"
        "annotated.write_text('payload')\n"
        "Path('opened.txt').open('w').write('payload')\n"
        "alias = Path('alias-opened.txt')\n"
        "alias.open('wb').write(b'payload')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.write"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_tracks_path_constructor_aliases(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_path_constructor_alias.py"
    source.write_text(
        "from pathlib import Path\n"
        "from pathlib import PosixPath\n"
        "P = Path\n"
        "P('payload.txt').write_text('payload')\n"
        "AnnotatedPath: object = Path\n"
        "AnnotatedPath('payload2.txt').write_text('payload')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.write"):
        assert_no_forbidden_semantic_cache_calls(source)

    concrete_source = tmp_path / "unsafe_annotated_concrete_path_alias.py"
    concrete_source.write_text(
        "from pathlib import PosixPath\n"
        "P: object = PosixPath\n"
        "P('payload.txt').write_text('payload')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.write"):
        assert_no_forbidden_semantic_cache_calls(concrete_source)


def test_import_guard_tracks_destructured_path_constructor_aliases(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_destructured_path_alias.py"
    source.write_text(
        "from pathlib import Path\n"
        "P, _ = Path, None\n"
        "P('payload.txt').write_text('payload')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.write"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_dynamic_path_getattr_writes(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_path_getattr.py"
    source.write_text(
        "from pathlib import Path\n"
        "getattr(Path('payload.txt'), 'write_text')('payload')\n"
        "target = Path('payload.bin')\n"
        "writer = getattr(target, 'write_bytes')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.getattr"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_fully_qualified_path_writes(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_pathlib.py"
    source.write_text(
        "import pathlib\n"
        "pathlib.Path.write_text(pathlib.Path('payload.txt'), 'payload')\n"
        "pathlib.Path.write_bytes(pathlib.Path('payload.bin'), b'payload')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="pathlib.Path.write_text"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_path_class_method_open_write_modes(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_path_class_open.py"
    source.write_text(
        "from pathlib import Path\n"
        "import pathlib\n"
        "Path.open(Path('payload.txt'), 'w')\n"
        "pathlib.Path.open(pathlib.Path('payload.bin'), mode='wb')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.open"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_joined_path_writes(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_joined_path.py"
    source.write_text(
        "from pathlib import Path\n"
        "(Path('out') / 'payload.txt').write_text('payload')\n"
        "base = Path('base')\n"
        "(base / 'payload.bin').write_bytes(b'payload')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.write"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_tracks_joined_path_aliases(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_joined_alias.py"
    source.write_text(
        "from pathlib import Path\n"
        "target = Path('out') / 'payload.txt'\n"
        "target.write_text('payload')\n"
        "joined = Path('out').joinpath('payload.bin')\n"
        "joined.open('wb')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.write"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_environment_reads(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_env.py"
    source.write_text(
        "import os\n"
        "os.getenv('SEMANTIC_CACHE_ENABLED')\n"
        "os.environ['SEMANTIC_CACHE_ENABLED']\n"
        "getenv = os.getenv\n"
        "getenv('REDIS_URL')\n"
        "annotated_getenv: object = os.getenv\n"
        "env = os.environ\n"
        "env.get('REDIS_URL')\n"
        "env['GPTCACHE_URL']\n"
        "annotated_env: object = os.environ\n"
        "annotated_env.get('CACHE_URL')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="os.getenv"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_direct_os_environ_value_reads(tmp_path: Path) -> None:
    for filename, source_text in {
        "unsafe_env_dict.py": "import os\nsettings = dict(os.environ)\n",
        "unsafe_env_getattr.py": "import os\nsettings = getattr(os, 'environ')\n",
        "unsafe_env_getattr_alias.py": "import os\ng = getattr\nsettings = g(os, 'environ')\n",
        "unsafe_env_getattr_dict.py": "import os\nsettings = dict(getattr(os, 'environ'))\n",
        "unsafe_env_dunder_dict.py": "import os\nsettings = os.__dict__['environ']\n",
        "unsafe_env_vars.py": "import os\nsettings = vars(os)['environ']\n",
        "unsafe_env_nested_dict.py": "import os\nsettings = {'env': os.environ}\n",
        "unsafe_env_unpack.py": "import os\nsettings = {**os.environ}\n",
        "unsafe_env_loop.py": "import os\nfor key in os.environ:\n    pass\n",
        "unsafe_env_if.py": "import os\nif os.environ:\n    pass\n",
        "unsafe_env_comprehension.py": "import os\nkeys = [key for key in os.environ]\n",
        "unsafe_env_alias_value.py": "import os\nenv = os.environ\nsettings = dict(env)\n",
        "unsafe_env_tuple_alias.py": "import os\nenv, other = os.environ, {}\nsettings = dict(env)\n",
        "unsafe_env_copy_alias.py": "import os\nreader = os.environ.copy\nsettings = reader()\n",
        "unsafe_env_list_literal.py": "import os\nsettings = [os.environ]\n",
        "unsafe_env_tuple_literal.py": "import os\nsettings = (os.environ,)\n",
        "unsafe_env_return.py": "import os\ndef leak():\n    return os.environ\n",
        "unsafe_env_yield.py": "import os\ndef leak():\n    yield os.environ\n",
    }.items():
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match="os.environ.value"):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_path_open_context_manager_writes(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_context.py"
    source.write_text(
        "from pathlib import Path\n"
        "with Path('context.txt').open('w') as handle:\n"
        "    handle.write('payload')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.open.write"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_write_mode_path_open(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_open_mode.py"
    source.write_text(
        "from pathlib import Path\n"
        "Path('truncate.txt').open('w')\n"
        "target = Path('append.txt')\n"
        "target.open(mode='a')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.open.write-mode"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_dynamic_path_open_modes(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_dynamic_open_mode.py"
    source.write_text(
        "from pathlib import Path\n"
        "mode = 'w'\n"
        "Path('payload.txt').open(mode)\n"
        "target = Path('payload.bin')\n"
        "target.open(mode=mode)\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.open.write-mode"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_unknown_path_open_kwargs(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_open_kwargs.py"
    source.write_text(
        "from pathlib import Path\n"
        "kwargs = {'mode': 'w'}\n"
        "Path('payload.txt').open(**kwargs)\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.open.write-mode"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_path_effect_method_aliases(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_method_alias.py"
    source.write_text(
        "from pathlib import Path\n"
        "writer = Path('payload.txt').write_text\n"
        "mutator = Path('payload-dir').mkdir\n"
        "opener = Path('payload.bin').open\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.method-alias"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_callable_effect_wrappers(tmp_path: Path) -> None:
    for filename, source_text, expected in (
        (
            "unsafe_partial_open.py",
            "from functools import partial\npartial(open, 'payload.txt', 'w')()\n",
            "functools.partial",
        ),
        (
            "unsafe_partial_path.py",
            (
                "from functools import partial\n"
                "from pathlib import Path\n"
                "partial(Path('payload.txt').write_text, 'payload')()\n"
            ),
            "functools.partial",
        ),
        (
            "unsafe_methodcaller.py",
            (
                "from operator import methodcaller\n"
                "from pathlib import Path\n"
                "methodcaller('write_text', 'payload')(Path('payload.txt'))\n"
            ),
            "operator.methodcaller",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match=expected):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_path_mutations_and_os_file_mutations(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_mutations.py"
    source.write_text(
        "from pathlib import Path\n"
        "import os\n"
        "Path('payload.txt').touch()\n"
        "(Path('payload-dir') / 'nested').mkdir()\n"
        "target = Path('old.txt')\n"
        "target.rename('new.txt')\n"
        "target.unlink()\n"
        "os.open('payload.txt', os.O_WRONLY | os.O_CREAT)\n"
        "os.mkdir('payload-dir')\n"
        "os.makedirs('payload-dir/nested')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.mutate"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_network_imports_and_calls(tmp_path: Path) -> None:
    imports = tmp_path / "unsafe_network_imports.py"
    imports.write_text(
        "import urllib.request\n" "import socket\n" "import http.client\n" "import requests\n",
        encoding="utf-8",
    )
    calls = tmp_path / "unsafe_network_calls.py"
    calls.write_text(
        "import urllib.request\n"
        "import socket\n"
        "import http.client\n"
        "import requests\n"
        "urllib.request.urlopen('https://example.invalid')\n"
        "socket.create_connection(('example.invalid', 443))\n"
        "http.client.HTTPSConnection('example.invalid')\n"
        "requests.get('https://example.invalid')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="forbidden semantic-cache imports"):
        assert_no_forbidden_semantic_cache_imports(imports)
    with pytest.raises(AssertionError, match="urlopen"):
        assert_no_forbidden_semantic_cache_calls(calls)


def test_import_guard_rejects_process_launch_imports_and_calls(tmp_path: Path) -> None:
    imports = tmp_path / "unsafe_process_imports.py"
    imports.write_text("import subprocess\n", encoding="utf-8")
    calls = tmp_path / "unsafe_process_calls.py"
    calls.write_text(
        "import os\n"
        "import subprocess\n"
        "subprocess.run(['/usr/bin/curl', 'https://example.invalid'])\n"
        "os.system('/usr/bin/curl https://example.invalid')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="forbidden semantic-cache imports"):
        assert_no_forbidden_semantic_cache_imports(imports)
    with pytest.raises(AssertionError, match="subprocess.run"):
        assert_no_forbidden_semantic_cache_calls(calls)


def test_import_guard_rejects_dynamic_os_process_calls(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_dynamic_os.py"
    source.write_text(
        "__import__('os').system('/usr/bin/curl https://example.invalid')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="os.system"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_string_execution_calls(tmp_path: Path) -> None:
    for filename, source_text in (
        ("unsafe_eval.py", "eval(\"__import__('redis')\")\n"),
        ("unsafe_exec.py", "exec(\"open('payload.txt', 'w').write('x')\")\n"),
        ("unsafe_compile.py", "compile(\"__import__('redis')\", '<sc-g5>', 'exec')\n"),
        ("unsafe_eval_alias.py", "runner = eval\nrunner(\"__import__('redis')\")\n"),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match="string-execution|eval|exec|compile"):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_importlib_dynamic_os_effects(tmp_path: Path) -> None:
    for filename, source_text in {
        "unsafe_importlib_os_effect.py": (
            "import importlib\n"
            "importlib.import_module('os').system('/usr/bin/curl https://example.invalid')\n"
        ),
        "unsafe_importlib_alias_os_effect.py": (
            "from importlib import import_module\n"
            "import_module('os').system('/usr/bin/curl https://example.invalid')\n"
        ),
        "unsafe_importlib_module_alias.py": (
            "import importlib\n"
            "module = importlib.import_module('os')\n"
            "module.system('/usr/bin/curl https://example.invalid')\n"
        ),
        "unsafe_builtin_import_alias_os_effect.py": (
            "imp = __import__\n" "imp('os').system('/usr/bin/curl https://example.invalid')\n"
        ),
    }.items():
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match="os.system|__dynamic_import__"):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_chained_dynamic_import_module_effects(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_chained_dynamic_import_module.py"
    source.write_text(
        "__import__('importlib').import_module('subprocess').run(['echo', 'bad'])\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="__dynamic_import__"):
        assert_no_forbidden_semantic_cache_imports(source)
    with pytest.raises(AssertionError, match="__dynamic_import__"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_os_effect_aliases(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_os_alias.py"
    source.write_text(
        "import os\n" "launcher = os.system\n" "opener = os.open\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="os.system.alias"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_tuple_unpacked_effect_aliases(tmp_path: Path) -> None:
    for filename, source_text, expected in (
        (
            "unsafe_tuple_open_alias.py",
            "writer, _ = open, None\nwriter('payload.txt', 'w')\n",
            "open.alias",
        ),
        (
            "unsafe_tuple_os_alias.py",
            "import os\nlauncher, _ = os.system, None\nlauncher('/usr/bin/curl https://example.invalid')\n",
            "os.system.alias",
        ),
        (
            "unsafe_tuple_path_write_alias.py",
            "from pathlib import Path\nwriter, _ = Path('payload.txt').write_text, None\nwriter('bad')\n",
            "Path.method-alias",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match=expected):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_tuple_unpacked_dynamic_import_aliases(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_tuple_import_alias.py"
    source.write_text(
        "loader, _ = __import__, None\nloader('redis')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="redis"):
        assert_no_forbidden_semantic_cache_imports(source)
    with pytest.raises(AssertionError, match="__dynamic_import__"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_path_objects_from_containers(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_path_container.py"
    source.write_text(
        "from pathlib import Path\n"
        "path = Path('payload.txt')\n"
        "paths = [path]\n"
        "paths[0].write_text('payload')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.write"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_annotated_path_containers(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_annotated_path_container.py"
    source.write_text(
        "from pathlib import Path\n"
        "paths: object = [Path('payload.txt')]\n"
        "paths[0].write_text('payload')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.write"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_concrete_pathlib_constructors(tmp_path: Path) -> None:
    for filename, source_text in (
        (
            "unsafe_posix_path.py",
            "from pathlib import PosixPath\nPosixPath('payload.txt').write_text('payload')\n",
        ),
        (
            "unsafe_qualified_posix_path.py",
            "import pathlib\npathlib.PosixPath('payload.txt').write_text('payload')\n",
        ),
        (
            "unsafe_windows_path.py",
            "from pathlib import WindowsPath\nWindowsPath('payload.txt').write_text('payload')\n",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match="Path.write"):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_concrete_pathlib_class_methods(tmp_path: Path) -> None:
    for filename, source_text, expected in (
        (
            "unsafe_posix_class_write.py",
            "from pathlib import PosixPath\nPosixPath.write_text(PosixPath('payload.txt'), 'payload')\n",
            "Path.write",
        ),
        (
            "unsafe_posix_class_open.py",
            "from pathlib import PosixPath\nPosixPath.open(PosixPath('payload.txt'), 'w')\n",
            "Path.open.write-mode",
        ),
        (
            "unsafe_qualified_posix_class_chmod.py",
            "import pathlib\npathlib.PosixPath.chmod(pathlib.PosixPath('payload.txt'), 0o777)\n",
            "Path.mutate",
        ),
        (
            "unsafe_windows_class_alias.py",
            "from pathlib import WindowsPath\nwriter = WindowsPath.write_text\nwriter(WindowsPath('payload.txt'), 'payload')\n",
            "Path.method-alias",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match=expected):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_pathlib_link_and_chmod_mutations(tmp_path: Path) -> None:
    for filename, source_text, expected in (
        (
            "unsafe_symlink.py",
            "from pathlib import Path\nPath('payload.txt').symlink_to('target.txt')\n",
            "Path.mutate",
        ),
        (
            "unsafe_hardlink.py",
            "from pathlib import Path\nPath('payload.txt').hardlink_to('target.txt')\n",
            "Path.mutate",
        ),
        (
            "unsafe_chmod_alias.py",
            "from pathlib import Path\nmutate = Path('payload.txt').chmod\nmutate(0o777)\n",
            "Path.method-alias",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match=expected):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_walrus_bound_effect_calls(tmp_path: Path) -> None:
    for filename, source_text, expected in (
        (
            "unsafe_walrus_open.py",
            "(writer := open)('payload.txt', 'w')\n",
            "open.alias",
        ),
        (
            "unsafe_walrus_os.py",
            "import os\n(launcher := os.system)('/usr/bin/curl https://example.invalid')\n",
            "os.system",
        ),
        (
            "unsafe_walrus_path.py",
            "from pathlib import Path\n(writer := Path('payload.txt').write_text)('payload')\n",
            "Path.method-alias",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match=expected):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_effect_aliases_in_callable_defaults(tmp_path: Path) -> None:
    for filename, source_text, expected in (
        (
            "unsafe_default_open.py",
            "def write(writer=open):\n    writer('payload.txt', 'w')\n",
            "open.alias",
        ),
        (
            "unsafe_default_path.py",
            "from pathlib import Path\ndef write(writer=Path('payload.txt').write_text):\n    writer('payload')\n",
            "Path.method-alias",
        ),
        (
            "unsafe_default_os.py",
            "import os\ndef launch(launcher=os.system):\n    launcher('/usr/bin/curl https://example.invalid')\n",
            "os.system.alias",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match=expected):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_attribute_bound_effect_aliases(tmp_path: Path) -> None:
    for filename, source_text, expected in (
        (
            "unsafe_attr_open.py",
            "class C: pass\nC.writer = open\nC.writer('payload.txt', 'w')\n",
            "open.alias",
        ),
        (
            "unsafe_attr_os.py",
            "import os\nclass C: pass\nC.launcher = os.system\nC.launcher('/usr/bin/curl https://example.invalid')\n",
            "os.system.alias",
        ),
        (
            "unsafe_attr_path.py",
            "from pathlib import Path\nclass C: pass\nC.writer = Path('payload.txt').write_text\nC.writer('payload')\n",
            "Path.method-alias",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match=expected):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_dynamic_effect_storage_helpers(tmp_path: Path) -> None:
    for filename, source_text, expected in (
        (
            "unsafe_setattr_open.py",
            "class C: pass\nsetattr(C, 'writer', open)\nC.writer('payload.txt', 'w')\n",
            "setattr",
        ),
        (
            "unsafe_setattr_import.py",
            "class C: pass\nsetattr(C, 'loader', __import__)\nC.loader('redis')\n",
            "setattr",
        ),
        (
            "unsafe_globals.py",
            "globals()['writer'] = open\nwriter('payload.txt', 'w')\n",
            "globals",
        ),
        (
            "unsafe_effect_container.py",
            "effects = {'writer': open}\neffects['writer']('payload.txt', 'w')\n",
            "effect.container",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match=expected):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_attribute_bound_dynamic_import_refs(tmp_path: Path) -> None:
    for filename, source_text in (
        (
            "unsafe_attr_import.py",
            "class C: pass\nC.loader = __import__\nC.loader('redis')\n",
        ),
        (
            "unsafe_attr_builtins_import.py",
            "class C: pass\nC.loader = __builtins__['__import__']\nC.loader('redis')\n",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match="__dynamic_import__"):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_annotated_attribute_dynamic_import_refs(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_annotated_attr_import.py"
    source.write_text(
        "class C: pass\n" "C.loader: object = __import__\n" "C.loader('redis')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="__dynamic_import__"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_dunder_builtins_dynamic_imports(tmp_path: Path) -> None:
    for filename, source_text in (
        (
            "unsafe_builtins_attr_import.py",
            "__builtins__.__import__('redis')\n",
        ),
        (
            "unsafe_builtins_subscript_import.py",
            "__builtins__['__import__']('redis')\n",
        ),
        (
            "unsafe_builtins_getattr_import.py",
            "getattr(__builtins__, '__import__')('redis')\n",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match="redis"):
            assert_no_forbidden_semantic_cache_imports(source)
        with pytest.raises(AssertionError, match="__dynamic_import__"):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_dynamic_builtin_open_calls(tmp_path: Path) -> None:
    for filename, source_text in (
        (
            "unsafe_builtins_subscript_open.py",
            "__builtins__['open']('payload.txt', 'w')\n",
        ),
        (
            "unsafe_builtins_getattr_open.py",
            "getattr(__builtins__, 'open')('payload.txt', 'w')\n",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match="open"):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_path_returning_expr_writes(tmp_path: Path) -> None:
    for filename, source_text, expected in (
        (
            "unsafe_parent_mkdir.py",
            "from pathlib import Path\nPath('out/payload.txt').parent.mkdir()\n",
            "Path.mutate",
        ),
        (
            "unsafe_cwd_joinpath_write.py",
            "from pathlib import Path\nPath.cwd().joinpath('payload.txt').write_text('payload')\n",
            "Path.write",
        ),
        (
            "unsafe_resolve_write.py",
            "from pathlib import Path\nPath('payload.txt').resolve().write_text('payload')\n",
            "Path.write",
        ),
        (
            "unsafe_absolute_write.py",
            "from pathlib import Path\nPath('payload.txt').absolute().write_text('payload')\n",
            "Path.write",
        ),
        (
            "unsafe_with_name_write.py",
            "from pathlib import Path\nPath('payload.txt').with_name('other.txt').write_text('payload')\n",
            "Path.write",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match=expected):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_class_level_pathlib_getattr_effects(tmp_path: Path) -> None:
    for filename, source_text in (
        (
            "unsafe_path_class_getattr.py",
            "from pathlib import Path\ngetattr(Path, 'write_text')(Path('payload.txt'), 'payload')\n",
        ),
        (
            "unsafe_posix_class_getattr.py",
            "from pathlib import PosixPath\ngetattr(PosixPath, 'chmod')(PosixPath('payload.txt'), 0o777)\n",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match="Path.getattr"):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_os_dict_effect_lookups(tmp_path: Path) -> None:
    for filename, source_text, expected in (
        (
            "unsafe_os_dunder_dict_system.py",
            "import os\nos.__dict__['system']('/usr/bin/curl https://example.invalid')\n",
            "os.system",
        ),
        (
            "unsafe_vars_os_getenv.py",
            "import os\nvars(os)['getenv']('REDIS_URL')\n",
            "os.getenv",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match=expected):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_getattr_os_effect_aliases(tmp_path: Path) -> None:
    for filename, source_text, expected in (
        (
            "unsafe_getattr_os_system.py",
            "import os\nlauncher = getattr(os, 'system')\nlauncher('/usr/bin/curl https://example.invalid')\n",
            "os.system.alias",
        ),
        (
            "unsafe_getattr_alias_os_system_call.py",
            "import os\ng = getattr\ng(os, 'system')('/usr/bin/curl https://example.invalid')\n",
            "os.system",
        ),
        (
            "unsafe_getattr_os_getenv.py",
            "import os\nreader = getattr(os, 'getenv')\nreader('REDIS_URL')\n",
            "os.getenv.alias",
        ),
        (
            "unsafe_getattr_os_system_call.py",
            "import os\ngetattr(os, 'system')('/usr/bin/curl https://example.invalid')\n",
            "os.system",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match=expected):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_copy_and_open_alias_escape_hatches(tmp_path: Path) -> None:
    imports = tmp_path / "unsafe_file_imports.py"
    imports.write_text(
        "import io\nimport shutil\nfrom builtins import open as o\n", encoding="utf-8"
    )
    calls = tmp_path / "unsafe_file_calls.py"
    calls.write_text(
        "import io\n"
        "import shutil\n"
        "from builtins import open as o\n"
        "io.open('payload.txt', 'w')\n"
        "o('payload2.txt', 'w')\n"
        "shutil.copyfile('seed.txt', 'payload3.txt')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="forbidden semantic-cache imports"):
        assert_no_forbidden_semantic_cache_imports(imports)
    with pytest.raises(AssertionError, match="io.open"):
        assert_no_forbidden_semantic_cache_calls(calls)


def test_import_guard_rejects_dunder_builtins_open(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_dunder_builtins_open.py"
    source.write_text(
        "__builtins__.open('payload.txt', 'w')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="__builtins__.open"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_builtin_open_aliases(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_builtin_open_alias.py"
    source.write_text(
        "writer = open\n" "writer('payload.txt', 'w')\n" "annotated: object = open\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="open.alias"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_os_environ_mutation_methods(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_environ_mutations.py"
    source.write_text(
        "import os\n"
        "os.environ.setdefault('CACHE_BACKEND', 'redis')\n"
        "os.environ.update({'CACHE_BACKEND': 'gptcache'})\n"
        "os.environ.pop('CACHE_BACKEND', None)\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="os.environ.setdefault"):
        assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_dynamic_forbidden_imports(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_dynamic_import.py"
    source.write_text(
        "name = 'redis'\n"
        "__import__(name)\n"
        "import importlib\n"
        "importlib.import_module(name)\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="__dynamic_import__"):
        assert_no_forbidden_semantic_cache_imports(source)

    alias_source = tmp_path / "unsafe_dynamic_import_alias.py"
    alias_source.write_text("imp = __import__\nimp('redis')\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="redis"):
        assert_no_forbidden_semantic_cache_imports(alias_source)


def test_import_guard_rejects_dynamic_import_alias_refs(tmp_path: Path) -> None:
    for filename, source_text in (
        (
            "unsafe_builtins_subscript_import_alias.py",
            "loader = __builtins__['__import__']\nloader('redis')\n",
        ),
        (
            "unsafe_builtins_getattr_import_alias.py",
            "loader = getattr(__builtins__, '__import__')\nloader('redis')\n",
        ),
        (
            "unsafe_dynamic_import_default.py",
            "def load(loader=__import__):\n    loader('redis')\n",
        ),
    ):
        source = tmp_path / filename
        source.write_text(source_text, encoding="utf-8")

        with pytest.raises(AssertionError, match="__dynamic_import__"):
            assert_no_forbidden_semantic_cache_calls(source)


def test_import_guard_rejects_core_ai_runtime_facade_imports(tmp_path: Path) -> None:
    source = tmp_path / "unsafe_core_ai_facade_import.py"
    source.write_text(
        "from core.ai import prepare_insight_runtime\n"
        "from core.ai.insight_runtime import PreparedInsightRuntime\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="core.ai"):
        assert_no_forbidden_semantic_cache_imports(source)
