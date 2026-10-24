#!/usr/bin/env python3
"""Offline, hash-bound FastEmbed 0.8.0 compatibility wheel transformation.

This command does not acquire, install, execute or publish packages. Its fixed
recipe permits only distribution-version and Pillow-upper-bound metadata edits.
Native compatibility and private-index delivery require separate evidence.
"""

from __future__ import annotations

import argparse
import base64
import copy
import csv
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile

SOURCE_FILENAME = "fastembed-0.8.0-py3-none-any.whl"
OUTPUT_FILENAME = "fastembed-0.8.0+pulseplate.1-py3-none-any.whl"
SOURCE_DIST_INFO = "fastembed-0.8.0.dist-info/"
OUTPUT_DIST_INFO = "fastembed-0.8.0+pulseplate.1.dist-info/"
RECIPE_PATH = Path(__file__).absolute().with_name("fastembed_compat_build.json")


@dataclass(frozen=True)
class BuildRecipe:
    """Captured identity and literal metadata edits for the single source wheel."""

    sha256: str
    size: int
    member_count: int
    uncompressed_size: int
    replacements: tuple[tuple[bytes, bytes], ...]


def _directory_fd(path: Path) -> int:
    """Open an existing directory chain without following symlinks."""
    absolute = path.absolute()
    descriptor = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:]:
            if part in {".", ".."}:
                raise ValueError("directory_path_not_literal")
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_regular(path: Path, limit: int) -> bytes:
    """Read one bounded regular-file buffer through the admitted descriptor."""
    parent = _directory_fd(path.parent)
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError("input_not_single_regular_file")
        if before.st_size > limit:
            raise ValueError("input_size_limit")
        content = stream.read(limit + 1)
        after = os.fstat(stream.fileno())

        def identity(item: os.stat_result) -> tuple[int, ...]:
            return (
                item.st_dev,
                item.st_ino,
                item.st_mode,
                item.st_nlink,
                item.st_size,
                item.st_mtime_ns,
                item.st_ctime_ns,
            )

        if identity(before) != identity(after) or len(content) != before.st_size:
            raise ValueError("input_changed_during_read")
        return content


def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("recipe_duplicate_key")
        result[key] = value
    return result


def _load_recipe() -> BuildRecipe:
    raw = json.loads(_read_regular(RECIPE_PATH, 8192), object_pairs_hook=_json_object)
    keys = {
        "source_filename",
        "output_filename",
        "source_sha256",
        "source_size",
        "member_count",
        "uncompressed_size",
        "metadata_replacements",
    }
    if type(raw) is not dict or set(raw) != keys:
        raise ValueError("recipe_fields")
    if raw["source_filename"] != SOURCE_FILENAME or raw["output_filename"] != OUTPUT_FILENAME:
        raise ValueError("recipe_identity")
    digest = raw["source_sha256"]
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("recipe_digest")
    for key, limit in (
        ("source_size", 1048576),
        ("member_count", 128),
        ("uncompressed_size", 1048576),
    ):
        if type(raw[key]) is not int or not 0 < raw[key] <= limit:
            raise ValueError("recipe_bounds")
    edits = raw["metadata_replacements"]
    if type(edits) is not list or len(edits) != 4:
        raise ValueError("recipe_edits")
    replacements: list[tuple[bytes, bytes]] = []
    for index, edit in enumerate(edits):
        if type(edit) is not dict or set(edit) != {"before", "after"}:
            raise ValueError("recipe_edits")
        before, after = edit["before"], edit["after"]
        if (
            not isinstance(before, str)
            or not isinstance(after, str)
            or any(character in before + after for character in "\r\n")
        ):
            raise ValueError("recipe_edits")
        if index == 0:
            valid = (before, after) == ("Version: 0.8.0", "Version: 0.8.0+pulseplate.1")
        else:
            valid = (
                before.startswith("Requires-Dist: pillow (")
                and before.count(",<13.0)") == 1
                and after == before.replace(",<13.0)", ",<14.0)")
            )
        if not valid or any(previous == before.encode("utf-8") for previous, _ in replacements):
            raise ValueError("recipe_edits")
        replacements.append((before.encode("utf-8"), after.encode("utf-8")))
    return BuildRecipe(
        digest,
        raw["source_size"],
        raw["member_count"],
        raw["uncompressed_size"],
        tuple(replacements),
    )


def _record_hash(content: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(
        b"="
    ).decode("ascii")


def _validate_record(members: dict[str, bytes], record_name: str) -> None:
    rows = csv.reader(io.StringIO(members[record_name].decode("utf-8"), newline=""), strict=True)
    seen: set[str] = set()
    for row in rows:
        if len(row) != 3 or row[0] in seen or row[0] not in members:
            raise ValueError("record_membership")
        name, digest, size = row
        seen.add(name)
        expected = (
            ("", "")
            if name == record_name
            else (_record_hash(members[name]), str(len(members[name])))
        )
        if (digest, size) != expected:
            raise ValueError("record_integrity")
    if seen != set(members):
        raise ValueError("record_membership")


def _rewrite_metadata(content: bytes, recipe: BuildRecipe) -> bytes:
    headers, separator, body = content.partition(b"\n\n")
    lines = headers.split(b"\n")
    if (
        not separator
        or [line for line in lines if line.lower().startswith(b"name:")] != [b"Name: fastembed"]
        or [line for line in lines if line.lower().startswith(b"requires-python:")]
        != [b"Requires-Python: >=3.10.0"]
    ):
        raise ValueError("metadata_identity")
    selected = [
        line
        for line in lines
        if line.lower().startswith(b"version:") or line.lower().startswith(b"requires-dist: pillow")
    ]
    if sorted(selected) != sorted(before for before, _ in recipe.replacements):
        raise ValueError("metadata_edit_cardinality")
    for before, after in recipe.replacements:
        if lines.count(before) != 1:
            raise ValueError("metadata_edit_cardinality")
        lines[lines.index(before)] = after
    return b"\n".join(lines) + separator + body


def _transform(content: bytes, recipe: BuildRecipe) -> bytes:
    """Validate the captured buffer before interpreting its ZIP members."""
    if len(content) != recipe.size:
        raise ValueError("source_size_mismatch")
    if hashlib.sha256(content).hexdigest() != recipe.sha256:
        raise ValueError("source_sha256_mismatch")
    with zipfile.ZipFile(io.BytesIO(content)) as source:
        infos = source.infolist()
        names = [info.filename for info in infos]
        if len(infos) != recipe.member_count or len(set(names)) != len(names):
            raise ValueError("wheel_member_cardinality")
        if sum(info.file_size for info in infos) != recipe.uncompressed_size:
            raise ValueError("wheel_uncompressed_size")
        for info in infos:
            parts = info.filename.split("/")
            if (
                info.orig_filename != info.filename
                or any(part in {"", ".", ".."} for part in parts)
                or "\\" in info.filename
                or parts[0] not in {"fastembed", SOURCE_DIST_INFO[:-1]}
                or stat.S_IFMT(info.external_attr >> 16) not in {0, stat.S_IFREG}
                or info.flag_bits != 0
                or info.compress_type != zipfile.ZIP_DEFLATED
            ):
                raise ValueError("wheel_member_identity")
        required = {
            SOURCE_DIST_INFO + name
            for name in ("METADATA", "WHEEL", "RECORD", "licenses/LICENSE", "licenses/NOTICE")
        }
        if not required <= set(names):
            raise ValueError("wheel_required_members")
        members = {info.filename: source.read(info) for info in infos}
        record_name = SOURCE_DIST_INFO + "RECORD"
        _validate_record(members, record_name)
        members[SOURCE_DIST_INFO + "METADATA"] = _rewrite_metadata(
            members[SOURCE_DIST_INFO + "METADATA"], recipe
        )
        renamed = {
            name: (
                name.replace(SOURCE_DIST_INFO, OUTPUT_DIST_INFO, 1)
                if name.startswith(SOURCE_DIST_INFO)
                else name
            )
            for name in names
        }
        record = io.StringIO(newline="")
        writer = csv.writer(record, lineterminator="\n")
        for name in names:
            writer.writerow(
                (renamed[name], "", "")
                if name == record_name
                else (renamed[name], _record_hash(members[name]), str(len(members[name])))
            )
        members[record_name] = record.getvalue().encode("utf-8")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as destination:
            destination.comment = source.comment
            for original in infos:
                item = copy.copy(original)
                item.filename = item.orig_filename = renamed[original.filename]
                destination.writestr(item, members[original.filename])
        return output.getvalue()


def build_wheel(source_wheel: Path, output_dir: Path) -> Path:
    """Create the one derived wheel exclusively in an existing real directory."""
    if source_wheel.name != SOURCE_FILENAME:
        raise ValueError("source_filename_mismatch")
    recipe = _load_recipe()
    result = _transform(_read_regular(source_wheel, recipe.size), recipe)
    directory = _directory_fd(output_dir)
    try:
        descriptor = os.open(
            OUTPUT_FILENAME,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(result)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(directory)
    finally:
        os.close(directory)
    return output_dir / OUTPUT_FILENAME


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-wheel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        output = build_wheel(args.source_wheel, args.output_dir)
    except (OSError, ValueError, csv.Error, zipfile.BadZipFile) as exc:
        detail = (
            str(exc)
            if isinstance(exc, ValueError) and not isinstance(exc, UnicodeError)
            else type(exc).__name__
        )
        print(f"ERROR: fastembed compatibility build: {detail}", file=sys.stderr)
        return 1
    print(f"Created {output.name}; native compatibility and publication are not established.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
