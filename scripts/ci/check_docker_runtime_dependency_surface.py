#!/usr/bin/env python3
"""Check the production Docker image dependency surface.

RU: Проверяет, что production Docker image не содержит CI/dev tooling или
optional vector/ML packages.
EN: Verifies that the production Docker image excludes CI/dev tooling and
optional vector/ML packages.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import re
import stat
import subprocess  # nosec B404 # B404: subprocess is required for bounded local Docker inspection (remove-by: 2026-10-30, ref: PR-docker-runtime-slimming)
import sys
from typing import Any
import uuid

DOCKER_BINARY = shutil.which("docker")
DOCKER_TIMEOUT_SECONDS = 60
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
        result = subprocess.run(  # nosec B603 # B603: resolved Docker for fixed run inventory or image inspect calls; 60-second timeout and no shell (remove-by: 2026-10-30, ref: PR-docker-runtime-slimming)
            [DOCKER_BINARY, *args],
            check=True,
            capture_output=True,
            text=not preserve_newlines,
            timeout=DOCKER_TIMEOUT_SECONDS,
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


# D is a temporary isolated frontend CI decision, never a backend/CD default.
CADDY_D_REVIEW_BY = date(2026, 10, 30)
CADDY_D_REMOVE_BY = date(2026, 11, 4)
CADDY_D_MODULES = {
    "github.com/go-jose/go-jose/v3": ("v3.0.5", "h1:BLLJWbC4nMZOfuPVxoZIxeYsn6Nl2r1fITaJ78UQlVQ="),
    "github.com/go-jose/go-jose/v4": ("v4.1.6", "h1:sNRkftxFJxwsILiQukqp5z83QBSmntVwmgRY7AqBDO4="),
}
CADDY_D_CONFIG = (
    b'{"admin":{"disabled":true,"config":{"persist":false}},"apps":{"http":{"servers":'
    b'{"ci":{"listen":["127.0.0.1:18080"],"automatic_https":{"disable":true},'
    b'"routes":[{"handle":[{"handler":"static_response","body":'
    b'"pulseplate-caddy-D\\nHOME={env.HOME}\\nTMPDIR={env.TMPDIR}\\n"}]}]}}}}}\n'
)
CADDY_D_FINDING = {
    "VulnerabilityID": "CVE-2026-116587",
    "PkgName": "github.com/go-jose/go-jose/v3",
    "PkgID": "github.com/go-jose/go-jose/v3@v3.0.5",
    "InstalledVersion": "v3.0.5",
    "Severity": "HIGH",
    "Status": "affected",
}


def caddy_ci_source_inventory(root: Path, paths: list[str]) -> dict[str, dict[str, object]]:
    """Hash the caller-enumerated complete tracked build context and fixed CI owners."""
    fixed = {
        ".github/workflows/frontend-ci.yml",
        "deploy/Caddyfile",
        "deploy/Caddyfile.production",
        "scripts/ci/check_docker_runtime_dependency_surface.py",
        "scripts/ci/prometheus_source_image.py",
        "scripts/ci/check_trivy_ignore_policy_expiry.py",
        "trivy/ignore-policy-caddy-go-jose-v3.rego",
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
        path = root / name
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
            raise ValueError("Caddy relevant source is not a regular file")
        raw = path.read_bytes()
        inventory[name] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "mode": stat.S_IMODE(path.stat().st_mode),
        }
    return inventory


def validate_caddy_ci_window(policy: Path, *, today: date) -> None:
    """Check the same accepted dates before admission/build and after scanning."""
    from scripts.ci.check_trivy_ignore_policy_expiry import evaluate_policy_file

    if (
        type(today) is not date
        or today < date(2026, 10, 28)
        or today > CADDY_D_REVIEW_BY
        or today > CADDY_D_REMOVE_BY
    ):
        raise ValueError("Caddy D review/expiry window is not current")
    failures = evaluate_policy_file(policy, today=today)
    if failures:
        raise ValueError("Caddy policy review/expiry HOLD: " + "; ".join(failures))


def observe_caddy_ci_runtime(image: str, directory: Path) -> dict[str, object]:
    """Bind two serving-process values and isolated storage, never a deployed service."""
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
    synthetic_environment = [
        "HOME=/run/pulseplate-caddy-tmp",
        "TMPDIR=/run/pulseplate-caddy-tmp",
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "CADDY_VERSION=v2.11.4",
        "XDG_CONFIG_HOME=/config",
        "XDG_DATA_HOME=/data",
    ]
    phase = "create"
    observed_channels: tuple[tuple[str, str], ...] = ()
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
            or prepared_config.get("Env") != synthetic_environment
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
        if inspected["Config"].get("Env") != synthetic_environment:
            raise ValueError("Caddy synthetic environment changed after startup")
        for channel, output in (("stdout", inspection.stdout), ("stderr", inspection.stderr)):
            try:
                with (directory / ("container-inspect." + channel)).open(
                    "x", encoding="utf-8"
                ) as stream:
                    stream.write(output)
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
        try:
            if created:
                inspection = _run_docker(["inspect", name])
                current = json.loads(inspection.stdout)[0]
                if current["Config"].get("Env") == synthetic_environment:
                    for channel, output in (
                        ("stdout", inspection.stdout),
                        ("stderr", inspection.stderr),
                    ):
                        try:
                            with (directory / ("cleanup-inspect." + channel)).open(
                                "x", encoding="utf-8"
                            ) as stream:
                                stream.write(output)
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


def validate_caddy_ci_report(
    image: str,
    report_path: Path,
    *,
    binary_metadata: bytes,
    today: date,
    native_exit: int,
    expected_report_sha256: str,
) -> dict[str, object]:
    """Decide the exact D finding inventory after the workflow binds source/runtime/run.

    This explicit caller does not authorize risk, prove execution from scalar inputs,
    change the raw report, or affect the generic structural validator or strict CD.
    """
    if type(native_exit) is not int or native_exit != 0:
        raise ValueError("Caddy native full scanner did not succeed")
    if (
        type(today) is not date
        or today < date(2026, 10, 28)
        or today > CADDY_D_REVIEW_BY
        or today > CADDY_D_REMOVE_BY
    ):
        raise ValueError("Caddy D review/expiry window is not current")
    if re.fullmatch(r"sha256:[0-9a-f]{64}", image) is None:
        raise ValueError("Caddy decision requires an immutable local image ID")
    report = _read_trivy_image_report(image, report_path)
    if hashlib.sha256(report_path.read_bytes()).hexdigest() != expected_report_sha256:
        raise ValueError("Caddy native report bytes differ")
    image_config = report["Metadata"].get("ImageConfig")
    if not isinstance(image_config, dict) or (
        image_config.get("architecture"),
        image_config.get("os"),
    ) != ("amd64", "linux"):
        raise ValueError("Caddy native report platform differs")
    lines = [line.split() for line in binary_metadata.decode("utf-8").splitlines()]
    if any(row and row[0] == "=>" for row in lines):
        raise ValueError("Caddy binary replacement is forbidden")
    for module, (version, checksum) in CADDY_D_MODULES.items():
        if [row for row in lines if len(row) > 1 and row[1] == module] != [
            ["dep", module, version, checksum]
        ]:
            raise ValueError("Caddy actual binary module identity differs")
    caddy_rows = [row for row in report["Results"] if row["Target"] == "usr/bin/caddy"]
    if len(caddy_rows) != 1 or (caddy_rows[0]["Class"], caddy_rows[0]["Type"]) != (
        "lang-pkgs",
        "gobinary",
    ):
        raise ValueError("Caddy result identity differs")
    accepted = []
    inventory = []
    for result in report["Results"]:
        if "Secrets" in result and (type(result["Secrets"]) is not list or result["Secrets"]):
            raise ValueError("Caddy secret results are not an empty native array")
        if result["Class"] not in ("os-pkgs", "lang-pkgs"):
            raise ValueError("Caddy unrecognized native result class")
        packages = result.get("Packages")
        if not isinstance(packages, list) or not packages:
            raise ValueError("Caddy complete package inventory missing")
        if any(
            not isinstance(p, dict)
            or not all(isinstance(p.get(k), str) and p[k] for k in ("Name", "Version", "ID"))
            for p in packages
        ):
            raise ValueError("Caddy package identity malformed")
        for finding in result.get("Vulnerabilities", []):
            if not all(
                isinstance(finding.get(k), str) and finding[k]
                for k in (
                    "VulnerabilityID",
                    "PkgName",
                    "PkgID",
                    "InstalledVersion",
                    "Severity",
                    "Status",
                )
            ) or finding["Severity"] not in ("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"):
                raise ValueError("Caddy finding identity/severity malformed")
            matches = [
                p
                for p in packages
                if (p["ID"], p["Name"], p["Version"])
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
            if finding["Severity"] in ("HIGH", "CRITICAL"):
                purl = "pkg:golang/github.com/go-jose/go-jose/v3@v3.0.5"
                if (
                    result is not caddy_rows[0]
                    or any(finding.get(k) != v for k, v in CADDY_D_FINDING.items())
                    or finding.get("FixedVersion", "") != ""
                    or not isinstance(finding.get("PkgIdentifier"), dict)
                    or finding["PkgIdentifier"].get("PURL") != purl
                    or not isinstance(matches[0].get("Identifier"), dict)
                    or matches[0]["Identifier"].get("PURL") != purl
                ):
                    raise ValueError("Caddy has a HIGH/CRITICAL outside accepted D")
                accepted.append(finding)
    if len(accepted) != 1:
        raise ValueError("Caddy requires exactly one visible accepted v3 finding")
    for module, (version, _checksum) in CADDY_D_MODULES.items():
        if [
            (p["Name"], p["Version"]) for p in caddy_rows[0]["Packages"] if p["Name"] == module
        ] != [(module, version)]:
            raise ValueError("Caddy native package module version differs")
    return {
        "decision": "accepted_temporary_CI_residual_risk",
        "accepted": accepted,
        "finding_inventory": inventory,
        "review_by": CADDY_D_REVIEW_BY.isoformat(),
        "remove_by_inclusive": CADDY_D_REMOVE_BY.isoformat(),
        "v3_fixed": False,
        "CD_release_accepted": False,
    }


def validate_caddy_policy_projection(
    image: str, raw_path: Path, projected_path: Path, *, accept_v3: bool
) -> None:
    """Require successful native conversion to preserve the complete raw report projection."""
    expected = copy.deepcopy(_read_trivy_image_report(image, raw_path))
    actual = _read_trivy_image_report(image, projected_path)
    removed = 0
    for result in expected["Results"]:
        if accept_v3 and result["Target"] == "usr/bin/caddy":
            original = result.get("Vulnerabilities", [])
            kept = [
                row for row in original if any(row.get(k) != v for k, v in CADDY_D_FINDING.items())
            ]
            removed += len(original) - len(kept)
            if kept:
                result["Vulnerabilities"] = kept
            else:
                result.pop("Vulnerabilities", None)
    if removed != int(accept_v3) or actual != expected:
        raise ValueError("Caddy native policy changed an unexpected report member")


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
