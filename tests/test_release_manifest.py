from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.release import release_manifest
from scripts.release import reviewer_packet_hashes

REPO_ROOT = Path(__file__).resolve().parents[1]
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
OCI_DIGEST = "sha256:" + ("a" * 64)
PROVENANCE_DIGEST = "sha256:" + ("b" * 64)
TEST_GIT_SHA = "git-sha-for-release-manifest-tests"


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


def _rag_payload(*, release_decision: str = "PASS") -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "release-rag-gate-result.v1",
        "hash_algorithm": "sha256",
        "canonicalization": "json-sorted-compact-utf8-single-trailing-newline",
        "eval_artifact_hash": "c" * 64,
        "experiment_id": "unit-test",
        "timestamp": "2026-04-30T00:00:00Z",
        "release_decision": release_decision,
        "gate_checks": {"answer_precision_min": release_decision == "PASS"},
        "threshold_results": [],
        "strict_violations": [] if release_decision == "PASS" else ["answer_precision_min"],
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


def _write_rag_gate_result(repo_root: Path, *, release_decision: str = "PASS") -> Path:
    rag_path = repo_root / "artifacts/rag_eval/unit-test/rag_gate_result.json"
    rag_path.parent.mkdir(parents=True, exist_ok=True)
    rag_path.write_text(
        json.dumps(_rag_payload(release_decision=release_decision), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return rag_path


def _build_manifest(repo_root: Path, *, rag_decision: str = "PASS") -> dict[str, object]:
    _write_metadata_pack(repo_root)
    rag_path = _write_rag_gate_result(repo_root, release_decision=rag_decision)
    return release_manifest.build_manifest_payload(
        repo_root=repo_root,
        git_sha=TEST_GIT_SHA,
        ios_build_number="100",
        marketing_version="1.0",
        bundle_id="app.pulseplate.PulsePlate",
        rag_gate_result_path=rag_path,
        sbom_digest=OCI_DIGEST,
        provenance_digest=PROVENANCE_DIGEST,
        attestation_status="VERIFIED",
    )


def _rehash_manifest(payload: dict[str, object]) -> dict[str, object]:
    updated = dict(payload)
    updated.pop("release_manifest_hash", None)
    updated["release_manifest_hash"] = release_manifest.sha256_lower_hex(
        release_manifest.canonical_json_bytes(updated)
    )
    return updated


def test_build_manifest_emits_schema_hashes_and_identity_groups(tmp_path: Path) -> None:
    payload = _build_manifest(tmp_path)

    assert payload["schema_version"] == "release-manifest.v1"
    assert payload["hash_algorithm"] == "sha256"
    assert payload["canonicalization"] == "json-sorted-compact-utf8-single-trailing-newline"
    assert HASH_RE.fullmatch(str(payload["release_manifest_hash"]))
    assert payload["release_decision"] == "ALLOW"
    assert payload["decision_reasons"] == []

    assert payload["build_identity"]["bundle_id"] == "app.pulseplate.PulsePlate"
    assert HASH_RE.fullmatch(payload["reviewer_identity"]["reviewer_notes_hash"])
    assert HASH_RE.fullmatch(payload["reviewer_identity"]["appstore_metadata_hash"])
    assert HASH_RE.fullmatch(payload["ml_identity"]["rag_gate_result_hash"])
    assert HASH_RE.fullmatch(payload["ml_identity"]["eval_artifact_hash"])
    assert payload["supply_chain_identity"]["attestation_status"] == "VERIFIED"


def test_manifest_self_hash_is_stable_and_changes_on_identity_change(tmp_path: Path) -> None:
    first = _build_manifest(tmp_path)
    second = _build_manifest(tmp_path)

    assert second["release_manifest_hash"] == first["release_manifest_hash"]

    changed = dict(first)
    changed["build_identity"] = dict(first["build_identity"])
    changed["build_identity"]["ios_build_number"] = "101"
    changed = _rehash_manifest(changed)

    assert changed["release_manifest_hash"] != first["release_manifest_hash"]


def test_validate_manifest_payload_accepts_valid_manifest(tmp_path: Path) -> None:
    payload = _build_manifest(tmp_path)

    assert release_manifest.validate_manifest_payload(payload) == []


def test_validate_manifest_payload_fails_closed_on_missing_identity_group(tmp_path: Path) -> None:
    payload = _build_manifest(tmp_path)
    del payload["reviewer_identity"]
    payload = _rehash_manifest(payload)

    errors = release_manifest.validate_manifest_payload(payload)

    assert "reviewer_identity must be an object." in errors


def test_rag_no_go_blocks_release_with_reason(tmp_path: Path) -> None:
    payload = _build_manifest(tmp_path, rag_decision="NO-GO")

    assert payload["release_decision"] == "BLOCK"
    assert payload["decision_reasons"] == ["rag_gate_result_not_pass"]
    assert release_manifest.validate_manifest_payload(payload) == []


def test_invalid_supply_chain_digest_blocks_release(tmp_path: Path) -> None:
    payload = _build_manifest(tmp_path)
    payload["supply_chain_identity"] = dict(payload["supply_chain_identity"])
    payload["supply_chain_identity"]["sbom_digest"] = "a" * 64
    payload["release_decision"] = "BLOCK"
    payload["decision_reasons"] = ["invalid_sbom_digest"]
    payload = _rehash_manifest(payload)

    errors = release_manifest.validate_manifest_payload(payload)

    assert "sbom_digest must use sha256:<64 lowercase hex> format." in errors


def test_invalid_provenance_digest_blocks_release(tmp_path: Path) -> None:
    payload = _build_manifest(tmp_path)
    payload["supply_chain_identity"] = dict(payload["supply_chain_identity"])
    payload["supply_chain_identity"]["provenance_digest"] = "b" * 64
    payload["release_decision"] = "BLOCK"
    payload["decision_reasons"] = ["invalid_provenance_digest"]
    payload = _rehash_manifest(payload)

    errors = release_manifest.validate_manifest_payload(payload)

    assert "provenance_digest must use sha256:<64 lowercase hex> format." in errors


def test_unverified_attestation_blocks_release(tmp_path: Path) -> None:
    _write_metadata_pack(tmp_path)
    rag_path = _write_rag_gate_result(tmp_path)

    payload = release_manifest.build_manifest_payload(
        repo_root=tmp_path,
        git_sha=TEST_GIT_SHA,
        ios_build_number="100",
        marketing_version="1.0",
        bundle_id="app.pulseplate.PulsePlate",
        rag_gate_result_path=rag_path,
        sbom_digest=OCI_DIGEST,
        provenance_digest=PROVENANCE_DIGEST,
        attestation_status="PENDING",
    )

    assert payload["release_decision"] == "BLOCK"
    assert payload["decision_reasons"] == ["attestation_not_verified"]
    assert release_manifest.validate_manifest_payload(payload) == []


def test_absolute_source_artifact_path_is_rejected(tmp_path: Path) -> None:
    payload = _build_manifest(tmp_path)
    payload["ml_identity"] = dict(payload["ml_identity"])
    payload["ml_identity"]["source_artifacts"] = [
        {
            "kind": "rag_gate_result",
            "path": str(tmp_path / "rag_gate_result.json"),
            "hash": "d" * 64,
        }
    ]
    payload = _rehash_manifest(payload)

    errors = release_manifest.validate_manifest_payload(payload)

    assert any(
        "ml_identity.source_artifacts[0].path must not be absolute" in error for error in errors
    )


def test_missing_source_artifacts_are_rejected_even_with_valid_self_hash(tmp_path: Path) -> None:
    payload = _build_manifest(tmp_path)
    payload["reviewer_identity"] = dict(payload["reviewer_identity"])
    del payload["reviewer_identity"]["source_artifacts"]
    payload = _rehash_manifest(payload)

    errors = release_manifest.validate_manifest_payload(payload)

    assert "reviewer_identity.source_artifacts is required." in errors


def test_invalid_source_artifact_kind_is_rejected(tmp_path: Path) -> None:
    payload = _build_manifest(tmp_path)
    payload["ml_identity"] = dict(payload["ml_identity"])
    payload["ml_identity"]["source_artifacts"] = [
        {
            "path": "artifacts/rag_eval/unit-test/rag_gate_result.json",
            "hash": "d" * 64,
        }
    ]
    payload = _rehash_manifest(payload)

    errors = release_manifest.validate_manifest_payload(payload)

    assert any(
        "ml_identity.source_artifacts[0].kind must be a non-empty lowercase artifact kind." in error
        for error in errors
    )


def test_rag_gate_result_metadata_is_required(tmp_path: Path) -> None:
    _write_metadata_pack(tmp_path)
    rag_payload = _rag_payload()
    del rag_payload["hash_algorithm"]
    rag_payload["canonicalization"] = "json-unsorted"
    del rag_payload["source_artifacts"]
    rag_payload["rag_gate_result_hash"] = release_manifest.sha256_lower_hex(
        release_manifest.canonical_json_bytes(
            {key: value for key, value in rag_payload.items() if key != "rag_gate_result_hash"}
        )
    )
    rag_path = tmp_path / "artifacts/rag_eval/unit-test/rag_gate_result.json"
    rag_path.parent.mkdir(parents=True, exist_ok=True)
    rag_path.write_text(json.dumps(rag_payload, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(release_manifest.ReleaseManifestError) as exc_info:
        release_manifest.build_manifest_payload(
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

    error_text = str(exc_info.value)
    assert "rag_gate_result.hash_algorithm must be sha256" in error_text
    assert "rag_gate_result.canonicalization must be" in error_text
    assert "rag_gate_result.source_artifacts is required" in error_text


def test_schema_file_matches_emitted_payload_shape(tmp_path: Path) -> None:
    payload = _build_manifest(tmp_path)
    schema = json.loads(
        (REPO_ROOT / "docs/release/RELEASE_MANIFEST_CONTRACT.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert set(schema["required"]) <= set(payload)
    assert payload["schema_version"] == schema["properties"]["schema_version"]["const"]
    assert payload["hash_algorithm"] == schema["properties"]["hash_algorithm"]["const"]
    assert payload["canonicalization"] == schema["properties"]["canonicalization"]["const"]


def test_cli_generate_and_validate_smoke(tmp_path: Path, capsys) -> None:
    _write_metadata_pack(tmp_path)
    rag_path = _write_rag_gate_result(tmp_path)
    manifest_path = tmp_path / "release_manifest.json"

    generate_status = release_manifest.main(
        [
            "generate",
            "--repo-root",
            str(tmp_path),
            "--git-sha",
            TEST_GIT_SHA,
            "--ios-build-number",
            "100",
            "--marketing-version",
            "1.0",
            "--bundle-id",
            "app.pulseplate.PulsePlate",
            "--rag-gate-result",
            str(rag_path),
            "--sbom-digest",
            OCI_DIGEST,
            "--provenance-digest",
            PROVENANCE_DIGEST,
            "--attestation-status",
            "VERIFIED",
            "--output",
            str(manifest_path),
        ]
    )
    validate_status = release_manifest.main(["validate", "--manifest", str(manifest_path)])

    output = capsys.readouterr().out
    assert generate_status == 0
    assert validate_status == 0
    assert "Wrote release manifest" in output
    assert "PASS: release manifest is valid" in output


def test_cli_validate_missing_manifest_uses_controlled_error(tmp_path: Path, capsys) -> None:
    missing_path = tmp_path / "missing_release_manifest.json"

    status = release_manifest.main(["validate", "--manifest", str(missing_path)])

    output = capsys.readouterr().out
    assert status == 1
    assert "ERROR:" in output
    assert "is not readable" in output


def test_cli_validate_invalid_utf8_manifest_uses_controlled_error(tmp_path: Path, capsys) -> None:
    manifest_path = tmp_path / "invalid_utf8_manifest.json"
    manifest_path.write_bytes(b"\xff\xfe")

    status = release_manifest.main(["validate", "--manifest", str(manifest_path)])

    output = capsys.readouterr().out
    assert status == 1
    assert "ERROR:" in output
    assert "is not readable" in output


def test_missing_reviewer_artifacts_use_controlled_error(tmp_path: Path, capsys) -> None:
    rag_path = _write_rag_gate_result(tmp_path)

    status = release_manifest.main(
        [
            "generate",
            "--repo-root",
            str(tmp_path),
            "--git-sha",
            TEST_GIT_SHA,
            "--ios-build-number",
            "100",
            "--marketing-version",
            "1.0",
            "--bundle-id",
            "app.pulseplate.PulsePlate",
            "--rag-gate-result",
            str(rag_path),
            "--sbom-digest",
            OCI_DIGEST,
            "--provenance-digest",
            PROVENANCE_DIGEST,
            "--attestation-status",
            "VERIFIED",
            "--output",
            str(tmp_path / "release_manifest.json"),
        ]
    )

    output = capsys.readouterr().out
    assert status == 1
    assert "ERROR:" in output
    assert "Unable to build reviewer identity" in output


def test_cli_generate_missing_rag_gate_result_uses_controlled_error(tmp_path: Path, capsys) -> None:
    _write_metadata_pack(tmp_path)
    missing_rag_path = tmp_path / "artifacts/rag_eval/missing/rag_gate_result.json"

    status = release_manifest.main(
        [
            "generate",
            "--repo-root",
            str(tmp_path),
            "--git-sha",
            TEST_GIT_SHA,
            "--ios-build-number",
            "100",
            "--marketing-version",
            "1.0",
            "--bundle-id",
            "app.pulseplate.PulsePlate",
            "--rag-gate-result",
            str(missing_rag_path),
            "--sbom-digest",
            OCI_DIGEST,
            "--provenance-digest",
            PROVENANCE_DIGEST,
            "--attestation-status",
            "VERIFIED",
            "--output",
            str(tmp_path / "release_manifest.json"),
        ]
    )

    output = capsys.readouterr().out
    assert status == 1
    assert "ERROR:" in output
    assert "is not readable" in output


# ---------------------------------------------------------------------------
# Invocation-mode tests (direct file + module)
# Policy: AGENTS.md:1781 — scripts/ may use path bootstrap for standalone CLI
# ---------------------------------------------------------------------------


def test_release_manifest_direct_invocation_help() -> None:
    """Direct file invocation must work from repo root."""
    result = subprocess.run(
        [sys.executable, "scripts/release/release_manifest.py", "--help"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()


def test_release_manifest_module_invocation_help() -> None:
    """Module invocation must still work."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.release.release_manifest", "--help"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()
