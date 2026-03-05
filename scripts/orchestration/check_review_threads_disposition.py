#!/usr/bin/env python3
"""
Guard: resolved review threads must have explicit Disposition records in PR body.

Strict mode: every resolved thread must be listed under **Fixed in Commit Mapping**
with Disposition (FIXED | NOT-A-BUG | DEFERRED) and proof (Commit / Evidence / Backlog).

Requires: GitHub CLI `gh` authenticated. Run inside a PR branch.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed gh CLI only, no user input
import sys
from dataclasses import dataclass
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


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)  # nosec B603
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result.stdout


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
    """
    thread_base = url.split("#")[0]
    lines = section.splitlines()
    for i, line in enumerate(lines):
        if thread_base in line:
            start = max(0, i - 12)
            end = min(len(lines), i + 13)
            window = "\n".join(lines[start:end])
            return bool(DISPOSITION_RE.search(window) and PROOF_RE.search(window))
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
                nodes { url }
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
                resolved.append(
                    ResolvedThreadRef(
                        url=comment_nodes[0]["url"],
                        source="comment",
                        is_resolved=True,
                    )
                )
        page = pr["reviewThreads"]["pageInfo"]
        if not page["hasNextPage"]:
            break
        after = page["endCursor"]

    uniq: dict[str, ResolvedThreadRef] = {r.url: r for r in resolved}
    return list(uniq.values())


def main() -> None:
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

    print(
        f"OK: All {len(resolved_threads)} resolved review threads have Disposition + proof in Fixed in Commit Mapping."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
