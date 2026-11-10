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
from datetime import datetime
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


# Frozen Go-v3 native metadata: seed2.11.4 and selected2.11.9 before local v3 replacement.
# These historical input bindings never become guessed x/net062 output pins.
CADDY_XNET062_INCUMBENT_FILES = {
    "baseline-go.mod": "1d41fe1c258e7c6a6180eeea06b31aa3fd068e35120038cbc6fe15e7f89c21a6",
    "baseline-go.sum": "912171681209ea4fcc6c3f2571307a16dfccb77ac88eb4ec6e1246329a1e23df",
    "baseline-modules.json": "f18a737a749e514db520c435e888dfced1865efe5aafb64c28fa5e1935d85a09",
    "baseline-module-graph.txt": "b1c650b3999bdd295f399bd1ed509b34b404c6fc239070b2c18d5dfae08bbace",
    "baseline-packages.json": "325952468890a84b81b734895b72342ea33907feb15aa38d016da2451f249992",
    "baseline-verify.txt": "b4537ed75f533f993f371954de47e42a793b8e5b0587577de7e27fb3e50696bd",
    "incumbent-go.mod": "40a8c29bde80ddaaf323030a9631453d905b1deafc4eb909c0b2b1c43bd2965d",
    "incumbent-go.sum": "bc1def232f1f0a8d205b39c38fa9b0159d481c05f90933bc975659ec0c0317c8",
    "incumbent-modules.json": "fa0c145b518c15baa0e9d215a101400066fc43f1d39992bdb4e1cd25ca542197",
    "incumbent-module-graph.txt": (
        "1db07897d94dae5f699b88b5dfccb5afffc21240bbe89297029839735246db93"
    ),
    "incumbent-packages.json": "e373e649e7db5cc5dc972e5e8881b44c7871de5b7ea93ea59ae38da2c7fa22bb",
    "incumbent-verify.txt": "b4537ed75f533f993f371954de47e42a793b8e5b0587577de7e27fb3e50696bd",
}
CADDY_XNET062_METADATA_EPOCH = "caddy2.11.9-xnet062-metadata"
CADDY_XNET062_METADATA_SUCCESS = "observed_xnet062_metadata_only"
_CADDY_METADATA_NEVER_STARTED = "0001-01-01T00:00:00Z"


def _caddy_metadata_mounts_by_destination(mounts: Any) -> dict[str, dict[str, Any]]:
    """Index the owned Caddy mounts without changing any row or path."""
    if type(mounts) is not list:
        raise ValueError("Caddy metadata Mounts must be a list")
    by_destination: dict[str, dict[str, Any]] = {}
    for row in mounts:
        if type(row) is not dict:
            raise ValueError("Caddy metadata mount must be an object")
        destination = row.get("Destination")
        if (
            type(destination) is not str
            or not destination.startswith("/")
            or "\0" in destination
            or any(part in ("", ".", "..") for part in destination[1:].split("/"))
        ):
            raise ValueError("Caddy metadata mount destination must be a canonical absolute path")
        if destination in by_destination:
            raise ValueError("Caddy metadata mount destination is duplicated")
        by_destination[destination] = row
    return by_destination


def validate_caddy_metadata_custody(
    before: dict[str, Any], actual: dict[str, Any], *, started_id: str | None
) -> None:
    """Bind a Caddy compiler or resolver container to its owned prestart profile."""
    from scripts.ci.prometheus_source_image import exact_data

    container_id = before.get("Id")
    if not isinstance(container_id, str) or re.fullmatch(r"[0-9a-f]{64}", container_id) is None:
        raise ValueError("Caddy metadata custody requires a full container ID")
    if started_id is not None and started_id != container_id:
        raise ValueError("Caddy metadata start belongs to another container")
    for field in ("Id", "Name", "Image", "Config"):
        exact_data(actual[field], before[field])
    exact_data(
        _caddy_metadata_mounts_by_destination(actual.get("Mounts")),
        _caddy_metadata_mounts_by_destination(before.get("Mounts")),
    )
    original, state = before["State"], actual["State"]
    if (
        original.get("Status") != "created"
        or original.get("Running") is not False
        or original.get("StartedAt") != _CADDY_METADATA_NEVER_STARTED
    ):
        raise ValueError("Caddy metadata prestart state differs")
    started_at = state.get("StartedAt")
    started = (state.get("Status") == "running" and state.get("Running") is True) or (
        state.get("Status") == "exited" and state.get("Running") is False
    )
    if started:
        if (
            started_id is None
            or not isinstance(started_at, str)
            or re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?Z",
                started_at,
            )
            is None
        ):
            raise ValueError("Caddy metadata actual start is unproved")
        try:
            parsed_start = datetime.fromisoformat(started_at)
        except ValueError as error:
            raise ValueError("Caddy metadata actual start is unproved") from error
        if parsed_start.year <= 1:
            raise ValueError("Caddy metadata actual start is unproved")
    elif (
        state.get("Status") != "created"
        or state.get("Running") is not False
        or started_at != _CADDY_METADATA_NEVER_STARTED
    ):
        raise ValueError("Caddy metadata current state differs")

    old_host, new_host = before["HostConfig"], actual["HostConfig"]
    if (
        started
        and old_host.get("OomKillDisable") is False
        and "OomKillDisable" in new_host
        and new_host["OomKillDisable"] is None
    ):
        new_host = {**new_host, "OomKillDisable": False}
    exact_data(new_host, old_host)


def validate_caddy_xnet062_metadata(
    output: Path, *, deadline: float | None = None
) -> dict[str, Any]:
    """Inspect one complete new-action replay; no build/profile adoption or native call."""
    from scripts.ci.prometheus_source_image import (
        _xnet062_member,
        decode_objects,
        decode_selected_modules,
    )

    if not stat.S_ISDIR(output.lstat().st_mode):
        raise ValueError("Caddy metadata output must be a real directory")
    suffixes = (
        "go.mod",
        "go.sum",
        "modules.json",
        "module-graph.txt",
        "packages.json",
        "verify.txt",
    )
    raw: dict[str, bytes] = {}
    for phase in ("baseline", "incumbent", "incumbent-offline", "final", "final-offline"):
        for suffix in suffixes:
            name = phase + "-" + suffix
            path = output / name
            info = path.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or not 0 < info.st_size <= 32 * 1024**2
            ):
                raise ValueError("Caddy metadata member type/size differs")
            data = _xnet062_member(output, name, deadline)
            if len(data) != info.st_size:
                raise ValueError("Caddy metadata member changed during read")
            raw[name] = data
    for name, digest in CADDY_XNET062_INCUMBENT_FILES.items():
        if hashlib.sha256(raw[name]).hexdigest() != digest:
            raise ValueError("Caddy retained incumbent metadata differs: " + name)
    for phase in ("incumbent", "final"):
        for suffix in suffixes:
            if raw[phase + "-" + suffix] != raw[phase + "-offline-" + suffix]:
                raise ValueError("Caddy online/offline metadata differs")
    phases = {}
    root = "github.com/caddyserver/caddy/v2"
    command = root + "/cmd/caddy"
    for phase in ("baseline", "incumbent", "final"):
        modules = decode_selected_modules(
            raw[phase + "-modules.json"], root_module="pulseplate.local/caddy-build"
        )
        if any("Replace" in row for row in modules.values()):
            raise ValueError("Caddy metadata replacement is unqualified")
        packages = decode_objects(raw[phase + "-packages.json"])
        indexed = {row.get("ImportPath"): row for row in packages}
        if (
            len(indexed) != len(packages)
            or any(not isinstance(name, str) or not name for name in indexed)
            or indexed.get(command, {}).get("Name") != "main"
            or any(
                row.get("Error") or row.get("DepsErrors") or row.get("Incomplete")
                for row in packages
            )
        ):
            raise ValueError("Caddy complete command metadata differs")
        for row in packages:
            mapping = row.get("ImportMap", {})
            if any(mapping.get(path, path) not in indexed for path in row.get("Imports", [])):
                raise ValueError("Caddy command import closure incomplete")
        graph = raw[phase + "-module-graph.txt"].splitlines()
        if (
            not graph
            or len(graph) != len(set(graph))
            or any(len(row.split()) != 2 for row in graph)
        ):
            raise ValueError("Caddy complete module edges malformed")
        expected_root = "v2.11.4" if phase == "baseline" else "v2.11.9"
        if modules.get(root, {}).get("Version") != expected_root:
            raise ValueError("Caddy original/incumbent root identity differs")
        phases[phase] = {"modules": modules, "packages": len(packages)}
    before, after = phases["incumbent"]["modules"], phases["final"]["modules"]
    target = "golang.org/x/net"
    if (
        before.get(target, {}).get("Version") != "v0.60.0"
        or after.get(target, {}).get("Version") != "v0.62.0"
    ):
        raise ValueError("Caddy xnet062 authored selection differs")
    if all(raw["incumbent-" + name] == raw["final-" + name] for name in ("go.mod", "go.sum")):
        raise ValueError("Caddy xnet062 lock delta is empty")
    delta = [
        {
            "path": path,
            "before": before.get(path),
            "after": after.get(path),
            "class": "I_R" if path == target else "C_R_candidate",
        }
        for path in sorted(set(before) | set(after))
        if before.get(path) != after.get(path)
    ]
    original = phases["baseline"]["modules"]
    historical = [
        {
            "path": path,
            "before": original.get(path),
            "after": before.get(path),
            "class": "historical_Caddy_intent" if path == root else "historical_Caddy_closure",
        }
        for path in sorted(set(original) | set(before))
        if original.get(path) != before.get(path)
    ]
    return {
        "epoch": CADDY_XNET062_METADATA_EPOCH,
        "phases": phases,
        "historical_caddy_delta": historical,
        "complete_delta": delta,
        "build_profile_admission": "HOLD pending actual closure/fullF and output-profile adoption",
    }


# Reviewed selected-source profile from metadata run 42614729223, artifact 13672158177.
# Only stable member bytes, module/graph facts and command package identities cross runs.
CADDY_XNET062_PROFILE_SHA256 = "872500ba864b9c4b5fc5e60686ba45465fd51a4f1d26d8560719d775410a3c94"


def _caddy_xnet062_profile(
    output: Path, inventory: list[dict[str, Any]], derivation: dict[str, Any], deadline: float
) -> str:
    from scripts.ci.prometheus_source_image import _xnet062_member, canonical_data, decode_objects

    digests = {row["path"]: row["sha256"] for row in inventory}

    def member(name: str) -> bytes:
        raw: bytes = _xnet062_member(output, name, deadline)
        if hashlib.sha256(raw).hexdigest() != digests[name]:
            raise ValueError("Caddy semantic input changed after inventory")
        return raw

    stable = {
        row["path"]: row["sha256"]
        for row in inventory
        if not row["path"].endswith(
            ("-modules.json", "-packages.json", "-delta.json", "-module-graph.txt")
        )
    }

    def facts(module: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in module.items() if k not in ("Dir", "GoMod")}

    phases = {}
    for phase, data in derivation["phases"].items():
        modules = {path: facts(module) for path, module in data["modules"].items()}
        packages = {}
        for row in decode_objects(member(phase + "-packages.json")):
            module = row.get("Module", {})
            packages[row["ImportPath"]] = [
                row["Name"],
                row.get("Standard", False),
                facts(module),
                sorted(row.get("Imports", [])),
                row.get("ImportMap", {}),
            ]
        edges = sorted(member(phase + "-module-graph.txt").decode().splitlines())
        phases[phase] = {"modules": modules, "edges": edges, "command_packages": packages}
    profile = {"members": [row["path"] for row in inventory], "stable": stable, "phases": phases}
    profile["transitions"] = {
        kind: [[row["path"], row["class"]] for row in derivation[kind]]
        for kind in ("complete_delta", "historical_caddy_delta")
    }
    return hashlib.sha256(canonical_data(profile)).hexdigest()


def validate_caddy_prebuild(
    work: Path, inputs: dict[str, dict[str, object]], checked_head: str, deadline: float
) -> None:
    """Bind the current metadata step's completed observation before a BUILD charge."""
    from scripts.ci.prometheus_source_image import (
        canonical_data,
        exact_data,
        _xnet062_member,
        one_object,
        real_directory,
        tree_inventory,
    )

    def read_object(path: Path, limit: int) -> tuple[dict[str, Any], str]:
        if path.lstat().st_size > limit:
            raise ValueError("Caddy prebuild JSON exceeds size bound")
        raw = _xnet062_member(path.parent, path.name, deadline)
        if len(raw) > limit:
            raise ValueError("Caddy prebuild JSON exceeds size bound")
        return one_object(raw), hashlib.sha256(raw).hexdigest()

    env = os.environ
    repository = "Katsiarynakavaleuskaya/PulsePlate"
    if (
        env["GITHUB_EVENT_NAME"] != "workflow_dispatch"
        or env["CADDY_ACTION"] != "candidate-D"
        or env["GITHUB_REPOSITORY"] != repository
        or env["GITHUB_REPOSITORY_ID"] != "1043311030"
        or env["GITHUB_REF"] != "refs/heads/codex/dependency-alertmanager-remediation"
        or not re.fullmatch(r"[0-9a-f]{40}", checked_head)
        or env["GITHUB_SHA"] != checked_head
        or env["GITHUB_RUN_ATTEMPT"] != "1"
        or not re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"])
    ):
        raise ValueError("Caddy prebuild event or source differs")
    run_id = int(env["GITHUB_RUN_ID"])
    state, _ = read_object(work / "caddy-admission/admission.json", 4 * 1024**2)
    expected_state = {
        "mode": "build",
        "repository": repository,
        "repository_id": 1043311030,
        "current_head": checked_head,
        "current_run_id": run_id,
        "current_run_attempt": 1,
        "inputs": inputs,
    }
    exact_data({key: state.get(key) for key in expected_state}, expected_state)
    metadata = work / "caddy-xnet062-metadata"
    report, report_hash = read_object(metadata / "evidence/qualification.json", 16 * 1024**2)
    recipe = inputs["frontend/Dockerfile.caddy-spa"]["sha256"]
    expected_report = {
        "status": CADDY_XNET062_METADATA_SUCCESS,
        "failure": None,
        "go_build_invocations": 0,
        "authored_action": "golang.org/x/net@v0.62.0",
        "source_head": checked_head,
        "run_id": run_id,
        "run_attempt": 1,
        "recipe_sha256": recipe,
    }
    exact_data({key: report[key] for key in expected_report}, expected_report)
    if (
        recipe != "0c78748dba55fceea2afbb62f4bd6693f3d784f613089c7a8fbc54b518344f92"
        or report.get("cleanup_failure") is not None
        or set(report["derivations"]) != {"a", "b"}
        or report["compiler_platform"]["digest"]
        != "sha256:9d1e2c4fda593efb2c405e1c855c75ec17fe42dc02f6b7142a5ea7af7f386bf4"
        or report["compiler_go_version_sha256"]
        != "4e0b213cba780f63b02f3ab9001ee61e4101d254e0af1a8205574c19dad0f93b"
        or type(report["compiler_scan"]["Secrets_fields_absent"]) is not int
        or report["compiler_scan"]["Secrets_fields_absent"] <= 0
    ):
        raise ValueError("Caddy qualification identity or cleanup differs")

    # The current successful producer validates the native commands and cleanup, then
    # exports its report/inventory binding. Require evidence of all eight distinct starts.
    native = report["native_commands"]
    if not isinstance(native, list) or not native:
        raise ValueError("Caddy native evidence missing")
    starts = [row for row in native if row["argv"][3:5] == ["start", "--attach"]]
    channels = {
        f"{lane}-{phase}-{network}-native.stdout"
        for lane in ("a", "b")
        for phase in ("incumbent", "final")
        for network in ("online", "offline")
    } | {"compiler-native-version.stdout"}
    ids = {row["argv"][-1] for row in starts}
    if (
        not all(
            type(row["exit"]) is int and row["exit"] == 0 and row["failure"] is None
            for row in native
        )
        or {Path(row["stdout"]).name for row in starts} != channels
        or len(starts) != len(ids)
        or len(ids) != len(channels)
        or not all(isinstance(cid, str) and re.fullmatch(r"[0-9a-f]{64}", cid) for cid in ids)
        or Path(native[-1]["stdout"]).name != "cleanup-absence.stdout"
    ):
        raise ValueError("Caddy native replay or terminal cleanup evidence differs")

    left, right = metadata / "a/output", metadata / "b/output"
    real_directory(left)
    real_directory(right)
    if left.samefile(right):
        raise ValueError("Caddy replay roots alias")
    previous = None
    for label, output in (("a", left), ("b", right)):
        # The native capture emits exactly 39 flat, single-link regular files.
        with os.scandir(output) as entries:
            count = 0
            for entry in entries:
                count += 1
                if count > 39 or not entry.is_file(follow_symlinks=False):
                    raise ValueError("Caddy replay member inventory differs")
        if count != 39:
            raise ValueError("Caddy replay member inventory differs")
        inventory = tree_inventory(output, maximum=64 * 1024**2, deadline=deadline)
        if previous is not None:
            exact_data(inventory, previous)
        previous = inventory
        binding = hashlib.sha256(canonical_data([report_hash, inventory])).hexdigest()
        if binding != env["CADDY_METADATA_BINDING"]:
            raise ValueError("Caddy metadata step binding differs")
        result = validate_caddy_xnet062_metadata(output, deadline=deadline)
        exact_data(result, report["derivations"][label])
        if (
            _caddy_xnet062_profile(output, inventory, result, deadline)
            != CADDY_XNET062_PROFILE_SHA256
        ):
            raise ValueError("Caddy reviewed selected-source profile differs")


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
CADDY_V3_BUILD_MEMBERS = frozenset(
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
CADDY_STDLIB_ROOT = "/opt/go1.26.10-http-patched"
CADDY_STDLIB_BASELINE_ROOT = "/opt/go1.26.10-http-baseline"
CADDY_STDLIB_ORIGINAL_TREE = "e54472503fcedc70793baefd53d9ae2eee748610e190f99f533ae6ef7c3ecf64"
CADDY_STDLIB_BASELINE_TREE = "aed4cf1ca75d78f74118dc8686cd0bdd6d017c1b8bb98e0f46c2ed859ad72a26"
CADDY_STDLIB_PATCHED_TREE = "afce6dcef776fcfe337fff1c5d4a3c68cd4729be7c27463d07e09fc7fafaa3f5"
CADDY_STDLIB_ORIGINAL_COUNT = 15045
CADDY_STDLIB_PATCH_SHA256 = "9beb880c561244794fda6176ac17f3f9c1690ae31fc26ac069afbf452e1c3f22"
CADDY_STDLIB_FIXTURE_SHA256 = "2dc6f44b2e7a95a1b970cdbbcf70ddc532c35921c4b83ff80ca6e48b20a1c32e"
CADDY_STDLIB_BEFORE_SHA256 = "3e04744176d3cf5bef2827ab158b10aaeec3981ac5f4e7fb86e3dbf5f592eed7"
CADDY_STDLIB_AFTER_SHA256 = "0a19c32dab21d8c906795189b5c35da22551e0c2932a07b1fe64ac4559e70a01"
CADDY_GO_BINARY_SHA256 = "9c2a37ae5b21ba1d5a004bb9ab4d0c64de6fc5778e9d30487adccea62678b8b5"
CADDY_STDLIB_MEMBERS = frozenset(
    {
        "stdlib-inputs.sha256",
        "stdlib-original-tree.sha256",
        "stdlib-baseline-tree.sha256",
        "stdlib-patched-tree.sha256",
        "stdlib-post-tests-tree.sha256",
        "stdlib-post-build-tree.sha256",
        "stdlib-original-post-build-tree.sha256",
        "stdlib-baseline-red.jsonl",
        "stdlib-baseline-controls.jsonl",
        "stdlib-patched-tests.jsonl",
        "stdlib-test-inventory.txt",
        "stdlib-test-commands.txt",
    }
)
CADDY_BUILD_MEMBERS = CADDY_V3_BUILD_MEMBERS | CADDY_STDLIB_MEMBERS
CADDY_V3_TOTAL_BYTES = 8 * 1024**2
CADDY_STDLIB_TOTAL_BYTES = 16 * 1024**2
CADDY_SOURCE_TOTAL_BYTES = 24 * 1024**2
CADDY_SOURCE_TAR_BYTES = CADDY_SOURCE_TOTAL_BYTES + 1024**2
CADDY_STDLIB_MEMBER_LIMITS = {
    "stdlib-inputs.sha256": 4096,
    "stdlib-test-inventory.txt": 65536,
    "stdlib-test-commands.txt": 16384,
}
CADDY_STDLIB_CUSTOM_TOPS = [
    "TestPPHTTPConnectionBaseline",
    "TestPPHTTPConnectionSurvivors",
    "TestPPHTTPConnectionFieldNameCase",
    "TestPPHTTPBoundaryControls",
    "TestPPHTTPFramingControls",
    "TestPPHTTPMalformedReaderControls",
    "TestPPHTTPMalformedAcceptedParity",
    "TestPPHTTPResponseWriteRoundTrip",
    "TestPPHTTPTransportCloseNominees",
    "TestPPHTTPTransportPersistenceOptions",
    "TestPPHTTPPersistenceOptions",
    "TestPPHTTPPersistenceBoundaryControls",
    "TestPPHTTPPersistenceWriteRoundTrip",
]
CADDY_STDLIB_CUSTOM_SUBTESTS = {
    "TestPPHTTPConnectionSurvivors": [
        "close_only",
        "repeated_close",
        "first",
        "middle",
        "last",
        "separate_fields",
        "duplicates_and_spelling",
        "ows_empty",
        "opaque_near_misses",
    ],
    "TestPPHTTPBoundaryControls": [
        "no_connection",
        "upgrade_no_close",
        "empty_elements_no_close",
        "near_misses_no_close",
        "http10_close",
        "http10_keepalive",
        "http10_close_keepalive",
        "request_false_flag",
    ],
    "TestPPHTTPFramingControls": [
        "content_length_nomination",
        "chunked_trailer",
        "eof_delimited",
        "truncated_content_length",
        "head",
        "no_content",
        "not_modified",
    ],
    "TestPPHTTPMalformedReaderControls": [
        "embedded_cr",
        "nul_value",
        "invalid_field_name",
        "bare_lf_broken_field",
        "invalid_content_length",
        "invalid_transfer_coding",
    ],
    "TestPPHTTPMalformedAcceptedParity": [
        "legacy_space_field_name",
        "opaque_obs_text",
        "bare_lf_lines",
        "folded_ows",
    ],
    "TestPPHTTPPersistenceOptions": [
        "same_line",
        "reversed",
        "split_fields",
        "case_duplicate_controls",
        "nominees",
        "duplicate_nominees",
        "ows_empty",
        "opaque_near_misses",
    ],
    "TestPPHTTPPersistenceBoundaryControls": [
        "keepalive_only",
        "keepalive_with_nominees",
        "eof_close_without_close_token",
        "request_both_controls",
    ],
    "TestPPHTTPPersistenceWriteRoundTrip": ["controls_only", "controls_and_nominees"],
}
CADDY_STDLIB_BASELINE_CUSTOM = {
    "TestPPHTTPBoundaryControls",
    "TestPPHTTPMalformedReaderControls",
    "TestPPHTTPMalformedAcceptedParity",
    "TestPPHTTPPersistenceBoundaryControls",
}
CADDY_STDLIB_UPSTREAM_TOPS = [
    "TestReadResponse",
    "TestWriteResponse",
    "TestReadResponseErrors",
    "TestResponseWritesOnlySingleConnectionClose",
    "TestReadResponseCloseInMiddle",
    "TestResponseContentLengthShortBody",
    "TestTransportConnectionCloseOnResponse",
    "TestTransportConnectionCloseOnRequest",
    "TestTransportRespectRequestWantsClose",
    "TestTransportReadToEndReusesConn",
    "TestIssue3644",
    "TestTransportResponseBodyWritableOnProtocolSwitch",
]
CADDY_STDLIB_HELPERS = {
    "src/net/http/internal/ascii/print.go": "f2af00c0c1b74c279c0bd7d1b0054a5440cb4046cbd60292dfc1aa4ada76845e",
    "src/net/http/server.go": "6f344ca40661ce5d31ce7f237dc23c53d4d34fe3043bd5e76bac50e6c97d91cb",
    "src/net/textproto/reader.go": "fe649123b4df42a4aeb7713aa3f8028de61897072874f37c67c497bd6bbf734f",
    "src/net/textproto/textproto.go": "e4f0d94752345b5dec4fe7f4805531e8036a9cd44131d807cafa700dd5323901",
    "src/vendor/golang.org/x/net/http/httpguts/httplex.go": "8cfd5819dc821d45f82fde10afff4b2e652535b0091e0559fc8ad7766051a2c2",
}

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


CADDY_CI_FIXED_SOURCES = {
    ".github/workflows/frontend-ci.yml",
    "deploy/Caddyfile",
    "deploy/Caddyfile.production",
    "scripts/ci/check_docker_runtime_dependency_surface.py",
    "scripts/ci/prometheus_source_image.py",
    "scripts/ci/check_trivy_ignore_policy_expiry.py",
    "trivy/ignore-policy.rego",
}


def caddy_ci_source_inventory(root: Path, paths: list[str]) -> dict[str, dict[str, object]]:
    """Hash the caller-enumerated complete tracked build context and fixed CI owners."""
    fixed = CADDY_CI_FIXED_SOURCES
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
    "CADDY_VERSION=v2.11.9",
    "XDG_CONFIG_HOME=/config",
    "XDG_DATA_HOME=/data",
)


def _is_caddy_synthetic_environment(value: object, *, vulnerable_control: bool = False) -> bool:
    """Recognize all six reviewed unique bindings, independent of Docker's list order."""
    if type(vulnerable_control) is not bool:
        return False
    expected = list(_CADDY_SYNTHETIC_ENVIRONMENT)
    if vulnerable_control:
        expected[3] = "CADDY_VERSION=v2.11.4"
    return (
        type(value) is list
        and len(value) == 6
        and all(type(entry) is str for entry in value)
        and Counter(value) == Counter(expected)
    )


# This is a second, finite runtime contour. CADDY_D_CONFIG remains byte-for-byte static.
CADDY_UPGRADE_CONFIG = (
    b'{"admin":{"disabled":true,"config":{"persist":false}},"apps":{"http":{"servers":'
    b'{"ci":{"listen":["127.0.0.1:18080"],"automatic_https":{"disable":true},'
    b'"routes":[{"match":[{"path":["/ws"]}],"handle":[{"handler":"reverse_proxy",'
    b'"upstreams":[{"dial":"127.0.0.1:18081"}],"transport":{"protocol":"http",'
    b'"dial_timeout":2000000000,"response_header_timeout":5000000000}}]},'
    b'{"handle":[{"handler":"static_response","body":'
    b'"pulseplate-caddy-D\\nHOME={env.HOME}\\nTMPDIR={env.TMPDIR}\\n"}]}]}}}}}\n'
)


def _caddy_upgrade_cases() -> dict[str, tuple[bytes, bytes, bool]]:
    """Closed synthetic HTTP/1.1 cases; no general network-protocol parser or generator."""
    request = (
        b"GET /ws HTTP/1.1\r\nHost: localhost\r\nConnection: Upgrade\r\n"
        b"Upgrade: websocket\r\nSec-WebSocket-Version: 13\r\n"
        b"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n\r\n"
    )
    preserved = (
        b"X-End-To-End: first\r\nx-end-to-end: second\r\n"
        b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n"
    )
    hop = (
        b"X-Strip-One: first-secret\r\nX-Strip-Two: second-secret\r\n"
        b'Alt-Svc: h3=":443"\r\n'
        b"Keep-Alive: timeout=5\r\nProxy-Connection: keep-alive\r\n"
        b"Proxy-Authenticate: synthetic\r\nProxy-Authorization: synthetic\r\n"
        b"Te: trailers\r\nTrailer: X-Trailer\r\n"
    )
    response = (
        b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
        b"Connection: Upgrade, X-Strip-One, X-Strip-Two\r\n" + hop + preserved + b"\r\n"
    )
    duplicate = response.replace(
        b"Connection: Upgrade, X-Strip-One, X-Strip-Two\r\n",
        b"Connection: Upgrade, X-Strip-One\r\ncOnNeCtIoN: X-Strip-Two, uPgRaDe\r\n",
    )
    return {
        "upgrade": (request, response, True),
        "duplicate-connection": (request, duplicate, True),
        "ordinary-200": (
            request.replace(b"Connection: Upgrade", b"Connection: close").replace(
                b"Upgrade: websocket\r\n", b""
            ),
            b"HTTP/1.1 200 OK\r\nContent-Length: 15\r\n"
            b"Connection: close, X-Strip-One, X-Strip-Two\r\n"
            + hop
            + b"X-End-To-End: first\r\nx-end-to-end: second\r\n\r\nordinary-body\r\n",
            False,
        ),
        "missing-upgrade": (request, response.replace(b"Upgrade: websocket\r\n", b""), False),
        "mismatched-upgrade": (
            request,
            response.replace(b"Upgrade: websocket\r\n", b"Upgrade: h2c\r\n"),
            False,
        ),
        "invalid-upgrade": (
            request,
            response.replace(b"Upgrade: websocket\r\n", b"Upgrade: \x80\r\n"),
            False,
        ),
        "no-request-upgrade": (
            request.replace(b"Connection: Upgrade", b"Connection: close").replace(
                b"Upgrade: websocket\r\n", b""
            ),
            response,
            False,
        ),
    }


def _caddy_websocket_frame(payload: bytes, *, masked: bool) -> bytes:
    """One short, final text frame for the two literal ASCII sentinels."""
    if payload not in (b"PP2494-client", b"PP2494-server"):
        raise ValueError("Caddy fixture sentinel differs")
    if not masked:
        return bytes((0x81, len(payload))) + payload
    mask = b"\x13\x57\x9b\xdf"
    return (
        bytes((0x81, 0x80 | len(payload)))
        + mask
        + bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
    )


_CADDY_UPGRADE_GUEST = r"""
set -eu
set -o pipefail
cd /run/pulseplate-caddy-tmp
mkdir "$1"
cd "$1"
ulimit -f 8
server_pid=
client_pid=
finish() {
  primary=$?
  trap - EXIT HUP INT TERM
  set +e
  for role in server client; do
    if [ "$role" = server ]; then pid=$server_pid; else pid=$client_pid; fi
    stop=255
    if [ -n "$pid" ]; then kill -STOP "$pid" 2>stop-"$role".stderr; stop=$?; fi
    printf '%s\n' "$stop" >stop-"$role".result
  done
  for role in server client; do
    if [ "$role" = server ]; then pid=$server_pid; else pid=$client_pid; fi
    killed=255
    if [ -n "$pid" ]; then kill -KILL "$pid" 2>kill-"$role".stderr; killed=$?; fi
    waited=255
    if [ -n "$pid" ]; then wait "$pid" 2>wait-"$role".stderr; waited=$?; fi
    printf 'TERMINAL role=%s stop=%s kill=%s wait=%s\n' \
      "$role" "$(cat stop-"$role".result)" "$killed" "$waited"
  done
  capture=0
  for channel in server-received client-received server-stderr client-stderr \
      stop-server.stderr stop-client.stderr kill-server.stderr kill-client.stderr \
      wait-server.stderr wait-client.stderr; do
    if [ ! -f "$channel" ]; then
      printf 'FILE name=%s missing=1\n' "$channel"
      capture=1
      continue
    fi
    bytes=$(wc -c <"$channel")
    if [ "$bytes" -gt 8192 ]; then capture=1; fi
    hex=$(head -c 8192 "$channel" | od -An -v -tx1 | tr -d ' \n')
    if [ "$?" -ne 0 ]; then capture=1; fi
    printf 'FILE name=%s bytes=%s hex=%s\n' "$channel" "$bytes" "$hex"
  done
  printf 'RESULT primary=%s capture=%s\n' "$primary" "$capture"
  if [ "$primary" -ne 0 ]; then exit "$primary"; fi
  exit "$capture"
}
trap finish EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
for file in server-received client-received server-stderr client-stderr \
    stop-server.stderr stop-client.stderr kill-server.stderr kill-client.stderr \
    wait-server.stderr wait-client.stderr; do : >"$file"; done
mkfifo server-in client-in
exec 3<>server-in
exec 4<>client-in
/bin/busybox nc -l -p 18081 -s 127.0.0.1 <server-in >server-received 2>server-stderr 3>&- 4>&- &
server_pid=$!
i=0
until /bin/busybox awk '$2 == "0100007F:46A1" && $4 == "0A" { found=1 } END { exit !found }' /proc/net/tcp; do
  i=$((i+1)); [ "$i" -le 4 ]; sleep 1
done
/bin/busybox nc 127.0.0.1 18080 <client-in >client-received 2>client-stderr 3>&- 4>&- &
client_pid=$!
printf '%b' "$2" >&4
i=0
until od -An -v -tx1 server-received | tr -d ' \n' | grep -q '0d0a0d0a'; do
  i=$((i+1)); [ "$i" -le 4 ]; sleep 1
done
printf '%b' "$3" >&3
i=0
until od -An -v -tx1 client-received | tr -d ' \n' | grep -q '0d0a0d0a'; do
  i=$((i+1)); [ "$i" -le 4 ]; sleep 1
done
if [ "$4" = duplex ]; then
  printf '%b' "$5" >&4
  printf '%b' "$6" >&3
  i=0
  until od -An -v -tx1 server-received | tr -d ' \n' | grep -q "$7" &&
      od -An -v -tx1 client-received | tr -d ' \n' | grep -q "$8"; do
    i=$((i+1)); [ "$i" -le 4 ]; sleep 1
  done
elif [ "$1" = ordinary-200 ]; then
  i=0
  until od -An -v -tx1 client-received | tr -d ' \n' | grep -q '6f7264696e6172792d626f64790d0a'; do
    i=$((i+1)); [ "$i" -le 4 ]; sleep 1
  done
fi
exit 0
"""


def _caddy_fixture_http(raw: bytes) -> tuple[bytes, list[tuple[bytes, bytes]], bytes]:
    """Read one bounded fixture message, preserving all repeated native headers."""
    if len(raw) > 8192 or b"\r\n\r\n" not in raw:
        raise ValueError("Caddy fixture missing or oversized HTTP header")
    head, body = raw.split(b"\r\n\r\n", 1)
    lines = head.split(b"\r\n")
    headers = []
    for line in lines[1:]:
        if b":" not in line or line[:1] in (b" ", b"\t"):
            raise ValueError("Caddy fixture malformed header")
        name, value = line.split(b":", 1)
        if re.fullmatch(rb"[A-Za-z0-9-]+", name) is None:
            raise ValueError("Caddy fixture malformed header name")
        headers.append((name.lower(), value.strip(b" \t")))
    return lines[0], headers, body


def _validate_caddy_upgrade_exchange(
    case: str, raw: bytes, *, vulnerable_control: bool
) -> dict[str, object]:
    cases = _caddy_upgrade_cases()
    if case not in cases:
        raise ValueError("Caddy fixture case differs")
    _, _, duplex = cases[case]
    lines = raw.decode("ascii").splitlines()
    files: dict[str, bytes] = {}
    roles: dict[str, tuple[int, int, int]] = {}
    expected_files = {
        "server-received",
        "client-received",
        "server-stderr",
        "client-stderr",
        "stop-server.stderr",
        "stop-client.stderr",
        "kill-server.stderr",
        "kill-client.stderr",
        "wait-server.stderr",
        "wait-client.stderr",
    }
    for line in lines[:-1]:
        terminal = re.fullmatch(
            r"TERMINAL role=(server|client) stop=([0-9]+) kill=([0-9]+) wait=([0-9]+)", line
        )
        channel = re.fullmatch(r"FILE name=([a-z.-]+) bytes=([0-9]+) hex=([0-9a-f]*)", line)
        if terminal:
            name = terminal[1]
            if name in roles:
                raise ValueError("Caddy fixture duplicate role")
            roles[name] = (int(terminal[2]), int(terminal[3]), int(terminal[4]))
        elif channel:
            name, size = channel[1], int(channel[2])
            data = bytes.fromhex(channel[3])
            if name in files or name not in expected_files or size != len(data) or size > 8192:
                raise ValueError("Caddy fixture channel binding differs")
            files[name] = data
        else:
            raise ValueError("Caddy fixture unrecognized native output")
    if (
        len(lines) != 13
        or lines[-1] != "RESULT primary=0 capture=0"
        or set(files) != expected_files
        or set(roles) != {"server", "client"}
    ):
        raise ValueError("Caddy fixture incomplete native terminal result")
    for name, result in roles.items():
        natural_exit = result[2] == 0 and all(code in (0, 1) for code in result[:2])
        if result != (0, 0, 137) and (duplex or not natural_exit):
            raise ValueError("Caddy fixture role did not terminate as expected")
        if result == (0, 0, 137):
            if (
                files["stop-" + name + ".stderr"]
                or files["kill-" + name + ".stderr"]
                or files["wait-" + name + ".stderr"] != b"Killed\n"
            ):
                raise ValueError("Caddy fixture controlled termination diagnostics differ")
        elif files["wait-" + name + ".stderr"]:
            raise ValueError("Caddy fixture natural termination diagnostic")
    if files["server-stderr"] or files["client-stderr"]:
        raise ValueError("Caddy fixture socket diagnostic")
    request, request_headers, sent = _caddy_fixture_http(files["server-received"])
    status, headers, received = _caddy_fixture_http(files["client-received"])
    if request != b"GET /ws HTTP/1.1":
        raise ValueError("Caddy fixture did not traverse /ws reverse_proxy")

    def values(name: bytes) -> list[bytes]:
        return [value for key, value in headers if key == name]

    if duplex:
        if (
            status != b"HTTP/1.1 101 Switching Protocols"
            or values(b"upgrade") != [b"websocket"]
            or values(b"sec-websocket-accept") != [b"s3pPLMBiTxaQ9kYGzzhZRbK+xOo="]
            or sent != _caddy_websocket_frame(b"PP2494-client", masked=True)
            or received != _caddy_websocket_frame(b"PP2494-server", masked=False)
            or [v.lower() for k, v in request_headers if k == b"upgrade"] != [b"websocket"]
        ):
            raise ValueError("Caddy fixture valid 101 or real duplex frames differ")
    elif status != b"HTTP/1.1 200 OK" or sent:
        # The selected Caddy source returns without writing a response on a rejected
        # backend upgrade; the HTTP server emits an empty 200, never a tunnel.
        raise ValueError("Caddy fixture rejection/ordinary response differs")
    elif received != (b"ordinary-body\r\n" if case == "ordinary-200" else b""):
        raise ValueError("Caddy fixture unexpected ordinary/rejected body")
    if case == "ordinary-200" and values(b"content-length") != [b"15"]:
        raise ValueError("Caddy fixture ordinary response length differs")
    if duplex or case == "ordinary-200":
        if values(b"x-end-to-end") != [b"first", b"second"]:
            raise ValueError("Caddy fixture end-to-end header multiplicity differs")
    elif values(b"upgrade") or values(b"sec-websocket-accept"):
        raise ValueError("Caddy fixture rejected upgrade leaked handshake")
    blocked = {
        b"alt-svc",
        b"x-strip-one",
        b"x-strip-two",
        b"keep-alive",
        b"proxy-connection",
        b"proxy-authenticate",
        b"proxy-authorization",
        b"te",
        b"trailer",
        b"transfer-encoding",
    }
    if vulnerable_control and duplex:
        if values(b"x-strip-one") != [b"first-secret"] or values(b"x-strip-two") != [
            b"second-secret"
        ]:
            raise ValueError("Caddy vulnerable control did not positively reproduce header leak")
    else:
        if any(name in blocked for name, _ in headers):
            raise ValueError("Caddy upstream hop-by-hop header leaked")
        if duplex and values(b"connection") != [b"Upgrade"]:
            raise ValueError("Caddy canonical upgrade Connection differs")
    return {
        "case": case,
        "duplex": duplex,
        "roles": roles,
        "native_stdout_sha256": hashlib.sha256(raw).hexdigest(),
        "request_sha256": hashlib.sha256(files["server-received"]).hexdigest(),
        "response_sha256": hashlib.sha256(files["client-received"]).hexdigest(),
        "vulnerable_leak_reproduced": vulnerable_control and duplex,
    }


def _observe_caddy_upgrade_exchanges(
    name: str, directory: Path, *, vulnerable_control: bool
) -> list[dict[str, object]]:
    from scripts.ci.prometheus_source_image import Native

    if DOCKER_BINARY is None or not Path(DOCKER_BINARY).is_absolute() or _CADDY_REMAINING is None:
        raise ValueError("Caddy upgrade requires the existing bounded native runtime phase")
    workspace = directory / "upgrade-native"
    workspace.mkdir(mode=0o700)
    config = workspace / "docker-config"
    config.mkdir(mode=0o700)
    native = Native(workspace, time.monotonic() + _CADDY_REMAINING(float("inf")), 0)
    environment = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(workspace.resolve()),
        "DOCKER_CONFIG": str(config.resolve()),
        "LANG": "C.UTF-8",
    }
    results = []
    client_frame = _caddy_websocket_frame(b"PP2494-client", masked=True)
    server_frame = _caddy_websocket_frame(b"PP2494-server", masked=False)

    def octal(value: bytes) -> str:
        return "".join("\\0" + format(byte, "03o") for byte in value)

    primary_error: BaseException | None = None
    try:
        for case, (request, response, duplex) in _caddy_upgrade_cases().items():
            # The historical image is a positive leak/duplex control, not a new
            # compatibility promise for its different invalid-upgrade behavior.
            if vulnerable_control and not duplex:
                continue
            raw = native.run(
                [
                    DOCKER_BINARY,
                    "--config",
                    str(config.resolve()),
                    "exec",
                    name,
                    "/bin/busybox",
                    "sh",
                    "-c",
                    _CADDY_UPGRADE_GUEST,
                    "fixture",
                    case,
                    octal(request),
                    octal(response),
                    "duplex" if duplex else "ordinary",
                    octal(client_frame),
                    octal(server_frame),
                    client_frame.hex(),
                    server_frame.hex(),
                ],
                case,
                environment,
                cwd=directory.resolve(),
                maximum_seconds=35,
                output_bound=65536,
            )
            if (workspace / (case + ".stderr")).read_bytes():
                raise ValueError("Caddy upgrade guest emitted unexpected stderr")
            results.append(
                _validate_caddy_upgrade_exchange(case, raw, vulnerable_control=vulnerable_control)
            )
    except BaseException as error:
        primary_error = error
    finally:
        try:
            with (workspace / "native-records.json").open("x", encoding="utf-8") as stream:
                json.dump(native.records, stream, indent=2)
        except BaseException as capture_error:
            if primary_error is None:
                primary_error = capture_error
            else:
                primary_error.add_note(
                    "Caddy upgrade record capture also failed: " + type(capture_error).__name__
                )
        try:
            config.rmdir()
        except BaseException as cleanup_error:
            if primary_error is None:
                primary_error = cleanup_error
            else:
                primary_error.add_note(
                    "Caddy upgrade config cleanup also failed: " + type(cleanup_error).__name__
                )
    if primary_error is not None:
        raise primary_error
    return results


def observe_caddy_ci_runtime(
    image: str, directory: Path, *, upgrade: bool = False, vulnerable_control: bool = False
) -> dict[str, object]:
    """Bind two serving-process values and isolated storage, never a deployed service."""
    global _CADDY_REMAINING
    if re.fullmatch(r"sha256:[0-9a-f]{64}", image) is None:
        raise ValueError("Caddy runtime requires an immutable local image ID")
    if (
        type(upgrade) is not bool
        or type(vulnerable_control) is not bool
        or (vulnerable_control and not upgrade)
    ):
        raise ValueError("Caddy runtime contour differs")
    selected_config = CADDY_UPGRADE_CONFIG if upgrade else CADDY_D_CONFIG
    config = directory / "loaded-ci-config.json"
    with config.open("xb") as stream:
        stream.write(selected_config)
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
            or not _is_caddy_synthetic_environment(
                prepared_config.get("Env"), vulnerable_control=vulnerable_control
            )
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
            loaded != selected_config
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
        if upgrade:
            phase, observed_channels = "normal-upgrade", ()
            evidence["upgrade_exchanges"] = _observe_caddy_upgrade_exchanges(
                name, directory, vulnerable_control=vulnerable_control
            )
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
        if not _is_caddy_synthetic_environment(
            inspected["Config"].get("Env"), vulnerable_control=vulnerable_control
        ):
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
                if _is_caddy_synthetic_environment(
                    current["Config"].get("Env"), vulnerable_control=vulnerable_control
                ):
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


def _caddy_stdlib_require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError("Caddy stdlib: " + message)


def _caddy_stdlib_custom_identities(tops: set[str]) -> set[str]:
    result = set(tops)
    for top in tops:
        result.update(top + "/" + suffix for suffix in CADDY_STDLIB_CUSTOM_SUBTESTS.get(top, ()))
    return result


def validate_caddy_stdlib_tests(raw: bytes, phase: str) -> dict[str, Any]:
    """Validate bounded phase-specific native events within final source-proof admission."""
    from scripts.ci.prometheus_source_image import decode_objects

    _caddy_stdlib_require(
        phase in {"baseline-controls", "baseline-red", "patched-tests"}, "native phase"
    )
    events = decode_objects(raw)
    red = phase == "baseline-red"
    custom = (
        {"TestPPHTTPConnectionBaseline"}
        if red
        else (
            CADDY_STDLIB_BASELINE_CUSTOM
            if phase == "baseline-controls"
            else set(CADDY_STDLIB_CUSTOM_TOPS)
        )
    )
    required_tops = {"net/http": custom | (set() if red else set(CADDY_STDLIB_UPSTREAM_TOPS))}
    if not red:
        required_tops["net/http/httputil"] = {"TestReverseProxyStripHeadersPresentInConnection"}
    starts: Counter[str] = Counter()
    runs: Counter[tuple[str, str]] = Counter()
    passes: Counter[tuple[str, str]] = Counter()
    fails: Counter[tuple[str, str]] = Counter()
    package_pass: Counter[str] = Counter()
    package_fail: Counter[str] = Counter()
    outputs: list[str] = []
    for event in events:
        _caddy_stdlib_require(
            type(event) is dict and event.get("Package") in required_tops, "native_package_identity"
        )
        action = event.get("Action")
        package = event["Package"]
        name = event.get("Test")
        _caddy_stdlib_require(
            action in {"start", "run", "pause", "cont", "output", "pass", "fail"},
            "native_unexpected_action_or_skip",
        )
        if name is not None:
            _caddy_stdlib_require(
                type(name) is str and name.split("/", 1)[0] in required_tops[package],
                "native_test_identity",
            )
        if action == "start":
            _caddy_stdlib_require(name is None, "package_start_shape")
            starts[package] += 1
        elif action == "run":
            _caddy_stdlib_require(
                name is not None
                and starts[package] == 1
                and not runs[(package, name)]
                and not package_pass[package]
                and not package_fail[package],
                "test_run_shape_order",
            )
            runs[(package, name)] += 1
        elif action in {"pass", "fail"}:
            if name is None:
                _caddy_stdlib_require(
                    starts[package] == 1
                    and not package_pass[package]
                    and not package_fail[package]
                    and all(p != package or passes[(p, n)] + fails[(p, n)] == 1 for p, n in runs),
                    "package_terminal_order",
                )
                (package_pass if action == "pass" else package_fail)[package] += 1
            else:
                _caddy_stdlib_require(
                    runs[(package, name)] == 1
                    and not passes[(package, name)]
                    and not fails[(package, name)]
                    and not package_pass[package]
                    and not package_fail[package],
                    "test_terminal_order",
                )
                (passes if action == "pass" else fails)[(package, name)] += 1
        elif action == "output":
            _caddy_stdlib_require(type(event.get("Output")) is str, "output_shape")
            outputs.append(event["Output"])
    _caddy_stdlib_require(
        starts == Counter({p: 1 for p in required_tops}), "complete_package_starts"
    )
    _caddy_stdlib_require(runs and all(n == 1 for n in runs.values()), "unique_native_runs")
    _caddy_stdlib_require(
        all(n == 1 for n in (passes + fails).values())
        and set(runs) == set(passes) | set(fails)
        and not (set(passes) & set(fails)),
        "unique_terminal_pairs",
    )
    for package, tops in required_tops.items():
        actual_tops = {name for pkg, name in runs if pkg == package and "/" not in name}
        _caddy_stdlib_require(actual_tops == tops, "complete_exact_top_inventory")
    actual_custom = {
        name for pkg, name in runs if pkg == "net/http" and name.startswith("TestPPHTTP")
    }
    _caddy_stdlib_require(
        actual_custom == _caddy_stdlib_custom_identities(custom),
        "A6_S2_exact_custom_top_subtest_inventory",
    )
    text = "".join(outputs)
    if red:
        expected = {("net/http", "TestPPHTTPConnectionBaseline")}
        _caddy_stdlib_require(
            set(fails) == expected
            and not passes
            and package_fail == Counter({"net/http": 1})
            and not package_pass,
            "exact_expected_RED",
        )
        _caddy_stdlib_require(
            text.count("PP_BASELINE_SETUP_BODY_CLOSE_OK\n") == 1
            and text.count('PP_EXPECTED_NOMINATION_MISMATCH: got=[] want=["X-A" "X-B"]\n') == 1,
            "RED_setup_and_specific_assertion",
        )
        _caddy_stdlib_require(
            all(
                word not in text
                for word in (
                    "PP_BASELINE_SETUP_OR_BODY_CLOSE_FAILURE",
                    "PP_SETUP_READ",
                    "PP_BODY_CLOSE",
                    "panic:",
                    "test timed out",
                    "build failed",
                    "[build failed]",
                )
            ),
            "RED_not_infrastructure",
        )
    else:
        _caddy_stdlib_require(
            not fails
            and not package_fail
            and package_pass == Counter({p: 1 for p in required_tops}),
            "all_selected_packages_PASS",
        )
    parity: list[str] = []
    rejections: list[str] = []
    headers: list[str] = []
    for line in text.splitlines():
        for marker, target in (
            ("PP_ACCEPTED_PARITY ", parity),
            ("PP_READER_REJECT ", rejections),
            ("PP_ACCEPTED_HEADER ", headers),
        ):
            if marker in line:
                _caddy_stdlib_require(line.count(marker) == 1, "parity_marker_unique")
                target.append(line[line.index(marker) :])
    if not red:
        _caddy_stdlib_require(
            len(parity) == 4
            and len(set(parity)) == 4
            and len(rejections) == 6
            and len(set(rejections)) == 6
            and len(headers) == 4,
            "complete_malformed_controls",
        )
        for case in CADDY_STDLIB_CUSTOM_SUBTESTS["TestPPHTTPMalformedAcceptedParity"]:
            wanted = (
                f'PP_ACCEPTED_PARITY name={case} close=false length=0 body="" error=<nil> field=["x"]'
                if case == "legacy_space_field_name"
                else f'PP_ACCEPTED_PARITY name={case} close=true length=1 body="x" error=<nil>'
            )
            _caddy_stdlib_require(wanted in parity, "accepted_framing_parity")
        for case in CADDY_STDLIB_CUSTOM_SUBTESTS["TestPPHTTPMalformedReaderControls"]:
            _caddy_stdlib_require(
                sum(x.startswith("PP_READER_REJECT name=" + case + " error=") for x in rejections)
                == 1,
                "reader_rejection_case",
            )
        for case in CADDY_STDLIB_CUSTOM_SUBTESTS["TestPPHTTPMalformedAcceptedParity"]:
            value = (
                "[]"
                if phase == "baseline-controls" or case == "legacy_space_field_name"
                else (
                    '["cloſe" "\\"close\\"" "close;parameter"]'
                    if case == "opaque_obs_text"
                    else '["X-A"]'
                )
            )
            _caddy_stdlib_require(
                "PP_ACCEPTED_HEADER name=" + case + " values=" + value in headers,
                "accepted_header_observation",
            )
    return {
        "runs": [[p, n] for p, n in sorted(runs)],
        "passes": [[p, n] for p, n in sorted(passes)],
        "fails": [[p, n] for p, n in sorted(fails)],
        "package_pass": dict(package_pass),
        "package_fail": dict(package_fail),
        "parity": sorted(parity),
        "reader_rejections": sorted(rejections),
        "accepted_headers": sorted(headers),
    }


def _caddy_stdlib_list(raw: bytes) -> list[str]:
    lines = raw.decode("utf-8").splitlines()
    names = [line for line in lines if line.startswith("Test")]
    _caddy_stdlib_require(
        len(names) == len(set(names))
        and set(names)
        == set(CADDY_STDLIB_UPSTREAM_TOPS)
        | set(CADDY_STDLIB_CUSTOM_TOPS)
        | {"TestReverseProxyStripHeadersPresentInConnection"},
        "exact_native_list",
    )
    rest = [line for line in lines if not line.startswith("Test")]
    _caddy_stdlib_require(
        len(rest) == 2
        and all(
            re.fullmatch(r"ok[ \t]+net/http(?:/httputil)?[ \t]+[0-9.]+s", line) for line in rest
        )
        and any(re.match(r"ok[ \t]+net/http[ \t]", line) for line in rest)
        and any(re.match(r"ok[ \t]+net/http/httputil[ \t]", line) for line in rest),
        "native_list_package_results",
    )
    return sorted(names)


def caddy_stdlib_test_argv(phase: str) -> list[str]:
    """Exact offline component selections, also used by the existing producer contract."""
    all_names = [
        *CADDY_STDLIB_UPSTREAM_TOPS,
        *CADDY_STDLIB_CUSTOM_TOPS,
        "TestReverseProxyStripHeadersPresentInConnection",
    ]
    selected = all_names
    if phase == "baseline-controls":
        selected = [
            *CADDY_STDLIB_UPSTREAM_TOPS,
            *sorted(CADDY_STDLIB_BASELINE_CUSTOM),
            "TestReverseProxyStripHeadersPresentInConnection",
        ]
    elif phase == "baseline-red":
        selected = ["TestPPHTTPConnectionBaseline"]
    elif phase not in {"baseline-list", "patched-list", "patched-tests"}:
        raise ValueError("Caddy stdlib: unknown phase")
    pattern = "^(" + "|".join(selected) + ")$"
    command = ["/usr/local/go/bin/go", "test", "-count=1", "-p=2"]
    if phase.endswith("-list"):
        command += ["-list", pattern]
    else:
        command += ["-parallel=2", "-timeout=90s", "-json", "-run", pattern]
    return command + (
        ["net/http"] if phase == "baseline-red" else ["net/http", "net/http/httputil"]
    )


def caddy_stdlib_inputs() -> bytes:
    paths = {
        "/opt/go1.26.10-http-connection-nominations.patch": CADDY_STDLIB_PATCH_SHA256,
        "/opt/go_http_connection_nominations_test.go": CADDY_STDLIB_FIXTURE_SHA256,
        "/usr/local/go/bin/go": CADDY_GO_BINARY_SHA256,
        "/usr/local/go/src/net/http/transfer.go": CADDY_STDLIB_BEFORE_SHA256,
        CADDY_STDLIB_ROOT + "/src/net/http/transfer.go": CADDY_STDLIB_AFTER_SHA256,
        **{"/usr/local/go/" + path: digest for path, digest in CADDY_STDLIB_HELPERS.items()},
    }
    return "".join(sorted(digest + "  " + path + "\n" for path, digest in paths.items())).encode()


def caddy_stdlib_commands() -> bytes:
    """Closed producer record; statuses come from actual shell execution."""
    rows = []
    for phase in (
        "baseline-list",
        "baseline-controls",
        "baseline-red",
        "patched-list",
        "patched-tests",
    ):
        stage = "baseline" if phase.startswith("baseline") else "patched"
        root = CADDY_STDLIB_BASELINE_ROOT if stage == "baseline" else CADDY_STDLIB_ROOT
        rows.append(
            "\t".join(
                (
                    phase,
                    "1" if phase == "baseline-red" else "0",
                    root,
                    "/opt/caddy-stdlib-" + stage + "-cache",
                    "off",
                    "off",
                    json.dumps(caddy_stdlib_test_argv(phase), separators=(",", ":")),
                )
            )
            + "\n"
        )
    return "".join(rows).encode()


def _validate_caddy_stdlib_evidence(data: dict[str, bytes], recipe: bytes) -> dict[str, Any]:
    require = _caddy_stdlib_require
    groups = (
        (
            ("stdlib-original-tree.sha256", "stdlib-original-post-build-tree.sha256"),
            CADDY_STDLIB_ORIGINAL_TREE,
            CADDY_STDLIB_ORIGINAL_COUNT,
        ),
        (
            ("stdlib-baseline-tree.sha256",),
            CADDY_STDLIB_BASELINE_TREE,
            CADDY_STDLIB_ORIGINAL_COUNT + 1,
        ),
        (
            (
                "stdlib-patched-tree.sha256",
                "stdlib-post-tests-tree.sha256",
                "stdlib-post-build-tree.sha256",
            ),
            CADDY_STDLIB_PATCHED_TREE,
            CADDY_STDLIB_ORIGINAL_COUNT + 1,
        ),
    )
    inventories = {}
    for names, digest, count in groups:
        for name in names:
            raw = data[name]
            require(
                hashlib.sha256(raw).hexdigest() == digest and raw.endswith(b"\n"),
                "complete tree identity",
            )
            lines = raw.decode("utf-8").splitlines()
            require(
                len(lines) == count and len(set(lines)) == count and lines == sorted(lines),
                "complete sorted tree records",
            )
            entries = {}
            for line in lines:
                match = re.fullmatch(r"([0-9a-f]{64})  \./([^\x00\r\n]+)", line)
                if match is None:
                    raise ValueError("Caddy stdlib: tree record syntax")
                path = match[2]
                require(
                    not PurePosixPath(path).is_absolute()
                    and ".." not in PurePosixPath(path).parts
                    and str(PurePosixPath(path)) == path
                    and "\\" not in path
                    and path not in entries,
                    "tree path identity",
                )
                entries[path] = match[1]
            inventories[name] = entries
    original = inventories["stdlib-original-tree.sha256"]
    baseline = inventories["stdlib-baseline-tree.sha256"]
    patched = inventories["stdlib-patched-tree.sha256"]
    fixture = "src/net/http/go_http_connection_nominations_test.go"
    transfer = "src/net/http/transfer.go"
    require(
        fixture not in original and baseline == {**original, fixture: CADDY_STDLIB_FIXTURE_SHA256},
        "baseline sole fixture addition",
    )
    require(
        baseline.get(transfer) == CADDY_STDLIB_BEFORE_SHA256
        and patched == {**baseline, transfer: CADDY_STDLIB_AFTER_SHA256},
        "patched sole transfer delta",
    )
    require(data["stdlib-inputs.sha256"] == caddy_stdlib_inputs(), "exact stdlib inputs")
    require(
        data["stdlib-test-commands.txt"] == caddy_stdlib_commands(),
        "actual source cache command exit binding",
    )
    inventory = data["stdlib-test-inventory.txt"]
    require(
        inventory.startswith(b"BASELINE_NATIVE_LIST\n")
        and inventory.count(b"PATCHED_NATIVE_LIST\n") == 1,
        "two native lists",
    )
    before, after = inventory.removeprefix(b"BASELINE_NATIVE_LIST\n").split(
        b"PATCHED_NATIVE_LIST\n"
    )
    require(_caddy_stdlib_list(before) == _caddy_stdlib_list(after), "native list equality")
    baseline_tests = validate_caddy_stdlib_tests(
        data["stdlib-baseline-controls.jsonl"], "baseline-controls"
    )
    red = validate_caddy_stdlib_tests(data["stdlib-baseline-red.jsonl"], "baseline-red")
    patched_tests = validate_caddy_stdlib_tests(data["stdlib-patched-tests.jsonl"], "patched-tests")
    require(
        baseline_tests["parity"] == patched_tests["parity"]
        and baseline_tests["reader_rejections"] == patched_tests["reader_rejections"],
        "finite malformed parity",
    )
    for witness in (
        ("ENV GOROOT=" + CADDY_STDLIB_ROOT).encode(),
        b"GOCACHE=/opt/caddy-stdlib-patched-cache",
        CADDY_STDLIB_PATCH_SHA256.encode(),
        CADDY_STDLIB_FIXTURE_SHA256.encode(),
        CADDY_STDLIB_BEFORE_SHA256.encode(),
        CADDY_STDLIB_AFTER_SHA256.encode(),
        b"apply --no-index --check --whitespace=error-all /opt/go1.26.10-http-connection-nominations.patch",
        b"apply --no-index --whitespace=error-all /opt/go1.26.10-http-connection-nominations.patch",
    ):
        require(witness in recipe, "stdlib producer recipe binding")
    require(
        recipe.index(b"go build -mod=readonly") < recipe.index(b"stdlib-post-build-tree.sha256"),
        "post-Caddy snapshot order",
    )
    return {
        "patched_goroot": CADDY_STDLIB_ROOT,
        "compiler_sha256": CADDY_GO_BINARY_SHA256,
        "custom_stdlib": True,
        "baseline_controls": baseline_tests,
        "baseline_red": red,
        "patched_tests": patched_tests,
    }


def validate_caddy_source_evidence(
    directory: Path,
    *,
    binary_metadata: bytes,
    binary_sha256: str,
    recipe: bytes,
) -> dict[str, object]:
    """Recognize the closed v3/stdlib source proof; execution belongs to its producer."""
    from scripts.ci.prometheus_source_image import decode_objects

    def require(condition: object, message: str) -> None:
        if not condition:
            raise ValueError("Caddy source: " + message)

    require(directory.is_dir() and not directory.is_symlink(), "evidence directory")
    require({path.name for path in directory.iterdir()} == CADDY_BUILD_MEMBERS, "closed 28 members")
    data = {}
    for name in sorted(CADDY_BUILD_MEMBERS):
        path = directory / name
        info = path.lstat()
        require(
            stat.S_ISREG(info.st_mode)
            and info.st_nlink == 1
            and 0 < info.st_size <= CADDY_STDLIB_MEMBER_LIMITS.get(name, 2097152),
            "regular bounded member",
        )
        data[name] = path.read_bytes()
        require(len(data[name]) == info.st_size, "member read drift")
    require(
        sum(len(data[name]) for name in CADDY_V3_BUILD_MEMBERS) <= CADDY_V3_TOTAL_BYTES,
        "original v3 aggregate bytes",
    )
    require(
        sum(len(data[name]) for name in CADDY_STDLIB_MEMBERS) <= CADDY_STDLIB_TOTAL_BYTES,
        "stdlib aggregate bytes",
    )
    require(sum(map(len, data.values())) <= CADDY_SOURCE_TOTAL_BYTES, "combined aggregate bytes")
    stdlib = _validate_caddy_stdlib_evidence(data, recipe)
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
            location.startswith((CADDY_STDLIB_ROOT + "/src/", "/go/pkg/mod/", CADDY_PATCHED_ROOT))
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
        if location.startswith(CADDY_STDLIB_ROOT + "/src/"):
            require(location == CADDY_STDLIB_ROOT + "/src/" + package, "standard library directory")
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
        "stdlib_source": stdlib,
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
