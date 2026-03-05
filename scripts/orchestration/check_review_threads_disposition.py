#!/usr/bin/env python3
"""
Guard: resolved review threads must have explicit Disposition records in PR body.

Strict mode: every resolved thread must be listed under **Fixed in Commit Mapping**
with Disposition (FIXED | NOT-A-BUG | DEFERRED) and proof (Commit / Evidence / Backlog).

Requires: GitHub CLI `gh` authenticated. **Canonical token: GH_TOKEN.** In CI use --require-auth and
export GH_TOKEN from secrets.GITHUB_TOKEN. GITHUB_TOKEN alone is not sufficient — gh reads GH_TOKEN.
Preflight: when --require-auth or CI=true, script requires GH_TOKEN and exits 1 with diagnostic before
any GraphQL; no mapping/resolve attempts without valid auth.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess  # nosec B404: fixed gh CLI only (remove-by: 2026-04-30, ref: PR-985)
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

DISPOSITION_RE = re.compile(r"Disposition:\s*(FIXED|NOT-A-BUG|DEFERRED)", re.IGNORECASE)
PROOF_RE = re.compile(r"(Commit:|Evidence:|Backlog:)", re.IGNORECASE)
# Match any heading level (#, ##, ###, ...) Fixed in Commit Mapping then content until next # or end
FIXED_MAPPING_SECTION_RE = re.compile(r"(?is)#+\s*Fixed in Commit Mapping\s*(.*?)(?:\n#+\s|\Z)")


@dataclass(frozen=True)
class ResolvedThreadRef:
    url: str
    source: str
    is_resolved: bool
    created_at: str  # ISO 8601 from GraphQL (first comment createdAt)


# Timeout for gh CLI calls to avoid hanging CI (CodeRabbit/Cubic).
_RUN_TIMEOUT_SEC = 60
_GIT_TIMEOUT_SEC = 15

# Mapping line: "- https://... -> sha" or "- https://...#anchor -> sha"
_MAPPING_LINE_RE = re.compile(r"^\s*-\s*(https://[^\s]+)\s*->\s*([a-f0-9]{7,40})\b", re.IGNORECASE)


def _run(cmd: list[str]) -> str:
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=_RUN_TIMEOUT_SEC
    )  # nosec B603: fixed argv from callers (remove-by: 2026-04-30, ref: PR-985)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result.stdout


def _parse_iso_datetime(value: str) -> datetime:
    """
    Parse ISO 8601 datetime from GitHub/GraphQL or git (%cI).
    Supports trailing 'Z'.
    """
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _git_commit_time_iso(commit_sha: str) -> str:
    """
    Return commit committer date in strict ISO 8601 (git %cI).
    Uses absolute git path (B607-class safe).
    """
    git_path = shutil.which("git")
    if not git_path:
        raise RuntimeError("git not found in PATH; required for commit-after-comment guard")
    result = subprocess.run(
        [git_path, "show", "-s", "--format=%cI", commit_sha],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SEC,
        check=False,
    )  # nosec B603: fixed argv, no user input (remove-by: 2026-04-30, ref: PR-985)
    if result.returncode != 0:
        raise RuntimeError(
            f"git show failed for sha={commit_sha}: rc={result.returncode} stderr={result.stderr.strip()!r}"
        )
    out = result.stdout.strip()
    if not out:
        raise RuntimeError(f"git returned empty commit time for sha={commit_sha}")
    return out


def _parse_mapping_section(section: str) -> dict[str, str]:
    """
    Parse Fixed in Commit Mapping section: lines like "- https://... -> sha".
    Returns dict mapping url (and url base) -> sha for lookup.
    """
    mapping: dict[str, str] = {}
    for line in section.splitlines():
        m = _MAPPING_LINE_RE.search(line)
        if not m:
            continue
        url_part, sha = m.group(1).strip(), m.group(2)
        mapping[url_part] = sha
        base = url_part.split("#")[0]
        if base not in mapping:
            mapping[base] = sha
    return mapping


def _check_commit_after_comment(
    resolved_threads: list[ResolvedThreadRef],
    section: str,
    *,
    _git_commit_time_fn: Any = None,
) -> list[str]:
    """
    For each resolved thread with a mapped SHA, require commit_time > comment_time.
    Returns list of violation messages (empty if all pass).
    _git_commit_time_fn(sha) -> ISO str for tests; default _git_commit_time_iso.
    """
    get_commit_time = _git_commit_time_fn or _git_commit_time_iso
    mapping_by_url = _parse_mapping_section(section)
    violations: list[str] = []
    for t in resolved_threads:
        thread_base = t.url.split("#")[0]
        sha = mapping_by_url.get(t.url) or mapping_by_url.get(thread_base)
        if not sha:
            violations.append(
                f"{t.url}: no commit SHA in mapping (add line '- <url> -> <sha>' in Fixed in Commit Mapping)"
            )
            continue
        if not t.created_at:
            violations.append(
                f"{t.url}: missing comment timestamp (cannot verify commit-after-comment)"
            )
            continue
        try:
            thread_created = _parse_iso_datetime(t.created_at)
            commit_iso = get_commit_time(sha)
            commit_dt = _parse_iso_datetime(commit_iso)
            if commit_dt <= thread_created:
                violations.append(
                    f"{t.url}: mapped to {sha} but commit_time={commit_iso} <= comment_time={t.created_at} "
                    "(commit must be after comment; fix code first, then map)"
                )
        except RuntimeError as e:
            violations.append(f"{t.url}: {e}")
    return violations


def _get_pr_number() -> int:
    out = _run(["gh", "pr", "view", "--json", "number", "-q", ".number"])
    out = out.strip()
    if not out.isdigit():
        raise RuntimeError(f"Unable to detect PR number from gh output: {out!r}")
    return int(out)


def _get_pr_body() -> str:
    return _run(["gh", "pr", "view", "--json", "body", "-q", ".body"])


def _graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    out = _run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-f",
            f"variables={json.dumps(variables)}",
        ]
    )
    data = json.loads(out)
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def _get_owner_repo() -> tuple[str, str]:
    owner = _run(["gh", "repo", "view", "--json", "owner", "-q", ".owner.login"]).strip()
    name = _run(["gh", "repo", "view", "--json", "name", "-q", ".name"]).strip()
    if not owner or not name:
        raise RuntimeError("Unable to detect owner/repo via gh repo view.")
    return owner, name


def _extract_fixed_mapping_section(body: str) -> str:
    """Extract content under ### Fixed in Commit Mapping."""
    match = FIXED_MAPPING_SECTION_RE.search(body)
    if not match:
        return ""
    return match.group(1).strip()


def _find_disposition_block_in_section(section: str, url: str) -> bool:
    """
    Base URL (without anchor) must appear inside Fixed in Commit Mapping section
    with Disposition + proof (Commit/Evidence/Backlog) nearby (±12 lines).
    Match by base URL so #discussion_r... and #pullrequestreview-... both match.
    Scan all occurrences; return True if any occurrence has a valid window.
    """
    thread_base = url.split("#")[0]
    lines = section.splitlines()
    for i, line in enumerate(lines):
        if thread_base in line:
            start = max(0, i - 12)
            end = min(len(lines), i + 13)
            window = "\n".join(lines[start:end])
            if DISPOSITION_RE.search(window) and PROOF_RE.search(window):
                return True
    return False


def _collect_resolved_threads(pr_number: int) -> list[ResolvedThreadRef]:
    owner, repo = _get_owner_repo()

    query = """
    query($owner:String!, $repo:String!, $pr:Int!, $after:String) {
      repository(owner:$owner, name:$repo) {
        pullRequest(number:$pr) {
          reviewThreads(first: 100, after: $after) {
            pageInfo { hasNextPage endCursor }
            nodes {
              isResolved
              comments(first: 1) {
                nodes { url createdAt }
              }
            }
          }
        }
      }
    }
    """
    after: str | None = None
    resolved: list[ResolvedThreadRef] = []

    while True:
        variables = {"owner": owner, "repo": repo, "pr": pr_number, "after": after}
        data = _graphql(query, variables)
        pr = data["repository"]["pullRequest"]
        threads = pr["reviewThreads"]["nodes"]
        for t in threads:
            if not t.get("isResolved", False):
                continue
            comment_nodes = (t.get("comments") or {}).get("nodes") or []
            if comment_nodes and comment_nodes[0].get("url"):
                first = comment_nodes[0]
                created_at = first.get("createdAt") or ""
                resolved.append(
                    ResolvedThreadRef(
                        url=first["url"],
                        source="comment",
                        is_resolved=True,
                        created_at=created_at,
                    )
                )
        page = pr["reviewThreads"]["pageInfo"]
        if not page["hasNextPage"]:
            break
        after = page["endCursor"]

    uniq: dict[str, ResolvedThreadRef] = {r.url: r for r in resolved}
    return list(uniq.values())


def _has_gh_auth() -> bool:
    """True if gh CLI can use a token (env vars or gh auth login)."""
    if (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip():
        return True
    # Users with `gh auth login` (no env): use resolved path to avoid partial-path execution (B607)
    gh_path = shutil.which("gh")
    if not gh_path:
        return False
    result = subprocess.run(
        [gh_path, "auth", "status"],
        capture_output=True,
        text=True,
        timeout=5,
    )  # nosec B603: fixed argv, no user input (remove-by: 2026-04-30, ref: PR-985)
    return result.returncode == 0


def _env_diagnostic() -> str:
    """Return one-line env status (SET/MISSING only, no values)."""
    keys = ("GH_TOKEN", "GITHUB_TOKEN", "GITHUB_PAT", "CI", "GITHUB_ACTIONS")
    parts = [f"{k}={('SET' if (os.environ.get(k) or '').strip() else 'MISSING')}" for k in keys]
    return " ".join(parts)


def _require_gh_token_preflight(require_auth: bool, in_ci: bool) -> None:
    """
    When require_auth or CI: require GH_TOKEN and optional gh auth status. Exit 1 with
    diagnostic and fix commands before any GraphQL. Single source of token: GH_TOKEN.
    """
    if not require_auth and not in_ci:
        return
    gh_token = (os.environ.get("GH_TOKEN") or "").strip()
    if not gh_token:
        print("ERROR: GH_TOKEN required for disposition guard (--require-auth or CI=true).")
        print("       gh reads GH_TOKEN; GITHUB_TOKEN alone is not sufficient.")
        print(f"       Env: {_env_diagnostic()}")
        print("Fix (choose one):")
        print('  export GH_TOKEN="$GITHUB_TOKEN"   # if GITHUB_TOKEN is set')
        print('  export GH_TOKEN="$GITHUB_PAT"    # or from your PAT')
        print("  Then: gh auth status")
        sys.exit(1)
    # GH_TOKEN set — verify gh can use it (preflight before GraphQL)
    gh_path = shutil.which("gh")
    if not gh_path:
        print("ERROR: gh CLI not found in PATH; required when GH_TOKEN is set.")
        sys.exit(1)
    result = subprocess.run(
        [gh_path, "auth", "status"],
        capture_output=True,
        text=True,
        timeout=10,
    )  # nosec B603: fixed argv (remove-by: 2026-04-30, ref: PR-985)
    if result.returncode != 0:
        print("ERROR: GH_TOKEN is set but gh auth status failed. Fix env before running GraphQL.")
        print(f"       Env: {_env_diagnostic()}")
        print("  gh auth status  # run manually to see reason")
        sys.stderr.write(result.stderr or "")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check resolved review threads have disposition in PR body."
    )
    parser.add_argument(
        "--require-auth",
        action="store_true",
        help="In CI: fail if GH_TOKEN not set. Otherwise without auth we SKIP (exit 0).",
    )
    args = parser.parse_args()

    in_ci = os.environ.get("CI") == "true"
    if args.require_auth or in_ci:
        # Strict preflight: require GH_TOKEN and gh auth status before any GraphQL
        _require_gh_token_preflight(args.require_auth, in_ci)
    else:
        if not _has_gh_auth():
            print("SKIP: no gh auth (set GH_TOKEN or run gh auth login for full check).")
            sys.exit(0)

    pr_number = _get_pr_number()
    body = _get_pr_body()
    section = _extract_fixed_mapping_section(body)

    if not section:
        print("ERROR: Missing 'Fixed in Commit Mapping' section in PR body.")
        sys.exit(1)

    resolved_threads = _collect_resolved_threads(pr_number)

    if not resolved_threads:
        print("OK: No resolved review threads found (nothing to enforce).")
        sys.exit(0)

    missing_refs: list[str] = []
    missing_disposition: list[str] = []

    for t in resolved_threads:
        thread_base = t.url.split("#")[0]
        if thread_base not in section:
            missing_refs.append(t.url)
            continue
        if not _find_disposition_block_in_section(section, t.url):
            missing_disposition.append(t.url)

    if missing_refs or missing_disposition:
        print("ERROR: Review disposition policy violated.\n")
        if missing_refs:
            print("Resolved threads missing from Fixed in Commit Mapping (must list URL there):")
            for u in missing_refs:
                print(f"  - {u}")
            print()
        if missing_disposition:
            print(
                "Resolved threads in section but missing Disposition + proof (Commit/Evidence/Backlog):"
            )
            for u in missing_disposition:
                print(f"  - {u}")
            print()
        print("Fix: In Fixed in Commit Mapping, for each resolved thread add:")
        print("  Disposition: FIXED | NOT-A-BUG | DEFERRED")
        print("  and one of: Commit: / Evidence: / Backlog:")
        sys.exit(1)

    # Commit-after-comment guard: mapping must reference a commit made AFTER the comment
    commit_after_violations = _check_commit_after_comment(resolved_threads, section)
    if commit_after_violations:
        print(
            "ERROR: Commit-after-comment policy violated. Map only commits made AFTER the comment.\n"
        )
        for v in commit_after_violations:
            print(f"  - {v}")
        print(
            "\nFix: Make a code/doc fix commit, then add '- <thread_url> -> <commit_sha>' in Fixed in Commit Mapping."
        )
        sys.exit(1)

    print(
        f"OK: All {len(resolved_threads)} resolved review threads have Disposition + proof and commit-after-comment."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
