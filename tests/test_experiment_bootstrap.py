"""Tests for deterministic experiment bootstrap packets."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.orchestration.experiment_bootstrap as experiment_bootstrap
from scripts.orchestration.experiment_bootstrap import (
    _resolve_output_path,
    build_experiment_packet,
    compute_experiment_id,
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
    assert first["metrics"]["baseline_reference"] == "current-main"
    assert first["metrics"]["acceptance_threshold"] == "strict_improvement"


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


def test_build_experiment_packet_does_not_match_cv_hint_on_substrings() -> None:
    """Substring noise like 'cve' must not force the cv advisory path."""

    packet = build_experiment_packet(
        decision_question="Evaluate drag coefficient with cve notes",
        task_class="Experimentation",
        mutable_paths=["core/rag/vector_rag.py"],
        oracle_commands=["pytest -q tests/test_rag_contracts.py"],
        metrics=["reliability_score"],
        negative_controls=["oracle file unchanged", "no hidden memory"],
        promotion_target="audit_artifact",
    )

    assert "cv-agent" not in packet["recommended_agents"]


def test_validate_mutable_candidate_surface_rejects_forbidden_path() -> None:
    """Forbidden mutable surfaces should fail closed."""

    with pytest.raises(ValueError, match="Invalid paths"):
        validate_mutable_candidate_surface(["docs/orchestration/workflow.md"])


def test_validate_mutable_candidate_surface_rejects_traversal_escape() -> None:
    """Traversal segments must not bypass the mutable-surface allowlist."""

    with pytest.raises(ValueError, match="docs/orchestration/workflow.md"):
        validate_mutable_candidate_surface(["core/rag/../../docs/orchestration/workflow.md"])


def test_validate_mutable_candidate_surface_normalizes_safe_relative_paths() -> None:
    """Benign traversal inside an allowed root should normalize to the allowed file."""

    normalized = validate_mutable_candidate_surface(["core/rag/../rag/vector_rag.py"])

    assert normalized == ["core/rag/vector_rag.py"]


def test_main_rejects_missing_oracles(capsys: pytest.CaptureFixture[str]) -> None:
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


def test_main_writes_relative_output_inside_repo(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """CLI should write output under the experiment artifact directory."""

    repo_root = tmp_path.resolve()
    experiment_dir = (repo_root / "artifacts" / "orchestration" / "experiments").resolve()
    monkeypatch.setattr(experiment_bootstrap, "REPO_ROOT", repo_root)
    monkeypatch.setattr(experiment_bootstrap, "EXPERIMENT_PACKET_DIR", experiment_dir)

    relative_output = Path("tmp/experiment-packet.json")
    repo_output = (experiment_bootstrap.EXPERIMENT_PACKET_DIR / relative_output).resolve()

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
        "metrics": {
            "primary": "val_bpb",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
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
    assert (
        json.loads(captured.out)["output"]
        == (Path("artifacts/orchestration/experiments") / relative_output).as_posix()
    )


def test_resolve_output_path_rejects_outside_repo(tmp_path: Path) -> None:
    """Output path must remain inside the experiment artifact directory."""

    outside = tmp_path / "experiment-packet.json"
    with pytest.raises(
        ValueError,
        match="--output must stay within artifacts/orchestration/experiments",
    ):
        _resolve_output_path(str(outside), "exp-ignored")


def test_build_experiment_packet_rejects_budget_overrides_above_hard_caps() -> None:
    """Budget overrides above protocol caps must fail closed."""

    with pytest.raises(ValueError, match="wall_clock_seconds must be <= 600"):
        build_experiment_packet(
            decision_question="Benchmark RAG reliability for contradiction reduction",
            task_class="Experimentation",
            mutable_paths=["core/rag/vector_rag.py"],
            oracle_commands=["python scripts/benchmarks/philosophical_runtime_benchmark.py"],
            metrics=["val_bpb"],
            negative_controls=["oracle file unchanged", "no forbidden path mutation"],
            promotion_target="pr_packet",
            budgets={"wall_clock_seconds": 601},
        )


def test_build_experiment_packet_rejects_unsupported_budget_keys() -> None:
    """Unknown budget override keys must fail closed before packet generation."""

    with pytest.raises(ValueError, match="Unsupported budget keys: gpu_budget"):
        build_experiment_packet(
            decision_question="Benchmark RAG reliability for contradiction reduction",
            task_class="Experimentation",
            mutable_paths=["core/rag/vector_rag.py"],
            oracle_commands=["python scripts/benchmarks/philosophical_runtime_benchmark.py"],
            metrics=["val_bpb"],
            negative_controls=["oracle file unchanged", "no forbidden path mutation"],
            promotion_target="pr_packet",
            budgets={"gpu_budget": 1},
        )


def test_compute_experiment_id_changes_with_budgets_and_stop_condition() -> None:
    """Execution constraints must participate in deterministic experiment ids."""

    base_kwargs = {
        "decision_question": "Benchmark RAG reliability for contradiction reduction",
        "task_class": "Experimentation",
        "mutable_paths": ["core/rag/vector_rag.py"],
        "immutable_oracles": [
            {
                "command": "python scripts/benchmarks/philosophical_runtime_benchmark.py",
                "expected_signal": "must pass",
            }
        ],
        "metrics": {
            "primary": "val_bpb",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": ["oracle file unchanged", "no forbidden path mutation"],
        "promotion_target": "pr_packet",
    }

    default_id = compute_experiment_id(
        budgets={
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 3,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 2,
        },
        stop_condition="Stop on timeout.",
        **base_kwargs,
    )
    budget_variant_id = compute_experiment_id(
        budgets={
            "wall_clock_seconds": 301,
            "retry_budget": 1,
            "max_changed_files": 3,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 2,
        },
        stop_condition="Stop on timeout.",
        **base_kwargs,
    )
    stop_variant_id = compute_experiment_id(
        budgets={
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 3,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 2,
        },
        stop_condition="Stop on unchanged result.",
        **base_kwargs,
    )

    assert default_id != budget_variant_id
    assert default_id != stop_variant_id


def test_main_fails_cleanly_on_output_write_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Write failures inside the artifact tree must respect the FAIL/exit=1 contract."""

    repo_root = tmp_path.resolve()
    experiment_dir = (repo_root / "artifacts" / "orchestration" / "experiments").resolve()
    experiment_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(experiment_bootstrap, "REPO_ROOT", repo_root)
    monkeypatch.setattr(experiment_bootstrap, "EXPERIMENT_PACKET_DIR", experiment_dir)

    output_dir = experiment_dir / "occupied"
    output_dir.mkdir()

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
            "occupied",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL: unable to write experiment packet:" in captured.out
