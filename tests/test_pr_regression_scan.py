"""Focused tests for the temporary PR regression scanner wrapper."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_SCRIPT = REPO_ROOT / "scripts" / "ci" / "pr_regression_scan.sh"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _run_scan_with_stubbed_tools(
    *,
    args: list[str],
    repo_env: str | None = None,
    github_repository: str | None = None,
) -> str:
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        log_path = tmp_path / "calls.log"

        _write_executable(
            tmp_path / "python3",
            "\n".join(
                [
                    "#!/bin/bash",
                    'printf "python3 %s\\n" "$*" >> "$PR_SCAN_TEST_LOG"',
                    "exit 0",
                ]
            ),
        )
        _write_executable(
            tmp_path / "make",
            "\n".join(
                [
                    "#!/bin/bash",
                    'printf "make %s\\n" "$*" >> "$PR_SCAN_TEST_LOG"',
                    "exit 0",
                ]
            ),
        )
        _write_executable(
            tmp_path / "pre-commit",
            "\n".join(
                [
                    "#!/bin/bash",
                    'printf "pre-commit %s\\n" "$*" >> "$PR_SCAN_TEST_LOG"',
                    "exit 0",
                ]
            ),
        )

        env = os.environ.copy()
        env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
        env["PR_SCAN_TEST_LOG"] = str(log_path)
        env["GH_TOKEN"] = "dummy-token"
        env["RUN_MAIN_SUITE"] = "0"
        if repo_env is None:
            env.pop("REPO", None)
        else:
            env["REPO"] = repo_env
        if github_repository is None:
            env.pop("GITHUB_REPOSITORY", None)
        else:
            env["GITHUB_REPOSITORY"] = github_repository

        subprocess.run(
            ["bash", str(SCAN_SCRIPT), *args],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        return log_path.read_text(encoding="utf-8")


def test_pr_regression_scan_honors_repo_env_override() -> None:
    """REPO env should feed GitHub current-head and merge-readiness checks."""
    calls = _run_scan_with_stubbed_tools(repo_env="custom/Repo", args=["1664"])

    assert (
        "python3 scripts/ci/check_current_head_pr_checks.py " "--pr-number 1664 --repo custom/Repo"
    ) in calls
    assert (
        "python3 scripts/orchestration/check_merge_ready.py "
        "--require-auth --pr-number 1664 --repo custom/Repo"
    ) in calls


def test_pr_regression_scan_cli_repo_arg_overrides_repo_env() -> None:
    """Explicit CLI repo argument should have highest precedence."""
    calls = _run_scan_with_stubbed_tools(
        repo_env="env/Repo",
        args=["1664", "cli/Repo"],
    )

    assert "--repo cli/Repo" in calls
    assert "--repo env/Repo" not in calls


def test_pr_regression_scan_uses_github_repository_fallback() -> None:
    """GITHUB_REPOSITORY should be used when CLI and REPO env are absent."""
    calls = _run_scan_with_stubbed_tools(
        args=["1664"],
        github_repository="github/Repo",
    )

    assert "--repo github/Repo" in calls


def test_pr_regression_scan_uses_default_repo_fallback() -> None:
    """Hardcoded repo fallback should remain explicit and deterministic."""
    calls = _run_scan_with_stubbed_tools(args=["1664"])

    assert "--repo Katsiarynakavaleuskaya/PulsePlate" in calls


def test_make_pr_regression_scan_forwards_repo_before_repo_name() -> None:
    """Make wrapper should pass REPO before legacy REPO_NAME fallback."""
    make_binary = which("make")
    assert make_binary is not None, "Required executable 'make' must be on PATH"

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        log_path = tmp_path / "bash.log"
        _write_executable(
            tmp_path / "bash",
            "\n".join(
                [
                    "#!/bin/bash",
                    'printf "%s\\n" "$*" >> "$PR_SCAN_TEST_LOG"',
                    "exit 0",
                ]
            ),
        )

        env = os.environ.copy()
        env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
        env["PR_SCAN_TEST_LOG"] = str(log_path)
        env["PR_NUMBER"] = "1664"
        env["REPO"] = "repo/Env"
        env["REPO_NAME"] = "legacy/RepoName"

        subprocess.run(
            [make_binary, "-s", "-C", str(REPO_ROOT), "pr-regression-scan"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        assert "scripts/ci/pr_regression_scan.sh 1664 repo/Env" in log_path.read_text(
            encoding="utf-8"
        )


def test_make_pr_regression_scan_preserves_repo_name_fallback() -> None:
    """Legacy REPO_NAME should still work when REPO is unset."""
    make_binary = which("make")
    assert make_binary is not None, "Required executable 'make' must be on PATH"

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        log_path = tmp_path / "bash.log"
        _write_executable(
            tmp_path / "bash",
            "\n".join(
                [
                    "#!/bin/bash",
                    'printf "%s\\n" "$*" >> "$PR_SCAN_TEST_LOG"',
                    "exit 0",
                ]
            ),
        )

        env = os.environ.copy()
        env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
        env["PR_SCAN_TEST_LOG"] = str(log_path)
        env["PR_NUMBER"] = "1664"
        env.pop("REPO", None)
        env["REPO_NAME"] = "legacy/RepoName"

        subprocess.run(
            [make_binary, "-s", "-C", str(REPO_ROOT), "pr-regression-scan"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        assert "scripts/ci/pr_regression_scan.sh 1664 legacy/RepoName" in log_path.read_text(
            encoding="utf-8"
        )
