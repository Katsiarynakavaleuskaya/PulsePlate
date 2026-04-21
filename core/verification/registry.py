"""Verification registry helpers.

RU: Сборка first-class verification artifacts поверх существующих runtime checks.
EN: First-class verification artifact assembly on top of existing runtime checks.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from hashlib import sha256

from core.insight.analytical import FalsificationReport, VerificationReport
from core.knowledge.policy import KnowledgePolicy
from core.rag.contracts import RAGDegradedReason
from core.verification.contracts import VerificationArtifact, VerificationBundle, VerificationStatus
from core.verification.policy import KNOWLEDGE_WRITE_POLICY, VerificationPolicy

_PASS: VerificationStatus = "pass"
_WARN: VerificationStatus = "warn"
_FAIL: VerificationStatus = "fail"


def build_rag_verification_bundle(
    *,
    knowledge_policy: KnowledgePolicy | None,
    confidence: float | None,
    degraded_reason: str | RAGDegradedReason | None,
    rag_actually_used: bool,
    philo_validation_enabled: bool,
    recursive_executed: bool,
    verification_calls: int,
    evidence_refs: Sequence[str] = (),
    policy: VerificationPolicy = KNOWLEDGE_WRITE_POLICY,
) -> VerificationBundle:
    """Build a canonical pre-generation bundle for knowledge-write admission."""

    degraded_reason_value = _normalize_degraded_reason(degraded_reason)
    artifacts: list[VerificationArtifact] = [
        _policy_artifact(knowledge_policy=knowledge_policy, policy=policy),
        _freshness_artifact(
            knowledge_policy=knowledge_policy,
            confidence=confidence,
            degraded_reason=degraded_reason_value,
            policy=policy,
        ),
        _evidence_artifact(
            rag_actually_used=rag_actually_used,
            philo_validation_enabled=philo_validation_enabled,
            recursive_executed=recursive_executed,
            degraded_reason=degraded_reason_value,
            evidence_refs=evidence_refs,
        ),
    ]
    recursive_artifact = _recursive_execution_artifact(
        recursive_executed=recursive_executed,
        verification_calls=verification_calls,
        evidence_refs=evidence_refs,
    )
    if recursive_artifact is not None:
        artifacts.append(recursive_artifact)
    return build_bundle(artifacts=artifacts, policy=policy)


def build_runtime_verification_bundle(
    *,
    rag_bundle: VerificationBundle | None,
    verification_report: VerificationReport | None,
    falsification_report: FalsificationReport | None,
    contradiction_count: int,
    verification_first_path: bool,
    runtime_verification_enabled: bool = True,
    policy: VerificationPolicy = KNOWLEDGE_WRITE_POLICY,
) -> VerificationBundle | None:
    """Merge pre-generation and runtime verification into one admission bundle."""

    if rag_bundle is None and not verification_first_path:
        return None

    if not runtime_verification_enabled:
        return rag_bundle

    artifacts: list[VerificationArtifact] = []
    if rag_bundle is None:
        artifacts.append(
            _artifact(
                verifier_id="runtime_preconditions_verifier",
                status=_FAIL,
                reason_codes=("rag_bundle_missing",),
                failure_reason="rag_bundle_missing",
            )
        )
    else:
        artifacts.extend(rag_bundle.artifacts)

    if verification_first_path:
        artifacts.append(
            _philosophical_verification_artifact(
                verification_report=verification_report,
                policy=policy,
            )
        )
        artifacts.append(
            _philosophical_falsification_artifact(
                falsification_report=falsification_report,
                contradiction_count=contradiction_count,
                policy=policy,
            )
        )

    return build_bundle(artifacts=artifacts, policy=policy)


def build_bundle(
    *,
    artifacts: Sequence[VerificationArtifact],
    policy: VerificationPolicy = KNOWLEDGE_WRITE_POLICY,
) -> VerificationBundle:
    """Build a deterministic bundle and derive admission from artifact statuses."""

    if not artifacts:
        artifacts = (
            _artifact(
                verifier_id="verification_registry",
                status=_FAIL,
                reason_codes=("verification_artifacts_missing",),
                failure_reason="verification_artifacts_missing",
                scope=policy.scope,
            ),
        )

    normalized_artifacts = tuple(artifacts)
    statuses = [artifact.status for artifact in normalized_artifacts]
    overall_status = _overall_status(statuses)
    admission_allowed = overall_status == _PASS or (overall_status == _WARN and policy.allow_warn)
    reason_codes = _dedupe_reason_codes(
        reason_code for artifact in normalized_artifacts for reason_code in artifact.reason_codes
    )
    return VerificationBundle(
        artifacts=normalized_artifacts,
        overall_status=overall_status,
        admission_allowed=admission_allowed,
        reason_codes=reason_codes,
    )


def _policy_artifact(
    *,
    knowledge_policy: KnowledgePolicy | None,
    policy: VerificationPolicy,
) -> VerificationArtifact:
    if knowledge_policy is None:
        return _artifact(
            verifier_id="policy_verifier",
            status=_FAIL,
            reason_codes=("knowledge_policy_missing",),
            failure_reason="knowledge_policy_missing",
            scope=policy.scope,
        )
    if not knowledge_policy.enabled:
        return _artifact(
            verifier_id="policy_verifier",
            status=_FAIL,
            reason_codes=("knowledge_policy_disabled",),
            failure_reason="knowledge_policy_disabled",
            scope=policy.scope,
        )
    if not knowledge_policy.allow_promotion:
        return _artifact(
            verifier_id="policy_verifier",
            status=_FAIL,
            reason_codes=("knowledge_promotion_disabled",),
            failure_reason="knowledge_promotion_disabled",
            scope=policy.scope,
        )
    return _artifact(
        verifier_id="policy_verifier",
        status=_PASS,
        reason_codes=("policy_checks_pass",),
        scope=policy.scope,
    )


def _freshness_artifact(
    *,
    knowledge_policy: KnowledgePolicy | None,
    confidence: float | None,
    degraded_reason: str | None,
    policy: VerificationPolicy,
) -> VerificationArtifact:
    if degraded_reason is not None:
        return _artifact(
            verifier_id="freshness_verifier",
            status=_FAIL,
            reason_codes=(degraded_reason,),
            failure_reason=degraded_reason,
            scope=policy.scope,
        )
    if confidence is None:
        return _artifact(
            verifier_id="freshness_verifier",
            status=_FAIL,
            reason_codes=("confidence_missing",),
            failure_reason="confidence_missing",
            scope=policy.scope,
        )
    threshold = 0.0 if knowledge_policy is None else knowledge_policy.min_confidence
    if confidence < threshold:
        return _artifact(
            verifier_id="freshness_verifier",
            status=_FAIL,
            reason_codes=("confidence_below_threshold",),
            failure_reason="confidence_below_threshold",
            scope=policy.scope,
        )
    return _artifact(
        verifier_id="freshness_verifier",
        status=_PASS,
        reason_codes=("freshness_checks_pass",),
        scope=policy.scope,
    )


def _evidence_artifact(
    *,
    rag_actually_used: bool,
    philo_validation_enabled: bool,
    recursive_executed: bool,
    degraded_reason: str | None,
    evidence_refs: Sequence[str],
) -> VerificationArtifact:
    if not rag_actually_used:
        return _artifact(
            verifier_id="evidence_verifier",
            status=_FAIL,
            reason_codes=("rag_not_used",),
            failure_reason="rag_not_used",
            evidence_refs=evidence_refs,
        )
    if not philo_validation_enabled:
        return _artifact(
            verifier_id="evidence_verifier",
            status=_FAIL,
            reason_codes=("philosophy_validation_disabled",),
            failure_reason="philosophy_validation_disabled",
            evidence_refs=evidence_refs,
        )
    if recursive_executed:
        return _artifact(
            verifier_id="evidence_verifier",
            status=_FAIL,
            reason_codes=("recursive_path_not_canonical",),
            failure_reason="recursive_path_not_canonical",
            evidence_refs=evidence_refs,
        )
    if degraded_reason is not None:
        return _artifact(
            verifier_id="evidence_verifier",
            status=_FAIL,
            reason_codes=("rag_degraded", degraded_reason),
            failure_reason="rag_degraded",
            evidence_refs=evidence_refs,
        )
    return _artifact(
        verifier_id="evidence_verifier",
        status=_PASS,
        reason_codes=("validated_evidence_pass",),
        evidence_refs=evidence_refs,
    )


def _recursive_execution_artifact(
    *,
    recursive_executed: bool,
    verification_calls: int,
    evidence_refs: Sequence[str],
) -> VerificationArtifact | None:
    if not recursive_executed:
        return None
    if verification_calls > 0:
        return _artifact(
            verifier_id="execution_verifier",
            status=_PASS,
            reason_codes=("recursive_verification_calls_observed",),
            evidence_refs=evidence_refs,
        )
    return _artifact(
        verifier_id="execution_verifier",
        status=_WARN,
        reason_codes=("recursive_verification_calls_missing",),
        failure_reason="recursive_verification_calls_missing",
        evidence_refs=evidence_refs,
    )


def _philosophical_verification_artifact(
    *,
    verification_report: VerificationReport | None,
    policy: VerificationPolicy,
) -> VerificationArtifact:
    if verification_report is None:
        return _artifact(
            verifier_id="analytical_verifier",
            status=_FAIL,
            reason_codes=("verification_report_missing",),
            failure_reason="verification_report_missing",
            scope=policy.scope,
        )
    if verification_report.verification_rate < policy.required_rate:
        return _artifact(
            verifier_id="analytical_verifier",
            status=_FAIL,
            reason_codes=("verification_below_threshold",),
            failure_reason="verification_below_threshold",
            scope=policy.scope,
        )
    return _artifact(
        verifier_id="analytical_verifier",
        status=_PASS,
        reason_codes=("verification_checks_pass",),
        scope=policy.scope,
    )


def _philosophical_falsification_artifact(
    *,
    falsification_report: FalsificationReport | None,
    contradiction_count: int,
    policy: VerificationPolicy,
) -> VerificationArtifact:
    if falsification_report is None:
        return _artifact(
            verifier_id="falsification_verifier",
            status=_FAIL,
            reason_codes=("falsification_report_missing",),
            failure_reason="falsification_report_missing",
            scope=policy.scope,
        )
    if contradiction_count > 0:
        return _artifact(
            verifier_id="falsification_verifier",
            status=_FAIL,
            reason_codes=("contradictions_detected",),
            failure_reason="contradictions_detected",
            scope=policy.scope,
        )
    if falsification_report.falsifiability_rate < policy.required_rate:
        return _artifact(
            verifier_id="falsification_verifier",
            status=_FAIL,
            reason_codes=("falsification_below_threshold",),
            failure_reason="falsification_below_threshold",
            scope=policy.scope,
        )
    return _artifact(
        verifier_id="falsification_verifier",
        status=_PASS,
        reason_codes=("falsification_checks_pass",),
        scope=policy.scope,
    )


def _artifact(
    *,
    verifier_id: str,
    status: VerificationStatus,
    reason_codes: Sequence[str],
    scope: str = KNOWLEDGE_WRITE_POLICY.scope,
    evidence_refs: Sequence[str] = (),
    failure_reason: str | None = None,
) -> VerificationArtifact:
    normalized_reason_codes = tuple(reason_codes)
    normalized_evidence_refs = tuple(evidence_refs)
    artifact_id = _artifact_id(
        verifier_id=verifier_id,
        status=status,
        scope=scope,
        evidence_refs=normalized_evidence_refs,
        reason_codes=normalized_reason_codes,
        failure_reason=failure_reason,
    )
    return VerificationArtifact(
        artifact_id=artifact_id,
        verifier_id=verifier_id,
        status=status,
        scope=scope,
        evidence_refs=normalized_evidence_refs,
        reason_codes=normalized_reason_codes,
        failure_reason=failure_reason,
    )


def _artifact_id(
    *,
    verifier_id: str,
    status: VerificationStatus,
    scope: str,
    evidence_refs: Sequence[str],
    reason_codes: Sequence[str],
    failure_reason: str | None,
) -> str:
    payload = "|".join(
        (
            verifier_id,
            status,
            scope,
            ",".join(evidence_refs),
            ",".join(reason_codes),
            failure_reason or "",
        )
    )
    return sha256(payload.encode("utf-8")).hexdigest()[:24]


def _normalize_degraded_reason(degraded_reason: str | RAGDegradedReason | None) -> str | None:
    if degraded_reason is None:
        return None
    if isinstance(degraded_reason, RAGDegradedReason):
        return degraded_reason.value
    return degraded_reason


def _overall_status(statuses: Sequence[VerificationStatus]) -> VerificationStatus:
    if any(status == _FAIL for status in statuses):
        return _FAIL
    if any(status == _WARN for status in statuses):
        return _WARN
    return _PASS


def _dedupe_reason_codes(reason_codes: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for reason_code in reason_codes:
        if reason_code in seen:
            continue
        seen.add(reason_code)
        ordered.append(reason_code)
    return tuple(ordered)
