"""Synthetic complete-inventory, bounded observation and private-file regressions."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import cast

import pytest
from scripts.ops import resource_cost_report as cost
from scripts.ops import resource_evidence_report as evidence

T = "2026-10-06T11:00:00Z"
A = "a" * 64


def cost_bytes(
    *,
    rows: list[dict[str, object]] | None = None,
    bindings: list[dict[str, object]] | None = None,
    total: str = "1.00",
) -> bytes:
    capture = {
        "schema_version": cost.CAPTURE_SCHEMA,
        "account_ref": "synthetic-account",
        "captured_at": T,
        "invoice_kind": "final",
        "invoice": {
            "invoice_uuid": "00000000-0000-4000-8000-000000000001",
            "invoice_period": "2026-09",
            "amount": total,
        },
        "pages": [
            {
                "page": 1,
                "per_page": 200,
                "response": {
                    "invoice_items": (
                        rows
                        if rows is not None
                        else [{"product": "Droplets", "resource_id": "d1", "amount": total}]
                    ),
                    "meta": {"total": len(rows) if rows is not None else 1},
                },
            }
        ],
    }
    binding = {
        "schema_version": cost.BINDING_SCHEMA,
        "account_ref": "synthetic-account",
        "bindings": bindings or [],
    }
    return cost.render_report(
        cost.attach_resource_context(cost.reconcile_invoice(capture), binding),
        cost._canonical(capture),
        cost._canonical(binding),
    )


def declaration(**changes: object) -> dict[str, object]:
    return {
        "resource_kind": "droplet",
        "resource_id": "d1",
        "environment": "staging",
        "service": "app",
        "owner_ref": "synthetic-owner",
        "evidence_ref": "synthetic",
        "recovery_ref": None,
        "utilization_ref": None,
        **changes,
    }


def record(kind: str = "metric", **changes: object) -> dict[str, object]:
    return {
        "record_kind": kind,
        "account_ref": "synthetic-account",
        "resource_kind": "droplet",
        "resource_id": "d1",
        "source_ref": "synthetic-source",
        "source_sha256": A,
        "acquisition_window": {"started_at": T, "completed_at": T},
        "observation_window": {"started_at": T, "completed_at": T},
        "topology_ref": "epoch1",
        "target": {"kind": "droplet", "ref": "d1"},
        "availability": "observed",
        "reason_code": None,
        "data": {
            "name": "memory.available",
            "unit": "kB",
            "cadence_seconds": None,
            "samples": [{"observed_at": T, "value": 0}],
        },
        **changes,
    }


def observations(raw: bytes, records: list[dict[str, object]] | None = None) -> dict[str, object]:
    report = json.loads(raw)
    return {
        "schema_version": evidence.OBSERVATIONS_SCHEMA,
        "policy_version": evidence.POLICY,
        "asset_type": "resource_observations",
        "cost_report_sha256": hashlib.sha256(raw).hexdigest(),
        "cost_report_fingerprint": report["report_fingerprint"],
        "account_ref": "synthetic-account",
        "assessment_at": "2026-10-06T12:00:00Z",
        "assessment_window": {
            "started_at": "2026-09-29T00:00:00Z",
            "completed_at": "2026-10-06T00:00:00Z",
        },
        "selected_resource": {"resource_kind": "droplet", "resource_id": "d1"},
        "declarations": [declaration()],
        "topology": {
            "epoch_ref": "epoch1",
            "root_filesystem_ref": "fs1",
            "volume_ids": ["v1"],
            "filesystem_volume_links": [],
        },
        "restore_expectations": [],
        "records": records if records is not None else [record()],
    }


def run(raw: bytes, obj: dict[str, object]) -> dict[str, object]:
    return evidence.assess(
        evidence.validate_cost(cost._parse(raw)),
        evidence.validate_observations(cost._parse(cost._canonical(obj))),
        raw,
    )


def rehash(report: dict[str, object]) -> bytes:
    report.pop("report_fingerprint", None)
    report["report_fingerprint"] = hashlib.sha256(cost._canonical(report)).hexdigest()
    return cost._canonical(report) + b"\n"


def test_current_zero_preserves_inventory_history_and_replay() -> None:
    raw = cost_bytes()
    obj = observations(raw)
    before = copy.deepcopy(obj)
    result = run(raw, obj)
    assert result["cost_inventory"] == json.loads(raw)
    assert result["conflicts"] == []
    entry = result["evidence"][0]
    assert entry["status"] == "observed"
    assert entry["record"]["data"]["samples"][0]["value"] == 0
    assert "REQUESTED_HISTORY_INCOMPLETE" in entry["reasons"]
    assert "CURRENT_OUTSIDE_REQUESTED_HISTORY" in entry["reasons"]
    assert obj == before
    rendered = evidence.render_report(result, raw, cost._canonical(obj))
    assert rendered == evidence.render_report(run(raw, obj), raw, cost._canonical(obj))
    parsed = json.loads(rendered)
    assert evidence.render_report(parsed, raw, cost._canonical(obj)) == rendered
    fingerprint = parsed.pop("report_fingerprint")
    assert fingerprint == hashlib.sha256(cost._canonical(parsed)).hexdigest()
    assert all(parsed[key] == value for key, value in evidence.AUTHORITY.items())


@pytest.mark.parametrize("field", ["cost_report_sha256", "cost_report_fingerprint", "account_ref"])
def test_foreign_report_or_account_does_not_join(field: str) -> None:
    raw = cost_bytes()
    obj = observations(raw)
    obj[field] = A if field != "account_ref" else "other-account"
    result = run(raw, obj)
    assert result["conflicts"]
    assert all(x["association"] == "unmatched" for x in result["evidence"])


@pytest.mark.parametrize(
    "changes",
    [
        {"resource_kind": "snapshot"},
        {"account_ref": "foreign"},
        {"target": {"kind": "droplet", "ref": "other"}},
        {"topology_ref": "old"},
    ],
)
def test_record_identity_epoch_conflicts(changes: dict[str, object]) -> None:
    raw = cost_bytes()
    result = run(raw, observations(raw, [record(**changes)]))
    assert result["conflicts"] and result["evidence"][0]["status"] == "conflict"


def test_other_member_retains_record_relative_identity_without_selected_conclusion() -> None:
    raw = cost_bytes(
        rows=[
            {"product": "Droplets", "resource_id": "d1", "amount": "0.50"},
            {"product": "Droplets", "resource_id": "d2", "amount": "0.50"},
        ]
    )
    result = run(
        raw, observations(raw, [record(resource_id="d2", target={"kind": "droplet", "ref": "d2"})])
    )
    assert result["conflicts"] == [] and result["evidence"][0]["association"] == "unmatched"
    assert len(result["question_inventory"]) == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("row_count", 2),
        ("total", "2.00"),
        ("page_count", False),
        ("invoice_kind", []),
        ("allocation_status", {}),
        ("mutation_authority", 0),
        ("accounting_status", {}),
        ("idempotency_key", A),
    ],
)
def test_valid_self_hash_cannot_hide_malformed_cost(field: str, value: object) -> None:
    report = json.loads(cost_bytes())
    report[field] = value
    with pytest.raises(cost.ReportError):
        evidence.validate_cost(cost._parse(rehash(report)))


def test_forged_allocation_and_unused_or_wrong_groups_refused() -> None:
    for mutate in (
        lambda r: r["rows"][0].update(bucket="allocated"),
        lambda r: r["resource_groups"][0].update(resource_kind="snapshot"),
        lambda r: r["rows"][0].update(group_ref="g2"),
        lambda r: r["rows"][0].update(ordinal=2),
    ):
        report = json.loads(cost_bytes())
        mutate(report)
        with pytest.raises(cost.ReportError):
            evidence.validate_cost(cost._parse(rehash(report)))


def test_old_long_money_references_cancellation_and_reference_conflicts_preserved() -> None:
    total = "1" + "0" * 600 + ".00"
    first = declaration(evidence_ref="x" * 700)
    second = declaration(evidence_ref="y" * 700)
    raw = cost_bytes(total=total, bindings=[first, second])
    result = run(raw, observations(raw))
    assert "ORIGINAL_BINDING_CONFLICT" in result["conflicts"]
    assert result["cost_inventory"] == json.loads(raw)
    rows = [
        {"product": "Droplets", "resource_id": "d1", "amount": "-1.00"},
        {"product": "Droplets", "resource_id": "d1", "amount": "1.00"},
        {"product": "Taxes", "amount": "0.00"},
        {"amount": "0.00"},
    ]
    raw = cost_bytes(rows=rows, total="0.00")
    assert len(run(raw, observations(raw))["cost_inventory"]["rows"]) == 4


def test_inconsistent_cost_preserves_source_error_without_refusal() -> None:
    raw = cost_bytes(rows=[{"product": "Droplets", "resource_id": "d1", "amount": "0.50"}])
    result = run(raw, observations(raw))
    assert "COST_ACCOUNTING_CONFLICT" in result["conflicts"]
    assert result["cost_inventory"]["residual"] == "0.50"


@pytest.mark.parametrize(
    "case,reason",
    [
        ("absent", "SAMPLES_ABSENT"),
        ("null", "SAMPLES_NULL"),
        ("empty", "SAMPLES_EMPTY"),
        ("all_null", "SAMPLES_ALL_NULL"),
    ],
)
def test_missing_null_empty_distinct(case: str, reason: str) -> None:
    raw = cost_bytes()
    r = record()
    data = cast(dict[str, object], r["data"])
    if case == "absent":
        data.pop("samples")
    else:
        data["samples"] = (
            None
            if case == "null"
            else [] if case == "empty" else [{"observed_at": T, "value": None}]
        )
    entry = run(raw, observations(raw, [r]))["evidence"][0]
    assert entry["status"] == "missing" and reason in entry["reasons"]


@pytest.mark.parametrize(
    "name,unit,value",
    [
        ("new.metric", "widgets", 0),
        ("new.metric", "widgets", 257),
        ("memory.total", "bytes", 0),
        ("memory.total", "bytes", 257),
        ("pressure.cpu.full.avg10", "percent", "0.00"),
        ("pressure.cpu.full.avg10", "percent", "12.375"),
    ],
)
def test_unsupported_metric_preserves_values(name: str, unit: str, value: int | str) -> None:
    raw = cost_bytes()
    r = record()
    r["data"] = {
        "name": name,
        "unit": unit,
        "cadence_seconds": None,
        "samples": [{"observed_at": T, "value": value}],
    }
    entry = run(raw, observations(raw, [r]))["evidence"][0]
    assert entry["status"] == "unsupported"
    preserved = entry["record"]["data"]["samples"][0]["value"]
    assert preserved == value and type(preserved) is type(value)


@pytest.mark.parametrize(
    "name,target,resource_kind,resource_id",
    [("memory.total", "volume", "volume", "v1"), ("filesystem.size", "droplet", "droplet", "d1")],
)
def test_wrong_target_conflicts_even_with_unsupported_unit(
    name: str, target: str, resource_kind: str, resource_id: str
) -> None:
    raw = cost_bytes()
    r = record(
        resource_kind=resource_kind,
        resource_id=resource_id,
        target={"kind": target, "ref": resource_id},
    )
    r["data"] = {"name": name, "unit": "wrong", "cadence_seconds": None, "samples": []}
    assert "METRIC_TARGET_CONFLICT" in run(raw, observations(raw, [r]))["conflicts"]


@pytest.mark.parametrize("value", [True, 1.2, "NaN", "1e9", "-1", "1" * 65, [], {}])
def test_invalid_values_in_unselected_record_rejected(value: object) -> None:
    raw = cost_bytes()
    r = record(resource_id="other", target={"kind": "droplet", "ref": "other"})
    r["data"]["samples"][0]["value"] = value
    with pytest.raises(cost.ReportError):
        evidence.validate_observations(cost._parse(cost._canonical(observations(raw, [r]))))


@pytest.mark.parametrize(
    "timestamp", ["2026-10-06T13:00:00Z", "2026-10-06T10:00:00Z", "2026-10-06T11:00:00.000001Z"]
)
def test_readable_sample_chronology_is_conflict(timestamp: str) -> None:
    raw = cost_bytes()
    r = record()
    r["data"]["samples"][0]["observed_at"] = timestamp
    assert run(raw, observations(raw, [r]))["conflicts"]


def test_finer_than_microsecond_timestamp_is_malformed() -> None:
    raw = cost_bytes()
    obj = observations(raw)
    obj["assessment_at"] = "2026-10-06T12:00:00.0000001Z"
    with pytest.raises(cost.ReportError):
        evidence.validate_observations(obj)


def test_metadata_span_cannot_replace_missing_history() -> None:
    raw = cost_bytes()
    r = record()
    r["observation_window"] = {"started_at": "2026-09-29T00:00:00Z", "completed_at": T}
    r["data"]["cadence_seconds"] = "5"
    assert (
        "REQUESTED_HISTORY_INCOMPLETE" in run(raw, observations(raw, [r]))["evidence"][0]["reasons"]
    )


def identity(backup_ids: object = None, **changes: object) -> dict[str, object]:
    return record(
        "identity",
        **{
            "data": {"root_filesystem_ref": "fs1", "volume_ids": ["v1"], "backup_ids": backup_ids},
            **changes,
        },
    )


def backup(**changes: object) -> dict[str, object]:
    return record(
        "backup_object",
        **{
            "data": {
                "object_kind": "backup",
                "object_id": "b1",
                "created_at": "2026-10-01T00:00:00Z",
                "status": "available",
                "membership_ids": ["b1"],
            },
            **changes,
        },
    )


@pytest.mark.parametrize(
    "membership,status",
    [(None, "observed"), ([], "conflict"), (["b1"], "observed"), (["b2"], "conflict")],
)
def test_backup_membership_requires_independent_identity(membership: object, status: str) -> None:
    raw = cost_bytes()
    result = run(raw, observations(raw, [identity(membership), backup()]))
    entry = result["evidence"][1]
    assert entry["status"] == status
    if membership is None:
        assert "BACKUP_MEMBERSHIP_MISSING" in entry["reasons"]
    assert "RESTORE_RECEIPT_MISSING" in result["gaps"]


def test_policy_listing_and_backup_never_manufacture_restore() -> None:
    raw = cost_bytes()
    policy = record("backup_policy", data={"enabled": True, "plan": "weekly"})
    listing = record(
        "archive_listing", data={"artifact_sha256": A, "listed_at": T, "entry_count": 1}
    )
    result = run(raw, observations(raw, [policy, listing, backup()]))
    assert "RESTORE_RECEIPT_MISSING" in result["gaps"]
    assert "FILESYSTEM_VOLUME_WITNESS_MISSING" in result["gaps"]


def restore(**changes: object) -> dict[str, object]:
    return record(
        "restore_receipt",
        data={
            "artifact_sha256": A,
            "target_ref": "synthetic-restore-db",
            "performed_at": T,
            "result": "succeeded",
            "checks": ["synthetic-row-check"],
        },
        **changes,
    )


def test_receipt_result_is_supplied_and_current_applicability_gaps_remain() -> None:
    raw = cost_bytes()
    r = restore(topology_ref=None, acquisition_window=None)
    r["data"]["checks"] = []
    entry = run(raw, observations(raw, [r]))["evidence"][0]
    assert entry["record"]["data"]["result"] == "succeeded"
    assert set(entry["reasons"]) >= {
        "CURRENT_ARTIFACT_MISSING",
        "TOPOLOGY_EPOCH_MISSING",
        "RESTORE_CHECKS_MISSING",
        "ACQUISITION_TIME_MISSING",
        "RESTORE_OUTSIDE_ASSESSMENT_WINDOW",
    }
    assert entry["status"] == "stale"


def test_exact_current_receipt_and_artifact_mismatch() -> None:
    raw = cost_bytes()
    r = restore()
    obj = observations(raw, [r])
    obj["assessment_window"] = {"started_at": T, "completed_at": "2026-10-06T11:01:00Z"}
    obj["restore_expectations"] = [
        {"target": r["target"], "artifact_sha256": A, "target_ref": "synthetic-restore-db"}
    ]
    assert run(raw, obj)["evidence"][0]["reasons"] == []
    obj["restore_expectations"][0]["artifact_sha256"] = "b" * 64
    assert "RESTORE_ARTIFACT_CONFLICT" in run(raw, obj)["conflicts"]


def test_permission_denied_preserves_unavailable_attempt() -> None:
    raw = cost_bytes()
    r = record(
        "archive_listing",
        availability="unavailable",
        reason_code="PERMISSION_DENIED",
        data=None,
        target={"kind": "filesystem", "ref": "datafs"},
    )
    entry = run(raw, observations(raw, [r]))["evidence"][0]
    assert entry["status"] == "missing" and "PERMISSION_DENIED" in entry["reasons"]
    assert "FILESYSTEM_VOLUME_WITNESS_MISSING" in entry["reasons"]


def test_topology_null_empty_conflicting_projections_and_links() -> None:
    raw = cost_bytes()
    assert not run(raw, observations(raw, [identity(), identity()]))["conflicts"]
    assert (
        "IDENTITY_TOPOLOGY_CONFLICT"
        in run(
            raw,
            observations(
                raw,
                [
                    identity(),
                    identity(
                        ["b1"],
                        data={
                            "root_filesystem_ref": "other",
                            "volume_ids": [],
                            "backup_ids": ["b1"],
                        },
                    ),
                ],
            ),
        )["conflicts"]
    )
    obj = observations(raw)
    obj["topology"]["filesystem_volume_links"] = [
        {
            "filesystem_ref": "datafs",
            "volume_id": "missing",
            "source_ref": "synthetic",
            "source_sha256": A,
        }
    ]
    assert "STORAGE_LINK_CONFLICT" in run(raw, obj)["conflicts"]


@pytest.fixture
def private_root(tmp_path: Path) -> Path:
    tmp_path.chmod(0o700)
    return tmp_path


def invoke(
    root: Path, raw: bytes, obj: dict[str, object], capsys: pytest.CaptureFixture[str]
) -> tuple[int, dict[str, object]]:
    for name, data in (("cost.json", raw), ("observations.json", cost._canonical(obj))):
        (root / name).write_bytes(data)
        (root / name).chmod(0o600)
    status = evidence.main(
        [
            "--input-dir",
            str(root),
            "--cost-report",
            "cost.json",
            "--observations",
            "observations.json",
            "--format",
            "json",
        ]
    )
    capture = capsys.readouterr()
    assert capture.err == ""
    return status, json.loads(capture.out)


def test_real_private_cli_success_conflict_error(
    private_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    raw = cost_bytes()
    obj = observations(raw)
    assert invoke(private_root, raw, obj, capsys)[0] == 0
    obj["account_ref"] = "private-foreign-account"
    assert invoke(private_root, raw, obj, capsys)[0] == 1
    obj["assessment_at"] = "private-invalid-time"
    status, result = invoke(private_root, raw, obj, capsys)
    assert status == 2 and result == {"error": "INVALID_INPUT", **evidence.AUTHORITY}


@pytest.mark.parametrize(
    "case",
    ["symlink", "hardlink", "permissions", "root_permissions", "fifo", "traversal", "directory"],
)
def test_actual_private_file_rejections(
    private_root: Path, capsys: pytest.CaptureFixture[str], case: str
) -> None:
    raw = cost_bytes()
    invoke(private_root, raw, observations(raw), capsys)
    leaf = private_root / "observations.json"
    name = "observations.json"
    if case == "symlink":
        leaf.rename(private_root / "other.json")
        leaf.symlink_to(private_root / "other.json")
    elif case == "hardlink":
        os.link(leaf, private_root / "other.json")
    elif case == "permissions":
        leaf.chmod(0o644)
    elif case == "root_permissions":
        private_root.chmod(0o755)
    elif case == "fifo":
        leaf.unlink()
        os.mkfifo(leaf)
    elif case == "directory":
        leaf.unlink()
        leaf.mkdir()
    else:
        name = "../observations.json"
    status = evidence.main(
        [
            "--input-dir",
            str(private_root),
            "--cost-report",
            "cost.json",
            "--observations",
            name,
            "--format",
            "json",
        ]
    )
    assert status == 2 and json.loads(capsys.readouterr().out) == {
        "error": "INVALID_INPUT",
        **evidence.AUTHORITY,
    }


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}',
        b'{"a":NaN}',
        b'{"a":Infinity}',
        b"\xff",
        b"{",
        b'{"a":' + b"[" * 10 + b"0" + b"]" * 10 + b"}",
    ],
)
def test_bad_json_refused(raw: bytes) -> None:
    with pytest.raises(cost.ReportError):
        cost._parse(raw)


def test_collection_text_decimal_and_total_sample_bounds() -> None:
    raw = cost_bytes()
    obj = observations(raw, [record()] * evidence.MAX_RECORDS)
    evidence.validate_observations(obj)
    obj["records"].append(record())
    with pytest.raises(cost.ReportError):
        evidence.validate_observations(obj)
    obj = observations(raw)
    obj["account_ref"] = "x" * 512
    evidence.validate_observations(obj)
    obj["account_ref"] += "x"
    with pytest.raises(cost.ReportError):
        evidence.validate_observations(obj)
    r = record()
    r["data"]["samples"] = [{"observed_at": T, "value": 0}] * 4000
    evidence.validate_observations(observations(raw, [r]))
    with pytest.raises(cost.ReportError):
        evidence.validate_observations(observations(raw, [r, record()]))
    assert evidence._decimal("1" * 64) > 0
    with pytest.raises(cost.ReportError):
        evidence._decimal("1" * 65)


def test_inert_references_and_standalone_import(private_root: Path) -> None:
    raw = cost_bytes()
    obj = observations(raw)
    obj["records"][0]["source_ref"] = "https://example.invalid/; $(touch forbidden)"
    for name, data in (("cost.json", raw), ("observations.json", cost._canonical(obj))):
        (private_root / name).write_bytes(data)
        (private_root / name).chmod(0o600)
    script = Path(evidence.__file__).resolve()
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(private_root),
            "--cost-report",
            "cost.json",
            "--observations",
            "observations.json",
            "--format",
            "json",
        ],
        cwd=private_root,
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not (private_root / "forbidden").exists()
    assert json.loads(result.stdout)["authority"] == "none"


def test_allocated_missing_identity_unclassified_and_foreign_binding_cost_projections() -> None:
    raw = cost_bytes(bindings=[declaration()])
    assert evidence.validate_cost(cost._parse(raw))["rows"][0]["bucket"] == "allocated"
    rows = [
        {"product": "Droplets", "amount": "0.00"},
        {"product": "Droplets", "resource_id": "x", "resource_uuid": "y", "amount": "0.00"},
        {"product": "Taxes", "resource_id": "x", "amount": "0.00"},
        {"amount": "0.00"},
    ]
    raw = cost_bytes(rows=rows, total="0.00")
    assert evidence.validate_cost(cost._parse(raw))["row_count"] == 4
    raw = cost_bytes(bindings=[declaration(resource_id="other")])
    assert len(evidence.validate_cost(cost._parse(raw))["unresolved_bindings"]) == 1
    raw = cost_bytes(rows=[], total="0.00")
    assert "SELECTED_RESOURCE_CONFLICT" in run(raw, observations(raw))["conflicts"]


@pytest.mark.parametrize("payload", [None, {}, [], True, 1, "not-object"])
def test_complete_inputs_reject_wrong_root_types(payload: object) -> None:
    for validator in (evidence.validate_cost, evidence.validate_observations):
        with pytest.raises(cost.ReportError):
            validator(payload)


@pytest.mark.parametrize("field", sorted(evidence.COST_KEYS))
def test_every_cost_field_is_typed_before_self_hash(field: str) -> None:
    report = json.loads(cost_bytes())
    report[field] = {}
    with pytest.raises(cost.ReportError):
        evidence.validate_cost(report)


@pytest.mark.parametrize(
    "kind,data",
    [
        ("identity", {"root_filesystem_ref": None, "volume_ids": None, "backup_ids": None}),
        (
            "metric",
            {
                "name": "cpu.user",
                "unit": "USER_HZ",
                "cadence_seconds": "5",
                "samples": [{"observed_at": T, "value": 1}],
            },
        ),
        (
            "metric",
            {
                "name": "pressure.io.some.avg10",
                "unit": "percent",
                "cadence_seconds": None,
                "samples": [{"observed_at": T, "value": "0.05"}],
            },
        ),
        (
            "metric",
            {
                "name": "pressure.memory.full.total",
                "unit": "microseconds",
                "cadence_seconds": None,
                "samples": [{"observed_at": T, "value": 10}],
            },
        ),
        ("backup_policy", {"enabled": False, "plan": "daily"}),
        (
            "backup_object",
            {
                "object_kind": "snapshot",
                "object_id": "s1",
                "created_at": T,
                "status": "unknown",
                "membership_ids": None,
            },
        ),
        ("archive_listing", {"artifact_sha256": A, "listed_at": T, "entry_count": 0}),
        (
            "restore_receipt",
            {
                "artifact_sha256": A,
                "target_ref": "synthetic-target",
                "performed_at": T,
                "result": "failed",
                "checks": [],
            },
        ),
    ],
)
def test_supported_record_grammar_and_semantic_boundaries(
    kind: str, data: dict[str, object]
) -> None:
    raw = cost_bytes()
    result = run(raw, observations(raw, [record(kind, data=data)]))
    assert result["conflicts"] == []
    assert result["evidence"][0]["record"]["data"] == data
    assert result["evidence"][0]["applicability"] != "compatible_supplied_scope"


@pytest.mark.parametrize(
    "kind,data,field,bad",
    [
        (
            "identity",
            {"root_filesystem_ref": None, "volume_ids": [], "backup_ids": []},
            "root_filesystem_ref",
            0,
        ),
        (
            "identity",
            {"root_filesystem_ref": None, "volume_ids": [], "backup_ids": []},
            "volume_ids",
            ["v1", "v1"],
        ),
        ("metric", {"name": "memory.total", "unit": "kB", "cadence_seconds": None}, "name", []),
        (
            "metric",
            {"name": "memory.total", "unit": "kB", "cadence_seconds": None},
            "cadence_seconds",
            "0",
        ),
        (
            "metric",
            {"name": "memory.total", "unit": "kB", "cadence_seconds": None},
            "samples",
            True,
        ),
        ("backup_policy", {"enabled": True, "plan": "weekly"}, "enabled", 1),
        ("backup_policy", {"enabled": True, "plan": "weekly"}, "plan", []),
        (
            "backup_object",
            {
                "object_kind": "backup",
                "object_id": "b1",
                "created_at": T,
                "status": "available",
                "membership_ids": [],
            },
            "created_at",
            "bad",
        ),
        (
            "archive_listing",
            {"artifact_sha256": A, "listed_at": T, "entry_count": 1},
            "entry_count",
            False,
        ),
        (
            "restore_receipt",
            {
                "artifact_sha256": A,
                "target_ref": "synthetic",
                "performed_at": T,
                "result": "succeeded",
                "checks": [],
            },
            "checks",
            [{}],
        ),
    ],
)
def test_unselected_payload_schema_cannot_hide_invalid_fields(
    kind: str, data: dict[str, object], field: str, bad: object
) -> None:
    raw = cost_bytes()
    data = dict(data)
    data[field] = bad
    with pytest.raises(cost.ReportError):
        evidence.validate_observations(
            observations(
                raw,
                [
                    record(
                        kind,
                        resource_id="other",
                        target={"kind": "droplet", "ref": "other"},
                        data=data,
                    )
                ],
            )
        )


@pytest.mark.parametrize(
    "field",
    [
        "record_kind",
        "account_ref",
        "resource_kind",
        "resource_id",
        "source_ref",
        "source_sha256",
        "acquisition_window",
        "observation_window",
        "topology_ref",
        "target",
        "availability",
        "reason_code",
        "data",
    ],
)
def test_every_record_field_typed_before_association(field: str) -> None:
    raw = cost_bytes()
    r = record()
    r[field] = []
    with pytest.raises(cost.ReportError):
        evidence.validate_observations(observations(raw, [r]))


def test_missing_acquisition_sources_and_observations_preserved() -> None:
    raw = cost_bytes(
        rows=[
            {"product": "Droplets", "resource_id": "d1", "amount": "1.00"},
            {"product": "Volumes", "resource_uuid": "v1", "amount": "0.00"},
        ]
    )
    r = record(
        "restore_receipt",
        availability="not_acquired",
        reason_code="RECEIPT_NOT_ACQUIRED",
        data=None,
        source_ref=None,
        source_sha256=None,
        acquisition_window=None,
        observation_window=None,
        resource_kind="volume",
        resource_id="v1",
        target={"kind": "volume", "ref": "v1"},
    )
    result = run(raw, observations(raw, [identity(), r]))
    assert result["evidence"][1]["status"] == "missing"
    assert set(result["evidence"][1]["reasons"]) >= {
        "RECEIPT_NOT_ACQUIRED",
        "ACQUISITION_TIME_MISSING",
        "OBSERVATION_TIME_MISSING",
        "FILESYSTEM_VOLUME_WITNESS_MISSING",
    }


def test_missing_owner_and_all_records_no_metrics_preserve_questions() -> None:
    raw = cost_bytes()
    obj = observations(raw, [])
    obj["declarations"] = []
    result = run(raw, obj)
    assert set(result["gaps"]) >= {
        "OWNER_SERVICE_MISSING",
        "UTILIZATION_MISSING",
        "RESTORE_RECEIPT_MISSING",
    }
    obj["declarations"] = [declaration(), declaration(owner_ref="different")]
    assert "DECLARATION_CONFLICT" in run(raw, obj)["conflicts"]


def test_known_partial_native_identities_merge_and_member_order_not_conflict() -> None:
    raw = cost_bytes()
    provider = identity(
        ["b1", "b2"],
        data={"root_filesystem_ref": None, "volume_ids": ["v1"], "backup_ids": ["b1", "b2"]},
    )
    host = identity(data={"root_filesystem_ref": "fs1", "volume_ids": None, "backup_ids": None})
    obj = observations(
        raw,
        [
            provider,
            host,
            backup(
                data={
                    "object_kind": "backup",
                    "object_id": "b1",
                    "created_at": T,
                    "status": "available",
                    "membership_ids": ["b2", "b1"],
                }
            ),
        ],
    )
    assert run(raw, obj)["conflicts"] == []


@pytest.mark.parametrize(
    "target", [{"kind": "root_filesystem", "ref": "fs1"}, {"kind": "filesystem", "ref": "datafs"}]
)
def test_filesystem_metrics_preserve_separate_identity_and_link_gaps(
    target: dict[str, str],
) -> None:
    raw = cost_bytes()
    r = record(
        target=target,
        data={
            "name": "filesystem.available",
            "unit": "bytes",
            "cadence_seconds": None,
            "samples": [{"observed_at": T, "value": 0}],
        },
    )
    obj = observations(raw, [r])
    entry = run(raw, obj)["evidence"][0]
    assert entry["status"] == "observed"
    if target["kind"] == "filesystem":
        assert "FILESYSTEM_VOLUME_WITNESS_MISSING" in entry["reasons"]
    obj["topology"]["root_filesystem_ref"] = None
    assert run(raw, obj)["conflicts"] == []


@pytest.mark.parametrize("field", ["acquisition_window", "observation_window", "assessment_window"])
def test_readable_window_order_future_conflict(field: str) -> None:
    raw = cost_bytes()
    obj = observations(raw)
    window = {"started_at": "2026-10-07T11:00:00Z", "completed_at": T}
    if field == "assessment_window":
        obj[field] = window
    else:
        obj["records"][0][field] = window
    assert run(raw, obj)["conflicts"]


def test_internal_sample_gap_stale_and_ordered_bounds_are_independent() -> None:
    raw = cost_bytes()
    r = record()
    r["data"]["cadence_seconds"] = "5"
    r["data"]["samples"] = [
        {"observed_at": "2026-09-01T00:00:00Z", "value": 1},
        {"observed_at": "2026-09-01T00:01:00Z", "value": 2},
    ]
    r["observation_window"] = {
        "started_at": "2026-09-01T00:00:00Z",
        "completed_at": "2026-09-01T00:01:00Z",
    }
    entry = run(raw, observations(raw, [r]))["evidence"][0]
    assert entry["status"] == "stale" and "INTERNAL_SAMPLE_GAP" in entry["reasons"]
    r["data"]["samples"].reverse()
    assert "SAMPLE_ORDER_CONFLICT" in run(raw, observations(raw, [r]))["conflicts"]


def test_conflicting_restore_expectations_and_links_select_no_winner() -> None:
    raw = cost_bytes()
    obj = observations(raw, [restore()])
    target = {"kind": "droplet", "ref": "d1"}
    obj["restore_expectations"] = [
        {"target": target, "artifact_sha256": A, "target_ref": "synthetic-restore-db"},
        {"target": target, "artifact_sha256": "b" * 64, "target_ref": "synthetic-restore-db"},
    ]
    assert "RESTORE_EXPECTATION_CONFLICT" in run(raw, obj)["conflicts"]
    obj["topology"]["volume_ids"].append("v2")
    obj["topology"]["filesystem_volume_links"] = [
        {"filesystem_ref": "datafs", "volume_id": v, "source_ref": "synthetic", "source_sha256": A}
        for v in ("v1", "v2")
    ]
    assert "STORAGE_LINK_CONFLICT" in run(raw, obj)["conflicts"]


def test_recovery_on_wrong_kind_and_root_mismatch_conflicts() -> None:
    raw = cost_bytes()
    r = record(
        "backup_policy",
        resource_kind="volume",
        resource_id="v1",
        target={"kind": "volume", "ref": "v1"},
        data={"enabled": True, "plan": "weekly"},
    )
    assert "TARGET_KIND_CONFLICT" in run(raw, observations(raw, [r]))["conflicts"]
    r = record(
        target={"kind": "root_filesystem", "ref": "other"},
        data={"name": "filesystem.size", "unit": "bytes", "cadence_seconds": None, "samples": []},
    )
    assert "ROOT_FILESYSTEM_CONFLICT" in run(raw, observations(raw, [r]))["conflicts"]


def test_constant_argument_refusal_and_read_error(
    private_root: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert evidence.main(["--unknown", "private-value"]) == 2
    assert json.loads(capsys.readouterr().out) == {"error": "INVALID_INPUT", **evidence.AUTHORITY}

    def fail(*args: object) -> tuple[bytes, bytes]:
        raise OSError("private-value")

    monkeypatch.setattr(cost, "_read_inputs", fail)
    assert (
        evidence.main(
            [
                "--input-dir",
                str(private_root),
                "--cost-report",
                "x",
                "--observations",
                "y",
                "--format",
                "json",
            ]
        )
        == 2
    )
    capture = capsys.readouterr()
    assert "private-value" not in capture.out + capture.err


def test_real_byte_limit_and_unsafe_nested_parents(
    private_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    raw = cost_bytes()
    invoke(private_root, raw, observations(raw), capsys)
    path = private_root / "observations.json"
    path.write_bytes(b" " * (cost.MAX_BYTES + 1))
    assert (
        evidence.main(
            [
                "--input-dir",
                str(private_root),
                "--cost-report",
                "cost.json",
                "--observations",
                "observations.json",
                "--format",
                "json",
            ]
        )
        == 2
    )
    capsys.readouterr()
    outside = private_root / "nested"
    outside.mkdir(mode=0o755)
    assert (
        evidence.main(
            [
                "--input-dir",
                str(private_root),
                "--cost-report",
                "cost.json",
                "--observations",
                "nested/file.json",
                "--format",
                "json",
            ]
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out) == {"error": "INVALID_INPUT", **evidence.AUTHORITY}


def test_question_inventory_does_not_reask_known_context_and_preserves_unidentified_rows() -> None:
    rows = [
        {"product": "Droplets", "resource_id": "d1", "amount": "1.00"},
        {"product": "Droplets", "amount": "0.00"},
        {"amount": "0.00"},
        {"product": "Taxes", "amount": "0.00"},
        {"product": "Droplets", "resource_id": "x", "resource_uuid": "y", "amount": "0.00"},
    ]
    raw = cost_bytes(rows=rows)
    result = run(raw, observations(raw))
    inventory = result["question_inventory"]
    group = inventory[0]
    assert group["context_status"] == "supplied"
    assert not set(group["questions"]) & {
        "identity",
        "owner_declaration",
        "service_declaration",
        "environment_declaration",
        "dated_utilization",
    }
    assert "representative_utilization_history" in group["questions"]
    assert [(r["page"], r["ordinal"], r["questions"]) for r in inventory[1:]] == [
        (1, 2, ["native_resource_identity"]),
        (1, 3, ["product_identity"]),
        (1, 5, ["resolve_native_identity"]),
    ]


def test_cost_member_volume_has_related_storage_without_filesystem_inference() -> None:
    raw = cost_bytes(
        rows=[
            {"product": "Droplets", "resource_id": "d1", "amount": "1.00"},
            {"product": "Volumes", "resource_uuid": "v1", "amount": "0.00"},
        ]
    )
    r = record(
        "restore_receipt",
        resource_kind="volume",
        resource_id="v1",
        target={"kind": "volume", "ref": "v1"},
        availability="not_acquired",
        reason_code="RECEIPT_NOT_ACQUIRED",
        source_ref=None,
        source_sha256=None,
        data=None,
    )
    result = run(raw, observations(raw, [identity(), r]))
    assert result["evidence"][1]["association"] == "related_storage"
    assert result["evidence"][1]["status"] == "missing"
    group = result["question_inventory"][1]
    assert group["related_storage"] and "filesystem_volume_identity_witness" in group["questions"]
    assert "FILESYSTEM_VOLUME_WITNESS_MISSING" in result["evidence"][1]["reasons"]
    # The expected topology list alone is not an independently observed attachment.
    result = run(raw, observations(raw, [r]))
    assert result["evidence"][0]["association"] == "unmatched"


def test_question_inventory_retains_original_reference_only_conflict() -> None:
    raw = cost_bytes(
        bindings=[declaration(evidence_ref="first"), declaration(evidence_ref="second")]
    )
    questions = run(raw, observations(raw))["question_inventory"][0]["questions"]
    assert "resolve_context_conflict" in questions and "resolve_evidence_binding" in questions
    assert "owner_declaration" not in questions


def test_foreign_report_declaration_cannot_fill_known_context() -> None:
    raw = cost_bytes()
    obj = observations(raw)
    obj["cost_report_sha256"] = A
    group = run(raw, obj)["question_inventory"][0]
    assert group["context_status"] == "missing"
    assert {"owner_declaration", "service_declaration"} <= set(group["questions"])


def test_original_binding_account_mismatch_remains_readable() -> None:
    capture = {
        "schema_version": cost.CAPTURE_SCHEMA,
        "account_ref": "synthetic-account",
        "captured_at": T,
        "invoice_kind": "final",
        "invoice": {
            "invoice_uuid": "00000000-0000-4000-8000-000000000001",
            "invoice_period": "2026-09",
            "amount": "1.00",
        },
        "pages": [
            {
                "page": 1,
                "per_page": 200,
                "response": {
                    "invoice_items": [
                        {"product": "Droplets", "resource_id": "d1", "amount": "1.00"}
                    ],
                    "meta": {"total": 1},
                },
            }
        ],
    }
    bindings = {
        "schema_version": cost.BINDING_SCHEMA,
        "account_ref": "foreign",
        "bindings": [declaration()],
    }
    report = cost.attach_resource_context(cost.reconcile_invoice(capture), bindings)
    raw = cost.render_report(report, cost._canonical(capture), cost._canonical(bindings))
    assert "COST_ACCOUNTING_CONFLICT" in run(raw, observations(raw))["conflicts"]


@pytest.mark.parametrize(
    "changes",
    [
        {
            "acquisition_window": {
                "started_at": "2026-10-06T10:00:00Z",
                "completed_at": "2026-10-06T10:01:00Z",
            }
        },
        {
            "resource_kind": "volume",
            "resource_id": "v1",
            "target": {"kind": "volume", "ref": "other"},
        },
        {
            "resource_kind": "volume",
            "resource_id": "v1",
            "target": {"kind": "filesystem", "ref": "datafs"},
        },
    ],
)
def test_readable_acquisition_and_generic_storage_conflicts(changes: dict[str, object]) -> None:
    raw = cost_bytes()
    assert run(raw, observations(raw, [record(**changes)]))["conflicts"]


def test_single_incompatible_identity_and_retained_missing_source_hash() -> None:
    raw = cost_bytes()
    r = identity(data={"root_filesystem_ref": "other", "volume_ids": ["v1"], "backup_ids": None})
    assert "IDENTITY_TOPOLOGY_CONFLICT" in run(raw, observations(raw, [r]))["conflicts"]
    r = record("metric", availability="not_acquired", reason_code="HISTORY_NOT_ACQUIRED", data=None)
    assert run(raw, observations(raw, [r]))["evidence"][0]["status"] == "missing"


def test_self_hashed_cost_cannot_exceed_original_total_binding_budget() -> None:
    report = json.loads(cost_bytes(bindings=[declaration()] * cost.MAX_BINDINGS))
    evidence.validate_cost(cost._parse(cost._canonical(report)))
    report["unresolved_bindings"].append(declaration(resource_id="unmatched"))
    with pytest.raises(cost.ReportError):
        evidence.validate_cost(cost._parse(rehash(report)))


def test_self_hashed_unresolved_binding_cannot_duplicate_matched_identity() -> None:
    report = json.loads(cost_bytes())
    report["unresolved_bindings"].append(declaration())
    with pytest.raises(cost.ReportError):
        evidence.validate_cost(cost._parse(rehash(report)))


def test_signed_zero_producer_report_keeps_original_values_and_bytes() -> None:
    raw = cost_bytes(total="-0.00")
    original = cost._parse(raw)
    assert {
        key: original[key]
        for key in ("header_total", "total", "residual", "errors", "accounting_status")
    } == {
        "header_total": "-0.00",
        "total": "0.00",
        "residual": "-0.00",
        "errors": [],
        "accounting_status": "reconciled",
    }
    validated = evidence.validate_cost(original)
    assert cost._canonical(validated) + b"\n" == raw
    result = run(raw, observations(raw))
    assert result["conflicts"] == [] and result["cost_inventory"] == original


def test_self_hashed_signed_zero_cannot_claim_reconciliation_mismatch() -> None:
    report = json.loads(cost_bytes(total="-0.00"))
    report["errors"] = ["RECONCILIATION_MISMATCH"]
    cost._totals(report)
    with pytest.raises(cost.ReportError):
        evidence.validate_cost(cost._parse(rehash(report)))


@pytest.mark.parametrize(
    "conflict", [None, "raw_cost_hash", "account", "epoch", "expectations", "unselected_record"]
)
def test_complete_receipt_applicability_requires_whole_context(conflict: str | None) -> None:
    raw = cost_bytes()
    receipt = restore()
    obj = observations(raw, [receipt])
    obj["assessment_window"] = {"started_at": T, "completed_at": "2026-10-06T11:01:00Z"}
    obj["restore_expectations"] = [
        {"target": receipt["target"], "artifact_sha256": A, "target_ref": "synthetic-restore-db"}
    ]
    if conflict == "raw_cost_hash":
        obj["cost_report_sha256"] = "b" * 64
    elif conflict == "account":
        obj["account_ref"] = "foreign-account"
    elif conflict == "epoch":
        obj["topology"]["epoch_ref"] = "other-epoch"
    elif conflict == "expectations":
        obj["restore_expectations"].append(
            {
                "target": receipt["target"],
                "artifact_sha256": "b" * 64,
                "target_ref": "synthetic-restore-db",
            }
        )
    elif conflict == "unselected_record":
        obj["records"].append(
            record(resource_id="other", target={"kind": "droplet", "ref": "wrong"})
        )
    result = run(raw, obj)
    entry = result["evidence"][0]
    assert entry["record"] == receipt
    assert entry["record"]["data"]["result"] == "succeeded"
    if conflict is None:
        assert result["conflicts"] == []
        assert (
            entry["association"],
            entry["status"],
            entry["applicability"],
            entry["reasons"],
        ) == ("selected", "observed", "compatible_supplied_scope", [])
    else:
        assert result["conflicts"]
        assert (entry["association"], entry["status"], entry["applicability"]) == (
            "unmatched",
            "conflict",
            "not_established",
        )
        assert "GLOBAL_CONTEXT_CONFLICT" in entry["reasons"]
        assert set(result["conflicts"]) <= set(entry["reasons"])
        assert all(
            item["applicability"] != "compatible_supplied_scope" for item in result["evidence"]
        )


@pytest.mark.parametrize(
    "row_pages,widths,page_count,valid",
    [
        ([2], [1], 2, False),
        ([1, 3], [1, 1], 3, False),
        ([1], [1], 2, False),
        ([1], [201], 1, False),
        ([1, 2, 3], [1, 2, 1], 3, False),
        ([], [], 2, False),
        ([1, 2], [1, 2], 2, False),
        ([1, 2], [201, 1], 2, False),
        ([1], [1], 1, True),
        ([1], [200], 1, True),
        ([1, 2], [2, 1], 2, True),
        ([1, 2, 3], [2, 2, 2], 3, True),
        ([1, 2], [200, 200], 2, True),
        ([], [], 1, True),
    ],
)
def test_complete_cost_projection_page_conservation(
    row_pages: list[int], widths: list[int], page_count: int, valid: bool
) -> None:
    report = json.loads(
        cost_bytes(
            rows=[{"product": "Droplets", "resource_id": "d1", "amount": "0.00"}] * sum(widths),
            total="0.00",
        )
    )
    report["errors"] = []
    report["page_count"] = page_count
    offset = 0
    for page, width in zip(row_pages, widths):
        for ordinal, row in enumerate(report["rows"][offset : offset + width], 1):
            row.update(page=page, ordinal=ordinal)
        offset += width
    cost._totals(report)
    raw = rehash(report)
    if valid:
        assert cost._canonical(evidence.validate_cost(cost._parse(raw))) + b"\n" == raw
    else:
        with pytest.raises(cost.ReportError, match="INVALID_INPUT"):
            evidence.validate_cost(cost._parse(raw))


def test_native_incomplete_empty_page_and_zero_inventory_preserved() -> None:
    capture = {
        "schema_version": cost.CAPTURE_SCHEMA,
        "account_ref": "synthetic-account",
        "captured_at": T,
        "invoice_kind": "final",
        "invoice": {
            "invoice_uuid": "00000000-0000-4000-8000-000000000001",
            "invoice_period": "2026-09",
            "amount": "0.00",
        },
        "pages": [
            {"page": 1, "per_page": 1, "response": {"invoice_items": [], "meta": {"total": 2}}},
            {
                "page": 2,
                "per_page": 1,
                "response": {
                    "invoice_items": [
                        {"product": "Droplets", "resource_id": "d1", "amount": "0.00"}
                    ],
                    "meta": {"total": 2},
                },
            },
        ],
    }
    bindings = {
        "schema_version": cost.BINDING_SCHEMA,
        "account_ref": "synthetic-account",
        "bindings": [],
    }
    raw = cost.render_report(
        cost.attach_resource_context(cost.reconcile_invoice(capture), bindings),
        cost._canonical(capture),
        cost._canonical(bindings),
    )
    validated = evidence.validate_cost(cost._parse(raw))
    assert validated["errors"] == ["INCOMPLETE_CAPTURE"]
    assert validated["rows"][0]["page"] == 2
    assert cost._canonical(validated) + b"\n" == raw
    result = run(raw, observations(raw))
    assert result["cost_inventory"] == validated
    assert "COST_ACCOUNTING_CONFLICT" in result["conflicts"]
    zero_raw = cost_bytes(rows=[], total="0.00")
    zero = evidence.validate_cost(cost._parse(zero_raw))
    assert zero["rows"] == [] and zero["page_count"] == 1 and zero["errors"] == []
    assert cost._canonical(zero) + b"\n" == zero_raw


@pytest.mark.parametrize("destination", ["missing", None, False, 257, "", "a\n", "x" * 513])
def test_restore_expectation_destination_is_required_bounded_literal(destination: object) -> None:
    raw = cost_bytes()
    obj = observations(raw, [restore()])
    expectation = {"target": {"kind": "droplet", "ref": "d1"}, "artifact_sha256": A}
    if destination != "missing":
        expectation["target_ref"] = destination
    obj["restore_expectations"] = [expectation]
    with pytest.raises(cost.ReportError, match="INVALID_INPUT"):
        evidence.validate_observations(obj)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    "conflict", [None, "receipt_destination", "expectation_destination", "artifact"]
)
def test_restore_destination_binding_and_global_revocation(
    conflict: str | None, reverse: bool
) -> None:
    raw = cost_bytes()
    first, second = restore(), restore()
    obj = observations(raw, [first, second])
    obj["assessment_window"] = {"started_at": T, "completed_at": "2026-10-06T11:01:00Z"}
    expectation = {
        "target": first["target"],
        "artifact_sha256": A,
        "target_ref": "synthetic-restore-db",
    }
    assert expectation["target_ref"] != first["target"]["ref"]
    obj["restore_expectations"] = [expectation, copy.deepcopy(expectation)]
    if conflict == "receipt_destination":
        second["data"]["target_ref"] = "other-isolated-destination"
    elif conflict == "expectation_destination":
        obj["restore_expectations"][1]["target_ref"] = "other-isolated-destination"
    elif conflict == "artifact":
        obj["restore_expectations"][1]["artifact_sha256"] = "b" * 64
    if reverse:
        obj["records"].reverse()
        obj["restore_expectations"].reverse()
    before = copy.deepcopy(obj)
    result = run(raw, obj)
    assert obj == before
    assert [entry["record"] for entry in result["evidence"]] == obj["records"]
    if conflict is None:
        assert result["conflicts"] == []
        assert all(
            entry["applicability"] == "compatible_supplied_scope" for entry in result["evidence"]
        )
    else:
        expected_reason = (
            "RESTORE_TARGET_CONFLICT"
            if conflict == "receipt_destination"
            else "RESTORE_EXPECTATION_CONFLICT"
        )
        assert expected_reason in result["conflicts"]
        assert all(
            (entry["association"], entry["status"], entry["applicability"])
            == ("unmatched", "conflict", "not_established")
            for entry in result["evidence"]
        )
