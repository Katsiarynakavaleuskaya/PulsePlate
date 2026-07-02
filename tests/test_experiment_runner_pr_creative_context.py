"""Tests for Experiment Runner PR creative-context contracts and CLI."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.orchestration import experiment_runner_pr_creative_context as cli
from scripts.orchestration.experiment_runner_pr_creative_context_contract import (
    AGENT_ROUTING_TYPE,
    APPROVAL_TYPE,
    AUTHORITY_FALSE_KEYS,
    AUTHORITY_TRUE_KEYS,
    CONTEXT_MAP_TYPE,
    CONSUMPTION_SUMMARY_TYPE,
    HYPOTHESIS_PACKET_TYPE,
    ORACLE_ATTACHMENT_TYPE,
    POLICY_VERSION,
    SCHEMA_VERSION,
    ExperimentRunnerCreativeContextContractError,
    build_agent_consumption_summary,
    build_creative_hypothesis_agent_routing,
    build_creative_hypothesis_approval,
    build_creative_hypothesis_packet,
    build_creative_protocol_context_map,
    build_experiment_runner_pr_oracle_attachment,
    default_creative_context_authority,
    read_json_object,
    reject_unsafe_creative_context_value,
    validate_artifact_by_type,
    validate_creative_hypothesis_packet,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
SHA256 = "sha256:" + ("c" * 64)


def _context(
    *,
    changed_paths: list[str] | None = None,
    label_enabled: bool = False,
    marker_enabled: bool = False,
    manual_enabled: bool = False,
) -> dict[str, object]:
    return build_creative_protocol_context_map(
        changed_paths=changed_paths
        or [
            "scripts/orchestration/experiment_runner_pr_creative_context.py",
            "docs/orchestration/contracts/EXPERIMENT_RUNNER_PR_CREATIVE_CONTEXT_CONTRACT.md",
        ],
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2061,
        base_ref="main",
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        task_packet_id="task:creative-context",
        generated_at_utc="2026-07-02T00:00:00Z",
        nearby_repo_refs=["scripts/orchestration/experiment_runner.py"],
        test_refs=["tests/test_experiment_runner_pr_creative_context.py"],
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
        label_enabled=label_enabled,
        marker_enabled=marker_enabled,
        manual_enabled=manual_enabled,
        sealed_codex_security_scan_ref=(
            "artifacts/orchestration/experiments/creative_context/codex-security.json"
        ),
        sealed_codex_security_scan_fingerprint=SHA256,
        security_relevant_diff_changed=False,
    )


def _packet(hypothesis_count: int = 4) -> dict[str, object]:
    return build_creative_hypothesis_packet(
        _context(),
        hypothesis_count=hypothesis_count,
    )


def test_valid_artifact_chain_enforces_creative_authority_boundary() -> None:
    context = _context()
    packet = build_creative_hypothesis_packet(context, hypothesis_count=4)
    routing = build_creative_hypothesis_agent_routing(packet)
    oracle = build_experiment_runner_pr_oracle_attachment(
        source=context["source"],
        oracle_status="accepted",
        result_ref="artifacts/orchestration/experiments/results/oracle-result.json",
        result_fingerprint=SHA256,
        coauthor_required=True,
    )
    summary = build_agent_consumption_summary(
        oracle_attachment=oracle,
        hypothesis_packet=packet,
        routing=routing,
    )
    approval = build_creative_hypothesis_approval(
        hypothesis_id=packet["hypotheses"][0]["hypothesis_id"],
        decision="approve_for_pr1_specification",
        approved_target_surfaces=packet["hypotheses"][0]["target_surfaces"],
        approved_agents=[routing["routing"][0]["primary_agent"]],
        next_step="create_pr1_specification",
    )

    assert packet["creative_status"] == "hypotheses_generated"
    assert packet["hypothesis_count"] == 4
    assert summary["next_allowed_action"] == "agent_review"
    assert summary["requires_human_approval"] is True
    assert summary["coauthor_required"] is True
    assert approval["generate_patch"] is False
    for artifact_type, payload in [
        (CONTEXT_MAP_TYPE, context),
        (HYPOTHESIS_PACKET_TYPE, packet),
        (AGENT_ROUTING_TYPE, routing),
        (ORACLE_ATTACHMENT_TYPE, oracle),
        (CONSUMPTION_SUMMARY_TYPE, summary),
        (APPROVAL_TYPE, approval),
    ]:
        validated = validate_artifact_by_type(artifact_type, payload)
        assert validated["authority"] == default_creative_context_authority()
        assert all(validated["authority"][key] is True for key in AUTHORITY_TRUE_KEYS)
        assert all(validated["authority"][key] is False for key in AUTHORITY_FALSE_KEYS)


@pytest.mark.parametrize("hypothesis_count", [3, 5])
def test_eligible_context_accepts_three_to_five_hypotheses(hypothesis_count: int) -> None:
    packet = _packet(hypothesis_count=hypothesis_count)

    assert packet["hypothesis_count"] == hypothesis_count
    assert all(row["requires_human_approval"] is True for row in packet["hypotheses"])
    assert all(row["eligible_for_pr2_patch"] is False for row in packet["hypotheses"])


@pytest.mark.parametrize("hypothesis_count", [2, 6])
def test_eligible_context_rejects_out_of_range_hypothesis_counts(
    hypothesis_count: int,
) -> None:
    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="3 to 5 hypotheses",
    ):
        _packet(hypothesis_count=hypothesis_count)


def test_each_generated_hypothesis_contains_quality_fields() -> None:
    packet = _packet()

    for row in packet["hypotheses"]:
        assert row["target_surfaces"]
        assert row["expected_behavior"]
        assert row["tests_or_oracles"]
        assert row["risk_notes"]
        assert row["falsifier"]
        assert row["cross_domain_analogies"]
        assert row["negative_controls"]
        assert row["requires_human_approval"] is True
        assert row["eligible_for_pr1_specification"] is True
        assert row["eligible_for_pr2_patch"] is False


@pytest.mark.parametrize(
    ("changed_paths", "reason_code"),
    [
        (["docs/README.md"], "docs_only_no_runtime_action"),
        (["app/main.py"], "product_runtime_surface"),
        ([".github/workflows/experiment-runner.yml"], "workflow_deferred_followup"),
    ],
)
def test_ineligible_surfaces_emit_no_creative_action(
    changed_paths: list[str],
    reason_code: str,
) -> None:
    context = _context(changed_paths=changed_paths)
    packet = build_creative_hypothesis_packet(context)

    assert context["classification"]["eligible"] is False
    assert packet["creative_status"] == "no_creative_action"
    assert packet["reason_code"] == reason_code
    assert packet["hypotheses"] == []


@pytest.mark.parametrize(
    ("flag_name", "reason_code"),
    [
        ("label_enabled", "label_activation"),
        ("marker_enabled", "marker_activation"),
        ("manual_enabled", "manual_activation"),
    ],
)
def test_marker_label_and_manual_activation_require_hypotheses(
    flag_name: str,
    reason_code: str,
) -> None:
    context = _context(
        changed_paths=["scripts/shared_creative_context_helper.py"],
        **{flag_name: True},
    )
    packet = build_creative_hypothesis_packet(context, hypothesis_count=3)

    assert context["classification"]["eligible"] is True
    assert context["classification"]["reason_code"] == reason_code
    assert packet["hypothesis_count"] == 3


def test_docs_only_hypothesis_packet_is_rejected_for_generated_creative_action() -> None:
    packet = deepcopy(_packet())
    for row in packet["hypotheses"]:
        row["target_surfaces"] = ["docs/orchestration/README.md"]

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="concrete code, test, contract, agent, or prompt/program target",
    ):
        validate_creative_hypothesis_packet(packet)


def test_unknown_fields_duplicate_keys_and_authority_escalation_are_rejected(
    tmp_path: Path,
) -> None:
    context = _context()
    context_with_extra = {**context, "raw_body": "redacted"}
    with pytest.raises(ExperimentRunnerCreativeContextContractError, match="unsupported fields"):
        validate_artifact_by_type(CONTEXT_MAP_TYPE, context_with_extra)

    duplicate_path = tmp_path / "duplicate.json"
    duplicate_path.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")
    with pytest.raises(ExperimentRunnerCreativeContextContractError, match="duplicate key"):
        read_json_object(duplicate_path)

    packet = deepcopy(_packet())
    packet["authority"]["generate_patch"] = True
    with pytest.raises(ExperimentRunnerCreativeContextContractError, match="generate_patch"):
        validate_creative_hypothesis_packet(packet)


@pytest.mark.parametrize(
    "unsafe_value",
    [
        {"review_thread_body": "looks actionable"},
        {"provider_payload": {"text": "hello"}},
        {"oracle_stdout": "pytest output"},
        {"candidate": "diff --git a/app/main.py b/app/main.py"},
        {"local_path": "/Users/example/repo/file.py"},
        {"token_value": "ghs_exampletoken"},
        {"status": "ready to merge"},
    ],
)
def test_safety_filter_rejects_raw_or_sensitive_surfaces(
    unsafe_value: dict[str, object],
) -> None:
    with pytest.raises(ExperimentRunnerCreativeContextContractError):
        reject_unsafe_creative_context_value(unsafe_value, label="payload")


@pytest.mark.parametrize(
    "bad_path",
    [
        "../scripts/orchestration/tool.py",
        "/Users/example/repo/tool.py",
        "file://repo/tool.py",
        "worktrees/lane/file.py",
        ".venv/bin/python",
        ".git/config",
        "artifacts/random/result.json",
    ],
)
def test_path_validation_rejects_traversal_local_paths_and_unapproved_artifacts(
    bad_path: str,
) -> None:
    with pytest.raises(ExperimentRunnerCreativeContextContractError):
        build_creative_protocol_context_map(changed_paths=[bad_path])


def test_routing_records_missing_specialist_agents_and_uses_registered_fallback() -> None:
    packet = _packet(hypothesis_count=5)
    registered_agents = {
        "agent-coordinator",
        "architecture-specialist",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
        "logic-agent",
        "data-scientist-agent",
        "epistemology-discovery-agent",
    }

    routing = build_creative_hypothesis_agent_routing(
        packet,
        registered_agents=registered_agents,
    )

    scientific_route = next(
        row
        for row in routing["routing"]
        if row["hypothesis_id"] == packet["hypotheses"][4]["hypothesis_id"]
    )
    assert scientific_route["primary_agent"] == "data-scientist-agent"
    assert "experiment-design-stats-agent" in scientific_route["missing_agent_capabilities"]
    assert all(row["mutation_authority"] is False for row in routing["routing"])


def test_cli_prepare_writes_only_approved_local_artifact_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    creative_root = tmp_path / "creative_context"
    monkeypatch.setattr(cli, "CREATIVE_CONTEXT_ROOT", creative_root)

    exit_code = cli.main(
        [
            "prepare",
            "--changed-path",
            "scripts/orchestration/experiment_runner_pr_creative_context.py",
            "--base-sha",
            BASE_SHA,
            "--head-sha",
            HEAD_SHA,
            "--generated-at-utc",
            "2026-07-02T00:00:00Z",
            "--test-ref",
            "tests/test_experiment_runner_pr_creative_context.py",
            "--contract-ref",
            "docs/orchestration/contracts/EXPERIMENT_RUNNER_PR_CREATIVE_CONTEXT_CONTRACT.md",
            "--output-dir",
            "lane",
            "--hypothesis-count",
            "3",
        ]
    )

    output = capsys.readouterr()
    assert exit_code == 0
    assert cli.SUCCESS_PREPARE_OUTPUT in output.out
    observed = sorted(path.name for path in (creative_root / "lane").iterdir())
    assert observed == [
        "agent_consumption_summary.json",
        "agent_routing.json",
        "context_map.json",
        "hypothesis_packet.json",
        "oracle_attachment.json",
    ]
    for name in observed:
        payload = read_json_object(creative_root / "lane" / name)
        assert payload["sanitized"] is True


def test_cli_rejects_output_outside_creative_context_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli, "CREATIVE_CONTEXT_ROOT", tmp_path / "creative_context")

    exit_code = cli.main(
        [
            "collect-context",
            "--changed-path",
            "scripts/orchestration/experiment_runner_pr_creative_context.py",
            "--output",
            str(tmp_path / "outside" / "context_map.json"),
        ]
    )

    assert exit_code == 1


def test_schema_files_pin_artifact_type_and_policy_version() -> None:
    schema_files = {
        "experiment_runner_pr_oracle_attachment.v1.schema.json": ORACLE_ATTACHMENT_TYPE,
        "creative_protocol_context_map.v1.schema.json": CONTEXT_MAP_TYPE,
        "creative_hypothesis_packet.v1.schema.json": HYPOTHESIS_PACKET_TYPE,
        "creative_hypothesis_agent_routing.v1.schema.json": AGENT_ROUTING_TYPE,
        "creative_hypothesis_agent_consumption_summary.v1.schema.json": (CONSUMPTION_SUMMARY_TYPE),
        "creative_hypothesis_approval.v1.schema.json": APPROVAL_TYPE,
    }

    for filename, artifact_type in schema_files.items():
        schema_path = REPO_ROOT / "docs" / "orchestration" / "contracts" / filename
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        assert schema["additionalProperties"] is False
        assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION
        assert schema["properties"]["artifact_type"]["const"] == artifact_type
        assert schema["properties"]["policy_version"]["const"] == POLICY_VERSION
        assert schema["properties"]["sanitized"]["const"] is True
