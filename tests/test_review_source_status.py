"""Tests for review-source degradation status helpers."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.orchestration.review_source_status import (
    build_review_source_status,
    summarize_degraded_sources,
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
        "fallback_required": True,
        "blocking": False,
        "reason": "usage limit reached",
        "evidence": "fallback dry run",
    }
    assert summarize_degraded_sources([status]) == [
        "coderabbit: rate_limited (usage limit reached)"
    ]


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


def test_review_source_status_redacts_reason_and_evidence() -> None:
    status = build_review_source_status(
        source="coderabbit",
        status="rate_limited",
        reason="raw fine grained token github_pat_FAKE1234567890abcdef at /Users/example/run",
        evidence="oauth token gho_FAKE1234567890abcdef in file:///private/tmp/evidence.json",
    )

    assert status["reason"] == "raw fine grained token <redacted> at <redacted-path>"
    assert status["evidence"] == "oauth token <redacted> in <redacted-path>"
