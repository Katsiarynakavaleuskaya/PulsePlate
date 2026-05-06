from __future__ import annotations

import ast
import math
from pathlib import Path
from typing import Any, cast

import pytest

from core.evidence.admission import (
    AdmissionAction,
    AdmissionInput,
    AdmissionPolicy,
    admission_input_from_eval_event,
    admission_input_from_ledger_entry,
    decide_admission,
    decide_allow_execute,
    decide_allow_promote,
    decide_allow_serve,
)
from core.evidence.assets import create_evidence_asset_ref
from core.evidence.events import (
    EvalEventProducer,
    EvidenceEvalEvent,
    ValidationStatus,
    create_eval_event,
)
from core.evidence.fingerprints import fingerprint_payload
from core.evidence.promotion_ledger import create_promotion_ledger_entry

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ADMISSION_MODULE = _REPO_ROOT / "core" / "evidence" / "admission.py"
_FIXED_TIMESTAMP = "2026-05-06T12:00:00+00:00"
_NOW = "2026-05-06T13:00:00+00:00"


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
        "upstream_ids": ("dataset-1", "gate-report-1"),
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


def _ledger_entry(**overrides: object):
    params: dict[str, Any] = {
        "source_event": _source_event(),
        "promotion_id": "promotion-rag-gate-1",
        "decision": "promote",
        "idempotency_key": "idem:promotion-rag-gate-1",
        "producer": _producer(),
        "produced_at": _FIXED_TIMESTAMP,
        "reason_codes": ("policy-pass",),
        "metadata": {"confidence": 1.0},
    }
    params.update(overrides)
    return create_promotion_ledger_entry(**params)


def _policy(**overrides: object) -> AdmissionPolicy:
    params: dict[str, Any] = {
        "policy_version": "policy-v1",
        "min_verification_rate": 0.9,
        "min_coverage_rate": 0.8,
        "max_fallback_rate": 0.1,
        "stale_after_seconds": 24 * 60 * 60,
    }
    params.update(overrides)
    return AdmissionPolicy(**params)


def _input(**overrides: object) -> AdmissionInput:
    params: dict[str, Any] = {
        "target_id": "eval-event:target-1",
        "target_type": "eval_event",
        "fingerprint": fingerprint_payload({"target": "eval-event-1"}),
        "idempotency_key": "idem:admission-target-1",
        "policy_version": "policy-v1",
        "produced_at": _FIXED_TIMESTAMP,
        "validation_status": "valid",
        "coverage_rate": 0.95,
        "verification_rate": 0.98,
        "fallback_rate": 0.02,
        "upstream_ids": ("gate-report-1", "dataset-1", "dataset-1"),
        "source_event_id": "eval-event:source-1",
        "event_type": "rag_gate_run",
        "metadata": {"labels": ["rag", "gate"]},
    }
    params.update(overrides)
    return AdmissionInput(**params)


def test_admission_allows_valid_execute_input() -> None:
    decision = decide_allow_execute(
        admission_input=_input(),
        policy=_policy(),
        now=_NOW,
    )

    assert decision.allowed is True
    assert decision.action == "execute"
    assert decision.reason_codes == ("execute_allowed",)
    assert decision.blocking_reasons == ()
    assert decision.decision_id.startswith("admission-decision:")


def test_admission_allows_valid_promote_input() -> None:
    decision = decide_allow_promote(
        admission_input=_input(),
        policy=_policy(),
        now=_NOW,
    )

    assert decision.allowed is True
    assert decision.reason_codes == ("promote_allowed",)


def test_admission_allows_serve_for_valid_non_stale_promoted_evidence() -> None:
    entry = _ledger_entry()
    admission_input = admission_input_from_ledger_entry(
        entry=entry,
        coverage_rate=0.95,
        verification_rate=0.99,
        fallback_rate=0.01,
    )

    decision = decide_allow_serve(
        admission_input=admission_input,
        policy=_policy(),
        now=_NOW,
    )

    assert decision.allowed is True
    assert decision.target_type == "promotion_ledger_entry"
    assert decision.reason_codes == ("serve_allowed",)


def test_admission_input_can_be_created_from_eval_event() -> None:
    event = _source_event()

    admission_input = admission_input_from_eval_event(
        event=event,
        coverage_rate=0.9,
        verification_rate=0.95,
        fallback_rate=0.02,
    )

    assert admission_input.target_id == event.event_id
    assert admission_input.source_event_id == event.event_id
    assert admission_input.event_type == "rag_gate_run"


def test_admission_blocks_execute_with_malformed_fingerprint() -> None:
    with pytest.raises(ValueError, match="fingerprint"):
        _input(fingerprint="not-a-fingerprint")


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("target_id", " ", "target_id"),
        ("target_type", "cache", "target_type"),
        ("idempotency_key", " ", "idempotency_key"),
        ("policy_version", " ", "policy_version"),
    ],
)
def test_admission_rejects_blank_identity_or_unsupported_target_type(
    field: str,
    value: str,
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        _input(**{field: value})


def test_admission_rejects_unsupported_status_and_action() -> None:
    with pytest.raises(ValueError, match="unsupported validation_status"):
        _input(validation_status=cast(ValidationStatus, "promoted"))

    with pytest.raises(ValueError, match="unsupported admission action"):
        decide_admission(
            action=cast(AdmissionAction, "cache"),
            admission_input=_input(),
            policy=_policy(),
            now=_NOW,
        )


@pytest.mark.parametrize("status", ["invalid", "degraded", "deferred"])
def test_admission_blocks_promote_when_status_is_not_valid(status: str) -> None:
    decision = decide_allow_promote(
        admission_input=_input(validation_status=cast(ValidationStatus, status)),
        policy=_policy(
            allow_degraded=True,
            allowed_validation_statuses=("valid", "invalid", "degraded", "deferred"),
        ),
        now=_NOW,
    )

    assert decision.allowed is False
    assert "promote_requires_valid_status" in decision.blocking_reasons


def test_admission_blocks_promote_when_verification_below_threshold() -> None:
    decision = decide_allow_promote(
        admission_input=_input(verification_rate=0.89),
        policy=_policy(min_verification_rate=0.9),
        now=_NOW,
    )

    assert decision.allowed is False
    assert "verification_rate_below_threshold" in decision.blocking_reasons


def test_admission_blocks_promote_when_coverage_below_threshold() -> None:
    decision = decide_allow_promote(
        admission_input=_input(coverage_rate=0.79),
        policy=_policy(min_coverage_rate=0.8),
        now=_NOW,
    )

    assert decision.allowed is False
    assert "coverage_rate_below_threshold" in decision.blocking_reasons


def test_admission_blocks_promote_when_fallback_above_threshold() -> None:
    decision = decide_allow_promote(
        admission_input=_input(fallback_rate=0.11),
        policy=_policy(max_fallback_rate=0.1),
        now=_NOW,
    )

    assert decision.allowed is False
    assert "fallback_rate_above_threshold" in decision.blocking_reasons


def test_admission_blocks_degraded_reason_unless_policy_allows_it() -> None:
    blocked = decide_allow_promote(
        admission_input=_input(degraded_reason="low-confidence-eval"),
        policy=_policy(),
        now=_NOW,
    )
    allowed = decide_allow_promote(
        admission_input=_input(degraded_reason="low-confidence-eval"),
        policy=_policy(allow_degraded=True),
        now=_NOW,
    )

    assert blocked.allowed is False
    assert "degraded_reason_not_allowed" in blocked.blocking_reasons
    assert allowed.allowed is True
    assert allowed.warnings == ("degraded_input_allowed",)


def test_admission_blocks_stale_and_future_timestamps_with_explicit_now() -> None:
    stale = decide_allow_execute(
        admission_input=_input(produced_at="2026-05-05T12:00:00+00:00"),
        policy=_policy(stale_after_seconds=60),
        now=_NOW,
    )
    future = decide_allow_execute(
        admission_input=_input(produced_at="2026-05-07T12:00:00+00:00"),
        policy=_policy(),
        now=_NOW,
    )

    assert stale.allowed is False
    assert "stale_input" in stale.blocking_reasons
    assert future.allowed is False
    assert "produced_at_in_future" in future.blocking_reasons


def test_admission_blocks_promote_without_upstream_lineage() -> None:
    decision = decide_allow_promote(
        admission_input=_input(upstream_ids=()),
        policy=_policy(),
        now=_NOW,
    )

    assert decision.allowed is False
    assert "upstream_lineage_required" in decision.blocking_reasons


def test_admission_blocks_serve_for_stale_or_degraded_evidence_unless_policy_allows_it() -> None:
    stale = decide_allow_serve(
        admission_input=_input(produced_at="2026-05-05T12:00:00+00:00"),
        policy=_policy(stale_after_seconds=60),
        now=_NOW,
    )
    degraded = decide_allow_serve(
        admission_input=_input(validation_status="degraded"),
        policy=_policy(allowed_validation_statuses=("valid", "degraded")),
        now=_NOW,
    )
    allowed_degraded = decide_allow_serve(
        admission_input=_input(validation_status="degraded"),
        policy=_policy(
            allow_degraded=True,
            allowed_validation_statuses=("valid", "degraded"),
        ),
        now=_NOW,
    )

    assert stale.allowed is False
    assert "stale_input" in stale.blocking_reasons
    assert degraded.allowed is False
    assert "serve_requires_valid_status" in degraded.blocking_reasons
    assert allowed_degraded.allowed is True


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
        {"note": "."},
        {"note": "./"},
        {"note": "./."},
    ],
)
def test_admission_metadata_rejects_prompt_response_secret_user_health_or_paths(
    metadata: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="metadata"):
        _input(metadata=metadata)


@pytest.mark.parametrize("metric_value", [math.nan, math.inf, -math.inf, -0.1, 1.1])
def test_admission_rejects_non_finite_or_out_of_range_metrics(metric_value: float) -> None:
    with pytest.raises(ValueError, match="coverage_rate"):
        _input(coverage_rate=metric_value)


def test_admission_rejects_unsupported_event_type_and_decision_by_policy() -> None:
    event_blocked = decide_allow_execute(
        admission_input=_input(event_type="ragas_report"),
        policy=_policy(allowed_event_types=("rag_gate_run",)),
        now=_NOW,
    )
    decision_blocked = decide_allow_serve(
        admission_input=_input(
            target_type="promotion_ledger_entry",
            promotion_decision="reject",
            promotion_id="promotion-rag-gate-1",
        ),
        policy=_policy(allowed_decisions=("promote", "supersede")),
        now=_NOW,
    )

    assert event_blocked.allowed is False
    assert "event_type_not_allowed" in event_blocked.blocking_reasons
    assert decision_blocked.allowed is False
    assert "promotion_decision_not_allowed" in decision_blocked.blocking_reasons


def test_admission_rejects_policy_mismatch_and_bad_policy_values() -> None:
    with pytest.raises(ValueError, match="policy_version"):
        decide_allow_execute(
            admission_input=_input(policy_version="policy-v2"),
            policy=_policy(),
            now=_NOW,
        )
    with pytest.raises(ValueError, match="stale_after_seconds"):
        _policy(stale_after_seconds=-1)


def test_admission_preserves_metadata_upstreams_and_decision_metadata_defensively() -> None:
    metadata: dict[str, Any] = {
        "labels": ["rag", "gate"],
        "stats": {"coverage": 0.95},
    }
    upstream_ids = ["z-upstream", "a-upstream"]
    admission_input = _input(metadata=metadata, upstream_ids=upstream_ids)

    metadata["labels"].append("mutated")
    metadata["stats"]["coverage"] = 0.1
    upstream_ids.append("mutated")

    decision = decide_allow_execute(
        admission_input=admission_input,
        policy=_policy(),
        now=_NOW,
    )
    returned_metadata = cast(dict[str, Any], decision.metadata)
    returned_metadata["input"]["metadata"]["labels"].append("also-mutated")

    assert admission_input.upstream_ids == ("a-upstream", "z-upstream")
    assert admission_input.metadata == {
        "labels": ["rag", "gate"],
        "stats": {"coverage": 0.95},
    }
    decision_metadata = cast(dict[str, Any], decision.metadata)
    assert decision_metadata["input"]["metadata"] == {
        "labels": ["rag", "gate"],
        "stats": {"coverage": 0.95},
    }


def test_admission_stable_serialization_and_decision_identity() -> None:
    first = _input(
        upstream_ids=("z-upstream", "a-upstream", "z-upstream"),
        metadata={"z": 1, "a": ["x", "y"]},
    )
    second = _input(
        upstream_ids=("a-upstream", "z-upstream"),
        metadata={"a": ["x", "y"], "z": 1},
    )

    first_decision = decide_allow_promote(
        admission_input=first,
        policy=_policy(),
        now=_NOW,
    )
    second_decision = decide_allow_promote(
        admission_input=second,
        policy=_policy(),
        now=_NOW,
    )

    assert first_decision.decision_id == second_decision.decision_id
    assert first_decision.to_json() == second_decision.to_json()


def test_admission_rejects_current_directory_degraded_reason_without_index_error() -> None:
    with pytest.raises(ValueError, match="path-like"):
        _input(degraded_reason="./.")


def test_admission_module_does_not_import_runtime_surfaces() -> None:
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
        "knowledge",
    )
    tree = ast.parse(_ADMISSION_MODULE.read_text(encoding="utf-8"))

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
