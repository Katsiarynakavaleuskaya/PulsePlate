"""Store seam for bounded internal knowledge records.

RU: Store seam для bounded knowledge records без DB rollout.
EN: Store seam for bounded knowledge records without DB rollout.
"""

from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Iterable
from typing import Protocol

from core.knowledge.contracts import KnowledgeFactCandidate, KnowledgeRecord
from core.knowledge.promotion import (
    candidate_should_supersede,
    candidate_to_record,
    mark_record_superseded,
)

KnowledgePromoteResult = list[KnowledgeRecord] | Awaitable[list[KnowledgeRecord]]


class KnowledgeStore(Protocol):
    """Protocol for internal knowledge promotion and lookup."""

    def promote(self, candidates: list[KnowledgeFactCandidate]) -> KnowledgePromoteResult:
        """Promote candidates into active records."""

    def read(
        self,
        *,
        subject: str,
        predicate: str,
        access_scope: str,
        rail: str,
    ) -> list[KnowledgeRecord]:
        """Return matching active records for the logical fact scope."""


class NoOpKnowledgeStore:
    """Store implementation that refuses persistence and returns no records."""

    def promote(self, candidates: list[KnowledgeFactCandidate]) -> list[KnowledgeRecord]:
        del candidates
        return []

    def read(
        self,
        *,
        subject: str,
        predicate: str,
        access_scope: str,
        rail: str,
    ) -> list[KnowledgeRecord]:
        del subject, predicate, access_scope, rail
        return []


class InMemoryKnowledgeStore:
    """Deterministic in-memory store for bounded tests and local seams."""

    def __init__(self) -> None:
        self._records: list[KnowledgeRecord] = []

    def promote(self, candidates: list[KnowledgeFactCandidate]) -> list[KnowledgeRecord]:
        promoted: list[KnowledgeRecord] = []
        for candidate in candidates:
            active_records = self.read(
                subject=candidate.subject,
                predicate=candidate.predicate,
                access_scope=candidate.access_scope,
                rail=candidate.rail,
            )
            if _candidate_replays_existing(active_records=active_records, candidate=candidate):
                continue
            if not active_records:
                record = candidate_to_record(candidate)
                self._records.append(record)
                promoted.append(record)
                continue

            if not _candidate_beats_all_active(active_records=active_records, candidate=candidate):
                continue

            updated_records: list[KnowledgeRecord] = []
            for record in self._records:
                if record in active_records:
                    updated_records.append(
                        mark_record_superseded(record=record, superseded_by=candidate.fact_key)
                    )
                else:
                    updated_records.append(record)
            record = candidate_to_record(candidate)
            updated_records.append(record)
            self._records = updated_records
            promoted.append(record)
        return promoted

    def read(
        self,
        *,
        subject: str,
        predicate: str,
        access_scope: str,
        rail: str,
    ) -> list[KnowledgeRecord]:
        return [
            record
            for record in self._records
            if record.status == "active"
            and record.subject == subject
            and record.predicate == predicate
            and record.access_scope == access_scope
            and record.rail == rail
        ]


def _candidate_beats_all_active(
    *,
    active_records: Iterable[KnowledgeRecord],
    candidate: KnowledgeFactCandidate,
) -> bool:
    """Return whether the candidate supersedes every active record in scope."""

    return all(
        candidate_should_supersede(existing=record, candidate=candidate)
        for record in active_records
    )


def _candidate_replays_existing(
    *,
    active_records: Iterable[KnowledgeRecord],
    candidate: KnowledgeFactCandidate,
) -> bool:
    """Return whether candidate is an idempotent replay of active evidence."""

    return any(
        record.fact_key == candidate.fact_key
        and record.value == candidate.value
        and record.provenance == candidate.provenance
        for record in active_records
    )
