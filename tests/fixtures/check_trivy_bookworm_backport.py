"""Run synthetic backport policy controls against the pinned native Trivy CLI."""

from __future__ import annotations

import asyncio
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import time

from scripts.ci import check_trivy_ignore_policy_native as report_helpers

_VERSION = "0.76.2"
_RELEASE_SHA256 = {
    ("linux", "x86_64"): "6a972c69606c7b3ea4c6bdcc6fc9332ea9ad38381624310c1e85cc77345909f3",
    ("darwin", "arm64"): "7a15c426f963473a485a4f315e21f8e2c881269d500bf0de35da13a4421fa108",
}
_RETIRED_POLICY = b"package trivy\n\nimport rego.v1\n\ndefault ignore := false\n"
BACKPORT_CVE = "CVE-2026-124851"
BACKPORT_VERSION = "1.5.7+dfsg-1+deb13u1~pulseplate12+1"
BACKPORT_CUTOFF = "2026-12-27T00:00:00Z"
_PACKAGE_UID = "e0ce9bfa57379d11"
_PACKAGE_PURL = (
    "pkg:deb/debian/libzstd1@1.5.7%2Bdfsg-1%2Bdeb13u1~pulseplate12%2B1"
    "?arch=amd64&distro=debian-12.15"
)
_DATA_SOURCE = {
    "ID": "debian",
    "Name": "Debian Security Tracker",
    "URL": "https://salsa.debian.org/security-tracker-team/security-tracker",
}
_TIMEOUT_SECONDS = 10


def _verified_binary() -> str:
    expected = _RELEASE_SHA256.get((sys.platform, platform.machine()))
    selected = shutil.which("trivy")
    if expected is None or selected is None:
        raise ValueError("Verified Trivy 0.76.2 requires Linux amd64 or macOS arm64")
    binary = Path(selected).resolve(strict=True)
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError("Trivy path is not a regular executable")
    with binary.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError("Native Trivy 0.76.2 executable SHA-256 differs")
    return str(binary)


async def _invoke(
    binary: str, args: tuple[str, ...], private: Path, payload: bytes | None = None
) -> tuple[int, bytes, bytes]:
    process = await asyncio.create_subprocess_exec(
        binary,
        *args,
        stdin=asyncio.subprocess.DEVNULL if payload is None else asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=private,
        env={
            "PATH": "/usr/bin:/bin",
            "LANG": "C",
            "LC_ALL": "C",
            "HOME": str(private),
            "XDG_CACHE_HOME": str(private / "cache"),
            "TMPDIR": str(private / "tmp"),
        },
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(payload), _TIMEOUT_SECONDS)
    except TimeoutError as exc:
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise ValueError("Native Trivy command timed out") from exc
    if process.returncode is None:
        raise ValueError("Native Trivy command has no exit status")
    return process.returncode, stdout, stderr


async def _convert(
    binary: str, policy: Path, private: Path, payload: bytes
) -> tuple[int, bytes, bytes]:
    return await _invoke(
        binary,
        (
            "convert",
            "--quiet",
            "--format",
            "json",
            "--ignore-policy",
            str(policy),
            "--ignorefile",
            "/dev/null",
            "/dev/stdin",
        ),
        private,
        payload,
    )


async def _check_case(
    binary: str,
    policy: Path,
    private: Path,
    case_id: str,
    finding: dict[str, object],
    expected: int | None,
) -> None:
    code, stdout, stderr = await _convert(
        binary, policy, private, report_helpers._report_bytes(finding)
    )
    if expected is None:
        if (
            code == 0
            or stdout.strip()
            or not all(
                token in stderr
                for token in (b"json decode error", b"FixedVersion", b"of type string")
            )
        ):
            raise ValueError(f"{case_id}: expected native FixedVersion type rejection")
        return
    if code != 0:
        raise ValueError(f"{case_id}: native Trivy conversion failed")
    # Trivy serializes an omitted input severity as UNKNOWN.
    normalized = {"Severity": "UNKNOWN", **finding}
    try:
        report_helpers._validate_output(stdout, normalized, expected)
    except ValueError as exc:
        raise ValueError(f"{case_id}: {exc}") from exc


def _backport_finding() -> dict[str, object]:
    return {
        "VulnerabilityID": BACKPORT_CVE,
        "PkgName": "libzstd1",
        "PkgID": f"libzstd1@{BACKPORT_VERSION}",
        "InstalledVersion": BACKPORT_VERSION,
        "PkgIdentifier": {"PURL": _PACKAGE_PURL, "UID": _PACKAGE_UID},
        "DataSource": dict(_DATA_SOURCE),
        "Severity": "HIGH",
        "Status": "affected",
    }


def _backport_negatives() -> list[tuple[str, dict[str, object], int | None]]:
    exact = _backport_finding()
    cases: list[tuple[str, dict[str, object], int | None]] = []
    for field, replacement in (
        ("VulnerabilityID", "CVE-2026-85091"),
        ("PkgName", "another-package"),
        ("PkgID", "libzstd1@1.5.4+dfsg2-5"),
        ("InstalledVersion", "1.5.4+dfsg2-5"),
        ("Severity", "CRITICAL"),
        ("Status", "fixed"),
    ):
        cases.append((f"wrong-{field}", {**exact, field: replacement}, 1))
        cases.append((f"missing-{field}", {k: v for k, v in exact.items() if k != field}, 1))

    cases.append(("missing-PURL", {**exact, "PkgIdentifier": {"UID": _PACKAGE_UID}}, 1))
    for dimension, old, new in (
        ("architecture", "arch=amd64", "arch=arm64"),
        ("distro", "debian-12.15", "debian-13.1"),
        ("namespace", "pkg:deb/debian/", "pkg:deb/ubuntu/"),
    ):
        different = {"PURL": _PACKAGE_PURL.replace(old, new), "UID": _PACKAGE_UID}
        cases.append((f"wrong-PURL-{dimension}", {**exact, "PkgIdentifier": different}, 1))

    for field, value in _DATA_SOURCE.items():
        different = {**_DATA_SOURCE, field: f"{value}-different"}
        omitted = {k: v for k, v in _DATA_SOURCE.items() if k != field}
        cases.append((f"wrong-vendor-{field}", {**exact, "DataSource": different}, 1))
        cases.append((f"missing-vendor-{field}", {**exact, "DataSource": omitted}, 1))

    cases.extend(
        (
            (
                "older-package",
                {
                    **exact,
                    "PkgID": "libzstd1@1.5.4+dfsg2-5",
                    "InstalledVersion": "1.5.4+dfsg2-5",
                    "PkgIdentifier": {
                        "PURL": "pkg:deb/debian/libzstd1@1.5.4%2Bdfsg2-5"
                        "?arch=amd64&distro=debian-12.15",
                        "UID": _PACKAGE_UID,
                    },
                },
                1,
            ),
            ("available-fix", {**exact, "FixedVersion": "1.5.4+dfsg2-6"}, 1),
            ("nonempty-whitespace-fix", {**exact, "FixedVersion": " "}, 1),
            ("malformed-fix-type", {**exact, "FixedVersion": 7}, None),
        )
    )
    return cases


async def _check_backport_mixed_report(
    binary: str, policy: Path, private: Path, *, active: bool
) -> None:
    exact = _backport_finding()
    other = {**report_helpers._visible_source_cases()[0][1], "Severity": "HIGH"}
    report = json.loads(report_helpers._report_bytes(other))
    report["Results"][0]["Secrets"] = [
        {
            "RuleID": "synthetic-fixture",
            "Category": "fixture",
            "Severity": "HIGH",
            "Title": "synthetic finding",
            "StartLine": 1,
            "EndLine": 1,
            "Code": {"Lines": None},
            "Match": "synthetic only",
        },
    ]
    report["Results"][0]["Vulnerabilities"].append(exact)
    code, stdout, _ = await _convert(binary, policy, private, json.dumps(report).encode())
    if code != 0:
        raise ValueError("backport mixed report: native Trivy conversion failed")
    if active:
        report["Results"][0]["Vulnerabilities"].pop()
    try:
        actual = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("backport mixed report: native Trivy returned invalid JSON") from exc
    if actual != report:
        raise ValueError("backport mixed report: unexpected finding or secret inventory")


async def _run_backport_contract(binary: str, scan_copy: Path, private: Path) -> int:
    policy = report_helpers._policy_bytes(scan_copy)
    if policy == _RETIRED_POLICY:
        await _check_case(binary, scan_copy, private, "retired", _backport_finding(), 1)
        return 1
    clock = b"time.now_ns()"
    bound = f'time.now_ns() < time.parse_rfc3339_ns("{BACKPORT_CUTOFF}")'.encode()
    if policy.count(clock) != 1 or policy.count(bound) != 1:
        raise ValueError("Expected exactly one strict native backport cutoff")
    cutoff_ns = int(datetime.fromisoformat(BACKPORT_CUTOFF).timestamp()) * 1_000_000_000
    active = time.time_ns() < cutoff_ns
    exact = _backport_finding()
    positives = (
        ("native-current-missing-fix", exact),
        ("native-current-empty-fix", {**exact, "FixedVersion": ""}),
        ("native-current-null-fix", {**exact, "FixedVersion": None}),
    )
    for label, finding in positives:
        await _check_case(binary, scan_copy, private, label, finding, 0 if active else 1)
    negatives = _backport_negatives()
    for case in negatives:
        await _check_case(binary, scan_copy, private, *case)
    await _check_backport_mixed_report(binary, scan_copy, private, active=active)

    # The disposable copies change only the clock expression, leaving the
    # actual Rego cutoff comparison and native evaluation intact.
    boundary = (
        ("cutoff-minus-one-ns", cutoff_ns - 1, 0),
        ("cutoff-exact", cutoff_ns, 1),
        ("cutoff-plus-one-ns", cutoff_ns + 1, 1),
    )
    for label, observed_ns, expected in boundary:
        fixed_clock_policy = private / f"{label}.rego"
        fixed_clock_policy.write_bytes(policy.replace(clock, str(observed_ns).encode(), 1))
        await _check_case(binary, fixed_clock_policy, private, label, exact, expected)
    return len(positives) + len(negatives) + len(boundary) + 1  # mixed report


async def _main() -> int:
    repo = Path(__file__).resolve().parents[2]
    policy = repo / ".trivy-ignore-policy.rego"
    report_helpers._verify_policy_copy(repo / "trivy/ignore-policy.rego", policy)
    binary = _verified_binary()
    with tempfile.TemporaryDirectory(prefix="pulseplate-trivy-bookworm-") as directory:
        private = Path(directory).resolve(strict=True)
        (private / "tmp").mkdir(mode=0o700)
        (private / "cache").mkdir(mode=0o700)
        code, stdout, _ = await _invoke(binary, ("--version",), private)
        if code != 0 or stdout.splitlines()[:1] != [f"Version: {_VERSION}".encode()]:
            raise ValueError(f"Native Trivy must be exactly version {_VERSION}")
        return await _run_backport_contract(binary, policy, private)


def main() -> int:
    try:
        count = asyncio.run(_main())
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Native Bookworm backport scope and cutoff controls passed: {count} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
