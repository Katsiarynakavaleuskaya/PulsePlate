"""Tests for bounded knowledge contracts and store seam."""

from __future__ import annotations

from datetime import datetime, timezone

from core.knowledge.contracts import (
    KnowledgeEvidenceRef,
    KnowledgeFactCandidate,
    KnowledgeRecord,
)
from core.knowledge.store import InMemoryKnowledgeStore


def test_knowledge_contracts_preserve_provenance_and_scope() -> None:
    """Contracts must keep provenance, access scope, and observed timestamp intact."""

    observed_at = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
    evidence = KnowledgeEvidenceRef(
        chunk_id="chunk-1",
        file="docs/test.md",
        score=0.91,
        hop=2,
    )
    candidate = KnowledgeFactCandidate(
        fact_key="fact-1",
        subject="subject:42",
        predicate="validated_rag_evidence:docs/test.md:chunk-1",
        value="chunk=chunk-1;source=docs/test.md;digest=abc123;hop=2",
        observed_at=observed_at,
        confidence=0.91,
        access_scope="subject:42",
        rail="product_ai_runtime",
        provenance=(evidence,),
    )
    record = KnowledgeRecord(
        fact_key=candidate.fact_key,
        subject=candidate.subject,
        predicate=candidate.predicate,
        value=candidate.value,
        status="active",
        confidence=candidate.confidence,
        access_scope=candidate.access_scope,
        rail=candidate.rail,
        provenance=candidate.provenance,
        observed_at=observed_at,
    )

    assert candidate.provenance[0].chunk_id == "chunk-1"
    assert candidate.access_scope == "subject:42"
    assert candidate.observed_at == observed_at
    assert record.provenance == candidate.provenance
    assert record.observed_at == observed_at


def test_in_memory_store_replays_identical_evidence_idempotently() -> None:
    """In-memory store must not duplicate or self-supersede identical evidence."""

    observed_at = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
    store = InMemoryKnowledgeStore()
    first = KnowledgeFactCandidate(
        fact_key="fact-1",
        subject="subject:42",
        predicate="validated_rag_evidence:docs/test.md:chunk-1",
        value="v1",
        observed_at=observed_at,
        confidence=0.7,
        access_scope="subject:42",
        rail="product_ai_runtime",
        provenance=(KnowledgeEvidenceRef("chunk-1", "docs/test.md", 0.7, 1),),
    )

    first_records = store.promote([first])
    second_records = store.promote([first])
    active = store.read(
        subject="subject:42",
        predicate="validated_rag_evidence:docs/test.md:chunk-1",
        access_scope="subject:42",
        rail="product_ai_runtime",
    )

    assert len(first_records) == 1
    assert second_records == []
    assert len(active) == 1
    assert active[0].fact_key == "fact-1"
    assert active[0].value == "v1"


def test_in_memory_store_only_supersedes_when_explicitly_declared() -> None:
    """Distinct evidence stays active unless the candidate explicitly supersedes it."""

    observed_at = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
    store = InMemoryKnowledgeStore()
    first = KnowledgeFactCandidate(
        fact_key="fact-1",
        subject="subject:42",
        predicate="validated_rag_evidence:docs/test.md:chunk-1",
        value="v1",
        observed_at=observed_at,
        confidence=0.7,
        access_scope="subject:42",
        rail="product_ai_runtime",
        provenance=(KnowledgeEvidenceRef("chunk-1", "docs/test.md", 0.7, 1),),
    )
    superseding = KnowledgeFactCandidate(
        fact_key="fact-2",
        subject="subject:42",
        predicate="validated_rag_evidence:docs/test.md:chunk-1",
        value="v2",
        observed_at=observed_at.replace(minute=1),
        confidence=0.9,
        access_scope="subject:42",
        rail="product_ai_runtime",
        provenance=(KnowledgeEvidenceRef("chunk-1", "docs/test.md", 0.9, 1),),
        supersedes=("fact-1",),
    )

    store.promote([first])
    promoted = store.promote([superseding])
    active = store.read(
        subject="subject:42",
        predicate="validated_rag_evidence:docs/test.md:chunk-1",
        access_scope="subject:42",
        rail="product_ai_runtime",
    )

    assert len(promoted) == 1
    assert len(active) == 1
    assert active[0].fact_key == "fact-2"
    assert len(store.all_records()) == 2
    superseded = [record for record in store.all_records() if record.status == "superseded"]
    assert len(superseded) == 1
    assert superseded[0].fact_key == "fact-1"
    assert superseded[0].superseded_by == "fact-2"


def test_in_memory_store_preserves_unrelated_records_when_superseding() -> None:
    """Superseding one fact must not drop unrelated active records."""

    observed_at = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
    store = InMemoryKnowledgeStore()
    first = KnowledgeFactCandidate(
        fact_key="fact-1",
        subject="subject:42",
        predicate="validated_rag_evidence:docs/test.md:chunk-1",
        value="v1",
        observed_at=observed_at,
        confidence=0.7,
        access_scope="subject:42",
        rail="product_ai_runtime",
        provenance=(KnowledgeEvidenceRef("chunk-1", "docs/test.md", 0.7, 1),),
    )
    unrelated = KnowledgeFactCandidate(
        fact_key="fact-unrelated",
        subject="subject:99",
        predicate="validated_rag_evidence:docs/other.md:chunk-9",
        value="keep",
        observed_at=observed_at,
        confidence=0.8,
        access_scope="subject:99",
        rail="product_ai_runtime",
        provenance=(KnowledgeEvidenceRef("chunk-9", "docs/other.md", 0.8, 1),),
    )
    superseding = KnowledgeFactCandidate(
        fact_key="fact-2",
        subject="subject:42",
        predicate="validated_rag_evidence:docs/test.md:chunk-1",
        value="v2",
        observed_at=observed_at.replace(minute=1),
        confidence=0.9,
        access_scope="subject:42",
        rail="product_ai_runtime",
        provenance=(KnowledgeEvidenceRef("chunk-1", "docs/test.md", 0.9, 1),),
        supersedes=("fact-1",),
    )

    store.promote([first, unrelated])
    store.promote([superseding])

    records_by_key = {record.fact_key: record for record in store.all_records()}
    assert set(records_by_key) == {"fact-1", "fact-2", "fact-unrelated"}
    assert records_by_key["fact-unrelated"].status == "active"
    assert records_by_key["fact-unrelated"].value == "keep"


def test_in_memory_store_keeps_identical_scope_isolated_by_rail() -> None:
    """Same logical fact may coexist across rails without cross-reading leakage."""

    observed_at = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
    store = InMemoryKnowledgeStore()
    runtime_candidate = KnowledgeFactCandidate(
        fact_key="fact-runtime",
        subject="subject:42",
        predicate="validated_rag_evidence:docs/test.md:chunk-1",
        value="v1",
        observed_at=observed_at,
        confidence=0.7,
        access_scope="subject:42",
        rail="product_ai_runtime",
        provenance=(KnowledgeEvidenceRef("chunk-1", "docs/test.md", 0.7, 1),),
    )
    shadow_candidate = KnowledgeFactCandidate(
        fact_key="fact-shadow",
        subject="subject:42",
        predicate="validated_rag_evidence:docs/test.md:chunk-1",
        value="v1",
        observed_at=observed_at,
        confidence=0.7,
        access_scope="subject:42",
        rail="shadow_runtime",
        provenance=(KnowledgeEvidenceRef("chunk-1", "docs/test.md", 0.7, 1),),
    )

    store.promote([runtime_candidate, shadow_candidate])

    runtime_records = store.read(
        subject="subject:42",
        predicate="validated_rag_evidence:docs/test.md:chunk-1",
        access_scope="subject:42",
        rail="product_ai_runtime",
    )
    shadow_records = store.read(
        subject="subject:42",
        predicate="validated_rag_evidence:docs/test.md:chunk-1",
        access_scope="subject:42",
        rail="shadow_runtime",
    )

    assert [record.fact_key for record in runtime_records] == ["fact-runtime"]
    assert [record.fact_key for record in shadow_records] == ["fact-shadow"]
