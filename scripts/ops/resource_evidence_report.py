#!/usr/bin/env python3
"""Assess supplied resource observations against a preserved cost report, offline."""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import re
import sys
from typing import cast

# Existing standalone-script bootstrap; loading remains an ordinary package import.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ops import resource_cost_report as cost

SCHEMA = "pulseplate.resource-evidence-report.v1"
OBSERVATIONS_SCHEMA = "pulseplate.resource-observations.v1"
POLICY = "resource-evidence-policy.v1"
ASSET = "resource_evidence_report"
MAX_RECORDS = 128
MAX_MEMBERS = 64
MAX_SAMPLES = 4000
MAX_TEXT = 512
MAX_DECIMAL = 64
SHA = re.compile(r"[0-9a-f]{64}\Z")
TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z")
DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
TARGETS = {"droplet", "root_filesystem", "filesystem", "volume"}
KINDS = {
    "identity",
    "metric",
    "backup_policy",
    "backup_object",
    "archive_listing",
    "restore_receipt",
}
AUTHORITY = {"authority": "none", "mutation_authority": False, "savings_verified": False}
COST_KEYS = {
    "schema_version",
    "policy_version",
    "asset_type",
    "account_ref",
    "captured_at",
    "invoice_kind",
    "invoice_period",
    "currency",
    "header_total",
    "header_observation_status",
    "rows",
    "resource_groups",
    "row_count",
    "declared_row_count",
    "page_count",
    "errors",
    "authority",
    "mutation_authority",
    "savings_verified",
    "unresolved_bindings",
    "total",
    "residual",
    "totals",
    "counts",
    "accounting_status",
    "allocation_status",
    "operator_summary",
    "upstream_assets",
    "idempotency_key",
    "report_fingerprint",
}
BINDING_KEYS = {
    "resource_kind",
    "resource_id",
    "environment",
    "service",
    "owner_ref",
    "evidence_ref",
    "recovery_ref",
    "utilization_ref",
}


def _text(value: object, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    result = cast(str, cost._text(value))
    cost._require(len(result) <= MAX_TEXT)
    return result


def _hash(value: object) -> str:
    text = cast(str, cost._text(value))
    cost._require(SHA.fullmatch(text) is not None)
    return text


def _integer(value: object, *, maximum: int | None = None) -> int:
    cost._require(type(value) is int)
    number = cast(int, value)
    cost._require(number >= 0 and (maximum is None or number <= maximum))
    return number


def _list(value: object, limit: int) -> list[object]:
    cost._require(isinstance(value, list) and len(value) <= limit)
    return cast(list[object], value)


def _members(value: object, *, nullable: bool = False) -> list[object] | None:
    if nullable and value is None:
        return None
    members = _list(value, MAX_MEMBERS)
    for item in members:
        _text(item)
    cost._require(len(set(cast(list[str], members))) == len(members))
    return members


def _time(value: object) -> datetime:
    text = cost._text(value)
    cost._require(TIME.fullmatch(text) is not None)
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _window(value: object, *, nullable: bool = False) -> tuple[datetime, datetime] | None:
    if nullable and value is None:
        return None
    obj = cost._keys(value, {"started_at", "completed_at"})
    return _time(obj["started_at"]), _time(obj["completed_at"])


def _decimal(value: object) -> Decimal:
    text = cost._text(value)
    cost._require(len(text) <= MAX_DECIMAL and DECIMAL.fullmatch(text) is not None)
    return Decimal(text)


def _binding(value: object, *, bounded: bool) -> dict[str, object]:
    obj = cost._keys(value, BINDING_KEYS)
    for key in ("resource_kind", "resource_id", "environment", "service"):
        (_text if bounded else cost._text)(obj[key])
    cost._require(obj["resource_kind"] in cost.KINDS)
    cost._require(obj["environment"] in {"production", "staging", "shared", "unknown"})
    cost._require(obj["service"] in {"app", "database", "prometheus", "packages", "unknown"})
    for key in ("owner_ref", "evidence_ref", "recovery_ref", "utilization_ref"):
        if obj[key] is not None:
            (_text if bounded else cost._text)(obj[key])
    return cast(dict[str, object], obj)


def validate_cost(value: object) -> dict[str, object]:
    """Validate the finite producer projection without reconstructing its source invoice."""
    report = cost._keys(value, COST_KEYS)
    cost._require(
        (report["schema_version"], report["policy_version"], report["asset_type"])
        == (cost.SCHEMA, cost.POLICY, cost.ASSET)
    )
    cost._require(report["authority"] == "none")
    for key in ("mutation_authority", "savings_verified"):
        cost._require(type(report[key]) is bool and report[key] is False)
    cost._text(report["account_ref"])
    cost._timestamp(report["captured_at"])
    cost._require(
        type(report["invoice_kind"]) is str and report["invoice_kind"] in {"preview", "final"}
    )
    cost._require(cost._PERIOD.fullmatch(cost._text(report["invoice_period"])) is not None)
    cost._require(report["currency"] == "USD")
    cost._require(
        type(report["header_observation_status"]) is str
        and report["header_observation_status"] in {"not_supplied", "unchanged", "changed"}
    )
    for key in ("header_total", "total", "residual"):
        cost._require(cost._money(cost._amount(report[key])) == report[key])
    row_count = _integer(report["row_count"], maximum=cost.MAX_ROWS)
    _integer(report["declared_row_count"], maximum=cost.MAX_ROWS)
    pages = _integer(report["page_count"], maximum=cost.MAX_PAGES)
    cost._require(pages > 0)
    errors = _list(report["errors"], 4)
    cost._require(all(type(error) is str for error in errors))
    cost._require(
        set(cast(list[str], errors))
        <= {"HEADER_CHANGED", "INCOMPLETE_CAPTURE", "RECONCILIATION_MISMATCH", "ACCOUNT_MISMATCH"}
        and errors == sorted(set(cast(list[str], errors)))
    )
    cost._require(
        (report["header_observation_status"] == "changed") == ("HEADER_CHANGED" in errors)
    )
    groups = _list(report["resource_groups"], cost.MAX_ROWS)
    group_index: dict[str, dict[str, object]] = {}
    identities: set[tuple[str, str]] = set()
    for index, raw in enumerate(groups, 1):
        group = cost._keys(
            raw,
            {
                "group_ref",
                "resource_kind",
                "resource_id",
                "context_status",
                "binding_candidates",
                "recovery_verification",
                "utilization_verification",
            },
        )
        ref = cost._text(group["group_ref"])
        kind, identity = cost._text(group["resource_kind"]), cost._text(group["resource_id"])
        cost._require(
            ref == f"g{index}" and kind in cost.KINDS and (kind, identity) not in identities
        )
        identities.add((kind, identity))
        candidates = [
            _binding(x, bounded=False)
            for x in _list(group["binding_candidates"], cost.MAX_BINDINGS)
        ]
        cost._require(
            all((x["resource_kind"], x["resource_id"]) == (kind, identity) for x in candidates)
        )
        expected = (
            "missing"
            if not candidates
            else "supplied" if all(x == candidates[0] for x in candidates) else "conflict"
        )
        cost._require(
            group["context_status"] == expected and group["recovery_verification"] == "not_assessed"
        )
        utilization = (
            "not_assessed"
            if candidates and candidates[0]["utilization_ref"] is not None
            else "unknown"
        )
        cost._require(group["utilization_verification"] == utilization)
        group_index[ref] = group
    unresolved = _list(report["unresolved_bindings"], cost.MAX_BINDINGS)
    cost._require(
        sum(len(cast(list[object], group["binding_candidates"])) for group in group_index.values())
        + len(unresolved)
        <= cost.MAX_BINDINGS
    )
    if "ACCOUNT_MISMATCH" in errors:
        cost._require(all(not group["binding_candidates"] for group in group_index.values()))
    for binding in unresolved:
        context = _binding(binding, bounded=False)
        cost._require(
            "ACCOUNT_MISMATCH" in errors
            or (context["resource_kind"], context["resource_id"]) not in identities
        )
    rows = _list(report["rows"], cost.MAX_ROWS)
    cost._require(len(rows) == row_count)
    cost._require(row_count == report["declared_row_count"] or "INCOMPLETE_CAPTURE" in errors)
    seen_groups: list[str] = []
    previous_page, previous_ordinal = 0, 0
    for raw in rows:
        row = cost._keys(
            raw, {"page", "ordinal", "amount", "product", "bucket", "identity_status", "group_ref"}
        )
        page, ordinal = _integer(row["page"]), _integer(row["ordinal"])
        cost._require(0 < page <= pages and ordinal > 0 and page >= previous_page)
        cost._require(ordinal == previous_ordinal + 1 if page == previous_page else ordinal == 1)
        previous_page, previous_ordinal = page, ordinal
        cost._require(cost._money(cost._amount(row["amount"])) == row["amount"])
        product, status, ref = row["product"], row["identity_status"], row["group_ref"]
        cost._require(
            product is None
            or type(product) is str
            and product in cost.PRODUCTS.keys() | cost.NON_RESOURCE
        )
        cost._require(
            type(status) is str
            and status in {"supplied", "missing", "conflict", "unrecognized", "not_applicable"}
        )
        cost._require(type(row["bucket"]) is str and row["bucket"] in cost.BUCKETS)
        if ref is not None:
            cost._require(type(ref) is str and ref in group_index)
            cost._require(product in cost.PRODUCTS and status == "supplied")
            group = group_index[cast(str, ref)]
            cost._require(cost.PRODUCTS[cast(str, product)][0] == group["resource_kind"])
            if ref not in seen_groups:
                seen_groups.append(cast(str, ref))
            candidates = cast(list[dict[str, object]], group["binding_candidates"])
            allocated = (
                group["context_status"] == "supplied"
                and candidates[0]["owner_ref"] is not None
                and candidates[0]["service"] != "unknown"
            )
            cost._require(row["bucket"] == ("allocated" if allocated else "unallocated"))
        else:
            expected_bucket = (
                "unallocated"
                if product in cost.PRODUCTS
                else (
                    "non_resource"
                    if product in cost.NON_RESOURCE and status == "not_applicable"
                    else "unclassified"
                )
            )
            cost._require(row["bucket"] == expected_bucket)
            allowed_statuses = (
                {"missing", "conflict"}
                if product in cost.PRODUCTS
                else (
                    {"unrecognized", "conflict", "not_applicable"}
                    if product in cost.NON_RESOURCE
                    else {"unrecognized", "conflict"}
                )
            )
            cost._require(status in allowed_statuses)
            cost._require(
                status != "supplied"
                and (status == "not_applicable") == (expected_bucket == "non_resource")
            )
    cost._require(seen_groups == list(group_index))
    for key in ("totals", "counts"):
        obj = cost._keys(report[key], set(cost.BUCKETS))
        for item in obj.values():
            if key == "counts":
                _integer(item, maximum=cost.MAX_ROWS)
            else:
                cost._require(cost._money(cost._amount(item)) == item)
    cost._require(
        type(report["accounting_status"]) is str
        and report["accounting_status"] in {"reconciled", "inconsistent"}
    )
    cost._require(
        type(report["allocation_status"]) is str
        and report["allocation_status"] in {"partial", "complete"}
    )
    summary = cost._keys(
        report["operator_summary"], {"accounting_status", "allocation_status", "next_question"}
    )
    for item in summary.values():
        cost._require(item is None or type(item) is str)
    derived = copy.deepcopy(report)
    cost._totals(derived)
    for key in (
        "total",
        "residual",
        "totals",
        "counts",
        "errors",
        "accounting_status",
        "allocation_status",
        "operator_summary",
    ):
        cost._require(derived[key] == report[key])
    cost._require((cost._amount(report["residual"]) != 0) == ("RECONCILIATION_MISMATCH" in errors))
    upstreams = _list(report["upstream_assets"], 2)
    cost._require(len(upstreams) == 2)
    hashes = []
    for raw, asset in zip(upstreams, ("invoice_capture", "resource_bindings")):
        upstream = cost._keys(raw, {"asset_type", "sha256"})
        cost._require(upstream["asset_type"] == asset)
        hashes.append(_hash(upstream["sha256"]))
    cost._require(
        _hash(report["idempotency_key"])
        == hashlib.sha256(
            cost._canonical([cost.ASSET, cost.SCHEMA, cost.POLICY, *hashes])
        ).hexdigest()
    )
    fingerprint = _hash(report["report_fingerprint"])
    projection = {key: item for key, item in report.items() if key != "report_fingerprint"}
    cost._require(fingerprint == hashlib.sha256(cost._canonical(projection)).hexdigest())
    return copy.deepcopy(report)


def _target(value: object) -> dict[str, object]:
    obj = cost._keys(value, {"kind", "ref"})
    cost._require(type(obj["kind"]) is str and obj["kind"] in TARGETS)
    _text(obj["ref"])
    return cast(dict[str, object], obj)


def _validate_record(value: object) -> dict[str, object]:
    record = cost._keys(
        value,
        {
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
        },
    )
    cost._require(type(record["record_kind"]) is str and record["record_kind"] in KINDS)
    cost._require(type(record["resource_kind"]) is str and record["resource_kind"] in cost.KINDS)
    for key in ("account_ref", "resource_id"):
        _text(record[key])
    _text(record["topology_ref"], nullable=True)
    _target(record["target"])
    _window(record["acquisition_window"], nullable=True)
    _window(record["observation_window"], nullable=True)
    availability = record["availability"]
    cost._require(
        type(availability) is str and availability in {"observed", "unavailable", "not_acquired"}
    )
    if availability == "not_acquired":
        _text(record["source_ref"], nullable=True)
        if record["source_sha256"] is not None:
            _hash(record["source_sha256"])
    else:
        _text(record["source_ref"])
        _hash(record["source_sha256"])
    if availability != "observed":
        cost._require(
            record["data"] is None
            and type(record["reason_code"]) is str
            and record["reason_code"]
            in {
                "PERMISSION_DENIED",
                "HISTORY_NOT_ACQUIRED",
                "RECEIPT_NOT_ACQUIRED",
                "SOURCE_NOT_ACQUIRED",
            }
        )
        return cast(dict[str, object], record)
    cost._require(record["reason_code"] is None)
    kind = record["record_kind"]
    if kind == "identity":
        data = cost._keys(record["data"], {"root_filesystem_ref", "volume_ids", "backup_ids"})
        _text(data["root_filesystem_ref"], nullable=True)
        _members(data["volume_ids"], nullable=True)
        _members(data["backup_ids"], nullable=True)
    elif kind == "metric":
        data = cost._keys(record["data"], {"name", "unit", "cadence_seconds"}, {"samples"})
        _text(data["name"])
        _text(data["unit"])
        if data["cadence_seconds"] is not None:
            cost._require(_decimal(data["cadence_seconds"]) > 0)
        if "samples" in data and data["samples"] is not None:
            for raw in _list(data["samples"], MAX_SAMPLES):
                sample = cost._keys(raw, {"observed_at", "value"})
                _time(sample["observed_at"])
                if sample["value"] is not None:
                    if type(sample["value"]) is int:
                        _integer(sample["value"])
                    else:
                        _decimal(sample["value"])
    elif kind == "backup_policy":
        data = cost._keys(record["data"], {"enabled", "plan"})
        cost._require(type(data["enabled"]) is bool)
        cost._require(type(data["plan"]) is str and data["plan"] in {"weekly", "daily", "unknown"})
    elif kind == "backup_object":
        data = cost._keys(
            record["data"], {"object_kind", "object_id", "created_at", "status", "membership_ids"}
        )
        cost._require(
            type(data["object_kind"]) is str and data["object_kind"] in {"backup", "snapshot"}
        )
        _text(data["object_id"])
        _time(data["created_at"])
        cost._require(
            type(data["status"]) is str
            and data["status"] in {"available", "unavailable", "unknown"}
        )
        _members(data["membership_ids"], nullable=True)
    elif kind == "archive_listing":
        data = cost._keys(record["data"], {"artifact_sha256", "listed_at", "entry_count"})
        _hash(data["artifact_sha256"])
        _time(data["listed_at"])
        _integer(data["entry_count"])
    else:
        data = cost._keys(
            record["data"], {"artifact_sha256", "target_ref", "performed_at", "result", "checks"}
        )
        _hash(data["artifact_sha256"])
        _text(data["target_ref"])
        _time(data["performed_at"])
        cost._require(
            type(data["result"]) is str and data["result"] in {"succeeded", "failed", "unknown"}
        )
        for item in _list(data["checks"], 32):
            _text(item)
    return cast(dict[str, object], record)


def validate_observations(value: object) -> dict[str, object]:
    obj = cost._keys(
        value,
        {
            "schema_version",
            "policy_version",
            "asset_type",
            "cost_report_sha256",
            "cost_report_fingerprint",
            "account_ref",
            "assessment_at",
            "assessment_window",
            "selected_resource",
            "declarations",
            "topology",
            "restore_expectations",
            "records",
        },
    )
    cost._require(
        (obj["schema_version"], obj["policy_version"], obj["asset_type"])
        == (OBSERVATIONS_SCHEMA, POLICY, "resource_observations")
    )
    for key in ("cost_report_sha256", "cost_report_fingerprint"):
        _hash(obj[key])
    _text(obj["account_ref"])
    _time(obj["assessment_at"])
    _window(obj["assessment_window"])
    selected = cost._keys(obj["selected_resource"], {"resource_kind", "resource_id"})
    cost._require(selected["resource_kind"] == "droplet")
    _text(selected["resource_id"])
    for declaration in _list(obj["declarations"], cost.MAX_BINDINGS):
        _binding(declaration, bounded=True)
    topology = cost._keys(
        obj["topology"],
        {"epoch_ref", "root_filesystem_ref", "volume_ids", "filesystem_volume_links"},
    )
    _text(topology["epoch_ref"], nullable=True)
    _text(topology["root_filesystem_ref"], nullable=True)
    _members(topology["volume_ids"])
    for raw in _list(topology["filesystem_volume_links"], MAX_MEMBERS):
        link = cost._keys(raw, {"filesystem_ref", "volume_id", "source_ref", "source_sha256"})
        for key in ("filesystem_ref", "volume_id", "source_ref"):
            _text(link[key])
        _hash(link["source_sha256"])
    for raw in _list(obj["restore_expectations"], MAX_MEMBERS):
        expectation = cost._keys(raw, {"target", "artifact_sha256"})
        _target(expectation["target"])
        _hash(expectation["artifact_sha256"])
    sample_count = 0
    for raw in _list(obj["records"], MAX_RECORDS):
        record = _validate_record(raw)
        if record["record_kind"] == "metric" and record["availability"] == "observed":
            samples = cost._object(record["data"]).get("samples")
            sample_count += len(samples) if isinstance(samples, list) else 0
    cost._require(sample_count <= MAX_SAMPLES)
    return copy.deepcopy(obj)


def _metric_spec(name: str) -> tuple[str, str] | None:
    if name in {
        "cpu." + column
        for column in (
            "user",
            "nice",
            "system",
            "idle",
            "iowait",
            "irq",
            "softirq",
            "steal",
            "guest",
            "guest_nice",
        )
    }:
        return "USER_HZ", "integer"
    if name in {"memory.available", "memory.total"}:
        return "kB", "integer"
    if name in {"filesystem.available", "filesystem.free", "filesystem.size"}:
        return "bytes", "integer"
    if re.fullmatch(r"pressure\.(cpu|memory|io)\.(some|full)\.(avg10|avg60|avg300|total)", name):
        return ("microseconds", "integer") if name.endswith(".total") else ("percent", "percent")
    return None


def _chronology(record: dict[str, object], assessment: datetime) -> list[str]:
    reasons = []
    acquisition = _window(record["acquisition_window"], nullable=True)
    observed = _window(record["observation_window"], nullable=True)
    for window in (acquisition, observed):
        if window is not None and (window[0] > window[1] or window[1] > assessment):
            reasons.append("CHRONOLOGY_CONFLICT")
    if observed and acquisition and observed[1] > acquisition[1]:
        reasons.append("CHRONOLOGY_CONFLICT")
    if record["availability"] != "observed":
        return reasons
    data = cost._object(record["data"])
    dates: list[datetime] = []
    if record["record_kind"] == "metric":
        samples = data.get("samples")
        dates = (
            [_time(cost._object(sample)["observed_at"]) for sample in samples]
            if isinstance(samples, list)
            else []
        )
        if any(first >= second for first, second in zip(dates, dates[1:])):
            reasons.append("SAMPLE_ORDER_CONFLICT")
    else:
        field = {
            "backup_object": "created_at",
            "archive_listing": "listed_at",
            "restore_receipt": "performed_at",
        }.get(cast(str, record["record_kind"]))
        if field:
            dates = [_time(data[field])]
    for date in dates:
        if date > assessment or acquisition and date > acquisition[1]:
            reasons.append("CHRONOLOGY_CONFLICT")
        if (
            observed
            and record["record_kind"] != "backup_object"
            and not observed[0] <= date <= observed[1]
        ):
            reasons.append("OBSERVATION_INTERVAL_CONFLICT")
    return reasons


def _target_reasons(record: dict[str, object]) -> list[str]:
    target = cost._object(record["target"])
    kind, identity = record["resource_kind"], record["resource_id"]
    reasons = []
    if target["kind"] == "droplet" and (kind != "droplet" or target["ref"] != identity):
        reasons.append("TARGET_IDENTITY_CONFLICT")
    if target["kind"] == "volume" and (kind != "volume" or target["ref"] != identity):
        reasons.append("TARGET_IDENTITY_CONFLICT")
    if target["kind"] in {"root_filesystem", "filesystem"} and kind != "droplet":
        reasons.append("TARGET_KIND_CONFLICT")
    if record["record_kind"] in {"identity", "backup_policy", "backup_object"} and (
        kind != "droplet" or target["kind"] not in {"droplet", "root_filesystem"}
    ):
        reasons.append("TARGET_KIND_CONFLICT")
    if record["record_kind"] == "metric" and record["availability"] == "observed":
        name = cast(str, cost._object(record["data"])["name"])
        if _metric_spec(name):
            allowed = (
                {"root_filesystem", "filesystem"} if name.startswith("filesystem.") else {"droplet"}
            )
            if target["kind"] not in allowed or kind != "droplet":
                reasons.append("METRIC_TARGET_CONFLICT")
    return reasons


def assess(
    report: dict[str, object], observations: dict[str, object], cost_raw: bytes
) -> dict[str, object]:
    """Join only validated supplied identities; every positive claim stays scoped."""
    selected = cost._object(observations["selected_resource"])
    topology = cost._object(observations["topology"])
    groups = cast(list[dict[str, object]], report["resource_groups"])
    chosen = [
        g
        for g in groups
        if (g["resource_kind"], g["resource_id"])
        == (selected["resource_kind"], selected["resource_id"])
    ]
    conflicts: list[str] = []
    if (
        observations["cost_report_sha256"] != hashlib.sha256(cost_raw).hexdigest()
        or observations["cost_report_fingerprint"] != report["report_fingerprint"]
    ):
        conflicts.append("COST_REPORT_BINDING_CONFLICT")
    if observations["account_ref"] != report["account_ref"]:
        conflicts.append("ACCOUNT_CONFLICT")
    if len(chosen) != 1:
        conflicts.append("SELECTED_RESOURCE_CONFLICT")
    if report["accounting_status"] != "reconciled":
        conflicts.append("COST_ACCOUNTING_CONFLICT")
    declarations = cast(list[dict[str, object]], observations["declarations"])
    binding_matches = not any(
        code in conflicts
        for code in (
            "COST_REPORT_BINDING_CONFLICT",
            "ACCOUNT_CONFLICT",
            "SELECTED_RESOURCE_CONFLICT",
        )
    )
    candidates = [
        d
        for d in declarations
        if (d["resource_kind"], d["resource_id"]) == ("droplet", selected["resource_id"])
        and binding_matches
    ]
    if chosen:
        original = cast(list[dict[str, object]], chosen[0]["binding_candidates"])
        if chosen[0]["context_status"] == "conflict":
            conflicts.append("ORIGINAL_BINDING_CONFLICT")
        candidates = original + candidates
    contexts = {(d["environment"], d["service"], d["owner_ref"]) for d in candidates}
    if len(contexts) > 1:
        conflicts.append("DECLARATION_CONFLICT")
    assessment = _time(observations["assessment_at"])
    history = cast(tuple[datetime, datetime], _window(observations["assessment_window"]))
    if not history[0] < history[1] <= assessment:
        conflicts.append("ASSESSMENT_WINDOW_CONFLICT")
    links = cast(list[dict[str, object]], topology["filesystem_volume_links"])
    for link in links:
        if link["volume_id"] not in topology["volume_ids"]:
            conflicts.append("STORAGE_LINK_CONFLICT")
    for filesystem in {link["filesystem_ref"] for link in links}:
        if len({link["volume_id"] for link in links if link["filesystem_ref"] == filesystem}) > 1:
            conflicts.append("STORAGE_LINK_CONFLICT")
    expectations = cast(list[dict[str, object]], observations["restore_expectations"])
    for target in {cost._canonical(e["target"]) for e in expectations}:
        if (
            len(
                {
                    e["artifact_sha256"]
                    for e in expectations
                    if cost._canonical(e["target"]) == target
                }
            )
            > 1
        ):
            conflicts.append("RESTORE_EXPECTATION_CONFLICT")
    records = cast(list[dict[str, object]], observations["records"])
    selected_identities = [
        r
        for r in records
        if r["record_kind"] == "identity"
        and r["availability"] == "observed"
        and (r["account_ref"], r["resource_kind"], r["resource_id"])
        == (report["account_ref"], "droplet", selected["resource_id"])
    ]
    backup_members: list[object] | None = None
    volume_members: list[object] | None = None
    for key in ("root_filesystem_ref", "volume_ids", "backup_ids"):
        known = [
            cost._object(r["data"])[key]
            for r in selected_identities
            if cost._object(r["data"])[key] is not None
        ]
        normalized = [set(item) if isinstance(item, list) else item for item in known]
        if known and any(item != normalized[0] for item in normalized):
            conflicts.append("IDENTITY_TOPOLOGY_CONFLICT")
        if key == "volume_ids" and known:
            volume_members = cast(list[object], known[0])
        if key == "backup_ids" and known:
            backup_members = cast(list[object], known[0])
        elif (
            known
            and topology[key] is not None
            and normalized[0]
            != (set(topology[key]) if isinstance(topology[key], list) else topology[key])
        ):
            conflicts.append("IDENTITY_TOPOLOGY_CONFLICT")
    related_volumes = (
        set(volume_members or [])
        & set(cast(list[str], topology["volume_ids"]))
        & {g["resource_id"] for g in groups if g["resource_kind"] == "volume"}
    )
    assessments: list[dict[str, object]] = []
    for record in records:
        reasons = _target_reasons(record) + _chronology(record, assessment)
        matched = (record["account_ref"], record["resource_kind"], record["resource_id"]) == (
            report["account_ref"],
            "droplet",
            selected["resource_id"],
        ) or (
            record["account_ref"] == report["account_ref"]
            and record["resource_kind"] == "volume"
            and record["resource_id"] in related_volumes
        )
        if record["account_ref"] != report["account_ref"]:
            reasons.append("ACCOUNT_CONFLICT")
        if not matched and record["resource_id"] == selected["resource_id"]:
            reasons.append("RESOURCE_KIND_CONFLICT")
        status = "observed" if matched else "unmatched"
        target = cost._object(record["target"])
        gaps: list[str] = []
        if matched:
            if (
                record["topology_ref"] is not None
                and topology["epoch_ref"] is not None
                and record["topology_ref"] != topology["epoch_ref"]
            ):
                reasons.append("TOPOLOGY_EPOCH_CONFLICT")
            elif record["topology_ref"] is None or topology["epoch_ref"] is None:
                gaps.append("TOPOLOGY_EPOCH_MISSING")
            if target["kind"] == "root_filesystem":
                if topology["root_filesystem_ref"] is None:
                    gaps.append("ROOT_FILESYSTEM_IDENTITY_MISSING")
                elif target["ref"] != topology["root_filesystem_ref"]:
                    reasons.append("ROOT_FILESYSTEM_CONFLICT")
            if (
                target["kind"] == "volume"
                and not any(link["volume_id"] == target["ref"] for link in links)
                or target["kind"] == "filesystem"
                and not any(link["filesystem_ref"] == target["ref"] for link in links)
            ):
                gaps.append("FILESYSTEM_VOLUME_WITNESS_MISSING")
        if record["acquisition_window"] is None:
            gaps.append("ACQUISITION_TIME_MISSING")
        if record["observation_window"] is None:
            gaps.append("OBSERVATION_TIME_MISSING")
        if record["availability"] != "observed":
            status = "missing" if matched else "unmatched"
            gaps.append(cast(str, record["reason_code"]))
        else:
            data = cost._object(record["data"])
            if record["record_kind"] == "metric":
                name = cast(str, data["name"])
                spec = _metric_spec(name)
                samples = data.get("samples")
                if spec and spec[0] == data["unit"] and isinstance(samples, list):
                    for sample in samples:
                        value = cost._object(sample)["value"]
                        if value is not None:
                            cost._require(
                                type(value) is int
                                if spec[1] == "integer"
                                else type(value) is str and _decimal(value) <= 100
                            )
                if not spec or spec[0] != data["unit"] or name.startswith("pressure.cpu.full."):
                    status = "unsupported" if matched else "unmatched"
                    gaps.append(
                        "SYSTEM_CPU_FULL_UNDEFINED"
                        if name.startswith("pressure.cpu.full.")
                        else "METRIC_UNSUPPORTED"
                    )
                elif (
                    samples is None
                    or not samples
                    or not any(
                        cost._object(s)["value"] is not None for s in cast(list[object], samples)
                    )
                ):
                    status = "missing" if matched else "unmatched"
                    gaps.append(
                        "SAMPLES_ABSENT"
                        if "samples" not in data
                        else (
                            "SAMPLES_NULL"
                            if samples is None
                            else "SAMPLES_EMPTY" if not samples else "SAMPLES_ALL_NULL"
                        )
                    )
                if isinstance(samples, list):
                    gaps.append("REPRESENTATIVE_WORKLOAD_NOT_ASSESSED")
                    if data["cadence_seconds"] is not None:
                        cadence = _decimal(data["cadence_seconds"])
                        moments = [_time(cost._object(sample)["observed_at"]) for sample in samples]
                        for first, second in zip(moments, moments[1:]):
                            delta = second - first
                            seconds = Decimal(delta.days * 86400 + delta.seconds) + Decimal(
                                delta.microseconds
                            ) / Decimal(1000000)
                            if seconds > cadence:
                                gaps.append("INTERNAL_SAMPLE_GAP")
                                gaps.append("REQUESTED_HISTORY_INCOMPLETE")
                    usable = [
                        _time(cost._object(s)["observed_at"])
                        for s in samples
                        if cost._object(s)["value"] is not None
                    ]
                    if (
                        not usable
                        or usable[0] > history[0]
                        or usable[-1] < history[1]
                        or any(cost._object(s)["value"] is None for s in samples)
                        or data["cadence_seconds"] is None
                    ):
                        gaps.append("REQUESTED_HISTORY_INCOMPLETE")
                    if usable and usable[-1] < history[0]:
                        status = "stale" if matched else "unmatched"
                    if usable and usable[0] > history[1]:
                        gaps.append("CURRENT_OUTSIDE_REQUESTED_HISTORY")
            elif record["record_kind"] == "backup_object":
                if data["object_kind"] == "backup" and matched:
                    if backup_members is None or data["membership_ids"] is None:
                        gaps.append("BACKUP_MEMBERSHIP_MISSING")
                    elif (
                        set(data["membership_ids"]) != set(backup_members)
                        or data["object_id"] not in backup_members
                    ):
                        reasons.append("BACKUP_MEMBERSHIP_CONFLICT")
                else:
                    gaps.append("SNAPSHOT_PARENT_NOT_ESTABLISHED")
            elif record["record_kind"] == "restore_receipt":
                expected = [e for e in expectations if e["target"] == target]
                if not expected:
                    gaps.append("CURRENT_ARTIFACT_MISSING")
                elif data["artifact_sha256"] != expected[0]["artifact_sha256"]:
                    reasons.append("RESTORE_ARTIFACT_CONFLICT")
                if not data["checks"]:
                    gaps.append("RESTORE_CHECKS_MISSING")
                if not history[0] <= _time(data["performed_at"]) <= history[1]:
                    gaps.append("RESTORE_OUTSIDE_ASSESSMENT_WINDOW")
                    status = "stale" if matched else "unmatched"
                if data["result"] != "succeeded":
                    gaps.append("RESTORE_RESULT_NOT_SUCCEEDED")
        if reasons:
            conflicts.extend(reasons)
            status = "conflict"
        assessments.append(
            {
                "record": copy.deepcopy(record),
                "association": (
                    ("related_storage" if record["resource_kind"] == "volume" else "selected")
                    if matched and not reasons
                    else "unmatched"
                ),
                "applicability": (
                    (
                        "compatible_supplied_scope"
                        if matched and not reasons and not gaps
                        else "not_established"
                    )
                    if record["record_kind"] == "restore_receipt"
                    else "not_assessed"
                ),
                "status": status,
                "reasons": sorted(set(reasons + gaps)),
            }
        )
    gaps = []
    if (
        not candidates
        or not contexts
        or any(d["owner_ref"] is None or d["service"] == "unknown" for d in candidates)
    ):
        gaps.append("OWNER_SERVICE_MISSING")
    if not any(
        item["association"] == "selected"
        and cost._object(item["record"])["record_kind"] == "metric"
        and item["status"] == "observed"
        for item in assessments
    ):
        gaps.append("UTILIZATION_MISSING")
    if not any(
        item["association"] != "unmatched"
        and cost._object(item["record"])["record_kind"] == "restore_receipt"
        and cost._object(item["record"])["availability"] == "observed"
        for item in assessments
    ):
        gaps.append("RESTORE_RECEIPT_MISSING")
    if topology["volume_ids"] and not links:
        gaps.append("FILESYSTEM_VOLUME_WITNESS_MISSING")
    if conflicts:
        related_volumes = set()
        for item in assessments:
            item["association"] = "unmatched"
            item["status"] = "conflict"
            if item["applicability"] == "compatible_supplied_scope":
                item["applicability"] = "not_established"
            item["reasons"] = sorted(
                set(cast(list[str], item["reasons"]) + ["GLOBAL_CONTEXT_CONFLICT", *conflicts])
            )
    return {
        "schema_version": SCHEMA,
        "policy_version": POLICY,
        "asset_type": ASSET,
        **AUTHORITY,
        "cost_inventory": copy.deepcopy(report),
        "assessment_at": observations["assessment_at"],
        "assessment_window": copy.deepcopy(observations["assessment_window"]),
        "selected_resource": copy.deepcopy(selected),
        "declarations": copy.deepcopy(declarations),
        "topology": copy.deepcopy(topology),
        "restore_expectations": copy.deepcopy(expectations),
        "evidence": assessments,
        "conflicts": sorted(set(conflicts)),
        "gaps": sorted(set(gaps)),
        "question_inventory": _question_inventory(
            report, chosen, candidates, assessments, related_volumes, bool(conflicts)
        ),
        "operator_summary": {
            "status": "conflict" if conflicts else "processed_with_gaps",
            "record_count": len(records),
            "unmatched_count": sum(x["association"] == "unmatched" for x in assessments),
            "next_question": (
                "resolve_conflict" if conflicts else "review_history_storage_and_recovery_gaps"
            ),
        },
    }


def _question_inventory(
    report: dict[str, object],
    chosen: list[dict[str, object]],
    selected_candidates: list[dict[str, object]],
    assessments: list[dict[str, object]],
    related_volumes: set[object],
    binding_conflict: bool,
) -> list[dict[str, object]]:
    """Ask only unresolved supplied-context questions, retaining ungrouped row anchors."""
    inventory: list[dict[str, object]] = []
    for group in cast(list[dict[str, object]], report["resource_groups"]):
        selected = group in chosen
        related = group["resource_kind"] == "volume" and group["resource_id"] in related_volumes
        candidates = (
            selected_candidates
            if selected
            else cast(list[dict[str, object]], group["binding_candidates"])
        )
        contexts = {(d["environment"], d["service"], d["owner_ref"]) for d in candidates}
        conflict = group["context_status"] == "conflict" or len(contexts) > 1
        questions = []
        if conflict:
            questions.append("resolve_context_conflict")
        else:
            if not candidates or candidates[0]["owner_ref"] is None:
                questions.append("owner_declaration")
            if not candidates or candidates[0]["service"] == "unknown":
                questions.append("service_declaration")
            if not candidates or candidates[0]["environment"] == "unknown":
                questions.append("environment_declaration")
        entries = [
            item
            for item in assessments
            if item["association"] != "unmatched"
            and (
                cost._object(item["record"])["resource_kind"],
                cost._object(item["record"])["resource_id"],
            )
            == (group["resource_kind"], group["resource_id"])
        ]
        if selected or related:
            if binding_conflict:
                questions.append("resolve_evidence_binding")
            metrics = [
                item
                for item in entries
                if cost._object(item["record"])["record_kind"] == "metric"
                and item["status"] == "observed"
            ]
            if not metrics:
                questions.append("dated_utilization")
            elif any(
                "REQUESTED_HISTORY_INCOMPLETE" in cast(list[str], item["reasons"])
                or "REPRESENTATIVE_WORKLOAD_NOT_ASSESSED" in cast(list[str], item["reasons"])
                for item in metrics
            ):
                questions.append("representative_utilization_history")
            restores = [
                item
                for item in entries
                if cost._object(item["record"])["record_kind"] == "restore_receipt"
            ]
            if not restores or any(
                item["applicability"] != "compatible_supplied_scope" for item in restores
            ):
                questions.append("applicable_restore_receipt")
            if (
                any(
                    "FILESYSTEM_VOLUME_WITNESS_MISSING" in cast(list[str], item["reasons"])
                    for item in entries
                )
                or related
                and not entries
            ):
                questions.append("filesystem_volume_identity_witness")
        else:
            questions.extend(("dated_utilization", "scoped_recovery"))
        inventory.append(
            {
                "group_ref": group["group_ref"],
                "selected": selected,
                "related_storage": related,
                "context_status": (
                    "conflict" if conflict else "supplied" if candidates else "missing"
                ),
                "questions": questions,
            }
        )
    for row in cast(list[dict[str, object]], report["rows"]):
        if row["group_ref"] is None and row["bucket"] != "non_resource":
            question = (
                "resolve_native_identity"
                if row["identity_status"] == "conflict"
                else (
                    "native_resource_identity"
                    if row["identity_status"] == "missing"
                    else "product_identity" if row["product"] is None else "charge_classification"
                )
            )
            inventory.append(
                {
                    "group_ref": None,
                    "page": row["page"],
                    "ordinal": row["ordinal"],
                    "questions": [question],
                }
            )
    return inventory


def render_report(report: dict[str, object], cost_raw: bytes, observations_raw: bytes) -> bytes:
    result = copy.deepcopy(report)
    result.pop("report_fingerprint", None)
    hashes = [hashlib.sha256(raw).hexdigest() for raw in (cost_raw, observations_raw)]
    result["upstream_assets"] = [
        {"asset_type": asset, "sha256": digest}
        for asset, digest in zip(("resource_cost_report", "resource_observations"), hashes)
    ]
    result["idempotency_key"] = hashlib.sha256(
        cost._canonical([ASSET, SCHEMA, POLICY, *hashes])
    ).hexdigest()
    result["report_fingerprint"] = hashlib.sha256(cost._canonical(result)).hexdigest()
    return cast(bytes, cost._canonical(result)) + b"\n"


def main(argv: list[str] | None = None) -> int:
    parser = cost._Parser(prog="resource_evidence_report", allow_abbrev=False)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--cost-report", required=True)
    parser.add_argument("--observations", required=True)
    parser.add_argument("--format", choices=("json",), required=True)
    try:
        args = parser.parse_args(argv)
        cost_raw, observations_raw = cost._read_inputs(
            args.input_dir, args.cost_report, args.observations
        )
        report = validate_cost(cost._parse(cost_raw))
        observations = validate_observations(cost._parse(observations_raw))
        result = assess(report, observations, cost_raw)
        sys.stdout.write(render_report(result, cost_raw, observations_raw).decode("utf-8"))
        return 1 if result["conflicts"] else 0
    except (cost.ReportError, OSError, ValueError, UnicodeError, ArithmeticError, RecursionError):
        sys.stdout.write(
            cost._canonical({"error": "INVALID_INPUT", **AUTHORITY}).decode("utf-8") + "\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
