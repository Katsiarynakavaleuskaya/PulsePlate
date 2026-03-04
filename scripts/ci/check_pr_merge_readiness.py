"""Merge-readiness CI gate: fail when non-draft PR has unresolved threads or unmapped bot comments."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


@dataclass
class ActionableItem:
    """A single bot comment/review deemed actionable (needs mapping in PR body)."""

    author: str
    url: str
    created_at: str
    kind: str


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
    body = response.read().decode("utf-8")
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
    while True:
        payload = {
            "query": query,
            "variables": {"owner": owner, "name": name, "number": pr_number, "cursor": cursor},
        }
        resp = _api_request(
            "https://api.github.com/graphql", token=token, method="POST", payload=payload
        )
        threads = (
            resp.get("data", {})
            .get("repository", {})
            .get("pullRequest", {})
            .get("reviewThreads", {})
        )
        nodes = threads.get("nodes", [])
        total += sum(
            1
            for item in nodes
            if item
            and not item.get("isResolved", False)
            and not _is_non_conversation_security_thread(item)
        )
        page_info = threads.get("pageInfo", {})
        if not page_info.get("hasNextPage", False):
            break
        cursor = page_info.get("endCursor")
        if not cursor:
            break
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
    while True:
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}{sep}page={page}" if page > 1 else base_url
        data = _api_request(url, token=token)
        if not isinstance(data, list):
            return out
        out.extend(data)
        if len(data) < 100:
            break
        page += 1
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
            items.append(
                ActionableItem(
                    author=author,
                    url=url,
                    created_at=created_at,
                    kind=kind,
                )
            )

    unique = {item.url: item for item in items}
    return sorted(unique.values(), key=lambda it: it.created_at)


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
    args = parser.parse_args()
    # Mutually exclusive: CI mode (--event-path) vs local/agent mode (--pr-number + --repo).
    if args.event_path and (args.pr_number is not None or (args.repo or "").strip()):
        parser.error("Use either --event-path (CI) or --pr-number and --repo (local), not both.")
    if (args.pr_number is not None) != bool((args.repo or "").strip()):
        parser.error("For local/agent mode provide both --pr-number and --repo.")

    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        print("ERROR: GITHUB_TOKEN is required for merge-readiness gate.")
        return 1

    if args.event_path:
        try:
            pr_number, repo, is_draft, pr_body = _extract_pr_context(Path(args.event_path))
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
        print("merge-readiness-gate: no PR context found; skipping.")
        return 0

    if is_draft:
        print("merge-readiness-gate: PR is draft; skipping strict checks.")
        return 0

    errors: list[str] = []

    try:
        unresolved_threads = _graphql_unresolved_threads(
            repo=repo, pr_number=pr_number, token=token
        )
    except urllib.error.HTTPError as exc:
        print(f"ERROR: cannot query unresolved review threads: HTTP {exc.code}")
        return 1

    if unresolved_threads > 0:
        errors.append(
            f"Unresolved review threads: {unresolved_threads}. Resolve all threads before merge."
        )

    try:
        actionable_items = _collect_actionable_items(repo=repo, pr_number=pr_number, token=token)
    except urllib.error.HTTPError as exc:
        print(f"ERROR: cannot query bot comments/reviews: HTTP {exc.code}")
        return 1

    mapped_urls, no_actionable_marker = _mapped_urls(pr_body=pr_body)

    if actionable_items:
        if no_actionable_marker:
            errors.append(
                "PR body claims `No actionable review comments` but actionable bot findings were detected."
            )
        unmapped = [item for item in actionable_items if item.url not in mapped_urls]
        if unmapped:
            errors.append(
                "Unmapped actionable bot comments found in `### Fixed in Commit Mapping` "
                "(add `<review-comment-url> -> <commit-sha>` entries)."
            )
            for item in unmapped:
                print(f"UNMAPPED: {item.author} [{item.kind}] {item.url} ({item.created_at})")

    if errors:
        print("ERROR: merge-readiness gate failed:")
        for line in errors:
            print(f"- {line}")
        return 1

    print("merge-readiness-gate: passed.")
    print("Zero comments: 0 unresolved threads, all actionable bot comments mapped in PR body.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
