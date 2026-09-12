"""Behavioral regression proof for the shell scope guard and its numeric counts."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

SCOPE_GUARD = Path(__file__).resolve().parents[1] / "scripts/ci/pr_scope_guard.sh"


def _binary(name: str) -> str:
    resolved = shutil.which(name)
    assert resolved is not None, f"Required test tool is missing: {name}"
    return resolved


def _grep_only_path(tmp_path: Path) -> str:
    """Exercise the supported CI environment without ripgrep."""
    tools_dir = tmp_path / "bin"
    tools_dir.mkdir()
    for name in ["git", "grep", "awk", "sed", "wc", "tr", "head"]:
        (tools_dir / name).symlink_to(_binary(name))
    return str(tools_dir)


@pytest.mark.parametrize(
    ("contents", "pattern", "expected"),
    [
        ("screen.swift\nnotes.md\n", r"\.py$", "0\n"),
        ("file.py\nfileapy\n", r"\.py$", "1\n"),
        ("one.py\ntwo.py\n", r"\.py$", "2\n"),
        ("", r"\.py$", "0\n"),
    ],
)
def test_scope_count_emits_one_integer(
    tmp_path: Path, contents: str, pattern: str, expected: str
) -> None:
    definitions = SCOPE_GUARD.read_text().split("# Base ref resolution:", maxsplit=1)[0]
    result = subprocess.run(
        [
            _binary("bash"),
            "-c",
            definitions + '\ncount=$(_count "$1")\nprintf "%s\\n" "$count"\n',
            "scope-count",
            pattern,
        ],
        input=contents,
        env={**os.environ, "PATH": _grep_only_path(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected
    assert result.stderr == ""


@pytest.mark.parametrize("contents", ["file.py\n", ""])
def test_scope_count_propagates_invalid_regex(tmp_path: Path, contents: str) -> None:
    definitions = SCOPE_GUARD.read_text().split("# Base ref resolution:", maxsplit=1)[0]
    result = subprocess.run(
        [
            _binary("bash"),
            "-c",
            definitions + '\ncount=$(_count "$1")\necho accepted\n',
            "scope-count",
            "[",
        ],
        input=contents,
        env={**os.environ, "PATH": _grep_only_path(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "accepted" not in result.stdout
    assert result.stderr


@pytest.mark.parametrize(
    ("paths", "expected_code", "expected_output"),
    [
        (["ios/Screen.swift", "docs/change.md"], 0, "Python files: 0\n"),
        (["app/route.py", "core/model.py", "docs/change.md"], 0, "Python files: 2\n"),
        (["docs/pr/test.py"], 1, "BLOCK: Python files found under docs/pr"),
        (["app/route.py", "docs/pr/PR_123_ROADMAP.md"], 1, "BLOCK: Planning docs"),
    ],
)
@pytest.mark.parametrize("inherited_index", [False, True])
def test_scope_shell_counts_and_forbidden_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    paths: list[str],
    expected_code: int,
    expected_output: str,
    inherited_index: bool,
) -> None:
    if inherited_index:
        monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "outer" / "index"))
    # A nested fixture repo must not inherit the outer commit hook's Git state.
    fixture_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    fixture_env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
    repo = tmp_path / "repo"
    repo.mkdir()
    git = _binary("git")
    commands = [
        ["init", "-q"],
        ["config", "user.name", "Scope Test"],
        ["config", "user.email", "scope-test@example.invalid"],
        ["commit", "-q", "--allow-empty", "-m", "base"],
        ["update-ref", "refs/remotes/origin/main", "HEAD"],
    ]
    for args in commands:
        subprocess.run([git, *args], cwd=repo, env=fixture_env, check=True, capture_output=True)
    for path in paths:
        destination = repo / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("fixture\n")
    subprocess.run([git, "add", "."], cwd=repo, env=fixture_env, check=True, capture_output=True)
    subprocess.run(
        [git, "commit", "-q", "-m", "candidate"],
        cwd=repo,
        env=fixture_env,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        [_binary("bash"), str(SCOPE_GUARD)],
        cwd=repo,
        env={**fixture_env, "PATH": _grep_only_path(tmp_path), "GITHUB_BASE_REF": "main"},
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == expected_code, result.stdout + result.stderr
    assert expected_output in result.stdout
    assert result.stderr == ""
    if expected_code == 0:
        assert "Markdown files: 1\n" in result.stdout
