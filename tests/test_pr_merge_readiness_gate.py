from __future__ import annotations

from scripts.ci import check_pr_merge_readiness as merge_gate
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


def test_graphql_unresolved_threads_ignores_ghas_non_conversation(
    monkeypatch,
) -> None:
    """GHAS code-scanning threads are not resolvable conversations and should not block merge."""

    def _fake_api_request(*_args, **_kwargs):
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {
                                    "isResolved": False,
                                    "isOutdated": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "author": {
                                                    "login": "coderabbitai",
                                                }
                                            }
                                        ]
                                    },
                                },
                                {
                                    "isResolved": False,
                                    "isOutdated": True,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "author": {
                                                    "login": "github-advanced-security",
                                                }
                                            }
                                        ]
                                    },
                                },
                            ],
                        }
                    }
                }
            }
        }

    monkeypatch.setattr(merge_gate, "_api_request", _fake_api_request)
    unresolved = merge_gate._graphql_unresolved_threads(
        repo="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=960,
        token="dummy",
    )

    assert unresolved == 1
