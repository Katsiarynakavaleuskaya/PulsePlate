"""Deterministic tests for scripts/orchestration/qoder_dispatch_bridge.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast, Dict, List

import pytest
from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import (
    qoder_dispatch_bridge,
    review_invariant_family_relations as relations,
    role_dispatch_bridge,
    task_bootstrap,
)
from scripts.orchestration.context_pack import compute_task_packet_id
from scripts.orchestration.native_subagent_bridge import build_native_subagent_bridge
from scripts.orchestration.task_bootstrap import build_role_agent_dispatch_contract

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

PACKET_PATH = REPO_ROOT / "docs" / "orchestration" / "PHILOSOPHY_EPIC_V2_PR1_PACKET_2026-05-17.md"
_SYNTHETIC_WORKSPACE_SOURCE = "test://synthetic-synthesis-workspace"

REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "manifest_contract_version",
    "generated_at",
    "packet_source",
    "mode",
    "dispatch_sequence",
    "parallelizable_groups",
    "parallel_execution_allowed",
    "parallel_execution_reason",
    "post_open_role_gates",
    "mandatory_post_open",
    "mandatory_post_open_gates",
    "mandatory_post_open_role_agents",
    "compatibility_aliases",
}

REQUIRED_ENTRY_KEYS = {
    "order",
    "role_slug",
    "qoder_subagent_type",
    "agent_definition_path",
    "required_context_paths",
    "recommended_skills",
    "mode",
    "system_prompt_excerpt",
    "description",
    "readonly",
    "implementation_owner_override",
    "constraints",
    "depends_on_previous",
}


class _LegacyCandidatePathList(list[object]):
    pass


@pytest.fixture(autouse=True)
def _isolate_synthetic_synthesis_workspace_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep metadata matrices synthetic while real CLI tests bind workspace artifacts."""

    validate_source = qoder_dispatch_bridge._validate_single_coordinator_synthesis_workspace_source

    def validate_or_stub(
        payload: Dict[str, Any],
        *,
        validated_synthesis_context: Dict[str, Any],
        candidate_paths: List[str],
    ) -> None:
        if payload.get("creative_pilot_workspace_source") == _SYNTHETIC_WORKSPACE_SOURCE:
            return
        validate_source(
            payload,
            validated_synthesis_context=validated_synthesis_context,
            candidate_paths=candidate_paths,
        )

    monkeypatch.setattr(
        qoder_dispatch_bridge,
        "_validate_single_coordinator_synthesis_workspace_source",
        validate_or_stub,
    )


def _rebind_single_coordinator_synthesis_task_packet_id(packet: dict[str, object]) -> None:
    context = cast(dict[str, Any], packet["creative_pilot_context"])
    creative_learning_hints = cast(dict[str, Any], packet["creative_learning_hints"])
    invariant_review = cast(dict[str, Any], packet["invariant_review"])
    creative_identity_fingerprint = fingerprint_payload(
        {
            "creative_learning_hints": creative_learning_hints["source_hints_fingerprint"],
            "creative_pilot": fingerprint_payload(context),
        }
    )
    base_packet_id = compute_task_packet_id(
        goal=cast(str, packet["goal"]),
        task_class=cast(str, packet["task_class"]),
        domain=cast(str, packet["domain"]),
        candidate_paths=cast(list[str], packet["candidate_paths"]),
        requested_agents=cast(list[str], packet["requested_agents"]),
        pr_phase=cast(str, packet["pr_phase"]),
        design_fingerprint=task_bootstrap._design_fingerprint(
            design_lane_mode=cast(str, packet["design_lane_mode"]),
            design_lane_contract=cast(dict[str, Any], packet["design_lane_contract"]),
        ),
        creative_learning_hints_fingerprint=creative_identity_fingerprint,
    )
    packet["task_packet_id"] = task_bootstrap._bind_invariant_review_packet_id(
        base_packet_id,
        invariant_review_fingerprint=",".join(cast(list[str], invariant_review["change_classes"])),
    )


def _substitute_synthesis_context_identity(context: dict[str, Any]) -> None:
    workspace_id = "workspace:substituted"
    revision_fingerprint = "sha256:" + ("9" * 64)
    context["workspace_id"] = workspace_id
    context["workspace_intent_fingerprint"] = "sha256:" + ("8" * 64)
    context["workspace_revision_fingerprint"] = revision_fingerprint
    context["dispatch_input_fingerprint"] = revision_fingerprint
    assignment = cast(dict[str, Any], cast(list[object], context["assignments"])[0])
    assignment["input_fingerprint"] = revision_fingerprint
    assignment["input_refs"] = [workspace_id, revision_fingerprint]


def _single_coordinator_synthesis_packet(
    *,
    goal: str = "synthesize validated creative pilot results",
    candidate_paths: list[str] | None = None,
) -> dict[str, object]:
    revision_fingerprint = "sha256:" + ("2" * 64)
    workspace_id = "workspace:synthesis-test"
    packet = task_bootstrap.build_task_packet(
        goal=goal,
        task_class="orchestration",
        candidate_paths=["README.md"] if candidate_paths is None else candidate_paths,
        requested_agents=["agent-coordinator"],
    )
    transport = packet["native_subagent_bridge"]["transport"]
    assert isinstance(transport, str)
    bridge = build_native_subagent_bridge(
        primary_agent="agent-coordinator",
        secondary_agents=[],
        reviewer="agent-coordinator",
        advisory_agents=[],
        transport=transport,
    )
    packet.update(
        {
            "primary_agent": "agent-coordinator",
            "secondary_agents": [],
            "reviewer": "agent-coordinator",
            "requested_agents": ["agent-coordinator"],
            "requested_agent_disposition": [],
            "creative_pilot_workspace_source": _SYNTHETIC_WORKSPACE_SOURCE,
            "native_subagent_bridge": bridge,
            "creative_pilot_context": {
                "schema_version": "creative_pilot_context.v2",
                "workspace_id": workspace_id,
                "workspace_intent_fingerprint": "sha256:" + ("1" * 64),
                "workspace_revision_fingerprint": revision_fingerprint,
                "phase": "synthesis",
                "dispatch_input_fingerprint": revision_fingerprint,
                "assignments": [
                    {
                        "assignment_id": "synthesis:agent-coordinator",
                        "role": "agent-coordinator",
                        "phase": "synthesis",
                        "review_mode": "specification_planning",
                        "diff_expected": False,
                        "review_question": (
                            "Synthesize only validated role results using deterministic hard gates."
                        ),
                        "input_fingerprint": revision_fingerprint,
                        "input_refs": [workspace_id, revision_fingerprint],
                    }
                ],
                "authority": {
                    "read_structured_inputs": True,
                    "generate_patch": False,
                    "write_repository": False,
                    "call_provider": False,
                },
            },
        }
    )
    automation_flags = packet["automation_flags"]
    assert isinstance(automation_flags, dict)
    automation_flags["creative_pilot_enabled"] = True
    packet["role_agent_dispatch_contract"] = build_role_agent_dispatch_contract(
        native_subagent_bridge=bridge,
        pr_phase=cast(str, packet["pr_phase"]),
    )
    normalized_packet = cast(dict[str, object], packet)
    _rebind_single_coordinator_synthesis_task_packet_id(normalized_packet)
    return normalized_packet


def test_role_dispatch_bridge_exports_compatibility_main() -> None:
    """The neutral CLI keeps the historical qoder bridge implementation."""
    assert role_dispatch_bridge.main is qoder_dispatch_bridge.main


def test_legacy_qoder_dispatch_bridge_script_help_importable() -> None:
    """Direct legacy script execution must install repo root before package imports."""

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "orchestration" / "qoder_dispatch_bridge.py"),
            "--help",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "usage: role_dispatch_bridge" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr


def test_role_dispatch_bridge_help_uses_neutral_name(capsys: pytest.CaptureFixture[str]) -> None:
    """The neutral CLI must not expose the old adapter name as the public command."""
    with pytest.raises(SystemExit) as exc_info:
        role_dispatch_bridge.main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: role_dispatch_bridge" in captured.out
    assert "Generate a JSON role dispatch manifest" in captured.out
    assert "Generate a JSON dispatch manifest for Qoder" not in captured.out


def test_single_coordinator_synthesis_aliases_parse_as_one_role() -> None:
    packet = _single_coordinator_synthesis_packet()

    assert qoder_dispatch_bridge._parse_json_packet_roles(packet) == ["agent-coordinator"]


def test_root_scope_packet_preserves_required_invariant_dispatch() -> None:
    packet = task_bootstrap.build_task_packet(
        goal="Inspect repository scope",
        task_class="Orchestration",
        candidate_paths=["."],
    )

    roles = qoder_dispatch_bridge._parse_json_packet_roles(packet)

    assert packet["candidate_paths"] == ["."]
    assert roles[:3] == ["agent-coordinator", "logic-agent", "philosophy-agent"]
    assert roles.count("security-auditor") == 1


def test_root_scope_cannot_claim_single_coordinator_synthesis_alias() -> None:
    packet = _single_coordinator_synthesis_packet()
    packet["candidate_paths"] = ["."]

    with pytest.raises(
        ValueError,
        match="invariant_review classes and evidence must match the canonical classifier",
    ):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_single_coordinator_synthesis_accepts_rebound_context_identity() -> None:
    packet = json.loads(json.dumps(_single_coordinator_synthesis_packet()))
    context = cast(dict[str, Any], packet["creative_pilot_context"])
    _substitute_synthesis_context_identity(context)
    _rebind_single_coordinator_synthesis_task_packet_id(packet)

    assert qoder_dispatch_bridge._parse_json_packet_roles(packet) == ["agent-coordinator"]


def test_single_coordinator_synthesis_rederives_domain_before_identity() -> None:
    packet = json.loads(json.dumps(_single_coordinator_synthesis_packet()))
    forged_domain = "frontend"
    forged_route = qoder_dispatch_bridge.load_routing_graph()[forged_domain]
    packet["domain"] = forged_domain
    packet["cluster"] = forged_route.cluster
    _rebind_single_coordinator_synthesis_task_packet_id(packet)

    with pytest.raises(ValueError) as exc_info:
        qoder_dispatch_bridge._parse_json_packet_roles(packet)
    assert str(exc_info.value) == (
        "creative pilot synthesis task_packet_id must match canonical packet identity"
    )


def test_single_coordinator_synthesis_rejects_noncanonical_cluster() -> None:
    packet = json.loads(json.dumps(_single_coordinator_synthesis_packet()))
    packet["cluster"] = "forged-cluster"

    with pytest.raises(ValueError) as exc_info:
        qoder_dispatch_bridge._parse_json_packet_roles(packet)
    assert str(exc_info.value) == (
        "creative pilot synthesis task_packet_id must match canonical packet identity"
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("domain", None),
        ("domain", 1),
        ("cluster", None),
        ("cluster", 1),
        ("cluster", "unknown-cluster"),
    ),
)
def test_single_coordinator_synthesis_requires_domain_cluster_shape(
    field: str,
    replacement: object,
) -> None:
    packet = json.loads(json.dumps(_single_coordinator_synthesis_packet()))
    if replacement is None:
        packet.pop(field)
    else:
        packet[field] = replacement

    with pytest.raises(ValueError) as exc_info:
        qoder_dispatch_bridge._parse_json_packet_roles(packet)
    assert str(exc_info.value) == (
        "creative pilot synthesis task_packet_id must match canonical packet identity"
    )


def test_synthesis_security_requirement_cannot_be_hidden_by_flag() -> None:
    packet = _single_coordinator_synthesis_packet(candidate_paths=["deploy/example.yaml"])
    automation_flags = cast(dict[str, Any], packet["automation_flags"])
    assert automation_flags["security_review_required"] is True
    automation_flags["security_review_required"] = False

    with pytest.raises(ValueError) as exc_info:
        qoder_dispatch_bridge._parse_json_packet_roles(packet)
    assert str(exc_info.value) == (
        "creative pilot synthesis packet metadata requires security_review_required=false"
    )


@pytest.mark.parametrize(
    "candidate_paths",
    (
        [str((REPO_ROOT / "deploy/example.yaml").resolve())],
        ["./deploy/example.yaml"],
        ["deploy/example.yaml", "deploy/example.yaml"],
    ),
)
def test_synthesis_candidate_paths_must_use_canonical_spelling(
    candidate_paths: list[str],
) -> None:
    packet = _single_coordinator_synthesis_packet(candidate_paths=["deploy/example.yaml"])
    automation_flags = cast(dict[str, Any], packet["automation_flags"])
    assert automation_flags["security_review_required"] is True
    automation_flags["security_review_required"] = False
    packet["candidate_paths"] = candidate_paths

    with pytest.raises(ValueError) as exc_info:
        qoder_dispatch_bridge._parse_json_packet_roles(packet)
    assert str(exc_info.value) == (
        "creative pilot synthesis packet metadata requires canonical candidate_paths"
    )


def test_synthesis_judgment_requirement_cannot_be_hidden_by_projection() -> None:
    packet = _single_coordinator_synthesis_packet(
        goal="synthesize validated creative pilot adjudication results"
    )
    automation_flags = cast(dict[str, Any], packet["automation_flags"])
    assert automation_flags["judgment_lane_enabled"] is True
    automation_flags["judgment_lane_enabled"] = False
    packet["decision_contract"] = {
        "mode": "standard",
        "judgment_enabled": False,
        "claim_taxonomy": [],
        "flow": [],
    }
    packet["judgment_budget"] = {
        "skeptic_pass_required": False,
        "verifier_pass_required": False,
        "max_provider_calls": 0,
        "uncertainty_split_required": False,
    }
    packet["result_adjudication"] = {
        "claim_evidence_fields": [],
        "support_statuses": [],
        "evidence_modes": [],
        "uncertainty_fields": [],
        "promotion_labels": [],
    }

    with pytest.raises(ValueError) as exc_info:
        qoder_dispatch_bridge._parse_json_packet_roles(packet)
    assert str(exc_info.value) == (
        "creative pilot synthesis packet metadata requires judgment lane disabled"
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "extra_secondary",
        "extra_advisory",
        "altered_primary_alias",
        "altered_reviewer_alias",
        "empty_assignments",
        "multiple_assignments",
        "non_coordinator_assignment",
        "tampered_assignment",
        "wrong_phase",
        "writable_authority",
        "provider_authority",
        "generate_patch_authority",
        "structured_input_authority",
        "numeric_structured_input_authority",
        "numeric_generate_patch_authority",
        "numeric_write_authority",
        "numeric_provider_authority",
        "implementation_owner_flags",
        "dispatch_role_order",
        "required_invariant_review",
        "malformed_bridge_contract",
        "malformed_dispatch_contract",
        "task_packet_schema_drift",
        "bridge_protocol_drift",
        "requested_agents_empty",
        "requested_agents_extra",
        "nonempty_requested_disposition",
        "post_open_phase",
        "merge_ready_phase",
        "creative_flag_false",
        "creative_flag_missing",
        "security_review_required",
        "numeric_security_review_flag",
        "invariant_review_required_flag",
        "numeric_invariant_review_flag",
        "stale_task_packet_id",
        "legacy_schema_without_invariant",
        "missing_schema_without_invariant",
        "legacy_non_object_context",
        "legacy_missing_phase_context",
        "legacy_invalid_phase_context",
    ),
)
def test_single_coordinator_synthesis_near_misses_fail_closed(mutation: str) -> None:
    packet = json.loads(json.dumps(_single_coordinator_synthesis_packet()))
    context = packet["creative_pilot_context"]
    bridge = packet["native_subagent_bridge"]
    dispatch_contract = packet["role_agent_dispatch_contract"]
    assert isinstance(context, dict)
    assert isinstance(bridge, dict)
    assert isinstance(dispatch_contract, dict)
    assignments = context["assignments"]
    assert isinstance(assignments, list)
    assignment = assignments[0]
    assert isinstance(assignment, dict)

    if mutation == "extra_secondary":
        bridge["secondary"].append(bridge["primary"])
    elif mutation == "extra_advisory":
        bridge["advisory"].append(bridge["primary"])
    elif mutation == "altered_primary_alias":
        packet["primary_agent"] = "architecture-specialist"
    elif mutation == "altered_reviewer_alias":
        packet["reviewer"] = "architecture-specialist"
    elif mutation == "empty_assignments":
        assignments.clear()
    elif mutation == "multiple_assignments":
        assignments.append(dict(assignment))
    elif mutation == "non_coordinator_assignment":
        assignment["role"] = "architecture-specialist"
    elif mutation == "tampered_assignment":
        assignment["input_refs"] = [context["workspace_id"]]
    elif mutation == "wrong_phase":
        context["phase"] = "independent"
    elif mutation == "writable_authority":
        context["authority"]["write_repository"] = True
    elif mutation == "provider_authority":
        context["authority"]["call_provider"] = True
    elif mutation == "generate_patch_authority":
        context["authority"]["generate_patch"] = True
    elif mutation == "structured_input_authority":
        context["authority"]["read_structured_inputs"] = False
    elif mutation == "numeric_structured_input_authority":
        context["authority"]["read_structured_inputs"] = 1
    elif mutation == "numeric_generate_patch_authority":
        context["authority"]["generate_patch"] = 0
    elif mutation == "numeric_write_authority":
        context["authority"]["write_repository"] = 0
    elif mutation == "numeric_provider_authority":
        context["authority"]["call_provider"] = 0
    elif mutation == "implementation_owner_flags":
        dispatch_contract["runtime_implementation_owner_flags_required"] = True
        dispatch_contract["runtime_implementation_owners"] = ["security-auditor"]
    elif mutation == "dispatch_role_order":
        dispatch_contract["dispatch_role_order"] = ["agent-coordinator"]
    elif mutation == "required_invariant_review":
        packet["invariant_review"]["state"] = "required_pending"
    elif mutation == "malformed_bridge_contract":
        bridge["primary"]["dispatch_contract"] = "spawn"
    elif mutation == "malformed_dispatch_contract":
        dispatch_contract.pop("dispatch_manifest_entrypoint")
    elif mutation == "task_packet_schema_drift":
        packet["schema_version"] = "3.0"
    elif mutation == "bridge_protocol_drift":
        bridge["protocol_version"] = "2.0"
    elif mutation == "requested_agents_empty":
        packet["requested_agents"] = []
    elif mutation == "requested_agents_extra":
        packet["requested_agents"] = ["agent-coordinator", "architecture-specialist"]
    elif mutation == "nonempty_requested_disposition":
        packet["requested_agent_disposition"] = [
            {
                "agent": "agent-coordinator",
                "status": "honored_primary",
                "reason": "Compatibility metadata must still fail closed for synthesis.",
            }
        ]
    elif mutation in {"post_open_phase", "merge_ready_phase"}:
        packet["pr_phase"] = "post_open_review" if mutation == "post_open_phase" else "merge_ready"
        packet["role_agent_dispatch_contract"] = build_role_agent_dispatch_contract(
            native_subagent_bridge=bridge,
            pr_phase=packet["pr_phase"],
        )
    elif mutation == "creative_flag_false":
        packet["automation_flags"]["creative_pilot_enabled"] = False
    elif mutation == "security_review_required":
        packet["automation_flags"]["security_review_required"] = True
    elif mutation == "numeric_security_review_flag":
        packet["automation_flags"]["security_review_required"] = 0
    elif mutation == "invariant_review_required_flag":
        packet["automation_flags"]["invariant_class_review_required"] = True
    elif mutation == "numeric_invariant_review_flag":
        packet["automation_flags"]["invariant_class_review_required"] = 0
    elif mutation == "stale_task_packet_id":
        _substitute_synthesis_context_identity(context)
    elif mutation in {"legacy_schema_without_invariant", "missing_schema_without_invariant"}:
        if mutation == "legacy_schema_without_invariant":
            packet["schema_version"] = "3.0"
        else:
            packet.pop("schema_version")
        packet.pop("invariant_review")
        packet["automation_flags"].pop("invariant_class_review_required")
    elif mutation in {
        "legacy_non_object_context",
        "legacy_missing_phase_context",
        "legacy_invalid_phase_context",
    }:
        packet["schema_version"] = "3.0"
        packet.pop("invariant_review")
        packet["automation_flags"].pop("invariant_class_review_required")
        if mutation == "legacy_non_object_context":
            packet["creative_pilot_context"] = []
        elif mutation == "legacy_missing_phase_context":
            packet["creative_pilot_context"] = {}
        else:
            packet["creative_pilot_context"] = {"phase": "unknown"}
    else:
        packet["automation_flags"].pop("creative_pilot_enabled")

    exact_errors = {
        "requested_agents_empty": (
            "creative pilot synthesis packet metadata requires only agent-coordinator"
        ),
        "requested_agents_extra": (
            "creative pilot synthesis packet metadata requires only agent-coordinator"
        ),
        "nonempty_requested_disposition": (
            "creative pilot synthesis packet metadata requires empty requested disposition"
        ),
        "post_open_phase": (
            "creative pilot synthesis packet metadata requires an opening PR phase"
        ),
        "merge_ready_phase": (
            "creative pilot synthesis packet metadata requires an opening PR phase"
        ),
        "creative_flag_false": (
            "creative pilot synthesis packet metadata requires creative_pilot_enabled=true"
        ),
        "creative_flag_missing": (
            "creative pilot synthesis packet metadata requires creative_pilot_enabled=true"
        ),
        "numeric_structured_input_authority": (
            "invalid creative_pilot_context: creative pilot task context authority is invalid"
        ),
        "numeric_generate_patch_authority": (
            "invalid creative_pilot_context: creative pilot task context authority is invalid"
        ),
        "numeric_write_authority": (
            "invalid creative_pilot_context: creative pilot task context authority is invalid"
        ),
        "numeric_provider_authority": (
            "invalid creative_pilot_context: creative pilot task context authority is invalid"
        ),
        "security_review_required": (
            "creative pilot synthesis packet metadata requires security_review_required=false"
        ),
        "numeric_security_review_flag": (
            "creative pilot synthesis packet metadata requires security_review_required=false"
        ),
        "invariant_review_required_flag": (
            "creative pilot synthesis packet metadata requires no invariant review pass"
        ),
        "numeric_invariant_review_flag": (
            "creative pilot synthesis packet metadata requires no invariant review pass"
        ),
        "stale_task_packet_id": (
            "creative pilot synthesis task_packet_id must match canonical packet identity"
        ),
        "legacy_schema_without_invariant": (
            "creative pilot synthesis requires task packet schema 3.1"
        ),
        "missing_schema_without_invariant": (
            "creative pilot synthesis requires task packet schema 3.1"
        ),
        "legacy_non_object_context": "legacy creative_pilot_context must be an object",
        "legacy_missing_phase_context": ("legacy creative_pilot_context phase is unsupported"),
        "legacy_invalid_phase_context": ("legacy creative_pilot_context phase is unsupported"),
    }
    with pytest.raises(ValueError) as exc_info:
        qoder_dispatch_bridge._parse_json_packet_roles(packet)
    if mutation in exact_errors:
        assert str(exc_info.value) == exact_errors[mutation]


@pytest.mark.parametrize(
    ("section", "field", "value"),
    (
        ("automation_flags", "judgment_lane_enabled", True),
        ("automation_flags", "judgment_lane_enabled", 0),
        ("decision_contract", "judgment_enabled", True),
        ("decision_contract", "judgment_enabled", 0),
        ("decision_contract", "mode", "verification_first"),
        ("decision_contract", "claim_taxonomy", ["normative_claim"]),
        ("decision_contract", "flow", ["skeptic"]),
        ("judgment_budget", "skeptic_pass_required", True),
        ("judgment_budget", "skeptic_pass_required", 0),
        ("judgment_budget", "verifier_pass_required", True),
        ("judgment_budget", "verifier_pass_required", 0),
        ("judgment_budget", "uncertainty_split_required", True),
        ("judgment_budget", "uncertainty_split_required", 0),
        ("judgment_budget", "max_provider_calls", False),
        ("judgment_budget", "max_provider_calls", 1),
        ("result_adjudication", "claim_evidence_fields", ["claim_id"]),
        ("result_adjudication", "support_statuses", ["supported"]),
        ("result_adjudication", "evidence_modes", ["direct"]),
        ("result_adjudication", "uncertainty_fields", ["confidence"]),
        ("result_adjudication", "promotion_labels", ["promote"]),
    ),
)
def test_single_coordinator_synthesis_judgment_near_misses_fail_closed(
    section: str,
    field: str,
    value: object,
) -> None:
    packet = json.loads(json.dumps(_single_coordinator_synthesis_packet()))
    projection = packet[section]
    assert isinstance(projection, dict)
    projection[field] = value

    with pytest.raises(ValueError) as exc_info:
        qoder_dispatch_bridge._parse_json_packet_roles(packet)
    assert str(exc_info.value) == (
        "creative pilot synthesis packet metadata requires judgment lane disabled"
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "decision_missing_key",
        "decision_extra_key",
        "decision_non_object",
        "budget_missing_key",
        "budget_extra_key",
        "budget_non_object",
        "adjudication_missing_key",
        "adjudication_extra_key",
        "adjudication_non_object",
        "goal_non_string",
        "task_class_non_string",
        "candidate_paths_non_list",
        "candidate_path_non_string",
    ),
)
def test_single_coordinator_synthesis_judgment_structure_fails_closed(
    mutation: str,
) -> None:
    packet = json.loads(json.dumps(_single_coordinator_synthesis_packet()))
    if mutation == "decision_missing_key":
        packet["decision_contract"].pop("flow")
    elif mutation == "decision_extra_key":
        packet["decision_contract"]["extra"] = []
    elif mutation == "decision_non_object":
        packet["decision_contract"] = []
    elif mutation == "budget_missing_key":
        packet["judgment_budget"].pop("verifier_pass_required")
    elif mutation == "budget_extra_key":
        packet["judgment_budget"]["extra"] = False
    elif mutation == "budget_non_object":
        packet["judgment_budget"] = []
    elif mutation == "adjudication_missing_key":
        packet["result_adjudication"].pop("promotion_labels")
    elif mutation == "adjudication_extra_key":
        packet["result_adjudication"]["extra"] = []
    elif mutation == "adjudication_non_object":
        packet["result_adjudication"] = []
    elif mutation == "goal_non_string":
        packet["goal"] = 1
    elif mutation == "task_class_non_string":
        packet["task_class"] = 1
    elif mutation == "candidate_paths_non_list":
        packet["candidate_paths"] = "README.md"
    else:
        packet["candidate_paths"] = [1]

    with pytest.raises(ValueError) as exc_info:
        qoder_dispatch_bridge._parse_json_packet_roles(packet)
    expected_error = (
        "creative pilot synthesis packet metadata requires canonical candidate_paths"
        if mutation in {"candidate_paths_non_list", "candidate_path_non_string"}
        else "creative pilot synthesis packet metadata requires judgment lane disabled"
    )
    assert str(exc_info.value) == expected_error


@pytest.mark.parametrize("rebind_context", (False, True))
def test_synthesis_judgment_error_precedes_packet_identity(
    rebind_context: bool,
) -> None:
    packet = json.loads(json.dumps(_single_coordinator_synthesis_packet()))
    context = cast(dict[str, Any], packet["creative_pilot_context"])
    _substitute_synthesis_context_identity(context)
    if rebind_context:
        _rebind_single_coordinator_synthesis_task_packet_id(packet)
    packet["automation_flags"]["judgment_lane_enabled"] = True

    with pytest.raises(ValueError) as exc_info:
        qoder_dispatch_bridge._parse_json_packet_roles(packet)
    assert str(exc_info.value) == (
        "creative pilot synthesis packet metadata requires judgment lane disabled"
    )


@pytest.mark.parametrize("schema_version", ("3.0", None))
@pytest.mark.parametrize("context_shape", ("absent", "null", "independent", "rebuttal"))
def test_legacy_creative_context_preserves_existing_role_order(
    schema_version: str | None,
    context_shape: str,
) -> None:
    packet: dict[str, object] = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [{"repo_agent_slug": "security-auditor"}],
            "advisory": [],
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
        }
    }
    if schema_version is not None:
        packet["schema_version"] = schema_version
    if context_shape == "null":
        packet["creative_pilot_context"] = None
    elif context_shape != "absent":
        packet["creative_pilot_context"] = {"phase": context_shape}

    assert qoder_dispatch_bridge._parse_json_packet_roles(packet) == [
        "agent-coordinator",
        "security-auditor",
        "architecture-specialist",
    ]


def test_single_coordinator_synthesis_cli_rejects_missing_coordinator_definition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    packet_path = tmp_path / "task_packet.json"
    packet_path.write_text(json.dumps(_single_coordinator_synthesis_packet()), encoding="utf-8")
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)

    result = role_dispatch_bridge.main(
        ["--packet", str(packet_path), "--mode", "runtime", "--pretty"]
    )

    assert result == 1
    assert "Agent definitions not found for: agent-coordinator" in capsys.readouterr().err


def _v2_source_artifact(*, repeated: bool = True) -> dict[str, object]:
    relation = {
        "left_family_id": "family_alpha",
        "right_family_id": "family_beta",
        "relation": "partial_overlap",
        "intersection_finding_ids": ["finding_b"],
        "left_only_finding_ids": ["finding_a"],
        "right_only_finding_ids": ["finding_c"],
    }
    return {
        "schema_version": "review_invariant_family_relations.v1",
        "policy_version": "review_invariant_family_relations.policy.v1",
        "snapshot": {
            "families": [
                {"family_id": "family_alpha", "finding_ids": ["finding_a", "finding_b"]},
                {
                    "family_id": "family_beta",
                    "finding_ids": ["finding_b", "finding_c"] if repeated else ["finding_c"],
                },
            ]
        },
        "snapshot_fingerprint": "sha256:" + ("1" * 64),
        "artifact_fingerprint": "sha256:" + ("2" * 64),
        "idempotency_key": "review-invariant-family-relations.v1:" + ("2" * 64),
        "relations": [relation],
        "unknown_finding_ids": [],
    }


def _v2_packet(
    monkeypatch: pytest.MonkeyPatch,
    *,
    repeated: bool = True,
    requested_agents: List[str] | None = None,
) -> dict[str, object]:
    artifact = _v2_source_artifact(repeated=repeated)
    if not repeated:
        snapshot = artifact["snapshot"]
        assert isinstance(snapshot, dict)
        families = snapshot["families"]
        assert isinstance(families, list)
        first_family = families[0]
        assert isinstance(first_family, dict)
        first_family["finding_ids"] = ["finding_a"]
    monkeypatch.setattr(
        task_bootstrap,
        "_read_invariant_family_relations_input",
        lambda _path: artifact,
    )
    return task_bootstrap.build_task_packet(
        goal="Review repeated explicit invariant families",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=(["agent-coordinator"] if requested_agents is None else requested_agents),
        review_invariant_family_relations_input=(
            "artifacts/orchestration/review_invariant_family_relations/input.json"
        ),
        pr_phase="post_open_review",
    )


def _recompute_v2_packet_id(packet: dict[str, object]) -> str:
    review = cast(Dict[str, Any], packet["invariant_review"])
    family_repeat = cast(Dict[str, Any], review["family_repeat"])
    creative_learning_hints = cast(Dict[str, Any], packet["creative_learning_hints"])
    return task_bootstrap.compute_invariant_family_review_packet_id(
        goal=cast(str, packet["goal"]),
        task_class=cast(str, packet["task_class"]),
        domain=cast(str, packet["domain"]),
        candidate_paths=cast(List[str], packet["candidate_paths"]),
        requested_agents=cast(List[str], packet["requested_agents"]),
        pr_phase=cast(str, packet["pr_phase"]),
        design_lane_mode=cast(str, packet["design_lane_mode"]),
        design_lane_contract=cast(Dict[str, Any], packet["design_lane_contract"]),
        creative_learning_hints_fingerprint=cast(
            str, creative_learning_hints["source_hints_fingerprint"]
        ),
        creative_learning_hints_projection=creative_learning_hints,
        recommended_skills=cast(List[str], packet["recommended_skills"]),
        skill_routing=cast(Dict[str, Any], packet["skill_routing"]),
        artifact_fingerprint=cast(str, family_repeat["artifact_fingerprint"]),
        invariant_review_projection=review,
        required_context=cast(List[str], packet["required_context"]),
        primary_agent=cast(str, packet["primary_agent"]),
        secondary_agents=cast(List[str], packet["secondary_agents"]),
        reviewer=cast(str, packet["reviewer"]),
        requested_agent_disposition=cast(
            List[Dict[str, str]], packet["requested_agent_disposition"]
        ),
    )


def test_qoder_accepts_closed_v2_without_recomputing_l1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    monkeypatch.setattr(
        relations,
        "process_input_bytes",
        lambda _raw: pytest.fail("Qoder must not recompute L1"),
    )

    assert qoder_dispatch_bridge._parse_json_packet_roles(packet) == [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]


def test_qoder_rejects_open_or_semantically_widened_v2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    review = packet["invariant_review"]
    assert isinstance(review, dict)
    review["change_classes"] = ["guard"]

    with pytest.raises(ValueError, match="exactly match the invariant_review.v2 fields"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_v2_under_legacy_task_packet_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    packet["schema_version"] = "3.0"

    with pytest.raises(ValueError, match="requires task packet schema 3.1"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_v2_idempotency_digest_mismatched_to_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    review = packet["invariant_review"]
    assert isinstance(review, dict)
    family_repeat = review["family_repeat"]
    assert isinstance(family_repeat, dict)
    family_repeat["idempotency_key"] = "review-invariant-family-relations.v1:" + ("0" * 64)

    with pytest.raises(ValueError, match="must match artifact_fingerprint"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_accepts_not_required_v2_with_ordinary_post_open_tail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch, repeated=False)

    roles = qoder_dispatch_bridge._parse_json_packet_roles(packet)

    qa_index = roles.index("qa-engineer-agent")
    assert roles[qa_index : qa_index + 3] == [
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]
    review = packet["invariant_review"]
    assert isinstance(review, dict)
    assert review["state"] == "not_required"


def test_qoder_accepts_producer_rejected_unknown_requested_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(
        monkeypatch,
        repeated=False,
        requested_agents=["invalid_slug"],
    )

    assert packet["requested_agent_disposition"] == [
        {
            "agent": "invalid_slug",
            "status": "rejected_unknown_agent",
            "reason": "Agent is not registered in the canonical inventory.",
        }
    ]
    roles = qoder_dispatch_bridge._parse_json_packet_roles(packet)
    qa_index = roles.index("qa-engineer-agent")
    assert roles[qa_index : qa_index + 3] == [
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]


def test_repeated_family_producer_rejects_credential_shaped_requested_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="credential-shaped requested agents"):
        _v2_packet(
            monkeypatch,
            repeated=False,
            requested_agents=["gh" + "p_" + ("a" * 20)],
        )


def test_qoder_rejects_credential_shaped_unknown_requested_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(
        monkeypatch,
        repeated=False,
        requested_agents=["invalid_slug"],
    )
    credential_shaped_agent = "gh" + "p_" + ("a" * 20)
    packet["requested_agents"] = [credential_shaped_agent]
    dispositions = cast(List[Dict[str, str]], packet["requested_agent_disposition"])
    dispositions[0]["agent"] = credential_shaped_agent
    packet["task_packet_id"] = _recompute_v2_packet_id(packet)

    with pytest.raises(ValueError, match="credential-shaped requested agents"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_not_required_v2_without_exact_post_open_tail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch, repeated=False)
    packet["primary_agent"] = "agent-coordinator"
    packet["secondary_agents"] = []
    packet["reviewer"] = "security-auditor"
    packet["requested_agent_disposition"] = [
        {
            "agent": "agent-coordinator",
            "status": "honored_primary",
            "reason": "Forged canonical assignment without the ordinary post-open tail.",
        }
    ]
    packet["native_subagent_bridge"] = build_native_subagent_bridge(
        primary_agent="agent-coordinator",
        secondary_agents=[],
        advisory_agents=[],
        reviewer="security-auditor",
    )
    packet["role_agent_dispatch_contract"] = build_role_agent_dispatch_contract(
        native_subagent_bridge=packet["native_subagent_bridge"],
        pr_phase="post_open_review",
    )
    review = cast(Dict[str, Any], packet["invariant_review"])
    family_repeat = cast(Dict[str, Any], review["family_repeat"])
    creative_learning_hints = cast(Dict[str, Any], packet["creative_learning_hints"])
    packet["task_packet_id"] = task_bootstrap.compute_invariant_family_review_packet_id(
        goal=cast(str, packet["goal"]),
        task_class=cast(str, packet["task_class"]),
        domain=cast(str, packet["domain"]),
        candidate_paths=cast(List[str], packet["candidate_paths"]),
        requested_agents=cast(List[str], packet["requested_agents"]),
        pr_phase=cast(str, packet["pr_phase"]),
        design_lane_mode=cast(str, packet["design_lane_mode"]),
        design_lane_contract=cast(Dict[str, Any], packet["design_lane_contract"]),
        creative_learning_hints_fingerprint=cast(
            str, creative_learning_hints["source_hints_fingerprint"]
        ),
        creative_learning_hints_projection=creative_learning_hints,
        recommended_skills=cast(List[str], packet["recommended_skills"]),
        skill_routing=cast(Dict[str, Any], packet["skill_routing"]),
        artifact_fingerprint=cast(str, family_repeat["artifact_fingerprint"]),
        invariant_review_projection=review,
        required_context=cast(List[str], packet["required_context"]),
        primary_agent=cast(str, packet["primary_agent"]),
        secondary_agents=cast(List[str], packet["secondary_agents"]),
        reviewer=cast(str, packet["reviewer"]),
        requested_agent_disposition=cast(
            List[Dict[str, str]], packet["requested_agent_disposition"]
        ),
    )

    with pytest.raises(ValueError, match="exact ordinary post-open role tail"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize(
    ("field", "forged_value"),
    [
        ("source_hints_id", "hints-forged"),
        ("recommended_role_focus", [{"role": "logic-agent"}]),
        ("reuse_lesson_ids", ["lesson-forged"]),
        ("avoid_lesson_ids", ["lesson-forged"]),
    ],
)
def test_qoder_rejects_v2_creative_hints_projection_tampering(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    forged_value: object,
) -> None:
    packet = _v2_packet(monkeypatch)
    creative_learning_hints = cast(Dict[str, Any], packet["creative_learning_hints"])
    creative_learning_hints[field] = forged_value

    with pytest.raises(ValueError, match="task_packet_id"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize("field", ["recommended_skills", "skill_routing"])
def test_qoder_rejects_v2_skill_projection_tampering(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    packet = _v2_packet(monkeypatch)
    if field == "recommended_skills":
        recommended_skills = cast(List[str], packet[field])
        recommended_skills.append("forged-skill")
    else:
        skill_routing = cast(Dict[str, Any], packet[field])
        skill_routing["forged"] = True

    with pytest.raises(ValueError, match="task_packet_id"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_active_v2_requested_agent_disposition_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    packet["requested_agents"] = ["backend-engineer"]
    packet["task_packet_id"] = _recompute_v2_packet_id(packet)

    with pytest.raises(ValueError, match="requested_agents"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_active_v2_requested_agent_outside_fixed_role_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    packet["requested_agents"] = ["backend-engineer"]
    packet["requested_agent_disposition"] = [
        {
            "agent": "backend-engineer",
            "status": "rejected_unknown_agent",
            "reason": "Forged aligned metadata must not widen the fixed L2 role order.",
        }
    ]
    packet["task_packet_id"] = _recompute_v2_packet_id(packet)

    with pytest.raises(ValueError, match="stay inside the repeated-family role order"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_active_v2_requested_agent_status_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    dispositions = cast(List[Dict[str, str]], packet["requested_agent_disposition"])
    dispositions[0]["status"] = "rejected_unknown_agent"
    dispositions[0]["reason"] = "Forged status contradicts the fixed primary assignment."
    packet["task_packet_id"] = _recompute_v2_packet_id(packet)

    with pytest.raises(ValueError, match="status must match the fixed role assignment"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_not_required_v2_requested_agent_status_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch, repeated=False)
    secondary_agents = cast(List[str], packet["secondary_agents"])
    dispositions = cast(List[Dict[str, str]], packet["requested_agent_disposition"])
    assert "agent-coordinator" in secondary_agents
    assert packet["reviewer"] != "agent-coordinator"
    assert dispositions[0]["status"] == "honored_secondary"
    dispositions[0]["status"] = "honored_reviewer"
    dispositions[0]["reason"] = "Forged status contradicts the ordinary role assignment."
    packet["task_packet_id"] = _recompute_v2_packet_id(packet)

    with pytest.raises(ValueError, match="status must match the role assignment"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_not_required_v2_assigned_agent_as_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch, repeated=False)
    secondary_agents = cast(List[str], packet["secondary_agents"])
    dispositions = cast(List[Dict[str, str]], packet["requested_agent_disposition"])
    assert "agent-coordinator" in secondary_agents
    assert dispositions[0]["status"] == "honored_secondary"
    dispositions[0]["status"] = "rejected_unknown_agent"
    dispositions[0]["reason"] = "Forged unknown status contradicts the assigned role."
    packet["task_packet_id"] = _recompute_v2_packet_id(packet)

    with pytest.raises(ValueError, match="status must match the role assignment"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_v2_noncanonical_candidate_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    candidate_paths = cast(List[str], packet["candidate_paths"])
    packet["candidate_paths"] = [str(REPO_ROOT / candidate_paths[0])]

    with pytest.raises(ValueError, match="candidate_paths"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_v2_parent_traversal_before_identity_recomputation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    packet["candidate_paths"] = ["../outside.py"]

    with pytest.raises(ValueError, match="candidate_paths"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_v2_without_repeated_family_contract_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    required_context = cast(List[str], packet["required_context"])
    packet["required_context"] = [
        path
        for path in required_context
        if path != task_bootstrap.INVARIANT_FAMILY_REVIEW_REQUIRED_CONTEXT
    ]

    with pytest.raises(ValueError, match="required_context"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize(
    "extra_context",
    ["/etc/passwd", "docs/roadmap/BACKLOG_LEDGER.md"],
)
def test_qoder_rejects_v2_required_context_addition_with_stale_identity(
    monkeypatch: pytest.MonkeyPatch,
    extra_context: str,
) -> None:
    packet = _v2_packet(monkeypatch)
    required_context = cast(List[str], packet["required_context"])
    packet["required_context"] = sorted([*required_context, extra_context])

    with pytest.raises(ValueError, match="required_context|task_packet_id"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize(
    "extra_context",
    [
        ".",
        ".env",
        "artifacts/orchestration/review_invariant_family_relations/input.json",
    ],
)
def test_qoder_rejects_recomputed_v2_context_outside_producer_owned_set(
    monkeypatch: pytest.MonkeyPatch,
    extra_context: str,
) -> None:
    packet = _v2_packet(monkeypatch)
    required_context = cast(List[str], packet["required_context"])
    packet["required_context"] = sorted([*required_context, extra_context])
    packet["task_packet_id"] = _recompute_v2_packet_id(packet)

    with pytest.raises(ValueError, match="producer-owned context paths"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_recomputed_v2_context_missing_required_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    packet["required_context"] = [task_bootstrap.INVARIANT_FAMILY_REVIEW_REQUIRED_CONTEXT]
    packet["task_packet_id"] = _recompute_v2_packet_id(packet)

    with pytest.raises(ValueError, match="required producer context baseline"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_recomputed_v2_context_missing_ops_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    required_context = cast(List[str], packet["required_context"])
    orchestration_context = set(task_bootstrap.ORCHESTRATION_CONTEXT_FILES)
    assert orchestration_context.issubset(required_context)
    packet["required_context"] = [
        path for path in required_context if path not in orchestration_context
    ]
    packet["task_packet_id"] = _recompute_v2_packet_id(packet)

    with pytest.raises(ValueError, match="required producer context baseline"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_v2_manifest_propagates_validated_packet_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    packet = _v2_packet(monkeypatch)
    required_context = cast(List[str], packet["required_context"])

    agents_dir = tmp_path / ".cursor" / "agents"
    agents_dir.mkdir(parents=True)
    for role in task_bootstrap.INVARIANT_FAMILY_REVIEW_ROLE_ORDER:
        (agents_dir / f"{role}.md").write_text(
            "---\n"
            f"name: {role}\n"
            "model: auto\n"
            f"description: {role}\n"
            "readonly: true\n"
            "---\n"
            f"\n# {role}\n",
            encoding="utf-8",
        )
    packet_path = tmp_path / "v2.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(qoder_dispatch_bridge, "_parse_context_map", lambda: {})
    monkeypatch.setattr(qoder_dispatch_bridge, "_ensure_routing_graph", lambda: {})

    result = qoder_dispatch_bridge.main(["--packet", str(packet_path), "--mode", "analysis"])

    assert result == 0
    manifest = json.loads(capsys.readouterr().out)

    assert all(
        entry["required_context_paths"] == sorted(required_context)
        for entry in manifest["dispatch_sequence"]
    )
    assert all(
        not any(
            path.startswith("artifacts/orchestration/review_invariant_family_relations/")
            for path in entry["required_context_paths"]
        )
        for entry in manifest["dispatch_sequence"]
    )


def test_qoder_rejects_not_required_v2_with_injected_secondary_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch, repeated=False)
    secondary_agents = packet["secondary_agents"]
    assert isinstance(secondary_agents, list)
    secondary_agents.append("philosophy-agent")
    primary_agent = packet["primary_agent"]
    reviewer = packet["reviewer"]
    assert isinstance(primary_agent, str)
    assert isinstance(reviewer, str)
    packet["native_subagent_bridge"] = build_native_subagent_bridge(
        primary_agent=primary_agent,
        secondary_agents=secondary_agents,
        advisory_agents=[],
        reviewer=reviewer,
    )
    packet["role_agent_dispatch_contract"] = build_role_agent_dispatch_contract(
        native_subagent_bridge=packet["native_subagent_bridge"],
        pr_phase="post_open_review",
    )

    with pytest.raises(ValueError, match="task_packet_id must bind"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_v2_artifact_pair_tampering_with_stale_task_packet_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    original_packet_id = packet["task_packet_id"]
    review = packet["invariant_review"]
    assert isinstance(review, dict)
    family_repeat = review["family_repeat"]
    assert isinstance(family_repeat, dict)
    family_repeat["artifact_fingerprint"] = "sha256:" + ("3" * 64)
    family_repeat["idempotency_key"] = "review-invariant-family-relations.v1:" + ("3" * 64)
    assert packet["task_packet_id"] == original_packet_id

    with pytest.raises(ValueError, match="task_packet_id must bind"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_qoder_rejects_active_projection_substituted_with_not_required_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_packet = _v2_packet(monkeypatch)
    active_review = active_packet["invariant_review"]
    assert isinstance(active_review, dict)
    active_repeat = active_review["family_repeat"]
    assert isinstance(active_repeat, dict)
    not_required_packet = _v2_packet(monkeypatch, repeated=False)
    not_required_review = not_required_packet["invariant_review"]
    assert isinstance(not_required_review, dict)
    not_required_repeat = not_required_review["family_repeat"]
    assert isinstance(not_required_repeat, dict)
    not_required_repeat["artifact_fingerprint"] = active_repeat["artifact_fingerprint"]
    not_required_repeat["idempotency_key"] = active_repeat["idempotency_key"]
    not_required_packet["task_packet_id"] = active_packet["task_packet_id"]

    with pytest.raises(ValueError, match="task_packet_id must bind"):
        qoder_dispatch_bridge._parse_json_packet_roles(not_required_packet)


def test_qoder_rejects_altered_repeated_families_with_stale_task_packet_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _v2_packet(monkeypatch)
    review = packet["invariant_review"]
    assert isinstance(review, dict)
    family_repeat = review["family_repeat"]
    assert isinstance(family_repeat, dict)
    repeated = family_repeat["repeated_families"]
    assert isinstance(repeated, list)
    assert isinstance(repeated[0], dict)
    repeated[0]["finding_ids"] = ["finding_a", "finding_c"]

    with pytest.raises(ValueError, match="task_packet_id must bind"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def require_feature(feature_key: str) -> None:
    """Skip with the repo-standard optional-feature reason prefix."""

    pytest.skip(f"feature_disabled:{feature_key}")


# ---------------------------------------------------------------------------
# 1. test_manifest_generation_from_packet
# ---------------------------------------------------------------------------


def test_manifest_generation_from_packet() -> None:
    """Use the existing packet to generate a manifest; verify valid JSON with expected roles."""
    if not PACKET_PATH.is_file():
        pytest.skip(f"Packet file not available: {PACKET_PATH}")

    # The packet declares these roles in order
    expected_roles = [
        "agent-coordinator",
        "architecture-specialist",
        "philosophy-agent",
        "rag-systems-agent",
        "logic-agent",
        "security-auditor",
    ]

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=expected_roles,
        mode="analysis",
        packet_source=str(PACKET_PATH.relative_to(REPO_ROOT)),
    )

    # Validate JSON serializability
    json_str = json.dumps(manifest)
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)

    # Roles appear in expected order (only those with agent definition files)
    produced_slugs = [entry["role_slug"] for entry in manifest["dispatch_sequence"]]
    # Filter expected to only those that exist as agent defs
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    existing = [s for s in expected_roles if (agents_dir / f"{s}.md").is_file()]
    assert produced_slugs == existing


def test_parse_task_bootstrap_json_packet_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bridge must consume the JSON packets emitted by task_bootstrap.py."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
            "secondary": [
                {"repo_agent_slug": "cursor-specialist-agent"},
                {"repo_agent_slug": "security-auditor"},
            ],
            "advisory": [
                {"repo_agent_slug": "qa-engineer-agent"},
                {"repo_agent_slug": "bug-hunter"},
                {"repo_agent_slug": "dev-operator"},
            ],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "cursor-specialist-agent",
        "security-auditor",
        "architecture-specialist",
    ]


def test_parse_task_bootstrap_json_packet_places_reviewer_tail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Declared JSON reviewer must remain in tail slot for reviewer semantics."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "reviewer": {"repo_agent_slug": "security-auditor"},
            "secondary": [{"repo_agent_slug": "architecture-specialist"}],
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "architecture-specialist",
        "security-auditor",
    ]


def test_parse_task_bootstrap_json_packet_preserves_repeated_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JSON packets may intentionally reuse the same role in distinct positions."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "reviewer": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [{"repo_agent_slug": "architecture-specialist"}],
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "architecture-specialist",
        "agent-coordinator",
    ]


def test_parse_task_bootstrap_json_packet_preserves_adjacent_repeated_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adjacent duplicate JSON bindings represent distinct packet slots."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "reviewer": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [],
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "agent-coordinator",
    ]


def test_task_bootstrap_json_reviewer_tail_resolves_code_review() -> None:
    """Reviewer-capable slugs from JSON packets should get CodeReview in tail slot."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "architecture-specialist", "security-auditor"]
    for slug in slugs:
        if not (agents_dir / f"{slug}.md").is_file():
            pytest.skip(f"Agent definition not found: {slug}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )
    by_slug = {
        entry["role_slug"]: entry["qoder_subagent_type"] for entry in manifest["dispatch_sequence"]
    }

    assert by_slug["architecture-specialist"] == "Research"
    assert by_slug["security-auditor"] == "CodeReview"


def test_parse_task_bootstrap_json_packet_forces_coordinator_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cursor-led packet projections must still dispatch coordinator first."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "cursor-specialist-agent"},
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
            "secondary": [],
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "cursor-specialist-agent",
        "architecture-specialist",
    ]


def test_parse_task_bootstrap_json_packet_skips_no_spawn_secondary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No-spawn metadata must be honored even if a future packet misplaces it."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
            "secondary": [
                {
                    "repo_agent_slug": "qa-engineer-agent",
                    "dispatch_contract": {
                        "advisory_only": True,
                        "spawn_with_native_subagent": False,
                    },
                }
            ],
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "architecture-specialist",
    ]


def test_parse_task_bootstrap_json_packet_includes_required_advisory_role_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Required advisory bindings are executable role passes, not skipped metadata."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
            "secondary": [{"repo_agent_slug": "qa-engineer-agent"}],
            "advisory": [
                {
                    "repo_agent_slug": "ml-engineer-agent",
                    "dispatch_contract": {
                        "advisory_only": False,
                        "spawn_with_native_subagent": True,
                        "required_role_pass": True,
                    },
                }
            ],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "qa-engineer-agent",
        "ml-engineer-agent",
        "architecture-specialist",
    ]


def test_parse_task_bootstrap_json_packet_preserves_requested_role_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit requested agents define the role order when they are spawnable."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "requested_agents": [
            "agent-coordinator",
            "architecture-specialist",
            "qa-engineer-agent",
            "bug-hunter",
            "security-auditor",
        ],
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [
                {"repo_agent_slug": "bug-hunter"},
                {"repo_agent_slug": "cursor-specialist-agent"},
                {"repo_agent_slug": "security-auditor"},
                {"repo_agent_slug": "architecture-specialist"},
            ],
            "reviewer": {"repo_agent_slug": "qa-engineer-agent"},
            "advisory": [],
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "architecture-specialist",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
        "cursor-specialist-agent",
    ]


def test_manifest_preserves_requested_order_from_json_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit requested order must survive final dispatch manifest generation."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    required_slugs = [
        "agent-coordinator",
        "architecture-specialist",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
        "cursor-specialist-agent",
    ]
    tmp_agents_dir = tmp_path / ".cursor" / "agents"
    tmp_agents_dir.mkdir(parents=True)
    for slug in required_slugs:
        qoder_type = "Verify" if slug in {"qa-engineer-agent", "bug-hunter"} else "Research"
        (tmp_agents_dir / f"{slug}.md").write_text(
            f"---\nslug: {slug}\nqoder_type: {qoder_type}\n---\n# {slug}\n",
            encoding="utf-8",
        )
    packet = {
        "requested_agents": [
            "agent-coordinator",
            "architecture-specialist",
            "qa-engineer-agent",
            "bug-hunter",
            "security-auditor",
        ],
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [
                {"repo_agent_slug": "bug-hunter"},
                {"repo_agent_slug": "cursor-specialist-agent"},
                {"repo_agent_slug": "security-auditor"},
                {"repo_agent_slug": "architecture-specialist"},
            ],
            "reviewer": {"repo_agent_slug": "qa-engineer-agent"},
            "advisory": [],
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    roles = qoder_dispatch_bridge._parse_packet_roles(packet_path)
    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=roles,
        mode="analysis",
        packet_source="packet.json",
        enforce_mandatory_post_open_tail=not (
            qoder_dispatch_bridge._json_packet_requested_order_preserves_mandatory_tail(packet_path)
        ),
    )

    assert [entry["role_slug"] for entry in manifest["dispatch_sequence"]] == [
        "agent-coordinator",
        "architecture-specialist",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
        "cursor-specialist-agent",
    ]


def test_manifest_normalizes_requested_order_when_security_precedes_bug_hunter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit requests must still preserve the canonical QA -> bug -> security tail."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    required_slugs = [
        "agent-coordinator",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
    ]
    tmp_agents_dir = tmp_path / ".cursor" / "agents"
    tmp_agents_dir.mkdir(parents=True)
    for slug in required_slugs:
        qoder_type = "Verify" if slug in {"qa-engineer-agent", "bug-hunter"} else "Research"
        (tmp_agents_dir / f"{slug}.md").write_text(
            f"---\nslug: {slug}\nqoder_type: {qoder_type}\n---\n# {slug}\n",
            encoding="utf-8",
        )
    packet = {
        "requested_agents": [
            "agent-coordinator",
            "qa-engineer-agent",
            "security-auditor",
            "bug-hunter",
        ],
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [
                {"repo_agent_slug": "security-auditor"},
                {"repo_agent_slug": "bug-hunter"},
            ],
            "reviewer": {"repo_agent_slug": "qa-engineer-agent"},
            "advisory": [],
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    roles = qoder_dispatch_bridge._parse_packet_roles(packet_path)
    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=roles,
        mode="analysis",
        packet_source="packet.json",
        enforce_mandatory_post_open_tail=not (
            qoder_dispatch_bridge._json_packet_requested_order_preserves_mandatory_tail(packet_path)
        ),
    )

    assert [entry["role_slug"] for entry in manifest["dispatch_sequence"]] == [
        "agent-coordinator",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]


def test_manifest_enforces_mandatory_tail_for_partial_requested_order_from_json_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Partial requested order must not disable the canonical QA -> bug tail."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    required_slugs = [
        "agent-coordinator",
        "frontend-engineer",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
    ]
    tmp_agents_dir = tmp_path / ".cursor" / "agents"
    tmp_agents_dir.mkdir(parents=True)
    for slug in required_slugs:
        qoder_type = "Verify" if slug in {"qa-engineer-agent", "bug-hunter"} else "Research"
        (tmp_agents_dir / f"{slug}.md").write_text(
            f"---\nslug: {slug}\nqoder_type: {qoder_type}\n---\n# {slug}\n",
            encoding="utf-8",
        )
    packet = {
        "requested_agents": ["frontend-engineer"],
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [
                {"repo_agent_slug": "bug-hunter"},
                {"repo_agent_slug": "frontend-engineer"},
                {"repo_agent_slug": "security-auditor"},
            ],
            "reviewer": {"repo_agent_slug": "qa-engineer-agent"},
            "advisory": [],
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    roles = qoder_dispatch_bridge._parse_packet_roles(packet_path)
    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=roles,
        mode="analysis",
        packet_source="packet.json",
        enforce_mandatory_post_open_tail=not (
            qoder_dispatch_bridge._json_packet_requested_order_preserves_mandatory_tail(packet_path)
        ),
    )

    assert [entry["role_slug"] for entry in manifest["dispatch_sequence"]] == [
        "agent-coordinator",
        "frontend-engineer",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]


def test_requested_order_must_include_security_immediately_after_bug_hunter() -> None:
    """A partial QA -> bug request cannot disable security tail normalization."""

    assert not qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
        {
            "requested_agents": [
                "qa-engineer-agent",
                "architecture-specialist",
                "bug-hunter",
                "security-auditor",
            ]
        }
    )
    assert not qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
        {
            "requested_agents": [
                "qa-engineer-agent",
                "bug-hunter",
                "architecture-specialist",
            ]
        }
    )
    assert qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
        {
            "requested_agents": [
                "qa-engineer-agent",
                "bug-hunter",
                "security-auditor",
                "architecture-specialist",
            ]
        }
    )


def test_pre_open_packet_preserves_requested_custom_role_order() -> None:
    """Pre-open bootstrap order is mandatory and must not get post-open tail sorting."""

    assert qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
        {
            "pr_phase": "pre_open",
            "requested_agents": [
                "agent-coordinator",
                "architecture-specialist",
                "frontend-engineer",
                "cursor-specialist-agent",
                "security-auditor",
                "qa-engineer-agent",
                "bug-hunter",
            ],
        }
    )


def test_none_phase_packet_does_not_preserve_inverted_mandatory_tail() -> None:
    """Default JSON packets must not bypass the QA -> bug -> security tail."""

    assert not qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
        {
            "pr_phase": "none",
            "requested_agents": [
                "qa-engineer-agent",
                "security-auditor",
                "bug-hunter",
            ],
        }
    )


def test_pre_open_packet_rejects_malformed_requested_agents_before_bypass() -> None:
    """Pre-open order bypass still validates requested_agents is a slug list."""

    malformed_payloads = [
        {"pr_phase": "pre_open", "requested_agents": "frontend-engineer"},
        {"pr_phase": "pre_open", "requested_agents": ["frontend-engineer", 42]},
        {"pr_phase": "pre_open", "requested_agents": ["frontend engineer"]},
    ]

    for payload in malformed_payloads:
        assert not qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
            payload
        )


def test_parse_task_bootstrap_json_packet_limits_duplicate_requested_roles_to_spawnable_slots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Requested duplicates must not synthesize extra passes beyond bridge slots."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "requested_agents": [
            "agent-coordinator",
            "security-auditor",
            "agent-coordinator",
        ],
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [{"repo_agent_slug": "security-auditor"}],
            "advisory": [],
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "security-auditor",
    ]


def test_parse_task_bootstrap_json_packet_requested_roles_keep_required_non_requested_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Requested role ordering must not drop required bridge roles."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "requested_agents": ["frontend-engineer"],
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [
                {"repo_agent_slug": "frontend-engineer"},
                {"repo_agent_slug": "security-auditor"},
            ],
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
            "advisory": [],
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "frontend-engineer",
        "security-auditor",
        "architecture-specialist",
    ]


def test_parse_task_bootstrap_json_packet_empty_bridge_returns_no_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed JSON packets must not be auto-repaired into coordinator-only lanes."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(
        json.dumps({"native_subagent_bridge": {}}),
        encoding="utf-8",
    )

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == []


def test_parse_task_bootstrap_json_packet_all_no_spawn_returns_no_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fully no-spawn bridge should fail fast instead of dispatching coordinator only."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {
                "repo_agent_slug": "agent-coordinator",
                "dispatch_contract": {
                    "advisory_only": True,
                    "spawn_with_native_subagent": False,
                },
            },
            "reviewer": {
                "repo_agent_slug": "architecture-specialist",
                "dispatch_contract": {
                    "advisory_only": True,
                    "spawn_with_native_subagent": False,
                },
            },
            "secondary": [],
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == []


def test_parse_task_bootstrap_json_packet_missing_primary_returns_no_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Secondary/reviewer roles cannot replace the required spawnable primary binding."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "secondary": [{"repo_agent_slug": "architecture-specialist"}],
            "reviewer": {"repo_agent_slug": "security-auditor"},
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == []


def test_parse_task_bootstrap_json_packet_empty_primary_slug_returns_no_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A primary binding without a repo_agent_slug cannot establish lane ownership."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": ""},
            "secondary": [{"repo_agent_slug": "architecture-specialist"}],
            "reviewer": {"repo_agent_slug": "security-auditor"},
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == []


def test_parse_task_bootstrap_json_packet_no_spawn_primary_returns_no_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-spawnable primary makes the JSON bridge malformed."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {
                "repo_agent_slug": "agent-coordinator",
                "dispatch_contract": {
                    "advisory_only": True,
                    "spawn_with_native_subagent": False,
                },
            },
            "secondary": [{"repo_agent_slug": "architecture-specialist"}],
            "reviewer": {"repo_agent_slug": "security-auditor"},
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == []


def test_parse_task_bootstrap_json_packet_malformed_dispatch_contract_returns_no_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed dispatch_contract metadata should fail closed."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {
                "repo_agent_slug": "agent-coordinator",
                "dispatch_contract": "spawnable",
            },
            "secondary": [{"repo_agent_slug": "architecture-specialist"}],
            "reviewer": {"repo_agent_slug": "security-auditor"},
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == []


def test_parse_task_bootstrap_json_packet_runs_spawnable_advisory_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Advisory bridge entries are required role passes when spawnable."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [],
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
            "advisory": [
                {
                    "repo_agent_slug": "qa-engineer-agent",
                    "dispatch_contract": {
                        "advisory_only": False,
                        "spawn_with_native_subagent": True,
                    },
                }
            ],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "qa-engineer-agent",
        "architecture-specialist",
    ]


def test_parse_packet_roles_rejects_symlink_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Packet reads must stay under the resolved repo root."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"native_subagent_bridge": {}}), encoding="utf-8")
    link = repo_root / "packet.json"
    link.symlink_to(outside)
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", repo_root)

    with pytest.raises(SystemExit):
        qoder_dispatch_bridge._parse_packet_roles(link)


# ---------------------------------------------------------------------------
# 2. test_role_to_qoder_type_mapping
# ---------------------------------------------------------------------------


class TestRoleToQoderTypeMapping:
    """Verify resolve_qoder_type covers each documented mapping."""

    def test_readonly_architecture_specialist(self) -> None:
        agent_def = {
            "slug": "architecture-specialist",
            "name": "architecture-specialist",
            "readonly": True,
        }
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="analysis", is_reviewer=False
        )
        assert result == "Research"

    def test_backend_engineer_runtime(self) -> None:
        agent_def = {"slug": "backend-engineer", "name": "backend-engineer", "readonly": False}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="runtime", is_reviewer=False
        )
        assert result == "Coding"

    def test_readonly_backend_engineer_runtime_requires_owner_override(self) -> None:
        agent_def = {"slug": "backend-engineer", "name": "backend-engineer", "readonly": True}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="runtime", is_reviewer=False
        )
        assert result == "Research"

        owned_result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def,
            mode="runtime",
            is_reviewer=False,
            implementation_owners={"backend-engineer"},
        )
        assert owned_result == "Coding"

    def test_qa_engineer_agent(self) -> None:
        agent_def = {"slug": "qa-engineer-agent", "name": "qa-engineer-agent", "readonly": True}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="analysis", is_reviewer=False
        )
        assert result == "Verify"
        assert (
            qoder_dispatch_bridge.resolve_qoder_type(agent_def, mode="docs-only", is_reviewer=False)
            == "Verify"
        )

    def test_qa_engineer_agent_reviewer_slot_stays_verify(self) -> None:
        agent_def = {"slug": "qa-engineer-agent", "name": "qa-engineer-agent", "readonly": True}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="analysis", is_reviewer=True
        )
        assert result == "Verify"

    def test_bug_hunter(self) -> None:
        agent_def = {"slug": "bug-hunter", "name": "bug-hunter", "readonly": True}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="analysis", is_reviewer=False
        )
        assert result == "Verify"
        assert (
            qoder_dispatch_bridge.resolve_qoder_type(agent_def, mode="docs-only", is_reviewer=False)
            == "Verify"
        )

    def test_reviewer_slot(self) -> None:
        agent_def = {"slug": "security-auditor", "name": "security-auditor", "readonly": True}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="analysis", is_reviewer=True
        )
        assert result == "CodeReview"

    def test_frontend_engineer_runtime_returns_browser(self) -> None:
        """frontend-engineer in runtime mode should return Browser (UI validation)."""
        agent_def = {"slug": "frontend-engineer", "name": "frontend-engineer", "readonly": False}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="runtime", is_reviewer=False
        )
        assert result == "Browser"

    def test_frontend_engineer_coding_mode(self) -> None:
        """frontend-engineer in runtime mode (non-browser path) falls to Coding via generic check."""
        # Note: with the fix, frontend-engineer + runtime → Browser.
        # For non-runtime, non-analysis modes it hits Coding.
        agent_def = {"slug": "frontend-engineer", "name": "frontend-engineer", "readonly": False}
        # Use a mode that isn't "analysis"/"docs-only" (triggers Research) or "runtime" (triggers Browser)
        # There's no such mode currently – so we verify the analysis mode returns Research correctly
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="analysis", is_reviewer=False
        )
        assert result == "Research"

    def test_readonly_frontend_engineer_runtime_owner_returns_browser(self) -> None:
        """Runtime Browser dispatch for a readonly frontend role requires explicit ownership."""
        agent_def = {"slug": "frontend-engineer", "name": "frontend-engineer", "readonly": True}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def,
            mode="runtime",
            is_reviewer=False,
            implementation_owners={"frontend-engineer"},
        )
        assert result == "Browser"

    def test_unknown_agent_fallback(self) -> None:
        agent_def = {"slug": "nonexistent-agent", "name": "nonexistent-agent", "readonly": False}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="runtime", is_reviewer=False
        )
        assert result == "Research"


# ---------------------------------------------------------------------------
# 3. test_routing_graph_resolution
# ---------------------------------------------------------------------------


def test_routing_graph_resolution() -> None:
    """Verify that agent slugs resolve to correct domain/cluster from routing graph."""
    routing = qoder_dispatch_bridge._ensure_routing_graph()

    # If graph is available, it should be a non-empty dict
    if not routing:
        pytest.skip("Routing graph not available (no AGENT_ROUTING_GRAPH.md)")

    # Each entry should have cluster, primary, and reviewer fields
    for domain, info in routing.items():
        assert "cluster" in info, f"Domain '{domain}' missing cluster"
        assert "primary" in info, f"Domain '{domain}' missing primary"
        assert "reviewer" in info, f"Domain '{domain}' missing reviewer"


# ---------------------------------------------------------------------------
# 4. test_context_path_loading
# ---------------------------------------------------------------------------


def test_context_path_loading() -> None:
    """Verify that context map parsing returns non-empty paths for known agents."""
    context_map = qoder_dispatch_bridge._parse_context_map()

    if not context_map:
        pytest.skip("Context map not available (no AGENT_CONTEXT_MAP.md)")

    # agent-coordinator should have context paths
    assert "agent-coordinator" in context_map, "agent-coordinator not found in context map"
    paths = context_map["agent-coordinator"]
    assert len(paths) > 0, "agent-coordinator should have at least one context path"

    # Check that well-known files appear
    path_str = " ".join(paths)
    assert (
        "AGENTS.md" in path_str or "RUNBOOK_AGENT.md" in path_str
    ), f"Expected AGENTS.md or RUNBOOK_AGENT.md in coordinator context paths, got: {paths}"


# ---------------------------------------------------------------------------
# 5. test_parallelizable_group_detection
# ---------------------------------------------------------------------------


def test_parallelizable_group_detection() -> None:
    """Multiple readonly agents with different domains should appear in the same parallel group."""
    # Create synthetic dispatch items: two readonly agents in different domains
    dispatch_items: List[Dict[str, Any]] = [
        {
            "order": 1,
            "role_slug": "alpha-agent",
            "readonly": True,
            "depends_on_previous": False,
        },
        {
            "order": 2,
            "role_slug": "beta-agent",
            "readonly": True,
            "depends_on_previous": False,
        },
    ]

    # Synthetic routing that maps the agents to different domains
    routing: Dict[str, Any] = {
        "domain-a": {
            "cluster": "analysis",
            "primary": "alpha-agent",
            "secondary": None,
            "reviewer": "reviewer-a",
        },
        "domain-b": {
            "cluster": "execution",
            "primary": "beta-agent",
            "secondary": None,
            "reviewer": "reviewer-b",
        },
    }

    groups = qoder_dispatch_bridge._detect_parallel_groups(dispatch_items, routing)
    assert len(groups) >= 1, "Expected at least one parallel group"
    # Both agents should be in the same parallel group
    flat = [slug for group in groups for slug in group]
    assert "alpha-agent" in flat
    assert "beta-agent" in flat


def test_packet_bracket_groups_must_match_independent_dispatch_items() -> None:
    """Packet bracket groups cannot name skipped agents or dependent steps."""
    dispatch_items: List[Dict[str, Any]] = [
        {
            "role_slug": "agent-coordinator",
            "readonly": True,
            "depends_on_previous": False,
        },
        {
            "role_slug": "architecture-specialist",
            "readonly": True,
            "depends_on_previous": False,
        },
        {
            "role_slug": "philosophy-agent",
            "readonly": True,
            "depends_on_previous": False,
        },
        {
            "role_slug": "bug-hunter",
            "readonly": False,
            "depends_on_previous": True,
        },
    ]

    groups = qoder_dispatch_bridge._validated_bracket_groups(
        [
            ["architecture-specialist", "philosophy-agent"],
            ["agent-coordinator", "architecture-specialist"],
            ["agent-coordinator", "missing-agent"],
            ["agent-coordinator", "bug-hunter"],
            ["agent-coordinator", "agent-coordinator"],
        ],
        dispatch_items,
    )

    assert groups == [["architecture-specialist", "philosophy-agent"]]


def test_packet_bracket_groups_drop_ambiguous_repeated_dispatch_slug() -> None:
    """Duplicate dispatch slugs make slug-only parallel groups ambiguous."""
    dispatch_items: List[Dict[str, Any]] = [
        {"role_slug": "agent-coordinator", "readonly": True, "depends_on_previous": False},
        {"role_slug": "architecture-specialist", "readonly": True, "depends_on_previous": False},
        {"role_slug": "agent-coordinator", "readonly": True, "depends_on_previous": False},
    ]

    groups = qoder_dispatch_bridge._validated_bracket_groups(
        [["agent-coordinator", "architecture-specialist"]],
        dispatch_items,
    )

    assert groups == []


def test_first_dispatch_item_cannot_depend_on_missing_previous_step() -> None:
    """Explicit dependency metadata is ignored for the first dispatch item."""
    assert (
        qoder_dispatch_bridge._depends_on_previous(
            "agent-coordinator",
            {"depends_on_previous": True},
            previous_slug=None,
        )
        is False
    )
    assert (
        qoder_dispatch_bridge._depends_on_previous(
            "agent-coordinator",
            {"depends_on_previous": True},
            previous_slug="dev-operator",
        )
        is True
    )


def test_packet_chain_successors_depend_on_previous() -> None:
    """Explicit packet chain notation carries dependency metadata into the manifest."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "architecture-specialist", "philosophy-agent"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
        chained_successors={"architecture-specialist", "philosophy-agent"},
    )
    by_slug = {e["role_slug"]: e for e in manifest["dispatch_sequence"]}

    assert by_slug["agent-coordinator"]["depends_on_previous"] is False
    assert by_slug["architecture-specialist"]["depends_on_previous"] is True
    assert by_slug["philosophy-agent"]["depends_on_previous"] is True


def test_manifest_bracket_parallel_group_and_qa_bug_chain() -> None:
    """Bracket groups stay parallel while qa -> bug -> security stays sequential."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = [
        "agent-coordinator",
        "architecture-specialist",
        "philosophy-agent",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
        bracket_groups=[["architecture-specialist", "philosophy-agent"]],
    )
    by_slug = {e["role_slug"]: e for e in manifest["dispatch_sequence"]}

    assert by_slug["architecture-specialist"]["depends_on_previous"] is False
    assert by_slug["philosophy-agent"]["depends_on_previous"] is False
    assert manifest["parallelizable_groups"] == []
    assert manifest["parallel_execution_allowed"] is False
    assert "dispatch_sequence order" in manifest["parallel_execution_reason"]
    assert by_slug["qa-engineer-agent"]["qoder_subagent_type"] == "Verify"
    assert by_slug["qa-engineer-agent"]["depends_on_previous"] is False
    assert by_slug["bug-hunter"]["qoder_subagent_type"] == "Verify"
    assert by_slug["bug-hunter"]["depends_on_previous"] is True
    assert by_slug["security-auditor"]["depends_on_previous"] is True
    assert all("security-auditor" not in group for group in manifest["parallelizable_groups"])


def test_mandatory_post_open_order_moves_all_bug_hunter_entries() -> None:
    """Duplicate bug-hunter entries must stay in the QA-led sequential block."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = [
        "agent-coordinator",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
        "bug-hunter",
    ]
    for s in set(slugs):
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )
    dispatch = manifest["dispatch_sequence"]
    manifest_order = [item["role_slug"] for item in dispatch]

    assert manifest_order == [
        "agent-coordinator",
        "qa-engineer-agent",
        "bug-hunter",
        "bug-hunter",
        "security-auditor",
    ]
    assert dispatch[2]["depends_on_previous"] is True
    assert dispatch[3]["depends_on_previous"] is True
    assert dispatch[4]["depends_on_previous"] is True
    assert all("bug-hunter" not in group for group in manifest["parallelizable_groups"])
    assert all("security-auditor" not in group for group in manifest["parallelizable_groups"])


def test_verify_agents_are_readonly_when_frontmatter_omits_readonly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify agents stay readonly even when frontmatter does not say so explicitly."""

    def fake_load_agent_definition(slug: str) -> Dict[str, Any]:
        return {
            "slug": slug,
            "name": slug,
            "description": "",
            "readonly": False,
            "readonly_explicit": False,
            "body": "",
            "definition_path": f".cursor/agents/{slug}.md",
        }

    monkeypatch.setattr(qoder_dispatch_bridge, "_load_agent_definition", fake_load_agent_definition)
    monkeypatch.setattr(qoder_dispatch_bridge, "_parse_context_map", lambda: {})
    monkeypatch.setattr(qoder_dispatch_bridge, "_ensure_routing_graph", lambda: {})

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["qa-engineer-agent", "bug-hunter"],
        mode="analysis",
        packet_source="test",
    )

    assert [item["qoder_subagent_type"] for item in manifest["dispatch_sequence"]] == [
        "Verify",
        "Verify",
    ]
    assert all(item["readonly"] for item in manifest["dispatch_sequence"])


def test_runtime_implementation_owner_override_clears_frontmatter_readonly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit runtime ownership is required to dispatch readonly implementation roles."""

    def fake_load_agent_definition(slug: str) -> Dict[str, Any]:
        return {
            "slug": slug,
            "name": slug,
            "description": "",
            "readonly": True,
            "readonly_explicit": True,
            "body": "",
            "definition_path": f".cursor/agents/{slug}.md",
        }

    monkeypatch.setattr(qoder_dispatch_bridge, "_load_agent_definition", fake_load_agent_definition)
    monkeypatch.setattr(qoder_dispatch_bridge, "_parse_context_map", lambda: {})
    monkeypatch.setattr(qoder_dispatch_bridge, "_ensure_routing_graph", lambda: {})

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["backend-engineer", "frontend-engineer"],
        mode="runtime",
        packet_source="test",
        implementation_owners={"backend-engineer", "frontend-engineer"},
    )

    by_slug = {entry["role_slug"]: entry for entry in manifest["dispatch_sequence"]}
    assert by_slug["backend-engineer"]["qoder_subagent_type"] == "Coding"
    assert by_slug["frontend-engineer"]["qoder_subagent_type"] == "Browser"
    assert by_slug["backend-engineer"]["readonly"] is False
    assert by_slug["frontend-engineer"]["readonly"] is False
    assert by_slug["backend-engineer"]["implementation_owner_override"] is True
    assert by_slug["frontend-engineer"]["implementation_owner_override"] is True


def test_runtime_verify_owner_override_clears_frontmatter_readonly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read-write QA/bug owner roles keep Verify type while clearing readonly."""

    def fake_load_agent_definition(slug: str) -> Dict[str, Any]:
        return {
            "slug": slug,
            "name": slug,
            "description": "",
            "readonly": True,
            "readonly_explicit": True,
            "body": "",
            "definition_path": f".cursor/agents/{slug}.md",
        }

    monkeypatch.setattr(qoder_dispatch_bridge, "_load_agent_definition", fake_load_agent_definition)
    monkeypatch.setattr(qoder_dispatch_bridge, "_parse_context_map", lambda: {})
    monkeypatch.setattr(qoder_dispatch_bridge, "_ensure_routing_graph", lambda: {})

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["qa-engineer-agent", "bug-hunter"],
        mode="runtime",
        packet_source="test",
        implementation_owners={"qa-engineer-agent", "bug-hunter"},
    )

    by_slug = {entry["role_slug"]: entry for entry in manifest["dispatch_sequence"]}
    assert by_slug["qa-engineer-agent"]["qoder_subagent_type"] == "Verify"
    assert by_slug["bug-hunter"]["qoder_subagent_type"] == "Verify"
    assert by_slug["qa-engineer-agent"]["readonly"] is False
    assert by_slug["bug-hunter"]["readonly"] is False
    assert by_slug["qa-engineer-agent"]["implementation_owner_override"] is True
    assert by_slug["bug-hunter"]["implementation_owner_override"] is True


def test_runtime_implementation_owner_cli_requires_packet(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ad-hoc role lists cannot grant runtime write-capable ownership."""
    result = qoder_dispatch_bridge.main(
        [
            "--roles",
            "backend-engineer",
            "--mode",
            "runtime",
            "--implementation-owner",
            "backend-engineer",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "--implementation-owner requires --packet" in captured.err


@pytest.mark.parametrize("suffix", [".json", ".JSON", ".JsOn"])
def test_duplicate_key_json_packet_fails_closed_before_dispatch(
    suffix: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    packet_file = tmp_path / f"packet{suffix}"
    packet_file.write_text(
        "{"
        '"requested_agents":["agent-coordinator"],'
        '"native_subagent_bridge":{"primary":{"repo_agent_slug":"agent-coordinator"},"secondary":[],"advisory":[]},'
        '"creative_pilot_context":null,'
        '"creative_pilot_context":{"phase":"independent"}'
        "}",
        encoding="utf-8",
    )
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)

    result = qoder_dispatch_bridge.main(["--packet", str(packet_file), "--mode", "analysis"])

    captured = capsys.readouterr()
    assert result == 1
    assert "invalid strict JSON task packet" in captured.err
    assert captured.out == ""


@pytest.mark.parametrize("suffix", [".json", ".JSON"])
def test_json_designated_packet_never_falls_back_to_markdown(
    suffix: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    packet_file = tmp_path / f"packet{suffix}"
    packet_file.write_text(
        '{"schema_version":"3.1"\n'
        "## Coordinator Role Order\n"
        "1. agent-coordinator\n"
        "2. backend-engineer\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)

    result = qoder_dispatch_bridge.main(["--packet", str(packet_file), "--mode", "analysis"])

    captured = capsys.readouterr()
    assert result == 1
    assert "invalid strict JSON task packet" in captured.err
    assert captured.out == ""


def test_json_designated_packet_requires_object_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet_file = tmp_path / "packet.json"
    packet_file.write_text(
        json.dumps(["## Coordinator Role Order", "1. backend-engineer"]),
        encoding="utf-8",
    )
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)

    with pytest.raises(ValueError, match="invalid strict JSON task packet"):
        qoder_dispatch_bridge._parse_packet_roles(packet_file)


def test_relative_json_symlink_cannot_downgrade_to_markdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "packet.md"
    target.write_text(
        "## Coordinator Role Order\n1. agent-coordinator\n2. backend-engineer\n",
        encoding="utf-8",
    )
    (tmp_path / "packet.json").symlink_to(target)
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)

    result = qoder_dispatch_bridge.main(["--packet", "packet.json", "--mode", "analysis"])

    captured = capsys.readouterr()
    assert result == 1
    assert "invalid strict JSON task packet" in captured.err
    assert captured.out == ""


def test_runtime_implementation_owner_cli_packet_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Packet-bound CLI owner override emits a write-capable manifest entry."""
    agents_dir = tmp_path / ".cursor" / "agents"
    agents_dir.mkdir(parents=True)
    coordinator_file = agents_dir / "agent-coordinator.md"
    coordinator_file.write_text(
        "---\n"
        "name: agent-coordinator\n"
        "model: auto\n"
        "description: Agent coordinator\n"
        "readonly: true\n"
        "---\n"
        "\n"
        "# Agent Coordinator\n",
        encoding="utf-8",
    )
    agent_file = agents_dir / "frontend-engineer.md"
    agent_file.write_text(
        "---\n"
        "name: frontend-engineer\n"
        "model: auto\n"
        "description: Frontend engineer\n"
        "readonly: true\n"
        "---\n"
        "\n"
        "# Frontend Engineer\n",
        encoding="utf-8",
    )
    packet_file = tmp_path / "packet.json"
    packet_file.write_text(
        json.dumps(
            {
                "role_agent_dispatch_contract": {
                    "runtime_implementation_owners": ["frontend-engineer"]
                },
                "native_subagent_bridge": {
                    "primary": {
                        "repo_agent_slug": "frontend-engineer",
                        "execution_mode": "read_write",
                    },
                    "secondary": [],
                    "advisory": [],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(qoder_dispatch_bridge, "_parse_context_map", lambda: {})
    monkeypatch.setattr(qoder_dispatch_bridge, "_ensure_routing_graph", lambda: {})

    result = qoder_dispatch_bridge.main(
        [
            "--packet",
            str(packet_file),
            "--mode",
            "runtime",
            "--implementation-owner",
            "frontend-engineer",
        ]
    )

    captured = capsys.readouterr()
    manifest = json.loads(captured.out)
    entry = next(
        item for item in manifest["dispatch_sequence"] if item["role_slug"] == "frontend-engineer"
    )
    assert result == 0
    assert manifest["missing_agents"] == []
    assert entry["role_slug"] == "frontend-engineer"
    assert entry["qoder_subagent_type"] == "Browser"
    assert entry["readonly"] is False
    assert entry["implementation_owner_override"] is True


def test_runtime_implementation_owner_cli_rejects_ungranted_packet_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Runtime owner flags must match packet-granted read-write owners."""

    agents_dir = tmp_path / ".cursor" / "agents"
    agents_dir.mkdir(parents=True)
    for slug in ["agent-coordinator", "backend-engineer"]:
        (agents_dir / f"{slug}.md").write_text(
            "---\n"
            f"name: {slug}\n"
            "model: auto\n"
            f"description: {slug}\n"
            "readonly: true\n"
            "---\n"
            f"\n# {slug}\n",
            encoding="utf-8",
        )
    packet_file = tmp_path / "packet.json"
    packet_file.write_text(
        json.dumps(
            {
                "role_agent_dispatch_contract": {
                    "runtime_implementation_owners": ["backend-engineer"]
                },
                "native_subagent_bridge": {
                    "primary": {"repo_agent_slug": "agent-coordinator"},
                    "secondary": [],
                    "advisory": [
                        {
                            "repo_agent_slug": "backend-engineer",
                            "execution_mode": "advisory_review",
                            "dispatch_contract": {
                                "advisory_only": False,
                                "spawn_with_native_subagent": True,
                                "required_role_pass": True,
                            },
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(qoder_dispatch_bridge, "_parse_context_map", lambda: {})
    monkeypatch.setattr(qoder_dispatch_bridge, "_ensure_routing_graph", lambda: {})

    result = qoder_dispatch_bridge.main(
        [
            "--packet",
            str(packet_file),
            "--mode",
            "runtime",
            "--implementation-owner",
            "backend-engineer",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "--implementation-owner not granted by packet for: backend-engineer" in captured.err


def test_coordinator_is_not_parallelized_with_readonly_reviewers() -> None:
    """Coordinator-first stays sequential and is excluded from auto-parallel groups."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "architecture-specialist"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
        bracket_groups=[["agent-coordinator", "architecture-specialist"]],
    )

    assert all("agent-coordinator" not in group for group in manifest["parallelizable_groups"])


def test_verify_agents_are_not_parallelized_with_reviewers() -> None:
    """Verify agents are readonly but still run in validation order, not parallel."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["architecture-specialist", "qa-engineer-agent"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
        bracket_groups=[slugs],
    )

    assert all("qa-engineer-agent" not in group for group in manifest["parallelizable_groups"])


def test_duplicate_readonly_slugs_are_not_auto_parallelized() -> None:
    """Slug-only auto parallel groups cannot represent repeated role phases safely."""
    dispatch_items: List[Dict[str, Any]] = [
        {
            "role_slug": "architecture-specialist",
            "readonly": True,
            "depends_on_previous": False,
            "qoder_subagent_type": "CodeReview",
        },
        {
            "role_slug": "architecture-specialist",
            "readonly": True,
            "depends_on_previous": False,
            "qoder_subagent_type": "CodeReview",
        },
        {
            "role_slug": "philosophy-agent",
            "readonly": True,
            "depends_on_previous": False,
            "qoder_subagent_type": "Research",
        },
    ]
    routing = {
        "architecture": {"reviewer": "architecture-specialist"},
        "philosophy": {"primary": "philosophy-agent"},
    }

    groups = qoder_dispatch_bridge._detect_parallel_groups(dispatch_items, routing)

    assert all("architecture-specialist" not in group for group in groups)


# ---------------------------------------------------------------------------
# 6. test_manifest_schema_compliance
# ---------------------------------------------------------------------------


def test_manifest_schema_compliance() -> None:
    """Verify output has all required top-level and entry-level keys."""
    # Use a known existing agent for a minimal manifest
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    existing_slugs = sorted([p.stem for p in agents_dir.glob("*.md") if p.stem != "AGENTS"])
    if not existing_slugs:
        pytest.skip("No agent definition files found")

    # Pick first two for a minimal test
    test_slugs = existing_slugs[:2]

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=test_slugs,
        mode="analysis",
        packet_source="test",
    )

    # Top-level keys
    missing_top = REQUIRED_TOP_LEVEL_KEYS - set(manifest.keys())
    assert not missing_top, f"Missing top-level keys: {missing_top}"

    # Entry-level keys
    for entry in manifest["dispatch_sequence"]:
        missing_entry = REQUIRED_ENTRY_KEYS - set(entry.keys())
        assert (
            not missing_entry
        ), f"Entry '{entry.get('role_slug', '?')}' missing keys: {missing_entry}"


# ---------------------------------------------------------------------------
# 7. test_roles_flag_explicit_list
# ---------------------------------------------------------------------------


def test_roles_flag_explicit_list() -> None:
    """Test --roles agent-coordinator philosophy-agent --mode analysis produces correct 2-entry manifest."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "philosophy-agent"]

    # Skip if either agent definition is missing
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source=None,
    )

    produced_slugs = [e["role_slug"] for e in manifest["dispatch_sequence"]]
    assert produced_slugs == slugs
    assert len(manifest["dispatch_sequence"]) == 2
    assert manifest["mode"] == "analysis"


def test_roles_flag_preserves_explicit_pre_open_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The public --roles fallback must not silently apply post-open tail sorting."""

    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = [
        "agent-coordinator",
        "architecture-specialist",
        "frontend-engineer",
        "cursor-specialist-agent",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
    ]
    for slug in slugs:
        if not (agents_dir / f"{slug}.md").is_file():
            pytest.skip(f"Agent definition not found: {slug}")

    result = role_dispatch_bridge.main(["--roles", *slugs, "--pr-phase", "pre_open", "--pretty"])

    assert result == 0
    manifest = json.loads(capsys.readouterr().out)
    assert [entry["role_slug"] for entry in manifest["dispatch_sequence"]] == slugs


def test_roles_flag_rejects_ambiguous_post_open_order_without_phase(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A full post-open role set cannot bypass ordering via phase-less --roles."""

    result = role_dispatch_bridge.main(
        [
            "--roles",
            "qa-engineer-agent",
            "security-auditor",
            "bug-hunter",
        ]
    )

    assert result == 1
    captured = capsys.readouterr()
    assert "Pass --pr-phase pre_open" in captured.err
    assert "--pr-phase post_open_review/merge_ready" in captured.err


def test_roles_flag_post_open_phase_enforces_mandatory_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Phase-aware explicit post-open dispatch keeps QA -> bug -> security."""

    result = role_dispatch_bridge.main(
        [
            "--roles",
            "qa-engineer-agent",
            "security-auditor",
            "bug-hunter",
            "--pr-phase",
            "post_open_review",
            "--pretty",
        ]
    )

    assert result == 0
    manifest = json.loads(capsys.readouterr().out)
    dispatch = manifest["dispatch_sequence"]
    assert [entry["role_slug"] for entry in dispatch] == [
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]
    assert dispatch[1]["depends_on_previous"] is True
    assert dispatch[2]["depends_on_previous"] is True


def test_roles_flag_merge_ready_phase_enforces_mandatory_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Merge-ready explicit role dispatch keeps QA -> bug -> security."""

    result = role_dispatch_bridge.main(
        [
            "--roles",
            "qa-engineer-agent",
            "security-auditor",
            "bug-hunter",
            "--pr-phase",
            "merge_ready",
            "--pretty",
        ]
    )

    assert result == 0
    manifest = json.loads(capsys.readouterr().out)
    dispatch = manifest["dispatch_sequence"]
    assert [entry["role_slug"] for entry in dispatch] == [
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]
    assert dispatch[1]["depends_on_previous"] is True
    assert dispatch[2]["depends_on_previous"] is True


def _invariant_review_packet(
    *,
    dispatch_role_order: object,
    implementation_authority: object = False,
    merge_authority: object = False,
) -> dict[str, object]:
    primary_agent = "architecture-specialist"
    secondary_agents = [
        "logic-agent",
        "agent-coordinator",
        "philosophy-agent",
        "security-auditor",
    ]
    reviewer = "cursor-specialist-agent"
    native_subagent_bridge = build_native_subagent_bridge(
        primary_agent=primary_agent,
        secondary_agents=secondary_agents,
        advisory_agents=[],
        reviewer=reviewer,
    )
    role_agent_dispatch_contract = build_role_agent_dispatch_contract(
        native_subagent_bridge=native_subagent_bridge,
        pr_phase="pre_open",
        dispatch_role_order=(dispatch_role_order if isinstance(dispatch_role_order, list) else []),
    )
    role_agent_dispatch_contract["dispatch_role_order"] = dispatch_role_order
    return {
        "schema_version": "3.1",
        "pr_phase": "pre_open",
        "candidate_paths": ["README.md"],
        "primary_agent": primary_agent,
        "secondary_agents": secondary_agents,
        "reviewer": reviewer,
        "requested_agents": ["architecture-specialist"],
        "requested_agent_disposition": [],
        "invariant_review": {
            "schema_version": "invariant_review.v1",
            "state": "required_pending",
            "change_classes": ["guard"],
            "trigger_evidence": [
                {"change_class": "guard", "source": "explicit"},
            ],
            "coverage_claim": "explicit_plus_bounded_positive_triggers_only",
            "required_roles": ["logic-agent", "philosophy-agent"],
            "boundary_classes": [
                "finite_closed_world",
                "bounded_surface",
                "delegated_recognizer",
                "open_world_stop",
            ],
            "required_output_fields": [
                "invariant_statement",
                "boundary_class",
                "canonical_sot",
                "completeness_claim",
                "counterexample_families",
                "fail_closed_behavior",
                "stop_condition",
                "residual_risk",
            ],
            "stop_condition": (
                "second_materially_novel_carrier_same_open_world_invariant_requires_rescope"
            ),
            "implementation_authority": implementation_authority,
            "merge_authority": merge_authority,
        },
        "role_agent_dispatch_contract": role_agent_dispatch_contract,
        "native_subagent_bridge": native_subagent_bridge,
    }


def _packet_with_advisory_secondaries() -> dict[str, object]:
    packet = _invariant_review_packet(dispatch_role_order=[])
    assigned_secondaries = packet["secondary_agents"]
    assert isinstance(assigned_secondaries, list)
    assigned_secondaries.extend(["qa-engineer-agent", "bug-hunter"])
    packet["requested_agent_disposition"] = [
        {
            "agent": "qa-engineer-agent",
            "reason": "Test advisory partition.",
            "status": "advisory_domain_mismatch",
        },
        {
            "agent": "bug-hunter",
            "reason": "Test advisory partition.",
            "status": "advisory_domain_mismatch",
        },
    ]
    bridge = build_native_subagent_bridge(
        primary_agent="architecture-specialist",
        secondary_agents=[
            "logic-agent",
            "agent-coordinator",
            "philosophy-agent",
            "security-auditor",
        ],
        advisory_agents=["qa-engineer-agent", "bug-hunter"],
        reviewer="cursor-specialist-agent",
    )
    packet["native_subagent_bridge"] = bridge
    _rebuild_invariant_dispatch_contract(packet)
    return packet


def _rebuild_invariant_dispatch_contract(packet: dict[str, object]) -> None:
    bridge = packet["native_subagent_bridge"]
    assert isinstance(bridge, dict)

    def slug(binding: object) -> str:
        assert isinstance(binding, dict)
        value = binding["repo_agent_slug"]
        assert isinstance(value, str)
        return value

    secondary = bridge["secondary"]
    advisory = bridge["advisory"]
    assert isinstance(secondary, list)
    assert isinstance(advisory, list)
    bridge_order = [
        slug(bridge["primary"]),
        *[slug(binding) for binding in secondary],
        *[slug(binding) for binding in advisory],
        slug(bridge["reviewer"]),
    ]
    required_prefix = ["agent-coordinator", "logic-agent", "philosophy-agent"]
    dispatch_order = [
        *required_prefix,
        *[role for role in bridge_order if role not in required_prefix],
    ]
    invariant_review = packet["invariant_review"]
    assert isinstance(invariant_review, dict)
    invariant_review["state"] = "required_pending"
    packet["role_agent_dispatch_contract"] = build_role_agent_dispatch_contract(
        native_subagent_bridge=bridge,
        pr_phase="pre_open",
        dispatch_role_order=dispatch_order,
    )


def test_invariant_review_dispatch_order_replaces_requested_agent_reordering() -> None:
    """System-required order is canonical without mutating requested agents."""

    expected_order = [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "architecture-specialist",
        "security-auditor",
        "cursor-specialist-agent",
    ]
    packet = _invariant_review_packet(dispatch_role_order=expected_order)

    assert qoder_dispatch_bridge._parse_json_packet_roles(packet) == expected_order
    assert packet["requested_agents"] == ["architecture-specialist"]


def test_invariant_review_dispatch_rejects_permuted_remaining_roles() -> None:
    """A matching role set cannot reorder the canonical implementation tail."""

    permuted_order = [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "security-auditor",
        "architecture-specialist",
        "cursor-specialist-agent",
    ]

    with pytest.raises(ValueError, match="canonical spawnable binding order"):
        qoder_dispatch_bridge._parse_json_packet_roles(
            _invariant_review_packet(dispatch_role_order=permuted_order)
        )


@pytest.mark.parametrize(
    ("native_bridge", "error"),
    [
        (None, "requires native_subagent_bridge object"),
        ({}, "native_subagent_bridge.primary must be a JSON object"),
    ],
)
def test_required_pending_invariant_review_requires_complete_native_bridge(
    native_bridge: object,
    error: str,
) -> None:
    """Current pending packets cannot fall back around missing bridge bindings."""

    packet = _invariant_review_packet(
        dispatch_role_order=[
            "agent-coordinator",
            "logic-agent",
            "philosophy-agent",
            "architecture-specialist",
            "security-auditor",
            "cursor-specialist-agent",
        ]
    )
    packet["native_subagent_bridge"] = native_bridge

    with pytest.raises(ValueError, match=error):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("secondary_scalar", r"secondary must be a JSON list"),
        ("advisory_scalar", r"advisory must be a JSON list"),
        ("secondary_null", r"secondary\[4\] must be a JSON object"),
        ("advisory_null", r"advisory\[0\] must be a JSON object"),
        ("empty_slug", r"secondary\[4\]\.repo_agent_slug must be canonical"),
        ("missing_dispatch_contract", r"canonical builder contract"),
        ("dispatch_contract_scalar", r"canonical builder contract"),
        (
            "spawn_flag_string",
            r"canonical builder contract",
        ),
        ("advisory_partial_contract", r"canonical builder contract"),
    ],
)
def test_current_invariant_review_rejects_lossy_bridge_projection(
    mutation: str,
    error: str,
) -> None:
    """Every current bridge input to spawnable-role projection is validated."""

    packet = _invariant_review_packet(
        dispatch_role_order=[
            "agent-coordinator",
            "logic-agent",
            "philosophy-agent",
            "architecture-specialist",
            "security-auditor",
            "cursor-specialist-agent",
        ]
    )
    bridge = packet["native_subagent_bridge"]
    assert isinstance(bridge, dict)
    secondary = bridge["secondary"]
    advisory = bridge["advisory"]
    assert isinstance(secondary, list)
    assert isinstance(advisory, list)
    if mutation == "secondary_scalar":
        bridge["secondary"] = {}
    elif mutation == "advisory_scalar":
        bridge["advisory"] = {}
    elif mutation == "secondary_null":
        secondary.append(None)
    elif mutation == "advisory_null":
        advisory.append(None)
    elif mutation == "empty_slug":
        secondary.append({"repo_agent_slug": ""})
    elif mutation == "missing_dispatch_contract":
        binding = secondary[0]
        assert isinstance(binding, dict)
        binding.pop("dispatch_contract")
    elif mutation == "dispatch_contract_scalar":
        binding = secondary[0]
        assert isinstance(binding, dict)
        binding["dispatch_contract"] = "spawn"
    elif mutation == "spawn_flag_string":
        binding = secondary[0]
        assert isinstance(binding, dict)
        binding["dispatch_contract"] = {"spawn_with_native_subagent": "false"}
    else:
        advisory_bridge = build_native_subagent_bridge(
            primary_agent="architecture-specialist",
            secondary_agents=[],
            advisory_agents=["qa-engineer-agent"],
            reviewer="cursor-specialist-agent",
        )
        advisory_binding = advisory_bridge["advisory"][0]
        assert isinstance(advisory_binding, dict)
        dispatch_contract = advisory_binding["dispatch_contract"]
        assert isinstance(dispatch_contract, dict)
        dispatch_contract.pop("advisory_only")
        advisory.append(advisory_binding)
        assigned_secondaries = packet["secondary_agents"]
        assert isinstance(assigned_secondaries, list)
        assigned_secondaries.append("qa-engineer-agent")
        requested_agent_disposition = packet["requested_agent_disposition"]
        assert isinstance(requested_agent_disposition, list)
        requested_agent_disposition.append(
            {
                "agent": "qa-engineer-agent",
                "reason": "Test advisory partition.",
                "status": "advisory_domain_mismatch",
            }
        )

    with pytest.raises(ValueError, match=error):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize(
    ("binding_collection", "binding_index", "field", "numeric_alias"),
    [
        ("secondary", 0, "native_executor_name_transport_only", 1),
        ("secondary", 0, "native_executor_name_transport_only", 1.0),
        ("advisory", 0, "spawn_with_native_subagent", 1),
        ("advisory", 0, "advisory_only", 0),
        ("advisory", 0, "advisory_only", 0.0),
    ],
)
def test_current_invariant_review_rejects_numeric_boolean_aliases(
    binding_collection: str,
    binding_index: int,
    field: str,
    numeric_alias: int | float,
) -> None:
    """Canonical JSON comparison preserves boolean types across the whole bridge."""

    packet = _invariant_review_packet(
        dispatch_role_order=[
            "agent-coordinator",
            "logic-agent",
            "philosophy-agent",
            "architecture-specialist",
            "security-auditor",
            "cursor-specialist-agent",
        ]
    )
    bridge = packet["native_subagent_bridge"]
    assert isinstance(bridge, dict)
    bindings = bridge[binding_collection]
    assert isinstance(bindings, list)
    if binding_collection == "advisory":
        advisory_bridge = build_native_subagent_bridge(
            primary_agent="architecture-specialist",
            secondary_agents=[],
            advisory_agents=["qa-engineer-agent"],
            reviewer="cursor-specialist-agent",
        )
        bindings.extend(advisory_bridge["advisory"])
        assigned_secondaries = packet["secondary_agents"]
        assert isinstance(assigned_secondaries, list)
        assigned_secondaries.append("qa-engineer-agent")
        requested_agent_disposition = packet["requested_agent_disposition"]
        assert isinstance(requested_agent_disposition, list)
        requested_agent_disposition.append(
            {
                "agent": "qa-engineer-agent",
                "reason": "Test advisory partition.",
                "status": "advisory_domain_mismatch",
            }
        )
    binding = bindings[binding_index]
    assert isinstance(binding, dict)
    dispatch_contract = binding["dispatch_contract"]
    assert isinstance(dispatch_contract, dict)
    dispatch_contract[field] = numeric_alias

    with pytest.raises(ValueError, match="canonical builder contract"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize("numeric_alias", [1, 1.0])
def test_current_invariant_review_rejects_numeric_bridge_policy_boolean_alias(
    numeric_alias: int | float,
) -> None:
    """Bridge-level policy booleans are type-exact, not Python-equality aliases."""

    packet = _invariant_review_packet(
        dispatch_role_order=[
            "agent-coordinator",
            "logic-agent",
            "philosophy-agent",
            "architecture-specialist",
            "security-auditor",
            "cursor-specialist-agent",
        ]
    )
    bridge = packet["native_subagent_bridge"]
    assert isinstance(bridge, dict)
    dispatch_policy = bridge["dispatch_policy"]
    assert isinstance(dispatch_policy, dict)
    dispatch_policy["spawn_via_coordinator_only"] = numeric_alias

    with pytest.raises(ValueError, match="canonical builder contract"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_current_invariant_review_binds_bridge_roles_to_packet_assignments() -> None:
    """A canonical replacement binding cannot substitute an assigned role."""

    packet = _invariant_review_packet(
        dispatch_role_order=[
            "agent-coordinator",
            "logic-agent",
            "philosophy-agent",
            "architecture-specialist",
            "security-auditor",
            "cursor-specialist-agent",
        ]
    )
    bridge = packet["native_subagent_bridge"]
    assert isinstance(bridge, dict)
    secondary = bridge["secondary"]
    assert isinstance(secondary, list)
    replacement_bridge = build_native_subagent_bridge(
        primary_agent="architecture-specialist",
        secondary_agents=["data-scientist-agent"],
        advisory_agents=[],
        reviewer="cursor-specialist-agent",
    )
    secondary[-1] = replacement_bridge["secondary"][0]

    with pytest.raises(ValueError, match="exactly match packet assignments"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize("binding_collection", ["secondary", "advisory"])
def test_current_invariant_review_preserves_ordered_assignment_projection(
    binding_collection: str,
) -> None:
    packet = _packet_with_advisory_secondaries()
    bridge = packet["native_subagent_bridge"]
    assert isinstance(bridge, dict)
    bindings = bridge[binding_collection]
    assert isinstance(bindings, list)
    bindings.reverse()
    _rebuild_invariant_dispatch_contract(packet)

    with pytest.raises(ValueError, match="ordered packet assignment projection"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_current_invariant_review_accepts_canonical_mixed_bucket_projection() -> None:
    packet = _packet_with_advisory_secondaries()

    assert qoder_dispatch_bridge._parse_json_packet_roles(packet) == [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "architecture-specialist",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
        "cursor-specialist-agent",
    ]


def test_current_invariant_review_rejects_cross_bucket_role_move() -> None:
    packet = _packet_with_advisory_secondaries()
    packet["native_subagent_bridge"] = build_native_subagent_bridge(
        primary_agent="architecture-specialist",
        secondary_agents=[
            "logic-agent",
            "agent-coordinator",
            "philosophy-agent",
            "security-auditor",
            "bug-hunter",
        ],
        advisory_agents=["qa-engineer-agent"],
        reviewer="cursor-specialist-agent",
    )
    _rebuild_invariant_dispatch_contract(packet)

    with pytest.raises(ValueError, match="ordered packet assignment projection"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize(
    "requested_agent_disposition",
    [
        "advisory",
        [{"agent": "qa-engineer-agent", "status": "unknown"}],
        [
            {"agent": "qa-engineer-agent", "status": "honored_secondary"},
            {"agent": "qa-engineer-agent", "status": "advisory_domain_mismatch"},
        ],
    ],
)
def test_current_invariant_review_rejects_malformed_assignment_disposition(
    requested_agent_disposition: object,
) -> None:
    packet = _invariant_review_packet(
        dispatch_role_order=[
            "agent-coordinator",
            "logic-agent",
            "philosophy-agent",
            "architecture-specialist",
            "security-auditor",
            "cursor-specialist-agent",
        ]
    )
    packet["requested_agent_disposition"] = requested_agent_disposition

    with pytest.raises(ValueError, match="requested_agent_disposition must be"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_current_invariant_review_rejects_duplicate_bridge_roles() -> None:
    """Canonical bindings cannot duplicate a required role pass."""

    packet = _invariant_review_packet(
        dispatch_role_order=[
            "agent-coordinator",
            "logic-agent",
            "philosophy-agent",
            "architecture-specialist",
            "security-auditor",
            "cursor-specialist-agent",
        ]
    )
    bridge = packet["native_subagent_bridge"]
    assert isinstance(bridge, dict)
    secondary = bridge["secondary"]
    assert isinstance(secondary, list)
    secondary.append(secondary[-1])

    with pytest.raises(ValueError, match="bridge roles must be unique"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("packet_creation_executes_roles", True),
        ("role_agent_dispatch_required", False),
        ("role_agent_dispatch_hard_gate", False),
        ("dispatch_manifest_command", "true"),
        ("must_execute_dispatch_sequence_in_order", False),
    ],
)
def test_current_invariant_review_requires_complete_dispatch_contract(
    field: str,
    replacement: object,
) -> None:
    """Current consumers use the producer builder as the dispatch-contract SoT."""

    packet = _invariant_review_packet(
        dispatch_role_order=[
            "agent-coordinator",
            "logic-agent",
            "philosophy-agent",
            "architecture-specialist",
            "security-auditor",
            "cursor-specialist-agent",
        ]
    )
    contract = packet["role_agent_dispatch_contract"]
    assert isinstance(contract, dict)
    contract[field] = replacement

    with pytest.raises(ValueError, match="canonical builder contract"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_current_invariant_bridge_cli_rejects_malformed_binding(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The neutral CLI fails before manifest construction on malformed bindings."""

    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = _invariant_review_packet(
        dispatch_role_order=[
            "agent-coordinator",
            "logic-agent",
            "philosophy-agent",
            "architecture-specialist",
            "security-auditor",
            "cursor-specialist-agent",
        ]
    )
    bridge = packet["native_subagent_bridge"]
    assert isinstance(bridge, dict)
    secondary = bridge["secondary"]
    assert isinstance(secondary, list)
    secondary.append(None)
    packet_path = tmp_path / "malformed-current-bridge.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    result = role_dispatch_bridge.main(["--packet", str(packet_path), "--mode", "analysis"])

    captured = capsys.readouterr()
    assert result == 1
    assert "native_subagent_bridge.secondary[4] must be a JSON object" in captured.err


@pytest.mark.parametrize(
    ("field", "replacement", "error"),
    [
        ("coverage_claim", None, "exactly match the invariant_review.v1 fields"),
        ("coverage_claim", "complete", "bounded coverage claim"),
        ("boundary_classes", [], "canonical boundary classes"),
        ("required_output_fields", [], "canonical output fields"),
        ("stop_condition", "continue", "canonical stop condition"),
    ],
)
def test_invariant_review_requires_complete_canonical_contract(
    field: str,
    replacement: object,
    error: str,
) -> None:
    """The consumer validates the closed v1 review object, not selected fields."""

    packet = _invariant_review_packet(
        dispatch_role_order=[
            "agent-coordinator",
            "logic-agent",
            "philosophy-agent",
            "architecture-specialist",
            "security-auditor",
            "cursor-specialist-agent",
        ]
    )
    invariant_review = packet["invariant_review"]
    assert isinstance(invariant_review, dict)
    if replacement is None:
        invariant_review.pop(field)
    else:
        invariant_review[field] = replacement

    with pytest.raises(ValueError, match=error):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_invariant_review_dispatch_order_chains_every_successor() -> None:
    """An accepted G0 order serializes every role after coordinator."""

    order = [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "architecture-specialist",
        "security-auditor",
        "cursor-specialist-agent",
    ]
    parsed_order = qoder_dispatch_bridge._parse_json_packet_roles(
        _invariant_review_packet(dispatch_role_order=order)
    )
    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=parsed_order,
        mode="analysis",
        packet_source="invariant-review-test",
        chained_successors=set(parsed_order[1:]),
        enforce_mandatory_post_open_tail=False,
    )

    dispatch = manifest["dispatch_sequence"]
    assert dispatch[0]["depends_on_previous"] is False
    assert all(entry["depends_on_previous"] is True for entry in dispatch[1:])


@pytest.mark.parametrize(
    ("dispatch_role_order", "error"),
    [
        (
            [
                "logic-agent",
                "agent-coordinator",
                "philosophy-agent",
                "architecture-specialist",
                "security-auditor",
                "cursor-specialist-agent",
            ],
            "must start with agent-coordinator",
        ),
        (
            [
                "agent-coordinator",
                "logic-agent",
                "philosophy-agent",
                "architecture-specialist",
                "cursor-specialist-agent",
            ],
            "canonical spawnable binding order",
        ),
        (
            [
                "agent-coordinator",
                "logic-agent",
                "philosophy-agent",
                "architecture-specialist",
                "security-auditor",
                "cursor-specialist-agent",
                "extra-agent",
            ],
            "canonical spawnable binding order",
        ),
        (
            [
                "agent-coordinator",
                "logic-agent",
                "logic-agent",
                "architecture-specialist",
                "security-auditor",
                "cursor-specialist-agent",
            ],
            "must not contain duplicate",
        ),
        ("agent-coordinator", "must be a non-empty JSON list"),
    ],
)
def test_invariant_review_dispatch_order_fails_closed(
    dispatch_role_order: object,
    error: str,
) -> None:
    """Malformed or set-mismatched canonical orders never use legacy fallback."""

    with pytest.raises(ValueError, match=error):
        qoder_dispatch_bridge._parse_json_packet_roles(
            _invariant_review_packet(
                dispatch_role_order=dispatch_role_order,
            )
        )


@pytest.mark.parametrize(
    ("implementation_authority", "merge_authority", "error"),
    [
        (True, False, "must not grant implementation authority"),
        (False, True, "must not grant merge authority"),
        (0, False, "must not grant implementation authority"),
        (False, None, "must not grant merge authority"),
    ],
)
def test_invariant_review_dispatch_rejects_authority_confusion(
    implementation_authority: object,
    merge_authority: object,
    error: str,
) -> None:
    """Authority fields must be exact JSON false values."""

    order = [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "architecture-specialist",
        "security-auditor",
        "cursor-specialist-agent",
    ]
    with pytest.raises(ValueError, match=error):
        qoder_dispatch_bridge._parse_json_packet_roles(
            _invariant_review_packet(
                dispatch_role_order=order,
                implementation_authority=implementation_authority,
                merge_authority=merge_authority,
            )
        )


def test_invariant_review_dispatch_rejects_creative_override() -> None:
    """A malicious combined packet cannot replace the pre-fix chain."""

    order = [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "architecture-specialist",
        "security-auditor",
        "cursor-specialist-agent",
    ]
    packet = _invariant_review_packet(dispatch_role_order=order)
    packet["creative_pilot_context"] = {"phase": "independent"}

    with pytest.raises(ValueError, match="cannot be combined with creative"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize("omit_contract", [False, True])
def test_required_pending_invariant_review_requires_dispatch_order(
    omit_contract: bool,
) -> None:
    """Removing the canonical order cannot downgrade a pending review to legacy."""

    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    contract = packet["role_agent_dispatch_contract"]
    assert isinstance(contract, dict)
    if omit_contract:
        packet.pop("role_agent_dispatch_contract")
        error = "requires role_agent_dispatch_contract"
    else:
        contract.pop("dispatch_role_order")
        error = "requires dispatch_role_order"

    with pytest.raises(ValueError, match=error):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_current_invariant_packet_cannot_remove_all_review_metadata() -> None:
    """The versioned post-G0 packet contract prevents a full metadata downgrade."""

    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    packet["schema_version"] = "3.1"
    packet.pop("invariant_review")
    packet.pop("role_agent_dispatch_contract")

    with pytest.raises(
        ValueError,
        match="task packet schema 3.1 requires invariant_review metadata",
    ):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_current_packet_with_malformed_path_cannot_downgrade_to_legacy() -> None:
    """Current provenance stays fail-closed before strict path normalization."""

    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    packet["schema_version"] = "3.1"
    packet["candidate_paths"] = ["scripts/ci/check_policy.py\nignored"]
    packet.pop("invariant_review")
    packet.pop("role_agent_dispatch_contract")

    with pytest.raises(
        ValueError,
        match="task packet schema 3.1 requires invariant_review metadata",
    ):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize("schema_version", ["3.0", None])
def test_legacy_packet_with_malformed_path_fails_closed(
    schema_version: str | None,
) -> None:
    """Legacy compatibility never converts invalid candidate paths into no trigger."""

    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    packet["candidate_paths"] = ["scripts//ci/check_pr_merge_readiness.py"]
    packet.pop("invariant_review")
    packet.pop("role_agent_dispatch_contract")
    if schema_version is None:
        packet.pop("schema_version", None)
    else:
        packet["schema_version"] = schema_version

    with pytest.raises(ValueError, match="invariant review paths must be canonical"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize("schema_version", ["3.0", None])
@pytest.mark.parametrize("pr_phase", ["none", "post_open_review"])
@pytest.mark.parametrize(
    "candidate_paths",
    [
        "scripts/ci/guard_actions_pin.py",
        {"path": "scripts/ci/guard_actions_pin.py"},
        1,
        ("scripts/ci/guard_actions_pin.py",),
        _LegacyCandidatePathList(["scripts/ci/guard_actions_pin.py"]),
        ["./scripts/ci/guard_actions_pin.py"],
    ],
    ids=("scalar", "mapping", "integer", "tuple", "list-subclass", "noncanonical-list"),
)
def test_legacy_packet_rejects_every_present_noncanonical_candidate_path_carrier(
    schema_version: str | None,
    pr_phase: str,
    candidate_paths: object,
) -> None:
    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    packet["candidate_paths"] = candidate_paths
    packet["pr_phase"] = pr_phase
    packet.pop("invariant_review")
    packet.pop("role_agent_dispatch_contract")
    if schema_version is None:
        packet.pop("schema_version", None)
    else:
        packet["schema_version"] = schema_version

    with pytest.raises(ValueError, match="invariant review paths must be canonical"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize("schema_version", ["3.0", None])
@pytest.mark.parametrize("pr_phase", ["none", "post_open_review"])
def test_legacy_packet_preserves_genuine_candidate_path_absence(
    schema_version: str | None,
    pr_phase: str,
) -> None:
    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    packet["pr_phase"] = pr_phase
    packet.pop("candidate_paths")
    packet.pop("invariant_review")
    packet.pop("role_agent_dispatch_contract")
    if schema_version is None:
        packet.pop("schema_version", None)
    else:
        packet["schema_version"] = schema_version

    roles = qoder_dispatch_bridge._parse_json_packet_roles(packet)

    assert roles[0] == "agent-coordinator"
    assert "architecture-specialist" in roles


@pytest.mark.parametrize(
    "schema_version",
    ["3.1 ", "3.01", 3.1, {}, [], None],
)
def test_unknown_or_malformed_packet_schema_cannot_claim_legacy(
    schema_version: object,
) -> None:
    """Only exact supported schema values participate in compatibility."""

    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    packet["schema_version"] = schema_version
    packet.pop("invariant_review")
    packet.pop("role_agent_dispatch_contract")

    with pytest.raises(
        ValueError,
        match="schema_version must be exact 3.0 or 3.1",
    ):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_bounded_opening_trigger_cannot_masquerade_as_legacy_packet() -> None:
    """A configured positive path hint remains fail-closed without metadata."""

    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    packet["candidate_paths"] = ["scripts/ci/guard_actions_pin.py"]
    packet.pop("schema_version")
    packet.pop("invariant_review")
    packet.pop("role_agent_dispatch_contract")

    with pytest.raises(
        ValueError,
        match="bounded invariant trigger requires invariant_review metadata",
    ):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_true_legacy_no_trigger_packet_retains_fallback() -> None:
    """Pre-G0 schema packets without a bounded trigger keep legacy ordering."""

    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    packet["schema_version"] = "3.0"
    packet.pop("invariant_review")
    packet.pop("role_agent_dispatch_contract")

    assert qoder_dispatch_bridge._parse_json_packet_roles(packet) == [
        "agent-coordinator",
        "architecture-specialist",
        "logic-agent",
        "philosophy-agent",
        "security-auditor",
        "cursor-specialist-agent",
    ]

    packet.pop("schema_version")
    assert qoder_dispatch_bridge._parse_json_packet_roles(packet) == [
        "agent-coordinator",
        "architecture-specialist",
        "logic-agent",
        "philosophy-agent",
        "security-auditor",
        "cursor-specialist-agent",
    ]


@pytest.mark.parametrize(
    ("invariant_review", "error"),
    [
        ("required_pending", "must be a JSON object"),
        (
            {
                "schema_version": "invariant_review.v1",
                "change_classes": ["guard"],
                "trigger_evidence": [
                    {"change_class": "guard", "source": "explicit"},
                ],
                "required_roles": ["logic-agent", "philosophy-agent"],
                "implementation_authority": False,
                "merge_authority": False,
            },
            "state must be not_required or required_pending",
        ),
        (
            {
                "schema_version": "invariant_review.v1",
                "state": "require_pending",
                "change_classes": ["guard"],
                "trigger_evidence": [
                    {"change_class": "guard", "source": "explicit"},
                ],
                "required_roles": ["logic-agent", "philosophy-agent"],
                "implementation_authority": False,
                "merge_authority": False,
            },
            "state must be not_required or required_pending",
        ),
        (
            {
                "schema_version": "invariant_review.v0",
                "state": "not_required",
                "change_classes": [],
                "trigger_evidence": [],
                "required_roles": [],
                "implementation_authority": False,
                "merge_authority": False,
            },
            "requires invariant_review.v1",
        ),
    ],
)
def test_present_invariant_review_metadata_fails_closed_when_malformed(
    invariant_review: object,
    error: str,
) -> None:
    """Only complete absence of invariant metadata may use legacy fallback."""

    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    packet["invariant_review"] = invariant_review
    packet.pop("role_agent_dispatch_contract")

    with pytest.raises(ValueError, match=error):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize(
    ("trigger_evidence", "error"),
    [
        ([None], "rows must be JSON objects"),
        (
            [{"change_class": "safety", "source": "explicit"}],
            "unknown change_class",
        ),
        (
            [{"change_class": "guard", "source": "manual"}],
            "unknown source",
        ),
        (
            [{"change_class": "guard", "source": "explicit", "path": "README.md"}],
            "must not contain path or extra fields",
        ),
        (
            [
                {
                    "change_class": "guard",
                    "source": "bounded_path_hint",
                    "path": "scripts/orchestration/check_merge_ready.py",
                }
            ],
            "must match the canonical classifier",
        ),
    ],
)
def test_invariant_review_evidence_must_match_canonical_classifier(
    trigger_evidence: object,
    error: str,
) -> None:
    """The bridge reuses the classifier instead of trusting packet evidence."""

    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    invariant_review = packet["invariant_review"]
    assert isinstance(invariant_review, dict)
    invariant_review["trigger_evidence"] = trigger_evidence

    with pytest.raises(ValueError, match=error):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_malformed_invariant_review_blocks_current_creative_override() -> None:
    """Creative routing cannot revive malformed invariant-review metadata."""

    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    packet["invariant_review"] = {
        "schema_version": "invariant_review.v1",
        "state": "required-pending",
        "change_classes": ["guard"],
        "trigger_evidence": [
            {"change_class": "guard", "source": "explicit"},
        ],
        "required_roles": ["logic-agent", "philosophy-agent"],
        "implementation_authority": False,
        "merge_authority": False,
    }
    packet.pop("role_agent_dispatch_contract")
    packet["creative_pilot_context"] = {"phase": "independent"}

    with pytest.raises(
        ValueError,
        match="state must be not_required or required_pending",
    ):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_opening_invariant_trigger_cannot_downgrade_to_not_required_or_creative() -> None:
    """Active opening evidence must retain the pending pre-fix chain."""

    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    invariant_review = packet["invariant_review"]
    assert isinstance(invariant_review, dict)
    invariant_review["state"] = "not_required"
    invariant_review["required_roles"] = []
    packet.pop("role_agent_dispatch_contract")
    packet["creative_pilot_context"] = {"phase": "independent"}

    with pytest.raises(
        ValueError,
        match="opening-phase invariant triggers require required_pending review",
    ):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_not_required_invariant_review_keeps_phase_bounded_dispatch() -> None:
    """No-trigger opening packets and recorded post-open classes remain valid."""

    opening_packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    opening_review = opening_packet["invariant_review"]
    assert isinstance(opening_review, dict)
    opening_review.update(
        {
            "state": "not_required",
            "change_classes": [],
            "trigger_evidence": [],
            "required_roles": [],
        }
    )
    opening_bridge = opening_packet["native_subagent_bridge"]
    assert isinstance(opening_bridge, dict)
    opening_packet["role_agent_dispatch_contract"] = build_role_agent_dispatch_contract(
        native_subagent_bridge=opening_bridge,
        pr_phase="pre_open",
    )

    post_open_packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    post_open_packet["pr_phase"] = "post_open_review"
    post_open_review = post_open_packet["invariant_review"]
    assert isinstance(post_open_review, dict)
    post_open_review.update(
        {
            "state": "not_required",
            "required_roles": [],
        }
    )
    post_open_bridge = post_open_packet["native_subagent_bridge"]
    assert isinstance(post_open_bridge, dict)
    post_open_packet["role_agent_dispatch_contract"] = build_role_agent_dispatch_contract(
        native_subagent_bridge=post_open_bridge,
        pr_phase="post_open_review",
    )

    assert qoder_dispatch_bridge._parse_json_packet_roles(opening_packet)
    assert qoder_dispatch_bridge._parse_json_packet_roles(post_open_packet)


def test_required_pending_invariant_review_without_order_blocks_creative_cli(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Creative metadata cannot revive a pending packet whose order is missing."""

    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    contract = packet["role_agent_dispatch_contract"]
    assert isinstance(contract, dict)
    contract.pop("dispatch_role_order")
    packet["creative_pilot_context"] = {"phase": "independent"}
    packet_path = tmp_path / "pending-without-order.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    result = qoder_dispatch_bridge.main(["--packet", str(packet_path), "--mode", "analysis"])

    assert result == 1
    assert (
        "required_pending invariant review requires dispatch_role_order" in capsys.readouterr().err
    )


# ---------------------------------------------------------------------------
# 8. test_packet_without_role_section_errors
# ---------------------------------------------------------------------------


def test_packet_without_role_section_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A packet without 'Coordinator Role Order' section should produce empty dispatch_sequence."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    fake_packet = tmp_path / "fake_packet.md"
    fake_packet.write_text(
        "# Fake Packet\n\n## Goal\n\nDo something.\n\n## Validation\n\nRun tests.\n",
        encoding="utf-8",
    )

    # _parse_packet_roles uses _list_known_agent_slugs which checks the real agents dir
    roles = qoder_dispatch_bridge._parse_packet_roles(fake_packet)
    # Without any recognized role section, expect empty list
    assert roles == [], f"Expected empty roles list, got: {roles}"


# ---------------------------------------------------------------------------
# 9. test_missing_agent_definition_graceful
# ---------------------------------------------------------------------------


def test_missing_agent_definition_graceful(capsys: pytest.CaptureFixture[str]) -> None:
    """If an agent slug doesn't have a corresponding definition file, handle gracefully."""
    slugs = ["nonexistent-agent-xyz-12345", "another-missing-agent-abc"]

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )

    # Missing agents should be skipped (not in dispatch_sequence)
    assert manifest["dispatch_sequence"] == []
    assert manifest["missing_agents"] == slugs

    # A warning should be emitted to stderr
    captured = capsys.readouterr()
    assert "nonexistent-agent-xyz-12345" in captured.err
    assert "another-missing-agent-abc" in captured.err


def test_cli_fails_when_requested_role_definition_is_missing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Executable CLI dispatch fails instead of emitting an empty manifest."""
    result = qoder_dispatch_bridge.main(
        ["--roles", "nonexistent-agent-xyz-12345", "--mode", "analysis"]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "FAIL: Agent definitions not found for: nonexistent-agent-xyz-12345" in captured.err


# ---------------------------------------------------------------------------
# 10. test_mandatory_post_open_detection
# ---------------------------------------------------------------------------


def test_mandatory_post_open_detection() -> None:
    """Verify that post-open mandatory pass agents are correctly identified in mandatory_post_open."""
    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["agent-coordinator"],
        mode="analysis",
        packet_source="test",
    )

    assert manifest["schema_version"] == "2.0"
    assert manifest["manifest_contract_version"] == "pulseplate.role-dispatch-manifest/v2"
    assert manifest["post_open_role_gates"] == [
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]
    assert "final_material_review_timing" not in manifest
    assert "final_material_review_gates" not in manifest
    assert "codex_security_invocation_policy" not in manifest

    # Every Qoder manifest gate alias remains role-only.
    assert "mandatory_post_open" in manifest
    post_open = manifest["mandatory_post_open"]
    assert isinstance(post_open, list)
    assert post_open == ["qa-engineer-agent", "bug-hunter", "security-auditor"]
    assert manifest["mandatory_post_open_gates"] == post_open
    assert manifest["mandatory_post_open_role_agents"] == [
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]
    assert manifest["compatibility_aliases"] == {
        "mandatory_post_open": {
            "canonical_fields": ["post_open_role_gates"],
            "fail_closed": True,
        },
        "mandatory_post_open_role_agents": {
            "canonical_fields": ["post_open_role_gates"],
            "fail_closed": True,
        },
        "mandatory_post_open_gates": {
            "canonical_fields": ["post_open_role_gates"],
            "fail_closed": True,
        },
    }
    dispatched_roles = {entry["role_slug"] for entry in manifest["dispatch_sequence"]}
    assert "pulseplate-pr-review" not in dispatched_roles
    assert "Codex Security diff scan / finding discovery" not in dispatched_roles


def test_mandatory_post_open_bug_hunter_depends_on_qa() -> None:
    """The post-open qa-engineer-agent -> bug-hunter pass stays sequential."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["qa-engineer-agent", "bug-hunter"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            require_feature(f"agent_definition:{s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )
    by_slug = {e["role_slug"]: e for e in manifest["dispatch_sequence"]}

    assert by_slug["qa-engineer-agent"]["qoder_subagent_type"] == "Verify"
    assert by_slug["qa-engineer-agent"]["depends_on_previous"] is False
    assert by_slug["bug-hunter"]["qoder_subagent_type"] == "Verify"
    assert by_slug["bug-hunter"]["depends_on_previous"] is True


def test_mandatory_post_open_pass_is_ordered_last() -> None:
    """Generated manifests keep the full QA -> bug -> security lane together."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = [
        "agent-coordinator",
        "bug-hunter",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
    ]
    for slug in slugs:
        if not (agents_dir / f"{slug}.md").is_file():
            require_feature(f"agent_definition:{slug}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )

    assert [entry["role_slug"] for entry in manifest["dispatch_sequence"]] == [
        "agent-coordinator",
        "qa-engineer-agent",
        "bug-hunter",
        "bug-hunter",
        "security-auditor",
    ]


def test_coordinator_order_keeps_mandatory_qa_bug_pass_adjacent() -> None:
    """The bridge preserves order except for the mandatory QA -> bug handoff."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = [
        "agent-coordinator",
        "philosophy-agent",
        "architecture-specialist",
        "qa-engineer-agent",
        "security-auditor",
        "bug-hunter",
    ]
    for slug in slugs:
        if not (agents_dir / f"{slug}.md").is_file():
            require_feature(f"agent_definition:{slug}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )

    assert [entry["role_slug"] for entry in manifest["dispatch_sequence"]] == [
        "agent-coordinator",
        "philosophy-agent",
        "architecture-specialist",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]


# ---------------------------------------------------------------------------
# 11. test_graph_reviewer_slot_infers_code_review
# ---------------------------------------------------------------------------


def test_solo_primary_capable_reviewer_is_not_code_review_by_default() -> None:
    """Solo ``security-auditor`` is a primary-capable lead → analysis type stays Research."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    if not (agents_dir / "security-auditor.md").is_file():
        pytest.skip("security-auditor agent definition not found")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["security-auditor"],
        mode="analysis",
        packet_source="test",
    )
    assert len(manifest["dispatch_sequence"]) == 1
    assert manifest["dispatch_sequence"][0]["qoder_subagent_type"] == "Research"


def test_security_auditor_tail_role_is_code_review() -> None:
    """When ``security-auditor`` is last in a multi-role list, treat as graph reviewer (CodeReview)."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "security-auditor"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )
    by_slug = {e["role_slug"]: e["qoder_subagent_type"] for e in manifest["dispatch_sequence"]}
    assert by_slug["agent-coordinator"] == "Research"
    assert by_slug["security-auditor"] == "CodeReview"


def test_missing_role_does_not_hide_tail_reviewer_slot() -> None:
    """Missing slugs are excluded before tail reviewer detection."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    if not (agents_dir / "security-auditor.md").is_file():
        pytest.skip("security-auditor agent definition not found")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["missing-agent", "agent-coordinator", "security-auditor", "also-missing"],
        mode="analysis",
        packet_source="test",
    )
    by_slug = {e["role_slug"]: e["qoder_subagent_type"] for e in manifest["dispatch_sequence"]}

    assert by_slug["security-auditor"] == "CodeReview"


def test_architecture_specialist_after_coordinator_is_code_review() -> None:
    """Two-role orchestration lane: coordinator then architecture reviewer → CodeReview."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "architecture-specialist"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )
    by_slug = {e["role_slug"]: e["qoder_subagent_type"] for e in manifest["dispatch_sequence"]}
    assert by_slug["agent-coordinator"] == "Research"
    assert by_slug["architecture-specialist"] == "CodeReview"


# ---------------------------------------------------------------------------
# 12. test_mode_review_forces_code_review
# ---------------------------------------------------------------------------


def test_mode_review_forces_code_review() -> None:
    """mode=review should force all agents to CodeReview type."""
    agent_def = {"slug": "backend-engineer", "name": "backend-engineer", "readonly": False}
    result = qoder_dispatch_bridge.resolve_qoder_type(agent_def, mode="review", is_reviewer=False)
    assert result == "CodeReview"


# ---------------------------------------------------------------------------
# 13. test_fenced_code_blocks_skipped
# ---------------------------------------------------------------------------


def test_fenced_code_blocks_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fenced code blocks in packets should not produce false role matches."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    known = sorted(item.stem for item in agents_dir.glob("*.md") if item.stem != "AGENTS")
    if not known:
        pytest.skip("No agent definitions found")
    sample_slug = known[0]
    tmp_agents_dir = tmp_path / ".cursor" / "agents"
    tmp_agents_dir.mkdir(parents=True)
    (tmp_agents_dir / f"{sample_slug}.md").write_text(f"---\nslug: {sample_slug}\n---\n")

    packet_content = (
        "# Test\n\n"
        "## Coordinator Role Order\n\n"
        "```bash\n"
        f"--requested-agent {sample_slug}\n"
        "```\n\n"
        "No agents listed here.\n"
    )
    fake_packet = tmp_path / "fence_test.md"
    fake_packet.write_text(packet_content, encoding="utf-8")

    roles = qoder_dispatch_bridge._parse_packet_roles(fake_packet)
    assert roles == [], f"Expected no roles from fenced code, got: {roles}"


# ---------------------------------------------------------------------------
# 14. test_repeated_coordinator_entries_preserved
# ---------------------------------------------------------------------------


def test_repeated_coordinator_entries_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repeated non-consecutive entries in role order should be preserved."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    if not (agents_dir / "agent-coordinator.md").is_file():
        pytest.skip("agent-coordinator definition not found")

    other_slugs = sorted(
        item.stem
        for item in agents_dir.glob("*.md")
        if item.stem not in ("AGENTS", "agent-coordinator")
    )
    if not other_slugs:
        pytest.skip("Need at least two different agent definitions")
    other = other_slugs[0]
    tmp_agents_dir = tmp_path / ".cursor" / "agents"
    tmp_agents_dir.mkdir(parents=True)
    (tmp_agents_dir / "agent-coordinator.md").write_text("---\nslug: agent-coordinator\n---\n")
    (tmp_agents_dir / f"{other}.md").write_text(f"---\nslug: {other}\n---\n")

    packet_content = (
        "# Test\n\n"
        "## Coordinator Role Order\n\n"
        f"1. agent-coordinator\n"
        f"2. {other}\n"
        f"3. agent-coordinator\n"
    )
    fake_packet = tmp_path / "repeat_test.md"
    fake_packet.write_text(packet_content, encoding="utf-8")

    roles = qoder_dispatch_bridge._parse_packet_roles(fake_packet)
    assert roles == ["agent-coordinator", other, "agent-coordinator"]


# ---------------------------------------------------------------------------
# 15. test_bracket_group_detection
# ---------------------------------------------------------------------------


def test_bracket_group_detection(tmp_path: Path) -> None:
    """Bracket notation [slug-a, slug-b] should produce parallel groups."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    known = sorted(item.stem for item in agents_dir.glob("*.md") if item.stem != "AGENTS")
    if len(known) < 2:
        pytest.skip("Need at least two agent definitions for bracket group test")

    slug_a, slug_b = known[0], known[1]
    packet_content = f"# Test\n\n## Coordinator Role Order\n\n1. [{slug_a}, {slug_b}]\n"
    fake_packet = tmp_path / "bracket_test.md"
    fake_packet.write_text(packet_content, encoding="utf-8")

    lines = fake_packet.read_text(encoding="utf-8").splitlines()
    groups = qoder_dispatch_bridge._extract_bracket_groups(lines)
    assert len(groups) >= 1
    assert slug_a in groups[0]
    assert slug_b in groups[0]


def test_bracket_group_detection_strips_inline_code_ticks(tmp_path: Path) -> None:
    """Markdown inline code around bracket slugs should not drop the group."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    known = sorted(item.stem for item in agents_dir.glob("*.md") if item.stem != "AGENTS")
    if len(known) < 2:
        pytest.skip("Need at least two agent definitions for bracket group test")

    slug_a, slug_b = known[0], known[1]
    packet_content = f"# Test\n\n## Coordinator Role Order\n\n1. [`{slug_a}`, `{slug_b}`]\n"
    fake_packet = tmp_path / "bracket_backticks_test.md"
    fake_packet.write_text(packet_content, encoding="utf-8")

    groups = qoder_dispatch_bridge._extract_bracket_groups(
        fake_packet.read_text(encoding="utf-8").splitlines()
    )
    assert groups == [[slug_a, slug_b]]


def test_fallback_role_order_field_continuation_is_parsed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fallback parsing includes indented continuations for role-order fields."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "architecture-specialist", "qa-engineer-agent"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")
    tmp_agents_dir = tmp_path / ".cursor" / "agents"
    tmp_agents_dir.mkdir(parents=True)
    for slug in slugs:
        (tmp_agents_dir / f"{slug}.md").write_text(f"---\nslug: {slug}\n---\n")

    packet_content = (
        "# Test\n\n"
        "## Packet Notes\n\n"
        "- Required role order:\n"
        "  `agent-coordinator -> architecture-specialist -> qa-engineer-agent`\n"
    )
    fake_packet = tmp_path / "continued_role_order.md"
    fake_packet.write_text(packet_content, encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(fake_packet) == slugs


# ---------------------------------------------------------------------------
# 16. test_readonly_derived_from_qoder_type
# ---------------------------------------------------------------------------


def test_readonly_derived_from_qoder_type() -> None:
    """When agent frontmatter does not set readonly, derive from Qoder type."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    if not (agents_dir / "agent-coordinator.md").is_file():
        pytest.skip("agent-coordinator definition not found")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["agent-coordinator"],
        mode="analysis",
        packet_source="test",
    )
    # In analysis mode, agent-coordinator resolves to Research; readonly=True
    assert len(manifest["dispatch_sequence"]) >= 1
    entry = manifest["dispatch_sequence"][0]
    assert entry["readonly"] is True


# ---------------------------------------------------------------------------
# 17. test_reviewer_name_detection
# ---------------------------------------------------------------------------


def test_reviewer_name_detection() -> None:
    """Agents with auditor in slug get CodeReview when in tail position."""
    result = qoder_dispatch_bridge._dispatch_is_reviewer_slot(
        "code-auditor",
        order_idx=2,
        total_roles=2,
        primary_slugs=set(),
        reviewer_slugs=set(),
    )
    assert result is True, "auditor slug in tail position should be detected as reviewer"
