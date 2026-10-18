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
from typing import TYPE_CHECKING, Any, BinaryIO, cast

if TYPE_CHECKING:
    from scripts.ci.prometheus_source_image import GitHubRead, Native
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "scripts" / "ci" / "docker_source_artifacts.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build" / "docker-sources"
ALLOWED_SOURCE_HOSTS = frozenset({"sqlite.org", "www.sqlite.org", "www.kernel.org"})
_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

# One observed successful metadata epoch; these selectors grant no compiler authority.
_ALERT_Q_SOURCE = "36cd171c4ebe44f63cb58d09a741b3d07098904d"
_ALERT_Q_BRANCH = "codex/dependency-alertmanager-remediation"
_ALERT_Q_RUN = 39018353942
_ALERT_Q_ARTIFACT = 12095483900
_ALERT_Q_JOB = 117354986951
_ALERT_Q_ZIP_SHA256 = "46276592068419330f3f73d71802a15ebff0db28f0e9b67cb63e5d054f26cce1"
_ALERT_PROBE_SHA256 = "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe"
_ALERT_TRIVY_SHA256 = "d89bcc6510a267f11b773398cbf1be5520ce39f9e8b6633178c4487f05b7d791"
_ALERT_BUILDX_SHA256 = "ae43fa08c796b44efc86d7a63c55f73f7c35f3101188dea7bf93bcd6f99577ba"
_ALERT_ORAS_SHA256 = "8c88339f9c1da7826734fa67fff5802ec9be6673a5e7db869758be96412fd9bf"
_ALERT_S_SOURCE = "df5ebd017bda93e31fbf9eccfd7cc7b98973a3c6"
_ALERT_S_RUN = 39030856891
_ALERT_S_ARTIFACT = 12100576545
_ALERT_S_JOB = 117390840636
_ALERT_S_ZIP_SHA256 = "ea0e4d24999792408f5a16eae9e803213eecc0e5c29095fd57a3d1520cc81a2e"
_ALERT_DB = {
    "db/trivy.db": "bf1f1b29d76cae9ff085d418cb4bfdb3906b6069f837abdef06558b8102dd1db",
    "db/metadata.json": "4b7a76b6270571c525a51ad67d3728a5f8237ce2c2a5b68a72948c24db616a83",
}
_ALERT_BASE_CONFIG = "sha256:55a757dc8ab862a4eb634c434261dcd26f17c186b54f7bce845404a335456110"
_ALERT_BASE_MANIFEST = "sha256:528f8a8d69ed17bdf99f19ade62e0a0e4c385de2791a94f4fa3c6286d8dad22c"
_ALERT_BUILDKIT = (
    "moby/buildkit:v0.32.2@sha256:040d34121c27906c4ff9ac152a30d52bf2c5d328d3bb748916bb3d2743c02528"
)
_ALERT_BUILD_METADATA = (
    "-X github.com/prometheus/common/version.Version=0.34.1 "
    "-X github.com/prometheus/common/version.Revision=73c6bfe7393929211294c1954f30d8ed78e4d0ad "
    "-X github.com/prometheus/common/version.Branch=HEAD "
    "-X github.com/prometheus/common/version.BuildUser=pulseplate@builder "
    "-X github.com/prometheus/common/version.BuildDate=19700101-00:00:00"
)
_ALERT_ASSEMBLY_LAUNCH = (
    "-I",
    "-S",
    "-B",
    "-c",
    "import os, sys; os.umask(0o022); os.execv(sys.argv[1], sys.argv[1:])",
)
_ALERT_Q_SOURCE_FILES = {
    "scripts/ci/fetch_docker_source_artifacts.py": "6f7775c25684725d11e57140c994203a9cc008ae805c01f49469fe28d88df648",
    ".github/workflows/cd.yml": "4e2abc1c8bab14bf97378b65e367433bb5b2435e08245fd12e2cd2cadba84ac0",
    "scripts/ci/docker_source_artifacts.json": "7230165fa5a61b17d7985d00e4c9f6dba9fca03fc64fd98a2b79e460469e575e",
    "deploy/alertmanager/Containerfile": "69af6364f15e3e5b9a4662a5919ff7f3b0209da0461cd7a85e01e21022abdb78",
    "deploy/alertmanager/alertmanager.yml": "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549",
}
_ALERT_S_SOURCE_FILES = {
    **_ALERT_Q_SOURCE_FILES,
    "scripts/ci/fetch_docker_source_artifacts.py": "0752e3be22abdf956ebdb995832a77d00aa556e18a2c1aa2220d3313ef3e3b81",
    ".github/workflows/cd.yml": "d7f5942a8394254add0a8de162413345908085edab89014c7bc9295b76729465",
}
_ALERT_ASSEMBLY_RECIPE_SHA256 = "8321b8129f819fadd64df26f0607c66fbabcef578bc76fe658e0d6d2cbab7347"
# Filled only by a later reviewed material update after actual full acceptance.
# Failed build artifacts and caller-supplied ancestors never select a producer.
_ALERT_ACCEPTED_CANDIDATE: dict[str, Any] | None = None

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
        "https://github.com/madler/zlib/commit/df84af25dc1942490e1d1c899a07619152a46148.patch?full_index=1",
        "zlib-gzwrite-fix-df84af25dc1942490e1d1c899a07619152a46148.patch",
        ("73d989d6" "57fc2056" "900feb1a" "83574139" "4b079f94" "3f8659fe" "441299ee" "bf91b310"),
    ),
    "zlib-gzwrite-null-fix": (
        ("e3dc0a85" "b7032e98" "380dec01" "1bc8f2c2" "ee0d8fca"),
        "https://github.com/madler/zlib/commit/e3dc0a85b7032e98380dec011bc8f2c2ee0d8fca.patch?full_index=1",
        "zlib-gzwrite-null-fix-e3dc0a85b7032e98380dec011bc8f2c2ee0d8fca.patch",
        ("2d97c97e" "020dfe05" "9b8b1981" "95a8fe42" "197f88b1" "184bb9ef" "0292a8af" "a535aa26"),
    ),
    "zlib-gzvprintf-return-fix": (
        ("bbc2ccf3" "d0de2675" "76b524b8" "75c769a7" "24a513b0"),
        "https://github.com/madler/zlib/commit/bbc2ccf3d0de267576b524b875c769a724a513b0.patch?full_index=1",
        "zlib-gzvprintf-return-fix-bbc2ccf3d0de267576b524b875c769a724a513b0.patch",
        ("28af72a5" "d4d20648" "1956ab11" "ab164090" "7577bc0c" "021ef3b5" "8344ea64" "f00c764c"),
    ),
    "zlib-gzprintf-return-fix": (
        ("7235b0a5" "81227c56" "a79a43ff" "828f8ef6" "794194c8"),
        "https://github.com/madler/zlib/commit/7235b0a581227c56a79a43ff828f8ef6794194c8.patch?full_index=1",
        "zlib-gzprintf-return-fix-7235b0a581227c56a79a43ff828f8ef6794194c8.patch",
        ("84bd6874" "0f1bf101" "fa85d3dd" "726a9c9b" "ec84c216" "3adf5b7b" "5c004bba" "62db6d5d"),
    ),
    "zlib-blocked-errno-fix": (
        ("813dac5d" "cb5902ed" "241e9b0d" "38abd2d8" "47a335a9"),
        "https://github.com/madler/zlib/commit/813dac5dcb5902ed241e9b0d38abd2d847a335a9.patch?full_index=1",
        "zlib-blocked-errno-fix-813dac5dcb5902ed241e9b0d38abd2d847a335a9.patch",
        ("d4fbd685" "ed4c2ec2" "d5e4962f" "0f6d5a98" "5ab1f542" "0bc1224d" "d262b419" "e7c26ab5"),
    ),
    "zlib-gzprintf-contract-fix": (
        ("d81c2d7e" "b705c622" "94ba0329" "92556720" "78e89115"),
        "https://github.com/madler/zlib/commit/d81c2d7eb705c62294ba03299255672078e89115.patch?full_index=1",
        "zlib-gzprintf-contract-fix-d81c2d7eb705c62294ba03299255672078e89115.patch",
        ("e9216856" "034689c7" "1656fb32" "dd1b25d3" "2304baf4" "42b7e9b8" "d454c732" "187b0bcf"),
    ),
    "zlib-errno-order-fix": (
        ("a82e0db3" "92178a3e" "05fb27bf" "551a6ce7" "57a47898"),
        "https://github.com/madler/zlib/commit/a82e0db392178a3e05fb27bf551a6ce757a47898.patch?full_index=1",
        "zlib-errno-order-fix-a82e0db392178a3e05fb27bf551a6ce757a47898.patch",
        ("33b8bc65" "706a2b85" "2e4b7ede" "ce112f13" "59078b3c" "8e475079" "d7b8d92d" "d4931d47"),
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
        "db74db83" "084f8ff5" "cf8d65ea" "5fd1bd63" "331f4c79" "fc809189" "d3735f35" "18ae2527"
    ),
    "zlib-gzwrite-null-fix": (
        "8be18219" "a658f1dd" "fa83d4e8" "f778d2c3" "be1ade11" "3863f166" "3929c399" "02e001cc"
    ),
    "zlib-gzvprintf-return-fix": (
        "96bd1c24" "2f09b244" "430bfe78" "54a9bb57" "a6e24a1e" "38e93bce" "f8ba946d" "22ecaf16"
    ),
    "zlib-gzprintf-return-fix": (
        "c5eff1cc" "8dd1997b" "16e0918e" "bf6074b9" "9bd38b2c" "244fb2bf" "2b697e74" "541a0987"
    ),
    "zlib-blocked-errno-fix": (
        "b1fcf877" "5123d729" "0a11e952" "21632fca" "7406cce1" "73820a09" "392c659e" "adb0ba0a"
    ),
    "zlib-gzprintf-contract-fix": (
        "22adf550" "e344229d" "f577ce66" "fddfce16" "451eb605" "20e8f68e" "5cae2192" "1b9bc0ea"
    ),
    "zlib-errno-order-fix": (
        "c12fbe1d" "d31e27c3" "90d4552c" "3862fe6b" "c50169c7" "3ab97a74" "e81682b6" "a713f1f9"
    ),
}
_PINNED_ZLIB_PATCH_SIZES = {
    "zlib-gzwrite-fix": 916,
    "zlib-gzwrite-null-fix": 833,
    "zlib-gzvprintf-return-fix": 809,
    "zlib-gzprintf-return-fix": 826,
    "zlib-blocked-errno-fix": 2629,
    "zlib-gzprintf-contract-fix": 2110,
    "zlib-errno-order-fix": 1538,
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
    """Remove only a retained full create ID whose exact name and owner label still match."""
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
    """Reconcile both complete replay inventories before the bounded sumdb exception."""
    from scripts.ci.prometheus_source_image import MAX_CACHE_BYTES

    if (
        type(replay) is not list
        or len(replay) != 2
        or any(type(item) is not dict for item in replay)
    ):
        raise RuntimeError("Alertmanager comparison requires two replay records.")
    inventories: list[list[dict[str, Any]]] = []
    # Validate every raw row before partitioning; retained inventories stay unfiltered.
    for item in replay:
        inventory = item.get("module_cache")
        if type(inventory) is not list or len(inventory) > 250000:
            raise RuntimeError("Alertmanager module_cache inventory shape or bound differs.")
        seen: set[str] = set()
        total = 0
        for row in inventory:
            if type(row) is not dict or set(row) != {"path", "size", "mode", "sha256"}:
                raise RuntimeError("Alertmanager module_cache row shape differs.")
            path, size, mode, digest = (row[key] for key in ("path", "size", "mode", "sha256"))
            if (
                type(path) is not str
                or "\\" in path
                or "\x00" in path
                or any(part in ("", ".", "..") for part in path.split("/"))
            ):
                raise RuntimeError("Alertmanager module_cache path is unsafe or noncanonical.")
            if (
                type(size) is not int
                or not 0 <= size <= MAX_CACHE_BYTES
                or type(mode) is not int
                or not 0 <= mode <= 0o7777
                or type(digest) is not str
                or _HEX_RE.fullmatch(digest) is None
            ):
                raise RuntimeError("Alertmanager module_cache row values differ.")
            if path in seen:
                raise RuntimeError("Alertmanager module_cache contains a duplicate path.")
            seen.add(path)
            total += size
            if total > MAX_CACHE_BYTES:
                raise RuntimeError("Alertmanager module_cache aggregate byte bound exceeded.")
        inventories.append(inventory)
    # Qualified Go 1.27.2 modfetch/sumdb.go owns precisely these cached lookups/tiles.
    # Their independent native state may differ; every other complete row stays exact.
    # This transient view never filters retention or each replay's raw offline stability.
    payloads = [
        [
            row
            for row in inventory
            if not (
                row["path"].split("/")[:3] == ["cache", "download", "sumdb"]
                and len(row["path"].split("/")) > 3
            )
        ]
        for inventory in inventories
    ]
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
        first, second = payloads if key == "module_cache" else (replay[0][key], replay[1][key])
        if first != second:
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
    """Bind the single native public-base config, platform, digest and thirteen diffIDs."""
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
    """Bound and retain the full native file/mode inventory in its one fresh footer."""
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
        replay: list[dict[str, object]] = []
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


def _alertmanager_accepted_producer(
    run_id: int | None = None,
    artifact_id: int | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Require the independent accepted A in this existing artifact owner before effects."""
    from scripts.ci.prometheus_source_image import require

    selected = _ALERT_ACCEPTED_CANDIDATE
    require(type(selected) is dict, "AM_accepted_producer_UNCONFIGURED_HOLD")
    selected = cast(dict[str, Any], selected)
    require(
        set(selected)
        == {
            "run",
            "attempt",
            "artifact",
            "source",
            "job",
            "zip_sha256",
            "source_files",
            "graph",
            "OCI_archive_sha256",
        }
        and all(
            type(selected.get(key)) is int and selected[key] > 0
            for key in ("run", "artifact", "job")
        )
        and type(selected.get("attempt")) is int
        and selected["attempt"] == 1
        and type(selected.get("source")) is str
        and re.fullmatch(r"[0-9a-f]{40}", selected["source"]) is not None
        and all(
            type(selected.get(key)) is str and _HEX_RE.fullmatch(selected[key]) is not None
            for key in ("zip_sha256", "OCI_archive_sha256")
        )
        and type(selected.get("source_files")) is dict
        and set(selected["source_files"])
        == {*_ALERT_Q_SOURCE_FILES, "tests/test_notify_premium_alias_checkpoint_failure.py"}
        and all(
            type(value) is str and _HEX_RE.fullmatch(value) is not None
            for value in selected["source_files"].values()
        )
        and selected["source_files"]["deploy/alertmanager/Containerfile"]
        == _ALERT_ASSEMBLY_RECIPE_SHA256
        and type(selected.get("graph")) is dict
        and bool(selected["graph"]),
        "AM_accepted_producer_canonical_binding",
    )
    if any(value is not None for value in (run_id, artifact_id, source)):
        require(
            type(run_id) is int
            and type(artifact_id) is int
            and type(source) is str
            and (run_id, artifact_id, source)
            == (selected["run"], selected["artifact"], selected["source"]),
            "AM_accepted_producer_exact_selectors",
        )
    return selected


def _alertmanager_authenticated_inputs(
    api: GitHubRead,
    run_id: int,
    artifact_id: int,
    source: str,
    destination: Path,
    *,
    kind: str = "qualification",
) -> dict[str, Any]:
    """Authenticate the three finite AM CD artifact cases; coordinates are not approval."""
    import base64
    from datetime import datetime, timezone
    from scripts.ci.prometheus_source_image import require

    require(kind in ("qualification", "support", "candidate"), "AM_closed_artifact_kind")
    accepted = (
        _alertmanager_accepted_producer(run_id, artifact_id, source) if kind == "candidate" else {}
    )
    selected_run, selected_artifact, selected_source, selected_job = (
        (_ALERT_Q_RUN, _ALERT_Q_ARTIFACT, _ALERT_Q_SOURCE, _ALERT_Q_JOB)
        if kind == "qualification"
        else (
            (_ALERT_S_RUN, _ALERT_S_ARTIFACT, _ALERT_S_SOURCE, _ALERT_S_JOB)
            if kind == "support"
            else (accepted["run"], accepted["artifact"], accepted["source"], accepted["job"])
        )
    )
    require(
        type(run_id) is int
        and run_id > 0
        and type(artifact_id) is int
        and artifact_id > 0
        and type(source) is str
        and re.fullmatch(r"[0-9a-f]{40}", source) is not None
        and (run_id, artifact_id, source) == (selected_run, selected_artifact, selected_source),
        "AM_qualification_exact_selectors",
    )
    job_name, artifact_name = {
        "qualification": ("alertmanager-module-qualification", "alertmanager-module-qualification"),
        "support": ("alertmanager-input-inspection", "alertmanager-input-inspection"),
        "candidate": ("alertmanager-candidate-build", "alertmanager-candidate"),
    }[kind]
    endpoint = "/repos/Katsiarynakavaleuskaya/PulsePlate"
    repository = api.json(endpoint)
    require(
        type(repository) is dict
        and type(repository.get("id")) is int
        and repository["id"] == 1043311030
        and repository.get("full_name") == "Katsiarynakavaleuskaya/PulsePlate",
        "AM_qualification_repository",
    )
    workflow = api.json(endpoint + "/actions/workflows/cd.yml")
    run = api.json(endpoint + f"/actions/runs/{run_id}")
    require(
        type(workflow) is dict
        and type(workflow.get("id")) is int
        and workflow.get("path") == ".github/workflows/cd.yml"
        and type(run) is dict
        and type(run.get("id")) is int
        and run["id"] == run_id
        and run.get("head_sha") == source
        and run.get("head_branch") == _ALERT_Q_BRANCH
        and run.get("event") == "workflow_dispatch"
        and type(run.get("run_attempt")) is int
        and run["run_attempt"] == 1
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
        and type(run.get("workflow_id")) is int
        and run["workflow_id"] == workflow["id"]
        and type(run.get("repository")) is dict
        and type(run["repository"].get("id")) is int
        and run["repository"]["id"] == 1043311030
        and type(run.get("head_repository")) is dict
        and type(run["head_repository"].get("id")) is int
        and run["head_repository"]["id"] == 1043311030,
        "AM_qualification_successful_CD_source",
    )
    jobs_endpoint = endpoint + f"/actions/runs/{run_id}/attempts/1/jobs"
    page = api.json(jobs_endpoint + "?per_page=100&page=1")
    require(type(page) is dict, "AM_qualification_jobs")
    jobs = api.pages(jobs_endpoint, "jobs", page.get("total_count"))
    selected = [job for job in jobs if job.get("name") == job_name]
    require(
        len(selected) == 1
        and type(selected[0].get("id")) is int
        and selected[0]["id"] == selected_job
        and type(selected[0].get("run_id")) is int
        and selected[0]["run_id"] == run_id
        and selected[0].get("head_sha") == source
        and selected[0].get("status") == "completed"
        and selected[0].get("conclusion") == "success",
        "AM_qualification_successful_unique_job",
    )
    source_hashes = {}
    source_contract = dict(_ALERT_Q_SOURCE_FILES)
    if kind == "support":
        source_contract = dict(_ALERT_S_SOURCE_FILES)
    elif kind == "candidate":
        source_contract = dict(accepted["source_files"])
    for path, expected in source_contract.items():
        record = api.json(endpoint + "/contents/" + path + "?ref=" + source)
        require(
            type(record) is dict
            and record.get("path") == path
            and record.get("type") == "file"
            and record.get("encoding") == "base64"
            and type(record.get("content")) is str
            and type(record.get("size")) is int
            and 0 < record["size"] <= 1024**2,
            "AM_qualification_source_blob",
        )
        raw = base64.b64decode(record["content"].replace("\n", ""), validate=True)
        require(
            len(raw) == record["size"] and sha256(raw).hexdigest() == expected,
            "AM_qualification_source_bytes",
        )
        source_hashes[path] = sha256(raw).hexdigest()
        if kind != "qualification":
            snapshot = destination.parent / (kind + "-producer-source") / path
            snapshot.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with snapshot.open("xb") as stream:
                stream.write(raw)
            snapshot.chmod(0o600)
    artifact = api.json(endpoint + f"/actions/artifacts/{artifact_id}")
    require(
        type(artifact) is dict
        and type(artifact.get("id")) is int
        and artifact["id"] == artifact_id
        and artifact.get("expired") is False
        and artifact.get("name") == f"{artifact_name}-{run_id}-1"
        and type(artifact.get("size_in_bytes")) is int
        and 0 < artifact["size_in_bytes"] <= 1024**3
        and type(artifact.get("digest")) is str
        and re.fullmatch(r"sha256:[0-9a-f]{64}", artifact["digest"]) is not None
        and (
            artifact["digest"]
            == "sha256:"
            + (
                accepted["zip_sha256"]
                if kind == "candidate"
                else (_ALERT_Q_ZIP_SHA256 if kind == "qualification" else _ALERT_S_ZIP_SHA256)
            )
        )
        and type(artifact.get("workflow_run")) is dict
        and type(artifact["workflow_run"].get("id")) is int
        and artifact["workflow_run"]["id"] == run_id
        and artifact["workflow_run"].get("head_sha") == source
        and type(artifact["workflow_run"].get("repository_id")) is int
        and artifact["workflow_run"]["repository_id"] == 1043311030
        and type(artifact["workflow_run"].get("head_repository_id")) is int
        and artifact["workflow_run"]["head_repository_id"] == 1043311030
        and type(artifact.get("expires_at")) is str,
        "AM_qualification_artifact_identity",
    )
    require(
        datetime.fromisoformat(artifact["expires_at"].replace("Z", "+00:00"))
        > datetime.now(timezone.utc),
        "AM_qualification_artifact_expired",
    )
    raw = api.raw(endpoint + f"/actions/artifacts/{artifact_id}/zip", maximum=1024**3)
    require(
        len(raw) == artifact["size_in_bytes"]
        and "sha256:" + sha256(raw).hexdigest() == artifact["digest"],
        "AM_qualification_download_bytes",
    )
    require(not destination.exists() and not destination.is_symlink(), "AM_download_not_fresh")
    with destination.open("xb") as stream:
        stream.write(raw)
    destination.chmod(0o600)
    return {
        "run": run_id,
        "attempt": 1,
        "artifact": artifact_id,
        "source": source,
        "zip_sha256": sha256(raw).hexdigest(),
        "source_files": source_hashes,
    }


def _alertmanager_package_read(api: GitHubRead) -> dict[str, Any]:
    """One finite GET of the existing package; this proves metadata READ only."""
    from scripts.ci.prometheus_source_image import one_object, require

    endpoint = "/users/Katsiarynakavaleuskaya/packages/container/pulseplate"
    raw = api._capture(
        [api.gh, "api", "--hostname", "github.com", "--method", "GET", endpoint], 1024**2
    )
    record = one_object(raw)
    repository = record.get("repository")
    require(
        record.get("name") == "pulseplate"
        and record.get("package_type") == "container"
        and record.get("visibility") == "public"
        and type(repository) is dict
        and repository.get("full_name") == "Katsiarynakavaleuskaya/PulsePlate"
        and type(repository.get("id")) is int
        and repository["id"] == 1043311030,
        "AM_existing_package_identity",
    )
    return {
        "endpoint": endpoint,
        "response_sha256": sha256(raw).hexdigest(),
        "metadata_read": True,
        "publication_write_proved": False,
    }


def _alertmanager_qualified_payload(archive: Path) -> dict[str, Any]:
    """Inspect complete retained AM inputs as data; no extraction or executable launch."""
    import zipfile
    from scripts.ci.prometheus_source_image import (
        MAX_CACHE_BYTES,
        _zip_members,
        one_object,
        require,
    )

    files = _zip_members(archive)

    def canonical(path: object) -> str:
        require(
            type(path) is str
            and "\\" not in path
            and "\x00" not in path
            and all(part not in ("", ".", "..") for part in path.split("/")),
            "AM_retained_member_path",
        )
        return cast(str, path)

    def rows(value: object) -> list[dict[str, Any]]:
        require(type(value) is list and len(value) <= 250000, "AM_retained_rows")
        value = cast(list[dict[str, Any]], value)
        seen = set()
        total = 0
        for row in value:
            require(
                type(row) is dict and set(row) == {"path", "size", "mode", "sha256"},
                "AM_retained_row_shape",
            )
            path = canonical(row["path"])
            require(path not in seen, "AM_retained_duplicate_path")
            seen.add(path)
            require(
                type(row["size"]) is int
                and 0 <= row["size"] <= MAX_CACHE_BYTES
                and type(row["mode"]) is int
                and 0 <= row["mode"] <= 0o7777
                and type(row["sha256"]) is str
                and _HEX_RE.fullmatch(row["sha256"]) is not None,
                "AM_retained_row_values",
            )
            total += row["size"]
        require(total <= MAX_CACHE_BYTES, "AM_retained_rows_byte_bound")
        return value

    def readonly(value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [dict(row, mode=0o555 if row["mode"] & 0o111 else 0o444) for row in value]

    require("artifact-payload-members.json" in files, "AM_retained_footer_missing")
    footer = one_object(files["artifact-payload-members.json"])
    require(
        set(footer) == {"files", "directories", "inventory_carrier_exception"}
        and footer["inventory_carrier_exception"]
        == (
            "Exactly artifact-payload-members.json is bound by external artifact bytes; "
            "its own hash is not recursively embedded."
        ),
        "AM_retained_footer",
    )
    declared = rows(footer["files"])
    require(
        set(files) == {row["path"] for row in declared} | {"artifact-payload-members.json"}
        and "failure.json" not in files,
        "AM_retained_complete_payload",
    )
    required_files = {
        "module-qualification.json",
        "frozen-inputs-inventory.json",
        "frozen-inputs.tar",
        "go-readonly-input-binding.json",
        "base-retention/base-image.tar",
        "public-base-inspect.stdout",
    }
    for number in (1, 2):
        prefix = "replay" + str(number)
        required_files |= {
            prefix + "-" + name
            for name in (
                "inventories.json",
                "offline-stability.json",
                "projections.json",
                "version.stdout",
            )
        }
        required_files |= {
            prefix + "-" + phase + "-" + lock
            for phase in ("original", "derived")
            for lock in ("go.mod", "go.sum")
        }
    require(required_files <= set(files), "AM_retained_required_payload_missing")
    implied = {
        "/".join(name.split("/")[:index])
        for name in files
        for index in range(1, len(name.split("/")))
    }
    require(type(footer["directories"]) is list, "AM_retained_directories")
    directories = {}
    for row in footer["directories"]:
        require(
            type(row) is dict
            and set(row) == {"path", "type", "mode"}
            and row["type"] == "directory"
            and type(row["mode"]) is int
            and 0 <= row["mode"] <= 0o7777,
            "AM_retained_directory_shape",
        )
        path = canonical(row["path"])
        require(path not in directories, "AM_retained_duplicate_directory")
        directories[path] = row["mode"]
    require(set(directories) == implied, "AM_retained_implied_directories")
    with zipfile.ZipFile(archive) as transported:
        for row in declared:
            raw = files[row["path"]]
            require(
                len(raw) == row["size"]
                and sha256(raw).hexdigest() == row["sha256"]
                and stat.S_IMODE(transported.getinfo(row["path"]).external_attr >> 16)
                == row["mode"],
                "AM_retained_file_bytes_modes",
            )
        require(
            stat.S_IMODE(transported.getinfo("artifact-payload-members.json").external_attr >> 16)
            == 0o600,
            "AM_retained_footer_mode",
        )
    report = one_object(files["module-qualification.json"])
    require(
        set(report)
        == {
            "metadata_only",
            "compiler_starts",
            "compiler_counter_meaning",
            "owned_container_names",
            "owned_container_ids",
            "owned_container_absence_observed",
            "logical_build_starts",
            "frozen_input_payload",
            "loaded_base_ID",
            "base_export_representation",
            "whole_GOPATH_GOCACHE_individually_retained",
            "delta",
            "native_records",
            "elapsed_limit_seconds",
            "qualification_requires_separate_fullF_and_build_admission",
        }
        and report["metadata_only"] is True
        and type(report["compiler_starts"]) is int
        and report["compiler_starts"] == 0
        and type(report["logical_build_starts"]) is int
        and report["logical_build_starts"] == 0
        and report["owned_container_absence_observed"] is True
        and report["whole_GOPATH_GOCACHE_individually_retained"] is True
        and type(report["elapsed_limit_seconds"]) is int
        and report["elapsed_limit_seconds"] == 825
        and report["qualification_requires_separate_fullF_and_build_admission"] is True,
        "AM_successful_metadata_footer",
    )
    frozen = one_object(files["frozen-inputs-inventory.json"])
    require(
        set(frozen) == {"path", "bytes", "sha256", "members", "private_HTTP_and_HOME_excluded"}
        and frozen["path"] == "frozen-inputs.tar"
        and frozen["private_HTTP_and_HOME_excluded"] is True
        and type(frozen["bytes"]) is int
        and 0 < frozen["bytes"] <= MAX_CACHE_BYTES
        and frozen == report["frozen_input_payload"],
        "AM_frozen_inventory",
    )
    raw_tar = files["frozen-inputs.tar"]
    require(
        len(raw_tar) == frozen["bytes"] and sha256(raw_tar).hexdigest() == frozen["sha256"],
        "AM_frozen_tar_bytes",
    )
    require(
        type(frozen["members"]) is list and len(frozen["members"]) <= 250000,
        "AM_frozen_member_bound",
    )
    frozen_files = {}
    declared_members = {}
    roots = {
        "source",
        "modules",
        "go-toolchain.tar.gz",
        "base-image.tar",
        "source.tar.gz",
        "ui.tar.gz",
    }
    for row in frozen["members"]:
        require(
            type(row) is dict and row.get("type") in ("file", "directory"), "AM_frozen_row_type"
        )
        expected = {"path", "mode", "bytes", "type"} | (
            {"sha256"} if row["type"] == "file" else set()
        )
        require(
            set(row) == expected
            and type(row["mode"]) is int
            and 0 <= row["mode"] <= 0o7777
            and type(row["bytes"]) is int
            and 0 <= row["bytes"] <= MAX_CACHE_BYTES,
            "AM_frozen_row_shape",
        )
        path = canonical(row["path"])
        require(
            path not in declared_members and path.split("/")[0] in roots,
            "AM_frozen_member_identity",
        )
        declared_members[path] = row
    require({path.split("/")[0] for path in declared_members} == roots, "AM_frozen_six_roots")
    root_bytes = {}
    observed = set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(raw_tar), mode="r:") as tar:
        for member in tar:
            path = canonical(member.name)
            require(path not in observed and path in declared_members, "AM_frozen_tar_membership")
            observed.add(path)
            row = declared_members[path]
            require(
                (member.isfile() if row["type"] == "file" else member.isdir())
                and member.mode == row["mode"]
                and member.size == row["bytes"]
                and member.uid == member.gid == member.mtime == 0
                and set(member.pax_headers) <= {"path"}
                and (
                    member.pax_headers.get("path", path) == path
                    or member.isdir()
                    and member.pax_headers.get("path") == path + "/"
                ),
                "AM_frozen_tar_type_mode",
            )
            if member.isfile():
                total += member.size
                require(total <= MAX_CACHE_BYTES, "AM_frozen_expanded_bound")
                stream = tar.extractfile(member)
                require(stream is not None, "AM_frozen_file_missing")
                stream = cast(BinaryIO, stream)
                body = stream.read(member.size + 1)
                require(
                    len(body) == member.size and sha256(body).hexdigest() == row["sha256"],
                    "AM_frozen_file_bytes",
                )
                frozen_files[path] = {
                    "path": path,
                    "size": member.size,
                    "mode": member.mode,
                    "sha256": row["sha256"],
                }
                if path in roots:
                    root_bytes[path] = body
            else:
                require(member.size == 0, "AM_frozen_directory_size")
    require(
        observed == set(declared_members)
        and set(root_bytes) == roots - {"source", "modules"}
        and declared_members["source"]["type"]
        == declared_members["modules"]["type"]
        == "directory",
        "AM_frozen_complete_readback",
    )
    replays = []
    for number in (1, 2):
        prefix = "replay" + str(number)
        inventory = one_object(files[prefix + "-inventories.json"])
        require(
            set(inventory)
            == {
                "original_source",
                "derived_source",
                "complete_GOMODCACHE",
                "whole_GOPATH",
                "whole_GOCACHE",
                "readonly_source",
                "readonly_GOPATH",
            },
            "AM_replay_inventory_fields",
        )
        for value in inventory.values():
            rows(value)
        require(
            readonly(inventory["derived_source"]) == inventory["readonly_source"]
            and readonly(inventory["whole_GOPATH"]) == inventory["readonly_GOPATH"],
            "AM_declared_readonly_mode_transition",
        )
        stability = one_object(files[prefix + "-offline-stability.json"])
        require(
            set(stability)
            == {
                "source_before",
                "source_after",
                "whole_GOPATH_before",
                "whole_GOPATH_after",
                "whole_GOCACHE_after",
            },
            "AM_offline_fields",
        )
        for value in stability.values():
            rows(value)
        require(
            stability["source_before"] == stability["source_after"] == inventory["readonly_source"]
            and stability["whole_GOPATH_before"]
            == stability["whole_GOPATH_after"]
            == inventory["readonly_GOPATH"]
            and stability["whole_GOCACHE_after"] == readonly(inventory["whole_GOCACHE"]),
            "AM_complete_raw_offline_stability",
        )
        projection = one_object(files[prefix + "-projections.json"])
        require(
            set(projection) == {"selected_modules", "package_graphs", "module_edges", "delta"}
            and type(projection["selected_modules"]) is list
            and bool(projection["selected_modules"])
            and type(projection["package_graphs"]) is dict
            and set(projection["package_graphs"]) == {"alertmanager", "amtool"}
            and type(projection["module_edges"]) is list
            and bool(projection["module_edges"])
            and projection["delta"] == report["delta"],
            "AM_replay_complete_projections",
        )
        for command in ("alertmanager", "amtool"):
            packages = projection["package_graphs"][command]
            require(
                type(packages) is list
                and bool(packages)
                and all(type(row) is dict for row in packages)
                and len(
                    [
                        row
                        for row in packages
                        if row.get("ImportPath")
                        == "github.com/prometheus/alertmanager/cmd/" + command
                    ]
                )
                == 1,
                "AM_both_retained_command_graphs",
            )
        original = {name: files[prefix + "-original-" + name] for name in ("go.mod", "go.sum")}
        derived = {name: files[prefix + "-derived-" + name] for name in original}
        before = {row["path"]: row for row in inventory["original_source"]}
        after = {row["path"]: row for row in inventory["derived_source"]}
        require(set(before) == set(after), "AM_replay_source_membership")
        for path, row in before.items():
            if path in original:
                require(
                    row["sha256"] == sha256(original[path]).hexdigest()
                    and row["size"] == len(original[path])
                    and after[path]["sha256"] == sha256(derived[path]).hexdigest()
                    and after[path]["size"] == len(derived[path]),
                    "AM_replay_lock_bytes",
                )
            else:
                require(row == after[path], "AM_replay_nonlock_source_drift")
        if number == 1:
            for root, expected_rows in (
                ("source", inventory["readonly_source"]),
                ("modules", readonly(inventory["complete_GOMODCACHE"])),
            ):
                actual = [
                    dict(row, path=path[len(root) + 1 :])
                    for path, row in frozen_files.items()
                    if path.startswith(root + "/")
                ]
                require(actual == expected_rows, "AM_frozen_readonly_epoch_" + root)
        replays.append(
            {
                "original": original,
                "derived": derived,
                "modules": projection["selected_modules"],
                "graph": projection["module_edges"],
                "packages": projection["package_graphs"],
                "delta": projection["delta"],
                "source": inventory["derived_source"],
                "module_cache": inventory["complete_GOMODCACHE"],
                "version": files[prefix + "-version.stdout"],
            }
        )
    _alertmanager_compare_replays(replays)
    require(replays[0]["version"] == b"go version go1.27.2 linux/amd64\n", "AM_retained_Go_version")
    delta = report["delta"]
    require(
        type(delta) is list
        and bool(delta)
        and all(
            type(row) is dict
            and set(row) == {"path", "before", "after", "class"}
            and all(type(row[field]) is str and row[field] for field in row)
            and row["before"] != row["after"]
            and row["class"] in ("authored", "solver_closure_reproduced_by_fixed_get")
            for row in delta
        ),
        "AM_complete_dependency_delta",
    )
    require(
        len({row["path"] for row in delta}) == len(delta)
        and {row["path"]: row["after"] for row in delta if row["class"] == "authored"}
        == {"golang.org/x/net": "v0.60.0", "google.golang.org/grpc": "v1.83.2"},
        "AM_two_authored_replacements",
    )
    go_binding = one_object(files["go-readonly-input-binding.json"])
    require(
        set(go_binding)
        == {"before_files", "after_files", "before_directories", "after_directories"},
        "AM_Go_binding_fields",
    )
    require(
        readonly(rows(go_binding["before_files"])) == rows(go_binding["after_files"]),
        "AM_Go_readonly_file_transition",
    )
    before_directories = go_binding["before_directories"]
    after_directories = go_binding["after_directories"]
    require(
        type(before_directories) is list
        and type(after_directories) is list
        and len(before_directories) == len(after_directories)
        and bool(before_directories),
        "AM_Go_directory_inventory",
    )
    seen_directories = set()
    for before, after in zip(before_directories, after_directories, strict=True):
        require(
            type(before) is dict
            and type(after) is dict
            and set(before) == set(after) == {"path", "mode"}
            and type(before["mode"]) is int
            and 0 <= before["mode"] <= 0o7777
            and type(after["mode"]) is int
            and after["mode"] == 0o555
            and before["path"] == after["path"],
            "AM_Go_directory_transition",
        )
        path = "." if before["path"] == "." else canonical(before["path"])
        require(path not in seen_directories, "AM_Go_duplicate_directory")
        seen_directories.add(path)
    _alertmanager_qualified_native(files, report)
    require(
        report["loaded_base_ID"]
        == _alertmanager_loaded_base([one_object(files["public-base-inspect.stdout"])]),
        "AM_loaded_base_binding",
    )
    require(
        root_bytes["base-image.tar"] == files["base-retention/base-image.tar"],
        "AM_retained_base_bytes",
    )
    plan = _alertmanager_input_plan(root_bytes, frozen_files, replays[0]["derived"])
    from scripts.ci.prometheus_source_image import GO

    require(
        sha256(root_bytes["go-toolchain.tar.gz"]).hexdigest() == GO.digest, "AM_retained_Go_archive"
    )
    return {
        "frozen_sha256": frozen["sha256"],
        "frozen_members": len(declared_members),
        "artifact_files": len(declared),
        "delta": report["delta"],
        "source_files": replays[0]["source"],
        "root_inputs": {name: sha256(raw).hexdigest() for name, raw in root_bytes.items()},
        "compiler_starts": 0,
        "build_admission": "HOLD_SEPARATE_HUMAN_DECISION",
        "plan": plan,
        "outstanding": [
            "full_supported_input_and_candidate_scans",
            "probe_origin_and_support",
            "version_matched_Buildx_context_syntax_review",
            "actual_compiler_context_and_budget",
        ],
    }


def _alertmanager_qualified_native(files: dict[str, bytes], report: dict[str, Any]) -> None:
    """Cross-bind the existing native protocol and every terminal output; no native call."""
    from scripts.ci.prometheus_source_image import one_object, require

    records = report["native_records"]
    require(type(records) is list and bool(records), "AM_native_records_missing")
    by_name = {}
    for row in records:
        require(
            type(row) is dict
            and set(row)
            == {
                "argv",
                "environment",
                "cwd",
                "exit",
                "failure",
                "stdout",
                "stderr",
                "stdout_sha256",
                "stderr_sha256",
            }
            and type(row["exit"]) is int
            and row["exit"] == 0
            and row["failure"] is None
            and type(row["argv"]) is list
            and bool(row["argv"])
            and all(type(arg) is str and arg for arg in row["argv"])
            and type(row["environment"]) is dict
            and all(
                type(key) is str and type(value) is str for key, value in row["environment"].items()
            )
            and type(row["cwd"]) is str,
            "AM_native_record_or_exit",
        )
        for kind in ("stdout", "stderr"):
            path = row[kind]
            require(
                type(path) is str
                and PurePosixPath(path).parent.name == "alertmanager-module-evidence",
                "AM_native_output_coordinate",
            )
            name = PurePosixPath(path).name
            require(
                name in files and sha256(files[name]).hexdigest() == row[kind + "_sha256"],
                "AM_native_output_bytes",
            )
        name = PurePosixPath(row["stdout"]).name.removesuffix(".stdout")
        require(name not in by_name, "AM_native_duplicate_command")
        by_name[name] = row
    expected = {
        "public-base-pull",
        "public-base-inspect",
        "retain-physical-base",
        "cleanup-census",
        "cleanup-absence",
    }
    ids = set()
    names = set()
    for number in (1, 2):
        prefix = "replay" + str(number)
        expected |= {
            prefix + "-" + name
            for name in (
                "version",
                "baseline-download",
                "baseline-modules",
                "two-authored-replacements",
                "derived-download",
                "online-verify",
                "online-modules",
                "online-graph",
                "online-alertmanager",
                "online-amtool",
            )
        }
        for command in ("version", "verify", "modules", "graph", "alertmanager", "amtool"):
            expected |= {
                prefix + "-" + stage + "-" + command
                for stage in ("create", "offline", "wait", "terminal")
            }
            identifier = files[prefix + "-create-" + command + ".stdout"].decode("ascii").strip()
            require(
                re.fullmatch(r"[0-9a-f]{64}", identifier) is not None and identifier not in ids,
                "AM_native_owned_ID",
            )
            ids.add(identifier)
            terminal = one_object(files[prefix + "-terminal-" + command + ".stdout"])
            name = terminal.get("Name", "").lstrip("/")
            match = re.fullmatch(
                r"pulseplate-alert-module-([0-9a-f]{32})-" + str(number) + "-" + command, name
            )
            require(match is not None, "AM_native_owned_name")
            match = cast(re.Match[str], match)
            names.add(name)
            _alertmanager_command_exit(
                terminal,
                identifier,
                name,
                match.group(1),
                files[prefix + "-wait-" + command + ".stdout"],
            )
    expected |= {
        "cleanup-" + stage + "-" + str(index)
        for index in range(12)
        for stage in ("inspect", "remove")
    }
    require(
        set(by_name) == expected
        and report["owned_container_ids"] == sorted(ids)
        and report["owned_container_names"] == sorted(names)
        and files["cleanup-absence.stdout"].strip() == b"",
        "AM_native_complete_commands_and_cleanup",
    )


def _alertmanager_input_plan(
    root_bytes: dict[str, bytes], frozen_files: dict[str, dict[str, Any]], locks: dict[str, bytes]
) -> dict[str, Any]:
    """Bound the retained source/UI and declare future argv, never execute a build."""
    from scripts.ci.prometheus_source_image import require

    source_rows = {}
    source_bytes = {}
    ui_hashes = {}
    for artifact in load_manifest(DEFAULT_MANIFEST, artifact="alertmanager"):
        is_ui = artifact.name == "alertmanager-ui"
        raw = root_bytes["ui.tar.gz" if is_ui else "source.tar.gz"]
        validate_source_payload(artifact, raw)
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as upstream:
            for member in upstream:
                if not member.isfile():
                    continue
                relative = member.name.split("/", 1)[1]
                path = "source/" + ("ui/app/dist/" if is_ui else "") + relative
                stream = upstream.extractfile(member)
                require(stream is not None, "AM_upstream_member_missing")
                stream = cast(BinaryIO, stream)
                body = stream.read(member.size + 1)
                require(len(body) == member.size, "AM_upstream_member_size")
                if is_ui:
                    require(
                        not member.mode & 0o111
                        and not body.startswith(
                            (
                                b"\x7fELF",
                                b"MZ",
                                b"\xfe\xed\xfa\xce",
                                b"\xce\xfa\xed\xfe",
                                b"\xfe\xed\xfa\xcf",
                                b"\xcf\xfa\xed\xfe",
                                b"\xca\xfe\xba\xbe",
                            )
                        ),
                        "AM_UI_contains_native_executable",
                    )
                    ui_hashes[relative] = sha256(body).hexdigest()
                if not is_ui and relative in locks:
                    body = locks[relative]
                source_rows[path] = {
                    "path": path,
                    "size": len(body),
                    "mode": 0o555 if member.mode & 0o111 else 0o444,
                    "sha256": sha256(body).hexdigest(),
                }
                if not is_ui and relative in (
                    "VERSION",
                    "ui/web.go",
                    "LICENSE",
                    "NOTICE",
                    ".promu.yml",
                ):
                    source_bytes[relative] = body
    require(
        source_rows
        == {path: row for path, row in frozen_files.items() if path.startswith("source/")},
        "AM_complete_source_UI_embedding",
    )
    require(
        source_bytes.get("VERSION") == b"0.34.1\n"
        and b"//go:embed app/dist" in source_bytes.get("ui/web.go", b""),
        "AM_source_UI_recipe",
    )
    context = []
    for path in ("deploy/alertmanager/Containerfile", "deploy/alertmanager/alertmanager.yml"):
        raw = (REPO_ROOT / path).read_bytes()
        require(
            sha256(raw).hexdigest()
            == (
                _ALERT_ASSEMBLY_RECIPE_SHA256
                if path == "deploy/alertmanager/Containerfile"
                else _ALERT_Q_SOURCE_FILES[path]
            ),
            "AM_current_COPY_recipe_input_drift",
        )
        context.append(
            {"path": path.split("/")[-1], "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
        )
    context += [
        {
            "path": name,
            "sha256": sha256(source_bytes[name]).hexdigest(),
            "bytes": len(source_bytes[name]),
        }
        for name in ("LICENSE", "NOTICE")
    ]
    flags = _ALERT_BUILD_METADATA
    return {
        "state": "DECLARED_ONLY_COMPILER_HOLD",
        "upstream_recipe_sha256": sha256(source_bytes[".promu.yml"]).hexdigest(),
        "source_UI_file_hashes": source_rows,
        "UI_file_hashes": ui_hashes,
        "assembly_input_members": context,
        "storage-dir": {"empty": True, "mode": 0o700, "final_uid": 65534, "final_gid": 65534},
        "probe": {
            "sha256": _ALERT_PROBE_SHA256,
            "origin": "HOLD_SEPARATE_RECOVERY_AND_SUPPORT_EVIDENCE",
        },
        "compiler_environment": {
            "PATH": "/toolchain/bin:/usr/bin:/bin",
            "TMPDIR": "/work/tmp",
            "GOFLAGS": "",
            "GOTOOLCHAIN": "local",
            "CGO_ENABLED": "0",
            "GOOS": "linux",
            "GOARCH": "amd64",
            "GOPROXY": "off",
            "GOSUMDB": "off",
            "GOMODCACHE": "/modules",
            "GOPATH": "/work/gopath",
            "GOCACHE": "/work/cache",
            "HOME": "/work/home",
        },
        "compiler_argv": [
            [
                "/toolchain/bin/go",
                "build",
                "-mod=readonly",
                "-tags=netgo",
                "-trimpath",
                "-buildvcs=false",
                "-ldflags",
                flags,
                "-o",
                "/out/" + name,
                "./cmd/" + name,
            ]
            for name in ("alertmanager", "amtool")
        ],
        "compiler_cwd": "/source",
        "outputs": ["alertmanager", "amtool"],
        "output_hashes": None,
        "produced_image_digest": None,
        "assembly_argv": [
            "<absolute-same-sys.executable>",
            *_ALERT_ASSEMBLY_LAUNCH,
            "docker",
            "--config",
            "<owned-pair-docker-config>",
            "buildx",
            "build",
            "--builder",
            "<fresh-owned-AM-builder>",
            "--platform=linux/amd64",
            "--provenance=false",
            "--sbom=false",
            "--annotation",
            "manifest-descriptor:org.opencontainers.image.ref.name=candidate",
            "--network=none",
            "--pull=false",
            "--build-context",
            "gcr.io/distroless/static-debian13@sha256:2293b36c7c9082bf4115aab724b4d2cddec82c8eba39bf27ac0517e159acf150=oci-layout:///inputs/base-layout@sha256:528f8a8d69ed17bdf99f19ade62e0a0e4c385de2791a94f4fa3c6286d8dad22c",
            "--file",
            "/context/Containerfile",
            "--output",
            "type=oci,tar=false,dest=/out/candidate-layout",
            "/context",
        ],
        "assembly_execution": "UNOBSERVED_UNTIL_THE_ONE_SEPARATELY_ADMITTED_PAIR_BUILD",
        "declared_tool_versions": {"buildx": "0.37.0", "buildkit": "0.32.2"},
        "builder_argv_after_human_admission": [
            "docker",
            "--config",
            "<owned-pair-docker-config>",
            "buildx",
            "create",
            "--driver=docker-container",
            "--driver-opt=image=" + _ALERT_BUILDKIT,
            "--driver-opt=network=none",
            "--driver-opt=env.PULSEPLATE_AM_OWNER=<fresh-owned-token>",
            "--name",
            "<fresh-owned-AM-builder>",
            "--use",
        ],
        "proposed_pair_seconds": 1800,
        "proposed_cleanup_seconds": 45,
        "budget_and_cleanup": "PROPOSAL_ONLY_REQUIRES_SEPARATE_HUMAN_BUILD_ADMISSION",
    }


def _alertmanager_support_observation(archive: Path, output: Path) -> dict[str, Any]:
    """One separately invoked compiler-free native support observation; no Docker start/build."""
    import shutil
    import struct
    import uuid
    import zipfile
    from scripts.ci.prometheus_source_image import (
        Native,
        _blob,
        _layout_root,
        file_hash,
        fresh_directory,
        one_object,
        require,
    )

    require(file_hash(archive) == _ALERT_Q_ZIP_SHA256, "AM_support_exact_retained_Q")
    seconds = os.environ.get("ALERTMANAGER_SUPPORT_SECONDS", "")
    require(
        re.fullmatch(r"[1-9][0-9]{0,3}", seconds) is not None and int(seconds) <= 1800,
        "AM_support_operation_budget",
    )
    scan_timeout = os.environ.get("ALERTMANAGER_SCAN_TIMEOUT_SECONDS", "")
    scan_process = os.environ.get("ALERTMANAGER_SCAN_PROCESS_SECONDS", "")
    # Workflow env owns execution values; these are the incumbent safety ceilings,
    # never fallback/default durations or permission to enlarge a scan budget.
    require(
        re.fullmatch(r"[1-9][0-9]{0,3}", scan_timeout) is not None
        and re.fullmatch(r"[1-9][0-9]{0,3}", scan_process) is not None
        and int(scan_timeout) <= 300
        and int(scan_timeout) < int(scan_process) <= 330
        and int(scan_process) <= int(seconds),
        "AM_support_scan_budgets",
    )
    scanner = Path(os.environ.get("TRIVY_BIN", ""))
    require(
        scanner.is_absolute()
        and scanner.is_file()
        and not scanner.is_symlink()
        and file_hash(scanner) == _ALERT_TRIVY_SHA256,
        "AM_support_pinned_scanner",
    )
    buildx = Path(os.environ.get("BUILDX_BIN", ""))
    require(
        buildx.is_absolute()
        and buildx.is_file()
        and not buildx.is_symlink()
        and file_hash(buildx) == _ALERT_BUILDX_SHA256,
        "AM_support_pinned_Buildx",
    )
    docker = shutil.which("docker")
    require(docker is not None and Path(docker).is_absolute(), "AM_support_Docker_missing")
    docker = cast(str, docker)
    work = output / "native-support"
    fresh_directory(work)
    shutil.copyfile(scanner, work / "trivy")
    scanner = work / "trivy"
    scanner.chmod(0o555)
    require(file_hash(scanner) == _ALERT_TRIVY_SHA256, "AM_copied_scanner_bytes")
    evidence = work / "evidence"
    fresh_directory(evidence)
    config = work / "empty-docker-config"
    fresh_directory(config)
    (config / "cli-plugins").mkdir(mode=0o700)
    shutil.copyfile(buildx, config / "cli-plugins/docker-buildx")
    plugin = config / "cli-plugins/docker-buildx"
    plugin.chmod(0o555)
    require(file_hash(plugin) == _ALERT_BUILDX_SHA256, "AM_copied_Buildx_bytes")
    native = Native(evidence, time.monotonic() + int(seconds), 45)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "DOCKER_CONFIG": str(config),
        "LANG": "C.UTF-8",
    }
    docker_prefix = [docker, "--config", str(config)]
    base_archive = work / "base-image.tar"
    with zipfile.ZipFile(archive) as retained:
        base_archive.write_bytes(retained.read("base-retention/base-image.tar"))
        original_base = one_object(retained.read("public-base-inspect.stdout"))
    base_archive.chmod(0o600)
    base_id = original_base["Id"]
    layout = work / "base-layout"
    fresh_directory(layout)
    layout_rows, seen = [], set()
    with tarfile.open(base_archive, mode="r:") as saved:
        for member in saved:
            parts = member.name.split("/")
            require(
                all(part not in ("", ".", "..") for part in parts)
                and "\\" not in member.name
                and member.name not in seen
                and (member.isfile() or member.isdir()),
                "AM_base_export_member",
            )
            seen.add(member.name)
            target = layout.joinpath(*parts)
            if member.isdir():
                target.mkdir(mode=0o700, parents=True, exist_ok=True)
            else:
                require(member.size <= base_archive.stat().st_size, "AM_base_export_size")
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                stream = saved.extractfile(member)
                require(stream is not None, "AM_base_export_missing_bytes")
                stream = cast(BinaryIO, stream)
                raw = stream.read(member.size + 1)
                require(len(raw) == member.size and not target.exists(), "AM_base_export_file")
                with target.open("xb") as destination:
                    destination.write(raw)
                target.chmod(0o600)
                layout_rows.append(
                    {"path": member.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
                )
    descriptor = _layout_root(layout)
    manifest = one_object(_blob(layout, descriptor))
    configuration = one_object(_blob(layout, manifest["config"]))
    require(
        manifest["config"]["digest"] == base_id
        and type(manifest.get("layers")) is list
        and configuration.get("rootfs", {}).get("diff_ids") == original_base["RootFS"]["Layers"]
        and [layer.get("digest") for layer in manifest["layers"]]
        == original_base["RootFS"]["Layers"]
        and configuration.get("os") == original_base["Os"]
        and configuration.get("architecture") == original_base["Architecture"],
        "AM_base_export_config_diffIDs",
    )
    for layer in manifest["layers"]:
        require(
            layer.get("mediaType") == "application/vnd.oci.image.layer.v1.tar",
            "AM_base_export_layer_representation",
        )
        _blob(layout, layer)
    old_image = (
        "prom/alertmanager@sha256:84967b9b7ba45e38a9278d3e594305f43d4993c310df3905b51138b816c365f3"
    )
    old_id = "sha256:53622b714941158bc20cc92a7571aef515556218eef914b7b8ec5b2a0cb6f607"
    token = uuid.uuid4().hex
    name = "pulseplate-am-support-" + token
    owned = ""
    create_attempted = False
    primary: BaseException | None = None
    cleanup_error: BaseException | None = None
    result: dict[str, Any] = {
        "compiler_starts": 0,
        "logical_build_starts": 0,
        "scope": "retained base and exact recovered upstream probe; no candidate image exists",
        "support_status": "HOLD_NOT_OBSERVED",
    }
    try:
        native.run(
            [*docker_prefix, "image", "load", "--input", str(base_archive)],
            "base-load",
            env,
            cwd=work,
        )
        loaded = one_object(
            native.run(
                [*docker_prefix, "image", "inspect", "--format", "{{json .}}", base_id],
                "base-inspect",
                env,
                cwd=work,
            )
        )
        require(
            all(
                loaded.get(key) == original_base.get(key)
                for key in ("Id", "Os", "Architecture", "RootFS")
            ),
            "AM_loaded_export_config_platform_diffIDs",
        )
        result["base"] = {
            "archive_sha256": file_hash(base_archive),
            "config": base_id,
            "RootFS": loaded["RootFS"],
            "original_compressed_OCI_claim": False,
            "actual_local_OCI_descriptor": descriptor,
            "complete_export_file_inventory": layout_rows,
        }
        native.run(
            [*docker_prefix, "pull", "--platform", "linux/amd64", old_image],
            "probe-public-origin-pull",
            env,
            cwd=work,
        )
        old = one_object(
            native.run(
                [*docker_prefix, "image", "inspect", "--format", "{{json .}}", old_id],
                "probe-origin-inspect",
                env,
                cwd=work,
            )
        )
        require(
            old.get("Id") == old_id
            and old.get("Os") == "linux"
            and old.get("Architecture") == "amd64"
            and type(old.get("RepoDigests")) is list
            and sum(value in (old_image, "docker.io/" + old_image) for value in old["RepoDigests"])
            == 1,
            "AM_probe_official_origin",
        )
        create_attempted = True
        candidate = (
            native.run(
                [
                    *docker_prefix,
                    "create",
                    "--pull=never",
                    "--name",
                    name,
                    "--label",
                    "pulseplate.alertmanager-support=" + token,
                    "--network=none",
                    "--read-only",
                    "--cap-drop=ALL",
                    "--security-opt=no-new-privileges:true",
                    "--entrypoint=/bin/[",
                    old_id,
                ],
                "probe-owned-create-never-start",
                env,
                cwd=work,
            )
            .decode("ascii")
            .strip()
        )
        require(re.fullmatch(r"[0-9a-f]{64}", candidate) is not None, "AM_probe_owned_ID")
        owned = candidate
        probe = work / "probe-bin-bracket"
        native.run(
            [*docker_prefix, "cp", owned + ":/bin/[", str(probe)],
            "probe-native-copy",
            env,
            cwd=work,
        )
        info = probe.lstat()
        require(
            stat.S_ISREG(info.st_mode)
            and not probe.is_symlink()
            and info.st_nlink == 1
            and info.st_size == 1173752
            and file_hash(probe) == _ALERT_PROBE_SHA256,
            "AM_probe_exact_physical_bytes",
        )
        probe_bytes = probe.read_bytes()
        header = probe_bytes[:64]
        require(
            header[:6] == b"\x7fELF\x02\x01" and struct.unpack_from("<HH", header, 16) == (2, 62),
            "AM_probe_ELF64_x86_64",
        )
        offset = struct.unpack_from("<Q", header, 32)[0]
        width, count = struct.unpack_from("<HH", header, 54)
        require(
            width == 56
            and 0 < count <= 256
            and 64 <= offset
            and offset + width * count <= len(probe_bytes),
            "AM_probe_program_header_bounds",
        )
        program_types = [
            struct.unpack_from("<I", probe_bytes, offset + width * index)[0]
            for index in range(count)
        ]
        require(
            3 not in program_types and b"BusyBox v1.38.0 " in probe_bytes,
            "AM_probe_static_ELF_and_version",
        )
        result["probe"] = {
            "origin": old_image,
            "config": old_id,
            "member": "bin/[",
            "sha256": file_hash(probe),
            "bytes": info.st_size,
            "native_copy_mode": stat.S_IMODE(info.st_mode),
            "ELF_machine": 62,
            "program_header_types": program_types,
            "PT_INTERP_present": False,
            "embedded_version": "BusyBox v1.38.0",
            "executed": False,
        }
        old_archive = work / "known-vulnerable-control.tar"
        native.run(
            [*docker_prefix, "image", "save", "--output", str(old_archive), old_id],
            "retain-known-vulnerable-control",
            env,
            cwd=work,
        )
        old_archive.chmod(0o600)
        result["buildx_version"] = native.run(
            [*docker_prefix, "buildx", "version"], "buildx-version-only", env, cwd=work
        ).decode("utf-8")
        require(
            re.search(r"(?:^|\s)v?0\.37\.0(?:\s|$)", result["buildx_version"]) is not None,
            "AM_support_Buildx_version",
        )
        help_bytes = native.run(
            [*docker_prefix, "buildx", "build", "--help"], "buildx-help-only", env, cwd=work
        )
        require(
            all(flag in help_bytes for flag in (b"--build-context", b"--network", b"--output")),
            "AM_buildx_CLI_flags",
        )
        require(file_hash(plugin) == _ALERT_BUILDX_SHA256, "AM_executed_Buildx_drift")
        result["buildx"] = {
            "docker_sha256": file_hash(Path(docker)),
            "buildx_sha256": file_hash(plugin),
            "help_sha256": sha256(help_bytes).hexdigest(),
            "scope": "version and CLI flags only; exact digest-key local OCI resolution remains unexecuted",
        }
        version = one_object(
            native.run(
                [str(scanner), "--version", "--format", "json"], "scanner-version", env, cwd=work
            )
        )
        require(version.get("Version") == "0.74.0", "AM_support_scanner_version")
        require(file_hash(scanner) == _ALERT_TRIVY_SHA256, "AM_executed_scanner_drift")
        cache = work / "trivy-cache"
        fresh_directory(cache)
        empty_config, empty_ignore = work / "empty-trivy.yaml", work / "empty.trivyignore"
        empty_config.write_bytes(b"{}\n")
        empty_ignore.write_bytes(b"")
        native.run(
            [
                str(scanner),
                "image",
                "--config",
                str(empty_config),
                "--cache-dir",
                str(cache),
                "--db-repository",
                "ghcr.io/aquasecurity/trivy-db",
                "--download-db-only",
                "--skip-version-check",
                "--disable-telemetry",
            ],
            "scanner-DB-acquisition",
            env,
            cwd=work,
        )
        db = {name: file_hash(cache / name) for name in ("db/trivy.db", "db/metadata.json")}
        result["scanner"] = {
            "sha256": file_hash(scanner),
            "version": version,
            "DB": db,
            "DB_metadata": one_object((cache / "db/metadata.json").read_bytes()),
        }

        def scan(kind: str, subject: Path, label: str) -> dict[str, Any]:
            destination = evidence / (label + ".private.json")
            require(not destination.exists(), "AM_scan_report_not_fresh")
            argv = [
                str(scanner),
                kind,
                "--config",
                str(empty_config),
                "--cache-dir",
                str(cache),
                "--skip-db-update",
                "--skip-java-db-update",
                "--skip-vex-repo-update",
                "--offline-scan",
                "--skip-version-check",
                "--disable-telemetry",
                "--scanners",
                "vuln,secret",
                "--pkg-types",
                "os,library",
                "--list-all-pkgs",
                "--severity",
                "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL",
                "--format",
                "json",
                "--exit-code",
                "0",
                "--ignore-unfixed=false",
                "--ignorefile",
                str(empty_ignore),
                "--timeout",
                scan_timeout + "s",
                "--output",
                str(destination),
            ]
            argv += ["--input", str(subject)] if kind == "image" else [str(subject)]
            native.run(argv, label, env, cwd=work, maximum_seconds=int(scan_process))
            require(
                destination.is_file()
                and not destination.is_symlink()
                and 0 < destination.stat().st_size <= 64 * 1024**2,
                "AM_scan_report_missing_or_bound",
            )
            destination.chmod(0o600)
            value: dict[str, Any] = one_object(destination.read_bytes())
            # v0.74.0 Report.Results uses json:",omitempty". Preserve native bytes;
            # only these two exact executed subjects may have no supported result.
            require(
                type(value.get("SchemaVersion")) is int
                and value["SchemaVersion"] == 2
                and (
                    type(value.get("Results")) is list
                    or "Results" not in value
                    and label in ("secret-negative", "probe-full-supported-scan")
                ),
                "AM_scan_native_schema",
            )
            require(
                {name: file_hash(cache / name) for name in db} == db
                and file_hash(scanner) == _ALERT_TRIVY_SHA256
                and file_hash(plugin) == _ALERT_BUILDX_SHA256,
                "AM_scanner_or_DB_drift",
            )
            return value

        positive, negative = work / "positive", work / "negative"
        fresh_directory(positive)
        fresh_directory(negative)
        marker = "ghp_" + "012345678901234567890123456789abcdef"
        (positive / "credentials.txt").write_text("GITHUB_PAT=" + marker + "\n")
        (negative / "credentials.txt").write_text("plain harmless operational text\n")
        first = scan("fs", positive, "secret-positive")
        second = scan("fs", negative, "secret-negative")
        result["secret_controls"] = _alertmanager_secret_controls(
            first, second, str(positive), str(negative)
        )
        vulnerable = scan("image", old_archive, "known-vulnerable-full-control")
        result["vulnerability_control"] = _alertmanager_vulnerability_control(vulnerable, old_id)
        base_scan = scan("image", base_archive, "base-full-supported-scan")
        require(
            base_scan.get("ArtifactType") == "container_image"
            and type(base_scan.get("Metadata")) is dict
            and base_scan["Metadata"].get("ImageID") == base_id,
            "AM_base_scan_exact_subject",
        )
        rootfs = work / "probe-rootfs"
        fresh_directory(rootfs)
        (rootfs / "usr/bin").mkdir(parents=True)
        for probe_target in ("wget", "httpd"):
            shutil.copyfile(probe, rootfs / "usr/bin" / probe_target)
            (rootfs / "usr/bin" / probe_target).chmod(0o755)
        probe_scan = scan("rootfs", rootfs, "probe-full-supported-scan")
        require(
            probe_scan.get("ArtifactName") == str(rootfs)
            and probe_scan.get("ArtifactType") == "filesystem",
            "AM_probe_scan_exact_subject",
        )
        result["base_scan"] = _alertmanager_support_inventory(base_scan)
        result["probe_scan"] = _alertmanager_support_inventory(probe_scan, probe_path=str(rootfs))
        require(
            result["base_scan"]["packages"]
            and any(row.get("Class") == "os-pkgs" for row in base_scan["Results"]),
            "AM_base_supported_OS_inventory_missing",
        )
        result["probe_scan"]["support_limit"] = (
            "Pinned Trivy has no standalone BusyBox package-CVE recognizer and skips ELF plaintext-secret analysis; "
            "an actual empty supported inventory is retained, never a CVE-free or secret-free claim."
        )
        result["support_status"] = "OBSERVED_NATIVE_SUPPORTED_DOMAIN"
        result["final_candidate_acceptance"] = "UNACHIEVED_NO_CANDIDATE_OR_BUILD"
        require(
            file_hash(base_archive) == result["base"]["archive_sha256"]
            and file_hash(probe) == result["probe"]["sha256"],
            "AM_support_subject_drift",
        )
    except BaseException as error:
        primary = error
        result["failure"] = type(error).__name__ + ":" + str(error)
    finally:
        try:
            native.begin_cleanup()
            census = (
                native.run(
                    [
                        *docker_prefix,
                        "ps",
                        "--all",
                        "--quiet",
                        "--no-trunc",
                        "--filter",
                        "label=pulseplate.alertmanager-support=" + token,
                    ],
                    "support-cleanup-census",
                    env,
                    cwd=work,
                    cleaning=True,
                )
                .decode("ascii")
                .splitlines()
            )
            require(
                len(census) <= 1 and all(re.fullmatch(r"[0-9a-f]{64}", value) for value in census),
                "AM_support_cleanup_census_ID",
            )
            for identifier in census:
                require(
                    create_attempted and (not owned or identifier == owned),
                    "AM_support_cleanup_attempt_binding",
                )
                observed = one_object(
                    native.run(
                        [*docker_prefix, "inspect", "--format", "{{json .}}", identifier],
                        "support-cleanup-inspect",
                        env,
                        cwd=work,
                        cleaning=True,
                    )
                )
                require(
                    observed.get("Id") == identifier
                    and observed.get("Name") == "/" + name
                    and observed.get("Config", {})
                    .get("Labels", {})
                    .get("pulseplate.alertmanager-support")
                    == token,
                    "AM_support_cleanup_ownership",
                )
                native.run(
                    [*docker_prefix, "rm", "--force", "--volumes", identifier],
                    "support-cleanup-remove",
                    env,
                    cwd=work,
                    cleaning=True,
                )
            absence = native.run(
                [
                    *docker_prefix,
                    "ps",
                    "--all",
                    "--quiet",
                    "--no-trunc",
                    "--filter",
                    "label=pulseplate.alertmanager-support=" + token,
                ],
                "support-cleanup-absence",
                env,
                cwd=work,
                cleaning=True,
            )
            require(not absence.strip(), "AM_support_owned_absence")
            result["owned_container_absence_observed"] = True
        except BaseException as error:
            cleanup_error = error
            result["cleanup_failure"] = type(error).__name__
        result["native_records"] = native.records
        (work / "support-observation.json").write_text(json.dumps(result, indent=2) + "\n")
        if native.cleanup_deadline is not None:
            try:
                _alertmanager_finalize_payload(work, native.cleanup_deadline)
            except BaseException as error:
                if primary is not None:
                    primary.add_note("Support payload retention failed: " + type(error).__name__)
                elif cleanup_error is None:
                    cleanup_error = error
    if primary is not None:
        if cleanup_error is not None:
            primary.add_note("Support cleanup failed: " + type(cleanup_error).__name__)
        raise primary
    if cleanup_error is not None:
        raise cleanup_error
    require(
        result["support_status"] == "OBSERVED_NATIVE_SUPPORTED_DOMAIN",
        "AM_support_observation_incomplete",
    )
    return result


def _alertmanager_secret_controls(
    positive: dict[str, Any], negative: dict[str, Any], positive_path: str, negative_path: str
) -> dict[str, Any]:
    """Bind the same-scanner positive and clean control subjects and exact findings."""
    from scripts.ci.prometheus_source_image import require

    observed: list[list[tuple[str, Any, Any]]] = []
    for report, path, clean in ((positive, positive_path, False), (negative, negative_path, True)):
        require(
            report.get("ArtifactType") == "filesystem"
            and report.get("ArtifactName") == path
            and (type(report.get("Results")) is list or clean and "Results" not in report),
            "AM_secret_control_subject",
        )
        findings: list[tuple[str, Any, Any]] = []
        for row in report.get("Results", []):
            require(
                type(row) is dict and type(row.get("Target")) is str, "AM_secret_control_target"
            )
            value = row.get("Secrets", [])
            require(
                type(value) is list and all(type(item) is dict for item in value),
                "AM_secret_control_fields",
            )
            findings.extend(
                (row["Target"], item.get("RuleID"), item.get("Severity")) for item in value
            )
        observed.append(findings)
    require(
        observed == [[("credentials.txt", "github-pat", "CRITICAL")], []],
        "AM_secret_positive_or_negative_control",
    )
    return {
        "positive": {"rule": "github-pat", "severity": "CRITICAL", "count": 1},
        "clean_counterpart_count": 0,
        "scope": "same pinned default scanner/DB/config; bounded fs behavior, not universal binary coverage",
    }


def _alertmanager_support_inventory(
    report: dict[str, Any], *, probe_path: str | None = None
) -> dict[str, Any]:
    """Decode retained base/probe inventory without manufacturing scanner members."""
    from scripts.ci.prometheus_source_image import require

    require(
        type(report.get("Results")) is list
        or "Results" not in report
        and probe_path is not None
        and report.get("ArtifactType") == "filesystem"
        and report.get("ArtifactName") == probe_path,
        "AM_support_results",
    )
    packages, findings, targets = [], [], []
    for row in report.get("Results", []):
        require(
            type(row) is dict and type(row.get("Target")) is str and row["Target"],
            "AM_support_target",
        )
        targets.append(row["Target"])
        require(
            "Secrets" not in row or (type(row["Secrets"]) is list and not row["Secrets"]),
            "AM_support_secret_HOLD_private_report",
        )
        require(
            type(row.get("Packages", [])) is list and type(row.get("Vulnerabilities", [])) is list,
            "AM_support_inventory_fields",
        )
        for package in row.get("Packages", []):
            require(
                type(package) is dict
                and type(package.get("Name")) is str
                and package["Name"]
                and type(package.get("Version")) is str
                and package["Version"],
                "AM_support_package_identity",
            )
            packages.append(package)
        for finding in row.get("Vulnerabilities", []):
            require(
                type(finding) is dict
                and all(
                    type(finding.get(key)) is str and finding[key]
                    for key in ("VulnerabilityID", "PkgName", "InstalledVersion", "Severity")
                ),
                "AM_support_finding_identity",
            )
            findings.append(finding)
            require(
                finding["Severity"] in ("UNKNOWN", "LOW", "MEDIUM"),
                "AM_new_blocking_support_finding_HOLD",
            )
    require(len(targets) == len(set(targets)), "AM_support_duplicate_target")
    return {
        "targets": targets,
        "packages": packages,
        "findings": findings,
        "missing_Secrets_fields_are_not_execution_evidence": True,
    }


def _alertmanager_vulnerability_control(report: dict[str, Any], image_id: str) -> dict[str, Any]:
    """The already selected OLD vulnerable subject is a control, never an admitted payload."""
    from scripts.ci.prometheus_source_image import require

    require(
        report.get("ArtifactType") == "container_image"
        and type(report.get("Metadata")) is dict
        and report["Metadata"].get("ImageID") == image_id
        and type(report.get("Results")) is list,
        "AM_vulnerable_control_subject",
    )
    expected = {
        (target, cve, purl, "HIGH")
        for target in ("bin/alertmanager", "bin/amtool")
        for cve, purl in (
            ("CVE-2026-84445", "pkg:golang/google.golang.org/grpc@v1.83.1"),
            ("CVE-2026-78669", "pkg:golang/golang.org/x/net@v0.58.0"),
            ("CVE-2026-78669", "pkg:golang/stdlib@v1.26.8"),
            ("CVE-2026-78667", "pkg:golang/stdlib@v1.26.8"),
            ("CVE-2026-97031", "pkg:golang/stdlib@v1.26.8"),
        )
    }
    found, targets = [], []
    for row in report["Results"]:
        require(
            type(row) is dict
            and type(row.get("Target")) is str
            and type(row.get("Vulnerabilities", [])) is list
            and ("Secrets" not in row or type(row["Secrets"]) is list and not row["Secrets"]),
            "AM_vulnerable_control_result",
        )
        if row.get("Class") == "lang-pkgs" and row.get("Type") == "gobinary":
            targets.append(row["Target"])
            require(
                type(row.get("Packages")) is list and row["Packages"],
                "AM_vulnerable_control_packages",
            )
        for finding in row.get("Vulnerabilities", []):
            require(
                type(finding) is dict
                and finding.get("Severity") in ("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"),
                "AM_vulnerable_control_finding",
            )
            if finding["Severity"] in ("HIGH", "CRITICAL"):
                identifier = finding.get("PkgIdentifier")
                require(type(identifier) is dict, "AM_vulnerable_control_PURL")
                found.append(
                    (
                        row["Target"],
                        finding.get("VulnerabilityID"),
                        identifier.get("PURL"),
                        finding["Severity"],
                    )
                )
    require(
        sorted(targets) == ["bin/alertmanager", "bin/amtool"]
        and len(found) == len(expected)
        and set(found) == expected,
        "AM_known_vulnerable_control_inventory_changed_HOLD",
    )
    return {
        "scope": "KNOWN_VULNERABLE_CONTROL_ONLY_NEVER_CANDIDATE",
        "known_HIGH_occurrences": len(found),
        "all_severity_findings_retained": True,
        "image_config": image_id,
    }


def _alertmanager_limits() -> dict[str, int]:
    """The existing AM phases have explicit workflow-owned values, never defaults."""
    from scripts.ci.prometheus_source_image import require

    ceilings = {
        "PREP_SECONDS": 600,
        "PAIR_SECONDS": 1800,
        "SECURITY_SECONDS": 1800,
        "NATIVE_SECONDS": 2400,
        "PUBLICATION_SECONDS": 1800,
        "CLEANUP_SECONDS": 45,
        "NATIVE_CLEANUP_SECONDS": 120,
        "SCAN_TIMEOUT_SECONDS": 300,
        "SCAN_PROCESS_SECONDS": 330,
    }
    result = {}
    for name, ceiling in ceilings.items():
        raw = os.environ.get("ALERTMANAGER_" + name, "")
        require(
            re.fullmatch(r"[1-9][0-9]{0,3}", raw) is not None and int(raw) <= ceiling,
            "AM_explicit_phase_budget_" + name,
        )
        result[name] = int(raw)
    require(
        result["NATIVE_SECONDS"] > 1230
        and result["SCAN_TIMEOUT_SECONDS"]
        < result["SCAN_PROCESS_SECONDS"]
        <= result["SECURITY_SECONDS"],
        "AM_phase_budget_order",
    )
    return result


def _alertmanager_source_snapshot(
    api: GitHubRead,
    source: str,
    *,
    accepted: bool = False,
) -> dict[str, bytes]:
    """The existing AM finite Contents reader; never call the Prometheus-only source selector."""
    import base64
    import hashlib
    from scripts.ci.prometheus_source_image import require

    selected = _alertmanager_accepted_producer() if accepted else None
    if selected is not None:
        require(source == selected["source"], "AM_accepted_producer_exact_selectors")
    result = {}
    for path in (*_ALERT_Q_SOURCE_FILES, "tests/test_notify_premium_alias_checkpoint_failure.py"):
        record = api.json(
            "/repos/Katsiarynakavaleuskaya/PulsePlate/contents/" + path + "?ref=" + source
        )
        require(
            type(record) is dict
            and record.get("type") == "file"
            and record.get("path") == path
            and record.get("encoding") == "base64"
            and type(record.get("content")) is str
            and type(record.get("size")) is int
            and 0 < record["size"] <= 1024**2,
            "AM_producer_finite_source_blob",
        )
        raw = base64.b64decode(record["content"].replace("\n", ""), validate=True)
        require(
            len(raw) == record["size"]
            and hashlib.sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
            ).hexdigest()
            == record.get("sha"),
            "AM_producer_raw_Git_blob",
        )
        if selected is not None:
            require(
                sha256(raw).hexdigest() == selected["source_files"][path],
                "AM_accepted_producer_source_bytes",
            )
        result[path] = raw
    return result


def _alertmanager_candidate_payload(
    archive: Path,
    destination: Path,
    source_files: dict[str, bytes],
    inspected: dict[str, Any],
    support: Path,
) -> dict[str, Any]:
    """Validate the retained accepted A against independent source and full graph identity."""
    import zipfile
    from scripts.ci.prometheus_source_image import (
        _zip_members,
        fresh_directory,
        one_object,
        require,
        unpack_layout,
    )

    accepted = _alertmanager_accepted_producer()
    require(
        sha256(archive.read_bytes()).hexdigest() == accepted["zip_sha256"],
        "AM_accepted_producer_archive_bytes",
    )
    require(
        {path: sha256(raw).hexdigest() for path, raw in source_files.items()}
        == accepted["source_files"],
        "AM_accepted_producer_source_bytes",
    )
    files = _zip_members(archive)
    footer = one_object(files["artifact-payload-members.json"])
    require(
        set(footer) == {"files", "directories", "inventory_carrier_exception"}
        and type(footer["files"]) is list
        and type(footer["directories"]) is list
        and footer["inventory_carrier_exception"]
        == "Exactly artifact-payload-members.json is bound by external artifact bytes; its own hash is not recursively embedded.",
        "AM_candidate_retained_footer",
    )
    declared = {}
    for row in footer["files"]:
        require(
            type(row) is dict
            and set(row) == {"path", "size", "mode", "sha256"}
            and type(row["path"]) is str
            and row["path"].isascii()
            and "\\" not in row["path"]
            and all(part not in ("", ".", "..") for part in row["path"].split("/"))
            and row["path"] != "artifact-payload-members.json"
            and type(row["size"]) is int
            and row["size"] >= 0
            and type(row["mode"]) is int
            and 0 <= row["mode"] <= 0o7777
            and type(row["sha256"]) is str
            and _HEX_RE.fullmatch(row["sha256"]) is not None
            and row["path"] not in declared,
            "AM_candidate_payload_row",
        )
        declared[row["path"]] = row
    directories = {}
    for row in footer["directories"]:
        require(
            type(row) is dict
            and set(row) == {"path", "type", "mode"}
            and row["type"] == "directory"
            and type(row["path"]) is str
            and row["path"].isascii()
            and "\\" not in row["path"]
            and all(part not in ("", ".", "..") for part in row["path"].split("/"))
            and type(row["mode"]) is int
            and 0 <= row["mode"] <= 0o7777
            and row["path"] not in directories,
            "AM_candidate_retained_directory",
        )
        directories[row["path"]] = row["mode"]
    require(
        set(directories)
        == {
            str(parent)
            for name in declared
            for parent in PurePosixPath(name).parents
            if str(parent) != "."
        },
        "AM_candidate_complete_retained_directories",
    )
    require(
        set(files) == set(declared) | {"artifact-payload-members.json"},
        "AM_candidate_complete_retained_members",
    )
    for name, row in declared.items():
        require(
            type(row["size"]) is int
            and len(files[name]) == row["size"]
            and sha256(files[name]).hexdigest() == row["sha256"],
            "AM_candidate_retained_member_bytes",
        )
    with zipfile.ZipFile(archive) as retained:
        require(
            all(
                stat.S_IMODE(retained.getinfo(name).external_attr >> 16) == row["mode"]
                for name, row in declared.items()
            )
            and stat.S_IMODE(retained.getinfo("artifact-payload-members.json").external_attr >> 16)
            == 0o600,
            "AM_candidate_retained_native_modes",
        )
    result: dict[str, Any] = one_object(files["candidate-observation.json"])
    require(
        result.get("source") == accepted["source"]
        and result.get("graph") == accepted["graph"]
        and result.get("OCI_archive_sha256") == accepted["OCI_archive_sha256"],
        "AM_accepted_producer_subject_graph",
    )
    require(
        result.get("status") == "OBSERVED_NATIVE_SECURITY_ACCEPTED"
        and result.get("failure") is None
        and result.get("cleanup_failure") is None
        and type(result.get("compiler_starts")) is int
        and result["compiler_starts"] == 2
        and type(result.get("logical_build_starts")) is int
        and result["logical_build_starts"] == 1
        and type(result.get("automatic_retries")) is int
        and result["automatic_retries"] == 0
        and result.get("owned_absence_observed") is True
        and result.get("plan") == inspected["plan"]
        and result.get("UI_file_hashes") == inspected["plan"]["UI_file_hashes"],
        "AM_candidate_positive_predecessors_and_finite_recipe",
    )
    require(
        result.get("producer_source_files")
        == {path: sha256(raw).hexdigest() for path, raw in source_files.items()},
        "AM_candidate_actual_raw_producer",
    )
    for path, raw in source_files.items():
        require(files.get("producer-source/" + path) == raw, "AM_candidate_retained_producer_bytes")
    require(
        result.get("upstream", {}).get("qualification", {}).get("zip_sha256") == _ALERT_Q_ZIP_SHA256
        and result["upstream"].get("support", {}).get("zip_sha256") == _ALERT_S_ZIP_SHA256,
        "AM_candidate_Q_S_predecessors",
    )
    for phase, records, prefix in (
        ("pair", result.get("native_records"), "pair-evidence"),
        ("security", result.get("security", {}).get("native_records"), "security-evidence"),
        ("native", result.get("native", {}).get("native_records"), "native-evidence"),
    ):
        require(type(records) is list and bool(records), "AM_candidate_missing_" + phase)
        for row in cast(list[dict[str, Any]], records):
            require(
                type(row) is dict
                and type(row.get("exit")) is int
                and row["exit"] == 0
                and row.get("failure") is None,
                "AM_candidate_native_exit",
            )
            for channel in ("stdout", "stderr"):
                name = prefix + "/" + PurePosixPath(row[channel]).name
                require(
                    name in files and sha256(files[name]).hexdigest() == row[channel + "_sha256"],
                    "AM_candidate_native_report_binding",
                )
    require(
        b"native_AM_full_candidate_controls=pass" in files["native-evidence/full-AM-native.stdout"],
        "AM_candidate_native_terminal",
    )
    require(
        result["security"].get("scanner", {}).get("sha256") == _ALERT_TRIVY_SHA256
        and result["security"]["scanner"].get("DB") == _ALERT_DB,
        "AM_candidate_exact_scanner_DB",
    )
    actual_build_information = {}
    for binary in ("alertmanager", "amtool"):
        observed_build = _alertmanager_build_information(
            files["pair-evidence/" + binary + "-buildinfo-attach.stdout"], binary
        )
        require(
            observed_build == result.get("build_information", {}).get(binary)
            and result.get("output_hashes", {}).get(binary)
            == result["graph"]["files"].get("usr/bin/" + binary),
            "AM_candidate_both_buildinfo_and_binary_hashes",
        )
        actual_build_information[binary] = observed_build
    full = one_object(files["security-evidence/candidate-full-supported.private.json"])
    require(
        _alertmanager_candidate_inventory(
            full,
            result["graph"]["config"]["digest"],
            one_object((support / "evidence/base-full-supported-scan.private.json").read_bytes()),
            actual_build_information,
        )
        == result["security"].get("candidate"),
        "AM_candidate_full_report_not_summary_only",
    )
    scans = {
        PurePosixPath(row["stdout"]).name.removesuffix(".stdout"): row
        for row in result["security"]["native_records"]
        if row["argv"][0].endswith("/trivy")
    }
    require(
        set(scans)
        == {
            "candidate-secret-positive",
            "candidate-secret-negative",
            "candidate-known-vulnerable-control",
            "candidate-full-supported",
        },
        "AM_candidate_complete_native_scan_commands",
    )
    for row in scans.values():
        argv = row["argv"]
        require(
            "--scanners" in argv
            and argv[argv.index("--scanners") + 1] == "vuln,secret"
            and "--offline-scan" in argv
            and "--list-all-pkgs" in argv
            and "--skip-db-update" in argv
            and "--ignore-unfixed=false" in argv
            and argv[argv.index("--severity") + 1] == "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL",
            "AM_candidate_unsuppressed_native_scan_recipe",
        )
    controls = _alertmanager_secret_controls(
        one_object(files["security-evidence/candidate-secret-positive.private.json"]),
        one_object(files["security-evidence/candidate-secret-negative.private.json"]),
        scans["candidate-secret-positive"]["argv"][-1],
        scans["candidate-secret-negative"]["argv"][-1],
    )
    require(controls == result["security"].get("secrets"), "AM_candidate_actual_secret_controls")
    old = _alertmanager_vulnerability_control(
        one_object(files["security-evidence/candidate-known-vulnerable-control.private.json"]),
        "sha256:53622b714941158bc20cc92a7571aef515556218eef914b7b8ec5b2a0cb6f607",
    )
    require(old == result["security"].get("old_control"), "AM_candidate_actual_vulnerable_control")
    fresh_directory(destination)
    for name, raw in files.items():
        target = destination / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes(raw)
        target.chmod(0o600)
    layout = destination / "layout"
    unpack_layout(files["candidate.oci.tar"], layout)
    require(
        sha256(files["candidate.oci.tar"]).hexdigest() == result.get("OCI_archive_sha256"),
        "AM_candidate_original_OCI_bytes",
    )
    require(
        _alertmanager_candidate_graph(layout, support, result["graph"]["files"]) == result["graph"],
        "AM_candidate_actual_graph_payload",
    )
    return result


def _alertmanager_support_payload(archive: Path, destination: Path) -> dict[str, Any]:
    """Read the exact observed S artifact, with the incumbent native payload inventory."""
    import shutil
    import zipfile
    from scripts.ci.prometheus_source_image import file_hash, fresh_directory, one_object, require

    require(file_hash(archive) == _ALERT_S_ZIP_SHA256, "AM_exact_support_archive")
    fresh_directory(destination)
    with zipfile.ZipFile(archive) as retained:
        entries = retained.infolist()
        require(len(entries) == 134, "AM_support_complete_transport")
        names = [info.filename for info in entries]
        require(len(names) == len(set(names)), "AM_support_transport_duplicate")
        total = 0
        for info in entries:
            name = info.filename[:-1] if info.is_dir() else info.filename
            require(
                bool(name)
                and not info.flag_bits & 1
                and "\\" not in name
                and all(part not in ("", ".", "..") for part in name.split("/"))
                and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG, stat.S_IFDIR),
                "AM_support_transport_path_type",
            )
            total += info.file_size
            require(0 <= info.file_size <= 2 * 1024**3 and total <= 2 * 1024**3, "AM_support_size")
        footer = one_object(retained.read("native-support/artifact-payload-members.json"))
        require(
            set(footer) == {"files", "directories", "inventory_carrier_exception"}
            and type(footer["files"]) is list
            and len(footer["files"]) == 91
            and type(footer["directories"]) is list
            and len(footer["directories"]) == 14,
            "AM_support_native_footer",
        )
        require(
            footer["inventory_carrier_exception"]
            == "Exactly artifact-payload-members.json is bound by external artifact bytes; its own hash is not recursively embedded.",
            "AM_support_footer_exception",
        )
        directories = {}
        for row in footer["directories"]:
            require(
                type(row) is dict
                and set(row) == {"path", "type", "mode"}
                and row["type"] == "directory"
                and type(row["path"]) is str
                and "\\" not in row["path"]
                and all(part not in ("", ".", "..") for part in row["path"].split("/"))
                and type(row["mode"]) is int
                and row["mode"] == 0o700
                and row["path"] not in directories,
                "AM_support_declared_directory",
            )
            directories[row["path"]] = row["mode"]
            (destination / row["path"]).mkdir(mode=row["mode"], parents=True, exist_ok=True)
        expected = {"native-support/" + row["path"] for row in footer["files"]}
        actual = {
            info.filename
            for info in entries
            if not info.is_dir() and info.filename.startswith("native-support/")
        }
        require(
            actual == expected | {"native-support/artifact-payload-members.json"},
            "AM_support_all_native_files",
        )
        require(len(expected) == len(footer["files"]), "AM_support_duplicate_declared_member")
        require(
            {
                str(parent)
                for row in footer["files"]
                for parent in PurePosixPath(row["path"]).parents
                if str(parent) != "."
            }
            <= set(directories),
            "AM_support_file_parent_inventory",
        )
        for row in footer["files"]:
            require(
                type(row) is dict
                and set(row) == {"path", "size", "mode", "sha256"}
                and type(row["path"]) is str
                and all(part not in ("", ".", "..") for part in row["path"].split("/"))
                and "\\" not in row["path"]
                and type(row["size"]) is int
                and type(row["mode"]) is int
                and 0 <= row["mode"] <= 0o777
                and type(row["sha256"]) is str
                and _HEX_RE.fullmatch(row["sha256"]) is not None,
                "AM_support_declared_member",
            )
            path = destination / row["path"]
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with (
                retained.open("native-support/" + row["path"]) as source,
                path.open("xb") as output,
            ):
                shutil.copyfileobj(source, output, 1024**2)
            path.chmod(row["mode"])
            require(
                path.stat().st_size == row["size"] and file_hash(path) == row["sha256"],
                "AM_support_member_bytes",
            )
        require(
            stat.S_IMODE(
                retained.getinfo("native-support/artifact-payload-members.json").external_attr >> 16
            )
            == 0o600,
            "AM_support_footer_native_mode",
        )
        inspected = one_object(retained.read("input-inspection.json"))
    report: dict[str, Any] = one_object((destination / "support-observation.json").read_bytes())
    require(
        inspected.get("consumer_source") == _ALERT_S_SOURCE
        and inspected.get("upstream", {}).get("zip_sha256") == _ALERT_Q_ZIP_SHA256
        and inspected.get("package_read", {}).get("metadata_read") is True
        and inspected["inspection"].get("support") == report
        and report.get("support_status") == "OBSERVED_NATIVE_SUPPORTED_DOMAIN"
        and report.get("compiler_starts") == report.get("logical_build_starts") == 0
        and report.get("owned_container_absence_observed") is True
        and report.get("base", {}).get("config") == _ALERT_BASE_CONFIG
        and report["base"]["actual_local_OCI_descriptor"]["digest"] == _ALERT_BASE_MANIFEST
        and report.get("probe", {}).get("sha256") == _ALERT_PROBE_SHA256
        and report.get("scanner", {}).get("sha256") == _ALERT_TRIVY_SHA256
        and report["scanner"]["DB"] == _ALERT_DB
        and file_hash(destination / "probe-bin-bracket") == _ALERT_PROBE_SHA256
        and file_hash(destination / "trivy") == _ALERT_TRIVY_SHA256,
        "AM_support_native_input_binding",
    )
    for name, digest in _ALERT_DB.items():
        require(file_hash(destination / "trivy-cache" / name) == digest, "AM_support_frozen_DB")
    records = report.get("native_records")
    require(type(records) is list and len(records) == 20, "AM_support_native_commands")
    seen = set()
    for row in cast(list[dict[str, Any]], records):
        require(
            type(row) is dict
            and type(row.get("exit")) is int
            and row["exit"] == 0
            and row.get("failure") is None
            and type(row.get("environment")) is dict
            and set(row["environment"]) == {"PATH", "HOME", "DOCKER_CONFIG", "LANG"},
            "AM_support_native_exit_environment",
        )
        for channel in ("stdout", "stderr"):
            path = PurePosixPath(row[channel])
            require(
                path.parent.name == "evidence"
                and path.parent.parent.name == "native-support"
                and file_hash(destination / "evidence" / path.name) == row[channel + "_sha256"],
                "AM_support_native_output_binding",
            )
        require(row["stdout"] not in seen, "AM_support_native_duplicate")
        seen.add(row["stdout"])
    require(file_hash(archive) == _ALERT_S_ZIP_SHA256, "AM_support_archive_drift")
    return report


def _alertmanager_materialize(archive: Path, destination: Path, deadline: float) -> Path:
    """Materialize only the already-qualified finite source/cache epoch, without acquisition."""
    import shutil
    import zipfile
    from scripts.ci.prometheus_source_image import GO, extract, fresh_directory, one_object, require

    fresh_directory(destination, 0o755)
    with zipfile.ZipFile(archive) as retained:
        metadata = one_object(retained.read("module-qualification.json"))
        expected = {row["path"]: row for row in metadata["frozen_input_payload"]["members"]}
        with (
            retained.open("frozen-inputs.tar") as stream,
            tarfile.open(fileobj=stream, mode="r|") as inputs,
        ):
            seen = set()
            for member in inputs:
                row = expected.get(member.name)
                require(
                    row is not None and member.name not in seen, "AM_materialized_declared_input"
                )
                row = cast(dict[str, Any], row)
                seen.add(member.name)
                require(
                    all(part not in ("", ".", "..") for part in member.name.split("/"))
                    and "\\" not in member.name
                    and (member.isfile() or member.isdir())
                    and member.mode == row["mode"]
                    and row["type"] == ("file" if member.isfile() else "directory")
                    and member.size == row["bytes"],
                    "AM_materialized_input_type_mode",
                )
                target = destination / member.name
                if member.isdir():
                    target.mkdir(mode=0o755, parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                    source = inputs.extractfile(member)
                    require(source is not None, "AM_materialized_input_missing")
                    with target.open("xb") as output:
                        shutil.copyfileobj(cast(BinaryIO, source), output, 1024**2)
                    from scripts.ci.prometheus_source_image import file_hash

                    require(
                        target.stat().st_size == row["bytes"]
                        and file_hash(target) == row["sha256"],
                        "AM_materialized_input_bytes",
                    )
                    target.chmod(row["mode"])
            require(seen == set(expected), "AM_materialized_complete_input")
    toolchain = destination / "alertmanager-go"
    extract(GO, destination / "go-toolchain.tar.gz", toolchain, deadline)
    _alertmanager_readonly_go(toolchain, deadline)
    for directory in sorted((p for p in destination.rglob("*") if p.is_dir()), reverse=True):
        directory.chmod(0o555)
    return toolchain


def _alertmanager_build_information(raw: bytes, binary: str) -> dict[str, Any]:
    """Interpret native Go build-info for the required pair, including embedded stdlib."""
    from scripts.ci.prometheus_source_image import require

    lines = raw.decode("utf-8").splitlines()
    require(
        bool(lines) and lines[0] == "/out/" + binary + ": go1.27.2", "AM_actual_Go_build_version"
    )
    dependencies, settings = {}, {}
    main: dict[str, str] = {}
    path = ""
    for line in lines[1:]:
        fields = line.strip().split("\t")
        if fields[0] == "dep":
            require(
                len(fields) >= 3
                and bool(fields[1])
                and bool(fields[2])
                and fields[1] not in dependencies,
                "AM_build_info_dependency",
            )
            dependencies[fields[1]] = fields[2]
        elif fields[0] == "path":
            require(len(fields) == 2 and not path, "AM_build_info_command_path")
            path = fields[1]
        elif fields[0] == "mod":
            require(
                len(fields) >= 3 and not main and bool(fields[1]) and bool(fields[2]),
                "AM_build_info_main",
            )
            main = {"Path": fields[1], "Version": fields[2]}
        elif fields[0] == "build":
            require(len(fields) == 2 and "=" in fields[1], "AM_build_info_setting")
            key, value = fields[1].split("=", 1)
            require(key not in settings, "AM_build_info_duplicate_setting")
            settings[key] = value
        require(fields[0] != "=>", "AM_build_info_replaced_module")
    require(
        path == "github.com/prometheus/alertmanager/cmd/" + binary
        and main.get("Path") == "github.com/prometheus/alertmanager"
        and main.get("Version") in ("(devel)", "0.34.1", "v0.34.1")
        and dependencies.get("golang.org/x/net") == "v0.60.0"
        and dependencies.get("google.golang.org/grpc") == "v1.83.2"
        and all(
            settings.get(k) == v
            for k, v in {
                "CGO_ENABLED": "0",
                "GOOS": "linux",
                "GOARCH": "amd64",
                "-tags": "netgo",
                "-trimpath": "true",
            }.items()
        )
        and "-ldflags" not in settings,
        "AM_actual_pair_build_settings",
    )
    return {
        "Go": "go1.27.2",
        "dependencies": dependencies,
        "main": main,
        "path": path,
        "settings": settings,
        "raw_sha256": sha256(raw).hexdigest(),
    }


def _alertmanager_candidate_inventory(
    report: dict[str, Any],
    image_id: str,
    base_report: dict[str, Any],
    build_information: dict[str, Any],
) -> dict[str, Any]:
    """Extend the existing supported inventory consumer for the exact final binary pair."""
    from scripts.ci.prometheus_source_image import require

    require(
        type(report.get("SchemaVersion")) is int
        and report["SchemaVersion"] == 2
        and report.get("ArtifactType") == "container_image"
        and type(report.get("Metadata")) is dict
        and report["Metadata"].get("ImageID") == image_id,
        "AM_candidate_scan_subject",
    )
    inventory = _alertmanager_support_inventory(report)
    require(
        set(build_information) == {"alertmanager", "amtool"},
        "AM_candidate_both_actual_buildinfo_required",
    )
    require(
        base_report.get("ArtifactType") == "container_image"
        and type(base_report.get("Metadata")) is dict
        and base_report["Metadata"].get("ImageID") == _ALERT_BASE_CONFIG,
        "AM_candidate_authenticated_base_scan_subject",
    )
    _alertmanager_support_inventory(base_report)
    os_inventories = []
    for observed in (base_report, report):
        operating_system = observed["Metadata"].get("OS")
        require(
            type(operating_system) is dict
            and all(
                type(operating_system.get(k)) is str and operating_system[k]
                for k in ("Family", "Name")
            ),
            "AM_candidate_comparable_OS_identity",
        )
        os_packages = []
        for row in observed["Results"]:
            if row.get("Class") != "os-pkgs":
                continue
            require(row.get("Type") == operating_system["Family"], "AM_candidate_OS_classifier")
            for package in row.get("Packages", []):
                fields = ("ID", "Name", "Version", "Arch", "SrcName", "SrcVersion")
                require(
                    all(type(package.get(k)) is str and package[k] for k in fields)
                    and type(package.get("Identifier")) is dict
                    and type(package["Identifier"].get("PURL")) is str
                    and package["Identifier"]["PURL"].startswith("pkg:"),
                    "AM_candidate_comparable_OS_package",
                )
                os_packages.append(
                    (
                        row["Class"],
                        row["Type"],
                        *(package[k] for k in fields),
                        package["Identifier"]["PURL"],
                    )
                )
        require(
            bool(os_packages) and len(os_packages) == len(set(os_packages)),
            "AM_candidate_complete_unique_OS_inventory",
        )
        os_inventories.append(
            (operating_system["Family"], operating_system["Name"], sorted(os_packages))
        )
    require(
        os_inventories[0] == os_inventories[1],
        "AM_candidate_all_and_only_authenticated_base_packages",
    )
    targets = []
    for row in report["Results"]:
        for finding in row.get("Vulnerabilities", []):
            require(
                finding["VulnerabilityID"]
                not in {"CVE-2026-84445", "CVE-2026-78669", "CVE-2026-78667", "CVE-2026-97031"},
                "AM_accepted_CVE_still_present",
            )
        if row.get("Class") == "lang-pkgs" and row.get("Type") == "gobinary":
            require(
                row["Target"]
                in ("usr/bin/alertmanager", "usr/bin/amtool", "bin/alertmanager", "bin/amtool"),
                "AM_unexpected_Go_binary",
            )
            targets.append(row["Target"].rsplit("/", 1)[1])
            binary = targets[-1]
            information = build_information[binary]
            require(
                information.get("Go") == "go1.27.2"
                and type(information.get("dependencies")) is dict
                and type(information.get("main")) is dict
                and information["main"].get("Path") == "github.com/prometheus/alertmanager"
                and information["main"].get("Version") in ("(devel)", "0.34.1", "v0.34.1"),
                "AM_candidate_comparable_native_Go_identity",
            )
            expected_modules = dict(information["dependencies"])
            require(
                all(
                    type(name) is str and bool(name) and type(version) is str and bool(version)
                    for name, version in expected_modules.items()
                )
                and "stdlib" not in expected_modules
                and information["main"]["Path"] not in expected_modules,
                "AM_candidate_comparable_native_dependencies",
            )
            expected_modules["stdlib"] = "v" + information["Go"].removeprefix("go")
            expected_modules[information["main"]["Path"]] = "0.34.1"
            actual_modules = {}
            for package in row.get("Packages", []):
                name, version = package.get("Name"), package.get("Version")
                require(
                    type(name) is str
                    and bool(name)
                    and type(version) is str
                    and bool(version)
                    and name not in actual_modules,
                    "AM_candidate_complete_unique_Go_package",
                )
                if name == information["main"]["Path"]:
                    version = version.removeprefix("v")
                actual_modules[name] = version
            require(
                actual_modules == expected_modules,
                "AM_candidate_all_and_only_actual_Go_dependencies",
            )
    require(sorted(targets) == ["alertmanager", "amtool"], "AM_candidate_two_Go_targets")
    return inventory


def _alertmanager_candidate_graph(
    layout: Path, support: Path, expected_files: dict[str, str]
) -> dict[str, Any]:
    """Observe the finite COPY-only AM graph using the incumbent OCI primitives."""
    from scripts.ci.prometheus_source_image import (
        _blob,
        _gunzip,
        _layout_inventory,
        _layout_root,
        one_object,
        require,
    )

    descriptor = _layout_root(layout)
    manifest = one_object(_blob(layout, descriptor))
    require(
        manifest.get("schemaVersion") == 2
        and manifest.get("mediaType") == "application/vnd.oci.image.manifest.v1+json"
        and type(manifest.get("layers")) is list,
        "AM_candidate_single_image_manifest",
    )
    config_raw = _blob(layout, manifest["config"])
    configuration = one_object(config_raw)
    base_layout = support / "base-layout"
    base = one_object(_blob(base_layout, _layout_root(base_layout)))
    base_config = one_object(_blob(base_layout, base["config"]))
    runtime = configuration.get("config", {})
    require(
        configuration.get("os") == "linux"
        and configuration.get("architecture") == "amd64"
        and runtime.get("User") == "65534:65534"
        and runtime.get("Entrypoint") == ["/bin/alertmanager"]
        and runtime.get("Cmd")
        == [
            "--config.file=/etc/alertmanager/alertmanager.yml",
            "--storage.path=/alertmanager",
            "--cluster.listen-address=",
        ]
        and runtime.get("WorkingDir") == "/alertmanager"
        and runtime.get("Volumes") == {"/alertmanager": {}}
        and runtime.get("Env") == base_config.get("config", {}).get("Env")
        and runtime.get("ExposedPorts") == {"9093/tcp": {}}
        and not runtime.get("Healthcheck")
        and not runtime.get("OnBuild"),
        "AM_candidate_platform_runtime_configuration",
    )
    require(
        type(configuration.get("rootfs")) is dict
        and configuration["rootfs"].get("type") == "layers"
        and type(configuration["rootfs"].get("diff_ids")) is list
        and len(configuration["rootfs"]["diff_ids"]) == len(manifest["layers"])
        and configuration["rootfs"]["diff_ids"][:13] == base_config["rootfs"]["diff_ids"]
        and 13 < len(manifest["layers"]) <= 24,
        "AM_candidate_base_and_COPY_layers",
    )
    found, payload, ca_hash = {}, [], None
    parents = {"usr", "usr/bin", "etc", "etc/alertmanager", "alertmanager"}
    storage = False
    for index, layer in enumerate(manifest["layers"]):
        raw = _blob(layout, layer)
        require(
            layer.get("mediaType")
            in (
                "application/vnd.oci.image.layer.v1.tar",
                "application/vnd.oci.image.layer.v1.tar+gzip",
            ),
            "AM_candidate_layer_media",
        )
        expanded = _gunzip(raw, 512 * 1024**2) if layer["mediaType"].endswith("+gzip") else raw
        require(
            "sha256:" + sha256(expanded).hexdigest() == configuration["rootfs"]["diff_ids"][index],
            "AM_candidate_layer_diffID",
        )
        if index < 13:
            require(
                "sha256:" + sha256(expanded).hexdigest()
                == base_config["rootfs"]["diff_ids"][index],
                "AM_candidate_exact_base_layer",
            )
        with tarfile.open(fileobj=io.BytesIO(expanded), mode="r:") as archive:
            seen = set()
            for member in archive:
                require(member.name not in seen, "AM_candidate_layer_duplicate")
                seen.add(member.name)
                if index < 13:
                    if member.name == "etc/ssl/certs/ca-certificates.crt" and member.isfile():
                        stream = archive.extractfile(member)
                        require(stream is not None, "AM_default_CA_bytes")
                        ca_hash = sha256(cast(BinaryIO, stream).read(member.size + 1)).hexdigest()
                    continue
                require(
                    member.name in expected_files
                    or member.name in parents
                    and member.isdir()
                    and member.size == 0,
                    "AM_COPY_only_payload_inventory",
                )
                require(
                    all(p not in ("", ".", "..") for p in member.name.split("/"))
                    and not member.linkname
                    and (member.isfile() or member.isdir())
                    and member.mode in (0o444, 0o555, 0o600, 0o644, 0o700, 0o755),
                    "AM_COPY_payload_type_mode",
                )
                row = {
                    "path": member.name,
                    "mode": member.mode,
                    "uid": member.uid,
                    "gid": member.gid,
                    "size": member.size,
                    "type": "directory" if member.isdir() else "file",
                }
                if member.isdir() and member.name == "alertmanager":
                    require(
                        member.uid == member.gid == 65534 and member.mode == 0o700,
                        "AM_storage_directory_owner_mode",
                    )
                    storage = True
                if member.isfile():
                    require(
                        member.name not in found and member.uid == member.gid == 0,
                        "AM_COPY_file_identity",
                    )
                    require(
                        member.mode == (0o555 if member.name.startswith("usr/bin/") else 0o444),
                        "AM_COPY_file_executable_mode",
                    )
                    stream = archive.extractfile(member)
                    require(
                        stream is not None and member.size <= 256 * 1024**2, "AM_COPY_file_bound"
                    )
                    value = cast(BinaryIO, stream).read(member.size + 1)
                    digest = sha256(value).hexdigest()
                    require(
                        len(value) == member.size and digest == expected_files[member.name],
                        "AM_COPY_file_bytes",
                    )
                    found[member.name] = digest
                    row["sha256"] = digest
                payload.append(row)
    require(
        found == expected_files and storage and ca_hash is not None, "AM_complete_final_COPY_and_CA"
    )
    descriptors = [descriptor, manifest["config"], *manifest["layers"]]
    _layout_inventory(layout, {value["digest"] for value in descriptors})
    return {
        "manifest": descriptor,
        "config": manifest["config"],
        "layers": manifest["layers"],
        "diff_ids": configuration["rootfs"]["diff_ids"],
        "configuration": configuration,
        "payload": payload,
        "files": found,
        "default_CA_sha256": ca_hash,
    }


def _alertmanager_pair(
    inputs: Path,
    support: Path,
    plan: dict[str, Any],
    work: Path,
    result: dict[str, Any],
    limits: dict[str, int],
    prep_deadline: float,
    *,
    retained: Path | None = None,
) -> dict[str, Any]:
    """One direct serial pair plus one COPY-only assembly; no resolver or retry."""
    from datetime import datetime
    import shutil
    import uuid
    from scripts.ci.prometheus_source_image import (
        Native,
        file_hash,
        fresh_directory,
        one_object,
        pack_layout,
        real_directory,
        require,
        tree_inventory,
    )

    docker = shutil.which("docker")
    require(docker is not None and Path(docker).is_absolute(), "AM_pair_Docker")
    require(Path(sys.executable).is_absolute(), "AM_pair_interpreter")
    docker = cast(str, docker)
    fresh_directory(work)
    evidence = work / "evidence"
    fresh_directory(evidence)
    config = work / "docker-config"
    fresh_directory(config)
    (config / "cli-plugins").mkdir(mode=0o700)
    plugin = config / "cli-plugins/docker-buildx"
    shutil.copyfile(support / "empty-docker-config/cli-plugins/docker-buildx", plugin)
    plugin.chmod(0o555)
    require(file_hash(plugin) == _ALERT_BUILDX_SHA256, "AM_pair_verified_Buildx")
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "DOCKER_CONFIG": str(config),
        "LANG": "C.UTF-8",
    }
    prefix = [docker, "--config", str(config)]
    prep = Native(evidence, prep_deadline, limits["CLEANUP_SECONDS"])
    snapshots = {
        name: tree_inventory(inputs / name) for name in ("source", "modules", "alertmanager-go")
    }
    output, scratch = work / "output", work / "scratch"
    for path in (output, scratch):
        fresh_directory(path, 0o777)
        path.chmod(0o777)
    for name in ("tmp", "home", "cache", "gopath"):
        fresh_directory(scratch / name, 0o777)
        (scratch / name).chmod(0o777)
    native = prep
    token = uuid.uuid4().hex
    owned: dict[str, str] = {}
    attempted: set[str] = set()
    builder = "pulseplate-am-" + token
    builder_attempted, builder_id = False, ""
    primary: BaseException | None = None
    cleanup_error: BaseException | None = None
    result.update(
        {
            "logical_build_starts": 0,
            "compiler_starts": 0,
            "compiler_attempts": 0,
            "automatic_retries": 0,
        }
    )

    def go(argv: list[str], label: str) -> bytes:
        name = "pulseplate-am-pair-" + token + "-" + label
        attempted.add(name)
        create = [
            *prefix,
            "create",
            "--name",
            name,
            "--label",
            "pulseplate.alertmanager-module=" + token,
            "--pull=never",
            "--network=none",
            "--read-only",
            "--user=65534:65534",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--workdir=/source",
        ]
        for source, target, readonly in (
            (inputs / "source", "/source", True),
            (inputs / "modules", "/modules", True),
            (inputs / "alertmanager-go", "/toolchain", True),
            (output, "/out", False),
            (scratch, "/work", False),
        ):
            create += [
                "--mount",
                "type=bind,source="
                + str(source)
                + ",target="
                + target
                + (",readonly" if readonly else ""),
            ]
        for key, value in plan["compiler_environment"].items():
            create += ["--env", key + "=" + value]
        create += ["--entrypoint=/toolchain/bin/go", _ALERT_BASE_CONFIG, *argv]
        identifier = native.run(create, label + "-create", env, cwd=work).decode("ascii").strip()
        require(re.fullmatch(r"[0-9a-f]{64}", identifier) is not None, "AM_pair_owned_ID")
        owned[identifier] = name
        if argv[0] == "build":
            result["compiler_starts"] += 1
            (work / "invocation-start.json").write_text(json.dumps(result, indent=2) + "\n")
        raw: bytes = native.run(
            [*prefix, "start", "--attach", identifier],
            label + "-attach",
            env,
            cwd=work,
            watched_output=work,
        )
        waited = native.run([*prefix, "wait", identifier], label + "-wait", env, cwd=work)
        observed = one_object(
            native.run(
                [*prefix, "inspect", "--format", "{{json .}}", identifier],
                label + "-terminal",
                env,
                cwd=work,
            )
        )
        _alertmanager_command_exit(observed, identifier, name, token, waited)
        return raw

    try:
        prep.run(
            [*prefix, "image", "load", "--input", str(support / "base-image.tar")],
            "pair-base-load",
            env,
            cwd=work,
        )
        base = one_object(
            prep.run(
                [*prefix, "image", "inspect", "--format", "{{json .}}", _ALERT_BASE_CONFIG],
                "pair-base-inspect",
                env,
                cwd=work,
            )
        )
        require(
            base.get("Id") == _ALERT_BASE_CONFIG
            and base.get("Os") == "linux"
            and base.get("Architecture") == "amd64",
            "AM_pair_exact_base",
        )
        prep.run(
            [*prefix, "pull", "--platform=linux/amd64", _ALERT_BUILDKIT],
            "pair-preload-BuildKit",
            env,
            cwd=work,
        )
        builder_image = one_object(
            prep.run(
                [*prefix, "image", "inspect", "--format", "{{json .}}", _ALERT_BUILDKIT],
                "pair-BuildKit-image",
                env,
                cwd=work,
            )
        )
        buildkit_ref, buildkit_digest = _ALERT_BUILDKIT.rsplit("@", 1)
        buildkit_repo_digest = buildkit_ref.rsplit(":", 1)[0] + "@" + buildkit_digest
        repo_digests = builder_image.get("RepoDigests")
        require(
            builder_image.get("Os") == "linux"
            and builder_image.get("Architecture") == "amd64"
            and type(repo_digests) is list
            and all(type(digest) is str and digest != "" for digest in repo_digests)
            and repo_digests.count(buildkit_repo_digest) == 1,
            "AM_pinned_BuildKit_image",
        )
        builder_attempted = True
        prep.run(
            [
                *prefix,
                "buildx",
                "create",
                "--driver=docker-container",
                "--driver-opt=image=" + _ALERT_BUILDKIT,
                "--driver-opt=network=none",
                "--driver-opt=env.PULSEPLATE_AM_OWNER=" + token,
                "--name",
                builder,
                "--use",
            ],
            "pair-builder-create",
            env,
            cwd=work,
        )
        prep.run(
            [*prefix, "buildx", "inspect", "--bootstrap", builder],
            "pair-builder-bootstrap",
            env,
            cwd=work,
        )
        builder_observed = one_object(
            prep.run(
                [*prefix, "inspect", "--format", "{{json .}}", "buildx_buildkit_" + builder + "0"],
                "pair-builder-bound",
                env,
                cwd=work,
            )
        )
        require(
            builder_observed.get("Name") == "/buildx_buildkit_" + builder + "0"
            and builder_observed.get("Image") == builder_image["Id"]
            and builder_observed.get("HostConfig", {}).get("NetworkMode") == "none"
            and "PULSEPLATE_AM_OWNER=" + token in builder_observed.get("Config", {}).get("Env", []),
            "AM_offline_owned_builder",
        )
        builder_id = builder_observed["Id"]
        require(re.fullmatch(r"[0-9a-f]{64}", builder_id) is not None, "AM_builder_full_ID")
        native = Native(
            evidence, time.monotonic() + limits["PAIR_SECONDS"], limits["CLEANUP_SECONDS"]
        )
        result["logical_build_starts"] = 1
        result["build_information"] = {}
        for command, binary in zip(plan["compiler_argv"], ("alertmanager", "amtool"), strict=True):
            result["compiler_attempts"] += 1
            (work / "invocation-start.json").write_text(json.dumps(result, indent=2) + "\n")
            go(command[1:], binary + "-compile")
            produced = output / binary
            require(
                produced.is_file()
                and not produced.is_symlink()
                and produced.stat().st_nlink == 1
                and 0 < produced.stat().st_size <= 256 * 1024**2,
                "AM_actual_produced_binary_before_assembly",
            )
            result.setdefault("output_hashes", {})[binary] = file_hash(produced)
            if retained is not None:
                destination = retained / "pair-outputs" / binary
                destination.parent.mkdir(mode=0o700, exist_ok=True)
                require(
                    not destination.exists() and not destination.is_symlink(),
                    "AM_fresh_retained_pair_output",
                )
                shutil.copyfile(produced, destination)
                destination.chmod(0o600)
                require(
                    file_hash(produced)
                    == result["output_hashes"][binary]
                    == file_hash(destination),
                    "AM_pair_output_retained_before_later_phase",
                )
            result["build_information"][binary] = _alertmanager_build_information(
                go(["version", "-m", "/out/" + binary], binary + "-buildinfo"), binary
            )
        require(
            all(tree_inventory(inputs / name) == before for name, before in snapshots.items()),
            "AM_pair_readonly_inputs_drift",
        )
        context = work / "context"
        fresh_directory(context)
        for binary in ("alertmanager", "amtool"):
            path = output / binary
            require(
                path.is_file()
                and not path.is_symlink()
                and path.stat().st_nlink == 1
                and 0 < path.stat().st_size <= 256 * 1024**2
                and file_hash(path) == result["output_hashes"][binary],
                "AM_required_pair_output",
            )
            shutil.copyfile(path, context / binary)
            (context / binary).chmod(0o555)
        for name, source in {
            "Containerfile": REPO_ROOT / "deploy/alertmanager/Containerfile",
            "alertmanager.yml": REPO_ROOT / "deploy/alertmanager/alertmanager.yml",
            "LICENSE": inputs / "source/LICENSE",
            "NOTICE": inputs / "source/NOTICE",
            "probe-bin-bracket": support / "probe-bin-bracket",
        }.items():
            shutil.copyfile(source, context / name)
            (context / name).chmod(0o555 if name == "probe-bin-bracket" else 0o444)
        (context / "storage-dir").mkdir(mode=0o700)
        context_inventory = tree_inventory(context)
        result["context"] = context_inventory
        require(
            file_hash(context / "Containerfile") == _ALERT_ASSEMBLY_RECIPE_SHA256
            and file_hash(context / "alertmanager.yml")
            == _ALERT_Q_SOURCE_FILES["deploy/alertmanager/alertmanager.yml"],
            "AM_context_recipe_drift",
        )
        require(
            file_hash(context / "probe-bin-bracket") == _ALERT_PROBE_SHA256,
            "AM_context_probe_drift",
        )
        require(file_hash(plugin) == _ALERT_BUILDX_SHA256, "AM_Buildx_before_assembly_drift")
        current_builder = one_object(
            native.run(
                [*prefix, "inspect", "--format", "{{json .}}", builder_id],
                "builder-before-assembly",
                env,
                cwd=work,
            )
        )
        require(
            current_builder.get("Id") == builder_id
            and current_builder.get("Image") == builder_image["Id"]
            and current_builder.get("HostConfig", {}).get("NetworkMode") == "none"
            and current_builder.get("State", {}).get("Running") is True
            and current_builder["State"].get("Restarting") is False,
            "AM_running_offline_builder_before_assembly",
        )
        layout = work / "candidate-layout"
        argv = [
            sys.executable,
            *_ALERT_ASSEMBLY_LAUNCH,
            *prefix,
            "buildx",
            "build",
            "--builder",
            builder,
            "--platform=linux/amd64",
            "--provenance=false",
            "--sbom=false",
            "--annotation",
            "manifest-descriptor:org.opencontainers.image.ref.name=candidate",
            "--network=none",
            "--pull=false",
            "--build-context",
            "gcr.io/distroless/static-debian13@sha256:2293b36c7c9082bf4115aab724b4d2cddec82c8eba39bf27ac0517e159acf150=oci-layout://"
            + str(support / "base-layout")
            + "@"
            + _ALERT_BASE_MANIFEST,
            "--file",
            str(context / "Containerfile"),
            "--output",
            "type=oci,tar=false,dest=" + str(layout),
            str(context),
        ]
        native.run(argv, "pair-only-COPY-assembly", env, cwd=work, watched_output=work)
        index_path = layout / "index.json"
        real_directory(layout)
        require(index_path.exists() or index_path.is_symlink(), "AM_export_index_missing")
        index_info = index_path.lstat()
        require(
            stat.S_ISREG(index_info.st_mode)
            and index_info.st_nlink == 1
            and index_info.st_uid == os.getuid()
            and stat.S_IMODE(index_info.st_mode) in (0o600, 0o644)
            and 0 < index_info.st_size <= 64 * 1024,
            "AM_export_index_leaf",
        )
        index_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_nlink",
            "st_uid",
            "st_gid",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        with os.fdopen(
            os.open(index_path, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK), "r+b"
        ) as index_stream:
            opened = os.fstat(index_stream.fileno())
            require(
                all(getattr(index_info, field) == getattr(opened, field) for field in index_fields),
                "AM_export_index_identity",
            )
            raw_index: bytes = index_stream.read(64 * 1024 + 1)
            after_read, current = os.fstat(index_stream.fileno()), index_path.lstat()
            require(
                len(raw_index) == index_info.st_size
                and all(
                    getattr(index_info, field)
                    == getattr(after_read, field)
                    == getattr(current, field)
                    for field in index_fields
                ),
                "AM_export_index_changed",
            )
            raw_path = evidence / "pair-export-index.raw.json"
            with os.fdopen(
                os.open(raw_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600),
                "wb",
            ) as raw_stream:
                raw_stream.write(raw_index)
            raw_info = raw_path.lstat()
            require(
                raw_info.st_uid == os.getuid()
                and stat.S_IMODE(raw_info.st_mode) == 0o600
                and file_hash(raw_path, native.deadline) == sha256(raw_index).hexdigest(),
                "AM_export_index_raw_readback",
            )
            blob_inventory = tree_inventory(layout / "blobs", deadline=native.deadline)
            export_index: dict[str, Any] = one_object(raw_index)
            require(
                set(export_index) == {"schemaVersion", "mediaType", "manifests"}
                and type(export_index.get("schemaVersion")) is int
                and export_index["schemaVersion"] == 2
                and export_index.get("mediaType") == "application/vnd.oci.image.index.v1+json"
                and type(export_index.get("manifests")) is list
                and len(export_index["manifests"]) == 1
                and type(export_index["manifests"][0]) is dict,
                "AM_export_index_shape",
            )
            annotations = export_index["manifests"][0].get("annotations")
            require(
                type(annotations) is dict
                and set(annotations)
                == {"org.opencontainers.image.created", "org.opencontainers.image.ref.name"}
                and all(type(value) is str and value != "" for value in annotations.values())
                and annotations["org.opencontainers.image.ref.name"] == "latest",
                "AM_export_index_annotations",
            )
            created = annotations["org.opencontainers.image.created"]
            require(
                re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", created)
                is not None,
                "AM_export_index_created_UTC",
            )
            valid_created = True
            try:
                datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                valid_created = False
            require(valid_created, "AM_export_index_created_UTC")
            export_index["manifests"][0]["annotations"] = {
                "org.opencontainers.image.ref.name": "candidate"
            }
            canonical_index = json.dumps(export_index, separators=(",", ":")).encode("utf-8")
            index_stream.seek(0)
            current, opened = index_path.lstat(), os.fstat(index_stream.fileno())
            require(
                index_stream.read(64 * 1024 + 1) == raw_index
                and all(
                    getattr(index_info, field) == getattr(opened, field) == getattr(current, field)
                    for field in index_fields
                ),
                "AM_export_index_changed",
            )
            index_stream.seek(0)
            index_stream.write(canonical_index)
            index_stream.truncate()
            index_stream.flush()
            index_stream.seek(0)
            current, opened = index_path.lstat(), os.fstat(index_stream.fileno())
            require(
                index_stream.read(64 * 1024 + 1) == canonical_index
                and all(
                    getattr(index_info, field) == getattr(opened, field) == getattr(current, field)
                    for field in index_fields[:6]
                )
                and all(getattr(opened, field) == getattr(current, field) for field in index_fields)
                and current.st_size == len(canonical_index),
                "AM_export_index_canonical_readback",
            )
            canonical_path = evidence / "pair-export-index.canonical.json"
            with os.fdopen(
                os.open(
                    canonical_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
                ),
                "wb",
            ) as canonical_stream:
                canonical_stream.write(canonical_index)
            canonical_info = canonical_path.lstat()
            require(
                canonical_info.st_uid == os.getuid()
                and stat.S_IMODE(canonical_info.st_mode) == 0o600
                and file_hash(canonical_path, native.deadline)
                == sha256(canonical_index).hexdigest()
                and file_hash(index_path, native.deadline) == sha256(canonical_index).hexdigest(),
                "AM_export_index_canonical_evidence",
            )
            require(
                tree_inventory(layout / "blobs", deadline=native.deadline) == blob_inventory,
                "AM_export_index_blob_drift",
            )
        require(
            tree_inventory(context) == context_inventory
            and all(tree_inventory(inputs / name) == before for name, before in snapshots.items()),
            "AM_assembly_input_drift",
        )
        expected = {
            "usr/bin/" + name: file_hash(context / name) for name in ("alertmanager", "amtool")
        }
        expected.update(
            {
                "usr/bin/wget": _ALERT_PROBE_SHA256,
                "usr/bin/httpd": _ALERT_PROBE_SHA256,
                "etc/alertmanager/alertmanager.yml": file_hash(context / "alertmanager.yml"),
                "LICENSE": file_hash(context / "LICENSE"),
                "NOTICE": file_hash(context / "NOTICE"),
            }
        )
        require(file_hash(plugin) == _ALERT_BUILDX_SHA256, "AM_executed_Buildx_post_drift")
        graph = _alertmanager_candidate_graph(layout, support, expected)
        pack_layout(layout, work / "candidate.oci.tar")
        result.update(
            {
                "graph": graph,
                "context": context_inventory,
                "assembly_argv": argv,
                "input_inventory": snapshots,
                "output_hashes": {
                    name: file_hash(context / name) for name in ("alertmanager", "amtool")
                },
                "OCI_archive_sha256": file_hash(work / "candidate.oci.tar"),
            }
        )
    except BaseException as error:
        primary = error
        try:
            rejection = getattr(error, "layout_rejection", None)
            if rejection is not None:
                error.add_note(
                    "AM layout rejection: "
                    + json.dumps(rejection, ensure_ascii=True, sort_keys=True)
                )
        except BaseException:
            # Optional diagnostics must never replace the original predicate failure.
            pass
    finally:
        go_absent, builder_absent = False, not builder_attempted
        try:
            native.begin_cleanup()
            census = (
                native.run(
                    [
                        *prefix,
                        "ps",
                        "--all",
                        "--quiet",
                        "--no-trunc",
                        "--filter",
                        "label=pulseplate.alertmanager-module=" + token,
                    ],
                    "pair-cleanup-census",
                    env,
                    cwd=work,
                    cleaning=True,
                )
                .decode("ascii")
                .splitlines()
            )
            require(len(census) <= len(attempted), "AM_pair_cleanup_census_bound")
            for index, identifier in enumerate(
                sorted(census, key=lambda value: value not in owned)
            ):
                require(
                    re.fullmatch(r"[0-9a-f]{64}", identifier) is not None, "AM_pair_cleanup_full_ID"
                )
                row = one_object(
                    native.run(
                        [*prefix, "inspect", "--format", "{{json .}}", identifier],
                        "pair-cleanup-identify-" + str(index),
                        env,
                        cwd=work,
                        cleaning=True,
                    )
                )
                require(
                    row.get("Name", "")[1:] in attempted
                    and row.get("Config", {})
                    .get("Labels", {})
                    .get("pulseplate.alertmanager-module")
                    == token
                    and row.get("Id") == identifier,
                    "AM_pair_cleanup_attempt_binding",
                )
                retained_id = next(
                    (value for value, known_name in owned.items() if known_name == row["Name"][1:]),
                    None,
                )
                require(
                    retained_id is None or identifier == retained_id,
                    "AM_cleanup_returned_ID_replaced_HOLD",
                )
                if retained_id is None:
                    result.setdefault("failed_create_residue_bindings", []).append(
                        {
                            "Id": identifier,
                            "Name": row["Name"],
                            "origin": "independent_exact_attempt_name_label_census",
                        }
                    )
                    owned[identifier] = row["Name"][1:]
                _alertmanager_cleanup_member(
                    native,
                    docker,
                    identifier,
                    set(owned),
                    attempted,
                    token,
                    env,
                    work,
                    index,
                    config,
                )
            require(
                not native.run(
                    [
                        *prefix,
                        "ps",
                        "--all",
                        "--quiet",
                        "--no-trunc",
                        "--filter",
                        "label=pulseplate.alertmanager-module=" + token,
                    ],
                    "pair-cleanup-absence",
                    env,
                    cwd=work,
                    cleaning=True,
                ).strip(),
                "AM_pair_owned_absence",
            )
            go_absent = True
        except BaseException as error:
            cleanup_error = error
        try:
            if builder_attempted:
                row = one_object(
                    native.run(
                        [
                            *prefix,
                            "inspect",
                            "--format",
                            "{{json .}}",
                            "buildx_buildkit_" + builder + "0",
                        ],
                        "builder-cleanup-identify",
                        env,
                        cwd=work,
                        cleaning=True,
                    )
                )
                require(
                    row.get("Name") == "/buildx_buildkit_" + builder + "0"
                    and row.get("Image") == builder_image["Id"]
                    and "PULSEPLATE_AM_OWNER=" + token in row.get("Config", {}).get("Env", [])
                    and (not builder_id or row.get("Id") == builder_id),
                    "AM_builder_cleanup_ownership",
                )
                native.run(
                    [*prefix, "buildx", "rm", "--force", builder],
                    "builder-cleanup-remove",
                    env,
                    cwd=work,
                    cleaning=True,
                )
                require(
                    not native.run(
                        [
                            *prefix,
                            "ps",
                            "--all",
                            "--quiet",
                            "--no-trunc",
                            "--filter",
                            "id=" + row["Id"],
                        ],
                        "builder-cleanup-absence",
                        env,
                        cwd=work,
                        cleaning=True,
                    ).strip(),
                    "AM_builder_owned_absence",
                )
            builder_absent = True
        except BaseException as error:
            if cleanup_error is not None:
                cleanup_error.add_note("Owned builder cleanup also failed: " + type(error).__name__)
            else:
                cleanup_error = error
        result["owned_absence_observed"] = go_absent and builder_absent
        result["native_records"] = prep.records + ([] if native is prep else native.records)
        result["failure"] = None if primary is None else type(primary).__name__ + ":" + str(primary)
        result["cleanup_failure"] = None if cleanup_error is None else type(cleanup_error).__name__
        try:
            (work / "pair-observation.json").write_text(json.dumps(result, indent=2) + "\n")
        except BaseException as observation_error:
            original = primary if primary is not None else cleanup_error
            if original is None:
                raise
            original.add_note(
                "AM pair observation write also failed: " + type(observation_error).__name__
            )
    if primary is not None:
        if cleanup_error is not None:
            primary.add_note("Owned pair cleanup failed: " + type(cleanup_error).__name__)
        raise primary
    if cleanup_error is not None:
        raise cleanup_error
    return result


def _alertmanager_docker_load_transport(
    source: Path, graph: dict[str, Any], work: Path, deadline: float
) -> dict[str, Any]:
    """Render one private Docker-load wrapper from the already recognized OCI bytes."""
    import shutil
    from scripts.ci.prometheus_source_image import (
        MAX_CACHE_BYTES,
        SOURCE_DATE_EPOCH,
        _blob,
        _layout_inventory,
        _layout_root,
        check_deadline,
        file_hash,
        one_object,
        require,
        unpack_layout,
    )

    check_deadline(deadline)
    source_size = source.lstat().st_size
    reserve = 512 * 1024**2
    require(
        0 < source_size <= MAX_CACHE_BYTES
        and shutil.disk_usage(work).free >= 2 * source_size + 64 * 1024 + reserve,
        "AM_load_transport_byte_space_bound",
    )
    source_hash = file_hash(source, deadline)
    destination = work / "docker-load.tar"
    require(not destination.exists() and not destination.is_symlink(), "AM_load_transport_fresh")
    raw_source = source.read_bytes()
    require(sha256(raw_source).hexdigest() == source_hash, "AM_load_transport_source_read_drift")
    layout = work / "docker-load-layout"
    unpack_layout(raw_source, layout)
    del raw_source
    check_deadline(deadline)
    descriptor = _layout_root(layout)
    manifest = one_object(_blob(layout, descriptor))
    require(
        descriptor == graph["manifest"]
        and manifest["config"] == graph["config"]
        and manifest["layers"] == graph["layers"],
        "AM_load_transport_recognized_graph",
    )
    descriptors = [descriptor, manifest["config"], *manifest["layers"]]
    _layout_inventory(layout, {row["digest"] for row in descriptors})
    blobs = {"blobs/sha256/" + row["digest"][7:]: row for row in descriptors}
    names = ["oci-layout", "index.json", *sorted(blobs)]
    header = [
        {
            "Config": "blobs/sha256/" + manifest["config"]["digest"][7:],
            "RepoTags": [],
            "Layers": ["blobs/sha256/" + row["digest"][7:] for row in manifest["layers"]],
        }
    ]
    raw_header = (json.dumps(header, separators=(",", ":")) + "\n").encode()
    members: dict[str, dict[str, Any]] = {}
    total = 0
    with destination.open("xb") as output:
        destination.chmod(0o600)
        with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name in [*names, "manifest.json"]:
                check_deadline(deadline)
                require(shutil.disk_usage(work).free >= reserve, "AM_load_transport_free_reserve")
                raw = (
                    raw_header
                    if name == "manifest.json"
                    else (
                        _blob(layout, blobs[name])
                        if name in blobs
                        else (layout / name).read_bytes()
                    )
                )
                total += 512 + ((len(raw) + 511) // 512) * 512
                require(total + 10240 <= MAX_CACHE_BYTES, "AM_load_transport_output_bound")
                member = tarfile.TarInfo(name)
                member.size, member.mode, member.mtime = len(raw), 0o644, SOURCE_DATE_EPOCH
                archive.addfile(member, io.BytesIO(raw))
                members[name] = {"path": name, "size": len(raw), "sha256": sha256(raw).hexdigest()}
    leaf = destination.lstat()
    require(
        stat.S_ISREG(leaf.st_mode)
        and leaf.st_uid == os.getuid()
        and leaf.st_nlink == 1
        and stat.S_IMODE(leaf.st_mode) == 0o600
        and leaf.st_size <= MAX_CACHE_BYTES,
        "AM_load_transport_owned_regular_output",
    )
    observed: list[str] = []
    with tarfile.open(destination, "r:") as archive:
        for member in archive:
            check_deadline(deadline)
            require(
                len(observed) < len(members)
                and member.name == [*names, "manifest.json"][len(observed)]
                and member.isreg()
                and not member.pax_headers
                and not member.linkname
                and member.mode == 0o644
                and member.uid == member.gid == 0
                and member.uname == member.gname == ""
                and member.mtime == SOURCE_DATE_EPOCH
                and member.size == members[member.name]["size"],
                "AM_constructed_load_transport_member",
            )
            stream = archive.extractfile(member)
            require(stream is not None, "AM_constructed_load_transport_bytes")
            raw = cast(BinaryIO, stream).read(member.size + 1)
            require(
                len(raw) == member.size
                and sha256(raw).hexdigest() == members[member.name]["sha256"],
                "AM_constructed_load_transport_unchanged_bytes",
            )
            observed.append(member.name)
    require(observed == [*names, "manifest.json"], "AM_constructed_load_transport_complete")
    require(file_hash(source, deadline) == source_hash, "AM_load_transport_source_drift")
    check_deadline(deadline)
    require(shutil.disk_usage(work).free >= reserve, "AM_load_transport_final_free_reserve")
    record = {
        "source_OCI_sha256": source_hash,
        "load_input": str(destination),
        "load_archive_sha256": file_hash(destination, deadline),
        "docker_manifest": header,
        "docker_manifest_sha256": sha256(raw_header).hexdigest(),
        "members": list(members.values()),
    }
    evidence = work / "evidence/docker-load-transport.json"
    require(not evidence.exists() and not evidence.is_symlink(), "AM_load_transport_fresh_evidence")
    evidence.write_text(json.dumps(record, indent=2) + "\n")
    evidence.chmod(0o600)
    return record


def _alertmanager_final_security(
    archive: Path,
    graph: dict[str, Any],
    support: Path,
    work: Path,
    limits: dict[str, int],
    *,
    build_information: dict[str, Any],
) -> dict[str, Any]:
    """Scan the retained candidate and controls with the exact already-observed DB."""
    import shutil
    from scripts.ci.prometheus_source_image import (
        Native,
        file_hash,
        fresh_directory,
        one_object,
        require,
    )

    fresh_directory(work)
    evidence = work / "evidence"
    fresh_directory(evidence)
    deadline = time.monotonic() + limits["SECURITY_SECONDS"]
    native = Native(evidence, deadline, limits["CLEANUP_SECONDS"])
    scanner = support / "trivy"
    require(file_hash(scanner) == _ALERT_TRIVY_SHA256, "AM_final_pinned_scanner")
    scanner.chmod(0o555)
    config = work / "empty-docker-config"
    fresh_directory(config)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "DOCKER_CONFIG": str(config),
        "LANG": "C.UTF-8",
    }
    docker = shutil.which("docker")
    require(docker is not None and Path(docker).is_absolute(), "AM_final_Docker")
    prefix = [cast(str, docker), "--config", str(config)]
    reports: dict[str, Any] = {}
    primary: BaseException | None = None
    try:
        reports["docker_load_transport"] = _alertmanager_docker_load_transport(
            archive, graph, work, deadline
        )
        native.run(
            [*prefix, "image", "load", "--input", reports["docker_load_transport"]["load_input"]],
            "candidate-load-same-OCI",
            env,
            cwd=work,
        )
        observed = one_object(
            native.run(
                [*prefix, "image", "inspect", "--format", "{{json .}}", graph["config"]["digest"]],
                "candidate-loaded-config",
                env,
                cwd=work,
            )
        )
        require(
            observed.get("Id") == graph["config"]["digest"]
            and observed.get("Os") == "linux"
            and observed.get("Architecture") == "amd64"
            and observed.get("RootFS", {}).get("Layers") == graph["diff_ids"],
            "AM_loaded_candidate_graph",
        )
        empty_config, empty_ignore = work / "trivy.yaml", work / "trivy.ignore"
        empty_config.write_bytes(b"{}\n")
        empty_ignore.write_bytes(b"")

        def scan(kind: str, subject: Path, label: str) -> dict[str, Any]:
            require(
                file_hash(scanner) == _ALERT_TRIVY_SHA256
                and all(file_hash(support / "trivy-cache" / n) == h for n, h in _ALERT_DB.items()),
                "AM_final_scanner_DB_drift",
            )
            destination = evidence / (label + ".private.json")
            argv = [
                str(scanner),
                kind,
                "--config",
                str(empty_config),
                "--cache-dir",
                str(support / "trivy-cache"),
                "--skip-db-update",
                "--skip-java-db-update",
                "--skip-vex-repo-update",
                "--offline-scan",
                "--skip-version-check",
                "--disable-telemetry",
                "--scanners",
                "vuln,secret",
                "--pkg-types",
                "os,library",
                "--list-all-pkgs",
                "--severity",
                "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL",
                "--format",
                "json",
                "--exit-code",
                "0",
                "--ignore-unfixed=false",
                "--ignorefile",
                str(empty_ignore),
                "--timeout",
                str(limits["SCAN_TIMEOUT_SECONDS"]) + "s",
                "--output",
                str(destination),
            ]
            argv += ["--input", str(subject)] if kind == "image" else [str(subject)]
            native.run(argv, label, env, cwd=work, maximum_seconds=limits["SCAN_PROCESS_SECONDS"])
            require(
                destination.is_file()
                and not destination.is_symlink()
                and 0 < destination.stat().st_size <= 64 * 1024**2,
                "AM_final_native_report_missing",
            )
            destination.chmod(0o600)
            report: dict[str, Any] = one_object(destination.read_bytes())
            require(
                report.get("SchemaVersion") == 2 and type(report.get("SchemaVersion")) is int,
                "AM_final_native_schema",
            )
            require(
                all(file_hash(support / "trivy-cache" / n) == h for n, h in _ALERT_DB.items())
                and file_hash(scanner) == _ALERT_TRIVY_SHA256,
                "AM_final_scanner_DB_post_drift",
            )
            return report

        positive, negative = work / "positive", work / "negative"
        fresh_directory(positive)
        fresh_directory(negative)
        (positive / "credentials.txt").write_text(
            "GITHUB_PAT=ghp_" + "012345678901234567890123456789abcdef" + "\n"
        )
        (negative / "credentials.txt").write_text("plain harmless operational text\n")
        reports["secrets"] = _alertmanager_secret_controls(
            scan("fs", positive, "candidate-secret-positive"),
            scan("fs", negative, "candidate-secret-negative"),
            str(positive),
            str(negative),
        )
        reports["old_control"] = _alertmanager_vulnerability_control(
            scan(
                "image",
                support / "known-vulnerable-control.tar",
                "candidate-known-vulnerable-control",
            ),
            "sha256:53622b714941158bc20cc92a7571aef515556218eef914b7b8ec5b2a0cb6f607",
        )
        layout = work / "docker-load-layout"
        require(
            _alertmanager_candidate_graph(layout, support, graph["files"]) == graph
            and file_hash(archive, deadline)
            == reports["docker_load_transport"]["source_OCI_sha256"],
            "AM_final_candidate_scan_identity",
        )
        candidate_report = scan("image", layout, "candidate-full-supported")
        require(
            _alertmanager_candidate_graph(layout, support, graph["files"]) == graph
            and file_hash(archive, deadline)
            == reports["docker_load_transport"]["source_OCI_sha256"],
            "AM_final_candidate_scan_post_identity",
        )
        reports["candidate"] = _alertmanager_candidate_inventory(
            candidate_report,
            graph["config"]["digest"],
            one_object((support / "evidence/base-full-supported-scan.private.json").read_bytes()),
            build_information,
        )
        reports["scanner"] = {
            "sha256": _ALERT_TRIVY_SHA256,
            "DB": _ALERT_DB,
            "DB_metadata": one_object((support / "trivy-cache/db/metadata.json").read_bytes()),
        }
    except BaseException as error:
        primary = error
        raise
    finally:
        reports["native_records"] = native.records
        try:
            (work / "security-observation.json").write_text(json.dumps(reports, indent=2) + "\n")
        except BaseException as observation_error:
            if primary is not None:
                primary.add_note(
                    "AM security observation write also failed: " + type(observation_error).__name__
                )
                raise primary from None
            raise
    return reports


def _alertmanager_native_candidate(
    candidate: dict[str, Any], observation: Path, work: Path, limits: dict[str, int]
) -> dict[str, Any]:
    """Run retained local OCI bytes through the existing bounded Linux fixture owner."""
    from scripts.ci.prometheus_source_image import Native, fresh_directory, require

    require(
        Path(sys.executable).is_absolute() and not observation.is_symlink(),
        "AM_native_host_interpreter_input",
    )
    fresh_directory(work)
    evidence = work / "evidence"
    fresh_directory(evidence)
    # The child owns its main alarm; this outer deadline retains the cleanup margin.
    # The cleanup environment value alone is not child-side cleanup enforcement.
    started = time.monotonic()
    native = Native(
        evidence,
        started + limits["NATIVE_SECONDS"] + limits["NATIVE_CLEANUP_SECONDS"],
        limits["NATIVE_CLEANUP_SECONDS"],
    )
    env = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "HOME": str(work),
        "COMPOSE_PROFILES": "",
        "PYTHONUNBUFFERED": "1",
        "ALERTMANAGER_NATIVE_SECONDS": str(limits["NATIVE_SECONDS"]),
        "ALERTMANAGER_NATIVE_CLEANUP_SECONDS": str(limits["NATIVE_CLEANUP_SECONDS"]),
    }
    import shutil
    from scripts.ci.prometheus_source_image import one_object

    docker = shutil.which("docker")
    require(docker is not None and Path(docker).is_absolute(), "AM_native_Docker")
    docker_config = work / "empty-docker-config"
    fresh_directory(docker_config)
    env["DOCKER_CONFIG"] = str(docker_config)
    prefix = [cast(str, docker), "--config", str(docker_config)]
    result: dict[str, Any] = {"compiler_starts": 0}
    primary: BaseException | None = None
    try:
        result["docker_load_transport"] = _alertmanager_docker_load_transport(
            observation.parent / "candidate.oci.tar",
            candidate["graph"],
            work,
            started + limits["NATIVE_SECONDS"],
        )
        native.run(
            [*prefix, "image", "load", "--input", result["docker_load_transport"]["load_input"]],
            "native-load-retained-OCI",
            env,
            cwd=work,
            maximum_seconds=120,
        )
        image = one_object(
            native.run(
                [
                    *prefix,
                    "image",
                    "inspect",
                    "--format",
                    "{{json .}}",
                    candidate["graph"]["config"]["digest"],
                ],
                "native-retained-image",
                env,
                cwd=work,
                maximum_seconds=30,
            )
        )
        require(
            image.get("Id") == candidate["graph"]["config"]["digest"]
            and image.get("RootFS", {}).get("Layers") == candidate["graph"]["diff_ids"],
            "AM_native_same_retained_graph",
        )
        env["ALERTMANAGER_NATIVE_SECONDS"] = str(
            int(limits["NATIVE_SECONDS"] - (time.monotonic() - started))
        )
        require(int(env["ALERTMANAGER_NATIVE_SECONDS"]) > 1230, "AM_native_minimum_lifetime_budget")
        argv = [
            sys.executable,
            "-m",
            "tests.test_notify_premium_alias_checkpoint_failure",
            "--native-alertmanager",
            "--alertmanager-image-id",
            candidate["graph"]["config"]["digest"],
            "--alertmanager-config-sha256",
            _ALERT_Q_SOURCE_FILES["deploy/alertmanager/alertmanager.yml"],
            "--alertmanager-observation",
            str(observation),
        ]
        raw = native.run(argv, "full-AM-native", env, cwd=REPO_ROOT, output_bound=16 * 1024**2)
        require(b"native_AM_full_candidate_controls=pass" in raw, "AM_native_full_terminal_missing")
        result.update({"native_records": native.records, "stdout_sha256": sha256(raw).hexdigest()})
        return result
    except BaseException as error:
        primary = error
        result["failure"] = type(error).__name__ + ":" + str(error)
        raise
    finally:
        result["native_records"] = native.records
        try:
            (work / "native-observation.json").write_text(json.dumps(result, indent=2) + "\n")
        except BaseException as observation_error:
            if primary is not None:
                primary.add_note(
                    "AM native observation write also failed: " + type(observation_error).__name__
                )
                raise primary from None
            raise


def _alertmanager_consume(args: argparse.Namespace) -> None:
    """PR checks read the actual accepted original artifact; registry is never involved."""
    from scripts.ci.prometheus_source_image import (
        GitHubRead,
        authenticate_pr_source,
        fresh_directory,
        one_object,
        require,
    )

    _alertmanager_accepted_producer(
        args.alertmanager_candidate_run,
        args.alertmanager_candidate_artifact,
        args.alertmanager_candidate_source,
    )
    require(
        os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
        and os.environ.get("GITHUB_REPOSITORY") == "Katsiarynakavaleuskaya/PulsePlate",
        "AM_candidate_PR_event",
    )
    event_path = Path(os.environ.get("GITHUB_EVENT_PATH", ""))
    require(
        event_path.is_file()
        and not event_path.is_symlink()
        and event_path.stat().st_size <= 8 * 1024**2,
        "AM_candidate_PR_event_payload",
    )
    event = one_object(event_path.read_bytes())
    limits = _alertmanager_limits()
    output = args.output_dir.absolute()
    require(".." not in args.output_dir.parts, "AM_consumer_output_path")
    for parent in (output.parent, *output.parent.parents):
        require(
            not parent.is_symlink() and (not parent.exists() or parent.is_dir()),
            "AM_consumer_output_parent",
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    fresh_directory(output)
    evidence = output / "github-read-evidence"
    fresh_directory(evidence)
    api = GitHubRead(
        output / "private",
        evidence,
        time.monotonic() + limits["PREP_SECONDS"],
        limits["CLEANUP_SECONDS"],
    )
    try:
        pr = api.json("/repos/Katsiarynakavaleuskaya/PulsePlate/pulls/" + str(event.get("number")))
        require(
            pr.get("state") == "open"
            and pr.get("head", {}).get("sha") == args.source_sha
            and pr["head"].get("ref") == _ALERT_Q_BRANCH
            and pr["head"].get("repo", {}).get("id") == 1043311030
            and pr.get("base", {}).get("repo", {}).get("id") == 1043311030,
            "AM_actual_same_repository_open_PR",
        )
        authenticate_pr_source(
            api,
            event["number"],
            args.alertmanager_candidate_source,
            args.source_sha,
            "refs/heads/" + _ALERT_Q_BRANCH,
        )
        _alertmanager_authenticated_inputs(
            api,
            args.alertmanager_qualification_run,
            args.alertmanager_qualification_artifact,
            args.alertmanager_qualification_source,
            output / "qualification.zip",
        )
        _alertmanager_authenticated_inputs(
            api,
            args.alertmanager_support_run,
            args.alertmanager_support_artifact,
            args.alertmanager_support_source,
            output / "support.zip",
            kind="support",
        )
        authenticated = _alertmanager_authenticated_inputs(
            api,
            args.alertmanager_candidate_run,
            args.alertmanager_candidate_artifact,
            args.alertmanager_candidate_source,
            output / "candidate.zip",
            kind="candidate",
        )
        source = _alertmanager_source_snapshot(
            api, args.alertmanager_candidate_source, accepted=True
        )
    finally:
        api.close()
    inspected = _alertmanager_qualified_payload(output / "qualification.zip")
    support = output / "support"
    supported = _alertmanager_support_payload(output / "support.zip", support)
    inspected["plan"]["probe"] = supported["probe"]
    payload = output / "candidate"
    candidate = _alertmanager_candidate_payload(
        output / "candidate.zip", payload, source, inspected, support
    )
    require(
        candidate.get("source") == authenticated["source"],
        "AM_original_producer_not_current_consumer",
    )
    native = _alertmanager_native_candidate(
        candidate, payload / "candidate-observation.json", output / "native", limits
    )
    (output / "consumer-observation.json").write_text(
        json.dumps(
            {
                "consumer": args.source_sha,
                "original_producer": authenticated,
                "graph": candidate["graph"],
                "native": native,
                "compiler_starts": 0,
                "registry_login": False,
            },
            indent=2,
        )
        + "\n"
    )


def _alertmanager_publish(
    args: argparse.Namespace,
    api: GitHubRead,
    output: Path,
    retained: Path,
    result: dict[str, Any],
    limits: dict[str, int],
) -> dict[str, Any]:
    """One guarded exact-byte main publication; canonical package/tag uncertainty holds."""
    import shutil
    from scripts.ci.prometheus_source_image import (
        authenticate_pr_source,
        require,
        retained_tool,
        existing_public_package,
        immutable_tag_state,
        _blob,
        pack_layout,
        file_hash,
        check_deadline,
    )

    _alertmanager_accepted_producer(
        args.alertmanager_candidate_run,
        args.alertmanager_candidate_artifact,
        args.alertmanager_candidate_source,
    )
    current = api.json("/repos/Katsiarynakavaleuskaya/PulsePlate/git/ref/heads/main")
    require(
        current.get("object", {}).get("sha") == args.source_sha, "AM_exact_current_main_publication"
    )
    require(
        type(args.alertmanager_pr) is int and args.alertmanager_pr > 0,
        "AM_publication_actual_merged_PR_required",
    )
    pr = api.json("/repos/Katsiarynakavaleuskaya/PulsePlate/pulls/" + str(args.alertmanager_pr))
    require(
        pr.get("merged") is True
        and pr.get("merge_commit_sha") == args.source_sha
        and pr.get("base", {}).get("ref") == "main"
        and pr.get("head", {}).get("ref") == _ALERT_Q_BRANCH,
        "AM_separate_human_merge_observed",
    )
    authenticate_pr_source(
        api,
        args.alertmanager_pr,
        args.alertmanager_candidate_source,
        pr["head"]["sha"],
        "refs/heads/" + _ALERT_Q_BRANCH,
    )
    original = _alertmanager_authenticated_inputs(
        api,
        args.alertmanager_candidate_run,
        args.alertmanager_candidate_artifact,
        args.alertmanager_candidate_source,
        output / "candidate.zip",
        kind="candidate",
    )
    source = _alertmanager_source_snapshot(api, args.alertmanager_candidate_source, accepted=True)
    inspected = _alertmanager_qualified_payload(output / "qualification.zip")
    support = output / "support"
    supported = _alertmanager_support_payload(output / "support.zip", support)
    inspected["plan"]["probe"] = supported["probe"]
    candidate = _alertmanager_candidate_payload(
        output / "candidate.zip", output / "candidate", source, inspected, support
    )
    tool, qualified = retained_tool(api, REPO_ROOT, output)
    digest = candidate["graph"]["manifest"]["digest"]
    tag = "alertmanager-0.34.1-" + digest.removeprefix("sha256:")
    destination = "ghcr.io/katsiarynakavaleuskaya/pulseplate"
    result.update(
        {
            "original_producer": original,
            "qualified_tool": qualified["coordinates"],
            "graph": candidate["graph"],
            "copy_attempts": 0,
            "copy_invocations": 0,
            "package_WRITE": "UNPROVED",
            "tag": tag,
        }
    )
    identity, versions = existing_public_package(api)
    present = immutable_tag_state(versions, tag, digest)
    result["public_package"] = identity
    require(
        api.json("/repos/Katsiarynakavaleuskaya/PulsePlate/git/ref/heads/main")
        .get("object", {})
        .get("sha")
        == args.source_sha,
        "AM_main_before_registry_credentials",
    )
    require(
        tool.is_absolute()
        and tool.is_file()
        and not tool.is_symlink()
        and file_hash(tool) == _ALERT_ORAS_SHA256,
        "AM_publication_retained_ORAS_bytes",
    )
    check_deadline(api.deadline)
    api.deadline = time.monotonic() + limits["PUBLICATION_SECONDS"]
    api.cleanup_seconds = limits["NATIVE_CLEANUP_SECONDS"]
    registry = api.private / "config/registry"
    registry.mkdir(mode=0o700)
    credential = registry / "config.json"
    docker = shutil.which("docker")
    require(docker is not None and Path(docker).is_absolute(), "AM_publication_absolute_Docker")
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    require(owner.lower() == "katsiarynakavaleuskaya" and bool(token), "AM_publication_owner_token")
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(api.private / "home"),
        "DOCKER_CONFIG": str(registry),
        "LANG": "C.UTF-8",
    }
    api._capture(
        [
            cast(str, docker),
            "--config",
            str(registry),
            "login",
            "ghcr.io",
            "--username",
            owner,
            "--password-stdin",
        ],
        2 * 1024**2,
        environment=env,
        input_data=token.encode() + b"\n",
    )
    info = credential.lstat()
    require(
        {v.name for v in registry.iterdir()} == {"config.json"}
        and stat.S_ISREG(info.st_mode)
        and info.st_uid == os.getuid()
        and info.st_nlink == 1
        and stat.S_IMODE(info.st_mode) == 0o600,
        "AM_owned0600_registry_config",
    )
    copy = [
        str(tool),
        "cp",
        "--registry-config",
        str(credential),
        "--from-oci-layout",
        str(output / "candidate/layout") + "@" + digest,
        destination + ":" + tag,
    ]
    pullback = [
        str(tool),
        "cp",
        "--registry-config",
        str(credential),
        "--to-oci-layout",
        destination + "@" + digest,
        str(output / "pullback") + ":pullback",
    ]
    result["publication_commands"] = [copy, pullback]
    if not present:
        require(
            api.json("/repos/Katsiarynakavaleuskaya/PulsePlate/git/ref/heads/main")
            .get("object", {})
            .get("sha")
            == args.source_sha,
            "AM_main_immediately_before_copy",
        )
        result["copy_attempts"] = 1
        api._capture(copy, 2 * 1024**2, environment=env)
        result["copy_invocations"] = 1
        result["package_WRITE"] = "OBSERVED_SUCCESSFUL_INTENDED_COPY"
    else:
        result["package_WRITE"] = "UNEXERCISED_EXISTING_SAME_SUBJECT"
    api._capture(pullback, 2 * 1024**2, environment=env)
    actual = _alertmanager_candidate_graph(
        output / "pullback", support, candidate["graph"]["files"]
    )
    require(actual == candidate["graph"], "AM_immutable_pullback_graph_payload")
    for descriptor in (actual["manifest"], actual["config"], *actual["layers"]):
        require(
            _blob(output / "candidate/layout", descriptor)
            == _blob(output / "pullback", descriptor),
            "AM_pullback_every_raw_blob",
        )
    after_identity, after_versions = existing_public_package(api)
    require(
        after_identity == identity and immutable_tag_state(after_versions, tag, digest),
        "AM_publication_canonical_readback",
    )
    require(
        api.json("/repos/Katsiarynakavaleuskaya/PulsePlate/git/ref/heads/main")
        .get("object", {})
        .get("sha")
        == args.source_sha,
        "AM_current_main_after_copy",
    )
    pack_layout(output / "pullback", retained / "candidate.oci.tar")
    (retained / "pullback-native-input.json").write_text(json.dumps(candidate, indent=2) + "\n")
    result["pullback_OCI_archive_sha256"] = file_hash(retained / "candidate.oci.tar")
    result["status"] = "OBSERVED_COPY_AND_IMMUTABLE_BLOBS_NATIVE_PENDING"
    result["tag_observation_limit"] = (
        "Canonical finite pre/post observations; no atomic no-clobber or continuous immutability claim."
    )
    return candidate


def _alertmanager_retain_execution(output: Path, retained: Path) -> None:
    """The three finite AM phases retain raw failures as well as accepted results."""
    import shutil
    from scripts.ci.prometheus_source_image import file_hash, require, tree_inventory

    observations = {
        "pair": ("pair-observation.json", "invocation-start.json"),
        "security": ("security-observation.json",),
        "native": ("native-observation.json",),
    }
    for phase, filenames in observations.items():
        work = output / phase
        evidence = work / "evidence"
        if evidence.exists() or evidence.is_symlink():
            require(evidence.is_dir() and not evidence.is_symlink(), "AM_phase_evidence_directory")
            before = tree_inventory(evidence)
            destination = retained / (phase + "-evidence")
            shutil.copytree(evidence, destination)
            require(
                tree_inventory(destination) == before and tree_inventory(evidence) == before,
                "AM_complete_phase_evidence_retention",
            )
        for name in filenames:
            source = work / name
            if source.exists() or source.is_symlink():
                require(
                    source.is_file()
                    and not source.is_symlink()
                    and source.stat().st_nlink == 1
                    and 0 < source.stat().st_size <= 64 * 1024**2,
                    "AM_phase_observation_leaf",
                )
                destination = retained / (phase + "-" + name)
                shutil.copyfile(source, destination)
                destination.chmod(0o600)
                require(
                    file_hash(source) == file_hash(destination), "AM_phase_observation_retention"
                )
    for binary in ("alertmanager", "amtool"):
        source = output / "pair/output" / binary
        if source.exists() or source.is_symlink():
            require(
                source.is_file()
                and not source.is_symlink()
                and source.stat().st_nlink == 1
                and 0 <= source.stat().st_size <= 256 * 1024**2,
                "AM_retained_spent_binary_leaf",
            )
            destination = retained / "pair-outputs" / binary
            destination.parent.mkdir(mode=0o700, exist_ok=True)
            binary_digest = file_hash(source)
            if destination.exists() or destination.is_symlink():
                require(
                    destination.is_file()
                    and not destination.is_symlink()
                    and destination.stat().st_nlink == 1
                    and file_hash(destination) == binary_digest,
                    "AM_previously_retained_spent_binary_drift",
                )
            else:
                shutil.copyfile(source, destination)
                destination.chmod(0o600)
            require(
                file_hash(source) == binary_digest == file_hash(destination),
                "AM_retained_spent_binary_bytes",
            )


def _alertmanager_execution(args: argparse.Namespace) -> None:
    """Connected manual proposal; only an actual operator dispatch can select build/publish."""
    import shutil
    from scripts.ci.prometheus_source_image import GitHubRead, file_hash, fresh_directory, require

    if args.alertmanager_stage == "publish":
        _alertmanager_accepted_producer(
            args.alertmanager_candidate_run,
            args.alertmanager_candidate_artifact,
            args.alertmanager_candidate_source,
        )
    limits = _alertmanager_limits()
    require(
        args.artifact == "alertmanager"
        and not args.alertmanager_module_qualify
        and args.manifest == DEFAULT_MANIFEST,
        "AM_effectful_mode_has_no_Q_or_identity_override",
    )
    require(
        (
            args.alertmanager_qualification_run,
            args.alertmanager_qualification_artifact,
            args.alertmanager_qualification_source,
        )
        == (_ALERT_Q_RUN, _ALERT_Q_ARTIFACT, _ALERT_Q_SOURCE)
        and (
            args.alertmanager_support_run,
            args.alertmanager_support_artifact,
            args.alertmanager_support_source,
        )
        == (_ALERT_S_RUN, _ALERT_S_ARTIFACT, _ALERT_S_SOURCE),
        "AM_required_exact_Q_S_before_execution",
    )
    require(
        os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
        and os.environ.get("GITHUB_REPOSITORY") == "Katsiarynakavaleuskaya/PulsePlate"
        and os.environ.get("GITHUB_REPOSITORY_ID") == "1043311030"
        and os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
        and type(args.source_sha) is str
        and re.fullmatch(r"[0-9a-f]{40}", args.source_sha) is not None
        and args.source_sha == os.environ.get("GITHUB_SHA")
        and os.environ.get("GITHUB_REF")
        == (
            "refs/heads/main"
            if args.alertmanager_stage == "publish"
            else "refs/heads/" + _ALERT_Q_BRANCH
        ),
        "AM_exact_manual_execution_source_HOLD",
    )
    output = args.output_dir.absolute()
    require(
        ".." not in args.output_dir.parts and not output.is_symlink(), "AM_execution_output_path"
    )
    for parent in (output.parent, *output.parent.parents):
        require(
            not parent.is_symlink() and (not parent.exists() or parent.is_dir()),
            "AM_execution_output_parent",
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    fresh_directory(output)
    retained = output / "retained"
    fresh_directory(retained)
    evidence = retained / "github-read-evidence"
    fresh_directory(evidence)
    started = time.monotonic()
    deadline = started + limits["PREP_SECONDS"]
    api = GitHubRead(output / "private", evidence, deadline, limits["CLEANUP_SECONDS"])
    result: dict[str, Any] = {
        "source": args.source_sha,
        "compiler_starts": 0,
        "logical_build_starts": 0,
        "status": "HOLD_NO_EXECUTION_OUTCOME",
        "policy_version": "DEP-AM-SEC-1.acceptance.v1",
    }
    published: dict[str, Any] | None = None
    try:
        try:
            git = shutil.which("git")
            require(git is not None and Path(git).is_absolute(), "AM_execution_absolute_Git")
            checkout = api._capture(
                [cast(str, git), "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                1024,
                environment={
                    "PATH": "/usr/bin:/bin",
                    "HOME": str(api.private / "home"),
                    "LANG": "C.UTF-8",
                },
            )
            require(
                checkout == (args.source_sha + "\n").encode(), "AM_execution_actual_checkout_HEAD"
            )
            commit = api.json("/repos/Katsiarynakavaleuskaya/PulsePlate/commits/" + args.source_sha)
            require(commit.get("sha") == args.source_sha, "AM_execution_API_source")
            q = _alertmanager_authenticated_inputs(
                api,
                args.alertmanager_qualification_run,
                args.alertmanager_qualification_artifact,
                args.alertmanager_qualification_source,
                output / "qualification.zip",
            )
            support_binding = _alertmanager_authenticated_inputs(
                api,
                args.alertmanager_support_run,
                args.alertmanager_support_artifact,
                args.alertmanager_support_source,
                output / "support.zip",
                kind="support",
            )
            _alertmanager_package_read(api)
            if args.alertmanager_stage == "publish":
                published = _alertmanager_publish(args, api, output, retained, result, limits)
            else:
                result["producer_source_files"] = {}
                for path, raw in _alertmanager_source_snapshot(api, args.source_sha).items():
                    require(
                        raw == (REPO_ROOT / path).read_bytes(),
                        "AM_execution_current_checkout_source",
                    )
                    destination = retained / "producer-source" / path
                    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    destination.write_bytes(raw)
                    result["producer_source_files"][path] = file_hash(destination)
        finally:
            api.close()
        require(
            not api.private.exists() and not api.private.is_symlink(),
            "AM_credentials_removed_before_native",
        )
        if published is not None:
            result["credential_cleanup_observed"] = True
            result["native"] = _alertmanager_native_candidate(
                published, retained / "pullback-native-input.json", output / "native", limits
            )
            result["status"] = "OBSERVED_IMMUTABLE_PUBLICATION_PULLBACK_NATIVE"
            return
        inspected = _alertmanager_qualified_payload(output / "qualification.zip")
        support = output / "support"
        supported = _alertmanager_support_payload(output / "support.zip", support)
        inspected["plan"]["probe"] = supported["probe"]
        inputs = output / "inputs"
        _alertmanager_materialize(output / "qualification.zip", inputs, deadline)
        result["upstream"] = {"qualification": q, "support": support_binding}
        result["plan"] = inspected["plan"]
        result["UI_file_hashes"] = inspected["plan"]["UI_file_hashes"]
        result["support"] = {
            k: supported[k] for k in ("probe", "scanner", "base_scan", "probe_scan")
        }
        _alertmanager_pair(
            inputs,
            support,
            inspected["plan"],
            output / "pair",
            result,
            limits,
            deadline,
            retained=retained,
        )
        shutil.copyfile(output / "pair/candidate.oci.tar", retained / "candidate.oci.tar")
        observation = retained / "candidate-observation.json"
        observation.write_text(json.dumps(result, indent=2) + "\n")
        result["security"] = _alertmanager_final_security(
            retained / "candidate.oci.tar",
            result["graph"],
            support,
            output / "security",
            limits,
            build_information=result["build_information"],
        )
        observation.write_text(json.dumps(result, indent=2) + "\n")
        result["native"] = _alertmanager_native_candidate(
            result, observation, output / "native", limits
        )
        result["status"] = "OBSERVED_NATIVE_SECURITY_ACCEPTED"
    except BaseException as error:
        result["failure"] = type(error).__name__ + ":" + str(error)
        raise
    finally:
        original_error = sys.exc_info()[1]
        try:
            destination = retained / "candidate-observation.json"
            destination.write_text(json.dumps(result, indent=2) + "\n")
            destination.chmod(0o600)
            _alertmanager_retain_execution(output, retained)
            _alertmanager_finalize_payload(retained, time.monotonic() + limits["CLEANUP_SECONDS"])
        except BaseException as retention_error:
            if original_error is not None:
                original_error.add_note(
                    "AM raw evidence retention also failed: " + type(retention_error).__name__
                )
                raise original_error from None
            raise


def _inspect_alertmanager_inputs(args: argparse.Namespace) -> None:
    """Inspect retained Q and optional native support without starting a compiler."""
    from scripts.ci.prometheus_source_image import GitHubRead, fresh_directory, require

    require(
        type(args.alertmanager_qualification_run) is int
        and args.alertmanager_qualification_run == _ALERT_Q_RUN
        and type(args.alertmanager_qualification_artifact) is int
        and args.alertmanager_qualification_artifact == _ALERT_Q_ARTIFACT
        and args.alertmanager_qualification_source == _ALERT_Q_SOURCE,
        "AM_qualification_exact_selectors",
    )
    seconds = os.environ.get("ALERTMANAGER_INPUT_INSPECT_SECONDS", "")
    require(
        re.fullmatch(r"[1-9][0-9]{0,2}", seconds) is not None and int(seconds) <= 600,
        "AM_input_inspection_budget",
    )
    output = args.output_dir.absolute()
    require(".." not in args.output_dir.parts, "AM_input_output_path")
    for parent in (output.parent, *output.parent.parents):
        require(
            not parent.is_symlink() and (not parent.exists() or parent.is_dir()),
            "AM_input_output_parent",
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    fresh_directory(output)
    evidence = output / "github-read-evidence"
    fresh_directory(evidence)
    api = GitHubRead(output / "private", evidence, time.monotonic() + int(seconds), 45)
    try:
        authentication = _alertmanager_authenticated_inputs(
            api,
            args.alertmanager_qualification_run,
            args.alertmanager_qualification_artifact,
            args.alertmanager_qualification_source,
            output / "qualification.zip",
        )
        package = _alertmanager_package_read(api)
    finally:
        api.close()
    inspected = _alertmanager_qualified_payload(output / "qualification.zip")
    result = {
        "asset_type": "Alertmanager retained-input inspection",
        "upstream": authentication,
        "package_read": package,
        "inspection": inspected,
        "policy_version": "DEP-AM-SEC-1.acceptance.v1",
        "authority": "observation_only",
        "consumer_source": os.environ.get("GITHUB_SHA"),
        "replay": "fresh_output_required_no_Q_or_build_retry",
        "idempotency_key": "AM-inputs-" + _ALERT_Q_SOURCE + "-" + str(_ALERT_Q_RUN),
        "compiler_admission": "HOLD_SEPARATE_HUMAN_DECISION",
    }
    destination = output / "input-inspection.json"
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    destination.chmod(0o600)
    if args.alertmanager_stage == "support-inspect":
        try:
            inspected["support"] = _alertmanager_support_observation(
                output / "qualification.zip", output
            )
            inspected["plan"]["probe"] = inspected["support"]["probe"]
            inspected["outstanding"] = [
                "complete_primary_advisory_and_build_packet_review",
                "separate_human_pair_compiler_admission",
                "actual_final_candidate_build_info_full_scans_and_native_acceptance",
            ]
        except BaseException as error:
            inspected["support"] = {
                "state": "HOLD_NATIVE_FAILURE_OR_UNSUPPORTED",
                "failure": type(error).__name__,
                "raw_observation": "native-support/support-observation.json",
            }
            raise
        finally:
            destination.write_text(json.dumps(result, indent=2) + "\n")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alertmanager-module-qualify",
        action="store_true",
        help="Fixed manual metadata replay, zero builds; requires retained Go and base inputs.",
    )
    parser.add_argument(
        "--alertmanager-stage",
        choices=(
            "disabled",
            "input-inspect",
            "support-inspect",
            "build",
            "candidate-check",
            "publish",
        ),
        default="disabled",
    )
    parser.add_argument("--alertmanager-qualification-run", type=int)
    parser.add_argument("--alertmanager-qualification-artifact", type=int)
    parser.add_argument("--alertmanager-qualification-source")
    parser.add_argument("--alertmanager-support-run", type=int)
    parser.add_argument("--alertmanager-support-artifact", type=int)
    parser.add_argument("--alertmanager-support-source")
    parser.add_argument("--alertmanager-candidate-run", type=int)
    parser.add_argument("--alertmanager-candidate-artifact", type=int)
    parser.add_argument("--alertmanager-candidate-source")
    parser.add_argument("--alertmanager-pr", type=int)
    parser.add_argument("--source-sha")
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
    if args.alertmanager_stage != "disabled":
        if (
            args.alertmanager_module_qualify
            or args.artifact != "alertmanager"
            or args.manifest != DEFAULT_MANIFEST
        ):
            raise RuntimeError("Alertmanager inspection has no Q/manifest/identity override.")
        if args.alertmanager_stage in ("input-inspect", "support-inspect"):
            _inspect_alertmanager_inputs(args)
        elif args.alertmanager_stage == "candidate-check":
            _alertmanager_consume(args)
        else:
            _alertmanager_execution(args)
        return 0
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
