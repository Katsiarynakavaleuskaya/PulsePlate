"""Deterministic tests for the verification registry."""

from __future__ import annotations

from core.insight.analytical import FalsificationReport, VerificationReport
from core.knowledge.policy import KnowledgePolicy
from core.verification.registry import (
    build_rag_verification_bundle,
    build_runtime_verification_bundle,
)


def _knowledge_policy() -> KnowledgePolicy:
    return KnowledgePolicy(
        enabled=True,
        allow_reads=True,
        allow_promotion=True,
        min_confidence=0.7,
        require_rag_factual_route=True,
        deny_degraded_reasons=("retrieval_empty", "all_chunks_filtered"),
        subject_scope_required=True,
        rail="product_ai_runtime",
    )


def test_rag_verification_bundle_materializes_recursive_artifacts_deterministically() -> None:
    """Recursive verification signals must become deterministic registry artifacts."""

    first = build_rag_verification_bundle(
        knowledge_policy=_knowledge_policy(),
        confidence=0.92,
        degraded_reason=None,
        rag_actually_used=True,
        philo_validation_enabled=True,
        recursive_executed=True,
        verification_calls=2,
        evidence_refs=("docs/keep.md:keep",),
    )
    second = build_rag_verification_bundle(
        knowledge_policy=_knowledge_policy(),
        confidence=0.92,
        degraded_reason=None,
        rag_actually_used=True,
        philo_validation_enabled=True,
        recursive_executed=True,
        verification_calls=2,
        evidence_refs=("docs/keep.md:keep",),
    )

    assert [artifact.verifier_id for artifact in first.artifacts] == [
        "policy_verifier",
        "freshness_verifier",
        "evidence_verifier",
        "execution_verifier",
    ]
    assert [artifact.artifact_id for artifact in first.artifacts] == [
        artifact.artifact_id for artifact in second.artifacts
    ]
    assert first.reason_codes == (
        "policy_checks_pass",
        "freshness_checks_pass",
        "recursive_path_not_canonical",
        "recursive_verification_calls_observed",
    )
    assert first.admission_allowed is False


def test_runtime_verification_bundle_merges_reports_into_full_pass_bundle() -> None:
    """Runtime verification and falsification must merge into one admissible bundle."""

    rag_bundle = build_rag_verification_bundle(
        knowledge_policy=_knowledge_policy(),
        confidence=0.92,
        degraded_reason=None,
        rag_actually_used=True,
        philo_validation_enabled=True,
        recursive_executed=False,
        verification_calls=0,
        evidence_refs=("docs/keep.md:keep",),
    )

    merged = build_runtime_verification_bundle(
        rag_bundle=rag_bundle,
        verification_report=VerificationReport(
            verification_rate=1.0,
            verified_claims=["Protein supports recovery."],
            unverified_claims=[],
            classifications={"analytical": 0, "synthetic": 1, "metaphysical": 0, "unknown": 0},
        ),
        falsification_report=FalsificationReport(
            falsifiability_rate=1.0,
            falsifiable_claims=["Protein supports recovery."],
            unfalsifiable_claims=[],
        ),
        contradiction_count=0,
        verification_first_path=True,
    )

    assert merged is not None
    assert merged.admission_allowed is True
    assert merged.reason_codes == (
        "policy_checks_pass",
        "freshness_checks_pass",
        "validated_evidence_pass",
        "verification_checks_pass",
        "falsification_checks_pass",
    )


def test_runtime_verification_bundle_denies_admission_when_reports_fail() -> None:
    """Knowledge-write admission must fail when runtime verification is incomplete."""

    rag_bundle = build_rag_verification_bundle(
        knowledge_policy=_knowledge_policy(),
        confidence=0.92,
        degraded_reason=None,
        rag_actually_used=True,
        philo_validation_enabled=True,
        recursive_executed=False,
        verification_calls=0,
        evidence_refs=("docs/keep.md:keep",),
    )

    merged = build_runtime_verification_bundle(
        rag_bundle=rag_bundle,
        verification_report=VerificationReport(
            verification_rate=0.8,
            verified_claims=["Protein supports recovery."],
            unverified_claims=["Everyone should eat the same amount."],
            classifications={"analytical": 0, "synthetic": 2, "metaphysical": 0, "unknown": 0},
        ),
        falsification_report=FalsificationReport(
            falsifiability_rate=1.0,
            falsifiable_claims=["Protein supports recovery."],
            unfalsifiable_claims=[],
        ),
        contradiction_count=0,
        verification_first_path=True,
    )

    assert merged is not None
    assert merged.admission_allowed is False
    assert "verification_below_threshold" in merged.reason_codes
