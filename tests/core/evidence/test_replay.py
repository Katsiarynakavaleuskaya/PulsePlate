from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.evidence.assets import create_evidence_asset_ref
from core.evidence.events import EvalEventProducer, EvidenceEvalEvent, create_eval_event
from core.evidence.fingerprints import fingerprint_payload
from typing import cast

from core.evidence.promotion_ledger import (
    PromotionDecision,
    PromotionLedgerEntry,
    create_promotion_ledger_entry,
)
from core.evidence.replay import dry_run_replay

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REPLAY_MODULE = _REPO_ROOT / "core" / "evidence" / "replay.py"
_FIXED_TIMESTAMP = "2026-05-06T12:00:00+00:00"


def _source_event(*, run_id: str = "1") -> EvidenceEvalEvent:
    asset_ref = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="runtime",
        policy_version="policy-v1",
        payload={"run": f"rag-gate-{run_id}"},
    )
    return create_eval_event(
        event_type="rag_gate_run",
        rail="eval",
        source_artifact=f"artifacts/rag_eval/run-{run_id}/traces.jsonl",
        asset_refs=(asset_ref,),
        upstream_ids=(f"dataset-{run_id}",),
        fingerprint=fingerprint_payload({"artifact": "traces.jsonl", "run": run_id}),
        idempotency_key=f"idem:rag-gate-run-{run_id}",
        policy_version="policy-v1",
        producer_name="rag-release-gates",
        producer_version="v1",
        produced_at=_FIXED_TIMESTAMP,
        validation_status="valid",
        metadata={"decision": "PASS", "run": run_id},
    )


def _producer() -> EvalEventProducer:
    return EvalEventProducer(name="evidence-promotion-ledger", version="v1")


def _entry(
    *,
    run_id: str = "1",
    promotion_id: str | None = None,
    decision: str = "promote",
    idempotency_key: str | None = None,
    supersedes: tuple[str, ...] = (),
) -> PromotionLedgerEntry:
    return create_promotion_ledger_entry(
        source_event=_source_event(run_id=run_id),
        promotion_id=promotion_id or f"promotion-rag-gate-{run_id}",
        decision=cast(PromotionDecision, decision),
        idempotency_key=idempotency_key or f"idem:promotion-rag-gate-{run_id}",
        producer=_producer(),
        produced_at=_FIXED_TIMESTAMP,
        supersedes=supersedes,
        reason_codes=("policy-pass",),
        metadata={"confidence": 1.0},
    )


def test_dry_run_replay_is_deterministic_regardless_of_input_order() -> None:
    first = _entry(run_id="1")
    second = _entry(run_id="2")

    forward = dry_run_replay(candidate_entries=(first, second))
    reverse = dry_run_replay(candidate_entries=(second, first))

    assert forward.to_json() == reverse.to_json()
    assert forward.diff.added == tuple(sorted((first.ledger_entry_id, second.ledger_entry_id)))


def test_duplicate_idempotency_key_is_reported_as_duplicate() -> None:
    entry = _entry()
    summary = dry_run_replay(candidate_entries=(entry, entry))

    assert summary.diff.added == (entry.ledger_entry_id,)
    assert summary.diff.duplicate == (entry.ledger_entry_id,)


def test_duplicate_supersede_is_reported_before_scope_validation() -> None:
    existing = _entry(run_id="1")
    superseding = _entry(
        run_id="2",
        promotion_id=existing.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-existing-duplicate",
        supersedes=(existing.ledger_entry_id,),
    )

    summary = dry_run_replay(
        existing_entries=(existing,),
        candidate_entries=(superseding, superseding),
    )

    assert summary.diff.superseded == (superseding.ledger_entry_id,)
    assert summary.diff.duplicate == (superseding.ledger_entry_id,)
    assert summary.diff.conflict == ()


def test_idempotency_collision_is_reported_as_conflict() -> None:
    first = _entry(run_id="1", idempotency_key="idem:collision")
    second = _entry(run_id="2", idempotency_key="idem:collision")
    summary = dry_run_replay(candidate_entries=(first, second))

    assert summary.diff.added == (first.ledger_entry_id,)
    assert summary.diff.conflict == (second.ledger_entry_id,)


def test_existing_idempotency_collision_fails_closed() -> None:
    first = _entry(run_id="1", idempotency_key="idem:existing-collision")
    second = _entry(run_id="2", idempotency_key="idem:existing-collision")

    with pytest.raises(ValueError, match="duplicate idempotency_key"):
        dry_run_replay(existing_entries=(first, second))


def test_existing_active_scope_collision_fails_closed() -> None:
    first = _entry(run_id="1", promotion_id="promotion-shared")
    second = _entry(
        run_id="2",
        promotion_id="promotion-shared",
        idempotency_key="idem:promotion-shared-second",
    )

    with pytest.raises(ValueError, match="conflicting active promotion_id"):
        dry_run_replay(existing_entries=(first, second))


def test_candidate_promote_against_existing_active_scope_is_conflict() -> None:
    existing = _entry(run_id="1", promotion_id="promotion-shared")
    candidate = _entry(
        run_id="2",
        promotion_id="promotion-shared",
        idempotency_key="idem:promotion-shared-candidate",
    )

    summary = dry_run_replay(
        existing_entries=(existing,),
        candidate_entries=(candidate,),
    )

    assert summary.diff.added == ()
    assert summary.diff.conflict == (candidate.ledger_entry_id,)


def test_same_promotion_scope_conflict_is_non_promoting() -> None:
    first = _entry(run_id="1", promotion_id="promotion-shared")
    second = _entry(
        run_id="2",
        promotion_id="promotion-shared",
        idempotency_key="idem:promotion-shared-second",
    )
    summary = dry_run_replay(candidate_entries=(second, first))

    assert len(summary.diff.added) == 1
    assert len(summary.diff.conflict) == 1
    assert set(summary.diff.added + summary.diff.conflict) == {
        first.ledger_entry_id,
        second.ledger_entry_id,
    }


def test_candidate_orphan_supersede_is_reported_as_conflict() -> None:
    superseding = _entry(
        run_id="2",
        promotion_id="promotion-rag-gate-1",
        decision="supersede",
        idempotency_key="idem:orphan-supersede",
        supersedes=("promotion-ledger:missing",),
    )
    summary = dry_run_replay(candidate_entries=(superseding,))

    assert summary.diff.superseded == ()
    assert summary.diff.conflict == (superseding.ledger_entry_id,)


def test_existing_orphan_supersede_fails_closed() -> None:
    superseding = _entry(
        run_id="2",
        promotion_id="promotion-rag-gate-1",
        decision="supersede",
        idempotency_key="idem:existing-orphan-supersede",
        supersedes=("promotion-ledger:missing",),
    )

    with pytest.raises(ValueError, match="orphan supersede"):
        dry_run_replay(existing_entries=(superseding,))


def test_existing_supersede_with_empty_parent_ids_is_orphan() -> None:
    active = _entry(run_id="1")
    superseding = _entry(
        run_id="2",
        promotion_id=active.promotion_id,
        decision="supersede",
        idempotency_key="idem:existing-supersede-without-parent",
        supersedes=(active.ledger_entry_id,),
    )
    object.__setattr__(superseding, "supersedes", ())

    with pytest.raises(ValueError, match="orphan supersede"):
        dry_run_replay(existing_entries=(active, superseding))


def test_supersede_reject_and_defer_buckets_are_deterministic() -> None:
    existing = _entry(run_id="1")
    superseding = _entry(
        run_id="2",
        promotion_id=existing.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-existing",
        supersedes=(existing.ledger_entry_id,),
    )
    rejected = _entry(
        run_id="3",
        decision="reject",
        idempotency_key="idem:reject-run-3",
    )
    deferred = _entry(
        run_id="4",
        decision="defer",
        idempotency_key="idem:defer-run-4",
    )

    summary = dry_run_replay(
        existing_entries=(existing,),
        candidate_entries=(deferred, superseding, rejected),
    )

    assert summary.diff.superseded == (superseding.ledger_entry_id,)
    assert summary.diff.rejected == (rejected.ledger_entry_id,)
    assert summary.diff.deferred == (deferred.ledger_entry_id,)
    assert summary.diff.added == ()
    assert summary.diff.conflict == ()
    assert rejected.ledger_entry_id in summary.applied_entry_ids
    assert deferred.ledger_entry_id in summary.applied_entry_ids


def test_existing_supersession_chain_resolves_current_active_entry() -> None:
    first = _entry(run_id="1")
    second = _entry(
        run_id="2",
        promotion_id=first.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-first",
        supersedes=(first.ledger_entry_id,),
    )
    third = _entry(
        run_id="3",
        promotion_id=first.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-second",
        supersedes=(second.ledger_entry_id,),
    )

    summary = dry_run_replay(
        existing_entries=(second, first),
        candidate_entries=(third,),
    )

    assert summary.diff.superseded == (third.ledger_entry_id,)
    assert summary.diff.conflict == ()


def test_existing_supersession_chain_replays_existing_entries_as_a_set() -> None:
    first = _entry(run_id="1")
    second = _entry(
        run_id="2",
        promotion_id=first.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-first",
        supersedes=(first.ledger_entry_id,),
    )
    third = _entry(
        run_id="3",
        promotion_id=first.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-second",
        supersedes=(second.ledger_entry_id,),
    )

    summary = dry_run_replay(existing_entries=(first, third, second))

    assert summary.applied_entry_ids == tuple(
        sorted(
            (
                first.ledger_entry_id,
                second.ledger_entry_id,
                third.ledger_entry_id,
            )
        )
    )
    assert summary.diff.conflict == ()


def test_existing_supersession_chain_with_multiple_leaves_is_orphaned() -> None:
    active = _entry(run_id="1")
    first = _entry(
        run_id="2",
        promotion_id=active.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-first",
        supersedes=(active.ledger_entry_id,),
    )
    second = _entry(
        run_id="3",
        promotion_id=active.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-second",
        supersedes=(active.ledger_entry_id,),
    )

    with pytest.raises(ValueError, match="conflicting active"):
        dry_run_replay(existing_entries=(active, first, second))


def test_existing_supersession_chain_with_disconnected_supersession_cycle_is_orphaned() -> None:
    active = _entry(run_id="1")
    first = _entry(
        run_id="2",
        promotion_id=active.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-first",
        supersedes=(active.ledger_entry_id,),
    )
    cycle_first = _entry(
        run_id="3",
        promotion_id=active.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-cycle-first",
        supersedes=("promotion-ledger:placeholder",),
    )
    sibling = _entry(
        run_id="4",
        promotion_id=active.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-cycle-second",
        supersedes=(cycle_first.ledger_entry_id,),
    )
    object.__setattr__(
        cycle_first,
        "supersedes",
        (sibling.ledger_entry_id,),
    )

    with pytest.raises(ValueError, match="orphan supersede"):
        dry_run_replay(existing_entries=(active, first, cycle_first, sibling))


def test_existing_supersession_chain_with_cumulative_supersede_uses_linear_traversal() -> None:
    active = _entry(run_id="1")
    first = _entry(
        run_id="2",
        promotion_id=active.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-first",
        supersedes=(active.ledger_entry_id,),
    )
    second = _entry(
        run_id="3",
        promotion_id=active.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-second",
        supersedes=(active.ledger_entry_id,),
    )
    third = _entry(
        run_id="4",
        promotion_id=active.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-third",
        supersedes=(first.ledger_entry_id, second.ledger_entry_id),
    )

    summary = dry_run_replay(existing_entries=(active, first, second, third))

    assert summary.diff.superseded == ()
    assert summary.diff.conflict == ()
    assert summary.applied_entry_ids == tuple(
        sorted(
            (
                active.ledger_entry_id,
                first.ledger_entry_id,
                second.ledger_entry_id,
                third.ledger_entry_id,
            )
        )
    )


def test_existing_supersession_chain_supports_cumulative_supersedes() -> None:
    first = _entry(run_id="1")
    second = _entry(
        run_id="2",
        promotion_id=first.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-first",
        supersedes=(first.ledger_entry_id,),
    )
    cumulative = _entry(
        run_id="3",
        promotion_id=first.promotion_id,
        decision="supersede",
        idempotency_key="idem:supersede-cumulative",
        supersedes=(first.ledger_entry_id, second.ledger_entry_id),
    )

    summary = dry_run_replay(
        existing_entries=(first, second),
        candidate_entries=(cumulative,),
    )

    assert summary.diff.superseded == (cumulative.ledger_entry_id,)
    assert summary.diff.conflict == ()


def test_replay_does_not_mutate_caller_owned_lists() -> None:
    existing = [_entry(run_id="1")]
    candidates = [_entry(run_id="2")]

    summary = dry_run_replay(existing_entries=existing, candidate_entries=candidates)
    existing.append(_entry(run_id="3"))
    candidates.clear()

    assert summary.existing_entry_ids == (existing[0].ledger_entry_id,)
    assert summary.diff.added == (summary.candidate_entry_ids[0],)


def test_replay_fails_closed_on_invalid_entries() -> None:
    with pytest.raises(ValueError, match="PromotionLedgerEntry"):
        dry_run_replay(candidate_entries=cast(tuple[PromotionLedgerEntry, ...], (object(),)))


def test_replay_module_does_not_import_runtime_surfaces() -> None:
    forbidden_prefixes = (
        "app",
        "fastapi",
        "legacy_app",
        "providers",
        "redis",
        "scripts.evals",
        "evals",
        "sqlalchemy",
        "mcp_pulseplate_server",
    )
    forbidden_fragments = (
        "cache",
        "graphrag",
        "semantic_cache",
        "support_plane",
        "wiki",
    )
    tree = ast.parse(_REPLAY_MODULE.read_text(encoding="utf-8"))

    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)

    for module_name in imported_modules:
        assert not any(
            module_name == prefix or module_name.startswith(f"{prefix}.")
            for prefix in forbidden_prefixes
        )
        assert not any(fragment in module_name.lower() for fragment in forbidden_fragments)
