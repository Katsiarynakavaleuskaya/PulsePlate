#!/usr/bin/env python3
"""Compare App Review and production-candidate build identities."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    # Support direct invocation from repository root:
    # `python3 scripts/release/build_equivalence.py ...`
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.release import release_manifest

SCHEMA_VERSION = "release-build-equivalence.v1"
BUILD_IDENTITY_SCHEMA_VERSION = "release-build-identity.v1"
EQUIVALENT_DECISION = "EQUIVALENT"
BLOCK_DECISION = "BLOCK"
TOOL_VERSION = SCHEMA_VERSION

BUILD_IDENTITY_FIELDS = (
    "git_sha",
    "bundle_id",
    "marketing_version",
    "ios_build_number",
)
OPTIONAL_IDENTITY_GROUPS = (
    "reviewer_identity",
    "ml_identity",
    "supply_chain_identity",
)
BASE_COMPARED_FIELDS = (
    "build_identity.git_sha",
    "build_identity.bundle_id",
    "build_identity.marketing_version",
    "build_identity.ios_build_number",
    "artifact_digest",
    "release_manifest_hash",
)
REASON_ORDER = {
    "missing_review_build_identity": 10,
    "missing_production_candidate_identity": 20,
    "malformed_review_build_identity": 30,
    "malformed_production_candidate_identity": 40,
    "invalid_release_manifest": 50,
    "unsupported_digest_format": 60,
    "attestation_not_verified": 70,
    "git_sha_mismatch": 80,
    "bundle_id_mismatch": 90,
    "marketing_version_mismatch": 100,
    "ios_build_number_mismatch": 110,
    "review_build_digest_mismatch": 120,
    "release_manifest_hash_mismatch": 130,
    "reviewer_identity_mismatch": 140,
    "ml_identity_mismatch": 150,
    "supply_chain_identity_mismatch": 160,
}
FIELD_REASON_CODES = {
    "git_sha": "git_sha_mismatch",
    "bundle_id": "bundle_id_mismatch",
    "marketing_version": "marketing_version_mismatch",
    "ios_build_number": "ios_build_number_mismatch",
}


class BuildEquivalenceError(ValueError):
    """Raised when build equivalence input cannot be read or parsed."""


@dataclass(frozen=True)
class Mismatch:
    """One deterministic mismatch detail."""

    field: str
    reason_code: str
    review_build: Any = None
    production_candidate: Any = None
    release_manifest: Any = None

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "field": self.field,
            "reason_code": self.reason_code,
        }
        if self.review_build is not None:
            payload["review_build"] = self.review_build
        if self.production_candidate is not None:
            payload["production_candidate"] = self.production_candidate
        if self.release_manifest is not None:
            payload["release_manifest"] = self.release_manifest
        return payload


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BuildEquivalenceError(f"{label} is not readable: {path}: {exc}") from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise BuildEquivalenceError(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BuildEquivalenceError(f"{label} must contain a JSON object: {path}")
    return payload


def _load_optional_identity_json(path: Path, *, label: str) -> dict[str, Any]:
    """Load a build identity artifact, returning empty payload when absent."""

    if not path.exists():
        return {}
    return _load_json(path, label=label)


def _stable_reason_codes(mismatches: list[Mismatch]) -> list[str]:
    reason_codes = {mismatch.reason_code for mismatch in mismatches}
    return sorted(reason_codes, key=lambda reason: (REASON_ORDER.get(reason, 10_000), reason))


def _stable_mismatch_details(mismatches: list[Mismatch]) -> list[dict[str, Any]]:
    return [
        mismatch.as_payload()
        for mismatch in sorted(
            mismatches,
            key=lambda item: (REASON_ORDER.get(item.reason_code, 10_000), item.field),
        )
    ]


def _validate_build_artifact(
    payload: dict[str, Any],
    *,
    label: str,
    source_field: str,
    missing_reason: str,
    malformed_reason: str,
) -> list[Mismatch]:
    mismatches: list[Mismatch] = []

    def _source_mismatch(field: str, reason_code: str, value: Any) -> Mismatch:
        if source_field == "review_build":
            return Mismatch(field, reason_code, review_build=value)
        return Mismatch(field, reason_code, production_candidate=value)

    if not payload:
        mismatches.append(Mismatch(label, missing_reason))
        return mismatches

    expected_metadata = {
        "schema_version": BUILD_IDENTITY_SCHEMA_VERSION,
        "hash_algorithm": release_manifest.HASH_ALGORITHM,
        "canonicalization": release_manifest.CANONICALIZATION,
    }
    for field_name, expected_value in expected_metadata.items():
        value = payload.get(field_name)
        if value is None:
            mismatches.append(Mismatch(field_name, missing_reason))
        elif value != expected_value:
            mismatches.append(
                Mismatch(
                    field_name,
                    malformed_reason,
                    **{source_field: value},
                    release_manifest=expected_value,
                )
            )

    build_identity = payload.get("build_identity")
    if not isinstance(build_identity, dict):
        mismatches.append(Mismatch("build_identity", missing_reason))
    else:
        for field_name in BUILD_IDENTITY_FIELDS:
            value = build_identity.get(field_name)
            if value is None:
                mismatches.append(Mismatch(f"build_identity.{field_name}", missing_reason))
            elif not isinstance(value, str) or not value:
                mismatches.append(
                    _source_mismatch(f"build_identity.{field_name}", malformed_reason, value)
                )

    artifact_digest = payload.get("artifact_digest")
    if artifact_digest is None:
        mismatches.append(Mismatch("artifact_digest", missing_reason))
    elif not isinstance(
        artifact_digest, str
    ) or not release_manifest.OCI_SHA256_DIGEST_RE.fullmatch(artifact_digest):
        mismatches.append(
            _source_mismatch("artifact_digest", "unsupported_digest_format", artifact_digest)
        )

    release_manifest_hash = payload.get("release_manifest_hash")
    if release_manifest_hash is None:
        mismatches.append(Mismatch("release_manifest_hash", missing_reason))
    elif not isinstance(release_manifest_hash, str) or not release_manifest.SHA256_HEX_RE.fullmatch(
        release_manifest_hash
    ):
        mismatches.append(
            _source_mismatch(
                "release_manifest_hash", "unsupported_digest_format", release_manifest_hash
            )
        )

    for group_name in OPTIONAL_IDENTITY_GROUPS:
        if group_name in payload and not isinstance(payload[group_name], dict):
            mismatches.append(_source_mismatch(group_name, malformed_reason, payload[group_name]))
    return mismatches


def _manifest_mismatches(manifest_payload: dict[str, Any]) -> list[Mismatch]:
    errors = release_manifest.validate_manifest_payload(manifest_payload)
    mismatches = [
        Mismatch("release_manifest", "invalid_release_manifest", release_manifest=error)
        for error in errors
    ]
    supply_chain_identity = manifest_payload.get("supply_chain_identity")
    if isinstance(supply_chain_identity, dict):
        if (
            supply_chain_identity.get("attestation_status")
            != release_manifest.VERIFIED_ATTESTATION_STATUS
        ):
            mismatches.append(
                Mismatch(
                    "supply_chain_identity.attestation_status",
                    "attestation_not_verified",
                    release_manifest=supply_chain_identity.get("attestation_status"),
                )
            )
    return mismatches


def _build_identity(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("build_identity")
    if isinstance(value, dict):
        return value
    return {}


def _compare_required_identity(
    *,
    review_payload: dict[str, Any],
    production_payload: dict[str, Any],
    manifest_payload: dict[str, Any],
) -> list[Mismatch]:
    mismatches: list[Mismatch] = []
    review_build = _build_identity(review_payload)
    production_build = _build_identity(production_payload)
    manifest_build = _build_identity(manifest_payload)

    for field_name in BUILD_IDENTITY_FIELDS:
        review_value = review_build.get(field_name)
        production_value = production_build.get(field_name)
        manifest_value = manifest_build.get(field_name)
        if review_value != production_value or review_value != manifest_value:
            mismatches.append(
                Mismatch(
                    f"build_identity.{field_name}",
                    FIELD_REASON_CODES[field_name],
                    review_build=review_value,
                    production_candidate=production_value,
                    release_manifest=manifest_value,
                )
            )

    review_digest = review_payload.get("artifact_digest")
    production_digest = production_payload.get("artifact_digest")
    if review_digest != production_digest:
        mismatches.append(
            Mismatch(
                "artifact_digest",
                "review_build_digest_mismatch",
                review_build=review_digest,
                production_candidate=production_digest,
            )
        )

    review_manifest_hash = review_payload.get("release_manifest_hash")
    production_manifest_hash = production_payload.get("release_manifest_hash")
    manifest_hash = manifest_payload.get("release_manifest_hash")
    if review_manifest_hash != production_manifest_hash or review_manifest_hash != manifest_hash:
        mismatches.append(
            Mismatch(
                "release_manifest_hash",
                "release_manifest_hash_mismatch",
                review_build=review_manifest_hash,
                production_candidate=production_manifest_hash,
                release_manifest=manifest_hash,
            )
        )
    return mismatches


def _compare_optional_identity_groups(
    *,
    review_payload: dict[str, Any],
    production_payload: dict[str, Any],
    manifest_payload: dict[str, Any],
) -> list[Mismatch]:
    mismatches: list[Mismatch] = []
    reason_by_group = {
        "reviewer_identity": "reviewer_identity_mismatch",
        "ml_identity": "ml_identity_mismatch",
        "supply_chain_identity": "supply_chain_identity_mismatch",
    }
    for group_name in OPTIONAL_IDENTITY_GROUPS:
        if (
            group_name not in manifest_payload
            and group_name not in review_payload
            and group_name not in production_payload
        ):
            continue
        review_value = review_payload.get(group_name)
        production_value = production_payload.get(group_name)
        manifest_value = manifest_payload.get(group_name)
        if review_value != production_value or review_value != manifest_value:
            mismatches.append(
                Mismatch(
                    group_name,
                    reason_by_group[group_name],
                    review_build=review_value,
                    production_candidate=production_value,
                    release_manifest=manifest_value,
                )
            )
    return mismatches


def build_equivalence_decision(
    *,
    review_payload: dict[str, Any],
    production_payload: dict[str, Any],
    manifest_payload: dict[str, Any],
) -> dict[str, Any]:
    """Return a deterministic build equivalence decision payload."""

    mismatches: list[Mismatch] = []
    mismatches.extend(
        _validate_build_artifact(
            review_payload,
            label="review_build_identity",
            source_field="review_build",
            missing_reason="missing_review_build_identity",
            malformed_reason="malformed_review_build_identity",
        )
    )
    mismatches.extend(
        _validate_build_artifact(
            production_payload,
            label="production_candidate_identity",
            source_field="production_candidate",
            missing_reason="missing_production_candidate_identity",
            malformed_reason="malformed_production_candidate_identity",
        )
    )
    mismatches.extend(_manifest_mismatches(manifest_payload))
    mismatches.extend(
        _compare_required_identity(
            review_payload=review_payload,
            production_payload=production_payload,
            manifest_payload=manifest_payload,
        )
    )
    mismatches.extend(
        _compare_optional_identity_groups(
            review_payload=review_payload,
            production_payload=production_payload,
            manifest_payload=manifest_payload,
        )
    )

    reason_codes = _stable_reason_codes(mismatches)
    compared_fields = list(BASE_COMPARED_FIELDS)
    for group_name in OPTIONAL_IDENTITY_GROUPS:
        if group_name in review_payload or group_name in production_payload:
            compared_fields.append(group_name)
    compared_fields = sorted(dict.fromkeys(compared_fields))

    manifest_hash = manifest_payload.get("release_manifest_hash")
    if not isinstance(manifest_hash, str) or not release_manifest.SHA256_HEX_RE.fullmatch(
        manifest_hash
    ):
        manifest_hash = "0" * 64

    return {
        "schema_version": SCHEMA_VERSION,
        "hash_algorithm": release_manifest.HASH_ALGORITHM,
        "canonicalization": release_manifest.CANONICALIZATION,
        "decision": BLOCK_DECISION if reason_codes else EQUIVALENT_DECISION,
        "reason_codes": reason_codes,
        "mismatch_details": _stable_mismatch_details(mismatches),
        "compared_fields": compared_fields,
        "release_manifest_hash": manifest_hash,
        "tool_version": TOOL_VERSION,
    }


def compare_build_files(
    *,
    review_build_path: Path,
    production_candidate_path: Path,
    release_manifest_path: Path,
) -> dict[str, Any]:
    """Load input files and return a deterministic build equivalence decision."""

    review_payload = _load_optional_identity_json(
        review_build_path,
        label="review build identity",
    )
    production_payload = _load_optional_identity_json(
        production_candidate_path,
        label="production candidate identity",
    )
    manifest_payload = _load_json(release_manifest_path, label="release manifest")
    return build_equivalence_decision(
        review_payload=review_payload,
        production_payload=production_payload,
        manifest_payload=manifest_payload,
    )


def write_decision(path: Path, payload: dict[str, Any]) -> None:
    """Write stable JSON with a trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-build", type=Path, required=True)
    parser.add_argument("--production-candidate", type=Path, required=True)
    parser.add_argument("--release-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        decision = compare_build_files(
            review_build_path=args.review_build,
            production_candidate_path=args.production_candidate,
            release_manifest_path=args.release_manifest,
        )
        write_decision(args.output, decision)
        if decision["decision"] == EQUIVALENT_DECISION:
            print(f"PASS: build identities are equivalent: {args.output}")
            return 0
        print(f"BLOCK: build identities are not equivalent: {args.output}")
        for reason_code in decision["reason_codes"]:
            print(f"REASON: {reason_code}")
        return 1
    except BuildEquivalenceError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
