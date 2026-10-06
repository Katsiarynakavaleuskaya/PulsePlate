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
from hashlib import sha256, sha3_256
import io
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
import sys
import tarfile
import tempfile
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "scripts" / "ci" / "docker_source_artifacts.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build" / "docker-sources"
ALLOWED_SOURCE_HOSTS = frozenset({"sqlite.org", "www.sqlite.org", "www.kernel.org"})
_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

# Only these two reviewed upstream repository/ref records use codeload basenames.
_PINNED_CODELOAD_SOURCES = {
    "pcre2": (
        "10.49",
        "https://codeload.github.com/PCRE2Project/pcre2/legacy.tar.gz/refs/tags/pcre2-10.49",
        "pcre2-10.49.tar.gz",
        ("6510970e92ea9410b44f85c606c389c3" "473ba05d2d6338f0ce763cc4ccaa382c"),
    ),
    "sljit": (
        "de0259c7aaf36aa40cba8014f3fad3edde9307f9",
        "https://codeload.github.com/zherczeg/sljit/legacy.tar.gz/de0259c7aaf36aa40cba8014f3fad3edde9307f9",
        "sljit-de0259c7aaf36aa40cba8014f3fad3edde9307f9.tar.gz",
        ("7ad006814d4d9c698832b14541634b9c" "c12039bae7b3bb547909fda51ee11a80"),
    ),
}


# Finite reviewed release/patch tuples; no generic source-host or patch allowance.
_PINNED_NATIVE_SOURCES = {
    "zlib": (
        "1.3.2",
        "https://zlib.net/zlib-1.3.2.tar.gz",
        "zlib-1.3.2.tar.gz",
        ("451bedbd" "cd78dec3" "704df673" "c976fab2" "5beaef6a" "db9433fe" "84665e7b" "f946e325"),
    ),
    "ncurses": (
        "6.6",
        "https://invisible-island.net/archives/ncurses/ncurses-6.6.tar.gz",
        "ncurses-6.6.tar.gz",
        ("b755b6ab" "f8bdb9fa" "fa048a0c" "55973212" "ee491051" "a0aaff08" "dfa45339" "34dc53cc"),
    ),
    "openssl": (
        "3.5.9",
        "https://codeload.github.com/openssl/openssl/legacy.tar.gz/45e844fa2a14ec92d146bd8f5778ac130b6625fb",
        "openssl-3.5.9.tar.gz",
        ("7392920f" "1897e1e2" "d9dc8483" "68aff6e4" "bdc94213" "44286d60" "ba517b9f" "14b202a0"),
    ),
    "postgresql": (
        "18.6",
        "https://ftp.postgresql.org/pub/source/v18.6/postgresql-18.6.tar.gz",
        "postgresql-18.6.tar.gz",
        ("672dab27" "4f12efd4" "9d7d431e" "77b42d23" "5d9583f1" "91608821" "b0e48dc1" "d09fb4c0"),
    ),
    "zlib-gzwrite-fix": (
        ("df84af25" "dc194249" "0e1d1c89" "9a076191" "52a46148"),
        "https://github.com/madler/zlib/commit/df84af25dc1942490e1d1c899a07619152a46148.patch",
        "zlib-gzwrite-fix-df84af25dc1942490e1d1c899a07619152a46148.patch",
        ("78aa4480" "48a5cc72" "d29156cf" "77483dd8" "f142018a" "7783a4fe" "9f73ea5f" "a02f034d"),
    ),
}
_PINNED_EXACT_SOURCES = {**_PINNED_CODELOAD_SOURCES, **_PINNED_NATIVE_SOURCES}
_NATIVE_ARCHIVE_INVENTORIES = {
    "zlib": ("zlib-1.3.2", 291, 3_579_037, "LICENSE"),
    "ncurses": ("ncurses-6.6", 1298, 18_614_617, "COPYING"),
    "openssl": ("openssl-openssl-45e844f", 6078, 131_230_833, "LICENSE.txt"),
    "postgresql": ("postgresql-18.6", 7944, 141_525_674, "COPYRIGHT"),
}
_NATIVE_ARCHIVE_MAX_BYTES = 64 * 1024 * 1024
_PINNED_NATIVE_SHA256 = {
    "zlib": (
        "bb329a0a" "2cd0274d" "05519d61" "c667c062" "e06990d7" "2e125ee2" "dfa8de64" "f0119d16"
    ),
    "ncurses": (
        "355b4cbb" "ed880b03" "81a04c46" "617b7656" "e362585d" "52e9cf84" "a67e2009" "b749ff11"
    ),
    "openssl": (
        "32662f03" "fc8e90bc" "8b8fc0ac" "b115ed41" "3eec5045" "a127e9af" "9f6c234b" "c3d0a8f2"
    ),
    "postgresql": (
        "983ee554" "ec53dbeb" "9b70797b" "ef9fcf4e" "67e117e7" "e48ca146" "3cc80b3f" "f8e8ff3f"
    ),
    "zlib-gzwrite-fix": (
        "110ff143" "75733173" "d8aa5457" "4473424f" "bd7dfe4b" "81f1ca34" "a759c6fe" "14b15b14"
    ),
}


class _NoRedirectHandler(HTTPRedirectHandler):
    """The manifest selects one source URL; redirects cannot select another."""

    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        return None


@dataclass(frozen=True)
class DockerSourceArtifact:
    """Normalized Docker source artifact metadata."""

    name: str
    version: str
    filename: str
    url: str
    sha3_256: str
    sha256: str | None = None


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
    if artifact_name in _PINNED_EXACT_SOURCES:
        if url != _PINNED_EXACT_SOURCES[artifact_name][1]:
            raise RuntimeError(
                f"{artifact_name} source URL does not match its exact reviewed identity."
            )
        return url
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if parsed.scheme != "https" or hostname not in ALLOWED_SOURCE_HOSTS:
        allowed = ", ".join(sorted(ALLOWED_SOURCE_HOSTS))
        raise RuntimeError(f"{artifact_name} source URL must use https and host one of: {allowed}")
    if not parsed.path.endswith(".tar.gz"):
        raise RuntimeError(f"{artifact_name} source URL must point to a .tar.gz artifact.")
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(f"{artifact_name} source URL must not contain credentials or overrides.")
    artifact_hosts = {
        "sqlite-autoconf": {"sqlite.org", "www.sqlite.org"},
        "util-linux": {"www.kernel.org"},
    }
    if hostname not in artifact_hosts.get(artifact_name, set()):
        raise RuntimeError(f"{artifact_name} source identity does not match its approved host.")
    return url


def _validate_source_identity(artifact: DockerSourceArtifact) -> None:
    """Cross-bind the finite codeload records, also before safe-cache reuse."""
    if artifact.name in _PINNED_EXACT_SOURCES:
        version, url, filename, digest = _PINNED_EXACT_SOURCES[artifact.name]
        if (artifact.version, artifact.url, artifact.filename, artifact.sha3_256) != (
            version,
            url,
            filename,
            digest,
        ):
            raise RuntimeError(
                f"{artifact.name} source does not match its exact reviewed identity."
            )
    _validate_source_url(artifact.url, artifact_name=artifact.name)
    if (
        artifact.name in _PINNED_NATIVE_SHA256
        and artifact.sha256 != _PINNED_NATIVE_SHA256[artifact.name]
    ):
        raise RuntimeError(f"{artifact.name} SHA256 metadata differs from its reviewed identity.")


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
    seen_names: set[str] = set()
    for index, raw_artifact in enumerate(raw_artifacts):
        if not isinstance(raw_artifact, dict):
            raise RuntimeError(f"Docker source artifact #{index} must be an object.")
        name = raw_artifact.get("name")
        version = raw_artifact.get("version")
        if "version_parts" in raw_artifact:
            parts = raw_artifact["version_parts"]
            if (
                name != "zlib-gzwrite-fix"
                or version is not None
                or type(parts) is not list
                or len(parts) != 5
                or any(
                    type(part) is not str or re.fullmatch(r"[0-9a-f]{8}", part) is None
                    for part in parts
                )
            ):
                raise RuntimeError(
                    "Only the exact zlib patch uses the reviewed version-parts form."
                )
            version = "".join(parts)
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
        if artifact_name in seen_names:
            raise RuntimeError(f"Duplicate Docker source artifact: {artifact_name}")
        seen_names.add(artifact_name)
        if (
            artifact_name not in _PINNED_EXACT_SOURCES
            and filename_text != f"{artifact_name}-{str(version).strip()}.tar.gz"
        ):
            raise RuntimeError(f"{artifact_name} filename does not match source identity/version.")
        if artifact_name not in _PINNED_EXACT_SOURCES and (
            Path(urlparse(str(url).strip()).path).name != filename_text
        ):
            raise RuntimeError(f"{artifact_name} URL filename does not match the source artifact.")
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
                sha256=(
                    _sha3_from_parts(raw_artifact["sha256_parts"], artifact_name=artifact_name)
                    if "sha256_parts" in raw_artifact
                    else None
                ),
            )
        )
    for artifact in artifacts:
        _validate_source_identity(artifact)
    return tuple(artifacts)


def validate_source_payload(artifact: DockerSourceArtifact, payload: bytes) -> None:
    """Bind the exact native bytes and reviewed member/license inventory before build."""
    _validate_source_identity(artifact)
    if sha3_256(payload).hexdigest() != artifact.sha3_256:
        raise RuntimeError(f"{artifact.name} SHA3 mismatch")
    if artifact.sha256 is not None and sha256(payload).hexdigest() != artifact.sha256:
        raise RuntimeError(f"{artifact.name} SHA256 mismatch")
    if artifact.name == "zlib-gzwrite-fix":
        if len(payload) != 854:
            raise RuntimeError("The exact zlib patch size differs from its reviewed identity.")
        return
    if artifact.name not in _NATIVE_ARCHIVE_INVENTORIES:
        return
    if len(payload) > _NATIVE_ARCHIVE_MAX_BYTES:
        raise RuntimeError("Native source archive exceeds the bounded acquisition size.")
    root, expected_count, expected_size, license_name = _NATIVE_ARCHIVE_INVENTORIES[artifact.name]
    seen: set[str] = set()
    expanded = 0
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if (
                member.name in seen
                or name.is_absolute()
                or ".." in name.parts
                or "\\" in member.name
                or not name.parts
                or name.parts[0] != root
                or not (member.isfile() or member.isdir() or member.issym() or member.islnk())
                or member.size > 32 * 1024 * 1024
                or len(seen) >= expected_count
            ):
                raise RuntimeError("Native source member layout differs from the reviewed archive.")
            if member.issym() or member.islnk():
                target = PurePosixPath(member.linkname)
                joined = (
                    member.linkname
                    if member.islnk()
                    else posixpath.join(str(name.parent), member.linkname)
                )
                normalized = posixpath.normpath(joined)
                if (
                    target.is_absolute()
                    or "\\" in member.linkname
                    or not (normalized == root or normalized.startswith(root + "/"))
                ):
                    raise RuntimeError("Native source link escapes its reviewed root.")
            seen.add(member.name)
            expanded += member.size
            if expanded > expected_size:
                raise RuntimeError("Native source expanded size differs from the reviewed archive.")
    if (
        len(seen) != expected_count
        or expanded != expected_size
        or f"{root}/{license_name}" not in seen
    ):
        raise RuntimeError("Native source member/license inventory is incomplete.")


def _write_verified_artifact(artifact: DockerSourceArtifact, output_dir: Path) -> Path:
    _validate_source_identity(artifact)
    # A cooperative build cache is not an arbitrary filesystem repair target.
    if ".." in output_dir.parts:
        raise RuntimeError("Source output directory must not traverse parent directories.")
    for directory in (output_dir.absolute(), *output_dir.absolute().parents):
        if directory.is_symlink():
            raise RuntimeError("Source output directory must not contain symlinks.")
        if directory.exists() and not directory.is_dir():
            raise RuntimeError("Source output directory must contain only real directories.")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / artifact.filename
    if output_path.is_symlink():
        raise RuntimeError("Source cache artifact must not be a symlink.")
    if output_path.exists():
        metadata = output_path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise RuntimeError("Source cache artifact must be a regular single-link file.")
        if artifact.name in _PINNED_NATIVE_SOURCES and metadata.st_size > _NATIVE_ARCHIVE_MAX_BYTES:
            raise RuntimeError("Native source cache exceeds its bounded acquisition size.")
        cached = output_path.read_bytes()
        current_digest = sha3_256(cached).hexdigest()
        if current_digest == artifact.sha3_256:
            validate_source_payload(artifact, cached)
            output_path.chmod(0o644)
            print(f"{artifact.name}: using existing verified artifact {output_path}")
            return output_path
        output_path.unlink()

    _validate_source_identity(artifact)
    source_url = _validate_source_url(artifact.url, artifact_name=artifact.name)
    print(f"{artifact.name}: fetching {source_url}")
    with build_opener(_NoRedirectHandler()).open(source_url, timeout=60) as response:
        if artifact.name in _PINNED_NATIVE_SOURCES:
            payload = response.read(_NATIVE_ARCHIVE_MAX_BYTES + 1)
        else:
            payload = response.read()
    actual_digest = sha3_256(payload).hexdigest()
    if actual_digest != artifact.sha3_256:
        raise RuntimeError(
            f"{artifact.name} SHA3 mismatch: expected {artifact.sha3_256}, got {actual_digest}"
        )
    validate_source_payload(artifact, payload)

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
