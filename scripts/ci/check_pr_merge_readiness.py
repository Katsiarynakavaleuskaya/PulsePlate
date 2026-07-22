"""Review-governance merge gate for unresolved threads and bot-comment mapping.

This script does not classify current-head required checks; the canonical
required-check truth lives in `check_current_head_pr_checks.py` and the
`check_merge_ready.py` wrapper bundles both hard gates.
"""

from __future__ import annotations

import argparse
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
    CodexConnectorAdvisoryReactionEvidence,
    PrSnapshot,
    RepositoryCommitRef,
    ReviewThreadEvidence,
    assert_snapshot_unchanged,
    classify_commit_ref,
    fetch_pr_snapshot,
    fetch_review_threads,
    is_ancestor,
    verify_codex_review_reference,
    verify_codex_review_source_unavailability_reference,
    verify_review_credit_outage_references,
    verify_security_outage_override_reference,
)
from scripts.orchestration.pr_review_evidence import (  # noqa: E402
    ReviewEvidenceError,
    build_review_credit_outage_receipt,
    build_review_source_positive_response_receipt,
    build_review_source_unavailability_receipt,
    build_security_outage_override_receipt,
    compute_material_manifest,
    is_review_credit_outage_receipt,
    is_mapping_only_positive_response_successor,
    is_review_source_positive_response_receipt,
    is_review_source_unavailability_receipt,
    is_security_outage_override_receipt,
    parse_embedded_review_seal,
    validate_review_credit_outage_scope,
    validate_security_outage_override_scope,
    validated_duplicate_reply_urls,
)
from scripts.ci.check_current_head_pr_checks import (  # noqa: E402
    _fetch_pr_metadata as _fetch_current_head_pr_metadata,
    _latest_entries as _latest_check_entries,
    _normalize_node as _normalize_check_node,
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
MARKDOWN_LINK_RE = re.compile(
    r"(?<![!\\])\[[^\]\n]+\]\(\s*(?:<(?P<angle>[^>\n]+)>|(?P<plain>[^\s)\n]+))"
    r"(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\s*\)"
)
_MAX_API_RESPONSE_BYTES = 8 * 1024 * 1024
_MAX_API_PAGES = 100
_OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES: Mapping[str, tuple[str, int, str]] = {
    "Analyze (actions)": ("CodeQL Advanced", 15_368, "github-actions"),
    "Analyze (javascript-typescript)": ("CodeQL Advanced", 15_368, "github-actions"),
    "Analyze (python)": ("CodeQL Advanced", 15_368, "github-actions"),
    "Private Python proxy health": ("CI", 15_368, "github-actions"),
    "Trivy ignore-policy expiry": ("CI", 15_368, "github-actions"),
    "security": ("CI", 15_368, "github-actions"),
    "security-scan": ("Docker Build and Push", 15_368, "github-actions"),
}


@dataclass
class ActionableItem:
    """A single bot comment/review deemed actionable (needs mapping in PR body)."""

    author: str
    url: str
    created_at: str
    kind: str
    review_id: int | None = None


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


def _canonical_artifact_markdown_link_count(pr_body: str, pr_number: int, repository: str) -> int:
    """Count real inline Markdown links whose destination is the canonical artifact."""

    artifact_path = f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    absolute_prefix = f"/{repository}/blob/"
    absolute_suffix = f"/{artifact_path}"
    count = 0
    body_without_comments = re.sub(r"(?s)<!--.*?-->", "", pr_body)
    body_without_fences = _strip_fenced_code_blocks(body_without_comments)
    body_without_indented_code = re.sub(r"(?m)^(?: {4}|\t).*?(?:\n|$)", "", body_without_fences)
    body_without_code = re.sub(r"`[^`\n]*`", "", body_without_indented_code)
    for match in MARKDOWN_LINK_RE.finditer(body_without_code):
        destination = urllib.parse.unquote(match.group("angle") or match.group("plain") or "")
        parsed = urllib.parse.urlsplit(destination)
        if parsed.query or parsed.fragment:
            continue
        if parsed.scheme or parsed.netloc:
            if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
                continue
            ref_path = ""
            if parsed.path.startswith(absolute_prefix) and parsed.path.endswith(absolute_suffix):
                ref_path = parsed.path[len(absolute_prefix) : -len(absolute_suffix)]
            is_canonical_destination = bool(ref_path) and all(
                segment not in {"", ".", ".."} for segment in ref_path.split("/")
            )
        else:
            is_canonical_destination = parsed.path in {artifact_path, f"./{artifact_path}"}
        if is_canonical_destination:
            count += 1
    return count


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
                )
            )

    unique = {item.url: item for item in items}
    return sorted(unique.values(), key=lambda it: it.created_at)


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


def _extract_pr_context(event_path: Path) -> tuple[int, str, bool, str]:
    """Read GitHub event JSON; return (pr_number, repo, is_draft, pr_body)."""
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    pr = payload.get("pull_request") or {}
    number = int(pr.get("number", 0))
    repo = str((payload.get("repository") or {}).get("full_name", ""))
    is_draft = bool(pr.get("draft", False))
    body = str(pr.get("body") or "")
    return number, repo, is_draft, body


def _fetch_pr_context(pr_number: int, repo: str, token: str) -> tuple[int, str, bool, str]:
    """Fetch PR via REST API; return (pr_number, repo, is_draft, pr_body). For local/agent use."""
    owner, name = repo.split("/", maxsplit=1)
    url = f"https://api.github.com/repos/{owner}/{name}/pulls/{pr_number}"
    data = _api_request(url, token=token)
    body = str(data.get("body") or "")
    is_draft = bool(data.get("draft", False))
    return pr_number, repo, is_draft, body


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


def _validate_operator_outage_security_checks(
    *,
    repository: str,
    pr_number: int,
    token: str,
    expected_head_sha: str,
    security_required: bool = True,
) -> None:
    """Require a strict successful current-head security bundle for outage overrides."""

    _is_draft, _merge_state, _base_ref, nodes = _fetch_current_head_pr_metadata(
        pr_number, repository, token, expected_head_sha
    )
    try:
        entries = [_normalize_check_node(node) for node in nodes if node]
    except ValueError as exc:
        raise ReviewEvidenceError(
            f"operator outage override cannot order current-head security checks: {exc}"
        ) from exc
    latest, superseded = _latest_check_entries(entries)
    latest, _superseded = _suppress_stale_check_entries(
        entries,
        latest,
        superseded,
    )
    terminal_failures: list[str] = []
    pending_failures: list[str] = []
    for name, expected_identity in sorted(_OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES.items()):
        candidates = [entry for entry in entries if entry.name == name]
        if not candidates:
            pending_failures.append(f"{name}=missing")
            continue
        expected_workflow, expected_app_id, expected_app_slug = expected_identity
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
            pending_failures.append(f"{name}=missing-latest")
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
            "operator outage override requires successful current-head security checks: "
            + ", ".join(failures)
            + ". Pending or not-yet-visible exact-head checks may be retried only "
            "within the bounded CI wait; failed or untrusted checks remain terminal."
        )


def _wait_for_operator_outage_security_checks(
    *,
    repository: str,
    pr_number: int,
    token: str,
    expected_head_sha: str,
    security_required: bool,
    timeout_seconds: int,
    poll_interval_seconds: int = 15,
) -> None:
    """Wait only for transient exact-head substitute-check states, then fail closed."""

    if timeout_seconds < 0:
        raise ValueError("outage security wait must be non-negative")
    if poll_interval_seconds <= 0:
        raise ValueError("outage security poll interval must be positive")

    deadline = time.monotonic() + timeout_seconds
    attempt = 1
    while True:
        try:
            _validate_operator_outage_security_checks(
                repository=repository,
                pr_number=pr_number,
                token=token,
                expected_head_sha=expected_head_sha,
                security_required=security_required,
            )
            return
        except _OutageSecurityChecksPending as exc:
            remaining = deadline - time.monotonic()
            if timeout_seconds == 0 or remaining <= 0:
                raise ReviewEvidenceError(
                    "operator outage override timed out waiting for exact-head "
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


def _validate_v1_seal(
    *,
    artifact_text: str,
    repository: str,
    pr_number: int,
    snapshot: PrSnapshot,
    token: str,
    outage_security_wait_seconds: int = 0,
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
    if is_review_source_positive_response_receipt(code_review):
        response_manifest = compute_material_manifest(
            REPO_ROOT,
            base_ref_oid=snapshot.base_sha,
            head_ref_oid=material_head.sha,
            pr_number=pr_number,
        )
        if response_manifest.digest != material["digest"]:
            raise ReviewEvidenceError(
                "positive response material head has a different material digest"
            )
        response_evidence = verify_codex_review_reference(
            code_review["response_reference"],
            repository=repository,
            pr_number=pr_number,
            token=token,
            expected_commit_ref=material_head.sha,
            expected_live_pr_head_ref=snapshot.head_sha,
        )
        if not isinstance(response_evidence, CodexConnectorAdvisoryReactionEvidence):
            raise ReviewEvidenceError("Codex positive response reference changed evidence type")
        expected_code_review = build_review_source_positive_response_receipt(
            material_digest=material["digest"],
            material_head_sha=material_head.sha,
            response_reference=response_evidence.reference,
            response_created_at=response_evidence.created_at,
            response_content=response_evidence.content,
        )
        successor_response = (
            snapshot.head_sha != material_head.sha
            and is_mapping_only_positive_response_successor(
                code_review,
                response_reference=response_evidence.reference,
                response_created_at=response_evidence.created_at,
                response_content=response_evidence.content,
            )
        )
        if code_review != expected_code_review and not successor_response:
            raise ReviewEvidenceError("Codex positive response receipt is stale")
    elif is_review_source_unavailability_receipt(code_review):
        unavailable_manifest = compute_material_manifest(
            REPO_ROOT,
            base_ref_oid=snapshot.base_sha,
            head_ref_oid=material_head.sha,
            pr_number=pr_number,
        )
        if unavailable_manifest.digest != material["digest"]:
            raise ReviewEvidenceError(
                "review-source unavailable material head has a different material digest"
            )
        source_evidence = verify_codex_review_source_unavailability_reference(
            code_review["quota_reference"],
            repository=repository,
            pr_number=pr_number,
            token=token,
        )
        expected_code_review = build_review_source_unavailability_receipt(
            material_digest=material["digest"],
            material_head_sha=material_head.sha,
            quota_reference=source_evidence.reference,
            quota_created_at=source_evidence.created_at,
            quota_body_sha256=source_evidence.body_sha256,
            source_status=source_evidence.source_status,
        )
        if code_review != expected_code_review:
            raise ReviewEvidenceError("Codex review-source unavailability receipt is stale")
    elif is_review_credit_outage_receipt(code_review):
        review_prefix = f"https://github.com/{repository}/pull/{pr_number}#"
        if not code_review["review_reference"].startswith(review_prefix):
            raise ReviewEvidenceError("code-review reference belongs to another PR")
        validate_review_credit_outage_scope(
            repository=repository,
            pr_number=pr_number,
            material_paths=(entry.path for entry in manifest.entries),
        )
        credit_evidence = verify_review_credit_outage_references(
            override_reference=code_review["override_reference"],
            quota_reference=code_review["quota_reference"],
            prior_review_reference=code_review["prior_review_reference"],
            operator_review_reference=code_review["review_reference"],
            repository=repository,
            pr_number=pr_number,
            token=token,
            snapshot=snapshot,
            expected_material_head_sha=material_head.sha,
            expected_material_digest=material["digest"],
        )
        expected_code_review = build_review_credit_outage_receipt(
            material_digest=material["digest"],
            material_head_sha=material_head.sha,
            override_reference=credit_evidence.override_reference,
            override_created_at=credit_evidence.override_created_at,
            quota_reference=credit_evidence.quota_reference,
            quota_created_at=credit_evidence.quota_created_at,
            prior_review_reference=credit_evidence.prior_review_reference,
            prior_review_submitted_at=credit_evidence.prior_review_submitted_at,
            prior_review_commit_ref=credit_evidence.prior_review_commit_ref,
            operator_review_reference=credit_evidence.operator_review_reference,
            operator_review_submitted_at=credit_evidence.operator_review_submitted_at,
            operator_user_id=credit_evidence.operator_user_id,
            operator_login=credit_evidence.operator_login,
            operator_association=credit_evidence.operator_association,
        )
        if code_review != expected_code_review:
            raise ReviewEvidenceError("Codex review credit-outage receipt is stale")
    else:
        review_prefix = f"https://github.com/{repository}/pull/{pr_number}#"
        if not code_review["review_reference"].startswith(review_prefix):
            raise ReviewEvidenceError("code-review reference belongs to another PR")
        review_evidence = verify_codex_review_reference(
            code_review["review_reference"],
            repository=repository,
            pr_number=pr_number,
            token=token,
            expected_commit_ref=material["material_head_sha"],
            # The digest check above permits only the canonical mapping artifact
            # to separate the sealed material head from the live PR head.
            expected_live_pr_head_ref=snapshot.head_sha,
        )
        if isinstance(review_evidence, CodexConnectorAdvisoryReactionEvidence):
            raise ReviewEvidenceError("Codex positive response is not exact-head review evidence")
        if (
            review_evidence.commit_ref != code_review["review_commit_ref"]
            or code_review["review_commit_ref_kind"] != "repository_commit"
            or review_evidence.commit_ref != material["material_head_sha"]
        ):
            raise ReviewEvidenceError("Codex review is not bound to the sealed material head")
        review_commit = classify_commit_ref(review_evidence.commit_ref, snapshot, token=token)
        if not isinstance(review_commit, RepositoryCommitRef) or review_commit.kind not in {
            CommitRefKind.PR_HEAD,
            CommitRefKind.PR_COMMIT,
        }:
            raise ReviewEvidenceError("Codex review commit is not a real commit in the live PR")
        reviewed_manifest = compute_material_manifest(
            REPO_ROOT,
            base_ref_oid=snapshot.base_sha,
            head_ref_oid=review_commit.sha,
            pr_number=pr_number,
        )
        if reviewed_manifest.digest != material["digest"]:
            raise ReviewEvidenceError("Codex review commit has a different material digest")
    live_head = RepositoryCommitRef(snapshot.head_sha, CommitRefKind.PR_HEAD)
    if not is_ancestor(
        material_head,
        live_head,
        repository=repository,
        token=token,
    ):
        raise ReviewEvidenceError("material head is not an ancestor of the live PR head")
    if (
        seal["codex_security"]["base_revision"] != manifest.merge_base_sha
        or seal["codex_security"]["head_revision"] != material_head.sha
    ):
        raise ReviewEvidenceError("Codex Security receipt range is stale")
    security_receipt = seal["codex_security"]
    if is_security_outage_override_receipt(security_receipt):
        validate_security_outage_override_scope(
            repository=repository,
            pr_number=pr_number,
            material_paths=(entry.path for entry in manifest.entries),
        )
        outage_evidence = verify_security_outage_override_reference(
            security_receipt["override_reference"],
            repository=repository,
            pr_number=pr_number,
            token=token,
            expected_material_head_sha=material_head.sha,
            expected_material_digest=material["digest"],
        )
        expected_receipt = build_security_outage_override_receipt(
            base_revision=manifest.merge_base_sha,
            head_revision=material_head.sha,
            material_digest=material["digest"],
            override_reference=outage_evidence.reference,
            created_at=outage_evidence.created_at,
            operator_user_id=outage_evidence.operator_user_id,
            operator_login=outage_evidence.operator_login,
            operator_association=outage_evidence.operator_association,
        )
        if security_receipt != expected_receipt:
            raise ReviewEvidenceError("Codex Security operator outage override receipt is stale")
        _wait_for_operator_outage_security_checks(
            repository=repository,
            pr_number=pr_number,
            token=token,
            expected_head_sha=snapshot.head_sha,
            security_required=_operator_outage_security_required(
                entry.path for entry in manifest.entries
            ),
            timeout_seconds=outage_security_wait_seconds,
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
    if not records:
        return set()
    candidate_urls = {
        item.url
        for item in actionable_items
        if item.url not in mapped_urls and item.kind == "review_comment"
    }
    raw_covered_urls = validated_duplicate_reply_urls(
        candidate_urls=candidate_urls,
        threads=threads,
        fingerprint_records=records,
        material_digest=str(seal["material"]["digest"]),
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
        default=0,
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

    if args.event_path:
        try:
            pr_number, repo, is_draft, pr_body = _extract_pr_context(Path(args.event_path))
            if pr_number and repo:
                pr_number, repo, is_draft, pr_body = _fetch_pr_context(
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
            pr_number, repo, is_draft, pr_body = _fetch_pr_context(
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
    if _canonical_artifact_markdown_link_count(pr_body, pr_number, repo) != 1:
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

    if actionable_items:
        if no_actionable_marker:
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

    try:
        assert_snapshot_unchanged(snapshot, token=token)
    except (CommitIdentityError, OSError) as exc:
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
            "pre-closeout-review-governance: passed; all live actionable issue comments, "
            "inline comments, and top-level bot reviews are explicitly mapped."
        )
        print("pre-closeout-review-governance: not merge-readiness evidence.")
        return 0

    print("merge-readiness-gate: passed (review governance only).")
    if seal is not None:
        print(f"CONTENT_BOUND_RECEIPT_VALID {seal['material']['digest']}")
        if is_review_source_positive_response_receipt(seal["code_review"]):
            print(
                f"REVIEW_SOURCE_POSITIVE_RESPONSE_VALID {seal['code_review']['response_content']}"
            )
        elif is_review_source_unavailability_receipt(seal["code_review"]):
            print(f"REVIEW_SOURCE_UNAVAILABLE_VALID {seal['code_review']['source_status']}")
        elif is_review_credit_outage_receipt(seal["code_review"]):
            print(f"REVIEW_CREDIT_OUTAGE_OVERRIDE_VALID {seal['code_review']['review_commit_ref']}")
        else:
            print(f"MACHINE_BOUND_REVIEW_COMMIT {seal['code_review']['review_commit_ref']}")
    if duplicate_covered_urls:
        print(f"DUPLICATE_FINDING_REUSED count={len(duplicate_covered_urls)}")
    print(
        "Zero comments: 0 unresolved threads, all actionable bot comments mapped in canonical artifact."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
