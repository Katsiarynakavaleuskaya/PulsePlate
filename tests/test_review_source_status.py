"""Tests for review-source degradation status helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestration.review_source_status import (
    REVIEW_SOURCE_STATUSES,
    build_review_source_status,
    classify_codex_review_source_unavailability_body,
    review_source_policy_projection,
    summarize_degraded_sources,
)

CODEX_USAGE_LIMIT_BODY = (
    "You have reached your Codex usage limits for code reviews. "
    "You can see your limits in the "
    "[Codex usage dashboard](https://chatgpt.com/codex/cloud/settings/usage)."
)
CODEX_USAGE_LIMIT_BODY_WITH_SETTINGS = (
    CODEX_USAGE_LIMIT_BODY
    + "\nTo continue using code reviews, add credits to your account and enable them "
    "for code reviews in your "
    "[settings](https://chatgpt.com/codex/cloud/settings/code-review)."
)


def test_review_source_degraded_is_warning_only_by_default() -> None:
    status = build_review_source_status(
        source="coderabbit",
        status="rate_limited",
        reason="usage limit reached",
        evidence="fallback dry run",
    )

    assert status == {
        "source": "coderabbit",
        "status": "rate_limited",
        "source_degraded": True,
        "fallback_required": False,
        "blocking": False,
        "reason": "usage limit reached",
        "evidence": "fallback dry run",
    }
    assert summarize_degraded_sources([status]) == [
        "coderabbit: rate_limited (usage limit reached)"
    ]


def test_terminal_quota_policy_requires_no_retry_or_substitute_authority() -> None:
    assert review_source_policy_projection() == {
        "blocking_statuses": [
            "actionable_bot_comments",
            "failed_required_check",
            "fallback_finding",
            "unresolved_threads",
        ],
        "policy_version": "pulseplate.review-source-policy/v1",
        "terminal_nonblocking_statuses": [
            "rate_limited",
            "usage_limit_reached",
        ],
        "terminal_unavailability": {
            "blocking": False,
            "fallback_required": False,
            "operator_override_required": False,
            "prior_review_required": False,
            "retry_required": False,
            "review_claim": "none",
            "source_degraded": True,
            "substitute_review_required": False,
            "ttl_required": False,
        },
    }


@pytest.mark.parametrize("status", ["rate_limited", "usage_limit_reached"])
def test_terminal_quota_status_rejects_blocking_override(status: str) -> None:
    with pytest.raises(
        ValueError,
        match="terminal review-source unavailability cannot be marked blocking",
    ):
        build_review_source_status(
            source="codex_review",
            status=status,
            blocking=True,
        )


@pytest.mark.parametrize(
    "body",
    [CODEX_USAGE_LIMIT_BODY, CODEX_USAGE_LIMIT_BODY_WITH_SETTINGS],
)
def test_codex_quota_body_classification_accepts_exact_known_bodies(body: str) -> None:
    assert classify_codex_review_source_unavailability_body(body) == "usage_limit_reached"


def test_codex_quota_body_classification_is_exact_and_fail_closed() -> None:
    for body in (
        CODEX_USAGE_LIMIT_BODY_WITH_SETTINGS + " ",
        CODEX_USAGE_LIMIT_BODY_WITH_SETTINGS.replace("usage limits", "rate limits"),
        CODEX_USAGE_LIMIT_BODY_WITH_SETTINGS.replace("settings/code-review", "settings/review"),
        "Codex review unavailable",
    ):
        try:
            classify_codex_review_source_unavailability_body(body)
        except ValueError as exc:
            assert "exact known quota response" in str(exc)
        else:  # pragma: no cover - assertion branch
            raise AssertionError("changed quota text must fail closed")


def test_review_source_blocking_requires_explicit_blocking_status() -> None:
    degraded = build_review_source_status(source="coderabbit", available=False)
    blocking = build_review_source_status(
        source="coderabbit",
        status="actionable_bot_comments",
        reason="bot comment has actionable item",
    )

    assert degraded["source_degraded"] is True
    assert degraded["blocking"] is False
    assert blocking["source_degraded"] is False
    assert blocking["fallback_required"] is True
    assert blocking["blocking"] is True


def test_review_source_status_schema_matches_helper_shape() -> None:
    status = build_review_source_status(source="github", available=True)
    schema = json.loads(
        Path("docs/orchestration/contracts/review_source_status.v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert set(schema["required"]) == set(status)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["status"]["enum"] == sorted(REVIEW_SOURCE_STATUSES)
    assert schema["allOf"] == [
        {
            "if": {
                "properties": {
                    "status": {
                        "enum": [
                            "rate_limited",
                            "usage_limit_reached",
                        ]
                    }
                },
                "required": ["status"],
            },
            "then": {
                "properties": {
                    "source_degraded": {"const": True},
                    "fallback_required": {"const": False},
                    "blocking": {"const": False},
                }
            },
        }
    ]


def test_review_source_status_rejects_unknown_status() -> None:
    try:
        build_review_source_status(source="coderabbit", status="rate-limitd")
    except ValueError as exc:
        assert "status must be one of" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("unknown status should fail closed")


def test_review_source_status_redacts_reason_and_evidence() -> None:
    status = build_review_source_status(
        source="coderabbit",
        status="rate_limited",
        reason="raw fine grained token github_pat_FAKE1234567890abcdef at /Users/example/run",
        evidence="oauth token gho_FAKE1234567890abcdef in file:///private/tmp/evidence.json",
    )

    assert status["reason"] == "raw fine grained token <redacted> at <redacted-path>"
    assert status["evidence"] == "oauth token <redacted> in <redacted-path>"
