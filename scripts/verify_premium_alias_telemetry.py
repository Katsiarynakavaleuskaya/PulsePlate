#!/usr/bin/env python3
"""Fail-closed evidence verifier for the premium-alias telemetry window."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
from typing import cast, Protocol, Sequence

SCHEMA = "pulseplate.premium_alias_telemetry_evidence.v1"
ASSET_TYPE = "pulseplate.premium_alias_telemetry_evidence"
POLICY_VERSION = "prod-obs-1.telemetry-evidence.v1"
PROMETHEUS_URL = "http://localhost:9090"
SCRAPE_INTERVAL_SECONDS = 30
MIN_RETENTION_DAYS = 45
FINAL_WINDOW = timedelta(days=30)
FINAL_MIN_SAMPLES = 86_400
MAX_JSON_BYTES = 1_048_576
COMMAND_TIMEOUT_SECONDS = 30.0
PROCESS_CLEANUP_TIMEOUT_SECONDS = 1.0
ALIAS_ROUTES: tuple[str, ...] = (
    "/api/v1/premium/bmr",
    "/api/v1/premium/targets",
    "/api/v1/premium/plate",
    "/api/v1/premium/gaps",
)
AUTHORITY = {
    "sets_t0": False,
    "authorizes_deploy": False,
    "authorizes_alias_removal": False,
}
_SAFE_IDENTITY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:@+-]{0,127}\Z")
_DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
_OUTPUT_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json\Z")
_CONTAINER_ID_RE = re.compile(r"[0-9a-f]{12,64}\Z")
_RELEASE_REVISION_RE = re.compile(r"[0-9a-f]{40}\Z")
_RETENTION_RE = re.compile(r"--storage\.tsdb\.retention\.time=([1-9][0-9]*)d\Z")
_PINNED_IMAGE_REFERENCE_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._/:+-]{0,191}@sha256:[0-9a-f]{64}\Z"
)
_UVICORN_RE = re.compile(r"(?:^|[ /])(?:python[^ ]* -m )?uvicorn(?:[ /]|$)")
_REASON_CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,95}\Z")
_REPLAY_CONTRACT = {
    "identical_same_idempotency": "verify_and_no_write",
    "divergent_existing": "fail_closed",
}
_ADMISSION_CONTRACT = {
    "behavior": "validate_schema_lineage_fingerprint_and_live_snapshot",
    "missing_or_invalid": "hold",
}
_EVIDENCE_FIELDS = frozenset(
    {
        "schema",
        "asset_type",
        "policy_version",
        "mode",
        "decision",
        "reasons",
        "observed_at",
        "checks",
        "identities",
        "topology",
        "retention_days",
        "target",
        "aliases",
        "window",
        "authority",
        "upstream_assets",
        "replay",
        "admission",
        "idempotency_key",
        "fingerprint",
    }
)
_IDENTITY_FIELDS = frozenset(
    {
        "app_container",
        "prometheus_container",
        "release",
        "app_image",
        "prometheus_image",
        "prometheus_image_reference",
        "prometheus_config",
        "prometheus_volume",
        "uvicorn_process",
    }
)
_TOPOLOGY_FIELDS = frozenset({"api_containers", "prometheus_containers", "uvicorn_processes"})
_TARGET_FIELDS = frozenset(
    {
        "expected_count",
        "observed_count",
        "current_up",
        "minimum_up",
        "sample_count",
        "required_samples",
        "restart_changes",
    }
)
_ALIAS_FIELDS = frozenset({"method", "route", "current_value", "increase", "resets", "observation"})
_WINDOW_FIELDS = frozenset({"started_at", "t0", "ended_at", "duration_seconds", "complete"})
_ALIAS_OBSERVATIONS = frozenset(
    {"missing", "observed_negative", "observed_positive", "observed_exact_zero"}
)


class VerificationError(RuntimeError):
    """Stable verifier failure that never embeds commands, paths, or provider output."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class PromtoolClient(Protocol):
    def collect_live_snapshot(self) -> LiveRuntimeSnapshot: ...

    def get_evaluation_anchor(self) -> datetime: ...

    def check_healthy(self) -> bool: ...

    def check_ready(self) -> bool: ...

    def query_scalar(self, expression: str, *, evaluation_time: str) -> float: ...


@dataclass(frozen=True)
class VerificationConfig:
    mode: str
    compose_file: Path
    evidence_dir: Path
    output_name: str | None
    baseline_evidence: Path | None
    t0: datetime | None


@dataclass(frozen=True)
class LiveRuntimeSnapshot:
    app_container_id: str
    prometheus_container_id: str
    release_id: str
    app_image_id: str
    prometheus_image_id: str
    prometheus_image_reference: str
    config_sha256: str
    volume_id: str
    api_container_count: int
    prometheus_container_count: int
    uvicorn_process_count: int
    uvicorn_process_identity: str
    retention_days: int


@dataclass(frozen=True)
class _CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes


def _parse_rfc3339_utc(raw: str) -> datetime:
    if not raw.endswith("Z"):
        raise argparse.ArgumentTypeError("timestamp must use RFC3339 UTC form ending in Z")
    try:
        parsed = datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timestamp must be valid RFC3339 UTC") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise argparse.ArgumentTypeError("timestamp must use UTC")
    return parsed.astimezone(timezone.utc)


def _canonical_timestamp(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)
    text = normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return text.replace(".000000Z", "Z")


def _output_name(raw: str) -> str:
    if not _OUTPUT_NAME_RE.fullmatch(raw):
        raise argparse.ArgumentTypeError("output name must be one bounded .json basename")
    return raw


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--compose-file", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output-name", type=_output_name)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    for mode in ("baseline", "checkpoint", "final"):
        mode_parser = subparsers.add_parser(mode)
        _add_common_arguments(mode_parser)
        if mode != "baseline":
            mode_parser.add_argument("--baseline-evidence", type=Path, required=True)
        if mode == "final":
            mode_parser.add_argument("--t0", type=_parse_rfc3339_utc, required=True)
    return parser.parse_args(argv)


def _default_output_name(mode: str, observed_at: datetime) -> str:
    stamp = observed_at.strftime("%Y%m%dT%H%M%SZ")
    return f"premium_alias_telemetry_{mode}_{stamp}.json"


def _config_from_args(args: argparse.Namespace) -> VerificationConfig:
    return VerificationConfig(
        mode=args.mode,
        compose_file=args.compose_file,
        evidence_dir=args.evidence_dir,
        output_name=args.output_name,
        baseline_evidence=getattr(args, "baseline_evidence", None),
        t0=getattr(args, "t0", None),
    )


def _json_loads_object(payload: bytes, *, error_code: str) -> dict[str, object]:
    def _reject_constant(_value: str) -> object:
        raise ValueError("non-finite JSON constant")

    try:
        decoded = json.loads(payload, parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise VerificationError(error_code) from exc
    if not isinstance(decoded, dict):
        raise VerificationError(error_code)
    return decoded


def _read_bounded_regular_json(file_name: Path) -> dict[str, object]:
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if not isinstance(no_follow, int) or no_follow <= 0:
        raise VerificationError("baseline_read_unavailable")
    try:
        descriptor = os.open(
            file_name,
            os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0),
        )
    except OSError as exc:
        raise VerificationError("baseline_read_failed") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_JSON_BYTES:
            raise VerificationError("baseline_read_failed")
        payload = bytearray()
        while len(payload) <= MAX_JSON_BYTES:
            try:
                chunk = os.read(descriptor, MAX_JSON_BYTES + 1 - len(payload))
            except InterruptedError:
                continue
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) > MAX_JSON_BYTES:
            raise VerificationError("baseline_read_failed")
    finally:
        os.close(descriptor)
    return _json_loads_object(bytes(payload), error_code="baseline_evidence_invalid")


def _parse_promtool_sample(payload: bytes) -> tuple[float, float]:
    decoded = _json_loads_object(payload, error_code="promtool_result_invalid")
    if decoded.get("status") != "success":
        raise VerificationError("promtool_result_invalid")
    data = decoded.get("data")
    if not isinstance(data, dict) or data.get("resultType") != "vector":
        raise VerificationError("promtool_result_invalid")
    result = data.get("result")
    if not isinstance(result, list) or len(result) != 1:
        raise VerificationError("promtool_vector_missing")
    sample = result[0]
    if not isinstance(sample, dict):
        raise VerificationError("promtool_result_invalid")
    value = sample.get("value")
    if (
        not isinstance(value, list)
        or len(value) != 2
        or isinstance(value[0], bool)
        or not isinstance(value[0], (int, float))
        or not isinstance(value[1], str)
    ):
        raise VerificationError("promtool_result_invalid")
    if not math.isfinite(float(value[0])):
        raise VerificationError("promtool_result_invalid")
    try:
        numeric = float(value[1])
    except ValueError as exc:
        raise VerificationError("promtool_result_invalid") from exc
    if not math.isfinite(numeric):
        raise VerificationError("promtool_value_nonfinite")
    return float(value[0]), numeric


def _parse_promtool_vector(payload: bytes) -> float:
    """Compatibility scalar parser over the strict timestamp/value sample parser."""

    return _parse_promtool_sample(payload)[1]


def _hash_container_config_tar(payload: bytes) -> str:
    """Hash exactly one safe regular config member from bounded `docker cp` tar bytes."""

    if not payload or len(payload) > MAX_JSON_BYTES:
        raise VerificationError("prometheus_config_tar_invalid")
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
            members = archive.getmembers()
            if len(members) != 1:
                raise VerificationError("prometheus_config_tar_invalid")
            member = members[0]
            member_path = PurePosixPath(member.name)
            if (
                not member.isfile()
                or member_path.is_absolute()
                or member_path.name != "prometheus.yml"
                or ".." in member_path.parts
                or member.size < 0
                or member.size > MAX_JSON_BYTES
            ):
                raise VerificationError("prometheus_config_tar_invalid")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise VerificationError("prometheus_config_tar_invalid")
            config_bytes = extracted.read(member.size + 1)
            if len(config_bytes) != member.size or extracted.read(1):
                raise VerificationError("prometheus_config_tar_invalid")
            archive_offset = archive.offset
            trailing = payload[archive_offset:]
            if (
                archive_offset < 0
                or archive_offset % tarfile.BLOCKSIZE != 0
                or len(trailing) < 2 * tarfile.BLOCKSIZE
                or len(trailing) % tarfile.BLOCKSIZE != 0
                or any(trailing)
            ):
                raise VerificationError("prometheus_config_tar_invalid")
    except VerificationError:
        raise
    except (EOFError, OSError, RecursionError, tarfile.TarError, ValueError) as exc:
        raise VerificationError("prometheus_config_tar_invalid") from exc
    return _sha256_fingerprint(config_bytes)


def _parse_retention_days(arguments: object) -> int:
    if not isinstance(arguments, list) or not all(isinstance(item, str) for item in arguments):
        raise VerificationError("prometheus_retention_unavailable")
    matches = [match for item in arguments if (match := _RETENTION_RE.fullmatch(item))]
    if len(matches) != 1:
        raise VerificationError("prometheus_retention_unavailable")
    return int(matches[0].group(1))


def _parse_pinned_image_reference(value: object) -> str:
    if (
        not isinstance(value, str)
        or "://" in value
        or not _PINNED_IMAGE_REFERENCE_RE.fullmatch(value)
    ):
        raise VerificationError("prometheus_image_reference_invalid")
    return value


def _parse_container_ids(payload: bytes, *, error_code: str) -> list[str]:
    try:
        text = payload.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise VerificationError(error_code) from exc
    identifiers = [line.strip() for line in text.splitlines() if line.strip()]
    if not identifiers or len(set(identifiers)) != len(identifiers):
        raise VerificationError(error_code)
    if any(not _CONTAINER_ID_RE.fullmatch(identifier) for identifier in identifiers):
        raise VerificationError(error_code)
    return identifiers


def _parse_uvicorn_processes(payload: bytes) -> tuple[int, str]:
    try:
        lines = payload.decode("utf-8", errors="strict").splitlines()
    except UnicodeDecodeError as exc:
        raise VerificationError("uvicorn_topology_unavailable") from exc
    if len(lines) < 2:
        raise VerificationError("uvicorn_topology_unavailable")
    matching_rows = [line.strip() for line in lines[1:] if _UVICORN_RE.search(line.strip())]
    identity = _sha256_fingerprint("\n".join(matching_rows).encode())
    return len(matching_rows), identity


def _parse_container_inspect(payload: bytes) -> list[dict[str, object]]:
    try:
        inspected = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise VerificationError("container_inspect_invalid") from exc
    if (
        not isinstance(inspected, list)
        or len(inspected) != 2
        or not all(isinstance(item, dict) for item in inspected)
    ):
        raise VerificationError("container_inspect_invalid")
    return inspected


class DockerPromtoolClient:
    """Derive live runtime truth and run fixed private promtool operations."""

    def __init__(self, *, docker: str, compose_file: Path) -> None:
        self._docker = docker
        self._compose_prefix = [
            docker,
            "compose",
            "-f",
            os.fspath(compose_file),
        ]
        self._bound_prometheus_container_id: str | None = None

    @classmethod
    def create(cls, *, compose_file: Path) -> DockerPromtoolClient:
        docker = shutil.which("docker")
        if docker is None or not os.path.isabs(docker) or not os.access(docker, os.X_OK):
            raise VerificationError("docker_unavailable")
        return cls(docker=docker, compose_file=compose_file)

    def _run_docker(
        self,
        arguments: list[str],
        *,
        error_code: str,
    ) -> _CommandResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._run_docker_async(arguments, error_code=error_code))
        raise VerificationError("docker_sync_context_invalid")

    @staticmethod
    async def _read_bounded_stream(
        stream: asyncio.StreamReader,
        target: bytearray,
        aggregate_size: list[int],
    ) -> None:
        while True:
            read_size = min(65_536, max(1, MAX_JSON_BYTES + 1 - aggregate_size[0]))
            chunk = await stream.read(read_size)
            if not chunk:
                return
            aggregate_size[0] += len(chunk)
            if aggregate_size[0] > MAX_JSON_BYTES:
                raise VerificationError("docker_output_limit")
            target.extend(chunk)

    @staticmethod
    async def _stop_process(process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(
                process.wait(),
                timeout=PROCESS_CLEANUP_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            process.kill()
            try:
                await asyncio.wait_for(
                    process.wait(),
                    timeout=PROCESS_CLEANUP_TIMEOUT_SECONDS,
                )
            except TimeoutError as exc:
                raise VerificationError("docker_termination_failed") from exc

    async def _cancel_readers_and_stop(
        self,
        process: asyncio.subprocess.Process,
        readers: list[asyncio.Task[None]],
    ) -> None:
        for reader in readers:
            reader.cancel()
        await asyncio.gather(*readers, return_exceptions=True)
        await self._stop_process(process)

    async def _run_docker_async(
        self,
        arguments: list[str],
        *,
        error_code: str,
    ) -> _CommandResult:
        argv = [self._docker, *arguments]
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise VerificationError(error_code) from exc
        if process.stdout is None or process.stderr is None:
            await self._stop_process(process)
            raise VerificationError(error_code)

        stdout = bytearray()
        stderr = bytearray()
        aggregate_size = [0]
        readers = [
            asyncio.create_task(self._read_bounded_stream(process.stdout, stdout, aggregate_size)),
            asyncio.create_task(self._read_bounded_stream(process.stderr, stderr, aggregate_size)),
        ]

        async def _finish() -> int:
            await asyncio.gather(*readers)
            return await process.wait()

        try:
            return_code = await asyncio.wait_for(
                _finish(),
                timeout=COMMAND_TIMEOUT_SECONDS,
            )
        except asyncio.CancelledError:
            cleanup_task = asyncio.create_task(self._cancel_readers_and_stop(process, readers))
            while not cleanup_task.done():
                try:
                    await asyncio.shield(cleanup_task)
                except asyncio.CancelledError:
                    if cleanup_task.done():
                        break
            with suppress(Exception):
                cleanup_task.result()
            raise
        except TimeoutError as exc:
            await self._cancel_readers_and_stop(process, readers)
            raise VerificationError("docker_timeout") from exc
        except VerificationError:
            await self._cancel_readers_and_stop(process, readers)
            raise
        except Exception as exc:
            await self._cancel_readers_and_stop(process, readers)
            raise VerificationError(error_code) from exc
        if return_code != 0:
            raise VerificationError(error_code)
        return _CommandResult(return_code, bytes(stdout), bytes(stderr))

    def _run_compose(self, arguments: list[str], *, error_code: str) -> bytes:
        result = self._run_docker(
            [*self._compose_prefix[1:], *arguments],
            error_code=error_code,
        )
        return result.stdout

    def _run_promtool(self, arguments: list[str]) -> _CommandResult:
        if self._bound_prometheus_container_id is None:
            raise VerificationError("prometheus_container_unbound")
        return self._run_docker(
            [
                "exec",
                self._bound_prometheus_container_id,
                "/bin/promtool",
                *arguments,
            ],
            error_code="promtool_execution_failed",
        )

    def collect_live_snapshot(self) -> LiveRuntimeSnapshot:
        app_ids = _parse_container_ids(
            self._run_compose(["ps", "-q", "app"], error_code="app_container_unavailable"),
            error_code="app_container_unavailable",
        )
        prometheus_ids = _parse_container_ids(
            self._run_compose(
                ["ps", "-q", "prometheus"],
                error_code="prometheus_container_unavailable",
            ),
            error_code="prometheus_container_unavailable",
        )
        if len(app_ids) != 1 or len(prometheus_ids) != 1:
            raise VerificationError("container_topology_mismatch")
        if self._bound_prometheus_container_id is None:
            self._bound_prometheus_container_id = prometheus_ids[0]

        inspect_result = self._run_docker(
            ["inspect", app_ids[0], prometheus_ids[0]],
            error_code="container_inspect_failed",
        )
        inspected = _parse_container_inspect(inspect_result.stdout)
        app_inspect, prometheus_inspect = inspected
        app_inspect_id = app_inspect.get("Id")
        prometheus_inspect_id = prometheus_inspect.get("Id")
        if (
            not isinstance(app_inspect_id, str)
            or not _CONTAINER_ID_RE.fullmatch(app_inspect_id)
            or not app_inspect_id.startswith(app_ids[0])
            or not isinstance(prometheus_inspect_id, str)
            or not _CONTAINER_ID_RE.fullmatch(prometheus_inspect_id)
            or not prometheus_inspect_id.startswith(prometheus_ids[0])
        ):
            raise VerificationError("container_inspect_invalid")

        app_image = app_inspect.get("Image")
        prometheus_image = prometheus_inspect.get("Image")
        if not isinstance(app_image, str) or not _DIGEST_RE.fullmatch(app_image):
            raise VerificationError("app_image_identity_invalid")
        if not isinstance(prometheus_image, str) or not _DIGEST_RE.fullmatch(prometheus_image):
            raise VerificationError("prometheus_image_identity_invalid")

        app_config = app_inspect.get("Config")
        if not isinstance(app_config, dict):
            raise VerificationError("release_identity_unavailable")
        labels = app_config.get("Labels")
        if not isinstance(labels, dict):
            raise VerificationError("release_identity_unavailable")
        release_id = labels.get("org.opencontainers.image.revision")
        if not isinstance(release_id, str) or not _RELEASE_REVISION_RE.fullmatch(release_id):
            raise VerificationError("release_identity_unavailable")

        prometheus_config = prometheus_inspect.get("Config")
        if not isinstance(prometheus_config, dict):
            raise VerificationError("prometheus_image_reference_invalid")
        prometheus_image_reference = _parse_pinned_image_reference(prometheus_config.get("Image"))

        mounts = prometheus_inspect.get("Mounts")
        if not isinstance(mounts, list) or not all(isinstance(item, dict) for item in mounts):
            raise VerificationError("prometheus_mounts_invalid")
        config_mounts = [
            mount
            for mount in mounts
            if mount.get("Destination") == "/etc/prometheus/prometheus.yml"
        ]
        volume_mounts = [mount for mount in mounts if mount.get("Destination") == "/prometheus"]
        if len(config_mounts) != 1 or len(volume_mounts) != 1:
            raise VerificationError("prometheus_mounts_invalid")
        if config_mounts[0].get("Type") != "bind" or volume_mounts[0].get("Type") != "volume":
            raise VerificationError("prometheus_mounts_invalid")
        config_copy = self._run_docker(
            [
                "cp",
                f"{prometheus_ids[0]}:/etc/prometheus/prometheus.yml",
                "-",
            ],
            error_code="prometheus_config_copy_failed",
        )
        config_sha256 = _hash_container_config_tar(config_copy.stdout)
        volume_name = volume_mounts[0].get("Name")
        if not isinstance(volume_name, str) or not _SAFE_IDENTITY_RE.fullmatch(volume_name):
            raise VerificationError("prometheus_volume_identity_invalid")

        retention_days = _parse_retention_days(prometheus_inspect.get("Args"))
        top_result = self._run_docker(
            ["top", app_ids[0], "-eo", "pid,lstart,args"],
            error_code="uvicorn_topology_unavailable",
        )
        uvicorn_process_count, uvicorn_process_identity = _parse_uvicorn_processes(
            top_result.stdout
        )

        return LiveRuntimeSnapshot(
            app_container_id=app_ids[0],
            prometheus_container_id=prometheus_ids[0],
            release_id=release_id,
            app_image_id=app_image,
            prometheus_image_id=prometheus_image,
            prometheus_image_reference=prometheus_image_reference,
            config_sha256=config_sha256,
            volume_id=volume_name,
            api_container_count=len(app_ids),
            prometheus_container_count=len(prometheus_ids),
            uvicorn_process_count=uvicorn_process_count,
            uvicorn_process_identity=uvicorn_process_identity,
            retention_days=retention_days,
        )

    def check_healthy(self) -> bool:
        try:
            self._run_promtool(["check", "healthy", f"--url={PROMETHEUS_URL}"])
        except VerificationError:
            return False
        return True

    def check_ready(self) -> bool:
        try:
            self._run_promtool(["check", "ready", f"--url={PROMETHEUS_URL}"])
        except VerificationError:
            return False
        return True

    def get_evaluation_anchor(self) -> datetime:
        try:
            result = self._run_promtool(
                ["query", "instant", "-o", "json", PROMETHEUS_URL, "time()"]
            )
        except VerificationError as exc:
            raise VerificationError("evaluation_anchor_unavailable") from exc
        sample_timestamp, value = _parse_promtool_sample(result.stdout)
        if abs(sample_timestamp - value) > 0.001:
            raise VerificationError("evaluation_anchor_invalid")
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as exc:
            raise VerificationError("evaluation_anchor_invalid") from exc

    def query_scalar(self, expression: str, *, evaluation_time: str) -> float:
        if "or vector(0)" in expression:
            raise VerificationError("missing_as_zero_forbidden")
        try:
            parsed_time = _parse_rfc3339_utc(evaluation_time)
        except argparse.ArgumentTypeError as exc:
            raise VerificationError("evaluation_anchor_invalid") from exc
        if _canonical_timestamp(parsed_time) != evaluation_time:
            raise VerificationError("evaluation_anchor_invalid")
        try:
            result = self._run_promtool(
                [
                    "query",
                    "instant",
                    "-o",
                    "json",
                    f"--time={evaluation_time}",
                    PROMETHEUS_URL,
                    expression,
                ]
            )
        except VerificationError as exc:
            raise VerificationError("promtool_query_failed") from exc
        return _parse_promtool_vector(result.stdout)


def _identity_snapshot(snapshot: LiveRuntimeSnapshot) -> dict[str, str]:
    return {
        "app_container": snapshot.app_container_id,
        "prometheus_container": snapshot.prometheus_container_id,
        "release": snapshot.release_id,
        "app_image": snapshot.app_image_id,
        "prometheus_image": snapshot.prometheus_image_id,
        "prometheus_image_reference": snapshot.prometheus_image_reference,
        "prometheus_config": snapshot.config_sha256,
        "prometheus_volume": snapshot.volume_id,
        "uvicorn_process": snapshot.uvicorn_process_identity,
    }


def _topology_snapshot(snapshot: LiveRuntimeSnapshot) -> dict[str, int]:
    return {
        "api_containers": snapshot.api_container_count,
        "prometheus_containers": snapshot.prometheus_container_count,
        "uvicorn_processes": snapshot.uvicorn_process_count,
    }


def _sha256_fingerprint(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _source_fingerprint(asset_type: str, value: str) -> str:
    payload = json.dumps(
        {"asset_type": asset_type, "value": value},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return _sha256_fingerprint(payload)


def _runtime_upstream_assets(snapshot: LiveRuntimeSnapshot) -> list[dict[str, str]]:
    return [
        {
            "asset_type": "app_release",
            "role": "release",
            "fingerprint": _source_fingerprint("app_release", snapshot.release_id),
        },
        {
            "asset_type": "runtime_container",
            "role": "app_container",
            "fingerprint": _source_fingerprint("app_container", snapshot.app_container_id),
        },
        {
            "asset_type": "container_image",
            "role": "app_image",
            "fingerprint": _source_fingerprint("app_image", snapshot.app_image_id),
        },
        {
            "asset_type": "runtime_container",
            "role": "prometheus_container",
            "fingerprint": _source_fingerprint(
                "prometheus_container", snapshot.prometheus_container_id
            ),
        },
        {
            "asset_type": "container_image",
            "role": "prometheus_image",
            "fingerprint": _source_fingerprint("prometheus_image", snapshot.prometheus_image_id),
        },
        {
            "asset_type": "container_image_reference",
            "role": "prometheus_image_reference",
            "fingerprint": _source_fingerprint(
                "prometheus_image_reference", snapshot.prometheus_image_reference
            ),
        },
        {
            "asset_type": "prometheus_config",
            "role": "scrape_config",
            "fingerprint": _source_fingerprint("prometheus_config", snapshot.config_sha256),
        },
        {
            "asset_type": "docker_volume",
            "role": "tsdb",
            "fingerprint": _source_fingerprint("prometheus_volume", snapshot.volume_id),
        },
        {
            "asset_type": "runtime_process",
            "role": "uvicorn_process",
            "fingerprint": snapshot.uvicorn_process_identity,
        },
    ]


def _idempotency_projection(evidence: dict[str, object]) -> dict[str, object]:
    window = evidence.get("window")
    canonical_t0 = (
        window.get("t0") if evidence.get("mode") == "final" and isinstance(window, dict) else None
    )
    return {
        "schema": evidence.get("schema"),
        "asset_type": evidence.get("asset_type"),
        "policy_version": evidence.get("policy_version"),
        "mode": evidence.get("mode"),
        "observed_at": evidence.get("observed_at"),
        "t0": canonical_t0,
        "upstream_assets": evidence.get("upstream_assets"),
    }


def _fingerprint_projection(evidence: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in evidence.items() if key != "fingerprint"}


def _canonical_object_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _attach_asset_contract(
    evidence: dict[str, object],
    *,
    snapshot: LiveRuntimeSnapshot | None,
    baseline: dict[str, object] | None,
) -> None:
    evidence["asset_type"] = ASSET_TYPE
    evidence["policy_version"] = POLICY_VERSION
    upstream_assets = _runtime_upstream_assets(snapshot) if snapshot is not None else []
    baseline_fingerprint = baseline.get("fingerprint") if baseline is not None else None
    if isinstance(baseline_fingerprint, str) and _DIGEST_RE.fullmatch(baseline_fingerprint):
        upstream_assets.append(
            {
                "asset_type": ASSET_TYPE,
                "role": "baseline_evidence",
                "fingerprint": baseline_fingerprint,
            }
        )
    evidence["upstream_assets"] = upstream_assets
    evidence["replay"] = dict(_REPLAY_CONTRACT)
    evidence["admission"] = dict(_ADMISSION_CONTRACT)
    evidence["idempotency_key"] = _sha256_fingerprint(
        _canonical_object_bytes(_idempotency_projection(evidence))
    )
    evidence["fingerprint"] = _sha256_fingerprint(
        _canonical_object_bytes(_fingerprint_projection(evidence))
    )


def _is_finite_number_or_none(value: object) -> bool:
    return value is None or (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _is_canonical_timestamp_or_none(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        return _canonical_timestamp(_parse_rfc3339_utc(value)) == value
    except argparse.ArgumentTypeError:
        return False


def _validate_evidence_structure(evidence: dict[str, object]) -> None:
    if set(evidence) != _EVIDENCE_FIELDS:
        raise VerificationError("evidence_asset_invalid")
    mode = evidence.get("mode")
    decision = evidence.get("decision")
    reasons = evidence.get("reasons")
    if (
        evidence.get("schema") != SCHEMA
        or not isinstance(mode, str)
        or mode not in {"baseline", "checkpoint", "final"}
        or not isinstance(decision, str)
        or decision not in {"PASS", "HOLD"}
        or not isinstance(reasons, list)
        or len(reasons) > 128
        or any(
            not isinstance(reason, str) or not _REASON_CODE_RE.fullmatch(reason)
            for reason in reasons
        )
        or reasons != sorted(set(reasons))
        or (decision == "PASS" and reasons)
        or (decision == "HOLD" and not reasons)
        or evidence.get("authority") != AUTHORITY
    ):
        raise VerificationError("evidence_asset_invalid")

    checks = evidence.get("checks")
    identities = evidence.get("identities")
    topology = evidence.get("topology")
    target = evidence.get("target")
    aliases = evidence.get("aliases")
    window = evidence.get("window")
    retention_days = evidence.get("retention_days")
    observed_at = evidence.get("observed_at")
    if (
        not isinstance(checks, dict)
        or set(checks) != {"prometheus_healthy", "prometheus_ready"}
        or any(not isinstance(value, bool) for value in checks.values())
        or not isinstance(identities, dict)
        or set(identities) != _IDENTITY_FIELDS
        or any(value is not None and not isinstance(value, str) for value in identities.values())
        or not (
            all(value is None for value in identities.values())
            or all(isinstance(value, str) for value in identities.values())
        )
        or not isinstance(topology, dict)
        or set(topology) != _TOPOLOGY_FIELDS
        or any(
            value is not None
            and (isinstance(value, bool) or not isinstance(value, int) or value < 0)
            for value in topology.values()
        )
        or not (
            all(value is None for value in topology.values())
            or all(
                isinstance(value, int) and not isinstance(value, bool)
                for value in topology.values()
            )
        )
        or (
            retention_days is not None
            and (
                isinstance(retention_days, bool)
                or not isinstance(retention_days, int)
                or retention_days <= 0
            )
        )
        or not _is_canonical_timestamp_or_none(observed_at)
    ):
        raise VerificationError("evidence_asset_invalid")

    if not isinstance(target, dict) or set(target) != _TARGET_FIELDS:
        raise VerificationError("evidence_asset_invalid")
    expected_count = target.get("expected_count")
    if (
        isinstance(expected_count, bool)
        or not isinstance(expected_count, int)
        or expected_count != 1
    ):
        raise VerificationError("evidence_asset_invalid")
    for field_name in (
        "observed_count",
        "current_up",
        "minimum_up",
        "sample_count",
        "restart_changes",
    ):
        if not _is_finite_number_or_none(target.get(field_name)):
            raise VerificationError("evidence_asset_invalid")
    required_samples = target.get("required_samples")
    if required_samples is not None and (
        isinstance(required_samples, bool)
        or not isinstance(required_samples, int)
        or required_samples < 0
    ):
        raise VerificationError("evidence_asset_invalid")

    if not isinstance(aliases, list) or len(aliases) != len(ALIAS_ROUTES):
        raise VerificationError("evidence_asset_invalid")
    for expected_route, alias in zip(ALIAS_ROUTES, aliases):
        if not isinstance(alias, dict):
            raise VerificationError("evidence_asset_invalid")
        observation = alias.get("observation")
        if (
            set(alias) != _ALIAS_FIELDS
            or alias.get("method") != "POST"
            or alias.get("route") != expected_route
            or not isinstance(observation, str)
            or observation not in _ALIAS_OBSERVATIONS
            or any(
                not _is_finite_number_or_none(alias.get(field_name))
                for field_name in ("current_value", "increase", "resets")
            )
        ):
            raise VerificationError("evidence_asset_invalid")

    if (
        not isinstance(window, dict)
        or set(window) != _WINDOW_FIELDS
        or any(
            not _is_canonical_timestamp_or_none(window.get(field_name))
            for field_name in ("started_at", "t0", "ended_at")
        )
        or window.get("ended_at") != observed_at
        or isinstance(window.get("duration_seconds"), bool)
        or not isinstance(window.get("duration_seconds"), int)
        or window["duration_seconds"] < 0
        or not isinstance(window.get("complete"), bool)
        or (mode != "final" and window.get("t0") is not None)
    ):
        raise VerificationError("evidence_asset_invalid")

    if decision == "PASS":
        if (
            not isinstance(observed_at, str)
            or checks != {"prometheus_healthy": True, "prometheus_ready": True}
            or any(not isinstance(value, str) for value in identities.values())
            or topology != {"api_containers": 1, "prometheus_containers": 1, "uvicorn_processes": 1}
            or not isinstance(retention_days, int)
            or retention_days < MIN_RETENTION_DAYS
            or target.get("observed_count") != 1.0
            or target.get("current_up") != 1.0
            or any(alias.get("observation") != "observed_exact_zero" for alias in aliases)
            or window.get("complete") is not True
            or not isinstance(window.get("started_at"), str)
            or not isinstance(window.get("ended_at"), str)
        ):
            raise VerificationError("evidence_asset_invalid")
        try:
            start_time = _parse_rfc3339_utc(cast(str, window["started_at"]))
            end_time = _parse_rfc3339_utc(cast(str, window["ended_at"]))
        except argparse.ArgumentTypeError as exc:
            raise VerificationError("evidence_asset_invalid") from exc
        duration_seconds = cast(int, window["duration_seconds"])
        alias_records = cast(list[dict[str, object]], aliases)
        if mode == "baseline":
            if (
                window.get("t0") is not None
                or window.get("started_at") != observed_at
                or duration_seconds != 0
                or any(
                    target.get(field_name) is not None
                    for field_name in (
                        "minimum_up",
                        "sample_count",
                        "required_samples",
                        "restart_changes",
                    )
                )
                or any(
                    alias.get("current_value") != 0.0
                    or alias.get("increase") is not None
                    or alias.get("resets") is not None
                    for alias in alias_records
                )
            ):
                raise VerificationError("evidence_asset_invalid")
        elif mode == "checkpoint":
            required_samples = target.get("required_samples")
            sample_count = target.get("sample_count")
            if (
                window.get("t0") is not None
                or duration_seconds <= 0
                or int((end_time - start_time).total_seconds()) != duration_seconds
                or target.get("minimum_up") != 1.0
                or isinstance(required_samples, bool)
                or not isinstance(required_samples, int)
                or required_samples < 1
                or isinstance(sample_count, bool)
                or not isinstance(sample_count, (int, float))
                or sample_count < required_samples
                or target.get("restart_changes") != 0.0
                or any(
                    alias.get("current_value") != 0.0
                    or alias.get("increase") != 0.0
                    or alias.get("resets") != 0.0
                    for alias in alias_records
                )
            ):
                raise VerificationError("evidence_asset_invalid")
        else:
            t0_value = window.get("t0")
            required_samples = target.get("required_samples")
            sample_count = target.get("sample_count")
            if not isinstance(t0_value, str):
                raise VerificationError("evidence_asset_invalid")
            try:
                t0_time = _parse_rfc3339_utc(t0_value)
            except argparse.ArgumentTypeError as exc:
                raise VerificationError("evidence_asset_invalid") from exc
            if (
                duration_seconds < int(FINAL_WINDOW.total_seconds())
                or int((end_time - start_time).total_seconds()) != duration_seconds
                or start_time > t0_time
                or end_time - t0_time < FINAL_WINDOW
                or target.get("minimum_up") != 1.0
                or isinstance(required_samples, bool)
                or not isinstance(required_samples, int)
                or required_samples < FINAL_MIN_SAMPLES
                or isinstance(sample_count, bool)
                or not isinstance(sample_count, (int, float))
                or sample_count < required_samples
                or target.get("restart_changes") != 0.0
                or any(
                    alias.get("current_value") != 0.0
                    or alias.get("increase") != 0.0
                    or alias.get("resets") != 0.0
                    for alias in alias_records
                )
            ):
                raise VerificationError("evidence_asset_invalid")


def _validate_evidence_asset(evidence: dict[str, object]) -> None:
    _validate_evidence_structure(evidence)
    if (
        evidence.get("asset_type") != ASSET_TYPE
        or evidence.get("policy_version") != POLICY_VERSION
        or evidence.get("replay") != _REPLAY_CONTRACT
        or evidence.get("admission") != _ADMISSION_CONTRACT
    ):
        raise VerificationError("evidence_asset_invalid")
    upstream_assets = evidence.get("upstream_assets")
    if not isinstance(upstream_assets, list):
        raise VerificationError("evidence_asset_invalid")
    for upstream in upstream_assets:
        if (
            not isinstance(upstream, dict)
            or set(upstream) != {"asset_type", "role", "fingerprint"}
            or not isinstance(upstream.get("asset_type"), str)
            or not isinstance(upstream.get("role"), str)
            or not isinstance(upstream.get("fingerprint"), str)
            or not _DIGEST_RE.fullmatch(upstream["fingerprint"])
        ):
            raise VerificationError("evidence_asset_invalid")
    identities = evidence.get("identities")
    if not isinstance(identities, dict):
        raise VerificationError("evidence_asset_invalid")
    identity_keys = (
        "app_container",
        "prometheus_container",
        "release",
        "app_image",
        "prometheus_image",
        "prometheus_image_reference",
        "prometheus_config",
        "prometheus_volume",
        "uvicorn_process",
    )
    identity_values = [identities.get(key) for key in identity_keys]
    if all(isinstance(value, str) for value in identity_values):
        app_container_id = cast(str, identity_values[0])
        prometheus_container_id = cast(str, identity_values[1])
        release_id = cast(str, identity_values[2])
        app_image_id = cast(str, identity_values[3])
        prometheus_image_id = cast(str, identity_values[4])
        prometheus_image_reference = cast(str, identity_values[5])
        config_sha256 = cast(str, identity_values[6])
        volume_id = cast(str, identity_values[7])
        uvicorn_process_identity = cast(str, identity_values[8])
        try:
            _parse_pinned_image_reference(prometheus_image_reference)
        except VerificationError as exc:
            raise VerificationError("evidence_asset_invalid") from exc
        if (
            not _CONTAINER_ID_RE.fullmatch(app_container_id)
            or not _CONTAINER_ID_RE.fullmatch(prometheus_container_id)
            or not _RELEASE_REVISION_RE.fullmatch(release_id)
            or not _DIGEST_RE.fullmatch(app_image_id)
            or not _DIGEST_RE.fullmatch(prometheus_image_id)
            or not _DIGEST_RE.fullmatch(config_sha256)
            or not _SAFE_IDENTITY_RE.fullmatch(volume_id)
            or not _DIGEST_RE.fullmatch(uvicorn_process_identity)
        ):
            raise VerificationError("evidence_asset_invalid")
        snapshot = LiveRuntimeSnapshot(
            app_container_id=app_container_id,
            prometheus_container_id=prometheus_container_id,
            release_id=release_id,
            app_image_id=app_image_id,
            prometheus_image_id=prometheus_image_id,
            prometheus_image_reference=prometheus_image_reference,
            config_sha256=config_sha256,
            volume_id=volume_id,
            api_container_count=1,
            prometheus_container_count=1,
            uvicorn_process_count=1,
            uvicorn_process_identity=uvicorn_process_identity,
            retention_days=MIN_RETENTION_DAYS,
        )
        expected_runtime_assets = _runtime_upstream_assets(snapshot)
        if upstream_assets[:9] != expected_runtime_assets or len(upstream_assets) not in {9, 10}:
            raise VerificationError("evidence_asset_invalid")
        if len(upstream_assets) == 10 and (
            upstream_assets[9].get("asset_type") != ASSET_TYPE
            or upstream_assets[9].get("role") != "baseline_evidence"
        ):
            raise VerificationError("evidence_asset_invalid")
    elif upstream_assets and not (
        len(upstream_assets) == 1
        and upstream_assets[0].get("asset_type") == ASSET_TYPE
        and upstream_assets[0].get("role") == "baseline_evidence"
    ):
        raise VerificationError("evidence_asset_invalid")
    idempotency_key = evidence.get("idempotency_key")
    fingerprint = evidence.get("fingerprint")
    if (
        not isinstance(idempotency_key, str)
        or not _DIGEST_RE.fullmatch(idempotency_key)
        or idempotency_key
        != _sha256_fingerprint(_canonical_object_bytes(_idempotency_projection(evidence)))
        or not isinstance(fingerprint, str)
        or not _DIGEST_RE.fullmatch(fingerprint)
        or fingerprint
        != _sha256_fingerprint(_canonical_object_bytes(_fingerprint_projection(evidence)))
    ):
        raise VerificationError("evidence_asset_invalid")


def _query(
    client: PromtoolClient,
    expression: str,
    *,
    evaluation_time: str | None,
    reason: str,
    reasons: list[str],
) -> float | None:
    if evaluation_time is None:
        reasons.extend((reason, "evaluation_anchor_unavailable"))
        return None
    try:
        value = client.query_scalar(expression, evaluation_time=evaluation_time)
    except VerificationError as exc:
        reasons.extend((reason, exc.code))
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        reasons.extend((reason, "promtool_value_nonfinite"))
        return None
    return float(value)


def _check_exact_zero(
    value: float | None,
    *,
    prefix: str,
    reasons: list[str],
) -> str:
    if value is None:
        reasons.append(f"{prefix}_missing")
        return "missing"
    if value < 0:
        reasons.append(f"{prefix}_negative")
        return "observed_negative"
    if value > 0:
        reasons.append(f"{prefix}_positive")
        return "observed_positive"
    return "observed_exact_zero"


def _baseline_start(
    baseline: dict[str, object] | None,
    *,
    config: VerificationConfig,
    snapshot: LiveRuntimeSnapshot | None,
    observed_at: datetime | None,
    reasons: list[str],
) -> datetime | None:
    if config.mode == "baseline":
        return observed_at
    if baseline is None:
        reasons.append("baseline_evidence_invalid")
        return None
    try:
        _validate_evidence_asset(baseline)
    except VerificationError as exc:
        reasons.append(exc.code)
        return None
    if snapshot is None:
        reasons.append("live_snapshot_unavailable")
        return None
    aliases = baseline.get("aliases")
    expected_aliases = [
        {
            "method": "POST",
            "route": route,
            "current_value": 0.0,
            "increase": None,
            "resets": None,
            "observation": "observed_exact_zero",
        }
        for route in ALIAS_ROUTES
    ]
    target = baseline.get("target")
    checks = baseline.get("checks")
    window = baseline.get("window")
    if (
        baseline.get("schema") != SCHEMA
        or baseline.get("mode") != "baseline"
        or baseline.get("decision") != "PASS"
        or baseline.get("reasons") != []
        or baseline.get("authority") != AUTHORITY
        or baseline.get("identities") != _identity_snapshot(snapshot)
        or baseline.get("topology") != _topology_snapshot(snapshot)
        or baseline.get("retention_days") != snapshot.retention_days
        or aliases != expected_aliases
        or checks != {"prometheus_healthy": True, "prometheus_ready": True}
        or not isinstance(target, dict)
        or target.get("expected_count") != 1
        or target.get("observed_count") != 1.0
        or target.get("current_up") != 1.0
        or target.get("minimum_up") is not None
        or target.get("sample_count") is not None
        or target.get("required_samples") is not None
        or target.get("restart_changes") is not None
        or not isinstance(window, dict)
        or window.get("complete") is not True
        or window.get("t0") is not None
        or window.get("duration_seconds") != 0
    ):
        reasons.append("baseline_evidence_invalid_or_drifted")
        return None
    baseline_observed_at = baseline.get("observed_at")
    if not isinstance(baseline_observed_at, str):
        reasons.append("baseline_evidence_invalid")
        return None
    try:
        parsed_observed_at = _parse_rfc3339_utc(baseline_observed_at)
    except argparse.ArgumentTypeError:
        reasons.append("baseline_evidence_invalid")
        return None
    if (
        window.get("started_at") != baseline_observed_at
        or window.get("ended_at") != baseline_observed_at
    ):
        reasons.append("baseline_evidence_invalid")
        return None
    return parsed_observed_at


def build_evidence(
    config: VerificationConfig,
    client: PromtoolClient,
    *,
    baseline: dict[str, object] | None = None,
    initial_reasons: Sequence[str] = (),
) -> dict[str, object]:
    """Evaluate one bounded snapshot without granting operational authority."""

    reasons = list(initial_reasons)
    snapshot: LiveRuntimeSnapshot | None = None
    try:
        snapshot = client.collect_live_snapshot()
    except VerificationError as exc:
        reasons.extend(("live_snapshot_unavailable", exc.code))
    try:
        healthy = client.check_healthy()
    except VerificationError as exc:
        healthy = False
        reasons.append(exc.code)
    try:
        ready = client.check_ready()
    except VerificationError as exc:
        ready = False
        reasons.append(exc.code)
    if not healthy:
        reasons.append("prometheus_unhealthy")
    if not ready:
        reasons.append("prometheus_not_ready")

    observed_at: datetime | None = None
    evaluation_time: str | None = None
    try:
        live_anchor = client.get_evaluation_anchor()
        if live_anchor.tzinfo is None or live_anchor.utcoffset() != timedelta(0):
            raise VerificationError("evaluation_anchor_invalid")
        observed_at = live_anchor.astimezone(timezone.utc)
        evaluation_time = _canonical_timestamp(observed_at)
    except VerificationError as exc:
        reasons.extend(("evaluation_anchor_unavailable", exc.code))

    identities: dict[str, object] = {
        "app_container": None,
        "prometheus_container": None,
        "release": None,
        "app_image": None,
        "prometheus_image": None,
        "prometheus_image_reference": None,
        "prometheus_config": None,
        "prometheus_volume": None,
        "uvicorn_process": None,
    }
    topology: dict[str, object] = {
        "api_containers": None,
        "prometheus_containers": None,
        "uvicorn_processes": None,
    }
    retention_days: int | None
    if snapshot is None:
        retention_days = None
    else:
        identities.update(_identity_snapshot(snapshot))
        topology.update(_topology_snapshot(snapshot))
        retention_days = snapshot.retention_days
    if topology != {
        "api_containers": 1,
        "prometheus_containers": 1,
        "uvicorn_processes": 1,
    }:
        reasons.append("topology_mismatch")
    if retention_days is None or retention_days < MIN_RETENTION_DAYS:
        reasons.append("retention_too_short")

    target_count = _query(
        client,
        'count(up{job="pulseplate-api"})',
        evaluation_time=evaluation_time,
        reason="target_count_missing",
        reasons=reasons,
    )
    current_up = _query(
        client,
        'min(up{job="pulseplate-api"})',
        evaluation_time=evaluation_time,
        reason="target_up_missing",
        reasons=reasons,
    )
    if target_count is not None and target_count != 1.0:
        reasons.append("target_count_mismatch")
    if current_up is not None and current_up != 1.0:
        reasons.append("target_not_up")

    start = _baseline_start(
        baseline,
        config=config,
        snapshot=snapshot,
        observed_at=observed_at,
        reasons=reasons,
    )
    if start is not None and observed_at is not None and start > observed_at:
        reasons.append("window_order_invalid")
    duration_seconds = (
        max(0, int((observed_at - start).total_seconds()))
        if start is not None and observed_at is not None
        else 0
    )
    t0 = config.t0
    if config.mode == "final":
        if t0 is None:
            reasons.append("t0_required")
        else:
            if start is not None and t0 < start:
                reasons.append("t0_precedes_baseline")
            if observed_at is None or observed_at - t0 < FINAL_WINDOW:
                reasons.append("final_window_too_short")

    range_selector = "30d" if config.mode == "final" else f"{max(1, duration_seconds)}s"
    min_up: float | None = None
    sample_count: float | None = None
    restart_changes: float | None = None
    required_samples: int | None = None
    if config.mode != "baseline":
        min_up = _query(
            client,
            f'min_over_time(up{{job="pulseplate-api"}}[{range_selector}])',
            evaluation_time=evaluation_time,
            reason="up_continuity_missing",
            reasons=reasons,
        )
        sample_count = _query(
            client,
            f'count_over_time(up{{job="pulseplate-api"}}[{range_selector}])',
            evaluation_time=evaluation_time,
            reason="sample_continuity_missing",
            reasons=reasons,
        )
        restart_changes = _query(
            client,
            f'sum(changes(process_start_time_seconds{{job="pulseplate-api"}}'
            f"[{range_selector}]))",
            evaluation_time=evaluation_time,
            reason="restart_evidence_missing",
            reasons=reasons,
        )
        required_samples = (
            FINAL_MIN_SAMPLES
            if config.mode == "final"
            else max(1, duration_seconds // SCRAPE_INTERVAL_SECONDS)
        )
        if min_up is not None and min_up != 1.0:
            reasons.append("scrape_gap_detected")
        if sample_count is not None and sample_count < required_samples:
            reasons.append("sample_count_too_low")
        _check_exact_zero(restart_changes, prefix="process_restart", reasons=reasons)

    aliases: list[dict[str, object]] = []
    for route in ALIAS_ROUTES:
        alias_name = route.rsplit("/", 1)[-1]
        selector = f'method="POST",route="{route}"'
        current = _query(
            client,
            f"sum(http_requests_total{{{selector}}})",
            evaluation_time=evaluation_time,
            reason=f"alias_{alias_name}_current_missing",
            reasons=reasons,
        )
        observation = _check_exact_zero(
            current,
            prefix=f"alias_{alias_name}_current",
            reasons=reasons,
        )
        increase: float | None = None
        resets: float | None = None
        if config.mode != "baseline":
            increase = _query(
                client,
                f"sum(increase(http_requests_total{{{selector}}}[{range_selector}]))",
                evaluation_time=evaluation_time,
                reason=f"alias_{alias_name}_increase_missing",
                reasons=reasons,
            )
            resets = _query(
                client,
                f"sum(resets(http_requests_total{{{selector}}}[{range_selector}]))",
                evaluation_time=evaluation_time,
                reason=f"alias_{alias_name}_reset_missing",
                reasons=reasons,
            )
            increase_observation = _check_exact_zero(
                increase,
                prefix=f"alias_{alias_name}_increase",
                reasons=reasons,
            )
            reset_observation = _check_exact_zero(
                resets,
                prefix=f"alias_{alias_name}_reset",
                reasons=reasons,
            )
            if increase_observation != "observed_exact_zero":
                observation = increase_observation
            if reset_observation != "observed_exact_zero":
                observation = reset_observation
        aliases.append(
            {
                "method": "POST",
                "route": route,
                "current_value": current,
                "increase": increase,
                "resets": resets,
                "observation": observation,
            }
        )

    try:
        post_snapshot = client.collect_live_snapshot()
    except VerificationError as exc:
        post_snapshot = None
        reasons.extend(("runtime_post_census_failed", exc.code))
    if snapshot is not None and post_snapshot != snapshot:
        reasons.append("runtime_identity_drift")

    incomplete_window_reasons = {
        "window_order_invalid",
        "t0_required",
        "t0_precedes_baseline",
        "final_window_too_short",
        "up_continuity_missing",
        "sample_continuity_missing",
        "scrape_gap_detected",
        "sample_count_too_low",
        "process_restart_missing",
        "process_restart_positive",
        "process_restart_negative",
        "runtime_post_census_failed",
        "runtime_identity_drift",
    }
    complete = not any(
        reason in incomplete_window_reasons or reason.startswith("baseline_") or "_reset_" in reason
        for reason in reasons
    )
    unique_reasons = sorted(set(reasons))
    evidence: dict[str, object] = {
        "schema": SCHEMA,
        "mode": config.mode,
        "decision": "PASS" if not unique_reasons else "HOLD",
        "reasons": unique_reasons,
        "observed_at": evaluation_time,
        "checks": {
            "prometheus_healthy": healthy,
            "prometheus_ready": ready,
        },
        "identities": identities,
        "topology": topology,
        "retention_days": retention_days,
        "target": {
            "expected_count": 1,
            "observed_count": target_count,
            "current_up": current_up,
            "minimum_up": min_up,
            "sample_count": sample_count,
            "required_samples": required_samples,
            "restart_changes": restart_changes,
        },
        "aliases": aliases,
        "window": {
            "started_at": _canonical_timestamp(start) if start is not None else None,
            "t0": _canonical_timestamp(t0) if t0 is not None else None,
            "ended_at": evaluation_time,
            "duration_seconds": duration_seconds,
            "complete": complete,
        },
        "authority": dict(AUTHORITY),
    }
    _attach_asset_contract(evidence, snapshot=snapshot, baseline=baseline)
    return evidence


def _canonical_json_bytes(evidence: dict[str, object]) -> bytes:
    return (json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _read_existing_evidence(
    directory_descriptor: int,
    output_name: str,
    no_follow: int,
) -> dict[str, object]:
    try:
        descriptor = os.open(
            output_name,
            os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=directory_descriptor,
        )
    except OSError as exc:
        raise VerificationError("evidence_existing_malformed") from exc
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_size > MAX_JSON_BYTES
        ):
            raise VerificationError("evidence_existing_malformed")
        payload = bytearray()
        while len(payload) <= MAX_JSON_BYTES:
            try:
                chunk = os.read(descriptor, MAX_JSON_BYTES + 1 - len(payload))
            except InterruptedError:
                continue
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) > MAX_JSON_BYTES:
            raise VerificationError("evidence_existing_malformed")
    finally:
        os.close(descriptor)
    try:
        evidence = _json_loads_object(bytes(payload), error_code="evidence_existing_malformed")
        _validate_evidence_asset(evidence)
    except VerificationError as exc:
        raise VerificationError("evidence_existing_malformed") from exc
    return evidence


def write_evidence_new_only(
    evidence_dir: Path,
    output_name: str,
    evidence: dict[str, object],
) -> str:
    """Publish once; identical replay is no-write and divergent replay fails closed."""

    _output_name(output_name)
    _validate_evidence_asset(evidence)
    payload = _canonical_json_bytes(evidence)
    no_follow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if (
        not isinstance(no_follow, int)
        or no_follow <= 0
        or not isinstance(directory_flag, int)
        or directory_flag <= 0
    ):
        raise VerificationError("evidence_write_unavailable")
    try:
        directory_descriptor = os.open(
            evidence_dir,
            os.O_RDONLY | directory_flag | no_follow | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as exc:
        raise VerificationError("evidence_directory_invalid") from exc
    try:
        try:
            descriptor = os.open(
                output_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | no_follow | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=directory_descriptor,
            )
        except FileExistsError:
            existing = _read_existing_evidence(
                directory_descriptor,
                output_name,
                no_follow,
            )
            if existing.get("idempotency_key") != evidence.get("idempotency_key"):
                raise VerificationError("evidence_idempotency_collision")
            if _canonical_json_bytes(existing) != payload:
                raise VerificationError("evidence_replay_divergent")
            return "identical_replay"
        except OSError as exc:
            raise VerificationError("evidence_write_failed") from exc
        try:
            os.fchmod(descriptor, 0o600)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
                raise VerificationError("evidence_write_failed")
            written = 0
            while written < len(payload):
                count = os.write(descriptor, payload[written:])
                if count <= 0:
                    raise VerificationError("evidence_write_failed")
                written += count
            os.fsync(descriptor)
        except OSError as exc:
            raise VerificationError("evidence_write_failed") from exc
        finally:
            os.close(descriptor)
        return "published"
    finally:
        os.close(directory_descriptor)


class _UnavailablePromtoolClient:
    def collect_live_snapshot(self) -> LiveRuntimeSnapshot:
        raise VerificationError("docker_unavailable")

    def get_evaluation_anchor(self) -> datetime:
        raise VerificationError("docker_unavailable")

    def check_healthy(self) -> bool:
        return False

    def check_ready(self) -> bool:
        return False

    def query_scalar(self, _expression: str, *, evaluation_time: str) -> float:
        del evaluation_time
        raise VerificationError("docker_unavailable")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    config = _config_from_args(args)
    initial_reasons: list[str] = []
    baseline: dict[str, object] | None = None
    if config.baseline_evidence is not None:
        try:
            baseline = _read_bounded_regular_json(config.baseline_evidence)
        except VerificationError as exc:
            initial_reasons.append(exc.code)

    try:
        client: PromtoolClient = DockerPromtoolClient.create(compose_file=config.compose_file)
    except VerificationError as exc:
        initial_reasons.append(exc.code)
        client = _UnavailablePromtoolClient()
    evidence = build_evidence(
        config,
        client,
        baseline=baseline,
        initial_reasons=initial_reasons,
    )
    observed_at = evidence.get("observed_at")
    if config.output_name is not None:
        output_name = config.output_name
    elif isinstance(observed_at, str):
        try:
            output_name = _default_output_name(
                config.mode,
                _parse_rfc3339_utc(observed_at),
            )
        except argparse.ArgumentTypeError:
            output_name = f"premium_alias_telemetry_{config.mode}_unavailable.json"
    else:
        output_name = f"premium_alias_telemetry_{config.mode}_unavailable.json"
    try:
        publication = write_evidence_new_only(
            config.evidence_dir,
            output_name,
            evidence,
        )
    except VerificationError as exc:
        print(json.dumps({"decision": "HOLD", "error": exc.code}, sort_keys=True))
        return 2
    print(
        json.dumps(
            {
                "decision": evidence["decision"],
                "evidence_file": output_name,
                "publication": publication,
            },
            sort_keys=True,
        )
    )
    return 0 if evidence["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
