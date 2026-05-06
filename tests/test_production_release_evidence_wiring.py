from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from scripts.ci import check_release_control_plane
from scripts.release import build_equivalence
from scripts.release import release_manifest
from scripts.release import reviewer_packet_hashes

REPO_ROOT = Path(__file__).resolve().parents[1]
CD_WORKFLOW_PATH = REPO_ROOT / ".github/workflows/cd.yml"
TEST_GIT_SHA = "git-sha-for-production-release-evidence-wiring-tests"
OCI_DIGEST = "sha256:" + ("a" * 64)
PROVENANCE_DIGEST = "sha256:" + ("b" * 64)
ARTIFACT_DIGEST = "sha256:" + ("e" * 64)


def _load_cd_workflow() -> dict[str, object]:
    return yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))


def _job(workflow: dict[str, object], name: str) -> dict[str, object]:
    return workflow["jobs"][name]  # type: ignore[index]


def _steps(job: dict[str, object]) -> list[dict[str, object]]:
    return job["steps"]  # type: ignore[index]


def _step_by_name(job: dict[str, object], name: str) -> dict[str, object]:
    for step in _steps(job):
        if step.get("name") == name:
            return step
    raise AssertionError(f"Step {name!r} not found")


def _step_run(job: dict[str, object], name: str) -> str:
    return str(_step_by_name(job, name)["run"])


def _write_metadata_pack(repo_root: Path) -> None:
    notes_path = repo_root / "ios/fastlane/metadata/review_information/notes.txt"
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text("Reviewer note\n", encoding="utf-8")

    privacy_path = repo_root / "ios/fastlane/app_privacy_details.json"
    privacy_path.parent.mkdir(parents=True, exist_ok=True)
    privacy_path.write_text('[{"data_protections":["DATA_NOT_COLLECTED"]}]\n', encoding="utf-8")

    for locale in reviewer_packet_hashes.REQUIRED_LOCALES:
        locale_dir = repo_root / "ios/fastlane/metadata" / locale
        locale_dir.mkdir(parents=True, exist_ok=True)
        for filename in reviewer_packet_hashes.REQUIRED_METADATA_FILES:
            (locale_dir / filename).write_text(f"{locale}:{filename}\n", encoding="utf-8")


def _rag_payload(*, git_sha: str = TEST_GIT_SHA) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "release-rag-gate-result.v1",
        "hash_algorithm": "sha256",
        "canonicalization": release_manifest.CANONICALIZATION,
        "eval_artifact_hash": "c" * 64,
        "experiment_id": "production-wiring-test",
        "timestamp": "2026-05-06T00:00:00Z",
        "release_decision": "PASS",
        "gate_checks": {"answer_precision_min": True},
        "threshold_results": [],
        "strict_violations": [],
        "runtime_warnings": [],
        "dataset_path_used": "tests/fixtures/rag.jsonl",
        "dataset_fallback_used": False,
        "sample_size": 1,
        "git_sha": git_sha,
        "retriever_mode": "local_tfidf",
        "generator_mode": "extractive_stub",
        "small_fixture_metric_gates_advisory": False,
        "source_artifacts": [
            {
                "kind": "metrics_summary",
                "path": "artifacts/rag_eval/production-wiring-test/metrics_summary.json",
                "hash": "d" * 64,
            }
        ],
    }
    payload["rag_gate_result_hash"] = release_manifest.sha256_lower_hex(
        release_manifest.canonical_json_bytes(payload)
    )
    return payload


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _build_evidence(
    tmp_path: Path,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    _write_metadata_pack(tmp_path)
    rag_payload = _rag_payload()
    rag_path = tmp_path / "artifacts/rag_eval/production-wiring-test/rag_gate_result.json"
    _write_json(rag_path, rag_payload)
    manifest_payload = release_manifest.build_manifest_payload(
        repo_root=tmp_path,
        git_sha=TEST_GIT_SHA,
        ios_build_number="100",
        marketing_version="1.0",
        bundle_id="app.pulseplate.PulsePlate",
        rag_gate_result_path=rag_path,
        sbom_digest=OCI_DIGEST,
        provenance_digest=PROVENANCE_DIGEST,
        attestation_status="VERIFIED",
    )
    identity_payload = {
        "schema_version": "release-build-identity.v1",
        "hash_algorithm": "sha256",
        "canonicalization": release_manifest.CANONICALIZATION,
        "build_identity": manifest_payload["build_identity"],
        "artifact_digest": ARTIFACT_DIGEST,
        "release_manifest_hash": manifest_payload["release_manifest_hash"],
        "reviewer_identity": manifest_payload["reviewer_identity"],
        "ml_identity": manifest_payload["ml_identity"],
        "supply_chain_identity": manifest_payload["supply_chain_identity"],
    }
    build_payload = build_equivalence.build_equivalence_decision(
        review_payload=identity_payload,
        production_payload=identity_payload,
        manifest_payload=manifest_payload,
    )
    return manifest_payload, rag_payload, build_payload


def _write_evidence(
    tmp_path: Path,
    *,
    manifest_payload: dict[str, object] | None = None,
    rag_payload: dict[str, object] | None = None,
    build_payload: dict[str, object] | None = None,
) -> tuple[Path, Path, Path]:
    if manifest_payload is None or rag_payload is None or build_payload is None:
        manifest_payload, rag_payload, build_payload = _build_evidence(tmp_path)
    evidence_dir = tmp_path / "release-control-plane"
    manifest_path = evidence_dir / "release_manifest.json"
    rag_path = evidence_dir / "rag_gate_result.json"
    build_path = evidence_dir / "build_equivalence_result.json"
    _write_json(manifest_path, manifest_payload)
    _write_json(rag_path, rag_payload)
    _write_json(build_path, build_payload)
    return manifest_path, rag_path, build_path


def test_production_tag_workflow_includes_release_control_plane_evidence_gate() -> None:
    workflow = _load_cd_workflow()
    production_job = _job(workflow, "release-control-plane-production-evidence")
    download_script = _step_run(
        production_job,
        "Download production release-control-plane evidence artifact",
    )
    validate_script = _step_run(
        production_job, "Validate production release-control-plane evidence"
    )

    assert production_job["if"] == (
        "startsWith(github.ref, 'refs/tags/v') && "
        "needs.production-deploy-config.outputs.should_deploy == 'true'"
    )
    assert production_job["needs"] == ["build-production", "production-deploy-config"]
    assert "RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID" in download_script
    assert "RELEASE_CONTROL_PLANE_EVIDENCE_ARTIFACT_NAME" in download_script
    assert 'gh run download "$RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID"' in download_script
    assert '--name "$RELEASE_CONTROL_PLANE_EVIDENCE_ARTIFACT_NAME"' in download_script
    assert "scripts/ci/check_release_control_plane.py" in validate_script
    assert "--release-manifest" in validate_script
    assert "--rag-gate-result" in validate_script
    assert "--build-equivalence" in validate_script
    assert 'git rev-parse "${GITHUB_REF#refs/tags/}^{commit}"' in validate_script
    assert "build_identity.git_sha" in validate_script


def test_production_deploy_jobs_depend_on_release_control_plane_gate() -> None:
    workflow = _load_cd_workflow()
    expected_gate = "release-control-plane-production-evidence"

    for job_name in ("deploy-production", "deploy-production-self-hosted"):
        assert expected_gate in _job(workflow, job_name)["needs"]


def test_pr_and_main_fixture_path_is_not_used_on_production_tags() -> None:
    workflow = _load_cd_workflow()
    fixture_job = _job(workflow, "release-control-plane-fixture-gate")
    production_job_text = json.dumps(
        _job(workflow, "release-control-plane-production-evidence"),
        sort_keys=True,
    )

    assert fixture_job["if"] == "github.ref == 'refs/heads/main'"
    assert "release-control-plane-fixture" not in production_job_text
    assert "tests/fixtures" not in production_job_text
    assert "fixture_root" not in production_job_text


def test_production_path_does_not_require_app_store_secrets_or_upload_behavior() -> None:
    workflow = _load_cd_workflow()
    production_job_text = json.dumps(
        _job(workflow, "release-control-plane-production-evidence"),
        sort_keys=True,
    )
    forbidden_terms = (
        "APP_STORE",
        "APPSTORE",
        "ASC_",
        "FASTLANE",
        "MATCH_PASSWORD",
        "app store connect",
    )

    assert "secrets.GITHUB_TOKEN" in production_job_text
    assert not any(term in production_job_text for term in forbidden_terms)
    assert "fastlane" not in production_job_text.lower()
    assert "upload_to_app_store" not in production_job_text.lower()


def test_release_control_plane_gate_uploads_json_and_markdown_artifacts() -> None:
    workflow = _load_cd_workflow()
    production_job = _job(workflow, "release-control-plane-production-evidence")
    upload_step = _step_by_name(
        production_job, "Upload production release-control-plane gate artifact"
    )
    summary_script = _step_run(
        production_job, "Publish production release-control-plane gate summary"
    )

    assert upload_step["if"] == "${{ always() }}"
    assert upload_step["with"]["name"] == "release-control-plane-ci-gate-cd-production"
    assert "release_control_plane_ci_gate.json" in upload_step["with"]["path"]
    assert "release_control_plane_ci_gate.md" in upload_step["with"]["path"]
    assert "release_control_plane_ci_gate.md" in summary_script


def test_production_deploy_config_requires_evidence_variables_when_deploy_is_active() -> None:
    workflow = _load_cd_workflow()
    config_job = _job(workflow, "production-deploy-config")
    resolve_script = _step_run(config_job, "Resolve production deploy configuration")

    assert "RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID" in resolve_script
    assert "RELEASE_CONTROL_PLANE_EVIDENCE_ARTIFACT_NAME" in resolve_script
    assert "is required when production deploy is active" in resolve_script
    assert (
        config_job["outputs"]["evidence_run_id"] == "${{ steps.resolve.outputs.evidence_run_id }}"
    )
    assert (
        config_job["outputs"]["evidence_artifact_name"]
        == "${{ steps.resolve.outputs.evidence_artifact_name }}"
    )


def test_missing_release_control_plane_evidence_blocks(tmp_path: Path) -> None:
    manifest_path, rag_path, build_path = _write_evidence(tmp_path)
    manifest_path.unlink()
    rag_path.unlink()
    build_path.unlink()

    decision = check_release_control_plane.check_release_control_plane_files(
        release_manifest_path=manifest_path,
        rag_gate_result_path=rag_path,
        build_equivalence_path=build_path,
    )

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == [
        "missing_release_manifest",
        "missing_rag_gate_result",
        "missing_build_equivalence",
    ]


def test_invalid_artifact_paths_block(tmp_path: Path) -> None:
    manifest_payload, rag_payload, build_payload = _build_evidence(tmp_path)
    rag_payload["source_artifacts"] = [
        {
            "kind": "metrics_summary",
            "path": "artifacts/../leak.json",
            "hash": "d" * 64,
        }
    ]
    rag_payload["rag_gate_result_hash"] = release_manifest.sha256_lower_hex(
        release_manifest.canonical_json_bytes(
            {key: value for key, value in rag_payload.items() if key != "rag_gate_result_hash"}
        )
    )
    manifest_path, rag_path, build_path = _write_evidence(
        tmp_path,
        manifest_payload=manifest_payload,
        rag_payload=rag_payload,
        build_payload=build_payload,
    )

    decision = check_release_control_plane.check_release_control_plane_files(
        release_manifest_path=manifest_path,
        rag_gate_result_path=rag_path,
        build_equivalence_path=build_path,
    )

    assert decision["decision"] == "BLOCK"
    assert "evidence_path_outside_allowed_artifacts" in decision["reason_codes"]


def test_production_job_rejects_evidence_for_different_tag_commit() -> None:
    workflow = _load_cd_workflow()
    production_job = _job(workflow, "release-control-plane-production-evidence")
    checkout_step = _step_by_name(production_job, "Checkout")
    validate_script = _step_run(
        production_job, "Validate production release-control-plane evidence"
    )

    assert checkout_step["with"]["fetch-depth"] == 0
    assert 'tag_commit="$(git rev-parse "${GITHUB_REF#refs/tags/}^{commit}")"' in validate_script
    assert 'if [ "$manifest_git_sha" != "$tag_commit" ]; then' in validate_script
    assert "Release manifest git SHA does not match production tag commit" in validate_script
    assert "exit 1" in validate_script


def test_evidence_git_sha_mismatch_blocks(tmp_path: Path) -> None:
    manifest_payload, _, build_payload = _build_evidence(tmp_path)
    rag_payload = _rag_payload(git_sha="different-git-sha")
    manifest_path, rag_path, build_path = _write_evidence(
        tmp_path,
        manifest_payload=manifest_payload,
        rag_payload=rag_payload,
        build_payload=build_payload,
    )

    decision = check_release_control_plane.check_release_control_plane_files(
        release_manifest_path=manifest_path,
        rag_gate_result_path=rag_path,
        build_equivalence_path=build_path,
    )

    assert decision["decision"] == "BLOCK"
    assert "git_sha_mismatch" in decision["reason_codes"]


def test_ledger_marks_pr5_merged_and_pr6_active() -> None:
    ledger = (REPO_ROOT / "docs/roadmap/BACKLOG_LEDGER.md").read_text(encoding="utf-8")

    assert "PR-5 merged in PR #1682 on 2026-05-06" in ledger
    assert (
        "PR-6 is active on branch `release/release-control-plane-pr6-production-artifact-wiring`"
        in ledger
    )
    assert (
        "Future protected upload automation and App Store Connect execution remain out of scope"
        in ledger
    )
    assert "full App Store readiness is not complete" in ledger


def test_no_runtime_api_ios_or_openapi_files_are_in_pr6_scope() -> None:
    scope_docs = "\n".join(
        (
            (REPO_ROOT / "docs/release/PRODUCTION_RELEASE_EVIDENCE_WIRING.md").read_text(
                encoding="utf-8"
            ),
            (REPO_ROOT / "docs/release/RELEASE_CONTROL_PLANE_EPIC.md").read_text(encoding="utf-8"),
        )
    )

    assert re.search(r"does not .*runtime", scope_docs, flags=re.IGNORECASE | re.DOTALL)
    assert "OpenAPI" in scope_docs
    assert "Fastlane" in scope_docs
