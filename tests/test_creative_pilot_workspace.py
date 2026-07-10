from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_artifact_inventory as inventory
from scripts.orchestration import task_bootstrap
from scripts.orchestration.qoder_dispatch_bridge import build_dispatch_manifest
from scripts.orchestration.creative_hypothesis_spec_bridge_contract import (
    build_creative_pilot_spec_bridge_bundle,
)
from scripts.orchestration.creative_pilot_workspace_contract import (
    CreativePilotContractError,
    add_rebuttal_assignments,
    apply_synthesis_transition,
    build_approval_v2,
    build_context_map_v2,
    build_evidence_events,
    build_hypothesis_packet_v2,
    build_role_result,
    build_synthesis,
    build_target_manifest,
    build_workspace,
    complete_handoff,
    detect_conflicts,
    ingest_role_result,
    load_json_strict,
    phase_dispatch_fingerprint,
    route_roles,
    validate_hypothesis_packet_v2,
    validate_workspace,
)
from scripts.orchestration.experiment_runner_pr_creative_context_contract import (
    ExperimentRunnerCreativeContextContractError,
    validate_creative_protocol_context_map_versioned,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
GIT = shutil.which("git")
assert GIT is not None


def _sha() -> str:
    return subprocess.check_output(
        [GIT, "rev-parse", "origin/main"], cwd=REPO_ROOT, text=True
    ).strip()


def _chain() -> tuple[dict, dict, dict]:
    sha = _sha()
    target = build_target_manifest(
        base_sha=sha,
        head_sha=sha,
        paths=["core/rag/orchestration.py"],
        symbols=["RAGOrchestrationResult"],
        immutable_oracles=[
            "tests/test_rag_orchestration.py",
            "tests/test_rag_release_gates_runner.py",
        ],
    )
    context = build_context_map_v2(
        target_manifest=target,
        context_refs=["core/rag/contracts.py", "tests/test_rag_orchestration.py"],
    )
    packet = build_hypothesis_packet_v2(
        context_map=context,
        hypotheses=[
            {
                "hypothesis_id": "degraded-path-invariants",
                "statement": "Repeated degraded result construction may drift across RAG metadata invariants.",
                "mechanism": "A bounded deterministic construction seam could preserve degraded-path metadata without changing successful behavior.",
                "target_symbols": ["RAGOrchestrationResult"],
                "tests_or_oracles": ["tests/test_rag_orchestration.py"],
                "negative_controls": ["successful RAG output remains unchanged"],
                "tags": ["degraded", "verification", "provenance"],
            }
        ],
    )
    workspace = build_workspace(
        context_map=context,
        hypothesis_packet=packet,
        selected_hypothesis_id="degraded-path-invariants",
    )
    return context, packet, workspace


def _complete(workspace: dict, *, security_stance: str = "pass") -> dict:
    current = workspace
    for assignment in list(workspace["assignments"]):
        stance = security_stance if assignment["role"] == "security-auditor" else "pass"
        result = build_role_result(
            workspace=current,
            assignment_id=assignment["assignment_id"],
            stance=stance,
            claim_ids=["claim-degraded-invariants"],
            evidence_refs=["core/rag/orchestration.py"],
            blocker_codes=["security-boundary"] if stance == "reject" else [],
            oracle_gap_codes=[],
        )
        current = ingest_role_result(current, result)
    return detect_conflicts(current)


def _resign_workspace(workspace: dict) -> dict:
    updated = deepcopy(workspace)
    body = {
        key: value
        for key, value in updated.items()
        if key
        not in {"workspace_id", "intent_fingerprint", "revision_fingerprint", "idempotency_key"}
    }
    updated["revision_fingerprint"] = fingerprint_payload(body)
    return updated


def test_production_adjacent_target_binds_git_blob_and_symbols() -> None:
    context, _packet, _workspace = _chain()
    target = context["target_manifest"]
    assert target["files"][0]["path"] == "core/rag/orchestration.py"
    assert target["files"][0]["content_fingerprint"].startswith("sha256:")
    assert target["base_sha"] == target["head_sha"]
    assert {row["path"] for row in target["oracle_bindings"]} == set(target["immutable_oracles"])
    assert {row["path"] for row in context["context_bindings"]} == set(context["context_refs"])


def test_target_rejects_stale_head_and_untracked_context() -> None:
    stale = subprocess.check_output(
        [GIT, "rev-parse", "origin/main^"], cwd=REPO_ROOT, text=True
    ).strip()
    with pytest.raises(CreativePilotContractError, match="current origin/main"):
        build_target_manifest(
            base_sha=stale,
            head_sha=stale,
            paths=["core/rag/orchestration.py"],
            symbols=["RAGOrchestrationResult"],
            immutable_oracles=["tests/test_rag_orchestration.py"],
        )
    context, _packet, _workspace = _chain()
    with pytest.raises(CreativePilotContractError, match="tracked blob"):
        build_context_map_v2(
            target_manifest=context["target_manifest"],
            context_refs=["core/rag/does_not_exist.py"],
        )


def test_version_router_accepts_v2_without_v1_downgrade() -> None:
    context, _packet, _workspace = _chain()
    assert validate_creative_protocol_context_map_versioned(context) == context
    downgraded = deepcopy(context)
    downgraded["schema_version"] = "1.0"
    with pytest.raises(ExperimentRunnerCreativeContextContractError):
        validate_creative_protocol_context_map_versioned(downgraded)


@pytest.mark.parametrize(
    "path",
    [
        "app/main.py",
        "legacy_app.py",
        "app/routers/legacy_insight.py",
        ".github/workflows/ci.yml",
        "tests/test_rag_orchestration.py",
        "core/rag/",
        "core/rag/*.py",
    ],
)
def test_production_adjacent_target_rejects_forbidden_surfaces(path: str) -> None:
    with pytest.raises((CreativePilotContractError, ValueError)):
        build_target_manifest(
            base_sha=_sha(),
            head_sha=_sha(),
            paths=[path],
            symbols=["RAGOrchestrationResult"],
            immutable_oracles=["tests/test_rag_orchestration.py"],
        )


def test_hypothesis_selection_is_bounded_to_two_attempts() -> None:
    context, packet, _workspace = _chain()
    rows = []
    source = {
        key: value
        for key, value in packet["hypotheses"][0].items()
        if key not in {"attempt", "hypothesis_fingerprint"}
    }
    for index in range(3):
        row = deepcopy(source)
        row["hypothesis_id"] = f"attempt-{index}"
        rows.append(row)
    with pytest.raises(CreativePilotContractError, match="one or two"):
        build_hypothesis_packet_v2(context_map=context, hypotheses=rows)


def test_v2_hypothesis_validation_requires_bound_context() -> None:
    _context, packet, _workspace = _chain()
    with pytest.raises(CreativePilotContractError, match="requires its bound context"):
        validate_hypothesis_packet_v2(packet)


def test_workspace_rejects_nested_assignment_and_result_tampering() -> None:
    _context, _packet, workspace = _chain()
    tampered_assignment = deepcopy(workspace)
    tampered_assignment["assignments"][0][
        "review_question"
    ] = "A substituted review question that exceeds the canonical role contract."
    with pytest.raises(CreativePilotContractError, match="assignment identity"):
        validate_workspace(_resign_workspace(tampered_assignment))

    result = build_role_result(
        workspace=workspace,
        assignment_id=workspace["assignments"][0]["assignment_id"],
        stance="pass",
        claim_ids=["claim-1"],
        evidence_refs=["core/rag/orchestration.py"],
        blocker_codes=[],
        oracle_gap_codes=[],
    )
    tampered_result = deepcopy(workspace)
    tampered_result["role_results"] = [result, result]
    with pytest.raises(CreativePilotContractError, match="IDs must be unique"):
        validate_workspace(_resign_workspace(tampered_result))


@pytest.mark.parametrize(
    "evidence_ref",
    [
        "/tmp/local.txt",
        "artifacts/orchestration/private.json",
        "https://github.com/example/review",
        "docs/roadmap/BACKLOG_LEDGER.md",
    ],
)
def test_role_result_rejects_unbound_evidence_refs(evidence_ref: str) -> None:
    _context, _packet, workspace = _chain()
    with pytest.raises(CreativePilotContractError, match="evidence"):
        build_role_result(
            workspace=workspace,
            assignment_id=workspace["assignments"][0]["assignment_id"],
            stance="pass",
            claim_ids=["claim-1"],
            evidence_refs=[evidence_ref],
            blocker_codes=[],
            oracle_gap_codes=[],
        )


def test_routing_uses_closed_tags_not_incidental_output_words() -> None:
    roles, _conditional = route_roles(
        {
            "statement": "Output chunks retain confidence provenance.",
            "mechanism": "Remove one redundant deterministic indirection.",
            "tags": ["confidence", "provenance"],
        }
    )
    assert "data-scientist-agent" in roles
    assert "epistemology-discovery-agent" in roles
    assert "prompt-engineering-eval-agent" not in roles


def test_independent_results_are_blind_and_replay_is_idempotent() -> None:
    _context, _packet, workspace = _chain()
    assignment = workspace["assignments"][0]
    with pytest.raises(CreativePilotContractError, match="must not reference peers"):
        build_role_result(
            workspace=workspace,
            assignment_id=assignment["assignment_id"],
            stance="pass",
            claim_ids=["claim-1"],
            evidence_refs=["core/rag/orchestration.py"],
            blocker_codes=[],
            oracle_gap_codes=[],
            peer_result_refs=["result:peer"],
        )
    result = build_role_result(
        workspace=workspace,
        assignment_id=assignment["assignment_id"],
        stance="pass",
        claim_ids=["claim-1"],
        evidence_refs=["core/rag/orchestration.py"],
        blocker_codes=[],
        oracle_gap_codes=[],
    )
    updated = ingest_role_result(workspace, result)
    assert ingest_role_result(updated, result) == updated
    tampered = deepcopy(result)
    tampered["stance"] = "reject"
    with pytest.raises(CreativePilotContractError):
        ingest_role_result(updated, tampered)


def test_security_reject_is_a_hard_synthesis_blocker() -> None:
    _context, _packet, workspace = _chain()
    completed = _complete(workspace, security_stance="reject")
    synthesis = build_synthesis(completed)
    assert synthesis["decision"] == "hold"
    assert synthesis["evidence_sufficiency"] == "insufficient"


def test_one_targeted_rebuttal_can_resolve_bounded_disagreement() -> None:
    _context, _packet, workspace = _chain()
    current = workspace
    for index, assignment in enumerate(list(workspace["assignments"])):
        result = build_role_result(
            workspace=current,
            assignment_id=assignment["assignment_id"],
            stance="revise" if index == 0 else "pass",
            claim_ids=["claim-degraded-invariants"],
            evidence_refs=["core/rag/orchestration.py"],
            blocker_codes=[],
            oracle_gap_codes=[],
        )
        current = ingest_role_result(current, result)
    current = detect_conflicts(current)
    assert current["state"]["phase"] == "rebuttal_required"
    current = add_rebuttal_assignments(current)
    with pytest.raises(CreativePilotContractError, match="only one"):
        add_rebuttal_assignments(current)
    for assignment in [row for row in current["assignments"] if row["phase"] == "rebuttal"]:
        result = build_role_result(
            workspace=current,
            assignment_id=assignment["assignment_id"],
            stance="pass",
            claim_ids=["claim-degraded-invariants"],
            evidence_refs=["core/rag/orchestration.py"],
            blocker_codes=[],
            oracle_gap_codes=[],
            peer_result_refs=["claim:claim-degraded-invariants"],
        )
        current = ingest_role_result(current, result)
    assert current["state"]["phase"] == "rebuttal_complete"
    current = detect_conflicts(current)
    synthesis = build_synthesis(current)
    assert synthesis["decision"] == "approve"
    assert synthesis["disagreement_class"] == "bounded"


def test_pass_synthesis_binds_approval_and_existing_candidate_v1() -> None:
    context, packet, workspace = _chain()
    completed = _complete(workspace)
    synthesis = build_synthesis(completed)
    synthesized = apply_synthesis_transition(completed, synthesis)
    approval = build_approval_v2(
        workspace=synthesized,
        synthesis=synthesis,
        approved_by="test-operator",
    )
    bundle = build_creative_pilot_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        workspace=synthesized,
        synthesis=synthesis,
        approval=approval,
        variant_count=3,
    )
    assert synthesis["decision"] == "approve"
    assert bundle["candidate"]["schema_version"] == "1.0"
    assert bundle["candidate"]["target_surface"] == ["core/rag/orchestration.py"]
    assert bundle["candidate"]["authority"]["generate_candidate_patch"] is False
    assert bundle["candidate"]["source_creative_research"]["fingerprint"] == fingerprint_payload(
        bundle["bridge"]["lineage"]
    )
    assert bundle["bridge"]["lineage"]["synthesis_id"] == synthesis["synthesis_id"]
    terminal = complete_handoff(
        workspace=synthesized,
        approval=approval,
        bridge=bundle["bridge"],
        candidate=bundle["candidate"],
    )
    assert terminal["state"] == {"phase": "approved_for_pr1_spec", "terminal": True}


def test_approval_rejects_stale_workspace_revision() -> None:
    _context, _packet, workspace = _chain()
    completed = _complete(workspace)
    synthesis = build_synthesis(completed)
    synthesized = apply_synthesis_transition(completed, synthesis)
    stale = deepcopy(synthesized)
    stale["revision"] += 1
    with pytest.raises(CreativePilotContractError, match="reviewed revision"):
        build_approval_v2(
            workspace=_resign_workspace(stale),
            synthesis=synthesis,
            approved_by="test-operator",
        )


def test_evidence_events_use_control_plane_and_tracked_target() -> None:
    _context, _packet, workspace = _chain()
    completed = _complete(workspace)
    synthesis = build_synthesis(completed)
    events = build_evidence_events(
        workspace=completed,
        synthesis=synthesis,
        produced_at="2026-07-10T00:00:00+00:00",
    )
    assert [event.event_type for event in events] == [
        "item_metadata",
        "gate_metric",
        "gate_decision",
    ]
    assert {event.rail for event in events} == {"control_plane"}
    assert {event.source_artifact for event in events} == {"core/rag/orchestration.py"}


def test_duplicate_json_keys_are_rejected() -> None:
    with pytest.raises(CreativePilotContractError, match="duplicate JSON key"):
        load_json_strict('{"phase":"one","phase":"two"}')


def test_pilot_v2_schemas_are_closed_and_version_aligned() -> None:
    contracts = REPO_ROOT / "docs" / "orchestration" / "contracts"
    for filename in (
        "creative_pilot_workspace.v2.schema.json",
        "creative_pilot_role_result.v2.schema.json",
        "creative_pilot_synthesis.v2.schema.json",
    ):
        schema = json.loads((contracts / filename).read_text(encoding="utf-8"))
        assert schema["$id"] == filename
        assert schema["additionalProperties"] is False
        assert schema["properties"]["schema_version"]["const"] == "2.0"


def test_non_tty_approval_fails_closed(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            PYTHON,
            "-m",
            "scripts.orchestration.creative_pilot_workspace",
            "approve-handoff",
            "--pilot-id",
            "missing",
            "--approved-by",
            "test-operator",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "interactive TTY" in result.stdout


def test_adaptive_inventory_blocks_nonterminal_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _context, _packet, workspace = _chain()
    root = tmp_path / "adaptive_pilots"
    pilot = root / "pilot-one"
    pilot.mkdir(parents=True)
    (pilot / "workspace.json").write_text(json.dumps(workspace), encoding="utf-8")
    monkeypatch.setattr(inventory, "ADAPTIVE_PILOTS_ROOT", root)
    report = inventory.build_adaptive_pilot_inventory_report()
    assert report["counts"]["adaptive_pilots_active"] == 1
    assert report["cleanup_blockers"] == ["adaptive_pilot_in_progress"]


def test_adaptive_inventory_requires_valid_terminal_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context, packet, workspace = _chain()
    completed = _complete(workspace)
    synthesis = build_synthesis(completed)
    synthesized = apply_synthesis_transition(completed, synthesis)
    approval = build_approval_v2(
        workspace=synthesized, synthesis=synthesis, approved_by="test-operator"
    )
    bundle = build_creative_pilot_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        workspace=synthesized,
        synthesis=synthesis,
        approval=approval,
        variant_count=3,
    )
    terminal = complete_handoff(
        workspace=synthesized,
        approval=approval,
        bridge=bundle["bridge"],
        candidate=bundle["candidate"],
    )
    root = tmp_path / "adaptive_pilots"
    pilot = root / "pilot-terminal"
    (pilot / "pr1_prepare").mkdir(parents=True)
    payloads = {
        "workspace.json": terminal,
        "synthesis.json": synthesis,
        "approval.v2.json": approval,
        "spec_bridge.v2.json": bundle["bridge"],
        "creative_code_candidate.v1.json": bundle["candidate"],
        "pr1_prepare/source_packet.json": bundle["candidate"],
    }
    for relative, payload in payloads.items():
        (pilot / relative).write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(inventory, "ADAPTIVE_PILOTS_ROOT", root)
    report = inventory.build_adaptive_pilot_inventory_report()
    assert report["counts"]["adaptive_pilots_terminal"] == 1
    assert report["adaptive_pilots"][0]["handoff_valid"] is True
    assert report["cleanup_blockers"] == []

    (pilot / "pr1_prepare" / "source_packet.json").unlink()
    report = inventory.build_adaptive_pilot_inventory_report()
    assert report["counts"]["adaptive_pilots_invalid"] == 1
    assert report["cleanup_blockers"] == ["adaptive_pilot_read_error"]


def test_task_bootstrap_binds_explicit_pilot_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _context, _packet, workspace = _chain()
    root = tmp_path / "adaptive_pilots"
    workspace_path = root / "pilot-one" / "workspace.json"
    workspace_path.parent.mkdir(parents=True)
    workspace_path.write_text(json.dumps(workspace), encoding="utf-8")
    monkeypatch.setattr(task_bootstrap, "CREATIVE_PILOT_ROOT", root)
    ordinary = task_bootstrap.build_task_packet(
        goal="ordinary orchestration task",
        task_class="orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
    )
    pilot = task_bootstrap.build_task_packet(
        goal="independent creative pilot review",
        task_class="orchestration",
        candidate_paths=["core/rag/orchestration.py"],
        creative_pilot_workspace_path=workspace_path,
        creative_pilot_phase="independent",
    )
    assert "creative_pilot_context" not in ordinary
    assert pilot["creative_pilot_context"]["phase"] == "independent"
    assert pilot["task_packet_id"] != ordinary["task_packet_id"]
    assert {row["role"] for row in pilot["creative_pilot_context"]["assignments"]} >= {
        "architecture-specialist",
        "qa-engineer-agent",
        "security-auditor",
    }


def test_canonical_dispatch_carries_role_specific_refs_read_only() -> None:
    _context, _packet, workspace = _chain()
    context = {
        "schema_version": "creative_pilot_context.v2",
        "workspace_id": workspace["workspace_id"],
        "workspace_intent_fingerprint": workspace["intent_fingerprint"],
        "workspace_revision_fingerprint": workspace["revision_fingerprint"],
        "phase": "independent",
        "dispatch_input_fingerprint": phase_dispatch_fingerprint(workspace, phase="independent"),
        "assignments": workspace["assignments"],
        "authority": {
            "read_structured_inputs": True,
            "generate_patch": False,
            "write_repository": False,
            "call_provider": False,
        },
    }
    roles = [row["role"] for row in workspace["assignments"]]
    manifest = build_dispatch_manifest(
        role_slugs=roles,
        mode="runtime",
        enforce_mandatory_post_open_tail=False,
        creative_pilot_context=context,
    )
    assert all(item["readonly"] for item in manifest["dispatch_sequence"])
    assert all(not item["implementation_owner_override"] for item in manifest["dispatch_sequence"])
    assert all(
        item["creative_pilot_assignment"]["review_mode"] == "specification_planning"
        and item["creative_pilot_assignment"]["diff_expected"] is False
        for item in manifest["dispatch_sequence"]
    )
    assert [
        item["creative_pilot_assignment"]["role"] for item in manifest["dispatch_sequence"]
    ] == roles
    tampered = deepcopy(context)
    tampered["dispatch_input_fingerprint"] = "sha256:" + ("0" * 64)
    with pytest.raises(ValueError, match="dispatch fingerprint"):
        build_dispatch_manifest(
            role_slugs=roles,
            mode="runtime",
            enforce_mandatory_post_open_tail=False,
            creative_pilot_context=tampered,
        )
