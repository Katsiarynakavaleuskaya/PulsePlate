from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from core.evidence.assets import create_evidence_asset_ref
from core.evidence.events import (
    EvalEventProducer,
    EvidenceEvalEvent,
    ValidationStatus,
    create_eval_event,
)
from core.evidence.fingerprints import fingerprint_payload
from core.evidence.promotion_ledger import (
    PromotionDecision,
    create_promotion_ledger_entry,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROMOTION_MODULE = _REPO_ROOT / "core" / "evidence" / "promotion_ledger.py"
_FIXED_TIMESTAMP = "2026-05-06T12:00:00+00:00"


def _source_event(**overrides: object) -> EvidenceEvalEvent:
    asset_ref = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="runtime",
        policy_version="policy-v1",
        payload={"run": "rag-gate"},
    )
    params: dict[str, Any] = {
        "event_type": "rag_gate_run",
        "rail": "eval",
        "source_artifact": "artifacts/rag_eval/run-1/traces.jsonl",
        "asset_refs": (asset_ref,),
        "upstream_ids": ("dataset-1", " gate-report-1 ", "dataset-1"),
        "fingerprint": fingerprint_payload({"artifact": "traces.jsonl", "rows": 2}),
        "idempotency_key": "idem:rag-gate-run-1",
        "policy_version": "policy-v1",
        "producer_name": "rag-release-gates",
        "producer_version": "v1",
        "produced_at": _FIXED_TIMESTAMP,
        "validation_status": "valid",
        "metadata": {"decision": "PASS", "sample_size": 2},
    }
    params.update(overrides)
    return create_eval_event(**params)


def _producer() -> EvalEventProducer:
    return EvalEventProducer(name="evidence-promotion-ledger", version="v1")


def _entry(**overrides: object):
    params: dict[str, Any] = {
        "source_event": _source_event(),
        "promotion_id": "promotion-rag-gate-1",
        "decision": "promote",
        "idempotency_key": "idem:promotion-rag-gate-1",
        "producer": _producer(),
        "produced_at": _FIXED_TIMESTAMP,
        "reason_codes": (" accepted ", "policy-pass"),
        "metadata": {"confidence": 1.0, "labels": ["rag", "gate"]},
    }
    params.update(overrides)
    return create_promotion_ledger_entry(**params)


def test_creates_valid_promotion_ledger_entry_from_eval_event() -> None:
    source = _source_event()
    entry = _entry(source_event=source)

    assert entry.ledger_entry_id.startswith("promotion-ledger:")
    assert entry.source_event_id == source.event_id
    assert entry.source_event_fingerprint == source.fingerprint
    assert entry.source_event_type == "rag_gate_run"
    assert entry.policy_version == "policy-v1"
    assert source.event_id in entry.upstream_ids
    assert entry.reason_codes == ("accepted", "policy-pass")


def test_rejects_blank_source_event_id() -> None:
    source = replace(_source_event(), event_id=" ")

    with pytest.raises(ValueError, match="source_event_id"):
        _entry(source_event=source)


def test_rejects_blank_source_event_fingerprint() -> None:
    source = replace(_source_event(), fingerprint=" ")

    with pytest.raises(ValueError, match="fingerprint"):
        _entry(source_event=source)


def test_rejects_unsupported_decision() -> None:
    with pytest.raises(ValueError, match="unsupported decision"):
        _entry(decision=cast(PromotionDecision, "cache"))


def test_rejects_missing_idempotency_key() -> None:
    with pytest.raises(ValueError, match="idempotency_key"):
        _entry(idempotency_key=" ")


def test_rejects_blank_policy_version() -> None:
    with pytest.raises(ValueError, match="policy_version"):
        _entry(policy_version=" ")


def test_rejects_unsupported_validation_status() -> None:
    with pytest.raises(ValueError, match="unsupported validation_status"):
        _entry(validation_status=cast(ValidationStatus, "promoted"))


def test_rejects_invalid_source_event_for_promote_or_supersede() -> None:
    invalid_source = _source_event(validation_status="degraded")

    with pytest.raises(ValueError, match="valid source_event"):
        _entry(source_event=invalid_source)
    with pytest.raises(ValueError, match="valid source_event"):
        _entry(
            source_event=invalid_source,
            decision="supersede",
            idempotency_key="idem:supersede-invalid-source",
            supersedes=("promotion-ledger:abc123",),
        )


def test_rejects_non_eval_source_event_rail() -> None:
    runtime_source = _source_event(
        rail="runtime",
        idempotency_key="idem:runtime-source-event",
    )

    with pytest.raises(ValueError, match="source_event rail"):
        _entry(source_event=runtime_source)


def test_reject_and_defer_can_record_degraded_source_without_promoting() -> None:
    degraded_source = _source_event(validation_status="degraded")
    rejected = _entry(
        source_event=degraded_source,
        decision="reject",
        idempotency_key="idem:reject-degraded",
    )
    deferred = _entry(
        source_event=degraded_source,
        decision="defer",
        idempotency_key="idem:defer-degraded",
    )

    assert rejected.decision == "reject"
    assert rejected.validation_status == "degraded"
    assert deferred.decision == "defer"
    assert deferred.validation_status == "degraded"


def test_rejects_self_supersession_and_duplicate_supersedes() -> None:
    base = _entry()

    with pytest.raises(ValueError, match="supersede decision requires"):
        _entry(decision="supersede", idempotency_key="idem:supersede-missing")
    with pytest.raises(ValueError, match="duplicate"):
        _entry(
            decision="supersede",
            idempotency_key="idem:supersede-duplicates",
            supersedes=(base.ledger_entry_id, base.ledger_entry_id),
        )

    superseding = _entry(
        decision="supersede",
        idempotency_key="idem:supersedes-base",
        supersedes=(base.ledger_entry_id,),
    )
    with pytest.raises(ValueError, match="supersede itself"):
        create_promotion_ledger_entry(
            source_event=_source_event(),
            promotion_id="promotion-rag-gate-1",
            decision="supersede",
            idempotency_key="idem:supersedes-base",
            producer=_producer(),
            produced_at=_FIXED_TIMESTAMP,
            supersedes=(base.ledger_entry_id, superseding.ledger_entry_id),
            ledger_entry_id=superseding.ledger_entry_id,
        )


def test_normalizes_and_sorts_upstream_supersedes_and_reason_codes() -> None:
    base = _entry()
    entry = _entry(
        decision="supersede",
        idempotency_key="idem:supersede-sorted",
        upstream_ids=("z-upstream", "a-upstream", "z-upstream"),
        supersedes=("promotion-ledger:bbbb", base.ledger_entry_id),
        reason_codes=("ZETA", "alpha"),
    )

    assert entry.upstream_ids == tuple(sorted(entry.upstream_ids))
    assert entry.supersedes == tuple(sorted(entry.supersedes))
    assert entry.reason_codes == ("alpha", "zeta")

    with pytest.raises(ValueError, match="reason_codes collide"):
        _entry(reason_codes=("Alpha", " alpha "))


def test_preserves_metadata_defensively() -> None:
    metadata: dict[str, Any] = {
        "labels": ["rag", "gate"],
        "stats": {"sample_size": 2},
    }
    entry = _entry(metadata=metadata)

    metadata["labels"].append("mutated")
    metadata["stats"]["sample_size"] = 999
    returned = entry.metadata
    returned["labels"].append("also-mutated")

    assert entry.metadata == {"labels": ["rag", "gate"], "stats": {"sample_size": 2}}


def test_metadata_keys_are_normalized_and_collision_checked_with_path_context() -> None:
    entry = _entry(metadata={" Labels ": ["rag"], "STATS": {" Sample_Size ": 2}})

    assert entry.metadata == {"labels": ["rag"], "stats": {"sample_size": 2}}

    with pytest.raises(ValueError, match=r"metadata key at stats\.sample_size"):
        _entry(metadata={"stats": {" Sample_Size ": 2, "sample_size": 3}})
    with pytest.raises(ValueError, match=r"metadata key at 1"):
        _entry(metadata=cast(dict[str, Any], {1: "bad"}))


@pytest.mark.parametrize(
    "metadata",
    [
        {"raw_prompt": "tell me about dinner"},
        {"raw_response": "model output"},
        {"nested": {"user_health_payload": "private"}},
        {"notes": "raw prompt: tell me about dinner"},
        {"notes": "user health payload from eval item"},
        {"notes": cast(Any, b"raw-bytes")},
        {"token_like": "Bearer abc"},
        {"artifact": "artifacts/rag_eval/run-1/traces.jsonl"},
        {"note": "C:/Users/example/eval.json"},
    ],
)
def test_rejects_raw_prompt_response_secret_user_health_or_path_metadata(
    metadata: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="metadata"):
        _entry(metadata=metadata)


def test_stable_serialization_and_ledger_entry_id() -> None:
    first = _entry(
        upstream_ids=("z", "a", "z"),
        reason_codes=("BETA", "alpha"),
        metadata={"z": 1, "a": ["x", "y"]},
    )
    second = _entry(
        upstream_ids=("a", "z"),
        reason_codes=("alpha", "beta"),
        metadata={"a": ["x", "y"], "z": 1},
    )

    assert first.ledger_entry_id == second.ledger_entry_id
    assert first.to_json() == second.to_json()


def test_rejects_non_deterministic_or_mismatched_ledger_entry_id() -> None:
    with pytest.raises(ValueError, match="ledger_entry_id"):
        _entry(ledger_entry_id="promotion-ledger:not-the-derived-id")


def test_promotion_ledger_module_does_not_import_runtime_surfaces() -> None:
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
    tree = ast.parse(_PROMOTION_MODULE.read_text(encoding="utf-8"))

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
