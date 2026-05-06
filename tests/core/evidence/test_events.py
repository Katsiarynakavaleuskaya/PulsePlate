from __future__ import annotations

import ast
import math
from pathlib import Path
from typing import cast

import pytest

from core.evidence.assets import EvidenceAssetRef, create_evidence_asset_ref
from core.evidence.events import (
    EvalEventRail,
    EvalEventType,
    EvidenceEvalEvent,
    ValidationStatus,
    create_eval_event,
    validate_produced_at,
    validate_source_artifact,
)
from core.evidence.fingerprints import fingerprint_payload

_REPO_ROOT = Path(__file__).resolve().parents[3]
_EVENTS_MODULE = _REPO_ROOT / "core" / "evidence" / "events.py"
_FIXED_TIMESTAMP = "2026-05-05T12:00:00+00:00"


def _asset_ref() -> EvidenceAssetRef:
    return create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="runtime",
        policy_version="policy-v1",
        payload={"run": "rag-gate"},
    )


def _make_event(**overrides: object) -> EvidenceEvalEvent:
    params = {
        "event_type": "rag_gate_run",
        "rail": "eval",
        "source_artifact": "artifacts/rag_eval/run-1/traces.jsonl",
        "asset_refs": (_asset_ref(),),
        "upstream_ids": (" gate-report-1 ", "dataset-1", "dataset-1"),
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


def test_creates_valid_rag_gate_event_with_source_artifact_path() -> None:
    event = _make_event()

    payload = event.to_dict()

    assert event.event_id.startswith("eval-event:")
    assert payload["event_type"] == "rag_gate_run"
    assert payload["rail"] == "eval"
    assert payload["source_artifact"] == "artifacts/rag_eval/run-1/traces.jsonl"
    assert payload["upstream_ids"] == ["dataset-1", "gate-report-1"]
    assert payload["asset_refs"][0]["asset_id"].startswith("evidence:eval_run:runtime:v1:")


def test_creates_valid_ragas_report_event() -> None:
    event = _make_event(
        event_type="ragas_report",
        source_artifact="evals/ragas/report.json",
        fingerprint=fingerprint_payload(
            {
                "faithfulness": 1.0,
                "answer_relevancy": 0.95,
                "context_precision": 0.9,
            }
        ),
        idempotency_key="idem:ragas-report-1",
        producer_name="ragas-bootstrap",
        metadata={
            "faithfulness": 1.0,
            "answer_relevancy": 0.95,
            "context_precision": 0.9,
            "report_only": True,
        },
    )

    assert event.event_type == "ragas_report"
    assert event.metadata["report_only"] is True


def test_creates_valid_eval_validity_sidecar_event() -> None:
    event = _make_event(
        event_type="eval_validity_record",
        source_artifact="artifacts/evals/validity_items.jsonl",
        fingerprint=fingerprint_payload({"canonical_id": "rag_001", "passed": True}),
        idempotency_key="idem:eval-validity-record-1",
        producer_name="eval-validity",
        metadata={"canonical_id": "rag_001", "variant_family": "canonical"},
    )

    assert event.event_type == "eval_validity_record"
    assert event.metadata["canonical_id"] == "rag_001"


def test_creates_valid_judgment_validity_sidecar_event() -> None:
    event = _make_event(
        event_type="judgment_validity_record",
        source_artifact="artifacts/evals/judgment_validity_items.jsonl",
        fingerprint=fingerprint_payload({"case_id": "judgment_001", "decision": "defer"}),
        idempotency_key="idem:judgment-validity-record-1",
        producer_name="judgment-validity",
        metadata={"case_id": "judgment_001", "decision": "defer"},
    )

    assert event.event_type == "judgment_validity_record"


@pytest.mark.parametrize(
    ("event_type", "source_artifact", "metadata"),
    [
        (
            "rag_gate_report",
            "artifacts/rag_eval/run-1/gate_report.md",
            {"report_format": "markdown", "decision": "PASS"},
        ),
        (
            "item_metadata",
            "data/evals/eval_item_metadata_registry.jsonl",
            {"canonical_id": "rag_001", "difficulty_band": "low"},
        ),
        (
            "item_statistics",
            "artifacts/evals/item_statistics_report.json",
            {"canonical_id": "rag_001", "instability_flag": False},
        ),
        (
            "gate_metric",
            "artifacts/rag_eval/run-1/metrics_summary.json",
            {"metric": "support_precision", "value": 0.91},
        ),
        (
            "gate_decision",
            "artifacts/rag_eval/run-1/rag_gate_result.json",
            {"decision": "PASS"},
        ),
    ],
)
def test_current_eval_artifact_event_types_are_supported(
    event_type: str,
    source_artifact: str,
    metadata: dict[str, object],
) -> None:
    event = _make_event(
        event_type=cast(EvalEventType, event_type),
        source_artifact=source_artifact,
        fingerprint=fingerprint_payload(metadata),
        idempotency_key=f"idem:{event_type}",
        metadata=metadata,
    )

    assert event.event_type == event_type


def test_rejects_unknown_rail() -> None:
    with pytest.raises(ValueError, match="unsupported rail"):
        _make_event(rail=cast(EvalEventRail, "wiki"))


@pytest.mark.parametrize(
    "source_artifact",
    [
        " ",
        ".",
        "./",
        "./.",
        "../traces.jsonl",
        "artifacts/rag_eval/../secret.json",
        "/tmp/traces.jsonl",
        "~/traces.jsonl",
        "C:/traces.jsonl",
        "C:\\traces.jsonl",
        "C:traces.jsonl",
        "worktrees/agent/traces.jsonl",
        ".venv/traces.jsonl",
        "artifacts/agent_runs/run-1.json",
        "artifacts/orchestration/task_packets/run-1.json",
        "artifacts/security_lab/lab-1.json",
    ],
)
def test_rejects_unsafe_source_artifact_paths(source_artifact: str) -> None:
    with pytest.raises(ValueError, match="source_artifact"):
        validate_source_artifact(source_artifact)


def test_rejects_missing_fingerprint() -> None:
    with pytest.raises(ValueError, match="fingerprint"):
        _make_event(fingerprint="")


def test_rejects_missing_idempotency_key() -> None:
    with pytest.raises(ValueError, match="idempotency_key"):
        _make_event(idempotency_key=" ")


def test_rejects_idempotency_key_with_whitespace() -> None:
    with pytest.raises(ValueError, match="idempotency_key"):
        _make_event(idempotency_key="idem key")


def test_rejects_unknown_event_type_and_validation_status() -> None:
    with pytest.raises(ValueError, match="unsupported event_type"):
        _make_event(event_type=cast(EvalEventType, "semantic_cache_hit"))
    with pytest.raises(ValueError, match="unsupported validation_status"):
        _make_event(validation_status=cast(ValidationStatus, "promoted"))


def test_validate_produced_at_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone"):
        validate_produced_at("2026-05-05T12:00:00")


def test_validate_produced_at_rejects_empty_timestamp() -> None:
    with pytest.raises(ValueError, match="produced_at"):
        validate_produced_at(" ")


def test_validate_produced_at_accepts_z_suffix_timestamp() -> None:
    assert validate_produced_at("2026-05-05T12:00:00Z") == "2026-05-05T12:00:00Z"


@pytest.mark.parametrize(
    "metadata",
    [
        {"raw_prompt": "tell me about dinner"},
        {"nested": {"user_health_payload": "private"}},
        {"token_like": "Bearer abc"},
    ],
)
def test_rejects_raw_secret_or_user_health_metadata(metadata: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="metadata"):
        _make_event(metadata=metadata)


def test_rejects_duplicate_metadata_keys_after_normalization() -> None:
    with pytest.raises(ValueError, match="collides after normalization"):
        _make_event(metadata={"metric": 1, " metric ": 2})


def test_rejects_non_string_metadata_key() -> None:
    metadata = cast(dict[str, object], {1: "bad"})

    with pytest.raises(ValueError, match="metadata keys must be strings"):
        _make_event(metadata=metadata)


def test_rejects_empty_metadata_key_after_normalization() -> None:
    with pytest.raises(ValueError, match="metadata keys must be non-empty"):
        _make_event(metadata={" ": "bad"})


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_rejects_non_finite_metadata_numbers(value: float) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        _make_event(metadata={"metric": value})


def test_metadata_sequence_errors_include_item_index() -> None:
    with pytest.raises(ValueError, match="labels\\.1"):
        _make_event(metadata={"labels": ["ok", object()]})


def test_preserves_asset_refs_upstream_ids_and_metadata_defensively() -> None:
    asset_refs = [_asset_ref()]
    upstream_ids = ["z-upstream", "a-upstream"]
    metadata = {"labels": ["rag", "gate"], "stats": {"sample_size": 2}}

    event = _make_event(asset_refs=asset_refs, upstream_ids=upstream_ids, metadata=metadata)

    asset_refs.clear()
    upstream_ids.append("mutated")
    metadata["labels"].append("mutated")
    metadata["stats"]["sample_size"] = 999
    returned_metadata = event.metadata
    returned_metadata["labels"].append("also-mutated")

    assert len(event.asset_refs) == 1
    assert event.upstream_ids == ("a-upstream", "z-upstream")
    assert event.metadata == {"labels": ["rag", "gate"], "stats": {"sample_size": 2}}


def test_stable_serialization_and_event_id() -> None:
    first = _make_event(
        upstream_ids=("b", "a", "b"),
        metadata={"z": 1, "a": ["x", "y"]},
    )
    second = _make_event(
        upstream_ids=("a", "b"),
        metadata={"a": ["x", "y"], "z": 1},
    )

    assert first.event_id == second.event_id
    assert first.to_json() == second.to_json()


def test_non_eval_event_rails_reject_cross_rail_asset_refs() -> None:
    advisory_ref = create_evidence_asset_ref(
        asset_type="gate_report",
        version="v1",
        rail="advisory",
        policy_version="policy-v1",
        payload={"report": "advisory"},
    )

    with pytest.raises(ValueError, match="cross-rail asset_refs"):
        _make_event(rail="runtime", asset_refs=(advisory_ref,))


def test_events_module_does_not_import_runtime_or_eval_runner_surfaces() -> None:
    forbidden_prefixes = (
        "app",
        "providers",
        "redis",
        "scripts.evals",
        "evals",
        "mcp_pulseplate_server",
        "legacy_app",
    )
    forbidden_fragments = ("semantic_cache", "wiki")
    tree = ast.parse(_EVENTS_MODULE.read_text(encoding="utf-8"))

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
        assert not any(fragment in module_name for fragment in forbidden_fragments)
