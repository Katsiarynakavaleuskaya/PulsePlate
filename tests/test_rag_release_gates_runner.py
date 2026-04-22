"""Tests for the PulsePlate RAG release-gates runner."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from core.ai import prepare_insight_runtime
from core.insight.philosophy_validator import validate_llm_output
from core.rag.contracts import RAGChunk, RAGDegradedReason
from core.rag.orchestration import RAGOrchestrationResult, retrieve_and_validate_rag
from app.security.agent_input_guard import scan_ai_agent_input
from app.services.insight_runtime import generate_traced_insight
from scripts.evals import run_rag_release_gates as runner
from scripts.evals.run_rag_release_gates import (
    EvalConfig,
    EvalRow,
    EvalRuntimeState,
    PulsePlateImports,
    apply_calibration,
    build_config,
    chunk_text,
    evaluate_one,
    expected_calibration_error,
    generate_answer,
    lexical_support_score,
    load_pulseplate_imports,
    main,
    map_orchestration_result_to_retrieved,
    map_rag_chunk,
    nli_entailment_score,
    proxy_correctness,
    retrieve,
    sanitize_experiment_id,
    validate_output_with_pulseplate,
    write_artifacts,
    write_summary_notebook,
)


def _config(tmp_path: Path, *, enable_nli_model: bool = False) -> EvalConfig:
    """Build a minimal config for helper tests."""

    return EvalConfig(
        project_root=tmp_path,
        input_path=tmp_path / "input.jsonl",
        artifact_root=tmp_path / "artifacts" / "rag_eval",
        experiment_id="test_run",
        sample_size=5,
        top_k=5,
        random_seed=42,
        retriever_mode="local_tfidf",
        generator_mode="extractive_stub",
        enable_nli_model=enable_nli_model,
        nli_model_name="roberta-large-mnli",
        notebook_path=tmp_path / "notebooks" / "pulseplate_rag_release_gates.ipynb",
        require_pass=False,
    )


def _make_release_gate_state(
    tmp_path: Path,
    *,
    experiment_id: str = "test_run",
    allow_runtime_fallbacks: bool = True,
) -> EvalRuntimeState:
    """Build a minimal runtime state for release-gate summary tests."""

    config = _config(tmp_path)
    config = EvalConfig(
        **{
            **config.__dict__,
            "experiment_id": experiment_id,
            "allow_runtime_fallbacks": allow_runtime_fallbacks,
        }
    )
    return EvalRuntimeState(config=config, pulseplate_imports=PulsePlateImports())


def _make_trace(
    query_id: str,
    *,
    routing_decision: str = "ship_candidate",
    recall_at_effective_k: float = 0.9,
    evidence_exact_match: bool = True,
    mean_nli_entailment: float = 0.9,
    support_precision: float = 0.9,
) -> dict[str, object]:
    """Build a deterministic trace row for summary-only tests."""

    return {
        "trace_id": f"trace-{query_id}",
        "timestamp": "2026-04-22T00:00:00+00:00",
        "experiment_id": "test_run",
        "query_id": query_id,
        "query_text": f"Query {query_id}",
        "top_k_retrieved": [{"doc_id": "docs/tiers.md", "source_url": "docs/tiers.md"}],
        "retrieval_metrics": {
            "recall_at_3": recall_at_effective_k,
            "recall_at_10": recall_at_effective_k,
            "recall_at_50": recall_at_effective_k,
            "recall_at_effective_k": recall_at_effective_k,
            "mrr_at_10": recall_at_effective_k,
            "ndcg_at_10": recall_at_effective_k,
        },
        "faithfulness_metrics": {
            "evidence_exact_match": evidence_exact_match,
            "mean_nli_entailment": mean_nli_entailment,
            "support_precision": support_precision,
        },
        "confidence": 0.9,
        "post_hoc_calibrated_confidence": 0.9,
        "routing_decision": routing_decision,
        "latency": 1,
        "human_label_if_any": 1,
        "philosophy_output_validation": {"ok": True},
    }


def _passing_release_gate_traces() -> list[dict[str, object]]:
    """Return traces that satisfy the current canonical gates."""

    return [
        _make_trace("q1", routing_decision="ship_candidate"),
        _make_trace("q2", routing_decision="ship_candidate"),
        _make_trace("q3", routing_decision="ship_candidate"),
        _make_trace("q4", routing_decision="escalate"),
    ]


def _companion_metrics_payload() -> dict[str, object]:
    """Return a valid companion RAGAS metrics payload."""

    return {
        "dataset_path": "evals/ragas/testset.jsonl",
        "sample_count": 16,
        "report_only": True,
        "metrics": {
            "faithfulness": 0.84,
            "answer_relevancy": 0.79,
            "context_precision": 0.88,
        },
    }


def _write_companion_metrics(
    tmp_path: Path,
    payload: dict[str, object] | None = None,
    *,
    relative_path: str = "artifacts/rag_eval/manual/metrics_summary.json",
) -> Path:
    """Write a companion metrics JSON artifact under the canonical artifact root."""

    companion_path = tmp_path / relative_path
    companion_path.parent.mkdir(parents=True, exist_ok=True)
    companion_path.write_text(
        json.dumps(payload or _companion_metrics_payload()),
        encoding="utf-8",
    )
    return companion_path


def test_runner_contract_imports_are_available() -> None:
    """The runner must point at the real repo hooks, not ad-hoc shims."""

    imports = load_pulseplate_imports()

    assert imports.scan_ai_agent_input is scan_ai_agent_input
    assert imports.validate_llm_output is validate_llm_output
    assert imports.retrieve_and_validate_rag is retrieve_and_validate_rag
    assert imports.prepare_insight_runtime is prepare_insight_runtime
    assert imports.generate_traced_insight is generate_traced_insight


def test_map_rag_chunk_matches_trace_contract() -> None:
    """RAGChunk fields must map into the trace schema deterministically."""

    chunk = RAGChunk(
        chunk_id="chunk-1",
        file="docs/contracts/RAG_CONTRACT.md",
        content="retrieval contract content",
        score=0.87,
        hop=2,
    )

    mapped = map_rag_chunk(chunk, rank=1, retriever="pulseplate")

    assert mapped == {
        "rank": 1,
        "doc_id": "chunk-1",
        "source_url": "docs/contracts/RAG_CONTRACT.md",
        "retrieval_score": 0.87,
        "doc_snippet": "retrieval contract content",
        "retriever": "pulseplate",
        "chunk_id": "chunk-1",
        "hop": 2,
    }


def test_map_orchestration_result_preserves_degraded_metadata() -> None:
    """Orchestration degraded-path metadata must survive adapter mapping."""

    result = RAGOrchestrationResult(
        chunks=[
            RAGChunk(
                chunk_id="chunk-7",
                file="core/rag/orchestration.py",
                content="retrieved content",
                score=0.61,
                hop=1,
            ),
        ],
        formatted_prompt="Context: ...",
        rag_actually_used=False,
        confidence=0.61,
        hops=3,
        latency_ms=144,
        warnings=["vector fallback used"],
        chunks_retrieved=4,
        chunks_filtered=3,
        recursive_executed=True,
        degraded_reason=RAGDegradedReason.ALL_CHUNKS_FILTERED,
    )

    retrieved, metadata = map_orchestration_result_to_retrieved(result)

    assert len(retrieved) == 1
    assert retrieved[0]["doc_id"] == "chunk-7"
    assert metadata["hops"] == 3
    assert metadata["latency_ms"] == 144
    assert metadata["warnings"] == ["vector fallback used"]
    assert metadata["chunks_retrieved"] == 4
    assert metadata["chunks_filtered"] == 3
    assert metadata["recursive_executed"] is True
    assert metadata["degraded_reason"] == "RAGDegradedReason.ALL_CHUNKS_FILTERED"


def test_philosophy_validator_integration_blocks_correctness() -> None:
    """Blocker findings must force the correctness proxy to fail closed."""

    answer = "We cure your condition and guarantee results."
    output_validation = validate_output_with_pulseplate(
        PulsePlateImports(validate_llm_output=validate_llm_output),
        answer,
    )

    trace = {
        "human_label_if_any": None,
        "faithfulness_metrics": {
            "evidence_exact_match": True,
            "support_precision": 1.0,
            "mean_nli_entailment": 1.0,
        },
        "philosophy_output_validation": output_validation,
    }

    assert output_validation["ok"] is False
    assert output_validation["blockers"]
    assert proxy_correctness(trace) == 0


def test_nli_entailment_score_uses_lexical_fallback_when_disabled(tmp_path: Path) -> None:
    """Disabled NLI must use lexical support instead of failing."""

    config = _config(tmp_path, enable_nli_model=False)
    contexts = ["PulsePlate canonical tiers are FREE PRO and VIP."]
    claim = "PulsePlate canonical tiers are FREE PRO and VIP."

    expected = lexical_support_score(claim, contexts)
    observed = nli_entailment_score(config, claim, contexts)

    assert observed == expected
    assert observed > 0.9


def test_apply_calibration_keeps_guard_blocks_intact() -> None:
    """Guard-blocked traces must not be rewritten into ordinary escalation."""

    traces = [
        {
            "routing_decision": "blocked_by_agent_input_guard",
            "confidence": 0.0,
            "faithfulness_metrics": {},
            "philosophy_output_validation": {},
            "human_label_if_any": None,
        },
        {
            "routing_decision": "pending_calibration",
            "confidence": 0.95,
            "faithfulness_metrics": {
                "evidence_exact_match": True,
                "support_precision": 1.0,
                "mean_nli_entailment": 1.0,
            },
            "philosophy_output_validation": {"ok": True},
            "human_label_if_any": 1,
        },
    ]

    calibration = apply_calibration(traces)

    assert calibration["temperature"] > 0
    assert traces[0]["routing_decision"] == "blocked_by_agent_input_guard"
    assert traces[1]["routing_decision"] == "ship_candidate"
    assert traces[1]["post_hoc_calibrated_confidence"] is not None


def test_expected_calibration_error_keeps_last_bin_bounded() -> None:
    """The terminal ECE bin must not double-count probabilities from lower bins."""

    labels = [0, 1]
    probabilities = [0.05, 0.95]

    observed = expected_calibration_error(labels, probabilities, n_bins=10)

    assert observed == pytest.approx(0.05)


def test_runner_smoke_writes_expected_artifacts(tmp_path: Path) -> None:
    """The cheap smoke path must finish and emit the canonical artifact pack."""

    project_root = tmp_path / "repo"
    (project_root / "docs").mkdir(parents=True)
    (project_root / "core").mkdir()
    (project_root / "app").mkdir()
    (project_root / "tests" / "guards").mkdir(parents=True)
    (project_root / "notebooks").mkdir()
    (project_root / "AGENTS.md").write_text("FREE PRO VIP", encoding="utf-8")
    (project_root / "RUNBOOK_AGENT.md").write_text(
        "retrieve_and_validate_rag",
        encoding="utf-8",
    )
    (project_root / "docs" / "tiers.md").write_text(
        "PulsePlate canonical tiers are FREE PRO and VIP.",
        encoding="utf-8",
    )
    (project_root / "core" / "runtime.py").write_text(
        "prepare insight runtime in core ai",
        encoding="utf-8",
    )
    (project_root / "app" / "guard.py").write_text(
        "screen input before provider calls",
        encoding="utf-8",
    )
    input_path = project_root / "input.jsonl"
    input_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "query_id": "q1",
                        "query_text": "What are the canonical tiers in PulsePlate?",
                        "gold_doc_ids": ["docs/tiers.md"],
                        "gold_answer": "FREE PRO and VIP",
                        "expected_claims": ["PulsePlate canonical tiers are FREE PRO and VIP."],
                        "evidence_quotes": ["FREE", "PRO", "VIP"],
                        "user_tier": "PRO",
                    },
                ),
            ],
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--project-root",
            str(project_root),
            "--input-path",
            str(input_path),
            "--artifact-root",
            str(project_root / "artifacts" / "rag_eval"),
            "--experiment-id",
            "smoke_eval",
            "--sample-size",
            "1",
            "--top-k",
            "5",
            "--retriever-mode",
            "local_tfidf",
            "--generator-mode",
            "extractive_stub",
        ],
    )

    run_dir = project_root / "artifacts" / "rag_eval" / "smoke_eval"
    assert exit_code == 0
    assert (run_dir / "traces.jsonl").is_file()
    assert (run_dir / "metrics_summary.json").is_file()
    assert (run_dir / "gate_report.md").is_file()
    assert (run_dir / "latest_executed.ipynb").is_file()


def test_chunk_text_preserves_overlap_for_long_paragraphs() -> None:
    """Long paragraphs must preserve overlap across adjacent windows."""

    long_text = "A" * 1500 + "B" * 1500

    chunks = chunk_text(long_text, max_chars=1200, overlap=160)

    assert len(chunks) >= 3
    assert chunks[0][-160:] == chunks[1][:160]


def test_sanitize_experiment_id_removes_path_tokens() -> None:
    """Artifact directory names must be reduced to safe slug-like identifiers."""

    assert sanitize_experiment_id("../../weekly strict") == "weekly_strict"


def test_build_config_rejects_paths_outside_project_root(tmp_path: Path) -> None:
    """Configured paths must stay inside the selected project root."""

    project_root = tmp_path / "repo"
    project_root.mkdir()
    (project_root / "artifacts").mkdir()
    outside_path = tmp_path / "outside.jsonl"

    args = argparse.Namespace(
        project_root=str(project_root),
        input_path=str(outside_path),
        artifact_root=str(project_root / "artifacts" / "rag_eval"),
        experiment_id="safe_run",
        sample_size="5",
        top_k="5",
        random_seed="42",
        retriever_mode="local_tfidf",
        generator_mode="extractive_stub",
        enable_nli_model=False,
        nli_model_name="roberta-large-mnli",
        notebook_path=str(project_root / "notebooks" / "pulseplate_rag_release_gates.ipynb"),
        require_pass=False,
        disallow_dataset_fallback=False,
        disallow_runtime_fallbacks=False,
    )

    with pytest.raises(ValueError, match="input_path"):
        build_config(args)


def test_build_config_uses_companion_metrics_env_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Companion artifact path may come from the canonical env fallback."""

    project_root = tmp_path / "repo"
    artifact_root = project_root / "artifacts" / "rag_eval"
    notebook_path = project_root / "notebooks" / "pulseplate_rag_release_gates.ipynb"
    input_path = project_root / "input.jsonl"
    companion_path = artifact_root / "manual" / "metrics_summary.json"

    artifact_root.mkdir(parents=True)
    notebook_path.parent.mkdir(parents=True)
    input_path.write_text("", encoding="utf-8")
    companion_path.parent.mkdir(parents=True, exist_ok=True)
    companion_path.write_text("{}", encoding="utf-8")

    monkeypatch.setenv(
        "PULSEPLATE_RAG_COMPANION_METRICS_JSON",
        str(companion_path),
    )

    args = argparse.Namespace(
        project_root=str(project_root),
        input_path=str(input_path),
        artifact_root=str(artifact_root),
        experiment_id="safe_run",
        sample_size="5",
        top_k="5",
        random_seed="42",
        retriever_mode="local_tfidf",
        generator_mode="extractive_stub",
        enable_nli_model=False,
        nli_model_name="roberta-large-mnli",
        notebook_path=str(notebook_path),
        require_pass=False,
        disallow_dataset_fallback=False,
        disallow_runtime_fallbacks=False,
        companion_metrics_json=None,
    )

    config = build_config(args)

    assert config.companion_metrics_json == companion_path.resolve()


def test_build_config_rejects_off_family_companion_metrics_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Companion artifact paths must stay inside the canonical rag_eval family."""

    project_root = tmp_path / "repo"
    artifact_root = project_root / "artifacts" / "rag_eval"
    notebook_path = project_root / "notebooks" / "pulseplate_rag_release_gates.ipynb"
    input_path = project_root / "input.jsonl"
    companion_path = project_root / "artifacts" / "tmp" / "metrics_summary.json"

    artifact_root.mkdir(parents=True)
    notebook_path.parent.mkdir(parents=True)
    input_path.write_text("", encoding="utf-8")
    companion_path.parent.mkdir(parents=True, exist_ok=True)
    companion_path.write_text("{}", encoding="utf-8")

    monkeypatch.setenv(
        "PULSEPLATE_RAG_COMPANION_METRICS_JSON",
        str(companion_path),
    )

    args = argparse.Namespace(
        project_root=str(project_root),
        input_path=str(input_path),
        artifact_root=str(artifact_root),
        experiment_id="safe_run",
        sample_size="5",
        top_k="5",
        random_seed="42",
        retriever_mode="local_tfidf",
        generator_mode="extractive_stub",
        enable_nli_model=False,
        nli_model_name="roberta-large-mnli",
        notebook_path=str(notebook_path),
        require_pass=False,
        disallow_dataset_fallback=False,
        disallow_runtime_fallbacks=False,
        companion_metrics_json=None,
    )

    with pytest.raises(ValueError, match="companion_metrics_json"):
        build_config(args)


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("sample_size", "0"),
        ("sample_size", "-1"),
        ("top_k", "0"),
        ("top_k", "-5"),
    ],
)
def test_build_config_rejects_non_positive_sampling_values(
    tmp_path: Path,
    field_name: str,
    field_value: str,
) -> None:
    """Sampling knobs must fail closed instead of silently disabling evaluation."""

    project_root = tmp_path / "repo"
    project_root.mkdir()
    (project_root / "artifacts").mkdir()
    inside_input = project_root / "input.jsonl"
    inside_input.write_text("", encoding="utf-8")

    args = argparse.Namespace(
        project_root=str(project_root),
        input_path=str(inside_input),
        artifact_root=str(project_root / "artifacts" / "rag_eval"),
        experiment_id="safe_run",
        sample_size="5",
        top_k="5",
        random_seed="42",
        retriever_mode="local_tfidf",
        generator_mode="extractive_stub",
        enable_nli_model=False,
        nli_model_name="roberta-large-mnli",
        notebook_path=str(project_root / "notebooks" / "pulseplate_rag_release_gates.ipynb"),
        require_pass=False,
        disallow_dataset_fallback=False,
        disallow_runtime_fallbacks=False,
    )
    setattr(args, field_name, field_value)

    with pytest.raises(ValueError, match=field_name):
        build_config(args)


def test_require_pass_returns_nonzero_for_no_go_dataset(tmp_path: Path) -> None:
    """Strict require-pass mode must fail the process on a NO-GO decision."""

    project_root = tmp_path / "repo"
    (project_root / "docs").mkdir(parents=True)
    (project_root / "core").mkdir()
    (project_root / "app").mkdir()
    (project_root / "tests" / "guards").mkdir(parents=True)
    (project_root / "notebooks").mkdir()
    (project_root / "artifacts").mkdir()
    (project_root / "AGENTS.md").write_text("FREE PRO VIP", encoding="utf-8")
    (project_root / "RUNBOOK_AGENT.md").write_text("retrieve_and_validate_rag", encoding="utf-8")
    (project_root / "docs" / "tiers.md").write_text(
        "PulsePlate canonical tiers are FREE PRO and VIP.",
        encoding="utf-8",
    )
    input_path = project_root / "input.jsonl"
    input_path.write_text(
        json.dumps(
            {
                "query_id": "q1",
                "query_text": "What are the canonical tiers in PulsePlate?",
                "gold_doc_ids": ["docs/does_not_exist.md"],
                "gold_answer": "FREE PRO and VIP",
                "expected_claims": ["PulsePlate canonical tiers are FREE PRO and VIP."],
                "evidence_quotes": ["FREE", "PRO", "VIP"],
                "user_tier": "PRO",
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--project-root",
            str(project_root),
            "--input-path",
            str(input_path),
            "--artifact-root",
            str(project_root / "artifacts" / "rag_eval"),
            "--experiment-id",
            "strict_no_go",
            "--sample-size",
            "1",
            "--top-k",
            "5",
            "--retriever-mode",
            "local_tfidf",
            "--generator-mode",
            "extractive_stub",
            "--require-pass",
        ],
    )

    assert exit_code == 2


def test_retrieve_marks_strict_violation_when_pulseplate_falls_back(tmp_path: Path) -> None:
    """Strict runtime lanes must record retriever degradations even if they continue locally."""

    state = EvalRuntimeState(
        config=EvalConfig(
            project_root=tmp_path,
            input_path=tmp_path / "input.jsonl",
            artifact_root=tmp_path / "artifacts" / "rag_eval",
            experiment_id="strict_retriever",
            sample_size=1,
            top_k=5,
            random_seed=42,
            retriever_mode="pulseplate",
            generator_mode="extractive_stub",
            enable_nli_model=False,
            nli_model_name="roberta-large-mnli",
            notebook_path=tmp_path / "notebooks" / "pulseplate_rag_release_gates.ipynb",
            require_pass=False,
            allow_dataset_fallback=True,
            allow_runtime_fallbacks=False,
        ),
        pulseplate_imports=PulsePlateImports(),
    )

    retrieved, metadata = asyncio.run(
        retrieve(
            state,
            "PulsePlate tiers",
            top_k=5,
            subject_id=None,
        )
    )

    assert retrieved == []
    assert metadata["max_supported_top_k"] == 5
    assert state.strict_violations
    assert state.strict_violations[0].startswith("pulseplate_retriever_fallback:")


def test_generate_answer_marks_strict_violation_when_runtime_falls_back(tmp_path: Path) -> None:
    """Strict runtime lanes must record generator degradations."""

    state = EvalRuntimeState(
        config=EvalConfig(
            project_root=tmp_path,
            input_path=tmp_path / "input.jsonl",
            artifact_root=tmp_path / "artifacts" / "rag_eval",
            experiment_id="strict_generator",
            sample_size=1,
            top_k=5,
            random_seed=42,
            retriever_mode="local_tfidf",
            generator_mode="pulseplate_runtime",
            enable_nli_model=False,
            nli_model_name="roberta-large-mnli",
            notebook_path=tmp_path / "notebooks" / "pulseplate_rag_release_gates.ipynb",
            require_pass=False,
            allow_dataset_fallback=True,
            allow_runtime_fallbacks=False,
        ),
        pulseplate_imports=PulsePlateImports(),
    )

    answer, confidence, metadata = asyncio.run(
        generate_answer(
            state,
            "PulsePlate tiers",
            [
                {
                    "doc_id": "docs/tiers.md",
                    "source_url": "docs/tiers.md",
                    "doc_snippet": "FREE PRO VIP",
                }
            ],
            user_tier="PRO",
            subject_id=None,
        )
    )

    assert "PulsePlate" in answer
    assert confidence > 0
    assert metadata["generator"] == "extractive_stub"
    assert state.strict_violations
    assert state.strict_violations[0].startswith("pulseplate_runtime_generator_fallback:")


def test_write_artifacts_returns_machine_stable_flat_export_path(tmp_path: Path) -> None:
    """Artifact metadata must expose a path, not a prose status blob."""

    run_dir = tmp_path / "artifacts" / "rag_eval" / "stable_export"
    run_dir.mkdir(parents=True)
    template_dir = tmp_path / "notebooks"
    template_dir.mkdir(parents=True)
    template_path = template_dir / "pulseplate_rag_release_gates.ipynb"
    template_path.write_text(
        json.dumps(
            {
                "cells": [],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            },
        ),
        encoding="utf-8",
    )
    traces = [
        {
            "trace_id": "trace-1",
            "timestamp": "2026-04-20T00:00:00+00:00",
            "experiment_id": "stable_export",
            "query_id": "q1",
            "query_text": "PulsePlate tiers",
            "top_k_retrieved": [{"doc_id": "docs/tiers.md", "source_url": "docs/tiers.md"}],
            "retrieval_metrics": {
                "recall_at_3": 1.0,
                "recall_at_10": 1.0,
                "recall_at_50": 1.0,
                "recall_at_effective_k": 1.0,
                "mrr_at_10": 1.0,
                "ndcg_at_10": 1.0,
            },
            "faithfulness_metrics": {
                "evidence_exact_match": True,
                "mean_nli_entailment": 1.0,
                "support_precision": 1.0,
            },
            "confidence": 0.9,
            "post_hoc_calibrated_confidence": 0.9,
            "routing_decision": "ship_candidate",
            "latency": 1,
            "human_label_if_any": 1,
        }
    ]
    metrics_summary = {
        "experiment_id": "stable_export",
        "release_decision": "PASS",
        "timestamp": "2026-04-20T00:00:00+00:00",
        "git_sha": "deadbeef",
        "sample_size": 1,
        "retriever_mode": "local_tfidf",
        "generator_mode": "extractive_stub",
        "dataset_path_used": "data/evals/pulseplate_rag_eval_sample.jsonl",
        "dataset_fallback_used": False,
        "runtime_warnings": [],
        "strict_violations": [],
        "retrieval": {"recall_at_effective_k": 1.0},
        "faithfulness": {},
        "calibration": {},
        "routing": {},
        "gate_checks": {},
    }

    artifacts = write_artifacts(
        run_dir,
        traces,
        metrics_summary,
        template_notebook_path=template_path,
    )

    assert artifacts["parquet_or_csv"].endswith((".parquet", ".csv"))


@pytest.mark.asyncio
async def test_missing_agent_input_guard_fails_closed_in_strict_mode(tmp_path: Path) -> None:
    """Strict mode must not silently bypass the shared AI input guard."""

    state = EvalRuntimeState(
        config=EvalConfig(
            project_root=tmp_path,
            input_path=tmp_path / "data" / "eval.jsonl",
            artifact_root=tmp_path / "artifacts" / "rag_eval",
            experiment_id="strict_guard_gap",
            sample_size=1,
            top_k=5,
            random_seed=42,
            retriever_mode="local_tfidf",
            generator_mode="extractive_stub",
            enable_nli_model=False,
            nli_model_name="roberta-large-mnli",
            notebook_path=tmp_path / "notebooks" / "pulseplate_rag_release_gates.ipynb",
            require_pass=True,
            allow_dataset_fallback=True,
            allow_runtime_fallbacks=False,
        ),
        pulseplate_imports=PulsePlateImports(),
    )
    row = EvalRow(
        query_id="q1",
        query_text="How does PulsePlate tiering work?",
        gold_doc_ids=["docs/tiers.md"],
        gold_answer="PulsePlate has tiers.",
        expected_claims=[],
        evidence_quotes=[],
        user_tier="PRO",
        subject_id=1,
        human_label_if_any=1,
    )

    trace = await evaluate_one(state, row)

    assert trace["routing_decision"] == "blocked_by_agent_input_guard"
    assert "agent_input_guard_unavailable:scan_ai_agent_input_missing" in state.strict_violations


@pytest.mark.asyncio
async def test_missing_philosophy_validator_records_strict_violation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strict mode must record missing philosophy validation as a blocker."""

    async def fake_generate_answer(
        *args: object, **kwargs: object
    ) -> tuple[str, float, dict[str, object]]:
        return "PulsePlate answer backed by evidence.", 0.91, {"generator": "stub"}

    def fake_scan(_: str) -> object:
        return type("Guard", (), {"is_safe": True, "threats": ()})()

    state = EvalRuntimeState(
        config=EvalConfig(
            project_root=tmp_path,
            input_path=tmp_path / "data" / "eval.jsonl",
            artifact_root=tmp_path / "artifacts" / "rag_eval",
            experiment_id="strict_validator_gap",
            sample_size=1,
            top_k=5,
            random_seed=42,
            retriever_mode="local_tfidf",
            generator_mode="extractive_stub",
            enable_nli_model=False,
            nli_model_name="roberta-large-mnli",
            notebook_path=tmp_path / "notebooks" / "pulseplate_rag_release_gates.ipynb",
            require_pass=True,
            allow_dataset_fallback=True,
            allow_runtime_fallbacks=False,
        ),
        pulseplate_imports=PulsePlateImports(scan_ai_agent_input=fake_scan),
    )
    row = EvalRow(
        query_id="q2",
        query_text="Summarize PulsePlate tiering.",
        gold_doc_ids=["docs/tiers.md"],
        gold_answer="PulsePlate has tiers.",
        expected_claims=[],
        evidence_quotes=[],
        user_tier="PRO",
        subject_id=1,
        human_label_if_any=1,
    )

    monkeypatch.setattr(
        runner,
        "retrieve",
        AsyncMock(
            return_value=(
                [
                    {
                        "doc_id": "docs/tiers.md",
                        "source_url": "docs/tiers.md",
                        "doc_snippet": "tiers",
                    }
                ],
                {"max_supported_top_k": 5},
            )
        ),
    )
    monkeypatch.setattr(runner, "generate_answer", fake_generate_answer)
    monkeypatch.setattr(
        runner,
        "evaluate_faithfulness",
        Mock(
            return_value={
                "extracted_claim_spans": [],
                "per_span_entailment_score": [],
                "support_flags": [],
                "evidence_exact_match": True,
                "mean_nli_entailment": 1.0,
                "support_precision": 1.0,
            }
        ),
    )

    trace = await evaluate_one(state, row)

    assert trace["philosophy_output_validation"]["ok"] is False
    assert "philosophy_validator_unavailable:validate_llm_output_missing" in state.strict_violations


def test_notebook_parity_uses_emitted_artifact_from_template(tmp_path: Path) -> None:
    """The emitted notebook artifact must derive from the tracked template notebook."""

    template_dir = tmp_path / "notebooks"
    template_dir.mkdir(parents=True)
    template_path = template_dir / "pulseplate_rag_release_gates.ipynb"
    template_notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "ROUTING_CONFIDENCE_THRESHOLD=0.65\n",
                    "SUPPORT_ENTAILMENT_THRESHOLD=0.50\n",
                    "recall_at_effective_k\n",
                    "mean_nli_entailment\n",
                    "# template sentinel\n",
                ],
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    template_path.write_text(json.dumps(template_notebook), encoding="utf-8")

    run_dir = tmp_path / "artifacts" / "rag_eval" / "parity"
    run_dir.mkdir(parents=True)
    metrics_summary = {
        "experiment_id": "parity",
        "release_decision": "PASS",
        "retriever_mode": "local_tfidf",
        "generator_mode": "extractive_stub",
        "dataset_path_used": "data/evals/pulseplate_rag_eval_sample.jsonl",
    }

    emitted = write_summary_notebook(
        run_dir,
        metrics_summary,
        "gate report",
        template_notebook_path=template_path,
    )
    emitted_text = emitted.read_text(encoding="utf-8")

    assert "# template sentinel" in emitted_text
    assert "ROUTING_CONFIDENCE_THRESHOLD=0.65" in emitted_text
    assert "SUPPORT_ENTAILMENT_THRESHOLD=0.50" in emitted_text
    assert "recall_at_effective_k" in emitted_text
    assert "mean_nli_entailment" in emitted_text
    assert "::chunk_" not in emitted_text
    assert "recall@50" not in emitted_text
    assert "mean_entailment" not in emitted_text


def test_no_companion_json_keeps_legacy_release_decision_behavior(tmp_path: Path) -> None:
    """Missing companion input must preserve legacy release-gate behavior."""

    state = _make_release_gate_state(tmp_path, experiment_id="legacy_no_companion")
    traces = _passing_release_gate_traces()

    baseline_summary, gate_checks, release_decision = runner.build_metrics_summary(
        state,
        traces,
        {"ece": 0.05},
        dataset_fallback_used=False,
        dataset_path_used="data/evals/pulseplate_rag_eval_sample.jsonl",
    )

    assert release_decision == "PASS"
    assert all(gate_checks.values()) is True
    assert "companion_metrics" not in baseline_summary


def test_valid_companion_json_adds_informational_metrics_without_affecting_release_decision(
    tmp_path: Path,
) -> None:
    """Valid companion metrics must stay informational and keep gate outcomes unchanged."""

    state = _make_release_gate_state(tmp_path, experiment_id="with_companion")
    traces = _passing_release_gate_traces()
    dataset_path = "data/evals/pulseplate_rag_eval_sample.jsonl"
    calibration_metrics = {"ece": 0.05}

    baseline_summary, _, baseline_release_decision = runner.build_metrics_summary(
        state,
        traces,
        calibration_metrics,
        dataset_fallback_used=False,
        dataset_path_used=dataset_path,
    )
    companion_path = _write_companion_metrics(tmp_path)
    companion_metrics = runner._load_companion_metrics(companion_path)

    metrics_summary, gate_checks, release_decision = runner.build_metrics_summary(
        state,
        traces,
        calibration_metrics,
        dataset_fallback_used=False,
        dataset_path_used=dataset_path,
        companion_metrics=companion_metrics,
    )
    gate_report = runner.build_gate_report_markdown(metrics_summary)

    assert baseline_release_decision == "PASS"
    assert release_decision == baseline_release_decision
    assert gate_checks == baseline_summary["gate_checks"]
    assert metrics_summary["companion_metrics"] == {
        "ragas": {
            "source_path": str(companion_path.resolve()),
            "dataset_path": "evals/ragas/testset.jsonl",
            "sample_count": 16,
            "report_only": True,
            "metrics": {
                "faithfulness": 0.84,
                "answer_relevancy": 0.79,
                "context_precision": 0.88,
            },
        }
    }
    assert "## Companion RAGAS metrics" in gate_report
    assert "`faithfulness` | `0.84`" in gate_report
    assert "`answer_relevancy` | `0.79`" in gate_report
    assert "`context_precision` | `0.88`" in gate_report


@pytest.mark.parametrize(
    ("payload", "error_pattern"),
    [
        (None, "Companion metrics JSON not found"),
        (
            {
                "dataset_path": "evals/ragas/testset.jsonl",
                "sample_count": 16,
                "report_only": True,
            },
            "must contain exactly: dataset_path, sample_count, report_only, metrics",
        ),
        (
            {
                "dataset_path": "evals/ragas/testset.jsonl",
                "sample_count": 16,
                "report_only": True,
                "metrics": {
                    "faithfulness": 0.84,
                    "answer_relevancy": float("nan"),
                    "context_precision": 0.88,
                },
            },
            "must be finite",
        ),
    ],
)
def test_malformed_companion_metrics_fail_closed(
    tmp_path: Path,
    payload: dict[str, object] | None,
    error_pattern: str,
) -> None:
    """Malformed companion artifacts must fail closed at the runner boundary."""

    companion_path = tmp_path / "artifacts" / "rag_eval" / "manual" / "metrics_summary.json"
    if payload is not None:
        companion_path.parent.mkdir(parents=True, exist_ok=True)
        companion_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises((FileNotFoundError, RuntimeError), match=error_pattern):
        runner._load_companion_metrics(companion_path)


def test_threshold_results_ordering_and_escalation_corridor_are_deterministic(
    tmp_path: Path,
) -> None:
    """Threshold rows must keep canonical order and stable corridor serialization."""

    state = _make_release_gate_state(tmp_path, experiment_id="threshold_ordering")
    metrics_summary, _, release_decision = runner.build_metrics_summary(
        state,
        _passing_release_gate_traces(),
        {"ece": 0.05},
        dataset_fallback_used=False,
        dataset_path_used="data/evals/pulseplate_rag_eval_sample.jsonl",
    )
    threshold_results = metrics_summary["threshold_results"]
    gate_report = runner.build_gate_report_markdown(metrics_summary)

    assert release_decision == "PASS"
    assert [row["gate_id"] for row in threshold_results] == [
        "gate_a_recall_at_effective_k",
        "gate_b1_evidence_exact_match",
        "gate_b2_mean_nli_entailment",
        "gate_b3_support_precision",
        "gate_c1_ece",
        "gate_c2_escalation_corridor",
        "gate_d1_no_runtime_mode_fallbacks",
    ]
    assert threshold_results[5] == {
        "gate_id": "gate_c2_escalation_corridor",
        "metric_key": "escalation_rate",
        "threshold_key": "escalation_corridor",
        "value": 0.25,
        "target": {"min": 0.1, "max": 0.25},
        "comparison": "between_inclusive",
        "passed": True,
    }
    assert "`gate_c2_escalation_corridor` | `escalation_rate` | `0.25` | `0.1..0.25`" in gate_report


def test_step_summary_includes_threshold_results_and_optional_companion_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub step summary must include threshold rows and optional companion metrics."""

    summary_path = tmp_path / "github_step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    state = _make_release_gate_state(tmp_path, experiment_id="step_summary")
    companion_metrics = runner._load_companion_metrics(_write_companion_metrics(tmp_path))
    metrics_summary, _, _ = runner.build_metrics_summary(
        state,
        _passing_release_gate_traces(),
        {"ece": 0.05},
        dataset_fallback_used=False,
        dataset_path_used="data/evals/pulseplate_rag_eval_sample.jsonl",
        companion_metrics=companion_metrics,
    )

    runner._write_github_step_summary(
        metrics_summary,
        {
            "gate_report": "artifacts/rag_eval/step_summary/gate_report.md",
            "metrics_summary": "artifacts/rag_eval/step_summary/metrics_summary.json",
            "traces_jsonl": "artifacts/rag_eval/step_summary/traces.jsonl",
        },
    )
    summary_text = summary_path.read_text(encoding="utf-8")

    assert "## PulsePlate RAG Release Gates" in summary_text
    assert "### Threshold results" in summary_text
    assert (
        "`gate_c2_escalation_corridor` | `0.25` | `0.1..0.25` | `between_inclusive` | `True`"
        in summary_text
    )
    assert "### Companion RAGAS metrics" in summary_text
    assert "- `faithfulness`: `0.84`" in summary_text
    assert "- `answer_relevancy`: `0.79`" in summary_text
    assert "- `context_precision`: `0.88`" in summary_text
