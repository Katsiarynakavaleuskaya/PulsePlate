#!/usr/bin/env python3
"""Run the canonical multi-manifest Safety dependency audit."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess  # nosec B404: Safety CLI execution is the bounded CI audit purpose (remove-by: 2026-07-31, ref: ledger-p1-safety-audit-shared-script-after-pr1479)
import sys
import tempfile
from typing import Any, Mapping, Sequence

REQUIRED_MANIFEST = "requirements.txt"
OPTIONAL_MANIFESTS: tuple[str, ...] = (
    "requirements-docker-runtime.txt",
    "requirements-rag-vector.txt",
    "requirements-rag-vector-cpu.txt",
)
HIGH_RISK_SEVERITIES = {"HIGH", "CRITICAL", "UNKNOWN"}
SAFETY_BINARY = "safety"
SAFETY_AUTH_ENV = "SAFETY_" + "API_KEY"
DEFAULT_SAFETY_STAGE = "cicd"
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
    safety_stage: str


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
    discovered_manifests = [required]
    discovered_manifests.extend(
        root / name for name in OPTIONAL_MANIFESTS if (root / name).is_file()
    )
    return tuple(discovered_manifests)


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


def _version_from_spec(spec: object) -> str:
    """Best-effort version extraction from a package specification string."""

    if not isinstance(spec, str):
        return ""
    for operator in ("===", "==", ">=", "<=", "~=", "!=", ">", "<"):
        if operator in spec:
            return spec.split(operator, maxsplit=1)[1].strip()
    return ""


def _scan_vulnerability_severity(vulnerability: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a legacy-compatible severity mapping for Safety scan v3 reports."""

    severity = vulnerability.get("severity")
    if isinstance(severity, Mapping):
        return severity

    cve = vulnerability.get("CVE") or vulnerability.get("cve")
    if isinstance(cve, Mapping):
        cvssv3 = cve.get("cvssv3")
        if isinstance(cvssv3, Mapping):
            return {"cvssv3": cvssv3}
        cvssv2 = cve.get("cvssv2")
        if isinstance(cvssv2, Mapping):
            return {"cvssv2": cvssv2}

    ignored = vulnerability.get("ignored")
    if isinstance(ignored, Mapping):
        reason = ignored.get("reason")
        if isinstance(reason, str) and "severity" in reason.lower():
            return {"severity": reason}
    return {}


def _legacy_entry_from_scan_vulnerability(
    *,
    dependency: Mapping[str, Any],
    specification: Mapping[str, Any],
    vulnerability: Mapping[str, Any],
    file_location: str,
) -> dict[str, Any]:
    """Convert one Safety scan v3 vulnerability to the legacy parser shape."""

    raw_spec = specification.get("raw") or vulnerability.get("vulnerable_spec") or ""
    return {
        "package_name": dependency.get("name") or "<unknown package>",
        "analyzed_version": _version_from_spec(vulnerability.get("vulnerable_spec") or raw_spec),
        "vuln_id": vulnerability.get("id") or vulnerability.get("vuln_id") or "",
        "advisory": vulnerability.get("advisory") or f"Found in {file_location}: {raw_spec}",
        "severity": _scan_vulnerability_severity(vulnerability),
    }


def _normalize_scan_v3_report(
    payload: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """Extract active and ignored vulnerabilities from Safety scan v3 JSON."""

    scan_results = payload.get("scan_results")
    if not isinstance(scan_results, Mapping):
        raise SafetyAuditError("Safety scan report missing scan_results object.", PARSE_ERROR)

    projects = scan_results.get("projects")
    if not isinstance(projects, list):
        raise SafetyAuditError(
            "Safety scan report scan_results.projects must be a list.", PARSE_ERROR
        )

    vulnerabilities: list[Mapping[str, Any]] = []
    ignored_vulnerabilities: list[Mapping[str, Any]] = []
    for project in projects:
        if not isinstance(project, Mapping):
            raise SafetyAuditError(
                "Safety scan report project entries must be objects.", PARSE_ERROR
            )
        files = project.get("files", [])
        if files is None:
            files = []
        if not isinstance(files, list):
            raise SafetyAuditError("Safety scan report project files must be a list.", PARSE_ERROR)
        for scanned_file in files:
            if not isinstance(scanned_file, Mapping):
                raise SafetyAuditError(
                    "Safety scan report file entries must be objects.", PARSE_ERROR
                )
            file_location = str(scanned_file.get("location") or "<unknown file>")
            results = scanned_file.get("results") or {}
            if not isinstance(results, Mapping):
                raise SafetyAuditError(
                    "Safety scan report file results must be objects.", PARSE_ERROR
                )
            dependencies = results.get("dependencies", [])
            if dependencies is None:
                dependencies = []
            if not isinstance(dependencies, list):
                raise SafetyAuditError(
                    "Safety scan report file dependencies must be a list.",
                    PARSE_ERROR,
                )
            for dependency in dependencies:
                if not isinstance(dependency, Mapping):
                    raise SafetyAuditError(
                        "Safety scan report dependency entries must be objects.",
                        PARSE_ERROR,
                    )
                specifications = dependency.get("specifications", [])
                if specifications is None:
                    specifications = []
                if not isinstance(specifications, list):
                    raise SafetyAuditError(
                        "Safety scan report dependency specifications must be a list.",
                        PARSE_ERROR,
                    )
                for specification in specifications:
                    if not isinstance(specification, Mapping):
                        raise SafetyAuditError(
                            "Safety scan report specification entries must be objects.",
                            PARSE_ERROR,
                        )
                    spec_vulnerabilities = specification.get("vulnerabilities") or {}
                    if not isinstance(spec_vulnerabilities, Mapping):
                        raise SafetyAuditError(
                            "Safety scan report specification vulnerabilities must be objects.",
                            PARSE_ERROR,
                        )
                    known = spec_vulnerabilities.get("known_vulnerabilities", [])
                    if known is None:
                        known = []
                    if not isinstance(known, list):
                        raise SafetyAuditError(
                            "Safety scan report known_vulnerabilities must be a list.",
                            PARSE_ERROR,
                        )
                    for vulnerability in known:
                        if not isinstance(vulnerability, Mapping):
                            raise SafetyAuditError(
                                "Safety scan vulnerability entries must be objects.",
                                PARSE_ERROR,
                            )
                        entry = _legacy_entry_from_scan_vulnerability(
                            dependency=dependency,
                            specification=specification,
                            vulnerability=vulnerability,
                            file_location=file_location,
                        )
                        if vulnerability.get("ignored"):
                            ignored_vulnerabilities.append(entry)
                        else:
                            vulnerabilities.append(entry)

    return vulnerabilities, ignored_vulnerabilities


def normalized_vulnerabilities(
    payload: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """Return active and ignored vulnerabilities for supported Safety report schemas."""

    if isinstance(payload.get("scan_results"), Mapping):
        return _normalize_scan_v3_report(payload)

    vulnerabilities = payload.get("vulnerabilities", [])
    if vulnerabilities is None:
        vulnerabilities = []
    ignored = payload.get("ignored_vulnerabilities", [])
    if ignored is None:
        ignored = []
    if not isinstance(vulnerabilities, list):
        raise SafetyAuditError("Safety report vulnerabilities field must be a list.", PARSE_ERROR)
    if not isinstance(ignored, list):
        raise SafetyAuditError(
            "Safety report ignored_vulnerabilities field must be a list.", PARSE_ERROR
        )
    if not all(isinstance(item, Mapping) for item in vulnerabilities):
        raise SafetyAuditError("Safety report vulnerability entries must be objects.", PARSE_ERROR)
    if not all(isinstance(item, Mapping) for item in ignored):
        raise SafetyAuditError(
            "Safety report ignored vulnerability entries must be objects.", PARSE_ERROR
        )
    return vulnerabilities, ignored


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

    if not isinstance(payload, Mapping):
        message = f"Safety report JSON must be an object, got {type(payload).__name__}."
        summary_path.write_text(f"{message}\n", encoding="utf-8")
        raise SafetyAuditError(message, PARSE_ERROR)

    try:
        vulnerabilities, ignored = normalized_vulnerabilities(payload)
    except SafetyAuditError as exc:
        message = str(exc)
        summary_path.write_text(f"{message}\n", encoding="utf-8")
        raise

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


def _manifest_reference_paths(manifest: Path) -> tuple[Path, ...]:
    """Return local requirement/constraint files referenced by a manifest."""

    references: list[Path] = []
    for raw_line in manifest.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not parts:
            continue
        option = parts[0]
        if option in {"-r", "--requirement", "-c", "--constraint"} and len(parts) >= 2:
            references.append((manifest.parent / parts[1]).resolve())
        elif option.startswith(("-r", "-c")) and len(option) > 2:
            references.append((manifest.parent / option[2:]).resolve())
    return tuple(references)


def _prepare_scan_target(root: Path, manifest: Path, target_dir: Path) -> Path:
    """Copy one manifest and its local requirement references into a scan target."""

    root_resolved = root.resolve()
    paths = [manifest.resolve()]
    paths.extend(_manifest_reference_paths(manifest))
    for source in paths:
        if root_resolved not in (source, *source.parents):
            raise SafetyAuditError(f"Safety manifest reference escapes repo root: {source}")
        if not source.is_file():
            raise SafetyAuditError(f"Safety manifest reference not found: {source}")
        destination = target_dir / source.relative_to(root_resolved)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return target_dir


def _require_scan_auth(stage: str) -> None:
    """Fail before invoking Safety scan when CI authentication is missing."""

    if stage in {"cicd", "production"} and not os.environ.get(SAFETY_AUTH_ENV):
        raise SafetyAuditError(
            "SAFETY_API_KEY is required for Safety scan in cicd/production stage. "
            "Add the GitHub Actions secret and expose it to this job as SAFETY_API_KEY.",
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
    for artifact_path in (report_json, report_txt, console_log):
        artifact_path.unlink(missing_ok=True)

    print(f"Running Safety scan for {manifest.name}")
    _require_scan_auth(config.safety_stage)
    with tempfile.TemporaryDirectory(prefix=f"pulseplate-safety-{stem}-") as temp_root:
        scan_target = _prepare_scan_target(config.root, manifest, Path(temp_root))
        command = [
            config.safety_binary,
            "--stage",
            config.safety_stage,
            "--disable-optional-telemetry",
            "scan",
            "--target",
            str(scan_target),
            "--output",
            "json",
            "--save-as",
            "json",
            str(report_json),
            *config.policy_file_args,
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
        report_txt.write_text(f"{message}\n", encoding="utf-8")
        raise SafetyAuditError(message, completed.returncode or 1)

    analysis = analyze_report(report_json, report_txt)
    if completed.returncode != 0 and analysis.status == PARSE_OK:
        message = (
            f"Safety exited with code {completed.returncode} for {manifest.name}, "
            "but the report contained no parsed vulnerabilities."
        )
        report_txt.write_text(f"{message}\n", encoding="utf-8")
        raise SafetyAuditError(message, completed.returncode)

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
    safety_stage: str = DEFAULT_SAFETY_STAGE,
) -> SafetyAuditConfig:
    """Build and validate Safety audit runtime configuration."""

    output_dir.mkdir(parents=True, exist_ok=True)
    return SafetyAuditConfig(
        root=root,
        output_dir=output_dir,
        manifests=discover_manifests(root, manifest_names),
        policy_file_args=policy_args(root, policy_file),
        safety_binary=safety_binary_path(safety_binary),
        safety_stage=safety_stage,
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
    parser.add_argument(
        "--safety-stage",
        default=DEFAULT_SAFETY_STAGE,
        choices=("development", "cicd", "production"),
        help="Safety lifecycle stage for scan execution.",
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
            safety_stage=args.safety_stage,
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
            print(f"OK: Safety scan passed for {manifest_name}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
