from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from scripts.release import build_equivalence
from scripts.release import release_manifest
from scripts.release import reviewer_packet_hashes

REPO_ROOT = Path(__file__).resolve().parents[1]
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
OCI_DIGEST = "sha256:" + ("a" * 64)
PROVENANCE_DIGEST = "sha256:" + ("b" * 64)
REVIEW_BUILD_DIGEST = "sha256:" + ("e" * 64)
TEST_GIT_SHA = "git-sha-for-build-equivalence-tests"


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
            (locale_dir / filename).write_text(
                f"{locale}:{filename}\n",
                encoding="utf-8",
            )


def _rag_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "release-rag-gate-result.v1",
        "hash_algorithm": "sha256",
        "canonicalization": release_manifest.CANONICALIZATION,
        "eval_artifact_hash": "c" * 64,
        "experiment_id": "unit-test",
        "timestamp": "2026-04-30T00:00:00Z",
        "release_decision": "PASS",
        "gate_checks": {"answer_precision_min": True},
        "threshold_results": [],
        "strict_violations": [],
        "runtime_warnings": [],
        "dataset_path_used": "tests/fixtures/rag.jsonl",
        "dataset_fallback_used": False,
        "sample_size": 1,
        "git_sha": TEST_GIT_SHA,
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


def _write_rag_gate_result(repo_root: Path) -> Path:
    rag_path = repo_root / "artifacts/rag_eval/unit-test/rag_gate_result.json"
    rag_path.parent.mkdir(parents=True, exist_ok=True)
    rag_path.write_text(json.dumps(_rag_payload(), sort_keys=True) + "\n", encoding="utf-8")
    return rag_path


def _build_manifest(repo_root: Path, *, attestation_status: str = "VERIFIED") -> dict[str, object]:
    _write_metadata_pack(repo_root)
    rag_path = _write_rag_gate_result(repo_root)
    return release_manifest.build_manifest_payload(
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


def _rehash_manifest(payload: dict[str, object]) -> dict[str, object]:
    updated = dict(payload)
    updated.pop("release_manifest_hash", None)
    updated["release_manifest_hash"] = release_manifest.sha256_lower_hex(
        release_manifest.canonical_json_bytes(updated)
    )
    return updated


def _build_identity(
    manifest_payload: dict[str, object],
    *,
    artifact_digest: str = REVIEW_BUILD_DIGEST,
    include_optional_groups: bool = True,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "release-build-identity.v1",
        "hash_algorithm": "sha256",
        "canonicalization": release_manifest.CANONICALIZATION,
        "build_identity": dict(manifest_payload["build_identity"]),
        "artifact_digest": artifact_digest,
        "release_manifest_hash": manifest_payload["release_manifest_hash"],
    }
    if include_optional_groups:
        payload["reviewer_identity"] = dict(manifest_payload["reviewer_identity"])
        payload["ml_identity"] = dict(manifest_payload["ml_identity"])
        payload["supply_chain_identity"] = dict(manifest_payload["supply_chain_identity"])
    return payload


def _decision(
    manifest_payload: dict[str, object],
    *,
    review_payload: dict[str, object] | None = None,
    production_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    if review_payload is None:
        review_payload = _build_identity(manifest_payload)
    if production_payload is None:
        production_payload = _build_identity(manifest_payload)
    return build_equivalence.build_equivalence_decision(
        review_payload=review_payload,
        production_payload=production_payload,
        manifest_payload=manifest_payload,
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_equivalent_build_identities_return_equivalent(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)

    decision = _decision(manifest_payload)

    assert decision["decision"] == "EQUIVALENT"
    assert decision["reason_codes"] == []
    assert decision["mismatch_details"] == []
    assert decision["release_manifest_hash"] == manifest_payload["release_manifest_hash"]
    assert HASH_RE.fullmatch(str(decision["release_manifest_hash"]))


def test_git_sha_mismatch_blocks(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    production_payload = _build_identity(manifest_payload)
    production_payload["build_identity"]["git_sha"] = "other-sha"

    decision = _decision(manifest_payload, production_payload=production_payload)

    assert decision["decision"] == "BLOCK"
    assert "git_sha_mismatch" in decision["reason_codes"]


def test_bundle_id_mismatch_blocks(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    production_payload = _build_identity(manifest_payload)
    production_payload["build_identity"]["bundle_id"] = "app.pulseplate.Other"

    decision = _decision(manifest_payload, production_payload=production_payload)

    assert decision["decision"] == "BLOCK"
    assert "bundle_id_mismatch" in decision["reason_codes"]


def test_marketing_version_mismatch_blocks(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    production_payload = _build_identity(manifest_payload)
    production_payload["build_identity"]["marketing_version"] = "1.1"

    decision = _decision(manifest_payload, production_payload=production_payload)

    assert decision["decision"] == "BLOCK"
    assert "marketing_version_mismatch" in decision["reason_codes"]


def test_ios_build_number_mismatch_blocks(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    production_payload = _build_identity(manifest_payload)
    production_payload["build_identity"]["ios_build_number"] = "101"

    decision = _decision(manifest_payload, production_payload=production_payload)

    assert decision["decision"] == "BLOCK"
    assert "ios_build_number_mismatch" in decision["reason_codes"]


def test_review_build_digest_mismatch_blocks(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    production_payload = _build_identity(
        manifest_payload,
        artifact_digest="sha256:" + ("f" * 64),
    )

    decision = _decision(manifest_payload, production_payload=production_payload)

    assert decision["decision"] == "BLOCK"
    assert "review_build_digest_mismatch" in decision["reason_codes"]


def test_release_manifest_hash_mismatch_blocks(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    production_payload = _build_identity(manifest_payload)
    production_payload["release_manifest_hash"] = "1" * 64

    decision = _decision(manifest_payload, production_payload=production_payload)

    assert decision["decision"] == "BLOCK"
    assert "release_manifest_hash_mismatch" in decision["reason_codes"]


def test_missing_review_identity_blocks(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)

    decision = _decision(manifest_payload, review_payload={})

    assert decision["decision"] == "BLOCK"
    assert "missing_review_build_identity" in decision["reason_codes"]


def test_missing_review_identity_file_writes_block_decision(tmp_path: Path, capsys) -> None:
    manifest_payload = _build_manifest(tmp_path)
    manifest_path = tmp_path / "release_manifest.json"
    review_path = tmp_path / "missing-review.json"
    production_path = tmp_path / "production.json"
    output_path = tmp_path / "equivalence.json"
    _write_json(manifest_path, manifest_payload)
    _write_json(production_path, _build_identity(manifest_payload))

    status = build_equivalence.main(
        [
            "--review-build",
            str(review_path),
            "--production-candidate",
            str(production_path),
            "--release-manifest",
            str(manifest_path),
            "--output",
            str(output_path),
        ]
    )

    output = capsys.readouterr().out
    decision = json.loads(output_path.read_text(encoding="utf-8"))
    assert status == 1
    assert "BLOCK:" in output
    assert decision["decision"] == "BLOCK"
    assert "missing_review_build_identity" in decision["reason_codes"]


def test_missing_production_identity_blocks(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)

    decision = _decision(manifest_payload, production_payload={})

    assert decision["decision"] == "BLOCK"
    assert "missing_production_candidate_identity" in decision["reason_codes"]


def test_missing_production_identity_file_writes_block_decision(tmp_path: Path, capsys) -> None:
    manifest_payload = _build_manifest(tmp_path)
    manifest_path = tmp_path / "release_manifest.json"
    review_path = tmp_path / "review.json"
    production_path = tmp_path / "missing-production.json"
    output_path = tmp_path / "equivalence.json"
    _write_json(manifest_path, manifest_payload)
    _write_json(review_path, _build_identity(manifest_payload))

    status = build_equivalence.main(
        [
            "--review-build",
            str(review_path),
            "--production-candidate",
            str(production_path),
            "--release-manifest",
            str(manifest_path),
            "--output",
            str(output_path),
        ]
    )

    output = capsys.readouterr().out
    decision = json.loads(output_path.read_text(encoding="utf-8"))
    assert status == 1
    assert "BLOCK:" in output
    assert decision["decision"] == "BLOCK"
    assert "missing_production_candidate_identity" in decision["reason_codes"]


def test_malformed_production_identity_reports_production_candidate(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    production_payload = _build_identity(manifest_payload)
    production_payload["schema_version"] = "release-build-identity.v0"

    decision = _decision(manifest_payload, production_payload=production_payload)

    assert decision["decision"] == "BLOCK"
    assert "malformed_production_candidate_identity" in decision["reason_codes"]
    assert {
        "field": "schema_version",
        "reason_code": "malformed_production_candidate_identity",
        "production_candidate": "release-build-identity.v0",
        "release_manifest": "release-build-identity.v1",
    } in decision["mismatch_details"]


def test_malformed_json_uses_controlled_error(tmp_path: Path, capsys) -> None:
    manifest_payload = _build_manifest(tmp_path)
    manifest_path = tmp_path / "release_manifest.json"
    review_path = tmp_path / "review.json"
    production_path = tmp_path / "production.json"
    output_path = tmp_path / "equivalence.json"
    _write_json(manifest_path, manifest_payload)
    review_path.write_text("{not-json\n", encoding="utf-8")
    _write_json(production_path, _build_identity(manifest_payload))

    status = build_equivalence.main(
        [
            "--review-build",
            str(review_path),
            "--production-candidate",
            str(production_path),
            "--release-manifest",
            str(manifest_path),
            "--output",
            str(output_path),
        ]
    )

    output = capsys.readouterr().out
    assert status == 1
    assert "ERROR:" in output
    assert "review build identity is not valid JSON" in output


def test_unsupported_digest_format_blocks(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    review_payload = _build_identity(manifest_payload)
    review_payload["artifact_digest"] = "e" * 64

    decision = _decision(manifest_payload, review_payload=review_payload)

    assert decision["decision"] == "BLOCK"
    assert "unsupported_digest_format" in decision["reason_codes"]


def test_output_json_is_deterministic(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    decision = _decision(manifest_payload)
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    build_equivalence.write_decision(first_path, decision)
    build_equivalence.write_decision(second_path, decision)

    assert first_path.read_bytes() == second_path.read_bytes()
    assert first_path.read_text(encoding="utf-8").endswith("\n")


def test_reason_code_ordering_is_deterministic(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    production_payload = _build_identity(
        manifest_payload,
        artifact_digest="sha256:" + ("f" * 64),
    )
    production_payload["build_identity"]["git_sha"] = "other-sha"
    production_payload["release_manifest_hash"] = "1" * 64

    decision = _decision(manifest_payload, production_payload=production_payload)

    assert decision["reason_codes"] == [
        "git_sha_mismatch",
        "review_build_digest_mismatch",
        "release_manifest_hash_mismatch",
    ]


def test_optional_identity_mismatch_blocks(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    production_payload = _build_identity(manifest_payload)
    production_payload["ml_identity"] = dict(production_payload["ml_identity"])
    production_payload["ml_identity"]["rag_gate_result_hash"] = "9" * 64

    decision = _decision(manifest_payload, production_payload=production_payload)

    assert decision["decision"] == "BLOCK"
    assert "ml_identity_mismatch" in decision["reason_codes"]


def test_manifest_identity_snapshots_are_required_for_equivalence(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    review_payload = _build_identity(manifest_payload, include_optional_groups=False)
    production_payload = _build_identity(manifest_payload, include_optional_groups=False)

    decision = _decision(
        manifest_payload,
        review_payload=review_payload,
        production_payload=production_payload,
    )

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == [
        "reviewer_identity_mismatch",
        "ml_identity_mismatch",
        "supply_chain_identity_mismatch",
    ]


def test_attestation_not_verified_blocks(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path, attestation_status="PENDING")

    decision = _decision(manifest_payload)

    assert decision["decision"] == "BLOCK"
    assert "attestation_not_verified" in decision["reason_codes"]


def test_schema_file_matches_emitted_payload_shape(tmp_path: Path) -> None:
    manifest_payload = _build_manifest(tmp_path)
    decision = _decision(manifest_payload)
    schema = json.loads(
        (REPO_ROOT / "docs/release/BUILD_EQUIVALENCE_CONTRACT.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert set(schema["required"]) <= set(decision)
    assert decision["schema_version"] == schema["properties"]["schema_version"]["const"]
    assert decision["hash_algorithm"] == schema["properties"]["hash_algorithm"]["const"]
    assert decision["canonicalization"] == schema["properties"]["canonicalization"]["const"]


def test_cli_direct_invocation_help() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/release/build_equivalence.py", "--help"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()


def test_ledger_release_control_plane_state_is_reconciled() -> None:
    ledger_text = (REPO_ROOT / "docs/roadmap/BACKLOG_LEDGER.md").read_text(encoding="utf-8")

    assert "PR-3 merged in PR #1605" in ledger_text
    assert "PR-4 merged in PR #1679 on 2026-05-06" in ledger_text
    assert "PR-5 is active on branch `release/release-control-plane-pr5-ci-gates`" in ledger_text
    assert (
        "Future protected upload and App Store Connect execution remain out of scope" in ledger_text
    )
    assert "not production-ready" in ledger_text
