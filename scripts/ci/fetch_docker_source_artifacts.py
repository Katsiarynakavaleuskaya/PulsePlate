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
from email.message import Message
from hashlib import sha256, sha3_256
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
import sys
import tarfile
import tempfile
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scripts.ci.prometheus_source_image import Native
from urllib.error import HTTPError
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
        "https://www.zlib.net/fossils/zlib-1.3.2.tar.gz",
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
    "zlib-gzwrite-null-fix": (
        ("e3dc0a85" "b7032e98" "380dec01" "1bc8f2c2" "ee0d8fca"),
        "https://github.com/madler/zlib/commit/e3dc0a85b7032e98380dec011bc8f2c2ee0d8fca.patch",
        "zlib-gzwrite-null-fix-e3dc0a85b7032e98380dec011bc8f2c2ee0d8fca.patch",
        ("63adc22e" "cebf8bbe" "e7b9aaf4" "f0587657" "68948996" "ca4b26fa" "260d8b80" "6a64e7d3"),
    ),
    "zlib-gzvprintf-return-fix": (
        ("bbc2ccf3" "d0de2675" "76b524b8" "75c769a7" "24a513b0"),
        "https://github.com/madler/zlib/commit/bbc2ccf3d0de267576b524b875c769a724a513b0.patch",
        "zlib-gzvprintf-return-fix-bbc2ccf3d0de267576b524b875c769a724a513b0.patch",
        ("55b2edac" "2662134a" "37863f6d" "1e11fb97" "d6e63e03" "5d8d0d3d" "70ec6d8a" "3b669734"),
    ),
    "zlib-gzprintf-return-fix": (
        ("7235b0a5" "81227c56" "a79a43ff" "828f8ef6" "794194c8"),
        "https://github.com/madler/zlib/commit/7235b0a581227c56a79a43ff828f8ef6794194c8.patch",
        "zlib-gzprintf-return-fix-7235b0a581227c56a79a43ff828f8ef6794194c8.patch",
        ("274bce56" "61e7c7cc" "9c47e21f" "100c7078" "7cad6d8c" "0c04104a" "ff8d8d84" "baced7a7"),
    ),
    "zlib-blocked-errno-fix": (
        ("813dac5d" "cb5902ed" "241e9b0d" "38abd2d8" "47a335a9"),
        "https://github.com/madler/zlib/commit/813dac5dcb5902ed241e9b0d38abd2d847a335a9.patch",
        "zlib-blocked-errno-fix-813dac5dcb5902ed241e9b0d38abd2d847a335a9.patch",
        ("438d0e57" "75f15081" "a3339eed" "38d4b207" "b100f5cf" "4f68db0e" "619ef9b3" "054e3e4a"),
    ),
    "zlib-gzprintf-contract-fix": (
        ("d81c2d7e" "b705c622" "94ba0329" "92556720" "78e89115"),
        "https://github.com/madler/zlib/commit/d81c2d7eb705c62294ba03299255672078e89115.patch",
        "zlib-gzprintf-contract-fix-d81c2d7eb705c62294ba03299255672078e89115.patch",
        ("adf2578c" "eaa4d9a5" "2ccfa8d7" "4f8b8792" "cce3084f" "9f770944" "39450eec" "2a7a214c"),
    ),
    "zlib-errno-order-fix": (
        ("a82e0db3" "92178a3e" "05fb27bf" "551a6ce7" "57a47898"),
        "https://github.com/madler/zlib/commit/a82e0db392178a3e05fb27bf551a6ce757a47898.patch",
        "zlib-errno-order-fix-a82e0db392178a3e05fb27bf551a6ce757a47898.patch",
        ("b9df8d4e" "ea80d15d" "dc0ddfe8" "cccfef28" "ab23bc74" "2f850f44" "792806fc" "32accd6a"),
    ),
}
_PINNED_ALERT_SOURCES = {
    "alertmanager-source": (
        "73c6bfe7393929211294c1954f30d8ed78e4d0ad",
        "https://codeload.github.com/prometheus/alertmanager/tar.gz/73c6bfe7393929211294c1954f30d8ed78e4d0ad",
        "alertmanager-73c6bfe7393929211294c1954f30d8ed78e4d0ad.tar.gz",
        "91f2352a99d986ddc734f19f0e082c7dc24f7baf31b22f89d5b61c4b4af32400",
    ),
    "alertmanager-ui": (
        "0.34.1",
        "https://github.com/prometheus/alertmanager/releases/download/v0.34.1/alertmanager-web-ui-0.34.1.tar.gz",
        "alertmanager-web-ui-0.34.1.tar.gz",
        "ba9042c87a601adb24bef90ccc2015fec88524f796eb63edc1d533f92f6ccdd1",
    ),
}
_PINNED_EXACT_SOURCES = {
    **_PINNED_CODELOAD_SOURCES,
    **_PINNED_NATIVE_SOURCES,
    **_PINNED_ALERT_SOURCES,
}

# Exact Alertmanager source/UI acquired and reconciled before this source preparation.
_ALERT_NAMES = frozenset({"alertmanager-source", "alertmanager-ui"})
_ALERT_SIZES = {"alertmanager-source": 819451, "alertmanager-ui": 931784}
_ALERT_MEMBER_DIGESTS = {
    "alertmanager-source": "0b3bbdeb5e198cb2341b98491deaea279a8ea4bbae1c4f6b60ece72eadcc634a",
    "alertmanager-ui": "21b3e50b72b698e0aed7085f7528b5e562b3b26e3eaa219e8158710b5bf59c02",
}

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
    "zlib-gzwrite-null-fix": (
        "183bc8b9" "dd078a41" "a62de5c2" "d905d9b0" "196b45bc" "46f100d7" "e4147ec2" "28207c74"
    ),
    "zlib-gzvprintf-return-fix": (
        "7d00ee29" "be5e636d" "30da2890" "961e83e3" "5cee0b15" "2333ecd9" "7a46ae2e" "71eb5d47"
    ),
    "zlib-gzprintf-return-fix": (
        "96040ee8" "4d0d1879" "05283912" "dbd3f7b6" "6ac20339" "76a2ceef" "e9b8cca6" "3143d9c2"
    ),
    "zlib-blocked-errno-fix": (
        "6475806c" "db638378" "8a03e7af" "5617188e" "f2692803" "889cded1" "fcb01482" "5923d16c"
    ),
    "zlib-gzprintf-contract-fix": (
        "a786b2b0" "84126860" "08c7fe12" "47e90701" "cebde564" "037806bd" "9935f849" "07737cc4"
    ),
    "zlib-errno-order-fix": (
        "5188930f" "b2689746" "8b73a62d" "4755c979" "2c642b8b" "b5b5a45d" "49502816" "a85f62dd"
    ),
}
_PINNED_ZLIB_PATCH_SIZES = {
    "zlib-gzwrite-fix": 854,
    "zlib-gzwrite-null-fix": 773,
    "zlib-gzvprintf-return-fix": 749,
    "zlib-gzprintf-return-fix": 764,
    "zlib-blocked-errno-fix": 2449,
    "zlib-gzprintf-contract-fix": 1990,
    "zlib-errno-order-fix": 1478,
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
        artifact.name in _ALERT_NAMES
        and artifact.sha256
        != {
            "alertmanager-source": "5c5c72ec6b4c4746d523f2ed1994dfec4b94f7457e530ee6fb16cfec158e545e",
            "alertmanager-ui": "881fe0f7beb9573f35be47dd233af6220e72c8db72c03bcd1780402eb8dc1307",
        }[artifact.name]
    ):
        raise RuntimeError("Alertmanager SHA256 identity differs.")
    if (
        artifact.name in _PINNED_NATIVE_SHA256
        and artifact.sha256 != _PINNED_NATIVE_SHA256[artifact.name]
    ):
        raise RuntimeError(f"{artifact.name} SHA256 metadata differs from its reviewed identity.")


def load_manifest(
    path: Path, *, today: date | None = None, artifact: str | None = None
) -> tuple[DockerSourceArtifact, ...]:
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
                not isinstance(name, str)
                or name not in _PINNED_ZLIB_PATCH_SIZES
                or version is not None
                or type(parts) is not list
                or len(parts) != 5
                or any(
                    type(part) is not str or re.fullmatch(r"[0-9a-f]{8}", part) is None
                    for part in parts
                )
            ):
                raise RuntimeError("Only exact reviewed zlib patches use the version-parts form.")
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
    for loaded_artifact in artifacts:
        _validate_source_identity(loaded_artifact)
    if artifact not in (None, "alertmanager"):
        raise RuntimeError("Only the finite Alertmanager selector is admitted.")
    return tuple(
        item for item in artifacts if (item.name in _ALERT_NAMES) == (artifact == "alertmanager")
    )


def validate_source_payload(
    artifact: DockerSourceArtifact,
    payload: bytes,
    *,
    deadline: float | None = None,
    decoded_total: list[int] | None = None,
) -> None:
    """Bind the exact native bytes and reviewed member/license inventory before build."""
    _validate_source_identity(artifact)
    if sha3_256(payload).hexdigest() != artifact.sha3_256:
        raise RuntimeError(f"{artifact.name} SHA3 mismatch")
    if artifact.sha256 is not None and sha256(payload).hexdigest() != artifact.sha256:
        raise RuntimeError(f"{artifact.name} SHA256 mismatch")
    if artifact.name in _ALERT_NAMES:
        _alertmanager_members(artifact, payload, deadline=deadline, decoded_total=decoded_total)
        return
    if artifact.name in _PINNED_ZLIB_PATCH_SIZES:
        if len(payload) != _PINNED_ZLIB_PATCH_SIZES[artifact.name]:
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


def _retain_rejected_zlib_response(
    artifact: DockerSourceArtifact,
    payload: bytes,
    status: int,
    headers: object,
    directory: Path,
    output_dir: Path,
) -> None:
    """Retain only the admitted public zlib response as private, untrusted data."""
    _validate_source_identity(artifact)
    if artifact.name != "zlib" or len(payload) > _NATIVE_ARCHIVE_MAX_BYTES + 1:
        raise RuntimeError("Rejected-response capture is limited to bounded exact zlib bytes.")
    destination = directory.absolute()
    if (
        ".." in directory.parts
        or destination.is_relative_to(REPO_ROOT)
        or destination.is_relative_to(output_dir.absolute())
    ):
        raise RuntimeError("Rejected-response quarantine must be outside the build context/cache.")
    for parent in (destination.parent, *destination.parent.parents):
        if parent.is_symlink() or not parent.is_dir():
            raise RuntimeError("Rejected-response quarantine requires real existing parents.")
    if type(status) is not int or not 100 <= status <= 599:
        raise RuntimeError("Rejected-response HTTP status is unavailable.")
    if not isinstance(headers, Message):
        raise RuntimeError("Rejected-response HTTP headers are unavailable.")
    selected: dict[str, str] = {}
    truncated: list[str] = []
    for name in ("Content-Type", "Content-Length", "Content-Encoding", "Date", "Last-Modified"):
        value = headers.get(name)  # HTTP response headers; no arbitrary-header serialization.
        if value is None:
            continue
        if not isinstance(value, str):
            raise RuntimeError("Rejected-response selected header is unavailable.")
        selected[name] = value[:512]
        if len(value) > 512:
            truncated.append(name)
    metadata = {
        "artifact": "zlib",
        "request_url": artifact.url,
        "status": status,
        "headers": selected,
        "truncated_headers": truncated,
        "retained_bytes": len(payload),
        "read_limit_bytes": _NATIVE_ARCHIVE_MAX_BYTES + 1,
        "body_scope": (
            "bounded_prefix" if len(payload) > _NATIVE_ARCHIVE_MAX_BYTES else "received_bytes"
        ),
        "untrusted_response": True,
        "expected_sha3_256": artifact.sha3_256,
        "actual_sha3_256": sha3_256(payload).hexdigest(),
        "expected_sha256": artifact.sha256,
        "actual_sha256": sha256(payload).hexdigest(),
    }
    encoded = (json.dumps(metadata, sort_keys=True) + "\n").encode("utf-8")
    if len(encoded) > 20 * 1024:
        raise RuntimeError("Rejected-response metadata exceeds its bound.")
    parent_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if os.fstat(parent_fd).st_uid != os.getuid():
            raise RuntimeError("Rejected-response quarantine parent must be owned.")
        os.mkdir(destination.name, 0o700, dir_fd=parent_fd)
        directory_fd = os.open(
            destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
        )
        try:
            owned = os.fstat(directory_fd)
            if owned.st_uid != os.getuid() or stat.S_IMODE(owned.st_mode) != 0o700:
                raise RuntimeError("Rejected-response quarantine must be private and owned.")
            for name, contents in (("response.bin", payload), ("metadata.json", encoded)):
                fd = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=directory_fd,
                )
                try:
                    created = os.fstat(fd)
                    if (
                        created.st_uid != os.getuid()
                        or created.st_nlink != 1
                        or stat.S_IMODE(created.st_mode) != 0o600
                    ):
                        raise RuntimeError("Rejected-response file must be private and owned.")
                    with os.fdopen(fd, "wb", closefd=False) as target:
                        target.write(contents)
                finally:
                    os.close(fd)
        finally:
            os.close(directory_fd)
    finally:
        os.close(parent_fd)


def _alertmanager_members(
    artifact: DockerSourceArtifact,
    payload: bytes,
    *,
    deadline: float | None = None,
    decoded_total: list[int] | None = None,
) -> list[dict[str, object]]:
    """Only the two actual retained archives; no general source recognizer."""
    from scripts.ci.prometheus_source_image import check_deadline
    import gzip

    counter = decoded_total if decoded_total is not None else [0]
    with gzip.GzipFile(fileobj=io.BytesIO(payload)) as stream:
        while chunk := stream.read(1024 * 1024):
            check_deadline(deadline)
            counter[0] += len(chunk)
            if counter[0] > 256 * 1024 * 1024:
                raise RuntimeError("Alertmanager aggregate decoded archive bound exceeded.")
    root = (
        "alertmanager-73c6bfe7393929211294c1954f30d8ed78e4d0ad"
        if artifact.name == "alertmanager-source"
        else "dist"
    )
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        for member in archive:
            check_deadline(deadline)
            parts = member.name.rstrip("/").split("/")
            if (
                not parts
                or parts[0] != root
                or any(part in ("", ".", "..") for part in parts)
                or "\\" in member.name
                or member.name in seen
                or not (member.isfile() or member.isdir())
            ):
                raise RuntimeError("Alertmanager exact archive member layout differs.")
            seen.add(member.name)
            row: dict[str, object] = {
                "name": member.name.rstrip("/"),
                "type": member.type.decode("ascii"),
                "mode": member.mode,
                "bytes": member.size,
                "linkname": member.linkname,
            }
            if member.isfile():
                member_stream = archive.extractfile(member)
                if member_stream is None:
                    raise RuntimeError("Alertmanager member is missing.")
                data = member_stream.read(member.size + 1)
                if len(data) != member.size:
                    raise RuntimeError("Alertmanager member is truncated.")
                import hashlib

                row.update(
                    sha256=sha256(data).hexdigest(),
                    git_blob=hashlib.sha1(
                        b"blob " + str(len(data)).encode() + b"\0" + data, usedforsecurity=False
                    ).hexdigest(),
                    git_mode="100755" if member.mode & 0o111 else "100644",
                )
            rows.append(row)
    digest = sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if (
        len(payload) != _ALERT_SIZES[artifact.name]
        or digest != _ALERT_MEMBER_DIGESTS[artifact.name]
    ):
        raise RuntimeError("Alertmanager complete retained member inventory differs.")
    return rows


def _download_alertmanager(
    artifact: DockerSourceArtifact,
    *,
    deadline: float,
    private: Path,
) -> bytes:
    """One exact request, one UI handoff, no retries or URL overrides."""
    from scripts.ci.prometheus_source_image import opener, check_deadline

    private.chmod(0o700)
    check_deadline(deadline)
    transport = opener()
    target = artifact.url
    records: list[dict[str, object]] = []

    def persist() -> None:
        path = private / (artifact.name + "-http.json")
        try:
            path.write_text(json.dumps(records, indent=2) + "\n")
            path.chmod(0o600)
        except TimeoutError:
            raise
        except Exception as diagnostic:
            records[-1]["diagnostic_persistence_error"] = type(diagnostic).__name__

    def close_http(error: HTTPError) -> None:
        try:
            error.close()
        except TimeoutError:
            raise
        except Exception as diagnostic:
            records[-1]["diagnostic_close_error"] = type(diagnostic).__name__
            persist()

    def retain(error: HTTPError, phase: str) -> None:
        record: dict[str, object] = {
            "artifact": artifact.name,
            "phase": phase,
            "actual_http_status": error.code,
            "diagnostic_read_error": None,
        }
        records.append(record)
        persist()
        try:
            body = error.read(65537)
            path = private / (artifact.name + "-" + phase + ".http-body")
            path.write_bytes(body[:65536])
            path.chmod(0o600)
            record.update(
                body_bytes=min(len(body), 65536),
                body_truncated=len(body) > 65536,
                body_sha256=sha256(body[:65536]).hexdigest(),
            )
        except TimeoutError:
            raise
        except Exception as diagnostic:
            record["diagnostic_read_error"] = type(diagnostic).__name__
        persist()

    try:
        response = transport.open(
            Request(target, headers={"User-Agent": "PulsePlate-source-qualification"}),
            timeout=min(60, deadline - time.monotonic()),
        )
    except HTTPError as error:
        status = error.code
        try:
            retain(error, "initial")
            if (
                artifact.name != "alertmanager-ui"
                or status != 302
                or error.geturl() != artifact.url
            ):
                raise RuntimeError("Alertmanager initial HTTP status " + str(status)) from None
            locations = error.headers.get_all("Location", [])
            if len(locations) != 1:
                raise RuntimeError("Alertmanager UI handoff count differs.")
            target = locations[0]
            parsed = urlparse(target)
            if (
                parsed.scheme != "https"
                or parsed.netloc != "release-assets.githubusercontent.com"
                or parsed.fragment
                or not parsed.query
                or len(target) > 8192
                or not all(32 < ord(c) < 127 for c in target)
                or not re.fullmatch(
                    r"/github-production-release-asset/[1-9][0-9]*/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
                    parsed.path,
                )
            ):
                raise RuntimeError("Alertmanager UI handoff authority differs.")
        finally:
            close_http(error)
        check_deadline(deadline)
        try:
            response = transport.open(
                Request(target, headers={"User-Agent": "PulsePlate-source-qualification"}),
                timeout=min(60, deadline - time.monotonic()),
            )
        except HTTPError as final_error:
            status = final_error.code
            try:
                retain(final_error, "handoff-final")
            finally:
                close_http(final_error)
            raise RuntimeError("Alertmanager handoff HTTP status " + str(status)) from None
    with response:
        if response.status != 200 or response.geturl() != target:
            raise RuntimeError("Alertmanager final HTTP status or redirect differs.")
        payload = bytearray()
        while chunk := response.read(1024 * 1024):
            check_deadline(deadline)
            payload.extend(chunk)
            if len(payload) > _ALERT_SIZES[artifact.name]:
                raise RuntimeError("Alertmanager compressed archive bound exceeded.")
    return bytes(payload)


def _fetch_alertmanager_pair(
    artifacts: tuple[DockerSourceArtifact, ...],
    output: Path,
    *,
    operation_deadline: float | None = None,
) -> None:
    """Aggregate 300 seconds for this exact pair, including cached member verification."""
    from datetime import datetime, timezone, timedelta
    from scripts.ci.prometheus_source_image import check_deadline
    import signal

    def timeout(signum: int, frame: object) -> None:
        raise TimeoutError("Alertmanager aggregate acquisition deadline.")

    old_timer = signal.getitimer(signal.ITIMER_REAL)
    old_alarm = signal.getsignal(signal.SIGALRM)
    started = time.monotonic()
    deadline = (
        min(started + 300, operation_deadline) if operation_deadline is not None else started + 300
    )
    check_deadline(deadline)
    signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, deadline - started)
    private = Path(tempfile.mkdtemp(prefix="pulseplate-alert-input-private-"))
    private.chmod(0o700)
    utc = datetime.now(timezone.utc)
    (private / "START.json").write_text(
        json.dumps(
            {
                "utc": utc.isoformat(),
                "deadline": (utc + timedelta(seconds=deadline - started)).isoformat(),
                "retry": 0,
            }
        )
    )
    (private / "START.json").chmod(0o600)
    total = [0]
    try:
        if {item.name for item in artifacts} != _ALERT_NAMES or len(artifacts) != 2:
            raise RuntimeError("Alertmanager requires exactly its source/UI pair.")
        for artifact in artifacts:
            check_deadline(deadline)
            _write_verified_artifact(
                artifact,
                output,
                alert_deadline=deadline,
                alert_private=private,
                alert_decoded=total,
            )
        check_deadline(deadline)
    except BaseException as error:
        (private / "failure.json").write_text(
            json.dumps(
                {
                    "error_type": type(error).__name__,
                    "elapsed": time.monotonic() - started,
                    "retry": 0,
                }
            )
        )
        (private / "failure.json").chmod(0o600)
        if isinstance(error, TimeoutError):
            raise
        raise RuntimeError(
            "Alertmanager acquisition failed; private capture retained at " + str(private)
        ) from None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_alarm)
        if old_timer[0] > 0:
            remaining_parent = old_timer[0] - (time.monotonic() - started)
            if remaining_parent <= 0:
                raise TimeoutError("Parent Alertmanager operation deadline exhausted.")
            signal.setitimer(signal.ITIMER_REAL, remaining_parent, old_timer[1])


def _write_verified_artifact(
    artifact: DockerSourceArtifact,
    output_dir: Path,
    *,
    integrity_rejection_dir: Path | None = None,
    alert_deadline: float | None = None,
    alert_private: Path | None = None,
    alert_decoded: list[int] | None = None,
) -> Path:
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
        if artifact.name in _ALERT_NAMES and metadata.st_size != _ALERT_SIZES[artifact.name]:
            raise RuntimeError("Alertmanager cached exact size differs; no read or replacement.")
        cached = output_path.read_bytes()
        current_digest = sha3_256(cached).hexdigest()
        if current_digest == artifact.sha3_256:
            validate_source_payload(
                artifact, cached, deadline=alert_deadline, decoded_total=alert_decoded
            )
            output_path.chmod(0o644)
            print(f"{artifact.name}: using existing verified artifact {output_path}")
            return output_path
        if artifact.name in _ALERT_NAMES:
            raise RuntimeError("Alertmanager cached digest differs; no repair or replacement.")
        output_path.unlink()

    _validate_source_identity(artifact)
    source_url = _validate_source_url(artifact.url, artifact_name=artifact.name)
    print(f"{artifact.name}: fetching {source_url}")
    if artifact.name in _ALERT_NAMES:
        if alert_deadline is None or alert_private is None:
            raise RuntimeError("Alertmanager acquisition needs its bounded pair owner.")
        payload = _download_alertmanager(artifact, deadline=alert_deadline, private=alert_private)
        validate_source_payload(
            artifact, payload, deadline=alert_deadline, decoded_total=alert_decoded
        )
        with tempfile.NamedTemporaryFile(dir=output_dir, delete=False) as verified:
            verified.write(payload)
            temporary = Path(verified.name)
        temporary.replace(output_path)
        output_path.chmod(0o644)
        return output_path
    first_http_error: HTTPError | None = None
    attempt = 1
    while True:
        try:
            with build_opener(_NoRedirectHandler()).open(source_url, timeout=60) as response:
                if artifact.name in _PINNED_NATIVE_SOURCES:
                    payload = response.read(_NATIVE_ARCHIVE_MAX_BYTES + 1)
                else:
                    payload = response.read()
            break
        except HTTPError as error:
            if type(error.code) is not int or error.code not in (502, 503, 504):
                raise
            if first_http_error is None:
                first_http_error = error
            print(
                f"{artifact.name}: source HTTP {error.code} on attempt {attempt}/3",
                file=sys.stderr,
                flush=True,
            )
            error.close()
            if attempt == 3:
                raise first_http_error
            time.sleep(attempt)
            attempt += 1
    actual_digest = sha3_256(payload).hexdigest()
    try:
        if actual_digest != artifact.sha3_256:
            raise RuntimeError(
                f"{artifact.name} SHA3 mismatch: expected {artifact.sha3_256}, got {actual_digest}"
            )
        validate_source_payload(artifact, payload)
    except Exception as rejection:
        if artifact.name == "zlib" and integrity_rejection_dir is not None:
            try:
                _retain_rejected_zlib_response(
                    artifact,
                    payload,
                    response.getcode(),
                    response.headers,
                    integrity_rejection_dir,
                    output_dir,
                )
            except Exception as capture_error:
                diagnostic = (
                    "zlib: rejected-response capture failed: " + type(capture_error).__name__
                )
                rejection.add_note(diagnostic)
                print(diagnostic, file=sys.stderr)
        raise

    with tempfile.NamedTemporaryFile(dir=output_dir, delete=False) as tmp_file:
        tmp_file.write(payload)
        tmp_path = Path(tmp_file.name)
    tmp_path.replace(output_path)
    output_path.chmod(0o644)
    print(f"{artifact.name}: wrote verified artifact {output_path}")
    return output_path


def _alertmanager_command_exit(
    observed: dict[str, object], identifier: str, name: str, owner_token: str, waited: bytes
) -> None:
    """Exact owned metadata container command must finish successfully, not just attach."""
    state = observed.get("State")
    config = observed.get("Config")
    if (
        observed.get("Id") != identifier
        or observed.get("Name") != "/" + name
        or not isinstance(config, dict)
        or not isinstance(config.get("Labels"), dict)
        or config["Labels"].get("pulseplate.alertmanager-module") != owner_token
    ):
        raise RuntimeError("Owned Alertmanager command container identity differs.")
    if (
        not isinstance(state, dict)
        or state.get("Status") != "exited"
        or any(
            state.get(key) is not False for key in ("Running", "Restarting", "Dead", "OOMKilled")
        )
        or state.get("Error") != ""
        or type(state.get("ExitCode")) is not int
        or state["ExitCode"] != 0
        or waited != b"0\n"
    ):
        raise RuntimeError("Actual Alertmanager container command exit is not successful.")


def _alertmanager_cleanup_member(
    native: Native,
    docker: str,
    identifier: str,
    owned_ids: set[str],
    owned_names: set[str],
    owner_token: str,
    env: dict[str, str],
    cwd: Path,
    index: int,
    docker_config: Path,
) -> None:
    from scripts.ci.prometheus_source_image import decode_objects

    if identifier not in owned_ids or re.fullmatch(r"[0-9a-f]{64}", identifier) is None:
        raise RuntimeError("Cleanup census ID is not an actual retained create identity.")
    observed = decode_objects(
        native.run(
            [
                docker,
                "--config",
                str(docker_config),
                "inspect",
                "--format",
                "{{json .}}",
                identifier,
            ],
            "cleanup-inspect-" + str(index),
            env,
            cwd=cwd,
            cleaning=True,
        )
    )
    if (
        len(observed) != 1
        or observed[0].get("Id") != identifier
        or observed[0].get("Name", "").lstrip("/") not in owned_names
        or observed[0].get("Config", {}).get("Labels", {}).get("pulseplate.alertmanager-module")
        != owner_token
    ):
        raise RuntimeError("Cleanup census includes unknown resource.")
    native.run(
        [docker, "--config", str(docker_config), "rm", "--force", identifier],
        "cleanup-remove-" + str(index),
        env,
        cwd=cwd,
        cleaning=True,
    )


def _alertmanager_compare_replays(replay: list[dict[str, object]]) -> None:
    # Complete explicit GOMODCACHE payload equality, not root-sensitive Go index caches.
    for key in (
        "original",
        "derived",
        "modules",
        "graph",
        "packages",
        "delta",
        "module_cache",
        "source",
        "version",
    ):
        if replay[0][key] != replay[1][key]:
            raise RuntimeError("Independent Alertmanager original-source replay differs: " + key)


def _retain_alertmanager_inputs(
    evidence: Path,
    source: Path,
    modules: Path,
    go_archive: Path,
    base_archive: Path,
    source_archive: Path,
    ui_archive: Path,
    deadline: float,
) -> dict[str, object]:
    """One closed frozen-input tar in the existing module-evidence artifact, no reader."""
    from scripts.ci.prometheus_source_image import (
        tree_inventory,
        file_hash,
        check_deadline,
        MAX_CACHE_BYTES,
    )

    declared = {
        "source": source,
        "modules": modules,
        "go-toolchain.tar.gz": go_archive,
        "base-image.tar": base_archive,
        "source.tar.gz": source_archive,
        "ui.tar.gz": ui_archive,
    }
    files: list[tuple[str, Path]] = []
    directories: list[tuple[str, Path]] = []
    for name, path in declared.items():
        check_deadline(deadline)
        if path.is_dir() and not path.is_symlink():
            tree_inventory(path, deadline=deadline)
            directories.append((name, path))
            for child in sorted(path.rglob("*")):
                if child.is_symlink():
                    raise RuntimeError("Frozen Alertmanager input symlink rejected.")
                if child.is_dir():
                    directories.append((name + "/" + child.relative_to(path).as_posix(), child))
                elif child.is_file():
                    files.append((name + "/" + child.relative_to(path).as_posix(), child))
                else:
                    raise RuntimeError("Frozen Alertmanager input member type differs.")
        elif path.is_file() and not path.is_symlink():
            files.append((name, path))
        else:
            raise RuntimeError("Frozen required Alertmanager input missing.")
    if (
        sum(path.stat().st_size for _, path in files) > MAX_CACHE_BYTES
        or len(files) + len(directories) > 250000
    ):
        raise RuntimeError("Frozen Alertmanager input payload exceeds existing carrier limits.")
    rows = []
    destination = evidence / "frozen-inputs.tar"
    # Go module-cache basenames can exceed USTAR's 100-byte name field. PAX
    # preserves the same logical members and their explicitly fixed metadata.
    with tarfile.open(destination, "x", format=tarfile.PAX_FORMAT) as archive:
        for name, path in directories + files:
            check_deadline(deadline)
            info = path.lstat()
            member = tarfile.TarInfo(name)
            member.mode = stat.S_IMODE(info.st_mode)
            member.uid = member.gid = 0
            member.mtime = 0
            row = {"path": name, "mode": member.mode, "bytes": 0, "type": "directory"}
            if stat.S_ISDIR(info.st_mode):
                member.type = tarfile.DIRTYPE
                archive.addfile(member)
            elif stat.S_ISREG(info.st_mode):
                member.size = info.st_size
                row.update(bytes=member.size, type="file", sha256=file_hash(path, deadline))
                with path.open("rb") as stream:
                    archive.addfile(member, stream)
                if path.stat().st_size != member.size or file_hash(path, deadline) != row["sha256"]:
                    raise RuntimeError("Frozen Alertmanager input changed during retention.")
            else:
                raise RuntimeError("Frozen Alertmanager retained type differs.")
            rows.append(row)
    if destination.stat().st_size > MAX_CACHE_BYTES:
        raise RuntimeError("Frozen Alertmanager tar exceeds existing carrier limit.")
    return {
        "path": "frozen-inputs.tar",
        "bytes": destination.stat().st_size,
        "sha256": file_hash(destination, deadline),
        "members": rows,
        "private_HTTP_and_HOME_excluded": True,
    }


def _alertmanager_loaded_base(objects: list[dict[str, Any]]) -> str:
    if len(objects) != 1:
        raise RuntimeError("Exact public base native observation ambiguous.")
    image = objects[0]
    expected = [
        "sha256:9486261b5a13f63ca6904b36721527ac8f19df53d300560138d69ae9b4c203de",
        "sha256:621c35e751a51a9a9dc3e80aa0b7fe8be2a93402ea6ccd307d30852cd7776cda",
        "sha256:763a77745f27b86cf26b97887b6842d83720e63b1c48848c0ba9ee54e351d63a",
        "sha256:f0d0eff4c2312a7bd6e21797bdfea5eb35f60e76b555ce2b22794424af2cad36",
        "sha256:275a30dd8ce958b21daa9ad962c6fbc09f98306ee2f486b65c9075dc257b1412",
        "sha256:4d049f83d9cf21d1f5cc0e11deaf36df02790d0e60c1a3829538fb4b61685368",
        "sha256:af5aa97ebe6ce1604747ec1e21af7136ded391bcabe4acef882e718a87c86bcc",
        "sha256:6f1cdceb6a3146f0ccb986521156bef8a422cdbb0863396f7f751f575ba308f4",
        "sha256:bd3cdfae1d3fdd83a2231d608969b38b82349777c2fff9a7c12d54f8ac5c9b38",
        "sha256:4cde6b0bb6f50a5f255eef7b2a42162c661cf776b803225dcac9a659e396bb6b",
        "sha256:ad51d0769d16ba578106a177987dfe3d2e02c1668c852b795b2f6b024068242a",
        "sha256:187cfc6d1e3e8a40a5e64653bcd3239c140807dcf1c09e48021178705a5a6139",
        "sha256:f2392a9484bf6b18f06beaf705b994e31dbb2716c99cf7d03c9c495cd107f364",
    ]
    reference = "gcr.io/distroless/static-debian13@sha256:2293b36c7c9082bf4115aab724b4d2cddec82c8eba39bf27ac0517e159acf150"
    digests = image.get("RepoDigests")
    rootfs = image.get("RootFS")
    if (
        type(digests) is not list
        or any(type(value) is not str for value in digests)
        or digests.count(reference) != 1
        or type(rootfs) is not dict
        or rootfs.get("Type") != "layers"
        or type(rootfs.get("Layers")) is not list
    ):
        raise RuntimeError("Exact public base native field shapes differ.")
    if (
        image.get("Id") != "sha256:55a757dc8ab862a4eb634c434261dcd26f17c186b54f7bce845404a335456110"
        or image.get("Os") != "linux"
        or image.get("Architecture") != "amd64"
        or rootfs["Layers"] != expected
    ):
        raise RuntimeError("Exact public base config/platform/RepoDigest/thirteen diffIDs differ.")
    identifier = image["Id"]
    if not isinstance(identifier, str):
        raise RuntimeError("Native base ID type differs.")
    return identifier


def _alertmanager_finalize_payload(evidence: Path, deadline: float) -> None:
    from scripts.ci.prometheus_source_image import tree_inventory, check_deadline, MAX_CACHE_BYTES

    check_deadline(deadline)
    paths = list(evidence.rglob("*"))
    if len(paths) + 1 > 250000:
        raise RuntimeError("Complete Alertmanager artifact member limit exceeded.")
    files = tree_inventory(evidence, deadline=deadline)
    dirs = [
        {
            "path": path.relative_to(evidence).as_posix(),
            "type": "directory",
            "mode": stat.S_IMODE(path.lstat().st_mode),
        }
        for path in paths
        if path.is_dir() and not path.is_symlink()
    ]
    carrier = evidence / "artifact-payload-members.json"
    if carrier.exists() or carrier.is_symlink():
        raise RuntimeError("Fresh Alertmanager inventory carrier collision.")
    raw = (
        json.dumps(
            {
                "files": files,
                "directories": dirs,
                "inventory_carrier_exception": "Exactly artifact-payload-members.json is bound by external artifact bytes; its own hash is not recursively embedded.",
            },
            indent=2,
        )
        + "\n"
    ).encode()
    if sum(row["size"] for row in files) + len(raw) > MAX_CACHE_BYTES or len(paths) + 1 > 250000:
        raise RuntimeError("Complete Alertmanager artifact byte/member limit exceeded.")
    check_deadline(deadline)
    with carrier.open("xb") as stream:
        stream.write(raw)
    carrier.chmod(0o600)


def _qualify_alertmanager_modules(output: Path) -> None:
    """ONE fixed825 owner; source child restores its remaining parent timer."""
    import signal

    seconds_text = os.environ.get("ALERTMANAGER_QUALIFY_SECONDS")
    if seconds_text != "825":
        raise RuntimeError(
            "Alertmanager qualification requires the workflow's exact 825-second bound."
        )
    seconds = int(seconds_text)
    started = time.monotonic()
    deadline = started + seconds
    saved_timer = signal.getitimer(signal.ITIMER_REAL)
    saved_handler = signal.getsignal(signal.SIGALRM)

    def timeout(signum: int, frame: object) -> None:
        raise TimeoutError("Alertmanager complete qualification825 deadline exhausted.")

    signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        _alertmanager_module_phase(output, deadline, seconds)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, saved_handler)
        if saved_timer[0] > 0:
            remaining = saved_timer[0] - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError("Caller timer expired during Alertmanager operation.")
            signal.setitimer(signal.ITIMER_REAL, remaining, saved_timer[1])


def _alertmanager_readonly_go(toolchain: Path, deadline: float) -> dict[str, list[dict[str, Any]]]:
    """Only the fresh byte-validated Go extraction, including searchable directories."""
    from scripts.ci.prometheus_source_image import tree_inventory, check_deadline

    if (
        toolchain.name != "alertmanager-go"
        or toolchain.is_symlink()
        or toolchain.stat().st_uid != os.getuid()
    ):
        raise RuntimeError("Owned qualified Go tree identity differs.")
    before = tree_inventory(toolchain, deadline=deadline)
    directories = [toolchain, *sorted(path for path in toolchain.rglob("*") if path.is_dir())]
    before_directories = [
        {"path": path.relative_to(toolchain).as_posix(), "mode": stat.S_IMODE(path.lstat().st_mode)}
        for path in directories
    ]
    for row in before:
        check_deadline(deadline)
        (toolchain / row["path"]).chmod(0o555 if row["mode"] & 0o111 else 0o444)
    for directory in directories:
        check_deadline(deadline)
        directory.chmod(0o555)
    after = tree_inventory(toolchain, deadline=deadline)
    if [{key: row[key] for key in ("path", "size", "sha256")} for row in before] != [
        {key: row[key] for key in ("path", "size", "sha256")} for row in after
    ]:
        raise RuntimeError("Owned Go input bytes changed during permission freeze.")
    return {
        "before_files": before,
        "after_files": after,
        "before_directories": before_directories,
        "after_directories": [
            {
                "path": path.relative_to(toolchain).as_posix(),
                "mode": stat.S_IMODE(path.lstat().st_mode),
            }
            for path in directories
        ],
    }


def _alertmanager_module_phase(output: Path, deadline: float, seconds: int) -> None:
    """Fixed metadata-only online/offline replay; this function never compiles."""
    import shutil
    import uuid
    from scripts.ci.prometheus_source_image import (
        Native,
        GO,
        extract,
        acquire,
        decode_objects,
        file_hash,
        tree_inventory,
    )

    evidence = output / "alertmanager-module-evidence"
    output.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(mode=0o700)
    native = Native(evidence, deadline, 45)
    owner_token = uuid.uuid4().hex
    owned_names: set[str] = set()
    owned_ids: set[str] = set()
    primary: BaseException | None = None
    cleanup_error: BaseException | None = None
    docker_config = output / "alertmanager-empty-docker-config"
    docker_config.mkdir(mode=0o700)
    docker_env = {"PATH": "/usr/bin:/bin", "HOME": str(docker_config)}
    try:
        artifacts = load_manifest(DEFAULT_MANIFEST, artifact="alertmanager")
        _fetch_alertmanager_pair(artifacts, output, operation_deadline=deadline)
        go_archive = output / "go1.27.2.linux-amd64.tar.gz"
        if not go_archive.exists() and not go_archive.is_symlink():
            acquire(GO, go_archive, deadline)

        if (
            go_archive.is_symlink()
            or not go_archive.is_file()
            or go_archive.stat().st_nlink != 1
            or go_archive.stat().st_size != 70590635
            or file_hash(go_archive, deadline)
            != "ecbadb99091a3f46e31f5f934b068b1864eafa7995211b39eaddf76996045fe5"
        ):
            raise RuntimeError("Exact Go input changed; no overwrite, replacement or retry.")
        toolchain = output / "alertmanager-go"
        go_members = extract(GO, go_archive, toolchain, deadline)
        (evidence / "go-compiler-input-members.json").write_text(
            json.dumps(go_members, indent=2) + "\n"
        )
        go_tree_binding = _alertmanager_readonly_go(toolchain, deadline)
        (evidence / "go-readonly-input-binding.json").write_text(
            json.dumps(go_tree_binding, indent=2) + "\n"
        )
        go = toolchain / "bin/go"
        docker = shutil.which("docker")
        if docker is None or not Path(docker).is_absolute():
            raise RuntimeError("Resolved Docker is required for real network-none metadata replay.")
        docker_prefix = [docker, "--config", str(docker_config)]
        base_ref = "gcr.io/distroless/static-debian13@sha256:2293b36c7c9082bf4115aab724b4d2cddec82c8eba39bf27ac0517e159acf150"
        native.run(
            [*docker_prefix, "pull", "--platform", "linux/amd64", base_ref],
            "public-base-pull",
            docker_env,
            cwd=output,
        )
        base_raw = native.run(
            [*docker_prefix, "image", "inspect", "--format", "{{json .}}", base_ref],
            "public-base-inspect",
            docker_env,
            cwd=output,
        )
        base_objects = decode_objects(base_raw)
        base_id = _alertmanager_loaded_base(base_objects)
        base_retention = evidence / "base-retention"
        base_retention.mkdir(mode=0o700)
        base_archive = base_retention / "base-image.tar"
        native.run(
            [*docker_prefix, "image", "save", "--output", str(base_archive), base_id],
            "retain-physical-base",
            docker_env,
            cwd=output,
            watched_output=base_retention,
        )
        originals = {item.name: item for item in artifacts}
        replay = []
        for number in (1, 2):
            source = output / ("alertmanager-replay-" + str(number))
            source.mkdir(mode=0o755)
            for name, destination in (
                ("alertmanager-source", source),
                ("alertmanager-ui", source / "ui/app/dist"),
            ):
                artifact = originals[name]
                payload = (output / artifact.filename).read_bytes()
                validate_source_payload(artifact, payload, deadline=deadline)
                destination.mkdir(parents=True, exist_ok=True)
                with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
                    for member in archive:
                        relative = PurePosixPath(member.name).parts[1:]
                        if not relative:
                            continue
                        target = destination.joinpath(*relative)
                        if member.isdir():
                            target.mkdir(parents=True, exist_ok=True)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            stream = archive.extractfile(member)
                            if stream is None or target.exists() or target.is_symlink():
                                raise RuntimeError("Fresh exact Alertmanager extraction collision.")
                            with target.open("xb") as writer:
                                shutil.copyfileobj(stream, writer)
                            target.chmod(0o755 if member.mode & 0o111 else 0o644)
            cache = output / ("alertmanager-cache-" + str(number))
            cache.mkdir(mode=0o755)
            home = output / ("alertmanager-home-" + str(number))
            home.mkdir(mode=0o700)
            env = {
                "PATH": str(toolchain / "bin") + ":/usr/bin:/bin",
                "HOME": str(home),
                "GOPATH": str(cache),
                "GOMODCACHE": str(cache / "pkg/mod"),
                "GOCACHE": str(cache / "build"),
                "GOTOOLCHAIN": "local",
                "GOOS": "linux",
                "GOARCH": "amd64",
                "CGO_ENABLED": "0",
                "GOPROXY": "https://proxy.golang.org",
                "GOSUMDB": "sum.golang.org",
                "GOFLAGS": "",
            }
            original_locks = {name: (source / name).read_bytes() for name in ("go.mod", "go.sum")}
            original_inventory = tree_inventory(source, deadline=deadline)
            for lock, raw in original_locks.items():
                (evidence / ("replay" + str(number) + "-original-" + lock)).write_bytes(raw)
            (evidence / ("replay" + str(number) + "-original-source.json")).write_text(
                json.dumps(original_inventory, indent=2) + "\n"
            )

            def nonlocks() -> list[dict[str, Any]]:
                return [
                    row
                    for row in tree_inventory(source, deadline=deadline)
                    if row["path"] not in ("go.mod", "go.sum")
                ]

            frozen_source = nonlocks()

            def command(args: list[str], label: str, solver: bool = False) -> bytes:
                before_locks = {name: (source / name).read_bytes() for name in original_locks}
                if nonlocks() != frozen_source or file_hash(go_archive, deadline) != GO.digest:
                    raise RuntimeError("Alertmanager source/tool drift before metadata command.")
                raw: bytes = native.run(
                    [str(go), *args], "replay" + str(number) + "-" + label, env, cwd=source
                )
                if nonlocks() != frozen_source or (
                    not solver
                    and before_locks
                    != {name: (source / name).read_bytes() for name in original_locks}
                ):
                    raise RuntimeError("Alertmanager source/lock drift after metadata command.")
                return raw

            version = command(["version"], "version")
            if version != b"go version go1.27.2 linux/amd64\n":
                raise RuntimeError("Qualified Go version/platform differs.")
            command(["mod", "download", "-json"], "baseline-download")
            baseline = decode_objects(
                command(["list", "-mod=readonly", "-m", "-json", "all"], "baseline-modules")
            )
            command(
                ["get", "golang.org/x/net@v0.60.0", "google.golang.org/grpc@v1.83.2"],
                "two-authored-replacements",
                True,
            )
            command(["mod", "download", "-json"], "derived-download")
            command(["mod", "verify"], "online-verify")
            modules_raw = command(["list", "-mod=readonly", "-m", "-json", "all"], "online-modules")
            graph = command(["mod", "graph"], "online-graph")
            package_graphs = {}
            for cmd in ("alertmanager", "amtool"):
                raw = command(
                    ["list", "-mod=readonly", "-tags=netgo", "-deps", "-json", "./cmd/" + cmd],
                    "online-" + cmd,
                )
                packages = decode_objects(raw)
                if any(
                    row.get("Error") or row.get("DepsErrors") or row.get("Incomplete")
                    for row in packages
                ):
                    raise RuntimeError("Alertmanager complete package graph unavailable.")
                if not any(
                    row.get("ImportPath") == "github.com/prometheus/alertmanager/cmd/" + cmd
                    and row.get("Module", {}).get("Main") is True
                    for row in packages
                ):
                    raise RuntimeError("Alertmanager command graph has wrong main identity.")
                package_graphs[cmd] = raw

            def coordinate(raw: bytes) -> bytes:
                return (
                    raw.replace(str(source).encode(), b"/source")
                    .replace(str(cache).encode(), b"/cache")
                    .replace(str(toolchain).encode(), b"/toolchain")
                )

            def modules_projection(raw: bytes) -> list[dict[str, object]]:
                rows = decode_objects(coordinate(raw))
                paths = [row.get("Path") for row in rows]
                if (
                    not rows
                    or any(not isinstance(path, str) for path in paths)
                    or len(set(paths)) != len(paths)
                    or any(row.get("Error") or row.get("Replace") for row in rows)
                ):
                    raise RuntimeError("Alertmanager selected modules incomplete or ambiguous.")
                main = [row for row in rows if row.get("Main") is True]
                versions = {row["Path"]: row.get("Version") for row in rows}
                if (
                    len(main) != 1
                    or main[0]["Path"] != "github.com/prometheus/alertmanager"
                    or versions.get("golang.org/x/net") != "v0.60.0"
                    or versions.get("google.golang.org/grpc") != "v1.83.2"
                ):
                    raise RuntimeError("Alertmanager selected module identities differ.")
                fields = ("Path", "Version", "Main", "GoVersion", "Sum", "GoModSum", "Indirect")
                return sorted(
                    ({key: row[key] for key in fields if key in row} for row in rows),
                    key=lambda row: row["Path"],
                )

            def packages_projection(raw: bytes, cmd: str) -> list[dict[str, object]]:
                rows = decode_objects(coordinate(raw))
                names = [row.get("ImportPath") for row in rows]
                if (
                    not rows
                    or any(not isinstance(name, str) for name in names)
                    or len(set(names)) != len(names)
                    or any(
                        row.get("Error") or row.get("DepsErrors") or row.get("Incomplete")
                        for row in rows
                    )
                ):
                    raise RuntimeError("Alertmanager package closure incomplete or ambiguous.")
                root = "github.com/prometheus/alertmanager/cmd/" + cmd
                if (
                    sum(
                        row.get("ImportPath") == root
                        and isinstance(row.get("Module"), dict)
                        and row["Module"].get("Main") is True
                        and row["Module"].get("Path") == "github.com/prometheus/alertmanager"
                        for row in rows
                    )
                    != 1
                ):
                    raise RuntimeError("Alertmanager package root identity differs.")
                if any(
                    dependency not in names for row in rows for dependency in row.get("Deps", [])
                ):
                    raise RuntimeError(
                        "Alertmanager package dependency missing from complete graph."
                    )
                fields = (
                    "ImportPath",
                    "Name",
                    "Standard",
                    "Imports",
                    "Deps",
                    "GoFiles",
                    "IgnoredGoFiles",
                    "CgoFiles",
                    "EmbedPatterns",
                    "EmbedFiles",
                )
                return sorted(
                    ({key: row[key] for key in fields if key in row} for row in rows),
                    key=lambda row: row["ImportPath"],
                )

            online_modules = modules_projection(modules_raw)
            online_packages = {
                cmd: packages_projection(raw, cmd) for cmd, raw in package_graphs.items()
            }
            if (
                not graph
                or len(graph.splitlines()) != len(set(graph.splitlines()))
                or any(len(line.split()) != 2 for line in graph.splitlines())
            ):
                raise RuntimeError("Alertmanager module graph malformed or duplicated.")
            online_graph = sorted(graph.splitlines())
            modules = decode_objects(modules_raw)
            before = {row["Path"]: row.get("Version") for row in baseline}
            after = {row["Path"]: row.get("Version") for row in modules}
            if (
                len(before) != len(baseline)
                or len(after) != len(modules)
                or before.get("golang.org/x/net") == "v0.60.0"
                or before.get("google.golang.org/grpc") == "v1.83.2"
            ):
                raise RuntimeError("Module duplicates or missing non-empty authored replacement.")
            if (
                after.get("golang.org/x/net") != "v0.60.0"
                or after.get("google.golang.org/grpc") != "v1.83.2"
                or any(row.get("Error") or row.get("Replace") for row in modules)
            ):
                raise RuntimeError(
                    "Alertmanager authored module targets or selected identities differ."
                )
            delta = [
                {
                    "path": path,
                    "before": before.get(path),
                    "after": after.get(path),
                    "class": (
                        "authored"
                        if path in ("golang.org/x/net", "google.golang.org/grpc")
                        else "solver_closure_reproduced_by_fixed_get"
                    ),
                }
                for path in sorted(set(before) | set(after))
                if before.get(path) != after.get(path)
            ]
            derived_locks = {name: (source / name).read_bytes() for name in original_locks}
            for lock, raw in derived_locks.items():
                (evidence / ("replay" + str(number) + "-derived-" + lock)).write_bytes(raw)
            cache_inventory = tree_inventory(cache, deadline=deadline)
            module_inventory = tree_inventory(cache / "pkg/mod", deadline=deadline)
            build_inventory = tree_inventory(cache / "build", deadline=deadline)
            source_inventory = tree_inventory(source, deadline=deadline)
            for base in (source, cache):
                for path in sorted(base.rglob("*"), reverse=True):
                    if not path.is_symlink():
                        path.chmod(0o555 if path.is_dir() or path.stat().st_mode & 0o111 else 0o444)
                base.chmod(0o555)
            readonly_source = tree_inventory(source, deadline=deadline)
            readonly_cache = tree_inventory(cache, deadline=deadline)
            (evidence / ("replay" + str(number) + "-inventories.json")).write_text(
                json.dumps(
                    {
                        "original_source": original_inventory,
                        "derived_source": source_inventory,
                        "complete_GOMODCACHE": module_inventory,
                        "whole_GOPATH": cache_inventory,
                        "whole_GOCACHE": build_inventory,
                        "readonly_source": readonly_source,
                        "readonly_GOPATH": readonly_cache,
                    },
                    indent=2,
                )
                + "\n"
            )
            (evidence / ("replay" + str(number) + "-projections.json")).write_text(
                json.dumps(
                    {
                        "selected_modules": online_modules,
                        "package_graphs": online_packages,
                        "module_edges": [line.decode("utf-8") for line in online_graph],
                        "delta": delta,
                    },
                    indent=2,
                )
                + "\n"
            )
            prefix = [
                *docker_prefix,
                "create",
                "--pull=never",
                "--network=none",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--user=65534:65534",
                "--tmpfs",
                "/run/alertmanager-metadata:size=64m,noexec,nosuid,uid=65534,gid=65534,mode=0700",
                "--mount",
                "type=bind,source=" + str(source) + ",target=/source,readonly",
                "--mount",
                "type=bind,source=" + str(cache) + ",target=/cache,readonly",
                "--mount",
                "type=bind,source=" + str(toolchain) + ",target=/toolchain,readonly",
                "--workdir=/source",
            ]
            for key, value in {
                "HOME": "/run/alertmanager-metadata",
                "GOPATH": "/cache",
                "GOMODCACHE": "/cache/pkg/mod",
                "GOCACHE": "/run/alertmanager-metadata/cache",
                "TMPDIR": "/run/alertmanager-metadata",
                "GOTOOLCHAIN": "local",
                "GOPROXY": "off",
                "GOSUMDB": "off",
                "CGO_ENABLED": "0",
                "GOOS": "linux",
                "GOARCH": "amd64",
                "GOFLAGS": "",
            }.items():
                prefix += ["--env", key + "=" + value]
            prefix += [
                "--entrypoint=/toolchain/bin/go",
                base_id,
            ]
            for label, args in (
                ("version", ["version"]),
                ("verify", ["mod", "verify"]),
                ("modules", ["list", "-mod=readonly", "-m", "-json", "all"]),
                ("graph", ["mod", "graph"]),
                (
                    "alertmanager",
                    [
                        "list",
                        "-mod=readonly",
                        "-tags=netgo",
                        "-deps",
                        "-json",
                        "./cmd/alertmanager",
                    ],
                ),
                (
                    "amtool",
                    ["list", "-mod=readonly", "-tags=netgo", "-deps", "-json", "./cmd/amtool"],
                ),
            ):
                name = "pulseplate-alert-module-" + owner_token + "-" + str(number) + "-" + label
                owned_names.add(name)
                owned_label = "pulseplate.alertmanager-module=" + owner_token
                create_argv = [
                    *prefix[:4],
                    "--name",
                    name,
                    "--label",
                    owned_label,
                    *prefix[4:],
                    *args,
                ]
                identifier = (
                    native.run(
                        create_argv,
                        "replay" + str(number) + "-create-" + label,
                        {"PATH": "/usr/bin:/bin", "HOME": str(home)},
                        cwd=source,
                    )
                    .decode("ascii")
                    .strip()
                )
                if re.fullmatch(r"[0-9a-f]{64}", identifier) is None:
                    raise RuntimeError("Owned Alertmanager metadata container identity malformed.")
                owned_ids.add(identifier)
                raw = native.run(
                    [*docker_prefix, "start", "--attach", identifier],
                    "replay" + str(number) + "-offline-" + label,
                    {"PATH": "/usr/bin:/bin", "HOME": str(home)},
                    cwd=source,
                )
                waited = native.run(
                    [*docker_prefix, "wait", identifier],
                    "replay" + str(number) + "-wait-" + label,
                    {"PATH": "/usr/bin:/bin", "HOME": str(home)},
                    cwd=source,
                )
                terminal = decode_objects(
                    native.run(
                        [*docker_prefix, "inspect", "--format", "{{json .}}", identifier],
                        "replay" + str(number) + "-terminal-" + label,
                        {"PATH": "/usr/bin:/bin", "HOME": str(home)},
                        cwd=source,
                    )
                )
                if len(terminal) != 1:
                    raise RuntimeError("Owned Alertmanager terminal state ambiguous.")
                _alertmanager_command_exit(terminal[0], identifier, name, owner_token, waited)
                if (
                    label in package_graphs
                    and packages_projection(raw, label) != online_packages[label]
                ):
                    raise RuntimeError("Offline Alertmanager package semantic graph differs.")
                if label == "modules" and modules_projection(raw) != online_modules:
                    raise RuntimeError("Offline Alertmanager selected module graph differs.")
                if label == "graph" and sorted(raw.splitlines()) != online_graph:
                    raise RuntimeError("Offline Alertmanager module edges differ.")
                if label == "version" and raw != version:
                    raise RuntimeError("Offline qualified Go version/platform differs.")
                if (
                    tree_inventory(source, deadline=deadline) != readonly_source
                    or tree_inventory(cache, deadline=deadline) != readonly_cache
                ):
                    raise RuntimeError("Readonly offline source/cache changed.")
            if tree_inventory(toolchain, deadline=deadline) != go_tree_binding[
                "after_files"
            ] or any(
                stat.S_IMODE((toolchain / row["path"]).stat().st_mode) != row["mode"]
                for row in go_tree_binding["after_directories"]
            ):
                raise RuntimeError("Readonly qualified Go input changed after metadata queries.")
            (evidence / ("replay" + str(number) + "-offline-stability.json")).write_text(
                json.dumps(
                    {
                        "source_before": readonly_source,
                        "source_after": tree_inventory(source, deadline=deadline),
                        "whole_GOPATH_before": readonly_cache,
                        "whole_GOPATH_after": tree_inventory(cache, deadline=deadline),
                        "whole_GOCACHE_after": tree_inventory(cache / "build", deadline=deadline),
                    },
                    indent=2,
                )
                + "\n"
            )
            if number == 1:
                frozen_payload = _retain_alertmanager_inputs(
                    evidence,
                    source,
                    cache / "pkg/mod",
                    go_archive,
                    base_archive,
                    output / originals["alertmanager-source"].filename,
                    output / originals["alertmanager-ui"].filename,
                    deadline,
                )
                (evidence / "frozen-inputs-inventory.json").write_text(
                    json.dumps(frozen_payload, indent=2) + "\n"
                )
            replay.append(
                {
                    "original": original_locks,
                    "derived": derived_locks,
                    "modules": online_modules,
                    "graph": online_graph,
                    "packages": online_packages,
                    "delta": delta,
                    "module_cache": module_inventory,
                    "whole_GOPATH": cache_inventory,
                    "whole_GOCACHE": build_inventory,
                    "source": source_inventory,
                    "version": version,
                }
            )
        _alertmanager_compare_replays(replay)
    except BaseException as error:
        primary = error
    finally:
        import signal

        signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            native.begin_cleanup()
        except BaseException as error:
            cleanup_error = error
        if owned_names and cleanup_error is None:
            try:
                binary = shutil.which("docker")
                if binary is None:
                    raise RuntimeError("Owned Docker cleanup binary unavailable.")
                cleanenv = docker_env
                raw = native.run(
                    [
                        binary,
                        "--config",
                        str(docker_config),
                        "ps",
                        "--all",
                        "--quiet",
                        "--no-trunc",
                        "--filter",
                        "label=pulseplate.alertmanager-module=" + owner_token,
                    ],
                    "cleanup-census",
                    cleanenv,
                    cwd=evidence,
                    cleaning=True,
                )
                ids = raw.decode("ascii").splitlines()
                for index, identifier in enumerate(ids):
                    if re.fullmatch(r"[0-9a-f]{64}", identifier) is None:
                        raise RuntimeError("Cleanup census identity malformed.")
                    _alertmanager_cleanup_member(
                        native,
                        binary,
                        identifier,
                        owned_ids,
                        owned_names,
                        owner_token,
                        cleanenv,
                        evidence,
                        index,
                        docker_config,
                    )
                absent = native.run(
                    [
                        binary,
                        "--config",
                        str(docker_config),
                        "ps",
                        "--all",
                        "--quiet",
                        "--no-trunc",
                        "--filter",
                        "label=pulseplate.alertmanager-module=" + owner_token,
                    ],
                    "cleanup-absence",
                    cleanenv,
                    cwd=evidence,
                    cleaning=True,
                )
                if absent.strip():
                    raise RuntimeError("Owned metadata container absence unproved.")
            except BaseException as error:
                cleanup_error = error
        if primary is not None or cleanup_error is not None:
            (evidence / "failure.json").write_text(
                json.dumps(
                    {
                        "primary_type": type(primary).__name__ if primary else None,
                        "cleanup_type": type(cleanup_error).__name__ if cleanup_error else None,
                        "owned_names": sorted(owned_names),
                        "owned_ids": sorted(owned_ids),
                        "native_records": native.records,
                    },
                    indent=2,
                )
                + "\n"
            )
    if primary is not None:
        if cleanup_error is not None:
            primary.add_note("Owned cleanup failed: " + type(cleanup_error).__name__)
        raise primary
    if cleanup_error is not None:
        raise cleanup_error
    report = {
        "metadata_only": True,
        "compiler_starts": 0,
        "compiler_counter_meaning": "Procedural fixed-command inventory excludes Go build/install/test; no whole-process-tree or external-compiler absence claim",
        "owned_container_names": sorted(owned_names),
        "owned_container_ids": sorted(owned_ids),
        "owned_container_absence_observed": True,
        "logical_build_starts": 0,
        "frozen_input_payload": frozen_payload,
        "loaded_base_ID": base_id,
        "base_export_representation": "Byte-bounded native Docker save of observed ID; original OCI compressed-blob digests not claimed",
        "whole_GOPATH_GOCACHE_individually_retained": True,
        "delta": replay[0]["delta"],
        "native_records": native.records,
        "elapsed_limit_seconds": int(seconds),
        "qualification_requires_separate_fullF_and_build_admission": True,
    }
    (evidence / "module-qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    if native.cleanup_deadline is None:
        raise RuntimeError("Owned finalization allowance unavailable.")
    _alertmanager_finalize_payload(evidence, native.cleanup_deadline)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alertmanager-module-qualify",
        action="store_true",
        help="Fixed manual metadata replay, zero builds; requires retained Go and base inputs.",
    )
    parser.add_argument(
        "--artifact",
        choices=["alertmanager"],
        help="Only the exact Alertmanager source/UI pair; default keeps incumbent inputs.",
    )
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
    parser.add_argument(
        "--integrity-rejection-dir",
        type=Path,
        help="Opt-in fresh private quarantine outside the build context/cache for rejected zlib bytes.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.alertmanager_module_qualify:
        if args.artifact != "alertmanager" or args.manifest != DEFAULT_MANIFEST:
            raise RuntimeError("Alertmanager qualification has no manifest/identity override.")
        _qualify_alertmanager_modules(args.output_dir)
        return 0
    artifacts = load_manifest(args.manifest, artifact=args.artifact)
    if args.artifact == "alertmanager":
        _fetch_alertmanager_pair(artifacts, args.output_dir)
        return 0
    for artifact in artifacts:
        _write_verified_artifact(
            artifact, args.output_dir, integrity_rejection_dir=args.integrity_rejection_dir
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
