#!/usr/bin/env python3
"""
Parse Safety report JSON and generate a text summary.

Reads safety-report.json, writes safety-report.txt, prints summary,
and exits with appropriate status codes:
- 0: No vulnerabilities found
- 2: Medium/Low severity vulnerabilities found
- 10: High/Critical/Unknown severity vulnerabilities found (unknown treated as high risk)
- 99: Safety report JSON was not generated or could not be parsed
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict

report_path: Path = Path("safety-report.json")
summary_path: Path = Path("safety-report.txt")

if not report_path.exists():
    summary_path.write_text("Safety report JSON was not generated.\n")
    print("❌ Safety report JSON was not generated.")
    sys.exit(99)

try:
    data = json.loads(report_path.read_text())
except json.JSONDecodeError as e:
    summary_path.write_text(f"Failed to parse Safety report JSON: {e}\n")
    print(f"❌ JSON parsing error: {e}")
    sys.exit(99)
vulns = data.get("vulnerabilities", []) or []
ignored = data.get("ignored_vulnerabilities", []) or []


def base_severity(entry: Dict[str, Any]) -> str:
    """Extract base severity from a vulnerability entry."""
    severity = entry.get("severity") or {}
    for key in ("cvssv3", "cvssv2"):
        info = severity.get(key)
        if isinstance(info, dict):
            base = info.get("base_severity")
            if base:
                return str(base).upper()
    base = severity.get("max_severity") or severity.get("severity") or severity.get("level")
    if isinstance(base, str):
        return base.upper()
    return "UNKNOWN"


def build_lines() -> list[str]:
    """Build summary lines from vulnerability data."""
    lines = []
    if not vulns:
        lines.append("No vulnerabilities reported by Safety.")
    else:
        lines.append("Reported vulnerabilities:")
        for item in vulns:
            pkg = item.get("package_name") or "<unknown package>"
            version = item.get("analyzed_version") or ""
            vuln_id = item.get("vuln_id") or item.get("advisory_id") or ""
            severity = base_severity(item) or "UNKNOWN"
            advisory = (item.get("advisory") or "").strip()
            lines.append(f"- [{severity}] {pkg} {version} — {vuln_id}")
            if advisory:
                lines.append(f"    {advisory}")
    if ignored:
        lines.append("")
        lines.append(f"Ignored vulnerabilities: {len(ignored)} (see JSON for details)")
    return lines


lines = build_lines()
summary_path.write_text("\n".join(lines) + "\n")

high_or_critical = [
    item for item in vulns if base_severity(item) in {"HIGH", "CRITICAL", "UNKNOWN"}
]
medium_or_low = [
    item for item in vulns if base_severity(item) not in {"HIGH", "CRITICAL", "UNKNOWN"}
]

print("=== Safety Report Summary ===")
print("\n".join(lines))
print(f"\nHigh/Critical/Unknown findings: {len(high_or_critical)}")
print(f"Other findings: {len(medium_or_low)}")

if high_or_critical:
    sys.exit(10)
elif medium_or_low:
    sys.exit(2)
else:
    sys.exit(0)
