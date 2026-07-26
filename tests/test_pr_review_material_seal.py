"""Focused fail-closed tests for real PR commits and material review seals."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest

from scripts.orchestration.pr_commit_identity import (
    CommitIdentityError,
    CommitRefKind,
    CodexReviewEvidence,
    CodexReviewSourceUnavailabilityEvidence,
    GitHubHttpError,
    PrCommitEvidence,
    PrSnapshot,
    ReviewCommentEvidence,
    RepositoryCommitRef,
    ReviewCreditOutageEvidence,
    ReviewExecutionRef,
    ReviewThreadEvidence,
    SecurityOutageOverrideEvidence,
    assert_snapshot_unchanged,
    classify_commit_ref,
    fetch_pr_snapshot,
    fetch_review_threads,
    is_ancestor,
    render_review_credit_outage_override_comment,
    render_security_outage_override_comment,
    verify_codex_connector_advisory_reaction_reference,
    verify_codex_review_reference,
    verify_codex_review_source_unavailability_reference,
    verify_review_credit_outage_references,
    verify_security_outage_override_reference,
)
from scripts.orchestration import pr_commit_identity as identity_module
from scripts.orchestration import pr_review_closeout as closeout_module
from scripts.orchestration import pr_review_evidence as evidence_module
from scripts.orchestration.pr_review_evidence import (
    ADVISORY_CAPABILITY_AUTHORIZING_PREFIXES,
    ADVISORY_CAPABILITY_AUTHORIZING_PATHS,
    MATERIAL_POLICY_VERSION,
    RECEIPT_AUTHORITY,
    SEAL_BEGIN,
    SEAL_END,
    MaterialManifest,
    ReviewEvidenceError,
    advisory_capability_marker_bytes,
    build_advisory_capability_receipts,
    build_review_credit_outage_receipt,
    build_review_source_positive_response_receipt,
    build_review_source_unavailability_receipt,
    build_security_outage_override_receipt,
    build_self_review_receipt,
    compute_material_manifest,
    ingest_codex_security_receipt,
    ingest_self_review_report,
    is_review_credit_outage_receipt,
    is_review_source_positive_response_receipt,
    is_review_source_unavailability_receipt,
    is_security_outage_override_receipt,
    parse_duplicate_disposition_reply,
    parse_embedded_review_seal,
    render_embedded_review_seal,
    self_review_report_content_digest,
    self_review_report_semantic_digest,
    unavailable_review_ref_fingerprint,
    validate_review_credit_outage_scope,
    validate_advisory_capability_activation,
    validate_advisory_live_head_topology,
    validate_security_outage_override_scope,
    validate_self_review_receipt,
    validated_duplicate_reply_urls,
)
from scripts.orchestration.review_mapping_artifact import (
    NO_ACTIONABLE_LINE,
    parse_canonical_fingerprint_records,
    validate_mapping_artifact_text,
)

BASE_SHA = "1" * 40
FIX_SHA = "2" * 40
HEAD_SHA = "3" * 40
OUTSIDE_SHA = "4" * 40
UNAVAILABLE_SHA = "5" * 40
DIGEST = "sha256:" + "a" * 64
SNAPSHOT_DIGEST = "codex-security-snapshot/v1:sha256:" + "b" * 64
SCAN_ID = "123e4567-e89b-42d3-a456-426614174000"


def _snapshot() -> PrSnapshot:
    return PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        commits=(
            PrCommitEvidence(FIX_SHA, "2026-07-15T10:00:00Z"),
            PrCommitEvidence(HEAD_SHA, "2026-07-15T11:00:00Z"),
        ),
    )


def _material_manifest(head_sha: str, *, digest: str = DIGEST) -> MaterialManifest:
    return MaterialManifest(
        base_ref_oid=BASE_SHA,
        head_ref_oid=head_sha,
        merge_base_sha=BASE_SHA,
        pr_number=42,
        entries=(),
        digest=digest,
    )


def _graphql_page(
    *,
    commits: list[tuple[str, str | None]],
    has_next: bool,
    cursor: str | None,
) -> dict[str, Any]:
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "baseRefOid": BASE_SHA,
                    "headRefOid": HEAD_SHA,
                    "commits": {
                        "nodes": [
                            {"commit": {"oid": sha, "pushedDate": pushed_at}}
                            for sha, pushed_at in commits
                        ],
                        "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                    },
                }
            }
        }
    }


def test_pr_snapshot_requires_complete_cursor_pagination() -> None:
    responses = iter(
        [
            _graphql_page(
                commits=[(FIX_SHA, "2026-07-15T10:00:00Z")],
                has_next=True,
                cursor="cursor-1",
            ),
            _graphql_page(
                commits=[(HEAD_SHA, "2026-07-15T11:00:00Z")],
                has_next=False,
                cursor=None,
            ),
        ]
    )

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return next(responses)

    snapshot = fetch_pr_snapshot("owner/repo", 42, token="opaque", request_json=request_json)

    assert snapshot.commit_shas == {FIX_SHA, HEAD_SHA}
    assert snapshot.base_sha == BASE_SHA
    assert snapshot.head_sha == HEAD_SHA


def test_pr_snapshot_fails_closed_for_missing_next_cursor() -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return _graphql_page(
            commits=[(HEAD_SHA, "2026-07-15T11:00:00Z")],
            has_next=True,
            cursor=None,
        )

    with pytest.raises(CommitIdentityError, match="cursor is missing or repeated"):
        fetch_pr_snapshot("owner/repo", 42, token="opaque", request_json=request_json)


@pytest.mark.parametrize("commit_count", [1, 100, 101, 251])
def test_pr_snapshot_covers_graphql_page_boundaries(commit_count: int) -> None:
    commit_shas = [f"{index:040x}" for index in range(1, commit_count)] + [HEAD_SHA]
    pages = [commit_shas[index : index + 100] for index in range(0, commit_count, 100)]
    requested_cursors: list[str | None] = []

    def request_json(*_args: Any, **kwargs: Any) -> Any:
        cursor = kwargs["payload"]["variables"]["cursor"]
        requested_cursors.append(cursor)
        page_index = len(requested_cursors) - 1
        expected_cursor = None if page_index == 0 else f"cursor-{page_index}"
        assert cursor == expected_cursor
        has_next = page_index + 1 < len(pages)
        end_cursor = f"cursor-{page_index + 1}" if has_next else None
        return _graphql_page(
            commits=[(sha, "2026-07-15T10:00:00Z") for sha in pages[page_index]],
            has_next=has_next,
            cursor=end_cursor,
        )

    snapshot = fetch_pr_snapshot("owner/repo", 42, token="opaque", request_json=request_json)

    assert len(snapshot.commits) == commit_count
    assert snapshot.commits[-1].sha == HEAD_SHA
    assert len(requested_cursors) == len(pages)


def test_pr_snapshot_rejects_empty_connection() -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return _graphql_page(commits=[], has_next=False, cursor=None)

    with pytest.raises(CommitIdentityError, match="connection is empty"):
        fetch_pr_snapshot("owner/repo", 42, token="opaque", request_json=request_json)


def test_pr_snapshot_rejects_repeated_non_adjacent_cursor() -> None:
    responses = iter(
        [
            _graphql_page(
                commits=[(FIX_SHA, "2026-07-15T10:00:00Z")],
                has_next=True,
                cursor="cursor-1",
            ),
            _graphql_page(
                commits=[(OUTSIDE_SHA, "2026-07-15T10:30:00Z")],
                has_next=True,
                cursor="cursor-2",
            ),
            _graphql_page(
                commits=[(HEAD_SHA, "2026-07-15T11:00:00Z")],
                has_next=True,
                cursor="cursor-1",
            ),
        ]
    )

    with pytest.raises(CommitIdentityError, match="cursor is missing or repeated"):
        fetch_pr_snapshot(
            "owner/repo",
            42,
            token="opaque",
            request_json=lambda *_args, **_kwargs: next(responses),
        )


def test_pr_snapshot_rejects_incomplete_terminal_set_without_head() -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return _graphql_page(
            commits=[(FIX_SHA, "2026-07-15T10:00:00Z")],
            has_next=False,
            cursor=None,
        )

    with pytest.raises(CommitIdentityError, match="live PR head is absent"):
        fetch_pr_snapshot("owner/repo", 42, token="opaque", request_json=request_json)


@pytest.mark.parametrize(
    ("sha", "expected_kind"),
    [
        (HEAD_SHA, CommitRefKind.PR_HEAD),
        (FIX_SHA, CommitRefKind.PR_COMMIT),
        (OUTSIDE_SHA, CommitRefKind.REPO_COMMIT_OUTSIDE_PR),
    ],
)
def test_commit_classification_requires_commit_api_existence(
    sha: str, expected_kind: CommitRefKind
) -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {"sha": sha}

    resolution = classify_commit_ref(sha, _snapshot(), token="opaque", request_json=request_json)

    assert isinstance(resolution, RepositoryCommitRef)
    assert resolution.kind is expected_kind


@pytest.mark.parametrize(
    "error",
    [
        GitHubHttpError(404, "Not Found"),
        GitHubHttpError(422, "Unprocessable Entity", "No commit found for SHA"),
    ],
)
def test_unavailable_review_ref_never_reaches_ancestry(error: GitHubHttpError) -> None:
    calls: list[str] = []

    def request_json(url: str, **_kwargs: Any) -> Any:
        calls.append(url)
        raise error

    resolution = classify_commit_ref(
        UNAVAILABLE_SHA,
        _snapshot(),
        token="opaque",
        request_json=request_json,
    )
    assert isinstance(resolution, ReviewExecutionRef)
    assert resolution.kind is CommitRefKind.REVIEW_REF_UNAVAILABLE

    with pytest.raises(TypeError, match="RepositoryCommitRef"):
        is_ancestor(
            cast(RepositoryCommitRef, resolution),
            RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD),
            repository="owner/repo",
            token="opaque",
            request_json=request_json,
        )
    assert len(calls) == 1


def test_api_outage_is_unknown_not_unavailable() -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        raise GitHubHttpError(503, "Service Unavailable")

    resolution = classify_commit_ref(
        UNAVAILABLE_SHA,
        _snapshot(),
        token="opaque",
        request_json=request_json,
    )

    assert isinstance(resolution, ReviewExecutionRef)
    assert resolution.kind is CommitRefKind.API_UNKNOWN


@pytest.mark.parametrize(
    "failure",
    [
        GitHubHttpError(403, "Forbidden"),
        GitHubHttpError(429, "Rate Limited"),
        GitHubHttpError(500, "Server Error"),
        TimeoutError(),
        CommitIdentityError("malformed response"),
    ],
)
def test_all_unproven_api_failures_remain_unknown(failure: Exception) -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        raise failure

    resolution = classify_commit_ref(
        UNAVAILABLE_SHA, _snapshot(), token="opaque", request_json=request_json
    )
    assert isinstance(resolution, ReviewExecutionRef)
    assert resolution.kind is CommitRefKind.API_UNKNOWN


def test_compare_rejects_conflicting_head_commit() -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "status": "ahead",
            "ahead_by": 1,
            "behind_by": 0,
            "base_commit": {"sha": FIX_SHA},
            "head_commit": {"sha": OUTSIDE_SHA},
            "merge_base_commit": {"sha": FIX_SHA},
            "commits": [{"sha": HEAD_SHA}],
            "total_commits": 1,
        }

    with pytest.raises(CommitIdentityError, match="does not bind"):
        is_ancestor(
            ancestor,
            descendant,
            repository="owner/repo",
            token="opaque",
            request_json=request_json,
        )


def test_compare_accepts_matching_head_commit() -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "status": "ahead",
            "ahead_by": 1,
            "behind_by": 0,
            "base_commit": {"sha": FIX_SHA},
            "head_commit": {"sha": HEAD_SHA},
            "merge_base_commit": {"sha": FIX_SHA},
            "commits": [{"sha": HEAD_SHA}],
            "total_commits": 1,
        }

    assert is_ancestor(
        ancestor,
        descendant,
        repository="owner/repo",
        token="opaque",
        request_json=request_json,
    )


def test_compare_accepts_current_api_shape_without_head_commit() -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "status": "ahead",
            "ahead_by": 1,
            "behind_by": 0,
            "base_commit": {"sha": FIX_SHA},
            "merge_base_commit": {"sha": FIX_SHA},
            "commits": [{"sha": HEAD_SHA}],
            "total_commits": 1,
        }

    assert is_ancestor(
        ancestor,
        descendant,
        repository="owner/repo",
        token="opaque",
        request_json=request_json,
    )


def test_compare_fetches_the_last_page_to_bind_a_distant_descendant() -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)
    requested_urls: list[str] = []

    def request_json(url: str, **_kwargs: Any) -> Any:
        requested_urls.append(url)
        commit_sha = HEAD_SHA if "page=257" in url else OUTSIDE_SHA
        return {
            "status": "ahead",
            "ahead_by": 257,
            "behind_by": 0,
            "base_commit": {"sha": FIX_SHA},
            "commits": [{"sha": commit_sha}],
            "merge_base_commit": {"sha": FIX_SHA},
            "total_commits": 257,
        }

    assert is_ancestor(
        ancestor,
        descendant,
        repository="owner/repo",
        token="opaque",
        request_json=request_json,
    )
    assert requested_urls == [
        (
            "https://api.github.com/repos/owner/repo/compare/"
            f"{FIX_SHA}...{HEAD_SHA}?per_page=1&page=1"
        ),
        (
            "https://api.github.com/repos/owner/repo/compare/"
            f"{FIX_SHA}...{HEAD_SHA}?per_page=1&page=257"
        ),
    ]


@pytest.mark.parametrize("head_commit", [None, {"sha": OUTSIDE_SHA}, {"sha": HEAD_SHA}])
def test_compare_rejects_unbound_descendant_even_with_head_commit(
    head_commit: Any,
) -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "status": "ahead",
            "ahead_by": 1,
            "behind_by": 0,
            "base_commit": {"sha": FIX_SHA},
            "head_commit": head_commit,
            "merge_base_commit": {"sha": FIX_SHA},
            "commits": [],
            "total_commits": 1,
        }

    with pytest.raises(CommitIdentityError, match="does not bind"):
        is_ancestor(
            ancestor,
            descendant,
            repository="owner/repo",
            token="opaque",
            request_json=request_json,
        )


def test_compare_fetches_terminal_page_for_truncated_commit_inventory() -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)
    calls: list[str] = []

    def request_json(url: str, **_kwargs: Any) -> Any:
        calls.append(url)
        commits = [{"sha": FIX_SHA}]
        if url.endswith("?per_page=1&page=2"):
            commits = [{"sha": HEAD_SHA}]
        return {
            "status": "ahead",
            "ahead_by": 2,
            "behind_by": 0,
            "base_commit": {"sha": FIX_SHA},
            "merge_base_commit": {"sha": FIX_SHA},
            "commits": commits,
            "total_commits": 2,
        }

    assert is_ancestor(
        ancestor,
        descendant,
        repository="owner/repo",
        token="opaque",
        request_json=request_json,
    )
    assert calls[-1].endswith("?per_page=1&page=2")


def test_compare_identical_requires_the_same_requested_sha() -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "status": "identical",
            "ahead_by": 0,
            "behind_by": 0,
            "base_commit": {"sha": FIX_SHA},
            "head_commit": {"sha": HEAD_SHA},
            "merge_base_commit": {"sha": FIX_SHA},
            "commits": [],
            "total_commits": 0,
        }

    with pytest.raises(CommitIdentityError, match="does not bind"):
        is_ancestor(
            ancestor,
            descendant,
            repository="owner/repo",
            token="opaque",
            request_json=request_json,
        )


def test_compare_identical_accepts_same_sha_without_head_commit() -> None:
    commit = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)
    requested_urls: list[str] = []

    def request_json(url: str, **_kwargs: Any) -> Any:
        requested_urls.append(url)
        return {
            "status": "identical",
            "ahead_by": 0,
            "behind_by": 0,
            "base_commit": {"sha": HEAD_SHA},
            "merge_base_commit": {"sha": HEAD_SHA},
            "commits": [],
            "total_commits": 0,
        }

    assert is_ancestor(
        commit,
        commit,
        repository="owner/repo",
        token="opaque",
        request_json=request_json,
    )
    assert requested_urls == [
        (
            "https://api.github.com/repos/owner/repo/compare/"
            f"{HEAD_SHA}...{HEAD_SHA}?per_page=1&page=1"
        )
    ]


def test_compare_identical_api_failure_remains_unproven() -> None:
    commit = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        raise GitHubHttpError(503, "Service Unavailable")

    with pytest.raises(CommitIdentityError, match="Compare API failed with HTTP 503"):
        is_ancestor(
            commit,
            commit,
            repository="owner/repo",
            token="opaque",
            request_json=request_json,
        )


@pytest.mark.parametrize(
    ("status", "merge_base_sha"),
    [("behind", HEAD_SHA), ("diverged", OUTSIDE_SHA)],
)
def test_compare_non_ancestor_statuses_return_false(status: str, merge_base_sha: str) -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "status": status,
            "ahead_by": 0,
            "behind_by": 1,
            "base_commit": {"sha": FIX_SHA},
            "merge_base_commit": {"sha": merge_base_sha},
            "commits": [],
            "total_commits": 0,
        }

    assert not is_ancestor(
        ancestor,
        descendant,
        repository="owner/repo",
        token="opaque",
        request_json=request_json,
    )


@pytest.mark.parametrize(
    ("commits", "total_commits", "ahead_by"),
    [
        (None, 1, 1),
        ([], 1, 1),
        ([{"sha": OUTSIDE_SHA}], 1, 1),
        ([{"sha": HEAD_SHA}], 1, 2),
        ("not-a-list", 1, 1),
    ],
)
def test_compare_rejects_incomplete_or_malformed_commit_inventory(
    commits: Any, total_commits: Any, ahead_by: Any
) -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "status": "ahead",
            "ahead_by": ahead_by,
            "behind_by": 0,
            "base_commit": {"sha": FIX_SHA},
            "merge_base_commit": {"sha": FIX_SHA},
            "commits": commits,
            "total_commits": total_commits,
        }

    with pytest.raises(CommitIdentityError, match="does not bind"):
        is_ancestor(
            ancestor,
            descendant,
            repository="owner/repo",
            token="opaque",
            request_json=request_json,
        )


@pytest.mark.parametrize(("ahead_by", "behind_by"), [(True, 0), (-1, 0), (0, -1)])
def test_compare_rejects_invalid_counters(ahead_by: Any, behind_by: Any) -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "status": "ahead",
            "ahead_by": ahead_by,
            "behind_by": behind_by,
            "base_commit": {"sha": FIX_SHA},
            "merge_base_commit": {"sha": FIX_SHA},
            "commits": [{"sha": HEAD_SHA}],
            "total_commits": 1,
        }

    with pytest.raises(CommitIdentityError, match="does not bind"):
        is_ancestor(
            ancestor,
            descendant,
            repository="owner/repo",
            token="opaque",
            request_json=request_json,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("head_commit", {"sha": OUTSIDE_SHA}),
        ("ahead_by", True),
        ("behind_by", False),
        ("total_commits", True),
    ],
)
def test_compare_rejects_invalid_terminal_page_binding(field: str, value: Any) -> None:
    ancestor = RepositoryCommitRef(FIX_SHA, CommitRefKind.PR_COMMIT)
    descendant = RepositoryCommitRef(HEAD_SHA, CommitRefKind.PR_HEAD)

    def request_json(url: str, **_kwargs: Any) -> Any:
        terminal = "page=2" in url
        response = {
            "status": "ahead",
            "ahead_by": 2,
            "behind_by": 0,
            "base_commit": {"sha": FIX_SHA},
            "head_commit": {"sha": HEAD_SHA},
            "merge_base_commit": {"sha": FIX_SHA},
            "commits": [{"sha": HEAD_SHA if terminal else OUTSIDE_SHA}],
            "total_commits": 2,
        }
        if terminal:
            response[field] = value
        return response

    with pytest.raises(CommitIdentityError, match="terminal page does not bind"):
        is_ancestor(
            ancestor,
            descendant,
            repository="owner/repo",
            token="opaque",
            request_json=request_json,
        )


def test_codex_review_reference_requires_exact_trusted_submitted_review() -> None:
    reference = "https://github.com/owner/repo/pull/42#pullrequestreview-123"

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "commit_id": HEAD_SHA,
            "html_url": reference,
            "state": "COMMENTED",
            "submitted_at": "2026-07-15T11:00:00Z",
            "user": {"login": "chatgpt-codex-connector[bot]"},
        }

    evidence = verify_codex_review_reference(
        reference,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        request_json=request_json,
    )
    assert evidence.commit_ref == HEAD_SHA

    with pytest.raises(CommitIdentityError, match="expected material commit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=OUTSIDE_SHA,
            request_json=request_json,
        )

    with pytest.raises(CommitIdentityError, match="submitted trusted Codex"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            request_json=lambda *_a, **_k: {
                "commit_id": HEAD_SHA,
                "html_url": reference,
                "state": "COMMENTED",
                "submitted_at": "2026-07-15T11:00:00Z",
                "user": {"login": "spoofed[bot]"},
            },
        )


def _codex_no_findings_body(
    commit_prefix: str = HEAD_SHA[:10],
    *,
    summary: str = "Codex Review: Didn't find any major issues. Breezy!",
) -> str:
    return f"""{summary}

**Reviewed commit:** `{commit_prefix}`

<details> <summary>ℹ️ About Codex in GitHub</summary>
<br/>

[Your team has set up Codex to review pull requests in this repo](https://chatgpt.com/codex/cloud/settings/general). Reviews are triggered when you
- Open a pull request for review
- Mark a draft as ready
- Comment "@codex review".

If Codex has suggestions, it will comment; otherwise it will react with 👍.



Codex can also answer questions or update the PR. Try commenting "@codex address that feedback".

</details>"""


def _codex_no_findings_comment(reference: str, *, body: str | None = None) -> dict[str, Any]:
    return {
        "body": _codex_no_findings_body() if body is None else body,
        "created_at": "2026-07-15T11:00:00Z",
        "html_url": reference,
        "performed_via_github_app": {
            "id": 1_144_995,
            "owner": {"login": "openai"},
            "slug": "chatgpt-codex-connector",
        },
        "updated_at": "2026-07-15T11:00:00Z",
        "user": {"login": "chatgpt-codex-connector[bot]", "type": "Bot"},
    }


def test_codex_no_findings_comment_is_bound_to_expected_full_head() -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    requested_urls: list[str] = []

    def request_json(url: str, **_kwargs: Any) -> Any:
        requested_urls.append(url)
        if url.endswith("/commits/" + HEAD_SHA[:10]):
            return {"sha": HEAD_SHA}
        return _codex_no_findings_comment(reference)

    evidence = verify_codex_review_reference(
        reference,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        expected_commit_ref=HEAD_SHA,
        request_json=request_json,
    )

    assert evidence.commit_ref == HEAD_SHA
    assert evidence.submitted_at == "2026-07-15T11:00:00Z"
    assert requested_urls == [
        "https://api.github.com/repos/owner/repo/issues/comments/456",
        f"https://api.github.com/repos/owner/repo/commits/{HEAD_SHA[:10]}",
    ]


@pytest.mark.parametrize(
    "summary",
    [
        "Codex Review: Didn't find any major issues. Breezy!",
        "Codex Review: Didn't find any major issues. Nice work!",
        "Codex Review: Didn't find any major issues. Can't wait for the next one!",
    ],
)
def test_codex_no_findings_comment_accepts_connector_summary_variants(summary: str) -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"

    def request_json(url: str, **_kwargs: Any) -> Any:
        if url.endswith("/commits/" + HEAD_SHA[:10]):
            return {"sha": HEAD_SHA}
        return _codex_no_findings_comment(
            reference,
            body=_codex_no_findings_body(summary=summary),
        )

    evidence = verify_codex_review_reference(
        reference,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        expected_commit_ref=HEAD_SHA,
        request_json=request_json,
    )

    assert evidence.commit_ref == HEAD_SHA


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (
            lambda response: response["user"].update(login="spoofed[bot]"),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response["user"].update(type="User"),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response["performed_via_github_app"].update(id=1),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response["performed_via_github_app"].update(slug="spoofed"),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response["performed_via_github_app"]["owner"].update(login="spoofed"),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response.update(
                html_url="https://github.com/owner/repo/pull/43#issuecomment-456"
            ),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response.update(updated_at="2026-07-15T11:01:00Z"),
            "edited after creation",
        ),
        (
            lambda response: response.update(
                body=response["body"].replace(
                    "Didn't find any major issues. Breezy!", "Found a major issue."
                )
            ),
            "not an exact Codex no-findings response",
        ),
        (
            lambda response: response.update(
                body=response["body"].replace(
                    "Didn't find any major issues.",
                    "Didn't find major issues.",
                )
            ),
            "not an exact Codex no-findings response",
        ),
        (
            lambda response: response.update(
                body=response["body"].replace(HEAD_SHA[:10], "ABCDEF1234")
            ),
            "invalid commit evidence",
        ),
        (
            lambda response: response.update(
                body=response["body"].replace(
                    f"**Reviewed commit:** `{HEAD_SHA[:10]}`",
                    (
                        f"**Reviewed commit:** `{HEAD_SHA[:10]}`\n"
                        f"**Reviewed commit:** `{HEAD_SHA[:10]}`"
                    ),
                )
            ),
            "invalid commit evidence",
        ),
    ],
)
def test_codex_no_findings_comment_rejects_untrusted_or_ambiguous_evidence(
    mutate: Any, error: str
) -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    response = _codex_no_findings_comment(reference)
    mutate(response)

    with pytest.raises(CommitIdentityError, match=error):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=lambda *_a, **_k: response,
        )


def test_codex_no_findings_comment_requires_exact_full_head_binding() -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    response = _codex_no_findings_comment(
        reference,
        body=_codex_no_findings_body(OUTSIDE_SHA[:10]),
    )

    with pytest.raises(CommitIdentityError, match="does not match the material commit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=lambda *_a, **_k: response,
        )


def test_codex_no_findings_comment_rejects_unresolved_short_commit() -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"

    def request_json(url: str, **_kwargs: Any) -> Any:
        if "/commits/" in url:
            return {"sha": OUTSIDE_SHA}
        return _codex_no_findings_comment(reference)

    with pytest.raises(CommitIdentityError, match="does not resolve to the material commit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=request_json,
        )

    with pytest.raises(CommitIdentityError, match="requires an expected full material commit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            request_json=lambda *_a, **_k: _codex_no_findings_comment(reference),
        )


def _codex_positive_reaction(
    reaction_id: int = 456,
    *,
    content: str = "+1",
    created_at: str = "2026-07-15T11:00:00Z",
) -> dict[str, Any]:
    return {
        "content": content,
        "created_at": created_at,
        "id": reaction_id,
        "user": {
            "id": 199_175_422,
            "login": "chatgpt-codex-connector[bot]",
            "type": "User",
        },
    }


def _codex_positive_reaction_request(
    reaction: dict[str, Any] | list[dict[str, Any]],
    *,
    pull_head: str = HEAD_SHA,
    workflow_runs: dict[str, Any] | None = None,
    head_events: list[dict[str, Any]] | None = None,
) -> Any:
    def request_json(url: str, **_kwargs: Any) -> Any:
        if "/reactions?" in url:
            return reaction if isinstance(reaction, list) else [reaction]
        if url.endswith("/pulls/42"):
            return {"head": {"sha": pull_head}}
        if "/actions/runs?" in url and workflow_runs is not None:
            return workflow_runs
        if "/issues/42/events?" in url:
            return [] if head_events is None else head_events
        raise AssertionError(f"unexpected GitHub API URL: {url}")

    return request_json


def _github_actions_workflow_runs(
    *,
    head_sha: str = HEAD_SHA,
    created_at: str = "2026-07-15T10:59:59Z",
    event: str = "pull_request",
    pr_number: int = 42,
) -> dict[str, Any]:
    return {
        "total_count": 1,
        "workflow_runs": [
            {
                "created_at": created_at,
                "event": event,
                "head_sha": head_sha,
                "pull_requests": [{"number": pr_number}],
            }
        ],
    }


def _workflow_run_response_with_pr_links(links: Any) -> dict[str, Any]:
    response = _github_actions_workflow_runs()
    response["workflow_runs"][0]["pull_requests"] = links
    return response


@pytest.mark.parametrize("content", ("+1", "heart", "hooray", "rocket"))
def test_codex_positive_reaction_is_accepted_without_exact_head_review_claim(
    content: str,
) -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"
    reaction = _codex_positive_reaction(content=content)
    requested_urls: list[str] = []
    request = _codex_positive_reaction_request(
        reaction,
        workflow_runs=_github_actions_workflow_runs(),
    )

    def request_json(url: str, **_kwargs: Any) -> Any:
        requested_urls.append(url)
        return request(url)

    evidence = verify_codex_review_reference(
        reference,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        expected_commit_ref=HEAD_SHA,
        request_json=request_json,
    )

    assert evidence == identity_module.CodexConnectorAdvisoryReactionEvidence(
        reference=reference,
        created_at="2026-07-15T11:00:00Z",
        content=content,
    )
    assert requested_urls == [
        "https://api.github.com/repos/owner/repo/issues/42/reactions?per_page=100&page=1",
        "https://api.github.com/repos/owner/repo/pulls/42",
        "https://api.github.com/repos/owner/repo/actions/runs"
        f"?event=pull_request&head_sha={HEAD_SHA}&per_page=100&page=1",
        "https://api.github.com/repos/owner/repo/issues/42/events?per_page=100&page=1",
    ]


def test_codex_positive_reaction_accepts_revalidated_mapping_only_live_head() -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"

    evidence = verify_codex_review_reference(
        reference,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        expected_commit_ref=HEAD_SHA,
        expected_live_pr_head_ref=OUTSIDE_SHA,
        request_json=_codex_positive_reaction_request(
            _codex_positive_reaction(),
            pull_head=OUTSIDE_SHA,
            workflow_runs=_github_actions_workflow_runs(),
        ),
    )

    assert isinstance(evidence, identity_module.CodexConnectorAdvisoryReactionEvidence)
    assert evidence.content == "+1"


def test_codex_positive_reaction_accepts_new_live_successor_after_mapping_only_push() -> None:
    sealed_reference = "https://github.com/owner/repo/pull/42#reaction-456"
    successor_reference = "https://github.com/owner/repo/pull/42#reaction-789"

    evidence = verify_codex_review_reference(
        sealed_reference,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        expected_commit_ref=HEAD_SHA,
        expected_live_pr_head_ref=OUTSIDE_SHA,
        request_json=_codex_positive_reaction_request(
            _codex_positive_reaction(
                789,
                created_at="2026-07-15T12:00:00Z",
            ),
            pull_head=OUTSIDE_SHA,
            workflow_runs=_github_actions_workflow_runs(),
        ),
    )

    assert evidence == identity_module.CodexConnectorAdvisoryReactionEvidence(
        reference=successor_reference,
        created_at="2026-07-15T12:00:00Z",
        content="+1",
    )


def test_codex_positive_reaction_does_not_rebind_on_material_head() -> None:
    with pytest.raises(CommitIdentityError, match="missing"):
        verify_codex_review_reference(
            "https://github.com/owner/repo/pull/42#reaction-456",
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=_codex_positive_reaction_request(
                _codex_positive_reaction(789),
                workflow_runs=_github_actions_workflow_runs(),
            ),
        )


def test_codex_positive_reaction_successor_rejects_malformed_live_content() -> None:
    malformed = _codex_positive_reaction(789)
    malformed["content"] = []
    with pytest.raises(CommitIdentityError, match="missing or ambiguous"):
        verify_codex_review_reference(
            "https://github.com/owner/repo/pull/42#reaction-456",
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            expected_live_pr_head_ref=OUTSIDE_SHA,
            request_json=_codex_positive_reaction_request(
                malformed,
                pull_head=OUTSIDE_SHA,
                workflow_runs=_github_actions_workflow_runs(),
            ),
        )


def test_codex_positive_reaction_accepts_head_observation_on_second_page() -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"
    untrusted_page = [
        {
            "created_at": "2026-07-15T10:59:59Z",
            "event": "pull_request",
            "head_sha": HEAD_SHA,
            "pull_requests": [{"number": 41}],
        }
        for _ in range(100)
    ]
    requested_urls: list[str] = []

    def request_json(url: str, **_kwargs: Any) -> Any:
        requested_urls.append(url)
        if "/reactions?" in url:
            return [_codex_positive_reaction()]
        if url.endswith("/pulls/42"):
            return {"head": {"sha": HEAD_SHA}}
        if "/actions/runs?" in url and url.endswith("&page=1"):
            return {"total_count": 101, "workflow_runs": untrusted_page}
        if "/actions/runs?" in url and url.endswith("&page=2"):
            return _github_actions_workflow_runs()
        if "/issues/42/events?" in url:
            return []
        raise AssertionError(f"unexpected GitHub API URL: {url}")

    evidence = verify_codex_review_reference(
        reference,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        expected_commit_ref=HEAD_SHA,
        request_json=request_json,
    )

    assert isinstance(evidence, identity_module.CodexConnectorAdvisoryReactionEvidence)
    assert evidence.content == "+1"
    assert requested_urls[-2].endswith("&per_page=100&page=2")
    assert requested_urls[-1].endswith("/issues/42/events?per_page=100&page=1")


@pytest.mark.parametrize(
    ("pull_response", "check_response", "error"),
    [
        ([], _github_actions_workflow_runs(), "PR response is malformed"),
        (
            {"head": {"sha": FIX_SHA}},
            _github_actions_workflow_runs(),
            "current material head",
        ),
        ({"head": {"sha": HEAD_SHA}}, [], "workflow-runs response is malformed"),
        (
            {"head": {"sha": HEAD_SHA}},
            {"total_count": 1, "workflow_runs": [None]},
            "workflow-run entry is malformed",
        ),
        (
            {"head": {"sha": HEAD_SHA}},
            _github_actions_workflow_runs(head_sha="not-a-sha"),
            "workflow-run SHA",
        ),
        (
            {"head": {"sha": HEAD_SHA}},
            _github_actions_workflow_runs(created_at="not-a-date"),
            "workflow-run created_at",
        ),
        (
            {"head": {"sha": HEAD_SHA}},
            {
                "total_count": 1,
                "workflow_runs": [
                    {
                        "created_at": "2026-07-15T10:59:59Z",
                        "event": "pull_request",
                        "head_sha": HEAD_SHA,
                        "pull_requests": {},
                    }
                ],
            },
            "workflow-run PR links are malformed",
        ),
        (
            {"head": {"sha": HEAD_SHA}},
            _workflow_run_response_with_pr_links([None, {"number": 42}]),
            "workflow-run PR link is malformed",
        ),
        (
            {"head": {"sha": HEAD_SHA}},
            _workflow_run_response_with_pr_links([{"number": True}]),
            "workflow-run PR link is malformed",
        ),
    ],
)
def test_codex_positive_reaction_rejects_malformed_head_observation_data(
    pull_response: Any,
    check_response: Any,
    error: str,
) -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"

    def request_json(url: str, **_kwargs: Any) -> Any:
        if "/reactions?" in url:
            return [_codex_positive_reaction()]
        if url.endswith("/pulls/42"):
            return pull_response
        if "/actions/runs?" in url:
            return check_response
        raise AssertionError(f"unexpected GitHub API URL: {url}")

    with pytest.raises(CommitIdentityError, match=error):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=request_json,
        )


def test_codex_positive_reaction_rejects_oversized_workflow_run_inventory() -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"
    response = _github_actions_workflow_runs()
    response["total_count"] = identity_module._MAX_HEAD_WORKFLOW_RUNS + 1

    with pytest.raises(CommitIdentityError, match="workflow-runs exceed safety limit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=_codex_positive_reaction_request(
                _codex_positive_reaction(),
                workflow_runs=response,
            ),
        )


@pytest.mark.parametrize(
    ("head_events", "error"),
    [
        ([None], "head-event entry is malformed"),
        ([{"event": None}], "head-event type is malformed"),
        (
            [{"created_at": "not-a-date", "event": "head_ref_force_pushed"}],
            "head-event created_at",
        ),
    ],
)
def test_codex_positive_reaction_rejects_malformed_head_events(
    head_events: Any,
    error: str,
) -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"

    with pytest.raises(CommitIdentityError, match=error):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=_codex_positive_reaction_request(
                _codex_positive_reaction(),
                workflow_runs=_github_actions_workflow_runs(),
                head_events=head_events,
            ),
        )


def test_codex_positive_reaction_fails_closed_at_head_event_page_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"
    monkeypatch.setattr(identity_module, "_MAX_PR_HEAD_EVENT_PAGES", 1)

    with pytest.raises(CommitIdentityError, match="head-event pagination exceeded page limit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=_codex_positive_reaction_request(
                _codex_positive_reaction(),
                workflow_runs=_github_actions_workflow_runs(),
                head_events=[{"event": "commented"} for _ in range(100)],
            ),
        )


@pytest.mark.parametrize("event", ("head_ref_force_pushed", "head_ref_restored"))
@pytest.mark.parametrize(
    "created_at",
    ("2026-07-15T10:59:59Z", "2026-07-15T10:59:59.500Z"),
)
def test_codex_positive_reaction_rejects_replayed_head_after_ref_rewrite(
    event: str,
    created_at: str,
) -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"

    with pytest.raises(CommitIdentityError, match="superseded PR head observation"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=_codex_positive_reaction_request(
                _codex_positive_reaction(),
                workflow_runs=_github_actions_workflow_runs(),
                head_events=[
                    {
                        "created_at": created_at,
                        "event": event,
                    }
                ],
            ),
        )


def test_codex_positive_reaction_fails_closed_at_workflow_run_page_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"
    monkeypatch.setattr(identity_module, "_MAX_HEAD_WORKFLOW_RUN_PAGES", 1)

    def request_json(url: str, **_kwargs: Any) -> Any:
        if "/reactions?" in url:
            return [_codex_positive_reaction()]
        if url.endswith("/pulls/42"):
            return {"head": {"sha": HEAD_SHA}}
        if "/actions/runs?" in url:
            return {
                "total_count": 100,
                "workflow_runs": [
                    {
                        "created_at": "2026-07-15T10:59:59Z",
                        "event": "pull_request",
                        "head_sha": HEAD_SHA,
                        "pull_requests": [{"number": 41}],
                    }
                    for _ in range(100)
                ],
            }
        raise AssertionError(f"unexpected GitHub API URL: {url}")

    with pytest.raises(CommitIdentityError, match="pagination exceeded page limit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=request_json,
        )


@pytest.mark.parametrize(
    ("run_head_sha", "run_created_at", "run_event", "run_pr_number"),
    [
        (FIX_SHA, "2026-07-15T10:59:59Z", "pull_request", 42),
        (HEAD_SHA, "2026-07-15T11:00:00Z", "pull_request", 42),
        (HEAD_SHA, "2026-07-15T11:00:01Z", "pull_request", 42),
        (HEAD_SHA, "2026-07-15T10:59:59Z", "push", 42),
        (HEAD_SHA, "2026-07-15T10:59:59Z", "pull_request", 41),
    ],
)
def test_codex_positive_reaction_rejects_invalid_head_observation(
    run_head_sha: str,
    run_created_at: str,
    run_event: str,
    run_pr_number: int,
) -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"

    with pytest.raises(
        CommitIdentityError,
        match="does not follow a GitHub observation of the exact material head",
    ):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA,
            request_json=_codex_positive_reaction_request(
                _codex_positive_reaction(),
                workflow_runs=_github_actions_workflow_runs(
                    head_sha=run_head_sha,
                    created_at=run_created_at,
                    event=run_event,
                    pr_number=run_pr_number,
                ),
            ),
        )


def test_codex_positive_reaction_requires_expected_full_material_head() -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"

    with pytest.raises(CommitIdentityError, match="requires an expected full material commit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            request_json=lambda *_a, **_k: pytest.fail(
                "reaction must require a material head first"
            ),
        )

    with pytest.raises(CommitIdentityError, match="expected Codex review commit"):
        verify_codex_review_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_commit_ref=HEAD_SHA[:10],
            request_json=lambda *_a, **_k: pytest.fail(
                "reaction must reject a short material head"
            ),
        )


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (lambda reaction: reaction["user"].update(login="spoofed[bot]"), "not a trusted"),
        (lambda reaction: reaction["user"].update(id=1), "not a trusted"),
        (lambda reaction: reaction["user"].update(type="Organization"), "not a trusted"),
        (lambda reaction: reaction.update(content="eyes"), "not a trusted"),
        (lambda reaction: reaction.update(content=[]), "not a trusted"),
        (
            lambda reaction: reaction.update(created_at="2026-99-15T11:00:00Z"),
            "not a valid ISO-8601",
        ),
    ],
)
def test_codex_positive_reaction_rejects_untrusted_or_malformed_inputs(
    mutate: Any,
    error: str,
) -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"
    reaction = _codex_positive_reaction()
    mutate(reaction)

    with pytest.raises(CommitIdentityError, match=error):
        verify_codex_connector_advisory_reaction_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            request_json=_codex_positive_reaction_request(reaction),
        )


def test_codex_positive_reaction_requires_exact_pr_reference_and_one_live_id() -> None:
    reference = "https://github.com/owner/repo/pull/42#reaction-456"
    reaction = _codex_positive_reaction()

    with pytest.raises(CommitIdentityError, match="ambiguous"):
        verify_codex_connector_advisory_reaction_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            request_json=_codex_positive_reaction_request([reaction, reaction]),
        )

    with pytest.raises(CommitIdentityError, match="canonical reaction URL"):
        verify_codex_connector_advisory_reaction_reference(
            "https://github.com/owner/repo/pull/43#reaction-456",
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            request_json=lambda *_a, **_k: pytest.fail("cross-PR reaction must not fetch"),
        )


def _review_credit_quota_comment(
    reference: str,
    *,
    body: str | None = None,
    created_at: str = "2026-07-15T11:05:00Z",
) -> dict[str, Any]:
    return {
        "body": (
            body
            if body is not None
            else (
                "Codex usage limits have been reached for code reviews. "
                "Please check with the admins of this repo to increase the limits "
                "by adding credits.\n"
                "Credits must be used to enable repository wide code reviews."
            )
        ),
        "created_at": created_at,
        "html_url": reference,
        "id": 456,
        "issue_url": "https://api.github.com/repos/owner/repo/issues/42",
        "performed_via_github_app": {
            "id": 1_144_995,
            "owner": {"login": "openai"},
            "slug": "chatgpt-codex-connector",
        },
        "updated_at": created_at,
        "user": {"login": "chatgpt-codex-connector[bot]", "type": "Bot"},
    }


def test_review_source_unavailability_verifies_exact_immutable_codex_comment() -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    response = _review_credit_quota_comment(
        reference,
        created_at="2020-01-01T00:00:00Z",
    )

    evidence = verify_codex_review_source_unavailability_reference(
        reference,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        request_json=lambda *_a, **_k: response,
    )

    assert evidence == CodexReviewSourceUnavailabilityEvidence(
        reference=reference,
        created_at="2020-01-01T00:00:00Z",
        source_status="usage_limit_reached",
        body_sha256=("sha256:" + hashlib.sha256(response["body"].encode("utf-8")).hexdigest()),
    )


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (
            lambda response: response["user"].update(login="spoofed[bot]"),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response["user"].update(type="User"),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response["performed_via_github_app"].update(id=1),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response["performed_via_github_app"].update(slug="spoofed"),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response["performed_via_github_app"]["owner"].update(login="spoofed"),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response.update(updated_at="2026-07-15T11:06:00Z"),
            "edited after creation",
        ),
        (
            lambda response: response.update(body=response["body"] + " "),
            "not an exact known quota response",
        ),
        (
            lambda response: response.update(body="Codex review unavailable"),
            "not an exact known quota response",
        ),
        (
            lambda response: response.update(id=999),
            "comment id does not match",
        ),
        (
            lambda response: response.update(
                html_url="https://github.com/owner/repo/pull/42#issuecomment-999"
            ),
            "not trusted Codex evidence",
        ),
        (
            lambda response: response.update(
                issue_url="https://api.github.com/repos/owner/repo/issues/43"
            ),
            "not trusted Codex evidence",
        ),
    ],
)
def test_review_source_unavailability_rejects_spoofed_or_changed_comment(
    mutation: Any,
    error: str,
) -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    response = _review_credit_quota_comment(reference)
    mutation(response)

    with pytest.raises(CommitIdentityError, match=error):
        verify_codex_review_source_unavailability_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            request_json=lambda *_a, **_k: response,
        )


@pytest.mark.parametrize(
    ("reference", "repository", "pr_number"),
    [
        (
            "https://github.com/owner/repo/pull/43#issuecomment-456",
            "owner/repo",
            42,
        ),
        (
            "https://github.com/owner/repo/pull/42#issuecomment-abc",
            "owner/repo",
            42,
        ),
        (
            "https://github.com/owner/repo/pull/42#issuecomment-456",
            "other/repo",
            42,
        ),
    ],
)
def test_review_source_unavailability_rejects_cross_pr_repo_or_noncanonical_id(
    reference: str,
    repository: str,
    pr_number: int,
) -> None:
    with pytest.raises(CommitIdentityError, match="exact PR"):
        verify_codex_review_source_unavailability_reference(
            reference,
            repository=repository,
            pr_number=pr_number,
            token="opaque",
            request_json=lambda *_a, **_k: pytest.fail("must reject before refetch"),
        )


def _prior_codex_review(reference: str) -> dict[str, Any]:
    return {
        "commit_id": FIX_SHA,
        "html_url": reference,
        "state": "COMMENTED",
        "submitted_at": "2026-07-15T10:30:00Z",
        "user": {"login": "chatgpt-codex-connector[bot]"},
    }


def _operator_exact_head_review(reference: str) -> dict[str, Any]:
    return {
        "author_association": "OWNER",
        "body": (
            f"Exact-head bounded review completed for `{HEAD_SHA}`. "
            "No actionable findings remain."
        ),
        "commit_id": HEAD_SHA,
        "html_url": reference,
        "state": "COMMENTED",
        "submitted_at": "2026-07-15T11:10:00Z",
        "user": {"id": 123, "login": "owner", "type": "User"},
    }


def _review_credit_override_comment(
    reference: str,
    *,
    quota_reference: str,
    prior_review_reference: str,
    operator_review_reference: str,
    created_at: str = "2026-07-15T11:15:00Z",
) -> dict[str, Any]:
    return {
        "author_association": "OWNER",
        "body": render_review_credit_outage_override_comment(
            pr_number=42,
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
            quota_reference=quota_reference,
            prior_review_reference=prior_review_reference,
            operator_review_reference=operator_review_reference,
        ),
        "created_at": created_at,
        "html_url": reference,
        "issue_url": "https://api.github.com/repos/owner/repo/issues/42",
        "performed_via_github_app": None,
        "updated_at": created_at,
        "user": {"id": 123, "login": "owner", "type": "User"},
    }


def _review_credit_request_json(
    override_reference: str,
    quota_reference: str,
    prior_review_reference: str,
    operator_review_reference: str,
) -> Any:
    def request_json(url: str, **_kwargs: Any) -> Any:
        if url.endswith("/issues/comments/456"):
            return _review_credit_quota_comment(quota_reference)
        if url.endswith("/issues/comments/654"):
            return _review_credit_override_comment(
                override_reference,
                quota_reference=quota_reference,
                prior_review_reference=prior_review_reference,
                operator_review_reference=operator_review_reference,
            )
        if url.endswith("/reviews/123"):
            return _prior_codex_review(prior_review_reference)
        if url.endswith("/reviews/789"):
            return _operator_exact_head_review(operator_review_reference)
        if url.endswith("/commits/" + FIX_SHA):
            return {"sha": FIX_SHA}
        if "/compare/" in url:
            return {
                "ahead_by": 1,
                "base_commit": {"sha": FIX_SHA},
                "behind_by": 0,
                "commits": [{"sha": HEAD_SHA}],
                "merge_base_commit": {"sha": FIX_SHA},
                "status": "ahead",
                "total_commits": 1,
            }
        raise AssertionError(f"unexpected GitHub API URL: {url}")

    return request_json


def test_review_credit_outage_requires_trusted_quota_prior_review_and_owner_head() -> None:
    override_reference = "https://github.com/owner/repo/pull/42#issuecomment-654"
    quota_reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    prior_review_reference = "https://github.com/owner/repo/pull/42#pullrequestreview-123"
    operator_review_reference = "https://github.com/owner/repo/pull/42#pullrequestreview-789"

    evidence = verify_review_credit_outage_references(
        override_reference=override_reference,
        quota_reference=quota_reference,
        prior_review_reference=prior_review_reference,
        operator_review_reference=operator_review_reference,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        snapshot=_snapshot(),
        expected_material_head_sha=HEAD_SHA,
        expected_material_digest=DIGEST,
        now=datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
        request_json=_review_credit_request_json(
            override_reference,
            quota_reference,
            prior_review_reference,
            operator_review_reference,
        ),
    )

    assert evidence.override_reference == override_reference
    assert evidence.material_digest == DIGEST
    assert evidence.material_head_sha == HEAD_SHA
    assert evidence.prior_review_commit_ref == FIX_SHA
    assert evidence.operator_user_id == 123
    assert evidence.operator_association == "OWNER"


def test_review_credit_outage_rejects_actionable_operator_review_suffix() -> None:
    override_reference = "https://github.com/owner/repo/pull/42#issuecomment-654"
    quota_reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    prior_review_reference = "https://github.com/owner/repo/pull/42#pullrequestreview-123"
    operator_review_reference = "https://github.com/owner/repo/pull/42#pullrequestreview-789"
    operator_review = _operator_exact_head_review(operator_review_reference)
    operator_review["body"] += "\n\nP2: unresolved review finding"
    base_request = _review_credit_request_json(
        override_reference,
        quota_reference,
        prior_review_reference,
        operator_review_reference,
    )

    def request_json(url: str, **kwargs: Any) -> Any:
        if url.endswith("/reviews/789"):
            return operator_review
        return base_request(url, **kwargs)

    with pytest.raises(
        CommitIdentityError,
        match="operator review is not trusted exact-head credit-outage evidence",
    ):
        verify_review_credit_outage_references(
            override_reference=override_reference,
            quota_reference=quota_reference,
            prior_review_reference=prior_review_reference,
            operator_review_reference=operator_review_reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            snapshot=_snapshot(),
            expected_material_head_sha=HEAD_SHA,
            expected_material_digest=DIGEST,
            now=datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
            request_json=request_json,
        )


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (
            lambda response: response.update(updated_at="2026-07-15T11:06:00Z"),
            "edited after creation",
        ),
        (
            lambda response: response.update(body="Codex review unavailable"),
            "not an exact review-credit outage",
        ),
        (
            lambda response: response["performed_via_github_app"].update(id=1),
            "not trusted Codex evidence",
        ),
    ],
)
def test_review_credit_outage_rejects_ambiguous_quota_evidence(
    mutation: Any,
    error: str,
) -> None:
    override_reference = "https://github.com/owner/repo/pull/42#issuecomment-654"
    quota_reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    prior_review_reference = "https://github.com/owner/repo/pull/42#pullrequestreview-123"
    operator_review_reference = "https://github.com/owner/repo/pull/42#pullrequestreview-789"
    quota_response = _review_credit_quota_comment(quota_reference)
    mutation(quota_response)
    base_request = _review_credit_request_json(
        override_reference,
        quota_reference,
        prior_review_reference,
        operator_review_reference,
    )

    def request_json(url: str, **kwargs: Any) -> Any:
        if url.endswith("/issues/comments/456"):
            return quota_response
        return base_request(url, **kwargs)

    with pytest.raises(CommitIdentityError, match=error):
        verify_review_credit_outage_references(
            override_reference=override_reference,
            quota_reference=quota_reference,
            prior_review_reference=prior_review_reference,
            operator_review_reference=operator_review_reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            snapshot=_snapshot(),
            expected_material_head_sha=HEAD_SHA,
            expected_material_digest=DIGEST,
            now=datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
            request_json=request_json,
        )


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (
            lambda response: response.update(updated_at="2026-07-15T11:16:00Z"),
            "edited after creation",
        ),
        (
            lambda response: response.update(body="operator says proceed"),
            "body does not match",
        ),
        (
            lambda response: response["user"].update(id=999),
            "not trusted review credit outage evidence",
        ),
        (
            lambda response: response.update(
                created_at="2026-07-15T11:09:00Z",
                updated_at="2026-07-15T11:09:00Z",
            ),
            "predates the exact-head operator review",
        ),
    ],
)
def test_review_credit_outage_rejects_ambiguous_owner_override(
    mutation: Any,
    error: str,
) -> None:
    override_reference = "https://github.com/owner/repo/pull/42#issuecomment-654"
    quota_reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    prior_review_reference = "https://github.com/owner/repo/pull/42#pullrequestreview-123"
    operator_review_reference = "https://github.com/owner/repo/pull/42#pullrequestreview-789"
    override_response = _review_credit_override_comment(
        override_reference,
        quota_reference=quota_reference,
        prior_review_reference=prior_review_reference,
        operator_review_reference=operator_review_reference,
    )
    mutation(override_response)
    base_request = _review_credit_request_json(
        override_reference,
        quota_reference,
        prior_review_reference,
        operator_review_reference,
    )

    def request_json(url: str, **kwargs: Any) -> Any:
        if url.endswith("/issues/comments/654"):
            return override_response
        return base_request(url, **kwargs)

    with pytest.raises(CommitIdentityError, match=error):
        verify_review_credit_outage_references(
            override_reference=override_reference,
            quota_reference=quota_reference,
            prior_review_reference=prior_review_reference,
            operator_review_reference=operator_review_reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            snapshot=_snapshot(),
            expected_material_head_sha=HEAD_SHA,
            expected_material_digest=DIGEST,
            now=datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
            request_json=request_json,
        )


def test_review_credit_outage_receipt_is_distinct_and_material_bound() -> None:
    receipt = build_review_credit_outage_receipt(
        material_digest=DIGEST,
        material_head_sha=HEAD_SHA,
        override_reference="https://github.com/owner/repo/pull/42#issuecomment-654",
        override_created_at="2026-07-15T11:15:00Z",
        quota_reference="https://github.com/owner/repo/pull/42#issuecomment-456",
        quota_created_at="2026-07-15T11:05:00Z",
        prior_review_reference=("https://github.com/owner/repo/pull/42#pullrequestreview-123"),
        prior_review_submitted_at="2026-07-15T10:30:00Z",
        prior_review_commit_ref=FIX_SHA,
        operator_review_reference=("https://github.com/owner/repo/pull/42#pullrequestreview-789"),
        operator_review_submitted_at="2026-07-15T11:10:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )

    assert is_review_credit_outage_receipt(receipt)
    assert receipt["status"] == "tooling_unavailable"
    assert receipt["review_commit_ref"] == HEAD_SHA
    seal = _seal(
        build_security_outage_override_receipt(
            base_revision=BASE_SHA,
            head_revision=HEAD_SHA,
            material_digest=DIGEST,
            override_reference=("https://github.com/owner/repo/pull/42#issuecomment-789"),
            created_at="2026-07-15T11:00:00Z",
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
        )
    )
    seal["code_review"] = receipt
    parsed = parse_embedded_review_seal(render_embedded_review_seal(seal))
    assert parsed["code_review"] == receipt


@pytest.mark.parametrize(
    ("repository", "pr_number", "paths", "allowed"),
    [
        (
            "Katsiarynakavaleuskaya/PulsePlate",
            2142,
            ("scripts/ci/check_pr_merge_readiness.py",),
            True,
        ),
        (
            "Katsiarynakavaleuskaya/PulsePlate",
            2143,
            ("scripts/ci/check_pr_merge_readiness.py",),
            False,
        ),
        (
            "Katsiarynakavaleuskaya/PulsePlate",
            2143,
            ("scripts/ci/check_pr_body_phase2_gates.py",),
            False,
        ),
        (
            "Katsiarynakavaleuskaya/PulsePlate",
            2143,
            ("docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",),
            False,
        ),
        (
            "Katsiarynakavaleuskaya/PulsePlate",
            2143,
            ("scripts/ci/ci_risk_profile.py",),
            False,
        ),
        (
            "Katsiarynakavaleuskaya/PulsePlate",
            2143,
            ("requirements-test.txt",),
            False,
        ),
        ("owner/repo", 42, ("requirements-test.txt",), False),
    ],
)
def test_review_credit_outage_scope_is_live_only_for_bootstrap_pr(
    repository: str,
    pr_number: int,
    paths: tuple[str, ...],
    allowed: bool,
) -> None:
    if allowed:
        validate_review_credit_outage_scope(
            repository=repository,
            pr_number=pr_number,
            material_paths=paths,
        )
        return
    with pytest.raises(ReviewEvidenceError, match="live-valid only.*PR #2142"):
        validate_review_credit_outage_scope(
            repository=repository,
            pr_number=pr_number,
            material_paths=paths,
        )


def _security_outage_comment(
    reference: str,
    *,
    body: str | None = None,
    created_at: str = "2026-07-15T11:00:00Z",
) -> dict[str, Any]:
    return {
        "author_association": "OWNER",
        "body": (
            body
            if body is not None
            else render_security_outage_override_comment(
                pr_number=42,
                material_head_sha=HEAD_SHA,
                material_digest=DIGEST,
            )
        ),
        "created_at": created_at,
        "html_url": reference,
        "issue_url": "https://api.github.com/repos/owner/repo/issues/42",
        "performed_via_github_app": None,
        "updated_at": created_at,
        "user": {"id": 123, "login": "owner", "type": "User"},
    }


def test_security_outage_override_is_bound_to_exact_operator_and_material() -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-789"
    evidence = verify_security_outage_override_reference(
        reference,
        repository="owner/repo",
        pr_number=42,
        token="opaque",
        expected_material_head_sha=HEAD_SHA,
        expected_material_digest=DIGEST,
        now=datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
        request_json=lambda *_a, **_k: _security_outage_comment(reference),
    )

    assert evidence.operator_login == "owner"
    assert evidence.operator_user_id == 123
    assert evidence.operator_association == "OWNER"
    assert evidence.material_head_sha == HEAD_SHA
    assert evidence.material_digest == DIGEST


@pytest.mark.parametrize(
    "mutate",
    [
        lambda response: response.update(author_association="COLLABORATOR"),
        lambda response: response["user"].update(type="Bot"),
        lambda response: response["user"].pop("id"),
        lambda response: response["user"].update(id=0),
        lambda response: response.pop("performed_via_github_app"),
        lambda response: response.update(performed_via_github_app={"id": 1}),
        lambda response: response.update(
            issue_url="https://api.github.com/repos/owner/repo/issues/43"
        ),
        lambda response: response.update(updated_at="2026-07-15T11:01:00Z"),
        lambda response: response.update(body=response["body"] + "\nextra"),
        lambda response: response.update(
            body=response["body"].replace("codex_security_mcp_timeout", "unknown")
        ),
        lambda response: response.update(body=response["body"].replace("-32001", "-32002")),
        lambda response: response.update(
            body=response["body"].replace("Scan-ID: none", "Scan-ID: scan-123")
        ),
        lambda response: response.update(body=response["body"].replace(HEAD_SHA, OUTSIDE_SHA)),
        lambda response: response.update(
            body=response["body"].replace(DIGEST, "sha256:" + "f" * 64)
        ),
    ],
)
def test_security_outage_override_rejects_untrusted_or_ambiguous_comment(
    mutate: Any,
) -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-789"
    response = _security_outage_comment(reference)
    mutate(response)

    with pytest.raises(CommitIdentityError):
        verify_security_outage_override_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_material_head_sha=HEAD_SHA,
            expected_material_digest=DIGEST,
            now=datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
            request_json=lambda *_a, **_k: response,
        )


def test_security_outage_override_rejects_expired_or_deleted_comment() -> None:
    reference = "https://github.com/owner/repo/pull/42#issuecomment-789"
    with pytest.raises(CommitIdentityError, match="expired"):
        verify_security_outage_override_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_material_head_sha=HEAD_SHA,
            expected_material_digest=DIGEST,
            now=datetime(2026, 7, 16, 12, 0, 1, tzinfo=timezone.utc),
            request_json=lambda *_a, **_k: _security_outage_comment(reference),
        )

    with pytest.raises(GitHubHttpError, match="HTTP 404"):
        verify_security_outage_override_reference(
            reference,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
            expected_material_head_sha=HEAD_SHA,
            expected_material_digest=DIGEST,
            now=datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
            request_json=lambda *_a, **_k: (_ for _ in ()).throw(GitHubHttpError(404, "Not Found")),
        )


def test_security_outage_receipt_is_distinct_and_material_bound() -> None:
    receipt = build_security_outage_override_receipt(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
        override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
        created_at="2026-07-15T11:00:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )

    assert is_security_outage_override_receipt(receipt)
    assert receipt["scan_id"] is None
    assert receipt["status"] == "tooling_unavailable"
    assert "findings_count" not in receipt
    assert (
        parse_embedded_review_seal(render_embedded_review_seal(_seal(receipt)))["codex_security"]
        == receipt
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda receipt: receipt.update(outage_class="unknown"),
        lambda receipt: receipt.update(error_code="-32002"),
        lambda receipt: receipt.update(scan_id="123e4567-e89b-42d3-a456-426614174000"),
        lambda receipt: receipt.update(operator_user_id=0),
        lambda receipt: receipt.update(operator_user_id=True),
        lambda receipt: receipt.update(extra="unexpected"),
        lambda receipt: receipt.pop("material_digest"),
        lambda receipt: receipt.update(material_digest="sha256:" + "f" * 64),
    ],
)
def test_security_outage_receipt_rejects_unknown_or_open_shapes(mutate: Any) -> None:
    receipt = build_security_outage_override_receipt(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
        override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
        created_at="2026-07-15T11:00:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )
    mutate(receipt)

    with pytest.raises(ReviewEvidenceError):
        render_embedded_review_seal(_seal(receipt))


@pytest.mark.parametrize(
    ("repository", "pr_number", "paths", "allowed"),
    [
        (
            "Katsiarynakavaleuskaya/PulsePlate",
            2142,
            ("scripts/ci/check_pr_merge_readiness.py",),
            True,
        ),
        (
            "Katsiarynakavaleuskaya/PulsePlate",
            2143,
            ("scripts/ci/check_pr_merge_readiness.py",),
            False,
        ),
        (
            "Katsiarynakavaleuskaya/PulsePlate",
            2143,
            ("scripts/orchestration/check_merge_ready.py",),
            False,
        ),
        (
            "owner/repo",
            2142,
            ("scripts/ci/check_pr_merge_readiness.py",),
            False,
        ),
        (
            "owner/repo",
            42,
            ("scripts/ci/check_private_python_proxy_health.py",),
            False,
        ),
        (
            "owner/repo",
            42,
            ("scripts/orchestration/review_source_status.py",),
            False,
        ),
        (
            "owner/repo",
            42,
            (".github/actions/python-setup/action.yml",),
            False,
        ),
        (
            "owner/repo",
            42,
            (
                "AGENTS.md",
                "RUNBOOK_AGENT.md",
                "docs/orchestration/AGENTS.md",
                "docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md",
                "scripts/orchestration/qoder_dispatch_bridge.py",
                "scripts/orchestration/render_codex_start_prompt.py",
                "scripts/orchestration/role_dispatch_bridge.py",
                "scripts/orchestration/task_bootstrap.py",
            ),
            False,
        ),
        ("owner/repo", 42, ("scripts/ci_pip_audit.sh",), False),
        ("owner/repo", 42, (".pre-commit-config.yaml",), False),
        ("owner/repo", 42, (".secrets.baseline",), False),
        ("owner/repo", 42, ("scripts/hooks/repo_python.sh",), False),
        ("owner/repo", 42, ("tests/guards/test_nosec_policy_guard.py",), False),
        ("owner/repo", 42, ("tests/test_repo_policy_guards.py",), False),
        (
            "owner/repo",
            42,
            ("scripts/run-backend-tests-pre-commit.sh",),
            False,
        ),
        (
            "owner/repo",
            42,
            ("scripts/orchestration/check_review_threads_disposition.py",),
            False,
        ),
        (
            "owner/repo",
            42,
            ("scripts/orchestration/review_mapping_artifact.py",),
            False,
        ),
        (
            "owner/repo",
            42,
            ("scripts/orchestration/requested_agents.py",),
            False,
        ),
        (
            "owner/repo",
            42,
            ("docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",),
            False,
        ),
        (
            "owner/repo",
            42,
            ("docs/orchestration/contracts/review_source_status.v1.json",),
            False,
        ),
        ("owner/repo", 42, (".bandit",), False),
        ("owner/repo", 42, (".bandit.yaml",), False),
        ("owner/repo", 42, ("trivy/ignore-policy.rego",), False),
        ("owner/repo", 42, ("requirements-test.txt",), False),
    ],
)
def test_security_outage_override_scope_blocks_future_self_authorization(
    repository: str,
    pr_number: int,
    paths: tuple[str, ...],
    allowed: bool,
) -> None:
    if allowed:
        validate_security_outage_override_scope(
            repository=repository,
            pr_number=pr_number,
            material_paths=paths,
        )
        return

    with pytest.raises(ReviewEvidenceError, match="trust-boundary changes"):
        validate_security_outage_override_scope(
            repository=repository,
            pr_number=pr_number,
            material_paths=paths,
        )


def test_security_outage_trust_boundary_covers_security_dependency_inputs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    audit_script = (repo_root / "scripts/ci_pip_audit.sh").read_text(encoding="utf-8")
    audited_manifests = set(re.findall(r'manifests(?:\+)?=\("([^"]+)"\)', audit_script))
    audited_inputs = {
        f"{path.removesuffix('.txt')}.in"
        for path in audited_manifests
        if (repo_root / f"{path.removesuffix('.txt')}.in").is_file()
    }
    dependency_basenames = {
        "Gemfile",
        "Gemfile.lock",
        "Package.resolved",
        "Package.swift",
        "package-lock.json",
        "package.json",
        "pyproject.toml",
    }
    tracked_dependency_paths = {
        path
        for path in _git(repo_root, "ls-files").splitlines()
        if PurePosixPath(path).name in dependency_basenames
        or re.fullmatch(
            r"requirements(?:-[a-z0-9][a-z0-9-]*)?\.(?:in|txt)",
            PurePosixPath(path).name,
        )
    }
    protected_paths = tracked_dependency_paths | {
        "Makefile",
        "constraints.txt",
        "tests/fixtures/dependency_security_schema.json",
        "tests/test_dependency_security_guard.py",
    }

    assert audited_manifests
    assert audited_manifests | audited_inputs <= protected_paths
    assert {
        "frontend/package-lock.json",
        "frontend/package.json",
        "ios/Gemfile",
        "ios/Gemfile.lock",
        "ios/Package.resolved",
        "ios/Package.swift",
        "package-lock.json",
        "package.json",
        "pyproject.toml",
        "requirements-ci-lite.in",
        "constraints.txt",
        "requirements-ci-lite.txt",
        "requirements-test.in",
        "requirements-test.txt",
        "requirements-dev.in",
        "requirements-dev.txt",
        "requirements-lock.txt",
        "requirements-all.txt",
        "Makefile",
        "tests/fixtures/dependency_security_schema.json",
        "tests/test_dependency_security_guard.py",
    } <= protected_paths
    for path in sorted(protected_paths):
        with pytest.raises(ReviewEvidenceError, match="trust-boundary changes"):
            validate_security_outage_override_scope(
                repository="owner/repo",
                pr_number=42,
                material_paths=(path,),
            )


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    git = shutil.which("git")
    assert git is not None
    run_env = dict(env or os.environ)
    allowed_git_prefixes = ("GIT_AUTHOR_", "GIT_COMMITTER_")
    for key in tuple(run_env):
        if key.startswith("GIT_") and not key.startswith(allowed_git_prefixes):
            run_env.pop(key)
    result = subprocess.run(
        [git, *args],
        cwd=repo,
        env=run_env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _commit(repo: Path, message: str) -> str:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "PulsePlate Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "PulsePlate Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
    )
    _git(repo, "add", "-A", env=env)
    _git(repo, "commit", "-m", message, env=env)
    return _git(repo, "rev-parse", "HEAD", env=env)


def test_material_digest_ignores_only_exact_current_pr_mapping(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base = _commit(repo, "base")

    source = repo / "src" / "nested" / "policy.py"
    source.parent.mkdir(parents=True)
    source.write_text("ENFORCED = True\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    before_closeout = compute_material_manifest(
        repo, base_ref_oid=base, head_ref_oid=material_head, pr_number=42
    )
    assert [entry.path for entry in before_closeout.entries] == ["src/nested/policy.py"]

    mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    mapping.write_text("mapping\n", encoding="utf-8")
    mapping_head = _commit(repo, "mapping closeout")
    after_closeout = compute_material_manifest(
        repo, base_ref_oid=base, head_ref_oid=mapping_head, pr_number=42
    )
    assert after_closeout.digest == before_closeout.digest

    (repo / "docs" / "operator.md").write_text("material docs\n", encoding="utf-8")
    docs_head = _commit(repo, "other docs")
    after_other_docs = compute_material_manifest(
        repo, base_ref_oid=base, head_ref_oid=docs_head, pr_number=42
    )
    assert after_other_docs.digest != before_closeout.digest


def _write_json(path: Path, value: Any) -> bytes:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _build_scan_bundle(root: Path) -> Path:
    coverage = {
        "completeness": "complete",
        "deferred": [],
        "documentType": "codex-security.coverage",
        "excludePaths": [],
        "explicitExclusions": [],
        "includePaths": ["."],
        "inventoryStrategy": "diff",
        "mode": "branch_diff",
        "openQuestions": [],
        "scanId": SCAN_ID,
        "schemaVersion": "1.0",
        "surfaces": [],
    }
    findings = {
        "documentType": "codex-security.findings",
        "findings": [],
        "scanId": SCAN_ID,
        "schemaVersion": "1.0",
    }
    coverage_raw = _write_json(root / "coverage.json", coverage)
    findings_raw = _write_json(root / "findings.json", findings)
    ledger_path = root / "artifacts" / "02_discovery" / "work_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True)
    ledger_raw = b'{"status":"reviewed"}\n'
    ledger_path.write_bytes(ledger_raw)

    manifest = {
        "documentType": "codex-security.scan-manifest",
        "scan": {
            "artifacts": [
                {
                    "mediaType": "application/json",
                    "path": "findings.json",
                    "sha256": hashlib.sha256(findings_raw).hexdigest(),
                },
                {
                    "mediaType": "application/json",
                    "path": "coverage.json",
                    "sha256": hashlib.sha256(coverage_raw).hexdigest(),
                },
                {
                    "mediaType": "application/octet-stream",
                    "path": "artifacts/02_discovery/work_ledger.jsonl",
                    "sha256": hashlib.sha256(ledger_raw).hexdigest(),
                },
            ],
            "completedAt": "2026-07-15T11:00:00Z",
            "coverageRef": "coverage.json",
            "findingsRef": "findings.json",
            "id": SCAN_ID,
            "producer": {"name": "codex-security-plugin", "version": "0.1.11"},
            "scope": {},
            "sealedAt": "2026-07-15T11:00:00Z",
            "startedAt": "2026-07-15T10:00:00Z",
            "status": "completed",
            "target": {
                "baseRevision": BASE_SHA,
                "displayName": "repo",
                "headRevision": HEAD_SHA,
                "kind": "git_diff",
                "snapshotDigest": SNAPSHOT_DIGEST,
                "targetId": "target_sha256_" + "c" * 64,
            },
            "threatModel": {},
        },
        "schemaVersion": "1.0",
    }
    _write_json(root / "scan-manifest.json", manifest)
    return root / "scan-manifest.json"


def _add_manifest_artifact(manifest_path: Path, *, path: str, media_type: str, raw: bytes) -> None:
    artifact_path = manifest_path.parent / path
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(raw)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scan"]["artifacts"].append(
        {
            "mediaType": media_type,
            "path": path,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    )
    _write_json(manifest_path, manifest)


def _build_v011_scan_bundle(root: Path) -> Path:
    manifest_path = _build_scan_bundle(root)
    hardening_path = root / "hardening" / "hardening.md"
    hardening_path.parent.mkdir(parents=True, exist_ok=True)
    hardening_path.write_bytes(b"# Hardening\n")
    for path, raw in (
        (
            "artifacts/02_discovery/finding_discovery_report.md",
            b"# Finding discovery\n",
        ),
        (
            "artifacts/03_coverage/repository_coverage_ledger.md",
            b"# Coverage ledger\n",
        ),
        (
            "artifacts/05_findings/attack_path_analysis_report.md",
            b"# Attack path analysis\n",
        ),
        ("artifacts/05_findings/validation_summary.md", b"# Validation summary\n"),
    ):
        _add_manifest_artifact(
            manifest_path, path=path, media_type="application/octet-stream", raw=raw
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scan"]["hardening"] = {"portfolioPath": "hardening/hardening.md"}
    manifest["scan"]["target"]["remote"] = "https://github.com/Katsiarynakavaleuskaya/PulsePlate"
    _write_json(manifest_path, manifest)
    return manifest_path


def test_scan_receipt_validates_real_bundle_and_contains_no_local_path(tmp_path: Path) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")

    receipt = ingest_codex_security_receipt(
        manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
    )

    assert receipt["authority"] == RECEIPT_AUTHORITY
    assert receipt["findings_count"] == 0
    assert str(tmp_path) not in json.dumps(receipt)


def test_scan_receipt_accepts_coverage_without_optional_open_questions(tmp_path: Path) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")
    coverage_path = manifest_path.parent / "coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    del coverage["openQuestions"]
    coverage_raw = _write_json(coverage_path, coverage)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["scan"]["artifacts"]:
        if artifact["path"] == "coverage.json":
            artifact["sha256"] = hashlib.sha256(coverage_raw).hexdigest()
    _write_json(manifest_path, manifest)

    receipt = ingest_codex_security_receipt(
        manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
    )

    assert receipt["coverage_completeness"] == "complete"


def test_scan_receipt_accepts_v011_remote_hardening_and_supplemental_artifacts(
    tmp_path: Path,
) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")

    receipt = ingest_codex_security_receipt(
        manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
    )

    assert set(receipt) == {
        "artifacts",
        "authority",
        "base_revision",
        "coverage_completeness",
        "findings_count",
        "head_revision",
        "manifest_sha256",
        "producer",
        "scan_id",
        "snapshot_digest",
    }
    assert receipt["producer"]["version"] == "0.1.11"
    assert set(receipt["artifacts"]) == {
        "coverage_sha256",
        "findings_sha256",
        "work_ledger_sha256",
    }


def test_scan_receipt_accepts_exact_redundant_diff_revision(tmp_path: Path) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scan"]["target"].update(
        remote="https://github.com/Katsiarynakavaleuskaya/PulsePlate",
        revision=HEAD_SHA,
    )
    _write_json(manifest_path, manifest)

    receipt = ingest_codex_security_receipt(
        manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
    )

    assert receipt["head_revision"] == HEAD_SHA


@pytest.mark.parametrize("revision", [None, True, 1, "f" * 40])
def test_scan_receipt_rejects_non_exact_redundant_diff_revision(
    tmp_path: Path,
    revision: Any,
) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scan"]["target"]["revision"] = revision
    _write_json(manifest_path, manifest)

    with pytest.raises(ReviewEvidenceError, match="revision must exactly match"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_revision_cannot_override_expected_head(tmp_path: Path) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scan"]["target"]["revision"] = HEAD_SHA
    _write_json(manifest_path, manifest)

    with pytest.raises(ReviewEvidenceError, match="expected Git diff"):
        ingest_codex_security_receipt(
            manifest_path,
            expected_base_sha=BASE_SHA,
            expected_head_sha="f" * 40,
        )


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (
            lambda manifest: manifest["scan"]["target"].update(
                remote="https://github.com/example/other"
            ),
            "remote",
        ),
        (lambda manifest: manifest["scan"].update(unexpected=True), "scan keys mismatch"),
        (
            lambda manifest: manifest["scan"]["target"].update(unexpected=True),
            "scan.target keys mismatch",
        ),
        (
            lambda manifest: manifest["scan"].update(hardening={"portfolioPath": "wrong.md"}),
            "hardening",
        ),
        (lambda manifest: manifest["scan"].update(hardening="wrong"), "must be an object"),
        (lambda manifest: manifest["scan"].update(hardening=[]), "must be an object"),
        (lambda manifest: manifest["scan"].update(hardening={}), "scan.hardening keys mismatch"),
        (
            lambda manifest: manifest["scan"].update(
                hardening={"portfolioPath": "hardening/hardening.md", "unexpected": True}
            ),
            "scan.hardening keys mismatch",
        ),
    ],
)
def test_scan_receipt_rejects_invalid_v011_manifest_shape(
    tmp_path: Path, mutate: Any, error: str
) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutate(manifest)
    _write_json(manifest_path, manifest)

    with pytest.raises(ReviewEvidenceError, match=error):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


@pytest.mark.parametrize(
    "canonical_path",
    ["coverage.json", "findings.json", "artifacts/02_discovery/work_ledger.jsonl"],
)
def test_scan_receipt_requires_canonical_artifact_media_types(
    tmp_path: Path, canonical_path: str
) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scan"]["artifacts"] = [
        artifact for artifact in manifest["scan"]["artifacts"] if artifact["path"] != canonical_path
    ]
    _write_json(manifest_path, manifest)

    with pytest.raises(ReviewEvidenceError, match="canonical artifacts"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


@pytest.mark.parametrize(
    ("canonical_path", "wrong_media_type"),
    [
        ("coverage.json", "text/plain"),
        ("findings.json", "text/plain"),
        ("artifacts/02_discovery/work_ledger.jsonl", "application/json"),
    ],
)
def test_scan_receipt_rejects_wrong_canonical_artifact_media_type(
    tmp_path: Path, canonical_path: str, wrong_media_type: str
) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["scan"]["artifacts"]:
        if artifact["path"] == canonical_path:
            artifact["mediaType"] = wrong_media_type
    _write_json(manifest_path, manifest)

    with pytest.raises(ReviewEvidenceError, match="canonical artifacts"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_rejects_supplemental_artifact_hash_drift(tmp_path: Path) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")
    supplemental_path = manifest_path.parent / "artifacts" / "05_findings" / "validation_summary.md"
    supplemental_path.write_text("changed\n", encoding="utf-8")

    with pytest.raises(ReviewEvidenceError, match="artifacts/05_findings/validation_summary.md"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_rejects_empty_supplemental_artifact_media_type(tmp_path: Path) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scan"]["artifacts"][3]["mediaType"] = ""
    _write_json(manifest_path, manifest)

    with pytest.raises(ReviewEvidenceError, match="mediaType must be a non-empty string"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


@pytest.mark.parametrize(
    "path", ["artifacts/02_discovery/finding_discovery_report.md", "../outside.txt"]
)
def test_scan_receipt_rejects_unsafe_supplemental_artifact_paths(tmp_path: Path, path: str) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    supplemental = manifest["scan"]["artifacts"][3]
    supplemental["path"] = path
    if path.startswith("../"):
        (manifest_path.parent.parent / "outside.txt").write_text("outside\n", encoding="utf-8")
    else:
        artifact_path = manifest_path.parent / path
        outside = tmp_path / "outside.md"
        outside.write_bytes(artifact_path.read_bytes())
        artifact_path.unlink()
        artifact_path.symlink_to(outside)
    _write_json(manifest_path, manifest)

    with pytest.raises(ReviewEvidenceError, match="symlink|escapes the scan root"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_rejects_dot_supplemental_artifact_path(tmp_path: Path) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scan"]["artifacts"][3]["path"] = "."
    _write_json(manifest_path, manifest)

    with pytest.raises(ReviewEvidenceError, match="escapes the scan root"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_rejects_fifo_supplemental_artifact_without_blocking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")
    fifo_path = manifest_path.parent / "artifacts" / "05_findings" / "validation_summary.md"
    fifo_path.unlink()
    os.mkfifo(fifo_path)
    original_open = evidence_module.os.open
    nonblocking_flag = os.O_NONBLOCK

    def require_nonblocking_fifo_open(
        path: Any,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path == fifo_path.name:
            assert flags & nonblocking_flag
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(evidence_module.os, "open", require_nonblocking_fifo_open)

    with pytest.raises(ReviewEvidenceError, match="must be a regular file"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_rejects_duplicate_supplemental_artifact_path(tmp_path: Path) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    duplicate = dict(manifest["scan"]["artifacts"][3])
    manifest["scan"]["artifacts"].append(duplicate)
    _write_json(manifest_path, manifest)

    with pytest.raises(ReviewEvidenceError, match="paths must be unique"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_rejects_excessive_artifact_count(tmp_path: Path) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    supplemental_count = (
        evidence_module._MAX_SCAN_ARTIFACTS + 1 - len(manifest["scan"]["artifacts"])
    )
    manifest["scan"]["artifacts"].extend(
        {
            "mediaType": "application/octet-stream",
            "path": f"artifacts/extra/{index}.bin",
            "sha256": "0" * 64,
        }
        for index in range(supplemental_count)
    )
    _write_json(manifest_path, manifest)

    with pytest.raises(ReviewEvidenceError, match="artifact count exceeds limit"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_rejects_excessive_aggregate_artifact_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    aggregate_bytes = sum(
        (manifest_path.parent / artifact["path"]).stat().st_size
        for artifact in manifest["scan"]["artifacts"]
    )
    monkeypatch.setattr(
        evidence_module,
        "_MAX_TOTAL_SCAN_ARTIFACT_BYTES",
        aggregate_bytes - 1,
    )

    with pytest.raises(ReviewEvidenceError, match="aggregate size exceeds limit"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_streams_non_json_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _build_v011_scan_bundle(tmp_path / "scan")
    original_reader = evidence_module._read_contained_artifact_from_descriptor

    def reject_buffered_non_json(descriptor: int, relative: Any, *, max_bytes: int) -> bytes:
        if str(relative) not in {
            "scan-manifest.json",
            "coverage.json",
            "findings.json",
        }:
            raise AssertionError(f"buffered non-JSON artifact: {relative}")
        return original_reader(descriptor, relative, max_bytes=max_bytes)

    monkeypatch.setattr(
        evidence_module,
        "_read_contained_artifact_from_descriptor",
        reject_buffered_non_json,
    )

    receipt = ingest_codex_security_receipt(
        manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
    )

    assert receipt["findings_count"] == 0


def test_scan_receipt_rejects_symlinked_artifact(tmp_path: Path) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")
    coverage_path = manifest_path.parent / "coverage.json"
    outside = tmp_path / "outside.json"
    outside.write_bytes(coverage_path.read_bytes())
    coverage_path.unlink()
    coverage_path.symlink_to(outside)

    with pytest.raises(ReviewEvidenceError, match="symlink"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_rejects_symlinked_manifest(tmp_path: Path) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")
    outside = tmp_path / "outside-manifest.json"
    outside.write_bytes(manifest_path.read_bytes())
    manifest_path.unlink()
    manifest_path.symlink_to(outside)

    with pytest.raises(ReviewEvidenceError, match="symlink"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def test_scan_receipt_uses_one_stable_root_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "scan"
    manifest_path = _build_scan_bundle(root)
    original_reader = evidence_module._read_contained_artifact_from_descriptor
    swapped = False

    def swap_root_after_manifest(descriptor: int, relative: Any, *, max_bytes: int) -> bytes:
        nonlocal swapped
        raw = original_reader(descriptor, relative, max_bytes=max_bytes)
        if str(relative) == "scan-manifest.json" and not swapped:
            swapped = True
            root.rename(tmp_path / "original-scan")
            root.mkdir()
            (root / "coverage.json").write_text("{}", encoding="utf-8")
        return raw

    monkeypatch.setattr(
        evidence_module,
        "_read_contained_artifact_from_descriptor",
        swap_root_after_manifest,
    )
    receipt = ingest_codex_security_receipt(
        manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
    )
    assert receipt["coverage_completeness"] == "complete"


def test_scan_receipt_rejects_hash_drift(tmp_path: Path) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")
    (manifest_path.parent / "findings.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ReviewEvidenceError, match="hash mismatch"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def _seal(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "authority": RECEIPT_AUTHORITY,
        "code_review": {
            "review_commit_ref": HEAD_SHA,
            "review_commit_ref_kind": "repository_commit",
            "review_reference": "https://github.com/owner/repo/pull/42#pullrequestreview-1",
            "reviewed_material_digest": DIGEST,
            "status": "completed",
        },
        "codex_security": receipt,
        "material": {
            "base_ref_oid": BASE_SHA,
            "digest": DIGEST,
            "material_head_sha": HEAD_SHA,
            "merge_base_sha": BASE_SHA,
            "policy_version": MATERIAL_POLICY_VERSION,
        },
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": "pulseplate.pr-review-seal/v1",
    }


def _review_source_unavailability_receipt(
    *,
    material_digest: str = DIGEST,
    material_head_sha: str = HEAD_SHA,
) -> dict[str, Any]:
    response = _review_credit_quota_comment(
        "https://github.com/owner/repo/pull/42#issuecomment-456"
    )
    return build_review_source_unavailability_receipt(
        material_digest=material_digest,
        material_head_sha=material_head_sha,
        quota_reference=response["html_url"],
        quota_created_at=response["created_at"],
        quota_body_sha256=(
            "sha256:" + hashlib.sha256(response["body"].encode("utf-8")).hexdigest()
        ),
        source_status="usage_limit_reached",
    )


def test_review_source_unavailability_receipt_is_tagged_and_material_bound() -> None:
    receipt = _review_source_unavailability_receipt()
    seal = _seal(
        build_security_outage_override_receipt(
            base_revision=BASE_SHA,
            head_revision=HEAD_SHA,
            material_digest=DIGEST,
            override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
            created_at="2026-07-15T11:00:00Z",
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
        )
    )
    seal["code_review"] = receipt

    parsed = parse_embedded_review_seal(render_embedded_review_seal(seal))

    assert is_review_source_unavailability_receipt(parsed["code_review"])
    assert parsed["code_review"] == {
        "authority": "trusted_codex_review_source_unavailability",
        "binding_kind": "seal_context_only",
        "blocking": False,
        "fallback_required": False,
        "material_digest": DIGEST,
        "material_head_sha": HEAD_SHA,
        "quota_body_sha256": receipt["quota_body_sha256"],
        "quota_created_at": "2026-07-15T11:05:00Z",
        "quota_reference": "https://github.com/owner/repo/pull/42#issuecomment-456",
        "review_claim": "none",
        "schema_version": "pulseplate.codex-review-source-unavailability/v1",
        "source": "codex_review",
        "source_degraded": True,
        "source_status": "usage_limit_reached",
        "status": "tooling_unavailable",
    }


@pytest.mark.parametrize("reaction_content", ["+1", "heart", "hooray", "rocket"])
def test_review_source_positive_response_receipt_is_nonblocking_without_review_claim(
    reaction_content: str,
) -> None:
    receipt = build_review_source_positive_response_receipt(
        material_digest=DIGEST,
        material_head_sha=HEAD_SHA,
        response_reference="https://github.com/owner/repo/pull/42#reaction-456",
        response_created_at="2026-07-15T11:00:00Z",
        response_content=reaction_content,
    )
    seal = _seal(
        build_security_outage_override_receipt(
            base_revision=BASE_SHA,
            head_revision=HEAD_SHA,
            material_digest=DIGEST,
            override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
            created_at="2026-07-15T11:00:00Z",
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
        )
    )
    seal["code_review"] = receipt

    parsed = parse_embedded_review_seal(render_embedded_review_seal(seal))

    assert is_review_source_positive_response_receipt(parsed["code_review"])
    assert parsed["code_review"] == {
        "authority": "trusted_codex_review_source_positive_response",
        "binding_kind": "seal_context_only",
        "blocking": False,
        "fallback_required": False,
        "material_digest": DIGEST,
        "material_head_sha": HEAD_SHA,
        "response_content": reaction_content,
        "response_created_at": "2026-07-15T11:00:00Z",
        "response_reference": "https://github.com/owner/repo/pull/42#reaction-456",
        "review_claim": "none",
        "schema_version": "pulseplate.codex-review-source-positive-response/v1",
        "source": "codex_review",
        "source_degraded": False,
        "source_status": "positive_response",
        "status": "completed",
    }


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (lambda receipt: receipt.update(review_claim="approved"), "malformed or stale"),
        (lambda receipt: receipt.update(source_degraded=True), "malformed or stale"),
        (lambda receipt: receipt.update(response_content="eyes"), "malformed or stale"),
        (lambda receipt: receipt.update(response_content=[]), "malformed or stale"),
        (
            lambda receipt: receipt.update(authority="trusted_codex_review_source_unavailability"),
            "tagged-union identity is ambiguous",
        ),
    ],
)
def test_review_source_positive_response_receipt_rejects_authority_escalation(
    mutation: Any, error: str
) -> None:
    receipt = build_review_source_positive_response_receipt(
        material_digest=DIGEST,
        material_head_sha=HEAD_SHA,
        response_reference="https://github.com/owner/repo/pull/42#reaction-456",
        response_created_at="2026-07-15T11:00:00Z",
        response_content="+1",
    )
    mutation(receipt)
    seal = _seal(
        build_security_outage_override_receipt(
            base_revision=BASE_SHA,
            head_revision=HEAD_SHA,
            material_digest=DIGEST,
            override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
            created_at="2026-07-15T11:00:00Z",
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
        )
    )
    seal["code_review"] = receipt

    with pytest.raises(ReviewEvidenceError, match=error):
        render_embedded_review_seal(seal)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (
            lambda receipt: receipt.update(source_status="unknown"),
            "malformed or stale",
        ),
        (
            lambda receipt: receipt.update(review_claim="no_findings"),
            "malformed or stale",
        ),
        (
            lambda receipt: receipt.update(review_reference="legacy"),
            "keys mismatch",
        ),
        (
            lambda receipt: receipt.update(quota_body_sha256="sha256:invalid"),
            "64 lowercase hex",
        ),
        (
            lambda receipt: receipt.update(authority="operator_review_credit_exhaustion_override"),
            "tagged-union identity is ambiguous",
        ),
    ],
)
def test_review_source_unavailability_receipt_rejects_ambiguous_or_unsafe_fields(
    mutation: Any,
    error: str,
) -> None:
    receipt = _review_source_unavailability_receipt()
    mutation(receipt)
    seal = _seal(
        build_security_outage_override_receipt(
            base_revision=BASE_SHA,
            head_revision=HEAD_SHA,
            material_digest=DIGEST,
            override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
            created_at="2026-07-15T11:00:00Z",
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
        )
    )
    seal["code_review"] = receipt

    with pytest.raises(ReviewEvidenceError, match=error):
        render_embedded_review_seal(seal)


def test_review_source_unavailability_receipt_rejects_stale_material_binding() -> None:
    receipt = _review_source_unavailability_receipt(material_head_sha=FIX_SHA)
    seal = _seal(
        build_security_outage_override_receipt(
            base_revision=BASE_SHA,
            head_revision=HEAD_SHA,
            material_digest=DIGEST,
            override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
            created_at="2026-07-15T11:00:00Z",
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
        )
    )
    seal["code_review"] = receipt

    with pytest.raises(ReviewEvidenceError, match="sealed material head"):
        render_embedded_review_seal(seal)


def _mapping_artifact_with_seal(seal: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PR 42 — Review Governance",
            "",
            "Review-Seal-Version: v1",
            "",
            "## Discussion Thread Pass",
            "- [x] Discussion-thread pass completed",
            "- [x] Fixed in commit mapping completed",
            "",
            "## Fixed in Commit Mapping",
            "- No actionable review comments",
            "",
            "## Review Material Seal",
            render_embedded_review_seal(seal),
            "",
        ]
    )


def test_closeout_seal_authors_terminal_review_source_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    target = repo / "docs/review/PR_42_FIXED_MAPPING.md"
    freeze = {
        "base_ref_oid": BASE_SHA,
        "digest": DIGEST,
        "material_head_sha": HEAD_SHA,
        "merge_base_sha": BASE_SHA,
        "policy_version": MATERIAL_POLICY_VERSION,
    }
    state = {
        "dispositions": [],
        "experiment_result": None,
        "freeze": freeze,
        "packet": None,
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": closeout_module.DRAFT_SCHEMA_VERSION,
    }
    source_evidence = CodexReviewSourceUnavailabilityEvidence(
        reference="https://github.com/owner/repo/pull/42#issuecomment-456",
        created_at="2020-01-01T00:00:00Z",
        source_status="usage_limit_reached",
        body_sha256="sha256:" + "c" * 64,
    )
    security_receipt = build_security_outage_override_receipt(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
        override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
        created_at="2026-07-15T11:00:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )
    monkeypatch.setattr(closeout_module, "REPO_ROOT", repo)
    monkeypatch.setattr(closeout_module, "_load_state", lambda _pr: state)
    monkeypatch.setattr(closeout_module, "_token", lambda: "opaque")
    monkeypatch.setattr(closeout_module, "fetch_pr_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(closeout_module, "_require_clean_live_head", lambda _head: None)
    monkeypatch.setattr(
        closeout_module,
        "compute_material_manifest",
        lambda *_a, **_k: _material_manifest(HEAD_SHA),
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_source_unavailability_reference",
        lambda *_a, **_k: source_evidence,
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_reference",
        lambda *_a, **_k: pytest.fail("normal review path must not run"),
    )

    def unavailable_advisory_reaction(*_args: Any, **_kwargs: Any) -> Any:
        raise CommitIdentityError("GitHub reaction not found")

    monkeypatch.setattr(
        closeout_module,
        "verify_codex_connector_advisory_reaction_reference",
        unavailable_advisory_reaction,
    )
    monkeypatch.setattr(
        closeout_module,
        "ingest_codex_security_receipt",
        lambda *_a, **_k: security_receipt,
    )
    monkeypatch.setattr(
        closeout_module,
        "_require_completed_final_security_preparation",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        closeout_module,
        "_render_mapping",
        lambda _state, seal: _mapping_artifact_with_seal(seal),
    )
    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: target)
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: "")
    monkeypatch.setattr(closeout_module, "assert_snapshot_unchanged", lambda *_a, **_k: None)
    args = Namespace(
        pr_number=42,
        repo="owner/repo",
        review_ref=None,
        review_source_unavailable_ref=source_evidence.reference,
        connector_advisory_reaction=[
            "https://github.com/owner/repo/pull/42#reaction-456",
        ],
        scan_manifest="/tmp/scan-manifest.json",
        security_outage_override_ref=None,
    )

    closeout_module._cmd_seal(args)

    parsed = parse_embedded_review_seal(target.read_text(encoding="utf-8"))
    assert parsed["code_review"]["authority"] == ("trusted_codex_review_source_unavailability")
    assert parsed["code_review"]["review_claim"] == "none"
    captured = capsys.readouterr()
    assert "CONTENT_BOUND_RECEIPT_VALID" in captured.out
    assert "WARNING: Connector advisory reaction omitted: GitHub reaction not found" in captured.err


@pytest.mark.parametrize("reaction_content", ["+1", "heart", "hooray", "rocket"])
def test_closeout_seal_records_connector_reaction_as_positive_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reaction_content: str,
) -> None:
    repo = tmp_path / "repo"
    target = repo / "docs/review/PR_42_FIXED_MAPPING.md"
    reaction_reference = "https://github.com/owner/repo/pull/42#reaction-456"
    freeze = {
        "base_ref_oid": BASE_SHA,
        "digest": DIGEST,
        "material_head_sha": HEAD_SHA,
        "merge_base_sha": BASE_SHA,
        "policy_version": MATERIAL_POLICY_VERSION,
    }
    state = {
        "dispositions": [],
        "experiment_result": None,
        "freeze": freeze,
        "packet": None,
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": closeout_module.DRAFT_SCHEMA_VERSION,
    }
    security_receipt = build_security_outage_override_receipt(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
        override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
        created_at="2026-07-15T11:00:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )
    review_calls: list[tuple[str, str | None]] = []
    snapshot_rechecks: list[PrSnapshot] = []

    def verify_reaction_review(
        reference: str, **kwargs: Any
    ) -> identity_module.CodexConnectorAdvisoryReactionEvidence:
        review_calls.append((reference, kwargs.get("expected_commit_ref")))
        return identity_module.CodexConnectorAdvisoryReactionEvidence(
            reference=reaction_reference,
            created_at="2026-07-15T11:00:00Z",
            content=reaction_content,
        )

    monkeypatch.setattr(closeout_module, "REPO_ROOT", repo)
    monkeypatch.setattr(closeout_module, "_load_state", lambda _pr: state)
    monkeypatch.setattr(closeout_module, "_token", lambda: "opaque")
    monkeypatch.setattr(closeout_module, "fetch_pr_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(closeout_module, "_require_clean_live_head", lambda _head: None)
    monkeypatch.setattr(
        closeout_module,
        "compute_material_manifest",
        lambda *_a, **_k: _material_manifest(HEAD_SHA),
    )
    monkeypatch.setattr(closeout_module, "verify_codex_review_reference", verify_reaction_review)
    monkeypatch.setattr(
        closeout_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_HEAD),
    )
    monkeypatch.setattr(
        closeout_module,
        "ingest_codex_security_receipt",
        lambda *_a, **_k: security_receipt,
    )
    monkeypatch.setattr(
        closeout_module,
        "_require_completed_final_security_preparation",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        closeout_module,
        "_render_mapping",
        lambda _state, seal: _mapping_artifact_with_seal(seal),
    )
    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: target)
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: "")
    monkeypatch.setattr(
        closeout_module,
        "assert_snapshot_unchanged",
        lambda snapshot, **_k: snapshot_rechecks.append(snapshot),
    )

    closeout_module._cmd_seal(
        Namespace(
            pr_number=42,
            repo="owner/repo",
            review_ref=reaction_reference,
            review_source_unavailable_ref=None,
            connector_advisory_reaction=[],
            scan_manifest="/tmp/scan-manifest.json",
            security_outage_override_ref=None,
        )
    )

    seal = parse_embedded_review_seal(target.read_text(encoding="utf-8"))
    assert review_calls == [(reaction_reference, HEAD_SHA)]
    assert seal["code_review"] == build_review_source_positive_response_receipt(
        material_digest=DIGEST,
        material_head_sha=HEAD_SHA,
        response_reference=reaction_reference,
        response_created_at="2026-07-15T11:00:00Z",
        response_content=reaction_content,
    )
    assert seal["codex_security"] == security_receipt
    assert snapshot_rechecks == [_snapshot()]


def test_authenticated_closeout_rejects_reaction_in_exact_review_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = ingest_codex_security_receipt(
        _build_scan_bundle(tmp_path / "scan"),
        expected_base_sha=BASE_SHA,
        expected_head_sha=HEAD_SHA,
    )
    reaction_reference = "https://github.com/owner/repo/pull/42#reaction-456"
    seal = _seal(receipt)
    seal["code_review"]["review_reference"] = reaction_reference
    mapping = tmp_path / "PR_42_FIXED_MAPPING.md"
    mapping.write_text(_mapping_artifact_with_seal(seal), encoding="utf-8")
    manifest = MaterialManifest(
        base_ref_oid=BASE_SHA,
        head_ref_oid=HEAD_SHA,
        merge_base_sha=BASE_SHA,
        pr_number=42,
        entries=(),
        digest=DIGEST,
    )
    verifier_calls: list[tuple[str, str | None, str | None]] = []

    def return_positive_response(reference: str, **kwargs: Any) -> Any:
        verifier_calls.append(
            (
                reference,
                kwargs.get("expected_commit_ref"),
                kwargs.get("expected_live_pr_head_ref"),
            )
        )
        return identity_module.CodexConnectorAdvisoryReactionEvidence(
            reference=reference,
            created_at="2026-07-15T11:00:00Z",
            content="+1",
        )

    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: mapping)
    monkeypatch.setattr(closeout_module, "fetch_pr_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: HEAD_SHA)
    monkeypatch.setattr(
        closeout_module,
        "compute_material_manifest",
        lambda *_a, **_k: manifest,
    )
    monkeypatch.setattr(
        closeout_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_HEAD),
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_reference",
        return_positive_response,
    )
    monkeypatch.setattr(closeout_module, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(closeout_module, "assert_snapshot_unchanged", lambda *_a, **_k: None)

    with pytest.raises(closeout_module.CloseoutError, match="not exact-head review evidence"):
        closeout_module.validate_live_mapping(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )

    assert verifier_calls == [(reaction_reference, HEAD_SHA, HEAD_SHA)]


@pytest.mark.parametrize("reaction_content", ["+1", "heart", "hooray", "rocket"])
def test_authenticated_closeout_revalidates_reaction_after_mapping_only_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reaction_content: str
) -> None:
    receipt = ingest_codex_security_receipt(
        _build_scan_bundle(tmp_path / "scan"),
        expected_base_sha=BASE_SHA,
        expected_head_sha=HEAD_SHA,
    )
    reaction_reference = "https://github.com/owner/repo/pull/42#reaction-456"
    seal = _seal(receipt)
    seal["code_review"] = build_review_source_positive_response_receipt(
        material_digest=DIGEST,
        material_head_sha=HEAD_SHA,
        response_reference=reaction_reference,
        response_created_at="2026-07-15T11:00:00Z",
        response_content=reaction_content,
    )
    mapping = tmp_path / "PR_42_FIXED_MAPPING.md"
    mapping.write_text(_mapping_artifact_with_seal(seal), encoding="utf-8")
    closeout_snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=BASE_SHA,
        head_sha=OUTSIDE_SHA,
        commits=(
            PrCommitEvidence(HEAD_SHA, "2026-07-15T11:00:00Z"),
            PrCommitEvidence(OUTSIDE_SHA, "2026-07-15T12:00:00Z"),
        ),
    )
    successor_reference = "https://github.com/owner/repo/pull/42#reaction-789"
    verifier_calls: list[tuple[str, str | None, str | None]] = []

    def verify_reaction(reference: str, **kwargs: Any) -> Any:
        verifier_calls.append(
            (
                reference,
                kwargs.get("expected_commit_ref"),
                kwargs.get("expected_live_pr_head_ref"),
            )
        )
        return identity_module.CodexConnectorAdvisoryReactionEvidence(
            reference=successor_reference,
            created_at="2026-07-15T12:00:00Z",
            content=reaction_content,
        )

    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: mapping)
    monkeypatch.setattr(
        closeout_module,
        "fetch_pr_snapshot",
        lambda *_a, **_k: closeout_snapshot,
    )
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: OUTSIDE_SHA)
    monkeypatch.setattr(
        closeout_module,
        "compute_material_manifest",
        lambda *_a, **kwargs: _material_manifest(kwargs["head_ref_oid"]),
    )
    monkeypatch.setattr(
        closeout_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD if value == OUTSIDE_SHA else CommitRefKind.PR_COMMIT,
        ),
    )
    monkeypatch.setattr(closeout_module, "verify_codex_review_reference", verify_reaction)
    monkeypatch.setattr(closeout_module, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(closeout_module, "assert_snapshot_unchanged", lambda *_a, **_k: None)

    validated = closeout_module.validate_live_mapping(
        repository="owner/repo",
        pr_number=42,
        token="opaque",
    )

    assert validated["code_review"]["response_reference"] == reaction_reference
    assert verifier_calls == [(reaction_reference, HEAD_SHA, OUTSIDE_SHA)]

    stale_seal = parse_embedded_review_seal(mapping.read_text(encoding="utf-8"))
    stale_seal["code_review"]["response_content"] = "heart" if reaction_content != "heart" else "+1"
    mapping.write_text(_mapping_artifact_with_seal(stale_seal), encoding="utf-8")
    with pytest.raises(closeout_module.CloseoutError, match="positive response receipt is stale"):
        closeout_module.validate_live_mapping(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )

    mapping.write_text(_mapping_artifact_with_seal(seal), encoding="utf-8")

    def manifest_for_head(
        _root: Path,
        *,
        base_ref_oid: str,
        head_ref_oid: str,
        pr_number: int,
    ) -> MaterialManifest:
        assert base_ref_oid == BASE_SHA
        assert pr_number == 42
        if head_ref_oid == OUTSIDE_SHA:
            return _material_manifest(OUTSIDE_SHA, digest=DIGEST)
        assert head_ref_oid == HEAD_SHA
        return _material_manifest(HEAD_SHA, digest="sha256:" + "d" * 64)

    monkeypatch.setattr(closeout_module, "compute_material_manifest", manifest_for_head)
    with pytest.raises(
        closeout_module.CloseoutError,
        match="positive response material head has a different material digest",
    ):
        closeout_module.validate_live_mapping(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


def test_authenticated_closeout_revalidates_operator_outage_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = build_security_outage_override_receipt(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
        override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
        created_at="2026-07-15T11:00:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )
    mapping = tmp_path / "PR_42_FIXED_MAPPING.md"
    mapping.write_text(_mapping_artifact_with_seal(_seal(receipt)), encoding="utf-8")
    manifest = MaterialManifest(
        base_ref_oid=BASE_SHA,
        head_ref_oid=HEAD_SHA,
        merge_base_sha=BASE_SHA,
        pr_number=42,
        entries=(),
        digest=DIGEST,
    )
    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: mapping)
    monkeypatch.setattr(closeout_module, "fetch_pr_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: HEAD_SHA)
    monkeypatch.setattr(
        closeout_module,
        "compute_material_manifest",
        lambda *_a, **_k: manifest,
    )
    monkeypatch.setattr(
        closeout_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_HEAD),
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_reference",
        lambda *_a, **_k: identity_module.CodexReviewEvidence(
            reference="https://github.com/owner/repo/pull/42#pullrequestreview-1",
            submitted_at="2026-07-15T11:00:00Z",
            commit_ref=HEAD_SHA,
        ),
    )
    override_calls: list[tuple[str, str]] = []

    def verify_override(*_args: Any, **kwargs: Any) -> SecurityOutageOverrideEvidence:
        override_calls.append(
            (kwargs["expected_material_head_sha"], kwargs["expected_material_digest"])
        )
        return SecurityOutageOverrideEvidence(
            reference=receipt["override_reference"],
            created_at=receipt["created_at"],
            operator_user_id=receipt["operator_user_id"],
            operator_login=receipt["operator_login"],
            operator_association=receipt["operator_association"],
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
        )

    monkeypatch.setattr(
        closeout_module,
        "verify_security_outage_override_reference",
        verify_override,
    )
    monkeypatch.setattr(closeout_module, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(closeout_module, "assert_snapshot_unchanged", lambda *_a, **_k: None)

    seal = closeout_module.validate_live_mapping(
        repository="owner/repo",
        pr_number=42,
        token="opaque",
    )

    assert seal["codex_security"] == receipt
    assert override_calls == [(HEAD_SHA, DIGEST)]


def test_authenticated_closeout_recomputes_quota_body_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    code_review = _review_source_unavailability_receipt()
    security_receipt = ingest_codex_security_receipt(
        _build_scan_bundle(tmp_path / "scan"),
        expected_base_sha=BASE_SHA,
        expected_head_sha=HEAD_SHA,
    )
    seal = _seal(security_receipt)
    seal["code_review"] = code_review
    mapping = tmp_path / "PR_42_FIXED_MAPPING.md"
    mapping.write_text(_mapping_artifact_with_seal(seal), encoding="utf-8")
    manifest = _material_manifest(HEAD_SHA)
    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: mapping)
    monkeypatch.setattr(closeout_module, "fetch_pr_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: HEAD_SHA)
    monkeypatch.setattr(
        closeout_module,
        "compute_material_manifest",
        lambda *_a, **_k: manifest,
    )
    monkeypatch.setattr(
        closeout_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_HEAD),
    )
    monkeypatch.setattr(closeout_module, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(closeout_module, "assert_snapshot_unchanged", lambda *_a, **_k: None)
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_reference",
        lambda *_a, **_k: pytest.fail("normal review path must not run"),
    )
    evidence = CodexReviewSourceUnavailabilityEvidence(
        reference=code_review["quota_reference"],
        created_at=code_review["quota_created_at"],
        source_status=code_review["source_status"],
        body_sha256=code_review["quota_body_sha256"],
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_source_unavailability_reference",
        lambda *_a, **_k: evidence,
    )

    validated = closeout_module.validate_live_mapping(
        repository="owner/repo",
        pr_number=42,
        token="opaque",
    )
    assert validated["code_review"] == code_review

    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_source_unavailability_reference",
        lambda *_a, **_k: CodexReviewSourceUnavailabilityEvidence(
            reference=evidence.reference,
            created_at=evidence.created_at,
            source_status=evidence.source_status,
            body_sha256="sha256:" + "f" * 64,
        ),
    )
    with pytest.raises(closeout_module.CloseoutError, match="receipt is stale"):
        closeout_module.validate_live_mapping(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


def test_authenticated_closeout_rejects_unavailable_receipt_with_ancestor_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    live_digest = DIGEST
    ancestor_digest = "sha256:" + "d" * 64
    code_review = _review_source_unavailability_receipt(
        material_digest=live_digest,
        material_head_sha=FIX_SHA,
    )
    security_receipt = build_security_outage_override_receipt(
        base_revision=BASE_SHA,
        head_revision=FIX_SHA,
        material_digest=live_digest,
        override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
        created_at="2026-07-15T11:00:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )
    seal = _seal(security_receipt)
    seal["code_review"] = code_review
    seal["material"]["digest"] = live_digest
    seal["material"]["material_head_sha"] = FIX_SHA
    mapping = tmp_path / "PR_42_FIXED_MAPPING.md"
    mapping.write_text(_mapping_artifact_with_seal(seal), encoding="utf-8")

    def manifest_for_head(
        _root: Path,
        *,
        base_ref_oid: str,
        head_ref_oid: str,
        pr_number: int,
    ) -> MaterialManifest:
        assert base_ref_oid == BASE_SHA
        assert pr_number == 42
        if head_ref_oid == HEAD_SHA:
            return _material_manifest(HEAD_SHA, digest=live_digest)
        assert head_ref_oid == FIX_SHA
        return _material_manifest(FIX_SHA, digest=ancestor_digest)

    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: mapping)
    monkeypatch.setattr(closeout_module, "fetch_pr_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: HEAD_SHA)
    monkeypatch.setattr(closeout_module, "compute_material_manifest", manifest_for_head)
    monkeypatch.setattr(
        closeout_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD if value == HEAD_SHA else CommitRefKind.PR_COMMIT,
        ),
    )

    with pytest.raises(
        closeout_module.CloseoutError,
        match="unavailable material head has a different material digest",
    ):
        closeout_module.validate_live_mapping(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


def test_authenticated_closeout_revalidates_review_credit_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = "Katsiarynakavaleuskaya/PulsePlate"
    pr_number = 2142
    quota_reference = f"https://github.com/{repository}/pull/{pr_number}#issuecomment-456"
    override_reference = f"https://github.com/{repository}/pull/{pr_number}#issuecomment-654"
    prior_reference = f"https://github.com/{repository}/pull/{pr_number}#pullrequestreview-123"
    operator_reference = f"https://github.com/{repository}/pull/{pr_number}#pullrequestreview-789"
    code_review = build_review_credit_outage_receipt(
        material_digest=DIGEST,
        material_head_sha=HEAD_SHA,
        override_reference=override_reference,
        override_created_at="2026-07-15T11:15:00Z",
        quota_reference=quota_reference,
        quota_created_at="2026-07-15T11:05:00Z",
        prior_review_reference=prior_reference,
        prior_review_submitted_at="2026-07-15T10:30:00Z",
        prior_review_commit_ref=FIX_SHA,
        operator_review_reference=operator_reference,
        operator_review_submitted_at="2026-07-15T11:10:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )
    security_receipt = build_security_outage_override_receipt(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
        override_reference=(f"https://github.com/{repository}/pull/{pr_number}#issuecomment-789"),
        created_at="2026-07-15T11:00:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )
    seal = _seal(security_receipt)
    seal["repository"] = repository
    seal["pr_number"] = pr_number
    seal["code_review"] = code_review
    mapping = tmp_path / f"PR_{pr_number}_FIXED_MAPPING.md"
    mapping.write_text(_mapping_artifact_with_seal(seal), encoding="utf-8")
    manifest = MaterialManifest(
        base_ref_oid=BASE_SHA,
        head_ref_oid=HEAD_SHA,
        merge_base_sha=BASE_SHA,
        pr_number=pr_number,
        entries=(),
        digest=DIGEST,
    )
    snapshot = PrSnapshot(
        repository=repository,
        pr_number=pr_number,
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        commits=(
            PrCommitEvidence(FIX_SHA, "2026-07-15T10:00:00Z"),
            PrCommitEvidence(HEAD_SHA, "2026-07-15T11:00:00Z"),
        ),
    )
    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: mapping)
    monkeypatch.setattr(closeout_module, "fetch_pr_snapshot", lambda *_a, **_k: snapshot)
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: HEAD_SHA)
    monkeypatch.setattr(
        closeout_module,
        "compute_material_manifest",
        lambda *_a, **_k: manifest,
    )
    monkeypatch.setattr(
        closeout_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD if value == HEAD_SHA else CommitRefKind.PR_COMMIT,
        ),
    )
    credit_calls: list[tuple[str, str]] = []

    def verify_credit(*_args: Any, **kwargs: Any) -> ReviewCreditOutageEvidence:
        credit_calls.append(
            (kwargs["expected_material_head_sha"], kwargs["expected_material_digest"])
        )
        return ReviewCreditOutageEvidence(
            override_reference=override_reference,
            override_created_at="2026-07-15T11:15:00Z",
            quota_reference=quota_reference,
            quota_created_at="2026-07-15T11:05:00Z",
            prior_review_reference=prior_reference,
            prior_review_submitted_at="2026-07-15T10:30:00Z",
            prior_review_commit_ref=FIX_SHA,
            operator_review_reference=operator_reference,
            operator_review_submitted_at="2026-07-15T11:10:00Z",
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
        )

    monkeypatch.setattr(
        closeout_module,
        "verify_review_credit_outage_references",
        verify_credit,
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_security_outage_override_reference",
        lambda *_a, **_k: SecurityOutageOverrideEvidence(
            reference=security_receipt["override_reference"],
            created_at=security_receipt["created_at"],
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
        ),
    )
    monkeypatch.setattr(closeout_module, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(closeout_module, "assert_snapshot_unchanged", lambda *_a, **_k: None)

    validated = closeout_module.validate_live_mapping(
        repository=repository,
        pr_number=pr_number,
        token="opaque",
    )

    assert validated["code_review"] == code_review
    assert credit_calls == [(HEAD_SHA, DIGEST)]


def test_embedded_seal_round_trip_is_strict_and_canonical(tmp_path: Path) -> None:
    receipt = ingest_codex_security_receipt(
        _build_scan_bundle(tmp_path / "scan"),
        expected_base_sha=BASE_SHA,
        expected_head_sha=HEAD_SHA,
    )
    rendered = render_embedded_review_seal(_seal(receipt))

    assert rendered.splitlines()[1] == "<!-- pragma: allowlist nextline secret -->"
    assert parse_embedded_review_seal(rendered) == _seal(receipt)

    noncanonical = rendered.replace('"authority":', '"authority" :', 1)
    with pytest.raises(ReviewEvidenceError, match="not canonical"):
        parse_embedded_review_seal(noncanonical)


def test_closeout_no_actionable_marker_is_not_persistent_reseal_proof() -> None:
    existing = (
        "## Fixed in Commit Mapping\n\n" f"{NO_ACTIONABLE_LINE}\n\n" "## Review Material Seal\n"
    )
    proof = (
        "Disposition: NOT-A-BUG\n"
        "Evidence: tests/test_example.py:10\n"
        "Reason: Exact contract remains satisfied.\n"
        "- https://github.com/owner/repo/pull/42#discussion_r1"
    )
    replacement = "## Fixed in Commit Mapping\n\n" f"{proof}\n\n" "## Review Material Seal\n"

    assert closeout_module._mapping_proof_blocks(existing) == set()
    assert closeout_module._mapping_proof_blocks(replacement) == {proof}


def test_closeout_reseal_requires_new_material_and_preserves_existing_proof() -> None:
    old_receipt = build_security_outage_override_receipt(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
        override_reference="https://github.com/owner/repo/pull/42#issuecomment-1",
        created_at="2026-07-15T11:00:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )
    new_digest = "sha256:" + "b" * 64
    new_receipt = build_security_outage_override_receipt(
        base_revision=BASE_SHA,
        head_revision=OUTSIDE_SHA,
        material_digest=new_digest,
        override_reference="https://github.com/owner/repo/pull/42#issuecomment-2",
        created_at="2026-07-15T12:00:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )
    old_seal = _seal(old_receipt)
    new_seal = _seal(new_receipt)
    new_seal["code_review"]["review_commit_ref"] = OUTSIDE_SHA
    new_seal["code_review"]["reviewed_material_digest"] = new_digest
    new_seal["material"]["digest"] = new_digest
    new_seal["material"]["material_head_sha"] = OUTSIDE_SHA
    existing_disposition = {
        "commit": FIX_SHA,
        "disposition": "FIXED",
        "evidence": "tests/test_example.py:10",
        "url": "https://github.com/owner/repo/pull/42#discussion_r1",
    }
    new_disposition = {
        "commit": OUTSIDE_SHA,
        "disposition": "FIXED",
        "evidence": "tests/test_example.py:20",
        "url": "https://github.com/owner/repo/pull/42#discussion_r2",
    }
    state = {
        "dispositions": [existing_disposition],
        "experiment_result": None,
        "packet": None,
        "pr_number": 42,
    }
    existing = closeout_module._render_mapping(state, old_seal)
    replacement = closeout_module._render_mapping(
        {**state, "dispositions": [existing_disposition, new_disposition]},
        new_seal,
    )
    expected_freeze = new_seal["material"]

    assert (
        closeout_module._validate_reseal_transition(
            existing,
            replacement,
            repository="owner/repo",
            pr_number=42,
            expected_freeze=expected_freeze,
        )
        == HEAD_SHA
    )
    with pytest.raises(closeout_module.CloseoutError, match="already seals this material"):
        closeout_module._validate_reseal_transition(
            replacement,
            replacement,
            repository="owner/repo",
            pr_number=42,
            expected_freeze=expected_freeze,
        )
    with pytest.raises(
        closeout_module.CloseoutError,
        match="drop existing disposition proof",
    ):
        closeout_module._validate_reseal_transition(
            existing,
            closeout_module._render_mapping(
                {**state, "dispositions": [new_disposition]},
                new_seal,
            ),
            repository="owner/repo",
            pr_number=42,
            expected_freeze=expected_freeze,
        )


def test_closeout_reseal_allows_only_proven_fast_forward_base_advance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    next_base = "6" * 40
    next_head = "7" * 40
    old_seal = _seal(
        build_security_outage_override_receipt(
            base_revision=BASE_SHA,
            head_revision=HEAD_SHA,
            material_digest=DIGEST,
            override_reference="https://github.com/owner/repo/pull/42#issuecomment-1",
            created_at="2026-07-15T11:00:00Z",
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
        )
    )
    next_digest = "sha256:" + "c" * 64
    new_seal = _seal(
        build_security_outage_override_receipt(
            base_revision=next_base,
            head_revision=next_head,
            material_digest=next_digest,
            override_reference="https://github.com/owner/repo/pull/42#issuecomment-2",
            created_at="2026-07-15T12:00:00Z",
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
        )
    )
    new_seal["code_review"]["review_commit_ref"] = next_head
    new_seal["code_review"]["reviewed_material_digest"] = next_digest
    new_seal["material"].update(
        {
            "base_ref_oid": next_base,
            "digest": next_digest,
            "material_head_sha": next_head,
            "merge_base_sha": next_base,
        }
    )
    state = {
        "dispositions": [],
        "experiment_result": None,
        "packet": None,
        "pr_number": 42,
    }
    existing = closeout_module._render_mapping(state, old_seal)
    replacement = closeout_module._render_mapping(state, new_seal)
    merge_bases = {
        (BASE_SHA, next_base): BASE_SHA,
        (HEAD_SHA, next_head): HEAD_SHA,
    }
    monkeypatch.setattr(
        closeout_module,
        "_git",
        lambda command, left, right: (
            merge_bases[(left, right)]
            if command == "merge-base"
            else pytest.fail(f"unexpected git command: {command}")
        ),
    )

    assert (
        closeout_module._validate_reseal_transition(
            existing,
            replacement,
            repository="owner/repo",
            pr_number=42,
            expected_freeze=new_seal["material"],
        )
        == HEAD_SHA
    )

    merge_bases[(BASE_SHA, next_base)] = OUTSIDE_SHA
    with pytest.raises(
        closeout_module.CloseoutError,
        match="without a proven fast-forward",
    ):
        closeout_module._validate_reseal_transition(
            existing,
            replacement,
            repository="owner/repo",
            pr_number=42,
            expected_freeze=new_seal["material"],
        )


def test_embedded_seal_rejects_duplicate_keys() -> None:
    text = f'{SEAL_BEGIN}\n{{"authority":"x","authority":"y"}}\n{SEAL_END}'

    with pytest.raises(ReviewEvidenceError, match="duplicate key"):
        parse_embedded_review_seal(text)


def test_snapshot_recheck_detects_force_push() -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "baseRefOid": BASE_SHA,
                        "headRefOid": OUTSIDE_SHA,
                    }
                }
            }
        }

    with pytest.raises(CommitIdentityError, match="SNAPSHOT_CHANGED"):
        assert_snapshot_unchanged(_snapshot(), token="opaque", request_json=request_json)


def test_sanitized_pr_2137_refs_share_one_fingerprint_and_never_compare() -> None:
    synthetic_refs = ("6" * 40, "7" * 40, "8" * 40)
    compare_calls = 0

    def request_json(url: str, **_kwargs: Any) -> Any:
        nonlocal compare_calls
        if "/compare/" in url:
            compare_calls += 1
        raise GitHubHttpError(404, "Not Found")

    fingerprints: set[str] = set()
    for review_ref in synthetic_refs:
        resolution = classify_commit_ref(
            review_ref, _snapshot(), token="opaque", request_json=request_json
        )
        assert isinstance(resolution, ReviewExecutionRef)
        assert resolution.kind is CommitRefKind.REVIEW_REF_UNAVAILABLE
        fingerprints.add(
            unavailable_review_ref_fingerprint(
                pr_number=42,
                material_digest=DIGEST,
                verified_real_fix_sha=FIX_SHA,
            )
        )
    assert fingerprints == {
        unavailable_review_ref_fingerprint(
            pr_number=42,
            material_digest=DIGEST,
            verified_real_fix_sha=FIX_SHA,
        )
    }
    assert compare_calls == 0


def test_sanitized_pr_2137_abbreviated_fix_dedupes_three_unavailable_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_fix = "fe7ff2017029ee9ede21264f2fbe19dca1ce23a2"  # pragma: allowlist secret
    real_head = "5a916507" + "a" * 32
    original_commits = (
        "2d828000" + "a" * 32,
        "69168f8e" + "b" * 32,
        real_head,
    )
    unavailable_refs = (
        "66c8634758c59916d46106e8e223e804c86733aa",  # pragma: allowlist secret
        "2aa032f808cdedc8f4b9a6514a5051cd6ff801be",  # pragma: allowlist secret
        "f31fd6332eb85cd4f9cff1131db69781896ebb8a",  # pragma: allowlist secret
    )
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=2137,
        base_sha=BASE_SHA,
        head_sha=real_head,
        commits=(
            PrCommitEvidence(real_fix, "2026-07-14T09:00:00Z"),
            *(
                PrCommitEvidence(sha, f"2026-07-14T{10 + index:02d}:00:00Z")
                for index, sha in enumerate(original_commits)
            ),
        ),
    )
    fingerprint = unavailable_review_ref_fingerprint(
        pr_number=2137,
        material_digest=DIGEST,
        verified_real_fix_sha=real_fix,
    )
    root_urls = tuple(
        f"https://github.com/owner/repo/pull/2137#discussion_r{index}" for index in range(1, 4)
    )
    findings = tuple(
        ReviewCommentEvidence(
            url=url,
            body=(
                "Commit ancestry finding: FIX fe7ff201... is reported unreachable "
                f"from reviewer execution ref {unavailable_ref}."
            ),
            created_at=f"2026-07-14T{13 + index:02d}:00:00Z",
            author_login="chatgpt-codex-connector",
            author_association="NONE",
            original_commit_sha=original_commits[index],
        )
        for index, (url, unavailable_ref) in enumerate(zip(root_urls, unavailable_refs))
    )
    threads = (
        ReviewThreadEvidence("canonical", True, (findings[0],)),
        *(
            ReviewThreadEvidence(
                f"duplicate-{index}",
                True,
                (
                    findings[index],
                    ReviewCommentEvidence(
                        url=f"{root_urls[index]}-reply",
                        body=_duplicate_reply(fingerprint),
                        created_at=f"2026-07-14T{16 + index:02d}:00:00Z",
                        author_login="maintainer",
                        author_association="OWNER",
                        original_commit_sha=original_commits[index],
                    ),
                ),
            )
            for index in (1, 2)
        ),
    )
    record = type(
        "Record",
        (),
        {
            "material_digest": DIGEST,
            "verified_fix": real_fix,
            "urls": (root_urls[0],),
        },
    )()
    ancestry_calls: list[tuple[str, str]] = []

    def classify(value: str, *_args: Any, **_kwargs: Any) -> Any:
        if value in unavailable_refs:
            return ReviewExecutionRef(value, CommitRefKind.REVIEW_REF_UNAVAILABLE, "unavailable")
        return RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD if value == real_head else CommitRefKind.PR_COMMIT,
        )

    def ancestor(left: RepositoryCommitRef, right: RepositoryCommitRef, **_kwargs: Any) -> bool:
        ancestry_calls.append((left.sha, right.sha))
        assert left.sha not in unavailable_refs
        assert right.sha not in unavailable_refs
        return True

    monkeypatch.setattr(identity_module, "classify_commit_ref", classify)
    monkeypatch.setattr(identity_module, "is_ancestor", ancestor)
    monkeypatch.setattr(
        evidence_module,
        "compute_material_manifest",
        lambda _root, *, head_ref_oid, **_kwargs: _material_manifest(head_ref_oid),
    )
    covered = validated_duplicate_reply_urls(
        candidate_urls=set(root_urls[1:]),
        threads=threads,
        fingerprint_records={fingerprint: record},
        material_digest=DIGEST,
        repo_root=Path(),
        snapshot=snapshot,
        repository="owner/repo",
        token="opaque",
    )

    assert covered == set(root_urls[1:])
    assert ancestry_calls
    assert all(
        left not in unavailable_refs and right not in unavailable_refs
        for left, right in ancestry_calls
    )


def _comment_connection(
    comments: list[dict[str, Any]], *, has_next: bool, cursor: str | None
) -> dict[str, Any]:
    return {
        "nodes": comments,
        "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
    }


def _comment(url_suffix: str) -> dict[str, Any]:
    return {
        "author": {"login": "chatgpt-codex-connector"},
        "authorAssociation": "NONE",
        "body": "Potential issue: commit ancestry",
        "createdAt": "2026-07-15T10:00:00Z",
        "originalCommit": {"oid": FIX_SHA},
        "url": f"https://github.com/owner/repo/pull/42#discussion_r{url_suffix}",
    }


def test_review_threads_paginate_outer_and_inner_connections() -> None:
    calls = 0

    def request_json(_url: str, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        variables = kwargs["payload"]["variables"]
        if "id" in variables:
            return {
                "data": {
                    "node": {
                        "comments": _comment_connection(
                            [_comment("2")], has_next=False, cursor=None
                        )
                    }
                }
            }
        if variables["cursor"] is None:
            return {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "nodes": [
                                    {
                                        "comments": _comment_connection(
                                            [_comment("1")],
                                            has_next=True,
                                            cursor="comments-1",
                                        ),
                                        "id": "thread-1",
                                        "isResolved": True,
                                    }
                                ],
                                "pageInfo": {
                                    "hasNextPage": True,
                                    "endCursor": "threads-1",
                                },
                            }
                        }
                    }
                }
            }
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "comments": _comment_connection(
                                        [_comment("3")], has_next=False, cursor=None
                                    ),
                                    "id": "thread-2",
                                    "isResolved": False,
                                }
                            ],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            }
        }

    threads = fetch_review_threads("owner/repo", 42, token="opaque", request_json=request_json)

    assert calls == 3
    assert [len(thread.comments) for thread in threads] == [2, 1]


def test_review_comment_pagination_fails_closed_for_missing_cursor() -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "comments": _comment_connection(
                                        [_comment("1")], has_next=True, cursor=None
                                    ),
                                    "id": "thread-1",
                                    "isResolved": True,
                                }
                            ],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            }
        }

    with pytest.raises(CommitIdentityError, match="cursor is missing or repeated"):
        fetch_review_threads("owner/repo", 42, token="opaque", request_json=request_json)


def test_review_comments_use_one_global_retained_comment_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(identity_module, "_MAX_REVIEW_COMMENTS", 1)

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "comments": _comment_connection(
                                        [_comment("1")], has_next=False, cursor=None
                                    ),
                                    "id": "thread-1",
                                    "isResolved": True,
                                },
                                {
                                    "comments": _comment_connection(
                                        [_comment("2")], has_next=False, cursor=None
                                    ),
                                    "id": "thread-2",
                                    "isResolved": False,
                                },
                            ],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            }
        }

    with pytest.raises(CommitIdentityError, match="global safety limit"):
        fetch_review_threads("owner/repo", 42, token="opaque", request_json=request_json)


def test_review_comments_use_one_global_nested_page_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(identity_module, "_MAX_REVIEW_COMMENT_PAGES", 1)
    calls = 0

    def request_json(_url: str, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        variables = kwargs["payload"]["variables"]
        if "id" in variables:
            return {
                "data": {
                    "node": {
                        "comments": _comment_connection(
                            [_comment("2")], has_next=False, cursor=None
                        )
                    }
                }
            }
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "comments": _comment_connection(
                                        [_comment("1")], has_next=True, cursor="comments-1"
                                    ),
                                    "id": "thread-1",
                                    "isResolved": True,
                                },
                                {
                                    "comments": _comment_connection(
                                        [_comment("3")], has_next=True, cursor="comments-2"
                                    ),
                                    "id": "thread-2",
                                    "isResolved": False,
                                },
                            ],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            }
        }

    with pytest.raises(CommitIdentityError, match="global page limit"):
        fetch_review_threads("owner/repo", 42, token="opaque", request_json=request_json)
    assert calls == 2


def test_material_digest_tracks_rename_mode_binary_and_symlink(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    tracked = repo / "tool.sh"
    tracked.write_text("echo one\n", encoding="utf-8")
    base = _commit(repo, "base")

    tracked.write_text("echo two\n", encoding="utf-8")
    first_head = _commit(repo, "content")
    first = compute_material_manifest(
        repo, base_ref_oid=base, head_ref_oid=first_head, pr_number=42
    )

    tracked.chmod(0o755)
    mode_head = _commit(repo, "mode")
    mode = compute_material_manifest(repo, base_ref_oid=base, head_ref_oid=mode_head, pr_number=42)
    assert mode.digest != first.digest

    tracked.rename(repo / "renamed.sh")
    (repo / "payload.bin").write_bytes(b"\x00\xff\x00")
    (repo / "tool-link").symlink_to("renamed.sh")
    final_head = _commit(repo, "rename binary symlink")
    final = compute_material_manifest(
        repo, base_ref_oid=base, head_ref_oid=final_head, pr_number=42
    )
    assert final.digest != mode.digest
    assert {entry.status for entry in final.entries} >= {"A", "D"}
    assert {entry.path for entry in final.entries} >= {
        "payload.bin",
        "renamed.sh",
        "tool-link",
        "tool.sh",
    }


def test_scan_receipt_rejects_path_traversal_and_incomplete_coverage(
    tmp_path: Path,
) -> None:
    manifest_path = _build_scan_bundle(tmp_path / "scan")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scan"]["artifacts"][0]["path"] = "../findings.json"
    _write_json(manifest_path, manifest)
    with pytest.raises(ReviewEvidenceError, match="escapes the scan root"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )

    manifest_path = _build_scan_bundle(tmp_path / "scan-2")
    coverage_path = manifest_path.parent / "coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage["deferred"] = ["security surface"]
    coverage_raw = _write_json(coverage_path, coverage)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["scan"]["artifacts"]:
        if artifact["path"] == "coverage.json":
            artifact["sha256"] = hashlib.sha256(coverage_raw).hexdigest()
    _write_json(manifest_path, manifest)
    with pytest.raises(ReviewEvidenceError, match="coverage is incomplete"):
        ingest_codex_security_receipt(
            manifest_path, expected_base_sha=BASE_SHA, expected_head_sha=HEAD_SHA
        )


def _duplicate_reply(fingerprint: str) -> str:
    return "\n".join(
        [
            "Disposition: NOT-A-BUG",
            f"Fingerprint: {fingerprint}",
            f"Duplicate-Of: {fingerprint}",
            "Evidence: material digest and verified FIX SHA",
            "Reason: reviewer ref is unavailable; canonical disposition reused",
        ]
    )


def test_duplicate_reply_requires_trusted_resolved_thread_and_real_fix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fingerprint = unavailable_review_ref_fingerprint(
        pr_number=42, material_digest=DIGEST, verified_real_fix_sha=FIX_SHA
    )
    record = type(
        "Record",
        (),
        {
            "material_digest": DIGEST,
            "verified_fix": FIX_SHA,
            "urls": ("https://github.com/owner/repo/pull/42#discussion_canonical",),
        },
    )()
    canonical_finding = ReviewCommentEvidence(
        url=record.urls[0],
        body=f"Potential issue: commit ancestry says {FIX_SHA} cannot reach {UNAVAILABLE_SHA}",
        created_at="2026-07-15T09:00:00Z",
        author_login="chatgpt-codex-connector",
        author_association="NONE",
        original_commit_sha=FIX_SHA,
    )
    finding = ReviewCommentEvidence(
        **{
            **canonical_finding.__dict__,
            "url": "https://github.com/owner/repo/pull/42#discussion_duplicate",
            "created_at": "2026-07-15T10:00:00Z",
        }
    )
    reply = ReviewCommentEvidence(
        url="https://github.com/owner/repo/pull/42#discussion_r2",
        body=_duplicate_reply(fingerprint),
        created_at="2026-07-15T11:00:00Z",
        author_login="maintainer",
        author_association="OWNER",
        original_commit_sha=FIX_SHA,
    )
    canonical_thread = ReviewThreadEvidence("canonical-thread", True, (canonical_finding,))
    thread = ReviewThreadEvidence("duplicate-thread", True, (finding, reply))

    def classify(value: str, *_args: Any, **_kwargs: Any) -> Any:
        if value == UNAVAILABLE_SHA:
            return ReviewExecutionRef(
                value=value,
                kind=CommitRefKind.REVIEW_REF_UNAVAILABLE,
                reason="unavailable",
            )
        return RepositoryCommitRef(value, CommitRefKind.PR_COMMIT)

    monkeypatch.setattr(identity_module, "classify_commit_ref", classify)
    monkeypatch.setattr(identity_module, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(
        evidence_module,
        "compute_material_manifest",
        lambda _root, *, head_ref_oid, **_kwargs: _material_manifest(head_ref_oid),
    )

    covered = validated_duplicate_reply_urls(
        candidate_urls={finding.url},
        threads=(canonical_thread, thread),
        fingerprint_records={fingerprint: record},
        material_digest=DIGEST,
        repo_root=Path(),
        snapshot=_snapshot(),
        repository="owner/repo",
        token="opaque",
    )
    assert covered == {finding.url}

    spoofed = ReviewThreadEvidence(
        "thread",
        True,
        (finding, ReviewCommentEvidence(**{**reply.__dict__, "author_association": "NONE"})),
    )
    assert not validated_duplicate_reply_urls(
        candidate_urls={finding.url},
        threads=(canonical_thread, spoofed),
        fingerprint_records={fingerprint: record},
        material_digest=DIGEST,
        repo_root=Path(),
        snapshot=_snapshot(),
        repository="owner/repo",
        token="opaque",
    )

    def classify_unknown(value: str, *_args: Any, **_kwargs: Any) -> Any:
        if value == UNAVAILABLE_SHA:
            return ReviewExecutionRef(
                value=value,
                kind=CommitRefKind.API_UNKNOWN,
                reason="rate limited",
            )
        return RepositoryCommitRef(value, CommitRefKind.PR_COMMIT)

    monkeypatch.setattr(identity_module, "classify_commit_ref", classify_unknown)
    with pytest.raises(ReviewEvidenceError, match="API_UNKNOWN"):
        validated_duplicate_reply_urls(
            candidate_urls={finding.url},
            threads=(canonical_thread, thread),
            fingerprint_records={fingerprint: record},
            material_digest=DIGEST,
            repo_root=Path(),
            snapshot=_snapshot(),
            repository="owner/repo",
            token="opaque",
        )


def test_duplicate_reply_binds_finding_original_commits_to_material_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base_sha = _commit(repo, "base")
    source = repo / "src" / "policy.py"
    source.parent.mkdir(parents=True)
    source.write_text("ENFORCED = True\n", encoding="utf-8")
    material_sha = _commit(repo, "material")
    material_manifest = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=material_sha,
        pr_number=42,
    )
    mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    mapping.write_text("governance-only\n", encoding="utf-8")
    governance_sha = _commit(repo, "governance closeout")
    governance_manifest = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=governance_sha,
        pr_number=42,
    )
    assert governance_manifest.digest == material_manifest.digest
    source.write_text("ENFORCED = False\n", encoding="utf-8")
    changed_sha = _commit(repo, "material change")
    changed_manifest = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=changed_sha,
        pr_number=42,
    )
    assert changed_manifest.digest != material_manifest.digest

    def classify(value: str, snapshot: PrSnapshot, **_kwargs: Any) -> Any:
        if value == UNAVAILABLE_SHA:
            return ReviewExecutionRef(
                value=value,
                kind=CommitRefKind.REVIEW_REF_UNAVAILABLE,
                reason="unavailable",
            )
        return RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD if value == snapshot.head_sha else CommitRefKind.PR_COMMIT,
        )

    monkeypatch.setattr(identity_module, "classify_commit_ref", classify)
    monkeypatch.setattr(identity_module, "is_ancestor", lambda *_a, **_k: True)

    canonical_url = "https://github.com/owner/repo/pull/42#discussion_canonical"
    duplicate_url = "https://github.com/owner/repo/pull/42#discussion_duplicate"

    def evidence(
        *, digest: str, canonical_original: str, duplicate_original: str
    ) -> tuple[str, Any, tuple[ReviewThreadEvidence, ...]]:
        fingerprint = unavailable_review_ref_fingerprint(
            pr_number=42,
            material_digest=digest,
            verified_real_fix_sha=material_sha,
        )
        record = type(
            "Record",
            (),
            {
                "material_digest": digest,
                "verified_fix": material_sha,
                "urls": (canonical_url,),
            },
        )()
        finding_body = (
            f"Potential issue: commit ancestry says {material_sha} cannot reach {UNAVAILABLE_SHA}"
        )
        canonical = ReviewCommentEvidence(
            url=canonical_url,
            body=finding_body,
            created_at="2026-07-15T09:00:00Z",
            author_login="chatgpt-codex-connector",
            author_association="NONE",
            original_commit_sha=canonical_original,
        )
        duplicate = ReviewCommentEvidence(
            url=duplicate_url,
            body=finding_body,
            created_at="2026-07-15T10:00:00Z",
            author_login="chatgpt-codex-connector",
            author_association="NONE",
            original_commit_sha=duplicate_original,
        )
        reply = ReviewCommentEvidence(
            url=f"{duplicate_url}-reply",
            body=_duplicate_reply(fingerprint),
            created_at="2026-07-15T11:00:00Z",
            author_login="maintainer",
            author_association="OWNER",
            original_commit_sha=duplicate_original,
        )
        threads = (
            ReviewThreadEvidence("canonical", True, (canonical,)),
            ReviewThreadEvidence("duplicate", True, (duplicate, reply)),
        )
        return fingerprint, record, threads

    governance_fingerprint, governance_record, governance_threads = evidence(
        digest=material_manifest.digest,
        canonical_original=material_sha,
        duplicate_original=governance_sha,
    )
    governance_snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=governance_sha,
        commits=(
            PrCommitEvidence(material_sha, None),
            PrCommitEvidence(governance_sha, None),
        ),
    )
    assert validated_duplicate_reply_urls(
        candidate_urls={duplicate_url},
        threads=governance_threads,
        fingerprint_records={governance_fingerprint: governance_record},
        material_digest=material_manifest.digest,
        repo_root=repo,
        snapshot=governance_snapshot,
        repository="owner/repo",
        token="opaque",
    ) == {duplicate_url}

    stale_fingerprint, stale_record, stale_threads = evidence(
        digest=changed_manifest.digest,
        canonical_original=material_sha,
        duplicate_original=changed_sha,
    )
    changed_snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=changed_sha,
        commits=(
            PrCommitEvidence(material_sha, None),
            PrCommitEvidence(governance_sha, None),
            PrCommitEvidence(changed_sha, None),
        ),
    )
    with pytest.raises(ReviewEvidenceError, match="different material digest"):
        validated_duplicate_reply_urls(
            candidate_urls={duplicate_url},
            threads=stale_threads,
            fingerprint_records={stale_fingerprint: stale_record},
            material_digest=changed_manifest.digest,
            repo_root=repo,
            snapshot=changed_snapshot,
            repository="owner/repo",
            token="opaque",
        )


def test_duplicate_reply_parser_rejects_extra_fields() -> None:
    fingerprint = "sha256:" + "a" * 64
    assert parse_duplicate_disposition_reply(_duplicate_reply(fingerprint)) == fingerprint
    with pytest.raises(ReviewEvidenceError, match="five exact fields"):
        parse_duplicate_disposition_reply(_duplicate_reply(fingerprint) + "\nExtra: no")


def test_closeout_renderer_round_trips_fingerprint_record(tmp_path: Path) -> None:
    receipt = ingest_codex_security_receipt(
        _build_scan_bundle(tmp_path / "scan"),
        expected_base_sha=BASE_SHA,
        expected_head_sha=HEAD_SHA,
    )
    fingerprint = unavailable_review_ref_fingerprint(
        pr_number=42, material_digest=DIGEST, verified_real_fix_sha=FIX_SHA
    )
    state = {
        "dispositions": [
            {
                "cause": "unavailable_review_ref_ancestry",
                "disposition": "NOT-A-BUG",
                "evidence": "GitHub Commit API 404",
                "fingerprint": fingerprint,
                "material_digest": DIGEST,
                "reason": "review execution ref is unavailable",
                "url": "https://github.com/owner/repo/pull/42#discussion_r1",
                "verified_fix": FIX_SHA,
            }
        ],
        "experiment_result": None,
        "packet": None,
        "pr_number": 42,
    }
    rendered = closeout_module._render_mapping(state, _seal(receipt))
    assert "Exception: no retained coordinator packet was supplied." in rendered
    assert validate_mapping_artifact_text(rendered) == []
    records = parse_canonical_fingerprint_records(rendered, pr_number=42)
    assert records[fingerprint].verified_fix == FIX_SHA


def _rendered_fingerprint_mapping(tmp_path: Path) -> tuple[str, str, str]:
    receipt = ingest_codex_security_receipt(
        _build_scan_bundle(tmp_path / "scan"),
        expected_base_sha=BASE_SHA,
        expected_head_sha=HEAD_SHA,
    )
    url = "https://github.com/owner/repo/pull/42#discussion_r1"
    fingerprint = unavailable_review_ref_fingerprint(
        pr_number=42, material_digest=DIGEST, verified_real_fix_sha=FIX_SHA
    )
    state = {
        "dispositions": [
            {
                "cause": "unavailable_review_ref_ancestry",
                "disposition": "NOT-A-BUG",
                "evidence": "GitHub Commit API 404",
                "fingerprint": fingerprint,
                "material_digest": DIGEST,
                "reason": "review execution ref is unavailable",
                "url": url,
                "verified_fix": FIX_SHA,
            }
        ],
        "experiment_result": None,
        "packet": None,
        "pr_number": 42,
    }
    return closeout_module._render_mapping(state, _seal(receipt)), fingerprint, url


def test_mapping_validator_rejects_non_recomputing_fingerprint(tmp_path: Path) -> None:
    rendered, fingerprint, _url = _rendered_fingerprint_mapping(tmp_path)
    tampered = rendered.replace(fingerprint, "sha256:" + "b" * 64, 1)

    assert any(
        "canonical fingerprint record does not recompute" in error
        for error in validate_mapping_artifact_text(tampered)
    )


def test_mapping_validator_rejects_fingerprint_for_different_material(
    tmp_path: Path,
) -> None:
    rendered, fingerprint, _url = _rendered_fingerprint_mapping(tmp_path)
    other_digest = "sha256:" + "c" * 64
    other_fingerprint = unavailable_review_ref_fingerprint(
        pr_number=42,
        material_digest=other_digest,
        verified_real_fix_sha=FIX_SHA,
    )
    tampered = rendered.replace(fingerprint, other_fingerprint, 1).replace(
        f"Material-Digest: {DIGEST}",
        f"Material-Digest: {other_digest}",
        1,
    )

    assert any(
        "canonical fingerprint record does not match sealed material" in error
        for error in validate_mapping_artifact_text(tampered)
    )


def test_mapping_validator_rejects_fingerprint_with_multiple_urls(tmp_path: Path) -> None:
    rendered, _fingerprint, url = _rendered_fingerprint_mapping(tmp_path)
    tampered = rendered.replace(
        f"- {url}",
        f"- {url}\n- https://github.com/owner/repo/pull/42#discussion_r2",
        1,
    )

    assert any(
        "canonical fingerprint record must identify exactly one URL" in error
        for error in validate_mapping_artifact_text(tampered)
    )


@pytest.mark.parametrize(
    ("module", "error_type"),
    [
        (evidence_module, ReviewEvidenceError),
        (closeout_module, closeout_module.CloseoutError),
    ],
)
def test_git_path_normalizes_relative_which_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: Any,
    error_type: type[Exception],
) -> None:
    del error_type
    executable = tmp_path / "tools" / "git"
    executable.parent.mkdir()
    executable.write_text("git", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: "tools/git")

    assert module._git_path() == str(executable.resolve())


@pytest.mark.parametrize(
    ("module", "error_type"),
    [
        (evidence_module, ReviewEvidenceError),
        (closeout_module, closeout_module.CloseoutError),
    ],
)
def test_git_path_rejects_unresolvable_which_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: Any,
    error_type: type[Exception],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: "missing/git")

    with pytest.raises(error_type, match="could not be resolved"):
        module._git_path()


def _write_backlog_entry(path: Path, *, include_dod: bool = True) -> None:
    lines = [
        '<a id="ledger-p1-governance-followup"></a>',
        "- [ ] P1: Governance follow-up",
        "  - Owner: @owner",
        "  - Priority: P1",
        "  - Target PR: #999",
        "  - Reason (EN): Keep the current PR bounded.",
        "  - Links: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`",
    ]
    if include_dod:
        lines.append("  - DoD: Ship the bounded follow-up with deterministic tests.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_deferred_disposition_requires_complete_canonical_backlog_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = tmp_path / "BACKLOG_LEDGER.md"
    _write_backlog_entry(ledger)
    monkeypatch.setattr(closeout_module, "BACKLOG_LEDGER_PATH", ledger)
    reference = "docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-governance-followup"

    assert closeout_module._validated_backlog_reference(reference) == reference


def test_deferred_disposition_rejects_incomplete_backlog_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = tmp_path / "BACKLOG_LEDGER.md"
    _write_backlog_entry(ledger, include_dod=False)
    monkeypatch.setattr(closeout_module, "BACKLOG_LEDGER_PATH", ledger)

    with pytest.raises(closeout_module.CloseoutError, match="DoD"):
        closeout_module._validated_backlog_reference(
            "docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-governance-followup"
        )


def test_deferred_disposition_rejects_noncanonical_backlog_reference() -> None:
    with pytest.raises(closeout_module.CloseoutError, match="BACKLOG_LEDGER"):
        closeout_module._validated_backlog_reference("docs/roadmap/OTHER.md#ledger-p1-item")


def test_authoritative_docs_preserve_phase2_body_scaffolding() -> None:
    template = (closeout_module.REPO_ROOT / ".github/pull_request_template.md").read_text(
        encoding="utf-8"
    )
    agents = (closeout_module.REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    runbook = (closeout_module.REPO_ROOT / "RUNBOOK_AGENT.md").read_text(encoding="utf-8")

    assert template.count("docs/review/PR_<N>_FIXED_MAPPING.md") == 1
    assert "## Discussion Thread Pass" in template
    assert "### Fixed in Commit Mapping" in template
    assert "- [ ] Discussion-thread pass completed" in template
    assert "- [ ] Fixed in commit mapping completed" in template
    for document in (agents, runbook):
        assert "## Discussion Thread Pass" in document
        assert "### Fixed in Commit Mapping" in document
        assert "checked checklist" in document


def test_closeout_init_is_atomic_and_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(closeout_module, "STATE_ROOT", tmp_path / "state")
    args = Namespace(
        repo="owner/repo",
        pr_number=42,
        packet="artifacts/orchestration/task_packets/packet.json",
        experiment_result="artifacts/orchestration/experiments/results/result.json",
    )
    closeout_module._cmd_init(args)
    first = closeout_module._state_path(42).read_bytes()
    closeout_module._cmd_init(args)
    assert closeout_module._state_path(42).read_bytes() == first


def _prepare_final_security_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Namespace, list[datetime]]:
    monkeypatch.setattr(closeout_module, "STATE_ROOT", tmp_path / "state")
    closeout_module._cmd_init(
        Namespace(
            repo="owner/repo",
            pr_number=42,
            packet=None,
            experiment_result=None,
        )
    )
    draft = closeout_module._load_state(42)
    draft["freeze"] = {
        "base_ref_oid": BASE_SHA,
        "digest": DIGEST,
        "material_head_sha": HEAD_SHA,
        "merge_base_sha": BASE_SHA,
        "policy_version": MATERIAL_POLICY_VERSION,
    }
    closeout_module._write_state(draft)
    clock = [datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)]
    monkeypatch.setattr(closeout_module, "_token", lambda: "opaque")
    monkeypatch.setattr(
        closeout_module,
        "fetch_pr_snapshot",
        lambda *_args, **_kwargs: _snapshot(),
    )
    monkeypatch.setattr(
        closeout_module,
        "_require_clean_live_head",
        lambda _head: None,
    )
    monkeypatch.setattr(
        closeout_module,
        "compute_material_manifest",
        lambda *_args, **_kwargs: _material_manifest(HEAD_SHA),
    )
    monkeypatch.setattr(
        closeout_module,
        "assert_snapshot_unchanged",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_reference",
        lambda reference, **_kwargs: CodexReviewEvidence(
            reference=reference,
            submitted_at="2026-07-15T11:59:00Z",
            commit_ref=HEAD_SHA,
        ),
    )
    monkeypatch.setattr(
        closeout_module,
        "classify_commit_ref",
        lambda value, *_args, **_kwargs: RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD,
        ),
    )
    monkeypatch.setattr(closeout_module, "_utc_now", lambda: clock[0])
    return (
        Namespace(
            repo="owner/repo",
            pr_number=42,
            review_ref="https://github.com/owner/repo/pull/42#pullrequestreview-789",
            review_source_unavailable_ref=None,
            operator_approval_ref=None,
        ),
        clock,
    )


@pytest.mark.parametrize(
    "state, error",
    [
        (None, "prepare and record final security"),
        (
            {
                "preparations": [
                    {
                        "attempt_outcome": "completed",
                        "attempt_status": "completed",
                        "material_digest": DIGEST,
                        "material_head_sha": FIX_SHA,
                    }
                ]
            },
            "does not match frozen material",
        ),
        (
            {
                "preparations": [
                    {
                        "attempt_outcome": None,
                        "attempt_status": "reserved",
                        "material_digest": DIGEST,
                        "material_head_sha": HEAD_SHA,
                    }
                ]
            },
            "lacks a completed scan outcome",
        ),
        (
            {
                "preparations": [
                    {
                        "attempt_outcome": "timeout",
                        "attempt_status": "completed",
                        "material_digest": DIGEST,
                        "material_head_sha": HEAD_SHA,
                    }
                ]
            },
            "lacks a completed scan outcome",
        ),
    ],
)
def test_seal_requires_completed_exact_material_final_security_preparation(
    state: dict[str, Any] | None,
    error: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        closeout_module,
        "_load_final_security_state",
        lambda **_kwargs: state,
    )

    with pytest.raises(closeout_module.CloseoutError, match=error):
        closeout_module._require_completed_final_security_preparation(
            repository="owner/repo",
            pr_number=42,
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
        )


def test_seal_binds_completed_scan_and_review_to_prepared_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded_manifest = tmp_path / "recorded" / "scan-manifest.json"
    supplied_manifest = tmp_path / "supplied" / "scan-manifest.json"
    recorded_manifest.parent.mkdir()
    supplied_manifest.parent.mkdir()
    recorded_manifest.write_text(
        '{"scan":{"completedAt":"2026-07-15T12:00:02Z",' '"startedAt":"2026-07-15T12:00:01Z"}}\n',
        encoding="utf-8",
    )
    supplied_manifest.write_text(
        '{"scan":{"completedAt":"2026-07-15T12:00:02Z",' '"startedAt":"2026-07-15T12:00:01Z"}}\n',
        encoding="utf-8",
    )
    review_evidence = {
        "kind": "completed_review",
        "review_commit_sha": HEAD_SHA,
        "review_reference": "https://github.com/owner/repo/pull/42#pullrequestreview-789",
        "review_submitted_at": "2026-07-15T11:59:00Z",
    }
    state = {
        "preparations": [
            {
                "attempt_completed_at": "2026-07-15T12:00:03Z",
                "attempt_outcome": "completed",
                "attempt_status": "completed",
                "material_digest": DIGEST,
                "material_head_sha": HEAD_SHA,
                "outcome_evidence_ref": str(recorded_manifest),
                "prepared_at": "2026-07-15T12:00:00Z",
                "review_evidence": review_evidence,
            }
        ]
    }
    monkeypatch.setattr(
        closeout_module,
        "_load_final_security_state",
        lambda **_kwargs: state,
    )

    closeout_module._require_completed_final_security_preparation(
        repository="owner/repo",
        pr_number=42,
        material_head_sha=HEAD_SHA,
        material_digest=DIGEST,
        expected_review_evidence=review_evidence,
        scan_manifest=recorded_manifest,
    )

    with pytest.raises(closeout_module.CloseoutError, match="does not match the recorded"):
        closeout_module._require_completed_final_security_preparation(
            repository="owner/repo",
            pr_number=42,
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
            expected_review_evidence=review_evidence,
            scan_manifest=supplied_manifest,
        )
    with pytest.raises(closeout_module.CloseoutError, match="review evidence does not match"):
        closeout_module._require_completed_final_security_preparation(
            repository="owner/repo",
            pr_number=42,
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
            expected_review_evidence={**review_evidence, "review_reference": "different"},
            scan_manifest=recorded_manifest,
        )

    recorded_manifest.write_text(
        '{"scan":{"completedAt":"2026-07-15T12:00:04Z",' '"startedAt":"2026-07-15T12:00:01Z"}}\n',
        encoding="utf-8",
    )
    with pytest.raises(closeout_module.CloseoutError, match="predates the scan completion"):
        closeout_module._require_completed_final_security_preparation(
            repository="owner/repo",
            pr_number=42,
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
            expected_review_evidence=review_evidence,
            scan_manifest=recorded_manifest,
        )

    recorded_manifest.write_text(
        '{"scan":{"completedAt":"2026-07-15T12:00:02Z",' '"startedAt":"2026-07-15T11:59:59Z"}}\n',
        encoding="utf-8",
    )
    with pytest.raises(closeout_module.CloseoutError, match="predates its preparation"):
        closeout_module._require_completed_final_security_preparation(
            repository="owner/repo",
            pr_number=42,
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
            expected_review_evidence=review_evidence,
            scan_manifest=recorded_manifest,
        )


def test_outage_seal_requires_matching_prepared_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review_evidence = {
        "kind": "completed_review",
        "review_commit_sha": HEAD_SHA,
        "review_reference": "https://github.com/owner/repo/pull/42#pullrequestreview-789",
        "review_submitted_at": "2026-07-15T11:59:00Z",
    }
    record = {
        "attempt_completed_at": "2026-07-15T12:00:00Z",
        "attempt_outcome": "incomplete",
        "attempt_status": "completed",
        "material_digest": DIGEST,
        "material_head_sha": HEAD_SHA,
        "review_evidence": review_evidence,
    }
    monkeypatch.setattr(
        closeout_module,
        "_load_final_security_state",
        lambda **_kwargs: {"preparations": [record]},
    )

    with pytest.raises(closeout_module.CloseoutError, match="recorded timeout"):
        closeout_module._require_terminal_outage_final_security_preparation(
            repository="owner/repo",
            pr_number=42,
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
            expected_review_evidence=review_evidence,
        )

    record["attempt_outcome"] = "timeout"
    completed_at = closeout_module._require_terminal_outage_final_security_preparation(
        repository="owner/repo",
        pr_number=42,
        material_head_sha=HEAD_SHA,
        material_digest=DIGEST,
        expected_review_evidence=review_evidence,
    )
    assert completed_at == datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("override_created_at", "should_pass"),
    [
        ("2026-07-15T12:00:00Z", False),
        ("2026-07-15T12:00:01Z", True),
    ],
)
def test_closeout_outage_override_must_follow_recorded_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    override_created_at: str,
    should_pass: bool,
) -> None:
    repo = tmp_path / "repo"
    target = repo / "docs/review/PR_42_FIXED_MAPPING.md"
    state = {
        "dispositions": [],
        "experiment_result": None,
        "freeze": {
            "base_ref_oid": BASE_SHA,
            "digest": DIGEST,
            "material_head_sha": HEAD_SHA,
            "merge_base_sha": BASE_SHA,
            "policy_version": MATERIAL_POLICY_VERSION,
        },
        "packet": None,
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": closeout_module.DRAFT_SCHEMA_VERSION,
    }
    review_reference = "https://github.com/owner/repo/pull/42#pullrequestreview-456"
    override_reference = "https://github.com/owner/repo/pull/42#issuecomment-789"
    monkeypatch.setattr(closeout_module, "REPO_ROOT", repo)
    monkeypatch.setattr(closeout_module, "_load_state", lambda _pr: state)
    monkeypatch.setattr(closeout_module, "_token", lambda: "opaque")
    monkeypatch.setattr(closeout_module, "fetch_pr_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(closeout_module, "_require_clean_live_head", lambda _head: None)
    monkeypatch.setattr(
        closeout_module,
        "compute_material_manifest",
        lambda *_a, **_k: _material_manifest(HEAD_SHA),
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_reference",
        lambda *_a, **_k: CodexReviewEvidence(
            reference=review_reference,
            submitted_at="2026-07-15T11:59:00Z",
            commit_ref=HEAD_SHA,
        ),
    )
    monkeypatch.setattr(
        closeout_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_HEAD),
    )
    monkeypatch.setattr(
        closeout_module,
        "_require_terminal_outage_final_security_preparation",
        lambda **_kwargs: datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        closeout_module,
        "validate_security_outage_override_scope",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_security_outage_override_reference",
        lambda *_a, **_k: SecurityOutageOverrideEvidence(
            reference=override_reference,
            created_at=override_created_at,
            operator_user_id=123,
            operator_login="owner",
            operator_association="OWNER",
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
        ),
    )
    monkeypatch.setattr(
        closeout_module,
        "_render_mapping",
        lambda _state, seal: _mapping_artifact_with_seal(seal),
    )
    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: target)
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: "")
    monkeypatch.setattr(closeout_module, "assert_snapshot_unchanged", lambda *_a, **_k: None)
    args = Namespace(
        pr_number=42,
        repo="owner/repo",
        review_ref=review_reference,
        review_source_unavailable_ref=None,
        connector_advisory_reaction=[],
        scan_manifest=None,
        security_outage_override_ref=override_reference,
    )

    if not should_pass:
        with pytest.raises(closeout_module.CloseoutError, match="after the recorded timeout"):
            closeout_module._cmd_seal(args)
        assert not target.exists()
        return

    closeout_module._cmd_seal(args)
    seal = parse_embedded_review_seal(target.read_text(encoding="utf-8"))
    assert seal["codex_security"]["created_at"] == override_created_at


def _final_security_approval_response(
    reference: str,
    *,
    created_at: str = "2026-07-15T12:01:00Z",
    updated_at: str | None = None,
    association: str = "OWNER",
    body: str | None = None,
) -> dict[str, Any]:
    comment_id = int(reference.rsplit("-", maxsplit=1)[1])
    return {
        "author_association": association,
        "body": body
        or closeout_module.render_final_security_approval_comment(
            repository="owner/repo",
            pr_number=42,
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
        ),
        "created_at": created_at,
        "html_url": reference,
        "id": comment_id,
        "issue_url": "https://api.github.com/repos/owner/repo/issues/42",
        "performed_via_github_app": None,
        "updated_at": updated_at or created_at,
        "url": f"https://api.github.com/repos/owner/repo/issues/comments/{comment_id}",
        "user": {"id": 1234, "login": "trusted-owner", "type": "User"},
    }


def _record_final_security_outcome(
    clock: list[datetime],
    *,
    outcome: str = "completed",
    when: datetime | None = None,
) -> None:
    clock[0] = when or datetime(2026, 7, 15, 12, 0, 30, tzinfo=timezone.utc)
    closeout_module._cmd_record_final_security_outcome(
        Namespace(
            repo="owner/repo",
            pr_number=42,
            outcome=outcome,
            evidence_ref=f"artifact:{outcome}:attempt-1",
        )
    )


def test_final_security_lock_fails_closed_without_posix_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(closeout_module, "STATE_ROOT", tmp_path)

    def missing_backend(name: str) -> Any:
        assert name == "fcntl"
        raise ImportError("fcntl unavailable")

    monkeypatch.setattr(closeout_module.importlib, "import_module", missing_backend)
    backend = closeout_module._load_posix_locking_backend()
    assert backend is None
    monkeypatch.setattr(closeout_module, "_FCNTL", backend)

    with pytest.raises(
        closeout_module.CloseoutError,
        match=r"requires POSIX fcntl\.flock support",
    ):
        with closeout_module._final_security_lock(42):
            pytest.fail("missing locking backend must not enter the critical section")

    assert not closeout_module._state_dir(42).exists()
    assert not closeout_module._final_security_lock_path(42).exists()


def test_prepare_final_security_first_request_is_local_advisory_and_idempotency_guarded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args, _clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    draft_before = closeout_module._state_path(42).read_bytes()
    monkeypatch.setattr(
        closeout_module,
        "github_api_request",
        lambda *_args, **_kwargs: pytest.fail("first preparation must not fetch a comment"),
    )

    closeout_module._cmd_prepare_final_security(args)

    output = capsys.readouterr().out
    assert "FINAL_SECURITY_PREPARED" in output
    assert "no Codex Security plugin call or GitHub mutation was made" in output
    assert "cannot prove cross-machine request consumption" in output
    assert "automatic_retries=0" in output
    assert closeout_module._state_path(42).read_bytes() == draft_before
    preparation = closeout_module._load_final_security_state(
        repository="owner/repo",
        pr_number=42,
    )
    assert preparation is not None
    assert preparation["preparations"] == [
        {
            "attempt_completed_at": None,
            "attempt_outcome": None,
            "attempt_status": "reserved",
            "material_digest": DIGEST,
            "material_head_sha": HEAD_SHA,
            "operator_approval": None,
            "outcome_evidence_ref": None,
            "pr_number": 42,
            "prepared_at": "2026-07-15T12:00:00Z",
            "repository": "owner/repo",
            "review_evidence": {
                "kind": "completed_review",
                "review_commit_sha": HEAD_SHA,
                "review_reference": args.review_ref,
                "review_submitted_at": "2026-07-15T11:59:00Z",
            },
        }
    ]

    state_before_duplicate = closeout_module._final_security_state_path(42).read_bytes()
    with pytest.raises(closeout_module.CloseoutError, match="already prepared"):
        closeout_module._cmd_prepare_final_security(args)
    assert closeout_module._final_security_state_path(42).read_bytes() == state_before_duplicate


@pytest.mark.parametrize("reaction_content", ["+1", "heart", "hooray", "rocket"])
def test_prepare_final_security_accepts_connector_positive_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reaction_content: str,
) -> None:
    args, _clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    reaction_reference = "https://github.com/owner/repo/pull/42#reaction-456"
    args.review_ref = reaction_reference
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_reference",
        lambda *_args, **_kwargs: identity_module.CodexConnectorAdvisoryReactionEvidence(
            reference=reaction_reference,
            created_at="2026-07-15T11:59:00Z",
            content=reaction_content,
        ),
    )

    closeout_module._cmd_prepare_final_security(args)

    state = closeout_module._load_final_security_state(
        repository="owner/repo",
        pr_number=42,
    )
    assert state is not None
    assert state["preparations"][0]["review_evidence"] == (
        build_review_source_positive_response_receipt(
            material_digest=DIGEST,
            material_head_sha=HEAD_SHA,
            response_reference=reaction_reference,
            response_created_at="2026-07-15T11:59:00Z",
            response_content=reaction_content,
        )
    )


def test_prepare_final_security_accepts_terminal_review_source_unavailability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args, _clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    source_evidence = CodexReviewSourceUnavailabilityEvidence(
        reference="https://github.com/owner/repo/pull/42#issuecomment-456",
        created_at="2020-01-01T00:00:00Z",
        source_status="usage_limit_reached",
        body_sha256="sha256:" + "c" * 64,
    )
    args.review_ref = None
    args.review_source_unavailable_ref = source_evidence.reference
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_source_unavailability_reference",
        lambda *_args, **_kwargs: source_evidence,
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_reference",
        lambda *_args, **_kwargs: pytest.fail(
            "terminal source evidence must not claim a completed review"
        ),
    )

    closeout_module._cmd_prepare_final_security(args)

    state = closeout_module._load_final_security_state(
        repository="owner/repo",
        pr_number=42,
    )
    assert state is not None
    receipt = state["preparations"][0]["review_evidence"]
    assert receipt == build_review_source_unavailability_receipt(
        material_digest=DIGEST,
        material_head_sha=HEAD_SHA,
        quota_reference=source_evidence.reference,
        quota_created_at=source_evidence.created_at,
        quota_body_sha256=source_evidence.body_sha256,
        source_status=source_evidence.source_status,
    )
    assert receipt["review_claim"] == "none"
    assert "review_commit_sha" not in receipt


@pytest.mark.parametrize(
    ("review_ref", "source_ref"),
    [
        (None, None),
        (
            "https://github.com/owner/repo/pull/42#pullrequestreview-789",
            "https://github.com/owner/repo/pull/42#issuecomment-456",
        ),
    ],
    ids=["missing", "ambiguous"],
)
def test_prepare_final_security_rejects_nonexclusive_review_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    review_ref: str | None,
    source_ref: str | None,
) -> None:
    args, _clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    args.review_ref = review_ref
    args.review_source_unavailable_ref = source_ref

    with pytest.raises(
        closeout_module.CloseoutError,
        match="provide exactly one of --review-ref or --review-source-unavailable-ref",
    ):
        closeout_module._cmd_prepare_final_security(args)


def test_prepare_final_security_rejects_unfrozen_material(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args, _clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    draft = closeout_module._load_state(42)
    draft["freeze"] = None
    closeout_module._write_state(draft)

    with pytest.raises(closeout_module.CloseoutError, match="run freeze"):
        closeout_module._cmd_prepare_final_security(args)
    assert not closeout_module._final_security_state_path(42).exists()


@pytest.mark.parametrize(
    ("failure", "match"),
    [
        ("freeze/seal requires a clean worktree", "clean worktree"),
        (
            f"local HEAD {OUTSIDE_SHA} does not match live PR head {HEAD_SHA}",
            "does not match live PR head",
        ),
    ],
    ids=["dirty", "stale-head"],
)
def test_prepare_final_security_rejects_dirty_or_stale_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    match: str,
) -> None:
    args, _clock = _prepare_final_security_fixture(tmp_path, monkeypatch)

    def reject_checkout(_head: str) -> None:
        raise closeout_module.CloseoutError(failure)

    monkeypatch.setattr(
        closeout_module,
        "_require_clean_live_head",
        reject_checkout,
    )

    with pytest.raises(closeout_module.CloseoutError, match=match):
        closeout_module._cmd_prepare_final_security(args)
    assert not closeout_module._final_security_state_path(42).exists()


def test_prepare_final_security_rejects_material_digest_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args, _clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        closeout_module,
        "compute_material_manifest",
        lambda *_args, **_kwargs: _material_manifest(
            HEAD_SHA,
            digest="sha256:" + "b" * 64,
        ),
    )

    with pytest.raises(closeout_module.CloseoutError, match="material state changed"):
        closeout_module._cmd_prepare_final_security(args)
    assert not closeout_module._final_security_state_path(42).exists()


def test_prepare_final_security_rejects_missing_exact_head_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args, _clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_reference",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CommitIdentityError("expected material commit does not match")
        ),
    )

    with pytest.raises(CommitIdentityError, match="expected material commit"):
        closeout_module._cmd_prepare_final_security(args)
    assert not closeout_module._final_security_state_path(42).exists()


@pytest.mark.parametrize(
    "outcome",
    sorted(closeout_module.FINAL_SECURITY_ATTEMPT_OUTCOMES),
)
def test_record_final_security_outcome_consumes_reserved_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    args, clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    closeout_module._cmd_prepare_final_security(args)

    _record_final_security_outcome(clock, outcome=outcome)

    state = closeout_module._load_final_security_state(
        repository="owner/repo",
        pr_number=42,
    )
    assert state is not None
    record = state["preparations"][0]
    assert record["attempt_status"] == "completed"
    assert record["attempt_outcome"] == outcome
    assert record["attempt_completed_at"] == "2026-07-15T12:00:30Z"
    assert record["outcome_evidence_ref"] == f"artifact:{outcome}:attempt-1"


def test_prepare_final_security_rejects_preapproved_rerun_before_terminal_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args, clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    closeout_module._cmd_prepare_final_security(args)
    args.operator_approval_ref = "https://github.com/owner/repo/pull/42#issuecomment-456"
    clock[0] = datetime(2026, 7, 15, 12, 2, tzinfo=timezone.utc)

    with pytest.raises(closeout_module.CloseoutError, match="still reserved"):
        closeout_module._cmd_prepare_final_security(args)


def test_prepare_final_security_accepts_one_fresh_exact_operator_approval_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args, clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    closeout_module._cmd_prepare_final_security(args)
    _record_final_security_outcome(clock)
    draft_before = closeout_module._state_path(42).read_bytes()
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    requests: list[tuple[str, str, str, object]] = []

    def request(
        url: str,
        *,
        token: str,
        method: str = "GET",
        payload: object = None,
    ) -> dict[str, Any]:
        requests.append((url, token, method, payload))
        return _final_security_approval_response(reference)

    monkeypatch.setattr(closeout_module, "github_api_request", request)
    clock[0] = datetime(2026, 7, 15, 12, 2, tzinfo=timezone.utc)
    args.operator_approval_ref = reference

    closeout_module._cmd_prepare_final_security(args)

    assert requests == [
        (
            "https://api.github.com/repos/owner/repo/issues/comments/456",
            "opaque",
            "GET",
            None,
        )
    ]
    assert closeout_module._state_path(42).read_bytes() == draft_before
    state = closeout_module._load_final_security_state(
        repository="owner/repo",
        pr_number=42,
    )
    assert state is not None
    assert len(state["preparations"]) == 2
    assert state["preparations"][1]["operator_approval"] == {
        "author_association": "OWNER",
        "author_login": "trusted-owner",
        "author_user_id": 1234,
        "comment_id": 456,
        "created_at": "2026-07-15T12:01:00Z",
        "reference": reference,
    }


@pytest.mark.parametrize(
    "body",
    [
        "approve another request",
        closeout_module.render_final_security_approval_comment(
            repository="owner/repo",
            pr_number=42,
            material_head_sha=OUTSIDE_SHA,
            material_digest=DIGEST,
        ),
        closeout_module.render_final_security_approval_comment(
            repository="owner/repo",
            pr_number=42,
            material_head_sha=HEAD_SHA,
            material_digest="sha256:" + "b" * 64,
        ),
    ],
    ids=["wrong-body", "wrong-head", "wrong-digest"],
)
def test_prepare_final_security_rejects_non_exact_operator_approval_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: str,
) -> None:
    args, clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    closeout_module._cmd_prepare_final_security(args)
    _record_final_security_outcome(clock)
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    monkeypatch.setattr(
        closeout_module,
        "github_api_request",
        lambda *_args, **_kwargs: _final_security_approval_response(
            reference,
            body=body,
        ),
    )
    clock[0] = datetime(2026, 7, 15, 12, 2, tzinfo=timezone.utc)
    args.operator_approval_ref = reference

    with pytest.raises(closeout_module.CloseoutError, match="exactly match"):
        closeout_module._cmd_prepare_final_security(args)


@pytest.mark.parametrize(
    ("response_changes", "error"),
    [
        ({"association": "COLLABORATOR"}, "trusted operator"),
        ({"updated_at": "2026-07-15T12:01:30Z"}, "edited"),
        ({"created_at": "2026-07-15T12:00:00Z"}, "newer than"),
    ],
    ids=["nonmember", "edited", "stale"],
)
def test_prepare_final_security_rejects_untrusted_or_stale_operator_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    response_changes: dict[str, str],
    error: str,
) -> None:
    args, clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    closeout_module._cmd_prepare_final_security(args)
    _record_final_security_outcome(clock)
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    monkeypatch.setattr(
        closeout_module,
        "github_api_request",
        lambda *_args, **_kwargs: _final_security_approval_response(
            reference,
            **response_changes,
        ),
    )
    clock[0] = datetime(2026, 7, 15, 12, 2, tzinfo=timezone.utc)
    args.operator_approval_ref = reference

    with pytest.raises(closeout_module.CloseoutError, match=error):
        closeout_module._cmd_prepare_final_security(args)


def test_prepare_final_security_rejects_reused_operator_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args, clock = _prepare_final_security_fixture(tmp_path, monkeypatch)
    closeout_module._cmd_prepare_final_security(args)
    _record_final_security_outcome(clock)
    reference = "https://github.com/owner/repo/pull/42#issuecomment-456"
    monkeypatch.setattr(
        closeout_module,
        "github_api_request",
        lambda *_args, **_kwargs: _final_security_approval_response(reference),
    )
    clock[0] = datetime(2026, 7, 15, 12, 2, tzinfo=timezone.utc)
    args.operator_approval_ref = reference
    closeout_module._cmd_prepare_final_security(args)
    _record_final_security_outcome(
        clock,
        when=datetime(2026, 7, 15, 12, 2, 30, tzinfo=timezone.utc),
    )
    state_before_reuse = closeout_module._final_security_state_path(42).read_bytes()
    clock[0] = datetime(2026, 7, 15, 12, 3, tzinfo=timezone.utc)

    with pytest.raises(closeout_module.CloseoutError, match="already consumed"):
        closeout_module._cmd_prepare_final_security(args)
    assert closeout_module._final_security_state_path(42).read_bytes() == state_before_reuse


def test_prepare_final_security_parser_keeps_seal_contract_separate() -> None:
    parser = closeout_module._parser()
    args = parser.parse_args(
        [
            "prepare-final-security",
            "--repo",
            "owner/repo",
            "--pr-number",
            "42",
            "--review-ref",
            "https://github.com/owner/repo/pull/42#pullrequestreview-789",
            "--operator-approval-ref",
            "https://github.com/owner/repo/pull/42#issuecomment-456",
        ]
    )

    assert args.handler is closeout_module._cmd_prepare_final_security
    assert args.review_ref.endswith("pullrequestreview-789")
    assert args.review_source_unavailable_ref is None
    assert args.operator_approval_ref.endswith("issuecomment-456")
    assert not hasattr(args, "review_credit_outage_ref")
    assert not hasattr(args, "review_credit_quota_ref")
    assert not hasattr(args, "prior_codex_review_ref")
    assert not hasattr(args, "scan_manifest")
    assert not hasattr(args, "security_outage_override_ref")

    source_args = parser.parse_args(
        [
            "prepare-final-security",
            "--repo",
            "owner/repo",
            "--pr-number",
            "42",
            "--review-source-unavailable-ref",
            "https://github.com/owner/repo/pull/42#issuecomment-456",
        ]
    )
    assert source_args.review_ref is None
    assert source_args.review_source_unavailable_ref.endswith("issuecomment-456")
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "prepare-final-security",
                "--repo",
                "owner/repo",
                "--pr-number",
                "42",
            ]
        )
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "prepare-final-security",
                "--repo",
                "owner/repo",
                "--pr-number",
                "42",
                "--review-ref",
                "https://github.com/owner/repo/pull/42#pullrequestreview-789",
                "--review-source-unavailable-ref",
                "https://github.com/owner/repo/pull/42#issuecomment-456",
            ]
        )

    outcome_args = parser.parse_args(
        [
            "record-final-security-outcome",
            "--repo",
            "owner/repo",
            "--pr-number",
            "42",
            "--outcome",
            "timeout",
            "--evidence-ref",
            "artifact:timeout:attempt-1",
        ]
    )
    assert outcome_args.handler is closeout_module._cmd_record_final_security_outcome


def test_closeout_seal_help_distinguishes_advisory_and_legacy_modes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    parser = closeout_module._parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["seal", "--help"])

    assert exc_info.value.code == 0
    help_text = capsys.readouterr().out
    normalized_help = " ".join(help_text.split())
    assert "closed no-provider advisory variant" in normalized_help
    assert "closed no-claim advisory receipts" in normalized_help
    assert "legacy v1 Connector evidence" in normalized_help
    assert "legacy v1 Codex Security evidence" in normalized_help
    assert "--review-ref" in normalized_help
    assert "--review-source-unavailable-ref" in normalized_help
    assert "--connector-advisory-reaction" in normalized_help
    assert "--scan-manifest" in normalized_help
    assert "--security-outage-override-ref" in normalized_help


def test_closeout_seal_requires_exactly_one_security_evidence_input() -> None:
    parser = closeout_module._parser()
    base = [
        "seal",
        "--repo",
        "owner/repo",
        "--pr-number",
        "42",
    ]
    common = [
        *base,
        "--review-ref",
        "https://github.com/owner/repo/pull/42#issuecomment-456",
    ]

    with pytest.raises(closeout_module.CloseoutError, match="legacy v1 seal requires"):
        closeout_module._validate_seal_evidence_mode(parser.parse_args(common))
    with pytest.raises(closeout_module.CloseoutError, match="legacy v1 seal requires"):
        closeout_module._validate_seal_evidence_mode(
            parser.parse_args(
                [
                    *base,
                    "--scan-manifest",
                    "/tmp/scan-manifest.json",
                ]
            )
        )
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                *common,
                "--scan-manifest",
                "/tmp/scan-manifest.json",
                "--security-outage-override-ref",
                "https://github.com/owner/repo/pull/42#issuecomment-789",
            ]
        )

    scan_args = parser.parse_args([*common, "--scan-manifest", "/tmp/scan-manifest.json"])
    override_args = parser.parse_args(
        [
            *common,
            "--security-outage-override-ref",
            "https://github.com/owner/repo/pull/42#issuecomment-789",
        ]
    )
    source_args = parser.parse_args(
        [
            *base,
            "--review-source-unavailable-ref",
            "https://github.com/owner/repo/pull/42#issuecomment-456",
            "--scan-manifest",
            "/tmp/scan-manifest.json",
        ]
    )
    advisory_args = parser.parse_args(
        [
            *common,
            "--scan-manifest",
            "/tmp/scan-manifest.json",
            "--connector-advisory-reaction",
            "https://github.com/owner/repo/pull/42#reaction-456",
            "--connector-advisory-reaction",
            "https://github.com/owner/repo/pull/42#reaction-457",
        ]
    )
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                *common,
                "--review-source-unavailable-ref",
                "https://github.com/owner/repo/pull/42#issuecomment-456",
                "--scan-manifest",
                "/tmp/scan-manifest.json",
            ]
        )
    assert scan_args.security_outage_override_ref is None
    assert override_args.scan_manifest is None
    assert source_args.review_ref is None
    assert advisory_args.connector_advisory_reaction == [
        "https://github.com/owner/repo/pull/42#reaction-456",
        "https://github.com/owner/repo/pull/42#reaction-457",
    ]
    capability_args = parser.parse_args(
        [
            *base,
            "--capability-sources-advisory",
            "--self-review-report",
            "/tmp/self-review.json",
        ]
    )
    assert closeout_module._validate_seal_evidence_mode(capability_args) is True
    with pytest.raises(closeout_module.CloseoutError, match="closed no-output mode"):
        closeout_module._validate_seal_evidence_mode(
            parser.parse_args(
                [
                    *base,
                    "--capability-sources-advisory",
                    "--scan-manifest",
                    "/tmp/scan-manifest.json",
                ]
            )
        )


@pytest.mark.parametrize(
    "field",
    (
        "review_ref",
        "review_source_unavailable_ref",
        "scan_manifest",
        "security_outage_override_ref",
    ),
)
@pytest.mark.parametrize("value", ("", "present"))
def test_advisory_seal_rejects_empty_or_nonempty_legacy_scalar_before_io(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    values: dict[str, Any] = {
        "capability_sources_advisory": True,
        "connector_advisory_reaction": [],
        "pr_number": 42,
        "repo": "owner/repo",
        "review_ref": None,
        "review_source_unavailable_ref": None,
        "scan_manifest": None,
        "security_outage_override_ref": None,
    }
    values[field] = value
    args = Namespace(**values)
    for name in ("_load_state", "_token", "fetch_pr_snapshot"):
        monkeypatch.setattr(
            closeout_module,
            name,
            lambda *_a, **_k: pytest.fail("invalid evidence mode must precede I/O"),
        )

    with pytest.raises(closeout_module.CloseoutError, match="closed no-output mode"):
        closeout_module._cmd_seal(args)


def test_advisory_seal_rejects_missing_self_review_receipt_before_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = Namespace(
        capability_sources_advisory=True,
        connector_advisory_reaction=[],
        pr_number=42,
        repo="owner/repo",
        review_ref=None,
        review_source_unavailable_ref=None,
        scan_manifest=None,
        security_outage_override_ref=None,
        self_review_report=None,
    )
    for name in ("_load_state", "_token", "fetch_pr_snapshot"):
        monkeypatch.setattr(
            closeout_module,
            name,
            lambda *_a, **_k: pytest.fail("missing self-review must precede I/O"),
        )

    with pytest.raises(closeout_module.CloseoutError, match="requires --self-review-report"):
        closeout_module._cmd_seal(args)


def test_closeout_renders_connector_reactions_as_advisory_without_mutating_seal() -> None:
    security_receipt = build_security_outage_override_receipt(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
        override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
        created_at="2026-07-15T11:00:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )
    seal = _seal(security_receipt)
    reaction = identity_module.CodexConnectorAdvisoryReactionEvidence(
        reference="https://github.com/owner/repo/pull/42#reaction-456",
        created_at="2026-07-15T11:05:00Z",
        content="+1",
    )
    rendered = closeout_module._render_mapping(
        {
            "dispositions": [],
            "experiment_result": None,
            "packet": None,
            "pr_number": 42,
        },
        seal,
        connector_advisory_reactions=(reaction,),
    )

    assert "## Connector Advisory Signals" in rendered
    assert reaction.reference in rendered
    assert "not a review, exact-head proof, GitHub approval, security receipt" in rendered
    assert parse_embedded_review_seal(rendered) == seal
    assert validate_mapping_artifact_text(rendered) == []


def test_closeout_verifies_unique_bounded_connector_advisory_reactions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified: list[str] = []

    def verify(
        reference: str, **_kwargs: Any
    ) -> identity_module.CodexConnectorAdvisoryReactionEvidence:
        verified.append(reference)
        return identity_module.CodexConnectorAdvisoryReactionEvidence(
            reference=reference,
            created_at="2026-07-15T11:05:00Z",
            content="+1",
        )

    monkeypatch.setattr(
        closeout_module,
        "verify_codex_connector_advisory_reaction_reference",
        verify,
    )
    reactions = closeout_module._verify_connector_advisory_reactions(
        [
            "https://github.com/owner/repo/pull/42#reaction-457",
            "https://github.com/owner/repo/pull/42#reaction-456",
        ],
        repository="owner/repo",
        pr_number=42,
        token="opaque",
    )

    assert verified == [
        "https://github.com/owner/repo/pull/42#reaction-457",
        "https://github.com/owner/repo/pull/42#reaction-456",
    ]
    assert [reaction.reference for reaction in reactions] == [
        "https://github.com/owner/repo/pull/42#reaction-456",
        "https://github.com/owner/repo/pull/42#reaction-457",
    ]

    with pytest.raises(closeout_module.CloseoutError, match="must be unique"):
        closeout_module._verify_connector_advisory_reactions(
            ["https://github.com/owner/repo/pull/42#reaction-456"] * 2,
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


def test_closeout_omits_connector_advisory_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def transport_failure(*_args: Any, **_kwargs: Any) -> Any:
        raise http.client.HTTPException("truncated response")

    monkeypatch.setattr(
        closeout_module,
        "verify_codex_connector_advisory_reaction_reference",
        transport_failure,
    )

    reactions = closeout_module._optional_connector_advisory_reactions(
        ["https://github.com/owner/repo/pull/42#reaction-456"],
        repository="owner/repo",
        pr_number=42,
        token="opaque",
    )

    assert reactions == ()
    assert (
        "WARNING: Connector advisory reaction omitted: truncated response"
        in capsys.readouterr().err
    )


def _advisory_seal(
    connector: dict[str, Any],
    security: dict[str, Any],
    *,
    base_sha: str = BASE_SHA,
    head_sha: str = HEAD_SHA,
    digest: str = DIGEST,
) -> dict[str, Any]:
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": connector,
        "codex_security": security,
        "material": {
            "base_ref_oid": base_sha,
            "digest": digest,
            "material_head_sha": head_sha,
            "merge_base_sha": base_sha,
            "policy_version": MATERIAL_POLICY_VERSION,
        },
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": "pulseplate.pr-review-seal/v1",
    }
    seal["self_review"] = build_self_review_receipt(
        material_head_sha=head_sha,
        material_digest=digest,
        completed_at="2026-07-26T15:00:00Z",
        unresolved_actionables=0,
        report_content_digest="sha256:" + "7" * 64,
        report_semantic_digest="sha256:" + "6" * 64,
    )
    return seal


def _write_self_review_report(
    path: Path,
    *,
    head_sha: str,
    material_digest: str,
    findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "1.0.0",
        "generated_at_utc": "2026-07-26T15:00:00Z",
        "mode": "dry-run-report",
        "findings": [] if findings is None else findings,
    }
    receipt = build_self_review_receipt(
        material_head_sha=head_sha,
        material_digest=material_digest,
        completed_at=payload["generated_at_utc"],
        unresolved_actionables=0,
        report_content_digest=self_review_report_content_digest(payload),
        report_semantic_digest=self_review_report_semantic_digest(payload),
    )
    payload["self_review_receipt"] = receipt
    path.write_text(json.dumps(payload), encoding="utf-8")
    return receipt


def _write_advisory_marker(repo: Path, raw: bytes | None = None) -> Path:
    marker = repo / "docs/orchestration/contracts/advisory_capability_sources.v1.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_bytes(advisory_capability_marker_bytes() if raw is None else raw)
    return marker


def _advisory_snapshot(base_sha: str, head_sha: str, *commits: str) -> PrSnapshot:
    return PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=head_sha,
        commits=tuple(PrCommitEvidence(commit, None) for commit in commits),
    )


def test_advisory_capability_receipts_are_closed_material_bound_no_claims() -> None:
    connector, security = build_advisory_capability_receipts(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
    )
    seal = _advisory_seal(connector, security)

    assert parse_embedded_review_seal(render_embedded_review_seal(seal)) == seal
    assert connector["review_claim"] == "none"
    assert connector["output_required"] is False
    assert security["scan_claim"] == "none"
    assert security["no_findings_claim"] is False
    assert security["scan_id"] is None
    assert security["substitute_security_bundle_required"] is True

    tampered = json.loads(json.dumps(seal))
    tampered["code_review"]["review_claim"] = "completed"
    with pytest.raises(ReviewEvidenceError, match="advisory capability receipt"):
        render_embedded_review_seal(tampered)


def test_advisory_self_review_receipt_is_closed_and_material_bound() -> None:
    receipt = build_self_review_receipt(
        material_head_sha=HEAD_SHA,
        material_digest=DIGEST,
        completed_at="2026-07-26T15:00:00Z",
        unresolved_actionables=0,
        report_content_digest="sha256:" + "8" * 64,
        report_semantic_digest="sha256:" + "6" * 64,
    )

    assert (
        validate_self_review_receipt(
            receipt,
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
            report_semantic_digest="sha256:" + "6" * 64,
        )
        == receipt
    )

    with pytest.raises(ReviewEvidenceError, match="canonical report semantics"):
        validate_self_review_receipt(
            receipt,
            report_semantic_digest="sha256:" + "5" * 64,
        )

    for field, value in (
        ("content_digest", "sha256:" + "0" * 64),
        ("report_id", "self-review-" + "0" * 64),
        ("report_semantic_digest", "sha256:" + "0" * 64),
        ("status", "incomplete"),
        ("completed_at", "2026-07-26T15:00:00+00:00"),
        ("unresolved_actionables", True),
    ):
        tampered = json.loads(json.dumps(receipt))
        tampered[field] = value
        with pytest.raises(ReviewEvidenceError):
            validate_self_review_receipt(tampered)


def test_self_review_report_ingestion_rejects_unresolved_or_tampered_evidence(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "self-review.json"
    receipt = _write_self_review_report(
        report_path,
        head_sha=HEAD_SHA,
        material_digest=DIGEST,
    )

    assert (
        ingest_self_review_report(
            report_path,
            expected_head_sha=HEAD_SHA,
            expected_material_digest=DIGEST,
        )
        == receipt
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["findings"] = [
        {
            "severity": "major",
            "disposition_candidate": "NEEDS-HUMAN",
        }
    ]
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ReviewEvidenceError, match="canonical report content"):
        ingest_self_review_report(
            report_path,
            expected_head_sha=HEAD_SHA,
            expected_material_digest=DIGEST,
        )

    payload["self_review_receipt"] = build_self_review_receipt(
        material_head_sha=HEAD_SHA,
        material_digest=DIGEST,
        completed_at=payload["generated_at_utc"],
        unresolved_actionables=0,
        report_content_digest=self_review_report_content_digest(payload),
        report_semantic_digest=self_review_report_semantic_digest(payload),
    )
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ReviewEvidenceError, match="unresolved actionables"):
        ingest_self_review_report(
            report_path,
            expected_head_sha=HEAD_SHA,
            expected_material_digest=DIGEST,
        )


def test_self_review_report_ingestion_rejects_noncanonical_live_context(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "self-review.json"
    _write_self_review_report(
        report_path,
        head_sha=HEAD_SHA,
        material_digest=DIGEST,
    )
    expected = json.loads(report_path.read_text(encoding="utf-8"))
    expected["scope_reviewed"] = {"changed_files": ["scripts/orchestration/pr_review_evidence.py"]}

    with pytest.raises(ReviewEvidenceError, match="canonical live review context"):
        ingest_self_review_report(
            report_path,
            expected_head_sha=HEAD_SHA,
            expected_material_digest=DIGEST,
            expected_report=expected,
        )


def test_historical_advisory_seal_without_self_review_remains_parseable() -> None:
    connector, security = build_advisory_capability_receipts(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
    )
    historical = _advisory_seal(connector, security)
    historical.pop("self_review")

    assert parse_embedded_review_seal(render_embedded_review_seal(historical)) == historical


def test_advisory_capability_receipts_require_linked_connector_and_security_variants() -> None:
    connector, security = build_advisory_capability_receipts(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
    )
    seal = _advisory_seal(connector, security)
    legacy_security = build_security_outage_override_receipt(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
        override_reference="https://github.com/owner/repo/pull/42#issuecomment-789",
        created_at="2026-07-15T11:00:00Z",
        operator_user_id=123,
        operator_login="owner",
        operator_association="OWNER",
    )

    connector_only = json.loads(json.dumps(seal))
    connector_only["codex_security"] = legacy_security
    with pytest.raises(ReviewEvidenceError, match="requires linked Connector and Security"):
        render_embedded_review_seal(connector_only)

    security_only = _seal(security)
    with pytest.raises(ReviewEvidenceError, match="requires linked Connector and Security"):
        render_embedded_review_seal(security_only)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("security_result", "passed", "keys mismatch"),
        ("scan_claim", "completed", "receipt is malformed"),
        ("no_findings_claim", True, "receipt is malformed"),
    ],
)
def test_advisory_security_receipt_rejects_unknown_or_claim_fields(
    field: str,
    value: Any,
    error: str,
) -> None:
    connector, security = build_advisory_capability_receipts(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
    )
    security[field] = value
    seal = _advisory_seal(connector, security)

    with pytest.raises(ReviewEvidenceError, match=error):
        render_embedded_review_seal(seal)


def test_closeout_advisory_seal_and_authenticated_mapping_successor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _write_advisory_marker(repo)
    base_sha = _commit(repo, "activate advisory capability")
    source = repo / "src" / "policy.py"
    source.parent.mkdir(parents=True)
    source.write_text("ENFORCED = True\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    material = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=material_head,
        pr_number=42,
    )
    freeze = {
        "base_ref_oid": base_sha,
        "digest": material.digest,
        "material_head_sha": material_head,
        "merge_base_sha": material.merge_base_sha,
        "policy_version": MATERIAL_POLICY_VERSION,
    }
    state = {
        "dispositions": [],
        "experiment_result": None,
        "freeze": freeze,
        "packet": None,
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": closeout_module.DRAFT_SCHEMA_VERSION,
    }
    target = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
    snapshots = [_advisory_snapshot(base_sha, material_head, material_head)]
    real_closeout_git = closeout_module._git

    def git_with_synthetic_live_head(*args: str) -> str:
        if args == ("rev-parse", "HEAD"):
            return snapshots[0].head_sha
        return real_closeout_git(*args)

    monkeypatch.setattr(closeout_module, "REPO_ROOT", repo)
    monkeypatch.setattr(closeout_module, "_load_state", lambda _pr: state)
    monkeypatch.setattr(closeout_module, "_token", lambda: "opaque")
    monkeypatch.setattr(closeout_module, "fetch_pr_snapshot", lambda *_a, **_k: snapshots[0])
    monkeypatch.setattr(closeout_module, "_require_clean_live_head", lambda _head: None)
    monkeypatch.setattr(closeout_module, "_git", git_with_synthetic_live_head)
    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: target)
    monkeypatch.setattr(closeout_module, "assert_snapshot_unchanged", lambda *_a, **_k: None)
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_reference",
        lambda *_a, **_k: pytest.fail("advisory seal must not verify Connector output"),
    )
    monkeypatch.setattr(
        closeout_module,
        "ingest_codex_security_receipt",
        lambda *_a, **_k: pytest.fail("advisory seal must not ingest plugin output"),
    )
    self_review_report = tmp_path / "self-review.json"
    expected_self_review = _write_self_review_report(
        self_review_report,
        head_sha=material_head,
        material_digest=material.digest,
    )
    canonical_self_review_report = json.loads(self_review_report.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        closeout_module,
        "collect_review_context",
        lambda **_kwargs: {},
    )
    monkeypatch.setattr(
        closeout_module,
        "build_report",
        lambda *_args, **_kwargs: canonical_self_review_report,
    )

    closeout_module._cmd_seal(
        Namespace(
            capability_sources_advisory=True,
            connector_advisory_reaction=[],
            pr_number=42,
            repo="owner/repo",
            review_ref=None,
            review_source_unavailable_ref=None,
            scan_manifest=None,
            security_outage_override_ref=None,
            self_review_report=str(self_review_report),
        )
    )

    authored = parse_embedded_review_seal(target.read_text(encoding="utf-8"))
    assert authored["code_review"]["review_claim"] == "none"
    assert authored["codex_security"]["scan_claim"] == "none"
    assert authored["self_review"] == expected_self_review
    mapping_head = _commit(repo, "mapping-only closeout")
    snapshots[0] = _advisory_snapshot(base_sha, mapping_head, material_head, mapping_head)
    monkeypatch.setattr(
        closeout_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(
            value,
            CommitRefKind.PR_COMMIT if value == material_head else CommitRefKind.PR_HEAD,
        ),
    )
    monkeypatch.setattr(closeout_module, "is_ancestor", lambda *_a, **_k: True)

    assert (
        closeout_module.validate_live_mapping(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )
        == authored
    )

    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    second_mapping_head = _commit(repo, "second mapping-only commit")
    snapshots[0] = _advisory_snapshot(
        base_sha,
        second_mapping_head,
        material_head,
        mapping_head,
        second_mapping_head,
    )
    with pytest.raises(ReviewEvidenceError, match="one direct child"):
        closeout_module.validate_live_mapping(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )

    source.write_text("ENFORCED = False\n", encoding="utf-8")
    material_descendant = _commit(repo, "material descendant")
    snapshots[0] = _advisory_snapshot(
        base_sha,
        material_descendant,
        material_head,
        mapping_head,
        second_mapping_head,
        material_descendant,
    )
    with pytest.raises(closeout_module.CloseoutError, match="stale for the live material state"):
        closeout_module.validate_live_mapping(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


@pytest.mark.parametrize(
    "authorizer_path",
    [
        *sorted(ADVISORY_CAPABILITY_AUTHORIZING_PATHS),
        *(f"{prefix}authority.yml" for prefix in ADVISORY_CAPABILITY_AUTHORIZING_PREFIXES),
    ],
)
def test_advisory_capability_denies_all_authority_self_use_paths(
    tmp_path: Path,
    authorizer_path: str,
) -> None:
    with pytest.raises(ReviewEvidenceError, match="SELF_USE_DENIED"):
        validate_advisory_capability_activation(
            tmp_path,
            base_ref_oid=BASE_SHA,
            head_ref_oid=HEAD_SHA,
            material_paths=(authorizer_path,),
        )


@pytest.mark.parametrize(
    "protected_path",
    (
        "scripts/orchestration/pr_commit_identity.py",
        "scripts/orchestration/review_mapping_artifact.py",
        "scripts/orchestration/check_review_threads_disposition.py",
        "scripts/ci/check_pr_body_phase2_gates.py",
        "scripts/ci_bandit.sh",
        "scripts/ci_pip_audit.sh",
        "scripts/ci/summarize_bandit_report.py",
        "scripts/ci/check_trivy_ignore_policy_expiry.py",
        ".bandit",
        ".trivyignore",
        "trivy/ignore-policy.rego",
    ),
)
def test_advisory_self_use_rejects_full_outage_boundary_examples(
    tmp_path: Path,
    protected_path: str,
) -> None:
    with pytest.raises(ReviewEvidenceError, match=re.escape(protected_path)):
        validate_advisory_capability_activation(
            tmp_path,
            base_ref_oid=BASE_SHA,
            head_ref_oid=HEAD_SHA,
            material_paths=(protected_path,),
        )


@pytest.mark.parametrize(
    ("raw_entry", "error"),
    [
        (b"", "marker missing"),
        (
            f"120000 blob {'a' * 40}\t"
            "docs/orchestration/contracts/advisory_capability_sources.v1.json\0".encode(),
            "exactly one 100644 blob",
        ),
        (
            f"100755 blob {'a' * 40}\t"
            "docs/orchestration/contracts/advisory_capability_sources.v1.json\0".encode(),
            "exactly one 100644 blob",
        ),
        (
            f"040000 tree {'a' * 40}\t"
            "docs/orchestration/contracts/advisory_capability_sources.v1.json\0".encode(),
            "exactly one 100644 blob",
        ),
        (
            f"160000 commit {'a' * 40}\t"
            "docs/orchestration/contracts/advisory_capability_sources.v1.json\0".encode(),
            "exactly one 100644 blob",
        ),
        (b"malformed\0", "tree entry is malformed"),
        (
            f"100644 blob {'b' * 40}\t"
            "docs/orchestration/contracts/advisory_capability_sources.v1.json\0".encode(),
            "blob OID differs",
        ),
        (
            (
                f"100644 blob {'a' * 40}\t"
                "docs/orchestration/contracts/advisory_capability_sources.v1.json\0"
            ).encode()
            * 2,
            "exactly one 100644 blob",
        ),
    ],
)
def test_advisory_marker_rejects_noncanonical_git_objects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_entry: bytes,
    error: str,
) -> None:
    def run_git(_root: Path, args: list[str], **_kwargs: Any) -> bytes:
        if args[0] == "ls-tree":
            return raw_entry
        pytest.fail(f"unexpected git command: {args}")

    monkeypatch.setattr(evidence_module, "_run_git", run_git)
    with pytest.raises(ReviewEvidenceError, match=error):
        evidence_module._require_advisory_marker_at_revision(
            tmp_path,
            revision=BASE_SHA,
            label="authenticated base",
            expected_bytes=advisory_capability_marker_bytes(),
            expected_oid="a" * 40,
        )


def test_advisory_marker_rejects_blob_bytes_that_do_not_match_oid_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = (
        f"100644 blob {'a' * 40}\t"
        "docs/orchestration/contracts/advisory_capability_sources.v1.json\0"
    ).encode()

    def run_git(_root: Path, args: list[str], **_kwargs: Any) -> bytes:
        return entry if args[0] == "ls-tree" else b"{}\n"

    monkeypatch.setattr(evidence_module, "_run_git", run_git)
    with pytest.raises(ReviewEvidenceError, match="marker bytes differ"):
        evidence_module._require_advisory_marker_at_revision(
            tmp_path,
            revision=BASE_SHA,
            label="authenticated base",
            expected_bytes=advisory_capability_marker_bytes(),
            expected_oid="a" * 40,
        )


@pytest.mark.parametrize(
    ("raw_entry", "error"),
    [
        (b"", "canonical mapping artifact is missing"),
        (
            f"040000 tree {'a' * 40}\t" "docs/review/PR_42_FIXED_MAPPING.md\0".encode(),
            "exactly one regular 100644 blob",
        ),
        (b"malformed\0", "canonical mapping tree entry is malformed"),
        (
            (f"100644 blob {'a' * 40}\t" "docs/review/PR_42_FIXED_MAPPING.md\0").encode() * 2,
            "exactly one regular 100644 blob",
        ),
    ],
)
def test_advisory_mapping_entry_rejects_missing_tree_malformed_or_duplicate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_entry: bytes,
    error: str,
) -> None:
    def run_git(_root: Path, args: list[str], **_kwargs: Any) -> bytes:
        assert args == [
            "ls-tree",
            "-z",
            "--full-tree",
            HEAD_SHA,
            "--",
            "docs/review/PR_42_FIXED_MAPPING.md",
        ]
        return raw_entry

    monkeypatch.setattr(evidence_module, "_run_git", run_git)
    with pytest.raises(ReviewEvidenceError, match=error):
        evidence_module._require_canonical_mapping_blob_at_revision(
            tmp_path,
            revision=HEAD_SHA,
            expected_path="docs/review/PR_42_FIXED_MAPPING.md",
        )


@pytest.mark.parametrize(
    ("entry_kind", "expected_entry_prefix"),
    [
        ("symlink", "120000 blob "),
        ("executable", "100755 blob "),
        ("gitlink", "160000 commit "),
    ],
)
def test_advisory_live_head_rejects_nonregular_mapping_entry(
    tmp_path: Path,
    entry_kind: str,
    expected_entry_prefix: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "policy.txt").write_text("stable\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    if entry_kind == "symlink":
        mapping.symlink_to("noncanonical-target")
    elif entry_kind == "executable":
        mapping.write_text("mapping\n", encoding="utf-8")
        mapping.chmod(0o755)
    else:
        mapping.mkdir()
        _git(mapping, "init", "-q")
        (mapping / "README.md").write_text("nested\n", encoding="utf-8")
        _commit(mapping, "nested mapping gitlink")
    mapping_child = _commit(repo, f"{entry_kind} mapping child")
    mapping_path = mapping.relative_to(repo).as_posix()

    assert _git(repo, "ls-tree", mapping_child, "--", mapping_path).startswith(
        expected_entry_prefix
    )
    with pytest.raises(ReviewEvidenceError, match="exactly one regular 100644 blob"):
        validate_advisory_live_head_topology(
            repo,
            material_head_sha=material_head,
            live_head_sha=mapping_child,
            pr_number=42,
            phase="final",
        )


def test_advisory_live_head_requires_exact_phase_and_one_mapping_child(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    source = repo / "src" / "policy.py"
    source.parent.mkdir(parents=True)
    source.write_text("stable\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)

    validate_advisory_live_head_topology(
        repo,
        material_head_sha=material_head,
        live_head_sha=material_head,
        pr_number=42,
        phase="pre_closeout",
    )
    with pytest.raises(ReviewEvidenceError, match="final live head must be one mapping-only child"):
        validate_advisory_live_head_topology(
            repo,
            material_head_sha=material_head,
            live_head_sha=material_head,
            pr_number=42,
            phase="final",
        )

    mapping.write_text("mapping\n", encoding="utf-8")
    mapping_child = _commit(repo, "mapping child")
    validate_advisory_live_head_topology(
        repo,
        material_head_sha=material_head,
        live_head_sha=mapping_child,
        pr_number=42,
        phase="final",
    )
    with pytest.raises(ReviewEvidenceError, match="pre-closeout live head must equal"):
        validate_advisory_live_head_topology(
            repo,
            material_head_sha=material_head,
            live_head_sha=mapping_child,
            pr_number=42,
            phase="pre_closeout",
        )

    mapping.write_text("mapping two\n", encoding="utf-8")
    second_child = _commit(repo, "second mapping commit")
    with pytest.raises(ReviewEvidenceError, match="one direct child"):
        validate_advisory_live_head_topology(
            repo,
            material_head_sha=material_head,
            live_head_sha=second_child,
            pr_number=42,
            phase="final",
        )

    _git(repo, "checkout", "-q", material_head)
    mapping.parent.mkdir(parents=True)
    mapping.write_text("mapping with material\n", encoding="utf-8")
    source.write_text("changed\n", encoding="utf-8")
    material_child = _commit(repo, "mapping and material child")
    with pytest.raises(ReviewEvidenceError, match="must change only"):
        validate_advisory_live_head_topology(
            repo,
            material_head_sha=material_head,
            live_head_sha=material_child,
            pr_number=42,
            phase="final",
        )

    source.write_text("stable\n", encoding="utf-8")
    mapping.write_text("mapping after revert\n", encoding="utf-8")
    reverted_head = _commit(repo, "revert material change")
    with pytest.raises(ReviewEvidenceError, match="one direct child"):
        validate_advisory_live_head_topology(
            repo,
            material_head_sha=material_head,
            live_head_sha=reverted_head,
            pr_number=42,
            phase="final",
        )


def test_advisory_capability_checks_distinct_base_and_merge_base_marker_bytes(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    marker = _write_advisory_marker(repo)
    merge_base = _commit(repo, "marker at shared ancestor")
    base_branch = _git(repo, "branch", "--show-current")
    _git(repo, "checkout", "-q", "-b", "feature", merge_base)
    (repo / "feature.txt").write_text("material\n", encoding="utf-8")
    head_sha = _commit(repo, "feature material")
    _git(repo, "checkout", "-q", base_branch)
    (repo / "base.txt").write_text("base advance\n", encoding="utf-8")
    base_sha = _commit(repo, "authenticated base advance")

    assert (
        validate_advisory_capability_activation(
            repo,
            base_ref_oid=base_sha,
            head_ref_oid=head_sha,
            material_paths=("feature.txt",),
        )
        == merge_base
    )

    marker.write_text("{}\n", encoding="utf-8")
    drifted_base = _commit(repo, "drift marker on authenticated base")
    with pytest.raises(ReviewEvidenceError, match="blob OID differs in authenticated base"):
        validate_advisory_capability_activation(
            repo,
            base_ref_oid=drifted_base,
            head_ref_oid=head_sha,
            material_paths=("feature.txt",),
        )


@pytest.mark.parametrize(
    ("merge_marker", "error"),
    [
        (b"{}\n", "blob OID differs in unique merge-base"),
        (None, "marker missing from unique merge-base"),
    ],
)
def test_advisory_capability_rejects_bad_marker_at_distinct_merge_base(
    tmp_path: Path,
    merge_marker: bytes | None,
    error: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    marker = (
        _write_advisory_marker(repo, merge_marker)
        if merge_marker is not None
        else repo / "docs/orchestration/contracts/advisory_capability_sources.v1.json"
    )
    if merge_marker is None:
        (repo / "README.md").write_text("base without marker\n", encoding="utf-8")
    merge_base = _commit(repo, "drifted marker at shared ancestor")
    base_branch = _git(repo, "branch", "--show-current")
    _git(repo, "checkout", "-q", "-b", "feature", merge_base)
    (repo / "feature.txt").write_text("material\n", encoding="utf-8")
    head_sha = _commit(repo, "feature material")
    _git(repo, "checkout", "-q", base_branch)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_bytes(advisory_capability_marker_bytes())
    base_sha = _commit(repo, "fix marker only on authenticated base")

    with pytest.raises(ReviewEvidenceError, match=error) as exc_info:
        validate_advisory_capability_activation(
            repo,
            base_ref_oid=base_sha,
            head_ref_oid=head_sha,
            material_paths=("feature.txt",),
        )
    assert str(exc_info.value).startswith("ADVISORY_CAPABILITY_INACTIVE:")
    assert "refresh the PR from that base" in str(exc_info.value)


def test_advisory_capability_rejects_missing_marker(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base_sha = _commit(repo, "base without marker")
    (repo / "README.md").write_text("material\n", encoding="utf-8")
    head_sha = _commit(repo, "material")

    with pytest.raises(
        ReviewEvidenceError, match="marker missing from authenticated base"
    ) as exc_info:
        validate_advisory_capability_activation(
            repo,
            base_ref_oid=base_sha,
            head_ref_oid=head_sha,
            material_paths=("README.md",),
        )
    assert "merge the prerequisite into the authenticated base" in str(exc_info.value)


def test_advisory_capability_rejects_non_unique_merge_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        evidence_module,
        "_run_git",
        lambda *_a, **_k: f"{BASE_SHA}\n{HEAD_SHA}\n".encode(),
    )

    with pytest.raises(ReviewEvidenceError, match="exactly one unique merge-base"):
        validate_advisory_capability_activation(
            tmp_path,
            base_ref_oid=BASE_SHA,
            head_ref_oid=HEAD_SHA,
            material_paths=(),
        )
