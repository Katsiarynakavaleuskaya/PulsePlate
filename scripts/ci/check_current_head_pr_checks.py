#!/usr/bin/env python3
"""Filter GitHub PR checks down to the latest current-head view for merge triage."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import urllib.error
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CheckEntry:
    """Normalized status-check entry for deterministic filtering."""

    name: str
    source_kind: str
    state: str
    timestamp: str
    details_url: str
    workflow_name: str


REPO_ROOT = Path(__file__).resolve().parents[2]
PENDING_STATUS_CONTEXT_STATES = {"EXPECTED", "PENDING"}


def _github_token() -> str:
    """Return the preferred GitHub token from environment."""
    return os.getenv("GH_TOKEN", "").strip() or os.getenv("GITHUB_TOKEN", "").strip()


def _api_request(
    url: str, token: str, method: str = "GET", payload: dict[str, Any] | None = None
) -> Any:
    """Perform one GitHub API request and decode JSON response."""
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pulseplate-current-head-checks",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "api.github.com":
        raise ValueError(f"Unsupported API URL: {url}")

    path = parsed.path
    if parsed.query:
        path = f"{path}?{parsed.query}"

    conn = http.client.HTTPSConnection(parsed.netloc, timeout=30)
    try:
        conn.request(method=method, url=path, body=data, headers=headers)
        response = conn.getresponse()
        body = response.read().decode("utf-8")
    finally:
        conn.close()

    if response.status >= 400:
        raise urllib.error.HTTPError(
            url=url,
            code=response.status,
            msg=response.reason,
            hdrs=response.headers,
            fp=None,
        )
    return json.loads(body)


def _extract_pr_context(event_path: Path) -> tuple[int, str]:
    """Read event payload and return (pr_number, repo)."""
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    pr = payload.get("pull_request") or {}
    number = int(pr.get("number", 0))
    repo = str((payload.get("repository") or {}).get("full_name", ""))
    return number, repo


def _fetch_pr_metadata(
    pr_number: int, repo: str, token: str
) -> tuple[bool, str, str, list[dict[str, Any]]]:
    """Fetch draft state, merge state, base branch, and raw status-check nodes."""
    owner, name = repo.split("/", maxsplit=1)
    query = """
    query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $number) {
          isDraft
          mergeStateStatus
          baseRefName
          statusCheckRollup {
            contexts(first: 100, after: $cursor) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                __typename
                ... on CheckRun {
                  name
                  status
                  conclusion
                  startedAt
                  completedAt
                  detailsUrl
                  checkSuite {
                    workflowRun {
                      workflow {
                        name
                      }
                    }
                  }
                }
                ... on StatusContext {
                  context
                  state
                  createdAt
                  targetUrl
                }
              }
            }
          }
        }
      }
    }
    """
    cursor: str | None = None
    nodes: list[dict[str, Any]] = []
    is_draft = False
    merge_state = ""
    base_ref = ""
    while True:
        response = _api_request(
            "https://api.github.com/graphql",
            token=token,
            method="POST",
            payload={
                "query": query,
                "variables": {
                    "owner": owner,
                    "name": name,
                    "number": pr_number,
                    "cursor": cursor,
                },
            },
        )
        pr = response.get("data", {}).get("repository", {}).get("pullRequest", {})
        is_draft = bool(pr.get("isDraft", False))
        merge_state = str(pr.get("mergeStateStatus") or "")
        base_ref = str(pr.get("baseRefName") or "")
        contexts = (pr.get("statusCheckRollup") or {}).get("contexts") or {}
        nodes.extend(contexts.get("nodes") or [])
        page_info = contexts.get("pageInfo") or {}
        if not page_info.get("hasNextPage", False):
            break
        cursor = page_info.get("endCursor")
        if not cursor:
            break
    return is_draft, merge_state, base_ref, nodes


def _fetch_required_check_names(repo: str, base_ref: str, token: str) -> tuple[set[str], bool]:
    """Fetch required check names from branch protection.

    Returns `(required_names, metadata_available)`.
    `metadata_available=False` means GitHub did not expose branch-protection data,
    so the caller must not treat non-required checks as blocking.
    """
    if not base_ref:
        return set(), False
    owner, name = repo.split("/", maxsplit=1)
    url = (
        f"https://api.github.com/repos/{owner}/{name}/branches/"
        f"{urllib.parse.quote(base_ref, safe='')}/protection/required_status_checks"
    )
    try:
        data = _api_request(url, token=token)
    except urllib.error.HTTPError as exc:
        if exc.code in {403, 404}:
            return set(), False
        raise

    required: set[str] = set()
    for item in data.get("contexts") or []:
        if isinstance(item, str) and item.strip():
            required.add(item.strip())
    for item in data.get("checks") or []:
        context = str((item or {}).get("context") or "").strip()
        if context:
            required.add(context)
    return required, True


def _normalize_node(node: dict[str, Any]) -> CheckEntry:
    """Normalize a GraphQL check node into a deterministic entry."""
    node_type = str(node.get("__typename") or "")
    if node_type == "CheckRun":
        name = str(node.get("name") or "").strip()
        status = str(node.get("status") or "").strip().upper()
        conclusion = str(node.get("conclusion") or "").strip().upper()
        if status in {"QUEUED", "IN_PROGRESS", "PENDING", "REQUESTED", "WAITING"}:
            state = "pending"
        elif conclusion in {
            "FAILURE",
            "TIMED_OUT",
            "CANCELLED",
            "ACTION_REQUIRED",
            "STALE",
            "STARTUP_FAILURE",
        }:
            state = "failed"
        else:
            state = "passed"
        workflow_name = str(
            (((node.get("checkSuite") or {}).get("workflowRun") or {}).get("workflow") or {}).get(
                "name"
            )
            or ""
        ).strip()
        timestamp = str(node.get("completedAt") or node.get("startedAt") or "")
        return CheckEntry(
            name=name,
            source_kind="check_run",
            state=state,
            timestamp=timestamp,
            details_url=str(node.get("detailsUrl") or ""),
            workflow_name=workflow_name,
        )

    name = str(node.get("context") or "").strip()
    raw_state = str(node.get("state") or "").strip().upper()
    if raw_state == "SUCCESS":
        state = "passed"
    elif raw_state in PENDING_STATUS_CONTEXT_STATES:
        state = "pending"
    else:
        state = "failed"
    return CheckEntry(
        name=name,
        source_kind="status_context",
        state=state,
        timestamp=str(node.get("createdAt") or ""),
        details_url=str(node.get("targetUrl") or ""),
        workflow_name="",
    )


def _latest_entries(entries: list[CheckEntry]) -> tuple[dict[str, CheckEntry], list[CheckEntry]]:
    """Split latest-per-name entries from superseded historical entries."""
    latest: dict[str, CheckEntry] = {}
    superseded: list[CheckEntry] = []
    for entry in sorted(entries, key=lambda item: (item.name, item.timestamp, item.details_url)):
        previous = latest.get(entry.name)
        if previous is None or (entry.timestamp, entry.details_url) >= (
            previous.timestamp,
            previous.details_url,
        ):
            if previous is not None:
                superseded.append(previous)
            latest[entry.name] = entry
        else:
            superseded.append(entry)
    return latest, superseded


def _required_snapshot(
    latest_entries: dict[str, CheckEntry], required_names: set[str]
) -> list[CheckEntry]:
    """Build required-check snapshot, inserting pending placeholders when missing."""
    snapshot: list[CheckEntry] = []
    for name in sorted(required_names):
        entry = latest_entries.get(name)
        if entry is None:
            snapshot.append(
                CheckEntry(
                    name=name,
                    source_kind="missing",
                    state="pending",
                    timestamp="",
                    details_url="",
                    workflow_name="",
                )
            )
        else:
            snapshot.append(entry)
    return snapshot


def _format_entry(entry: CheckEntry) -> str:
    """Render one check entry for terminal output."""
    source = f" [{entry.workflow_name}]" if entry.workflow_name else ""
    url = f" -> {entry.details_url}" if entry.details_url else ""
    return f"- {entry.name}: {entry.state}{source}{url}"


def _print_entries(title: str, entries: list[CheckEntry]) -> None:
    """Print a deterministic check-entry section."""

    print(title)
    if not entries:
        print("- none")
        return
    for entry in sorted(entries, key=lambda item: item.name):
        print(_format_entry(entry))


def main(argv: list[str] | None = None) -> int:
    """Validate current-head checks and filter superseded noise."""
    parser = argparse.ArgumentParser(
        description="Filter GitHub PR checks to the latest current-head view."
    )
    parser.add_argument("--event-path", default="", help="GitHub event payload path.")
    parser.add_argument("--pr-number", type=int, help="PR number for local runs.")
    parser.add_argument("--repo", default="", help="Repo owner/name for local runs.")
    args = parser.parse_args(argv)

    if args.event_path and (args.pr_number is not None or args.repo.strip()):
        parser.error("Use either --event-path or --pr-number/--repo, not both.")
    if (args.pr_number is not None) != bool(args.repo.strip()):
        parser.error("For local mode provide both --pr-number and --repo.")

    token = _github_token()
    if not token:
        print("ERROR: GH_TOKEN or GITHUB_TOKEN is required for current-head check filtering.")
        return 1

    if args.event_path:
        pr_number, repo = _extract_pr_context(Path(args.event_path))
    else:
        pr_number = args.pr_number or 0
        repo = args.repo.strip()

    if not pr_number or not repo:
        print("current-head-checks: no PR context found; skipping.")
        return 0

    try:
        is_draft, merge_state, base_ref, nodes = _fetch_pr_metadata(pr_number, repo, token)
        required_names, required_metadata_available = _fetch_required_check_names(
            repo, base_ref, token
        )
    except urllib.error.HTTPError as exc:
        print(f"ERROR: failed to query GitHub check state: HTTP {exc.code}")
        return 1

    if is_draft:
        print("current-head-checks: PR is draft; skipping strict checks.")
        return 0

    latest, superseded = _latest_entries([_normalize_node(node) for node in nodes if node])
    current_required = (
        _required_snapshot(latest, required_names) if required_metadata_available else []
    )
    _print_entries("Current-head required checks:", current_required)

    if not required_metadata_available:
        print(
            "Required check metadata unavailable; merge gating falls back to GitHub "
            "mergeStateStatus and reports current-head checks as advisory only."
        )
        _print_entries("Current-head advisory checks:", list(latest.values()))

    noisy_superseded = [entry for entry in superseded if entry.state != "passed"]
    if noisy_superseded:
        print("Superseded non-blocking checks:")
        for entry in sorted(noisy_superseded, key=lambda item: (item.name, item.timestamp)):
            print(_format_entry(entry))

    blocking_entries = [entry for entry in current_required if entry.state in {"pending", "failed"}]
    if merge_state != "CLEAN" or blocking_entries:
        print("ERROR: current-head check filter failed.")
        print(f"- GitHub mergeStateStatus={merge_state or 'UNKNOWN'}")
        if blocking_entries:
            print("- Blocking current-head checks remain pending or failed.")
        return 1

    # RU/EN: superseded failures stay visible but non-blocking once latest head is clean.
    print("current-head-checks: passed.")
    print("Superseded historical failures are visible above but treated as non-blocking.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
