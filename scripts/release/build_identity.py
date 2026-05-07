#!/usr/bin/env python3
"""Generate deterministic release build identity artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    # Support direct invocation from repository root:
    # `.venv/bin/python scripts/release/build_identity.py ...`
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.release import release_manifest

SCHEMA_VERSION = "release-build-identity.v1"
SENTINEL_OCI_SHA256_DIGEST_RE = re.compile(r"^sha256:([0-9a-f])\1{63}$")


class BuildIdentityError(ValueError):
    """Raised when build identity generation fails closed."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BuildIdentityError(f"{path} is not readable: {exc}") from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise BuildIdentityError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise BuildIdentityError(f"{path} must contain a JSON object.")
    return payload


def build_identity_payload(
    *,
    manifest_payload: dict[str, Any],
    artifact_digest: str,
) -> dict[str, Any]:
    """Return a deterministic build identity artifact derived from a manifest."""

    manifest_errors = release_manifest.validate_manifest_payload(manifest_payload)
    if manifest_errors:
        raise BuildIdentityError("; ".join(manifest_errors))
    if not release_manifest.OCI_SHA256_DIGEST_RE.fullmatch(artifact_digest):
        raise BuildIdentityError("artifact_digest must use sha256:<64 lowercase hex> format.")
    if SENTINEL_OCI_SHA256_DIGEST_RE.fullmatch(artifact_digest):
        raise BuildIdentityError("artifact_digest must not be a sentinel placeholder digest.")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "hash_algorithm": release_manifest.HASH_ALGORITHM,
        "canonicalization": release_manifest.CANONICALIZATION,
        "build_identity": dict(manifest_payload["build_identity"]),
        "artifact_digest": artifact_digest,
        "release_manifest_hash": manifest_payload["release_manifest_hash"],
    }
    for identity_group in ("reviewer_identity", "ml_identity", "supply_chain_identity"):
        if identity_group in manifest_payload:
            payload[identity_group] = manifest_payload[identity_group]
    return payload


def write_identity(path: Path, payload: dict[str, Any]) -> None:
    """Write stable JSON with sorted keys and one trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-manifest", type=Path, required=True)
    parser.add_argument("--artifact-digest", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        manifest_payload = _load_json(args.release_manifest)
        payload = build_identity_payload(
            manifest_payload=manifest_payload,
            artifact_digest=args.artifact_digest,
        )
        write_identity(args.output, payload)
        print(f"Wrote build identity: {args.output}")
        return 0
    except BuildIdentityError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
