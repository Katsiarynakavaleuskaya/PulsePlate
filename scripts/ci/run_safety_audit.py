#!/usr/bin/env python3
"""Run the canonical multi-manifest Safety dependency audit."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess  # nosec B404: Safety CLI execution is the bounded CI audit purpose (remove-by: 2026-07-31, ref: ledger-p1-safety-audit-shared-script-after-pr1479)
import sys
from typing import Any, Mapping, Sequence

REQUIRED_MANIFEST = "requirements.txt"
OPTIONAL_MANIFESTS: tuple[str, ...] = (
    "requirements-docker-runtime.txt",
    "requirements-rag-vector.txt",
)
HIGH_RISK_SEVERITIES = {"HIGH", "CRITICAL", "UNKNOWN"}
SAFETY_BINARY = "safety"
PARSE_OK = 0
PARSE_WARNING = 2
PARSE_BLOCKING = 10
PARSE_ERROR = 99


class SafetyAuditError(RuntimeError):
    """Fail-closed Safety audit error."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class SafetyAnalysis:
    """Parsed Safety report severity summary."""

    status: int
    high_risk_count: int
    other_count: int
    lines: tuple[str, ...]


@dataclass(frozen=True)
class ManifestAuditResult:
    """Audit result and artifact paths for one requirements manifest."""

    manifest: Path
    report_json: Path
    report_txt: Path
    console_log: Path
    safety_exit_code: int
    analysis: SafetyAnalysis


@dataclass(frozen=True)
class SafetyAuditConfig:
    """Runtime configuration for the canonical Safety audit."""

    root: Path
    output_dir: Path
    manifests: tuple[Path, ...]
    policy_file_args: tuple[str, ...]
    safety_binary: str


def artifact_stem(manifest: Path) -> str:
    """Return the stable artifact stem for a requirements manifest."""

    name = manifest.name
    return name.removesuffix(".txt")


def discover_manifests(root: Path, manifest_names: Sequence[str] | None = None) -> tuple[Path, ...]:
    """Return Safety manifest paths, failing closed when requested files are missing."""

    names = tuple(manifest_names or ())
    if names:
        manifests = tuple(root / name for name in names)
        missing = [path.name for path in manifests if not path.is_file()]
        if missing:
            missing_list = ", ".join(missing)
            raise SafetyAuditError(f"Safety manifest(s) not found: {missing_list}")
        return manifests

    required = root / REQUIRED_MANIFEST
    if not required.is_file():
        raise SafetyAuditError(
            "ERROR: requirements.txt not found. Safety scan requires requirements.txt.",
        )
    manifests = [required]
    manifests.extend(root / name for name in OPTIONAL_MANIFESTS if (root / name).is_file())
    return tuple(manifests)


def policy_args(root: Path, policy_file: str | None = None) -> tuple[str, ...]:
    """Return Safety policy-file args, preferring YAML over TOML."""

    if policy_file is not None:
        policy_path = root / policy_file
        if not policy_path.is_file():
            raise SafetyAuditError(f"Safety policy file not found: {policy_file}")
        return ("--policy-file", str(policy_path))

    yaml_policy = root / "safety-policy.yaml"
    if yaml_policy.is_file():
        return ("--policy-file", str(yaml_policy))
    toml_policy = root / "safety-policy.toml"
    if toml_policy.is_file():
        return ("--policy-file", str(toml_policy))
    print("WARNING: safety-policy.yaml not found; running Safety without a policy file.")
    return ()


def safety_binary_path(binary_name: str = SAFETY_BINARY) -> str:
    """Resolve the Safety CLI path for subprocess execution."""

    safety_path = shutil.which(binary_name)
    if safety_path is None:
        raise SafetyAuditError(f"Safety CLI is not available on PATH: {binary_name}")
    return safety_path


def base_severity(entry: Mapping[str, Any]) -> str:
    """Extract a normalized severity from a Safety vulnerability entry."""

    severity = entry.get("severity") or {}
    if isinstance(severity, Mapping):
        for key in ("cvssv3", "cvssv2"):
            info = severity.get(key)
            if isinstance(info, Mapping):
                base = info.get("base_severity")
                if base:
                    return str(base).upper()
        base = severity.get("max_severity") or severity.get("severity") or severity.get("level")
        if isinstance(base, str):
            return base.upper()
    return "UNKNOWN"


def build_summary_lines(
    vulnerabilities: Sequence[Mapping[str, Any]], ignored: Sequence[object]
) -> tuple[str, ...]:
    """Build deterministic human-readable Safety summary lines."""

    lines: list[str] = []
    if not vulnerabilities:
        lines.append("No vulnerabilities reported by Safety.")
    else:
        lines.append("Reported vulnerabilities:")
        for item in vulnerabilities:
            package = item.get("package_name") or "<unknown package>"
            version = item.get("analyzed_version") or ""
            vuln_id = item.get("vuln_id") or item.get("advisory_id") or ""
            severity = base_severity(item)
            advisory = str(item.get("advisory") or "").strip()
            lines.append(f"- [{severity}] {package} {version} - {vuln_id}")
            if advisory:
                lines.append(f"    {advisory}")
    if ignored:
        lines.append("")
        lines.append(f"Ignored vulnerabilities: {len(ignored)} (see JSON for details)")
    return tuple(lines)


def analyze_report(report_path: Path, summary_path: Path) -> SafetyAnalysis:
    """Parse one Safety JSON report, write summary text, and return severity status."""

    if not report_path.is_file() or report_path.stat().st_size == 0:
        summary_path.write_text("Safety report JSON was not generated.\n", encoding="utf-8")
        raise SafetyAuditError("Safety report JSON was not generated.", PARSE_ERROR)

    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        summary_path.write_text(f"Failed to parse Safety report JSON: {exc}\n", encoding="utf-8")
        raise SafetyAuditError(f"Failed to parse Safety report JSON: {exc}", PARSE_ERROR) from exc

    vulnerabilities = payload.get("vulnerabilities", []) or []
    ignored = payload.get("ignored_vulnerabilities", []) or []
    if not isinstance(vulnerabilities, list):
        raise SafetyAuditError("Safety report vulnerabilities field must be a list.", PARSE_ERROR)
    if not isinstance(ignored, list):
        ignored = []

    lines = build_summary_lines(vulnerabilities, ignored)
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    high_risk_count = sum(
        1 for item in vulnerabilities if base_severity(item) in HIGH_RISK_SEVERITIES
    )
    other_count = len(vulnerabilities) - high_risk_count
    if high_risk_count:
        status = PARSE_BLOCKING
    elif other_count:
        status = PARSE_WARNING
    else:
        status = PARSE_OK
    return SafetyAnalysis(
        status=status,
        high_risk_count=high_risk_count,
        other_count=other_count,
        lines=lines,
    )


def run_safety_for_manifest(
    *,
    config: SafetyAuditConfig,
    manifest: Path,
) -> ManifestAuditResult:
    """Run Safety and parse artifacts for one requirements manifest."""

    stem = artifact_stem(manifest)
    report_json = config.output_dir / f"safety-{stem}.json"
    report_txt = config.output_dir / f"safety-{stem}.txt"
    console_log = config.output_dir / f"safety-{stem}.log"
    print(f"Running Safety audit for {manifest.name}")
    command = [
        config.safety_binary,
        "check",
        *config.policy_file_args,
        "--json",
        "-r",
        str(manifest),
        "--save-json",
        str(report_json),
    ]
    completed = subprocess.run(  # nosec B603: argv uses resolved Safety CLI and manifest paths from canonical discovery only (remove-by: 2026-07-31, ref: ledger-p1-safety-audit-shared-script-after-pr1479)
        command,
        cwd=config.root,
        capture_output=True,
        text=True,
        check=False,
    )
    console_log.write_text((completed.stdout or "") + (completed.stderr or ""), encoding="utf-8")
    if console_log.stat().st_size > 0:
        print(f"=== Raw Safety Output ({manifest.name}) ===")
        print(console_log.read_text(encoding="utf-8"), end="")

    if not report_json.is_file() or report_json.stat().st_size == 0:
        message = (
            f"Safety failed to produce {report_json.name} for {manifest.name} "
            f"(exit code: {completed.returncode})"
        )
        raise SafetyAuditError(message, completed.returncode or 1)

    analysis = analyze_report(report_json, report_txt)
    print("=== Safety Report Summary ===")
    print("\n".join(analysis.lines))
    print(f"\nHigh/Critical/Unknown findings: {analysis.high_risk_count}")
    print(f"Other findings: {analysis.other_count}")
    return ManifestAuditResult(
        manifest=manifest,
        report_json=report_json,
        report_txt=report_txt,
        console_log=console_log,
        safety_exit_code=completed.returncode,
        analysis=analysis,
    )


def build_config(
    *,
    root: Path,
    output_dir: Path,
    manifest_names: Sequence[str] | None = None,
    policy_file: str | None = None,
    safety_binary: str = SAFETY_BINARY,
) -> SafetyAuditConfig:
    """Build and validate Safety audit runtime configuration."""

    output_dir.mkdir(parents=True, exist_ok=True)
    return SafetyAuditConfig(
        root=root,
        output_dir=output_dir,
        manifests=discover_manifests(root, manifest_names),
        policy_file_args=policy_args(root, policy_file),
        safety_binary=safety_binary_path(safety_binary),
    )


def run_audit(config: SafetyAuditConfig) -> tuple[ManifestAuditResult, ...]:
    """Run the canonical multi-manifest Safety audit and return all results."""

    results: list[ManifestAuditResult] = []
    for manifest in config.manifests:
        results.append(
            run_safety_for_manifest(
                config=config,
                manifest=manifest,
            )
        )
    return tuple(results)


def exit_code_for_results(results: Sequence[ManifestAuditResult]) -> int:
    """Return aggregate workflow exit code for parsed Safety results."""

    if any(result.analysis.status == PARSE_BLOCKING for result in results):
        return 1
    return 0


def parse_legacy_report(report_path: Path, summary_path: Path) -> int:
    """Compatibility entrypoint for the historical parse-safety-report.py wrapper."""

    try:
        analysis = analyze_report(report_path, summary_path)
    except SafetyAuditError as exc:
        print(str(exc))
        return exc.exit_code
    print("=== Safety Report Summary ===")
    print("\n".join(analysis.lines))
    print(f"\nHigh/Critical/Unknown findings: {analysis.high_risk_count}")
    print(f"Other findings: {analysis.other_count}")
    return analysis.status


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root containing requirements manifests and output artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory where safety-*.json/txt/log artifacts are written.",
    )
    parser.add_argument(
        "--manifest",
        action="append",
        dest="manifests",
        help="Requirement manifest to audit. Repeat to override default discovery.",
    )
    parser.add_argument(
        "--policy-file",
        help="Explicit Safety policy file relative to --root.",
    )
    parser.add_argument(
        "--safety-binary",
        default=SAFETY_BINARY,
        help="Safety executable name or path.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for GitHub workflows."""

    args = _parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(args.root).resolve()
    output_dir = root if args.output_dir is None else Path(args.output_dir).resolve()
    try:
        config = build_config(
            root=root,
            output_dir=output_dir,
            manifest_names=args.manifests,
            policy_file=args.policy_file,
            safety_binary=args.safety_binary,
        )
        results = run_audit(config)
    except SafetyAuditError as exc:
        print(f"ERROR: {exc}")
        return exc.exit_code

    exit_code = exit_code_for_results(results)
    for result in results:
        manifest_name = result.manifest.name
        if result.analysis.status == PARSE_BLOCKING:
            print(f"ERROR: Safety found high/critical/unknown vulnerabilities in {manifest_name}")
        elif result.analysis.status == PARSE_WARNING:
            print(
                f"WARNING: Safety reported vulnerabilities below HIGH severity in {manifest_name}"
            )
        else:
            print(f"OK: Safety check passed for {manifest_name}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
