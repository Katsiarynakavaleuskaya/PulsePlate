"""Private bounded process, OCI, and HTTP mechanics."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import http.client
import json
import os
import re
import shutil
import stat
import subprocess  # nosec B404: required for bounded absolute-argv tool execution (remove-by: 2026-10-31, ref: PR-2347)
import sys
import tarfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlencode, urlsplit

_DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
_OCI_MANIFEST = "application/vnd.oci.image.manifest.v1+json"
_OCI_CONFIG = "application/vnd.oci.image.config.v1+json"
_OCI_LAYERS = {
    "application/vnd.oci.image.layer.v1.tar",
    "application/vnd.oci.image.layer.v1.tar+gzip",
    "application/vnd.oci.image.layer.v1.tar+zstd",
}


class TransportError(RuntimeError):
    """Bounded mechanical failure."""


@dataclass(frozen=True)
class ProcessPlan:
    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str]
    timeout_seconds: int
    max_output_bytes: int


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class OCIResult:
    manifest_digest: str
    config_digest: str
    platform: str
    layer_digests: tuple[str, ...]


@dataclass(frozen=True)
class RegistryPlan:
    host: str
    repository: str
    scope: str
    locator: str
    accept: str
    timeout_seconds: int
    max_response_bytes: int
    allowed_redirect_hosts: tuple[str, ...]


@dataclass(frozen=True)
class ProgramObservation:
    path: Path
    sha256: str
    returncode: int
    stdout: str


def resolve_program(name: str) -> Path:
    discovered = shutil.which(name)
    if discovered is None:
        raise TransportError("executable_missing")
    try:
        return Path(discovered).resolve(strict=True)
    except OSError as exc:
        raise TransportError("executable_invalid") from exc


def _safe_executable_links(path: Path, metadata: os.stat_result) -> bool:
    if metadata.st_nlink == 1:
        return True
    return (
        sys.platform == "darwin"
        and metadata.st_uid == 0
        and path.parent in {Path("/usr/bin"), Path("/bin"), Path("/usr/sbin"), Path("/sbin")}
    )


def _checked_program(argv: Sequence[str]) -> None:
    if not argv or any(not isinstance(item, str) or "\x00" in item for item in argv):
        raise TransportError("process_plan_invalid")
    program = Path(argv[0])
    if not program.is_absolute():
        raise TransportError("process_program_not_absolute")
    try:
        metadata = os.lstat(program)
    except OSError as exc:
        raise TransportError("process_program_unavailable") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or not _safe_executable_links(program, metadata)
        or not os.access(program, os.X_OK)
    ):
        raise TransportError("process_program_unsafe")


def hash_regular(path: Path, *, max_bytes: int, executable: bool = False) -> str:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or (before.st_nlink != 1 and not (executable and _safe_executable_links(path, before)))
            or before.st_size > max_bytes
            or (executable and not os.access(path, os.X_OK))
        ):
            raise TransportError("regular_file_unsafe")
        digest = hashlib.sha256()
        observed = 0
        while True:
            chunk = os.read(descriptor, 1_048_576)
            if not chunk:
                break
            observed += len(chunk)
            digest.update(chunk)
        after = os.fstat(descriptor)
        pathname = os.lstat(path)
    except TransportError:
        raise
    except OSError as exc:
        raise TransportError("regular_file_unavailable") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if (
        observed != before.st_size
        or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
        or (after.st_dev, after.st_ino) != (pathname.st_dev, pathname.st_ino)
        or (pathname.st_nlink != 1 and not (executable and _safe_executable_links(path, pathname)))
    ):
        raise TransportError("regular_file_changed")
    return f"sha256:{digest.hexdigest()}"


def read_regular(path: Path, *, max_bytes: int, expected_mode: int | None = None) -> bytes:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise TransportError("regular_file_unsafe")
        if expected_mode is not None and stat.S_IMODE(before.st_mode) != expected_mode:
            raise TransportError("regular_file_mode_invalid")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
        pathname = os.lstat(path)
    except TransportError:
        raise
    except OSError as exc:
        raise TransportError("regular_file_unavailable") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if (
        len(payload) > max_bytes
        or after.st_size != len(payload)
        or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
        or (after.st_dev, after.st_ino) != (pathname.st_dev, pathname.st_ino)
        or pathname.st_nlink != 1
    ):
        raise TransportError("regular_file_changed")
    return payload


def run_process(plan: ProcessPlan, *, stdin: bytes | None = None) -> ProcessResult:
    _checked_program(plan.argv)
    if (
        plan.timeout_seconds <= 0
        or plan.max_output_bytes <= 0
        or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in plan.env.items()
        )
    ):
        raise TransportError("process_plan_invalid")
    try:
        completed = subprocess.run(  # nosec B603: argv is absolute and validated by _checked_program (remove-by: 2026-10-31, ref: PR-2347)
            list(plan.argv),
            cwd=plan.cwd,
            env=dict(plan.env),
            input=stdin,
            capture_output=True,
            check=False,
            timeout=plan.timeout_seconds,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TransportError("process_execution_failed") from exc
    if (
        len(completed.stdout) > plan.max_output_bytes
        or len(completed.stderr) > plan.max_output_bytes
    ):
        raise TransportError("process_output_too_large")
    return ProcessResult(completed.returncode, completed.stdout, completed.stderr)


def observe_programs(
    commands: Mapping[str, tuple[str, ...]],
    cwd: Path,
    env: Mapping[str, str],
    *,
    timeout_seconds: int,
    max_output_bytes: int,
    max_program_bytes: int,
) -> Mapping[str, ProgramObservation]:
    programs: dict[str, tuple[Path, str]] = {}
    observed: dict[str, ProgramObservation] = {}
    for label, command in commands.items():
        if not command:
            raise TransportError("program_observation_invalid")
        name = command[0]
        if name not in programs:
            path = resolve_program(name)
            programs[name] = (
                path,
                hash_regular(path, max_bytes=max_program_bytes, executable=True),
            )
        path, digest = programs[name]
        result = run_process(
            ProcessPlan(
                (str(path), *command[1:]),
                cwd,
                env,
                timeout_seconds,
                max_output_bytes,
            )
        )
        try:
            stdout = result.stdout.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise TransportError("program_observation_invalid") from exc
        observed[label] = ProgramObservation(path, digest, result.returncode, stdout)
    return observed


def write_private_file(path: Path, payload: bytes) -> None:
    descriptor = -1
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
        )
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise TransportError("private_file_write_failed")
            remaining = remaining[written:]
        os.fsync(descriptor)
    except TransportError:
        raise
    except OSError as exc:
        raise TransportError("private_file_write_failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def atomic_rename_noreplace(source: Path, destination: Path) -> None:
    """Atomically move one prepared file without replacing a winner."""

    if sys.platform == "darwin":
        symbol, flag = "renameatx_np", 0x00000004
    elif sys.platform.startswith("linux"):
        symbol, flag = "renameat2", 1
    else:
        raise TransportError("atomic_noreplace_unsupported")
    source_fd = destination_fd = -1
    try:
        source_fd = os.open(
            source.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        destination_fd = os.open(
            destination.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        libc = ctypes.CDLL(None, use_errno=True)
        rename_noreplace = getattr(libc, symbol)
        rename_noreplace.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename_noreplace.restype = ctypes.c_int
        ctypes.set_errno(0)
        result = rename_noreplace(
            source_fd,
            os.fsencode(source.name),
            destination_fd,
            os.fsencode(destination.name),
            flag,
        )
        if result != 0:
            error_number = ctypes.get_errno()
            if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
                raise FileExistsError(error_number, "no-replace destination exists")
            raise TransportError("atomic_noreplace_failed")
        os.fsync(destination_fd)
    except (AttributeError, OSError) as exc:
        if isinstance(exc, FileExistsError):
            raise
        raise TransportError("atomic_noreplace_failed") from exc
    finally:
        if source_fd >= 0:
            os.close(source_fd)
        if destination_fd >= 0:
            os.close(destination_fd)


def login_push_logout(
    login: ProcessPlan,
    push: ProcessPlan,
    logout: ProcessPlan,
    credential: bytes,
) -> ProcessResult:
    if not credential or b"\x00" in credential or b"\r" in credential or b"\n" in credential:
        raise TransportError("credential_input_invalid")
    if any(credential in item.encode() for plan in (login, push, logout) for item in plan.argv):
        raise TransportError("credential_in_argv")
    logged_in = False
    primary_error: BaseException | None = None
    push_result: ProcessResult | None = None
    try:
        login_result = run_process(login, stdin=credential)
        if login_result.returncode != 0:
            raise TransportError("login_failed")
        logged_in = True
        push_result = run_process(push)
        if push_result.returncode != 0:
            raise TransportError("push_failed")
    except BaseException as exc:
        primary_error = exc
    finally:
        if logged_in:
            try:
                logout_result = run_process(logout)
                if logout_result.returncode != 0:
                    raise TransportError("logout_failed")
            except BaseException as exc:
                if primary_error is None:
                    primary_error = exc
    if primary_error is not None:
        raise primary_error
    if push_result is None:
        raise TransportError("push_result_missing")
    redacted_stdout = push_result.stdout.replace(credential, b"[REDACTED]")
    redacted_stderr = push_result.stderr.replace(credential, b"[REDACTED]")
    return ProcessResult(push_result.returncode, redacted_stdout, redacted_stderr)


def _safe_member_name(raw: str) -> str:
    name = raw.rstrip("/")
    candidate = PurePosixPath(name)
    if (
        not name
        or raw.startswith("/")
        or "\\" in raw
        or candidate.is_absolute()
        or ".." in candidate.parts
        or str(candidate) != name
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in raw)
    ):
        raise TransportError("oci_member_unsafe")
    return name


def _json(raw: bytes) -> object:
    def reject(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise TransportError("json_duplicate_key")
            result[key] = value
        return result

    try:
        return json.loads(
            raw,
            object_pairs_hook=reject,
            parse_constant=lambda _value: (_ for _ in ()).throw(TransportError("json_invalid")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise TransportError("json_invalid") from exc


def parse_json_bytes(raw: bytes) -> object:
    return _json(raw)


def extract_assignments(
    raw: bytes, names: Sequence[str], *, reserved_prefix: str
) -> Mapping[str, str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TransportError("assignment_output_invalid") from exc
    expected = set(names)
    observed: dict[str, list[str]] = {name: [] for name in names}
    for match in re.finditer(r"\b([A-Z][A-Z0-9_]+)=([a-z0-9]+)\b", text):
        name = match.group(1)
        if name.startswith(reserved_prefix) and name not in expected:
            raise TransportError("assignment_output_invalid")
        if name in expected:
            observed[name].append(match.group(2))
    if any(len(values) != 1 for values in observed.values()):
        raise TransportError("assignment_output_invalid")
    return {name: values[0] for name, values in observed.items()}


def rename_assignments(
    observed: Mapping[str, str], names: Mapping[str, str], count_names: Sequence[str]
) -> Mapping[str, object]:
    counts = set(count_names)
    return {
        names[key]: int(value) if names[key] in counts else value for key, value in observed.items()
    }


def oci_mapping(observed: OCIResult) -> Mapping[str, object]:
    return {
        "platform": observed.platform,
        "manifest_digest": observed.manifest_digest,
        "config_digest": observed.config_digest,
        "layer_digests": list(observed.layer_digests),
    }


def merge_build_observation(
    observed: tuple[ProcessResult, Mapping[str, str], OCIResult],
    names: Mapping[str, str],
    count_names: Sequence[str],
) -> tuple[ProcessResult, Mapping[str, object]]:
    result, assignments, oci = observed
    evidence = dict(rename_assignments(assignments, names, count_names))
    evidence.update(oci_mapping(oci))
    return result, evidence


def execute_build_observation(
    plan: ProcessPlan,
    archive: Path,
    names: Sequence[str],
    *,
    reserved_prefix: str,
    max_archive_bytes: int,
    max_members: int,
    max_metadata_bytes: int,
) -> tuple[ProcessResult, Mapping[str, str], OCIResult]:
    result = run_process(plan)
    assignments = extract_assignments(
        result.stdout + result.stderr, names, reserved_prefix=reserved_prefix
    )
    oci = parse_oci_archive(
        archive,
        max_archive_bytes=max_archive_bytes,
        max_members=max_members,
        max_metadata_bytes=max_metadata_bytes,
    )
    return result, assignments, oci


def execute_json_observation(
    plan: ProcessPlan, output: Path, *, max_bytes: int
) -> tuple[ProcessResult, object]:
    result = run_process(plan)
    return result, parse_json_bytes(read_regular(output, max_bytes=max_bytes))


def execute_versioned_json_observation(
    version_plan: ProcessPlan,
    observation_plan: ProcessPlan,
    output: Path,
    *,
    max_bytes: int,
) -> tuple[ProcessResult, ProcessResult, object, object]:
    version = run_process(version_plan)
    observation, report = execute_json_observation(
        observation_plan,
        output,
        max_bytes=max_bytes,
    )
    return version, observation, parse_json_bytes(version.stdout), report


def _descriptor(value: object) -> tuple[str, int]:
    if not isinstance(value, dict):
        raise TransportError("oci_descriptor_invalid")
    digest = value.get("digest")
    size = value.get("size")
    if (
        not isinstance(digest, str)
        or _DIGEST_RE.fullmatch(digest) is None
        or not isinstance(size, int)
        or isinstance(size, bool)
        or size < 0
    ):
        raise TransportError("oci_descriptor_invalid")
    return digest, size


def parse_oci_archive(
    path: Path,
    *,
    max_archive_bytes: int,
    max_members: int,
    max_metadata_bytes: int,
) -> OCIResult:
    try:
        metadata = os.lstat(path)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size > max_archive_bytes
        ):
            raise TransportError("oci_archive_unsafe")
        with tarfile.open(path, mode="r:*") as archive:
            members = archive.getmembers()
            if not members or len(members) > max_members:
                raise TransportError("oci_archive_unsafe")
            by_name: dict[str, tarfile.TarInfo] = {}
            for member in members:
                name = _safe_member_name(member.name)
                if name in by_name or not (member.isdir() or member.isreg()):
                    raise TransportError("oci_archive_unsafe")
                by_name[name] = member

            def read_small(name: str) -> bytes:
                member = by_name.get(name)
                if member is None or not member.isreg() or member.size > max_metadata_bytes:
                    raise TransportError("oci_metadata_invalid")
                stream = archive.extractfile(member)
                if stream is None:
                    raise TransportError("oci_metadata_invalid")
                payload = stream.read(max_metadata_bytes + 1)
                if len(payload) != member.size:
                    raise TransportError("oci_metadata_invalid")
                return payload

            def verify_blob(name: str, size: int, digest: str) -> None:
                member = by_name.get(name)
                if member is None or not member.isreg() or member.size != size:
                    raise TransportError("oci_layers_invalid")
                stream = archive.extractfile(member)
                if stream is None:
                    raise TransportError("oci_layers_invalid")
                observed = hashlib.sha256()
                remaining = size
                while remaining:
                    chunk = stream.read(min(1_048_576, remaining))
                    if not chunk:
                        raise TransportError("oci_layers_invalid")
                    observed.update(chunk)
                    remaining -= len(chunk)
                if f"sha256:{observed.hexdigest()}" != digest:
                    raise TransportError("oci_layers_invalid")

            layout = _json(read_small("oci-layout"))
            if layout != {"imageLayoutVersion": "1.0.0"}:
                raise TransportError("oci_layout_invalid")
            index = _json(read_small("index.json"))
            if not isinstance(index, dict) or index.get("schemaVersion") != 2:
                raise TransportError("oci_index_invalid")
            descriptors = index.get("manifests")
            if not isinstance(descriptors, list) or len(descriptors) != 1:
                raise TransportError("oci_index_invalid")
            if (
                not isinstance(descriptors[0], dict)
                or descriptors[0].get("mediaType") != _OCI_MANIFEST
            ):
                raise TransportError("oci_index_invalid")
            manifest_digest, manifest_size = _descriptor(descriptors[0])
            manifest_raw = read_small(f"blobs/sha256/{manifest_digest[7:]}")
            if len(manifest_raw) != manifest_size or (
                f"sha256:{hashlib.sha256(manifest_raw).hexdigest()}" != manifest_digest
            ):
                raise TransportError("oci_manifest_invalid")
            manifest = _json(manifest_raw)
            if (
                not isinstance(manifest, dict)
                or manifest.get("schemaVersion") != 2
                or manifest.get("mediaType") != _OCI_MANIFEST
                or not isinstance(manifest.get("config"), dict)
                or manifest["config"].get("mediaType") != _OCI_CONFIG
            ):
                raise TransportError("oci_manifest_invalid")
            config_digest, config_size = _descriptor(manifest.get("config"))
            config_raw = read_small(f"blobs/sha256/{config_digest[7:]}")
            if len(config_raw) != config_size or (
                f"sha256:{hashlib.sha256(config_raw).hexdigest()}" != config_digest
            ):
                raise TransportError("oci_config_invalid")
            config = _json(config_raw)
            if not isinstance(config, dict):
                raise TransportError("oci_config_invalid")
            os_name = config.get("os")
            architecture = config.get("architecture")
            if not isinstance(os_name, str) or not isinstance(architecture, str):
                raise TransportError("oci_config_invalid")
            raw_layers = manifest.get("layers")
            if not isinstance(raw_layers, list) or not raw_layers:
                raise TransportError("oci_layers_invalid")
            layers: list[str] = []
            expected_files = {
                "oci-layout",
                "index.json",
                f"blobs/sha256/{manifest_digest[7:]}",
                f"blobs/sha256/{config_digest[7:]}",
            }
            for raw_layer in raw_layers:
                if not isinstance(raw_layer, dict) or raw_layer.get("mediaType") not in _OCI_LAYERS:
                    raise TransportError("oci_layers_invalid")
                layer_digest, layer_size = _descriptor(raw_layer)
                layer_name = f"blobs/sha256/{layer_digest[7:]}"
                verify_blob(layer_name, layer_size, layer_digest)
                expected_files.add(layer_name)
                layers.append(layer_digest)
            regular_names = {name for name, member in by_name.items() if member.isreg()}
            directory_names = {name for name, member in by_name.items() if member.isdir()}
            if regular_names != expected_files or not directory_names.issubset(
                {"blobs", "blobs/sha256"}
            ):
                raise TransportError("oci_inventory_invalid")
            return OCIResult(
                manifest_digest,
                config_digest,
                f"{os_name}/{architecture}",
                tuple(layers),
            )
    except TransportError:
        raise
    except (OSError, tarfile.TarError) as exc:
        raise TransportError("oci_archive_invalid") from exc


def extract_oci_layout(
    archive_path: Path,
    destination: Path,
    *,
    max_archive_bytes: int,
    max_members: int,
    max_metadata_bytes: int,
) -> OCIResult:
    """Validate and privately extract one closed OCI layout."""

    observed = parse_oci_archive(
        archive_path,
        max_archive_bytes=max_archive_bytes,
        max_members=max_members,
        max_metadata_bytes=max_metadata_bytes,
    )
    try:
        destination.mkdir(mode=0o700)
        if any(destination.iterdir()):
            raise TransportError("oci_destination_not_empty")
        with tarfile.open(archive_path, mode="r:*") as archive:
            for member in archive.getmembers():
                relative = _safe_member_name(member.name)
                target = destination.joinpath(*PurePosixPath(relative).parts)
                if member.isdir():
                    target.mkdir(mode=0o700, parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                stream = archive.extractfile(member)
                if stream is None:
                    raise TransportError("oci_extract_invalid")
                descriptor = os.open(
                    target,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                )
                try:
                    remaining = member.size
                    while remaining:
                        chunk = stream.read(min(1_048_576, remaining))
                        if not chunk:
                            raise TransportError("oci_extract_invalid")
                        view = memoryview(chunk)
                        while view:
                            written = os.write(descriptor, view)
                            if written <= 0:
                                raise TransportError("oci_extract_invalid")
                            view = view[written:]
                        remaining -= len(chunk)
                    if stream.read(1):
                        raise TransportError("oci_extract_invalid")
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        return observed
    except TransportError:
        raise
    except (OSError, tarfile.TarError) as exc:
        raise TransportError("oci_extract_invalid") from exc


class _HTTPS:
    def __init__(self, plan: RegistryPlan) -> None:
        self.plan = plan

    def get(
        self,
        host: str,
        target: str,
        headers: Mapping[str, str],
        *,
        redirects: int = 2,
    ) -> tuple[int, Mapping[str, str], bytes]:
        if host not in self.plan.allowed_redirect_hosts or not target.startswith("/"):
            raise TransportError("http_target_invalid")
        connection = http.client.HTTPSConnection(host, timeout=self.plan.timeout_seconds)
        try:
            connection.request("GET", target, headers=dict(headers))
            response = connection.getresponse()
            response_headers = {key.lower(): value for key, value in response.getheaders()}
            if response.status in {301, 302, 307, 308}:
                location = response_headers.get("location")
                response.read()
                parsed = urlsplit(location or "")
                if (
                    redirects <= 0
                    or parsed.scheme != "https"
                    or parsed.hostname not in self.plan.allowed_redirect_hosts
                    or parsed.username is not None
                    or parsed.password is not None
                    or parsed.port not in {None, 443}
                ):
                    raise TransportError("http_redirect_invalid")
                redirected = parsed.path or "/"
                if parsed.query:
                    redirected += f"?{parsed.query}"
                return self.get(parsed.hostname, redirected, headers, redirects=redirects - 1)
            payload = response.read(self.plan.max_response_bytes + 1)
            if len(payload) > self.plan.max_response_bytes:
                raise TransportError("http_response_too_large")
            return response.status, response_headers, payload
        except TransportError:
            raise
        except (OSError, http.client.HTTPException) as exc:
            raise TransportError("http_unavailable") from exc
        finally:
            connection.close()


def observe_registry(plan: RegistryPlan) -> OCIResult | None:
    client = _HTTPS(plan)
    manifest_path = f"/v2/{plan.repository}/manifests/{plan.locator}"
    status, headers, _payload = client.get(plan.host, manifest_path, {"Accept": plan.accept})
    if status != 401:
        raise TransportError("bearer_challenge_invalid")
    challenge = headers.get("www-authenticate", "")
    match = re.fullmatch(r'Bearer realm="([^"]+)",service="([^"]+)",scope="([^"]+)"', challenge)
    if match is None:
        raise TransportError("bearer_challenge_invalid")
    realm = urlsplit(match.group(1))
    if (
        realm.scheme != "https"
        or realm.hostname != plan.host
        or match.group(2) != plan.host
        or match.group(3) != plan.scope
    ):
        raise TransportError("bearer_challenge_invalid")
    query = urlencode({"service": plan.host, "scope": plan.scope})
    token_path = realm.path or "/"
    token_status, _headers, token_raw = client.get(
        plan.host, f"{token_path}?{query}", {"Accept": "application/json"}
    )
    token_value = _json(token_raw)
    if token_status != 200 or not isinstance(token_value, dict):
        raise TransportError("bearer_token_invalid")
    token_fields = [field for field in ("token", "access_token") if field in token_value]
    if len(token_fields) != 1:
        raise TransportError("bearer_token_invalid")
    token = token_value[token_fields[0]]
    if not isinstance(token, str) or not token or len(token) > 16_384:
        raise TransportError("bearer_token_invalid")
    authorization = {"Accept": plan.accept, "Authorization": f"Bearer {token}"}
    status, headers, manifest_raw = client.get(plan.host, manifest_path, authorization)
    if status == 404:
        return None
    if status != 200:
        raise TransportError("manifest_response_invalid")
    content_type = headers.get("content-type", "").split(";", 1)[0].strip()
    if content_type != plan.accept:
        raise TransportError("manifest_media_type_invalid")
    manifest_digest = f"sha256:{hashlib.sha256(manifest_raw).hexdigest()}"
    declared = headers.get("docker-content-digest")
    if declared is not None and declared != manifest_digest:
        raise TransportError("manifest_digest_invalid")
    manifest = _json(manifest_raw)
    if (
        not isinstance(manifest, dict)
        or manifest.get("schemaVersion") != 2
        or manifest.get("mediaType") != plan.accept
        or not isinstance(manifest.get("config"), dict)
        or manifest["config"].get("mediaType") != _OCI_CONFIG
    ):
        raise TransportError("manifest_response_invalid")
    config_digest, config_size = _descriptor(manifest.get("config"))
    config_status, config_headers, config_raw = client.get(
        plan.host,
        f"/v2/{plan.repository}/blobs/{config_digest}",
        {"Authorization": f"Bearer {token}"},
    )
    if (
        config_status != 200
        or config_headers.get("content-type", "").split(";", 1)[0].strip() != _OCI_CONFIG
        or len(config_raw) != config_size
        or (f"sha256:{hashlib.sha256(config_raw).hexdigest()}" != config_digest)
    ):
        raise TransportError("config_response_invalid")
    config = _json(config_raw)
    if not isinstance(config, dict):
        raise TransportError("config_response_invalid")
    os_name = config.get("os")
    architecture = config.get("architecture")
    if not isinstance(os_name, str) or not isinstance(architecture, str):
        raise TransportError("config_response_invalid")
    raw_layers = manifest.get("layers")
    if not isinstance(raw_layers, list) or not raw_layers:
        raise TransportError("layers_response_invalid")
    if any(
        not isinstance(layer, dict) or layer.get("mediaType") not in _OCI_LAYERS
        for layer in raw_layers
    ):
        raise TransportError("layers_response_invalid")
    layers = tuple(_descriptor(layer)[0] for layer in raw_layers)
    return OCIResult(manifest_digest, config_digest, f"{os_name}/{architecture}", layers)
