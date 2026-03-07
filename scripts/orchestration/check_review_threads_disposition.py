#!/usr/bin/env python3
"""
Guard: resolved review threads must have explicit Disposition records in canonical artifact.

Strict mode: every resolved thread must be listed under **Fixed in Commit Mapping**
in docs/review/PR_<N>_FIXED_MAPPING.md with Disposition (FIXED | NOT-A-BUG | DEFERRED)
and proof (Commit / Evidence / Backlog).

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
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.review_mapping_artifact import (
    extract_fixed_mapping_section as _artifact_extract_fixed_mapping,
    read_mapping_artifact,
)

DISPOSITION_RE = re.compile(r"Disposition:\s*(FIXED|NOT-A-BUG|DEFERRED)", re.IGNORECASE)
PROOF_RE = re.compile(r"(Commit:|Evidence:|Backlog:)", re.IGNORECASE)


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
# Relaxed: match mapping-like lines to validate SHA (catches "- url -> notasha")
_MAPPING_LINE_RELAXED_RE = re.compile(r"^\s*-\s*(https://[^\s]+)\s*->\s*(\S+)", re.IGNORECASE)


def _gh_path() -> str:
    """Resolved path to gh CLI (B607 / Sourcery: no partial path in subprocess)."""
    path = shutil.which("gh")
    if not path:
        raise RuntimeError("gh CLI not found in PATH")
    return path


def _run(cmd: list[str]) -> str:
    # Sourcery: use resolved binary path; argv from callers is fixed (no user input)
    argv = list(cmd)
    if argv and argv[0] == "gh":
        argv = [_gh_path()] + argv[1:]
    result = subprocess.run(  # nosec B603: argv from _gh_path()+static; no user input (remove-by: 2026-04-30, ref: PR-985)
        argv,
        capture_output=True,
        text=True,
        timeout=_RUN_TIMEOUT_SEC,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(argv)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
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


# Allow only git rev format (7–40 hex chars) so argv is safe (Sourcery / injection)
_GIT_SHA_RE = re.compile(r"^[a-f0-9]{7,40}$", re.IGNORECASE)

# Trigger-only commit subject patterns (P1: ban mapping to rerun/trigger commits)
_TRIGGER_SUBJECT_RE = re.compile(
    r"(?:^|\b)(trigger\s+ci|re-?run\s+ci|re-?run\s+checks)(?:\b|$)",
    re.IGNORECASE,
)


def _git_commit_time_iso(commit_sha: str) -> str:
    """
    Return commit committer date in strict ISO 8601 (git %cI).
    Uses absolute git path; commit_sha validated so argv is safe (no injection).
    """
    if not _GIT_SHA_RE.match(commit_sha.strip()):
        raise RuntimeError(f"Invalid commit SHA format: {commit_sha!r}")
    git_path = shutil.which("git")
    if not git_path:
        raise RuntimeError("git not found in PATH; required for commit-after-comment guard")
    result = subprocess.run(  # nosec B603: git_path from which(); commit_sha validated by _GIT_SHA_RE (remove-by: 2026-04-30, ref: PR-985)
        [git_path, "show", "-s", "--format=%cI", commit_sha.strip()],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SEC,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git show failed for sha={commit_sha}: rc={result.returncode} stderr={result.stderr.strip()!r}"
        )
    out = result.stdout.strip()
    if not out:
        raise RuntimeError(f"git returned empty commit time for sha={commit_sha}")
    return out


def _git_commit_subject(commit_sha: str) -> str:
    """Return commit subject line for a SHA (git show -s --format=%s). SHA validated for safe argv."""
    sha = commit_sha.strip()
    if not _GIT_SHA_RE.match(sha):
        raise RuntimeError(f"Invalid commit SHA format: {commit_sha!r}")
    git_path = shutil.which("git")
    if not git_path:
        raise RuntimeError("git not found in PATH; required for trigger-only mapping guard")
    result = subprocess.run(  # nosec B603: fixed argv, sha validated (remove-by: 2026-04-30, ref: PR-985)
        [git_path, "show", "-s", "--format=%s", sha],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SEC,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git show subject failed for sha={commit_sha}: rc={result.returncode} stderr={result.stderr.strip()!r}"
        )
    return result.stdout.strip()


def _git_changed_files(commit_sha: str) -> list[str]:
    """Return list of files changed in a SHA (git show --name-only). Empty means empty commit. SHA validated."""
    sha = commit_sha.strip()
    if not _GIT_SHA_RE.match(sha):
        raise RuntimeError(f"Invalid commit SHA format: {commit_sha!r}")
    git_path = shutil.which("git")
    if not git_path:
        raise RuntimeError("git not found in PATH; required for trigger-only mapping guard")
    result = subprocess.run(  # nosec B603: fixed argv, sha validated (remove-by: 2026-04-30, ref: PR-985)
        [git_path, "show", "--name-only", "--pretty=format:", sha],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SEC,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git show name-only failed for sha={commit_sha}: rc={result.returncode} stderr={result.stderr.strip()!r}"
        )
    return [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]


def _check_trigger_only_mapping(
    resolved_threads: list[ResolvedThreadRef],
    fixed_mapping_section: str,
) -> list[str]:
    """
    Validate that each mapped SHA is not trigger-only (empty commit or rerun/trigger subject).
    Returns list of violation messages; empty if all pass.
    """
    mapping = _parse_mapping_section(fixed_mapping_section)
    violations: list[str] = []
    for t in resolved_threads:
        sha = mapping.get(t.url)
        if not sha:
            continue
        changed_files = _git_changed_files(sha)
        if not changed_files:
            violations.append(
                f"{t.url}: mapped to {sha} but commit is EMPTY (no changed files). "
                "Trigger-only commits are not valid FIXED proof."
            )
            continue
        subject = _git_commit_subject(sha)
        if _TRIGGER_SUBJECT_RE.search(subject):
            violations.append(
                f"{t.url}: mapped to {sha} but commit subject looks like CI rerun/trigger "
                f"('{subject}'). Trigger-only commits are not valid FIXED proof."
            )
    return violations


def _parse_mapping_section(section: str) -> dict[str, str]:
    """
    Parse Fixed in Commit Mapping section: lines like "- https://... -> sha".
    Returns dict mapping full URL -> sha only (thread-specific; no base URL to avoid one URL satisfying multiple threads).
    """
    mapping: dict[str, str] = {}
    for line in section.splitlines():
        m = _MAPPING_LINE_RE.search(line)
        if not m:
            continue
        url_part, sha = m.group(1).strip(), m.group(2)
        mapping[url_part] = sha
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
        sha = mapping_by_url.get(t.url)
        if not sha:
            # Thread may be FIXED (needs SHA) or NOT-A-BUG/DEFERRED (Evidence/Backlog only); only FIXED with -> sha is checked here
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


def _graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    # Sourcery: no dynamic argv — pass body via stdin (static argv only)
    body = json.dumps({"query": query, "variables": variables})
    result = subprocess.run(  # nosec B603: argv static; body via stdin only (remove-by: 2026-04-30, ref: PR-985)
        [_gh_path(), "api", "graphql", "--input", "-"],
        input=body,
        capture_output=True,
        text=True,
        timeout=_RUN_TIMEOUT_SEC,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh api graphql failed: {result.returncode}\nSTDERR:\n{result.stderr}")
    data = json.loads(result.stdout)
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return cast(dict[str, Any], data["data"])


def _get_owner_repo() -> tuple[str, str]:
    owner = _run(["gh", "repo", "view", "--json", "owner", "-q", ".owner.login"]).strip()
    name = _run(["gh", "repo", "view", "--json", "name", "-q", ".name"]).strip()
    if not owner or not name:
        raise RuntimeError("Unable to detect owner/repo via gh repo view.")
    return owner, name


def _find_disposition_block_in_section(section: str, url: str) -> bool:
    """
    Thread-specific URL (full URL with anchor) must appear in section with Disposition + proof
    (Commit/Evidence/Backlog). For single-block artifacts, Disposition+Proof at top applies to
    all mapping lines; scan only lines containing this exact thread URL so one mapping does not
    satisfy multiple threads (CodeRabbit/Sourcery/Cubic). Use a ±25 line window to cover the
    repo's single-block artifact layout while still keeping the scan local to the matched URL.
    Use exact URL match to avoid substring false positives (e.g. discussion_r1 vs discussion_r10).
    """
    lines = section.splitlines()
    url_pattern = re.escape(url) + r"(?![0-9a-zA-Z])"
    for i, line in enumerate(lines):
        if re.search(url_pattern, line):
            start = max(0, i - 25)
            end = min(len(lines), i + 26)
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
    # Sourcery/B607: use resolved path only; argv is static
    try:
        result = subprocess.run(  # nosec B603: argv [_gh_path(), "auth", "status"]; no user input (remove-by: 2026-04-30, ref: PR-985)
            [_gh_path(), "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except RuntimeError:
        return False


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
    # Sourcery/B607: argv is [resolved_gh_path, "auth", "status"] — no user input
    try:
        argv = [_gh_path(), "auth", "status"]
    except RuntimeError:
        print("ERROR: gh CLI not found in PATH; required when GH_TOKEN is set.")
        sys.exit(1)
    result = subprocess.run(  # nosec B603: argv from _gh_path()+static; no user input (remove-by: 2026-04-30, ref: PR-985)
        argv,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        print("ERROR: GH_TOKEN is set but gh auth status failed. Fix env before running GraphQL.")
        print(f"       Env: {_env_diagnostic()}")
        print("  gh auth status  # run manually to see reason")
        sys.stderr.write(result.stderr or "")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check resolved review threads have disposition in canonical artifact."
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
    try:
        artifact_text = read_mapping_artifact(pr_number)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    section = _artifact_extract_fixed_mapping(artifact_text)

    if not section:
        print(
            f"ERROR: Missing '## Fixed in Commit Mapping' section in canonical artifact "
            f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
        )
        sys.exit(1)

    # Reject invalid FIXED mappings: validate raw section for any "- url -> X" lines
    for line in section.splitlines():
        m = _MAPPING_LINE_RELAXED_RE.search(line.strip())
        if m:
            url_part, sha_part = m.group(1), m.group(2).strip()
            if not _GIT_SHA_RE.match(sha_part):
                print(
                    f"ERROR: Invalid FIXED mapping in artifact: {url_part} -> {sha_part!r} "
                    "(SHA must be 7–40 hex chars)"
                )
                sys.exit(1)

    # Reject invalid FIXED blocks: Commit: value must be valid SHA or known placeholder
    if re.search(r"Disposition:\s*FIXED\b", section, re.IGNORECASE):
        commit_re = re.compile(r"Commit:\s*(.+)$", re.IGNORECASE)
        for line in section.splitlines():
            mo = commit_re.search(line.strip())
            if mo:
                val = mo.group(1).strip()
                if not _GIT_SHA_RE.match(val) and val.lower() != "see mapping entries below":
                    print(
                        f"ERROR: Invalid Commit value in FIXED block: {val!r} "
                        "(must be 7–40 hex chars or 'see mapping entries below')"
                    )
                    sys.exit(1)
    resolved_threads = _collect_resolved_threads(pr_number)

    if not resolved_threads:
        print("OK: No resolved review threads found (nothing to enforce).")
        sys.exit(0)

    missing_refs: list[str] = []
    missing_disposition: list[str] = []

    for t in resolved_threads:
        # Use exact URL match to avoid substring false positives (e.g. discussion_r1 vs r10)
        if not re.search(re.escape(t.url) + r"(?![0-9a-zA-Z])", section):
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

    # Trigger-only mapping ban (P1): mapping to empty or rerun/trigger subject is not valid FIXED proof
    trigger_violations = _check_trigger_only_mapping(resolved_threads, section)
    if trigger_violations:
        print("ERROR: Trigger-only commit policy violated. Map only real fix commits.\n")
        for v in trigger_violations:
            print(f"  - {v}")
        print(
            "\nFix: Do not map to empty commits or commits whose subject contains 'trigger ci' / 'rerun ci' / 'rerun checks'."
        )
        sys.exit(1)

    print(
        f"OK: All {len(resolved_threads)} resolved review threads have Disposition + proof and commit-after-comment."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
