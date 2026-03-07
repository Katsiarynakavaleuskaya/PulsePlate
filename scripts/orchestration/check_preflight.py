#!/usr/bin/env python3
"""Mode-aware pre-flight auto-verification for orchestration workflow.

Modes:
- analyze: repo discovery / task analysis, dirty tree allowed
- execute: implementation start, task scope must be isolated and routed
- merge: merge-prep checks, requires local gate evidence
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404: fixed git commands only, no user input (remove-by: 2026-06-30, ref: PR-996)
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.context_pack import collect_scoped_agents, repo_relative_paths

ROOT = REPO_ROOT
GIT_BIN = shutil.which("git")
if GIT_BIN is None:
    raise RuntimeError("git executable not found on PATH")

REQUIRED_FILES = [
    "docs/orchestration/workflow.md",
    "docs/orchestration/AGENT_CONTEXT_MAP.md",
    "docs/orchestration/AGENT_CAPABILITY_MATRIX.md",
    "docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md",
    "docs/roadmap/BACKLOG_LEDGER.md",
    "AGENTS.md",
]

STATUS_HEAD_LINES = 10
VALID_MODES = {"analyze", "execute", "merge"}


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    if cmd and cmd[0] == "git":
        cmd = [GIT_BIN, *cmd[1:]]
    r = subprocess.run(  # nosec B603: fixed git commands only (remove-by: 2026-06-30, ref: PR-996)
        cmd,
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    out = (r.stdout or "").strip() + "\n" + (r.stderr or "").strip()
    return r.returncode, out.strip()


def _parse_dirty_paths(status_output: str) -> list[str]:
    paths: list[str] = []
    for line in status_output.splitlines():
        if not line.strip():
            continue
        raw = line[3:].strip()
        path_part = raw.split(" -> ", 1)[-1]
        paths.append(path_part)
    return sorted(set(paths))


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


def check_agent_consistency() -> bool:
    """Verify routing/inventory/capability consistency."""

    code, out = _run([sys.executable, "scripts/orchestration/check_agent_consistency.py"])
    if code != 0:
        print("FAIL: agent consistency check failed")
        print(out)
        return False
    print("PASS: agent consistency check")
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


def check_task_scope_isolated(task_paths: list[str]) -> bool:
    """Verify dirty tree is contained inside the explicit task scope."""

    normalized_paths = repo_relative_paths(task_paths)
    if not normalized_paths:
        print("FAIL: execute/merge mode requires at least one --path")
        return False

    code, out = _run(["git", "status", "--porcelain"])
    if code != 0:
        print("FAIL: git status failed")
        print(out)
        return False

    dirty_paths = _parse_dirty_paths(out)
    outside_scope = [
        path
        for path in dirty_paths
        if not any(
            path == scope or path.startswith(f"{scope.rstrip('/')}/") for scope in normalized_paths
        )
    ]
    if outside_scope:
        print("FAIL: dirty paths outside explicit task scope:")
        for path in outside_scope[:STATUS_HEAD_LINES]:
            print(f"  - {path}")
        if len(outside_scope) > STATUS_HEAD_LINES:
            print(f"  ... and {len(outside_scope) - STATUS_HEAD_LINES} more")
        return False

    print("PASS: task scope isolated")
    return True


def check_scoped_agents_exist(task_paths: list[str]) -> bool:
    """Verify nearest module AGENTS files exist for each candidate path."""

    normalized_paths = repo_relative_paths(task_paths)
    if not normalized_paths:
        print("FAIL: preflight requires at least one --path to resolve scoped AGENTS")
        return False

    scoped_agents = collect_scoped_agents(normalized_paths)
    if not scoped_agents:
        print("FAIL: no scoped AGENTS.md files resolved for candidate paths")
        return False

    missing = [path for path in scoped_agents if not (ROOT / path).is_file()]
    if missing:
        print("FAIL: resolved scoped AGENTS.md paths missing:")
        for path in missing:
            print(f"  - {path}")
        return False

    print("PASS: scoped AGENTS resolved")
    return True


def check_routing_readiness(primary: str, secondary: list[str], reviewer: str) -> bool:
    """Verify explicit routing assignment exists for execute/merge mode."""

    if not primary.strip():
        print("FAIL: --primary is required in execute/merge mode")
        return False
    if not reviewer.strip():
        print("FAIL: --reviewer is required in execute/merge mode")
        return False
    if reviewer.strip() == primary.strip():
        print("FAIL: reviewer must be independent from primary")
        return False
    if len([agent for agent in secondary if agent.strip()]) > 2:
        print("FAIL: maximum 2 secondary agents allowed")
        return False
    print("PASS: routing readiness")
    return True


def check_gate_evidence(files: list[str]) -> bool:
    """Verify merge-mode local gate evidence artifacts exist and are non-empty."""

    if not files:
        print("FAIL: merge mode requires at least one --evidence-file")
        return False

    missing = [path for path in files if not Path(path).is_file()]
    if missing:
        print("FAIL: gate evidence files missing:")
        for path in missing:
            print(f"  - {path}")
        return False

    unreadable: list[str] = []
    empty: list[str] = []
    for raw_path in files:
        try:
            content = Path(raw_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            unreadable.append(raw_path)
            continue
        if not content.strip():
            empty.append(raw_path)

    if unreadable:
        print("FAIL: gate evidence files must be readable UTF-8 text:")
        for path in unreadable:
            print(f"  - {path}")
        return False

    if empty:
        print("FAIL: gate evidence files must be non-empty:")
        for path in empty:
            print(f"  - {path}")
        return False

    print("PASS: local gate evidence present")
    return True


def _parse_args(
    argv: list[str] | None = None,
) -> tuple[str, list[str], str, list[str], str, list[str]]:
    import argparse

    parser = argparse.ArgumentParser(
        prog="check_preflight",
        description="Mode-aware orchestration preflight validator.",
    )
    parser.add_argument("--mode", default="analyze", choices=sorted(VALID_MODES))
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--primary", default="")
    parser.add_argument("--secondary", action="append", default=[])
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--evidence-file", action="append", default=[])
    args = parser.parse_args(argv)
    return (
        args.mode,
        args.path,
        args.primary,
        args.secondary,
        args.reviewer,
        args.evidence_file,
    )


def main(argv: list[str] | None = None) -> int:
    """Run all checks. Return 0 on PASS, 1 on FAIL."""
    mode, task_paths, primary, secondary, reviewer, evidence_files = _parse_args(argv)
    ok = True
    ok &= check_sot_files()
    ok &= check_worktrees_untracked()
    ok &= check_agent_consistency()
    check_artifact_gitignore()  # Soft guard: warning only, never fails

    if mode == "analyze":
        if task_paths:
            ok &= check_scoped_agents_exist(task_paths)
        else:
            print("WARNING: analyze mode without --path skips scoped AGENTS resolution")
        code, out = _run(["git", "status", "--porcelain"])
        if code == 0 and out.strip():
            print("INFO: analyze mode allows dirty working tree")
        elif code == 0:
            print("PASS: working tree clean")
        else:
            print("FAIL: git status failed")
            print(out)
            ok = False
        return 0 if ok else 1

    ok &= check_task_scope_isolated(task_paths)
    ok &= check_scoped_agents_exist(task_paths)
    ok &= check_routing_readiness(primary, secondary, reviewer)

    if mode == "merge":
        ok &= check_gate_evidence(evidence_files)
        ok &= check_working_tree_clean()

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
