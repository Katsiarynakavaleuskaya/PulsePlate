"""CLI wrapper for the local execution sandbox.

RU: Тонкая CLI-обёртка для bounded local sandbox.
EN: Thin CLI wrapper for the bounded local sandbox.
"""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from app.security.execution_sandbox import SandboxRequest
from app.security.execution_sandbox import run_local_sandbox


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for sandbox execution."""

    parser = argparse.ArgumentParser(
        prog="run_local_sandbox",
        description="Run an allowlisted command inside the local execution sandbox.",
    )
    parser.add_argument("--binary", required=True, help="Allowlisted binary name, e.g. python3.")
    parser.add_argument(
        "--cwd",
        default=".",
        help="Working directory relative to sandbox root. Defaults to sandbox root.",
    )
    parser.add_argument(
        "--mode",
        default=None,
        help="Optional execution mode override (auto-safe, review-required, blocked).",
    )
    parser.add_argument(
        "--action",
        default="sandbox.exec",
        help="Policy action evaluated by the control plane allowlist.",
    )
    parser.add_argument(
        "--target",
        default="local://sandbox",
        help="Policy target evaluated by the control plane allowlist.",
    )
    parser.add_argument(
        "command_args",
        nargs=argparse.REMAINDER,
        help="Command arguments. Prefix with -- to stop argparse parsing.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested command and print deterministic JSON."""

    args = _parse_args(argv)
    command_args = tuple(args.command_args)
    if command_args[:1] == ("--",):
        command_args = command_args[1:]

    result = run_local_sandbox(
        SandboxRequest(
            binary=args.binary,
            args=command_args,
            cwd=args.cwd,
            mode=args.mode,
            action=args.action,
            target=args.target,
        )
    )
    print(
        json.dumps(
            {
                "argv": list(result.argv),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timed_out": result.timed_out,
                "truncated": result.truncated,
                "cwd": result.cwd,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
