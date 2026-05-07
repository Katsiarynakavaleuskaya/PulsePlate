#!/usr/bin/env python3
"""Validate governed release-control-plane source workflow inputs."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import PurePosixPath
from typing import Any

GIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
OCI_SHA256_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SENTINEL_SHA_RE = re.compile(r"^sha256:([0-9a-f])\1{63}$")
FORBIDDEN_TOKENS = (
    "/test/",
    "/tests/",
    "test/",
    "tests/",
    "tests/fixtures",
    "fixture",
    "fixtures",
    "sample",
    "example",
    "placeholder",
    "fake",
    "fallback",
)


class EvidenceSourceError(ValueError):
    """Raised when governed evidence source input is unsafe or malformed."""


def _has_control_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _reject_text(value: str, *, label: str) -> None:
    if not value or _has_control_character(value):
        raise EvidenceSourceError(f"{label} must be non-empty and contain no control characters.")
    lowered = value.lower().replace("\\", "/")
    if any(token in lowered for token in FORBIDDEN_TOKENS):
        raise EvidenceSourceError(
            f"{label} must not reference fixture/sample/example/placeholder/fake/fallback data."
        )


def validate_git_sha(value: str) -> str:
    """Return lowercase full git SHA or fail closed."""

    if not GIT_SHA_RE.fullmatch(value):
        raise EvidenceSourceError("git_sha must be a full 40-character hexadecimal commit SHA.")
    return value.lower()


def validate_oci_digest(value: str, *, label: str) -> str:
    """Return OCI SHA-256 digest or fail closed."""

    _reject_text(value, label=label)
    if not OCI_SHA256_DIGEST_RE.fullmatch(value):
        raise EvidenceSourceError(f"{label} must use sha256:<64 lowercase hex> format.")
    if SENTINEL_SHA_RE.fullmatch(value):
        raise EvidenceSourceError(f"{label} must not be a sentinel placeholder digest.")
    return value


def validate_artifact_name(value: str, *, label: str = "artifact_name") -> str:
    """Return an artifact name after rejecting placeholders and controls."""

    _reject_text(value, label=label)
    return value


def validate_source_payload(
    raw_json: str, *, label: str, expected_path: str | None = None
) -> dict[str, str]:
    """Validate source object JSON and return run_id/artifact_name/path."""

    if _has_control_character(raw_json):
        raise EvidenceSourceError(f"{label}_source must be single-line JSON.")
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise EvidenceSourceError(f"{label}_source must be JSON: {exc}") from exc
    required = {"run_id", "artifact_name", "path"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise EvidenceSourceError(
            f"{label}_source must contain exactly run_id, artifact_name, path."
        )

    run_id = payload["run_id"]
    artifact_name = payload["artifact_name"]
    path = payload["path"]
    for key, value in payload.items():
        if not isinstance(value, str):
            raise EvidenceSourceError(f"{label}_source.{key} must be a string.")
        _reject_text(value, label=f"{label}_source.{key}")

    if not run_id.isdigit():
        raise EvidenceSourceError(f"{label}_source.run_id must be a numeric GitHub Actions run id.")
    normalized_path = path.replace("\\", "/")
    pure_path = PurePosixPath(normalized_path)
    if (
        normalized_path.startswith("/")
        or "//" in normalized_path
        or any(part in {"", ".", ".."} for part in pure_path.parts)
    ):
        raise EvidenceSourceError(f"{label}_source.path must stay inside the downloaded artifact.")
    if expected_path is not None and normalized_path != expected_path:
        raise EvidenceSourceError(f"{label}_source.path must be exactly {expected_path}.")
    return {
        "run_id": run_id,
        "artifact_name": artifact_name,
        "path": normalized_path,
    }


def shell_env_lines(payload: dict[str, str], *, prefix: str) -> list[str]:
    """Return shell-safe environment assignment lines."""

    return [f"{prefix}_{key.upper()}={shlex.quote(payload[key])}" for key in sorted(payload)]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    source_env = subparsers.add_parser("source-env")
    source_env.add_argument("--label", required=True)
    source_env.add_argument("--prefix", required=True)
    source_env.add_argument("--source-json", required=True)
    source_env.add_argument("--expected-path")

    git_sha = subparsers.add_parser("git-sha")
    git_sha.add_argument("value")

    digest = subparsers.add_parser("oci-digest")
    digest.add_argument("--label", required=True)
    digest.add_argument("value")

    artifact_name = subparsers.add_parser("artifact-name")
    artifact_name.add_argument("value")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "source-env":
            payload = validate_source_payload(
                args.source_json,
                label=args.label,
                expected_path=args.expected_path,
            )
            for line in shell_env_lines(payload, prefix=args.prefix):
                print(line)
            return 0
        if args.command == "git-sha":
            print(validate_git_sha(args.value))
            return 0
        if args.command == "oci-digest":
            print(validate_oci_digest(args.value, label=args.label))
            return 0
        print(validate_artifact_name(args.value))
        return 0
    except EvidenceSourceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
