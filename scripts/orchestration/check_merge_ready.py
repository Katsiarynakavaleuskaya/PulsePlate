#!/usr/bin/env python3
"""Canonical orchestration wrapper for merge-readiness gates."""

from __future__ import annotations

import argparse
import subprocess  # nosec B404: wrapper executes fixed repo scripts only (remove-by: 2026-06-30, ref: PR-1005)
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PHASE2_GATE = REPO_ROOT / "scripts" / "ci" / "check_pr_body_phase2_gates.py"
MERGE_GATE = REPO_ROOT / "scripts" / "ci" / "check_pr_merge_readiness.py"
DISPOSITION_GATE = REPO_ROOT / "scripts" / "orchestration" / "check_review_threads_disposition.py"


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
    result = subprocess.run(  # nosec B603: fixed interpreter/script paths; args validated by parser (remove-by: 2026-06-30, ref: PR-1005)
        argv,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
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


def _disposition_args(args: argparse.Namespace) -> list[str]:
    disposition_args: list[str] = []
    if args.pr_number is not None:
        disposition_args.extend(["--pr-number", str(args.pr_number)])
    if args.require_auth:
        disposition_args.append("--require-auth")
    return disposition_args


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
        help="Require GH_TOKEN for disposition guard even outside CI.",
    )
    parsed = parser.parse_args(argv)
    _validate_args(parsed, parser)

    gate_results = [
        _run_gate("phase2-pr-body-gates", PHASE2_GATE, _phase2_args(parsed)),
        _run_gate("merge-readiness-gate", MERGE_GATE, _merge_gate_args(parsed)),
        _run_gate(
            "review-threads-disposition",
            DISPOSITION_GATE,
            _disposition_args(parsed),
        ),
    ]

    failed = [result.name for result in gate_results if result.returncode != 0]
    for result in gate_results:
        _print_gate_output(result)

    if failed:
        print("ERROR: orchestration merge-check failed.")
        print(f"Failing gates: {', '.join(failed)}")
        return 1

    print("orchestration-merge-check: passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
