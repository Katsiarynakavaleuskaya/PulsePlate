#!/usr/bin/env python3
"""Repo-owned Playwright MCP/toolchain doctor and bootstrap helper."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import re
import subprocess  # nosec B404: subprocess is required for bounded local Node/Playwright diagnostics with absolute binaries only (remove-by: 2027-02-01, ref: PR-playwright-mcp-node22)
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
NVMRC_PATH = REPO_ROOT / ".nvmrc"
CODEX_HOME = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
PLAYWRIGHT_WRAPPER_PATH = CODEX_HOME / "skills" / "playwright" / "scripts" / "playwright_cli.sh"
PLAYWRIGHT_PACKAGE_PATH = FRONTEND_DIR / "node_modules" / "playwright"
NODE_MODULES_PATH = FRONTEND_DIR / "node_modules"
CHROMIUM_BROWSER_PREFIXES = ("chromium-", "chromium_headless_shell-")


def _playwright_hermetic_browser_dir() -> Path:
    """Return the repo-local Playwright browser path used for hermetic installs."""
    return FRONTEND_DIR / "node_modules" / "playwright-core" / ".local-browsers"


def _playwright_cache_dir() -> Path:
    """Return the platform-aware Playwright browser cache directory."""
    configured_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if configured_path == "0":
        # RU: `0` в Playwright означает hermetic install рядом с пакетом, а не global cache.
        # EN: `0` means Playwright's package-local hermetic browser directory, not the global cache.
        return _playwright_hermetic_browser_dir()
    if configured_path:
        return Path(configured_path).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    if sys.platform == "win32":
        local_appdata = os.environ.get(
            "LOCALAPPDATA",
            str(Path.home() / "AppData" / "Local"),
        )
        return Path(local_appdata).expanduser() / "ms-playwright"
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME", "").strip()
    if xdg_cache_home:
        return Path(xdg_cache_home).expanduser() / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


PLAYWRIGHT_CACHE_DIR = _playwright_cache_dir()


@dataclass(frozen=True)
class CheckResult:
    """Single doctor check result."""

    name: str
    ok: bool
    detail: str
    remediation: str | None = None


def _normalize_node_version(version: str) -> str:
    """Normalize Node version strings before parity checks."""
    # RU: `.nvmrc` может хранить версию как `v24.16.0`, а runtime возвращает `24.16.0`.
    # EN: `.nvmrc` may store `v24.16.0` while the runtime reports `24.16.0`.
    return version.strip().lstrip("vV")


def _read_expected_node_version() -> str | None:
    """Return the repo-canonical Node version from .nvmrc, if present."""
    if not NVMRC_PATH.is_file():
        return None
    expected_node_version = _normalize_node_version(NVMRC_PATH.read_text(encoding="utf-8"))
    return expected_node_version or None


def _resolve_binary(name: str) -> str | None:
    """Return an absolute executable path for a required binary."""
    return shutil.which(name)


def _current_node_version(node_bin: str) -> str | None:
    """Return the current Node runtime version without a leading `v`."""
    selected = Path(node_bin)
    if not selected.is_absolute():
        return None
    try:
        node = selected.resolve(strict=True)
        if not node.is_file() or not os.access(node, os.X_OK):
            return None
        env = {"PATH": os.defpath, "LC_ALL": "C"}
        if os.name == "nt" and os.environ.get("SystemRoot"):
            env["SystemRoot"] = os.environ["SystemRoot"]
        process = subprocess.run(  # nosec B603: argv uses absolute node path from shutil.which() with fixed diagnostic flags only (remove-by: 2027-01-01, ref: PR-playwright-mcp-node22)
            [str(node), "-p", "process.versions.node"],
            cwd=REPO_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
            timeout=10,
            check=False,
        )
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        return None
    if process.returncode != 0:
        return None
    version = (process.stdout or "").removesuffix("\n")
    if re.fullmatch(
        r"[vV]?[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?",
        version,
    ):
        return _normalize_node_version(version)
    return None


def _playwright_browser_cache_present() -> bool:
    """Return True when the Playwright cache contains a Chromium payload."""
    if not PLAYWRIGHT_CACHE_DIR.is_dir():
        return False
    try:
        return any(
            child.is_dir() and child.name.startswith(CHROMIUM_BROWSER_PREFIXES)
            for child in PLAYWRIGHT_CACHE_DIR.iterdir()
        )
    except OSError:
        return False


def _build_doctor_report() -> list[CheckResult]:
    """Collect the repo-local MCP/toolchain health checks."""
    results: list[CheckResult] = []
    expected_node_version = _read_expected_node_version()
    if expected_node_version is None:
        results.append(
            CheckResult(
                name="node-version",
                ok=False,
                detail="Repo Node baseline is missing because .nvmrc is absent or empty.",
                remediation="Restore a non-empty `.nvmrc` with the repo-required Node version.",
            )
        )

    node_bin = _resolve_binary("node")
    if node_bin is None:
        results.append(
            CheckResult(
                name="node-version",
                ok=False,
                detail=(
                    f"Node {expected_node_version} is required on PATH."
                    if expected_node_version is not None
                    else "Node is missing on PATH and the repo baseline cannot be verified."
                ),
                remediation=(
                    f"Activate Node {expected_node_version} via your local toolchain."
                    if expected_node_version is not None
                    else "Install the repo-required Node runtime and restore `.nvmrc`."
                ),
            )
        )
    else:
        current_node_version = _current_node_version(node_bin)
        if current_node_version is None:
            results.append(
                CheckResult(
                    name="node-version",
                    ok=False,
                    detail="Unable to resolve the current Node runtime version.",
                    remediation="Verify that `node -p process.versions.node` works in this shell.",
                )
            )
        elif expected_node_version is None:
            results.append(
                CheckResult(
                    name="node-version",
                    ok=False,
                    detail=(
                        f"Current Node runtime is {current_node_version}, but the repo baseline "
                        "is missing."
                    ),
                    remediation="Restore a non-empty `.nvmrc` before using Playwright MCP.",
                )
            )
        elif current_node_version != expected_node_version:
            # RU: Для Codex MCP нужен exact runtime parity, а не только совпадение major.
            # EN: Codex MCP needs exact runtime parity, not only a matching major version.
            results.append(
                CheckResult(
                    name="node-version",
                    ok=False,
                    detail=(
                        f"Repo baseline is Node {expected_node_version}, current runtime is "
                        f"{current_node_version}."
                    ),
                    remediation=(
                        f"Switch the shell/tooling to Node {expected_node_version} before using "
                        "Playwright MCP."
                    ),
                )
            )
        else:
            results.append(
                CheckResult(
                    name="node-version",
                    ok=True,
                    detail=f"Node runtime matches repo baseline ({expected_node_version}).",
                )
            )

    for binary_name in ("npm", "npx"):
        resolved = _resolve_binary(binary_name)
        results.append(
            CheckResult(
                name=binary_name,
                ok=resolved is not None,
                detail=(
                    f"{binary_name} resolved to {resolved}."
                    if resolved is not None
                    else f"{binary_name} is missing on PATH."
                ),
                remediation=(
                    None
                    if resolved is not None
                    else f"Install {binary_name} with the Node toolchain."
                ),
            )
        )

    results.append(
        CheckResult(
            name="frontend-node-modules",
            ok=NODE_MODULES_PATH.is_dir(),
            detail=(
                f"Frontend dependencies present at {NODE_MODULES_PATH}."
                if NODE_MODULES_PATH.is_dir()
                else "frontend/node_modules is missing."
            ),
            remediation="Run `cd frontend && npm ci`.",
        )
    )

    results.append(
        CheckResult(
            name="frontend-playwright-package",
            ok=PLAYWRIGHT_PACKAGE_PATH.exists(),
            detail=(
                f"Local Playwright package present at {PLAYWRIGHT_PACKAGE_PATH}."
                if PLAYWRIGHT_PACKAGE_PATH.exists()
                else "Local Playwright package is missing from frontend/node_modules."
            ),
            remediation="Run `cd frontend && npm ci` to install @playwright/test and Playwright.",
        )
    )

    browser_cache_present = _playwright_browser_cache_present()
    results.append(
        CheckResult(
            name="playwright-browser-cache",
            ok=browser_cache_present,
            detail=(
                f"Browser cache found at {PLAYWRIGHT_CACHE_DIR}."
                if browser_cache_present
                else f"No Playwright browser payloads found under {PLAYWRIGHT_CACHE_DIR}."
            ),
            remediation="Run `cd frontend && npx playwright install chromium`.",
        )
    )

    results.append(
        CheckResult(
            name="codex-playwright-wrapper",
            ok=PLAYWRIGHT_WRAPPER_PATH.is_file(),
            detail=(
                f"Codex Playwright wrapper found at {PLAYWRIGHT_WRAPPER_PATH}."
                if PLAYWRIGHT_WRAPPER_PATH.is_file()
                else f"Codex Playwright wrapper is missing at {PLAYWRIGHT_WRAPPER_PATH}."
            ),
            remediation=(
                "Reinstall the local Codex Playwright skill or restore the wrapper path under "
                "$CODEX_HOME."
            ),
        )
    )

    return results


def _print_text_report(results: list[CheckResult]) -> None:
    """Render the doctor output for humans."""
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")
        if not result.ok and result.remediation:
            print(f"  remediation: {result.remediation}")


def _doctor_exit_code(results: list[CheckResult]) -> int:
    """Return non-zero when any doctor check blocks MCP usage."""
    return 0 if all(result.ok for result in results) else 1


def _installed_playwright_cli() -> Path:
    """Select the installed package's regular CLI from the matching frontend lock row."""
    package = FRONTEND_DIR / "node_modules" / "playwright"
    if FRONTEND_DIR != REPO_ROOT / "frontend" or package.resolve(strict=True) != package:
        raise ValueError("Invalid Playwright package location")

    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate Playwright metadata field")
            result[key] = value
        return result

    def record(path: Path) -> dict[str, object]:
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError("Invalid Playwright metadata file")
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=object_pairs)
        if not isinstance(data, dict):
            raise ValueError("Invalid Playwright metadata")
        return data

    lock = record(FRONTEND_DIR / "package-lock.json")
    packages = lock.get("packages")
    expected = packages.get("node_modules/playwright") if isinstance(packages, dict) else None
    actual = record(package / "package.json")
    if (
        not isinstance(expected, dict)
        or expected.get("link")
        or expected.get("name", "playwright") != "playwright"
        or actual.get("name") != "playwright"
        or not isinstance(expected.get("version"), str)
        or not expected["version"]
        or expected["version"] != actual.get("version")
    ):
        raise ValueError("Playwright installation does not match the lock")
    declared = expected.get("bin")
    installed = actual.get("bin")
    entry = declared.get("playwright") if isinstance(declared, dict) else None
    if (
        not isinstance(entry, str)
        or not entry
        or not isinstance(installed, dict)
        or installed.get("playwright") != entry
        or "\\" in entry
        or Path(entry).is_absolute()
        or ".." in Path(entry).parts
    ):
        raise ValueError("Invalid Playwright CLI declaration")
    cli = package / entry
    if cli.resolve(strict=True) != cli or not cli.is_file() or cli.stat().st_nlink != 1:
        raise ValueError("Invalid Playwright CLI file")
    return cli


def _run_install_browser() -> int:
    """Install the Chromium browser payload used by the repo Playwright flows."""
    results = _build_doctor_report()
    blocking_names = {
        result.name
        for result in results
        if not result.ok
        and result.name
        in {
            "node-version",
            "npm",
            "npx",
            "frontend-node-modules",
            "frontend-playwright-package",
        }
    }
    if blocking_names:
        _print_text_report(results)
        print(
            "Refusing to install Playwright browsers because the repo toolchain is not ready.",
            file=sys.stderr,
        )
        return 1

    selected = _resolve_binary("node")
    try:
        baseline = _read_expected_node_version()
        if not selected or not Path(selected).is_absolute() or not baseline:
            raise ValueError("Missing selected Node")
        node = Path(selected).resolve(strict=True)
        if (
            not node.is_file()
            or not os.access(node, os.X_OK)
            or _current_node_version(str(node)) != baseline
        ):
            raise ValueError("Selected Node no longer matches the repo baseline")
        cli = _installed_playwright_cli()
    except (ValueError, OSError, RuntimeError, RecursionError):
        print(
            "Refusing to install Playwright browsers: local toolchain binding failed.",
            file=sys.stderr,
        )
        return 1
    # Keep the caller's browser destination and download transport settings.
    names = {
        "HOME",
        "USERPROFILE",
        "LOCALAPPDATA",
        "APPDATA",
        "SYSTEMROOT",
        "TMPDIR",
        "TEMP",
        "TMP",
        "XDG_CACHE_HOME",
        "LANG",
        "LC_ALL",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "NPM_CONFIG_PROXY",
        "NPM_CONFIG_HTTP_PROXY",
        "NPM_CONFIG_HTTPS_PROXY",
        "NPM_CONFIG_NOPROXY",
        "NODE_EXTRA_CA_CERTS",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "PLAYWRIGHT_BROWSERS_PATH",
        "PLAYWRIGHT_SKIP_BROWSER_GC",
        "PLAYWRIGHT_HOST_PLATFORM_OVERRIDE",
        "INIT_CWD",
        "PLAYWRIGHT_DOWNLOAD_HOST",
        "PLAYWRIGHT_CHROMIUM_DOWNLOAD_HOST",
        "PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT",
    }
    names.update(
        {
            prefix + name
            for name in tuple(names)
            if name.startswith("PLAYWRIGHT_")
            for prefix in ("NPM_CONFIG_", "NPM_PACKAGE_CONFIG_")
        }
    )
    env = {key: value for key, value in os.environ.items() if key.upper() in names}
    env["PATH"] = str(node.parent) + os.pathsep + os.defpath
    try:
        process = subprocess.run(  # nosec B603: qualified Node runs the locked local Playwright CLI with fixed install arguments (remove-by: 2026-12-01, ref: PR-playwright-mcp-node22)
            [str(node), str(cli), "install", "chromium"],
            cwd=FRONTEND_DIR,
            env=env,
            check=False,
        )
    except OSError:
        print("Unable to start the local Playwright browser installer.", file=sys.stderr)
        return 1
    return process.returncode


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="playwright_mcp.py",
        description="Repo-owned Playwright MCP/toolchain doctor and bootstrap helper.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Validate Node/MCP/browser prerequisites.")
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the doctor report as JSON.",
    )

    subparsers.add_parser(
        "install-browser",
        help="Install the Chromium browser payload from the repo frontend directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        results = _build_doctor_report()
        if args.json:
            print(json.dumps([asdict(result) for result in results], indent=2))
        else:
            _print_text_report(results)
        return _doctor_exit_code(results)

    if args.command == "install-browser":
        return _run_install_browser()

    parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
