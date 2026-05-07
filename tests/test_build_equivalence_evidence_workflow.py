from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from scripts.release import build_identity, release_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/build-equivalence-evidence.yml"
LEDGER_PATH = REPO_ROOT / "docs/roadmap/BACKLOG_LEDGER.md"

ARTIFACT_DIGEST = "sha256:" + "a1" * 32


def _load_workflow(path: Path = WORKFLOW_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _workflow_on(workflow: dict[str, Any]) -> dict[str, Any]:
    return workflow.get("on") or workflow[True]


def _job(workflow: dict[str, Any]) -> dict[str, Any]:
    return workflow["jobs"]["publish-build-equivalence-evidence"]


def _step_by_name(job: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [step for step in job["steps"] if step.get("name") == name]
    assert len(matches) == 1
    return matches[0]


def _run_script() -> str:
    return str(
        _step_by_name(_job(_load_workflow()), "Generate governed build equivalence evidence")["run"]
    )


def _manifest_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": release_manifest.SCHEMA_VERSION,
        "hash_algorithm": release_manifest.HASH_ALGORITHM,
        "canonicalization": release_manifest.CANONICALIZATION,
        "build_identity": {
            "git_sha": "a" * 40,
            "ios_build_number": "100",
            "marketing_version": "1.0",
            "bundle_id": "app.pulseplate.PulsePlate",
        },
        "reviewer_identity": {
            "schema_version": release_manifest.REVIEWER_SCHEMA_VERSION,
            "reviewer_notes_hash": "b" * 64,
            "appstore_metadata_hash": "c" * 64,
            "source_artifacts": [
                {
                    "kind": "reviewer_notes",
                    "path": "docs/release/reviewer_notes.md",
                    "hash": "d" * 64,
                }
            ],
        },
        "ml_identity": {
            "schema_version": release_manifest.RAG_GATE_SCHEMA_VERSION,
            "rag_gate_result_hash": "e" * 64,
            "eval_artifact_hash": "f" * 64,
            "release_decision": "PASS",
            "source_artifacts": [
                {
                    "kind": "rag_gate_result",
                    "path": "artifacts/release_control_plane_sources/rag_gate_result.json",
                    "hash": "1" * 64,
                }
            ],
        },
        "supply_chain_identity": {
            "sbom_digest": "sha256:" + "2" * 64,
            "provenance_digest": "sha256:" + "3" * 64,
            "attestation_status": release_manifest.VERIFIED_ATTESTATION_STATUS,
        },
        "release_decision": release_manifest.ALLOW_DECISION,
        "decision_reasons": [],
    }
    payload["release_manifest_hash"] = release_manifest.sha256_lower_hex(
        release_manifest.canonical_json_bytes(payload)
    )
    assert release_manifest.validate_manifest_payload(payload) == []
    return payload


def test_workflow_exists_and_is_dispatch_only() -> None:
    workflow = _load_workflow()

    assert WORKFLOW_PATH.is_file()
    assert workflow["name"] == "Build Equivalence Evidence"
    assert set(_workflow_on(workflow)) == {"workflow_dispatch"}
    assert "pull_request" not in _workflow_on(workflow)
    assert "push" not in _workflow_on(workflow)
    assert "schedule" not in _workflow_on(workflow)


def test_workflow_permissions_environment_and_inputs_are_bounded() -> None:
    workflow = _load_workflow()
    inputs = _workflow_on(workflow)["workflow_dispatch"]["inputs"]
    expected_inputs = {
        "git_sha",
        "release_manifest_source",
        "review_artifact_digest",
        "production_candidate_artifact_digest",
        "evidence_artifact_name",
    }

    assert set(inputs) == expected_inputs
    assert all(inputs[name]["required"] is True for name in expected_inputs)
    assert "run_id" in inputs["release_manifest_source"]["description"]
    assert "artifact_name" in inputs["release_manifest_source"]["description"]
    assert "path" in inputs["release_manifest_source"]["description"]
    assert workflow["permissions"] == {"actions": "read", "contents": "read"}
    assert _job(workflow)["environment"]["name"] == "release-evidence"
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "id-token:" not in workflow_text
    assert "packages:" not in workflow_text


def test_workflow_validates_release_manifest_source_run_and_git_sha() -> None:
    script = _run_script()

    assert "scripts/release/evidence_source.py source-env" in script
    assert "--label release_manifest" in script
    assert "--expected-path release_manifest.json" in script
    assert "gh run view" in script
    assert "--json status,conclusion,headSha,event,workflowName,url" in script
    assert 'gh api "repos/${GITHUB_REPOSITORY}/actions/runs/${RELEASE_MANIFEST_RUN_ID}"' in script
    assert '[ "$run_status" != "completed" ]' in script
    assert '[ "$run_conclusion" != "success" ]' in script
    assert '[ "$run_event" != "workflow_dispatch" ]' in script
    assert '[ "$run_workflow_name" != "Release Manifest Evidence" ]' in script
    assert '[ "$run_workflow_path" != ".github/workflows/release-manifest-evidence.yml" ]' in script
    assert "release manifest source run head SHA does not match git_sha" in script
    assert "Build Equivalence Evidence workflow ref must match git_sha" in script


def test_workflow_generates_identities_runs_equivalence_and_uploads_stable_path() -> None:
    workflow = _load_workflow()
    script = _run_script()
    upload_step = _step_by_name(
        _job(workflow), "Upload governed build equivalence evidence artifact"
    )
    summary_script = str(
        _step_by_name(_job(workflow), "Publish build equivalence evidence summary")["run"]
    )

    assert "scripts/release/evidence_source.py oci-digest --label review_artifact_digest" in script
    assert (
        "scripts/release/evidence_source.py oci-digest --label production_candidate_artifact_digest"
        in script
    )
    assert "release_manifest path escapes downloaded artifact" in script
    assert "Path(sys.argv[1]).resolve()" in script
    assert "scripts/release/release_manifest.py validate" in script
    assert "scripts/release/build_identity.py" in script
    assert '--artifact-digest "$REVIEW_ARTIFACT_DIGEST"' in script
    assert '--artifact-digest "$PRODUCTION_CANDIDATE_ARTIFACT_DIGEST"' in script
    assert "review_build_identity.json" in script
    assert "production_candidate_identity.json" in script
    assert "scripts/release/build_equivalence.py" in script
    assert "build_equivalence_result.decision must be EQUIVALENT" in script
    assert "--review-build" in script
    assert "--production-candidate" in script
    assert "--release-manifest" in script
    assert (
        upload_step["with"]["path"]
        == "${{ runner.temp }}/build-equivalence-evidence/build_equivalence_result.json"
    )
    assert (
        upload_step["with"]["name"]
        == "${{ steps.generate-build-equivalence-evidence.outputs.artifact_name }}"
    )
    assert "${{ inputs.evidence_artifact_name }}" not in upload_step["with"]["name"]
    assert upload_step["with"]["if-no-files-found"] == "error"
    assert 'echo "artifact_name=$EVIDENCE_ARTIFACT_NAME" >> "$GITHUB_OUTPUT"' in script
    assert "GITHUB_RUN_ID" in summary_script
    assert "build_equivalence_result.json" in summary_script


def test_build_identity_helper_derives_existing_contract_without_new_manifest_format() -> None:
    manifest_payload = _manifest_payload()
    payload = build_identity.build_identity_payload(
        manifest_payload=manifest_payload,
        artifact_digest=ARTIFACT_DIGEST,
    )

    assert payload["schema_version"] == "release-build-identity.v1"
    assert payload["hash_algorithm"] == release_manifest.HASH_ALGORITHM
    assert payload["canonicalization"] == release_manifest.CANONICALIZATION
    assert payload["build_identity"] == manifest_payload["build_identity"]
    assert payload["artifact_digest"] == ARTIFACT_DIGEST
    assert payload["release_manifest_hash"] == manifest_payload["release_manifest_hash"]
    assert payload["reviewer_identity"] == manifest_payload["reviewer_identity"]
    assert payload["ml_identity"] == manifest_payload["ml_identity"]
    assert payload["supply_chain_identity"] == manifest_payload["supply_chain_identity"]


def test_build_identity_helper_rejects_invalid_manifest_and_placeholder_digest() -> None:
    manifest_payload = _manifest_payload()

    for digest in ("sha256:" + "0" * 64, "a" * 64, "sha256:" + "A" * 64):
        try:
            build_identity.build_identity_payload(
                manifest_payload=manifest_payload,
                artifact_digest=digest,
            )
        except build_identity.BuildIdentityError:
            continue
        raise AssertionError(f"Expected digest to be rejected: {digest}")

    invalid_manifest = dict(manifest_payload)
    invalid_manifest["release_manifest_hash"] = "0" * 64
    try:
        build_identity.build_identity_payload(
            manifest_payload=invalid_manifest,
            artifact_digest=ARTIFACT_DIGEST,
        )
    except build_identity.BuildIdentityError:
        pass
    else:
        raise AssertionError("Expected invalid manifest to be rejected")


def test_workflow_has_no_app_store_fastlane_or_runtime_surface() -> None:
    workflow_json = json.dumps(_load_workflow(), default=str).lower()

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
        "release control plane evidence",
    )
    assert not any(term in workflow_json for term in forbidden_terms)
    assert "ci/release-control-plane-source-producers" in LEDGER_PATH.read_text(encoding="utf-8")
