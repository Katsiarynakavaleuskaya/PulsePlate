#!/usr/bin/env python3
"""Qualify the one approved Prometheus source graph; never build or select an image.

Only the explicit hosted metadata job calls this entrypoint. Go owns module
semantics. Raw package observations require independent advisory review and
later binary cross-checks; this module makes no remediation/publication claim.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import ssl
import stat
import subprocess  # nosec B404: # fixed native Go/Docker metadata commands require subprocess (remove-by: 2026-10-28, ref: PR-2477)
import sys
import tarfile
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener
import uuid
import zlib

REVISION = "5241a27fe3c6983549fccc32f6e65917408c63cd"
TREE = "ffa0c7e9512071483f6c40a95aba9b97fbd86583"
GO_VERSION = "go version go1.27.2 linux/amd64\n"
BASE = "gcr.io/distroless/static-debian13@sha256:2293b36c7c9082bf4115aab724b4d2cddec82c8eba39bf27ac0517e159acf150"
BASE_CONFIG = "sha256:55a757dc8ab862a4eb634c434261dcd26f17c186b54f7bce845404a335456110"
ROOT_MODULE = "github.com/prometheus/prometheus"
LOCKS = {
    "go.mod": "94e39d68d3abd10168c4b1944a63356a1d9a467ddeceee46aea75fc14e4381d1",
    "go.sum": "2b0f11cdccdc6605922c8f48d7afc68ae44fdc90df6b5d2f6f677b447b07d99e",
}
SOURCE_INVENTORY = "5ccb3d899fc89ba6f918d71a2923742172baa2f9a073789f70529e088c5a3a8b"
EMBED_TEMPLATE = "ccdee3172876fa092175431df6986274737d06f0b6409cb280ad91833c2f1755"
GO_LICENSE = "911f8f5782931320f5b8d1160a76365b83aea6447ee6c04fa6d5591467db9dad"
SOURCE_LICENSES = {
    "LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
    "NOTICE": "ac9e304462a58a4d71b6488423d4447e614c8b31d517fe24345016522c102a78",
}
UI_FILES = {
    "static/react-app/manifest.json": {
        "size": 318,
        "sha256": "976d3997489cdc4998a52e6e6245cdd9487a1af915d5c068fd790c5dc4a5df7a",
    },
    "static/react-app/static/js/main.5b2d3908.js.LICENSE.txt": {
        "size": 3152,
        "sha256": "c6472c3954f3ac3117d32db6b0f026236708b835ad52ee1acbc3f378cbd17a66",
    },
    "static/react-app/static/js/main.5b2d3908.js.map": {
        "size": 7267253,
        "sha256": "9dd0a666b35cdfd61eb2719615add94d64cbe476c00b8838ce6d0c6a626b4903",
    },
    "static/react-app/static/js/main.5b2d3908.js": {
        "size": 2195301,
        "sha256": "b4fe2ab290b349c142a755d217591a44a44bda65e625d17257ac22bfe09ba558",
    },
    "static/react-app/static/css/main.3a01f811.css.map": {
        "size": 340286,
        "sha256": "8cad096102e1780946316d1eb69bc2e9ec437faae425d383b4bab17a3defb73e",
    },
    "static/react-app/static/css/main.3a01f811.css": {
        "size": 414406,
        "sha256": "5352633a20e078eafc288d4aa7e7593918c2e8803bdff80be10e29c2d98ab966",
    },
    "static/react-app/static/media/index.f6d03137e8c9dd0de04c.cjs": {
        "size": 329,
        "sha256": "1dd6e0edcfd633f8b90187b580982bc3ba7308d3050da2988ba2271368f5569a",
    },
    "static/react-app/static/media/prometheus_logo_grey.3cf697e5443028ca5e5255b93c7906c5.svg": {
        "size": 1533,
        "sha256": "584958f7b25abe6db5f9dff2b6743c60311571feaa2c3f5047d831ae92e74489",
    },
    "static/react-app/static/media/codicon.b3726f0165bf67ac6849.ttf": {
        "size": 61024,
        "sha256": "1b55f12eca93ba6743e7a196adb0fd4828a4f85311d17f21d03a65a6fe763b6e",
    },
    "static/react-app/index.html": {
        "size": 751,
        "sha256": "80358a376abe4495010d10c5f03aec56dd0bb5baaf25eb0e5f0e186ee8a550b5",
    },
    "static/react-app/favicon.ico": {
        "size": 15086,
        "sha256": "d72fc7b0bd1a4c1c4a016dfa4bfd594b2fb65a409575ec8f857864d4bdc658be",
    },
    "static/react-app/asset-manifest.json": {
        "size": 657,
        "sha256": "bf3d5f3fb1c3dc7eada20b561603a754288190c68e0f35f68bf1bc69a86d4122",
    },
    "static/mantine-ui/favicon.svg": {
        "size": 2777,
        "sha256": "cb3a90f7f2449b1696f6e253c03ba3eecefe174fca96b67a7f238e3b0345cea5",
    },
    "static/mantine-ui/assets/codicon-B_nZgZYP.ttf": {
        "size": 61024,
        "sha256": "1b55f12eca93ba6743e7a196adb0fd4828a4f85311d17f21d03a65a6fe763b6e",
    },
    "static/mantine-ui/assets/third-party-licenses.txt": {
        "size": 100441,
        "sha256": "5f9909113990a31a464a36362831b9eca44ce48084edb51484a8d58ef4850871",
    },
    "static/mantine-ui/assets/index-MKGKlG4_.js": {
        "size": 1931373,
        "sha256": "a931767fe023a9076a56663d43cc453f1a2e020037ebbdb3e5231072e3c05d06",
    },
    "static/mantine-ui/assets/index-BV7pz6k1.css": {
        "size": 286212,
        "sha256": "a70076684eaf0dff3e809211397bad284a2fafaa5f6605c902afdf5620bc8fd8",
    },
    "static/mantine-ui/index.html": {
        "size": 1832,
        "sha256": "266f63a42dcaf55fe74c264aaa037b17d74adc7c501da6a9fcc3218714cedb48",
    },
}
# References retain every primary record; observations below never disposition it.
ADVISORIES = {
    "GO-2026-6603": "76a1945737d8c2ea4a34d18fd44230946b1185894ea155f9812d1149b2838d3c",
    "GO-2026-6610": "2c7881c7945c7c5eadefd3d0caceb1a23b14467373fb28c601141545ff21f190",
    "GO-2026-6611": "5e89ac4314a24eac41111b71ef4544f22836c7b1baf48747e31c5c1d8282c3de",
    "GO-2026-6612": "76c44a4cbdbc463286fb968abd288a26025b8576fe2aed3dcda542fde9518452",
    "GO-2026-6617": "197efc1b2f05e891ab3dad2127b7ea3997dc80dc39b21294ab93e11333c4c08b",
    "GO-2026-5932": "f277b0400996200a7d5034c676661cd8cf18adeab1fdc5d0dc369e456ddf1fad",
}
AFFECTED_PATHS = (
    "golang.org/x/net/http2",
    "golang.org/x/crypto/openpgp",
    "golang.org/x/crypto/openpgp/packet",
    "golang.org/x/crypto/openpgp/armor",
    "golang.org/x/crypto/openpgp/clearsign",
    "golang.org/x/crypto/openpgp/errors",
    "golang.org/x/crypto/openpgp/elgamal",
    "golang.org/x/crypto/openpgp/s2k",
)
MAX_NATIVE_OUTPUT = 64 * 1024**2
MAX_CACHE_BYTES = 2 * 1024**3
LABEL = "io.pulseplate.prometheus-source-qualification"
GUEST_TMP = Path("/qualification")
GUEST_TMPFS = "rw,nosuid,nodev,noexec,size=1g,mode=1777"
CLEANING = False
INTERRUPTIONS: list[int] = []


class QualificationError(RuntimeError):
    """Constant diagnostics only: signed release URLs must never be logged."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise QualificationError(code)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_deadline(deadline: float | None) -> None:
    require(deadline is None or time.monotonic() < deadline, "qualification_deadline")


def interrupt(signum: int, frame: Any) -> None:
    INTERRUPTIONS.append(signum)
    if not CLEANING:
        raise KeyboardInterrupt("owned_qualification_interrupted")


def file_hash(path: Path, deadline: float | None = None) -> str:
    """Read one bounded single-link regular leaf in cooperative private directories."""
    real_directory(path.parent)
    leaf = path.lstat()
    require(stat.S_ISREG(leaf.st_mode) and leaf.st_nlink == 1, "nonregular_or_multilink_file")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    descriptor = os.open(path, flags)
    digest, total = hashlib.sha256(), 0
    try:
        before = os.fstat(descriptor)
        require(
            stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and (before.st_dev, before.st_ino) == (leaf.st_dev, leaf.st_ino),
            "file_leaf_identity",
        )
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            for chunk in iter(lambda: stream.read(1024**2), b""):
                check_deadline(deadline)
                total += len(chunk)
                require(total <= MAX_CACHE_BYTES, "file_byte_bound")
                digest.update(chunk)
        after = os.fstat(descriptor)
        current = path.lstat()
        fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_nlink",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        require(
            all(
                getattr(before, field) == getattr(after, field) == getattr(current, field)
                for field in fields
            )
            and total == before.st_size,
            "file_changed",
        )
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def producer_paths() -> tuple[Path, Path]:
    helper = Path(__file__).absolute()
    return helper, helper.parents[2] / ".github/workflows/build.yml"


def real_directory(path: Path) -> None:
    require(path.is_absolute() and ".." not in path.parts, "unsafe_directory")
    for parent in (path, *path.parents):
        info = parent.lstat()
        require(
            stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode), "nonreal_directory_chain"
        )


def fresh_directory(path: Path, mode: int = 0o700) -> None:
    real_directory(path.parent)
    require(not path.exists() and not path.is_symlink(), "output_not_fresh")
    path.mkdir(mode=mode)
    real_directory(path)


@dataclass(frozen=True)
class Artifact:
    name: str
    url: str
    size: int
    digest: str
    root: str
    members: int
    files: int
    expanded: int
    release: bool = False


SOURCE = Artifact(
    "source",
    "https://codeload.github.com/prometheus/prometheus/tar.gz/" + REVISION,
    6163228,
    "eee7ec029ffdba7d9ee59171cad5ddaff10e71514b0bae1a6fde6dc1ae99e181",
    "prometheus-" + REVISION,
    1951,
    1686,
    32 * 1024**2,
)
GO = Artifact(
    "go",
    "https://dl.google.com/go/go1.27.2.linux-amd64.tar.gz",
    70590635,
    "ecbadb99091a3f46e31f5f934b068b1864eafa7995211b39eaddf76996045fe5",
    "go",
    17373,
    15657,
    300 * 1024**2,
)
UI = Artifact(
    "ui",
    "https://github.com/prometheus/prometheus/releases/download/v3.15.0/prometheus-web-ui-3.15.0.tar.gz",
    3343738,
    "fa8c918ed05e3f89e232e9b69eccd6ed074602cd9e8a2cab7a92bec9651974ae",
    "",
    18,
    18,
    16 * 1024**2,
    True,
)
CHECKSUMS = Artifact(
    "checksums",
    "https://github.com/prometheus/prometheus/releases/download/v3.15.0/sha256sums.txt",
    3725,
    "023cab1e6b275ee1b8f5f64215a01d74bbb1b19c45183b7296ced4aa4532707b",
    "",
    0,
    0,
    0,
    True,
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def opener() -> Any:
    return build_opener(
        ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()), NoRedirect()
    )


def validate_release_handoff(url: str, artifact_name: str) -> None:
    value = urlsplit(url)
    require(
        value.scheme == "https"
        and value.netloc == "release-assets.githubusercontent.com"
        and not value.fragment
        and len(url) <= 8192
        and all(32 < ord(c) < 127 for c in url),
        "release_handoff_authority",
    )
    paths = {
        "ui": "/github-production-release-asset/6838921/45b9efd2-fa57-4f55-951b-67f2ea9abb5d",
        "checksums": "/github-production-release-asset/6838921/db11dc7b-ce43-4aba-ba65-516523e5be1a",
    }
    require(
        artifact_name in paths and value.path == paths[artifact_name] and bool(value.query),
        "release_handoff_path",
    )


def acquire(artifact: Artifact, path: Path, deadline: float | None = None) -> dict[str, Any]:
    real_directory(path.parent)
    require(not path.exists() and not path.is_symlink(), "download_cache_collision")
    expected = {"source": SOURCE.url, "go": GO.url, "ui": UI.url, "checksums": CHECKSUMS.url}
    value = urlsplit(artifact.url)
    require(
        artifact.name in expected
        and artifact.url == expected[artifact.name]
        and value.scheme == "https"
        and value.username is None
        and value.password is None
        and value.port is None
        and not value.query
        and not value.fragment
        and artifact.release == (artifact.name in ("ui", "checksums")),
        "source_authority",
    )
    transport = opener()
    check_deadline(deadline)
    target = artifact.url
    handoff = False
    try:
        if artifact.release:
            try:
                initial = transport.open(
                    Request(target, headers={"User-Agent": "PulsePlate-source-qualification"}),
                    timeout=60,
                )
            except HTTPError as error:
                try:
                    require(
                        error.code == 302 and error.geturl() == artifact.url,
                        "release_initial_status",
                    )
                    locations = error.headers.get_all("Location", [])
                    require(len(locations) == 1, "release_location_count")
                    target = locations[0]
                    validate_release_handoff(target, artifact.name)
                    handoff = True
                finally:
                    error.close()
            else:
                initial.close()
                raise QualificationError("release_handoff_missing")
        with transport.open(
            Request(target, headers={"User-Agent": "PulsePlate-source-qualification"}), timeout=60
        ) as response:
            require(
                type(response.status) is int
                and response.status == 200
                and response.geturl() == target,
                "download_response",
            )
            length = response.headers.get("Content-Length")
            require(length is None or length == str(artifact.size), "download_content_length")
            digest, count = hashlib.sha256(), 0
            with path.open("xb") as output:
                while chunk := response.read(1024**2):
                    check_deadline(deadline)
                    count += len(chunk)
                    require(count <= artifact.size, "download_size")
                    digest.update(chunk)
                    output.write(chunk)
            require(
                count == artifact.size and digest.hexdigest() == artifact.digest,
                "download_integrity",
            )
    except QualificationError:
        raise
    except (HTTPError, URLError, TimeoutError, ssl.SSLError):
        raise QualificationError("source_transport_failed") from None
    return {
        "artifact": artifact.name,
        "public_source": artifact.url,
        "bytes": count,
        "sha256": digest.hexdigest(),
        "explicit_release_handoff": handoff,
        "final_redirects": 0,
    }


def extract(
    artifact: Artifact, archive: Path, destination: Path, deadline: float | None = None
) -> list[dict[str, Any]]:
    require(
        file_hash(archive) == artifact.digest and archive.stat().st_size == artifact.size,
        "archive_bytes",
    )
    require(
        not destination.exists() and not destination.is_symlink(), "extract_destination_collision"
    )
    rows: list[dict[str, Any]] = []
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        require(len(members) == artifact.members, "archive_member_count")
        seen: set[str] = set()
        files: set[str] = set()
        parents: set[str] = set()
        total = 0
        for member in members:
            check_deadline(deadline)
            name = member.name
            require(
                bool(name)
                and "\x00" not in name
                and "\\" not in name
                and not name.startswith("/")
                and all(part not in ("", ".", "..") for part in name.rstrip("/").split("/")),
                "archive_path",
            )
            require(member.isreg() or member.isdir(), "archive_member_type")
            require(member.mode in (0o644, 0o664, 0o755, 0o775), "archive_mode")
            parts = PurePosixPath(name.rstrip("/")).parts
            require(not artifact.root or parts[0] == artifact.root, "archive_root")
            relative = "/".join(parts[1:]) if artifact.root else "/".join(parts)
            require(relative not in seen, "archive_duplicate")
            seen.add(relative)
            require(bool(relative) or member.isdir(), "archive_root_type")
            if member.isreg():
                files.add(relative)
                total += member.size
                require(
                    0 <= member.size <= 64 * 1024**2 and total <= artifact.expanded,
                    "archive_expanded_size",
                )
                stream = source.extractfile(member)
                if stream is None:
                    raise QualificationError("archive_member_missing")
                data = stream.read(member.size + 1)
                require(len(data) == member.size, "archive_member_short")
                rows.append(
                    {
                        "path": relative,
                        "sha256": sha(data),
                        "size": member.size,
                        "git_mode": "100755" if member.mode & 0o111 else "100644",
                    }
                )
            if relative:
                parents.update(str(p) for p in PurePosixPath(relative).parents if str(p) != ".")
        require(
            len(rows) == artifact.files and not files.intersection(parents),
            "archive_file_directory_collision",
        )
        if artifact.name == "source":
            require(
                sha(
                    json.dumps(
                        sorted(rows, key=lambda r: r["path"]), sort_keys=True, separators=(",", ":")
                    ).encode()
                )
                == SOURCE_INVENTORY,
                "source_complete_git_inventory",
            )
        if artifact.name == "ui":
            require(
                {r["path"]: {"size": r["size"], "sha256": r["sha256"]} for r in rows} == UI_FILES,
                "UI_complete_inventory",
            )
        fresh_directory(destination, 0o755)
        for member in members:
            check_deadline(deadline)
            parts = PurePosixPath(member.name.rstrip("/")).parts
            relative = "/".join(parts[1:]) if artifact.root else "/".join(parts)
            if not relative:
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            real_directory(target.parent)
            if member.isdir():
                target.mkdir(exist_ok=True, mode=0o755)
            else:
                require(not target.exists() and not target.is_symlink(), "extract_output_collision")
                stream = source.extractfile(member)
                if stream is None:
                    raise QualificationError("extract_member_missing")
                with target.open("xb") as output:
                    shutil.copyfileobj(stream, output, 1024**2)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
    return sorted(rows, key=lambda row: row["path"])


def tree_inventory(
    root: Path, *, maximum: int = MAX_CACHE_BYTES, deadline: float | None = None
) -> list[dict[str, Any]]:
    real_directory(root)
    rows: list[dict[str, Any]] = []
    total = 0
    for path in sorted(root.rglob("*")):
        check_deadline(deadline)
        info = path.lstat()
        require(
            not stat.S_ISLNK(info.st_mode)
            and (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)),
            "unsafe_tree_member",
        )
        if stat.S_ISREG(info.st_mode):
            total += info.st_size
            require(total <= maximum and len(rows) < 250000, "tree_size_bound")
            rows.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size": info.st_size,
                    "mode": stat.S_IMODE(info.st_mode),
                    "sha256": file_hash(path, deadline),
                }
            )
    return rows


def stage_ui(source: Path, ui: Path, deadline: float | None = None) -> dict[str, Any]:
    template = source / "web/ui/embed.go.tmpl"
    require(file_hash(template) == EMBED_TEMPLATE, "embed_template")
    target_root = source / "web/ui/static"
    target_root.mkdir(exist_ok=True, mode=0o755)
    generated = []
    for relative, expected in sorted(UI_FILES.items()):
        check_deadline(deadline)
        raw = (ui / relative).read_bytes()
        require(
            sha(raw) == expected["sha256"] and len(raw) == expected["size"], "UI_asset_identity"
        )
        target = source / "web/ui" / (relative + ".gz")
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        real_directory(target.parent)
        with (
            target.open("xb") as stream,
            gzip.GzipFile(
                filename="", mode="wb", fileobj=stream, compresslevel=6, mtime=0
            ) as compressed,
        ):
            compressed.write(raw)
        target.chmod(0o644)
        data = target.read_bytes()
        require(
            data[3] == 0 and data[9] == 255 and gzip.decompress(data) == raw, "UI_gzip_roundtrip"
        )
        generated.append(relative + ".gz")
    embed = source / "web/ui/embed.go"
    with embed.open("xb") as stream:
        stream.write(
            template.read_bytes()
            + ("//go:embed " + " ".join(generated) + "\nvar EmbedFS embed.FS\n").encode()
        )
    embed.chmod(0o644)
    return {
        "generated_paths": generated,
        "embed_sha256": file_hash(embed),
        "python": sys.version,
        "gzip_source_sha256": file_hash(Path(gzip.__file__)),
        "zlib_build": zlib.ZLIB_VERSION,
        "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION,
        "algorithm": "Python GzipFile filename-empty mtime0 level6 OS255; not GNU gzip byte equality",
    }


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "duplicate_JSON_key")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise QualificationError("nonfinite_JSON")


def decode_objects(raw: bytes) -> list[dict[str, Any]]:
    require(0 < len(raw) <= MAX_NATIVE_OUTPUT, "native_JSON_size")
    text = raw.decode("utf-8", errors="strict")
    decoder = json.JSONDecoder(object_pairs_hook=unique_object, parse_constant=reject_constant)
    offset, objects = 0, []
    while offset < len(text):
        while offset < len(text) and text[offset] in " \r\n\t":
            offset += 1
        if offset == len(text):
            break
        value, offset = decoder.raw_decode(text, offset)
        require(isinstance(value, dict), "native_JSON_not_object")
        objects.append(value)
    require(bool(objects), "native_JSON_empty")
    return objects


def decode_modules(raw: bytes) -> list[dict[str, Any]]:
    objects = decode_objects(raw)
    seen = set()
    for value in objects:
        require(
            "Error" not in value
            and type(value.get("Path")) is str
            and bool(value["Path"])
            and type(value.get("Version")) is str
            and bool(value["Version"]),
            "native_module_error_or_identity",
        )
        identity = (value["Path"], value["Version"])
        require(identity not in seen, "duplicate_native_module")
        seen.add(identity)
    return objects


def decode_packages(raw: bytes, command: str) -> dict[str, Any]:
    require(command in ("prometheus", "promtool"), "package_command")
    packages: dict[str, dict[str, Any]] = {}
    for value in decode_objects(raw):
        require(isinstance(value, dict), "package_not_object")
        path = value.get("ImportPath")
        if type(path) is not str or not path or path in packages:
            raise QualificationError("package_identity")
        require(
            "Error" not in value
            and value.get("DepsErrors", []) == []
            and type(value.get("Incomplete", False)) is bool
            and not value.get("Incomplete", False),
            "package_error_or_incomplete",
        )
        imports = value.get("Imports", [])
        mapping = value.get("ImportMap", {})
        require(
            type(imports) is list
            and all(type(v) is str and bool(v) for v in imports)
            and isinstance(mapping, dict)
            and all(type(k) is str and type(v) is str for k, v in mapping.items()),
            "package_import_shape",
        )
        packages[path] = value
    root = ROOT_MODULE + "/cmd/" + command
    require(root in packages and packages[root].get("Name") == "main", "missing_root_command")
    for value in packages.values():
        mapping = value.get("ImportMap", {})
        require(
            all(mapping.get(path, path) in packages for path in value.get("Imports", [])),
            "missing_dependency_object",
        )
    ui = packages.get(ROOT_MODULE + "/web/ui")
    require(
        (command != "prometheus" and ui is None)
        or (
            ui is not None
            and sorted(ui.get("EmbedFiles", [])) == sorted(path + ".gz" for path in UI_FILES)
        ),
        "missing_matching_UI_embed_metadata",
    )
    return {
        "command": command,
        "package_count": len(packages),
        "package_paths": sorted(packages),
        "affected_package_path_observations": {path: path in packages for path in AFFECTED_PATHS},
        "module_objects": {
            path: value["Module"] for path, value in packages.items() if "Module" in value
        },
        "advisory_disposition": "pending independent source/call/config review and later actual binary cross-check",
    }


def clean_environment(
    home: Path, tmp: Path, cache: Path, modules: Path, *, offline: bool
) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "TMPDIR": str(tmp),
        "GOCACHE": str(cache),
        "GOMODCACHE": str(modules),
        "GOPATH": str(home / "gopath"),
        "GOOS": "linux",
        "GOARCH": "amd64",
        "CGO_ENABLED": "0",
        "GOTOOLCHAIN": "local",
        "GOWORK": "off",
        "GOENV": "off",
        "GOFLAGS": "-mod=readonly",
        "GOPROXY": "off" if offline else "https://proxy.golang.org",
        "GOSUMDB": "off" if offline else "sum.golang.org",
        "GOMAXPROCS": "2",
        "LANG": "C.UTF-8",
    }


def sandbox_arguments(
    docker: str,
    config: Path,
    image_id: str,
    name: str,
    owner: str,
    source: Path,
    go: Path,
    modules: Path,
) -> list[str]:
    environment = clean_environment(
        GUEST_TMP, GUEST_TMP, GUEST_TMP / "gocache", Path("/modules"), offline=True
    )
    argv = [
        docker,
        "--config",
        str(config),
        "create",
        "--pull",
        "never",
        "--name",
        name,
        "--label",
        LABEL + "=" + owner,
        "--platform",
        "linux/amd64",
        "--user",
        "65532:65532",
        "--workdir",
        "/src",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--cpus",
        "2",
        "--memory",
        "4g",
        "--pids-limit",
        "128",
        "--tmpfs",
        str(GUEST_TMP) + ":" + GUEST_TMPFS,
        "--entrypoint",
        "/usr/local/go/bin/go",
    ]
    for host, guest in ((source, "/src"), (go, "/usr/local/go"), (modules, "/modules")):
        real_directory(host)
        argv += ["--mount", f"type=bind,source={host},target={guest},readonly"]
    for key, value in environment.items():
        argv += ["--env", key + "=" + value]
    return argv + [image_id]


class Native:
    def __init__(self, evidence: Path, deadline: float, cleanup: int) -> None:
        self.evidence, self.deadline, self.cleanup = evidence, deadline, cleanup
        self.cleanup_deadline: float | None = None
        self.records: list[dict[str, Any]] = []

    def begin_cleanup(self) -> None:
        require(self.cleanup_deadline is None, "cleanup_deadline_already_started")
        self.cleanup_deadline = min(self.deadline + self.cleanup, time.monotonic() + self.cleanup)

    def run(
        self, argv: list[str], name: str, env: dict[str, str], *, cwd: Path, cleaning: bool = False
    ) -> bytes:
        require(Path(argv[0]).is_absolute(), "native_absolute_binary")
        stdout, stderr = self.evidence / (name + ".stdout"), self.evidence / (name + ".stderr")
        if cleaning:
            if self.cleanup_deadline is None:
                raise QualificationError("cleanup_deadline_not_started")
            cap = self.cleanup_deadline
        else:
            cap = self.deadline
        check_deadline(cap)
        code = None
        failure = None
        with stdout.open("xb") as output, stderr.open("xb") as error:
            process = subprocess.Popen(
                argv, cwd=cwd, env=env, stdout=output, stderr=error, start_new_session=True
            )  # nosec B603: # closed absolute verified native metadata argv, no shell, bounded owned group (remove-by: 2026-10-28, ref: PR-2477)
            try:
                while process.poll() is None:
                    require(
                        time.monotonic() < cap
                        and stdout.stat().st_size + stderr.stat().st_size <= MAX_NATIVE_OUTPUT,
                        "native_time_or_output_bound",
                    )
                    time.sleep(0.05)
                code = process.returncode
            except BaseException as caught:
                failure = type(caught).__name__
                if process.poll() is None:
                    require(os.getpgid(process.pid) == process.pid, "owned_native_group")
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                raise
            finally:
                self.records.append(
                    {
                        "argv": argv,
                        "environment": env,
                        "cwd": str(cwd),
                        "exit": code if code is not None else process.poll(),
                        "failure": failure,
                        "stdout": str(stdout),
                        "stderr": str(stderr),
                        "stdout_sha256": file_hash(stdout),
                        "stderr_sha256": file_hash(stderr),
                    }
                )
        require(
            stdout.stat().st_size + stderr.stat().st_size <= MAX_NATIVE_OUTPUT and code == 0,
            "native_failed",
        )
        return stdout.read_bytes()


def locks_unchanged(source: Path) -> None:
    require(
        all(file_hash(source / path) == digest for path, digest in LOCKS.items()),
        "source_lock_changed",
    )


def diagnostic_code(error: BaseException) -> str | None:
    if isinstance(error, QualificationError):
        value = str(error)
        if re.fullmatch(r"[A-Za-z0-9_]{1,96}", value):
            return value
    return None


def create_owned(
    native: Native,
    argv: list[str],
    name: str,
    expected: dict[str, Any],
    owned: dict[str, dict[str, Any]],
    label: str,
    env: dict[str, str],
    work: Path,
) -> None:
    owned[name] = expected
    native.run(argv, label + "-create", env, cwd=work)


def start_owned(
    native: Native,
    docker: str,
    config: Path,
    name: str,
    expected: dict[str, Any],
    label: str,
    env: dict[str, str],
    work: Path,
) -> tuple[bytes, dict[str, Any]]:
    raw = native.run(
        [docker, "--config", str(config), "start", "--attach", name],
        label + "-native",
        env,
        cwd=work,
    )
    actual = json.loads(
        native.run(
            [docker, "--config", str(config), "inspect", name],
            label + "-completed-inspect",
            env,
            cwd=work,
        )
    )[0]
    validate_container(actual, name, expected)
    state = actual["State"]
    require(
        state.get("Running") is False
        and type(state.get("ExitCode")) is int
        and state["ExitCode"] == 0
        and state.get("OOMKilled") is False,
        "container_native_completion",
    )
    return raw, state


def cleanup_owned(
    native: Native,
    docker: str,
    config: Path,
    owned: dict[str, dict[str, Any]],
    env: dict[str, str],
    work: Path,
) -> list[dict[str, Any]]:
    removals = []
    for name, expected in owned.items():
        try:
            inventory = (
                native.run(
                    [docker, "--config", str(config), "ps", "--all", "--format", "{{.Names}}"],
                    name + "-cleanup-inventory",
                    env,
                    cwd=work,
                    cleaning=True,
                )
                .decode()
                .splitlines()
            )
            if name not in inventory:
                removals.append(
                    {"name": name, "native_absent": True, "already_or_never_created": True}
                )
                continue
            actual = json.loads(
                native.run(
                    [docker, "--config", str(config), "inspect", name],
                    name + "-cleanup-inspect",
                    env,
                    cwd=work,
                    cleaning=True,
                )
            )[0]
            validate_container(actual, name, expected)
            native.run(
                [docker, "--config", str(config), "rm", "--force", name],
                name + "-cleanup-remove",
                env,
                cwd=work,
                cleaning=True,
            )
            inventory = (
                native.run(
                    [docker, "--config", str(config), "ps", "--all", "--format", "{{.Names}}"],
                    name + "-cleanup-absence",
                    env,
                    cwd=work,
                    cleaning=True,
                )
                .decode()
                .splitlines()
            )
            require(name not in inventory, "owned_container_survives")
            removals.append({"name": name, "native_absent": True})
        except BaseException as error:
            removals.append(
                {"name": name, "failure": type(error).__name__, "code": diagnostic_code(error)}
            )
    return removals


def qualify(work: Path, seconds: int, cleanup: int) -> dict[str, Any]:
    require(
        platform.system() == "Linux"
        and platform.machine() in ("x86_64", "amd64")
        and os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("RUNNER_OS") == "Linux",
        "hosted_linux_only",
    )
    require(
        type(seconds) is int and 0 < seconds <= 900 and type(cleanup) is int and 0 < cleanup <= 120,
        "qualification_budget",
    )
    global CLEANING
    fresh_directory(work)
    evidence = work / "evidence"
    fresh_directory(evidence)
    deadline = time.monotonic() + seconds
    native = Native(evidence, deadline, cleanup)
    report: dict[str, Any] = {
        "purpose": "Complete native package metadata only; no binary/source-build, selection, remediation, readiness or publication claim",
        "source_revision": REVISION,
        "source_tree": TREE,
        "heavy_build_invocations": 0,
        "publication_commands": 0,
        "automatic_retries": 0,
        "primary_advisory_references": [
            {"id": k, "raw_sha256": v, "review": "pending"} for k, v in ADVISORIES.items()
        ],
        "failure": None,
    }
    owned: dict[str, dict[str, Any]] = {}
    docker_path = shutil.which("docker")
    if docker_path is None:
        raise QualificationError("native_Docker_missing")
    docker = str(Path(docker_path).resolve())
    config = work / "docker-config"
    fresh_directory(config)
    docker_env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "DOCKER_CONFIG": str(config),
        "LANG": "C.UTF-8",
    }
    stage = "source_acquisition"
    try:
        downloads = work / "downloads"
        fresh_directory(downloads)
        report["acquisition"] = []
        for artifact in (SOURCE, GO, UI, CHECKSUMS):
            require(time.monotonic() < deadline, "qualification_deadline")
            stage = "acquire_" + artifact.name
            report["acquisition"].append(acquire(artifact, downloads / artifact.name, deadline))
        expected_row = UI.digest + "  prometheus-web-ui-3.15.0.tar.gz"
        require(
            (downloads / "checksums").read_text().splitlines().count(expected_row) == 1,
            "UI_checksum_row",
        )
        source, go, ui = work / "source", work / "go", work / "ui"
        for artifact, target in ((SOURCE, source), (GO, go), (UI, ui)):
            stage = "extract_" + artifact.name
            rows = extract(artifact, downloads / artifact.name, target, deadline)
            (evidence / (artifact.name + "-members.json")).write_text(
                json.dumps(rows, sort_keys=True, indent=2) + "\n"
            )
        require(
            (source / "VERSION").read_bytes() == b"3.15.0\n"
            and (go / "VERSION").read_bytes() == b"go1.27.2\ntime 2026-10-02T20:28:03Z\n",
            "source_VERSION",
        )
        require(
            file_hash(go / "LICENSE") == GO_LICENSE
            and all(file_hash(source / p) == v for p, v in SOURCE_LICENSES.items()),
            "source_licenses",
        )
        stage = "matching_UI_staging"
        report["UI_transform"] = stage_ui(source, ui, deadline)
        locks_unchanged(source)
        initial_source = tree_inventory(source, deadline=deadline)
        modules = work / "modules"
        fresh_directory(modules, 0o755)
        home, tmp, cache = work / "online-home", work / "online-tmp", work / "online-cache"
        for target in (home, tmp, cache):
            fresh_directory(target)
        online = clean_environment(home, tmp, cache, modules, offline=False)
        stage = "public_native_Go_prefetch"
        go_binary = str(go / "bin/go")
        require(
            native.run([go_binary, "version"], "online-go-version", online, cwd=source).decode()
            == GO_VERSION,
            "native_Go_version",
        )
        module_raw = native.run(
            [go_binary, "mod", "download", "-json"],
            "public-module-download",
            online,
            cwd=source,
        )
        report["native_module_objects"] = decode_modules(module_raw)
        locks_unchanged(source)
        native.run([go_binary, "mod", "verify"], "online-module-verify", online, cwd=source)
        locks_unchanged(source)
        for target in modules.rglob("*"):
            info = target.lstat()
            require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), "module_cache_member")
            target.chmod(0o555 if stat.S_ISDIR(info.st_mode) else 0o444)
        modules.chmod(0o555)
        module_inventory = tree_inventory(modules, deadline=deadline)
        require(bool(module_inventory), "empty_module_cache")
        (evidence / "module-cache-members.json").write_text(
            json.dumps(module_inventory, sort_keys=True, indent=2) + "\n"
        )
        before_names = (
            native.run(
                [docker, "--config", str(config), "ps", "--all", "--format", "{{.Names}}"],
                "containers-before",
                docker_env,
                cwd=work,
            )
            .decode()
            .splitlines()
        )
        native.run(
            [docker, "--config", str(config), "pull", "--platform", "linux/amd64", BASE],
            "public-base-pull",
            docker_env,
            cwd=work,
        )
        image = json.loads(
            native.run(
                [docker, "--config", str(config), "image", "inspect", BASE],
                "base-native-inspect",
                docker_env,
                cwd=work,
            )
        )[0]
        require(
            image["Os"] == "linux"
            and image["Architecture"] == "amd64"
            and BASE in image["RepoDigests"]
            and image["Id"] == BASE_CONFIG
            and not image["Config"].get("Volumes"),
            "base_native_identity",
        )
        report["runtime_base_native"] = image
        owner = uuid.uuid4().hex
        captures = [
            ("go-version", ["version"]),
            ("module-verify", ["mod", "verify"]),
            (
                "prometheus",
                ["list", "-deps", "-json", "-tags=netgo,builtinassets", "./cmd/prometheus"],
            ),
            ("promtool", ["list", "-deps", "-json", "-tags=netgo,builtinassets", "./cmd/promtool"]),
        ]
        observations = {}
        report["container_completion"] = {}
        for label, command in captures:
            name = "pp-prom-source-" + owner[:12] + "-" + label
            argv = (
                sandbox_arguments(docker, config, image["Id"], name, owner, source, go, modules)
                + command
            )
            require(name not in before_names, "owned_container_collision")
            expected_env = dict(v.split("=", 1) for v in image["Config"].get("Env", []))
            expected_env.update(
                clean_environment(
                    GUEST_TMP, GUEST_TMP, GUEST_TMP / "gocache", Path("/modules"), offline=True
                )
            )
            expected = {
                "image": image["Id"],
                "owner": owner,
                "command": command,
                "environment": expected_env,
                "mounts": {"/src": str(source), "/usr/local/go": str(go), "/modules": str(modules)},
            }
            stage = "offline_" + label
            create_owned(native, argv, name, expected, owned, label, docker_env, work)
            actual = json.loads(
                native.run(
                    [docker, "--config", str(config), "inspect", name],
                    label + "-inspect",
                    docker_env,
                    cwd=work,
                )
            )[0]
            validate_container(actual, name, expected)
            raw, completion = start_owned(
                native, docker, config, name, expected, label, docker_env, work
            )
            report["container_completion"][label] = completion
            if label == "go-version":
                require(raw.decode() == GO_VERSION, "sandbox_Go_version")
            elif label in ("prometheus", "promtool"):
                observations[label] = decode_packages(raw, label)
        require(set(observations) == {"prometheus", "promtool"}, "both_command_graphs_required")
        locks_unchanged(source)
        require(
            tree_inventory(source, deadline=deadline) == initial_source
            and tree_inventory(modules, deadline=deadline) == module_inventory,
            "readonly_inputs_changed",
        )
        report["command_observations"] = observations
        report["source_inventory_sha256"] = sha(json.dumps(initial_source, sort_keys=True).encode())
        report["module_inventory_sha256"] = sha(
            json.dumps(module_inventory, sort_keys=True).encode()
        )
        report["producer"] = {str(p): file_hash(p) for p in producer_paths()}
    except BaseException as error:
        report["failure"] = {
            "class": type(error).__name__,
            "code": diagnostic_code(error),
            "stage": stage,
        }
        raise
    finally:
        CLEANING = True
        try:
            native.begin_cleanup()
            removals = cleanup_owned(native, docker, config, owned, docker_env, work)
            report["cleanup"] = removals
            report["native_operations"] = native.records
            report["interruptions"] = list(INTERRUPTIONS)
            report["status"] = (
                "observed_package_metadata_only"
                if report["failure"] is None
                and not INTERRUPTIONS
                and not any("failure" in v for v in removals)
                else "failed_or_unknown"
            )
            (evidence / "qualification.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n"
            )
        finally:
            CLEANING = False
    require(report["status"] == "observed_package_metadata_only", "qualification_or_cleanup_failed")
    return report


def validate_container(actual: dict[str, Any], name: str, expected: dict[str, Any]) -> None:
    config, host = actual["Config"], actual["HostConfig"]
    require(
        actual["Name"] == "/" + name
        and actual["Image"] == expected["image"]
        and config["Labels"].get(LABEL) == expected["owner"],
        "container_identity",
    )
    require(
        config["User"] == "65532:65532"
        and config["WorkingDir"] == "/src"
        and config["Entrypoint"] == ["/usr/local/go/bin/go"]
        and config["Cmd"] == expected["command"],
        "container_command",
    )
    require(
        host["NetworkMode"] == "none"
        and host["ReadonlyRootfs"] is True
        and host["Privileged"] is False
        and host["NanoCpus"] == 2000000000
        and host["Memory"] == 4294967296
        and host["PidsLimit"] == 128,
        "container_isolation",
    )
    require(
        host["CapDrop"] == ["ALL"]
        and host.get("CapAdd") in (None, [])
        and host["SecurityOpt"] in (["no-new-privileges"], ["no-new-privileges:true"]),
        "container_capabilities",
    )
    mounts = {
        v["Destination"]: v["Source"]
        for v in actual["Mounts"]
        if v["Type"] == "bind" and v["RW"] is False
    }
    require(
        mounts == expected["mounts"]
        and len(actual["Mounts"]) == 3
        and host.get("Binds") in (None, []),
        "container_mounts",
    )
    require(host.get("Tmpfs") == {str(GUEST_TMP): GUEST_TMPFS}, "container_tmpfs")
    environment = dict(value.split("=", 1) for value in config["Env"])
    required_env = clean_environment(
        GUEST_TMP, GUEST_TMP, GUEST_TMP / "gocache", Path("/modules"), offline=True
    )
    require(
        all(environment.get(k) == v for k, v in required_env.items())
        and environment == expected["environment"],
        "container_environment",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--timeout-seconds", required=True, type=int)
    parser.add_argument("--cleanup-seconds", required=True, type=int)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    try:
        qualify(args.work_dir, args.timeout_seconds, args.cleanup_seconds)
    except (Exception, KeyboardInterrupt) as error:
        code = diagnostic_code(error)
        print(
            "Prometheus qualification failed: "
            + type(error).__name__
            + (":" + code if code else ""),
            file=sys.stderr,
        )
        return 1
    print("Prometheus package metadata captured; advisory and binary review pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
