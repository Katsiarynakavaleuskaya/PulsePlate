"""Tests for proposal-only agent learning-loop helpers."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.orchestration.agent_learning_loop import (
    build_agent_learning_record,
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


def test_learning_loop_redacts_linux_home_and_workspace_paths() -> None:
    assert redact_learning_text("see /home/runner/work/PulsePlate/.env") == "see <redacted-path>"
    assert redact_learning_text("see /workspace/PulsePlate/log.txt") == "see <redacted-path>"


def test_learning_loop_redacts_common_linux_absolute_paths() -> None:
    for path in (
        "/root/.ssh/id_rsa",
        "/etc/passwd",
        "/opt/pulseplate/config.toml",
        "/usr/local/bin/tool",
        "/mnt/runner/work/PulsePlate/log.txt",
    ):
        assert redact_learning_text(f"see {path}") == "see <redacted-path>"


def test_learning_loop_redacts_raw_model_artifact_markers() -> None:
    assert redact_learning_text("raw_prompt: please mutate workflow") == "<redacted>"
    assert redact_learning_text('provider_payload={"token":"x"} was included') == "<redacted>"
    assert redact_learning_text("chain of thought should never be stored") == "<redacted>"
    assert redact_learning_text("candidate.patch=/tmp/candidate.patch") == "<redacted>"
    assert redact_learning_text("before\ndiff --git a/app/main.py b/app/main.py\nafter") == (
        "before\n<redacted>\nafter"
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
        "pattern_kind",
        "pattern",
        "severity",
        "affected_surfaces",
        "root_cause",
        "required_oracle",
        "promotion_target",
        "learning_metrics",
        "dedupe_fingerprint",
        "redaction_status",
        "human_review_required",
    }
    assert record["severity"] == "high"
    assert record["pattern_kind"] == "failure"
    assert record["learning_metrics"]["primary_metric"] == "repeat_failure_reduction"
    assert record["learning_metrics"]["runtime_telemetry_allowed"] is False
    assert record["learning_metrics"]["product_runtime_truth"] is False
    assert record["learning_metrics"]["semantic_cache_used"] is False
    assert record["learning_metrics"]["graph_truth_updated"] is False
    assert record["source"] == "review <redacted> <redacted-path>"
    assert record["affected_surfaces"] == ["scripts/orchestration"]
    assert record["root_cause"] == "<redacted> reused stale schema from <redacted-path>"
    assert record["redaction_status"] == "redacted"
    assert record["human_review_required"] is True


def test_agent_lesson_extractor_records_successful_iteration_patterns() -> None:
    failure_record = extract_agent_lesson_record(
        source="role pass",
        pattern="premortem closed risks with code and tests",
        severity="low",
        affected_surfaces=["AGENTS.md"],
        root_cause="repeatable effective iteration",
        required_oracle="evidence_hygiene_mapping_timing",
        promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
    )
    success_record = extract_agent_lesson_record(
        source="role pass",
        pattern="premortem closed risks with code and tests",
        severity="low",
        affected_surfaces=["AGENTS.md"],
        root_cause="repeatable effective iteration",
        required_oracle="evidence_hygiene_mapping_timing",
        promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
        pattern_kind="successful_iteration",
    )

    assert failure_record["pattern_kind"] == "failure"
    assert success_record["pattern_kind"] == "successful_iteration"
    assert success_record["learning_metrics"]["primary_metric"] == ("successful_pattern_reuse")
    assert "agent_iteration_quality" in success_record["learning_metrics"]["secondary_metrics"]
    assert failure_record["dedupe_fingerprint"] != success_record["dedupe_fingerprint"]
    assert promote_agent_lesson_record(success_record)["pattern_kind"] == ("successful_iteration")


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

    with pytest.raises(ValueError, match="pattern_kind must be one of"):
        extract_agent_lesson_record(
            source="review",
            pattern="schema validator drift",
            pattern_kind="maybe",
            severity="high",
            affected_surfaces=["scripts/orchestration"],
            root_cause="stale schema",
            required_oracle="schema_validator_parity",
            promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
        )

    with pytest.raises(ValueError, match="learning_metrics.primary_metric must be one of"):
        build_agent_learning_record(
            source="review",
            pattern="schema validator drift",
            severity="high",
            affected_surfaces=["scripts/orchestration"],
            root_cause="stale schema",
            required_oracle="schema_validator_parity",
            promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
            learning_metrics={
                "schema_version": "agent_learning_metrics.v1",
                "primary_metric": "not_a_metric",
                "secondary_metrics": [],
                "measurement_window": "next_comparable_pr",
                "authority_boundary": "proposal_only_non_runtime",
                "runtime_telemetry_allowed": False,
                "product_runtime_truth": False,
                "semantic_cache_used": False,
                "graph_truth_updated": False,
            },
        )

    with pytest.raises(
        ValueError,
        match="primary_metric must be successful_pattern_reuse for successful_iteration",
    ):
        build_agent_learning_record(
            source="review",
            pattern="effective premortem",
            severity="low",
            affected_surfaces=["scripts/orchestration"],
            root_cause="operator success pattern",
            required_oracle="evidence_hygiene_mapping_timing",
            promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
            pattern_kind="successful_iteration",
            learning_metrics={
                "schema_version": "agent_learning_metrics.v1",
                "primary_metric": "repeat_failure_reduction",
                "secondary_metrics": ["agent_iteration_quality"],
                "measurement_window": "next_comparable_pr",
                "authority_boundary": "proposal_only_non_runtime",
                "runtime_telemetry_allowed": False,
                "product_runtime_truth": False,
                "semantic_cache_used": False,
                "graph_truth_updated": False,
            },
        )

    with pytest.raises(
        ValueError,
        match="secondary_metrics must include agent_iteration_quality for successful_iteration",
    ):
        build_agent_learning_record(
            source="review",
            pattern="effective premortem",
            severity="low",
            affected_surfaces=["scripts/orchestration"],
            root_cause="operator success pattern",
            required_oracle="evidence_hygiene_mapping_timing",
            promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
            pattern_kind="successful_iteration",
            learning_metrics={
                "schema_version": "agent_learning_metrics.v1",
                "primary_metric": "successful_pattern_reuse",
                "secondary_metrics": [],
                "measurement_window": "next_comparable_pr",
                "authority_boundary": "proposal_only_non_runtime",
                "runtime_telemetry_allowed": False,
                "product_runtime_truth": False,
                "semantic_cache_used": False,
                "graph_truth_updated": False,
            },
        )

    with pytest.raises(
        ValueError,
        match="secondary_metrics must not use failure metrics for successful_iteration",
    ):
        build_agent_learning_record(
            source="review",
            pattern="effective premortem",
            severity="low",
            affected_surfaces=["scripts/orchestration"],
            root_cause="operator success pattern",
            required_oracle="evidence_hygiene_mapping_timing",
            promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
            pattern_kind="successful_iteration",
            learning_metrics={
                "schema_version": "agent_learning_metrics.v1",
                "primary_metric": "successful_pattern_reuse",
                "secondary_metrics": ["agent_iteration_quality", "repeat_failure_reduction"],
                "measurement_window": "next_comparable_pr",
                "authority_boundary": "proposal_only_non_runtime",
                "runtime_telemetry_allowed": False,
                "product_runtime_truth": False,
                "semantic_cache_used": False,
                "graph_truth_updated": False,
            },
        )

    with pytest.raises(
        ValueError,
        match="secondary_metrics must not use successful_pattern_reuse for failure",
    ):
        build_agent_learning_record(
            source="review",
            pattern="premortem escaped code closure",
            severity="medium",
            affected_surfaces=["scripts/orchestration"],
            root_cause="failure pattern",
            required_oracle="evidence_hygiene_mapping_timing",
            promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
            pattern_kind="failure",
            learning_metrics={
                "schema_version": "agent_learning_metrics.v1",
                "primary_metric": "repeat_failure_reduction",
                "secondary_metrics": ["successful_pattern_reuse"],
                "measurement_window": "next_comparable_pr",
                "authority_boundary": "proposal_only_non_runtime",
                "runtime_telemetry_allowed": False,
                "product_runtime_truth": False,
                "semantic_cache_used": False,
                "graph_truth_updated": False,
            },
        )

    with pytest.raises(
        ValueError,
        match=(
            "secondary_metrics must include premortem_code_closure_rate "
            "or review_actionable_escape_reduction for failure"
        ),
    ):
        build_agent_learning_record(
            source="review",
            pattern="premortem escaped code closure",
            severity="medium",
            affected_surfaces=["scripts/orchestration"],
            root_cause="failure pattern",
            required_oracle="evidence_hygiene_mapping_timing",
            promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
            pattern_kind="failure",
            learning_metrics={
                "schema_version": "agent_learning_metrics.v1",
                "primary_metric": "repeat_failure_reduction",
                "secondary_metrics": ["user_impact_clarity"],
                "measurement_window": "next_comparable_pr",
                "authority_boundary": "proposal_only_non_runtime",
                "runtime_telemetry_allowed": False,
                "product_runtime_truth": False,
                "semantic_cache_used": False,
                "graph_truth_updated": False,
            },
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


def test_agent_lesson_extractor_redacts_raw_model_payload_before_promotion() -> None:
    record = extract_agent_lesson_record(
        source="raw_response: generated by external tool",
        pattern='provider_payload={"candidate":true}',
        severity="medium",
        affected_surfaces=["docs/orchestration"],
        root_cause="diff --git a/app/main.py b/app/main.py",
        required_oracle="fail_closed_security_edge",
        promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
    )

    combined = "\n".join([record["source"], record["pattern"], record["root_cause"]])
    assert "raw_response" not in combined
    assert "provider_payload" not in combined
    assert "diff --git" not in combined
    assert promote_agent_lesson_record(record)["dedupe_fingerprint"] == record["dedupe_fingerprint"]


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
    assert proposal["learning_metrics"]["primary_metric"] == "repeat_failure_reduction"
    assert proposal["learning_metrics"]["runtime_telemetry_allowed"] is False
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


def test_agent_lesson_promoter_rejects_tampered_redaction_status() -> None:
    record = extract_agent_lesson_record(
        source="review token=abc",
        pattern="degraded review source",
        severity="medium",
        affected_surfaces=["docs/orchestration"],
        root_cause="source unavailable",
        required_oracle="review_source_degraded",
        promotion_target="docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
    )

    assert record["redaction_status"] == "redacted"
    record["redaction_status"] = "clean"

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
    assert record["pattern_kind"] in schema["properties"]["pattern_kind"]["enum"]
    assert schema["properties"]["pattern_kind"]["enum"] == [
        "failure",
        "successful_iteration",
    ]
    metrics_schema = schema["properties"]["learning_metrics"]
    failure_guard, success_guard = schema["allOf"]
    assert metrics_schema["properties"]["schema_version"]["const"] == ("agent_learning_metrics.v1")
    assert metrics_schema["properties"]["authority_boundary"]["const"] == (
        "proposal_only_non_runtime"
    )
    assert metrics_schema["properties"]["runtime_telemetry_allowed"]["const"] is False
    assert metrics_schema["properties"]["product_runtime_truth"]["const"] is False
    assert metrics_schema["properties"]["semantic_cache_used"]["const"] is False
    assert metrics_schema["properties"]["graph_truth_updated"]["const"] is False
    assert (
        record["learning_metrics"]["primary_metric"]
        in metrics_schema["properties"]["primary_metric"]["enum"]
    )
    assert failure_guard["if"]["properties"]["pattern_kind"]["const"] == "failure"
    failure_secondary = failure_guard["then"]["properties"]["learning_metrics"]["properties"][
        "secondary_metrics"
    ]
    assert (
        failure_guard["then"]["properties"]["learning_metrics"]["properties"]["primary_metric"][
            "const"
        ]
        == "repeat_failure_reduction"
    )
    assert failure_secondary["contains"]["enum"] == [
        "premortem_code_closure_rate",
        "review_actionable_escape_reduction",
    ]
    assert failure_secondary["not"]["contains"]["const"] == "successful_pattern_reuse"
    assert success_guard["if"]["properties"]["pattern_kind"]["const"] == "successful_iteration"
    assert (
        success_guard["then"]["properties"]["learning_metrics"]["properties"]["primary_metric"][
            "const"
        ]
        == "successful_pattern_reuse"
    )
    assert (
        success_guard["then"]["properties"]["learning_metrics"]["properties"]["secondary_metrics"][
            "contains"
        ]["const"]
        == "agent_iteration_quality"
    )
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
