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


def test_hook_resolver_prefers_root_checkout_venv(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(tmp_path, "init", "--quiet", str(repo))
    checkout_python = repo / ".venv" / "bin" / "python"
    checkout_python.parent.mkdir(parents=True)
    _write_executable(checkout_python)

    resolved = _bash(RESOLVE_COMMAND, cwd=repo)

    assert resolved == str(checkout_python)


def test_hook_resolver_finds_primary_venv_from_arbitrary_worktree_locations(
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
    worktrees = [
        repo / "worktrees" / "lane",
        repo / "nested" / "linked" / "lane",
        repo.parent / "sibling-lane",
        tmp_path / "external" / "arbitrary" / "lane",
        tmp_path / "external with spaces" / "linked lane",
    ]

    for worktree in worktrees:
        _git(repo, "worktree", "add", "--detach", "--quiet", str(worktree), "HEAD")

        resolved = _bash(
            RESOLVE_COMMAND,
            cwd=worktree,
        )

        assert resolved == str(shared_python)

    worktree_alias = tmp_path / "external-worktree-alias"
    worktree_alias.symlink_to(worktrees[-1], target_is_directory=True)
    alias_command = (
        f"source {shlex.quote(str(HOOK_RESOLVER))}; "
        f"resolve_repo_python {shlex.quote(str(worktree_alias))}"
    )

    assert _bash(alias_command, cwd=repo) == str(shared_python)


def test_hook_resolver_sanitizes_commit_hook_git_env_for_every_git_query(
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
    worktree = tmp_path / "external" / "lane"
    _git(repo, "worktree", "add", "--detach", "--quiet", str(worktree), "HEAD")
    env = _clean_hook_env()
    poisoned = str(tmp_path / "poisoned-git-state")
    env.update(
        {
            "GIT_DIR": poisoned,
            "GIT_WORK_TREE": poisoned,
            "GIT_INDEX_FILE": poisoned,
            "GIT_PREFIX": poisoned,
            "GIT_COMMON_DIR": poisoned,
            "GIT_IMPLICIT_WORK_TREE": "0",
        }
    )

    resolved = _bash(
        RESOLVE_COMMAND,
        cwd=worktree,
        env=env,
    )

    assert resolved == str(shared_python)


def test_hook_resolver_accepts_relative_reciprocal_worktree_metadata(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "primary checkout"
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
    worktree = tmp_path / "external relative linked lane"
    _git(repo, "worktree", "add", "--detach", "--quiet", str(worktree), "HEAD")
    checkout_git_dir = Path(
        _git(
            worktree,
            "rev-parse",
            "--path-format=absolute",
            "--git-dir",
        ).stdout.strip()
    )
    relative_admin_dir = os.path.relpath(checkout_git_dir, start=worktree)
    (worktree / ".git").write_text(
        f"gitdir: {relative_admin_dir}\n",
        encoding="utf-8",
    )
    relative_backlink = os.path.relpath(worktree / ".git", start=checkout_git_dir)
    (checkout_git_dir / "gitdir").write_text(
        f"{relative_backlink}\n",
        encoding="utf-8",
    )

    resolved = _bash(RESOLVE_COMMAND, cwd=worktree)

    assert resolved == str(shared_python)


def test_hook_resolver_rejects_shell_function_tool_interposition(
    tmp_path: Path,
) -> None:
    apparent_checkout = tmp_path / "apparent-checkout"
    apparent_checkout.mkdir()
    decoy_root = tmp_path / "decoy-root"
    (decoy_root / ".git" / "worktrees" / "lane").mkdir(parents=True)
    decoy_python = decoy_root / ".venv" / "bin" / "python"
    decoy_python.parent.mkdir(parents=True)
    _write_executable(decoy_python)
    env = _clean_hook_env()
    env.update(
        {
            "DECOY_ROOT": str(decoy_root),
            "GIT_DIR": str(tmp_path / "poisoned-git-dir"),
            "GIT_WORK_TREE": str(tmp_path / "poisoned-work-tree"),
            "GIT_INDEX_FILE": str(tmp_path / "poisoned-index"),
            "GIT_PREFIX": "poisoned-prefix",
            "GIT_COMMON_DIR": str(tmp_path / "poisoned-common-dir"),
            "GIT_IMPLICIT_WORK_TREE": "0",
        }
    )
    command = f"""
        env() {{
            case "$*" in
                *--git-common-dir*) printf '%s\\n' "$DECOY_ROOT/.git" ;;
                *--git-dir*) printf '%s\\n' "$DECOY_ROOT/.git/worktrees/lane" ;;
                *--show-toplevel*)
                    if [[ "$*" == *"-C $DECOY_ROOT "* ]]; then
                        printf '%s\\n' "$DECOY_ROOT"
                    else
                        printf '%s\\n' "$PWD"
                    fi
                    ;;
                *) return 1 ;;
            esac
        }}
        basename() {{ printf '%s\\n' '.git'; }}
        dirname() {{ printf '%s\\n' "$DECOY_ROOT"; }}
        cd() {{ builtin cd -- "$DECOY_ROOT"; }}
        pwd() {{ printf '%s\\n' "$DECOY_ROOT"; }}
        {RESOLVE_COMMAND}
    """

    completed = _bash_failure(
        command,
        cwd=apparent_checkout,
        env=env,
    )

    assert completed.returncode == 1
    assert str(decoy_python) not in completed.stdout
    assert "no repo/shared .venv Python found" in completed.stderr


def test_hook_resolver_ignores_command_function_tool_lookup_interposition(
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
    worktree = tmp_path / "external-linked-lane"
    _git(repo, "worktree", "add", "--detach", "--quiet", str(worktree), "HEAD")
    fake_env = tmp_path / "fake-env"
    fake_git = tmp_path / "fake-git"
    _write_executable(fake_env)
    _write_executable(fake_git)
    env = _clean_hook_env()
    env.update({"FAKE_ENV": str(fake_env), "FAKE_GIT": str(fake_git)})
    command = f"""
        command() {{
            case "$*" in
                "-v env") printf '%s\\n' "$FAKE_ENV" ;;
                "-v git") printf '%s\\n' "$FAKE_GIT" ;;
                *) return 1 ;;
            esac
        }}
        {RESOLVE_COMMAND}
    """

    resolved = _bash(command, cwd=worktree, env=env)

    assert resolved == str(shared_python)


def test_hook_resolver_prefers_current_worktree_venv_symlink_to_primary_venv(
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
    worktree = tmp_path / "external" / "lane"
    _git(repo, "worktree", "add", "--detach", "--quiet", str(worktree), "HEAD")
    local_python = worktree / ".venv" / "bin" / "python"
    local_python.parent.mkdir(parents=True)
    local_python.symlink_to(shared_python)

    resolved = _bash(RESOLVE_COMMAND, cwd=worktree)

    assert resolved == str(local_python)


def test_hook_resolver_prefers_valid_venv_override(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    checkout_python = repo / ".venv" / "bin" / "python"
    checkout_python.parent.mkdir(parents=True)
    _write_executable(checkout_python)
    dev_override = tmp_path / "dev-python"
    _write_executable(dev_override)
    venv_override = tmp_path / "venv-python"
    _write_executable(venv_override)
    env = _clean_hook_env()
    env["DEV_PYTHON"] = str(dev_override)
    env["VENV_PYTHON"] = str(venv_override)

    resolved = _bash(RESOLVE_COMMAND, cwd=repo, env=env)

    assert resolved == str(venv_override)


def test_hook_resolver_uses_valid_dev_override_when_venv_override_is_unset(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    dev_override = tmp_path / "dev-python"
    _write_executable(dev_override)
    env = _clean_hook_env()
    env["DEV_PYTHON"] = str(dev_override)

    resolved = _bash(RESOLVE_COMMAND, cwd=repo, env=env)

    assert resolved == str(dev_override)


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
    assert "is set but is not a regular executable file" in completed.stderr
    assert str(shared_python) not in completed.stdout


def test_hook_resolver_rejects_directory_python_override(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    directory_override = tmp_path / "python-directory"
    directory_override.mkdir()
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(directory_override)

    completed = _bash_failure(
        RESOLVE_COMMAND,
        cwd=repo,
        env=env,
    )

    assert completed.returncode == 1
    assert "is set but is not a regular executable file" in completed.stderr


def test_hook_resolver_rejects_directory_checkout_python(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    directory_python = repo / ".venv" / "bin" / "python"
    directory_python.mkdir(parents=True)

    completed = _bash_failure(
        RESOLVE_COMMAND,
        cwd=repo,
        env=_clean_hook_env(),
    )

    assert completed.returncode == 1
    assert "no repo/shared .venv Python found" in completed.stderr


def test_hook_resolver_rejects_bare_dot_git_decoy(tmp_path: Path) -> None:
    decoy_root = tmp_path / "decoy-root"
    decoy_root.mkdir()
    _git(tmp_path, "init", "--bare", "--quiet", str(decoy_root / ".git"))
    shared_python = decoy_root / ".venv" / "bin" / "python"
    shared_python.parent.mkdir(parents=True)
    _write_executable(shared_python)
    apparent_worktree = decoy_root / "linked" / "lane"
    apparent_worktree.mkdir(parents=True)

    completed = _bash_failure(
        RESOLVE_COMMAND,
        cwd=apparent_worktree,
        env=_clean_hook_env(),
    )

    assert completed.returncode == 1
    assert str(shared_python) not in completed.stdout


def test_hook_resolver_rejects_ordinary_non_git_dot_git_decoy(tmp_path: Path) -> None:
    decoy_root = tmp_path / "decoy-root"
    (decoy_root / ".git").mkdir(parents=True)
    shared_python = decoy_root / ".venv" / "bin" / "python"
    shared_python.parent.mkdir(parents=True)
    _write_executable(shared_python)
    apparent_worktree = decoy_root / "linked" / "lane"
    apparent_worktree.mkdir(parents=True)

    completed = _bash_failure(
        RESOLVE_COMMAND,
        cwd=apparent_worktree,
        env=_clean_hook_env(),
    )

    assert completed.returncode == 1
    assert str(shared_python) not in completed.stdout


def test_hook_resolver_rejects_forged_linked_worktree_gitdir_file(
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
    real_worktree = tmp_path / "real-linked-worktree"
    _git(repo, "worktree", "add", "--detach", "--quiet", str(real_worktree), "HEAD")
    forged_checkout = tmp_path / "forged-checkout"
    forged_checkout.mkdir()
    shutil.copy2(real_worktree / ".git", forged_checkout / ".git")
    symlinked_forged_checkout = tmp_path / "symlinked-forged-checkout"
    symlinked_forged_checkout.mkdir()
    (symlinked_forged_checkout / ".git").symlink_to(real_worktree / ".git")

    for checkout in (forged_checkout, symlinked_forged_checkout):
        completed = _bash_failure(
            RESOLVE_COMMAND,
            cwd=checkout,
            env=_clean_hook_env(),
        )

        assert completed.returncode == 1
        assert str(shared_python) not in completed.stdout
        assert "no repo/shared .venv Python found" in completed.stderr


def test_hook_resolver_rejects_separate_git_dir_as_primary_checkout(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "separate-worktree"
    decoy_root = tmp_path / "decoy-root"
    decoy_root.mkdir()
    separate_git_dir = decoy_root / ".git"
    _git(
        tmp_path,
        "init",
        "--quiet",
        f"--separate-git-dir={separate_git_dir}",
        str(repo),
    )
    decoy_python = decoy_root / ".venv" / "bin" / "python"
    decoy_python.parent.mkdir(parents=True)
    _write_executable(decoy_python)

    completed = _bash_failure(
        RESOLVE_COMMAND,
        cwd=repo,
        env=_clean_hook_env(),
    )

    assert completed.returncode == 1
    assert str(decoy_python) not in completed.stdout


def test_hook_resolver_allows_ambient_python_only_in_ci(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = _clean_hook_env()
    env["CI"] = "true"

    resolved = Path(_bash(RESOLVE_COMMAND, cwd=repo, env=env))

    assert resolved.is_absolute()
    assert resolved.is_file()
    assert os.access(resolved, os.X_OK)
    assert resolved.name in {"python3", "python"}


def test_hook_resolver_ci_rejects_shell_function_python_interposition(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = _clean_hook_env()
    env["CI"] = "true"
    command = f"python3() {{ :; }}; python() {{ :; }}; {RESOLVE_COMMAND}"

    completed = _bash_failure(
        command,
        cwd=repo,
        env=env,
    )

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "no repo/shared .venv Python found" in completed.stderr


def test_hook_resolver_ci_ignores_command_function_python_lookup_interposition(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    fake_python3 = tmp_path / "fake-python3"
    fake_python = tmp_path / "fake-python"
    _write_executable(fake_python3)
    _write_executable(fake_python)
    env = _clean_hook_env()
    env.update(
        {
            "CI": "true",
            "FAKE_PYTHON3": str(fake_python3),
            "FAKE_PYTHON": str(fake_python),
        }
    )
    command = f"""
        command() {{
            case "$*" in
                "-v python3") printf '%s\\n' "$FAKE_PYTHON3" ;;
                "-v python") printf '%s\\n' "$FAKE_PYTHON" ;;
                *) return 1 ;;
            esac
        }}
        {RESOLVE_COMMAND}
    """

    resolved = Path(_bash(command, cwd=repo, env=env))

    assert resolved not in {fake_python3, fake_python}
    assert resolved.is_absolute()
    assert resolved.is_file()
    assert os.access(resolved, os.X_OK)


def test_hook_resolver_rejects_ambient_python_outside_ci(tmp_path: Path) -> None:
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


def test_backend_hook_skips_unrelated_staged_changes_without_repo_python(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate Hook Resolver")
    (repo / "scripts").mkdir()
    shutil.copy2(
        REPO_ROOT / "scripts" / "run-backend-tests-pre-commit.sh",
        repo / "scripts" / "run-backend-tests-pre-commit.sh",
    )
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    (repo / "docs").mkdir()
    (repo / "docs" / "note.md").write_text("docs-only\n", encoding="utf-8")
    _git(repo, "add", "docs/note.md")
    env = _clean_hook_env()
    env["PRE_COMMIT"] = "1"

    output = _bash("bash scripts/run-backend-tests-pre-commit.sh", cwd=repo, env=env)

    assert "No Python or cross-surface governance files changed" in output


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


def test_backend_hook_maps_all_files_frontend_package_delta_to_governance_tests(
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
    _git(repo, "switch", "--quiet", "-c", "package-lock-all-files")
    (repo / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion":3,"allFiles":1}\n', encoding="utf-8"
    )
    _git(repo, "add", "frontend/package-lock.json")
    _git(repo, "commit", "--quiet", "-m", "update frontend lockfile")
    calls_file = tmp_path / "pytest-all-files-args.txt"
    fake_python = tmp_path / "fake-python-all-files"
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


def test_backend_hook_all_files_keeps_branch_manifest_delta_with_unrelated_staged_file(
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
    _git(repo, "switch", "--quiet", "-c", "package-lock-all-files")
    (repo / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion":3,"allFiles":1}\n', encoding="utf-8"
    )
    _git(repo, "add", "frontend/package-lock.json")
    _git(repo, "commit", "--quiet", "-m", "update frontend lockfile")
    (repo / "docs").mkdir()
    (repo / "docs" / "note.md").write_text("docs-only\n", encoding="utf-8")
    _git(repo, "add", "docs/note.md")
    calls_file = tmp_path / "pytest-all-files-staged-args.txt"
    fake_python = tmp_path / "fake-python-all-files-staged"
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


def test_backend_pre_commit_maps_python_dependency_surface_to_ci_lite_safe_guards(
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
    (repo / "requirements-test.in").write_text("pytest~=9.1.1\n", encoding="utf-8")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    (repo / "requirements-test.in").write_text(
        "httpx2>=2.3.0,<2.4.0\npytest~=9.1.1\n",
        encoding="utf-8",
    )
    _git(repo, "add", "requirements-test.in")
    calls_file = tmp_path / "pytest-dependency-surface-args.txt"
    fake_python = tmp_path / "fake-python-dependency-surface"
    _write_fake_pytest_python(fake_python, calls_file)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(fake_python)
    env["PRE_COMMIT"] = "1"

    output = _bash("bash scripts/run-backend-tests-pre-commit.sh", cwd=repo, env=env)

    called_args = calls_file.read_text(encoding="utf-8").splitlines()
    assert "tests/compat/test_starlette_httpx2_testclient_compat.py" not in called_args
    assert "tests/test_httpx_testclient_compat_guard.py" in called_args
    assert "tests/test_python_dependency_surfaces.py" in called_args
    assert "tests/test_python_supply_chain_controls.py" in called_args
    assert "Backend tests passed" in output


def test_backend_pre_commit_skips_httpx2_canary_direct_collection(
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
    (repo / "tests" / "compat").mkdir(parents=True)
    canary = repo / "tests" / "compat" / "test_starlette_httpx2_testclient_compat.py"
    canary.write_text("def test_initial():\n    assert True\n", encoding="utf-8")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    canary.write_text(
        "def test_initial():\n    assert True\n\n" "def test_changed():\n    assert True\n",
        encoding="utf-8",
    )
    _git(repo, "add", "tests/compat/test_starlette_httpx2_testclient_compat.py")
    calls_file = tmp_path / "pytest-httpx2-canary-pre-commit-args.txt"
    fake_python = tmp_path / "fake-python-httpx2-canary-pre-commit"
    _write_fake_pytest_python(fake_python, calls_file)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(fake_python)
    env["PRE_COMMIT"] = "1"

    output = _bash("bash scripts/run-backend-tests-pre-commit.sh", cwd=repo, env=env)

    called_args = calls_file.read_text(encoding="utf-8").splitlines()
    assert "tests/compat/test_starlette_httpx2_testclient_compat.py" not in called_args
    assert "tests/test_httpx_testclient_compat_guard.py" in called_args
    assert "tests/test_python_dependency_surfaces.py" in called_args
    assert "tests/test_python_supply_chain_controls.py" in called_args
    assert "Backend tests passed" in output


def test_backend_branch_diff_maps_python_dependency_surface_to_testclient_canary(
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
    (repo / "requirements-test.in").write_text("pytest~=9.1.1\n", encoding="utf-8")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    _git(repo, "checkout", "--quiet", "-b", "feature")
    (repo / "requirements-test.in").write_text(
        "httpx2>=2.3.0,<2.4.0\npytest~=9.1.1\n",
        encoding="utf-8",
    )
    _git(repo, "add", "requirements-test.in")
    _git(repo, "commit", "--quiet", "-m", "add httpx2 test backend")
    calls_file = tmp_path / "pytest-dependency-surface-branch-diff-args.txt"
    fake_python = tmp_path / "fake-python-dependency-surface-branch-diff"
    _write_fake_pytest_python(fake_python, calls_file)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(fake_python)
    env["BRANCH_DIFF_MODE"] = "1"

    output = _bash("bash scripts/run-backend-tests-pre-commit.sh", cwd=repo, env=env)

    called_args = calls_file.read_text(encoding="utf-8").splitlines()
    assert "tests/compat/test_starlette_httpx2_testclient_compat.py" in called_args
    assert "tests/test_httpx_testclient_compat_guard.py" in called_args
    assert "tests/test_python_dependency_surfaces.py" in called_args
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


def test_backend_hook_maps_authz_contract_helper_to_static_contract_test(
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
    (repo / "tests" / "security").mkdir(parents=True)
    (repo / "tests" / "security" / "_api_authz_contracts.py").write_text(
        "AUTHZ = 1\n", encoding="utf-8"
    )
    (repo / "tests" / "security" / "test_api_authz_contract_static.py").write_text(
        "def test_static_contract():\n    assert True\n", encoding="utf-8"
    )
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    (repo / "tests" / "security" / "_api_authz_contracts.py").write_text(
        "AUTHZ = 2\n", encoding="utf-8"
    )
    _git(repo, "add", "tests/security/_api_authz_contracts.py")
    calls_file = tmp_path / "pytest-authz-contract-args.txt"
    fake_python = tmp_path / "fake-python-authz-contract"
    _write_fake_pytest_python(fake_python, calls_file)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(fake_python)
    env["PRE_COMMIT"] = "1"

    output = _bash("bash scripts/run-backend-tests-pre-commit.sh", cwd=repo, env=env)

    called_args = calls_file.read_text(encoding="utf-8").splitlines()
    assert "tests/security/test_api_authz_contract_static.py" in called_args
    assert "tests/security/_api_authz_contracts.py" not in called_args
    assert "Backend tests passed" in output


def test_backend_hook_fails_closed_for_missing_helper_test_target(
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
    (repo / "tests" / "security").mkdir(parents=True)
    (repo / "tests" / "security" / "_api_authz_contracts.py").write_text(
        "AUTHZ = 1\n", encoding="utf-8"
    )
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    (repo / "tests" / "security" / "_api_authz_contracts.py").write_text(
        "AUTHZ = 2\n", encoding="utf-8"
    )
    _git(repo, "add", "tests/security/_api_authz_contracts.py")
    calls_file = tmp_path / "pytest-authz-contract-missing-target-args.txt"
    fake_python = tmp_path / "fake-python-authz-contract-missing-target"
    _write_fake_pytest_python(fake_python, calls_file)
    env = _clean_hook_env()
    env["VENV_PYTHON"] = str(fake_python)
    env["PRE_COMMIT"] = "1"

    completed = _bash_failure(
        "bash scripts/run-backend-tests-pre-commit.sh",
        cwd=repo,
        env=env,
    )

    assert completed.returncode == 1
    assert (
        "Missing mapped pytest target for helper file "
        "'tests/security/_api_authz_contracts.py': "
        "tests/security/test_api_authz_contract_static.py"
    ) in completed.stderr
    assert not calls_file.exists()


def test_backend_hook_uses_helper_test_mapping_table() -> None:
    hook_text = (REPO_ROOT / "scripts" / "run-backend-tests-pre-commit.sh").read_text(
        encoding="utf-8"
    )

    assert "PYTHON_HELPER_SOURCE_FILES" in hook_text
    assert "PYTHON_HELPER_TEST_TARGETS" in hook_text
    assert '"tests/security/_api_authz_contracts.py"' in hook_text
    assert '"tests/security/test_api_authz_contract_static.py"' in hook_text


def test_pre_commit_config_runs_backend_hook_for_frontend_package_manifests() -> None:
    config_text = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "frontend/package(?:-lock)?\\.json" in config_text
    assert "always_run: true" in config_text


def test_makefile_hook_targets_use_shared_python_resolver() -> None:
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "HOOK_REPO_PYTHON = . scripts/hooks/repo_python.sh" in makefile_text
    assert 'VENV_PYTHON="$$($(HOOK_REPO_PYTHON))"' in makefile_text
    assert '"$$($(HOOK_REPO_PYTHON))" -m pre_commit run --all-files' in makefile_text
