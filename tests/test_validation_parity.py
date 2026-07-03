"""Shared negative fixture parity for orchestration schema/runtime validators."""

from __future__ import annotations

from copy import deepcopy
import json
import re
from pathlib import Path
from typing import Any

import pytest

from scripts.orchestration.agent_learning_loop import (
    build_agent_learning_record,
    validate_agent_learning_record,
)
from scripts.orchestration.experiment_runner_pr_creative_context_contract import (
    ExperimentRunnerCreativeContextContractError,
    build_creative_hypothesis_agent_routing,
    build_creative_hypothesis_packet,
    build_creative_protocol_context_map,
    reject_unsafe_creative_context_value,
    validate_creative_hypothesis_agent_routing,
    validate_creative_hypothesis_packet,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "orchestration" / "validation_negative_cases.json"
CONTRACT_DIR = REPO_ROOT / "docs" / "orchestration" / "contracts"
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
SHA256 = "sha256:" + ("c" * 64)


def _negative_cases() -> list[dict[str, Any]]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["schema_version"] == "orchestration_validation_negative_cases.v1"
    return list(fixture["cases"])


def _cases_by_category(category: str) -> list[dict[str, Any]]:
    return [case for case in _negative_cases() if case["category"] == category]


def _schema(filename: str) -> dict[str, Any]:
    return json.loads((CONTRACT_DIR / filename).read_text(encoding="utf-8"))


def _safe_text_patterns(filename: str) -> list[str]:
    schema = _schema(filename)
    return [row["pattern"] for row in schema["$defs"]["safe_text"]["not"]["anyOf"]]


def _context(*, generated_at_utc: str | None = "2026-07-03T12:00:00Z") -> dict[str, Any]:
    return build_creative_protocol_context_map(
        changed_paths=[
            "scripts/orchestration/experiment_runner_pr_creative_context.py",
            "docs/orchestration/contracts/EXPERIMENT_RUNNER_PR_CREATIVE_CONTEXT_CONTRACT.md",
        ],
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2069,
        base_ref="main",
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        task_packet_id="task:validation-parity",
        generated_at_utc=generated_at_utc,
        nearby_repo_refs=["scripts/orchestration/experiment_runner.py"],
        test_refs=["tests/test_validation_parity.py"],
        contract_refs=[
            "docs/orchestration/contracts/EXPERIMENT_RUNNER_PR_CREATIVE_CONTEXT_CONTRACT.md",
        ],
        backlog_refs=["docs/roadmap/BACKLOG_LEDGER.md"],
        review_source_refs=[
            "artifacts/orchestration/experiments/results/oracle-result.json",
        ],
        capability_state_ref=(
            "artifacts/orchestration/experiments/creative_context/capability_state.json"
        ),
        philosophical_context_refs=["docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md"],
        cross_domain_candidate_refs=[
            "docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md",
        ],
        label_enabled=True,
        sealed_codex_security_scan_ref=(
            "artifacts/orchestration/experiments/creative_context/codex-security.json"
        ),
        sealed_codex_security_scan_fingerprint=SHA256,
        security_relevant_diff_changed=False,
    )


def _packet() -> dict[str, Any]:
    return build_creative_hypothesis_packet(_context(), hypothesis_count=3)


def _learning_record() -> dict[str, Any]:
    return build_agent_learning_record(
        source="review",
        pattern="schema validator parity",
        severity="high",
        affected_surfaces=["scripts/orchestration"],
        root_cause="schema drift",
        required_oracle="schema_validator_parity",
        promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
        pattern_kind="failure",
    )


def test_negative_fixture_matrix_pins_expected_review_case_categories() -> None:
    """The fixture should cover the recurring review classes from recent PRs."""

    assert {case["category"] for case in _negative_cases()} == {
        "raw_model_labels",
        "patch_hunks",
        "broad_root_targets",
        "null_learning_metrics",
        "invalid_timestamps",
        "invalid_agent_slugs",
        "local_absolute_paths",
    }


@pytest.mark.parametrize(
    "case",
    _cases_by_category("raw_model_labels")
    + _cases_by_category("patch_hunks")
    + _cases_by_category("local_absolute_paths"),
    ids=lambda case: case["case_id"],
)
def test_safe_text_schema_patterns_match_python_unsafe_text_rejections(
    case: dict[str, Any],
) -> None:
    """Unsafe text classes must be rejected by both schema fragments and Python."""

    value = str(case["value"])
    for filename in (
        "creative_hypothesis_operator_model_intake.v1.schema.json",
        "creative_hypothesis_packet.v1.schema.json",
    ):
        assert any(re.search(pattern, value) for pattern in _safe_text_patterns(filename))

    with pytest.raises(ExperimentRunnerCreativeContextContractError):
        reject_unsafe_creative_context_value(value, label=case["case_id"])


@pytest.mark.parametrize(
    "case",
    _cases_by_category("broad_root_targets"),
    ids=lambda case: case["case_id"],
)
def test_concrete_target_schema_patterns_match_python_target_rejections(
    case: dict[str, Any],
) -> None:
    """Broad/root targets must not pass schema path classes or runtime validation."""

    value = str(case["value"])
    for filename in (
        "creative_hypothesis_operator_model_intake.v1.schema.json",
        "creative_hypothesis_packet.v1.schema.json",
    ):
        concrete_target_path = _schema(filename)["$defs"]["concrete_target_path"]
        allowed_prefix = concrete_target_path["allOf"][1]["pattern"]
        assert re.match(allowed_prefix, value) is None

    packet = _packet()
    packet["hypotheses"][0]["target_surfaces"] = [value]
    with pytest.raises(ExperimentRunnerCreativeContextContractError):
        validate_creative_hypothesis_packet(packet)


@pytest.mark.parametrize(
    "case",
    _cases_by_category("null_learning_metrics"),
    ids=lambda case: case["case_id"],
)
def test_learning_record_schema_and_python_reject_null_metrics(case: dict[str, Any]) -> None:
    """Learning metrics must be a real object, never a null placeholder."""

    field = str(case["field"])
    schema = _schema("agent_learning_record.v1.json")
    assert field in schema["required"]
    assert schema["properties"][field]["type"] == "object"

    record = _learning_record()
    record[field] = case["value"]
    with pytest.raises(ValueError, match="learning_metrics must be a JSON object"):
        validate_agent_learning_record(record)


@pytest.mark.parametrize(
    "case",
    _cases_by_category("invalid_timestamps"),
    ids=lambda case: case["case_id"],
)
def test_timestamp_schema_patterns_match_python_timestamp_rejections(
    case: dict[str, Any],
) -> None:
    """UTC timestamp schema shape and runtime validator must reject offset timestamps."""

    value = str(case["value"])
    timestamp_schema = _schema("creative_protocol_context_map.v1.schema.json")["$defs"][
        "utc_timestamp"
    ]
    assert re.match(timestamp_schema["pattern"], value) is None

    with pytest.raises(ExperimentRunnerCreativeContextContractError):
        _context(generated_at_utc=value)


@pytest.mark.parametrize(
    "case",
    _cases_by_category("invalid_agent_slugs"),
    ids=lambda case: case["case_id"],
)
def test_agent_slug_schema_patterns_match_python_routing_rejections(
    case: dict[str, Any],
) -> None:
    """Missing-agent capability names must use the same slug class as active agents."""

    value = str(case["value"])
    agent_slug_schema = _schema("creative_hypothesis_agent_routing.v1.schema.json")["$defs"][
        "agent_slug"
    ]
    assert re.match(agent_slug_schema["pattern"], value) is None

    routing = deepcopy(build_creative_hypothesis_agent_routing(_packet()))
    routing["routing"][0]["missing_agent_capabilities"] = [value]
    with pytest.raises(ExperimentRunnerCreativeContextContractError, match="agent slug"):
        validate_creative_hypothesis_agent_routing(routing)
