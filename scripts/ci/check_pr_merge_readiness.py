"""Review-governance merge gate for unresolved threads and bot-comment mapping.

This script does not classify current-head required checks; the canonical
required-check truth lives in `check_current_head_pr_checks.py` and the
`check_merge_ready.py` wrapper bundles both hard gates.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess  # nosec B404: bounded absolute git identity checks are required (remove-by: 2026-09-30, ref: PR-governance-material-seal)
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.review_mapping_artifact import (
    extract_fixed_mapping_section,
    has_no_actionable_marker,
    parse_canonical_fingerprint_records,
    parse_fixed_mapping_entries,
    read_mapping_artifact,
    review_seal_version,
    validate_mapping_artifact_text,
)
from scripts.orchestration.pr_commit_identity import (  # noqa: E402
    CommitIdentityError,
    CommitRefKind,
    PrSnapshot,
    RepositoryCommitRef,
    ReviewThreadEvidence,
    assert_snapshot_unchanged,
    classify_commit_ref,
    fetch_pr_snapshot,
    fetch_review_threads,
    is_ancestor,
)
from scripts.orchestration.pr_review_evidence import (  # noqa: E402
    ReviewEvidenceError,
    build_provider_no_claim_pair,
    compute_material_manifest,
    is_provider_no_claim_review_receipt,
    is_provider_no_claim_security_receipt,
    parse_embedded_review_seal,
    review_thread_inventory as _review_thread_inventory,
    validate_mapping_only_closeout_successor,
    validate_review_seal,
    validated_duplicate_reply_urls,
)
from scripts.ci.check_current_head_pr_checks import (  # noqa: E402
    DOCKER_SURFACE_PREFIXES,
    _fetch_pr_metadata as _fetch_current_head_pr_metadata,
    _latest_entries as _latest_check_entries,
    _normalize_node as _normalize_check_node,
    _path_touches_any,
    _suppress_stale_latest_entries_with_newer_workflow_activity as _suppress_stale_check_entries,
)
from scripts.ci.ci_risk_profile import build_risk_profile  # noqa: E402

# Set to governance PR number + 1 immediately after that PR is opened.  ``None``
# deliberately blocks CI v1 activation finalization until the PR number exists.
REVIEW_SEAL_REQUIRED_FROM_PR: int | None = 2142


def _review_seal_v1_required(pr_number: int, seal_version: str | None) -> bool:
    """Apply the rollout boundary while allowing this governance PR to opt in."""

    if seal_version == "v1":
        return True
    if REVIEW_SEAL_REQUIRED_FROM_PR is None:
        raise ValueError(
            "REVIEW_SEAL_REQUIRED_FROM_PR is pending; set it to the "
            "governance PR number + 1 before final validation"
        )
    return pr_number >= REVIEW_SEAL_REQUIRED_FROM_PR


ACTIONABLE_MARKERS = (
    "Actionable comments posted",
    "Potential issue",
    "Prompt for AI Agents",
    "P0:",
    "P1:",
    "P2:",
    "P3:",
)

NON_ACTIONABLE_MARKERS = (
    "No actionable comments were generated",
    "No issues found",
    "look great",
)

MAPPING_HEADING_RE = re.compile(r"(?im)^\s*###\s+Fixed\s+in\s+Commit\s+Mapping\s*$")
MAPPING_ENTRY_RE = re.compile(r"(?im)^\s*-\s*`?(https?://[^\s`]+)`?\s*->\s*`?[0-9a-f]{7,40}`?\s*$")
MAPPING_NO_ACTIONABLE_RE = re.compile(r"(?im)^\s*-\s*No actionable review comments\s*$")
CANONICAL_ARTIFACT_LINK_LINE_RE = re.compile(
    r"^ {0,3}-[ \t]+\[[^\]\n]+\]\(\s*"
    r"(?:<(?P<angle>[^>\n]+)>|(?P<plain>[^\s)\n]+))\s*\)"
    r"[ \t]*$",
    re.IGNORECASE,
)
FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
RAW_HTML_BLOCK_OPEN_RE = re.compile(
    r"^ {0,3}<(?P<tag>[A-Za-z][A-Za-z0-9-]*)(?:[\t />]|$)",
    re.IGNORECASE,
)
RAW_HTML_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_MAX_API_RESPONSE_BYTES = 8 * 1024 * 1024
_MAX_API_PAGES = 100
_MAX_OUTAGE_SECURITY_WAIT_SECONDS = 300
_REVIEW_QUIET_SECONDS = 60
_REVIEW_QUIET_POLL_SECONDS = 15
_MAX_REVIEW_SETTLEMENT_SECONDS = 105
_PENDING_REVIEW_TIMESTAMP = "pending-review"
_review_quiet_monotonic = time.monotonic
_review_quiet_sleep = time.sleep
_OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES: Mapping[str, tuple[str, int, str]] = {
    "Analyze (actions)": ("CodeQL Advanced", 15_368, "github-actions"),
    "Analyze (javascript-typescript)": ("CodeQL Advanced", 15_368, "github-actions"),
    "Analyze (python)": ("CodeQL Advanced", 15_368, "github-actions"),
    "Private Python proxy health": ("CI", 15_368, "github-actions"),
    "Trivy ignore-policy expiry": ("CI", 15_368, "github-actions"),
    "security": ("CI", 15_368, "github-actions"),
    "security-scan": ("Docker Build and Push", 15_368, "github-actions"),
}
_OUTAGE_OVERRIDE_REQUIRED_WORKFLOW_PATHS: Mapping[str, str] = {
    "Analyze (actions)": ".github/workflows/codeql.yml",
    "Analyze (javascript-typescript)": ".github/workflows/codeql.yml",
    "Analyze (python)": ".github/workflows/codeql.yml",
    "Private Python proxy health": ".github/workflows/ci.yml",
    "Trivy ignore-policy expiry": ".github/workflows/ci.yml",
    "security": ".github/workflows/ci.yml",
    "security-scan": ".github/workflows/build.yml",
}


@dataclass
class ActionableItem:
    """A single bot comment/review deemed actionable (needs mapping in PR body)."""

    author: str
    url: str
    created_at: str
    kind: str
    review_id: int | None = None
    updated_at: str = ""
    body_digest: str = ""


@dataclass(frozen=True)
class _OutagePullRequestTarget:
    repository: str
    number: int
    base_sha: str
    head_sha: str
    base_ref: str


@dataclass(frozen=True)
class _OutageRequiredContext:
    name: str
    workflow_name: str
    workflow_path: str


class _OutageSecurityChecksPending(ReviewEvidenceError):
    """Exact-head substitute checks are not terminal yet."""


def _strip_fenced_code_blocks(text: str) -> str:
    """Remove ``` and ~~~ fenced code blocks from text so regex does not match inside them."""
    no_ticks = re.sub(r"(?s)```.*?```", "", text)
    return re.sub(r"(?s)~~~.*?~~~", "", no_ticks)


def _extract_mapping_section(pr_body: str) -> str:
    """Return the content of the last ### Fixed in Commit Mapping section in pr_body."""
    cleaned = _strip_fenced_code_blocks(pr_body)
    matches = list(MAPPING_HEADING_RE.finditer(cleaned))
    if not matches:
        return ""
    start = matches[-1].end()
    next_h2 = re.search(r"(?im)^\s*##\s+", cleaned[start:])
    end = start + next_h2.start() if next_h2 else len(cleaned)
    return cleaned[start:end]


def _mapped_urls(pr_body: str) -> tuple[set[str], bool]:
    """Parse PR body mapping section; return (set of mapped comment URLs, has_no_actionable_marker)."""
    section = _extract_mapping_section(pr_body)
    urls = {m.group(1).strip() for m in MAPPING_ENTRY_RE.finditer(section)}
    return urls, bool(MAPPING_NO_ACTIONABLE_RE.search(section))


def _canonical_artifact_markdown_link_count(
    pr_body: str,
    pr_number: int,
    repository: str,
    head_ref: str,
) -> int:
    """Count canonical standalone Markdown links outside non-rendered block regions."""

    artifact_path = f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    expected_path = f"/{repository}/blob/{head_ref}/{artifact_path}"
    expected_url = f"https://github.com{expected_path}"

    def is_canonical_destination(destination: str) -> bool:
        parsed = urllib.parse.urlsplit(destination)
        return (
            bool(head_ref)
            and parsed.scheme == "https"
            and parsed.netloc.lower() == "github.com"
            and not parsed.query
            and not parsed.fragment
            and urllib.parse.unquote(parsed.path) == expected_path
        )

    canonical_url_occurrences = urllib.parse.unquote(pr_body).count(expected_url)
    count = 0
    in_html_comment = False
    fence_char = ""
    fence_length = 0
    raw_html_tag = ""
    raw_html_depth = 0
    for raw_line in pr_body.splitlines():
        line = raw_line
        visible_parts: list[str] = []
        cursor = 0
        while cursor < len(line):
            if in_html_comment:
                comment_end = line.find("-->", cursor)
                if comment_end < 0:
                    cursor = len(line)
                    break
                in_html_comment = False
                cursor = comment_end + 3
                continue
            comment_start = line.find("<!--", cursor)
            if comment_start < 0:
                visible_parts.append(line[cursor:])
                break
            visible_parts.append(line[cursor:comment_start])
            visible_parts.append(" ")
            in_html_comment = True
            cursor = comment_start + 4
        visible_line = "".join(visible_parts)

        if fence_char:
            closing_fence = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*",
                visible_line,
            )
            if closing_fence:
                fence_char = ""
                fence_length = 0
            continue
        fence_open = FENCE_OPEN_RE.match(visible_line)
        if fence_open:
            fence = fence_open.group("fence")
            fence_char = fence[0]
            fence_length = len(fence)
            continue
        if raw_html_tag:
            raw_html_depth += len(
                re.findall(
                    rf"<{re.escape(raw_html_tag)}(?:[\t />]|$)",
                    visible_line,
                    re.IGNORECASE,
                )
            )
            raw_html_depth -= len(
                re.findall(
                    rf"</{re.escape(raw_html_tag)}\s*>",
                    visible_line,
                    re.IGNORECASE,
                )
            )
            if raw_html_depth <= 0:
                raw_html_tag = ""
                raw_html_depth = 0
            continue
        raw_html_open = RAW_HTML_BLOCK_OPEN_RE.search(visible_line)
        if raw_html_open:
            tag = raw_html_open.group("tag").lower()
            remainder = visible_line[raw_html_open.end() :]
            if (
                tag not in RAW_HTML_VOID_TAGS
                and not re.search(r"/\s*>\s*$", visible_line)
                and not re.search(rf"</{re.escape(tag)}\s*>", remainder, re.IGNORECASE)
            ):
                raw_html_tag = tag
                raw_html_depth = 1
            continue
        if raw_line.startswith(("\t", "    ")):
            continue
        match = CANONICAL_ARTIFACT_LINK_LINE_RE.fullmatch(visible_line)
        if match is None:
            continue
        raw_destination = match.group("angle") or match.group("plain") or ""
        destination = raw_destination or ""
        parsed = urllib.parse.urlsplit(destination)
        if parsed.query or parsed.fragment:
            continue
        if is_canonical_destination(destination):
            count += 1
    if count == 1:
        return canonical_url_occurrences
    return count


def _actionable_inventory(
    items: list[ActionableItem],
) -> tuple[tuple[str, str, str, str, int, str, str], ...]:
    """Return a deterministic identity for the live actionable review inventory."""

    return tuple(
        sorted(
            (
                item.author,
                item.url,
                item.created_at,
                item.kind,
                item.review_id or 0,
                item.updated_at,
                item.body_digest,
            )
            for item in items
        )
    )


def _comment_body_digest(body: str) -> str:
    """Bind review inventory to content without retaining or logging bot bodies."""

    normalized = body.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _pre_closeout_dirty_paths() -> set[str]:
    """Return all tracked, staged, or untracked paths visible to a closeout commit."""

    git = shutil.which("git")
    if not git:
        raise ValueError("git not found in PATH")
    try:
        completed = subprocess.run(  # nosec B603: absolute git with fixed status argv only (remove-by: 2026-09-30, ref: PR-strict-closeout-precommit-guard)
            [git, "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("git status timed out during pre-closeout cleanliness check") from exc
    if completed.returncode != 0:
        raise ValueError("git status failed during pre-closeout cleanliness check")
    status_lines = [line for line in completed.stdout.splitlines() if len(line) >= 4]
    if any(line[0] not in {" ", "?"} for line in status_lines):
        raise ValueError("staged changes are forbidden during pre-closeout validation")
    return {line[3:] for line in status_lines}


def _is_actionable(body: str) -> bool:
    """True if body contains an actionable marker; False if non-actionable marker or neither."""
    if not body:
        return False
    if any(marker.lower() in body.lower() for marker in ACTIONABLE_MARKERS):
        return True
    if any(marker.lower() in body.lower() for marker in NON_ACTIONABLE_MARKERS):
        return False
    return False


def _api_request(
    url: str, token: str, method: str = "GET", payload: dict[str, Any] | None = None
) -> Any:
    """Perform a single GitHub API request (REST or GraphQL); raise HTTPError on 4xx/5xx."""
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pulseplate-merge-readiness-gate",
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
    conn.request(method=method, url=path, body=data, headers=headers)
    response = conn.getresponse()
    raw = response.read(_MAX_API_RESPONSE_BYTES + 1)
    conn.close()

    if len(raw) > _MAX_API_RESPONSE_BYTES:
        raise ValueError("GitHub API response exceeds size limit")

    if response.status >= 400:
        raise urllib.error.HTTPError(
            url=url,
            code=response.status,
            msg=response.reason,
            hdrs=response.headers,
            fp=None,
        )
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("GitHub API returned malformed JSON") from exc


def _graphql_unresolved_threads(repo: str, pr_number: int, token: str) -> int:
    """Return count of unresolved review threads for the PR (paginated via GraphQL)."""
    owner, name = repo.split("/", maxsplit=1)
    query = """
    query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $number) {
          reviewThreads(first: 100, after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              isResolved
              comments(first: 1) {
                nodes {
                  author {
                    login
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    total = 0
    cursor: str | None = None
    seen_cursors: set[str] = set()
    for _page in range(_MAX_API_PAGES):
        payload = {
            "query": query,
            "variables": {"owner": owner, "name": name, "number": pr_number, "cursor": cursor},
        }
        resp = _api_request(
            "https://api.github.com/graphql", token=token, method="POST", payload=payload
        )
        if not isinstance(resp, dict) or resp.get("errors"):
            raise ValueError("GraphQL response contains errors or is malformed")
        data = resp.get("data")
        repository = data.get("repository") if isinstance(data, dict) else None
        pull_request = repository.get("pullRequest") if isinstance(repository, dict) else None
        threads = pull_request.get("reviewThreads") if isinstance(pull_request, dict) else None
        if not isinstance(threads, dict):
            raise ValueError("GraphQL response is missing reviewThreads")
        nodes = threads.get("nodes", [])
        if not isinstance(nodes, list) or any(not isinstance(item, dict) for item in nodes):
            raise ValueError("GraphQL reviewThreads nodes are malformed")
        total += sum(
            1
            for item in nodes
            if item
            and not item.get("isResolved", False)
            and not _is_non_conversation_security_thread(item)
        )
        page_info = threads.get("pageInfo", {})
        if not isinstance(page_info, dict) or not isinstance(page_info.get("hasNextPage"), bool):
            raise ValueError("GraphQL reviewThreads pageInfo is malformed")
        if not page_info["hasNextPage"]:
            break
        next_cursor = page_info.get("endCursor")
        if (
            not isinstance(next_cursor, str)
            or not next_cursor
            or next_cursor == cursor
            or next_cursor in seen_cursors
        ):
            raise ValueError("GraphQL reviewThreads cursor is missing or repeated")
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    else:
        raise ValueError("GraphQL reviewThreads pagination exceeded page limit")
    return total


def _is_non_conversation_security_thread(thread: dict[str, Any]) -> bool:
    """Ignore GHAS code-scanning threads because they cannot be resolved as conversations."""
    first_comment = ((thread.get("comments") or {}).get("nodes") or [None])[0] or {}
    author = ((first_comment.get("author") or {}).get("login") or "").strip().lower()
    return author == "github-advanced-security"


def _api_request_paginated_list(base_url: str, token: str) -> list[Any]:
    """Fetch all pages of a GitHub REST list endpoint (per_page=100)."""
    out: list[Any] = []
    page = 1
    for _page in range(_MAX_API_PAGES):
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}{sep}page={page}" if page > 1 else base_url
        data = _api_request(url, token=token)
        if not isinstance(data, list):
            raise ValueError("GitHub REST pagination returned a non-list page")
        out.extend(data)
        if len(data) < 100:
            break
        page += 1
    else:
        raise ValueError("GitHub REST pagination exceeded page limit")
    return out


def _collect_actionable_items(repo: str, pr_number: int, token: str) -> list[ActionableItem]:
    """Fetch all issue comments, reviews, and review comments (paginated); return actionable bot items."""
    base = f"https://api.github.com/repos/{repo}"
    encoded = urllib.parse.quote(str(pr_number), safe="")
    comments_url = f"{base}/issues/{encoded}/comments?per_page=100"
    reviews_url = f"{base}/pulls/{encoded}/reviews?per_page=100"
    review_comments_url = f"{base}/pulls/{encoded}/comments?per_page=100"

    issue_comments = _api_request_paginated_list(comments_url, token=token)
    reviews = _api_request_paginated_list(reviews_url, token=token)
    review_comments = _api_request_paginated_list(review_comments_url, token=token)

    items: list[ActionableItem] = []

    for source, kind in (
        (issue_comments, "issue_comment"),
        (reviews, "review"),
        (review_comments, "review_comment"),
    ):
        for row in source:
            author = str((row.get("user") or {}).get("login", ""))
            if not author.endswith("[bot]"):
                continue
            body = str(row.get("body") or "")
            if not _is_actionable(body):
                continue
            url = str(row.get("html_url") or "")
            created_at = str(row.get("created_at") or row.get("submitted_at") or "")
            updated_at = str(row.get("updated_at") or created_at)
            if not url:
                continue
            raw_review_id = row.get("id") if kind == "review" else row.get("pull_request_review_id")
            review_id = (
                raw_review_id
                if isinstance(raw_review_id, int)
                and not isinstance(raw_review_id, bool)
                and raw_review_id > 0
                else None
            )
            items.append(
                ActionableItem(
                    author=author,
                    url=url,
                    created_at=created_at,
                    kind=kind,
                    review_id=review_id,
                    updated_at=updated_at,
                    body_digest=_comment_body_digest(body),
                )
            )

    unique = {item.url: item for item in items}
    return sorted(unique.values(), key=lambda it: it.created_at)


def _validated_review_timestamp(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} is missing or malformed")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{label} is missing or malformed") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} is missing or malformed")
    return value


def _review_activity_inventory(
    repo: str,
    pr_number: int,
    token: str,
) -> tuple[tuple[object, ...], ...]:
    """Return a content-bound inventory of all issue/review activity."""

    base = f"https://api.github.com/repos/{repo}"
    encoded = urllib.parse.quote(str(pr_number), safe="")
    sources = (
        (
            "issue_comment",
            _api_request_paginated_list(
                f"{base}/issues/{encoded}/comments?per_page=100",
                token=token,
            ),
        ),
        (
            "review",
            _api_request_paginated_list(
                f"{base}/pulls/{encoded}/reviews?per_page=100",
                token=token,
            ),
        ),
        (
            "review_comment",
            _api_request_paginated_list(
                f"{base}/pulls/{encoded}/comments?per_page=100",
                token=token,
            ),
        ),
    )
    inventory: list[tuple[object, ...]] = []
    seen: set[tuple[str, int]] = set()
    for kind, rows in sources:
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"{kind} activity row is malformed")
            event_id = row.get("id")
            user = row.get("user")
            user_id = user.get("id") if isinstance(user, dict) else None
            author = user.get("login") if isinstance(user, dict) else None
            body = row.get("body")
            state = row.get("state")
            created_raw = row.get("submitted_at") if kind == "review" else row.get("created_at")
            if kind == "review" and state == "PENDING" and created_raw is None:
                created_at = _PENDING_REVIEW_TIMESTAMP
            else:
                created_at = _validated_review_timestamp(
                    created_raw,
                    label=f"{kind} created_at",
                )
            updated_raw = row.get("updated_at") or created_at
            if updated_raw == _PENDING_REVIEW_TIMESTAMP:
                updated_at = _PENDING_REVIEW_TIMESTAMP
            else:
                updated_at = _validated_review_timestamp(
                    updated_raw,
                    label=f"{kind} updated_at",
                )
            if (
                not isinstance(event_id, int)
                or isinstance(event_id, bool)
                or event_id <= 0
                or not isinstance(user_id, int)
                or isinstance(user_id, bool)
                or user_id <= 0
                or not isinstance(author, str)
                or not author
                or body is not None
                and not isinstance(body, str)
            ):
                raise ValueError(f"{kind} activity identity is missing or malformed")
            key = (kind, event_id)
            if key in seen:
                raise ValueError(f"{kind} activity contains duplicate id {event_id}")
            seen.add(key)
            inventory.append(
                (
                    kind,
                    event_id,
                    user_id,
                    author,
                    str(row.get("html_url") or ""),
                    created_at,
                    updated_at,
                    _comment_body_digest(body or ""),
                    str(state or ""),
                    str(row.get("commit_id") or ""),
                    row.get("pull_request_review_id") or 0,
                )
            )
    return tuple(sorted(inventory))


def _wait_for_review_quiet_window(
    *,
    repo: str,
    pr_number: int,
    token: str,
    expected_pr_context: tuple[int, str, bool, str, str],
    snapshot: PrSnapshot,
) -> tuple[int, int]:
    """Require one bounded provider-neutral quiet period over live review state."""

    def observe() -> tuple[
        tuple[tuple[object, ...], ...],
        tuple[tuple[str, bool, tuple[tuple[str, ...], ...]], ...],
    ]:
        context = _fetch_pr_context(pr_number=pr_number, repo=repo, token=token)
        if context != expected_pr_context:
            raise CommitIdentityError(
                "SNAPSHOT_CHANGED: live PR body or draft state changed during review wait"
            )
        activity = _review_activity_inventory(repo, pr_number, token)
        threads = fetch_review_threads(repo, pr_number, token=token)
        assert_snapshot_unchanged(snapshot, token=token)
        return activity, _review_thread_inventory(threads)

    state = observe()
    quiet_started = _review_quiet_monotonic()
    deadline = quiet_started + _MAX_REVIEW_SETTLEMENT_SECONDS
    observations = 1
    while True:
        now = _review_quiet_monotonic()
        quiet_remaining = _REVIEW_QUIET_SECONDS - (now - quiet_started)
        if quiet_remaining <= 0:
            return observations, len(state[0])
        total_remaining = deadline - now
        if total_remaining <= 0:
            raise ReviewEvidenceError(
                "review activity did not settle within the bounded "
                f"{_MAX_REVIEW_SETTLEMENT_SECONDS}s window"
            )
        sleep_seconds = min(
            float(_REVIEW_QUIET_POLL_SECONDS),
            quiet_remaining,
            total_remaining,
        )
        _review_quiet_sleep(sleep_seconds)
        after_sleep = _review_quiet_monotonic()
        if after_sleep <= now:
            raise ReviewEvidenceError("review quiet-window clock did not advance")
        current = observe()
        observations += 1
        if current != state:
            state = current
            quiet_started = _review_quiet_monotonic()


def _covered_review_summary_urls(
    actionable_items: list[ActionableItem],
    evidence_covered_urls: set[str],
) -> set[str]:
    """Cover a review summary only when every actionable child comment is covered."""

    child_urls_by_review: dict[int, set[str]] = {}
    for item in actionable_items:
        if item.kind == "review_comment" and item.review_id is not None:
            child_urls_by_review.setdefault(item.review_id, set()).add(item.url)

    covered: set[str] = set()
    for item in actionable_items:
        if item.kind != "review" or item.review_id is None:
            continue
        child_urls = child_urls_by_review.get(item.review_id, set())
        if child_urls and child_urls.issubset(evidence_covered_urls):
            covered.add(item.url)
    return covered


def _extract_pr_context(event_path: Path) -> tuple[int, str, bool, str, str]:
    """Read GitHub event JSON; return PR identity, body, and exact head ref."""
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    pr = payload.get("pull_request") or {}
    number = int(pr.get("number", 0))
    repo = str((payload.get("repository") or {}).get("full_name", ""))
    is_draft = bool(pr.get("draft", False))
    body = str(pr.get("body") or "")
    head_ref = str((pr.get("head") or {}).get("ref") or "")
    return number, repo, is_draft, body, head_ref


def _fetch_pr_context(pr_number: int, repo: str, token: str) -> tuple[int, str, bool, str, str]:
    """Fetch PR identity, body, and exact head ref via REST for local/agent use."""
    owner, name = repo.split("/", maxsplit=1)
    url = f"https://api.github.com/repos/{owner}/{name}/pulls/{pr_number}"
    data = _api_request(url, token=token)
    body = str(data.get("body") or "")
    is_draft = bool(data.get("draft", False))
    head_ref = str((data.get("head") or {}).get("ref") or "")
    return pr_number, repo, is_draft, body, head_ref


def _event_head_sha(event_path: Path) -> str:
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    head = ((payload.get("pull_request") or {}).get("head") or {}).get("sha")
    if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("event pull_request.head.sha is missing or malformed")
    return head


def _local_head_sha() -> str:
    git = shutil.which("git")
    if not git:
        raise ValueError("git not found in PATH")
    completed = subprocess.run(  # nosec B603: absolute git with fixed rev-parse argv only (remove-by: 2026-09-30, ref: PR-governance-material-seal)
        [git, "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    head = completed.stdout.strip()
    if completed.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("local checkout HEAD is unavailable")
    return head


def _is_ghas_thread(thread: ReviewThreadEvidence) -> bool:
    return bool(thread.comments) and (
        thread.comments[0].author_login.strip().lower() == "github-advanced-security"
    )


def _actions_run_and_job_ids(
    details_url: object,
    target: _OutagePullRequestTarget,
) -> tuple[int, int]:
    if not isinstance(details_url, str):
        raise ReviewEvidenceError("check run details URL is missing")
    parsed = urllib.parse.urlparse(details_url)
    expected_prefix = f"/{target.repository}/actions/runs/"
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or not parsed.path.startswith(expected_prefix)
    ):
        raise ReviewEvidenceError("check run is not linked to this repository Actions run")
    tail = parsed.path[len(expected_prefix) :].split("/")
    if (
        len(tail) != 3
        or not tail[0].isdigit()
        or int(tail[0]) <= 0
        or tail[1] != "job"
        or not tail[2].isdigit()
        or int(tail[2]) <= 0
    ):
        raise ReviewEvidenceError("check run Actions run/job identity is malformed")
    return int(tail[0]), int(tail[2])


def _validated_action_run(
    check: Mapping[str, Any],
    *,
    required: _OutageRequiredContext,
    target: _OutagePullRequestTarget,
    token: str,
    run_cache: dict[int, dict[str, Any]],
    job_cache: dict[int, dict[str, Any]],
) -> tuple[str, int] | None:
    """Bind one check to the exact pull_request Actions run and job."""

    run_id, job_id = _actions_run_and_job_ids(check.get("details_url"), target)
    api_root = f"https://api.github.com/repos/{target.repository}"
    if run_id not in run_cache:
        run = _api_request(f"{api_root}/actions/runs/{run_id}", token=token)
        if not isinstance(run, dict):
            raise ReviewEvidenceError("linked Actions run is malformed")
        run_cache[run_id] = run
    run = run_cache[run_id]
    if run.get("id") != run_id:
        raise ReviewEvidenceError(f"{required.name} linked Actions run identity is malformed")
    event = run.get("event")
    if not isinstance(event, str) or not event:
        raise ReviewEvidenceError(f"{required.name} linked Actions run event is malformed")
    if event != "pull_request":
        return None
    pull_requests = run.get("pull_requests")
    if not isinstance(pull_requests, list):
        raise ReviewEvidenceError("linked Actions run PR binding is malformed")
    matching_prs = [
        item
        for item in pull_requests
        if isinstance(item, dict)
        and item.get("number") == target.number
        and isinstance(item.get("head"), dict)
        and item["head"].get("sha") == target.head_sha
        and isinstance(item.get("base"), dict)
        and item["base"].get("ref") == target.base_ref
        and item["base"].get("sha") == target.base_sha
    ]
    if (
        run.get("head_sha") != target.head_sha
        or run.get("name") != required.workflow_name
        or run.get("path") != required.workflow_path
        or len(matching_prs) != 1
    ):
        raise ReviewEvidenceError(
            f"{required.name} is not linked to an exact PR/base/head "
            "base-allowlisted Actions run"
        )
    created_at = run.get("created_at")
    if not isinstance(created_at, str) or not created_at:
        raise ReviewEvidenceError(f"{required.name} linked Actions chronology is malformed")
    if job_id not in job_cache:
        job = _api_request(f"{api_root}/actions/jobs/{job_id}", token=token)
        if not isinstance(job, dict):
            raise ReviewEvidenceError("linked Actions job is malformed")
        job_cache[job_id] = job
    job = job_cache[job_id]
    check_id = check.get("id")
    attempt = job.get("run_attempt")
    if (
        not isinstance(check_id, int)
        or isinstance(check_id, bool)
        or check_id <= 0
        or job.get("id") != job_id
        or job.get("run_id") != run_id
        or job.get("check_run_url") != f"{api_root}/check-runs/{check_id}"
        or not isinstance(attempt, int)
        or isinstance(attempt, bool)
        or attempt <= 0
    ):
        raise ReviewEvidenceError(f"{required.name} linked Actions job identity is malformed")
    return created_at, attempt


def _validate_selected_outage_action_run(
    check_node: Mapping[str, Any],
    *,
    required: _OutageRequiredContext,
    target: _OutagePullRequestTarget,
    token: str,
    run_cache: dict[int, dict[str, Any]],
    job_cache: dict[int, dict[str, Any]],
) -> None:
    """Bind one selected rollup check to its exact PR Actions run and job."""

    details_url = check_node.get("detailsUrl")
    run_id, job_id = _actions_run_and_job_ids(details_url, target)
    api_root = f"https://api.github.com/repos/{target.repository}"
    if run_id not in run_cache:
        run = _api_request(f"{api_root}/actions/runs/{run_id}", token=token)
        if not isinstance(run, dict):
            raise ReviewEvidenceError(f"{required.name} linked Actions run is malformed")
        run_cache[run_id] = run
    if job_id not in job_cache:
        job = _api_request(f"{api_root}/actions/jobs/{job_id}", token=token)
        if not isinstance(job, dict):
            raise ReviewEvidenceError(f"{required.name} linked Actions job is malformed")
        job_cache[job_id] = job
    check_run_url = job_cache[job_id].get("check_run_url")
    if not isinstance(check_run_url, str):
        raise ReviewEvidenceError(f"{required.name} linked Actions job identity is malformed")
    raw_check_id = check_run_url.rsplit("/", maxsplit=1)[-1]
    if not raw_check_id.isdigit() or int(raw_check_id) <= 0:
        raise ReviewEvidenceError(f"{required.name} linked Actions job identity is malformed")
    validated = _validated_action_run(
        {"details_url": details_url, "id": int(raw_check_id)},
        required=required,
        target=target,
        token=token,
        run_cache=run_cache,
        job_cache=job_cache,
    )
    if validated is None:
        raise ReviewEvidenceError(f"{required.name} is not linked to a pull_request Actions run")


def _validate_operator_outage_security_checks(
    *,
    repository: str,
    pr_number: int,
    token: str,
    expected_base_sha: str,
    expected_head_sha: str,
    security_required: bool = True,
    material_paths: Iterable[str] | None = None,
    evidence_label: str = "operator outage override",
) -> None:
    """Require a strict successful trusted current-head security bundle."""

    _is_draft, _merge_state, base_ref, nodes = _fetch_current_head_pr_metadata(
        pr_number, repository, token, expected_head_sha
    )
    try:
        normalized_nodes = [(node, _normalize_check_node(node)) for node in nodes if node]
    except ValueError as exc:
        raise ReviewEvidenceError(
            f"{evidence_label} cannot order current-head security checks: {exc}"
        ) from exc
    entries = [entry for _node, entry in normalized_nodes]
    latest, superseded = _latest_check_entries(entries)
    latest, _superseded = _suppress_stale_check_entries(
        entries,
        latest,
        superseded,
    )
    target = _OutagePullRequestTarget(
        repository=repository,
        number=pr_number,
        base_sha=expected_base_sha,
        head_sha=expected_head_sha,
        base_ref=base_ref,
    )
    docker_security_required = (
        True
        if material_paths is None
        else _operator_outage_docker_security_required(base_ref, material_paths)
    )
    run_cache: dict[int, dict[str, Any]] = {}
    job_cache: dict[int, dict[str, Any]] = {}
    terminal_failures: list[str] = []
    pending_failures: list[str] = []
    for name, expected_identity in sorted(_OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES.items()):
        if name == "security-scan" and not docker_security_required:
            continue
        candidates = [entry for entry in entries if entry.name == name]
        if not candidates:
            pending_failures.append(f"{name}=missing")
            continue
        expected_workflow, expected_app_id, expected_app_slug = expected_identity
        expected_workflow_path = _OUTAGE_OVERRIDE_REQUIRED_WORKFLOW_PATHS[name]
        untrusted = [
            entry
            for entry in candidates
            if entry.source_kind != "check_run"
            or entry.workflow_name != expected_workflow
            or entry.app_database_id != expected_app_id
            or entry.app_slug != expected_app_slug
        ]
        if untrusted:
            producers = sorted(
                {
                    (
                        entry.source_kind,
                        entry.workflow_name or "none",
                        str(entry.app_database_id or "none"),
                        entry.app_slug or "none",
                    )
                    for entry in untrusted
                }
            )
            rendered = ";".join("/".join(item) for item in producers)
            terminal_failures.append(f"{name}=untrusted-producer({rendered})")
            continue
        entry = latest.get(name)
        if entry is None:  # Defensive: candidates were present above.
            terminal_failures.append(f"{name}=missing-latest")
            continue
        selected_nodes = [
            node
            for node, normalized in normalized_nodes
            if normalized.source_kind == "check_run" and normalized == entry
        ]
        if len(selected_nodes) != 1:
            terminal_failures.append(f"{name}=ambiguous-actions-run")
            continue
        try:
            _validate_selected_outage_action_run(
                selected_nodes[0],
                required=_OutageRequiredContext(
                    name=name,
                    workflow_name=expected_workflow,
                    workflow_path=expected_workflow_path,
                ),
                target=target,
                token=token,
                run_cache=run_cache,
                job_cache=job_cache,
            )
        except ReviewEvidenceError as exc:
            terminal_failures.append(f"{name}=untrusted-actions-run({exc})")
            continue
        if (
            name == "security"
            and not security_required
            and entry.source_kind == "check_run"
            and entry.state == "failed"
            and entry.conclusion == "SKIPPED"
        ):
            passed = True
        elif entry.source_kind == "check_run":
            passed = entry.state == "passed" and entry.conclusion == "SUCCESS"
        else:
            passed = entry.state == "passed"
        if not passed:
            failure = f"{name}={entry.state}/{entry.conclusion or 'status'}"
            if entry.state == "pending":
                pending_failures.append(failure)
            else:
                terminal_failures.append(failure)
    failures = terminal_failures + pending_failures
    if failures:
        error_type = (
            _OutageSecurityChecksPending
            if pending_failures and not terminal_failures
            else ReviewEvidenceError
        )
        raise error_type(
            f"{evidence_label} requires successful current-head security checks: "
            + ", ".join(failures)
            + ". Pending or not-yet-visible exact-head checks may be retried only "
            "within the bounded CI wait; failed, stale, skipped-when-applicable, "
            "or untrusted checks remain terminal."
        )


def _wait_for_operator_outage_security_checks(
    *,
    repository: str,
    pr_number: int,
    token: str,
    expected_base_sha: str,
    expected_head_sha: str,
    security_required: bool,
    material_paths: Iterable[str] | None = None,
    timeout_seconds: int,
    poll_interval_seconds: int = 15,
    evidence_label: str = "operator outage override",
) -> None:
    """Wait only for transient exact-head substitute-check states, then fail closed."""

    if timeout_seconds < 0:
        raise ValueError("outage security wait must be non-negative")
    if timeout_seconds > _MAX_OUTAGE_SECURITY_WAIT_SECONDS:
        raise ValueError(
            f"outage security wait must not exceed {_MAX_OUTAGE_SECURITY_WAIT_SECONDS} seconds"
        )
    if poll_interval_seconds <= 0:
        raise ValueError("outage security poll interval must be positive")

    frozen_material_paths = None if material_paths is None else tuple(material_paths)
    deadline = time.monotonic() + timeout_seconds
    attempt = 1
    while True:
        try:
            _validate_operator_outage_security_checks(
                repository=repository,
                pr_number=pr_number,
                token=token,
                expected_base_sha=expected_base_sha,
                expected_head_sha=expected_head_sha,
                security_required=security_required,
                material_paths=frozen_material_paths,
                evidence_label=evidence_label,
            )
            return
        except _OutageSecurityChecksPending as exc:
            remaining = deadline - time.monotonic()
            if timeout_seconds == 0 or remaining <= 0:
                raise ReviewEvidenceError(
                    f"{evidence_label} timed out waiting for exact-head "
                    f"security checks after {timeout_seconds}s: {exc}"
                ) from exc
            sleep_seconds = min(float(poll_interval_seconds), remaining)
            print(
                "merge-readiness-gate: exact-head security checks are still "
                f"settling; retrying in {sleep_seconds:.0f}s (attempt {attempt})."
            )
            time.sleep(sleep_seconds)
            attempt += 1


def _operator_outage_security_required(material_paths: Iterable[str]) -> bool:
    """Recompute security-job applicability from the sealed material paths."""

    return bool(build_risk_profile(tuple(material_paths)).run_security)


def _operator_outage_docker_security_required(
    base_ref: str,
    material_paths: Iterable[str],
) -> bool:
    """Require Docker security only when its PR trigger and surface both attach."""

    return base_ref == "main" and _path_touches_any(
        set(material_paths),
        DOCKER_SURFACE_PREFIXES,
    )


def _validate_v1_seal(
    *,
    artifact_text: str,
    repository: str,
    pr_number: int,
    snapshot: PrSnapshot,
    token: str,
    outage_security_wait_seconds: int = 0,
    enforce_outage_security_checks: bool = True,
    require_committed_closeout: bool = True,
) -> dict[str, Any]:
    raw_seal = parse_embedded_review_seal(artifact_text)
    if not isinstance(raw_seal, dict):
        raise ReviewEvidenceError("embedded review seal must be a string-keyed object")
    seal: dict[str, Any] = {}
    for key, value in raw_seal.items():
        if not isinstance(key, str):
            raise ReviewEvidenceError("embedded review seal must be a string-keyed object")
        seal[key] = value
    if seal["repository"] != repository or seal["pr_number"] != pr_number:
        raise ReviewEvidenceError("review seal repository/PR identity mismatch")
    manifest = compute_material_manifest(
        REPO_ROOT,
        base_ref_oid=snapshot.base_sha,
        head_ref_oid=snapshot.head_sha,
        pr_number=pr_number,
    )
    seal = validate_review_seal(
        seal,
        material_paths=(entry.path for entry in manifest.entries),
        material_diff_summary=manifest.diff_summary,
    )
    material = seal["material"]
    if (
        material["base_ref_oid"] != snapshot.base_sha
        or material["merge_base_sha"] != manifest.merge_base_sha
        or material["digest"] != manifest.digest
    ):
        raise ReviewEvidenceError("review seal does not match the live material digest")
    material_head = classify_commit_ref(material["material_head_sha"], snapshot, token=token)
    if not isinstance(material_head, RepositoryCommitRef) or material_head.kind not in {
        CommitRefKind.PR_HEAD,
        CommitRefKind.PR_COMMIT,
    }:
        raise ReviewEvidenceError("material head is not a real commit in the live PR")
    code_review = seal["code_review"]
    if not is_provider_no_claim_review_receipt(code_review):
        raise ReviewEvidenceError(
            "legacy provider-backed review seals are read-only and cannot authorize "
            "current merge readiness"
        )
    expected_code_review, expected_security = build_provider_no_claim_pair(
        base_revision=manifest.merge_base_sha,
        head_revision=material_head.sha,
        material_digest=material["digest"],
    )
    if code_review != expected_code_review:
        raise ReviewEvidenceError("provider-neutral review no-claim receipt is stale")
    if require_committed_closeout:
        validate_mapping_only_closeout_successor(
            REPO_ROOT,
            material_head_sha=material_head.sha,
            live_head_sha=snapshot.head_sha,
            pr_number=pr_number,
        )
    else:
        live_head = RepositoryCommitRef(snapshot.head_sha, CommitRefKind.PR_HEAD)
        if not is_ancestor(
            material_head,
            live_head,
            repository=repository,
            token=token,
        ):
            raise ReviewEvidenceError("material head is not an ancestor of the live PR head")
    security_receipt = seal["codex_security"]
    if not is_provider_no_claim_security_receipt(security_receipt):
        raise ReviewEvidenceError(
            "legacy provider-backed security seals are read-only and cannot authorize "
            "current merge readiness"
        )
    if (
        security_receipt["base_revision"] != manifest.merge_base_sha
        or security_receipt["head_revision"] != material_head.sha
    ):
        raise ReviewEvidenceError("Codex Security receipt range is stale")
    if security_receipt != expected_security:
        raise ReviewEvidenceError("provider-neutral security no-claim receipt is stale")
    if enforce_outage_security_checks:
        material_paths = tuple(entry.path for entry in manifest.entries)
        _wait_for_operator_outage_security_checks(
            repository=repository,
            pr_number=pr_number,
            token=token,
            expected_base_sha=snapshot.base_sha,
            expected_head_sha=snapshot.head_sha,
            security_required=_operator_outage_security_required(material_paths),
            material_paths=material_paths,
            timeout_seconds=outage_security_wait_seconds,
            evidence_label="provider-neutral no-claim evidence",
        )
    return seal


def _prove_v1_fixed_commits(
    *,
    mapping_entries: Mapping[str, str],
    snapshot: PrSnapshot,
    repository: str,
    token: str,
) -> None:
    live_head = RepositoryCommitRef(snapshot.head_sha, CommitRefKind.PR_HEAD)
    for sha in sorted({sha for sha in mapping_entries.values() if sha}):
        resolution = classify_commit_ref(sha, snapshot, token=token)
        if not isinstance(resolution, RepositoryCommitRef) or resolution.kind not in {
            CommitRefKind.PR_HEAD,
            CommitRefKind.PR_COMMIT,
        }:
            raise CommitIdentityError(f"mapped FIXED SHA is not a real PR commit: {sha}")
        if not is_ancestor(
            resolution,
            live_head,
            repository=repository,
            token=token,
        ):
            raise CommitIdentityError(f"mapped FIXED SHA is not reachable from live head: {sha}")


def _duplicate_reply_coverage(
    *,
    actionable_items: list[ActionableItem],
    mapped_urls: set[str],
    threads: tuple[ReviewThreadEvidence, ...],
    artifact_text: str,
    seal: Mapping[str, Any],
    snapshot: PrSnapshot,
    repository: str,
    pr_number: int,
    token: str,
) -> set[str]:
    records = parse_canonical_fingerprint_records(artifact_text, pr_number=pr_number)
    candidate_urls = {
        item.url
        for item in actionable_items
        if item.url not in mapped_urls and item.kind == "review_comment"
    }
    raw_covered_urls = validated_duplicate_reply_urls(
        candidate_urls=candidate_urls,
        threads=threads,
        fingerprint_records=records,
        mapping_entries=parse_fixed_mapping_entries(extract_fixed_mapping_section(artifact_text)),
        material_digest=str(seal["material"]["digest"]),
        material_head_sha=str(seal["material"]["material_head_sha"]),
        repo_root=REPO_ROOT,
        snapshot=snapshot,
        repository=repository,
        token=token,
    )
    if not isinstance(raw_covered_urls, set):
        raise ReviewEvidenceError("duplicate-reply coverage must be a set of URLs")
    covered_urls: set[str] = set()
    for url in raw_covered_urls:
        if not isinstance(url, str):
            raise ReviewEvidenceError("duplicate-reply coverage must be a set of URLs")
        covered_urls.add(url)
    return covered_urls


def main() -> int:
    """Entry point: parse args, run merge-readiness checks, exit 0 on pass and 1 on fail."""
    parser = argparse.ArgumentParser(
        description="Fail CI when non-draft PR has unresolved review threads or unmapped actionable bot comments."
    )
    parser.add_argument(
        "--event-path",
        help="Path to GitHub event payload JSON (e.g. $GITHUB_EVENT_PATH). Required in CI.",
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        help="PR number for local/agent run (use with --repo; alternative to --event-path).",
    )
    parser.add_argument(
        "--repo",
        help="Repo full name owner/repo for local/agent run (e.g. Katsiarynakavaleuskaya/PulsePlate).",
    )
    parser.add_argument(
        "--outage-security-wait-seconds",
        type=int,
        default=_MAX_OUTAGE_SECURITY_WAIT_SECONDS,
        help=(
            "Bounded CI wait for transient exact-head substitute security checks. "
            "Failed or untrusted checks are never retried."
        ),
    )
    parser.add_argument(
        "--pre-closeout",
        action="store_true",
        help=(
            "Validate the local uncommitted canonical mapping and live PR-body link "
            "before its sole closeout commit. Does not require resolved threads or CI."
        ),
    )
    args = parser.parse_args()
    if args.outage_security_wait_seconds < 0:
        parser.error("--outage-security-wait-seconds must be non-negative")
    if args.outage_security_wait_seconds > _MAX_OUTAGE_SECURITY_WAIT_SECONDS:
        parser.error(
            "--outage-security-wait-seconds must not exceed " f"{_MAX_OUTAGE_SECURITY_WAIT_SECONDS}"
        )
    # Mutually exclusive: CI mode (--event-path) vs local/agent mode (--pr-number + --repo).
    if args.event_path and (args.pr_number is not None or (args.repo or "").strip()):
        parser.error("Use either --event-path (CI) or --pr-number and --repo (local), not both.")
    if args.pre_closeout and args.event_path:
        parser.error("--pre-closeout is local-only; use --pr-number and --repo.")
    if (args.pr_number is not None) != bool((args.repo or "").strip()):
        parser.error("For local/agent mode provide both --pr-number and --repo.")
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        print("ERROR: GITHUB_TOKEN is required for merge-readiness gate.")
        return 1
    if args.pre_closeout and not os.getenv("GH_TOKEN", "").strip():
        print("ERROR: GH_TOKEN is also required for strict pre-closeout validation.")
        return 1
    expected_mapping_path: str | None = None
    if args.pre_closeout and args.pr_number is not None:
        expected_mapping_path = f"docs/review/PR_{args.pr_number}_FIXED_MAPPING.md"
        try:
            dirty_paths = _pre_closeout_dirty_paths()
        except (OSError, ValueError) as exc:
            print(f"ERROR: pre-closeout cleanliness check failed: {exc}")
            return 1
        if dirty_paths != {expected_mapping_path}:
            rendered = ", ".join(sorted(dirty_paths)) or "none"
            print(
                "ERROR: pre-closeout requires the canonical mapping artifact to be the "
                f"only dirty path; found: {rendered}"
            )
            return 1

    if args.event_path:
        try:
            pr_number, repo, is_draft, pr_body, head_ref = _extract_pr_context(
                Path(args.event_path)
            )
            if pr_number and repo:
                pr_number, repo, is_draft, pr_body, head_ref = _fetch_pr_context(
                    pr_number=pr_number, repo=repo, token=token
                )
        except Exception as exc:  # noqa: BLE001 - fail closed for CI gate script
            print(f"ERROR: failed to parse event payload: {exc}")
            return 1
    elif args.pr_number and args.repo:
        repo = args.repo.strip()
        if "/" not in repo or repo.count("/") != 1:
            print("ERROR: --repo must be owner/name (e.g. Katsiarynakavaleuskaya/PulsePlate).")
            return 1
        try:
            pr_number, repo, is_draft, pr_body, head_ref = _fetch_pr_context(
                pr_number=args.pr_number, repo=repo, token=token
            )
        except ValueError as exc:
            print(f"ERROR: invalid repository format: {exc}")
            return 1
        except urllib.error.HTTPError as exc:
            print(f"ERROR: failed to fetch PR: HTTP {exc.code}")
            return 1
    else:
        print("ERROR: provide either --event-path (CI) or both --pr-number and --repo (local).")
        return 1

    if not pr_number or not repo:
        if args.pre_closeout:
            print("ERROR: pre-closeout validation requires a live PR context.")
            return 1
        print("merge-readiness-gate: no PR context found; skipping.")
        return 0

    if is_draft and not args.pre_closeout:
        print("merge-readiness-gate: PR is draft; skipping strict checks.")
        return 0

    errors: list[str] = []

    try:
        snapshot = fetch_pr_snapshot(repo, pr_number, token=token)
        event_head = _event_head_sha(Path(args.event_path)) if args.event_path else None
        if event_head is not None and event_head != snapshot.head_sha:
            raise CommitIdentityError(
                "SNAPSHOT_CHANGED: event head does not match the live PR head"
            )
        if _local_head_sha() != snapshot.head_sha:
            raise CommitIdentityError("local checkout HEAD does not match the live PR head")
        review_threads = fetch_review_threads(repo, pr_number, token=token)
    except (CommitIdentityError, OSError, ValueError) as exc:
        print(f"ERROR: cannot establish immutable live PR snapshot: {exc}")
        return 1

    unresolved_threads = sum(
        1 for thread in review_threads if not thread.is_resolved and not _is_ghas_thread(thread)
    )
    if unresolved_threads > 0 and not args.pre_closeout:
        errors.append(
            f"Unresolved review threads: {unresolved_threads}. Resolve all threads before merge."
        )

    try:
        actionable_items = _collect_actionable_items(repo=repo, pr_number=pr_number, token=token)
    except (urllib.error.HTTPError, OSError, ValueError) as exc:
        code = f" HTTP {exc.code}" if isinstance(exc, urllib.error.HTTPError) else ""
        print(f"ERROR: cannot query bot comments/reviews:{code} {exc}")
        return 1

    # Canonical SoT: repo artifact (docs/review/PR_<N>_FIXED_MAPPING.md)
    try:
        artifact_text = read_mapping_artifact(pr_number)
        artifact_errors = validate_mapping_artifact_text(artifact_text)
        if artifact_errors:
            raise ValueError("; ".join(artifact_errors))
        fixed_mapping_section = extract_fixed_mapping_section(artifact_text)
        mapping_entries = parse_fixed_mapping_entries(fixed_mapping_section)
        mapped_urls = set(mapping_entries.keys())
        no_actionable_marker = has_no_actionable_marker(fixed_mapping_section)
        seal_version = review_seal_version(artifact_text)
    except (FileNotFoundError, ReviewEvidenceError, ValueError) as exc:
        print(f"ERROR: canonical review artifact is invalid: {exc}")
        return 1

    try:
        v1_required = _review_seal_v1_required(pr_number, seal_version)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1
    seal: dict[str, Any] | None = None
    if v1_required:
        if seal_version != "v1":
            errors.append(
                f"Review-Seal-Version v1 is required from PR #{REVIEW_SEAL_REQUIRED_FROM_PR}."
            )
        else:
            try:
                seal = _validate_v1_seal(
                    artifact_text=artifact_text,
                    repository=repo,
                    pr_number=pr_number,
                    snapshot=snapshot,
                    token=token,
                    outage_security_wait_seconds=args.outage_security_wait_seconds,
                    enforce_outage_security_checks=not args.pre_closeout,
                    require_committed_closeout=not args.pre_closeout,
                )
                _prove_v1_fixed_commits(
                    mapping_entries=mapping_entries,
                    snapshot=snapshot,
                    repository=repo,
                    token=token,
                )
            except (CommitIdentityError, ReviewEvidenceError, OSError, ValueError) as exc:
                errors.append(f"Material review seal validation failed: {exc}")
    artifact_reference = f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    if _canonical_artifact_markdown_link_count(pr_body, pr_number, repo, head_ref) != 1:
        errors.append(
            "PR body must contain exactly one true Markdown link whose destination is "
            f"`{artifact_reference}` (plain text and fenced examples do not count)."
        )

    duplicate_covered_urls: set[str] = set()
    if seal is not None:
        try:
            duplicate_covered_urls = _duplicate_reply_coverage(
                actionable_items=actionable_items,
                mapped_urls=mapped_urls,
                threads=review_threads,
                artifact_text=artifact_text,
                seal=seal,
                snapshot=snapshot,
                repository=repo,
                pr_number=pr_number,
                token=token,
            )
        except (CommitIdentityError, ReviewEvidenceError, ValueError) as exc:
            errors.append(f"Duplicate reply validation failed: {exc}")

    review_summary_covered_urls = _covered_review_summary_urls(
        actionable_items,
        mapped_urls | duplicate_covered_urls,
    )
    disposition_covered_urls = mapped_urls | duplicate_covered_urls | review_summary_covered_urls

    if actionable_items:
        if no_actionable_marker and any(
            item.url not in disposition_covered_urls for item in actionable_items
        ):
            errors.append(
                "Canonical artifact claims `No actionable review comments` but actionable bot findings were detected."
            )
        unmapped = [
            item
            for item in actionable_items
            if item.url not in mapped_urls
            and item.url not in duplicate_covered_urls
            and (args.pre_closeout or item.url not in review_summary_covered_urls)
        ]
        if unmapped:
            errors.append(
                "Unmapped actionable bot comments found in canonical artifact "
                "`docs/review/PR_<N>_FIXED_MAPPING.md` "
                "(add `<review-comment-url>` entries for NOT-A-BUG/DEFERRED or "
                "`<review-comment-url> -> <commit-sha>` for FIXED)."
            )
            for item in unmapped:
                print(f"UNMAPPED: {item.author} [{item.kind}] {item.url} ({item.created_at})")

    review_wait_result: tuple[int, int] | None = None
    if not args.pre_closeout and not errors:
        try:
            review_wait_result = _wait_for_review_quiet_window(
                repo=repo,
                pr_number=pr_number,
                token=token,
                expected_pr_context=(pr_number, repo, is_draft, pr_body, head_ref),
                snapshot=snapshot,
            )
        except (
            CommitIdentityError,
            OSError,
            ReviewEvidenceError,
            ValueError,
            urllib.error.HTTPError,
        ) as exc:
            errors.append(f"Mandatory review wait failed: {exc}")

    if review_wait_result is not None and seal is not None:
        try:
            seal = _validate_v1_seal(
                artifact_text=artifact_text,
                repository=repo,
                pr_number=pr_number,
                snapshot=snapshot,
                token=token,
                outage_security_wait_seconds=0,
                enforce_outage_security_checks=True,
                require_committed_closeout=True,
            )
        except (CommitIdentityError, ReviewEvidenceError, OSError, ValueError) as exc:
            errors.append(f"Post-wait material review seal validation failed: {exc}")

    try:
        final_pr_context = _fetch_pr_context(pr_number=pr_number, repo=repo, token=token)
        final_actionable_items = _collect_actionable_items(
            repo=repo, pr_number=pr_number, token=token
        )
        final_review_threads = fetch_review_threads(repo, pr_number, token=token)
        if final_pr_context != (pr_number, repo, is_draft, pr_body, head_ref):
            raise CommitIdentityError(
                "SNAPSHOT_CHANGED: live PR body or draft state changed during validation"
            )
        if _actionable_inventory(final_actionable_items) != _actionable_inventory(actionable_items):
            raise CommitIdentityError(
                "SNAPSHOT_CHANGED: actionable bot review inventory changed during validation"
            )
        if _review_thread_inventory(final_review_threads) != _review_thread_inventory(
            review_threads
        ):
            raise CommitIdentityError(
                "SNAPSHOT_CHANGED: review-thread inventory changed during validation"
            )
        if args.pre_closeout and expected_mapping_path is not None:
            if _local_head_sha() != snapshot.head_sha:
                raise CommitIdentityError(
                    "SNAPSHOT_CHANGED: local HEAD changed during pre-closeout validation"
                )
            if _pre_closeout_dirty_paths() != {expected_mapping_path}:
                raise CommitIdentityError(
                    "SNAPSHOT_CHANGED: local working tree changed during pre-closeout validation"
                )
            if read_mapping_artifact(pr_number) != artifact_text:
                raise CommitIdentityError(
                    "SNAPSHOT_CHANGED: canonical mapping artifact changed during "
                    "pre-closeout validation"
                )
        assert_snapshot_unchanged(snapshot, token=token)
    except (CommitIdentityError, OSError, ValueError, urllib.error.HTTPError) as exc:
        errors.append(str(exc))

    if errors:
        gate_label = (
            "pre-closeout review-governance check"
            if args.pre_closeout
            else "review-governance merge gate"
        )
        print(f"ERROR: {gate_label} failed:")
        for line in errors:
            print(f"- {line}")
        return 1

    if args.pre_closeout:
        print(
            "pre-closeout-review-governance: passed; all live actionable bot issue comments, "
            "bot inline comments, and top-level bot reviews are explicitly mapped."
        )
        print("pre-closeout-review-governance: not merge-readiness evidence.")
        return 0

    print("merge-readiness-gate: passed (review governance only).")
    if seal is not None:
        print(f"CONTENT_BOUND_RECEIPT_VALID {seal['material']['digest']}")
        print("PROVIDER_NO_CLAIM_VALID review_claim=none scan_claim=none")
    if review_wait_result is not None:
        observations, events = review_wait_result
        print(
            "REVIEW_WAIT_WINDOW_VALID "
            f"observations={observations} quiet_seconds={_REVIEW_QUIET_SECONDS} events={events}"
        )
    if duplicate_covered_urls:
        print(f"DUPLICATE_FINDING_REUSED count={len(duplicate_covered_urls)}")
    print(
        "Zero comments: 0 unresolved threads, all actionable bot comments mapped in canonical artifact."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
