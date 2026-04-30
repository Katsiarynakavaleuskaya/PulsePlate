#!/usr/bin/env python3
"""Build deterministic App Store reviewer-packet identity hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "release-reviewer-packet-hashes.v1"
HASH_ALGORITHM = "sha256"
REVIEWER_NOTES_PATH = Path("ios/fastlane/metadata/review_information/notes.txt")
APP_PRIVACY_CONTEXT_PATH = Path("ios/fastlane/app_privacy_details.json")
METADATA_ROOT = Path("ios/fastlane/metadata")
REQUIRED_LOCALES = ("en-US", "ru-RU", "es-ES")
REQUIRED_METADATA_FILES = (
    "name.txt",
    "subtitle.txt",
    "description.txt",
    "keywords.txt",
    "promotional_text.txt",
    "release_notes.txt",
    "privacy_url.txt",
    "support_url.txt",
    "marketing_url.txt",
)


def canonical_utf8_bytes(raw: bytes, *, artifact_path: Path | None = None) -> bytes:
    """Return canonical UTF-8 bytes for reviewer packet text artifacts."""

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        artifact = artifact_path.as_posix() if artifact_path else "<unknown artifact>"
        raise UnicodeDecodeError(
            exc.encoding,
            exc.object,
            exc.start,
            exc.end,
            f"{exc.reason}; while decoding {artifact} as UTF-8",
        ) from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    return f"{normalized}\n".encode("utf-8")


def sha256_lower_hex(payload: bytes) -> str:
    """Return lowercase hex using the configured algorithm without a prefix."""

    return hashlib.new(HASH_ALGORITHM, payload).hexdigest()


def hash_text_artifact(path: Path) -> str:
    """Hash one UTF-8 text artifact using reviewer-packet canonicalization."""

    return sha256_lower_hex(canonical_utf8_bytes(path.read_bytes(), artifact_path=path))


def metadata_artifact_paths(repo_root: Path) -> list[Path]:
    """Return canonical localized metadata file paths in deterministic order."""

    paths: list[Path] = []
    missing_paths: list[Path] = []
    for locale in REQUIRED_LOCALES:
        for filename in REQUIRED_METADATA_FILES:
            relative_path = METADATA_ROOT / locale / filename
            absolute_path = repo_root / relative_path
            if not absolute_path.is_file():
                missing_paths.append(relative_path)
                continue
            paths.append(relative_path)
    if missing_paths:
        missing = ", ".join(path.as_posix() for path in missing_paths)
        raise FileNotFoundError(f"Missing App Store metadata artifacts: {missing}")
    return sorted(paths, key=lambda path: path.as_posix())


def _source_entry(kind: str, relative_path: Path, artifact_hash: str) -> dict[str, str]:
    return {
        "kind": kind,
        "path": relative_path.as_posix(),
        "hash": artifact_hash,
    }


def _canonical_json_bytes(payload: Any) -> bytes:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{serialized}\n".encode("utf-8")


def build_reviewer_packet_hash_contract(repo_root: Path) -> dict[str, Any]:
    """Build the PR-1 reviewer-packet hash contract payload."""

    resolved_root = repo_root.resolve()
    reviewer_notes_path = resolved_root / REVIEWER_NOTES_PATH
    if not reviewer_notes_path.is_file():
        raise FileNotFoundError(f"Missing reviewer notes artifact: {REVIEWER_NOTES_PATH}")

    reviewer_notes_hash = hash_text_artifact(reviewer_notes_path)
    metadata_entries = [
        _source_entry(
            "appstore_metadata",
            relative_path,
            hash_text_artifact(resolved_root / relative_path),
        )
        for relative_path in metadata_artifact_paths(resolved_root)
    ]
    metadata_manifest = {
        "canonicalization": "utf8-lf-single-trailing-newline",
        "entries": metadata_entries,
        "schema_version": SCHEMA_VERSION,
    }
    appstore_metadata_hash = sha256_lower_hex(_canonical_json_bytes(metadata_manifest))

    source_artifacts: list[dict[str, str]] = [
        _source_entry("reviewer_notes", REVIEWER_NOTES_PATH, reviewer_notes_hash),
        *metadata_entries,
    ]

    app_privacy_path = resolved_root / APP_PRIVACY_CONTEXT_PATH
    if app_privacy_path.is_file():
        source_artifacts.append(
            _source_entry(
                "app_privacy_context",
                APP_PRIVACY_CONTEXT_PATH,
                hash_text_artifact(app_privacy_path),
            )
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "hash_algorithm": HASH_ALGORITHM,
        "canonicalization": "utf8-lf-single-trailing-newline",
        "reviewer_notes_hash": reviewer_notes_hash,
        "appstore_metadata_hash": appstore_metadata_hash,
        "source_artifacts": source_artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root containing ios/fastlane artifacts.",
    )
    args = parser.parse_args()
    payload = build_reviewer_packet_hash_contract(args.repo_root)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
