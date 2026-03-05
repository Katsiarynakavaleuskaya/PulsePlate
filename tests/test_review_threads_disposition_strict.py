"""Tests for review thread disposition guard (strict: Fixed in Commit Mapping section)."""

from __future__ import annotations

import re

# Section extraction and auth only; no gh/GraphQL mocks
import scripts.orchestration.check_review_threads_disposition as _disposition_mod
from scripts.orchestration.check_review_threads_disposition import (
    _extract_fixed_mapping_section,
    _find_disposition_block_in_section,
    _has_gh_auth,
)


def test_extract_fixed_mapping_section_finds_section() -> None:
    body = """
## Summary
text

## Discussion Thread Pass
- [x] done

### Fixed in Commit Mapping
Thread: https://example.com/1
Disposition: FIXED
Commit: abc123

## Merge Readiness
"""
    section = _extract_fixed_mapping_section(body)
    assert "https://example.com/1" in section
    assert re.search(r"Disposition:\s*FIXED", section)


def test_extract_fixed_mapping_section_accepts_double_hash_heading() -> None:
    """Section may use ## Fixed in Commit Mapping (any heading level)."""
    body = """
## Summary
## Fixed in Commit Mapping
- https://github.com/org/repo/pull/99#discussion_r1
Disposition: FIXED
Commit: abc

## Discussion Thread Pass
"""
    section = _extract_fixed_mapping_section(body)
    assert "https://github.com/org/repo/pull/99" in section
    assert re.search(r"Disposition:\s*FIXED", section)


def test_extract_fixed_mapping_section_empty_when_missing() -> None:
    body = """
## Summary
## Discussion Thread Pass
## Merge Readiness
"""
    section = _extract_fixed_mapping_section(body)
    assert section == ""


def test_extract_fixed_mapping_section_stops_at_next_heading() -> None:
    body = """
### Fixed in Commit Mapping
- https://github.com/org/repo/pull/1#discussion_r123 -> abc1234
Disposition: FIXED
Evidence: file.md:10

## Discussion Thread Pass
- [x] done
"""
    section = _extract_fixed_mapping_section(body)
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


def test_has_gh_auth_false_when_no_token(monkeypatch: object) -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    # With no env, _has_gh_auth() falls back to gh auth status; mock as not logged in
    def fake_run(*args: object, **kwargs: object) -> object:
        return type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(_disposition_mod.subprocess, "run", fake_run)
    assert _has_gh_auth() is False


def test_has_gh_auth_true_when_gh_token_set(monkeypatch: object) -> None:
    monkeypatch.setenv("GH_TOKEN", "gh_secret")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert _has_gh_auth() is True


def test_has_gh_auth_true_when_github_token_set(monkeypatch: object) -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "github_secret")
    assert _has_gh_auth() is True


def test_has_gh_auth_true_when_gh_auth_status_ok(monkeypatch: object) -> None:
    """No env vars but gh auth login → full check (Cubic P2 fix)."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    def fake_run(*args: object, **kwargs: object) -> object:
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(_disposition_mod.subprocess, "run", fake_run)
    assert _has_gh_auth() is True


def test_find_disposition_block_matches_by_base_url() -> None:
    """Body may have #pullrequestreview-xxx while GraphQL returns #discussion_rxxx; base URL match."""
    section = """
- https://github.com/org/repo/pull/5#pullrequestreview-3895
Disposition: FIXED
Commit: deadbeef
Evidence: file.py:10
"""
    # GraphQL returns discussion URL; section lists review URL — same base
    assert (
        _find_disposition_block_in_section(
            section, "https://github.com/org/repo/pull/5#discussion_r2889026503"
        )
        is True
    )
