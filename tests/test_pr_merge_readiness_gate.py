from __future__ import annotations

from scripts.ci.check_pr_merge_readiness import _is_actionable, _mapped_urls


def test_is_actionable_detects_known_markers() -> None:
    body = "Actionable comments posted: 1\nPrompt for AI Agents"
    assert _is_actionable(body) is True


def test_is_actionable_ignores_explicit_no_actionables() -> None:
    body = "No actionable comments were generated in the recent review."
    assert _is_actionable(body) is False


def test_mapped_urls_extracts_review_url_and_no_actionable_marker() -> None:
    pr_body = """
## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- https://github.com/acme/repo/pull/1#discussion_r1 -> abc1234
- No actionable review comments
"""
    urls, has_no_actionable = _mapped_urls(pr_body)
    assert "https://github.com/acme/repo/pull/1#discussion_r1" in urls
    assert has_no_actionable is True
