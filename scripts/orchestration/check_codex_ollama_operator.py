#!/usr/bin/env python3
"""Diagnose host-only Codex + Ollama operator setup.

This script is intentionally read-only. It checks local tool availability and
prints actionable guidance, but it never writes host config such as
``~/.codex/config.toml``.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess  # nosec B404: required for bounded local CLI version checks (remove-by: 2026-09-30, ref: PR-main-nightly-nosec-ttl)
import sys
from dataclasses import asdict, dataclass
from typing import Any, ContextManager, Sequence, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

MIN_OLLAMA_CODEX_CLI_VERSION = (0, 15, 0)
MIN_OLLAMA_CODEX_APP_VERSION = (0, 24, 0)
MIN_OLLAMA_OPENAI_RESPONSES_VERSION = (0, 13, 3)
DEFAULT_OLLAMA_URL = "http://localhost:11434"
LOCAL_OLLAMA_HOSTS = {"localhost", "127.0.0.1", "::1"}
VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")
CLIENT_VERSION_RE = re.compile(
    r"\bclient\s+version(?:\s+is)?\s+(\d+\.\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)
OLLAMA_VERSION_RE = re.compile(
    r"\bollama\s+version\s+is\s+(\d+\.\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)


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


def _parse_ollama_binary_version(text: str) -> tuple[int, int, int] | None:
    for pattern in (CLIENT_VERSION_RE, OLLAMA_VERSION_RE):
        match = pattern.search(text)
        if match is not None:
            return _parse_version(match.group(1))
    return _parse_version(text)


def _format_version(version: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version)


def _run_version(binary: str, args: Sequence[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(  # nosec B603: argv uses shutil.which-resolved absolute binaries (remove-by: 2026-09-30, ref: PR-main-nightly-nosec-ttl)
            [binary, *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
            shell=False,
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
    binary = os.path.abspath(binary)
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


def _check_ollama_version(binary: str | None) -> tuple[CheckResult, CheckResult]:
    if binary is None:
        missing = CheckResult(
            name="ollama-codex-cli-version",
            ok=False,
            detail="skipped because ollama executable is missing.",
            fix="Install Ollama v0.15+ before using `ollama launch codex` for Codex CLI.",
        )
        return (
            missing,
            CheckResult(
                name="ollama-codex-app-version",
                ok=False,
                detail="skipped because ollama executable is missing.",
                fix="Install Ollama v0.24+ before using `ollama launch codex-app` for Codex App.",
            ),
        )
    returncode, output = _run_version(binary, ["--version"])
    version = _parse_ollama_binary_version(output)
    if returncode != 0:
        version_detail = f" Parsed version: {_format_version(version)}." if version else ""
        failed = CheckResult(
            name="ollama-codex-cli-version",
            ok=False,
            detail=f"`ollama --version` failed: {output or 'no output'}.{version_detail}",
            fix="Update Ollama and confirm `ollama --version` works.",
        )
        return (
            failed,
            CheckResult(
                name="ollama-codex-app-version",
                ok=False,
                detail=failed.detail,
                fix=failed.fix,
            ),
        )
    if version is None:
        failed = CheckResult(
            name="ollama-codex-cli-version",
            ok=False,
            detail=f"could not parse Ollama version from: {output or 'no output'}",
            fix="Update Ollama to v0.24+ and rerun this doctor.",
        )
        return (
            failed,
            CheckResult(
                name="ollama-codex-app-version",
                ok=False,
                detail=failed.detail,
                fix=failed.fix,
            ),
        )
    if version < MIN_OLLAMA_CODEX_CLI_VERSION:
        cli_check = CheckResult(
            name="ollama-codex-cli-version",
            ok=False,
            detail=(
                f"found Ollama {_format_version(version)}; `ollama launch codex` "
                f"requires {_format_version(MIN_OLLAMA_CODEX_CLI_VERSION)}+."
            ),
            fix="Upgrade Ollama, then use `ollama launch codex` for Codex CLI.",
        )
    else:
        cli_check = CheckResult(
            name="ollama-codex-cli-version",
            ok=True,
            detail=(f"found Ollama {_format_version(version)} with Codex CLI launch support."),
            fix="",
        )
    if version < MIN_OLLAMA_CODEX_APP_VERSION:
        app_check = CheckResult(
            name="ollama-codex-app-version",
            ok=False,
            detail=(
                f"found Ollama {_format_version(version)}; `ollama launch codex-app` "
                f"requires {_format_version(MIN_OLLAMA_CODEX_APP_VERSION)}+."
            ),
            fix="Upgrade Ollama, then use `ollama launch codex-app` for Codex App.",
        )
    else:
        app_check = CheckResult(
            name="ollama-codex-app-version",
            ok=True,
            detail=(f"found Ollama {_format_version(version)} with Codex App launch support."),
            fix="",
        )
    return cli_check, app_check


def _normalize_ollama_root_url(raw_url: str) -> tuple[bool, str, str]:
    try:
        parsed = urlparse(raw_url)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError:
        return False, "", "Malformed Ollama URL."
    if parsed.scheme not in {"http", "https"}:
        return False, "", "Ollama URL must use http or https."
    if parsed.username is not None or parsed.password is not None:
        return False, "", "Ollama URL must not include credentials."
    if hostname not in LOCAL_OLLAMA_HOSTS:
        return False, "", "Ollama URL must be localhost, 127.0.0.1, or ::1 for this doctor."
    if parsed.query or parsed.fragment:
        return False, "", "Ollama URL must not include query strings or fragments."
    normalized_path = parsed.path.rstrip("/")
    if normalized_path not in {"", "/v1"}:
        return (
            False,
            "",
            "Ollama URL must be the server root or OpenAI-compatible /v1 path.",
        )
    root_url = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    return True, root_url, ""


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None


def _open_no_redirect(url: str, timeout_s: float) -> ContextManager[Any]:
    opener = build_opener(ProxyHandler({}), _NoRedirectHandler)
    return cast(ContextManager[Any], opener.open(url, timeout=timeout_s))


def _read_ollama_server_version(response: Any) -> tuple[int, int, int] | None:
    raw_body = response.read()
    if isinstance(raw_body, bytes):
        raw_text = raw_body.decode("utf-8", errors="replace")
    else:
        raw_text = str(raw_body)
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    version = payload.get("version")
    if not isinstance(version, str):
        return None
    return _parse_version(version)


def _positive_timeout(raw_value: str) -> float:
    try:
        timeout_s = float(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a number of seconds") from exc
    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise argparse.ArgumentTypeError("timeout must be greater than 0 seconds")
    return timeout_s


def _check_ollama_server(base_url: str, timeout_s: float) -> CheckResult:
    valid, root_url, reason = _normalize_ollama_root_url(base_url)
    if not valid:
        return CheckResult(
            name="ollama-local-server",
            ok=False,
            detail=reason,
            fix="Use the default local URL or pass a localhost Ollama URL.",
        )
    version_url = root_url.rstrip("/") + "/api/version"
    try:
        with _open_no_redirect(
            version_url, timeout_s
        ) as response:  # nosec B310: URL is validated as localhost http(s) immediately before use (remove-by: 2026-09-30, ref: PR-main-nightly-nosec-ttl)
            status = getattr(response, "status", 200)
            server_version = _read_ollama_server_version(response)
    except HTTPError as exc:
        if 300 <= exc.code < 400:
            return CheckResult(
                name="ollama-local-server",
                ok=False,
                detail=f"{version_url} returned redirect HTTP {exc.code}; redirects are blocked.",
                fix="Use the direct localhost Ollama server URL without redirects.",
            )
        return CheckResult(
            name="ollama-local-server",
            ok=False,
            detail=f"{version_url} returned HTTP {exc.code}.",
            fix="Confirm a healthy Ollama server is listening on the configured localhost URL.",
        )
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
    if server_version is None:
        return CheckResult(
            name="ollama-local-server",
            ok=False,
            detail=f"{version_url} returned HTTP 200 but no parseable server version.",
            fix="Confirm this is an Ollama server and rerun the doctor.",
        )
    if server_version < MIN_OLLAMA_OPENAI_RESPONSES_VERSION:
        return CheckResult(
            name="ollama-local-server",
            ok=False,
            detail=(
                f"{version_url} returned Ollama server {_format_version(server_version)}; "
                "Codex profiles need OpenAI Responses API support "
                f"({_format_version(MIN_OLLAMA_OPENAI_RESPONSES_VERSION)}+)."
            ),
            fix="Upgrade or restart Ollama so the running server is v0.13.3+ before using Codex profiles.",
        )
    return CheckResult(
        name="ollama-local-server",
        ok=True,
        detail=f"{version_url} returned Ollama server {_format_version(server_version)}.",
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
    binary = os.path.abspath(binary)
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
    cli_version_check, app_version_check = _check_ollama_version(ollama_binary)
    return [
        ollama_binary_check,
        cli_version_check,
        app_version_check,
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
        print(
            "Next: run `ollama launch codex-app` for Codex App, "
            "`ollama launch codex` for Codex CLI, or "
            "`codex --profile ollama-launch` for the host profile."
        )
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
