from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_patch_builder
from scripts.orchestration import creative_code_patch_generation as generation_cli
from scripts.orchestration import creative_code_patch_workspace
from scripts.orchestration import creative_spec_learning_rollup_contract
from scripts.orchestration import creative_spec_patch_admission as admission_cli
from scripts.orchestration.creative_code_patch_contract import (
    build_creative_code_patch_result,
    validate_creative_code_patch_result,
)
from scripts.orchestration.creative_code_patch_generation import (
    CreativeCodePatchGenerationError,
    validate_generation_gate,
    validate_generation_receipt,
)
from tests.test_creative_spec_patch_admission import (
    _git,
    _init_patch_repo,
    _output_dir,
    _patch_modules_to_repo as _patch_admission_modules_to_repo,
    _write_inputs,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_patch_generation_gate.v1.schema.json"
)
RECEIPT_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_patch_generation_receipt.v1.schema.json"
)


def _patch_modules_to_repo(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    _patch_admission_modules_to_repo(monkeypatch, repo)
    creative_root = repo / "artifacts" / "orchestration" / "creative_code"
    monkeypatch.setattr(generation_cli, "REPO_ROOT", repo)
    monkeypatch.setattr(generation_cli, "CREATIVE_CODE_ROOT", creative_root)
    monkeypatch.setattr(generation_cli, "PATCH_GENERATION_ROOT", creative_root / "patch_generation")


def _prepare_admission(
    *,
    repo: Path,
    base_sha: str,
    run_id: str,
    output_name: str = "generation-admission",
) -> Path:
    _bundle, bundle_path, receipt_path, human_path = _write_inputs(repo)
    output_dir = _output_dir(repo, output_name)
    assert (
        admission_cli.main(
            [
                "build-and-prepare",
                "--finalize-receipt",
                str(receipt_path),
                "--bundle",
                str(bundle_path),
                "--human-admission",
                str(human_path),
                "--base-sha",
                base_sha,
                "--output-dir",
                str(output_dir),
                "--run-id",
                run_id,
            ]
        )
        == 0
    )
    return output_dir / admission_cli.ADMISSION_FILENAME


def _generation_dir(repo: Path, name: str) -> Path:
    return repo / "artifacts" / "orchestration" / "creative_code" / "patch_generation" / name


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mock_successful_builder_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_codex_exec(
        *,
        checkout: Path,
        prompt: str,
        timeout_seconds: int,
    ) -> dict[str, int]:
        assert "Do not run network commands" in prompt
        assert timeout_seconds == 60
        (checkout / "core" / "rag" / "orchestration.py").write_text(
            "def value() -> int:\n    return 2\n",
            encoding="utf-8",
        )
        return {"returncode": 0, "stdout_lines": 0, "stderr_lines": 0}

    def fake_evaluate_candidate(packet: dict[str, Any], patch_file: Path) -> dict[str, Any]:
        assert patch_file.name == creative_code_patch_builder.CANDIDATE_PATCH_FILE
        assert packet["budgets"]["network_budget"] == 0
        return {
            "experiment_id": packet["experiment_id"],
            "status": "accepted",
            "failure_class": None,
            "mutated_paths": ["core/rag/orchestration.py"],
            "oracle_results": [{"status": "passed"}],
            "budget_observations": {
                "oracle_commands_configured": len(packet["immutable_oracles"]),
                "attempts": 1,
                "retries_consumed": 0,
            },
            "shared_tree_untouched": True,
        }

    monkeypatch.setattr(creative_code_patch_builder, "run_codex_exec", fake_run_codex_exec)
    monkeypatch.setattr(creative_code_patch_builder, "evaluate_candidate", fake_evaluate_candidate)


def _write_gate(
    *,
    repo: Path,
    admission_path: Path,
    run_id: str,
    output_name: str = "generation-gate",
) -> Path:
    output_dir = _generation_dir(repo, output_name)
    assert (
        generation_cli.main(
            [
                "validate-run-plan",
                "--admission",
                str(admission_path),
                "--run-id",
                run_id,
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )
    return output_dir / generation_cli.GATE_FILENAME


def _prepare_generated_dispatch_handoff(
    *,
    monkeypatch: pytest.MonkeyPatch,
    repo: Path,
    base_sha: str,
    run_id: str,
) -> tuple[Path, Path, dict[str, Any]]:
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)

    def raise_capability_signal(_packet: dict[str, Any], _patch_file: Path) -> dict[str, Any]:
        raise creative_code_patch_builder.RunnerCapabilitySignal

    monkeypatch.setattr(
        creative_code_patch_builder,
        "evaluate_candidate",
        raise_capability_signal,
    )
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 1
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    metadata = json.loads(
        (run_dir / creative_code_patch_builder.PATCH_METADATA_FILE).read_text(encoding="utf-8")
    )
    packet = json.loads(
        (run_dir / creative_code_patch_builder.EXPERIMENT_PACKET_FILE).read_text(encoding="utf-8")
    )
    assert packet["candidate_patch_fingerprint"] == metadata["patch_fingerprint"]
    result_path = (
        repo / "artifacts" / "orchestration" / "experiments" / "results" / f"{run_id}.json"
    )
    return gate_path, result_path, packet


def _trusted_dispatch_result(
    packet: dict[str, Any],
    *,
    status: str = "accepted",
    failure_class: str | None = None,
    mutated_paths: list[str] | None = None,
) -> dict[str, Any]:
    configured_commands = [oracle["command"] for oracle in packet["immutable_oracles"]]
    accepted = status == "accepted"
    if mutated_paths is None:
        mutated_paths = list(packet["mutable_candidate_surface"])
    oracle_results = [
        {
            "command": command,
            "returncode": 0,
            "timed_out": False,
            "truncated": False,
            "stdout": "",
            "stderr": "",
            "cwd": "/workspace",
        }
        for command in configured_commands
    ]
    if not accepted and failure_class in generation_cli.FAILING_ORACLE_REQUIRED_FAILURE_CLASSES:
        oracle_results[-1]["returncode"] = 1
    return {
        "schema_version": "1.0",
        "experiment_id": packet["experiment_id"],
        "runner_mode": "candidate_patch",
        "candidate_patch": ".experiment-runner-input/candidate.patch",
        "candidate_patch_fingerprint": packet["candidate_patch_fingerprint"],
        "status": status,
        "failure_class": failure_class,
        "mutated_paths": mutated_paths,
        "oracle_results": oracle_results,
        "budget_observations": {
            "configured_budgets": dict(packet["budgets"]),
            "oracle_commands_configured": len(configured_commands),
            "oracle_commands_executed": len(oracle_results),
            "candidate_changed_files": len(packet["mutable_candidate_surface"]),
            "attempts": 1,
            "retries_consumed": 0,
        },
        "shared_tree_untouched": True,
        "promotion_ready": False,
        "contribution_kind": "none",
        "coauthor_required": False,
        "coauthor_reason": "",
        "execution_backend": {
            "name": "apple-container",
            "guest_platform": "linux_arm64",
            "runtime_version": "1.1.0",
            "image_digest": "sha256:" + ("a" * 64),
            "network_isolation": "apple_internal_no_dns_plus_linux_unshare",
            "preflight_status": "passed",
        },
    }


def _reset_receipt_identity(receipt: dict[str, Any]) -> None:
    generation_cli._set_identity(
        receipt,
        id_key="receipt_id",
        asset_type=generation_cli.RECEIPT_ARTIFACT_TYPE,
    )


def _semantic_binding_inputs(
    *, metrics: list[str] | None = None
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    request = {
        "budgets": {
            "evaluation_timeout_seconds": 120,
            "max_changed_files": 1,
        },
        "oracle_commands": ["pytest -q tests/test_example.py"],
        "metrics": ["quality"] if metrics is None else metrics,
    }
    packet = {
        "experiment_id": "experiment:test",
        "candidate_patch_fingerprint": "sha256:" + ("b" * 64),
        "mutable_candidate_surface": ["core/rag/example.py"],
        "immutable_oracles": [
            {
                "command": "pytest -q tests/test_example.py",
                "expected_signal": "must pass",
            }
        ],
        "budgets": generation_cli._expected_experiment_budgets(request),
        "metrics": {
            "primary": "quality",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
    }
    result = {
        "changed_paths": ["core/rag/example.py"],
        "patch_summary": {
            "patch_fingerprint": "sha256:" + ("b" * 64),
            "patch_bytes": 1,
            "diff_lines": 1,
        },
        "runner_summary": {
            "experiment_id": "experiment:test",
            "oracle_commands_configured": 1,
            "oracle_commands_executed": 1,
        },
    }
    return request, packet, result


def test_generation_budget_envelope_uses_builder_overrides() -> None:
    request, _packet, _result = _semantic_binding_inputs()

    expected = generation_cli._expected_experiment_budgets(request)
    stop_condition = expected.pop("stop_condition")

    assert expected == creative_code_patch_builder.build_pr2_experiment_budget_overrides(request)
    assert isinstance(stop_condition, str)
    assert stop_condition


@pytest.mark.parametrize("metrics", [[], [" "]])
def test_semantic_binding_rejects_invalid_metrics_with_domain_error(metrics: list[str]) -> None:
    request, packet, result = _semantic_binding_inputs(metrics=metrics)

    with pytest.raises(
        CreativeCodePatchGenerationError,
        match="generation receipt request metrics are invalid",
    ):
        generation_cli._validate_experiment_packet_matches_result(
            experiment_packet_payload=packet,
            request=request,
            source_bundle={},
            result=result,
        )


@pytest.mark.parametrize(
    ("mismatch", "message"),
    [
        ("experiment_id", "experiment_id is stale"),
        ("mutable_surface", "mutable surface is stale"),
        ("oracle_command", "immutable oracles are stale"),
        ("oracle_count", "oracle count is stale"),
        ("oracle_executions", "oracle executions exceed"),
        ("patch_fingerprint", "candidate patch fingerprint is stale"),
        ("budgets", "budgets are stale"),
        ("metrics", "metrics are stale"),
    ],
)
def test_semantic_binding_rejects_cross_artifact_mismatches(
    mismatch: str,
    message: str,
) -> None:
    request, packet, result = _semantic_binding_inputs()
    if mismatch == "experiment_id":
        packet["experiment_id"] = "experiment:stale"
    elif mismatch == "mutable_surface":
        packet["mutable_candidate_surface"] = ["core/rag/stale.py"]
    elif mismatch == "oracle_command":
        packet["immutable_oracles"][0]["command"] = "pytest -q tests/test_stale.py"
    elif mismatch == "oracle_count":
        result["runner_summary"]["oracle_commands_configured"] = 2
    elif mismatch == "oracle_executions":
        result["runner_summary"]["oracle_commands_executed"] = 2
    elif mismatch == "patch_fingerprint":
        result["patch_summary"]["patch_fingerprint"] = "sha256:" + ("c" * 64)
    elif mismatch == "budgets":
        packet["budgets"]["network_budget"] = 1
    else:
        packet["metrics"]["primary"] = "stale"

    with pytest.raises(CreativeCodePatchGenerationError, match=message):
        generation_cli._validate_experiment_packet_matches_result(
            experiment_packet_payload=packet,
            request=request,
            source_bundle={},
            result=result,
        )


def test_semantic_binding_ignores_telemetry_derived_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, packet, result = _semantic_binding_inputs()
    expected_packet = {
        **packet,
        "negative_controls": ["stable control"],
        "recommended_agents": ["agent-coordinator", "backend-engineer"],
        "routing_context": {
            "primary": "backend-engineer",
            "secondary": None,
        },
    }
    actual_packet = deepcopy(expected_packet)
    actual_packet["recommended_agents"] = ["agent-coordinator", "security-auditor"]
    actual_packet["routing_context"] = {
        "primary": "security-auditor",
        "secondary": "backend-engineer",
    }
    monkeypatch.setattr(
        creative_code_patch_builder,
        "build_pr2_experiment_packet",
        lambda **_kwargs: expected_packet,
    )

    generation_cli._validate_experiment_packet_matches_result(
        experiment_packet_payload=actual_packet,
        request=request,
        source_bundle={},
        result=result,
    )

    actual_packet["negative_controls"] = ["tampered control"]
    with pytest.raises(
        CreativeCodePatchGenerationError,
        match="experiment packet semantics are stale",
    ):
        generation_cli._validate_experiment_packet_matches_result(
            experiment_packet_payload=actual_packet,
            request=request,
            source_bundle={},
            result=result,
        )


def test_generate_candidate_happy_path_writes_sanitized_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "generation-happy"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    gate = validate_generation_gate(json.loads(gate_path.read_text(encoding="utf-8")))

    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    captured = capsys.readouterr()
    assert generation_cli.GENERATE_CANDIDATE_SUCCESS_OUTPUT in captured.out
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    receipt = validate_generation_receipt(json.loads(receipt_path.read_text(encoding="utf-8")))

    assert receipt["gate_id"] == gate["gate_id"]
    assert receipt["status"] == "accepted"
    assert receipt["promotion_ready"] is False
    assert receipt["authority"]["open_pull_request"] is False
    assert receipt["authority"]["resolve_review_threads"] is False
    assert receipt["authority"]["merge"] is False
    serialized = json.dumps(receipt, sort_keys=True)
    assert "diff --git" not in serialized
    assert "Do not run network commands" not in serialized
    assert "/Users/" not in serialized
    assert str(repo) not in serialized
    assert str(tmp_path) not in serialized
    assert "provider_payload" not in serialized

    assert generation_cli.main(["summarize-result", "--receipt", str(receipt_path)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["authority_boundary"] == "pr2_local_candidate_generation_only"
    assert summary["not_merge_readiness_evidence"] is True
    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 0
    )


def test_finalize_dispatched_result_writes_canonical_result_and_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "dispatch-finalize-accepted"
    gate_path, dispatch_path, packet = _prepare_generated_dispatch_handoff(
        monkeypatch=monkeypatch,
        repo=repo,
        base_sha=base_sha,
        run_id=run_id,
    )
    _write_json(dispatch_path, _trusted_dispatch_result(packet))
    monkeypatch.setattr(
        creative_code_patch_builder,
        "generate",
        lambda **_kwargs: pytest.fail("dispatch finalization must not regenerate"),
    )
    monkeypatch.setattr(
        creative_code_patch_builder,
        "evaluate",
        lambda **_kwargs: pytest.fail("dispatch finalization must not re-evaluate directly"),
    )

    assert (
        generation_cli.main(
            [
                "finalize-dispatched-result",
                "--gate",
                str(gate_path),
                "--dispatch-result",
                str(dispatch_path),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert generation_cli.FINALIZE_DISPATCHED_RESULT_SUCCESS_OUTPUT in captured.out
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    result = validate_creative_code_patch_result(
        json.loads((run_dir / creative_code_patch_builder.RESULT_FILE).read_text(encoding="utf-8"))
    )
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    receipt = validate_generation_receipt(json.loads(receipt_path.read_text(encoding="utf-8")))
    state = json.loads(
        (run_dir / creative_code_patch_builder.STATE_FILE).read_text(encoding="utf-8")
    )

    assert result["status"] == "accepted"
    assert result["runner_summary"]["attempts"] == 1
    assert result["runner_summary"]["retries_consumed"] == 0
    assert result["runner_summary"]["shared_tree_untouched"] is True
    assert receipt["result_fingerprint"] == fingerprint_payload(result)
    assert receipt["status"] == "accepted"
    assert state["candidate_patch_generated"] is True
    assert state["candidate_patch_evaluated"] is True
    serialized = json.dumps({"result": result, "receipt": receipt}, sort_keys=True)
    assert "oracle_results" not in serialized
    assert "/workspace" not in serialized
    assert "stdout" not in serialized
    assert "stderr" not in serialized
    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 0
    )


def test_finalize_dispatched_result_rejects_cooperative_lock_contention(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "dispatch-finalize-lock-contention"
    gate_path, dispatch_path, packet = _prepare_generated_dispatch_handoff(
        monkeypatch=monkeypatch,
        repo=repo,
        base_sha=base_sha,
        run_id=run_id,
    )
    _write_json(dispatch_path, _trusted_dispatch_result(packet))
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    command = [
        "finalize-dispatched-result",
        "--gate",
        str(gate_path),
        "--dispatch-result",
        str(dispatch_path),
    ]

    with generation_cli._exclusive_finalize_lock(run_dir):
        assert generation_cli.main(command) == 1
        assert "finalization is already in progress" in capsys.readouterr().err
        assert not (run_dir / creative_code_patch_builder.RESULT_FILE).exists()
        assert not (gate_path.parent / generation_cli.RECEIPT_FILENAME).exists()

    assert generation_cli.main(command) == 0
    capsys.readouterr()


def test_finalize_lock_reports_unavailable_platform_and_open_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    real_import = generation_cli.importlib.import_module

    def missing_fcntl(name: str) -> object:
        if name == "fcntl":
            raise ModuleNotFoundError(name)
        return real_import(name)

    with monkeypatch.context() as context:
        context.setattr(generation_cli.importlib, "import_module", missing_fcntl)
        with pytest.raises(
            CreativeCodePatchGenerationError,
            match="locking is unavailable",
        ):
            with generation_cli._exclusive_finalize_lock(run_dir):
                pytest.fail("unavailable lock must not enter the finalization body")

    def deny_open(*_args: object, **_kwargs: object) -> int:
        raise PermissionError("denied")

    with monkeypatch.context() as context:
        context.setattr(
            generation_cli.os,
            "open",
            deny_open,
        )
        with pytest.raises(
            CreativeCodePatchGenerationError,
            match="lock could not be acquired",
        ):
            with generation_cli._exclusive_finalize_lock(run_dir):
                pytest.fail("unavailable lock must not enter the finalization body")


def test_finalize_lock_is_released_after_abrupt_owner_exit(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import fcntl, os, sys; "
                "fd = os.open(sys.argv[1], os.O_RDONLY); "
                "fcntl.flock(fd, fcntl.LOCK_EX); "
                "os._exit(0)"
            ),
            str(run_dir),
        ],
        check=False,
    )
    assert child.returncode == 0

    with generation_cli._exclusive_finalize_lock(run_dir):
        pass


def test_finalize_dispatched_result_rolls_back_partial_publication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "dispatch-finalize-rollback"
    gate_path, dispatch_path, packet = _prepare_generated_dispatch_handoff(
        monkeypatch=monkeypatch,
        repo=repo,
        base_sha=base_sha,
        run_id=run_id,
    )
    _write_json(dispatch_path, _trusted_dispatch_result(packet))
    original_write_json_new = generation_cli._write_json_new

    def fail_receipt_write(path: Path, payload: dict[str, Any]) -> None:
        if path.name == generation_cli.RECEIPT_FILENAME:
            raise CreativeCodePatchGenerationError("simulated receipt publication failure")
        original_write_json_new(path, payload)

    monkeypatch.setattr(generation_cli, "_write_json_new", fail_receipt_write)

    assert (
        generation_cli.main(
            [
                "finalize-dispatched-result",
                "--gate",
                str(gate_path),
                "--dispatch-result",
                str(dispatch_path),
            ]
        )
        == 1
    )
    assert "simulated receipt publication failure" in capsys.readouterr().err
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    assert not (run_dir / creative_code_patch_builder.RESULT_FILE).exists()
    assert not (gate_path.parent / generation_cli.RECEIPT_FILENAME).exists()
    state = json.loads(
        (run_dir / creative_code_patch_builder.STATE_FILE).read_text(encoding="utf-8")
    )
    assert state["candidate_patch_generated"] is True
    assert state["candidate_patch_evaluated"] is False


def test_finalize_dispatched_result_wraps_raw_publication_error_after_rollback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "dispatch-finalize-raw-publication-error"
    gate_path, dispatch_path, packet = _prepare_generated_dispatch_handoff(
        monkeypatch=monkeypatch,
        repo=repo,
        base_sha=base_sha,
        run_id=run_id,
    )
    _write_json(dispatch_path, _trusted_dispatch_result(packet))

    def fail_result_write(_path: Path, _payload: dict[str, Any]) -> None:
        raise OSError("simulated filesystem failure")

    monkeypatch.setattr(generation_cli, "_write_json_new", fail_result_write)

    assert (
        generation_cli.main(
            [
                "finalize-dispatched-result",
                "--gate",
                str(gate_path),
                "--dispatch-result",
                str(dispatch_path),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "dispatch result publication failed after complete rollback" in captured.err
    assert "Traceback" not in captured.err


def test_finalize_dispatched_result_preserves_foreign_receipt_on_collision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "dispatch-finalize-foreign-receipt"
    gate_path, dispatch_path, packet = _prepare_generated_dispatch_handoff(
        monkeypatch=monkeypatch,
        repo=repo,
        base_sha=base_sha,
        run_id=run_id,
    )
    _write_json(dispatch_path, _trusted_dispatch_result(packet))
    foreign_receipt = {"owner": "another-publication"}
    original_write_json_new = generation_cli._write_json_new

    def collide_on_receipt(path: Path, payload: dict[str, Any]) -> None:
        if path.name == generation_cli.RECEIPT_FILENAME:
            _write_json(path, foreign_receipt)
            raise CreativeCodePatchGenerationError("simulated foreign receipt collision")
        original_write_json_new(path, payload)

    monkeypatch.setattr(generation_cli, "_write_json_new", collide_on_receipt)

    assert (
        generation_cli.main(
            [
                "finalize-dispatched-result",
                "--gate",
                str(gate_path),
                "--dispatch-result",
                str(dispatch_path),
            ]
        )
        == 1
    )
    assert "simulated foreign receipt collision" in capsys.readouterr().err
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == foreign_receipt
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    assert not (run_dir / creative_code_patch_builder.RESULT_FILE).exists()


def test_finalize_dispatched_result_attempts_every_rollback_after_cleanup_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "dispatch-finalize-rollback-cleanup-failure"
    gate_path, dispatch_path, packet = _prepare_generated_dispatch_handoff(
        monkeypatch=monkeypatch,
        repo=repo,
        base_sha=base_sha,
        run_id=run_id,
    )
    _write_json(dispatch_path, _trusted_dispatch_result(packet))
    original_write_json_new = generation_cli._write_json_new
    original_write_json_atomic = generation_cli.write_json_atomic

    def publish_receipt_then_fail(path: Path, payload: dict[str, Any]) -> None:
        original_write_json_new(path, payload)
        if path.name == generation_cli.RECEIPT_FILENAME:
            raise CreativeCodePatchGenerationError("simulated receipt publication failure")

    def fail_state_restoration(path: Path, payload: dict[str, Any]) -> None:
        if path.name == creative_code_patch_builder.STATE_FILE and (
            payload.get("candidate_patch_evaluated") is False
        ):
            raise OSError("simulated state restoration failure")
        original_write_json_atomic(path, payload)

    monkeypatch.setattr(generation_cli, "_write_json_new", publish_receipt_then_fail)
    monkeypatch.setattr(generation_cli, "write_json_atomic", fail_state_restoration)

    assert (
        generation_cli.main(
            [
                "finalize-dispatched-result",
                "--gate",
                str(gate_path),
                "--dispatch-result",
                str(dispatch_path),
            ]
        )
        == 1
    )
    assert "rollback was incomplete: state restoration: OSError" in capsys.readouterr().err
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    assert not (run_dir / creative_code_patch_builder.RESULT_FILE).exists()
    assert not (gate_path.parent / generation_cli.RECEIPT_FILENAME).exists()


@pytest.mark.parametrize(
    ("failure_class", "mutated_paths"),
    [
        ("guard_failure", None),
        ("timeout", None),
        ("capability_mismatch", []),
    ],
)
def test_finalize_dispatched_result_retains_trusted_rejection_without_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    failure_class: str,
    mutated_paths: list[str] | None,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = f"dispatch-finalize-{failure_class}"
    gate_path, dispatch_path, packet = _prepare_generated_dispatch_handoff(
        monkeypatch=monkeypatch,
        repo=repo,
        base_sha=base_sha,
        run_id=run_id,
    )
    dispatch_result = _trusted_dispatch_result(
        packet,
        status="rejected",
        failure_class=failure_class,
        mutated_paths=mutated_paths,
    )
    if failure_class == "capability_mismatch":
        dispatch_result["oracle_results"] = []
        dispatch_result["budget_observations"]["oracle_commands_executed"] = 0
    elif failure_class == "timeout":
        dispatch_result["oracle_results"][-1]["timed_out"] = True
    _write_json(dispatch_path, dispatch_result)

    assert (
        generation_cli.main(
            [
                "finalize-dispatched-result",
                "--gate",
                str(gate_path),
                "--dispatch-result",
                str(dispatch_path),
            ]
        )
        == 0
    )
    capsys.readouterr()
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    receipt = validate_generation_receipt(json.loads(receipt_path.read_text(encoding="utf-8")))
    assert receipt["status"] == "rejected"
    assert receipt["failure_class"] == failure_class
    assert receipt["runner_summary"]["attempts"] == 1
    assert receipt["runner_summary"]["retries_consumed"] == 0
    assert receipt["promotion_ready"] is False


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("experiment_id", "experiment_id does not match"),
        ("missing_backend", "execution backend provenance"),
        ("native_linux_backend", "failed Experiment Runner validation"),
        ("candidate_marker", "candidate marker is invalid"),
        ("patch_fingerprint", "candidate patch fingerprint does not match"),
        ("retry", "one attempt and zero retries"),
        ("extra_path", "mutated paths do not match"),
        ("oracle_command", "oracle commands do not match"),
        ("material_attribution", "must not claim promotion or material attribution"),
        ("all_pass_rejection", "requires failing oracle evidence"),
        ("timeout_without_timeout", "requires timed-out oracle evidence"),
        ("timeout_non_boolean", "failed Experiment Runner validation"),
        ("missing_oracle_paths", "must bind every candidate path"),
        ("unchanged_result", "does not support unchanged_result"),
    ],
)
def test_finalize_dispatched_result_rejects_unbound_dispatch_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    mutation: str,
    message: str,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = f"dispatch-unbound-{mutation}"
    gate_path, dispatch_path, packet = _prepare_generated_dispatch_handoff(
        monkeypatch=monkeypatch,
        repo=repo,
        base_sha=base_sha,
        run_id=run_id,
    )
    dispatch_result = _trusted_dispatch_result(packet)
    if mutation == "experiment_id":
        dispatch_result["experiment_id"] = "experiment_stale"
    elif mutation == "missing_backend":
        dispatch_result.pop("execution_backend")
    elif mutation == "native_linux_backend":
        dispatch_result["execution_backend"]["name"] = "native-linux"
    elif mutation == "candidate_marker":
        dispatch_result["candidate_patch"] = ".experiment-runner-input/other.patch"
    elif mutation == "patch_fingerprint":
        dispatch_result["candidate_patch_fingerprint"] = "sha256:" + ("f" * 64)
    elif mutation == "retry":
        dispatch_result["budget_observations"]["retries_consumed"] = 1
    elif mutation == "extra_path":
        dispatch_result["mutated_paths"] = ["core/rag/other.py"]
    elif mutation == "material_attribution":
        dispatch_result["promotion_ready"] = True
        dispatch_result["contribution_kind"] = "oracle_review"
        dispatch_result["coauthor_required"] = True
        dispatch_result["coauthor_reason"] = "Untrusted attribution."
    elif mutation == "all_pass_rejection":
        dispatch_result["status"] = "rejected"
        dispatch_result["failure_class"] = "guard_failure"
    elif mutation == "timeout_without_timeout":
        dispatch_result["status"] = "rejected"
        dispatch_result["failure_class"] = "timeout"
        dispatch_result["oracle_results"][-1]["returncode"] = 1
    elif mutation == "timeout_non_boolean":
        dispatch_result["status"] = "rejected"
        dispatch_result["failure_class"] = "timeout"
        dispatch_result["oracle_results"][-1]["timed_out"] = "false"
    elif mutation == "missing_oracle_paths":
        dispatch_result["status"] = "rejected"
        dispatch_result["failure_class"] = "guard_failure"
        dispatch_result["mutated_paths"] = []
        dispatch_result["oracle_results"][-1]["returncode"] = 1
    elif mutation == "unchanged_result":
        dispatch_result["status"] = "rejected"
        dispatch_result["failure_class"] = "unchanged_result"
        dispatch_result["mutated_paths"] = []
    else:
        dispatch_result["oracle_results"][0]["command"] = "pytest -q tests/test_other.py"
    _write_json(dispatch_path, dispatch_result)

    assert (
        generation_cli.main(
            [
                "finalize-dispatched-result",
                "--gate",
                str(gate_path),
                "--dispatch-result",
                str(dispatch_path),
            ]
        )
        == 1
    )
    assert message in capsys.readouterr().err
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    assert not (run_dir / creative_code_patch_builder.RESULT_FILE).exists()
    assert not (gate_path.parent / generation_cli.RECEIPT_FILENAME).exists()
    state = json.loads(
        (run_dir / creative_code_patch_builder.STATE_FILE).read_text(encoding="utf-8")
    )
    assert state["candidate_patch_evaluated"] is False


def test_resolve_dispatch_result_rejects_symlinked_canonical_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _patch_modules_to_repo(monkeypatch, repo)
    external_root = tmp_path / "external-results"
    external_root.mkdir()
    result_path = external_root / "dispatch.json"
    _write_json(result_path, {})
    canonical_parent = repo / "artifacts" / "orchestration" / "experiments"
    canonical_parent.mkdir(parents=True)
    (canonical_parent / "results").symlink_to(external_root, target_is_directory=True)

    with pytest.raises(
        generation_cli.CreativeCodePatchGenerationError,
        match="trusted dispatch result root must not traverse symlinks",
    ):
        generation_cli._resolve_dispatch_result(result_path)


def test_pinned_dispatch_read_rejects_leaf_replaced_by_symlink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _patch_modules_to_repo(monkeypatch, repo)
    result_root = repo / "artifacts" / "orchestration" / "experiments" / "results"
    result_root.mkdir(parents=True)
    result_path = result_root / "dispatch.json"
    _write_json(result_path, {"status": "accepted"})
    resolved = result_path.resolve(strict=True)
    external_result = tmp_path / "external-dispatch.json"
    _write_json(external_result, {"status": "rejected"})
    result_path.unlink()
    result_path.symlink_to(external_result)

    with pytest.raises(
        generation_cli.CreativeCodePatchGenerationError,
        match="unable to read trusted dispatch result safely",
    ):
        generation_cli._read_pinned_dispatch_json_object(resolved)


def test_finalize_dispatched_result_rejects_selected_variant_content_tamper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "dispatch-tampered-selected-variant"
    gate_path, dispatch_path, packet = _prepare_generated_dispatch_handoff(
        monkeypatch=monkeypatch,
        repo=repo,
        base_sha=base_sha,
        run_id=run_id,
    )
    _write_json(dispatch_path, _trusted_dispatch_result(packet))
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    selected_variant_path = run_dir / creative_code_patch_builder.SELECTED_VARIANT_FILE
    selected_variant = json.loads(selected_variant_path.read_text(encoding="utf-8"))
    selected_variant["problem_statement"] = "tampered but fingerprint field retained"
    _write_json(selected_variant_path, selected_variant)

    assert (
        generation_cli.main(
            [
                "finalize-dispatched-result",
                "--gate",
                str(gate_path),
                "--dispatch-result",
                str(dispatch_path),
            ]
        )
        == 1
    )
    assert (
        "selected variant no longer matches the validated source bundle" in capsys.readouterr().err
    )


def test_finalize_dispatched_result_rejects_tampered_candidate_and_duplicate_finalize(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "dispatch-tampered-candidate"
    gate_path, dispatch_path, packet = _prepare_generated_dispatch_handoff(
        monkeypatch=monkeypatch,
        repo=repo,
        base_sha=base_sha,
        run_id=run_id,
    )
    _write_json(dispatch_path, _trusted_dispatch_result(packet))
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    patch_path = run_dir / creative_code_patch_builder.CANDIDATE_PATCH_FILE
    original_patch = patch_path.read_text(encoding="utf-8")
    patch_path.write_text(original_patch.replace("return 2", "return 999"), encoding="utf-8")

    command = [
        "finalize-dispatched-result",
        "--gate",
        str(gate_path),
        "--dispatch-result",
        str(dispatch_path),
    ]
    assert generation_cli.main(command) == 1
    assert "candidate patch metadata is stale" in capsys.readouterr().err
    patch_path.write_text(original_patch, encoding="utf-8")
    assert generation_cli.main(command) == 0
    capsys.readouterr()
    assert generation_cli.main(command) == 1
    assert "generation receipt already exists" in capsys.readouterr().err


def test_generate_candidate_persists_capability_mismatch_without_retry_or_promotion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "generation-capability-mismatch"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    evaluator_calls = 0

    def reject_for_capability(packet: dict[str, Any], patch_file: Path) -> dict[str, Any]:
        nonlocal evaluator_calls
        evaluator_calls += 1
        assert patch_file.name == creative_code_patch_builder.CANDIDATE_PATCH_FILE
        return {
            "experiment_id": packet["experiment_id"],
            "status": "rejected",
            "failure_class": "capability_mismatch",
            "mutated_paths": ["core/rag/orchestration.py"],
            "oracle_results": [],
            "budget_observations": {
                "oracle_commands_configured": len(packet["immutable_oracles"]),
                "attempts": 1,
                "retries_consumed": 0,
                "runner_error": "/Users/example/ghp_secretsecretsecret",
            },
            "shared_tree_untouched": True,
        }

    monkeypatch.setattr(creative_code_patch_builder, "evaluate_candidate", reject_for_capability)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)

    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    assert evaluator_calls == 1
    assert generation_cli.GENERATE_CANDIDATE_SUCCESS_OUTPUT in capsys.readouterr().out

    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    result_path = run_dir / creative_code_patch_builder.RESULT_FILE
    result = validate_creative_code_patch_result(
        json.loads(result_path.read_text(encoding="utf-8"))
    )
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    receipt = validate_generation_receipt(json.loads(receipt_path.read_text(encoding="utf-8")))

    assert result["status"] == "rejected"
    assert result["failure_class"] == "capability_mismatch"
    assert result["runner_summary"]["failure_class"] == "capability_mismatch"
    assert result["runner_summary"]["attempts"] == 1
    assert result["runner_summary"]["retries_consumed"] == 0
    assert result["promotion_ready"] is False
    assert result["authority"]["promotion"] is False
    assert receipt["status"] == "rejected"
    assert receipt["failure_class"] == "capability_mismatch"
    assert receipt["result_fingerprint"] == fingerprint_payload(result)
    assert receipt["runner_summary"]["failure_class"] == "capability_mismatch"
    assert receipt["runner_summary"]["attempts"] == 1
    assert receipt["runner_summary"]["retries_consumed"] == 0
    assert receipt["promotion_ready"] is False
    assert receipt["authority"]["promote_candidate"] is False

    serialized = json.dumps({"result": result, "receipt": receipt}, sort_keys=True)
    assert "/Users/example" not in serialized
    assert "ghp_secret" not in serialized
    assert "oracle_results" not in serialized
    assert "stdout" not in serialized
    assert "stderr" not in serialized
    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 0
    )

    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 1
    assert evaluator_calls == 1
    assert "prepared run already generated candidate patch" in capsys.readouterr().err


def test_validate_artifacts_rejects_receipt_gate_fingerprint_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "receipt-gate-mismatch"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["gate_fingerprint"] = "sha256:" + ("0" * 64)
    generation_cli._set_identity(
        receipt,
        id_key="receipt_id",
        asset_type=generation_cli.RECEIPT_ARTIFACT_TYPE,
    )
    _write_json(receipt_path, receipt)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "gate fingerprint does not match" in capsys.readouterr().err


def test_receipt_validator_rejects_unknown_failures_and_incoherent_runner_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "receipt-failure-coherence"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    capsys.readouterr()
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    reference = json.loads(receipt_path.read_text(encoding="utf-8"))

    unsupported_top_level = deepcopy(reference)
    unsupported_top_level["status"] = "rejected"
    unsupported_top_level["failure_class"] = "unknown_failure"
    _reset_receipt_identity(unsupported_top_level)
    with pytest.raises(CreativeCodePatchGenerationError, match="failure_class is unsupported"):
        validate_generation_receipt(unsupported_top_level)

    unsupported_runner = deepcopy(reference)
    unsupported_runner["runner_summary"]["status"] = "rejected"
    unsupported_runner["runner_summary"]["failure_class"] = "unknown_failure"
    _reset_receipt_identity(unsupported_runner)
    with pytest.raises(
        CreativeCodePatchGenerationError,
        match="runner_summary.failure_class is unsupported",
    ):
        validate_generation_receipt(unsupported_runner)

    for receipt_failure, runner_failure in (
        ("capability_mismatch", "infra_flake"),
        ("infra_flake", "capability_mismatch"),
    ):
        mismatched_rejection = deepcopy(reference)
        mismatched_rejection["status"] = "rejected"
        mismatched_rejection["failure_class"] = receipt_failure
        mismatched_rejection["runner_summary"].update(
            {
                "status": "rejected",
                "failure_class": runner_failure,
                "attempts": 1,
                "retries_consumed": 0,
            }
        )
        _reset_receipt_identity(mismatched_rejection)
        with pytest.raises(
            CreativeCodePatchGenerationError,
            match="rejected receipt and runner summary failure_class values must match",
        ):
            validate_generation_receipt(mismatched_rejection)

    capability_retry_tamper = deepcopy(reference)
    capability_retry_tamper["status"] = "rejected"
    capability_retry_tamper["failure_class"] = "capability_mismatch"
    capability_retry_tamper["runner_summary"].update(
        {
            "status": "rejected",
            "failure_class": "capability_mismatch",
            "attempts": 2,
            "retries_consumed": 1,
        }
    )
    _reset_receipt_identity(capability_retry_tamper)
    with pytest.raises(
        CreativeCodePatchGenerationError,
        match="capability_mismatch must use attempts 0 or 1 and retries_consumed 0",
    ):
        validate_generation_receipt(capability_retry_tamper)

    for field, message in (
        (
            "mutated_path_count",
            "capability_mismatch with attempts 0 must use mutated_path_count 0",
        ),
        (
            "oracle_commands_executed",
            "capability_mismatch with attempts 0 must use oracle_commands_executed 0",
        ),
    ):
        zero_attempt_tamper = deepcopy(reference)
        zero_attempt_tamper["status"] = "rejected"
        zero_attempt_tamper["failure_class"] = "capability_mismatch"
        zero_attempt_tamper["runner_summary"].update(
            {
                "status": "rejected",
                "failure_class": "capability_mismatch",
                "mutated_path_count": 0,
                "oracle_commands_executed": 0,
                "attempts": 0,
                "retries_consumed": 0,
            }
        )
        zero_attempt_tamper["runner_summary"][field] = 1
        _reset_receipt_identity(zero_attempt_tamper)
        with pytest.raises(CreativeCodePatchGenerationError, match=message):
            validate_generation_receipt(zero_attempt_tamper)

    for attempts, mutated_path_count, oracle_commands_executed in (
        (0, 0, 0),
        (1, 1, 1),
    ):
        coherent_capability = deepcopy(reference)
        coherent_capability["status"] = "rejected"
        coherent_capability["failure_class"] = "capability_mismatch"
        coherent_capability["runner_summary"].update(
            {
                "status": "rejected",
                "failure_class": "capability_mismatch",
                "mutated_path_count": mutated_path_count,
                "oracle_commands_configured": 1,
                "oracle_commands_executed": oracle_commands_executed,
                "attempts": attempts,
                "retries_consumed": 0,
            }
        )
        _reset_receipt_identity(coherent_capability)
        assert validate_generation_receipt(coherent_capability) == coherent_capability

    top_level_capability_retry_tamper = deepcopy(reference)
    top_level_capability_retry_tamper["status"] = "rejected"
    top_level_capability_retry_tamper["failure_class"] = "capability_mismatch"
    top_level_capability_retry_tamper["runner_summary"]["attempts"] = 2
    top_level_capability_retry_tamper["runner_summary"]["retries_consumed"] = 1
    _reset_receipt_identity(top_level_capability_retry_tamper)
    with pytest.raises(
        CreativeCodePatchGenerationError,
        match="capability_mismatch receipts require a rejected runner summary",
    ):
        validate_generation_receipt(top_level_capability_retry_tamper)

    compound_capability_retry_tamper = deepcopy(reference)
    compound_capability_retry_tamper["failure_class"] = "capability_mismatch"
    compound_capability_retry_tamper["runner_summary"].update(
        {
            "status": "rejected",
            "failure_class": "capability_mismatch",
            "attempts": 2,
            "retries_consumed": 1,
        }
    )
    _reset_receipt_identity(compound_capability_retry_tamper)
    with pytest.raises(
        CreativeCodePatchGenerationError,
        match="accepted receipt must not have failure_class",
    ):
        validate_generation_receipt(compound_capability_retry_tamper)

    accepted_with_rejected_runner = deepcopy(reference)
    accepted_with_rejected_runner["runner_summary"]["status"] = "rejected"
    accepted_with_rejected_runner["runner_summary"]["failure_class"] = "guard_failure"
    accepted_with_rejected_runner["workspace_summary"]["origin_removed"] = False
    _reset_receipt_identity(accepted_with_rejected_runner)
    with pytest.raises(
        CreativeCodePatchGenerationError,
        match="accepted receipt requires an accepted runner summary",
    ):
        validate_generation_receipt(accepted_with_rejected_runner)

    for runner_updates in (
        {"shared_tree_untouched": False},
        {"oracle_commands_configured": 0, "oracle_commands_executed": 0},
        {"oracle_commands_configured": 2, "oracle_commands_executed": 1},
    ):
        incomplete_runner_proof = deepcopy(reference)
        incomplete_runner_proof["runner_summary"].update(runner_updates)
        _reset_receipt_identity(incomplete_runner_proof)
        with pytest.raises(
            CreativeCodePatchGenerationError,
            match="accepted receipt requires complete runner oracle and shared-tree proof",
        ):
            validate_generation_receipt(incomplete_runner_proof)

    wrapper_rejection = deepcopy(reference)
    wrapper_rejection["status"] = "rejected"
    wrapper_rejection["failure_class"] = "guard_failure"
    _reset_receipt_identity(wrapper_rejection)
    assert validate_generation_receipt(wrapper_rejection) == wrapper_rejection

    capability_without_runner_proof = deepcopy(reference)
    capability_without_runner_proof["status"] = "rejected"
    capability_without_runner_proof["failure_class"] = "capability_mismatch"
    _reset_receipt_identity(capability_without_runner_proof)
    with pytest.raises(
        CreativeCodePatchGenerationError,
        match="capability_mismatch receipts require a rejected runner summary",
    ):
        validate_generation_receipt(capability_without_runner_proof)


def test_validate_artifacts_rejects_tampered_receipt_gate_ref_with_recomputed_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "receipt-gate-ref-tamper"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["gate_ref"] = (
        "artifacts/orchestration/creative_code/patch_generation/" "other-run/generation_gate.json"
    )
    _reset_receipt_identity(receipt)
    _write_json(receipt_path, receipt)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "generation receipt gate_ref does not match gate" in capsys.readouterr().err


def test_validate_artifacts_rejects_tampered_receipt_request_id_with_recomputed_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "receipt-request-id-tamper"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["request_id"] = "tampered-request-id"
    _reset_receipt_identity(receipt)
    _write_json(receipt_path, receipt)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "generation receipt request_id does not match gate" in capsys.readouterr().err


def test_validate_artifacts_rejects_receipt_authority_tamper_with_recomputed_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "receipt-authority-tamper"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["authority"]["open_pull_request"] = True
    _reset_receipt_identity(receipt)
    _write_json(receipt_path, receipt)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "open_pull_request" in capsys.readouterr().err


def test_validate_artifacts_rejects_missing_linked_candidate_patch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "missing-linked-candidate"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    (run_dir / creative_code_patch_builder.CANDIDATE_PATCH_FILE).unlink()

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "candidate_patch_ref must exist" in capsys.readouterr().err


def test_validate_artifacts_rejects_stale_result_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "stale-result-fingerprint"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    result_path = run_dir / creative_code_patch_builder.RESULT_FILE
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["runner_summary"]["runner_result_fingerprint"] = "sha256:" + ("0" * 64)
    _write_json(result_path, result)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "result_id does not match result content" in capsys.readouterr().err


def test_validate_artifacts_rejects_tampered_candidate_patch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "tampered-candidate-patch"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    patch_path = run_dir / creative_code_patch_builder.CANDIDATE_PATCH_FILE
    patch_path.write_text(
        patch_path.read_text(encoding="utf-8").replace("return 2", "return 999"),
        encoding="utf-8",
    )

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "candidate patch does not match receipt summary" in capsys.readouterr().err


def test_validate_artifacts_rejects_tampered_experiment_packet(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "tampered-experiment-packet"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    packet_path = run_dir / creative_code_patch_builder.EXPERIMENT_PACKET_FILE
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["budgets"]["network_budget"] = 1
    _write_json(packet_path, packet)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "experiment packet fingerprint is stale" in capsys.readouterr().err

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["experiment_packet_fingerprint"] = fingerprint_payload(packet)
    _reset_receipt_identity(receipt)
    _write_json(receipt_path, receipt)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "experiment packet budgets are stale" in capsys.readouterr().err


def test_validate_artifacts_checks_patch_metadata_fingerprint_before_semantics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "tampered-patch-metadata-order"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    metadata_path = run_dir / creative_code_patch_builder.PATCH_METADATA_FILE
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["changed_paths"] = ["core/rag/other.py"]
    metadata["changed_path_statuses"] = {"core/rag/other.py": "M"}
    _write_json(metadata_path, metadata)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "patch metadata fingerprint is stale" in capsys.readouterr().err

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["patch_metadata_fingerprint"] = fingerprint_payload(metadata)
    _reset_receipt_identity(receipt)
    _write_json(receipt_path, receipt)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "patch_metadata changed paths mismatch" in capsys.readouterr().err


def test_validate_artifacts_rejects_recomputed_noncanonical_experiment_packet(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "noncanonical-experiment-packet"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    packet_path = run_dir / creative_code_patch_builder.EXPERIMENT_PACKET_FILE
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["negative_controls"][0] = "noncanonical but structurally valid control"
    _write_json(packet_path, packet)

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["experiment_packet_fingerprint"] = fingerprint_payload(packet)
    _reset_receipt_identity(receipt)
    _write_json(receipt_path, receipt)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "experiment packet semantics are stale" in capsys.readouterr().err


def test_validate_artifacts_rejects_cross_run_sidecar_refs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    _mock_successful_builder_edges(monkeypatch)

    run_a = "cross-run-a"
    admission_a = _prepare_admission(
        repo=repo,
        base_sha=base_sha,
        run_id=run_a,
        output_name="generation-admission-a",
    )
    gate_a = _write_gate(
        repo=repo,
        admission_path=admission_a,
        run_id=run_a,
        output_name="generation-gate-a",
    )
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_a)]) == 0
    receipt_a_path = gate_a.parent / generation_cli.RECEIPT_FILENAME

    run_b = "cross-run-b"
    admission_b = _prepare_admission(
        repo=repo,
        base_sha=base_sha,
        run_id=run_b,
        output_name="generation-admission-b",
    )
    gate_b = _write_gate(
        repo=repo,
        admission_path=admission_b,
        run_id=run_b,
        output_name="generation-gate-b",
    )
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_b)]) == 0
    receipt_b = json.loads(
        (gate_b.parent / generation_cli.RECEIPT_FILENAME).read_text(encoding="utf-8")
    )

    receipt_a = json.loads(receipt_a_path.read_text(encoding="utf-8"))
    for key in (
        "candidate_patch_ref",
        "patch_metadata_ref",
        "patch_metadata_fingerprint",
        "experiment_packet_ref",
        "experiment_packet_fingerprint",
        "result_ref",
        "result_id",
        "result_fingerprint",
        "status",
        "failure_class",
        "changed_paths",
        "patch_summary",
        "workspace_summary",
        "runner_summary",
        "promotion_ready",
    ):
        receipt_a[key] = deepcopy(receipt_b[key])
    generation_cli._set_identity(
        receipt_a,
        id_key="receipt_id",
        asset_type=generation_cli.RECEIPT_ARTIFACT_TYPE,
    )
    _write_json(receipt_a_path, receipt_a)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_a), "--receipt", str(receipt_a_path)]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "sidecar refs must point to the receipt run_id" in captured.err
    assert "patch_metadata_ref" in captured.err


def test_validate_artifacts_rejects_unsafe_patch_metadata_extra_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "unsafe-patch-metadata"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    metadata_path = run_dir / creative_code_patch_builder.PATCH_METADATA_FILE
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["raw_prompt"] = "diff --git a/core/rag/orchestration.py b/core/rag/orchestration.py"
    _write_json(metadata_path, metadata)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    stderr = capsys.readouterr().err
    assert "patch metadata has unsupported fields." in stderr
    assert "raw_prompt" not in stderr


def test_validate_artifacts_rejects_duplicate_patch_metadata_key_without_echoing_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "duplicate-patch-metadata"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    metadata_path = run_dir / creative_code_patch_builder.PATCH_METADATA_FILE
    metadata_path.write_text(
        '{"changed_paths":[],"GH_TOKEN=ghs_secretsecretsecret":1,'
        '"GH_TOKEN=ghs_secretsecretsecret":2}',
        encoding="utf-8",
    )

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    stderr = capsys.readouterr().err
    assert "duplicate key" in stderr
    assert "GH_TOKEN" not in stderr
    assert "ghs_secret" not in stderr


def test_validate_artifacts_rejects_forged_sidecars_outside_request_allowlist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "forged-sidecar-allowlist"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    patch_text = (
        (run_dir / creative_code_patch_builder.CANDIDATE_PATCH_FILE)
        .read_text(encoding="utf-8")
        .replace(
            "core/rag/orchestration.py",
            "core/rag/other.py",
        )
    )
    patch_fingerprint = fingerprint_payload({"candidate_patch": patch_text})
    request = json.loads(
        (run_dir / creative_code_patch_builder.REQUEST_FILE).read_text(encoding="utf-8")
    )
    result = build_creative_code_patch_result(
        request=request,
        changed_paths=["core/rag/other.py"],
        patch_fingerprint=patch_fingerprint,
        patch_bytes=len(patch_text.encode("utf-8")),
        diff_lines=len(patch_text.splitlines()),
        runner_result={
            "experiment_id": "exp-reference",
            "status": "accepted",
            "failure_class": None,
            "mutated_paths": ["core/rag/other.py"],
            "budget_observations": {
                "oracle_commands_configured": 1,
                "attempts": 1,
                "retries_consumed": 0,
            },
            "oracle_results": [{"status": "passed"}],
            "shared_tree_untouched": True,
        },
        checkout_destroyed=True,
        origin_removed=True,
        shared_tree_untouched=True,
        failure_class=None,
    )
    metadata = {
        "changed_paths": ["core/rag/other.py"],
        "changed_path_statuses": {"core/rag/other.py": "M"},
        "patch_fingerprint": patch_fingerprint,
        "patch_bytes": len(patch_text.encode("utf-8")),
        "diff_lines": len(patch_text.splitlines()),
    }
    (run_dir / creative_code_patch_builder.CANDIDATE_PATCH_FILE).write_text(
        patch_text,
        encoding="utf-8",
    )
    _write_json(run_dir / creative_code_patch_builder.PATCH_METADATA_FILE, metadata)
    _write_json(run_dir / creative_code_patch_builder.RESULT_FILE, result)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt.update(
        {
            "patch_metadata_fingerprint": fingerprint_payload(metadata),
            "result_id": result["result_id"],
            "result_fingerprint": fingerprint_payload(result),
            "status": result["status"],
            "failure_class": result["failure_class"],
            "changed_paths": result["changed_paths"],
            "patch_summary": result["patch_summary"],
            "workspace_summary": result["workspace_summary"],
            "runner_summary": result["runner_summary"],
            "promotion_ready": result["promotion_ready"],
        }
    )
    generation_cli._set_identity(
        receipt,
        id_key="receipt_id",
        asset_type=generation_cli.RECEIPT_ARTIFACT_TYPE,
    )
    _write_json(receipt_path, receipt)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "outside PR-2 request allowlist" in capsys.readouterr().err


def test_validate_artifacts_rejects_duplicate_result_key_without_echoing_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "duplicate-result-key"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 0
    receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    result_path = run_dir / creative_code_patch_builder.RESULT_FILE
    result_path.write_text(
        '{"schema_version":"1.0","GH_TOKEN=ghs_secretsecretsecret":1,'
        '"GH_TOKEN=ghs_secretsecretsecret":2}',
        encoding="utf-8",
    )

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    stderr = capsys.readouterr().err
    assert "GH_TOKEN" not in stderr
    assert "ghs_secret" not in stderr


def test_generation_gate_rejects_unprepared_admission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    _bundle, bundle_path, receipt_path, human_path = _write_inputs(repo)
    output_dir = _output_dir(repo, "unprepared-admission")
    assert (
        admission_cli.main(
            [
                "build-request",
                "--finalize-receipt",
                str(receipt_path),
                "--bundle",
                str(bundle_path),
                "--human-admission",
                str(human_path),
                "--base-sha",
                base_sha,
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        generation_cli.main(
            [
                "validate-run-plan",
                "--admission",
                str(output_dir / admission_cli.ADMISSION_FILENAME),
                "--run-id",
                "unprepared",
                "--output-dir",
                str(_generation_dir(repo, "unprepared")),
            ]
        )
        == 1
    )
    assert "admission must be prepared" in capsys.readouterr().err
    assert not _generation_dir(repo, "unprepared").exists()

    run_dir = "unprepared-retry"
    assert (
        generation_cli.main(
            [
                "validate-run-plan",
                "--admission",
                str(output_dir / admission_cli.ADMISSION_FILENAME),
                "--run-id",
                run_dir,
                "--output-dir",
                str(_generation_dir(repo, "unprepared")),
            ]
        )
        == 1
    )
    assert "admission must be prepared" in capsys.readouterr().err
    assert not _generation_dir(repo, "unprepared").exists()


def test_generation_gate_rejects_stale_base_before_generate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "stale-before-generate"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    called = {"codex": False}

    def fail_run_codex_exec(**_kwargs: Any) -> dict[str, int]:
        called["codex"] = True
        raise AssertionError("generation must not start for a stale base")

    monkeypatch.setattr(creative_code_patch_builder, "run_codex_exec", fail_run_codex_exec)
    (repo / "core" / "rag" / "second.py").write_text("value = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "advance main")
    new_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "update-ref", "refs/remotes/origin/main", new_sha)

    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 1
    assert "base_commit_sha must match current origin/main" in capsys.readouterr().err
    assert called["codex"] is False
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    assert not (run_dir / creative_code_patch_builder.CANDIDATE_PATCH_FILE).exists()


def test_generation_gate_rejects_dirty_shared_tree(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "dirty-tree"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    assert (
        generation_cli.main(
            [
                "validate-run-plan",
                "--admission",
                str(admission_path),
                "--run-id",
                run_id,
                "--output-dir",
                str(_generation_dir(repo, "dirty-tree")),
            ]
        )
        == 1
    )
    assert "shared worktree must be clean" in capsys.readouterr().err


def test_generation_gate_rejects_request_source_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "request-mismatch"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    admission = json.loads(admission_path.read_text(encoding="utf-8"))
    request_path = repo / admission["patch_request"]["request_ref"]
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["metrics"] = ["request/source mismatch tamper"]
    _write_json(request_path, request)

    assert (
        generation_cli.main(
            [
                "validate-run-plan",
                "--admission",
                str(admission_path),
                "--run-id",
                run_id,
                "--output-dir",
                str(_generation_dir(repo, "request-mismatch")),
            ]
        )
        == 1
    )
    assert "request_id does not match request content" in capsys.readouterr().err


def test_generation_gate_rejects_authority_widening_and_unsafe_refs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "authority-widening"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    gate = json.loads(gate_path.read_text(encoding="utf-8"))

    widened = deepcopy(gate)
    widened["authority"]["open_pull_request"] = True
    with pytest.raises(CreativeCodePatchGenerationError, match="open_pull_request"):
        validate_generation_gate(widened)

    unsafe = deepcopy(gate)
    unsafe["admission_ref"] = "artifacts/orchestration/creative_code/raw_prompt.json"
    with pytest.raises(CreativeCodePatchGenerationError, match="unsafe text"):
        validate_generation_gate(unsafe)

    absolute = deepcopy(gate)
    absolute["request_ref"] = "/Users/example/request.json"
    with pytest.raises(CreativeCodePatchGenerationError, match="repo-relative"):
        validate_generation_gate(absolute)


def test_generation_gate_rejects_unsafe_advisory_hints(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "unsafe-hints"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    hints = {
        "schema_version": "1.0",
        "artifact_type": creative_spec_learning_rollup_contract.HINTS_ARTIFACT_TYPE,
        "policy_version": creative_spec_learning_rollup_contract.POLICY_VERSION,
        "hints_id": "unsafe-hints",
        "idempotency_key": "unsafe-hints-key",
        "source_rollup_id": "learning-rollup",
        "source_rollup_fingerprint": "sha256:" + ("9" * 64),
        "recommended_role_focus": [],
        "reuse_lesson_ids": [],
        "avoid_lesson_ids": [],
        "authority": creative_spec_learning_rollup_contract.default_hints_authority(),
        "sanitized": True,
    }
    hints["authority"]["generate_patch"] = True
    hints_path = (
        repo / "artifacts" / "orchestration" / "creative_code" / "learning" / "unsafe_hints.json"
    )
    _write_json(hints_path, hints)

    assert (
        generation_cli.main(
            [
                "validate-run-plan",
                "--admission",
                str(admission_path),
                "--run-id",
                run_id,
                "--coordinator-advisory-hints",
                str(hints_path),
                "--output-dir",
                str(_generation_dir(repo, "unsafe-hints")),
            ]
        )
        == 1
    )
    assert "generate_patch" in capsys.readouterr().err


def test_generate_candidate_rejects_preexisting_candidate_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "stale-candidate-artifact"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    called = {"codex": False}

    def fail_run_codex_exec(**_kwargs: Any) -> dict[str, int]:
        called["codex"] = True
        raise AssertionError("generation must not start with stale candidate artifacts")

    monkeypatch.setattr(creative_code_patch_builder, "run_codex_exec", fail_run_codex_exec)
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    (run_dir / creative_code_patch_builder.CANDIDATE_PATCH_FILE).write_text(
        "diff --git a/x b/x\n",
        encoding="utf-8",
    )

    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 1
    assert "pre-generation run already contains candidate.patch" in capsys.readouterr().err
    assert called["codex"] is False


def test_generate_candidate_rejects_changed_patch_metadata_before_evaluate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "changed-patch-metadata"
    admission_path = _prepare_admission(repo=repo, base_sha=base_sha, run_id=run_id)
    gate_path = _write_gate(repo=repo, admission_path=admission_path, run_id=run_id)
    _mock_successful_builder_edges(monkeypatch)
    real_generate = creative_code_patch_builder.generate
    called = {"evaluator": False}

    def tampering_generate(*, run_id: str) -> dict[str, Any]:
        metadata = real_generate(run_id=run_id)
        run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
        metadata_path = run_dir / creative_code_patch_builder.PATCH_METADATA_FILE
        tampered = json.loads(metadata_path.read_text(encoding="utf-8"))
        tampered["patch_bytes"] += 1
        _write_json(metadata_path, tampered)
        return metadata

    def fail_evaluate_candidate(_packet: dict[str, Any], _patch_file: Path) -> dict[str, Any]:
        called["evaluator"] = True
        raise AssertionError("tampered metadata must fail before evaluator")

    monkeypatch.setattr(creative_code_patch_builder, "generate", tampering_generate)
    monkeypatch.setattr(creative_code_patch_builder, "evaluate_candidate", fail_evaluate_candidate)

    assert generation_cli.main(["generate-candidate", "--gate", str(gate_path)]) == 1
    assert "candidate patch metadata does not match patch" in capsys.readouterr().err
    assert called["evaluator"] is False
    assert not (gate_path.parent / generation_cli.RECEIPT_FILENAME).exists()


def test_generation_schemas_are_closed_and_authority_is_const_false() -> None:
    gate_schema = json.loads(GATE_SCHEMA.read_text(encoding="utf-8"))
    receipt_schema = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))

    assert gate_schema["additionalProperties"] is False
    assert receipt_schema["additionalProperties"] is False
    assert gate_schema["$defs"]["checks"]["additionalProperties"] is False
    assert receipt_schema["$defs"]["checks"]["additionalProperties"] is False
    assert gate_schema["$defs"]["authority"]["properties"]["open_pull_request"]["const"] is False
    assert gate_schema["$defs"]["authority"]["properties"]["write_repository"]["const"] is False
    assert gate_schema["$defs"]["authority"]["properties"]["use_semantic_cache"]["const"] is False
    assert receipt_schema["$defs"]["authority"]["properties"]["promote_candidate"]["const"] is False
    assert (
        receipt_schema["$defs"]["authority"]["properties"]["resolve_review_threads"]["const"]
        is False
    )
    assert receipt_schema["properties"]["promotion_ready"]["const"] is False
    assert "candidate\\.patch" in receipt_schema["$defs"]["patch_artifact_ref"]["pattern"]
    failure_classes = [
        "timeout",
        "oom",
        "metric_regression",
        "guard_failure",
        "policy_violation",
        "unchanged_result",
        "capability_mismatch",
        "infra_flake",
    ]
    assert receipt_schema["$defs"]["failure_class"]["enum"] == [None, *failure_classes]
    assert receipt_schema["allOf"][0]["then"]["properties"]["failure_class"] == {"const": None}
    assert receipt_schema["allOf"][0]["then"]["properties"]["runner_summary"] == {
        "$ref": "#/$defs/accepted_runner_proof"
    }
    accepted_runner_proof = receipt_schema["$defs"]["accepted_runner_proof"]
    assert accepted_runner_proof["properties"]["status"] == {"const": "accepted"}
    assert accepted_runner_proof["properties"]["failure_class"] == {"const": None}
    assert accepted_runner_proof["properties"]["shared_tree_untouched"] == {"const": True}
    accepted_oracle_pairs = {
        (
            pair["properties"]["oracle_commands_configured"]["const"],
            pair["properties"]["oracle_commands_executed"]["const"],
        )
        for pair in accepted_runner_proof["oneOf"]
    }
    assert accepted_oracle_pairs == {(count, count) for count in range(1, 21)}
    assert (
        receipt_schema["allOf"][1]["then"]["properties"]["failure_class"]["enum"] == failure_classes
    )
    assert receipt_schema["allOf"][2]["if"]["properties"]["failure_class"] == {
        "const": "capability_mismatch"
    }
    root_runner_rule = receipt_schema["allOf"][2]["then"]["properties"]["runner_summary"]
    assert root_runner_rule["required"] == ["status", "failure_class"]
    root_retry_rule = root_runner_rule["properties"]
    assert root_retry_rule["status"] == {"const": "rejected"}
    assert root_retry_rule["failure_class"] == {"const": "capability_mismatch"}
    assert root_retry_rule["attempts"] == {"enum": [0, 1]}
    assert root_retry_rule["retries_consumed"] == {"const": 0}
    rejected_pair_rule = receipt_schema["allOf"][3]
    assert rejected_pair_rule["if"]["properties"]["status"] == {"const": "rejected"}
    assert rejected_pair_rule["if"]["properties"]["runner_summary"]["properties"]["status"] == {
        "const": "rejected"
    }
    rejected_pairs = {
        (
            pair["properties"]["failure_class"]["const"],
            pair["properties"]["runner_summary"]["properties"]["failure_class"]["const"],
        )
        for pair in rejected_pair_rule["then"]["oneOf"]
    }
    assert rejected_pairs == {(failure, failure) for failure in failure_classes}
    runner_rules = receipt_schema["$defs"]["runner_summary"]["allOf"]
    assert runner_rules[0]["then"]["properties"]["failure_class"] == {"const": None}
    assert runner_rules[1]["then"]["properties"]["failure_class"]["enum"] == failure_classes
    assert runner_rules[2]["if"]["properties"]["failure_class"] == {"const": "capability_mismatch"}
    assert runner_rules[2]["then"]["properties"]["attempts"] == {"enum": [0, 1]}
    assert runner_rules[2]["then"]["properties"]["retries_consumed"] == {"const": 0}
    zero_attempt_rule = runner_rules[3]
    assert zero_attempt_rule["if"]["required"] == ["failure_class", "attempts"]
    assert zero_attempt_rule["if"]["properties"] == {
        "failure_class": {"const": "capability_mismatch"},
        "attempts": {"const": 0},
    }
    assert zero_attempt_rule["then"]["properties"] == {
        "mutated_path_count": {"const": 0},
        "oracle_commands_executed": {"const": 0},
    }
    assert "oracle_commands_configured" not in zero_attempt_rule["then"]["properties"]


def test_generation_cli_exposes_no_promotion_or_github_commands() -> None:
    forbidden = {
        "promote",
        "open-pr",
        "resolve-thread",
        "merge",
        "push",
        "approve",
        "fix",
    }
    for command in forbidden:
        with pytest.raises(SystemExit):
            generation_cli._parse_args([command])
