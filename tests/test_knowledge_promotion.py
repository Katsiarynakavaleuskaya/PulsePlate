"""Tests for knowledge promotion fail-closed behavior."""

from __future__ import annotations

from datetime import datetime, timezone

from core.knowledge.contracts import KnowledgeRecord
from core.knowledge.policy import KnowledgePolicy
from core.knowledge.promotion import (
    build_knowledge_promotion_candidates,
    candidate_should_supersede,
)
from core.rag.contracts import RAGChunk
from core.verification.contracts import VerificationArtifact, VerificationBundle


def _policy() -> KnowledgePolicy:
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


def _verification_bundle(*, admission_allowed: bool = True) -> VerificationBundle:
    status = "pass" if admission_allowed else "fail"
    return VerificationBundle(
        artifacts=(
            VerificationArtifact(
                artifact_id=f"verification-{status}",
                verifier_id="test_verifier",
                status=status,
                reason_codes=(
                    ("verification_checks_pass",) if admission_allowed else ("verification_failed",)
                ),
            ),
        ),
        overall_status=status,
        admission_allowed=admission_allowed,
        reason_codes=(
            ("verification_checks_pass",) if admission_allowed else ("verification_failed",)
        ),
    )


def test_build_knowledge_promotion_candidates_uses_validated_chunks_only() -> None:
    """Promotion must derive candidates from the surviving validated chunks only."""

    chunks = [
        RAGChunk(
            chunk_id="chunk-1",
            file="docs/one.md",
            content=" First validated chunk. ",
            score=0.88,
            hop=1,
        ),
        RAGChunk(
            chunk_id="chunk-2",
            file="docs/two.md",
            content="Second validated chunk.",
            score=0.84,
            hop=2,
        ),
    ]

    candidates = build_knowledge_promotion_candidates(
        chunks=chunks,
        confidence=0.82,
        degraded_reason=None,
        subject_id=42,
        knowledge_policy=_policy(),
        verification_bundle=_verification_bundle(),
    )

    assert [candidate.predicate for candidate in candidates] == [
        "validated_rag_evidence:docs/one.md:chunk-1",
        "validated_rag_evidence:docs/two.md:chunk-2",
    ]
    assert candidates[0].subject == "subject:42"
    assert candidates[0].access_scope == "subject:42"
    assert candidates[0].provenance[0].file == "docs/one.md"
    assert "First validated chunk." not in candidates[0].value


def test_build_knowledge_promotion_candidates_fails_closed_on_degraded_confidence_and_scope() -> (
    None
):
    """Promotion must deny degraded, low-confidence, and missing-scope paths."""

    chunks = [
        RAGChunk(
            chunk_id="chunk-1",
            file="docs/one.md",
            content="Validated chunk.",
            score=0.88,
            hop=1,
        )
    ]

    degraded = build_knowledge_promotion_candidates(
        chunks=chunks,
        confidence=0.82,
        degraded_reason="retrieval_empty",
        subject_id=42,
        knowledge_policy=_policy(),
        verification_bundle=_verification_bundle(),
    )
    low_confidence = build_knowledge_promotion_candidates(
        chunks=chunks,
        confidence=0.69,
        degraded_reason=None,
        subject_id=42,
        knowledge_policy=_policy(),
        verification_bundle=_verification_bundle(),
    )
    missing_scope = build_knowledge_promotion_candidates(
        chunks=chunks,
        confidence=0.82,
        degraded_reason=None,
        subject_id=None,
        knowledge_policy=_policy(),
        verification_bundle=_verification_bundle(),
    )
    disabled_policy = build_knowledge_promotion_candidates(
        chunks=chunks,
        confidence=0.82,
        degraded_reason=None,
        subject_id=42,
        knowledge_policy=KnowledgePolicy(
            enabled=False,
            allow_reads=True,
            allow_promotion=True,
            min_confidence=0.7,
            require_rag_factual_route=True,
            deny_degraded_reasons=("retrieval_empty", "all_chunks_filtered"),
            subject_scope_required=True,
            rail="product_ai_runtime",
        ),
        verification_bundle=_verification_bundle(),
    )
    denied_policy = build_knowledge_promotion_candidates(
        chunks=chunks,
        confidence=0.82,
        degraded_reason=None,
        subject_id=42,
        knowledge_policy=KnowledgePolicy(
            enabled=True,
            allow_reads=True,
            allow_promotion=False,
            min_confidence=0.7,
            require_rag_factual_route=True,
            deny_degraded_reasons=("retrieval_empty", "all_chunks_filtered"),
            subject_scope_required=True,
            rail="product_ai_runtime",
        ),
        verification_bundle=_verification_bundle(),
    )
    missing_bundle = build_knowledge_promotion_candidates(
        chunks=chunks,
        confidence=0.82,
        degraded_reason=None,
        subject_id=42,
        knowledge_policy=_policy(),
    )
    denied_bundle = build_knowledge_promotion_candidates(
        chunks=chunks,
        confidence=0.82,
        degraded_reason=None,
        subject_id=42,
        knowledge_policy=_policy(),
        verification_bundle=_verification_bundle(admission_allowed=False),
    )

    assert degraded == []
    assert low_confidence == []
    assert missing_scope == []
    assert disabled_policy == []
    assert denied_policy == []
    assert missing_bundle == []
    assert denied_bundle == []


def test_candidate_should_supersede_only_when_scope_matches_and_evidence_is_stronger() -> None:
    """Supersession must stay bounded to the logical fact scope and stronger evidence."""

    observed_at = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
    existing = KnowledgeRecord(
        fact_key="fact-1",
        subject="subject:42",
        predicate="validated_rag_evidence:docs/one.md:chunk-1",
        value="v1",
        status="active",
        confidence=0.75,
        access_scope="subject:42",
        rail="product_ai_runtime",
        provenance=(),
        observed_at=observed_at,
    )
    stronger = build_knowledge_promotion_candidates(
        chunks=[
            RAGChunk(
                chunk_id="chunk-1",
                file="docs/one.md",
                content="v2",
                score=0.91,
                hop=1,
            )
        ],
        confidence=0.91,
        degraded_reason=None,
        subject_id=42,
        knowledge_policy=_policy(),
        verification_bundle=_verification_bundle(),
    )[0]
    stronger = KnowledgeRecord(
        fact_key=stronger.fact_key,
        subject=stronger.subject,
        predicate=stronger.predicate,
        value=stronger.value,
        status="active",
        confidence=stronger.confidence,
        access_scope=stronger.access_scope,
        rail=stronger.rail,
        provenance=stronger.provenance,
        observed_at=stronger.observed_at,
    )
    explicit_superseding_candidate = build_knowledge_promotion_candidates(
        chunks=[
            RAGChunk(
                chunk_id="chunk-1",
                file="docs/one.md",
                content="v4",
                score=0.95,
                hop=1,
            )
        ],
        confidence=0.95,
        degraded_reason=None,
        subject_id=42,
        knowledge_policy=_policy(),
        verification_bundle=_verification_bundle(),
    )[0]
    explicit_superseding_candidate = explicit_superseding_candidate.__class__(
        fact_key=explicit_superseding_candidate.fact_key,
        subject=explicit_superseding_candidate.subject,
        predicate=explicit_superseding_candidate.predicate,
        value=explicit_superseding_candidate.value,
        observed_at=explicit_superseding_candidate.observed_at,
        confidence=explicit_superseding_candidate.confidence,
        access_scope=explicit_superseding_candidate.access_scope,
        rail=explicit_superseding_candidate.rail,
        provenance=explicit_superseding_candidate.provenance,
        supersedes=("fact-1",),
    )
    other_scope = build_knowledge_promotion_candidates(
        chunks=[
            RAGChunk(
                chunk_id="chunk-1",
                file="docs/one.md",
                content="v3",
                score=0.8,
                hop=1,
            )
        ],
        confidence=0.8,
        degraded_reason=None,
        subject_id=99,
        knowledge_policy=_policy(),
        verification_bundle=_verification_bundle(),
    )[0]

    assert (
        candidate_should_supersede(
            existing=existing,
            candidate=build_knowledge_promotion_candidates(
                chunks=[
                    RAGChunk(
                        chunk_id="chunk-1",
                        file="docs/one.md",
                        content="v2",
                        score=0.91,
                        hop=1,
                    )
                ],
                confidence=0.91,
                degraded_reason=None,
                subject_id=42,
                knowledge_policy=_policy(),
                verification_bundle=_verification_bundle(),
            )[0],
        )
        is False
    )
    assert (
        candidate_should_supersede(existing=existing, candidate=explicit_superseding_candidate)
        is True
    )
    assert candidate_should_supersede(existing=existing, candidate=other_scope) is False
