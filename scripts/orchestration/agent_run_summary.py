"""Generate deterministic agent run summary artifact (JSON).

Single-path: philosophy_validator + optional static docs scan.
Exit 0 = PASS, 1 = REWRITE_REQUIRED (BLOCKER or failed static scans).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

# Canonical wellness guard marker (same meaning as docs guard)
IN_FILE_ALLOW_MARKER = "pulseplate-allow:blocker-example"

# Minimal BLOCKER patterns for static docs scan (aligned with tests/guards)
_BLOCKER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "WELLNESS_MEDICAL_CLAIM_RU",
        re.compile(
            r"\b(лечит|вылечит|вылечим|исцелит|диагноз|диагностирую|диагностирует)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "WELLNESS_MEDICAL_CLAIM_EN",
        re.compile(
            r"\b(we\s+cure|we\s+diagnose|will\s+cure|will\s+diagnose"
            r"|cures?\s+your|cures?\s+the)\b",
            re.IGNORECASE,
        ),
    ),
]


def _repo_root() -> Path:
    # scripts/orchestration/agent_run_summary.py -> repo root = parents[2]
    return Path(__file__).resolve().parents[2]


def _sha12(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def compute_run_id(agent: str, domain: str, task_type: str, text: str) -> str:
    """Deterministic run ID from inputs."""
    payload = f"agent={agent}\ndomain={domain}\ntask_type={task_type}\ntext={text}"
    return _sha12(payload)


def read_text_from_stdin() -> str:
    return sys.stdin.read().strip("\n")


def read_text_from_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip("\n")


def _load_allowlist(repo_root: Path) -> list[str]:
    allow_path = repo_root / "tests" / "guards" / "wellness_language_allowlist.txt"
    if not allow_path.exists():
        return []
    patterns: list[str] = []
    for raw in allow_path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        patterns.append(s)
    return patterns


def _is_allowlisted(path_rel: str, line: str, allow_regexes: list[str]) -> bool:
    target = f"{path_rel}::{line}"
    for rx in allow_regexes:
        if re.search(rx, target, flags=re.IGNORECASE):
            return True
    return False


def scan_docs_for_wellness_blockers(
    repo_root: Path,
    *,
    scan_root: Path | None = None,
    max_findings: int = 50,
) -> dict[str, Any]:
    """Deterministic static scan of docs/ for BLOCKER medical claims."""
    if scan_root is None:
        scan_root = repo_root / "docs"
    if not scan_root.exists():
        return {"ok": True, "findings_count": 0, "findings": []}

    allow_regexes = _load_allowlist(repo_root)
    findings: list[dict[str, Any]] = []

    text_exts = {".md", ".txt", ".yml", ".yaml", ".json", ".py", ".ts", ".tsx"}
    exclude_dirs = {".git", ".venv", "node_modules", "dist", "build", "worktrees"}

    for path in sorted(scan_root.rglob("*")):
        if path.is_dir():
            continue
        if any(part in exclude_dirs for part in path.parts):
            continue
        if path.suffix.lower() not in text_exts:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        path_rel = path.relative_to(repo_root).as_posix()

        for line_no, line in enumerate(content.splitlines(), start=1):
            if IN_FILE_ALLOW_MARKER in line:
                continue

            for code, pattern in _BLOCKER_PATTERNS:
                if pattern.search(line):
                    if _is_allowlisted(path_rel, line, allow_regexes):
                        continue
                    findings.append(
                        {
                            "code": code,
                            "path": path_rel,
                            "line_no": line_no,
                            "line": line.strip()[:240],
                        }
                    )
                    if len(findings) >= max_findings:
                        break
            if len(findings) >= max_findings:
                break
        if len(findings) >= max_findings:
            break

    ok = len(findings) == 0
    return {"ok": ok, "findings_count": len(findings), "findings": findings}


def validate_text_with_philosophy_validator(text: str, *, domain: str) -> dict[str, Any]:
    """Wrap core.insight.philosophy_validator, return JSON-safe dict."""
    from core.insight.philosophy_validator import validate_llm_output

    report = validate_llm_output(text, domain=domain)
    issues = []
    for b in getattr(report, "blockers", []):
        d = asdict(b) if hasattr(b, "__dataclass_fields__") else dict(b)
        d["severity"] = "BLOCKER"
        issues.append(d)
    ok = bool(getattr(report, "ok", True))
    return {"ok": ok, "summary": {"blockers_count": len(issues)}, "issues": issues}


def decide_action(philosophy_ok: bool, max_severity: str, static_ok: bool) -> dict[str, Any]:
    action = "PASS"
    if not static_ok:
        action = "REWRITE_REQUIRED"
    if not philosophy_ok or max_severity == "BLOCKER":
        action = "REWRITE_REQUIRED"
    return {"action": action, "max_severity": max_severity}


def _max_severity_from_issues(issues: list[dict[str, Any]]) -> str:
    order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "BLOCKER": 4}
    max_sev = "LOW"
    for it in issues:
        sev = str(it.get("severity", "LOW"))
        if sev in order and order[sev] > order[max_sev]:
            max_sev = sev
    return max_sev


def build_summary(
    *,
    agent: str,
    domain: str,
    task_type: str,
    text: str,
    run_id: str | None,
    static_scan_docs: bool,
) -> dict[str, Any]:
    """Build full summary dict (deterministic)."""
    repo_root = _repo_root()

    rid = run_id or compute_run_id(agent, domain, task_type, text)

    philosophy = validate_text_with_philosophy_validator(text, domain=domain)
    max_sev = _max_severity_from_issues(philosophy.get("issues", []))

    static_scans: dict[str, Any] = {}
    static_ok = True
    if static_scan_docs:
        docs_scan = scan_docs_for_wellness_blockers(repo_root)
        static_scans["wellness_language_guard_docs"] = docs_scan
        static_ok = bool(docs_scan.get("ok", True))

    decision = decide_action(
        philosophy_ok=bool(philosophy.get("ok", True)),
        max_severity=max_sev,
        static_ok=static_ok,
    )

    return {
        "run_id": rid,
        "agent": agent,
        "domain": domain,
        "task_type": task_type,
        "inputs": {"text_len": len(text)},
        "philosophy_validator": philosophy,
        "static_scans": static_scans,
        "decision": decision,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="agent_run_summary",
        description="Generate deterministic agent run summary artifact (JSON).",
    )
    p.add_argument("--agent", required=True)
    p.add_argument("--domain", required=True)
    p.add_argument("--task-type", required=True)
    p.add_argument(
        "--run-id",
        default=None,
        help="Optional. If omitted, deterministic hash-based id is used.",
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text-file", type=str, default=None, help="Read input text from file.")
    g.add_argument("--stdin", action="store_true", help="Read input text from stdin.")
    p.add_argument(
        "--scan-docs", action="store_true", help="Run static docs wellness blockers scan."
    )
    p.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write JSON to this file. If omitted, prints to stdout.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    text = read_text_from_file(Path(args.text_file)) if args.text_file else read_text_from_stdin()

    summary = build_summary(
        agent=args.agent,
        domain=args.domain,
        task_type=args.task_type,
        text=text,
        run_id=args.run_id,
        static_scan_docs=bool(args.scan_docs),
    )

    payload = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)

    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    return 0 if summary["decision"]["action"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
