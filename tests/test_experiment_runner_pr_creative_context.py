"""Tests for Experiment Runner PR creative-context contracts and CLI."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any
import uuid

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import experiment_runner_pr_creative_context as cli
from scripts.orchestration import evidence_rail_applicability as rail_applicability
from scripts.orchestration import task_bootstrap as bootstrap
from scripts.orchestration.experiment_runner_pr_creative_context_contract import (
    AGENT_ROUTING_TYPE,
    APPROVAL_TYPE,
    AUTHORITY_FALSE_KEYS,
    AUTHORITY_KEYS,
    AUTHORITY_TRUE_KEYS,
    COORDINATOR_DISPATCH_AUTHORITY_FALSE_KEYS,
    COORDINATOR_DISPATCH_AUTHORITY_KEYS,
    COORDINATOR_DISPATCH_AUTHORITY_TRUE_KEYS,
    COORDINATOR_DISPATCH_POLICY_VERSION,
    COORDINATOR_DISPATCH_TYPE,
    CONTEXT_MAP_TYPE,
    CONSUMPTION_SUMMARY_TYPE,
    HYPOTHESIS_PACKET_TYPE,
    INTAKE_AUTHORITY_FALSE_KEYS,
    INTAKE_AUTHORITY_KEYS,
    INTAKE_AUTHORITY_TRUE_KEYS,
    ORACLE_ATTACHMENT_TYPE,
    OPERATOR_MODEL_INTAKE_POLICY_VERSION,
    OPERATOR_MODEL_INTAKE_TYPE,
    POLICY_VERSION,
    REASON_CODES,
    SCHEMA_VERSION,
    ExperimentRunnerCreativeContextContractError,
    _artifact_identity,
    build_agent_consumption_summary,
    build_creative_hypothesis_coordinator_dispatch,
    build_creative_hypothesis_agent_routing,
    build_creative_hypothesis_approval,
    build_creative_hypothesis_packet,
    build_creative_hypothesis_packet_from_model_intake,
    build_creative_protocol_context_map,
    build_creative_workflow_stage,
    build_experiment_runner_pr_oracle_attachment,
    default_creative_context_authority,
    default_coordinator_dispatch_authority,
    default_operator_model_intake_authority,
    read_json_object,
    reject_unsafe_creative_context_value,
    validate_artifact_by_type,
    validate_creative_hypothesis_agent_routing,
    validate_creative_hypothesis_coordinator_dispatch,
    validate_creative_hypothesis_operator_model_intake,
    validate_creative_hypothesis_packet,
    validate_creative_workflow_request,
    validate_creative_workflow_native_result,
    validate_creative_workflow_review,
    validate_creative_workflow_handoff,
    validate_creative_workflow_stage,
    workflow_fingerprint,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
SHA256 = "sha256:" + ("c" * 64)
SCHEMA_FILES = {
    "experiment_runner_pr_oracle_attachment.v1.schema.json": (
        ORACLE_ATTACHMENT_TYPE,
        POLICY_VERSION,
    ),
    "creative_protocol_context_map.v1.schema.json": (CONTEXT_MAP_TYPE, POLICY_VERSION),
    "creative_hypothesis_packet.v1.schema.json": (HYPOTHESIS_PACKET_TYPE, POLICY_VERSION),
    "creative_hypothesis_agent_routing.v1.schema.json": (AGENT_ROUTING_TYPE, POLICY_VERSION),
    "creative_hypothesis_agent_consumption_summary.v1.schema.json": (
        CONSUMPTION_SUMMARY_TYPE,
        POLICY_VERSION,
    ),
    "creative_hypothesis_approval.v1.schema.json": (APPROVAL_TYPE, POLICY_VERSION),
    "creative_hypothesis_operator_model_intake.v1.schema.json": (
        OPERATOR_MODEL_INTAKE_TYPE,
        OPERATOR_MODEL_INTAKE_POLICY_VERSION,
    ),
    "creative_hypothesis_coordinator_dispatch.v1.schema.json": (
        COORDINATOR_DISPATCH_TYPE,
        COORDINATOR_DISPATCH_POLICY_VERSION,
    ),
}


def _schema(filename: str) -> dict[str, object]:
    schema_path = REPO_ROOT / "docs" / "orchestration" / "contracts" / filename
    return json.loads(schema_path.read_text(encoding="utf-8"))


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


def _operator_model_intake(
    context: dict[str, object],
    *,
    hypothesis_count: int = 4,
) -> dict[str, object]:
    packet = build_creative_hypothesis_packet(context, hypothesis_count=hypothesis_count)
    hypotheses = [
        {key: value for key, value in row.items() if key != "hypothesis_id"}
        for row in packet["hypotheses"]
    ]
    body: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": OPERATOR_MODEL_INTAKE_TYPE,
        "policy_version": OPERATOR_MODEL_INTAKE_POLICY_VERSION,
        "context_map_id": context["context_id"],
        "context_map_fingerprint": fingerprint_payload(context),
        "generation": {
            "mode": "operator_supplied_model_json",
            "tool_label": "codex",
            "repo_provider_calls": False,
            "raw_model_payload_stored": False,
            "semantic_cache_used": False,
        },
        "hypothesis_count": hypothesis_count,
        "hypotheses": hypotheses,
        "authority": default_operator_model_intake_authority(),
        "sanitized": True,
    }
    intake_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=OPERATOR_MODEL_INTAKE_TYPE,
        upstream_ids=(str(context["context_id"]),),
        policy_version=OPERATOR_MODEL_INTAKE_POLICY_VERSION,
    )
    return {
        **body,
        "intake_id": intake_id,
        "idempotency_key": idempotency_key,
    }


def _refresh_operator_model_intake_identity(intake: dict[str, object]) -> dict[str, object]:
    body = {
        key: value for key, value in intake.items() if key not in {"intake_id", "idempotency_key"}
    }
    intake_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=OPERATOR_MODEL_INTAKE_TYPE,
        upstream_ids=(str(intake["context_map_id"]),),
        policy_version=OPERATOR_MODEL_INTAKE_POLICY_VERSION,
    )
    intake["intake_id"] = intake_id
    intake["idempotency_key"] = idempotency_key
    return intake


def _refresh_agent_routing_identity(routing: dict[str, object]) -> dict[str, object]:
    body = {
        key: value for key, value in routing.items() if key not in {"routing_id", "idempotency_key"}
    }
    routing_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=AGENT_ROUTING_TYPE,
        upstream_ids=(str(routing["source_hypothesis_packet_id"]),),
    )
    routing["routing_id"] = routing_id
    routing["idempotency_key"] = idempotency_key
    return routing


def test_valid_artifact_chain_enforces_creative_authority_boundary() -> None:
    context = _context()
    packet = build_creative_hypothesis_packet(context, hypothesis_count=4)
    routing = build_creative_hypothesis_agent_routing(packet)
    dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=packet,
        routing=routing,
    )
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
        hypothesis_packet=packet,
        approved_target_surfaces=packet["hypotheses"][0]["target_surfaces"],
        approved_agents=[routing["routing"][0]["primary_agent"]],
        next_step="create_pr1_specification",
    )

    assert packet["creative_status"] == "hypotheses_generated"
    assert packet["hypothesis_count"] == 4
    assert dispatch["dispatch"][0]["task_packet_kind"] == "TASK_PACKET_V1"
    assert dispatch["dispatch"][0]["task_mode"] == "critique_refine_only"
    assert dispatch["dispatch"][0]["mutation_authority"] is False
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
    validated_dispatch = validate_artifact_by_type(COORDINATOR_DISPATCH_TYPE, dispatch)
    assert validated_dispatch["authority"] == default_coordinator_dispatch_authority()
    assert all(
        validated_dispatch["authority"][key] is True
        for key in COORDINATOR_DISPATCH_AUTHORITY_TRUE_KEYS
    )
    assert all(
        validated_dispatch["authority"][key] is False
        for key in COORDINATOR_DISPATCH_AUTHORITY_FALSE_KEYS
    )


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


def test_valid_model_intake_normalizes_to_hypothesis_packet_and_dispatch() -> None:
    context = _context()
    intake = _operator_model_intake(context, hypothesis_count=4)

    validated_intake = validate_creative_hypothesis_operator_model_intake(
        intake,
        context_map=context,
    )
    assert validated_intake["authority"] == default_operator_model_intake_authority()
    assert all(validated_intake["authority"][key] is True for key in INTAKE_AUTHORITY_TRUE_KEYS)
    assert all(validated_intake["authority"][key] is False for key in INTAKE_AUTHORITY_FALSE_KEYS)
    assert all("hypothesis_id" not in row for row in validated_intake["hypotheses"])

    packet = build_creative_hypothesis_packet_from_model_intake(context, intake)
    routing = build_creative_hypothesis_agent_routing(packet)
    dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=packet,
        routing=routing,
    )

    assert packet["hypothesis_generation_mode"] == "operator_validated_intake_v1"
    assert packet["source_model_intake_fingerprint"] == fingerprint_payload(validated_intake)
    assert packet["repo_provider_calls"] is False
    assert packet["raw_model_payload_stored"] is False
    assert packet["semantic_cache_used"] is False
    assert [row["hypothesis_id"] for row in packet["hypotheses"]] == [
        "hyp-001",
        "hyp-002",
        "hyp-003",
        "hyp-004",
    ]
    assert all(row["task_mode"] == "critique_refine_only" for row in dispatch["dispatch"])
    assert all(row["mutation_authority"] is False for row in dispatch["dispatch"])


def test_coordinator_dispatch_rejects_empty_dispatch_entries() -> None:
    context = _context()
    packet = build_creative_hypothesis_packet(context, hypothesis_count=3)
    routing = build_creative_hypothesis_agent_routing(packet)
    dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=packet,
        routing=routing,
    )
    dispatch["dispatch"] = []
    dispatch_id, idempotency_key = _artifact_identity(
        {
            key: value
            for key, value in dispatch.items()
            if key not in {"dispatch_id", "idempotency_key"}
        },
        artifact_type=COORDINATOR_DISPATCH_TYPE,
        upstream_ids=(str(packet["packet_id"]),),
        policy_version=COORDINATOR_DISPATCH_POLICY_VERSION,
    )
    dispatch["dispatch_id"] = dispatch_id
    dispatch["idempotency_key"] = idempotency_key

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="at least one dispatch entry",
    ):
        validate_creative_hypothesis_coordinator_dispatch(dispatch)


def test_model_intake_derives_repo_identity_when_operator_omits_it() -> None:
    context = _context()
    intake = _operator_model_intake(context, hypothesis_count=4)
    intake.pop("intake_id")
    intake.pop("idempotency_key")

    validated_intake = validate_creative_hypothesis_operator_model_intake(
        intake,
        context_map=context,
    )
    body_without_identity = {
        key: value
        for key, value in validated_intake.items()
        if key not in {"intake_id", "idempotency_key"}
    }
    expected_intake_id, expected_idempotency_key = _artifact_identity(
        body_without_identity,
        artifact_type=OPERATOR_MODEL_INTAKE_TYPE,
        upstream_ids=(str(context["context_id"]),),
        policy_version=OPERATOR_MODEL_INTAKE_POLICY_VERSION,
    )

    assert validated_intake["intake_id"] == expected_intake_id
    assert validated_intake["idempotency_key"] == expected_idempotency_key


def test_model_intake_overwrites_supplied_identity_with_repo_identity() -> None:
    context = _context()
    intake = _operator_model_intake(context, hypothesis_count=4)
    intake["intake_id"] = "operator-supplied-id"
    intake["idempotency_key"] = "operator-supplied-key"

    validated_intake = validate_creative_hypothesis_operator_model_intake(
        intake,
        context_map=context,
    )
    body_without_identity = {
        key: value
        for key, value in validated_intake.items()
        if key not in {"intake_id", "idempotency_key"}
    }
    expected_intake_id, expected_idempotency_key = _artifact_identity(
        body_without_identity,
        artifact_type=OPERATOR_MODEL_INTAKE_TYPE,
        upstream_ids=(str(context["context_id"]),),
        policy_version=OPERATOR_MODEL_INTAKE_POLICY_VERSION,
    )

    assert validated_intake["intake_id"] == expected_intake_id
    assert validated_intake["idempotency_key"] == expected_idempotency_key


def test_model_intake_derives_hypothesis_count_when_operator_omits_it() -> None:
    context = _context()
    intake = _operator_model_intake(context, hypothesis_count=3)
    intake.pop("hypothesis_count")

    validated_intake = validate_creative_hypothesis_operator_model_intake(
        intake,
        context_map=context,
    )
    packet = build_creative_hypothesis_packet_from_model_intake(context, intake)

    assert validated_intake["hypothesis_count"] == 3
    assert packet["hypothesis_count"] == 3
    assert packet["source_model_intake_fingerprint"] == fingerprint_payload(validated_intake)


def test_model_intake_accepts_schema_safe_text_limit_at_runtime() -> None:
    context = _context()
    intake = _operator_model_intake(context, hypothesis_count=3)
    intake["hypotheses"][0]["title"] = "T" * 300
    intake["hypotheses"][0]["risk_notes"] = ["R" * 300]
    _refresh_operator_model_intake_identity(intake)

    validated = validate_creative_hypothesis_operator_model_intake(intake, context_map=context)

    assert validated["hypotheses"][0]["title"] == "T" * 300
    assert validated["hypotheses"][0]["risk_notes"] == ["R" * 300]


def test_model_intake_requires_context_fingerprint_match() -> None:
    context = _context()
    intake = _operator_model_intake(context)
    intake["context_map_fingerprint"] = "sha256:" + ("d" * 64)

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="context_map_fingerprint must match context map",
    ):
        validate_creative_hypothesis_operator_model_intake(intake, context_map=context)


@pytest.mark.parametrize("hypothesis_count", [1, 2, 6])
def test_model_intake_requires_three_to_five_hypotheses(hypothesis_count: int) -> None:
    context = _context()
    intake = _operator_model_intake(context, hypothesis_count=5)
    intake["hypothesis_count"] = hypothesis_count
    intake["hypotheses"] = list(intake["hypotheses"])[:hypothesis_count]
    if hypothesis_count == 6:
        intake["hypotheses"] = [
            *intake["hypotheses"],
            deepcopy(intake["hypotheses"][0]),
        ]

    with pytest.raises(ExperimentRunnerCreativeContextContractError):
        validate_creative_hypothesis_operator_model_intake(intake, context_map=context)


def test_model_intake_rejects_count_mismatch() -> None:
    context = _context()
    intake = _operator_model_intake(context, hypothesis_count=4)
    intake["hypothesis_count"] = 3

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="hypothesis_count must match hypotheses",
    ):
        validate_creative_hypothesis_operator_model_intake(intake, context_map=context)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda payload: payload["hypotheses"][0].update({"hypothesis_id": "external-id"}),
        lambda payload: payload["hypotheses"][0].update({"target_surfaces": []}),
        lambda payload: payload["hypotheses"][0].update(
            {"target_surfaces": ["docs/orchestration/README.md"]}
        ),
        lambda payload: payload["hypotheses"][0].update({"tests_or_oracles": []}),
        lambda payload: payload["hypotheses"][0].update({"risk_notes": []}),
        lambda payload: payload["hypotheses"][0].update({"cross_domain_analogies": []}),
        lambda payload: payload["hypotheses"][0].update({"falsifier": ""}),
        lambda payload: payload["hypotheses"][0].update({"negative_controls": []}),
    ],
)
def test_model_intake_rejects_missing_quality_fields(
    mutator: Callable[[dict[str, Any]], object],
) -> None:
    context = _context()
    intake = _operator_model_intake(context)
    mutator(intake)

    with pytest.raises(ExperimentRunnerCreativeContextContractError):
        validate_creative_hypothesis_operator_model_intake(intake, context_map=context)


def test_model_intake_rejects_pr2_patch_eligibility() -> None:
    context = _context()
    intake = _operator_model_intake(context)
    intake["hypotheses"][0]["eligible_for_pr2_patch"] = True

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="eligible_for_pr2_patch must be False",
    ):
        validate_creative_hypothesis_operator_model_intake(intake, context_map=context)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda payload: payload.update({"raw_prompt": "make a patch"}),
        lambda payload: payload["generation"].update({"tool_label": "remote_provider"}),
        lambda payload: payload["generation"].update({"repo_provider_calls": True}),
        lambda payload: payload["generation"].update({"raw_model_payload_stored": True}),
        lambda payload: payload["generation"].update({"semantic_cache_used": True}),
        lambda payload: payload["hypotheses"][0].update(
            {"title": "diff --git a/app/main.py b/app/main.py"}
        ),
        lambda payload: payload["hypotheses"][0].update(
            {"expected_behavior": "raw model payload includes provider response"}
        ),
        lambda payload: payload["hypotheses"][0].update(
            {"expected_behavior": "raw.prompt includes provider response"}
        ),
        lambda payload: payload["hypotheses"][0].update(
            {"risk_notes": ["provider.payload included"]}
        ),
        lambda payload: payload["hypotheses"][0].update({"falsifier": "chain.of.thought included"}),
        lambda payload: payload["hypotheses"][0].update({"falsifier": "@@ -1 +1 @@ patch hunk"}),
        lambda payload: payload["hypotheses"][0].update(
            {"target_surfaces": ["/Users/example/repo/file.py"]}
        ),
        lambda payload: payload["authority"].update({"workflow_dispatch": True}),
        lambda payload: payload["authority"].update({"modify_github_app": True}),
        lambda payload: payload["authority"].update({"repo_provider_calls": True}),
    ],
)
def test_model_intake_rejects_unsafe_payload_or_authority(
    mutator: Callable[[dict[str, Any]], object],
) -> None:
    context = _context()
    intake = _operator_model_intake(context)
    mutator(intake)

    with pytest.raises(ExperimentRunnerCreativeContextContractError):
        validate_creative_hypothesis_operator_model_intake(intake, context_map=context)


@pytest.mark.parametrize(
    "forbidden_target",
    [
        ".",
        "app",
        "app/main.py",
        "core",
        "frontend",
        ".github/workflows",
        ".github/workflows/ci.yml",
    ],
)
def test_model_intake_rejects_mixed_product_runtime_or_workflow_targets(
    forbidden_target: str,
) -> None:
    context = _context()
    intake = _operator_model_intake(context)
    intake["hypotheses"][0]["target_surfaces"] = [
        forbidden_target,
        "scripts/orchestration/experiment_runner_pr_creative_context.py",
    ]

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="must not include product runtime or workflow targets|bounded repo-relative path",
    ):
        validate_creative_hypothesis_operator_model_intake(intake, context_map=context)


def test_model_intake_rejects_nonconcrete_repo_root_with_valid_target() -> None:
    context = _context()
    intake = _operator_model_intake(context)
    intake["hypotheses"][0]["target_surfaces"] = [
        "docs/orchestration/README.md",
        "scripts/orchestration/experiment_runner_pr_creative_context.py",
    ]

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="target_surfaces must all be concrete",
    ):
        validate_creative_hypothesis_operator_model_intake(intake, context_map=context)


@pytest.mark.parametrize(
    "forbidden_oracle",
    ["app/main.py", ".github/workflows/ci.yml"],
)
def test_model_intake_rejects_product_runtime_or_workflow_tests_or_oracles(
    forbidden_oracle: str,
) -> None:
    context = _context()
    intake = _operator_model_intake(context)
    intake["hypotheses"][0]["tests_or_oracles"] = [
        forbidden_oracle,
        "tests/test_experiment_runner_pr_creative_context.py",
    ]

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="must not include product runtime or workflow targets",
    ):
        validate_creative_hypothesis_operator_model_intake(intake, context_map=context)


@pytest.mark.parametrize(
    "forbidden_target",
    ["core/nutrition.py", ".github/workflows/security.yml"],
)
def test_model_intake_rejects_cross_domain_analogy_runtime_targets(
    forbidden_target: str,
) -> None:
    context = _context()
    intake = _operator_model_intake(context)
    intake["hypotheses"][0]["cross_domain_analogies"][0]["target_repo_surface"] = forbidden_target

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="must not include product runtime or workflow targets",
    ):
        validate_creative_hypothesis_operator_model_intake(intake, context_map=context)


def test_operator_mode_packet_requires_generated_status() -> None:
    no_action_context = _context(changed_paths=["docs/README.md"])
    packet = build_creative_hypothesis_packet(no_action_context)
    packet["hypothesis_generation_mode"] = "operator_validated_intake_v1"
    packet["source_model_intake_fingerprint"] = SHA256

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="operator_validated_intake_v1 packets require hypotheses_generated",
    ):
        validate_creative_hypothesis_packet(packet)


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


def test_accepted_oracle_attachment_requires_fingerprint() -> None:
    context = _context()

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="accepted oracle attachments require result_fingerprint",
    ):
        build_experiment_runner_pr_oracle_attachment(
            source=context["source"],
            oracle_status="accepted",
            result_ref="artifacts/orchestration/experiments/results/oracle-result.json",
            result_fingerprint=None,
        )


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


def test_cross_domain_analogy_routes_registered_specialist_agent() -> None:
    context = _context()
    intake = _operator_model_intake(context, hypothesis_count=3)
    intake["hypotheses"][0]["cross_domain_analogies"][0]["source_domain"] = "nutrition"
    _refresh_operator_model_intake_identity(intake)
    packet = build_creative_hypothesis_packet_from_model_intake(context, intake)
    registered_agents = {
        "agent-coordinator",
        "architecture-specialist",
        "security-auditor",
        "qa-engineer-agent",
        "nutritionist-agent",
    }

    routing = build_creative_hypothesis_agent_routing(
        packet,
        registered_agents=registered_agents,
    )

    architecture_route = routing["routing"][0]
    assert architecture_route["hypothesis_id"] == "hyp-001"
    assert "nutritionist-agent" in architecture_route["cross_domain_agents"]
    assert "nutritionist-agent" not in architecture_route["missing_agent_capabilities"]
    assert "wellness-analyst-agent" not in architecture_route["missing_agent_capabilities"]


def test_cross_domain_analogy_records_missing_specialist_capability() -> None:
    context = _context()
    intake = _operator_model_intake(context, hypothesis_count=3)
    intake["hypotheses"][0]["cross_domain_analogies"][0]["source_domain"] = "nutrition"
    _refresh_operator_model_intake_identity(intake)
    packet = build_creative_hypothesis_packet_from_model_intake(context, intake)
    registered_agents = {
        "agent-coordinator",
        "architecture-specialist",
        "security-auditor",
        "qa-engineer-agent",
    }

    routing = build_creative_hypothesis_agent_routing(
        packet,
        registered_agents=registered_agents,
    )

    architecture_route = routing["routing"][0]
    assert "nutritionist-agent" in architecture_route["missing_agent_capabilities"]
    assert "wellness-analyst-agent" in architecture_route["missing_agent_capabilities"]


def test_economics_analogy_routes_to_canonical_business_specialist() -> None:
    context = _context()
    intake = _operator_model_intake(context, hypothesis_count=3)
    intake["hypotheses"][0]["cross_domain_analogies"][0]["source_domain"] = "economics"
    _refresh_operator_model_intake_identity(intake)
    packet = build_creative_hypothesis_packet_from_model_intake(context, intake)
    registered_agents = {
        "agent-coordinator",
        "architecture-specialist",
        "security-auditor",
        "qa-engineer-agent",
        "business-strategist-agent",
    }

    routing = build_creative_hypothesis_agent_routing(
        packet,
        registered_agents=registered_agents,
    )

    architecture_route = routing["routing"][0]
    assert "business-strategist-agent" in architecture_route["cross_domain_agents"]
    assert "business-analyst-agent" not in architecture_route["missing_agent_capabilities"]


def test_coordinator_dispatch_preserves_critique_refine_only_routing() -> None:
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

    dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=packet,
        routing=routing,
        registered_agents=registered_agents,
    )
    validated_dispatch = validate_creative_hypothesis_coordinator_dispatch(
        dispatch,
        registered_agents=registered_agents,
    )

    assert dispatch["source_hypothesis_packet_id"] == packet["packet_id"]
    assert {row["hypothesis_id"] for row in validated_dispatch["dispatch"]} == {
        row["hypothesis_id"] for row in packet["hypotheses"]
    }
    architecture = dispatch["dispatch"][0]
    security = dispatch["dispatch"][1]
    testing = dispatch["dispatch"][2]
    scientific = dispatch["dispatch"][4]
    assert architecture["primary_agent"] == "architecture-specialist"
    assert set(architecture["review_agents"]) == {"qa-engineer-agent", "security-auditor"}
    assert security["primary_agent"] == "security-auditor"
    assert set(security["review_agents"]) == {"architecture-specialist", "bug-hunter"}
    assert testing["primary_agent"] == "qa-engineer-agent"
    assert set(testing["review_agents"]) == {"bug-hunter", "logic-agent"}
    assert scientific["primary_agent"] == "data-scientist-agent"
    assert "experiment-design-stats-agent" in scientific["missing_agent_capabilities"]
    assert all(row["task_packet_kind"] == "TASK_PACKET_V1" for row in dispatch["dispatch"])
    assert all(row["task_mode"] == "critique_refine_only" for row in dispatch["dispatch"])
    assert all(row["mutation_authority"] is False for row in dispatch["dispatch"])
    assert dispatch["authority"] == default_coordinator_dispatch_authority()


def test_coordinator_dispatch_rejects_unrelated_routing_packet() -> None:
    packet = _packet(hypothesis_count=3)
    other_context = _context(
        changed_paths=[
            "scripts/orchestration/task_bootstrap.py",
            "docs/orchestration/contracts/EXPERIMENT_RUNNER_PR_CREATIVE_CONTEXT_CONTRACT.md",
        ],
    )
    other_packet = build_creative_hypothesis_packet(other_context, hypothesis_count=3)
    other_routing = build_creative_hypothesis_agent_routing(other_packet)

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="coordinator dispatch routing must reference",
    ):
        build_creative_hypothesis_coordinator_dispatch(
            hypothesis_packet=packet,
            routing=other_routing,
        )


def test_coordinator_dispatch_rejects_stale_routing_fingerprint() -> None:
    packet = _packet(hypothesis_count=3)
    routing = build_creative_hypothesis_agent_routing(packet)
    bad_routing = dict(routing)
    bad_routing["source_hypothesis_packet_fingerprint"] = SHA256
    _refresh_agent_routing_identity(bad_routing)

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="coordinator dispatch routing fingerprint must match",
    ):
        build_creative_hypothesis_coordinator_dispatch(
            hypothesis_packet=packet,
            routing=bad_routing,
        )


def test_coordinator_dispatch_rejects_missing_routing_rows() -> None:
    packet = _packet(hypothesis_count=3)
    routing = build_creative_hypothesis_agent_routing(packet)
    bad_routing = dict(routing)
    bad_routing["routing"] = []
    _refresh_agent_routing_identity(bad_routing)

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="coordinator dispatch rows must match hypothesis packet rows",
    ):
        build_creative_hypothesis_coordinator_dispatch(
            hypothesis_packet=packet,
            routing=bad_routing,
        )


def test_routing_rejects_malformed_missing_agent_capability_slug() -> None:
    packet = _packet(hypothesis_count=3)
    routing = build_creative_hypothesis_agent_routing(packet)
    routing["routing"][0]["missing_agent_capabilities"] = ["not an agent slug"]

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="agent slug",
    ):
        validate_creative_hypothesis_agent_routing(routing)


def test_coordinator_dispatch_rejects_malformed_missing_agent_capability_slug() -> None:
    packet = _packet(hypothesis_count=3)
    routing = build_creative_hypothesis_agent_routing(packet)
    dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=packet,
        routing=routing,
    )
    dispatch["dispatch"][0]["missing_agent_capabilities"] = ["Bad.Agent"]

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="agent slug",
    ):
        validate_creative_hypothesis_coordinator_dispatch(dispatch)


def test_consumption_summary_rejects_unrelated_routing_packet() -> None:
    packet = _packet(hypothesis_count=3)
    other_context = _context(
        changed_paths=[
            "scripts/orchestration/task_bootstrap.py",
            "docs/orchestration/contracts/EXPERIMENT_RUNNER_PR_CREATIVE_CONTEXT_CONTRACT.md",
        ],
    )
    other_packet = build_creative_hypothesis_packet(other_context, hypothesis_count=3)
    other_routing = build_creative_hypothesis_agent_routing(other_packet)

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="agent routing must reference the supplied hypothesis packet",
    ):
        build_agent_consumption_summary(hypothesis_packet=packet, routing=other_routing)


def test_consumption_summary_rejects_missing_routing_rows_for_generated_packet() -> None:
    packet = _packet(hypothesis_count=3)
    routing = build_creative_hypothesis_agent_routing(packet)
    bad_routing = dict(routing)
    bad_routing["routing"] = []
    body_without_identity = {
        key: value
        for key, value in bad_routing.items()
        if key not in {"routing_id", "idempotency_key"}
    }
    routing_id, idempotency_key = _artifact_identity(
        body_without_identity,
        artifact_type=AGENT_ROUTING_TYPE,
        upstream_ids=(packet["packet_id"],),
    )
    bad_routing["routing_id"] = routing_id
    bad_routing["idempotency_key"] = idempotency_key

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="agent routing rows must match hypothesis packet rows",
    ):
        build_agent_consumption_summary(hypothesis_packet=packet, routing=bad_routing)


def test_approval_rejects_rejected_or_deferred_pr1_handoff() -> None:
    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="only approve_for_pr1_specification may create PR-1 specification",
    ):
        build_creative_hypothesis_approval(
            hypothesis_id="hyp-001",
            decision="reject",
            next_step="create_pr1_specification",
        )

    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="deferred approvals must set defer",
    ):
        build_creative_hypothesis_approval(
            hypothesis_id="hyp-001",
            decision="defer",
            next_step="no_action",
        )


def test_approval_requires_packet_binding_for_pr1_handoff() -> None:
    packet = _packet()
    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="PR-1 approval requires source hypothesis packet and hypothesis fingerprint binding",
    ):
        build_creative_hypothesis_approval(
            hypothesis_id=packet["hypotheses"][0]["hypothesis_id"],
            decision="approve_for_pr1_specification",
            approved_target_surfaces=packet["hypotheses"][0]["target_surfaces"],
            approved_agents=["orchestration-architect"],
            next_step="create_pr1_specification",
        )


def test_approval_rejects_product_runtime_pr1_targets() -> None:
    with pytest.raises(
        ExperimentRunnerCreativeContextContractError,
        match="PR-1 approval targets must stay on creative-context orchestration surfaces",
    ):
        build_creative_hypothesis_approval(
            hypothesis_id="hyp-001",
            decision="approve_for_pr1_specification",
            hypothesis_packet=_packet(),
            approved_target_surfaces=["app/main.py"],
            next_step="create_pr1_specification",
        )


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
        "coordinator_dispatch.json",
        "hypothesis_packet.json",
        "oracle_attachment.json",
    ]
    for name in observed:
        payload = read_json_object(creative_root / "lane" / name)
        assert payload["sanitized"] is True


def test_cli_prepare_with_model_intake_reuses_supplied_context_map(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    creative_root = tmp_path / "creative_context"
    monkeypatch.setattr(cli, "CREATIVE_CONTEXT_ROOT", creative_root)
    context = _context()
    intake = _operator_model_intake(context, hypothesis_count=3)
    context_path = tmp_path / "context_map.json"
    intake_path = tmp_path / "model_intake.json"
    context_path.write_text(json.dumps(context), encoding="utf-8")
    intake_path.write_text(json.dumps(intake), encoding="utf-8")

    exit_code = cli.main(
        [
            "prepare",
            "--context-map",
            str(context_path),
            "--model-intake",
            str(intake_path),
            "--output-dir",
            "operator-lane",
        ]
    )

    assert exit_code == 0
    written_context = read_json_object(creative_root / "operator-lane" / "context_map.json")
    packet = read_json_object(creative_root / "operator-lane" / "hypothesis_packet.json")
    dispatch = read_json_object(creative_root / "operator-lane" / "coordinator_dispatch.json")
    assert written_context["context_id"] == context["context_id"]
    assert packet["hypothesis_generation_mode"] == "operator_validated_intake_v1"
    normalized_intake = read_json_object(creative_root / "operator-lane" / "model_intake.json")
    assert packet["context_map_fingerprint"] == fingerprint_payload(context)
    assert normalized_intake == validate_creative_hypothesis_operator_model_intake(
        intake,
        context_map=context,
    )
    assert packet["source_model_intake_fingerprint"] == fingerprint_payload(normalized_intake)
    assert all(row["task_mode"] == "critique_refine_only" for row in dispatch["dispatch"])


def test_cli_ingest_model_hypotheses_writes_normalized_packet(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    creative_root = tmp_path / "creative_context"
    monkeypatch.setattr(cli, "CREATIVE_CONTEXT_ROOT", creative_root)
    context = _context()
    intake = _operator_model_intake(context, hypothesis_count=3)
    context_path = tmp_path / "context_map.json"
    intake_path = tmp_path / "model_intake.json"
    context_path.write_text(json.dumps(context), encoding="utf-8")
    intake_path.write_text(json.dumps(intake), encoding="utf-8")

    exit_code = cli.main(
        [
            "ingest-model-hypotheses",
            "--context-map",
            str(context_path),
            "--model-intake",
            str(intake_path),
            "--output",
            "hypothesis_packet.json",
        ]
    )

    assert exit_code == 0
    packet = read_json_object(creative_root / "hypothesis_packet.json")
    assert packet["hypothesis_generation_mode"] == "operator_validated_intake_v1"
    assert packet["hypothesis_count"] == 3
    normalized_intake = read_json_object(creative_root / "model_intake.json")
    assert packet["source_model_intake_fingerprint"] == fingerprint_payload(normalized_intake)
    assert [row["hypothesis_id"] for row in packet["hypotheses"]] == [
        "hyp-001",
        "hyp-002",
        "hyp-003",
    ]


def test_cli_dispatch_coordinator_writes_handoff(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    creative_root = tmp_path / "creative_context"
    monkeypatch.setattr(cli, "CREATIVE_CONTEXT_ROOT", creative_root)
    packet = _packet(hypothesis_count=3)
    routing = build_creative_hypothesis_agent_routing(packet)
    packet_path = tmp_path / "hypothesis_packet.json"
    routing_path = tmp_path / "agent_routing.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    routing_path.write_text(json.dumps(routing), encoding="utf-8")

    exit_code = cli.main(
        [
            "dispatch-coordinator",
            "--hypothesis-packet",
            str(packet_path),
            "--routing",
            str(routing_path),
            "--output",
            "coordinator_dispatch.json",
        ]
    )

    assert exit_code == 0
    dispatch = read_json_object(creative_root / "coordinator_dispatch.json")
    assert dispatch["artifact_type"] == COORDINATOR_DISPATCH_TYPE
    assert all(row["task_mode"] == "critique_refine_only" for row in dispatch["dispatch"])


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
    for filename, (artifact_type, policy_version) in SCHEMA_FILES.items():
        schema = _schema(filename)
        assert schema["additionalProperties"] is False
        assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION
        assert schema["properties"]["artifact_type"]["const"] == artifact_type
        assert schema["properties"]["policy_version"]["const"] == policy_version
        assert schema["properties"]["sanitized"]["const"] is True


def test_schema_authority_definitions_match_runtime_authority() -> None:
    authority_cases = [
        (
            filename,
            "authority",
            AUTHORITY_KEYS,
            AUTHORITY_TRUE_KEYS,
            AUTHORITY_FALSE_KEYS,
        )
        for filename in SCHEMA_FILES
        if filename
        not in {
            "creative_hypothesis_operator_model_intake.v1.schema.json",
            "creative_hypothesis_coordinator_dispatch.v1.schema.json",
        }
    ]
    authority_cases.extend(
        [
            (
                "creative_hypothesis_operator_model_intake.v1.schema.json",
                "intake_authority",
                INTAKE_AUTHORITY_KEYS,
                INTAKE_AUTHORITY_TRUE_KEYS,
                INTAKE_AUTHORITY_FALSE_KEYS,
            ),
            (
                "creative_hypothesis_coordinator_dispatch.v1.schema.json",
                "dispatch_authority",
                COORDINATOR_DISPATCH_AUTHORITY_KEYS,
                COORDINATOR_DISPATCH_AUTHORITY_TRUE_KEYS,
                COORDINATOR_DISPATCH_AUTHORITY_FALSE_KEYS,
            ),
        ]
    )
    for filename, authority_def, authority_keys, true_keys, false_keys in authority_cases:
        authority = _schema(filename)["$defs"][authority_def]
        assert authority["additionalProperties"] is False
        assert set(authority["required"]) == authority_keys
        assert set(authority["properties"]) == authority_keys
        for key in true_keys:
            assert authority["properties"][key]["const"] is True
        for key in false_keys:
            assert authority["properties"][key]["const"] is False


def test_hypothesis_packet_schema_encodes_generated_and_no_action_guards() -> None:
    schema = _schema("creative_hypothesis_packet.v1.schema.json")
    generated_guard = next(
        guard
        for guard in schema["allOf"]
        if guard["if"]["properties"].get("creative_status", {}).get("const")
        == "hypotheses_generated"
    )
    no_action_guard = next(
        guard
        for guard in schema["allOf"]
        if guard["if"]["properties"].get("creative_status", {}).get("const") == "no_creative_action"
    )
    operator_guard = next(
        guard
        for guard in schema["allOf"]
        if guard["if"]["properties"].get("hypothesis_generation_mode", {}).get("const")
        == "operator_validated_intake_v1"
    )
    deterministic_guard = next(
        guard
        for guard in schema["allOf"]
        if guard["if"]["properties"].get("hypothesis_generation_mode", {}).get("const")
        == "deterministic_templates_v1"
    )

    generated_then = generated_guard["then"]["properties"]
    assert generated_then["hypothesis_count"]["enum"] == [3, 4, 5]
    assert generated_then["hypotheses"]["minItems"] == 3
    assert generated_then["hypotheses"]["maxItems"] == 5
    contains_target = generated_then["hypotheses"]["contains"]["properties"]["target_surfaces"]
    assert contains_target["contains"]["$ref"] == "#/$defs/concrete_target_path"
    assert no_action_guard["then"]["properties"]["hypothesis_count"]["const"] == 0
    assert no_action_guard["then"]["properties"]["hypotheses"]["maxItems"] == 0
    assert (
        operator_guard["then"]["properties"]["source_model_intake_fingerprint"]["$ref"]
        == "#/$defs/sha256"
    )
    assert (
        operator_guard["then"]["properties"]["creative_status"]["const"] == "hypotheses_generated"
    )
    assert operator_guard["then"]["properties"]["hypothesis_count"]["enum"] == [3, 4, 5]
    assert operator_guard["then"]["properties"]["hypotheses"]["minItems"] == 3
    assert operator_guard["then"]["properties"]["hypotheses"]["maxItems"] == 5
    assert (
        deterministic_guard["then"]["properties"]["source_model_intake_fingerprint"]["type"]
        == "null"
    )


def test_operator_model_intake_schema_enforces_local_sanitized_shape() -> None:
    schema = _schema("creative_hypothesis_operator_model_intake.v1.schema.json")
    hypothesis = schema["$defs"]["operator_hypothesis"]
    generation = schema["$defs"]["generation"]
    repo_path_not_pattern = schema["$defs"]["repo_path"]["not"]["pattern"]
    unsafe_text_patterns = [row["pattern"] for row in schema["$defs"]["safe_text"]["not"]["anyOf"]]

    assert "intake_id" not in schema["required"]
    assert "idempotency_key" not in schema["required"]
    assert "hypothesis_count" not in schema["required"]
    assert "hypothesis_id" not in hypothesis["properties"]
    assert "hypothesis_id" not in hypothesis["required"]
    assert "^(app|core|frontend|ios|providers|alembic)(/|$)" in repo_path_not_pattern
    assert "^\\.github/workflows(/|$)" in repo_path_not_pattern
    assert "^\\.$" in repo_path_not_pattern
    assert hypothesis["properties"]["target_surfaces"]["items"]["$ref"] == (
        "#/$defs/concrete_target_path"
    )
    assert schema["properties"]["hypothesis_count"]["minimum"] == 3
    assert schema["properties"]["hypothesis_count"]["maximum"] == 5
    assert schema["properties"]["hypotheses"]["minItems"] == 3
    assert schema["properties"]["hypotheses"]["maxItems"] == 5
    assert generation["properties"]["repo_provider_calls"]["const"] is False
    assert generation["properties"]["raw_model_payload_stored"]["const"] is False
    assert generation["properties"]["semantic_cache_used"]["const"] is False
    for unsafe_value in (
        "DIFF --GIT a/app/main.py b/app/main.py",
        "@@ -1 +1 @@",
        "--- a/app/main.py",
        "+++ b/app/main.py",
        "raw model payload included",
        "raw.prompt included",
        "Provider_Payload included",
        "provider.payload included",
        "chain.of.thought included",
        "/Users/example/repo/file.py",
        "github_token",
    ):
        # These regexes are loaded from repo-owned schema JSON, not from
        # attacker-controlled input, so schema parity checks may execute them.
        assert any(re.search(pattern, unsafe_value) for pattern in unsafe_text_patterns)

    assert (
        _schema("creative_hypothesis_agent_routing.v1.schema.json")["$defs"]["agent_slug"][
            "pattern"
        ]
        == "^[a-z][a-z0-9-]{1,63}$"
    )
    assert (
        _schema("creative_hypothesis_coordinator_dispatch.v1.schema.json")["$defs"]["agent_slug"][
            "pattern"
        ]
        == "^[a-z][a-z0-9-]{1,63}$"
    )


def test_coordinator_dispatch_schema_requires_at_least_one_dispatch_entry() -> None:
    schema = _schema("creative_hypothesis_coordinator_dispatch.v1.schema.json")

    assert schema["properties"]["dispatch"]["minItems"] == 1


def test_hypothesis_packet_schema_rejects_unsafe_text_classes() -> None:
    schema = _schema("creative_hypothesis_packet.v1.schema.json")
    unsafe_text_patterns = [row["pattern"] for row in schema["$defs"]["safe_text"]["not"]["anyOf"]]

    for unsafe_value in (
        "DIFF --GIT a/app/main.py b/app/main.py",
        "Provider_Payload included",
        "/Users/example/repo/file.py",
        "github_token",
    ):
        # These regexes are loaded from repo-owned schema JSON, not from
        # attacker-controlled input, so schema parity checks may execute them.
        assert any(re.search(pattern, unsafe_value) for pattern in unsafe_text_patterns)


def test_coordinator_dispatch_schema_enforces_handoff_only() -> None:
    schema = _schema("creative_hypothesis_coordinator_dispatch.v1.schema.json")
    entry = schema["$defs"]["dispatch_entry"]
    authority = schema["$defs"]["dispatch_authority"]

    assert entry["properties"]["task_packet_kind"]["const"] == "TASK_PACKET_V1"
    assert entry["properties"]["task_mode"]["const"] == "critique_refine_only"
    assert entry["properties"]["mutation_authority"]["const"] is False
    assert authority["properties"]["dispatch_to_coordinator"]["const"] is True
    assert authority["properties"]["execute_agent_tasks"]["const"] is False
    assert authority["properties"]["mutate_code"]["const"] is False


def test_context_and_packet_schemas_pin_reason_codes_and_artifact_path_ban() -> None:
    for filename in (
        "creative_protocol_context_map.v1.schema.json",
        "creative_hypothesis_packet.v1.schema.json",
    ):
        schema = _schema(filename)
        if filename == "creative_protocol_context_map.v1.schema.json":
            reason_schema = schema["$defs"]["classification"]["properties"]["reason_code"]
        else:
            reason_schema = schema["properties"]["reason_code"]
        assert set(reason_schema["enum"]) == REASON_CODES
        assert "artifacts" in schema["$defs"]["repo_path"]["not"]["pattern"]
        if filename == "creative_hypothesis_packet.v1.schema.json":
            assert (
                "^(app|core|frontend|ios|providers|alembic)/"
                in schema["$defs"]["repo_path"]["not"]["pattern"]
            )
            assert "^\\.github/workflows/" in schema["$defs"]["repo_path"]["not"]["pattern"]


def test_artifact_ref_schemas_reject_traversal_segments() -> None:
    for filename in (
        "creative_protocol_context_map.v1.schema.json",
        "experiment_runner_pr_oracle_attachment.v1.schema.json",
    ):
        schema = _schema(filename)
        artifact_ref = schema["$defs"]["artifact_ref"]
        assert "(^|/)\\.\\.?" in artifact_ref["not"]["pattern"]


def test_oracle_attachment_schema_requires_fingerprint_for_accepted_status() -> None:
    schema = _schema("experiment_runner_pr_oracle_attachment.v1.schema.json")
    accepted_guard = next(
        guard
        for guard in schema["allOf"]
        if guard["if"]["properties"]["oracle_status"]["const"] == "accepted"
    )

    accepted_then = accepted_guard["then"]["properties"]
    assert accepted_then["result_ref"]["$ref"] == "#/$defs/artifact_ref"
    assert accepted_then["result_fingerprint"]["$ref"] == "#/$defs/sha256"


def test_approval_schema_encodes_decision_state_machine() -> None:
    schema = _schema("creative_hypothesis_approval.v1.schema.json")
    approve_guard = next(
        guard
        for guard in schema["allOf"]
        if guard["if"]["properties"]["decision"]["const"] == "approve_for_pr1_specification"
    )
    reject_guard = next(
        guard
        for guard in schema["allOf"]
        if guard["if"]["properties"]["decision"]["const"] == "reject"
    )
    defer_guard = next(
        guard
        for guard in schema["allOf"]
        if guard["if"]["properties"]["decision"]["const"] == "defer"
    )

    approve_then = approve_guard["then"]["properties"]
    assert approve_then["next_step"]["const"] == "create_pr1_specification"
    assert approve_then["source_hypothesis_packet_id"]["$ref"] == "#/$defs/safe_id"
    assert approve_then["source_hypothesis_packet_fingerprint"]["$ref"] == "#/$defs/sha256"
    assert approve_then["hypothesis_fingerprint"]["$ref"] == "#/$defs/sha256"
    assert approve_then["approved_target_surfaces"]["minItems"] == 1
    assert (
        approve_then["approved_target_surfaces"]["items"]["$ref"]
        == "#/$defs/approvable_pr1_target_path"
    )
    assert reject_guard["then"]["properties"]["next_step"]["const"] == "no_action"
    assert reject_guard["then"]["properties"]["approved_target_surfaces"]["maxItems"] == 0
    assert reject_guard["then"]["properties"]["approved_agents"]["maxItems"] == 0
    assert defer_guard["then"]["properties"]["next_step"]["const"] == "defer"
    assert defer_guard["then"]["properties"]["approved_target_surfaces"]["maxItems"] == 0
    assert "app/" in schema["$defs"]["approvable_pr1_target_path"]["allOf"][2]["not"]["pattern"]


def _operational_request() -> dict[str, Any]:
    return {
        "schema_version": "creative_workflow_request.v1",
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "base_sha": BASE_SHA,
        "head_sha": HEAD_SHA,
        "task_packet_id": "a" * 12,
        "task_packet_fingerprint": SHA256,
        "criteria_ref": "artifacts/orchestration/creative_ops_1/task_analysis.md",
        "criteria_sha256": SHA256,
        "criteria_version": "CREATIVE-OPS-1.criteria.v1",
        "requirements_ref": "artifacts/orchestration/creative_ops_1/accepted_plan.md",
        "requirements_sha256": SHA256,
        "original_dod": ["Preserve every original requirement", "Observe a real patch"],
        "criteria": [
            {
                "id": "C1",
                "description": "Preserve requirements",
                "source_items": ["Preserve every original requirement"],
            },
            {
                "id": "C2",
                "description": "Observe a patch",
                "source_items": ["Observe a real patch"],
            },
        ],
        "allowed_paths": ["scripts/orchestration/example.py", "tests/test_example.py"],
        "euler": {
            "artifact_ref": "artifacts/orchestration/creative_ops_1/euler.json",
            "artifact_sha256": SHA256,
            "relations": [
                {
                    "id": "relation_a",
                    "description": "Candidate preserves the relation",
                    "finding_ids": [],
                }
            ],
        },
        "budget": {"seconds": 300, "max_files": 3, "max_test_commands": 2, "max_infra_retries": 1},
        "test_commands": ["pytest -q tests/test_example.py"],
    }


def _operational_native(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "creative_workflow_native_result.v1",
        "request_fingerprint": workflow_fingerprint(request),
        "task_packet_id": request["task_packet_id"],
        "status": "ok",
        "variants": [
            {
                "id": f"variant_{index}",
                "criteria": ["C1", "C2"],
                "change": f"Use formatter approach {index}",
                "paths": ["scripts/orchestration/example.py"],
                "assumptions": ["Existing validated inputs remain available"],
                "expected_observation": "A readable capsule is produced",
                "counterexample": "A stale source is rejected",
                "tests": ["pytest -q tests/test_example.py"],
                "risks": ["A malformed source blocks rendering"],
                "euler_relation_ids": ["relation_a"],
            }
            for index in (1, 2, 3)
        ],
        "unchanged_baseline": {
            "expected_observation": "Manual transfer remains",
            "risk": "Manual errors persist",
        },
    }


def _operational_review(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "creative_workflow_review.v1",
        "request_fingerprint": workflow_fingerprint(request),
        "selected_variant_id": "variant_1",
        "reviewer_role": "agent-coordinator",
        "rationale": "The first approach preserves every criterion with a direct test",
        "criteria_coverage": [
            {"id": "C1", "status": "supported", "evidence": "Source is retained"},
            {"id": "C2", "status": "supported", "evidence": "Focused patch test passes"},
        ],
        "euler_assessment": [
            {
                "id": "relation_a",
                "status": "satisfied",
                "evidence": "The counterexample is rejected",
            }
        ],
    }


def test_operational_workflow_binds_full_dod_euler_review_and_one_writer() -> None:
    request = validate_creative_workflow_request(_operational_request())
    schema = json.loads(
        (REPO_ROOT / "docs/orchestration/contracts/creative_workflow.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(schema["$defs"]["request"]["required"]) == set(request)
    assert (
        schema["$defs"]["request"]["properties"]["budget"]["properties"]["max_files"]["maximum"]
        == 3
    )
    result = validate_creative_workflow_native_result(_operational_native(request), request)
    review = validate_creative_workflow_review(_operational_review(request), request, result)
    handoff = {
        "schema_version": "creative_workflow_handoff.v1",
        "request_fingerprint": workflow_fingerprint(request),
        "selected_variant_id": "variant_1",
        "coordinator_role": "agent-coordinator",
        "writer_role": "security-auditor",
        "manifest_order": 5,
        "files": ["scripts/orchestration/example.py"],
    }
    assert (
        validate_creative_workflow_handoff(
            handoff,
            request,
            result,
            review,
            [(5, "security-auditor")],
            [
                "agent-coordinator",
                "logic-agent",
                "philosophy-agent",
                "cursor-specialist-agent",
                "security-auditor",
            ],
        )
        == handoff
    )
    stage = {
        "schema_version": "creative_workflow.v1",
        "stage": "admitted",
        "request": request,
        "native_result": result,
        "review": review,
        "handoff": handoff,
        "intake_error": None,
    }
    stage = build_creative_workflow_stage(stage, upstream_fingerprint=SHA256)
    assert validate_creative_workflow_stage(stage) == stage
    assert stage["upstream_assets"] == [SHA256]


@pytest.mark.parametrize(
    "field",
    [
        "base_sha",
        "head_sha",
        "criteria_version",
        "criteria_sha256",
        "task_packet_fingerprint",
        "requirements_sha256",
    ],
)
def test_operational_native_rejects_stale_request_identity(field: str) -> None:
    request = _operational_request()
    result = _operational_native(request)
    request[field] = "c" * 40 if field in {"base_sha", "head_sha"} else "different"
    with pytest.raises(ExperimentRunnerCreativeContextContractError):
        validate_creative_workflow_native_result(result, request)


def test_operational_review_blocks_missing_dod_and_violated_euler() -> None:
    request = _operational_request()
    request["criteria"][1]["source_items"] = ["Preserve every original requirement"]
    with pytest.raises(ExperimentRunnerCreativeContextContractError, match="DoD coverage"):
        validate_creative_workflow_request(request)
    request = _operational_request()
    result = _operational_native(request)
    review = _operational_review(request)
    review["euler_assessment"][0]["status"] = "violated"
    with pytest.raises(ExperimentRunnerCreativeContextContractError, match="Euler relation"):
        validate_creative_workflow_review(review, request, result)


def test_operational_native_and_handoff_reject_out_of_scope() -> None:
    request = _operational_request()
    result = _operational_native(request)
    result["variants"][0]["paths"] = ["app/services/unsafe.py"]
    with pytest.raises(ExperimentRunnerCreativeContextContractError, match="allowed paths"):
        validate_creative_workflow_native_result(result, request)
    result = _operational_native(request)
    review = _operational_review(request)
    handoff = {
        "schema_version": "creative_workflow_handoff.v1",
        "request_fingerprint": workflow_fingerprint(request),
        "selected_variant_id": "variant_1",
        "coordinator_role": "agent-coordinator",
        "writer_role": "security-auditor",
        "manifest_order": 5,
        "files": ["tests/test_example.py"],
    }
    with pytest.raises(ExperimentRunnerCreativeContextContractError, match="file scope"):
        validate_creative_workflow_handoff(
            handoff,
            request,
            result,
            review,
            [(5, "security-auditor")],
            [
                "agent-coordinator",
                "logic-agent",
                "philosophy-agent",
                "cursor-specialist-agent",
                "security-auditor",
            ],
        )


def test_operational_handoff_rejects_missing_canonical_occurrence_order() -> None:
    request = _operational_request()
    result = _operational_native(request)
    review = _operational_review(request)
    handoff = {
        "schema_version": "creative_workflow_handoff.v1",
        "request_fingerprint": workflow_fingerprint(request),
        "selected_variant_id": "variant_1",
        "coordinator_role": "agent-coordinator",
        "writer_role": "qa-engineer-agent",
        "manifest_order": 999,
        "files": ["scripts/orchestration/example.py"],
    }
    with pytest.raises(ExperimentRunnerCreativeContextContractError, match="occurrence"):
        validate_creative_workflow_handoff(
            handoff, request, result, review, [(1, "qa-engineer-agent")], dispatch_order=None
        )


def test_operational_handoff_rejects_readonly_repeated_slug_occurrence() -> None:
    request = _operational_request()
    result = _operational_native(request)
    review = _operational_review(request)
    role_order = [
        "security-auditor",
        "logic-agent",
        "philosophy-agent",
        "cursor-specialist-agent",
        "security-auditor",
    ]
    handoff = {
        "schema_version": "creative_workflow_handoff.v1",
        "request_fingerprint": workflow_fingerprint(request),
        "selected_variant_id": "variant_1",
        "coordinator_role": "agent-coordinator",
        "writer_role": "security-auditor",
        "manifest_order": 1,
        "files": ["scripts/orchestration/example.py"],
    }
    with pytest.raises(ExperimentRunnerCreativeContextContractError, match="occurrence"):
        validate_creative_workflow_handoff(
            handoff, request, result, review, [(5, "security-auditor")], role_order
        )
    handoff["manifest_order"] = 5
    assert (
        validate_creative_workflow_handoff(
            handoff, request, result, review, [(5, "security-auditor")], role_order
        )
        == handoff
    )


def test_operational_native_rejects_unapproved_test_command() -> None:
    request = _operational_request()
    result = _operational_native(request)
    result["variants"][0]["tests"] = ["pytest -q tests/test_unreviewed.py"]
    with pytest.raises(ExperimentRunnerCreativeContextContractError, match="test command"):
        validate_creative_workflow_native_result(result, request)


def test_operational_writer_occurrence_comes_from_canonical_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = bootstrap.build_task_packet(
        goal=f"Compare formatter approaches {uuid.uuid4().hex}",
        task_class="Implementation",
        candidate_paths=["tests/test_example.py"],
        creative_applicability="alternatives",
    )
    packet_path = (
        REPO_ROOT / "artifacts/orchestration/task_packets" / f"{packet['task_packet_id']}.json"
    )
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    try:
        role_order, eligible = cli._canonical_manifest_writer_occurrences(
            {
                "task_packet_id": packet["task_packet_id"],
                "task_packet_fingerprint": "sha256:"
                + hashlib.sha256(packet_path.read_bytes()).hexdigest(),
            }
        )
        assert any(role == "qa-engineer-agent" for _order, role in eligible)
        assert role_order.index("qa-engineer-agent") + 1 < 999
        with monkeypatch.context() as patch:
            patch.setattr(cli.qoder_dispatch_bridge, "main", lambda _argv: 1)
            with pytest.raises(cli.ExperimentRunnerCreativeContextCliError, match="unavailable"):
                cli._canonical_manifest_writer_occurrences(
                    {
                        "task_packet_id": packet["task_packet_id"],
                        "task_packet_fingerprint": "sha256:"
                        + hashlib.sha256(packet_path.read_bytes()).hexdigest(),
                    }
                )
    finally:
        packet_path.unlink(missing_ok=True)


def test_operational_cli_native_stages_and_archive_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(rail_applicability, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        cli,
        "CREATIVE_CONTEXT_ROOT",
        tmp_path / "artifacts/orchestration/experiments/creative_context",
    )
    source_dir = tmp_path / "artifacts/orchestration/creative_ops_1"
    source_dir.mkdir(parents=True)
    for name, content in (
        ("task_analysis.md", "Accepted criteria v1"),
        ("accepted_plan.md", "Complete accepted owner plan"),
        ("euler.json", '{"relations": ["relation_a"]}'),
    ):
        (source_dir / name).write_text(content, encoding="utf-8")
    packet = bootstrap.build_task_packet(
        goal="Compare a local formatter",
        task_class="Implementation",
        candidate_paths=["tests/test_example.py", "tests/test_other_example.py"],
        creative_applicability="alternatives",
    )
    packet_root = tmp_path / "artifacts/orchestration/task_packets"
    packet_root.mkdir(parents=True)
    packet_path = packet_root / f"{packet['task_packet_id']}.json"
    packet_path.write_text(json.dumps(packet, sort_keys=True), encoding="utf-8")
    request = _operational_request()
    request["task_packet_id"] = packet["task_packet_id"]
    request["task_packet_fingerprint"] = (
        "sha256:" + hashlib.sha256(packet_path.read_bytes()).hexdigest()
    )
    for field, name in (
        ("criteria_sha256", "task_analysis.md"),
        ("requirements_sha256", "accepted_plan.md"),
    ):
        request[field] = "sha256:" + hashlib.sha256((source_dir / name).read_bytes()).hexdigest()
    request["euler"]["artifact_sha256"] = (
        "sha256:" + hashlib.sha256((source_dir / "euler.json").read_bytes()).hexdigest()
    )
    monkeypatch.setattr(
        cli,
        "_git_identity",
        lambda: (request["repository"], request["base_sha"], request["head_sha"]),
    )
    monkeypatch.setattr(
        cli,
        "_canonical_manifest_writer_occurrences",
        lambda _request: (["qa-engineer-agent"], [(1, "qa-engineer-agent")]),
    )
    for field, wrong in (
        ("repository", "Other/PulsePlate"),
        ("base_sha", "c" * 40),
        ("head_sha", "d" * 40),
    ):
        stale = deepcopy(request)
        stale[field] = wrong
        with pytest.raises(cli.ExperimentRunnerCreativeContextCliError, match="Git material"):
            cli._workflow_sources(stale)
    request_path = source_dir / "request.json"
    unauthorized = deepcopy(request)
    unauthorized["allowed_paths"] = ["app/services/payments_activation.py"]
    request_path.write_text(json.dumps(unauthorized), encoding="utf-8")
    output_dir = cli.CREATIVE_CONTEXT_ROOT / "live-case"
    assert (
        cli.main(
            [
                "workflow-prepare",
                "--packet",
                packet_path.relative_to(tmp_path).as_posix(),
                "--request",
                request_path.relative_to(tmp_path).as_posix(),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 1
    )
    descendant = deepcopy(request)
    descendant["allowed_paths"] = ["tests/test_example.py/child.py"]
    request_path.write_text(json.dumps(descendant), encoding="utf-8")
    assert (
        cli.main(
            [
                "workflow-prepare",
                "--packet",
                packet_path.relative_to(tmp_path).as_posix(),
                "--request",
                request_path.relative_to(tmp_path).as_posix(),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 1
    )
    broad_packet = bootstrap.build_task_packet(
        goal="Compare a product formatter",
        task_class="Implementation",
        candidate_paths=["app"],
        creative_applicability="alternatives",
    )
    broad_path = packet_root / f"{broad_packet['task_packet_id']}.json"
    broad_path.write_text(json.dumps(broad_packet), encoding="utf-8")
    broad_snapshot = rail_applicability.read_task_packet_snapshot(
        broad_path.relative_to(tmp_path).as_posix()
    )
    broad_treatment = dict(
        (name, treatment)
        for name, treatment, _reasons in rail_applicability.build_evidence_rail_applicability(
            broad_snapshot
        ).treatments
    )
    assert broad_treatment["creative"] == rail_applicability.RailTreatment.RECOMMEND
    broad_request = deepcopy(request)
    broad_request["task_packet_id"] = broad_packet["task_packet_id"]
    broad_request["task_packet_fingerprint"] = (
        "sha256:" + hashlib.sha256(broad_path.read_bytes()).hexdigest()
    )
    broad_request["allowed_paths"] = ["app/services/payments_activation.py"]
    request_path.write_text(json.dumps(broad_request), encoding="utf-8")
    assert (
        cli.main(
            [
                "workflow-prepare",
                "--packet",
                broad_path.relative_to(tmp_path).as_posix(),
                "--request",
                request_path.relative_to(tmp_path).as_posix(),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 1
    )
    request["allowed_paths"] = ["tests/test_example.py", "tests/test_other_example.py"]
    request_path.write_text(json.dumps(request), encoding="utf-8")
    assert (
        cli.main(
            [
                "workflow-prepare",
                "--packet",
                packet_path.relative_to(tmp_path).as_posix(),
                "--request",
                request_path.relative_to(tmp_path).as_posix(),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )
    prepared = output_dir / "workflow.prepared.json"
    assert prepared.exists()
    native = _operational_native(request)
    for variant in native["variants"]:
        variant["paths"] = ["tests/test_example.py"]
    monkeypatch.setattr(cli.sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(native).encode())))
    assert cli.main(["workflow-ingest", "--workflow", str(prepared), "--native-result-stdin"]) == 0
    assert (output_dir / "workflow.returned.json").exists()
    validated = output_dir / "workflow.validated.json"
    review_path = source_dir / "review.json"
    review_path.write_text(json.dumps(_operational_review(request)), encoding="utf-8")
    assert (
        cli.main(
            [
                "workflow-review",
                "--workflow",
                str(validated),
                "--review",
                review_path.relative_to(tmp_path).as_posix(),
            ]
        )
        == 0
    )
    handoff_path = source_dir / "handoff.json"
    handoff = {
        "schema_version": "creative_workflow_handoff.v1",
        "request_fingerprint": workflow_fingerprint(request),
        "selected_variant_id": "variant_1",
        "coordinator_role": "agent-coordinator",
        "writer_role": "qa-engineer-agent",
        "manifest_order": 1,
        "files": ["tests/test_example.py"],
    }
    handoff_path.write_text(json.dumps(dict(handoff, manifest_order=999)), encoding="utf-8")
    assert (
        cli.main(
            [
                "workflow-admit",
                "--workflow",
                str(output_dir / "workflow.reviewed.json"),
                "--handoff",
                handoff_path.relative_to(tmp_path).as_posix(),
            ]
        )
        == 1
    )
    handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
    assert (
        cli.main(
            [
                "workflow-admit",
                "--workflow",
                str(output_dir / "workflow.reviewed.json"),
                "--handoff",
                handoff_path.relative_to(tmp_path).as_posix(),
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "workflow-prepare",
                "--packet",
                packet_path.relative_to(tmp_path).as_posix(),
                "--request",
                request_path.relative_to(tmp_path).as_posix(),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )
    for name, content in (
        ("patch.diff", "A sanitized candidate patch summary"),
        ("test_evidence.json", '{"focused_tests":"passed"}'),
        ("work_review.md", "Observed C1 and C2 after local checks"),
    ):
        (output_dir / name).write_text(content, encoding="utf-8")
    names = [
        *cli.WORKFLOW_STAGE_FILES.values(),
        "patch.diff",
        "test_evidence.json",
        "work_review.md",
    ]
    export_args = ["workflow-export", "--workflow", str(output_dir / "workflow.admitted.json")]
    for name in names:
        export_args.extend(["--include", name])
    assert cli.main(export_args) == 0
    archive = output_dir / "creative_workflow_capsule.zip"
    assert (
        cli.main(
            [
                "workflow-verify-archive",
                "--archive",
                str(archive),
                "--sha256",
                hashlib.sha256(archive.read_bytes()).hexdigest(),
                "--restore-dir",
                str(cli.CREATIVE_CONTEXT_ROOT / "restored"),
            ]
        )
        == 0
    )
    assert (
        cli.CREATIVE_CONTEXT_ROOT / "restored/work_review.md"
    ).read_text() == "Observed C1 and C2 after local checks"
    assert (
        cli.main(
            [
                "workflow-verify-archive",
                "--archive",
                str(archive),
                "--sha256",
                "0" * 64,
                "--restore-dir",
                str(cli.CREATIVE_CONTEXT_ROOT / "another-restore"),
            ]
        )
        == 1
    )
    (source_dir / "euler.json").write_text('{"relations": []}', encoding="utf-8")
    with pytest.raises(cli.ExperimentRunnerCreativeContextCliError, match="digest changed"):
        cli._load_workflow_stage(str(output_dir / "workflow.admitted.json"), "admitted")


def test_operational_stage_and_archive_reject_false_completion_and_unsafe_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _operational_request()
    prepared = {
        "schema_version": "creative_workflow.v1",
        "stage": "prepared",
        "request": request,
        "native_result": None,
        "review": None,
        "handoff": None,
        "intake_error": None,
    }
    with pytest.raises(ExperimentRunnerCreativeContextContractError, match="native result"):
        build_creative_workflow_stage(
            dict(prepared, stage="validated"), upstream_fingerprint=SHA256
        )
    with pytest.raises(cli.ExperimentRunnerCreativeContextCliError, match="malformed"):
        cli._workflow_json_bytes(b'{"a":1,"a":2}')
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    output = tmp_path / "artifacts/orchestration/experiments/creative_context/attempt"
    output.mkdir(parents=True)
    for name in cli.WORKFLOW_STAGE_FILES.values():
        (output / name).write_text("{}", encoding="utf-8")
    for name in ("patch.diff", "test_evidence.json", "work_review.md"):
        (output / name).write_text("safe", encoding="utf-8")
    include = [
        *cli.WORKFLOW_STAGE_FILES.values(),
        "patch.diff",
        "test_evidence.json",
        "work_review.md",
    ]
    (output / "patch.diff").unlink()
    (output / "patch.diff").symlink_to(tmp_path / "secret")
    with pytest.raises(cli.ExperimentRunnerCreativeContextCliError, match="symlink"):
        cli._workflow_archive_inputs(output, include)
    with pytest.raises(cli.ExperimentRunnerCreativeContextCliError, match="unapproved"):
        cli._workflow_archive_inputs(output, [*include, "../secret"])
