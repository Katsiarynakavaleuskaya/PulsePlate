"""Tests for offline review-pattern oracle helpers."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.orchestration.review_pattern_oracles import match_review_pattern_oracles


def test_review_pattern_oracles_redact_and_match_without_authority() -> None:
    report = match_review_pattern_oracles(
        text="token=abc123 schema validator parity and fixed mapping hygiene",
        changed_paths=["docs/orchestration/contracts/example.schema.json"],
    )

    assert report["schema_version"] == "review_pattern_oracles.v1"
    assert report["side_effects_allowed"] is False
    assert report["posting_allowed"] is False
    assert report["thread_resolution_allowed"] is False
    assert report["merge_readiness_authority"] is False
    assert str(report["input_fingerprint"]).startswith("sha256:")
    assert report["oracle_ids"] == [
        "schema_validator_parity",
        "fail_closed_security_edge",
        "deterministic_content_oracle",
        "canonical_route_ownership_guard",
        "evidence_hygiene_mapping_timing",
        "review_source_degraded",
    ]
    oracle_ids = {item["oracle_id"] for item in report["matches"]}
    assert "schema_validator_parity" in oracle_ids
    assert "evidence_hygiene_mapping_timing" in oracle_ids


def test_review_pattern_oracles_are_deterministic() -> None:
    kwargs = {
        "text": "review thread fixed mapping",
        "changed_paths": ["docs/review/PR_1_FIXED_MAPPING.md"],
    }

    assert match_review_pattern_oracles(**kwargs) == match_review_pattern_oracles(**kwargs)


def test_review_pattern_oracle_schema_matches_helper_shape() -> None:
    report = match_review_pattern_oracles(
        text="review source degraded schema validator",
        changed_paths=["docs/orchestration/contracts/review_pattern_oracles.v1.json"],
    )
    schema = json.loads(
        Path("docs/orchestration/contracts/review_pattern_oracles.v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert set(schema["required"]) == set(report)
    assert schema["properties"]["schema_version"]["const"] == report["schema_version"]
    assert schema["properties"]["oracle_ids"]["items"]["enum"] == report["oracle_ids"]
    allowed_match_keys = set(schema["properties"]["matches"]["items"]["properties"])
    for match in report["matches"]:
        assert set(match) == allowed_match_keys
