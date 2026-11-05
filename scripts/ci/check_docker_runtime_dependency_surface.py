#!/usr/bin/env python3
"""Check the production Docker image dependency surface.

RU: Проверяет, что production Docker image не содержит CI/dev tooling или
optional vector/ML packages.
EN: Verifies that the production Docker image excludes CI/dev tooling and
optional vector/ML packages.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import os
import time
import math
from contextlib import contextmanager
from typing import Iterator
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import re
import stat
import subprocess  # nosec B404 # B404: subprocess is required for bounded local Docker inspection; owned call sites individually reviewed (remove-by: 2027-01-31, ref: PR-docker-runtime-slimming)
import sys
from typing import Any, Callable
import uuid

DOCKER_BINARY = shutil.which("docker")
DOCKER_TIMEOUT_SECONDS = 60
_CADDY_REMAINING: Callable[[float], float] | None = None
DEFAULT_BLOCKED_PREFIXES: tuple[str, ...] = (
    "bandit",
    "coverage",
    "cuda-",
    "diff-cover",
    "faker",
    "huggingface-hub",
    "hypothesis",
    "mypy",
    "nvidia-",
    "pgvector",
    "pip-audit",
    "pre-commit",
    "pytest",
    "pytest-",
    "ruff",
    "scikit-learn",
    "scipy",
    "sentence-transformers",
    "tokenizers",
    "torch",
    "transformers",
    "triton",
)


@dataclass(frozen=True)
class DependencySurfaceResult:
    """Normalized Docker runtime dependency-surface report."""

    image: str
    installed_count: int
    blocked: tuple[str, ...]
    passed: bool
    installed_debian_count: int = 0
    blocked_debian_packages: tuple[str, ...] = ()


def normalize_package_name(name: str) -> str:
    """Normalize package names to pip-comparison form."""

    return name.strip().lower().replace("_", "-")


def normalize_debian_package_name(name: str) -> str:
    """Normalize Debian package names and drop optional architecture qualifiers."""

    return normalize_package_name(name).split(":", 1)[0]


def parse_installed_packages(payload: str) -> tuple[str, ...]:
    """Parse the image-side JSON package inventory."""

    data = json.loads(payload)
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError("Image package inventory must be a JSON list of strings.")
    return tuple(sorted({normalize_package_name(item) for item in data}))


def parse_installed_debian_packages(payload: str) -> dict[str, str]:
    """Parse the image-side dpkg package inventory."""

    installed: dict[str, str] = {}
    for line in payload.splitlines():
        if not line.strip():
            continue
        try:
            status, name, version = line.split("\t", 2)
        except ValueError as exc:
            raise ValueError(
                "Debian package inventory must be '<status>\\t<name>\\t<version>' lines."
            ) from exc
        if not status.startswith("ii"):
            continue
        normalized = normalize_debian_package_name(name)
        if not normalized or not version.strip():
            raise ValueError("Debian package inventory contains an empty name or version.")
        installed[normalized] = version.strip()
    return dict(sorted(installed.items()))


def find_blocked_packages(
    installed_packages: tuple[str, ...], blocked_prefixes: tuple[str, ...]
) -> tuple[str, ...]:
    """Return installed packages matching blocked runtime prefixes."""

    normalized_prefixes = tuple(normalize_package_name(item) for item in blocked_prefixes)
    blocked = [package for package in installed_packages if package.startswith(normalized_prefixes)]
    return tuple(sorted(set(blocked)))


def find_blocked_debian_packages(
    installed_packages: dict[str, str],
    blocked_packages: tuple[str, ...],
    blocked_prefixes: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Return Debian packages that must not exist in the production image."""

    normalized_blocked = {normalize_debian_package_name(item) for item in blocked_packages}
    normalized_prefixes = tuple(
        normalize_debian_package_name(item) for item in blocked_prefixes if item.strip()
    )
    blocked = [
        f"{name}={version}"
        for name, version in installed_packages.items()
        if name in normalized_blocked
        or (normalized_prefixes and name.startswith(normalized_prefixes))
    ]
    return tuple(sorted(blocked))


def _run_docker(
    args: list[str], *, preserve_newlines: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run Docker with a resolved binary path and fixed argv."""

    if DOCKER_BINARY is None:
        raise RuntimeError(
            "docker binary is not available on PATH; run this check in a Docker-enabled "
            "environment."
        )
    try:
        result = subprocess.run(  # nosec B603 # B603: resolved Docker for fixed run inventory or image inspect calls; 60-second timeout and no shell; timeout and failure controls reviewed (remove-by: 2027-01-31, ref: PR-docker-runtime-slimming)
            [DOCKER_BINARY, *args],
            check=True,
            capture_output=True,
            text=not preserve_newlines,
            timeout=(
                _CADDY_REMAINING(DOCKER_TIMEOUT_SECONDS)
                if _CADDY_REMAINING
                else DOCKER_TIMEOUT_SECONDS
            ),
        )
        if preserve_newlines:
            try:
                return subprocess.CompletedProcess(
                    result.args,
                    result.returncode,
                    stdout=result.stdout.decode("utf-8"),
                    stderr=result.stderr.decode("utf-8"),
                )
            except UnicodeDecodeError:
                failure = RuntimeError("Docker output is not valid UTF-8")
                for channel, output in (("stdout", result.stdout), ("stderr", result.stderr)):
                    failure.add_note(
                        "Docker "
                        + channel
                        + " bytes="
                        + str(len(output))
                        + " sha256="
                        + hashlib.sha256(output).hexdigest()
                    )
                raise failure from None
        return result
    except subprocess.TimeoutExpired as exc:
        if preserve_newlines:
            failure = RuntimeError(
                f"docker command timed out after {DOCKER_TIMEOUT_SECONDS}s: {' '.join(args)}"
            )
            for channel, output in (("stdout", exc.stdout), ("stderr", exc.stderr)):
                if isinstance(output, bytes):
                    failure.add_note(
                        "Docker "
                        + channel
                        + " bytes="
                        + str(len(output))
                        + " sha256="
                        + hashlib.sha256(output).hexdigest()
                    )
                else:
                    failure.add_note("Docker " + channel + " capture unavailable")
            raise failure from None
        raise RuntimeError(
            f"docker command timed out after {DOCKER_TIMEOUT_SECONDS}s: {' '.join(args)}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        if preserve_newlines:
            failure = RuntimeError(
                f"docker command failed (returncode={exc.returncode}, args={' '.join(args)})"
            )
            for channel, output in (("stdout", exc.stdout), ("stderr", exc.stderr)):
                if isinstance(output, bytes):
                    failure.add_note(
                        "Docker "
                        + channel
                        + " bytes="
                        + str(len(output))
                        + " sha256="
                        + hashlib.sha256(output).hexdigest()
                    )
                else:
                    failure.add_note("Docker " + channel + " capture unavailable")
            raise failure from None
        stderr = (exc.stderr or "").strip()
        stderr_suffix = f", stderr={stderr}" if stderr else ""
        raise RuntimeError(
            "docker command failed "
            f"(returncode={exc.returncode}, args={' '.join(args)}{stderr_suffix})"
        ) from exc


def inspect_image_packages(image: str) -> tuple[str, ...]:
    """Inspect installed package names inside the target image."""

    snippet = (
        "import importlib.metadata as m, json; "
        "print(json.dumps(sorted(d.metadata['Name'] for d in m.distributions())))"
    )
    result = _run_docker(["run", "--rm", image, "python", "-c", snippet])
    return parse_installed_packages(result.stdout)


def inspect_image_debian_packages(image: str) -> dict[str, str]:
    """Inspect installed Debian package names and versions inside the target image."""

    snippet = "dpkg-query -W -f='${db:Status-Abbrev}\\t${Package}\\t${Version}\\n'"
    result = _run_docker(["run", "--rm", image, "sh", "-c", snippet])
    return parse_installed_debian_packages(result.stdout)


def build_result(
    image: str,
    blocked_prefixes: tuple[str, ...],
    blocked_debian_packages: tuple[str, ...] = (),
    blocked_debian_prefixes: tuple[str, ...] = (),
) -> DependencySurfaceResult:
    """Build the normalized dependency-surface result for an image."""

    installed = inspect_image_packages(image)
    blocked = find_blocked_packages(installed, blocked_prefixes)
    installed_debian = (
        inspect_image_debian_packages(image)
        if blocked_debian_packages or blocked_debian_prefixes
        else {}
    )
    blocked_debian = find_blocked_debian_packages(
        installed_debian,
        blocked_debian_packages,
        blocked_debian_prefixes,
    )
    return DependencySurfaceResult(
        image=image,
        installed_count=len(installed),
        blocked=blocked,
        passed=not blocked and not blocked_debian,
        installed_debian_count=len(installed_debian),
        blocked_debian_packages=blocked_debian,
    )


def _read_trivy_image_report(image: str, report_path: Path) -> dict[str, Any]:
    """Bind the native Trivy v2 image report to this local Docker image.

    This checks the finite image/report projection, not the entire Trivy schema
    or vulnerability semantics. Trivy owns scanning and JSON-to-SARIF conversion.
    """
    if report_path.is_symlink():
        raise ValueError("Trivy image report must not be a symlink.")
    metadata = report_path.stat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size == 0:
        raise ValueError("Trivy image report must be a nonempty regular file.")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (
        not isinstance(report, dict)
        or type(report.get("SchemaVersion")) is not int
        or report["SchemaVersion"] != 2
    ):
        raise ValueError("Expected a native Trivy schema version 2 report.")
    if report.get("ArtifactType") != "container_image" or report.get("ArtifactName") != image:
        raise ValueError("Trivy report does not describe the selected container image.")
    image_metadata = report.get("Metadata")
    if not isinstance(image_metadata, dict):
        raise ValueError("Trivy image metadata is missing.")
    image_id = _run_docker(["image", "inspect", "--format", "{{.Id}}", image]).stdout.strip()
    if not image_id.startswith("sha256:") or image_metadata.get("ImageID") != image_id:
        raise ValueError("Trivy report image ID differs from the inspected Docker image.")
    results = report.get("Results")
    if not isinstance(results, list) or not results:
        raise ValueError("Trivy image report has no package scan results.")
    has_os_result = False
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("Trivy scan result must be an object.")
        if not all(
            isinstance(result.get(key), str) and result[key] for key in ("Target", "Class", "Type")
        ):
            raise ValueError("Trivy scan result identity is missing.")
        has_os_result = has_os_result or result["Class"] == "os-pkgs"
        if "Vulnerabilities" in result:
            findings = result["Vulnerabilities"]
            if not isinstance(findings, list) or not all(isinstance(v, dict) for v in findings):
                raise ValueError("Trivy vulnerability results must be an array of objects.")
    if not has_os_result:
        raise ValueError("Trivy production image report is missing its OS package scan.")

    return report


def validate_trivy_image_report(image: str, report_path: Path) -> None:
    """Validate the structural image projection only; retain the public None contract."""
    _read_trivy_image_report(image, report_path)


# The original module checksum remains pre-replacement source evidence.
CADDY_SOURCE_MODULES = {
    "github.com/go-jose/go-jose/v3": ("v3.0.5", "h1:BLLJWbC4nMZOfuPVxoZIxeYsn6Nl2r1fITaJ78UQlVQ="),
    "github.com/go-jose/go-jose/v4": ("v4.1.6", "h1:sNRkftxFJxwsILiQukqp5z83QBSmntVwmgRY7AqBDO4="),
}
CADDY_D_CONFIG = (
    b'{"admin":{"disabled":true,"config":{"persist":false}},"apps":{"http":{"servers":'
    b'{"ci":{"listen":["127.0.0.1:18080"],"automatic_https":{"disable":true},'
    b'"routes":[{"handle":[{"handler":"static_response","body":'
    b'"pulseplate-caddy-D\\nHOME={env.HOME}\\nTMPDIR={env.TMPDIR}\\n"}]}]}}}}}\n'
)
CADDY_PATCHED_ROOT = "/opt/go-jose-v3.0.5-patched"
CADDY_BUILD_EVIDENCE_PATH = "/usr/share/pulseplate-caddy-build"
CADDY_BUILD_MEMBERS = frozenset(
    {
        "patch-tool.txt",
        "inputs.sha256",
        "original-tree.sha256",
        "copied-tree.sha256",
        "patched-tree.sha256",
        "post-unit-tree.sha256",
        "post-build-tree.sha256",
        "original-post-build-tree.sha256",
        "jose-tests.jsonl",
        "compat-tests.jsonl",
        "modules.json",
        "module-graph.txt",
        "import-graph.txt",
        "build-module.sha256",
        "build-info.txt",
        "binary.sha256",
    }
)
CADDY_ORIGINAL_TREE = "1c0d532bafdf2a7de4fea465082117f97e6e8bcf31e1704203f838a873901ce1"
CADDY_PATCHED_TREE = "e71a63d7a08abecf4c3f2f72c41c1f469c097d853eafe854fdb6e782a70e1065"
CADDY_PATCH_SHA256 = "f0e1b6f4791089dfebbc9a742533af650268e87bffec09847190e59da04aad27"
CADDY_COMPAT_SHA256 = "628d25c62a2141fb35bea13003483a22f277b3b2c9ba319ff5a53b7b591e7de6"
CADDY_IMPORT_CHAIN = (
    "github.com/caddyserver/caddy/v2/cmd/caddy",
    "github.com/caddyserver/caddy/v2/modules/standard",
    "github.com/caddyserver/caddy/v2/modules/caddypki",
    "github.com/smallstep/certificates/authority",
    "go.step.sm/crypto/jose",
    "github.com/go-jose/go-jose/v3",
)


def caddy_ci_source_inventory(root: Path, paths: list[str]) -> dict[str, dict[str, object]]:
    """Hash the caller-enumerated complete tracked build context and fixed CI owners."""
    fixed = {
        ".github/workflows/frontend-ci.yml",
        "deploy/Caddyfile",
        "deploy/Caddyfile.production",
        "scripts/ci/check_docker_runtime_dependency_surface.py",
        "scripts/ci/prometheus_source_image.py",
        "scripts/ci/check_trivy_ignore_policy_expiry.py",
        "trivy/ignore-policy.rego",
    }
    selected = set(paths)
    if (
        len(selected) != len(paths)
        or not fixed <= selected
        or not {
            "frontend/Dockerfile.caddy-spa",
            "frontend/package-lock.json",
            "frontend/.dockerignore",
        }
        <= selected
        or any(not (name.startswith("frontend/") or name in fixed) for name in selected)
    ):
        raise ValueError("Caddy relevant source inventory is incomplete or ambiguous")
    inventory: dict[str, dict[str, object]] = {}
    for name in sorted(selected):
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or relative.as_posix() != name
            or ".." in relative.parts
            or "\\" in name
        ):
            raise ValueError("Caddy relevant source path alias")
        path = root / name
        for parent in path.parents:
            if parent == root:
                break
            if parent.is_symlink() or not parent.is_dir():
                raise ValueError("Caddy relevant source parent alias")
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
            raise ValueError("Caddy relevant source is not a regular file")
        raw = path.read_bytes()
        inventory[name] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "mode": stat.S_IMODE(path.stat().st_mode),
        }
    return inventory


_CADDY_SYNTHETIC_ENVIRONMENT = (
    "HOME=/run/pulseplate-caddy-tmp",
    "TMPDIR=/run/pulseplate-caddy-tmp",
    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "CADDY_VERSION=v2.11.4",
    "XDG_CONFIG_HOME=/config",
    "XDG_DATA_HOME=/data",
)


def _is_caddy_synthetic_environment(value: object) -> bool:
    """Recognize all six reviewed unique bindings, independent of Docker's list order."""
    return (
        type(value) is list
        and len(value) == 6
        and all(type(entry) is str for entry in value)
        and Counter(value) == Counter(_CADDY_SYNTHETIC_ENVIRONMENT)
    )


def observe_caddy_ci_runtime(image: str, directory: Path) -> dict[str, object]:
    """Bind two serving-process values and isolated storage, never a deployed service."""
    global _CADDY_REMAINING
    if re.fullmatch(r"sha256:[0-9a-f]{64}", image) is None:
        raise ValueError("Caddy runtime requires an immutable local image ID")
    config = directory / "loaded-ci-config.json"
    with config.open("xb") as stream:
        stream.write(CADDY_D_CONFIG)
    config.chmod(0o444)
    name = "pulseplate-caddy-D-" + uuid.uuid4().hex
    arguments = [
        "create",
        "--pull",
        "never",
        "--name",
        name,
        "--label",
        "pulseplate.caddy-D=" + name,
        "--network",
        "none",
        "--read-only",
        "--user",
        "65532:65532",
        "--cap-drop",
        "ALL",
        "--cap-add",
        "NET_BIND_SERVICE",
        "--security-opt",
        "no-new-privileges",
        "--cpus",
        "1",
        "--memory",
        "256m",
        "--pids-limit",
        "64",
        "--tmpfs",
        "/run/pulseplate-caddy-tmp:size=8m,uid=65532,gid=65532,mode=0700",
        "--tmpfs",
        "/data:size=8m,uid=65532,gid=65532,mode=0700",
        "--tmpfs",
        "/config:size=8m,uid=65532,gid=65532,mode=0700",
        "--mount",
        f"type=bind,source={config.resolve()},target=/ci.json,readonly",
        "--env",
        "HOME=/run/pulseplate-caddy-tmp",
        "--env",
        "TMPDIR=/run/pulseplate-caddy-tmp",
        "--entrypoint",
        "/usr/bin/caddy",
        image,
        "run",
        "--config",
        "/ci.json",
    ]
    created = False
    diagnostic_errors: list[tuple[str, Exception]] = []
    primary_error: BaseException | None = None
    evidence: dict[str, object] = {"image_config_id": image, "argv": arguments}
    phase = "create"
    observed_channels: tuple[tuple[str, str], ...] = ()
    outer_remaining = _CADDY_REMAINING
    if outer_remaining is not None:
        work_deadline = (
            time.monotonic() + outer_remaining(float("inf")) - 2 * DOCKER_TIMEOUT_SECONDS
        )

        def work_remaining(cap: float) -> float:
            value = min(cap, work_deadline - time.monotonic())
            if value <= 0:
                raise ValueError("Caddy runtime work exhausted reserved cleanup budget")
            return value

        _CADDY_REMAINING = work_remaining
    try:
        _run_docker(arguments)
        created = True
        # Keep the closed synthetic input gate; do not model all environment
        # transformations performed inside the serving process.
        phase = "pre-start-inspect"
        inspection = _run_docker(["inspect", name])
        observed_channels = (("inspect.stdout", inspection.stdout),)
        prepared = json.loads(inspection.stdout)[0]
        prepared_config = prepared["Config"]
        if (
            re.fullmatch(r"[0-9a-f]{64}", prepared["Id"]) is None
            or prepared["Image"] != image
            or prepared["Path"] != "/usr/bin/caddy"
            or prepared["Args"] != ["run", "--config", "/ci.json"]
            or prepared["State"]["Status"] != "created"
            or prepared["State"]["Running"]
            or prepared["RestartCount"] != 0
            or prepared_config["Labels"].get("pulseplate.caddy-D") != name
            or prepared_config["Tty"] is not False
            or prepared_config["WorkingDir"] != "/srv"
            or prepared_config["Hostname"] != prepared["Id"][:12]
            or not _is_caddy_synthetic_environment(prepared_config.get("Env"))
        ):
            raise ValueError("Caddy pre-start synthetic environment binding differs")
        phase, observed_channels = "start", ()
        _run_docker(["start", name])
        # The same request proves readiness and only the two required getenv values.
        # Literal placeholders stay in CADDY_D_CONFIG; expected values stay here.
        expected_response = (
            "pulseplate-caddy-D\n"
            "HOME=/run/pulseplate-caddy-tmp\n"
            "TMPDIR=/run/pulseplate-caddy-tmp\n"
        )
        phase, observed_channels = "readiness-private-environment", ()
        probe = _run_docker(
            [
                "exec",
                name,
                "/bin/busybox",
                "sh",
                "-c",
                "for i in 1 2 3 4 5; do "
                "wget -q -T 1 -O - http://127.0.0.1:18080/ && exit 0; "
                "sleep 1; done; exit 1",
            ],
            preserve_newlines=True,
        )
        observed_channels = (("response.stdout", probe.stdout), ("response.stderr", probe.stderr))
        if probe.stdout != expected_response:
            raise ValueError("Caddy loaded configuration/private environment response differs")
        phase, observed_channels = "config-readback", ()
        config_result = _run_docker(
            ["exec", name, "/bin/busybox", "cat", "/ci.json"], preserve_newlines=True
        )
        loaded = config_result.stdout.encode()
        observed_channels = (("config.stdout", config_result.stdout),)
        phase = "process-command"
        command = _run_docker(
            ["exec", name, "/bin/busybox", "cat", "/proc/1/cmdline"], preserve_newlines=True
        ).stdout
        observed_channels += (("command.stdout", command),)
        if (
            loaded != CADDY_D_CONFIG
            or command != "/usr/bin/caddy\x00run\x00--config\x00/ci.json\x00"
        ):
            mismatch = ValueError("Caddy actual process/config binding differs")
            mismatch.add_note(
                "Caddy config_equal="
                + str(loaded == CADDY_D_CONFIG)
                + " command_equal="
                + str(command == "/usr/bin/caddy\x00run\x00--config\x00/ci.json\x00")
            )
            raise mismatch
        sockets = {}
        for kind in ("tcp", "tcp6", "udp", "udp6"):
            phase, observed_channels = "sockets-" + kind, ()
            raw = _run_docker(["exec", name, "/bin/busybox", "cat", "/proc/net/" + kind]).stdout
            observed_channels = (("sockets.stdout", raw),)
            rows = [line.split() for line in raw.splitlines()[1:] if line.strip()]
            if any(len(row) < 4 for row in rows):
                raise ValueError("Caddy native socket inventory malformed")
            sockets[kind] = raw
            listening = [row[1] for row in rows if kind.startswith("udp") or row[3] == "0A"]
            if listening != (["0100007F:46A0"] if kind == "tcp" else []):
                raise ValueError("Caddy native listener/admin boundary differs")
        phase, observed_channels = "runtime-inspect", ()
        inspection = _run_docker(["inspect", name])
        observed_channels = (("inspect.stdout", inspection.stdout),)
        inspected = json.loads(inspection.stdout)[0]
        if not _is_caddy_synthetic_environment(inspected["Config"].get("Env")):
            raise ValueError("Caddy synthetic environment changed after startup")
        for channel, output in (("stdout", inspection.stdout), ("stderr", inspection.stderr)):
            try:
                with (directory / ("container-inspect." + channel)).open(
                    "x", encoding="utf-8"
                ) as inspect_stream:
                    inspect_stream.write(output)
            except Exception as capture_error:
                diagnostic_errors.append(("container-inspect." + channel, capture_error))
        host, native_config, state = (
            inspected["HostConfig"],
            inspected["Config"],
            inspected["State"],
        )
        phase = "isolation-state"
        if (
            inspected["Image"] != image
            or inspected["Id"] != prepared["Id"]
            or native_config["Tty"] is not False
            or type(state.get("Pid")) is not int
            or state["Pid"] <= 0
            or not isinstance(state.get("StartedAt"), str)
            or not state["StartedAt"]
            or state["StartedAt"].startswith("0001-")
            or not state["Running"]
            or state["Restarting"]
            or state["OOMKilled"]
            or inspected["RestartCount"] != 0
            or host["NetworkMode"] != "none"
            or not host["ReadonlyRootfs"]
            or host["PortBindings"]
            or host["Privileged"]
            or host["CapAdd"] != ["CAP_NET_BIND_SERVICE"]
            or host["CapDrop"] != ["ALL"]
            or native_config["User"] != "65532:65532"
            or native_config["Labels"].get("pulseplate.caddy-D") != name
        ):
            raise ValueError("Caddy native isolation/state differs")
        phase = "private-tmpfs"
        # Docker's legacy --tmpfs entries live in HostConfig.Tmpfs, not Mounts.
        if host.get("Tmpfs") != {
            "/run/pulseplate-caddy-tmp": "size=8m,uid=65532,gid=65532,mode=0700",
            "/data": "size=8m,uid=65532,gid=65532,mode=0700",
            "/config": "size=8m,uid=65532,gid=65532,mode=0700",
        }:
            raise ValueError("Caddy native tmpfs configuration differs")
        phase = "configuration-mount"
        mounts = inspected["Mounts"]
        if (
            not isinstance(mounts, list)
            or len(mounts) != 1
            or not isinstance(mounts[0], dict)
            or mounts[0].get("Type") != "bind"
            or mounts[0].get("Destination") != "/ci.json"
            or mounts[0].get("Source") != str(config.resolve())
            or mounts[0].get("RW") is not False
        ):
            raise ValueError("Caddy immutable configuration mount differs")
        phase = "configured-private-environment"
        private_environment = ["HOME=/run/pulseplate-caddy-tmp", "TMPDIR=/run/pulseplate-caddy-tmp"]
        configured_environment = native_config.get("Env")
        if (
            not isinstance(configured_environment, list)
            or not all(isinstance(value, str) for value in configured_environment)
            or sorted(
                value
                for value in configured_environment
                if value.split("=", 1)[0] in ("HOME", "TMPDIR")
            )
            != private_environment
        ):
            raise ValueError("Caddy private temporary environment differs")
        phase, observed_channels = "native-log-bounds", ()
        logs = _run_docker(["logs", name], preserve_newlines=True)
        observed_channels = (("logs.stdout", logs.stdout), ("logs.stderr", logs.stderr))
        if len(logs.stdout.encode("utf-8")) > 65536 or len(logs.stderr.encode("utf-8")) > 65536:
            raise ValueError("Caddy native log output exceeds retained bound")
        # Logs are opaque diagnostic channels, never process-environment truth.
        # Retain digests only; no unknown stdout or stderr values are uploaded.
        phase, observed_channels = "private-directory", ()
        private_directory = _run_docker(
            [
                "exec",
                name,
                "/bin/busybox",
                "stat",
                "-c",
                "%u:%g:%a:%F",
                "/run/pulseplate-caddy-tmp",
            ],
            preserve_newlines=True,
        ).stdout
        observed_channels = (("stat.stdout", private_directory),)
        if private_directory != "65532:65532:700:directory\n":
            raise ValueError("Caddy private temporary directory owner/mode differs")
        evidence.update(
            config_sha256=hashlib.sha256(loaded).hexdigest(),
            response=probe.stdout,
            process_command=command,
            sockets=sockets,
            inspected=inspected,
            startup_stdout_sha256=hashlib.sha256(logs.stdout.encode("utf-8")).hexdigest(),
            startup_stderr_sha256=hashlib.sha256(logs.stderr.encode("utf-8")).hexdigest(),
            private_temporary_environment=private_environment,
            private_temporary_directory=private_directory,
        )
    except BaseException as operation_error:
        operation_error.add_note("Caddy runtime phase: " + phase)
        for channel, output in observed_channels:
            diagnostic_bytes = output.encode("utf-8")
            operation_error.add_note(
                "Caddy "
                + channel
                + " utf8_bytes="
                + str(len(diagnostic_bytes))
                + " sha256="
                + hashlib.sha256(diagnostic_bytes).hexdigest()
            )
        primary_error = operation_error
        raise
    finally:
        _CADDY_REMAINING = outer_remaining
        try:
            if created:
                inspection = _run_docker(["inspect", name])
                current = json.loads(inspection.stdout)[0]
                if _is_caddy_synthetic_environment(current["Config"].get("Env")):
                    for channel, output in (
                        ("stdout", inspection.stdout),
                        ("stderr", inspection.stderr),
                    ):
                        try:
                            with (directory / ("cleanup-inspect." + channel)).open(
                                "x", encoding="utf-8"
                            ) as cleanup_stream:
                                cleanup_stream.write(output)
                        except Exception as capture_error:
                            diagnostic_errors.append(("cleanup-inspect." + channel, capture_error))
                else:
                    diagnostic_errors.append(
                        ("cleanup-inspect", ValueError("Caddy synthetic inspection not retained"))
                    )
                if current["Config"]["Labels"].get("pulseplate.caddy-D") != name:
                    raise ValueError("Caddy cleanup ownership differs")
                if primary_error is None:
                    try:
                        final_state = current["State"]
                        if (
                            current["Id"] != prepared["Id"]
                            or current["Image"] != image
                            or current["Path"] != "/usr/bin/caddy"
                            or current["Args"] != ["run", "--config", "/ci.json"]
                            or current["Config"]["Tty"] is not False
                            or final_state["Pid"] != state["Pid"]
                            or final_state["StartedAt"] != state["StartedAt"]
                            or current["RestartCount"] != 0
                            or not final_state["Running"]
                            or final_state["Restarting"]
                            or final_state["OOMKilled"]
                        ):
                            primary_error = ValueError("Caddy final process identity differs")
                            primary_error.add_note("Caddy runtime phase: final-identity")
                    except Exception as identity_error:
                        identity_error.add_note("Caddy runtime phase: final-identity")
                        primary_error = identity_error
                _run_docker(["rm", "--force", name])
        except BaseException as cleanup_error:
            cleanup_error.add_note("Caddy runtime phase: cleanup")
            if primary_error is None:
                primary_error = cleanup_error
            else:
                primary_error.add_note("Caddy cleanup also failed: " + type(cleanup_error).__name__)
        if diagnostic_errors:
            if primary_error is None:
                primary_error = diagnostic_errors[0][1]
            for filename, recorded_error in diagnostic_errors:
                primary_error.add_note(
                    "Caddy diagnostic write failed ("
                    + filename
                    + "): "
                    + type(recorded_error).__name__
                )
        if primary_error is not None:
            raise primary_error
    return evidence


CADDY_API_WORKER = r"""
import hashlib
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import stat
import sys
from urllib.request import Request

root = Path(sys.argv[1])
expected = sys.argv[2]
endpoint = sys.argv[3]
cache = Path(sys.pycache_prefix)
if not root.is_absolute() or root.resolve(strict=True) != root or cache.is_symlink() or not cache.is_dir() or any(cache.iterdir()):
    raise ValueError("Caddy API fixed source/cache root differs")
for relative in ("scripts", "scripts/ci"):
    directory = root / relative
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Caddy API namespace directory differs")
for relative in ("scripts.py", "scripts.pyc", "scripts/__init__.py", "scripts/__init__.pyc", "scripts/ci.py", "scripts/ci.pyc", "scripts/ci/__init__.py", "scripts/ci/__init__.pyc", "scripts/ci/prometheus_source_image.pyc"):
    path = root / relative
    if path.exists() or path.is_symlink():
        raise ValueError("Caddy API namespace shadow or bytecode")
for relative in ("__pycache__", "scripts/__pycache__", "scripts/ci/__pycache__"):
    directory = root / relative
    if directory.is_symlink() or (directory.exists() and (not directory.is_dir() or any(directory.glob("*.pyc")))):
        raise ValueError("Caddy API project bytecode is not a source input")
source = root / "scripts/ci/prometheus_source_image.py"
if source.is_symlink() or not stat.S_ISREG(source.stat().st_mode) or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
    raise ValueError("Caddy API helper source drift")
# Standard-library roots remain ahead of this one explicit project root.
# This is a fixed standalone child import, not a generic module loader.
sys.path.append(str(root))
for name, relative in (("scripts", "scripts"), ("scripts.ci", "scripts/ci")):
    spec = importlib.util.find_spec(name)
    if spec is None or spec.loader is not None or spec.origin is not None or list(spec.submodule_search_locations or ()) != [str(root / relative)]:
        raise ValueError("Caddy API namespace resolver differs")
spec = importlib.util.find_spec("scripts.ci.prometheus_source_image")
if spec is None or spec.origin != str(source) or type(spec.loader) is not importlib.machinery.SourceFileLoader or not spec.cached or not Path(spec.cached).is_relative_to(cache) or Path(spec.cached).exists():
    raise ValueError("Caddy API canonical source resolver differs")
from scripts.ci.prometheus_source_image import opener
import scripts.ci.prometheus_source_image as owner
if owner.__file__ != str(source) or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
    raise ValueError("Caddy API imported source drift")
url = "https://api.github.com/repos/Katsiarynakavaleuskaya/PulsePlate" + endpoint
request = Request(url, headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
    "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
with opener().open(request, timeout=float(sys.argv[4])) as response:
    if response.geturl() != url:
        raise ValueError("Caddy API redirect")
    raw = response.read(8388609)
if len(raw) > 8388608:
    raise ValueError("Caddy API response bound")
sys.stdout.buffer.write(raw)
"""


def caddy_ci_api(
    root: Path, directory: Path, endpoint: str, remaining: Callable[[float], float], expected: str
) -> Any:
    """Use the incumbent process owner for the same finite no-redirect API GET."""
    source = root / "scripts/ci/prometheus_source_image.py"
    if source.is_symlink() or not source.is_file():
        raise ValueError("Caddy API source is not regular")
    if (
        re.fullmatch(r"[0-9a-f]{64}", expected) is None
        or hashlib.sha256(source.read_bytes()).hexdigest() != expected
    ):
        raise ValueError("Caddy API helper differs from admitted source")
    from scripts.ci.prometheus_source_image import GitHubRead, reject_constant, unique_object

    slot = min(int(os.environ["CADDY_API_CALL_SECONDS"]), remaining(float("inf")))
    cleanup = int(os.environ["CADDY_API_CLEANUP_SECONDS"])
    if not 0 < cleanup <= 10 or not cleanup < slot <= 30:
        raise ValueError("Caddy API whole-call slot unavailable")
    # Auth and HTTP child share this one work deadline; construction does not
    # earn another slot. The existing close owner has only the reserved tail.
    deadline = time.monotonic() + slot - cleanup
    directory.mkdir(mode=0o700)
    evidence = directory / "evidence"
    evidence.mkdir(mode=0o700)
    cache = directory / "pycache"
    cache.mkdir(mode=0o700)
    reader = GitHubRead(directory / "private", evidence, deadline, cleanup)
    primary: BaseException | None = None
    try:
        raw = reader._capture(
            [
                sys.executable,
                "-E",
                "-S",
                "-B",
                "-X",
                "pycache_prefix=" + str(cache),
                "-c",
                CADDY_API_WORKER,
                str(root),
                expected,
                endpoint,
                str(slot - cleanup),
            ],
            8388608,
        )
        return json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            reader.close()
        except BaseException as cleanup_error:
            if primary is None:
                raise
            primary.add_note("Caddy API cleanup also failed: " + type(cleanup_error).__name__)


def caddy_ci_charge_action(phase: str, seconds: int | None = None) -> int:
    """Debit one existing action ceiling before its independently timed invocation."""
    with caddy_ci_phase(phase) as remaining:
        available = remaining(float("inf"))
        state_path = Path(os.environ["RUNNER_TEMP"]) / "caddy-admission/admission.json"
        state = json.loads(state_path.read_bytes())
        cap = int(os.environ["CADDY_PHASE_" + phase]) if seconds is None else seconds
        if type(cap) is not int or cap <= 0 or available < cap - 0.05:
            raise ValueError("Caddy complete action ceiling is unavailable: " + phase)
        state["budget"]["action_deadlines"][phase] = time.monotonic() + available
        state["budget"]["charged"][phase] += cap
        state_path.write_text(json.dumps(state, sort_keys=True))
        return cap


@contextmanager
def caddy_ci_phase(phase: str) -> Iterator[Callable[[float], float]]:
    """Charge a finite Caddy phase against the same runner clock and existing state."""
    global _CADDY_REMAINING
    state_path = Path(os.environ["RUNNER_TEMP"]) / "caddy-admission/admission.json"
    if state_path.is_symlink() or not state_path.is_file():
        raise ValueError("Caddy budget state unavailable")
    state = json.loads(state_path.read_bytes())
    budget = state["budget"]
    if budget["boot_id"] != Path("/proc/sys/kernel/random/boot_id").read_text().strip():
        raise ValueError("Caddy monotonic clock host differs")
    caps = {
        key.removeprefix("CADDY_PHASE_"): int(value)
        for key, value in os.environ.items()
        if key.startswith("CADDY_PHASE_")
    }
    if (
        phase not in caps
        or any(value <= 0 for value in caps.values())
        or set(budget["charged"]) != set(caps)
        or budget["seconds"] != sum(caps.values())
        or type(budget["started"]) not in (int, float)
        or not math.isfinite(budget["started"])
        or any(
            type(value) not in (int, float)
            or not math.isfinite(value)
            or not 0 <= value <= caps[name]
            for name, value in budget["charged"].items()
        )
    ):
        raise ValueError("Caddy phase inventory differs")
    global_seconds = sum(caps.values())
    if state.get("mode") == "reuse":
        caps["BUILD"] = int(os.environ["CADDY_REUSE_TIMEOUT_SECONDS"])
    started = time.monotonic()
    if started < float(budget["started"]) or any(
        float(budget["charged"][name]) > cap for name, cap in caps.items()
    ):
        raise ValueError("Caddy future clock or mode phase charge differs")
    spent = float(budget["charged"][phase])
    if type(spent) not in (float, int) or not 0 <= spent <= caps[phase]:
        raise ValueError("Caddy phase charge differs")
    reserve = sum(
        caps[name] - float(budget["charged"][name])
        for name in caps
        if name not in (phase, "SAFETY")
    )
    deadline = min(
        started + caps[phase] - spent, float(budget["started"]) + global_seconds - reserve
    )

    def remaining(cap: float) -> float:
        value = min(cap, deadline - time.monotonic())
        if value <= 0:
            raise ValueError("Caddy exhausted phase/global reserved budget: " + phase)
        return value

    previous = _CADDY_REMAINING
    _CADDY_REMAINING = remaining
    try:
        remaining(float("inf"))
        yield remaining
        remaining(float("inf"))
    finally:
        _CADDY_REMAINING = previous
        current = json.loads(state_path.read_bytes())
        if current["budget"]["started"] != budget["started"]:
            raise ValueError("Caddy budget clock reset")
        current["budget"]["charged"][phase] = min(
            caps[phase],
            max(current["budget"]["charged"][phase], spent + time.monotonic() - started),
        )
        state_path.write_text(json.dumps(current, sort_keys=True))


def validate_caddy_source_evidence(
    directory: Path,
    *,
    binary_metadata: bytes,
    binary_sha256: str,
    recipe: bytes,
) -> dict[str, object]:
    """Recognize only the reviewed v3 source carrier; execution belongs to its producer."""
    from scripts.ci.prometheus_source_image import decode_objects

    def require(condition: object, message: str) -> None:
        if not condition:
            raise ValueError("Caddy source: " + message)

    require(directory.is_dir() and not directory.is_symlink(), "evidence directory")
    require({path.name for path in directory.iterdir()} == CADDY_BUILD_MEMBERS, "sixteen members")
    data = {}
    for name in sorted(CADDY_BUILD_MEMBERS):
        path = directory / name
        info = path.lstat()
        require(
            stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= 2097152,
            "regular bounded member",
        )
        data[name] = path.read_bytes()
        require(len(data[name]) == info.st_size, "member read drift")
    require(sum(map(len, data.values())) <= 8388608, "aggregate bytes")
    for names, digest, count in (
        (
            ("original-tree.sha256", "copied-tree.sha256", "original-post-build-tree.sha256"),
            CADDY_ORIGINAL_TREE,
            71,
        ),
        (
            ("patched-tree.sha256", "post-unit-tree.sha256", "post-build-tree.sha256"),
            CADDY_PATCHED_TREE,
            72,
        ),
    ):
        for name in names:
            require(hashlib.sha256(data[name]).hexdigest() == digest, "source tree identity")
            lines = data[name].decode("ascii").splitlines()
            require(
                len(lines) == count
                and len(set(lines)) == count
                and all(re.fullmatch(r"[0-9a-f]{64}  \./[A-Za-z0-9_./-]+", line) for line in lines),
                "source tree members",
            )
    require(
        data["inputs.sha256"]
        == (
            CADDY_PATCH_SHA256
            + "  /opt/go-jose-v3.patch\n"
            + CADDY_COMPAT_SHA256
            + "  /opt/caddy_v3_compat_test.go\n"
        ).encode(),
        "patch and consumer identities",
    )
    require(
        re.fullmatch(rb"git version [0-9.]+\n[0-9a-f]{64}  /usr/bin/git\n", data["patch-tool.txt"]),
        "patch tool",
    )
    require(
        re.fullmatch(rb"[0-9a-f]{64}  go.mod\n[0-9a-f]{64}  go.sum\n", data["build-module.sha256"]),
        "module file hashes",
    )
    require(re.fullmatch(r"[0-9a-f]{64}", binary_sha256), "binary digest")
    require(
        data["binary.sha256"] == (binary_sha256 + "  /go/bin/caddy\n").encode(),
        "binary source binding",
    )
    # These intended pre-replacement checks are joined to the authenticated fresh
    # successful build step by the workflow, never treated alone as execution.
    for witness in (
        b"4e7e6b60541ab03bd402e573fc2c1264297e661726c5f53529ca14ae58625a27",
        CADDY_SOURCE_MODULES["github.com/go-jose/go-jose/v3"][1].encode(),
        b"go mod verify",
        b"go mod edit -replace=github.com/go-jose/go-jose/v3@v3.0.5=/opt/go-jose-v3.0.5-patched",
    ):
        require(witness in recipe, "pre-replacement verification recipe")
    for name, count, packages in (
        (
            "jose-tests.jsonl",
            301,
            {
                "github.com/go-jose/go-jose/v3" + tail
                for tail in ("", "/cipher", "/cryptosigner", "/json", "/jwt")
            },
        ),
        ("compat-tests.jsonl", 19, {"pulseplate.local/caddy-build/compat"}),
    ):
        records = [json.loads(line) for line in data[name].splitlines()]
        require(
            all(
                isinstance(row, dict)
                and row.get("Action") in {"start", "run", "pause", "cont", "output", "pass"}
                for row in records
            ),
            "test failure or unsupported event",
        )
        running = [
            (row.get("Package"), row["Test"])
            for row in records
            if row.get("Action") == "run" and "Test" in row
        ]
        passed = [
            (row.get("Package"), row["Test"])
            for row in records
            if row.get("Action") == "pass" and "Test" in row
        ]
        terminal = [
            row.get("Package")
            for row in records
            if row.get("Action") == "pass" and "Test" not in row
        ]
        started = [row.get("Package") for row in records if row.get("Action") == "start"]
        require(
            len(passed) == count
            and len(set(passed)) == count
            and set(running) == set(passed)
            and len(running) == count
            and set(terminal) == packages
            and set(started) == packages
            and len(terminal) == len(started) == len(packages),
            "complete native test outcomes",
        )
    rows = decode_objects(data["modules.json"])
    require(
        all(isinstance(row, dict) and type(row.get("Path")) is str for row in rows),
        "module records",
    )
    modules = {row["Path"]: row for row in rows}
    require(len(modules) == len(rows), "duplicate module")
    original = "github.com/go-jose/go-jose/v3"
    require([row["Path"] for row in rows if "Replace" in row] == [original], "one replacement")
    require(
        modules.get(original)
        == {
            "Path": original,
            "Version": "v3.0.5",
            "Replace": {
                "Path": CADDY_PATCHED_ROOT,
                "Dir": CADDY_PATCHED_ROOT,
                "GoMod": CADDY_PATCHED_ROOT + "/go.mod",
                "GoVersion": "1.12",
            },
            "Indirect": True,
            "Dir": CADDY_PATCHED_ROOT,
            "GoMod": CADDY_PATCHED_ROOT + "/go.mod",
            "GoVersion": "1.12",
        },
        "version-qualified native replacement without fabricated Sum",
    )
    for module, row in modules.items():
        if module not in (original, "pulseplate.local/caddy-build"):
            require(
                type(row.get("Version")) is str
                and type(row.get("Sum")) is str
                and row["Sum"].startswith("h1:"),
                "ordinary module version and sum",
            )
    graph = {}
    for line in data["import-graph.txt"].decode().splitlines():
        fields = line.split("|")
        require(len(fields) == 3 and fields[0] and fields[0] not in graph, "import graph identity")
        package, location, imports = fields
        require(
            location.startswith(("/usr/local/go/src/", "/go/pkg/mod/", CADDY_PATCHED_ROOT))
            and ".." not in Path(location).parts
            and not any(c.isspace() for c in package + location),
            "import graph directory",
        )
        if package == original or package.startswith(original + "/"):
            require(
                location == CADDY_PATCHED_ROOT + package[len(original) :],
                "patched package directory",
            )
        graph[package] = (location, imports.split())
    require(
        all(set(imports) <= set(graph) for _, imports in graph.values()), "complete target imports"
    )
    reached: set[str] = set()
    pending = [CADDY_IMPORT_CHAIN[0]]
    while pending:
        package = pending.pop()
        require(package in graph, "target package missing")
        if package not in reached:
            reached.add(package)
            pending.extend(graph[package][1])
    require(reached == set(graph), "disconnected target graph member")
    imported_modules: set[str] = set()
    for package, (location, _) in graph.items():
        require(str(Path(location)) == location, "import directory alias")
        if location.startswith("/usr/local/go/src/"):
            require(location == "/usr/local/go/src/" + package, "standard library directory")
            continue
        owners = [
            (name, row["Dir"])
            for name, row in modules.items()
            if type(row.get("Dir")) is str
            and (location == row["Dir"] or location.startswith(row["Dir"] + "/"))
        ]
        require(bool(owners), "import module directory missing")
        owner, directory_root = max(owners, key=lambda pair: len(pair[1]))
        require(
            package == owner + location[len(directory_root) :], "import module path association"
        )
        imported_modules.add(owner)
    require(
        all(
            a in graph and b in graph[a][1]
            for a, b in zip(CADDY_IMPORT_CHAIN, CADDY_IMPORT_CHAIN[1:])
        ),
        "connected Caddy v3 imports",
    )
    module_edges = [line.split() for line in data["module-graph.txt"].decode().splitlines()]
    require(module_edges and all(len(edge) == 2 for edge in module_edges), "module graph rows")
    require(
        any(edge[1] == original + "@v3.0.5" for edge in module_edges),
        "module graph original version",
    )

    def selected_binary(raw: bytes) -> list[list[str]]:
        lines = [line.split() for line in raw.decode().splitlines() if line.strip()]
        require(
            any(
                line == ["go", "go1.26.10"] or line == ["/go/bin/caddy:", "go1.26.10"]
                for line in lines
            ),
            "Go compiler",
        )
        selected = [line for line in lines if line[0] in ("mod", "dep", "=>")]
        require(all(len(line) >= 2 for line in selected), "malformed binary module row")
        replacements = [i for i, line in enumerate(selected) if line[0] == "=>"]
        require(len(replacements) == 1 and replacements[0] > 0, "binary one replacement")
        at = replacements[0]
        require(
            selected[at - 1] == ["dep", original, "v3.0.5"]
            and selected[at] == ["=>", CADDY_PATCHED_ROOT, "(devel)"],
            "binary replacement association",
        )
        ordinary = [line for line in selected if line[0] != "=>" and line[1] != original]
        require(
            all(
                len(line) == 4
                and line[1] in modules
                and (line[2], line[3])
                == (modules[line[1]].get("Version"), modules[line[1]].get("Sum"))
                for line in ordinary
            ),
            "binary module sums",
        )
        require(len({line[1] for line in ordinary}) == len(ordinary), "binary duplicate module")
        require(
            {line[1] for line in ordinary} | {original} == imported_modules,
            "binary complete imported modules",
        )
        require(
            [line for line in ordinary if line[1] == "github.com/go-jose/go-jose/v4"]
            == [
                [
                    "dep",
                    "github.com/go-jose/go-jose/v4",
                    *CADDY_SOURCE_MODULES["github.com/go-jose/go-jose/v4"],
                ]
            ],
            "binary v4",
        )
        return selected

    require(
        selected_binary(binary_metadata) == selected_binary(data["build-info.txt"]),
        "retained versus actual binary metadata",
    )
    return {
        "members": {name: hashlib.sha256(raw).hexdigest() for name, raw in data.items()},
        "binary_sha256": binary_sha256,
        "compiled_module_versions": {
            name: modules[name]["Version"] for name in sorted(imported_modules)
        },
        "import_packages": len(graph),
        "source_correction": "CVE-2026-116587",
        "v3_scanner_comparability": "UNKNOWN",
    }


def validate_caddy_ci_report(
    image: str,
    report_path: Path,
    *,
    binary_metadata: bytes,
    source_evidence: Path,
    binary_sha256: str,
    recipe: bytes,
    native_exit: int,
    expected_report_sha256: str,
) -> dict[str, object]:
    """Recognize the exact patched source and unsuppressed report, never a D waiver."""
    if type(native_exit) is not int or native_exit != 0:
        raise ValueError("Caddy native full scanner did not succeed")
    source = validate_caddy_source_evidence(
        source_evidence, binary_metadata=binary_metadata, binary_sha256=binary_sha256, recipe=recipe
    )
    if re.fullmatch(r"sha256:[0-9a-f]{64}", image) is None:
        raise ValueError("Caddy decision requires an immutable local image ID")
    report = _read_trivy_image_report(image, report_path)
    if hashlib.sha256(report_path.read_bytes()).hexdigest() != expected_report_sha256:
        raise ValueError("Caddy native report bytes differ")
    config = report["Metadata"].get("ImageConfig", {})
    if (config.get("architecture"), config.get("os")) != ("amd64", "linux"):
        raise ValueError("Caddy native report platform differs")
    caddy = [row for row in report["Results"] if row["Target"] == "usr/bin/caddy"]
    if len(caddy) != 1 or (caddy[0]["Class"], caddy[0]["Type"]) != ("lang-pkgs", "gobinary"):
        raise ValueError("Caddy result identity differs")
    inventory = []
    for result in report["Results"]:
        if "Secrets" in result and (type(result["Secrets"]) is not list or result["Secrets"]):
            raise ValueError("Caddy secret results are not an empty native array")
        if result["Class"] not in ("os-pkgs", "lang-pkgs"):
            raise ValueError("Caddy unrecognized native result class")
        packages = result.get("Packages")
        if not isinstance(packages, list) or not packages:
            raise ValueError("Caddy complete package inventory missing")
        for package in packages:
            if not isinstance(package, dict) or not all(
                type(package.get(k)) is str and package[k] for k in ("Name", "ID")
            ):
                raise ValueError("Caddy package identity malformed")
            if package["Name"] == CADDY_PATCHED_ROOT:
                if (
                    result is not caddy[0]
                    or package["ID"] != CADDY_PATCHED_ROOT
                    or "Version" in package
                    or package.get("Identifier", {}).get("PURL")
                    != "pkg:golang/opt/go-jose-v3.0.5-patched"
                ):
                    raise ValueError("Caddy local replacement report identity differs")
            elif not isinstance(package.get("Version"), str) or not package["Version"]:
                raise ValueError("Caddy package version missing outside exact source replacement")
        for finding in result.get("Vulnerabilities", []):
            if not all(
                type(finding.get(k)) is str and finding[k]
                for k in (
                    "VulnerabilityID",
                    "PkgName",
                    "PkgID",
                    "InstalledVersion",
                    "Severity",
                    "Status",
                )
            ):
                raise ValueError("Caddy finding identity malformed")
            if finding["Severity"] not in ("UNKNOWN", "LOW", "MEDIUM"):
                raise ValueError("Caddy unsuppressed HIGH/CRITICAL or unknown severity")
            matches = [
                p
                for p in packages
                if (p["ID"], p["Name"], p.get("Version"))
                == (finding["PkgID"], finding["PkgName"], finding["InstalledVersion"])
            ]
            if len(matches) != 1:
                raise ValueError("Caddy finding/package identity is not unique")
            identity = (
                result["Target"],
                result["Class"],
                result["Type"],
                finding["VulnerabilityID"],
                finding["PkgID"],
                finding["InstalledVersion"],
                finding["Severity"],
            )
            if identity in inventory:
                raise ValueError("Caddy duplicate finding")
            inventory.append(identity)
    if len([p for p in caddy[0]["Packages"] if p["Name"] == CADDY_PATCHED_ROOT]) != 1:
        raise ValueError("Caddy exact unversioned replacement package missing")
    if [
        (p["Name"], p.get("Version"))
        for p in caddy[0]["Packages"]
        if p["Name"] == "github.com/go-jose/go-jose/v4"
    ] != [("github.com/go-jose/go-jose/v4", "v4.1.6")]:
        raise ValueError("Caddy native v4 identity differs")
    compiled = source["compiled_module_versions"]
    if not isinstance(compiled, dict):
        raise ValueError("Caddy compiled module observation malformed")
    expected_go = dict(compiled)
    expected_go.pop("github.com/go-jose/go-jose/v3")
    expected_go[CADDY_PATCHED_ROOT] = None
    expected_go["stdlib"] = "v1.26.10"
    observed_go = [(package["Name"], package.get("Version")) for package in caddy[0]["Packages"]]
    if len(observed_go) != len(set(observed_go)) or set(observed_go) != set(expected_go.items()):
        raise ValueError("Caddy complete binary and scanner Go package inventory differ")
    if any(
        package["ID"] != package["Name"] + "@" + package["Version"]
        for package in caddy[0]["Packages"]
        if package["Name"] != CADDY_PATCHED_ROOT
    ):
        raise ValueError("Caddy ordinary Go package identity differs")
    return {
        "decision": "source_CVE116587_correction_with_unsuppressed_scan",
        "source": source,
        "finding_inventory": inventory,
        "v3_scanner_comparability": "UNKNOWN",
        "CD_release_accepted": False,
    }


def validate_caddy_policy_projection(image: str, raw_path: Path, projected_path: Path) -> None:
    """Native strict conversion must preserve every complete raw report field."""
    if _read_trivy_image_report(image, raw_path) != _read_trivy_image_report(image, projected_path):
        raise ValueError("Caddy strict native conversion changed a report member")


def _validate_caddy_local_control_layers(
    reports: dict[str, dict[str, Any]], controls: dict[str, Any]
) -> None:
    """Identify the local image transport before accepting a finding without a compressed digest."""
    parent_layers, child_layers = controls["parent_layers"], controls["child_layers"]
    if (
        not parent_layers
        or child_layers[-1] in parent_layers
        or not all(
            isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value)
            for value in child_layers
        )
    ):
        raise ValueError("Caddy local child DiffIDs differ")
    child_tag = controls.get("child_tag")
    if (
        not isinstance(controls.get("owner"), str)
        or not controls["owner"]
        or child_tag != "pulseplate-caddy-control:" + controls["owner"]
    ):
        raise ValueError("Caddy owned local control tag required")
    for subject, tag, expected_layers in (
        ("candidate", "pulseplate-caddy:contract", parent_layers),
        ("secret", child_tag, child_layers),
    ):
        metadata = reports[subject + "-full"]["Metadata"]
        high_metadata = reports[subject + "-HC"]["Metadata"]
        expected_rootfs = {"type": "layers", "diff_ids": expected_layers}
        for observed in (metadata, high_metadata):
            config = observed.get("ImageConfig")
            if not isinstance(config, dict) or config.get("rootfs") != expected_rootfs:
                raise ValueError("Caddy local image config layers differ")
            descriptors = observed.get("Layers")
            if (
                observed.get("Reference") != tag
                or observed.get("RepoTags") != [tag]
                or observed.get("RepoDigests", []) != []
                or observed.get("DiffIDs") != expected_layers
                or not isinstance(descriptors, list)
                or len(descriptors) != len(expected_layers)
            ):
                raise ValueError("Caddy local control source or layer metadata differs")
            for descriptor, diff_id in zip(descriptors, expected_layers, strict=True):
                if (
                    not isinstance(descriptor, dict)
                    or set(descriptor) not in ({"Size", "DiffID"}, {"Size", "Digest", "DiffID"})
                    or not isinstance(descriptor["DiffID"], str)
                    or descriptor["DiffID"] != diff_id
                    or type(descriptor["Size"]) is not int
                    or descriptor["Size"] < 0
                    or (
                        "Digest" in descriptor
                        and not (
                            isinstance(descriptor["Digest"], str)
                            and re.fullmatch(r"sha256:[0-9a-f]{64}", descriptor["Digest"])
                        )
                    )
                ):
                    raise ValueError("Caddy native layer descriptor differs")
        if metadata["Layers"] != high_metadata["Layers"]:
            raise ValueError("Caddy local full and HC layer metadata differ")
    if "Digest" in reports["secret-full"]["Metadata"]["Layers"][-1]:
        raise ValueError("Caddy uncompressed finding contradicts native layer digest")


def validate_caddy_control_reports(
    candidate: dict[str, Any],
    controls: dict[str, Any],
    directory: Path,
) -> dict[str, object]:
    """Consume the finite same-epoch candidate/official/secret native observations."""
    if (
        set(controls["subjects"]) != {"candidate", "official", "secret"}
        or len(set(controls["subjects"].values())) != 3
    ):
        raise ValueError("Caddy distinct control subjects required")
    reports: dict[str, dict[str, Any]] = {"candidate-full": candidate}
    expected_exits = {
        "candidate-full": 0,
        "candidate-HC": 0,
        "official-full": 0,
        "official-HC": 1,
        "secret-full": 0,
        "secret-HC": 1,
    }
    observations = controls["scans"]
    if set(observations) != set(expected_exits):
        raise ValueError("Caddy six native control observations required")
    for name, expected in expected_exits.items():
        observation = observations[name]
        if (
            type(observation.get("exit")) is not int
            or observation["exit"] != expected
            or observation.get("timeout") is not False
        ):
            raise ValueError("Caddy expected rejection requires successful native scanning")
        if observation.get("file") != name + ".raw.json":
            raise ValueError("Caddy native control report alias")
        path = directory / observation["file"]
        if (
            path.parent != directory
            or path.is_symlink()
            or not path.is_file()
            or not 0 < path.stat().st_size <= 134217728
        ):
            raise ValueError("Caddy native control report file")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != observation["sha256"]:
            raise ValueError("Caddy native control bytes changed")
        report = json.loads(raw)
        image = controls["subjects"][name.split("-")[0]]
        if type(image) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image) is None:
            raise ValueError("Caddy immutable control image required")
        if (
            report.get("SchemaVersion") != 2
            or report.get("ArtifactType") != "container_image"
            or report.get("ArtifactName") != image
            or report.get("Metadata", {}).get("ImageID") != image
            or not isinstance(report.get("Results"), list)
            or not report["Results"]
        ):
            raise ValueError("Caddy native control subject or shape")
        if name == "candidate-full":
            if report != candidate:
                raise ValueError("Caddy candidate report changed before controls")
        else:
            native_id = _run_docker(
                ["image", "inspect", "--format", "{{.Id}}", image]
            ).stdout.strip()
            if native_id != image:
                raise ValueError("Caddy control native image changed")
        reports[name] = report
    for subject in ("candidate", "official", "secret"):
        full, high = reports[subject + "-full"], reports[subject + "-HC"]
        expected_results = copy.deepcopy(full["Results"])
        for row in expected_results:
            if "Vulnerabilities" in row:
                selected = [
                    v for v in row["Vulnerabilities"] if v.get("Severity") in ("HIGH", "CRITICAL")
                ]
                if selected:
                    row["Vulnerabilities"] = selected
                else:
                    del row["Vulnerabilities"]
        if high["Results"] != expected_results:
            raise ValueError("Caddy full and HC native inventory differ")
    official = reports["official-HC"]
    witness = [
        finding
        for row in official["Results"]
        if row.get("Target") == "usr/bin/caddy"
        for finding in row.get("Vulnerabilities", [])
        if finding.get("VulnerabilityID") == "CVE-2026-116587"
        and finding.get("PkgName") == "github.com/go-jose/go-jose/v3"
        and finding.get("InstalledVersion") == "v3.0.5"
        and finding.get("Severity") == "HIGH"
        and finding.get("PkgID") == "github.com/go-jose/go-jose/v3@v3.0.5"
        and finding.get("PkgIdentifier", {}).get("PURL")
        == "pkg:golang/github.com/go-jose/go-jose/v3@v3.0.5"
        and finding.get("Status") == "affected"
    ]
    official_packages = [
        package
        for row in official["Results"]
        if row.get("Target") == "usr/bin/caddy"
        for package in row.get("Packages", [])
        if package.get("Name") == "github.com/go-jose/go-jose/v3"
        and package.get("Version") == "v3.0.5"
        and package.get("ID") == "github.com/go-jose/go-jose/v3@v3.0.5"
    ]
    if len(witness) != 1 or len(official_packages) != 1:
        raise ValueError("Caddy official vulnerable positive witness missing")
    for subject in ("candidate", "official"):
        if any(
            row.get("Secrets") or row.get("Class") == "secret"
            for row in reports[subject + "-full"]["Results"]
        ):
            raise ValueError("Caddy unexpected actual secret report")
    secret_rows = [row for row in reports["secret-full"]["Results"] if row.get("Class") == "secret"]
    if (
        len(secret_rows) != 1
        or set(secret_rows[0]) != {"Target", "Class", "Secrets"}
        or secret_rows[0]["Target"] != "/credentials.txt"
    ):
        raise ValueError("Caddy exact synthetic secret result required")
    findings = secret_rows[0]["Secrets"]
    if not isinstance(findings, list) or len(findings) != 1:
        raise ValueError("Caddy exact synthetic secret finding required")
    secret = findings[0]
    masked = "GITHUB_PAT=" + "*" * 40
    expected_secret = {
        "RuleID": "github-pat",
        "Category": "GitHub",
        "Severity": "CRITICAL",
        "Title": "GitHub Personal Access Token",
        "StartLine": 1,
        "EndLine": 1,
        "Code": {
            "Lines": [
                {
                    "Number": 1,
                    "Content": masked,
                    "IsCause": True,
                    "Annotation": "",
                    "Truncated": False,
                    "Highlighted": masked,
                    "FirstCause": True,
                    "LastCause": True,
                },
                {
                    "Number": 2,
                    "Content": "",
                    "IsCause": False,
                    "Annotation": "",
                    "Truncated": False,
                    "FirstCause": False,
                    "LastCause": False,
                },
            ]
        },
        "Match": masked,
        "Offset": 11,
        "Layer": secret.get("Layer"),
    }
    parent_layers, child_layers = controls["parent_layers"], controls["child_layers"]
    if (
        not isinstance(parent_layers, list)
        or not isinstance(child_layers, list)
        or len(child_layers) != len(parent_layers) + 1
        or child_layers[:-1] != parent_layers
    ):
        raise ValueError("Caddy secret child layer lineage")
    layer = secret.get("Layer")
    if (
        secret != expected_secret
        or not isinstance(layer, dict)
        or set(layer) not in ({"DiffID", "CreatedBy"}, {"Digest", "DiffID", "CreatedBy"})
        or layer["DiffID"] != child_layers[-1]
        or (
            "Digest" in layer
            and not (
                isinstance(layer["Digest"], str)
                and re.fullmatch(r"sha256:[0-9a-f]{64}", layer["Digest"])
            )
        )
        or layer["CreatedBy"] != "caddy run --config /etc/caddy/Caddyfile --adapter caddyfile"
    ):
        raise ValueError("Caddy synthetic secret contents or layer differ")
    if "Digest" not in layer:
        _validate_caddy_local_control_layers(reports, controls)
    else:
        for stage in ("secret-full", "secret-HC"):
            metadata = reports[stage]["Metadata"]
            if "Layers" in metadata:
                descriptors = metadata["Layers"]
                if (
                    not isinstance(descriptors, list)
                    or not descriptors
                    or not isinstance(descriptors[-1], dict)
                ):
                    raise ValueError("Caddy compressed layer metadata malformed")
                final = descriptors[-1]
                if "Digest" in final and (
                    final["Digest"] != layer["Digest"] or final.get("DiffID") != layer["DiffID"]
                ):
                    raise ValueError("Caddy compressed finding contradicts native layer digest")
    if (
        controls["filesystem_delta"] != ["A /credentials.txt"]
        or controls["child_was_started"] is not False
    ):
        raise ValueError("Caddy secret child execution or filesystem delta")
    expected_fixture = (
        "GITHUB_PAT=" + "ghp_" + "012345678901234567890123456789abcdef" + "\n"
    ).encode()
    if controls["fixture_sha256"] != hashlib.sha256(expected_fixture).hexdigest():
        raise ValueError("Caddy synthetic fixture bytes differ")
    for subject, context in (
        ("candidate", "pulseplate-caddy"),
        ("secret", "pulseplate-caddy-control"),
    ):
        report = reports[subject + "-full"]
        artifact = (
            "sha256:"
            + hashlib.sha256(
                (controls["subjects"][subject] + ":index.docker.io/library/" + context).encode()
            ).hexdigest()
        )
        if report.get("ArtifactID") != artifact:
            raise ValueError("Caddy exact native ArtifactID context differs")
        for row in report["Results"]:
            for finding in row.get("Vulnerabilities", []):
                expected_fingerprint = (
                    "sha256:"
                    + hashlib.sha256(
                        (
                            artifact
                            + ":"
                            + row["Target"]
                            + ":"
                            + finding["PkgID"]
                            + ":"
                            + finding["VulnerabilityID"]
                        ).encode()
                    ).hexdigest()
                )
                if finding.get("Fingerprint") != expected_fingerprint:
                    raise ValueError("Caddy native vulnerability fingerprint differs")
    original, child = reports["candidate-full"], reports["secret-full"]
    expected_rows = copy.deepcopy(original["Results"])
    for row in expected_rows:
        if row["Class"] == "os-pkgs":
            if not row["Target"].startswith(original["ArtifactName"] + " "):
                raise ValueError("Caddy OS target prefix differs")
            row["Target"] = child["ArtifactName"] + row["Target"][len(original["ArtifactName"]) :]
        for finding in row.get("Vulnerabilities", []):
            finding["Fingerprint"] = (
                "sha256:"
                + hashlib.sha256(
                    (
                        child["ArtifactID"]
                        + ":"
                        + row["Target"]
                        + ":"
                        + finding["PkgID"]
                        + ":"
                        + finding["VulnerabilityID"]
                    ).encode()
                ).hexdigest()
            )
    if expected_rows != [row for row in child["Results"] if row.get("Class") != "secret"]:
        raise ValueError("Caddy secret child changed complete nonsecret inventory")
    return {
        "native_controls": "observed_exact_current_epoch",
        "v3_scanner_comparability": "UNKNOWN",
        "reports": {name: value["sha256"] for name, value in observations.items()},
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Docker image reference to inspect.")
    parser.add_argument(
        "--trivy-report",
        type=Path,
        help="Optional native Trivy JSON image report to bind before reporting runtime inventory.",
    )
    parser.add_argument(
        "--blocked-prefix",
        action="append",
        dest="blocked_prefixes",
        default=None,
        help="Additional blocked package prefix. May be passed multiple times.",
    )
    parser.add_argument(
        "--blocked-debian-package",
        action="append",
        dest="blocked_debian_packages",
        default=None,
        help="Exact Debian package name that must not exist in the production image. May be passed multiple times.",
    )
    parser.add_argument(
        "--blocked-debian-prefix",
        action="append",
        dest="blocked_debian_prefixes",
        default=None,
        help="Debian package-name prefix that must not exist in the production image. May be passed multiple times.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path for writing the JSON result payload.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    args = parse_args(argv)
    if args.trivy_report is not None:
        validate_trivy_image_report(args.image, args.trivy_report)
    extra_blocked_prefixes = tuple(args.blocked_prefixes or ())
    blocked_prefixes = DEFAULT_BLOCKED_PREFIXES + extra_blocked_prefixes
    blocked_debian_packages = tuple(args.blocked_debian_packages or ())
    blocked_debian_prefixes = tuple(args.blocked_debian_prefixes or ())
    result = build_result(
        args.image,
        blocked_prefixes,
        blocked_debian_packages,
        blocked_debian_prefixes,
    )
    payload = json.dumps(asdict(result), indent=2)

    if args.output_json is not None:
        args.output_json.write_text(payload + "\n", encoding="utf-8")

    stream = sys.stdout if result.passed else sys.stderr
    print(payload, file=stream)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
