#!/usr/bin/env python3
"""Validate governed release-control-plane source workflow inputs."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

GIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
OCI_SHA256_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SENTINEL_SHA_RE = re.compile(r"^sha256:([0-9a-f])\1{63}$")
SENTINEL_HASH_RE = re.compile(r"^(?:sha256:)?([0-9a-f])\1{63}$")
FORBIDDEN_TEST_PATH_RE = re.compile(r"(^|/)tests?(/|$)")
FORBIDDEN_WORDS = {
    "test",
    "tests",
    "fixture",
    "fixtures",
    "sample",
    "example",
    "placeholder",
    "fake",
    "fallback",
}


class EvidenceSourceError(ValueError):
    """Raised when governed evidence source input is unsafe or malformed."""


def _has_control_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _reject_text(value: str, *, label: str) -> None:
    if not value or _has_control_character(value):
        raise EvidenceSourceError(f"{label} must be non-empty and contain no control characters.")
    lowered = value.lower().replace("\\", "/")
    if _has_forbidden_evidence_word(lowered):
        raise EvidenceSourceError(
            f"{label} must not reference fixture/sample/example/placeholder/fake/fallback data."
        )


def _has_forbidden_evidence_word(value: str) -> bool:
    words = re.findall(r"[a-z0-9]+", value)
    return any(word in FORBIDDEN_WORDS for word in words)


def _is_safe_artifact_path(value: str) -> bool:
    normalized_path = value.replace("\\", "/")
    pure_path = PurePosixPath(normalized_path)
    return not (
        normalized_path.startswith("/")
        or "//" in normalized_path
        or any(part in {"", ".", ".."} for part in pure_path.parts)
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


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceSourceError(f"{path} must be readable JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise EvidenceSourceError(f"{path} must contain a JSON object.")
    return payload


def _reject_payload_strings(value: Any, *, pointer: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _reject_payload_strings(child, pointer=f"{pointer}.{key}" if pointer else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_payload_strings(child, pointer=f"{pointer}[{index}]")
    elif isinstance(value, str):
        lowered = value.lower().replace("\\", "/")
        if SENTINEL_HASH_RE.fullmatch(lowered):
            raise EvidenceSourceError(f"sentinel placeholder digest/hash rejected at {pointer}")
        if FORBIDDEN_TEST_PATH_RE.search(lowered):
            raise EvidenceSourceError(f"test evidence path rejected at {pointer}")
        if _has_forbidden_evidence_word(lowered):
            raise EvidenceSourceError(f"fixture/sample/fallback evidence rejected at {pointer}")
        if pointer.endswith(".path") and not _is_safe_artifact_path(value):
            raise EvidenceSourceError(f"unsafe evidence path rejected at {pointer}")


def validate_rag_gate_result_file(path: Path, *, expected_git_sha: str) -> None:
    """Validate a governed RAG gate result before manifest publication."""

    payload = _load_json_object(path)
    git_sha = payload.get("git_sha")
    if not isinstance(git_sha, str) or not GIT_SHA_RE.fullmatch(git_sha):
        raise EvidenceSourceError(
            "rag_gate_result.git_sha must be a full 40-character hexadecimal SHA."
        )
    if git_sha.lower() != validate_git_sha(expected_git_sha):
        raise EvidenceSourceError("rag_gate_result.git_sha must match git_sha.")
    _reject_payload_strings(payload, pointer="rag_gate_result")
    if payload.get("release_decision") != "PASS":
        raise EvidenceSourceError("rag_gate_result.release_decision must be PASS.")
    if payload.get("dataset_fallback_used") is not False:
        raise EvidenceSourceError("rag_gate_result.dataset_fallback_used must be false.")
    if payload.get("small_fixture_metric_gates_advisory") is not False:
        raise EvidenceSourceError(
            "rag_gate_result.small_fixture_metric_gates_advisory must be false."
        )


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
    if not _is_safe_artifact_path(normalized_path):
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

    rag_gate_result = subparsers.add_parser("rag-gate-result")
    rag_gate_result.add_argument("--expected-git-sha", required=True)
    rag_gate_result.add_argument("path", type=Path)
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
        if args.command == "rag-gate-result":
            validate_rag_gate_result_file(args.path, expected_git_sha=args.expected_git_sha)
            return 0
        if args.command == "artifact-name":
            print(validate_artifact_name(args.value))
            return 0
        parser.error(f"Unknown command: {args.command}")
    except EvidenceSourceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
