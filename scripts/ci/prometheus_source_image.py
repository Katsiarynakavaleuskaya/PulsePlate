#!/usr/bin/env python3
"""The finite Prometheus source producer and its existing image consumers.

Go owns module semantics; Docker owns native layer application. The declared
recipe is data for one constructor, never a Dockerfile or arbitrary OCI
interpreter. Compilation is manual, hosted and bounded to the admitted pair.
Metadata, synthetic format observations and real candidate evidence are distinct.
"""

from __future__ import annotations

import argparse
import base64
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import selectors
import signal
import ssl
import stat
import subprocess  # nosec B404: # fixed native Go/Docker metadata commands require subprocess (remove-by: 2026-10-28, ref: PR-2477)
import sys
import tarfile
import time
from typing import Any, BinaryIO, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener
import uuid
import zipfile
import zlib

REVISION = "5241a27fe3c6983549fccc32f6e65917408c63cd"
TREE = "ffa0c7e9512071483f6c40a95aba9b97fbd86583"
GO_VERSION = "go version go1.27.2 linux/amd64\n"
BASE = "gcr.io/distroless/static-debian13@sha256:2293b36c7c9082bf4115aab724b4d2cddec82c8eba39bf27ac0517e159acf150"
BASE_CONFIG = "sha256:55a757dc8ab862a4eb634c434261dcd26f17c186b54f7bce845404a335456110"

# Exact acquired vendor graph, not a registry index or an arbitrary layer policy.
SOURCE_DATE_EPOCH = 1790321138
IMAGE_SCHEMA = "pulseplate.prometheus_image_manifest.v3"
IMAGE_REPOSITORY = "ghcr.io/katsiarynakavaleuskaya/pulseplate"
OCI_MANIFEST = "application/vnd.oci.image.manifest.v1+json"
OCI_CONFIG = "application/vnd.oci.image.config.v1+json"
OCI_LAYER = "application/vnd.oci.image.layer.v1.tar+gzip"
DERIVED_LOCKS = {
    "go.mod": "d85af091d5bf9ba19f98e4d92e24b368d3e5537af086521ef10c7dd669695fd7",
    "go.sum": "eaeb5e4f16a9edcab1aeeb2b1a90a0f85decbd0065b3bf63e03729d324f7fc1f",
}
DEFAULT_CONFIG_SHA256 = "aafcee2a237ad599327d07ed79e57ba1e57bdcf5a4bba6e3ba22eb09e25af479"
ORAS_REVISION = "db9e29505c3059f2b8fde34ae8cae266c5c765e9"
ORAS_TREE = "fa717b77576c315f859d3178977920f935533dee"
ORAS_SOURCE_INVENTORY = "69577a4027743fd734c33c678cdc62c93de4392e65a75e41d6f9f2d9c92c75b9"
ORAS_RAW_HEADERS = "6f59a7b473ab3f4a6e47c77169ae31258301c28d6c73192d1f692aa8ff180236"
ORAS_LICENSE = "eccb04b94c71454ea03f00ecb518b997952c4f2f23aca50baab98230f5c8dc00"
ORAS_LOCKS = {
    "go.mod": "02f8c886457ca22d404a2c0f8ce90a2d98cc42350bd08ab1bd43a91b6f13760f",
    "go.sum": "4f30ae58ea70de3be56e6befa2d9b737dc37379261fd812a8b51236a216d654f",
}
ORAS_COMMAND = "oras.land/oras/cmd/oras"
ORAS_METADATA = (
    "-X oras.land/oras/internal/version.Version=1.3.4 "
    "-X oras.land/oras/internal/version.GitCommit=" + ORAS_REVISION + " "
    "-X oras.land/oras/internal/version.BuildMetadata= "
    "-X oras.land/oras/internal/version.GitTreeState=clean"
)
PROMETHEUS_METADATA = (
    "-X github.com/prometheus/common/version.Version=3.15.0 "
    "-X github.com/prometheus/common/version.Revision=" + REVISION + " "
    "-X github.com/prometheus/common/version.Branch=HEAD "
    "-X github.com/prometheus/common/version.BuildUser=pulseplate "
    "-X github.com/prometheus/common/version.BuildDate=20260925-07:25:38"
)
BASE_LAYER_CONTRACTS: list[dict[str, Any]] = [
    {
        "descriptor": {
            "size": 124525,
            "digest": "sha256:2cc7ee286bf3a9e6af5f71756d7fc8e22e23ce65fec9047d774511ffcef79fa8",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:9486261b5a13f63ca6904b36721527ac8f19df53d300560138d69ae9b4c203de",
        "expanded": 491520,
        "members": 102,
        "inventory_sha256": "5354f3b705a681bdbdd9c2b69a894e0f56954ab3f420a50bfbd6aa4fb18fbf9e",
    },
    {
        "descriptor": {
            "size": 12675,
            "digest": "sha256:c172f21841dff4c8cf45cde46589c1c2616cefe7e819965e92e6d3475c428aa0",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:621c35e751a51a9a9dc3e80aa0b7fe8be2a93402ea6ccd307d30852cd7776cda",
        "expanded": 40960,
        "members": 17,
        "inventory_sha256": "6f3a3c9fc89cc96f1c51a98e5f0925c523f4bb6057fec51f39d59451f3bb63c3",
    },
    {
        "descriptor": {
            "size": 288057,
            "digest": "sha256:218cf840d0d95a86231eb9d33d26ac8a520a4299c6096cb70a0c2fb2a87c9e0a",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:763a77745f27b86cf26b97887b6842d83720e63b1c48848c0ba9ee54e351d63a",
        "expanded": 1157120,
        "members": 528,
        "inventory_sha256": "e66fb0f75e7ff8ae210c3789b509bb89634006d53ae9e8b0681c21a32c2d81be",
    },
    {
        "descriptor": {
            "size": 254668,
            "digest": "sha256:f6069939f718601b38d25ec5ed5631ed047e4da24acec2e252f8f29d251be718",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:f0d0eff4c2312a7bd6e21797bdfea5eb35f60e76b555ce2b22794424af2cad36",
        "expanded": 1331200,
        "members": 761,
        "inventory_sha256": "355355459c8f97843266dfc9af93a9b7d3772dac464b73432613912f725fd644",
    },
    {
        "descriptor": {
            "size": 32093,
            "digest": "sha256:d6b1b89eccacc15c2420b2776d72c1dae334a00805ed9af54bf2f71e4d536f28",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:275a30dd8ce958b21daa9ad962c6fbc09f98306ee2f486b65c9075dc257b1412",
        "expanded": 102400,
        "members": 17,
        "inventory_sha256": "19cce3cc56c3a63abfe14f9a31a51c2f5b9a5c52b38a7c8234c4d3e62c0a0701",
    },
    {
        "descriptor": {
            "size": 67,
            "digest": "sha256:2780920e5dbfbe103d03a583ed75345306e572ec5a48cb10361f046767d9f29a",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:4d049f83d9cf21d1f5cc0e11deaf36df02790d0e60c1a3829538fb4b61685368",
        "expanded": 1536,
        "members": 1,
        "inventory_sha256": "b405415ec34e6efa906c1c4e58460fc1aee3ed44c30c2fe4690a847ccedb8df8",
    },
    {
        "descriptor": {
            "size": 188,
            "digest": "sha256:7c12895b777bcaa8ccae0605b4de635b68fc32d60fa08f421dc3818bf55ee212",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:af5aa97ebe6ce1604747ec1e21af7136ded391bcabe4acef882e718a87c86bcc",
        "expanded": 2560,
        "members": 2,
        "inventory_sha256": "84b6b049b5ebabbfc9550909a1cb652795bbe444725387ff47ab1ba26590b5ab",
    },
    {
        "descriptor": {
            "size": 123,
            "digest": "sha256:3214acf345c0cc6bbdb56b698a41ccdefc624a09d6beb0d38b5de0b2303ecaf4",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:6f1cdceb6a3146f0ccb986521156bef8a422cdbb0863396f7f751f575ba308f4",
        "expanded": 2560,
        "members": 3,
        "inventory_sha256": "d814686c93c24fd85eec8c12aa3aedb03f5eca52f8936a9f8e2dfe815c8a893f",
    },
    {
        "descriptor": {
            "size": 162,
            "digest": "sha256:52630fc75a18675c530ed9eba5f55eca09b03e91bd5bc15307918bbc1a7e7296",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:bd3cdfae1d3fdd83a2231d608969b38b82349777c2fff9a7c12d54f8ac5c9b38",
        "expanded": 2560,
        "members": 2,
        "inventory_sha256": "b56bbd4d385ce7a38ae96b3ac9d5c894b9b2d1a7e81cb751c318d127fd26c809",
    },
    {
        "descriptor": {
            "size": 80,
            "digest": "sha256:dd64bf2dd177757451a98fcdc999a339c35dee5d9872d8f4dc69c8f3c4dd0112",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:4cde6b0bb6f50a5f255eef7b2a42162c661cf776b803225dcac9a659e396bb6b",
        "expanded": 1536,
        "members": 1,
        "inventory_sha256": "52718246e6fcb9b4e631cfd4b581bc299afb4ae98589b6a6d1f932c7c1c2d9f6",
    },
    {
        "descriptor": {
            "size": 351,
            "digest": "sha256:b839dfae01f66e15c6a8b63520557ed315bdfe036342fa7a0c537259f10d7a9a",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:ad51d0769d16ba578106a177987dfe3d2e02c1668c852b795b2f6b024068242a",
        "expanded": 2048,
        "members": 1,
        "inventory_sha256": "8a452647660cfe3e5a620f3fdb7ee33334bbe8a0aa5f04a2f54cc2cbcd583b93",
    },
    {
        "descriptor": {
            "size": 311,
            "digest": "sha256:ebddc55facdc6b1f7e0f30816a5fc7cc62f38abdf76c0a8b0a0ce52085754795",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:187cfc6d1e3e8a40a5e64653bcd3239c140807dcf1c09e48021178705a5a6139",
        "expanded": 3072,
        "members": 3,
        "inventory_sha256": "6869ca4e9b4c88ef56f14fcd7afc596d2a6550da6577b580fc4a0f3b0f100cbc",
    },
    {
        "descriptor": {
            "size": 143338,
            "digest": "sha256:c4bc6f35ff5e25aa1afe7a148a0b6f10a760f54e298f86a4a4d44b91f1afbfab",
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        },
        "diff_id": "sha256:f2392a9484bf6b18f06beaf705b994e31dbb2716c99cf7d03c9c495cd107f364",
        "expanded": 276480,
        "members": 15,
        "inventory_sha256": "31d48342ff6ca53acaa34c50f6cf4721f1a3b9276e073ef41dffecca5ed51b90",
    },
]
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
MAX_COMPILE_OUTPUT_BYTES = 4 * 1024**3
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

ORAS_SOURCE = Artifact(
    "oras-source",
    "https://codeload.github.com/oras-project/oras/tar.gz/" + ORAS_REVISION,
    406029,
    "df21c91ff25c13b9c5c5d26b43dd3830fb978c9a93605f641d1e4d25a871b1ee",
    "oras-" + ORAS_REVISION,
    507,
    411,
    4 * 1024**2,
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
    expected = {
        "source": SOURCE.url,
        "go": GO.url,
        "ui": UI.url,
        "checksums": CHECKSUMS.url,
        "oras-source": ORAS_SOURCE.url,
    }
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
        if artifact.name == "oras-source":
            require(
                sha(canonical_data(sorted(rows, key=lambda row: row["path"])))
                == ORAS_SOURCE_INVENTORY,
                "oras_complete_git_inventory",
            )
            headers = [
                {
                    "path": member.name,
                    "type": member.type.decode("ascii"),
                    "mode": member.mode,
                    "size": member.size,
                    "linkname": member.linkname,
                }
                for member in members
            ]
            require(
                sha(canonical_data(headers)) == ORAS_RAW_HEADERS, "oras_raw_archive_modes_inventory"
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
    output: Path | None = None,
) -> list[str]:
    environment = clean_environment(
        GUEST_TMP, GUEST_TMP, GUEST_TMP / "gocache", Path("/modules"), offline=True
    )
    if output is not None:
        environment.update(TMPDIR="/output/tmp", GOCACHE="/output/cache")
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
    if output is not None:
        real_directory(output)
        argv += ["--mount", f"type=bind,source={output},target=/output"]
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
        self,
        argv: list[str],
        name: str,
        env: dict[str, str],
        *,
        cwd: Path,
        cleaning: bool = False,
        maximum_seconds: int | None = None,
        output_bound: int = MAX_NATIVE_OUTPUT,
        watched_output: Path | None = None,
    ) -> bytes:
        require(Path(argv[0]).is_absolute(), "native_absolute_binary")
        stdout, stderr = self.evidence / (name + ".stdout"), self.evidence / (name + ".stderr")
        if cleaning:
            if self.cleanup_deadline is None:
                raise QualificationError("cleanup_deadline_not_started")
            cap = self.cleanup_deadline
        else:
            cap = self.deadline
        if maximum_seconds is not None:
            require(type(maximum_seconds) is int and maximum_seconds > 0, "native_subdeadline")
            cap = min(cap, time.monotonic() + maximum_seconds)
        check_deadline(cap)
        require(
            type(output_bound) is int and 0 < output_bound <= 512 * 1024**2, "native_output_limit"
        )
        code = None
        failure = None
        with stdout.open("xb") as output, stderr.open("xb") as error:
            process = subprocess.Popen(
                argv, cwd=cwd, env=env, stdout=output, stderr=error, start_new_session=True
            )  # nosec B603: # closed absolute verified native metadata argv, no shell, bounded owned group (remove-by: 2026-10-28, ref: PR-2477)
            try:
                next_inventory = 0.0
                while process.poll() is None:
                    require(
                        time.monotonic() < cap
                        and stdout.stat().st_size + stderr.stat().st_size <= output_bound,
                        "native_time_or_output_bound",
                    )
                    if watched_output is not None and time.monotonic() >= next_inventory:
                        total, count = 0, 0
                        for path in watched_output.rglob("*"):
                            try:
                                info = path.lstat()
                            except FileNotFoundError:
                                # This one owned Go output tree is changing while observed.
                                continue
                            require(
                                stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode),
                                "compiler_output_member",
                            )
                            total += info.st_size if stat.S_ISREG(info.st_mode) else 0
                            count += 1
                            require(
                                total <= MAX_COMPILE_OUTPUT_BYTES and count <= 250000,
                                "compiler_output_byte_or_member_bound",
                            )
                        require(
                            shutil.disk_usage(watched_output).free >= 512 * 1024**2,
                            "compiler_filesystem_free_reserve_HOLD",
                        )
                        next_inventory = time.monotonic() + 5
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
            stdout.stat().st_size + stderr.stat().st_size <= output_bound and code == 0,
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
    *,
    cleaning: bool = True,
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
                    cleaning=cleaning,
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
                    cleaning=cleaning,
                )
            )[0]
            validate_container(actual, name, expected)
            native.run(
                [docker, "--config", str(config), "rm", "--force", name],
                name + "-cleanup-remove",
                env,
                cwd=work,
                cleaning=cleaning,
            )
            inventory = (
                native.run(
                    [docker, "--config", str(config), "ps", "--all", "--format", "{{.Names}}"],
                    name + "-cleanup-absence",
                    env,
                    cwd=work,
                    cleaning=cleaning,
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


def decode_selected_modules(
    raw: bytes, *, root_module: str = ROOT_MODULE
) -> dict[str, dict[str, Any]]:
    """Full native list objects; Main has different identity from download rows."""
    result: dict[str, dict[str, Any]] = {}
    require(
        root_module in (ROOT_MODULE, "oras.land/oras", "pulseplate.local/caddy-build"),
        "finite_selected_module_root",
    )
    roots = 0
    for value in decode_objects(raw):
        path = value.get("Path")
        if type(path) is not str or not path or path in result or "Error" in value:
            raise QualificationError("selected_module_identity_or_error")
        require("Main" not in value or type(value["Main"]) is bool, "selected_module_Main_type")
        if value.get("Main") is True:
            roots += 1
            require(path == root_module, "selected_module_root")
            require(
                "Version" not in value or type(value["Version"]) is str,
                "selected_root_version_type",
            )
        else:
            require(
                type(value.get("Version")) is str and bool(value["Version"]),
                "selected_module_version",
            )
        if "Replace" in value:
            replacement = value["Replace"]
            require(
                type(replacement) is dict
                and "Error" not in replacement
                and type(replacement.get("Path")) is str
                and bool(replacement["Path"]),
                "selected_replacement_identity_or_error",
            )
            require(
                "Version" not in replacement
                or (type(replacement["Version"]) is str and bool(replacement["Version"])),
                "selected_replacement_version_type",
            )
        result[path] = value
    require(roots == 1, "exact_one_selected_Main")
    return result


def replay_coordinates(
    value: dict[str, Any], source: Path, modules: Path, *, download: bool
) -> dict[str, Any]:
    """Only named native coordinate fields; retain all raw objects separately."""
    from copy import deepcopy

    result = deepcopy(value)
    roots = ((str(source), "source"), (str(modules), "modules"))

    def coordinates(obj: dict[str, Any], fields: tuple[str, ...]) -> None:
        for field in fields:
            if field not in obj:
                continue
            raw = obj[field]
            require(
                type(raw) is str
                and bool(raw)
                and raw.startswith("/")
                and str(PurePosixPath(raw)) == raw
                and ".." not in PurePosixPath(raw).parts,
                "unsupported_native_coordinate",
            )
            matches = [
                (root, role) for root, role in roots if raw == root or raw.startswith(root + "/")
            ]
            require(len(matches) == 1, "unbound_native_coordinate")
            root, role = matches[0]
            obj[field] = {"owned_root_role": role, "relative_suffix": raw[len(root) :]}

    coordinates(result, ("Dir", "Info", "GoMod", "Zip") if download else ("Dir", "GoMod"))
    if "Replace" in result:
        require(type(result["Replace"]) is dict, "native_Replace_shape")
        coordinates(result["Replace"], ("Dir", "GoMod"))
    return result


def _derivation_locks(source: Path) -> dict[str, bytes]:
    result = {}
    for name in LOCKS:
        digest = file_hash(source / name)
        raw = (source / name).read_bytes()
        require(sha(raw) == digest, "derivation_lock_read_changed")
        result[name] = raw
    return result


def _derivation_nonlocks(source: Path, deadline: float) -> list[dict[str, Any]]:
    return [row for row in tree_inventory(source, deadline=deadline) if row["path"] not in LOCKS]


def _derivation_guard(
    source: Path,
    expected: dict[str, bytes],
    remainder: list[dict[str, Any]],
    go: Path,
    go_hash: str,
    deadline: float,
) -> None:
    require(_derivation_locks(source) == expected, "frozen_derivation_locks_changed")
    require(
        _derivation_nonlocks(source, deadline) == remainder, "derivation_nonlock_source_changed"
    )
    require(file_hash(go / "bin/go", deadline) == go_hash, "derivation_Go_binary_changed")


def _derivation_phase(
    native: Native,
    source: Path,
    go: Path,
    modules: Path,
    environment: dict[str, str],
    label: str,
    expected: dict[str, bytes],
    remainder: list[dict[str, Any]],
    go_hash: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    commands = (
        ("version", ["version"]),
        ("edit", ["mod", "edit", "-json"]),
        ("download", ["mod", "download", "-json"]),
        ("verify", ["mod", "verify"]),
        ("selected", ["list", "-m", "-json", "all"]),
        ("graph", ["mod", "graph"]),
    )
    # Observe full selected objects after readonly acquisition so pre-get cache
    # hydration cannot masquerade as get-produced module metadata transitions.
    for key, command in commands:
        _derivation_guard(source, expected, remainder, go, go_hash, native.deadline)
        raw = native.run([str(go / "bin/go"), *command], label + "-" + key, environment, cwd=source)
        _derivation_guard(source, expected, remainder, go, go_hash, native.deadline)
        if key == "version":
            require(raw.decode() == GO_VERSION, "derivation_native_Go_version")
        elif key == "edit":
            objects = decode_objects(raw)
            require(
                len(objects) == 1
                and "Error" not in objects[0]
                and type(objects[0].get("Module")) is dict
                and objects[0]["Module"].get("Path") == ROOT_MODULE,
                "native_mod_edit_identity",
            )
            result[key] = objects[0]
        elif key == "selected":
            result[key] = decode_selected_modules(raw)
        elif key == "download":
            result[key] = decode_modules(raw)
        else:
            result[key] = raw.decode("utf-8", errors="strict")
    require(bool(result["graph"]), "empty_native_module_graph")
    return result


def _derivation_comparison(phase: dict[str, Any], source: Path, modules: Path) -> dict[str, Any]:
    return {
        "edit": phase["edit"],
        "selected": {
            key: replay_coordinates(value, source, modules, download=False)
            for key, value in phase["selected"].items()
        },
        "download": sorted(
            (
                replay_coordinates(value, source, modules, download=True)
                for value in phase["download"]
            ),
            key=lambda value: (value["Path"], value["Version"]),
        ),
        "graph_complete_line_multiset": sorted(phase["graph"].splitlines(keepends=True)),
        "verify": phase["verify"],
    }


def _derivation_offline(
    native: Native,
    source: Path,
    go: Path,
    modules: Path,
    expected_locks: dict[str, bytes],
    remainder: list[dict[str, Any]],
    go_hash: str,
    label: str,
    docker: str,
    config: Path,
    image: dict[str, Any],
    owner: str,
    before_names: list[str],
    owned: dict[str, dict[str, Any]],
    docker_env: dict[str, str],
    work: Path,
) -> dict[str, Any]:
    for path in modules.rglob("*"):
        check_deadline(native.deadline)
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), "module_cache_member")
        path.chmod(0o555 if stat.S_ISDIR(info.st_mode) else 0o444)
    modules.chmod(0o555)
    cache = tree_inventory(modules, deadline=native.deadline)
    require(bool(cache), "empty_module_cache")
    (native.evidence / (label + "-module-cache-members.json")).write_text(
        json.dumps(cache, sort_keys=True) + "\n"
    )
    observations: dict[str, Any] = {}
    full_packages: dict[str, Any] = {}
    completions: dict[str, Any] = {}
    for command_name, command in (
        ("version", ["version"]),
        ("verify", ["mod", "verify"]),
        ("prometheus", ["list", "-deps", "-json", "-tags=netgo,builtinassets", "./cmd/prometheus"]),
        ("promtool", ["list", "-deps", "-json", "-tags=netgo,builtinassets", "./cmd/promtool"]),
    ):
        _derivation_guard(source, expected_locks, remainder, go, go_hash, native.deadline)
        require(
            tree_inventory(modules, deadline=native.deadline) == cache,
            "readonly_derivation_cache_changed",
        )
        stage = label + "-offline-" + command_name
        name = "pp-prom-derive-" + owner[:12] + "-" + label + "-" + command_name
        argv = (
            sandbox_arguments(docker, config, image["Id"], name, owner, source, go, modules)
            + command
        )
        require(name not in before_names, "owned_container_collision")
        environment = dict(value.split("=", 1) for value in image["Config"].get("Env", []))
        environment.update(
            clean_environment(
                GUEST_TMP, GUEST_TMP, GUEST_TMP / "gocache", Path("/modules"), offline=True
            )
        )
        expected = {
            "image": image["Id"],
            "owner": owner,
            "command": command,
            "environment": environment,
            "mounts": {"/src": str(source), "/usr/local/go": str(go), "/modules": str(modules)},
        }
        create_owned(native, argv, name, expected, owned, stage, docker_env, work)
        actual = json.loads(
            native.run(
                [docker, "--config", str(config), "inspect", name],
                stage + "-inspect",
                docker_env,
                cwd=work,
            )
        )[0]
        validate_container(actual, name, expected)
        raw, completed = start_owned(
            native, docker, config, name, expected, stage, docker_env, work
        )
        completions[command_name] = completed
        _derivation_guard(source, expected_locks, remainder, go, go_hash, native.deadline)
        require(
            tree_inventory(modules, deadline=native.deadline) == cache,
            "readonly_derivation_cache_changed",
        )
        if command_name == "version":
            require(raw.decode() == GO_VERSION, "sandbox_Go_version")
        elif command_name in ("prometheus", "promtool"):
            observations[command_name] = decode_packages(raw, command_name)
            full_packages[command_name] = {
                value["ImportPath"]: value for value in decode_objects(raw)
            }
    require(set(observations) == {"prometheus", "promtool"}, "both_command_graphs_required")
    return {
        "command_observations": observations,
        "full_native_package_objects": full_packages,
        "container_completion": completions,
        "module_inventory_sha256": sha(json.dumps(cache, sort_keys=True).encode()),
    }


def derive_xnet060_observe(
    native: Native,
    work: Path,
    downloads: Path,
    source_a: Path,
    go: Path,
    ui: Path,
    owned: dict[str, dict[str, Any]],
    docker: str,
    config: Path,
    docker_env: dict[str, str],
    report: dict[str, Any],
) -> None:
    """Exactly two original-source fixed-get replays inside this existing Native lease."""
    import difflib

    owner = uuid.uuid4().hex
    before_names = (
        native.run(
            [docker, "--config", str(config), "ps", "--all", "--format", "{{.Names}}"],
            "derive-containers-before",
            docker_env,
            cwd=work,
        )
        .decode()
        .splitlines()
    )
    native.run(
        [docker, "--config", str(config), "pull", "--platform", "linux/amd64", BASE],
        "derive-base-pull",
        docker_env,
        cwd=work,
    )
    image = json.loads(
        native.run(
            [docker, "--config", str(config), "image", "inspect", BASE],
            "derive-base-inspect",
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
    report["module_action"] = "xnet060-replay"
    report["module_derivation"] = {"authored_action": "golang.org/x/net@v0.60.0", "replays": []}
    go_hash = file_hash(go / "bin/go", native.deadline)
    original_remainder = _derivation_nonlocks(source_a, native.deadline)
    prior: dict[str, Any] | None = None
    for label in ("a", "b"):
        report["derivation_stage"] = label + "-original-source"
        source = source_a if label == "a" else work / "source-b"
        if label == "b":
            rows = extract(SOURCE, downloads / SOURCE.name, source, native.deadline)
            (native.evidence / "source-b-members.json").write_text(
                json.dumps(rows, sort_keys=True) + "\n"
            )
            require(
                stage_ui(source, ui, native.deadline) == report["UI_transform"],
                "matching_replay_UI",
            )
        locks_unchanged(source)
        require(
            _derivation_nonlocks(source, native.deadline) == original_remainder,
            "replay_original_nonlocks",
        )
        area = work / ("replay-" + label)
        fresh_directory(area)
        home, tmp, cache, modules = (area / name for name in ("home", "tmp", "gocache", "modules"))
        for target in (home, tmp, cache, modules):
            fresh_directory(target, 0o755 if target == modules else 0o700)
        online = clean_environment(home, tmp, cache, modules, offline=False)
        original = _derivation_locks(source)
        for name, raw in original.items():
            (native.evidence / (label + "-original-" + name)).write_bytes(raw)
        report["derivation_stage"] = label + "-base-readonly"
        before = _derivation_phase(
            native,
            source,
            go,
            modules,
            online,
            label + "-base",
            original,
            original_remainder,
            go_hash,
        )
        old = before["selected"].get("golang.org/x/net")
        require(
            old is not None and old["Version"] == "v0.58.0" and "Replace" not in old,
            "original_xnet_identity",
        )
        writable = dict(online, GOFLAGS="")
        report["derivation_stage"] = label + "-sole-fixed-get"
        try:
            native.run(
                [str(go / "bin/go"), "get", "golang.org/x/net@v0.60.0"],
                label + "-sole-get",
                writable,
                cwd=source,
            )
        except BaseException:
            for name, raw in _derivation_locks(source).items():
                (native.evidence / (label + "-failed-get-" + name)).write_bytes(raw)
            raise
        # Freeze exactly ONCE, immediately after successful get. Never after download.
        derived = _derivation_locks(source)
        require(derived != original, "empty_authored_module_delta")
        for name, raw in derived.items():
            (native.evidence / (label + "-derived-" + name)).write_bytes(raw)
        (native.evidence / (label + "-postget-source-members.json")).write_text(
            json.dumps(tree_inventory(source, deadline=native.deadline), sort_keys=True) + "\n"
        )
        _derivation_guard(source, derived, original_remainder, go, go_hash, native.deadline)
        patch = b"".join(
            b"".join(
                difflib.diff_bytes(
                    difflib.unified_diff,
                    original[name].splitlines(keepends=True),
                    derived[name].splitlines(keepends=True),
                    fromfile=("a/" + name).encode(),
                    tofile=("b/" + name).encode(),
                )
            )
            for name in LOCKS
        )
        (native.evidence / (label + "-module-derivation.patch")).write_bytes(patch)
        report["derivation_stage"] = label + "-derived-readonly"
        after = _derivation_phase(
            native,
            source,
            go,
            modules,
            online,
            label + "-derived",
            derived,
            original_remainder,
            go_hash,
        )
        selected = after["selected"].get("golang.org/x/net")
        require(
            selected is not None and selected["Version"] == "v0.60.0" and "Replace" not in selected,
            "derived_xnet_identity",
        )
        transitions = [
            {
                "Path": path,
                "before": before["selected"].get(path),
                "after": after["selected"].get(path),
                "class": (
                    "I_R"
                    if path == "golang.org/x/net"
                    else "C_R_candidate_pending_independent_review"
                ),
            }
            for path in sorted(set(before["selected"]) | set(after["selected"]))
            if before["selected"].get(path) != after["selected"].get(path)
        ]
        report["derivation_stage"] = label + "-offline-both-commands"
        offline = _derivation_offline(
            native,
            source,
            go,
            modules,
            derived,
            original_remainder,
            go_hash,
            label,
            docker,
            config,
            image,
            owner,
            before_names,
            owned,
            docker_env,
            work,
        )
        record = {
            "replay": label,
            "original_locks": {name: sha(raw) for name, raw in original.items()},
            "derived_locks": {name: sha(raw) for name, raw in derived.items()},
            "patch_sha256": sha(patch),
            "before": before,
            "after": after,
            "complete_module_transitions": transitions,
            "native_directives_before": before["edit"],
            "native_directives_after": after["edit"],
            "offline": offline,
            "nonlock_source_inventory_sha256": sha(
                json.dumps(original_remainder, sort_keys=True).encode()
            ),
        }
        report["module_derivation"]["replays"].append(record)
        comparison = {
            "original": original,
            "derived": derived,
            "patch": patch,
            "before": _derivation_comparison(before, source, modules),
            "after": _derivation_comparison(after, source, modules),
            "full_native_package_objects": offline["full_native_package_objects"],
            "nonlock_source": original_remainder,
        }
        if prior is not None:
            require(comparison == prior, "independent_derivation_replay_mismatch")
        prior = comparison
    require(
        len(report["module_derivation"]["replays"]) == 2, "two_complete_derivation_replays_required"
    )
    report["module_derivation"][
        "replay_equality"
    ] = "observed_under_explicit_coordinate_correspondence_only"
    report["module_derivation"][
        "closure_disposition"
    ] = "pending independent complete delta/fullF review; metadata only"


def qualify(
    work: Path, seconds: int, cleanup: int, *, derive_xnet060: bool = False
) -> dict[str, Any]:
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
        if derive_xnet060:
            stage = "xnet060_replay"
            derive_xnet060_observe(
                native, work, downloads, source, go, ui, owned, docker, config, docker_env, report
            )
        else:
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
                require(
                    stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), "module_cache_member"
                )
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
                (
                    "promtool",
                    ["list", "-deps", "-json", "-tags=netgo,builtinassets", "./cmd/promtool"],
                ),
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
                    "mounts": {
                        "/src": str(source),
                        "/usr/local/go": str(go),
                        "/modules": str(modules),
                    },
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
            report["source_inventory_sha256"] = sha(
                json.dumps(initial_source, sort_keys=True).encode()
            )
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
        and len(actual["Mounts"]) == (4 if "output" in expected else 3)
        and host.get("Binds") in (None, []),
        "container_mounts",
    )
    if "output" in expected:
        writable = [v for v in actual["Mounts"] if v["Type"] == "bind" and v["RW"] is True]
        require(
            len(writable) == 1
            and writable[0]["Destination"] == "/output"
            and writable[0]["Source"] == expected["output"],
            "container_finite_output_mount",
        )
    require(host.get("Tmpfs") == {str(GUEST_TMP): GUEST_TMPFS}, "container_tmpfs")
    environment = dict(value.split("=", 1) for value in config["Env"])
    required_env = clean_environment(
        GUEST_TMP, GUEST_TMP, GUEST_TMP / "gocache", Path("/modules"), offline=True
    )
    if "output" in expected:
        required_env.update(TMPDIR="/output/tmp", GOCACHE="/output/cache")
    require(
        all(environment.get(k) == v for k, v in required_env.items())
        and environment == expected["environment"],
        "container_environment",
    )


# Preparation only. No authenticated invocation or native-format parity claim.
GHCR_REPOSITORY = "Katsiarynakavaleuskaya/PulsePlate"
GHCR_OWNER = "Katsiarynakavaleuskaya"
GHCR_PACKAGE = "pulseplate"
GHCR_REQUESTS = (
    "/repos/Katsiarynakavaleuskaya/PulsePlate",
    "/users/Katsiarynakavaleuskaya/packages/container/pulseplate",
)
GHCR_OUTPUT_LIMIT = 1024**2


def ghcr_response(raw: bytes) -> tuple[int, dict[str, Any]]:
    """Consume one bounded native --include response; never publish its fields wholesale."""
    require(0 < len(raw) <= GHCR_OUTPUT_LIMIT, "GHCR_response_size")
    header, separator, body = raw.partition(b"\r\n\r\n")
    require(bool(separator) and len(header) <= 32768, "GHCR_HTTP_header")
    status_line, status_lf, fields = header.partition(b"\n")
    require(status_lf == b"\n" and b"\r" not in status_line, "GHCR_HTTP_status")
    require(bool(fields), "GHCR_HTTP_header")
    lines = fields.split(b"\r\n")
    match = re.fullmatch(rb"HTTP/(?:1\.1|2(?:\.0)?) ([1-5][0-9]{2})(?: [\x20-\x7e]+)?", status_line)
    if match is None:
        raise QualificationError("GHCR_HTTP_status")
    status_code = int(match.group(1))
    require(
        all(re.fullmatch(rb"[A-Za-z0-9!#$%&'*+.^_`|~-]+: [\x20-\x7e]*", line) for line in lines),
        "GHCR_HTTP_header",
    )
    require(status_code == 200, "GHCR_HTTP_status_" + str(status_code))
    value = json.loads(
        body.decode("utf-8", errors="strict"),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )
    require(type(value) is dict, "GHCR_JSON_not_object")
    return status_code, value


def ghcr_identity(repository: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
    def positive(value: Any) -> int:
        if type(value) is not int or value <= 0:
            raise QualificationError("GHCR_positive_ID")
        return value

    def expected(value: Any, literal: str) -> None:
        require(
            type(value) is str and value.isascii() and value.lower() == literal.lower(),
            "GHCR_expected_identity",
        )

    repo_owner = repository.get("owner")
    package_owner, linked_repository = package.get("owner"), package.get("repository")
    if type(repo_owner) is not dict:
        raise QualificationError("GHCR_identity_objects")
    if type(package_owner) is not dict:
        raise QualificationError("GHCR_identity_objects")
    if type(linked_repository) is not dict:
        raise QualificationError("GHCR_identity_objects")
    repo_id, owner_id, package_id = (
        positive(repository.get("id")),
        positive(repo_owner.get("id")),
        positive(package.get("id")),
    )
    expected(repository.get("full_name"), GHCR_REPOSITORY)
    expected(repo_owner.get("login"), GHCR_OWNER)
    expected(package_owner.get("login"), GHCR_OWNER)
    expected(linked_repository.get("full_name"), GHCR_REPOSITORY)
    require(
        positive(package_owner.get("id")) == owner_id
        and positive(linked_repository.get("id")) == repo_id,
        "GHCR_cross_ID",
    )
    require(
        package.get("name") == GHCR_PACKAGE
        and package.get("package_type") == "container"
        and package.get("visibility") == "public",
        "GHCR_package_properties",
    )
    return {
        "repository": {"id": repo_id, "full_name": GHCR_REPOSITORY},
        "owner": {"id": owner_id, "login": GHCR_OWNER},
        "package": {
            "id": package_id,
            "name": GHCR_PACKAGE,
            "package_type": "container",
            "visibility": "public",
            "source_repository_id": repo_id,
        },
    }


def process_census(cap: float, known: tuple[bytes, ...]) -> dict[int, dict[str, Any]]:
    check_deadline(cap)
    observed = subprocess.run(
        ["/bin/ps", "-axo", "pid,ppid,pgid,uid,lstart,state,comm"],
        capture_output=True,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        timeout=min(1, max(0.001, cap - time.monotonic())),
        check=False,
    )  # nosec B603 # B603: fixed absolute ps ownership census; closed env, bounded capture before credential inspection (remove-by: 2026-10-28, ref: PR-2477)
    require(
        observed.returncode == 0
        and len(observed.stdout) + len(observed.stderr) <= GHCR_OUTPUT_LIMIT,
        "GHCR_process_census",
    )
    require(
        all(value not in observed.stdout and value not in observed.stderr for value in known),
        "GHCR_credential_reflection_HOLD",
    )
    rows: dict[int, dict[str, Any]] = {}
    for line in observed.stdout.decode("utf-8", errors="strict").splitlines()[1:]:
        fields = line.split(None, 10)
        require(len(fields) == 11, "GHCR_process_census_row")
        pid, ppid, pgid, uid = (int(value) for value in fields[:4])
        require(pid > 0 and pid not in rows, "GHCR_process_census_identity")
        rows[pid] = {
            "pid": pid,
            "ppid": ppid,
            "pgid": pgid,
            "uid": uid,
            "start": " ".join(fields[4:9]),
            "state": fields[9],
            "comm": fields[10],
        }
    return rows


def process_identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row["pid"], row["pgid"], row["uid"], row["start"], row["comm"])


def owned_members(
    process: subprocess.Popen[bytes],
    seen: dict[int, tuple[Any, ...]],
    cap: float,
    known: tuple[bytes, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not seen:
        rows = process_census(cap, known)
        require(
            not any(row["pgid"] == process.pid for row in rows.values())
            and process.poll() is not None,
            "GHCR_owned_group_unverified",
        )
        return [], []
    process.poll()
    rows = process_census(cap, known)
    leader = rows.get(process.pid)
    if leader is not None and process_identity(leader) != seen.get(process.pid):
        # An exited direct child can have a transient kernel comm before reap.
        # Native wait/absence resolves it; a live changed identity still rejects.
        try:
            process.wait(timeout=min(0.05, max(0.001, cap - time.monotonic())))
        except subprocess.TimeoutExpired:
            pass
        if process.returncode is not None:
            rows = process_census(cap, known)
    live = {
        pid
        for pid, identity in seen.items()
        if pid in rows and process_identity(rows[pid]) == identity
    }
    while True:
        children = {
            pid for pid, row in rows.items() if row["ppid"] in live and row["uid"] == os.getuid()
        } - live
        if not children:
            break
        for pid in children:
            seen[pid] = process_identity(rows[pid])
        live |= children
    group = [row for row in rows.values() if row["pgid"] == process.pid]
    active = [row for row in group if not row["state"].startswith("Z")]
    require(
        all(row["pid"] in live and row["uid"] == os.getuid() for row in active),
        "GHCR_unknown_or_reused_group_member",
    )
    return group, active


def cleanup_process(
    process: subprocess.Popen[bytes] | None,
    seen: dict[int, tuple[Any, ...]],
    cap: float,
    known: tuple[bytes, ...],
) -> None:
    if process is None:
        return
    process.poll()
    for signum in (signal.SIGTERM, signal.SIGKILL):
        group, active = owned_members(process, seen, cap, known)
        if not group:
            break
        if active:
            os.killpg(process.pid, signum)
        wait_until = min(cap, time.monotonic() + 5)
        while time.monotonic() < wait_until:
            process.poll()
            # Observation of absence sends no signal and makes no ownership claim.
            # Revalidate every live identity before any subsequent signal above.
            group = [
                row for row in process_census(cap, known).values() if row["pgid"] == process.pid
            ]
            if not group:
                break
            time.sleep(0.05)
    while time.monotonic() < cap:
        group = [row for row in process_census(cap, known).values() if row["pgid"] == process.pid]
        if not group:
            break
        time.sleep(0.05)
    require(
        not any(row["pgid"] == process.pid for row in process_census(cap, known).values()),
        "GHCR_owned_group_cleanup_absence",
    )
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            stream.close()


def witness_owned_process(
    process: subprocess.Popen[bytes],
    seen: dict[int, tuple[Any, ...]],
    cap: float,
    known: tuple[bytes, ...],
) -> None:
    # Capture the actual own-child identity before poll/wait can reap its leader.
    seen.clear()
    rows = process_census(cap, known)
    row = rows.get(process.pid)
    if row is None:
        require(
            not any(value["pgid"] == process.pid for value in rows.values())
            and process.poll() is not None,
            "GHCR_owned_group_unverified",
        )
        return
    require(
        row["ppid"] == os.getpid() and row["pgid"] == process.pid and row["uid"] == os.getuid(),
        "GHCR_owned_group_unverified",
    )
    seen[process.pid] = process_identity(row)
    owned_members(process, seen, cap, known)


def qualify_existing_ghcr_package(
    work: Path, public: Path, seconds: int, cleanup: int
) -> dict[str, Any]:
    """Exactly one auth status and two fixed API commands, with memory-first output capture."""
    global CLEANING
    require(not INTERRUPTIONS, "GHCR_interrupted")
    require(
        type(seconds) is int and 0 < seconds <= 90 and type(cleanup) is int and 0 < cleanup <= 30,
        "GHCR_budget",
    )
    require(
        os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_OS") == "Linux",
        "GHCR_hosted_only",
    )
    require(
        os.environ.get("GITHUB_REPOSITORY") == GHCR_REPOSITORY
        and os.environ.get("GITHUB_JOB") == "prometheus-ghcr-package-qualification",
        "GHCR_job_context",
    )
    run, attempt, head = (
        os.environ.get(key, "") for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA")
    )
    require(
        re.fullmatch(r"[1-9][0-9]{0,19}", run) is not None
        and attempt == "1"
        and re.fullmatch(r"[0-9a-f]{40}", head) is not None,
        "GHCR_run_context",
    )
    runner = Path(os.environ.get("RUNNER_TEMP", ""))
    real_directory(runner)
    require(
        work == runner / ("ghcr-private-" + run + "-" + attempt)
        and public == runner / ("ghcr-public-" + run + "-" + attempt) / "qualification.json",
        "GHCR_output_coordinates",
    )
    require(not public.parent.exists() and not public.parent.is_symlink(), "GHCR_public_not_fresh")
    credential = os.environ.get("GH_TOKEN")
    if type(credential) is not str or not credential:
        raise QualificationError("GHCR_step_credential_missing")
    known = credential.encode("utf-8", errors="strict")
    gh = shutil.which("gh")
    if gh is None or not Path(gh).is_absolute():
        raise QualificationError("GHCR_native_missing")
    private = [work / name for name in ("home", "config", "cache", "tmp")]
    identities: dict[Path, tuple[int, int]] = {}
    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GH_HOST": "github.com",
        "GH_TOKEN": credential,
        "GH_PROMPT_DISABLED": "1",
        "GH_PAGER": "cat",
        "PAGER": "cat",
        "GH_NO_UPDATE_NOTIFIER": "1",
        "GH_NO_EXTENSION_UPDATE_NOTIFIER": "1",
        "GH_TELEMETRY": "0",
        "DO_NOT_TRACK": "1",
        "HOME": str(private[0]),
        "GH_CONFIG_DIR": str(private[1]),
        "XDG_CONFIG_HOME": str(private[1]),
        "XDG_CACHE_HOME": str(private[2]),
        "TMPDIR": str(private[3]),
    }
    deadline = time.monotonic() + seconds
    cleanup_deadline: float | None = None
    process: subprocess.Popen[bytes] | None = None

    def begin_cleanup() -> float:
        nonlocal cleanup_deadline
        if cleanup_deadline is None:
            cleanup_deadline = min(deadline + cleanup, time.monotonic() + cleanup)
        return cleanup_deadline

    seen: dict[int, tuple[Any, ...]] = {}

    def capture(argv: list[str]) -> bytes:
        nonlocal process
        check_deadline(deadline)
        streams = [bytearray(), bytearray()]
        # This fixed seam deliberately does not call Native.run or serialize environment/raw output.
        process = subprocess.Popen(
            argv,
            cwd=work,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )  # nosec B603 # B603: fixed absolute gh auth/API argv; bounded memory before inspection (remove-by: 2026-10-28, ref: PR-2477)
        if process.stdout is None or process.stderr is None:
            raise QualificationError("GHCR_capture_streams_missing")
        witness_owned_process(process, seen, deadline, (known,))
        try:
            with selectors.DefaultSelector() as selector:
                for index, stream in enumerate((process.stdout, process.stderr)):
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, index)
                while selector.get_map():
                    check_deadline(deadline)
                    owned_members(process, seen, deadline, (known,))
                    for key, _ in selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                        block = os.read(key.fd, 65536)
                        if not block:
                            selector.unregister(key.fileobj)
                        else:
                            require(
                                sum(map(len, streams)) + len(block) <= GHCR_OUTPUT_LIMIT,
                                "GHCR_native_output_bound",
                            )
                            streams[key.data].extend(block)
        except BaseException:
            require(
                all(known not in bytes(stream) for stream in streams),
                "GHCR_credential_reflection_HOLD",
            )
            raise
        code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        process.stdout.close()
        process.stderr.close()
        require(
            all(known not in bytes(stream) for stream in streams), "GHCR_credential_reflection_HOLD"
        )
        require(
            not owned_members(process, seen, deadline, (known,))[0], "GHCR_owned_group_survived"
        )
        exit_code = "GHCR_native_exit_" + ("signal_" + str(-code) if code < 0 else str(code))
        if code != 0 and argv[1] == "api":
            try:
                ghcr_response(bytes(streams[0]))
            except (QualificationError, ValueError, UnicodeError) as error:
                raise QualificationError(
                    exit_code + "_" + (diagnostic_code(error) or type(error).__name__)
                ) from None
        require(code == 0, exit_code)
        process = None
        return bytes(streams[0])

    primary: BaseException | None = None
    cleanup_error: BaseException | None = None
    result: dict[str, Any] | None = None
    try:
        for directory in [work, *private]:
            fresh_directory(directory)
            info = directory.lstat()
            identities[directory] = (info.st_dev, info.st_ino)
        capture([gh, "auth", "status", "--hostname", "github.com"])
        responses = [
            ghcr_response(
                capture(
                    [
                        gh,
                        "api",
                        "--hostname",
                        "github.com",
                        "--method",
                        "GET",
                        "--include",
                        "-H",
                        "Accept:application/vnd.github+json",
                        endpoint,
                    ]
                )
            )
            for endpoint in GHCR_REQUESTS
        ]
        identity = ghcr_identity(responses[0][1], responses[1][1])
        result = {
            "purpose": "One existing GHCR package identity observation only",
            "qualified": True,
            "observed_utc": datetime.now(timezone.utc).isoformat(),
            "source_head": head,
            "run_id": int(run),
            "run_attempt": 1,
            "job": "prometheus-ghcr-package-qualification",
            "native_auth_exit": 0,
            "requests": [
                {"path": endpoint, "native_exit": 0, "HTTP_status": response[0]}
                for endpoint, response in zip(GHCR_REQUESTS, responses, strict=True)
            ],
            "repository": identity["repository"],
            "owner": identity["owner"],
            "package": identity["package"],
        }
    except BaseException as error:
        primary = error
    finally:
        cap = begin_cleanup()
        CLEANING = True
        try:
            cleanup_process(process, seen, cap, (known,))
            if work in identities:
                require(
                    set(work.iterdir()) == set(identities) - {work}, "GHCR_private_members_changed"
                )
            for directory in reversed(identities):
                check_deadline(cap)
                info = directory.lstat()
                require(
                    stat.S_ISDIR(info.st_mode)
                    and info.st_uid == os.getuid()
                    and stat.S_IMODE(info.st_mode) == 0o700
                    and (info.st_dev, info.st_ino) == identities[directory],
                    "GHCR_private_directory_identity",
                )
                directory.rmdir()
            require(not work.exists() and not work.is_symlink(), "GHCR_private_cleanup_absence")
        except BaseException as error:
            cleanup_error = error
        finally:
            CLEANING = False
    if primary is not None:
        if cleanup_error is not None:
            print(
                "GHCR cleanup also failed:"
                + (diagnostic_code(cleanup_error) or type(cleanup_error).__name__),
                file=sys.stderr,
            )
        raise primary
    require(cleanup_error is None, "GHCR_cleanup_failed")
    require(not INTERRUPTIONS, "GHCR_interrupted")
    if result is None:
        raise QualificationError("GHCR_result_missing")
    encoded = (json.dumps(result, sort_keys=True, indent=2) + "\n").encode()
    require(known not in encoded and len(encoded) <= 16384, "GHCR_public_projection_HOLD")
    check_deadline(cap)
    fresh_directory(public.parent)
    descriptor = os.open(public, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
    return result


def canonical_data(value: Any) -> bytes:
    """Canonicalize declared data only; executable producer bytes stay raw."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def one_object(raw: bytes) -> dict[str, Any]:
    objects = decode_objects(raw)
    require(len(objects) == 1, "exact_one_JSON_object")
    return objects[0]


def exact_data(actual: Any, expected: Any) -> None:
    require(type(actual) is type(expected), "declared_data_type")
    if type(expected) is dict:
        require(set(actual) == set(expected), "declared_data_keys")
        for key, value in expected.items():
            exact_data(actual[key], value)
    elif type(expected) is list:
        require(len(actual) == len(expected), "declared_data_length")
        for left, right in zip(actual, expected, strict=True):
            exact_data(left, right)
    else:
        require(actual == expected, "declared_data_value")


def finite_recipe() -> bytes:
    return (
        "# Finite payload declaration; prometheus_source_image.py compares these exact bytes.\n"
        "# This file is DATA. No Dockerfile frontend or build executor consumes it.\n"
        f"FROM {BASE}\n"
        "COPY prometheus /usr/bin/prometheus\nCOPY promtool /usr/bin/promtool\n"
        "COPY prometheus.yml /etc/prometheus/prometheus.yml\nCOPY LICENSE /LICENSE\n"
        "COPY NOTICE /NOTICE\nUSER 65532:65532\nWORKDIR /prometheus\n"
        'ENTRYPOINT ["/bin/prometheus"]\n'
        'CMD ["--config.file=/etc/prometheus/prometheus.yml","--storage.tsdb.path=/prometheus"]\n'
    ).encode()


def declared_inputs() -> dict[str, Any]:
    return {
        "source": {
            "version": "3.15.0",
            "revision": REVISION,
            "tree": TREE,
            "epoch": SOURCE_DATE_EPOCH,
            "archive": SOURCE.__dict__,
            "original_locks": LOCKS,
            "derived_locks": DERIVED_LOCKS,
        },
        "go": {"archive": GO.__dict__, "version": GO_VERSION},
        "ui": {
            "archive": UI.__dict__,
            "checksums": CHECKSUMS.__dict__,
            "files": UI_FILES,
            "compression": "Python GzipFile filename-empty mtime0 level6 OS255",
        },
        "base": {
            "runtime_ref": BASE,
            "config_digest": BASE_CONFIG,
            "root_media_type": OCI_MANIFEST,
            "layers": BASE_LAYER_CONTRACTS,
        },
        "oras": {
            "identity": "PulsePlate-rebuilt upstream ORAS; not the upstream release binary",
            "version": "1.3.4",
            "revision": ORAS_REVISION,
            "tree": ORAS_TREE,
            "source": ORAS_SOURCE.__dict__,
            "canonical_inventory_sha256": ORAS_SOURCE_INVENTORY,
            "raw_headers_sha256": ORAS_RAW_HEADERS,
            "original_locks": ORAS_LOCKS,
            "license_sha256": ORAS_LICENSE,
            "compiler": "go1.27.2 linux/amd64 CGO_ENABLED=0",
            "command": ORAS_COMMAND,
            "flags": [
                "-mod=readonly",
                "-p=1",
                "-trimpath",
                "-buildvcs=false",
                "-ldflags=" + ORAS_METADATA,
            ],
            "retained": None,
        },
        "platform": "linux/amd64",
        "recipe_sha256": sha(finite_recipe()),
        "compiler": {
            "user": "65532:65532",
            "network": "none",
            "CGO_ENABLED": "0",
            "commands": ["./cmd/prometheus", "./cmd/promtool"],
            "flags": ["-p=1", "-trimpath", "-buildvcs=false", "-tags=netgo,builtinassets"],
            "ldflags": PROMETHEUS_METADATA,
            "cache": "fresh-per-logical-image-build; shared only by its two named commands",
            "maximum_seconds_each": 3600,
            "total_serial_invocations": 2,
            "automatic_retries": 0,
        },
    }


def read_image_manifest(path: Path, *, preparation: bool = False) -> dict[str, Any]:
    real_directory(path.parent)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        require(
            stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and 0 < before.st_size <= 64 * 1024,
            "manifest_bounded_regular_leaf",
        )
        raw = os.read(descriptor, before.st_size + 1)
        after, current = os.fstat(descriptor), path.lstat()
        require(
            len(raw) == before.st_size
            and all(
                getattr(before, key) == getattr(after, key) == getattr(current, key)
                for key in (
                    "st_dev",
                    "st_ino",
                    "st_mode",
                    "st_size",
                    "st_mtime_ns",
                    "st_ctime_ns",
                    "st_nlink",
                )
            ),
            "manifest_read_changed",
        )
    finally:
        os.close(descriptor)
    value = one_object(raw)
    require(
        set(value) == {"schema", "phase", "inputs", "selection", "candidate"}, "image_manifest_keys"
    )
    require(value["schema"] == IMAGE_SCHEMA, "image_manifest_schema")
    require(
        type(value["inputs"]) is dict and type(value["inputs"].get("oras")) is dict,
        "image_input_objects",
    )
    expected = declared_inputs()
    retained = value["inputs"]["oras"].get("retained")
    if retained is not None:
        validate_tool_coordinates(retained)
        expected["oras"]["retained"] = retained
    exact_data(value["inputs"], expected)
    if value["phase"] == "source_prepared":
        require(
            preparation and value["selection"] is None and value["candidate"] is None,
            "source_prepared_not_consumable",
        )
    else:
        require(value["phase"] == "candidate_selected", "image_manifest_phase")
        require(retained is not None, "candidate_requires_retained_tool")
        validate_selection(value["selection"])
        validate_candidate_coordinates(value["candidate"])
    return value


def validate_tool_coordinates(value: Any) -> None:
    require(
        type(value) is dict
        and set(value)
        == {
            "source_head",
            "run_id",
            "artifact_id",
            "artifact_name",
            "artifact_digest",
            "binary_sha256",
            "binary_bytes",
            "input_digest",
        },
        "tool_retained_keys",
    )
    require(
        type(value["source_head"]) is str
        and re.fullmatch(r"[0-9a-f]{40}", value["source_head"]) is not None,
        "tool_source_head",
    )
    for name in ("run_id", "artifact_id", "binary_bytes"):
        require(type(value[name]) is int and value[name] > 0, "tool_retained_positive_integer")
    require(value["binary_bytes"] <= 64 * 1024**2, "tool_binary_bound")
    require(value["artifact_name"] == f'prometheus-oras-{value["run_id"]}-1', "tool_artifact_name")
    for name in ("artifact_digest", "input_digest"):
        _digest(value[name])
    require(
        type(value["binary_sha256"]) is str
        and re.fullmatch(r"[0-9a-f]{64}", value["binary_sha256"]) is not None,
        "tool_binary_digest",
    )


def tool_input_projection(root: Path) -> dict[str, Any]:
    """The tool's own output coordinates are never inputs to that tool build."""
    value = read_image_manifest(root / "deploy/prometheus/image-manifest.json", preparation=True)
    inputs = copy.deepcopy(value["inputs"])
    inputs["oras"]["retained"] = None
    return {
        "inputs": inputs,
        "raw_producer": {
            name: {"bytes": (root / name).stat().st_size, "sha256": file_hash(root / name)}
            for name in (
                "scripts/ci/prometheus_source_image.py",
                ".github/workflows/build.yml",
                "deploy/prometheus/Containerfile",
            )
        },
    }


def producer_projection(root: Path, acquired: object) -> dict[str, Any]:
    """No selection, artifact-output ID, wrapper head or timestamp is a build input."""
    recipe = root / "deploy/prometheus/Containerfile"
    require(recipe.read_bytes() == finite_recipe(), "finite_recipe_bytes")
    paths = (
        "scripts/ci/prometheus_source_image.py",
        ".github/workflows/build.yml",
        "deploy/prometheus/Containerfile",
    )
    manifest = read_image_manifest(root / "deploy/prometheus/image-manifest.json", preparation=True)
    require(
        type(acquired) is dict
        and set(acquired) == {"source", "go", "modules", "UI_transform", "tool_implementations"},
        "acquired_input_inventory",
    )
    acquired = cast(dict[str, Any], acquired)
    for name in ("source", "go", "modules"):
        require(
            type(acquired[name]) is str
            and re.fullmatch(r"[0-9a-f]{64}", acquired[name]) is not None,
            "acquired_digest_type",
        )
    require(acquired["go"] == GO.digest, "acquired_qualified_Go")
    transform, implementations = acquired["UI_transform"], acquired["tool_implementations"]
    require(
        type(transform) is dict
        and set(transform)
        == {
            "generated_paths",
            "embed_sha256",
            "python",
            "gzip_source_sha256",
            "zlib_build",
            "zlib_runtime",
            "algorithm",
        },
        "acquired_UI_transform_fields",
    )
    exact_data(transform["generated_paths"], [name + ".gz" for name in sorted(UI_FILES)])
    exact_data(
        transform["algorithm"],
        "Python GzipFile filename-empty mtime0 level6 OS255; not GNU gzip byte equality",
    )
    require(
        type(implementations) is dict
        and set(implementations)
        == {"oras_sha256", "python_executable_sha256", "python_version", "zlib"},
        "acquired_implementation_fields",
    )
    for value in (
        transform["embed_sha256"],
        transform["gzip_source_sha256"],
        implementations["oras_sha256"],
        implementations["python_executable_sha256"],
    ):
        require(
            type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            "acquired_implementation_digest_type",
        )
    for value in (
        transform["python"],
        transform["zlib_build"],
        transform["zlib_runtime"],
        implementations["python_version"],
        implementations["zlib"],
    ):
        require(type(value) is str and 0 < len(value) <= 1024, "acquired_implementation_version")
    require(
        transform["python"] == implementations["python_version"]
        and transform["zlib_runtime"] == implementations["zlib"]
        and manifest["inputs"]["oras"]["retained"] is not None
        and implementations["oras_sha256"]
        == manifest["inputs"]["oras"]["retained"]["binary_sha256"],
        "acquired_retained_implementation_binding",
    )
    return {
        "raw_producer": {
            name: {"bytes": (root / name).stat().st_size, "sha256": file_hash(root / name)}
            for name in paths
        },
        "inputs": manifest["inputs"],
        "acquired": acquired,
    }


def _digest(value: Any) -> str:
    require(
        type(value) is str and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None,
        "sha256_digest_shape",
    )
    return cast(str, value)


def _descriptor(value: Any, media: str) -> dict[str, Any]:
    require(
        type(value) is dict and set(value) == {"mediaType", "size", "digest"}, "descriptor_keys"
    )
    require(
        value["mediaType"] == media
        and type(value["size"]) is int
        and 0 < value["size"] <= MAX_CACHE_BYTES,
        "descriptor_media_or_size",
    )
    _digest(value["digest"])
    return cast(dict[str, Any], value)


def _blob(layout: Path, descriptor: dict[str, Any]) -> bytes:
    path = layout / "blobs/sha256" / _digest(descriptor["digest"])[7:]
    require(
        path.stat().st_size == descriptor["size"] and file_hash(path) == descriptor["digest"][7:],
        "blob_identity",
    )
    raw = path.read_bytes()
    require(
        len(raw) == descriptor["size"] and sha(raw) == descriptor["digest"][7:], "blob_read_changed"
    )
    return raw


def _gunzip(raw: bytes, maximum: int) -> bytes:
    output = bytearray()
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        while chunk := stream.read(1024**2):
            output.extend(chunk)
            require(len(output) <= maximum, "layer_expanded_bound")
    return bytes(output)


def base_graph(layout: Path) -> dict[str, Any]:
    """Authenticate and inspect the one vendor graph; never extract/apply its layers."""
    root_path = layout / "blobs/sha256" / BASE.rsplit(":", 1)[1]
    require(file_hash(root_path) == BASE.rsplit(":", 1)[1], "vendor_root_digest")
    raw_root = root_path.read_bytes()
    exact_data(
        _layout_root(layout),
        {"mediaType": OCI_MANIFEST, "size": len(raw_root), "digest": BASE.rsplit("@", 1)[1]},
    )
    root = one_object(raw_root)
    require(
        set(root) == {"schemaVersion", "mediaType", "config", "layers", "annotations"},
        "vendor_manifest_keys",
    )
    exact_data(root["schemaVersion"], 2)
    exact_data(root["mediaType"], OCI_MANIFEST)
    exact_data(root["layers"], [row["descriptor"] for row in BASE_LAYER_CONTRACTS])
    exact_data(root["config"], {"mediaType": OCI_CONFIG, "size": 2938, "digest": BASE_CONFIG})
    config_raw = _blob(layout, root["config"])
    config = one_object(config_raw)
    exact_data(
        config["rootfs"],
        {"type": "layers", "diff_ids": [row["diff_id"] for row in BASE_LAYER_CONTRACTS]},
    )
    require(
        config["architecture"] == "amd64"
        and config["os"] == "linux"
        and not config["config"].get("OnBuild")
        and not config["config"].get("Volumes"),
        "vendor_config",
    )
    layers = []
    topology = []
    for contract in BASE_LAYER_CONTRACTS:
        compressed = _blob(layout, contract["descriptor"])
        expanded = _gunzip(compressed, contract["expanded"])
        require(
            len(expanded) == contract["expanded"]
            and "sha256:" + sha(expanded) == contract["diff_id"],
            "vendor_independent_diffID",
        )
        rows = []
        with tarfile.open(fileobj=io.BytesIO(expanded), mode="r:") as archive:
            members = archive.getmembers()
            require(len(members) == contract["members"], "vendor_member_count")
            for member in members:
                require(
                    member.type in (tarfile.REGTYPE, tarfile.DIRTYPE, tarfile.SYMTYPE),
                    "unsupported_vendor_member_type",
                )
                row = {
                    "name": member.name,
                    "type": member.type.decode("ascii"),
                    "size": member.size,
                    "mode": member.mode,
                    "linkname": member.linkname,
                }
                if member.isreg():
                    stream = archive.extractfile(member)
                    require(stream is not None, "vendor_member_stream")
                    stream = cast(BinaryIO, stream)
                    data = stream.read(member.size + 1)
                    require(len(data) == member.size, "vendor_member_size")
                    row["sha256"] = sha(data)
                rows.append(row)
                if member.name in ("bin", "usr", "usr/bin", "etc", "etc/prometheus", "prometheus"):
                    topology.append(row)
        require(
            sha(canonical_data(rows)) == contract["inventory_sha256"], "vendor_complete_inventory"
        )
        layers.append({"compressed": compressed, "uncompressed": expanded})
    require(
        [row for row in topology if row["name"] == "bin"]
        == [{"name": "bin", "type": "2", "size": 0, "mode": 0o777, "linkname": "usr/bin"}],
        "vendor_known_bin_alias",
    )
    require(
        all(
            row["type"] == "5" and row["mode"] == 0o755
            for row in topology
            if row["name"] in ("usr", "usr/bin", "etc")
        )
        and not any(row["name"] in ("etc/prometheus", "prometheus") for row in topology),
        "vendor_payload_parent_topology",
    )
    _layout_inventory(
        layout,
        {BASE.rsplit("@", 1)[1], BASE_CONFIG}
        | {row["descriptor"]["digest"] for row in BASE_LAYER_CONTRACTS},
    )
    return {
        "manifest": root,
        "manifest_raw": raw_root,
        "config": config,
        "config_raw": config_raw,
        "layers": layers,
    }


PAYLOAD_DIRECTORIES = (("etc/prometheus", 0, 0), ("prometheus", 65532, 65532))
PAYLOAD_FILES = {
    "LICENSE": ("LICENSE", 0o644),
    "NOTICE": ("NOTICE", 0o644),
    "etc/prometheus/prometheus.yml": ("prometheus.yml", 0o644),
    "usr/bin/prometheus": ("prometheus", 0o755),
    "usr/bin/promtool": ("promtool", 0o755),
}


def payload_layer(files: dict[str, bytes], *, synthetic: bool = False) -> tuple[bytes, bytes]:
    require(set(files) == {entry[0] for entry in PAYLOAD_FILES.values()}, "payload_exact_files")
    for name in ("prometheus", "promtool"):
        raw = files[name]
        require(0 < len(raw) <= 256 * 1024**2, "payload_binary_size")
        if not synthetic:
            require(
                raw[:6] == b"\x7fELF\x02\x01" and raw[18:20] == b"\x3e\x00", "payload_amd64_ELF"
            )
    require(
        synthetic
        or (
            sha(files["prometheus.yml"]) == DEFAULT_CONFIG_SHA256
            and all(sha(files[name]) == digest for name, digest in SOURCE_LICENSES.items())
        ),
        "payload_source_files",
    )
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        # Existing vendor usr/usr-bin/etc ownership is retained byte-for-byte.
        for name, uid, gid in PAYLOAD_DIRECTORIES:
            member = tarfile.TarInfo(name)
            member.type, member.mode, member.uid, member.gid, member.mtime = (
                tarfile.DIRTYPE,
                0o755,
                uid,
                gid,
                SOURCE_DATE_EPOCH,
            )
            archive.addfile(member)
        for path, (name, mode) in sorted(PAYLOAD_FILES.items()):
            raw = files[name]
            member = tarfile.TarInfo(path)
            member.mode, member.size, member.mtime = mode, len(raw), SOURCE_DATE_EPOCH
            archive.addfile(member, io.BytesIO(raw))
    uncompressed = stream.getvalue()
    compressed = io.BytesIO()
    with gzip.GzipFile(
        filename="", mode="wb", fileobj=compressed, compresslevel=6, mtime=0
    ) as output:
        output.write(uncompressed)
    result = compressed.getvalue()
    require(result[3] == 0 and result[9] == 255, "payload_gzip_header")
    return uncompressed, result


def _write_blob(layout: Path, raw: bytes, media: str) -> dict[str, Any]:
    digest = sha(raw)
    path = layout / "blobs/sha256" / digest
    if path.exists():
        require(file_hash(path) == digest and path.read_bytes() == raw, "blob_collision")
    else:
        with path.open("xb") as output:
            output.write(raw)
        path.chmod(0o644)
    return {"mediaType": media, "size": len(raw), "digest": "sha256:" + digest}


def construct_image(
    base: dict[str, Any],
    files: dict[str, bytes],
    layout: Path,
    docker_archive: Path,
    *,
    synthetic: bool = False,
) -> dict[str, Any]:
    fresh_directory(layout, 0o755)
    (layout / "blobs/sha256").mkdir(parents=True, mode=0o755)
    uncompressed, compressed = payload_layer(files, synthetic=synthetic)
    diff_id = "sha256:" + sha(uncompressed)
    layers = []
    for contract, layer in zip(BASE_LAYER_CONTRACTS, base["layers"], strict=True):
        layers.append(_write_blob(layout, layer["compressed"], OCI_LAYER))
        exact_data(layers[-1], contract["descriptor"])
    layers.append(_write_blob(layout, compressed, OCI_LAYER))
    config = copy.deepcopy(base["config"])
    config["created"] = "2026-09-25T07:25:38Z"
    config["config"].update(
        {
            "User": "65532:65532",
            "WorkingDir": "/prometheus",
            "Entrypoint": ["/bin/prometheus"],
            "Cmd": [
                "--config.file=/etc/prometheus/prometheus.yml",
                "--storage.tsdb.path=/prometheus",
            ],
            "ExposedPorts": {"9090/tcp": {}},
            "Labels": {
                "org.opencontainers.image.version": "3.15.0",
                "org.opencontainers.image.revision": REVISION,
                "org.opencontainers.image.source": "https://github.com/prometheus/prometheus",
            },
        }
    )
    config["rootfs"]["diff_ids"].append(diff_id)
    config["history"].append(
        {"created": config["created"], "created_by": "PulsePlate finite Prometheus payload"}
    )
    config_raw = canonical_data(config)
    config_descriptor = _write_blob(layout, config_raw, OCI_CONFIG)
    manifest = {
        "schemaVersion": 2,
        "mediaType": OCI_MANIFEST,
        "config": config_descriptor,
        "layers": layers,
    }
    manifest_descriptor = _write_blob(layout, canonical_data(manifest), OCI_MANIFEST)
    (layout / "oci-layout").write_bytes(canonical_data({"imageLayoutVersion": "1.0.0"}))
    (layout / "index.json").write_bytes(
        canonical_data(
            {
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.index.v1+json",
                "manifests": [manifest_descriptor],
            }
        )
    )
    require(
        not docker_archive.exists() and not docker_archive.is_symlink(), "docker_archive_not_fresh"
    )
    config_name = config_descriptor["digest"][7:] + ".json"
    layer_names = [value[7:] + "/layer.tar" for value in config["rootfs"]["diff_ids"]]
    docker_manifest = [
        {
            "Config": config_name,
            "RepoTags": ["pulseplate-prometheus:candidate"],
            "Layers": layer_names,
        }
    ]
    entries = [("manifest.json", canonical_data(docker_manifest)), (config_name, config_raw)]
    entries += list(
        zip(
            layer_names,
            [layer["uncompressed"] for layer in base["layers"]] + [uncompressed],
            strict=True,
        )
    )
    with tarfile.open(docker_archive, "x", format=tarfile.USTAR_FORMAT) as archive:
        for name, raw in entries:
            member = tarfile.TarInfo(name)
            member.size, member.mode, member.mtime = len(raw), 0o644, SOURCE_DATE_EPOCH
            archive.addfile(member, io.BytesIO(raw))
    return {
        "manifest_digest": manifest_descriptor["digest"],
        "config_digest": config_descriptor["digest"],
        "layers": layers,
        "diff_ids": config["rootfs"]["diff_ids"],
        "binary_sha256": {name: sha(files[name]) for name in ("prometheus", "promtool")},
        "synthetic_format_only": synthetic,
        "docker_archive_sha256": file_hash(docker_archive),
    }


def validate_selection(value: Any) -> None:
    require(
        type(value) is dict
        and set(value)
        == {
            "repository",
            "platform",
            "root_media_type",
            "manifest_digest",
            "config_digest",
            "layers",
            "diff_ids",
            "runtime_ref",
            "binaries",
            "ui_inventory_sha256",
            "source_revision",
            "version",
        },
        "selection_keys",
    )
    require(
        value["repository"] == IMAGE_REPOSITORY
        and value["platform"] == "linux/amd64"
        and value["root_media_type"] == OCI_MANIFEST
        and value["source_revision"] == REVISION
        and value["version"] == "3.15.0",
        "selection_fixed_identity",
    )
    root, config = _digest(value["manifest_digest"]), _digest(value["config_digest"])
    require(
        root != config and value["runtime_ref"] == IMAGE_REPOSITORY + "@" + root,
        "selection_distinct_identity",
    )
    require(
        type(value["layers"]) is list
        and len(value["layers"]) == 14
        and type(value["diff_ids"]) is list
        and len(value["diff_ids"]) == 14,
        "selection_layer_count",
    )
    for descriptor in value["layers"]:
        _descriptor(descriptor, OCI_LAYER)
    exact_data(value["layers"][:13], [row["descriptor"] for row in BASE_LAYER_CONTRACTS])
    exact_data(value["diff_ids"][:13], [row["diff_id"] for row in BASE_LAYER_CONTRACTS])
    for digest in value["diff_ids"]:
        _digest(digest)
    require(len(set(value["diff_ids"])) == 14, "selection_duplicate_diffID")
    require(
        type(value["binaries"]) is dict and set(value["binaries"]) == {"prometheus", "promtool"},
        "selection_both_binaries",
    )
    for record in value["binaries"].values():
        require(
            type(record) is dict
            and set(record) == {"sha256", "version"}
            and record["version"] == "3.15.0"
            and type(record["sha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is not None,
            "selection_binary_identity",
        )
    exact_data(value["ui_inventory_sha256"], sha(canonical_data(UI_FILES)))


def validate_candidate_coordinates(value: Any) -> None:
    require(
        type(value) is dict and set(value) == {"repository", "producer", "artifact", "outputs"},
        "candidate_keys",
    )
    exact_data(value["repository"], {"id": 1043311030, "full_name": GHCR_REPOSITORY})
    producer = value["producer"]
    require(
        type(producer) is dict
        and set(producer)
        == {
            "workflow_id",
            "workflow_path",
            "source_head",
            "source_ref",
            "pr_number",
            "run_id",
            "run_attempt",
            "job_ids",
            "raw_producer",
            "input_projection_sha256",
        },
        "candidate_producer_keys",
    )
    require(
        producer["workflow_path"] == ".github/workflows/build.yml"
        and producer["run_attempt"] == 1
        and type(producer["run_attempt"]) is int,
        "candidate_producer_workflow_attempt",
    )
    for field in ("workflow_id", "pr_number", "run_id"):
        require(type(producer[field]) is int and producer[field] > 0, "candidate_positive_ID")
    require(
        type(producer["source_head"]) is str
        and re.fullmatch(r"[0-9a-f]{40}", producer["source_head"]) is not None
        and type(producer["source_ref"]) is str
        and re.fullmatch(r"refs/heads/[A-Za-z0-9_./-]{1,200}", producer["source_ref"]) is not None
        and ".." not in producer["source_ref"],
        "candidate_source_coordinate",
    )
    require(
        type(producer["job_ids"]) is list
        and bool(producer["job_ids"])
        and all(type(v) is int and v > 0 for v in producer["job_ids"])
        and len(set(producer["job_ids"])) == len(producer["job_ids"]),
        "candidate_job_inventory",
    )
    paths = {
        "scripts/ci/prometheus_source_image.py",
        ".github/workflows/build.yml",
        "deploy/prometheus/Containerfile",
    }
    require(
        type(producer["raw_producer"]) is dict and set(producer["raw_producer"]) == paths,
        "candidate_full_raw_producer",
    )
    for record in producer["raw_producer"].values():
        require(
            type(record) is dict
            and set(record) == {"bytes", "sha256"}
            and type(record["bytes"]) is int
            and 0 < record["bytes"] <= 1024**2,
            "candidate_producer_size",
        )
        _digest("sha256:" + record["sha256"])
    _digest("sha256:" + producer["input_projection_sha256"])
    artifact = value["artifact"]
    require(
        type(artifact) is dict
        and set(artifact) == {"id", "name", "digest", "size", "expires_at", "archive_sha256"},
        "candidate_artifact_keys",
    )
    require(
        type(artifact["id"]) is int
        and artifact["id"] > 0
        and type(artifact["size"]) is int
        and 0 < artifact["size"] <= MAX_CACHE_BYTES
        and artifact["name"] == f"prometheus-source-candidate-{producer['run_id']}-1",
        "candidate_artifact_identity",
    )
    require(
        _digest(artifact["digest"]) == "sha256:" + artifact["archive_sha256"],
        "candidate_artifact_raw_digest",
    )
    require(
        type(artifact["expires_at"]) is str
        and re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", artifact["expires_at"]
        )
        is not None,
        "candidate_expiry_type",
    )
    require(
        type(value["outputs"]) is dict
        and set(value["outputs"])
        == {
            "oci_archive_sha256",
            "docker_archive_sha256",
            "native_report_sha256",
            "pair_report_sha256",
            "spdx_sha256",
            "provenance_bundle_sha256",
            "sbom_bundle_sha256",
        },
        "candidate_output_keys",
    )
    for digest in value["outputs"].values():
        _digest("sha256:" + digest)


def _layout_inventory(layout: Path, blobs: set[str]) -> None:
    real_directory(layout)
    files: set[str] = set()
    directories: set[str] = set()
    for path in layout.rglob("*"):
        info = path.lstat()
        relative = path.relative_to(layout).as_posix()
        require(
            info.st_uid == os.getuid() and len(files) + len(directories) < 64, "layout_owner_count"
        )
        if stat.S_ISDIR(info.st_mode):
            directories.add(relative)
        else:
            require(
                stat.S_ISREG(info.st_mode)
                and info.st_nlink == 1
                and stat.S_IMODE(info.st_mode) in (0o600, 0o644),
                "layout_regular_leaf",
            )
            files.add(relative)
    require(
        directories == {"blobs", "blobs/sha256"}
        and files == {"oci-layout", "index.json"} | {"blobs/sha256/" + d[7:] for d in blobs},
        "layout_closed_inventory",
    )


def _layout_root(layout: Path) -> dict[str, Any]:
    exact_data(one_object((layout / "oci-layout").read_bytes()), {"imageLayoutVersion": "1.0.0"})
    index = one_object((layout / "index.json").read_bytes())
    require(set(index) == {"schemaVersion", "mediaType", "manifests"}, "layout_index_keys")
    exact_data(index["schemaVersion"], 2)
    require(
        index["mediaType"] == "application/vnd.oci.image.index.v1+json"
        and type(index["manifests"]) is list
        and len(index["manifests"]) == 1,
        "layout_one_descriptor",
    )
    descriptor = dict(index["manifests"][0])
    if "annotations" in descriptor:
        annotations = descriptor.pop("annotations")
        require(
            type(annotations) is dict
            and set(annotations) == {"org.opencontainers.image.ref.name"}
            and annotations["org.opencontainers.image.ref.name"]
            in ("base", "candidate", "format-probe", "pullback"),
            "layout_transport_annotation",
        )
    if "platform" in descriptor:
        exact_data(descriptor.pop("platform"), {"architecture": "amd64", "os": "linux"})
    return _descriptor(descriptor, OCI_MANIFEST)


def _payload_files(expanded: bytes) -> dict[str, bytes]:
    expected_names = [name for name, _, _ in PAYLOAD_DIRECTORIES] + sorted(PAYLOAD_FILES)
    values = {}
    with tarfile.open(fileobj=io.BytesIO(expanded), mode="r:") as archive:
        members = archive.getmembers()
        require(
            [member.name for member in members] == expected_names, "payload_member_inventory_order"
        )
        for member in members:
            require(
                not member.pax_headers
                and not member.linkname
                and not member.uname
                and not member.gname
                and member.mtime == SOURCE_DATE_EPOCH,
                "payload_fixed_header",
            )
            if member.name in PAYLOAD_FILES:
                name, mode = PAYLOAD_FILES[member.name]
                require(
                    member.isreg() and member.mode == mode and member.uid == member.gid == 0,
                    "payload_file_type_owner_mode",
                )
                stream = archive.extractfile(member)
                require(stream is not None, "payload_file_stream")
                stream = cast(BinaryIO, stream)
                raw = stream.read(member.size + 1)
                require(len(raw) == member.size, "payload_file_size")
                values[name] = raw
            else:
                name, uid, gid = next(row for row in PAYLOAD_DIRECTORIES if row[0] == member.name)
                require(
                    member.isdir()
                    and member.mode == 0o755
                    and member.uid == uid
                    and member.gid == gid
                    and member.size == 0,
                    "payload_directory_type_owner_mode",
                )
    return values


def validate_oci_graph(
    layout: Path, base: dict[str, Any], *, synthetic: bool = False
) -> dict[str, Any]:
    descriptor = _layout_root(layout)
    raw = _blob(layout, descriptor)
    manifest = one_object(raw)
    require(set(manifest) == {"schemaVersion", "mediaType", "config", "layers"}, "image_root_keys")
    exact_data(manifest["schemaVersion"], 2)
    require(
        manifest["mediaType"] == OCI_MANIFEST and raw == canonical_data(manifest),
        "image_root_encoding",
    )
    require(type(manifest["layers"]) is list and len(manifest["layers"]) == 14, "image_layer_count")
    config_descriptor = _descriptor(manifest["config"], OCI_CONFIG)
    exact_data(manifest["layers"][:13], [row["descriptor"] for row in BASE_LAYER_CONTRACTS])
    expanded_layers = []
    for contract, layer in zip(BASE_LAYER_CONTRACTS, manifest["layers"][:13], strict=True):
        compressed = _blob(layout, _descriptor(layer, OCI_LAYER))
        expanded = _gunzip(compressed, contract["expanded"])
        require(
            len(expanded) == contract["expanded"]
            and "sha256:" + sha(expanded) == contract["diff_id"],
            "image_base_diffID",
        )
        expanded_layers.append(expanded)
    payload = _blob(layout, _descriptor(manifest["layers"][-1], OCI_LAYER))
    expanded = _gunzip(payload, 512 * 1024**2)
    files = _payload_files(expanded)
    expected_expanded, expected_compressed = payload_layer(files, synthetic=synthetic)
    require(
        expanded == expected_expanded and payload == expected_compressed, "payload_exact_encoding"
    )
    expanded_layers.append(expanded)
    diff_ids = [row["diff_id"] for row in BASE_LAYER_CONTRACTS] + ["sha256:" + sha(expanded)]
    config_raw = _blob(layout, config_descriptor)
    config = one_object(config_raw)
    expected_config = copy.deepcopy(base["config"])
    expected_config["created"] = "2026-09-25T07:25:38Z"
    expected_config["config"].update(
        {
            "User": "65532:65532",
            "WorkingDir": "/prometheus",
            "Entrypoint": ["/bin/prometheus"],
            "Cmd": [
                "--config.file=/etc/prometheus/prometheus.yml",
                "--storage.tsdb.path=/prometheus",
            ],
            "ExposedPorts": {"9090/tcp": {}},
            "Labels": {
                "org.opencontainers.image.version": "3.15.0",
                "org.opencontainers.image.revision": REVISION,
                "org.opencontainers.image.source": "https://github.com/prometheus/prometheus",
            },
        }
    )
    expected_config["rootfs"]["diff_ids"] = diff_ids
    expected_config["history"].append(
        {
            "created": expected_config["created"],
            "created_by": "PulsePlate finite Prometheus payload",
        }
    )
    exact_data(config, expected_config)
    require(config_raw == canonical_data(expected_config), "image_config_raw_encoding")
    blobs = {descriptor["digest"], config_descriptor["digest"]} | {
        layer["digest"] for layer in manifest["layers"]
    }
    require(len(blobs) == 16, "image_duplicate_blob")
    _layout_inventory(layout, blobs)
    return {
        "manifest_digest": descriptor["digest"],
        "manifest_raw": raw,
        "config_raw": config_raw,
        "config_digest": config_descriptor["digest"],
        "layers": manifest["layers"],
        "diff_ids": diff_ids,
        "expanded_layers": expanded_layers,
        "files": files,
        "binary_sha256": {name: sha(files[name]) for name in ("prometheus", "promtool")},
    }


def validate_docker_archive(path: Path, graph: dict[str, Any]) -> None:
    require(path.stat().st_size <= MAX_CACHE_BYTES, "docker_archive_bound")
    config_name = graph["config_digest"][7:] + ".json"
    layer_names = [value[7:] + "/layer.tar" for value in graph["diff_ids"]]
    expected_manifest = [
        {
            "Config": config_name,
            "RepoTags": ["pulseplate-prometheus:candidate"],
            "Layers": layer_names,
        }
    ]
    expected = {
        "manifest.json": canonical_data(expected_manifest),
        config_name: graph["config_raw"],
    }
    expected.update(zip(layer_names, graph["expanded_layers"], strict=True))
    before = file_hash(path)
    with tarfile.open(path, "r:") as archive:
        members = archive.getmembers()
        require(
            len(members) == len(expected)
            and len(set(member.name for member in members)) == len(expected)
            and set(member.name for member in members) == set(expected),
            "docker_archive_closed_inventory",
        )
        for member in members:
            require(
                member.isreg()
                and not member.linkname
                and not member.pax_headers
                and member.uid == member.gid == 0
                and member.mode == 0o644
                and member.mtime == SOURCE_DATE_EPOCH
                and member.size == len(expected[member.name]),
                "docker_archive_regular_header",
            )
            stream = archive.extractfile(member)
            require(
                stream is not None and stream.read(member.size + 1) == expected[member.name],
                "docker_archive_raw_config_layer",
            )
    require(file_hash(path) == before, "docker_archive_read_changed")


def compare_pair(first: dict[str, Any], second: dict[str, Any]) -> None:
    for field in (
        "manifest_digest",
        "manifest_raw",
        "config_raw",
        "config_digest",
        "layers",
        "diff_ids",
        "binary_sha256",
    ):
        require(first[field] == second[field], "independent_pair_mismatch_" + field)
    require(first["expanded_layers"] == second["expanded_layers"], "independent_pair_layer_bytes")


def consumer_result(mode: str, admission: str, promotion: str) -> str:
    """Closed event/result table; a generic skipped-or-success bypass is forbidden."""
    table = {
        ("changed_pr_candidate", "success", "skipped"): "local",
        ("new_main_selection", "success", "success"): "published",
        ("unchanged_published", "skipped", "skipped"): "published",
    }
    require((mode, admission, promotion) in table, "consumer_predecessors")
    return table[(mode, admission, promotion)]


class GitHubRead:
    """Bounded same-repository native API reads; credentials never enter Native records."""

    def __init__(self, private: Path, evidence: Path, deadline: float, cleanup: int) -> None:
        gh = shutil.which("gh")
        if gh is None or not Path(gh).is_absolute():
            raise QualificationError("GitHub_native_missing")
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not isinstance(token, str) or not token:
            raise QualificationError("GitHub_credential_missing")
        self.gh, self.private, self.evidence, self.deadline = gh, private, evidence, deadline
        self.known = token.encode()
        self.additional_known = tuple(
            value.encode()
            for name in ("GITHUB_TOKEN", "GHCR_READ_TOKEN")
            if (value := os.environ.get(name))
        )
        require(type(cleanup) is int and 0 < cleanup <= 120, "GitHub_cleanup_budget")
        self.cleanup_seconds = cleanup
        self.cleanup_deadline: float | None = None
        self.process: subprocess.Popen[bytes] | None = None
        self.seen: dict[int, tuple[Any, ...]] = {}
        self.sequence = 0
        fresh_directory(private)
        for name in ("home", "config", "cache", "tmp"):
            fresh_directory(private / name)
        self.environment = {
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "GH_HOST": "github.com",
            "GH_TOKEN": token,
            "GITHUB_TOKEN": token,
            "GH_PROMPT_DISABLED": "1",
            "GH_PAGER": "cat",
            "PAGER": "cat",
            "GH_NO_UPDATE_NOTIFIER": "1",
            "GH_NO_EXTENSION_UPDATE_NOTIFIER": "1",
            "GH_TELEMETRY": "0",
            "DO_NOT_TRACK": "1",
            "HOME": str(private / "home"),
            "GH_CONFIG_DIR": str(private / "config"),
            "XDG_CONFIG_HOME": str(private / "config"),
            "XDG_CACHE_HOME": str(private / "cache"),
            "TMPDIR": str(private / "tmp"),
        }
        try:
            self._capture([gh, "auth", "status", "--hostname", "github.com"], 1024**2)
        except BaseException:
            self.close()
            raise

    def begin_cleanup(self) -> float:
        if self.cleanup_deadline is None:
            self.cleanup_deadline = min(
                self.deadline + self.cleanup_seconds, time.monotonic() + self.cleanup_seconds
            )
        return self.cleanup_deadline

    def _capture(
        self,
        argv: list[str],
        maximum: int,
        *,
        environment: dict[str, str] | None = None,
        input_data: bytes | None = None,
    ) -> bytes:
        global CLEANING
        check_deadline(self.deadline)
        require(self.process is None, "GitHub_prior_owned_group_unresolved")
        require(input_data is None or type(input_data) is bytes, "GitHub_stdin_type")
        process = subprocess.Popen(
            argv,
            cwd=self.private,
            env=self.environment if environment is None else environment,
            stdin=subprocess.DEVNULL if input_data is None else subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )  # nosec B603 # fixed absolute authenticated gh/native argv; bounded memory and stdin, secret reflection checked before retention (remove-by: 2026-10-28, ref: PR-2477)
        self.process = process
        streams = [bytearray(), bytearray()]
        primary: BaseException | None = None
        cleanup_error: BaseException | None = None
        code: int | None = None
        tokens = (self.known, *self.additional_known)
        try:
            # This witness precedes poll/wait; use the same closed recognizer as GHCR qualification.
            witness_owned_process(process, self.seen, self.deadline, tokens)
            require(
                process.stdout is not None and process.stderr is not None, "GitHub_capture_streams"
            )
            with selectors.DefaultSelector() as selector:
                for index, stream in enumerate(
                    (cast(BinaryIO, process.stdout), cast(BinaryIO, process.stderr))
                ):
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, index)
                offset = 0
                if input_data is not None:
                    require(process.stdin is not None, "GitHub_capture_stdin")
                    stdin_stream = cast(BinaryIO, process.stdin)
                    os.set_blocking(stdin_stream.fileno(), False)
                    if input_data:
                        selector.register(stdin_stream, selectors.EVENT_WRITE, 2)
                    else:
                        stdin_stream.close()
                while selector.get_map():
                    check_deadline(self.deadline)
                    owned_members(process, self.seen, self.deadline, tokens)
                    for key, _ in selector.select(
                        min(0.1, max(0, self.deadline - time.monotonic()))
                    ):
                        if key.data == 2:
                            if input_data is None:
                                raise QualificationError("GitHub_capture_stdin_state")
                            try:
                                written = os.write(
                                    key.fd, memoryview(input_data)[offset : offset + 65536]
                                )
                            except BrokenPipeError:
                                raise QualificationError("GitHub_native_stdin_closed") from None
                            offset += written
                            if offset == len(input_data):
                                selector.unregister(key.fileobj)
                                cast(BinaryIO, key.fileobj).close()
                            continue
                        raw = os.read(key.fd, 65536)
                        if raw:
                            require(
                                sum(map(len, streams)) + len(raw) <= maximum,
                                "GitHub_native_output_bound",
                            )
                            streams[key.data].extend(raw)
                        else:
                            selector.unregister(key.fileobj)
            code = process.wait(timeout=max(0.001, self.deadline - time.monotonic()))
            require(
                not owned_members(process, self.seen, self.deadline, tokens)[0],
                "GHCR_owned_group_survived",
            )
            self.process = None
            self.seen.clear()
        except BaseException as error:
            primary = error
            if any(value in bytes(stream) for value in tokens for stream in streams):
                primary = QualificationError("GitHub_credential_reflection_HOLD")
        finally:
            if self.process is not None:
                previous_cleaning, CLEANING = CLEANING, True
                try:
                    cleanup_process(self.process, self.seen, self.begin_cleanup(), tokens)
                    self.process = None
                    self.seen.clear()
                except BaseException as error:
                    cleanup_error = error
                finally:
                    CLEANING = previous_cleaning
            for cleanup_stream in (process.stdin, process.stdout, process.stderr):
                if cleanup_stream is not None and not cleanup_stream.closed:
                    cleanup_stream.close()
        if primary is not None:
            if cleanup_error is not None:
                print(
                    "GitHub cleanup also failed:"
                    + (diagnostic_code(cleanup_error) or type(cleanup_error).__name__),
                    file=sys.stderr,
                )
            raise primary
        require(cleanup_error is None, "GitHub_cleanup_failed")
        raw, stderr_raw = bytes(streams[0]), bytes(streams[1])
        require(
            all(value not in raw and value not in stderr_raw for value in tokens),
            "GitHub_credential_reflection_HOLD",
        )
        self.sequence += 1
        stem = "GitHub-" + str(self.sequence)
        (self.evidence / (stem + ".stderr")).write_bytes(stderr_raw)
        if len(raw) <= 16 * 1024**2:
            (self.evidence / (stem + ".stdout")).write_bytes(raw)
        (self.evidence / (stem + ".json")).write_bytes(
            canonical_data(
                {
                    "argv": argv,
                    "exit": code,
                    "stdout_bytes": len(raw),
                    "stdout_sha256": sha(raw),
                    "stderr_sha256": sha(stderr_raw),
                }
            )
        )
        require(code == 0, "GitHub_native_failed")
        return raw

    def raw(self, endpoint: str, *, maximum: int = 16 * 1024**2) -> bytes:
        require(
            type(endpoint) is str
            and (
                endpoint == "/repos/" + GHCR_REPOSITORY
                or endpoint.startswith("/repos/" + GHCR_REPOSITORY + "/")
            )
            and ".." not in endpoint
            and "#" not in endpoint
            and all(32 < ord(c) < 127 for c in endpoint),
            "GitHub_same_repository_endpoint",
        )
        return self._capture(
            [self.gh, "api", "--hostname", "github.com", "--method", "GET", endpoint], maximum
        )

    def json(self, endpoint: str) -> Any:
        return json.loads(
            self.raw(endpoint), object_pairs_hook=unique_object, parse_constant=reject_constant
        )

    def pages(self, endpoint: str, key: str | None, count: int) -> list[dict[str, Any]]:
        require(type(count) is int and 0 <= count <= 10000, "GitHub_finite_page_count")
        values = []
        for page in range(1, max(1, (count + 99) // 100) + 1):
            response = self.json(
                endpoint + ("&" if "?" in endpoint else "?") + f"per_page=100&page={page}"
            )
            if key is not None:
                require(
                    type(response) is dict
                    and response.get("total_count") == count
                    and type(response.get("total_count")) is int,
                    "GitHub_page_count_drift",
                )
                response = response.get(key)
            require(
                type(response) is list and all(type(v) is dict for v in response),
                "GitHub_page_shape",
            )
            values.extend(response)
        require(
            len(values) == count and len({v.get("id", v.get("sha")) for v in values}) == count,
            "GitHub_complete_distinct_pages",
        )
        return values

    def close(self) -> None:
        global CLEANING
        primary = sys.exc_info()[1]
        previous_cleaning, CLEANING = CLEANING, True
        try:
            cap = self.begin_cleanup()
            if self.process is not None:
                cleanup_process(self.process, self.seen, cap, (self.known, *self.additional_known))
                self.process = None
                self.seen.clear()
            # Never remove credential/config state unless the owned group is proved absent.
            check_deadline(cap)
            require(
                {p.name for p in self.private.iterdir()} == {"home", "config", "cache", "tmp"},
                "GitHub_private_directory_inventory",
            )
            for path in self.private.rglob("*"):
                info = path.lstat()
                require(
                    info.st_uid == os.getuid()
                    and not stat.S_ISLNK(info.st_mode)
                    and (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)),
                    "GitHub_private_member",
                )
            shutil.rmtree(self.private)
            require(
                not self.private.exists() and not self.private.is_symlink(),
                "GitHub_private_cleanup",
            )
            self.environment.clear()
            self.known = b""
            self.additional_known = ()
        except BaseException as error:
            if primary is not None:
                detail = diagnostic_code(error) or type(error).__name__
                print("GitHub cleanup also failed:" + detail, file=sys.stderr)
                primary.add_note("GitHub cleanup also failed:" + detail)
                raise primary from None
            raise
        finally:
            CLEANING = previous_cleaning

    def source_files(self, head: str, paths: tuple[str, ...]) -> dict[str, bytes]:
        require(
            type(head) is str and re.fullmatch(r"[0-9a-f]{40}", head) is not None,
            "GitHub_source_SHA",
        )
        commit = self.json(f"/repos/{GHCR_REPOSITORY}/git/commits/{head}")
        require(type(commit) is dict and commit.get("sha") == head, "GitHub_commit_binding")
        tree_sha = commit.get("tree", {}).get("sha")
        require(
            type(tree_sha) is str and re.fullmatch(r"[0-9a-f]{40}", tree_sha) is not None,
            "GitHub_commit_tree",
        )
        tree = self.json(f"/repos/{GHCR_REPOSITORY}/git/trees/{tree_sha}?recursive=1")
        require(
            type(tree) is dict
            and tree.get("sha") == tree_sha
            and tree.get("truncated") is False
            and type(tree.get("tree")) is list,
            "GitHub_complete_source_tree",
        )
        result = {}
        for path in paths:
            require(
                type(path) is str
                and path
                in {
                    "scripts/ci/prometheus_source_image.py",
                    ".github/workflows/build.yml",
                    "deploy/prometheus/Containerfile",
                    "deploy/prometheus/image-manifest.json",
                },
                "GitHub_finite_source_path",
            )
            rows = [row for row in tree["tree"] if row.get("path") == path]
            require(
                len(rows) == 1
                and rows[0].get("mode") == "100644"
                and rows[0].get("type") == "blob",
                "GitHub_regular_source_blob",
            )
            blob = self.json(f'/repos/{GHCR_REPOSITORY}/git/blobs/{rows[0]["sha"]}')
            require(
                blob.get("encoding") == "base64" and type(blob.get("content")) is str,
                "GitHub_blob_encoding",
            )
            raw = base64.b64decode(blob["content"].replace("\n", ""), validate=True)
            require(
                0 < len(raw) <= 1024**2
                and blob.get("size") == len(raw)
                and type(blob.get("size")) is int
                and blob.get("sha") == rows[0]["sha"]
                and hashlib.sha1(
                    b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
                ).hexdigest()
                == rows[0]["sha"],
                "GitHub_blob_native_identity",
            )
            result[path] = raw
        return result


PRODUCER_FILES = (
    "scripts/ci/prometheus_source_image.py",
    ".github/workflows/build.yml",
    "deploy/prometheus/Containerfile",
)
MANIFEST_PATH = "deploy/prometheus/image-manifest.json"


def authenticate_pr_source(
    api: GitHubRead, number: object, source: str, final: str, source_ref: str
) -> dict[str, Any]:
    require(type(number) is int and number > 0, "candidate_PR_number")
    pr = api.json(f"/repos/{GHCR_REPOSITORY}/pulls/{number}")
    require(
        pr.get("number") == number
        and pr.get("head", {}).get("repo", {}).get("id") == 1043311030
        and pr.get("base", {}).get("repo", {}).get("id") == 1043311030
        and pr["head"].get("sha") == final
        and "refs/heads/" + pr["head"].get("ref", "") == source_ref
        and pr["base"].get("ref") == "main",
        "candidate_same_repository_PR",
    )
    count = pr.get("commits")
    require(type(count) is int and 0 < count <= 250, "candidate_complete_PR_commit_bound")
    commits = api.pages(f"/repos/{GHCR_REPOSITORY}/pulls/{number}/commits", None, count)
    graph = {row["sha"]: row for row in commits}
    require(source in graph and final in graph, "producer_and_final_within_PR")
    pending, visited = [final], set()
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        row = graph.get(current)
        if row is not None:
            require(type(row.get("parents")) is list, "PR_native_parent_inventory")
            pending.extend(parent["sha"] for parent in row["parents"] if parent["sha"] in graph)
    require(source in visited, "producer_ancestor_within_PR")
    return cast(dict[str, Any], pr)


def authenticate_producer_inputs(
    api: GitHubRead, root: Path, source: str, *, tool: bool = False
) -> dict[str, Any]:
    files = api.source_files(source, (*PRODUCER_FILES, MANIFEST_PATH))
    for name in PRODUCER_FILES:
        require(files[name] == (root / name).read_bytes(), "full_raw_producer_input_drift")
    source_manifest = one_object(files[MANIFEST_PATH])
    current = read_image_manifest(root / MANIFEST_PATH, preparation=True)
    source_inputs = copy.deepcopy(source_manifest.get("inputs"))
    current_inputs = copy.deepcopy(current["inputs"])
    require(
        source_manifest.get("schema") == IMAGE_SCHEMA and type(source_inputs) is dict,
        "producer_source_manifest_inputs",
    )
    source_inputs = cast(dict[str, Any], source_inputs)
    if tool:
        source_inputs["oras"]["retained"] = None
        current_inputs["oras"]["retained"] = None
    exact_data(source_inputs, current_inputs)
    return {
        name: {"bytes": len(raw), "sha256": sha(raw)}
        for name, raw in files.items()
        if name in PRODUCER_FILES
    }


def event_admission(
    api: GitHubRead, root: Path, event: dict[str, Any], event_name: str, head: str
) -> dict[str, Any]:
    """Authenticate the three finite event cases. Squash ancestry is never inferred."""
    manifest = read_image_manifest(root / MANIFEST_PATH)
    candidate = manifest["candidate"]
    producer = candidate["producer"]
    if event_name == "pull_request":
        number = event.get("number")
        pr = api.json(f"/repos/{GHCR_REPOSITORY}/pulls/{number}")
        require(
            pr.get("head", {}).get("sha") == head
            and pr.get("state") == "open"
            and pr["head"].get("repo", {}).get("id") == 1043311030
            and pr.get("base", {}).get("repo", {}).get("id") == 1043311030,
            "consumer_actual_open_PR",
        )
        base_files = api.source_files(pr["base"]["sha"], (MANIFEST_PATH,))
        if base_files[MANIFEST_PATH] == (root / MANIFEST_PATH).read_bytes():
            return {
                "mode": "unchanged_published",
                "head": head,
                "publisher_head": pr["base"]["sha"],
            }
        require(number == producer["pr_number"], "changed_PR_original_producer")
        authenticate_pr_source(api, number, producer["source_head"], head, producer["source_ref"])
        authenticate_producer_inputs(api, root, producer["source_head"])
        return {"mode": "changed_pr_candidate", "head": head, "publisher_head": None}
    require(event_name in ("push", "schedule", "workflow_dispatch"), "consumer_event_table")
    if (
        event_name == "push"
        and type(event.get("ref")) is str
        and event["ref"].startswith("refs/tags/v")
    ):
        tag = event["ref"][len("refs/tags/") :]
        require(re.fullmatch(r"v[A-Za-z0-9_.-]{1,100}", tag) is not None, "published_tag_shape")
        reference = api.json(f"/repos/{GHCR_REPOSITORY}/git/ref/tags/{tag}")
        target = reference.get("object", {})
        if target.get("type") == "tag":
            annotated = api.json(f'/repos/{GHCR_REPOSITORY}/git/tags/{target["sha"]}')
            target = annotated.get("object", {})
        require(
            target.get("type") == "commit" and target.get("sha") == head,
            "published_tag_native_commit",
        )
        return {"mode": "unchanged_published", "head": head, "publisher_head": head}
    current = api.json(f"/repos/{GHCR_REPOSITORY}/git/ref/heads/main")
    require(current.get("object", {}).get("sha") == head, "consumer_current_main")
    if event_name == "push" and event.get("ref") == "refs/heads/main":
        before = event.get("before")
        require(
            type(before) is str and re.fullmatch(r"[0-9a-f]{40}", before) is not None,
            "main_before_SHA",
        )
        before = cast(str, before)
        previous = api.source_files(before, (MANIFEST_PATH,))
        if previous[MANIFEST_PATH] != (root / MANIFEST_PATH).read_bytes():
            pr = authenticate_pr_source(
                api,
                producer["pr_number"],
                producer["source_head"],
                api.json(f'/repos/{GHCR_REPOSITORY}/pulls/{producer["pr_number"]}')["head"]["sha"],
                producer["source_ref"],
            )
            require(
                pr.get("merged") is True
                and pr.get("state") == "closed"
                and pr.get("merge_commit_sha") == head,
                "new_selection_actual_squash",
            )
            authenticate_producer_inputs(api, root, producer["source_head"])
            return {
                "mode": "new_main_selection",
                "head": head,
                "publisher_head": head,
                "final_PR_head": pr["head"]["sha"],
            }
    return {"mode": "unchanged_published", "head": head, "publisher_head": head}


def require_publication_predecessor(api: GitHubRead, head: str) -> dict[str, Any]:
    endpoint = (
        f"/repos/{GHCR_REPOSITORY}/actions/workflows/build.yml/runs?event=push&head_sha={head}"
    )
    first = api.json(endpoint + "&per_page=100&page=1")
    runs = api.pages(endpoint, "workflow_runs", first["total_count"])
    eligible = []
    for run in runs:
        if (
            run.get("head_sha") != head
            or run.get("head_branch") != "main"
            or run.get("repository", {}).get("id") != 1043311030
            or run.get("head_repository", {}).get("id") != 1043311030
            or run.get("event") != "push"
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
        ):
            continue
        jobs_endpoint = (
            f'/repos/{GHCR_REPOSITORY}/actions/runs/{run["id"]}/attempts/{run["run_attempt"]}/jobs'
        )
        page = api.json(jobs_endpoint + "?per_page=100&page=1")
        jobs = api.pages(jobs_endpoint, "jobs", page["total_count"])
        positive = [
            job
            for job in jobs
            if job.get("name") == "prometheus-publish"
            and job.get("status") == "completed"
            and job.get("conclusion") == "success"
            and job.get("head_sha") == head
        ]
        if len(positive) == 1:
            eligible.append({"run": run, "job": positive[0]})
    require(bool(eligible), "positive_publication_predecessor_pending_or_missing")
    return max(eligible, key=lambda value: value["run"]["id"])


def authenticated_artifact(
    api: GitHubRead,
    artifact_id: int,
    destination: Path,
    *,
    expected_run: int,
    expected_job: str,
    expected_head: str,
) -> dict[str, Any]:
    require(type(artifact_id) is int and artifact_id > 0, "artifact_positive_ID")
    record = api.json(f"/repos/{GHCR_REPOSITORY}/actions/artifacts/{artifact_id}")
    require(
        type(record) is dict
        and record.get("id") == artifact_id
        and record.get("expired") is False
        and type(record.get("size_in_bytes")) is int
        and 0 < record["size_in_bytes"] <= 1024**3,
        "artifact_identity_expiry_size",
    )
    workflow_run = record.get("workflow_run")
    require(
        type(workflow_run) is dict
        and workflow_run.get("id") == expected_run
        and workflow_run.get("repository_id") == 1043311030
        and workflow_run.get("head_repository_id") == 1043311030
        and workflow_run.get("head_sha") == expected_head,
        "artifact_run_repository_source",
    )
    expiry = record.get("expires_at")
    require(
        type(expiry) is str
        and datetime.fromisoformat(expiry.replace("Z", "+00:00")) > datetime.now(timezone.utc),
        "artifact_current_expiry",
    )
    run = api.json(f"/repos/{GHCR_REPOSITORY}/actions/runs/{expected_run}")
    workflow = api.json(f"/repos/{GHCR_REPOSITORY}/actions/workflows/build.yml")
    require(
        run.get("id") == expected_run
        and run.get("head_sha") == expected_head
        and run.get("repository", {}).get("id") == 1043311030
        and run.get("head_repository", {}).get("id") == 1043311030
        and run.get("event") == "workflow_dispatch"
        and run.get("run_attempt") == 1
        and type(run.get("run_attempt")) is int
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
        and run.get("workflow_id") == workflow.get("id")
        and workflow.get("path") == ".github/workflows/build.yml",
        "artifact_completed_workflow",
    )
    job_page = api.json(
        f"/repos/{GHCR_REPOSITORY}/actions/runs/{expected_run}/attempts/1/jobs?per_page=100&page=1"
    )
    jobs = api.pages(
        f"/repos/{GHCR_REPOSITORY}/actions/runs/{expected_run}/attempts/1/jobs",
        "jobs",
        job_page["total_count"],
    )
    matches = [v for v in jobs if v.get("name") == expected_job]
    require(
        len(matches) == 1
        and matches[0].get("status") == "completed"
        and matches[0].get("conclusion") == "success"
        and matches[0].get("run_id") == expected_run
        and matches[0].get("head_sha") == expected_head,
        "artifact_successful_producer_job",
    )
    raw = api.raw(f"/repos/{GHCR_REPOSITORY}/actions/artifacts/{artifact_id}/zip", maximum=1024**3)
    require(
        len(raw) == record["size_in_bytes"]
        and _digest(record.get("digest")) == "sha256:" + sha(raw),
        "artifact_native_download_digest",
    )
    require(
        not destination.exists() and not destination.is_symlink(), "artifact_download_not_fresh"
    )
    with destination.open("xb") as stream:
        stream.write(raw)
    destination.chmod(0o600)
    return {"artifact": record, "run": run, "workflow": workflow, "job": matches[0]}


def _zip_members(path: Path) -> dict[str, bytes]:
    """Actions transport members are data, never executable inputs by discovery."""
    before = file_hash(path)
    result: dict[str, bytes] = {}
    total = 0
    with zipfile.ZipFile(path) as archive:
        require(0 < len(archive.infolist()) <= 4096, "artifact_member_count")
        for info in archive.infolist():
            name = info.filename
            require(
                type(name) is str
                and name.isascii()
                and not name.startswith("/")
                and "\\" not in name
                and all(v not in ("", ".", "..") for v in name.split("/"))
                and name not in result
                and not info.is_dir()
                and not info.flag_bits & 1,
                "artifact_member_path_or_alias",
            )
            mode = info.external_attr >> 16
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG), "artifact_member_type")
            total += info.file_size
            require(
                0 <= info.file_size <= MAX_CACHE_BYTES and total <= MAX_CACHE_BYTES,
                "artifact_expanded_bound",
            )
            raw = archive.read(info)
            require(len(raw) == info.file_size, "artifact_member_size")
            result[name] = raw
    require(file_hash(path) == before, "artifact_transport_changed")
    return result


def qualification_locks(archive: Path) -> dict[str, bytes]:
    require(
        file_hash(archive) == "1c1f72b037cc8a4446bfae7ff9812ba92fcf8fc10f5f27bd61ee96e889d57762",
        "qualification_acquired_input_zip",
    )
    files = _zip_members(archive)
    result = {}
    for name, digest in DERIVED_LOCKS.items():
        a, b = files["a-derived-" + name], files["b-derived-" + name]
        require(a == b and sha(a) == digest, "qualification_both_native_lock_bytes")
        result[name] = a
    require(
        files["a-module-derivation.patch"] == files["b-module-derivation.patch"]
        and sha(files["a-module-derivation.patch"])
        == "c4598c7cf10147c2155b847ca6fa62cf380a2a95df52cb3df22e11a7202fe8ef",
        "qualification_native_patch",
    )
    report = one_object(files["qualification.json"])
    require(
        report.get("status") == "observed_package_metadata_only"
        and report.get("failure") is None
        and report.get("heavy_build_invocations") == 0
        and type(report.get("heavy_build_invocations")) is int,
        "qualification_not_a_build_output",
    )
    return result


def pack_layout(layout: Path, destination: Path) -> None:
    """Transport this closed layout; never tar a discovered host tree."""
    descriptor = _layout_root(layout)
    manifest = one_object(_blob(layout, descriptor))
    descriptors = [descriptor, manifest["config"], *manifest["layers"]]
    _layout_inventory(layout, {row["digest"] for row in descriptors})
    names = [
        "oci-layout",
        "index.json",
        *sorted("blobs/sha256/" + row["digest"][7:] for row in descriptors),
    ]
    require(not destination.exists() and not destination.is_symlink(), "layout_transport_fresh")
    with tarfile.open(destination, "x", format=tarfile.USTAR_FORMAT) as archive:
        for name in names:
            raw = (layout / name).read_bytes()
            member = tarfile.TarInfo(name)
            member.size, member.mode, member.mtime = len(raw), 0o644, SOURCE_DATE_EPOCH
            archive.addfile(member, io.BytesIO(raw))


def unpack_layout(raw: bytes, destination: Path) -> None:
    fresh_directory(destination)
    fresh_directory(destination / "blobs")
    fresh_directory(destination / "blobs/sha256")
    names, total = set(), 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        for member in archive:
            name = member.name
            require(
                name in ("oci-layout", "index.json")
                or re.fullmatch(r"blobs/sha256/[0-9a-f]{64}", name) is not None,
                "layout_transport_path",
            )
            require(
                name not in names
                and member.isreg()
                and not member.pax_headers
                and member.mode == 0o644
                and member.uid == member.gid == 0
                and member.linkname == ""
                and member.mtime == SOURCE_DATE_EPOCH,
                "layout_transport_header",
            )
            names.add(name)
            total += member.size
            require(
                len(names) <= 32
                and 0 < member.size <= MAX_CACHE_BYTES
                and total <= MAX_CACHE_BYTES,
                "layout_transport_bound",
            )
            source = archive.extractfile(member)
            require(source is not None, "layout_transport_member")
            source = cast(BinaryIO, source)
            with (destination / name).open("xb") as output:
                shutil.copyfileobj(source, output, 1024**2)
            (destination / name).chmod(0o600)
    require({"oci-layout", "index.json"} <= names, "layout_transport_complete")


def manual_hosted_admission(api: GitHubRead, purpose: str) -> dict[str, Any]:
    require(
        purpose in ("tool", "pair")
        and platform.system() == "Linux"
        and platform.machine() in ("x86_64", "amd64")
        and os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
        and os.environ.get("GITHUB_REPOSITORY") == GHCR_REPOSITORY
        and os.environ.get("GITHUB_REPOSITORY_ID") == "1043311030"
        and os.environ.get("GITHUB_RUN_ATTEMPT") == "1",
        "manual_hosted_first_attempt",
    )
    run_id = int(os.environ["GITHUB_RUN_ID"])
    head, ref = os.environ["GITHUB_SHA"], os.environ["GITHUB_REF"]
    current = api.json(f"/repos/{GHCR_REPOSITORY}/actions/runs/{run_id}")
    workflow = api.json(f"/repos/{GHCR_REPOSITORY}/actions/workflows/build.yml")
    require(
        current.get("head_sha") == head
        and current.get("run_attempt") == 1
        and type(current.get("run_attempt")) is int
        and type(workflow.get("id")) is int
        and workflow["id"] > 0
        and current.get("repository", {}).get("id") == 1043311030
        and current.get("head_repository", {}).get("id") == 1043311030
        and current.get("event") == "workflow_dispatch"
        and current.get("workflow_id") == workflow.get("id")
        and workflow.get("path") == ".github/workflows/build.yml",
        "manual_authenticated_run",
    )
    endpoint = f"/repos/{GHCR_REPOSITORY}/actions/workflows/build.yml/runs?event=workflow_dispatch"
    page = api.json(endpoint + "&per_page=100&page=1")
    history = api.pages(endpoint, "workflow_runs", page["total_count"])
    job_name = (
        "prometheus-oras-qualification" if purpose == "tool" else "prometheus-source-build-pair"
    )
    observed = []
    for run in history:
        if run["id"] == run_id:
            continue
        jobs_endpoint = f'/repos/{GHCR_REPOSITORY}/actions/runs/{run["id"]}/jobs?filter=all'
        jobs_page = api.json(jobs_endpoint + "&per_page=100&page=1")
        jobs = api.pages(jobs_endpoint, "jobs", jobs_page["total_count"])
        observed += [
            {
                "run_id": run["id"],
                "job_id": job["id"],
                "status": job.get("status"),
                "conclusion": job.get("conclusion"),
            }
            for job in jobs
            if job.get("name") == job_name and job.get("conclusion") != "skipped"
        ]
    require(not observed, "nonrenewable_hosted_invocation_budget_spent_or_unknown")
    return {
        "run_id": run_id,
        "head": head,
        "ref": ref,
        "workflow_id": workflow["id"],
        "job": job_name,
        "actual_prior_invocations": observed,
        "budget": 1 if purpose == "tool" else 2,
    }


def finite_go(
    native: Native,
    work: Path,
    docker: str,
    config: Path,
    docker_env: dict[str, str],
    source: Path,
    go: Path,
    modules: Path,
    owned: dict[str, dict[str, Any]],
    label: str,
    command: list[str],
    *,
    output: Path | None = None,
    compile_seconds: int | None = None,
) -> bytes:
    name, owner = "pp-prom-" + uuid.uuid4().hex[:16], uuid.uuid4().hex
    image = one_object(
        native.run(
            [docker, "--config", str(config), "image", "inspect", "--format", "{{json .}}", BASE],
            label + "-base",
            docker_env,
            cwd=work,
        )
    )
    require(
        image.get("Id") == BASE_CONFIG
        and image.get("Os") == "linux"
        and image.get("Architecture") == "amd64"
        and BASE in image.get("RepoDigests", [])
        and not image.get("Config", {}).get("Volumes"),
        "compiler_fixed_base",
    )
    environment = dict(value.split("=", 1) for value in image["Config"].get("Env", []))
    environment.update(
        clean_environment(
            GUEST_TMP, GUEST_TMP, GUEST_TMP / "gocache", Path("/modules"), offline=True
        )
    )
    if output is not None:
        environment.update(TMPDIR="/output/tmp", GOCACHE="/output/cache")
    expected = {
        "image": BASE_CONFIG,
        "owner": owner,
        "command": command,
        "environment": environment,
        "mounts": {"/src": str(source), "/usr/local/go": str(go), "/modules": str(modules)},
    }
    if output is not None:
        expected["output"] = str(output)
    argv = (
        sandbox_arguments(
            docker, config, BASE_CONFIG, name, owner, source, go, modules, output=output
        )
        + command
    )
    create_owned(native, argv, name, expected, owned, label, docker_env, work)
    actual = json.loads(
        native.run(
            [docker, "--config", str(config), "inspect", name],
            label + "-before",
            docker_env,
            cwd=work,
        )
    )[0]
    validate_container(actual, name, expected)
    raw = native.run(
        [docker, "--config", str(config), "start", "--attach", name],
        label + "-native",
        docker_env,
        cwd=work,
        maximum_seconds=compile_seconds,
        watched_output=output if compile_seconds is not None else None,
    )
    actual = json.loads(
        native.run(
            [docker, "--config", str(config), "inspect", name],
            label + "-terminal",
            docker_env,
            cwd=work,
        )
    )[0]
    validate_container(actual, name, expected)
    require(
        actual["State"].get("Running") is False
        and actual["State"].get("ExitCode") == 0
        and type(actual["State"].get("ExitCode")) is int
        and actual["State"].get("OOMKilled") is False,
        "finite_go_terminal",
    )
    return raw


def prefetch_modules(
    native: Native, work: Path, source: Path, go: Path, label: str, locks: dict[str, str]
) -> tuple[Path, dict[str, Any]]:
    modules = work / (label + "-modules")
    fresh_directory(modules, 0o755)
    home, tmp, cache = (work / (label + "-" + value) for value in ("home", "tmp", "cache"))
    for path in (home, tmp, cache):
        fresh_directory(path)
    online = clean_environment(home, tmp, cache, modules, offline=False)
    binary = str(go / "bin/go")
    require(
        native.run([binary, "version"], label + "-version", online, cwd=source).decode()
        == GO_VERSION,
        "prefetch_qualified_Go",
    )
    before = tree_inventory(source)
    downloads = native.run(
        [binary, "mod", "download", "-json", "all"], label + "-download", online, cwd=source
    )
    decode_modules(downloads)
    native.run([binary, "mod", "verify"], label + "-verify", online, cwd=source)
    require(
        all(file_hash(source / name) == digest for name, digest in locks.items())
        and tree_inventory(source) == before,
        "prefetch_original_locks_source",
    )
    for path in modules.rglob("*"):
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), "prefetch_cache_type")
        path.chmod(0o555 if stat.S_ISDIR(info.st_mode) else 0o444)
    modules.chmod(0o555)
    inventory = tree_inventory(modules)
    return modules, {
        "inventory_sha256": sha(canonical_data(inventory)),
        "download_stdout_sha256": sha(downloads),
        "files": len(inventory),
    }


def tool_packages(raw: bytes) -> dict[str, Any]:
    packages = decode_objects(raw)
    indexed: dict[str, dict[str, Any]] = {}
    for value in packages:
        path = value.get("ImportPath")
        require(
            type(path) is str
            and bool(path)
            and path not in indexed
            and not value.get("Error")
            and not value.get("DepsErrors")
            and not value.get("Incomplete"),
            "ORAS_package_identity_error",
        )
        indexed[cast(str, path)] = value
    require(
        ORAS_COMMAND in indexed and indexed[ORAS_COMMAND].get("Name") == "main",
        "ORAS_command_graph",
    )
    for value in indexed.values():
        mapping = value.get("ImportMap", {})
        require(
            type(mapping) is dict
            and type(value.get("Imports", [])) is list
            and all(mapping.get(name, name) in indexed for name in value.get("Imports", [])),
            "ORAS_complete_command_graph",
        )
    forbidden = sorted(
        path
        for path in indexed
        if path == "golang.org/x/crypto/ssh"
        or path.startswith("golang.org/x/crypto/ssh/")
        or path == "golang.org/x/crypto/openpgp"
        or path.startswith("golang.org/x/crypto/openpgp/")
    )
    require(not forbidden, "ORAS_SSH_OpenPGP_imports_HOLD")
    return {
        "command": ORAS_COMMAND,
        "packages": len(indexed),
        "package_paths": sorted(indexed),
        "SSH_OpenPGP_paths": forbidden,
        "scope": "exact Linux amd64 CGO0 command graph",
    }


def selection_from_graph(graph: dict[str, Any]) -> dict[str, Any]:
    manifest = one_object(graph["manifest_raw"])
    selection = {
        "repository": IMAGE_REPOSITORY,
        "platform": "linux/amd64",
        "root_media_type": OCI_MANIFEST,
        "manifest_digest": "sha256:" + sha(graph["manifest_raw"]),
        "config_digest": manifest["config"]["digest"],
        "layers": manifest["layers"],
        "diff_ids": graph["diff_ids"],
        "runtime_ref": IMAGE_REPOSITORY + "@sha256:" + sha(graph["manifest_raw"]),
        "binaries": {
            name: {"sha256": sha(graph["files"][name]), "version": "3.15.0"}
            for name in ("prometheus", "promtool")
        },
        "ui_inventory_sha256": sha(canonical_data(UI_FILES)),
        "source_revision": REVISION,
        "version": "3.15.0",
    }
    validate_selection(selection)
    return selection


def native_import(
    native: Native,
    work: Path,
    docker: str,
    config: Path,
    env: dict[str, str],
    archive: Path,
    graph: dict[str, Any],
    *,
    synthetic: bool,
) -> dict[str, Any]:
    validate_docker_archive(archive, graph)
    inventory = native.run(
        [docker, "--config", str(config), "image", "ls", "--format", "{{.Repository}}:{{.Tag}}"],
        "import-inventory",
        env,
        cwd=work,
    )
    require(
        b"pulseplate-prometheus:candidate" not in inventory.splitlines(),
        "native_import_tag_collision",
    )
    native.run(
        [docker, "--config", str(config), "load", "--input", str(archive)],
        "import-load",
        env,
        cwd=work,
    )
    image = one_object(
        native.run(
            [
                docker,
                "--config",
                str(config),
                "image",
                "inspect",
                "--format",
                "{{json .}}",
                "pulseplate-prometheus:candidate",
            ],
            "import-image",
            env,
            cwd=work,
        )
    )
    require(
        image.get("Id") == graph["config_digest"]
        and (image.get("Os"), image.get("Architecture")) == ("linux", "amd64")
        and image.get("RootFS", {}).get("Layers") == graph["diff_ids"]
        and image.get("Config", {}).get("User") == "65532:65532"
        and image["Config"].get("Entrypoint") == ["/bin/prometheus"]
        and image["Config"].get("Volumes") in (None, {}),
        "native_import_identity",
    )
    name, owner = "pp-prom-format-" + uuid.uuid4().hex[:16], uuid.uuid4().hex
    created = False
    captures = {}
    try:
        native.run(
            [
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
                "--network",
                "none",
                "--read-only",
                "--user",
                "65532:65532",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                graph["config_digest"],
            ],
            "import-create",
            env,
            cwd=work,
        )
        created = True
        for index, path in enumerate(
            (
                "/usr/bin/prometheus",
                "/bin/prometheus",
                "/usr/bin/promtool",
                "/bin/promtool",
                "/etc/prometheus/prometheus.yml",
                "/LICENSE",
                "/NOTICE",
            )
        ):
            raw = native.run(
                [docker, "--config", str(config), "cp", name + ":" + path, "-"],
                "import-copy-" + str(index),
                env,
                cwd=work,
                output_bound=257 * 1024**2,
            )
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as stream:
                members = stream.getmembers()
                require(
                    len(members) == 1 and members[0].isreg() and members[0].linkname == "",
                    "native_copy_one_regular_file",
                )
                member = members[0]
                filename = PurePosixPath(path).name
                expected = graph["files"][filename]
                source = stream.extractfile(member)
                require(
                    source is not None
                    and member.name == filename
                    and member.uid == member.gid == 0
                    and member.mode == (0o755 if filename in ("prometheus", "promtool") else 0o644)
                    and member.size == len(expected)
                    and source.read() == expected,
                    "native_copy_physical_alias_bytes_modes",
                )
                captures[path] = {
                    "tar_sha256": sha(raw),
                    "file_sha256": sha(expected),
                    "header": {
                        "name": member.name,
                        "mode": member.mode,
                        "uid": member.uid,
                        "gid": member.gid,
                        "size": member.size,
                    },
                }
            # Preserve complete native tar bytes losslessly without retaining several
            # uncompressed copies of the same large binaries in the Actions archive.
            original = native.evidence / ("import-copy-" + str(index) + ".stdout")
            compressed = original.with_suffix(original.suffix + ".gz")
            with (
                compressed.open("xb") as target,
                gzip.GzipFile(
                    filename="", fileobj=target, mode="wb", mtime=0, compresslevel=6
                ) as gzip_output,
            ):
                gzip_output.write(raw)
            require(
                _gunzip(compressed.read_bytes(), 257 * 1024**2) == raw,
                "native_copy_lossless_retention",
            )
            native.records[-1].update(
                stdout=str(compressed),
                stdout_encoding="gzip",
                stdout_stored_sha256=file_hash(compressed),
            )
            captures[path]["retained_tar_gzip_sha256"] = file_hash(compressed)
            original.unlink()
        if not synthetic:
            for binary in ("prometheus", "promtool"):
                output = native.run(
                    [
                        docker,
                        "--config",
                        str(config),
                        "run",
                        "--rm",
                        "--pull",
                        "never",
                        "--network",
                        "none",
                        "--read-only",
                        "--cap-drop",
                        "ALL",
                        "--security-opt",
                        "no-new-privileges",
                        "--user",
                        "65532:65532",
                        "--entrypoint",
                        "/bin/" + binary,
                        graph["config_digest"],
                        "--version",
                    ],
                    "import-" + binary + "-version",
                    env,
                    cwd=work,
                )
                require(
                    re.search(rb"\bversion 3\.15\.0\b", output) is not None
                    and REVISION.encode() in output
                    and b"go1.27.2" in output,
                    "native_candidate_version_revision_compiler",
                )
        return {
            "status": (
                "observed_synthetic_format_only" if synthetic else "observed_real_native_import"
            ),
            "image_config_id": image["Id"],
            "diff_ids": image["RootFS"]["Layers"],
            "copies": captures,
            "synthetic_executed": False,
        }
    finally:
        cleaning = sys.exc_info()[0] is not None or time.monotonic() >= native.deadline
        if cleaning and native.cleanup_deadline is None:
            native.begin_cleanup()
        if created:
            actual = one_object(
                native.run(
                    [docker, "--config", str(config), "inspect", "--format", "{{json .}}", name],
                    "import-owned-before-remove",
                    env,
                    cwd=work,
                    cleaning=cleaning,
                )
            )
            require(
                actual["Image"] == graph["config_digest"]
                and actual["Config"]["Labels"].get(LABEL) == owner
                and actual["State"]["Running"] is False
                and actual.get("Mounts") == [],
                "native_format_owned_container",
            )
            native.run(
                [docker, "--config", str(config), "rm", name],
                "import-remove",
                env,
                cwd=work,
                cleaning=cleaning,
            )
            remaining = native.run(
                [docker, "--config", str(config), "ps", "--all", "--format", "{{.Names}}"],
                "import-container-absence",
                env,
                cwd=work,
                cleaning=cleaning,
            )
            require(name.encode() not in remaining.splitlines(), "native_format_container_survives")
        actual_image = one_object(
            native.run(
                [
                    docker,
                    "--config",
                    str(config),
                    "image",
                    "inspect",
                    "--format",
                    "{{json .}}",
                    graph["config_digest"],
                ],
                "import-image-before-remove",
                env,
                cwd=work,
                cleaning=cleaning,
            )
        )
        require(
            actual_image.get("RepoTags") == ["pulseplate-prometheus:candidate"],
            "native_import_owned_tag",
        )
        native.run(
            [docker, "--config", str(config), "image", "rm", graph["config_digest"]],
            "import-image-remove",
            env,
            cwd=work,
            cleaning=cleaning,
        )
        remaining = native.run(
            [
                docker,
                "--config",
                str(config),
                "image",
                "ls",
                "--format",
                "{{.Repository}}:{{.Tag}}",
            ],
            "import-image-absence",
            env,
            cwd=work,
            cleaning=cleaning,
        )
        require(
            b"pulseplate-prometheus:candidate" not in remaining.splitlines(),
            "native_format_image_survives",
        )


def tool_scan_inventory(raw: bytes, subject: str) -> dict[str, Any]:
    """Validate observation structure/coverage/privacy, never classify its findings."""
    require(
        type(subject) is str and Path(subject).is_absolute() and ".." not in Path(subject).parts,
        "tool_scan_subject_coordinate",
    )
    value = one_object(raw)
    require(
        type(value.get("SchemaVersion")) is int
        and value["SchemaVersion"] == 2
        and value.get("ArtifactName") == subject
        and value.get("ArtifactType") == "filesystem"
        and type(value.get("Trivy")) is dict
        and value["Trivy"].get("Version") == "0.74.0"
        and type(value.get("Results")) is list
        and bool(value["Results"]),
        "tool_full_scan_schema_subject",
    )
    findings, missing_secrets, targets = [], 0, []
    for row in value["Results"]:
        require(
            type(row) is dict
            and type(row.get("Target")) is str
            and bool(row["Target"])
            and type(row.get("Class")) is str
            and type(row.get("Type")) is str,
            "tool_full_result_identity",
        )
        require(
            "Secrets" not in row or (type(row["Secrets"]) is list and not row["Secrets"]),
            "tool_detected_secret_HOLD_private_report",
        )
        missing_secrets += "Secrets" not in row
        require(type(row.get("Vulnerabilities", [])) is list, "tool_full_finding_inventory")
        for finding in row.get("Vulnerabilities", []):
            require(
                type(finding) is dict
                and all(
                    type(finding.get(name)) is str and finding[name]
                    for name in ("VulnerabilityID", "PkgName", "InstalledVersion", "Severity")
                )
                and finding["Severity"] in ("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"),
                "tool_full_finding_types",
            )
            findings.append(finding)
        if (row["Target"], row["Class"], row["Type"]) == ("usr/bin/oras", "lang-pkgs", "gobinary"):
            targets.append(row)
    require(
        len(targets) == 1 and len(value["Results"]) == 1, "tool_complete_named_target_inventory"
    )
    packages = targets[0].get("Packages")
    require(
        type(packages) is list
        and bool(packages)
        and all(
            type(row) is dict
            and type(row.get("Name")) is str
            and row["Name"]
            and type(row.get("Version")) is str
            and row["Version"]
            for row in packages
        ),
        "tool_listed_package_identity",
    )
    require(
        len({(row["Name"], row["Version"]) for row in packages}) == len(packages)
        and [row["Version"] for row in packages if row["Name"] == "stdlib"] == ["v1.27.2"],
        "tool_native_Go_scanner_coverage",
    )
    identities = {(row["Name"], row["Version"]) for row in packages}
    require(
        all((row["PkgName"], row["InstalledVersion"]) in identities for row in findings),
        "tool_finding_listed_package_binding",
    )
    return {"all_findings": findings, "Secrets_fields_absent": missing_secrets}


def scan_tool(native: Native, work: Path, binary: Path, env: dict[str, str]) -> dict[str, Any]:
    scanner = shutil.which("trivy")
    require(scanner is not None and Path(scanner).is_absolute(), "tool_native_scanner_missing")
    scanner = cast(str, scanner)
    version = native.run([scanner, "--version"], "tool-scanner-version", env, cwd=work)
    require(
        re.search(rb"^Version: 0\.74\.0$", version, re.MULTILINE) is not None,
        "tool_pinned_scanner_version",
    )
    cache = Path(os.environ["PROMETHEUS_TOOL_TRIVY_CACHE"])
    real_directory(cache)
    db = {
        name: {"bytes": (cache / name).stat().st_size, "sha256": file_hash(cache / name)}
        for name in ("db/trivy.db", "db/metadata.json")
    }
    rootfs = work / "tool-rootfs"
    fresh_directory(rootfs)
    (rootfs / "usr/bin").mkdir(parents=True)
    shutil.copyfile(binary, rootfs / "usr/bin/oras")
    (rootfs / "usr/bin/oras").chmod(0o755)
    config, ignore, report = (
        work / "empty-trivy.yaml",
        work / "empty.trivyignore",
        work / "tool-full.private.json",
    )
    config.write_bytes(b"{}\n")
    ignore.write_bytes(b"")
    before = file_hash(binary)
    native.run(
        [
            scanner,
            "rootfs",
            "--config",
            str(config),
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
            "library",
            "--list-all-pkgs",
            "--severity",
            "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL",
            "--format",
            "json",
            "--exit-code",
            "0",
            "--ignore-unfixed=false",
            "--ignorefile",
            str(ignore),
            "--timeout",
            "300s",
            "--output",
            str(report),
            str(rootfs),
        ],
        "tool-full-scan",
        env,
        cwd=work,
        maximum_seconds=330,
    )
    require(
        file_hash(binary) == before
        and file_hash(rootfs / "usr/bin/oras") == before
        and {
            name: {"bytes": (cache / name).stat().st_size, "sha256": file_hash(cache / name)}
            for name in db
        }
        == db,
        "tool_scan_subject_DB_changed",
    )
    inventory = tool_scan_inventory(report.read_bytes(), str(rootfs))
    destination = native.evidence / "tool-full.raw.json"
    require(not destination.exists(), "tool_full_publication_fresh")
    os.rename(report, destination)
    coverage_description = (
        "Native successful vuln,secret invocation on this executable rootfs; omitted Secrets "
        "fields remain omitted. No forced empty list or zero-secret claim."
    )
    return {
        "binary_sha256": before,
        "scanner_sha256": file_hash(Path(scanner)),
        "report_sha256": file_hash(destination),
        "DB": db,
        **inventory,
        "subject": str(rootfs),
        "native_argv": native.records[-1]["argv"],
        "native_exit": native.records[-1]["exit"],
        "secret_coverage": coverage_description,
        "scope": "Current native inventory; independent complete advisory applicability review remains required",
    }


def qualify_tool(work: Path, root: Path, seconds: int, cleanup: int) -> dict[str, Any]:
    require(
        type(seconds) is int
        and 0 < seconds <= 1800
        and type(cleanup) is int
        and 0 < cleanup <= 120,
        "tool_operation_budget",
    )
    fresh_directory(work)
    evidence = work / "evidence"
    fresh_directory(evidence)
    native = Native(evidence, time.monotonic() + seconds, cleanup)
    api = GitHubRead(work / "GitHub-private", evidence, native.deadline, cleanup)
    try:
        admission = manual_hosted_admission(api, "tool")
        authenticate_producer_inputs(api, root, admission["head"], tool=True)
    finally:
        api.close()
    projection = tool_input_projection(root)
    report: dict[str, Any] = {
        "identity": "PulsePlate-rebuilt ORAS 1.3.4",
        "source_revision": ORAS_REVISION,
        "source_tree": ORAS_TREE,
        "original_locks": ORAS_LOCKS,
        "admission": admission,
        "input_projection": projection,
        "input_digest": "sha256:" + sha(canonical_data(projection)),
        "tool_compile_invocations": 0,
        "Prometheus_compile_invocations": 0,
        "failure": None,
    }
    docker = shutil.which("docker")
    require(docker is not None and Path(docker).is_absolute(), "tool_Docker_missing")
    docker = cast(str, docker)
    config = work / "docker-config"
    fresh_directory(config)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "DOCKER_CONFIG": str(config),
        "LANG": "C.UTF-8",
    }
    owned: dict[str, dict[str, Any]] = {}
    try:
        downloads = work / "downloads"
        fresh_directory(downloads)
        for artifact in (ORAS_SOURCE, GO):
            acquire(artifact, downloads / artifact.name, native.deadline)
        source, go = work / "source", work / "go"
        for artifact, path in ((ORAS_SOURCE, source), (GO, go)):
            rows = extract(artifact, downloads / artifact.name, path, native.deadline)
            (evidence / (artifact.name + "-members.json")).write_bytes(canonical_data(rows))
        require(
            all(file_hash(source / name) == value for name, value in ORAS_LOCKS.items())
            and file_hash(source / "LICENSE") == ORAS_LICENSE,
            "tool_source_locks_license",
        )
        modules, report["public_modules"] = prefetch_modules(
            native, work, source, go, "tool", ORAS_LOCKS
        )
        native.run(
            [docker, "--config", str(config), "pull", "--platform", "linux/amd64", BASE],
            "tool-base-pull",
            env,
            cwd=work,
        )
        before_source, before_cache = tree_inventory(source), tree_inventory(modules)
        commands = (
            ("version", ["version"]),
            ("verify", ["mod", "verify"]),
            ("modules", ["list", "-mod=readonly", "-m", "-json", "all"]),
            ("graph", ["mod", "graph"]),
            ("packages", ["list", "-mod=readonly", "-deps", "-json", ORAS_COMMAND]),
        )
        for label, command in commands:
            raw = finite_go(
                native,
                work,
                docker,
                config,
                env,
                source,
                go,
                modules,
                owned,
                "tool-" + label,
                command,
            )
            if label == "version":
                require(raw.decode() == GO_VERSION, "tool_offline_compiler")
            elif label == "modules":
                report["full_modules"] = decode_selected_modules(raw, root_module="oras.land/oras")
                require(
                    all("Replace" not in row for row in report["full_modules"].values()),
                    "ORAS_unchanged_source_replacements",
                )
            elif label == "packages":
                report["command_graph"] = tool_packages(raw)
        output = work / "compiled"
        require(
            sum(path.is_file() for path in evidence.rglob("*")) <= 3500,
            "tool_precompile_transport_member_reserve",
        )
        fresh_directory(output, 0o777)
        output.chmod(0o777)
        for name in ("cache", "tmp"):
            fresh_directory(output / name, 0o777)
            (output / name).chmod(0o777)
        report["tool_compile_invocations"] += 1
        (evidence / "invocation-start.json").write_bytes(canonical_data(report))
        finite_go(
            native,
            work,
            docker,
            config,
            env,
            source,
            go,
            modules,
            owned,
            "tool-compile",
            [
                "build",
                "-mod=readonly",
                "-trimpath",
                "-buildvcs=false",
                "-p=1",
                "-ldflags=" + ORAS_METADATA,
                "-o",
                "/output/oras",
                ORAS_COMMAND,
            ],
            output=output,
            compile_seconds=600,
        )
        binary = output / "oras"
        raw = binary.read_bytes()
        require(raw[:6] == b"\x7fELF\x02\x01" and raw[18:20] == b"\x3e\x00", "tool_amd64_ELF")
        report["binary"] = {"bytes": len(raw), "sha256": sha(raw)}
        buildinfo = finite_go(
            native,
            work,
            docker,
            config,
            env,
            source,
            go,
            modules,
            owned,
            "tool-buildinfo",
            ["version", "-m", "/output/oras"],
            output=output,
        )
        require(
            b"go1.27.2" in buildinfo
            and ORAS_COMMAND.encode() in buildinfo
            and b"\tbuild\tCGO_ENABLED=0" in buildinfo
            and b"\t=>\t" not in buildinfo,
            "tool_native_buildinfo",
        )
        for label, command in (("version", ["version"]), ("help", ["cp", "--help"])):
            raw = native.run([str(binary), *command], "ORAS-" + label, env, cwd=work)
            if label == "version":
                require(
                    b"1.3.4" in raw and ORAS_REVISION.encode() in raw and b"go1.27.2" in raw,
                    "tool_native_version",
                )
            else:
                require(
                    b"--from-oci-layout" in raw and b"--to-oci-layout" in raw,
                    "tool_native_copy_help",
                )
        vendor = work / "vendor"
        native.run(
            [str(binary), "cp", "--to-oci-layout", BASE, str(vendor) + ":base"],
            "ORAS-authenticated-base",
            env,
            cwd=work,
        )
        base = base_graph(vendor)
        files = {
            name: b"PulsePlate synthetic format probe only\n"
            for name in ("prometheus", "promtool", "prometheus.yml", "LICENSE", "NOTICE")
        }
        layout, archive = work / "format", work / "format.docker.tar"
        construct_image(base, files, layout, archive, synthetic=True)
        graph = validate_oci_graph(layout, base, synthetic=True)
        copied = work / "format-copy"
        native.run(
            [
                str(binary),
                "cp",
                "--from-oci-layout",
                "--to-oci-layout",
                str(layout) + "@" + graph["manifest_digest"],
                str(copied) + ":format-probe",
            ],
            "ORAS-local-format-copy",
            env,
            cwd=work,
        )
        compare_pair(graph, validate_oci_graph(copied, base, synthetic=True))
        report["native_format"] = native_import(
            native, work, docker, config, env, archive, graph, synthetic=True
        )
        report["native_scan"] = scan_tool(native, work, binary, env)
        require(
            tree_inventory(source) == before_source and tree_inventory(modules) == before_cache,
            "tool_readonly_inputs_changed",
        )
        require(
            all(file_hash(source / name) == value for name, value in ORAS_LOCKS.items()),
            "tool_original_locks_after",
        )
        report["status"] = "observed_tool_and_synthetic_format_only"
        destination = evidence / "oras"
        shutil.copyfile(binary, destination)
        destination.chmod(0o755)
        shutil.copyfile(source / "LICENSE", evidence / "LICENSE")
        pack_layout(vendor, evidence / "vendor.oci.tar")
    except BaseException as error:
        report["failure"] = {"class": type(error).__name__, "code": diagnostic_code(error)}
        raise
    finally:
        if native.cleanup_deadline is None:
            native.begin_cleanup()
        report["cleanup"] = cleanup_owned(native, docker, config, owned, env, work)
        report["native_commands"] = native.records
        (evidence / "tool.json").write_bytes(canonical_data(report))
    require(not any("failure" in row for row in report["cleanup"]), "tool_cleanup_failed")
    return report


def retained_tool(api: GitHubRead, root: Path, work: Path) -> tuple[Path, dict[str, Any]]:
    manifest = read_image_manifest(root / MANIFEST_PATH, preparation=True)
    coordinates = manifest["inputs"]["oras"]["retained"]
    require(coordinates is not None, "qualified_retained_tool_not_selected")
    archive = work / "tool-input.zip"
    authenticated = authenticated_artifact(
        api,
        coordinates["artifact_id"],
        archive,
        expected_run=coordinates["run_id"],
        expected_job="prometheus-oras-qualification",
        expected_head=coordinates["source_head"],
    )
    require(
        authenticated["artifact"].get("name") == coordinates["artifact_name"]
        and authenticated["artifact"].get("digest") == coordinates["artifact_digest"],
        "retained_tool_API_coordinates",
    )
    authenticate_producer_inputs(api, root, coordinates["source_head"], tool=True)
    files = _zip_members(archive)
    require(
        {"oras", "tool.json", "LICENSE", "vendor.oci.tar", "tool-full.raw.json"} <= set(files),
        "retained_tool_payload",
    )
    report = one_object(files["tool.json"])
    projection = tool_input_projection(root)
    require(
        report.get("status") == "observed_tool_and_synthetic_format_only"
        and report.get("failure") is None
        and report.get("tool_compile_invocations") == 1
        and type(report.get("tool_compile_invocations")) is int
        and report.get("Prometheus_compile_invocations") == 0
        and report.get("source_revision") == ORAS_REVISION
        and report.get("source_tree") == ORAS_TREE,
        "retained_tool_native_outcome",
    )
    exact_data(report.get("original_locks"), ORAS_LOCKS)
    exact_data(report.get("input_projection"), projection)
    require(
        report.get("input_digest")
        == coordinates["input_digest"]
        == "sha256:" + sha(canonical_data(projection)),
        "retained_tool_input_binding",
    )
    require(
        sha(files["oras"]) == coordinates["binary_sha256"]
        and len(files["oras"]) == coordinates["binary_bytes"]
        and report.get("binary") == {"bytes": len(files["oras"]), "sha256": sha(files["oras"])}
        and sha(files["LICENSE"]) == ORAS_LICENSE,
        "retained_tool_binary_license",
    )
    require(
        report.get("command_graph", {}).get("SSH_OpenPGP_paths") == []
        and report.get("native_format", {}).get("status") == "observed_synthetic_format_only"
        and report.get("native_scan", {}).get("report_sha256") == sha(files["tool-full.raw.json"]),
        "retained_tool_graph_format_scan_binding",
    )
    scan = report["native_scan"]
    inventory = tool_scan_inventory(files["tool-full.raw.json"], scan.get("subject"))
    for name, value in inventory.items():
        exact_data(scan.get(name), value)
    require(
        scan.get("binary_sha256") == coordinates["binary_sha256"]
        and type(scan.get("native_exit")) is int
        and scan["native_exit"] == 0
        and type(scan.get("scanner_sha256")) is str,
        "retained_tool_scan_subject_execution",
    )
    _digest("sha256:" + scan["scanner_sha256"])
    require(
        type(scan.get("DB")) is dict and set(scan["DB"]) == {"db/trivy.db", "db/metadata.json"},
        "retained_tool_scan_DB_inventory",
    )
    for value in scan["DB"].values():
        require(
            type(value) is dict
            and set(value) == {"bytes", "sha256"}
            and type(value["bytes"]) is int
            and value["bytes"] > 0,
            "retained_tool_scan_DB_type",
        )
        _digest("sha256:" + value["sha256"])
    exact_data(report.get("command_graph"), tool_packages(files["tool-packages-native.stdout"]))
    exact_data(
        report.get("full_modules"),
        decode_selected_modules(files["tool-modules-native.stdout"], root_module="oras.land/oras"),
    )
    require(
        all("Replace" not in row for row in report["full_modules"].values()),
        "retained_tool_original_module_graph",
    )
    commands = report.get("native_commands")
    require(
        type(commands) is list
        and bool(commands)
        and all(
            row.get("exit") == 0 and type(row.get("exit")) is int and row.get("failure") is None
            for row in commands
        )
        and type(report.get("cleanup")) is list
        and all(row.get("native_absent") is True for row in report["cleanup"]),
        "retained_tool_positive_native_predecessors",
    )
    commands = cast(list[dict[str, Any]], commands)
    scans = [row for row in commands if row.get("argv") == scan.get("native_argv")]
    require(
        len(scans) == 1
        and scans[0]["exit"] == scan["native_exit"]
        and type(scan["native_argv"]) is list
        and scan["native_argv"][-1] == scan["subject"]
        and "--scanners" in scan["native_argv"]
        and scan["native_argv"][scan["native_argv"].index("--scanners") + 1] == "vuln,secret",
        "retained_tool_exact_native_scan_command",
    )
    binary = work / "oras"
    with binary.open("xb") as output:
        output.write(files["oras"])
    binary.chmod(0o755)
    vendor = work / "vendor"
    unpack_layout(files["vendor.oci.tar"], vendor)
    base = base_graph(vendor)
    return binary, {
        "base": base,
        "vendor": vendor,
        "coordinates": coordinates,
        "report_sha256": sha(files["tool.json"]),
    }


def build_pair(work: Path, root: Path, seconds: int, cleanup: int) -> dict[str, Any]:
    require(
        type(seconds) is int
        and 0 < seconds <= 3600
        and type(cleanup) is int
        and 0 < cleanup <= 120,
        "Prometheus_pair_budget",
    )
    fresh_directory(work)
    evidence = work / "evidence"
    fresh_directory(evidence)
    preparatory = Native(evidence, time.monotonic() + 900, cleanup)
    manifest = read_image_manifest(root / MANIFEST_PATH, preparation=True)
    require(manifest["phase"] == "source_prepared", "pair_preparation_phase_only")
    api = GitHubRead(work / "GitHub-private", evidence, preparatory.deadline, cleanup)
    try:
        admission = manual_hosted_admission(api, "pair")
        authenticate_producer_inputs(api, root, admission["head"])
        tool, tool_record = retained_tool(api, root, work)
        qualification = work / "xnet-qualified-input.zip"
        authenticated_artifact(
            api,
            11664089525,
            qualification,
            expected_run=38037035815,
            expected_job="prometheus-source-qualification",
            expected_head="f0442f4fdf5f281730c4584f6352beac09cfd754",
        )
        derived = qualification_locks(qualification)
    finally:
        api.close()
    downloads = work / "downloads"
    fresh_directory(downloads)
    for artifact in (SOURCE, GO, UI, CHECKSUMS):
        acquire(artifact, downloads / artifact.name, preparatory.deadline)
    require(
        (downloads / "checksums")
        .read_text()
        .splitlines()
        .count(UI.digest + "  prometheus-web-ui-3.15.0.tar.gz")
        == 1,
        "pair_official_matching_UI",
    )
    go, ui = work / "go", work / "ui"
    extract(GO, downloads / "go", go, preparatory.deadline)
    extract(UI, downloads / "ui", ui, preparatory.deadline)
    require(file_hash(go / "LICENSE") == GO_LICENSE, "pair_Go_license")
    docker = shutil.which("docker")
    require(docker is not None and Path(docker).is_absolute(), "pair_Docker_missing")
    docker = cast(str, docker)
    config = work / "docker-config"
    fresh_directory(config)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "DOCKER_CONFIG": str(config),
        "LANG": "C.UTF-8",
    }
    preparatory.run(
        [docker, "--config", str(config), "pull", "--platform", "linux/amd64", BASE],
        "pair-base-pull",
        env,
        cwd=work,
    )
    report: dict[str, Any] = {
        "admission": admission,
        "source_revision": REVISION,
        "logical_build_invocations": 0,
        "binary_compile_starts": 0,
        "automatic_retries": 0,
        "qualification_input_zip_sha256": file_hash(qualification),
        "tool_sha256": file_hash(tool),
        "builds": [],
        "failure": None,
    }
    owned: dict[str, dict[str, Any]] = {}
    natives, graphs, projections = [], [], []
    cleanup_native = Native(evidence, time.monotonic() + 2 * seconds + 600, cleanup)
    try:
        require(
            sum(path.is_file() for path in evidence.rglob("*")) <= 3500,
            "pair_precompile_transport_member_reserve",
        )
        require(shutil.disk_usage(work).free >= 12 * 1024**3, "pair_hosted_free_space_reserve_HOLD")
        for label in ("a", "b"):
            started = time.monotonic()
            lane = work / label
            fresh_directory(lane)
            lane_evidence = evidence / label
            fresh_directory(lane_evidence)
            native = Native(lane_evidence, started + seconds, cleanup)
            natives.append(native)
            report["logical_build_invocations"] += 1
            (evidence / (label + "-invocation-start.json")).write_bytes(canonical_data(report))
            source = lane / "source"
            extract(SOURCE, downloads / "source", source, native.deadline)
            locks_unchanged(source)
            for name, raw in derived.items():
                (source / name).write_bytes(raw)
            transform = stage_ui(source, ui, native.deadline)
            require(
                (source / "VERSION").read_bytes() == b"3.15.0\n"
                and all(
                    file_hash(source / name) == value for name, value in SOURCE_LICENSES.items()
                ),
                "pair_authentic_source_licenses",
            )
            modules, module_record = prefetch_modules(
                native, lane, source, go, label, DERIVED_LOCKS
            )
            source_inventory, module_inventory = tree_inventory(source), tree_inventory(modules)
            observations, graph_hashes = {}, {}
            for binary in ("prometheus", "promtool"):
                raw = finite_go(
                    native,
                    lane,
                    docker,
                    config,
                    env,
                    source,
                    go,
                    modules,
                    owned,
                    label + "-" + binary + "-graph",
                    [
                        "list",
                        "-mod=readonly",
                        "-deps",
                        "-json",
                        "-tags=netgo,builtinassets",
                        "./cmd/" + binary,
                    ],
                )
                observations[binary] = decode_packages(raw, binary)
                graph_hashes[binary] = sha(raw)
            acquired = {
                "source": sha(canonical_data(source_inventory)),
                "go": GO.digest,
                "modules": module_record["inventory_sha256"],
                "UI_transform": transform,
                "tool_implementations": {
                    "oras_sha256": file_hash(tool),
                    "python_executable_sha256": file_hash(
                        Path(sys.executable).resolve(strict=True)
                    ),
                    "python_version": sys.version,
                    "zlib": zlib.ZLIB_RUNTIME_VERSION,
                },
            }
            projection = producer_projection(root, acquired)
            projections.append(projection)
            output = lane / "output"
            fresh_directory(output, 0o777)
            output.chmod(0o777)
            for name in ("tmp", "cache"):
                fresh_directory(output / name, 0o777)
                (output / name).chmod(0o777)
            for binary in ("prometheus", "promtool"):
                report["binary_compile_starts"] += 1
                (evidence / (label + "-" + binary + "-compile-start.json")).write_bytes(
                    canonical_data(report)
                )
                finite_go(
                    native,
                    lane,
                    docker,
                    config,
                    env,
                    source,
                    go,
                    modules,
                    owned,
                    label + "-" + binary + "-compile",
                    [
                        "build",
                        "-mod=readonly",
                        "-p=1",
                        "-trimpath",
                        "-buildvcs=false",
                        "-tags=netgo,builtinassets",
                        "-ldflags=" + PROMETHEUS_METADATA,
                        "-o",
                        "/output/" + binary,
                        "./cmd/" + binary,
                    ],
                    output=output,
                    compile_seconds=max(1, int(native.deadline - time.monotonic())),
                )
                finite_go(
                    native,
                    lane,
                    docker,
                    config,
                    env,
                    source,
                    go,
                    modules,
                    owned,
                    label + "-" + binary + "-buildinfo",
                    ["version", "-m", "/output/" + binary],
                    output=output,
                )
            require(
                tree_inventory(source) == source_inventory
                and tree_inventory(modules) == module_inventory
                and all(file_hash(source / name) == value for name, value in DERIVED_LOCKS.items()),
                "pair_readonly_compilation_inputs",
            )
            files = {name: (output / name).read_bytes() for name in ("prometheus", "promtool")}
            files.update(
                {
                    "prometheus.yml": (
                        source / "documentation/examples/prometheus.yml"
                    ).read_bytes(),
                    "LICENSE": (source / "LICENSE").read_bytes(),
                    "NOTICE": (source / "NOTICE").read_bytes(),
                }
            )
            layout, archive = lane / "image", lane / "image.docker.tar"
            result = construct_image(tool_record["base"], files, layout, archive)
            graph = validate_oci_graph(layout, tool_record["base"])
            validate_docker_archive(archive, graph)
            pack_layout(layout, lane / "image.oci.tar")
            check_deadline(native.deadline)
            graphs.append(graph)
            # A finished image and its complete raw observations survive a B failure.
            # Only the successful invocation's disposable compiler cache/tmp are removed.
            finite_go(
                native,
                lane,
                docker,
                config,
                env,
                source,
                go,
                modules,
                owned,
                label + "-compiler-cache-clean",
                ["clean", "-cache"],
                output=output,
            )
            removals = cleanup_owned(native, docker, config, owned, env, lane, cleaning=False)
            require(
                not any("failure" in row for row in removals), "logical_build_container_cleanup"
            )
            owned.clear()
            for scratch in (output / "cache", output / "tmp"):
                require(
                    scratch.parent == output
                    and scratch.name in ("cache", "tmp")
                    and not scratch.is_symlink(),
                    "compile_scratch_exact_path",
                )
                shutil.rmtree(scratch)
                require(
                    not scratch.exists() and not scratch.is_symlink(), "compile_scratch_survives"
                )
            for name in ("image.oci.tar", "image.docker.tar"):
                os.rename(lane / name, lane_evidence / name)
            check_deadline(native.deadline)
            report["builds"].append(
                {
                    "label": label,
                    "logical_build_elapsed_seconds": time.monotonic() - started,
                    "outputs": result,
                    "OCI_archive_sha256": file_hash(lane_evidence / "image.oci.tar"),
                    "index_sha256": file_hash(layout / "index.json"),
                    "graph_sha256": graph_hashes,
                    "command_graphs": observations,
                    "input_digest": sha(canonical_data(projection)),
                    "cleanup": removals,
                    "compile_cache_tmp_absent": True,
                    "growth_check": "Periodic size/free-space observation with a stop threshold; not filesystem quota enforcement",
                }
            )
        require(
            report["logical_build_invocations"] == 2 and report["binary_compile_starts"] == 4,
            "exact_two_logical_builds_both_commands",
        )
        compare_pair(graphs[0], graphs[1])
        exact_data(projections[0], projections[1])
        for key in ("OCI_archive_sha256", "index_sha256", "graph_sha256"):
            exact_data(report["builds"][0][key], report["builds"][1][key])
        require(
            file_hash(evidence / "a/image.docker.tar")
            == file_hash(evidence / "b/image.docker.tar"),
            "pair_Docker_archives_byte_equal",
        )
        for label, graph in zip(("a", "b"), graphs, strict=True):
            observation = Native(evidence / label, time.monotonic() + 300, cleanup)
            natives.append(observation)
            native_started = time.monotonic()
            report["builds"][0 if label == "a" else 1]["native_import"] = native_import(
                observation,
                work / label,
                docker,
                config,
                env,
                evidence / label / "image.docker.tar",
                graph,
                synthetic=False,
            )
            check_deadline(observation.deadline)
            report["builds"][0 if label == "a" else 1]["post_build_native_elapsed_seconds"] = (
                time.monotonic() - native_started
            )
        selection = selection_from_graph(graphs[0])
        report["selection"] = selection
        report["input_projection"] = projections[0]
        report["input_projection_sha256"] = sha(canonical_data(projections[0]))
        report["raw_producer"] = projections[0]["raw_producer"]
        for name in ("image.oci.tar", "image.docker.tar"):
            os.rename(evidence / "a" / name, evidence / name)
        report["status"] = "observed_equal_real_source_pair"
    except BaseException as error:
        report["failure"] = {"class": type(error).__name__, "code": diagnostic_code(error)}
        raise
    finally:
        previous_cleanup = [
            native.cleanup_deadline for native in natives if native.cleanup_deadline is not None
        ]
        if previous_cleanup:
            cleanup_native.cleanup_deadline = min(previous_cleanup)
        else:
            cleanup_native.begin_cleanup()
        report["cleanup"] = cleanup_owned(cleanup_native, docker, config, owned, env, work)
        report["native_commands"] = (
            preparatory.records
            + [row for native in natives for row in native.records]
            + cleanup_native.records
        )
        (evidence / "pair.json").write_bytes(canonical_data(report))
    require(not any("failure" in row for row in report["cleanup"]), "pair_cleanup_failed")
    native_report = {
        "selection": report["selection"],
        "native_imports": [row["native_import"] for row in report["builds"]],
    }
    (evidence / "native.json").write_bytes(canonical_data(native_report))
    return report


def candidate_payload(api: GitHubRead, root: Path, work: Path) -> dict[str, Any]:
    manifest = read_image_manifest(root / MANIFEST_PATH)
    candidate, selection = manifest["candidate"], manifest["selection"]
    producer, coordinates = candidate["producer"], candidate["artifact"]
    archive = work / "candidate.zip"
    authenticated = authenticated_artifact(
        api,
        coordinates["id"],
        archive,
        expected_run=producer["run_id"],
        expected_job="prometheus-source-build-pair",
        expected_head=producer["source_head"],
    )
    observed = authenticated["artifact"]
    require(
        observed.get("name") == coordinates["name"]
        and observed.get("digest") == coordinates["digest"]
        and observed.get("size_in_bytes") == coordinates["size"]
        and observed.get("expires_at") == coordinates["expires_at"]
        and authenticated["workflow"].get("id") == producer["workflow_id"]
        and [authenticated["job"].get("id")] == producer["job_ids"],
        "candidate_native_API_coordinates",
    )
    require(file_hash(archive) == coordinates["archive_sha256"], "candidate_transport_SHA")
    authenticate_producer_inputs(api, root, producer["source_head"])
    files = _zip_members(archive)
    required = {
        "image.oci.tar",
        "image.docker.tar",
        "pair.json",
        "native.json",
        "sbom.spdx.json",
        "provenance-bundle.jsonl",
        "sbom-bundle.jsonl",
    }
    require(required <= set(files), "candidate_complete_retained_payload")
    mapping = {
        "image.oci.tar": "oci_archive_sha256",
        "image.docker.tar": "docker_archive_sha256",
        "pair.json": "pair_report_sha256",
        "native.json": "native_report_sha256",
        "sbom.spdx.json": "spdx_sha256",
        "provenance-bundle.jsonl": "provenance_bundle_sha256",
        "sbom-bundle.jsonl": "sbom_bundle_sha256",
    }
    require(
        all(sha(files[name]) == candidate["outputs"][key] for name, key in mapping.items()),
        "candidate_all_output_hashes",
    )
    report = one_object(files["pair.json"])
    require(
        report.get("status") == "observed_equal_real_source_pair"
        and report.get("failure") is None
        and report.get("logical_build_invocations") == 2
        and type(report.get("logical_build_invocations")) is int
        and report.get("binary_compile_starts") == 4
        and type(report.get("binary_compile_starts")) is int
        and report.get("automatic_retries") == 0
        and type(report.get("automatic_retries")) is int,
        "candidate_exact_pair_outcome",
    )
    exact_data(report.get("selection"), selection)
    exact_data(report.get("raw_producer"), producer["raw_producer"])
    projection = report.get("input_projection")
    require(
        type(projection) is dict
        and projection.get("inputs") == manifest["inputs"]
        and projection.get("raw_producer") == producer["raw_producer"]
        and report.get("input_projection_sha256")
        == producer["input_projection_sha256"]
        == sha(canonical_data(projection)),
        "candidate_projection_positive_equivalence",
    )
    projection = cast(dict[str, Any], projection)
    exact_data(projection, producer_projection(root, projection.get("acquired")))
    exact_data(report.get("admission", {}).get("head"), producer["source_head"])
    exact_data(report["admission"].get("ref"), producer["source_ref"])
    exact_data(report["admission"].get("run_id"), producer["run_id"])
    exact_data(report["admission"].get("workflow_id"), producer["workflow_id"])
    require(
        type(report.get("builds")) is list
        and len(report["builds"]) == 2
        and [row.get("label") for row in report["builds"]] == ["a", "b"],
        "candidate_both_observed_builds",
    )
    for row in report["builds"]:
        require(
            type(row.get("logical_build_elapsed_seconds")) in (float, int)
            and 0 < row["logical_build_elapsed_seconds"] <= 3600
            and type(row.get("post_build_native_elapsed_seconds")) in (float, int)
            and 0 < row["post_build_native_elapsed_seconds"] <= 300
            and row.get("input_digest") == producer["input_projection_sha256"]
            and row.get("native_import", {}).get("status") == "observed_real_native_import"
            and row["native_import"].get("image_config_id") == selection["config_digest"],
            "candidate_native_build_bound",
        )
    for key in (
        "outputs",
        "OCI_archive_sha256",
        "index_sha256",
        "graph_sha256",
        "command_graphs",
        "input_digest",
    ):
        exact_data(report["builds"][0][key], report["builds"][1][key])
    require(
        type(report.get("native_commands")) is list
        and bool(report["native_commands"])
        and all(
            row.get("exit") == 0 and type(row.get("exit")) is int and row.get("failure") is None
            for row in report["native_commands"]
        )
        and type(report.get("cleanup")) is list
        and all(row.get("native_absent") is True for row in report["cleanup"]),
        "candidate_positive_native_cleanup",
    )
    spdx = one_object(files["sbom.spdx.json"])
    require(
        spdx.get("spdxVersion") == "SPDX-2.3"
        and type(spdx.get("packages")) is list
        and bool(spdx["packages"]),
        "candidate_real_SPDX_inventory",
    )
    payload = work / "candidate"
    fresh_directory(payload)
    for name in required:
        with (payload / name).open("xb") as output:
            output.write(files[name])
        (payload / name).chmod(0o600)
    # The base comes from the independently retained, already qualified tool input.
    tool, tool_record = retained_tool(api, root, work)
    layout = payload / "oci"
    unpack_layout(files["image.oci.tar"], layout)
    graph = validate_oci_graph(layout, tool_record["base"])
    validate_docker_archive(payload / "image.docker.tar", graph)
    exact_data(selection_from_graph(graph), selection)
    native = one_object(files["native.json"])
    exact_data(native.get("selection"), selection)
    exact_data(native.get("native_imports"), [row["native_import"] for row in report["builds"]])
    return {
        "selection": selection,
        "layout": layout,
        "docker_archive": payload / "image.docker.tar",
        "graph": graph,
        "tool": tool,
        "tool_record": tool_record,
        "pair": report,
        "payload": payload,
        "authenticated": authenticated,
    }


def native_image_contract(image: Any, selection: dict[str, Any], *, local: bool = False) -> None:
    validate_selection(selection)
    require(
        type(image) is dict
        and image.get("Id") == selection["config_digest"]
        and (image.get("Os"), image.get("Architecture")) == ("linux", "amd64")
        and image.get("RootFS", {}).get("Layers") == selection["diff_ids"],
        "consumer_native_config_layers",
    )
    config = image.get("Config")
    require(
        type(config) is dict
        and config.get("User") == "65532:65532"
        and config.get("Entrypoint") == ["/bin/prometheus"]
        and config.get("WorkingDir") == "/prometheus"
        and config.get("Cmd")
        == ["--config.file=/etc/prometheus/prometheus.yml", "--storage.tsdb.path=/prometheus"]
        and config.get("Volumes") in (None, {}),
        "consumer_native_runtime_contract",
    )
    if not local:
        require(
            type(image.get("RepoDigests")) is list
            and selection["runtime_ref"] in image["RepoDigests"],
            "consumer_published_immutable_subject",
        )


def consume_image(work: Path, root: Path, seconds: int, cleanup: int) -> dict[str, Any]:
    require(
        type(seconds) is int
        and 0 < seconds <= 1800
        and type(cleanup) is int
        and 0 < cleanup <= 120,
        "consumer_budget",
    )
    fresh_directory(work)
    evidence = work / "evidence"
    fresh_directory(evidence)
    native = Native(evidence, time.monotonic() + seconds, cleanup)
    event = one_object(Path(os.environ["GITHUB_EVENT_PATH"]).read_bytes())
    head = (
        event["pull_request"]["head"]["sha"]
        if os.environ["GITHUB_EVENT_NAME"] == "pull_request"
        else os.environ["GITHUB_SHA"]
    )
    selection = read_image_manifest(root / MANIFEST_PATH)["selection"]
    docker = shutil.which("docker")
    require(docker is not None and Path(docker).is_absolute(), "consumer_native_Docker_missing")
    docker = cast(str, docker)
    config = work / "docker-config"
    fresh_directory(config)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "DOCKER_CONFIG": str(config),
        "LANG": "C.UTF-8",
    }
    api = GitHubRead(work / "GitHub-private", evidence, native.deadline, cleanup)
    payload = None
    reader: Path | None = None
    reader_identity: tuple[int, int] | None = None
    primary: BaseException | None = None
    cleanup_error: BaseException | None = None
    try:
        admission = event_admission(api, root, event, os.environ["GITHUB_EVENT_NAME"], head)
        if admission["mode"] == "changed_pr_candidate":
            payload = candidate_payload(api, root, work)
        else:
            # No registry availability probe can substitute for a positive publisher.
            while True:
                try:
                    admission["publication_predecessor"] = require_publication_predecessor(
                        api, admission["publisher_head"]
                    )
                    break
                except QualificationError as error:
                    require(
                        str(error) == "positive_publication_predecessor_pending_or_missing",
                        "publication_read_failed",
                    )
                    check_deadline(native.deadline)
                    time.sleep(min(5, max(0, native.deadline - time.monotonic())))
            identity, versions = existing_public_package(api)
            tag = "prometheus-3.15.0-" + selection["manifest_digest"][7:]
            require(
                immutable_tag_state(versions, tag, selection["manifest_digest"]),
                "consumer_published_subject_missing",
            )
            admission["public_package"] = identity
            token = os.environ.get("GHCR_READ_TOKEN")
            if not isinstance(token, str) or not token:
                raise QualificationError("consumer_registry_token_missing")
            owner = os.environ.get("GITHUB_REPOSITORY_OWNER")
            require(
                isinstance(owner, str) and owner.lower() == GHCR_OWNER.lower(),
                "consumer_registry_owner",
            )
            owner = cast(str, owner)
            runner = Path(os.environ["RUNNER_TEMP"])
            real_directory(runner)
            name = (
                "prometheus-consumer-auth-"
                + os.environ["GITHUB_RUN_ID"]
                + "-"
                + os.environ["GITHUB_RUN_ATTEMPT"]
            )
            reader = runner / name
            require(
                reader.parent == runner and reader.name == name, "consumer_owned_registry_config"
            )
            fresh_directory(reader)
            info = reader.lstat()
            reader_identity = (info.st_dev, info.st_ino)
            published_env = {**env, "HOME": str(api.private / "home"), "DOCKER_CONFIG": str(reader)}
            api._capture(
                [
                    docker,
                    "--config",
                    str(reader),
                    "login",
                    "ghcr.io",
                    "--username",
                    owner,
                    "--password-stdin",
                ],
                MAX_NATIVE_OUTPUT,
                environment=published_env,
                input_data=token.encode() + b"\n",
            )
            credential = reader / "config.json"
            info = credential.lstat()
            require(
                {path.name for path in reader.iterdir()} == {"config.json"}
                and stat.S_ISREG(info.st_mode)
                and info.st_uid == os.getuid()
                and info.st_nlink == 1
                and stat.S_IMODE(info.st_mode) == 0o600,
                "consumer_credential_leaf",
            )
            api._capture(
                [
                    docker,
                    "--config",
                    str(reader),
                    "pull",
                    "--platform",
                    "linux/amd64",
                    selection["runtime_ref"],
                ],
                MAX_NATIVE_OUTPUT,
                environment=published_env,
            )
            raw = api._capture(
                [
                    docker,
                    "--config",
                    str(reader),
                    "buildx",
                    "imagetools",
                    "inspect",
                    "--raw",
                    selection["runtime_ref"],
                ],
                1024**2,
                environment=published_env,
            )
            require("sha256:" + sha(raw) == selection["manifest_digest"], "published_raw_OCI_root")
            observed_root = one_object(raw)
            descriptor = _descriptor(observed_root.get("config"), OCI_CONFIG)
            require(
                descriptor["digest"] == selection["config_digest"], "published_config_descriptor"
            )
            exact_data(
                observed_root,
                {
                    "schemaVersion": 2,
                    "mediaType": OCI_MANIFEST,
                    "config": descriptor,
                    "layers": selection["layers"],
                },
            )
    except BaseException as error:
        primary = error
    finally:
        try:
            api.close()
            if reader is not None:
                check_deadline(api.begin_cleanup())
                info = reader.lstat()
                require(
                    stat.S_ISDIR(info.st_mode)
                    and info.st_uid == os.getuid()
                    and stat.S_IMODE(info.st_mode) == 0o700
                    and (info.st_dev, info.st_ino) == reader_identity,
                    "consumer_credential_directory_identity",
                )
                require(
                    {path.name for path in reader.iterdir()} in ({"config.json"}, set()),
                    "consumer_credential_members",
                )
                credential = reader / "config.json"
                if credential.exists() or credential.is_symlink():
                    info = credential.lstat()
                    require(
                        stat.S_ISREG(info.st_mode)
                        and info.st_uid == os.getuid()
                        and info.st_nlink == 1
                        and stat.S_IMODE(info.st_mode) == 0o600,
                        "consumer_credential_cleanup_leaf",
                    )
                    credential.unlink()
                reader.rmdir()
                require(
                    not reader.exists() and not reader.is_symlink(),
                    "consumer_credential_cleanup_absence",
                )
        except BaseException as error:
            cleanup_error = error
    if primary is not None:
        if cleanup_error is not None:
            print(
                "Consumer cleanup also failed:"
                + (diagnostic_code(cleanup_error) or type(cleanup_error).__name__),
                file=sys.stderr,
            )
        raise primary
    if cleanup_error is not None:
        raise cleanup_error
    if admission["mode"] == "changed_pr_candidate":
        component = consumer_result(admission["mode"], "success", "skipped")
    elif admission["mode"] == "new_main_selection":
        component = consumer_result(admission["mode"], "success", "success")
    else:
        component = consumer_result(admission["mode"], "skipped", "skipped")
    if payload is not None:
        native.run(
            [docker, "--config", str(config), "load", "--input", str(payload["docker_archive"])],
            "candidate-load",
            env,
            cwd=work,
        )
        runtime = selection["config_digest"]
    else:
        runtime = selection["runtime_ref"]
    image = one_object(
        native.run(
            [
                docker,
                "--config",
                str(config),
                "image",
                "inspect",
                "--format",
                "{{json .}}",
                runtime,
            ],
            "consumer-native-image",
            env,
            cwd=work,
        )
    )
    native_image_contract(image, selection, local=payload is not None)
    result = {
        "admission": admission,
        "component_consumption": component,
        "selection": selection,
        "runtime_ref": runtime,
        "native_image": image,
        "native_commands": native.records,
        "boundary": "Image admission only; existing promtool/runtime/security checks remain mandatory",
    }
    (evidence / "consumer.json").write_bytes(canonical_data(result))
    return result


def existing_public_package(api: GitHubRead) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    repository = api.json("/repos/" + GHCR_REPOSITORY)
    endpoint = GHCR_REQUESTS[1]
    package = one_object(
        api._capture(
            [api.gh, "api", "--hostname", "github.com", "--method", "GET", endpoint], 1024**2
        )
    )
    identity = ghcr_identity(repository, package)
    require(
        identity["repository"]["id"] == 1043311030
        and identity["owner"]["id"] == 169792616
        and identity["package"]["id"] == 9374404,
        "existing_public_package_exact_IDs",
    )
    versions = []
    for page in range(1, 101):
        raw = api._capture(
            [
                api.gh,
                "api",
                "--hostname",
                "github.com",
                "--method",
                "GET",
                endpoint + f"/versions?per_page=100&page={page}",
            ],
            16 * 1024**2,
        )
        values = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
        require(
            type(values) is list
            and len(values) <= 100
            and all(
                type(row) is dict and type(row.get("id")) is int and row["id"] > 0 for row in values
            ),
            "package_native_versions",
        )
        versions.extend(values)
        require(
            len({row["id"] for row in versions}) == len(versions), "package_pagination_distinct"
        )
        if len(values) < 100:
            return identity, versions
    raise QualificationError("package_complete_inventory_bound")


def immutable_tag_state(versions: list[dict[str, Any]], tag: str, digest: str) -> bool:
    matches = []
    for version in versions:
        tags = version.get("metadata", {}).get("container", {}).get("tags")
        require(
            type(tags) is list and all(type(value) is str for value in tags),
            "package_native_tag_inventory",
        )
        if tag in tags:
            matches.append(version)
    require(
        len(matches) <= 1 and all(row.get("name") == digest for row in matches),
        "immutable_tag_existing_other_subject_HOLD",
    )
    return bool(matches)


def promote_image(work: Path, root: Path, seconds: int, cleanup: int) -> dict[str, Any]:
    require(
        type(seconds) is int
        and 0 < seconds <= 1800
        and type(cleanup) is int
        and 0 < cleanup <= 120
        and os.environ.get("GITHUB_EVENT_NAME") == "push"
        and os.environ.get("GITHUB_REF") == "refs/heads/main"
        and os.environ.get("GITHUB_REPOSITORY") == GHCR_REPOSITORY
        and os.environ.get("GITHUB_REPOSITORY_ID") == "1043311030",
        "main_only_promotion",
    )
    fresh_directory(work)
    evidence = work / "evidence"
    fresh_directory(evidence)
    api = GitHubRead(work / "GitHub-private", evidence, time.monotonic() + seconds, cleanup)
    config: Path | None = None
    config_identity: tuple[int, int] | None = None
    primary: BaseException | None = None
    cleanup_error: BaseException | None = None
    result: dict[str, Any] | None = None
    try:
        event = one_object(Path(os.environ["GITHUB_EVENT_PATH"]).read_bytes())
        head = os.environ["GITHUB_SHA"]
        admission = event_admission(api, root, event, "push", head)
        require(
            admission["mode"] in ("new_main_selection", "unchanged_published"),
            "publisher_event_table",
        )
        endpoint = f'/repos/{GHCR_REPOSITORY}/actions/runs/{os.environ["GITHUB_RUN_ID"]}/attempts/{os.environ["GITHUB_RUN_ATTEMPT"]}/jobs'
        page = api.json(endpoint + "?per_page=100&page=1")
        jobs = api.pages(endpoint, "jobs", page["total_count"])
        for name in ("build", "security-scan"):
            required = [row for row in jobs if row.get("name") == name]
            require(
                len(required) == 1
                and required[0].get("head_sha") == head
                and required[0].get("conclusion") == "success"
                and required[0].get("status") == "completed",
                "publisher_positive_build_security_predecessors",
            )
        manifest = read_image_manifest(root / MANIFEST_PATH)
        selection = manifest["selection"]
        candidate = None
        predecessor = None
        if admission["mode"] == "new_main_selection":
            # Complete source, artifact, tool, native/scanner and input admission
            # before creating or logging in to any registry-writer directory.
            candidate = candidate_payload(api, root, work)
            tool = candidate["tool"]
            expected_tool = candidate["tool_record"]["coordinates"]["binary_sha256"]
            require(file_hash(tool) == expected_tool, "publisher_retained_tool_changed")
        else:
            predecessor = require_publication_predecessor(api, event["before"])
        identity, before = existing_public_package(api)
        tag = "prometheus-3.15.0-" + selection["manifest_digest"][7:]
        present = immutable_tag_state(before, tag, selection["manifest_digest"])
        if candidate is None:
            require(present, "unchanged_published_subject_missing")
        docker = shutil.which("docker")
        require(docker is not None and Path(docker).is_absolute(), "publisher_Docker_missing")
        docker = cast(str, docker)
        owner = os.environ.get("GITHUB_REPOSITORY_OWNER")
        if not isinstance(owner, str) or owner.lower() != GHCR_OWNER.lower():
            raise QualificationError("publisher_registry_owner")
        current = api.json(f"/repos/{GHCR_REPOSITORY}/git/ref/heads/main")
        require(current.get("object", {}).get("sha") == head, "publisher_main_before_credentials")
        result = {
            "head": head,
            "admission": admission,
            "package": identity,
            "selection": selection,
            "tag": tag,
            "copy_invocations": 0,
            "compile_invocations": 0,
            "verify_retained_bundles": candidate is not None,
            "provenance": "Original same-repository PR producer; main copies retained bytes without rebuilding",
        }
        # Registry credentials activate only after the complete admission above.
        runner = Path(os.environ["RUNNER_TEMP"])
        real_directory(runner)
        name = (
            "prometheus-publisher-auth-"
            + os.environ["GITHUB_RUN_ID"]
            + "-"
            + os.environ["GITHUB_RUN_ATTEMPT"]
        )
        config = runner / name
        require(
            config.parent == runner and config.name == name, "publisher_owned_credential_directory"
        )
        fresh_directory(config)
        directory = config.lstat()
        config_identity = (directory.st_dev, directory.st_ino)
        credential = config / "config.json"
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(api.private / "home"),
            "DOCKER_CONFIG": str(config),
            "LANG": "C.UTF-8",
        }
        writer_token = os.environ.get("GITHUB_TOKEN")
        if not isinstance(writer_token, str) or not writer_token:
            raise QualificationError("publisher_registry_token_missing")
        api._capture(
            [
                docker,
                "--config",
                str(config),
                "login",
                "ghcr.io",
                "--username",
                owner,
                "--password-stdin",
            ],
            2 * 1024**2,
            environment=env,
            input_data=writer_token.encode() + b"\n",
        )
        info = credential.lstat()
        require(
            {path.name for path in config.iterdir()} == {"config.json"}
            and stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and info.st_nlink == 1
            and stat.S_IMODE(info.st_mode) == 0o600,
            "publisher_credential_leaf",
        )
        if candidate is not None:
            if not present:
                current = api.json(f"/repos/{GHCR_REPOSITORY}/git/ref/heads/main")
                require(current.get("object", {}).get("sha") == head, "publisher_main_before_write")
                api._capture(
                    [
                        str(tool),
                        "cp",
                        "--registry-config",
                        str(credential),
                        "--from-oci-layout",
                        str(candidate["layout"]) + "@" + selection["manifest_digest"],
                        IMAGE_REPOSITORY + ":" + tag,
                    ],
                    2 * 1024**2,
                    environment=env,
                )
                result["copy_invocations"] = 1
            pullback = work / "pullback"
            api._capture(
                [
                    str(tool),
                    "cp",
                    "--registry-config",
                    str(credential),
                    "--to-oci-layout",
                    selection["runtime_ref"],
                    str(pullback) + ":pullback",
                ],
                2 * 1024**2,
                environment=env,
            )
            graph = validate_oci_graph(pullback, candidate["tool_record"]["base"])
            compare_pair(candidate["graph"], graph)
            pack_layout(pullback, evidence / "published-pullback.oci.tar")
            result["pullback_SHA256"] = file_hash(evidence / "published-pullback.oci.tar")
            original = manifest["candidate"]["producer"]
            result["original_producer"] = original
            for filename in ("sbom.spdx.json", "provenance-bundle.jsonl", "sbom-bundle.jsonl"):
                shutil.copyfile(candidate["payload"] / filename, evidence / filename)
            # OCI verification still needs this authenticated registry lifetime.
            # Verify retained original PR bundles, never an API-only attestation lookup.
            for bundle, output, predicate in (
                ("provenance-bundle.jsonl", "original-provenance-verification.json", None),
                (
                    "sbom-bundle.jsonl",
                    "original-sbom-verification.json",
                    "https://spdx.dev/Document/v2.3",
                ),
            ):
                argv = [
                    api.gh,
                    "attestation",
                    "verify",
                    "oci://" + selection["runtime_ref"],
                    "--repo",
                    GHCR_REPOSITORY,
                    "--bundle",
                    str(evidence / bundle),
                    "--signer-workflow",
                    GHCR_REPOSITORY + "/.github/workflows/build.yml",
                    "--source-digest",
                    original["source_head"],
                    "--source-ref",
                    original["source_ref"],
                ]
                if predicate is not None:
                    argv += ["--predicate-type", predicate]
                argv += ["--deny-self-hosted-runners", "--format", "json"]
                verified = api._capture(
                    argv,
                    16 * 1024**2,
                    environment={**api.environment, "DOCKER_CONFIG": str(config)},
                )
                (evidence / output).write_bytes(verified)
        else:
            result["publication_predecessor"] = predecessor
            raw = api._capture(
                [
                    docker,
                    "--config",
                    str(config),
                    "buildx",
                    "imagetools",
                    "inspect",
                    "--raw",
                    selection["runtime_ref"],
                ],
                1024**2,
                environment=env,
            )
            require(
                "sha256:" + sha(raw) == selection["manifest_digest"],
                "unchanged_published_raw_digest",
            )
        after_identity, after = existing_public_package(api)
        exact_data(after_identity, identity)
        require(
            immutable_tag_state(after, tag, selection["manifest_digest"]),
            "published_existing_package_readback",
        )
        current = api.json(f"/repos/{GHCR_REPOSITORY}/git/ref/heads/main")
        require(current.get("object", {}).get("sha") == head, "publisher_main_after_write")
        result["status"] = "observed_published_exact_immutable_subject"
        (evidence / "publication.json").write_bytes(canonical_data(result))
    except BaseException as error:
        primary = error
    finally:
        try:
            # A failed/uncertain group check retains BOTH private auth directories.
            api.close()
            if config is not None:
                check_deadline(api.begin_cleanup())
                directory = config.lstat()
                require(
                    stat.S_ISDIR(directory.st_mode)
                    and directory.st_uid == os.getuid()
                    and stat.S_IMODE(directory.st_mode) == 0o700
                    and (directory.st_dev, directory.st_ino) == config_identity,
                    "publisher_credential_directory_identity",
                )
                require(
                    {path.name for path in config.iterdir()} in ({"config.json"}, set()),
                    "publisher_credential_members",
                )
                credential = config / "config.json"
                if credential.exists() or credential.is_symlink():
                    info = credential.lstat()
                    require(
                        stat.S_ISREG(info.st_mode)
                        and info.st_uid == os.getuid()
                        and info.st_nlink == 1
                        and stat.S_IMODE(info.st_mode) == 0o600,
                        "publisher_credential_cleanup_leaf",
                    )
                    credential.unlink()
                config.rmdir()
                require(
                    not config.exists() and not config.is_symlink(),
                    "publisher_credential_cleanup_absence",
                )
        except BaseException as error:
            cleanup_error = error
    if primary is not None:
        if cleanup_error is not None:
            print(
                "Publisher cleanup also failed:"
                + (diagnostic_code(cleanup_error) or type(cleanup_error).__name__),
                file=sys.stderr,
            )
        raise primary
    if cleanup_error is not None:
        raise cleanup_error
    require(result is not None, "publisher_result_missing")
    return cast(dict[str, Any], result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--operation",
        choices=(
            "metadata",
            "tool",
            "pair",
            "consume",
            "promote",
            "read-manifest",
            "inspect-image",
        ),
        default="metadata",
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--field", choices=("runtime_ref", "selection"), default="selection")
    parser.add_argument("--derive-xnet060", action="store_true")
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--timeout-seconds", type=int)
    parser.add_argument("--cleanup-seconds", type=int)
    parser.add_argument("--qualify-existing-ghcr-package", action="store_true")
    parser.add_argument("--public-output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve(strict=True).parents[2]
    manifest_path = args.manifest if args.manifest is not None else root / MANIFEST_PATH
    if args.operation != "metadata" and (
        args.derive_xnet060 or args.qualify_existing_ghcr_package or args.public_output is not None
    ):
        parser.error("Native producer/consumer operations cannot combine with metadata selectors")
    if args.operation not in ("read-manifest", "inspect-image") and (
        args.work_dir is None or args.timeout_seconds is None or args.cleanup_seconds is None
    ):
        parser.error(
            "An owned work directory, operation deadline and cleanup deadline are required"
        )
    if args.derive_xnet060 and (
        args.qualify_existing_ghcr_package or args.public_output is not None
    ):
        parser.error("Module derivation cannot combine with GHCR/public output")
    if args.qualify_existing_ghcr_package != (args.public_output is not None):
        parser.error("GHCR selector and public output are required together")
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    try:
        if args.operation in ("read-manifest", "inspect-image"):
            manifest = read_image_manifest(manifest_path)
            if args.operation == "inspect-image":
                raw = sys.stdin.buffer.read(1024**2 + 1)
                require(0 < len(raw) <= 1024**2, "native_inspect_input_bound")
                images = json.loads(
                    raw, object_pairs_hook=unique_object, parse_constant=reject_constant
                )
                require(type(images) is list and len(images) == 1, "native_inspect_one_image")
                native_image_contract(images[0], manifest["selection"])
            elif args.field == "runtime_ref":
                print(manifest["selection"]["runtime_ref"])
            else:
                print(canonical_data(manifest["selection"]).decode())
            return 0
        result = None
        if args.operation == "tool":
            result = qualify_tool(args.work_dir, root, args.timeout_seconds, args.cleanup_seconds)
        elif args.operation == "pair":
            result = build_pair(args.work_dir, root, args.timeout_seconds, args.cleanup_seconds)
        elif args.operation == "consume":
            result = consume_image(args.work_dir, root, args.timeout_seconds, args.cleanup_seconds)
        elif args.operation == "promote":
            result = promote_image(args.work_dir, root, args.timeout_seconds, args.cleanup_seconds)
        elif args.qualify_existing_ghcr_package:
            qualify_existing_ghcr_package(
                args.work_dir, args.public_output, args.timeout_seconds, args.cleanup_seconds
            )
        elif args.operation == "metadata":
            if args.derive_xnet060:
                qualify(
                    args.work_dir, args.timeout_seconds, args.cleanup_seconds, derive_xnet060=True
                )
            else:
                qualify(args.work_dir, args.timeout_seconds, args.cleanup_seconds)
        if result is not None and os.environ.get("GITHUB_OUTPUT"):
            outputs = {}
            if args.operation == "tool":
                outputs = {
                    "binary_sha256": result["binary"]["sha256"],
                    "binary_bytes": result["binary"]["bytes"],
                    "input_digest": result["input_digest"],
                }
            elif args.operation in ("pair", "consume", "promote"):
                selection = result["selection"]
                outputs = {
                    "manifest_digest": selection["manifest_digest"],
                    "config_digest": selection["config_digest"],
                    "source_revision": selection["source_revision"],
                    "runtime_ref": result.get("runtime_ref", selection["runtime_ref"]),
                }
                if args.operation == "promote":
                    original = read_image_manifest(root / MANIFEST_PATH)["candidate"]["producer"]
                    outputs.update(
                        source_head=original["source_head"],
                        source_ref=original["source_ref"],
                        original_run_id=original["run_id"],
                        verify_retained_bundles=str(result["verify_retained_bundles"]).lower(),
                    )
            with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
                for key, value in outputs.items():
                    require(
                        "\n" not in str(value) and "\r" not in str(value),
                        "native_output_single_line",
                    )
                    output.write(key + "=" + str(value) + "\n")
    except (Exception, KeyboardInterrupt) as error:
        code = diagnostic_code(error)
        print(
            "Prometheus qualification failed: "
            + type(error).__name__
            + (":" + code if code else ""),
            file=sys.stderr,
        )
        return 1
    print(
        "Finite operation observed; downstream readiness and publication gates remain separate."
        if args.operation != "metadata"
        else (
            "Existing GHCR identity observed."
            if args.qualify_existing_ghcr_package
            else "Prometheus package metadata captured; advisory and binary review pending."
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
