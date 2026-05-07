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


def _rag_payload(tmp_path: Path) -> Path:
    payload: dict[str, Any] = {
        "schema_version": release_manifest.RAG_GATE_SCHEMA_VERSION,
        "hash_algorithm": release_manifest.HASH_ALGORITHM,
        "canonicalization": release_manifest.CANONICALIZATION,
        "eval_artifact_hash": "b" * 64,
        "release_decision": "PASS",
        "dataset_fallback_used": False,
        "small_fixture_metric_gates_advisory": False,
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
        "rag_gate_result_source",
        "evidence_artifact_name",
    }

    assert set(inputs) == expected_inputs
    assert all(inputs[name]["required"] is True for name in expected_inputs)
    assert inputs["attestation_status"]["options"] == ["VERIFIED", "FAILED", "MISSING", "PENDING"]
    assert "run_id" in inputs["rag_gate_result_source"]["description"]
    assert "artifact_name" in inputs["rag_gate_result_source"]["description"]
    assert "path" in inputs["rag_gate_result_source"]["description"]
    assert workflow["permissions"] == {"actions": "read", "contents": "read"}
    assert _job(workflow)["environment"]["name"] == "release-evidence"
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "id-token:" not in workflow_text
    assert "packages:" not in workflow_text


def test_workflow_validates_governed_rag_source_run_and_git_sha() -> None:
    script = _run_script()

    assert "scripts/release/evidence_source.py source-env" in script
    assert "--label rag_gate_result" in script
    assert "source-env" in script and "run_id, artifact_name, path" not in script
    assert "gh run view" in script
    assert "--json status,conclusion,headSha,event,workflowName,url" in script
    assert 'gh api "repos/${GITHUB_REPOSITORY}/actions/runs/${RAG_GATE_RESULT_RUN_ID}"' in script
    assert '[ "$run_status" != "completed" ]' in script
    assert '[ "$run_conclusion" != "success" ]' in script
    assert '[ "$run_event" != "workflow_dispatch" ]' in script
    assert '[ "$run_workflow_name" != "RAG Release Gates" ]' in script
    assert '[ "$run_workflow_path" != ".github/workflows/rag-release-gates.yml" ]' in script
    assert "RAG source run head SHA does not match git_sha" in script
    assert "Release Manifest Evidence workflow ref must match git_sha" in script
    assert "scripts/release/evidence_source.py git-sha" in script


def test_workflow_rejects_fixture_sample_fallback_and_requires_pass() -> None:
    script = _run_script()

    for token in ("fixture", "sample", "example", "placeholder", "fake", "fallback"):
        assert token in script
    assert "dataset_fallback_used must be false" in script
    assert "small_fixture_metric_gates_advisory must be false" in script
    assert "release_decision must be PASS" in script
    assert "attestation_status must be VERIFIED" in script
    assert "rag_gate_result path escapes downloaded artifact" in script
    assert "artifacts/release_control_plane_sources" in script


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
    assert upload_step["with"]["if-no-files-found"] == "error"
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


def test_evidence_source_helper_requires_full_sha_and_non_placeholder_digests() -> None:
    assert evidence_source.validate_git_sha("A" * 40) == "a" * 40
    assert evidence_source.validate_oci_digest("sha256:" + "a1" * 32, label="digest")

    for value in ("deadbeef", "g" * 40):
        with pytest.raises(evidence_source.EvidenceSourceError):
            evidence_source.validate_git_sha(value)
    for value in ("sha256:" + "0" * 64, "a" * 64, "sha256:" + "A" * 64):
        with pytest.raises(evidence_source.EvidenceSourceError):
            evidence_source.validate_oci_digest(value, label="digest")


def test_release_manifest_generation_rejects_sample_rag_fixture(tmp_path: Path) -> None:
    rag_path = _rag_payload(tmp_path)
    rag_payload = json.loads(rag_path.read_text(encoding="utf-8"))
    rag_payload["source_artifacts"][0]["path"] = "data/evals/pulseplate_rag_eval_sample.jsonl"
    rag_path.write_text(json.dumps(rag_payload, sort_keys=True) + "\n", encoding="utf-8")

    script = _run_script()
    assert "data/evals/pulseplate_rag_eval_sample.jsonl" not in script
    rag_triggers = _workflow_on(_load_workflow(RAG_WORKFLOW_PATH))
    assert "workflow_dispatch" in rag_triggers
    assert "ci/release-control-plane-source-producers" in LEDGER_PATH.read_text(encoding="utf-8")
