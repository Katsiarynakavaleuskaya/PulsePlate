#!/usr/bin/env python3
"""Prepare and validate one strict advisory query; the shell owns scanner execution.

Only the byte-proven FastEmbed compatibility wheel may use upstream 0.8.0 as
an explicit advisory comparand. No private-version or universal safety claim
follows from that comparison. Intermediate files carry bytes, not authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import unquote, urljoin, urlparse

from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci import build_fastembed_compat_wheel as builder
from scripts.ci.compile_locked_python_requirements import _exact_pin_map
from scripts.ci.check_private_python_proxy_health import (
    _parse_simple_page_anchors,
    fetch_project_page,
    project_page_url,
    trusted_exact_pin_wheel_hashes,
    validate_index_url,
)
from scripts.ci.install_locked_python_requirements import (
    _admit_private_proxy_netrc_auth,
    resolve_private_proxy_settings,
)

PRIVATE_VERSION = "0.8.0+pulseplate.1"
SOURCE_SHA256 = "40bee672657574a1009e35ec50030a55f2b426842cb011845379817641bbbbd0"
PRIVATE_SHA256 = "3dd7642eb4d7ceecf208df4c9e290b08f14f28007b056ff81488810b9a366a45"
RECIPE_SHA256 = "d8c1f34ee1097236614913442b51156926d1bb6c15f854d429f95d72c94c8d41"
LOCK_LIMIT = 500_000
REPORT_LIMIT = 16 * 1024 * 1024


class AuditFailure(ValueError):
    """A constant diagnostic without credentials or untrusted payload text."""


def _hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _new_bytes(path: Path, content: bytes) -> None:
    parent = builder._directory_fd(path.parent)
    try:
        descriptor = os.open(
            path.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent,
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(parent)


def _projection(content: bytes) -> tuple[bytes, dict[str, str], dict[str, str], bool]:
    try:
        text = content.decode("utf-8")
        if any(line.split("#", 1)[0].strip().startswith("-") for line in text.splitlines()):
            raise AuditFailure("unsupported_requirement_directive")
        pins = _exact_pin_map(text, label="audit input")
    except (RuntimeError, UnicodeError, ValueError) as exc:
        raise AuditFailure("invalid_exact_requirement_inventory") from exc
    private = False
    original: dict[str, str] = {}
    for name, pin in pins.items():
        version = Version(pin.version)
        if pin.marker is not None or pin.url is not None:
            raise AuditFailure("unsupported_requirement_metadata")
        if version.local is not None:
            if name != "fastembed" or pin.version != PRIVATE_VERSION or pin.extras:
                raise AuditFailure("unsupported_private_dependency")
            private = True
        original[name] = str(version)
    comparand = dict(original)
    if private:
        lines = text.splitlines(keepends=True)
        selected = [
            i
            for i, line in enumerate(lines)
            if line.split("#", 1)[0].strip() == f"fastembed=={PRIVATE_VERSION}"
        ]
        if len(selected) != 1:
            raise AuditFailure("unsupported_private_requirement_carrier")
        index = selected[0]
        lines[index] = lines[index].replace(f"fastembed=={PRIVATE_VERSION}", "fastembed==0.8.0", 1)
        text = "".join(lines)
        comparand["fastembed"] = "0.8.0"
    return text.encode("utf-8"), original, comparand, private


def _acquire_pair(work_dir: Path) -> None:
    index, trusted_host = resolve_private_proxy_settings(index_url=None, trusted_host=None)
    index = validate_index_url(index)
    if trusted_host is not None:
        raise AuditFailure("verified_https_required")
    page = project_page_url(index, "fastembed")
    authorization = _admit_private_proxy_netrc_auth(parsed_url=urlparse(page), trusted_host=None)
    status, body = fetch_project_page(
        page, timeout_seconds=60, max_bytes=REPORT_LIMIT, authorization_header=authorization
    )
    if status != 200 or len(body) > REPORT_LIMIT:
        raise AuditFailure("private_project_page_failed")
    anchors, malformed = _parse_simple_page_anchors(body)
    if malformed:
        raise AuditFailure("private_project_page_malformed")
    for version, filename, size, digest in (
        ("0.8.0", builder.SOURCE_FILENAME, 116572, SOURCE_SHA256),
        (PRIVATE_VERSION, builder.OUTPUT_FILENAME, 116726, PRIVATE_SHA256),
    ):
        hashes = trusted_exact_pin_wheel_hashes(
            body=body, project_url=page, normalized_project="fastembed", expected_version=version
        )
        if hashes.get(filename.lower()) != digest:
            raise AuditFailure("private_wheel_advertised_digest_mismatch")
        links = [
            urljoin(page, anchor.href).split("#", 1)[0]
            for anchor in anchors
            if unquote(urlparse(anchor.href).path.rsplit("/", 1)[-1]).lower() == filename.lower()
        ]
        if len(links) != 1:
            raise AuditFailure("private_wheel_link_cardinality")
        status, wheel = fetch_project_page(
            links[0], timeout_seconds=60, max_bytes=size, authorization_header=authorization
        )
        if status != 200 or len(wheel) != size or _hash(wheel) != digest:
            raise AuditFailure("private_wheel_bytes_mismatch")
        _new_bytes(work_dir / filename, wheel)


def _prove_pair(work_dir: Path) -> dict[str, str]:
    recipe = builder._read_regular(builder.RECIPE_PATH, 8192)
    if _hash(recipe) != RECIPE_SHA256:
        raise AuditFailure("compat_recipe_changed")
    source = builder._read_regular(work_dir / builder.SOURCE_FILENAME, 116572)
    private = builder._read_regular(work_dir / builder.OUTPUT_FILENAME, 116726)
    if _hash(source) != SOURCE_SHA256 or _hash(private) != PRIVATE_SHA256:
        raise AuditFailure("compat_wheel_identity_changed")
    if builder._transform(source, builder._load_recipe()) != private:
        raise AuditFailure("compat_wheel_derivation_mismatch")
    if builder._read_regular(builder.RECIPE_PATH, 8192) != recipe:
        raise AuditFailure("compat_recipe_changed")
    return {
        "source_wheel_sha256": SOURCE_SHA256,
        "private_wheel_sha256": PRIVATE_SHA256,
        "recipe_sha256": RECIPE_SHA256,
    }


def prepare(manifest: Path, output: Path, work_dir: Path) -> None:
    """Capture original and query bytes; reserve fresh scanner output paths."""
    if any(
        os.path.lexists(path)
        for path in (
            output,
            output.with_suffix(".stderr.log"),
            output.with_suffix(".evidence.json"),
        )
    ):
        raise AuditFailure("stale_audit_output_exists")
    descriptor = builder._directory_fd(work_dir)
    try:
        if os.fstat(descriptor).st_mode & 0o077:
            raise AuditFailure("private_work_directory_required")
    finally:
        os.close(descriptor)
    original = builder._read_regular(manifest, LOCK_LIMIT)
    query, _, _, private = _projection(original)
    _new_bytes(work_dir / "original.txt", original)
    if private:
        _acquire_pair(work_dir)
        _prove_pair(work_dir)
    _new_bytes(work_dir / "comparand.txt", query)
    if builder._read_regular(manifest, LOCK_LIMIT) != original:
        raise AuditFailure("original_manifest_changed")
    _new_bytes(output, b"")
    _new_bytes(output.with_suffix(".stderr.log"), b"")
    home = work_dir / "scanner-home"
    home.mkdir(mode=0o700)


def _report_inventory(raw: bytes, expected: dict[str, str]) -> int:
    try:
        document = json.loads(
            raw,
            object_pairs_hook=builder._json_object,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (ValueError, UnicodeError) as exc:
        raise AuditFailure("invalid_scanner_json") from exc
    if (
        type(document) is not dict
        or set(document) != {"dependencies", "fixes"}
        or document["fixes"] != []
        or type(document["dependencies"]) is not list
    ):
        raise AuditFailure("invalid_scanner_report_shape")
    actual: dict[str, str] = {}
    findings = 0
    for row in document["dependencies"]:
        if (
            type(row) is not dict
            or set(row) != {"name", "version", "vulns"}
            or type(row["name"]) is not str
            or type(row["version"]) is not str
            or type(row["vulns"]) is not list
        ):
            raise AuditFailure("skipped_or_malformed_scanner_dependency")
        name, version = row["name"], row["version"]
        if name not in expected or name in actual or version != expected[name]:
            raise AuditFailure("scanner_inventory_mismatch")
        actual[name] = version
        for vulnerability in row["vulns"]:
            if (
                type(vulnerability) is not dict
                or not {"id", "fix_versions"} <= set(vulnerability)
                or not set(vulnerability) <= {"id", "fix_versions", "aliases", "description"}
            ):
                raise AuditFailure("malformed_scanner_finding")
            if (
                type(vulnerability["id"]) is not str
                or not vulnerability["id"]
                or type(vulnerability["fix_versions"]) is not list
                or any(type(value) is not str for value in vulnerability["fix_versions"])
            ):
                raise AuditFailure("malformed_scanner_finding")
            if "aliases" in vulnerability and (
                type(vulnerability["aliases"]) is not list
                or any(type(value) is not str for value in vulnerability["aliases"])
            ):
                raise AuditFailure("malformed_scanner_finding")
            if "description" in vulnerability and type(vulnerability["description"]) is not str:
                raise AuditFailure("malformed_scanner_finding")
            findings += 1
    if actual != expected:
        raise AuditFailure("scanner_inventory_mismatch")
    return findings


def validate(
    manifest: Path,
    output: Path,
    work_dir: Path,
    *,
    scanner_exit: int,
    scanner_version: str,
    auditor: str,
) -> bool:
    """Rebind actual inputs/provenance and raw report; never trust a prepared verdict."""
    original = builder._read_regular(work_dir / "original.txt", LOCK_LIMIT)
    if builder._read_regular(manifest, LOCK_LIMIT) != original:
        raise AuditFailure("original_manifest_changed")
    query, original_pins, query_pins, private = _projection(original)
    if builder._read_regular(work_dir / "comparand.txt", LOCK_LIMIT) != query:
        raise AuditFailure("comparand_bytes_changed")
    provenance = _prove_pair(work_dir) if private else None
    version_prefix = "pip-audit "
    if not scanner_version.startswith(version_prefix) or len(scanner_version) > 100:
        raise AuditFailure("scanner_version_unavailable")
    Version(scanner_version[len(version_prefix) :])
    raw = builder._read_regular(output, REPORT_LIMIT)
    stderr = builder._read_regular(output.with_suffix(".stderr.log"), REPORT_LIMIT)
    findings: int | None = None
    error: str | None = None
    try:
        findings = _report_inventory(raw, query_pins)
    except AuditFailure as exc:
        error = str(exc)
    passed = scanner_exit == 0 and error is None and findings == 0
    evidence = {
        "asset_type": "python_dependency_advisory_comparison",
        "policy_version": "fastembed-0.8.0-pulseplate.1-v1",
        "original_input_sha256": _hash(original),
        "comparand_input_sha256": _hash(query),
        "original_coordinates": original_pins,
        "query_coordinates": query_pins,
        "upstream_comparison": private,
        "private_version_directly_audited": False,
        "provenance": provenance,
        "scanner_version": scanner_version,
        "scanner_exit": scanner_exit,
        "scanner_argv": [
            auditor,
            "-r",
            str(work_dir / "comparand.txt"),
            "--no-deps",
            "--disable-pip",
            "--strict",
            "-f",
            "json",
            "-o",
            str(output),
        ],
        "raw_report_sha256": _hash(raw),
        "raw_stderr_sha256": _hash(stderr),
        "inventory_validation_error": error,
        "findings": findings,
        "passed": passed,
        "replay_admission": "new-output-only; existing output paths fail closed",
        "execution_evidence": "shell-reported exit; no independent execution attestation",
    }
    upstream_assets = [_hash(original), _hash(query), _hash(raw), _hash(stderr)]
    if provenance is not None:
        upstream_assets.extend(provenance.values())
    evidence["upstream_assets"] = upstream_assets
    evidence["idempotency_key"] = _hash(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    )
    evidence["fingerprint"] = _hash(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    )
    _new_bytes(
        output.with_suffix(".evidence.json"),
        (json.dumps(evidence, sort_keys=True, indent=2) + "\n").encode(),
    )
    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "validate"))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--scanner-exit", type=int)
    parser.add_argument("--scanner-version")
    parser.add_argument("--auditor")
    args = parser.parse_args(argv)
    try:
        if args.phase == "prepare":
            if any(
                value is not None
                for value in (args.scanner_exit, args.scanner_version, args.auditor)
            ):
                raise AuditFailure("prepare_rejects_terminal_metadata")
            prepare(args.manifest, args.output, args.work_dir)
            return 0
        if args.scanner_exit is None or args.scanner_version is None or args.auditor is None:
            raise AuditFailure("scanner_terminal_metadata_required")
        return (
            0
            if validate(
                args.manifest,
                args.output,
                args.work_dir,
                scanner_exit=args.scanner_exit,
                scanner_version=args.scanner_version,
                auditor=args.auditor,
            )
            else 1
        )
    except Exception as exc:
        detail = str(exc) if isinstance(exc, AuditFailure) else type(exc).__name__
        print(f"[ci_pip_audit] ERROR: comparison validation failed: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
