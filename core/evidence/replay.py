"""Dry-run replay helpers for Evidence Graph promotion ledger entries."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

from core.evidence.fingerprints import JsonValue
from core.evidence.promotion_ledger import PromotionLedgerEntry


@dataclass(frozen=True)
class PromotionDiff:
    """Deterministic replay diff buckets."""

    added: tuple[str, ...] = ()
    duplicate: tuple[str, ...] = ()
    superseded: tuple[str, ...] = ()
    rejected: tuple[str, ...] = ()
    deferred: tuple[str, ...] = ()
    conflict: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-compatible deterministic diff payload."""

        return {
            "added": list(self.added),
            "conflict": list(self.conflict),
            "deferred": list(self.deferred),
            "duplicate": list(self.duplicate),
            "rejected": list(self.rejected),
            "superseded": list(self.superseded),
        }


@dataclass(frozen=True)
class PromotionReplaySummary:
    """Dry-run replay result without mutating or writing ledger state."""

    candidate_entry_ids: tuple[str, ...]
    existing_entry_ids: tuple[str, ...]
    applied_entry_ids: tuple[str, ...]
    diff: PromotionDiff

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-compatible deterministic replay payload."""

        return {
            "applied_entry_ids": list(self.applied_entry_ids),
            "candidate_entry_ids": list(self.candidate_entry_ids),
            "diff": self.diff.to_dict(),
            "existing_entry_ids": list(self.existing_entry_ids),
        }

    def to_json(self) -> str:
        """Serialize replay summary with stable key ordering."""

        return json.dumps(
            self.to_dict(),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


def dry_run_replay(
    *,
    existing_entries: Iterable[PromotionLedgerEntry] = (),
    candidate_entries: Iterable[PromotionLedgerEntry] = (),
) -> PromotionReplaySummary:
    """Replay candidate ledger entries deterministically without side effects."""

    existing = _sorted_entries(tuple(existing_entries))
    candidates = _sorted_entries(tuple(candidate_entries))

    existing_ids = tuple(entry.ledger_entry_id for entry in existing)
    candidate_ids = tuple(entry.ledger_entry_id for entry in candidates)
    seen_idempotency, active_by_scope = _seed_existing_replay_state(existing)
    candidate_scope_owner: dict[str, PromotionLedgerEntry] = {}

    added: list[str] = []
    duplicate: list[str] = []
    superseded: list[str] = []
    rejected: list[str] = []
    deferred: list[str] = []
    conflict: list[str] = []
    applied = list(existing_ids)

    for entry in candidates:
        seen_entry = seen_idempotency.get(entry.idempotency_key)
        if seen_entry is not None:
            if seen_entry.ledger_entry_id == entry.ledger_entry_id:
                duplicate.append(entry.ledger_entry_id)
            else:
                conflict.append(entry.ledger_entry_id)
            continue

        candidate_owner = candidate_scope_owner.get(entry.promotion_id)
        if candidate_owner is not None and candidate_owner.ledger_entry_id != entry.ledger_entry_id:
            conflict.append(entry.ledger_entry_id)
            continue

        active_entry = active_by_scope.get(entry.promotion_id)
        if entry.decision == "supersede" and (
            active_entry is None or active_entry.ledger_entry_id not in entry.supersedes
        ):
            conflict.append(entry.ledger_entry_id)
            continue
        if entry.decision == "promote" and active_entry is not None:
            conflict.append(entry.ledger_entry_id)
            continue

        seen_idempotency[entry.idempotency_key] = entry
        candidate_scope_owner[entry.promotion_id] = entry

        if entry.decision == "promote":
            added.append(entry.ledger_entry_id)
            active_by_scope[entry.promotion_id] = entry
            applied.append(entry.ledger_entry_id)
        elif entry.decision == "supersede":
            superseded.append(entry.ledger_entry_id)
            active_by_scope[entry.promotion_id] = entry
            applied.append(entry.ledger_entry_id)
        elif entry.decision == "reject":
            rejected.append(entry.ledger_entry_id)
            applied.append(entry.ledger_entry_id)
        elif entry.decision == "defer":
            deferred.append(entry.ledger_entry_id)
            applied.append(entry.ledger_entry_id)

    return PromotionReplaySummary(
        candidate_entry_ids=candidate_ids,
        existing_entry_ids=existing_ids,
        applied_entry_ids=tuple(sorted(applied)),
        diff=PromotionDiff(
            added=tuple(sorted(added)),
            duplicate=tuple(sorted(duplicate)),
            superseded=tuple(sorted(superseded)),
            rejected=tuple(sorted(rejected)),
            deferred=tuple(sorted(deferred)),
            conflict=tuple(sorted(conflict)),
        ),
    )


def _sorted_entries(
    entries: tuple[PromotionLedgerEntry, ...],
) -> tuple[PromotionLedgerEntry, ...]:
    """Validate and sort entries deterministically."""

    for entry in entries:
        if not isinstance(entry, PromotionLedgerEntry):
            raise ValueError("replay entries must be PromotionLedgerEntry instances")
    return tuple(sorted(entries, key=_entry_sort_key))


def _seed_existing_replay_state(
    existing: tuple[PromotionLedgerEntry, ...],
) -> tuple[dict[str, PromotionLedgerEntry], dict[str, PromotionLedgerEntry]]:
    """Build fail-closed replay indexes from existing ledger entries."""

    seen_idempotency: dict[str, PromotionLedgerEntry] = {}
    promoting_by_scope: dict[str, list[PromotionLedgerEntry]] = {}
    for entry in existing:
        previous = seen_idempotency.get(entry.idempotency_key)
        if previous is not None:
            raise ValueError(
                f"existing ledger has duplicate idempotency_key: {entry.idempotency_key}"
            )
        seen_idempotency[entry.idempotency_key] = entry

        if entry.decision in {"promote", "supersede"}:
            promoting_by_scope.setdefault(entry.promotion_id, []).append(entry)

    active_by_scope = _resolve_existing_active_entries(promoting_by_scope)
    return seen_idempotency, active_by_scope


def _resolve_existing_active_entries(
    promoting_by_scope: dict[str, list[PromotionLedgerEntry]],
) -> dict[str, PromotionLedgerEntry]:
    """Resolve active existing promotion entries in supersession order."""

    active_by_scope: dict[str, PromotionLedgerEntry] = {}
    for promotion_id in sorted(promoting_by_scope):
        active_by_scope[promotion_id] = _resolve_existing_scope_active(
            promotion_id,
            promoting_by_scope[promotion_id],
        )
    return active_by_scope


def _resolve_existing_scope_active(
    promotion_id: str,
    entries: list[PromotionLedgerEntry],
) -> PromotionLedgerEntry:
    """Resolve one existing promotion scope without trusting hash order."""

    promoted = tuple(entry for entry in entries if entry.decision == "promote")
    if not promoted:
        orphan = min(entries, key=_entry_sort_key)
        raise ValueError(f"existing ledger has orphan supersede entry: {orphan.ledger_entry_id}")
    if len(promoted) > 1:
        raise ValueError(f"existing ledger has conflicting active promotion_id: {promotion_id}")

    active_entry = promoted[0]
    supersedes = tuple(entry for entry in entries if entry.decision == "supersede")
    if not supersedes:
        return active_entry

    child_ids: set[str] = set()
    entry_by_id: dict[str, PromotionLedgerEntry] = {
        entry.ledger_entry_id: entry for entry in entries
    }
    child_by_parent: dict[str, list[PromotionLedgerEntry]] = {}
    for entry in supersedes:
        parent_ids = entry.supersedes
        if not parent_ids:
            orphan = entry
            raise ValueError(
                f"existing ledger has orphan supersede entry: {orphan.ledger_entry_id}"
            )

        for parent_id in parent_ids:
            if parent_id not in entry_by_id:
                orphan = entry
                raise ValueError(
                    f"existing ledger has orphan supersede entry: {orphan.ledger_entry_id}"
                )
            child_by_parent.setdefault(parent_id, []).append(entry)
            child_ids.add(parent_id)

    active_ids: set[str] = set()
    to_visit = [active_entry.ledger_entry_id]
    while to_visit:
        current_id = to_visit.pop()
        if current_id in active_ids:
            continue
        active_ids.add(current_id)
        children = child_by_parent.get(current_id)
        if not children:
            continue
        for child in sorted(children, key=_entry_sort_key):
            to_visit.append(child.ledger_entry_id)

    if len(active_ids) != len(entry_by_id):
        orphans = tuple(entry for entry in entries if entry.ledger_entry_id not in active_ids)
        orphan = min(orphans, key=_entry_sort_key)
        raise ValueError(f"existing ledger has orphan supersede entry: {orphan.ledger_entry_id}")

    leaves = tuple(entry for entry in supersedes if entry.ledger_entry_id not in child_ids)
    if not leaves:
        orphan = min(supersedes, key=_entry_sort_key)
        raise ValueError(f"existing ledger has orphan supersede entry: {orphan.ledger_entry_id}")
    if len(leaves) > 1:
        raise ValueError(f"existing ledger has conflicting active promotion_id: {promotion_id}")

    return min(leaves, key=_entry_sort_key)


def _entry_sort_key(entry: PromotionLedgerEntry) -> tuple[str, str, str, str]:
    """Return stable ordering key for replay inputs."""

    return (
        entry.promotion_id,
        _decision_sort_rank(entry.decision),
        entry.ledger_entry_id,
        entry.source_event_id,
    )


def _decision_sort_rank(decision: str) -> str:
    """Return stable semantic order for ledger replay decisions."""

    ranks = {
        "promote": "0",
        "supersede": "1",
        "reject": "2",
        "defer": "3",
    }
    return ranks[decision]
