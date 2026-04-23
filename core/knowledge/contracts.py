"""Canonical internal contracts for knowledge promotion.

RU: Канонические внутренние контракты для knowledge promotion.
EN: Canonical internal contracts for knowledge promotion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class KnowledgeEvidenceRef:
    """Reference to validated retrieval evidence used for promotion."""

    chunk_id: str
    file: str
    score: float
    hop: int


@dataclass(frozen=True)
class KnowledgeFactCandidate:
    """Internal fact candidate derived from validated RAG evidence only."""

    fact_key: str
    subject: str
    predicate: str
    value: str
    observed_at: datetime
    confidence: float
    access_scope: str
    rail: str
    provenance: tuple[KnowledgeEvidenceRef, ...]
    supersedes: tuple[str, ...] = ()


@dataclass(frozen=True)
class KnowledgeRecord:
    """Persistable internal record produced by the knowledge store seam."""

    fact_key: str
    subject: str
    predicate: str
    value: str
    status: str
    confidence: float
    access_scope: str
    rail: str
    provenance: tuple[KnowledgeEvidenceRef, ...]
    observed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    superseded_by: str | None = None
