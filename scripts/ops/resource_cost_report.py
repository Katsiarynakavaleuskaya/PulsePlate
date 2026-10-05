#!/usr/bin/env python3
"""Reconcile supplied DigitalOcean charges and declared context, entirely offline."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from datetime import datetime
from decimal import (
    MAX_EMAX,
    MIN_EMIN,
    ROUND_HALF_EVEN,
    Clamped,
    Context,
    Decimal,
    DivisionByZero,
    FloatOperation,
    Inexact,
    InvalidOperation,
    Overflow,
    Rounded,
    Subnormal,
    Underflow,
    localcontext,
)
from typing import NoReturn, cast
from urllib.parse import parse_qs, urlsplit

MAX_BYTES = 4 * 1024 * 1024
MAX_PAGES = 20
MAX_ROWS = 4000
MAX_BINDINGS = 512
MAX_DEPTH = 8
SCHEMA = "pulseplate.resource-cost-report.v1"
POLICY = "resource-cost-policy.v1"
ASSET = "resource_cost_report"
CAPTURE_SCHEMA = "pulseplate.do-invoice-capture.v1"
BINDING_SCHEMA = "pulseplate.resource-cost-bindings.v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTS = {
    "Droplets": ("droplet", "resource_id"),
    "Droplet Backups": ("droplet", "resource_id"),
    "Droplet Snapshots": ("snapshot", "resource_id"),
    "Volumes": ("volume", "resource_uuid"),
    "Database Clusters": ("database_cluster", "resource_uuid"),
}
NON_RESOURCE = {"Taxes", "Uptime Health Check", "Container Registry Subscription"}
KINDS = {kind for kind, _ in PRODUCTS.values()}
BUCKETS = ("allocated", "unallocated", "non_resource", "unclassified")
_MONEY = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,2})?\Z")
_UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")
_PERIOD = re.compile(r"[0-9]{4}-(?:0[1-9]|1[0-2])\Z")
_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z\Z")


class ReportError(ValueError):
    """Only constant diagnostics cross the private input boundary."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ReportError("INVALID_ARGUMENTS")


def _require(condition: bool, code: str = "INVALID_INPUT") -> None:
    if not condition:
        raise ReportError(code)


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ReportError("INVALID_INPUT")
    return value


def _keys(value: object, required: set[str], optional: set[str] | None = None) -> dict[str, object]:
    obj = _object(value)
    _require(required <= obj.keys() <= required | (optional or set()))
    return obj


def _text(value: object, *, empty: bool = False, allow_controls: bool = False) -> str:
    if not isinstance(value, str):
        raise ReportError("INVALID_INPUT")
    _require(empty or bool(value))
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ReportError("INVALID_INPUT") from exc
    _require(allow_controls or all(ord(char) >= 32 and ord(char) != 127 for char in value))
    return value


def _timestamp(value: object) -> str:
    text = _text(value)
    _require(_TIME.fullmatch(text) is not None)
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReportError("INVALID_INPUT") from exc
    return text


def _amount(value: object) -> Decimal:
    text = _text(value)
    _require(_MONEY.fullmatch(text) is not None, "INVALID_AMOUNT")
    return Decimal(text)


def _money(value: Decimal) -> str:
    return format(value, ".2f") if value else "0.00"


def _sum(values: list[Decimal]) -> Decimal:
    """Accumulate ascending widths so a huge coefficient is not revisited per tiny row."""
    groups: dict[int, list[Decimal]] = {}
    for value in values:
        groups.setdefault(len(value.as_tuple().digits), []).append(value)
    result = Decimal("0.00")
    for width in sorted(groups):
        subtotal = sum(groups[width], Decimal("0.00"))
        result += subtotal
    return result


def _precision(values: list[Decimal], count: int) -> int:
    # Include two fractional positions for integer inputs and every financial operation.
    return (
        max((len(value.as_tuple().digits) + 2 for value in values), default=2) + len(str(count)) + 3
    )


def _tree(value: object) -> None:
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        _require(depth <= MAX_DEPTH, "INPUT_DEPTH")
        if isinstance(item, dict):
            pending.extend((key, depth + 1) for key in item)
            pending.extend((entry, depth + 1) for entry in item.values())
        elif isinstance(item, list):
            _require(len(item) <= MAX_ROWS, "INPUT_LIMIT")
            pending.extend((entry, depth + 1) for entry in item)
        elif isinstance(item, str):
            _text(item, empty=True, allow_controls=True)
        elif isinstance(item, Decimal):
            _require(item.is_finite(), "INVALID_JSON_NUMBER")
        else:
            _require(item is None or type(item) in (int, bool), "INVALID_JSON")


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        _require(key not in result, "DUPLICATE_KEY")
        result[key] = value
    return result


def _number(value: str) -> NoReturn:
    raise ReportError("INVALID_JSON_NUMBER")


def _parse(raw: bytes) -> dict[str, object]:
    try:
        _require(len(raw) <= MAX_BYTES, "INPUT_TOO_LARGE")
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_number,
            parse_float=Decimal,
        )
        _tree(value)
        return _object(value)
    except ReportError:
        raise
    except (ValueError, UnicodeError, ArithmeticError, RecursionError) as exc:
        raise ReportError("INVALID_JSON") from exc


def _path_parts(value: str, *, absolute: bool) -> list[str]:
    _text(value)
    _require("\\" not in value and value.startswith("/") is absolute, "UNSAFE_INPUT_PATH")
    parts = value.split("/")[1:] if absolute else value.split("/")
    _require(
        bool(parts) and all(part not in ("", ".", "..") for part in parts), "UNSAFE_INPUT_PATH"
    )
    _require(all(part.casefold() != "secrets" for part in parts), "UNSAFE_INPUT_PATH")
    return parts


def _flag(name: str) -> int:
    value = getattr(os, name, None)
    if not isinstance(value, int):
        raise ReportError("UNSUPPORTED_FILESYSTEM")
    return value


def _admit_file(metadata: os.stat_result) -> None:
    """Reject an unsafe at-rest leaf before open and validate the acquired descriptor."""
    _require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1, "UNSAFE_INPUT_FILE")
    _require(
        metadata.st_uid == os.geteuid() and stat.S_IMODE(metadata.st_mode) & ~0o600 == 0,
        "UNSAFE_INPUT_PERMISSIONS",
    )
    _require(metadata.st_size <= MAX_BYTES, "INPUT_TOO_LARGE")


def _read_inputs(root: str, invoice: str, bindings: str) -> tuple[bytes, bytes]:
    root_parts = _path_parts(root, absolute=True)
    names = [_path_parts(name, absolute=False) for name in (invoice, bindings)]
    _require(not Path(root).is_relative_to(REPO_ROOT), "UNSAFE_INPUT_PATH")
    _require(
        hasattr(os, "geteuid") and os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd,
        "UNSUPPORTED_FILESYSTEM",
    )
    directory_flags = os.O_RDONLY | _flag("O_DIRECTORY") | _flag("O_NOFOLLOW") | _flag("O_CLOEXEC")
    file_flags = os.O_RDONLY | _flag("O_NOFOLLOW") | _flag("O_CLOEXEC") | _flag("O_NONBLOCK")
    descriptors: list[int] = []
    result: list[bytes] = []
    try:
        descriptors.append(os.open("/", directory_flags))
        for part in root_parts:
            descriptors.append(os.open(part, directory_flags, dir_fd=descriptors[-1]))
        root_fd = descriptors[-1]
        metadata = os.fstat(root_fd)
        _require(
            metadata.st_uid == os.geteuid() and stat.S_IMODE(metadata.st_mode) == 0o700,
            "UNSAFE_INPUT_PERMISSIONS",
        )
        for parts in names:
            parent_fd = root_fd
            for part in parts[:-1]:
                descriptors.append(os.open(part, directory_flags, dir_fd=parent_fd))
                parent_fd = descriptors[-1]
                directory = os.fstat(parent_fd)
                _require(
                    directory.st_uid == os.geteuid() and stat.S_IMODE(directory.st_mode) == 0o700,
                    "UNSAFE_INPUT_PERMISSIONS",
                )
            before = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
            _admit_file(before)
            descriptors.append(os.open(parts[-1], file_flags, dir_fd=parent_fd))
            fd = descriptors[-1]
            metadata = os.fstat(fd)
            _admit_file(metadata)
            _require(
                (before.st_dev, before.st_ino) == (metadata.st_dev, metadata.st_ino),
                "INPUT_IDENTITY_CHANGED",
            )
            chunks: list[bytes] = []
            remaining = MAX_BYTES + 1
            while remaining:
                chunk = os.read(fd, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            _require(len(raw) <= MAX_BYTES, "INPUT_TOO_LARGE")
            result.append(raw)
        return result[0], result[1]
    except OSError as exc:
        raise ReportError("UNSAFE_INPUT_READ") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _header(value: object) -> tuple[str, str, Decimal, str | None]:
    header = _object(value)
    _require({"invoice_uuid", "invoice_period", "amount"} <= header.keys())
    if "currency" in header:
        _require(header["currency"] == "USD", "UNSUPPORTED_CURRENCY")
    uuid = _text(header["invoice_uuid"])
    period = _text(header["invoice_period"])
    _require(_UUID.fullmatch(uuid) is not None and _PERIOD.fullmatch(period) is not None)
    update = _timestamp(header["updated_at"]) if "updated_at" in header else None
    return uuid, period, _amount(header["amount"]), update


def _pagination(
    links: object, *, uuid: str, kind: str, page: int, per_page: int, page_count: int
) -> bool:
    obj = _keys(links, set(), {"pages"})
    if "pages" not in obj:
        return True
    pages = _keys(obj["pages"], set(), {"first", "last", "next", "prev"})
    expected = {"first": 1, "last": page_count, "next": page + 1, "prev": page - 1}
    consistent = True
    for label, raw in pages.items():
        url = urlsplit(_text(raw))
        _require(
            url.scheme == "https" and url.netloc == "api.digitalocean.com" and not url.fragment,
            "INVALID_PAGINATION",
        )
        accepted = {f"/v2/customers/my/invoices/{uuid}"}
        if kind == "preview":
            accepted.add("/v2/customers/my/invoices/preview")
        _require(
            re.fullmatch(r"/v2/customers/my/invoices/(?:[0-9a-f-]{36}|preview)", url.path)
            is not None,
            "INVALID_PAGINATION",
        )
        consistent &= url.path in accepted
        query = parse_qs(url.query, keep_blank_values=True, strict_parsing=True)
        _require(
            set(query) == {"page", "per_page"} and all(len(v) == 1 for v in query.values()),
            "INVALID_PAGINATION",
        )
        consistent &= query["page"] == [str(expected[label])] and query["per_page"] == [
            str(per_page)
        ]
        consistent &= label != "next" or page < page_count
        consistent &= label != "prev" or page > 1
    return consistent


def reconcile_invoice(capture: dict[str, object]) -> dict[str, object]:
    """Account for every supplied page/ordinal without inferring provider authenticity."""
    _tree(capture)
    obj = _keys(
        capture,
        {"schema_version", "account_ref", "captured_at", "invoice_kind", "invoice", "pages"},
        {"invoice_after"},
    )
    _require(obj["schema_version"] == CAPTURE_SCHEMA)
    account = _text(obj["account_ref"])
    captured = _timestamp(obj["captured_at"])
    kind = _text(obj["invoice_kind"])
    _require(kind in {"preview", "final"})
    header = _header(obj["invoice"])
    observation = "not_supplied"
    if "invoice_after" in obj:
        observation = "unchanged" if _header(obj["invoice_after"]) == header else "changed"
    pages = obj["pages"]
    if not isinstance(pages, list):
        raise ReportError("INVALID_INPUT")
    _require(0 < len(pages) <= MAX_PAGES, "INPUT_LIMIT")
    errors = ["HEADER_CHANGED"] if observation == "changed" else []
    rows: list[dict[str, object]] = []
    groups: list[dict[str, object]] = []
    group_keys: dict[tuple[str, str], str] = {}
    expected_total: int | None = None
    selected_per_page: int | None = None
    for ordinal_page, raw_page in enumerate(pages, 1):
        page = _keys(raw_page, {"page", "per_page", "response"})
        number, per_page = page["page"], page["per_page"]
        if type(number) is not int or type(per_page) is not int:
            raise ReportError("INVALID_INPUT")
        _require(number > 0 and 1 <= per_page <= 200)
        response = _object(page["response"])
        _require({"invoice_items", "meta"} <= response.keys())
        total = _object(response["meta"]).get("total")
        if type(total) is not int:
            raise ReportError("INVALID_INPUT")
        _require(0 <= total <= MAX_ROWS, "INPUT_LIMIT")
        items = response["invoice_items"]
        if not isinstance(items, list):
            raise ReportError("INVALID_INPUT")
        expected_total = total if expected_total is None else expected_total
        selected_per_page = per_page if selected_per_page is None else selected_per_page
        page_count = max(1, (total + per_page - 1) // per_page)
        if (
            number != ordinal_page
            or total != expected_total
            or per_page != selected_per_page
            or len(pages) != page_count
        ):
            errors.append("INCOMPLETE_CAPTURE")
        expected_items = max(0, min(per_page, total - (ordinal_page - 1) * per_page))
        if len(items) != expected_items or not _pagination(
            response.get("links", {}),
            uuid=header[0],
            kind=kind,
            page=number,
            per_page=per_page,
            page_count=page_count,
        ):
            errors.append("INCOMPLETE_CAPTURE")
        _require(len(rows) + len(items) <= MAX_ROWS, "INPUT_LIMIT")
        for ordinal, raw_row in enumerate(items, 1):
            row = _object(raw_row)
            _require("amount" in row)
            if "currency" in row:
                _require(row["currency"] == "USD", "UNSUPPORTED_CURRENCY")
            product = _text(row.get("product", ""), empty=True)
            resource_id = _text(row.get("resource_id", ""), empty=True)
            resource_uuid = _text(row.get("resource_uuid", ""), empty=True)
            amount = _amount(row["amount"])
            for name in ("start_time", "end_time"):
                if name in row:
                    _timestamp(row[name])
            if "start_time" in row and "end_time" in row:
                _require(
                    datetime.fromisoformat(str(row["start_time"]).replace("Z", "+00:00"))
                    <= datetime.fromisoformat(str(row["end_time"]).replace("Z", "+00:00"))
                )
            bucket, identity_status, group_ref = "unclassified", "unrecognized", None
            if product in PRODUCTS:
                resource_kind, field = PRODUCTS[product]
                identity = resource_id if field == "resource_id" else resource_uuid
                bucket, identity_status = "unallocated", "missing"
                if resource_id and resource_uuid:
                    identity_status = "conflict"
                elif identity:
                    identity_status = "supplied"
                    key = resource_kind, identity
                    if key not in group_keys:
                        group_keys[key] = f"g{len(groups) + 1}"
                        groups.append(
                            {
                                "group_ref": group_keys[key],
                                "resource_kind": resource_kind,
                                "resource_id": identity,
                                "context_status": "missing",
                                "binding_candidates": [],
                                "recovery_verification": "not_assessed",
                                "utilization_verification": "unknown",
                            }
                        )
                    group_ref = group_keys[key]
            elif product in NON_RESOURCE and not resource_id and not resource_uuid:
                bucket, identity_status = "non_resource", "not_applicable"
            elif resource_id and resource_uuid:
                identity_status = "conflict"
            rows.append(
                {
                    "page": ordinal_page,
                    "ordinal": ordinal,
                    "amount": _money(amount),
                    "product": product if product in PRODUCTS or product in NON_RESOURCE else None,
                    "bucket": bucket,
                    "identity_status": identity_status,
                    "group_ref": group_ref,
                }
            )
    if len(rows) != expected_total:
        errors.append("INCOMPLETE_CAPTURE")
    report: dict[str, object] = {
        "schema_version": SCHEMA,
        "policy_version": POLICY,
        "asset_type": ASSET,
        "account_ref": account,
        "captured_at": captured,
        "invoice_kind": kind,
        "invoice_period": header[1],
        "currency": "USD",
        "header_total": _money(header[2]),
        "header_observation_status": observation,
        "rows": rows,
        "resource_groups": groups,
        "row_count": len(rows),
        "declared_row_count": expected_total,
        "page_count": len(pages),
        "errors": sorted(set(errors)),
        "authority": "none",
        "mutation_authority": False,
        "savings_verified": False,
        "unresolved_bindings": [],
    }
    _totals(report)
    return report


def _totals(report: dict[str, object]) -> None:
    rows = cast(list[dict[str, object]], report["rows"])
    amounts = [_amount(_object(row)["amount"]) for row in rows]
    header = _amount(report["header_total"])
    context = Context(
        prec=_precision(amounts + [header], len(rows)),
        rounding=ROUND_HALF_EVEN,
        Emin=MIN_EMIN,
        Emax=MAX_EMAX,
        capitals=1,
        clamp=0,
        flags=[],
        traps=[
            Clamped,
            DivisionByZero,
            FloatOperation,
            Inexact,
            InvalidOperation,
            Overflow,
            Rounded,
            Subnormal,
            Underflow,
        ],
    )
    with localcontext(context):
        total = _sum(amounts)
        report["total"] = _money(total)
        report["residual"] = _money(header - total)
        report["totals"] = {
            bucket: _money(
                _sum(
                    [value for value, row in zip(amounts, rows) if _object(row)["bucket"] == bucket]
                )
            )
            for bucket in BUCKETS
        }
    counts = {bucket: sum(_object(row)["bucket"] == bucket for row in rows) for bucket in BUCKETS}
    report["counts"] = counts
    errors = list(cast(list[str], report["errors"]))
    if report["residual"] != "0.00":
        errors.append("RECONCILIATION_MISMATCH")
    report["errors"] = sorted(set(errors))
    report["accounting_status"] = "inconsistent" if errors else "reconciled"
    report["allocation_status"] = (
        "partial" if counts["unallocated"] or counts["unclassified"] else "complete"
    )
    report["operator_summary"] = {
        "accounting_status": report["accounting_status"],
        "allocation_status": report["allocation_status"],
        "next_question": _question(report),
    }


def _question(report: dict[str, object]) -> str | None:
    if report["errors"]:
        return "Which complete native capture corrects the reported accounting or pagination discrepancy?"
    for group in cast(list[dict[str, object]], report["resource_groups"]):
        obj = _object(group)
        if obj["context_status"] == "conflict":
            return f"Which explicit binding resolves the conflicting declarations for {obj['group_ref']}?"
    for row in cast(list[dict[str, object]], report["rows"]):
        obj = _object(row)
        if obj["bucket"] in {"unallocated", "unclassified"}:
            subject = f"page {obj['page']} ordinal {obj['ordinal']}"
            if obj["identity_status"] == "conflict":
                return f"Which native identity resolves the conflicting fields for {subject}?"
            if obj["identity_status"] == "missing":
                return f"Which explicit native resource identity applies to {subject}?"
            if obj["bucket"] == "unclassified":
                if obj["product"] in NON_RESOURCE:
                    return (
                        f"Which missing classification or association context applies to {subject}?"
                    )
                return f"Which documented product identity explains the unclassified charge at {subject}?"
            for group in cast(list[dict[str, object]], report["resource_groups"]):
                current = _object(group)
                if (
                    current["group_ref"] == obj["group_ref"]
                    and current["context_status"] == "supplied"
                ):
                    candidate = _object(
                        cast(list[dict[str, object]], current["binding_candidates"])[0]
                    )
                    if candidate["owner_ref"] is None:
                        return f"Which missing owner declaration applies to {subject}?"
                    if candidate["service"] == "unknown":
                        return f"Which missing service declaration applies to {subject}?"
            return f"Which missing owner/service binding applies to {subject}?"
    if report["resource_groups"]:
        first = cast(list[dict[str, object]], report["resource_groups"])[0]
        return f"Which dated utilization or recovery observation should be assessed for {first['group_ref']} under OPS-04B?"
    return None


def attach_resource_context(
    report: dict[str, object], bindings: dict[str, object]
) -> dict[str, object]:
    """Attach supplied context once per group; never follow or assess its references."""
    _tree(bindings)
    obj = _keys(bindings, {"schema_version", "account_ref", "bindings"})
    _require(obj["schema_version"] == BINDING_SCHEMA)
    account = _text(obj["account_ref"])
    declarations = obj["bindings"]
    if not isinstance(declarations, list):
        raise ReportError("INVALID_INPUT")
    _require(len(declarations) <= MAX_BINDINGS, "INPUT_LIMIT")
    index: dict[tuple[str, str], list[dict[str, object]]] = {}
    for raw in declarations:
        binding = _keys(
            raw,
            {
                "resource_kind",
                "resource_id",
                "environment",
                "service",
                "owner_ref",
                "evidence_ref",
                "recovery_ref",
                "utilization_ref",
            },
        )
        kind, identity = _text(binding["resource_kind"]), _text(binding["resource_id"])
        _require(
            kind in KINDS
            and _text(binding["environment"]) in {"production", "staging", "shared", "unknown"}
        )
        _require(
            _text(binding["service"]) in {"app", "database", "prometheus", "packages", "unknown"}
        )
        context = dict(binding)
        for field in ("owner_ref", "evidence_ref", "recovery_ref", "utilization_ref"):
            _require(binding[field] is None or isinstance(binding[field], str))
            if binding[field] is not None:
                _text(binding[field])
        index.setdefault((kind, identity), []).append(context)
    result = copy.deepcopy(report)
    if account != result["account_ref"]:
        result["errors"] = sorted(
            set(list(cast(list[str], result["errors"])) + ["ACCOUNT_MISMATCH"])
        )
    unused = set(index)
    allocated: set[str] = set()
    for raw_group in cast(list[dict[str, object]], result["resource_groups"]):
        group = _object(raw_group)
        key = str(group["resource_kind"]), str(group["resource_id"])
        candidates = index.get(key, []) if account == result["account_ref"] else []
        if candidates:
            unused.discard(key)
        group["binding_candidates"] = candidates
        if candidates:
            group["context_status"] = (
                "supplied"
                if all(candidate == candidates[0] for candidate in candidates)
                else "conflict"
            )
            if (
                group["context_status"] == "supplied"
                and candidates[0]["owner_ref"] is not None
                and candidates[0]["service"] != "unknown"
            ):
                allocated.add(str(group["group_ref"]))
            group["utilization_verification"] = (
                "not_assessed" if candidates[0]["utilization_ref"] is not None else "unknown"
            )
    result["unresolved_bindings"] = [
        candidate for key in index if key in unused for candidate in index[key]
    ]
    for raw_row in cast(list[dict[str, object]], result["rows"]):
        row = _object(raw_row)
        if row["group_ref"] in allocated:
            row["bucket"] = "allocated"
    _totals(result)
    return result


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def render_report(report: dict[str, object], invoice_raw: bytes, bindings_raw: bytes) -> bytes:
    """Bind only the two acquired input bytes and the deterministic content projection."""
    result = copy.deepcopy(report)
    fingerprints = [hashlib.sha256(raw).hexdigest() for raw in (invoice_raw, bindings_raw)]
    result["upstream_assets"] = [
        {"asset_type": role, "sha256": digest}
        for role, digest in zip(("invoice_capture", "resource_bindings"), fingerprints)
    ]
    result["idempotency_key"] = hashlib.sha256(
        _canonical([ASSET, SCHEMA, POLICY, *fingerprints])
    ).hexdigest()
    result.pop("report_fingerprint", None)
    result["report_fingerprint"] = hashlib.sha256(_canonical(result)).hexdigest()
    return _canonical(result) + b"\n"


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="resource_cost_report", allow_abbrev=False)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--invoice", required=True)
    parser.add_argument("--bindings", required=True)
    parser.add_argument("--format", choices=("json",), required=True)
    try:
        args = parser.parse_args(argv)
        invoice_raw, bindings_raw = _read_inputs(args.input_dir, args.invoice, args.bindings)
        report = attach_resource_context(
            reconcile_invoice(_parse(invoice_raw)), _parse(bindings_raw)
        )
        output = render_report(report, invoice_raw, bindings_raw)
        sys.stdout.write(output.decode("utf-8"))
        return 1 if report["accounting_status"] == "inconsistent" else 0
    except (ReportError, ValueError, UnicodeError, ArithmeticError, RecursionError):
        sys.stdout.write(
            _canonical({"error": "INVALID_INPUT", "authority": "none"}).decode("utf-8") + "\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
