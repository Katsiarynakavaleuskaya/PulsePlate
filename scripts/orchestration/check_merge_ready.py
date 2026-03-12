#!/usr/bin/env python3
"""Canonical orchestration wrapper for merge-readiness gates."""

from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404: wrapper executes fixed repo scripts only (remove-by: 2026-06-30, ref: PR-1005)
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PHASE2_GATE = REPO_ROOT / "scripts" / "ci" / "check_pr_body_phase2_gates.py"
MERGE_GATE = REPO_ROOT / "scripts" / "ci" / "check_pr_merge_readiness.py"
CURRENT_HEAD_CHECKS_GATE = REPO_ROOT / "scripts" / "ci" / "check_current_head_pr_checks.py"
DISPOSITION_GATE = REPO_ROOT / "scripts" / "orchestration" / "check_review_threads_disposition.py"
RUN_TIMEOUT_SEC = 120


@dataclass(frozen=True)
class GateResult:
    """Result of one gate subprocess."""

    name: str
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str


def _validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Enforce CI vs local mode contract for the wrapper CLI."""

    has_event = bool((args.event_path or "").strip())
    has_local_pr = args.pr_number is not None or bool((args.repo or "").strip())

    if has_event and has_local_pr:
        parser.error(
            "Use either --event-path (CI) or both --pr-number and --repo (local), not both."
        )

    if has_event:
        return

    if (args.pr_number is not None) != bool((args.repo or "").strip()):
        parser.error("For local mode provide both --pr-number and --repo.")

    if args.pr_number is None and not (args.repo or "").strip():
        parser.error("Provide either --event-path (CI) or both --pr-number and --repo (local).")


def _run_gate(name: str, script_path: Path, extra_args: list[str]) -> GateResult:
    """Run a gate script and capture its output without mutating its behavior."""

    argv = [sys.executable, str(script_path), *extra_args]
    try:
        result = subprocess.run(  # nosec B603: fixed interpreter/script paths; args validated by parser (remove-by: 2026-06-30, ref: PR-1005)
            argv,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=RUN_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "").strip() if isinstance(exc.stdout, str) else ""
        return GateResult(
            name=name,
            argv=argv,
            returncode=1,
            stdout=stdout,
            stderr=f"Timed out after {RUN_TIMEOUT_SEC}s while running {script_path.name}: {exc}",
        )
    return GateResult(
        name=name,
        argv=argv,
        returncode=result.returncode,
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
    )


def _phase2_args(args: argparse.Namespace) -> list[str]:
    if args.event_path:
        return ["--event-path", args.event_path]
    phase2_args = ["--pr-number", str(args.pr_number)]
    if args.body:
        phase2_args.extend(["--body", args.body])
    return phase2_args


def _merge_gate_args(args: argparse.Namespace) -> list[str]:
    if args.event_path:
        return ["--event-path", args.event_path]
    return ["--pr-number", str(args.pr_number), "--repo", args.repo]


def _current_head_checks_args(args: argparse.Namespace) -> list[str]:
    if args.event_path:
        return ["--event-path", args.event_path]
    return ["--pr-number", str(args.pr_number), "--repo", args.repo]


def _event_pr_number(event_path: str) -> int | None:
    """Extract PR number from a GitHub event payload for deterministic CI routing."""

    if not event_path.strip():
        return None
    try:
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        return None
    pr_number = pull_request.get("number")
    if isinstance(pr_number, bool) or pr_number is None:
        return None
    if isinstance(pr_number, int):
        return pr_number
    if isinstance(pr_number, str) and pr_number.isdigit():
        return int(pr_number)
    return None


def _disposition_args(args: argparse.Namespace) -> list[str]:
    disposition_args: list[str] = []
    disposition_pr_number = args.pr_number
    if disposition_pr_number is None:
        disposition_pr_number = _event_pr_number(args.event_path)
    if disposition_pr_number is not None:
        disposition_args.extend(["--pr-number", str(disposition_pr_number)])
    if args.require_auth:
        disposition_args.append("--require-auth")
    return disposition_args


def _disposition_gate_skipped(result: GateResult) -> bool:
    """True when disposition exited 0 via advisory SKIP instead of strict evidence."""

    if result.name != "review-threads-disposition":
        return False
    if result.returncode != 0:
        return False
    combined_output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    return "SKIP:" in combined_output


def _print_gate_output(result: GateResult) -> None:
    """Render one gate block for deterministic local/CI diagnostics."""

    status = "PASS" if result.returncode == 0 else "FAIL"
    print(f"[{status}] {result.name}")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run canonical PR governance gates and emit a single merge verdict."
    )
    parser.add_argument(
        "--event-path",
        default="",
        help="Path to GitHub event payload JSON for CI mode.",
    )
    parser.add_argument(
        "--body",
        default="",
        help="Explicit PR body text for local Phase2 validation.",
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        help="PR number for local mode (must be paired with --repo).",
    )
    parser.add_argument(
        "--repo",
        default="",
        help="Repo full name owner/repo for local mode.",
    )
    parser.add_argument(
        "--require-auth",
        action="store_true",
        help="Upgrade local disposition checks to strict CI-like auth semantics.",
    )
    parsed = parser.parse_args(argv)
    _validate_args(parsed, parser)

    gate_results = [
        _run_gate("phase2-pr-body-gates", PHASE2_GATE, _phase2_args(parsed)),
        _run_gate("merge-readiness-gate", MERGE_GATE, _merge_gate_args(parsed)),
        _run_gate(
            "current-head-checks",
            CURRENT_HEAD_CHECKS_GATE,
            _current_head_checks_args(parsed),
        ),
        _run_gate(
            "review-threads-disposition",
            DISPOSITION_GATE,
            _disposition_args(parsed),
        ),
    ]

    failed = [result.name for result in gate_results if result.returncode != 0]
    disposition_skipped = any(_disposition_gate_skipped(result) for result in gate_results)
    if disposition_skipped:
        failed.append("review-threads-disposition")
    for result in gate_results:
        _print_gate_output(result)

    if failed:
        if "review-threads-disposition" in failed and disposition_skipped:
            print("ERROR: review-threads-disposition ran in advisory SKIP mode.")
            print("Re-run with --require-auth and GH_TOKEN for merge-readiness evidence.")
        print("ERROR: orchestration merge-check failed.")
        unique_failed = list(dict.fromkeys(failed))
        print(f"Failing gates: {', '.join(unique_failed)}")
        return 1

    print("orchestration-merge-check: passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
