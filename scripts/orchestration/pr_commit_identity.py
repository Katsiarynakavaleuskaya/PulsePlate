"""Fail-closed GitHub identity proof for pull-request commits.

Review-provider execution references are deliberately represented by a
different type from repository-addressable commits.  Callers can therefore
perform ancestry checks only after GitHub has proved that both endpoints are
real commits in the live pull-request snapshot.
"""

from __future__ import annotations

import http.client
import json
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Mapping

_API_HOST = "api.github.com"
_API_ROOT = f"https://{_API_HOST}"
_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_MAX_PR_COMMIT_PAGES = 100
_MAX_PR_COMMITS = 10_000
_MAX_REVIEW_THREAD_PAGES = 100
_MAX_REVIEW_COMMENT_PAGES = 100
_MAX_REVIEW_THREADS = 10_000
_MAX_REVIEW_COMMENTS = 10_000
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_ISO_8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


class CommitIdentityError(RuntimeError):
    """Raised when GitHub cannot supply complete, unambiguous identity proof."""


class GitHubHttpError(CommitIdentityError):
    """Sanitized GitHub HTTP failure; response bodies are never exposed."""

    def __init__(self, status: int, message: str = "", api_message: str = "") -> None:
        super().__init__(f"GitHub API request failed with HTTP {status}: {message}".rstrip())
        self.status = status
        self.api_message = api_message


class CommitRefKind(str, Enum):
    """Closed identity classes used by review governance."""

    PR_HEAD = "pr_head"
    PR_COMMIT = "pr_commit"
    REPO_COMMIT_OUTSIDE_PR = "repo_commit_outside_pr"
    REVIEW_REF_UNAVAILABLE = "review_ref_unavailable"
    API_UNKNOWN = "api_unknown"


@dataclass(frozen=True)
class PrCommitEvidence:
    """Server-side evidence attached to a commit in the PR connection."""

    sha: str
    pushed_at: str | None


@dataclass(frozen=True)
class PrSnapshot:
    """Immutable live PR refs plus the complete commit connection."""

    repository: str
    pr_number: int
    base_sha: str
    head_sha: str
    commits: tuple[PrCommitEvidence, ...]

    @property
    def commit_shas(self) -> frozenset[str]:
        return frozenset(commit.sha for commit in self.commits)


@dataclass(frozen=True)
class ReviewCommentEvidence:
    """Bounded review-comment fields used by duplicate-disposition validation."""

    url: str
    body: str
    created_at: str
    author_login: str
    author_association: str
    original_commit_sha: str | None


@dataclass(frozen=True)
class ReviewThreadEvidence:
    """One fully paginated GitHub review thread."""

    node_id: str
    is_resolved: bool
    comments: tuple[ReviewCommentEvidence, ...]


@dataclass(frozen=True)
class CodexReviewEvidence:
    """Trusted submitted review metadata; commit_ref still needs graph proof."""

    reference: str
    submitted_at: str
    commit_ref: str


@dataclass(frozen=True)
class RepositoryCommitRef:
    """A repository-addressable commit safe to pass to ancestry checks."""

    sha: str
    kind: CommitRefKind
    pushed_at: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in {
            CommitRefKind.PR_HEAD,
            CommitRefKind.PR_COMMIT,
            CommitRefKind.REPO_COMMIT_OUTSIDE_PR,
        }:
            raise ValueError(f"RepositoryCommitRef cannot carry kind={self.kind.value}")
        _require_sha(self.sha, field="repository commit")


@dataclass(frozen=True)
class ReviewExecutionRef:
    """An unavailable or API-unknown reviewer reference; never graph-safe."""

    value: str
    kind: CommitRefKind
    reason: str

    def __post_init__(self) -> None:
        if self.kind not in {
            CommitRefKind.REVIEW_REF_UNAVAILABLE,
            CommitRefKind.API_UNKNOWN,
        }:
            raise ValueError(f"ReviewExecutionRef cannot carry kind={self.kind.value}")


CommitResolution = RepositoryCommitRef | ReviewExecutionRef
ApiRequest = Callable[..., Any]


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CommitIdentityError(f"GitHub JSON contains duplicate key {key!r}")
        result[key] = value
    return result


def _json_loads(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CommitIdentityError("GitHub API returned malformed JSON") from exc


def github_api_request(
    url: str,
    *,
    token: str,
    method: str = "GET",
    payload: Mapping[str, Any] | None = None,
) -> Any:
    """Issue one bounded request to GitHub's API with sanitized failures."""

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != _API_HOST or parsed.fragment:
        raise CommitIdentityError("GitHub API URL must use https://api.github.com")
    if not token.strip():
        raise CommitIdentityError("GitHub API token is required")

    body = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "pulseplate-pr-commit-identity",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        headers["Content-Type"] = "application/json"

    path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    connection = http.client.HTTPSConnection(_API_HOST, timeout=30)
    try:
        connection.request(method=method, url=path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read(_MAX_RESPONSE_BYTES + 1)
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise CommitIdentityError("GitHub API response exceeds size limit")
        if response.status >= 400:
            api_message = ""
            try:
                error_payload = _json_loads(raw)
                if isinstance(error_payload, dict):
                    api_message = str(error_payload.get("message") or "")
            except CommitIdentityError:
                pass
            raise GitHubHttpError(response.status, response.reason or "error", api_message)
        content_type = (response.getheader("Content-Type") or "").lower()
        if "json" not in content_type:
            raise CommitIdentityError("GitHub API returned a non-JSON response")
        return _json_loads(raw)
    finally:
        connection.close()


def _require_sha(value: str, *, field: str) -> str:
    normalized = value.strip().lower()
    if not _SHA_RE.fullmatch(normalized):
        raise CommitIdentityError(f"{field} must be a full lowercase 40-character SHA")
    return normalized


def _require_repository(repository: str) -> tuple[str, str]:
    parts = repository.strip().split("/")
    if len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts):
        raise CommitIdentityError("repository must be owner/name")
    return parts[0], parts[1]


def _require_graphql_object(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise CommitIdentityError("GitHub GraphQL response must be an object")
    if response.get("errors"):
        raise CommitIdentityError("GitHub GraphQL response contains errors")
    data = response.get("data")
    if not isinstance(data, dict):
        raise CommitIdentityError("GitHub GraphQL response is missing data")
    return data


def _require_iso8601(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not _ISO_8601_RE.fullmatch(value):
        raise CommitIdentityError(f"{field} must be a timezone-aware ISO-8601 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise CommitIdentityError(f"{field} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise CommitIdentityError(f"{field} must include a timezone")
    return value


def _parse_pr_page(
    response: Any,
) -> tuple[str, str, list[PrCommitEvidence], bool, str | None]:
    data = _require_graphql_object(response)
    repository = data.get("repository")
    if not isinstance(repository, dict):
        raise CommitIdentityError("GitHub GraphQL response is missing repository")
    pull_request = repository.get("pullRequest")
    if not isinstance(pull_request, dict):
        raise CommitIdentityError("GitHub GraphQL response is missing pullRequest")
    base_sha = _require_sha(str(pull_request.get("baseRefOid") or ""), field="baseRefOid")
    head_sha = _require_sha(str(pull_request.get("headRefOid") or ""), field="headRefOid")
    connection = pull_request.get("commits")
    if not isinstance(connection, dict):
        raise CommitIdentityError("GitHub GraphQL response is missing commits connection")
    nodes = connection.get("nodes")
    page_info = connection.get("pageInfo")
    if not isinstance(nodes, list) or not isinstance(page_info, dict):
        raise CommitIdentityError("GitHub commits connection has invalid shape")

    parsed_nodes: list[PrCommitEvidence] = []
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("commit"), dict):
            raise CommitIdentityError("GitHub commits connection contains malformed node")
        commit = node["commit"]
        oid = _require_sha(str(commit.get("oid") or ""), field="PR commit oid")
        pushed_at_raw = commit.get("pushedDate")
        if pushed_at_raw is not None and (
            not isinstance(pushed_at_raw, str) or not _ISO_8601_RE.fullmatch(pushed_at_raw)
        ):
            raise CommitIdentityError("GitHub PR commit pushedDate is malformed")
        parsed_nodes.append(PrCommitEvidence(sha=oid, pushed_at=pushed_at_raw))

    has_next_page = page_info.get("hasNextPage")
    end_cursor = page_info.get("endCursor")
    if not isinstance(has_next_page, bool):
        raise CommitIdentityError("GitHub commits pageInfo.hasNextPage must be boolean")
    if end_cursor is not None and not isinstance(end_cursor, str):
        raise CommitIdentityError("GitHub commits pageInfo.endCursor must be string or null")
    return base_sha, head_sha, parsed_nodes, has_next_page, end_cursor


def fetch_pr_snapshot(
    repository: str,
    pr_number: int,
    *,
    token: str,
    request_json: ApiRequest = github_api_request,
) -> PrSnapshot:
    """Fetch the complete PR commit connection while pinning base/head on every page."""

    owner, name = _require_repository(repository)
    if pr_number <= 0:
        raise CommitIdentityError("pr_number must be positive")
    query = """
    query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $number) {
          baseRefOid
          headRefOid
          commits(first: 100, after: $cursor) {
            nodes { commit { oid pushedDate } }
            pageInfo { hasNextPage endCursor }
          }
        }
      }
    }
    """
    cursor: str | None = None
    seen_cursors: set[str] = set()
    expected_refs: tuple[str, str] | None = None
    commits: list[PrCommitEvidence] = []

    for _page in range(_MAX_PR_COMMIT_PAGES):
        response = request_json(
            f"{_API_ROOT}/graphql",
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
        base_sha, head_sha, page_commits, has_next, end_cursor = _parse_pr_page(response)
        page_refs = (base_sha, head_sha)
        if expected_refs is None:
            expected_refs = page_refs
        elif page_refs != expected_refs:
            raise CommitIdentityError("PR base/head changed during commit pagination")
        commits.extend(page_commits)
        if len(commits) > _MAX_PR_COMMITS:
            raise CommitIdentityError("PR commit connection exceeds safety limit")
        if not has_next:
            break
        if not end_cursor or end_cursor == cursor or end_cursor in seen_cursors:
            raise CommitIdentityError("PR commit pagination cursor is missing or repeated")
        seen_cursors.add(end_cursor)
        cursor = end_cursor
    else:
        raise CommitIdentityError("PR commit pagination exceeded page limit")

    if expected_refs is None or not commits:
        raise CommitIdentityError("PR commit connection is empty")
    shas = [commit.sha for commit in commits]
    if len(shas) != len(set(shas)):
        raise CommitIdentityError("PR commit connection contains duplicate OIDs")
    if expected_refs[1] not in set(shas):
        raise CommitIdentityError("live PR head is absent from the PR commit connection")
    return PrSnapshot(
        repository=repository,
        pr_number=pr_number,
        base_sha=expected_refs[0],
        head_sha=expected_refs[1],
        commits=tuple(commits),
    )


def _is_unavailable_422(error: GitHubHttpError, sha: str) -> bool:
    return error.status == 422 and error.api_message in {
        "No commit found for SHA",
        f"No commit found for SHA: {sha}",
    }


def classify_commit_ref(
    value: str,
    snapshot: PrSnapshot,
    *,
    token: str,
    request_json: ApiRequest = github_api_request,
) -> CommitResolution:
    """Classify a ref using Commit API existence plus complete PR membership."""

    try:
        sha = _require_sha(value, field="commit reference")
    except CommitIdentityError as exc:
        return ReviewExecutionRef(value=value, kind=CommitRefKind.API_UNKNOWN, reason=str(exc))
    owner, name = _require_repository(snapshot.repository)
    encoded_sha = urllib.parse.quote(sha, safe="")
    try:
        response = request_json(
            f"{_API_ROOT}/repos/{owner}/{name}/commits/{encoded_sha}",
            token=token,
        )
    except GitHubHttpError as exc:
        if exc.status == 404 or _is_unavailable_422(exc, sha):
            return ReviewExecutionRef(
                value=sha,
                kind=CommitRefKind.REVIEW_REF_UNAVAILABLE,
                reason="commit is unavailable from the GitHub Commit API",
            )
        return ReviewExecutionRef(
            value=sha,
            kind=CommitRefKind.API_UNKNOWN,
            reason=f"Commit API failed with HTTP {exc.status}",
        )
    except (CommitIdentityError, OSError, TimeoutError) as exc:
        return ReviewExecutionRef(
            value=sha,
            kind=CommitRefKind.API_UNKNOWN,
            reason=f"Commit API could not prove identity: {type(exc).__name__}",
        )
    if not isinstance(response, dict):
        return ReviewExecutionRef(
            value=sha,
            kind=CommitRefKind.API_UNKNOWN,
            reason="Commit API response is malformed",
        )
    try:
        returned_sha = _require_sha(str(response.get("sha") or ""), field="Commit API sha")
    except CommitIdentityError as exc:
        return ReviewExecutionRef(value=sha, kind=CommitRefKind.API_UNKNOWN, reason=str(exc))
    if returned_sha != sha:
        return ReviewExecutionRef(
            value=sha,
            kind=CommitRefKind.API_UNKNOWN,
            reason="Commit API returned a different SHA",
        )

    pushed_by_sha = {commit.sha: commit.pushed_at for commit in snapshot.commits}
    if sha == snapshot.head_sha:
        kind = CommitRefKind.PR_HEAD
    elif sha in pushed_by_sha:
        kind = CommitRefKind.PR_COMMIT
    else:
        kind = CommitRefKind.REPO_COMMIT_OUTSIDE_PR
    return RepositoryCommitRef(sha=sha, kind=kind, pushed_at=pushed_by_sha.get(sha))


def is_ancestor(
    ancestor: RepositoryCommitRef,
    descendant: RepositoryCommitRef,
    *,
    repository: str,
    token: str,
    request_json: ApiRequest = github_api_request,
) -> bool:
    """Return GitHub Compare ancestry; reviewer execution refs cannot be passed."""

    if not isinstance(ancestor, RepositoryCommitRef) or not isinstance(
        descendant, RepositoryCommitRef
    ):
        raise TypeError("ancestry requires two RepositoryCommitRef values")
    owner, name = _require_repository(repository)
    url = (
        f"{_API_ROOT}/repos/{owner}/{name}/compare/"
        f"{urllib.parse.quote(ancestor.sha, safe='')}..."
        f"{urllib.parse.quote(descendant.sha, safe='')}"
    )
    try:
        response = request_json(url, token=token)
    except GitHubHttpError as exc:
        raise CommitIdentityError(f"Compare API failed with HTTP {exc.status}") from exc
    if not isinstance(response, dict):
        raise CommitIdentityError("Compare API response is malformed")
    status = response.get("status")
    ahead_by = response.get("ahead_by")
    behind_by = response.get("behind_by")
    base_commit = response.get("base_commit")
    merge_base_commit = response.get("merge_base_commit")
    if (
        not isinstance(base_commit, dict)
        or not isinstance(merge_base_commit, dict)
        or base_commit.get("sha") != ancestor.sha
        or merge_base_commit.get("sha") != ancestor.sha
        or not isinstance(ahead_by, int)
        or isinstance(ahead_by, bool)
        or not isinstance(behind_by, int)
        or isinstance(behind_by, bool)
    ):
        raise CommitIdentityError("Compare API response does not bind the requested commits")
    if status == "identical":
        return ahead_by == 0 and behind_by == 0
    if status == "ahead":
        return ahead_by >= 1 and behind_by == 0
    if status in {"behind", "diverged"}:
        return False
    raise CommitIdentityError("Compare API returned unknown ancestry status")


def verify_codex_review_reference(
    reference: str,
    *,
    repository: str,
    pr_number: int,
    token: str,
    request_json: ApiRequest = github_api_request,
) -> CodexReviewEvidence:
    """Prove that a seal reference names one submitted trusted Codex PR review."""

    owner, name = _require_repository(repository)
    pattern = re.compile(
        rf"^https://github\.com/{re.escape(owner)}/{re.escape(name)}/pull/"
        rf"{pr_number}#pullrequestreview-(\d+)$"
    )
    match = pattern.fullmatch(reference)
    if not match:
        raise CommitIdentityError("code-review reference must be a GitHub PR review URL")
    review_id = match.group(1)
    response = request_json(
        f"{_API_ROOT}/repos/{owner}/{name}/pulls/{pr_number}/reviews/{review_id}",
        token=token,
    )
    if not isinstance(response, dict):
        raise CommitIdentityError("GitHub review response is malformed")
    user = response.get("user")
    login = user.get("login") if isinstance(user, dict) else None
    state = response.get("state")
    submitted_at = response.get("submitted_at")
    commit_id = response.get("commit_id")
    html_url = response.get("html_url")
    if (
        login != "chatgpt-codex-connector[bot]"
        or state not in {"COMMENTED", "APPROVED"}
        or html_url != reference
    ):
        raise CommitIdentityError("code-review reference is not a submitted trusted Codex review")
    submitted = _require_iso8601(submitted_at, field="Codex review submitted_at")
    commit_ref = _require_sha(str(commit_id or ""), field="Codex review commit_id")
    return CodexReviewEvidence(
        reference=reference,
        submitted_at=submitted,
        commit_ref=commit_ref,
    )


def assert_snapshot_unchanged(
    snapshot: PrSnapshot,
    *,
    token: str,
    request_json: ApiRequest = github_api_request,
) -> None:
    """Re-fetch live refs and fail if base or head changed during the gate."""

    owner, name = _require_repository(snapshot.repository)
    query = """
    query($owner: String!, $name: String!, $number: Int!) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $number) { baseRefOid headRefOid }
      }
    }
    """
    response = request_json(
        f"{_API_ROOT}/graphql",
        token=token,
        method="POST",
        payload={
            "query": query,
            "variables": {"owner": owner, "name": name, "number": snapshot.pr_number},
        },
    )
    data = _require_graphql_object(response)
    repository = data.get("repository")
    pull_request = repository.get("pullRequest") if isinstance(repository, dict) else None
    if not isinstance(pull_request, dict):
        raise CommitIdentityError("GitHub GraphQL response is missing pullRequest")
    refs = (
        _require_sha(str(pull_request.get("baseRefOid") or ""), field="baseRefOid"),
        _require_sha(str(pull_request.get("headRefOid") or ""), field="headRefOid"),
    )
    if refs != (snapshot.base_sha, snapshot.head_sha):
        raise CommitIdentityError("SNAPSHOT_CHANGED: live PR base/head changed during validation")


def _parse_review_comment_node(node: Any) -> ReviewCommentEvidence:
    if not isinstance(node, dict):
        raise CommitIdentityError("review thread contains malformed comment")
    author = node.get("author")
    if author is not None and not isinstance(author, dict):
        raise CommitIdentityError("review comment author is malformed")
    login = "" if author is None else author.get("login")
    if not isinstance(login, str):
        raise CommitIdentityError("review comment author login is malformed")
    url = node.get("url")
    body = node.get("body")
    created_at = node.get("createdAt")
    association = node.get("authorAssociation")
    if (
        not isinstance(url, str)
        or not url.startswith("https://github.com/")
        or not isinstance(body, str)
        or len(body.encode("utf-8")) > 256 * 1024
        or not isinstance(association, str)
    ):
        raise CommitIdentityError("review comment fields are malformed")
    original_commit = node.get("originalCommit")
    if original_commit is not None and not isinstance(original_commit, dict):
        raise CommitIdentityError("review comment originalCommit is malformed")
    original_sha = None
    if isinstance(original_commit, dict):
        original_sha = _require_sha(
            str(original_commit.get("oid") or ""), field="review comment originalCommit"
        )
    return ReviewCommentEvidence(
        url=url,
        body=body,
        created_at=_require_iso8601(created_at, field="review comment createdAt"),
        author_login=login,
        author_association=association,
        original_commit_sha=original_sha,
    )


def _parse_review_comments_connection(
    connection: Any,
) -> tuple[list[ReviewCommentEvidence], bool, str | None]:
    if not isinstance(connection, dict):
        raise CommitIdentityError("review comments connection is missing")
    nodes = connection.get("nodes")
    page_info = connection.get("pageInfo")
    if not isinstance(nodes, list) or not isinstance(page_info, dict):
        raise CommitIdentityError("review comments connection has invalid shape")
    comments = [_parse_review_comment_node(node) for node in nodes]
    has_next = page_info.get("hasNextPage")
    end_cursor = page_info.get("endCursor")
    if not isinstance(has_next, bool) or (
        end_cursor is not None and not isinstance(end_cursor, str)
    ):
        raise CommitIdentityError("review comments pageInfo is malformed")
    return comments, has_next, end_cursor


def _fetch_remaining_review_comments(
    thread_id: str,
    initial_comments: list[ReviewCommentEvidence],
    initial_cursor: str | None,
    *,
    token: str,
    request_json: ApiRequest,
) -> list[ReviewCommentEvidence]:
    query = """
    query($id: ID!, $cursor: String!) {
      node(id: $id) {
        ... on PullRequestReviewThread {
          comments(first: 100, after: $cursor) {
            nodes {
              url body createdAt authorAssociation
              author { login }
              originalCommit { oid }
            }
            pageInfo { hasNextPage endCursor }
          }
        }
      }
    }
    """
    comments = list(initial_comments)
    cursor = initial_cursor
    seen_cursors: set[str] = set()
    for _page in range(_MAX_REVIEW_COMMENT_PAGES):
        if not cursor or cursor in seen_cursors:
            raise CommitIdentityError("review comment pagination cursor is missing or repeated")
        seen_cursors.add(cursor)
        response = request_json(
            f"{_API_ROOT}/graphql",
            token=token,
            method="POST",
            payload={"query": query, "variables": {"id": thread_id, "cursor": cursor}},
        )
        data = _require_graphql_object(response)
        node = data.get("node")
        if not isinstance(node, dict):
            raise CommitIdentityError("review thread disappeared during comment pagination")
        page_comments, has_next, end_cursor = _parse_review_comments_connection(
            node.get("comments")
        )
        comments.extend(page_comments)
        if len(comments) > _MAX_REVIEW_COMMENTS:
            raise CommitIdentityError("review thread comments exceed safety limit")
        if not has_next:
            return comments
        if not end_cursor or end_cursor == cursor:
            raise CommitIdentityError("review comment pagination cursor is missing or repeated")
        cursor = end_cursor
    raise CommitIdentityError("review comment pagination exceeded page limit")


def fetch_review_threads(
    repository: str,
    pr_number: int,
    *,
    token: str,
    request_json: ApiRequest = github_api_request,
) -> tuple[ReviewThreadEvidence, ...]:
    """Fetch every review thread and every comment with strict pagination."""

    owner, name = _require_repository(repository)
    if pr_number <= 0:
        raise CommitIdentityError("pr_number must be positive")
    query = """
    query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $number) {
          reviewThreads(first: 100, after: $cursor) {
            nodes {
              id isResolved
              comments(first: 100) {
                nodes {
                  url body createdAt authorAssociation
                  author { login }
                  originalCommit { oid }
                }
                pageInfo { hasNextPage endCursor }
              }
            }
            pageInfo { hasNextPage endCursor }
          }
        }
      }
    }
    """
    cursor: str | None = None
    seen_cursors: set[str] = set()
    threads: list[ReviewThreadEvidence] = []
    for _page in range(_MAX_REVIEW_THREAD_PAGES):
        response = request_json(
            f"{_API_ROOT}/graphql",
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
        data = _require_graphql_object(response)
        repository_node = data.get("repository")
        pull_request = (
            repository_node.get("pullRequest") if isinstance(repository_node, dict) else None
        )
        connection = pull_request.get("reviewThreads") if isinstance(pull_request, dict) else None
        if not isinstance(connection, dict):
            raise CommitIdentityError("GitHub GraphQL response is missing reviewThreads")
        nodes = connection.get("nodes")
        page_info = connection.get("pageInfo")
        if not isinstance(nodes, list) or not isinstance(page_info, dict):
            raise CommitIdentityError("reviewThreads connection has invalid shape")
        for node in nodes:
            if not isinstance(node, dict):
                raise CommitIdentityError("reviewThreads connection contains malformed node")
            thread_id = node.get("id")
            is_resolved = node.get("isResolved")
            if not isinstance(thread_id, str) or not thread_id or not isinstance(is_resolved, bool):
                raise CommitIdentityError("review thread identity is malformed")
            comments, has_more_comments, comment_cursor = _parse_review_comments_connection(
                node.get("comments")
            )
            if has_more_comments:
                comments = _fetch_remaining_review_comments(
                    thread_id,
                    comments,
                    comment_cursor,
                    token=token,
                    request_json=request_json,
                )
            if not comments:
                raise CommitIdentityError("review thread contains no comments")
            if len({comment.url for comment in comments}) != len(comments):
                raise CommitIdentityError("review thread contains duplicate comment URLs")
            threads.append(
                ReviewThreadEvidence(
                    node_id=thread_id,
                    is_resolved=is_resolved,
                    comments=tuple(comments),
                )
            )
            if len(threads) > _MAX_REVIEW_THREADS:
                raise CommitIdentityError("review threads exceed safety limit")
        has_next = page_info.get("hasNextPage")
        end_cursor = page_info.get("endCursor")
        if not isinstance(has_next, bool) or (
            end_cursor is not None and not isinstance(end_cursor, str)
        ):
            raise CommitIdentityError("reviewThreads pageInfo is malformed")
        if not has_next:
            break
        if not end_cursor or end_cursor == cursor or end_cursor in seen_cursors:
            raise CommitIdentityError("review thread pagination cursor is missing or repeated")
        seen_cursors.add(end_cursor)
        cursor = end_cursor
    else:
        raise CommitIdentityError("review thread pagination exceeded page limit")
    if len({thread.node_id for thread in threads}) != len(threads):
        raise CommitIdentityError("reviewThreads connection contains duplicate thread IDs")
    return tuple(threads)
