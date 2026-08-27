#!/usr/bin/env python3
"""Immutable, local-only PR evidence sidecar receipts and aggregate reporting."""

from __future__ import annotations

import argparse
import ctypes
import errno
import fcntl
import hashlib
import json
import os
import stat
import sys
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NoReturn, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
STORE_ROOT = REPO_ROOT / "artifacts/orchestration/pr_evidence_sidecars"
RAILS = ("teleology", "euler", "experiment_runner")
START_SCHEMA = "pr_evidence_sidecar.start.v1"
TERMINAL_INPUT_SCHEMA = "pr_evidence_sidecar.terminal_input.v1"
TERMINAL_SCHEMA = "pr_evidence_sidecar.terminal.v1"
REPORT_SCHEMA = "pr_evidence_sidecar.report.v1"
POLICY_VERSION = "pr_evidence_sidecar.policy.v1"
REPOSITORY = "Katsiarynakavaleuskaya/PulsePlate"
DISCLAIMER = (
    "Structural local receipt only; no review, CI, merge, release, enrollment, "
    "causality, outcome, or other authority is granted."
)
AUTHORITY = {
    "approval_authority": False,
    "causality_authority": False,
    "ci_authority": False,
    "enrollment_authority": False,
    "implementation_authority": False,
    "merge_authority": False,
    "outcome_authority": False,
    "promotion_authority": False,
    "release_authority": False,
    "review_authority": False,
    "routing_authority": False,
}
MAX_PACKET_BYTES = 2_000_000
MAX_TERMINAL_INPUT_BYTES = 64_000
MAX_RECEIPT_BYTES = 128_000
MAX_SIDECARS = 128
_THREAD_STORE_LOCK = threading.RLock()


class SidecarError(ValueError):
    """Fail-closed error with a stable stderr category."""

    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


class StrictParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SidecarError("INVALID_INPUT")


def _reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SidecarError("INVALID_INPUT")
        result[key] = value
    return result


def _strict_json_bytes(raw: bytes, *, limit: int) -> Any:
    if not raw or len(raw) > limit or raw.startswith(b"\xef\xbb\xbf"):
        raise SidecarError("INVALID_INPUT")
    try:
        text = raw.decode("utf-8")
        decoder = json.JSONDecoder(
            object_pairs_hook=_reject_duplicate,
            parse_constant=lambda _value: (_ for _ in ()).throw(SidecarError("INVALID_INPUT")),
        )
        value, end = decoder.raw_decode(text)
    except (UnicodeDecodeError, json.JSONDecodeError, SidecarError) as exc:
        raise SidecarError("INVALID_INPUT") from exc
    if text[end:].strip():
        raise SidecarError("INVALID_INPUT")
    return value


def _read_regular(
    path: Path,
    *,
    limit: int,
) -> bytes:
    required_flags = ("O_NOFOLLOW", "O_CLOEXEC")
    if any(not hasattr(os, name) for name in required_flags):
        raise SidecarError("STORAGE_UNAVAILABLE")
    descriptor = -1
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        initial = os.fstat(descriptor)
        if not stat.S_ISREG(initial.st_mode):
            raise SidecarError("INVALID_INPUT")
        if initial.st_nlink != 1:
            raise SidecarError("INVALID_INPUT")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        final = os.fstat(descriptor)
        path_metadata = os.lstat(path)
    except SidecarError:
        raise
    except OSError as exc:
        raise SidecarError("INVALID_INPUT") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if (
        len(raw) > limit
        or final.st_size != len(raw)
        or (initial.st_dev, initial.st_ino) != (final.st_dev, final.st_ino)
        or (final.st_dev, final.st_ino) != (path_metadata.st_dev, path_metadata.st_ino)
        or not stat.S_ISREG(path_metadata.st_mode)
        or final.st_nlink != 1
    ):
        raise SidecarError("INVALID_INPUT")
    return raw


def _require_mode(path: Path, expected: int) -> None:
    try:
        if stat.S_IMODE(path.lstat().st_mode) != expected:
            raise SidecarError("INVALID_INPUT")
    except SidecarError:
        raise
    except OSError as exc:
        raise SidecarError("STORAGE_UNAVAILABLE") from exc


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode()


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _receipt(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result["receipt_fingerprint"] = _fingerprint(result)
    return result


def _start_identity(
    *,
    repository: str,
    task_packet_id: str,
    task_packet_fingerprint: str,
    base_sha: str,
    applicable_rails: list[str],
) -> dict[str, Any]:
    """Project exactly the fields that define one start receipt identity."""

    return {
        "schema_version": START_SCHEMA,
        "policy_version": POLICY_VERSION,
        "repository": repository,
        "task_packet_id": task_packet_id,
        "task_packet_fingerprint": task_packet_fingerprint,
        "base_sha": base_sha,
        "applicable_rails": applicable_rails,
    }


def _exact_object(value: Any, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise SidecarError("INVALID_INPUT")
    return cast(dict[str, Any], value)


def _lower_sha(value: Any) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or value != value.lower()
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise SidecarError("INVALID_INPUT")
    return value


def _sha256_id(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise SidecarError("INVALID_INPUT")
    return value


def _sidecar_dir(sidecar_id: str) -> Path:
    return STORE_ROOT / _sha256_id(sidecar_id).removeprefix("sha256:")


def _walk_repo_components(path: Path, *, create_missing: bool) -> None:
    try:
        relative = path.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise SidecarError("INVALID_INPUT") from exc
    current = REPO_ROOT
    for part in relative.parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            if not create_missing:
                raise SidecarError("INVALID_INPUT")
            try:
                current.mkdir(mode=0o700)
                metadata = current.lstat()
            except FileExistsError:
                metadata = current.lstat()
            except OSError as exc:
                raise SidecarError("STORAGE_UNAVAILABLE") from exc
        except OSError as exc:
            raise SidecarError("STORAGE_UNAVAILABLE") from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise SidecarError("INVALID_INPUT")


def _ensure_private_dir(path: Path) -> None:
    _walk_repo_components(path, create_missing=True)
    try:
        metadata = path.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise SidecarError("STORAGE_UNAVAILABLE")
        os.chmod(path, 0o700)
    except SidecarError:
        raise
    except OSError as exc:
        raise SidecarError("STORAGE_UNAVAILABLE") from exc


def _store_root_exists_without_alias() -> bool:
    """Return whether the fixed root exists, rejecting unsafe existing components."""

    try:
        relative = STORE_ROOT.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise SidecarError("INVALID_INPUT") from exc
    current = REPO_ROOT
    for part in relative.parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise SidecarError("STORAGE_UNAVAILABLE") from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise SidecarError("INVALID_INPUT")
    return True


@contextmanager
def _store_lock(*, exclusive: bool, create_store: bool) -> Iterator[bool]:
    """Serialize cooperative access across threads and local processes."""

    required_flags = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC")
    if any(not hasattr(os, name) for name in required_flags):
        raise SidecarError("STORAGE_UNAVAILABLE")
    with _THREAD_STORE_LOCK:
        if create_store:
            _ensure_private_dir(STORE_ROOT)
        elif not _store_root_exists_without_alias():
            yield False
            return
        descriptor = -1
        try:
            descriptor = os.open(
                STORE_ROOT,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            metadata = os.fstat(descriptor)
            if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o700:
                raise SidecarError("INVALID_INPUT")
            fcntl.flock(descriptor, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            yield True
        except SidecarError:
            raise
        except OSError as exc:
            raise SidecarError("STORAGE_UNAVAILABLE") from exc
        finally:
            if descriptor >= 0:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)


def _kernel_rename_noreplace(
    source_fd: int,
    source_name: str,
    destination_fd: int,
    destination_name: str,
) -> None:
    if sys.platform == "darwin":
        symbol = "renameatx_np"
        flag = 0x00000004
    elif sys.platform.startswith("linux"):
        symbol = "renameat2"
        flag = 1
    else:
        raise SidecarError("STORAGE_UNAVAILABLE")
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        rename_noreplace = getattr(libc, symbol)
    except (AttributeError, OSError) as exc:
        raise SidecarError("STORAGE_UNAVAILABLE") from exc
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
        os.fsencode(source_name),
        destination_fd,
        os.fsencode(destination_name),
        flag,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FileExistsError(error_number, "no-replace destination exists")
    raise SidecarError("STORAGE_UNAVAILABLE")


def _open_directory_fd(path: Path) -> int:
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        metadata = os.fstat(descriptor)
    except OSError as exc:
        raise SidecarError("STORAGE_UNAVAILABLE") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        raise SidecarError("INVALID_INPUT")
    return descriptor


def _remove_owned_stage(path: Path, identity: tuple[int, int]) -> None:
    try:
        metadata = path.lstat()
        if (
            stat.S_ISREG(metadata.st_mode)
            and metadata.st_nlink == 1
            and (metadata.st_dev, metadata.st_ino) == identity
        ):
            path.unlink()
    except (FileNotFoundError, OSError):
        return


def _atomic_immutable_write(path: Path, payload: bytes) -> bool:
    if len(payload) > MAX_RECEIPT_BYTES:
        raise SidecarError("INVALID_INPUT")
    _ensure_private_dir(STORE_ROOT)
    _ensure_private_dir(path.parent)
    if path.exists() or path.is_symlink():
        existing = _read_regular(path, limit=MAX_RECEIPT_BYTES)
        if existing == payload:
            return False
        raise SidecarError("CONFLICT")
    stage_path: Path | None = None
    stage_identity: tuple[int, int] | None = None
    source_fd = -1
    destination_fd = -1
    try:
        stage_parent = STORE_ROOT.parent
        _walk_repo_components(stage_parent, create_missing=False)
        descriptor, name = tempfile.mkstemp(prefix=".pr-evidence-receipt-", dir=stage_parent)
        stage_path = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(stage_path, 0o600)
        stage_metadata = stage_path.lstat()
        stage_identity = (stage_metadata.st_dev, stage_metadata.st_ino)
        source_fd = _open_directory_fd(stage_parent)
        destination_fd = _open_directory_fd(path.parent)
        try:
            _kernel_rename_noreplace(
                source_fd,
                stage_path.name,
                destination_fd,
                path.name,
            )
        except FileExistsError:
            existing = _read_regular(path, limit=MAX_RECEIPT_BYTES)
            if existing == payload:
                return False
            raise SidecarError("CONFLICT")
        os.chmod(path, 0o600)
        os.fsync(destination_fd)
        return True
    except SidecarError:
        raise
    except OSError as exc:
        raise SidecarError("STORAGE_UNAVAILABLE") from exc
    finally:
        if source_fd >= 0:
            os.close(source_fd)
        if destination_fd >= 0:
            os.close(destination_fd)
        if stage_path is not None and stage_identity is not None:
            _remove_owned_stage(stage_path, stage_identity)


def _validate_receipt_fingerprint(value: dict[str, Any]) -> None:
    actual = value.get("receipt_fingerprint")
    unsigned = dict(value)
    unsigned.pop("receipt_fingerprint", None)
    if actual != _fingerprint(unsigned):
        raise SidecarError("INVALID_INPUT")


def _load_start(sidecar_id: str) -> dict[str, Any]:
    path = _sidecar_dir(sidecar_id) / "start.json"
    parsed = _strict_json_bytes(
        _read_regular(path, limit=MAX_RECEIPT_BYTES),
        limit=MAX_RECEIPT_BYTES,
    )
    _require_mode(path, 0o600)
    value = _exact_object(
        parsed,
        {
            "schema_version",
            "policy_version",
            "repository",
            "sidecar_id",
            "task_packet_id",
            "task_packet_fingerprint",
            "base_sha",
            "applicable_rails",
            "authority",
            "disclaimer",
            "receipt_fingerprint",
        },
    )
    if value["schema_version"] != START_SCHEMA or value["policy_version"] != POLICY_VERSION:
        raise SidecarError("INVALID_INPUT")
    if value["repository"] != REPOSITORY:
        raise SidecarError("INVALID_INPUT")
    if (
        value["sidecar_id"] != sidecar_id
        or path.parent.name != sidecar_id.removeprefix("sha256:")
        or value["authority"] != AUTHORITY
        or value["disclaimer"] != DISCLAIMER
    ):
        raise SidecarError("INVALID_INPUT")
    _lower_sha(value["base_sha"])
    _sha256_id(value["task_packet_fingerprint"])
    if (
        not isinstance(value["task_packet_id"], str)
        or len(value["task_packet_id"]) != 12
        or any(char not in "0123456789abcdef" for char in value["task_packet_id"])
    ):
        raise SidecarError("INVALID_INPUT")
    rails = value["applicable_rails"]
    if (
        not isinstance(rails, list)
        or not rails
        or rails != sorted(set(rails))
        or any(item not in RAILS for item in rails)
    ):
        raise SidecarError("INVALID_INPUT")
    expected_sidecar_id = _fingerprint(
        _start_identity(
            repository=value["repository"],
            task_packet_id=value["task_packet_id"],
            task_packet_fingerprint=value["task_packet_fingerprint"],
            base_sha=value["base_sha"],
            applicable_rails=rails,
        )
    )
    if expected_sidecar_id != sidecar_id:
        raise SidecarError("INVALID_INPUT")
    _validate_receipt_fingerprint(value)
    return value


def _canonical_packet_path(packet_path: Path) -> Path:
    path = packet_path if packet_path.is_absolute() else REPO_ROOT / packet_path
    packet_root = REPO_ROOT / "artifacts/orchestration/task_packets"
    try:
        path.relative_to(packet_root)
    except ValueError as exc:
        raise SidecarError("INVALID_INPUT") from exc
    if path.parent != packet_root or path.suffix != ".json":
        raise SidecarError("INVALID_INPUT")
    _walk_repo_components(path.parent, create_missing=False)
    return path


def _validate_root_index() -> list[Path]:
    """Validate and bound the complete canonical sidecar directory index."""

    _walk_repo_components(STORE_ROOT, create_missing=False)
    _require_mode(STORE_ROOT, 0o700)
    try:
        entries = sorted(STORE_ROOT.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise SidecarError("INVALID_INPUT") from exc
    if len(entries) > MAX_SIDECARS:
        raise SidecarError("INVALID_INPUT")
    for entry in entries:
        try:
            metadata = entry.lstat()
        except OSError as exc:
            raise SidecarError("INVALID_INPUT") from exc
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or len(entry.name) != 64
            or any(char not in "0123456789abcdef" for char in entry.name)
        ):
            raise SidecarError("INVALID_INPUT")
    return entries


def _prepare_unlocked(
    packet_path: Path,
    base_sha: str,
    applicable_rails: list[str],
) -> dict[str, Any]:
    base_sha = _lower_sha(base_sha)
    rails = sorted(set(applicable_rails))
    if not rails or len(rails) != len(applicable_rails) or any(rail not in RAILS for rail in rails):
        raise SidecarError("INVALID_INPUT")
    canonical_packet_path = _canonical_packet_path(packet_path)
    raw = _read_regular(canonical_packet_path, limit=MAX_PACKET_BYTES)
    packet = _strict_json_bytes(raw, limit=MAX_PACKET_BYTES)
    if not isinstance(packet, dict) or packet.get("schema_version") != "3.1":
        raise SidecarError("INVALID_INPUT")
    task_packet_id = packet.get("task_packet_id")
    if (
        not isinstance(task_packet_id, str)
        or len(task_packet_id) != 12
        or any(char not in "0123456789abcdef" for char in task_packet_id)
    ):
        raise SidecarError("INVALID_INPUT")
    if canonical_packet_path.name != f"{task_packet_id}.json":
        raise SidecarError("INVALID_INPUT")
    packet_fingerprint = "sha256:" + hashlib.sha256(raw).hexdigest()
    identity = _start_identity(
        repository=REPOSITORY,
        task_packet_id=task_packet_id,
        task_packet_fingerprint=packet_fingerprint,
        base_sha=base_sha,
        applicable_rails=rails,
    )
    sidecar_id = _fingerprint(identity)
    existing_entries = _validate_root_index()
    candidate_name = sidecar_id.removeprefix("sha256:")
    if (
        all(entry.name != candidate_name for entry in existing_entries)
        and len(existing_entries) >= MAX_SIDECARS
    ):
        raise SidecarError("INVALID_INPUT")
    receipt = _receipt(
        {
            "schema_version": START_SCHEMA,
            "policy_version": POLICY_VERSION,
            "repository": REPOSITORY,
            "sidecar_id": sidecar_id,
            "task_packet_id": task_packet_id,
            "task_packet_fingerprint": packet_fingerprint,
            "base_sha": base_sha,
            "applicable_rails": rails,
            "authority": AUTHORITY,
            "disclaimer": DISCLAIMER,
        }
    )
    path = _sidecar_dir(sidecar_id) / "start.json"
    created = _atomic_immutable_write(path, _canonical(receipt))
    _validate_sidecar_container(sidecar_id)
    return {
        "schema_version": START_SCHEMA,
        "command": "prepare",
        "sidecar_id": sidecar_id,
        "sidecar_path": path.relative_to(REPO_ROOT).as_posix(),
        "created": created,
    }


def prepare(packet_path: Path, base_sha: str, applicable_rails: list[str]) -> dict[str, Any]:
    with _store_lock(exclusive=True, create_store=True):
        return _prepare_unlocked(packet_path, base_sha, applicable_rails)


def _repo_input_path(raw_path: str) -> Path:
    if not raw_path or "\\" in raw_path:
        raise SidecarError("INVALID_INPUT")
    candidate = Path(raw_path)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise SidecarError("INVALID_INPUT")
    path = REPO_ROOT / candidate
    _walk_repo_components(path.parent, create_missing=False)
    return path


def _validate_terminal_input(value: Any, start: dict[str, Any]) -> dict[str, Any]:
    document = _exact_object(
        value,
        {
            "schema_version",
            "pr_number",
            "observed_pr_terminal_state",
            "material_head_sha",
            "merge_commit_sha",
            "rails",
            "operator_observations",
        },
    )
    if document["schema_version"] != TERMINAL_INPUT_SCHEMA:
        raise SidecarError("INVALID_INPUT")
    if (
        isinstance(document["pr_number"], bool)
        or not isinstance(document["pr_number"], int)
        or document["pr_number"] <= 0
    ):
        raise SidecarError("INVALID_INPUT")
    if document["observed_pr_terminal_state"] not in {"merged", "closed_unmerged"}:
        raise SidecarError("INVALID_INPUT")
    _lower_sha(document["material_head_sha"])
    merge_sha = document["merge_commit_sha"]
    if document["observed_pr_terminal_state"] == "merged":
        _lower_sha(merge_sha)
    elif merge_sha is not None:
        raise SidecarError("INVALID_INPUT")
    rails = _exact_object(document["rails"], set(RAILS))
    applicable = set(start["applicable_rails"])
    for rail in RAILS:
        record = _exact_object(rails[rail], {"applicable", "status", "reference_fingerprint"})
        if record["applicable"] is not (rail in applicable):
            raise SidecarError("INVALID_INPUT")
        allowed = (
            (False, "not_applicable", None),
            (True, "referenced", record["reference_fingerprint"]),
            (True, "unknown", None),
        )
        triple = (record["applicable"], record["status"], record["reference_fingerprint"])
        if triple not in allowed:
            raise SidecarError("INVALID_INPUT")
        if record["status"] == "referenced":
            _sha256_id(record["reference_fingerprint"])
    operator_observations = _exact_object(
        document["operator_observations"],
        {
            "operator_minutes",
            "review_cycles",
            "repair_cycles",
        },
    )
    operator_minutes = operator_observations["operator_minutes"]
    if operator_minutes != "unknown" and (
        isinstance(operator_minutes, bool)
        or not isinstance(operator_minutes, int)
        or operator_minutes < 0
    ):
        raise SidecarError("INVALID_INPUT")
    for key in ("review_cycles", "repair_cycles"):
        observation = operator_observations[key]
        if isinstance(observation, bool) or not isinstance(observation, int) or observation < 0:
            raise SidecarError("INVALID_INPUT")
    return document


def _finalize_unlocked(sidecar_id: str, terminal_input_path: str) -> dict[str, Any]:
    start, _existing_terminal = _validate_sidecar_container(sidecar_id)
    input_path = _repo_input_path(terminal_input_path)
    value = _strict_json_bytes(
        _read_regular(input_path, limit=MAX_TERMINAL_INPUT_BYTES), limit=MAX_TERMINAL_INPUT_BYTES
    )
    terminal_input = _validate_terminal_input(value, start)
    terminal = _receipt(
        {
            "schema_version": TERMINAL_SCHEMA,
            "policy_version": POLICY_VERSION,
            "sidecar_id": sidecar_id,
            "start_receipt_fingerprint": start["receipt_fingerprint"],
            **{
                key: terminal_input[key]
                for key in (
                    "pr_number",
                    "observed_pr_terminal_state",
                    "material_head_sha",
                    "merge_commit_sha",
                    "rails",
                    "operator_observations",
                )
            },
            "causal_status": "not_assessed",
            "authority": AUTHORITY,
            "disclaimer": DISCLAIMER,
        }
    )
    path = _sidecar_dir(sidecar_id) / "terminal.json"
    created = _atomic_immutable_write(path, _canonical(terminal))
    _validate_sidecar_container(sidecar_id)
    return {
        "schema_version": TERMINAL_SCHEMA,
        "command": "finalize",
        "sidecar_id": sidecar_id,
        "sidecar_path": path.relative_to(REPO_ROOT).as_posix(),
        "created": created,
        "disclaimer": DISCLAIMER,
    }


def finalize(sidecar_id: str, terminal_input_path: str) -> dict[str, Any]:
    with _store_lock(exclusive=True, create_store=False) as store_exists:
        if not store_exists:
            raise SidecarError("INVALID_INPUT")
        return _finalize_unlocked(sidecar_id, terminal_input_path)


def _load_terminal(sidecar_id: str, start: dict[str, Any]) -> dict[str, Any] | None:
    path = _sidecar_dir(sidecar_id) / "terminal.json"
    if not path.exists() and not path.is_symlink():
        return None
    parsed = _strict_json_bytes(
        _read_regular(path, limit=MAX_RECEIPT_BYTES),
        limit=MAX_RECEIPT_BYTES,
    )
    _require_mode(path, 0o600)
    keys = {
        "schema_version",
        "policy_version",
        "sidecar_id",
        "start_receipt_fingerprint",
        "pr_number",
        "observed_pr_terminal_state",
        "material_head_sha",
        "merge_commit_sha",
        "rails",
        "operator_observations",
        "causal_status",
        "authority",
        "disclaimer",
        "receipt_fingerprint",
    }
    value = _exact_object(parsed, keys)
    if value["schema_version"] != TERMINAL_SCHEMA or value["policy_version"] != POLICY_VERSION:
        raise SidecarError("INVALID_INPUT")
    if (
        value["sidecar_id"] != sidecar_id
        or value["start_receipt_fingerprint"] != start["receipt_fingerprint"]
    ):
        raise SidecarError("INVALID_INPUT")
    if (
        value["causal_status"] != "not_assessed"
        or value["authority"] != AUTHORITY
        or value["disclaimer"] != DISCLAIMER
    ):
        raise SidecarError("INVALID_INPUT")
    _validate_terminal_input(
        {
            "schema_version": TERMINAL_INPUT_SCHEMA,
            **{
                key: value[key]
                for key in (
                    "pr_number",
                    "observed_pr_terminal_state",
                    "material_head_sha",
                    "merge_commit_sha",
                    "rails",
                    "operator_observations",
                )
            },
        },
        start,
    )
    _validate_receipt_fingerprint(value)
    return value


def _validate_sidecar_container(
    sidecar_id: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    _walk_repo_components(STORE_ROOT, create_missing=False)
    _require_mode(STORE_ROOT, 0o700)
    directory = _sidecar_dir(sidecar_id)
    try:
        metadata = directory.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise SidecarError("INVALID_INPUT")
        _require_mode(directory, 0o700)
        names = {item.name for item in directory.iterdir()}
    except SidecarError:
        raise
    except OSError as exc:
        raise SidecarError("INVALID_INPUT") from exc
    if "start.json" not in names or not names <= {"start.json", "terminal.json"}:
        raise SidecarError("INVALID_INPUT")
    start = _load_start(sidecar_id)
    return start, _load_terminal(sidecar_id, start)


def _validate_unlocked(sidecar_id: str) -> dict[str, Any]:
    _start, terminal = _validate_sidecar_container(sidecar_id)
    return {
        "schema_version": "pr_evidence_sidecar.validation.v1",
        "policy_version": POLICY_VERSION,
        "repository": REPOSITORY,
        "command": "validate",
        "sidecar_id": sidecar_id,
        "receipt_state": "terminal_recorded" if terminal is not None else "start_recorded",
        "authority": AUTHORITY,
        "disclaimer": DISCLAIMER,
    }


def validate(sidecar_id: str) -> dict[str, Any]:
    with _store_lock(exclusive=False, create_store=False) as store_exists:
        if not store_exists:
            raise SidecarError("INVALID_INPUT")
        return _validate_unlocked(sidecar_id)


def _report_unlocked() -> dict[str, Any]:
    if not STORE_ROOT.exists() and not STORE_ROOT.is_symlink():
        entries: list[Path] = []
    else:
        entries = _validate_root_index()
    starts: list[dict[str, Any]] = []
    terminals: list[dict[str, Any]] = []
    for directory in entries:
        sidecar_id = "sha256:" + directory.name
        start, terminal = _validate_sidecar_container(sidecar_id)
        starts.append(start)
        if terminal is not None:
            terminals.append(terminal)
    totals = {
        "operator_minutes_known": 0,
        "review_cycles": 0,
        "repair_cycles": 0,
    }
    counts = {
        "start_receipts": len(starts),
        "terminal_receipts": len(terminals),
        "start_only_receipts": len(starts) - len(terminals),
        "observed_merged": 0,
        "observed_closed_unmerged": 0,
        "operator_minutes_unknown": 0,
    }
    for terminal in terminals:
        counts[f"observed_{terminal['observed_pr_terminal_state']}"] += 1
        observations = terminal["operator_observations"]
        if observations["operator_minutes"] == "unknown":
            counts["operator_minutes_unknown"] += 1
        else:
            totals["operator_minutes_known"] += observations["operator_minutes"]
        totals["review_cycles"] += observations["review_cycles"]
        totals["repair_cycles"] += observations["repair_cycles"]
    return {
        "schema_version": REPORT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "repository": REPOSITORY,
        "command": "report",
        "counts": counts,
        "totals": totals,
        "authority": AUTHORITY,
        "disclaimer": DISCLAIMER,
    }


def report() -> dict[str, Any]:
    with _store_lock(exclusive=False, create_store=False) as store_exists:
        if not store_exists:
            return _report_unlocked()
        return _report_unlocked()


def _parser() -> StrictParser:
    parser = StrictParser()
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--packet", required=True)
    prepare_parser.add_argument("--base-sha", required=True)
    prepare_parser.add_argument("--applicable-rail", action="append", required=True, choices=RAILS)
    finalize_parser = commands.add_parser("finalize")
    finalize_parser.add_argument("--sidecar-id", required=True)
    finalize_parser.add_argument("--terminal-input", required=True)
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--sidecar-id", required=True)
    commands.add_parser("report")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.command == "prepare":
            output = prepare(Path(args.packet), args.base_sha, args.applicable_rail)
        elif args.command == "finalize":
            output = finalize(args.sidecar_id, args.terminal_input)
        elif args.command == "validate":
            output = validate(args.sidecar_id)
        else:
            output = report()
        print(json.dumps(output, sort_keys=True, separators=(",", ":")))
        return 0
    except SidecarError as exc:
        print(exc.category, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
