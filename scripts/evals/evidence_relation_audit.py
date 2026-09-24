"""Offline NOOS-1A JSONL validator and deterministic structural report.

Usage: python -m scripts.evals.evidence_relation_audit validate --input SNAPSHOT.jsonl
       python -m scripts.evals.evidence_relation_audit report --input SNAPSHOT.jsonl --output REPORT.json

Limits: 8 MiB input and report, 256 KiB per line, 10,000 records, JSON depth
32, and 512 references per record. Successful report publication may include
negative assessments; it does not certify causality or grant authority.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import stat
import sys
from typing import cast

from core.evidence.relations import audit_snapshot, parse_snapshot

MAX_BYTES = 8 * 1024 * 1024
MAX_LINE_BYTES = 256 * 1024
MAX_RECORDS = 10_000
MAX_DEPTH = 32
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


class _JsonlPolicyError(ValueError):
    """Known parser-policy rejection with a fixed, content-free category."""


def _components(path: Path) -> tuple[str, ...]:
    parts = path.parts
    if not parts or any(part in ("", ".", "..") for part in parts if part != path.anchor):
        raise ValueError("unsafe_path")
    components = parts[1:] if path.is_absolute() else parts
    if not components or any(part in ("", ".", "..") for part in components):
        raise ValueError("unsafe_path")
    return tuple(components)


def _parent_fd(path: Path) -> tuple[int, str]:
    components = _components(path)
    try:
        current = os.open(path.anchor if path.is_absolute() else ".", _DIR_FLAGS)
    except OSError as exc:
        raise ValueError("unsafe_path") from exc
    try:
        for part in components[:-1]:
            next_fd = os.open(part, _DIR_FLAGS, dir_fd=current)
            os.close(current)
            current = next_fd
        return current, components[-1]
    except OSError as exc:
        os.close(current)
        raise ValueError("unsafe_path") from exc


def _read_input(path: Path) -> bytes:
    parent, name = _parent_fd(path)
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        try:
            fd = os.open(name, flags, dir_fd=parent)
        except OSError as exc:
            raise ValueError("unsafe_input") from exc
        try:
            before = os.fstat(fd)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size > MAX_BYTES
            ):
                raise ValueError("unsafe_input")
            chunks: list[bytes] = []
            total = 0
            while True:
                part = os.read(fd, min(65536, MAX_BYTES + 1 - total))
                if not part:
                    break
                total += len(part)
                if total > MAX_BYTES:
                    raise ValueError("input_limit")
                chunks.append(part)
            after = os.fstat(fd)
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            before_identity = (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_nlink,
            )
            after_identity = (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_nlink,
            )
            named_identity = (
                named.st_dev,
                named.st_ino,
                named.st_size,
                named.st_mtime_ns,
                named.st_nlink,
            )
            if before_identity != after_identity or after_identity != named_identity:
                raise ValueError("input_changed")
            first_read = b"".join(chunks)
            os.lseek(fd, 0, os.SEEK_SET)
            compared = 0
            while True:
                part = os.read(fd, min(65536, MAX_BYTES + 1 - compared))
                if not part:
                    break
                next_offset = compared + len(part)
                if next_offset > MAX_BYTES or first_read[compared:next_offset] != part:
                    raise ValueError("input_changed")
                compared = next_offset
            if compared != len(first_read):
                raise ValueError("input_changed")
            final = os.fstat(fd)
            final_named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            final_identity = (
                final.st_dev,
                final.st_ino,
                final.st_size,
                final.st_mtime_ns,
                final.st_nlink,
            )
            final_named_identity = (
                final_named.st_dev,
                final_named.st_ino,
                final_named.st_size,
                final_named.st_mtime_ns,
                final_named.st_nlink,
            )
            if after_identity != final_identity or final_identity != final_named_identity:
                raise ValueError("input_changed")
            return first_read
        except OSError as exc:
            raise ValueError("unsafe_input") from exc
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _JsonlPolicyError("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise _JsonlPolicyError("json_constant")


def _check_depth(value: object, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise _JsonlPolicyError("json_depth")
    if type(value) is dict:
        for child in cast(dict[str, object], value).values():
            _check_depth(child, depth + 1)
    elif type(value) is list:
        for child in cast(list[object], value):
            _check_depth(child, depth + 1)


def read_jsonl(path: Path) -> list[object]:
    """Read a bounded, strict JSONL snapshot through no-follow descriptors."""
    data = _read_input(path)
    if not data or data.startswith(b"\xef\xbb\xbf"):
        raise ValueError("jsonl_format")
    lines = data.split(b"\n")
    if lines[-1] == b"":
        lines.pop()
    if len(lines) > MAX_RECORDS:
        raise ValueError("input_limit")
    rows: list[object] = []
    for line in lines:
        if not line or len(line) > MAX_LINE_BYTES or line.endswith(b"\r"):
            raise ValueError("jsonl_format")
        try:
            value = json.loads(
                line.decode("utf-8"),
                object_pairs_hook=_unique_pairs,
                parse_constant=_reject_constant,
            )
            _check_depth(value)
        except _JsonlPolicyError:
            raise
        except (UnicodeDecodeError, ValueError, RecursionError) as exc:
            raise ValueError("jsonl_format") from exc
        rows.append(value)
    return rows


def _report_bytes(rows: list[object]) -> bytes:
    report = audit_snapshot(parse_snapshot(rows)).to_dict()
    data = (
        json.dumps(
            report, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")
    if len(data) > MAX_BYTES:
        raise ValueError("report_limit")
    return data


def write_report(path: Path, data: bytes) -> None:
    """Publish one private complete report with a same-directory no-replace link."""
    if len(data) > MAX_BYTES:
        raise ValueError("report_limit")
    parent, name = _parent_fd(path)
    stage = f".noos1a-{secrets.token_hex(16)}.tmp"
    staged = False
    failure: ValueError | None = None
    try:
        parent_info = os.fstat(parent)
        if parent_info.st_uid != os.getuid() or parent_info.st_mode & 0o022:
            raise ValueError("unsafe_output_parent")
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError("output_exists")
        fd = os.open(
            stage,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=parent,
        )
        staged = True
        try:
            os.fchmod(fd, 0o600)
            offset = 0
            while offset < len(data):
                count = os.write(fd, data[offset:])
                if count <= 0:
                    raise ValueError("output_publication")
                offset += count
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.link(stage, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        except FileExistsError as exc:
            raise ValueError("output_exists") from exc
        os.fsync(parent)
    except ValueError as exc:
        failure = exc
    except OSError:
        failure = ValueError("output_publication")
    finally:
        if staged:
            try:
                os.unlink(stage, dir_fd=parent)
                os.fsync(parent)
            except OSError:
                failure = ValueError("output_publication")
        os.close(parent)
    if failure is not None:
        raise failure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "report"):
        sub = commands.add_parser(command)
        sub.add_argument("--input", required=True, type=Path)
        if command == "report":
            sub.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        rows = read_jsonl(args.input)
        if args.command == "validate":
            parse_snapshot(rows)
        else:
            data = _report_bytes(rows)
            write_report(args.output, data)
    except ValueError as exc:
        print(f"evidence_relation_audit: {exc}", file=sys.stderr)
        return 2
    except OSError:
        print("evidence_relation_audit: io_failure", file=sys.stderr)
        return 2
    print(
        "evidence_relation_audit: valid snapshot"
        if args.command == "validate"
        else "evidence_relation_audit: report published"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
