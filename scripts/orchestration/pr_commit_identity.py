"""Fail-closed GitHub identity proof for pull-request commits.

Review-provider execution references are deliberately represented by a
different type from repository-addressable commits.  Callers can therefore
perform ancestry checks only after GitHub has proved that both endpoints are
real commits in the live pull-request snapshot.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Mapping

from scripts.orchestration.review_source_status import (
    classify_codex_review_source_unavailability_body,
)

_API_HOST = "api.github.com"
_API_ROOT = f"https://{_API_HOST}"
_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_MAX_PR_COMMIT_PAGES = 100
_MAX_PR_COMMITS = 10_000
_MAX_PR_REACTION_PAGES = 100
_MAX_PR_REACTIONS = 10_000
_MAX_REVIEW_THREAD_PAGES = 100
_MAX_REVIEW_COMMENT_PAGES = 100
_MAX_REVIEW_THREADS = 10_000
_MAX_REVIEW_COMMENTS = 10_000
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_ISO_8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
_CODEX_CONNECTOR_LOGIN = "chatgpt-codex-connector[bot]"
_CODEX_CONNECTOR_USER_ID = 199_175_422
_CODEX_CONNECTOR_APP_ID = 1_144_995
_CODEX_CONNECTOR_APP_SLUG = "chatgpt-codex-connector"
_CODEX_CONNECTOR_OWNER = "openai"
_CODEX_REVIEWED_COMMIT_RE = re.compile(r"^\*\*Reviewed commit:\*\* `(?P<commit>[0-9a-f]{10})`$")
_CODEX_NO_FINDINGS_SUMMARY_PREFIX = "Codex Review: Didn't find any major issues."
_CODEX_NO_FINDINGS_DETAILS = """<details> <summary>ℹ️ About Codex in GitHub</summary>
<br/>

[Your team has set up Codex to review pull requests in this repo](https://chatgpt.com/codex/cloud/settings/general). Reviews are triggered when you
- Open a pull request for review
- Mark a draft as ready
- Comment "@codex review".

If Codex has suggestions, it will comment; otherwise it will react with 👍.



Codex can also answer questions or update the PR. Try commenting "@codex address that feedback".
</details>"""
_MATERIAL_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CODEX_SECURITY_OUTAGE_CLASS = "codex_security_mcp_timeout"
_CODEX_SECURITY_OUTAGE_CODE = "-32001"
_CODEX_SECURITY_OUTAGE_MESSAGE = "Request timed out"
_CODEX_SECURITY_OUTAGE_STATUS = "TOOLING_UNAVAILABLE"
_CODEX_SECURITY_OUTAGE_TTL = timedelta(hours=24)
_CODEX_SECURITY_OUTAGE_CLOCK_SKEW = timedelta(minutes=5)
_CODEX_REVIEW_CREDIT_OUTAGE_TTL = timedelta(hours=24)
_CODEX_REVIEW_CREDIT_OUTAGE_CLOCK_SKEW = timedelta(minutes=5)
_OPERATOR_EXACT_HEAD_REVIEW_PREFIX = "Exact-head bounded review completed for"
_CODEX_REVIEW_CREDIT_OUTAGE_CLASS = "codex_review_credits_exhausted"
_CODEX_REVIEW_CREDIT_OUTAGE_STATUS = "TOOLING_UNAVAILABLE"
_CODEX_POSITIVE_REACTION_CONTENTS = frozenset({"+1", "heart", "hooray", "rocket"})


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


@dataclass
class _ReviewCommentBudget:
    """One shared nested-pagination and retained-comment budget per PR fetch."""

    remaining_pages: int
    remaining_comments: int

    def consume_page(self) -> None:
        if self.remaining_pages <= 0:
            raise CommitIdentityError("review comment pagination exceeded global page limit")
        self.remaining_pages -= 1

    def retain_comments(self, count: int) -> None:
        if count < 0 or count > self.remaining_comments:
            raise CommitIdentityError("review comments exceed global safety limit")
        self.remaining_comments -= count


@dataclass(frozen=True)
class CodexReviewEvidence:
    """Trusted submitted review metadata; commit_ref still needs graph proof."""

    reference: str
    submitted_at: str
    commit_ref: str


@dataclass(frozen=True)
class CodexConnectorAdvisoryReactionEvidence:
    """Verified Connector reaction that intentionally carries no review claim."""

    reference: str
    created_at: str
    content: str


@dataclass(frozen=True)
class CodexReviewSourceUnavailabilityEvidence:
    """Immutable trusted Codex evidence that the review source was unavailable."""

    reference: str
    created_at: str
    source_status: str
    body_sha256: str


@dataclass(frozen=True)
class SecurityOutageOverrideEvidence:
    """Authenticated, exact-material operator evidence for a bounded MCP outage."""

    reference: str
    created_at: str
    operator_user_id: int
    operator_login: str
    operator_association: str
    material_head_sha: str
    material_digest: str


@dataclass(frozen=True)
class ReviewCreditOutageEvidence:
    """Trusted quota response plus an exact-head operator review."""

    override_reference: str
    override_created_at: str
    quota_reference: str
    quota_created_at: str
    prior_review_reference: str
    prior_review_submitted_at: str
    prior_review_commit_ref: str
    operator_review_reference: str
    operator_review_submitted_at: str
    operator_user_id: int
    operator_login: str
    operator_association: str
    material_head_sha: str
    material_digest: str


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


def _require_material_digest(value: str) -> str:
    normalized = value.strip()
    if not _MATERIAL_DIGEST_RE.fullmatch(normalized):
        raise CommitIdentityError("material digest must use sha256:<64 lowercase hex>")
    return normalized


def render_security_outage_override_comment(
    *, pr_number: int, material_head_sha: str, material_digest: str
) -> str:
    """Render the sole accepted operator-outage comment body."""

    if pr_number <= 0:
        raise CommitIdentityError("pr_number must be positive")
    head = _require_sha(material_head_sha, field="operator override material head")
    digest = _require_material_digest(material_digest)
    return "\n".join(
        (
            "PulsePlate Codex Security operator outage override v1",
            "",
            f"Status: {_CODEX_SECURITY_OUTAGE_STATUS}",
            f"Outage-Class: {_CODEX_SECURITY_OUTAGE_CLASS}",
            f"MCP-Error-Code: {_CODEX_SECURITY_OUTAGE_CODE}",
            f"MCP-Error-Message: {_CODEX_SECURITY_OUTAGE_MESSAGE}",
            "Scan-ID: none",
            f"PR: #{pr_number}",
            f"Material-Head: {head}",
            f"Material-Digest: {digest}",
            (
                "Attestation: This operator override records tool unavailability; "
                "it is not a security scan or a no-findings claim."
            ),
        )
    )


def render_review_credit_outage_override_comment(
    *,
    pr_number: int,
    material_head_sha: str,
    material_digest: str,
    quota_reference: str,
    prior_review_reference: str,
    operator_review_reference: str,
) -> str:
    """Render the sole accepted code-review credit-outage operator comment."""

    if pr_number <= 0:
        raise CommitIdentityError("pr_number must be positive")
    head = _require_sha(material_head_sha, field="review credit outage material head")
    digest = _require_material_digest(material_digest)
    references = (quota_reference, prior_review_reference, operator_review_reference)
    if any(
        not isinstance(reference, str)
        or not 1 <= len(reference) <= 500
        or "\n" in reference
        or "\r" in reference
        for reference in references
    ):
        raise CommitIdentityError("review credit outage references must be bounded lines")
    return "\n".join(
        (
            "PulsePlate Codex review credit exhaustion override v1",
            "",
            f"Status: {_CODEX_REVIEW_CREDIT_OUTAGE_STATUS}",
            f"Outage-Class: {_CODEX_REVIEW_CREDIT_OUTAGE_CLASS}",
            f"PR: #{pr_number}",
            f"Material-Head: {head}",
            f"Material-Digest: {digest}",
            f"Quota-Reference: {quota_reference}",
            f"Prior-Codex-Review: {prior_review_reference}",
            f"Operator-Exact-Head-Review: {operator_review_reference}",
            (
                "Attestation: This operator override records exhausted review credits; "
                "it is not a Codex review or a no-findings claim."
            ),
        )
    )


def verify_security_outage_override_reference(
    reference: str,
    *,
    repository: str,
    pr_number: int,
    token: str,
    expected_material_head_sha: str,
    expected_material_digest: str,
    now: datetime | None = None,
    request_json: ApiRequest = github_api_request,
) -> SecurityOutageOverrideEvidence:
    """Verify one short-lived, unedited GitHub operator outage override."""

    owner, name = _require_repository(repository)
    if pr_number <= 0:
        raise CommitIdentityError("pr_number must be positive")
    expected_head = _require_sha(
        expected_material_head_sha, field="operator override material head"
    )
    expected_digest = _require_material_digest(expected_material_digest)
    pattern = re.compile(
        rf"^https://github\.com/{re.escape(owner)}/{re.escape(name)}/pull/"
        rf"{pr_number}#issuecomment-(\d+)$"
    )
    match = pattern.fullmatch(reference)
    if not match:
        raise CommitIdentityError(
            "security outage override must be a GitHub issue comment on the exact PR"
        )

    response = request_json(
        f"{_API_ROOT}/repos/{owner}/{name}/issues/comments/{match.group(1)}",
        token=token,
    )
    if not isinstance(response, dict):
        raise CommitIdentityError("GitHub operator comment response is malformed")
    user = response.get("user")
    user_id = user.get("id") if isinstance(user, dict) else None
    login = user.get("login") if isinstance(user, dict) else None
    user_type = user.get("type") if isinstance(user, dict) else None
    association = response.get("author_association")
    expected_issue_url = f"{_API_ROOT}/repos/{owner}/{name}/issues/{pr_number}"
    if (
        not isinstance(login, str)
        or not login
        or not isinstance(user_id, int)
        or isinstance(user_id, bool)
        or user_id <= 0
        or user_type != "User"
        or association not in {"OWNER", "MEMBER"}
        or "performed_via_github_app" not in response
        or response.get("performed_via_github_app") is not None
        or response.get("html_url") != reference
        or response.get("issue_url") != expected_issue_url
    ):
        raise CommitIdentityError("issue comment is not trusted operator outage evidence")

    created_at = _require_iso8601(response.get("created_at"), field="operator override created_at")
    updated_at = _require_iso8601(response.get("updated_at"), field="operator override updated_at")
    if created_at != updated_at:
        raise CommitIdentityError("operator outage override was edited after creation")
    body = response.get("body")
    expected_body = render_security_outage_override_comment(
        pr_number=pr_number,
        material_head_sha=expected_head,
        material_digest=expected_digest,
    )
    if not isinstance(body, str) or "\r" in body or body != expected_body:
        raise CommitIdentityError(
            "operator outage override body does not exactly match the expected material"
        )

    created = datetime.fromisoformat(
        created_at[:-1] + "+00:00" if created_at.endswith("Z") else created_at
    )
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise CommitIdentityError("operator override validation time must include a timezone")
    if created > current + _CODEX_SECURITY_OUTAGE_CLOCK_SKEW:
        raise CommitIdentityError("operator outage override timestamp is in the future")
    if current - created > _CODEX_SECURITY_OUTAGE_TTL:
        raise CommitIdentityError("operator outage override has expired")

    return SecurityOutageOverrideEvidence(
        reference=reference,
        created_at=created_at,
        operator_user_id=user_id,
        operator_login=login,
        operator_association=association,
        material_head_sha=expected_head,
        material_digest=expected_digest,
    )


def _trusted_codex_app_comment(
    response: Any,
    *,
    reference: str,
    expected_issue_url: str,
) -> tuple[str, str, str]:
    """Validate immutable connector identity and return body plus timestamps."""

    if not isinstance(response, dict):
        raise CommitIdentityError("GitHub issue-comment response is malformed")
    user = response.get("user")
    login = user.get("login") if isinstance(user, dict) else None
    user_type = user.get("type") if isinstance(user, dict) else None
    app = response.get("performed_via_github_app")
    app_owner = app.get("owner") if isinstance(app, dict) else None
    app_owner_login = app_owner.get("login") if isinstance(app_owner, dict) else None
    if (
        login != _CODEX_CONNECTOR_LOGIN
        or user_type != "Bot"
        or not isinstance(app, dict)
        or app.get("id") != _CODEX_CONNECTOR_APP_ID
        or app.get("slug") != _CODEX_CONNECTOR_APP_SLUG
        or app_owner_login != _CODEX_CONNECTOR_OWNER
        or response.get("html_url") != reference
        or response.get("issue_url") != expected_issue_url
    ):
        raise CommitIdentityError("issue-comment reference is not trusted Codex evidence")
    created_at = _require_iso8601(response.get("created_at"), field="Codex comment created_at")
    updated_at = _require_iso8601(response.get("updated_at"), field="Codex comment updated_at")
    if created_at != updated_at:
        raise CommitIdentityError("Codex issue comment was edited after creation")
    body = response.get("body")
    if not isinstance(body, str) or "\r" in body:
        raise CommitIdentityError("Codex issue-comment body is malformed")
    return body, created_at, updated_at


def verify_codex_review_source_unavailability_reference(
    reference: str,
    *,
    repository: str,
    pr_number: int,
    token: str,
    request_json: ApiRequest = github_api_request,
) -> CodexReviewSourceUnavailabilityEvidence:
    """Prove one immutable same-PR trusted Codex quota response.

    The evidence proves only that the configured review source was unavailable
    at the recorded attempt. It does not claim a review or no-findings result.
    """

    owner, name = _require_repository(repository)
    if pr_number <= 0:
        raise CommitIdentityError("pr_number must be positive")
    pattern = re.compile(
        rf"^https://github\.com/{re.escape(owner)}/{re.escape(name)}/pull/"
        rf"{pr_number}#issuecomment-(\d+)$"
    )
    match = pattern.fullmatch(reference)
    if not match:
        raise CommitIdentityError(
            "review-source unavailability evidence must be a GitHub issue comment "
            "on the exact PR"
        )
    response = request_json(
        f"{_API_ROOT}/repos/{owner}/{name}/issues/comments/{match.group(1)}",
        token=token,
    )
    if not isinstance(response, dict) or response.get("id") != int(match.group(1)):
        raise CommitIdentityError(
            "review-source unavailability comment id does not match its canonical URL"
        )
    body, created_at, _updated_at = _trusted_codex_app_comment(
        response,
        reference=reference,
        expected_issue_url=f"{_API_ROOT}/repos/{owner}/{name}/issues/{pr_number}",
    )
    try:
        source_status = classify_codex_review_source_unavailability_body(body)
    except ValueError as exc:
        raise CommitIdentityError(str(exc)) from exc
    return CodexReviewSourceUnavailabilityEvidence(
        reference=reference,
        created_at=created_at,
        source_status=source_status,
        body_sha256="sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest(),
    )


def verify_review_credit_outage_references(
    *,
    override_reference: str,
    quota_reference: str,
    prior_review_reference: str,
    operator_review_reference: str,
    repository: str,
    pr_number: int,
    token: str,
    snapshot: PrSnapshot,
    expected_material_head_sha: str,
    expected_material_digest: str,
    now: datetime | None = None,
    request_json: ApiRequest = github_api_request,
) -> ReviewCreditOutageEvidence:
    """Prove one bounded credit-exhaustion fallback without claiming Codex review."""

    owner, name = _require_repository(repository)
    if (
        snapshot.repository.casefold() != repository.casefold()
        or snapshot.pr_number != pr_number
        or pr_number <= 0
    ):
        raise CommitIdentityError("review credit outage snapshot identity mismatch")
    material_head = _require_sha(
        expected_material_head_sha,
        field="review credit outage material head",
    )
    if material_head not in snapshot.commit_shas:
        raise CommitIdentityError(
            "review credit outage material head is absent from the PR commit graph"
        )
    material_digest = _require_material_digest(expected_material_digest)
    quota_pattern = re.compile(
        rf"^https://github\.com/{re.escape(owner)}/{re.escape(name)}/pull/"
        rf"{pr_number}#issuecomment-(\d+)$"
    )
    quota_match = quota_pattern.fullmatch(quota_reference)
    if not quota_match:
        raise CommitIdentityError(
            "review credit outage evidence must be a GitHub issue comment on the exact PR"
        )
    quota_response = request_json(
        f"{_API_ROOT}/repos/{owner}/{name}/issues/comments/{quota_match.group(1)}",
        token=token,
    )
    quota_body, quota_created_at, _quota_updated_at = _trusted_codex_app_comment(
        quota_response,
        reference=quota_reference,
        expected_issue_url=f"{_API_ROOT}/repos/{owner}/{name}/issues/{pr_number}",
    )
    try:
        classify_codex_review_source_unavailability_body(quota_body)
    except ValueError as exc:
        raise CommitIdentityError(
            "Codex comment is not an exact review-credit outage response"
        ) from exc

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise CommitIdentityError("review credit outage validation time must include a timezone")
    quota_created = datetime.fromisoformat(
        quota_created_at[:-1] + "+00:00" if quota_created_at.endswith("Z") else quota_created_at
    )
    if quota_created > current + _CODEX_REVIEW_CREDIT_OUTAGE_CLOCK_SKEW:
        raise CommitIdentityError("review credit outage timestamp is in the future")
    if current - quota_created > _CODEX_REVIEW_CREDIT_OUTAGE_TTL:
        raise CommitIdentityError("review credit outage evidence has expired")

    prior_review = verify_codex_review_reference(
        prior_review_reference,
        repository=repository,
        pr_number=pr_number,
        token=token,
        request_json=request_json,
    )
    prior_commit = classify_commit_ref(
        prior_review.commit_ref,
        snapshot,
        token=token,
        request_json=request_json,
    )
    if (
        not isinstance(prior_commit, RepositoryCommitRef)
        or prior_commit.kind is not CommitRefKind.PR_COMMIT
        or not is_ancestor(
            prior_commit,
            RepositoryCommitRef(
                material_head,
                (
                    CommitRefKind.PR_HEAD
                    if material_head == snapshot.head_sha
                    else CommitRefKind.PR_COMMIT
                ),
            ),
            repository=repository,
            token=token,
            request_json=request_json,
        )
    ):
        raise CommitIdentityError(
            "review credit outage requires a trusted Codex review on an ancestor PR commit"
        )
    prior_submitted = datetime.fromisoformat(
        prior_review.submitted_at[:-1] + "+00:00"
        if prior_review.submitted_at.endswith("Z")
        else prior_review.submitted_at
    )
    if prior_submitted > quota_created:
        raise CommitIdentityError("trusted prior Codex review postdates the quota response")

    review_pattern = re.compile(
        rf"^https://github\.com/{re.escape(owner)}/{re.escape(name)}/pull/"
        rf"{pr_number}#pullrequestreview-(\d+)$"
    )
    review_match = review_pattern.fullmatch(operator_review_reference)
    if not review_match:
        raise CommitIdentityError("operator fallback must be a GitHub review on the exact PR")
    operator_response = request_json(
        f"{_API_ROOT}/repos/{owner}/{name}/pulls/{pr_number}/reviews/" f"{review_match.group(1)}",
        token=token,
    )
    if not isinstance(operator_response, dict):
        raise CommitIdentityError("GitHub operator review response is malformed")
    user = operator_response.get("user")
    operator_user_id = user.get("id") if isinstance(user, dict) else None
    operator_login = user.get("login") if isinstance(user, dict) else None
    operator_type = user.get("type") if isinstance(user, dict) else None
    operator_association = operator_response.get("author_association")
    operator_submitted_at = _require_iso8601(
        operator_response.get("submitted_at"),
        field="operator exact-head review submitted_at",
    )
    operator_commit = _require_sha(
        str(operator_response.get("commit_id") or ""),
        field="operator exact-head review commit_id",
    )
    operator_body = operator_response.get("body")
    expected_body = (
        f"{_OPERATOR_EXACT_HEAD_REVIEW_PREFIX} `{material_head}`. " "No actionable findings remain."
    )
    if (
        not isinstance(operator_user_id, int)
        or isinstance(operator_user_id, bool)
        or operator_user_id <= 0
        or not isinstance(operator_login, str)
        or not operator_login
        or operator_type != "User"
        or operator_association not in {"OWNER", "MEMBER"}
        or operator_response.get("state") not in {"COMMENTED", "APPROVED"}
        or operator_response.get("html_url") != operator_review_reference
        or operator_commit != material_head
        or not isinstance(operator_body, str)
        or "\r" in operator_body
        or operator_body != expected_body
    ):
        raise CommitIdentityError(
            "operator review is not trusted exact-head credit-outage evidence"
        )
    operator_submitted = datetime.fromisoformat(
        operator_submitted_at[:-1] + "+00:00"
        if operator_submitted_at.endswith("Z")
        else operator_submitted_at
    )
    if operator_submitted < quota_created:
        raise CommitIdentityError("operator exact-head review predates the quota response")

    override_pattern = re.compile(
        rf"^https://github\.com/{re.escape(owner)}/{re.escape(name)}/pull/"
        rf"{pr_number}#issuecomment-(\d+)$"
    )
    override_match = override_pattern.fullmatch(override_reference)
    if not override_match:
        raise CommitIdentityError(
            "review credit outage override must be a GitHub issue comment on the exact PR"
        )
    override_response = request_json(
        f"{_API_ROOT}/repos/{owner}/{name}/issues/comments/{override_match.group(1)}",
        token=token,
    )
    if not isinstance(override_response, dict):
        raise CommitIdentityError("GitHub review credit override response is malformed")
    override_user = override_response.get("user")
    override_user_id = override_user.get("id") if isinstance(override_user, dict) else None
    override_login = override_user.get("login") if isinstance(override_user, dict) else None
    override_type = override_user.get("type") if isinstance(override_user, dict) else None
    override_association = override_response.get("author_association")
    expected_issue_url = f"{_API_ROOT}/repos/{owner}/{name}/issues/{pr_number}"
    if (
        not isinstance(override_user_id, int)
        or isinstance(override_user_id, bool)
        or override_user_id <= 0
        or not isinstance(override_login, str)
        or not override_login
        or override_type != "User"
        or override_association not in {"OWNER", "MEMBER"}
        or override_user_id != operator_user_id
        or override_login != operator_login
        or "performed_via_github_app" not in override_response
        or override_response.get("performed_via_github_app") is not None
        or override_response.get("html_url") != override_reference
        or override_response.get("issue_url") != expected_issue_url
    ):
        raise CommitIdentityError("issue comment is not trusted review credit outage evidence")
    override_created_at = _require_iso8601(
        override_response.get("created_at"),
        field="review credit outage override created_at",
    )
    override_updated_at = _require_iso8601(
        override_response.get("updated_at"),
        field="review credit outage override updated_at",
    )
    if override_created_at != override_updated_at:
        raise CommitIdentityError("review credit outage override was edited after creation")
    expected_override_body = render_review_credit_outage_override_comment(
        pr_number=pr_number,
        material_head_sha=material_head,
        material_digest=material_digest,
        quota_reference=quota_reference,
        prior_review_reference=prior_review_reference,
        operator_review_reference=operator_review_reference,
    )
    if (
        not isinstance(override_response.get("body"), str)
        or "\r" in override_response["body"]
        or override_response["body"] != expected_override_body
    ):
        raise CommitIdentityError(
            "review credit outage override body does not match the expected material"
        )
    override_created = datetime.fromisoformat(
        override_created_at[:-1] + "+00:00"
        if override_created_at.endswith("Z")
        else override_created_at
    )
    if override_created > current + _CODEX_REVIEW_CREDIT_OUTAGE_CLOCK_SKEW:
        raise CommitIdentityError("review credit outage override timestamp is in the future")
    if current - override_created > _CODEX_REVIEW_CREDIT_OUTAGE_TTL:
        raise CommitIdentityError("review credit outage override has expired")
    if override_created < operator_submitted:
        raise CommitIdentityError(
            "review credit outage override predates the exact-head operator review"
        )

    return ReviewCreditOutageEvidence(
        override_reference=override_reference,
        override_created_at=override_created_at,
        quota_reference=quota_reference,
        quota_created_at=quota_created_at,
        prior_review_reference=prior_review.reference,
        prior_review_submitted_at=prior_review.submitted_at,
        prior_review_commit_ref=prior_review.commit_ref,
        operator_review_reference=operator_review_reference,
        operator_review_submitted_at=operator_submitted_at,
        operator_user_id=override_user_id,
        operator_login=override_login,
        operator_association=override_association,
        material_head_sha=material_head,
        material_digest=material_digest,
    )


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


def _normalize_codex_comment_details(value: str) -> str:
    """Ignore connector-only whitespace while preserving exact nonblank content."""

    normalized: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.rstrip(" \t")
        if line:
            normalized.append(line)
    return "\n".join(normalized)


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
    if ancestor.sha == descendant.sha:
        return True
    owner, name = _require_repository(repository)
    compare_url = (
        f"{_API_ROOT}/repos/{owner}/{name}/compare/"
        f"{urllib.parse.quote(ancestor.sha, safe='')}..."
        f"{urllib.parse.quote(descendant.sha, safe='')}"
    )

    def fetch_compare_page(page: int) -> dict[str, Any]:
        url = f"{compare_url}?per_page=1&page={page}"
        try:
            response = request_json(url, token=token)
        except GitHubHttpError as exc:
            raise CommitIdentityError(f"Compare API failed with HTTP {exc.status}") from exc
        if not isinstance(response, dict):
            raise CommitIdentityError("Compare API response is malformed")
        return response

    response = fetch_compare_page(1)
    status = response.get("status")
    ahead_by = response.get("ahead_by")
    behind_by = response.get("behind_by")
    base_commit = response.get("base_commit")
    merge_base_commit = response.get("merge_base_commit")
    if (
        not isinstance(base_commit, dict)
        or base_commit.get("sha") != ancestor.sha
        or not isinstance(ahead_by, int)
        or isinstance(ahead_by, bool)
        or not isinstance(behind_by, int)
        or isinstance(behind_by, bool)
    ):
        raise CommitIdentityError("Compare API response does not bind the requested commits")

    if status in {"behind", "diverged"}:
        return False
    if status != "ahead" or not 1 <= ahead_by <= _MAX_PR_COMMITS or behind_by != 0:
        raise CommitIdentityError("Compare API returned unknown ancestry status")
    if not isinstance(merge_base_commit, dict) or merge_base_commit.get("sha") != ancestor.sha:
        raise CommitIdentityError("Compare API response does not bind the requested commits")

    last_page = response if ahead_by == 1 else fetch_compare_page(ahead_by)
    if ahead_by > 1 and (
        last_page.get("status") != status
        or last_page.get("ahead_by") != ahead_by
        or last_page.get("behind_by") != behind_by
        or not isinstance(last_page.get("base_commit"), dict)
        or last_page["base_commit"].get("sha") != ancestor.sha
        or not isinstance(last_page.get("merge_base_commit"), dict)
        or last_page["merge_base_commit"].get("sha") != ancestor.sha
    ):
        raise CommitIdentityError("Compare API response changed while paginating")
    commits = last_page.get("commits")
    last_commit = commits[-1] if isinstance(commits, list) and commits else None
    if not isinstance(last_commit, dict) or last_commit.get("sha") != descendant.sha:
        raise CommitIdentityError("Compare API response does not bind the requested commits")
    return True


def verify_codex_connector_advisory_reaction_reference(
    reference: str,
    *,
    repository: str,
    pr_number: int,
    token: str,
    request_json: ApiRequest = github_api_request,
) -> CodexConnectorAdvisoryReactionEvidence:
    """Verify one official positive PR-root reaction as advisory evidence only.

    GitHub reactions do not name a reviewed commit or execution run.  This
    verifier therefore intentionally cannot bind a reaction to material and
    must never be used as a code-review or review-seal proof.
    """

    owner, name = _require_repository(repository)
    pattern = re.compile(
        rf"^https://github\.com/{re.escape(owner)}/{re.escape(name)}/pull/"
        rf"{pr_number}#reaction-([1-9]\d*)$"
    )
    match = pattern.fullmatch(reference)
    if not match:
        raise CommitIdentityError(
            "Codex positive reaction must be a canonical reaction URL on the exact PR"
        )
    reaction_id_text = match.group(1)
    reaction_id = int(reaction_id_text)
    if str(reaction_id) != reaction_id_text:
        raise CommitIdentityError("Codex positive reaction reference is not canonical")

    matches: list[dict[str, Any]] = []
    reaction_count = 0
    for page in range(1, _MAX_PR_REACTION_PAGES + 1):
        response = request_json(
            f"{_API_ROOT}/repos/{owner}/{name}/issues/{pr_number}/reactions"
            f"?per_page=100&page={page}",
            token=token,
        )
        if not isinstance(response, list) or len(response) > 100:
            raise CommitIdentityError("GitHub PR reactions response is malformed")
        reaction_count += len(response)
        if reaction_count > _MAX_PR_REACTIONS:
            raise CommitIdentityError("GitHub PR reactions exceed safety limit")
        for reaction in response:
            if not isinstance(reaction, dict):
                raise CommitIdentityError("GitHub PR reaction entry is malformed")
            candidate_id = reaction.get("id")
            if (
                not isinstance(candidate_id, int)
                or isinstance(candidate_id, bool)
                or candidate_id <= 0
            ):
                raise CommitIdentityError("GitHub PR reaction id is malformed")
            if candidate_id == reaction_id:
                matches.append(reaction)
        if len(response) < 100:
            break
    else:
        raise CommitIdentityError("GitHub PR reaction pagination exceeded page limit")

    if len(matches) != 1:
        raise CommitIdentityError("Codex positive reaction is missing or ambiguous")
    reaction = matches[0]
    user = reaction.get("user")
    user_id = user.get("id") if isinstance(user, dict) else None
    login = user.get("login") if isinstance(user, dict) else None
    user_type = user.get("type") if isinstance(user, dict) else None
    content = reaction.get("content")
    created_at = _require_iso8601(
        reaction.get("created_at"),
        field="Codex positive reaction created_at",
    )
    if (
        not isinstance(user_id, int)
        or isinstance(user_id, bool)
        or user_id != _CODEX_CONNECTOR_USER_ID
        or not isinstance(login, str)
        or login != _CODEX_CONNECTOR_LOGIN
        or not isinstance(user_type, str)
        or user_type not in {"Bot", "User"}
        or not isinstance(content, str)
        or content not in _CODEX_POSITIVE_REACTION_CONTENTS
    ):
        raise CommitIdentityError("reaction is not a trusted positive Codex connector reaction")
    return CodexConnectorAdvisoryReactionEvidence(
        reference=reference,
        created_at=created_at,
        content=content,
    )


def verify_codex_review_reference(
    reference: str,
    *,
    repository: str,
    pr_number: int,
    token: str,
    expected_commit_ref: str | None = None,
    request_json: ApiRequest = github_api_request,
) -> CodexReviewEvidence:
    """Prove that a seal reference names trusted exact-head Codex review evidence."""

    owner, name = _require_repository(repository)
    expected_commit = (
        _require_sha(expected_commit_ref, field="expected Codex review commit")
        if expected_commit_ref is not None
        else None
    )
    review_pattern = re.compile(
        rf"^https://github\.com/{re.escape(owner)}/{re.escape(name)}/pull/"
        rf"{pr_number}#pullrequestreview-(\d+)$"
    )
    review_match = review_pattern.fullmatch(reference)
    if review_match:
        review_id = review_match.group(1)
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
            login != _CODEX_CONNECTOR_LOGIN
            or state not in {"COMMENTED", "APPROVED"}
            or html_url != reference
        ):
            raise CommitIdentityError(
                "code-review reference is not a submitted trusted Codex review"
            )
        submitted = _require_iso8601(submitted_at, field="Codex review submitted_at")
        commit_ref = _require_sha(str(commit_id or ""), field="Codex review commit_id")
        if expected_commit is not None and commit_ref != expected_commit:
            raise CommitIdentityError("Codex review does not match the expected material commit")
        return CodexReviewEvidence(
            reference=reference,
            submitted_at=submitted,
            commit_ref=commit_ref,
        )

    reaction_pattern = re.compile(
        rf"^https://github\.com/{re.escape(owner)}/{re.escape(name)}/pull/"
        rf"{pr_number}#reaction-[1-9]\d*$"
    )
    if reaction_pattern.fullmatch(reference):
        raise CommitIdentityError(
            "positive Codex connector reactions are advisory only and cannot satisfy "
            "exact-head code-review evidence"
        )

    comment_pattern = re.compile(
        rf"^https://github\.com/{re.escape(owner)}/{re.escape(name)}/pull/"
        rf"{pr_number}#issuecomment-(\d+)$"
    )
    comment_match = comment_pattern.fullmatch(reference)
    if not comment_match:
        raise CommitIdentityError(
            "code-review reference must be a GitHub PR review or Codex no-findings comment URL"
        )
    if expected_commit is None:
        raise CommitIdentityError(
            "Codex no-findings comment requires an expected full material commit"
        )
    comment_id = comment_match.group(1)
    response = request_json(
        f"{_API_ROOT}/repos/{owner}/{name}/issues/comments/{comment_id}",
        token=token,
    )
    if not isinstance(response, dict):
        raise CommitIdentityError("GitHub issue-comment response is malformed")
    user = response.get("user")
    login = user.get("login") if isinstance(user, dict) else None
    user_type = user.get("type") if isinstance(user, dict) else None
    app = response.get("performed_via_github_app")
    app_owner = app.get("owner") if isinstance(app, dict) else None
    app_owner_login = app_owner.get("login") if isinstance(app_owner, dict) else None
    created_at = response.get("created_at")
    updated_at = response.get("updated_at")
    if (
        login != _CODEX_CONNECTOR_LOGIN
        or user_type != "Bot"
        or not isinstance(app, dict)
        or app.get("id") != _CODEX_CONNECTOR_APP_ID
        or app.get("slug") != _CODEX_CONNECTOR_APP_SLUG
        or app_owner_login != _CODEX_CONNECTOR_OWNER
        or response.get("html_url") != reference
    ):
        raise CommitIdentityError("issue-comment reference is not trusted Codex evidence")
    submitted = _require_iso8601(created_at, field="Codex comment created_at")
    edited_at = _require_iso8601(updated_at, field="Codex comment updated_at")
    if submitted != edited_at:
        raise CommitIdentityError("Codex no-findings comment was edited after creation")
    body = response.get("body")
    if not isinstance(body, str) or "\r" in body:
        raise CommitIdentityError("Codex no-findings comment body is malformed")
    sections = body.split("\n\n", 2)
    if (
        len(sections) != 3
        or "\n" in sections[0]
        or not sections[0].startswith(_CODEX_NO_FINDINGS_SUMMARY_PREFIX)
        or _normalize_codex_comment_details(sections[2])
        != _normalize_codex_comment_details(_CODEX_NO_FINDINGS_DETAILS)
    ):
        raise CommitIdentityError("issue-comment is not an exact Codex no-findings response")
    commit_matches = list(_CODEX_REVIEWED_COMMIT_RE.finditer(sections[1]))
    if len(commit_matches) != 1 or commit_matches[0].group(0) != sections[1]:
        raise CommitIdentityError("Codex no-findings comment has invalid commit evidence")
    reviewed_prefix = commit_matches[0].group("commit")
    if not expected_commit.startswith(reviewed_prefix):
        raise CommitIdentityError("Codex no-findings comment does not match the material commit")
    resolved_commit = request_json(
        f"{_API_ROOT}/repos/{owner}/{name}/commits/{reviewed_prefix}",
        token=token,
    )
    if not isinstance(resolved_commit, dict):
        raise CommitIdentityError("GitHub commit response is malformed")
    resolved_sha = _require_sha(
        str(resolved_commit.get("sha") or ""), field="resolved Codex review commit"
    )
    if resolved_sha != expected_commit:
        raise CommitIdentityError(
            "Codex no-findings commit marker does not resolve to the material commit"
        )
    return CodexReviewEvidence(
        reference=reference,
        submitted_at=submitted,
        commit_ref=expected_commit,
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
    budget: _ReviewCommentBudget,
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
    while True:
        if not cursor or cursor in seen_cursors:
            raise CommitIdentityError("review comment pagination cursor is missing or repeated")
        seen_cursors.add(cursor)
        budget.consume_page()
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
        budget.retain_comments(len(page_comments))
        comments.extend(page_comments)
        if not has_next:
            return comments
        if not end_cursor or end_cursor == cursor:
            raise CommitIdentityError("review comment pagination cursor is missing or repeated")
        cursor = end_cursor


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
    comment_budget = _ReviewCommentBudget(
        remaining_pages=_MAX_REVIEW_COMMENT_PAGES,
        remaining_comments=_MAX_REVIEW_COMMENTS,
    )
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
            comment_budget.retain_comments(len(comments))
            if has_more_comments:
                comments = _fetch_remaining_review_comments(
                    thread_id,
                    comments,
                    comment_cursor,
                    budget=comment_budget,
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
