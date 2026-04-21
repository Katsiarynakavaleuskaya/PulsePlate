"""Deterministic tests for the verification registry."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from core.insight.analytical import FalsificationReport, VerificationReport
from core.knowledge.policy import KnowledgePolicy
from core.verification.contracts import VerificationArtifact
from core.verification.policy import VerificationPolicy
from core.verification.registry import (
    build_bundle,
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


def test_runtime_verification_bundle_fails_closed_when_rag_bundle_is_missing() -> None:
    """Verification-first runtime must emit deterministic failure artifacts without a RAG bundle."""

    merged = build_runtime_verification_bundle(
        rag_bundle=None,
        verification_report=None,
        falsification_report=None,
        contradiction_count=0,
        verification_first_path=True,
    )

    assert merged is not None
    assert merged.admission_allowed is False
    assert [artifact.verifier_id for artifact in merged.artifacts] == [
        "runtime_preconditions_verifier",
        "analytical_verifier",
        "falsification_verifier",
    ]
    assert merged.reason_codes == (
        "rag_bundle_missing",
        "verification_report_missing",
        "falsification_report_missing",
    )


def test_runtime_verification_bundle_returns_none_without_rag_bundle_outside_verification_path() -> (
    None
):
    """Non-verification-first runtime should not invent a bundle when none exists."""

    merged = build_runtime_verification_bundle(
        rag_bundle=None,
        verification_report=None,
        falsification_report=None,
        contradiction_count=0,
        verification_first_path=False,
    )

    assert merged is None


def test_runtime_verification_bundle_passthrough_when_runtime_verification_is_disabled() -> None:
    """Disabled runtime verification must preserve the already-built RAG bundle verbatim."""

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
        verification_report=None,
        falsification_report=None,
        contradiction_count=0,
        verification_first_path=True,
        runtime_verification_enabled=False,
    )

    assert merged == rag_bundle


def test_runtime_verification_bundle_reuses_rag_bundle_when_verification_first_path_is_off() -> (
    None
):
    """Runtime merge must preserve pre-generation artifacts when no philosophical pass runs."""

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
        verification_report=None,
        falsification_report=None,
        contradiction_count=0,
        verification_first_path=False,
    )

    assert merged is not None
    assert merged == rag_bundle


def test_rag_verification_bundle_uses_string_degraded_reason_and_promotion_policy() -> None:
    """String degraded reasons and promotion-disabled policy must stay canonical."""

    knowledge_policy = replace(_knowledge_policy(), allow_promotion=False)

    bundle = build_rag_verification_bundle(
        knowledge_policy=knowledge_policy,
        confidence=0.92,
        degraded_reason="manual_degraded_reason",
        rag_actually_used=True,
        philo_validation_enabled=True,
        recursive_executed=False,
        verification_calls=0,
        evidence_refs=("docs/keep.md:keep",),
    )

    assert bundle.admission_allowed is False
    assert bundle.reason_codes == (
        "knowledge_promotion_disabled",
        "manual_degraded_reason",
        "rag_degraded",
    )


def test_rag_verification_bundle_denies_disabled_policy() -> None:
    """Disabled knowledge policy must fail closed at the policy verifier layer."""

    bundle = build_rag_verification_bundle(
        knowledge_policy=replace(_knowledge_policy(), enabled=False),
        confidence=0.92,
        degraded_reason=None,
        rag_actually_used=True,
        philo_validation_enabled=True,
        recursive_executed=False,
        verification_calls=0,
        evidence_refs=("docs/keep.md:keep",),
    )

    assert bundle.admission_allowed is False
    assert "knowledge_policy_disabled" in bundle.reason_codes


def test_runtime_verification_bundle_denies_non_finite_verification_rate() -> None:
    """Non-finite verification rates must fail closed instead of slipping through."""

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
            verification_rate=float("nan"),
            verified_claims=[],
            unverified_claims=["Synthetic claim."],
            classifications={"analytical": 0, "synthetic": 1, "metaphysical": 0, "unknown": 0},
        ),
        falsification_report=FalsificationReport(
            falsifiability_rate=1.0,
            falsifiable_claims=["Synthetic claim."],
            unfalsifiable_claims=[],
        ),
        contradiction_count=0,
        verification_first_path=True,
    )

    assert merged is not None
    assert merged.admission_allowed is False
    assert "verification_below_threshold" in merged.reason_codes


def test_runtime_verification_bundle_denies_contradictions_before_rate_checks() -> None:
    """Contradictions must deny admission even when rates look sufficient."""

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
            verified_claims=["Claim A."],
            unverified_claims=[],
            classifications={"analytical": 0, "synthetic": 1, "metaphysical": 0, "unknown": 0},
        ),
        falsification_report=FalsificationReport(
            falsifiability_rate=1.0,
            falsifiable_claims=["Claim A."],
            unfalsifiable_claims=[],
        ),
        contradiction_count=1,
        verification_first_path=True,
    )

    assert merged is not None
    assert merged.admission_allowed is False
    assert "contradictions_detected" in merged.reason_codes


def test_runtime_verification_bundle_denies_out_of_range_falsification_rate() -> None:
    """Out-of-range falsification rates must fail closed deterministically."""

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
            verified_claims=["Claim A."],
            unverified_claims=[],
            classifications={"analytical": 0, "synthetic": 1, "metaphysical": 0, "unknown": 0},
        ),
        falsification_report=FalsificationReport(
            falsifiability_rate=1.1,
            falsifiable_claims=["Claim A."],
            unfalsifiable_claims=[],
        ),
        contradiction_count=0,
        verification_first_path=True,
    )

    assert merged is not None
    assert merged.admission_allowed is False
    assert "falsification_below_threshold" in merged.reason_codes


def test_build_bundle_falls_back_to_registry_failure_when_artifacts_are_missing() -> None:
    """An empty registry input must become a deterministic fail-closed bundle."""

    bundle = build_bundle(artifacts=())

    assert bundle.overall_status == "fail"
    assert bundle.admission_allowed is False
    assert bundle.reason_codes == ("verification_artifacts_missing",)


def test_build_bundle_supports_warn_only_status_when_policy_allows_it() -> None:
    """Warn-only bundles must preserve warn status and follow the supplied policy."""

    bundle = build_bundle(
        artifacts=(
            VerificationArtifact(
                artifact_id="warn-artifact",
                verifier_id="execution_verifier",
                status="warn",
                checked_at=datetime.now(timezone.utc),
                reason_codes=("recursive_verification_calls_missing",),
            ),
        ),
        policy=VerificationPolicy(scope="knowledge_write", allow_warn=True),
    )

    assert bundle.overall_status == "warn"
    assert bundle.admission_allowed is True
    assert bundle.reason_codes == ("recursive_verification_calls_missing",)
