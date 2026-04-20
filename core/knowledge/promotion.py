"""Promotion helpers for validated RAG evidence.

RU: Хелперы promotion только из validated RAG evidence.
EN: Promotion helpers only from validated RAG evidence.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib

from core.knowledge.contracts import (
    KnowledgeEvidenceRef,
    KnowledgeFactCandidate,
    KnowledgeRecord,
)
from core.knowledge.policy import KnowledgePolicy
from core.rag.contracts import RAGChunk


def build_knowledge_promotion_candidates(
    *,
    chunks: list[RAGChunk],
    confidence: float | None,
    degraded_reason: str | None,
    subject_id: int | None,
    knowledge_policy: KnowledgePolicy,
) -> list[KnowledgeFactCandidate]:
    """Return deterministic candidates from validated chunks or fail closed."""

    if not knowledge_policy.enabled or not knowledge_policy.allow_promotion:
        return []
    if not chunks:
        return []
    if degraded_reason is not None and degraded_reason in knowledge_policy.deny_degraded_reasons:
        return []
    if confidence is None or confidence < knowledge_policy.min_confidence:
        return []
    if knowledge_policy.subject_scope_required and subject_id is None:
        return []

    access_scope = _resolve_access_scope(subject_id=subject_id)
    observed_at = datetime.now(timezone.utc)
    candidates: list[KnowledgeFactCandidate] = []
    for chunk in chunks:
        if not chunk.content.strip():
            continue
        source = chunk.file.strip() or "unknown_source"
        evidence_ref = KnowledgeEvidenceRef(
            chunk_id=chunk.chunk_id,
            file=source,
            score=chunk.score,
            hop=chunk.hop,
        )
        # RU: canonical candidate stores an evidence envelope, not raw chunk text.
        # EN: canonical candidate stores an evidence envelope, not raw chunk text.
        subject = access_scope
        predicate = f"validated_rag_evidence:{source}:{chunk.chunk_id}"
        value = _build_evidence_value(chunk=chunk, source=source)
        fact_key = _build_fact_key(
            subject=subject,
            predicate=predicate,
            value=value,
            access_scope=access_scope,
            rail=knowledge_policy.rail,
        )
        candidates.append(
            KnowledgeFactCandidate(
                fact_key=fact_key,
                subject=subject,
                predicate=predicate,
                value=value,
                observed_at=observed_at,
                confidence=confidence,
                access_scope=access_scope,
                rail=knowledge_policy.rail,
                provenance=(evidence_ref,),
            )
        )
    return candidates


def candidate_should_supersede(
    *,
    existing: KnowledgeRecord,
    candidate: KnowledgeFactCandidate,
) -> bool:
    """Return whether a candidate should supersede an existing active record."""

    if not _shares_supersession_scope(existing=existing, candidate=candidate):
        return False
    if existing.fact_key not in candidate.supersedes:
        return False
    if candidate.confidence > existing.confidence:
        return True
    if (
        candidate.confidence == existing.confidence
        and candidate.observed_at > existing.observed_at
        and bool(candidate.supersedes)
    ):
        return True
    return False


def candidate_to_record(candidate: KnowledgeFactCandidate) -> KnowledgeRecord:
    """Convert a candidate into an active knowledge record."""

    return KnowledgeRecord(
        fact_key=candidate.fact_key,
        subject=candidate.subject,
        predicate=candidate.predicate,
        value=candidate.value,
        status="active",
        confidence=candidate.confidence,
        access_scope=candidate.access_scope,
        rail=candidate.rail,
        provenance=candidate.provenance,
        observed_at=candidate.observed_at,
    )


def mark_record_superseded(
    *,
    record: KnowledgeRecord,
    superseded_by: str,
) -> KnowledgeRecord:
    """Return a superseded copy of an existing record."""

    return replace(record, status="superseded", superseded_by=superseded_by)


def _build_fact_key(
    *,
    subject: str,
    predicate: str,
    value: str,
    access_scope: str,
    rail: str,
) -> str:
    """Build a deterministic fact key from the canonical promotion scope."""

    digest = hashlib.sha256(
        f"{subject}|{predicate}|{value}|{access_scope}|{rail}".encode("utf-8")
    ).hexdigest()
    return digest[:24]


def _resolve_access_scope(*, subject_id: int | None) -> str:
    """Resolve deterministic access scope for the candidate."""

    return "subject:none" if subject_id is None else f"subject:{subject_id}"


def _shares_supersession_scope(
    *,
    existing: KnowledgeRecord,
    candidate: KnowledgeFactCandidate,
) -> bool:
    """Return whether record and candidate belong to the same logical fact scope."""

    return (
        existing.subject == candidate.subject
        and existing.predicate == candidate.predicate
        and existing.access_scope == candidate.access_scope
        and existing.rail == candidate.rail
    )


def _build_evidence_value(*, chunk: RAGChunk, source: str) -> str:
    """Build deterministic evidence envelope value without storing raw chunk text."""

    digest = hashlib.sha256(chunk.content.strip().encode("utf-8")).hexdigest()[:16]
    return f"chunk={chunk.chunk_id};source={source};digest={digest};hop={chunk.hop}"
