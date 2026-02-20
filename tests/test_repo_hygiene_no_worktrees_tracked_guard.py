from __future__ import annotations

import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=_repo_root(),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_no_tracked_worktrees_paths() -> None:
    tracked = _git("ls-files", "worktrees")
    assert (
        tracked == ""
    ), "worktrees must never be committed; remove tracked paths under worktrees/."


def test_gitignore_contains_worktrees_rule() -> None:
    gitignore_path = _repo_root() / ".gitignore"
    content = gitignore_path.read_text(encoding="utf-8")
    assert "worktrees/" in content, ".gitignore must contain worktrees/ ignore rule."
