"""Tests for review thread disposition guard (strict: Fixed in Commit Mapping section)."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest import MonkeyPatch

# Section extraction from artifact; auth from disposition
import scripts.orchestration.check_review_threads_disposition as _disposition_mod
from scripts.orchestration.check_review_threads_disposition import (
    ResolvedThreadRef,
    _block_thread_urls,
    _check_commit_after_comment,
    _check_real_commit_proofs,
    _check_trigger_only_mapping,
    _env_diagnostic,
    _find_disposition_block_in_section,
    _has_gh_auth,
    _iter_disposition_blocks,
    _parse_iso_datetime,
    _parse_mapping_section,
    _require_gh_token_preflight,
    _validate_fixed_commit_blocks,
)
from scripts.orchestration.pr_commit_identity import (
    CommitRefKind,
    PrCommitEvidence,
    PrSnapshot,
    RepositoryCommitRef,
    ReviewExecutionRef,
)
from scripts.orchestration.review_mapping_artifact import extract_fixed_mapping_section


def test_extract_fixed_mapping_section_finds_section() -> None:
    body = """
## Summary
text

## Discussion Thread Pass
- [x] done

## Fixed in Commit Mapping
Thread: https://example.com/1
Disposition: FIXED
Commit: abc123

## Merge Readiness
"""
    section = extract_fixed_mapping_section(body)
    assert "https://example.com/1" in section
    assert re.search(r"Disposition:\s*FIXED", section)


def test_get_pr_number_prefers_explicit_cli_value(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(_disposition_mod, "_run", lambda cmd: "999")
    assert _disposition_mod._get_pr_number(1005) == 1005


def test_get_pr_number_rejects_non_positive_cli_value() -> None:
    with pytest.raises(RuntimeError, match="must be > 0"):
        _disposition_mod._get_pr_number(0)


def test_extract_fixed_mapping_section_accepts_double_hash_heading() -> None:
    """Section uses ## Fixed in Commit Mapping (artifact format)."""
    body = """
## Summary
## Fixed in Commit Mapping
- https://github.com/org/repo/pull/99#discussion_r1
Disposition: FIXED
Commit: abc

## Discussion Thread Pass
"""
    section = extract_fixed_mapping_section(body)
    assert "https://github.com/org/repo/pull/99" in section
    assert re.search(r"Disposition:\s*FIXED", section)


def test_extract_fixed_mapping_section_empty_when_missing() -> None:
    body = """
## Summary
## Discussion Thread Pass
## Merge Readiness
"""
    section = extract_fixed_mapping_section(body)
    assert section == ""


def test_extract_fixed_mapping_section_stops_at_next_heading() -> None:
    body = """
## Fixed in Commit Mapping
- https://github.com/org/repo/pull/1#discussion_r123 -> abc1234
Disposition: FIXED
Evidence: file.md:10

## Discussion Thread Pass
- [x] done
"""
    section = extract_fixed_mapping_section(body)
    assert "https://github.com/org/repo/pull/1" in section
    assert "Discussion Thread Pass" not in section


def test_find_disposition_block_in_section_requires_disposition_and_proof() -> None:
    section = """
- https://github.com/org/repo/pull/2#discussion_r456
Disposition: FIXED
Commit: def5678
Evidence: docs/foo.md:12
"""
    assert (
        _find_disposition_block_in_section(
            section, "https://github.com/org/repo/pull/2#discussion_r456"
        )
        is True
    )


def test_find_disposition_block_in_section_requires_reason_for_not_a_bug() -> None:
    section = """
- https://github.com/org/repo/pull/2#discussion_r456
Disposition: NOT-A-BUG
Evidence: docs/foo.md:12
"""
    assert (
        _find_disposition_block_in_section(
            section, "https://github.com/org/repo/pull/2#discussion_r456"
        )
        is False
    )


def test_find_disposition_block_in_section_fails_without_proof() -> None:
    section = """
- https://github.com/org/repo/pull/3#discussion_r789
Disposition: FIXED
"""
    assert (
        _find_disposition_block_in_section(
            section, "https://github.com/org/repo/pull/3#discussion_r789"
        )
        is False
    )


def test_find_disposition_block_in_section_fails_without_disposition() -> None:
    section = """
- https://github.com/org/repo/pull/4#discussion_r000
Commit: abc123
"""
    assert (
        _find_disposition_block_in_section(
            section, "https://github.com/org/repo/pull/4#discussion_r000"
        )
        is False
    )


def test_find_disposition_block_accepts_deferred_with_backlog() -> None:
    section = """
- https://example.com/thread
Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#xyz
"""
    assert _find_disposition_block_in_section(section, "https://example.com/thread") is True


def test_iter_disposition_blocks_splits_on_blank_lines() -> None:
    section = """
- https://example.com/1
Disposition: FIXED
Commit: deadbeef

- https://example.com/2
Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#x
"""
    blocks = _iter_disposition_blocks(section)
    assert len(blocks) == 2
    assert "https://example.com/1" in blocks[0]
    assert "https://example.com/2" in blocks[1]


def test_find_disposition_block_does_not_cross_block_boundaries() -> None:
    section = """
Disposition: FIXED
Commit: deadbeef
- https://example.com/1

Evidence: docs/file.md:10
- https://example.com/2
"""
    assert _find_disposition_block_in_section(section, "https://example.com/1") is False
    assert _find_disposition_block_in_section(section, "https://example.com/2") is False


def test_find_disposition_block_accepts_mapping_block_after_detail_header() -> None:
    section = """
Disposition: FIXED
Commit: see mapping entries below
Evidence: docs/review/PR_1000_FIXED_MAPPING.md:1

- https://example.com/thread -> deadbeef
    """
    assert _find_disposition_block_in_section(section, "https://example.com/thread") is True


def test_find_disposition_block_requires_matching_sha_mapping_for_placeholder_commit() -> None:
    section = """
Disposition: FIXED
Commit: see mapping entries below
Evidence: docs/review/PR_1000_FIXED_MAPPING.md:1
- https://example.com/thread
"""
    assert _find_disposition_block_in_section(section, "https://example.com/thread") is False


def test_find_disposition_block_accepts_case_insensitive_mapping_placeholder() -> None:
    section = """
Disposition: FIXED
Commit: See Mapping Entries Below
Evidence: docs/review/PR_1000_FIXED_MAPPING.md:1

- https://example.com/thread -> deadbeef
"""
    assert _find_disposition_block_in_section(section, "https://example.com/thread") is True


def test_find_disposition_block_rejects_unrelated_previous_detail_block() -> None:
    section = """
Disposition: FIXED
Commit: see mapping entries below
Evidence: docs/review/PR_1000_FIXED_MAPPING.md:1

- https://example.com/other -> deadbeef
"""
    assert _find_disposition_block_in_section(section, "https://example.com/thread") is False


def test_validate_fixed_commit_blocks_rejects_empty_commit() -> None:
    section = """
Disposition: FIXED
Commit:
- https://example.com/thread -> deadbeef
"""
    errors = _validate_fixed_commit_blocks(section)
    assert any("empty" in error for error in errors)


def test_validate_fixed_commit_blocks_requires_sha_mapping_for_mapping_placeholder() -> None:
    section = """
Disposition: FIXED
Commit: see mapping entries below
Evidence: docs/review/PR_1000_FIXED_MAPPING.md:1

- https://example.com/thread
"""
    errors = _validate_fixed_commit_blocks(section)
    assert any("no valid SHA mappings" in error for error in errors)


def test_validate_fixed_commit_blocks_requires_mapping_for_every_placeholder_url() -> None:
    section = """
Disposition: FIXED
Commit: see mapping entries below
Evidence: docs/review/PR_1000_FIXED_MAPPING.md:1
- https://github.com/org/repo/pull/1000#discussion_r1
- https://github.com/org/repo/pull/1000#discussion_r2

- https://github.com/org/repo/pull/1000#discussion_r1 -> deadbeef
"""
    errors = _validate_fixed_commit_blocks(section)
    assert any("missing SHA mappings for" in error for error in errors)
    assert any("discussion_r2" in error for error in errors)


def test_block_thread_urls_accepts_review_thread_anchors_only() -> None:
    block = """
- https://github.com/org/repo/pull/1000#discussion_r123
- https://github.com/org/repo/pull/1000#pullrequestreview-456
- https://github.com/org/repo/pull/1000/files
- https://example.com/not-a-thread
"""
    assert _block_thread_urls(block) == [
        "https://github.com/org/repo/pull/1000#discussion_r123",
        "https://github.com/org/repo/pull/1000#pullrequestreview-456",
    ]


def test_validate_fixed_commit_blocks_ignores_deferred_commit_lines() -> None:
    section = """
Disposition: DEFERRED
Commit:
Backlog: docs/roadmap/BACKLOG_LEDGER.md#x
- https://example.com/thread
"""
    assert _validate_fixed_commit_blocks(section) == []


def test_has_gh_auth_false_when_no_token(monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    # With no env, _has_gh_auth() uses _gh_path() then gh auth status; mock both
    monkeypatch.setattr(
        _disposition_mod.shutil, "which", lambda x: "/usr/bin/gh" if x == "gh" else None
    )

    def fake_run(*args: object, **kwargs: object) -> object:
        return type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(_disposition_mod.subprocess, "run", fake_run)
    assert _has_gh_auth() is False


def test_has_gh_auth_true_when_gh_token_set(monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.setenv("GH_TOKEN", "gh_secret")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(
        _disposition_mod.shutil, "which", lambda x: "/usr/bin/gh" if x == "gh" else None
    )
    monkeypatch.setattr(
        _disposition_mod.subprocess,
        "run",
        lambda *args, **kwargs: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
    )
    assert _has_gh_auth() is True


def test_has_gh_auth_true_when_github_token_set(monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "github_secret")
    monkeypatch.setattr(
        _disposition_mod.shutil, "which", lambda x: "/usr/bin/gh" if x == "gh" else None
    )
    monkeypatch.setattr(
        _disposition_mod.subprocess,
        "run",
        lambda *args, **kwargs: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
    )
    assert _has_gh_auth() is True


def test_has_gh_auth_false_when_token_present_but_auth_status_fails(
    monkeypatch: "MonkeyPatch",
) -> None:
    monkeypatch.setenv("GH_TOKEN", "gh_secret")
    monkeypatch.setattr(
        _disposition_mod.shutil, "which", lambda x: "/usr/bin/gh" if x == "gh" else None
    )
    monkeypatch.setattr(
        _disposition_mod.subprocess,
        "run",
        lambda *args, **kwargs: type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})(),
    )
    assert _has_gh_auth() is False


def test_has_gh_auth_false_when_gh_auth_times_out(monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.setenv("GH_TOKEN", "gh_secret")
    monkeypatch.setattr(
        _disposition_mod.shutil, "which", lambda x: "/usr/bin/gh" if x == "gh" else None
    )

    def raise_timeout(*args: object, **kwargs: object) -> object:
        raise _disposition_mod.subprocess.TimeoutExpired(
            cmd=["/usr/bin/gh", "auth", "status"], timeout=5
        )

    monkeypatch.setattr(_disposition_mod.subprocess, "run", raise_timeout)
    assert _has_gh_auth() is False


def test_has_gh_auth_false_when_gh_auth_oserror(monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.setenv("GH_TOKEN", "gh_secret")
    monkeypatch.setattr(
        _disposition_mod.shutil, "which", lambda x: "/usr/bin/gh" if x == "gh" else None
    )

    def raise_oserror(*args: object, **kwargs: object) -> object:
        raise OSError("gh unavailable")

    monkeypatch.setattr(_disposition_mod.subprocess, "run", raise_oserror)
    assert _has_gh_auth() is False


def test_has_gh_auth_true_when_gh_auth_status_ok(monkeypatch: "MonkeyPatch") -> None:
    """No env vars but gh auth login → full check (Cubic P2 fix)."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    monkeypatch.setattr(
        _disposition_mod.shutil, "which", lambda x: "/usr/bin/gh" if x == "gh" else None
    )

    def fake_run(*args: object, **kwargs: object) -> object:
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(_disposition_mod.subprocess, "run", fake_run)
    assert _has_gh_auth() is True


def test_find_disposition_block_requires_thread_specific_url() -> None:
    """Thread-specific URL required (CodeRabbit/Cubic): section line must contain this thread URL, not just base."""
    section = """
- https://github.com/org/repo/pull/5#pullrequestreview-3895
Disposition: FIXED
Commit: deadbeef
Evidence: file.py:10
"""
    # Thread URL #discussion_r... not in section (only #pullrequestreview-3895) → no match
    assert (
        _find_disposition_block_in_section(
            section, "https://github.com/org/repo/pull/5#discussion_r2889026503"
        )
        is False
    )
    # When section contains this thread URL → match
    section2 = """
- https://github.com/org/repo/pull/5#discussion_r2889026503
Disposition: FIXED
Commit: deadbeef
Evidence: file.py:10
"""
    assert (
        _find_disposition_block_in_section(
            section2, "https://github.com/org/repo/pull/5#discussion_r2889026503"
        )
        is True
    )


def test_parse_iso_datetime_z_suffix() -> None:
    """Parse ISO with trailing Z as UTC."""
    dt = _parse_iso_datetime("2026-02-27T12:00:00Z")
    assert dt.year == 2026 and dt.month == 2 and dt.day == 27
    assert dt.hour == 12 and dt.minute == 0
    assert dt.tzinfo is not None


def test_parse_iso_datetime_explicit_utc() -> None:
    """Parse ISO with +00:00."""
    dt = _parse_iso_datetime("2026-02-27T10:00:00+00:00")
    assert dt.hour == 10 and dt.tzinfo is not None


def test_parse_mapping_section_extracts_url_and_sha() -> None:
    """Mapping is thread-specific: full URL only, no base URL (one URL must not satisfy multiple threads)."""
    section = """
- https://github.com/org/repo/pull/99#discussion_r1 -> abc1234
Disposition: FIXED
- https://github.com/org/repo/pull/99#discussion_r2 -> deadbeef
"""
    m = _parse_mapping_section(section)
    assert m.get("https://github.com/org/repo/pull/99#discussion_r1") == "abc1234"
    assert m.get("https://github.com/org/repo/pull/99#discussion_r2") == "deadbeef"
    assert m.get("https://github.com/org/repo/pull/99") is None


def test_parse_mapping_section_extracts_inline_fixed_commit_sha() -> None:
    section = """
- https://github.com/org/repo/pull/99#discussion_r1
- https://github.com/org/repo/pull/99#discussion_r2
Disposition: FIXED
Commit: deadbeef
Evidence: docs/file.md:10
"""
    mapping = _parse_mapping_section(section)
    assert mapping["https://github.com/org/repo/pull/99#discussion_r1"] == "deadbeef"
    assert mapping["https://github.com/org/repo/pull/99#discussion_r2"] == "deadbeef"


def test_check_commit_after_comment_fail_when_commit_before_comment() -> None:
    """Commit time <= comment time → violation."""
    thread = ResolvedThreadRef(
        url="https://github.com/org/repo/pull/1#discussion_r1",
        source="comment",
        is_resolved=True,
        created_at="2026-02-27T14:00:00Z",
    )
    section = """
- https://github.com/org/repo/pull/1#discussion_r1 -> abc1234
Disposition: FIXED
Commit: abc1234
"""

    def fake_git_time(sha: str) -> str:
        # commit at 13:00, comment at 14:00 → commit before comment → fail
        return "2026-02-27T13:00:00+00:00"

    violations = _check_commit_after_comment([thread], section, _git_commit_time_fn=fake_git_time)
    assert len(violations) == 1
    assert "commit_time=" in violations[0] and "comment_time=" in violations[0]


def test_check_commit_after_comment_pass_when_commit_after_comment() -> None:
    """Commit time > comment time → no violation."""
    thread = ResolvedThreadRef(
        url="https://github.com/org/repo/pull/1#discussion_r1",
        source="comment",
        is_resolved=True,
        created_at="2026-02-27T12:00:00Z",
    )
    section = """
- https://github.com/org/repo/pull/1#discussion_r1 -> abc1234
Disposition: FIXED
Commit: abc1234
"""

    def fake_git_time(sha: str) -> str:
        return "2026-02-27T13:00:00+00:00"

    violations = _check_commit_after_comment([thread], section, _git_commit_time_fn=fake_git_time)
    assert violations == []


def test_check_commit_after_comment_uses_inline_fixed_commit_sha() -> None:
    thread = ResolvedThreadRef(
        url="https://github.com/org/repo/pull/1#discussion_r1",
        source="comment",
        is_resolved=True,
        created_at="2026-02-27T12:00:00Z",
    )
    section = """
- https://github.com/org/repo/pull/1#discussion_r1
Disposition: FIXED
Commit: abc1234
Evidence: file.md:10
"""

    def fake_git_time(sha: str) -> str:
        assert sha == "abc1234"
        return "2026-02-27T13:00:00+00:00"

    violations = _check_commit_after_comment([thread], section, _git_commit_time_fn=fake_git_time)
    assert violations == []


def test_check_commit_after_comment_skips_when_no_sha_in_mapping() -> None:
    """NOT-A-BUG/DEFERRED may have no commit; only threads with '- url -> sha' are checked for commit-after."""
    thread = ResolvedThreadRef(
        url="https://github.com/org/repo/pull/1#discussion_r1",
        source="comment",
        is_resolved=True,
        created_at="2026-02-27T12:00:00Z",
    )
    section = """
- https://github.com/org/repo/pull/1#discussion_r1
Disposition: NOT-A-BUG
Evidence: file.md:1
"""
    violations = _check_commit_after_comment([thread], section)
    assert violations == []


def test_v1_commit_after_comment_uses_server_timestamp() -> None:
    sha = "a" * 40
    thread = ResolvedThreadRef(
        url="https://github.com/org/repo/pull/1#discussion_r1",
        source="comment",
        is_resolved=True,
        created_at="2026-02-27T12:00:00Z",
    )
    section = f"- {thread.url} -> {sha}\nDisposition: FIXED\nCommit: {sha}\n"

    violations = _check_commit_after_comment(
        [thread],
        section,
        _git_commit_time_fn=lambda _sha: (_ for _ in ()).throw(
            AssertionError("local git timestamp must not be used")
        ),
        commit_time_by_sha={sha: "2026-02-27T13:00:00+00:00"},
    )
    assert violations == []


def test_v1_commit_after_comment_fails_without_server_timestamp() -> None:
    sha = "a" * 40
    thread = ResolvedThreadRef(
        url="https://github.com/org/repo/pull/1#discussion_r1",
        source="comment",
        is_resolved=True,
        created_at="2026-02-27T12:00:00Z",
    )
    section = f"- {thread.url} -> {sha}\nDisposition: FIXED\nCommit: {sha}\n"

    violations = _check_commit_after_comment(
        [thread],
        section,
        commit_time_by_sha={sha: None},
    )

    assert len(violations) == 1
    assert "lacks server-side pushedDate or immutable repository push" in violations[0]


@pytest.mark.parametrize("activity_timestamp_field", ("timestamp", "pushed_at"))
def test_server_commit_times_use_repository_activity_and_push_event(
    monkeypatch: "MonkeyPatch",
    activity_timestamp_field: str,
) -> None:
    first_sha = "a" * 40
    second_sha = "b" * 40
    third_sha = "c" * 40
    base_sha = "d" * 40
    snapshot = PrSnapshot(
        repository="org/repo",
        pr_number=1,
        base_sha=base_sha,
        head_sha=third_sha,
        commits=(
            PrCommitEvidence(first_sha, None),
            PrCommitEvidence(second_sha, None),
            PrCommitEvidence(third_sha, None),
        ),
    )

    def run(command: list[str]) -> str:
        endpoint = command[-1]
        if endpoint == "repos/org/repo/pulls/1":
            return json.dumps({"head": {"ref": "feature", "repo": {"full_name": "org/repo"}}})
        if endpoint == "repos/org/repo/activity?ref=feature&activity_type=push&per_page=100":
            return json.dumps(
                [
                    [
                        {
                            "activity_type": "push",
                            activity_timestamp_field: "2026-02-27T13:00:00Z",
                            "ref": "refs/heads/feature",
                            "before": base_sha,
                            "after": second_sha,
                        }
                    ]
                ]
            )
        if endpoint == "repos/org/repo/events?per_page=100":
            return json.dumps(
                [
                    [
                        {
                            "type": "PushEvent",
                            "created_at": "2026-02-27T14:00:00Z",
                            "payload": {
                                "ref": "refs/heads/feature",
                                "before": second_sha,
                                "head": third_sha,
                            },
                        }
                    ]
                ]
            )
        raise AssertionError(command)

    monkeypatch.setattr(_disposition_mod, "_run", run)

    assert _disposition_mod._fetch_server_commit_times(
        snapshot=snapshot,
        repository="org/repo",
        pr_number=1,
        mapped_shas=frozenset({first_sha, second_sha, third_sha}),
    ) == {
        first_sha: "2026-02-27T13:00:00Z",
        second_sha: "2026-02-27T13:00:00Z",
        third_sha: "2026-02-27T14:00:00Z",
    }


def test_repository_activity_push_timestamp_rejects_conflicting_fields() -> None:
    with pytest.raises(RuntimeError, match="conflicting timestamps"):
        _disposition_mod._repository_activity_push_timestamp(
            {
                "timestamp": "2026-02-27T13:00:00Z",
                "pushed_at": "2026-02-27T14:00:00Z",
            }
        )


def test_server_commit_times_fail_closed_without_immutable_push_evidence(
    monkeypatch: "MonkeyPatch",
) -> None:
    sha = "a" * 40
    snapshot = PrSnapshot(
        repository="org/repo",
        pr_number=1,
        base_sha="b" * 40,
        head_sha=sha,
        commits=(PrCommitEvidence(sha, None),),
    )

    def run(command: list[str]) -> str:
        endpoint = command[-1]
        if endpoint == "repos/org/repo/pulls/1":
            return json.dumps({"head": {"ref": "feature", "repo": {"full_name": "org/repo"}}})
        if endpoint in {
            "repos/org/repo/activity?ref=feature&activity_type=push&per_page=100",
            "repos/org/repo/events?per_page=100",
            "repos/org/repo/issues/1/timeline?per_page=100",
        }:
            return json.dumps([[]])
        raise AssertionError(command)

    monkeypatch.setattr(_disposition_mod, "_run", run)

    assert _disposition_mod._fetch_server_commit_times(
        snapshot=snapshot,
        repository="org/repo",
        pr_number=1,
        mapped_shas=frozenset({sha}),
    ) == {sha: None}


def test_server_commit_times_use_exact_pr_force_push_event(
    monkeypatch: "MonkeyPatch",
) -> None:
    first_sha = "a" * 40
    head_sha = "b" * 40
    snapshot = PrSnapshot(
        repository="org/repo",
        pr_number=1,
        base_sha="c" * 40,
        head_sha=head_sha,
        commits=(
            PrCommitEvidence(first_sha, None),
            PrCommitEvidence(head_sha, None),
        ),
    )

    def run(command: list[str]) -> str:
        endpoint = command[-1]
        if endpoint == "repos/org/repo/pulls/1":
            return json.dumps({"head": {"ref": "feature", "repo": {"full_name": "org/repo"}}})
        if endpoint in {
            "repos/org/repo/activity?ref=feature&activity_type=push&per_page=100",
            "repos/org/repo/events?per_page=100",
        }:
            return json.dumps([[]])
        if endpoint == "repos/org/repo/issues/1/timeline?per_page=100":
            return json.dumps(
                [
                    [
                        {
                            "event": "head_ref_force_pushed",
                            "commit_id": head_sha,
                            "created_at": "2026-02-27T13:00:00Z",
                        }
                    ]
                ]
            )
        raise AssertionError(command)

    monkeypatch.setattr(_disposition_mod, "_run", run)

    assert _disposition_mod._fetch_server_commit_times(
        snapshot=snapshot,
        repository="org/repo",
        pr_number=1,
        mapped_shas=frozenset({first_sha, head_sha}),
    ) == {
        first_sha: "2026-02-27T13:00:00Z",
        head_sha: "2026-02-27T13:00:00Z",
    }


def test_real_commit_proof_caches_ancestry(
    monkeypatch: "MonkeyPatch",
) -> None:
    original_sha = "a" * 40
    fix_sha = "b" * 40
    head_sha = "c" * 40
    urls = [
        "https://github.com/org/repo/pull/1#discussion_r1",
        "https://github.com/org/repo/pull/1#discussion_r2",
    ]
    snapshot = PrSnapshot(
        repository="org/repo",
        pr_number=1,
        base_sha="d" * 40,
        head_sha=head_sha,
        commits=(
            PrCommitEvidence(original_sha, None),
            PrCommitEvidence(fix_sha, None),
            PrCommitEvidence(head_sha, None),
        ),
    )
    threads = [
        ResolvedThreadRef(
            url=url,
            source="comment",
            is_resolved=True,
            created_at="2026-02-27T12:00:00Z",
            original_commit_sha=original_sha,
        )
        for url in urls
    ]
    section = "\n".join(
        f"- {url} -> {fix_sha}\nDisposition: FIXED\nCommit: {fix_sha}\n" for url in urls
    )
    ancestry_calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        _disposition_mod,
        "classify_commit_ref",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("live PR snapshot identities must be reused")
        ),
    )

    def ancestor(
        left: RepositoryCommitRef,
        right: RepositoryCommitRef,
        **_kwargs: object,
    ) -> bool:
        ancestry_calls.append((left.sha, right.sha))
        return True

    monkeypatch.setattr(_disposition_mod, "is_ancestor", ancestor)
    assert (
        _check_real_commit_proofs(
            threads,
            section,
            snapshot=snapshot,
            repository="org/repo",
            token="opaque",
        )
        == []
    )
    assert ancestry_calls == [(fix_sha, head_sha), (original_sha, fix_sha)]


@pytest.mark.parametrize(
    ("original_kind", "expected_violation"),
    [
        (CommitRefKind.REVIEW_REF_UNAVAILABLE, None),
        (CommitRefKind.API_UNKNOWN, "API_UNKNOWN"),
    ],
)
def test_real_commit_proof_never_uses_unavailable_original_for_ancestry(
    monkeypatch: "MonkeyPatch",
    original_kind: CommitRefKind,
    expected_violation: str | None,
) -> None:
    fix_sha = "b" * 40
    original_sha = "c" * 40
    head_sha = "d" * 40
    url = "https://github.com/org/repo/pull/1#discussion_r1"
    snapshot = PrSnapshot(
        repository="org/repo",
        pr_number=1,
        base_sha="e" * 40,
        head_sha=head_sha,
        commits=(
            PrCommitEvidence(fix_sha, "2026-02-27T13:00:00Z"),
            PrCommitEvidence(head_sha, "2026-02-27T14:00:00Z"),
        ),
    )
    thread = ResolvedThreadRef(
        url=url,
        source="comment",
        is_resolved=True,
        created_at="2026-02-27T12:00:00Z",
        author_login="chatgpt-codex-connector",
        original_commit_sha=original_sha,
    )
    ancestry_calls: list[tuple[str, str]] = []

    def classify(value: str, *_args: object, **_kwargs: object) -> object:
        if value == original_sha:
            return ReviewExecutionRef(value, original_kind, "test")
        return RepositoryCommitRef(
            value,
            CommitRefKind.PR_HEAD if value == head_sha else CommitRefKind.PR_COMMIT,
        )

    def ancestor(left: RepositoryCommitRef, right: RepositoryCommitRef, **_kwargs: object) -> bool:
        ancestry_calls.append((left.sha, right.sha))
        return True

    monkeypatch.setattr(_disposition_mod, "classify_commit_ref", classify)
    monkeypatch.setattr(_disposition_mod, "is_ancestor", ancestor)
    violations = _check_real_commit_proofs(
        [thread],
        f"- {url} -> {fix_sha}\nDisposition: FIXED\nCommit: {fix_sha}\n",
        snapshot=snapshot,
        repository="org/repo",
        token="opaque",
    )

    assert ancestry_calls == [(fix_sha, head_sha)]
    if expected_violation is None:
        assert violations == []
    else:
        assert expected_violation in violations[0]


@pytest.mark.parametrize(
    "author_login",
    [
        "chatgpt-codex-connector",
        "coderabbitai",
        "human-reviewer",
    ],
)
def test_repository_backed_historical_original_is_review_context(
    monkeypatch: "MonkeyPatch",
    author_login: str,
) -> None:
    fix_sha = "b" * 40
    original_sha = "c" * 40
    head_sha = "d" * 40
    url = "https://github.com/org/repo/pull/1#discussion_r1"
    snapshot = PrSnapshot(
        repository="org/repo",
        pr_number=1,
        base_sha="e" * 40,
        head_sha=head_sha,
        commits=(
            PrCommitEvidence(fix_sha, "2026-02-27T13:00:00Z"),
            PrCommitEvidence(head_sha, "2026-02-27T14:00:00Z"),
        ),
    )
    thread = ResolvedThreadRef(
        url=url,
        source="comment",
        is_resolved=True,
        created_at="2026-02-27T12:00:00Z",
        author_login=author_login,
        original_commit_sha=original_sha,
    )

    def classify(value: str, *_args: object, **_kwargs: object) -> RepositoryCommitRef:
        if value == original_sha:
            return RepositoryCommitRef(value, CommitRefKind.REPO_COMMIT_OUTSIDE_PR)
        return RepositoryCommitRef(value, CommitRefKind.PR_COMMIT)

    monkeypatch.setattr(_disposition_mod, "classify_commit_ref", classify)
    monkeypatch.setattr(_disposition_mod, "is_ancestor", lambda *_a, **_k: True)

    violations = _check_real_commit_proofs(
        [thread],
        f"- {url} -> {fix_sha}\nDisposition: FIXED\nCommit: {fix_sha}\n",
        snapshot=snapshot,
        repository="org/repo",
        token="opaque",
    )

    assert violations == []


def test_unavailable_original_from_arbitrary_bot_fails_closed(
    monkeypatch: "MonkeyPatch",
) -> None:
    fix_sha = "b" * 40
    original_sha = "c" * 40
    head_sha = "d" * 40
    url = "https://github.com/org/repo/pull/1#discussion_r1"
    snapshot = PrSnapshot(
        repository="org/repo",
        pr_number=1,
        base_sha="e" * 40,
        head_sha=head_sha,
        commits=(
            PrCommitEvidence(fix_sha, None),
            PrCommitEvidence(head_sha, None),
        ),
    )
    thread = ResolvedThreadRef(
        url=url,
        source="comment",
        is_resolved=True,
        created_at="2026-02-27T12:00:00Z",
        author_login="arbitrary-reviewer[bot]",
        original_commit_sha=original_sha,
    )

    monkeypatch.setattr(
        _disposition_mod,
        "classify_commit_ref",
        lambda value, *_a, **_k: ReviewExecutionRef(
            value, CommitRefKind.REVIEW_REF_UNAVAILABLE, "unavailable"
        ),
    )
    monkeypatch.setattr(_disposition_mod, "is_ancestor", lambda *_a, **_k: True)

    violations = _check_real_commit_proofs(
        [thread],
        f"- {url} -> {fix_sha}\nDisposition: FIXED\nCommit: {fix_sha}\n",
        snapshot=snapshot,
        repository="org/repo",
        token="opaque",
    )

    assert "trusted only for chatgpt-codex-connector" in violations[0]


def test_env_diagnostic_returns_set_or_missing() -> None:
    """_env_diagnostic reports keys as SET or MISSING only (no token values)."""
    out = _env_diagnostic()
    assert "GH_TOKEN=" in out
    assert "GITHUB_TOKEN=" in out
    assert "SET" in out or "MISSING" in out
    assert "ghp_" not in out and "gho_" not in out


def test_require_gh_token_preflight_exits_when_gh_token_missing_in_ci(
    monkeypatch: "MonkeyPatch",
) -> None:
    """When require_auth or CI and GH_TOKEN missing → SystemExit(1)."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("CI", "true")
    with pytest.raises(SystemExit) as exc_info:
        _require_gh_token_preflight(True, True)
    assert exc_info.value.code == 1


def test_require_gh_token_preflight_rejects_github_token_only_in_strict_mode(
    monkeypatch: "MonkeyPatch",
) -> None:
    """Strict disposition auth requires GH_TOKEN even when GITHUB_TOKEN is present."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "github_only")
    with pytest.raises(SystemExit) as exc_info:
        _require_gh_token_preflight(True, False)
    assert exc_info.value.code == 1


def test_require_gh_token_preflight_skips_when_not_required() -> None:
    """When not require_auth and not CI, preflight does nothing (no exit)."""
    _require_gh_token_preflight(False, False)


def test_require_gh_token_preflight_passes_when_gh_token_set_and_gh_ok(
    monkeypatch: "MonkeyPatch",
) -> None:
    """When GH_TOKEN set and gh auth status succeeds, preflight returns without exit."""
    monkeypatch.setenv("GH_TOKEN", "ghp_test_dummy")
    # Mock shutil.which("gh") and subprocess.run so gh auth status succeeds
    monkeypatch.setattr(
        _disposition_mod.shutil, "which", lambda x: "/usr/bin/gh" if x == "gh" else None
    )
    fake_ok = type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(_disposition_mod.subprocess, "run", lambda *a, **k: fake_ok)
    _require_gh_token_preflight(True, True)


def test_require_gh_token_preflight_prints_diagnostic_on_timeout(
    monkeypatch: "MonkeyPatch", capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("GH_TOKEN", "ghp_test_dummy")
    monkeypatch.setattr(
        _disposition_mod.shutil, "which", lambda x: "/usr/bin/gh" if x == "gh" else None
    )

    def raise_timeout(*args: object, **kwargs: object) -> object:
        raise _disposition_mod.subprocess.TimeoutExpired(
            cmd=["/usr/bin/gh", "auth", "status"], timeout=10
        )

    monkeypatch.setattr(_disposition_mod.subprocess, "run", raise_timeout)

    with pytest.raises(SystemExit) as exc_info:
        _require_gh_token_preflight(True, True)

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "strict preflight" in captured.out
    assert "Cause:" in captured.out


def test_main_skips_in_advisory_local_mode_without_auth(
    monkeypatch: "MonkeyPatch", capsys: pytest.CaptureFixture[str]
) -> None:
    """Default local mode is advisory: no gh auth means SKIP with exit 0."""
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(_disposition_mod, "_has_gh_auth", lambda: False)
    monkeypatch.setattr(_disposition_mod.sys, "argv", ["check_review_threads_disposition.py"])

    with pytest.raises(SystemExit) as exc_info:
        _disposition_mod.main()

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    assert "advisory local run" in captured.out
    assert "not merge-readiness evidence" in captured.out


def test_main_requires_gh_token_in_ci_mode_without_flag(
    monkeypatch: "MonkeyPatch", capsys: pytest.CaptureFixture[str]
) -> None:
    """CI mode is strict even when --require-auth is omitted."""
    monkeypatch.setenv("CI", "true")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(_disposition_mod.sys, "argv", ["check_review_threads_disposition.py"])

    with pytest.raises(SystemExit) as exc_info:
        _disposition_mod.main()

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "GH_TOKEN required for disposition guard" in captured.out


def test_main_passes_in_ci_mode_with_valid_gh_token(
    monkeypatch: "MonkeyPatch", capsys: pytest.CaptureFixture[str]
) -> None:
    """CI mode should run successfully when strict auth preflight passes."""
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("GH_TOKEN", "ghp_test_dummy")
    monkeypatch.setattr(_disposition_mod.sys, "argv", ["check_review_threads_disposition.py"])
    monkeypatch.setattr(
        _disposition_mod.shutil, "which", lambda name: "/usr/bin/gh" if name == "gh" else None
    )
    fake_ok = type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(_disposition_mod.subprocess, "run", lambda *a, **k: fake_ok)
    monkeypatch.setattr(_disposition_mod, "_get_pr_number", lambda _value=None: 1009)
    monkeypatch.setattr(
        _disposition_mod,
        "read_mapping_artifact",
        lambda _pr_number: (
            "# PR 1009 — Fixed in Commit Mapping\n\n"
            "## Fixed in Commit Mapping\n"
            "- No actionable review comments\n"
        ),
    )
    monkeypatch.setattr(_disposition_mod, "_collect_resolved_threads", lambda _pr_number: [])

    with pytest.raises(SystemExit) as exc_info:
        _disposition_mod.main()

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    assert "OK: No resolved review threads found" in captured.out


def test_trigger_only_mapping_fails_on_empty_commit(monkeypatch: "MonkeyPatch") -> None:
    """Mapped SHA with no changed files → violation (empty commit)."""
    monkeypatch.setattr(_disposition_mod, "_git_changed_files", lambda _sha: [])
    monkeypatch.setattr(_disposition_mod, "_git_commit_subject", lambda _sha: "fix: real change")

    threads = [
        ResolvedThreadRef(
            url="https://github.com/org/repo/pull/985#discussion_r1",
            source="comment",
            is_resolved=True,
            created_at="2026-03-01T00:00:00Z",
        )
    ]
    section = "- https://github.com/org/repo/pull/985#discussion_r1 -> abcdef12"

    violations = _check_trigger_only_mapping(threads, section)
    assert violations
    assert "EMPTY" in violations[0]


def test_trigger_only_mapping_fails_on_rerun_subject(monkeypatch: "MonkeyPatch") -> None:
    """Mapped SHA with trigger/rerun subject → violation."""
    monkeypatch.setattr(
        _disposition_mod, "_git_changed_files", lambda _sha: ["scripts/orchestration/x.py"]
    )
    monkeypatch.setattr(
        _disposition_mod,
        "_git_commit_subject",
        lambda _sha: "chore: trigger CI after resolving threads",
    )

    threads = [
        ResolvedThreadRef(
            url="https://github.com/org/repo/pull/985#discussion_r2",
            source="comment",
            is_resolved=True,
            created_at="2026-03-01T00:00:00Z",
        )
    ]
    section = "- https://github.com/org/repo/pull/985#discussion_r2 -> deadbeef"

    violations = _check_trigger_only_mapping(threads, section)
    assert violations
    assert "rerun/trigger" in violations[0]


def test_trigger_only_mapping_passes_on_normal_commit(monkeypatch: "MonkeyPatch") -> None:
    """Mapped SHA with real changes and normal subject → no violation."""
    monkeypatch.setattr(
        _disposition_mod,
        "_git_changed_files",
        lambda _sha: ["scripts/orchestration/check_review_threads_disposition.py"],
    )
    monkeypatch.setattr(
        _disposition_mod,
        "_git_commit_subject",
        lambda _sha: "fix(orchestration): enforce mapping proof correctness",
    )

    threads = [
        ResolvedThreadRef(
            url="https://github.com/org/repo/pull/985#discussion_r3",
            source="comment",
            is_resolved=True,
            created_at="2026-03-01T00:00:00Z",
        )
    ]
    section = "- https://github.com/org/repo/pull/985#discussion_r3 -> cafe1234"

    violations = _check_trigger_only_mapping(threads, section)
    assert violations == []


def test_trigger_only_mapping_checks_inline_fixed_commit_sha(monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.setattr(_disposition_mod, "_git_changed_files", lambda _sha: [])
    monkeypatch.setattr(_disposition_mod, "_git_commit_subject", lambda _sha: "fix: real change")

    threads = [
        ResolvedThreadRef(
            url="https://github.com/org/repo/pull/985#discussion_r4",
            source="comment",
            is_resolved=True,
            created_at="2026-03-01T00:00:00Z",
        )
    ]
    section = """
- https://github.com/org/repo/pull/985#discussion_r4
Disposition: FIXED
Commit: deadbeef
Evidence: file.md:10
"""

    violations = _check_trigger_only_mapping(threads, section)
    assert violations
    assert "EMPTY" in violations[0]
