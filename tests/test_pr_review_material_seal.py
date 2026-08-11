"""Focused fail-closed tests for real PR commits and material review seals."""

from __future__ import annotations

from collections.abc import Iterator
import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import urllib.parse
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
from scripts.orchestration import pr_review_context as review_context_module
from scripts.orchestration import pr_review_evidence as evidence_module
from scripts.orchestration import pr_review_report as review_report_module
from scripts.orchestration.pr_review_evidence import (
    MATERIAL_POLICY_VERSION,
    RECEIPT_AUTHORITY,
    SEAL_BEGIN,
    SEAL_END,
    MaterialDiffSummary,
    MaterialManifest,
    ReviewEvidenceError,
    build_provider_no_claim_pair,
    build_review_credit_outage_receipt,
    build_review_source_positive_response_receipt,
    build_review_source_unavailability_receipt,
    build_security_outage_override_receipt,
    compute_material_manifest,
    ingest_codex_security_receipt,
    ingest_repo_native_self_review_receipt,
    is_provider_no_claim_review_receipt,
    is_provider_no_claim_security_receipt,
    is_review_credit_outage_receipt,
    is_review_source_positive_response_receipt,
    is_review_source_unavailability_receipt,
    is_security_outage_override_receipt,
    parse_duplicate_disposition_reply,
    parse_embedded_review_seal,
    render_embedded_review_seal,
    review_thread_inventory,
    unavailable_review_ref_fingerprint,
    validate_review_credit_outage_scope,
    validate_security_outage_override_scope,
    validated_duplicate_reply_urls,
)
from scripts.orchestration.review_mapping_artifact import (
    CanonicalFingerprintRecord,
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


def _material_manifest(
    head_sha: str,
    *,
    base_ref_oid: str = BASE_SHA,
    merge_base_sha: str = BASE_SHA,
    digest: str = DIGEST,
    paths: tuple[str, ...] = (),
    additions: int = 0,
    deletions: int = 0,
) -> MaterialManifest:
    return MaterialManifest(
        base_ref_oid=base_ref_oid,
        head_ref_oid=head_sha,
        merge_base_sha=merge_base_sha,
        pr_number=42,
        entries=tuple(
            evidence_module.MaterialEntry(
                status="M",
                path=path,
                base_mode="100644",
                base_blob_oid="a" * 40,
                head_mode="100644",
                head_blob_oid="b" * 40,
            )
            for path in paths
        ),
        digest=digest,
        diff_summary=MaterialDiffSummary(
            files=len(paths),
            additions=additions,
            deletions=deletions,
        ),
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


def test_global_commit_classifier_rejects_short_sha_without_api_request() -> None:
    calls = 0

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        raise AssertionError("global classifier must reject short SHA before API access")

    resolution = classify_commit_ref(
        "a" * 7,
        _snapshot(),
        token="opaque",
        request_json=request_json,
    )

    assert isinstance(resolution, ReviewExecutionRef)
    assert resolution.kind is CommitRefKind.API_UNKNOWN
    assert calls == 0


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


@pytest.mark.parametrize(
    "path",
    (
        ".flake8",
        ".github/CODEOWNERS",
        ".markdownlint.json",
        ".yamllint",
        "CODEOWNERS",
        "docs/design/figma-manifest.json",
        "docs/CODEOWNERS",
        "docs/telemetry/docker_image_baseline.production.json",
        "docs/telemetry/docker_image_budget.production.json",
        "pyproject.toml",
        "pyrightconfig.json",
        "scripts/design_guard.py",
    ),
)
def test_security_outage_trust_boundary_covers_authority_inputs(path: str) -> None:
    assert evidence_module.protected_trust_boundary_paths((path,)) == (path,)

    with pytest.raises(ReviewEvidenceError, match="trust-boundary changes"):
        validate_security_outage_override_scope(
            repository="owner/repo",
            pr_number=42,
            material_paths=(path,),
        )


def test_security_outage_trust_boundary_rejects_nested_noncanonical_codeowners() -> None:
    path = ".github/config/CODEOWNERS"

    assert evidence_module.protected_trust_boundary_paths((path,)) == ()


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


def _commit(repo: Path, message: str, *, allow_empty: bool = False) -> str:
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
    commit_args = ["commit", "-m", message]
    if allow_empty:
        commit_args.append("--allow-empty")
    _git(repo, *commit_args, env=env)
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


def _self_review_report_payload(
    *,
    changed_files: tuple[str, ...] = (),
    findings: tuple[dict[str, Any], ...] = (),
    base_ref_oid: str = BASE_SHA,
    merge_base_sha: str = BASE_SHA,
    material_head_sha: str = HEAD_SHA,
    material_digest: str = DIGEST,
) -> dict[str, Any]:
    return {
        "actionable_findings_count": sum(
            finding.get("severity") in evidence_module.SELF_REVIEW_ACTIONABLE_SEVERITIES
            for finding in findings
        ),
        "base_ref_oid": base_ref_oid,
        "calibration": {},
        "coordinator_packet": {},
        "decision_log": [],
        "deferred_followups": [],
        "findings": list(findings),
        "findings_count": len(findings),
        "gate_plan": [],
        "generated_at_utc": "2026-07-27T00:00:00Z",
        "material_digest": material_digest,
        "material_head_sha": material_head_sha,
        "merge_base_sha": merge_base_sha,
        "mode": "dry-run-report",
        "review_source_status": [],
        "role_review": [],
        "schema_version": "2.0.0",
        "scope_reviewed": {
            "changed_files": list(changed_files),
            "diff_summary": {
                "additions": 0,
                "changed_lines": 0,
                "deletions": 0,
                "files": len(changed_files),
            },
            "fixed_mapping_errors": [],
            "pr_metadata_available": True,
            "scoped_agents_md": review_context_module.discover_scoped_agents(
                evidence_module._REPO_ROOT,
                list(changed_files),
            ),
        },
        "warnings": [],
    }


def _self_review_receipt(report: dict[str, Any]) -> dict[str, Any]:
    canonical = json.dumps(
        report,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "actionable_findings_count": report["actionable_findings_count"],
        "authority": "repo_native_pulseplate_pr_review_advisory",
        "blocking": False,
        "findings_count": report["findings_count"],
        "material_digest": report["material_digest"],
        "material_head_sha": report["material_head_sha"],
        "report_payload": report,
        "report_sha256": "sha256:" + hashlib.sha256(canonical).hexdigest(),
        "review_claim": "none",
        "review_tool": "pulseplate-pr-review",
        "schema_version": "pulseplate.self-review-advisory/v1",
        "status": "advisory_report_attached",
    }


def _provider_no_claim_seal() -> dict[str, Any]:
    code_review, codex_security = build_provider_no_claim_pair(
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
        material_digest=DIGEST,
    )
    seal = _seal(codex_security)
    seal["code_review"] = code_review
    seal["self_review"] = _self_review_receipt(_self_review_report_payload())
    return seal


def _write_self_review_report(
    path: Path,
    *,
    changed_files: tuple[str, ...] = (),
    findings: tuple[dict[str, Any], ...] = (),
    base_ref_oid: str = BASE_SHA,
    merge_base_sha: str = BASE_SHA,
    material_head_sha: str = HEAD_SHA,
    material_digest: str = DIGEST,
) -> Path:
    _write_json(
        path,
        _self_review_report_payload(
            changed_files=changed_files,
            findings=findings,
            base_ref_oid=base_ref_oid,
            merge_base_sha=merge_base_sha,
            material_head_sha=material_head_sha,
            material_digest=material_digest,
        ),
    )
    return path


def test_provider_no_claim_pair_is_exact_static_and_material_bound() -> None:
    parsed = parse_embedded_review_seal(render_embedded_review_seal(_provider_no_claim_seal()))

    assert is_provider_no_claim_review_receipt(parsed["code_review"])
    assert is_provider_no_claim_security_receipt(parsed["codex_security"])
    assert parsed["code_review"] == {
        "blocking": False,
        "material_digest": DIGEST,
        "material_head_sha": HEAD_SHA,
        "output_required": False,
        "review_claim": "none",
    }
    assert parsed["codex_security"] == {
        "base_revision": BASE_SHA,
        "blocking": False,
        "head_revision": HEAD_SHA,
        "material_digest": DIGEST,
        "no_findings_claim": False,
        "output_required": False,
        "scan_claim": "none",
    }
    assert set(parsed["self_review"]) == {
        "actionable_findings_count",
        "authority",
        "blocking",
        "findings_count",
        "material_digest",
        "material_head_sha",
        "report_payload",
        "report_sha256",
        "review_claim",
        "review_tool",
        "schema_version",
        "status",
    }
    assert parsed["self_review"]["schema_version"] == "pulseplate.self-review-advisory/v1"
    assert parsed["self_review"]["authority"] == ("repo_native_pulseplate_pr_review_advisory")
    assert parsed["self_review"]["review_tool"] == "pulseplate-pr-review"
    assert parsed["self_review"]["review_claim"] == "none"
    assert parsed["self_review"]["blocking"] is False
    assert parsed["self_review"]["status"] == "advisory_report_attached"


def test_provider_no_claim_requires_exact_material_self_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scoped_agents = review_context_module.discover_scoped_agents(
        evidence_module._REPO_ROOT,
        ["app/example.py"],
    )
    monkeypatch.setattr(
        evidence_module,
        "_applicable_scoped_agents",
        lambda _paths, *, material_head_sha: scoped_agents,
    )
    manifest = _material_manifest(HEAD_SHA, paths=("app/example.py",))
    report_path = _write_self_review_report(
        tmp_path / "review.json",
        changed_files=("app/example.py",),
    )
    receipt = ingest_repo_native_self_review_receipt(
        report_path,
        material_manifest=manifest,
    )

    assert receipt["material_head_sha"] == HEAD_SHA
    assert receipt["material_digest"] == DIGEST
    assert receipt["report_sha256"].startswith("sha256:")

    with pytest.raises(ReviewEvidenceError, match="exact material path set"):
        ingest_repo_native_self_review_receipt(
            report_path,
            material_manifest=_material_manifest(HEAD_SHA, paths=("app/other.py",)),
        )

    symlinked_report = tmp_path / "symlinked-review.json"
    symlinked_report.symlink_to(report_path)
    with pytest.raises(ReviewEvidenceError, match="missing, unsafe, or unreadable"):
        ingest_repo_native_self_review_receipt(
            symlinked_report,
            material_manifest=manifest,
        )

    missing = _provider_no_claim_seal()
    del missing["self_review"]
    with pytest.raises(ReviewEvidenceError, match="requires an exact-material"):
        render_embedded_review_seal(missing)

    stale = _provider_no_claim_seal()
    stale["self_review"]["material_head_sha"] = FIX_SHA
    with pytest.raises(ReviewEvidenceError, match="malformed or stale"):
        render_embedded_review_seal(stale)


@pytest.mark.parametrize(
    ("operation", "expected_scopes", "tampered_scopes"),
    (
        (
            "add",
            ["AGENTS.md", "frontend/AGENTS.md"],
            ["AGENTS.md"],
        ),
        (
            "delete",
            ["AGENTS.md"],
            ["AGENTS.md", "frontend/AGENTS.md"],
        ),
    ),
)
def test_self_review_scoped_agents_are_resolved_from_material_head_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    expected_scopes: list[str],
    tampered_scopes: list[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(evidence_module, "_REPO_ROOT", repo)
    _git(repo, "init", "-q")
    (repo / "AGENTS.md").write_text("root instructions\n", encoding="utf-8")
    frontend = repo / "frontend"
    frontend.mkdir()
    scoped_agents_path = frontend / "AGENTS.md"
    if operation == "delete":
        scoped_agents_path.write_text("frontend instructions\n", encoding="utf-8")
    base = _commit(repo, "base")

    if operation == "add":
        scoped_agents_path.write_text("frontend instructions\n", encoding="utf-8")
    else:
        scoped_agents_path.unlink()
    head = _commit(repo, f"{operation} scoped agents")

    manifest = compute_material_manifest(
        repo,
        base_ref_oid=base,
        head_ref_oid=head,
        pr_number=42,
    )
    assert manifest.diff_summary is not None
    changed_files = tuple(entry.path for entry in manifest.entries)
    report = _self_review_report_payload(
        changed_files=changed_files,
        base_ref_oid=base,
        merge_base_sha=manifest.merge_base_sha,
        material_head_sha=head,
        material_digest=manifest.digest,
    )
    report["scope_reviewed"]["diff_summary"] = manifest.diff_summary.as_dict()
    report["scope_reviewed"]["scoped_agents_md"] = expected_scopes
    report_path = tmp_path / "review.json"
    _write_json(report_path, report)

    _git(repo, "checkout", "-q", "--detach", base)
    assert scoped_agents_path.is_file() is (operation == "delete")
    assert (
        ingest_repo_native_self_review_receipt(
            report_path,
            material_manifest=manifest,
        )["status"]
        == "advisory_report_attached"
    )

    report["scope_reviewed"]["scoped_agents_md"] = tampered_scopes
    _write_json(report_path, report)
    with pytest.raises(
        ReviewEvidenceError,
        match="scoped AGENTS.md coverage does not match the exact material paths",
    ):
        ingest_repo_native_self_review_receipt(
            report_path,
            material_manifest=manifest,
        )


def test_self_review_material_paths_are_materialized_at_validation_entry() -> None:
    consumed = False

    def material_paths() -> Iterator[str]:
        nonlocal consumed
        yield "app/example.py"
        consumed = True

    with pytest.raises(ReviewEvidenceError, match="report must be an object"):
        evidence_module._validate_self_review_report_payload(
            None,
            base_ref_oid=BASE_SHA,
            merge_base_sha=BASE_SHA,
            material_head_sha=HEAD_SHA,
            material_digest=DIGEST,
            material_paths=material_paths(),
        )

    assert consumed is True


@pytest.mark.parametrize(
    "current_manifest",
    (
        _material_manifest(FIX_SHA, paths=("app/example.py",)),
        _material_manifest(
            HEAD_SHA,
            digest="sha256:" + "f" * 64,
            paths=("app/example.py",),
        ),
    ),
    ids=("changed-head-same-path-set", "changed-digest-same-path-set"),
)
def test_self_review_report_cannot_rebind_across_changed_material_with_same_paths(
    tmp_path: Path,
    current_manifest: MaterialManifest,
) -> None:
    report_path = _write_self_review_report(
        tmp_path / "review.json",
        changed_files=("app/example.py",),
    )

    with pytest.raises(ReviewEvidenceError, match="stale for the exact material"):
        ingest_repo_native_self_review_receipt(
            report_path,
            material_manifest=current_manifest,
        )


@pytest.mark.parametrize(
    ("report_identity", "current_manifest"),
    (
        (
            {"base_ref_oid": FIX_SHA},
            _material_manifest(HEAD_SHA, paths=("app/example.py",)),
        ),
        (
            {"merge_base_sha": FIX_SHA},
            _material_manifest(HEAD_SHA, paths=("app/example.py",)),
        ),
    ),
    ids=("changed-base-ref", "changed-merge-base"),
)
def test_self_review_report_rejects_noncanonical_base_identity(
    tmp_path: Path,
    report_identity: dict[str, str],
    current_manifest: MaterialManifest,
) -> None:
    report_path = _write_self_review_report(
        tmp_path / "review.json",
        changed_files=("app/example.py",),
        **report_identity,
    )

    with pytest.raises(ReviewEvidenceError, match="stale for the exact material"):
        ingest_repo_native_self_review_receipt(
            report_path,
            material_manifest=current_manifest,
        )


@pytest.mark.parametrize(
    ("mutation", "error"),
    (
        (
            lambda finding: finding.update(diagnostic_code="unknown_note_code"),
            "severity or diagnostic code",
        ),
        (
            lambda finding: finding.update(disposition_candidate="NEEDS-HUMAN"),
            "severity or diagnostic code",
        ),
        (
            lambda finding: finding.update(
                diagnostic_code="context_warning",
                disposition_candidate="NEEDS-HUMAN",
            ),
            "severity or diagnostic code",
        ),
        (
            lambda finding: finding.update(severity="warning"),
            "severity or diagnostic code",
        ),
    ),
)
def test_self_review_advisory_rejects_note_demotions(
    tmp_path: Path,
    mutation: Any,
    error: str,
) -> None:
    finding = {
        "category": "tests",
        "diagnostic_code": "large_diff_review_risk",
        "disposition_candidate": "NOT-A-BUG",
        "evidence": "Diff contains 905 changed lines, above review-risk threshold 800.",
        "file": "docs/roadmap/BACKLOG_LEDGER.md",
        "gate_to_run": "make validate-changed",
        "line": None,
        "role_agent": "bug-hunter",
        "severity": "note",
        "suggested_fix": (
            "Confirm PR split rationale and targeted deterministic gates before opening review."
        ),
    }
    mutation(finding)
    report = _self_review_report_payload(
        changed_files=("app/example.py",),
        findings=(finding,),
    )
    report["scope_reviewed"]["diff_summary"] = {
        "additions": 905,
        "changed_lines": 905,
        "deletions": 0,
        "files": 1,
    }
    report_path = tmp_path / "demoted-review.json"
    _write_json(report_path, report)

    with pytest.raises(ReviewEvidenceError, match=error):
        ingest_repo_native_self_review_receipt(
            report_path,
            material_manifest=_material_manifest(
                HEAD_SHA,
                paths=("app/example.py",),
                additions=905,
            ),
        )


def test_embedded_self_review_payload_tamper_is_rejected() -> None:
    seal = _provider_no_claim_seal()
    seal["self_review"]["report_payload"]["generated_at_utc"] = "forged"

    with pytest.raises(ReviewEvidenceError, match="payload integrity"):
        render_embedded_review_seal(seal)


def test_embedded_self_review_counter_forgery_is_rejected() -> None:
    seal = _provider_no_claim_seal()
    seal["self_review"]["findings_count"] = 1

    with pytest.raises(ReviewEvidenceError, match="payload integrity"):
        render_embedded_review_seal(seal)


def test_real_large_diff_context_report_and_seal_bind_exact_material(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(evidence_module, "_REPO_ROOT", repo)
    _git(repo, "init", "-q")
    (repo / "AGENTS.md").write_text("root instructions\n", encoding="utf-8")
    (repo / "app").mkdir()
    (repo / "app/example.py").write_text("VALUE = 1\n", encoding="utf-8")
    base = _commit(repo, "base")
    (repo / "app/example.py").write_text(
        "".join(f"VALUE_{index} = {index}\n" for index in range(905)),
        encoding="utf-8",
    )
    head = _commit(repo, "material")

    monkeypatch.setattr(
        review_context_module,
        "collect_pr_metadata",
        lambda **_kwargs: (
            {
                "number": 42,
                "base_sha": base,
                "head_sha": head,
            },
            [],
        ),
    )
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "hook-caller.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "hook-caller-worktree"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "hook-caller.index"))
    context = review_context_module.collect_review_context(
        repo_root=repo,
        pr_number=42,
        repo="owner/repo",
        base_ref=base,
        head_ref=head,
    )
    report = review_report_module.build_report(context)
    assert report["findings_count"] == 1
    assert report["actionable_findings_count"] == 0
    assert report["findings"][0]["diagnostic_code"] == "large_diff_review_risk"
    manifest = compute_material_manifest(
        repo,
        base_ref_oid=base,
        head_ref_oid=head,
        pr_number=42,
    )
    assert report["base_ref_oid"] == base
    assert report["material_head_sha"] == head
    assert report["material_digest"] == manifest.digest
    assert report["merge_base_sha"] == manifest.merge_base_sha

    report_path = tmp_path / "generated-review.json"
    _write_json(report_path, report)
    receipt = ingest_repo_native_self_review_receipt(
        report_path,
        material_manifest=manifest,
    )
    assert receipt["status"] == "advisory_report_attached"
    assert receipt["review_claim"] == "none"
    assert receipt["blocking"] is False
    code_review, codex_security = build_provider_no_claim_pair(
        base_revision=manifest.merge_base_sha,
        head_revision=head,
        material_digest=manifest.digest,
    )
    seal = _seal(codex_security)
    seal["code_review"] = code_review
    seal["material"] = {
        "base_ref_oid": base,
        "digest": manifest.digest,
        "material_head_sha": head,
        "merge_base_sha": manifest.merge_base_sha,
        "policy_version": MATERIAL_POLICY_VERSION,
    }
    seal["self_review"] = receipt
    parsed = parse_embedded_review_seal(render_embedded_review_seal(seal))
    assert parsed["self_review"]["findings_count"] == 1
    assert parsed["self_review"]["actionable_findings_count"] == 0

    forged_report = json.loads(json.dumps(report))
    forged_report["scope_reviewed"]["diff_summary"] = {
        "additions": 0,
        "changed_lines": 0,
        "deletions": 0,
        "files": 1,
    }
    forged_report["findings"] = []
    forged_report["findings_count"] = 0
    forged_report["actionable_findings_count"] = 0
    _write_json(report_path, forged_report)
    with pytest.raises(
        ReviewEvidenceError,
        match="diff summary does not match the exact material",
    ):
        ingest_repo_native_self_review_receipt(
            report_path,
            material_manifest=manifest,
        )


def test_self_review_context_uses_merge_base_and_no_rename_material_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(evidence_module, "_REPO_ROOT", repo)
    _git(repo, "init", "-q")
    (repo / "AGENTS.md").write_text("root instructions\n", encoding="utf-8")
    source = repo / "src" / "old.py"
    source.parent.mkdir()
    source.write_text("FIRST = 1\nSECOND = 2\n", encoding="utf-8")
    common_base = _commit(repo, "common base")

    _git(repo, "checkout", "-q", "-b", "feature")
    _git(repo, "mv", "src/old.py", "src/new.py")
    material_head = _commit(repo, "rename on feature")

    _git(repo, "checkout", "-q", "-b", "current-base", common_base)
    (repo / "base-only.py").write_text("BASE_ONLY = True\n", encoding="utf-8")
    current_base = _commit(repo, "advance current base")

    monkeypatch.setattr(
        review_context_module,
        "collect_pr_metadata",
        lambda **_kwargs: (
            {
                "number": 42,
                "base_sha": current_base,
                "head_sha": material_head,
            },
            [],
        ),
    )
    context = review_context_module.collect_review_context(
        repo_root=repo,
        pr_number=42,
        repo="owner/repo",
        base_ref=current_base,
        head_ref=material_head,
    )
    manifest = compute_material_manifest(
        repo,
        base_ref_oid=current_base,
        head_ref_oid=material_head,
        pr_number=42,
    )
    expected_paths = [entry.path for entry in manifest.entries]

    assert manifest.merge_base_sha == common_base
    assert context["material"]["merge_base_sha"] == common_base
    assert (
        [entry["path"] for entry in context["diff"]["files"]]
        == expected_paths
        == [
            "src/new.py",
            "src/old.py",
        ]
    )
    assert context["diff"]["files"] == [
        {"path": "src/new.py", "additions": 2, "deletions": 0},
        {"path": "src/old.py", "additions": 0, "deletions": 2},
    ]
    assert context["diff"]["summary"] == {
        "files": 2,
        "additions": 2,
        "deletions": 2,
        "changed_lines": 4,
    }
    assert "base-only.py" not in expected_paths

    report = review_report_module.build_report(context)
    assert report["scope_reviewed"]["changed_files"] == expected_paths
    report_path = tmp_path / "rename-review.json"
    _write_json(report_path, report)
    assert (
        ingest_repo_native_self_review_receipt(
            report_path,
            material_manifest=manifest,
        )["status"]
        == "advisory_report_attached"
    )

    report["scope_reviewed"]["changed_files"] = ["src/new.py"]
    _write_json(report_path, report)
    with pytest.raises(ReviewEvidenceError, match="exact material path set"):
        ingest_repo_native_self_review_receipt(
            report_path,
            material_manifest=manifest,
        )


@pytest.mark.parametrize(
    ("receipt_name", "mutation"),
    [
        ("code_review", lambda value: value.update(extra_authority="owner")),
        ("code_review", lambda value: value.update(blocking=True)),
        ("code_review", lambda value: value.update(output_required=True)),
        ("code_review", lambda value: value.update(review_claim="completed")),
        ("code_review", lambda value: value.update(material_head_sha=FIX_SHA)),
        (
            "code_review",
            lambda value: value.update(material_digest="sha256:" + "f" * 64),
        ),
        ("code_review", lambda value: value.pop("output_required")),
        ("codex_security", lambda value: value.update(operator_override=True)),
        ("codex_security", lambda value: value.update(blocking=True)),
        ("codex_security", lambda value: value.update(output_required=True)),
        ("codex_security", lambda value: value.update(scan_claim="completed")),
        ("codex_security", lambda value: value.update(no_findings_claim=True)),
        ("codex_security", lambda value: value.update(head_revision=FIX_SHA)),
        (
            "codex_security",
            lambda value: value.update(material_digest="sha256:" + "f" * 64),
        ),
        ("codex_security", lambda value: value.pop("no_findings_claim")),
    ],
)
def test_provider_no_claim_pair_rejects_open_escalating_partial_or_stale_shapes(
    receipt_name: str,
    mutation: Any,
) -> None:
    seal = _provider_no_claim_seal()
    mutation(seal[receipt_name])

    with pytest.raises(ReviewEvidenceError):
        render_embedded_review_seal(seal)


@pytest.mark.parametrize("replace_receipt", ["code_review", "codex_security"])
def test_provider_no_claim_pair_rejects_one_sided_or_mixed_evidence(
    replace_receipt: str,
) -> None:
    seal = _provider_no_claim_seal()
    legacy = _seal(
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
    seal[replace_receipt] = legacy[replace_receipt]

    with pytest.raises(ReviewEvidenceError, match="exact symmetric pair"):
        render_embedded_review_seal(seal)


def test_legacy_v1_provider_receipts_remain_readable_without_no_claim_authority() -> None:
    legacy = _seal(
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

    parsed = parse_embedded_review_seal(render_embedded_review_seal(legacy))

    assert parsed == legacy
    assert not is_provider_no_claim_review_receipt(parsed["code_review"])
    assert not is_provider_no_claim_security_receipt(parsed["codex_security"])


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


@pytest.mark.parametrize("token", (None, "opaque"), ids=("tokenless", "authenticated"))
def test_live_mapping_rejects_rehashed_wrong_report_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    token: str | None,
) -> None:
    seal = _provider_no_claim_seal()
    self_review = seal["self_review"]
    self_review["report_payload"]["scope_reviewed"]["changed_files"] = ["wrong/path.py"]
    self_review["report_payload"]["scope_reviewed"]["diff_summary"]["files"] = 1
    canonical_report = json.dumps(
        self_review["report_payload"],
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    self_review["report_sha256"] = "sha256:" + hashlib.sha256(canonical_report).hexdigest()
    mapping = tmp_path / "PR_42_FIXED_MAPPING.md"
    mapping.write_text(_mapping_artifact_with_seal(seal), encoding="utf-8")
    manifest = _material_manifest(HEAD_SHA, paths=("app/example.py",))
    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: mapping)
    monkeypatch.setattr(closeout_module, "fetch_pr_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: HEAD_SHA)
    monkeypatch.setattr(
        closeout_module,
        "compute_material_manifest",
        lambda *_a, **_k: manifest,
    )

    with pytest.raises(ReviewEvidenceError, match="exact material path set"):
        closeout_module.validate_live_mapping(
            repository="owner/repo",
            pr_number=42,
            token=token,
        )


@pytest.mark.parametrize(
    "field",
    ("files", "additions", "deletions", "changed_lines"),
)
@pytest.mark.parametrize("token", (None, "opaque"), ids=("tokenless", "authenticated"))
def test_live_mapping_rejects_rehashed_wrong_report_diff_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    token: str | None,
    field: str,
) -> None:
    seal = _provider_no_claim_seal()
    self_review = seal["self_review"]
    forged_summary = {
        "additions": 0,
        "changed_lines": 0,
        "deletions": 0,
        "files": 0,
    }
    forged_summary[field] = 1
    self_review["report_payload"]["scope_reviewed"]["diff_summary"] = forged_summary
    canonical_report = json.dumps(
        self_review["report_payload"],
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    self_review["report_sha256"] = "sha256:" + hashlib.sha256(canonical_report).hexdigest()
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

    with pytest.raises(
        ReviewEvidenceError,
        match="diff summary does not match the exact material",
    ):
        closeout_module.validate_live_mapping(
            repository="owner/repo",
            pr_number=42,
            token=token,
        )


def test_authenticated_provider_no_claim_rejects_second_mapping_only_successor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("root instructions\n", encoding="utf-8")
    base_sha = _commit(repo, "base")

    material_path = repo / "src" / "policy.py"
    material_path.parent.mkdir(parents=True)
    material_path.write_text("ENFORCED = True\n", encoding="utf-8")
    material_head = _commit(repo, "material")
    manifest = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=material_head,
        pr_number=42,
    )
    code_review, codex_security = build_provider_no_claim_pair(
        base_revision=manifest.merge_base_sha,
        head_revision=material_head,
        material_digest=manifest.digest,
    )
    report = _self_review_report_payload(
        changed_files=("src/policy.py",),
        base_ref_oid=base_sha,
        merge_base_sha=manifest.merge_base_sha,
        material_head_sha=material_head,
        material_digest=manifest.digest,
    )
    report["scope_reviewed"]["diff_summary"] = {
        "additions": 1,
        "changed_lines": 1,
        "deletions": 0,
        "files": 1,
    }
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": code_review,
        "codex_security": codex_security,
        "material": {
            "base_ref_oid": base_sha,
            "digest": manifest.digest,
            "material_head_sha": material_head,
            "merge_base_sha": manifest.merge_base_sha,
            "policy_version": MATERIAL_POLICY_VERSION,
        },
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": "pulseplate.pr-review-seal/v1",
        "self_review": _self_review_receipt(report),
    }
    mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    artifact = _mapping_artifact_with_seal(seal)
    mapping.write_text(artifact, encoding="utf-8")
    first_mapping_head = _commit(repo, "mapping closeout")
    mapping.write_text(artifact + "\n<!-- second mapping commit -->\n", encoding="utf-8")
    second_mapping_head = _commit(repo, "second mapping-only closeout")
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=second_mapping_head,
        commits=(
            PrCommitEvidence(material_head, None),
            PrCommitEvidence(first_mapping_head, None),
            PrCommitEvidence(second_mapping_head, None),
        ),
    )

    monkeypatch.setattr(closeout_module, "REPO_ROOT", repo)
    monkeypatch.setattr(evidence_module, "_REPO_ROOT", repo)
    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: mapping)

    tokenless = closeout_module.validate_live_mapping(
        repository="owner/repo",
        pr_number=42,
        token=None,
    )
    assert tokenless["material"]["material_head_sha"] == material_head

    monkeypatch.setattr(closeout_module, "fetch_pr_snapshot", lambda *_a, **_k: snapshot)
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: second_mapping_head)
    monkeypatch.setattr(
        closeout_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: RepositoryCommitRef(value, CommitRefKind.PR_COMMIT),
    )
    monkeypatch.setattr(closeout_module, "is_ancestor", lambda *_a, **_k: True)
    monkeypatch.setattr(closeout_module, "assert_snapshot_unchanged", lambda *_a, **_k: None)

    with pytest.raises(ReviewEvidenceError, match="one mapping-only successor"):
        closeout_module.validate_live_mapping(
            repository="owner/repo",
            pr_number=42,
            token="opaque",
        )


def _configure_provider_no_claim_closeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Namespace, Path]:
    repo = tmp_path / "repo"
    target = repo / "docs/review/PR_42_FIXED_MAPPING.md"
    self_review_report = _write_self_review_report(tmp_path / "self-review.json")
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

    def unexpected_provider_call(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("provider-neutral no-claim seal must not call provider evidence paths")

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
        evidence_module,
        "_applicable_scoped_agents",
        lambda _paths, *, material_head_sha: ["AGENTS.md"],
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_reference",
        unexpected_provider_call,
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_codex_review_source_unavailability_reference",
        unexpected_provider_call,
    )
    monkeypatch.setattr(
        closeout_module,
        "verify_security_outage_override_reference",
        unexpected_provider_call,
    )
    monkeypatch.setattr(
        closeout_module,
        "_render_mapping",
        lambda _state, seal: _mapping_artifact_with_seal(seal),
    )
    monkeypatch.setattr(closeout_module, "mapping_artifact_path", lambda _pr: target)
    monkeypatch.setattr(closeout_module, "_git", lambda *_a, **_k: "")
    monkeypatch.setattr(closeout_module, "assert_snapshot_unchanged", lambda *_a, **_k: None)
    return (
        Namespace(
            pr_number=42,
            repo="owner/repo",
            self_review_report=str(self_review_report),
        ),
        target,
    )


def test_closeout_seal_auto_authors_provider_no_claim_without_provider_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args, target = _configure_provider_no_claim_closeout(tmp_path, monkeypatch)

    closeout_module._cmd_seal(args)

    seal = parse_embedded_review_seal(target.read_text(encoding="utf-8"))
    assert is_provider_no_claim_review_receipt(seal["code_review"])
    assert is_provider_no_claim_security_receipt(seal["codex_security"])


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

    merge_bases[(BASE_SHA, next_base)] = BASE_SHA
    merge_bases[(HEAD_SHA, next_head)] = OUTSIDE_SHA
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

    merge_bases[(HEAD_SHA, next_head)] = HEAD_SHA
    old_seal["material"]["base_ref_oid"] = FIX_SHA
    previous_identity_mismatch = closeout_module._render_mapping(state, old_seal)
    with pytest.raises(
        closeout_module.CloseoutError,
        match="without a proven fast-forward",
    ):
        closeout_module._validate_reseal_transition(
            previous_identity_mismatch,
            replacement,
            repository="owner/repo",
            pr_number=42,
            expected_freeze=new_seal["material"],
        )

    old_seal["material"]["base_ref_oid"] = BASE_SHA
    new_seal["material"]["merge_base_sha"] = BASE_SHA
    new_seal["codex_security"]["base_revision"] = BASE_SHA
    next_identity_mismatch = closeout_module._render_mapping(state, new_seal)
    with pytest.raises(
        closeout_module.CloseoutError,
        match="without a proven fast-forward",
    ):
        closeout_module._validate_reseal_transition(
            existing,
            next_identity_mismatch,
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

    def resolve_short_fix(url: str, **_kwargs: Any) -> dict[str, str]:
        candidate = urllib.parse.unquote(url.rsplit("/", 1)[-1])
        assert real_fix.startswith(candidate)
        return {"sha": real_fix}

    def ancestor(left: RepositoryCommitRef, right: RepositoryCommitRef, **_kwargs: Any) -> bool:
        ancestry_calls.append((left.sha, right.sha))
        assert left.sha not in unavailable_refs
        assert right.sha not in unavailable_refs
        return True

    monkeypatch.setattr(identity_module, "github_api_request", resolve_short_fix)
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
        mapping_entries={root_urls[0]: real_fix},
        material_digest=DIGEST,
        material_head_sha=real_head,
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


def test_review_thread_inventory_preserves_comment_order_within_each_thread() -> None:
    root = ReviewCommentEvidence(
        url="https://github.com/owner/repo/pull/42#discussion_r1",
        body="Root finding",
        created_at="2026-07-15T10:00:00Z",
        author_login="chatgpt-codex-connector",
        author_association="NONE",
        original_commit_sha=FIX_SHA,
    )
    reply = ReviewCommentEvidence(
        url="https://github.com/owner/repo/pull/42#discussion_r1_reply",
        body="Disposition reply",
        created_at="2026-07-15T11:00:00Z",
        author_login="maintainer",
        author_association="OWNER",
        original_commit_sha=HEAD_SHA,
    )
    ordered = ReviewThreadEvidence("thread", True, (root, reply))
    reversed_comments = ReviewThreadEvidence("thread", True, (reply, root))
    sibling = ReviewThreadEvidence("sibling", False, (root,))

    assert review_thread_inventory((ordered, sibling)) == review_thread_inventory(
        (sibling, ordered)
    )
    assert review_thread_inventory((ordered,)) != review_thread_inventory((reversed_comments,))


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


def test_material_manifest_records_copy_only_as_exact_no_rename_addition(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    source = repo / "source.txt"
    source.write_text("same bytes\n", encoding="utf-8")
    base = _commit(repo, "base")

    copied = repo / "copied.txt"
    shutil.copyfile(source, copied)
    head = _commit(repo, "copy only")

    manifest = compute_material_manifest(
        repo,
        base_ref_oid=base,
        head_ref_oid=head,
        pr_number=42,
    )
    source_blob = _git(repo, "rev-parse", f"{base}:source.txt")
    copied_blob = _git(repo, "rev-parse", f"{head}:copied.txt")

    assert copied_blob == source_blob
    assert [entry.as_dict() for entry in manifest.entries] == [
        {
            "base_blob_oid": None,
            "base_mode": "000000",
            "head_blob_oid": copied_blob,
            "head_mode": "100644",
            "path": "copied.txt",
            "status": "A",
        }
    ]


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


def _recordless_seed_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    seed_count: int = 1,
    ineligible_seed_indexes: frozenset[int] = frozenset(),
    mapped_fix: bool = True,
    mapping_url_kind: str = "resolved-root",
    fix_pushed_at: str | None = "2026-07-15T09:00:00Z",
    fix_subject: str = "fix",
    empty_fix: bool = False,
    fingerprint_matches: bool = True,
    unavailable_kind: CommitRefKind = CommitRefKind.REVIEW_REF_UNAVAILABLE,
) -> tuple[set[str], list[tuple[str, str]]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base_sha = _commit(repo, "base")
    policy = repo / "policy.py"
    if not empty_fix:
        policy.write_text("ENFORCED = True\n", encoding="utf-8")
    fix_sha = _commit(repo, fix_subject, allow_empty=empty_fix)
    policy.write_text("ENFORCED = True\nBOUND = True\n", encoding="utf-8")
    material_head_sha = _commit(repo, "material head")
    manifest = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=material_head_sha,
        pr_number=42,
    )
    mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    mapping.write_text("mapping\n", encoding="utf-8")
    live_head_sha = _commit(repo, "mapping closeout")
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=base_sha,
        head_sha=live_head_sha,
        commits=tuple(
            PrCommitEvidence(sha, fix_pushed_at if sha == fix_sha else None)
            for sha in (fix_sha, material_head_sha, live_head_sha)
        ),
    )
    unavailable_sha = "6" * 40
    fingerprint = unavailable_review_ref_fingerprint(
        pr_number=42,
        material_digest=manifest.digest,
        verified_real_fix_sha=fix_sha,
    )
    reply_fingerprint = (
        fingerprint
        if fingerprint_matches
        else unavailable_review_ref_fingerprint(
            pr_number=42,
            material_digest=manifest.digest,
            verified_real_fix_sha="f" * 40,
        )
    )
    root_urls = tuple(
        f"https://github.com/owner/repo/pull/42#discussion_seed_{index}"
        for index in range(seed_count)
    )
    mapped_root_url = "https://github.com/owner/repo/pull/42#discussion_mapped"
    mapped_entry_url = {
        "resolved-root": mapped_root_url,
        "issue": "https://github.com/owner/repo/issues/42#issuecomment-1",
        "top-level": "https://github.com/owner/repo/pull/42#issuecomment-2",
    }[mapping_url_kind]
    mapped_thread = ReviewThreadEvidence(
        "mapped",
        True,
        (
            ReviewCommentEvidence(
                url=mapped_root_url,
                body="Original FIXED finding",
                created_at="2026-07-15T08:00:00Z",
                author_login="reviewer",
                author_association="NONE",
                original_commit_sha=material_head_sha,
            ),
        ),
    )
    seed_threads = tuple(
        ReviewThreadEvidence(
            f"seed-{index}",
            True,
            (
                ReviewCommentEvidence(
                    url=url,
                    body=(
                        "Commit ancestry finding: verified FIX "
                        f"{fix_sha}; reviewed material "
                        f"head {material_head_sha}; reviewer ref {unavailable_sha} is unreachable."
                    ),
                    created_at=f"2026-07-15T1{index}:00:00Z",
                    author_login="chatgpt-codex-connector",
                    author_association="NONE",
                    original_commit_sha=(
                        material_head_sha if index in ineligible_seed_indexes else live_head_sha
                    ),
                ),
                ReviewCommentEvidence(
                    url=f"{url}-reply",
                    body=_duplicate_reply(reply_fingerprint),
                    created_at=f"2026-07-15T1{index}:30:00Z",
                    author_login="maintainer",
                    author_association="OWNER",
                    original_commit_sha=live_head_sha,
                ),
            ),
        )
        for index, url in enumerate(root_urls)
    )
    threads = (mapped_thread, *seed_threads)
    ancestry_calls: list[tuple[str, str]] = []

    def classify(value: str, *_args: Any, **_kwargs: Any) -> Any:
        if value == unavailable_sha:
            return ReviewExecutionRef(value, unavailable_kind, "unavailable")
        return RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD if value == live_head_sha else CommitRefKind.PR_COMMIT,
        )

    def ancestor(left: RepositoryCommitRef, right: RepositoryCommitRef, **_kwargs: Any) -> bool:
        ancestry_calls.append((left.sha, right.sha))
        assert unavailable_sha not in {left.sha, right.sha}
        return True

    monkeypatch.setattr(identity_module, "classify_commit_ref", classify)
    monkeypatch.setattr(identity_module, "is_ancestor", ancestor)
    covered = validated_duplicate_reply_urls(
        candidate_urls=set(root_urls),
        threads=threads,
        fingerprint_records={},
        mapping_entries=({mapped_entry_url: fix_sha} if mapped_fix else {}),
        material_digest=manifest.digest,
        material_head_sha=material_head_sha,
        repo_root=repo,
        snapshot=snapshot,
        repository="owner/repo",
        token="opaque",
    )
    return covered, ancestry_calls


def test_recordless_first_post_mapping_seed_accepts_sanitized_live_finding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    covered, ancestry_calls = _recordless_seed_coverage(tmp_path, monkeypatch)

    assert covered == {"https://github.com/owner/repo/pull/42#discussion_seed_0"}
    assert ancestry_calls


@pytest.mark.parametrize(
    ("ineligible_seed_indexes", "expected_seed_index"),
    [
        (frozenset({1}), 0),
        (frozenset({0}), 1),
    ],
    ids=("eligible-first", "ineligible-first"),
)
def test_recordless_cardinality_ignores_ineligible_same_fingerprint_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ineligible_seed_indexes: frozenset[int],
    expected_seed_index: int,
) -> None:
    covered, _ = _recordless_seed_coverage(
        tmp_path,
        monkeypatch,
        seed_count=2,
        ineligible_seed_indexes=ineligible_seed_indexes,
    )

    assert covered == {
        f"https://github.com/owner/repo/pull/42#discussion_seed_{expected_seed_index}"
    }


@pytest.mark.parametrize(
    ("kwargs", "raises_api_unknown"),
    [
        ({"seed_count": 2}, False),
        ({"mapped_fix": False}, False),
        ({"ineligible_seed_indexes": frozenset({0})}, False),
        ({"mapping_url_kind": "issue"}, False),
        ({"mapping_url_kind": "top-level"}, False),
        ({"fix_pushed_at": None}, False),
        ({"fix_pushed_at": "2026-07-15T08:00:00Z"}, False),
        ({"empty_fix": True}, False),
        ({"fix_subject": "trigger ci"}, False),
        ({"fingerprint_matches": False}, False),
        (
            {
                "seed_count": 2,
                "unavailable_kind": CommitRefKind.API_UNKNOWN,
            },
            True,
        ),
    ],
    ids=(
        "second-eligible-seed",
        "unmapped-fix",
        "non-live-original",
        "issue-only-mapping",
        "top-level-only-mapping",
        "missing-pushed-at",
        "not-post-comment",
        "empty-fix",
        "trigger-subject",
        "fingerprint-mismatch",
        "api-unknown",
    ),
)
def test_recordless_post_mapping_seed_stays_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kwargs: dict[str, Any],
    raises_api_unknown: bool,
) -> None:
    if raises_api_unknown:
        with pytest.raises(ReviewEvidenceError, match="API_UNKNOWN"):
            _recordless_seed_coverage(tmp_path, monkeypatch, **kwargs)
        return

    covered, _ = _recordless_seed_coverage(tmp_path, monkeypatch, **kwargs)
    assert covered == set()


def _owner_unavailable_reply(review_ref: str) -> str:
    return (
        "OWNER NOT-A-BUG: ignore unavailable reviewer ref "
        f"{review_ref}; authenticated live PR graph is authoritative."
    )


def _owner_only_empty_mapping_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    root_count: int = 1,
    root_resolved: bool = True,
    root_is_first: bool = True,
    root_author: str = "chatgpt-codex-connector",
    original_commit: str = "live",
    reply_body: str | None = None,
    reply_association: str = "OWNER",
    reply_count: int = 1,
    reply_created_at: str = "2026-08-11T11:00:00Z",
    root_body_variant: str = "valid",
    ref_resolution: str = "unavailable",
    mapping_path: str = "canonical",
    successor_shape: str = "direct",
    material_digest_matches: bool = True,
    mapping_entries: dict[str, str] | None = None,
    forbid_generic: bool = True,
    comment_path_matches: bool = True,
    selected_ref_source: str = "review",
    candidate_indexes: frozenset[int] | None = None,
    repository_arg: str = "owner/repo",
    snapshot_repository: str = "owner/repo",
    root_repository: str = "owner/repo",
    additional_owner_reply_body: str | None = None,
    classified_values: list[str] | None = None,
    selected_ref_value: str | None = None,
) -> tuple[set[str], list[str]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base_sha = _commit(repo, "base")
    source = repo / "src" / "policy.py"
    source.parent.mkdir(parents=True)
    source.write_text("ENFORCED = True\n", encoding="utf-8")
    material_head_sha = _commit(repo, "material")
    manifest = compute_material_manifest(
        repo,
        base_ref_oid=base_sha,
        head_ref_oid=material_head_sha,
        pr_number=42,
    )
    if successor_shape == "two-successors":
        mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
        mapping.parent.mkdir(parents=True)
        mapping.write_text("first closeout\n", encoding="utf-8")
        _commit(repo, "first mapping closeout")
        mapping.write_text("second closeout\n", encoding="utf-8")
    elif mapping_path == "wrong":
        mapping = repo / "docs" / "review" / "PR_41_FIXED_MAPPING.md"
        mapping.parent.mkdir(parents=True)
        mapping.write_text("wrong closeout\n", encoding="utf-8")
    else:
        mapping = repo / "docs" / "review" / "PR_42_FIXED_MAPPING.md"
        mapping.parent.mkdir(parents=True)
        mapping.write_text("closeout\n", encoding="utf-8")
    live_head_sha = _commit(repo, "mapping closeout")
    sealed_head_sha = base_sha if successor_shape == "non-direct" else material_head_sha
    selected_ref = (
        material_head_sha if selected_ref_source == "pr-commit" else selected_ref_value or "6" * 40
    )
    exact_reply = _owner_unavailable_reply(selected_ref) if reply_body is None else reply_body
    root_body = (
        "Commit ancestry finding on docs/review/PR_42_FIXED_MAPPING.md: "
        f"sealed material {sealed_head_sha} is not an ancestor of `{selected_ref}`. "
        "Unrelated base-short 909aed84... and live URL "
        f"https://github.com/owner/repo/commit/{live_head_sha}."
    )
    if root_body_variant == "real-2265":
        root_body = (
            f"Material `{sealed_head_sha}` is not an ancestor of `{selected_ref}` "
            "(`git merge-base --is-ancestor` exits 1). The latter is the reviewed commit."
        )
    elif root_body_variant == "unrelated-selected-ref":
        root_body = (
            f"Commit ancestry finding for sealed material {sealed_head_sha}. "
            f"An unrelated appendix mentions SHA {selected_ref}."
        )
    elif root_body_variant == "url-query-label":
        root_body = (
            f"Commit ancestry finding for sealed material {sealed_head_sha}. "
            f"Appendix: https://example.invalid/?unavailable-ref={selected_ref}."
        )
    elif root_body_variant == "wrong-ancestry-sha-appendix-label":
        root_body = (
            f"Material {sealed_head_sha} is not an ancestor of {'7' * 40}. "
            f"Appendix unavailable-ref={selected_ref}."
        )
    elif root_body_variant == "uppercase-selected-ref":
        root_body = f"Material {sealed_head_sha} is not an ancestor of `{selected_ref.upper()}`."
    elif root_body_variant == "mixed-case-selected-ref":
        mixed_selected_ref = selected_ref[:20].upper() + selected_ref[20:]
        root_body = f"Material {sealed_head_sha} is not an ancestor of `{mixed_selected_ref}`."
    elif root_body_variant == "uppercase-phrase":
        root_body = f"Material {sealed_head_sha} is NOT AN ANCESTOR OF `{selected_ref}`."
    elif root_body_variant == "tab-before-selected-ref":
        root_body = f"Material {sealed_head_sha} is not an ancestor of\t`{selected_ref}`."
    elif root_body_variant == "newline-before-selected-ref":
        root_body = f"Material {sealed_head_sha} is not an ancestor of\n`{selected_ref}`."
    elif root_body_variant == "selected-ref-without-backticks":
        root_body = f"Material {sealed_head_sha} is not an ancestor of {selected_ref}."
    elif root_body_variant == "multiple-spaces-before-selected-ref":
        root_body = f"Material {sealed_head_sha} is not an ancestor of  `{selected_ref}`."
    elif root_body_variant == "missing-cause":
        root_body = root_body.replace("Commit ancestry finding", "Review finding").replace(
            "is not an ancestor of", "has an unrelated comparison with"
        )
    elif root_body_variant == "missing-material":
        root_body = root_body.replace(sealed_head_sha, "material-head-missing", 1)
    elif root_body_variant == "missing-ref":
        root_body = root_body.replace(selected_ref, "review-ref-missing", 1)
    elif root_body_variant == "material-boundary":
        root_body = root_body.replace(sealed_head_sha, f"a{sealed_head_sha}", 1)
    elif root_body_variant == "ref-boundary":
        root_body = root_body.replace(selected_ref, f"{selected_ref}a", 1)

    snapshot = PrSnapshot(
        repository=snapshot_repository,
        pr_number=42,
        base_sha=base_sha,
        head_sha=live_head_sha,
        commits=tuple(PrCommitEvidence(sha, None) for sha in (material_head_sha, live_head_sha)),
    )
    root_urls = tuple(
        f"https://github.com/{root_repository}/pull/42#discussion_r{100 + index}"
        for index in range(root_count)
    )
    threads: list[ReviewThreadEvidence] = []
    for index, root_url in enumerate(root_urls):
        root = ReviewCommentEvidence(
            url=root_url,
            body=root_body,
            created_at="2026-08-11T10:00:00Z",
            author_login=root_author,
            author_association="NONE",
            original_commit_sha=(live_head_sha if original_commit == "live" else material_head_sha),
        )
        replies = tuple(
            ReviewCommentEvidence(
                url=f"{root_url}_reply_{reply_index}",
                body=exact_reply,
                created_at=reply_created_at,
                author_login="repository-owner",
                author_association=reply_association,
                original_commit_sha=live_head_sha,
            )
            for reply_index in range(reply_count)
        )
        additional_owner_replies = (
            (
                ReviewCommentEvidence(
                    url=f"{root_url}_additional_owner_reply",
                    body=additional_owner_reply_body,
                    created_at="2026-08-11T11:30:00Z",
                    author_login="repository-owner",
                    author_association="OWNER",
                    original_commit_sha=live_head_sha,
                ),
            )
            if additional_owner_reply_body is not None
            else ()
        )
        comments = (root, *replies, *additional_owner_replies)
        if not root_is_first:
            sibling = ReviewCommentEvidence(
                url=f"{root_url}_earlier",
                body="Earlier thread root",
                created_at="2026-08-11T09:00:00Z",
                author_login="reviewer",
                author_association="NONE",
                original_commit_sha=live_head_sha,
            )
            comments = (sibling, root, *replies, *additional_owner_replies)
        threads.append(
            ReviewThreadEvidence(
                f"owner-seed-{index}",
                root_resolved,
                comments,
            )
        )

    api_calls: list[str] = []

    def request_json(url: str, **_kwargs: Any) -> Any:
        api_calls.append(url)
        if "/pulls/comments/" in url:
            return {
                "html_url": root_urls[int(url.rsplit("/", 1)[-1]) - 100],
                "path": (
                    "docs/review/PR_42_FIXED_MAPPING.md"
                    if comment_path_matches
                    else "docs/review/PR_41_FIXED_MAPPING.md"
                ),
            }
        if url.endswith(f"/commits/{selected_ref}"):
            if ref_resolution == "unavailable":
                raise GitHubHttpError(404)
            if ref_resolution == "unavailable-422":
                raise GitHubHttpError(
                    422,
                    api_message=f"No commit found for SHA: {selected_ref}",
                )
            if ref_resolution == "api-unknown-422":
                raise GitHubHttpError(422, api_message="Validation Failed")
            if ref_resolution == "api-unknown":
                raise GitHubHttpError(503)
            if ref_resolution == "response-not-ready":
                raise http.client.ResponseNotReady("deterministic transport failure")
            return {"sha": selected_ref}
        raise AssertionError(f"unexpected GitHub API call: {url}")

    def forbidden_generic(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("owner-only path called generic finding parsing or ancestry")

    monkeypatch.setattr(identity_module, "github_api_request", request_json)
    if classified_values is not None:
        canonical_classifier = identity_module.classify_commit_ref

        def tracked_classifier(
            value: str, snapshot: PrSnapshot, *, token: str, **_kwargs: Any
        ) -> Any:
            classified_values.append(value)
            return canonical_classifier(
                value,
                snapshot,
                token=token,
                request_json=request_json,
            )

        monkeypatch.setattr(identity_module, "classify_commit_ref", tracked_classifier)
    if forbid_generic:
        monkeypatch.setattr(identity_module, "is_ancestor", forbidden_generic)
        monkeypatch.setattr(evidence_module, "review_finding_sha_candidates", forbidden_generic)
    covered = validated_duplicate_reply_urls(
        candidate_urls={
            root_urls[index]
            for index in (range(root_count) if candidate_indexes is None else candidate_indexes)
        },
        threads=tuple(threads),
        fingerprint_records={},
        mapping_entries=mapping_entries or {},
        material_digest=(manifest.digest if material_digest_matches else DIGEST),
        material_head_sha=sealed_head_sha,
        repo_root=repo,
        snapshot=snapshot,
        repository=repository_arg,
        token="opaque",
    )
    return covered, api_calls


def test_owner_only_empty_mapping_accepts_exact_sanitized_finding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    classified_values: list[str] = []
    covered, api_calls = _owner_only_empty_mapping_coverage(
        tmp_path,
        monkeypatch,
        classified_values=classified_values,
    )

    assert covered == {"https://github.com/owner/repo/pull/42#discussion_r100"}
    assert classified_values == ["6" * 40]
    assert any("/pulls/comments/100" in call for call in api_calls)
    assert any(call.endswith("/commits/" + "6" * 40) for call in api_calls)


def test_owner_only_empty_mapping_accepts_exact_unavailable_422(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    covered, _ = _owner_only_empty_mapping_coverage(
        tmp_path,
        monkeypatch,
        ref_resolution="unavailable-422",
    )

    assert covered == {"https://github.com/owner/repo/pull/42#discussion_r100"}


def test_owner_only_empty_mapping_accepts_real_2265_ancestry_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    covered, _ = _owner_only_empty_mapping_coverage(
        tmp_path,
        monkeypatch,
        root_body_variant="real-2265",
    )

    assert covered == {"https://github.com/owner/repo/pull/42#discussion_r100"}


def test_owner_only_empty_mapping_rejects_unrelated_selected_ref_mention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    covered, _ = _owner_only_empty_mapping_coverage(
        tmp_path,
        monkeypatch,
        root_body_variant="unrelated-selected-ref",
    )

    assert covered == set()


@pytest.mark.parametrize(
    ("root_body_variant", "selected_ref_value"),
    [
        ("url-query-label", None),
        ("wrong-ancestry-sha-appendix-label", None),
        ("uppercase-selected-ref", "abcdefabcdefabcdefabcdefabcdefabcdefabcd"),
        ("mixed-case-selected-ref", "abcdefabcdefabcdefabcdefabcdefabcdefabcd"),
    ],
    ids=("url-query-label", "wrong-ancestry-target", "uppercase", "mixed-case"),
)
def test_owner_only_empty_mapping_rejects_nonexact_selected_ref_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    root_body_variant: str,
    selected_ref_value: str | None,
) -> None:
    covered, _ = _owner_only_empty_mapping_coverage(
        tmp_path,
        monkeypatch,
        root_body_variant=root_body_variant,
        selected_ref_value=selected_ref_value,
    )

    assert covered == set()


@pytest.mark.parametrize(
    "root_body_variant",
    [
        "uppercase-phrase",
        "tab-before-selected-ref",
        "newline-before-selected-ref",
        "selected-ref-without-backticks",
        "multiple-spaces-before-selected-ref",
    ],
    ids=("uppercase-phrase", "tab", "newline", "no-backticks", "multiple-spaces"),
)
def test_owner_only_empty_mapping_rejects_ancestry_fragment_variations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    root_body_variant: str,
) -> None:
    covered, _ = _owner_only_empty_mapping_coverage(
        tmp_path,
        monkeypatch,
        root_body_variant=root_body_variant,
    )

    assert covered == set()


def test_owner_only_empty_mapping_counts_root_hidden_by_url_only_disposition_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # URL-only NOT-A-BUG/DEFERRED entries are removed from candidate_urls by
    # callers, but they must remain in the global owner-eligibility census.
    covered, _ = _owner_only_empty_mapping_coverage(
        tmp_path,
        monkeypatch,
        root_count=2,
        candidate_indexes=frozenset({0}),
    )

    assert covered == set()


def test_owner_only_empty_mapping_rejects_additional_malformed_owner_reply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    covered, _ = _owner_only_empty_mapping_coverage(
        tmp_path,
        monkeypatch,
        additional_owner_reply_body="OWNER acknowledgement without the exact contract",
    )

    assert covered == set()


def test_owner_only_empty_mapping_binds_repository_to_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ReviewEvidenceError, match="repository.*snapshot"):
        _owner_only_empty_mapping_coverage(
            tmp_path,
            monkeypatch,
            repository_arg="other/repo",
        )


def test_owner_only_empty_mapping_repository_binding_is_case_insensitive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    covered, _ = _owner_only_empty_mapping_coverage(
        tmp_path,
        monkeypatch,
        repository_arg="Owner/Repo",
    )

    assert covered == {"https://github.com/owner/repo/pull/42#discussion_r100"}


def test_owner_only_empty_mapping_root_url_repository_is_case_insensitive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    covered, _ = _owner_only_empty_mapping_coverage(
        tmp_path,
        monkeypatch,
        repository_arg="owner/repo",
        snapshot_repository="Owner/Repo",
        root_repository="owner/repo",
    )

    assert covered == {"https://github.com/owner/repo/pull/42#discussion_r100"}


@pytest.mark.parametrize(
    "body",
    [
        _owner_unavailable_reply("6" * 39),
        _owner_unavailable_reply("6" * 41),
        _owner_unavailable_reply("A" * 40),
        " " + _owner_unavailable_reply("6" * 40),
        _owner_unavailable_reply("6" * 40) + " ",
        _owner_unavailable_reply("6" * 40) + "\n",
        _owner_unavailable_reply("6" * 40) + " extra",
        _owner_unavailable_reply("6" * 40).replace("OWNER NOT-A-BUG", "NOT-A-BUG"),
    ],
    ids=(
        "sha-39",
        "sha-41",
        "uppercase",
        "leading-whitespace",
        "trailing-whitespace",
        "newline",
        "extra",
        "syntax-variant",
    ),
)
def test_owner_unavailable_reply_parser_is_exact(body: str) -> None:
    with pytest.raises(ReviewEvidenceError, match="owner unavailable-ref reply"):
        evidence_module.parse_owner_unavailable_ref_reply(body)


def test_owner_unavailable_reply_parser_returns_selected_ref() -> None:
    review_ref = "6" * 40
    assert (
        evidence_module.parse_owner_unavailable_ref_reply(_owner_unavailable_reply(review_ref))
        == review_ref
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"reply_association": "MEMBER"},
        {"reply_association": "COLLABORATOR"},
        {"reply_association": "NONE"},
        {"reply_count": 0},
        {"reply_count": 2},
        {"reply_created_at": "2026-08-11T09:00:00Z"},
        {"root_resolved": False},
        {"root_is_first": False},
        {"root_author": "other-reviewer"},
        {"original_commit": "material"},
        {"root_body_variant": "missing-cause"},
        {"root_body_variant": "missing-material"},
        {"root_body_variant": "missing-ref"},
        {"root_body_variant": "material-boundary"},
        {"root_body_variant": "ref-boundary"},
        {"material_digest_matches": False},
        {"successor_shape": "non-direct"},
        {"successor_shape": "two-successors"},
        {"mapping_path": "wrong"},
        {"comment_path_matches": False},
        {"ref_resolution": "real"},
        {"selected_ref_source": "pr-commit"},
        {"root_count": 2},
        {"mapping_entries": {"https://github.com/owner/repo/pull/42#discussion_mapped": FIX_SHA}},
    ],
    ids=(
        "member",
        "collaborator",
        "none",
        "zero-replies",
        "two-replies",
        "earlier-reply",
        "unresolved",
        "nonroot",
        "wrong-author",
        "stale-original",
        "missing-cause",
        "missing-material",
        "missing-ref",
        "material-boundary",
        "ref-boundary",
        "wrong-digest",
        "non-direct",
        "two-successors",
        "wrong-mapping-path",
        "wrong-review-comment-path",
        "real-commit",
        "real-pr-commit",
        "two-eligible-roots",
        "mapped-fix-route",
    ),
)
def test_owner_only_empty_mapping_rejects_ineligible_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kwargs: dict[str, Any],
) -> None:
    covered, _ = _owner_only_empty_mapping_coverage(tmp_path, monkeypatch, **kwargs)

    assert covered == set()


@pytest.mark.parametrize("ref_resolution", ["api-unknown", "api-unknown-422"])
def test_owner_only_empty_mapping_keeps_api_unknown_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ref_resolution: str,
) -> None:
    with pytest.raises(ReviewEvidenceError, match="API_UNKNOWN"):
        _owner_only_empty_mapping_coverage(
            tmp_path,
            monkeypatch,
            ref_resolution=ref_resolution,
        )


def test_owner_only_empty_mapping_converts_http_exception_to_api_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(
        ReviewEvidenceError,
        match="owner unavailable-ref selected ref identity is API_UNKNOWN",
    ):
        _owner_only_empty_mapping_coverage(
            tmp_path,
            monkeypatch,
            ref_resolution="response-not-ready",
        )


def test_old_five_field_reply_does_not_authorize_empty_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fingerprint = unavailable_review_ref_fingerprint(
        pr_number=42,
        material_digest=DIGEST,
        verified_real_fix_sha=FIX_SHA,
    )
    covered, _ = _owner_only_empty_mapping_coverage(
        tmp_path,
        monkeypatch,
        reply_body=_duplicate_reply(fingerprint),
        forbid_generic=False,
    )

    assert covered == set()


def _validate_duplicate_finding_body(
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    *,
    unavailable_shas: tuple[str, ...] = (UNAVAILABLE_SHA,),
    api_unknown_shas: tuple[str, ...] = (),
    classified_values: list[str] | None = None,
    ancestry_values: list[tuple[str, str]] | None = None,
) -> set[str]:
    canonical_url = "https://github.com/owner/repo/pull/42#discussion_canonical"
    duplicate_url = "https://github.com/owner/repo/pull/42#discussion_duplicate"
    fingerprint = unavailable_review_ref_fingerprint(
        pr_number=42,
        material_digest=DIGEST,
        verified_real_fix_sha=FIX_SHA,
    )
    record = CanonicalFingerprintRecord(
        fingerprint=fingerprint,
        cause=evidence_module.UNAVAILABLE_REVIEW_REF_CAUSE,
        material_digest=DIGEST,
        verified_fix=FIX_SHA,
        urls=(canonical_url,),
    )
    canonical_finding = ReviewCommentEvidence(
        url=canonical_url,
        body=body,
        created_at="2026-07-15T09:00:00Z",
        author_login="chatgpt-codex-connector",
        author_association="NONE",
        original_commit_sha=FIX_SHA,
    )
    duplicate_finding = ReviewCommentEvidence(
        url=duplicate_url,
        body=body,
        created_at="2026-07-15T10:00:00Z",
        author_login="chatgpt-codex-connector",
        author_association="NONE",
        original_commit_sha=HEAD_SHA,
    )
    reply = ReviewCommentEvidence(
        url=f"{duplicate_url}-reply",
        body=_duplicate_reply(fingerprint),
        created_at="2026-07-15T11:00:00Z",
        author_login="maintainer",
        author_association="OWNER",
        original_commit_sha=HEAD_SHA,
    )
    threads = (
        ReviewThreadEvidence("canonical-thread", True, (canonical_finding,)),
        ReviewThreadEvidence("duplicate-thread", True, (duplicate_finding, reply)),
    )

    def classify(
        value: str, snapshot: PrSnapshot, *, token: str, **_kwargs: Any
    ) -> RepositoryCommitRef | ReviewExecutionRef:
        del token
        if classified_values is not None:
            classified_values.append(value)
        if value in api_unknown_shas:
            return ReviewExecutionRef(value, CommitRefKind.API_UNKNOWN, "rate limited")
        if value in unavailable_shas:
            return ReviewExecutionRef(
                value,
                CommitRefKind.REVIEW_REF_UNAVAILABLE,
                "unavailable",
            )
        if value == snapshot.head_sha:
            kind = CommitRefKind.PR_HEAD
        elif value in snapshot.commit_shas:
            kind = CommitRefKind.PR_COMMIT
        else:
            kind = CommitRefKind.REPO_COMMIT_OUTSIDE_PR
        return RepositoryCommitRef(value, kind)

    def ancestor(
        _left: RepositoryCommitRef,
        _right: RepositoryCommitRef,
        *,
        repository: str,
        token: str,
    ) -> bool:
        del repository, token
        if ancestry_values is not None:
            ancestry_values.append((_left.sha, _right.sha))
        return True

    def material_manifest(
        _repo_root: Path,
        *,
        base_ref_oid: str,
        head_ref_oid: str,
        pr_number: int,
    ) -> MaterialManifest:
        assert base_ref_oid == BASE_SHA
        assert pr_number == 42
        return _material_manifest(head_ref_oid)

    monkeypatch.setattr(identity_module, "classify_commit_ref", classify)
    monkeypatch.setattr(identity_module, "is_ancestor", ancestor)
    monkeypatch.setattr(evidence_module, "compute_material_manifest", material_manifest)

    return validated_duplicate_reply_urls(
        candidate_urls={duplicate_url},
        threads=threads,
        fingerprint_records={fingerprint: record},
        mapping_entries={canonical_url: FIX_SHA},
        material_digest=DIGEST,
        material_head_sha=HEAD_SHA,
        repo_root=Path(),
        snapshot=_snapshot(),
        repository="owner/repo",
        token="opaque",
    )


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        (FIX_SHA, (FIX_SHA,)),
        ("a" * 7 + "...", ("a" * 7,)),
        ("b" * 39 + "…", ("b" * 39,)),
    ],
    ids=["full-baseline", "ascii-ellipsis-min", "unicode-ellipsis-max"],
)
def test_review_finding_commit_ref_parser_accepts_only_bounded_carriers(
    reference: str,
    expected: tuple[str, ...],
) -> None:
    assert (
        evidence_module.review_finding_sha_candidates(
            f"Commit ancestry reports {reference} as unreachable."
        )
        == expected
    )


@pytest.mark.parametrize(
    "reference",
    [
        "a" * 6 + "...",
        "a" * 7,
        "A" * 7 + "...",
        "a" * 40 + "...",
        "a" * 7 + "....",
        "a" * 7 + "……",
        "a" * 7 + "...…",
        "a" * 7 + "…...",
        "a" * 7 + "….",
    ],
    ids=[
        "six",
        "bare-short",
        "uppercase",
        "forty-short-carrier",
        "four-ascii-dots",
        "double-unicode-ellipsis",
        "ascii-then-unicode-ellipsis",
        "unicode-then-ascii-ellipsis",
        "unicode-ellipsis-then-dot",
    ],
)
def test_review_finding_commit_ref_parser_rejects_outside_class(reference: str) -> None:
    with pytest.raises(ReviewEvidenceError, match="ambiguous commit references"):
        evidence_module.review_finding_sha_candidates(
            f"Commit ancestry reports {reference} as unreachable."
        )


@pytest.mark.parametrize(
    "malformed_reference",
    [
        "a" * 7 + "...…",
        "A" * 7 + "...",
        "A" * 40,
        "a" * 40 + "…",
        "a" * 41,
        "a" * 41 + "...",
        "a...",
        "a" * 6 + "...",
        "ABCDEF…",
        "a" * 7 + "g",
        "a" * 39 + "_tail",
        "a" * 40 + "g",
        "a" * 40 + "\u0301tail",
        "a" * 40 + "\u200dtail",
        "a" * 7 + "...c",
        "a" * 7 + "…A",
        "abcdef1...garbage",
        "abcdef1...хвост",
        "abcdef1...\u0301tail",
        "abcdef1...\u200dtail",
        "abcdef1...\u200btail",
        "abcdef1...\x00tail",
        "abcdef1...\x07tail",
        "abcdef1...\ue000tail",
        "abcdef1...\u0378tail",
    ],
    ids=[
        "mixed-carrier",
        "uppercase-short",
        "uppercase-full-bare",
        "full-with-carrier",
        "overlong-bare",
        "overlong-with-carrier",
        "one-character-carried-core",
        "six-character-carried-core",
        "uppercase-subminimum-carried-core",
        "min-core-letter-suffix",
        "max-short-core-underscore-suffix",
        "full-core-letter-suffix",
        "full-core-combining-mark-suffix",
        "full-core-joiner-suffix",
        "ascii-carrier-trailing-lower-hex",
        "unicode-carrier-trailing-upper-hex",
        "ascii-carrier-trailing-word",
        "ascii-carrier-trailing-unicode-word",
        "ascii-carrier-trailing-combining-mark",
        "ascii-carrier-trailing-joiner",
        "ascii-carrier-trailing-zero-width-space",
        "ascii-carrier-trailing-null-control",
        "ascii-carrier-trailing-bell-control",
        "ascii-carrier-trailing-private-use",
        "ascii-carrier-trailing-unassigned",
    ],
)
def test_review_finding_parser_rejects_malformed_token_beside_valid_candidates(
    malformed_reference: str,
) -> None:
    body = (
        f"Commit ancestry reports verified FIX {FIX_SHA} and unavailable "
        f"{UNAVAILABLE_SHA}; malformed ref {malformed_reference} is also cited."
    )

    with pytest.raises(ReviewEvidenceError, match="ambiguous commit references"):
        evidence_module.review_finding_sha_candidates(body)


@pytest.mark.parametrize("punctuation", [",", ";", ")", "]", "`", ":", "=", "/"])
def test_review_finding_parser_accepts_short_ref_before_ordinary_punctuation(
    punctuation: str,
) -> None:
    short_ref = "a" * 7

    assert evidence_module.review_finding_sha_candidates(
        f"Commit ancestry reports {short_ref}...{punctuation} then continues."
    ) == (short_ref,)


@pytest.mark.parametrize(
    "ordinary_atom",
    [
        "a",
        "abcdef",
        "prefixabcdef1...",
        "prefixabcdef...",
        "prefixabcdef1",
        "_abcdef1..._",
        "e\u0301abcdef1...",
        "prefix\u200dabcdef1...",
    ],
    ids=[
        "single-bare-hex",
        "subminimum-bare-hex",
        "word-prefix",
        "word-prefixed-subminimum-carrier",
        "ordinary-word",
        "underscore-identifier",
        "decomposed-unicode-word",
        "format-joined-word",
    ],
)
def test_review_finding_parser_does_not_extract_refs_from_word_atoms(
    ordinary_atom: str,
) -> None:
    assert evidence_module.review_finding_sha_candidates(
        f"Commit ancestry reports {FIX_SHA}. Ordinary prose: {ordinary_atom}"
    ) == (FIX_SHA,)


def test_review_finding_parser_accepts_full_sha_before_sentence_period() -> None:
    assert evidence_module.review_finding_sha_candidates(f"Commit ancestry reports {FIX_SHA}.") == (
        FIX_SHA,
    )


@pytest.mark.parametrize("separator", ["\n", "\r", "\t"], ids=["lf", "cr", "tab"])
def test_review_finding_parser_accepts_short_ref_before_control_whitespace(
    separator: str,
) -> None:
    short_ref = "a" * 7

    assert evidence_module.review_finding_sha_candidates(
        f"Commit ancestry reports {short_ref}...{separator}then continues."
    ) == (short_ref,)


def test_review_finding_parser_rejects_unpaired_surrogate() -> None:
    with pytest.raises(ReviewEvidenceError, match="review finding body is malformed"):
        evidence_module.review_finding_sha_candidates("Commit ancestry reports abcdef1...\ud800")


def test_short_finding_ref_resolves_to_one_matching_full_sha_before_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    short_ref = "a" * 7
    full_ref = short_ref + "b" * 33
    requested_urls: list[str] = []
    classified_values: list[str] = []

    def request_json(url: str, **_kwargs: Any) -> dict[str, str]:
        requested_urls.append(url)
        return {"sha": full_ref}

    def classify(value: str, *_args: Any, **_kwargs: Any) -> RepositoryCommitRef:
        classified_values.append(value)
        return RepositoryCommitRef(value, CommitRefKind.REPO_COMMIT_OUTSIDE_PR)

    monkeypatch.setattr(identity_module, "github_api_request", request_json)
    monkeypatch.setattr(identity_module, "classify_commit_ref", classify)

    resolution = evidence_module._classify_finding_commit_candidate(
        short_ref,
        _snapshot(),
        token="opaque",
    )

    assert resolution == RepositoryCommitRef(full_ref, CommitRefKind.REPO_COMMIT_OUTSIDE_PR)
    assert requested_urls == [f"https://api.github.com/repos/owner/repo/commits/{short_ref}"]
    assert classified_values == [full_ref]


@pytest.mark.parametrize(
    "contradictory_second_outcome",
    [
        GitHubHttpError(404, "Not Found"),
        GitHubHttpError(422, "Unprocessable", "No commit found for SHA"),
    ],
    ids=["second-404", "second-422"],
)
def test_short_finding_ref_reuses_successful_binding_for_canonical_classification(
    monkeypatch: pytest.MonkeyPatch,
    contradictory_second_outcome: GitHubHttpError,
) -> None:
    short_ref = FIX_SHA[:8]
    requested_urls: list[str] = []

    def request_json(url: str, **_kwargs: Any) -> dict[str, str]:
        requested_urls.append(url)
        if len(requested_urls) > 1:
            raise contradictory_second_outcome
        return {"sha": FIX_SHA}

    monkeypatch.setattr(identity_module, "github_api_request", request_json)

    resolution = evidence_module._classify_finding_commit_candidate(
        short_ref,
        _snapshot(),
        token="opaque",
    )

    assert resolution == RepositoryCommitRef(
        FIX_SHA,
        CommitRefKind.PR_COMMIT,
        pushed_at="2026-07-15T10:00:00Z",
    )
    assert requested_urls == [f"https://api.github.com/repos/owner/repo/commits/{short_ref}"]


def test_short_finding_ref_rejects_malformed_repository_before_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot()
    malformed_snapshot = PrSnapshot(
        repository="owner",
        pr_number=snapshot.pr_number,
        base_sha=snapshot.base_sha,
        head_sha=snapshot.head_sha,
        commits=snapshot.commits,
    )
    api_calls: list[str] = []
    monkeypatch.setattr(
        identity_module,
        "github_api_request",
        lambda url, **_kwargs: api_calls.append(url),
    )

    resolution = evidence_module._classify_finding_commit_candidate(
        "a" * 7,
        malformed_snapshot,
        token="opaque",
    )

    assert resolution == ReviewExecutionRef(
        value="a" * 7,
        kind=CommitRefKind.API_UNKNOWN,
        reason="repository identity is malformed",
    )
    assert api_calls == []


def test_short_finding_ref_accepts_only_definitive_404_unavailable_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    classify_calls: list[str] = []

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        raise GitHubHttpError(404, "Not Found")

    monkeypatch.setattr(identity_module, "github_api_request", request_json)
    monkeypatch.setattr(
        identity_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: classify_calls.append(value),
    )

    resolution = evidence_module._classify_finding_commit_candidate(
        "a" * 7,
        _snapshot(),
        token="opaque",
    )

    assert isinstance(resolution, ReviewExecutionRef)
    assert resolution.kind is CommitRefKind.REVIEW_REF_UNAVAILABLE
    assert classify_calls == []


@pytest.mark.parametrize(
    "known_sha",
    [BASE_SHA, HEAD_SHA, FIX_SHA],
    ids=["base", "head", "pr-commit"],
)
def test_short_finding_ref_keeps_snapshot_known_404_api_unknown(
    monkeypatch: pytest.MonkeyPatch,
    known_sha: str,
) -> None:
    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        raise GitHubHttpError(404, "Not Found")

    monkeypatch.setattr(identity_module, "github_api_request", request_json)

    resolution = evidence_module._classify_finding_commit_candidate(
        known_sha[:8],
        _snapshot(),
        token="opaque",
    )

    assert resolution == ReviewExecutionRef(
        value=known_sha[:8],
        kind=CommitRefKind.API_UNKNOWN,
        reason="Commit API contradicts the live PR snapshot",
    )


@pytest.mark.parametrize(
    ("known_shas", "returned_sha"),
    [
        (("a" * 8 + "b" * 32,), "a" * 8 + "c" * 32),
        (
            ("a" * 8 + "b" * 32, "a" * 8 + "c" * 32),
            "a" * 8 + "b" * 32,
        ),
    ],
    ids=["different-known-match", "multiple-known-matches"],
)
def test_short_finding_ref_rejects_commit_api_snapshot_conflicts(
    monkeypatch: pytest.MonkeyPatch,
    known_shas: tuple[str, ...],
    returned_sha: str,
) -> None:
    snapshot = PrSnapshot(
        repository="owner/repo",
        pr_number=42,
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        commits=tuple(PrCommitEvidence(sha, "2026-07-15T10:00:00Z") for sha in known_shas),
    )
    classify_calls: list[str] = []
    monkeypatch.setattr(
        identity_module,
        "github_api_request",
        lambda *_args, **_kwargs: {"sha": returned_sha},
    )
    monkeypatch.setattr(
        identity_module,
        "classify_commit_ref",
        lambda value, *_args, **_kwargs: classify_calls.append(value),
    )

    resolution = evidence_module._classify_finding_commit_candidate(
        "a" * 8,
        snapshot,
        token="opaque",
    )

    assert resolution == ReviewExecutionRef(
        value="a" * 8,
        kind=CommitRefKind.API_UNKNOWN,
        reason="Commit API contradicts the live PR snapshot",
    )
    assert classify_calls == []


@pytest.mark.parametrize(
    "outcome",
    [
        [{"sha": "a" * 40}, {"sha": "a" * 39 + "b"}],
        {"sha": "b" * 40},
        {"sha": "a" * 39},
        {"sha": "A" * 40},
        GitHubHttpError(422, "Unprocessable", "No commit found for SHA"),
        GitHubHttpError(
            422,
            "Unprocessable",
            "No commit found for SHA: " + "a" * 7,
        ),
        GitHubHttpError(422, "Unprocessable", "ambiguous short ref"),
        GitHubHttpError(403, "Forbidden"),
        GitHubHttpError(429, "Rate Limited"),
        GitHubHttpError(503, "Unavailable"),
        TimeoutError(),
        http.client.BadStatusLine("malformed status"),
        http.client.IncompleteRead(b"partial", 10),
        http.client.HTTPException("protocol failure"),
    ],
    ids=[
        "ambiguous",
        "non-prefix",
        "partial",
        "uppercase",
        "bounded-422",
        "bounded-422-with-ref",
        "unbounded-422",
        "forbidden",
        "rate-limit",
        "server",
        "timeout",
        "bad-status-line",
        "incomplete-read",
        "http-exception",
    ],
)
def test_short_finding_ref_keeps_unproven_responses_api_unknown(
    monkeypatch: pytest.MonkeyPatch,
    outcome: Any,
) -> None:
    classify_calls: list[str] = []

    def request_json(*_args: Any, **_kwargs: Any) -> Any:
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(identity_module, "github_api_request", request_json)
    monkeypatch.setattr(
        identity_module,
        "classify_commit_ref",
        lambda value, *_a, **_k: classify_calls.append(value),
    )

    resolution = evidence_module._classify_finding_commit_candidate(
        "a" * 7,
        _snapshot(),
        token="opaque",
    )

    assert isinstance(resolution, ReviewExecutionRef)
    assert resolution.kind is CommitRefKind.API_UNKNOWN
    assert classify_calls == []


@pytest.mark.parametrize(
    "body_template",
    [
        (
            "Commit ancestry finding: verified FIX {fix}… descends from base {base}; "
            "reviewer execution ref {unavailable}... is not reachable from the "
            "reviewed head [policy](https://github.com/owner/repo/blob/{head}/AGENTS.md)."
        ),
        (
            "The commit graph cannot prove reviewer ref {unavailable}…; current "
            "head is {head}, base is {base}, and the already verified FIX is {fix}..., "
            "as recorded."
        ),
    ],
    ids=["policy-link-order", "reordered-wording"],
)
def test_pr_shaped_findings_distinguish_short_fix_from_short_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    body_template: str,
) -> None:
    short_fix = FIX_SHA[:8]
    short_unavailable = "6" * 8
    requested_refs: list[str] = []
    classified_values: list[str] = []
    ancestry_values: list[tuple[str, str]] = []

    def request_json(url: str, **_kwargs: Any) -> dict[str, str]:
        candidate = urllib.parse.unquote(url.rsplit("/", 1)[-1])
        requested_refs.append(candidate)
        if candidate == short_fix:
            return {"sha": FIX_SHA}
        if candidate == short_unavailable:
            raise GitHubHttpError(404, "Not Found")
        raise AssertionError(f"unexpected short candidate: {candidate}")

    monkeypatch.setattr(identity_module, "github_api_request", request_json)
    body = body_template.format(
        base=BASE_SHA,
        fix=short_fix,
        head=HEAD_SHA,
        unavailable=short_unavailable,
    )

    assert _validate_duplicate_finding_body(
        monkeypatch,
        body,
        unavailable_shas=(),
        classified_values=classified_values,
        ancestry_values=ancestry_values,
    ) == {"https://github.com/owner/repo/pull/42#discussion_duplicate"}
    assert requested_refs.count(short_fix) == 2
    assert requested_refs.count(short_unavailable) == 2
    assert short_unavailable not in classified_values
    assert all(
        short_unavailable not in endpoint
        for ancestry_pair in ancestry_values
        for endpoint in ancestry_pair
    )


def test_short_unavailable_422_remains_api_unknown_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    short_unavailable = "6" * 8

    def request_json(url: str, **_kwargs: Any) -> dict[str, str]:
        candidate = urllib.parse.unquote(url.rsplit("/", 1)[-1])
        if candidate == short_unavailable:
            raise GitHubHttpError(
                422,
                "Unprocessable",
                f"No commit found for SHA: {candidate}",
            )
        raise AssertionError(f"unexpected short candidate: {candidate}")

    monkeypatch.setattr(identity_module, "github_api_request", request_json)
    body = (
        f"Commit ancestry finding: verified FIX {FIX_SHA}; "
        f"reviewer execution ref {short_unavailable}... is not reachable."
    )

    with pytest.raises(ReviewEvidenceError, match="API_UNKNOWN"):
        _validate_duplicate_finding_body(
            monkeypatch,
            body,
            unavailable_shas=(),
        )


@pytest.mark.parametrize(
    "malformed_reference",
    [
        "a" * 7 + "...…",
        "A" * 40,
        "a" * 41,
        "a" * 6 + "...",
        "a" * 40 + "g",
        "a" * 7 + "...c",
        "a" * 7 + "…A",
        "abcdef1...garbage",
        "abcdef1...хвост",
        "abcdef1...\u0301tail",
        "abcdef1...\u200dtail",
        "abcdef1...\u200btail",
        "abcdef1...\x00tail",
        "abcdef1...\x07tail",
        "abcdef1...\ue000tail",
        "abcdef1...\u0378tail",
    ],
    ids=[
        "mixed-carrier",
        "uppercase-full-bare",
        "overlong-bare",
        "subminimum-carried-core",
        "full-core-letter-suffix",
        "ascii-carrier-trailing-hex",
        "unicode-carrier-trailing-hex",
        "ascii-carrier-trailing-word",
        "ascii-carrier-trailing-unicode-word",
        "ascii-carrier-trailing-combining-mark",
        "ascii-carrier-trailing-joiner",
        "ascii-carrier-trailing-zero-width-space",
        "ascii-carrier-trailing-null-control",
        "ascii-carrier-trailing-bell-control",
        "ascii-carrier-trailing-private-use",
        "ascii-carrier-trailing-unassigned",
    ],
)
def test_malformed_token_beside_valid_candidates_is_terminal_before_identity(
    monkeypatch: pytest.MonkeyPatch,
    malformed_reference: str,
) -> None:
    classified_values: list[str] = []
    ancestry_values: list[tuple[str, str]] = []
    body = (
        f"Commit ancestry finding: verified FIX {FIX_SHA}; "
        f"reviewer execution ref {UNAVAILABLE_SHA} is not reachable; "
        f"malformed ref {malformed_reference} is also cited."
    )
    monkeypatch.setattr(
        evidence_module,
        "_classify_finding_commit_candidate",
        lambda *_args, **_kwargs: pytest.fail(
            "malformed finding reached candidate identity classification"
        ),
    )

    with pytest.raises(ReviewEvidenceError, match="ambiguous commit references"):
        _validate_duplicate_finding_body(
            monkeypatch,
            body,
            classified_values=classified_values,
            ancestry_values=ancestry_values,
        )

    assert classified_values == []
    assert ancestry_values == []


def test_short_fix_snapshot_known_404_remains_api_unknown_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    short_fix = FIX_SHA[:8]

    def unavailable_short_fix(*_args: Any, **_kwargs: Any) -> Any:
        raise GitHubHttpError(404, "Not Found")

    monkeypatch.setattr(identity_module, "github_api_request", unavailable_short_fix)
    body = f"Commit ancestry finding: verified FIX {short_fix}... " "is reported unreachable."

    with pytest.raises(
        ReviewEvidenceError,
        match="API_UNKNOWN",
    ):
        _validate_duplicate_finding_body(
            monkeypatch,
            body,
            unavailable_shas=(),
        )


@pytest.mark.parametrize(
    ("fix_reference", "head_reference"),
    [
        (
            FIX_SHA,
            f"[evidence](https://github.com/owner/repo/commit/{HEAD_SHA})",
        ),
        (f"{FIX_SHA[:8]}...", HEAD_SHA),
    ],
    ids=["full-fix-markdown-head", "abbreviated-fix-plain-head"],
)
def test_duplicate_reply_accepts_exact_fix_base_head_and_one_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    fix_reference: str,
    head_reference: str,
) -> None:
    body = (
        f"Commit ancestry finding: verified FIX {fix_reference} descends from base {BASE_SHA}; "
        f"the reviewed head is {head_reference}, "
        f"but reviewer execution ref {UNAVAILABLE_SHA} is reported unreachable."
    )

    def resolve_short_fix(url: str, **_kwargs: Any) -> dict[str, str]:
        candidate = urllib.parse.unquote(url.rsplit("/", 1)[-1])
        assert candidate == FIX_SHA[:8], f"unexpected short candidate: {candidate}"
        return {"sha": FIX_SHA}

    monkeypatch.setattr(identity_module, "github_api_request", resolve_short_fix)
    assert body.count(HEAD_SHA) == 1
    assert _validate_duplicate_finding_body(monkeypatch, body) == {
        "https://github.com/owner/repo/pull/42#discussion_duplicate"
    }


@pytest.mark.parametrize(
    "repository_shas",
    [
        (FIX_SHA, BASE_SHA),
        (FIX_SHA, HEAD_SHA),
    ],
    ids=["missing-head", "missing-base"],
)
def test_duplicate_reply_rejects_partial_enriched_repository_identity_set(
    monkeypatch: pytest.MonkeyPatch,
    repository_shas: tuple[str, ...],
) -> None:
    body = "Commit ancestry finding: " + " ".join((*repository_shas, UNAVAILABLE_SHA))

    with pytest.raises(ReviewEvidenceError, match="ancestry cause is ambiguous"):
        _validate_duplicate_finding_body(monkeypatch, body)


@pytest.mark.parametrize(
    ("repository_shas", "error"),
    [
        ((FIX_SHA, BASE_SHA, OUTSIDE_SHA), "ancestry cause is ambiguous"),
        (
            (FIX_SHA, BASE_SHA, HEAD_SHA, OUTSIDE_SHA),
            "ambiguous commit references",
        ),
    ],
    ids=["foreign-fourth", "foreign-fifth"],
)
def test_duplicate_reply_rejects_foreign_repository_identity(
    monkeypatch: pytest.MonkeyPatch,
    repository_shas: tuple[str, ...],
    error: str,
) -> None:
    body = "Commit ancestry finding: " + " ".join((*repository_shas, UNAVAILABLE_SHA))

    with pytest.raises(ReviewEvidenceError, match=error):
        _validate_duplicate_finding_body(monkeypatch, body)


def test_duplicate_reply_rejects_multiple_unavailable_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second_unavailable = "6" * 40
    body = "Commit ancestry finding: " f"{FIX_SHA} {UNAVAILABLE_SHA} {second_unavailable}"

    with pytest.raises(ReviewEvidenceError, match="ancestry cause is ambiguous"):
        _validate_duplicate_finding_body(
            monkeypatch,
            body,
            unavailable_shas=(UNAVAILABLE_SHA, second_unavailable),
        )


def test_duplicate_reply_keeps_api_unknown_terminal_with_enriched_identities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = "Commit ancestry finding: " f"{FIX_SHA} {BASE_SHA} {HEAD_SHA} {UNAVAILABLE_SHA}"

    with pytest.raises(ReviewEvidenceError, match="API_UNKNOWN"):
        _validate_duplicate_finding_body(
            monkeypatch,
            body,
            api_unknown_shas=(UNAVAILABLE_SHA,),
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
        mapping_entries={canonical_finding.url: FIX_SHA},
        material_digest=DIGEST,
        material_head_sha=HEAD_SHA,
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
        mapping_entries={canonical_finding.url: FIX_SHA},
        material_digest=DIGEST,
        material_head_sha=HEAD_SHA,
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
            mapping_entries={canonical_finding.url: FIX_SHA},
            material_digest=DIGEST,
            material_head_sha=HEAD_SHA,
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
        mapping_entries={canonical_url: material_sha},
        material_digest=material_manifest.digest,
        material_head_sha=material_sha,
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
            mapping_entries={canonical_url: material_sha},
            material_digest=changed_manifest.digest,
            material_head_sha=changed_sha,
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


def test_agents_limits_mapping_exception_to_validator_covered_reply_only_roots() -> None:
    agents = (closeout_module.REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert (
        "Validator-covered canonical reply-only roots under rule 10 are the only exception"
        in agents
    )
    assert "the exact reply and resolved thread are the disposition evidence" in agents
    assert "Every other resolved actionable must appear" in agents


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


@pytest.mark.parametrize(
    "command",
    ("prepare-final-security", "record-final-security-outcome"),
)
def test_legacy_provider_authoring_commands_are_not_registered(command: str) -> None:
    parser = closeout_module._parser()

    with pytest.raises(SystemExit):
        parser.parse_args([command])


@pytest.mark.parametrize(
    "name",
    (
        "FINAL_SECURITY_PREPARATION_SCHEMA_VERSION",
        "FINAL_SECURITY_ATTEMPT_OUTCOMES",
        "_final_security_state_path",
        "_final_security_lock_path",
        "_final_security_lock",
        "_load_final_security_state",
        "_require_completed_final_security_preparation",
        "_require_terminal_outage_final_security_preparation",
        "render_final_security_approval_comment",
        "_verify_final_material_review",
        "_verify_final_material_review_source_unavailability",
        "_verify_final_security_approval",
        "_cmd_prepare_final_security",
        "_cmd_record_final_security_outcome",
        "_verify_connector_advisory_reactions",
        "_optional_connector_advisory_reactions",
    ),
)
def test_legacy_provider_authoring_private_surface_is_absent(name: str) -> None:
    assert not hasattr(closeout_module, name)


def test_closeout_seal_parser_requires_self_review_and_rejects_provider_flags() -> None:
    parser = closeout_module._parser()
    base = [
        "seal",
        "--repo",
        "owner/repo",
        "--pr-number",
        "42",
    ]
    with pytest.raises(SystemExit):
        parser.parse_args(base)

    args = parser.parse_args([*base, "--self-review-report", "/tmp/self-review.json"])
    assert args.self_review_report == "/tmp/self-review.json"

    for legacy_flag in (
        "--review-ref",
        "--review-source-unavailable-ref",
        "--scan-manifest",
        "--security-outage-override-ref",
        "--connector-advisory-reaction",
    ):
        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    *base,
                    "--self-review-report",
                    "/tmp/self-review.json",
                    legacy_flag,
                    "/tmp/provider-evidence",
                ]
            )
