from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import (
    creative_code_patch_builder,
    creative_code_patch_workspace,
    creative_spec_patch_admission as admission_cli,
    creative_specification_skeptic_review_contract as review_contract,
)
from scripts.orchestration.creative_code_patch_contract import (
    source_bundle_fingerprint,
    validate_creative_code_patch_build_request,
)
from scripts.orchestration.creative_code_specification import (
    read_creative_code_specification_bundle,
)
from scripts.orchestration.creative_spec_patch_admission_contract import (
    HUMAN_ADMISSION_ARTIFACT_TYPE,
    HUMAN_DECISION,
    POLICY_VERSION,
    CreativeSpecPatchAdmissionError,
    default_human_admission_authority,
    validate_creative_spec_patch_admission,
    validate_human_admission,
)
from scripts.orchestration.creative_specification_skeptic_review_contract import (
    FINALIZE_RECEIPT_ARTIFACT_TYPE,
    default_finalize_receipt_authority,
    validate_finalize_receipt,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_BUNDLE = REPO_ROOT / "docs/orchestration/contracts/creative_code_specification.v1.json"
HUMAN_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_spec_patch_human_admission.v1.schema.json"
)
ADMISSION_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_spec_patch_admission.v1.schema.json"
)


def _git(repo: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    git_binary = shutil.which("git")
    if not git_binary:
        raise AssertionError("git binary is required for creative-spec admission tests.")
    if git_binary.endswith("/usr/libexec/git-core/git"):
        git_binary = "/usr/bin/git"
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.run(
        [git_binary, *args],
        cwd=str(repo),
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        check=True,
    )


def _init_patch_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    (repo / "core" / "rag").mkdir(parents=True)
    (repo / "docs" / "orchestration").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / ".gitignore").write_text("artifacts/\n", encoding="utf-8")
    (repo / "core" / "rag" / "orchestration.py").write_text(
        "def value() -> int:\n    return 1\n",
        encoding="utf-8",
    )
    (repo / "docs" / "orchestration" / "GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md").write_text(
        "# Contract\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_creative_code_contract.py").write_text(
        "def test_placeholder() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "update-ref", "refs/remotes/origin/main", base_sha)
    return repo, base_sha


def _patch_modules_to_repo(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    creative_root = repo / "artifacts" / "orchestration" / "creative_code"
    monkeypatch.setattr(creative_code_patch_workspace, "REPO_ROOT", repo)
    monkeypatch.setattr(
        creative_code_patch_workspace, "ARTIFACT_ROOT", creative_root / "patch_runs"
    )
    monkeypatch.setattr(creative_code_patch_builder, "REPO_ROOT", repo)
    monkeypatch.setattr(admission_cli, "REPO_ROOT", repo)
    monkeypatch.setattr(admission_cli, "CREATIVE_CODE_ROOT", creative_root)
    monkeypatch.setattr(admission_cli, "PATCH_ADMISSION_ROOT", creative_root / "patch_admission")


def _reference_bundle() -> dict[str, Any]:
    return read_creative_code_specification_bundle(REFERENCE_BUNDLE)


def _selected_variant(bundle: dict[str, Any]) -> dict[str, Any]:
    selected_id = bundle["synthesis"]["selected_variant_id"]
    selected_fingerprint = bundle["synthesis"]["selected_variant_fingerprint"]
    for variant in bundle["variants"]:
        if (
            variant["variant_id"] == selected_id
            and variant["variant_fingerprint"] == selected_fingerprint
        ):
            return dict(variant)
    raise AssertionError("reference bundle must contain selected variant")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _refresh_receipt_identity(receipt: dict[str, Any]) -> dict[str, Any]:
    receipt["finalize_id"] = "pending"
    receipt["idempotency_key"] = "pending"
    review_contract._set_identity(
        receipt,
        id_key="finalize_id",
        asset_type=FINALIZE_RECEIPT_ARTIFACT_TYPE,
    )
    return receipt


def _finalize_receipt(bundle: dict[str, Any], *, bundle_ref: str) -> dict[str, Any]:
    selected = _selected_variant(bundle)
    rejected_variant_ids = {record["variant_id"] for record in bundle["rejection_index"]["records"]}
    reviewed_dir_ref = str(Path(bundle_ref).parent)
    receipt = {
        "schema_version": "1.0",
        "artifact_type": FINALIZE_RECEIPT_ARTIFACT_TYPE,
        "finalize_id": "pending",
        "idempotency_key": "pending",
        "policy_version": "creative-specification-skeptic-review-finalize-v1",
        "source_attachment_id": "creative-spec-patch-admission-test-attachment",
        "source_attachment_fingerprint": "sha256:" + ("1" * 64),
        "source_attachment_ref": f"{reviewed_dir_ref}/skeptic_review_attachment.json",
        "reviewed_run_dir_ref": reviewed_dir_ref,
        "bundle_ref": bundle_ref,
        "bundle_id": bundle["bundle_id"],
        "bundle_fingerprint": source_bundle_fingerprint(bundle),
        "bundle_idempotency_key": bundle["idempotency_key"],
        "selected_variant_id": selected["variant_id"],
        "synthesis_status": "selected",
        "next_allowed_action": "human_review_for_patch_builder",
        "counts": {
            "variant_count": len(bundle["variants"]),
            "review_count": len(bundle["skeptic_reviews"]),
            "selected_variant_count": 1,
            "rejected_variant_count": len(rejected_variant_ids),
            "unresolved_blocker_count": len(bundle["synthesis"]["unresolved_blockers"]),
            "rejection_record_count": len(bundle["rejection_index"]["records"]),
        },
        "authority": default_finalize_receipt_authority(),
        "sanitized": True,
    }
    return validate_finalize_receipt(_refresh_receipt_identity(receipt))


def _human_admission(bundle: dict[str, Any]) -> dict[str, Any]:
    selected = _selected_variant(bundle)
    return {
        "schema_version": "1.0",
        "artifact_type": HUMAN_ADMISSION_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "decision": HUMAN_DECISION,
        "approval_ref": "creative-spec-patch-admission-test",
        "approved_by": "operator",
        "approved_at_utc": "2026-07-05T00:00:00Z",
        "approved_source_bundle_id": bundle["bundle_id"],
        "approved_source_bundle_fingerprint": source_bundle_fingerprint(bundle),
        "approved_selected_variant_id": selected["variant_id"],
        "approved_selected_variant_fingerprint": selected["variant_fingerprint"],
        "allowed_existing_paths": ["core/rag/orchestration.py"],
        "allowed_new_paths": [],
        "oracle_commands": ["pytest -q tests/test_creative_code_contract.py"],
        "metrics": [
            "request preserves selected creative spec binding",
            "builder prepare leaves candidate patch absent",
        ],
        "budgets": {
            "generation_attempts": 1,
            "generation_timeout_seconds": 60,
            "evaluation_timeout_seconds": 60,
            "max_changed_files": 3,
            "max_diff_lines": 200,
            "max_patch_bytes": 20000,
        },
        "authority": default_human_admission_authority(),
        "sanitized": True,
    }


def _write_inputs(repo: Path) -> tuple[dict[str, Any], Path, Path, Path]:
    bundle = _reference_bundle()
    reviewed_dir = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "spec_bridge"
        / "admission-test"
        / "spec_finalize_reviewed"
    )
    bundle_path = reviewed_dir / "creative_code_specification_bundle.json"
    bundle_ref = bundle_path.relative_to(repo).as_posix()
    receipt = _finalize_receipt(bundle, bundle_ref=bundle_ref)
    receipt_path = reviewed_dir / "finalize_receipt.json"
    human_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "patch_admission"
        / "operator-input"
        / "human_admission.json"
    )
    _write_json(bundle_path, bundle)
    _write_json(receipt_path, receipt)
    _write_json(human_path, _human_admission(bundle))
    return bundle, bundle_path, receipt_path, human_path


def _output_dir(repo: Path, name: str = "admission-run") -> Path:
    return repo / "artifacts" / "orchestration" / "creative_code" / "patch_admission" / name


def test_build_and_prepare_happy_path_no_generate_evaluate_or_candidate_patch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    bundle, _bundle_path, receipt_path, human_path = _write_inputs(repo)
    output_dir = _output_dir(repo)
    run_id = "admission-prepare-test"

    def fail_generate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("generate must not be called")

    def fail_evaluate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("evaluate must not be called")

    monkeypatch.setattr(creative_code_patch_builder, "generate", fail_generate)
    monkeypatch.setattr(creative_code_patch_builder, "evaluate", fail_evaluate)

    assert (
        admission_cli.main(
            [
                "build-and-prepare",
                "--finalize-receipt",
                str(receipt_path),
                "--bundle",
                str(_bundle_path),
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
    captured = capsys.readouterr()
    assert admission_cli.BUILD_SUCCESS_OUTPUT not in captured.out
    assert admission_cli.PREPARE_SUCCESS_OUTPUT in captured.out

    admission_path = output_dir / admission_cli.ADMISSION_FILENAME
    request_path = output_dir / admission_cli.REQUEST_FILENAME
    admission = validate_creative_spec_patch_admission(json.loads(admission_path.read_text()))
    request = json.loads(request_path.read_text())
    assert validate_creative_code_patch_build_request(request, source_bundle=bundle) == request
    assert admission["builder_prepare"]["prepared"] is True
    assert admission["builder_prepare"]["candidate_patch_path_present"] is False
    assert admission["builder_prepare"]["candidate_patch_generated"] is False
    assert admission["builder_prepare"]["candidate_patch_evaluated"] is False
    assert admission["executed_effects"]["codex_exec_called"] is False

    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=False)
    assert (run_dir / creative_code_patch_builder.REQUEST_FILE).is_file()
    assert (run_dir / creative_code_patch_builder.SOURCE_BUNDLE_FILE).is_file()
    assert (run_dir / creative_code_patch_builder.SELECTED_VARIANT_FILE).is_file()
    assert (run_dir / creative_code_patch_builder.STATE_FILE).is_file()
    assert not (run_dir / creative_code_patch_builder.CANDIDATE_PATCH_FILE).exists()
    assert not (run_dir / creative_code_patch_builder.RESULT_FILE).exists()

    assert admission_cli.main(["summarize", "--admission", str(admission_path)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["authority_boundary"] == admission_cli.SUMMARY_AUTHORITY_BOUNDARY
    assert summary["candidate_patch_generated"] is False
    assert summary["candidate_patch_path_present"] is False

    creative_code_patch_workspace.cleanup_run_dir(run_id)
    assert not run_dir.exists()


def test_admission_validator_rejects_prepare_proof_parity_regressions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    _bundle, bundle_path, receipt_path, human_path = _write_inputs(repo)
    output_dir = _output_dir(repo, "validator-negatives")

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
    admission = json.loads((output_dir / admission_cli.ADMISSION_FILENAME).read_text())

    prepared_with_missing_file = json.loads(json.dumps(admission))
    prepared_with_missing_file["builder_prepare"].update(
        {
            "prepared": True,
            "run_id": "validator-negative-run",
            "state_fingerprint": "sha256:" + ("2" * 64),
            "request_file_present": True,
            "source_bundle_file_present": False,
            "selected_variant_file_present": True,
            "state_file_present": True,
        }
    )
    prepared_with_missing_file["executed_effects"]["builder_prepared"] = True
    with pytest.raises(CreativeSpecPatchAdmissionError, match="source_bundle_file_present"):
        validate_creative_spec_patch_admission(prepared_with_missing_file)

    unprepared_with_prepare_proof = json.loads(json.dumps(admission))
    unprepared_with_prepare_proof["builder_prepare"]["run_id"] = "validator-negative-run"
    unprepared_with_prepare_proof["builder_prepare"]["state_fingerprint"] = "sha256:" + ("3" * 64)
    with pytest.raises(CreativeSpecPatchAdmissionError, match="must not include run_id"):
        validate_creative_spec_patch_admission(unprepared_with_prepare_proof)

    effects_disagree = json.loads(json.dumps(admission))
    effects_disagree["executed_effects"]["builder_prepared"] = True
    with pytest.raises(CreativeSpecPatchAdmissionError, match="disagree"):
        validate_creative_spec_patch_admission(effects_disagree)


def test_build_request_rejects_receipt_bundle_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    _bundle, bundle_path, receipt_path, human_path = _write_inputs(repo)
    receipt = json.loads(receipt_path.read_text())
    receipt["bundle_fingerprint"] = "sha256:" + ("0" * 64)
    _write_json(receipt_path, _refresh_receipt_identity(receipt))

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
                str(_output_dir(repo, "receipt-mismatch")),
            ]
        )
        == 1
    )
    assert "bundle_fingerprint" in capsys.readouterr().err


def test_human_admission_selected_variant_mismatch_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    _bundle, bundle_path, receipt_path, human_path = _write_inputs(repo)
    human = json.loads(human_path.read_text())
    human["approved_selected_variant_id"] = "creative-code-pr0-reference:spec-2"
    _write_json(human_path, human)

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
                str(_output_dir(repo, "human-mismatch")),
            ]
        )
        == 1
    )
    assert "human admission selected variant id" in capsys.readouterr().err


def test_stale_origin_main_and_dirty_shared_worktree_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    _bundle, bundle_path, receipt_path, human_path = _write_inputs(repo)

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
                "b" * 40,
                "--output-dir",
                str(_output_dir(repo, "stale-base")),
            ]
        )
        == 1
    )
    assert "base_commit_sha must match current origin/main" in capsys.readouterr().err

    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
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
                str(_output_dir(repo, "dirty-tree")),
            ]
        )
        == 1
    )
    assert "shared worktree must be clean" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (
            lambda human: human["authority"].update({"run_patch_builder_generate": True}),
            "run_patch_builder_generate",
        ),
        (lambda human: human.update({"oracle_commands": []}), "oracle_commands"),
        (lambda human: human.update({"metrics": ["diff --git a/file b/file"]}), "unsafe text"),
        (lambda human: human["budgets"].update({"max_changed_files": 6}), "max_changed_files"),
        (
            lambda human: human["budgets"].update({"generation_attempts": True}),
            "generation_attempts",
        ),
    ],
)
def test_human_admission_rejects_authority_strings_empty_and_budget_bounds(
    mutator: Any,
    match: str,
) -> None:
    human = _human_admission(_reference_bundle())
    mutator(human)

    with pytest.raises(CreativeSpecPatchAdmissionError, match=match):
        validate_human_admission(human)


def test_allowed_path_must_stay_inside_selected_variant_surface(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    _bundle, bundle_path, receipt_path, human_path = _write_inputs(repo)
    human = json.loads(human_path.read_text())
    human["allowed_existing_paths"] = ["core/rag/other.py"]
    _write_json(human_path, human)

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
                str(_output_dir(repo, "bad-path")),
            ]
        )
        == 1
    )
    assert "selected variant target paths" in capsys.readouterr().err


def test_prepare_builder_rejects_stale_base_after_request_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    _bundle, bundle_path, receipt_path, human_path = _write_inputs(repo)
    output_dir = _output_dir(repo, "stale-before-prepare")

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
    (repo / "core" / "rag" / "second.py").write_text("value = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "advance main")
    new_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "update-ref", "refs/remotes/origin/main", new_sha)

    assert (
        admission_cli.main(
            [
                "prepare-builder",
                "--admission",
                str(output_dir / admission_cli.ADMISSION_FILENAME),
                "--run-id",
                "stale-prepare",
            ]
        )
        == 1
    )
    assert "base_commit_sha must match current origin/main" in capsys.readouterr().err


def test_prepare_builder_cleans_new_run_dir_on_prepare_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    _bundle, bundle_path, receipt_path, human_path = _write_inputs(repo)
    output_dir = _output_dir(repo, "cleanup")
    run_id = "cleanup-run"

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

    def fail_prepare(*args: Any, **kwargs: Any) -> dict[str, Any]:
        run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=True)
        (run_dir / "partial.json").write_text("{}", encoding="utf-8")
        raise creative_code_patch_builder.CreativeCodePatchBuilderError("injected prepare failure")

    monkeypatch.setattr(creative_code_patch_builder, "prepare", fail_prepare)

    assert (
        admission_cli.main(
            [
                "prepare-builder",
                "--admission",
                str(output_dir / admission_cli.ADMISSION_FILENAME),
                "--run-id",
                run_id,
            ]
        )
        == 1
    )
    assert "injected prepare failure" in capsys.readouterr().err
    with pytest.raises(creative_code_patch_workspace.CreativeCodePatchWorkspaceError):
        creative_code_patch_workspace.resolve_run_dir(run_id, create=False)


def test_schemas_closed_and_cli_has_no_generate_or_evaluate_commands() -> None:
    human_schema = json.loads(HUMAN_SCHEMA.read_text(encoding="utf-8"))
    admission_schema = json.loads(ADMISSION_SCHEMA.read_text(encoding="utf-8"))

    assert human_schema["additionalProperties"] is False
    assert admission_schema["additionalProperties"] is False
    assert human_schema["$defs"]["authority"]["additionalProperties"] is False
    assert (
        admission_schema["$defs"]["authority"]["properties"]["run_patch_builder_generate"]["const"]
        is False
    )
    assert (
        admission_schema["$defs"]["authority"]["properties"]["run_patch_builder_evaluate"]["const"]
        is False
    )
    assert (
        admission_schema["$defs"]["builder_prepare"]["properties"]["candidate_patch_generated"][
            "const"
        ]
        is False
    )
    prepared_rules = admission_schema["$defs"]["builder_prepare"]["allOf"]
    prepared_then = prepared_rules[0]["then"]["properties"]
    unprepared_then = prepared_rules[1]["then"]["properties"]
    for key in (
        "request_file_present",
        "source_bundle_file_present",
        "selected_variant_file_present",
        "state_file_present",
    ):
        assert prepared_then[key]["const"] is True
        assert unprepared_then[key]["const"] is False
    assert prepared_then["run_id"]["$ref"] == "#/$defs/safe_id"
    assert prepared_then["state_fingerprint"]["$ref"] == "#/$defs/sha256"
    assert unprepared_then["run_id"]["type"] == "null"
    assert unprepared_then["state_fingerprint"]["type"] == "null"

    admission_prepare_effect_rules = admission_schema["allOf"]
    assert (
        admission_prepare_effect_rules[0]["then"]["properties"]["executed_effects"]["properties"][
            "builder_prepared"
        ]["const"]
        is True
    )
    assert (
        admission_prepare_effect_rules[1]["then"]["properties"]["executed_effects"]["properties"][
            "builder_prepared"
        ]["const"]
        is False
    )

    with pytest.raises(SystemExit):
        admission_cli._parse_args(["generate"])
    with pytest.raises(SystemExit):
        admission_cli._parse_args(["evaluate"])
