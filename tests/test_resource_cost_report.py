"""Native-shaped offline accounting and private-input regressions for OPS-04A."""

from __future__ import annotations

from scripts.ops import resource_cost_report as cost


def test_shared_resource_preserves_compute_backup_and_idless_tax() -> None:
    rows = [
        {"product": "Droplets", "resource_id": "123", "resource_uuid": "", "amount": "10.00"},
        {"product": "Droplet Backups", "resource_id": "123", "resource_uuid": "", "amount": "2.00"},
        {"product": "Taxes", "resource_id": "", "resource_uuid": "", "amount": "1.00"},
    ]
    capture = {
        "schema_version": "pulseplate.do-invoice-capture.v1",
        "account_ref": "synthetic-account",
        "captured_at": "2026-10-05T12:00:00Z",
        "invoice_kind": "final",
        "invoice": {
            "invoice_uuid": "00000000-0000-4000-8000-000000000001",
            "invoice_period": "2026-09",
            "amount": "13.00",
        },
        "pages": [
            {
                "page": 1,
                "per_page": 200,
                "response": {
                    "invoice_items": rows,
                    "links": {},
                    "meta": {"total": 3},
                },
            }
        ],
    }
    report = cost.reconcile_invoice(capture)
    assert report["row_count"] == 3
    assert report["total"] == "13.00"
    assert report["residual"] == "0.00"
    assert len(report["resource_groups"]) == 1


import copy
from decimal import Decimal, localcontext
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import cast

import pytest

UUID = "00000000-0000-4000-8000-000000000001"


def native_row(
    product: str = "Droplets", amount: str = "1.00", identity: str = "123", *, uuid: bool = False
) -> dict[str, object]:
    return {
        "product": product,
        "resource_id": "" if uuid else identity,
        "resource_uuid": identity if uuid else "",
        "amount": amount,
        "description": "synthetic description",
        "group_description": "synthetic group",
        "duration": "744",
        "duration_unit": "Hours",
        "project_name": "synthetic-project",
        "category": "iaas",
        "start_time": "2026-09-01T00:00:00Z",
        "end_time": "2026-10-01T00:00:00Z",
    }


def capture(
    rows: list[dict[str, object]] | None = None,
    *,
    total: str = "1.00",
    kind: str = "final",
    after: bool = False,
) -> dict[str, object]:
    items = rows if rows is not None else [native_row()]
    result: dict[str, object] = {
        "schema_version": cost.CAPTURE_SCHEMA,
        "account_ref": "account",
        "captured_at": "2026-09-15T00:00:00Z",
        "invoice_kind": kind,
        "invoice": {"invoice_uuid": UUID, "invoice_period": "2026-09", "amount": total},
        "pages": [
            {
                "page": 1,
                "per_page": 200,
                "response": {"invoice_items": items, "links": {}, "meta": {"total": len(items)}},
            }
        ],
    }
    if after:
        result["invoice_after"] = copy.deepcopy(result["invoice"])
    return result


def binding(identity: str = "123", kind: str = "droplet") -> dict[str, object]:
    return {
        "resource_kind": kind,
        "resource_id": identity,
        "environment": "shared",
        "service": "packages",
        "owner_ref": "operator",
        "evidence_ref": "inventory",
        "recovery_ref": "restore",
        "utilization_ref": None,
    }


def bindings(
    rows: list[dict[str, object]] | None = None, *, account: str = "account"
) -> dict[str, object]:
    return {
        "schema_version": cost.BINDING_SCHEMA,
        "account_ref": account,
        "bindings": rows if rows is not None else [binding()],
    }


def reconciled(cap: dict[str, object], bind: dict[str, object] | None = None) -> dict[str, object]:
    return cost.attach_resource_context(
        cost.reconcile_invoice(cap), bind if bind is not None else bindings()
    )


def objects(value: object) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], value)


def private_inputs(
    tmp_path: Path, cap: dict[str, object] | None = None, bind: dict[str, object] | None = None
) -> tuple[Path, list[str]]:
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    for name, obj in (
        ("invoice.json", cap if cap is not None else capture()),
        ("bindings.json", bind if bind is not None else bindings()),
    ):
        path = root / name
        path.write_text(json.dumps(obj), encoding="utf-8")
        path.chmod(0o600)
    return root, [
        "--input-dir",
        str(root),
        "--invoice",
        "invoice.json",
        "--bindings",
        "bindings.json",
        "--format",
        "json",
    ]


@pytest.mark.parametrize(
    "product,kind,use_uuid",
    [
        ("Droplets", "droplet", False),
        ("Droplet Backups", "droplet", False),
        ("Droplet Snapshots", "snapshot", False),
        ("Volumes", "volume", True),
        ("Database Clusters", "database_cluster", True),
    ],
)
def test_exact_native_kind_and_generic_binding_identity(
    product: str, kind: str, use_uuid: bool
) -> None:
    report = reconciled(
        capture([native_row(product, uuid=use_uuid)]), bindings([binding(kind=kind)])
    )
    assert report["allocation_status"] == "complete"
    assert report["counts"] == {
        "allocated": 1,
        "unallocated": 0,
        "non_resource": 0,
        "unclassified": 0,
    }
    assert objects(report["resource_groups"])[0]["recovery_verification"] == "not_assessed"


def test_database_components_free_rows_equal_rows_and_signs_survive() -> None:
    rows = [
        native_row("Database Clusters", amount=value, uuid=True)
        for value in ("0.00", "0.10", "0.20", "-0.10", "0.10")
    ]
    report = reconciled(capture(rows, total="0.30"), bindings([binding(kind="database_cluster")]))
    assert report["row_count"] == 5 and report["total"] == "0.30"
    assert [row["ordinal"] for row in objects(report["rows"])] == [1, 2, 3, 4, 5]
    assert len(objects(report["resource_groups"])) == 1
    assert {row["group_ref"] for row in objects(report["rows"])} == {"g1"}


@pytest.mark.parametrize("product", sorted(cost.NON_RESOURCE))
def test_known_non_resource_has_no_fake_identity(product: str) -> None:
    report = reconciled(
        capture([native_row(product, amount="0", identity="")], total="0"), bindings([])
    )
    assert report["totals"] == {
        "allocated": "0.00",
        "unallocated": "0.00",
        "non_resource": "0.00",
        "unclassified": "0.00",
    }
    assert objects(report["rows"])[0]["bucket"] == "non_resource"
    assert report["resource_groups"] == []


@pytest.mark.parametrize(
    "amount", [None, 1, 1.5, True, "NaN", "Infinity", "1e2", "1.000", "+1", " 1", "01.00", ""]
)
def test_invalid_money_never_becomes_zero_or_rounded(amount: object) -> None:
    row = native_row()
    row["amount"] = amount
    with pytest.raises(cost.ReportError):
        cost.reconcile_invoice(capture([row]))


def test_large_coefficient_cancellation_is_independent_of_ambient_context() -> None:
    large = "1" + "0" * 5000
    rows = [
        native_row(amount=large + ".10"),
        native_row(amount="-" + large + ".00"),
        native_row(amount="0.20"),
    ]
    with localcontext() as context:
        context.prec = 2
        report = reconciled(capture(rows, total="0.30"))
    assert report["total"] == "0.30" and report["residual"] == "0.00"


def test_header_large_residual_and_canceling_unallocated_counts() -> None:
    report = reconciled(
        capture([native_row(amount="1"), native_row(amount="-1")], total="9" + "0" * 40),
        bindings([]),
    )
    assert report["accounting_status"] == "inconsistent"
    assert report["residual"] == "9" + "0" * 40 + ".00"
    assert report["allocation_status"] == "partial"
    assert report["counts"]["unallocated"] == 2


def test_zero_unbound_and_unknown_product_prevent_complete_allocation() -> None:
    report = reconciled(
        capture(
            [native_row(amount="0"), native_row("future SECRET product", amount="0")], total="0"
        ),
        bindings([]),
    )
    assert report["accounting_status"] == "reconciled"
    assert report["allocation_status"] == "partial"
    assert "SECRET" not in json.dumps(report)


@pytest.mark.parametrize(
    "change", ["missing", "dual", "wrong_field", "unknown", "unexpected_nonresource_id"]
)
def test_unresolved_native_identity_preserves_cost(change: str) -> None:
    row = native_row()
    if change == "missing":
        row["resource_id"] = ""
    elif change == "dual":
        row["resource_uuid"] = "uuid"
    elif change == "wrong_field":
        row["resource_id"], row["resource_uuid"] = "", "123"
    elif change == "unknown":
        row["product"] = "droplets"
        row["category"] = "droplet"
    else:
        row["product"] = "Taxes"
    report = reconciled(capture([row]))
    assert report["total"] == "1.00" and report["allocation_status"] == "partial"
    assert report["resource_groups"] == []


def test_name_similarity_never_links_snapshot_to_droplet() -> None:
    row = native_row("Droplet Snapshots")
    row["description"] = "droplet 123"
    report = reconciled(capture([row]))
    assert objects(report["resource_groups"])[0]["context_status"] == "missing"
    assert report["allocation_status"] == "partial"


@pytest.mark.parametrize(
    "case", ["different", "same", "wrong_account", "unused", "missing_owner", "unknown_service"]
)
def test_binding_conflicts_and_missing_context(case: str) -> None:
    first = binding()
    other = binding()
    entries = [first]
    account = "account"
    if case == "different":
        other["owner_ref"] = "other"
        entries.append(other)
    elif case == "same":
        entries.append(other)
    elif case == "wrong_account":
        account = "other"
    elif case == "unused":
        entries = [binding("999")]
    elif case == "missing_owner":
        first["owner_ref"] = None
    else:
        first["service"] = "unknown"
    cap, bound = capture(), bindings(entries, account=account)
    original = copy.deepcopy((cap, bound))
    report = reconciled(cap, bound)
    assert (cap, bound) == original
    assert report["allocation_status"] == ("complete" if case == "same" else "partial")
    if case == "different":
        assert objects(report["resource_groups"])[0]["context_status"] == "conflict"
    if case == "wrong_account":
        assert "ACCOUNT_MISMATCH" in report["errors"]


@pytest.mark.parametrize("field", list(binding()))
def test_malformed_binding_fields_fail_closed(field: str) -> None:
    row = binding()
    row[field] = []
    with pytest.raises(cost.ReportError):
        reconciled(capture(), bindings([row]))


def test_private_context_once_and_summary_without_arbitrary_prose() -> None:
    sentinel = "SIGNED-URL-SECRET-" + "z" * 6000
    row = binding()
    row["owner_ref"] = sentinel
    row["evidence_ref"] = "https://untrusted.invalid/SECRET"
    row["utilization_ref"] = "file:///SECRET"
    rows = [native_row(amount="0") for _ in range(4000)]
    for item in rows:
        item["description"] = "EXECUTE SECRET"
    cap = capture(rows, total="0")
    # Twenty real page wrappers, no reference dereference or per-row binding expansion.
    cap["pages"] = multipages(rows)
    report = reconciled(cap, bindings([row]))
    output = cost.render_report(report, b"invoice", b"bindings").decode()
    assert output.count(sentinel) == 1
    assert len(output) < 1000000
    summary = json.dumps(report["operator_summary"])
    assert "SECRET" not in summary and "EXECUTE" not in output
    group = objects(report["resource_groups"])[0]
    assert group["utilization_verification"] == "not_assessed"
    assert {item["group_ref"] for item in objects(report["rows"])} == {"g1"}


def page_url(number: int, per_page: int = 200, target: str = UUID) -> str:
    return f"https://api.digitalocean.com/v2/customers/my/invoices/{target}?page={number}&per_page={per_page}"


def multipages(rows: list[dict[str, object]], per_page: int = 200) -> list[dict[str, object]]:
    total = len(rows)
    count = max(1, (total + per_page - 1) // per_page)
    pages: list[dict[str, object]] = []
    for index in range(count):
        links: dict[str, object] = {}
        if count > 1:
            link_pages = {"first": page_url(1, per_page), "last": page_url(count, per_page)}
            if index:
                link_pages["prev"] = page_url(index, per_page)
            if index + 1 < count:
                link_pages["next"] = page_url(index + 2, per_page)
            links["pages"] = link_pages
        pages.append(
            {
                "page": index + 1,
                "per_page": per_page,
                "response": {
                    "invoice_items": rows[index * per_page : (index + 1) * per_page],
                    "links": links,
                    "meta": {"total": total},
                },
            }
        )
    return pages


@pytest.mark.parametrize(
    "case", ["valid", "missing", "repeated", "meta", "per_page", "next", "crossed_uuid"]
)
def test_real_pagination_conservation_and_detected_conflicts(case: str) -> None:
    cap = capture([native_row()] * 3, total="3")
    pages = multipages([native_row()] * 3, per_page=2)
    cap["pages"] = pages
    if case == "missing":
        pages.pop()
    elif case == "repeated":
        pages[1] = copy.deepcopy(pages[0])
    elif case == "meta":
        pages[1]["response"]["meta"]["total"] = 4
    elif case == "per_page":
        pages[1]["per_page"] = 3
    elif case == "next":
        pages[0]["response"]["links"]["pages"]["next"] = page_url(1, 2)
    elif case == "crossed_uuid":
        pages[0]["response"]["links"]["pages"]["next"] = page_url(
            2, 2, "00000000-0000-4000-8000-000000000002"
        )
    report = cost.reconcile_invoice(cap)
    assert report["accounting_status"] == ("reconciled" if case == "valid" else "inconsistent")


@pytest.mark.parametrize("field", ["invoice_uuid", "invoice_period", "amount", "updated_at"])
def test_after_header_valid_drift_is_inconsistent(field: str) -> None:
    cap = capture(after=True)
    changed = {
        "invoice_uuid": "00000000-0000-4000-8000-000000000002",
        "invoice_period": "2026-08",
        "amount": "2.00",
        "updated_at": "2026-10-01T00:00:00Z",
    }
    cap["invoice_after"][field] = changed[field]
    report = cost.reconcile_invoice(cap)
    assert report["header_observation_status"] == "changed"
    assert "HEADER_CHANGED" in report["errors"]


@pytest.mark.parametrize("after,updated", [(False, False), (True, False), (True, True)])
def test_original_and_final_optional_update_header_compatibility(
    after: bool, updated: bool
) -> None:
    cap = capture(after=after)
    if updated:
        for name in ("invoice", "invoice_after"):
            cap[name]["updated_at"] = "2026-10-01T00:00:00Z"
    report = cost.reconcile_invoice(cap)
    assert report["header_observation_status"] == ("unchanged" if after else "not_supplied")
    assert report["accounting_status"] == "reconciled"


@pytest.mark.parametrize(
    "value",
    [
        None,
        {},
        {"amount": "1"},
        {"invoice_uuid": UUID, "invoice_period": "2026-09", "amount": "1", "updated_at": None},
    ],
)
def test_malformed_after_header_is_invalid(value: object) -> None:
    cap = capture()
    cap["invoice_after"] = value
    with pytest.raises(cost.ReportError):
        cost.reconcile_invoice(cap)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}',
        b'{"a":{"b":1,"b":2}}',
        b'{"a":NaN}',
        b'{"a":Infinity}',
        b"\xff",
        b'{"a":"\\ud800"}',
        b"{",
        ('{"a":' + "9" * 5000 + "}").encode(),
    ],
)
def test_strict_json_refuses_ambiguous_or_nonfinite_bytes(raw: bytes) -> None:
    with pytest.raises(cost.ReportError):
        cost._parse(raw)


@pytest.mark.parametrize("depth,accepted", [(8, True), (9, False)])
def test_json_depth_boundary(depth: int, accepted: bool) -> None:
    value: object = 0
    for _ in range(depth):
        value = {"x": value}
    if accepted:
        assert cost._parse(json.dumps(value).encode()) == value
    else:
        with pytest.raises(cost.ReportError, match="INPUT_DEPTH"):
            cost._parse(json.dumps(value).encode())


@pytest.mark.parametrize("size,accepted", [(cost.MAX_BYTES, True), (cost.MAX_BYTES + 1, False)])
def test_reader_byte_limit(tmp_path: Path, size: int, accepted: bool) -> None:
    root, _ = private_inputs(tmp_path)
    (root / "invoice.json").write_bytes(b" " * size)
    if accepted:
        first, _ = cost._read_inputs(str(root), "invoice.json", "bindings.json")
        assert len(first) == size
    else:
        with pytest.raises(cost.ReportError, match="INPUT_TOO_LARGE"):
            cost._read_inputs(str(root), "invoice.json", "bindings.json")


@pytest.mark.parametrize(
    "case",
    [
        "root_link",
        "ancestor_link",
        "leaf_link",
        "intermediate_link",
        "fifo",
        "directory",
        "hardlink",
        "root_mode",
        "leaf_mode",
        "traversal",
        "absolute",
        "secrets",
    ],
)
def test_unsafe_paths_and_objects_refused(tmp_path: Path, case: str) -> None:
    root, _ = private_inputs(tmp_path)
    selected = "invoice.json"
    if case == "root_link":
        link = tmp_path / "link"
        link.symlink_to(root, target_is_directory=True)
        root = link
    elif case == "ancestor_link":
        link = tmp_path / "link"
        link.symlink_to(tmp_path, target_is_directory=True)
        root = link / "private"
    elif case in {"leaf_link", "fifo", "directory", "hardlink"}:
        leaf = root / "invoice.json"
        leaf.unlink()
        if case == "leaf_link":
            leaf.symlink_to(root / "bindings.json")
        elif case == "fifo":
            os.mkfifo(leaf)
        elif case == "directory":
            leaf.mkdir()
        else:
            os.link(root / "bindings.json", leaf)
    elif case == "intermediate_link":
        (root / "link").symlink_to(root, target_is_directory=True)
        selected = "link/invoice.json"
    elif case == "root_mode":
        root.chmod(0o755)
    elif case == "leaf_mode":
        (root / "invoice.json").chmod(0o644)
    elif case == "traversal":
        selected = "../private/invoice.json"
    elif case == "absolute":
        selected = str(root / "invoice.json")
    else:
        selected = "secrets/invoice.json"
    with pytest.raises(cost.ReportError):
        cost._read_inputs(str(root), selected, "bindings.json")


def test_filesystem_primitive_and_owner_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = private_inputs(tmp_path)
    with monkeypatch.context() as patch:
        patch.delattr(cost.os, "O_NOFOLLOW")
        with pytest.raises(cost.ReportError, match="UNSUPPORTED_FILESYSTEM"):
            cost._read_inputs(str(root), "invoice.json", "bindings.json")
    monkeypatch.setattr(cost.os, "geteuid", lambda: -1)
    with pytest.raises(cost.ReportError, match="UNSAFE_INPUT_PERMISSIONS"):
        cost._read_inputs(str(root), "invoice.json", "bindings.json")


def test_cli_repeat_lineage_and_private_read_scope(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, argv = private_inputs(tmp_path)
    acquired: list[str] = []
    real_read = cost.os.read

    def observe(fd: int, size: int) -> bytes:
        acquired.append("read")
        return real_read(fd, size)

    monkeypatch.setattr(cost.os, "read", observe)
    assert cost.main(argv) == 0
    first = capsys.readouterr()
    assert cost.main(argv) == 0
    second = capsys.readouterr()
    assert first == second and first.err == ""
    report = json.loads(first.out)
    hashes = [
        hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ("invoice.json", "bindings.json")
    ]
    assert [item["sha256"] for item in report["upstream_assets"]] == hashes
    fingerprint = report.pop("report_fingerprint")
    assert fingerprint == hashlib.sha256(cost._canonical(report)).hexdigest()
    assert (
        report["idempotency_key"]
        == hashlib.sha256(
            cost._canonical([cost.ASSET, cost.SCHEMA, cost.POLICY, *hashes])
        ).hexdigest()
    )
    assert len(acquired) == 8  # Two selected files, one data and one EOF read each, twice.


@pytest.mark.parametrize(
    "case,exit_code",
    [
        ("mismatch", 1),
        ("after_changed", 1),
        ("bad_json", 2),
        ("arguments", 2),
        ("malformed_binding", 2),
    ],
)
def test_cli_codes_and_constant_no_echo_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], case: str, exit_code: int
) -> None:
    cap = capture(total="2" if case == "mismatch" else "1", after=case == "after_changed")
    if case == "after_changed":
        cap["invoice_after"]["amount"] = "3"
    root, argv = private_inputs(tmp_path, cap)
    if case == "bad_json":
        (root / "invoice.json").write_text('{"SECRET":NaN}')
    elif case == "arguments":
        argv += ["--SECRET", "secret-value"]
    elif case == "malformed_binding":
        (root / "bindings.json").write_text('{"SECRET":[]}')
    assert cost.main(argv) == exit_code
    output = capsys.readouterr()
    assert "SECRET" not in output.out + output.err and str(root) not in output.out + output.err
    assert json.loads(output.out)["authority"] == "none"


def test_standalone_subprocess_has_fixed_program_and_no_host_credentials(tmp_path: Path) -> None:
    _, argv = private_inputs(tmp_path)
    script = Path(cost.__file__)
    result = subprocess.run(
        [sys.executable, str(script), *argv],
        env={"PATH": os.defpath},
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0 and result.stderr == ""
    assert json.loads(result.stdout)["accounting_status"] == "reconciled"


def test_lineage_input_and_policy_sensitivity(monkeypatch: pytest.MonkeyPatch) -> None:
    report = reconciled(capture())
    one = json.loads(cost.render_report(report, b"invoice", b"binding"))
    two = json.loads(cost.render_report(report, b"invoice ", b"binding"))
    assert one["idempotency_key"] != two["idempotency_key"]
    monkeypatch.setattr(cost, "POLICY", "resource-cost-policy.v2")
    three = json.loads(cost.render_report(report, b"invoice", b"binding"))
    assert one["idempotency_key"] != three["idempotency_key"]


@pytest.mark.parametrize("surface", ["rows", "pages", "bindings"])
def test_inventory_limits_refuse_overflow(surface: str) -> None:
    with pytest.raises(cost.ReportError, match="INPUT_LIMIT"):
        if surface == "bindings":
            reconciled(capture(), bindings([binding()] * 513))
        elif surface == "pages":
            cap = capture()
            cap["pages"] *= 21
            cost.reconcile_invoice(cap)
        else:
            cost.reconcile_invoice(capture([native_row()] * 4001, total="4001"))


def test_empty_native_capture_and_optional_metadata() -> None:
    report = reconciled(capture([], total="0", kind="preview"), bindings([]))
    assert report["total"] == "0.00" and report["row_count"] == 0
    assert report["invoice_kind"] == "preview" and report["allocation_status"] == "complete"


@pytest.mark.parametrize(
    "case",
    [
        "capture_object",
        "pages",
        "items",
        "bindings",
        "boolean_count",
        "invalid_date",
        "invalid_period",
        "dual_unknown",
    ],
)
def test_malformed_native_container_and_date_boundaries(case: str) -> None:
    cap = capture()
    bound = bindings()
    if case == "capture_object":
        with pytest.raises(cost.ReportError):
            cost.reconcile_invoice(cast(dict[str, object], []))
        return
    if case == "pages":
        cap["pages"] = None
    elif case == "items":
        cap["pages"][0]["response"]["invoice_items"] = {}
    elif case == "bindings":
        bound["bindings"] = None
    elif case == "boolean_count":
        cap["pages"][0]["response"]["meta"]["total"] = True
    elif case == "invalid_date":
        cap["captured_at"] = "2026-02-30T00:00:00Z"
    elif case == "invalid_period":
        cap["invoice"]["invoice_period"] = "2026-13"
    else:
        row = native_row("Future Product")
        row["resource_uuid"] = "uuid"
        report = reconciled(capture([row]))
        assert objects(report["rows"])[0]["identity_status"] == "conflict"
        return
    with pytest.raises(cost.ReportError):
        reconciled(cap, bound)


def test_private_nested_inputs_and_directory_permissions(tmp_path: Path) -> None:
    root, _ = private_inputs(tmp_path)
    nested = root / "nested"
    nested.mkdir(mode=0o700)
    (root / "invoice.json").rename(nested / "invoice.json")
    first, _ = cost._read_inputs(str(root), "nested/invoice.json", "bindings.json")
    assert json.loads(first)["invoice_kind"] == "final"
    nested.chmod(0o755)
    with pytest.raises(cost.ReportError, match="UNSAFE_INPUT_PERMISSIONS"):
        cost._read_inputs(str(root), "nested/invoice.json", "bindings.json")


def test_shared_summary_does_not_reask_supplied_identity() -> None:
    report = reconciled(capture(), bindings([]))
    question = report["operator_summary"]["next_question"]
    assert "owner/service binding" in question
    assert "123" not in question and "identity" not in question


def test_supported_preview_link_and_foreign_endpoint_refusal() -> None:
    cap = capture([native_row()] * 2, total="2", kind="preview")
    pages = multipages([native_row()] * 2, per_page=1)
    cap["pages"] = pages
    for page in pages:
        link_pages = page["response"]["links"]["pages"]
        for label in link_pages:
            link_pages[label] = link_pages[label].replace(UUID, "preview")
    assert cost.reconcile_invoice(cap)["accounting_status"] == "reconciled"
    pages[0]["response"]["links"]["pages"]["next"] = "https://untrusted.invalid/SECRET"
    with pytest.raises(cost.ReportError, match="INVALID_PAGINATION"):
        cost.reconcile_invoice(cap)


def test_malformed_second_input_emits_no_partial_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, argv = private_inputs(tmp_path)
    (root / "bindings.json").write_text("{malformed-private-secret")
    assert cost.main(argv) == 2
    report = json.loads(capsys.readouterr().out)
    assert report == {"error": "INVALID_INPUT", "authority": "none"}


def test_512_bindings_admitted_and_no_context_aliases() -> None:
    supplied = bindings([binding(str(index)) for index in range(512)])
    report = reconciled(capture(), supplied)
    assert report["allocation_status"] == "complete"
    objects(supplied["bindings"])[123]["owner_ref"] = "changed-after-call"
    assert objects(report["resource_groups"])[0]["binding_candidates"][0]["owner_ref"] == "operator"


def test_reader_rejects_checkout_containment_and_noncanonical_root() -> None:
    for root in (
        str(cost.REPO_ROOT),
        str(cost.REPO_ROOT) + "/../private",
        "/private//tmp/input",
        "/private/tmp/secrets",
    ):
        with pytest.raises(cost.ReportError, match="UNSAFE_INPUT_PATH"):
            cost._read_inputs(root, "invoice.json", "bindings.json")


@pytest.mark.parametrize("missing", ["owner_ref", "service"])
def test_question_requests_only_missing_binding_fact(missing: str) -> None:
    supplied = binding()
    supplied[missing] = None if missing == "owner_ref" else "unknown"
    report = reconciled(capture(), bindings([supplied]))
    question = report["operator_summary"]["next_question"]
    assert ("owner declaration" if missing == "owner_ref" else "service declaration") in question
    assert (
        "service declaration" if missing == "owner_ref" else "owner declaration"
    ) not in question


def test_finite_decimal_optional_metadata_remains_uninterpreted() -> None:
    parsed = cost._parse(b'{"large":1e999,"fraction":1.5}')
    assert parsed == {"large": Decimal("1e999"), "fraction": Decimal("1.5")}
    cap = capture()
    cap["invoice"]["optional_metadata"] = parsed
    report = cost.reconcile_invoice(cap)
    assert report["total"] == "1.00" and "optional_metadata" not in report
    cap["invoice"]["amount"] = parsed["fraction"]
    with pytest.raises(cost.ReportError):
        cost.reconcile_invoice(cap)


def test_nonfinite_and_unsupported_decimal_metadata_fail_closed() -> None:
    with pytest.raises(cost.ReportError):
        cost._parse(b'{"a":1e9999999999999999999999999}')
    cap = capture()
    cap["invoice"]["optional_metadata"] = Decimal("Infinity")
    with pytest.raises(cost.ReportError):
        cost.reconcile_invoice(cap)


def test_ignored_native_prose_can_contain_escaped_controls_without_echo() -> None:
    row = native_row()
    row["description"] = "SECRET\n\x1b[31mhostile display"
    row["optional_metadata"] = {"notes": "SECRET\r\ttext"}
    parsed = cost._parse(json.dumps(capture([row])).encode())
    report = reconciled(parsed)
    assert report["accounting_status"] == "reconciled"
    assert "SECRET" not in json.dumps(report)
    row["resource_id"] = "123\nSECRET"
    with pytest.raises(cost.ReportError):
        cost.reconcile_invoice(capture([row]))


@pytest.mark.parametrize(
    "case",
    [
        "idless_tax",
        "droplet_id_only",
        "database_uuid_only",
        "spaces",
        "kubernetes",
        "missing_product",
        "empty_product",
    ],
)
def test_optional_native_fields_keep_canonical_minimal_charge_shapes(case: str) -> None:
    rows = {
        "idless_tax": {"product": "Taxes", "amount": "1.00"},
        "droplet_id_only": {"product": "Droplets", "resource_id": "123", "amount": "1.00"},
        "database_uuid_only": {
            "product": "Database Clusters",
            "resource_uuid": "123",
            "amount": "1.00",
        },
        "spaces": {"product": "Spaces", "amount": "1.00"},
        "kubernetes": {"product": "Kubernetes", "resource_uuid": "native-uuid", "amount": "1.00"},
        "missing_product": {"amount": "1.00"},
        "empty_product": {"product": "", "amount": "1.00"},
    }
    bound = bindings(
        [binding(kind="database_cluster" if case == "database_uuid_only" else "droplet")]
    )
    report = reconciled(capture([rows[case]]), bound)
    assert report["row_count"] == 1 and report["total"] == "1.00"
    assert report["accounting_status"] == "reconciled"
    expected = (
        "non_resource"
        if case == "idless_tax"
        else "allocated" if case in {"droplet_id_only", "database_uuid_only"} else "unclassified"
    )
    assert objects(report["rows"])[0]["bucket"] == expected
    assert len(objects(report["resource_groups"])) == (1 if expected == "allocated" else 0)


@pytest.mark.parametrize("field", ["product", "resource_id", "resource_uuid"])
@pytest.mark.parametrize("value", [None, 123, [], {}])
def test_present_malformed_optional_native_fields_remain_invalid(field: str, value: object) -> None:
    row: dict[str, object] = {"amount": "1.00", field: value}
    with pytest.raises(cost.ReportError):
        cost.reconcile_invoice(capture([row]))


@pytest.mark.parametrize("surface", ["invoice", "invoice_after", "row"])
def test_explicit_non_usd_financial_context_refused(surface: str) -> None:
    cap = capture(after=True)
    target = (
        objects(cap["pages"])[0]["response"]["invoice_items"][0]
        if surface == "row"
        else cap[surface]
    )
    target["currency"] = "EUR"
    with pytest.raises(cost.ReportError, match="UNSUPPORTED_CURRENCY"):
        cost.reconcile_invoice(cap)


def test_at_rest_fifo_rejected_before_leaf_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = private_inputs(tmp_path)
    (root / "invoice.json").unlink()
    os.mkfifo(root / "invoice.json")
    original = cost.os.open
    opened: list[object] = []

    def observe(path: object, flags: int, *args: object, **kwargs: object) -> int:
        opened.append(path)
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(cost.os, "open", observe)
    monkeypatch.setattr(cost.os, "supports_dir_fd", cost.os.supports_dir_fd | {observe})
    with pytest.raises(cost.ReportError):
        cost._read_inputs(str(root), "invoice.json", "bindings.json")
    assert "invoice.json" not in opened


def test_explicit_usd_context_and_absent_native_ids_preserve_accounting() -> None:
    cap = capture([{"product": "Taxes", "amount": "1.00", "currency": "USD"}], after=True)
    cap["invoice"]["currency"] = "USD"
    cap["invoice_after"]["currency"] = "USD"
    assert reconciled(cap, bindings([]))["accounting_status"] == "reconciled"


def test_absent_native_amount_never_becomes_a_zero_charge() -> None:
    with pytest.raises(cost.ReportError):
        cost.reconcile_invoice(capture([{"product": "Taxes"}], total="0"))


@pytest.mark.parametrize("case", ["no_links", "forward_only"])
def test_complete_counted_capture_accepts_optional_native_pagination_links(case: str) -> None:
    cap = capture([native_row()] * 2, total="2")
    pages = multipages([native_row()] * 2, per_page=1)
    cap["pages"] = pages
    if case == "no_links":
        for page in pages:
            page["response"].pop("links")
    else:
        pages[0]["response"]["links"]["pages"].pop("first")
        pages[1]["response"].pop("links")
    report = cost.reconcile_invoice(cap)
    assert report["accounting_status"] == "reconciled"
    assert report["row_count"] == 2 and report["total"] == "2.00"


@pytest.mark.parametrize("case", ["native_uuid", "wrong_id_only", "dual_identity"])
def test_volume_uses_native_uuid_without_identifier_fallback(case: str) -> None:
    row: dict[str, object] = {
        "product": "Volumes",
        "resource_id": "",
        "resource_uuid": "volume-native-uuid",
        "amount": "5.00",
        "duration": "744",
        "duration_unit": "Hours",
        "category": "iaas",
    }
    if case == "wrong_id_only":
        row["resource_id"], row["resource_uuid"] = "volume-native-uuid", ""
    elif case == "dual_identity":
        row["resource_id"] = "another-id"
    report = reconciled(
        capture([row], total="5.00"), bindings([binding("volume-native-uuid", "volume")])
    )
    assert report["total"] == "5.00" and report["row_count"] == 1
    assert report["allocation_status"] == ("complete" if case == "native_uuid" else "partial")
    if case == "native_uuid":
        assert objects(report["resource_groups"])[0]["resource_id"] == "volume-native-uuid"
        assert objects(report["rows"])[0]["bucket"] == "allocated"
    else:
        assert report["resource_groups"] == []
        assert objects(report["rows"])[0]["identity_status"] == (
            "missing" if case == "wrong_id_only" else "conflict"
        )


def test_uuid_volume_without_binding_does_not_reask_known_identity() -> None:
    row = {
        "product": "Volumes",
        "resource_id": "",
        "resource_uuid": "volume-native-uuid",
        "amount": "5.00",
    }
    report = reconciled(capture([row], total="5.00"), bindings([]))
    question = report["operator_summary"]["next_question"]
    assert "missing owner/service binding" in question
    assert "identity" not in question and "volume-native-uuid" not in question


def test_uuid_bearing_known_nonresource_product_requests_missing_context_only() -> None:
    row = {
        "product": "Uptime Health Check",
        "resource_id": "",
        "resource_uuid": "uptime-native-uuid",
        "amount": "0.00",
        "duration": "744",
        "duration_unit": "Hours",
        "category": "saas",
    }
    report = reconciled(capture([row], total="0.00"), bindings([]))
    assert report["allocation_status"] == "partial"
    assert objects(report["rows"])[0]["bucket"] == "unclassified"
    question = report["operator_summary"]["next_question"]
    assert "classification or association context" in question
    assert "product identity" not in question and "uptime-native-uuid" not in question
    assert report["resource_groups"] == [] and report["mutation_authority"] is False


@pytest.mark.parametrize("amount", ["1000.00", "0.01"])
def test_financial_context_does_not_inherit_ambient_exponents_or_behavior(amount: str) -> None:
    from decimal import ROUND_DOWN, Clamped, Inexact, Overflow, Rounded, Subnormal, Underflow

    with localcontext() as ambient:
        ambient.prec = 3
        ambient.Emax = 2
        ambient.Emin = -1
        ambient.rounding = ROUND_DOWN
        ambient.clamp = 1
        ambient.capitals = 0
        for signal in (Clamped, Inexact, Overflow, Rounded, Subnormal, Underflow):
            ambient.traps[signal] = True
            ambient.flags[signal] = True
        before = repr(ambient)
        report = reconciled(capture([native_row(amount=amount)], total=amount))
        if (
            report["total"] != amount
            or report["header_total"] != amount
            or report["residual"] != "0.00"
        ):
            pytest.fail("Exact financial output changed under hostile ambient Decimal context")
        assert report["accounting_status"] == "reconciled"
        assert repr(ambient) == before


def test_legal_million_digit_fixed_point_capture_and_cli_exceed_default_exponent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Adjusted exponent1,000,000 exceeds default999,999; both native amounts fit4MiB.
    amount = "1" + "0" * 1000000 + ".00"
    cap = capture([native_row(amount=amount)], total=amount)
    raw = json.dumps(cap).encode("utf-8")
    assert len(raw) < cost.MAX_BYTES
    report = reconciled(cap)
    if (
        report["total"] != amount
        or report["header_total"] != amount
        or report["residual"] != "0.00"
    ):
        pytest.fail("Legal byte-bounded wide capture did not reconcile exactly")
    if report["totals"]["allocated"] != amount:
        pytest.fail("Wide allocated bucket lost exactness")
    _, argv = private_inputs(tmp_path, cap)
    assert cost.main(argv) == 0
    output = capsys.readouterr()
    parsed = json.loads(output.out)
    if (
        parsed["total"] != amount
        or parsed["rows"][0]["amount"] != amount
        or parsed["residual"] != "0.00"
    ):
        pytest.fail("CLI output changed supported wide fixed-point money")
    assert output.err == ""
    assert parsed["currency"] == "USD" and parsed["accounting_status"] == "reconciled"
