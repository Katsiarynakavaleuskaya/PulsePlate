"""Offline contract tests for the fixed FastEmbed compatibility transformation."""

from __future__ import annotations

import base64
import csv
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import stat
from typing import Callable
import zipfile

import pytest

from scripts.ci import build_fastembed_compat_wheel as builder


def _digest(content: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(
        b"="
    ).decode("ascii")


def _members(recipe: builder.BuildRecipe) -> dict[str, bytes]:
    metadata = b"Metadata-Version: 2.4\nName: fastembed\nRequires-Python: >=3.10.0\n"
    metadata += b"\n".join(before for before, _ in recipe.replacements)
    metadata += b"\nRequires-Dist: other (>=1.0)\n\nDescription keeps Version: 0.8.0 unchanged.\n"
    return {
        "fastembed/__init__.py": b'raise RuntimeError("must never execute wheel code")\n',
        "fastembed/model.bin": b"\x00\xffunchanged payload\x00",
        builder.SOURCE_DIST_INFO + "METADATA": metadata,
        builder.SOURCE_DIST_INFO
        + "WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        builder.SOURCE_DIST_INFO + "licenses/LICENSE": b"License bytes\n",
        builder.SOURCE_DIST_INFO + "licenses/NOTICE": b"Notice bytes\n",
    }


def _source_bytes(
    members: dict[str, bytes],
    *,
    record_edit: Callable[[list[list[str]]], None] | None = None,
    duplicate: bool = False,
    mode: int = stat.S_IFREG | 0o644,
) -> bytes:
    record_name = builder.SOURCE_DIST_INFO + "RECORD"
    rows = [[name, _digest(value), str(len(value))] for name, value in members.items()]
    rows.append([record_name, "", ""])
    if record_edit is not None:
        record_edit(rows)
    record = io.StringIO(newline="")
    csv.writer(record, lineterminator="\n").writerows(rows)
    complete = {**members, record_name: record.getvalue().encode("utf-8")}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, value in complete.items():
            item = zipfile.ZipInfo(name, date_time=(2016, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.create_system = 3
            item.external_attr = (0o644 if name == record_name else mode) << 16
            archive.writestr(item, value)
        if duplicate:
            with pytest.warns(UserWarning, match="Duplicate name"):
                archive.writestr(next(iter(complete)), next(iter(complete.values())))
    return output.getvalue()


def _bind(content: bytes, recipe: builder.BuildRecipe) -> builder.BuildRecipe:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return replace(
            recipe,
            sha256=hashlib.sha256(content).hexdigest(),
            size=len(content),
            member_count=len(archive.infolist()),
            uncompressed_size=sum(item.file_size for item in archive.infolist()),
        )


@pytest.fixture
def baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, builder.BuildRecipe]:
    recipe = builder._load_recipe()
    content = _source_bytes(_members(recipe))
    recipe = _bind(content, recipe)
    source = tmp_path / builder.SOURCE_FILENAME
    source.write_bytes(content)
    monkeypatch.setattr(builder, "_load_recipe", lambda: recipe)
    return source, recipe


def _assert_output(source: bytes, output: bytes, recipe: builder.BuildRecipe) -> None:
    with (
        zipfile.ZipFile(io.BytesIO(source)) as original,
        zipfile.ZipFile(io.BytesIO(output)) as derived,
    ):
        expected_names = [
            name.replace(builder.SOURCE_DIST_INFO, builder.OUTPUT_DIST_INFO, 1)
            for name in original.namelist()
        ]
        assert derived.namelist() == expected_names
        for old, new in zip(original.infolist(), derived.infolist(), strict=True):
            assert new.external_attr == old.external_attr
            assert new.date_time == old.date_time
            assert new.create_system == old.create_system
            if old.filename.endswith("/RECORD"):
                continue
            expected = original.read(old)
            if old.filename.endswith("/METADATA"):
                for before, after in recipe.replacements:
                    expected = expected.replace(before + b"\n", after + b"\n", 1)
            assert derived.read(new) == expected
        record_name = builder.OUTPUT_DIST_INFO + "RECORD"
        rows = list(csv.reader(io.StringIO(derived.read(record_name).decode("utf-8"))))
        assert len(rows) == len(expected_names)
        assert {row[0] for row in rows} == set(expected_names)
        for name, digest, size in rows:
            assert (digest, size) == (
                ("", "")
                if name == record_name
                else (_digest(derived.read(name)), str(len(derived.read(name))))
            )


def test_fixed_recipe_records_actual_upstream_and_only_four_edits() -> None:
    recipe = builder._load_recipe()
    assert recipe.sha256 == "40bee672657574a1009e35ec50030a55f2b426842cb011845379817641bbbbd0"
    assert (recipe.size, recipe.member_count, recipe.uncompressed_size) == (116572, 64, 382377)
    assert recipe.replacements[0] == (b"Version: 0.8.0", b"Version: 0.8.0+pulseplate.1")
    for before, after in recipe.replacements[1:]:
        assert after == before.replace(b",<13.0)", b",<14.0)")


@pytest.mark.parametrize(
    "defect,diagnostic",
    [
        ("duplicate", "recipe_duplicate_key"),
        ("unknown", "recipe_fields"),
        ("identity", "recipe_identity"),
        ("digest", "recipe_digest"),
        ("boolean_size", "recipe_bounds"),
        ("oversized", "recipe_bounds"),
        ("missing_edit", "recipe_edits"),
        ("extra_edit_field", "recipe_edits"),
        ("newline", "recipe_edits"),
        ("version", "recipe_edits"),
        ("changed_minimum", "recipe_edits"),
        ("duplicate_edit", "recipe_edits"),
    ],
)
def test_recipe_rejects_unexpected_transform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str, diagnostic: str
) -> None:
    builder._load_recipe()
    document = json.loads(builder.RECIPE_PATH.read_bytes())
    if defect == "unknown":
        document["unexpected"] = True
    elif defect == "identity":
        document["output_filename"] = "other.whl"
    elif defect == "digest":
        document["source_sha256"] = "invalid"
    elif defect == "boolean_size":
        document["source_size"] = True
    elif defect == "oversized":
        document["uncompressed_size"] = 1048577
    elif defect == "missing_edit":
        document["metadata_replacements"].pop()
    elif defect == "extra_edit_field":
        document["metadata_replacements"][0]["unexpected"] = True
    elif defect == "newline":
        document["metadata_replacements"][0]["after"] += "\n"
    elif defect == "version":
        document["metadata_replacements"][0]["after"] = "Version: 0.9.0"
    elif defect == "changed_minimum":
        document["metadata_replacements"][1]["after"] = document["metadata_replacements"][1][
            "after"
        ].replace("10.3.0", "13.0.0")
    elif defect == "duplicate_edit":
        document["metadata_replacements"][2] = document["metadata_replacements"][1]
    raw = json.dumps(document)
    if defect == "duplicate":
        raw = raw.replace("{", '{"source_size":116572,', 1)
    recipe_path = tmp_path / "recipe.json"
    recipe_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(builder, "RECIPE_PATH", recipe_path)
    with pytest.raises(ValueError, match=diagnostic):
        builder._load_recipe()


def test_wrong_source_filename_and_oversized_input_fail_without_output(
    baseline: tuple[Path, builder.BuildRecipe], tmp_path: Path
) -> None:
    source, _ = baseline
    with pytest.raises(ValueError, match="source_filename_mismatch"):
        builder.build_wheel(source.with_name("other.whl"), tmp_path)
    source.write_bytes(source.read_bytes() + b"extra")
    with pytest.raises(ValueError, match="input_size_limit"):
        builder.build_wheel(source, tmp_path)
    assert not (tmp_path / builder.OUTPUT_FILENAME).exists()


def test_declared_member_count_and_uncompressed_size_are_bound(
    baseline: tuple[Path, builder.BuildRecipe],
) -> None:
    source, recipe = baseline
    with pytest.raises(ValueError, match="wheel_member_cardinality"):
        builder._transform(
            source.read_bytes(), replace(recipe, member_count=recipe.member_count + 1)
        )
    with pytest.raises(ValueError, match="wheel_uncompressed_size"):
        builder._transform(
            source.read_bytes(), replace(recipe, uncompressed_size=recipe.uncompressed_size + 1)
        )


def test_two_builds_preserve_all_other_payload_modes_and_records(
    baseline: tuple[Path, builder.BuildRecipe], tmp_path: Path
) -> None:
    source, recipe = baseline
    original = source.read_bytes()
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    result = builder.build_wheel(source, first)
    assert result.read_bytes() == builder.build_wheel(source, second).read_bytes()
    assert stat.S_IMODE(result.stat().st_mode) == 0o600
    assert source.read_bytes() == original
    _assert_output(original, result.read_bytes(), recipe)


@pytest.mark.parametrize(
    "defect,diagnostic", [("digest", "source_sha256_mismatch"), ("size", "source_size_mismatch")]
)
def test_source_binding_rejects_before_zip_parsing(
    baseline: tuple[Path, builder.BuildRecipe],
    monkeypatch: pytest.MonkeyPatch,
    defect: str,
    diagnostic: str,
) -> None:
    source, recipe = baseline
    content = source.read_bytes()
    bad = b"!" * len(content) if defect == "digest" else content[:-1]

    def forbidden_zip(*args: object, **kwargs: object) -> None:
        pytest.fail("ZIP parser ran before source binding")

    monkeypatch.setattr(builder.zipfile, "ZipFile", forbidden_zip)
    with pytest.raises(ValueError, match=diagnostic):
        builder._transform(bad, recipe)


@pytest.mark.parametrize(
    "defect,diagnostic",
    [
        ("duplicate", "wheel_member_cardinality"),
        ("missing_license", "wheel_required_members"),
        ("foreign_root", "wheel_member_identity"),
        ("traversal", "wheel_member_identity"),
        ("symlink_member", "wheel_member_identity"),
        ("metadata_missing", "metadata_edit_cardinality"),
        ("metadata_duplicate", "metadata_edit_cardinality"),
        ("metadata_name", "metadata_identity"),
        ("record_omitted", "record_membership"),
        ("record_duplicate", "record_membership"),
        ("record_extra", "record_membership"),
        ("record_hash", "record_integrity"),
        ("record_size", "record_integrity"),
        ("record_self", "record_integrity"),
    ],
)
def test_independent_mutants_fail_without_output(
    baseline: tuple[Path, builder.BuildRecipe],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    defect: str,
    diagnostic: str,
) -> None:
    source, recipe = baseline
    builder._transform(source.read_bytes(), recipe)
    members = _members(recipe)
    metadata = builder.SOURCE_DIST_INFO + "METADATA"
    if defect == "missing_license":
        del members[builder.SOURCE_DIST_INFO + "licenses/LICENSE"]
    elif defect in {"foreign_root", "traversal"}:
        members["other/file" if defect == "foreign_root" else "fastembed/../file"] = b"bad"
    elif defect == "metadata_missing":
        members[metadata] = members[metadata].replace(recipe.replacements[1][0] + b"\n", b"")
    elif defect == "metadata_duplicate":
        members[metadata] = recipe.replacements[1][0] + b"\n" + members[metadata]
    elif defect == "metadata_name":
        members[metadata] = b"Name: other\n" + members[metadata]

    def edit(rows: list[list[str]]) -> None:
        if defect == "record_omitted":
            rows.pop(0)
        elif defect == "record_duplicate":
            rows.append(rows[0])
        elif defect == "record_extra":
            rows.append(["absent", "", ""])
        elif defect == "record_hash":
            rows[0][1] = "sha256=wrong"
        elif defect == "record_size":
            rows[0][2] = "0"
        elif defect == "record_self":
            rows[-1][1] = "sha256=wrong"

    mutated = _source_bytes(
        members,
        record_edit=edit,
        duplicate=defect == "duplicate",
        mode=stat.S_IFLNK | 0o644 if defect == "symlink_member" else stat.S_IFREG | 0o644,
    )
    source.write_bytes(mutated)
    monkeypatch.setattr(builder, "_load_recipe", lambda: _bind(mutated, recipe))
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ValueError, match=diagnostic):
        builder.build_wheel(source, output)
    assert list(output.iterdir()) == []
    assert source.read_bytes() == mutated


def test_existing_output_is_never_replaced(
    baseline: tuple[Path, builder.BuildRecipe], tmp_path: Path
) -> None:
    source, _ = baseline
    output = tmp_path / builder.OUTPUT_FILENAME
    output.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        builder.build_wheel(source, tmp_path)
    assert output.read_bytes() == b"existing"


@pytest.mark.parametrize(
    "defect", ["symlink_source", "hardlink_source", "symlink_parent", "symlink_output"]
)
def test_unsafe_filesystem_objects_are_rejected(
    baseline: tuple[Path, builder.BuildRecipe], tmp_path: Path, defect: str
) -> None:
    source, _ = baseline
    original = source.read_bytes()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    if defect == "symlink_source":
        saved = source.rename(tmp_path / "saved")
        source.symlink_to(saved)
    elif defect == "hardlink_source":
        os.link(source, tmp_path / "alias")
    elif defect == "symlink_parent":
        alias = tmp_path / "alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        source = alias / source.name
    else:
        (output_dir / builder.OUTPUT_FILENAME).symlink_to(source)
    with pytest.raises((OSError, ValueError)):
        builder.build_wheel(source, output_dir)
    assert source.read_bytes() == original
    assert (
        not (output_dir / builder.OUTPUT_FILENAME).exists()
        or (output_dir / builder.OUTPUT_FILENAME).is_symlink()
    )


def test_cli_reports_success_and_collision_without_native_claim(
    baseline: tuple[Path, builder.BuildRecipe], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source, _ = baseline
    args = ["--source-wheel", str(source), "--output-dir", str(tmp_path)]
    assert builder.main(args) == 0
    assert "native compatibility and publication are not established" in capsys.readouterr().out
    assert builder.main(args) == 1
    assert "FileExistsError" in capsys.readouterr().err


@pytest.mark.parametrize("mutation", [None, "source", "private", "recipe", "different-derivation"])
def test_audit_comparison_requires_actual_canonical_pair(
    baseline: tuple[Path, builder.BuildRecipe],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str | None,
) -> None:
    from scripts.ci import audit_fastembed_compat as audit

    source, recipe = baseline
    original = source.read_bytes()
    private = builder._transform(original, recipe)
    private_path = tmp_path / builder.OUTPUT_FILENAME
    private_path.write_bytes(private)
    monkeypatch.setattr(audit, "SOURCE_SHA256", hashlib.sha256(original).hexdigest())
    monkeypatch.setattr(audit, "PRIVATE_SHA256", hashlib.sha256(private).hexdigest())
    proof = audit._prove_pair(tmp_path)
    assert proof["private_wheel_sha256"] == hashlib.sha256(private).hexdigest()
    if mutation is None:
        return
    diagnostic = "compat_wheel_identity_changed"
    if mutation == "source":
        source.write_bytes(b"!" + original[1:])
    elif mutation == "private":
        private_path.write_bytes(b"!" + private[1:])
    elif mutation == "recipe":
        changed_recipe = tmp_path / "recipe.json"
        changed_recipe.write_bytes(builder.RECIPE_PATH.read_bytes() + b" ")
        monkeypatch.setattr(builder, "RECIPE_PATH", changed_recipe)
        diagnostic = "compat_recipe_changed"
    else:
        members = _members(recipe)
        members["fastembed/__init__.py"] = b"print('unapproved executable change')\n"
        different_source = _source_bytes(members)
        different_private = builder._transform(different_source, _bind(different_source, recipe))
        private_path.write_bytes(different_private)
        monkeypatch.setattr(audit, "PRIVATE_SHA256", hashlib.sha256(different_private).hexdigest())
        diagnostic = "compat_wheel_derivation_mismatch"
    with pytest.raises(audit.AuditFailure, match=diagnostic):
        audit._prove_pair(tmp_path)
