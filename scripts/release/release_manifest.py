#!/usr/bin/env python3
"""Generate and validate PulsePlate release-control-plane manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    # Support direct invocation from repository root:
    # `python3 scripts/release/release_manifest.py ...`
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.release import reviewer_packet_hashes

SCHEMA_VERSION = "release-manifest.v1"
HASH_ALGORITHM = "sha256"
CANONICALIZATION = "json-sorted-compact-utf8-single-trailing-newline"
RAG_GATE_SCHEMA_VERSION = "release-rag-gate-result.v1"
REVIEWER_SCHEMA_VERSION = "release-reviewer-packet-hashes.v1"
ALLOW_DECISION = "ALLOW"
BLOCK_DECISION = "BLOCK"
VERIFIED_ATTESTATION_STATUS = "VERIFIED"
ATTESTATION_STATUSES = frozenset({"VERIFIED", "FAILED", "MISSING", "PENDING"})
SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
OCI_SHA256_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SOURCE_ARTIFACT_KIND_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")


class ReleaseManifestError(ValueError):
    """Raised when release manifest generation or validation fails closed."""


def canonical_json_bytes(payload: Any) -> bytes:
    """Return canonical JSON bytes for release-control-plane hashing."""

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{serialized}\n".encode("utf-8")


def sha256_lower_hex(payload: bytes) -> str:
    """Return SHA-256 lowercase hexadecimal without a prefix."""

    return hashlib.new(HASH_ALGORITHM, payload).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReleaseManifestError(f"{path} is not readable: {exc}") from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ReleaseManifestError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReleaseManifestError(f"{path} must contain a JSON object.")
    return payload


def _repo_relative_path(path: Path, *, repo_root: Path) -> str:
    resolved_path = path.resolve()
    resolved_root = repo_root.resolve()
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError as exc:
        raise ReleaseManifestError(f"Artifact path must stay under repo root: {path}") from exc


def _artifact_file_hash(path: Path) -> str:
    if not path.is_file():
        raise ReleaseManifestError(f"Artifact does not exist: {path}")
    try:
        return sha256_lower_hex(path.read_bytes())
    except OSError as exc:
        raise ReleaseManifestError(f"Artifact is not readable: {path}: {exc}") from exc


def _check_sha256_hex(value: Any, field_name: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not SHA256_HEX_RE.fullmatch(value):
        errors.append(f"{field_name} must be a lowercase 64-character SHA-256 hex value.")


def _check_oci_digest(value: Any, field_name: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not OCI_SHA256_DIGEST_RE.fullmatch(value):
        errors.append(f"{field_name} must use sha256:<64 lowercase hex> format.")


def _validate_source_artifacts(
    entries: Any,
    *,
    field_name: str,
    errors: list[str],
    require_non_empty: bool = False,
) -> None:
    if not isinstance(entries, list):
        errors.append(f"{field_name} must be a list.")
        return
    if require_non_empty and not entries:
        errors.append(f"{field_name} must contain at least one artifact.")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"{field_name}[{index}] must be an object.")
            continue
        kind_value = entry.get("kind")
        if not isinstance(kind_value, str) or not SOURCE_ARTIFACT_KIND_RE.fullmatch(kind_value):
            errors.append(
                f"{field_name}[{index}].kind must be a non-empty lowercase artifact kind."
            )
        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"{field_name}[{index}].path must be a non-empty string.")
            continue
        if Path(path_value).is_absolute():
            errors.append(f"{field_name}[{index}].path must not be absolute.")
        _check_sha256_hex(entry.get("hash"), f"{field_name}[{index}].hash", errors)


def _validate_rag_gate_result(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != RAG_GATE_SCHEMA_VERSION:
        errors.append("rag_gate_result.schema_version must be release-rag-gate-result.v1.")
    if payload.get("hash_algorithm") != HASH_ALGORITHM:
        errors.append("rag_gate_result.hash_algorithm must be sha256.")
    if payload.get("canonicalization") != CANONICALIZATION:
        errors.append(f"rag_gate_result.canonicalization must be {CANONICALIZATION}.")
    _check_sha256_hex(payload.get("rag_gate_result_hash"), "rag_gate_result_hash", errors)
    _check_sha256_hex(payload.get("eval_artifact_hash"), "eval_artifact_hash", errors)
    if payload.get("release_decision") not in {"PASS", "NO-GO"}:
        errors.append("rag_gate_result.release_decision must be PASS or NO-GO.")

    self_hash = payload.get("rag_gate_result_hash")
    if isinstance(self_hash, str) and SHA256_HEX_RE.fullmatch(self_hash):
        without_self_hash = dict(payload)
        without_self_hash.pop("rag_gate_result_hash", None)
        expected_hash = sha256_lower_hex(canonical_json_bytes(without_self_hash))
        if self_hash != expected_hash:
            errors.append("rag_gate_result_hash does not match canonical payload.")

    if "source_artifacts" not in payload:
        errors.append("rag_gate_result.source_artifacts is required.")
    else:
        _validate_source_artifacts(
            payload["source_artifacts"],
            field_name="rag_gate_result.source_artifacts",
            errors=errors,
            require_non_empty=True,
        )
    return errors


def build_manifest_payload(
    *,
    repo_root: Path,
    git_sha: str,
    ios_build_number: str,
    marketing_version: str,
    bundle_id: str,
    rag_gate_result_path: Path,
    sbom_digest: str,
    provenance_digest: str,
    attestation_status: str,
) -> dict[str, Any]:
    """Build a release manifest payload with a deterministic self-hash."""

    resolved_root = repo_root.resolve()
    try:
        reviewer_identity = reviewer_packet_hashes.build_reviewer_packet_hash_contract(
            resolved_root
        )
    except (OSError, UnicodeDecodeError) as exc:
        raise ReleaseManifestError(f"Unable to build reviewer identity: {exc}") from exc
    rag_gate_result = _load_json(rag_gate_result_path)
    rag_errors = _validate_rag_gate_result(rag_gate_result)
    if rag_errors:
        raise ReleaseManifestError("; ".join(rag_errors))

    ml_identity: dict[str, Any] = {
        "schema_version": rag_gate_result["schema_version"],
        "rag_gate_result_hash": rag_gate_result["rag_gate_result_hash"],
        "eval_artifact_hash": rag_gate_result["eval_artifact_hash"],
        "release_decision": rag_gate_result["release_decision"],
        "source_artifacts": [
            {
                "kind": "rag_gate_result",
                "path": _repo_relative_path(rag_gate_result_path, repo_root=resolved_root),
                "hash": _artifact_file_hash(rag_gate_result_path),
            }
        ],
    }
    for optional_key in ("mlflow_run_id", "model_version"):
        optional_value = rag_gate_result.get(optional_key)
        if optional_value:
            ml_identity[optional_key] = optional_value

    supply_chain_identity = {
        "sbom_digest": sbom_digest,
        "provenance_digest": provenance_digest,
        "attestation_status": attestation_status,
    }
    decision_reasons = decision_reasons_for(
        ml_release_decision=rag_gate_result["release_decision"],
        supply_chain_identity=supply_chain_identity,
    )
    release_decision = BLOCK_DECISION if decision_reasons else ALLOW_DECISION

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "hash_algorithm": HASH_ALGORITHM,
        "canonicalization": CANONICALIZATION,
        "build_identity": {
            "git_sha": git_sha,
            "ios_build_number": ios_build_number,
            "marketing_version": marketing_version,
            "bundle_id": bundle_id,
        },
        "reviewer_identity": {
            "schema_version": reviewer_identity["schema_version"],
            "reviewer_notes_hash": reviewer_identity["reviewer_notes_hash"],
            "appstore_metadata_hash": reviewer_identity["appstore_metadata_hash"],
            "source_artifacts": reviewer_identity["source_artifacts"],
        },
        "ml_identity": ml_identity,
        "supply_chain_identity": supply_chain_identity,
        "release_decision": release_decision,
        "decision_reasons": decision_reasons,
    }
    payload["release_manifest_hash"] = sha256_lower_hex(canonical_json_bytes(payload))
    return payload


def decision_reasons_for(
    *,
    ml_release_decision: Any,
    supply_chain_identity: dict[str, Any],
) -> list[str]:
    """Return fail-closed release decision reasons."""

    reasons: list[str] = []
    if ml_release_decision != "PASS":
        reasons.append("rag_gate_result_not_pass")
    if supply_chain_identity.get("attestation_status") != VERIFIED_ATTESTATION_STATUS:
        reasons.append("attestation_not_verified")
    if not OCI_SHA256_DIGEST_RE.fullmatch(str(supply_chain_identity.get("sbom_digest", ""))):
        reasons.append("invalid_sbom_digest")
    if not OCI_SHA256_DIGEST_RE.fullmatch(str(supply_chain_identity.get("provenance_digest", ""))):
        reasons.append("invalid_provenance_digest")
    return reasons


def validate_manifest_payload(payload: dict[str, Any]) -> list[str]:
    """Return validation errors for a release manifest payload."""

    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be release-manifest.v1.")
    if payload.get("hash_algorithm") != HASH_ALGORITHM:
        errors.append("hash_algorithm must be sha256.")
    if payload.get("canonicalization") != CANONICALIZATION:
        errors.append(f"canonicalization must be {CANONICALIZATION}.")

    self_hash = payload.get("release_manifest_hash")
    _check_sha256_hex(self_hash, "release_manifest_hash", errors)
    if isinstance(self_hash, str) and SHA256_HEX_RE.fullmatch(self_hash):
        without_self_hash = dict(payload)
        without_self_hash.pop("release_manifest_hash", None)
        expected_hash = sha256_lower_hex(canonical_json_bytes(without_self_hash))
        if self_hash != expected_hash:
            errors.append("release_manifest_hash does not match canonical payload.")

    build_identity = payload.get("build_identity")
    if not isinstance(build_identity, dict):
        errors.append("build_identity must be an object.")
    else:
        for field_name in ("git_sha", "ios_build_number", "marketing_version", "bundle_id"):
            if (
                not isinstance(build_identity.get(field_name), str)
                or not build_identity[field_name]
            ):
                errors.append(f"build_identity.{field_name} must be a non-empty string.")

    reviewer_identity = payload.get("reviewer_identity")
    if not isinstance(reviewer_identity, dict):
        errors.append("reviewer_identity must be an object.")
    else:
        if reviewer_identity.get("schema_version") != REVIEWER_SCHEMA_VERSION:
            errors.append("reviewer_identity.schema_version is invalid.")
        _check_sha256_hex(
            reviewer_identity.get("reviewer_notes_hash"), "reviewer_notes_hash", errors
        )
        _check_sha256_hex(
            reviewer_identity.get("appstore_metadata_hash"),
            "appstore_metadata_hash",
            errors,
        )
        if "source_artifacts" not in reviewer_identity:
            errors.append("reviewer_identity.source_artifacts is required.")
        else:
            _validate_source_artifacts(
                reviewer_identity["source_artifacts"],
                field_name="reviewer_identity.source_artifacts",
                errors=errors,
                require_non_empty=True,
            )

    ml_identity = payload.get("ml_identity")
    if not isinstance(ml_identity, dict):
        errors.append("ml_identity must be an object.")
        ml_decision = None
    else:
        ml_decision = ml_identity.get("release_decision")
        if ml_identity.get("schema_version") != RAG_GATE_SCHEMA_VERSION:
            errors.append("ml_identity.schema_version is invalid.")
        _check_sha256_hex(ml_identity.get("rag_gate_result_hash"), "rag_gate_result_hash", errors)
        _check_sha256_hex(ml_identity.get("eval_artifact_hash"), "eval_artifact_hash", errors)
        if ml_decision not in {"PASS", "NO-GO"}:
            errors.append("ml_identity.release_decision must be PASS or NO-GO.")
        if "source_artifacts" not in ml_identity:
            errors.append("ml_identity.source_artifacts is required.")
        else:
            _validate_source_artifacts(
                ml_identity["source_artifacts"],
                field_name="ml_identity.source_artifacts",
                errors=errors,
                require_non_empty=True,
            )

    supply_chain_identity = payload.get("supply_chain_identity")
    if not isinstance(supply_chain_identity, dict):
        errors.append("supply_chain_identity must be an object.")
        supply_chain_identity = {}
    else:
        _check_oci_digest(supply_chain_identity.get("sbom_digest"), "sbom_digest", errors)
        _check_oci_digest(
            supply_chain_identity.get("provenance_digest"),
            "provenance_digest",
            errors,
        )
        if supply_chain_identity.get("attestation_status") not in ATTESTATION_STATUSES:
            errors.append("attestation_status must be VERIFIED, FAILED, MISSING, or PENDING.")

    expected_reasons = decision_reasons_for(
        ml_release_decision=ml_decision,
        supply_chain_identity=supply_chain_identity,
    )
    expected_decision = BLOCK_DECISION if expected_reasons else ALLOW_DECISION
    if payload.get("release_decision") != expected_decision:
        errors.append(f"release_decision must be {expected_decision}.")
    if payload.get("decision_reasons") != expected_reasons:
        errors.append("decision_reasons do not match the fail-closed decision contract.")
    return errors


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    """Write pretty JSON with stable key ordering and a trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate a release manifest JSON file.")
    generate.add_argument("--repo-root", type=Path, default=Path.cwd())
    generate.add_argument("--git-sha", required=True)
    generate.add_argument("--ios-build-number", required=True)
    generate.add_argument("--marketing-version", required=True)
    generate.add_argument("--bundle-id", required=True)
    generate.add_argument("--rag-gate-result", type=Path, required=True)
    generate.add_argument("--sbom-digest", required=True)
    generate.add_argument("--provenance-digest", required=True)
    generate.add_argument(
        "--attestation-status", required=True, choices=sorted(ATTESTATION_STATUSES)
    )
    generate.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser("validate", help="Validate a release manifest JSON file.")
    validate.add_argument("--manifest", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            payload = build_manifest_payload(
                repo_root=args.repo_root,
                git_sha=args.git_sha,
                ios_build_number=args.ios_build_number,
                marketing_version=args.marketing_version,
                bundle_id=args.bundle_id,
                rag_gate_result_path=args.rag_gate_result,
                sbom_digest=args.sbom_digest,
                provenance_digest=args.provenance_digest,
                attestation_status=args.attestation_status,
            )
            write_manifest(args.output, payload)
            print(f"Wrote release manifest: {args.output}")
            return 0

        payload = _load_json(args.manifest)
        errors = validate_manifest_payload(payload)
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print(f"PASS: release manifest is valid: {args.manifest}")
        return 0
    except ReleaseManifestError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
