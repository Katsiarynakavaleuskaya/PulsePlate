"""Offline JSONL and publication boundaries for NOOS-1A."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
from typing import cast

import pytest

from core.evidence.fingerprints import (
    JsonValue,
    build_asset_id,
    build_idempotency_key,
    fingerprint_payload,
)
from core.evidence.relations import audit_snapshot, parse_snapshot
from scripts.evals import evidence_relation_audit as cli

FIXTURE = Path(__file__).parent / "fixtures/evidence_relation_audit_v1.jsonl"


def _seal(row: dict[str, object]) -> None:
    row["record_fingerprint"] = fingerprint_payload(
        cast(JsonValue, {key: value for key, value in row.items() if key != "record_fingerprint"})
    )


def _basic_rows() -> list[dict[str, object]]:
    source = cli.read_jsonl(FIXTURE)
    return [
        deepcopy(row)
        for row in source
        if isinstance(row, dict) and (row.get("kind") == "asset" or row.get("id") == "W7")
    ]


def _asset_id(row: dict[str, object]) -> str:
    asset = row["asset"]
    assert isinstance(asset, dict)
    identifier = asset["asset_id"]
    assert isinstance(identifier, str)
    return identifier


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8"
    )


def test_frozen_corpus_has_independent_matrix_and_report_bytes(tmp_path: Path) -> None:
    rows = cli.read_jsonl(FIXTURE)
    report = audit_snapshot(parse_snapshot(rows))
    assert len(report.assessments) == 8
    assert [item.causal_structural_pass for item in report.assessments] == [
        False,
        False,
        False,
        False,
        False,
        False,
        True,
        False,
    ]
    assert report.assessments[-1].reason_codes == ("unresolved_contradiction",)
    assert all(item.authority_granted is False for item in report.assessments)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    assert cli.main(["report", "--input", str(FIXTURE), "--output", str(first)]) == 0
    assert cli.main(["report", "--input", str(FIXTURE), "--output", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes()
    material = json.loads(first.read_bytes())
    checksum = material.pop("report_fingerprint")
    assert fingerprint_payload(material) == checksum
    assert stat.S_IMODE(first.stat().st_mode) == 0o600


def test_input_order_does_not_change_report(tmp_path: Path) -> None:
    rows = _basic_rows()
    source_a = tmp_path / "a.jsonl"
    source_b = tmp_path / "b.jsonl"
    _write(source_a, rows)
    _write(source_b, list(reversed(rows)))
    assert cli._report_bytes(cli.read_jsonl(source_a)) == cli._report_bytes(
        cli.read_jsonl(source_b)
    )
    reversed_keys = [dict(reversed(list(row.items()))) for row in reversed(rows)]
    _write(source_b, reversed_keys)
    assert cli._report_bytes(cli.read_jsonl(source_a)) == cli._report_bytes(
        cli.read_jsonl(source_b)
    )


@pytest.mark.parametrize(
    "bad",
    [
        b"\xef\xbb\xbf{}\n",
        b"{} {}\n",
        b'{"kind":"asset","kind":"asset"}\n',
        b"\xff\n",
        b"{}\n\n",
        b"[" * 34 + b"]" * 34 + b"\n",
        b"{}\n" + b"x" * (cli.MAX_LINE_BYTES + 1),
    ],
)
def test_bad_jsonl_cannot_publish(tmp_path: Path, bad: bytes) -> None:
    source = tmp_path / "bad.jsonl"
    target = tmp_path / "out.json"
    source.write_bytes(bad)
    assert cli.main(["report", "--input", str(source), "--output", str(target)]) == 2
    assert not target.exists()


def test_decoder_integer_limit_error_is_content_free_and_cannot_publish(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "huge-integer.jsonl"
    target = tmp_path / "out.json"
    source.write_bytes(b'{"value":' + b"9" * 5000 + b"}\n")
    assert cli.main(["report", "--input", str(source), "--output", str(target)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "evidence_relation_audit: jsonl_format\n"
    assert not target.exists()


def test_reference_type_duplicate_and_raw_value_rejection() -> None:
    rows = _basic_rows()
    with pytest.raises(ValueError, match="duplicate_id"):
        parse_snapshot([*rows, deepcopy(rows[-1])])
    broken = deepcopy(rows)
    broken[-1]["method_refs"] = ["missing"]
    _seal(broken[-1])
    with pytest.raises(ValueError, match="reference"):
        parse_snapshot(broken)
    broken = deepcopy(rows)
    broken[-1]["method_refs"] = [_asset_id(broken[0])]
    _seal(broken[-1])
    with pytest.raises(ValueError, match="reference"):
        parse_snapshot(broken)
    broken = deepcopy(rows)
    broken[-1]["epistemic_status"] = True
    _seal(broken[-1])
    with pytest.raises(ValueError, match="schema_value"):
        parse_snapshot(broken)
    broken = deepcopy(rows)
    broken[-1]["produced_at"] = "2026-01-01T00:00:00"
    _seal(broken[-1])
    with pytest.raises(ValueError, match="time_format"):
        parse_snapshot(broken)
    broken = _basic_rows()
    asset = broken[0]["asset"]
    assert isinstance(asset, dict)
    asset["idempotency_key"] = "idem:" + "0" * 64
    with pytest.raises(ValueError, match="asset_identity"):
        parse_snapshot(broken)
    broken = _basic_rows()
    broken[-1]["epistemic_link_refs"] = [f"L{i}" for i in range(511)]
    _seal(broken[-1])
    with pytest.raises(ValueError, match="reference_limit"):
        parse_snapshot(broken)


@pytest.mark.parametrize("field,value", [("version", "v:1"), ("policy_version", "noos1a:v1")])
def test_asset_tokens_reject_colons_even_with_recomputed_identity(field: str, value: str) -> None:
    rows = _basic_rows()
    asset = rows[0]["asset"]
    assert isinstance(asset, dict)
    asset[field] = value
    identity = {
        "asset_type": asset["asset_type"],
        "rail": asset["rail"],
        "version": asset["version"],
        "policy_version": asset["policy_version"],
        "fingerprint": asset["fingerprint"],
        "upstream_ids": tuple(asset["upstream_ids"]),
    }
    asset["asset_id"] = build_asset_id(**identity)
    asset["idempotency_key"] = build_idempotency_key(**identity)
    with pytest.raises(ValueError, match="^schema_value$"):
        parse_snapshot(rows)


def test_revision_cycles_and_cross_type_refs_rejected() -> None:
    rows = _basic_rows()
    prior = deepcopy(rows[-1])
    prior["id"] = "W2"
    prior["revision_of_ref"] = "W7"
    _seal(prior)
    rows[-1]["revision_of_ref"] = "W2"
    _seal(rows[-1])
    with pytest.raises(ValueError, match="revision_cycle"):
        parse_snapshot([*rows, prior])
    rows = _basic_rows()
    rows[-1]["revision_of_ref"] = _asset_id(rows[0])
    _seal(rows[-1])
    with pytest.raises(ValueError, match="revision_reference"):
        parse_snapshot(rows)


def test_unsafe_inputs_and_outputs_preserve_files(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _write(source, _basic_rows())
    alias = tmp_path / "alias.jsonl"
    alias.symlink_to(source)
    with pytest.raises(ValueError, match="unsafe_input"):
        cli.read_jsonl(alias)
    hardlink = tmp_path / "hardlink.jsonl"
    os.link(source, hardlink)
    with pytest.raises(ValueError, match="unsafe_input"):
        cli.read_jsonl(source)
    hardlink.unlink()
    old = tmp_path / "old.json"
    old.write_bytes(b"preserve")
    with pytest.raises(ValueError, match="output_exists"):
        cli.write_report(old, b"replacement")
    assert old.read_bytes() == b"preserve"
    with pytest.raises(ValueError, match="output_exists"):
        cli.write_report(source, b"replacement")
    assert source.read_text(encoding="utf-8").startswith("{")
    symlink = tmp_path / "symlink.json"
    symlink.symlink_to(old)
    with pytest.raises(ValueError, match="output_exists"):
        cli.write_report(symlink, b"replacement")
    assert old.read_bytes() == b"preserve"
    assert not list(tmp_path.glob(".noos1a-*.tmp"))
    linked_dir = tmp_path / "linked_dir"
    linked_dir.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="unsafe_path"):
        cli.write_report(linked_dir / "new.json", b"safe\n")
    fifo = tmp_path / "pipe.jsonl"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="unsafe_input"):
        cli.read_jsonl(fifo)


def test_same_size_rewrite_with_restored_mtime_during_read_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "source.jsonl"
    source.write_bytes(FIXTURE.read_bytes())
    target = tmp_path / "report.json"
    initial = source.stat()
    original = source.read_bytes()
    changed = bytearray(original)
    changed[0] = ord("[")
    triggered = False
    real_read = os.read

    def rewrite_at_first_eof(fd: int, amount: int) -> bytes:
        nonlocal triggered
        part = real_read(fd, amount)
        if not part and not triggered:
            triggered = True
            with source.open("r+b") as stream:
                stream.write(changed)
            os.utime(source, ns=(initial.st_atime_ns, initial.st_mtime_ns))
        return part

    monkeypatch.setattr(cli.os, "read", rewrite_at_first_eof)
    assert cli.main(["report", "--input", str(source), "--output", str(target)]) == 2
    assert triggered
    assert len(source.read_bytes()) == len(original)
    assert source.stat().st_mtime_ns == initial.st_mtime_ns
    assert capsys.readouterr().err == "evidence_relation_audit: input_changed\n"
    assert not target.exists()


def test_hardlink_added_during_read_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "source.jsonl"
    source.write_bytes(FIXTURE.read_bytes())
    alias = tmp_path / "late-hardlink.jsonl"
    target = tmp_path / "report.json"
    triggered = False
    real_read = os.read

    def link_at_first_eof(fd: int, amount: int) -> bytes:
        nonlocal triggered
        part = real_read(fd, amount)
        if not part and not triggered:
            triggered = True
            os.link(source, alias)
        return part

    monkeypatch.setattr(cli.os, "read", link_at_first_eof)
    assert cli.main(["report", "--input", str(source), "--output", str(target)]) == 2
    assert triggered
    assert source.stat().st_nlink == 2
    assert capsys.readouterr().err == "evidence_relation_audit: input_changed\n"
    assert not target.exists()


def test_post_link_sync_failure_keeps_complete_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "report.json"
    real_fsync = cli.os.fsync
    calls = 0

    def fail_parent_sync(fd: int) -> None:
        nonlocal calls
        calls += 1
        if stat.S_ISDIR(os.fstat(fd).st_mode) and calls >= 2:
            raise OSError("synthetic")
        real_fsync(fd)

    monkeypatch.setattr(cli.os, "fsync", fail_parent_sync)
    with pytest.raises(ValueError, match="output_publication"):
        cli.write_report(target, b"complete\n")
    assert target.read_bytes() == b"complete\n"


def test_output_parent_must_be_owned_and_private(tmp_path: Path) -> None:
    parent = tmp_path / "wide"
    parent.mkdir(mode=0o777)
    parent.chmod(0o777)
    with pytest.raises(ValueError, match="unsafe_output_parent"):
        cli.write_report(parent / "report.json", b"safe\n")
    assert not (parent / "report.json").exists()


def test_validate_and_report_make_no_network_or_subprocess_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("external call")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    assert cli.main(["validate", "--input", str(FIXTURE)]) == 0
    assert (
        cli.main(["report", "--input", str(FIXTURE), "--output", str(tmp_path / "offline.json")])
        == 0
    )


def test_derived_report_reference_bound_is_explicit() -> None:
    rows = _basic_rows()
    world = rows[-1]
    context = world["context_ref"]
    assert isinstance(context, str)
    evidence_id = next(_asset_id(row) for row in rows[:-1] if row["use_kind"] == "evidence")
    link_ids: list[str] = []
    for index in range(501):
        identifier = f"L{index:03d}"
        link_ids.append(identifier)
        link: dict[str, object] = {
            "kind": "epistemic_link",
            "id": identifier,
            "claim_ref": "C1",
            "evidence_ref": evidence_id,
            "relation": "contradicted_by",
            "context_ref": context,
            "time_scope": "T1",
            "attribution": "actor-1",
            "produced_at": "2026-01-01T00:00:00+00:00",
            "source_fingerprint": "sha256:" + "0" * 64,
            "revision_of_ref": None,
        }
        _seal(link)
        rows.append(link)
    world["epistemic_link_refs"] = link_ids
    _seal(world)
    for index in range(100):
        duplicate = deepcopy(world)
        duplicate["id"] = f"W{index:03d}"
        _seal(duplicate)
        rows.append(duplicate)
    with pytest.raises(ValueError, match="report_limit"):
        audit_snapshot(parse_snapshot(rows))
