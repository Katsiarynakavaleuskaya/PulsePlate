"""Tests for proposal-only agent learning-loop helpers."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.orchestration.agent_learning_loop import (
    build_learning_loop_proposal,
    redact_learning_text,
)
from scripts.orchestration.agent_lesson_extractor import extract_agent_lesson_record
from scripts.orchestration.agent_lesson_promoter import _load_record, promote_agent_lesson_record
from scripts.orchestration.review_pattern_oracles import REVIEW_PATTERN_ORACLE_IDS


def test_learning_loop_proposal_redacts_and_stays_non_runtime() -> None:
    proposal = build_learning_loop_proposal(
        source="review github_pat_FAKE1234567890abcdef",
        lessons=["gho_FAKE1234567890abcdef promote validator parity lesson"],
        target_paths=["docs/orchestration/AGENT_LEARNING_LOOP.md"],
    )

    assert proposal["schema_version"] == "agent-learning-loop.v1"
    assert proposal["source"] == "review <redacted>"
    assert proposal["side_effects_allowed"] is False
    assert proposal["runtime_authority"] is False
    assert proposal["canonical_until_promoted_by_repo_diff"] is False
    assert proposal["redacted_lessons"] == ["<redacted> promote validator parity lesson"]
    assert str(proposal["proposal_fingerprint"]).startswith("sha256:")


def test_learning_loop_redacts_ghs_tokens_with_dots_and_hyphens() -> None:
    assert redact_learning_text("review ghs_abc-def.ghi evidence") == "review <redacted> evidence"


def test_learning_loop_redacts_local_paths_in_free_text() -> None:
    assert (
        redact_learning_text("see /Users/example/project/.env and file:///private/tmp/log.txt")
        == "see <redacted-path> and <redacted-path>"
    )
    assert (
        redact_learning_text(r"windows C:\Users\example\secret.txt path")
        == "windows <redacted-path> path"
    )


def test_learning_loop_proposal_dedupes_targets_deterministically() -> None:
    proposal = build_learning_loop_proposal(
        source="review",
        lessons=["durable lesson"],
        target_paths=["b.md", "a.md", "b.md"],
    )

    assert proposal["target_paths"] == ["a.md", "b.md"]


def test_learning_loop_rejects_absolute_target_paths() -> None:
    with pytest.raises(ValueError, match="target_paths must be a repo-relative path"):
        build_learning_loop_proposal(
            source="review",
            lessons=["durable lesson"],
            target_paths=["/Users/example/worktree/docs.md"],
        )


def test_agent_lesson_extractor_emits_requested_record_shape() -> None:
    record = extract_agent_lesson_record(
        source="review secret=abc /Users/example/worktree",
        pattern="schema validator drift",
        severity="HIGH",
        affected_surfaces=["scripts/orchestration", "scripts/orchestration"],
        root_cause="token=abc reused stale schema from file:///private/tmp/trace.log",
        required_oracle="schema_validator_parity",
        promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
    )

    assert set(record) == {
        "lesson_id",
        "source",
        "pattern",
        "severity",
        "affected_surfaces",
        "root_cause",
        "required_oracle",
        "promotion_target",
        "dedupe_fingerprint",
        "redaction_status",
        "human_review_required",
    }
    assert record["severity"] == "high"
    assert record["source"] == "review <redacted> <redacted-path>"
    assert record["affected_surfaces"] == ["scripts/orchestration"]
    assert record["root_cause"] == "<redacted> reused stale schema from <redacted-path>"
    assert record["redaction_status"] == "redacted"
    assert record["human_review_required"] is True


def test_agent_lesson_extractor_rejects_invalid_schema_values() -> None:
    with pytest.raises(ValueError, match="severity must be one of"):
        extract_agent_lesson_record(
            source="review",
            pattern="schema validator drift",
            severity="urgent",
            affected_surfaces=["scripts/orchestration"],
            root_cause="stale schema",
            required_oracle="schema_validator_parity",
            promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
        )

    with pytest.raises(ValueError, match="promotion_target must be a repo-relative path"):
        extract_agent_lesson_record(
            source="review",
            pattern="schema validator drift",
            severity="high",
            affected_surfaces=["scripts/orchestration"],
            root_cause="stale schema",
            required_oracle="schema_validator_parity",
            promotion_target="/Users/example/AGENT_LEARNING_LOOP.md",
        )

    with pytest.raises(ValueError, match="promotion_target must be a repo-relative path"):
        extract_agent_lesson_record(
            source="review",
            pattern="schema validator drift",
            severity="high",
            affected_surfaces=["scripts/orchestration"],
            root_cause="stale schema",
            required_oracle="schema_validator_parity",
            promotion_target="C:\\Users\\example\\AGENT_LEARNING_LOOP.md",
        )

    with pytest.raises(ValueError, match="affected_surfaces must be a repo-relative path"):
        extract_agent_lesson_record(
            source="review",
            pattern="schema validator drift",
            severity="high",
            affected_surfaces=["C:\\Users\\example\\AGENTS.md"],
            root_cause="stale schema",
            required_oracle="schema_validator_parity",
            promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
        )

    with pytest.raises(ValueError, match="promotion_target must be a repo-relative path"):
        extract_agent_lesson_record(
            source="review",
            pattern="schema validator drift",
            severity="high",
            affected_surfaces=["scripts/orchestration"],
            root_cause="stale schema",
            required_oracle="schema_validator_parity",
            promotion_target="file:///Users/example/AGENT_LEARNING_LOOP.md",
        )

    with pytest.raises(ValueError, match="affected_surfaces must be a repo-relative path"):
        extract_agent_lesson_record(
            source="review",
            pattern="schema validator drift",
            severity="high",
            affected_surfaces=["file:///Users/example/AGENTS.md"],
            root_cause="stale schema",
            required_oracle="schema_validator_parity",
            promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
        )

    with pytest.raises(ValueError, match="required_oracle must be one of"):
        extract_agent_lesson_record(
            source="review",
            pattern="schema validator drift",
            severity="high",
            affected_surfaces=["scripts/orchestration"],
            root_cause="stale schema",
            required_oracle="not_a_real_oracle",
            promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
        )


def test_agent_lesson_promoter_is_proposal_only() -> None:
    record = extract_agent_lesson_record(
        source="review",
        pattern="degraded review source",
        severity="medium",
        affected_surfaces=["docs/orchestration"],
        root_cause="source unavailable",
        required_oracle="review_source_degraded",
        promotion_target="docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
    )

    proposal = promote_agent_lesson_record(record)

    assert proposal["side_effects_allowed"] is False
    assert proposal["runtime_authority"] is False
    assert proposal["canonical_until_promoted_by_repo_diff"] is False
    assert proposal["human_review_required"] is True


def test_agent_lesson_promoter_rejects_malformed_records() -> None:
    record = extract_agent_lesson_record(
        source="review",
        pattern="degraded review source",
        severity="medium",
        affected_surfaces=["docs/orchestration"],
        root_cause="source unavailable",
        required_oracle="review_source_degraded",
        promotion_target="docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
    )
    record.update(
        {
            "severity": "urgent",
            "promotion_target": "/Users/example/AGENTS.md",
            "required_oracle": "not_a_real_oracle",
            "dedupe_fingerprint": "notsha",
            "human_review_required": False,
        }
    )

    with pytest.raises(ValueError, match="severity must be one of"):
        promote_agent_lesson_record(record)


def test_agent_lesson_promoter_rejects_tampered_record_fingerprint() -> None:
    record = extract_agent_lesson_record(
        source="review",
        pattern="degraded review source",
        severity="medium",
        affected_surfaces=["docs/orchestration"],
        root_cause="source unavailable",
        required_oracle="review_source_degraded",
        promotion_target="docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
    )

    record["dedupe_fingerprint"] = "sha256:" + ("0" * 64)

    with pytest.raises(ValueError, match="dedupe_fingerprint does not match"):
        promote_agent_lesson_record(record)


def test_agent_lesson_promoter_rejects_unredacted_stored_text() -> None:
    record = extract_agent_lesson_record(
        source="review",
        pattern="degraded review source",
        severity="medium",
        affected_surfaces=["docs/orchestration"],
        root_cause="source unavailable",
        required_oracle="review_source_degraded",
        promotion_target="docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
    )

    record["source"] = "review token=abc"

    with pytest.raises(ValueError, match="source must be redacted"):
        promote_agent_lesson_record(record)


def test_agent_lesson_promoter_rejects_tampered_lesson_id() -> None:
    record = extract_agent_lesson_record(
        source="review",
        pattern="degraded review source",
        severity="medium",
        affected_surfaces=["docs/orchestration"],
        root_cause="source unavailable",
        required_oracle="review_source_degraded",
        promotion_target="docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
    )

    record["lesson_id"] = "lesson-000000000000"

    with pytest.raises(ValueError, match="lesson_id does not match"):
        promote_agent_lesson_record(record)


def test_agent_lesson_promoter_cli_rejects_malformed_records() -> None:
    record = extract_agent_lesson_record(
        source="review",
        pattern="degraded review source",
        severity="medium",
        affected_surfaces=["docs/orchestration"],
        root_cause="source unavailable",
        required_oracle="review_source_degraded",
        promotion_target="docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
    )
    record.update(
        {
            "severity": "urgent",
            "promotion_target": "/Users/example/AGENTS.md",
            "required_oracle": "not_a_real_oracle",
            "dedupe_fingerprint": "notsha",
            "human_review_required": False,
        }
    )

    result = subprocess.run(
        [sys.executable, "scripts/orchestration/agent_lesson_promoter.py"],
        input=json.dumps(record),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Invalid learning record input: severity must be one of" in result.stderr


def test_agent_lesson_promoter_loads_record_file_with_full_contract_validation(
    tmp_path: Path,
) -> None:
    record = extract_agent_lesson_record(
        source="review",
        pattern="degraded review source",
        severity="medium",
        affected_surfaces=["docs/orchestration"],
        root_cause="source unavailable",
        required_oracle="review_source_degraded",
        promotion_target="docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
    )
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record), encoding="utf-8")

    assert _load_record(str(path)) == record

    record["unexpected"] = "drift"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected fields unexpected"):
        _load_record(str(path))


def test_agent_lesson_promoter_cli_emits_proposal_from_stdin() -> None:
    record = extract_agent_lesson_record(
        source="review",
        pattern="degraded review source",
        severity="medium",
        affected_surfaces=["docs/orchestration"],
        root_cause="source unavailable",
        required_oracle="review_source_degraded",
        promotion_target="docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
    )

    result = subprocess.run(
        [sys.executable, "scripts/orchestration/agent_lesson_promoter.py"],
        input=json.dumps(record),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    proposal = json.loads(result.stdout)
    assert proposal["schema_version"] == "agent_learning_promotion_proposal.v1"
    assert proposal["human_review_required"] is True


def test_agent_lesson_promoter_cli_reports_unreadable_record_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing-record.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/orchestration/agent_lesson_promoter.py",
            "--record",
            str(missing),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Invalid learning record input:" in result.stderr
    assert str(missing) not in result.stderr
    assert "unable to read record file" in result.stderr


def test_agent_lesson_promoter_cli_redacts_system_absolute_record_path() -> None:
    missing = "/etc/pulseplate-missing-record.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/orchestration/agent_lesson_promoter.py",
            "--record",
            missing,
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Invalid learning record input:" in result.stderr
    assert missing not in result.stderr
    assert "unable to read record file" in result.stderr


def test_agent_learning_record_schema_matches_extractor_shape() -> None:
    record = extract_agent_lesson_record(
        source="review",
        pattern="mapping evidence timing",
        severity="low",
        affected_surfaces=["docs/review"],
        root_cause="stale mapping",
        required_oracle="evidence_hygiene_mapping_timing",
        promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
    )
    schema = json.loads(
        Path("docs/orchestration/contracts/agent_learning_record.v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert set(schema["required"]) == set(record)
    assert schema["properties"]["human_review_required"]["const"] is True
    assert record["severity"] in schema["properties"]["severity"]["enum"]
    assert schema["properties"]["required_oracle"]["enum"] == list(REVIEW_PATTERN_ORACLE_IDS)
    assert "pattern" in schema["properties"]["affected_surfaces"]["items"]
    assert "pattern" in schema["properties"]["promotion_target"]
    assert "(?![A-Za-z]:[\\\\/])" in schema["properties"]["promotion_target"]["pattern"]
    assert "(?![A-Za-z][A-Za-z0-9+.-]*:)" in schema["properties"]["promotion_target"]["pattern"]
    assert "(?![A-Za-z]:[\\\\/])" in schema["properties"]["affected_surfaces"]["items"]["pattern"]
    assert (
        "(?![A-Za-z][A-Za-z0-9+.-]*:)"
        in schema["properties"]["affected_surfaces"]["items"]["pattern"]
    )
