"""Guards for repo/worktree-aware Python resolution in local hooks."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import shlex
import subprocess
import textwrap

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_RESOLVER = REPO_ROOT / "scripts" / "hooks" / "repo_python.sh"
HOOK_FILES = [
    REPO_ROOT / ".githooks" / "pre-commit",
    REPO_ROOT / ".githooks" / "pre-commit-unified",
]
RESOLVE_COMMAND = f'source {shlex.quote(str(HOOK_RESOLVER))}; resolve_repo_python "$PWD"'


def _write_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


def _write_fake_pytest_python(path: Path, calls_file: Path) -> None:
    path.write_text(
        textwrap.dedent(f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            if [[ "$*" == "-m pytest --version" ]]; then
                echo "pytest 0.0"
                exit 0
            fi
            if [[ "$1" == "-m" && "$2" == "pytest" ]]; then
                shift 2
                printf '%s\\n' "$@" > {shlex.quote(str(calls_file))}
                exit 0
            fi
            echo "unexpected fake python args: $*" >&2
            exit 2
            """),
        encoding="utf-8",
    )
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
    env.pop("PRE_COMMIT", None)
    env.pop("BRANCH_DIFF_MODE", None)
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
        RESOLVE_COMMAND,
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
        RESOLVE_COMMAND,
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
        RESOLVE_COMMAND,
        cwd=repo,
        env=env,
    )

    assert completed.returncode == 1
    assert "must be an absolute executable path" in completed.stderr


def test_hook_resolver_rejects_non_executable_absolute_python_override(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shared_python = repo / ".venv" / "bin" / "python"
    shared_python.parent.mkdir(parents=True)
    _write_executable(shared_python)
    bad_override = tmp_path / "not-python"
    bad_override.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    bad_override.chmod(0o644)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(bad_override)

    completed = _bash_failure(
        RESOLVE_COMMAND,
        cwd=repo,
        env=env,
    )

    assert completed.returncode == 1
    assert "is set but is not executable" in completed.stderr
    assert str(shared_python) not in completed.stdout


def test_hook_resolver_fails_closed_without_repo_python(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = _clean_hook_env()

    completed = _bash_failure(
        RESOLVE_COMMAND,
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


def test_backend_hook_maps_frontend_lockfile_changes_to_governance_tests(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate Hook Resolver")
    (repo / "scripts" / "hooks").mkdir(parents=True)
    shutil.copy2(HOOK_RESOLVER, repo / "scripts" / "hooks" / "repo_python.sh")
    shutil.copy2(
        REPO_ROOT / "scripts" / "run-backend-tests-pre-commit.sh",
        repo / "scripts" / "run-backend-tests-pre-commit.sh",
    )
    (repo / "frontend").mkdir()
    (repo / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion":3}\n', encoding="utf-8"
    )
    (repo / "frontend" / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    _git(repo, "switch", "--quiet", "-c", "package-lock-change")
    (repo / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion":3,"t":1}\n', encoding="utf-8"
    )
    _git(repo, "add", "frontend/package-lock.json")
    _git(repo, "commit", "--quiet", "-m", "update frontend lockfile")
    calls_file = tmp_path / "pytest-args.txt"
    fake_python = tmp_path / "fake-python"
    _write_fake_pytest_python(fake_python, calls_file)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(fake_python)

    output = _bash(
        "BRANCH_DIFF_MODE=1 bash scripts/run-backend-tests-pre-commit.sh",
        cwd=repo,
        env=env,
    )

    called_args = calls_file.read_text(encoding="utf-8").splitlines()
    assert "tests/test_ci_workflow_pr_size_governance_contract.py" in called_args
    assert "tests/test_frontend_dependency_guards.py" in called_args
    assert "tests/test_python_supply_chain_controls.py" in called_args
    assert "Backend tests passed" in output


def test_backend_hook_preserves_upstream_frontend_package_delta(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate Hook Resolver")
    _git(repo, "branch", "-M", "main")
    (repo / "scripts" / "hooks").mkdir(parents=True)
    shutil.copy2(HOOK_RESOLVER, repo / "scripts" / "hooks" / "repo_python.sh")
    shutil.copy2(
        REPO_ROOT / "scripts" / "run-backend-tests-pre-commit.sh",
        repo / "scripts" / "run-backend-tests-pre-commit.sh",
    )
    (repo / "frontend").mkdir()
    (repo / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion":3}\n', encoding="utf-8"
    )
    (repo / "frontend" / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    _git(repo, "switch", "--quiet", "-c", "package-lock-change")
    (repo / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion":3,"remote":1}\n', encoding="utf-8"
    )
    _git(repo, "add", "frontend/package-lock.json")
    _git(repo, "commit", "--quiet", "-m", "remote frontend lockfile delta")
    _git(repo, "update-ref", "refs/remotes/origin/package-lock-change", "HEAD")
    _git(repo, "config", "branch.package-lock-change.remote", "origin")
    _git(repo, "config", "branch.package-lock-change.merge", "refs/heads/package-lock-change")
    (repo / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion":3}\n', encoding="utf-8"
    )
    _git(repo, "add", "frontend/package-lock.json")
    _git(repo, "commit", "--quiet", "-m", "revert frontend lockfile to main")
    calls_file = tmp_path / "pytest-upstream-args.txt"
    fake_python = tmp_path / "fake-python-upstream"
    _write_fake_pytest_python(fake_python, calls_file)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(fake_python)

    output = _bash("bash scripts/run-backend-tests-pre-commit.sh", cwd=repo, env=env)

    called_args = calls_file.read_text(encoding="utf-8").splitlines()
    assert "tests/test_ci_workflow_pr_size_governance_contract.py" in called_args
    assert "tests/test_frontend_dependency_guards.py" in called_args
    assert "tests/test_python_supply_chain_controls.py" in called_args
    assert "Backend tests passed" in output


def test_backend_hook_maps_upstream_frontend_package_deletion_to_governance_tests(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate Hook Resolver")
    _git(repo, "branch", "-M", "main")
    (repo / "scripts" / "hooks").mkdir(parents=True)
    shutil.copy2(HOOK_RESOLVER, repo / "scripts" / "hooks" / "repo_python.sh")
    shutil.copy2(
        REPO_ROOT / "scripts" / "run-backend-tests-pre-commit.sh",
        repo / "scripts" / "run-backend-tests-pre-commit.sh",
    )
    (repo / "frontend").mkdir()
    (repo / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion":3}\n', encoding="utf-8"
    )
    (repo / "frontend" / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    _git(repo, "switch", "--quiet", "-c", "package-lock-delete")
    _git(repo, "update-ref", "refs/remotes/origin/package-lock-delete", "HEAD")
    _git(repo, "config", "branch.package-lock-delete.remote", "origin")
    _git(
        repo,
        "config",
        "branch.package-lock-delete.merge",
        "refs/heads/package-lock-delete",
    )
    _git(repo, "rm", "--quiet", "frontend/package-lock.json")
    _git(repo, "commit", "--quiet", "-m", "delete frontend lockfile")
    calls_file = tmp_path / "pytest-upstream-delete-args.txt"
    fake_python = tmp_path / "fake-python-upstream-delete"
    _write_fake_pytest_python(fake_python, calls_file)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(fake_python)

    output = _bash("bash scripts/run-backend-tests-pre-commit.sh", cwd=repo, env=env)

    called_args = calls_file.read_text(encoding="utf-8").splitlines()
    assert "tests/test_ci_workflow_pr_size_governance_contract.py" in called_args
    assert "tests/test_frontend_dependency_guards.py" in called_args
    assert "tests/test_python_supply_chain_controls.py" in called_args
    assert "Backend tests passed" in output


def test_backend_hook_maps_upstream_frontend_package_rename_to_governance_tests(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate Hook Resolver")
    _git(repo, "branch", "-M", "main")
    (repo / "scripts" / "hooks").mkdir(parents=True)
    shutil.copy2(HOOK_RESOLVER, repo / "scripts" / "hooks" / "repo_python.sh")
    shutil.copy2(
        REPO_ROOT / "scripts" / "run-backend-tests-pre-commit.sh",
        repo / "scripts" / "run-backend-tests-pre-commit.sh",
    )
    (repo / "frontend").mkdir()
    (repo / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion":3}\n', encoding="utf-8"
    )
    (repo / "frontend" / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    _git(repo, "switch", "--quiet", "-c", "package-lock-rename")
    _git(repo, "update-ref", "refs/remotes/origin/package-lock-rename", "HEAD")
    _git(repo, "config", "branch.package-lock-rename.remote", "origin")
    _git(
        repo,
        "config",
        "branch.package-lock-rename.merge",
        "refs/heads/package-lock-rename",
    )
    _git(repo, "mv", "frontend/package-lock.json", "frontend/package-lock.old")
    _git(repo, "commit", "--quiet", "-m", "rename frontend lockfile")
    calls_file = tmp_path / "pytest-upstream-rename-args.txt"
    fake_python = tmp_path / "fake-python-upstream-rename"
    _write_fake_pytest_python(fake_python, calls_file)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(fake_python)

    output = _bash("bash scripts/run-backend-tests-pre-commit.sh", cwd=repo, env=env)

    called_args = calls_file.read_text(encoding="utf-8").splitlines()
    assert "tests/test_ci_workflow_pr_size_governance_contract.py" in called_args
    assert "tests/test_frontend_dependency_guards.py" in called_args
    assert "tests/test_python_supply_chain_controls.py" in called_args
    assert "Backend tests passed" in output


def test_backend_hook_maps_upstream_frontend_package_type_change_to_governance_tests(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate Hook Resolver")
    _git(repo, "branch", "-M", "main")
    (repo / "scripts" / "hooks").mkdir(parents=True)
    shutil.copy2(HOOK_RESOLVER, repo / "scripts" / "hooks" / "repo_python.sh")
    shutil.copy2(
        REPO_ROOT / "scripts" / "run-backend-tests-pre-commit.sh",
        repo / "scripts" / "run-backend-tests-pre-commit.sh",
    )
    (repo / "frontend").mkdir()
    (repo / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion":3}\n', encoding="utf-8"
    )
    (repo / "frontend" / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    _git(repo, "switch", "--quiet", "-c", "package-lock-type-change")
    _git(repo, "update-ref", "refs/remotes/origin/package-lock-type-change", "HEAD")
    _git(repo, "config", "branch.package-lock-type-change.remote", "origin")
    _git(
        repo,
        "config",
        "branch.package-lock-type-change.merge",
        "refs/heads/package-lock-type-change",
    )
    (repo / "frontend" / "package-lock.json").unlink()
    (repo / "frontend" / "package-lock.json").symlink_to("package-lock.actual.json")
    (repo / "frontend" / "package-lock.actual.json").write_text(
        '{"lockfileVersion":3}\n', encoding="utf-8"
    )
    _git(repo, "add", "frontend/package-lock.json", "frontend/package-lock.actual.json")
    _git(repo, "commit", "--quiet", "-m", "change frontend lockfile type")
    calls_file = tmp_path / "pytest-upstream-type-change-args.txt"
    fake_python = tmp_path / "fake-python-upstream-type-change"
    _write_fake_pytest_python(fake_python, calls_file)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(fake_python)

    output = _bash("bash scripts/run-backend-tests-pre-commit.sh", cwd=repo, env=env)

    called_args = calls_file.read_text(encoding="utf-8").splitlines()
    assert "tests/test_ci_workflow_pr_size_governance_contract.py" in called_args
    assert "tests/test_frontend_dependency_guards.py" in called_args
    assert "tests/test_python_supply_chain_controls.py" in called_args
    assert "Backend tests passed" in output


def test_backend_hook_maps_staged_frontend_package_changes_to_governance_tests(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate Hook Resolver")
    (repo / "scripts" / "hooks").mkdir(parents=True)
    shutil.copy2(HOOK_RESOLVER, repo / "scripts" / "hooks" / "repo_python.sh")
    shutil.copy2(
        REPO_ROOT / "scripts" / "run-backend-tests-pre-commit.sh",
        repo / "scripts" / "run-backend-tests-pre-commit.sh",
    )
    (repo / "frontend").mkdir()
    (repo / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion":3}\n', encoding="utf-8"
    )
    (repo / "frontend" / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    (repo / "frontend" / "package.json").write_text(
        '{"name":"pulseplate-test"}\n', encoding="utf-8"
    )
    _git(repo, "add", "frontend/package.json")
    calls_file = tmp_path / "pytest-staged-args.txt"
    fake_python = tmp_path / "fake-python-staged"
    _write_fake_pytest_python(fake_python, calls_file)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(fake_python)
    env["PRE_COMMIT"] = "1"

    output = _bash("bash scripts/run-backend-tests-pre-commit.sh", cwd=repo, env=env)

    called_args = calls_file.read_text(encoding="utf-8").splitlines()
    assert "tests/test_ci_workflow_pr_size_governance_contract.py" in called_args
    assert "tests/test_frontend_dependency_guards.py" in called_args
    assert "tests/test_python_supply_chain_controls.py" in called_args
    assert "Backend tests passed" in output


def test_backend_hook_maps_staged_frontend_package_rename_to_governance_tests(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate Hook Resolver")
    (repo / "scripts" / "hooks").mkdir(parents=True)
    shutil.copy2(HOOK_RESOLVER, repo / "scripts" / "hooks" / "repo_python.sh")
    shutil.copy2(
        REPO_ROOT / "scripts" / "run-backend-tests-pre-commit.sh",
        repo / "scripts" / "run-backend-tests-pre-commit.sh",
    )
    (repo / "frontend").mkdir()
    (repo / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion":3}\n', encoding="utf-8"
    )
    (repo / "frontend" / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    _git(repo, "mv", "frontend/package-lock.json", "frontend/package-lock.old")
    calls_file = tmp_path / "pytest-staged-rename-args.txt"
    fake_python = tmp_path / "fake-python-staged-rename"
    _write_fake_pytest_python(fake_python, calls_file)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(fake_python)
    env["PRE_COMMIT"] = "1"

    output = _bash("bash scripts/run-backend-tests-pre-commit.sh", cwd=repo, env=env)

    called_args = calls_file.read_text(encoding="utf-8").splitlines()
    assert "tests/test_ci_workflow_pr_size_governance_contract.py" in called_args
    assert "tests/test_frontend_dependency_guards.py" in called_args
    assert "tests/test_python_supply_chain_controls.py" in called_args
    assert "Backend tests passed" in output


def test_pre_commit_config_runs_backend_hook_for_frontend_package_manifests() -> None:
    config_text = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "frontend/package(?:-lock)?\\.json" in config_text
    assert "always_run: true" in config_text


def test_makefile_hook_targets_use_shared_python_resolver() -> None:
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "HOOK_REPO_PYTHON = . scripts/hooks/repo_python.sh" in makefile_text
    assert 'VENV_PYTHON="$$($(HOOK_REPO_PYTHON))"' in makefile_text
    assert '"$$($(HOOK_REPO_PYTHON))" -m pre_commit run --all-files' in makefile_text
