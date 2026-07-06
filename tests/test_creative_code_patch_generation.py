from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.orchestration import creative_code_patch_builder
from scripts.orchestration import creative_code_patch_generation as generation_cli
from scripts.orchestration import creative_code_patch_workspace
from scripts.orchestration import creative_spec_learning_rollup_contract
from scripts.orchestration import creative_spec_patch_admission as admission_cli
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
    result["runner_summary"]["oracle_commands_executed"] = 0
    _write_json(result_path, result)

    assert (
        generation_cli.main(
            ["validate-artifacts", "--gate", str(gate_path), "--receipt", str(receipt_path)]
        )
        == 1
    )
    assert "result_id does not match result content" in capsys.readouterr().err


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
