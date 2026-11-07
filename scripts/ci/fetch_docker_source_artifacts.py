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
from fractions import Fraction
from hashlib import sha1, sha256, sha3_256
import io
import json
from math import nextafter
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
    from zipfile import ZipFile, ZipInfo
    from scripts.ci.prometheus_source_image import GitHubRead, Native
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPO_ROOT = (
    Path("/")
    if any(
        flag in sys.argv[1:]
        for flag in ("--alertmanager-contract", "--alertmanager-contract-collect")
    )
    else Path(__file__).resolve().parents[2]
)
DEFAULT_MANIFEST = REPO_ROOT / "scripts" / "ci" / "docker_source_artifacts.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build" / "docker-sources"
ALLOWED_SOURCE_HOSTS = frozenset({"sqlite.org", "www.sqlite.org", "www.kernel.org"})
_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

# One observed successful metadata epoch; these selectors grant no compiler authority.
_ALERT_Q_SOURCE = "36cd171c4ebe44f63cb58d09a741b3d07098904d"
_ALERT_Q_BRANCH = "codex/dependency-alertmanager-remediation"
_ALERT_DONOR_SOURCE = "b82f3868caa305ef8592a30d707ca37d7725905d"
_ALERT_RECEIVER_PR = 2497
_ALERT_RECEIVER_BRANCH = "codex/python-setup-security-stabilization"
_ALERT_Q_RUN = 39018353942
_ALERT_Q_ARTIFACT = 12095483900
_ALERT_Q_JOB = 117354986951
_ALERT_Q_ZIP_SHA256 = "46276592068419330f3f73d71802a15ebff0db28f0e9b67cb63e5d054f26cce1"
_ALERT_PROBE_SHA256 = "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe"
_ALERT_TRIVY_SHA256 = "d89bcc6510a267f11b773398cbf1be5520ce39f9e8b6633178c4487f05b7d791"
_ALERT_BUILDX_SHA256 = "ae43fa08c796b44efc86d7a63c55f73f7c35f3101188dea7bf93bcd6f99577ba"
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
# Upstream source identity is independent of the compiler/CA current flag.
_ALERT_UPSTREAM_0342_REVISION = "e8349048265ccc0871c3d0d668b05eacc68baf50"
_ALERT_UPSTREAM_0342_METADATA = _ALERT_BUILD_METADATA.replace(
    "Version=0.34.1", "Version=0.34.2"
).replace("73c6bfe7393929211294c1954f30d8ed78e4d0ad", _ALERT_UPSTREAM_0342_REVISION)
_ALERT_ASSEMBLY_EPOCH = 0
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
_ALERT_CURRENT_ASSEMBLY_RECIPE_SHA256 = (
    "2c70a5f492866c30e2c7db69be001003c674ef0f16b336f94a8a23be2777de13"
)
# Filled only by a later reviewed material update after actual full acceptance.
# Failed build artifacts and caller-supplied ancestors never select a producer.
_ALERT_HISTORICAL_C10: dict[str, Any] = {
    "run": 39143039135,
    "attempt": 1,
    "artifact": 12142714566,
    "source": "63455b8a750ef07a1e525078b4e3ce2089eecdde",
    "job": 117721196331,
    "zip_sha256": "16d1a4e8f6eaeb57f65d946c6b34daaa489c8f3b02bd7778e0d65f836c582307",
    "source_files": {
        "scripts/ci/fetch_docker_source_artifacts.py": "c4bff70395e025e751d28eb6da55e7cd14c9105c69cd0217dab9df2becefe062",
        ".github/workflows/cd.yml": "24ec2e95fbf9ac896f1aa90523022972254f53ffb518f2c3bd79aa57988890c6",
        "scripts/ci/docker_source_artifacts.json": "7230165fa5a61b17d7985d00e4c9f6dba9fca03fc64fd98a2b79e460469e575e",
        "deploy/alertmanager/Containerfile": "8321b8129f819fadd64df26f0607c66fbabcef578bc76fe658e0d6d2cbab7347",
        "deploy/alertmanager/alertmanager.yml": "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549",
        "tests/test_notify_premium_alias_checkpoint_failure.py": "bbcaad269757350db93dedaa544bd58dab695b901b8fef90ec68922be34a3654",
    },
    "graph": {
        "manifest": {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "digest": "sha256:bc6c847d25e48a8bcddfd8fef0aec25b6ac890346b4bfe6dea3d2d82cd0dc3b9",
            "size": 4402,
        },
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "digest": "sha256:46928bb4d3eac8b7bd9d8516a9427c3ec684244fc5f74260324e0acb6bcea9d4",
            "size": 5392,
        },
        "layers": [
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:9486261b5a13f63ca6904b36721527ac8f19df53d300560138d69ae9b4c203de",
                "size": 491520,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:621c35e751a51a9a9dc3e80aa0b7fe8be2a93402ea6ccd307d30852cd7776cda",
                "size": 40960,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:763a77745f27b86cf26b97887b6842d83720e63b1c48848c0ba9ee54e351d63a",
                "size": 1157120,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:f0d0eff4c2312a7bd6e21797bdfea5eb35f60e76b555ce2b22794424af2cad36",
                "size": 1331200,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:275a30dd8ce958b21daa9ad962c6fbc09f98306ee2f486b65c9075dc257b1412",
                "size": 102400,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:4d049f83d9cf21d1f5cc0e11deaf36df02790d0e60c1a3829538fb4b61685368",
                "size": 1536,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:af5aa97ebe6ce1604747ec1e21af7136ded391bcabe4acef882e718a87c86bcc",
                "size": 2560,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:6f1cdceb6a3146f0ccb986521156bef8a422cdbb0863396f7f751f575ba308f4",
                "size": 2560,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:bd3cdfae1d3fdd83a2231d608969b38b82349777c2fff9a7c12d54f8ac5c9b38",
                "size": 2560,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:4cde6b0bb6f50a5f255eef7b2a42162c661cf776b803225dcac9a659e396bb6b",
                "size": 1536,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:ad51d0769d16ba578106a177987dfe3d2e02c1668c852b795b2f6b024068242a",
                "size": 2048,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:187cfc6d1e3e8a40a5e64653bcd3239c140807dcf1c09e48021178705a5a6139",
                "size": 3072,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:f2392a9484bf6b18f06beaf705b994e31dbb2716c99cf7d03c9c495cd107f364",
                "size": 276480,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:bd026780cc0c5382e535233aee825d870e66d6d82e07b73ac18f220ed7c9d934",
                "size": 25455180,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:2ab5d4c77316257dddf81e2b234e34390b489eef2120ca4733c9d669d983923d",
                "size": 15781723,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:ab74bfcac3265805d1ed60ec03a891bed24891405520590480fc06e12b030a28",
                "size": 757855,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:17ff0eff1cc56cf8d79fb9ea18cd9abace34750fbb1040b20fdd445942f4ea9a",
                "size": 757859,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:8209ebe206ef975eeb451391dd7dd45503ba312e6a1696790577a795d4ff7b31",
                "size": 627,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:9e2e80ab47f927d9f8c4762633f5ec437d25e0e7b3057554ceb243b8ec52a98c",
                "size": 4022,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:2ba8d9b08f1ae2e781271e512771dc9137aee1b9208856c344405faf69866b08",
                "size": 305,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:9ccc61aefe1be8fdd987ffb4f600b1c3d9bd364eb72d45486d093dfdc8deb097",
                "size": 106,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:4f4fb700ef54461cfa02571ae0db9a0dc1e0cdb5577484a6d75e68dc38e8acc1",
                "size": 32,
            },
        ],
        "diff_ids": [
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
            "sha256:b8d01f4956f8c5e0d15d6ac6f06e436500c4c4f39d557c5c3615f445b0a5c29e",
            "sha256:faefc9bd77de8cc0152e10e6928ab8eb71e3bd6ed4c2b45ba6994d567c7ece1c",
            "sha256:41d124b2b1a246b7d61671670fbf78a6b00b02b4fe1c3cbbfc121dd78ea66e3e",
            "sha256:25abd9bad5ceae54afa864e07ffd2607d314bded1226c1387f6501b9abf255bb",
            "sha256:58c1d3a584115f2413fc76937ec358934a0d552f713db514e6001eca8d12d560",
            "sha256:a397d7cdd103c8c07b7c2ec85a71e03769a2297b222cd6948dfa30104f02cee3",
            "sha256:c8267a994d5ab6a6d994508c960f204baf85ba06aebe2423bbc420b0f2b75bfb",
            "sha256:16b5b96ce2ee1da809adae25e1cabb9afa41e4789048d3a8b8b760db8090fd98",
            "sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef",
        ],
        "configuration": {
            "architecture": "amd64",
            "config": {
                "User": "65534:65534",
                "ExposedPorts": {"9093/tcp": {}},
                "Env": [
                    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                    "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt",
                ],
                "Entrypoint": ["/bin/alertmanager"],
                "Cmd": [
                    "--config.file=/etc/alertmanager/alertmanager.yml",
                    "--storage.path=/alertmanager",
                    "--cluster.listen-address=",
                ],
                "Volumes": {"/alertmanager": {}},
                "WorkingDir": "/alertmanager",
                "ArgsEscaped": True,
            },
            "created": "2026-10-18T16:06:01.356356122Z",
            "history": [
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build " "@trixie//base-files/amd64:data_statusd",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build " "@trixie//netbase/amd64:data_statusd",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build " "@trixie//tzdata/amd64:data_statusd",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build " "@trixie//tzdata-legacy/amd64:data_statusd",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build " "@trixie//media-types/amd64:data_statusd",
                },
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:rootfs"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:passwd"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:home"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:group"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:tmp"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //static:nsswitch"},
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build //common:os_release_debian13",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build " "//common:cacerts_debian13_amd64_tar",
                },
                {
                    "created": "2026-10-18T16:06:01.190926447Z",
                    "created_by": "COPY alertmanager /usr/bin/alertmanager # " "buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-18T16:06:01.299802409Z",
                    "created_by": "COPY amtool /usr/bin/amtool # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-18T16:06:01.308970092Z",
                    "created_by": "COPY probe-bin-bracket /usr/bin/wget # " "buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-18T16:06:01.318051658Z",
                    "created_by": "COPY probe-bin-bracket /usr/bin/httpd # " "buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-18T16:06:01.32597619Z",
                    "created_by": "COPY alertmanager.yml "
                    "/etc/alertmanager/alertmanager.yml # "
                    "buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-18T16:06:01.333874361Z",
                    "created_by": "COPY LICENSE /LICENSE # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-18T16:06:01.341392231Z",
                    "created_by": "COPY NOTICE /NOTICE # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-18T16:06:01.349348549Z",
                    "created_by": "USER 65534:65534",
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
                {
                    "created": "2026-10-18T16:06:01.349348549Z",
                    "created_by": "COPY --chown=65534:65534 --chmod=0700 "
                    "storage-dir /alertmanager # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-18T16:06:01.356356122Z",
                    "created_by": "WORKDIR /alertmanager",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-18T16:06:01.356356122Z",
                    "created_by": "EXPOSE [9093/tcp]",
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
                {
                    "created": "2026-10-18T16:06:01.356356122Z",
                    "created_by": "VOLUME [/alertmanager]",
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
                {
                    "created": "2026-10-18T16:06:01.356356122Z",
                    "created_by": 'ENTRYPOINT ["/bin/alertmanager"]',
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
                {
                    "created": "2026-10-18T16:06:01.356356122Z",
                    "created_by": "CMD "
                    '["--config.file=/etc/alertmanager/alertmanager.yml" '
                    '"--storage.path=/alertmanager" '
                    '"--cluster.listen-address="]',
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
            ],
            "os": "linux",
            "rootfs": {
                "type": "layers",
                "diff_ids": [
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
                    "sha256:b8d01f4956f8c5e0d15d6ac6f06e436500c4c4f39d557c5c3615f445b0a5c29e",
                    "sha256:faefc9bd77de8cc0152e10e6928ab8eb71e3bd6ed4c2b45ba6994d567c7ece1c",
                    "sha256:41d124b2b1a246b7d61671670fbf78a6b00b02b4fe1c3cbbfc121dd78ea66e3e",
                    "sha256:25abd9bad5ceae54afa864e07ffd2607d314bded1226c1387f6501b9abf255bb",
                    "sha256:58c1d3a584115f2413fc76937ec358934a0d552f713db514e6001eca8d12d560",
                    "sha256:a397d7cdd103c8c07b7c2ec85a71e03769a2297b222cd6948dfa30104f02cee3",
                    "sha256:c8267a994d5ab6a6d994508c960f204baf85ba06aebe2423bbc420b0f2b75bfb",
                    "sha256:16b5b96ce2ee1da809adae25e1cabb9afa41e4789048d3a8b8b760db8090fd98",
                    "sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef",
                ],
            },
        },
        "payload": [
            {"path": "usr", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {"path": "usr/bin", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "usr/bin/alertmanager",
                "mode": 365,
                "uid": 0,
                "gid": 0,
                "size": 50293672,
                "type": "file",
                "sha256": "08778bcb751b4ccdf1727701cb5af5cdfaae3f0cc122d697a49792a987c56f6b",
            },
            {"path": "usr", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {"path": "usr/bin", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "usr/bin/amtool",
                "mode": 365,
                "uid": 0,
                "gid": 0,
                "size": 30655748,
                "type": "file",
                "sha256": "5cfcb4a40897f2095339284989b563e144bc8ed2e827493e47cb9083202c89b4",
            },
            {"path": "usr", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {"path": "usr/bin", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "usr/bin/wget",
                "mode": 365,
                "uid": 0,
                "gid": 0,
                "size": 1173752,
                "type": "file",
                "sha256": "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe",
            },
            {"path": "usr", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {"path": "usr/bin", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "usr/bin/httpd",
                "mode": 365,
                "uid": 0,
                "gid": 0,
                "size": 1173752,
                "type": "file",
                "sha256": "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe",
            },
            {"path": "etc", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "etc/alertmanager",
                "mode": 493,
                "uid": 0,
                "gid": 0,
                "size": 0,
                "type": "directory",
            },
            {
                "path": "etc/alertmanager/alertmanager.yml",
                "mode": 292,
                "uid": 0,
                "gid": 0,
                "size": 1094,
                "type": "file",
                "sha256": "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549",
            },
            {
                "path": "LICENSE",
                "mode": 292,
                "uid": 0,
                "gid": 0,
                "size": 11357,
                "type": "file",
                "sha256": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
            },
            {
                "path": "NOTICE",
                "mode": 292,
                "uid": 0,
                "gid": 0,
                "size": 311,
                "type": "file",
                "sha256": "24f7d73529defd2e28b4bb5e0f0396cebb6d3e74b7f66a26b62d0d3251431582",
            },
            {
                "path": "alertmanager",
                "mode": 448,
                "uid": 65534,
                "gid": 65534,
                "size": 0,
                "type": "directory",
            },
        ],
        "files": {
            "usr/bin/alertmanager": "08778bcb751b4ccdf1727701cb5af5cdfaae3f0cc122d697a49792a987c56f6b",
            "usr/bin/amtool": "5cfcb4a40897f2095339284989b563e144bc8ed2e827493e47cb9083202c89b4",
            "usr/bin/wget": "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe",
            "usr/bin/httpd": "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe",
            "etc/alertmanager/alertmanager.yml": "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549",
            "LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
            "NOTICE": "24f7d73529defd2e28b4bb5e0f0396cebb6d3e74b7f66a26b62d0d3251431582",
        },
        "default_CA_sha256": "714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5",
    },
    "OCI_archive_sha256": "2991bf19f770c296e437aadbe9ca1169e25665797aa233611335de50f3551401",
}

# Prepared current producer: actual accepted output is populated only after native/security proof.
_ALERT_HISTORICAL_AM11: dict[str, Any] = {
    "run": 40387641620,
    "attempt": 1,
    "artifact": 12684611600,
    "source": "a8c9b361dbd57d86e2adf8f01f7880830fc04e53",
    "job": 121800078082,
    "zip_sha256": "9d64f8a3814a69e94756c6e4cc9ddfe32f37b712e9091de67a167f3cad8a02cc",
    "source_files": {
        "scripts/ci/fetch_docker_source_artifacts.py": "a5ce1d231df3266e3f79c5ca757935ee92450e4d2373e3581e4e16d067f236b0",
        ".github/workflows/cd.yml": "9793418af04ca3f9330fd0c0600384704082e887dfcd7f2a66616d7057af5ae8",
        "scripts/ci/docker_source_artifacts.json": "d128fa5f624493cdc51665fd0fbbdf8c404e2a275022e9687f39d85ba275ebf0",
        "deploy/alertmanager/Containerfile": "2c70a5f492866c30e2c7db69be001003c674ef0f16b336f94a8a23be2777de13",
        "deploy/alertmanager/alertmanager.yml": "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549",
        "tests/test_notify_premium_alias_checkpoint_failure.py": "bf3aa402c2f388c88a9700eb6a5db71b31cc23caff53a8e8018a03b428d9fd01",
    },
    "graph": {
        "manifest": {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "digest": "sha256:5a476cb3c572d11f8b5fcb6d42400f4613011a5f592ca574b7015c5231b70781",
            "size": 4402,
        },
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "digest": "sha256:542c5e287fc8e0dc4f6c7db21576f4eaa508b28e9733e205ef78d2e3d06be62c",
            "size": 5393,
        },
        "layers": [
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:9486261b5a13f63ca6904b36721527ac8f19df53d300560138d69ae9b4c203de",
                "size": 491520,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:621c35e751a51a9a9dc3e80aa0b7fe8be2a93402ea6ccd307d30852cd7776cda",
                "size": 40960,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:92a3b02188b326c1b10a0a375d3c0019dff4ee8ff02a4b51a7e640bb9400932f",
                "size": 1157120,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:ef430e4865b6130e131d5777c1d072fdcc89478668d10ab41a18549e0fdc88b5",
                "size": 1331200,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:275a30dd8ce958b21daa9ad962c6fbc09f98306ee2f486b65c9075dc257b1412",
                "size": 102400,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:4d049f83d9cf21d1f5cc0e11deaf36df02790d0e60c1a3829538fb4b61685368",
                "size": 1536,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:af5aa97ebe6ce1604747ec1e21af7136ded391bcabe4acef882e718a87c86bcc",
                "size": 2560,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:6f1cdceb6a3146f0ccb986521156bef8a422cdbb0863396f7f751f575ba308f4",
                "size": 2560,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:bd3cdfae1d3fdd83a2231d608969b38b82349777c2fff9a7c12d54f8ac5c9b38",
                "size": 2560,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:4cde6b0bb6f50a5f255eef7b2a42162c661cf776b803225dcac9a659e396bb6b",
                "size": 1536,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:ad51d0769d16ba578106a177987dfe3d2e02c1668c852b795b2f6b024068242a",
                "size": 2048,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:187cfc6d1e3e8a40a5e64653bcd3239c140807dcf1c09e48021178705a5a6139",
                "size": 3072,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:0762a1f6557d1e88a761ab05aa7f65a10dc0e559913ea13befb873d907e1a396",
                "size": 276480,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:59ba35e2b5232c91af81a0d75ea400f0aeca5e6b34f889199746e487e391b3e4",
                "size": 25457662,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:1d7e93175a5a327c3b0c65c4684de75d884ebd2c5f341939bc542dfba60e698c",
                "size": 15782244,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:4e3c14bca0c0997d0a99d999c7e94acf52e89a38fa9a73ef94f51edd50754dff",
                "size": 757856,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:ae18b45f2decac38791db3c3699b506f187b23660b1a209cdccf63e4e860fc08",
                "size": 757856,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:e7643c91b99167835dcbf7bea533953e4274bc0eec7ab77832f52cc46c9ae2ab",
                "size": 627,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:96e5ede9a46e17833eaef049f706c7782fbabb7cf948be23becf99d0f7030174",
                "size": 4022,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:21af9a1d47c28faa66d24403d5bc06746852ea4bc6bde40e99bdcd6e39334954",
                "size": 305,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:bc26cacb46c3ccffb76545edbfd6e44f2cbee2db68776e40fbb31f3efdd0dec0",
                "size": 104,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:4f4fb700ef54461cfa02571ae0db9a0dc1e0cdb5577484a6d75e68dc38e8acc1",
                "size": 32,
            },
        ],
        "diff_ids": [
            "sha256:9486261b5a13f63ca6904b36721527ac8f19df53d300560138d69ae9b4c203de",
            "sha256:621c35e751a51a9a9dc3e80aa0b7fe8be2a93402ea6ccd307d30852cd7776cda",
            "sha256:92a3b02188b326c1b10a0a375d3c0019dff4ee8ff02a4b51a7e640bb9400932f",
            "sha256:ef430e4865b6130e131d5777c1d072fdcc89478668d10ab41a18549e0fdc88b5",
            "sha256:275a30dd8ce958b21daa9ad962c6fbc09f98306ee2f486b65c9075dc257b1412",
            "sha256:4d049f83d9cf21d1f5cc0e11deaf36df02790d0e60c1a3829538fb4b61685368",
            "sha256:af5aa97ebe6ce1604747ec1e21af7136ded391bcabe4acef882e718a87c86bcc",
            "sha256:6f1cdceb6a3146f0ccb986521156bef8a422cdbb0863396f7f751f575ba308f4",
            "sha256:bd3cdfae1d3fdd83a2231d608969b38b82349777c2fff9a7c12d54f8ac5c9b38",
            "sha256:4cde6b0bb6f50a5f255eef7b2a42162c661cf776b803225dcac9a659e396bb6b",
            "sha256:ad51d0769d16ba578106a177987dfe3d2e02c1668c852b795b2f6b024068242a",
            "sha256:187cfc6d1e3e8a40a5e64653bcd3239c140807dcf1c09e48021178705a5a6139",
            "sha256:0762a1f6557d1e88a761ab05aa7f65a10dc0e559913ea13befb873d907e1a396",
            "sha256:b8db3796f4e87f1a6ce0bf738ddefe7a4fec22094c70dd02dada1b9240fd8641",
            "sha256:3472ef71ed568a199fa93cac34441ebfcdbfd6864cb328285f90e841b8fcad8a",
            "sha256:b31a97d984edc094d85a62425ae840c7c8df5f6c7a126b7eae07b06280e033c2",
            "sha256:f01151e6dd7dbf87c4048a968600eb9182047e0908a7a5b0fe63d30d9f416d1e",
            "sha256:55fe60a8d959c16dc5753336a6977eb2488b405e32fcaed2eac9f8ab4eea273a",
            "sha256:49b1190cc45f406436a4bc706dd15a3fc0efb71ccaf50f1b7fcb736512cbdae5",
            "sha256:ea06a73386e697bcf480be17aea640c768d103e84cf384adc138d4c4ba62e86c",
            "sha256:81eee2246c1ed9889c5bb3e86905e6c03f3c90716243a80444366983fe5d0362",
            "sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef",
        ],
        "configuration": {
            "architecture": "amd64",
            "config": {
                "User": "65534:65534",
                "ExposedPorts": {"9093/tcp": {}},
                "Env": [
                    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                    "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt",
                ],
                "Entrypoint": ["/bin/alertmanager"],
                "Cmd": [
                    "--config.file=/etc/alertmanager/alertmanager.yml",
                    "--storage.path=/alertmanager",
                    "--cluster.listen-address=",
                ],
                "Volumes": {"/alertmanager": {}},
                "WorkingDir": "/alertmanager",
                "ArgsEscaped": True,
            },
            "created": "2026-10-26T19:38:32.167128975Z",
            "history": [
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build " "@trixie//base-files/amd64:data_statusd",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build " "@trixie//netbase/amd64:data_statusd",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build " "@trixie//tzdata/amd64:data_statusd",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build " "@trixie//tzdata-legacy/amd64:data_statusd",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build " "@trixie//media-types/amd64:data_statusd",
                },
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:rootfs"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:passwd"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:home"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:group"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:tmp"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //static:nsswitch"},
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build //common:os_release_debian13",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build " "//common:cacerts_debian13_amd64_tar",
                },
                {
                    "created": "2026-10-26T19:38:31.957837416Z",
                    "created_by": "COPY alertmanager /usr/bin/alertmanager # " "buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-26T19:38:32.115719879Z",
                    "created_by": "COPY amtool /usr/bin/amtool # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-26T19:38:32.127899001Z",
                    "created_by": "COPY probe-bin-bracket /usr/bin/wget # " "buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-26T19:38:32.139560719Z",
                    "created_by": "COPY probe-bin-bracket /usr/bin/httpd # " "buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-26T19:38:32.145526487Z",
                    "created_by": "COPY alertmanager.yml "
                    "/etc/alertmanager/alertmanager.yml # "
                    "buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-26T19:38:32.151230068Z",
                    "created_by": "COPY LICENSE /LICENSE # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-26T19:38:32.156995526Z",
                    "created_by": "COPY NOTICE /NOTICE # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-26T19:38:32.162032794Z",
                    "created_by": "USER 65534:65534",
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
                {
                    "created": "2026-10-26T19:38:32.162032794Z",
                    "created_by": "COPY --chown=65534:65534 --chmod=0700 "
                    "storage-dir /alertmanager # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-26T19:38:32.167128975Z",
                    "created_by": "WORKDIR /alertmanager",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "2026-10-26T19:38:32.167128975Z",
                    "created_by": "EXPOSE [9093/tcp]",
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
                {
                    "created": "2026-10-26T19:38:32.167128975Z",
                    "created_by": "VOLUME [/alertmanager]",
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
                {
                    "created": "2026-10-26T19:38:32.167128975Z",
                    "created_by": 'ENTRYPOINT ["/bin/alertmanager"]',
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
                {
                    "created": "2026-10-26T19:38:32.167128975Z",
                    "created_by": "CMD "
                    '["--config.file=/etc/alertmanager/alertmanager.yml" '
                    '"--storage.path=/alertmanager" '
                    '"--cluster.listen-address="]',
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
            ],
            "os": "linux",
            "rootfs": {
                "type": "layers",
                "diff_ids": [
                    "sha256:9486261b5a13f63ca6904b36721527ac8f19df53d300560138d69ae9b4c203de",
                    "sha256:621c35e751a51a9a9dc3e80aa0b7fe8be2a93402ea6ccd307d30852cd7776cda",
                    "sha256:92a3b02188b326c1b10a0a375d3c0019dff4ee8ff02a4b51a7e640bb9400932f",
                    "sha256:ef430e4865b6130e131d5777c1d072fdcc89478668d10ab41a18549e0fdc88b5",
                    "sha256:275a30dd8ce958b21daa9ad962c6fbc09f98306ee2f486b65c9075dc257b1412",
                    "sha256:4d049f83d9cf21d1f5cc0e11deaf36df02790d0e60c1a3829538fb4b61685368",
                    "sha256:af5aa97ebe6ce1604747ec1e21af7136ded391bcabe4acef882e718a87c86bcc",
                    "sha256:6f1cdceb6a3146f0ccb986521156bef8a422cdbb0863396f7f751f575ba308f4",
                    "sha256:bd3cdfae1d3fdd83a2231d608969b38b82349777c2fff9a7c12d54f8ac5c9b38",
                    "sha256:4cde6b0bb6f50a5f255eef7b2a42162c661cf776b803225dcac9a659e396bb6b",
                    "sha256:ad51d0769d16ba578106a177987dfe3d2e02c1668c852b795b2f6b024068242a",
                    "sha256:187cfc6d1e3e8a40a5e64653bcd3239c140807dcf1c09e48021178705a5a6139",
                    "sha256:0762a1f6557d1e88a761ab05aa7f65a10dc0e559913ea13befb873d907e1a396",
                    "sha256:b8db3796f4e87f1a6ce0bf738ddefe7a4fec22094c70dd02dada1b9240fd8641",
                    "sha256:3472ef71ed568a199fa93cac34441ebfcdbfd6864cb328285f90e841b8fcad8a",
                    "sha256:b31a97d984edc094d85a62425ae840c7c8df5f6c7a126b7eae07b06280e033c2",
                    "sha256:f01151e6dd7dbf87c4048a968600eb9182047e0908a7a5b0fe63d30d9f416d1e",
                    "sha256:55fe60a8d959c16dc5753336a6977eb2488b405e32fcaed2eac9f8ab4eea273a",
                    "sha256:49b1190cc45f406436a4bc706dd15a3fc0efb71ccaf50f1b7fcb736512cbdae5",
                    "sha256:ea06a73386e697bcf480be17aea640c768d103e84cf384adc138d4c4ba62e86c",
                    "sha256:81eee2246c1ed9889c5bb3e86905e6c03f3c90716243a80444366983fe5d0362",
                    "sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef",
                ],
            },
        },
        "payload": [
            {"path": "usr", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {"path": "usr/bin", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "usr/bin/alertmanager",
                "mode": 365,
                "uid": 0,
                "gid": 0,
                "size": 50298871,
                "type": "file",
                "sha256": "c7df6fc46c9f41f83657de5956b0373d1e733b04549c59d9657c44a426334aff",
            },
            {"path": "usr", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {"path": "usr/bin", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "usr/bin/amtool",
                "mode": 365,
                "uid": 0,
                "gid": 0,
                "size": 30655667,
                "type": "file",
                "sha256": "47bd3f8d054eb8b6ab1005577508da00b52efba55ba647a83612ec31731da42b",
            },
            {"path": "usr", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {"path": "usr/bin", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "usr/bin/wget",
                "mode": 365,
                "uid": 0,
                "gid": 0,
                "size": 1173752,
                "type": "file",
                "sha256": "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe",
            },
            {"path": "usr", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {"path": "usr/bin", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "usr/bin/httpd",
                "mode": 365,
                "uid": 0,
                "gid": 0,
                "size": 1173752,
                "type": "file",
                "sha256": "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe",
            },
            {"path": "etc", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "etc/alertmanager",
                "mode": 493,
                "uid": 0,
                "gid": 0,
                "size": 0,
                "type": "directory",
            },
            {
                "path": "etc/alertmanager/alertmanager.yml",
                "mode": 292,
                "uid": 0,
                "gid": 0,
                "size": 1094,
                "type": "file",
                "sha256": "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549",
            },
            {
                "path": "LICENSE",
                "mode": 292,
                "uid": 0,
                "gid": 0,
                "size": 11357,
                "type": "file",
                "sha256": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
            },
            {
                "path": "NOTICE",
                "mode": 292,
                "uid": 0,
                "gid": 0,
                "size": 311,
                "type": "file",
                "sha256": "24f7d73529defd2e28b4bb5e0f0396cebb6d3e74b7f66a26b62d0d3251431582",
            },
            {
                "path": "alertmanager",
                "mode": 448,
                "uid": 65534,
                "gid": 65534,
                "size": 0,
                "type": "directory",
            },
        ],
        "files": {
            "usr/bin/alertmanager": "c7df6fc46c9f41f83657de5956b0373d1e733b04549c59d9657c44a426334aff",
            "usr/bin/amtool": "47bd3f8d054eb8b6ab1005577508da00b52efba55ba647a83612ec31731da42b",
            "usr/bin/wget": "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe",
            "usr/bin/httpd": "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe",
            "etc/alertmanager/alertmanager.yml": "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549",
            "LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
            "NOTICE": "24f7d73529defd2e28b4bb5e0f0396cebb6d3e74b7f66a26b62d0d3251431582",
        },
        "default_CA_sha256": "e9c7b63ee2623386e9b0a3ee32f499d01a8ea23dc83b8383ddff9f8e749543b7",
    },
    "OCI_archive_sha256": "fa74ac0777c59c73299c6424239038bfcd9b0a0d7366beaf24fc432b364090c1",
}

# Accepted C2 retains its original producer source and complete native graph.
_ALERT_ACCEPTED_CANDIDATE: dict[str, Any] | None = {
    "run": 42110438896,
    "attempt": 1,
    "artifact": 13456175467,
    "source": "8aee3976d8f13027a5f2a38f0152ede0f4990156",
    "job": 127536259342,
    "zip_sha256": "9a3780a984c8d4c309eb8755c71d0bda09c3884f923c5e3a023aa5b38b60867f",
    "source_files": {
        "scripts/ci/fetch_docker_source_artifacts.py": "2da3e626cfea5a9c33c6d32eded9b9c2a6896ca7e500626279a717cd5b4a3487",
        ".github/workflows/cd.yml": "ae36965ae3b20893a16cb2363a355e73c5f4b3547a99292f8fa498bb107f4a64",
        "scripts/ci/docker_source_artifacts.json": "8b14ca1c62bf4ec0a130e5a2cbe55e986f823c3b8686ddb835c7f736f09be98b",
        "deploy/alertmanager/Containerfile": "2c70a5f492866c30e2c7db69be001003c674ef0f16b336f94a8a23be2777de13",
        "deploy/alertmanager/alertmanager.yml": "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549",
        "tests/test_notify_premium_alias_checkpoint_failure.py": "3c8d43cf2b9c33e8d95ef522620a2ff3aef1d9610ba99c5db171e015de6112e3",
    },
    "graph": {
        "manifest": {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "digest": "sha256:e4b0453fb56079d8ee565f76c4029c34d0711215b2a72541cc060bdcbe9827d3",
            "size": 5085,
        },
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "digest": "sha256:db6b5863659a4d2e4372cbf32602429299763e0efacc2c165dc7245c3e9df2ee",
            "size": 5243,
        },
        "layers": [
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:9486261b5a13f63ca6904b36721527ac8f19df53d300560138d69ae9b4c203de",
                "size": 491520,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:621c35e751a51a9a9dc3e80aa0b7fe8be2a93402ea6ccd307d30852cd7776cda",
                "size": 40960,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:92a3b02188b326c1b10a0a375d3c0019dff4ee8ff02a4b51a7e640bb9400932f",
                "size": 1157120,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:ef430e4865b6130e131d5777c1d072fdcc89478668d10ab41a18549e0fdc88b5",
                "size": 1331200,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:275a30dd8ce958b21daa9ad962c6fbc09f98306ee2f486b65c9075dc257b1412",
                "size": 102400,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:4d049f83d9cf21d1f5cc0e11deaf36df02790d0e60c1a3829538fb4b61685368",
                "size": 1536,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:af5aa97ebe6ce1604747ec1e21af7136ded391bcabe4acef882e718a87c86bcc",
                "size": 2560,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:6f1cdceb6a3146f0ccb986521156bef8a422cdbb0863396f7f751f575ba308f4",
                "size": 2560,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:bd3cdfae1d3fdd83a2231d608969b38b82349777c2fff9a7c12d54f8ac5c9b38",
                "size": 2560,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:4cde6b0bb6f50a5f255eef7b2a42162c661cf776b803225dcac9a659e396bb6b",
                "size": 1536,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:ad51d0769d16ba578106a177987dfe3d2e02c1668c852b795b2f6b024068242a",
                "size": 2048,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:187cfc6d1e3e8a40a5e64653bcd3239c140807dcf1c09e48021178705a5a6139",
                "size": 3072,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar",
                "digest": "sha256:0762a1f6557d1e88a761ab05aa7f65a10dc0e559913ea13befb873d907e1a396",
                "size": 276480,
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:f0c99cb46dc3075e00bcbf7cacb455db42cc1919a5317ab7ee74e00365c2d772",
                "size": 25500490,
                "annotations": {"buildkit/rewritten-timestamp": "0"},
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:14462b113359b676c1048b09131792950e2890decacdd40a3c01f453c0f443c7",
                "size": 15805672,
                "annotations": {"buildkit/rewritten-timestamp": "0"},
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:ed53005ab7a3eda1c4e318dc3749f1b0e1bbaf7b1f512f5ed23874920a8e1b67",
                "size": 757847,
                "annotations": {"buildkit/rewritten-timestamp": "0"},
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:3f7073302b8d53123283aed48a518b1921ce8feddb14942d83394be258419f72",
                "size": 757849,
                "annotations": {"buildkit/rewritten-timestamp": "0"},
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:45b6955d306ab4f615bb5dbf288dcdc2db5c8c04934a4e6b8681f33a298d5c16",
                "size": 612,
                "annotations": {"buildkit/rewritten-timestamp": "0"},
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:088129772a902e049909e77376849a4f5363c89f983d50a5138904bb41a0a92d",
                "size": 4010,
                "annotations": {"buildkit/rewritten-timestamp": "0"},
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:9426ce3b6d972a36e7f2ac052b62757765a9209a376f43bb6f17c404b3cb804d",
                "size": 297,
                "annotations": {"buildkit/rewritten-timestamp": "0"},
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:1bcd9d02d07c61ea09b224e897faef8c89a6c46f2892c57f6549e312610d6dcb",
                "size": 97,
                "annotations": {"buildkit/rewritten-timestamp": "0"},
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:4f4fb700ef54461cfa02571ae0db9a0dc1e0cdb5577484a6d75e68dc38e8acc1",
                "size": 32,
                "annotations": {"buildkit/rewritten-timestamp": "0"},
            },
        ],
        "diff_ids": [
            "sha256:9486261b5a13f63ca6904b36721527ac8f19df53d300560138d69ae9b4c203de",
            "sha256:621c35e751a51a9a9dc3e80aa0b7fe8be2a93402ea6ccd307d30852cd7776cda",
            "sha256:92a3b02188b326c1b10a0a375d3c0019dff4ee8ff02a4b51a7e640bb9400932f",
            "sha256:ef430e4865b6130e131d5777c1d072fdcc89478668d10ab41a18549e0fdc88b5",
            "sha256:275a30dd8ce958b21daa9ad962c6fbc09f98306ee2f486b65c9075dc257b1412",
            "sha256:4d049f83d9cf21d1f5cc0e11deaf36df02790d0e60c1a3829538fb4b61685368",
            "sha256:af5aa97ebe6ce1604747ec1e21af7136ded391bcabe4acef882e718a87c86bcc",
            "sha256:6f1cdceb6a3146f0ccb986521156bef8a422cdbb0863396f7f751f575ba308f4",
            "sha256:bd3cdfae1d3fdd83a2231d608969b38b82349777c2fff9a7c12d54f8ac5c9b38",
            "sha256:4cde6b0bb6f50a5f255eef7b2a42162c661cf776b803225dcac9a659e396bb6b",
            "sha256:ad51d0769d16ba578106a177987dfe3d2e02c1668c852b795b2f6b024068242a",
            "sha256:187cfc6d1e3e8a40a5e64653bcd3239c140807dcf1c09e48021178705a5a6139",
            "sha256:0762a1f6557d1e88a761ab05aa7f65a10dc0e559913ea13befb873d907e1a396",
            "sha256:7cbccd2b7da66b161400635cf64d46a21195e590f44320b20deb0436c6677f47",
            "sha256:7a97889d786f042fae2f59f9cb17a3e21d1dea08a9fe38b4333bec5dc3c5d9a0",
            "sha256:f051c02db927594f23745b7dc826033115c2e33debba4d67204ae615943f7e73",
            "sha256:94e89fbfb258668bb6fdc87b0fc7f37eeeefd1fc89aa739bcc57ffada8663f8b",
            "sha256:65f56c9aa7619e167cb91d1beb61ced1d834816e96a73af2aa760f3ef433245c",
            "sha256:e24bff050ddf9053222fc87bb07da9d515fdffaa6b8f00b613dc4229f0b3b150",
            "sha256:3a4a9e6bb5564f8d757029258936b0c566d6110e1339463f0bfb729b30ed2ed5",
            "sha256:620f62c178df2355281c80decca65ea32427834c05d5a78ea387547f5fd13435",
            "sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef",
        ],
        "configuration": {
            "architecture": "amd64",
            "config": {
                "User": "65534:65534",
                "ExposedPorts": {"9093/tcp": {}},
                "Env": [
                    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                    "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt",
                ],
                "Entrypoint": ["/bin/alertmanager"],
                "Cmd": [
                    "--config.file=/etc/alertmanager/alertmanager.yml",
                    "--storage.path=/alertmanager",
                    "--cluster.listen-address=",
                ],
                "Volumes": {"/alertmanager": {}},
                "WorkingDir": "/alertmanager",
                "ArgsEscaped": True,
            },
            "created": "1970-01-01T00:00:00Z",
            "history": [
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build @trixie//base-files/amd64:data_statusd",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build @trixie//netbase/amd64:data_statusd",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build @trixie//tzdata/amd64:data_statusd",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build @trixie//tzdata-legacy/amd64:data_statusd",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build @trixie//media-types/amd64:data_statusd",
                },
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:rootfs"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:passwd"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:home"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:group"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //common:tmp"},
                {"created": "1970-01-01T00:00:00Z", "created_by": "bazel build //static:nsswitch"},
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build //common:os_release_debian13",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "bazel build //common:cacerts_debian13_amd64_tar",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "COPY alertmanager /usr/bin/alertmanager # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "COPY amtool /usr/bin/amtool # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "COPY probe-bin-bracket /usr/bin/wget # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "COPY probe-bin-bracket /usr/bin/httpd # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "COPY alertmanager.yml /etc/alertmanager/alertmanager.yml # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "COPY LICENSE /LICENSE # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "COPY NOTICE /NOTICE # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "USER 65534:65534",
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "COPY --chown=65534:65534 --chmod=0700 storage-dir /alertmanager # buildkit",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "WORKDIR /alertmanager",
                    "comment": "buildkit.dockerfile.v0",
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "EXPOSE [9093/tcp]",
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": "VOLUME [/alertmanager]",
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": 'ENTRYPOINT ["/bin/alertmanager"]',
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
                {
                    "created": "1970-01-01T00:00:00Z",
                    "created_by": 'CMD ["--config.file=/etc/alertmanager/alertmanager.yml" "--storage.path=/alertmanager" "--cluster.listen-address="]',
                    "comment": "buildkit.dockerfile.v0",
                    "empty_layer": True,
                },
            ],
            "os": "linux",
            "rootfs": {
                "type": "layers",
                "diff_ids": [
                    "sha256:9486261b5a13f63ca6904b36721527ac8f19df53d300560138d69ae9b4c203de",
                    "sha256:621c35e751a51a9a9dc3e80aa0b7fe8be2a93402ea6ccd307d30852cd7776cda",
                    "sha256:92a3b02188b326c1b10a0a375d3c0019dff4ee8ff02a4b51a7e640bb9400932f",
                    "sha256:ef430e4865b6130e131d5777c1d072fdcc89478668d10ab41a18549e0fdc88b5",
                    "sha256:275a30dd8ce958b21daa9ad962c6fbc09f98306ee2f486b65c9075dc257b1412",
                    "sha256:4d049f83d9cf21d1f5cc0e11deaf36df02790d0e60c1a3829538fb4b61685368",
                    "sha256:af5aa97ebe6ce1604747ec1e21af7136ded391bcabe4acef882e718a87c86bcc",
                    "sha256:6f1cdceb6a3146f0ccb986521156bef8a422cdbb0863396f7f751f575ba308f4",
                    "sha256:bd3cdfae1d3fdd83a2231d608969b38b82349777c2fff9a7c12d54f8ac5c9b38",
                    "sha256:4cde6b0bb6f50a5f255eef7b2a42162c661cf776b803225dcac9a659e396bb6b",
                    "sha256:ad51d0769d16ba578106a177987dfe3d2e02c1668c852b795b2f6b024068242a",
                    "sha256:187cfc6d1e3e8a40a5e64653bcd3239c140807dcf1c09e48021178705a5a6139",
                    "sha256:0762a1f6557d1e88a761ab05aa7f65a10dc0e559913ea13befb873d907e1a396",
                    "sha256:7cbccd2b7da66b161400635cf64d46a21195e590f44320b20deb0436c6677f47",
                    "sha256:7a97889d786f042fae2f59f9cb17a3e21d1dea08a9fe38b4333bec5dc3c5d9a0",
                    "sha256:f051c02db927594f23745b7dc826033115c2e33debba4d67204ae615943f7e73",
                    "sha256:94e89fbfb258668bb6fdc87b0fc7f37eeeefd1fc89aa739bcc57ffada8663f8b",
                    "sha256:65f56c9aa7619e167cb91d1beb61ced1d834816e96a73af2aa760f3ef433245c",
                    "sha256:e24bff050ddf9053222fc87bb07da9d515fdffaa6b8f00b613dc4229f0b3b150",
                    "sha256:3a4a9e6bb5564f8d757029258936b0c566d6110e1339463f0bfb729b30ed2ed5",
                    "sha256:620f62c178df2355281c80decca65ea32427834c05d5a78ea387547f5fd13435",
                    "sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef",
                ],
            },
        },
        "payload": [
            {"path": "usr", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {"path": "usr/bin", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "usr/bin/alertmanager",
                "mode": 365,
                "uid": 0,
                "gid": 0,
                "size": 50375721,
                "type": "file",
                "sha256": "4a871fe631f8b91e9f421f2ff9c3a4f2472d340cc654448155cb8722cae125d1",
            },
            {"path": "usr", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {"path": "usr/bin", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "usr/bin/amtool",
                "mode": 365,
                "uid": 0,
                "gid": 0,
                "size": 30696071,
                "type": "file",
                "sha256": "e041a8aadb52426695dcee36f2ce854ca26d82f53a2f0379d4faaabfb316b954",
            },
            {"path": "usr", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {"path": "usr/bin", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "usr/bin/wget",
                "mode": 365,
                "uid": 0,
                "gid": 0,
                "size": 1173752,
                "type": "file",
                "sha256": "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe",
            },
            {"path": "usr", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {"path": "usr/bin", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "usr/bin/httpd",
                "mode": 365,
                "uid": 0,
                "gid": 0,
                "size": 1173752,
                "type": "file",
                "sha256": "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe",
            },
            {"path": "etc", "mode": 493, "uid": 0, "gid": 0, "size": 0, "type": "directory"},
            {
                "path": "etc/alertmanager",
                "mode": 493,
                "uid": 0,
                "gid": 0,
                "size": 0,
                "type": "directory",
            },
            {
                "path": "etc/alertmanager/alertmanager.yml",
                "mode": 292,
                "uid": 0,
                "gid": 0,
                "size": 1094,
                "type": "file",
                "sha256": "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549",
            },
            {
                "path": "LICENSE",
                "mode": 292,
                "uid": 0,
                "gid": 0,
                "size": 11357,
                "type": "file",
                "sha256": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
            },
            {
                "path": "NOTICE",
                "mode": 292,
                "uid": 0,
                "gid": 0,
                "size": 311,
                "type": "file",
                "sha256": "24f7d73529defd2e28b4bb5e0f0396cebb6d3e74b7f66a26b62d0d3251431582",
            },
            {
                "path": "alertmanager",
                "mode": 448,
                "uid": 65534,
                "gid": 65534,
                "size": 0,
                "type": "directory",
            },
        ],
        "files": {
            "usr/bin/alertmanager": "4a871fe631f8b91e9f421f2ff9c3a4f2472d340cc654448155cb8722cae125d1",
            "usr/bin/amtool": "e041a8aadb52426695dcee36f2ce854ca26d82f53a2f0379d4faaabfb316b954",
            "usr/bin/wget": "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe",
            "usr/bin/httpd": "462febe85977f9787d1d4a45fae0c0858fdb65f2312ccb95e034a505cbaaebfe",
            "etc/alertmanager/alertmanager.yml": "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549",
            "LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
            "NOTICE": "24f7d73529defd2e28b4bb5e0f0396cebb6d3e74b7f66a26b62d0d3251431582",
        },
        "default_CA_sha256": "e9c7b63ee2623386e9b0a3ee32f499d01a8ea23dc83b8383ddff9f8e749543b7",
    },
    "OCI_archive_sha256": "2c3f25468765d3c84c1f2eba73b25b96bb71b2cbeaaf6e42dd5b531ed9eaff5f",
}

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
        "1.3.2.1-motley",
        "https://codeload.github.com/madler/zlib/tar.gz/71747d1d39168833e0cae8ed84b8ce77cb049699",
        "zlib-71747d1d39168833e0cae8ed84b8ce77cb049699.tar.gz",
        "d03279035bd9536a0d4e0396a593acd330c7ed51fc42f7d8aa83450957f30a16",
    ),
    "ncurses": (
        "6.6-20261024",
        "https://codeload.github.com/ThomasDickey/ncurses-snapshots/tar.gz/dc909d77781ef5c2a0684e9ad9eb9f0c0baf5ecc",
        "ncurses-snapshots-dc909d77781ef5c2a0684e9ad9eb9f0c0baf5ecc.tar.gz",
        "3c75e58a86e20f380f2e245e75c8ac48b2b0fa61881f0a81394f565682c9532e",
    ),
    "openssl": (
        "3.5.9",
        "https://codeload.github.com/openssl/openssl/legacy.tar.gz/45e844fa2a14ec92d146bd8f5778ac130b6625fb",
        "openssl-3.5.9.tar.gz",
        "7392920f1897e1e2d9dc848368aff6e4bdc9421344286d60ba517b9f14b202a0",
    ),
    "postgresql": (
        "18.6",
        "https://ftp.postgresql.org/pub/source/v18.6/postgresql-18.6.tar.gz",
        "postgresql-18.6.tar.gz",
        "672dab274f12efd49d7d431e77b42d235d9583f191608821b0e48dc1d09fb4c0",
    ),
}
_PINNED_ALERT_SOURCES = {
    "alertmanager-source": (
        "e8349048265ccc0871c3d0d668b05eacc68baf50",
        "https://codeload.github.com/prometheus/alertmanager/tar.gz/e8349048265ccc0871c3d0d668b05eacc68baf50",
        "alertmanager-e8349048265ccc0871c3d0d668b05eacc68baf50.tar.gz",
        "06d88cbef612a0d4ddb991177e5628a3519a192b16505581b4e0c0985797fac7",
    ),
    "alertmanager-ui": (
        "0.34.2",
        "https://github.com/prometheus/alertmanager/releases/download/v0.34.2/alertmanager-web-ui-0.34.2.tar.gz",
        "alertmanager-web-ui-0.34.2.tar.gz",
        "94cca0b0c04577a86deea79a58e337ef8a5854ea026df8f992eb4040c813f743",
    ),
}
_PINNED_EXACT_SOURCES = {
    **_PINNED_CODELOAD_SOURCES,
    **_PINNED_NATIVE_SOURCES,
    **_PINNED_ALERT_SOURCES,
}

# Exact Alertmanager source/UI acquired and reconciled before this source preparation.
_ALERT_NAMES = frozenset({"alertmanager-source", "alertmanager-ui"})
_ALERT_SIZES = {"alertmanager-source": 820631, "alertmanager-ui": 931818}
_ALERT_MEMBER_DIGESTS = {
    "alertmanager-source": "05072e406e1a25cec5f743d3647243fb40a2d74a83c4971b9d6e8f043cf4215a",
    "alertmanager-ui": "20649d8f64d2c50f5d707045f4f3b688792e46b3534e239d043564707ec9745c",
}

_NATIVE_ARCHIVE_INVENTORIES = {
    "zlib": ("zlib-71747d1d39168833e0cae8ed84b8ce77cb049699", 310, 3636732, "LICENSE"),
    "ncurses": (
        "ncurses-snapshots-dc909d77781ef5c2a0684e9ad9eb9f0c0baf5ecc",
        1299,
        18736809,
        "COPYING",
    ),
    "openssl": ("openssl-openssl-45e844f", 6078, 131230833, "LICENSE.txt"),
    "postgresql": ("postgresql-18.6", 7944, 141525674, "COPYRIGHT"),
}
_NATIVE_ARCHIVE_MAX_BYTES = 64 * 1024 * 1024
_PINNED_NATIVE_SHA256 = {
    "zlib": "c9db0fa65f2ab5432d7d97097c058c81e0cfff250f9e900ac3dc1d70989d4dd5",
    "ncurses": "4c1a95b8f05f0f8665988fa407693d33224776f46e4728c15db910a2f653fe29",
    "openssl": "32662f03fc8e90bc8b8fc0acb115ed413eec5045a127e9af9f6c234bc3d0a8f2",
    "postgresql": "983ee554ec53dbeb9b70797bef9fcf4e67e117e7e48ca1463cc80b3ff8e8ff3f",
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
            "alertmanager-source": "81e69f87954aedb557ed67d9ef0218a1c0c9b9e0c3184c9ddffe07bd247239fc",
            "alertmanager-ui": "3d6b13c5af094724e0bed8f757399e08af44d40d6c6cd87392a1f8ee6ed1e457",
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
            raise RuntimeError("Retired zlib patch version_parts are not current source inputs.")
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


def _alertmanager_upstream_identity(
    root_inputs: dict[str, str] | None = None,
    *,
    current: bool,
    accepted: dict[str, Any] | None = None,
    api: GitHubRead | None = None,
) -> str:
    """Select only reviewed source/UI hash pairs; compiler/CA remains independent."""
    from scripts.ci.prometheus_source_image import one_object, require

    require(type(current) is bool, "AM_upstream_compiler_epoch_type")
    if accepted is not None:
        require(
            root_inputs is None and accepted == _alertmanager_accepted_producer(),
            "AM_accepted_source_context",
        )
        if accepted in (_ALERT_HISTORICAL_C10, _ALERT_HISTORICAL_AM11):
            return "0.34.1"
        require(api is not None, "AM_accepted_source_snapshot_required")
        snapshot = _alertmanager_source_snapshot(
            cast("GitHubRead", api), accepted["source"], accepted=True
        )
        # Git-addressable accepted provenance, not a new acquisition or a date renewal.
        catalog = one_object(snapshot["scripts/ci/docker_source_artifacts.json"])
        rows = catalog.get("artifacts")
        require(type(rows) is list and bool(rows), "AM_lineage_source_catalog")
        selected: dict[str, dict[str, Any]] = {}
        seen: set[str] = set()
        for row in rows:
            require(
                type(row) is dict and type(row.get("name")) is str and row["name"] not in seen,
                "AM_lineage_catalog_distinct_names",
            )
            seen.add(row["name"])
            if row["name"] in _ALERT_NAMES:
                selected[row["name"]] = row
        require(set(selected) == set(_ALERT_NAMES), "AM_lineage_exact_source_UI_members")
        root_inputs = {
            key: _sha3_from_parts(selected[name].get("sha256_parts"), artifact_name=name)
            for key, name in (
                ("source.tar.gz", "alertmanager-source"),
                ("ui.tar.gz", "alertmanager-ui"),
            )
        }
        upstream = _alertmanager_upstream_identity(root_inputs, current=True)
        if upstream == "0.34.2":
            for name, row in selected.items():
                require(
                    (
                        row.get("version"),
                        row.get("url"),
                        row.get("filename"),
                        _sha3_from_parts(row.get("sha3_256_parts"), artifact_name=name),
                    )
                    == _PINNED_ALERT_SOURCES[name],
                    "AM_lineage_exact_current_source_tuple",
                )
        return upstream
    require(api is None and type(root_inputs) is dict, "AM_upstream_compiler_epoch_type")
    root_inputs = cast(dict[str, str], root_inputs)
    pair = tuple(root_inputs.get(name) for name in ("source.tar.gz", "ui.tar.gz"))
    if pair == (
        "5c5c72ec6b4c4746d523f2ed1994dfec4b94f7457e530ee6fb16cfec158e545e",
        "881fe0f7beb9573f35be47dd233af6220e72c8db72c03bcd1780402eb8dc1307",
    ):
        return "0.34.1"
    require(
        current
        and pair
        == (
            "81e69f87954aedb557ed67d9ef0218a1c0c9b9e0c3184c9ddffe07bd247239fc",
            "3d6b13c5af094724e0bed8f757399e08af44d40d6c6cd87392a1f8ee6ed1e457",
        ),
        "AM_exact_upstream_source_UI_compiler_join",
    )
    return "0.34.2"


def _alertmanager_upstream_version(root_bytes: dict[str, bytes], *, current: bool) -> str:
    """Cross-bind actual retained bytes through the same finite source tuple owner."""
    return _alertmanager_upstream_identity(
        {name: sha256(root_bytes[name]).hexdigest() for name in ("source.tar.gz", "ui.tar.gz")},
        current=current,
    )


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
        "alertmanager-e8349048265ccc0871c3d0d668b05eacc68baf50"
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
    *,
    image_relation: dict[str, Any] | None = None,
    expected_commands: dict[str, list[str]] | None = None,
    expected_profiles: dict[str, dict[str, Any]] | None = None,
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
    if image_relation is not None:
        from scripts.ci.prometheus_source_image import native_container_image_identity, require

        native_container_image_identity(observed[0], image_relation)
        require(
            expected_commands is not None
            and identifier in expected_commands
            and observed[0]["Config"].get("Cmd") == expected_commands[identifier]
            and observed[0]["Config"].get("Entrypoint") == ["/toolchain/bin/go"],
            "AM_metadata_cleanup_command",
        )
        require(
            expected_profiles is not None
            and identifier in expected_profiles
            and all(
                observed[0].get(key) == expected_profiles[identifier].get(key)
                for key in ("Config", "HostConfig", "Mounts")
            ),
            "AM_metadata_cleanup_profile",
        )
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


def _alertmanager_loaded_base(objects: list[dict[str, Any]], *, current: bool = False) -> str:
    """Return the native operand, never reinterpret it as config-content identity."""
    from scripts.ci.prometheus_source_image import native_base_identity, require

    require(type(objects) is list and len(objects) == 1, "AM_exact_one_native_base")
    relation = native_base_identity(objects[0], current=current)
    return cast(str, relation["engine_id"])


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

    if output.absolute().is_relative_to(REPO_ROOT):
        raise RuntimeError("AM qualification output must be outside the source checkout")
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


_ALERT_XNET062_METADATA_EPOCH = "alertmanager-0.34.2-xnet062"


def _alertmanager_xnet062_delta(
    before_rows: list[dict[str, Any]],
    after_rows: list[dict[str, Any]],
    *,
    epoch: str,
) -> list[dict[str, Any]]:
    """One current metadata action; historical qualification readers stay separate."""
    if epoch != _ALERT_XNET062_METADATA_EPOCH:
        raise RuntimeError("Alertmanager xnet062 metadata epoch differs.")

    def selected(rows: list[dict[str, Any]]) -> dict[str, str | None]:
        result: dict[str, str | None] = {}
        mains = 0
        for row in rows:
            path = row.get("Path")
            version = row.get("Version")
            if (
                not isinstance(path, str)
                or not path
                or path in result
                or "Error" in row
                or "Replace" in row
                or ("Main" in row and type(row["Main"]) is not bool)
            ):
                raise RuntimeError("Alertmanager metadata module identity differs.")
            if row.get("Main") is True:
                mains += 1
                if path != "github.com/prometheus/alertmanager" or version is not None:
                    raise RuntimeError("Alertmanager metadata main module differs.")
            elif not isinstance(version, str) or not version:
                raise RuntimeError("Alertmanager metadata module version missing.")
            result[path] = version
        if mains != 1:
            raise RuntimeError("Alertmanager metadata requires one main module.")
        return result

    before, after = selected(before_rows), selected(after_rows)
    if (
        before.get("golang.org/x/net") != "v0.60.0"
        or before.get("google.golang.org/grpc") != "v1.83.2"
        or after.get("golang.org/x/net") != "v0.62.0"
    ):
        raise RuntimeError("Alertmanager xnet062 original/derived selection differs.")
    return [
        {
            "path": path,
            "before": before.get(path),
            "after": after.get(path),
            "class": (
                "authored"
                if path == "golang.org/x/net"
                else "solver_closure_reproduced_by_fixed_get"
            ),
        }
        for path in sorted(set(before) | set(after))
        if before.get(path) != after.get(path)
    ]


def _alertmanager_module_phase(output: Path, deadline: float, seconds: int) -> None:
    """Fixed metadata-only online/offline replay; this function never compiles."""
    import shutil
    import uuid
    from scripts.ci.prometheus_source_image import (
        Native,
        CURRENT_GO as GO,
        extract,
        acquire,
        decode_objects,
        file_hash,
        tree_inventory,
        native_base_identity,
        native_container_image_identity,
        one_object,
        require,
    )

    evidence = output / "alertmanager-module-evidence"
    output.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(mode=0o700)
    native = Native(evidence, deadline, 45)
    owner_token = uuid.uuid4().hex
    owned_names: set[str] = set()
    owned_ids: set[str] = set()
    expected_commands: dict[str, list[str]] = {}
    expected_profiles: dict[str, dict[str, Any]] = {}
    base_relation: dict[str, Any] | None = None
    primary: BaseException | None = None
    cleanup_error: BaseException | None = None
    docker_config = output / "alertmanager-empty-docker-config"
    docker_config.mkdir(mode=0o700)
    docker_env = {"PATH": "/usr/bin:/bin", "HOME": str(docker_config)}
    try:
        artifacts = load_manifest(DEFAULT_MANIFEST, artifact="alertmanager")
        _fetch_alertmanager_pair(artifacts, output, operation_deadline=deadline)
        go_archive = output / "go1.27.3.linux-amd64.tar.gz"
        if not go_archive.exists() and not go_archive.is_symlink():
            acquire(GO, go_archive, deadline)

        if (
            go_archive.is_symlink()
            or not go_archive.is_file()
            or go_archive.stat().st_nlink != 1
            or go_archive.stat().st_size != GO.size
            or file_hash(go_archive, deadline) != GO.digest
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
        from scripts.ci.prometheus_source_image import BASE

        base_ref = BASE
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
        base_id = _alertmanager_loaded_base(base_objects, current=True)
        base_relation = native_base_identity(base_objects[0])
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
        baseline_observations: list[dict[str, object]] = []
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
                "GOENV": "off",
                "GOWORK": "off",
                "GOOS": "linux",
                "GOARCH": "amd64",
                "CGO_ENABLED": "0",
                "GOPROXY": "https://proxy.golang.org",
                "GOSUMDB": "sum.golang.org",
                "GOFLAGS": "-mod=readonly",
            }
            original_locks = {name: (source / name).read_bytes() for name in ("go.mod", "go.sum")}
            if (
                sha256(original_locks["go.mod"]).hexdigest()
                != "55a63e9214662673cdbf865dd859b2d62da89f6d5b32b2165ec80f5af3fc6139"
                or sha256(original_locks["go.sum"]).hexdigest()
                != "4ab3b4e64e70b2cca7be33ac1d572e659595e17c98703a26efb5b32790ea1cbf"
            ):
                raise RuntimeError("Current upstream module source bytes differ.")
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
            expected_locks = original_locks

            def command(args: list[str], label: str, solver: bool = False) -> bytes:
                before_locks = {name: (source / name).read_bytes() for name in original_locks}
                if (
                    nonlocks() != frozen_source
                    or file_hash(go_archive, deadline) != GO.digest
                    or before_locks != expected_locks
                ):
                    raise RuntimeError("Alertmanager source/tool drift before metadata command.")
                raw: bytes = native.run(
                    [str(go), *args],
                    "replay" + str(number) + "-" + label,
                    dict(env, GOFLAGS="") if solver else env,
                    cwd=source,
                )
                if nonlocks() != frozen_source or (
                    not solver
                    and before_locks
                    != {name: (source / name).read_bytes() for name in original_locks}
                ):
                    raise RuntimeError("Alertmanager source/lock drift after metadata command.")
                return raw

            version = command(["version"], "version")
            if version != b"go version go1.27.3 linux/amd64\n":
                raise RuntimeError("Qualified Go version/platform differs.")
            command(["mod", "download", "-json"], "baseline-download")
            baseline_raw = command(
                ["list", "-mod=readonly", "-m", "-json", "all"], "baseline-modules"
            )
            baseline = decode_objects(baseline_raw)
            baseline_graph = command(["mod", "graph"], "baseline-graph")
            if (
                not baseline_graph
                or len(baseline_graph.splitlines()) != len(set(baseline_graph.splitlines()))
                or any(len(line.split()) != 2 for line in baseline_graph.splitlines())
            ):
                raise RuntimeError("Alertmanager original module graph malformed or duplicated.")
            baseline_versions = {row.get("Path"): row.get("Version") for row in baseline}
            if (
                len(baseline_versions) != len(baseline)
                or baseline_versions.get("golang.org/x/net") != "v0.60.0"
                or baseline_versions.get("google.golang.org/grpc") != "v1.83.2"
                or any("Error" in row or "Replace" in row for row in baseline)
            ):
                raise RuntimeError("Alertmanager original selected module graph differs.")
            try:
                command(
                    ["get", "golang.org/x/net@v0.62.0"],
                    "xnet062-authored-get",
                    solver=True,
                )
            except BaseException as error:
                try:
                    for lock in original_locks:
                        (evidence / ("replay" + str(number) + "-failed-get-" + lock)).write_bytes(
                            (source / lock).read_bytes()
                        )
                except BaseException as retention_error:
                    error.add_note(
                        "Failed-get lock retention failed: " + type(retention_error).__name__
                    )
                raise
            # Capture immediately, before any download can modify checksum history.
            derived_locks = {name: (source / name).read_bytes() for name in original_locks}
            if derived_locks == original_locks:
                raise RuntimeError("Alertmanager xnet062 derivation must change original locks.")
            for lock, raw in derived_locks.items():
                (evidence / ("replay" + str(number) + "-derived-" + lock)).write_bytes(raw)
            expected_locks = derived_locks
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
                    or versions.get("golang.org/x/net") != "v0.62.0"
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

            baseline_observations.append(
                {
                    "modules": sorted(
                        decode_objects(coordinate(baseline_raw)), key=lambda row: row["Path"]
                    ),
                    "graph": sorted(baseline_graph.splitlines()),
                }
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
            delta = _alertmanager_xnet062_delta(
                baseline, modules, epoch=_ALERT_XNET062_METADATA_EPOCH
            )
            if {name: (source / name).read_bytes() for name in original_locks} != derived_locks:
                raise RuntimeError("Alertmanager immediate post-get locks changed.")
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
                        "derivation_epoch": _ALERT_XNET062_METADATA_EPOCH,
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
                "--cpus=2",
                "--memory=4g",
                "--pids-limit=128",
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
            guest_env = {
                "HOME": "/run/alertmanager-metadata",
                "GOPATH": "/cache",
                "GOMODCACHE": "/cache/pkg/mod",
                "GOCACHE": "/run/alertmanager-metadata/cache",
                "TMPDIR": "/run/alertmanager-metadata",
                "GOTOOLCHAIN": "local",
                "GOENV": "off",
                "GOWORK": "off",
                "GOPROXY": "off",
                "GOSUMDB": "off",
                "CGO_ENABLED": "0",
                "GOOS": "linux",
                "GOARCH": "amd64",
                "GOFLAGS": "-mod=readonly",
            }
            for key, value in guest_env.items():
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
                expected_commands[identifier] = args
                before_start = one_object(
                    native.run(
                        [*docker_prefix, "inspect", "--format", "{{json .}}", identifier],
                        "replay" + str(number) + "-prestart-" + label,
                        docker_env,
                        cwd=source,
                    )
                )
                expected_profiles[identifier] = before_start
                require(base_relation is not None, "AM_metadata_base_relation")
                native_container_image_identity(before_start, base_relation)
                expected_env = dict(
                    value.split("=", 1) for value in base_objects[0]["Config"]["Env"]
                )
                expected_env.update(guest_env)
                cfg, host = before_start["Config"], before_start["HostConfig"]
                require(
                    before_start.get("Id") == identifier
                    and before_start.get("Name") == "/" + name
                    and cfg.get("Labels", {}).get("pulseplate.alertmanager-module") == owner_token
                    and cfg.get("Entrypoint") == ["/toolchain/bin/go"]
                    and cfg.get("Cmd") == args
                    and cfg.get("User") == "65534:65534"
                    and cfg.get("WorkingDir") == "/source"
                    and dict(value.split("=", 1) for value in cfg["Env"]) == expected_env,
                    "AM_metadata_prestart_identity_command",
                )
                require(
                    host.get("NetworkMode") == "none"
                    and host.get("ReadonlyRootfs") is True
                    and host.get("Privileged") is False
                    and host.get("CapDrop") == ["ALL"]
                    and host.get("CapAdd") in (None, [])
                    and host.get("SecurityOpt")
                    in (["no-new-privileges"], ["no-new-privileges:true"])
                    and host.get("NanoCpus") == 2000000000
                    and host.get("Memory") == 4294967296
                    and host.get("PidsLimit") == 128,
                    "AM_metadata_prestart_isolation",
                )
                mounts = before_start["Mounts"]
                require(
                    len(mounts) == 3
                    and all(row["Type"] == "bind" and row["RW"] is False for row in mounts)
                    and {row["Destination"]: row["Source"] for row in mounts}
                    == {"/source": str(source), "/cache": str(cache), "/toolchain": str(toolchain)},
                    "AM_metadata_prestart_mounts",
                )
                require(
                    host.get("Binds") in (None, [])
                    and host.get("Tmpfs")
                    == {
                        "/run/alertmanager-metadata": "size=64m,noexec,nosuid,uid=65534,gid=65534,mode=0700"
                    },
                    "AM_metadata_prestart_tmpfs",
                )
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
                native_container_image_identity(terminal[0], base_relation)
                require(
                    terminal[0]["Config"] == before_start["Config"]
                    and terminal[0]["HostConfig"] == before_start["HostConfig"]
                    and terminal[0]["Mounts"] == before_start["Mounts"],
                    "AM_metadata_terminal_profile_changed",
                )
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
        if len(baseline_observations) != 2 or baseline_observations[0] != baseline_observations[1]:
            raise RuntimeError("Independent Alertmanager original selected graphs differ.")
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
                        image_relation=base_relation,
                        expected_commands=expected_commands,
                        expected_profiles=expected_profiles,
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
        # Existing historical Q readers reject this new epoch until separately admitted.
        "derivation_epoch": _ALERT_XNET062_METADATA_EPOCH,
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
        and type(selected.get("graph")) is dict
        and bool(selected["graph"]),
        "AM_accepted_producer_canonical_binding",
    )
    if selected["source"] == _ALERT_HISTORICAL_C10["source"]:
        require(selected == _ALERT_HISTORICAL_C10, "AM_exact_historical_C10")
        expected_recipe = _ALERT_ASSEMBLY_RECIPE_SHA256
    else:
        expected_recipe = _ALERT_CURRENT_ASSEMBLY_RECIPE_SHA256
    require(
        selected["source_files"]["deploy/alertmanager/Containerfile"] == expected_recipe,
        "AM_accepted_producer_exact_epoch_recipe",
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
    current_source_files: dict[str, str] | None = None,
    current_artifact_digest: str | None = None,
    upstream_version: str = "0.34.1",
    source_branch: str | None = None,
) -> dict[str, Any]:
    """Authenticate the three finite AM CD artifact cases; coordinates are not approval."""
    import base64
    from datetime import datetime, timezone
    from scripts.ci.prometheus_source_image import require

    require(
        kind in ("qualification", "support", "candidate", "publication"), "AM_closed_artifact_kind"
    )
    require(upstream_version in ("0.34.1", "0.34.2"), "AM_authenticated_upstream_epoch")
    current = current_source_files is not None
    merged_candidate = kind in ("candidate", "publication") and current
    require(kind != "publication" or current, "AM_publication_artifact_requires_H_binding")
    require(
        not merged_candidate or upstream_version == "0.34.2" and source_branch == "main",
        "AM_current_candidate_is_merged_H_only",
    )
    require(
        upstream_version == "0.34.1" or current or kind == "candidate",
        "AM_new_upstream_requires_current_inputs",
    )
    require(
        source_branch is None
        or upstream_version == "0.34.2"
        and source_branch in (_ALERT_Q_BRANCH, "main"),
        "AM_closed_source_branch",
    )
    require(
        current == (current_artifact_digest is not None)
        and (not current or kind in ("qualification", "support") or merged_candidate),
        "AM_current_input_binding_pair",
    )
    if current:
        require(
            type(current_source_files) is dict
            and set(current_source_files)
            == (
                set(_ALERT_Q_SOURCE_FILES)
                | {"tests/test_notify_premium_alias_checkpoint_failure.py"}
                if merged_candidate
                else set(_ALERT_Q_SOURCE_FILES)
            )
            and all(
                type(value) is str and _HEX_RE.fullmatch(value) is not None
                for value in current_source_files.values()
            )
            and type(current_artifact_digest) is str
            and re.fullmatch(r"sha256:[0-9a-f]{64}", current_artifact_digest) is not None,
            "AM_current_input_binding_fields",
        )

    accepted = (
        (
            _alertmanager_accepted_producer()
            if merged_candidate
            else _alertmanager_accepted_producer(run_id, artifact_id, source)
        )
        if kind in ("candidate", "publication")
        else {}
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
    if current:
        selected_run, selected_artifact, selected_source, selected_job = (
            run_id,
            artifact_id,
            source,
            None,
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
        "publication": ("alertmanager-main-publication", "alertmanager-publication"),
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
        and run.get("head_branch")
        == (
            (
                (source_branch or _ALERT_Q_BRANCH)
                if upstream_version == "0.34.2"
                else _ALERT_RECEIVER_BRANCH
            )
            if current
            or kind == "candidate"
            and accepted["source"] != _ALERT_HISTORICAL_C10["source"]
            else _ALERT_Q_BRANCH
        )
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
        and (selected_job is None or selected[0]["id"] == selected_job)
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
    elif kind in ("candidate", "publication"):
        source_contract = dict(accepted["source_files"])
    if current:
        source_contract = dict(cast(dict[str, str], current_source_files))
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
            == (
                current_artifact_digest
                if current
                else "sha256:"
                + (
                    accepted["zip_sha256"]
                    if kind == "candidate"
                    else (_ALERT_Q_ZIP_SHA256 if kind == "qualification" else _ALERT_S_ZIP_SHA256)
                )
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
    binding: dict[str, Any] = {
        "run": run_id,
        "attempt": 1,
        "artifact": artifact_id,
        "source": source,
        "zip_sha256": sha256(raw).hexdigest(),
        "source_files": source_hashes,
    }
    if merged_candidate:
        binding["job"] = selected[0]["id"]
    return binding


def _alertmanager_current_inputs(
    api: GitHubRead,
    source: str,
    destination: Path,
    *,
    kind: str,
    source_files: dict[str, str],
    upstream_version: str = "0.34.1",
    source_branch: str | None = None,
) -> dict[str, Any]:
    """Resolve one actual current Q or S; no latest-success or supplied-ID fallback."""
    from scripts.ci.prometheus_source_image import require

    require(upstream_version in ("0.34.1", "0.34.2"), "AM_current_input_upstream_epoch")
    require(
        source_branch is None
        or upstream_version == "0.34.2"
        and source_branch in (_ALERT_Q_BRANCH, "main"),
        "AM_current_closed_source_branch",
    )
    branch = (
        (source_branch or _ALERT_Q_BRANCH)
        if upstream_version == "0.34.2"
        else _ALERT_RECEIVER_BRANCH
    )
    require(kind in ("qualification", "support"), "AM_current_input_kind")
    require(
        type(source) is str
        and re.fullmatch(r"[0-9a-f]{40}", source) is not None
        and set(source_files) == set(_ALERT_Q_SOURCE_FILES)
        and all(
            type(value) is str and _HEX_RE.fullmatch(value) is not None
            for value in source_files.values()
        ),
        "AM_current_input_source_binding",
    )
    endpoint = "/repos/Katsiarynakavaleuskaya/PulsePlate"
    runs_endpoint = endpoint + "/actions/workflows/cd.yml/runs?event=workflow_dispatch"
    first = api.json(runs_endpoint + "&per_page=100&page=1")
    runs = api.pages(runs_endpoint, "workflow_runs", first["total_count"])
    job_name, prefix = {
        "qualification": ("alertmanager-module-qualification", "alertmanager-module-qualification"),
        "support": ("alertmanager-input-inspection", "alertmanager-input-inspection"),
    }[kind]
    matches: list[dict[str, Any]] = []
    current_run = os.environ.get("GITHUB_RUN_ID")
    for run in runs:
        if run.get("head_sha") != source or str(run.get("id")) == current_run:
            continue
        jobs_endpoint = endpoint + f'/actions/runs/{run["id"]}/jobs?filter=all'
        first_jobs = api.json(jobs_endpoint + "&per_page=100&page=1")
        jobs = api.pages(jobs_endpoint, "jobs", first_jobs["total_count"])
        selected = [
            job
            for job in jobs
            if job.get("name") == job_name and job.get("conclusion") != "skipped"
        ]
        if not selected:
            continue
        require(
            len(selected) == 1
            and run.get("head_branch") == branch
            and type(run.get("run_attempt")) is int
            and run["run_attempt"] == 1
            and run.get("status") == "completed"
            and run.get("conclusion") == "success"
            and selected[0].get("run_id") == run["id"]
            and selected[0].get("head_sha") == source
            and selected[0].get("status") == "completed"
            and selected[0].get("conclusion") == "success",
            "AM_current_input_terminal",
        )
        artifacts_endpoint = endpoint + f'/actions/runs/{run["id"]}/artifacts'
        first_artifacts = api.json(artifacts_endpoint + "?per_page=100&page=1")
        artifacts = api.pages(artifacts_endpoint, "artifacts", first_artifacts["total_count"])
        found = [row for row in artifacts if row.get("name") == f'{prefix}-{run["id"]}-1']
        require(len(found) == 1, "AM_current_input_artifact_unique")
        matches.append({"run": run, "artifact": found[0]})
    require(len(matches) == 1, "AM_current_input_unique")
    matched_input = matches[0]
    return _alertmanager_authenticated_inputs(
        api,
        matched_input["run"]["id"],
        matched_input["artifact"]["id"],
        source,
        destination,
        kind=kind,
        current_source_files=source_files,
        current_artifact_digest=matched_input["artifact"]["digest"],
        upstream_version=upstream_version,
        source_branch=source_branch,
    )


def _alertmanager_selected_inputs(
    api: GitHubRead,
    args: argparse.Namespace,
    output: Path,
    accepted: dict[str, Any],
    *,
    upstream_version: str = "0.34.1",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Acquire Q/S for the independently selected producer, preserving historical tuples."""
    from scripts.ci.prometheus_source_image import require

    require(upstream_version in ("0.34.1", "0.34.2"), "AM_selected_upstream_epoch")
    current = accepted["source"] != _ALERT_HISTORICAL_C10["source"]
    require(current or upstream_version == "0.34.1", "AM_historical_Q_S_upstream")
    bindings = []
    for kind, prefix in (("qualification", "qualification"), ("support", "support")):
        supplied = tuple(
            getattr(args, "alertmanager_" + prefix + "_" + key)
            for key in ("run", "artifact", "source")
        )
        if current:
            binding = _alertmanager_current_inputs(
                api,
                accepted["source"],
                output / (prefix + ".zip"),
                kind=kind,
                **({"upstream_version": upstream_version} if upstream_version == "0.34.2" else {}),
                source_files={key: accepted["source_files"][key] for key in _ALERT_Q_SOURCE_FILES},
            )
            require(
                all(value is None for value in supplied)
                or supplied == tuple(binding[key] for key in ("run", "artifact", "source")),
                "AM_selected_Q_S_exact_selectors",
            )
        else:
            binding = _alertmanager_authenticated_inputs(
                api, supplied[0], supplied[1], supplied[2], output / (prefix + ".zip"), kind=kind
            )
        bindings.append(binding)
    return bindings[0], bindings[1]


def _alertmanager_publication_predecessor(
    api: GitHubRead, root: Path, revision: str, work: Path, deadline: float
) -> dict[str, Any]:
    """Bind durable AM reads to the actual merged PR's successful native CD publication.

    The incumbent API transport owns finite, distinct pagination. This case does
    not retrieve historical qualification archives or infer publication from a
    tag alone; a missing native predecessor remains HOLD.
    """
    import shutil
    from scripts.ci.prometheus_source_image import Native, fresh_directory, one_object, require

    accepted = _alertmanager_accepted_producer()
    upstream = _alertmanager_upstream_identity(
        current=accepted["source"] != _ALERT_HISTORICAL_C10["source"], accepted=accepted, api=api
    )
    if accepted not in (_ALERT_HISTORICAL_C10, _ALERT_HISTORICAL_AM11):
        require(
            _alertmanager_original_lineage(api) == upstream, "AM_publication_source_context_drift"
        )
    require(upstream in ("0.34.1", "0.34.2"), "AM_publication_authenticated_source_epoch_HOLD")
    selected_pr = 2494 if upstream == "0.34.2" else _ALERT_RECEIVER_PR
    selected_branch = _ALERT_Q_BRANCH if upstream == "0.34.2" else _ALERT_RECEIVER_BRANCH
    endpoint = "/repos/Katsiarynakavaleuskaya/PulsePlate"
    pr = api.json(endpoint + "/pulls/" + str(selected_pr))
    merge = pr.get("merge_commit_sha") if type(pr) is dict else None
    require(
        type(pr) is dict
        and type(pr.get("number")) is int
        and pr["number"] == selected_pr
        and pr.get("merged") is True
        and pr.get("state") == "closed"
        and type(merge) is str
        and re.fullmatch(r"[0-9a-f]{40}", merge) is not None
        and pr.get("base", {}).get("ref") == "main"
        and pr.get("head", {}).get("ref") == selected_branch
        and all(
            type(pr.get(side, {}).get("repo", {}).get("id")) is int
            and pr[side]["repo"]["id"] == 1043311030
            for side in ("head", "base")
        ),
        "AM_publication_actual_merged_own_PR",
    )
    merge = cast(str, merge)
    git = shutil.which("git")
    require(git is not None and Path(git).is_absolute(), "AM_publication_native_Git")
    fresh_directory(work)
    native = Native(work, deadline, 45)
    environment = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_NO_REPLACE_OBJECTS": "1",
    }
    prefix = [
        git,
        "--no-replace-objects",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-C",
        str(root),
    ]

    def current_observation(
        run: dict[str, Any], job: dict[str, Any], publisher: str
    ) -> dict[str, Any] | None:
        source = _alertmanager_source_snapshot(api, publisher)
        # These are additional executable-contract checks, not a substitute for
        # the complete H material below. Reuse both existing source owners.
        source.update(api.source_files(publisher, ("scripts/ci/prometheus_source_image.py",)))
        require(
            set(source)
            == set(_ALERT_Q_SOURCE_FILES)
            | {
                "tests/test_notify_premium_alias_checkpoint_failure.py",
                "scripts/ci/prometheus_source_image.py",
            },
            "AM_H_reviewed_source_members",
        )
        if any(raw != (root / name).read_bytes() for name, raw in source.items()):
            return None
        observed_dir = work / (str(run["id"]) + "-current-observations")
        fresh_directory(observed_dir)
        source_hashes = {
            name: sha256(source[name]).hexdigest()
            for name in (
                *_ALERT_Q_SOURCE_FILES,
                "tests/test_notify_premium_alias_checkpoint_failure.py",
            )
        }
        artifacts_endpoint = endpoint + f'/actions/runs/{run["id"]}/artifacts'
        first_artifacts = api.json(artifacts_endpoint + "?per_page=100&page=1")
        artifacts = api.pages(artifacts_endpoint, "artifacts", first_artifacts.get("total_count"))
        selected = [
            row for row in artifacts if row.get("name") == f'alertmanager-publication-{run["id"]}-1'
        ]
        require(len(selected) == 1, "AM_current_publication_artifact_unique_HOLD")
        artifact = selected[0]
        publication = _alertmanager_authenticated_inputs(
            api,
            run["id"],
            artifact["id"],
            publisher,
            observed_dir / "publication.zip",
            kind="publication",
            current_source_files=source_hashes,
            current_artifact_digest=artifact.get("digest"),
            upstream_version="0.34.2",
            source_branch="main",
        )
        require(publication.get("job") == job["id"], "AM_publication_observed_job_binding")
        files = _alertmanager_candidate_members(observed_dir / "publication.zip")
        report = one_object(files["candidate-observation.json"])
        original = report.get("original_producer")
        require(
            type(original) is dict
            and original.get("source") == publisher
            and type(original.get("run")) is int
            and original["run"] > 0
            and original["run"] != run["id"]
            and type(original.get("artifact")) is int
            and original["artifact"] > 0,
            "AM_current_actual_H_producer_coordinates_HOLD",
        )
        descriptor = api.json(endpoint + f'/actions/artifacts/{original["artifact"]}')
        producer = _alertmanager_authenticated_inputs(
            api,
            original["run"],
            original["artifact"],
            publisher,
            observed_dir / "producer.zip",
            kind="candidate",
            current_source_files=source_hashes,
            current_artifact_digest=descriptor.get("digest"),
            upstream_version="0.34.2",
            source_branch="main",
        )
        require(producer == original, "AM_current_selected_H_producer_binding")
        producer_files = _alertmanager_candidate_members(observed_dir / "producer.zip")
        built = one_object(producer_files["candidate-observation.json"])
        require(
            one_object(files["pullback-native-input.json"]) == built,
            "AM_publication_actual_selected_H_observation",
        )
        admission = built.get("producer_admission", {})
        material = built.get("material")
        require(
            built.get("source") == publisher
            and built.get("status") == "OBSERVED_MERGED_H_REBUILD_SECURITY_NATIVE"
            and built.get("failure") is None
            and built.get("cleanup_failure") is None
            and type(built.get("compiler_starts")) is int
            and built["compiler_starts"] == 2
            and type(built.get("logical_build_starts")) is int
            and built["logical_build_starts"] == 1
            and type(built.get("automatic_retries")) is int
            and built["automatic_retries"] == 0
            and built.get("owned_absence_observed") is True
            and admission.get("mode") == "H"
            and admission.get("source") == publisher
            and admission.get("run") == producer["run"]
            and admission.get("job") == producer["job"]
            and admission.get("merge_commit") == merge
            and admission.get("expected_C") == accepted
            and built.get("graph") == accepted["graph"]
            and type(material) is dict
            and material.get("source") == publisher
            and type(built.get("host_inputs")) is dict
            and bool(built["host_inputs"]),
            "AM_current_H_observed_material_graph_scope_HOLD",
        )
        require(
            _alertmanager_upstream_identity(built.get("root_inputs", {}), current=True) == upstream
            and built.get("producer_source_files") == source_hashes
            and all(
                producer_files.get("producer-source/" + name) == source[name]
                for name in source_hashes
            ),
            "AM_current_H_raw_source_tuple",
        )
        counter = 0

        def query(*arguments: str) -> bytes:
            nonlocal counter
            counter += 1
            raw: bytes = native.run(
                [*prefix, *arguments],
                "AM-H-material-" + str(run["id"]) + "-" + str(counter),
                environment,
                cwd=root,
                maximum_seconds=8,
                output_bound=16 * 1024**2,
            )
            return raw

        graft = query("rev-parse", "--git-path", "info/grafts").decode().strip()
        graft_path = Path(graft) if Path(graft).is_absolute() else root / graft
        require(
            bool(graft)
            and "\n" not in graft
            and not graft_path.exists()
            and not graft_path.is_symlink(),
            "AM_H_material_grafts",
        )
        tree, expected = _alertmanager_material_tree(api, publisher, query)
        require(
            material.get("tree") == tree and type(material.get("members")) is list,
            "AM_current_H_complete_material_tree_HOLD",
        )
        members: dict[str, dict[str, Any]] = {}
        for row in material["members"]:
            require(
                type(row) is dict and type(row.get("path")) is str and row["path"] not in members,
                "AM_H_material_distinct_members",
            )
            name = row["path"]
            require(
                name in expected and (row.get("mode"), row.get("oid")) == expected[name],
                "AM_H_material_authenticated_member",
            )
            if row["mode"] == "160000":
                require(
                    name == "tools/cybersecurity_skills"
                    and row["oid"] == "d04d818b41cc300f8110f17ea167fa494db7fb29"
                    and row.get("content_scope") == "uninspected_nonexecuted_gitlink_pointer_only"
                    and row.get("worktree_state") in ("directory", "uninitialized_absent"),
                    "AM_H_material_gitlink_scope",
                )
            else:
                require(
                    type(row.get("bytes")) is int
                    and 0 <= row["bytes"] <= 128 * 1024**2
                    and type(row.get("sha256")) is str
                    and _HEX_RE.fullmatch(row["sha256"]) is not None,
                    "AM_H_material_blob_observation",
                )
            members[name] = row
        require(set(members) == set(expected), "AM_H_material_all_tracked_members")
        for name, raw in source.items():
            require(
                members[name].get("sha256") == sha256(raw).hexdigest()
                and members[name].get("bytes") == len(raw),
                "AM_H_reviewed_executable_bytes",
            )
        require(
            report.get("source") == publisher
            and report.get("publication_source_sha") == publisher
            and report.get("publication_merge_sha") == merge
            and report.get("material") == material
            and report.get("graph") == built["graph"] == accepted["graph"]
            and report.get("status") == "OBSERVED_IMMUTABLE_PUBLICATION_PULLBACK_NATIVE"
            and report.get("failure") is None
            and report.get("cleanup_failure") is None
            and report.get("retention_failure") is None
            and report.get("cleanup_failures") == []
            and report.get("preparation_credentials_removed") is True
            and report.get("credential_cleanup_observed") is True
            and type(report.get("host_inputs")) is dict
            and bool(report["host_inputs"])
            and type(report.get("compiler_starts")) is int
            and report["compiler_starts"] == 0
            and type(report.get("logical_build_starts")) is int
            and report["logical_build_starts"] == 0
            and type(report.get("copy_attempts")) is int
            and type(report.get("copy_invocations")) is int
            and (report["copy_attempts"], report["copy_invocations"], report.get("package_WRITE"))
            in (
                (0, 0, "UNEXERCISED_EXISTING_SAME_SUBJECT"),
                (1, 1, "OBSERVED_SUCCESSFUL_INTENDED_COPY"),
            ),
            "AM_current_publication_full_outcome_HOLD",
        )
        for payload, observation, prefix_name in (
            (producer_files, built.get("native", {}), "native-evidence"),
            (files, report.get("pre_copy_native", {}), "pre-native-evidence"),
            (files, report.get("native", {}), "native-evidence"),
        ):
            require(
                observation.get("validation_scope") == "merged_H_selected_image",
                "AM_current_full_H_native_scope",
            )
            _alertmanager_candidate_native_records(
                payload, observation.get("native_records"), prefix_name, "H-native"
            )
            lines = payload[prefix_name + "/full-AM-native.stdout"].splitlines()
            require(
                lines.count(b"native_AM_merged_H_full_controls=pass") == 1
                and b"native_AM_producer_image_controls=pass" not in lines
                and b"native_AM_full_candidate_controls=pass" not in lines,
                "AM_current_full_H_native_marker",
            )
        security_inventories = []
        for payload, security in (
            (producer_files, built.get("security", {})),
            (files, report.get("pre_copy_security", {})),
        ):
            require(
                type(security) is dict
                and type(security.get("candidate")) is dict
                and bool(security["candidate"])
                and type(security.get("scanner")) is dict
                and type(security["scanner"].get("DB")) is dict
                and set(security["scanner"]["DB"]) == set(_ALERT_DB)
                and all(
                    type(value) is str and _HEX_RE.fullmatch(value) is not None
                    for value in security["scanner"]["DB"].values()
                ),
                "AM_current_H_complete_security_observation",
            )
            _alertmanager_candidate_native_records(
                payload, security.get("native_records"), "security-evidence", "H-security"
            )
            full = one_object(payload["security-evidence/candidate-full-supported.private.json"])
            require(
                type(full.get("SchemaVersion")) is int
                and full["SchemaVersion"] == 2
                and full.get("ArtifactType") == "container_image"
                and full.get("Metadata", {}).get("ImageID") == built["graph"]["config"]["digest"]
                and _alertmanager_support_inventory(full) == security.get("candidate"),
                "AM_current_H_full_raw_security_report",
            )
            security_inventories.append(
                _alertmanager_candidate_scan_evidence(
                    payload,
                    security,
                    current=True,
                    comparison_subject=built["graph"]["config"]["digest"],
                )
            )
            require(
                security.get("scanner", {}).get("sha256") == _ALERT_TRIVY_SHA256
                and security.get("scanner", {}).get("DB") == built["security"]["scanner"]["DB"],
                "AM_current_H_security_binding",
            )
        require(
            all(type(value) is dict for value in security_inventories)
            and security_inventories[0] == security_inventories[1],
            "AM_current_H_same_subject_inventory_drift",
        )
        require(
            sha256(files["candidate.oci.tar"]).hexdigest()
            == report.get("pullback_OCI_archive_sha256")
            and sha256(producer_files["candidate.oci.tar"]).hexdigest()
            == built.get("OCI_archive_sha256"),
            "AM_current_H_retained_OCI_bytes",
        )
        ui = built.get("UI_file_hashes")
        require(
            type(ui) is dict
            and "index.html.gz" in ui
            and all(
                type(name) is str
                and bool(name)
                and type(digest) is str
                and _HEX_RE.fullmatch(digest) is not None
                for name, digest in ui.items()
            ),
            "AM_current_H_native_UI_inventory",
        )
        return {
            "publication": publication,
            "producer": producer,
            "material_tree": tree,
            "graph": built["graph"],
            "upstream_version": upstream,
            "root_inputs": built["root_inputs"],
            "UI_file_hashes": ui,
        }

    proof_failure: BaseException | None = None
    try:
        require(
            native.run(
                [*prefix, "rev-parse", "--is-shallow-repository"],
                "AM-publication-complete-Git",
                environment,
                cwd=root,
                maximum_seconds=8,
            )
            == b"false\n",
            "AM_publication_shallow_history",
        )
        workflow = api.json(endpoint + "/actions/workflows/cd.yml")
        require(
            type(workflow) is dict
            and type(workflow.get("id")) is int
            and workflow["id"] > 0
            and workflow.get("path") == ".github/workflows/cd.yml",
            "AM_publication_actual_CD_workflow",
        )
        runs_endpoint = (
            endpoint
            + "/actions/workflows/cd.yml/runs?branch=main&event=workflow_dispatch&status=success"
        )
        page = api.json(runs_endpoint + "&per_page=100&page=1")
        require(type(page) is dict, "AM_publication_runs")
        count = page.get("total_count")
        require(type(count) is int and 0 <= count < 1000, "AM_publication_filtered_run_bound")
        runs = api.pages(runs_endpoint, "workflow_runs", count)
        positive = []
        for run in runs:
            require(type(run.get("id")) is int and run["id"] > 0, "AM_publication_run_ID")
            publisher = run.get("head_sha")
            require(
                type(publisher) is str and re.fullmatch(r"[0-9a-f]{40}", publisher) is not None,
                "AM_publication_run_source",
            )
            publisher = cast(str, publisher)
            if not (
                run.get("head_branch") == "main"
                and run.get("event") == "workflow_dispatch"
                and type(run.get("run_attempt")) is int
                and run["run_attempt"] == 1
                and run.get("status") == "completed"
                and run.get("conclusion") == "success"
                and type(run.get("workflow_id")) is int
                and run["workflow_id"] == workflow["id"]
                and all(
                    type(run.get(key, {}).get("id")) is int and run[key]["id"] == 1043311030
                    for key in ("repository", "head_repository")
                )
            ):
                continue
            jobs_endpoint = endpoint + f'/actions/runs/{run["id"]}/attempts/1/jobs'
            first = api.json(jobs_endpoint + "?per_page=100&page=1")
            require(type(first) is dict, "AM_publication_jobs")
            jobs = api.pages(jobs_endpoint, "jobs", first.get("total_count"))
            selected = [job for job in jobs if job.get("name") == "alertmanager-main-publication"]
            require(len(selected) <= 1, "AM_publication_unique_job")
            if selected:
                job = selected[0]
                require(
                    type(job.get("id")) is int
                    and job["id"] > 0
                    and type(job.get("run_id")) is int
                    and job["run_id"] == run["id"]
                    and job.get("head_sha") == publisher,
                    "AM_publication_job_binding",
                )
                if job.get("status") == "completed" and job.get("conclusion") == "success":
                    for ancestor, descendant, suffix in (
                        (merge, publisher, "merge-to-publisher"),
                        (publisher, revision, "publisher-to-consumer"),
                    ):
                        native.run(
                            [*prefix, "merge-base", "--is-ancestor", ancestor, descendant],
                            "AM-publication-" + str(run["id"]) + "-" + suffix,
                            environment,
                            cwd=root,
                            maximum_seconds=8,
                        )
                    if upstream == "0.34.2":
                        observed = current_observation(run, job, publisher)
                        if observed is not None:
                            positive.append(
                                {
                                    "run": run,
                                    "job": job,
                                    "merge": merge,
                                    "current_observation": observed,
                                    "upstream_version": upstream,
                                }
                            )
                    else:
                        historical = _alertmanager_regular_sources(
                            root, merge, work / (str(run["id"]) + "-merged-sources"), deadline
                        )
                        published = _alertmanager_regular_sources(
                            root,
                            publisher,
                            work / (str(run["id"]) + "-publisher-sources"),
                            deadline,
                        )
                        require(
                            historical == published, "AM_publication_historical_six_source_drift"
                        )
                        positive.append(
                            {"run": run, "job": job, "merge": merge, "upstream_version": upstream}
                        )
        require(bool(positive), "AM_positive_publication_predecessor_missing")
        if upstream == "0.34.2":
            require(len(positive) == 1, "AM_current_subject_publication_ambiguous_HOLD")
            return positive[0]
        return max(positive, key=lambda value: value["run"]["id"])
    except BaseException as error:
        proof_failure = error
        raise
    finally:
        try:
            (work / "native-observation.json").write_text(
                json.dumps({"native_records": native.records}, indent=2) + "\n"
            )
        except BaseException as error:
            if proof_failure is None:
                raise
            proof_failure.add_note("AM native proof retention failed: " + type(error).__name__)


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


def _alertmanager_qualified_payload(
    archive: Path,
    *,
    material_root: Path | None = None,
    current: bool = False,
    producer_recipe: bytes | None = None,
) -> dict[str, Any]:
    """Inspect complete retained AM inputs as data; no extraction or executable launch."""
    import zipfile
    from scripts.ci.prometheus_source_image import (
        MAX_CACHE_BYTES,
        _zip_members,
        one_object,
        require,
    )

    require(type(current) is bool, "AM_qualification_epoch_type")
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
    upstream_version = _alertmanager_upstream_version(root_bytes, current=current)
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
    require(
        replays[0]["version"]
        == (
            b"go version go1.27.3 linux/amd64\n"
            if current
            else b"go version go1.27.2 linux/amd64\n"
        ),
        "AM_retained_Go_version",
    )
    delta = report["delta"]
    require(
        type(delta) is list
        and (bool(delta) if upstream_version == "0.34.1" else delta == [])
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
        == (
            {"golang.org/x/net": "v0.60.0", "google.golang.org/grpc": "v1.83.2"}
            if upstream_version == "0.34.1"
            else {}
        ),
        "AM_source_epoch_dependency_action",
    )
    if upstream_version == "0.34.2":
        for replay in replays:
            require(
                replay["original"] == replay["derived"] and replay["delta"] == delta,
                "AM_upstream_noop_lock_replay",
            )
            modules = replay["modules"]
            require(type(modules) is list, "AM_upstream_modules_shape")
            selected_modules = {row["Path"]: row.get("Version") for row in modules}
            require(
                len(selected_modules) == len(modules)
                and selected_modules.get("golang.org/x/net") == "v0.60.0"
                and selected_modules.get("google.golang.org/grpc") == "v1.83.2",
                "AM_upstream_existing_module_targets",
            )
            require(
                sha256(replay["original"]["go.mod"]).hexdigest()
                == "55a63e9214662673cdbf865dd859b2d62da89f6d5b32b2165ec80f5af3fc6139"
                and sha256(replay["original"]["go.sum"]).hexdigest()
                == "4ab3b4e64e70b2cca7be33ac1d572e659595e17c98703a26efb5b32790ea1cbf",
                "AM_upstream_original_lock_identity",
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
    _alertmanager_qualified_native(files, report, upstream_version=upstream_version)
    require(
        report["loaded_base_ID"]
        == _alertmanager_loaded_base(
            [one_object(files["public-base-inspect.stdout"])], current=current
        ),
        "AM_loaded_base_binding",
    )
    require(
        root_bytes["base-image.tar"] == files["base-retention/base-image.tar"],
        "AM_retained_base_bytes",
    )
    plan = _alertmanager_input_plan(
        root_bytes,
        frozen_files,
        replays[0]["derived"],
        material_root=material_root,
        current=current,
        producer_recipe=producer_recipe,
    )
    from scripts.ci.prometheus_source_image import GO, CURRENT_GO

    require(
        sha256(root_bytes["go-toolchain.tar.gz"]).hexdigest()
        == (CURRENT_GO if current else GO).digest,
        "AM_retained_Go_archive",
    )
    return {
        "frozen_sha256": frozen["sha256"],
        "frozen_members": len(declared_members),
        "artifact_files": len(declared),
        "delta": report["delta"],
        "source_files": replays[0]["source"],
        "root_inputs": {name: sha256(raw).hexdigest() for name, raw in root_bytes.items()},
        "loaded_base": one_object(files["public-base-inspect.stdout"]),
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


def _alertmanager_qualified_native(
    files: dict[str, bytes], report: dict[str, Any], *, upstream_version: str = "0.34.1"
) -> None:
    """Cross-bind the existing native protocol and every terminal output; no native call."""
    from scripts.ci.prometheus_source_image import one_object, require

    require(upstream_version in ("0.34.1", "0.34.2"), "AM_native_upstream_epoch")
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
                (
                    "two-authored-replacements"
                    if upstream_version == "0.34.1"
                    else "upstream-target-replay"
                ),
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
    root_bytes: dict[str, bytes],
    frozen_files: dict[str, dict[str, Any]],
    locks: dict[str, bytes],
    *,
    material_root: Path | None = None,
    current: bool = False,
    producer_recipe: bytes | None = None,
) -> dict[str, Any]:
    """Bound the retained source/UI and declare future argv, never execute a build."""
    from scripts.ci.prometheus_source_image import BASE, require

    require(type(current) is bool, "AM_plan_epoch_type")

    upstream_version = _alertmanager_upstream_version(root_bytes, current=current)
    source_rows = {}
    source_bytes = {}
    ui_hashes = {}
    for artifact in load_manifest(DEFAULT_MANIFEST, artifact="alertmanager"):
        is_ui = artifact.name == "alertmanager-ui"
        raw = root_bytes["ui.tar.gz" if is_ui else "source.tar.gz"]
        if upstream_version == "0.34.2":
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
        source_bytes.get("VERSION") == (upstream_version + "\n").encode("ascii")
        and b"//go:embed app/dist" in source_bytes.get("ui/web.go", b""),
        "AM_source_UI_recipe",
    )
    context = []
    for path in ("deploy/alertmanager/Containerfile", "deploy/alertmanager/alertmanager.yml"):
        if path == "deploy/alertmanager/Containerfile" and producer_recipe is not None:
            require(type(producer_recipe) is bytes, "AM_producer_recipe_bytes")
            raw = producer_recipe
        else:
            raw = ((material_root if material_root is not None else REPO_ROOT) / path).read_bytes()
        require(
            sha256(raw).hexdigest()
            == (
                (
                    _ALERT_CURRENT_ASSEMBLY_RECIPE_SHA256
                    if current
                    else _ALERT_ASSEMBLY_RECIPE_SHA256
                )
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
    flags = _ALERT_UPSTREAM_0342_METADATA if upstream_version == "0.34.2" else _ALERT_BUILD_METADATA
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
            **({"GOENV": "off", "GOWORK": "off"} if upstream_version == "0.34.2" else {}),
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
            *(["--build-arg", f"SOURCE_DATE_EPOCH={_ALERT_ASSEMBLY_EPOCH}"] if current else []),
            "--annotation",
            "manifest-descriptor:org.opencontainers.image.ref.name=candidate",
            "--network=none",
            "--pull=false",
            "--build-context",
            (
                BASE + "=oci-layout:///inputs/base-layout@<UNOBSERVED_CURRENT_EXPORT>"
                if current
                else "gcr.io/distroless/static-debian13@sha256:2293b36c7c9082bf4115aab724b4d2cddec82c8eba39bf27ac0517e159acf150=oci-layout:///inputs/base-layout@sha256:528f8a8d69ed17bdf99f19ade62e0a0e4c385de2791a94f4fa3c6286d8dad22c"
            ),
            "--file",
            "/context/Containerfile",
            "--output",
            "type=oci,tar=false,"
            + ("rewrite-timestamp=true," if current else "")
            + "dest=/out/candidate-layout",
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


def _alertmanager_base_export_inventory(
    base_archive: Path, *, destination: Path | None = None
) -> tuple[list[dict[str, Any]], set[str]]:
    """Read the finite Docker save export once; optionally perform its private extraction."""
    from scripts.ci.prometheus_source_image import require

    metadata = base_archive.lstat()
    require(
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_nlink == 1
        and 0 < metadata.st_size <= 16 * 1024**2,
        "AM_base_export_archive",
    )
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    files: set[str] = set()
    directories: set[str] = set()
    total = 0
    with tarfile.open(base_archive, mode="r:") as saved:
        for member in saved:
            parts = member.name.split("/")
            require(
                all(part not in ("", ".", "..") for part in parts)
                and "\\" not in member.name
                and "\x00" not in member.name
                and member.name not in seen
                and len(seen) < 33
                and (member.isfile() or member.isdir()),
                "AM_base_export_member",
            )
            seen.add(member.name)
            parents = {"/".join(parts[:number]) for number in range(1, len(parts))}
            require(not parents.intersection(files), "AM_base_export_file_parent")
            directories.update(parents)
            if member.isdir():
                require(member.name not in files and member.size == 0, "AM_base_export_directory")
                directories.add(member.name)
                if destination is not None:
                    destination.joinpath(*parts).mkdir(mode=0o700, parents=True, exist_ok=True)
                continue
            require(member.name not in directories, "AM_base_export_directory_as_file")
            require(0 <= member.size <= metadata.st_size, "AM_base_export_size")
            total += member.size
            require(total <= metadata.st_size, "AM_base_export_total")
            stream = saved.extractfile(member)
            require(stream is not None, "AM_base_export_missing_bytes")
            raw = cast(BinaryIO, stream).read(member.size + 1)
            require(len(raw) == member.size, "AM_base_export_file")
            files.add(member.name)
            if destination is not None:
                target = destination.joinpath(*parts)
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                require(not target.exists(), "AM_base_export_file")
                with target.open("xb") as output:
                    output.write(raw)
                target.chmod(0o600)
            rows.append({"path": member.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    return sorted(rows, key=lambda row: row["path"]), directories


def _alertmanager_current_base_graph(layout: Path) -> dict[str, Any]:
    """Delegate both finite current export transports to the P content owner."""
    from scripts.ci.prometheus_source_image import native_base_export_graph

    return cast(dict[str, Any], native_base_export_graph(layout))


def _alertmanager_support_observation(
    archive: Path, output: Path, *, qualification_sha256: str | None = None, current: bool = False
) -> dict[str, Any]:
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

    expected_q = _ALERT_Q_ZIP_SHA256 if qualification_sha256 is None else qualification_sha256
    require(
        type(expected_q) is str and _HEX_RE.fullmatch(expected_q) is not None,
        "AM_support_qualified_Q_digest",
    )
    require(file_hash(archive) == expected_q, "AM_support_exact_retained_Q")
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
    layout_rows, _ = _alertmanager_base_export_inventory(base_archive, destination=layout)
    require(type(current) is bool, "AM_support_observation_epoch")
    if current:
        _alertmanager_loaded_base([original_base], current=True)
        descriptor = _alertmanager_current_base_graph(layout)
    else:
        descriptor = _layout_root(layout)
    manifest = one_object(_blob(layout, descriptor))
    configuration = one_object(_blob(layout, manifest["config"]))
    from scripts.ci.prometheus_source_image import BASE_CONFIG

    config_digest = BASE_CONFIG if current else _ALERT_BASE_CONFIG
    require(
        manifest["config"]["digest"] == config_digest
        and type(manifest.get("layers")) is list
        and configuration.get("rootfs", {}).get("diff_ids") == original_base["RootFS"]["Layers"]
        and configuration.get("os") == original_base["Os"]
        and configuration.get("architecture") == original_base["Architecture"],
        "AM_base_export_config_diffIDs",
    )
    if not current:
        require(
            [layer.get("digest") for layer in manifest["layers"]]
            == original_base["RootFS"]["Layers"],
            "AM_historical_export_diffIDs",
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
            "config": config_digest,
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
        result["vulnerability_control"] = _alertmanager_vulnerability_control(
            vulnerable, old_id, current=qualification_sha256 is not None
        )
        base_scan = scan("image", base_archive, "base-full-supported-scan")
        require(
            base_scan.get("ArtifactType") == "container_image"
            and type(base_scan.get("Metadata")) is dict
            and base_scan["Metadata"].get("ImageID") == config_digest,
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
    report: dict[str, Any],
    *,
    probe_path: str | None = None,
    comparison_subject: str | None = None,
    comparison_input: str | None = None,
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
    require(
        (comparison_subject is None) == (comparison_input is None), "AM_inventory_comparison_pair"
    )
    comparison_target = None
    if comparison_subject is not None:
        operating_system = report.get("Metadata", {}).get("OS", {})
        require(
            probe_path is None
            and type(comparison_input) is str
            and Path(comparison_input).is_absolute()
            and ".." not in Path(comparison_input).parts
            and report.get("ArtifactName") == comparison_input
            and report.get("ArtifactID") == comparison_subject
            and report.get("Metadata", {}).get("ImageID") == comparison_subject
            and report.get("ArtifactType") == "container_image"
            and type(report.get("SchemaVersion")) is int
            and report["SchemaVersion"] == 2
            and type(operating_system) is dict
            and all(
                type(operating_system.get(key)) is str and bool(operating_system[key])
                for key in ("Family", "Name")
            ),
            "AM_inventory_actual_native_input_subject",
        )
        suffix = " (" + operating_system["Family"] + " " + operating_system["Name"] + ")"
        os_rows = [
            row
            for row in report.get("Results", [])
            if type(row) is dict and row.get("Class") == "os-pkgs"
        ]
        require(
            len(os_rows) == 1
            and os_rows[0].get("Type") == operating_system["Family"]
            and os_rows[0].get("Target") == comparison_input + suffix,
            "AM_inventory_exact_native_OS_target",
        )
        comparison_target = (comparison_input + suffix, comparison_subject + suffix)
    packages, findings, targets = [], [], []
    for row in report.get("Results", []):
        require(
            type(row) is dict and type(row.get("Target")) is str and row["Target"],
            "AM_support_target",
        )
        targets.append(
            comparison_target[1]
            if comparison_target is not None and row["Target"] == comparison_target[0]
            else row["Target"]
        )
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
    if comparison_target is not None:
        from copy import deepcopy

        # Preserve every per-result association and unknown field. Only the
        # proven native OS input-context Target changes in this comparison view.
        compared = deepcopy(report["Results"])
        for row in compared:
            if row.get("Class") == "os-pkgs":
                row["Target"] = comparison_target[1]
        return {"Results": compared, "OS": deepcopy(report["Metadata"]["OS"])}
    return {
        "targets": targets,
        "packages": packages,
        "findings": findings,
        "missing_Secrets_fields_are_not_execution_evidence": True,
    }


def _alertmanager_vulnerability_control(
    report: dict[str, Any], image_id: str, *, current: bool = False
) -> dict[str, Any]:
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
    require(type(current) is bool, "AM_control_epoch_type")
    found, targets, ca_findings = [], [], []
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
            is_ca_finding = finding.get("VulnerabilityID") == "CVE-2026-111943"
            if is_ca_finding or finding["Severity"] in ("HIGH", "CRITICAL"):
                identifier = finding.get("PkgIdentifier")
                require(type(identifier) is dict, "AM_vulnerable_control_PURL")
                require(
                    row.get("Class") == "lang-pkgs"
                    and row.get("Type") == "gobinary"
                    and row["Target"] in ("bin/alertmanager", "bin/amtool"),
                    "AM_known_vulnerable_control_inventory_changed_HOLD",
                )
                occurrence = (
                    row["Target"],
                    finding.get("VulnerabilityID"),
                    identifier.get("PURL"),
                    finding["Severity"],
                )
                if is_ca_finding:
                    require(
                        current
                        and identifier.get("PURL") == "pkg:golang/stdlib@v1.26.8"
                        and finding["Severity"] in ("HIGH", "MEDIUM"),
                        "AM_known_vulnerable_control_inventory_changed_HOLD",
                    )
                    ca_findings.append(occurrence)
                if finding["Severity"] in ("HIGH", "CRITICAL"):
                    found.append(occurrence)
    if current:
        # Retain both observed whole-report scores without losing mandatory CA detection.
        require(
            len(ca_findings) == 2
            and {item[0] for item in ca_findings} == {"bin/alertmanager", "bin/amtool"}
            and len({item[3] for item in ca_findings}) == 1,
            "AM_known_vulnerable_control_inventory_changed_HOLD",
        )
        expected |= {item for item in ca_findings if item[3] == "HIGH"}
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


def _alertmanager_limits(*, caller: bool = False) -> dict[str, int]:
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
    if caller:
        kind = os.environ.get("ALERTMANAGER_CALLER_KIND", "")
        maintained = {
            "ci-lint": (184, 6),
            "shared-pr": (165, 5),
            "shared-main": (285, 5),
            "standalone": (78, 2),
            "third-main": (102, 8),
        }
        require(kind in maintained, "AM_caller_resource_route")
        raw = os.environ.get("ALERTMANAGER_JOB_TIMEOUT_MINUTES", "")
        require(re.fullmatch(r"[1-9][0-9]{0,2}", raw) is not None, "AM_caller_job_budget_shape")
        require(sum(maintained[kind]) <= int(raw) <= 360, "AM_caller_maintained_steps_and_margin")
        if kind in ("ci-lint", "third-main"):
            native_minutes = os.environ.get("ALERTMANAGER_GENERIC_NATIVE_MINUTES", "")
            require(
                re.fullmatch(r"[1-9][0-9]?", native_minutes) is not None
                and int(native_minutes) == 40,
                "AM_generic_native_step_budget",
            )
        if kind == "ci-lint":
            require(
                os.environ.get("ALERTMANAGER_LINT_CHECK_MINUTES") == "60", "AM_lint_step_budget"
            )
        if kind == "shared-main":
            values = [
                os.environ.get(key, "")
                for key in (
                    "PROMETHEUS_PUBLICATION_WAIT_SECONDS",
                    "PROMETHEUS_CONSUME_SECONDS",
                    "PROMETHEUS_CLEANUP_SECONDS",
                    "PROMETHEUS_SECURITY_RESERVE_SECONDS",
                )
            ]
            require(
                all(re.fullmatch(r"[1-9][0-9]{0,4}", value) is not None for value in values),
                "AM_shared_Prom_budget_shape",
            )
            wait, consume, cleanup, reserve = map(int, values)
            require(
                wait == 10800
                and consume == 900
                and cleanup == 120
                and reserve == 2400
                and wait + consume + 2 * cleanup + reserve <= int(raw) * 60,
                "AM_shared_Prom_reservation",
            )
    return result


def _alertmanager_source_snapshot(
    api: GitHubRead,
    source: str,
    *,
    accepted: bool = False,
    controller_templates: bool = False,
    upstream_version: str | None = None,
) -> dict[str, bytes]:
    """The existing AM finite Contents reader; never call the Prometheus-only source selector."""
    import base64
    import hashlib
    from scripts.ci.prometheus_source_image import require

    require(not (accepted and controller_templates), "AM_source_cases_are_disjoint")
    selected = _alertmanager_accepted_producer() if accepted else None
    if selected is not None:
        require(source == selected["source"], "AM_accepted_producer_exact_selectors")
    leaf_sha: dict[str, str] = {}
    if controller_templates:
        require(
            type(source) is str
            and re.fullmatch(r"[0-9a-f]{40}", source) is not None
            and source == os.environ.get("ALERTMANAGER_CONTROLLER_SOURCE"),
            "AM_designated_controller_data_source",
        )
        endpoint = "/repos/Katsiarynakavaleuskaya/PulsePlate"
        commit = api.json(endpoint + "/git/commits/" + source)
        tree_record = commit.get("tree") if type(commit) is dict else None
        root_tree = tree_record.get("sha") if type(tree_record) is dict else None
        require(
            type(commit) is dict
            and commit.get("sha") == source
            and type(root_tree) is str
            and re.fullmatch(r"[0-9a-f]{40}", root_tree) is not None,
            "AM_controller_data_commit_tree",
        )
        root_tree = cast(str, root_tree)
        trees: dict[str, dict[str, Any]] = {}
        for path in _ALERT_SELECTION_FILES[:5]:
            tree_sha = root_tree
            parts = path.split("/")
            for index, part in enumerate(parts):
                if tree_sha not in trees:
                    tree = api.json(endpoint + "/git/trees/" + tree_sha)
                    require(
                        type(tree) is dict
                        and tree.get("sha") == tree_sha
                        and tree.get("truncated") is False
                        and type(tree.get("tree")) is list
                        and all(
                            type(row) is dict and type(row.get("path")) is str
                            for row in tree["tree"]
                        )
                        and len({row["path"] for row in tree["tree"]}) == len(tree["tree"]),
                        "AM_controller_data_complete_distinct_tree",
                    )
                    trees[tree_sha] = {row["path"]: row for row in tree["tree"]}
                row = trees[tree_sha].get(part)
                leaf = index == len(parts) - 1
                require(
                    type(row) is dict
                    and row.get("type") == ("blob" if leaf else "tree")
                    and row.get("mode") == ("100644" if leaf else "040000")
                    and type(row.get("sha")) is str
                    and re.fullmatch(r"[0-9a-f]{40}", row["sha"]) is not None,
                    "AM_controller_data_regular_git_path",
                )
                row = cast(dict[str, Any], row)
                tree_sha = cast(str, row["sha"])
            leaf_sha[path] = tree_sha
    paths = (
        _ALERT_SELECTION_FILES[:5]
        if controller_templates
        else (*_ALERT_Q_SOURCE_FILES, "tests/test_notify_premium_alias_checkpoint_failure.py")
    )
    result = {}
    for path in paths:
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
        if controller_templates:
            require(record.get("sha") == leaf_sha[path], "AM_controller_data_leaf_cross_binding")
        if selected is not None:
            require(
                sha256(raw).hexdigest() == selected["source_files"][path],
                "AM_accepted_producer_source_bytes",
            )
        result[path] = raw
    if upstream_version is not None:
        require(
            upstream_version == "0.34.2" and not controller_templates, "AM_source_snapshot_upstream"
        )
        require(
            result["scripts/ci/docker_source_artifacts.json"] == DEFAULT_MANIFEST.read_bytes(),
            "AM_current_upstream_catalog_bytes",
        )
        artifacts = load_manifest(DEFAULT_MANIFEST, artifact="alertmanager")
        require(
            {row.name: row.version for row in artifacts}
            == {"alertmanager-source": _ALERT_UPSTREAM_0342_REVISION, "alertmanager-ui": "0.34.2"},
            "AM_current_upstream_catalog_tuple",
        )
    return result


def _alertmanager_candidate_members(archive: Path) -> dict[str, bytes]:
    """Reuse the existing complete retained execution footer for candidate/publication reads."""
    import zipfile
    from scripts.ci.prometheus_source_image import _zip_members, one_object, require

    files: dict[str, bytes] = _zip_members(archive)
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
    return files


def _alertmanager_candidate_native_records(
    files: dict[str, bytes], records: Any, prefix: str, phase: str
) -> None:
    """Existing raw native-record binding shared by retained execution observations."""
    from scripts.ci.prometheus_source_image import require

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


def _alertmanager_candidate_scan_evidence(
    files: dict[str, bytes] | Path,
    security: dict[str, Any],
    *,
    current: bool,
    comparison_subject: str | None = None,
    deadline: float | None = None,
) -> dict[str, Any] | None:
    """Reuse the existing full scan/positive-control raw evidence contract."""
    from scripts.ci.prometheus_source_image import file_hash, one_object, require

    def raw(name: str) -> bytes:
        if isinstance(files, Path):
            require(name.startswith("security-evidence/"), "AM_security_evidence_prefix")
            leaf = files / name.removeprefix("security-evidence/")
            require(leaf.stat().st_size <= 64 * 1024**2, "AM_security_evidence_bound")
            expected = file_hash(leaf, deadline)
            value = leaf.read_bytes()
            require(sha256(value).hexdigest() == expected, "AM_security_evidence_read_drift")
            return value
        return files[name]

    scans = {
        PurePosixPath(row["stdout"]).name.removesuffix(".stdout"): row
        for row in security["native_records"]
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
        one_object(raw("security-evidence/candidate-secret-positive.private.json")),
        one_object(raw("security-evidence/candidate-secret-negative.private.json")),
        scans["candidate-secret-positive"]["argv"][-1],
        scans["candidate-secret-negative"]["argv"][-1],
    )
    require(controls == security.get("secrets"), "AM_candidate_actual_secret_controls")
    old = _alertmanager_vulnerability_control(
        one_object(raw("security-evidence/candidate-known-vulnerable-control.private.json")),
        "sha256:53622b714941158bc20cc92a7571aef515556218eef914b7b8ec5b2a0cb6f607",
        current=current,
    )
    require(old == security.get("old_control"), "AM_candidate_actual_vulnerable_control")
    if comparison_subject is not None:
        report = one_object(raw("security-evidence/candidate-full-supported.private.json"))
        require(
            _alertmanager_support_inventory(report) == security.get("candidate"),
            "AM_security_raw_inventory_observation",
        )
        arguments = scans["candidate-full-supported"]["argv"]
        require(
            len(arguments) >= 2 and arguments[-2] == "--input", "AM_security_native_layout_input"
        )
        return _alertmanager_support_inventory(
            report, comparison_subject=comparison_subject, comparison_input=arguments[-1]
        )
    return None


def _alertmanager_candidate_payload(
    archive: Path,
    destination: Path,
    source_files: dict[str, bytes],
    inspected: dict[str, Any],
    support: Path,
    *,
    qualification: dict[str, Any] | None = None,
    support_binding: dict[str, Any] | None = None,
    support_report: dict[str, Any] | None = None,
    merged_producer: dict[str, Any] | None = None,
    merged_material: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate the retained accepted A against independent source and full graph identity."""
    from scripts.ci.prometheus_source_image import (
        fresh_directory,
        one_object,
        require,
        unpack_layout,
    )

    accepted = _alertmanager_accepted_producer()
    current = accepted["source"] != _ALERT_HISTORICAL_C10["source"]
    merged = merged_producer is not None
    require(merged == (merged_material is not None), "AM_H_payload_material_pair")
    require(not merged or current, "AM_H_requires_current_C_subject")
    producer = accepted if merged_producer is None else merged_producer
    producer_source = producer["source"]
    require(
        (
            all(value is not None for value in (qualification, support_binding, support_report))
            if current
            else all(value is None for value in (qualification, support_binding, support_report))
        ),
        "AM_candidate_upstream_epoch",
    )
    if current:
        qualification = cast(dict[str, Any], qualification)
        support_binding = cast(dict[str, Any], support_binding)
        support_report = cast(dict[str, Any], support_report)
        require(
            qualification.get("source") == support_binding.get("source") == producer_source
            and qualification.get("source_files")
            == support_binding.get("source_files")
            == {key: producer["source_files"][key] for key in _ALERT_Q_SOURCE_FILES},
            "AM_candidate_current_Q_S_source",
        )
    require(
        sha256(archive.read_bytes()).hexdigest() == producer["zip_sha256"],
        "AM_accepted_producer_archive_bytes",
    )
    require(
        {path: sha256(raw).hexdigest() for path, raw in source_files.items()}
        == producer["source_files"],
        "AM_accepted_producer_source_bytes",
    )
    files = _alertmanager_candidate_members(archive)
    result: dict[str, Any] = one_object(files["candidate-observation.json"])
    require(
        result.get("source") == producer_source
        and result.get("graph") == accepted["graph"]
        and (merged or result.get("OCI_archive_sha256") == accepted["OCI_archive_sha256"]),
        "AM_accepted_producer_subject_graph",
    )
    upstream = _alertmanager_upstream_identity(inspected["root_inputs"], current=current)
    if merged:
        admission = result.get("producer_admission", {})
        require(
            upstream == "0.34.2"
            and type(admission) is dict
            and admission.get("mode") == "H"
            and admission.get("source") == producer_source
            and admission.get("branch") == "main"
            and admission.get("run") == producer["run"]
            and admission.get("job") == producer["job"]
            and admission.get("merge_commit") == producer["merge_commit"]
            and admission.get("expected_C") == accepted
            and result.get("material") == merged_material
            and type(result.get("host_inputs")) is dict
            and bool(result["host_inputs"]),
            "AM_H_actual_producer_material_subject",
        )
        require(
            cast(dict[str, Any], merged_material).get("source") == producer_source,
            "AM_H_material_source",
        )
    elif upstream == "0.34.2":
        admission = result.get("producer_admission", {})
        require(
            type(admission) is dict
            and admission.get("mode") == "C"
            and admission.get("source") == producer_source
            and admission.get("branch") == _ALERT_Q_BRANCH
            and admission.get("run") == accepted["run"]
            and admission.get("job") == accepted["job"]
            and admission.get("expected_C") is None
            and admission.get("merge_commit") is None,
            "AM_current_C_producer_scope",
        )
    require(
        result.get("status")
        == (
            "OBSERVED_MERGED_H_REBUILD_SECURITY_NATIVE"
            if merged
            else (
                "OBSERVED_PR2494_C_SECURITY_NATIVE"
                if upstream == "0.34.2"
                else (
                    "OBSERVED_PRODUCER_IMAGE_SECURITY"
                    if current
                    else "OBSERVED_NATIVE_SECURITY_ACCEPTED"
                )
            )
        )
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
        (
            result.get("upstream") == {"qualification": qualification, "support": support_binding}
            if current
            else result.get("upstream", {}).get("qualification", {}).get("zip_sha256")
            == _ALERT_Q_ZIP_SHA256
            and result["upstream"].get("support", {}).get("zip_sha256") == _ALERT_S_ZIP_SHA256
        ),
        "AM_candidate_Q_S_predecessors",
    )
    if _alertmanager_upstream_identity(inspected["root_inputs"], current=current) == "0.34.2":
        require(
            result.get("root_inputs") == inspected["root_inputs"],
            "AM_candidate_source_input_binding",
        )
    for phase, records, prefix in (
        ("pair", result.get("native_records"), "pair-evidence"),
        ("security", result.get("security", {}).get("native_records"), "security-evidence"),
        ("native", result.get("native", {}).get("native_records"), "native-evidence"),
    ):
        _alertmanager_candidate_native_records(files, records, prefix, phase)
    marker = (
        b"native_AM_merged_H_full_controls=pass"
        if merged
        else (
            b"native_AM_producer_image_controls=pass"
            if current
            else b"native_AM_full_candidate_controls=pass"
        )
    )
    opposite = (
        b"native_AM_full_candidate_controls=pass"
        if current
        else b"native_AM_producer_image_controls=pass"
    )
    native_lines = files["native-evidence/full-AM-native.stdout"].splitlines()
    require(
        native_lines.count(marker) == 1
        and opposite not in native_lines
        and (not merged or b"native_AM_producer_image_controls=pass" not in native_lines)
        and result["native"].get("validation_scope", "selected_consumer")
        == (
            "merged_H_selected_image"
            if merged
            else "producer_image" if current else "selected_consumer"
        ),
        "AM_candidate_native_terminal",
    )
    require(
        result["security"].get("scanner", {}).get("sha256") == _ALERT_TRIVY_SHA256
        and result["security"]["scanner"].get("DB")
        == (cast(dict[str, Any], support_report)["scanner"]["DB"] if current else _ALERT_DB),
        "AM_candidate_exact_scanner_DB",
    )
    actual_build_information = {}
    for binary in ("alertmanager", "amtool"):
        observed_build = _alertmanager_build_information(
            files["pair-evidence/" + binary + "-buildinfo-attach.stdout"],
            binary,
            current=current,
            upstream_version=_alertmanager_upstream_identity(
                inspected["root_inputs"], current=current
            ),
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
            current=current,
            upstream_version=_alertmanager_upstream_identity(
                inspected["root_inputs"], current=current
            ),
            proof_mode="dynamic",
        )
        == result["security"].get("candidate"),
        "AM_candidate_full_report_not_summary_only",
    )
    _alertmanager_candidate_scan_evidence(files, result["security"], current=current)
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
        _alertmanager_candidate_graph(layout, support, result["graph"]["files"], current=current)
        == result["graph"],
        "AM_candidate_actual_graph_payload",
    )
    return result


def _alertmanager_current_support_transport(
    retained: ZipFile, entries: list[ZipInfo], native_files: set[str], inspected: dict[str, Any]
) -> None:
    """Bind every uploaded current API evidence member using the existing inventory owner."""
    from scripts.ci.prometheus_source_image import require

    names = [info.filename for info in entries]
    # Reuse the existing native inventory shape for the actual API transport.
    # The authenticated outer ZIP binds this report; no fixed historical count
    # can describe a current, completely paginated API observation.
    api_files = inspected.get("github_read_evidence")
    require(type(api_files) is list and bool(api_files), "AM_support_API_inventory")
    declared_api: set[str] = set()
    for row in cast(list[Any], api_files):
        require(
            type(row) is dict
            and set(row) == {"path", "size", "mode", "sha256"}
            and type(row.get("path")) is str
            and re.fullmatch(r"GitHub-[1-9][0-9]*\.(json|stdout|stderr)", row["path"]) is not None
            and type(row.get("size")) is int
            and 0 <= row["size"] <= 16 * 1024**2
            and type(row.get("mode")) is int
            and row["mode"] in (0o600, 0o644)
            and type(row.get("sha256")) is str
            and _HEX_RE.fullmatch(row["sha256"]) is not None,
            "AM_support_API_member",
        )
        name = "github-read-evidence/" + row["path"]
        require(name not in declared_api, "AM_support_API_duplicate")
        declared_api.add(name)
        require(name in names, "AM_support_API_missing")
        raw = retained.read(name)
        require(
            len(raw) == row["size"]
            and sha256(raw).hexdigest() == row["sha256"]
            and stat.S_IMODE(retained.getinfo(name).external_attr >> 16) == row["mode"],
            "AM_support_API_member_bytes",
        )
    transport_files = native_files | declared_api | {"input-inspection.json"}
    require(
        {info.filename for info in entries if not info.is_dir()} == transport_files,
        "AM_support_complete_current_transport",
    )
    allowed_directories = {
        str(parent) + "/"
        for name in transport_files
        for parent in PurePosixPath(name).parents
        if str(parent) != "."
    }
    require(
        {info.filename for info in entries if info.is_dir()} <= allowed_directories,
        "AM_support_current_transport_directories",
    )


def _alertmanager_current_support_base(
    destination: Path, report: dict[str, Any], qualification_payload: dict[str, Any]
) -> None:
    """Bind the complete materialized current S base to actual authenticated Q archive bytes."""
    from scripts.ci.prometheus_source_image import (
        BASE_CONFIG,
        exact_data,
        tree_inventory,
        file_hash,
        require,
    )

    expected_archive = qualification_payload["root_inputs"]["base-image.tar"]
    require(
        file_hash(destination / "base-image.tar")
        == expected_archive
        == report["base"]["archive_sha256"],
        "AM_current_S_exact_Q_export",
    )
    q_rows, q_directories = _alertmanager_base_export_inventory(destination / "base-image.tar")
    layout = destination / "base-layout"
    inventory = tree_inventory(layout, maximum=16 * 1024**2)
    for row in inventory:
        require(
            (layout / row["path"]).lstat().st_nlink == 1 and row["mode"] == 0o600,
            "AM_current_export_regular_single_link",
        )
    exact_data(
        [{"path": row["path"], "bytes": row["size"], "sha256": row["sha256"]} for row in inventory],
        q_rows,
    )
    actual_directories = {
        path.relative_to(layout).as_posix() for path in layout.rglob("*") if path.is_dir()
    }
    exact_data(actual_directories, q_directories)
    require(
        all(stat.S_IMODE((layout / name).lstat().st_mode) == 0o700 for name in q_directories),
        "AM_current_export_directory_mode",
    )
    exact_data(
        sorted(report["base"]["complete_export_file_inventory"], key=lambda row: row["path"]),
        q_rows,
    )
    descriptor = _alertmanager_current_base_graph(layout)
    exact_data(descriptor, report["base"]["actual_local_OCI_descriptor"])
    exact_data(report["base"]["config"], BASE_CONFIG)
    exact_data(report["base"]["RootFS"], qualification_payload["loaded_base"]["RootFS"])


def _alertmanager_support_payload(
    archive: Path,
    destination: Path,
    *,
    qualification: dict[str, Any] | None = None,
    support_binding: dict[str, Any] | None = None,
    qualification_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read the exact observed S artifact, with the incumbent native payload inventory."""
    import shutil
    import zipfile
    from scripts.ci.prometheus_source_image import file_hash, fresh_directory, one_object, require

    require((qualification is None) == (support_binding is None), "AM_support_epoch_pair")
    current = support_binding is not None
    require(current == (qualification_payload is not None), "AM_support_Q_payload_pair")
    expected_zip = _ALERT_S_ZIP_SHA256
    expected_source = _ALERT_S_SOURCE
    expected_q = _ALERT_Q_ZIP_SHA256
    if current:
        qualification = cast(dict[str, Any], qualification)
        support_binding = cast(dict[str, Any], support_binding)
        require(
            support_binding.get("source") == qualification.get("source")
            and type(support_binding.get("source")) is str
            and re.fullmatch(r"[0-9a-f]{40}", support_binding["source"]) is not None
            and all(
                type(value) is str and _HEX_RE.fullmatch(value) is not None
                for value in (support_binding.get("zip_sha256"), qualification.get("zip_sha256"))
            ),
            "AM_support_current_upstream_binding",
        )
        expected_zip = support_binding["zip_sha256"]
        expected_source = support_binding["source"]
        expected_q = qualification["zip_sha256"]
    require(file_hash(archive) == expected_zip, "AM_exact_support_archive")
    fresh_directory(destination)
    with zipfile.ZipFile(archive) as retained:
        entries = retained.infolist()
        if not current:
            require(len(entries) == 134, "AM_support_complete_transport")
        require(len(entries) <= 250000, "AM_support_transport_member_bound")
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
            and (
                len(footer["files"]) == 91
                if not current
                else all(
                    type(row) is dict and type(row.get("path")) is str for row in footer["files"]
                )
                and sum(not row["path"].startswith("base-layout/") for row in footer["files"]) == 60
            )
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
        if current:
            _alertmanager_current_support_transport(retained, entries, actual, inspected)
    report: dict[str, Any] = one_object((destination / "support-observation.json").read_bytes())
    database = _ALERT_DB
    if current:
        scanner_record = report.get("scanner")
        require(
            type(scanner_record) is dict and type(scanner_record.get("DB")) is dict,
            "AM_support_current_DB_binding",
        )
        database = cast(dict[str, Any], scanner_record)["DB"]
        require(
            set(database) == set(_ALERT_DB)
            and all(
                type(value) is str and _HEX_RE.fullmatch(value) is not None
                for value in database.values()
            ),
            "AM_support_current_DB_fields",
        )
    if current:
        _alertmanager_current_support_base(
            destination, report, cast(dict[str, Any], qualification_payload)
        )
    else:
        require(
            report.get("base", {}).get("config") == _ALERT_BASE_CONFIG
            and report["base"]["actual_local_OCI_descriptor"]["digest"] == _ALERT_BASE_MANIFEST,
            "AM_historical_export_identity",
        )
    require(
        inspected.get("consumer_source") == expected_source
        and inspected.get("upstream", {}).get("zip_sha256") == expected_q
        and inspected.get("package_read", {}).get("metadata_read") is True
        and inspected["inspection"].get("support") == report
        and report.get("support_status") == "OBSERVED_NATIVE_SUPPORTED_DOMAIN"
        and report.get("compiler_starts") == report.get("logical_build_starts") == 0
        and report.get("owned_container_absence_observed") is True
        and report.get("probe", {}).get("sha256") == _ALERT_PROBE_SHA256
        and report.get("scanner", {}).get("sha256") == _ALERT_TRIVY_SHA256
        and report["scanner"]["DB"] == database
        and file_hash(destination / "probe-bin-bracket") == _ALERT_PROBE_SHA256
        and file_hash(destination / "trivy") == _ALERT_TRIVY_SHA256,
        "AM_support_native_input_binding",
    )
    for name, digest in database.items():
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
    require(file_hash(archive) == expected_zip, "AM_support_archive_drift")
    return report


def _alertmanager_materialize(archive: Path, destination: Path, deadline: float) -> Path:
    """Materialize only the already-qualified finite source/cache epoch, without acquisition."""
    import shutil
    import zipfile
    from scripts.ci.prometheus_source_image import (
        CURRENT_GO as GO,
        extract,
        fresh_directory,
        one_object,
        require,
    )

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


def _alertmanager_build_information(
    raw: bytes, binary: str, *, current: bool = False, upstream_version: str = "0.34.1"
) -> dict[str, Any]:
    """Interpret native Go build-info for the required pair, including embedded stdlib."""
    from scripts.ci.prometheus_source_image import require

    lines = raw.decode("utf-8").splitlines()
    require(type(current) is bool, "AM_build_info_epoch_type")
    require(
        upstream_version in ("0.34.1", "0.34.2") and (upstream_version == "0.34.1" or current),
        "AM_build_info_upstream_join",
    )
    compiler = "go1.27.3" if current else "go1.27.2"
    require(
        bool(lines) and lines[0] == "/out/" + binary + ": " + compiler, "AM_actual_Go_build_version"
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
        and main.get("Version") in ("(devel)", upstream_version, "v" + upstream_version)
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
        "Go": compiler,
        "dependencies": dependencies,
        "main": main,
        "path": path,
        "settings": settings,
        "raw_sha256": sha256(raw).hexdigest(),
    }


# Accepted native build-info and base-package oracle, bound to immutable S.
_ALERT_CURRENT_SCAN_ORACLE: dict[str, dict[str, Any]] = {
    "subject": {
        "source": "8aee3976d8f13027a5f2a38f0152ede0f4990156",
        "upstream_version": "0.34.2",
        "manifest": "sha256:e4b0453fb56079d8ee565f76c4029c34d0711215b2a72541cc060bdcbe9827d3",
        "config": "sha256:db6b5863659a4d2e4372cbf32602429299763e0efacc2c165dc7245c3e9df2ee",
        "binary_sha256": {
            "alertmanager": "4a871fe631f8b91e9f421f2ff9c3a4f2472d340cc654448155cb8722cae125d1",
            "amtool": "e041a8aadb52426695dcee36f2ce854ca26d82f53a2f0379d4faaabfb316b954",
        },
    },
    "expected_OS": {
        "OS": {"Family": "debian", "Name": "13.7"},
        "packages": [
            [
                "os-pkgs",
                "debian",
                "base-files@13.8+deb13u7",
                "base-files",
                "13.8+deb13u7",
                "amd64",
                "base-files",
                "13.8+deb13u7",
                "pkg:deb/debian/base-files@13.8%2Bdeb13u7?arch=amd64&distro=debian-13.7",
            ],
            [
                "os-pkgs",
                "debian",
                "ca-certificates@20250419+deb13u1",
                "ca-certificates",
                "20250419+deb13u1",
                "all",
                "ca-certificates",
                "20250419+deb13u1",
                "pkg:deb/debian/ca-certificates@20250419%2Bdeb13u1?arch=all&distro=debian-13.7",
            ],
            [
                "os-pkgs",
                "debian",
                "media-types@13.0.0",
                "media-types",
                "13.0.0",
                "all",
                "media-types",
                "13.0.0",
                "pkg:deb/debian/media-types@13.0.0?arch=all&distro=debian-13.7",
            ],
            [
                "os-pkgs",
                "debian",
                "netbase@6.5",
                "netbase",
                "6.5",
                "all",
                "netbase",
                "6.5",
                "pkg:deb/debian/netbase@6.5?arch=all&distro=debian-13.7",
            ],
            [
                "os-pkgs",
                "debian",
                "tzdata-legacy@2026e-0+deb13u1",
                "tzdata-legacy",
                "2026e",
                "all",
                "tzdata",
                "2026e",
                "pkg:deb/debian/tzdata-legacy@2026e-0%2Bdeb13u1?arch=all&distro=debian-13.7",
            ],
            [
                "os-pkgs",
                "debian",
                "tzdata@2026e-0+deb13u1",
                "tzdata",
                "2026e",
                "all",
                "tzdata",
                "2026e",
                "pkg:deb/debian/tzdata@2026e-0%2Bdeb13u1?arch=all&distro=debian-13.7",
            ],
        ],
    },
    "expected_modules": {
        "alertmanager": {
            "github.com/KimMachineGun/automemlimit": "v0.7.5",
            "github.com/alecthomas/kingpin/v2": "v2.4.0",
            "github.com/alecthomas/units": "v0.0.0-20240927000941-0f3dac36c52b",
            "github.com/armon/go-metrics": "v0.4.1",
            "github.com/aws/aws-sdk-go-v2": "v1.43.2",
            "github.com/aws/aws-sdk-go-v2/config": "v1.32.33",
            "github.com/aws/aws-sdk-go-v2/credentials": "v1.19.32",
            "github.com/aws/aws-sdk-go-v2/feature/ec2/imds": "v1.18.33",
            "github.com/aws/aws-sdk-go-v2/internal/configsources": "v1.4.33",
            "github.com/aws/aws-sdk-go-v2/internal/endpoints/v2": "v2.7.33",
            "github.com/aws/aws-sdk-go-v2/internal/v4a": "v1.4.34",
            "github.com/aws/aws-sdk-go-v2/service/internal/accept-encoding": "v1.13.14",
            "github.com/aws/aws-sdk-go-v2/service/internal/presigned-url": "v1.13.33",
            "github.com/aws/aws-sdk-go-v2/service/signin": "v1.5.2",
            "github.com/aws/aws-sdk-go-v2/service/sns": "v1.42.2",
            "github.com/aws/aws-sdk-go-v2/service/sso": "v1.33.2",
            "github.com/aws/aws-sdk-go-v2/service/ssooidc": "v1.38.2",
            "github.com/aws/aws-sdk-go-v2/service/sts": "v1.45.2",
            "github.com/aws/smithy-go": "v1.27.5",
            "github.com/beorn7/perks": "v1.0.1",
            "github.com/cenkalti/backoff/v5": "v5.0.3",
            "github.com/cespare/xxhash/v2": "v2.3.0",
            "github.com/coreos/go-systemd/v22": "v22.7.0",
            "github.com/docker/go-units": "v0.5.0",
            "github.com/felixge/httpsnoop": "v1.0.4",
            "github.com/fsnotify/fsnotify": "v1.10.1",
            "github.com/go-logr/logr": "v1.4.4",
            "github.com/go-logr/stdr": "v1.2.2",
            "github.com/go-openapi/analysis": "v0.25.5",
            "github.com/go-openapi/errors": "v0.22.8",
            "github.com/go-openapi/jsonpointer": "v1.0.0",
            "github.com/go-openapi/jsonreference": "v1.0.0",
            "github.com/go-openapi/loads": "v0.25.0",
            "github.com/go-openapi/runtime": "v0.33.0",
            "github.com/go-openapi/runtime/server-middleware": "v0.33.0",
            "github.com/go-openapi/spec": "v0.22.9",
            "github.com/go-openapi/strfmt": "v0.27.0",
            "github.com/go-openapi/swag": "v0.28.0",
            "github.com/go-openapi/swag/cmdutils": "v0.28.0",
            "github.com/go-openapi/swag/conv": "v0.28.0",
            "github.com/go-openapi/swag/fileutils": "v0.28.0",
            "github.com/go-openapi/swag/jsonutils": "v0.28.0",
            "github.com/go-openapi/swag/loading": "v0.28.0",
            "github.com/go-openapi/swag/mangling": "v0.28.0",
            "github.com/go-openapi/swag/netutils": "v0.28.0",
            "github.com/go-openapi/swag/pools": "v0.28.0",
            "github.com/go-openapi/swag/stringutils": "v0.28.0",
            "github.com/go-openapi/swag/typeutils": "v0.28.0",
            "github.com/go-openapi/swag/yamlutils": "v0.28.0",
            "github.com/go-openapi/validate": "v0.26.1",
            "github.com/go-viper/mapstructure/v2": "v2.5.0",
            "github.com/golang-jwt/jwt/v5": "v5.3.1",
            "github.com/google/btree": "v1.1.3",
            "github.com/google/uuid": "v1.6.0",
            "github.com/grpc-ecosystem/grpc-gateway/v2": "v2.29.0",
            "github.com/hashicorp/errwrap": "v1.1.0",
            "github.com/hashicorp/go-immutable-radix": "v1.3.1",
            "github.com/hashicorp/go-metrics": "v0.6.0",
            "github.com/hashicorp/go-msgpack/v2": "v2.1.5",
            "github.com/hashicorp/go-multierror": "v1.1.1",
            "github.com/hashicorp/go-sockaddr": "v1.0.7",
            "github.com/hashicorp/golang-lru": "v0.5.4",
            "github.com/hashicorp/golang-lru/v2": "v2.0.7",
            "github.com/hashicorp/memberlist": "v0.6.0",
            "github.com/jessevdk/go-flags": "v1.6.1",
            "github.com/jpillora/backoff": "v1.0.0",
            "github.com/julienschmidt/httprouter": "v1.3.0",
            "github.com/klauspost/compress": "v1.19.1",
            "github.com/mdlayher/socket": "v0.6.0",
            "github.com/mdlayher/vsock": "v1.3.0",
            "github.com/miekg/dns": "v1.1.72",
            "github.com/munnerz/goautoneg": "v0.0.0-20191010083416-a7dc8b61c822",
            "github.com/mwitkow/go-conntrack": "v0.0.0-20190716064945-2f068394615f",
            "github.com/oklog/run": "v1.2.0",
            "github.com/oklog/ulid/v2": "v2.1.2",
            "github.com/pbnjay/memory": "v0.0.0-20210728143218-7b4eea64cf58",
            "github.com/pierrec/lz4/v4": "v4.1.26",
            "github.com/prometheus/client_golang": "v1.24.1",
            "github.com/prometheus/client_model": "v0.6.2",
            "github.com/prometheus/common": "v0.70.1",
            "github.com/prometheus/exporter-toolkit": "v0.17.1",
            "github.com/prometheus/procfs": "v0.21.1",
            "github.com/prometheus/sigv4": "v0.4.1",
            "github.com/rs/cors": "v1.11.1",
            "github.com/sean-/seed": "v0.0.0-20170313163322-e2103e2c3529",
            "github.com/twmb/franz-go": "v1.21.5",
            "github.com/twmb/franz-go/pkg/kmsg": "v1.13.1",
            "github.com/twmb/franz-go/plugin/kslog": "v1.0.0",
            "github.com/xhit/go-str2duration/v2": "v2.1.0",
            "go.opentelemetry.io/auto/sdk": "v1.2.1",
            "go.opentelemetry.io/contrib/instrumentation/net/http/httptrace/otelhttptrace": "v0.69.0",
            "go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp": "v0.69.0",
            "go.opentelemetry.io/otel": "v1.45.0",
            "go.opentelemetry.io/otel/exporters/otlp/otlptrace": "v1.45.0",
            "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc": "v1.45.0",
            "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp": "v1.45.0",
            "go.opentelemetry.io/otel/metric": "v1.45.0",
            "go.opentelemetry.io/otel/sdk": "v1.45.0",
            "go.opentelemetry.io/otel/trace": "v1.45.0",
            "go.opentelemetry.io/proto/otlp": "v1.11.0",
            "go.yaml.in/yaml/v2": "v2.4.4",
            "go.yaml.in/yaml/v3": "v3.0.4",
            "golang.org/x/crypto": "v0.57.0",
            "golang.org/x/net": "v0.60.0",
            "golang.org/x/oauth2": "v0.36.0",
            "golang.org/x/sync": "v0.23.0",
            "golang.org/x/sys": "v0.48.0",
            "golang.org/x/text": "v0.42.0",
            "golang.org/x/time": "v0.15.0",
            "google.golang.org/genproto/googleapis/api": "v0.0.0-20260803160001-6ac0973c030d",
            "google.golang.org/genproto/googleapis/rpc": "v0.0.0-20260803160001-6ac0973c030d",
            "google.golang.org/grpc": "v1.83.2",
            "google.golang.org/protobuf": "v1.36.11",
            "gopkg.in/telebot.v3": "v3.3.8",
            "gopkg.in/yaml.v2": "v2.4.0",
            "stdlib": "v1.27.3",
            "github.com/prometheus/alertmanager": "0.34.2",
        },
        "amtool": {
            "github.com/alecthomas/kingpin/v2": "v2.4.0",
            "github.com/alecthomas/units": "v0.0.0-20240927000941-0f3dac36c52b",
            "github.com/armon/go-metrics": "v0.4.1",
            "github.com/aws/aws-sdk-go-v2": "v1.43.2",
            "github.com/aws/aws-sdk-go-v2/config": "v1.32.33",
            "github.com/aws/aws-sdk-go-v2/credentials": "v1.19.32",
            "github.com/aws/aws-sdk-go-v2/feature/ec2/imds": "v1.18.33",
            "github.com/aws/aws-sdk-go-v2/internal/configsources": "v1.4.33",
            "github.com/aws/aws-sdk-go-v2/internal/endpoints/v2": "v2.7.33",
            "github.com/aws/aws-sdk-go-v2/internal/v4a": "v1.4.34",
            "github.com/aws/aws-sdk-go-v2/service/internal/accept-encoding": "v1.13.14",
            "github.com/aws/aws-sdk-go-v2/service/internal/presigned-url": "v1.13.33",
            "github.com/aws/aws-sdk-go-v2/service/signin": "v1.5.2",
            "github.com/aws/aws-sdk-go-v2/service/sso": "v1.33.2",
            "github.com/aws/aws-sdk-go-v2/service/ssooidc": "v1.38.2",
            "github.com/aws/aws-sdk-go-v2/service/sts": "v1.45.2",
            "github.com/aws/smithy-go": "v1.27.5",
            "github.com/beorn7/perks": "v1.0.1",
            "github.com/cenkalti/backoff/v5": "v5.0.3",
            "github.com/cespare/xxhash/v2": "v2.3.0",
            "github.com/coreos/go-systemd/v22": "v22.7.0",
            "github.com/felixge/httpsnoop": "v1.0.4",
            "github.com/fsnotify/fsnotify": "v1.10.1",
            "github.com/go-logr/logr": "v1.4.4",
            "github.com/go-logr/stdr": "v1.2.2",
            "github.com/go-openapi/analysis": "v0.25.5",
            "github.com/go-openapi/errors": "v0.22.8",
            "github.com/go-openapi/jsonpointer": "v1.0.0",
            "github.com/go-openapi/jsonreference": "v1.0.0",
            "github.com/go-openapi/loads": "v0.25.0",
            "github.com/go-openapi/runtime": "v0.33.0",
            "github.com/go-openapi/runtime/server-middleware": "v0.33.0",
            "github.com/go-openapi/spec": "v0.22.9",
            "github.com/go-openapi/strfmt": "v0.27.0",
            "github.com/go-openapi/swag": "v0.28.0",
            "github.com/go-openapi/swag/cmdutils": "v0.28.0",
            "github.com/go-openapi/swag/conv": "v0.28.0",
            "github.com/go-openapi/swag/fileutils": "v0.28.0",
            "github.com/go-openapi/swag/jsonutils": "v0.28.0",
            "github.com/go-openapi/swag/loading": "v0.28.0",
            "github.com/go-openapi/swag/mangling": "v0.28.0",
            "github.com/go-openapi/swag/netutils": "v0.28.0",
            "github.com/go-openapi/swag/pools": "v0.28.0",
            "github.com/go-openapi/swag/stringutils": "v0.28.0",
            "github.com/go-openapi/swag/typeutils": "v0.28.0",
            "github.com/go-openapi/swag/yamlutils": "v0.28.0",
            "github.com/go-openapi/validate": "v0.26.1",
            "github.com/go-viper/mapstructure/v2": "v2.5.0",
            "github.com/golang-jwt/jwt/v5": "v5.3.1",
            "github.com/google/btree": "v1.1.3",
            "github.com/google/uuid": "v1.6.0",
            "github.com/grpc-ecosystem/grpc-gateway/v2": "v2.29.0",
            "github.com/hashicorp/errwrap": "v1.1.0",
            "github.com/hashicorp/go-immutable-radix": "v1.3.1",
            "github.com/hashicorp/go-metrics": "v0.6.0",
            "github.com/hashicorp/go-msgpack/v2": "v2.1.5",
            "github.com/hashicorp/go-multierror": "v1.1.1",
            "github.com/hashicorp/go-sockaddr": "v1.0.7",
            "github.com/hashicorp/golang-lru": "v0.5.4",
            "github.com/hashicorp/golang-lru/v2": "v2.0.7",
            "github.com/hashicorp/memberlist": "v0.6.0",
            "github.com/jpillora/backoff": "v1.0.0",
            "github.com/klauspost/compress": "v1.19.1",
            "github.com/mdlayher/socket": "v0.6.0",
            "github.com/mdlayher/vsock": "v1.3.0",
            "github.com/miekg/dns": "v1.1.72",
            "github.com/munnerz/goautoneg": "v0.0.0-20191010083416-a7dc8b61c822",
            "github.com/mwitkow/go-conntrack": "v0.0.0-20190716064945-2f068394615f",
            "github.com/oklog/run": "v1.2.0",
            "github.com/oklog/ulid/v2": "v2.1.2",
            "github.com/pierrec/lz4/v4": "v4.1.26",
            "github.com/prometheus/client_golang": "v1.24.1",
            "github.com/prometheus/client_model": "v0.6.2",
            "github.com/prometheus/common": "v0.70.1",
            "github.com/prometheus/exporter-toolkit": "v0.17.1",
            "github.com/prometheus/procfs": "v0.21.1",
            "github.com/prometheus/sigv4": "v0.4.1",
            "github.com/sean-/seed": "v0.0.0-20170313163322-e2103e2c3529",
            "github.com/twmb/franz-go": "v1.21.5",
            "github.com/twmb/franz-go/pkg/kmsg": "v1.13.1",
            "github.com/twmb/franz-go/plugin/kslog": "v1.0.0",
            "github.com/xhit/go-str2duration/v2": "v2.1.0",
            "github.com/xlab/treeprint": "v1.2.0",
            "go.opentelemetry.io/auto/sdk": "v1.2.1",
            "go.opentelemetry.io/contrib/instrumentation/net/http/httptrace/otelhttptrace": "v0.69.0",
            "go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp": "v0.69.0",
            "go.opentelemetry.io/otel": "v1.45.0",
            "go.opentelemetry.io/otel/exporters/otlp/otlptrace": "v1.45.0",
            "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc": "v1.45.0",
            "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp": "v1.45.0",
            "go.opentelemetry.io/otel/metric": "v1.45.0",
            "go.opentelemetry.io/otel/sdk": "v1.45.0",
            "go.opentelemetry.io/otel/trace": "v1.45.0",
            "go.opentelemetry.io/proto/otlp": "v1.11.0",
            "go.yaml.in/yaml/v2": "v2.4.4",
            "go.yaml.in/yaml/v3": "v3.0.4",
            "golang.org/x/crypto": "v0.57.0",
            "golang.org/x/mod": "v0.41.0",
            "golang.org/x/net": "v0.60.0",
            "golang.org/x/oauth2": "v0.36.0",
            "golang.org/x/sync": "v0.23.0",
            "golang.org/x/sys": "v0.48.0",
            "golang.org/x/text": "v0.42.0",
            "golang.org/x/time": "v0.15.0",
            "google.golang.org/genproto/googleapis/api": "v0.0.0-20260803160001-6ac0973c030d",
            "google.golang.org/genproto/googleapis/rpc": "v0.0.0-20260803160001-6ac0973c030d",
            "google.golang.org/grpc": "v1.83.2",
            "google.golang.org/protobuf": "v1.36.11",
            "gopkg.in/telebot.v3": "v3.3.8",
            "gopkg.in/yaml.v2": "v2.4.0",
            "stdlib": "v1.27.3",
            "github.com/prometheus/alertmanager": "0.34.2",
        },
    },
}


def _alertmanager_accepted_live_profile() -> tuple[dict[str, Any], str]:
    """Join the configured immutable subject to its independent static inventory profile."""
    from scripts.ci.prometheus_source_image import require

    selected = _alertmanager_accepted_producer()
    subject = _ALERT_CURRENT_SCAN_ORACLE.get("subject")
    require(type(subject) is dict, "AM_current_scan_profile_UNCONFIGURED_HOLD")
    subject = cast(dict[str, Any], subject)
    version = subject.get("upstream_version")
    require(
        subject.get("source") == selected["source"]
        and version in ("0.34.1", "0.34.2")
        and (version == "0.34.1") == (selected["source"] == _ALERT_HISTORICAL_C10["source"]),
        "AM_current_scan_profile_UNCONFIGURED_HOLD",
    )
    graph = selected["graph"]
    binaries = subject.get("binary_sha256")
    modules = _ALERT_CURRENT_SCAN_ORACLE.get("expected_modules")
    require(
        all(type(graph.get(key)) is dict for key in ("manifest", "config", "files"))
        and type(binaries) is dict
        and set(binaries) == {"alertmanager", "amtool"}
        and type(modules) is dict
        and set(modules) == {"alertmanager", "amtool"}
        and all(
            type(modules[name]) is dict and modules[name] for name in ("alertmanager", "amtool")
        )
        and graph["config"]["digest"] == subject.get("config")
        and graph["manifest"]["digest"] == subject.get("manifest")
        and all(
            type(digest) is str
            and _HEX_RE.fullmatch(digest) is not None
            and graph["files"].get("usr/bin/" + name) == digest
            for name, digest in binaries.items()
        ),
        "AM_current_scan_accepted_subject",
    )
    return selected, cast(str, version)


def _alertmanager_candidate_inventory(
    report: dict[str, Any],
    image_id: str,
    base_report: dict[str, Any] | None,
    build_information: dict[str, Any] | None,
    *,
    proof_mode: str,
    upstream_version: str,
    current: bool = False,
) -> dict[str, Any]:
    """Check retained solver closure or a current complete supported scan of immutable S.

    The durable case has no historical archive dependency: it keeps current OS/Go
    inventory and all findings, with the accepted subject and four-CVE postcondition.
    It does not pretend to replay historical base/module resolution.
    """
    from scripts.ci.prometheus_source_image import BASE_CONFIG, require

    require(
        type(report.get("SchemaVersion")) is int
        and report["SchemaVersion"] == 2
        and report.get("ArtifactType") == "container_image"
        and type(report.get("Metadata")) is dict
        and report["Metadata"].get("ImageID") == image_id,
        "AM_candidate_scan_subject",
    )
    require(type(current) is bool, "AM_candidate_epoch_type")
    require(
        upstream_version in ("0.34.1", "0.34.2") and (upstream_version == "0.34.1" or current),
        "AM_scan_upstream_join",
    )
    require(proof_mode in ("dynamic", "accepted-live"), "AM_scan_proof_mode")
    if proof_mode == "accepted-live":
        require(base_report is None and build_information is None, "AM_scan_proof_modes_mixed")
        selected, version = _alertmanager_accepted_live_profile()
        require(upstream_version == version, "AM_scan_upstream_profile")
        require(
            image_id == selected["graph"]["config"]["digest"], "AM_current_scan_accepted_subject"
        )
    else:
        require(
            type(base_report) is dict and type(build_information) is dict,
            "AM_scan_dynamic_proof_required",
        )
        base_report = cast(dict[str, Any], base_report)
        build_information = cast(dict[str, Any], build_information)
        require(
            set(build_information) == {"alertmanager", "amtool"}
            and all(type(value) is dict for value in build_information.values()),
            "AM_candidate_both_actual_buildinfo_required",
        )
        require(
            base_report.get("ArtifactType") == "container_image"
            and type(base_report.get("Metadata")) is dict
            and base_report["Metadata"].get("ImageID")
            == (BASE_CONFIG if current else _ALERT_BASE_CONFIG),
            "AM_candidate_authenticated_base_scan_subject",
        )
        _alertmanager_support_inventory(base_report)
    inventory = _alertmanager_support_inventory(report)
    expected_os = _ALERT_CURRENT_SCAN_ORACLE["expected_OS"] if base_report is None else {}
    os_inventories = (
        [
            (
                expected_os["OS"]["Family"],
                expected_os["OS"]["Name"],
                sorted(tuple(row) for row in expected_os["packages"]),
            )
        ]
        if base_report is None
        else []
    )
    for observed in ((report,) if base_report is None else (base_report, report)):
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
        require(
            not row.get("Packages")
            or row.get("Class") == "os-pkgs"
            or (row.get("Class") == "lang-pkgs" and row.get("Type") == "gobinary"),
            "AM_unclassified_package_bearing_target",
        )
        for finding in row.get("Vulnerabilities", []):
            require(
                finding["VulnerabilityID"]
                not in {"CVE-2026-84445", "CVE-2026-78669", "CVE-2026-78667", "CVE-2026-97031"},
                "AM_accepted_CVE_still_present",
            )
            if current:
                require(
                    finding["VulnerabilityID"] != "CVE-2026-111943",
                    "AM_current_Go_CVE_still_present",
                )
        if row.get("Class") == "lang-pkgs" and row.get("Type") == "gobinary":
            require(
                row["Target"]
                in ("usr/bin/alertmanager", "usr/bin/amtool", "bin/alertmanager", "bin/amtool"),
                "AM_unexpected_Go_binary",
            )
            targets.append(row["Target"].rsplit("/", 1)[1])
            binary = targets[-1]
            expected_modules = (
                _ALERT_CURRENT_SCAN_ORACLE["expected_modules"][binary]
                if build_information is None
                else {}
            )
            if build_information is not None:
                information = build_information[binary]
                require(
                    information.get("Go") == ("go1.27.3" if current else "go1.27.2")
                    and type(information.get("dependencies")) is dict
                    and type(information.get("main")) is dict
                    and information["main"].get("Path") == "github.com/prometheus/alertmanager"
                    and information["main"].get("Version")
                    in ("(devel)", upstream_version, "v" + upstream_version),
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
                expected_modules[information["main"]["Path"]] = upstream_version
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
                if name == "github.com/prometheus/alertmanager":
                    version = version.removeprefix("v")
                actual_modules[name] = version
            require(
                actual_modules == expected_modules,
                "AM_candidate_all_and_only_actual_Go_dependencies",
            )
    require(sorted(targets) == ["alertmanager", "amtool"], "AM_candidate_two_Go_targets")
    return inventory


def _alertmanager_candidate_graph(
    layout: Path, support: Path, expected_files: dict[str, str], *, current: bool = False
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

    from scripts.ci.prometheus_source_image import BASE_LAYER_CONTRACTS, validate_default_ca

    require(type(current) is bool, "AM_candidate_graph_epoch")
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
    if current:
        require(
            configuration["rootfs"]["diff_ids"][:13]
            == [row["diff_id"] for row in BASE_LAYER_CONTRACTS],
            "AM_candidate_current_base_diffIDs",
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
                        ca_bytes = cast(BinaryIO, stream).read(member.size + 1)
                        require(
                            len(ca_bytes) == member.size and ca_hash is None, "AM_default_CA_unique"
                        )
                        if current:
                            validate_default_ca(ca_bytes)
                        ca_hash = sha256(ca_bytes).hexdigest()
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
    base_descriptor: dict[str, Any],
    upstream_version: str = "0.34.1",
    preparation_finished: list[float] | None = None,
) -> dict[str, Any]:
    """One direct serial pair plus one COPY-only assembly; no resolver or retry."""
    from datetime import datetime
    import shutil
    import uuid
    from scripts.ci.prometheus_source_image import (
        BASE,
        BASE_CONFIG,
        Native,
        file_hash,
        fresh_directory,
        one_object,
        pack_layout,
        real_directory,
        require,
        tree_inventory,
    )

    require(
        base_descriptor == _alertmanager_current_base_graph(support / "base-layout"),
        "AM_pair_validated_current_base",
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
        create += ["--entrypoint=/toolchain/bin/go", BASE_CONFIG, *argv]
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
                [*prefix, "image", "inspect", "--format", "{{json .}}", BASE_CONFIG],
                "pair-base-inspect",
                env,
                cwd=work,
            )
        )
        require(
            base.get("Id") == BASE_CONFIG
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
        require(time.monotonic() <= prep_deadline, "AM_pair_preparation_deadline")
        if preparation_finished is not None:
            require(not preparation_finished, "AM_pair_preparation_clock_duplicate")
            preparation_finished.append(time.monotonic())
        native = Native(
            evidence, time.monotonic() + limits["PAIR_SECONDS"], limits["CLEANUP_SECONDS"]
        )
        result["logical_build_starts"] = 1
        result["build_information"] = {}
        require(upstream_version in ("0.34.1", "0.34.2"), "AM_pair_upstream_epoch")
        expected_metadata = (
            _ALERT_BUILD_METADATA if upstream_version == "0.34.1" else _ALERT_UPSTREAM_0342_METADATA
        )
        for argv in plan["compiler_argv"]:
            require(
                argv.count("-ldflags") == 1
                and argv.index("-ldflags") + 1 < len(argv)
                and argv[argv.index("-ldflags") + 1] == expected_metadata,
                "AM_pair_source_bound_metadata",
            )
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
                go(["version", "-m", "/out/" + binary], binary + "-buildinfo"),
                binary,
                current=True,
                upstream_version=upstream_version,
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
        context_modes = {
            "alertmanager": 0o555,
            "amtool": 0o555,
            "Containerfile": 0o444,
            "alertmanager.yml": 0o444,
            "LICENSE": 0o444,
            "NOTICE": 0o444,
            "probe-bin-bracket": 0o555,
            "storage-dir": 0o700,
            ".": 0o700,
        }
        context_identities: dict[str, tuple[int, int, int, int]] = {}

        def check_context(*, normalized: bool) -> None:
            require(
                {path.name for path in context.iterdir()} == set(context_modes) - {"."},
                "AM_context_exact_members",
            )
            for name, mode in context_modes.items():
                path = context / name
                info = path.lstat()
                directory = name in ("storage-dir", ".")
                require(
                    (
                        stat.S_ISDIR(info.st_mode)
                        if directory
                        else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                    )
                    and stat.S_IMODE(info.st_mode) == mode,
                    "AM_context_type_or_mode",
                )
                identity = (info.st_dev, info.st_ino, info.st_uid, info.st_gid)
                if normalized:
                    require(
                        identity == context_identities[name]
                        and info.st_mtime_ns == _ALERT_ASSEMBLY_EPOCH * 1_000_000_000,
                        "AM_context_identity_or_timestamp",
                    )
                else:
                    context_identities[name] = identity
            require(not any((context / "storage-dir").iterdir()), "AM_context_storage_not_empty")

        check_context(normalized=False)
        epoch_ns = _ALERT_ASSEMBLY_EPOCH * 1_000_000_000
        for name in context_modes:
            os.utime(context / name, ns=(epoch_ns, epoch_ns), follow_symlinks=False)
        check_context(normalized=True)

        context_inventory = tree_inventory(context)
        result["context"] = context_inventory
        require(
            file_hash(context / "Containerfile") == _ALERT_CURRENT_ASSEMBLY_RECIPE_SHA256
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
            "--build-arg",
            f"SOURCE_DATE_EPOCH={_ALERT_ASSEMBLY_EPOCH}",
            "--annotation",
            "manifest-descriptor:org.opencontainers.image.ref.name=candidate",
            "--network=none",
            "--pull=false",
            "--build-context",
            BASE
            + "=oci-layout://"
            + str(support / "base-layout")
            + "@"
            + base_descriptor["digest"],
            "--file",
            str(context / "Containerfile"),
            "--output",
            "type=oci,tar=false,rewrite-timestamp=true,dest=" + str(layout),
            str(context),
        ]
        check_context(normalized=True)
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
        check_context(normalized=True)
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
        graph = _alertmanager_candidate_graph(layout, support, expected, current=True)
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


def _alertmanager_live_security(args: argparse.Namespace) -> None:
    """Run the four current unsuppressed controls against local image IDs and one observed DB."""
    import shutil
    import signal
    from scripts.ci.prometheus_source_image import (
        Native,
        file_hash,
        fresh_directory,
        one_object,
        require,
    )

    selected, live_upstream = _alertmanager_accepted_live_profile()
    limits = _alertmanager_limits(caller=True)
    scanner, cache = args.alertmanager_scanner, args.alertmanager_cache
    require(
        isinstance(scanner, Path)
        and scanner.is_absolute()
        and scanner.is_file()
        and not scanner.is_symlink()
        and file_hash(scanner) == _ALERT_TRIVY_SHA256,
        "AM_live_pinned_scanner",
    )
    require(
        isinstance(cache, Path)
        and cache.is_absolute()
        and cache.is_dir()
        and not cache.is_symlink(),
        "AM_live_cache",
    )
    database = {name: file_hash(cache / name) for name in _ALERT_DB}
    work = args.output_dir.absolute()
    fresh_directory(work)
    evidence = work / "evidence"
    fresh_directory(evidence)
    config = work / "empty-docker-config"
    fresh_directory(config)
    empty_config, empty_ignore = work / "trivy.yaml", work / "trivy.ignore"
    empty_config.write_bytes(b"{}\n")
    empty_ignore.write_bytes(b"")
    environment = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "DOCKER_CONFIG": str(config),
        "LANG": "C.UTF-8",
    }
    docker = shutil.which("docker")
    require(docker is not None and Path(docker).is_absolute(), "AM_live_Docker")
    prefix = [docker, "--config", str(config)]
    start = time.monotonic()
    previous_handler, previous_timer = signal.getsignal(signal.SIGALRM), signal.getitimer(
        signal.ITIMER_REAL
    )
    deadline = min(
        start + limits["SECURITY_SECONDS"],
        start + previous_timer[0] if previous_timer[0] > 0 else float("inf"),
    )
    native = Native(evidence, deadline, limits["CLEANUP_SECONDS"])

    def interrupt(signum: int, frame: object) -> None:
        raise TimeoutError("AM_live_security_deadline")

    def scan(kind: str, subject: str, label: str) -> dict[str, Any]:
        """Require actual scanner success and complete original JSON before a control can count."""
        require(
            file_hash(scanner) == _ALERT_TRIVY_SHA256
            and {name: file_hash(cache / name) for name in database} == database,
            "AM_live_scanner_DB_drift",
        )
        target = evidence / (label + ".private.json")
        command = [
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
            str(limits["SCAN_TIMEOUT_SECONDS"]) + "s",
            "--output",
            str(target),
        ]
        if kind == "image":
            command += ["--image-src", "docker"]
        native.run(
            [*command, subject],
            label,
            environment,
            cwd=work,
            maximum_seconds=limits["SCAN_PROCESS_SECONDS"],
        )
        require(
            target.is_file()
            and not target.is_symlink()
            and 0 < target.stat().st_size <= 64 * 1024**2,
            "AM_live_native_report_missing",
        )
        target.chmod(0o600)
        report = one_object(target.read_bytes())
        require(
            type(report.get("SchemaVersion")) is int and report["SchemaVersion"] == 2,
            "AM_live_native_schema",
        )
        require(
            file_hash(scanner) == _ALERT_TRIVY_SHA256
            and {name: file_hash(cache / name) for name in database} == database,
            "AM_live_scanner_DB_post_drift",
        )
        return cast(dict[str, Any], report)

    result: dict[str, Any] = {
        "compiler_starts": 0,
        "scanner_sha256": _ALERT_TRIVY_SHA256,
        "DB": database,
        "DB_metadata": one_object((cache / "db/metadata.json").read_bytes()),
    }
    signal.signal(signal.SIGALRM, interrupt)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, deadline - time.monotonic()))
    primary: BaseException | None = None
    try:
        result["scanner_version"] = one_object(
            native.run(
                [str(scanner), "--version", "--format", "json"],
                "current-scanner-version",
                environment,
                cwd=work,
                maximum_seconds=30,
            )
        )
        require(
            result["scanner_version"].get("Version") == "0.74.0", "AM_live_native_scanner_version"
        )
        current_epoch = selected["source"] != _ALERT_HISTORICAL_C10["source"]
        graph = selected["graph"]
        image_id = graph["config"]["digest"]
        image = one_object(
            native.run(
                [*prefix, "image", "inspect", "--format", "{{json .}}", image_id],
                "live-local-candidate",
                environment,
                cwd=work,
                maximum_seconds=30,
            )
        )
        require(
            image.get("Id") == image_id
            and image.get("Os") == "linux"
            and image.get("Architecture") == "amd64"
            and image.get("RootFS", {}).get("Layers") == graph["diff_ids"],
            "AM_live_actual_local_candidate",
        )
        result["candidate"] = _alertmanager_candidate_inventory(
            scan("image", image_id, "current-candidate-full-supported"),
            image_id,
            None,
            None,
            current=current_epoch,
            proof_mode="accepted-live",
            upstream_version=live_upstream,
        )
        native.run(
            [*prefix, "pull", "--platform", "linux/amd64", _ALERT_OLD_RUNTIME_REF],
            "live-old-control-pull",
            environment,
            cwd=work,
            maximum_seconds=120,
        )
        old = one_object(
            native.run(
                [*prefix, "image", "inspect", "--format", "{{json .}}", _ALERT_OLD_RUNTIME_REF],
                "live-old-control-identity",
                environment,
                cwd=work,
                maximum_seconds=30,
            )
        )
        require(
            _alertmanager_contract_image([old], _ALERT_OLD_RUNTIME_CONFIG) == "old",
            "AM_live_actual_old_control",
        )
        result["old_control"] = _alertmanager_vulnerability_control(
            scan("image", _ALERT_OLD_RUNTIME_CONFIG, "current-known-vulnerable-control"),
            _ALERT_OLD_RUNTIME_CONFIG,
            current=current_epoch,
        )
        positive, negative = work / "positive", work / "negative"
        fresh_directory(positive)
        fresh_directory(negative)
        (positive / "credentials.txt").write_text(
            "GITHUB_PAT=ghp_" + "012345678901234567890123456789abcdef" + "\n"
        )
        (negative / "credentials.txt").write_text("plain harmless operational text\n")
        result["secrets"] = _alertmanager_secret_controls(
            scan("fs", str(positive), "current-secret-positive"),
            scan("fs", str(negative), "current-secret-negative"),
            str(positive),
            str(negative),
        )
        result["status"] = "OBSERVED_CURRENT_SUPPORTED_INVENTORY_AND_FOUR_CONTROLS"
    except BaseException as error:
        primary = error
        result["failure"] = type(error).__name__
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        result["native_records"] = native.records
        try:
            try:
                (work / "security-observation.json").write_text(json.dumps(result, indent=2) + "\n")
            except BaseException as observation_error:
                if primary is not None:
                    primary.add_note(
                        "AM current security observation also failed: "
                        + type(observation_error).__name__
                    )
                    raise primary from None
                raise
        finally:
            if previous_timer[0] > 0:
                remaining = previous_timer[0] - (time.monotonic() - start)
                if remaining > 0:
                    signal.setitimer(signal.ITIMER_REAL, remaining, previous_timer[1])
                else:
                    active_error = primary or sys.exc_info()[1]
                    if active_error is None:
                        raise TimeoutError("Caller timer expired during current AM security checks")
                    active_error.add_note(
                        "Caller timer also expired during current AM security checks"
                    )


def _alertmanager_final_security(
    archive: Path,
    graph: dict[str, Any],
    support: Path,
    work: Path,
    limits: dict[str, int],
    *,
    build_information: dict[str, Any],
    support_report: dict[str, Any],
    upstream_version: str = "0.34.1",
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

    database = support_report.get("scanner", {}).get("DB")
    require(
        type(database) is dict
        and set(database) == set(_ALERT_DB)
        and all(
            type(value) is str and _HEX_RE.fullmatch(value) is not None
            for value in database.values()
        ),
        "AM_final_current_DB_binding",
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
    cache = work / "trivy-cache"
    primary: BaseException | None = None
    try:
        # Qualified support remains immutable. Trivy's filesystem cache (fanal)
        # is derived work output and must never be seeded from retained cache state.
        fresh_directory(cache)
        for name, expected in database.items():
            source = support / "trivy-cache" / name
            destination = cache / name
            require(file_hash(source, deadline) == expected, "AM_final_source_DB_before_copy")
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            destination.chmod(0o600)
            require(
                file_hash(source, deadline) == expected == file_hash(destination, deadline),
                "AM_final_private_DB_copy",
            )
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
                and all(
                    file_hash(support / "trivy-cache" / n, deadline)
                    == h
                    == file_hash(cache / n, deadline)
                    for n, h in database.items()
                ),
                "AM_final_scanner_DB_drift",
            )
            destination = evidence / (label + ".private.json")
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
                all(
                    file_hash(support / "trivy-cache" / n, deadline)
                    == h
                    == file_hash(cache / n, deadline)
                    for n, h in database.items()
                )
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
            current=True,
        )
        layout = work / "docker-load-layout"
        require(
            _alertmanager_candidate_graph(layout, support, graph["files"], current=True) == graph
            and file_hash(archive, deadline)
            == reports["docker_load_transport"]["source_OCI_sha256"],
            "AM_final_candidate_scan_identity",
        )
        candidate_report = scan("image", layout, "candidate-full-supported")
        require(
            _alertmanager_candidate_graph(layout, support, graph["files"], current=True) == graph
            and file_hash(archive, deadline)
            == reports["docker_load_transport"]["source_OCI_sha256"],
            "AM_final_candidate_scan_post_identity",
        )
        reports["candidate"] = _alertmanager_candidate_inventory(
            candidate_report,
            graph["config"]["digest"],
            one_object((support / "evidence/base-full-supported-scan.private.json").read_bytes()),
            build_information,
            current=True,
            upstream_version=upstream_version,
            proof_mode="dynamic",
        )
        reports["scanner"] = {
            "sha256": _ALERT_TRIVY_SHA256,
            "DB": database,
            "DB_metadata": one_object((support / "trivy-cache/db/metadata.json").read_bytes()),
        }
    except BaseException as error:
        primary = error
        raise
    finally:
        post_failure: BaseException | None = None
        poststate: dict[str, Any] = {}
        operands = [("scanner", scanner, _ALERT_TRIVY_SHA256)]
        operands += [
            ("support/" + name, support / "trivy-cache" / name, expected)
            for name, expected in database.items()
        ]
        operands += [
            ("private/" + name, cache / name, expected) for name, expected in database.items()
        ]
        for label, path, expected in operands:
            try:
                observed = file_hash(path, deadline)
                poststate[label] = {"sha256": observed, "matches": observed == expected}
                require(observed == expected, "AM_final_input_poststate_drift_" + label)
            except BaseException as post_error:
                poststate.setdefault(label, {})["failure"] = (
                    type(post_error).__name__ + ":" + str(post_error)
                )
                if primary is not None:
                    primary.add_note(
                        "AM input poststate also failed ("
                        + label
                        + "): "
                        + type(post_error).__name__
                    )
                else:
                    post_failure = post_error
                    primary = post_error
        reports["input_poststate"] = poststate
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
        if post_failure is not None:
            raise post_failure
    return reports


def _alertmanager_native_candidate(
    candidate: dict[str, Any],
    observation: Path,
    work: Path,
    limits: dict[str, int],
    *,
    prepared: dict[str, Any] | None = None,
    material_root: Path | None = None,
    producer_image: bool = False,
) -> dict[str, Any]:
    """Run retained local OCI bytes through the existing bounded Linux fixture owner."""
    from scripts.ci.prometheus_source_image import Native, fresh_directory, require

    require(type(producer_image) is bool, "AM_native_scope_type")
    require(
        not producer_image or prepared is None and material_root is None,
        "AM_producer_native_not_selected_consumer",
    )
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
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
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
    result: dict[str, Any] = {
        "compiler_starts": 0,
        "validation_scope": (
            (
                "merged_H_selected_image"
                if candidate.get("producer_admission", {}).get("mode") == "H"
                else "producer_image"
            )
            if producer_image
            else "selected_consumer"
        ),
    }
    primary: BaseException | None = None
    try:
        if prepared is None:
            result["docker_load_transport"] = _alertmanager_docker_load_transport(
                observation.parent / "candidate.oci.tar",
                candidate["graph"],
                work,
                started + limits["NATIVE_SECONDS"],
            )
            native.run(
                [
                    *prefix,
                    "image",
                    "load",
                    "--input",
                    result["docker_load_transport"]["load_input"],
                ],
                "native-load-retained-OCI",
                env,
                cwd=work,
                maximum_seconds=120,
            )
        else:
            require(
                prepared.get("image_id") == candidate["graph"]["config"]["digest"],
                "AM_prepared_native_identity",
            )
            result["docker_load_transport"] = prepared["docker_load_transport"]
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
        if producer_image:
            argv.append("--alertmanager-producer-image")
        raw = native.run(
            argv,
            "full-AM-native",
            env,
            cwd=material_root if material_root is not None else REPO_ROOT,
            output_bound=16 * 1024**2,
        )
        marker = (
            b"native_AM_merged_H_full_controls=pass"
            if producer_image and candidate.get("producer_admission", {}).get("mode") == "H"
            else (
                b"native_AM_producer_image_controls=pass"
                if producer_image
                else b"native_AM_full_candidate_controls=pass"
            )
        )
        other_markers = {
            b"native_AM_full_candidate_controls=pass",
            b"native_AM_producer_image_controls=pass",
            b"native_AM_merged_H_full_controls=pass",
        } - {marker}
        require(
            raw.splitlines().count(marker) == 1
            and not other_markers.intersection(raw.splitlines()),
            "AM_native_full_terminal_missing",
        )
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


_ALERT_SELECTION_FILES = (
    "deploy/docker-compose.staging.yaml",
    "deploy/docker-compose.production.yaml",
    "deploy/docker-compose.production.selfhosted.yaml",
    "deploy/alertmanager/alertmanager.yml",
    "deploy/alertmanager/trivy-ignore.yaml",
    "scripts/ci/fetch_docker_source_artifacts.py",
)


def _alertmanager_regular_sources(
    root: Path, revision: str, work: Path, deadline: float
) -> dict[str, bytes]:
    """Reuse the finite native regular-Git-object transport; never render or import HEAD code."""
    import shutil
    from scripts.ci.prometheus_source_image import Native, fresh_directory, require

    require(
        re.fullmatch(r"[0-9a-f]{40}", revision) is not None and root.is_absolute(),
        "AM_raw_source_revision",
    )
    fresh_directory(work)
    native = Native(work, deadline, 45)
    git = shutil.which("git")
    require(git is not None and Path(git).is_absolute(), "AM_raw_source_native_Git")
    prefix = [
        git,
        "--no-replace-objects",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.pager=cat",
        "-C",
        str(root),
    ]
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "LANG": "C",
    }
    proof_failure: BaseException | None = None
    try:
        result = {}
        for index, path in enumerate(_ALERT_SELECTION_FILES):
            row = native.run(
                [*prefix, "ls-tree", "-z", revision, "--", path],
                "selection-tree-" + str(index),
                env,
                cwd=root,
                maximum_seconds=8,
                output_bound=4096,
            )
            match = re.fullmatch(
                rb"100644 blob ([0-9a-f]{40})\t" + re.escape(path.encode()) + b"\x00", row
            )
            require(match is not None, "AM_selection_regular100644_blob")
            match = cast(re.Match[bytes], match)
            raw = native.run(
                [*prefix, "cat-file", "blob", revision + ":" + path],
                "selection-blob-" + str(index),
                env,
                cwd=root,
                maximum_seconds=8,
                output_bound=1048576,
            )
            require(
                0 < len(raw) <= 1048576
                and sha256(raw).hexdigest()
                and sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw, usedforsecurity=False)
                .hexdigest()
                .encode()
                == match[1],
                "AM_selection_raw_Git_object",
            )
            result[path] = raw
        return result
    except BaseException as error:
        proof_failure = error
        raise
    finally:
        try:
            (work / "native-observation.json").write_text(
                json.dumps({"native_records": native.records}, indent=2) + "\n"
            )
        except BaseException as error:
            if proof_failure is None:
                raise
            proof_failure.add_note("AM native proof retention failed: " + type(error).__name__)


def _alertmanager_bind_material(
    root: Path, revision: str, work: Path, deadline: float
) -> dict[str, bytes]:
    """Bind the actually executed material, including a restored merge checkout, to admitted HEAD data."""
    from scripts.ci.prometheus_source_image import require

    sources = _alertmanager_regular_sources(root, revision, work, deadline)
    for path, raw in sources.items():
        selected = root / path
        require(
            not selected.is_symlink() and selected.is_file() and selected.read_bytes() == raw,
            "AM_actual_material_not_admitted_HEAD",
        )
    require(
        sources["scripts/ci/fetch_docker_source_artifacts.py"] == Path(__file__).read_bytes(),
        "AM_current_F_trusted_controller_binding",
    )
    return sources


def _alertmanager_render_source_contract(
    sources: dict[str, bytes],
    work: Path,
    deadline: float,
    *,
    expected_case: str,
    controller_templates: dict[str, bytes],
) -> None:
    """Validate only trusted BASE/first-main native models in a closed synthetic render context."""
    import shutil
    from scripts.ci.prometheus_source_image import Native, fresh_directory, one_object, require

    require(
        expected_case in ("old", "accepted", "historical-AM11-before")
        and set(sources) == set(_ALERT_SELECTION_FILES)
        and set(controller_templates)
        == set(
            _ALERT_SELECTION_FILES
            if expected_case == "historical-AM11-before"
            else _ALERT_SELECTION_FILES[:5]
        ),
        "AM_closed_controller_template_inventory",
    )
    accepted_ref = _alertmanager_contract_subject()[0].encode()
    historical_before = (
        _ALERT_HISTORICAL_AM11 if expected_case == "historical-AM11-before" else None
    )
    if historical_before is not None:
        before_ref = _alertmanager_contract_subject(historical_before=historical_before)[0].encode()
        require(
            before_ref != accepted_ref and sources == controller_templates,
            "AM_before_reference_controller_and_disjoint_after",
        )
        require(
            sources["deploy/alertmanager/trivy-ignore.yaml"] == b"vulnerabilities: []\n"
            and sha256(sources["deploy/alertmanager/alertmanager.yml"]).hexdigest()
            == historical_before["source_files"]["deploy/alertmanager/alertmanager.yml"]
            and all(sources[path].count(before_ref) == 1 for path in _ALERT_SELECTION_FILES[:3]),
            "AM_before_AM11_complete_configuration",
        )
    else:
        for path in _ALERT_SELECTION_FILES[:5]:
            expected = controller_templates[path]
            if expected_case == "old" and path in _ALERT_SELECTION_FILES[:3]:
                require(expected.count(accepted_ref) == 1, "AM_controller_template_single_subject")
                expected = expected.replace(accepted_ref, _ALERT_OLD_RUNTIME_REF.encode(), 1)
            if expected_case == "old" and path == "deploy/alertmanager/trivy-ignore.yaml":
                require(
                    expected == b"vulnerabilities: []\n"
                    and sha256(sources[path]).hexdigest() == _ALERT_OLD_POLICY_SHA256,
                    "AM_first_main_original_policy",
                )
            else:
                require(sources[path] == expected, "AM_reviewed_controller_data_closure")
    fresh_directory(work)
    for path, raw in sources.items():
        target = work / path
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.write_bytes(raw)
    deploy = work / "deploy"
    application = deploy / ".env"
    application.write_bytes(b"")
    empty = work / "synthetic.env"
    empty.write_bytes(b"")
    home = work / "home"
    fresh_directory(home)
    docker = shutil.which("docker")
    require(docker is not None and Path(docker).is_absolute(), "AM_BASE_native_Compose")
    evidence = work / "evidence"
    fresh_directory(evidence)
    native = Native(evidence, deadline, 120)
    synthetic = "ghcr.io/pulseplate/configuration-only@sha256:" + "1" * 64
    postgres_password = "synthetic"  # nosec B105: # public synthetic interpolation for config-only Compose rendering (remove-by: 2026-12-15, ref: PR-2494)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "COMPOSE_PROFILES": "",
        "STAGING_IMAGE_REF": synthetic,
        "STAGING_CADDY_IMAGE_REF": synthetic,
        "PROMETHEUS_RUNTIME_REF": synthetic,
        "IMAGE_REF": synthetic,
        "STAGING_ENV_FILE": str(application),
        "POSTGRES_USER": "synthetic",
        "POSTGRES_DB": "synthetic",
        "POSTGRES_PASSWORD": postgres_password,
        "DATABASE_URL": "postgresql://synthetic:synthetic@database.invalid/synthetic",
        "STAGING_DOMAIN": "staging.invalid",
        "PRODUCTION_DOMAIN": "production.invalid",
        "STAGING_FALLBACK_DOMAIN": "staging.invalid",
    }
    # These exact reviewed templates use only the declared synthetic env-file and mounts.
    # HEAD is never rendered, and no ambient sibling .env/COMPOSE_FILE or secret is read.
    proof_failure: BaseException | None = None
    try:
        for index, path in enumerate(_ALERT_SELECTION_FILES[:3]):
            compose = work / path
            raw = native.run(
                [
                    docker,
                    "compose",
                    "--env-file",
                    str(empty),
                    "--project-directory",
                    str(deploy),
                    "-f",
                    str(compose),
                    "--profile",
                    "*",
                    "config",
                    "--format",
                    "json",
                ],
                "BASE-all-profile-" + str(index),
                env,
                cwd=deploy,
                maximum_seconds=8,
                output_bound=1048576,
            )
            case = _alertmanager_contract_candidate(
                one_object(raw),
                compose,
                deploy / "alertmanager/alertmanager.yml",
                deploy / "alertmanager/trivy-ignore.yaml",
                "staging" if index == 0 else "production",
                installed_compose=compose,
                **(
                    {"historical_before": historical_before}
                    if historical_before is not None
                    else {}
                ),
            )
            require(case == expected_case, "AM_source_transition_selection")
    except BaseException as error:
        proof_failure = error
        raise
    finally:
        try:
            (evidence / "native-observation.json").write_text(
                json.dumps({"native_records": native.records}, indent=2) + "\n"
            )
        except BaseException as error:
            if proof_failure is None:
                raise
            proof_failure.add_note("AM native proof retention failed: " + type(error).__name__)


def _alertmanager_original_lineage(
    api: GitHubRead, *, historical_before: dict[str, Any] | None = None
) -> str:
    """Keep original donor ancestry distinct from the actual selected receiver producer."""
    from scripts.ci.prometheus_source_image import require

    accepted = _alertmanager_accepted_producer()
    upstream = _alertmanager_upstream_identity(
        current=accepted["source"] != _ALERT_HISTORICAL_C10["source"], accepted=accepted, api=api
    )
    cases = [(2494, _ALERT_Q_BRANCH, _ALERT_HISTORICAL_C10["source"], _ALERT_DONOR_SOURCE)]
    if accepted["source"] != _ALERT_HISTORICAL_C10["source"]:
        cases.append(
            (
                2494 if upstream == "0.34.2" else _ALERT_RECEIVER_PR,
                _ALERT_Q_BRANCH if upstream == "0.34.2" else _ALERT_RECEIVER_BRANCH,
                accepted["source"],
                accepted["source"],
            )
        )
    if historical_before is not None:
        require(
            upstream == "0.34.2" and historical_before == _ALERT_HISTORICAL_AM11,
            "AM_before_historical_lineage_context",
        )
        cases.append(
            (
                _ALERT_RECEIVER_PR,
                _ALERT_RECEIVER_BRANCH,
                historical_before["source"],
                historical_before["source"],
            )
        )
    for number, branch, source, donor in cases:
        endpoint = "/repos/Katsiarynakavaleuskaya/PulsePlate/pulls/" + str(number)
        pr = api.json(endpoint)
        head = pr.get("head", {}).get("sha")
        count = pr.get("commits")
        require(
            type(pr.get("number")) is int
            and pr["number"] == number
            and all(
                type(pr.get(side, {}).get("repo", {}).get("id")) is int
                and pr[side]["repo"]["id"] == 1043311030
                for side in ("head", "base")
            )
            and pr.get("head", {}).get("ref") == branch
            and pr.get("base", {}).get("ref") == "main"
            and type(head) is str
            and re.fullmatch(r"[0-9a-f]{40}", head) is not None
            and type(count) is int
            and 0 < count <= 250,
            "AM_original_PR_identity",
        )
        rows = api.pages(endpoint + "/commits", None, count)
        graph: dict[str, list[str]] = {}
        for row in rows:
            revision = row.get("sha") if type(row) is dict else None
            parents = row.get("parents") if type(row) is dict else None
            require(
                type(revision) is str
                and re.fullmatch(r"[0-9a-f]{40}", revision) is not None
                and revision not in graph
                and type(parents) is list
                and all(
                    type(parent) is dict
                    and type(parent.get("sha")) is str
                    and re.fullmatch(r"[0-9a-f]{40}", parent["sha"]) is not None
                    for parent in parents
                ),
                "AM_original_complete_native_graph",
            )
            graph[cast(str, revision)] = [
                parent["sha"] for parent in cast(list[dict[str, Any]], parents)
            ]
        require(
            len(graph) == count and source in graph and donor in graph and head in graph,
            "AM_original_source_donor_membership",
        )
        for descendant, ancestor in ((head, donor), (donor, source)):
            pending, visited = [descendant], set()
            while pending:
                current = pending.pop()
                if current not in visited:
                    visited.add(current)
                    pending.extend(parent for parent in graph.get(current, []) if parent in graph)
            require(ancestor in visited, "AM_original_source_donor_ancestry")
    return upstream


def _alertmanager_reader_route(
    api: GitHubRead, args: argparse.Namespace, event: dict[str, Any], output: Path, deadline: float
) -> dict[str, Any]:
    """Choose initial own PR, positive first main or durable published without registry-state fallback."""
    import shutil
    from scripts.ci.prometheus_source_image import (
        Native,
        fresh_directory,
        require,
    )

    accepted = _alertmanager_accepted_producer()
    upstream = _alertmanager_upstream_identity(
        current=accepted["source"] != _ALERT_HISTORICAL_C10["source"], accepted=accepted, api=api
    )
    own_pr = 2494 if upstream == "0.34.2" else _ALERT_RECEIVER_PR
    own_branch = _ALERT_Q_BRANCH if upstream == "0.34.2" else _ALERT_RECEIVER_BRANCH
    name = os.environ.get("GITHUB_EVENT_NAME")
    repository = event.get("repository")
    require(
        type(repository) is dict
        and type(repository.get("id")) is int
        and repository["id"] == 1043311030
        and repository.get("full_name") == "Katsiarynakavaleuskaya/PulsePlate",
        "AM_reader_event_repository",
    )
    current = api.json("/repos/Katsiarynakavaleuskaya/PulsePlate/git/ref/heads/main")
    current_main = current.get("object", {}).get("sha")
    require(
        type(current_main) is str and re.fullmatch(r"[0-9a-f]{40}", current_main) is not None,
        "AM_current_main_binding",
    )
    if name == "pull_request":
        number = event.get("number")
        require(type(number) is int and number > 0, "AM_actual_PR_number")
        pr = api.json("/repos/Katsiarynakavaleuskaya/PulsePlate/pulls/" + str(number))
        event_pr = event.get("pull_request")
        require(
            type(event_pr) is dict
            and all(
                type(event_pr.get(side, {}).get("repo", {}).get("id")) is int
                and event_pr[side]["repo"]["id"] == 1043311030
                for side in ("head", "base")
            )
            and event_pr.get("head", {}).get("ref") == pr.get("head", {}).get("ref")
            and event_pr.get("base", {}).get("ref") == "main",
            "AM_reader_event_PR_repository",
        )
        require(
            type(pr.get("number")) is int
            and pr["number"] == number
            and pr.get("state") == "open"
            and pr.get("head", {}).get("sha") == args.source_sha
            and pr.get("base", {}).get("ref") == "main"
            and pr.get("head", {}).get("repo", {}).get("id") == 1043311030
            and pr.get("base", {}).get("repo", {}).get("id") == 1043311030
            and event.get("pull_request", {}).get("head", {}).get("sha") == args.source_sha
            and event["pull_request"].get("base", {}).get("sha") == pr["base"]["sha"]
            and current_main == pr["base"]["sha"],
            "AM_actual_same_repository_open_PR",
        )
        require(
            number != own_pr or pr["head"].get("ref") == own_branch,
            "AM_receiver_branch",
        )
        if number == own_pr:
            _alertmanager_original_lineage(api)
            return {
                "mode": "initial_own_PR_retained",
                "upstream_version": upstream,
                "pr": number,
                "head": args.source_sha,
                "base": pr["base"]["sha"],
            }
        return {
            "mode": "ordinary_published_PR",
            "upstream_version": upstream,
            "pr": number,
            "head": args.source_sha,
            "base": pr["base"]["sha"],
        }
    require(
        (
            name == "push"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"
            and event.get("ref") == "refs/heads/main"
            and event.get("deleted") is not True
            and event.get("after") == args.source_sha
        )
        or (name == "schedule" and os.environ.get("GITHUB_REF") == "refs/heads/main")
        or (name == "push" and os.environ.get("GITHUB_REF", "").startswith("refs/tags/v")),
        "AM_actual_trusted_reader_event",
    )
    require(
        args.source_sha == os.environ.get("GITHUB_SHA") and args.source_sha == current_main,
        "AM_exact_current_main_reader",
    )
    pr = api.json("/repos/Katsiarynakavaleuskaya/PulsePlate/pulls/" + str(own_pr))
    if (
        name == "push"
        and os.environ.get("GITHUB_REF") == "refs/heads/main"
        and os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
        and pr.get("merged") is True
        and pr.get("merge_commit_sha") == args.source_sha
    ):
        require(
            type(pr.get("number")) is int
            and pr["number"] == own_pr
            and pr.get("state") == "closed"
            and pr.get("base", {}).get("ref") == "main"
            and type(pr.get("head", {}).get("sha")) is str
            and re.fullmatch(r"[0-9a-f]{40}", pr["head"]["sha"]) is not None
            and pr.get("head", {}).get("ref") == own_branch
            and pr["head"].get("repo", {}).get("id") == 1043311030
            and pr["base"].get("repo", {}).get("id") == 1043311030,
            "AM_genuine_first_main_PR",
        )
        _alertmanager_original_lineage(api)
        before = event.get("before")
        require(
            type(before) is str and re.fullmatch(r"[0-9a-f]{40}", before) is not None,
            "AM_first_main_before",
        )
        git = shutil.which("git")
        require(git is not None and Path(git).is_absolute(), "AM_first_main_native_Git")
        evidence = output / "first-main-native-Git"
        fresh_directory(evidence)
        native = Native(evidence, deadline, 45)
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(evidence),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_NO_REPLACE_OBJECTS": "1",
        }
        raw = native.run(
            [
                git,
                "--no-replace-objects",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.hooksPath=/dev/null",
                "-C",
                str(args.material_root),
                "rev-list",
                "--parents",
                "-n",
                "1",
                args.source_sha,
            ],
            "actual-first-parent",
            env,
            cwd=args.material_root,
            maximum_seconds=8,
        )
        parents = raw.decode().strip().split()
        require(
            parents in ([args.source_sha, before], [args.source_sha, before, pr["head"]["sha"]]),
            "AM_first_main_native_parent_form",
        )
        return {
            "mode": "genuine_first_main_retained",
            "upstream_version": upstream,
            "pr": own_pr,
            "head": args.source_sha,
            "pr_head": pr["head"]["sha"],
            "base": before,
        }
    return {
        "mode": "ordinary_published_main",
        "upstream_version": upstream,
        "pr": own_pr,
        "head": args.source_sha,
        "base": args.source_sha,
    }


def _alertmanager_controller_binding(args: argparse.Namespace) -> None:
    """Require the separately ROOT-designated workflow pin and actual trusted checkout before credentials."""
    import shutil
    from scripts.ci.prometheus_source_image import Native, require

    controller = getattr(args, "alertmanager_controller_source", None)
    data_controller = os.environ.get("ALERTMANAGER_CONTROLLER_SOURCE", "")
    require(
        re.fullmatch(r"[0-9a-f]{40}", data_controller) is not None,
        "AM_controller_data_UNCONFIGURED_HOLD",
    )
    require(
        type(controller) is str
        and re.fullmatch(r"[0-9a-f]{40}", controller) is not None
        and controller == data_controller,
        "AM_controller_UNCONFIGURED_HOLD",
    )
    controller = cast(str, controller)
    material = getattr(args, "material_root", None)
    require(
        isinstance(material, Path)
        and material.is_absolute()
        and material.is_dir()
        and not material.is_symlink(),
        "AM_explicit_material_root",
    )
    git = shutil.which("git")
    require(git is not None and Path(git).is_absolute(), "AM_controller_native_Git")
    with tempfile.TemporaryDirectory(prefix="pulseplate-am-controller-") as temporary:
        evidence = Path(temporary)
        native = Native(evidence, time.monotonic() + 8, 45)
        observed = native.run(
            [
                git,
                "--no-replace-objects",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.hooksPath=/dev/null",
                "-C",
                str(REPO_ROOT),
                "rev-parse",
                "HEAD",
            ],
            "actual-controller-checkout",
            {
                "PATH": "/usr/bin:/bin",
                "HOME": str(evidence),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
            },
            cwd=REPO_ROOT,
            maximum_seconds=8,
            output_bound=4096,
        )
        require(observed == (controller + "\n").encode(), "AM_controller_actual_checkout")


def _alertmanager_close_preparation_api(api: GitHubRead, deadline: float) -> None:
    """Give API cleanup its own existing bound without replenishing the interrupted main clock."""
    import signal

    primary = sys.exc_info()[1]
    signal.setitimer(signal.ITIMER_REAL, 0)
    try:
        api.close()
        if api.private.exists() or api.private.is_symlink():
            raise RuntimeError("AM_credentials_removed_before_material_execution")
    except BaseException as cleanup_error:
        if primary is not None:
            primary.add_note("AM API cleanup also failed: " + type(cleanup_error).__name__)
            raise primary from None
        raise
    finally:
        remaining = deadline - time.monotonic()
        if remaining > 0:
            signal.setitimer(signal.ITIMER_REAL, remaining)
        elif primary is None:
            raise TimeoutError("AM complete preparation600 deadline exhausted during cleanup")


def _alertmanager_prepare_local(
    candidate: dict[str, Any],
    observation: Path,
    work: Path,
    limits: dict[str, int],
    deadline: float,
) -> dict[str, Any]:
    """Load and inspect the already authenticated OCI once, after credential cleanup, without claiming native success."""
    import shutil
    from scripts.ci.prometheus_source_image import Native, fresh_directory, one_object, require

    fresh_directory(work)
    evidence = work / "evidence"
    fresh_directory(evidence)
    config = work / "empty-docker-config"
    fresh_directory(config)
    native = Native(evidence, deadline, limits["NATIVE_CLEANUP_SECONDS"])
    docker = shutil.which("docker")
    require(docker is not None and Path(docker).is_absolute(), "AM_preparation_Docker")
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "LANG": "C.UTF-8",
        "DOCKER_CONFIG": str(config),
    }
    transport = _alertmanager_docker_load_transport(
        observation.parent / "candidate.oci.tar", candidate["graph"], work, deadline
    )
    native.run(
        [docker, "--config", str(config), "image", "load", "--input", transport["load_input"]],
        "prepare-retained-image",
        env,
        cwd=work,
        maximum_seconds=120,
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
                candidate["graph"]["config"]["digest"],
            ],
            "prepare-local-identity",
            env,
            cwd=work,
            maximum_seconds=30,
        )
    )
    require(
        image.get("Id") == candidate["graph"]["config"]["digest"]
        and image.get("Os") == "linux"
        and image.get("Architecture") == "amd64"
        and image.get("RootFS", {}).get("Layers") == candidate["graph"]["diff_ids"],
        "AM_preparation_actual_local_graph",
    )
    return {
        "image_id": image["Id"],
        "config_sha256": _ALERT_Q_SOURCE_FILES["deploy/alertmanager/alertmanager.yml"],
        "docker_load_transport": transport,
        "native_records": native.records,
    }


def _alertmanager_pull_published(
    api: GitHubRead,
    args: argparse.Namespace,
    route: dict[str, Any],
    sources: dict[str, bytes],
    output: Path,
    deadline: float,
) -> dict[str, Any]:
    """Read a positively published S with stdin-only credentials and no artifact-expiry dependency."""
    import shutil
    from scripts.ci.prometheus_source_image import (
        existing_public_package,
        immutable_tag_state,
        one_object,
        require,
    )

    base = _alertmanager_regular_sources(
        args.material_root, route["base"], output / "published-BASE-native-Git", deadline
    )
    templates = _alertmanager_source_snapshot(
        api, os.environ.get("ALERTMANAGER_CONTROLLER_SOURCE", ""), controller_templates=True
    )
    _alertmanager_render_source_contract(
        base,
        output / "published-BASE-contract",
        deadline,
        expected_case="accepted",
        controller_templates=templates,
    )
    require(
        base == sources
        and base["scripts/ci/fetch_docker_source_artifacts.py"] == Path(__file__).read_bytes(),
        "AM_published_complete_BASE_HEAD_selection",
    )
    predecessor = _alertmanager_publication_predecessor(
        api,
        args.material_root,
        route["base"],
        output / "github-read-evidence/published-predecessor-Git",
        deadline,
    )
    accepted = _alertmanager_accepted_producer()
    upstream = predecessor.get("upstream_version")
    require(upstream in ("0.34.1", "0.34.2"), "AM_published_authenticated_source_epoch_HOLD")
    graph = accepted["graph"]
    digest = graph["manifest"]["digest"]
    tag = "alertmanager-" + cast(str, upstream) + "-" + digest.removeprefix("sha256:")
    package, versions = existing_public_package(api)
    require(
        immutable_tag_state(versions, tag, digest) is True, "AM_positive_published_tag_required"
    )
    # All positive source/package/publication bindings precede this first login.
    registry = api.private / "config" / "AM-registry"
    registry.mkdir(mode=0o700)
    docker = shutil.which("docker")
    require(docker is not None and Path(docker).is_absolute(), "AM_published_absolute_Docker")
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    token = os.environ.get(
        (
            "GITHUB_TOKEN"
            if os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
            else "GHCR_READ_TOKEN"
        ),
        "",
    )
    require(
        owner.lower() == "katsiarynakavaleuskaya" and bool(token),
        "AM_published_scoped_read_credential",
    )
    environment = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(api.private / "home"),
        "DOCKER_CONFIG": str(registry),
        "LANG": "C.UTF-8",
    }
    prefix = [docker, "--config", str(registry)]
    api._capture(
        [*prefix, "login", "ghcr.io", "--username", owner, "--password-stdin"],
        2 * 1024**2,
        environment=environment,
        input_data=token.encode() + b"\n",
    )
    credential = registry / "config.json"
    metadata = credential.lstat()
    require(
        {entry.name for entry in registry.iterdir()} == {"config.json"}
        and stat.S_ISREG(metadata.st_mode)
        and metadata.st_uid == os.getuid()
        and metadata.st_nlink == 1
        and stat.S_IMODE(metadata.st_mode) == 0o600,
        "AM_published_owned_registry_config",
    )
    reference = "ghcr.io/katsiarynakavaleuskaya/pulseplate@" + digest
    manifest = api._capture(
        [*prefix, "buildx", "imagetools", "inspect", "--raw", reference],
        1024**2,
        environment=environment,
    )
    require(
        len(manifest) == graph["manifest"]["size"]
        and "sha256:" + sha256(manifest).hexdigest() == digest,
        "AM_published_exact_manifest_bytes",
    )
    decoded = one_object(manifest)
    require(
        decoded.get("config") == graph["config"] and decoded.get("layers") == graph["layers"],
        "AM_published_manifest_graph",
    )
    api._capture(
        [*prefix, "pull", "--platform", "linux/amd64", reference],
        4 * 1024**2,
        environment=environment,
    )
    image = one_object(
        api._capture(
            [*prefix, "image", "inspect", "--format", "{{json .}}", reference],
            1024**2,
            environment=environment,
        )
    )
    require(
        _alertmanager_contract_image([image], graph["config"]["digest"]) == "accepted",
        "AM_published_actual_local_identity",
    )
    return {
        "image_id": image["Id"],
        "config_sha256": _ALERT_Q_SOURCE_FILES["deploy/alertmanager/alertmanager.yml"],
        "publication_predecessor": predecessor,
        "public_package": package,
        "manifest_sha256": sha256(manifest).hexdigest(),
        "registry_login": True,
        "docker_load_transport": None,
    }


def _alertmanager_prepare_candidate_body(
    args: argparse.Namespace, limits: dict[str, int], deadline: float
) -> tuple[dict[str, Any], Path, Path, dict[str, Any]]:
    """Authenticate the original complete retained predecessor with current consumer data kept separate."""
    from scripts.ci.prometheus_source_image import (
        GitHubRead,
        fresh_directory,
        one_object,
        require,
    )

    accepted = _alertmanager_accepted_producer(
        args.alertmanager_candidate_run,
        args.alertmanager_candidate_artifact,
        args.alertmanager_candidate_source,
    )
    require(
        os.environ.get("GITHUB_EVENT_NAME") in ("pull_request", "push", "schedule")
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
        deadline,
        limits["CLEANUP_SECONDS"],
    )
    try:
        route = _alertmanager_reader_route(api, args, event, output, deadline)
        material_sources = _alertmanager_bind_material(
            args.material_root, args.source_sha, output / "current-material-native-Git", deadline
        )
        if route["mode"].startswith("ordinary_published"):
            prepared = _alertmanager_pull_published(
                api, args, route, material_sources, output, deadline
            )
            candidate = {"source": accepted["source"], "graph": accepted["graph"]}
            if route["upstream_version"] == "0.34.2":
                # source remains the independent C selection owner; actual H
                # production stays separately bound in publication_predecessor.
                candidate["root_inputs"] = prepared["publication_predecessor"][
                    "current_observation"
                ]["root_inputs"]
                ui = prepared["publication_predecessor"]["current_observation"].get(
                    "UI_file_hashes"
                )
                require(
                    type(ui) is dict
                    and "index.html.gz" in ui
                    and all(
                        type(name) is str
                        and bool(name)
                        and type(digest) is str
                        and _HEX_RE.fullmatch(digest) is not None
                        for name, digest in ui.items()
                    ),
                    "AM_published_native_UI_inventory",
                )
                candidate["UI_file_hashes"] = ui
                require(
                    _alertmanager_upstream_identity(candidate["root_inputs"], current=True)
                    == route["upstream_version"],
                    "AM_published_native_source_tuple",
                )
            payload = output / "candidate"
            fresh_directory(payload)
            (payload / "candidate-observation.json").write_text(json.dumps(candidate) + "\n")
            prepared["admission"] = route
            return candidate, payload, output, prepared
        templates = _alertmanager_source_snapshot(
            api, os.environ.get("ALERTMANAGER_CONTROLLER_SOURCE", ""), controller_templates=True
        )
        require(
            {path: material_sources[path] for path in _ALERT_SELECTION_FILES[:5]} == templates,
            "AM_reviewed_controller_data_closure",
        )
        before_sources = None
        before_reference = None
        if route["mode"] == "genuine_first_main_retained":
            before_sources = _alertmanager_regular_sources(
                args.material_root, route["base"], output / "first-main-BASE-native-Git", deadline
            )
            final_pr = _alertmanager_regular_sources(
                args.material_root,
                route["pr_head"],
                output / "first-main-final-PR-native-Git",
                deadline,
            )
            require(final_pr == material_sources, "AM_first_main_final_PR_selection_control")
            if route["upstream_version"] == "0.34.2":
                _alertmanager_original_lineage(api, historical_before=_ALERT_HISTORICAL_AM11)
                receiver = api.json("/repos/Katsiarynakavaleuskaya/PulsePlate/pulls/2497")
                merged = receiver.get("merge_commit_sha")
                require(
                    type(receiver.get("number")) is int
                    and receiver["number"] == _ALERT_RECEIVER_PR
                    and receiver.get("merged") is True
                    and receiver.get("state") == "closed"
                    and type(merged) is str
                    and re.fullmatch(r"[0-9a-f]{40}", merged) is not None
                    and receiver.get("head", {}).get("ref") == _ALERT_RECEIVER_BRANCH
                    and receiver.get("base", {}).get("ref") == "main"
                    and all(
                        type(receiver.get(side, {}).get("repo", {}).get("id")) is int
                        and receiver[side]["repo"]["id"] == 1043311030
                        for side in ("head", "base")
                    ),
                    "AM_before_actual_historical_receiver_merge",
                )
                from scripts.ci.prometheus_source_image import require_native_ancestor

                require_native_ancestor(api, cast(str, merged), route["base"])
                before_reference = _alertmanager_regular_sources(
                    args.material_root,
                    cast(str, merged),
                    output / "historical-AM11-reference-native-Git",
                    deadline,
                )
                require(before_sources == before_reference, "AM_before_full_six_reference_identity")
                route["historical_before_reference"] = merged
        qualification, support_binding = _alertmanager_selected_inputs(
            api, args, output, accepted, upstream_version=route["upstream_version"]
        )
        authenticated = _alertmanager_authenticated_inputs(
            api,
            args.alertmanager_candidate_run,
            args.alertmanager_candidate_artifact,
            args.alertmanager_candidate_source,
            output / "candidate.zip",
            kind="candidate",
            upstream_version=route["upstream_version"],
            source_branch=_ALERT_Q_BRANCH if route["upstream_version"] == "0.34.2" else None,
        )
        source = _alertmanager_source_snapshot(
            api, args.alertmanager_candidate_source, accepted=True
        )
    finally:
        _alertmanager_close_preparation_api(api, deadline)
    require(
        not api.private.exists() and not api.private.is_symlink(),
        "AM_credentials_removed_before_preparation_native",
    )
    if before_sources is not None:
        _alertmanager_render_source_contract(
            before_sources,
            output / "first-main-BASE-contract",
            deadline,
            expected_case="historical-AM11-before" if before_reference is not None else "old",
            controller_templates=before_reference if before_reference is not None else templates,
        )
        _alertmanager_render_source_contract(
            material_sources,
            output / "first-main-current-contract",
            deadline,
            expected_case="accepted",
            controller_templates=templates,
        )
    inspected = _alertmanager_qualified_payload(
        output / "qualification.zip",
        material_root=args.material_root,
        current=accepted["source"] != _ALERT_HISTORICAL_C10["source"],
        producer_recipe=source["deploy/alertmanager/Containerfile"],
    )
    support = output / "support"
    current = accepted["source"] != _ALERT_HISTORICAL_C10["source"]
    supported = _alertmanager_support_payload(
        output / "support.zip",
        support,
        qualification=qualification if current else None,
        support_binding=support_binding if current else None,
        qualification_payload=inspected if current else None,
    )
    if current:
        _alertmanager_bind_current_plan(inspected["plan"], supported)
    inspected["plan"]["probe"] = supported["probe"]
    payload = output / "candidate"
    candidate = _alertmanager_candidate_payload(
        output / "candidate.zip",
        payload,
        source,
        inspected,
        support,
        qualification=qualification if current else None,
        support_binding=support_binding if current else None,
        support_report=supported if current else None,
    )
    require(
        candidate.get("source") == authenticated["source"],
        "AM_original_producer_not_current_consumer",
    )
    prepared = _alertmanager_prepare_local(
        candidate, payload / "candidate-observation.json", output / "preparation", limits, deadline
    )
    prepared["admission"] = route
    return candidate, payload, output, prepared


def _alertmanager_prepare_candidate(
    args: argparse.Namespace, limits: dict[str, int]
) -> tuple[dict[str, Any], Path, Path, dict[str, Any]]:
    """Preempt the whole one-shot preparation, including pure payload/serializer/load work, at600s."""
    import signal

    started = time.monotonic()
    saved_timer = signal.getitimer(signal.ITIMER_REAL)
    deadline = min(
        started + limits["PREP_SECONDS"],
        started + saved_timer[0] if saved_timer[0] > 0 else float("inf"),
    )
    saved_handler = signal.getsignal(signal.SIGALRM)

    def interrupt(signum: int, frame: object) -> None:
        raise TimeoutError("AM complete preparation600 deadline exhausted")

    signal.signal(signal.SIGALRM, interrupt)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, deadline - time.monotonic()))
    try:
        _alertmanager_controller_binding(args)
        return _alertmanager_prepare_candidate_body(args, limits, deadline)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, saved_handler)
        if saved_timer[0] > 0:
            remaining = saved_timer[0] - (time.monotonic() - started)
            if remaining <= 0:
                primary = sys.exc_info()[1]
                if primary is not None:
                    primary.add_note("Caller timer also expired during AM preparation")
                else:
                    raise TimeoutError("Caller timer expired during AM preparation")
            else:
                signal.setitimer(signal.ITIMER_REAL, remaining, saved_timer[1])


def _alertmanager_consume(args: argparse.Namespace) -> None:
    """Compose one complete retained preparation with optional actual full-native replay on this runner."""
    from scripts.ci.prometheus_source_image import require

    _alertmanager_accepted_producer(
        args.alertmanager_candidate_run,
        args.alertmanager_candidate_artifact,
        args.alertmanager_candidate_source,
    )
    require(
        type(args.alertmanager_candidate_run) is int
        and type(args.alertmanager_candidate_artifact) is int
        and type(args.alertmanager_candidate_source) is str,
        "AM_accepted_producer_exact_selectors",
    )
    limits = _alertmanager_limits(caller=True)
    candidate, payload, output, prepared = _alertmanager_prepare_candidate(args, limits)
    result: dict[str, Any] = {
        "consumer": args.source_sha,
        "original_producer": _ALERT_ACCEPTED_CANDIDATE,
        "graph": candidate["graph"],
        "preparation": prepared,
        "compiler_starts": 0,
        "registry_login": prepared.get("registry_login", False),
    }
    if not args.alertmanager_prepare_only:
        result["native"] = _alertmanager_native_candidate(
            candidate,
            payload / "candidate-observation.json",
            output / "native",
            limits,
            prepared=prepared,
            material_root=args.material_root,
        )
    (output / "consumer-observation.json").write_text(json.dumps(result, indent=2) + "\n")
    prepared["observation"] = str(payload / "candidate-observation.json")
    for name in ("image_id", "config_sha256", "observation"):
        print(name + "=" + prepared[name])


def _alertmanager_publish(
    args: argparse.Namespace,
    api: GitHubRead,
    output: Path,
    retained: Path,
    result: dict[str, Any],
    limits: dict[str, int],
    *,
    qualification: dict[str, Any] | None = None,
    support_binding: dict[str, Any] | None = None,
    prepared: dict[str, Any] | None = None,
    phase: str = "prepare",
) -> dict[str, Any]:
    """One existing publisher: prepare, fresh rebind, then one guarded registry copy."""
    import shutil
    from scripts.ci.prometheus_source_image import (
        Native,
        fresh_directory,
        require,
        retained_tool,
        existing_public_package,
        immutable_tag_state,
        _blob,
        pack_layout,
        file_hash,
        check_deadline,
        tree_inventory,
    )

    accepted = _alertmanager_accepted_producer()
    require(
        phase in ("prepare", "rebind", "publish") and (prepared is None) == (phase == "prepare"),
        "AM_closed_publication_phase",
    )
    require(qualification is None and support_binding is None, "AM_publication_owns_exact_H_Q_S")
    require(
        accepted["source"] != _ALERT_HISTORICAL_C10["source"],
        "AM_publication_requires_current_accepted_C",
    )
    require(
        type(args.alertmanager_pr) is int
        and args.alertmanager_pr == 2494
        and type(args.source_sha) is str
        and re.fullmatch(r"[0-9a-f]{40}", args.source_sha) is not None
        and args.alertmanager_candidate_source == args.source_sha,
        "AM_publication_actual_H_selectors",
    )
    endpoint = "/repos/Katsiarynakavaleuskaya/PulsePlate"

    def read_inputs(directory: Path, *, source_proof: bool) -> dict[str, Any]:
        fresh_directory(directory)
        main = api.json(endpoint + "/git/ref/heads/main")
        require(
            main.get("object", {}).get("sha") == args.source_sha
            and main.get("ref") == "refs/heads/main",
            "AM_exact_current_main_publication",
        )
        pr = api.json(endpoint + "/pulls/2494")
        merge = pr.get("merge_commit_sha")
        require(
            type(pr.get("number")) is int
            and pr["number"] == 2494
            and pr.get("merged") is True
            and pr.get("state") == "closed"
            and type(merge) is str
            and re.fullmatch(r"[0-9a-f]{40}", merge) is not None
            and pr.get("head", {}).get("ref") == _ALERT_Q_BRANCH
            and pr.get("base", {}).get("ref") == "main"
            and all(
                type(pr.get(side, {}).get("repo", {}).get("id")) is int
                and pr[side]["repo"]["id"] == 1043311030
                for side in ("head", "base")
            ),
            "AM_separate_human_merge_observed",
        )
        count = pr.get("commits")
        require(type(count) is int and 0 < count <= 250, "AM_publication_PR_commit_inventory")
        commits = api.pages(endpoint + "/pulls/2494/commits", None, count)
        require(
            sum(row.get("sha") == accepted["source"] for row in commits) == 1,
            "AM_publication_accepted_C_actual_PR_graph",
        )
        git = shutil.which("git")
        require(git is not None and Path(git).is_absolute(), "AM_publication_native_Git")
        command = [
            cast(str, git),
            "--no-replace-objects",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-C",
            str(REPO_ROOT),
            "merge-base",
            "--is-ancestor",
            cast(str, merge),
            args.source_sha,
        ]
        environment = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(api.private / "home"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_NO_REPLACE_OBJECTS": "1",
        }
        if source_proof:
            proof = retained / "publication-source-proof"
            fresh_directory(proof)
            native = Native(proof, api.deadline, limits["CLEANUP_SECONDS"])
            primary: BaseException | None = None
            try:
                native.run(
                    command,
                    "actual-merge-ancestor-H",
                    environment,
                    cwd=REPO_ROOT,
                    maximum_seconds=8,
                )
            except BaseException as error:
                primary = error
                raise
            finally:
                try:
                    (proof / "native-observation.json").write_text(
                        json.dumps({"native_records": native.records}, indent=2) + "\n"
                    )
                except BaseException as error:
                    if primary is not None:
                        primary.add_note(
                            "AM publication source-proof retention failed: " + type(error).__name__
                        )
                        raise primary from None
                    raise
        else:
            api._capture(command, 1024**2, environment=environment)
        material = _alertmanager_whole_material(api, args.source_sha)
        host = _alertmanager_host_inputs(api)
        source = _alertmanager_source_snapshot(api, args.source_sha, upstream_version="0.34.2")
        source_hashes = {name: sha256(raw).hexdigest() for name, raw in source.items()}
        bindings: dict[str, Any] = {}
        for kind, prefix in (
            ("qualification", "qualification"),
            ("support", "support"),
            ("candidate", "candidate"),
        ):
            run = getattr(args, "alertmanager_" + prefix + "_run")
            artifact = getattr(args, "alertmanager_" + prefix + "_artifact")
            revision = getattr(args, "alertmanager_" + prefix + "_source")
            require(
                type(run) is int
                and run > 0
                and type(artifact) is int
                and artifact > 0
                and revision == args.source_sha
                and str(run) != os.environ.get("GITHUB_RUN_ID"),
                "AM_publication_exact_terminal_H_inputs",
            )
            descriptor = api.json(endpoint + f"/actions/artifacts/{artifact}")
            require(type(descriptor) is dict, "AM_publication_artifact_metadata")
            bindings[kind] = _alertmanager_authenticated_inputs(
                api,
                run,
                artifact,
                revision,
                directory / (prefix + ".zip"),
                kind=kind,
                current_source_files=(
                    source_hashes
                    if kind == "candidate"
                    else {name: source_hashes[name] for name in _ALERT_Q_SOURCE_FILES}
                ),
                current_artifact_digest=descriptor.get("digest"),
                upstream_version="0.34.2",
                source_branch="main",
            )
        producer = dict(bindings["candidate"], merge_commit=merge)
        inspected = _alertmanager_qualified_payload(
            directory / "qualification.zip",
            current=True,
            producer_recipe=source["deploy/alertmanager/Containerfile"],
        )
        require(
            _alertmanager_upstream_identity(inspected["root_inputs"], current=True) == "0.34.2",
            "AM_publication_exact_upstream",
        )
        support = directory / "support"
        supported = _alertmanager_support_payload(
            directory / "support.zip",
            support,
            qualification=bindings["qualification"],
            support_binding=bindings["support"],
            qualification_payload=inspected,
        )
        _alertmanager_bind_current_plan(inspected["plan"], supported)
        inspected["plan"]["probe"] = supported["probe"]
        candidate = _alertmanager_candidate_payload(
            directory / "candidate.zip",
            directory / "candidate",
            source,
            inspected,
            support,
            qualification=bindings["qualification"],
            support_binding=bindings["support"],
            support_report=supported,
            merged_producer=producer,
            merged_material=material,
        )
        tool, qualified = retained_tool(api, REPO_ROOT, directory)
        (support / "trivy").chmod(0o555)
        support_inventory = tree_inventory(support, deadline=api.deadline)
        binding = {
            "material": material,
            "host": host,
            "inputs": bindings,
            "merge_commit": merge,
            "accepted_C": accepted,
            "graph": candidate["graph"],
            "OCI_archive_sha256": candidate["OCI_archive_sha256"],
            "tool": qualified["coordinates"],
            "support_inventory": support_inventory,
        }
        return {
            "binding": binding,
            "candidate": candidate,
            "candidate_directory": directory / "candidate",
            "support": support,
            "support_report": supported,
            "tool": tool,
        }

    observed = read_inputs(output / (phase + "-inputs"), source_proof=phase == "prepare")
    if phase == "prepare":
        initial_identity, initial_versions = existing_public_package(api)
        initial_digest = observed["candidate"]["graph"]["manifest"]["digest"]
        immutable_tag_state(
            initial_versions,
            "alertmanager-0.34.2-" + initial_digest.removeprefix("sha256:"),
            initial_digest,
        )
        result["preparation_public_package"] = initial_identity
        result.update(
            original_producer=observed["binding"]["inputs"]["candidate"],
            publication_merge_sha=observed["binding"]["merge_commit"],
            publication_source_sha=args.source_sha,
            material=observed["binding"]["material"],
            host_inputs=observed["binding"]["host"],
            graph=observed["candidate"]["graph"],
            qualified_tool=observed["binding"]["tool"],
        )
        return observed
    require(
        prepared is not None and observed["binding"] == prepared["binding"],
        "AM_publication_fresh_binding_drift",
    )
    prepared = cast(dict[str, Any], prepared)
    candidate: dict[str, Any] = prepared["candidate"]
    support, tool = prepared["support"], prepared["tool"]

    def verify_local() -> None:
        require(
            tree_inventory(support, deadline=api.deadline)
            == prepared["binding"]["support_inventory"],
            "AM_publication_local_support_drift",
        )
        require(
            _alertmanager_candidate_graph(
                prepared["candidate_directory"] / "layout",
                support,
                candidate["graph"]["files"],
                current=True,
            )
            == candidate["graph"]
            and file_hash(prepared["candidate_directory"] / "candidate.oci.tar", api.deadline)
            == candidate["OCI_archive_sha256"],
            "AM_publication_local_subject_drift",
        )
        require(
            tool.is_absolute()
            and tool.is_file()
            and not tool.is_symlink()
            and file_hash(tool, api.deadline) == prepared["binding"]["tool"]["binary_sha256"],
            "AM_publication_retained_ORAS_bytes",
        )

    verify_local()
    digest = candidate["graph"]["manifest"]["digest"]
    tag = "alertmanager-0.34.2-" + digest.removeprefix("sha256:")
    destination = "ghcr.io/katsiarynakavaleuskaya/pulseplate"
    identity, versions = existing_public_package(api)
    present = immutable_tag_state(versions, tag, digest)
    result["public_package"] = identity
    result["tag"] = tag
    if phase == "rebind":
        return prepared
    security = result.get("pre_copy_security", {})
    native_proof = result.get("pre_copy_native", {})
    require(
        result.get("preparation_credentials_removed") is True
        and type(security) is dict
        and type(native_proof) is dict
        and security.get("scanner", {}).get("sha256") == _ALERT_TRIVY_SHA256
        and security.get("scanner", {}).get("DB") == prepared["support_report"]["scanner"]["DB"]
        and all(
            type(proof.get("native_records")) is list
            and bool(proof["native_records"])
            and all(
                type(row) is dict
                and type(row.get("exit")) is int
                and row["exit"] == 0
                and row.get("failure") is None
                for row in proof["native_records"]
            )
            for proof in (security, native_proof)
        )
        and native_proof.get("validation_scope") == "merged_H_selected_image",
        "AM_publication_fresh_security_native_before_credentials",
    )
    original_inventory = _alertmanager_candidate_scan_evidence(
        prepared["candidate_directory"] / "security-evidence",
        candidate["security"],
        current=True,
        comparison_subject=candidate["graph"]["config"]["digest"],
        deadline=api.deadline,
    )
    fresh_inventory = _alertmanager_candidate_scan_evidence(
        output / "security/evidence",
        security,
        current=True,
        comparison_subject=candidate["graph"]["config"]["digest"],
        deadline=api.deadline,
    )
    require(
        type(original_inventory) is dict
        and type(fresh_inventory) is dict
        and original_inventory == fresh_inventory,
        "AM_publication_same_subject_inventory_drift",
    )
    check_deadline(api.deadline)
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
        str(prepared["candidate_directory"] / "layout") + "@" + digest,
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
    latest = read_inputs(output / "immediate-precopy-inputs", source_proof=False)
    require(latest["binding"] == prepared["binding"], "AM_immediate_precopy_all_inputs_drift")
    verify_local()
    final_identity, final_versions = existing_public_package(api)
    require(
        final_identity == identity and immutable_tag_state(final_versions, tag, digest) == present,
        "AM_immediate_precopy_package_tag_drift",
    )
    if not present:
        require(
            api.json("/repos/Katsiarynakavaleuskaya/PulsePlate/git/ref/heads/main")
            .get("object", {})
            .get("sha")
            == args.source_sha,
            "AM_main_immediately_before_copy",
        )
        result["copy_attempts"] = 1
        # Capture can fail before or after process start; neither zero invocations
        # nor zero registry effects is established by an exceptional return.
        result["copy_invocations"] = None
        result["package_WRITE"] = "UNKNOWN_COPY_ATTEMPT_MAY_HAVE_WRITTEN"
        api._capture(copy, 2 * 1024**2, environment=env)
        result["copy_invocations"] = 1
        result["package_WRITE"] = "OBSERVED_SUCCESSFUL_INTENDED_COPY"
    else:
        result["package_WRITE"] = "UNEXERCISED_EXISTING_SAME_SUBJECT"
    api._capture(pullback, 2 * 1024**2, environment=env)
    actual = _alertmanager_candidate_graph(
        output / "pullback", support, candidate["graph"]["files"], current=True
    )
    require(actual == candidate["graph"], "AM_immutable_pullback_graph_payload")
    for descriptor in (actual["manifest"], actual["config"], *actual["layers"]):
        require(
            _blob(prepared["candidate_directory"] / "layout", descriptor)
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
    result["pullback_OCI_archive_sha256"] = file_hash(retained / "candidate.oci.tar", api.deadline)
    result["status"] = "OBSERVED_COPY_AND_IMMUTABLE_BLOBS_NATIVE_PENDING"
    result["tag_observation_limit"] = (
        "Canonical finite pre/post observations; no atomic no-clobber or continuous immutability claim."
    )
    return candidate


def _alertmanager_retain_execution(output: Path, retained: Path) -> None:
    """Retain raw failures and both full native publisher phases in the existing carrier."""
    import shutil
    from scripts.ci.prometheus_source_image import file_hash, require, tree_inventory

    observations = {
        "pair": ("pair-observation.json", "invocation-start.json"),
        "security": ("security-observation.json",),
        "pre-native": ("native-observation.json",),
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


def _alertmanager_material_tree(
    api: GitHubRead, source: str, query: Any
) -> tuple[str, dict[str, tuple[str, str]]]:
    """Existing complete tree recognizer, shared by live and historical material readers."""
    from scripts.ci.prometheus_source_image import require

    endpoint = "/repos/Katsiarynakavaleuskaya/PulsePlate"
    commit = api.json(endpoint + "/git/commits/" + source)
    require(
        type(commit) is dict and commit.get("sha") == source and type(commit.get("tree")) is dict,
        "AM_material_API_commit",
    )
    tree_sha = commit["tree"].get("sha")
    require(
        type(tree_sha) is str and re.fullmatch(r"[0-9a-f]{40}", tree_sha) is not None,
        "AM_material_API_tree",
    )
    require(
        query("rev-parse", source + "^{tree}") == (tree_sha + "\n").encode(),
        "AM_material_local_tree",
    )
    tree = api.json(endpoint + "/git/trees/" + tree_sha + "?recursive=1")
    require(
        type(tree) is dict
        and tree.get("sha") == tree_sha
        and tree.get("truncated") is False
        and type(tree.get("tree")) is list
        and 0 < len(tree["tree"]) <= 25000,
        "AM_material_complete_tree",
    )
    expected: dict[str, tuple[str, str]] = {}
    seen: set[str] = set()
    for row in tree["tree"]:
        require(type(row) is dict and type(row.get("path")) is str, "AM_material_tree_row")
        path = row["path"]
        require(
            path not in seen
            and "\\" not in path
            and "\x00" not in path
            and all(part not in ("", ".", "..") for part in path.split("/")),
            "AM_material_tree_path",
        )
        seen.add(path)
        mode, kind, oid = row.get("mode"), row.get("type"), row.get("sha")
        require(
            type(oid) is str and re.fullmatch(r"[0-9a-f]{40}", oid) is not None,
            "AM_material_tree_oid",
        )
        if mode == "040000":
            require(kind == "tree", "AM_material_tree_directory")
            continue
        require(
            (mode, kind)
            in {("100644", "blob"), ("100755", "blob"), ("120000", "blob"), ("160000", "commit")},
            "AM_material_tree_type",
        )
        expected[path] = (mode, oid)
    native_tree: dict[str, tuple[str, str]] = {}
    raw_tree = query("ls-tree", "-r", "-z", source)
    require(raw_tree.endswith(b"\0"), "AM_material_native_tree_terminator")
    for record in raw_tree[:-1].split(b"\0"):
        header, separator, path_bytes = record.partition(b"\t")
        fields = header.split()
        require(
            separator == b"\t" and len(fields) == 3 and fields[1] in (b"blob", b"commit"),
            "AM_material_native_tree_record",
        )
        path = path_bytes.decode("utf-8")
        require(path not in native_tree, "AM_material_native_tree_duplicate")
        native_tree[path] = (fields[0].decode("ascii"), fields[2].decode("ascii"))
    require(native_tree == expected, "AM_material_API_native_tree_equality")
    return tree_sha, expected


def _alertmanager_whole_material(api: GitHubRead, source: str) -> dict[str, Any]:
    """Bind this AM checkout's typed Git tree, index and bytes to the authenticated source."""
    import shutil
    from scripts.ci.prometheus_source_image import check_deadline, require

    require(
        type(source) is str and re.fullmatch(r"[0-9a-f]{40}", source) is not None,
        "AM_material_source",
    )
    git = shutil.which("git")
    require(git is not None and Path(git).is_absolute(), "AM_material_absolute_git")
    environment = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(api.private / "home"),
        "LANG": "C.UTF-8",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }

    def query(*arguments: str) -> bytes:
        captured = api._capture(
            [
                cast(str, git),
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.hooksPath=" + os.devnull,
                "-C",
                str(REPO_ROOT),
                *arguments,
            ],
            16 * 1024**2,
            environment=environment,
        )
        require(type(captured) is bytes, "AM_material_query_bytes")
        return cast(bytes, captured)

    require(query("rev-parse", "HEAD") == (source + "\n").encode(), "AM_material_HEAD")
    graft = query("rev-parse", "--git-path", "info/grafts").decode().strip()
    require(bool(graft) and "\n" not in graft, "AM_material_graft_path")
    graft_path = Path(graft) if Path(graft).is_absolute() else REPO_ROOT / graft
    require(not graft_path.exists() and not graft_path.is_symlink(), "AM_material_grafts")
    tree_sha, expected = _alertmanager_material_tree(api, source, query)
    indexed: dict[str, tuple[str, str]] = {}
    raw_index = query("ls-files", "--stage", "-z")
    require(raw_index.endswith(b"\0"), "AM_material_index_terminator")
    for record in raw_index[:-1].split(b"\0"):
        header, separator, path_bytes = record.partition(b"\t")
        fields = header.split()
        require(
            separator == b"\t" and len(fields) == 3 and fields[2] == b"0", "AM_material_index_stage"
        )
        path = path_bytes.decode("utf-8")
        require(path not in indexed, "AM_material_duplicate_index")
        indexed[path] = (fields[0].decode("ascii"), fields[1].decode("ascii"))
    require(indexed == expected, "AM_material_index_tree_equality")
    # Fresh producer workspaces contain no ignored/untracked executable or build input.
    for arguments in (
        ("ls-files", "--others", "--exclude-standard", "-z"),
        ("ls-files", "--others", "--ignored", "--exclude-standard", "-z"),
    ):
        require(query(*arguments) == b"", "AM_material_untracked_or_ignored_input")
    observed: list[dict[str, str | int]] = []
    total = 0
    for path, (mode, oid) in sorted(expected.items()):
        check_deadline(api.deadline)
        leaf = REPO_ROOT / path
        for parent in leaf.parents:
            if parent == REPO_ROOT:
                break
            require(parent.is_dir() and not parent.is_symlink(), "AM_material_parent_type")
        if mode == "160000":
            require(
                path == "tools/cybersecurity_skills"
                and oid == "d04d818b41cc300f8110f17ea167fa494db7fb29"
                and not leaf.is_symlink()
                and (not leaf.exists() or leaf.is_dir()),
                "AM_material_nonexecuted_gitlink",
            )
            observed.append(
                {
                    "path": path,
                    "mode": mode,
                    "oid": oid,
                    "content_scope": "uninspected_nonexecuted_gitlink_pointer_only",
                    "worktree_state": "directory" if leaf.exists() else "uninitialized_absent",
                }
            )
            continue
        info = leaf.lstat()
        if mode == "120000":
            require(
                not path.startswith(("scripts/", "tests/", ".github/", "deploy/"))
                and path
                not in {"requirements-dev.txt", "constraints.txt", "Dockerfile", "Makefile"}
                and not path.endswith((".py", ".pyc", ".pth", ".so")),
                "AM_material_consumed_symlink",
            )
            require(stat.S_ISLNK(info.st_mode), "AM_material_symlink_type")
            raw = os.fsencode(os.readlink(leaf))
        else:
            require(
                stat.S_ISREG(info.st_mode)
                and info.st_nlink == 1
                and ("100755" if info.st_mode & 0o111 else "100644") == mode
                and info.st_size <= 128 * 1024**2,
                "AM_material_regular_mode",
            )
            descriptor = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, "rb") as stream:
                opened = os.fstat(stream.fileno())
                require(
                    (opened.st_dev, opened.st_ino, opened.st_size)
                    == (info.st_dev, info.st_ino, info.st_size),
                    "AM_material_open_binding",
                )
                raw = stream.read(128 * 1024**2 + 1)
            require(len(raw) == info.st_size, "AM_material_file_length")
        total += len(raw)
        require(total <= 1024**3, "AM_material_total_byte_bound")
        blob = sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
        ).hexdigest()
        require(blob == oid, "AM_material_worktree_blob")
        after = leaf.lstat()
        require(
            (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns),
            "AM_material_read_drift",
        )
        observed.append(
            {
                "path": path,
                "mode": mode,
                "oid": oid,
                "bytes": len(raw),
                "sha256": sha256(raw).hexdigest(),
            }
        )
    require(
        query("ls-files", "--stage", "-z") == raw_index
        and query("rev-parse", "HEAD") == (source + "\n").encode(),
        "AM_material_final_index_HEAD",
    )
    return {
        "source": source,
        "tree": tree_sha,
        "members": observed,
        "gitlink_scope": "exact nonexecuted pointer/type only; no recursive content claim",
        "shallow_scope": "whole tree/bytes only; selected merge ancestry separately authenticated",
    }


def _alertmanager_host_inputs(api: GitHubRead) -> dict[str, Any]:
    """Measure the selected isolated host tools separately from tracked source identity."""
    import importlib.metadata
    import shutil
    import site
    import sysconfig
    import pytest
    import yaml
    import pip._vendor.certifi
    from scripts.ci.check_python_startup_hooks import collect_unexpected_executable_pth_files
    from scripts.ci.install_locked_python_requirements import (
        _exact_locked_artifacts,
        _normalized_package_name,
    )
    from scripts.ci.prometheus_source_image import check_deadline, file_hash, require

    prefix = Path(sys.prefix)
    require(
        sys.platform == "linux"
        and os.uname().machine == "x86_64"
        and prefix.is_absolute()
        and prefix != Path(sys.base_prefix)
        and not prefix.is_relative_to(REPO_ROOT)
        and not prefix.is_symlink()
        and sys.executable == str(prefix / "bin/python")
        and sys.version_info[:3] == (3, 13, 14)
        and site.ENABLE_USER_SITE is False
        and not os.environ.get("PYTHONPATH")
        and not os.environ.get("PYTHONHOME")
        and os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
        and not ({"sitecustomize", "usercustomize"} & set(sys.modules)),
        "AM_qualified_host_interpreter",
    )
    expected = set(_exact_locked_artifacts((REPO_ROOT / "requirements-dev.txt",)))
    expected.add(("pip", "26.2.2"))
    distributions = list(importlib.metadata.distributions())
    versions = [
        (_normalized_package_name(dist.metadata["Name"]), dist.version) for dist in distributions
    ]
    require(
        len(versions) == len(set(versions)) and set(versions) == expected,
        "AM_complete_host_locked_distributions",
    )
    require(
        importlib.metadata.version("pytest") == "9.1.1"
        and importlib.metadata.version("PyYAML") == "6.0.3"
        and file_hash(Path(pip._vendor.certifi.where()), api.deadline)
        == "50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785",
        "AM_host_pytest_yaml_pip_trust",
    )
    sites = {Path(value) for value in site.getsitepackages()}
    require(
        bool(sites)
        and all(path.is_relative_to(prefix) and not path.is_symlink() for path in sites),
        "AM_host_site_roots",
    )
    require(not collect_unexpected_executable_pth_files(sites), "AM_host_startup_hooks")
    declared: set[Path] = set()
    rows: list[dict[str, Any]] = []
    for dist in distributions:
        distribution_files = dist.files
        require(distribution_files is not None, "AM_host_distribution_files_missing")
        for item in cast(Sequence[Any], distribution_files):
            check_deadline(api.deadline)
            located = dist.locate_file(item)
            require(isinstance(located, os.PathLike), "AM_host_distribution_filesystem_path")
            filesystem_path = os.fspath(cast(os.PathLike[str], located))
            require(type(filesystem_path) is str, "AM_host_distribution_path_text")
            path = Path(filesystem_path)
            resolved = path.resolve(strict=True)
            require(
                resolved.is_relative_to(prefix) and path.is_file() and not path.is_symlink(),
                "AM_host_distribution_file_boundary",
            )
            if resolved in declared:
                continue
            declared.add(resolved)
            require(len(declared) <= 50000, "AM_host_distribution_file_bound")
            rows.append(
                {
                    "path": str(resolved.relative_to(prefix)),
                    "sha256": file_hash(resolved, api.deadline),
                    "bytes": resolved.stat().st_size,
                }
            )
    actual: set[Path] = set()
    visited = 0
    for root in sites:
        for path in root.rglob("*"):
            check_deadline(api.deadline)
            visited += 1
            require(visited <= 100000, "AM_host_site_inventory_bound")
            require(not path.is_symlink(), "AM_host_site_alias")
            if path.is_file():
                require(path.stat().st_nlink == 1, "AM_host_site_hardlink")
                resolved = path.resolve(strict=True)
                require(resolved in declared, "AM_host_unregistered_site_input")
                actual.add(resolved)
    require(actual <= declared, "AM_host_unregistered_site_input")
    for module in (pytest, yaml):
        require(
            Path(cast(str, module.__file__)).resolve(strict=True) in declared,
            "AM_host_import_origin",
        )
    stdlib = Path(sysconfig.get_path("stdlib")).resolve(strict=True)
    standard: list[dict[str, Any]] = []
    visited = 0
    for path in stdlib.rglob("*"):
        check_deadline(api.deadline)
        visited += 1
        require(visited <= 100000, "AM_host_stdlib_inventory_bound")
        if "site-packages" in path.relative_to(stdlib).parts or not path.is_file():
            continue
        require(not path.is_symlink() and len(standard) < 25000, "AM_host_stdlib_input")
        standard.append(
            {
                "path": str(path.relative_to(stdlib)),
                "sha256": file_hash(path, api.deadline),
                "bytes": path.stat().st_size,
            }
        )
    tools = {}
    for name in (
        "docker",
        "git",
        "gh",
        "openssl",
        "env",
        "sudo",
        "install",
        "rm",
        "systemctl",
        "busctl",
        "test",
    ):
        selected = shutil.which(name)
        require(
            selected is not None and Path(selected).is_absolute(), "AM_host_tool_missing_" + name
        )
        path = Path(cast(str, selected)).resolve(strict=True)
        require(path.is_file(), "AM_host_tool_not_file")
        if name in {"docker", "openssl", "env", "sudo", "install", "rm", "systemctl"}:
            for search in ("/usr/bin:/bin", os.defpath):
                native_path = shutil.which(name, path=search)
                require(
                    native_path is not None and Path(native_path).resolve(strict=True) == path,
                    "AM_host_native_resolver_identity",
                )
        tools[name] = {"path": str(path), "sha256": file_hash(path, api.deadline)}
    require(
        Path(api.gh).resolve(strict=True) == Path(tools["gh"]["path"]),
        "AM_host_GitHub_transport_binary",
    )
    environment = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(api.private / "home"),
        "LANG": "C.UTF-8",
    }
    docker = tools["docker"]["path"]
    observations = {}
    for label, arguments in (
        ("docker_versions", ["version", "--format", "{{json .}}"]),
        (
            "docker_storage",
            [
                "info",
                "--format",
                "driver={{json .Driver}} os={{json .OSType}} arch={{json .Architecture}}",
            ],
        ),
        ("compose_version", ["compose", "version", "--short"]),
        ("docker_plugins", ["info", "--format", "{{json .ClientInfo.Plugins}}"]),
    ):
        raw = api._capture([docker, *arguments], 1024**2, environment=environment)
        require(bool(raw.strip()), "AM_host_native_observation_empty")
        observations[label] = raw.decode("utf-8")
    plugins = json.loads(observations["docker_plugins"])
    require(
        type(plugins) is list and all(type(row) is dict for row in plugins),
        "AM_host_plugin_inventory",
    )
    compose = [row for row in plugins if row.get("Name") == "compose"]
    require(
        len(compose) == 1
        and type(compose[0].get("Path")) is str
        and Path(compose[0]["Path"]).is_absolute()
        and type(compose[0].get("Version")) is str
        and compose[0]["Version"].removeprefix("v")
        == observations["compose_version"].strip().removeprefix("v"),
        "AM_host_compose_plugin_binding",
    )
    compose_path = Path(compose[0]["Path"]).resolve(strict=True)
    require(compose_path.is_file(), "AM_host_compose_plugin_file")
    tools["compose"] = {
        "path": str(compose_path),
        "sha256": file_hash(compose_path, api.deadline),
        "version": compose[0]["Version"],
    }
    trust_inputs = {}
    for name in (
        "/etc/ssl/openssl.cnf",
        "/usr/lib/ssl/openssl.cnf",
        "/etc/ssl/certs/ca-certificates.crt",
    ):
        path = Path(name)
        require(path.exists() and path.is_file(), "AM_host_default_trust_input")
        trust_inputs[name] = {
            "resolved": str(path.resolve(strict=True)),
            "sha256": file_hash(path.resolve(strict=True), api.deadline),
        }
    executable = Path(sys.executable).resolve(strict=True)
    return {
        "python": sys.version,
        "executable": str(executable),
        "executable_sha256": file_hash(executable, api.deadline),
        "prefix": str(prefix),
        "packages": sorted(versions),
        "distribution_files": sorted(rows, key=lambda row: row["path"]),
        "stdlib": str(stdlib),
        "stdlib_files": sorted(standard, key=lambda row: row["path"]),
        "tools": tools,
        "native": observations,
        "default_trust_inputs": trust_inputs,
        "platform_assumptions": "trusted GitHub runner OS/kernel/daemon and system dynamic libraries; not hostile-host isolation",
    }


_ALERT_HISTORICAL_BUILD_STARTS = (
    (
        39048899349,
        117443160727,
        "6c9f537e89d38f82f8d685150a32e25aee14c6c7",
        "failure",
        _ALERT_Q_BRANCH,
    ),
    (
        39052648330,
        117454182747,
        "2e28d62f4311930f1caeabb5378af3e1d3c1e1a1",
        "failure",
        _ALERT_Q_BRANCH,
    ),
    (
        39059505765,
        117474381581,
        "917854fb7832d7a980c8e6a8ee85940fd2e7724f",
        "failure",
        _ALERT_Q_BRANCH,
    ),
    (
        39067589451,
        117498357173,
        "45409a39ce06804d4cbb5dce6c7dbb61a85167c8",
        "failure",
        _ALERT_Q_BRANCH,
    ),
    (
        39072367157,
        117512436494,
        "bf5b6a9053c9b42727834ffd6966f45e4a493062",
        "failure",
        _ALERT_Q_BRANCH,
    ),
    (
        39077538191,
        117527703920,
        "9d849ab2128aa0a2ff7c065fcc47fdc36a771b1d",
        "failure",
        _ALERT_Q_BRANCH,
    ),
    (
        39084669786,
        117548630619,
        "557b66bf9287feadc68b9916f41f1f471bee9e49",
        "failure",
        _ALERT_Q_BRANCH,
    ),
    (
        39093991413,
        117576475833,
        "91bf3744fcc5f5bbdfdd6e08699d703db46a491f",
        "failure",
        _ALERT_Q_BRANCH,
    ),
    (
        39099358458,
        117592265589,
        "8a00dc7fe7c754c6801dc5c19f1772546ed8696e",
        "failure",
        _ALERT_Q_BRANCH,
    ),
    (
        39143039135,
        117721196331,
        "63455b8a750ef07a1e525078b4e3ce2089eecdde",
        "success",
        _ALERT_Q_BRANCH,
    ),
    (
        40237598500,
        121302388554,
        "04b76f42c09854405df00328ead16b30d701a24f",
        "success",
        _ALERT_RECEIVER_BRANCH,
    ),
)


def _alertmanager_new_source_admission(
    api: GitHubRead, source: str, *, support_only: bool
) -> dict[str, Any]:
    """Admit disjoint real PR2494 qualification C and actual merged-main H runs."""
    from scripts.ci.prometheus_source_image import require, require_native_ancestor

    branch = "main" if os.environ.get("GITHUB_REF") == "refs/heads/main" else _ALERT_Q_BRANCH
    endpoint = "/repos/Katsiarynakavaleuskaya/PulsePlate"
    require(
        type(source) is str
        and re.fullmatch(r"[0-9a-f]{40}", source) is not None
        and source == os.environ.get("GITHUB_SHA")
        and source == os.environ.get("GITHUB_WORKFLOW_SHA")
        and os.environ.get("GITHUB_WORKFLOW_REF")
        == "Katsiarynakavaleuskaya/PulsePlate/.github/workflows/cd.yml@refs/heads/" + branch
        and os.environ.get("GITHUB_REF") == "refs/heads/" + branch
        and os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
        and os.environ.get("GITHUB_REPOSITORY") == "Katsiarynakavaleuskaya/PulsePlate"
        and os.environ.get("GITHUB_REPOSITORY_ID") == "1043311030"
        and os.environ.get("GITHUB_RUN_ATTEMPT") == "1",
        "AM_current_C_H_execution_binding",
    )
    run_text = os.environ.get("GITHUB_RUN_ID", "")
    require(re.fullmatch(r"[1-9][0-9]*", run_text) is not None, "AM_current_run_id")
    run_id = int(run_text)
    workflow = api.json(endpoint + "/actions/workflows/cd.yml")
    run = api.json(endpoint + f"/actions/runs/{run_id}")
    pr = api.json(endpoint + "/pulls/2494")
    require(
        type(workflow) is dict
        and workflow.get("path") == ".github/workflows/cd.yml"
        and type(workflow.get("id")) is int
        and workflow["id"] > 0
        and type(run) is dict
        and type(run.get("id")) is int
        and run["id"] == run_id
        and run.get("workflow_id") == workflow["id"]
        and run.get("head_sha") == source
        and run.get("head_branch") == branch
        and run.get("event") == "workflow_dispatch"
        and run.get("status") == "in_progress"
        and run.get("conclusion") is None
        and type(run.get("run_attempt")) is int
        and run["run_attempt"] == 1
        and run.get("repository", {}).get("id") == 1043311030
        and run.get("head_repository", {}).get("id") == 1043311030
        and type(pr) is dict
        and pr.get("number") == 2494
        and pr.get("head", {}).get("ref") == _ALERT_Q_BRANCH
        and pr["head"].get("repo", {}).get("id") == 1043311030
        and pr.get("base", {}).get("ref") == "main"
        and pr["base"].get("repo", {}).get("id") == 1043311030,
        "AM_current_C_H_API_binding",
    )
    expected_candidate = None
    merge = None
    if branch == "main":
        merge = pr.get("merge_commit_sha")
        require(
            pr.get("merged") is True
            and pr.get("state") == "closed"
            and type(merge) is str
            and re.fullmatch(r"[0-9a-f]{40}", merge) is not None,
            "AM_actual_PR2494_merge",
        )
        main = api.json(endpoint + "/git/ref/heads/main")
        require(
            main.get("ref") == "refs/heads/main"
            and main.get("object", {}).get("type") == "commit"
            and main["object"].get("sha") == source,
            "AM_actual_current_main_H",
        )
        merge = cast(str, merge)
        # Squash merges need merge_commit -> H, never the false premerge C -> H relation.
        require_native_ancestor(api, merge, source)
        if not support_only:
            expected_candidate = _alertmanager_accepted_producer()
            count = pr.get("commits")
            require(type(count) is int and 0 < count <= 250, "AM_complete_PR2494_commit_bound")
            commits = api.pages(endpoint + "/pulls/2494/commits", None, count)
            require(
                sum(row.get("sha") == expected_candidate["source"] for row in commits) == 1,
                "AM_expected_C_in_actual_PR_graph",
            )
            require(
                expected_candidate["source_files"]["scripts/ci/docker_source_artifacts.json"]
                == sha256(DEFAULT_MANIFEST.read_bytes()).hexdigest(),
                "AM_expected_C_current_source_catalog",
            )
            expected_directory = api.private.parent / (api.private.name + "-expected-C")
            expected_directory.mkdir(mode=0o700)
            expected_binding = _alertmanager_authenticated_inputs(
                api,
                expected_candidate["run"],
                expected_candidate["artifact"],
                expected_candidate["source"],
                expected_directory / "candidate.zip",
                kind="candidate",
                upstream_version="0.34.2",
                source_branch=_ALERT_Q_BRANCH,
            )
            require(
                expected_binding["source"] == expected_candidate["source"],
                "AM_expected_C_terminal_producer",
            )
    else:
        require(
            pr.get("merged") is False
            and pr.get("state") == "open"
            and pr["head"].get("sha") == source,
            "AM_actual_open_PR2494_C",
        )
    jobs_endpoint = endpoint + f"/actions/runs/{run_id}/attempts/1/jobs"
    first = api.json(jobs_endpoint + "?per_page=100&page=1")
    jobs = api.pages(jobs_endpoint, "jobs", first["total_count"])
    name = "alertmanager-input-inspection" if support_only else "alertmanager-candidate-build"
    selected = [row for row in jobs if row.get("name") == name]
    require(
        len(selected) == 1
        and type(selected[0].get("id")) is int
        and selected[0]["id"] > 0
        and selected[0].get("run_id") == run_id
        and selected[0].get("head_sha") == source
        and selected[0].get("status") == "in_progress",
        "AM_current_C_H_job",
    )
    starts = []
    if not support_only:
        steps = selected[0].get("steps")
        require(type(steps) is list, "AM_host_install_step_inventory")
        for step_name in (
            "Install isolated AM host tools through the locked owner",
            "Verify isolated AM host import capability before effects",
        ):
            completed = [step for step in steps if step.get("name") == step_name]
            require(
                len(completed) == 1
                and completed[0].get("status") == "completed"
                and completed[0].get("conclusion") == "success",
                "AM_host_install_predecessor",
            )
        history_endpoint = endpoint + "/actions/workflows/cd.yml/runs?event=workflow_dispatch"
        first = api.json(history_endpoint + "&per_page=100&page=1")
        history = api.pages(history_endpoint, "workflow_runs", first["total_count"])
        for prior in history:
            require(type(prior.get("id")) is int and prior["id"] > 0, "AM_prior_build_run_id")
            if prior.get("id") == run_id:
                continue
            jobs_endpoint = endpoint + f'/actions/runs/{prior["id"]}/jobs?filter=all'
            first_jobs = api.json(jobs_endpoint + "&per_page=100&page=1")
            jobs = api.pages(jobs_endpoint, "jobs", first_jobs["total_count"])
            for job in jobs:
                if (
                    job.get("name") != "alertmanager-candidate-build"
                    or job.get("conclusion") == "skipped"
                ):
                    continue
                require(
                    type(job.get("id")) is int
                    and job["id"] > 0
                    and prior.get("status") == job.get("status") == "completed"
                    and type(prior.get("run_attempt")) is int
                    and prior["run_attempt"] == 1
                    and prior.get("event") == "workflow_dispatch"
                    and prior.get("workflow_id") == workflow["id"]
                    and prior.get("repository", {}).get("id") == 1043311030
                    and prior.get("head_repository", {}).get("id") == 1043311030
                    and prior.get("head_branch")
                    in (_ALERT_Q_BRANCH, _ALERT_RECEIVER_BRANCH, "main")
                    and job.get("run_id") == prior["id"]
                    and job.get("head_sha") == prior.get("head_sha")
                    and type(prior.get("conclusion")) is str
                    and job.get("conclusion") == prior["conclusion"],
                    "AM_prior_build_identity_or_concurrent_start",
                )
                starts.append(
                    (
                        prior["id"],
                        job["id"],
                        prior["head_sha"],
                        prior["conclusion"],
                        prior["head_branch"],
                    )
                )
        historical = set(_ALERT_HISTORICAL_BUILD_STARTS) | {
            (
                _ALERT_HISTORICAL_AM11["run"],
                _ALERT_HISTORICAL_AM11["job"],
                _ALERT_HISTORICAL_AM11["source"],
                "success",
                _ALERT_RECEIVER_BRANCH,
            )
        }
        require(
            len(starts) == len(set(starts)) and historical <= set(starts),
            "AM_preserved_complete_historical_starts",
        )
    return {
        "mode": "H" if branch == "main" else "C",
        "source": source,
        "branch": branch,
        "merge_commit": merge,
        "run": run_id,
        "job": selected[0]["id"],
        "prior_builds": sorted(starts),
        "expected_C": expected_candidate,
    }


def _alertmanager_current_manual_admission(
    api: GitHubRead, source: str, *, support_only: bool = False, upstream_version: str = "0.34.1"
) -> dict[str, Any] | None:
    """One AM07 manual build; retain every previous observable build job."""
    from scripts.ci.prometheus_source_image import require

    require(type(support_only) is bool, "AM_current_manual_stage_type")
    require(upstream_version in ("0.34.1", "0.34.2"), "AM_manual_upstream_epoch")
    if upstream_version == "0.34.2":
        return _alertmanager_new_source_admission(api, source, support_only=support_only)
    selected_pr = 2494 if upstream_version == "0.34.2" else 2497
    selected_branch = _ALERT_Q_BRANCH if upstream_version == "0.34.2" else _ALERT_RECEIVER_BRANCH
    endpoint = "/repos/Katsiarynakavaleuskaya/PulsePlate"
    require(
        os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
        and os.environ.get("GITHUB_REPOSITORY") == "Katsiarynakavaleuskaya/PulsePlate"
        and os.environ.get("GITHUB_REPOSITORY_ID") == "1043311030"
        and os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
        and os.environ.get("GITHUB_REF") == "refs/heads/" + selected_branch
        and type(source) is str
        and re.fullmatch(r"[0-9a-f]{40}", source) is not None
        and source == os.environ.get("GITHUB_SHA"),
        "AM_current_build_manual_source",
    )
    run_id = int(os.environ["GITHUB_RUN_ID"])
    workflow = api.json(endpoint + "/actions/workflows/cd.yml")
    run = api.json(endpoint + f"/actions/runs/{run_id}")
    pr = api.json(endpoint + "/pulls/" + str(selected_pr))
    require(
        workflow.get("path") == ".github/workflows/cd.yml"
        and type(workflow.get("id")) is int
        and run.get("id") == run_id
        and run.get("head_sha") == source
        and run.get("head_branch") == selected_branch
        and run.get("workflow_id") == workflow["id"]
        and run.get("event") == "workflow_dispatch"
        and type(run.get("run_attempt")) is int
        and run["run_attempt"] == 1
        and run.get("repository", {}).get("id") == 1043311030
        and run.get("head_repository", {}).get("id") == 1043311030
        and pr.get("number") == selected_pr
        and pr.get("state") == "open"
        and pr.get("head", {}).get("ref") == selected_branch
        and pr["head"].get("sha") == source
        and pr["head"].get("repo", {}).get("id") == 1043311030
        and pr.get("base", {}).get("ref") == "main"
        and pr["base"].get("repo", {}).get("id") == 1043311030,
        "AM_current_build_authenticated_source",
    )
    if not support_only:
        history_endpoint = endpoint + "/actions/workflows/cd.yml/runs?event=workflow_dispatch"
        first = api.json(history_endpoint + "&per_page=100&page=1")
        history = api.pages(history_endpoint, "workflow_runs", first["total_count"])
        expected = _ALERT_HISTORICAL_BUILD_STARTS
        observed = []
        for prior in history:
            if prior["id"] == run_id:
                continue
            jobs_endpoint = endpoint + f'/actions/runs/{prior["id"]}/jobs?filter=all'
            first_jobs = api.json(jobs_endpoint + "&per_page=100&page=1")
            jobs = api.pages(jobs_endpoint, "jobs", first_jobs["total_count"])
            for job in jobs:
                if (
                    job.get("name") != "alertmanager-candidate-build"
                    or job.get("conclusion") == "skipped"
                ):
                    continue
                require(
                    type(prior.get("run_attempt")) is int
                    and prior["run_attempt"] == 1
                    and prior.get("status") == "completed"
                    and prior.get("event") == "workflow_dispatch"
                    and prior.get("workflow_id") == workflow["id"]
                    and prior.get("repository", {}).get("id") == 1043311030
                    and prior.get("head_repository", {}).get("id") == 1043311030
                    and job.get("run_id") == prior["id"]
                    and job.get("head_sha") == prior.get("head_sha")
                    and job.get("status") == "completed"
                    and job.get("conclusion") == prior.get("conclusion"),
                    "AM_current_build_prior_identity",
                )
                observed.append(
                    (
                        prior["id"],
                        job["id"],
                        prior["head_sha"],
                        prior["conclusion"],
                        prior.get("head_branch"),
                    )
                )
        require(sorted(observed) == list(expected), "AM_current_build_complete_spent_history")
    jobs_endpoint = endpoint + f"/actions/runs/{run_id}/attempts/1/jobs"
    first_jobs = api.json(jobs_endpoint + "?per_page=100&page=1")
    jobs = api.pages(jobs_endpoint, "jobs", first_jobs["total_count"])
    job_name = "alertmanager-input-inspection" if support_only else "alertmanager-candidate-build"
    selected = [job for job in jobs if job.get("name") == job_name]
    require(
        len(selected) == 1
        and selected[0].get("run_id") == run_id
        and selected[0].get("head_sha") == source
        and selected[0].get("status") == "in_progress",
        "AM_current_build_job",
    )
    return None


def _alertmanager_bind_current_plan(plan: dict[str, Any], support: dict[str, Any]) -> None:
    """Resolve the one declared-only context operand from the validated current S descriptor."""
    from scripts.ci.prometheus_source_image import BASE, require

    argv = plan["assembly_argv"]
    require(type(argv) is list and argv.count("--build-context") == 1, "AM_current_plan_context")
    position = argv.index("--build-context") + 1
    require(
        position < len(argv)
        and argv[position]
        == BASE + "=oci-layout:///inputs/base-layout@<UNOBSERVED_CURRENT_EXPORT>",
        "AM_current_plan_unobserved_context",
    )
    descriptor = support["base"]["actual_local_OCI_descriptor"]
    require(
        type(descriptor) is dict
        and type(descriptor.get("digest")) is str
        and re.fullmatch(r"sha256:[0-9a-f]{64}", descriptor["digest"]) is not None,
        "AM_current_plan_verified_descriptor",
    )
    argv[position] = BASE + "=oci-layout:///inputs/base-layout@" + descriptor["digest"]


def _alertmanager_clock_float(value: Fraction) -> float:
    """Round an exact clock span or deadline toward the earlier representable time."""
    projected = float(value)
    if projected > value:
        projected = nextafter(projected, float("-inf"))
    if value > 0 and projected <= 0:
        raise TimeoutError("AM positive clock interval cannot be represented")
    return projected


def _alertmanager_current_build(args: argparse.Namespace) -> None:
    """Qualify real C or rebuilt H using one producer clock and incumbent evidence owners."""
    import signal
    from scripts.ci.prometheus_source_image import GitHubRead, fresh_directory, require

    require(
        args.alertmanager_stage == "build"
        and args.artifact == "alertmanager"
        and not args.alertmanager_module_qualify
        and args.manifest == DEFAULT_MANIFEST
        and type(args.source_sha) is str
        and re.fullmatch(r"[0-9a-f]{40}", args.source_sha) is not None
        and args.source_sha == os.environ.get("GITHUB_SHA"),
        "AM_current_build_cli",
    )
    limits = _alertmanager_limits()
    budgets = {}
    for name, ceiling in (
        ("PRODUCER_SECONDS", 8160),
        ("PRODUCER_MATERIAL_SECONDS", 840),
        ("PRODUCER_OTHER_CLEANUP_SECONDS", 600),
        ("PRODUCER_RETENTION_SECONDS", 225),
        ("PRODUCER_FAILURE_SECONDS", 120),
    ):
        raw = os.environ.get("ALERTMANAGER_" + name, "")
        require(
            re.fullmatch(r"[1-9][0-9]{0,4}", raw) is not None and int(raw) == ceiling,
            "AM_producer_explicit_budget_" + name,
        )
        budgets[name] = int(raw)
    require(
        budgets["PRODUCER_SECONDS"]
        >= limits["PREP_SECONDS"]
        + limits["PAIR_SECONDS"]
        + limits["SECURITY_SECONDS"]
        + limits["NATIVE_SECONDS"]
        + limits["NATIVE_CLEANUP_SECONDS"]
        + budgets["PRODUCER_MATERIAL_SECONDS"]
        + budgets["PRODUCER_OTHER_CLEANUP_SECONDS"],
        "AM_producer_complete_phase_budget",
    )
    job_minutes = os.environ.get("ALERTMANAGER_PRODUCER_JOB_MINUTES", "")
    step_minutes = os.environ.get("ALERTMANAGER_PRODUCER_STEP_MINUTES", "")
    require(
        re.fullmatch(r"[1-9][0-9]{0,2}", job_minutes) is not None
        and 180 <= int(job_minutes) <= 360
        and step_minutes == "138"
        and budgets["PRODUCER_SECONDS"] + 120 <= int(step_minutes) * 60,
        "AM_producer_workflow_budget",
    )
    output = args.output_dir.absolute()
    require(
        ".." not in args.output_dir.parts
        and not output.is_symlink()
        and not output.is_relative_to(REPO_ROOT),
        "AM_producer_output_outside_source",
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
    started = Fraction(time.monotonic())
    saved_timer = signal.getitimer(signal.ITIMER_REAL)
    saved_handler = signal.getsignal(signal.SIGALRM)
    capacity = Fraction(budgets["PRODUCER_SECONDS"])
    if saved_timer[0] > 0:
        capacity = min(capacity, Fraction(saved_timer[0]))
    overall_deadline = started + capacity
    work_deadline = (
        overall_deadline
        - budgets["PRODUCER_RETENTION_SECONDS"]
        - budgets["PRODUCER_FAILURE_SECONDS"]
    )
    require(work_deadline > started, "AM_producer_parent_cleanup_reservation")

    def timeout(_signum: int, _frame: object) -> None:
        raise TimeoutError("AM producer shared deadline exhausted")

    charged_seconds = Fraction(0)

    def reserve(seconds: Fraction) -> None:
        now = Fraction(time.monotonic())
        require(now - started - charged_seconds <= 75, "AM_producer_controller_overhead")
        require(now + seconds <= overall_deadline, "AM_producer_remaining_reservation")

    work_remaining = work_deadline - Fraction(time.monotonic())
    require(work_remaining > 0, "AM_producer_parent_cleanup_reservation")
    first_alarm = _alertmanager_clock_float(work_remaining)
    signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, first_alarm)
    result: dict[str, Any] = {
        "source": args.source_sha,
        "compiler_starts": 0,
        "logical_build_starts": 0,
        "status": "HOLD_NO_EXECUTION_OUTCOME",
        "policy_version": "DEP-AM-SEC-1.acceptance.v1",
    }
    material_remaining = Fraction(budgets["PRODUCER_MATERIAL_SECONDS"])
    prep_remaining = Fraction(limits["PREP_SECONDS"])
    # 525 seconds cover concrete cleanup/retention owners; the other75 cover controller overhead.
    cleanup_remaining = Fraction(budgets["PRODUCER_OTHER_CLEANUP_SECONDS"] - 75)
    api: GitHubRead | None = None
    try:
        reserve(
            prep_remaining
            + material_remaining
            + limits["PAIR_SECONDS"]
            + limits["SECURITY_SECONDS"]
            + limits["NATIVE_SECONDS"]
            + limits["NATIVE_CLEANUP_SECONDS"]
            + cleanup_remaining
        )
        phase_started = Fraction(time.monotonic())
        api = GitHubRead(
            output / "private",
            evidence,
            _alertmanager_clock_float(min(work_deadline, phase_started + prep_remaining)),
            limits["CLEANUP_SECONDS"],
        )
        try:
            admission = _alertmanager_current_manual_admission(
                api, args.source_sha, upstream_version="0.34.2"
            )
            require(type(admission) is dict, "AM_producer_admission_observation")
            admission = cast(dict[str, Any], admission)
            result["producer_admission"] = admission
            used = Fraction(time.monotonic()) - phase_started
            prep_remaining -= used
            charged_seconds += used
            require(prep_remaining > 0, "AM_producer_preparation_remaining")
            phase_started = Fraction(time.monotonic())
            api.deadline = _alertmanager_clock_float(
                min(work_deadline, phase_started + material_remaining)
            )
            material = _alertmanager_whole_material(api, args.source_sha)
            result["material"] = material
            host = _alertmanager_host_inputs(api)
            result["host_inputs"] = host
            used = Fraction(time.monotonic()) - phase_started
            material_remaining -= used
            charged_seconds += used
            require(material_remaining > 0, "AM_producer_material_remaining")
            phase_started = Fraction(time.monotonic())
            api.deadline = _alertmanager_clock_float(
                min(work_deadline, phase_started + prep_remaining)
            )
            source_bytes = _alertmanager_source_snapshot(
                api, args.source_sha, upstream_version="0.34.2"
            )
            result["producer_source_files"] = {}
            for path, source_raw in source_bytes.items():
                require(
                    source_raw == (REPO_ROOT / path).read_bytes(),
                    "AM_execution_current_checkout_source",
                )
                target = retained / "producer-source" / path
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                target.write_bytes(source_raw)
                result["producer_source_files"][path] = sha256(source_raw).hexdigest()
            source_contract = {
                path: result["producer_source_files"][path] for path in _ALERT_Q_SOURCE_FILES
            }
            bindings = {}
            for kind in ("qualification", "support"):
                bindings[kind] = _alertmanager_current_inputs(
                    api,
                    args.source_sha,
                    output / (kind + ".zip"),
                    kind=kind,
                    source_files=source_contract,
                    upstream_version="0.34.2",
                    source_branch=admission["branch"],
                )
                supplied = tuple(
                    getattr(args, "alertmanager_" + kind + "_" + key)
                    for key in ("run", "artifact", "source")
                )
                actual = bindings[kind]
                require(
                    all(value is None for value in supplied)
                    or supplied == (actual["run"], actual["artifact"], actual["source"]),
                    "AM_current_build_no_mixed_selector",
                )
            _alertmanager_package_read(api)
            used = Fraction(time.monotonic()) - phase_started
            prep_remaining -= used
            charged_seconds += used
        finally:
            cleanup_started = Fraction(time.monotonic())
            original = sys.exc_info()[1]
            try:
                api.close()
            except BaseException as cleanup_error:
                if original is not None:
                    original.add_note(
                        "AM preparation credential cleanup failed: " + type(cleanup_error).__name__
                    )
                    raise original from None
                raise
        require(
            not api.private.exists() and not api.private.is_symlink(),
            "AM_credentials_removed_before_native",
        )
        charged_seconds += Fraction(time.monotonic()) - cleanup_started
        cleanup_remaining -= limits["CLEANUP_SECONDS"]
        require(prep_remaining > 0, "AM_producer_preparation_remaining")
        reserve(
            prep_remaining
            + material_remaining
            + limits["PAIR_SECONDS"]
            + limits["SECURITY_SECONDS"]
            + limits["NATIVE_SECONDS"]
            + limits["NATIVE_CLEANUP_SECONDS"]
            + cleanup_remaining
        )
        prep_started = Fraction(time.monotonic())
        deadline = _alertmanager_clock_float(min(work_deadline, prep_started + prep_remaining))
        q, supported_binding = bindings["qualification"], bindings["support"]
        inspected = _alertmanager_qualified_payload(output / "qualification.zip", current=True)
        require(
            _alertmanager_upstream_identity(inspected["root_inputs"], current=True) == "0.34.2",
            "AM_current_producer_upstream",
        )
        support = output / "support"
        supported = _alertmanager_support_payload(
            output / "support.zip",
            support,
            qualification=q,
            support_binding=supported_binding,
            qualification_payload=inspected,
        )
        _alertmanager_bind_current_plan(inspected["plan"], supported)
        inspected["plan"]["probe"] = supported["probe"]
        inputs = output / "inputs"
        _alertmanager_materialize(output / "qualification.zip", inputs, deadline)
        result["upstream"] = {"qualification": q, "support": supported_binding}
        result["root_inputs"] = inspected["root_inputs"]
        result["plan"] = inspected["plan"]
        result["UI_file_hashes"] = inspected["plan"]["UI_file_hashes"]
        result["support"] = {
            key: supported[key] for key in ("probe", "scanner", "base_scan", "probe_scan")
        }
        prep_finished: list[float] = []
        _alertmanager_pair(
            inputs,
            support,
            inspected["plan"],
            output / "pair",
            result,
            limits,
            deadline,
            retained=retained,
            base_descriptor=supported["base"]["actual_local_OCI_descriptor"],
            upstream_version="0.34.2",
            preparation_finished=prep_finished,
        )
        charged_seconds += Fraction(time.monotonic()) - prep_started
        require(len(prep_finished) == 1, "AM_pair_preparation_clock")
        prep_remaining -= Fraction(prep_finished[0]) - prep_started
        require(prep_remaining >= 0, "AM_pair_preparation_exhausted")
        cleanup_remaining -= limits["CLEANUP_SECONDS"]
        import shutil

        shutil.copyfile(output / "pair/candidate.oci.tar", retained / "candidate.oci.tar")
        observation = retained / "candidate-observation.json"
        observation.write_text(json.dumps(result, indent=2) + "\n")
        if admission["mode"] == "H":
            expected_C = admission["expected_C"]
            require(
                type(expected_C) is dict and result["graph"] == expected_C["graph"],
                "AM_H_rebuild_expected_C_subject_mismatch",
            )
        reserve(
            material_remaining
            + limits["SECURITY_SECONDS"]
            + limits["NATIVE_SECONDS"]
            + limits["NATIVE_CLEANUP_SECONDS"]
            + cleanup_remaining
        )
        security_started = Fraction(time.monotonic())
        result["security"] = _alertmanager_final_security(
            retained / "candidate.oci.tar",
            result["graph"],
            support,
            output / "security",
            limits,
            build_information=result["build_information"],
            support_report=supported,
            upstream_version="0.34.2",
        )
        charged_seconds += Fraction(time.monotonic()) - security_started
        cleanup_remaining -= limits["CLEANUP_SECONDS"]
        observation.write_text(json.dumps(result, indent=2) + "\n")
        reserve(
            material_remaining
            + limits["NATIVE_SECONDS"]
            + limits["NATIVE_CLEANUP_SECONDS"]
            + cleanup_remaining
        )
        native_started = Fraction(time.monotonic())
        result["native"] = _alertmanager_native_candidate(
            result, observation, output / "native", limits, producer_image=True
        )
        charged_seconds += Fraction(time.monotonic()) - native_started
        reserve(material_remaining + cleanup_remaining)
        rebind_started = Fraction(time.monotonic())
        fresh_directory(retained / "rebind-evidence")
        rebind = GitHubRead(
            output / "rebind-private",
            retained / "rebind-evidence",
            _alertmanager_clock_float(min(work_deadline, rebind_started + material_remaining)),
            limits["CLEANUP_SECONDS"],
        )
        try:
            final_admission = _alertmanager_current_manual_admission(
                rebind, args.source_sha, upstream_version="0.34.2"
            )
            require(final_admission == admission, "AM_producer_final_source_run_drift")
            require(
                _alertmanager_whole_material(rebind, args.source_sha) == material,
                "AM_producer_final_material_drift",
            )
            require(_alertmanager_host_inputs(rebind) == host, "AM_producer_final_host_input_drift")
        finally:
            rebind_work_finished = Fraction(time.monotonic())
            original = sys.exc_info()[1]
            try:
                rebind.close()
            except BaseException as cleanup_error:
                if original is not None:
                    original.add_note(
                        "AM final credential cleanup failed: " + type(cleanup_error).__name__
                    )
                    raise original from None
                raise
        require(
            not rebind.private.exists() and not rebind.private.is_symlink(),
            "AM_final_credentials_removed",
        )
        charged_seconds += Fraction(time.monotonic()) - rebind_started
        material_remaining -= rebind_work_finished - rebind_started
        cleanup_remaining -= limits["CLEANUP_SECONDS"]
        require(material_remaining >= 0, "AM_producer_final_material_budget")
        reserve(cleanup_remaining)
        result["budget"] = {
            "controller_seconds": float(Fraction(time.monotonic()) - started - charged_seconds),
            "maximum_seconds": budgets["PRODUCER_SECONDS"],
            "preparation_seconds_used": float(limits["PREP_SECONDS"] - prep_remaining),
            "material_seconds_used": float(
                budgets["PRODUCER_MATERIAL_SECONDS"] - material_remaining
            ),
            "elapsed_seconds": float(Fraction(time.monotonic()) - started),
        }
        result["status"] = (
            "OBSERVED_MERGED_H_REBUILD_SECURITY_NATIVE"
            if admission["mode"] == "H"
            else "OBSERVED_PR2494_C_SECURITY_NATIVE"
        )
    except BaseException as error:
        result["status"] = "HOLD_NO_EXECUTION_OUTCOME"
        result["failure"] = type(error).__name__ + ":" + str(error)
        raise
    finally:
        original_error = sys.exc_info()[1]
        try:
            now = Fraction(time.monotonic())
            remaining = min(Fraction(budgets["PRODUCER_RETENTION_SECONDS"]), overall_deadline - now)
            require(remaining > 0, "AM_producer_retention_reserve_exhausted")
            retention_deadline = _alertmanager_clock_float(now + remaining)
            signal.setitimer(signal.ITIMER_REAL, _alertmanager_clock_float(remaining))
            path = retained / "candidate-observation.json"
            path.write_text(json.dumps(result, indent=2) + "\n")
            path.chmod(0o600)
            _alertmanager_retain_execution(output, retained)
            _alertmanager_finalize_payload(retained, retention_deadline)
        except BaseException as retention_error:
            if original_error is not None:
                original_error.add_note(
                    "AM raw evidence retention also failed: " + type(retention_error).__name__
                )
                raise original_error from None
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, saved_handler)
            if saved_timer[0] > 0:
                caller_remaining = Fraction(saved_timer[0]) - (Fraction(time.monotonic()) - started)
                if caller_remaining > 0:
                    signal.setitimer(
                        signal.ITIMER_REAL,
                        _alertmanager_clock_float(caller_remaining),
                        saved_timer[1],
                    )
                else:
                    active_error = sys.exc_info()[1]
                    if active_error is not None:
                        active_error.add_note("Caller deadline also expired during AM producer")
                    else:
                        raise TimeoutError("Caller deadline expired during AM producer")


def _alertmanager_execution(args: argparse.Namespace) -> None:
    """Publish only after fresh full H controls, under one original bounded clock."""
    import signal
    from scripts.ci.prometheus_source_image import GitHubRead, fresh_directory, require

    started = Fraction(time.monotonic())
    saved_timer = signal.getitimer(signal.ITIMER_REAL)
    saved_handler = signal.getsignal(signal.SIGALRM)
    require(args.alertmanager_stage == "publish", "AM_new_compiler_not_admitted")
    _alertmanager_accepted_producer()
    limits = _alertmanager_limits()
    budgets: dict[str, int] = {}
    for name, expected in (
        ("PUBLISHER_SECONDS", 10440),
        ("PUBLISHER_REBIND_SECONDS", 600),
        ("PUBLISHER_OTHER_CLEANUP_SECONDS", 600),
        ("PUBLISHER_API_CLEANUP_SECONDS", 120),
        ("PUBLISHER_RETENTION_SECONDS", 225),
        ("PUBLISHER_FAILURE_SECONDS", 120),
    ):
        raw = os.environ.get("ALERTMANAGER_" + name, "")
        require(raw == str(expected), "AM_publisher_explicit_budget_" + name)
        budgets[name] = int(raw)
    native_seconds = limits["NATIVE_SECONDS"] + limits["NATIVE_CLEANUP_SECONDS"]
    require(
        budgets["PUBLISHER_SECONDS"]
        == limits["PREP_SECONDS"]
        + limits["SECURITY_SECONDS"]
        + 2 * native_seconds
        + budgets["PUBLISHER_REBIND_SECONDS"]
        + limits["PUBLICATION_SECONDS"]
        + budgets["PUBLISHER_OTHER_CLEANUP_SECONDS"],
        "AM_publisher_complete_phase_budget",
    )
    job = os.environ.get("ALERTMANAGER_PUBLISHER_JOB_MINUTES", "")
    require(
        re.fullmatch(r"[1-9][0-9]{0,2}", job) is not None
        and 240 <= int(job) <= 360
        and os.environ.get("ALERTMANAGER_PUBLISHER_STEP_MINUTES") == "176",
        "AM_publisher_workflow_budget",
    )
    require(
        args.artifact == "alertmanager"
        and not args.alertmanager_module_qualify
        and args.manifest == DEFAULT_MANIFEST
        and type(args.alertmanager_pr) is int
        and args.alertmanager_pr == 2494
        and os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
        and os.environ.get("GITHUB_REPOSITORY") == "Katsiarynakavaleuskaya/PulsePlate"
        and os.environ.get("GITHUB_REPOSITORY_ID") == "1043311030"
        and os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
        and type(args.source_sha) is str
        and re.fullmatch(r"[0-9a-f]{40}", args.source_sha) is not None
        and args.source_sha == os.environ.get("GITHUB_SHA") == os.environ.get("GITHUB_WORKFLOW_SHA")
        and os.environ.get("GITHUB_REF") == "refs/heads/main"
        and os.environ.get("GITHUB_WORKFLOW_REF")
        == "Katsiarynakavaleuskaya/PulsePlate/.github/workflows/cd.yml@refs/heads/main",
        "AM_exact_manual_execution_source_HOLD",
    )
    output = args.output_dir.absolute()
    require(
        ".." not in args.output_dir.parts
        and not output.is_symlink()
        and not output.is_relative_to(REPO_ROOT),
        "AM_execution_output_path",
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
    capacity = Fraction(budgets["PUBLISHER_SECONDS"])
    if saved_timer[0] > 0:
        capacity = min(capacity, Fraction(saved_timer[0]))
    overall_deadline = started + capacity
    cleanup_remaining = budgets["PUBLISHER_OTHER_CLEANUP_SECONDS"]
    result: dict[str, Any] = {
        "source": args.source_sha,
        "compiler_starts": 0,
        "logical_build_starts": 0,
        "copy_attempts": 0,
        "copy_invocations": 0,
        "package_WRITE": "UNPROVED",
        "status": "HOLD_NO_EXECUTION_OUTCOME",
        "policy_version": "DEP-AM-SEC-1.acceptance.v1",
        "phases": [],
        "cleanup_failures": [],
    }

    def timeout(_signum: int, _frame: object) -> None:
        # A phase alarm must not leave exceptional owned cleanup without the
        # original overall ceiling. This rearms remaining time, never a new clock.
        remaining = overall_deadline - Fraction(time.monotonic())
        if remaining > 0:
            signal.setitimer(signal.ITIMER_REAL, _alertmanager_clock_float(remaining))
        raise TimeoutError("AM publisher original phase/overall deadline exhausted")

    def phase(name: str, seconds: int, downstream: int, *, initial: bool = False) -> float:
        now = Fraction(time.monotonic())
        origin = started if initial else now
        # Compare exact sampled operands before any rounding of absolute deadlines.
        elapsed = origin - started
        remaining = origin + seconds - now
        require(
            remaining > 0 and elapsed + seconds + downstream + cleanup_remaining <= capacity,
            "AM_publisher_downstream_reserve_" + name,
        )
        end = origin + seconds
        signal.setitimer(signal.ITIMER_REAL, _alertmanager_clock_float(remaining))
        result["phases"].append(
            {"phase": name, "started": float(now - started), "deadline": float(end - started)}
        )
        return _alertmanager_clock_float(end)

    def close(api: GitHubRead, name: str, seconds: int) -> None:
        nonlocal cleanup_remaining
        original = sys.exc_info()[1]
        remaining = min(
            Fraction(seconds),
            overall_deadline - Fraction(time.monotonic()) - budgets["PUBLISHER_RETENTION_SECONDS"],
        )
        try:
            require(remaining > 0, "AM_publisher_cleanup_remaining")
            signal.setitimer(signal.ITIMER_REAL, _alertmanager_clock_float(remaining))
            api.close()
            require(
                not api.private.exists() and not api.private.is_symlink(),
                "AM_publisher_private_cleanup_" + name,
            )
        except BaseException as error:
            result["cleanup_failures"].append(
                {"phase": name, "error": type(error).__name__ + ":" + str(error)}
            )
            if original is not None:
                original.add_note("AM " + name + " cleanup also failed: " + type(error).__name__)
                raise original from None
            raise
        finally:
            cleanup_remaining -= seconds

    signal.signal(signal.SIGALRM, timeout)
    try:
        downstream = (
            limits["SECURITY_SECONDS"]
            + 2 * native_seconds
            + budgets["PUBLISHER_REBIND_SECONDS"]
            + limits["PUBLICATION_SECONDS"]
        )
        prep_deadline = phase("preparation", limits["PREP_SECONDS"], downstream, initial=True)
        evidence = retained / "github-read-evidence"
        fresh_directory(evidence)
        api = GitHubRead(output / "private", evidence, prep_deadline, limits["CLEANUP_SECONDS"])
        try:
            prepared = _alertmanager_publish(
                args, api, output, retained, result, limits, phase="prepare"
            )
        finally:
            close(api, "preparation", limits["CLEANUP_SECONDS"])
        result["preparation_credentials_removed"] = True
        # Initial source-proof Native owner has a separate45-second exceptional tail.
        cleanup_remaining -= limits["CLEANUP_SECONDS"]
        cleanup_remaining -= limits["CLEANUP_SECONDS"]
        phase(
            "fresh-security",
            limits["SECURITY_SECONDS"] + limits["CLEANUP_SECONDS"],
            2 * native_seconds
            + budgets["PUBLISHER_REBIND_SECONDS"]
            + limits["PUBLICATION_SECONDS"],
        )
        candidate = prepared["candidate"]
        result["pre_copy_security"] = _alertmanager_final_security(
            prepared["candidate_directory"] / "candidate.oci.tar",
            candidate["graph"],
            prepared["support"],
            output / "security",
            limits,
            build_information=candidate["build_information"],
            support_report=prepared["support_report"],
            upstream_version="0.34.2",
        )
        phase(
            "pre-copy-full-native",
            native_seconds,
            budgets["PUBLISHER_REBIND_SECONDS"] + limits["PUBLICATION_SECONDS"] + native_seconds,
        )
        require(
            candidate.get("producer_admission", {}).get("mode") == "H",
            "AM_prepublication_requires_H_full_scope",
        )
        result["pre_copy_native"] = _alertmanager_native_candidate(
            candidate,
            prepared["candidate_directory"] / "candidate-observation.json",
            output / "pre-native",
            limits,
            producer_image=True,
        )
        require(
            result["pre_copy_native"].get("validation_scope") == "merged_H_selected_image",
            "AM_prepublication_full_selected_controls",
        )
        phase(
            "final-authenticated-rebind",
            budgets["PUBLISHER_REBIND_SECONDS"],
            limits["PUBLICATION_SECONDS"] + native_seconds,
        )
        final_evidence = retained / "final-github-read-evidence"
        fresh_directory(final_evidence)
        # One new, fixed credential-session lifetime covers the separately charged
        # rebind and publication. Neither the old session nor this deadline is renewed.
        session_deadline = min(
            Fraction(time.monotonic())
            + budgets["PUBLISHER_REBIND_SECONDS"]
            + limits["PUBLICATION_SECONDS"],
            overall_deadline - native_seconds - cleanup_remaining,
        )
        final_api = GitHubRead(
            output / "final-private",
            final_evidence,
            _alertmanager_clock_float(session_deadline),
            budgets["PUBLISHER_API_CLEANUP_SECONDS"],
        )
        try:
            _alertmanager_publish(
                args, final_api, output, retained, result, limits, prepared=prepared, phase="rebind"
            )
            phase("publication", limits["PUBLICATION_SECONDS"], native_seconds)
            published = _alertmanager_publish(
                args,
                final_api,
                output,
                retained,
                result,
                limits,
                prepared=prepared,
                phase="publish",
            )
        finally:
            close(final_api, "publication", budgets["PUBLISHER_API_CLEANUP_SECONDS"])
        result["credential_cleanup_observed"] = True
        phase("post-copy-full-native", native_seconds, 0)
        result["native"] = _alertmanager_native_candidate(
            published,
            retained / "pullback-native-input.json",
            output / "native",
            limits,
            producer_image=True,
        )
        require(
            result["native"].get("validation_scope") == "merged_H_selected_image",
            "AM_postpublication_full_selected_controls",
        )
        result["status"] = "OBSERVED_IMMUTABLE_PUBLICATION_PULLBACK_NATIVE"
        result["budget"] = {
            "maximum_seconds": budgets["PUBLISHER_SECONDS"],
            "elapsed_seconds": float(Fraction(time.monotonic()) - started),
        }
    except BaseException as error:
        result["failure"] = type(error).__name__ + ":" + str(error)
        raise
    finally:
        original_error = sys.exc_info()[1]
        try:
            now = Fraction(time.monotonic())
            remaining = min(
                Fraction(budgets["PUBLISHER_RETENTION_SECONDS"]), overall_deadline - now
            )
            require(remaining > 0, "AM_publisher_retention_remaining")
            retention_deadline = _alertmanager_clock_float(now + remaining)
            signal.setitimer(signal.ITIMER_REAL, _alertmanager_clock_float(remaining))
            destination = retained / "candidate-observation.json"
            destination.write_text(json.dumps(result, indent=2) + "\n")
            destination.chmod(0o600)
            _alertmanager_retain_execution(output, retained)
            _alertmanager_finalize_payload(retained, retention_deadline)
        except BaseException as retention_error:
            result["retention_failure"] = (
                type(retention_error).__name__ + ":" + str(retention_error)
            )
            try:
                if (
                    "retention_deadline" in locals()
                    and Fraction(time.monotonic()) < retention_deadline
                ):
                    (retained / "candidate-observation.json").write_text(
                        json.dumps(result, indent=2) + "\n"
                    )
            except BaseException as evidence_error:
                retention_error.add_note(
                    "AM retention-failure evidence also failed: " + type(evidence_error).__name__
                )
            if original_error is not None:
                original_error.add_note(
                    "AM raw evidence retention also failed: " + type(retention_error).__name__
                )
                raise original_error from None
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, saved_handler)
            if saved_timer[0] > 0:
                caller_remaining = Fraction(saved_timer[0]) - (Fraction(time.monotonic()) - started)
                if caller_remaining > 0:
                    signal.setitimer(
                        signal.ITIMER_REAL,
                        _alertmanager_clock_float(caller_remaining),
                        saved_timer[1],
                    )
                elif sys.exc_info()[1] is not None:
                    cast(BaseException, sys.exc_info()[1]).add_note(
                        "Caller deadline also expired during AM publisher"
                    )
                else:
                    raise TimeoutError("Caller deadline expired during AM publisher")


# One finite AM selection/runtime owner. Original A source bytes remain independent.
_ALERT_OLD_RUNTIME_REF = (
    "prom/alertmanager@sha256:84967b9b7ba45e38a9278d3e594305f43d4993c310df3905b51138b816c365f3"
)
_ALERT_OLD_RUNTIME_CONFIG = (
    "sha256:53622b714941158bc20cc92a7571aef515556218eef914b7b8ec5b2a0cb6f607"
)
_ALERT_RUNTIME_LIMITS = {
    "seconds": 90,
    "cleanup_seconds": 8,
    "call_seconds": 8,
    "json_bytes": 1048576,
    "census_bytes": 4096,
}
_ALERT_OLD_POLICY_SHA256 = "3018ef35c8c41c40ae48600893a2876768ba69e2c95fd2cb63a525eb12212493"


def _alertmanager_contract_require(condition: object, diagnostic: str) -> None:
    """Reject an unsupported finite native observation before dependent effects."""
    if not condition:
        raise ValueError(diagnostic)


def _alertmanager_contract_json(raw: bytes) -> dict[str, Any] | list[Any]:
    """Decode one complete bounded native JSON value without duplicate/coercive fields."""

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            _alertmanager_contract_require(key not in result, "AM_contract_duplicate_JSON_key")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise ValueError("AM_contract_nonfinite_JSON:" + value)

    _alertmanager_contract_require(
        0 < len(raw) <= _ALERT_RUNTIME_LIMITS["json_bytes"], "AM_contract_JSON_bound"
    )
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=nonfinite)
    _alertmanager_contract_require(type(value) in (dict, list), "AM_contract_JSON_shape")
    return cast(dict[str, Any] | list[Any], value)


def _alertmanager_contract_file(path: Path) -> bytes:
    """Read one explicit regular data operand; never discover an installed fallback."""
    _alertmanager_contract_require(
        path.is_absolute() and ".." not in path.parts, "AM_contract_absolute_data_path"
    )
    for parent in path.parents:
        _alertmanager_contract_require(
            not parent.is_symlink() and parent.is_dir(), "AM_contract_data_parent"
        )
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        _alertmanager_contract_require(
            stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and 0 <= before.st_size <= _ALERT_RUNTIME_LIMITS["json_bytes"],
            "AM_contract_regular_data",
        )
        raw = os.pread(descriptor, _ALERT_RUNTIME_LIMITS["json_bytes"] + 1, 0)
        after = os.fstat(descriptor)
        _alertmanager_contract_require(
            all(
                getattr(before, key) == getattr(after, key)
                for key in (
                    "st_dev",
                    "st_ino",
                    "st_mode",
                    "st_nlink",
                    "st_size",
                    "st_mtime_ns",
                    "st_ctime_ns",
                )
            )
            and len(raw) == before.st_size,
            "AM_contract_data_drift",
        )
        return raw
    finally:
        os.close(descriptor)


def _alertmanager_contract_fd(
    descriptor: int, maximum: int, status: int, identities: set[tuple[int, int]]
) -> bytes:
    """Read the same held regular readonly capture at offset zero, without consuming EOF."""
    import fcntl

    _alertmanager_contract_require(
        type(descriptor) is int and descriptor >= 0 and type(status) is int and status == 0,
        "AM_contract_native_status",
    )
    before = os.fstat(descriptor)
    identity = (before.st_dev, before.st_ino)
    _alertmanager_contract_require(identity not in identities, "AM_contract_capture_alias")
    identities.add(identity)
    _alertmanager_contract_require(
        stat.S_ISREG(before.st_mode)
        and before.st_nlink == 1
        and before.st_uid == os.getuid()
        and stat.S_IMODE(before.st_mode) == 0o600
        and 0 <= before.st_size <= maximum
        and fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY,
        "AM_contract_readonly_capture",
    )
    raw = os.pread(descriptor, maximum + 1, 0)
    after = os.fstat(descriptor)
    _alertmanager_contract_require(
        all(
            getattr(before, key) == getattr(after, key)
            for key in (
                "st_dev",
                "st_ino",
                "st_mode",
                "st_nlink",
                "st_size",
                "st_mtime_ns",
                "st_ctime_ns",
            )
        )
        and len(raw) == before.st_size
        and len(raw) <= maximum,
        "AM_contract_capture_drift",
    )
    return raw


def _alertmanager_contract_subject(
    *, historical_before: dict[str, Any] | None = None
) -> tuple[str, str]:
    """Return only ROOT's actually accepted subject, never a caller-selected producer."""
    if historical_before is not None:
        _alertmanager_contract_require(
            historical_before == _ALERT_HISTORICAL_AM11, "AM_before_complete_historical_record"
        )
    selected = _ALERT_ACCEPTED_CANDIDATE if historical_before is None else historical_before
    _alertmanager_contract_require(type(selected) is dict, "AM_accepted_producer_UNCONFIGURED_HOLD")
    graph = cast(dict[str, Any], selected)["graph"]
    return (
        "ghcr.io/katsiarynakavaleuskaya/pulseplate@" + graph["manifest"]["digest"],
        graph["config"]["digest"],
    )


def _alertmanager_contract_candidate(
    payload: dict[str, Any] | list[Any],
    compose: Path,
    alert_config: Path,
    ignore: Path,
    expected_environment: str,
    *,
    installed_compose: Path,
    historical_before: dict[str, Any] | None = None,
) -> str:
    """Validate candidate bytes independently of their intended installed mount paths."""
    _alertmanager_contract_require(
        type(payload) is dict and expected_environment in ("staging", "production"),
        "AM_contract_contour",
    )
    payload = cast(dict[str, Any], payload)
    # The trusted caller selects this existing context before inspecting incoming data.
    # Intended AM target leaves may be absent before the first bundle transaction.
    _alertmanager_contract_file(installed_compose)
    installed_directory = installed_compose.parent
    raw = _alertmanager_contract_file(compose).decode("utf-8")
    alert_bytes = _alertmanager_contract_file(alert_config)
    policy = _alertmanager_contract_file(ignore)
    accepted_ref, _ = _alertmanager_contract_subject(historical_before=historical_before)
    image = payload.get("services", {}).get("alertmanager", {}).get("image")
    _alertmanager_contract_require(
        (
            image == accepted_ref
            if historical_before is not None
            else image in (_ALERT_OLD_RUNTIME_REF, accepted_ref)
        ),
        "Alertmanager image identity differs from the admitted platform digest",
    )
    kind = (
        "historical-AM11-before"
        if historical_before is not None
        else "old" if image == _ALERT_OLD_RUNTIME_REF else "accepted"
    )
    _alertmanager_contract_require(
        (kind == "old" and sha256(policy).hexdigest() == _ALERT_OLD_POLICY_SHA256)
        or (kind in ("accepted", "historical-AM11-before") and policy == b"vulnerabilities: []\n"),
        "Alertmanager Trivy policy differs from the admitted complete file",
    )
    services = payload.get("services", {})
    prometheus = services.get("prometheus", {})
    alertmanager = services.get("alertmanager", {})
    app = services.get("app", {})
    networks = payload.get("networks", {})
    if not all(
        isinstance(part, dict) for part in (services, prometheus, alertmanager, app, networks)
    ):
        raise SystemExit("Alertmanager Compose topology is malformed")
    marker = "- PULSEPLATE_ENVIRONMENT=" + expected_environment
    if (
        len(re.findall(r"(?m)^\s*(?:-\s*)?PULSEPLATE_ENVIRONMENT\s*(?::|=)", raw)) != 1
        or raw.count(marker) != 1
    ):
        raise SystemExit("Prometheus environment must be one literal contour value")
    if raw.count(image) != 1:
        raise SystemExit("Raw Alertmanager image must use the admitted platform digest")
    if prometheus.get("environment", {}).get("PULSEPLATE_ENVIRONMENT") != expected_environment:
        raise SystemExit("Rendered Prometheus environment is wrong")
    if alertmanager.get("image") != image or alertmanager.get("platform") != "linux/amd64":
        raise SystemExit("Alertmanager image identity differs from the admitted platform digest")
    if alertmanager.get("profiles") != ["alerting"] or alertmanager.get("ports") not in (None, []):
        raise SystemExit("Alertmanager must be private and profile selected")
    if set(alertmanager.get("networks", {})) != {"alerting", "smtp-egress"}:
        raise SystemExit("Alertmanager networks are not canonical")
    alertmanager_networks = alertmanager["networks"]
    if (
        type(alertmanager_networks["alerting"]) is not dict
        or type(alertmanager_networks["smtp-egress"]) is not dict
        or type(alertmanager_networks["alerting"].get("gw_priority")) is not int
        or type(alertmanager_networks["smtp-egress"].get("gw_priority")) is not int
        or alertmanager_networks["alerting"]["gw_priority"] != 1
        or alertmanager_networks["smtp-egress"]["gw_priority"] != 2
    ):
        raise SystemExit("Alertmanager SMTP egress must be the explicit highest-priority gateway")
    if set(prometheus.get("networks", {})) != {"observability", "alerting"}:
        raise SystemExit("Prometheus networks are not canonical")
    expected_app_networks = (
        {"web", "observability", "database"}
        if expected_environment == "staging"
        else {"web", "observability"}
    )
    if set(app.get("networks", {})) != expected_app_networks:
        raise SystemExit("Product app networks changed or gained SMTP egress")
    if networks.get("alerting", {}).get("internal") is not True:
        raise SystemExit("Alerting network must be internal")
    smtp_egress = networks.get("smtp-egress")
    if (
        type(smtp_egress) is not dict
        or smtp_egress.get("driver") != "bridge"
        or smtp_egress.get("internal") not in (None, False)
        or smtp_egress.get("external") not in (None, False)
    ):
        raise SystemExit("SMTP egress must be a non-internal, non-external bridge")
    commands = alertmanager.get("command", [])
    if commands != [
        "--config.file=/etc/alertmanager/alertmanager.yml",
        "--storage.path=/alertmanager",
        "--cluster.listen-address=",
    ] or alertmanager.get("entrypoint"):
        raise SystemExit("Alertmanager command or disabled cluster listener changed")
    if (
        alertmanager.get("environment")
        or alertmanager.get("env_file")
        or alertmanager.get("extra_hosts")
    ):
        raise SystemExit("Alertmanager gained an unreviewed environment or host mapping")
    if alertmanager.get("read_only") is not True or alertmanager.get("user") != "65534:65534":
        raise SystemExit("Alertmanager runtime isolation changed")
    if alertmanager.get("cap_drop") != ["ALL"] or alertmanager.get("security_opt") != [
        "no-new-privileges:true"
    ]:
        raise SystemExit("Alertmanager capabilities or privilege policy changed")
    if alertmanager.get("tmpfs") != [
        "/alertmanager:size=16m,mode=0700,uid=65534,gid=65534,noexec,nosuid"
    ]:
        raise SystemExit("Alertmanager temporary storage contract changed")
    if alertmanager.get("healthcheck", {}).get("test") != [
        "CMD",
        "/bin/wget",
        "-q",
        "-T",
        "5",
        "-O",
        "/dev/null",
        "http://127.0.0.1:9093/-/ready",
    ]:
        raise SystemExit("Alertmanager readiness command is not the bounded native probe")
    if (
        alertmanager.get("depends_on")
        or alertmanager.get("privileged")
        or alertmanager.get("network_mode")
    ):
        raise SystemExit("Alertmanager gained a dependency or privileged network")
    mounts = alertmanager.get("volumes", [])
    if (
        len(mounts) != 1
        or mounts[0].get("type") != "bind"
        or mounts[0].get("source") != str(installed_directory / "alertmanager/alertmanager.yml")
        or mounts[0].get("target") != "/etc/alertmanager/alertmanager.yml"
        or mounts[0].get("read_only") is not True
    ):
        raise SystemExit("Alertmanager configuration mount changed")
    expected_secret = [
        {"source": "alertmanager_smtp_key", "target": "/run/secrets/alertmanager_smtp_key"}
    ]
    if alertmanager.get("secrets") != expected_secret:
        raise SystemExit("Alertmanager SMTP secret mount changed")
    secret_records = payload.get("secrets", {})
    if type(secret_records) is not dict:
        raise SystemExit("Rendered Compose secrets are malformed")
    smtp_key_path = str(installed_directory / "secrets/alertmanager_smtp_key")
    for service_name, service in services.items():
        if type(service) is not dict:
            raise SystemExit("Rendered Compose service is malformed")
        dependencies = service.get("depends_on", {})
        if type(dependencies) is not dict or any(
            type(edge) is not dict for edge in dependencies.values()
        ):
            raise SystemExit("Rendered Compose dependency map is malformed")
        if service_name != "alertmanager" and "alertmanager" in dependencies:
            raise SystemExit("Another service may not depend on Alertmanager")
        if service_name != "alertmanager":
            if "network_mode" in service:
                raise SystemExit("Another service may not share Alertmanager network namespace")
            if "smtp-egress" in service.get("networks", {}):
                raise SystemExit("SMTP egress leaked to another service")
            for mount in service.get("volumes", []):
                if type(mount) is not dict:
                    raise SystemExit("Rendered Compose service volume is malformed")
                if mount.get("type") == "bind" and (
                    mount.get("source") == smtp_key_path
                    or mount.get("target") == "/run/secrets/alertmanager_smtp_key"
                ):
                    raise SystemExit("SMTP key bind mount leaked to another service")
            for secret in service.get("secrets", []):
                if type(secret) is not dict:
                    raise SystemExit("Rendered Compose service secret is malformed")
                source = secret.get("source")
                source_record = secret_records.get(source, {})
                if (
                    source == "alertmanager_smtp_key"
                    or secret.get("target") == "/run/secrets/alertmanager_smtp_key"
                    or (type(source_record) is dict and source_record.get("file") == smtp_key_path)
                ):
                    raise SystemExit("SMTP secret leaked to another service")
    secret_record = secret_records.get("alertmanager_smtp_key", {})
    if type(secret_record) is not dict or secret_record.get("file") != smtp_key_path:
        raise SystemExit("Alertmanager SMTP secret source changed")
    alert_text = alert_bytes.decode("utf-8")
    for required in (
        "smtp.resend.com:2465",
        "alerts@alerts.pulseplate.app",
        "pulseplate@pm.me",
        "smtp_auth_username: resend",
        "smtp_auth_password_file: /run/secrets/alertmanager_smtp_key",
        "smtp_require_tls: true",
        "smtp_force_implicit_tls: true",
        "group_wait: 30s",
        "group_interval: 5m",
        "repeat_interval: 24h",
        "send_resolved: false",
    ):
        if alert_text.count(required) != 1:
            raise SystemExit("Alertmanager SMTP or route contract changed")
    # Finite complete-byte recognizer for the reviewed SMTP route and sole recipient.
    expected_alertmanager_lines = (
        "global:",
        "  smtp_smarthost: smtp.resend.com:2465",
        "  smtp_from: alerts@alerts.pulseplate.app",
        "  smtp_auth_username: resend",
        "  smtp_auth_password_file: /run/secrets/alertmanager_smtp_key",
        "  smtp_require_tls: true",
        "  smtp_force_implicit_tls: true",
        "",
        "route:",
        "  receiver: pulseplate-email",
        "  group_by: [alertname, environment, alias]",
        "  group_wait: 30s",
        "  group_interval: 5m",
        "  repeat_interval: 24h",
        "",
        "receivers:",
        "  - name: pulseplate-email",
        "    email_configs:",
        "      - to: pulseplate@pm.me",
        "        send_resolved: false",
        "        force_implicit_tls: true",
        "        text: |",
        "          PulsePlate alert {{ .CommonLabels.alertname }} ({{ .CommonLabels.environment }}).",
        "          Open PulsePlate monitoring runbook: https://github.com/Katsiarynakavaleuskaya/PulsePlate/blob/main/docs/deploy/OPERATIONAL_SIGNALS.md#daily-checkpoint",
        "        html: |",
        "          <p>PulsePlate alert {{ .CommonLabels.alertname }} ({{ .CommonLabels.environment }}).</p>",
        '          <p><a href="https://github.com/Katsiarynakavaleuskaya/PulsePlate/blob/main/docs/deploy/OPERATIONAL_SIGNALS.md#daily-checkpoint">Open PulsePlate monitoring runbook</a></p>',
    )
    if (
        len(re.findall(r"(?m)^route:\s*$", alert_text)) != 1
        or len(re.findall(r"(?m)^  receiver: pulseplate-email\s*$", alert_text)) != 1
        or len(re.findall(r"(?m)^receivers:\s*$", alert_text)) != 1
        or len(re.findall(r"(?m)^  - name: pulseplate-email\s*$", alert_text)) != 1
        or len(re.findall(r"(?m)^    email_configs:\s*$", alert_text)) != 1
        or len(re.findall(r"(?m)^      - to: pulseplate@pm[.]me\s*$", alert_text)) != 1
        or len(re.findall(r"(?m)^\s*(?:-\s*)?to\s*:", alert_text)) != 1
        or re.search(r"(?m)^\s*smtp_auth_password\s*:", alert_text)
        or alert_bytes != (chr(10).join(expected_alertmanager_lines) + chr(10)).encode("utf-8")
    ):
        raise SystemExit("Alertmanager route and sole recipient are not the exact reviewed config")
    return kind


def _alertmanager_contract_project(installed: Any, candidate: Any) -> str:
    """Select the census namespace from independent installed native data, with candidate agreement."""
    project = installed.get("name") if type(installed) is dict else None
    _alertmanager_contract_require(
        type(project) is str
        and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,4095}", project) is not None
        and type(candidate) is dict
        and candidate.get("name") == project,
        "AM_contract_installed_project_identity",
    )
    return cast(str, project)


def _alertmanager_contract_census(raw: bytes) -> str:
    """Recognize successful exact empty or one native full-CID output, never normalize failures."""
    text = raw.decode("utf-8")
    _alertmanager_contract_require(
        text == "" or re.fullmatch(r"[0-9a-f]{64}\n?", text) is not None,
        "AM_contract_census_full_ID",
    )
    return text.removesuffix("\n")


def _alertmanager_contract_container(value: Any, cid: str, project: str) -> str:
    """Preserve the existing exact deployed State proposition and bind the next image operand."""
    _alertmanager_contract_require(
        type(value) is list and len(value) == 1 and type(value[0]) is dict,
        "AM_contract_container_cardinality",
    )
    row = value[0]
    labels = row.get("Config", {}).get("Labels") if type(row.get("Config")) is dict else None
    _alertmanager_contract_require(
        row.get("Id") == cid
        and type(labels) is dict
        and labels.get("com.docker.compose.project") == project
        and labels.get("com.docker.compose.service") == "alertmanager",
        "AM_contract_container_identity",
    )
    state = row.get("State")
    _alertmanager_contract_require(
        type(state) is dict
        and all(state.get(key) is False for key in ("Restarting", "Paused", "Dead")),
        "AM_contract_runtime_state",
    )
    if state.get("Status") in ("created", "exited") and state.get("Running") is False:
        return "stopped"
    _alertmanager_contract_require(
        state.get("Status") == "running" and state.get("Running") is True,
        "AM_contract_runtime_state",
    )
    image = row.get("Image")
    _alertmanager_contract_require(
        type(image) is str and re.fullmatch(r"sha256:[0-9a-f]{64}", image) is not None,
        "AM_contract_container_image",
    )
    return cast(str, image)


def _alertmanager_contract_image(value: Any, image_id: str) -> str:
    """Join running container config, canonical RepoDigest and platform in one indivisible case."""
    _alertmanager_contract_require(
        type(value) is list and len(value) == 1 and type(value[0]) is dict,
        "AM_contract_image_cardinality",
    )
    row = value[0]
    refs = row.get("RepoDigests")
    _alertmanager_contract_require(
        row.get("Id") == image_id
        and row.get("Os") == "linux"
        and row.get("Architecture") == "amd64"
        and type(refs) is list
        and len(refs) <= 64
        and all(type(ref) is str for ref in refs)
        and len(set(refs)) == len(refs),
        "AM_contract_runtime_image",
    )
    accepted_ref, accepted_config = _alertmanager_contract_subject()
    if image_id == _ALERT_OLD_RUNTIME_CONFIG and (
        {_ALERT_OLD_RUNTIME_REF, "docker.io/" + _ALERT_OLD_RUNTIME_REF} & set(refs)
    ):
        return "old"
    _alertmanager_contract_require(
        image_id == accepted_config and accepted_ref in refs, "AM_contract_runtime_image"
    )
    _alertmanager_contract_require(
        row.get("RootFS", {}).get("Layers")
        == cast(dict[str, Any], _ALERT_ACCEPTED_CANDIDATE)["graph"]["diff_ids"],
        "AM_contract_runtime_layers",
    )
    return "accepted"


def _alertmanager_contract_main(argv: Sequence[str], *, candidate_fd: int = 0) -> int:
    """Evaluate only the reviewed finite pure ABI before operational imports and effects."""
    options = [value.split("=", 1)[0] for value in argv if value.startswith("--")]
    _alertmanager_contract_require(
        len(options) == len(set(options)), "AM_contract_duplicate_option"
    )
    parser = argparse.ArgumentParser(
        description="Finite AM native contract; final is not overall deployment admission.",
        allow_abbrev=False,
    )
    parser.add_argument("--alertmanager-contract", action="store_true", required=True)
    parser.add_argument(
        "--phase",
        choices=("candidate", "project", "census", "container", "final", "selected-image"),
        required=True,
    )
    for name in ("compose", "installed-compose", "config", "policy"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--contour", choices=("staging", "production"))
    parser.add_argument("--profiles")
    parser.add_argument("--selected-case", choices=("old", "accepted"))
    parser.add_argument("--field", choices=("runtime_ref",))
    for name in ("installed-compose", "census", "container", "image"):
        parser.add_argument("--" + name + "-fd", type=int)
        parser.add_argument("--" + name + "-exit", type=int)
    args = parser.parse_args(argv)
    if args.phase == "selected-image":
        _alertmanager_contract_require(
            args.selected_case is not None
            and all(
                getattr(args, name) is None
                for name in (
                    "compose",
                    "installed_compose",
                    "config",
                    "policy",
                    "contour",
                    "profiles",
                    "installed_compose_fd",
                    "installed_compose_exit",
                    "census_fd",
                    "census_exit",
                    "container_fd",
                    "container_exit",
                    "image_fd",
                    "image_exit",
                )
            ),
            "AM_contract_selected_image_operands",
        )
        if args.field == "runtime_ref":
            # Operand projection only; this result is never image or deployment admission.
            print(
                _ALERT_OLD_RUNTIME_REF
                if args.selected_case == "old"
                else _alertmanager_contract_subject()[0]
            )
            return 0
        raw = sys.stdin.buffer.read(_ALERT_RUNTIME_LIMITS["json_bytes"] + 1)
        expected = (
            _ALERT_OLD_RUNTIME_CONFIG
            if args.selected_case == "old"
            else _alertmanager_contract_subject()[1]
        )
        actual = _alertmanager_contract_image(_alertmanager_contract_json(raw), expected)
        _alertmanager_contract_require(
            actual == args.selected_case, "AM_contract_selected_image_case"
        )
        print(actual)
        return 0
    _alertmanager_contract_require(
        args.selected_case is None
        and args.field is None
        and all(
            getattr(args, name) is not None
            for name in ("compose", "installed_compose", "config", "policy", "contour", "profiles")
        ),
        "AM_contract_candidate_operands",
    )
    identities: set[tuple[int, int]] = set()
    if args.phase == "candidate":
        raw = sys.stdin.buffer.read(_ALERT_RUNTIME_LIMITS["json_bytes"] + 1)
    else:
        raw = _alertmanager_contract_fd(
            candidate_fd, _ALERT_RUNTIME_LIMITS["json_bytes"], 0, identities
        )
    payload = _alertmanager_contract_json(raw)
    kind = _alertmanager_contract_candidate(
        payload,
        args.compose,
        args.config,
        args.policy,
        args.contour,
        installed_compose=args.installed_compose,
    )
    if args.phase == "candidate":
        required: set[str] = set()
    else:
        required = {"installed-compose"}

    def capture(name: str, maximum: int) -> bytes:
        descriptor, status = getattr(args, name.replace("-", "_") + "_fd"), getattr(
            args, name.replace("-", "_") + "_exit"
        )
        _alertmanager_contract_require(
            descriptor is not None and status is not None, "AM_contract_missing_capture:" + name
        )
        return _alertmanager_contract_fd(descriptor, maximum, status, identities)

    project = cid = running = ""
    result = kind
    if args.phase != "candidate":
        project = _alertmanager_contract_project(
            _alertmanager_contract_json(
                capture("installed-compose", _ALERT_RUNTIME_LIMITS["json_bytes"])
            ),
            payload,
        )
        result = project
    if args.phase in ("census", "container", "final"):
        required.add("census")
        cid = _alertmanager_contract_census(
            capture("census", _ALERT_RUNTIME_LIMITS["census_bytes"])
        )
        result = cid or "absent"
    if args.phase in ("container", "final") and cid:
        required.add("container")
        running = _alertmanager_contract_container(
            _alertmanager_contract_json(capture("container", _ALERT_RUNTIME_LIMITS["json_bytes"])),
            cid,
            project,
        )
        result = running
    if args.phase == "container":
        _alertmanager_contract_require(bool(cid), "AM_contract_surplus_phase")
    if args.phase == "final":
        runtime = ""
        if running and running != "stopped":
            required.add("image")
            runtime = _alertmanager_contract_image(
                _alertmanager_contract_json(capture("image", _ALERT_RUNTIME_LIMITS["json_bytes"])),
                running,
            )
        selected = "alerting" in [token.strip() for token in args.profiles.split(",")]
        from datetime import datetime, timezone

        _alertmanager_contract_require(
            not ((selected and kind == "old") or runtime == "old")
            or datetime.now(timezone.utc) < datetime(2026, 10, 21, tzinfo=timezone.utc),
            "Selected or running Alertmanager Trivy exception has expired",
        )
        result = "selected" if selected else "off"
    for name in ("installed-compose", "census", "container", "image"):
        supplied = (
            getattr(args, name.replace("-", "_") + "_fd"),
            getattr(args, name.replace("-", "_") + "_exit"),
        )
        _alertmanager_contract_require(
            (
                all(value is None for value in supplied)
                if name not in required
                else all(value is not None for value in supplied)
            ),
            "AM_contract_conditional_capture:" + name,
        )
    print(result)
    return 0


def _alertmanager_contract_collect(argv: Sequence[str]) -> int:
    """Compose only the admitted native read-only captures under one90/8/8 owner clock."""
    import contextlib
    import selectors
    import signal
    import subprocess  # nosec B404: # stdlib subprocess required by held-FD read-only Docker collector (remove-by: 2026-12-15, ref: PR-2494)

    started = time.monotonic()
    saved_timer = signal.getitimer(signal.ITIMER_REAL)
    deadline = min(
        started + _ALERT_RUNTIME_LIMITS["seconds"],
        started + saved_timer[0] if saved_timer[0] > 0 else float("inf"),
    )
    work_deadline = deadline - _ALERT_RUNTIME_LIMITS["cleanup_seconds"]
    saved_handler = signal.getsignal(signal.SIGALRM)
    primary: BaseException | None = None
    process: subprocess.Popen[bytes] | None = None
    directory: Path | None = None
    captures: dict[str, tuple[int, Path, tuple[Any, ...], str]] = {}
    owned: list[tuple[Path, int, int]] = []
    capture_statuses: dict[str, int] = {}

    def interrupt(signum: int, frame: object) -> None:
        raise TimeoutError("AM_contract_collection_deadline")

    def arm_work() -> float:
        remaining = work_deadline - time.monotonic()
        _alertmanager_contract_require(remaining > 0, "AM_contract_collection_deadline")
        signal.setitimer(signal.ITIMER_REAL, min(_ALERT_RUNTIME_LIMITS["call_seconds"], remaining))
        return min(_ALERT_RUNTIME_LIMITS["call_seconds"], remaining)

    def fingerprint(info: os.stat_result) -> tuple[Any, ...]:
        return tuple(
            getattr(info, name)
            for name in (
                "st_dev",
                "st_ino",
                "st_mode",
                "st_uid",
                "st_nlink",
                "st_size",
                "st_mtime_ns",
                "st_ctime_ns",
            )
        )

    def raw_capture(name: str, command: list[str], maximum: int) -> bytes:
        nonlocal process
        _alertmanager_contract_require(directory is not None, "AM_contract_owned_capture_directory")
        budget = arm_work()
        phase_deadline = min(work_deadline, time.monotonic() + budget)
        path = cast(Path, directory) / name
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        info = os.fstat(fd)
        owned.append((path, info.st_dev, info.st_ino))
        selector = selectors.DefaultSelector()
        diagnostic = bytearray()
        written = 0
        waited = None
        try:
            process = subprocess.Popen(
                command,
                env=native_environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )  # nosec B603: # trusted installed Docker, validated argv, no shell, bounded capture and owned-group cleanup (remove-by: 2026-12-15, ref: PR-2494)
            _alertmanager_contract_require(
                process.stdout is not None and process.stderr is not None,
                "AM_contract_native_capture_streams",
            )
            for stream in (cast(BinaryIO, process.stdout), cast(BinaryIO, process.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ)
            while selector.get_map():
                remaining = phase_deadline - time.monotonic()
                _alertmanager_contract_require(remaining > 0, "AM_contract_capture_timeout:" + name)
                for key, _ in selector.select(remaining):
                    block = os.read(key.fd, 8192)
                    if not block:
                        selector.unregister(key.fileobj)
                    elif key.fileobj is process.stdout:
                        written += len(block)
                        _alertmanager_contract_require(
                            written <= maximum, "AM_contract_capture_oversize:" + name
                        )
                        view = memoryview(block)
                        while view:
                            count = os.write(fd, view)
                            view = view[count:]
                    else:
                        diagnostic.extend(block)
                        _alertmanager_contract_require(
                            len(diagnostic) <= 65536, "AM_contract_diagnostic_bound:" + name
                        )
            remaining = phase_deadline - time.monotonic()
            _alertmanager_contract_require(remaining > 0, "AM_contract_capture_timeout:" + name)
            # WNOWAIT keeps our leader's PID/PGID reserved through owned-group cleanup.
            # Waiting/reaping first would allow a surviving child or a reused PGID.
            waited = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOWAIT)
            _alertmanager_contract_require(
                waited is not None and waited.si_pid == process.pid,
                "AM_contract_native_wait_identity",
            )
            waited = cast(os.waitid_result, waited)
            status = waited.si_status if waited.si_code == os.CLD_EXITED else -waited.si_status
            capture_statuses[name] = status
            _alertmanager_contract_require(
                status == 0, "AM_contract_native_exit:" + name + ":" + str(status)
            )
            os.fsync(fd)
        finally:
            selector.close()
            captured_error = sys.exc_info()[1]
            cleanup_error = None
            if process is not None:
                try:
                    cleanup_until = min(
                        deadline, time.monotonic() + _ALERT_RUNTIME_LIMITS["cleanup_seconds"]
                    )
                    _alertmanager_contract_require(
                        cleanup_until > time.monotonic(), "AM_contract_group_cleanup_deadline"
                    )
                    signal.setitimer(signal.ITIMER_REAL, cleanup_until - time.monotonic())
                    try:
                        _alertmanager_contract_require(
                            os.getpgid(process.pid) == process.pid,
                            "AM_contract_owned_group_identity",
                        )
                    except ProcessLookupError:
                        # Darwin hides an exited leader from getpgid before waitpid;
                        # the successful WNOWAIT observation still reserves its PID.
                        _alertmanager_contract_require(
                            waited is not None, "AM_contract_owned_leader_unknown"
                        )
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except PermissionError:
                        # An exited Darwin leader may leave a zombie-only group
                        # reporting EPERM. Reap only our WNOWAIT-proven leader;
                        # the mandatory absence loop still rejects live members.
                        _alertmanager_contract_require(
                            waited is not None, "AM_contract_group_signal_denied"
                        )
                    process.wait(timeout=max(0.001, cleanup_until - time.monotonic()))
                    while True:
                        try:
                            os.killpg(process.pid, 0)
                        except ProcessLookupError:
                            break
                        _alertmanager_contract_require(
                            time.monotonic() < cleanup_until, "AM_contract_owned_group_survived"
                        )
                        time.sleep(min(0.01, max(0, cleanup_until - time.monotonic())))
                except BaseException as error:
                    cleanup_error = error
                finally:
                    if process.stdout is not None:
                        process.stdout.close()
                    if process.stderr is not None:
                        process.stderr.close()
                    process = None
            os.close(fd)
            if cleanup_error is not None:
                if captured_error is not None:
                    captured_error.add_note(
                        "AM owned group cleanup failed: " + type(cleanup_error).__name__
                    )
                    raise captured_error from None
                raise cleanup_error
        readonly = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        metadata = fingerprint(os.fstat(readonly))
        raw = os.pread(readonly, maximum + 1, 0)
        _alertmanager_contract_require(
            len(raw) <= maximum and fingerprint(os.fstat(readonly)) == metadata,
            "AM_contract_capture_drift",
        )
        captures[name] = (readonly, path, metadata, sha256(raw).hexdigest())
        signal.setitimer(signal.ITIMER_REAL, max(0.001, work_deadline - time.monotonic()))
        return raw

    def verify_captures() -> None:
        for descriptor, path, metadata, digest in captures.values():
            current = os.lstat(path)
            raw = os.pread(descriptor, _ALERT_RUNTIME_LIMITS["json_bytes"] + 1, 0)
            _alertmanager_contract_require(
                fingerprint(current) == metadata
                and fingerprint(os.fstat(descriptor)) == metadata
                and sha256(raw).hexdigest() == digest,
                "AM_contract_capture_drift",
            )

    _alertmanager_contract_require(work_deadline > time.monotonic(), "AM_contract_parent_budget")
    _alertmanager_contract_require(
        hasattr(os, "WNOWAIT") and signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL,
        "AM_contract_unreaped_child_capability",
    )
    signal.signal(signal.SIGALRM, interrupt)
    signal.setitimer(signal.ITIMER_REAL, work_deadline - time.monotonic())
    try:
        options = [value.split("=", 1)[0] for value in argv if value.startswith("--")]
        _alertmanager_contract_require(
            len(options) == len(set(options)), "AM_contract_duplicate_option"
        )
        parser = argparse.ArgumentParser(
            description="Finite read-only AM deployment collection; no activation.",
            allow_abbrev=False,
        )
        parser.add_argument("--alertmanager-contract-collect", action="store_true", required=True)
        for name in ("compose", "installed-compose", "config", "policy", "env-file", "docker"):
            parser.add_argument("--" + name, type=Path, required=True)
        parser.add_argument("--contour", choices=("staging", "production"), required=True)
        parser.add_argument("--profiles", required=True)
        args = parser.parse_args(argv)
        for path in (args.compose, args.installed_compose, args.env_file, args.docker):
            _alertmanager_contract_require(
                path.is_absolute()
                and ".." not in path.parts
                and path.is_file()
                and not path.is_symlink(),
                "AM_contract_installed_source",
            )
        _alertmanager_contract_require(os.access(args.docker, os.X_OK), "AM_contract_native_Docker")
        # These values belong to the incumbent installed caller, never candidate JSON.
        native_environment = dict(os.environ)
        native_environment["COMPOSE_PROFILES"] = args.profiles
        context = tuple(
            native_environment.get(name)
            for name in (
                "DOCKER_HOST",
                "DOCKER_CONTEXT",
                "DOCKER_CONFIG",
                "HOME",
                "COMPOSE_PROJECT_NAME",
            )
        )
        installed_identity = fingerprint(args.installed_compose.stat())
        env_identity = fingerprint(args.env_file.stat())
        directory = Path(tempfile.mkdtemp(prefix="pulseplate-am-admission-"))
        directory.chmod(0o700)
        docker = str(args.docker)

        def compose_command(path: Path) -> list[str]:
            return [
                docker,
                "compose",
                "--env-file",
                str(args.env_file),
                "--project-directory",
                str(args.installed_compose.parent),
                "-f",
                str(path),
                "--profile",
                "*",
                "config",
                "--format",
                "json",
            ]

        candidate = _alertmanager_contract_json(
            raw_capture(
                "candidate", compose_command(args.compose), _ALERT_RUNTIME_LIMITS["json_bytes"]
            )
        )
        installed = _alertmanager_contract_json(
            raw_capture(
                "installed-compose",
                compose_command(args.installed_compose),
                _ALERT_RUNTIME_LIMITS["json_bytes"],
            )
        )
        arm_work()
        selected_case = _alertmanager_contract_candidate(
            candidate,
            args.compose,
            args.config,
            args.policy,
            args.contour,
            installed_compose=args.installed_compose,
        )
        project = _alertmanager_contract_project(installed, candidate)
        verify_captures()
        census = raw_capture(
            "census",
            [
                docker,
                "ps",
                "--all",
                "--no-trunc",
                "--quiet",
                "--filter",
                "label=com.docker.compose.project=" + project,
                "--filter",
                "label=com.docker.compose.service=alertmanager",
            ],
            _ALERT_RUNTIME_LIMITS["census_bytes"],
        )
        arm_work()
        cid = _alertmanager_contract_census(census)
        verify_captures()
        if cid:
            container = _alertmanager_contract_json(
                raw_capture(
                    "container", [docker, "inspect", cid], _ALERT_RUNTIME_LIMITS["json_bytes"]
                )
            )
            arm_work()
            image = _alertmanager_contract_container(container, cid, project)
            verify_captures()
            if image != "stopped":
                raw_capture(
                    "image",
                    [docker, "image", "inspect", image],
                    _ALERT_RUNTIME_LIMITS["json_bytes"],
                )
        _alertmanager_contract_require(
            fingerprint(args.installed_compose.stat()) == installed_identity
            and fingerprint(args.env_file.stat()) == env_identity
            and tuple(
                os.environ.get(name)
                for name in (
                    "DOCKER_HOST",
                    "DOCKER_CONTEXT",
                    "DOCKER_CONFIG",
                    "HOME",
                    "COMPOSE_PROJECT_NAME",
                )
            )
            == context,
            "AM_contract_installed_context_drift",
        )
        verify_captures()
        arm_work()
        final = [
            "--alertmanager-contract",
            "--phase",
            "final",
            "--compose",
            str(args.compose),
            "--installed-compose",
            str(args.installed_compose),
            "--config",
            str(args.config),
            "--policy",
            str(args.policy),
            "--contour",
            args.contour,
            "--profiles=" + args.profiles,
        ]
        for name, (descriptor, _, _, _) in captures.items():
            if name != "candidate":
                final += [
                    "--" + name + "-fd",
                    str(descriptor),
                    "--" + name + "-exit",
                    str(capture_statuses[name]),
                ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            _alertmanager_contract_main(final, candidate_fd=captures["candidate"][0])
        verify_captures()
        answer = output.getvalue()
        _alertmanager_contract_require(
            answer in ("selected\n", "off\n"), "AM_contract_final_result"
        )
    except BaseException as error:
        primary = error
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        remaining = min(_ALERT_RUNTIME_LIMITS["cleanup_seconds"], deadline - time.monotonic())
        cleanup_error: BaseException | None = None
        try:
            _alertmanager_contract_require(remaining > 0, "AM_contract_cleanup_deadline")
            signal.setitimer(signal.ITIMER_REAL, remaining)
            for descriptor, _, _, _ in captures.values():
                os.close(descriptor)
            for path, device, inode in owned:
                metadata = os.lstat(path)
                _alertmanager_contract_require(
                    (metadata.st_dev, metadata.st_ino) == (device, inode),
                    "AM_contract_cleanup_identity",
                )
                path.unlink()
            if directory is not None:
                directory.rmdir()
        except BaseException as error:
            cleanup_error = error
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, saved_handler)
            if saved_timer[0] > 0:
                parent_remaining = saved_timer[0] - (time.monotonic() - started)
                if parent_remaining > 0:
                    signal.setitimer(signal.ITIMER_REAL, parent_remaining, saved_timer[1])
                elif cleanup_error is None:
                    cleanup_error = TimeoutError("Parent timer expired during AM collection")
        if cleanup_error is not None:
            if primary is not None:
                primary.add_note("AM owned capture cleanup failed: " + type(cleanup_error).__name__)
            else:
                raise cleanup_error
    print(answer.strip() + " " + selected_case)
    return 0


def _inspect_alertmanager_inputs(args: argparse.Namespace) -> None:
    """Compiler-free current Q/support observation on the exact admitted source."""
    import shutil
    from scripts.ci.prometheus_source_image import (
        GitHubRead,
        fresh_directory,
        require,
        tree_inventory,
    )

    require(args.alertmanager_stage == "support-inspect", "AM_current_support_stage")
    require(
        type(args.source_sha) is str
        and re.fullmatch(r"[0-9a-f]{40}", args.source_sha) is not None
        and args.source_sha == os.environ.get("GITHUB_SHA"),
        "AM_current_support_source",
    )
    seconds = os.environ.get("ALERTMANAGER_INPUT_INSPECT_SECONDS", "")
    require(
        re.fullmatch(r"[1-9][0-9]{0,2}", seconds) is not None and int(seconds) <= 600,
        "AM_input_inspection_budget",
    )
    output = args.output_dir.absolute()
    require(
        ".." not in args.output_dir.parts and not output.is_relative_to(REPO_ROOT),
        "AM_input_output_path",
    )
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
        admission = _alertmanager_current_manual_admission(
            api, args.source_sha, support_only=True, upstream_version="0.34.2"
        )
        require(type(admission) is dict, "AM_support_source_admission")
        admission = cast(dict[str, Any], admission)
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
        require(checkout == (args.source_sha + "\n").encode(), "AM_execution_actual_checkout_HEAD")
        sources = _alertmanager_source_snapshot(api, args.source_sha, upstream_version="0.34.2")
        require(
            all(raw == (REPO_ROOT / path).read_bytes() for path, raw in sources.items()),
            "AM_execution_current_checkout_source",
        )
        contract = {path: sha256(sources[path]).hexdigest() for path in _ALERT_Q_SOURCE_FILES}
        qualification = _alertmanager_current_inputs(
            api,
            args.source_sha,
            output / "qualification.zip",
            kind="qualification",
            upstream_version="0.34.2",
            source_branch=admission["branch"],
            source_files=contract,
        )
        supplied = (
            args.alertmanager_qualification_run,
            args.alertmanager_qualification_artifact,
            args.alertmanager_qualification_source,
        )
        require(
            all(value is None for value in supplied)
            or supplied
            == (qualification["run"], qualification["artifact"], qualification["source"]),
            "AM_current_support_no_mixed_selector",
        )
        package = _alertmanager_package_read(api)
    finally:
        api.close()
    require(
        not api.private.exists() and not api.private.is_symlink(),
        "AM_credentials_removed_before_native",
    )
    inspected = _alertmanager_qualified_payload(output / "qualification.zip", current=True)
    result = {
        "asset_type": "Alertmanager retained-input inspection",
        "upstream": qualification,
        "github_read_evidence": tree_inventory(evidence, deadline=time.monotonic() + 45),
        "package_read": package,
        "inspection": inspected,
        "policy_version": "DEP-AM-SEC-1.acceptance.v1",
        "authority": "observation_only",
        "consumer_source": args.source_sha,
        "replay": "fresh_output_required_no_Q_or_build_retry",
        "idempotency_key": "AM-inputs-" + args.source_sha + "-" + str(qualification["run"]),
        "compiler_admission": "HOLD_SEPARATE_HUMAN_DECISION",
    }
    destination = output / "input-inspection.json"
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    destination.chmod(0o600)
    try:
        inspected["support"] = _alertmanager_support_observation(
            output / "qualification.zip",
            output,
            qualification_sha256=qualification["zip_sha256"],
            current=True,
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
            "support-inspect",
            "build",
            "candidate-check",
            "security-check",
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
    parser.add_argument("--alertmanager-prepare-only", action="store_true")
    parser.add_argument("--alertmanager-scanner", type=Path)
    parser.add_argument("--alertmanager-cache", type=Path)
    parser.add_argument("--alertmanager-controller-source")
    parser.add_argument("--material-root", type=Path)
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
    if "--alertmanager-contract-collect" in (sys.argv[1:] if argv is None else argv):
        try:
            return _alertmanager_contract_collect(sys.argv[1:] if argv is None else argv)
        except (ValueError, TypeError, KeyError, OSError, UnicodeError, TimeoutError) as error:
            raise SystemExit("AM_contract_HOLD:" + str(error)) from None
    if "--alertmanager-contract" in (sys.argv[1:] if argv is None else argv):
        try:
            return _alertmanager_contract_main(sys.argv[1:] if argv is None else argv)
        except (ValueError, TypeError, KeyError, OSError, UnicodeError) as error:
            raise SystemExit("AM_contract_HOLD:" + str(error)) from None
    args = parse_args(argv)
    if args.alertmanager_prepare_only and args.alertmanager_stage != "candidate-check":
        raise RuntimeError("AM preparation is exclusive to the candidate consumer")
    if (
        args.alertmanager_scanner is not None or args.alertmanager_cache is not None
    ) and args.alertmanager_stage != "security-check":
        raise RuntimeError(
            "AM current scanner operands are exclusive to the current security stage"
        )
    if args.alertmanager_stage == "security-check" and any(
        getattr(args, name) is not None
        for name in (
            "alertmanager_qualification_run",
            "alertmanager_qualification_artifact",
            "alertmanager_qualification_source",
            "alertmanager_support_run",
            "alertmanager_support_artifact",
            "alertmanager_support_source",
            "alertmanager_candidate_run",
            "alertmanager_candidate_artifact",
            "alertmanager_candidate_source",
            "alertmanager_pr",
            "alertmanager_controller_source",
            "material_root",
            "source_sha",
        )
    ):
        raise RuntimeError("AM current scanner does not accept producer or controller overrides")
    if args.alertmanager_stage != "disabled":
        if (
            args.alertmanager_module_qualify
            or args.artifact != "alertmanager"
            or args.manifest != DEFAULT_MANIFEST
        ):
            raise RuntimeError("Alertmanager inspection has no Q/manifest/identity override.")
        if args.alertmanager_stage == "support-inspect":
            _inspect_alertmanager_inputs(args)
        elif args.alertmanager_stage == "build":
            _alertmanager_current_build(args)
        elif args.alertmanager_stage == "candidate-check":
            _alertmanager_consume(args)
        elif args.alertmanager_stage == "security-check":
            _alertmanager_live_security(args)
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
