"""Deterministic tests for the governed experiment runner."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest

from app.security.execution_sandbox import SandboxResult
import scripts.orchestration.experiment_contract as experiment_contract
import scripts.orchestration.experiment_runner as experiment_runner


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    git_binary = shutil.which("git")
    if not git_binary:
        raise AssertionError("git binary is required for experiment runner tests.")
    return subprocess.run(
        [git_binary, *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "core" / "rag").mkdir(parents=True)
    (repo / "docs" / "orchestration").mkdir(parents=True)
    (repo / "core" / "rag" / "allowed.py").write_text(
        "def candidate_value() -> int:\n" "    return 1\n",
        encoding="utf-8",
    )
    (repo / "docs" / "orchestration" / "workflow.md").write_text(
        "# Workflow\n",
        encoding="utf-8",
    )

    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "runner@example.com")
    _git(repo, "config", "user.name", "Experiment Runner")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    return repo


def _write_patch(repo: Path, relative_path: str, new_text: str, patch_path: Path) -> Path:
    file_path = repo / relative_path
    original = file_path.read_text(encoding="utf-8")
    file_path.write_text(new_text, encoding="utf-8")
    patch_text = _git(repo, "diff", "--", relative_path).stdout
    patch_path.write_text(patch_text, encoding="utf-8")
    file_path.write_text(original, encoding="utf-8")
    return patch_path


def _base_packet(
    *, mutable_path: str, oracle_command: str, experiment_id: str = "exp-test"
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "decision_question": "Evaluate bounded candidate patch",
        "task_class": "Experimentation",
        "mutable_candidate_surface": [mutable_path],
        "immutable_oracles": [{"command": oracle_command, "expected_signal": "must pass"}],
        "budgets": {
            "wall_clock_seconds": 5,
            "retry_budget": 1,
            "max_changed_files": 1,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 1,
            "stop_condition": "Stop on timeout.",
        },
        "metrics": {
            "primary": "reliability_score",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": ["oracle file unchanged", "no hidden memory"],
        "promotion_target": "audit_artifact",
    }


def _configure_runner_repo(
    monkeypatch: pytest.MonkeyPatch,
    repo: Path,
) -> Path:
    result_dir = repo / "artifacts" / "orchestration" / "experiments" / "results"
    monkeypatch.setattr(experiment_contract, "REPO_ROOT", repo)
    monkeypatch.setattr(experiment_runner, "REPO_ROOT", repo)
    monkeypatch.setattr(experiment_runner, "RESULT_ARTIFACT_DIR", result_dir)
    return result_dir


def _validate_packet(packet: dict[str, object]) -> dict[str, object]:
    validated = experiment_contract.validate_experiment_packet(packet)
    assert validated["experiment_id"]
    return validated


def test_validate_packet_rejects_wrong_schema_version() -> None:
    """Runner input must fail closed on incompatible packet schema versions."""

    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
    )
    packet["schema_version"] = "0.9"

    with pytest.raises(ValueError, match="schema_version"):
        experiment_contract.validate_experiment_packet(packet)


def test_validate_packet_rejects_non_allowlisted_oracle_binary() -> None:
    """Packet validation should reject oracles that the runner would reject later."""

    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='bash -lc "exit 0"',
    )

    with pytest.raises(ValueError, match="not allowlisted"):
        experiment_contract.validate_experiment_packet(packet)


def test_validate_packet_rejects_empty_primary_metric() -> None:
    """The primary metric must be explicit and non-empty."""

    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
    )
    packet["metrics"] = {
        **packet["metrics"],
        "primary": "",
        "secondary": ["latency_p95_ms"],
    }

    with pytest.raises(ValueError, match="primary --metric"):
        experiment_contract.validate_experiment_packet(packet)


def test_validate_packet_rejects_unknown_budget_keys() -> None:
    """Unsupported budget keys must fail closed during packet validation."""

    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
    )
    packet["budgets"] = {
        **packet["budgets"],
        "gpu_budget": 1,
    }

    with pytest.raises(ValueError, match="Unsupported budget keys: gpu_budget"):
        experiment_contract.validate_experiment_packet(packet)


def test_evaluate_candidate_accepts_allowlisted_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "accepted.patch",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command=(
                'python3 -c "from pathlib import Path; import sys; '
                "sys.exit(0 if 'return 2' in Path('core/rag/allowed.py').read_text() else 1)\""
            ),
        )
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "accepted"
    assert result["failure_class"] is None
    assert result["mutated_paths"] == ["core/rag/allowed.py"]
    assert result["shared_tree_untouched"] is True
    assert result["promotion_ready"] is False
    assert _git(repo, "status", "--short").stdout.strip() == ""


def test_evaluate_candidate_rejects_forbidden_patch_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "docs/orchestration/workflow.md",
        "# Mutated workflow\n",
        tmp_path / "forbidden.patch",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "import sys; sys.exit(0)"',
        )
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "policy_violation"
    assert result["shared_tree_untouched"] is True


def test_evaluate_candidate_rejects_traversal_patch_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = tmp_path / "traversal.patch"
    patch_path.write_text(
        "diff --git a/../docs/orchestration/workflow.md b/../docs/orchestration/workflow.md\n"
        "--- a/../docs/orchestration/workflow.md\n"
        "+++ b/../docs/orchestration/workflow.md\n"
        "@@ -1 +1 @@\n"
        "-# Workflow\n"
        "+# Escaped workflow\n",
        encoding="utf-8",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "import sys; sys.exit(0)"',
        )
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "policy_violation"


def test_evaluate_candidate_rejects_rename_from_forbidden_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rename sources must count toward mutable-surface validation."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = tmp_path / "rename-forbidden.patch"
    patch_path.write_text(
        "diff --git a/docs/orchestration/workflow.md b/core/rag/allowed.py\n"
        "similarity index 100%\n"
        "rename from docs/orchestration/workflow.md\n"
        "rename to core/rag/allowed.py\n",
        encoding="utf-8",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "import sys; sys.exit(0)"',
        )
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "policy_violation"


def test_extract_mutated_paths_ignores_copy_from_source() -> None:
    """Copy diffs should validate only the mutated target path."""

    mutated_paths = experiment_runner._extract_mutated_paths(
        "diff --git a/docs/orchestration/workflow.md b/core/rag/allowed.py\n"
        "similarity index 100%\n"
        "copy from docs/orchestration/workflow.md\n"
        "copy to core/rag/allowed.py\n"
    )

    assert mutated_paths == ["core/rag/allowed.py"]


def test_evaluate_candidate_returns_unchanged_result_for_empty_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = tmp_path / "empty.patch"
    patch_path.write_text("", encoding="utf-8")
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "import sys; sys.exit(0)"',
        )
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "unchanged_result"
    assert result["mutated_paths"] == []


def test_evaluate_candidate_maps_nonzero_oracle_to_guard_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "guard.patch",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "import sys; sys.exit(3)"',
        )
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "guard_failure"
    assert result["oracle_results"][0]["returncode"] == 3


def test_evaluate_candidate_maps_timeout_oracle_to_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "timeout.patch",
    )
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "import time; time.sleep(2)"',
    )
    packet["budgets"] = {
        **packet["budgets"],
        "wall_clock_seconds": 1,
    }
    validated_packet = _validate_packet(packet)
    monkeypatch.setattr(
        experiment_runner.sandbox,
        "run_local_sandbox",
        lambda *_args, **_kwargs: SandboxResult(
            argv=("python3", "-c", "import time; time.sleep(2)"),
            returncode=124,
            stdout="",
            stderr="command timed out",
            timed_out=True,
            truncated=False,
            cwd=".",
        ),
    )

    result = experiment_runner.evaluate_candidate(validated_packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "timeout"
    assert result["oracle_results"][0]["timed_out"] is True


def test_classify_oracle_failure_matches_only_standalone_oom_markers() -> None:
    """OOM classification should ignore unrelated substrings such as rooms/zoom."""

    noisy_result = SandboxResult(
        argv=("python3", "-c", "import sys; sys.exit(1)"),
        returncode=1,
        stdout="rooms.py failed",
        stderr="zoom level mismatch",
        timed_out=False,
        truncated=False,
        cwd=".",
    )
    oom_result = SandboxResult(
        argv=("python3", "-c", "import sys; sys.exit(1)"),
        returncode=1,
        stdout="",
        stderr="Worker hit OOM while loading batch",
        timed_out=False,
        truncated=False,
        cwd=".",
    )

    assert experiment_runner._classify_oracle_failure(noisy_result) == "guard_failure"
    assert experiment_runner._classify_oracle_failure(oom_result) == "oom"


def test_evaluate_candidate_allows_first_oracle_on_one_second_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 1-second budget should still allow the first oracle to start."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "one-second.patch",
    )
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
    )
    packet["budgets"] = {
        **packet["budgets"],
        "wall_clock_seconds": 1,
    }
    validated_packet = _validate_packet(packet)

    monotonic_values = iter([0.0, 0.01])
    monkeypatch.setattr(
        experiment_runner.time,
        "monotonic",
        lambda: next(monotonic_values),
    )
    monkeypatch.setattr(
        experiment_runner.sandbox,
        "run_local_sandbox",
        lambda *_args, **_kwargs: SandboxResult(
            argv=("python3", "-c", "import sys; sys.exit(0)"),
            returncode=0,
            stdout="ok",
            stderr="",
            timed_out=False,
            truncated=False,
            cwd=".",
        ),
    )

    result = experiment_runner.evaluate_candidate(validated_packet, patch_path)

    assert result["status"] == "accepted"
    assert result["failure_class"] is None
    assert result["oracle_results"][0]["returncode"] == 0


def test_evaluate_candidate_maps_sandbox_exception_to_infra_flake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sandbox failures must return a deterministic infra_flake result artifact."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "sandbox-exception.patch",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "import sys; sys.exit(0)"',
        )
    )

    def _raise_sandbox_error(*_args: object, **_kwargs: object) -> SandboxResult:
        raise RuntimeError("sandbox exploded")

    monkeypatch.setattr(
        experiment_runner.sandbox,
        "run_local_sandbox",
        _raise_sandbox_error,
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "infra_flake"
    assert "Unable to execute oracle" in result["budget_observations"]["runner_error"]
    assert "sandbox exploded" in result["budget_observations"]["runner_error"]
    assert result["shared_tree_untouched"] is True


def test_evaluate_candidate_retries_infra_flake_within_retry_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transient infra flakes should consume retry_budget before final rejection."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "retry.patch",
    )
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
    )
    packet["budgets"] = {
        **packet["budgets"],
        "retry_budget": 1,
    }
    validated_packet = _validate_packet(packet)

    attempts = {"count": 0}

    def _flaky_sandbox(*_args: object, **_kwargs: object) -> SandboxResult:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary sandbox failure")
        return SandboxResult(
            argv=("python3", "-c", "import sys; sys.exit(0)"),
            returncode=0,
            stdout="ok",
            stderr="",
            timed_out=False,
            truncated=False,
            cwd=".",
        )

    monkeypatch.setattr(
        experiment_runner.sandbox,
        "run_local_sandbox",
        _flaky_sandbox,
    )

    result = experiment_runner.evaluate_candidate(validated_packet, patch_path)

    assert result["status"] == "accepted"
    assert result["failure_class"] is None
    assert result["budget_observations"]["attempts"] == 2
    assert result["budget_observations"]["retries_consumed"] == 1


def test_evaluate_candidate_retries_cleanup_infra_flake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cleanup failures should route through retry_budget instead of escaping raw."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "cleanup-retry.patch",
    )
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
    )
    packet["budgets"] = {
        **packet["budgets"],
        "retry_budget": 1,
    }
    validated_packet = _validate_packet(packet)

    real_create_temp_checkout = experiment_runner._create_temp_checkout
    cleanup_failures = {"count": 0}

    class _CleanupWrapper:
        def __init__(self, inner: tempfile.TemporaryDirectory[str]) -> None:
            self._inner = inner
            self.name = inner.name

        def cleanup(self) -> None:
            self._inner.cleanup()
            raise OSError("cleanup locked")

    def _checkout_with_flaky_cleanup(
        root: Path,
    ) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp_dir, checkout_root = real_create_temp_checkout(root)
        if cleanup_failures["count"] == 0:
            cleanup_failures["count"] += 1
            return _CleanupWrapper(temp_dir), checkout_root
        return temp_dir, checkout_root

    monkeypatch.setattr(
        experiment_runner,
        "_create_temp_checkout",
        _checkout_with_flaky_cleanup,
    )

    result = experiment_runner.evaluate_candidate(validated_packet, patch_path)

    assert result["status"] == "accepted"
    assert result["failure_class"] is None
    assert result["budget_observations"]["attempts"] == 2
    assert result["budget_observations"]["retries_consumed"] == 1


def test_evaluate_candidate_retries_temp_checkout_infra_flake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transient clone/checkout failures should also consume retry_budget."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "checkout-retry.patch",
    )
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
    )
    packet["budgets"] = {
        **packet["budgets"],
        "retry_budget": 1,
    }
    validated_packet = _validate_packet(packet)

    attempts = {"count": 0}
    real_create_temp_checkout = experiment_runner._create_temp_checkout

    def _flaky_checkout(root: Path) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise experiment_runner.InfraFlakeError("temporary checkout failure")
        return real_create_temp_checkout(root)

    monkeypatch.setattr(
        experiment_runner,
        "_create_temp_checkout",
        _flaky_checkout,
    )

    result = experiment_runner.evaluate_candidate(validated_packet, patch_path)

    assert result["status"] == "accepted"
    assert result["failure_class"] is None
    assert result["budget_observations"]["attempts"] == 2
    assert result["budget_observations"]["retries_consumed"] == 1


def test_evaluate_candidate_enforces_total_wall_clock_budget_across_oracles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Total wall_clock_seconds must bound the full oracle sequence, not each command."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "budget.patch",
    )
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
    )
    packet["immutable_oracles"] = [
        {"command": 'python3 -c "import sys; sys.exit(0)"', "expected_signal": "must pass"},
        {"command": 'python3 -c "import sys; sys.exit(0)"', "expected_signal": "must pass"},
    ]
    packet["budgets"] = {
        **packet["budgets"],
        "wall_clock_seconds": 1,
    }
    validated_packet = _validate_packet(packet)

    monotonic_values = iter([0.0, 0.0, 1.6])
    monkeypatch.setattr(
        experiment_runner.time,
        "monotonic",
        lambda: next(monotonic_values),
    )
    monkeypatch.setattr(
        experiment_runner.sandbox,
        "run_local_sandbox",
        lambda *_args, **_kwargs: SandboxResult(
            argv=("python3", "-c", "import sys; sys.exit(0)"),
            returncode=0,
            stdout="ok",
            stderr="",
            timed_out=False,
            truncated=False,
            cwd=".",
        ),
    )

    result = experiment_runner.evaluate_candidate(validated_packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "timeout"
    assert len(result["oracle_results"]) == 2
    assert result["oracle_results"][0]["returncode"] == 0
    assert result["oracle_results"][1]["timed_out"] is True
    assert result["budget_observations"]["oracle_commands_executed"] == 2


def test_evaluate_candidate_maps_non_applicable_patch_to_infra_flake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = tmp_path / "broken.patch"
    patch_path.write_text(
        "diff --git a/core/rag/allowed.py b/core/rag/allowed.py\n"
        "--- a/core/rag/allowed.py\n"
        "+++ b/core/rag/allowed.py\n"
        "@@ -9 +9 @@\n"
        "-return 99\n"
        "+return 100\n",
        encoding="utf-8",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "import sys; sys.exit(0)"',
        )
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "infra_flake"


def test_evaluate_candidate_returns_infra_flake_for_missing_patch_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preflight patch-read failures must still return a deterministic result artifact."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "import sys; sys.exit(0)"',
        )
    )

    result = experiment_runner.evaluate_candidate(packet, tmp_path / "missing.patch")

    assert result["status"] == "rejected"
    assert result["failure_class"] == "infra_flake"
    assert "Unable to read candidate patch" in result["budget_observations"]["runner_error"]


def test_evaluate_candidate_marks_unverified_shared_tree_probe_as_infra_flake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Baseline shared-tree probe failures must not claim untouched=True."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "shared-status.patch",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "import sys; sys.exit(0)"',
        )
    )

    calls = {"count": 0}
    real_shared_tree_status = experiment_runner._shared_tree_status

    def _flaky_shared_tree_status(root: Path) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            raise experiment_runner.InfraFlakeError("baseline status probe failed")
        return real_shared_tree_status(root)

    monkeypatch.setattr(
        experiment_runner,
        "_shared_tree_status",
        _flaky_shared_tree_status,
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "infra_flake"
    assert result["shared_tree_untouched"] is False
    assert "baseline status probe failed" in result["budget_observations"]["runner_error"]
    assert calls["count"] == 1


def test_main_writes_result_inside_artifact_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    result_dir = _configure_runner_repo(monkeypatch, repo)
    packet_path = tmp_path / "packet.json"
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "cli.patch",
    )
    packet_path.write_text(
        json.dumps(
            _base_packet(
                mutable_path="core/rag/allowed.py",
                oracle_command=(
                    'python3 -c "from pathlib import Path; import sys; '
                    "sys.exit(0 if 'return 2' in Path('core/rag/allowed.py').read_text() else 1)\""
                ),
                experiment_id="exp-cli",
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = experiment_runner.main(
        [
            "--packet",
            str(packet_path),
            "--candidate-patch",
            str(patch_path),
            "--output",
            "nested/result.json",
        ]
    )

    captured = capsys.readouterr()
    result_path = result_dir / "nested" / "result.json"
    assert exit_code == 0
    assert result_path.exists()
    written = json.loads(result_path.read_text(encoding="utf-8"))
    assert written["experiment_id"] == "exp-cli"
    assert (
        json.loads(captured.out)["output"]
        == (
            Path("artifacts/orchestration/experiments/results") / "nested" / "result.json"
        ).as_posix()
    )


def test_resolve_output_path_rejects_default_experiment_id_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default output path must stay inside the result artifact directory."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)

    with pytest.raises(
        ValueError,
        match="--output must stay within artifacts/orchestration/experiments/results",
    ):
        experiment_runner._resolve_output_path(None, "../outside")


def test_evaluate_candidate_applies_validated_patch_text_not_mutated_patch_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runner must apply the already-validated patch text, not reread the patch file."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "validated.patch",
    )
    validated_patch_text = patch_path.read_text(encoding="utf-8")
    patch_path.write_text(
        "diff --git a/docs/orchestration/workflow.md b/docs/orchestration/workflow.md\n"
        "--- a/docs/orchestration/workflow.md\n"
        "+++ b/docs/orchestration/workflow.md\n"
        "@@ -1 +1 @@\n"
        "-# Workflow\n"
        "+# Mutated workflow\n",
        encoding="utf-8",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command=(
                'python3 -c "from pathlib import Path; import sys; '
                "sys.exit(0 if 'return 2' in Path('core/rag/allowed.py').read_text() else 1)\""
            ),
        )
    )
    monkeypatch.setattr(
        experiment_runner,
        "_read_patch_text",
        lambda _path: validated_patch_text,
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "accepted"
    assert result["failure_class"] is None
    assert result["mutated_paths"] == ["core/rag/allowed.py"]
