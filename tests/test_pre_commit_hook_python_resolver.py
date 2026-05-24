"""Guards for repo/worktree-aware Python resolution in local hooks."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_RESOLVER = REPO_ROOT / "scripts" / "hooks" / "repo_python.sh"
HOOK_FILES = [
    REPO_ROOT / ".githooks" / "pre-commit",
    REPO_ROOT / ".githooks" / "pre-commit-unified",
]


def _write_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    git_binary = shutil.which("git")
    assert git_binary is not None, "git binary is required for hook resolver tests"
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.run(
        [git_binary, *args],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def _clean_hook_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.pop("VENV_PYTHON", None)
    env.pop("DEV_PYTHON", None)
    env.pop("CI", None)
    return env


def _bash(command: str, *, cwd: Path, env: dict[str, str] | None = None) -> str:
    bash_binary = shutil.which("bash")
    assert bash_binary is not None, "bash binary is required for hook resolver tests"
    completed = subprocess.run(
        [bash_binary, "-lc", command],
        cwd=str(cwd),
        env=env or _clean_hook_env(),
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _bash_failure(
    command: str, *, cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    bash_binary = shutil.which("bash")
    assert bash_binary is not None, "bash binary is required for hook resolver tests"
    return subprocess.run(
        [bash_binary, "-lc", command],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_hook_resolver_prefers_shared_root_venv_from_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate Hook Resolver")
    (repo / "README.md").write_text("hook resolver test\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "--quiet", "-m", "init")
    shared_python = repo / ".venv" / "bin" / "python"
    shared_python.parent.mkdir(parents=True)
    _write_executable(shared_python)
    worktree = repo / "worktrees" / "lane"
    _git(repo, "worktree", "add", "--quiet", str(worktree), "HEAD")

    resolved = _bash(
        f'source {HOOK_RESOLVER}; resolve_repo_python "$PWD"',
        cwd=worktree,
    )

    assert resolved == str(shared_python)


def test_hook_resolver_ignores_commit_hook_git_env_for_worktree_lookup(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate Hook Resolver")
    (repo / "README.md").write_text("hook resolver test\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "--quiet", "-m", "init")
    shared_python = repo / ".venv" / "bin" / "python"
    shared_python.parent.mkdir(parents=True)
    _write_executable(shared_python)
    worktree = repo / "worktrees" / "lane"
    _git(repo, "worktree", "add", "--quiet", str(worktree), "HEAD")
    env = _clean_hook_env()
    env["GIT_DIR"] = str(repo / ".git")
    env["GIT_INDEX_FILE"] = str(repo / ".git" / "index")

    resolved = _bash(
        f'source {HOOK_RESOLVER}; resolve_repo_python "$PWD"',
        cwd=worktree,
        env=env,
    )

    assert resolved == str(shared_python)


def test_hook_resolver_rejects_relative_python_override(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = _clean_hook_env()
    env["VENV_PYTHON"] = ".venv/bin/python"

    completed = _bash_failure(
        f'source {HOOK_RESOLVER}; resolve_repo_python "$PWD"',
        cwd=repo,
        env=env,
    )

    assert completed.returncode == 1
    assert "must be an absolute executable path" in completed.stderr


def test_hook_resolver_fails_closed_without_repo_python(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = _clean_hook_env()

    completed = _bash_failure(
        f'source {HOOK_RESOLVER}; resolve_repo_python "$PWD"',
        cwd=repo,
        env=env,
    )

    assert completed.returncode == 1
    assert "no repo/shared .venv Python found" in completed.stderr


def test_hook_entrypoints_use_repo_python_for_python_tools() -> None:
    for hook_file in HOOK_FILES:
        text = hook_file.read_text(encoding="utf-8")
        assert "scripts/hooks/repo_python.sh" in text
        assert 'export VENV_PYTHON="$REPO_PYTHON_BIN"' in text
        assert '"$REPO_PYTHON_BIN" -m py_compile' in text
        assert '"$REPO_PYTHON_BIN" -m pytest' in text
        assert '"$REPO_PYTHON_BIN" -m pre_commit' in text
        assert "not available through repo Python" in text


def test_backend_hook_honors_skip_tests_before_python_resolution() -> None:
    hook_text = (REPO_ROOT / "scripts" / "run-backend-tests-pre-commit.sh").read_text(
        encoding="utf-8"
    )

    skip_index = hook_text.index('if [ "${SKIP_TESTS:-0}" = "1" ]; then')
    resolver_index = hook_text.index('source "$ROOT_DIR/scripts/hooks/repo_python.sh"')
    pytest_index = hook_text.index('"$REPO_PYTHON_BIN" -m pytest --version')

    assert skip_index < resolver_index < pytest_index


def test_makefile_hook_targets_use_shared_python_resolver() -> None:
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "HOOK_REPO_PYTHON = . scripts/hooks/repo_python.sh" in makefile_text
    assert 'VENV_PYTHON="$$($(HOOK_REPO_PYTHON))"' in makefile_text
    assert '"$$($(HOOK_REPO_PYTHON))" -m pre_commit run --all-files' in makefile_text
