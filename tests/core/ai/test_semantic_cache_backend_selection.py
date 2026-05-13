from __future__ import annotations

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
    REASON_CURRENT_HEAD_CI_MISSING,
    REASON_FALSE_HIT_RATE_EXCEEDED,
    REASON_HUMAN_APPROVAL_MISSING,
    REASON_CONTEXT_LEAKAGE_EXCEEDED,
    REASON_FRESH_RUNTIME_COMPARISONS_MISSING,
    REASON_MODEL_MISMATCH_EXCEEDED,
    REASON_NEGATIVE_CONTROLS_MISSING,
    REASON_NO_ELIGIBLE_CANDIDATE,
    REASON_POLICY_MISMATCH_EXCEEDED,
    REASON_ROLLBACK_PROOF_MISSING,
    REASON_SC_G4_EVIDENCE_MISSING,
    REASON_SELECTED,
    REASON_STALE_ANSWER_RATE_EXCEEDED,
    SemanticCacheBackendCandidate,
    SemanticCacheBackendEvaluationMatrix,
    SemanticCacheBackendRollbackProof,
    SemanticCacheBackendSafetyEvidence,
    SemanticCacheBackendSelectionCriteria,
    SemanticCacheBackendSelectionDecision,
    evaluate_semantic_cache_backend_candidate,
    evaluate_semantic_cache_backend_matrix,
    select_semantic_cache_backend,
    to_stable_mapping,
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
    *, verified: bool = True, blast_radius_bps: int = 10
) -> SemanticCacheBackendRollbackProof:
    return SemanticCacheBackendRollbackProof(
        proof_id="rollback:backend:1",
        kill_switch_proof_id="proof:kill-switch",
        request_bypass_proof_id="proof:bypass",
        no_cache_fallback_proof_id="proof:no-cache",
        purge_invalidation_proof_id="proof:purge",
        disabled_state_test_ids=("test:disabled",),
        stop_rule_replay_ids=("replay:stop-rule",),
        rollback_runbook_id="runbook:rollback",
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
    human_approval_record_id: str | None = "approval:human",
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
        rollback_proof=_rollback() if rollback is None else rollback,
        latency_saved_p50_ms=50,
        latency_saved_p95_ms=latency_saved_p95_ms,
        provider_calls_avoided_count=5,
        cost_saved_microunits=cost_saved_microunits,
        current_head_ci_passed=current_head_ci_passed,
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
    assert "blocked_surface_hits" in decision.reason_codes
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


def test_selector_recomputes_safety_and_ignores_forged_decisions() -> None:
    unsafe = _candidate(
        evidence=_evidence(false_hit_rate_bps=1),
        current_head_ci_passed=False,
        human_approval_record_id=None,
    )
    forged = SemanticCacheBackendSelectionDecision(
        decision_id="decision:forged",
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


def test_metadata_rejects_raw_payloads_paths_and_product_truth_sources() -> None:
    unsafe_metadata = (
        {"raw_prompt": "plan"},
        {"provider_payload": "payload"},
        {"path": "/tmp/cache"},
        {"truth": "advisory wiki"},
        {"credential": "blocked-value"},
        {"health": "HealthKit symptom"},
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

    assert stable["candidate_ids"] == ["candidate:redis"]


def test_json_metadata_copy_rejects_non_finite_and_unsupported_values() -> None:
    for metadata in ({"value": float("nan")}, {"value": object()}):
        with pytest.raises(ValueError):
            replace(_candidate(), metadata=cast(Any, metadata))
    with pytest.raises(ValueError, match="metadata must be a mapping"):
        replace(_candidate(), metadata=cast(Any, ["not-a-mapping"]))


def test_criteria_cannot_enable_runtime_or_implementation() -> None:
    with pytest.raises(ValueError):
        replace(_criteria(), runtime_allowed=True)
    with pytest.raises(ValueError):
        replace(_criteria(), implementation_allowed=True)


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
    with pytest.raises(ValueError, match="candidate"):
        evaluate_semantic_cache_backend_candidate(candidate=cast(Any, "bad"), criteria=_criteria())


def test_matrix_invariants_fail_closed() -> None:
    candidate = _candidate()
    decision = evaluate_semantic_cache_backend_candidate(candidate=candidate, criteria=_criteria())
    matrix = evaluate_semantic_cache_backend_matrix(candidates=(candidate,), criteria=_criteria())
    forged_final = SemanticCacheBackendSelectionDecision(
        decision_id="decision:forged-final",
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
    forged_candidate_decision = SemanticCacheBackendSelectionDecision(
        decision_id="decision:forged-candidate",
        decision=DECISION_ELIGIBLE,
        policy_version="semantic-cache-sc-g5-v1",
        selected_candidate_id=None,
        selected_backend_label=None,
        candidate_id=candidate.candidate_id,
        backend_label=candidate.backend_label,
        reason_codes=(REASON_SELECTED,),
        rejected_candidate_ids=(),
        runtime_allowed=False,
        implementation_allowed=False,
        metadata={"scope": "forged"},
    )
    forged_final = SemanticCacheBackendSelectionDecision(
        decision_id="decision:forged-final",
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

    with pytest.raises(ValueError, match="candidate_decisions"):
        SemanticCacheBackendEvaluationMatrix(
            matrix_id="matrix:forged",
            policy_version="semantic-cache-sc-g5-v1",
            criteria=_criteria(),
            candidates=(candidate,),
            candidate_decisions=(forged_candidate_decision,),
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
    with pytest.raises(ValueError, match="duplicate"):
        replace(_candidate(), supported_surfaces=("insight", "insight"))
    with pytest.raises(ValueError, match="non-empty"):
        replace(_candidate(), supported_surfaces=())
    with pytest.raises(ValueError, match="bool"):
        replace(_criteria(), require_human_approval=cast(Any, "yes"))


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
        "alias.open('wb').write(b'payload')\n"
        "with Path('context.txt').open('w') as handle:\n"
        "    handle.write('payload')\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="Path.write"):
        assert_no_forbidden_semantic_cache_calls(source)
