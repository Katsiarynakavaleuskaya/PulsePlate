#!/usr/bin/env python3
"""Diagnose host-only Codex + Ollama operator setup.

This script is intentionally read-only. It checks local tool availability and
prints actionable guidance, but it never writes host config such as
``~/.codex/config.toml``.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess  # nosec B404: required for bounded local CLI version checks (remove-by: 2026-08-15, ref: PR-WALK3-OLLAMA-CODEX)
import sys
from dataclasses import asdict, dataclass
from typing import Sequence
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

MIN_OLLAMA_LAUNCH_VERSION = (0, 15, 0)
DEFAULT_OLLAMA_URL = "http://localhost:11434"
LOCAL_OLLAMA_HOSTS = {"localhost", "127.0.0.1", "::1"}
VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    fix: str


def _parse_version(text: str) -> tuple[int, int, int] | None:
    match = VERSION_RE.search(text)
    if match is None:
        return None
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch or "0"))


def _format_version(version: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version)


def _run_version(binary: str, args: Sequence[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(  # nosec B603: argv uses shutil.which-resolved absolute binaries (remove-by: 2026-08-15, ref: PR-WALK3-OLLAMA-CODEX)
            [binary, *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except subprocess.TimeoutExpired as exc:
        command = " ".join(str(part) for part in exc.cmd)
        return 124, f"`{command}` timed out after {exc.timeout} seconds"
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    return completed.returncode, output.strip()


def _check_ollama_binary() -> tuple[CheckResult, str | None, str]:
    binary = shutil.which("ollama")
    if binary is None:
        return (
            CheckResult(
                name="ollama-binary",
                ok=False,
                detail="ollama executable was not found on PATH.",
                fix="Install or update Ollama, then rerun this doctor.",
            ),
            None,
            "",
        )
    return (
        CheckResult(
            name="ollama-binary",
            ok=True,
            detail=f"found {binary}",
            fix="",
        ),
        binary,
        "",
    )


def _check_ollama_version(binary: str | None) -> CheckResult:
    if binary is None:
        return CheckResult(
            name="ollama-launch-version",
            ok=False,
            detail="skipped because ollama executable is missing.",
            fix="Install Ollama v0.15+ before using `ollama launch codex`.",
        )
    returncode, output = _run_version(binary, ["--version"])
    version = _parse_version(output)
    if returncode != 0 and version is None:
        return CheckResult(
            name="ollama-launch-version",
            ok=False,
            detail=f"`ollama --version` failed: {output or 'no output'}",
            fix="Update Ollama and confirm `ollama --version` works.",
        )
    if version is None:
        return CheckResult(
            name="ollama-launch-version",
            ok=False,
            detail=f"could not parse Ollama version from: {output or 'no output'}",
            fix="Update Ollama to v0.15+ and rerun this doctor.",
        )
    if version < MIN_OLLAMA_LAUNCH_VERSION:
        return CheckResult(
            name="ollama-launch-version",
            ok=False,
            detail=(
                f"found Ollama {_format_version(version)}; `ollama launch` "
                f"requires {_format_version(MIN_OLLAMA_LAUNCH_VERSION)}+."
            ),
            fix="Upgrade Ollama, then use `ollama launch codex`, not `ollama launch codex-app`.",
        )
    return CheckResult(
        name="ollama-launch-version",
        ok=True,
        detail=f"found Ollama {_format_version(version)} with launch support.",
        fix="",
    )


def _validate_local_url(raw_url: str) -> tuple[bool, str]:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"}:
        return False, "Ollama URL must use http or https."
    if parsed.hostname not in LOCAL_OLLAMA_HOSTS:
        return False, "Ollama URL must be localhost, 127.0.0.1, or ::1 for this doctor."
    return True, ""


def _positive_timeout(raw_value: str) -> float:
    try:
        timeout_s = float(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a number of seconds") from exc
    if timeout_s <= 0:
        raise argparse.ArgumentTypeError("timeout must be greater than 0 seconds")
    return timeout_s


def _check_ollama_server(base_url: str, timeout_s: float) -> CheckResult:
    valid, reason = _validate_local_url(base_url)
    if not valid:
        return CheckResult(
            name="ollama-local-server",
            ok=False,
            detail=reason,
            fix="Use the default local URL or pass a localhost Ollama URL.",
        )
    version_url = base_url.rstrip("/") + "/api/version"
    try:
        with urlopen(
            version_url, timeout=timeout_s
        ) as response:  # nosec B310: URL is validated as localhost http(s) immediately before use (remove-by: 2026-08-15, ref: PR-WALK3-OLLAMA-CODEX)
            status = getattr(response, "status", 200)
    except (OSError, URLError) as exc:
        return CheckResult(
            name="ollama-local-server",
            ok=False,
            detail=f"could not reach {version_url}: {exc}",
            fix="Start Ollama with `ollama serve` or the desktop app, then rerun this doctor.",
        )
    if status != 200:
        return CheckResult(
            name="ollama-local-server",
            ok=False,
            detail=f"{version_url} returned HTTP {status}.",
            fix="Confirm Ollama is healthy on localhost:11434.",
        )
    return CheckResult(
        name="ollama-local-server",
        ok=True,
        detail=f"{version_url} returned HTTP 200.",
        fix="",
    )


def _check_codex_binary() -> CheckResult:
    binary = shutil.which("codex")
    if binary is None:
        return CheckResult(
            name="codex-binary",
            ok=False,
            detail="codex executable was not found on PATH.",
            fix="Install Codex CLI, then rerun this doctor.",
        )
    returncode, output = _run_version(binary, ["--version"])
    if returncode != 0:
        return CheckResult(
            name="codex-binary",
            ok=False,
            detail=f"found {binary}, but `codex --version` failed: {output or 'no output'}",
            fix="Repair or reinstall Codex CLI.",
        )
    first_line = output.splitlines()[0] if output else "version output empty"
    return CheckResult(
        name="codex-binary",
        ok=True,
        detail=f"found {binary}; {first_line}",
        fix="",
    )


def run_checks(ollama_url: str, timeout_s: float) -> list[CheckResult]:
    ollama_binary_check, ollama_binary, _ = _check_ollama_binary()
    return [
        ollama_binary_check,
        _check_ollama_version(ollama_binary),
        _check_ollama_server(ollama_url, timeout_s),
        _check_codex_binary(),
        CheckResult(
            name="host-config-write-guard",
            ok=True,
            detail="read-only diagnostic; no host config files are inspected or written.",
            fix="",
        ),
    ]


def _print_text(results: list[CheckResult]) -> None:
    print("PulsePlate Codex/Ollama operator doctor")
    print("Scope: host-only diagnostics; no PulsePlate runtime or MCP changes.")
    print()
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"{status}: {result.name}: {result.detail}")
        if result.fix:
            print(f"  fix: {result.fix}")
    print()
    if all(result.ok for result in results):
        print("Next: run `ollama launch codex` or `codex --profile ollama-launch`.")
    else:
        print("Next: fix failed checks, then rerun this doctor.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check local Codex + Ollama operator setup without writing host config."
    )
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--timeout", type=_positive_timeout, default=1.0)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args(argv)

    results = run_checks(ollama_url=args.ollama_url, timeout_s=args.timeout)
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2, sort_keys=True))
    else:
        _print_text(results)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
