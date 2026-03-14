#!/usr/bin/env python3
"""Canonical orchestration wrapper for merge-readiness gates."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess  # nosec B404: wrapper executes fixed repo scripts only (remove-by: 2026-06-30, ref: PR-1005)
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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


@dataclass(frozen=True)
class GatePolicy:
    """Static gate classification used by the wrapper output."""

    gate_class: Literal["hard", "soft", "external", "advisory"]
    lane: Literal[
        "pr-governance", "review-governance", "required-checks", "review-proof", "unclassified"
    ]
    blocking: bool


GATE_POLICIES: dict[str, GatePolicy] = {
    "phase2-pr-body-gates": GatePolicy(gate_class="hard", lane="pr-governance", blocking=True),
    "merge-readiness-gate": GatePolicy(gate_class="hard", lane="review-governance", blocking=True),
    "current-head-checks": GatePolicy(gate_class="hard", lane="required-checks", blocking=True),
    "review-threads-disposition": GatePolicy(gate_class="hard", lane="review-proof", blocking=True),
}

BLOCKING_MERGE_READY_GATES: tuple[str, ...] = (
    "phase2-pr-body-gates",
    "merge-readiness-gate",
    "current-head-checks",
    "review-threads-disposition",
)


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


def _github_cli_path() -> str:
    """Resolve gh binary path for read-only PR metadata access."""

    gh_path = shutil.which("gh")
    if not gh_path:
        raise RuntimeError("GitHub CLI `gh` is required to fetch PR body in local mode.")
    return gh_path


def _fetch_pr_body(pr_number: int, repo: str) -> str:
    """Fetch live PR body so Phase2 mirror checks work in local wrapper mode."""

    env = os.environ.copy()
    if not (env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")):
        auth_status = subprocess.run(  # nosec B603: absolute gh path with fixed auth-status argv (remove-by: 2026-06-30, ref: PR-1129)
            [_github_cli_path(), "auth", "status"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=RUN_TIMEOUT_SEC,
            env=env,
        )
        if auth_status.returncode != 0:
            stderr = (
                auth_status.stderr.strip() or auth_status.stdout.strip() or "unknown gh auth error"
            )
            raise RuntimeError(
                "GH_TOKEN/GITHUB_TOKEN is unset and gh auth status failed; "
                f"run `gh auth login` or export GH_TOKEN. Details: {stderr}"
            )
    argv = [
        _github_cli_path(),
        "pr",
        "view",
        str(pr_number),
        "--repo",
        repo,
        "--json",
        "body",
        "--jq",
        ".body",
    ]
    result = subprocess.run(  # nosec B603: absolute gh path with fixed read-only argv (remove-by: 2026-06-30, ref: PR-1129)
        argv,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=RUN_TIMEOUT_SEC,
        env=env,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown gh error"
        raise RuntimeError(f"Failed to fetch PR body for #{pr_number}: {stderr}")
    return result.stdout


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

    policy = GATE_POLICIES.get(
        result.name,
        GatePolicy(gate_class="advisory", lane="unclassified", blocking=False),
    )
    status = "PASS" if result.returncode == 0 else "FAIL"
    blocking_label = "blocking" if policy.blocking else "advisory"
    print(
        f"[{status}] {result.name} " f"({policy.gate_class}; lane={policy.lane}; {blocking_label})"
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)


def _print_merge_ready_bundle() -> None:
    """Render the canonical blocking bundle before gate execution output."""

    print("Blocking merge-ready bundle:")
    for gate_name in BLOCKING_MERGE_READY_GATES:
        policy = GATE_POLICIES[gate_name]
        blocking_value = "yes" if policy.blocking else "no"
        print(
            f"- {gate_name}: class={policy.gate_class}, "
            f"lane={policy.lane}, blocking={blocking_value}"
        )
    print("Advisory / external signals:")
    print("- third-party review bots remain advisory unless GitHub branch protection promotes them")


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

    phase2_args = _phase2_args(parsed)
    phase2_result = _run_gate("phase2-pr-body-gates", PHASE2_GATE, phase2_args)

    gate_results = [
        phase2_result,
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
    _print_merge_ready_bundle()
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
