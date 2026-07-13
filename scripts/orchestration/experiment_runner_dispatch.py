#!/usr/bin/env python3
"""Strict execution-backend dispatcher for the PulsePlate Experiment Runner.

The dispatcher is deliberately a local evidence tool.  It selects one backend
before an experiment starts, proves the backend's isolation properties, and
never retries an experiment with a weaker backend or network policy.
"""

from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from dataclasses import dataclass
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess  # nosec B404: bounded absolute runtime/git argv only (remove-by: 2026-10-31, ref: ledger-p1-experiment-runner-macos-strict-backend)
import sys
import tempfile
import threading
from typing import Any, Iterator
import uuid

DISPATCH_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(DISPATCH_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(DISPATCH_REPO_ROOT))

from scripts.orchestration.context_pack import REPO_ROOT
from scripts.orchestration.experiment_contract import (
    IMAGE_DIGEST_RE,
    ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
    validate_experiment_packet,
    validate_experiment_result,
)

CAPABILITY_SCHEMA_VERSION = "1.0"
CAPABILITY_ARTIFACT_TYPE = "experiment_runner_backend_capability.v1"
CAPABILITY_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "capabilities"
RESULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "results"
CONTAINERFILE = REPO_ROOT / "deploy" / "experiment-runner" / "Containerfile"

BACKENDS = ("auto", "apple-container", "docker", "native-linux")
CONTAINER_BACKENDS = ("apple-container", "docker")
CPU_LIMIT = "2"
MEMORY_LIMIT = "4g"
TMPFS_SIZE = "1g"
APPLE_TMPFS_SIZE = "1G"
CONTAINER_PYTHON = "/opt/venv/bin/python"
CONTAINER_UNSHARE = "/usr/bin/unshare"
CONTAINER_REPO = "/repo"
CONTAINER_INPUT = "/repo/.experiment-runner-input"
CONTAINER_RESULT_DIR = "/repo/artifacts/orchestration/experiments/results"
CONTAINER_PRIVATE_TMP = Path("/", "tmp").as_posix()
RESULT_VOLUME_SIZE = "64M"
MAX_RESULT_BYTES = 2 * 1024 * 1024
IMAGE_REF_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._:/-]{0,254})@(?P<digest>sha256:[0-9a-f]{64})$"
)
TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,254}$")
VERSION_RE = re.compile(r"(?<![0-9])([0-9]+\.[0-9]+\.[0-9]+)(?![0-9])")
BLOCKER_CODES = frozenset(
    {
        "unsupported_host",
        "unsupported_arch",
        "runtime_cli_missing",
        "runtime_stopped",
        "apple_kernel_not_configured",
        "runtime_not_ready",
        "image_required",
        "image_missing",
        "image_digest_drift",
        "guest_platform_mismatch",
        "guest_unshare_unavailable",
        "filesystem_isolation_unavailable",
        "strict_network_budget_required",
        "network_isolation_failed",
        "network_gateway_unavailable",
        "mount_contract_failed",
        "result_volume_failed",
        "container_cleanup_failed",
        "probe_execution_failed",
    }
)

PROBE_RESULT_KEYS = (
    "runtime_available",
    "image_digest_verified",
    "guest_platform_supported",
    "host_listener_ready",
    "outer_host_control",
    "outer_dns_blocked",
    "outer_direct_ip_blocked",
    "inner_host_blocked",
    "inner_dns_blocked",
    "inner_direct_ip_blocked",
    "unshare_without_broad_capabilities",
    "source_read_only",
    "input_read_only",
    "root_read_only",
    "result_volume_writable",
    "private_tmpfs",
    "cleanup_completed",
)
HOST_PLATFORM_CLASSES = frozenset(
    {
        "macos_arm64",
        "macos_amd64",
        "macos_unsupported",
        "linux_arm64",
        "linux_amd64",
        "linux_unsupported",
        "unsupported",
    }
)
GUEST_PLATFORM_CLASSES = frozenset({"linux_arm64", "linux_amd64", "linux_unsupported"})
REQUIRED_PROBE_KEYS = {
    "apple-container": PROBE_RESULT_KEYS,
    "docker": tuple(key for key in PROBE_RESULT_KEYS if key != "outer_host_control"),
    "native-linux": (
        "runtime_available",
        "guest_platform_supported",
        "host_listener_ready",
        "inner_host_blocked",
        "inner_dns_blocked",
        "inner_direct_ip_blocked",
        "unshare_without_broad_capabilities",
        "cleanup_completed",
    ),
}


def _canary_code(host: str, port: int) -> str:
    return rf"""
import json, os, platform, socket

def blocked_write(path):
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("blocked")
    except OSError:
        return True
    return False

def blocked_connect(host, port):
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return False
    except OSError:
        return True

host = {host!r}
port = {port}
output_path = "/repo/artifacts/orchestration/experiments/results/probe-write.json"
tmp_path = "/tmp/probe-write"
output_writable = False
private_tmpfs = False
try:
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("{{}}")
    os.unlink(output_path)
    output_writable = True
except OSError:
    pass
try:
    with open(tmp_path, "w", encoding="utf-8") as handle:
        handle.write("ok")
    os.unlink(tmp_path)
    private_tmpfs = True
except OSError:
    pass
payload = {{
    "guest_platform_supported": platform.system() == "Linux" and platform.machine() in {{"aarch64", "arm64", "x86_64", "amd64"}},
    "host_reachable": not blocked_connect(host, port),
    "dns_blocked": blocked_connect("example.com", 443),
    "direct_ip_blocked": blocked_connect("1.1.1.1", 443),
    "source_read_only": blocked_write("/repo/probe-source-write"),
    "input_read_only": blocked_write("/repo/.experiment-runner-input/probe-input-write"),
    "root_read_only": blocked_write("/probe-root-write"),
    "result_volume_writable": output_writable,
    "private_tmpfs": private_tmpfs,
}}
print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
""".strip()


_COLLECTOR_CODE = rf"""
import base64, json, os, stat
path = os.environ["RESULT_PATH"]
flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
fd = os.open(path, flags)
try:
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_size > {MAX_RESULT_BYTES}:
        raise SystemExit(71)
    payload = os.read(fd, {MAX_RESULT_BYTES} + 1)
    if len(payload) != info.st_size or len(payload) > {MAX_RESULT_BYTES}:
        raise SystemExit(72)
finally:
    os.close(fd)
print(json.dumps({{"payload_b64": base64.b64encode(payload).decode("ascii")}}, separators=(",", ":")))
""".strip()


class DispatchError(RuntimeError):
    """Stable dispatcher failure without raw host/runtime output."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PreRunCapabilityError(DispatchError):
    """Deterministic backend drift detected after selection but before execution."""


@dataclass(frozen=True)
class ImageReference:
    name: str
    digest: str

    def runtime_ref(self, backend: str) -> str:
        if backend == "apple-container":
            return f"{self.name}@{self.digest}"
        return self.digest


@dataclass(frozen=True)
class BackendProbe:
    backend: str
    host_platform: str
    guest_platform: str
    runtime_version: str
    image_digest: str | None
    isolation_method: str
    probe_results: dict[str, bool | None]
    blocking_reasons: tuple[str, ...]

    @property
    def strict(self) -> bool:
        return not self.blocking_reasons and all(
            self.probe_results.get(key) is True for key in REQUIRED_PROBE_KEYS[self.backend]
        )

    def to_artifact(self) -> dict[str, Any]:
        payload = {
            "schema_version": CAPABILITY_SCHEMA_VERSION,
            "artifact_type": CAPABILITY_ARTIFACT_TYPE,
            "authority": "evidence_only",
            "backend": self.backend,
            "host_platform": self.host_platform,
            "guest_platform": self.guest_platform,
            "runtime_version": self.runtime_version,
            "image_digest": self.image_digest,
            "isolation_method": self.isolation_method,
            "probe_results": dict(sorted(self.probe_results.items())),
            "blocking_reasons": list(self.blocking_reasons),
            "strict_isolation": self.strict,
            "sanitized": True,
        }
        return validate_capability_artifact(payload)


def _host_platform_class() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine in {"aarch64", "arm64"}:
        normalized_machine = "arm64"
    elif machine in {"x86_64", "amd64"}:
        normalized_machine = "amd64"
    else:
        normalized_machine = "unsupported"
    if system == "darwin":
        system = "macos"
    elif system != "linux":
        return "unsupported"
    return f"{system}_{normalized_machine}"


def _guest_platform_class() -> str:
    machine = platform.machine().lower()
    if machine in {"aarch64", "arm64"}:
        normalized_machine = "arm64"
    elif machine in {"x86_64", "amd64"}:
        normalized_machine = "amd64"
    else:
        normalized_machine = "unsupported"
    return f"linux_{normalized_machine}"


def _isolation_method(backend: str) -> str:
    return {
        "native-linux": "linux_unshare",
        "apple-container": "apple_internal_no_dns_plus_linux_unshare",
        "docker": "docker_network_none_plus_linux_unshare",
    }[backend]


def _safe_env() -> dict[str, str]:
    allowed = ("HOME", "LANG", "LC_ALL", "LC_CTYPE", "PATH", "TMPDIR")
    return {key: os.environ[key] for key in allowed if os.environ.get(key)}


def _run(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int = 30,
    input_text: str | None = None,
    secret_env_keys: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    if not argv or not Path(argv[0]).is_absolute():
        raise DispatchError("runtime_cli_missing")
    try:
        child_env = _safe_env()
        child_env.update({key: os.environ[key] for key in secret_env_keys if os.environ.get(key)})
        return subprocess.run(  # nosec B603: argv begins with resolved absolute executable, no shell (remove-by: 2026-10-31, ref: ledger-p1-experiment-runner-macos-strict-backend)
            argv,
            cwd=str(cwd),
            env=child_env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            input=input_text,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DispatchError("probe_execution_failed") from exc


def _resolve_cli(name: str) -> str | None:
    discovered = shutil.which(name)
    if discovered is None:
        return None
    resolved = Path(discovered).expanduser().resolve(strict=True)
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        return None
    return str(resolved)


def _runtime_version(cli: str) -> str:
    result = _run([cli, "--version"], cwd=REPO_ROOT)
    if result.returncode != 0:
        return "unavailable"
    match = VERSION_RE.search(result.stdout or result.stderr)
    return match.group(1) if match else "unknown"


def parse_image_reference(raw: str) -> ImageReference:
    match = IMAGE_REF_RE.fullmatch(raw.strip())
    if match is None:
        raise ValueError("--image must use immutable name@sha256:<64 lowercase hex> syntax.")
    return ImageReference(name=match.group("name"), digest=match.group("digest"))


def _primary_image_digest(payload: Any) -> str:
    record = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(record, dict):
        raise DispatchError("image_missing")
    configuration = record.get("configuration")
    if isinstance(configuration, dict):
        descriptor = configuration.get("descriptor")
        if isinstance(descriptor, dict):
            digest = descriptor.get("digest")
            if isinstance(digest, str) and IMAGE_DIGEST_RE.fullmatch(digest):
                return digest
    for key in ("Id", "id"):
        digest = record.get(key)
        if isinstance(digest, str):
            normalized = digest if digest.startswith("sha256:") else f"sha256:{digest}"
            if IMAGE_DIGEST_RE.fullmatch(normalized):
                return normalized
    raise DispatchError("image_missing")


def _inspect_image(cli: str, backend: str, image: ImageReference) -> str:
    del backend
    argv = [cli, "image", "inspect", image.name]
    result = _run(argv, cwd=REPO_ROOT)
    if result.returncode != 0:
        raise DispatchError("image_missing")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DispatchError("image_missing") from exc
    if image.digest != _primary_image_digest(payload):
        raise DispatchError("image_digest_drift")
    return image.digest


def _base_probe_results(backend: str) -> dict[str, bool | None]:
    results: dict[str, bool | None] = {key: None for key in PROBE_RESULT_KEYS}
    for key in REQUIRED_PROBE_KEYS[backend]:
        results[key] = False
    return results


def _failed_probe(
    backend: str,
    reason: str,
    *,
    runtime_version: str = "unavailable",
    image_digest: str | None = None,
    results: dict[str, bool | None] | None = None,
) -> BackendProbe:
    if reason not in BLOCKER_CODES:
        raise ValueError(f"Unsupported blocker code: {reason}")
    return BackendProbe(
        backend=backend,
        host_platform=_host_platform_class(),
        guest_platform=_guest_platform_class(),
        runtime_version=runtime_version,
        image_digest=image_digest,
        isolation_method=_isolation_method(backend),
        probe_results=results or _base_probe_results(backend),
        blocking_reasons=(reason,),
    )


def _probe_with_blocker(probe: BackendProbe, reason: str) -> BackendProbe:
    if reason not in BLOCKER_CODES:
        raise ValueError(f"Unsupported blocker code: {reason}")
    return BackendProbe(
        backend=probe.backend,
        host_platform=probe.host_platform,
        guest_platform=probe.guest_platform,
        runtime_version=probe.runtime_version,
        image_digest=probe.image_digest,
        isolation_method=probe.isolation_method,
        probe_results=probe.probe_results,
        blocking_reasons=(reason,),
    )


def _docker_mount(source: Path, target: str, *, readonly: bool) -> str:
    suffix = ",readonly" if readonly else ""
    return f"type=bind,source={source},target={target}{suffix}"


def _apple_mount(source: Path, target: str, *, readonly: bool) -> str:
    suffix = ",readonly" if readonly else ""
    return f"source={source},target={target}{suffix}"


def _volume_mount(volume: str, target: str, *, readonly: bool) -> str:
    suffix = ",readonly" if readonly else ""
    return f"type=volume,source={volume},target={target}{suffix}"


def _container_run_argv(
    *,
    cli: str,
    backend: str,
    image_ref: str,
    container_name: str,
    result_volume: str,
    command: list[str],
    repository: Path | None = None,
    input_dir: Path | None = None,
    apple_network: str | None = None,
    user: str = "65532:65532",
    result_readonly: bool = False,
    extra_env: tuple[str, ...] = (),
) -> list[str]:
    if backend == "docker":
        argv = [
            cli,
            "run",
            "--name",
            container_name,
            "--pull",
            "never",
            "--network",
            "none",
            "--read-only",
            "--user",
            user,
            "--cpus",
            CPU_LIMIT,
            "--memory",
            MEMORY_LIMIT,
            "--tmpfs",
            f"{CONTAINER_PRIVATE_TMP}:rw,noexec,nosuid,size={TMPFS_SIZE}",
        ]
        if repository is not None and input_dir is not None:
            argv.extend(
                [
                    "--mount",
                    _docker_mount(repository, CONTAINER_REPO, readonly=True),
                    "--mount",
                    _docker_mount(input_dir, CONTAINER_INPUT, readonly=True),
                ]
            )
    elif backend == "apple-container" and apple_network:
        argv = [
            cli,
            "run",
            "--name",
            container_name,
            "--network",
            apple_network,
            "--no-dns",
            "--read-only",
            "--user",
            user,
            "--cpus",
            CPU_LIMIT,
            "--memory",
            MEMORY_LIMIT,
            "--mount",
            (
                "type=tmpfs,"
                f"destination={CONTAINER_PRIVATE_TMP},"
                f"size={APPLE_TMPFS_SIZE},mode=1777"
            ),
        ]
        if repository is not None and input_dir is not None:
            argv.extend(
                [
                    "--mount",
                    _apple_mount(repository, CONTAINER_REPO, readonly=True),
                    "--mount",
                    _apple_mount(input_dir, CONTAINER_INPUT, readonly=True),
                ]
            )
    else:
        raise DispatchError("probe_execution_failed")
    argv.extend(
        [
            "--mount",
            _volume_mount(result_volume, CONTAINER_RESULT_DIR, readonly=result_readonly),
            "--env",
            f"VENV_PYTHON={CONTAINER_PYTHON}",
            "--env",
            f"PYTHONPATH={CONTAINER_REPO}",
        ]
    )
    for entry in extra_env:
        argv.extend(["--env", entry])
    argv.extend([image_ref, *command])
    return argv


def _cleanup_container(cli: str, backend: str, name: str) -> bool:
    stop_args = [cli, "stop", "--time", "1", name]
    try:
        _run(stop_args, cwd=REPO_ROOT)
    except DispatchError:
        pass
    delete_args = (
        [cli, "delete", "--force", name]
        if backend == "apple-container"
        else [cli, "rm", "--force", name]
    )
    try:
        return _run(delete_args, cwd=REPO_ROOT).returncode == 0
    except DispatchError:
        return False


def _create_result_volume(cli: str, backend: str) -> str:
    name = f"pp-er-result-{uuid.uuid4().hex[:12]}"
    argv = (
        [cli, "volume", "create", "-s", RESULT_VOLUME_SIZE, name]
        if backend == "apple-container"
        else [cli, "volume", "create", name]
    )
    if _run(argv, cwd=REPO_ROOT).returncode != 0:
        raise DispatchError("result_volume_failed")
    return name


def _delete_result_volume(cli: str, backend: str, name: str) -> bool:
    argv = (
        [cli, "volume", "delete", name]
        if backend == "apple-container"
        else [cli, "volume", "rm", "--force", name]
    )
    try:
        return _run(argv, cwd=REPO_ROOT).returncode == 0
    except DispatchError:
        return False


def _initialize_result_volume(
    *,
    cli: str,
    backend: str,
    image_ref: str,
    volume: str,
    apple_network: str | None,
) -> bool:
    name = f"pp-er-init-{uuid.uuid4().hex[:12]}"
    completed_ok = False
    cleanup_ok = False
    try:
        argv = _container_run_argv(
            cli=cli,
            backend=backend,
            image_ref=image_ref,
            container_name=name,
            result_volume=volume,
            apple_network=apple_network,
            user="0:0",
            command=["/usr/bin/chown", "65532:65532", CONTAINER_RESULT_DIR],
        )
        completed = _run(argv, cwd=REPO_ROOT, timeout=30)
        completed_ok = completed.returncode == 0
    finally:
        cleanup_ok = _cleanup_container(cli, backend, name)
    return completed_ok and cleanup_ok


def _address_is_bindable(address: str) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((address, 0))
    except OSError:
        return False
    finally:
        probe.close()
    return True


def _discover_host_bind_address() -> str:
    """Return one exact non-loopback IPv4 address without persisting host identity."""

    try:
        records = socket.getaddrinfo(
            socket.gethostname(),
            None,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise DispatchError("host_listener_unavailable") from exc

    candidates: list[str] = []
    for _family, _kind, _proto, _canonical, sockaddr in records:
        candidate = str(sockaddr[0])
        address = ipaddress.ip_address(candidate)
        if (
            address.is_loopback
            or address.is_unspecified
            or address.is_multicast
            or address.is_link_local
            or candidate in candidates
        ):
            continue
        candidates.append(candidate)
    for candidate in candidates:
        if _address_is_bindable(candidate):
            return candidate
    raise DispatchError("host_listener_unavailable")


@contextmanager
def _host_listener() -> Iterator[tuple[str, int, bool]]:
    bind_address = _discover_host_bind_address()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((bind_address, 0))
    listener.listen(8)
    listener.settimeout(0.2)
    stop = threading.Event()

    def serve() -> None:
        while not stop.is_set():
            try:
                connection, _address = listener.accept()
            except (TimeoutError, OSError):
                if stop.is_set():
                    return
                continue
            with connection:
                connection.sendall(b"pulseplate-strict-canary")

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    port = int(listener.getsockname()[1])
    ready = False
    try:
        with socket.create_connection((bind_address, port), timeout=1):
            ready = True
        yield bind_address, port, ready
    finally:
        stop.set()
        listener.close()
        thread.join(timeout=1)


def _find_gateway(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in {
                "gateway",
                "gatewayaddress",
                "gateway_address",
                "ipv4gateway",
            }:
                candidate = str(nested).strip()
                if re.fullmatch(r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}", candidate):
                    return candidate
            found = _find_gateway(nested)
            if found:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_gateway(nested)
            if found:
                return found
    return None


def _discover_gateway(cli: str, backend: str, apple_network: str | None) -> str:
    argv = (
        [cli, "network", "inspect", apple_network]
        if backend == "apple-container" and apple_network
        else [cli, "network", "inspect", "bridge"]
    )
    completed = _run(argv, cwd=REPO_ROOT)
    if completed.returncode != 0:
        raise DispatchError("network_gateway_unavailable")
    try:
        gateway = _find_gateway(json.loads(completed.stdout))
    except json.JSONDecodeError as exc:
        raise DispatchError("network_gateway_unavailable") from exc
    if gateway is None:
        raise DispatchError("network_gateway_unavailable")
    return gateway


def _parse_canary(completed: subprocess.CompletedProcess[str]) -> dict[str, bool]:
    if completed.returncode != 0:
        raise DispatchError("probe_execution_failed")
    try:
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise DispatchError("probe_execution_failed") from exc
    if not isinstance(payload, dict) or not all(
        isinstance(value, bool) for value in payload.values()
    ):
        raise DispatchError("probe_execution_failed")
    return payload


def _runtime_readiness_reason(cli: str, backend: str) -> str | None:
    argv = (
        [cli, "info", "--format", "{{.ServerVersion}}"]
        if backend == "docker"
        else [cli, "system", "status"]
    )
    result = _run(argv, cwd=REPO_ROOT)
    if result.returncode == 0:
        return None
    if backend == "docker":
        return "runtime_stopped"
    diagnostic = f"{result.stdout}\n{result.stderr}".lower()
    if "kernel" in diagnostic:
        return "apple_kernel_not_configured"
    return "runtime_not_ready"


def _create_apple_network(cli: str) -> str:
    name = f"pp-er-{uuid.uuid4().hex[:12]}"
    result = _run([cli, "network", "create", "--internal", name], cwd=REPO_ROOT)
    if result.returncode != 0:
        raise DispatchError("network_isolation_failed")
    return name


def _delete_apple_network(cli: str, name: str) -> bool:
    try:
        return _run([cli, "network", "delete", name], cwd=REPO_ROOT).returncode == 0
    except DispatchError:
        return False


def _cleanup_container_resources(
    *,
    cli: str,
    backend: str,
    volume: str | None,
    apple_network: str | None,
    prior_cleanup_ok: bool,
) -> bool:
    cleanup_ok = prior_cleanup_ok
    if volume is not None:
        cleanup_ok = _delete_result_volume(cli, backend, volume) and cleanup_ok
    if apple_network is not None:
        cleanup_ok = _delete_apple_network(cli, apple_network) and cleanup_ok
    return cleanup_ok


def _run_container_canary(
    cli: str,
    backend: str,
    image: ImageReference,
) -> dict[str, bool | None]:
    with tempfile.TemporaryDirectory(prefix="pp-er-probe-") as raw_temp:
        root = Path(raw_temp)
        repository = root / "repo"
        input_dir = root / "input"
        for directory in (repository, input_dir):
            directory.mkdir()
        (repository / CONTAINER_INPUT.removeprefix(f"{CONTAINER_REPO}/")).mkdir()
        (repository / CONTAINER_RESULT_DIR.removeprefix(f"{CONTAINER_REPO}/")).mkdir(parents=True)
        (repository / "probe-source").write_text("source", encoding="utf-8")
        (input_dir / "probe-input").write_text("input", encoding="utf-8")
        apple_network: str | None = None
        volume: str | None = None
        cleanup_completed = True
        try:
            if backend == "apple-container":
                apple_network = _create_apple_network(cli)
            gateway = _discover_gateway(cli, backend, apple_network)
            volume = _create_result_volume(cli, backend)
            runtime_ref = image.runtime_ref(backend)
            if not _initialize_result_volume(
                cli=cli,
                backend=backend,
                image_ref=runtime_ref,
                volume=volume,
                apple_network=apple_network,
            ):
                raise DispatchError("result_volume_failed")
            results = _base_probe_results(backend)
            results["runtime_available"] = True
            results["image_digest_verified"] = True
            with _host_listener() as (host_address, port, listener_ready):
                results["host_listener_ready"] = listener_ready
                outer_name = f"pp-er-outer-{uuid.uuid4().hex[:12]}"
                inner_name = f"pp-er-inner-{uuid.uuid4().hex[:12]}"
                canary_address = host_address if backend == "apple-container" else gateway
                code = _canary_code(canary_address, port)
                try:
                    outer = _run(
                        _container_run_argv(
                            cli=cli,
                            backend=backend,
                            image_ref=runtime_ref,
                            container_name=outer_name,
                            result_volume=volume,
                            repository=repository,
                            input_dir=input_dir,
                            apple_network=apple_network,
                            command=[CONTAINER_PYTHON, "-c", code],
                        ),
                        cwd=REPO_ROOT,
                        timeout=45,
                    )
                    outer_payload = _parse_canary(outer)
                finally:
                    cleanup_completed = (
                        _cleanup_container(cli, backend, outer_name) and cleanup_completed
                    )
                try:
                    inner = _run(
                        _container_run_argv(
                            cli=cli,
                            backend=backend,
                            image_ref=runtime_ref,
                            container_name=inner_name,
                            result_volume=volume,
                            repository=repository,
                            input_dir=input_dir,
                            apple_network=apple_network,
                            command=[
                                CONTAINER_UNSHARE,
                                "--net",
                                "--map-root-user",
                                CONTAINER_PYTHON,
                                "-c",
                                code,
                            ],
                        ),
                        cwd=REPO_ROOT,
                        timeout=45,
                    )
                    inner_payload = _parse_canary(inner)
                    results["unshare_without_broad_capabilities"] = True
                finally:
                    cleanup_completed = (
                        _cleanup_container(cli, backend, inner_name) and cleanup_completed
                    )
            results["guest_platform_supported"] = outer_payload["guest_platform_supported"]
            results["outer_host_control"] = (
                outer_payload["host_reachable"] if backend == "apple-container" else None
            )
            results["outer_dns_blocked"] = outer_payload["dns_blocked"]
            results["outer_direct_ip_blocked"] = outer_payload["direct_ip_blocked"]
            results["inner_host_blocked"] = not inner_payload["host_reachable"]
            results["inner_dns_blocked"] = inner_payload["dns_blocked"]
            results["inner_direct_ip_blocked"] = inner_payload["direct_ip_blocked"]
            for key in (
                "source_read_only",
                "input_read_only",
                "root_read_only",
                "result_volume_writable",
                "private_tmpfs",
            ):
                results[key] = inner_payload[key]
        except BaseException as exc:
            cleanup_completed = _cleanup_container_resources(
                cli=cli,
                backend=backend,
                volume=volume,
                apple_network=apple_network,
                prior_cleanup_ok=cleanup_completed,
            )
            if not cleanup_completed:
                raise DispatchError("container_cleanup_failed") from exc
            raise
        cleanup_completed = _cleanup_container_resources(
            cli=cli,
            backend=backend,
            volume=volume,
            apple_network=apple_network,
            prior_cleanup_ok=cleanup_completed,
        )
        results["cleanup_completed"] = cleanup_completed
        return results


def probe_backend(backend: str, image: ImageReference | None = None) -> BackendProbe:
    if backend == "native-linux":
        if image is None:
            return _failed_probe(backend, "image_required")
        if platform.system() != "Linux":
            return _failed_probe(backend, "unsupported_host", image_digest=image.digest)
        if platform.machine().lower() not in {"arm64", "aarch64", "x86_64", "amd64"}:
            return _failed_probe(backend, "unsupported_arch", image_digest=image.digest)
        unshare = _resolve_cli("unshare")
        if unshare is None:
            return _failed_probe(backend, "runtime_cli_missing", image_digest=image.digest)
        results = _base_probe_results(backend)
        results["runtime_available"] = True
        with _host_listener() as (_host_address, port, ready):
            results["host_listener_ready"] = ready
            completed = _run(
                [
                    unshare,
                    "--net",
                    "--map-root-user",
                    sys.executable,
                    "-c",
                    _canary_code("127.0.0.1", port),
                ],
                cwd=REPO_ROOT,
            )
        if completed.returncode != 0:
            return _failed_probe(
                backend,
                "guest_unshare_unavailable",
                runtime_version=platform.release(),
                image_digest=image.digest,
                results=results,
            )
        inner = _parse_canary(completed)
        results["guest_platform_supported"] = inner["guest_platform_supported"]
        results["inner_host_blocked"] = not inner["host_reachable"]
        results["inner_dns_blocked"] = inner["dns_blocked"]
        results["inner_direct_ip_blocked"] = inner["direct_ip_blocked"]
        results["unshare_without_broad_capabilities"] = True
        results["cleanup_completed"] = True
        native_blockers = ["filesystem_isolation_unavailable"]
        if not all(results[key] is True for key in REQUIRED_PROBE_KEYS[backend]):
            native_blockers.append("network_isolation_failed")
        return BackendProbe(
            backend=backend,
            host_platform=_host_platform_class(),
            guest_platform=_guest_platform_class(),
            runtime_version=platform.release(),
            image_digest=image.digest,
            isolation_method=_isolation_method(backend),
            probe_results=results,
            blocking_reasons=tuple(sorted(native_blockers)),
        )

    expected_cli = "container" if backend == "apple-container" else "docker"
    if backend == "apple-container":
        if platform.system() != "Darwin":
            return _failed_probe(
                backend, "unsupported_host", image_digest=image.digest if image else None
            )
        if platform.machine().lower() not in {"arm64", "aarch64"}:
            return _failed_probe(
                backend, "unsupported_arch", image_digest=image.digest if image else None
            )
    cli = _resolve_cli(expected_cli)
    if cli is None:
        return _failed_probe(
            backend, "runtime_cli_missing", image_digest=image.digest if image else None
        )
    version = _runtime_version(cli)
    readiness_reason = _runtime_readiness_reason(cli, backend)
    if readiness_reason is not None:
        return _failed_probe(
            backend,
            readiness_reason,
            runtime_version=version,
            image_digest=image.digest if image else None,
        )
    if image is None:
        results = _base_probe_results(backend)
        results["runtime_available"] = True
        return _failed_probe(backend, "image_required", runtime_version=version, results=results)
    try:
        _inspect_image(cli, backend, image)
        results = _run_container_canary(cli, backend, image)
    except DispatchError as exc:
        reason = str(exc)
        if reason not in BLOCKER_CODES:
            reason = "probe_execution_failed"
        return _failed_probe(
            backend,
            reason,
            runtime_version=version,
            image_digest=image.digest,
        )
    container_blockers: list[str] = []
    if results["guest_platform_supported"] is not True:
        container_blockers.append("guest_platform_mismatch")
    if results["unshare_without_broad_capabilities"] is not True:
        container_blockers.append("guest_unshare_unavailable")
    network_keys: tuple[str, ...] = (
        "host_listener_ready",
        "outer_dns_blocked",
        "outer_direct_ip_blocked",
        "inner_host_blocked",
        "inner_dns_blocked",
        "inner_direct_ip_blocked",
    )
    if backend == "apple-container":
        network_keys = (*network_keys, "outer_host_control")
    if not all(results[key] is True for key in network_keys):
        container_blockers.append("network_isolation_failed")
    if not all(
        results[key] is True
        for key in (
            "source_read_only",
            "input_read_only",
            "root_read_only",
            "result_volume_writable",
            "private_tmpfs",
        )
    ):
        container_blockers.append("mount_contract_failed")
    if results["cleanup_completed"] is not True:
        container_blockers.append("container_cleanup_failed")
    return BackendProbe(
        backend=backend,
        host_platform=_host_platform_class(),
        guest_platform=_guest_platform_class(),
        runtime_version=version,
        image_digest=image.digest,
        isolation_method=_isolation_method(backend),
        probe_results=results,
        blocking_reasons=tuple(sorted(set(container_blockers))),
    )


def select_backend(
    requested: str, image: ImageReference
) -> tuple[BackendProbe | None, list[BackendProbe]]:
    if requested != "auto":
        probe = probe_backend(requested, image)
        return (probe if probe.strict else None), [probe]
    candidates = (
        ("native-linux",) if platform.system() == "Linux" else ("apple-container", "docker")
    )
    attempts: list[BackendProbe] = []
    for backend in candidates:
        probe = probe_backend(backend, image)
        attempts.append(probe)
        if probe.strict:
            return probe, attempts
    return None, attempts


def _strict_network_budget_probe(requested: str, image: ImageReference) -> BackendProbe:
    """Build a deterministic fail-closed probe without contacting a runtime."""

    if requested != "auto":
        backend = requested
    elif platform.system() == "Darwin":
        backend = "apple-container"
    elif platform.system() == "Linux":
        backend = "native-linux"
    else:
        backend = "docker"
    return _failed_probe(
        backend,
        "strict_network_budget_required",
        image_digest=image.digest,
    )


def validate_capability_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "schema_version",
        "artifact_type",
        "authority",
        "backend",
        "host_platform",
        "guest_platform",
        "runtime_version",
        "image_digest",
        "isolation_method",
        "probe_results",
        "blocking_reasons",
        "strict_isolation",
        "sanitized",
    }
    if set(payload) != expected:
        raise ValueError("Capability artifact has unexpected or missing fields.")
    if payload["schema_version"] != CAPABILITY_SCHEMA_VERSION:
        raise ValueError("Capability artifact schema_version is unsupported.")
    if payload["artifact_type"] != CAPABILITY_ARTIFACT_TYPE:
        raise ValueError("Capability artifact type is unsupported.")
    if payload["authority"] != "evidence_only" or payload["sanitized"] is not True:
        raise ValueError("Capability artifact must remain sanitized evidence_only output.")
    if payload["backend"] not in BACKENDS[1:]:
        raise ValueError("Capability artifact backend is unsupported.")
    backend = str(payload["backend"])
    if payload["host_platform"] not in HOST_PLATFORM_CLASSES:
        raise ValueError("Capability artifact host_platform is unsupported.")
    if payload["guest_platform"] not in GUEST_PLATFORM_CLASSES:
        raise ValueError("Capability artifact guest_platform is unsupported.")
    runtime_version = payload["runtime_version"]
    if not isinstance(runtime_version, str) or not re.fullmatch(
        r"[A-Za-z0-9._+-]{1,64}", runtime_version
    ):
        raise ValueError("Capability artifact runtime_version is invalid.")
    if payload["isolation_method"] != _isolation_method(backend):
        raise ValueError("Capability artifact isolation_method is inconsistent.")
    digest = payload["image_digest"]
    if digest is not None and not IMAGE_DIGEST_RE.fullmatch(str(digest)):
        raise ValueError("Capability artifact image_digest is invalid.")
    reasons = payload["blocking_reasons"]
    if not isinstance(reasons, list) or reasons != sorted(set(reasons)):
        raise ValueError("Capability artifact blocking_reasons must be sorted and unique.")
    if any(reason not in BLOCKER_CODES for reason in reasons):
        raise ValueError("Capability artifact blocker code is unsupported.")
    probe_results = payload["probe_results"]
    if set(probe_results) != set(PROBE_RESULT_KEYS) or not all(
        isinstance(value, bool) or value is None for value in probe_results.values()
    ):
        raise ValueError(
            "Capability artifact probe_results must contain the exact boolean/null contract."
        )
    strict = not reasons and all(probe_results[key] is True for key in REQUIRED_PROBE_KEYS[backend])
    if payload["strict_isolation"] is not strict:
        raise ValueError("Capability artifact strict_isolation is inconsistent.")
    return dict(payload)


def _reject_symlink_components(path: Path) -> None:
    absolute = path.absolute()
    for component in reversed((absolute, *absolute.parents)):
        if component.exists() or component.is_symlink():
            if component.is_symlink():
                raise ValueError("Artifact paths must not contain symlinked components.")


def _resolve_local_output(raw: str, *, root: Path, suffix: str = ".json") -> Path:
    candidate = Path(raw)
    if candidate.is_absolute() or candidate.name != raw or not raw.endswith(suffix):
        raise ValueError(f"Output must be a local {suffix} filename without path separators.")
    _reject_symlink_components(root)
    root.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(root)
    resolved = (root / candidate).resolve()
    if resolved.parent != root.resolve() or resolved.is_symlink():
        raise ValueError("Output path escaped the canonical local artifact directory.")
    return resolved


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _reject_symlink_components(path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(path.parent)
    if path.is_symlink():
        raise ValueError("Refusing to write through a symlinked artifact path.")
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(raw_temp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _require_repo_local_file(raw: str, *, suffix: str) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        raise ValueError("Input paths must be repository-relative.")
    repo_root = Path(REPO_ROOT).resolve()
    resolved = (repo_root / candidate).resolve(strict=True)
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError("Input paths must stay inside the repository.") from exc
    if not resolved.is_file() or resolved.suffix != suffix:
        raise ValueError(f"Input must be an existing repository-local {suffix} file.")
    return resolved


def _git_binary() -> str:
    git = _resolve_cli("git")
    if git is None:
        raise DispatchError("runtime_cli_missing")
    return git


def _git(
    args: list[str], *, cwd: Path, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    result = _run([_git_binary(), *args], cwd=cwd, input_text=input_text)
    if result.returncode != 0:
        raise DispatchError("probe_execution_failed")
    return result


def _create_snapshot(root: Path, destination: Path) -> str:
    before = _git(["status", "--short", "--untracked-files=no"], cwd=root).stdout
    _git(["clone", "--quiet", "--no-hardlinks", str(root), str(destination)], cwd=root)
    head = _git(["rev-parse", "HEAD"], cwd=root).stdout.strip()
    _git(["checkout", "--quiet", "--detach", head], cwd=destination)
    tracked_diff = _git(["diff", "--binary", "HEAD"], cwd=root).stdout
    if tracked_diff:
        _git(["apply", "--index", "--binary", "-"], cwd=destination, input_text=tracked_diff)
    after = _git(["status", "--short", "--untracked-files=no"], cwd=root).stdout
    if before != after:
        raise DispatchError("probe_execution_failed")
    return tracked_diff


def _execution_backend_payload(probe: BackendProbe, *, passed: bool) -> dict[str, str]:
    if probe.image_digest is None:
        raise ValueError("Execution backend provenance requires an image digest.")
    return {
        "name": probe.backend,
        "guest_platform": probe.guest_platform,
        "runtime_version": probe.runtime_version,
        "image_digest": probe.image_digest,
        "network_isolation": probe.isolation_method,
        "preflight_status": "passed" if passed else "failed",
    }


def _validated_experiment_result(result: dict[str, Any]) -> dict[str, Any]:
    validated: dict[str, Any] = validate_experiment_result(result)
    return validated


def _capability_mismatch_result(
    packet: dict[str, Any],
    image: ImageReference,
    probe: BackendProbe,
) -> dict[str, Any]:
    experiment_id = packet["experiment_id"]
    runner_mode = packet["runner_mode"]
    candidate_patch = (
        ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE
        if runner_mode == ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE
        else "candidate.patch"
    )
    result = {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "runner_mode": runner_mode,
        "candidate_patch": candidate_patch,
        "status": "rejected",
        "failure_class": "capability_mismatch",
        "mutated_paths": [],
        "oracle_results": [],
        "budget_observations": {
            "configured_budgets": dict(packet["budgets"]),
            "oracle_commands_executed": 0,
            "attempts": 0,
            "retries_consumed": 0,
            "runner_error": probe.blocking_reasons[0],
        },
        "shared_tree_untouched": True,
        "promotion_ready": False,
        "contribution_kind": "none",
        "coauthor_required": False,
        "coauthor_reason": "",
        "execution_backend": _execution_backend_payload(
            BackendProbe(
                backend=probe.backend,
                host_platform=probe.host_platform,
                guest_platform=probe.guest_platform,
                runtime_version=probe.runtime_version,
                image_digest=image.digest,
                isolation_method=probe.isolation_method,
                probe_results=probe.probe_results,
                blocking_reasons=probe.blocking_reasons,
            ),
            passed=False,
        ),
    }
    return _validated_experiment_result(result)


def _infra_flake_result(
    packet: dict[str, Any],
    image: ImageReference,
    probe: BackendProbe,
    error_code: str,
) -> dict[str, Any]:
    runner_mode = packet["runner_mode"]
    candidate_patch = (
        ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE
        if runner_mode == ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE
        else "candidate.patch"
    )
    result = {
        "schema_version": "1.0",
        "experiment_id": packet["experiment_id"],
        "runner_mode": runner_mode,
        "candidate_patch": candidate_patch,
        "status": "rejected",
        "failure_class": "infra_flake",
        "mutated_paths": [],
        "oracle_results": [],
        "budget_observations": {
            "configured_budgets": dict(packet["budgets"]),
            "oracle_commands_executed": 0,
            "attempts": 1,
            "retries_consumed": 0,
            "runner_error": error_code,
        },
        "shared_tree_untouched": True,
        "promotion_ready": False,
        "contribution_kind": "none",
        "coauthor_required": False,
        "coauthor_reason": "",
        "execution_backend": _execution_backend_payload(probe, passed=True),
    }
    return _validated_experiment_result(_redact_result_value(result))


_SECRET_TEXT_PATTERNS = (
    re.compile(r"(?i)(token|secret|password|api[_-]?key)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})\b"),
)


def _redact_result_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _redact_result_value(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_redact_result_value(nested) for nested in value]
    if not isinstance(value, str):
        return value
    redacted = value
    path_replacements = (
        (str(REPO_ROOT), "<repo>"),
        (str(Path.home()), "<home>"),
        (tempfile.gettempdir(), "<tmp>"),
    )
    for raw, replacement in path_replacements:
        if raw and len(raw) > 1:
            redacted = redacted.replace(raw, replacement)
    for key, secret in os.environ.items():
        if any(token in key.upper() for token in ("TOKEN", "SECRET", "PASSWORD", "SALT", "KEY")):
            if len(secret) >= 6:
                redacted = redacted.replace(secret, "<redacted>")
    for pattern in _SECRET_TEXT_PATTERNS:
        redacted = pattern.sub("<redacted>", redacted)
    return redacted


def _sanitize_result(result: dict[str, Any], probe: BackendProbe) -> dict[str, Any]:
    sanitized = _redact_result_value(dict(result))
    if not isinstance(sanitized, dict):
        raise DispatchError("result_redaction_failed")
    sanitized["execution_backend"] = _execution_backend_payload(probe, passed=True)
    oracle_results = []
    for raw_oracle in sanitized.get("oracle_results", []):
        oracle = dict(raw_oracle)
        oracle["cwd"] = "/workspace"
        oracle_results.append(oracle)
    sanitized["oracle_results"] = oracle_results
    return _validated_experiment_result(sanitized)


def _collect_result_volume(
    *,
    cli: str,
    backend: str,
    image_ref: str,
    volume: str,
    output_name: str,
    apple_network: str | None,
) -> dict[str, Any]:
    collector = f"pp-er-collector-{uuid.uuid4().hex[:12]}"
    try:
        completed = _run(
            _container_run_argv(
                cli=cli,
                backend=backend,
                image_ref=image_ref,
                container_name=collector,
                result_volume=volume,
                result_readonly=True,
                apple_network=apple_network,
                extra_env=(f"RESULT_PATH={CONTAINER_RESULT_DIR}/{output_name}",),
                command=[
                    CONTAINER_UNSHARE,
                    "--net",
                    "--map-root-user",
                    CONTAINER_PYTHON,
                    "-c",
                    _COLLECTOR_CODE,
                ],
            ),
            cwd=REPO_ROOT,
            timeout=30,
        )
        if completed.returncode != 0:
            raise DispatchError("result_extraction_failed")
        try:
            envelope = json.loads(completed.stdout.strip().splitlines()[-1])
            encoded = envelope["payload_b64"]
            payload_bytes = base64.b64decode(encoded, validate=True)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (
            IndexError,
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise DispatchError("result_extraction_failed") from exc
        if len(payload_bytes) > MAX_RESULT_BYTES or not isinstance(payload, dict):
            raise DispatchError("result_extraction_failed")
        return payload
    finally:
        if not _cleanup_container(cli, backend, collector):
            raise DispatchError("container_cleanup_failed")


def _invoke_container_runner(
    *,
    probe: BackendProbe,
    image: ImageReference,
    packet_path: Path,
    candidate_patch: Path | None,
    output_name: str,
) -> dict[str, Any]:
    cli_name = "container" if probe.backend == "apple-container" else "docker"
    cli = _resolve_cli(cli_name)
    if cli is None:
        raise DispatchError("runtime_cli_missing")
    with tempfile.TemporaryDirectory(prefix="pp-er-run-") as raw_temp:
        temp_root = Path(raw_temp)
        snapshot = temp_root / "repo"
        input_dir = temp_root / "input"
        input_dir.mkdir()
        _create_snapshot(REPO_ROOT, snapshot)
        (snapshot / CONTAINER_INPUT.removeprefix(f"{CONTAINER_REPO}/")).mkdir()
        (snapshot / CONTAINER_RESULT_DIR.removeprefix(f"{CONTAINER_REPO}/")).mkdir(
            parents=True, exist_ok=True
        )
        shutil.copyfile(packet_path, input_dir / "packet.json")
        if candidate_patch is not None:
            shutil.copyfile(candidate_patch, input_dir / "candidate.patch")
        command = [
            CONTAINER_PYTHON,
            f"{CONTAINER_REPO}/scripts/orchestration/experiment_runner.py",
            "--packet",
            f"{CONTAINER_INPUT}/packet.json",
            "--output",
            output_name,
        ]
        if candidate_patch is not None:
            command.extend(["--candidate-patch", f"{CONTAINER_INPUT}/candidate.patch"])
        apple_network: str | None = None
        volume: str | None = None
        runner_name = f"pp-er-runner-{uuid.uuid4().hex[:12]}"
        cleanup_completed = True
        try:
            try:
                if probe.backend == "apple-container":
                    apple_network = _create_apple_network(cli)
                _inspect_image(cli, probe.backend, image)
                runtime_ref = image.runtime_ref(probe.backend)
                volume = _create_result_volume(cli, probe.backend)
                if not _initialize_result_volume(
                    cli=cli,
                    backend=probe.backend,
                    image_ref=runtime_ref,
                    volume=volume,
                    apple_network=apple_network,
                ):
                    raise DispatchError("result_volume_failed")
            except DispatchError as exc:
                raise PreRunCapabilityError(exc.code) from exc
            packet = validate_experiment_packet(json.loads(packet_path.read_text(encoding="utf-8")))
            timeout = int(packet["budgets"]["wall_clock_seconds"]) + 60
            try:
                completed = _run(
                    _container_run_argv(
                        cli=cli,
                        backend=probe.backend,
                        image_ref=runtime_ref,
                        container_name=runner_name,
                        result_volume=volume,
                        repository=snapshot,
                        input_dir=input_dir,
                        command=command,
                        apple_network=apple_network,
                    ),
                    cwd=REPO_ROOT,
                    timeout=timeout,
                )
            finally:
                cleanup_completed = (
                    _cleanup_container(cli, probe.backend, runner_name) and cleanup_completed
                )
            if not cleanup_completed:
                raise DispatchError("container_cleanup_failed")
            if completed.returncode not in {0, 1}:
                raise DispatchError("runner_execution_failed")
            payload = _collect_result_volume(
                cli=cli,
                backend=probe.backend,
                image_ref=runtime_ref,
                volume=volume,
                output_name=output_name,
                apple_network=apple_network,
            )
        except BaseException as exc:
            cleanup_completed = _cleanup_container_resources(
                cli=cli,
                backend=probe.backend,
                volume=volume,
                apple_network=apple_network,
                prior_cleanup_ok=cleanup_completed,
            )
            if not cleanup_completed:
                raise DispatchError("container_cleanup_failed") from exc
            raise
        cleanup_completed = _cleanup_container_resources(
            cli=cli,
            backend=probe.backend,
            volume=volume,
            apple_network=apple_network,
            prior_cleanup_ok=cleanup_completed,
        )
        if not cleanup_completed:
            raise DispatchError("container_cleanup_failed")
        return _sanitize_result(payload, probe)


def _build_image(backend: str, tag: str) -> dict[str, str]:
    if not TAG_RE.fullmatch(tag) or "@" in tag:
        raise ValueError("--tag must be a bounded mutable local image tag without a digest.")
    cli_name = "container" if backend == "apple-container" else "docker"
    cli = _resolve_cli(cli_name)
    if cli is None:
        raise DispatchError("runtime_cli_missing")
    readiness_reason = _runtime_readiness_reason(cli, backend)
    if readiness_reason is not None:
        raise DispatchError(readiness_reason)
    argv = [cli, "build", "--file", str(CONTAINERFILE), "--tag", tag]
    for env_name, secret_id in (
        ("PULSEPLATE_PYTHON_INDEX_URL", "pp_py_index"),
        ("PULSEPLATE_PYTHON_TRUSTED_HOST", "pp_py_host"),
        ("PULSEPLATE_PYTHON_NETRC", "pp_netrc"),
    ):
        if os.environ.get(env_name):
            argv.extend(["--secret", f"id={secret_id},env={env_name}"])
    argv.append(str(REPO_ROOT))
    secret_env_keys = tuple(
        env_name
        for env_name in (
            "PULSEPLATE_PYTHON_INDEX_URL",
            "PULSEPLATE_PYTHON_TRUSTED_HOST",
            "PULSEPLATE_PYTHON_NETRC",
        )
        if os.environ.get(env_name)
    )
    completed = _run(
        argv,
        cwd=REPO_ROOT,
        timeout=1800,
        secret_env_keys=secret_env_keys,
    )
    if completed.returncode != 0:
        raise DispatchError("probe_execution_failed")
    inspect = _run([cli, "image", "inspect", tag], cwd=REPO_ROOT)
    if inspect.returncode != 0:
        raise DispatchError("image_missing")
    try:
        digest = _primary_image_digest(json.loads(inspect.stdout))
    except json.JSONDecodeError as exc:
        raise DispatchError("image_missing") from exc
    history = ""
    if backend == "docker":
        history_result = _run(
            [cli, "history", "--no-trunc", "--format", "{{json .CreatedBy}}", tag],
            cwd=REPO_ROOT,
        )
        if history_result.returncode != 0:
            raise DispatchError("image_hygiene_failed")
        history = history_result.stdout
    immutable_ref = f"{tag}@{digest}"
    if backend == "apple-container":
        registered = _run(
            [cli, "image", "tag", tag, immutable_ref],
            cwd=REPO_ROOT,
        )
        if registered.returncode != 0:
            raise DispatchError("image_digest_drift")
        immutable_inspect = _run(
            [cli, "image", "inspect", immutable_ref],
            cwd=REPO_ROOT,
        )
        if immutable_inspect.returncode != 0:
            raise DispatchError("image_digest_drift")
        try:
            if _primary_image_digest(json.loads(immutable_inspect.stdout)) != digest:
                raise DispatchError("image_digest_drift")
        except json.JSONDecodeError as exc:
            raise DispatchError("image_digest_drift") from exc
        inspect = immutable_inspect
    image_metadata = f"{inspect.stdout}\n{history}"
    forbidden_names = secret_env_keys
    forbidden_values = tuple(
        os.environ[key] for key in secret_env_keys if len(os.environ.get(key, "")) >= 6
    )
    if any(name in image_metadata for name in forbidden_names) or any(
        value in image_metadata for value in forbidden_values
    ):
        raise DispatchError("image_hygiene_failed")
    return {"backend": backend, "image": immutable_ref, "sanitized": "true"}


def _read_packet(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Unable to read a valid experiment packet JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Experiment packet must be a JSON object.")
    return payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="experiment_runner_dispatch",
        description="Select and execute a strict Experiment Runner backend without downgrade.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    probe = subparsers.add_parser("probe")
    probe.add_argument("--backend", choices=BACKENDS, default="auto")
    probe.add_argument("--image", required=True)
    probe.add_argument("--output", required=True)
    build = subparsers.add_parser("build-image")
    build.add_argument("--backend", choices=CONTAINER_BACKENDS, required=True)
    build.add_argument("--tag", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--backend", choices=BACKENDS, default="auto")
    run.add_argument("--packet", required=True)
    run.add_argument("--candidate-patch", default=None)
    run.add_argument("--image", required=True)
    run.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
        if args.command == "probe":
            image = parse_image_reference(args.image)
            if args.backend == "auto":
                selected, attempts = select_backend("auto", image)
                probe = selected or attempts[-1]
            else:
                probe = probe_backend(args.backend, image)
            output = _resolve_local_output(args.output, root=CAPABILITY_ARTIFACT_DIR)
            _atomic_write_json(output, probe.to_artifact())
            print(
                json.dumps(
                    {"artifact": output.name, "strict_isolation": probe.strict}, sort_keys=True
                )
            )
            return 0 if probe.strict else 2
        if args.command == "build-image":
            print(json.dumps(_build_image(args.backend, args.tag), sort_keys=True))
            return 0

        image = parse_image_reference(args.image)
        packet_path = _require_repo_local_file(args.packet, suffix=".json")
        candidate_patch = (
            _require_repo_local_file(args.candidate_patch, suffix=".patch")
            if args.candidate_patch
            else None
        )
        output_path = _resolve_local_output(args.output, root=RESULT_ARTIFACT_DIR)
        packet = validate_experiment_packet(_read_packet(packet_path))
        if packet["runner_mode"] == ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE:
            if candidate_patch is not None:
                raise ValueError("Oracle-only packets must not include --candidate-patch.")
        elif candidate_patch is None:
            raise ValueError("Candidate-patch packets require --candidate-patch.")
        if int(packet["budgets"]["network_budget"]) != 0:
            probe = _strict_network_budget_probe(args.backend, image)
            result = _capability_mismatch_result(packet, image, probe)
            _atomic_write_json(output_path, result)
            print(
                json.dumps(
                    {"artifact": output_path.name, "status": result["status"]},
                    sort_keys=True,
                )
            )
            return 1
        selected, attempts = select_backend(args.backend, image)
        if selected is None:
            result = _capability_mismatch_result(packet, image, attempts[-1])
        else:
            try:
                if selected.backend not in CONTAINER_BACKENDS:
                    raise PreRunCapabilityError("filesystem_isolation_unavailable")
                result = _invoke_container_runner(
                    probe=selected,
                    image=image,
                    packet_path=packet_path,
                    candidate_patch=candidate_patch,
                    output_name=output_path.name,
                )
            except PreRunCapabilityError as exc:
                result = _capability_mismatch_result(
                    packet,
                    image,
                    _probe_with_blocker(selected, exc.code),
                )
            except DispatchError as exc:
                result = _infra_flake_result(packet, image, selected, exc.code)
            except (OSError, ValueError):
                result = _infra_flake_result(packet, image, selected, "result_validation_failed")
        _atomic_write_json(output_path, result)
        print(
            json.dumps({"artifact": output_path.name, "status": result["status"]}, sort_keys=True)
        )
        return 0 if result["status"] == "accepted" else 1
    except (DispatchError, OSError, ValueError) as exc:
        print(f"experiment_runner_dispatch: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
