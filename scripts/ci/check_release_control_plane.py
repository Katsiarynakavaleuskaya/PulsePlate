#!/usr/bin/env python3
"""Validate release-control-plane evidence before release decisions."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    # Support direct invocation from repository root:
    # `python3 scripts/ci/check_release_control_plane.py ...`
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.release import build_equivalence
from scripts.release import release_manifest

SCHEMA_VERSION = "release-control-plane-ci-gate.v1"
ALLOW_DECISION = "ALLOW"
BLOCK_DECISION = "BLOCK"
TOOL_VERSION = SCHEMA_VERSION
ALLOWED_EVIDENCE_PATH_PREFIXES = ("artifacts/",)

REASON_ORDER = {
    "missing_release_manifest": 10,
    "malformed_release_manifest": 20,
    "invalid_release_manifest": 30,
    "release_manifest_block": 40,
    "missing_rag_gate_result": 50,
    "malformed_rag_gate_result": 60,
    "invalid_rag_gate_result": 70,
    "rag_gate_result_not_pass": 80,
    "missing_build_equivalence": 90,
    "malformed_build_equivalence": 100,
    "invalid_build_equivalence": 110,
    "build_equivalence_not_equivalent": 120,
    "missing_sbom_digest": 130,
    "missing_provenance_digest": 140,
    "attestation_not_verified": 150,
    "unsupported_digest_format": 160,
    "release_manifest_hash_mismatch": 170,
    "git_sha_mismatch": 180,
    "build_identity_mismatch": 190,
    "evidence_path_outside_allowed_artifacts": 200,
}


@dataclass(frozen=True)
class Finding:
    """One stable release-control-plane gate finding."""

    field: str
    reason_code: str
    detail: Any = None

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "field": self.field,
            "reason_code": self.reason_code,
        }
        if self.detail is not None:
            payload["detail"] = self.detail
        return payload


def _load_evidence(
    path: Path, *, missing_reason: str, malformed_reason: str
) -> tuple[dict[str, Any] | None, list[Finding]]:
    findings: list[Finding] = []
    if not path.exists():
        findings.append(Finding(str(path), missing_reason))
        return None, findings
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        findings.append(Finding(str(path), malformed_reason, str(exc)))
        return None, findings
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        findings.append(Finding(str(path), malformed_reason, str(exc)))
        return None, findings
    if not isinstance(payload, dict):
        findings.append(
            Finding(str(path), malformed_reason, "top-level JSON value must be an object")
        )
        return None, findings
    return payload, findings


def _stable_reason_codes(findings: list[Finding]) -> list[str]:
    return sorted(
        {finding.reason_code for finding in findings},
        key=lambda reason: (REASON_ORDER.get(reason, 10_000), reason),
    )


def _stable_findings(findings: list[Finding]) -> list[dict[str, Any]]:
    return [
        finding.as_payload()
        for finding in sorted(
            findings,
            key=lambda item: (REASON_ORDER.get(item.reason_code, 10_000), item.field),
        )
    ]


def _sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        digest = release_manifest.sha256_lower_hex(path.read_bytes())
    except OSError:
        return None
    if not isinstance(digest, str):
        return None
    return digest


def _artifact_entry(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "sha256": _sha256_file(path),
    }


def _validate_release_manifest(payload: dict[str, Any]) -> list[Finding]:
    findings = [
        Finding("release_manifest", "invalid_release_manifest", error)
        for error in release_manifest.validate_manifest_payload(payload)
    ]
    if payload.get("release_decision") != release_manifest.ALLOW_DECISION:
        findings.append(
            Finding(
                "release_manifest.release_decision",
                "release_manifest_block",
                payload.get("release_decision"),
            )
        )
    supply_chain_identity = payload.get("supply_chain_identity")
    if not isinstance(supply_chain_identity, dict):
        return findings

    sbom_digest = supply_chain_identity.get("sbom_digest")
    provenance_digest = supply_chain_identity.get("provenance_digest")
    if sbom_digest is None:
        findings.append(Finding("supply_chain_identity.sbom_digest", "missing_sbom_digest"))
    elif not isinstance(sbom_digest, str) or not release_manifest.OCI_SHA256_DIGEST_RE.fullmatch(
        sbom_digest
    ):
        findings.append(
            Finding("supply_chain_identity.sbom_digest", "unsupported_digest_format", sbom_digest)
        )
    if provenance_digest is None:
        findings.append(
            Finding("supply_chain_identity.provenance_digest", "missing_provenance_digest")
        )
    elif not isinstance(
        provenance_digest, str
    ) or not release_manifest.OCI_SHA256_DIGEST_RE.fullmatch(provenance_digest):
        findings.append(
            Finding(
                "supply_chain_identity.provenance_digest",
                "unsupported_digest_format",
                provenance_digest,
            )
        )
    if (
        supply_chain_identity.get("attestation_status")
        != release_manifest.VERIFIED_ATTESTATION_STATUS
    ):
        findings.append(
            Finding(
                "supply_chain_identity.attestation_status",
                "attestation_not_verified",
                supply_chain_identity.get("attestation_status"),
            )
        )
    return findings


def _validate_rag_gate_result(payload: dict[str, Any]) -> list[Finding]:
    findings = [
        Finding("rag_gate_result", "invalid_rag_gate_result", error)
        for error in release_manifest._validate_rag_gate_result(payload)  # noqa: SLF001
    ]
    if any("hash" in finding.detail for finding in findings if isinstance(finding.detail, str)):
        findings.append(Finding("rag_gate_result", "unsupported_digest_format"))
    if payload.get("release_decision") != "PASS":
        findings.append(
            Finding(
                "rag_gate_result.release_decision",
                "rag_gate_result_not_pass",
                payload.get("release_decision"),
            )
        )
    findings.extend(
        _validate_allowed_artifact_paths(
            payload.get("source_artifacts"),
            field_name="rag_gate_result.source_artifacts",
        )
    )
    return findings


def _validate_build_equivalence_result(payload: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if payload.get("schema_version") != build_equivalence.SCHEMA_VERSION:
        findings.append(
            Finding(
                "build_equivalence.schema_version",
                "invalid_build_equivalence",
                payload.get("schema_version"),
            )
        )
    if payload.get("hash_algorithm") != release_manifest.HASH_ALGORITHM:
        findings.append(Finding("build_equivalence.hash_algorithm", "invalid_build_equivalence"))
    if payload.get("canonicalization") != release_manifest.CANONICALIZATION:
        findings.append(Finding("build_equivalence.canonicalization", "invalid_build_equivalence"))

    manifest_hash = payload.get("release_manifest_hash")
    if not isinstance(manifest_hash, str) or not release_manifest.SHA256_HEX_RE.fullmatch(
        manifest_hash
    ):
        findings.append(
            Finding(
                "build_equivalence.release_manifest_hash",
                "unsupported_digest_format",
                manifest_hash,
            )
        )
    reason_codes = payload.get("reason_codes")
    if not isinstance(reason_codes, list) or reason_codes != sorted(
        reason_codes,
        key=lambda reason: (
            build_equivalence.REASON_ORDER.get(str(reason), 10_000),
            str(reason),
        ),
    ):
        findings.append(Finding("build_equivalence.reason_codes", "invalid_build_equivalence"))

    if payload.get("decision") != build_equivalence.EQUIVALENT_DECISION:
        findings.append(
            Finding(
                "build_equivalence.decision",
                "build_equivalence_not_equivalent",
                payload.get("decision"),
            )
        )
        mismatch_details = payload.get("mismatch_details")
        if isinstance(mismatch_details, list):
            if any(
                isinstance(item, dict) and str(item.get("field", "")).startswith("build_identity.")
                for item in mismatch_details
            ):
                findings.append(
                    Finding("build_equivalence.mismatch_details", "build_identity_mismatch")
                )
    return findings


def _validate_allowed_artifact_paths(entries: Any, *, field_name: str) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(entries, list):
        return findings
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        path_value = entry.get("path")
        if not isinstance(path_value, str):
            continue
        if Path(path_value).is_absolute() or not path_value.startswith(
            ALLOWED_EVIDENCE_PATH_PREFIXES
        ):
            findings.append(
                Finding(
                    f"{field_name}[{index}].path",
                    "evidence_path_outside_allowed_artifacts",
                    path_value,
                )
            )
    return findings


def _cross_evidence_findings(
    *,
    manifest_payload: dict[str, Any] | None,
    rag_payload: dict[str, Any] | None,
    build_equivalence_payload: dict[str, Any] | None,
) -> list[Finding]:
    findings: list[Finding] = []
    if manifest_payload is None:
        return findings

    manifest_hash = manifest_payload.get("release_manifest_hash")
    if build_equivalence_payload is not None:
        build_manifest_hash = build_equivalence_payload.get("release_manifest_hash")
        if manifest_hash != build_manifest_hash:
            findings.append(
                Finding(
                    "build_equivalence.release_manifest_hash",
                    "release_manifest_hash_mismatch",
                    {"build_equivalence": build_manifest_hash, "release_manifest": manifest_hash},
                )
            )

    ml_identity = manifest_payload.get("ml_identity")
    if isinstance(ml_identity, dict):
        findings.extend(
            _validate_allowed_artifact_paths(
                ml_identity.get("source_artifacts"),
                field_name="release_manifest.ml_identity.source_artifacts",
            )
        )

    if rag_payload is None or not isinstance(ml_identity, dict):
        return findings

    hash_pairs = (
        ("ml_identity.rag_gate_result_hash", "rag_gate_result_hash"),
        ("ml_identity.eval_artifact_hash", "eval_artifact_hash"),
    )
    for manifest_field, rag_field in hash_pairs:
        manifest_value = ml_identity.get(manifest_field.split(".")[-1])
        rag_value = rag_payload.get(rag_field)
        if manifest_value != rag_value:
            findings.append(
                Finding(
                    manifest_field,
                    "release_manifest_hash_mismatch",
                    {"rag_gate_result": rag_value, "release_manifest": manifest_value},
                )
            )
    if ml_identity.get("release_decision") != rag_payload.get("release_decision"):
        findings.append(
            Finding(
                "ml_identity.release_decision",
                "rag_gate_result_not_pass",
                {
                    "rag_gate_result": rag_payload.get("release_decision"),
                    "release_manifest": ml_identity.get("release_decision"),
                },
            )
        )

    manifest_build = manifest_payload.get("build_identity")
    if isinstance(manifest_build, dict) and manifest_build.get("git_sha") != rag_payload.get(
        "git_sha"
    ):
        findings.append(
            Finding(
                "build_identity.git_sha",
                "git_sha_mismatch",
                {
                    "rag_gate_result": rag_payload.get("git_sha"),
                    "release_manifest": manifest_build.get("git_sha"),
                },
            )
        )
    return findings


def build_release_control_plane_decision(
    *,
    release_manifest_payload: dict[str, Any] | None,
    rag_gate_result_payload: dict[str, Any] | None,
    build_equivalence_payload: dict[str, Any] | None,
    release_manifest_path: Path,
    rag_gate_result_path: Path,
    build_equivalence_path: Path,
    load_findings: list[Finding] | None = None,
) -> dict[str, Any]:
    """Return a deterministic fail-closed release-control-plane decision."""

    findings = list(load_findings or [])
    if release_manifest_payload is not None:
        findings.extend(_validate_release_manifest(release_manifest_payload))
    if rag_gate_result_payload is not None:
        findings.extend(_validate_rag_gate_result(rag_gate_result_payload))
    if build_equivalence_payload is not None:
        findings.extend(_validate_build_equivalence_result(build_equivalence_payload))
    findings.extend(
        _cross_evidence_findings(
            manifest_payload=release_manifest_payload,
            rag_payload=rag_gate_result_payload,
            build_equivalence_payload=build_equivalence_payload,
        )
    )

    reason_codes = _stable_reason_codes(findings)
    manifest_hash = None
    if release_manifest_payload is not None:
        value = release_manifest_payload.get("release_manifest_hash")
        if isinstance(value, str) and release_manifest.SHA256_HEX_RE.fullmatch(value):
            manifest_hash = value

    supply_chain_identity = {}
    if release_manifest_payload is not None and isinstance(
        release_manifest_payload.get("supply_chain_identity"), dict
    ):
        supply_chain_identity = release_manifest_payload["supply_chain_identity"]

    return {
        "schema_version": SCHEMA_VERSION,
        "hash_algorithm": release_manifest.HASH_ALGORITHM,
        "canonicalization": release_manifest.CANONICALIZATION,
        "decision": BLOCK_DECISION if reason_codes else ALLOW_DECISION,
        "reason_codes": reason_codes,
        "mismatch_details": _stable_findings(findings),
        "checked_artifacts": {
            "release_manifest": _artifact_entry(release_manifest_path),
            "rag_gate_result": _artifact_entry(rag_gate_result_path),
            "build_equivalence": _artifact_entry(build_equivalence_path),
        },
        "evidence_hashes": {
            "release_manifest": _sha256_file(release_manifest_path),
            "rag_gate_result": _sha256_file(rag_gate_result_path),
            "build_equivalence": _sha256_file(build_equivalence_path),
        },
        "evidence_digests": {
            "sbom_digest": supply_chain_identity.get("sbom_digest"),
            "provenance_digest": supply_chain_identity.get("provenance_digest"),
        },
        "release_manifest_hash": manifest_hash,
        "build_equivalence_decision": (build_equivalence_payload or {}).get("decision"),
        "rag_gate_decision": (rag_gate_result_payload or {}).get("release_decision"),
        "attestation_status": supply_chain_identity.get("attestation_status"),
        "tool_version": TOOL_VERSION,
    }


def check_release_control_plane_files(
    *,
    release_manifest_path: Path,
    rag_gate_result_path: Path,
    build_equivalence_path: Path,
) -> dict[str, Any]:
    """Load evidence files and return the deterministic CI gate payload."""

    manifest_payload, manifest_findings = _load_evidence(
        release_manifest_path,
        missing_reason="missing_release_manifest",
        malformed_reason="malformed_release_manifest",
    )
    rag_payload, rag_findings = _load_evidence(
        rag_gate_result_path,
        missing_reason="missing_rag_gate_result",
        malformed_reason="malformed_rag_gate_result",
    )
    build_payload, build_findings = _load_evidence(
        build_equivalence_path,
        missing_reason="missing_build_equivalence",
        malformed_reason="malformed_build_equivalence",
    )
    return build_release_control_plane_decision(
        release_manifest_payload=manifest_payload,
        rag_gate_result_payload=rag_payload,
        build_equivalence_payload=build_payload,
        release_manifest_path=release_manifest_path,
        rag_gate_result_path=rag_gate_result_path,
        build_equivalence_path=build_equivalence_path,
        load_findings=[*manifest_findings, *rag_findings, *build_findings],
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write stable JSON with a trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    """Write a stable Markdown summary for CI artifacts."""

    lines = [
        "# Release Control Plane CI Gate",
        "",
        f"- Decision: `{payload['decision']}`",
        f"- Release manifest hash: `{payload.get('release_manifest_hash')}`",
        f"- RAG gate decision: `{payload.get('rag_gate_decision')}`",
        f"- Build equivalence decision: `{payload.get('build_equivalence_decision')}`",
        f"- Attestation status: `{payload.get('attestation_status')}`",
        "",
        "## Reason Codes",
        "",
    ]
    reason_codes = payload.get("reason_codes", [])
    if reason_codes:
        lines.extend(f"- `{reason_code}`" for reason_code in reason_codes)
    else:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-manifest", type=Path, required=True)
    parser.add_argument("--rag-gate-result", type=Path, required=True)
    parser.add_argument("--build-equivalence", type=Path, required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--markdown-out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    decision = check_release_control_plane_files(
        release_manifest_path=args.release_manifest,
        rag_gate_result_path=args.rag_gate_result,
        build_equivalence_path=args.build_equivalence,
    )
    write_json(args.json_out, decision)
    if args.markdown_out:
        write_markdown(args.markdown_out, decision)
    if decision["decision"] == ALLOW_DECISION:
        print(f"ALLOW: release-control-plane evidence passed: {args.json_out}")
        return 0
    print(f"BLOCK: release-control-plane evidence failed: {args.json_out}")
    for reason_code in decision["reason_codes"]:
        print(f"REASON: {reason_code}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
