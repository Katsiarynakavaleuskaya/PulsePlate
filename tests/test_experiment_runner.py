"""Deterministic tests for the governed experiment runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any, cast

import pytest

from app.security.execution_sandbox import SandboxRequest, SandboxResult
import scripts.orchestration.context_pack as context_pack
import scripts.orchestration.experiment_contract as experiment_contract
import scripts.orchestration.experiment_runner as experiment_runner


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    git_binary = shutil.which("git")
    if not git_binary:
        raise AssertionError("git binary is required for experiment runner tests.")
    if git_binary.endswith("/usr/libexec/git-core/git"):
        git_binary = "/usr/bin/git"
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
    (repo / "docs" / "orchestration").mkdir(parents=True)
    (repo / "docs" / "review").mkdir(parents=True)
    (repo / "scripts" / "ci").mkdir(parents=True)
    (repo / "scripts" / "orchestration").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "AGENTS.md").write_text("# Agent rules\n", encoding="utf-8")
    (repo / "core" / "rag" / "allowed.py").write_text(
        "def candidate_value() -> int:\n" "    return 1\n",
        encoding="utf-8",
    )
    (repo / "docs" / "orchestration" / "workflow.md").write_text(
        "# Workflow\n",
        encoding="utf-8",
    )
    (repo / "docs" / "review" / "PR_1_FIXED_MAPPING.md").write_text(
        "# Mapping\n",
        encoding="utf-8",
    )
    (repo / "scripts" / "ci" / "check_gate.py").write_text(
        "raise SystemExit(0)\n",
        encoding="utf-8",
    )
    (repo / "scripts" / "orchestration" / "check_merge_ready.py").write_text(
        "raise SystemExit(0)\n",
        encoding="utf-8",
    )
    (repo / "scripts" / "orchestration" / "experiment_runner.py").write_text(
        "raise SystemExit(0)\n",
        encoding="utf-8",
    )
    (repo / "scripts" / "orchestration" / "check_review_threads_disposition.py").write_text(
        "raise SystemExit(0)\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_oracle.py").write_text(
        "def test_oracle() -> None:\n" "    assert True\n",
        encoding="utf-8",
    )
    (repo / ".venv" / "bin").mkdir(parents=True)
    for python_name in ("python", "python3"):
        python_path = repo / ".venv" / "bin" / python_name
        python_path.write_text(
            f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n',
            encoding="utf-8",
        )
        python_path.chmod(0o755)

    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate Experiment Runner")
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
    *,
    mutable_path: str,
    oracle_command: str,
    experiment_id: str = "exp-test",
    runner_mode: str = "candidate_patch",
    network_budget: int = 1,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "runner_mode": runner_mode,
        "decision_question": "Evaluate bounded candidate patch",
        "task_class": "Experimentation",
        "mutable_candidate_surface": [mutable_path],
        "immutable_oracles": [{"command": oracle_command, "expected_signal": "must pass"}],
        "budgets": {
            "wall_clock_seconds": 5,
            "retry_budget": 1,
            "max_changed_files": 1,
            "network_budget": network_budget,
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
    resolved_repo = repo.resolve()
    result_dir = resolved_repo / "artifacts" / "orchestration" / "experiments" / "results"
    monkeypatch.setattr(context_pack, "REPO_ROOT", resolved_repo)
    monkeypatch.setattr(experiment_contract, "REPO_ROOT", resolved_repo)
    monkeypatch.setattr(experiment_runner, "REPO_ROOT", resolved_repo)
    monkeypatch.setattr(experiment_runner, "RESULT_ARTIFACT_DIR", result_dir)
    return result_dir


def _validate_packet(packet: dict[str, Any]) -> dict[str, Any]:
    validated = experiment_contract.validate_experiment_packet(packet)
    assert validated["experiment_id"]
    return validated


def _packet_budgets(packet: dict[str, object]) -> dict[str, object]:
    budgets = packet["budgets"]
    assert isinstance(budgets, dict)
    return cast(dict[str, object], budgets)


def _packet_metrics(packet: dict[str, object]) -> dict[str, object]:
    metrics = packet["metrics"]
    assert isinstance(metrics, dict)
    return cast(dict[str, object], metrics)


def _run_python_with_fastapi_blocked(
    tmp_path: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    """Run Python with an import hook that fails if FastAPI is imported."""

    blocker_dir = tmp_path / "fastapi-blocker"
    blocker_dir.mkdir()
    (blocker_dir / "sitecustomize.py").write_text(
        "import importlib.abc\n"
        "\n"
        "class _BlockFastAPI(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, fullname, path=None, target=None):\n"
        "        if fullname == 'fastapi' or fullname.startswith('fastapi.'):\n"
        "            raise ImportError('blocked fastapi import')\n"
        "        return None\n"
        "\n"
        "import sys\n"
        "sys.meta_path.insert(0, _BlockFastAPI())\n",
        encoding="utf-8",
    )
    python_path_entries = [
        str(blocker_dir),
        str(context_pack.REPO_ROOT),
        os.environ.get("PYTHONPATH", ""),
    ]
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(python_path_entries),
    }
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(context_pack.REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


def test_experiment_runner_import_does_not_require_fastapi(tmp_path: Path) -> None:
    """Runner import must stay lightweight enough for tooling-only environments."""

    result = _run_python_with_fastapi_blocked(
        tmp_path,
        "-c",
        "import scripts.orchestration.experiment_runner as runner; "
        "print(runner.RESULT_SCHEMA_VERSION)",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == experiment_runner.RESULT_SCHEMA_VERSION


def test_experiment_runner_help_does_not_require_fastapi(tmp_path: Path) -> None:
    """The CLI help path should not fail before artifact/result handling can run."""

    result = _run_python_with_fastapi_blocked(
        tmp_path,
        "scripts/orchestration/experiment_runner.py",
        "--help",
    )

    assert result.returncode == 0, result.stderr
    assert "Evaluate a governed candidate patch" in result.stdout


def test_security_sandbox_import_does_not_require_fastapi(tmp_path: Path) -> None:
    """Sandbox-only tooling imports must not pull FastAPI-bound package exports."""

    result = _run_python_with_fastapi_blocked(
        tmp_path,
        "-c",
        "from app.security.execution_sandbox import SandboxRequest; "
        "print(SandboxRequest(binary='python3').binary)",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "python3"


def test_security_package_dir_does_not_require_fastapi(tmp_path: Path) -> None:
    """Package introspection must not load FastAPI-bound lazy exports."""

    result = _run_python_with_fastapi_blocked(
        tmp_path,
        "-c",
        "import app.security as security; "
        "names = dir(security); "
        "print('RATE_LIMIT_INSIGHT' in names); "
        "print('SandboxRequest' in names)",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["True", "True"]


@pytest.mark.parametrize(
    "statement",
    [
        "from app.security import RATE_LIMIT_INSIGHT",
        "from app.security import rate_limit",
    ],
)
def test_security_fastapi_bound_exports_have_repo_python_diagnostic(
    tmp_path: Path,
    statement: str,
) -> None:
    """Explicit FastAPI-bound exports should fail with an actionable env hint."""

    result = _run_python_with_fastapi_blocked(tmp_path, "-c", statement)

    assert result.returncode != 0
    assert "requires FastAPI/runtime dependencies" in result.stderr
    assert "VENV_PYTHON" in result.stderr
    assert ".venv" in result.stderr
    assert sys.executable in result.stderr


def test_oracle_only_main_writes_result_artifact_without_fastapi(
    tmp_path: Path,
) -> None:
    """Oracle-only result artifact writing must work in tooling-only environments."""

    repo = _init_repo(tmp_path)
    packet_path = repo / "packet.json"
    packet_path.write_text(
        json.dumps(
            _base_packet(
                mutable_path="scripts/orchestration/experiment_runner.py",
                oracle_command='python -c "print(42)"',
                experiment_id="exp-no-fastapi",
                runner_mode="oracle_only_governance_reviewer",
            )
        ),
        encoding="utf-8",
    )
    code = (
        "from pathlib import Path\n"
        "import json\n"
        "import scripts.orchestration.context_pack as context_pack\n"
        "import scripts.orchestration.experiment_contract as experiment_contract\n"
        "import scripts.orchestration.experiment_runner as runner\n"
        f"repo = Path({str(repo)!r}).resolve()\n"
        "result_dir = repo / 'artifacts' / 'orchestration' / 'experiments' / 'results'\n"
        "context_pack.REPO_ROOT = repo\n"
        "experiment_contract.REPO_ROOT = repo\n"
        "runner.REPO_ROOT = repo\n"
        "runner.RESULT_ARTIFACT_DIR = result_dir\n"
        f"exit_code = runner.main(['--packet', {str(packet_path)!r}])\n"
        "output = result_dir / 'exp-no-fastapi.json'\n"
        "payload = json.loads(output.read_text(encoding='utf-8'))\n"
        "print(exit_code)\n"
        "print(output.is_file())\n"
        "print(payload['mutated_paths'])\n"
        "print(payload['promotion_ready'])\n"
        "print(payload['runner_mode'])\n"
    )

    result = _run_python_with_fastapi_blocked(tmp_path, "-c", code)

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[-5:] == [
        "0",
        "True",
        "[]",
        "False",
        "oracle_only_governance_reviewer",
    ]


def test_security_package_fastapi_bound_exports_still_resolve() -> None:
    """Lazy package exports must preserve the runtime FastAPI-facing API."""

    from app.security import RATE_LIMIT_INSIGHT, rate_limit_client_key

    assert RATE_LIMIT_INSIGHT
    assert callable(rate_limit_client_key)


def test_absolute_path_env_resolves_relative_entries(tmp_path: Path) -> None:
    relative_bin = tmp_path / "relative-bin"
    relative_bin.mkdir()
    raw_path = f"{relative_bin.relative_to(tmp_path)}{os.pathsep}/usr/bin"

    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        normalized = experiment_runner._absolute_path_env(raw_path)
    finally:
        os.chdir(original_cwd)

    entries = normalized.split(os.pathsep)
    assert entries == [str(relative_bin.resolve()), "/usr/bin"]


def test_absolute_path_env_uses_default_path_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PATH", raising=False)

    with experiment_runner._temporary_sandbox_env(
        sandbox_root=Path.cwd(),
        allowed_binaries=("python3",),
        timeout_seconds=1,
    ):
        assert os.environ["PATH"] == experiment_runner._absolute_path_env(os.defpath)


def _write_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


def _fake_python_bin(tmp_path: Path, name: str) -> Path:
    bin_dir = tmp_path / name
    bin_dir.mkdir()
    python = bin_dir / "python"
    python3 = bin_dir / "python3"
    _write_executable(python)
    _write_executable(python3)
    return python


def test_python_oracle_path_prefix_prefers_venv_python(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    venv_python = _fake_python_bin(tmp_path, "venv-bin")
    dev_python = _fake_python_bin(tmp_path, "dev-bin")
    monkeypatch.setenv("VENV_PYTHON", str(venv_python))
    monkeypatch.setenv("DEV_PYTHON", str(dev_python))

    prefix = experiment_runner._python_oracle_path_prefix(
        [SandboxRequest(binary="python", args=("-c", "pass"), cwd=".")]
    )

    assert prefix == str(venv_python.parent)


def test_python_oracle_path_prefix_preserves_symlinked_venv_bin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_bin = tmp_path / "real-bin"
    real_bin.mkdir()
    real_python3 = real_bin / "python3"
    _write_executable(real_python3)
    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python3").symlink_to(real_python3)
    venv_python = venv_bin / "python"
    venv_python.symlink_to("python3")
    monkeypatch.setenv("VENV_PYTHON", str(venv_python))
    monkeypatch.delenv("DEV_PYTHON", raising=False)

    prefix = experiment_runner._python_oracle_path_prefix(
        [SandboxRequest(binary="python3", args=("-c", "pass"), cwd=".")]
    )

    assert prefix == str(venv_bin)


def test_python_oracle_path_prefix_uses_dev_python_without_venv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dev_python = _fake_python_bin(tmp_path, "dev-bin")
    monkeypatch.delenv("VENV_PYTHON", raising=False)
    monkeypatch.setenv("DEV_PYTHON", str(dev_python))

    prefix = experiment_runner._python_oracle_path_prefix(
        [SandboxRequest(binary="python3", args=("-c", "pass"), cwd=".")]
    )

    assert prefix == str(dev_python.parent)


def test_python_oracle_path_prefix_uses_repo_venv_python(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_python = tmp_path / ".venv" / "bin" / "python"
    repo_python.parent.mkdir(parents=True)
    _write_executable(repo_python)
    _write_executable(repo_python.parent / "python3")
    monkeypatch.delenv("VENV_PYTHON", raising=False)
    monkeypatch.delenv("DEV_PYTHON", raising=False)
    monkeypatch.setattr(experiment_runner, "REPO_ROOT", tmp_path)

    prefix = experiment_runner._python_oracle_path_prefix(
        [SandboxRequest(binary="python", args=("-c", "pass"), cwd=".")]
    )

    assert prefix == str(repo_python.parent)


def test_python_oracle_path_prefix_uses_shared_worktree_root_venv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared_root = tmp_path / "repo"
    worktree_root = shared_root / "worktrees" / "lane"
    shared_python = shared_root / ".venv" / "bin" / "python"
    worktree_root.mkdir(parents=True)
    shared_python.parent.mkdir(parents=True)
    _write_executable(shared_python)
    _write_executable(shared_python.parent / "python3")
    monkeypatch.delenv("VENV_PYTHON", raising=False)
    monkeypatch.delenv("DEV_PYTHON", raising=False)
    monkeypatch.setattr(experiment_runner, "REPO_ROOT", worktree_root)

    def fake_run_git(
        args: list[str],
        *,
        cwd: Path,
        check: bool = True,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]
        assert cwd == worktree_root
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout=str(shared_root / ".git")
        )

    monkeypatch.setattr(experiment_runner, "_run_git", fake_run_git)

    prefix = experiment_runner._python_oracle_path_prefix(
        [SandboxRequest(binary="python3", args=("-c", "pass"), cwd=".")]
    )

    assert prefix == str(shared_python.parent)


def test_python_oracle_path_prefix_rejects_relative_venv_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VENV_PYTHON", ".venv/bin/python")

    with pytest.raises(experiment_runner.InfraFlakeError, match="absolute executable path"):
        experiment_runner._python_oracle_path_prefix(
            [SandboxRequest(binary="python", args=("-c", "pass"), cwd=".")]
        )


def test_python_oracle_path_prefix_rejects_non_executable_venv_python(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    python = tmp_path / "python"
    python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    monkeypatch.setenv("VENV_PYTHON", str(python))

    with pytest.raises(experiment_runner.InfraFlakeError, match="not executable"):
        experiment_runner._python_oracle_path_prefix(
            [SandboxRequest(binary="python", args=("-c", "pass"), cwd=".")]
        )


def test_python_oracle_path_prefix_fails_closed_without_repo_python(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VENV_PYTHON", raising=False)
    monkeypatch.delenv("DEV_PYTHON", raising=False)
    monkeypatch.setattr(experiment_runner, "REPO_ROOT", tmp_path)

    with pytest.raises(experiment_runner.InfraFlakeError, match="repo-approved Python"):
        experiment_runner._python_oracle_path_prefix(
            [SandboxRequest(binary="python3", args=("-c", "pass"), cwd=".")]
        )


def test_non_python_oracle_path_prefix_does_not_validate_python_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VENV_PYTHON", ".venv/bin/python")

    assert (
        experiment_runner._python_oracle_path_prefix(
            [SandboxRequest(binary="git", args=("--version",), cwd=".")]
        )
        is None
    )


def test_run_oracles_passes_network_disable_marker_for_zero_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command="git --version",
            network_budget=0,
        )
    )
    captured_requests: list[SandboxRequest] = []

    def _capture_request(
        request: SandboxRequest,
        **_kwargs: object,
    ) -> SandboxResult:
        captured_requests.append(request)
        return SandboxResult(
            argv=("git", "--version"),
            returncode=0,
            stdout="git version 2.0\n",
            stderr="",
            timed_out=False,
            truncated=False,
            cwd=str(tmp_path),
        )

    monkeypatch.setattr(experiment_runner.sandbox, "run_local_sandbox", _capture_request)

    results, failure_class = experiment_runner._run_oracles(packet, tmp_path)

    assert failure_class is None
    assert results[0]["returncode"] == 0
    assert captured_requests[0].env == {experiment_runner.sandbox.SANDBOX_DISABLE_NETWORK_ENV: "1"}


def test_run_oracles_omits_network_disable_marker_for_positive_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command="git --version",
    )
    packet["budgets"] = {
        **_packet_budgets(packet),
        "network_budget": 1,
    }
    validated_packet = _validate_packet(packet)
    captured_requests: list[SandboxRequest] = []

    def _capture_request(
        request: SandboxRequest,
        **_kwargs: object,
    ) -> SandboxResult:
        captured_requests.append(request)
        return SandboxResult(
            argv=("git", "--version"),
            returncode=0,
            stdout="git version 2.0\n",
            stderr="",
            timed_out=False,
            truncated=False,
            cwd=str(tmp_path),
        )

    monkeypatch.setattr(experiment_runner.sandbox, "run_local_sandbox", _capture_request)

    results, failure_class = experiment_runner._run_oracles(validated_packet, tmp_path)

    assert failure_class is None
    assert results[0]["returncode"] == 0
    assert captured_requests[0].env is None


def test_temporary_sandbox_env_prepends_python_path_and_restores_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_path = "/usr/bin"
    python_bin = tmp_path / "repo-python-bin"
    python_bin.mkdir()
    monkeypatch.setenv("PATH", original_path)
    monkeypatch.setenv("VENV_PYTHON", "keep-me")

    with experiment_runner._temporary_sandbox_env(
        sandbox_root=Path.cwd(),
        allowed_binaries=("python",),
        timeout_seconds=1,
        path_prefix=str(python_bin),
    ):
        assert os.environ["PATH"].split(os.pathsep)[0] == str(python_bin)
        assert os.environ["VENV_PYTHON"] == "keep-me"

    assert os.environ["PATH"] == original_path
    assert os.environ["VENV_PYTHON"] == "keep-me"


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
        **_packet_metrics(packet),
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
        **_packet_budgets(packet),
        "gpu_budget": 1,
    }

    with pytest.raises(ValueError, match="Unsupported budget keys: gpu_budget"):
        experiment_contract.validate_experiment_packet(packet)


def test_validate_packet_accepts_oracle_only_governance_reviewer_mode() -> None:
    """Oracle-only PR participation is advisory and does not expand mutable surfaces."""

    packet = _base_packet(
        mutable_path="scripts/orchestration/experiment_runner.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
        runner_mode="oracle_only_governance_reviewer",
    )

    validated = experiment_contract.validate_experiment_packet(packet)

    assert validated["runner_mode"] == "oracle_only_governance_reviewer"
    assert validated["mutable_candidate_surface"] == ["scripts/orchestration/experiment_runner.py"]


@pytest.mark.parametrize("runner_mode", [False, 0, [], ""])
def test_validate_runner_mode_rejects_explicit_invalid_values(runner_mode: object) -> None:
    with pytest.raises(ValueError, match="runner_mode must be one of"):
        experiment_contract.validate_runner_mode(runner_mode)


def test_validate_oracle_only_context_ignores_parent_git_index_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracked-context validation must not inherit pre-commit parent git state."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "parent-hook-index"))
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
        runner_mode="oracle_only_governance_reviewer",
    )

    validated = experiment_contract.validate_experiment_packet(packet)

    assert validated["mutable_candidate_surface"] == ["core/rag/allowed.py"]


def test_validate_oracle_only_context_rejects_git_pathspec_magic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Git pathspec magic must not expand oracle-only tracked-context checks."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    packet = _base_packet(
        mutable_path=":(glob)core/rag/*.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
        runner_mode="oracle_only_governance_reviewer",
    )

    with pytest.raises(ValueError, match="tracked by git"):
        experiment_contract.validate_experiment_packet(packet)


def test_validate_packet_rejects_governance_prompt_surface_in_candidate_mode() -> None:
    """Governance docs can be immutable oracles, not runner-mutable prompt docs."""

    packet = _base_packet(
        mutable_path="docs/orchestration/prompts/governance.program.md",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
    )

    with pytest.raises(ValueError, match="Invalid paths|must not include governance"):
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
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "parent-hook-index"))

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


@pytest.mark.parametrize(
    "relative_path",
    [
        "AGENTS.md",
        "docs/review/PR_1_FIXED_MAPPING.md",
        "scripts/ci/check_gate.py",
        "scripts/orchestration/check_merge_ready.py",
        "scripts/orchestration/check_review_threads_disposition.py",
        "tests/test_oracle.py",
    ],
)
def test_validate_candidate_packet_rejects_governance_mutation_surfaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_path: str,
) -> None:
    """Candidate-patch packets must not make governance oracles mutable."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    packet = _base_packet(
        mutable_path=relative_path,
        oracle_command='python3 -c "import sys; sys.exit(0)"',
    )

    with pytest.raises(ValueError, match="Invalid paths|must not include governance"):
        experiment_contract.validate_experiment_packet(packet)


def test_evaluate_candidate_rejects_oracle_only_direct_api_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct helper calls must preserve the same oracle-only boundary as the CLI."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "oracle-only-direct.patch",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "import sys; sys.exit(0)"',
            runner_mode="oracle_only_governance_reviewer",
        )
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["runner_mode"] == "oracle_only_governance_reviewer"
    assert result["candidate_patch"] == "oracle_only_governance_reviewer"
    assert result["failure_class"] == "policy_violation"
    assert result["mutated_paths"] == []
    assert result["oracle_results"] == []
    assert "must not evaluate candidate patches" in result["budget_observations"]["runner_error"]
    assert experiment_contract.validate_experiment_result(result)["runner_mode"] == (
        "oracle_only_governance_reviewer"
    )


def test_evaluate_candidate_invalid_oracle_only_packet_result_is_schema_valid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "oracle-only-invalid-packet.patch",
    )
    packet = _base_packet(
        mutable_path="artifacts/not-tracked.json",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
        runner_mode="oracle_only_governance_reviewer",
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["runner_mode"] == "oracle_only_governance_reviewer"
    assert result["candidate_patch"] == "oracle_only_governance_reviewer"
    assert result["failure_class"] == "policy_violation"
    assert "repo-relative tracked surfaces" in result["budget_observations"]["runner_error"]
    assert experiment_contract.validate_experiment_result(result)["runner_mode"] == (
        "oracle_only_governance_reviewer"
    )


def test_evaluate_candidate_invalid_runner_mode_result_is_schema_valid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "invalid-runner-mode.patch",
    )
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
        runner_mode="oracle-only",
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["runner_mode"] == "candidate_patch"
    assert result["candidate_patch"]
    assert result["failure_class"] == "policy_violation"
    assert "runner_mode must be one of" in result["budget_observations"]["runner_error"]
    assert experiment_contract.validate_experiment_result(result)["runner_mode"] == (
        "candidate_patch"
    )


def test_evaluate_candidate_invalid_experiment_id_result_is_schema_valid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "invalid-experiment-id.patch",
    )
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
    )
    packet["experiment_id"] = "invalid id"

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["experiment_id"] == "invalid-experiment"
    assert result["runner_mode"] == "candidate_patch"
    assert result["failure_class"] == "policy_violation"
    assert "experiment_id must contain" in result["budget_observations"]["runner_error"]
    assert experiment_contract.validate_experiment_result(result)["experiment_id"] == (
        "invalid-experiment"
    )


def test_evaluate_candidate_non_dict_packet_result_is_schema_valid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "non-dict-packet.patch",
    )
    packet = cast(dict[str, Any], ["not", "a", "packet"])

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["experiment_id"] == "invalid-experiment"
    assert result["runner_mode"] == "candidate_patch"
    assert result["candidate_patch"]
    assert result["failure_class"] == "policy_violation"
    assert (
        "Experiment packet must be a JSON object" in result["budget_observations"]["runner_error"]
    )
    assert experiment_contract.validate_experiment_result(result)["runner_mode"] == (
        "candidate_patch"
    )


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
        **_packet_budgets(packet),
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

    scratch = tmp_path / "checkout-reservations"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(scratch))
    result = experiment_runner.evaluate_candidate(validated_packet, patch_path)
    assert list(scratch.iterdir()) == []

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


def test_classify_oracle_failure_maps_unshare_setup_to_capability_mismatch() -> None:
    result = SandboxResult(
        argv=("unshare", "--net", "python3"),
        returncode=1,
        stdout="",
        stderr="unshare: unshare failed: Operation not permitted",
        timed_out=False,
        truncated=False,
        cwd="/tmp",
    )

    assert experiment_runner._classify_oracle_failure(result) == "capability_mismatch"


def test_evaluate_candidate_does_not_retry_lost_unshare_capability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n    return 2\n",
        tmp_path / "lost-unshare.patch",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "print(1)"',
            network_budget=0,
        )
    )
    attempts = {"count": 0}

    def _missing_unshare(*_args: object, **_kwargs: object) -> SandboxResult:
        attempts["count"] += 1
        raise RuntimeError("Network-disabled sandbox requires unshare on PATH.")

    monkeypatch.setattr(experiment_runner, "_shared_tree_status", lambda _root: "stable")
    monkeypatch.setattr(experiment_runner, "_has_effective_diff", lambda _root: True)
    monkeypatch.setattr(experiment_runner.sandbox, "run_local_sandbox", _missing_unshare)

    with pytest.raises(experiment_runner.RunnerCapabilitySignal) as caught:
        experiment_runner.evaluate_candidate(packet, patch_path)

    assert caught.value.args == ()
    assert attempts["count"] == 1


def test_evaluate_candidate_returns_data_free_signal_for_returned_capability_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n    return 2\n",
        tmp_path / "returned-first-capability.patch",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "print(1)"',
            network_budget=0,
        )
    )
    calls = 0

    def _returned_capability(**_kwargs: object) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {
            "status": "rejected",
            "failure_class": "capability_mismatch",
            "budget_observations": {"runner_error": "/private/capability-canary"},
        }

    monkeypatch.setattr(experiment_runner, "_evaluate_attempt", _returned_capability)

    with pytest.raises(experiment_runner.RunnerCapabilitySignal) as caught:
        experiment_runner.evaluate_candidate(packet, patch_path)

    assert caught.value.args == ()
    assert calls == 1


def test_evaluate_candidate_shared_tree_change_overrides_capability_signal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n    return 2\n",
        tmp_path / "capability-shared-tree-change.patch",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "print(1)"',
            network_budget=0,
        )
    )
    statuses = iter(("before", "after"))
    monkeypatch.setattr(experiment_runner, "_shared_tree_status", lambda _root: next(statuses))
    monkeypatch.setattr(
        experiment_runner,
        "_evaluate_attempt",
        lambda **_kwargs: {
            "status": "rejected",
            "failure_class": "capability_mismatch",
        },
    )

    result = experiment_runner.evaluate_candidate(packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "infra_flake"
    assert result["shared_tree_untouched"] is False
    assert result["budget_observations"]["runner_error"] == (
        "Shared working tree changed during run."
    )


def test_evaluate_candidate_classifies_capability_loss_after_infra_retry_as_infra_flake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n    return 2\n",
        tmp_path / "capability-loss-after-retry.patch",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "print(1)"',
            network_budget=0,
        )
    )
    calls = 0
    infra_canary = "infra-retry-canary"
    capability_path_canary = "/Users/capability-loss-canary"
    capability_credential_canary = "credential-capability-loss-canary"

    def _mixed_failure(**_kwargs: object) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise experiment_runner.InfraFlakeError(infra_canary)
        raise experiment_runner.CapabilityMismatchError(
            f"{capability_path_canary} {capability_credential_canary}"
        )

    monkeypatch.setattr(experiment_runner, "_evaluate_attempt", _mixed_failure)

    result = experiment_runner.evaluate_candidate(packet, patch_path)
    serialized = json.dumps(result, sort_keys=True)

    assert calls == 2
    assert result["status"] == "rejected"
    assert result["failure_class"] == "infra_flake"
    assert result["promotion_ready"] is False
    assert result["budget_observations"]["attempts"] == 2
    assert result["budget_observations"]["retries_consumed"] == 1
    assert experiment_contract.validate_experiment_result(result)["failure_class"] == "infra_flake"
    assert (
        result["budget_observations"]["runner_error"]
        == experiment_runner.CAPABILITY_LOSS_AFTER_INFRA_RETRY_ERROR
    )
    assert infra_canary not in serialized
    assert capability_path_canary not in serialized
    assert capability_credential_canary not in serialized


def test_evaluate_candidate_classifies_returned_capability_loss_after_infra_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n    return 2\n",
        tmp_path / "returned-capability-loss-after-retry.patch",
    )
    raw_packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "print(1)"',
        network_budget=0,
    )
    raw_packet["budgets"] = {
        **_packet_budgets(raw_packet),
        "retry_budget": 2,
    }
    packet = _validate_packet(raw_packet)
    calls = 0
    infra_canary = "returned-infra-retry-canary"
    capability_path_canary = "/Users/returned-capability-loss-canary"
    capability_credential_canary = "returned-credential-capability-loss-canary"

    def _mixed_failure(**kwargs: object) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise experiment_runner.InfraFlakeError(infra_canary)
        budget_observations = cast(dict[str, Any], kwargs["budget_observations"])
        budget_observations["oracle_commands_executed"] = 1
        return {
            "status": "rejected",
            "failure_class": "capability_mismatch",
            "budget_observations": {
                "runner_error": f"{capability_path_canary} {capability_credential_canary}"
            },
        }

    monkeypatch.setattr(experiment_runner, "_evaluate_attempt", _mixed_failure)

    result = experiment_runner.evaluate_candidate(packet, patch_path)
    serialized = json.dumps(result, sort_keys=True)

    assert calls == 2
    assert result["status"] == "rejected"
    assert result["failure_class"] == "infra_flake"
    assert result["promotion_ready"] is False
    assert result["oracle_results"] == []
    assert result["budget_observations"]["oracle_commands_executed"] == 0
    assert result["budget_observations"]["attempts"] == 2
    assert result["budget_observations"]["retries_consumed"] == 1
    assert experiment_contract.validate_experiment_result(result)["failure_class"] == "infra_flake"
    assert (
        result["budget_observations"]["runner_error"]
        == experiment_runner.CAPABILITY_LOSS_AFTER_INFRA_RETRY_ERROR
    )
    assert infra_canary not in serialized
    assert capability_path_canary not in serialized
    assert capability_credential_canary not in serialized

    tampered = {
        **result,
        "budget_observations": {
            **result["budget_observations"],
            "oracle_commands_executed": 1,
        },
    }
    with pytest.raises(
        ValueError,
        match="oracle_commands_executed must match oracle_results",
    ):
        experiment_contract.validate_experiment_result(tampered)


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
        **_packet_budgets(packet),
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
        **_packet_budgets(packet),
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
        **_packet_budgets(packet),
        "retry_budget": 1,
    }
    validated_packet = _validate_packet(packet)

    real_create_temp_checkout = experiment_runner._create_temp_checkout
    checkout_paths: list[Path] = []
    cleaned_paths: list[Path] = []
    oracle_roots: list[Path] = []

    def _successful_oracle(
        request: SandboxRequest,
        *,
        allowlist: set[tuple[str, str]] | None = None,
    ) -> SandboxResult:
        # This test owns cleanup retry; real process timing has separate coverage.
        assert request.binary == "python3"
        assert request.args == ("-c", "import sys; sys.exit(0)")
        assert allowlist == {("sandbox.exec", "local://sandbox")}
        oracle_roots.append(Path(os.environ[experiment_runner.sandbox.SANDBOX_ROOT_ENV]))
        return SandboxResult(
            argv=(request.binary, *request.args),
            returncode=0,
            stdout="ok",
            stderr="",
            timed_out=False,
            truncated=False,
            cwd=".",
        )

    class _CleanupWrapper:
        def __init__(self, inner: experiment_runner._CheckoutReservation, *, fail: bool) -> None:
            self._inner = inner
            self.name = inner.name
            self._fail = fail

        @property
        def removal_completed(self) -> bool:
            return self._inner.removal_completed

        def cleanup(self) -> None:
            self._inner.cleanup()
            cleaned_paths.append(Path(self.name))
            assert not Path(self.name).exists()
            if self._fail:
                raise OSError("cleanup locked")

    def _checkout_with_flaky_cleanup(
        root: Path,
    ) -> tuple[Any, Path]:
        temp_dir, checkout_root = real_create_temp_checkout(root)
        checkout_paths.append(checkout_root)
        return _CleanupWrapper(temp_dir, fail=len(checkout_paths) == 1), checkout_root

    monkeypatch.setattr(experiment_runner.sandbox, "run_local_sandbox", _successful_oracle)
    monkeypatch.setattr(
        experiment_runner,
        "_create_temp_checkout",
        _checkout_with_flaky_cleanup,
    )

    result = experiment_runner.evaluate_candidate(validated_packet, patch_path)

    assert result["status"] == "accepted", result
    assert result["failure_class"] is None
    assert result["budget_observations"]["attempts"] == 2
    assert result["budget_observations"]["retries_consumed"] == 1
    assert len(set(checkout_paths)) == 2
    assert oracle_roots == checkout_paths
    assert cleaned_paths == [path.parent for path in checkout_paths]


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
        **_packet_budgets(packet),
        "retry_budget": 1,
    }
    validated_packet = _validate_packet(packet)

    attempts = {"count": 0}
    real_create_temp_checkout = experiment_runner._create_temp_checkout

    def _flaky_checkout(root: Path) -> tuple[experiment_runner._CheckoutReservation, Path]:
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
        **_packet_budgets(packet),
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

    scratch = tmp_path / "checkout-reservations"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(scratch))
    result = experiment_runner.evaluate_candidate(validated_packet, patch_path)
    assert list(scratch.iterdir()) == []

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
    stdout_payload = json.loads(captured.out)
    assert stdout_payload == {"result_artifact_written": True}
    assert "nested/result.json" not in captured.out
    assert "exp-cli" not in captured.out


def test_main_capability_signal_uses_fixed_exit_without_artifact_or_canary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    result_dir = _configure_runner_repo(monkeypatch, repo)
    packet_path = tmp_path / "packet.json"
    patch_path = tmp_path / "candidate.patch"
    packet_path.write_text(
        json.dumps(
            _base_packet(
                mutable_path="core/rag/allowed.py",
                oracle_command='python3 -c "print(1)"',
                experiment_id="exp-capability-cli",
                network_budget=0,
            )
        ),
        encoding="utf-8",
    )
    patch_path.write_text("private-capability-canary", encoding="utf-8")
    monkeypatch.setattr(
        experiment_runner,
        "evaluate_candidate",
        lambda *_args: (_ for _ in ()).throw(experiment_runner.RunnerCapabilitySignal()),
    )

    exit_code = experiment_runner.main(
        [
            "--packet",
            str(packet_path),
            "--candidate-patch",
            str(patch_path),
            "--output",
            "capability.json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == experiment_runner.RUNNER_CAPABILITY_EXIT_CODE
    assert captured.out == experiment_runner.RUNNER_CAPABILITY_DIAGNOSTIC + "\n"
    assert captured.err == ""
    assert "private-capability-canary" not in captured.out
    assert not (result_dir / "capability.json").exists()


def test_main_uses_owned_exit_code_for_written_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    result_dir = _configure_runner_repo(monkeypatch, repo)
    packet_path = tmp_path / "packet.json"
    patch_path = tmp_path / "candidate.patch"
    packet_path.write_text(
        json.dumps(
            _base_packet(
                mutable_path="core/rag/allowed.py",
                oracle_command='python3 -c "print(1)"',
                experiment_id="exp-rejected-cli",
            )
        ),
        encoding="utf-8",
    )
    patch_path.write_text("rejected candidate", encoding="utf-8")
    monkeypatch.setattr(
        experiment_runner,
        "evaluate_candidate",
        lambda *_args: experiment_runner._result_payload(
            experiment_id="exp-rejected-cli",
            candidate_patch="candidate.patch",
            status="rejected",
            failure_class="policy_violation",
            mutated_paths=[],
            oracle_results=[],
            budget_observations={"attempts": 0, "retries_consumed": 0},
            shared_tree_untouched=True,
        ),
    )

    exit_code = experiment_runner.main(
        [
            "--packet",
            str(packet_path),
            "--candidate-patch",
            str(patch_path),
            "--output",
            "rejected.json",
        ]
    )

    assert exit_code == experiment_runner.RUNNER_REJECTED_EXIT_CODE
    written = json.loads((result_dir / "rejected.json").read_text(encoding="utf-8"))
    assert written["status"] == "rejected"


def test_main_writes_oracle_only_governance_reviewer_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    result_dir = _configure_runner_repo(monkeypatch, repo)
    packet_path = tmp_path / "oracle-only-packet.json"
    packet_path.write_text(
        json.dumps(
            _base_packet(
                mutable_path="core/rag/allowed.py",
                oracle_command='python3 -c "import sys; sys.exit(0)"',
                experiment_id="exp-oracle-only",
                runner_mode="oracle_only_governance_reviewer",
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
            "--output",
            "oracle/result.json",
        ]
    )

    captured = capsys.readouterr()
    result_path = result_dir / "oracle" / "result.json"
    assert exit_code == 0
    written = json.loads(result_path.read_text(encoding="utf-8"))
    assert written["experiment_id"] == "exp-oracle-only"
    assert written["status"] == "accepted"
    assert written["candidate_patch"] == "oracle_only_governance_reviewer"
    assert written["mutated_paths"] == []
    assert written["promotion_ready"] is False
    assert written["contribution_kind"] == "none"
    assert written["coauthor_required"] is False
    assert written["coauthor_reason"] == ""
    assert written["shared_tree_untouched"] is True
    assert json.loads(captured.out) == {"result_artifact_written": True}


def test_main_writes_oracle_only_coauthor_contribution_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    result_dir = _configure_runner_repo(monkeypatch, repo)
    packet_path = tmp_path / "oracle-only-packet.json"
    packet_path.write_text(
        json.dumps(
            _base_packet(
                mutable_path="core/rag/allowed.py",
                oracle_command='python3 -c "import sys; sys.exit(0)"',
                experiment_id="exp-oracle-coauthor",
                runner_mode="oracle_only_governance_reviewer",
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
            "--output",
            "oracle/coauthor.json",
            "--contribution-kind",
            "oracle_review",
            "--coauthor-required",
            "--coauthor-reason",
            "Runner oracle shaped the validation and commit decision.",
        ]
    )

    result_path = result_dir / "oracle" / "coauthor.json"
    assert exit_code == 0
    written = json.loads(result_path.read_text(encoding="utf-8"))
    assert written["mutated_paths"] == []
    assert written["promotion_ready"] is False
    assert written["contribution_kind"] == "oracle_review"
    assert written["coauthor_required"] is True
    assert written["coauthor_reason"] == "Runner oracle shaped the validation and commit decision."
    assert experiment_contract.validate_experiment_result(written)["coauthor_required"] is True


def test_main_rejects_oracle_only_coauthor_without_material_contribution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    packet_path = tmp_path / "oracle-only-packet.json"
    packet_path.write_text(
        json.dumps(
            _base_packet(
                mutable_path="core/rag/allowed.py",
                oracle_command='python3 -c "import sys; sys.exit(0)"',
                runner_mode="oracle_only_governance_reviewer",
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = experiment_runner.main(
        [
            "--packet",
            str(packet_path),
            "--coauthor-required",
            "--coauthor-reason",
            "Missing material contribution kind.",
        ]
    )

    assert exit_code == 1
    assert "coauthor_required requires a material contribution_kind" in capsys.readouterr().out


def test_main_rejects_oracle_only_orphan_coauthor_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    packet_path = tmp_path / "oracle-only-packet.json"
    packet_path.write_text(
        json.dumps(
            _base_packet(
                mutable_path="core/rag/allowed.py",
                oracle_command='python3 -c "import sys; sys.exit(0)"',
                runner_mode="oracle_only_governance_reviewer",
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = experiment_runner.main(
        [
            "--packet",
            str(packet_path),
            "--coauthor-reason",
            "Orphan reason must not survive in a non-attribution artifact.",
        ]
    )

    assert exit_code == 1
    assert "coauthor_reason must be empty unless coauthor_required" in capsys.readouterr().out


def test_main_rejects_candidate_patch_attribution_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    packet_path = tmp_path / "candidate-packet.json"
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "candidate.patch",
    )
    packet_path.write_text(
        json.dumps(
            _base_packet(
                mutable_path="core/rag/allowed.py",
                oracle_command='python3 -c "import sys; sys.exit(0)"',
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = experiment_runner.main(
        [
            "--packet",
            str(packet_path),
            "--candidate-patch",
            str(patch_path),
            "--contribution-kind",
            "oracle_review",
            "--coauthor-required",
            "--coauthor-reason",
            "Candidate mode must not accept attribution flags.",
        ]
    )

    assert exit_code == 1
    assert "supported only in oracle-only mode" in capsys.readouterr().out


@pytest.mark.parametrize("returned", [False, True])
def test_oracle_only_capability_loss_raises_data_free_signal_after_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returned: bool,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "print(1)"',
            runner_mode="oracle_only_governance_reviewer",
            network_budget=0,
        )
    )
    # Use the production reservation/clone/cleanup contract in a test-owned parent.
    monkeypatch.setattr(experiment_runner.tempfile, "tempdir", str(tmp_path))
    original_create = experiment_runner._create_temp_checkout
    reservations: list[experiment_runner._CheckoutReservation] = []

    def observe_checkout(root: Path) -> tuple[experiment_runner._CheckoutReservation, Path]:
        owner, checkout = original_create(root)
        reservations.append(owner)
        assert checkout == Path(owner.name) / "checkout"
        assert Path(owner.name).parent == tmp_path
        assert os.path.samestat(Path(owner.name).lstat(), owner.identity)
        assert not owner.removal_completed
        return owner, checkout

    monkeypatch.setattr(experiment_runner, "_create_temp_checkout", observe_checkout)
    if returned:
        monkeypatch.setattr(
            experiment_runner,
            "_run_oracles",
            lambda *_args: (
                [
                    {
                        "command": "oracle",
                        "returncode": 1,
                        "stderr": "private-oracle-capability-canary",
                    }
                ],
                "capability_mismatch",
            ),
        )
    else:
        monkeypatch.setattr(
            experiment_runner,
            "_run_oracles",
            lambda *_args: (_ for _ in ()).throw(
                experiment_runner.CapabilityMismatchError("private-oracle-capability-canary")
            ),
        )

    with pytest.raises(experiment_runner.RunnerCapabilitySignal) as caught:
        experiment_runner.evaluate_oracle_only_governance_reviewer(packet)

    assert caught.value.args == ()
    assert len(reservations) == 1
    owner = reservations[0]
    assert owner.removal_completed is True
    assert not Path(owner.name).exists()
    assert not Path(owner.name).is_symlink()
    assert repo.is_dir()
    assert "private-oracle-capability-canary" not in str(caught.value) + repr(caught.value.args)


def test_oracle_only_shared_tree_change_overrides_capability_signal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command='python3 -c "print(1)"',
            runner_mode="oracle_only_governance_reviewer",
            network_budget=0,
        )
    )
    statuses = iter(("before", "after"))
    monkeypatch.setattr(experiment_runner, "_shared_tree_status", lambda _root: next(statuses))
    monkeypatch.setattr(
        experiment_runner,
        "_run_oracles",
        lambda *_args: ([], "capability_mismatch"),
    )

    result = experiment_runner.evaluate_oracle_only_governance_reviewer(packet)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "infra_flake"
    assert result["shared_tree_untouched"] is False
    assert result["budget_observations"]["runner_error"] == (
        "Shared working tree changed during run."
    )


def test_oracle_only_governance_reviewer_applies_current_tracked_diff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Oracle-only evidence must cover the current tracked PR diff, not stale HEAD."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    (repo / "core" / "rag" / "allowed.py").write_text(
        "def candidate_value() -> int:\n" "    return 2\n",
        encoding="utf-8",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="core/rag/allowed.py",
            oracle_command=(
                'python3 -c "from pathlib import Path; import sys; '
                "sys.exit(0 if 'return 2' in Path('core/rag/allowed.py').read_text() else 1)\""
            ),
            runner_mode="oracle_only_governance_reviewer",
        )
    )

    result = experiment_runner.evaluate_oracle_only_governance_reviewer(packet)

    assert result["status"] == "accepted"
    assert result["mutated_paths"] == []
    assert result["budget_observations"]["source_diff_applied"] is True
    assert _git(repo, "status", "--short").stdout.strip() == "M core/rag/allowed.py"


def test_oracle_only_governance_reviewer_rejects_unowned_tracked_diff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Oracle-only evidence must not silently include dirty paths outside context."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    (repo / "core" / "rag" / "allowed.py").write_text(
        "def candidate_value() -> int:\n" "    return 2\n",
        encoding="utf-8",
    )
    packet = _validate_packet(
        _base_packet(
            mutable_path="scripts/orchestration/experiment_runner.py",
            oracle_command='python3 -c "import sys; sys.exit(0)"',
            runner_mode="oracle_only_governance_reviewer",
        )
    )

    result = experiment_runner.evaluate_oracle_only_governance_reviewer(packet)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "policy_violation"
    assert result["mutated_paths"] == []
    assert result["budget_observations"]["source_diff_paths"] == ["core/rag/allowed.py"]
    assert (
        "must stay within packet context surface" in result["budget_observations"]["runner_error"]
    )


def test_oracle_only_context_surface_must_be_tracked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    packet = _base_packet(
        mutable_path="does/not/exist.py",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
        runner_mode="oracle_only_governance_reviewer",
    )

    with pytest.raises(ValueError, match="tracked by git"):
        experiment_contract.validate_experiment_packet(packet)


def test_oracle_context_metadata_matches_only_literal_index_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    tracked = "core/rag/allowed.py"
    assert experiment_contract.validate_oracle_context_surface([tracked]) == [tracked]
    (repo / "core/rag/untracked.py").write_text("fixture")
    for name in ("core/rag/untracked.py", "core/rag/*.py"):
        with pytest.raises(ValueError, match="tracked by git"):
            experiment_contract.validate_oracle_context_surface([name])


@pytest.mark.parametrize("fault", ["timeout", "oserror", "bad-index", "relative", "non-executable"])
def test_oracle_context_metadata_failure_rejects_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    selected = "core/rag/allowed.py"
    packet = _base_packet(
        mutable_path=selected,
        oracle_command='python3 -c "pass"',
        runner_mode="oracle_only_governance_reviewer",
    )
    binary = tmp_path / "git-fixture"
    binary.write_bytes(b"controlled subprocess seam")
    binary.chmod(0o600 if fault == "non-executable" else 0o700)
    monkeypatch.setattr(
        experiment_contract.shutil,
        "which",
        lambda _: "bin/git" if fault == "relative" else str(binary),
    )
    monkeypatch.setenv("GIT_DIR", "synthetic-private")
    calls = []

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(argv)
        assert argv == [
            str(binary),
            "--literal-pathspecs",
            "ls-files",
            "--error-unmatch",
            "--",
            selected,
        ]
        assert kwargs["cwd"] == str(repo.resolve()) and kwargs["timeout"] == 30
        assert "GIT_DIR" not in kwargs["env"] and kwargs.get("shell", False) is False
        assert kwargs["stdout"] == kwargs["stderr"] == kwargs["stdin"] == subprocess.DEVNULL
        if fault == "timeout":
            raise subprocess.TimeoutExpired(
                ["synthetic-private"], 30, output=b"partial tracked", stderr=b"synthetic-private"
            )
        if fault == "oserror":
            raise OSError("synthetic-private")
        return subprocess.CompletedProcess(
            argv, 128, stdout=b"partial tracked", stderr=b"synthetic-private"
        )

    monkeypatch.setattr(experiment_contract.subprocess, "run", run)
    monkeypatch.setattr(
        experiment_runner, "_run_oracles", lambda *args, **kwargs: pytest.fail("unexpected Oracle")
    )
    result = experiment_runner.evaluate_oracle_only_governance_reviewer(packet)
    assert result["status"] == "rejected" and result["failure_class"] == "policy_violation"
    diagnostic = result["budget_observations"]["runner_error"]
    assert (
        diagnostic
        == {
            "timeout": "Git tracked-context query timed out.",
            "oserror": "Git tracked-context query could not execute.",
            "bad-index": "Git tracked-context query failed.",
            "relative": "An absolute executable Git is required for the context query.",
            "non-executable": "An absolute executable Git is required for the context query.",
        }[fault]
    )
    assert len(calls) == (0 if fault in ("relative", "non-executable") else 1)


def test_oracle_only_direct_api_validates_raw_packet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    packet = _base_packet(
        mutable_path="artifacts/not-tracked.json",
        oracle_command='python3 -c "import sys; sys.exit(0)"',
        runner_mode="oracle_only_governance_reviewer",
    )

    result = experiment_runner.evaluate_oracle_only_governance_reviewer(packet)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "policy_violation"
    assert result["shared_tree_untouched"] is False
    assert "repo-relative tracked surfaces" in result["budget_observations"]["runner_error"]


def test_main_rejects_missing_candidate_patch_for_candidate_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    packet_path = tmp_path / "candidate-packet.json"
    packet_path.write_text(
        json.dumps(
            _base_packet(
                mutable_path="core/rag/allowed.py",
                oracle_command='python3 -c "import sys; sys.exit(0)"',
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = experiment_runner.main(["--packet", str(packet_path)])

    assert exit_code == 1
    assert "--candidate-patch is required" in capsys.readouterr().out


def test_main_rejects_candidate_patch_for_oracle_only_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    packet_path = tmp_path / "oracle-only-packet.json"
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "should-not-apply.patch",
    )
    packet_path.write_text(
        json.dumps(
            _base_packet(
                mutable_path="core/rag/allowed.py",
                oracle_command='python3 -c "import sys; sys.exit(0)"',
                runner_mode="oracle_only_governance_reviewer",
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = experiment_runner.main(
        [
            "--packet",
            str(packet_path),
            "--candidate-patch",
            str(patch_path),
        ]
    )

    assert exit_code == 1
    assert "does not accept --candidate-patch" in capsys.readouterr().out


@pytest.mark.parametrize(
    "override,match",
    [
        ({"mutated_paths": ["core/rag/allowed.py"]}, "must not record mutated_paths"),
        ({"promotion_ready": True}, "must not be promotion_ready"),
        ({"candidate_patch": "candidate.patch"}, "stable candidate_patch marker"),
        ({"contribution_kind": "unknown"}, "contribution_kind"),
        (
            {"coauthor_required": True, "contribution_kind": "none"},
            "material contribution_kind",
        ),
        (
            {"contribution_kind": "oracle_review", "coauthor_required": False},
            "material contribution_kind requires coauthor_required",
        ),
        (
            {
                "contribution_kind": "oracle_review",
                "coauthor_required": True,
                "coauthor_reason": "",
            },
            "coauthor_reason",
        ),
        (
            {
                "contribution_kind": "oracle_review",
                "coauthor_required": True,
                "coauthor_reason": None,
            },
            "coauthor_reason must be a string",
        ),
        (
            {"coauthor_required": False, "coauthor_reason": "orphan reason survives"},
            "coauthor_reason must be empty",
        ),
    ],
)
def test_validate_result_rejects_malformed_oracle_only_artifacts(
    override: dict[str, object],
    match: str,
) -> None:
    result = {
        "schema_version": "1.0",
        "experiment_id": "exp-oracle-only",
        "runner_mode": "oracle_only_governance_reviewer",
        "candidate_patch": "oracle_only_governance_reviewer",
        "status": "accepted",
        "failure_class": None,
        "mutated_paths": [],
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
        "shared_tree_untouched": True,
        "promotion_ready": False,
        "contribution_kind": "none",
        "coauthor_required": False,
        "coauthor_reason": "",
        **override,
    }

    with pytest.raises(ValueError, match=match):
        experiment_contract.validate_experiment_result(result)


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


def test_evaluate_candidate_rejects_fingerprinted_packet_at_wrong_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct candidate evaluation must not run against a stale packet base."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "candidate.patch",
    )
    patch_text = patch_path.read_text(encoding="utf-8")
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "raise SystemExit(0)"',
    )
    packet["candidate_patch_fingerprint"] = experiment_runner.fingerprint_payload(
        {"candidate_patch": patch_text}
    )
    packet["base_commit_sha"] = "0" * 40
    validated_packet = _validate_packet(packet)
    monkeypatch.setattr(
        experiment_runner,
        "_evaluate_attempt",
        lambda **_kwargs: pytest.fail("stale-base packets must fail before evaluation"),
    )

    result = experiment_runner.evaluate_candidate(validated_packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "policy_violation"
    assert result["mutated_paths"] == []
    assert result["oracle_results"] == []
    assert result["budget_observations"]["attempts"] == 0
    assert (
        result["budget_observations"]["runner_error"]
        == "Experiment packet base_commit_sha does not match current repository HEAD."
    )


def test_evaluate_candidate_bounds_fingerprinted_patch_before_evaluation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fingerprint-bound direct packets must not read an unbounded patch into memory."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_text = "x" * 9
    patch_path = tmp_path / "oversized.patch"
    patch_path.write_text(patch_text, encoding="utf-8")
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "raise SystemExit(0)"',
    )
    packet["candidate_patch_fingerprint"] = experiment_runner.fingerprint_payload(
        {"candidate_patch": patch_text}
    )
    packet["base_commit_sha"] = _git(repo, "rev-parse", "HEAD").stdout.strip()
    validated_packet = _validate_packet(packet)
    monkeypatch.setattr(experiment_runner, "MAX_CANDIDATE_PATCH_BYTES", 8)
    monkeypatch.setattr(
        experiment_runner,
        "_evaluate_attempt",
        lambda **_kwargs: pytest.fail("oversized patches must fail before evaluation"),
    )

    result = experiment_runner.evaluate_candidate(validated_packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "policy_violation"
    assert result["mutated_paths"] == []
    assert result["oracle_results"] == []
    assert result["budget_observations"]["attempts"] == 0
    assert result["budget_observations"]["runner_error"] == (
        "Candidate patch exceeds the host fingerprint limit."
    )


def test_evaluate_candidate_rejects_fingerprinted_packet_in_dirty_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fingerprint-bound direct run requires a clean tracked source checkout."""

    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n" "    return 2\n",
        tmp_path / "candidate.patch",
    )
    patch_text = patch_path.read_text(encoding="utf-8")
    packet = _base_packet(
        mutable_path="core/rag/allowed.py",
        oracle_command='python3 -c "raise SystemExit(0)"',
    )
    packet["candidate_patch_fingerprint"] = experiment_runner.fingerprint_payload(
        {"candidate_patch": patch_text}
    )
    packet["base_commit_sha"] = _git(repo, "rev-parse", "HEAD").stdout.strip()
    validated_packet = _validate_packet(packet)
    (repo / "docs" / "orchestration" / "workflow.md").write_text(
        "# Dirty workflow\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        experiment_runner,
        "_evaluate_attempt",
        lambda **_kwargs: pytest.fail("dirty source checkouts must fail before evaluation"),
    )

    result = experiment_runner.evaluate_candidate(validated_packet, patch_path)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "policy_violation"
    assert result["mutated_paths"] == []
    assert result["oracle_results"] == []
    assert result["budget_observations"]["attempts"] == 0
    assert result["budget_observations"]["runner_error"] == (
        "Fingerprinted candidate packets require a clean tracked repository checkout."
    )


@pytest.mark.parametrize(
    "fault", ["clone-interrupted", "checkout-interrupted", "settled-clone", "metadata-error"]
)
def test_checkout_creator_owns_partial_reservation_until_transfer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    repo = tmp_path / "source"
    repo.mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    sibling = scratch / "sibling"
    sibling.write_text("preserve")
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(scratch))
    observed: list[Path] = []

    def native(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "clone" in argv:
            dest = Path(argv[-1])
            dest.mkdir()
            (dest / "partial").write_text("partial clone")
            observed.append(dest.parent)
            if fault == "clone-interrupted":
                raise KeyboardInterrupt()
            code = int(fault == "settled-clone")
        elif "rev-parse" in argv:
            code = int(fault == "metadata-error")
        else:
            assert "checkout" in argv and fault == "checkout-interrupted"
            code = -15
        return subprocess.CompletedProcess(argv, code, stdout="a" * 40, stderr="controlled")

    monkeypatch.setattr(experiment_runner.subprocess, "run", native)
    with pytest.raises((KeyboardInterrupt, experiment_runner.InfraFlakeError)) as failed:
        experiment_runner._create_temp_checkout(repo)
    assert len(observed) == 1
    retained = fault.endswith("interrupted")
    assert observed[0].exists() is retained
    assert getattr(failed.value, "_checkout_uncertain", False) is retained
    if retained:
        assert Path(getattr(failed.value, "_retained_checkout")) == observed[0]
        assert (observed[0] / "checkout/partial").read_text() == "partial clone"
    assert sibling.read_text() == "preserve" and list(repo.iterdir()) == []


@pytest.mark.parametrize("cancel", [False, True])
def test_replaced_checkout_reservation_preserves_sibling_and_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cancel: bool
) -> None:
    source = tmp_path / "source"
    scratch = tmp_path / "scratch"
    source.mkdir()
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(scratch))
    owner = experiment_runner._CheckoutReservation(source)
    original = Path(owner.name)
    original.rename(scratch / "retained")
    original.mkdir()
    (original / "foreign").write_text("untouched")
    if cancel:
        with pytest.raises(KeyboardInterrupt) as caught:
            try:
                raise KeyboardInterrupt()
            except KeyboardInterrupt as primary:
                experiment_runner._finish_checkout(owner, primary)
                raise
        assert getattr(caught.value, "_checkout_uncertain")
        assert any("cleanup failed" in note for note in caught.value.__notes__)
    else:
        with pytest.raises(experiment_runner.InfraFlakeError) as failed:
            experiment_runner._finish_checkout(owner, None)
        assert failed.value._checkout_uncertain
    assert (original / "foreign").read_text() == "untouched" and source.is_dir()


@pytest.mark.parametrize("mode", ["candidate_patch", "oracle_only_governance_reviewer"])
@pytest.mark.parametrize("fault", ["extra-member", "renamed-away"])
def test_unknown_cleanup_blocks_reuse_in_both_runner_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, fault: str
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n    return 2\n",
        patch_path=tmp_path / "uncertain-cleanup.patch",
    )
    packet = _base_packet(
        mutable_path="core/rag/allowed.py", oracle_command='python3 -c "pass"', runner_mode=mode
    )
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(scratch))
    sibling = scratch / "separate"
    sibling.write_text("preserve")
    runs = []

    def synthetic(_packet: dict[str, Any], checkout: Path) -> tuple[list[dict[str, Any]], None]:
        runs.append(checkout)
        if fault == "renamed-away":
            checkout.parent.rename(scratch / "moved-reservation")
        else:
            (checkout.parent / "unexpected").write_text("unknown ownership")
        return [], None

    monkeypatch.setattr(experiment_runner, "_run_oracles", synthetic)
    if mode == "candidate_patch":
        result = experiment_runner.evaluate_candidate(packet, patch_path)
    else:
        result = experiment_runner.evaluate_oracle_only_governance_reviewer(packet)
    assert result["status"] == "rejected" and result["failure_class"] == "infra_flake"
    assert len(runs) == 1
    if fault == "renamed-away":
        assert not runs[0].parent.exists() and (scratch / "moved-reservation/checkout").is_dir()
    else:
        assert (runs[0].parent / "unexpected").is_file()
    assert (
        result["budget_observations"]["runner_error"]
        == "Isolated checkout state is uncertain; retry is blocked."
    )
    assert sibling.read_text() == "preserve" and (repo / "core/rag/allowed.py").is_file()


@pytest.mark.parametrize("mode", ["candidate_patch", "oracle_only_governance_reviewer"])
def test_checkout_retained_when_entered_sandbox_call_is_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n    return 2\n",
        patch_path=tmp_path / "interrupted-sandbox.patch",
    )
    packet = _base_packet(
        mutable_path="core/rag/allowed.py", oracle_command='python3 -c "pass"', runner_mode=mode
    )
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(scratch))
    calls = []

    def synthetic_interruption(*args: object, **kwargs: object) -> SandboxResult:
        checkout = Path(os.environ[experiment_runner.sandbox.SANDBOX_ROOT_ENV])
        calls.append(checkout)
        (checkout / "partial-control").write_text("interrupted fixture")
        raise KeyboardInterrupt()

    monkeypatch.setattr(experiment_runner.sandbox, "run_local_sandbox", synthetic_interruption)
    with pytest.raises(KeyboardInterrupt) as failure:
        if mode == "candidate_patch":
            experiment_runner.evaluate_candidate(packet, patch_path)
        else:
            experiment_runner.evaluate_oracle_only_governance_reviewer(packet)
    assert len(calls) == 1
    assert list(scratch.iterdir()) == [calls[0].parent]
    assert getattr(failure.value, "_retained_checkout") == str(calls[0].parent)
    assert (calls[0] / "partial-control").read_text() == "interrupted fixture"
    assert not (repo / "partial-control").exists()


@pytest.mark.parametrize("operation", ["clone", "checkout", "apply"])
def test_native_signalled_git_writer_is_uncertain_even_without_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    binary = tmp_path / "fixture-git"
    binary.write_text(
        f"#!{sys.executable}\nimport os, signal\nfrom pathlib import Path\n"
        "signal.signal(signal.SIGTERM, signal.SIG_DFL)\nPath('partial').write_text('started')\nos.kill(os.getpid(), signal.SIGTERM)\n"
    )
    binary.chmod(0o700)
    monkeypatch.setattr(experiment_runner, "_resolve_git_binary", lambda: str(binary))
    with pytest.raises(experiment_runner.InfraFlakeError, match="terminated by signal") as failed:
        experiment_runner._run_git([operation], cwd=tmp_path, check=False)
    assert failed.value._checkout_uncertain and (tmp_path / "partial").read_text() == "started"
    readonly = experiment_runner._run_git(["apply", "--check"], cwd=tmp_path, check=False)
    assert readonly.returncode < 0


def test_checkout_identification_failure_releases_fd_and_preserves_private_locator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "source"
    scratch = tmp_path / "scratch"
    root.mkdir()
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(scratch))
    original = os.fstat
    descriptors = []

    def fail(fd: int) -> os.stat_result:
        descriptors.append(fd)
        raise OSError("private-identification-detail")

    with monkeypatch.context() as scoped:
        scoped.setattr(experiment_runner.os, "fstat", fail)
        with pytest.raises(experiment_runner.InfraFlakeError) as caught:
            experiment_runner._CheckoutReservation(root)
    assert caught.value._checkout_uncertain and caught.value._retained_checkout is not None
    assert Path(caught.value._retained_checkout).parent == scratch
    assert list(scratch.iterdir()) == [Path(caught.value._retained_checkout)]
    assert str(scratch) not in str(caught.value) and "private-identification-detail" not in str(
        caught.value
    )
    assert len(descriptors) == 1
    with pytest.raises(OSError):
        original(descriptors[0])


@pytest.mark.parametrize("fault", ["checked", "status"])
@pytest.mark.parametrize("stderr_present", [False, True])
def test_completed_git_failure_keeps_private_process_data_out_of_runner_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, stderr_present: bool
) -> None:
    import traceback

    marker = "synthetic-runner-private"
    repo = _init_repo(tmp_path)
    _configure_runner_repo(monkeypatch, repo)
    patch_path = _write_patch(
        repo,
        "core/rag/allowed.py",
        "def candidate_value() -> int:\n    return 2\n",
        tmp_path / "candidate.patch",
    )
    packet = _validate_packet(
        _base_packet(mutable_path="core/rag/allowed.py", oracle_command='python3 -c "pass"')
    )
    original = subprocess.run
    failed_calls = []

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        in_checkout = Path(kwargs.get("cwd") or repo) != repo
        if marker in argv or (
            in_checkout
            and (
                ("apply" in argv and fault == "checked")
                or (argv[-2:] == ["status", "--short"] and fault == "status")
            )
        ):
            failed_calls.append(1)
            return subprocess.CompletedProcess(
                argv, 23, stdout=marker, stderr=marker if stderr_present else ""
            )
        return original(argv, **kwargs)

    monkeypatch.setattr(experiment_runner.subprocess, "run", run)
    checked_text = "Git operation failed (exit 23)."
    with pytest.raises(experiment_runner.InfraFlakeError) as failed:
        experiment_runner._run_git(["status", marker], cwd=repo)
    assert str(failed.value) == checked_text
    assert marker not in repr(failed.value.args) + repr(failed.value) + "".join(
        traceback.format_exception(failed.value)
    )
    private = experiment_runner._run_git(["status", marker], cwd=repo, check=False)
    assert private.returncode == 23 and private.stdout == marker
    failed_calls.clear()
    monkeypatch.setattr(
        experiment_runner,
        "_run_oracles",
        lambda *_: pytest.fail("Oracle reached after Git failure"),
    )
    result = experiment_runner.evaluate_candidate(packet, patch_path)
    assert result["status"] == "rejected" and result["failure_class"] == "infra_flake"
    expected = checked_text if fault == "checked" else "Git status after patch failed (exit 23)."
    assert result["budget_observations"]["runner_error"] == expected
    assert len(failed_calls) == result["budget_observations"]["attempts"] == 2
    assert result["budget_observations"]["retries_consumed"] == 1
    assert marker not in json.dumps(result)
