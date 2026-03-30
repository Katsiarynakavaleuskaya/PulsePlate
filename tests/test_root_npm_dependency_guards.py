"""Deterministic root npm dependency security guards.

RU: Проверяем, что root package-lock.json удерживает исправленные security floors
для канонических npm remediation paths.
EN: Ensure the root package-lock.json keeps patched security floors for the
canonical npm remediation paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_LOCK_JSON = REPO_ROOT / "package-lock.json"
MIN_HONO_VERSION = Version("4.12.7")
MIN_BRACE_EXPANSION_VERSION = Version("5.0.5")


def _load_json(path: Path) -> dict:
    """RU/EN: Read a UTF-8 JSON file and return the decoded object."""
    return json.loads(path.read_text(encoding="utf-8"))


def test_root_lock_resolves_hono_to_safe_npm_release() -> None:
    """RU/EN: Root lockfile must resolve hono from npm registry at secure floor version."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    hono_pkg = package_lock.get("packages", {}).get("node_modules/hono", {})
    lock_version = hono_pkg.get("version")
    resolved = hono_pkg.get("resolved", "")

    assert isinstance(lock_version, str), "package-lock.json: hono version missing"
    assert Version(lock_version) >= MIN_HONO_VERSION
    assert isinstance(resolved, str) and resolved, "package-lock.json: hono resolved missing"

    parsed = urlparse(resolved)
    assert parsed.scheme == "https", "hono lock resolution must use https"
    assert parsed.netloc == "registry.npmjs.org", "hono must resolve from npm registry"
    assert parsed.path.startswith("/hono/"), "hono lock resolution path mismatch"


def test_root_lock_tracks_hono_as_mcp_sdk_transitive_dependency() -> None:
    """RU/EN: Dependency path should still show hono under @modelcontextprotocol/sdk."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    mcp_sdk_pkg = package_lock.get("packages", {}).get("node_modules/@modelcontextprotocol/sdk", {})
    dependencies = mcp_sdk_pkg.get("dependencies", {})

    hono_range = dependencies.get("hono")
    assert isinstance(hono_range, str), "package-lock.json: MCP SDK hono dependency missing"
    assert hono_range.strip(), "package-lock.json: MCP SDK hono dependency range missing"


def test_root_lock_resolves_brace_expansion_to_safe_npm_release() -> None:
    """RU/EN: Root lockfile must resolve all brace-expansion entries to the patched npm floor."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    packages = package_lock.get("packages", {})

    assert isinstance(packages, dict), "package-lock.json: 'packages' must be a dict"

    brace_expansion_entries = {
        package_path: package_data
        for package_path, package_data in packages.items()
        if isinstance(package_path, str) and package_path.endswith("/brace-expansion")
    }

    assert (
        brace_expansion_entries
    ), "package-lock.json: no brace-expansion entries found in packages map"

    for package_path, brace_expansion_pkg in brace_expansion_entries.items():
        lock_version = brace_expansion_pkg.get("version")
        resolved = brace_expansion_pkg.get("resolved", "")

        assert isinstance(lock_version, str), f"{package_path}: brace-expansion version missing"
        assert Version(lock_version) >= MIN_BRACE_EXPANSION_VERSION
        assert isinstance(resolved, str) and resolved, f"{package_path}: resolved tarball missing"

        parsed = urlparse(resolved)
        assert parsed.scheme == "https", f"{package_path}: lock resolution must use https"
        assert (
            parsed.netloc == "registry.npmjs.org"
        ), f"{package_path}: must resolve from npm registry"
        assert parsed.path.startswith(
            "/brace-expansion/"
        ), f"{package_path}: brace-expansion lock resolution path mismatch"


def test_root_lock_tracks_brace_expansion_under_agentguard_dependency_path() -> None:
    """RU/EN: Dependency path must stay rooted at AgentGuard -> glob -> minimatch."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    agentguard_pkg = package_lock.get("packages", {}).get("node_modules/@goplus/agentguard", {})
    glob_pkg = package_lock.get("packages", {}).get("node_modules/glob", {})
    minimatch_pkg = package_lock.get("packages", {}).get("node_modules/minimatch", {})

    agentguard_dependencies = agentguard_pkg.get("dependencies", {})
    glob_dependencies = glob_pkg.get("dependencies", {})
    minimatch_dependencies = minimatch_pkg.get("dependencies", {})

    glob_range = agentguard_dependencies.get("glob")
    minimatch_range = glob_dependencies.get("minimatch")
    brace_expansion_range = minimatch_dependencies.get("brace-expansion")

    assert (
        isinstance(glob_range, str) and glob_range.strip()
    ), "package-lock.json: AgentGuard glob dependency missing"
    assert (
        isinstance(minimatch_range, str) and minimatch_range.strip()
    ), "package-lock.json: glob minimatch dependency missing"
    assert (
        isinstance(brace_expansion_range, str) and brace_expansion_range.strip()
    ), "package-lock.json: minimatch brace-expansion dependency missing"
