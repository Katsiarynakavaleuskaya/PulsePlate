from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload
from scripts.orchestration import creative_code_artifact_inventory as inventory
from scripts.orchestration import context_pack_compression
from scripts.orchestration import creative_code_spec_pipeline
from scripts.orchestration import creative_specification_skeptic_review as skeptic_review_cli
from scripts.orchestration import creative_pilot_workspace as pilot_cli
from scripts.orchestration import creative_pilot_workspace_contract as pilot_contract
from scripts.orchestration import task_bootstrap
from scripts.orchestration.qoder_dispatch_bridge import build_dispatch_manifest, main as qoder_main
from scripts.orchestration.creative_hypothesis_spec_bridge_contract import (
    build_creative_pilot_spec_bridge_bundle,
)
from scripts.orchestration.creative_code_spec_pipeline import CreativeCodeSpecPipelineError
from scripts.orchestration.creative_code_specification import REQUIRED_SKEPTIC_REVIEWERS
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
from scripts.orchestration.creative_specification_skeptic_review_contract import (
    default_review_input_authority,
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


def test_tracked_blob_size_uses_object_metadata_without_reading_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commit = "a" * 40
    blob_oid = "b" * 40
    path = "AGENTS.md"
    calls: list[tuple[tuple[str, ...], bool]] = []

    def fake_git(*args: str, binary: bool = False) -> str | bytes:
        calls.append((args, binary))
        responses: dict[tuple[str, ...], str] = {
            ("cat-file", "-t", commit): "commit\n",
            ("ls-tree", commit, "--", path): f"100644 blob {blob_oid}\t{path}\n",
            ("cat-file", "-s", blob_oid): "33554432\n",
        }
        return responses[args]

    monkeypatch.setattr(pilot_contract, "_git", fake_git)

    assert pilot_contract.tracked_blob_size_at_commit(commit, path) == 33_554_432
    assert calls == [
        (("cat-file", "-t", commit), False),
        (("ls-tree", commit, "--", path), False),
        (("cat-file", "-s", blob_oid), False),
    ]


def test_tracked_blob_size_rejects_non_numeric_git_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commit = "a" * 40
    blob_oid = "b" * 40
    path = "AGENTS.md"

    def fake_git(*args: str, binary: bool = False) -> str | bytes:
        del binary
        responses: dict[tuple[str, ...], str] = {
            ("cat-file", "-t", commit): "commit\n",
            ("ls-tree", commit, "--", path): f"100644 blob {blob_oid}\t{path}\n",
            ("cat-file", "-s", blob_oid): "not-a-size\n",
        }
        return responses[args]

    monkeypatch.setattr(pilot_contract, "_git", fake_git)

    with pytest.raises(CreativePilotContractError, match="non-negative integer"):
        pilot_contract.tracked_blob_size_at_commit(commit, path)


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


def test_bound_workspace_replays_after_origin_main_advances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _context, _packet, workspace = _chain()
    monkeypatch.setattr(pilot_contract, "current_origin_main_sha", lambda: "f" * 40)
    assert validate_workspace(workspace) == workspace


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


def test_build_handoff_rejects_origin_main_drift_before_any_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, workspace = _chain()
    completed = _complete(workspace)
    synthesis = build_synthesis(completed)
    synthesized = apply_synthesis_transition(completed, synthesis)
    approval = build_approval_v2(
        workspace=synthesized,
        synthesis=synthesis,
        approved_by="test-operator",
    )
    artifact_root = REPO_ROOT / "artifacts" / "orchestration"
    artifact_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pilot-handoff-drift-", dir=artifact_root) as raw_dir:
        pilot_root = Path(raw_dir)
        pilot_id = "handoff-base-drift"
        pilot_dir = pilot_root / pilot_id
        pilot_dir.mkdir()
        payloads = {
            "context_map.v2.json": context,
            "hypothesis_packet.v2.json": packet,
            "workspace.json": synthesized,
            "synthesis.json": synthesis,
            "approval.v2.json": approval,
        }
        for filename, payload in payloads.items():
            (pilot_dir / filename).write_text(
                json.dumps(payload, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        workspace_before = (pilot_dir / "workspace.json").read_bytes()
        bundle_called = False
        prepare_called = False

        def unexpected_bundle(**_kwargs: object) -> dict[str, object]:
            nonlocal bundle_called
            bundle_called = True
            return {}

        def unexpected_prepare(_candidate_path: Path, _prepare_dir: Path) -> None:
            nonlocal prepare_called
            prepare_called = True

        monkeypatch.setattr(pilot_cli, "PILOT_ROOT", pilot_root)
        monkeypatch.setattr(pilot_cli, "current_origin_main_sha", lambda: "f" * 40)
        monkeypatch.setattr(
            pilot_cli,
            "build_creative_pilot_spec_bridge_bundle",
            unexpected_bundle,
        )
        monkeypatch.setattr(pilot_cli, "prepare_specification", unexpected_prepare)

        assert (
            pilot_cli.main(
                [
                    "build-handoff",
                    "--pilot-id",
                    pilot_id,
                    "--variant-count",
                    "3",
                ]
            )
            == 1
        )
        assert capsys.readouterr().out == (
            "FAIL: adaptive_base_drift: build-handoff requires current origin/main "
            "to equal workspace target head_sha\n"
        )
        assert bundle_called is False
        assert prepare_called is False
        assert (pilot_dir / "workspace.json").read_bytes() == workspace_before
        assert not (pilot_dir / "spec_bridge.v2.json").exists()
        assert not (pilot_dir / "creative_code_candidate.v1.json").exists()
        assert not (pilot_dir / "pr1_prepare").exists()


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


def test_evidence_events_reject_cross_workspace_synthesis() -> None:
    _context, _packet, workspace = _chain()
    completed = _complete(workspace)
    synthesis = build_synthesis(completed)
    forged = deepcopy(synthesis)
    forged["workspace_id"] = "unrelated-workspace"
    body = dict(forged)
    body.pop("synthesis_id")
    body.pop("idempotency_key")
    fingerprint = fingerprint_payload(body)
    upstream = (forged["workspace_id"], *forged["role_result_ids"])
    forged["synthesis_id"] = build_asset_id(
        asset_type="creative_pilot_synthesis",
        rail="orchestration",
        version="2.0",
        policy_version="creative-production-adjacent-pilot-v2",
        fingerprint=fingerprint,
        upstream_ids=upstream,
    )
    forged["idempotency_key"] = build_idempotency_key(
        asset_type="creative_pilot_synthesis",
        rail="orchestration",
        version="2.0",
        policy_version="creative-production-adjacent-pilot-v2",
        fingerprint=fingerprint,
        upstream_ids=upstream,
    )
    with pytest.raises(CreativePilotContractError, match="workspace_id binding mismatch"):
        build_evidence_events(
            workspace=completed,
            synthesis=forged,
            produced_at="2026-07-10T00:00:00+00:00",
        )


def test_duplicate_json_keys_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(CreativePilotContractError, match="duplicate JSON key"):
        load_json_strict('{"phase":"one","phase":"two"}')

    def raise_recursion(*_args: object, **_kwargs: object) -> object:
        raise RecursionError("synthetic nested JSON")

    monkeypatch.setattr(json, "loads", raise_recursion)
    with pytest.raises(CreativePilotContractError, match="invalid JSON"):
        load_json_strict("{}")

    artifact_root = creative_code_spec_pipeline.ARTIFACT_ROOT
    artifact_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="pytest-recursive-json-", dir=artifact_root))
    try:
        recursive_path = root / "recursive.json"
        recursive_path.write_text("{}", encoding="utf-8")
        with pytest.raises(CreativePilotContractError, match="safe exact variant declarations"):
            pilot_cli._read_array(recursive_path)
        with pytest.raises(CreativePilotContractError, match="safe pilot JSON value"):
            pilot_cli._read_json_value(recursive_path)
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "github_" + "pat_" + ("a" * 24),
        "ghp_" + ("b" * 24),
        "xoxb-" + ("c" * 24),
        "-----BEGIN " + "PRIVATE KEY-----",
        "contains api_key marker",
        "diff --git a/file b/file",
        "/Users/example/private.json",
    ],
)
def test_v2_hypothesis_rejects_secret_and_leak_shaped_text(unsafe_text: str) -> None:
    context, _packet, _workspace = _chain()
    with pytest.raises(CreativePilotContractError, match="forbidden raw or secret-shaped text"):
        build_hypothesis_packet_v2(
            context_map=context,
            hypotheses=[
                {
                    "hypothesis_id": "unsafe-hypothesis",
                    "statement": f"Unsafe hypothesis payload {unsafe_text}",
                    "mechanism": "A deterministic mechanism description that remains bounded.",
                    "target_symbols": ["RAGOrchestrationResult"],
                    "tests_or_oracles": ["tests/test_rag_orchestration.py"],
                    "negative_controls": ["successful output remains unchanged"],
                    "tags": ["verification"],
                }
            ],
        )


def test_cli_read_rejects_symlink_outside_root_and_invalid_utf8(tmp_path: Path) -> None:
    artifact_root = REPO_ROOT / "artifacts" / "orchestration"
    artifact_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pilot-read-test-", dir=artifact_root) as raw_dir:
        run_dir = Path(raw_dir)
        outside = tmp_path / "outside.json"
        outside.write_text('{"safe": true}', encoding="utf-8")
        link = run_dir / "linked.json"
        link.symlink_to(outside)
        with pytest.raises(CreativePilotContractError, match="symlink"):
            pilot_cli._read(link)
        with pytest.raises(CreativePilotContractError, match="stay inside repository"):
            pilot_cli._read(outside)
        invalid = run_dir / "invalid.json"
        invalid.write_bytes(b"\xff\xfe")
        with pytest.raises(CreativePilotContractError, match="safe repo-local"):
            pilot_cli._read(invalid)


def test_atomic_write_pins_parent_directory_against_symlink_swap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_root = REPO_ROOT / "artifacts" / "orchestration"
    artifact_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pilot-write-test-", dir=artifact_root) as raw_dir:
        root = Path(raw_dir)
        target_parent = root / "target"
        moved_parent = root / "target-pinned"
        target_parent.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        target = target_parent / "workspace.json"
        real_replace = pilot_cli.os.replace

        def swap_parent_then_replace(
            src: str,
            dst: str,
            *,
            src_dir_fd: int,
            dst_dir_fd: int,
        ) -> None:
            os.rename(target_parent, moved_parent)
            os.symlink(outside, target_parent)
            real_replace(
                src,
                dst,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=dst_dir_fd,
            )

        monkeypatch.setattr(pilot_cli.os, "replace", swap_parent_then_replace)
        pilot_cli._atomic_write(target, {"safe": True})
        assert json.loads((moved_parent / "workspace.json").read_text(encoding="utf-8")) == {
            "safe": True
        }
        assert not (outside / "workspace.json").exists()
        target_parent.unlink()


def test_read_pins_parent_directory_against_symlink_swap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_root = REPO_ROOT / "artifacts" / "orchestration"
    artifact_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pilot-read-race-test-", dir=artifact_root) as raw_dir:
        root = Path(raw_dir)
        target_parent = root / "target"
        moved_parent = root / "target-pinned"
        target_parent.mkdir()
        target = target_parent / "workspace.json"
        target.write_text('{"source":"pinned"}', encoding="utf-8")
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "workspace.json").write_text('{"source":"outside"}', encoding="utf-8")
        real_open_parent = pilot_cli._open_pinned_parent

        def pin_parent_then_swap(path: Path, *, create: bool) -> tuple[int, str]:
            parent_fd, filename = real_open_parent(path, create=create)
            os.rename(target_parent, moved_parent)
            os.symlink(outside, target_parent)
            return parent_fd, filename

        monkeypatch.setattr(pilot_cli, "_open_pinned_parent", pin_parent_then_swap)
        assert pilot_cli._read(target) == {"source": "pinned"}
        target_parent.unlink()


def test_atomic_write_cleanup_preserves_primary_error_and_closes_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_root = REPO_ROOT / "artifacts" / "orchestration"
    artifact_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pilot-cleanup-test-", dir=artifact_root) as raw_dir:
        target = Path(raw_dir) / "workspace.json"
        real_open_parent = pilot_cli._open_pinned_parent
        real_close = pilot_cli.os.close
        parent_descriptors: list[int] = []
        closed_descriptors: list[int] = []

        def capture_parent(path: Path, *, create: bool) -> tuple[int, str]:
            parent_fd, filename = real_open_parent(path, create=create)
            parent_descriptors.append(parent_fd)
            return parent_fd, filename

        def fail_replace(
            _src: str,
            _dst: str,
            *,
            src_dir_fd: int,
            dst_dir_fd: int,
        ) -> None:
            del src_dir_fd, dst_dir_fd
            raise OSError("simulated primary write failure")

        def fail_unlink(_path: str, *, dir_fd: int) -> None:
            del dir_fd
            raise PermissionError("simulated cleanup failure")

        def capture_close(descriptor: int) -> None:
            closed_descriptors.append(descriptor)
            real_close(descriptor)

        with monkeypatch.context() as context:
            context.setattr(pilot_cli, "_open_pinned_parent", capture_parent)
            context.setattr(pilot_cli.os, "replace", fail_replace)
            context.setattr(pilot_cli.os, "unlink", fail_unlink)
            context.setattr(pilot_cli.os, "close", capture_close)
            with pytest.raises(CreativePilotContractError, match="unable to write"):
                pilot_cli._atomic_write(target, {"safe": True})

        assert parent_descriptors
        assert parent_descriptors[-1] in closed_descriptors


def test_atomic_write_translates_missing_dir_fd_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_root = REPO_ROOT / "artifacts" / "orchestration"
    artifact_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pilot-platform-test-", dir=artifact_root) as raw_dir:
        target = Path(raw_dir) / "workspace.json"

        def unsupported_replace(
            _src: str,
            _dst: str,
            *,
            src_dir_fd: int,
            dst_dir_fd: int,
        ) -> None:
            del src_dir_fd, dst_dir_fd
            raise NotImplementedError("dir_fd unsupported")

        monkeypatch.setattr(pilot_cli.os, "replace", unsupported_replace)
        with pytest.raises(CreativePilotContractError, match="unable to write"):
            pilot_cli._atomic_write(target, {"safe": True})


def test_pinned_traversal_closes_child_when_previous_close_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_root = REPO_ROOT / "artifacts" / "orchestration"
    artifact_root.mkdir(parents=True, exist_ok=True)
    target = artifact_root / "pilot-fd-transfer" / "workspace.json"
    real_open = pilot_cli.os.open
    real_close = pilot_cli.os.close
    opened: list[int] = []
    fail_next_close = True

    def capture_open(*args: object, **kwargs: object) -> int:
        descriptor = real_open(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    def fail_first_close(descriptor: int) -> None:
        nonlocal fail_next_close
        if fail_next_close:
            fail_next_close = False
            raise OSError("simulated descriptor transfer failure")
        real_close(descriptor)

    with monkeypatch.context() as context:
        context.setattr(pilot_cli.os, "open", capture_open)
        context.setattr(pilot_cli.os, "close", fail_first_close)
        with pytest.raises(CreativePilotContractError, match="transfer pinned"):
            pilot_cli._open_pinned_parent(target, create=True)

    assert opened
    with pytest.raises(OSError):
        os.fstat(opened[-1])


def test_cli_catches_specification_pipeline_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(_args: object) -> None:
        raise CreativeCodeSpecPipelineError("specification preparation failed")

    monkeypatch.setattr(pilot_cli, "_cmd_status", fail)
    assert pilot_cli.main(["status", "--pilot-id", "safe-pilot"]) == 1
    assert capsys.readouterr().out == "FAIL: specification preparation failed\n"


def _resume_declarations(candidate: dict) -> list[dict]:
    return [
        {
            "approach_family": family,
            "problem_statement": f"Exact {family} candidate specification.",
            "implementation_steps": [f"Apply only the {family} type contract."],
            "target_paths": list(candidate["target_surface"]),
            "tests_to_add": list(candidate["evidence_bundle"]["required_tests"]),
            "negative_controls": ["runtime_values_unchanged", "immutable_oracles_unchanged"],
            "rollback_plan": "Discard before patch generation.",
            "falsifier": "Reject any runtime or target drift.",
            "risk_notes": ["Specification-only local artifact."],
            "wellness_boundary": "No medical claim.",
            "estimated_changed_files": len(candidate["target_surface"]),
        }
        for family in ("fail_closed_guard", "minimal_surgical_change", "seam_extraction")
    ]


def _alternate_chain() -> tuple[dict, dict, dict]:
    context, _packet, _workspace = _chain()
    packet = build_hypothesis_packet_v2(
        context_map=context,
        hypotheses=[
            {
                "hypothesis_id": "alternate-confidence-contract",
                "statement": "An alternate bounded confidence contract may preserve metadata.",
                "mechanism": "Use a distinct specification identity without runtime authority.",
                "target_symbols": ["RAGOrchestrationResult"],
                "tests_or_oracles": ["tests/test_rag_orchestration.py"],
                "negative_controls": ["successful RAG output remains unchanged"],
                "tags": ["confidence", "verification", "provenance"],
            }
        ],
    )
    workspace = build_workspace(
        context_map=context,
        hypothesis_packet=packet,
        selected_hypothesis_id="alternate-confidence-contract",
    )
    return context, packet, workspace


def _write_terminal_pilot(pilot_dir: Path, *, chain: tuple[dict, dict, dict] | None = None) -> dict:
    context, packet, workspace = chain or _chain()
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
    pilot_dir.mkdir(parents=True)
    payloads = {
        "context_map.v2.json": context,
        "hypothesis_packet.v2.json": packet,
        "workspace.json": terminal,
        "synthesis.json": synthesis,
        "approval.v2.json": approval,
        "spec_bridge.v2.json": bundle["bridge"],
        "creative_code_candidate.v1.json": bundle["candidate"],
    }
    for filename, payload in payloads.items():
        (pilot_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    creative_code_spec_pipeline.prepare(
        pilot_dir / "creative_code_candidate.v1.json", pilot_dir / "pr1_prepare"
    )
    return bundle["candidate"]


def _assert_schema_top_level_consts(payload: dict, schema: dict) -> None:
    assert set(payload) == set(schema["required"])
    for key, definition in schema["properties"].items():
        if "const" in definition:
            assert payload[key] == definition["const"]


def _assert_resume_schema_binding_prefixes(binding: dict, schema: dict) -> None:
    lineage_schema = schema["properties"]["source_lineage"]["properties"]
    for field in ("source_artifacts", "original_prepare_bindings"):
        rows = binding["source_lineage"][field]
        prefix_items = lineage_schema[field]["prefixItems"]
        assert len(rows) == len(prefix_items)
        for row, prefix in zip(rows, prefix_items, strict=True):
            definition = schema["$defs"][prefix["$ref"].rsplit("/", 1)[-1]]["allOf"][1]
            properties = definition["properties"]
            assert row["filename"] == properties["filename"]["const"]
            assert row["artifact_type"] == properties["artifact_type"]["const"]
            assert re.search(properties["ref"]["pattern"], row["ref"])


def _publish_adaptive_resume_for_test(
    *,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    prefix: str,
) -> dict[str, object]:
    artifact_root = creative_code_spec_pipeline.ARTIFACT_ROOT
    artifact_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=f"pytest-{prefix}-", dir=artifact_root))
    pilot_root = artifact_root / "adaptive_pilots"
    pilot_id = f"pilot-{root.name}"
    pilot_dir = pilot_root / pilot_id
    spec_root = artifact_root / "spec_bridge"
    declarations = root / "declarations.json"
    candidate = _write_terminal_pilot(pilot_dir)
    declarations.write_text(json.dumps(_resume_declarations(candidate), indent=2), encoding="utf-8")
    spec_root.mkdir(parents=True, exist_ok=True)
    existing_outputs = {entry.name for entry in spec_root.iterdir()}
    monkeypatch.setattr(pilot_cli, "PILOT_ROOT", pilot_root)
    monkeypatch.setattr(pilot_cli, "SPEC_BRIDGE_ROOT", spec_root)
    monkeypatch.setattr(
        pilot_cli,
        "tracked_blob_size_at_commit",
        lambda commit_sha, path: (REPO_ROOT / path).stat().st_size,
    )
    monkeypatch.setattr(skeptic_review_cli, "SPEC_BRIDGE_ROOT", spec_root)
    capsys.readouterr()
    assert (
        pilot_cli.main(
            [
                "resume-pr1",
                "--pilot-id",
                pilot_id,
                "--variant-declarations",
                str(declarations),
                "--current-base-sha",
                _sha(),
            ]
        )
        == 0
    )
    outputs = [entry for entry in spec_root.iterdir() if entry.name not in existing_outputs]
    assert len(outputs) == 1
    output = outputs[0]
    return {
        "root": root,
        "pilot_id": pilot_id,
        "pilot_dir": pilot_dir,
        "output": output,
        "candidate": candidate,
        "intake": json.loads(
            (output / pilot_cli.RESUME_INTAKE_FILENAME).read_text(encoding="utf-8")
        ),
        "binding": json.loads(
            (output / pilot_cli.RESUME_BINDING_FILENAME).read_text(encoding="utf-8")
        ),
    }


def _cleanup_published_adaptive_resume(fixture: dict[str, object]) -> None:
    shutil.rmtree(Path(fixture["output"]), ignore_errors=True)
    shutil.rmtree(Path(fixture["pilot_dir"]), ignore_errors=True)
    shutil.rmtree(Path(fixture["root"]), ignore_errors=True)


def _rederive_resume_binding_identity(
    binding: dict,
    *,
    intake: dict,
    candidate: dict,
) -> dict:
    updated = deepcopy(binding)
    updated["intake"]["intake_id"] = intake["intake_id"]
    updated["intake"]["intake_fingerprint"] = fingerprint_payload(intake)
    resume_id, idempotency_key = pilot_contract.derive_adaptive_pr1_resume_identity(
        pilot_id=updated["pilot_id"],
        intake=intake,
        candidate=candidate,
        source_artifacts=updated["source_lineage"]["source_artifacts"],
        original_prepare_bindings=updated["source_lineage"]["original_prepare_bindings"],
        old_target_manifest=updated["source_lineage"]["old_target_manifest"],
        current_target_manifest=updated["source_lineage"]["current_target_manifest"],
    )
    updated["resume_id"] = resume_id
    updated["bridge_id"] = resume_id
    updated["idempotency_key"] = idempotency_key
    output_root = f"artifacts/orchestration/creative_code/spec_bridge/{resume_id}"
    updated["intake"]["intake_ref"] = f"{output_root}/{pilot_cli.RESUME_INTAKE_FILENAME}"
    updated["candidate_packet"][
        "candidate_packet_ref"
    ] = f"{output_root}/{pilot_cli.RESUME_CANDIDATE_FILENAME}"
    updated["spec_prepare"]["run_dir_ref"] = f"{output_root}/spec_prepare"
    return updated


def _adaptive_review_input(output: Path) -> dict:
    bridge = json.loads((output / pilot_cli.RESUME_BINDING_FILENAME).read_text(encoding="utf-8"))
    candidate = json.loads(
        (output / pilot_cli.RESUME_CANDIDATE_FILENAME).read_text(encoding="utf-8")
    )
    source_packet = json.loads(
        (output / "spec_prepare/source_packet.json").read_text(encoding="utf-8")
    )
    variants = json.loads((output / "spec_prepare/variants.json").read_text(encoding="utf-8"))
    reviews = []
    for variant_index, variant in enumerate(variants):
        for reviewer in REQUIRED_SKEPTIC_REVIEWERS:
            decision = "pass" if variant_index == 0 else "reject"
            reviews.append(
                {
                    "variant_id": variant["variant_id"],
                    "reviewer_role": reviewer,
                    "decision": decision,
                    "blockers": [] if decision == "pass" else ["skeptic_rejected_variant"],
                    "unsafe_authority_flags": [],
                    "duplicate_reason": "none",
                    "required_revision": "none",
                }
            )
    return {
        "schema_version": "1.0",
        "artifact_type": "creative_specification_agent_skeptic_reviews",
        "policy_version": "creative-specification-skeptic-review-finalize-v1",
        "source_bridge_id": bridge["bridge_id"],
        "source_bridge_fingerprint": fingerprint_payload(bridge),
        "source_candidate_id": candidate["candidate_id"],
        "source_candidate_fingerprint": fingerprint_payload(candidate),
        "source_packet_fingerprint": fingerprint_payload(source_packet),
        "variants_fingerprint": fingerprint_payload(variants),
        "reviews": reviews,
        "authority": default_review_input_authority(),
        "sanitized": True,
    }


def _tamper_adaptive_prepare_artifact(output: Path, kind: str) -> tuple[Path, bytes, str]:
    if kind == "context":
        path = output / "spec_prepare/context_pack.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["forged_after_resume"] = True
        error_code = "adaptive_prepare_context_mismatch"
    else:
        path = output / "spec_prepare/skeptic_reviews.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload[0]["blockers"] = ["forged_but_schema_valid"]
        payload[0]["review_fingerprint"] = fingerprint_payload(
            {
                key: payload[0][key]
                for key in sorted(payload[0])
                if key not in {"review_id", "review_fingerprint"}
            }
        )
        error_code = "adaptive_prepare_reviews_mismatch"
    original = path.read_bytes()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path, original, error_code


def test_resume_pr1_publishes_exact_new_only_bundle(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact_root = creative_code_spec_pipeline.ARTIFACT_ROOT
    artifact_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="pytest-resume-", dir=artifact_root))
    pilot_root = artifact_root / "adaptive_pilots"
    pilot_id = f"pilot-{root.name}"
    pilot_dir = pilot_root / pilot_id
    spec_root = artifact_root / "spec_bridge"
    declarations = root / "declarations.json"
    output: Path | None = None
    try:
        spec_root.mkdir(parents=True, exist_ok=True)
        existing_outputs = {entry.name for entry in spec_root.iterdir()}
        candidate = _write_terminal_pilot(pilot_dir)
        with monkeypatch.context() as historical_sizes:
            historical_sizes.setattr(
                context_pack_compression,
                "_safe_context_char_count",
                lambda path, *, repo_root: 4096 + len(path),
            )
            historical_context = creative_code_spec_pipeline.build_default_prepare_artifacts(
                candidate
            )["context_pack.json"]
        retained_context_path = pilot_dir / "pr1_prepare/context_pack.json"
        retained_context_path.write_text(
            json.dumps(historical_context, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        retained_before = {
            path.relative_to(pilot_dir): path.read_bytes() for path in pilot_dir.rglob("*.json")
        }
        declarations.write_text(
            json.dumps(_resume_declarations(candidate), indent=2), encoding="utf-8"
        )
        monkeypatch.setattr(pilot_cli, "PILOT_ROOT", pilot_root)
        monkeypatch.setattr(pilot_cli, "SPEC_BRIDGE_ROOT", spec_root)
        monkeypatch.setattr(
            pilot_cli,
            "tracked_blob_size_at_commit",
            lambda commit_sha, path: 4096 + len(path),
        )
        monkeypatch.setattr(skeptic_review_cli, "SPEC_BRIDGE_ROOT", spec_root)
        args = [
            "resume-pr1",
            "--pilot-id",
            pilot_id,
            "--variant-declarations",
            str(declarations),
            "--current-base-sha",
            _sha(),
        ]
        assert pilot_cli.main(args) == 0
        outputs = [entry for entry in spec_root.iterdir() if entry.name not in existing_outputs]
        assert len(outputs) == 1
        output = outputs[0]
        assert {entry.name for entry in output.iterdir()} == {
            pilot_cli.RESUME_INTAKE_FILENAME,
            pilot_cli.RESUME_BINDING_FILENAME,
            pilot_cli.RESUME_CANDIDATE_FILENAME,
            "spec_prepare",
        }
        variants = json.loads((output / "spec_prepare/variants.json").read_text())
        assert [row["approach_family"] for row in variants] == [
            "minimal_surgical_change",
            "seam_extraction",
            "fail_closed_guard",
        ]
        assert all(
            row["negative_controls"] == ["runtime_values_unchanged", "immutable_oracles_unchanged"]
            for row in variants
        )
        prepared = skeptic_review_cli._read_prepared_bridge(
            output / pilot_cli.RESUME_BINDING_FILENAME
        )
        assert prepared["metrics"]["artifact_type"] == "creative_adaptive_pr1_variant_intake"
        intake_payload = json.loads(
            (output / pilot_cli.RESUME_INTAKE_FILENAME).read_text(encoding="utf-8")
        )
        binding_payload = json.loads(
            (output / pilot_cli.RESUME_BINDING_FILENAME).read_text(encoding="utf-8")
        )
        contracts = REPO_ROOT / "docs/orchestration/contracts"
        intake_schema = json.loads(
            (contracts / "creative_adaptive_pr1_variant_intake.v1.schema.json").read_text()
        )
        binding_schema = json.loads(
            (contracts / "creative_adaptive_pr1_resume_binding.v1.schema.json").read_text()
        )
        _assert_schema_top_level_consts(intake_payload, intake_schema)
        _assert_schema_top_level_consts(binding_payload, binding_schema)
        assert re.fullmatch(
            intake_schema["properties"]["source_candidate"]["properties"]["candidate_ref"][
                "pattern"
            ],
            intake_payload["source_candidate"]["candidate_ref"],
        )
        target_pattern = intake_schema["properties"]["target_surface"]["items"]["pattern"]
        test_pattern = intake_schema["properties"]["required_tests"]["items"]["pattern"]
        assert all(re.fullmatch(target_pattern, path) for path in intake_payload["target_surface"])
        assert all(re.fullmatch(test_pattern, path) for path in intake_payload["required_tests"])
        expected_families = [
            item["allOf"][1]["properties"]["approach_family"]["const"]
            for item in intake_schema["properties"]["declarations"]["prefixItems"][:3]
        ]
        assert [row["approach_family"] for row in intake_payload["declarations"]] == (
            expected_families
        )
        _assert_resume_schema_binding_prefixes(binding_payload, binding_schema)
        context_binding = next(
            row
            for row in binding_payload["source_lineage"]["original_prepare_bindings"]
            if row["filename"] == "context_pack.json"
        )
        assert context_binding["fingerprint"] == fingerprint_payload(historical_context)
        assert re.fullmatch(
            binding_schema["$defs"]["artifactRef"]["properties"]["intake_ref"]["pattern"],
            binding_payload["intake"]["intake_ref"],
        )
        assert re.fullmatch(
            binding_schema["properties"]["candidate_packet"]["properties"]["candidate_packet_ref"][
                "pattern"
            ],
            binding_payload["candidate_packet"]["candidate_packet_ref"],
        )
        expected_files = [
            row["const"]
            for row in binding_schema["properties"]["spec_prepare"]["properties"]["expected_files"][
                "prefixItems"
            ]
        ]
        assert binding_payload["spec_prepare"]["expected_files"] == expected_files

        reordered_binding = deepcopy(binding_payload)
        reordered_binding["source_lineage"]["source_artifacts"][0:2] = reversed(
            reordered_binding["source_lineage"]["source_artifacts"][0:2]
        )
        with pytest.raises(CreativePilotContractError, match="exact ordered set"):
            pilot_contract.validate_adaptive_pr1_resume_binding(
                reordered_binding,
                intake=intake_payload,
                candidate=candidate,
            )
        with pytest.raises(AssertionError):
            _assert_resume_schema_binding_prefixes(reordered_binding, binding_schema)

        semantic_drift = deepcopy(intake_payload)
        semantic_drift["target_surface"] = ["core/rag/contracts.py"]
        with pytest.raises(CreativePilotContractError, match="target or required test binding"):
            pilot_contract.validate_adaptive_pr1_variant_intake(
                semantic_drift,
                candidate=candidate,
            )
        before = {path.relative_to(output): path.read_bytes() for path in output.rglob("*.json")}
        assert pilot_cli.main(args) == 0
        after = {path.relative_to(output): path.read_bytes() for path in output.rglob("*.json")}
        assert before == after
        retained_after = {
            path.relative_to(pilot_dir): path.read_bytes() for path in pilot_dir.rglob("*.json")
        }
        assert retained_before == retained_after

        prepared_variants_path = output / "spec_prepare/variants.json"
        prepared_variants_bytes = prepared_variants_path.read_bytes()
        tampered_variants = json.loads(prepared_variants_bytes)
        tampered_variants[0]["problem_statement"] = "Tampered replay content."
        prepared_variants_path.write_text(json.dumps(tampered_variants), encoding="utf-8")
        capsys.readouterr()
        assert pilot_cli.main(args) == 1
        assert "adaptive_prepare_variants_mismatch" in capsys.readouterr().out
        prepared_variants_path.write_bytes(prepared_variants_bytes)

        context_pack_path = output / "spec_prepare/context_pack.json"
        context_pack_bytes = context_pack_path.read_bytes()
        nested_target = root / "nested-context-pack.json"
        nested_target.write_bytes(context_pack_bytes)
        context_pack_path.unlink()
        context_pack_path.symlink_to(nested_target)
        capsys.readouterr()
        assert pilot_cli.main(args) == 1
        assert "adaptive_source_symlink: nested resume child" in capsys.readouterr().out
        context_pack_path.unlink()
        context_pack_path.write_bytes(context_pack_bytes)

        intake_path = output / pilot_cli.RESUME_INTAKE_FILENAME
        intake_bytes = intake_path.read_bytes()
        intake_path.write_text('{"divergent": true}\n', encoding="utf-8")
        capsys.readouterr()
        assert pilot_cli.main(args) == 1
        assert "adaptive_divergent_replay" in capsys.readouterr().out
        intake_path.write_bytes(intake_bytes)

        candidate_path = output / pilot_cli.RESUME_CANDIDATE_FILENAME
        candidate_bytes = candidate_path.read_bytes()
        candidate_path.unlink()
        candidate_path.symlink_to(pilot_dir / "creative_code_candidate.v1.json")
        capsys.readouterr()
        assert pilot_cli.main(args) == 1
        assert "adaptive_source_symlink" in capsys.readouterr().out
        candidate_path.unlink()
        candidate_path.write_bytes(candidate_bytes)

        (output / "spec_prepare/context_pack.json").unlink()
        capsys.readouterr()
        assert pilot_cli.main(args) == 1
        assert "adaptive_partial_output" in capsys.readouterr().out
    finally:
        if output is not None:
            shutil.rmtree(output, ignore_errors=True)
        shutil.rmtree(pilot_dir, ignore_errors=True)
        shutil.rmtree(root, ignore_errors=True)


def test_resume_exact_replay_is_byte_mtime_and_entry_count_stable() -> None:
    source = Path(pilot_cli.__file__).read_text(encoding="utf-8")
    resume_body = source[source.index("def _cmd_resume_pr1(") :]
    existing_branch = resume_body.index("if final_dir.exists() or final_dir.is_symlink():")
    validation = resume_body.index("_validate_existing_resume(", existing_branch)
    replay_return = resume_body.index("return", validation)
    staging_allocation = resume_body.index("for _attempt in range(32):")
    assert existing_branch < validation < replay_return < staging_allocation


def test_resume_rejects_stale_origin_main_before_publication() -> None:
    source = Path(pilot_cli.__file__).read_text(encoding="utf-8")
    resume_body = source[source.index("def _cmd_resume_pr1(") :]
    stale_check = resume_body.index("current_base != current_origin_main_sha()")
    lock_open = resume_body.index("_open_resume_parent_lock(final_dir)")
    assert stale_check < lock_open
    assert "adaptive_base_drift: current-base-sha must equal origin/main" in resume_body


def test_resume_rejects_retained_lineage_substitution(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture = _publish_adaptive_resume_for_test(
        monkeypatch=monkeypatch,
        capsys=capsys,
        prefix="pilot-binding",
    )
    try:
        pilot_id = str(fixture["pilot_id"])
        candidate = dict(fixture["candidate"])
        intake = dict(fixture["intake"])
        binding = dict(fixture["binding"])
        copied_pilot_id = f"{pilot_id}-copied"

        substituted = deepcopy(binding)
        substituted["pilot_id"] = copied_pilot_id
        substituted = _rederive_resume_binding_identity(
            substituted,
            intake=intake,
            candidate=candidate,
        )
        with pytest.raises(CreativePilotContractError, match="resume and intake pilot_id differ"):
            pilot_contract.validate_adaptive_pr1_resume_binding(
                substituted,
                intake=intake,
                candidate=candidate,
                revalidate_git=False,
            )

        copied_root = "artifacts/orchestration/creative_code/adaptive_pilots/" f"{copied_pilot_id}"
        copied_intake = pilot_contract.build_adaptive_pr1_variant_intake(
            pilot_id=pilot_id,
            candidate=candidate,
            candidate_ref=f"{copied_root}/creative_code_candidate.v1.json",
            declarations=intake["declarations"],
        )
        copied = deepcopy(binding)
        for row in copied["source_lineage"]["source_artifacts"]:
            row["ref"] = f"{copied_root}/{row['filename']}"
        for row in copied["source_lineage"]["original_prepare_bindings"]:
            row["ref"] = f"{copied_root}/pr1_prepare/{row['filename']}"
        copied = _rederive_resume_binding_identity(
            copied,
            intake=copied_intake,
            candidate=candidate,
        )
        with pytest.raises(CreativePilotContractError, match="intake candidate ref escaped"):
            pilot_contract.validate_adaptive_pr1_resume_binding(
                copied,
                intake=copied_intake,
                candidate=candidate,
                revalidate_git=False,
            )

        mixed = deepcopy(binding)
        mixed["source_lineage"]["source_artifacts"][0]["ref"] = f"{copied_root}/context_map.v2.json"
        mixed = _rederive_resume_binding_identity(
            mixed,
            intake=intake,
            candidate=candidate,
        )
        with pytest.raises(CreativePilotContractError, match="retained source ref escaped"):
            pilot_contract.validate_adaptive_pr1_resume_binding(
                mixed,
                intake=intake,
                candidate=candidate,
                revalidate_git=False,
            )

        historical = deepcopy(binding)
        historical_manifest = historical["source_lineage"]["old_target_manifest"]
        historical_manifest["base_sha"] = "1" * 40
        historical_manifest["head_sha"] = "2" * 40
        historical["source_lineage"]["source_base_sha"] = "1" * 40
        historical["source_lineage"]["source_head_sha"] = "2" * 40
        historical = _rederive_resume_binding_identity(
            historical,
            intake=intake,
            candidate=candidate,
        )
        assert historical["resume_id"] != binding["resume_id"]
        assert historical["idempotency_key"] != binding["idempotency_key"]
    finally:
        _cleanup_published_adaptive_resume(fixture)


@pytest.mark.parametrize("tamper_kind", ["context", "reviews"])
def test_adaptive_attach_and_reentry_recompute_exact_prepare_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tamper_kind: str,
) -> None:
    fixture = _publish_adaptive_resume_for_test(
        monkeypatch=monkeypatch,
        capsys=capsys,
        prefix=f"adaptive-{tamper_kind}",
    )
    try:
        output = Path(fixture["output"])
        reviews_path = Path(fixture["root"]) / f"{tamper_kind}-reviews.json"
        reviews_path.write_text(
            json.dumps(_adaptive_review_input(output), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tampered_path, original, error_code = _tamper_adaptive_prepare_artifact(output, tamper_kind)
        capsys.readouterr()
        assert (
            skeptic_review_cli.main(
                [
                    "attach",
                    "--bridge",
                    str(output / pilot_cli.RESUME_BINDING_FILENAME),
                    "--reviews",
                    str(reviews_path),
                ]
            )
            == 1
        )
        captured = capsys.readouterr()
        assert error_code in captured.err
        assert "Traceback" not in captured.err
        assert not (output / "spec_finalize_reviewed").exists()

        tampered_path.write_bytes(original)
        assert (
            skeptic_review_cli.main(
                [
                    "attach",
                    "--bridge",
                    str(output / pilot_cli.RESUME_BINDING_FILENAME),
                    "--reviews",
                    str(reviews_path),
                ]
            )
            == 0
        )
        capsys.readouterr()
        attachment = output / "spec_finalize_reviewed" / skeptic_review_cli.ATTACHMENT_FILENAME
        _tamper_adaptive_prepare_artifact(output, tamper_kind)

        assert skeptic_review_cli.main(["validate", "--attachment", str(attachment)]) == 1
        captured = capsys.readouterr()
        assert error_code in captured.err
        assert "Traceback" not in captured.err
        assert skeptic_review_cli.main(["finalize", "--attachment", str(attachment)]) == 1
        captured = capsys.readouterr()
        assert error_code in captured.err
        assert "Traceback" not in captured.err
        reviewed_dir = output / "spec_finalize_reviewed"
        assert not (reviewed_dir / skeptic_review_cli.BUNDLE_FILENAME).exists()
        assert not (reviewed_dir / skeptic_review_cli.FINALIZE_RECEIPT_FILENAME).exists()
    finally:
        _cleanup_published_adaptive_resume(fixture)


def test_resume_continuity_uses_distinct_target_and_oracle_failure_codes() -> None:
    context, _packet, _workspace = _chain()
    original = context["target_manifest"]
    target_drift = deepcopy(original)
    target_drift["files"][0]["content_fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(CreativePilotContractError, match="adaptive_target_drift"):
        pilot_contract._assert_target_continuity(original, target_drift)

    oracle_drift = deepcopy(original)
    oracle_drift["oracle_bindings"][0]["content_fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(CreativePilotContractError, match="adaptive_oracle_drift"):
        pilot_contract._assert_target_continuity(original, oracle_drift)


def _assert_resume_lineage_failure(
    *,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mutate: Callable[[Path, Path], None],
) -> None:
    artifact_root = creative_code_spec_pipeline.ARTIFACT_ROOT
    artifact_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="pytest-lineage-", dir=artifact_root))
    pilot_root = artifact_root / "adaptive_pilots"
    pilot_id = f"pilot-{root.name}"
    pilot_dir = pilot_root / pilot_id
    alternate_dir = pilot_root / f"alternate-{root.name}"
    spec_root = artifact_root / "spec_bridge"
    declarations = root / "declarations.json"
    try:
        candidate = _write_terminal_pilot(pilot_dir)
        _write_terminal_pilot(alternate_dir, chain=_alternate_chain())
        declarations.write_text(
            json.dumps(_resume_declarations(candidate), indent=2), encoding="utf-8"
        )
        mutate(pilot_dir, alternate_dir)
        retained_before = {
            path.relative_to(pilot_dir): path.read_bytes() for path in pilot_dir.rglob("*.json")
        }
        spec_root.mkdir(parents=True, exist_ok=True)
        outputs_before = {entry.name for entry in spec_root.iterdir()}
        monkeypatch.setattr(pilot_cli, "PILOT_ROOT", pilot_root)
        monkeypatch.setattr(pilot_cli, "SPEC_BRIDGE_ROOT", spec_root)
        capsys.readouterr()
        assert (
            pilot_cli.main(
                [
                    "resume-pr1",
                    "--pilot-id",
                    pilot_id,
                    "--variant-declarations",
                    str(declarations),
                    "--current-base-sha",
                    _sha(),
                ]
            )
            == 1
        )
        captured = capsys.readouterr()
        assert captured.out.startswith("FAIL: adaptive_source_lineage_mismatch:")
        assert "Traceback" not in captured.out
        assert {entry.name for entry in spec_root.iterdir()} == outputs_before
        retained_after = {
            path.relative_to(pilot_dir): path.read_bytes() for path in pilot_dir.rglob("*.json")
        }
        assert retained_before == retained_after
    finally:
        shutil.rmtree(pilot_dir, ignore_errors=True)
        shutil.rmtree(alternate_dir, ignore_errors=True)
        shutil.rmtree(root, ignore_errors=True)


def test_resume_rejects_source_fingerprint_drift(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def mutate(pilot_dir: Path, _alternate_dir: Path) -> None:
        candidate_path = pilot_dir / "creative_code_candidate.v1.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["forged_before_resume"] = True
        candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

    _assert_resume_lineage_failure(monkeypatch=monkeypatch, capsys=capsys, mutate=mutate)


def test_resume_cooperative_lock_contention_then_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = pilot_cli.importlib.import_module

    def missing_fcntl(name: str) -> object:
        if name == "fcntl":
            raise ModuleNotFoundError(name)
        return real_import(name)

    monkeypatch.setattr(pilot_cli.importlib, "import_module", missing_fcntl)
    with pytest.raises(
        CreativePilotContractError,
        match="cooperative locking is unavailable",
    ):
        pilot_cli._open_resume_parent_lock(Path("artifacts/unavailable-lock"))
    monkeypatch.undo()

    try:
        fcntl_module = importlib.import_module("fcntl")
    except ModuleNotFoundError:
        return
    artifact_root = creative_code_spec_pipeline.ARTIFACT_ROOT
    artifact_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="pytest-resume-lock-", dir=artifact_root))
    try:
        final_dir = root / "resume"
        owner_fd = os.open(final_dir.parent, os.O_RDONLY)
        fcntl_module.flock(owner_fd, fcntl_module.LOCK_EX | fcntl_module.LOCK_NB)
        try:
            with pytest.raises(
                CreativePilotContractError,
                match="adaptive_resume_lock_contended",
            ):
                pilot_cli._open_resume_parent_lock(final_dir)
        finally:
            fcntl_module.flock(owner_fd, fcntl_module.LOCK_UN)
            os.close(owner_fd)
        replay_fd = pilot_cli._open_resume_parent_lock(final_dir)
        os.close(replay_fd)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_resume_atomic_publish_preserves_existing_destination() -> None:
    artifact_root = creative_code_spec_pipeline.ARTIFACT_ROOT
    artifact_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="pytest-resume-publish-", dir=artifact_root))
    try:
        staging = root / ".resume.staging"
        final_dir = root / "resume"
        staging.mkdir()
        final_dir.mkdir()
        (staging / "candidate.json").write_text("staging\n", encoding="utf-8")
        (final_dir / "owner.marker").write_text("owner\n", encoding="utf-8")

        with pytest.raises(CreativePilotContractError, match="adaptive_publish_collision"):
            pilot_cli._atomic_publish_directory_noreplace(staging, final_dir)

        assert (final_dir / "owner.marker").read_text(encoding="utf-8") == "owner\n"
        assert staging.is_dir()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_resume_partial_or_divergent_output_fails_closed(tmp_path: Path) -> None:
    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / pilot_cli.RESUME_INTAKE_FILENAME).write_text("{}\n", encoding="utf-8")
    with pytest.raises(CreativePilotContractError, match="adaptive_partial_output"):
        pilot_cli._assert_complete_resume_dir(partial)

    source = Path(pilot_cli.__file__).read_text(encoding="utf-8")
    assert "adaptive_divergent_replay: resume inputs changed" in source


def test_resume_cleanup_quarantines_only_owned_staging() -> None:
    artifact_root = creative_code_spec_pipeline.ARTIFACT_ROOT
    artifact_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="pytest-resume-cleanup-", dir=artifact_root))
    try:
        staging = root / ".resume.staging"
        staging.mkdir()
        identity = pilot_cli._directory_identity(staging)
        retained_name = pilot_cli._retain_owned_staging(
            staging,
            expected_identity=identity,
        )
        retained = root / retained_name
        assert retained.is_dir()
        assert not staging.exists()

        foreign = root / ".foreign.staging"
        foreign.mkdir()
        with pytest.raises(CreativePilotContractError, match="ownership changed"):
            pilot_cli._retain_owned_staging(foreign, expected_identity=identity)
        assert foreign.is_dir()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_adaptive_authority_flags_remain_false() -> None:
    allowed = {
        "read_sanitized_context",
        "emit_local_artifacts",
        "run_specification_prepare",
    }
    assert {key for key, value in pilot_contract.ADAPTIVE_PR1_AUTHORITY.items() if value} == allowed
    assert all(
        value is False
        for key, value in pilot_contract.ADAPTIVE_PR1_AUTHORITY.items()
        if key not in allowed
    )


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


def test_prepare_invalid_surface_uses_stable_cli_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(pilot_cli, "PILOT_ROOT", tmp_path / "adaptive_pilots")
    hypotheses = tmp_path / "hypotheses.json"
    hypotheses.write_text('{"hypotheses": []}', encoding="utf-8")
    sha = _sha()
    assert (
        pilot_cli.main(
            [
                "prepare",
                "--pilot-id",
                "invalid-surface",
                "--base-sha",
                sha,
                "--head-sha",
                sha,
                "--target",
                "app/main.py",
                "--symbol",
                "app",
                "--oracle",
                "tests/test_app.py",
                "--context-ref",
                "tests/test_app.py",
                "--hypotheses",
                str(hypotheses),
                "--selected-hypothesis",
                "invalid",
            ]
        )
        == 1
    )
    output = capsys.readouterr().out
    assert output.startswith("FAIL: ")
    assert "Traceback" not in output


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
    artifact_root = REPO_ROOT / "artifacts" / "orchestration"
    artifact_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pilot-dispatch-test-", dir=artifact_root) as raw_dir:
        packet_path = Path(raw_dir) / "task_packet.json"
        packet_path.write_text(json.dumps(pilot), encoding="utf-8")
        manifest_path = Path(raw_dir) / "dispatch_manifest.json"
        assert (
            qoder_main(
                [
                    "--packet",
                    str(packet_path),
                    "--mode",
                    "runtime",
                    "--output",
                    str(manifest_path),
                ]
            )
            == 0
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert [row["role_slug"] for row in manifest["dispatch_sequence"]] == [
        row["role"] for row in pilot["creative_pilot_context"]["assignments"]
    ]


def test_terminal_and_wrong_phase_workspace_cannot_dispatch(
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
    workspace_path = root / "pilot-terminal" / "workspace.json"
    workspace_path.parent.mkdir(parents=True)
    monkeypatch.setattr(task_bootstrap, "CREATIVE_PILOT_ROOT", root)
    workspace_path.write_text(json.dumps(terminal), encoding="utf-8")
    with pytest.raises(ValueError, match="terminal workspace"):
        task_bootstrap.build_task_packet(
            goal="invalid replay",
            task_class="orchestration",
            candidate_paths=["core/rag/orchestration.py"],
            creative_pilot_workspace_path=workspace_path,
            creative_pilot_phase="independent",
        )
    workspace_path.write_text(json.dumps(workspace), encoding="utf-8")
    with pytest.raises(ValueError, match="synthesis dispatch requires"):
        task_bootstrap.build_task_packet(
            goal="invalid early synthesis",
            task_class="orchestration",
            candidate_paths=["core/rag/orchestration.py"],
            creative_pilot_workspace_path=workspace_path,
            creative_pilot_phase="synthesis",
        )


def test_creative_pilot_rejects_post_open_and_merge_ready_lifecycle_phases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _context, _packet, workspace = _chain()
    root = tmp_path / "adaptive_pilots"
    workspace_path = root / "pilot-lifecycle" / "workspace.json"
    workspace_path.parent.mkdir(parents=True)
    workspace_path.write_text(json.dumps(workspace), encoding="utf-8")
    monkeypatch.setattr(task_bootstrap, "CREATIVE_PILOT_ROOT", root)
    for phase in ("post_open_review", "merge_ready"):
        with pytest.raises(ValueError, match="cannot be combined"):
            task_bootstrap.build_task_packet(
                goal="invalid lifecycle composition",
                task_class="orchestration",
                candidate_paths=["core/rag/orchestration.py"],
                pr_phase=phase,
                creative_pilot_workspace_path=workspace_path,
                creative_pilot_phase="independent",
            )

    ordinary = task_bootstrap.build_task_packet(
        goal="pilot packet for direct bridge guard",
        task_class="orchestration",
        candidate_paths=["core/rag/orchestration.py"],
        creative_pilot_workspace_path=workspace_path,
        creative_pilot_phase="independent",
    )
    ordinary["pr_phase"] = "post_open_review"
    artifact_root = REPO_ROOT / "artifacts" / "orchestration"
    artifact_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pilot-lifecycle-test-", dir=artifact_root) as raw_dir:
        packet_path = Path(raw_dir) / "task_packet.json"
        packet_path.write_text(json.dumps(ordinary), encoding="utf-8")
        assert qoder_main(["--packet", str(packet_path), "--mode", "review"]) == 1


def test_handoff_rejects_minimal_forged_bridge_and_candidate() -> None:
    _context, _packet, workspace = _chain()
    completed = _complete(workspace)
    synthesis = build_synthesis(completed)
    synthesized = apply_synthesis_transition(completed, synthesis)
    approval = build_approval_v2(
        workspace=synthesized, synthesis=synthesis, approved_by="test-operator"
    )
    with pytest.raises(CreativePilotContractError, match="handoff artifact is invalid"):
        complete_handoff(
            workspace=synthesized,
            approval=approval,
            bridge={
                "bridge_id": "fake-bridge",
                "candidate_id": "fake-candidate",
                "candidate_fingerprint": fingerprint_payload({"candidate_id": "fake-candidate"}),
            },
            candidate={"candidate_id": "fake-candidate"},
        )


def test_record_role_result_exact_replay_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _context, _packet, workspace = _chain()
    artifact_root = REPO_ROOT / "artifacts" / "orchestration"
    artifact_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pilot-replay-test-", dir=artifact_root) as raw_dir:
        root = Path(raw_dir)
        pilot_dir = root / "pilot-replay"
        pilot_dir.mkdir(parents=True)
        (pilot_dir / "workspace.json").write_text(json.dumps(workspace), encoding="utf-8")
        monkeypatch.setattr(pilot_cli, "PILOT_ROOT", root)
        assignment = workspace["assignments"][0]
        argv = [
            "record-role-result",
            "--pilot-id",
            "pilot-replay",
            "--assignment-id",
            assignment["assignment_id"],
            "--stance",
            "pass",
            "--claim-id",
            "claim-replay",
            "--evidence-ref",
            "core/rag/orchestration.py",
        ]
        assert pilot_cli.main(argv) == 0
        after_first = (pilot_dir / "workspace.json").read_text(encoding="utf-8")
        replay_argv = list(argv)
        replay_argv[replay_argv.index("claim-replay")] = " claim-replay "
        replay_argv[replay_argv.index("core/rag/orchestration.py")] = " core/rag/orchestration.py "
        assert pilot_cli.main(replay_argv) == 0
        assert (pilot_dir / "workspace.json").read_text(encoding="utf-8") == after_first


def test_apply_synthesis_rejects_structurally_valid_forgery() -> None:
    _context, _packet, workspace = _chain()
    completed = _complete(workspace)
    synthesis = build_synthesis(completed)
    forged = deepcopy(synthesis)
    forged["decision"] = "revise"
    forged["next_allowed_action"] = "revise_or_stop"
    body = dict(forged)
    body.pop("synthesis_id")
    body.pop("idempotency_key")
    # Rebuild a structurally valid identity without changing workspace truth.
    fingerprint = fingerprint_payload(body)
    upstream = (completed["workspace_id"], *forged["role_result_ids"])
    forged["synthesis_id"] = build_asset_id(
        asset_type="creative_pilot_synthesis",
        rail="orchestration",
        version="2.0",
        policy_version="creative-production-adjacent-pilot-v2",
        fingerprint=fingerprint,
        upstream_ids=upstream,
    )
    forged["idempotency_key"] = build_idempotency_key(
        asset_type="creative_pilot_synthesis",
        rail="orchestration",
        version="2.0",
        policy_version="creative-production-adjacent-pilot-v2",
        fingerprint=fingerprint,
        upstream_ids=upstream,
    )
    with pytest.raises(CreativePilotContractError, match="deterministic workspace truth"):
        apply_synthesis_transition(completed, forged)


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
