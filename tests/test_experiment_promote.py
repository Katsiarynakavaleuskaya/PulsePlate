"""Deterministic tests for governed experiment promotion tooling."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

import scripts.orchestration.context_pack as context_pack
import scripts.orchestration.experiment_contract as experiment_contract
import scripts.orchestration.experiment_promote as experiment_promote


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    git_binary = shutil.which("git")
    if not git_binary:
        raise AssertionError("git binary is required for experiment promotion tests.")
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.run(
        [git_binary, *args],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "core" / "rag").mkdir(parents=True)
    (repo / "docs" / "roadmap").mkdir(parents=True)
    (repo / "docs" / "memory").mkdir(parents=True)
    (repo / "docs" / "orchestration").mkdir(parents=True)
    (repo / "docs" / "audit").mkdir(parents=True)
    (repo / "core" / "rag" / "allowed.py").write_text(
        "def candidate_value() -> int:\n    return 2\n",
        encoding="utf-8",
    )
    (repo / "docs" / "roadmap" / "BACKLOG_LEDGER.md").write_text(
        "# Backlog Ledger\n\n<!-- EXPERIMENT_BACKLOG_ENTRIES:INSERT BELOW -->\n",
        encoding="utf-8",
    )
    (repo / "docs" / "memory" / "index.md").write_text(
        "# Project Memory\n\n## Capsules\n\n<!-- EXPERIMENT_MEMORY_CAPSULES:INSERT BELOW -->\n",
        encoding="utf-8",
    )
    (repo / "docs" / "orchestration" / "AGENT_EXPERIMENTATION_PROTOCOL.md").write_text(
        "# Experiment Protocol\n",
        encoding="utf-8",
    )
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate Experiment Runner")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    return repo


def _configure_repo(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    promotion_dir = repo / "artifacts" / "orchestration" / "experiments" / "promotions"
    monkeypatch.setattr(context_pack, "REPO_ROOT", repo)
    monkeypatch.setattr(experiment_contract, "REPO_ROOT", repo)
    monkeypatch.setattr(experiment_promote, "REPO_ROOT", repo)
    monkeypatch.setattr(experiment_promote, "PROMOTION_ARTIFACT_DIR", promotion_dir)
    monkeypatch.setattr(
        experiment_promote,
        "PR_PACKET_DIR",
        repo / "docs" / "orchestration" / "experiment_pr_packets",
    )
    monkeypatch.setattr(
        experiment_promote,
        "GUARD_PROPOSAL_DIR",
        repo / "docs" / "orchestration" / "experiment_guard_proposals",
    )
    monkeypatch.setattr(
        experiment_promote,
        "MEMORY_INDEX_PATH",
        repo / "docs" / "memory" / "index.md",
    )
    monkeypatch.setattr(
        experiment_promote,
        "BACKLOG_LEDGER_PATH",
        repo / "docs" / "roadmap" / "BACKLOG_LEDGER.md",
    )


def _packet(
    *,
    experiment_id: str = "exp-promote",
    promotion_target: str = "pr_packet",
    creative_research_origin: dict[str, str] | None = None,
) -> dict[str, object]:
    packet: dict[str, object] = {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "decision_question": "Promote governed experiment result",
        "task_class": "Experimentation",
        "domain": "ml",
        "mutable_candidate_surface": ["core/rag/allowed.py"],
        "immutable_oracles": [
            {"command": 'python3 -c "import sys; sys.exit(0)"', "expected_signal": "must pass"}
        ],
        "budgets": {
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 1,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 1,
            "stop_condition": "stop",
        },
        "metrics": {
            "primary": "reliability_score",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": ["oracle file unchanged", "no hidden memory"],
        "promotion_target": promotion_target,
    }
    if creative_research_origin is not None:
        packet["creative_research_origin"] = creative_research_origin
    return packet


def _result(
    *,
    experiment_id: str = "exp-promote",
    status: str = "accepted",
    failure_class: str | None = None,
    shared_tree_untouched: bool = True,
    runner_mode: str = "candidate_patch",
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "runner_mode": runner_mode,
        "candidate_patch": "candidate.patch",
        "status": status,
        "failure_class": failure_class,
        "mutated_paths": ["core/rag/allowed.py"],
        "oracle_results": [
            {
                "command": 'python3 -c "import sys; sys.exit(0)"',
                "returncode": 0,
                "timed_out": False,
                "truncated": False,
                "stdout": "",
                "stderr": "",
                "cwd": ".",
            }
        ],
        "budget_observations": {"attempts": 1},
        "shared_tree_untouched": shared_tree_untouched,
        "promotion_ready": False,
    }


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_main_writes_decision_and_pr_packet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    result_path = _write_json(tmp_path / "result.json", _result())

    exit_code = experiment_promote.main(
        ["--packet", str(packet_path), "--result", str(result_path)]
    )

    assert exit_code == 0
    decision_path = (
        repo / "artifacts" / "orchestration" / "experiments" / "promotions" / "exp-promote.json"
    )
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    assert decision["disposition"] == "promoted"
    assert decision["promotion_target"] == "pr_packet"
    packet_output = repo / "docs" / "orchestration" / "experiment_pr_packets" / "exp-promote.md"
    assert packet_output.exists()
    assert "Experiment PR Packet" in packet_output.read_text(encoding="utf-8")


def test_build_promotion_decision_writes_audit_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = experiment_contract.validate_experiment_packet(
        _packet(promotion_target="audit_artifact")
    )
    result = experiment_contract.validate_experiment_result(_result())

    decision = experiment_promote.build_promotion_decision(packet, result)

    assert decision["promotion_target"] == "audit_artifact"
    audit_path = repo / "docs" / "audit" / "EXPERIMENT_EXP_PROMOTE.md"
    assert audit_path.exists()
    assert "Experiment Audit Artifact" in audit_path.read_text(encoding="utf-8")


def test_build_promotion_decision_writes_guard_proposal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = experiment_contract.validate_experiment_packet(
        _packet(promotion_target="guard_test_proposal")
    )
    result = experiment_contract.validate_experiment_result(_result())

    decision = experiment_promote.build_promotion_decision(packet, result)

    assert decision["promotion_target"] == "guard_test_proposal"
    proposal_path = (
        repo / "docs" / "orchestration" / "experiment_guard_proposals" / "exp-promote.md"
    )
    assert proposal_path.exists()
    assert "Experiment Guard Proposal" in proposal_path.read_text(encoding="utf-8")


def test_creative_research_origin_is_copied_to_decision_and_markdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    origin = {
        "bundle_id": "creative-research-valid",
        "candidate_id": "hyp-batch",
        "promotion_decision": "promote",
    }
    packet = experiment_contract.validate_experiment_packet(
        _packet(creative_research_origin=origin)
    )
    result = experiment_contract.validate_experiment_result(_result())

    decision = experiment_promote.build_promotion_decision(packet, result)

    assert decision["promotion_target"] == "pr_packet"
    assert decision["disposition"] == "promoted"
    assert decision["creative_research_origin"] == origin
    packet_output = repo / "docs" / "orchestration" / "experiment_pr_packets" / "exp-promote.md"
    markdown = packet_output.read_text(encoding="utf-8")
    assert "Creative Research Origin" in markdown
    assert "creative-research-valid" in markdown
    assert "hyp-batch" in markdown


def test_invalid_creative_research_origin_fails_before_artifact_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = _packet(
        creative_research_origin={
            "bundle_id": "creative-research-valid",
            "candidate_id": "hyp-batch",
            "promotion_decision": "promote",
            "raw_prompt": "must not be accepted",
        }
    )
    result = experiment_contract.validate_experiment_result(_result())

    with pytest.raises(experiment_promote.ExperimentPromotionError, match="unsupported"):
        experiment_promote.build_promotion_decision(packet, result)

    packet_output = repo / "docs" / "orchestration" / "experiment_pr_packets" / "exp-promote.md"
    assert not packet_output.exists()


def test_invalid_creative_research_origin_decision_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = _packet(
        creative_research_origin={
            "bundle_id": "creative-research-valid",
            "candidate_id": "hyp-batch",
            "promotion_decision": "ship",
        }
    )
    result = experiment_contract.validate_experiment_result(_result())

    with pytest.raises(experiment_promote.ExperimentPromotionError, match="must be one of"):
        experiment_promote.build_promotion_decision(packet, result)


def test_main_rejects_invalid_origin_before_artifact_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet_path = _write_json(
        tmp_path / "packet.json",
        _packet(
            creative_research_origin={
                "bundle_id": "../escape",
                "candidate_id": "hyp-batch",
                "promotion_decision": "promote",
            }
        ),
    )
    result_path = _write_json(tmp_path / "result.json", _result())

    exit_code = experiment_promote.main(
        ["--packet", str(packet_path), "--result", str(result_path)]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "creative_research_origin.bundle_id must be a safe local identifier" in captured.out
    assert not (
        repo / "docs" / "orchestration" / "experiment_pr_packets" / "exp-promote.md"
    ).exists()


def test_memory_capsule_updates_index_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = experiment_contract.validate_experiment_packet(
        _packet(promotion_target="memory_capsule")
    )
    result = experiment_contract.validate_experiment_result(_result())

    first = experiment_promote.build_promotion_decision(packet, result)
    second = experiment_promote.build_promotion_decision(packet, result)

    assert first == second
    capsule_path = repo / "docs" / "memory" / "exp-promote_capsule.md"
    assert capsule_path.exists()
    index_content = (repo / "docs" / "memory" / "index.md").read_text(encoding="utf-8")
    assert index_content.count("exp-promote_capsule.md") == 1


def test_rejected_result_backlog_entry_is_allowed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = experiment_contract.validate_experiment_packet(
        _packet(promotion_target="backlog_entry")
    )
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="guard_failure")
    )

    decision = experiment_promote.build_promotion_decision(packet, result)

    assert decision["disposition"] == "deferred"
    ledger = (repo / "docs" / "roadmap" / "BACKLOG_LEDGER.md").read_text(encoding="utf-8")
    assert "Experiment follow-up for exp-promote" in ledger
    assert ledger.count("ledger-exp-promote") == 1


def test_rejected_backlog_entry_preserves_creative_research_origin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    origin = {
        "bundle_id": "creative-research-valid",
        "candidate_id": "hyp-batch",
        "promotion_decision": "defer",
    }
    packet = experiment_contract.validate_experiment_packet(
        _packet(
            promotion_target="backlog_entry",
            creative_research_origin=origin,
        )
    )
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="guard_failure")
    )

    decision = experiment_promote.build_promotion_decision(packet, result)

    assert decision["disposition"] == "deferred"
    assert decision["creative_research_origin"] == origin
    ledger = (repo / "docs" / "roadmap" / "BACKLOG_LEDGER.md").read_text(encoding="utf-8")
    assert "Creative research origin:" in ledger
    assert "Bundle ID: `creative-research-valid`" in ledger
    assert "Candidate ID: `hyp-batch`" in ledger
    assert "Promotion decision: `defer`" in ledger


def test_rejected_result_with_non_backlog_target_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = experiment_contract.validate_experiment_packet(_packet(promotion_target="pr_packet"))
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="guard_failure")
    )

    with pytest.raises(experiment_promote.ExperimentPromotionError, match="backlog_entry"):
        experiment_promote.build_promotion_decision(packet, result)


def test_oracle_only_governance_reviewer_result_never_promotes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = {
        **_packet(promotion_target="audit_artifact"),
        "runner_mode": "oracle_only_governance_reviewer",
    }
    result = experiment_contract.validate_experiment_result(
        {
            **_result(runner_mode="oracle_only_governance_reviewer"),
            "candidate_patch": "oracle_only_governance_reviewer",
            "mutated_paths": [],
            "promotion_ready": False,
        }
    )

    with pytest.raises(experiment_promote.ExperimentPromotionError, match="advisory"):
        experiment_promote.build_promotion_decision(packet, result)


def test_oracle_only_packet_cannot_pair_with_legacy_result_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = {
        **_packet(promotion_target="audit_artifact"),
        "runner_mode": "oracle_only_governance_reviewer",
    }
    result = experiment_contract.validate_experiment_result(_result())

    with pytest.raises(experiment_promote.ExperimentPromotionError, match="runner_mode"):
        experiment_promote.build_promotion_decision(packet, result)


def test_mismatched_experiment_id_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = experiment_contract.validate_experiment_packet(_packet(experiment_id="exp-one"))
    result = experiment_contract.validate_experiment_result(_result(experiment_id="exp-two"))

    with pytest.raises(experiment_promote.ExperimentPromotionError, match="experiment_id"):
        experiment_promote.build_promotion_decision(packet, result)


def test_validate_packet_rejects_pathlike_experiment_id() -> None:
    with pytest.raises(ValueError, match="must contain only ASCII letters"):
        experiment_contract.validate_experiment_packet(_packet(experiment_id="../escape"))


def test_validate_result_requires_failure_class_for_rejection() -> None:
    with pytest.raises(ValueError, match="when status is 'rejected'"):
        experiment_contract.validate_experiment_result(_result(status="rejected"))


def test_existing_target_with_different_content_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    target_path = repo / "docs" / "orchestration" / "experiment_pr_packets" / "exp-promote.md"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("conflicting content\n", encoding="utf-8")
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(_result())

    with pytest.raises(experiment_promote.ExperimentPromotionError, match="different content"):
        experiment_promote.build_promotion_decision(packet, result)


def test_resolve_output_path_rejects_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)

    with pytest.raises(ValueError, match="promotions"):
        experiment_promote._resolve_output_path("../outside.json", "exp-promote")


def test_artifact_paths_reject_pathlike_experiment_id() -> None:
    with pytest.raises(ValueError, match="must contain only ASCII letters"):
        experiment_promote._artifact_paths_for_target("../escape", "pr_packet")
