#!/usr/bin/env python3
"""Check exact retained exceptions and util-linux retirement with native Trivy 0.74.0."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess  # nosec B404: fixed native Trivy CLI only (remove-by: 2026-10-28, ref: PR-2453)
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_POLICY = REPO_ROOT / "trivy/ignore-policy.rego"
SCAN_POLICY = REPO_ROOT / ".trivy-ignore-policy.rego"
TIMEOUT_SECONDS = 10
TUPLES = (
    ("CVE-2026-27171", "zlib1g", "1:1.2.13.dfsg-1", "1:1.3.dfsg+really1.3.2-3"),
    ("CVE-2025-69720", "libncursesw6", "6.4-4", "6.6+20260608-2"),
    ("CVE-2025-69720", "libtinfo6", "6.4-4", "6.6+20260608-2"),
    ("CVE-2025-69720", "ncurses-base", "6.4-4", "6.6+20260608-2"),
    ("CVE-2025-69720", "ncurses-bin", "6.4-4", "6.6+20260608-2"),
)

OPENSSL_VERSION = "3.0.22-1~deb12u1"
OPENSSL_TUPLES = (
    ("libssl3", "libssl3@3.0.22-1~deb12u1"),
    ("openssl", "openssl@3.0.22-1~deb12u1"),
)


def _policy_bytes(path: Path) -> bytes:
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError(f"Trivy policy must be a real single-link file: {path}")
        return path.read_bytes()
    except OSError as exc:
        raise ValueError(f"Unable to read Trivy policy: {path}") from exc


def _verify_policy_copy(source: Path, scan_copy: Path) -> None:
    if _policy_bytes(source) != _policy_bytes(scan_copy):
        raise ValueError("Trivy scan-policy copy differs from tracked policy")


def _trivy_binary() -> str:
    selected = shutil.which("trivy")
    if selected is None:
        raise ValueError("Native Trivy executable is missing")
    try:
        resolved = Path(selected).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("Unable to resolve native Trivy executable") from exc
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise ValueError("Native Trivy executable is not an executable file")
    return str(resolved)


def _invoke(argv: list[str], *, payload: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(  # nosec B603: absolute CLI and fixed argv, no shell (remove-by: 2026-10-28, ref: PR-2453)
            argv,
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=REPO_ROOT,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Native Trivy command timed out") from exc
    except OSError as exc:
        raise ValueError("Native Trivy command could not start") from exc


def _require_version(binary: str) -> None:
    result = _invoke([binary, "--version"])
    if result.returncode != 0 or result.stdout.splitlines()[:1] != [b"Version: 0.74.0"]:
        raise ValueError("Native Trivy must be exactly version 0.74.0")


def _report_bytes(finding: dict[str, object]) -> bytes:
    report = {
        "SchemaVersion": 2,
        "ArtifactName": "synthetic",
        "ArtifactType": "filesystem",
        "Results": [
            {
                "Target": "fixture",
                "Class": "os-pkgs",
                "Type": "debian",
                "Vulnerabilities": [finding],
            }
        ],
    }
    return (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _validate_output(raw: bytes, finding: dict[str, object], expected_count: int) -> None:
    try:
        report = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Native Trivy returned invalid JSON") from exc
    if not isinstance(report, dict) or set(report) != {
        "SchemaVersion",
        "ArtifactName",
        "ArtifactType",
        "Results",
    }:
        raise ValueError("Native Trivy returned an unexpected report shape")
    if (
        type(report["SchemaVersion"]) is not int
        or report["SchemaVersion"] != 2
        or report["ArtifactName"] != "synthetic"
        or report["ArtifactType"] != "filesystem"
        or not isinstance(report["Results"], list)
        or len(report["Results"]) != 1
    ):
        raise ValueError("Native Trivy returned a different report identity")
    row = report["Results"][0]
    if not isinstance(row, dict) or not {"Target", "Class", "Type"} <= set(row):
        raise ValueError("Native Trivy returned an invalid result row")
    if (
        row["Target"] != "fixture"
        or row["Class"] != "os-pkgs"
        or row["Type"] != "debian"
        or set(row) - {"Target", "Class", "Type", "Vulnerabilities"}
    ):
        raise ValueError("Native Trivy returned a different result identity")
    vulnerabilities = row.get("Vulnerabilities", [])
    if not isinstance(vulnerabilities, list) or len(vulnerabilities) != expected_count:
        raise ValueError("Native Trivy returned an unexpected finding count")
    expected_finding = dict(finding)
    if expected_finding.get("FixedVersion") in (None, ""):
        expected_finding.pop("FixedVersion", None)
    if expected_count == 1 and vulnerabilities != [expected_finding]:
        raise ValueError("Native Trivy returned a different finding identity")


def _cases() -> list[tuple[str, dict[str, object], int | None]]:
    cases: list[tuple[str, dict[str, object], int | None]] = []
    for cve, package, version, fixed in TUPLES:
        exact: dict[str, object] = {
            "VulnerabilityID": cve,
            "PkgName": package,
            "PkgID": f"{package}@{version}",
            "InstalledVersion": version,
            "Severity": "HIGH",
            "Title": "synthetic fixture",
        }
        prefix = f"{cve}/{package}"
        cases.extend(
            (
                (f"{prefix}/missing", exact, 0),
                (f"{prefix}/empty", {**exact, "FixedVersion": ""}, 0),
                (f"{prefix}/null", {**exact, "FixedVersion": None}, 0),
                (f"{prefix}/nonempty", {**exact, "FixedVersion": fixed}, 1),
                (f"{prefix}/wrong-cve", {**exact, "VulnerabilityID": "CVE-0000-0000"}, 1),
                (f"{prefix}/wrong-package", {**exact, "PkgName": "other"}, 1),
                (f"{prefix}/wrong-version", {**exact, "InstalledVersion": "other"}, 1),
                (f"{prefix}/wrong-pkgid", {**exact, "PkgID": "other@0"}, 1),
                (f"{prefix}/integer", {**exact, "FixedVersion": 7}, None),
            )
        )
    return cases


def _openssl_cases() -> list[tuple[str, dict[str, object], int | None]]:
    """Challenge both ordered pairs without interpreting Rego in Python."""
    cases: list[tuple[str, dict[str, object], int | None]] = []
    for package, pkgid in OPENSSL_TUPLES:
        exact: dict[str, object] = {
            "VulnerabilityID": "CVE-2026-84782",
            "PkgName": package,
            "PkgID": pkgid,
            "InstalledVersion": OPENSSL_VERSION,
            "Severity": "HIGH",
            "Title": "synthetic fixture",
        }
        other_pkgid = next(value for name, value in OPENSSL_TUPLES if name != package)
        prefix = f"CVE-2026-84782/{package}"
        cases.extend(
            (
                (f"{prefix}/missing", exact, 0),
                (f"{prefix}/empty", {**exact, "FixedVersion": ""}, 0),
                (f"{prefix}/null", {**exact, "FixedVersion": None}, 0),
                (f"{prefix}/wrong-cve", {**exact, "VulnerabilityID": "CVE-0000-0000"}, 1),
                (f"{prefix}/wrong-package", {**exact, "PkgName": "other"}, 1),
                (f"{prefix}/wrong-version", {**exact, "InstalledVersion": "other"}, 1),
                (f"{prefix}/wrong-pkgid", {**exact, "PkgID": "other@0"}, 1),
                (f"{prefix}/cross-pair", {**exact, "PkgID": other_pkgid}, 1),
                (f"{prefix}/pkgid-prefix", {**exact, "PkgID": f"prefix/{pkgid}"}, 1),
                (f"{prefix}/pkgid-suffix", {**exact, "PkgID": f"{pkgid}:suffix"}, 1),
                (f"{prefix}/pkgid-lookalike", {**exact, "PkgID": f"{pkgid}0"}, 1),
                (f"{prefix}/nonempty", {**exact, "FixedVersion": "3.0.23"}, 1),
                (f"{prefix}/fixed-text", {**exact, "FixedVersion": "fixed metadata"}, 1),
                (f"{prefix}/fixed-whitespace", {**exact, "FixedVersion": " "}, 1),
                (f"{prefix}/critical", {**exact, "Severity": "CRITICAL"}, 1),
                (f"{prefix}/integer", {**exact, "FixedVersion": 7}, None),
                (f"{prefix}/float", {**exact, "FixedVersion": 7.5}, None),
                (f"{prefix}/bool", {**exact, "FixedVersion": True}, None),
                (f"{prefix}/array", {**exact, "FixedVersion": []}, None),
                (f"{prefix}/object", {**exact, "FixedVersion": {}}, None),
            )
        )
    return cases


def _identity_cases() -> list[tuple[str, dict[str, object], int | None]]:
    """Challenge each legacy identity and every ncurses off-diagonal pair."""
    cases: list[tuple[str, dict[str, object], int | None]] = []
    for cve, package, version, _fixed in TUPLES:
        exact: dict[str, object] = {
            "VulnerabilityID": cve,
            "PkgName": package,
            "PkgID": f"{package}@{version}",
            "InstalledVersion": version,
            "Severity": "HIGH",
            "Title": "synthetic fixture",
        }
        pkgid = f"{package}@{version}"
        prefix = f"{cve}/{package}"
        cases.extend(
            (
                (f"{prefix}/pkgid-prefix", {**exact, "PkgID": f"prefix/{pkgid}"}, 1),
                (f"{prefix}/pkgid-suffix", {**exact, "PkgID": f"{pkgid}:suffix"}, 1),
                (f"{prefix}/pkgid-lookalike", {**exact, "PkgID": f"{pkgid}0"}, 1),
            )
        )
        if cve == "CVE-2025-69720":
            for other_cve, other_package, other_version, _ in TUPLES:
                if other_cve == cve and other_package != package:
                    cases.append(
                        (
                            f"{prefix}/cross-pair-{other_package}",
                            {**exact, "PkgID": f"{other_package}@{other_version}"},
                            1,
                        )
                    )
        else:
            cases.append(
                (
                    f"{prefix}/pkgid-combined-affix",
                    {**exact, "PkgID": f"prefix/{pkgid}:suffix"},
                    1,
                )
            )
    return cases


def _retired_util_linux_cases() -> list[tuple[str, dict[str, object], int | None]]:
    """All eight historical Debian tuples must remain visible after retirement."""
    cases: list[tuple[str, dict[str, object], int | None]] = []
    for package in (
        "bsdutils",
        "libblkid1",
        "libmount1",
        "libsmartcols1",
        "libuuid1",
        "mount",
        "util-linux",
        "util-linux-extra",
    ):
        version = "1:2.38.1-5+deb12u3" if package == "bsdutils" else "2.38.1-5+deb12u3"
        finding: dict[str, object] = {
            "VulnerabilityID": "CVE-2026-53615",
            "PkgName": package,
            "PkgID": f"{package}@{version}",
            "InstalledVersion": version,
            "Severity": "HIGH",
            "Title": "synthetic fixture",
        }
        # Omit FixedVersion: native empty/null decoding omits that output field.
        cases.append((f"CVE-2026-53615/{package}/retired", finding, 1))
    return cases


def _run_contract(binary: str, scan_copy: Path) -> int:
    argv = [
        binary,
        "convert",
        "--quiet",
        "--format",
        "json",
        "--ignore-policy",
        str(scan_copy),
        "--ignorefile",
        "/dev/null",
        "/dev/stdin",
    ]
    cases = _cases() + _openssl_cases() + _identity_cases() + _retired_util_linux_cases()
    for case_id, finding, expected in cases:
        result = _invoke(argv, payload=_report_bytes(finding))
        if expected is None:
            diagnostic = result.stderr.decode("utf-8", errors="replace")
            if (
                result.returncode == 0
                or result.stdout.strip()
                or "json decode error" not in diagnostic
                or "FixedVersion" not in diagnostic
                or "of type string" not in diagnostic
            ):
                raise ValueError(f"{case_id}: expected native FixedVersion type rejection")
            continue
        if result.returncode != 0:
            raise ValueError(f"{case_id}: native Trivy conversion failed")
        _validate_output(result.stdout, finding, expected)
    return len(cases)


def main() -> int:
    try:
        _verify_policy_copy(SOURCE_POLICY, SCAN_POLICY)
        binary = _trivy_binary()
        _require_version(binary)
        case_count = _run_contract(binary, SCAN_POLICY)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Native Trivy suppression contract passed: {case_count} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
