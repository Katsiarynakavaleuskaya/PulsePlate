from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.release import evidence_source, release_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/release-manifest-evidence.yml"
RAG_WORKFLOW_PATH = REPO_ROOT / ".github/workflows/rag-release-gates.yml"
BUILD_WORKFLOW_PATH = REPO_ROOT / ".github/workflows/build.yml"
LEDGER_PATH = REPO_ROOT / "docs/roadmap/BACKLOG_LEDGER.md"


def _load_workflow(path: Path = WORKFLOW_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _workflow_on(workflow: dict[str, Any]) -> dict[str, Any]:
    return workflow.get("on") or workflow[True]


def _job(workflow: dict[str, Any]) -> dict[str, Any]:
    return workflow["jobs"]["publish-release-manifest-evidence"]


def _step_by_name(job: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [step for step in job["steps"] if step.get("name") == name]
    assert len(matches) == 1
    return matches[0]


def _run_script() -> str:
    return str(
        _step_by_name(_job(_load_workflow()), "Generate governed release manifest evidence")["run"]
    )


def _helper_text() -> str:
    return (REPO_ROOT / "scripts/release/evidence_source.py").read_text(encoding="utf-8")


def _rag_payload(tmp_path: Path) -> Path:
    payload: dict[str, Any] = {
        "schema_version": release_manifest.RAG_GATE_SCHEMA_VERSION,
        "hash_algorithm": release_manifest.HASH_ALGORITHM,
        "canonicalization": release_manifest.CANONICALIZATION,
        "eval_artifact_hash": "b" * 64,
        "release_decision": "PASS",
        "dataset_fallback_used": False,
        "small_fixture_metric_gates_advisory": False,
        "git_sha": "a" * 40,
        "source_artifacts": [
            {"kind": "eval_input", "path": "data/evals/release.jsonl", "hash": "c" * 64}
        ],
    }
    payload["rag_gate_result_hash"] = release_manifest.sha256_lower_hex(
        release_manifest.canonical_json_bytes(payload)
    )
    path = tmp_path / "rag_gate_result.json"
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_workflow_exists_and_is_dispatch_only() -> None:
    workflow = _load_workflow()

    assert WORKFLOW_PATH.is_file()
    assert workflow["name"] == "Release Manifest Evidence"
    assert set(_workflow_on(workflow)) == {"workflow_dispatch"}
    assert "pull_request" not in _workflow_on(workflow)
    assert "push" not in _workflow_on(workflow)
    assert "schedule" not in _workflow_on(workflow)


def test_workflow_permissions_environment_and_inputs_are_bounded() -> None:
    workflow = _load_workflow()
    inputs = _workflow_on(workflow)["workflow_dispatch"]["inputs"]
    expected_inputs = {
        "git_sha",
        "ios_build_number",
        "marketing_version",
        "bundle_id",
        "sbom_digest",
        "provenance_digest",
        "attestation_status",
        "supply_chain_source",
        "rag_gate_result_source",
        "evidence_artifact_name",
    }

    assert set(inputs) == expected_inputs
    assert len(inputs) == 10
    assert all(inputs[name]["required"] is True for name in expected_inputs)
    assert inputs["attestation_status"]["options"] == ["VERIFIED", "FAILED", "MISSING", "PENDING"]
    assert "run_id" in inputs["rag_gate_result_source"]["description"]
    assert "artifact_name" in inputs["rag_gate_result_source"]["description"]
    assert "path" in inputs["rag_gate_result_source"]["description"]
    assert "run_id" in inputs["supply_chain_source"]["description"]
    assert "artifact_name" in inputs["supply_chain_source"]["description"]
    assert (
        "path=release-control-plane-build-sources" in inputs["supply_chain_source"]["description"]
    )
    assert workflow["permissions"] == {"actions": "read", "contents": "read"}
    assert _job(workflow)["environment"]["name"] == "release-evidence"
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "id-token:" not in workflow_text
    assert "packages:" not in workflow_text


def test_workflow_validates_governed_rag_source_run_and_git_sha() -> None:
    script = _run_script()

    assert "scripts/release/evidence_source.py source-env" in script
    assert "--label rag_gate_result" in script
    assert "--expected-path rag_gate_result.json" in script
    assert "source-env" in script and "run_id, artifact_name, path" not in script
    assert "gh run view" in script
    assert "--json status,conclusion,headSha,event,workflowName,url" in script
    assert 'gh api "repos/${GITHUB_REPOSITORY}/actions/runs/${run_id}"' in script
    assert "validate_source_run" in script
    assert '[ "$run_status" != "completed" ]' in script
    assert '[ "$run_conclusion" != "success" ]' in script
    assert '[ "$run_event" != "workflow_dispatch" ]' in script
    assert '"RAG Release Gates" ".github/workflows/rag-release-gates.yml"' in script
    assert '"Docker Build and Push" ".github/workflows/build.yml"' in script
    assert "source run head SHA does not match git_sha" in script
    assert "Release Manifest Evidence workflow ref must match git_sha" in script
    assert "scripts/release/evidence_source.py rag-gate-result" in script
    assert "rag_gate_result.git_sha must match git_sha" in _helper_text()
    assert "scripts/release/evidence_source.py git-sha" in script


def test_workflow_rejects_fixture_sample_test_fallback_and_requires_pass() -> None:
    script = _run_script()

    helper = _helper_text()

    for token in ("fixture", "sample", "example", "placeholder", "fake", "fallback"):
        assert token in helper
    assert "FORBIDDEN_TEST_PATH_RE" in helper
    assert "test evidence path rejected" in helper
    assert "dataset_fallback_used must be false" in helper
    assert "small_fixture_metric_gates_advisory must be false" in helper
    assert "release_decision must be PASS" in helper
    assert "attestation_status must be VERIFIED" in script
    assert "rag_gate_result path escapes downloaded artifact" in script
    assert "Path(sys.argv[1]).resolve()" in script
    assert "scripts/release/evidence_source.py rag-gate-result" in script
    assert "artifacts/release_control_plane_sources" in script
    assert 'args.command == "artifact-name"' in helper


def test_workflow_requires_governed_supply_chain_sources() -> None:
    script = _run_script()
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "sbom_digest_source" not in workflow_text
    assert "provenance_digest_source" not in workflow_text
    assert "attestation_status_source" not in workflow_text
    assert "--label supply_chain" in script
    assert "--expected-path release-control-plane-build-sources" in script
    assert '"Docker Build and Push" ".github/workflows/build.yml"' in script
    assert 'gh run download "$supply_chain_run_id"' in script
    assert "fetch_text_source" in script
    assert "${supply_chain_source_path}/sbom_digest.txt" in script
    assert "${supply_chain_source_path}/provenance_digest.txt" in script
    assert "${supply_chain_source_path}/attestation_status.txt" in script
    assert "governed ${label} source does not match explicit input" in script
    assert "governed attestation status source must be VERIFIED" in script
    assert "path escapes downloaded artifact" in script


def test_workflow_generates_validates_and_uploads_stable_manifest_path() -> None:
    workflow = _load_workflow()
    script = _run_script()
    upload_step = _step_by_name(
        _job(workflow), "Upload governed release manifest evidence artifact"
    )
    summary_script = str(
        _step_by_name(_job(workflow), "Publish release manifest evidence summary")["run"]
    )

    assert "scripts/release/release_manifest.py generate" in script
    assert "--rag-gate-result" in script
    assert "--sbom-digest" in script
    assert "--provenance-digest" in script
    assert "--attestation-status" in script
    assert "scripts/release/release_manifest.py validate" in script
    assert (
        upload_step["with"]["path"]
        == "${{ runner.temp }}/release-manifest-evidence/release_manifest.json"
    )
    assert (
        upload_step["with"]["name"]
        == "${{ steps.generate-release-manifest-evidence.outputs.artifact_name }}"
    )
    assert "${{ inputs.evidence_artifact_name }}" not in upload_step["with"]["name"]
    assert upload_step["with"]["if-no-files-found"] == "error"
    assert 'echo "artifact_name=$EVIDENCE_ARTIFACT_NAME" >> "$GITHUB_OUTPUT"' in script
    assert "GITHUB_RUN_ID" in summary_script
    assert "release_manifest.json" in summary_script


def test_workflow_has_no_app_store_fastlane_or_runtime_surface() -> None:
    workflow_json = json.dumps(_load_workflow(), default=str).lower()
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8").lower()

    forbidden_terms = (
        "fastlane",
        "upload_to_app_store",
        "app-store-connect",
        "app_store_connect",
        "asc_",
        "match_password",
        "frontend/",
        "ios/",
        "openapi",
    )
    assert not any(term in workflow_json for term in forbidden_terms)
    assert ".github/workflows/rag-release-gates.yml" in workflow_text


def test_evidence_source_helper_rejects_malformed_source_and_unsafe_paths() -> None:
    valid = '{"run_id":"123","artifact_name":"rag-release-gates-weekly","path":"artifacts/rag/rag_gate_result.json"}'
    assert (
        evidence_source.validate_source_payload(valid, label="rag_gate_result")["run_id"] == "123"
    )
    assert (
        evidence_source.validate_source_payload(
            '{"run_id":"123","artifact_name":"latest-release-evidence","path":"latest/rag_gate_result.json"}',
            label="rag_gate_result",
        )["path"]
        == "latest/rag_gate_result.json"
    )
    canonical = (
        '{"run_id":"123","artifact_name":"rag-release-gates-weekly","path":"rag_gate_result.json"}'
    )
    assert (
        evidence_source.validate_source_payload(
            canonical,
            label="rag_gate_result",
            expected_path="rag_gate_result.json",
        )["path"]
        == "rag_gate_result.json"
    )

    invalid_payloads = [
        "{not json}",
        '{"run_id":"123","artifact_name":"ok","path":"../rag_gate_result.json"}',
        '{"run_id":"123","artifact_name":"ok","path":"/rag_gate_result.json"}',
        '{"run_id":"123","artifact_name":"ok","path":"a//rag_gate_result.json"}',
        '{"run_id":"123","artifact_name":"fixture","path":"rag_gate_result.json"}',
        '{"run_id":"abc","artifact_name":"ok","path":"rag_gate_result.json"}',
        '{"run_id":"123","artifact_name":"ok","path":"rag_gate_result.json","workflow_name":"RAG Release Gates"}',
    ]
    for raw_json in invalid_payloads:
        with pytest.raises(evidence_source.EvidenceSourceError):
            evidence_source.validate_source_payload(raw_json, label="rag_gate_result")
    with pytest.raises(evidence_source.EvidenceSourceError):
        evidence_source.validate_source_payload(
            valid,
            label="rag_gate_result",
            expected_path="rag_gate_result.json",
        )


def test_evidence_source_helper_requires_full_sha_and_non_placeholder_digests() -> None:
    assert evidence_source.validate_git_sha("A" * 40) == "a" * 40
    assert evidence_source.validate_oci_digest("sha256:" + "a1" * 32, label="digest")

    for value in ("deadbeef", "g" * 40):
        with pytest.raises(evidence_source.EvidenceSourceError):
            evidence_source.validate_git_sha(value)
    for value in ("sha256:" + "0" * 64, "a" * 64, "sha256:" + "A" * 64):
        with pytest.raises(evidence_source.EvidenceSourceError):
            evidence_source.validate_oci_digest(value, label="digest")


def test_release_manifest_source_validation_rejects_sample_test_paths_and_sha_mismatch(
    tmp_path: Path,
) -> None:
    rag_path = _rag_payload(tmp_path)
    rag_payload = json.loads(rag_path.read_text(encoding="utf-8"))
    rag_payload["source_artifacts"][0]["path"] = "data/evals/pulseplate_rag_eval_sample.jsonl"
    rag_path.write_text(json.dumps(rag_payload, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(evidence_source.EvidenceSourceError):
        evidence_source.validate_rag_gate_result_file(rag_path, expected_git_sha="a" * 40)

    rag_payload["source_artifacts"][0]["path"] = "tests/evals/release.jsonl"
    rag_path.write_text(json.dumps(rag_payload, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(evidence_source.EvidenceSourceError):
        evidence_source.validate_rag_gate_result_file(rag_path, expected_git_sha="a" * 40)

    for unsafe_path in ("../prod/release.jsonl", "/prod/release.jsonl", "data//release.jsonl"):
        rag_payload["source_artifacts"][0]["path"] = unsafe_path
        rag_path.write_text(json.dumps(rag_payload, sort_keys=True) + "\n", encoding="utf-8")
        with pytest.raises(evidence_source.EvidenceSourceError):
            evidence_source.validate_rag_gate_result_file(rag_path, expected_git_sha="a" * 40)

    rag_payload["source_artifacts"][0]["path"] = "data/evals/release.jsonl"
    rag_payload["git_sha"] = "b" * 40
    rag_path.write_text(json.dumps(rag_payload, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(evidence_source.EvidenceSourceError):
        evidence_source.validate_rag_gate_result_file(rag_path, expected_git_sha="a" * 40)

    rag_triggers = _workflow_on(_load_workflow(RAG_WORKFLOW_PATH))
    assert "workflow_dispatch" in rag_triggers
    assert "ci/release-control-plane-source-producers" in LEDGER_PATH.read_text(encoding="utf-8")


def test_docker_build_workflow_emits_governed_release_control_plane_sources() -> None:
    workflow_text = BUILD_WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = _load_workflow(BUILD_WORKFLOW_PATH)
    publish_job = workflow["jobs"]["publish"]
    publish_steps = workflow["jobs"]["publish"]["steps"]
    upload_step = next(
        step
        for step in publish_steps
        if step.get("name") == "Upload release-control-plane build digest sources"
    )

    assert "artifact-metadata" not in publish_job["permissions"]
    assert publish_job["permissions"]["attestations"] == "write"
    assert publish_job["permissions"]["id-token"] == "write"
    assert "id: docker-build-push" in workflow_text
    assert "Attest Docker image provenance" in workflow_text
    assert "Attest Docker image SBOM" in workflow_text
    assert "Verify Docker image attestations" in workflow_text
    assert "scripts/ci/check_docker_provenance_attestation.py" in workflow_text
    assert "docker-provenance-attestation-check.json" in workflow_text
    assert "docker-provenance-attestation-check.json" not in upload_step["with"]["path"]
    assert "docker-provenance-attestation-check.md" not in upload_step["with"]["path"]
    assert "Prepare release-control-plane build digest sources" in workflow_text
    for path in (
        "sbom_digest.txt",
        "provenance_digest.txt",
        "attestation_status.txt",
    ):
        assert path in workflow_text
        assert path in upload_step["with"]["path"]
    assert "review_artifact_digest.txt" not in upload_step["with"]["path"]
    assert "production_candidate_artifact_digest.txt" not in upload_step["with"]["path"]
    assert 'write_text("VERIFIED\\n", encoding="utf-8")' in workflow_text
    assert 'attestation_payload.get("passed") is not True' in workflow_text
    assert upload_step["with"]["name"] == "release-control-plane-build-sources"
    assert upload_step["with"]["if-no-files-found"] == "error"
