from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.ci import check_release_control_plane
from scripts.release import build_equivalence
from scripts.release import release_manifest
from scripts.release import reviewer_packet_hashes

REPO_ROOT = Path(__file__).resolve().parents[1]
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
OCI_DIGEST = "sha256:" + ("a" * 64)
PROVENANCE_DIGEST = "sha256:" + ("b" * 64)
ARTIFACT_DIGEST = "sha256:" + ("e" * 64)
TEST_GIT_SHA = "git-sha-for-release-control-plane-ci-gate-tests"


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


def _rag_payload(
    *, release_decision: str = "PASS", git_sha: str = TEST_GIT_SHA
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "release-rag-gate-result.v1",
        "hash_algorithm": "sha256",
        "canonicalization": release_manifest.CANONICALIZATION,
        "eval_artifact_hash": "c" * 64,
        "experiment_id": "unit-test",
        "timestamp": "2026-05-06T00:00:00Z",
        "release_decision": release_decision,
        "gate_checks": {"answer_precision_min": release_decision == "PASS"},
        "threshold_results": [],
        "strict_violations": [] if release_decision == "PASS" else ["answer_precision_min"],
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
                "path": "artifacts/rag_eval/unit-test/metrics_summary.json",
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


def _write_rag_gate_result(
    repo_root: Path,
    *,
    release_decision: str = "PASS",
    git_sha: str = TEST_GIT_SHA,
) -> tuple[Path, dict[str, object]]:
    payload = _rag_payload(release_decision=release_decision, git_sha=git_sha)
    rag_path = repo_root / "artifacts/rag_eval/unit-test/rag_gate_result.json"
    _write_json(rag_path, payload)
    return rag_path, payload


def _build_manifest(
    repo_root: Path,
    *,
    rag_decision: str = "PASS",
    attestation_status: str = "VERIFIED",
) -> tuple[dict[str, object], dict[str, object]]:
    _write_metadata_pack(repo_root)
    rag_path, rag_payload = _write_rag_gate_result(repo_root, release_decision=rag_decision)
    manifest_payload = release_manifest.build_manifest_payload(
        repo_root=repo_root,
        git_sha=TEST_GIT_SHA,
        ios_build_number="100",
        marketing_version="1.0",
        bundle_id="app.pulseplate.PulsePlate",
        rag_gate_result_path=rag_path,
        sbom_digest=OCI_DIGEST,
        provenance_digest=PROVENANCE_DIGEST,
        attestation_status=attestation_status,
    )
    return manifest_payload, rag_payload


def _rehash_manifest(payload: dict[str, object]) -> dict[str, object]:
    updated = dict(payload)
    updated.pop("release_manifest_hash", None)
    updated["release_manifest_hash"] = release_manifest.sha256_lower_hex(
        release_manifest.canonical_json_bytes(updated)
    )
    return updated


def _build_identity(
    manifest_payload: dict[str, object], *, artifact_digest: str = ARTIFACT_DIGEST
) -> dict[str, object]:
    return {
        "schema_version": "release-build-identity.v1",
        "hash_algorithm": "sha256",
        "canonicalization": release_manifest.CANONICALIZATION,
        "build_identity": dict(manifest_payload["build_identity"]),
        "artifact_digest": artifact_digest,
        "release_manifest_hash": manifest_payload["release_manifest_hash"],
        "reviewer_identity": dict(manifest_payload["reviewer_identity"]),
        "ml_identity": dict(manifest_payload["ml_identity"]),
        "supply_chain_identity": dict(manifest_payload["supply_chain_identity"]),
    }


def _build_equivalence_result(manifest_payload: dict[str, object]) -> dict[str, object]:
    identity = _build_identity(manifest_payload)
    return build_equivalence.build_equivalence_decision(
        review_payload=identity,
        production_payload=identity,
        manifest_payload=manifest_payload,
    )


def _write_evidence(
    tmp_path: Path,
    *,
    manifest_payload: dict[str, object] | None = None,
    rag_payload: dict[str, object] | None = None,
    build_payload: dict[str, object] | None = None,
) -> tuple[Path, Path, Path]:
    if manifest_payload is None or rag_payload is None:
        manifest_payload, rag_payload = _build_manifest(tmp_path)
    if build_payload is None:
        build_payload = _build_equivalence_result(manifest_payload)

    manifest_path = tmp_path / "artifacts/release/release_manifest.json"
    rag_path = tmp_path / "artifacts/rag_eval/unit-test/rag_gate_result.json"
    build_path = tmp_path / "artifacts/release/build_equivalence_result.json"
    _write_json(manifest_path, manifest_payload)
    _write_json(rag_path, rag_payload)
    _write_json(build_path, build_payload)
    return manifest_path, rag_path, build_path


def _decision(
    tmp_path: Path,
    *,
    manifest_payload: dict[str, object] | None = None,
    rag_payload: dict[str, object] | None = None,
    build_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    manifest_path, rag_path, build_path = _write_evidence(
        tmp_path,
        manifest_payload=manifest_payload,
        rag_payload=rag_payload,
        build_payload=build_payload,
    )
    return check_release_control_plane.check_release_control_plane_files(
        release_manifest_path=manifest_path,
        rag_gate_result_path=rag_path,
        build_equivalence_path=build_path,
    )


def test_allow_when_all_release_control_plane_evidence_passes(tmp_path: Path) -> None:
    decision = _decision(tmp_path)

    assert decision["decision"] == "ALLOW"
    assert decision["reason_codes"] == []
    assert decision["rag_gate_decision"] == "PASS"
    assert decision["build_equivalence_decision"] == "EQUIVALENT"
    assert decision["attestation_status"] == "VERIFIED"
    assert HASH_RE.fullmatch(str(decision["release_manifest_hash"]))


def test_block_when_release_manifest_missing(tmp_path: Path) -> None:
    manifest_path, rag_path, build_path = _write_evidence(tmp_path)
    manifest_path.unlink()

    decision = check_release_control_plane.check_release_control_plane_files(
        release_manifest_path=manifest_path,
        rag_gate_result_path=rag_path,
        build_equivalence_path=build_path,
    )

    assert decision["decision"] == "BLOCK"
    assert "missing_release_manifest" in decision["reason_codes"]


def test_block_when_release_manifest_decision_blocks(tmp_path: Path) -> None:
    manifest_payload, rag_payload = _build_manifest(tmp_path, rag_decision="NO-GO")
    build_payload = _build_equivalence_result(manifest_payload)

    decision = _decision(
        tmp_path,
        manifest_payload=manifest_payload,
        rag_payload=rag_payload,
        build_payload=build_payload,
    )

    assert decision["decision"] == "BLOCK"
    assert "release_manifest_block" in decision["reason_codes"]
    assert "rag_gate_result_not_pass" in decision["reason_codes"]


def test_block_when_rag_gate_result_missing(tmp_path: Path) -> None:
    manifest_path, rag_path, build_path = _write_evidence(tmp_path)
    rag_path.unlink()

    decision = check_release_control_plane.check_release_control_plane_files(
        release_manifest_path=manifest_path,
        rag_gate_result_path=rag_path,
        build_equivalence_path=build_path,
    )

    assert decision["decision"] == "BLOCK"
    assert "missing_rag_gate_result" in decision["reason_codes"]


def test_block_when_rag_gate_result_is_no_go(tmp_path: Path) -> None:
    manifest_payload, rag_payload = _build_manifest(tmp_path)
    rag_payload["release_decision"] = "NO-GO"
    rag_payload["strict_violations"] = ["answer_precision_min"]
    rag_payload["rag_gate_result_hash"] = release_manifest.sha256_lower_hex(
        release_manifest.canonical_json_bytes(
            {key: value for key, value in rag_payload.items() if key != "rag_gate_result_hash"}
        )
    )

    decision = _decision(tmp_path, manifest_payload=manifest_payload, rag_payload=rag_payload)

    assert decision["decision"] == "BLOCK"
    assert "rag_gate_result_not_pass" in decision["reason_codes"]


def test_block_when_build_equivalence_missing(tmp_path: Path) -> None:
    manifest_path, rag_path, build_path = _write_evidence(tmp_path)
    build_path.unlink()

    decision = check_release_control_plane.check_release_control_plane_files(
        release_manifest_path=manifest_path,
        rag_gate_result_path=rag_path,
        build_equivalence_path=build_path,
    )

    assert decision["decision"] == "BLOCK"
    assert "missing_build_equivalence" in decision["reason_codes"]


def test_block_when_build_equivalence_blocks(tmp_path: Path) -> None:
    manifest_payload, rag_payload = _build_manifest(tmp_path)
    build_payload = _build_equivalence_result(manifest_payload)
    build_payload["decision"] = "BLOCK"
    build_payload["reason_codes"] = ["git_sha_mismatch"]
    build_payload["mismatch_details"] = [
        {"field": "build_identity.git_sha", "reason_code": "git_sha_mismatch"}
    ]

    decision = _decision(
        tmp_path,
        manifest_payload=manifest_payload,
        rag_payload=rag_payload,
        build_payload=build_payload,
    )

    assert decision["decision"] == "BLOCK"
    assert "build_equivalence_not_equivalent" in decision["reason_codes"]
    assert "build_identity_mismatch" in decision["reason_codes"]


def test_block_when_equivalent_build_equivalence_has_mismatch_findings(tmp_path: Path) -> None:
    manifest_payload, rag_payload = _build_manifest(tmp_path)
    build_payload = _build_equivalence_result(manifest_payload)
    build_payload["reason_codes"] = ["git_sha_mismatch"]
    build_payload["mismatch_details"] = [
        {"field": "build_identity.git_sha", "reason_code": "git_sha_mismatch"}
    ]

    decision = _decision(
        tmp_path,
        manifest_payload=manifest_payload,
        rag_payload=rag_payload,
        build_payload=build_payload,
    )

    assert decision["decision"] == "BLOCK"
    assert "invalid_build_equivalence" in decision["reason_codes"]


def test_block_when_attestation_not_verified(tmp_path: Path) -> None:
    manifest_payload, rag_payload = _build_manifest(tmp_path, attestation_status="PENDING")
    build_payload = _build_equivalence_result(manifest_payload)

    decision = _decision(
        tmp_path,
        manifest_payload=manifest_payload,
        rag_payload=rag_payload,
        build_payload=build_payload,
    )

    assert decision["decision"] == "BLOCK"
    assert "attestation_not_verified" in decision["reason_codes"]


def test_block_on_malformed_json(tmp_path: Path) -> None:
    manifest_path, rag_path, build_path = _write_evidence(tmp_path)
    rag_path.write_text("{not-json\n", encoding="utf-8")

    decision = check_release_control_plane.check_release_control_plane_files(
        release_manifest_path=manifest_path,
        rag_gate_result_path=rag_path,
        build_equivalence_path=build_path,
    )

    assert decision["decision"] == "BLOCK"
    assert "malformed_rag_gate_result" in decision["reason_codes"]


def test_empty_evidence_objects_are_invalid_not_allowed(tmp_path: Path) -> None:
    manifest_path, rag_path, build_path = _write_evidence(
        tmp_path,
        manifest_payload={},
        rag_payload={},
        build_payload={},
    )

    decision = check_release_control_plane.check_release_control_plane_files(
        release_manifest_path=manifest_path,
        rag_gate_result_path=rag_path,
        build_equivalence_path=build_path,
    )

    assert decision["decision"] == "BLOCK"
    assert "invalid_release_manifest" in decision["reason_codes"]
    assert "invalid_rag_gate_result" in decision["reason_codes"]
    assert "invalid_build_equivalence" in decision["reason_codes"]


def test_block_on_invalid_digest_format(tmp_path: Path) -> None:
    manifest_payload, rag_payload = _build_manifest(tmp_path)
    manifest_payload["supply_chain_identity"] = dict(manifest_payload["supply_chain_identity"])
    manifest_payload["supply_chain_identity"]["sbom_digest"] = "not-an-oci-digest"
    manifest_payload["release_decision"] = "BLOCK"
    manifest_payload["decision_reasons"] = ["invalid_sbom_digest"]
    manifest_payload = _rehash_manifest(manifest_payload)
    build_payload = _build_equivalence_result(manifest_payload)

    decision = _decision(
        tmp_path,
        manifest_payload=manifest_payload,
        rag_payload=rag_payload,
        build_payload=build_payload,
    )

    assert decision["decision"] == "BLOCK"
    assert "unsupported_digest_format" in decision["reason_codes"]


def test_release_manifest_hash_mismatch_blocks(tmp_path: Path) -> None:
    manifest_payload, rag_payload = _build_manifest(tmp_path)
    build_payload = _build_equivalence_result(manifest_payload)
    build_payload["release_manifest_hash"] = "1" * 64

    decision = _decision(
        tmp_path,
        manifest_payload=manifest_payload,
        rag_payload=rag_payload,
        build_payload=build_payload,
    )

    assert decision["decision"] == "BLOCK"
    assert "release_manifest_hash_mismatch" in decision["reason_codes"]


def test_git_sha_mismatch_between_manifest_and_rag_blocks(tmp_path: Path) -> None:
    manifest_payload, _rag_payload_valid = _build_manifest(tmp_path)
    _rag_path, rag_payload = _write_rag_gate_result(tmp_path, git_sha="other-git-sha")

    decision = _decision(tmp_path, manifest_payload=manifest_payload, rag_payload=rag_payload)

    assert decision["decision"] == "BLOCK"
    assert "git_sha_mismatch" in decision["reason_codes"]


def test_evidence_paths_must_stay_under_artifacts(tmp_path: Path) -> None:
    manifest_payload, rag_payload = _build_manifest(tmp_path)
    rag_payload["source_artifacts"] = [
        {
            "kind": "metrics_summary",
            "path": "tmp/not-artifacts/metrics.json",
            "hash": "d" * 64,
        }
    ]
    rag_payload["rag_gate_result_hash"] = release_manifest.sha256_lower_hex(
        release_manifest.canonical_json_bytes(
            {key: value for key, value in rag_payload.items() if key != "rag_gate_result_hash"}
        )
    )

    decision = _decision(tmp_path, manifest_payload=manifest_payload, rag_payload=rag_payload)

    assert decision["decision"] == "BLOCK"
    assert "evidence_path_outside_allowed_artifacts" in decision["reason_codes"]


def test_evidence_paths_reject_parent_directory_escape(tmp_path: Path) -> None:
    manifest_payload, rag_payload = _build_manifest(tmp_path)
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

    decision = _decision(tmp_path, manifest_payload=manifest_payload, rag_payload=rag_payload)

    assert decision["decision"] == "BLOCK"
    assert "evidence_path_outside_allowed_artifacts" in decision["reason_codes"]


def test_reason_code_ordering_is_deterministic(tmp_path: Path) -> None:
    manifest_payload, rag_payload = _build_manifest(tmp_path, attestation_status="PENDING")
    build_payload = _build_equivalence_result(manifest_payload)
    build_payload["decision"] = "BLOCK"
    build_payload["reason_codes"] = ["git_sha_mismatch"]
    build_payload["mismatch_details"] = [
        {"field": "build_identity.git_sha", "reason_code": "git_sha_mismatch"}
    ]
    rag_payload["release_decision"] = "NO-GO"
    rag_payload["rag_gate_result_hash"] = release_manifest.sha256_lower_hex(
        release_manifest.canonical_json_bytes(
            {key: value for key, value in rag_payload.items() if key != "rag_gate_result_hash"}
        )
    )

    decision = _decision(
        tmp_path,
        manifest_payload=manifest_payload,
        rag_payload=rag_payload,
        build_payload=build_payload,
    )

    assert decision["reason_codes"] == sorted(
        decision["reason_codes"],
        key=lambda reason: (
            check_release_control_plane.REASON_ORDER.get(str(reason), 10_000),
            str(reason),
        ),
    )


def test_output_json_is_deterministic(tmp_path: Path) -> None:
    manifest_path, rag_path, build_path = _write_evidence(tmp_path)
    first_output = tmp_path / "out/first.json"
    second_output = tmp_path / "out/second.json"

    first = check_release_control_plane.check_release_control_plane_files(
        release_manifest_path=manifest_path,
        rag_gate_result_path=rag_path,
        build_equivalence_path=build_path,
    )
    second = check_release_control_plane.check_release_control_plane_files(
        release_manifest_path=manifest_path,
        rag_gate_result_path=rag_path,
        build_equivalence_path=build_path,
    )
    check_release_control_plane.write_json(first_output, first)
    check_release_control_plane.write_json(second_output, second)

    assert first_output.read_text(encoding="utf-8") == second_output.read_text(encoding="utf-8")
    assert first_output.read_text(encoding="utf-8").endswith("\n")


def test_schema_allows_raw_malformed_summary_values_for_block_outputs(tmp_path: Path) -> None:
    schema = json.loads(
        (REPO_ROOT / "docs/release/RELEASE_CONTROL_PLANE_CI_GATE.schema.json").read_text(
            encoding="utf-8"
        )
    )
    manifest_payload, rag_payload = _build_manifest(tmp_path)
    rag_payload["release_decision"] = "MALFORMED"
    build_payload = _build_equivalence_result(manifest_payload)
    build_payload["decision"] = "MAYBE"
    manifest_payload["supply_chain_identity"] = dict(manifest_payload["supply_chain_identity"])
    manifest_payload["supply_chain_identity"]["attestation_status"] = "BROKEN"

    decision = _decision(
        tmp_path,
        manifest_payload=manifest_payload,
        rag_payload=rag_payload,
        build_payload=build_payload,
    )

    assert decision["decision"] == "BLOCK"
    assert decision["build_equivalence_decision"] == "MAYBE"
    assert decision["rag_gate_decision"] == "MALFORMED"
    assert decision["attestation_status"] == "BROKEN"
    assert schema["properties"]["build_equivalence_decision"] == {"type": ["string", "null"]}
    assert schema["properties"]["rag_gate_decision"] == {"type": ["string", "null"]}
    assert schema["properties"]["attestation_status"] == {"type": ["string", "null"]}


def test_cli_writes_json_and_markdown_outputs(tmp_path: Path, capsys) -> None:
    manifest_path, rag_path, build_path = _write_evidence(tmp_path)
    json_out = tmp_path / "gate.json"
    markdown_out = tmp_path / "gate.md"

    status = check_release_control_plane.main(
        [
            "--release-manifest",
            str(manifest_path),
            "--rag-gate-result",
            str(rag_path),
            "--build-equivalence",
            str(build_path),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    assert status == 0
    assert "ALLOW:" in capsys.readouterr().out
    assert json.loads(json_out.read_text(encoding="utf-8"))["decision"] == "ALLOW"
    assert "- Decision: `ALLOW`" in markdown_out.read_text(encoding="utf-8")


# These workflow/docs assertions intentionally guard PR-5 textual integration
# points. If the workflow contract grows, migrate them to YAML/schema parsing.
def test_workflow_integration_does_not_require_app_store_secrets() -> None:
    workflow = (REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8")
    marker = "release-control-plane-fixture-gate:"
    assert marker in workflow
    job_block = workflow.split(marker, 1)[1].split("\n  production-gates:", 1)[0]

    forbidden_terms = ("APP_STORE", "FASTLANE", "MATCH_PASSWORD", "ASC_", "APPSTORE")
    assert not any(term in job_block for term in forbidden_terms)
    assert "secrets." not in job_block


def test_workflow_integration_does_not_alter_app_store_upload_behavior() -> None:
    workflow = (REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8")
    fixture_job = workflow.split("release-control-plane-fixture-gate:", 1)[1].split(
        "\n  production-gates:",
        1,
    )[0]
    deploy_jobs = workflow.split("\n  deploy-production:", 1)[1]

    assert "upload" not in fixture_job.lower()
    assert "app store connect" not in fixture_job.lower()
    assert "release-control-plane-fixture-gate" not in deploy_jobs


def test_ledger_marks_pr4_merged_and_pr5_active() -> None:
    ledger = (REPO_ROOT / "docs/roadmap/BACKLOG_LEDGER.md").read_text(encoding="utf-8")

    assert "PR-4 merged in PR #1679 on 2026-05-06" in ledger
    assert "PR-5 is active on branch `release/release-control-plane-pr5-ci-gates`" in ledger
    assert "Future protected upload and App Store Connect execution remain out of scope" in ledger
    assert "full App Store readiness is not complete" in ledger


def test_pr1682_premortem_artifact_has_no_unresolved_p0_p1_findings() -> None:
    premortem = (REPO_ROOT / "docs/review/PR_1682_PREMORTEM.md").read_text(encoding="utf-8")

    assert "Unresolved P0/P1: none." in premortem
    assert "scripts/ci/check_release_control_plane.py" in premortem
    assert "tests/test_release_control_plane_ci_gate.py" in premortem
    assert ".github/workflows/cd.yml" in premortem
