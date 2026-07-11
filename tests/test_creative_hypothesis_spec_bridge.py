from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import shutil
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_hypothesis_spec_bridge as cli
from scripts.orchestration.creative_code_contract import validate_creative_code_candidate_packet
from scripts.orchestration.creative_hypothesis_spec_bridge_contract import (
    BRIDGE_ARTIFACT_TYPE,
    BRIDGE_SUCCESS_STATUS,
    METRICS_ARTIFACT_TYPE,
    NO_ALLOWED_MUTABLE_TARGET,
    PREPARE_FILENAMES,
    POLICY_VERSION,
    CreativeHypothesisSpecBridgeError,
    build_bridge_metrics,
    build_creative_hypothesis_spec_bridge_bundle,
    mark_bridge_prepared,
    validate_bridge_metrics,
    validate_creative_hypothesis_specification_bridge,
    _artifact_identity as _bridge_artifact_identity,
    _bridge_identity_payload,
)
from scripts.orchestration.experiment_runner_pr_creative_context_contract import (
    COORDINATOR_DISPATCH_POLICY_VERSION,
    COORDINATOR_DISPATCH_TYPE,
    HYPOTHESIS_PACKET_TYPE,
    _artifact_identity,
    build_creative_hypothesis_agent_routing,
    build_creative_hypothesis_approval,
    build_creative_hypothesis_coordinator_dispatch,
    build_creative_hypothesis_packet,
    build_creative_protocol_context_map,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
SHA256_D = "sha256:" + ("d" * 64)


def test_typed_bundle_narrows_only_string_keyed_artifact_objects() -> None:
    assert cli._require_typed_bundle({"bridge": {"bridge_id": "bridge-1"}}) == {
        "bridge": {"bridge_id": "bridge-1"}
    }
    with pytest.raises(cli.CreativeHypothesisSpecBridgeCliError, match="must return an object"):
        cli._require_typed_bundle([])
    with pytest.raises(
        cli.CreativeHypothesisSpecBridgeCliError,
        match="string-keyed artifact objects",
    ):
        cli._require_typed_bundle({"bridge": []})
    with pytest.raises(
        cli.CreativeHypothesisSpecBridgeCliError,
        match="bridge artifacts must use string keys",
    ):
        cli._require_typed_bundle({"bridge": {1: "invalid"}})


def _context() -> dict[str, Any]:
    return build_creative_protocol_context_map(
        changed_paths=[
            "scripts/orchestration/creative_hypothesis_spec_bridge.py",
            "docs/orchestration/contracts/creative_hypothesis_specification_bridge.v1.schema.json",
        ],
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2068,
        base_ref="main",
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        task_packet_id="task:spec-bridge",
        generated_at_utc="2026-07-03T00:00:00Z",
        nearby_repo_refs=["scripts/orchestration/creative_code_spec_pipeline.py"],
        test_refs=["tests/test_creative_hypothesis_spec_bridge.py"],
        contract_refs=[
            "docs/orchestration/contracts/EXPERIMENT_RUNNER_PR_CREATIVE_CONTEXT_CONTRACT.md"
        ],
        backlog_refs=["docs/roadmap/BACKLOG_LEDGER.md"],
        review_source_refs=["artifacts/orchestration/experiments/results/oracle-result.json"],
        capability_state_ref=(
            "artifacts/orchestration/experiments/creative_context/capability_state.json"
        ),
        philosophical_context_refs=["docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md"],
        cross_domain_candidate_refs=[
            "docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md"
        ],
        label_enabled=False,
        marker_enabled=False,
        manual_enabled=False,
        sealed_codex_security_scan_ref=(
            "artifacts/orchestration/experiments/creative_context/codex-security.json"
        ),
        sealed_codex_security_scan_fingerprint=SHA256_D,
        security_relevant_diff_changed=False,
    )


def _refresh_packet_identity(packet: dict[str, Any]) -> dict[str, Any]:
    body = {
        key: value for key, value in packet.items() if key not in {"packet_id", "idempotency_key"}
    }
    packet_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=HYPOTHESIS_PACKET_TYPE,
        upstream_ids=(str(packet["context_map_id"]),),
    )
    packet["packet_id"] = packet_id
    packet["idempotency_key"] = idempotency_key
    return packet


def _refresh_dispatch_identity(dispatch: dict[str, Any]) -> dict[str, Any]:
    body = {
        key: value
        for key, value in dispatch.items()
        if key not in {"dispatch_id", "idempotency_key"}
    }
    dispatch_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=COORDINATOR_DISPATCH_TYPE,
        upstream_ids=(str(dispatch["source_hypothesis_packet_id"]),),
        policy_version=COORDINATOR_DISPATCH_POLICY_VERSION,
    )
    dispatch["dispatch_id"] = dispatch_id
    dispatch["idempotency_key"] = idempotency_key
    return dispatch


def _chain(
    *,
    approved_targets: list[str] | None = None,
    decision: str = "approve_for_pr1_specification",
    next_step: str = "create_pr1_specification",
    hypothesis_suffix: str = "",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    context = _context()
    packet = build_creative_hypothesis_packet(context, hypothesis_count=3)
    hypothesis = dict(packet["hypotheses"][0])
    if hypothesis_suffix:
        hypothesis["hypothesis_id"] = f"{hypothesis['hypothesis_id']}-{hypothesis_suffix}"
    hypothesis["target_surfaces"] = sorted(
        [
            "docs/prompts/cv/program.md",
            "scripts/orchestration/creative_hypothesis_spec_bridge.py",
            "tests/test_creative_hypothesis_spec_bridge.py",
            "docs/orchestration/contracts/creative_hypothesis_specification_bridge.v1.schema.json",
        ]
    )
    hypothesis["tests_or_oracles"] = sorted(
        [
            "tests/test_creative_hypothesis_spec_bridge.py",
            "docs/orchestration/contracts/creative_hypothesis_spec_bridge_metrics.v1.schema.json",
        ]
    )
    packet["hypotheses"][0] = hypothesis
    packet = _refresh_packet_identity(packet)
    routing = build_creative_hypothesis_agent_routing(packet)
    dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=packet,
        routing=routing,
    )
    selected_targets = (
        approved_targets if approved_targets is not None else list(hypothesis["target_surfaces"])
    )
    approval = build_creative_hypothesis_approval(
        hypothesis_id=hypothesis["hypothesis_id"],
        decision=decision,
        hypothesis_packet=packet if decision == "approve_for_pr1_specification" else None,
        approved_target_surfaces=selected_targets,
        approved_agents=[dispatch["dispatch"][0]["primary_agent"]] if selected_targets else [],
        next_step=next_step,
    )
    return context, packet, dispatch, approval


def _bundle() -> dict[str, dict[str, Any]]:
    context, packet, dispatch, approval = _chain()
    return build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )


def _refresh_bridge_identity(bridge: dict[str, Any]) -> dict[str, Any]:
    source = bridge["source"]
    candidate_ref = bridge["candidate_packet"]
    bridge_id, idempotency_key = _bridge_artifact_identity(
        _bridge_identity_payload(bridge),
        artifact_type=BRIDGE_ARTIFACT_TYPE,
        upstream_ids=(
            str(source["hypothesis_packet_id"]),
            str(source["approval_id"]),
            str(candidate_ref["candidate_id"]),
        ),
    )
    artifact_root_ref = f"artifacts/orchestration/creative_code/spec_bridge/{bridge_id}"
    bridge["bridge_id"] = bridge_id
    bridge["idempotency_key"] = idempotency_key
    bridge["candidate_packet"][
        "candidate_packet_ref"
    ] = f"{artifact_root_ref}/creative_code_candidate_packet.json"
    bridge["spec_prepare"]["run_dir_ref"] = f"{artifact_root_ref}/spec_prepare"
    return bridge


def _write_creative_context_inputs(
    *,
    leaf: str,
    context: dict[str, Any],
    packet: dict[str, Any],
    dispatch: dict[str, Any],
    approval: dict[str, Any],
) -> tuple[Path, Path, Path, Path, Path]:
    input_dir = cli.CREATIVE_CONTEXT_ROOT / leaf
    shutil.rmtree(input_dir, ignore_errors=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    paths = (
        input_dir / "context_map.json",
        input_dir / "hypothesis_packet.json",
        input_dir / "coordinator_dispatch.json",
        input_dir / "approval.json",
    )
    for path, payload in zip(paths, (context, packet, dispatch, approval), strict=True):
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return input_dir, *paths


def test_valid_approval_builds_valid_candidate_and_metrics() -> None:
    bundle = _bundle()
    candidate = validate_creative_code_candidate_packet(bundle["candidate"])
    bridge = bundle["bridge"]
    metrics = validate_bridge_metrics(bundle["metrics"])

    assert bridge["artifact_type"] == BRIDGE_ARTIFACT_TYPE
    assert bridge["policy_version"] == POLICY_VERSION
    assert candidate["target_surface"] == ["docs/prompts/cv/program.md"]
    assert "tests/test_creative_hypothesis_spec_bridge.py" in candidate["immutable_oracles"]
    assert (
        "docs/orchestration/contracts/creative_hypothesis_specification_bridge.v1.schema.json"
        in candidate["immutable_oracles"]
    )
    assert metrics["artifact_type"] == METRICS_ARTIFACT_TYPE
    assert metrics["status"] == BRIDGE_SUCCESS_STATUS
    assert metrics["blocked_reason"] is None
    assert metrics["counts"]["candidate_target_count"] == 1
    assert metrics["counts"]["immutable_oracle_count"] >= 2
    assert metrics["cost_metadata"] == {
        "provider_cost_available": False,
        "provider_call_count": 0,
        "provider_cost_basis": "not_available_local_no_provider_calls",
    }
    assert all(
        value is False for key, value in metrics["authority"].items() if key.startswith("open_")
    )


def test_same_inputs_are_deterministic() -> None:
    first = _bundle()
    second = _bundle()

    assert first == second


def test_dispatch_fingerprint_mismatch_rejects_before_candidate_output() -> None:
    context, packet, dispatch, approval = _chain()
    dispatch["source_hypothesis_packet_fingerprint"] = SHA256_D
    dispatch = _refresh_dispatch_identity(dispatch)

    with pytest.raises(CreativeHypothesisSpecBridgeError, match="fingerprint_mismatch"):
        build_creative_hypothesis_spec_bridge_bundle(
            context_map=context,
            hypothesis_packet=packet,
            coordinator_dispatch=dispatch,
            approval=approval,
            variant_count=3,
        )


def test_stale_approval_rejects_changed_hypothesis_fingerprint() -> None:
    context, packet, _dispatch, approval = _chain(hypothesis_suffix="stale-approval")
    mutated_packet = deepcopy(packet)
    mutated_hypothesis = dict(mutated_packet["hypotheses"][0])
    mutated_hypothesis["expected_behavior"] = (
        "Changed hypothesis content must require a fresh human approval binding."
    )
    mutated_packet["hypotheses"][0] = mutated_hypothesis
    mutated_packet = _refresh_packet_identity(mutated_packet)
    routing = build_creative_hypothesis_agent_routing(mutated_packet)
    dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=mutated_packet,
        routing=routing,
    )

    with pytest.raises(CreativeHypothesisSpecBridgeError, match="approval must bind"):
        build_creative_hypothesis_spec_bridge_bundle(
            context_map=context,
            hypothesis_packet=mutated_packet,
            coordinator_dispatch=dispatch,
            approval=approval,
            variant_count=3,
        )


def test_blocked_hypothesis_packet_cannot_build_candidate() -> None:
    context, packet, _dispatch, _approval = _chain(hypothesis_suffix="blocked-packet")
    blocked_packet = deepcopy(packet)
    blocked_packet["creative_status"] = "blocked"
    blocked_packet = _refresh_packet_identity(blocked_packet)
    routing = build_creative_hypothesis_agent_routing(blocked_packet)
    dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=blocked_packet,
        routing=routing,
    )
    approval = build_creative_hypothesis_approval(
        hypothesis_id=blocked_packet["hypotheses"][0]["hypothesis_id"],
        decision="approve_for_pr1_specification",
        hypothesis_packet=blocked_packet,
        approved_target_surfaces=blocked_packet["hypotheses"][0]["target_surfaces"],
        approved_agents=[dispatch["dispatch"][0]["primary_agent"]],
        next_step="create_pr1_specification",
    )

    with pytest.raises(
        CreativeHypothesisSpecBridgeError,
        match="bridge requires a generated hypothesis packet",
    ):
        build_creative_hypothesis_spec_bridge_bundle(
            context_map=context,
            hypothesis_packet=blocked_packet,
            coordinator_dispatch=dispatch,
            approval=approval,
            variant_count=3,
        )


@pytest.mark.parametrize(
    ("decision", "next_step"),
    [
        ("reject", "no_action"),
        ("defer", "defer"),
    ],
)
def test_reject_or_defer_approval_cannot_build_candidate(
    decision: str,
    next_step: str,
) -> None:
    context, packet, dispatch, approval = _chain(
        approved_targets=[],
        decision=decision,
        next_step=next_step,
    )

    with pytest.raises(CreativeHypothesisSpecBridgeError, match="approval_not_pr1"):
        build_creative_hypothesis_spec_bridge_bundle(
            context_map=context,
            hypothesis_packet=packet,
            coordinator_dispatch=dispatch,
            approval=approval,
            variant_count=3,
        )


def test_approved_scripts_tests_and_docs_targets_become_immutable_oracles() -> None:
    bundle = _bundle()
    candidate = bundle["candidate"]

    assert candidate["target_surface"] == ["docs/prompts/cv/program.md"]
    assert (
        "scripts/orchestration/creative_hypothesis_spec_bridge.py" in candidate["immutable_oracles"]
    )
    assert "tests/test_creative_hypothesis_spec_bridge.py" in candidate["immutable_oracles"]


def test_no_allowed_mutable_target_fails_closed() -> None:
    context, packet, dispatch, approval = _chain(
        approved_targets=[
            "scripts/orchestration/creative_hypothesis_spec_bridge.py",
            "tests/test_creative_hypothesis_spec_bridge.py",
            "docs/orchestration/contracts/creative_hypothesis_specification_bridge.v1.schema.json",
        ],
    )

    with pytest.raises(CreativeHypothesisSpecBridgeError, match=NO_ALLOWED_MUTABLE_TARGET):
        build_creative_hypothesis_spec_bridge_bundle(
            context_map=context,
            hypothesis_packet=packet,
            coordinator_dispatch=dispatch,
            approval=approval,
            variant_count=3,
        )


def test_metrics_sidecar_is_redacted_and_rejects_unsafe_claims() -> None:
    metrics = deepcopy(_bundle()["metrics"])
    serialized = json.dumps(metrics, sort_keys=True)

    for forbidden in (
        "raw_prompt",
        "provider_payload",
        "candidate.patch",
        "diff --git",
        "/Users/",
        "sk-proj-",
        "semantic-cache",
        "graph truth",
        "mergeable",
    ):
        assert forbidden not in serialized

    metrics["source"]["approval_id"] = "raw_prompt"
    with pytest.raises(ValueError):
        validate_bridge_metrics(metrics)

    metrics = deepcopy(_bundle()["metrics"])
    metrics["counts"]["candidate_target_count"] = 101
    with pytest.raises(ValueError):
        validate_bridge_metrics(metrics)


def test_bridge_validator_rejects_loose_spec_bridge_artifact_refs() -> None:
    bridge = deepcopy(_bundle()["bridge"])
    bridge["candidate_packet"][
        "candidate_packet_ref"
    ] = "artifacts/orchestration/creative_code/spec_bridge/-unsafe/candidate.json"
    with pytest.raises(CreativeHypothesisSpecBridgeError, match="spec_bridge local artifact"):
        validate_creative_hypothesis_specification_bridge(bridge)

    bridge = deepcopy(_bundle()["bridge"])
    bridge["spec_prepare"][
        "run_dir_ref"
    ] = "artifacts/orchestration/creative_code/spec_bridge/-unsafe/spec_prepare"
    with pytest.raises(CreativeHypothesisSpecBridgeError, match="spec_bridge local artifact"):
        validate_creative_hypothesis_specification_bridge(bridge)


def test_cli_build_and_prepare_writes_four_prepare_artifacts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix="happy")
    expected_bundle = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    bridge_id = str(expected_bundle["bridge"]["bridge_id"])
    assert (
        expected_bundle["bridge"]["spec_prepare"]["next_allowed_action"] == "prepare_specification"
    )
    output_dir = cli.SPEC_BRIDGE_ROOT / bridge_id
    shutil.rmtree(output_dir, ignore_errors=True)
    input_dir, context_path, packet_path, dispatch_path, approval_path = (
        _write_creative_context_inputs(
            leaf="pytest-spec-bridge-happy",
            context=context,
            packet=packet,
            dispatch=dispatch,
            approval=approval,
        )
    )
    try:
        exit_code = cli.main(
            [
                "build-and-prepare",
                "--context-map",
                str(context_path),
                "--hypothesis-packet",
                str(packet_path),
                "--coordinator-dispatch",
                str(dispatch_path),
                "--approval",
                str(approval_path),
                "--variant-count",
                "3",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        assert captured.out.strip() == cli.SUCCESS_BUILD_PREPARE_OUTPUT
        assert captured.err == ""
        assert (output_dir / cli.BRIDGE_FILENAME).is_file()
        assert (output_dir / cli.CANDIDATE_FILENAME).is_file()
        assert (output_dir / cli.METRICS_FILENAME).is_file()
        spec_prepare_dir = output_dir / "spec_prepare"
        assert sorted(path.name for path in spec_prepare_dir.iterdir()) == sorted(
            list(PREPARE_FILENAMES)
        )
        assert not (spec_prepare_dir / "bundle.json").exists()
        metrics = json.loads((output_dir / cli.METRICS_FILENAME).read_text(encoding="utf-8"))
        bridge = json.loads((output_dir / cli.BRIDGE_FILENAME).read_text(encoding="utf-8"))
        assert bridge["spec_prepare"]["next_allowed_action"] == "agent_skeptic_review"
        assert metrics["status"] == "prepared"
        assert metrics["counts"]["prepare_files_written"] == 4
        assert metrics["counts"]["pending_skeptic_review_count"] == 9
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_prepare_specification_rejects_candidate_tampering(
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix="tamper")
    expected_bundle = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    bridge_id = str(expected_bundle["bridge"]["bridge_id"])
    output_dir = cli.SPEC_BRIDGE_ROOT / bridge_id
    shutil.rmtree(output_dir, ignore_errors=True)
    input_dir, context_path, packet_path, dispatch_path, approval_path = (
        _write_creative_context_inputs(
            leaf="pytest-spec-bridge-tamper",
            context=context,
            packet=packet,
            dispatch=dispatch,
            approval=approval,
        )
    )
    try:
        assert (
            cli.main(
                [
                    "build-candidate",
                    "--context-map",
                    str(context_path),
                    "--hypothesis-packet",
                    str(packet_path),
                    "--coordinator-dispatch",
                    str(dispatch_path),
                    "--approval",
                    str(approval_path),
                    "--variant-count",
                    "3",
                ]
            )
            == 0
        )
        capsys.readouterr()
        candidate_path = output_dir / cli.CANDIDATE_FILENAME
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["candidate_id"] = "tampered-candidate-id"
        candidate_path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n")

        exit_code = cli.main(
            [
                "prepare-specification",
                "--bridge",
                str(output_dir / cli.BRIDGE_FILENAME),
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 1
        assert captured.out == ""
        assert "fingerprint_mismatch" in captured.err
        bridge = json.loads((output_dir / cli.BRIDGE_FILENAME).read_text(encoding="utf-8"))
        metrics = json.loads((output_dir / cli.METRICS_FILENAME).read_text(encoding="utf-8"))
        assert bridge["spec_prepare"]["prepared"] is False
        assert metrics["status"] == "blocked"
        assert metrics["blocked_reason"] == "fingerprint_mismatch"
        assert not (output_dir / "spec_prepare" / "source_packet.json").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_and_prepare_reject_bridge_candidate_parity_mismatch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix="parity")
    bundle = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    bridge = deepcopy(bundle["bridge"])
    bridge["selected_hypothesis"]["immutable_oracles"] = bridge["selected_hypothesis"][
        "immutable_oracles"
    ][:1]
    bridge = _refresh_bridge_identity(bridge)
    metrics = build_bridge_metrics(
        bridge=bridge,
        candidate=bundle["candidate"],
        hypothesis_packet=packet,
        approval=approval,
        status=BRIDGE_SUCCESS_STATUS,
        prepare_files_written=0,
        pending_skeptic_review_count=0,
    )
    output_dir = cli.SPEC_BRIDGE_ROOT / str(bridge["bridge_id"])
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        (output_dir / cli.BRIDGE_FILENAME).write_text(
            json.dumps(bridge, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / cli.CANDIDATE_FILENAME).write_text(
            json.dumps(bundle["candidate"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / cli.METRICS_FILENAME).write_text(
            json.dumps(metrics, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        exit_code = cli.main(["validate", "--bridge", str(output_dir / cli.BRIDGE_FILENAME)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "candidate immutable_oracles" in captured.err

        exit_code = cli.main(
            ["prepare-specification", "--bridge", str(output_dir / cli.BRIDGE_FILENAME)]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "candidate immutable_oracles" in captured.err
        blocked_metrics = json.loads((output_dir / cli.METRICS_FILENAME).read_text("utf-8"))
        assert blocked_metrics["status"] == "blocked"
        assert blocked_metrics["blocked_reason"] == "fingerprint_mismatch"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_prepare_rejects_swapped_metrics_before_prepare(
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix="swapped-metrics")
    input_dir, context_path, packet_path, dispatch_path, approval_path = (
        _write_creative_context_inputs(
            leaf="pytest-spec-bridge-swapped-metrics",
            context=context,
            packet=packet,
            dispatch=dispatch,
            approval=approval,
        )
    )
    first = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    second = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=4,
    )
    first_dir = cli.SPEC_BRIDGE_ROOT / str(first["bridge"]["bridge_id"])
    second_dir = cli.SPEC_BRIDGE_ROOT / str(second["bridge"]["bridge_id"])
    shutil.rmtree(first_dir, ignore_errors=True)
    shutil.rmtree(second_dir, ignore_errors=True)
    try:
        for variant_count in ("3", "4"):
            assert (
                cli.main(
                    [
                        "build-candidate",
                        "--context-map",
                        str(context_path),
                        "--hypothesis-packet",
                        str(packet_path),
                        "--coordinator-dispatch",
                        str(dispatch_path),
                        "--approval",
                        str(approval_path),
                        "--variant-count",
                        variant_count,
                    ]
                )
                == 0
            )
            capsys.readouterr()

        shutil.copyfile(second_dir / cli.METRICS_FILENAME, first_dir / cli.METRICS_FILENAME)
        exit_code = cli.main(
            ["prepare-specification", "--bridge", str(first_dir / cli.BRIDGE_FILENAME)]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "fingerprint_mismatch" in captured.err
        assert not (first_dir / "spec_prepare" / "source_packet.json").exists()
        metrics = json.loads((first_dir / cli.METRICS_FILENAME).read_text(encoding="utf-8"))
        assert metrics["status"] == "blocked"
        assert metrics["blocked_reason"] == "fingerprint_mismatch"
        assert metrics["bridge_id"] == first["bridge"]["bridge_id"]
        assert metrics["candidate_id"] == first["candidate"]["candidate_id"]
    finally:
        shutil.rmtree(first_dir, ignore_errors=True)
        shutil.rmtree(second_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_prepare_rejects_stale_spec_prepare_artifacts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix="stale-prepare-file")
    input_dir, context_path, packet_path, dispatch_path, approval_path = (
        _write_creative_context_inputs(
            leaf="pytest-spec-bridge-stale-prepare-file",
            context=context,
            packet=packet,
            dispatch=dispatch,
            approval=approval,
        )
    )
    bundle = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    output_dir = cli.SPEC_BRIDGE_ROOT / str(bundle["bridge"]["bridge_id"])
    shutil.rmtree(output_dir, ignore_errors=True)
    try:
        assert (
            cli.main(
                [
                    "build-candidate",
                    "--context-map",
                    str(context_path),
                    "--hypothesis-packet",
                    str(packet_path),
                    "--coordinator-dispatch",
                    str(dispatch_path),
                    "--approval",
                    str(approval_path),
                    "--variant-count",
                    "3",
                ]
            )
            == 0
        )
        capsys.readouterr()
        spec_prepare_dir = output_dir / "spec_prepare"
        spec_prepare_dir.mkdir(parents=True, exist_ok=True)
        (spec_prepare_dir / "bundle.json").write_text("{}\n", encoding="utf-8")

        exit_code = cli.main(
            ["prepare-specification", "--bridge", str(output_dir / cli.BRIDGE_FILENAME)]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "unexpected spec_prepare artifact" in captured.err
        metrics = json.loads((output_dir / cli.METRICS_FILENAME).read_text(encoding="utf-8"))
        assert metrics["status"] == "blocked"
        assert metrics["blocked_reason"] == "spec_prepare_failed"
        assert not (spec_prepare_dir / "source_packet.json").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_prepare_rejects_already_prepared_bridge_without_rewriting_reviews(
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix="already-prepared")
    input_dir, context_path, packet_path, dispatch_path, approval_path = (
        _write_creative_context_inputs(
            leaf="pytest-spec-bridge-already-prepared",
            context=context,
            packet=packet,
            dispatch=dispatch,
            approval=approval,
        )
    )
    bundle = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    output_dir = cli.SPEC_BRIDGE_ROOT / str(bundle["bridge"]["bridge_id"])
    shutil.rmtree(output_dir, ignore_errors=True)
    try:
        assert (
            cli.main(
                [
                    "build-and-prepare",
                    "--context-map",
                    str(context_path),
                    "--hypothesis-packet",
                    str(packet_path),
                    "--coordinator-dispatch",
                    str(dispatch_path),
                    "--approval",
                    str(approval_path),
                    "--variant-count",
                    "3",
                ]
            )
            == 0
        )
        capsys.readouterr()
        reviews_path = output_dir / "spec_prepare" / "skeptic_reviews.json"
        reviews = json.loads(reviews_path.read_text(encoding="utf-8"))
        reviews[0]["decision"] = "pass"
        reviews[0]["blockers"] = []
        reviews_path.write_text(json.dumps(reviews, indent=2, sort_keys=True) + "\n")
        expected_fingerprint = fingerprint_payload(reviews)

        exit_code = cli.main(
            ["prepare-specification", "--bridge", str(output_dir / cli.BRIDGE_FILENAME)]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "spec_prepare_already_prepared" in captured.err
        assert (
            fingerprint_payload(json.loads(reviews_path.read_text("utf-8"))) == expected_fingerprint
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_rejects_candidate_and_metrics_mismatch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix="validate-mismatch")
    input_dir, context_path, packet_path, dispatch_path, approval_path = (
        _write_creative_context_inputs(
            leaf="pytest-spec-bridge-validate",
            context=context,
            packet=packet,
            dispatch=dispatch,
            approval=approval,
        )
    )
    first = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    second = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=4,
    )
    first_dir = cli.SPEC_BRIDGE_ROOT / str(first["bridge"]["bridge_id"])
    second_dir = cli.SPEC_BRIDGE_ROOT / str(second["bridge"]["bridge_id"])
    shutil.rmtree(first_dir, ignore_errors=True)
    shutil.rmtree(second_dir, ignore_errors=True)
    try:
        assert (
            cli.main(
                [
                    "build-candidate",
                    "--context-map",
                    str(context_path),
                    "--hypothesis-packet",
                    str(packet_path),
                    "--coordinator-dispatch",
                    str(dispatch_path),
                    "--approval",
                    str(approval_path),
                    "--variant-count",
                    "3",
                ]
            )
            == 0
        )
        capsys.readouterr()
        assert (
            cli.main(
                [
                    "build-candidate",
                    "--context-map",
                    str(context_path),
                    "--hypothesis-packet",
                    str(packet_path),
                    "--coordinator-dispatch",
                    str(dispatch_path),
                    "--approval",
                    str(approval_path),
                    "--variant-count",
                    "4",
                ]
            )
            == 0
        )
        capsys.readouterr()

        assert cli.main(["validate", "--bridge", str(first_dir / cli.BRIDGE_FILENAME)]) == 0
        capsys.readouterr()

        first_candidate = json.loads(
            (first_dir / cli.CANDIDATE_FILENAME).read_text(encoding="utf-8")
        )
        first_candidate["candidate_id"] = "tampered-candidate-id"
        tampered_candidate = first_dir / "tampered_candidate.json"
        tampered_candidate.write_text(
            json.dumps(first_candidate, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        exit_code = cli.main(
            [
                "validate",
                "--bridge",
                str(first_dir / cli.BRIDGE_FILENAME),
                "--candidate",
                str(tampered_candidate),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "fingerprint_mismatch" in captured.err

        exit_code = cli.main(
            [
                "validate",
                "--bridge",
                str(first_dir / cli.BRIDGE_FILENAME),
                "--metrics",
                str(second_dir / cli.METRICS_FILENAME),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "fingerprint_mismatch" in captured.err
    finally:
        shutil.rmtree(first_dir, ignore_errors=True)
        shutil.rmtree(second_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_rejects_prepared_bridge_with_unprepared_metrics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix="prepared-metrics")
    bundle = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    bridge = mark_bridge_prepared(bundle["bridge"])
    output_dir = cli.SPEC_BRIDGE_ROOT / str(bridge["bridge_id"])
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        (output_dir / cli.BRIDGE_FILENAME).write_text(
            json.dumps(bridge, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / cli.CANDIDATE_FILENAME).write_text(
            json.dumps(bundle["candidate"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / cli.METRICS_FILENAME).write_text(
            json.dumps(bundle["metrics"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        exit_code = cli.main(["validate", "--bridge", str(output_dir / cli.BRIDGE_FILENAME)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "prepared bridge requires prepared metrics" in captured.err
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.parametrize(
    ("bridge_section", "bridge_key", "expected_error"),
    (
        (
            "candidate_packet",
            "candidate_packet_ref",
            "candidate_packet_ref must match the bridge id",
        ),
        ("spec_prepare", "run_dir_ref", "run_dir_ref must match the bridge id"),
    ),
)
def test_validate_and_prepare_reject_cross_bridge_refs(
    capsys: pytest.CaptureFixture[str],
    bridge_section: str,
    bridge_key: str,
    expected_error: str,
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix=f"cross-ref-{bridge_key}")
    input_dir, context_path, packet_path, dispatch_path, approval_path = (
        _write_creative_context_inputs(
            leaf=f"pytest-spec-bridge-cross-ref-{bridge_key}",
            context=context,
            packet=packet,
            dispatch=dispatch,
            approval=approval,
        )
    )
    first = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    second = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=4,
    )
    first_dir = cli.SPEC_BRIDGE_ROOT / str(first["bridge"]["bridge_id"])
    second_dir = cli.SPEC_BRIDGE_ROOT / str(second["bridge"]["bridge_id"])
    shutil.rmtree(first_dir, ignore_errors=True)
    shutil.rmtree(second_dir, ignore_errors=True)
    try:
        for variant_count in ("3", "4"):
            assert (
                cli.main(
                    [
                        "build-candidate",
                        "--context-map",
                        str(context_path),
                        "--hypothesis-packet",
                        str(packet_path),
                        "--coordinator-dispatch",
                        str(dispatch_path),
                        "--approval",
                        str(approval_path),
                        "--variant-count",
                        variant_count,
                    ]
                )
                == 0
            )
            capsys.readouterr()

        bridge_path = first_dir / cli.BRIDGE_FILENAME
        bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
        bridge[bridge_section][bridge_key] = second["bridge"][bridge_section][bridge_key]
        bridge_path.write_text(
            json.dumps(bridge, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        for command in ("validate", "prepare-specification"):
            exit_code = cli.main([command, "--bridge", str(bridge_path)])
            captured = capsys.readouterr()
            assert exit_code == 1
            assert expected_error in captured.err
        assert not (second_dir / "spec_prepare" / "source_packet.json").exists()
    finally:
        shutil.rmtree(first_dir, ignore_errors=True)
        shutil.rmtree(second_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_cli_failure_prints_single_fail_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, dispatch, approval = _chain(
        approved_targets=[
            "scripts/orchestration/creative_hypothesis_spec_bridge.py",
            "tests/test_creative_hypothesis_spec_bridge.py",
        ],
    )
    input_dir, context_path, packet_path, dispatch_path, approval_path = (
        _write_creative_context_inputs(
            leaf="pytest-spec-bridge-failure",
            context=context,
            packet=packet,
            dispatch=dispatch,
            approval=approval,
        )
    )

    try:
        exit_code = cli.main(
            [
                "build-candidate",
                "--context-map",
                str(context_path),
                "--hypothesis-packet",
                str(packet_path),
                "--coordinator-dispatch",
                str(dispatch_path),
                "--approval",
                str(approval_path),
                "--variant-count",
                "3",
            ]
        )
        captured = capsys.readouterr()
    finally:
        shutil.rmtree(input_dir, ignore_errors=True)

    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.startswith(f"FAIL: {NO_ALLOWED_MUTABLE_TARGET}")
    assert captured.err.count("\n") == 1


def test_cli_rejects_outside_repo_and_symlink_inputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix="input-guard")
    input_dir, _context_path, packet_path, dispatch_path, approval_path = (
        _write_creative_context_inputs(
            leaf="pytest-spec-bridge-input-guard",
            context=context,
            packet=packet,
            dispatch=dispatch,
            approval=approval,
        )
    )
    outside_context = tmp_path / "context_map.json"
    outside_context.write_text(json.dumps(context), encoding="utf-8")
    try:
        exit_code = cli.main(
            [
                "build-candidate",
                "--context-map",
                str(outside_context),
                "--hypothesis-packet",
                str(packet_path),
                "--coordinator-dispatch",
                str(dispatch_path),
                "--approval",
                str(approval_path),
                "--variant-count",
                "3",
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "must stay inside the repository" in captured.err

        capsys.readouterr()
        symlink_context = input_dir / "context_map_link.json"
        symlink_context.symlink_to(input_dir / "context_map.json")
        exit_code = cli.main(
            [
                "build-candidate",
                "--context-map",
                str(symlink_context),
                "--hypothesis-packet",
                str(packet_path),
                "--coordinator-dispatch",
                str(dispatch_path),
                "--approval",
                str(approval_path),
                "--variant-count",
                "3",
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "must not traverse symlinks" in captured.err
    finally:
        shutil.rmtree(input_dir, ignore_errors=True)


def test_cli_rejects_noncanonical_output_dir(
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix="output-dir")
    expected_bundle = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    bridge_id = str(expected_bundle["bridge"]["bridge_id"])
    custom_dir = cli.SPEC_BRIDGE_ROOT / "custom-review" / bridge_id
    input_dir, context_path, packet_path, dispatch_path, approval_path = (
        _write_creative_context_inputs(
            leaf="pytest-spec-bridge-output-dir",
            context=context,
            packet=packet,
            dispatch=dispatch,
            approval=approval,
        )
    )
    shutil.rmtree(custom_dir.parent, ignore_errors=True)
    try:
        exit_code = cli.main(
            [
                "build-candidate",
                "--context-map",
                str(context_path),
                "--hypothesis-packet",
                str(packet_path),
                "--coordinator-dispatch",
                str(dispatch_path),
                "--approval",
                str(approval_path),
                "--variant-count",
                "3",
                "--output-dir",
                str(custom_dir),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "canonical spec_bridge/<bridge-id>" in captured.err
        assert not custom_dir.exists()
    finally:
        shutil.rmtree(custom_dir.parent, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_rejects_symlinked_bridge_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix="bridge-link")
    bundle = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    output_dir = cli.SPEC_BRIDGE_ROOT / str(bundle["bridge"]["bridge_id"])
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    bridge_path = output_dir / cli.BRIDGE_FILENAME
    bridge_path.write_text(
        json.dumps(bundle["bridge"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    symlink_path = output_dir / "bridge_link.json"
    symlink_path.symlink_to(bridge_path)
    try:
        exit_code = cli.main(["validate", "--bridge", str(symlink_path)])
        captured = capsys.readouterr()

        assert exit_code == 1
        assert "must not traverse symlinks" in captured.err
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_validate_and_prepare_reject_default_metrics_symlink(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    context, packet, dispatch, approval = _chain(hypothesis_suffix="metrics-link")
    input_dir, context_path, packet_path, dispatch_path, approval_path = (
        _write_creative_context_inputs(
            leaf="pytest-spec-bridge-metrics-link",
            context=context,
            packet=packet,
            dispatch=dispatch,
            approval=approval,
        )
    )
    bundle = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    output_dir = cli.SPEC_BRIDGE_ROOT / str(bundle["bridge"]["bridge_id"])
    shutil.rmtree(output_dir, ignore_errors=True)
    outside_metrics = tmp_path / cli.METRICS_FILENAME
    outside_metrics.write_text(
        json.dumps(bundle["metrics"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        assert (
            cli.main(
                [
                    "build-candidate",
                    "--context-map",
                    str(context_path),
                    "--hypothesis-packet",
                    str(packet_path),
                    "--coordinator-dispatch",
                    str(dispatch_path),
                    "--approval",
                    str(approval_path),
                    "--variant-count",
                    "3",
                ]
            )
            == 0
        )
        capsys.readouterr()
        metrics_path = output_dir / cli.METRICS_FILENAME
        metrics_path.unlink()
        metrics_path.symlink_to(outside_metrics)

        for command in ("validate", "prepare-specification"):
            exit_code = cli.main(
                [
                    command,
                    "--bridge",
                    str(output_dir / cli.BRIDGE_FILENAME),
                ]
            )
            captured = capsys.readouterr()
            assert exit_code == 1
            assert "must not traverse symlinks" in captured.err
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_new_schemas_are_closed() -> None:
    for filename in (
        "creative_hypothesis_specification_bridge.v1.schema.json",
        "creative_hypothesis_spec_bridge_metrics.v1.schema.json",
    ):
        schema = json.loads(
            (REPO_ROOT / "docs/orchestration/contracts" / filename).read_text(encoding="utf-8")
        )
        assert schema["additionalProperties"] is False
        assert schema["properties"]["authority"]["$ref"] == "#/$defs/bridge_authority"
        assert schema["$defs"]["bridge_authority"]["additionalProperties"] is False
        if filename == "creative_hypothesis_specification_bridge.v1.schema.json":
            repo_path_pattern = schema["$defs"]["repo_path"]["not"]["pattern"]
            assert "(?:^|/)\\.\\.?(?:/|$)" in repo_path_pattern
            assert "artifacts" in repo_path_pattern
            spec_prepare = schema["$defs"]["spec_prepare"]
            assert spec_prepare["properties"]["next_allowed_action"]["enum"] == [
                "prepare_specification",
                "agent_skeptic_review",
            ]
            prepared_guards = spec_prepare["allOf"]
            assert (
                prepared_guards[0]["then"]["properties"]["next_allowed_action"]["const"]
                == "prepare_specification"
            )
            assert (
                prepared_guards[1]["then"]["properties"]["next_allowed_action"]["const"]
                == "agent_skeptic_review"
            )


def test_bridge_modules_do_not_import_downstream_mutation_surfaces() -> None:
    banned_prefixes = (
        "app",
        "httpx",
        "requests",
        "slack",
        "github",
        "scripts.orchestration.creative_code_patch",
        "scripts.orchestration.creative_code_pr_promotion",
    )
    banned_exact = {
        "scripts.orchestration.experiment_runner",
        "scripts.orchestration.experiment_pipeline",
    }
    for module_path in (
        REPO_ROOT / "scripts/orchestration/creative_hypothesis_spec_bridge.py",
        REPO_ROOT / "scripts/orchestration/creative_hypothesis_spec_bridge_contract.py",
    ):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        assert not [
            imported
            for imported in imports
            if imported in banned_exact or imported.startswith(banned_prefixes)
        ]
