"""Tests for the PulsePlate RAG release-gates runner."""

from __future__ import annotations

import json
from pathlib import Path

from core.ai import prepare_insight_runtime
from core.insight.philosophy_validator import validate_llm_output
from core.rag.contracts import RAGChunk, RAGDegradedReason
from core.rag.orchestration import RAGOrchestrationResult, retrieve_and_validate_rag
from app.security.agent_input_guard import scan_ai_agent_input
from app.services.insight_runtime import generate_traced_insight
from scripts.evals.run_rag_release_gates import (
    EvalConfig,
    PulsePlateImports,
    apply_calibration,
    lexical_support_score,
    load_pulseplate_imports,
    main,
    map_orchestration_result_to_retrieved,
    map_rag_chunk,
    nli_entailment_score,
    proxy_correctness,
    validate_output_with_pulseplate,
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
