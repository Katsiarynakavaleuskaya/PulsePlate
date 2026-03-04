#!/usr/bin/env python3
"""
Pre-flight auto-verification script for orchestration workflow.

Runs before any coordinator task or PR. Exit 0 = PASS, 1 = FAIL.
No external dependencies; Python 3.13 compatible.

Usage:
    python scripts/orchestration/check_preflight.py
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed git commands only, no user input
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "docs/orchestration/workflow.md",
    "docs/orchestration/AGENT_CONTEXT_MAP.md",
    "docs/orchestration/AGENT_CAPABILITY_MATRIX.md",
    "docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md",
    "docs/roadmap/BACKLOG_LEDGER.md",
    "AGENTS.md",
]

STATUS_HEAD_LINES = 10


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    r = subprocess.run(  # nosec B603 - fixed git commands only
        cmd,
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    out = (r.stdout or "").strip() + "\n" + (r.stderr or "").strip()
    return r.returncode, out.strip()


def check_sot_files() -> bool:
    """Verify required SoT files exist. Return True if all present."""
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).exists()]
    if missing:
        print("FAIL: Required SoT files missing:")
        for m in missing:
            print(f"  - {m}")
        return False
    print("PASS: All required SoT files present")
    return True


def check_worktrees_untracked() -> bool:
    """Verify worktrees/ is not tracked. Return True if clean."""
    code, out = _run(["git", "ls-files", "worktrees"])
    if code != 0:
        print("FAIL: git ls-files worktrees failed")
        print(out)
        return False
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if lines:
        print("FAIL: worktrees/ must not be tracked. Tracked paths:")
        for p in lines[:20]:
            print(f"  - {p}")
        if len(lines) > 20:
            print(f"  ... and {len(lines) - 20} more")
        return False
    print("PASS: worktrees/ not tracked")
    return True


ARTIFACT_GITIGNORE_RULES = [
    "artifacts/agent_runs/",
    "artifacts/orchestration/",
]


def check_artifact_gitignore() -> bool:
    """Warn if agent run artifacts are not gitignored. Soft guard (always returns True)."""
    gitignore_path = ROOT / ".gitignore"
    if not gitignore_path.exists():
        print("WARNING: .gitignore not found; agent run artifacts may be committed")
        return True
    try:
        content = gitignore_path.read_text(encoding="utf-8")
    except OSError:
        print("WARNING: Could not read .gitignore; agent run artifacts may be committed")
        return True
    for rule in ARTIFACT_GITIGNORE_RULES:
        if rule not in content:
            print(f"WARNING: {rule} not in .gitignore; agent run summaries may be committed")
    return True


def check_working_tree_clean() -> bool:
    """Verify working tree is clean. Return True if clean."""
    code, out = _run(["git", "status", "--porcelain"])
    if code != 0:
        print("FAIL: git status failed")
        print(out)
        return False
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if lines:
        print("FAIL: Working tree not clean. First lines:")
        for ln in lines[:STATUS_HEAD_LINES]:
            print(f"  {ln}")
        if len(lines) > STATUS_HEAD_LINES:
            print(f"  ... and {len(lines) - STATUS_HEAD_LINES} more")
        return False
    print("PASS: Working tree clean")
    return True


def main() -> int:
    """Run all checks. Return 0 on PASS, 1 on FAIL."""
    ok = True
    ok &= check_sot_files()
    ok &= check_worktrees_untracked()
    ok &= check_working_tree_clean()
    check_artifact_gitignore()  # Soft guard: warning only, never fails
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
