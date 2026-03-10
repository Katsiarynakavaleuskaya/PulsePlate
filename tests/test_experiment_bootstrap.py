"""Tests for deterministic experiment bootstrap packets."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.orchestration.context_pack import REPO_ROOT
from scripts.orchestration.experiment_bootstrap import (
    _resolve_output_path,
    build_experiment_packet,
    main,
    validate_mutable_candidate_surface,
)


def test_build_experiment_packet_is_deterministic() -> None:
    """Identical inputs should produce identical packets and ids."""

    kwargs = {
        "decision_question": "Benchmark RAG reliability for contradiction reduction",
        "task_class": "Experimentation",
        "mutable_paths": ["core/rag/vector_rag.py", "core/insight/pipeline.py"],
        "oracle_commands": ["python scripts/benchmarks/philosophical_runtime_benchmark.py"],
        "metrics": ["val_bpb", "latency_p95_ms"],
        "negative_controls": ["oracle file unchanged", "no forbidden path mutation"],
        "promotion_target": "pr_packet",
    }

    first = build_experiment_packet(**kwargs)
    second = build_experiment_packet(**kwargs)

    assert first == second
    assert first["experiment_id"].startswith("exp-")
    assert first["domain"] == "ml"
    assert "data-scientist-agent" in first["recommended_agents"]
    assert "ml-engineer-agent" in first["recommended_agents"]
    assert "pulseplate-workflow" in first["recommended_skills"]
    assert "pulseplate-gates" in first["recommended_skills"]
    assert "docs-sync" in first["recommended_skills"]


def test_build_experiment_packet_adds_cv_agent_for_cv_intent() -> None:
    """CV-oriented experiment text should add cv-agent to the advisory stack."""

    packet = build_experiment_packet(
        decision_question="Evaluate CV photo pipeline confidence on food image reliability",
        task_class="Experimentation",
        mutable_paths=["docs/prompts/cv/program.md"],
        oracle_commands=["pytest -q tests/test_cv_contract.py"],
        metrics=["confidence_error"],
        negative_controls=["oracle file unchanged", "no hidden memory"],
        promotion_target="audit_artifact",
    )

    assert "cv-agent" in packet["recommended_agents"]
    assert "ml-engineer-agent" in packet["recommended_agents"]


def test_validate_mutable_candidate_surface_rejects_forbidden_path() -> None:
    """Forbidden mutable surfaces should fail closed."""

    try:
        validate_mutable_candidate_surface(["docs/orchestration/workflow.md"])
    except ValueError as exc:
        assert "Invalid paths" in str(exc)
    else:
        raise AssertionError("Expected ValueError for forbidden mutable surface")


def test_validate_mutable_candidate_surface_rejects_traversal_escape() -> None:
    """Traversal segments must not bypass the mutable-surface allowlist."""

    try:
        validate_mutable_candidate_surface(["core/rag/../../docs/orchestration/workflow.md"])
    except ValueError as exc:
        assert "docs/orchestration/workflow.md" in str(exc)
    else:
        raise AssertionError("Expected ValueError for traversal escape")


def test_validate_mutable_candidate_surface_normalizes_safe_relative_paths() -> None:
    """Benign traversal inside an allowed root should normalize to the allowed file."""

    normalized = validate_mutable_candidate_surface(["core/rag/../rag/vector_rag.py"])

    assert normalized == ["core/rag/vector_rag.py"]


def test_main_rejects_missing_oracles(capsys) -> None:
    """CLI should fail cleanly when no immutable oracle command is provided."""

    exit_code = main(
        [
            "--decision-question",
            "Benchmark RAG reliability",
            "--mutable-path",
            "core/rag/vector_rag.py",
            "--metric",
            "val_bpb",
            "--negative-control",
            "oracle file unchanged",
            "--negative-control",
            "no forbidden path mutation",
            "--promotion-target",
            "pr_packet",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL: At least one --oracle-command is required." in captured.out


def test_main_writes_relative_output_inside_repo(monkeypatch, capsys) -> None:
    """CLI should write relative output and report the repo-relative artifact path."""

    relative_output = Path("tmp/experiment-packet.json")
    repo_output = (REPO_ROOT / relative_output).resolve()
    if repo_output.exists():
        repo_output.unlink()

    packet = {
        "schema_version": "1.0",
        "experiment_id": "exp-testpacket",
        "decision_question": "Test experiment bootstrap write",
        "task_class": "Experimentation",
        "domain": "ml",
        "mutable_candidate_surface": ["core/rag/vector_rag.py"],
        "immutable_oracles": [
            {"command": "pytest -q tests/test_rag.py", "expected_signal": "must pass"}
        ],
        "budgets": {
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 3,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 2,
            "stop_condition": "stop",
        },
        "metrics": {"primary": "val_bpb", "secondary": []},
        "negative_controls": ["oracle file unchanged", "no forbidden path mutation"],
        "promotion_target": "pr_packet",
        "primary_agent": "agent-coordinator",
        "reviewer": "architecture-specialist",
        "recommended_agents": ["agent-coordinator", "data-scientist-agent"],
        "recommended_skills": ["pulseplate-workflow", "pulseplate-gates"],
        "skill_routing": {
            "policy_version": "2026-03-08",
            "selection_mode": "deterministic-weighted",
            "recommended": [{"skill": "pulseplate-workflow", "score": 100}],
            "blocked": [],
        },
        "routing_context": {
            "cluster": "ml",
            "domain": "ml",
            "task_type": "Experimentation",
            "primary": "ai-innovation-specialist",
            "secondary": "rag-systems-agent",
            "reviewer": "architecture-specialist",
        },
    }
    monkeypatch.setattr(
        "scripts.orchestration.experiment_bootstrap.build_experiment_packet",
        lambda **_: packet,
    )

    try:
        exit_code = main(
            [
                "--decision-question",
                "ignored",
                "--mutable-path",
                "core/rag/vector_rag.py",
                "--oracle-command",
                "pytest -q tests/test_rag.py",
                "--metric",
                "val_bpb",
                "--negative-control",
                "oracle file unchanged",
                "--negative-control",
                "no forbidden path mutation",
                "--promotion-target",
                "pr_packet",
                "--output",
                str(relative_output),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        written = json.loads(repo_output.read_text(encoding="utf-8"))
        assert written["experiment_id"] == "exp-testpacket"
        assert json.loads(captured.out)["output"] == relative_output.as_posix()
    finally:
        if repo_output.exists():
            repo_output.unlink()


def test_resolve_output_path_rejects_outside_repo(tmp_path) -> None:
    """Output path must remain inside the repository root."""

    outside = tmp_path / "experiment-packet.json"
    try:
        _resolve_output_path(str(outside), "exp-ignored")
    except ValueError as exc:
        assert "--output must stay within the repository root" in str(exc)
    else:
        raise AssertionError("Expected ValueError for output outside repo")
