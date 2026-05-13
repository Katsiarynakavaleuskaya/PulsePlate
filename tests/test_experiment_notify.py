"""Deterministic tests for governed experiment notification rendering."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import scripts.orchestration.context_pack as context_pack
import scripts.orchestration.experiment_contract as experiment_contract
import scripts.orchestration.experiment_notify as experiment_notify


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "core" / "rag").mkdir(parents=True)
    (repo / "core" / "rag" / "allowed.py").write_text(
        "def candidate_value() -> int:\n    return 2\n",
        encoding="utf-8",
    )
    return repo


def _configure_repo(monkeypatch: pytest.MonkeyPatch, repo: Path) -> Path:
    notification_dir = repo / "artifacts" / "orchestration" / "experiments" / "notifications"
    monkeypatch.setattr(context_pack, "REPO_ROOT", repo)
    monkeypatch.setattr(experiment_contract, "REPO_ROOT", repo)
    monkeypatch.setattr(experiment_notify, "REPO_ROOT", repo)
    monkeypatch.setattr(experiment_notify, "NOTIFICATION_ARTIFACT_DIR", notification_dir)
    return notification_dir


def _packet(
    *,
    experiment_id: str = "exp-notify",
    promotion_target: str = "audit_artifact",
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "decision_question": "Notify about governed experiment result",
        "task_class": "Experimentation",
        "domain": "ml",
        "mutable_candidate_surface": ["core/rag/allowed.py"],
        "immutable_oracles": [
            {
                "command": 'python3 -c "import sys; sys.exit(0)"',
                "expected_signal": "must pass",
            }
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


def _result(
    *,
    experiment_id: str = "exp-notify",
    status: str = "accepted",
    failure_class: str | None = None,
    command: str = 'python3 -c "import sys; sys.exit(0)"',
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "candidate_patch": "candidate.patch",
        "status": status,
        "failure_class": failure_class,
        "mutated_paths": ["core/rag/allowed.py"],
        "oracle_results": [
            {
                "command": command,
                "returncode": 0 if status == "accepted" else 1,
                "timed_out": False,
                "truncated": False,
                "stdout": "secret stdout should never render",
                "stderr": "secret stderr should never render",
                "cwd": "/Users/example/local/repo",
            }
        ],
        "budget_observations": {"attempts": 1},
        "shared_tree_untouched": True,
        "promotion_ready": False,
    }


def _promotion(*, experiment_id: str = "exp-notify") -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "result_status": "accepted",
        "failure_class": None,
        "promotion_target": "audit_artifact",
        "disposition": "promoted",
        "durable_artifact_path": "docs/audit/EXPERIMENT_EXP_NOTIFY.md",
        "shared_tree_untouched": True,
        "domain": "ml",
        "evidence": {
            "oracle_commands": ['python3 -c "import sys; sys.exit(0)"'],
            "mutated_paths": ["core/rag/allowed.py"],
            "oracle_count": 1,
        },
    }


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_audit_artifact(repo: Path, experiment_id: str = "exp-notify") -> Path:
    upper_id = experiment_id.upper().replace("-", "_")
    path = repo / "docs" / "audit" / f"EXPERIMENT_{upper_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Experiment Audit Artifact: {experiment_id}\n", encoding="utf-8")
    return path


def _write_backlog_entry(repo: Path, experiment_id: str = "exp-notify") -> Path:
    experiment_slug = experiment_id.replace("_", "-")
    path = repo / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<a id="ledger-{experiment_slug}"></a>\n'
        f"- [ ] P1: Experiment follow-up for {experiment_id}\n",
        encoding="utf-8",
    )
    return path


def _subprocess_env_without_repo_pythonpath() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


EXPECTED_NOTIFICATION = """# Experiment Result Notification: exp-notify

- Result status: `accepted`
- Failure class: `none`
- Shared tree untouched: `true`
- Promotion target: `audit_artifact`
- Promotion disposition: `not-run`
- Durable artifact: `none`

## Mutated Paths

- `core/rag/allowed.py`

## Oracle Summary

- `python3` -> rc=0, timed_out=false, truncated=false

## Delivery Boundary

- Artifact-only summary; no email, Slack, PR comment, or external delivery was sent.
- Raw patch text, oracle stdout/stderr, cwd, and local absolute paths are intentionally omitted.
"""


def test_main_writes_deterministic_notification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    result_path = _write_json(tmp_path / "result.json", _result())

    exit_code = experiment_notify.main(["--packet", str(packet_path), "--result", str(result_path)])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    output = (
        repo / "artifacts" / "orchestration" / "experiments" / "notifications" / "exp-notify.md"
    )
    content = output.read_text(encoding="utf-8")
    assert content == EXPECTED_NOTIFICATION
    assert json.loads(stdout) == {
        "experiment_id": "exp-notify",
        "github_step_summary": False,
        "output": "artifacts/orchestration/experiments/notifications/exp-notify.md",
    }

    second_exit_code = experiment_notify.main(
        ["--packet", str(packet_path), "--result", str(result_path)]
    )
    capsys.readouterr()

    assert second_exit_code == 0
    assert output.read_text(encoding="utf-8") == EXPECTED_NOTIFICATION


def test_notification_includes_promotion_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    _write_audit_artifact(repo)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    result_path = _write_json(tmp_path / "result.json", _result())
    promotion_path = _write_json(tmp_path / "promotion.json", _promotion())

    exit_code = experiment_notify.main(
        [
            "--packet",
            str(packet_path),
            "--result",
            str(result_path),
            "--promotion",
            str(promotion_path),
        ]
    )

    assert exit_code == 0
    content = (
        repo / "artifacts" / "orchestration" / "experiments" / "notifications" / "exp-notify.md"
    ).read_text(encoding="utf-8")
    assert "- Promotion target: `audit_artifact`" in content
    assert "- Promotion disposition: `promoted`" in content
    assert "- Durable artifact: `docs/audit/EXPERIMENT_EXP_NOTIFY.md`" in content


@pytest.mark.parametrize(
    ("override", "match"),
    [
        (
            {
                "promotion_target": "memory_capsule",
                "durable_artifact_path": "docs/memory/exp-notify_capsule.md",
            },
            "target must match",
        ),
        ({"disposition": "claimed"}, "disposition must be one of"),
        ({"disposition": "deferred"}, "must have promotion disposition promoted"),
        ({"result_status": "rejected"}, "result_status must match"),
        ({"failure_class": "guard_failure"}, "failure_class must match"),
        ({"shared_tree_untouched": False}, "shared_tree_untouched must match"),
        ({"durable_artifact_path": "../outside.md"}, "repo-relative"),
        ({"durable_artifact_path": ""}, "repo-relative"),
        (
            {"durable_artifact_path": "docs/review/PR_999_FIXED_MAPPING.md"},
            "must match promotion_target",
        ),
    ],
)
def test_invalid_promotion_decision_is_rejected(
    override: dict[str, object],
    match: str,
) -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(_result())

    with pytest.raises((ValueError, experiment_notify.ExperimentNotificationError), match=match):
        promotion = experiment_notify._validate_promotion_decision({**_promotion(), **override})
        experiment_notify.render_notification_markdown(packet, result, promotion)


def test_wrong_rejected_promotion_policy_is_rejected() -> None:
    packet = experiment_contract.validate_experiment_packet(
        _packet(promotion_target="backlog_entry")
    )
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="guard_failure")
    )
    promotion = experiment_notify._validate_promotion_decision(
        {
            **_promotion(),
            "result_status": "rejected",
            "failure_class": "guard_failure",
            "promotion_target": "backlog_entry",
            "disposition": "promoted",
            "durable_artifact_path": "docs/roadmap/BACKLOG_LEDGER.md",
        }
    )

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="must have promotion disposition deferred",
    ):
        experiment_notify.render_notification_markdown(packet, result, promotion)


def test_promoted_accepted_result_with_dirty_shared_tree_is_rejected() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(
        _result(status="accepted", failure_class=None) | {"shared_tree_untouched": False}
    )
    promotion = experiment_notify._validate_promotion_decision(
        {
            **_promotion(),
            "shared_tree_untouched": False,
        }
    )

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="shared_tree_untouched must be true",
    ):
        experiment_notify.render_notification_markdown(packet, result, promotion)


def test_accepted_result_must_include_packet_oracle_results() -> None:
    packet = experiment_contract.validate_experiment_packet(
        _packet()
        | {
            "immutable_oracles": [
                {"command": "python3 -m pytest tests/test_a.py", "expected_signal": "must pass"},
                {"command": "python3 -m pytest tests/test_b.py", "expected_signal": "must pass"},
            ]
        }
    )
    result = experiment_contract.validate_experiment_result(
        _result(command="python3 -m pytest tests/test_a.py")
    )

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="oracle_results must match",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_result_evidence_must_stay_within_packet_mutable_surface() -> None:
    packet = experiment_contract.validate_experiment_packet(
        _packet() | {"mutable_candidate_surface": ["core/rag/allowed.py"]}
    )
    result = experiment_contract.validate_experiment_result(_result())
    result["mutated_paths"] = ["core/rag/other.py"]

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="mutable_candidate_surface",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_result_evidence_allows_directory_mutable_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    (repo / "docs" / "prompts" / "reliability").mkdir(parents=True)
    packet = experiment_contract.validate_experiment_packet(
        _packet()
        | {
            "mutable_candidate_surface": ["docs/prompts/reliability"],
            "immutable_oracles": [
                {"command": "python3 -m pytest tests/test_a.py", "expected_signal": "must pass"}
            ],
        }
    )
    result = experiment_contract.validate_experiment_result(
        _result(command="python3 -m pytest tests/test_a.py")
    )
    result["mutated_paths"] = ["docs/prompts/reliability/program.md"]

    content = experiment_notify.render_notification_markdown(packet, result)

    assert "- `docs/prompts/reliability/program.md`" in content


def test_result_evidence_allows_directory_surface_with_dots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    (repo / "docs" / "prompts" / "v1.2").mkdir(parents=True)
    packet = experiment_contract.validate_experiment_packet(
        _packet()
        | {
            "mutable_candidate_surface": ["docs/prompts/v1.2"],
            "immutable_oracles": [
                {"command": "python3 -m pytest tests/test_a.py", "expected_signal": "must pass"}
            ],
        }
    )
    result = experiment_contract.validate_experiment_result(
        _result(command="python3 -m pytest tests/test_a.py")
    )
    result["mutated_paths"] = ["docs/prompts/v1.2/program.md"]

    content = experiment_notify.render_notification_markdown(packet, result)

    assert "- `docs/prompts/v1.2/program.md`" in content


def test_result_evidence_rejects_nested_paths_under_file_surface() -> None:
    packet = experiment_contract.validate_experiment_packet(
        _packet() | {"mutable_candidate_surface": ["core/rag/allowed.py"]}
    )
    result = experiment_contract.validate_experiment_result(_result())
    result["mutated_paths"] = ["core/rag/allowed.py/child.py"]

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="mutable_candidate_surface",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_result_evidence_rejects_nested_paths_under_extensionless_file_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    (repo / "core" / "rag" / "runner").write_text("#!/bin/sh\n", encoding="utf-8")
    packet = experiment_contract.validate_experiment_packet(
        _packet() | {"mutable_candidate_surface": ["core/rag/runner"]}
    )
    result = experiment_contract.validate_experiment_result(_result())
    result["mutated_paths"] = ["core/rag/runner/child.py"]

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="mutable_candidate_surface",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_result_evidence_allows_new_extensionless_directory_surface() -> None:
    packet = experiment_contract.validate_experiment_packet(
        _packet() | {"mutable_candidate_surface": ["core/rag/new_feature"]}
    )
    result = experiment_contract.validate_experiment_result(_result())
    result["mutated_paths"] = ["core/rag/new_feature/impl.py"]

    content = experiment_notify.render_notification_markdown(packet, result)

    assert "- `core/rag/new_feature/impl.py`" in content


def test_result_evidence_rejects_traversal_under_directory_surface() -> None:
    packet = experiment_contract.validate_experiment_packet(
        _packet() | {"mutable_candidate_surface": ["core/rag/new_feature"]}
    )
    result = experiment_contract.validate_experiment_result(_result())
    result["mutated_paths"] = ["core/rag/new_feature/../../docs/orchestration/workflow.md"]

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="mutable_candidate_surface",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_result_oracle_commands_must_come_from_packet() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="guard_failure")
    )
    result["oracle_results"] = [
        {
            "command": "API_TOKEN=super-secret python3 -m pytest tests/unknown.py",
            "returncode": 1,
            "timed_out": False,
            "truncated": False,
            "stdout": "",
            "stderr": "",
            "cwd": "",
        }
    ]

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="commands outside packet",
    ) as exc_info:
        experiment_notify.render_notification_markdown(packet, result)
    message = str(exc_info.value)
    assert "python3" in message
    assert "API_TOKEN" not in message
    assert "super-secret" not in message


def test_outside_surface_diagnostic_redacts_mutated_paths() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(_result())
    result["mutated_paths"] = ["/Users/alice/.ssh/id_rsa"]

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="mutable_candidate_surface",
    ) as exc_info:
        experiment_notify.render_notification_markdown(packet, result)
    message = str(exc_info.value)
    assert "[redacted-path]" in message
    assert "/Users/alice" not in message
    assert "id_rsa" not in message


def test_accepted_result_with_failed_oracle_is_rejected() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(_result())
    result["oracle_results"][0]["returncode"] = 1

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="oracle_results must pass",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_accepted_result_with_failure_class_is_rejected() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(_result())
    result["failure_class"] = "guard_failure"

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="failure_class must be null",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_accepted_result_with_dirty_shared_tree_is_rejected() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(_result())
    result["shared_tree_untouched"] = False

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="shared_tree_untouched must be true",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_rejected_result_oracles_must_preserve_packet_prefix() -> None:
    packet = experiment_contract.validate_experiment_packet(
        _packet()
        | {
            "immutable_oracles": [
                {"command": "python3 -m pytest tests/test_a.py", "expected_signal": "must pass"},
                {"command": "python3 -m pytest tests/test_b.py", "expected_signal": "must pass"},
            ]
        }
    )
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="guard_failure")
    )
    result["oracle_results"] = [
        {
            "command": "python3 -m pytest tests/test_b.py",
            "returncode": 1,
            "timed_out": False,
            "truncated": False,
            "stdout": "",
            "stderr": "",
            "cwd": "",
        }
    ]

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="immutable_oracles prefix",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_rejected_infra_flake_allows_passing_oracle_prefix() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="infra_flake")
    )
    result["oracle_results"][0]["returncode"] = 0

    content = experiment_notify.render_notification_markdown(packet, result)

    assert "- Result status: `rejected`" in content
    assert "- Failure class: `infra_flake`" in content


def test_rejected_metric_regression_allows_passing_oracle_prefix() -> None:
    packet = experiment_contract.validate_experiment_packet(
        _packet()
        | {
            "immutable_oracles": [
                {"command": "python3 -m pytest tests/test_a.py", "expected_signal": "must pass"},
                {"command": "python3 -m pytest tests/test_b.py", "expected_signal": "must pass"},
            ]
        }
    )
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="metric_regression")
    )
    result["oracle_results"] = [
        {
            "command": "python3 -m pytest tests/test_a.py",
            "returncode": 0,
            "timed_out": False,
            "truncated": False,
            "stdout": "",
            "stderr": "",
            "cwd": "",
        },
        {
            "command": "python3 -m pytest tests/test_b.py",
            "returncode": 0,
            "timed_out": False,
            "truncated": False,
            "stdout": "",
            "stderr": "",
            "cwd": "",
        },
    ]

    content = experiment_notify.render_notification_markdown(packet, result)

    assert "- Result status: `rejected`" in content
    assert "- Failure class: `metric_regression`" in content


def test_rejected_metric_regression_requires_full_passing_oracle_evidence() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="metric_regression")
    )

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="oracle_results must pass",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_rejected_result_terminal_oracle_must_fail() -> None:
    packet = experiment_contract.validate_experiment_packet(
        _packet()
        | {
            "immutable_oracles": [
                {"command": "python3 -m pytest tests/test_a.py", "expected_signal": "must pass"},
                {"command": "python3 -m pytest tests/test_b.py", "expected_signal": "must pass"},
            ]
        }
    )
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="guard_failure")
    )
    result["oracle_results"] = [
        {
            "command": "python3 -m pytest tests/test_a.py",
            "returncode": 0,
            "timed_out": False,
            "truncated": False,
            "stdout": "",
            "stderr": "",
            "cwd": "",
        }
    ]

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="terminal oracle must fail",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_rejected_oracle_failure_requires_terminal_oracle_evidence() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="guard_failure")
    )
    result["oracle_results"] = []

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="terminal oracle evidence",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_rejected_pre_oracle_class_must_not_include_oracle_evidence() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="unchanged_result")
    )

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="must not include oracle evidence",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_rejected_policy_violation_must_not_include_mutated_paths() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="policy_violation")
    )
    result["oracle_results"] = []

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="mutated_paths must be empty",
    ):
        experiment_notify.render_notification_markdown(packet, result)


def test_promotion_evidence_must_match_packet_and_result() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(_result())
    promotion = experiment_notify._validate_promotion_decision(
        {
            **_promotion(),
            "evidence": {
                "oracle_commands": ["python3 -m pytest tests/stale.py"],
                "mutated_paths": ["core/rag/allowed.py"],
                "oracle_count": 1,
            },
        }
    )

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="evidence.oracle_commands",
    ):
        experiment_notify.render_notification_markdown(packet, result, promotion)


def test_promoted_durable_artifact_must_exist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(_result())
    promotion = experiment_notify._validate_promotion_decision(_promotion())

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="durable_artifact_path must exist",
    ):
        experiment_notify.render_notification_markdown(packet, result, promotion)


def test_backlog_promotion_requires_experiment_anchor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    backlog_path = repo / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text("# Backlog\n", encoding="utf-8")
    packet = experiment_contract.validate_experiment_packet(
        _packet(promotion_target="backlog_entry")
    )
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="guard_failure")
    )
    promotion = experiment_notify._validate_promotion_decision(
        {
            **_promotion(),
            "result_status": "rejected",
            "failure_class": "guard_failure",
            "promotion_target": "backlog_entry",
            "disposition": "deferred",
            "durable_artifact_path": "docs/roadmap/BACKLOG_LEDGER.md",
        }
    )

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="experiment anchor",
    ):
        experiment_notify.render_notification_markdown(packet, result, promotion)


def test_backlog_promotion_accepts_existing_experiment_anchor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    _write_backlog_entry(repo)
    packet = experiment_contract.validate_experiment_packet(
        _packet(promotion_target="backlog_entry")
    )
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="guard_failure")
    )
    promotion = experiment_notify._validate_promotion_decision(
        {
            **_promotion(),
            "result_status": "rejected",
            "failure_class": "guard_failure",
            "promotion_target": "backlog_entry",
            "disposition": "deferred",
            "durable_artifact_path": "docs/roadmap/BACKLOG_LEDGER.md",
        }
    )

    content = experiment_notify.render_notification_markdown(packet, result, promotion)

    assert "- Promotion target: `backlog_entry`" in content
    assert "- Promotion disposition: `deferred`" in content


def test_promotion_evidence_oracle_count_must_match_result() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(_result())
    promotion = experiment_notify._validate_promotion_decision(
        {
            **_promotion(),
            "evidence": {
                "oracle_commands": ['python3 -c "import sys; sys.exit(0)"'],
                "mutated_paths": ["core/rag/allowed.py"],
                "oracle_count": 2,
            },
        }
    )

    with pytest.raises(
        experiment_notify.ExperimentNotificationError,
        match="evidence.oracle_count",
    ):
        experiment_notify.render_notification_markdown(packet, result, promotion)


def test_promotion_experiment_id_mismatch_is_rejected() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(_result())
    promotion = experiment_notify._validate_promotion_decision(
        {
            **_promotion(experiment_id="other-exp"),
            "durable_artifact_path": "docs/audit/EXPERIMENT_OTHER_EXP.md",
        }
    )

    with pytest.raises(experiment_notify.ExperimentNotificationError, match="same experiment_id"):
        experiment_notify.render_notification_markdown(packet, result, promotion)


def test_rejected_result_includes_failure_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(
        _result(status="rejected", failure_class="guard_failure")
    )

    content = experiment_notify.render_notification_markdown(packet, result)

    assert "- Result status: `rejected`" in content
    assert "- Failure class: `guard_failure`" in content


def test_notification_redacts_raw_outputs_patch_and_local_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    _write_audit_artifact(repo)
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(_result())
    promotion = experiment_notify._validate_promotion_decision(
        {
            **_promotion(),
            "durable_artifact_path": "docs/audit/EXPERIMENT_EXP_NOTIFY.md",
        }
    )

    content = experiment_notify.render_notification_markdown(packet, result, promotion)

    assert "secret stdout" not in content
    assert "secret stderr" not in content
    assert "candidate.patch" not in content
    assert "Notify about governed experiment result" not in content
    assert "/Users/example" not in content
    assert "--token" not in content
    assert "super-secret" not in content
    assert "- `python3` -> rc=0, timed_out=false, truncated=false" in content
    assert (
        experiment_notify._oracle_command_name(
            "/Users/example/.venv/bin/python3 --token super-secret"
        )
        == "python3"
    )
    assert (
        experiment_notify._oracle_command_name("API_TOKEN=super-secret python3 -m pytest")
        == "python3"
    )
    assert "super-secret" not in experiment_notify._oracle_command_name(
        "API_TOKEN=super-secret python3 -m pytest"
    )
    assert (
        experiment_notify._oracle_command_name("API_TOKEN='super\nsecret' python3 -m pytest")
        == "python3"
    )
    assert "super" not in experiment_notify._oracle_command_name(
        "API_TOKEN='super\nsecret' python3 -m pytest"
    )
    assert (
        experiment_notify._oracle_command_name("/Users/alice/.ssh/id_rsa --help")
        == "[redacted-command]"
    )
    assert "id_rsa" not in experiment_notify._oracle_command_name("/Users/alice/.ssh/id_rsa --help")
    assert experiment_notify._oracle_command_name("id_rsa --help") == "[redacted-command]"
    assert experiment_notify._safe_repo_path("/Users/example/private-token/path.py") == (
        "[redacted-path]"
    )
    assert experiment_notify._safe_repo_path("../outside.py") == "[redacted-path]"


def test_notification_redacts_windows_local_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = experiment_contract.validate_experiment_result(_result())
    unsafe_paths = [
        r"C:\Users\alice\repo\core\rag.py",
        r"C:Users\alice\repo\core\rag.py",
        r"Users\alice\repo\core\rag.py",
        r"\\server\share\pulseplate\core\rag.py",
    ]

    content = experiment_notify.render_notification_markdown(packet, result)

    assert "C:" not in content
    assert "Users" not in content
    assert "server" not in content
    assert "share" not in content
    assert (
        experiment_notify._oracle_command_name(
            r"C:\Users\alice\repo\.venv\Scripts\python.exe -m pytest"
        )
        == "[redacted-command]"
    )
    for unsafe_path in unsafe_paths:
        assert experiment_notify._safe_repo_path(unsafe_path) == "[redacted-path]"


def test_notification_redacts_home_credential_and_control_character_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet = experiment_contract.validate_experiment_packet(_packet())
    unsafe_paths = [
        "~/.ssh/id_rsa",
        ".aws/credentials",
        "core/rag/allowed.py\n- Result status: `accepted`",
    ]

    content = experiment_notify.render_notification_markdown(
        packet,
        experiment_contract.validate_experiment_result(_result()),
    )

    assert ".ssh" not in content
    assert "id_rsa" not in content
    assert ".aws" not in content
    assert "credentials" not in content
    for unsafe_path in unsafe_paths:
        assert experiment_notify._safe_repo_path(unsafe_path) == "[redacted-path]"


def test_read_json_load_failures_do_not_echo_unsafe_paths(tmp_path: Path) -> None:
    unsafe_path = tmp_path / ".ssh" / "id_rsa"

    with pytest.raises(ValueError, match="Unable to load packet JSON") as exc_info:
        experiment_notify._read_json_object(unsafe_path, label="packet")

    message = str(exc_info.value)
    assert ".ssh" not in message
    assert "id_rsa" not in message
    assert str(tmp_path) not in message


def test_resolve_output_path_rejects_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)

    with pytest.raises(ValueError, match="notifications"):
        experiment_notify._resolve_output_path("../outside.md", "exp-notify")


def test_resolve_output_path_rejects_symlinked_notification_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    notification_dir = _configure_repo(monkeypatch, repo)
    outside = tmp_path / "outside"
    notification_dir.parent.mkdir(parents=True, exist_ok=True)
    outside.mkdir()
    notification_dir.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        experiment_notify._resolve_output_path("exp-notify.md", "exp-notify")


def test_resolve_output_path_rejects_symlinked_child_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    notification_dir = _configure_repo(monkeypatch, repo)
    outside = tmp_path / "outside"
    symlinked_child = notification_dir / "child"
    notification_dir.mkdir(parents=True, exist_ok=True)
    outside.mkdir()
    symlinked_child.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        experiment_notify._resolve_output_path("child/exp-notify.md", "exp-notify")


def test_resolve_output_path_rejects_broken_symlinked_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    notification_dir = _configure_repo(monkeypatch, repo)
    outside = tmp_path / "outside.md"
    output_path = notification_dir / "exp-notify.md"
    notification_dir.mkdir(parents=True, exist_ok=True)
    output_path.symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        experiment_notify._resolve_output_path("exp-notify.md", "exp-notify")


def test_resolve_output_path_rejects_symlinked_artifact_ancestor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    outside = tmp_path / "outside"
    experiments = repo / "artifacts" / "orchestration" / "experiments"
    experiments.parent.mkdir(parents=True, exist_ok=True)
    outside.mkdir()
    experiments.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        experiment_notify._resolve_output_path("exp-notify.md", "exp-notify")


def test_module_cli_shows_help() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "scripts.orchestration.experiment_notify", "--help"],
        check=False,
        capture_output=True,
        env=_subprocess_env_without_repo_pythonpath(),
        text=True,
    )

    assert completed.returncode == 0
    assert "Render artifact-only notifications" in completed.stdout


def test_direct_script_invocation_fails_without_repo_pythonpath() -> None:
    script_path = Path("scripts/orchestration/experiment_notify.py")

    completed = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        check=False,
        capture_output=True,
        env=_subprocess_env_without_repo_pythonpath(),
        text=True,
    )

    assert completed.returncode == 2
    assert "python -m scripts.orchestration.experiment_notify" in completed.stderr
    assert "ModuleNotFoundError" not in completed.stderr


def test_direct_script_invocation_outside_repo_fails_without_sys_path_mutation(
    tmp_path: Path,
) -> None:
    script_path = Path("scripts/orchestration/experiment_notify.py").resolve()

    completed = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        check=False,
        capture_output=True,
        cwd=tmp_path,
        env=_subprocess_env_without_repo_pythonpath(),
        text=True,
    )

    assert completed.returncode == 2
    assert "python -m scripts.orchestration.experiment_notify" in completed.stderr
    assert "ModuleNotFoundError" not in completed.stderr


def test_cli_rejects_absolute_output_escape_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    result_path = _write_json(tmp_path / "result.json", _result())
    outside_path = tmp_path / "outside.md"

    exit_code = experiment_notify.main(
        [
            "--packet",
            str(packet_path),
            "--result",
            str(result_path),
            "--output",
            str(outside_path),
        ]
    )

    assert exit_code == 1
    assert not outside_path.exists()


def test_cli_write_failure_redacts_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    result_path = _write_json(tmp_path / "result.json", _result())
    output_dir = repo / "artifacts" / "orchestration" / "experiments" / "notifications" / "exp.md"
    output_dir.mkdir(parents=True)

    exit_code = experiment_notify.main(
        [
            "--packet",
            str(packet_path),
            "--result",
            str(result_path),
            "--output",
            str(output_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "unable to write experiment notification" in captured.out
    assert "artifacts/orchestration" not in captured.out
    assert str(repo) not in captured.out


def test_cli_validation_failure_redacts_validator_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    result = _result()
    result["oracle_results"][0]["returncode"] = "API_TOKEN=super-secret"
    result_path = _write_json(tmp_path / "result.json", result)

    exit_code = experiment_notify.main(["--packet", str(packet_path), "--result", str(result_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "invalid experiment notification input" in captured.out
    assert "API_TOKEN" not in captured.out
    assert "super-secret" not in captured.out


def test_github_step_summary_requires_explicit_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    summary_path = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    result_path = _write_json(tmp_path / "result.json", _result())

    exit_without_flag = experiment_notify.main(
        ["--packet", str(packet_path), "--result", str(result_path)]
    )
    assert exit_without_flag == 0
    assert not summary_path.exists()

    exit_with_flag = experiment_notify.main(
        [
            "--packet",
            str(packet_path),
            "--result",
            str(result_path),
            "--github-step-summary",
        ]
    )

    assert exit_with_flag == 0
    assert "# Experiment Result Notification: exp-notify" in summary_path.read_text(
        encoding="utf-8"
    )


def test_github_step_summary_flag_fails_without_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    result_path = _write_json(tmp_path / "result.json", _result())

    exit_code = experiment_notify.main(
        [
            "--packet",
            str(packet_path),
            "--result",
            str(result_path),
            "--github-step-summary",
        ]
    )

    assert exit_code == 1


def test_github_step_summary_write_failure_redacts_unsafe_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    _configure_repo(monkeypatch, repo)
    unsafe_summary_path = tmp_path / ".ssh" / "id_rsa"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(unsafe_summary_path))
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    result_path = _write_json(tmp_path / "result.json", _result())

    exit_code = experiment_notify.main(
        [
            "--packet",
            str(packet_path),
            "--result",
            str(result_path),
            "--github-step-summary",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Unable to write GITHUB_STEP_SUMMARY." in captured.out
    assert ".ssh" not in captured.out
    assert "id_rsa" not in captured.out
    assert str(tmp_path) not in captured.out
