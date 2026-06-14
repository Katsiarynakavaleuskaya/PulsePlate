#!/usr/bin/env python3
"""Fetch pinned Docker source artifacts before building images.

This keeps Dockerfiles deterministic and free of hidden live upstream downloads:
CI/local setup performs the network fetch explicitly, validates the artifact
digest, and places the verified tarball in the build context.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from hashlib import sha3_256
import json
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlparse
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "scripts" / "ci" / "docker_source_artifacts.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build" / "docker-sources"
ALLOWED_SOURCE_HOSTS = frozenset({"sqlite.org", "www.sqlite.org"})
_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class DockerSourceArtifact:
    """Normalized Docker source artifact metadata."""

    name: str
    version: str
    filename: str
    url: str
    sha3_256: str


def _parse_iso_date(value: object, *, field_name: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{field_name} must be a non-empty YYYY-MM-DD string.")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"{field_name} must be a valid YYYY-MM-DD date.") from exc


def _sha3_from_parts(raw_parts: object, *, artifact_name: str) -> str:
    if not isinstance(raw_parts, list) or not raw_parts:
        raise RuntimeError(f"{artifact_name} requires non-empty sha3_256_parts.")
    if not all(isinstance(part, str) and part for part in raw_parts):
        raise RuntimeError(f"{artifact_name} sha3_256_parts must be non-empty strings.")
    digest = "".join(raw_parts).lower()
    if not _HEX_RE.fullmatch(digest):
        raise RuntimeError(f"{artifact_name} sha3_256_parts must join to 64 lowercase hex chars.")
    return digest


def _validate_source_url(url: str, *, artifact_name: str) -> str:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if parsed.scheme != "https" or hostname not in ALLOWED_SOURCE_HOSTS:
        allowed = ", ".join(sorted(ALLOWED_SOURCE_HOSTS))
        raise RuntimeError(f"{artifact_name} source URL must use https and host one of: {allowed}")
    if not parsed.path.endswith(".tar.gz"):
        raise RuntimeError(f"{artifact_name} source URL must point to a .tar.gz artifact.")
    return url


def load_manifest(path: Path, *, today: date | None = None) -> tuple[DockerSourceArtifact, ...]:
    """Load and validate Docker source artifact metadata."""

    current_date = today or date.today()
    try:
        raw_manifest = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"Unable to read Docker source artifact manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Docker source artifact manifest is not valid JSON: {path}") from exc

    if not isinstance(raw_manifest, dict):
        raise RuntimeError("Docker source artifact manifest must be a JSON object.")
    if raw_manifest.get("schema_version") != 1:
        raise RuntimeError("Docker source artifact manifest schema_version must be 1.")
    review_by = _parse_iso_date(raw_manifest.get("review_by"), field_name="review_by")
    if review_by < current_date:
        raise RuntimeError(
            f"Docker source artifact manifest review_by is stale: {review_by.isoformat()}"
        )

    raw_artifacts = raw_manifest.get("artifacts")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        raise RuntimeError("Docker source artifact manifest requires a non-empty artifacts list.")

    artifacts: list[DockerSourceArtifact] = []
    for index, raw_artifact in enumerate(raw_artifacts):
        if not isinstance(raw_artifact, dict):
            raise RuntimeError(f"Docker source artifact #{index} must be an object.")
        name = raw_artifact.get("name")
        version = raw_artifact.get("version")
        filename = raw_artifact.get("filename")
        url = raw_artifact.get("url")
        if not all(
            isinstance(value, str) and value.strip() for value in (name, version, filename, url)
        ):
            raise RuntimeError(
                "Docker source artifacts require non-empty name/version/filename/url fields."
            )
        filename_text = str(filename).strip()
        if "/" in filename_text or filename_text.startswith("."):
            raise RuntimeError(
                f"Docker source artifact filename is not a safe basename: {filename_text}"
            )
        artifact_name = str(name).strip()
        artifacts.append(
            DockerSourceArtifact(
                name=artifact_name,
                version=str(version).strip(),
                filename=filename_text,
                url=_validate_source_url(str(url).strip(), artifact_name=artifact_name),
                sha3_256=_sha3_from_parts(
                    raw_artifact.get("sha3_256_parts"),
                    artifact_name=artifact_name,
                ),
            )
        )
    return tuple(artifacts)


def _write_verified_artifact(artifact: DockerSourceArtifact, output_dir: Path) -> Path:
    output_path = output_dir / artifact.filename
    if output_path.exists():
        current_digest = sha3_256(output_path.read_bytes()).hexdigest()
        if current_digest == artifact.sha3_256:
            output_path.chmod(0o644)
            print(f"{artifact.name}: using existing verified artifact {output_path}")
            return output_path
        output_path.unlink()

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"{artifact.name}: fetching {artifact.url}")
    payload = urlopen(  # nosec B310: URL is manifest-pinned to approved HTTPS hosts and SHA3-verified (remove-by: 2026-09-30, ref: PR-fix-main-trivy-container-cves)
        artifact.url,
        timeout=60,
    ).read()
    actual_digest = sha3_256(payload).hexdigest()
    if actual_digest != artifact.sha3_256:
        raise RuntimeError(
            f"{artifact.name} SHA3 mismatch: expected {artifact.sha3_256}, got {actual_digest}"
        )

    with tempfile.NamedTemporaryFile(dir=output_dir, delete=False) as tmp_file:
        tmp_file.write(payload)
        tmp_path = Path(tmp_file.name)
    tmp_path.replace(output_path)
    output_path.chmod(0o644)
    print(f"{artifact.name}: wrote verified artifact {output_path}")
    return output_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Pinned Docker source-artifact manifest.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to receive verified source artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    artifacts = load_manifest(args.manifest)
    for artifact in artifacts:
        _write_verified_artifact(artifact, args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
