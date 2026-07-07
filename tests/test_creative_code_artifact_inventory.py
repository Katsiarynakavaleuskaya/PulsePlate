from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_artifact_inventory as inventory_cli
from scripts.orchestration import creative_code_patch_generation as generation_cli
from scripts.orchestration import creative_code_patch_workspace
from scripts.orchestration.creative_code_patch_builder import (
    EXPERIMENT_PACKET_FILE,
    PATCH_METADATA_FILE,
    RESULT_FILE,
)
from scripts.orchestration.creative_code_pr_promotion_contract import (
    build_creative_code_pr_promotion_receipt,
)
from tests.test_creative_code_pr_promotion import _make_patch_run, _write_json

REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_SCHEMA = (
    REPO_ROOT
    / "docs/orchestration/contracts/creative_code_artifact_inventory_report.v1.schema.json"
)


def _patch_inventory_roots(
    monkeypatch: pytest.MonkeyPatch,
    repo: Path,
    *,
    origin_main: str = "a" * 40,
) -> None:
    creative_root = repo / "artifacts" / "orchestration" / "creative_code"
    monkeypatch.setattr(inventory_cli, "REPO_ROOT", repo)
    monkeypatch.setattr(inventory_cli, "CREATIVE_CODE_ROOT", creative_root)
    monkeypatch.setattr(inventory_cli, "PATCH_RUNS_ROOT", creative_root / "patch_runs")
    monkeypatch.setattr(
        inventory_cli,
        "PATCH_GENERATION_ROOT",
        creative_root / "patch_generation",
    )
    monkeypatch.setattr(inventory_cli, "PROMOTIONS_ROOT", creative_root / "promotions")
    monkeypatch.setattr(generation_cli, "REPO_ROOT", repo)
    monkeypatch.setattr(generation_cli, "CREATIVE_CODE_ROOT", creative_root)
    monkeypatch.setattr(generation_cli, "PATCH_GENERATION_ROOT", creative_root / "patch_generation")
    monkeypatch.setattr(creative_code_patch_workspace, "REPO_ROOT", repo)
    monkeypatch.setattr(
        creative_code_patch_workspace,
        "ARTIFACT_ROOT",
        creative_root / "patch_runs",
    )
    monkeypatch.setattr(inventory_cli, "current_origin_main_sha", lambda: origin_main)


def _report(
    monkeypatch: pytest.MonkeyPatch, repo: Path, *, origin_main: str = "a" * 40
) -> dict[str, Any]:
    _patch_inventory_roots(monkeypatch, repo, origin_main=origin_main)
    return inventory_cli.build_creative_code_artifact_inventory_report()


def _run_dir(repo: Path, run_id: str) -> Path:
    return repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs" / run_id


def _promotion_dir(repo: Path, promotion_id: str) -> Path:
    return repo / "artifacts" / "orchestration" / "creative_code" / "promotions" / promotion_id


def _write_promotion_receipt(
    repo: Path,
    *,
    result: dict[str, Any],
    promotion_id: str = "promotion-test",
    partial_failure: str | None = None,
) -> dict[str, Any]:
    receipt = build_creative_code_pr_promotion_receipt(
        promotion_id=promotion_id,
        plan_fingerprint="sha256:" + ("1" * 64),
        validation_fingerprint="sha256:" + ("2" * 64),
        approval_id="evidence:approval",
        source_result_id=result["result_id"],
        patch_fingerprint=result["patch_summary"]["patch_fingerprint"],
        head_branch="experiment/inventory-test-12345678",
        commit_sha="b" * 40,
        pull_request_number=9999,
        pull_request_url="https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/9999",
        approved_by_login="Katsiarynakavaleuskaya",
        partial_failure=partial_failure,
    )
    _write_json(_promotion_dir(repo, promotion_id) / inventory_cli.RECEIPT_FILE, receipt)
    return receipt


def _write_generation_receipt(
    repo: Path,
    *,
    run_id: str,
    tamper_ref: bool = False,
) -> dict[str, Any]:
    run_dir = _run_dir(repo, run_id)
    result = json.loads((run_dir / RESULT_FILE).read_text(encoding="utf-8"))
    metadata = json.loads((run_dir / PATCH_METADATA_FILE).read_text(encoding="utf-8"))
    packet = json.loads((run_dir / EXPERIMENT_PACKET_FILE).read_text(encoding="utf-8"))
    receipt = {
        "schema_version": generation_cli.SCHEMA_VERSION,
        "artifact_type": generation_cli.RECEIPT_ARTIFACT_TYPE,
        "policy_version": generation_cli.POLICY_VERSION,
        "receipt_id": "pending",
        "idempotency_key": "pending",
        "gate_id": "evidence:generation-gate",
        "gate_fingerprint": "sha256:" + ("3" * 64),
        "gate_ref": f"artifacts/orchestration/creative_code/patch_generation/{run_id}/generation_gate.json",
        "admission_id": "evidence:admission",
        "admission_fingerprint": "sha256:" + ("4" * 64),
        "admission_ref": "artifacts/orchestration/creative_code/patch_admission/admission.json",
        "request_id": result["request_id"],
        "request_fingerprint": "sha256:" + ("5" * 64),
        "request_ref": f"artifacts/orchestration/creative_code/patch_runs/{run_id}/request.json",
        "source_bundle_id": result["source_bundle_id"],
        "source_bundle_fingerprint": result["source_bundle_fingerprint"],
        "source_bundle_ref": f"artifacts/orchestration/creative_code/patch_runs/{run_id}/source_bundle.json",
        "selected_variant_id": result["selected_variant_id"],
        "selected_variant_fingerprint": result["selected_variant_fingerprint"],
        "base_commit_sha": result["base_commit_sha"],
        "run_id": run_id,
        "candidate_patch_ref": f"artifacts/orchestration/creative_code/patch_runs/{run_id}/candidate.patch",
        "patch_metadata_ref": f"artifacts/orchestration/creative_code/patch_runs/{run_id}/patch_metadata.json",
        "patch_metadata_fingerprint": fingerprint_payload(metadata),
        "experiment_packet_ref": f"artifacts/orchestration/creative_code/patch_runs/{run_id}/experiment_packet.json",
        "experiment_packet_fingerprint": fingerprint_payload(packet),
        "result_ref": f"artifacts/orchestration/creative_code/patch_runs/{run_id}/result.json",
        "result_id": result["result_id"],
        "result_fingerprint": fingerprint_payload(result),
        "status": result["status"],
        "failure_class": result["failure_class"],
        "changed_paths": result["changed_paths"],
        "patch_summary": result["patch_summary"],
        "workspace_summary": result["workspace_summary"],
        "runner_summary": result["runner_summary"],
        "promotion_ready": result["promotion_ready"],
        "checks": {key: True for key in sorted(generation_cli.RECEIPT_CHECK_KEYS)},
        "passed_checks": len(generation_cli.RECEIPT_CHECK_KEYS),
        "total_checks": len(generation_cli.RECEIPT_CHECK_KEYS),
        "authority": generation_cli.default_generation_authority(),
        "sanitized": True,
    }
    if tamper_ref:
        receipt["patch_metadata_ref"] = (
            "artifacts/orchestration/creative_code/patch_runs/other-run/patch_metadata.json"
        )
    generation_cli._set_identity(  # existing generation contract identity helper
        receipt,
        id_key="receipt_id",
        asset_type=generation_cli.RECEIPT_ARTIFACT_TYPE,
    )
    receipt_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "patch_generation"
        / run_id
        / generation_cli.RECEIPT_FILENAME
    )
    _write_json(receipt_path, receipt)
    return receipt


def test_status_empty_artifact_tree_is_safe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    report = _report(monkeypatch, repo)

    assert report["counts"]["patch_runs_total"] == 0
    assert report["cleanup"]["safe"] is True
    assert report["authority"]["delete_artifacts"] is False

    assert inventory_cli.main(["status", "--format", "text"]) == 0
    text = capsys.readouterr().out
    assert "ACCEPTED_RUNS=<none>" in text
    assert "CLEANUP_SAFE=true" in text


def test_accepted_unpromoted_run_allows_promotion_assertion_and_blocks_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, result = _make_patch_run(monkeypatch, tmp_path, accepted=True)
    report = _report(monkeypatch, repo, origin_main=result["base_commit_sha"])

    assert report["counts"]["patch_runs_accepted"] == 1
    assert report["patch_runs"][0]["promotion_candidate_state"] == "eligible"
    assert inventory_cli.assert_ready_for_promotion(run_id) == (True, [])
    assert inventory_cli.assert_ready_for_cleanup() == (False, ["accepted_run_unpromoted"])


def test_rejected_run_blocks_promotion_without_blocking_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, result = _make_patch_run(monkeypatch, tmp_path, accepted=False)
    report = _report(monkeypatch, repo, origin_main=result["base_commit_sha"])

    assert report["patch_runs"][0]["status"] == "rejected"
    ok, blockers = inventory_cli.assert_ready_for_promotion(run_id)
    assert ok is False
    assert "patch_run_not_accepted" in blockers
    assert inventory_cli.assert_ready_for_cleanup() == (True, [])


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (lambda path: path.unlink(), "missing_artifact"),
        (
            lambda path: path.write_text(
                json.dumps(
                    {
                        "changed_paths": ["core/rag/other.py"],
                        "patch_fingerprint": "sha256:" + ("0" * 64),
                        "patch_bytes": 1,
                        "diff_lines": 1,
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            ),
            "invalid_patch_run_sidecar",
        ),
    ],
)
def test_missing_or_tampered_sidecar_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutate: Any,
    expected_code: str,
) -> None:
    repo, run_id, result = _make_patch_run(monkeypatch, tmp_path, accepted=True)
    mutate(_run_dir(repo, run_id) / PATCH_METADATA_FILE)
    report = _report(monkeypatch, repo, origin_main=result["base_commit_sha"])

    assert report["patch_runs"][0]["valid"] is False
    assert report["read_errors"][0]["error_code"] == expected_code
    ok, blockers = inventory_cli.assert_ready_for_promotion(run_id)
    assert ok is False
    assert "invalid_patch_run_sidecar" in blockers


def test_patch_metadata_extra_unsafe_fields_blocks_promotion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, result = _make_patch_run(monkeypatch, tmp_path, accepted=True)
    metadata_path = _run_dir(repo, run_id) / PATCH_METADATA_FILE
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["raw_prompt"] = "/Users/example diff --git Authorization: Bearer ghp_secret"
    _write_json(metadata_path, metadata)
    report = _report(monkeypatch, repo, origin_main=result["base_commit_sha"])

    assert report["patch_runs"][0]["valid"] is False
    assert report["read_errors"][0]["error_code"] == "invalid_patch_run_sidecar"
    ok, blockers = inventory_cli.assert_ready_for_promotion(run_id)
    assert ok is False
    assert "artifact_read_error" in blockers
    assert "invalid_patch_run_sidecar" in blockers


def test_base_sha_drift_blocks_promotion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, result = _make_patch_run(monkeypatch, tmp_path, accepted=True)
    report = _report(monkeypatch, repo, origin_main="b" * 40)

    assert report["patch_runs"][0]["promotion_candidate_state"] == "base_sha_drift"
    ok, blockers = inventory_cli.assert_ready_for_promotion(run_id)
    assert ok is False
    assert "base_sha_drift" in blockers
    assert result["base_commit_sha"] == "a" * 40


def test_generation_receipt_mismatch_blocks_promotion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, result = _make_patch_run(monkeypatch, tmp_path, accepted=True)
    _write_generation_receipt(repo, run_id=run_id, tamper_ref=True)
    report = _report(monkeypatch, repo, origin_main=result["base_commit_sha"])

    assert report["generation_receipts"][0]["valid"] is False
    assert "generation_receipt_mismatch" in report["patch_runs"][0]["blockers"]
    ok, blockers = inventory_cli.assert_ready_for_promotion(run_id)
    assert ok is False
    assert "generation_receipt_mismatch" in blockers


def test_malformed_unlinked_generation_receipt_blocks_promotion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, result = _make_patch_run(monkeypatch, tmp_path, accepted=True)
    receipt_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "patch_generation"
        / "malformed"
        / generation_cli.RECEIPT_FILENAME
    )
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text('{"schema_version":"1.0",', encoding="utf-8")
    report = _report(monkeypatch, repo, origin_main=result["base_commit_sha"])

    assert report["read_errors"][0]["error_code"] == "unreadable_json"
    ok, blockers = inventory_cli.assert_ready_for_promotion(run_id)
    assert ok is False
    assert "artifact_read_error" in blockers


def test_malformed_unlinked_promotion_receipt_blocks_promotion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, result = _make_patch_run(monkeypatch, tmp_path, accepted=True)
    receipt_path = _promotion_dir(repo, "promotion-malformed") / inventory_cli.RECEIPT_FILE
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text('{"schema_version":"1.0",', encoding="utf-8")
    report = _report(monkeypatch, repo, origin_main=result["base_commit_sha"])

    assert report["read_errors"][0]["error_code"] == "invalid_promotion_receipt"
    ok, blockers = inventory_cli.assert_ready_for_promotion(run_id)
    assert ok is False
    assert "artifact_read_error" in blockers


def test_completed_promotion_receipt_blocks_duplicate_promotion_and_allows_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, result = _make_patch_run(monkeypatch, tmp_path, accepted=True)
    receipt = _write_promotion_receipt(repo, result=result)
    report = _report(monkeypatch, repo, origin_main=result["base_commit_sha"])

    assert report["patch_runs"][0]["promotion_linkage"] == "completed"
    assert report["patch_runs"][0]["promotion_receipt_ids"] == [receipt["receipt_id"]]
    assert report["cleanup"]["safe"] is True
    ok, blockers = inventory_cli.assert_ready_for_promotion(run_id)
    assert ok is False
    assert "promotion_receipt_exists" in blockers


def test_in_progress_promotion_artifact_blocks_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, _run_id, result = _make_patch_run(monkeypatch, tmp_path, accepted=True)
    _write_json(
        _promotion_dir(repo, "promotion-in-progress") / inventory_cli.PROMOTION_STATE_FILE, {}
    )
    report = _report(monkeypatch, repo, origin_main=result["base_commit_sha"])

    assert "promotion_in_progress" in report["cleanup"]["blockers"]
    assert "promotion-in-progress" in report["cleanup"]["in_progress_promotion_ids"]


def test_unsafe_artifact_content_is_redacted_from_json_and_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _run_id, result = _make_patch_run(monkeypatch, tmp_path, accepted=True)
    result_path = _run_dir(repo, "patch-run") / RESULT_FILE
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    payload["raw_prompt"] = "/Users/example diff --git Authorization: Bearer ghp_secret"
    _write_json(result_path, payload)
    _patch_inventory_roots(monkeypatch, repo, origin_main=result["base_commit_sha"])

    assert inventory_cli.main(["status", "--format", "json"]) == 0
    json_output = capsys.readouterr().out
    assert inventory_cli.main(["status", "--format", "text"]) == 0
    text_output = capsys.readouterr().out
    combined = json_output + text_output

    assert "/Users/example" not in combined
    assert "diff --git" not in combined
    assert "Authorization: Bearer" not in combined
    assert "ghp_secret" not in combined
    assert "invalid_patch_result" in combined


def test_schema_and_runtime_report_are_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    report = _report(monkeypatch, repo)
    schema = json.loads(INVENTORY_SCHEMA.read_text(encoding="utf-8"))

    assert schema["additionalProperties"] is False
    assert schema["properties"]["authority"]["additionalProperties"] is False
    assert inventory_cli.validate_creative_code_artifact_inventory_report(report) == report

    mutated = deepcopy(report)
    mutated["unexpected"] = True
    with pytest.raises(inventory_cli.CreativeCodeArtifactInventoryError):
        inventory_cli.validate_creative_code_artifact_inventory_report(mutated)


@pytest.mark.parametrize(
    "artifact_ref",
    [
        "artifacts/orchestration/creative_code/../secret.json",
        "artifacts/orchestration/creative_code//result.json",
        "artifacts/orchestration/creative_code/.hidden/result.json",
        "artifacts/orchestration/creative_code/unsafe path/result.json",
        "artifacts/orchestration/creative_code/patch_runs/путь/result.json",
    ],
)
def test_runtime_artifact_ref_validation_matches_schema_pattern(artifact_ref: str) -> None:
    with pytest.raises(inventory_cli.InventoryArtifactError):
        inventory_cli._validate_artifact_ref(artifact_ref)


def test_inventory_cli_has_no_action_imports_or_write_delete_calls() -> None:
    source = Path(inventory_cli.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    assert "scripts.orchestration.creative_code_pr_promotion" not in imports
    assert "subprocess" not in imports
    assert "requests" not in imports
    assert "httpx" not in imports

    forbidden_calls = {"unlink", "write_text", "mkdir", "rmtree"}
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert called.isdisjoint(forbidden_calls)
