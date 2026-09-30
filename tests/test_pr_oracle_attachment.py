"""Behavioral regressions for local oracle composition and retained evidence."""

from __future__ import annotations

import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any
import zipfile

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import experiment_runner_pr_creative_context as context
from scripts.orchestration import pr_oracle_attachment as oracle
from scripts.orchestration import experiment_contract
from scripts.orchestration import qoder_dispatch_bridge
from scripts.orchestration.task_bootstrap import build_task_packet
from scripts.orchestration import evidence_rail_applicability as rails
from scripts.orchestration.experiment_contract import validate_experiment_packet


def _accepted_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    budgets = {
        "wall_clock_seconds": 30,
        "retry_budget": 1,
        "network_budget": 0,
        "max_changed_files": 1,
        "test_budget": 1,
        "benchmark_budget": 1,
        "stop_condition": "Stop on any failure.",
    }
    packet = {
        "schema_version": "1.0",
        "experiment_id": "oracle-test",
        "runner_mode": "oracle_only_governance_reviewer",
        "decision_question": "Verify the approved local oracle",
        "task_class": "Orchestration",
        "mutable_candidate_surface": ["scripts/orchestration"],
        "immutable_oracles": [{"command": "git --version", "expected_signal": "must pass"}],
        "budgets": budgets,
        "metrics": {
            "primary": "strict_isolation",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": ["network remains unavailable", "shared checkout remains unchanged"],
        "promotion_target": "audit_artifact",
    }
    material = {
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "base_sha": "f" * 40,
        "head_sha": "f" * 40,
        "admitted_new_files": [],
        "tracked_content_sha256": "c" * 64,
    }
    request = {
        "source_material": material,
        "backend": "apple-container",
        "image": "test/runner@sha256:" + "a" * 64,
        "contribution": {"kind": "none", "coauthor_required": False, "reason": ""},
    }
    backend = {
        "name": "apple-container",
        "guest_platform": "linux_arm64",
        "runtime_version": "1.1.0",
        "image_digest": "sha256:" + "a" * 64,
        "network_isolation": "guest_unshare_net",
        "preflight_status": "passed",
    }
    result = {
        "schema_version": "1.0",
        "experiment_id": "oracle-test",
        "runner_mode": "oracle_only_governance_reviewer",
        "status": "accepted",
        "failure_class": None,
        "mutated_paths": [],
        "candidate_patch": "oracle_only_governance_reviewer",
        "oracle_results": [
            {
                "command": "git --version",
                "returncode": 0,
                "timed_out": False,
                "stdout": "",
                "stderr": "",
                "cwd": "owned_guest_checkout",
                "truncated": False,
            }
        ],
        "budget_observations": {
            "configured_budgets": budgets,
            "oracle_commands_configured": 1,
            "oracle_commands_executed": 1,
            "attempts": 1,
            "retries_consumed": 0,
        },
        "shared_tree_untouched": True,
        "promotion_ready": False,
        "execution_backend": backend,
        "contribution_kind": "none",
        "coauthor_required": False,
        "coauthor_reason": "",
    }
    backend["network_isolation"] = oracle.dispatcher._isolation_method("apple-container")
    proof = {
        "schema_version": "experiment_runner_checked_snapshot.v1",
        "authority": "evidence_only",
        "source_material": material,
        "snapshot_diff_sha256": "b" * 64,
        "copied_new_files": [],
        "experiment_packet_fingerprint": fingerprint_payload(packet),
        "result_fingerprint": fingerprint_payload(result),
        "execution_backend": backend,
        "result_projection": "sanitized_command_observations_v1",
        "snapshot_content_sha256": "c" * 64,
    }
    return packet, request, result, proof


def test_complete_accepted_conjunction() -> None:
    packet, request, result, proof = _accepted_inputs()
    validated = oracle._accepted(result, packet, proof, request)
    assert validated["status"] == "accepted"
    assert validated["coauthor_required"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("oracle_results", []),
        ("shared_tree_untouched", False),
        ("execution_backend", None),
        ("experiment_id", "another-experiment"),
        ("promotion_ready", True),
    ],
)
def test_structurally_accepted_counterexamples_are_not_consumable(field: str, value: Any) -> None:
    packet, request, result, proof = _accepted_inputs()
    result[field] = value
    with pytest.raises(ValueError):
        oracle._accepted(result, packet, proof, request)


@pytest.mark.parametrize(
    "field,value",
    [
        ("returncode", 1),
        ("timed_out", True),
        ("command", "git status"),
        ("stdout", "private output"),
    ],
)
def test_failed_substituted_or_raw_command_observation_rejected(field: str, value: Any) -> None:
    packet, request, result, proof = _accepted_inputs()
    result["oracle_results"][0][field] = value
    with pytest.raises(ValueError):
        oracle._accepted(result, packet, proof, request)


@pytest.fixture
def evidence_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, Any], list[list[str]], dict[str, Any]]:
    root = tmp_path.resolve()
    store = root / "artifacts/orchestration/experiments/results"
    task = build_task_packet(
        goal="Verify retained local oracle evidence",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration"],
        pr_phase="pre_open",
    )
    task_raw = json.dumps(task).encode()
    monkeypatch.setattr(oracle, "REPO_ROOT", root)
    monkeypatch.setattr(oracle, "EVIDENCE_ROOT", store / "oracle_attachments")
    monkeypatch.setattr(context, "REPO_ROOT", root)
    monkeypatch.setattr(oracle.dispatcher, "RESULT_ARTIFACT_DIR", store)
    packet, request, result, proof = _accepted_inputs()
    task_ref = f"artifacts/orchestration/task_packets/{task['task_packet_id']}.json"
    experiment_ref = "artifacts/orchestration/experiments/test.json"
    for ref, raw in [(task_ref, task_raw), (experiment_ref, json.dumps(packet).encode())]:
        target = root / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    request.update(
        {
            "policy_version": oracle.POLICY_VERSION,
            "selector_policy_version": oracle.SELECTOR_POLICY,
            "task_packet_ref": task_ref,
            "task_packet_id": task["task_packet_id"],
            "task_packet_fingerprint": oracle._digest(task_raw),
            "experiment_packet_ref": experiment_ref,
            "experiment_packet_sha256": oracle._digest((root / experiment_ref).read_bytes()),
            "experiment_packet_fingerprint": fingerprint_payload(packet),
            "dispatch_mode": "runtime",
            "implementation_owners": ["security-auditor"],
            "checked_inputs": [],
        }
    )
    selected = {
        "order": 1,
        "role_slug": "security-auditor",
        "readonly": False,
        "implementation_owner_override": True,
    }
    monkeypatch.setattr(oracle, "_selection", lambda *args: dict(selected))
    monkeypatch.setattr(
        oracle, "_request", lambda **kwargs: (copy.deepcopy(request), copy.deepcopy(packet))
    )
    commands: list[list[str]] = []

    def run(argv: list[str]) -> int:
        commands.append(list(argv))
        output = store / argv[argv.index("--output") + 1]
        snapshot = store / argv[argv.index("--snapshot-proof-output") + 1]
        observed = copy.deepcopy(result)
        if "--contribution-kind" in argv:
            observed.update(
                {
                    "contribution_kind": argv[argv.index("--contribution-kind") + 1],
                    "coauthor_required": True,
                    "coauthor_reason": argv[argv.index("--coauthor-reason") + 1],
                }
            )
        observed["execution_backend"]["image_digest"] = oracle.dispatcher.parse_image_reference(
            request["image"]
        ).digest
        bound = {
            **proof,
            "source_material": copy.deepcopy(request["source_material"]),
            "copied_new_files": copy.deepcopy(request["source_material"]["admitted_new_files"]),
            "snapshot_content_sha256": request["source_material"]["tracked_content_sha256"],
            "execution_backend": observed["execution_backend"],
            "result_fingerprint": fingerprint_payload(observed),
        }
        output.write_text(json.dumps(observed), encoding="utf-8")
        snapshot.write_text(json.dumps(bound), encoding="utf-8")
        observation_path = snapshot.with_name(snapshot.stem + ".observations.json")
        observation_path.write_text(
            json.dumps(
                {
                    "schema_version": "experiment_runner_private_observations.v1",
                    "authority": "local_observation_only",
                    "oracle_results": observed["oracle_results"],
                }
            ),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(oracle, "_execute_dispatch", run)
    return request, commands, selected


def _ensure(request: dict[str, Any]) -> str:
    return oracle.ensure_oracle_evidence(
        packet=request["task_packet_ref"],
        experiment_packet="artifacts/orchestration/experiments/test.json",
        role_context_order=1,
        mode="runtime",
        implementation_owners=("security-auditor",),
        backend="apple-container",
        image=request["image"],
        admitted_new_files=tuple(
            row["path"] for row in request["source_material"]["admitted_new_files"]
        ),
        checked_inputs=tuple(row["ref"] for row in request["checked_inputs"]),
        contribution_kind=request["contribution"]["kind"],
        coauthor_required=request["contribution"]["coauthor_required"],
        coauthor_reason=request["contribution"]["reason"],
    )


def test_identical_replay_executes_once_and_rewrites_nothing(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
) -> None:
    _, calls, _ = evidence_runtime
    ref = _ensure(evidence_runtime[0])
    before = {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in oracle.EVIDENCE_ROOT.rglob("*")
        if p.is_file()
    }
    assert _ensure(evidence_runtime[0]) == ref
    assert len(calls) == 1
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before}
    assert calls[0][0] == "run"
    assert "--snapshot-proof-output" in calls[0]


def test_tampered_linked_result_blocks_reuse(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
) -> None:
    _, calls, _ = evidence_runtime
    ref = _ensure(evidence_runtime[0])
    result = oracle.REPO_ROOT / Path(ref).parent / "result.json"
    result.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="bind every"):
        _ensure(evidence_runtime[0])
    assert len(calls) == 1


def test_stale_head_blocks_consumer(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
) -> None:
    request, calls, selected = evidence_runtime
    ref = _ensure(evidence_runtime[0])
    request["source_material"]["head_sha"] = "e" * 40
    with pytest.raises(ValueError, match="stale"):
        oracle.validate_oracle_evidence(
            ref,
            packet=request["task_packet_ref"],
            selected_dispatch=selected,
            mode="runtime",
            implementation_owners=("security-auditor",),
        )
    assert len(calls) == 1


def test_archive_roundtrip_corruption_and_repeat_preserve_source(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
) -> None:
    _, calls, _ = evidence_runtime
    ref = _ensure(evidence_runtime[0])
    archive, digest = oracle.export_evidence(ref)
    original = (oracle.REPO_ROOT / archive).read_bytes()
    with pytest.raises(ValueError, match="preserved"):
        oracle.export_evidence(ref)
    restore = oracle._ref(oracle.EVIDENCE_ROOT / "restores/restored")
    assert oracle.verify_archive(archive, digest, restore) == restore
    assert (oracle.REPO_ROOT / restore / "result.json").read_bytes() == (
        oracle.REPO_ROOT / Path(ref).parent / "result.json"
    ).read_bytes()
    (oracle.REPO_ROOT / archive).write_bytes(original + b"tampered")
    with pytest.raises(ValueError, match="hash"):
        oracle.verify_archive(
            archive, digest, oracle._ref(oracle.EVIDENCE_ROOT / "restores/another")
        )
    assert (oracle.REPO_ROOT / ref).exists()
    assert len(calls) == 1


def test_optout_still_requires_manual_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oracle, "_selection", lambda *args: {"order": 1})
    assert (
        oracle.main(
            ["dispatch", "--packet", "some.json", "--role-context-order", "1", "--no-auto-oracle"]
        )
        == 1
    )


@pytest.mark.parametrize(
    "key",
    ["oracle_commands_configured", "oracle_commands_executed", "attempts", "retries_consumed"],
)
def test_bool_count_aliases_are_rejected(key: str) -> None:
    packet, request, result, proof = _accepted_inputs()
    result["budget_observations"][key] = True if key != "retries_consumed" else False
    with pytest.raises(ValueError):
        oracle._accepted(result, packet, proof, request)


@pytest.mark.parametrize("target", ["receipt", "request", "new_files"])
def test_malformed_linked_shapes_fail_with_valueerror(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]], target: str
) -> None:
    request, _, selected = evidence_runtime
    ref = _ensure(request)
    path = oracle.REPO_ROOT / ref
    if target == "receipt":
        value = json.loads(path.read_text())
        value["files"] = 1
    else:
        path = path.parent / "request.json"
        value = json.loads(path.read_text())
        if target == "request":
            del value["experiment_packet_ref"]
        else:
            value["source_material"]["admitted_new_files"] = False
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError):
        oracle.validate_oracle_evidence(
            ref,
            packet=request["task_packet_ref"],
            selected_dispatch=selected,
            mode="runtime",
            implementation_owners=("security-auditor",),
        )


def test_interruption_preserves_owned_recovery_refs_and_never_retries(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, calls, _ = evidence_runtime

    def interrupted(arguments: list[str]) -> int:
        calls.append(arguments)
        raise KeyboardInterrupt

    monkeypatch.setattr(oracle, "_execute_dispatch", interrupted)
    with pytest.raises(KeyboardInterrupt):
        _ensure(request)
    directory = next(path for path in oracle.EVIDENCE_ROOT.iterdir() if path.is_dir())
    marker = json.loads((directory / "attempt-1.json").read_text())
    assert marker["snapshot_ref"].startswith("artifacts/orchestration/experiments/results/oracle-")
    assert json.loads((directory / "failure.json").read_text())["lifecycle_state"] == "interrupted"
    with pytest.raises(ValueError, match="Partial"):
        _ensure(request)
    assert len(calls) == 1


def test_fixed_dispatch_owner_is_called_without_an_outer_subprocess_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(oracle.dispatcher, "main", lambda arguments: calls.append(arguments) or 4)
    assert oracle._execute_dispatch(["run", "--packet", "approved.json"]) == 4
    assert calls == [["run", "--packet", "approved.json"]]


def test_capacity_allows_exact_replay_but_blocks_new_identity(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, calls, _ = evidence_runtime
    monkeypatch.setattr(oracle, "MAX_RETAINED_RUNS", 1)
    ref = _ensure(request)
    assert _ensure(request) == ref
    request["source_material"]["head_sha"] = "e" * 40
    with pytest.raises(ValueError, match="capacity"):
        _ensure(request)
    assert len(calls) == 1


def test_restore_history_has_no_live_currentness_claim(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
) -> None:
    request, _, _ = evidence_runtime
    ref = _ensure(request)
    archive, digest = oracle.export_evidence(ref)
    request["source_material"]["head_sha"] = "e" * 40
    restore = oracle._ref(oracle.EVIDENCE_ROOT / "restores/historical")
    oracle.verify_archive(archive, digest, restore)
    history = oracle.validate_restored_bundle(restore)
    assert history["historical_lineage"] == "validated"
    assert history["currentness_claim"] is False
    assert history["material_head_sha"] == "f" * 40


def test_well_hashed_unrelated_bundle_is_not_valid_lineage(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
) -> None:
    request, _, _ = evidence_runtime
    ref = _ensure(request)
    files = oracle._bundle_bytes((oracle.REPO_ROOT / ref).parent)
    result = json.loads(files["result.json"])
    result["experiment_id"] = "unrelated-experiment"
    files["result.json"] = json.dumps(result).encode()
    terminal = json.loads(files["attempt-1.terminal.json"])
    terminal["result_sha256"] = oracle._digest(files["result.json"])
    files["attempt-1.terminal.json"] = json.dumps(terminal).encode()
    receipt = json.loads(files["receipt.json"])
    receipt["files"]["result.json"] = oracle._digest(files["result.json"])
    receipt["files"]["attempt-1.terminal.json"] = oracle._digest(files["attempt-1.terminal.json"])
    files["receipt.json"] = json.dumps(receipt).encode()
    with pytest.raises(ValueError, match="approved oracle"):
        oracle._historical_bundle(files)


@pytest.mark.parametrize(
    "member,field,value",
    [
        ("attempt-1.terminal.json", "result_sha256", "sha256:" + "e" * 64),
        (
            "attempt-1.json",
            "result_ref",
            "artifacts/orchestration/experiments/results/oracle-" + "e" * 32 + ".json",
        ),
        (
            "attempt-1.json",
            "snapshot_ref",
            "artifacts/orchestration/experiments/results/unrelated.snapshot.json",
        ),
        (
            "attempt-1.terminal.json",
            "private_observations_ref",
            "artifacts/orchestration/experiments/results/unrelated.observations.json",
        ),
    ],
)
def test_rehashed_attempt_substitution_does_not_validate_as_result_lineage(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    member: str,
    field: str,
    value: str,
) -> None:
    request, _, _ = evidence_runtime
    ref = _ensure(request)
    files = oracle._bundle_bytes((oracle.REPO_ROOT / ref).parent)
    altered = json.loads(files[member])
    altered[field] = value
    files[member] = json.dumps(altered).encode()
    receipt = json.loads(files["receipt.json"])
    receipt["files"][member] = oracle._digest(files[member])
    files["receipt.json"] = json.dumps(receipt).encode()

    with pytest.raises(ValueError, match="[Aa]ttempt|final result"):
        oracle._historical_bundle(files)


def test_body_projection_validates_current_evidence(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
) -> None:
    request, _, selected = evidence_runtime
    ref = _ensure(request)
    body = oracle.render_pr_evidence(
        ref,
        packet=request["task_packet_ref"],
        selected_dispatch=selected,
        mode="runtime",
        implementation_owners=("security-auditor",),
    )
    assert "## Experiment Runner Evidence" in body
    assert "Material contribution declared: false" in body
    request["source_material"]["head_sha"] = "e" * 40
    with pytest.raises(ValueError, match="stale"):
        oracle.render_pr_evidence(
            ref,
            packet=request["task_packet_ref"],
            selected_dispatch=selected,
            mode="runtime",
            implementation_owners=("security-auditor",),
        )


def test_explicit_material_contribution_is_bound_and_forwarded(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
) -> None:
    request, calls, selected = evidence_runtime
    request["contribution"] = {
        "kind": "oracle_review",
        "coauthor_required": True,
        "reason": "Observed oracle evidence shapes the concrete review.",
    }
    ref = _ensure(request)
    assert "--coauthor-required" in calls[0]
    assert calls[0][calls[0].index("--contribution-kind") + 1] == "oracle_review"
    evidence = oracle.validate_oracle_evidence(
        ref,
        packet=request["task_packet_ref"],
        selected_dispatch=selected,
        mode="runtime",
        implementation_owners=("security-auditor",),
    )
    assert evidence["attachment"]["coauthor_required"] is True


@pytest.mark.parametrize(
    "failure,retry_expected", [("infra_flake", True), ("guard_failure", False), ("timeout", False)]
)
def test_only_admitted_infrastructure_failure_retries(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    retry_expected: bool,
) -> None:
    request, calls, _ = evidence_runtime
    original = oracle._execute_dispatch

    def run(arguments: list[str]) -> int:
        status = original(arguments)
        if len(calls) == 1:
            output = (
                oracle.dispatcher.RESULT_ARTIFACT_DIR / arguments[arguments.index("--output") + 1]
            )
            result = json.loads(output.read_text())
            result.update({"status": "rejected", "failure_class": failure})
            output.write_text(json.dumps(result), encoding="utf-8")
            return 4
        return status

    monkeypatch.setattr(oracle, "_execute_dispatch", run)
    if retry_expected:
        ref = _ensure(request)
        assert json.loads((oracle.REPO_ROOT / ref).read_text())["retries_consumed"] == 1
    else:
        with pytest.raises(ValueError, match="failed"):
            _ensure(request)
    assert len(calls) == (2 if retry_expected else 1)


@pytest.mark.parametrize(
    "field",
    [
        "base_sha",
        "head_sha",
        "index_sha256",
        "staged_diff_sha256",
        "unstaged_diff_sha256",
        "tracked_content_sha256",
        "image",
        "policy_version",
    ],
)
def test_each_binding_change_blocks_old_delivery_and_runs_new_identity(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    request, calls, selected = evidence_runtime
    ref = _ensure(request)
    original = (oracle.REPO_ROOT / ref).read_bytes()
    if field == "image":
        request[field] = "test/runner@sha256:" + "b" * 64
    elif field == "policy_version":
        monkeypatch.setattr(oracle, "POLICY_VERSION", "pr_oracle_attachment.next")
        request[field] = oracle.POLICY_VERSION
    else:
        request["source_material"][field] = "e" * (40 if field.endswith("_sha") else 64)
    with pytest.raises(ValueError):
        oracle.validate_oracle_evidence(
            ref,
            packet=request["task_packet_ref"],
            selected_dispatch=selected,
            mode="runtime",
            implementation_owners=("security-auditor",),
        )
    fresh = _ensure(request)
    assert fresh != ref
    assert len(calls) == 2
    assert (oracle.REPO_ROOT / ref).read_bytes() == original


@pytest.mark.parametrize(
    "choice,path",
    [
        (None, "README.md"),
        ("direct_fix", "tests/example.py"),
        ("alternatives", "tests/example.py"),
        ("alternatives", "scripts/orchestration/pr_oracle_attachment.py"),
    ],
)
def test_actual_request_uses_canonical_selector_and_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, choice: str | None, path: str
) -> None:
    root = tmp_path.resolve()
    packet, request, _, _ = _accepted_inputs()
    task = build_task_packet(
        goal="Evaluate bounded local material",
        task_class="Implementation",
        candidate_paths=[path],
        pr_phase="pre_open",
        creative_applicability=choice,
    )
    task_ref = f"artifacts/orchestration/task_packets/{task['task_packet_id']}.json"
    experiment_ref = "artifacts/orchestration/experiments/request-test.json"
    for ref, payload in [(task_ref, task), (experiment_ref, packet)]:
        target = root / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(oracle, "REPO_ROOT", root)
    monkeypatch.setattr(context, "REPO_ROOT", root)
    monkeypatch.setattr(rails, "REPO_ROOT", root)
    monkeypatch.setattr(
        oracle.dispatcher,
        "capture_source_material",
        lambda *args: copy.deepcopy(request["source_material"]),
    )
    bound, admitted = oracle._request(
        packet=task_ref,
        experiment_packet=experiment_ref,
        mode="analysis",
        owners=(),
        backend="apple-container",
        image=request["image"],
        admitted_new_files=(),
        checked_inputs=(),
    )
    assert bound["task_packet_id"] == task["task_packet_id"]
    assert bound["selector_policy_version"] == rails.POLICY_VERSION
    assert admitted["runner_mode"] == "oracle_only_governance_reviewer"
    packet["budgets"]["network_budget"] = 1
    (root / experiment_ref).write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(ValueError, match="network_budget"):
        oracle._request(
            packet=task_ref,
            experiment_packet=experiment_ref,
            mode="analysis",
            owners=(),
            backend="apple-container",
            image=request["image"],
            admitted_new_files=(),
            checked_inputs=(),
        )


@pytest.mark.parametrize("command", ["ensure", "validate", "body", "dispatch"])
@pytest.mark.parametrize("mode", ["runtime", "review", "docs-only"])
def test_cli_commands_keep_fixed_dispatch_and_current_manual_gate(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    mode: str,
) -> None:
    request, calls, _ = evidence_runtime
    ref = _ensure(request)
    bridge_calls: list[list[str]] = []

    def bridge(
        arguments: list[str], *, cwd: Path, timeout: int
    ) -> subprocess.CompletedProcess[str]:
        bridge_calls.append(arguments)
        return subprocess.CompletedProcess(
            arguments, 0, '{"schema_version":"exact-test-envelope"}\n', ""
        )

    monkeypatch.setattr(oracle.dispatcher, "_run", bridge)
    arguments = [
        command,
        "--packet",
        request["task_packet_ref"],
        "--role-context-order",
        "1",
        "--mode",
        mode,
        "--implementation-owner",
        "security-auditor",
    ]
    if command == "ensure":
        arguments += [
            "--experiment-packet",
            request["experiment_packet_ref"],
            "--image",
            request["image"],
        ]
    else:
        arguments += ["--oracle-evidence", ref, "--no-auto-oracle"]
    if command == "dispatch":
        arguments += [
            "--instruction-file",
            "tools/codex_skills/pulseplate-workflow/SKILL.md",
            "--pretty",
        ]
    assert oracle.main(arguments) == 0
    output = capsys.readouterr().out
    assert len(calls) == 1
    if command == "dispatch":
        assert json.loads(output)["schema_version"] == "exact-test-envelope"
        assert bridge_calls[0][1].endswith("scripts/orchestration/role_dispatch_bridge.py")
        assert bridge_calls[0][bridge_calls[0].index("--oracle-evidence") + 1] == ref
        assert bridge_calls[0][-3:] == [
            "--instruction-file",
            "tools/codex_skills/pulseplate-workflow/SKILL.md",
            "--pretty",
        ]
    elif command == "body":
        assert output.startswith("## Experiment Runner Evidence")
    elif command == "ensure":
        assert output.strip() == ref
    else:
        assert json.loads(output)["authority"] == "evidence_only"


@pytest.fixture
def admitted_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Use canonical packets and real Git material, replacing no admission owners."""

    root = tmp_path.resolve()
    task = build_task_packet(
        goal="Verify an admitted local orchestration change",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/fixture.py"],
        pr_phase="pre_open",
        creative_applicability="direct_fix",
    )
    source_root = Path(__file__).resolve().parents[1]
    roles = qoder_dispatch_bridge._parse_json_packet_roles(task)
    for relative in [
        "docs/orchestration/AGENT_CONTEXT_MAP.md",
        "docs/orchestration/AGENT_ROUTING_GRAPH.md",
        *[f".cursor/agents/{role}.md" for role in roles],
    ]:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, destination)
    for module in (
        oracle,
        oracle.dispatcher,
        context,
        rails,
        experiment_contract,
        qoder_dispatch_bridge,
    ):
        monkeypatch.setattr(module, "REPO_ROOT", root)
    monkeypatch.setattr(qoder_dispatch_bridge, "_routing_graph", None)
    monkeypatch.setattr(
        oracle,
        "EVIDENCE_ROOT",
        root / "artifacts/orchestration/experiments/results/oracle_attachments",
    )
    for arguments in (
        ["init", "--quiet"],
        ["config", "user.name", "Oracle admission fixture"],
        ["config", "user.email", "oracle-test@example.com"],
        ["remote", "add", "origin", "git@github.com:Katsiarynakavaleuskaya/PulsePlate.git"],
    ):
        subprocess.run(
            [oracle.dispatcher._git_binary(), *arguments],
            cwd=root,
            env=oracle.dispatcher._sanitized_git_env_without_parent_state(),
            check=True,
            capture_output=True,
            text=True,
        )
    fixture = root / "scripts/orchestration/fixture.py"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text("observed = 'baseline'\n", encoding="utf-8")
    oracle.dispatcher._git(["add", "scripts/orchestration/fixture.py"], cwd=root)
    oracle.dispatcher._git(["commit", "--quiet", "-m", "admitted fixture"], cwd=root)
    oracle.dispatcher._git(["update-ref", "refs/remotes/origin/main", "HEAD"], cwd=root)
    experiment, request, _, _ = _accepted_inputs()
    task_ref = f"artifacts/orchestration/task_packets/{task['task_packet_id']}.json"
    experiment_ref = "artifacts/orchestration/experiments/admission.json"
    for ref, payload in [(task_ref, task), (experiment_ref, experiment)]:
        target = root / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload), encoding="utf-8")
    return {
        "packet": task_ref,
        "experiment_packet": experiment_ref,
        "mode": "runtime",
        "owners": (),
        "backend": "apple-container",
        "image": request["image"],
        "admitted_new_files": (),
        "checked_inputs": (),
    }, experiment


def test_canonical_request_binds_real_staged_unstaged_new_and_checked_bytes(
    admitted_request: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    arguments, _ = admitted_request
    root = oracle.REPO_ROOT
    before, _ = oracle._request(**arguments)
    tracked = root / "scripts/orchestration/fixture.py"
    tracked.write_text("observed = 'staged'\n", encoding="utf-8")
    oracle.dispatcher._git(["add", "scripts/orchestration/fixture.py"], cwd=root)
    tracked.write_text("observed = 'baseline'\n", encoding="utf-8")
    staged, _ = oracle._request(**arguments)
    assert before["source_material"]["head_sha"] == staged["source_material"]["head_sha"]
    assert (
        before["source_material"]["tracked_content_sha256"]
        == staged["source_material"]["tracked_content_sha256"]
    )
    assert (
        before["source_material"]["staged_diff_sha256"]
        != staged["source_material"]["staged_diff_sha256"]
    )
    assert (
        before["source_material"]["unstaged_diff_sha256"]
        != staged["source_material"]["unstaged_diff_sha256"]
    )
    new_ref = "scripts/orchestration/new-input.txt"
    checked_ref = "artifacts/orchestration/criteria.json"
    (root / new_ref).write_bytes(b"exact new bytes\n")
    (root / checked_ref).write_bytes(b'{"criterion":"observed"}\n')
    arguments.update({"admitted_new_files": (new_ref,), "checked_inputs": (checked_ref,)})
    bound, _ = oracle._request(**arguments)
    assert bound["checked_inputs"] == [
        {"ref": checked_ref, "sha256": oracle._digest((root / checked_ref).read_bytes())}
    ]
    assert bound["source_material"]["admitted_new_files"][0]["path"] == new_ref
    assert oracle.dispatcher._git(["ls-files", "--", new_ref], cwd=root).stdout == ""
    (root / new_ref).write_bytes(b"changed new bytes\n")
    changed, _ = oracle._request(**arguments)
    assert fingerprint_payload(changed) != fingerprint_payload(bound)
    (root / checked_ref).write_bytes(b'{"criterion":"changed"}\n')
    checked_changed, _ = oracle._request(**arguments)
    assert checked_changed["checked_inputs"] != changed["checked_inputs"]


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("owners", ("security-auditor", "security-auditor"), "unique"),
        ("checked_inputs", ("same.json", "same.json"), "unique"),
        ("checked_inputs", tuple(f"input-{index}.json" for index in range(33)), "bounded"),
        ("admitted_new_files", ("outside/new.py",), "context"),
        ("image", "test/runner:mutable", "immutable|digest"),
    ],
)
def test_actual_request_rejects_unadmitted_input_before_retention(
    admitted_request: tuple[dict[str, Any], dict[str, Any]],
    field: str,
    value: object,
    message: str,
) -> None:
    arguments, _ = admitted_request
    arguments[field] = value
    with pytest.raises(ValueError, match=message):
        oracle._request(**arguments)
    assert not oracle.EVIDENCE_ROOT.exists()


@pytest.mark.parametrize("backend", ["auto", "docker", "native-linux"])
def test_actual_request_darwin_requires_explicit_apple(
    admitted_request: tuple[dict[str, Any], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    backend: str,
) -> None:
    arguments, _ = admitted_request
    arguments["backend"] = backend
    monkeypatch.setattr(oracle.platform, "system", lambda: "Darwin")
    with pytest.raises(ValueError, match="explicit apple-container"):
        oracle._request(**arguments)
    monkeypatch.setattr(oracle.platform, "system", lambda: "Linux")
    if backend != "docker":
        with pytest.raises(ValueError, match="strict container"):
            oracle._request(**arguments)
    else:
        request, _ = oracle._request(**arguments)
        assert request["backend"] == "docker"


@pytest.mark.parametrize("malformation", ["bool_budget", "non_oracle", "rejected_command"])
def test_actual_request_rejects_packet_command_mode_and_budget_changes(
    admitted_request: tuple[dict[str, Any], dict[str, Any]], malformation: str
) -> None:
    arguments, experiment = admitted_request
    if malformation == "bool_budget":
        experiment["budgets"]["test_budget"] = True
    elif malformation == "non_oracle":
        experiment["runner_mode"] = "candidate_patch"
        experiment["mutable_candidate_surface"] = ["core/rag/formatting.py"]
    else:
        experiment["immutable_oracles"][0]["command"] = "sh -c arbitrary-command"
    (oracle.REPO_ROOT / arguments["experiment_packet"]).write_text(
        json.dumps(experiment), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        oracle._request(**arguments)
    assert not oracle.EVIDENCE_ROOT.exists()


def test_actual_request_unavailable_raw_material_has_distinct_state(
    admitted_request: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    arguments, _ = admitted_request
    oracle.dispatcher._git(
        ["update-index", "--skip-worktree", "scripts/orchestration/fixture.py"],
        cwd=oracle.REPO_ROOT,
    )
    with pytest.raises(oracle.OracleEvidenceError) as failure:
        oracle._request(**arguments)
    assert failure.value.lifecycle_state == "material_unavailable"
    assert failure.value.runner_failure_class is None


@pytest.mark.parametrize("mode", ["runtime", "analysis", "review", "docs-only"])
def test_real_dispatch_selection_preserves_mode_and_exact_role_rights(
    admitted_request: tuple[dict[str, Any], dict[str, Any]], mode: str
) -> None:
    arguments, _ = admitted_request
    manifest = oracle._manifest(arguments["packet"], mode, ())
    for row in manifest["dispatch_sequence"]:
        expected = {
            key: row[key]
            for key in ("order", "role_slug", "readonly", "implementation_owner_override")
        }
        assert oracle._selection(arguments["packet"], row["order"], mode, ()) == expected
    assert all(row["readonly"] for row in manifest["dispatch_sequence"])
    for invalid_order in (False, 0, len(manifest["dispatch_sequence"]) + 1):
        with pytest.raises(ValueError, match="one-based"):
            oracle._selection(arguments["packet"], invalid_order, mode, ())
    with pytest.raises(ValueError, match="dispatch did not validate"):
        oracle._manifest(arguments["packet"], mode, ("backend-engineer",))
    if mode == "runtime":
        security = next(
            row for row in manifest["dispatch_sequence"] if row["role_slug"] == "security-auditor"
        )
        writer = oracle._selection(
            arguments["packet"], security["order"], mode, ("security-auditor",)
        )
        assert writer == {
            "order": security["order"],
            "role_slug": "security-auditor",
            "readonly": False,
            "implementation_owner_override": True,
        }


def test_archive_retains_exact_checked_and_new_dependencies(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
) -> None:
    request, calls, _ = evidence_runtime
    new_ref = "scripts/orchestration/new-input.txt"
    checked_ref = "artifacts/orchestration/checked.json"
    new = oracle.REPO_ROOT / new_ref
    new.parent.mkdir(parents=True)
    new.write_bytes(b"new material\n")
    checked = oracle.REPO_ROOT / checked_ref
    checked.write_bytes(b'{"criterion":"bounded"}\n')
    request["checked_inputs"] = [
        {"ref": checked_ref, "sha256": oracle._digest(checked.read_bytes())}
    ]
    request["source_material"]["admitted_new_files"] = [
        {
            "path": new_ref,
            "mode": "100644",
            "sha256": oracle._digest(new.read_bytes()).removeprefix("sha256:"),
        }
    ]
    ref = _ensure(request)
    archive, digest = oracle.export_evidence(ref)
    restore = oracle._ref(oracle.EVIDENCE_ROOT / "restores/dependencies")
    oracle.verify_archive(archive, digest, restore)
    restored = oracle.REPO_ROOT / restore
    assert (restored / "checked-00.input").read_bytes() == checked.read_bytes()
    assert (restored / "new-00.input").read_bytes() == new.read_bytes()
    assert calls[0][calls[0].index("--admitted-new-file") + 1] == new_ref
    assert len(calls) == 1


@pytest.mark.parametrize("malformation", ["traversal", "symlink", "compression", "member_hash"])
def test_unsafe_or_corrupted_download_never_restores_or_discards_source(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    malformation: str,
) -> None:
    request, calls, _ = evidence_runtime
    ref = _ensure(request)
    archive_ref, _ = oracle.export_evidence(ref)
    original = (oracle.REPO_ROOT / archive_ref).read_bytes()
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        members = {info.filename: archive.read(info) for info in archive.infolist()}
    if malformation == "traversal":
        members["../escaped.txt"] = b"unsafe member"
    elif malformation == "member_hash":
        members["result.json"] += b"\n"
    altered = io.BytesIO()
    with zipfile.ZipFile(altered, "w") as archive:
        for name, raw in members.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (
                0o120600 if malformation == "symlink" and name == "result.json" else 0o100600
            ) << 16
            info.compress_type = (
                zipfile.ZIP_DEFLATED if malformation == "compression" else zipfile.ZIP_STORED
            )
            archive.writestr(info, raw)
    download = oracle.REPO_ROOT / "artifacts/orchestration/unsafe-download.zip"
    download.write_bytes(altered.getvalue())
    restore = oracle._ref(oracle.EVIDENCE_ROOT / "restores/rejected")
    with pytest.raises(ValueError, match="[Aa]rchive member"):
        oracle.verify_archive(oracle._ref(download), oracle._digest(altered.getvalue()), restore)
    assert not (oracle.REPO_ROOT / restore).exists()
    assert (oracle.REPO_ROOT / archive_ref).read_bytes() == original
    assert (oracle.REPO_ROOT / ref).exists()
    assert len(calls) == 1


def test_restore_requires_original_task_dependency_and_owned_fresh_leaf(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, calls, _ = evidence_runtime
    ref = _ensure(request)
    archive, digest = oracle.export_evidence(ref)
    with pytest.raises(ValueError, match="fresh leaf"):
        oracle.verify_archive(archive, digest, "artifacts/unowned-restore")
    task = oracle.REPO_ROOT / request["task_packet_ref"]
    original = task.read_bytes()
    task.write_bytes(original + b"\n")
    restore = oracle._ref(oracle.EVIDENCE_ROOT / "restores/retained")
    with pytest.raises(ValueError, match="task dependency differs"):
        oracle.verify_archive(archive, digest, restore)
    assert not (oracle.REPO_ROOT / restore).exists()
    task.write_bytes(original)
    monkeypatch.setattr(oracle, "MAX_RETAINED_RUNS", 1)
    oracle.verify_archive(archive, digest, restore)
    with pytest.raises(ValueError, match="capacity"):
        oracle.verify_archive(
            archive, digest, oracle._ref(oracle.EVIDENCE_ROOT / "restores/second")
        )
    assert len(calls) == 1


def test_partial_transport_retains_storage_pending_original_without_runner_retry(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Simulate interrupted copying only; this is not an external upload claim."""

    request, calls, _ = evidence_runtime
    ref = _ensure(request)
    assert oracle.main(["export", "--oracle-evidence", ref]) == 0
    exported = json.loads(capsys.readouterr().out)
    assert exported["storage_state"] == "storage_pending"
    original = (oracle.REPO_ROOT / exported["archive"]).read_bytes()
    download = oracle.REPO_ROOT / "artifacts/orchestration/interrupted-download.zip"
    download.write_bytes(original[: len(original) // 2])
    restore = oracle._ref(oracle.EVIDENCE_ROOT / "restores/interrupted")
    assert (
        oracle.main(
            [
                "verify-archive",
                "--archive",
                oracle._ref(download),
                "--sha256",
                exported["sha256"],
                "--restore-dir",
                restore,
            ]
        )
        == 1
    )
    failure = json.loads(capsys.readouterr().err)
    assert failure["lifecycle_state"] == "invalid_evidence"
    assert not (oracle.REPO_ROOT / restore).exists()
    assert (oracle.REPO_ROOT / ref).exists()
    assert (oracle.REPO_ROOT / exported["archive"]).read_bytes() == original
    download.write_bytes(original)
    assert (
        oracle.main(
            [
                "verify-archive",
                "--archive",
                oracle._ref(download),
                "--sha256",
                exported["sha256"],
                "--restore-dir",
                restore,
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert oracle.main(["validate-restored", "--restore-dir", restore]) == 0
    assert json.loads(capsys.readouterr().out)["currentness_claim"] is False
    assert len(calls) == 1


def test_same_run_lock_blocks_cooperative_duplicate_without_overwrite(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
) -> None:
    request, calls, _ = evidence_runtime
    ref = _ensure(request)
    directory = (oracle.REPO_ROOT / ref).parent
    original = (directory / "receipt.json").read_bytes()
    with oracle.exclusive_patch_run_lock(directory, label="already running oracle"):
        with pytest.raises(ValueError, match="already in progress"):
            _ensure(request)
    assert _ensure(request) == ref
    assert (directory / "receipt.json").read_bytes() == original
    assert len(calls) == 1


@pytest.mark.parametrize("malformation", ["public_directory", "foreign_inventory"])
def test_retention_rejects_invalid_existing_store_without_cleanup(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    malformation: str,
) -> None:
    request, calls, _ = evidence_runtime
    oracle.EVIDENCE_ROOT.mkdir(parents=True, mode=0o700)
    if malformation == "public_directory":
        oracle.EVIDENCE_ROOT.chmod(0o755)
        marker = oracle.EVIDENCE_ROOT / "keep.txt"
    else:
        marker = oracle.EVIDENCE_ROOT / "foreign-entry"
    marker.write_text("preserve foreign bytes", encoding="utf-8")
    with pytest.raises(ValueError, match="private mode|inventory"):
        _ensure(request)
    assert marker.read_text() == "preserve foreign bytes"
    assert calls == []


@pytest.mark.parametrize("when", ["before_admission", "during_execution"])
def test_material_drift_between_acquisitions_never_publishes_accepted_receipt(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    when: str,
) -> None:
    request, calls, _ = evidence_runtime
    original_request = oracle._request
    acquisition_count = 0

    def acquire(**kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        nonlocal acquisition_count
        acquisition_count += 1
        if when == "before_admission" and acquisition_count == 2:
            request["source_material"]["head_sha"] = "e" * 40
        return original_request(**kwargs)

    original_execute = oracle._execute_dispatch

    def execute(arguments: list[str]) -> int:
        status = original_execute(arguments)
        if when == "during_execution":
            request["source_material"]["head_sha"] = "e" * 40
        return status

    monkeypatch.setattr(oracle, "_request", acquire)
    monkeypatch.setattr(oracle, "_execute_dispatch", execute)
    with pytest.raises(
        oracle.OracleEvidenceError, match="Material changed|Source material changed"
    ) as error:
        _ensure(request)
    assert error.value.lifecycle_state == "stale"
    assert len(calls) == (0 if when == "before_admission" else 1)
    assert list(oracle.EVIDENCE_ROOT.rglob("receipt.json")) == []
    if when == "during_execution":
        assert len(list(oracle.EVIDENCE_ROOT.rglob("attempt-1.terminal.json"))) == 1


@pytest.mark.parametrize("missing", ["result", "private_observation"])
def test_missing_execution_output_blocks_receipt_without_retry(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    request, calls, _ = evidence_runtime
    original = oracle._execute_dispatch

    def execute(arguments: list[str]) -> int:
        status = original(arguments)
        option = "--output" if missing == "result" else "--snapshot-proof-output"
        path = oracle.dispatcher.RESULT_ARTIFACT_DIR / arguments[arguments.index(option) + 1]
        if missing == "private_observation":
            path = path.with_name(path.stem + ".observations.json")
        path.unlink()
        return status

    monkeypatch.setattr(oracle, "_execute_dispatch", execute)
    with pytest.raises(ValueError, match="retain a result|observation provenance is missing"):
        _ensure(request)
    assert len(calls) == 1
    assert list(oracle.EVIDENCE_ROOT.rglob("receipt.json")) == []


def test_infrastructure_retry_exhaustion_preserves_both_attempts_and_stops(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, calls, _ = evidence_runtime
    original = oracle._execute_dispatch

    def fail(arguments: list[str]) -> int:
        original(arguments)
        output = oracle.dispatcher.RESULT_ARTIFACT_DIR / arguments[arguments.index("--output") + 1]
        result = json.loads(output.read_text())
        result.update({"status": "rejected", "failure_class": "infra_flake"})
        output.write_text(json.dumps(result), encoding="utf-8")
        return 4

    monkeypatch.setattr(oracle, "_execute_dispatch", fail)
    with pytest.raises(oracle.OracleEvidenceError) as failure:
        _ensure(request)
    assert failure.value.runner_failure_class == "infra_flake"
    assert len(calls) == 2
    assert len(list(oracle.EVIDENCE_ROOT.rglob("attempt-*.terminal.json"))) == 2
    with pytest.raises(ValueError, match="Partial"):
        _ensure(request)
    assert len(calls) == 2


@pytest.mark.parametrize(
    "shape", ["noncanonical_ref", "wrong_slot", "wrong_rights", "missing_order"]
)
def test_consumer_rejects_receipt_aliases_and_selected_occurrence_substitution(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]], shape: str
) -> None:
    request, calls, selected = evidence_runtime
    ref = _ensure(request)
    original = (oracle.REPO_ROOT / ref).read_bytes()
    if shape == "noncanonical_ref":
        ref = ref.replace("receipt.json", "attachment.json")
    elif shape == "wrong_slot":
        source = (oracle.REPO_ROOT / ref).parent
        moved = source.with_name("e" * 64)
        source.rename(moved)
        ref = oracle._ref(moved / "receipt.json")
    elif shape == "wrong_rights":
        selected = {**selected, "readonly": True, "implementation_owner_override": False}
    else:
        selected = {key: value for key, value in selected.items() if key != "order"}
    with pytest.raises(ValueError):
        oracle.validate_oracle_evidence(
            ref,
            packet=request["task_packet_ref"],
            selected_dispatch=selected,
            mode="runtime",
            implementation_owners=("security-auditor",),
        )
    assert len(calls) == 1
    assert any(path.read_bytes() == original for path in oracle.EVIDENCE_ROOT.rglob("receipt.json"))


@pytest.mark.parametrize("mutation", ["bool_budget", "attribution", "proof"])
def test_result_cannot_substitute_approved_budget_attribution_or_snapshot(mutation: str) -> None:
    packet, request, result, proof = _accepted_inputs()
    if mutation == "bool_budget":
        result["budget_observations"]["configured_budgets"] = {
            **packet["budgets"],
            "test_budget": True,
        }
    elif mutation == "attribution":
        result.update(
            {
                "contribution_kind": "oracle_review",
                "coauthor_required": True,
                "coauthor_reason": "Unapproved material use.",
            }
        )
    else:
        proof["snapshot_content_sha256"] = "e" * 64
    with pytest.raises(ValueError):
        oracle._accepted(result, packet, proof, request)


@pytest.mark.parametrize("which", ["checked", "new"])
def test_malformed_dependency_inventory_is_not_consumable(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]], which: str
) -> None:
    request, calls, _ = evidence_runtime
    if which == "checked":
        request["checked_inputs"] = [{"ref": "some.json"}]
    else:
        request["source_material"]["admitted_new_files"] = [
            {"path": "new.txt", "mode": "120000", "sha256": "e" * 64}
        ]
    with pytest.raises(ValueError, match="binding is malformed"):
        _ensure(request)
    assert calls == []


def test_input_dependency_drift_after_request_capture_is_not_retained(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
) -> None:
    request, calls, _ = evidence_runtime
    source = oracle.REPO_ROOT / request["experiment_packet_ref"]
    source.write_bytes(source.read_bytes() + b"\n")
    with pytest.raises(oracle.OracleEvidenceError, match="changed before retention") as error:
        _ensure(request)
    assert error.value.lifecycle_state == "stale"
    assert calls == []


@pytest.mark.parametrize("bound", ["MAX_BYTES", "MAX_RUN_BYTES"])
def test_oversized_retention_blocks_execution_and_preserves_source(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    bound: str,
) -> None:
    request, calls, _ = evidence_runtime
    source = oracle.REPO_ROOT / request["experiment_packet_ref"]
    original = source.read_bytes()
    monkeypatch.setattr(oracle, bound, 1)
    with pytest.raises(ValueError, match="bound|budget"):
        _ensure(request)
    assert calls == []
    assert source.read_bytes() == original


def test_dispatch_summary_bound_preserves_controlled_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def verbose(arguments: list[str]) -> int:
        print("unexpected oversized dispatcher summary")
        return 0

    monkeypatch.setattr(oracle.dispatcher, "main", verbose)
    monkeypatch.setattr(oracle, "MAX_BYTES", 8)
    with pytest.raises(ValueError, match="summary exceeds"):
        oracle._execute_dispatch(["run"])


def test_cli_rejects_missing_admission_and_bridge_failure_without_payload_leak(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    request, calls, _ = evidence_runtime
    assert oracle.main(["ensure"]) == 1
    assert json.loads(capsys.readouterr().err)["lifecycle_state"] == "invalid_evidence"
    base_args = ["--packet", request["task_packet_ref"], "--role-context-order", "1"]
    assert oracle.main(["ensure", *base_args]) == 1
    assert json.loads(capsys.readouterr().err)["lifecycle_state"] == "invalid_evidence"
    assert calls == []
    ref = _ensure(request)

    def failed_bridge(arguments: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            arguments, 1, "private rejected payload", "private stderr"
        )

    monkeypatch.setattr(oracle.dispatcher, "_run", failed_bridge)
    assert oracle.main(["dispatch", *base_args, "--no-auto-oracle", "--oracle-evidence", ref]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "private" not in captured.err
    assert json.loads(captured.err)["error_class"] == "OracleEvidenceError"
    assert len(calls) == 1


@pytest.mark.parametrize(
    "mutation,message",
    [
        ("attempt_count", "Attempt inventory"),
        ("missing_member", "bundle inventory"),
        ("dependency", "input dependency differs"),
        ("experiment", "experiment semantics differ"),
        ("retry_count", "retry observation"),
        ("attempt_ref", "attempt reference"),
        ("result_hash", "original byte binding"),
        ("returncode", "retry lineage"),
        ("private_hash", "private observations lack"),
        ("attachment", "attachment does not bind"),
        ("source_shape", "Malformed frozen"),
    ],
)
def test_internal_lineage_rejects_rehashed_inconsistent_records(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    mutation: str,
    message: str,
) -> None:
    request, _, _ = evidence_runtime
    ref = _ensure(request)
    files = oracle._bundle_bytes((oracle.REPO_ROOT / ref).parent)
    receipt = json.loads(files["receipt.json"])
    retained_request = json.loads(files["request.json"])
    terminal = json.loads(files["attempt-1.terminal.json"])
    if mutation == "attempt_count":
        receipt["attempts"] = True
    elif mutation == "missing_member":
        del files["snapshot.json"]
    elif mutation == "dependency":
        files["task_packet.json"] += b"\n"
    elif mutation == "experiment":
        retained_request["experiment_packet_fingerprint"] = "sha256:" + "e" * 64
    elif mutation == "retry_count":
        receipt["retries_consumed"] = False
    elif mutation == "attempt_ref":
        terminal["result_ref"] = "artifacts/orchestration/foreign.json"
    elif mutation == "result_hash":
        terminal["result_sha256"] = "not-a-digest"
    elif mutation == "returncode":
        terminal["returncode"] = False
    elif mutation == "private_hash":
        terminal.pop("private_observations_sha256")
    elif mutation == "attachment":
        unrelated = copy.deepcopy(request)
        unrelated["source_material"]["head_sha"] = "e" * 40
        files["attachment.json"] = json.dumps(
            oracle._attachment(
                unrelated, json.loads(files["result.json"]), str(Path(ref).parent / "result.json")
            )
        ).encode()
    else:
        retained_request["source_material"] = []
    files["attempt-1.terminal.json"] = json.dumps(terminal).encode()
    files["request.json"] = json.dumps(retained_request).encode()
    receipt["request_fingerprint"] = fingerprint_payload(retained_request)
    receipt["files"] = {
        name: oracle._digest(raw) for name, raw in files.items() if name != "receipt.json"
    }
    files["receipt.json"] = json.dumps(receipt).encode()

    with pytest.raises(ValueError, match=message):
        oracle._historical_bundle(files)


def test_export_size_limit_and_unowned_refs_never_remove_original(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, calls, _ = evidence_runtime
    ref = _ensure(request)
    with pytest.raises(ValueError, match="canonical evidence"):
        oracle.export_evidence(ref.replace("receipt.json", "result.json"))
    with pytest.raises(ValueError, match="owned restore root"):
        oracle.validate_restored_bundle(str(Path(ref).parent))
    monkeypatch.setattr(oracle, "MAX_ARCHIVE_BYTES", 1)
    with pytest.raises(ValueError, match="Archive exceeds"):
        oracle.export_evidence(ref)
    assert (oracle.REPO_ROOT / ref).exists()
    assert not (oracle.REPO_ROOT / ref).with_name("oracle_evidence.zip").exists()
    assert len(calls) == 1


@pytest.mark.parametrize("error", [KeyError, TypeError, AttributeError, IndexError])
def test_restored_validation_normalizes_malformed_linkage_without_mutation(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    error: type[Exception],
) -> None:
    request, calls, _ = evidence_runtime
    ref = _ensure(request)
    archive, digest = oracle.export_evidence(ref)
    restore = oracle._ref(oracle.EVIDENCE_ROOT / "restores/normalized-error")
    oracle.verify_archive(archive, digest, restore)
    root = oracle.REPO_ROOT / restore
    before = {path.name: path.read_bytes() for path in root.iterdir()}

    def malformed(_files: dict[str, bytes]) -> Any:
        raise error("untrusted linkage detail")

    monkeypatch.setattr(oracle, "_historical_bundle", malformed)
    with pytest.raises(oracle.OracleEvidenceError, match=r"^Malformed restored bundle\.$"):
        oracle.validate_restored_bundle(restore)
    assert {path.name: path.read_bytes() for path in root.iterdir()} == before
    assert len(calls) == 1


def test_request_semantics_and_raw_digest_come_from_one_acquisition(
    admitted_request: tuple[dict[str, Any], dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    arguments, _ = admitted_request
    ref = arguments["experiment_packet"]
    source = oracle.REPO_ROOT / ref
    original_bytes = source.read_bytes()
    replacement = json.loads(original_bytes)
    replacement["immutable_oracles"][0]["command"] = "git status --short"
    real_raw = oracle._raw
    reads = 0

    def acquire_then_change(reference: str) -> bytes:
        nonlocal reads
        data = real_raw(reference)
        if reference == ref:
            reads += 1
            if reads == 1:
                source.write_text(json.dumps(replacement), encoding="utf-8")
        return data

    monkeypatch.setattr(oracle, "_raw", acquire_then_change)
    request, experiment = oracle._request(**arguments)
    assert request["experiment_packet_sha256"] == oracle._digest(original_bytes)
    assert request["experiment_packet_fingerprint"] == fingerprint_payload(experiment)
    assert experiment["immutable_oracles"][0]["command"] == "git --version"
    assert reads == 1
    assert source.read_bytes() != original_bytes


def test_dispatch_executes_retained_experiment_bytes_when_original_reference_changes(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, calls, _ = evidence_runtime
    source = oracle.REPO_ROOT / request["experiment_packet_ref"]
    frozen = source.read_bytes()
    original_execute = oracle._execute_dispatch
    observed: list[bytes] = []

    def execute(arguments: list[str]) -> int:
        replacement = json.loads(source.read_bytes())
        replacement["immutable_oracles"][0]["command"] = "git status --short"
        source.write_text(json.dumps(replacement), encoding="utf-8")
        actual_ref = arguments[arguments.index("--packet") + 1]
        assert actual_ref != request["experiment_packet_ref"]
        actual_path = oracle.REPO_ROOT / actual_ref
        assert actual_path.parent.parent == oracle.EVIDENCE_ROOT
        observed.append(actual_path.read_bytes())
        assert observed[-1] == frozen
        return original_execute(arguments)

    monkeypatch.setattr(oracle, "_execute_dispatch", execute)
    ref = _ensure(request)
    assert observed == [frozen]
    assert len(calls) == 1
    assert (oracle.REPO_ROOT / ref).with_name("experiment_packet.json").read_bytes() == frozen


@pytest.mark.parametrize(
    "drift", ["material", "command", "checked_input", "policy", "image", "new_file"]
)
def test_infrastructure_retry_stops_stale_inputs_before_second_execution(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    request, calls, _ = evidence_runtime
    original_execute = oracle._execute_dispatch

    def execute(arguments: list[str]) -> int:
        status = original_execute(arguments)
        if len(calls) == 1:
            output = (
                oracle.dispatcher.RESULT_ARTIFACT_DIR / arguments[arguments.index("--output") + 1]
            )
            result = json.loads(output.read_text())
            result.update({"status": "rejected", "failure_class": "infra_flake"})
            output.write_text(json.dumps(result), encoding="utf-8")
            if drift == "material":
                request["source_material"]["head_sha"] = "e" * 40
            elif drift == "command":
                request["experiment_packet_fingerprint"] = "sha256:" + "e" * 64
            elif drift == "checked_input":
                request["checked_inputs"] = [{"ref": "checked.txt", "sha256": "sha256:" + "e" * 64}]
            elif drift == "policy":
                request["policy_version"] = "changed-policy"
            elif drift == "image":
                request["image"] = "test/runner@sha256:" + "e" * 64
            else:
                request["source_material"]["admitted_new_files"] = [
                    {"path": "new.py", "mode": "100644", "sha256": "e" * 64}
                ]
            return 4
        return status

    monkeypatch.setattr(oracle, "_execute_dispatch", execute)
    with pytest.raises(oracle.OracleEvidenceError) as error:
        _ensure(request)
    assert len(calls) == 1
    assert error.value.lifecycle_state == "stale"
    assert len(list(oracle.EVIDENCE_ROOT.rglob("attempt-1.terminal.json"))) == 1
    assert list(oracle.EVIDENCE_ROOT.rglob("attempt-2.json")) == []
    assert list(oracle.EVIDENCE_ROOT.rglob("receipt.json")) == []


@pytest.mark.parametrize("phase", ["first_attempt", "retry_attempt"])
def test_attempt_gate_rechecks_inputs_after_retention_and_between_retry_observations(
    evidence_runtime: tuple[dict[str, Any], list[list[str]], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    request, calls, _ = evidence_runtime
    original_publish = oracle._publish_bytes
    original_request = oracle._request
    original_execute = oracle._execute_dispatch
    changed = False

    def publish(path: Path, raw: bytes, **kwargs: Any) -> None:
        original_publish(path, raw, **kwargs)
        if phase == "first_attempt" and path.name == "experiment_packet.json":
            request["source_material"]["head_sha"] = "e" * 40

    def acquire(**kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        nonlocal changed
        observed = original_request(**kwargs)
        if phase == "retry_attempt" and calls and not changed:
            request["source_material"]["head_sha"] = "e" * 40
            changed = True
        return observed

    def execute(arguments: list[str]) -> int:
        status = original_execute(arguments)
        if len(calls) == 1:
            output = (
                oracle.dispatcher.RESULT_ARTIFACT_DIR / arguments[arguments.index("--output") + 1]
            )
            result = json.loads(output.read_text())
            result.update({"status": "rejected", "failure_class": "infra_flake"})
            output.write_text(json.dumps(result), encoding="utf-8")
            return 4
        return status

    monkeypatch.setattr(oracle, "_publish_bytes", publish)
    monkeypatch.setattr(oracle, "_request", acquire)
    monkeypatch.setattr(oracle, "_execute_dispatch", execute)
    with pytest.raises(oracle.OracleEvidenceError, match="before execution attempt") as error:
        _ensure(request)
    assert error.value.lifecycle_state == "stale"
    assert len(calls) == (0 if phase == "first_attempt" else 1)
    assert not list(oracle.EVIDENCE_ROOT.rglob("attempt-2.json"))
    assert not list(oracle.EVIDENCE_ROOT.rglob("receipt.json"))
