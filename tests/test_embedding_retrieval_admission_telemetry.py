from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration.embedding_retrieval_admission_telemetry import (
    EMBEDDING_RETRIEVAL_AUTHORITY_BOUNDARY,
    EmbeddingRetrievalAdmissionTelemetry,
    EmbeddingRetrievalEvidenceRef,
    build_embedding_retrieval_admission_policy_snapshot,
    build_embedding_retrieval_admission_telemetry,
    embedding_retrieval_admission_to_stable_mapping,
)
from tests.helpers.semantic_cache_import_guard import (
    assert_no_forbidden_semantic_cache_calls,
    assert_no_forbidden_semantic_cache_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE = REPO_ROOT / "scripts" / "orchestration" / "embedding_retrieval_admission_telemetry.py"


def _telemetry() -> EmbeddingRetrievalAdmissionTelemetry:
    return build_embedding_retrieval_admission_telemetry(
        candidate_paths=(
            "scripts/orchestration/embedding_retrieval_admission_telemetry.py",
            "docs/orchestration/contracts/SEMANTIC_CACHE_EMBEDDING_RETRIEVAL_ADMISSION_TELEMETRY.md",
            "tests/test_embedding_retrieval_admission_telemetry.py",
        ),
        required_context=("AGENTS.md", "RUNBOOK_AGENT.md", "docs/roadmap/BACKLOG_LEDGER.md"),
        pr_phase="pre_open",
        domain="ai_runtime",
        cluster="orchestration",
    )


def test_policy_snapshot_is_deterministic_metadata_only() -> None:
    first = build_embedding_retrieval_admission_policy_snapshot()
    second = build_embedding_retrieval_admission_policy_snapshot(
        metadata={"fingerprint_ref": fingerprint_payload({"safe": "metadata"})}
    )

    assert first.policy_id == second.policy_id
    assert first.authority_boundary == EMBEDDING_RETRIEVAL_AUTHORITY_BOUNDARY
    stable = dict(embedding_retrieval_admission_to_stable_mapping(first))
    assert stable["policy_version"] == "embedding-retrieval-admission-o4-v1"
    assert stable["authority_boundary"] == "metadata_only_non_serving"
    assert stable["gate_status"] == "closed"
    assert "embedding_candidate" in stable["candidate_types"]
    assert "retrieval_candidate" in stable["candidate_types"]


def test_admission_telemetry_is_deterministic_and_closed_gate() -> None:
    first = dict(embedding_retrieval_admission_to_stable_mapping(_telemetry()))
    second = dict(embedding_retrieval_admission_to_stable_mapping(_telemetry()))

    assert first == second
    assert first["telemetry_phase"] == "PR-O4"
    assert first["admission_allowed"] is False
    assert first["embedding_allowed"] is False
    assert first["retrieval_runtime_allowed"] is False
    assert first["semantic_similarity_allowed"] is False
    assert first["vector_search_allowed"] is False
    assert first["provider_calls_allowed"] is False
    assert first["cache_read_allowed"] is False
    assert first["cache_write_allowed"] is False
    assert first["serving_allowed"] is False
    assert first["selected_embedding_backend"] == "none"
    assert first["selected_retrieval_runtime"] == "none"
    assert len(first["evidence_refs"]) >= 3
    assert len(first["candidates"]) == 3
    for reason in (
        "gate_closed",
        "metadata_only",
        "admission_deferred",
        "no_embeddings",
        "no_vector_search",
        "no_runtime_retrieval",
        "no_provider_call",
        "no_cache_serving",
        "future_gate_required",
    ):
        assert reason in first["reason_codes"]


def test_admission_telemetry_serializes_without_raw_or_local_payloads() -> None:
    serialized = json.dumps(
        dict(embedding_retrieval_admission_to_stable_mapping(_telemetry())),
        sort_keys=True,
    )

    for blocked in (
        "raw_prompt",
        "raw_query",
        "normalized_query",
        "raw_context",
        "raw_answer",
        "provider_payload",
        "embedding_vector",
        "similarity_score",
        "/Users/",
        "/tmp/",
        "authorization",
        "live_savings",
    ):
        assert blocked not in serialized


@pytest.mark.parametrize(
    "metadata",
    (
        {"raw_prompt": "unsafe"},
        {"payload": "provider_payload"},
        {"path": "/Users/name/private.txt"},
        {"tmp_path": "/tmp/private.txt"},
        {"auth_marker": "authorization"},
        {"query": "normalized_query"},
        {"vector": "embedding_vector"},
        {"score": "semantic_similarity"},
        {"route": "retrieval_runtime"},
        {"claim": "live_savings"},
        {"review": "model_downgrade"},
        {"fingerprint_ref": "sha256:not-a-full-digest"},
    ),
)
def test_admission_telemetry_rejects_unsafe_metadata(metadata: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        build_embedding_retrieval_admission_telemetry(
            candidate_paths=("scripts/orchestration/task_bootstrap.py",),
            required_context=("AGENTS.md",),
            pr_phase="pre_open",
            domain="ai_runtime",
            cluster="orchestration",
            metadata=metadata,
        )


def test_evidence_ref_rejects_malformed_fingerprint_without_echoing_payload() -> None:
    with pytest.raises(ValueError, match="fingerprint"):
        EmbeddingRetrievalEvidenceRef(
            ref_id="embedding-retrieval-ref:" + "1" * 24,
            ref_type="contract",
            source_path="docs/orchestration/contracts/example.md",
            source_fingerprint="sha256:not-a-full-digest",
            metadata={},
        )


def test_admission_telemetry_rejects_any_runtime_authority_flag() -> None:
    telemetry = _telemetry()

    with pytest.raises(ValueError, match="embedding_allowed"):
        EmbeddingRetrievalAdmissionTelemetry(
            telemetry_id=telemetry.telemetry_id,
            telemetry_phase=telemetry.telemetry_phase,
            policy_snapshot_id=telemetry.policy_snapshot_id,
            evidence_refs=telemetry.evidence_refs,
            candidates=telemetry.candidates,
            admission_allowed=False,
            embedding_allowed=True,
            retrieval_runtime_allowed=False,
            semantic_similarity_allowed=False,
            vector_search_allowed=False,
            provider_calls_allowed=False,
            cache_read_allowed=False,
            cache_write_allowed=False,
            serving_allowed=False,
            selected_embedding_backend="none",
            selected_retrieval_runtime="none",
            required_followups=telemetry.required_followups,
            reason_codes=telemetry.reason_codes,
            metadata={},
        )


def test_embedding_retrieval_admission_has_no_runtime_imports_or_effects() -> None:
    assert_no_forbidden_semantic_cache_imports(MODULE)
    assert_no_forbidden_semantic_cache_calls(MODULE)
