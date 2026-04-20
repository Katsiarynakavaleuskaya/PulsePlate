"""Tests for the PulsePlate RAG release-gates runner."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import pytest

from core.ai import prepare_insight_runtime
from core.insight.philosophy_validator import validate_llm_output
from core.rag.contracts import RAGChunk, RAGDegradedReason
from core.rag.orchestration import RAGOrchestrationResult, retrieve_and_validate_rag
from app.security.agent_input_guard import scan_ai_agent_input
from app.services.insight_runtime import generate_traced_insight
from scripts.evals.run_rag_release_gates import (
    EvalConfig,
    EvalRuntimeState,
    PulsePlateImports,
    apply_calibration,
    build_config,
    chunk_text,
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

    artifacts = write_artifacts(run_dir, traces, metrics_summary)

    assert artifacts["parquet_or_csv"].endswith((".parquet", ".csv"))


def test_notebook_parity_uses_runner_thresholds_and_metric_keys() -> None:
    """Notebook and runner must not drift on critical thresholds and schema keys."""

    notebook_text = Path("notebooks/pulseplate_rag_release_gates.ipynb").read_text(encoding="utf-8")

    assert "ROUTING_CONFIDENCE_THRESHOLD" in notebook_text
    assert '\\"0.65\\"' in notebook_text
    assert "SUPPORT_ENTAILMENT_THRESHOLD" in notebook_text
    assert '\\"0.50\\"' in notebook_text
    assert "recall_at_effective_k" in notebook_text
    assert "mean_nli_entailment" in notebook_text
    assert "::chunk_" not in notebook_text
    assert "recall@50" not in notebook_text
    assert "mean_entailment" not in notebook_text
