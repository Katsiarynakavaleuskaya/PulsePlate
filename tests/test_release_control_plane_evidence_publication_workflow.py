from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/release-control-plane-evidence.yml"
CD_WORKFLOW_PATH = REPO_ROOT / ".github/workflows/cd.yml"
DOC_PATH = REPO_ROOT / "docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md"
CI_GATE_DOC_PATH = REPO_ROOT / "docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md"
EPIC_PATH = REPO_ROOT / "docs/release/RELEASE_CONTROL_PLANE_EPIC.md"
TASK_PACKET_PATH = REPO_ROOT / "docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md"
LEDGER_PATH = REPO_ROOT / "docs/roadmap/BACKLOG_LEDGER.md"


def _load_workflow() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _workflow_on(workflow: dict[str, Any]) -> dict[str, Any]:
    # PyYAML 5.x still resolves the YAML 1.1 key "on" as boolean True.
    return workflow.get("on") or workflow[True]


def _job(workflow: dict[str, Any]) -> dict[str, Any]:
    return workflow["jobs"]["publish-release-control-plane-evidence"]


def _step_by_name(job: dict[str, Any], name: str) -> dict[str, Any]:
    for step in job["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError(f"Step {name!r} not found")


def _collect_script(workflow: dict[str, Any]) -> str:
    return str(_step_by_name(_job(workflow), "Collect governed release evidence")["run"])


def test_workflow_exists_and_is_workflow_dispatch_only() -> None:
    assert WORKFLOW_PATH.is_file()
    workflow = _load_workflow()
    triggers = _workflow_on(workflow)

    assert set(triggers) == {"workflow_dispatch"}
    assert "pull_request" not in triggers
    assert "push" not in triggers


def test_workflow_inputs_define_source_artifact_contract() -> None:
    inputs = _workflow_on(_load_workflow())["workflow_dispatch"]["inputs"]
    expected_inputs = {
        "git_sha",
        "release_manifest_run_id",
        "release_manifest_artifact_name",
        "release_manifest_workflow_name",
        "release_manifest_path",
        "rag_gate_result_run_id",
        "rag_gate_result_artifact_name",
        "rag_gate_result_workflow_name",
        "rag_gate_result_path",
        "build_equivalence_run_id",
        "build_equivalence_artifact_name",
        "build_equivalence_workflow_name",
        "build_equivalence_path",
        "evidence_artifact_name",
    }

    assert set(inputs) == expected_inputs
    assert all(inputs[name]["required"] is True for name in expected_inputs)
    assert inputs["release_manifest_path"]["default"] == "release_manifest.json"
    assert inputs["rag_gate_result_path"]["default"] == "rag_gate_result.json"
    assert inputs["rag_gate_result_workflow_name"]["default"] == "RAG Release Gates"
    assert inputs["build_equivalence_path"]["default"] == "build_equivalence_result.json"
    assert (
        inputs["evidence_artifact_name"]["default"] == "release-control-plane-production-evidence"
    )


def test_workflow_permissions_are_least_privilege() -> None:
    workflow = _load_workflow()

    assert workflow["permissions"] == {"actions": "read", "contents": "read"}
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "id-token:" not in workflow_text
    assert "packages:" not in workflow_text


def test_workflow_downloads_governed_sources_and_publishes_canonical_layout() -> None:
    workflow = _load_workflow()
    collect_script = _collect_script(workflow)
    upload_step = _step_by_name(
        _job(workflow), "Upload governed release-control-plane evidence artifact"
    )
    upload_path = str(upload_step["with"]["path"])

    assert "gh run view" in collect_script
    assert "gh run download" in collect_script
    assert "--json status,conclusion,headSha,event,workflowName,url" in collect_script
    assert '[ "$run_event" != "workflow_dispatch" ]' in collect_script
    assert "require_expected_source_workflow" in collect_script
    assert "source workflow does not match expected producer" in collect_script
    assert "RELEASE_MANIFEST_WORKFLOW_NAME" in collect_script
    assert "RAG_GATE_RESULT_WORKFLOW_NAME" in collect_script
    assert "BUILD_EQUIVALENCE_WORKFLOW_NAME" in collect_script
    assert "scripts/ci/check_release_control_plane.py" in collect_script

    for canonical_path in (
        "release-control-plane/release_manifest.json",
        "release-control-plane/rag_gate_result.json",
        "release-control-plane/build_equivalence_result.json",
    ):
        assert canonical_path in collect_script
        assert canonical_path in upload_path

    assert "release_control_plane_ci_gate.json" in upload_path
    assert "release_control_plane_ci_gate.md" in upload_path
    assert "source_runs.txt" in upload_path
    assert upload_step["with"]["if-no-files-found"] == "error"


def test_workflow_rejects_fixtures_placeholders_paths_and_git_sha_mismatch() -> None:
    collect_script = _collect_script(_load_workflow())

    assert "reject_placeholder" in collect_script
    assert "fixtures/tests/placeholders/fakes" in collect_script
    assert "/*|*..*|*//*" in collect_script
    assert "must be a numeric GitHub Actions run id" in collect_script
    assert "git_sha must be a hexadecimal commit SHA" in collect_script
    assert "source run head SHA does not match git_sha" in collect_script
    assert "publication workflow ref must match git_sha" in collect_script
    assert "Release manifest git SHA does not match workflow git_sha" in collect_script
    assert "sentinel placeholder digest/hash rejected" in collect_script
    assert "data/evals/pulseplate_rag_eval_sample.jsonl" in collect_script
    assert "dataset_fallback_used must be false" in collect_script
    assert "small_fixture_metric_gates_advisory must be false" in collect_script


def test_workflow_has_no_app_store_or_fastlane_upload_surface() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow_json = json.dumps(_load_workflow(), default=str)

    forbidden_terms = (
        "APP_STORE",
        "APPSTORE",
        "ASC_",
        "FASTLANE",
        "MATCH_PASSWORD",
        "upload_to_app_store",
        "app store connect",
    )

    assert "secrets.GITHUB_TOKEN" in workflow_text
    assert not any(term in workflow_json for term in forbidden_terms)
    assert "fastlane" not in workflow_json.lower()


def test_workflow_summary_documents_run_id_and_artifact_name_handoff() -> None:
    summary_script = str(
        _step_by_name(_job(_load_workflow()), "Publish evidence handoff summary")["run"]
    )

    assert "GITHUB_RUN_ID" in summary_script
    assert "RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID" in summary_script
    assert "RELEASE_CONTROL_PLANE_EVIDENCE_ARTIFACT_NAME" in summary_script
    assert "Set production Actions variables" in summary_script


def test_docs_define_publication_ceremony_and_virtualenv_policy() -> None:
    docs = DOC_PATH.read_text(encoding="utf-8")
    ci_gate_docs = CI_GATE_DOC_PATH.read_text(encoding="utf-8")

    assert "Release Control Plane Evidence" in docs
    assert "RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID" in docs
    assert "RELEASE_CONTROL_PLANE_EVIDENCE_ARTIFACT_NAME" in docs
    assert "successful `workflow_dispatch` source runs" in docs
    assert "RAG Release Gates" in docs
    assert "release_manifest_workflow_name" in docs
    assert "build_equivalence_workflow_name" in docs
    assert "do not yet exist for every evidence type" in docs.replace("\n", " ")
    assert "release-control-plane/release_manifest.json" in docs
    assert "release-control-plane/rag_gate_result.json" in docs
    assert "release-control-plane/build_equivalence_result.json" in docs
    assert ".venv/bin/python" in docs
    assert "must not" in docs
    assert "contact App Store Connect" in docs
    assert "Fastlane upload behavior" in docs
    assert "placeholder digest" in docs
    assert "workflow ref must match `git_sha`" in docs
    assert "PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md" in ci_gate_docs


def test_ledger_and_epic_record_followup_without_closing_release_readiness() -> None:
    ledger = LEDGER_PATH.read_text(encoding="utf-8")
    epic = EPIC_PATH.read_text(encoding="utf-8")
    task_packet = TASK_PACKET_PATH.read_text(encoding="utf-8")

    for content in (ledger, epic, task_packet):
        assert "ci/release-control-plane-evidence-publication" in content
        assert "PR #1692" in content

    assert "full App Store readiness is not complete" in ledger
    assert "train is not production-ready" in ledger
    assert "App Store Connect execution" in ledger
    assert "Fastlane protected upload mutation" in ledger
    assert "does not create release truth" in task_packet.replace("\n", " ")


def test_existing_cd_gate_variable_contract_is_preserved() -> None:
    cd_workflow = CD_WORKFLOW_PATH.read_text(encoding="utf-8")
    ci_gate_docs = CI_GATE_DOC_PATH.read_text(encoding="utf-8")

    assert "RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID" in cd_workflow
    assert "RELEASE_CONTROL_PLANE_EVIDENCE_ARTIFACT_NAME" in cd_workflow
    assert "RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID" in ci_gate_docs
    assert "RELEASE_CONTROL_PLANE_EVIDENCE_ARTIFACT_NAME" in ci_gate_docs
