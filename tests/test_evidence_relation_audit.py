"""Offline JSONL and publication boundaries for NOOS-1A."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
from typing import Iterator, NoReturn, cast
import shlex

import pytest

from core.evidence.fingerprints import (
    JsonValue,
    build_asset_id,
    build_idempotency_key,
    fingerprint_payload,
)
from core.evidence.relations import audit_snapshot, parse_snapshot
from core.evidence import federation as fed
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


def test_rewrite_after_second_read_with_restored_mtime_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "source.jsonl"
    source.write_bytes(FIXTURE.read_bytes())
    target = tmp_path / "report.json"
    original = source.read_bytes()
    initial = source.stat()
    changed = bytearray(original)
    changed[0] = ord("[")
    eof_count = 0
    real_read = os.read

    def rewrite_after_second_eof(fd: int, amount: int) -> bytes:
        nonlocal eof_count
        part = real_read(fd, amount)
        if not part:
            eof_count += 1
            if eof_count == 2:
                with source.open("r+b") as stream:
                    stream.write(changed)
                os.utime(source, ns=(initial.st_atime_ns, initial.st_mtime_ns))
        return part

    monkeypatch.setattr(cli.os, "read", rewrite_after_second_eof)
    assert cli.main(["report", "--input", str(source), "--output", str(target)]) == 2
    assert eof_count == 2
    assert source.read_bytes() == bytes(changed)
    assert source.stat().st_mtime_ns == initial.st_mtime_ns
    assert source.stat().st_ctime_ns != initial.st_ctime_ns
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


INSPECT_CONTEXT = "evidence:eval_run:advisory:v1:e5e0c649bcb2f8dac2ed3218"


def _inspect_args(
    source: Path,
    target: Path,
    *,
    claim: str = "C2",
    period: str = "T1",
) -> list[str]:
    return [
        "inspect",
        "--input",
        str(source),
        "--output",
        str(target),
        "--claim-ref",
        claim,
        "--context-ref",
        INSPECT_CONTEXT,
        "--time-scope",
        period,
    ]


@pytest.mark.parametrize(
    "claim,period,state,links,assertions",
    [
        ("missing", "T1", "claim_absent", [], []),
        ("C2", "T2", "scope_absent", [], []),
        ("C1", "T1", "no_epistemic_links", [], [f"W{index}" for index in range(1, 8)]),
        ("C2", "T1", "present", ["L1"], ["W8"]),
    ],
)
def test_inspect_returns_complete_fixture_only_neighborhood(
    tmp_path: Path,
    claim: str,
    period: str,
    state: str,
    links: list[str],
    assertions: list[str],
) -> None:
    source = tmp_path / "fixture.jsonl"
    source.write_bytes(FIXTURE.read_bytes())
    before = source.read_bytes()
    target = tmp_path / "neighborhood.json"
    assert cli.main(_inspect_args(source, target, claim=claim, period=period)) == 0
    material = json.loads(target.read_bytes())
    assert material["lookup_state"] == state
    assert [item["record"]["id"] for item in material["main"]["links"]] == links
    assert [item["record"]["id"] for item in material["main"]["assertions"]] == assertions
    assert [
        item["record"]["assertion_id"] for item in material["main"]["assessments"]
    ] == assertions
    assert material["history"] == {"links": [], "assertions": [], "assessments": []}
    assert material["input_fingerprint"] == (
        "sha256:d63e6eeb0bfb3d0acb230852e4be5f4f94fc7914f1202e4eaddfac7cb53db39f"
    )
    if state == "present":
        expected_assets = {
            row["asset"]["asset_id"]
            for row in map(json.loads, before.splitlines())
            if row["kind"] == "asset"
        }
        assert {item["ref"]["local_id"] for item in material["assets"]} == expected_assets
        assert {item["ref"]["local_id"] for item in material["upstream_refs"]} == expected_assets
        assessment = material["main"]["assessments"][0]
        assert assessment["unresolved_link_refs"] == [material["main"]["links"][0]["ref"]]
        assert assessment["record"]["causal_structural_pass"] is False
    assert material["complete_for_supplied_inventory"] is True
    assert material["authority_granted"] is False
    assert material["answer_change_allowed"] is False
    assert source.read_bytes() == before
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    second = tmp_path / "second.json"
    assert cli.main(_inspect_args(source, second, claim=claim, period=period)) == 0
    assert second.read_bytes() == target.read_bytes()


@pytest.mark.parametrize(
    "bad",
    [
        b'{"kind":"asset","kind":"world_relation"}\n',
        b"\xff\n",
        b"\xef\xbb\xbf{}\n",
        b"{} {}\n",
        b"{}\n\n",
        b"[" * 34 + b"]" * 34 + b"\n",
        b"x" * (cli.MAX_LINE_BYTES + 1),
    ],
)
def test_inspect_bad_json_uses_existing_reader_and_cannot_publish(
    tmp_path: Path,
    bad: bytes,
) -> None:
    source = tmp_path / "bad.jsonl"
    source.write_bytes(bad)
    target = tmp_path / "out.json"
    assert cli.main(_inspect_args(source, target)) == 2
    assert not target.exists()


def test_inspect_preserves_input_alias_output_and_private_parent_boundaries(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jsonl"
    source.write_bytes(FIXTURE.read_bytes())
    target = tmp_path / "existing.json"
    target.write_bytes(b"preserved")
    assert cli.main(_inspect_args(source, target)) == 2
    assert target.read_bytes() == b"preserved"
    alias = tmp_path / "alias.jsonl"
    alias.symlink_to(source)
    assert cli.main(_inspect_args(alias, tmp_path / "symlink-result.json")) == 2
    alias.unlink()
    os.link(source, alias)
    assert cli.main(_inspect_args(source, tmp_path / "hardlink-result.json")) == 2
    alias.unlink()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(tmp_path, target_is_directory=True)
    assert cli.main(_inspect_args(source, linked_parent / "result.json")) == 2
    wide = tmp_path / "wide"
    wide.mkdir()
    wide.chmod(0o777)
    assert cli.main(_inspect_args(source, wide / "result.json")) == 2
    pipe = tmp_path / "pipe"
    os.mkfifo(pipe)
    assert cli.main(_inspect_args(pipe, tmp_path / "pipe-result.json")) == 2
    assert source.read_bytes() == FIXTURE.read_bytes()
    assert not list(tmp_path.glob(".noos1a-*.tmp"))


@pytest.mark.parametrize("mutation", ["first-eof", "second-eof", "late-hardlink"])
def test_inspect_reuses_input_race_checks(
    tmp_path: Path,
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.jsonl"
    source.write_bytes(FIXTURE.read_bytes())
    initial = source.stat()
    target = tmp_path / "out.json"
    real_read = cli.os.read
    eof_count = 0

    def change_on_eof(fd: int, count: int) -> bytes:
        nonlocal eof_count
        data = real_read(fd, count)
        if not data:
            eof_count += 1
            if eof_count == (2 if mutation == "second-eof" else 1):
                if mutation == "late-hardlink":
                    os.link(source, tmp_path / "late-alias")
                else:
                    changed = bytearray(source.read_bytes())
                    changed[0] = ord("[")
                    with source.open("r+b") as stream:
                        stream.write(changed)
                    os.utime(source, ns=(initial.st_atime_ns, initial.st_mtime_ns))
        return data

    monkeypatch.setattr(cli.os, "read", change_on_eof)
    assert cli.main(_inspect_args(source, target)) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "evidence_relation_audit: input_changed\n"
    assert not target.exists()


def test_inspect_post_link_error_retains_complete_bytes_without_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "retained.json"
    expected = cli._inspect_bytes(
        cli.read_jsonl(FIXTURE), claim_ref="C2", context_ref=INSPECT_CONTEXT, time_scope="T1"
    )
    real_fsync = cli.os.fsync

    def fail_directory(fd: int) -> None:
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("synthetic")
        real_fsync(fd)

    monkeypatch.setattr(cli.os, "fsync", fail_directory)
    assert cli.main(_inspect_args(FIXTURE, target)) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "evidence_relation_audit: output_publication\n"
    assert target.read_bytes() == expected


@pytest.mark.parametrize(
    "case,subparser_error",
    [
        ("unknown-option", False),
        ("extra-positional", False),
        ("missing-input", True),
        ("missing-output", True),
        ("missing-claim-ref", True),
        ("missing-context-ref", True),
        ("missing-time-scope", True),
        ("missing-value", True),
    ],
)
@pytest.mark.parametrize("native_argv", [False, True])
def test_selected_inspect_argument_errors_are_fixed_before_io(
    tmp_path: Path,
    case: str,
    subparser_error: bool,
    native_argv: bool,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "existing.json"
    target.write_bytes(b"preserved")
    args = _inspect_args(FIXTURE, target)
    if case == "unknown-option":
        args += ["--unknown", "/private/customer-marker"]
    elif case == "extra-positional":
        args += ["ghp_SYNTHETIC_NOT_A_CREDENTIAL"]
    elif case == "missing-value":
        args = args[:-1]
    else:
        field = "--" + case.removeprefix("missing-")
        index = args.index(field)
        del args[index : index + 2]
    origins: list[bool] = []
    real_error = cli._InspectArgumentParser.error

    def observe_error(parser: cli._InspectArgumentParser, message: str) -> NoReturn:
        origins.append(parser.prog.endswith(" inspect"))
        real_error(parser, message)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("argument failure reached I/O or external activity")

    monkeypatch.setattr(cli._InspectArgumentParser, "error", observe_error)
    monkeypatch.setattr(cli, "read_jsonl", forbidden)
    monkeypatch.setattr(cli, "write_report", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(cli.sys, "argv", ["synthetic-program", *args])
    assert cli.main(None if native_argv else args) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "evidence_relation_audit: argument_error\n"
    assert origins == [subparser_error]
    assert target.read_bytes() == b"preserved"


@pytest.mark.parametrize(
    "args", [["--help"], ["inspect", "--help"], ["validate", "--help"], ["report", "--help"]]
)
def test_native_help_is_retained(args: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stopped:
        cli.main(args)
    assert stopped.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert captured.err == ""


def test_unselected_legacy_argument_error_remains_native(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as stopped:
        cli.main(["validate", "--input", str(FIXTURE), "--unknown", "synthetic-legacy-value"])
    assert stopped.value.code == 2
    assert "synthetic-legacy-value" in capsys.readouterr().err


def test_inspect_invalid_query_and_output_limit_are_content_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "out.json"
    assert cli.main(_inspect_args(FIXTURE, target, claim=" C2")) == 2
    assert capsys.readouterr().err == "evidence_relation_audit: schema_value\n"
    rows = cli.read_jsonl(FIXTURE)
    monkeypatch.setattr(cli, "MAX_BYTES", 1)
    with pytest.raises(ValueError, match="^report_limit$"):
        cli._inspect_bytes(rows, claim_ref="C2", context_ref=INSPECT_CONTEXT, time_scope="T1")
    assert not target.exists()


def test_inspect_has_no_network_or_subprocess_activity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("external activity")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    assert cli.main(_inspect_args(FIXTURE, tmp_path / "offline-inspect.json")) == 0


def test_inspect_positive_fanout_budget_rejects_before_material_and_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = _basic_rows()
    world = rows[-1]
    evidence = next(_asset_id(row) for row in rows[:-1] if row["use_kind"] == "evidence")
    identifiers = [f"P{index:02d}" for index in range(16)]
    for identifier in identifiers:
        link: dict[str, object] = {
            "kind": "epistemic_link",
            "id": identifier,
            "claim_ref": "C1",
            "evidence_ref": evidence,
            "relation": "supported_by",
            "context_ref": world["context_ref"],
            "time_scope": "T1",
            "attribution": "actor-1",
            "produced_at": "2026-01-01T00:00:00+00:00",
            "source_fingerprint": "sha256:" + "0" * 64,
            "revision_of_ref": None,
        }
        _seal(link)
        rows.append(link)
    world["epistemic_link_refs"] = identifiers
    _seal(world)
    duplicate = deepcopy(world)
    duplicate["id"] = "W-repeat"
    _seal(duplicate)
    rows.append(duplicate)
    assert all(
        not item.unresolved_link_refs for item in audit_snapshot(parse_snapshot(rows)).assessments
    )
    source = tmp_path / "positive-fanout.jsonl"
    _write(source, rows)
    target = tmp_path / "unpublished.json"

    def forbidden(*_args: object, **_kwargs: object) -> NoReturn:
        raise AssertionError("derived material or publication reached")

    monkeypatch.setattr(fed, "MAX_DERIVED_BYTES", 1, raising=False)
    monkeypatch.setattr(fed, "_projection_material", forbidden)
    monkeypatch.setattr(cli, "write_report", forbidden)
    assert cli.main(_inspect_args(source, target, claim="missing")) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "evidence_relation_audit: report_limit\n"
    assert not target.exists()


def test_inspect_retains_original_fixture_canonical_bytes() -> None:
    data = cli._inspect_bytes(
        cli.read_jsonl(FIXTURE), claim_ref="C2", context_ref=INSPECT_CONTEXT, time_scope="T1"
    )
    assert len(data) == 8309
    assert f"sha256:{hashlib.sha256(data).hexdigest()}" == (
        "sha256:d5c54b50b78cf1221963bca1f4f0cbe42708b496014564544e6fee44ed111f26"
    )


def test_inspect_final_encoding_stops_before_overflowing_chunk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = cli.read_jsonl(FIXTURE)
    real_iterencode = json.JSONEncoder.iterencode
    final_chunks: list[str] = []

    def observe(
        encoder: json.JSONEncoder,
        value: object,
        _one_shot: bool = False,
    ) -> Iterator[str]:
        for part in real_iterencode(encoder, value, _one_shot):
            if not _one_shot:
                final_chunks.append(part)
            yield part

    monkeypatch.setattr(json.JSONEncoder, "iterencode", observe)
    monkeypatch.setattr(cli, "MAX_BYTES", 1)
    with pytest.raises(ValueError, match="^report_limit$"):
        cli._inspect_bytes(rows, claim_ref="C2", context_ref=INSPECT_CONTEXT, time_scope="T1")
    assert final_chunks == ["{"]


def test_source_inspect_usage_is_one_copyable_logical_command(tmp_path: Path) -> None:
    source_lines = Path(cast(str, cli.__file__)).read_text(encoding="utf-8").splitlines()
    first = next(
        index
        for index, line in enumerate(source_lines)
        if "python -m scripts.evals.evidence_relation_audit inspect" in line
    )
    assert source_lines[first].endswith("\\")
    assert cli.__doc__ is not None
    assert next(line for line in cli.__doc__.splitlines() if " inspect " in line).endswith("\\")
    command = shlex.split(source_lines[first][:-1] + source_lines[first + 1])
    assert command[:3] == ["python", "-m", "scripts.evals.evidence_relation_audit"]
    replacements = {
        "SNAPSHOT.jsonl": str(FIXTURE),
        "CLAIM": "C2",
        "CONTEXT": INSPECT_CONTEXT,
        "PERIOD": "T1",
        "REPORT.json": str(tmp_path / "copied-usage.json"),
    }
    assert cli.main([replacements.get(value, value) for value in command[3:]]) == 0


@pytest.mark.parametrize("width", [52, 120])
def test_rendered_root_help_inspect_command_executes_at_two_widths(
    width: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("COLUMNS", str(width))
    monkeypatch.setattr(cli.sys, "argv", ["evidence_relation_audit.py", "--help"])
    with pytest.raises(SystemExit) as stopped:
        cli.main()
    assert stopped.value.code == 0
    rendered = capsys.readouterr()
    assert rendered.err == ""
    help_lines = rendered.out.splitlines()
    first = next(
        index
        for index, line in enumerate(help_lines)
        if line.strip().startswith("python -m scripts.evals.evidence_relation_audit inspect")
    )
    assert help_lines[first].endswith("\\")
    assert help_lines[first + 1].strip().startswith("--claim-ref CLAIM")
    assert help_lines[first + 1].endswith("REPORT.json")
    assert help_lines[first + 2] == ""
    assert help_lines[first + 3].startswith("Limits:")
    command = shlex.split(help_lines[first][:-1] + help_lines[first + 1])
    assert command[:3] == ["python", "-m", "scripts.evals.evidence_relation_audit"]
    target = tmp_path / "rendered-help-report.json"
    replacements = {
        "SNAPSHOT.jsonl": str(FIXTURE),
        "CLAIM": "C2",
        "CONTEXT": INSPECT_CONTEXT,
        "PERIOD": "T1",
        "REPORT.json": str(target),
    }
    assert cli.main([replacements.get(value, value) for value in command[3:]]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == "evidence_relation_audit: neighborhood published\n"
    assert len(target.read_bytes()) == 8309
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
