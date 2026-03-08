"""CLI wrapper for the local execution sandbox.

RU: Тонкая CLI-обёртка для bounded local sandbox.
EN: Thin CLI wrapper for the bounded local sandbox.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import NoReturn, Sequence

from app.security.execution_sandbox import SandboxRequest
from app.security.execution_sandbox import run_local_sandbox


class _JsonArgumentParser(argparse.ArgumentParser):
    """Argument parser that fails without emitting usage text to stderr."""

    def error(self, message: str) -> NoReturn:
        raise ValueError(f"CLI argument error: {message}")


def _emit_payload(payload: dict[str, object]) -> None:
    """Print deterministic JSON payload for sandbox CLI consumers."""

    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def _error_payload(
    *,
    argv: Sequence[str],
    cwd: str,
    error: str,
    returncode: int = 1,
) -> dict[str, object]:
    """Build deterministic error payload matching the success shape."""

    return {
        "argv": list(argv),
        "returncode": returncode,
        "stdout": "",
        "stderr": error,
        "timed_out": False,
        "truncated": False,
        "cwd": cwd,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for sandbox execution."""

    parser = _JsonArgumentParser(
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
        help="Optional stricter execution mode request; runtime config remains the upper bound.",
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

    request: SandboxRequest | None = None
    request_argv = tuple(argv if argv is not None else sys.argv[1:])
    request_cwd = "."
    try:
        args = _parse_args(argv)
        command_args = tuple(args.command_args)
        if command_args[:1] == ("--",):
            command_args = command_args[1:]

        request = SandboxRequest(
            binary=args.binary,
            args=command_args,
            cwd=args.cwd,
            mode=args.mode,
            action=args.action,
            target=args.target,
        )
        result = run_local_sandbox(request)
    except Exception as exc:
        if request is not None:
            request_argv = (request.binary, *request.args)
            request_cwd = str(request.cwd or ".")
        _emit_payload(
            _error_payload(
                argv=request_argv,
                cwd=request_cwd,
                error=str(exc),
            )
        )
        return 1

    _emit_payload(
        {
            "argv": list(result.argv),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
            "truncated": result.truncated,
            "cwd": result.cwd,
        }
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
