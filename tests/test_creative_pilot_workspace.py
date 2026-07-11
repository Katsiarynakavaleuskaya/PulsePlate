from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload
from scripts.orchestration import creative_code_artifact_inventory as inventory
from scripts.orchestration import creative_pilot_workspace as pilot_cli
from scripts.orchestration import creative_pilot_workspace_contract as pilot_contract
from scripts.orchestration import task_bootstrap
from scripts.orchestration.qoder_dispatch_bridge import build_dispatch_manifest, main as qoder_main
from scripts.orchestration.creative_hypothesis_spec_bridge_contract import (
    build_creative_pilot_spec_bridge_bundle,
)
from scripts.orchestration.creative_code_spec_pipeline import CreativeCodeSpecPipelineError
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


def test_duplicate_json_keys_are_rejected() -> None:
    with pytest.raises(CreativePilotContractError, match="duplicate JSON key"):
        load_json_strict('{"phase":"one","phase":"two"}')


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


def test_pilot_v2_schemas_are_closed_and_version_aligned() -> None:
    contracts = REPO_ROOT / "docs" / "orchestration" / "contracts"
    for filename in (
        "creative_pilot_workspace.v2.schema.json",
        "creative_pilot_role_result.v2.schema.json",
        "creative_pilot_synthesis.v2.schema.json",
        "creative_hypothesis_approval.v2.schema.json",
        "creative_hypothesis_packet.v2.schema.json",
        "creative_hypothesis_specification_bridge.v2.schema.json",
        "creative_protocol_context_map.v2.schema.json",
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
