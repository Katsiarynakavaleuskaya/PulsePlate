"""Tests for review thread disposition guard (strict: Fixed in Commit Mapping section)."""

from __future__ import annotations

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
    assert _has_gh_auth() is True


def test_has_gh_auth_true_when_github_token_set(monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "github_secret")
    assert _has_gh_auth() is True


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
