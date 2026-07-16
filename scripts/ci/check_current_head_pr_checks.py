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
from datetime import datetime, timezone
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
    conclusion: str
    app_database_id: int | None = None
    app_slug: str = ""


REPO_ROOT = Path(__file__).resolve().parents[2]
_MAX_STATUS_CHECK_PAGES = 100
PENDING_STATUS_CONTEXT_STATES = {"EXPECTED", "PENDING"}
CANONICAL_FALLBACK_STATUS_CONTEXT_NAMES = {"CI"}
CANONICAL_FALLBACK_WORKFLOW_NAMES = {"CI"}
CANONICAL_FALLBACK_CI_CHECK_NAMES = {
    "Determine changed paths (for conditional jobs)",
    "pr_scope_guard",
    "Trivy ignore-policy expiry",
    "Ruby jwt/Fastlane unblock guard",
    "Pygments exception seam guard",
    "Docs Phase1 gates",
    "PR Body Phase2 gates",
    "Merge readiness gate",
    "Private Python proxy health",
    "lint",
    "security",
    "OpenAPI sync (backend -> frontend artifacts)",
    "test-pr (3.13)",
    "test-main (3.11, 60)",
    "test-main (3.12, 90)",
    "test-main (3.13, 90)",
    "coverage-pr",
    "diff-coverage",
}
DOCKER_FALLBACK_WORKFLOW_NAMES = {"Docker Build and Push"}
SECURITY_FALLBACK_CHECK_NAMES = {"security-scan"}
DOCKER_RELEASE_ONLY_FALLBACK_CHECK_NAMES = {"publish"}
DOCKER_SURFACE_PREFIXES = {
    ".dockerignore",
    ".trivyignore",
    ".github/workflows/build.yml",
    ".github/workflows/cd.yml",
    "Dockerfile",
    "docker-compose",
    "docs/telemetry/docker_image_",
    "constraints.txt",
    "requirements-docker-runtime.in",
    "requirements-docker-runtime.txt",
    "scripts/ci/check_docker_image_budget.py",
    "scripts/ci/check_docker_runtime_dependency_surface.py",
    "scripts/ci/check_python_startup_hooks.py",
    "scripts/ci/docker_image_telemetry.py",
    "scripts/ci/emergency_python_wheels.json",
    "scripts/ci/fetch_docker_image_baseline.py",
    "scripts/ci/install_locked_python_requirements.py",
    "trivy/",
}
FRONTEND_FALLBACK_WORKFLOW_NAMES = {"Frontend CI"}
FRONTEND_SURFACE_PREFIXES = {
    ".github/actions/npm-ci-with-retry/",
    ".github/actions/python-setup/",
    ".github/workflows/frontend-ci.yml",
    ".nvmrc",
    "constraints.txt",
    "docs/design/",
    "docs/figma/",
    "docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md",
    "docs/roadmap/BACKLOG_LEDGER.md",
    "docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md",
    "docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md",
    "frontend/",
    "ios/PulsePlate/Assets.xcassets/AccentGreen.colorset/",
    "ios/PulsePlate/Assets.xcassets/AppPrimary.colorset/",
    "ios/PulsePlate/Assets.xcassets/Gold.colorset/",
    "ios/PulsePlate/Assets.xcassets/HeartRed.colorset/",
    "ios/PulsePlate/Assets.xcassets/Navy.colorset/",
    "ios/PulsePlate/DesignSystem/",
    "ios/PulsePlate/Extensions/Color+Assets.swift",
    "Makefile",
    "package.json",
    "package-lock.json",
    "requirements-ci-lite.in",
    "requirements-ci-lite.txt",
    "requirements.txt",
    "scripts/ci/check_python_startup_hooks.py",
    "scripts/ci/emergency_python_wheels.json",
    "scripts/ci/install_locked_python_requirements.py",
    "scripts/design_guard.py",
    "tests/test_design_invariant_guard.py",
    "tests/test_design_token_parity.py",
    "tests/test_frontend_raw_hex_guard.py",
    "tests/test_python_supply_chain_controls.py",
    "tokens/",
    "web/",
}
IOS_FALLBACK_CHECK_PREFIXES = {"iOS "}
IOS_SURFACE_PREFIXES = {
    "ios/",
    ".github/actions/",
    ".github/workflows/",
    "fastlane/",
}


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
                    createdAt
                    app {
                      databaseId
                      slug
                    }
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
    seen_cursors: set[str] = set()
    nodes: list[dict[str, Any]] = []
    is_draft = False
    merge_state = ""
    base_ref = ""
    for _page in range(_MAX_STATUS_CHECK_PAGES):
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
        if not isinstance(response, dict) or response.get("errors"):
            raise ValueError("GraphQL status-check response is malformed")
        data = response.get("data")
        repository_data = data.get("repository") if isinstance(data, dict) else None
        pr = repository_data.get("pullRequest") if isinstance(repository_data, dict) else None
        if not isinstance(pr, dict):
            raise ValueError("GraphQL status-check response is missing the pull request")
        raw_is_draft = pr.get("isDraft")
        if not isinstance(raw_is_draft, bool):
            raise ValueError("GraphQL pull request isDraft must be boolean")
        is_draft = raw_is_draft
        merge_state = str(pr.get("mergeStateStatus") or "")
        base_ref = str(pr.get("baseRefName") or "")
        rollup = pr.get("statusCheckRollup")
        contexts = rollup.get("contexts") if isinstance(rollup, dict) else None
        if not isinstance(contexts, dict):
            raise ValueError("GraphQL status-check response is missing contexts")
        page_nodes = contexts.get("nodes")
        if not isinstance(page_nodes, list) or not all(
            isinstance(node, dict) for node in page_nodes
        ):
            raise ValueError("GraphQL status-check nodes are malformed")
        nodes.extend(page_nodes)
        page_info = contexts.get("pageInfo") or {}
        if not isinstance(page_info, dict):
            raise ValueError("GraphQL status-check pageInfo is malformed")
        has_next_page = page_info.get("hasNextPage")
        if not isinstance(has_next_page, bool):
            raise ValueError("GraphQL status-check hasNextPage must be boolean")
        if not has_next_page:
            break
        next_cursor = page_info.get("endCursor")
        if not isinstance(next_cursor, str) or not next_cursor:
            raise ValueError("GraphQL status-check pagination cursor is malformed")
        if next_cursor in seen_cursors:
            raise ValueError("GraphQL status-check pagination cursor repeated")
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    else:
        raise ValueError("GraphQL status-check pagination exceeded page limit")
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


def _fetch_pr_changed_paths(pr_number: int, repo: str, token: str) -> set[str]:
    """Fetch changed file paths for touched-surface fallback routing."""
    owner, name = repo.split("/", maxsplit=1)
    paths: set[str] = set()
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{owner}/{name}/pulls/{pr_number}/files"
            f"?per_page=100&page={page}"
        )
        data = _api_request(url, token=token)
        if not data:
            break
        for item in data:
            paths.update(_changed_paths_from_pr_file(item or {}))
        if len(data) < 100:
            break
        page += 1
    return paths


def _changed_paths_from_pr_file(item: dict[str, Any]) -> set[str]:
    """Return current and previous paths for one PR file API item."""
    paths: set[str] = set()
    filename = str(item.get("filename") or "").strip()
    if filename:
        paths.add(filename)
    previous_filename = str(item.get("previous_filename") or "").strip()
    if previous_filename:
        paths.add(previous_filename)
    return paths


def _normalize_node(node: dict[str, Any]) -> CheckEntry:
    """Normalize a GraphQL check node into a deterministic entry."""
    node_type = str(node.get("__typename") or "")
    if node_type == "CheckRun":
        name = str(node.get("name") or "").strip()
        status = str(node.get("status") or "").strip().upper()
        conclusion = str(node.get("conclusion") or "").strip().upper()
        if status in {"QUEUED", "IN_PROGRESS", "PENDING", "REQUESTED", "WAITING"}:
            state = "pending"
        elif status == "COMPLETED" and conclusion == "SUCCESS":
            state = "passed"
        else:
            state = "failed"
        check_suite = node.get("checkSuite")
        if not isinstance(check_suite, dict):
            raise ValueError(
                f"CheckRun {name or '<unnamed>'!r} is missing valid checkSuite.createdAt"
            )
        workflow_run = check_suite.get("workflowRun")
        if workflow_run is None:
            workflow_run = {}
        if not isinstance(workflow_run, dict):
            raise ValueError(f"CheckRun {name or '<unnamed>'!r} has malformed workflowRun")
        workflow = workflow_run.get("workflow")
        if workflow is None:
            workflow = {}
        if not isinstance(workflow, dict):
            raise ValueError(f"CheckRun {name or '<unnamed>'!r} has malformed workflow")
        workflow_name = str(workflow.get("name") or "").strip()
        app = check_suite.get("app")
        if app is None:
            app = {}
        if not isinstance(app, dict):
            raise ValueError(f"CheckRun {name or '<unnamed>'!r} has malformed app identity")
        raw_app_database_id = app.get("databaseId")
        app_database_id = (
            raw_app_database_id
            if isinstance(raw_app_database_id, int)
            and not isinstance(raw_app_database_id, bool)
            and raw_app_database_id > 0
            else None
        )
        app_slug = str(app.get("slug") or "").strip()
        # Order every CheckRun by one attempt-creation clock. ``startedAt`` is
        # null while queued and can be later than a newer queued suite when an
        # older run waits for capacity. Mixing those clocks can select stale
        # success, so CheckSuite.createdAt is the only ordering authority.
        timestamp = _normalize_timestamp(
            check_suite.get("createdAt"),
            label=f"CheckRun {name or '<unnamed>'!r} checkSuite.createdAt",
        )
        return CheckEntry(
            name=name,
            source_kind="check_run",
            state=state,
            timestamp=timestamp,
            details_url=str(node.get("detailsUrl") or ""),
            workflow_name=workflow_name,
            conclusion=conclusion,
            app_database_id=app_database_id,
            app_slug=app_slug,
        )

    name = str(node.get("context") or "").strip()
    raw_state = str(node.get("state") or "").strip().upper()
    if raw_state == "SUCCESS":
        state = "passed"
    elif raw_state in PENDING_STATUS_CONTEXT_STATES:
        state = "pending"
    else:
        state = "failed"
    timestamp = _normalize_timestamp(
        node.get("createdAt"),
        label=f"StatusContext {name or '<unnamed>'!r} createdAt",
    )
    return CheckEntry(
        name=name,
        source_kind="status_context",
        state=state,
        timestamp=timestamp,
        details_url=str(node.get("targetUrl") or ""),
        workflow_name="",
        conclusion="",
        app_database_id=None,
        app_slug="",
    )


def _normalize_timestamp(value: Any, *, label: str) -> str:
    """Validate one timezone-aware ISO-8601 value and canonicalize it to UTC."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is missing or invalid")
    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} is missing or invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} is missing or invalid")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _latest_entries(entries: list[CheckEntry]) -> tuple[dict[str, CheckEntry], list[CheckEntry]]:
    """Split latest-per-name entries from superseded historical entries."""

    def attempt_order_key(entry: CheckEntry) -> tuple[str, int, str]:
        # Equal CheckSuite creation times cannot prove attempt order. Prefer a
        # blocking or non-SUCCESS CheckRun over exact success so URL
        # lexicography can never create a false green. Status contexts have no
        # conclusion field, so their normalized passed state remains exact.
        exact_success = entry.state == "passed" and (
            entry.source_kind != "check_run" or entry.conclusion == "SUCCESS"
        )
        fail_closed_rank = 0 if exact_success else 1
        return entry.timestamp, fail_closed_rank, entry.details_url

    latest: dict[str, CheckEntry] = {}
    superseded: list[CheckEntry] = []
    for entry in sorted(entries, key=lambda item: (item.name, *attempt_order_key(item))):
        previous = latest.get(entry.name)
        if previous is None or attempt_order_key(entry) >= attempt_order_key(previous):
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
                    conclusion="",
                )
            )
        else:
            snapshot.append(entry)
    return snapshot


def _path_touches_any(paths: set[str], prefixes: set[str]) -> bool:
    """Return whether any changed path attaches a fallback surface."""
    return any(path == prefix or path.startswith(prefix) for path in paths for prefix in prefixes)


def _is_blocking_fallback_advisory(entry: CheckEntry, changed_paths: set[str]) -> bool:
    """Return whether fallback merge gating must block on this advisory entry."""
    if (
        entry.workflow_name in DOCKER_FALLBACK_WORKFLOW_NAMES
        and entry.name in DOCKER_RELEASE_ONLY_FALLBACK_CHECK_NAMES
        and entry.conclusion == "SKIPPED"
    ):
        return False
    if entry.state not in {"pending", "failed"}:
        return False
    if entry.source_kind == "status_context":
        return entry.name in CANONICAL_FALLBACK_STATUS_CONTEXT_NAMES
    if entry.source_kind != "check_run":
        return False
    if any(entry.name.startswith(prefix) for prefix in IOS_FALLBACK_CHECK_PREFIXES):
        return _path_touches_any(changed_paths, IOS_SURFACE_PREFIXES)
    if entry.workflow_name in CANONICAL_FALLBACK_WORKFLOW_NAMES:
        return entry.name in CANONICAL_FALLBACK_CI_CHECK_NAMES
    if entry.workflow_name in DOCKER_FALLBACK_WORKFLOW_NAMES:
        return entry.name in SECURITY_FALLBACK_CHECK_NAMES or _path_touches_any(
            changed_paths, DOCKER_SURFACE_PREFIXES
        )
    if entry.workflow_name in FRONTEND_FALLBACK_WORKFLOW_NAMES:
        return _path_touches_any(changed_paths, FRONTEND_SURFACE_PREFIXES)
    return False


def _partition_fallback_advisory_entries(
    entries: list[CheckEntry], changed_paths: set[str]
) -> tuple[list[CheckEntry], list[CheckEntry]]:
    """Split fallback-blocking entries from advisory-only entries.

    RU: В fallback-режиме canonical PR checks и security scans блокируют merge;
    остальные specialized checks блокируют когда changed paths прикрепляют surface.
    EN: In fallback mode, canonical PR checks and security scans block merge;
    other specialized checks block when changed paths attach that surface.
    """

    blocking_entries: list[CheckEntry] = []
    advisory_only_entries: list[CheckEntry] = []
    for entry in entries:
        if _is_blocking_fallback_advisory(entry, changed_paths):
            blocking_entries.append(entry)
        else:
            advisory_only_entries.append(entry)
    return blocking_entries, advisory_only_entries


def _suppress_stale_latest_entries_with_newer_workflow_activity(
    entries: list[CheckEntry],
    latest: dict[str, CheckEntry],
    superseded: list[CheckEntry],
) -> tuple[dict[str, CheckEntry], list[CheckEntry]]:
    """Demote stale latest entries when a newer run from the same workflow exists.

    RU: Если у того же workflow на этом же SHA уже есть более новый activity,
    older status из предыдущего workflow run не должен считаться latest signal
    даже если новое выполнение ещё не выпустило тот же job name.
    EN: If the same workflow has newer activity on the same SHA, an older status
    from a previous workflow run is stale noise even when the newer run has not
    emitted that exact job name yet.
    """

    newest_workflow_timestamp: dict[str, str] = {}
    for entry in entries:
        if not entry.workflow_name:
            continue
        previous = newest_workflow_timestamp.get(entry.workflow_name)
        if previous is None or entry.timestamp >= previous:
            newest_workflow_timestamp[entry.workflow_name] = entry.timestamp

    filtered_latest = dict(latest)
    updated_superseded = list(superseded)
    for name, entry in list(filtered_latest.items()):
        if not entry.workflow_name:
            continue
        latest_workflow_timestamp = newest_workflow_timestamp.get(entry.workflow_name)
        if latest_workflow_timestamp and latest_workflow_timestamp > entry.timestamp:
            updated_superseded.append(entry)
            del filtered_latest[name]
    return filtered_latest, updated_superseded


def _format_entry(entry: CheckEntry) -> str:
    """Render one check entry for terminal output."""
    display_state = "skipped" if entry.conclusion == "SKIPPED" else entry.state
    source = f" [{entry.workflow_name}]" if entry.workflow_name else ""
    url = f" -> {entry.details_url}" if entry.details_url else ""
    return f"- {entry.name}: {display_state}{source}{url}"


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
        normalized_entries = [_normalize_node(node) for node in nodes if node]
    except urllib.error.HTTPError as exc:
        print(f"ERROR: failed to query GitHub check state: HTTP {exc.code}")
        return 1
    except ValueError as exc:
        print(f"ERROR: failed to validate GitHub check state: {exc}")
        return 1

    if is_draft:
        print("current-head-checks: PR is draft; skipping strict checks.")
        return 0

    latest, superseded = _latest_entries(normalized_entries)
    latest, superseded = _suppress_stale_latest_entries_with_newer_workflow_activity(
        normalized_entries,
        latest,
        superseded,
    )
    current_required = (
        _required_snapshot(latest, required_names) if required_metadata_available else []
    )
    advisory_entries = list(latest.values()) if not required_metadata_available else []
    advisory_blocking_entries: list[CheckEntry] = []
    _print_entries("Current-head required checks:", current_required)

    if not required_metadata_available:
        try:
            changed_paths = _fetch_pr_changed_paths(pr_number, repo, token)
        except urllib.error.HTTPError as exc:
            print(f"ERROR: failed to query GitHub changed files: HTTP {exc.code}")
            return 1
        advisory_blocking_entries, advisory_entries = _partition_fallback_advisory_entries(
            advisory_entries, changed_paths
        )
        print(
            "Required check metadata unavailable; merge gating falls back to a "
            "fail-closed current-head check snapshot. Canonical PR checks and security "
            "scans remain blocking; other specialized checks block when changed files "
            "attach their surface."
        )
        if advisory_blocking_entries:
            _print_entries("Current-head blocking fallback checks:", advisory_blocking_entries)
        if advisory_entries:
            _print_entries("Current-head advisory checks:", advisory_entries)

    noisy_superseded = [entry for entry in superseded if entry.state != "passed"]
    if noisy_superseded:
        print("Superseded non-blocking checks:")
        for entry in sorted(noisy_superseded, key=lambda item: (item.name, item.timestamp)):
            print(_format_entry(entry))

    blocking_entries = [entry for entry in current_required if entry.state in {"pending", "failed"}]
    merge_state_note_needed = not required_metadata_available and merge_state != "CLEAN"
    if blocking_entries or advisory_blocking_entries:
        print("ERROR: current-head check filter failed.")
        if merge_state_note_needed:
            print(f"- GitHub mergeStateStatus={merge_state or 'UNKNOWN'}")
        if blocking_entries:
            print("- Blocking current-head checks remain pending or failed.")
        if advisory_blocking_entries:
            print("- Blocking fallback current-head checks remain pending or failed.")
        return 1

    if merge_state_note_needed:
        print(
            f"NOTE: GitHub mergeStateStatus={merge_state or 'UNKNOWN'} is stale/non-blocking "
            "because required check metadata is unavailable and no fallback-blocking "
            "current-head checks are pending or failed."
        )

    # RU/EN: superseded failures stay visible but non-blocking once latest head is clean.
    print("current-head-checks: passed.")
    print("Superseded historical failures are visible above but treated as non-blocking.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
