#!/usr/bin/env python3
"""Collect advisory review context for PulsePlate PR PR-review skill."""

from __future__ import annotations

import argparse
import json
import re
import os
import shutil
import shlex
import subprocess  # nosec B404: fixed command execution only, bounded to internal helper paths (remove-by: 2026-12-31, ref: ledger-p2-pulseplate-pr-review-context-collector)
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.review_source_status import build_review_source_status

SCHEMA_VERSION = "1.0.0"

AGENTS_BASENAME = "AGENTS.md"

DIFF_NUMSTAT_RE = re.compile(r"^(\d+|-)\t(\d+|-)\t(.*)$")
MAPPING_SECTION_RE = re.compile(r"^#{2,3}\s+Fixed in Commit Mapping\s*$", re.IGNORECASE)
MAPPING_COMMENT_RE = re.compile(r"^\s*-\s*(https://github\.com/\S+)\s*$")
MAPPING_MAPPED_RE = re.compile(
    r"^\s*-\s*(https://github\.com/\S+)\s*->\s*([0-9a-f]{7,40})\s*$",
    re.IGNORECASE,
)
NO_ACTIONABLE_RE = re.compile(r"\s*-\s*No actionable review comments\s*$")


@dataclass(frozen=True)
class DiffStats:
    path: str
    additions: int
    deletions: int


def _binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise FileNotFoundError(f"Missing required binary: {name}")
    return path


def _run_command(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(  # nosec B603: fixed argv flow via helper + absolute binaries only (remove-by: 2026-12-31, ref: ledger-p2-pulseplate-pr-review-context-collector)
        args,
        cwd=str(cwd),
        text=True,
        check=False,
        capture_output=True,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(f"Command failed ({shlex.join(args)}): {completed.stderr.strip()}")
    return completed


def _run_json_command(args: list[str], *, cwd: Path) -> list[Any] | dict[str, Any]:
    completed = _run_command(args, cwd=cwd)
    raw = completed.stdout.strip()
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, (list, dict)):
            return parsed
    except json.JSONDecodeError:
        pass

    results: list[Any] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, list):
                results.extend(parsed)
            elif isinstance(parsed, dict):
                results.append(parsed)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON payload: {line!r}") from exc
    return results


def _read_text_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def infer_repo_name(repo_root: Path) -> str | None:
    env_repo = os.environ.get("GITHUB_REPOSITORY")
    if env_repo:
        return env_repo.strip()

    git_binary = _binary("git")
    completed = _run_command(
        [git_binary, "-C", str(repo_root), "config", "--get", "remote.origin.url"],
        cwd=repo_root,
    )
    raw = completed.stdout.strip()
    if not raw:
        return None

    if raw.startswith("https://github.com/"):
        owner_repo = raw[len("https://github.com/") :].removesuffix(".git")
        return owner_repo

    if raw.startswith("git@github.com:"):
        owner_repo = raw[len("git@github.com:") :].removesuffix(".git")
        return owner_repo

    return None


def _parse_mapping_entry(line: str) -> tuple[str, str] | tuple[str, None] | None:
    mapped = MAPPING_MAPPED_RE.match(line)
    if mapped:
        return mapped.group(1), mapped.group(2)

    comment_only = MAPPING_COMMENT_RE.match(line)
    if comment_only:
        return comment_only.group(1), None

    return None


def collect_fixed_mapping_state(repo_root: Path, pr_number: int) -> dict[str, Any]:
    path = repo_root / "docs" / "review" / f"PR_{pr_number}_FIXED_MAPPING.md"
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "entries": {},
            "no_actionable": False,
            "errors": [
                "Fixed mapping artifact is missing; PR body-only evidence is advisory-only until artifact exists."
            ],
        }

    lines = _read_text_lines(path)
    section: list[str] = []
    started = False
    for line in lines:
        if MAPPING_SECTION_RE.match(line):
            started = True
            continue
        if started:
            if line.startswith("##"):
                break
            section.append(line.strip())

    entries: dict[str, str | None] = {}
    no_actionable = False
    for line in section:
        if NO_ACTIONABLE_RE.match(line):
            no_actionable = True
            continue
        parsed = _parse_mapping_entry(line)
        if parsed:
            entries[parsed[0]] = parsed[1]

    return {
        "path": str(path),
        "exists": True,
        "entries": entries,
        "no_actionable": no_actionable,
        "errors": [],
    }


def collect_pr_metadata(
    *,
    repo: str,
    pr_number: int,
    repo_root: Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    gh_binary = _binary("gh")
    warnings: list[str] = []

    try:
        payload = _run_json_command(
            [gh_binary, "api", f"repos/{repo}/pulls/{pr_number}"],
            cwd=repo_root,
        )
    except RuntimeError as exc:
        warnings.append(f"Unable to load PR metadata: {exc}")
        return None, warnings

    if not isinstance(payload, dict):
        warnings.append("Unexpected PR metadata shape from gh API response.")
        return None, warnings

    head = payload.get("head", {})
    base = payload.get("base", {})
    return {
        "number": payload.get("number", pr_number),
        "title": payload.get("title", ""),
        "state": payload.get("state", ""),
        "url": payload.get("html_url", ""),
        "author": ((payload.get("user") or {}).get("login") or ""),
        "created_at": payload.get("created_at", ""),
        "base_sha": (base.get("sha") or ""),
        "head_sha": (head.get("sha") or ""),
    }, warnings


def collect_scope_diff(
    *,
    repo_root: Path,
    base_sha: str | None,
    head_sha: str | None,
) -> tuple[list[DiffStats], dict[str, Any], list[str]]:
    if not base_sha or not head_sha:
        return (
            [],
            {"files": 0, "additions": 0, "deletions": 0, "changed_lines": 0},
            ["Diff base/head missing: skipping changed file discovery."],
        )

    git_binary = _binary("git")
    try:
        completed = _run_command(
            [
                git_binary,
                "-C",
                str(repo_root),
                "diff",
                "--numstat",
                f"{base_sha}..{head_sha}",
            ],
            cwd=repo_root,
        )
    except RuntimeError as exc:
        return [], {"files": 0, "additions": 0, "deletions": 0, "changed_lines": 0}, [str(exc)]

    files: list[DiffStats] = []
    lines = 0
    additions_total = 0
    deletions_total = 0
    for raw in completed.stdout.splitlines():
        match = DIFF_NUMSTAT_RE.match(raw)
        if not match:
            continue
        additions_raw, deletions_raw, path = match.groups()
        additions = 0 if additions_raw == "-" else int(additions_raw)
        deletions = 0 if deletions_raw == "-" else int(deletions_raw)
        files.append(DiffStats(path=path, additions=additions, deletions=deletions))
        additions_total += additions
        deletions_total += deletions
        lines += additions + deletions

    return (
        files,
        {
            "files": len(files),
            "additions": additions_total,
            "deletions": deletions_total,
            "changed_lines": lines,
        },
        [],
    )


def discover_scoped_agents(repo_root: Path, changed_files: list[str]) -> list[str]:
    discovered: list[str] = []
    for raw in changed_files:
        path = Path(raw)
        if path.is_absolute():
            target = path
        else:
            target = repo_root / path

        current = target
        if current.is_file():
            current = current.parent

        while True:
            candidate = current / AGENTS_BASENAME
            if candidate.is_file():
                rel = str(candidate.relative_to(repo_root))
                if rel not in discovered:
                    discovered.append(rel)
            if current == repo_root:
                break
            current = current.parent

    if "AGENTS.md" not in discovered and (repo_root / "AGENTS.md").is_file():
        discovered.insert(0, "AGENTS.md")

    return sorted(discovered)


def _suggest_tests(
    *,
    changed_files: list[str],
    fixed_mapping_exists: bool,
    pr_metadata_available: bool,
) -> list[str]:
    tests: set[str] = {"python3 scripts/orchestration/check_preflight.py"}

    if any(path.startswith("scripts/") for path in changed_files):
        tests.add("python3 scripts/orchestration/check_agent_consistency.py")
    if any(path.startswith("tests/") for path in changed_files):
        tests.add("make test-fast")
    if not fixed_mapping_exists:
        tests.add("Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop")
    if not pr_metadata_available:
        tests.add("python3 scripts/orchestration/pr_review_context.py --pr <PR_NUMBER>")

    return sorted(tests)


def collect_review_context(
    *,
    repo_root: Path,
    pr_number: int | None,
    repo: str | None,
    base_ref: str | None = None,
    head_ref: str | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    repo = repo or infer_repo_name(repo_root)

    pr_metadata = None
    if pr_number is not None:
        if not repo:
            warnings.append("Cannot read PR metadata: repository slug unavailable.")
        else:
            pr_metadata, metadata_warnings = collect_pr_metadata(
                repo=repo,
                pr_number=pr_number,
                repo_root=repo_root,
            )
            warnings.extend(metadata_warnings)

    pr_metadata_base = pr_metadata.get("base_sha", "") if pr_metadata else ""
    pr_metadata_head = pr_metadata.get("head_sha", "") if pr_metadata else ""

    diff_base = base_ref or pr_metadata_base
    diff_head = head_ref or pr_metadata_head
    if not diff_base and not diff_head:
        git_binary = _binary("git")
        diff_base = _run_command(
            [git_binary, "-C", str(repo_root), "merge-base", "origin/main", "HEAD"],
            cwd=repo_root,
        ).stdout.strip()
        diff_head = _run_command(
            [git_binary, "-C", str(repo_root), "rev-parse", "HEAD"],
            cwd=repo_root,
        ).stdout.strip()

    changed_file_stats, diff_summary, diff_warnings = collect_scope_diff(
        repo_root=repo_root,
        base_sha=diff_base,
        head_sha=diff_head,
    )
    warnings.extend(diff_warnings)

    changed_files = [entry.path for entry in changed_file_stats]
    scoped_agents = discover_scoped_agents(repo_root=repo_root, changed_files=changed_files)

    if pr_number is None:
        fixed_mapping = {
            "path": str(repo_root / "docs" / "review" / "PR_<N>_FIXED_MAPPING.md"),
            "exists": False,
            "errors": ["No PR number provided for fixed-mapping lookup."],
        }
    else:
        fixed_mapping = collect_fixed_mapping_state(repo_root=repo_root, pr_number=pr_number)
        if not fixed_mapping.get("exists"):
            warnings.append("Fixed-mapping artifact is missing for this PR.")

    review_source_status = [
        build_review_source_status(
            source="github_pr_metadata",
            available=pr_metadata is not None,
            reason="" if pr_metadata is not None else "PR metadata unavailable",
            evidence="gh api repos/<repo>/pulls/<pr>",
        ),
        build_review_source_status(
            source="git_diff",
            available=bool(changed_file_stats) or not diff_warnings,
            degraded=bool(diff_warnings),
            reason="; ".join(diff_warnings),
            evidence=f"{diff_base}..{diff_head}" if diff_base and diff_head else "",
        ),
        build_review_source_status(
            source="fixed_mapping_artifact",
            available=bool(fixed_mapping.get("exists")),
            reason="" if fixed_mapping.get("exists") else "Fixed-mapping artifact unavailable",
            evidence=str(fixed_mapping.get("path") or ""),
        ),
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query": {
            "repo": repo or "",
            "pr_number": pr_number,
            "base_ref": diff_base,
            "head_ref": diff_head,
        },
        "pr": pr_metadata,
        "diff": {
            "summary": diff_summary,
            "files": [entry.__dict__ for entry in changed_file_stats],
        },
        "agents_discovery": {
            "scoped_agents_md": scoped_agents,
            "files_seen": changed_files,
        },
        "fixed_mapping": fixed_mapping,
        "review_source_status": review_source_status,
        "test_suggestions": _suggest_tests(
            changed_files=changed_files,
            fixed_mapping_exists=bool(fixed_mapping.get("exists")),
            pr_metadata_available=pr_metadata is not None,
        ),
        "warnings": warnings,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect advisory read-only context for PulsePlate PR review skill."
    )
    parser.add_argument("--pr", type=int, help="Pull request number", default=None)
    parser.add_argument("--repo", help="owner/repo slug for gh API", default=None)
    parser.add_argument("--base", help="Override base sha for diff", default=None)
    parser.add_argument("--head", help="Override head sha for diff", default=None)
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repo root path")
    parser.add_argument("--output", help="Write JSON to file", default=None)

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    context = collect_review_context(
        repo_root=Path(args.repo_root),
        pr_number=args.pr,
        repo=args.repo,
        base_ref=args.base,
        head_ref=args.head,
    )

    payload = json.dumps(context, indent=2, ensure_ascii=False)
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    if context["warnings"]:
        for warning in context["warnings"]:
            print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
