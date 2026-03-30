"""Deterministic root npm dependency security guards.

RU: Проверяем, что root package-lock.json удерживает исправленные security floors
для канонических npm remediation paths.
EN: Ensure the root package-lock.json keeps patched security floors for the
canonical npm remediation paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_LOCK_JSON = REPO_ROOT / "package-lock.json"
MIN_HONO_VERSION = Version("4.12.7")
MIN_BRACE_EXPANSION_VERSION = Version("5.0.5")
MIN_PATH_TO_REGEXP_VERSION = Version("8.4.0")


def _load_json(path: Path) -> dict[str, Any]:
    """RU/EN: Read a UTF-8 JSON file and return the decoded object."""
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


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
        if (
            isinstance(package_path, str)
            and package_path.endswith("/brace-expansion")
            and isinstance(package_data, dict)
        )
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


def test_root_lock_resolves_path_to_regexp_to_safe_npm_release() -> None:
    """RU/EN: Root lockfile must keep path-to-regexp at the secure runtime floor."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    path_to_regexp_pkg = package_lock.get("packages", {}).get("node_modules/path-to-regexp", {})
    lock_version = path_to_regexp_pkg.get("version")
    resolved = path_to_regexp_pkg.get("resolved", "")

    assert isinstance(lock_version, str), "package-lock.json: path-to-regexp version missing"
    assert Version(lock_version) >= MIN_PATH_TO_REGEXP_VERSION
    assert (
        isinstance(resolved, str) and resolved
    ), "package-lock.json: path-to-regexp resolved missing"

    parsed = urlparse(resolved)
    assert parsed.scheme == "https", "path-to-regexp lock resolution must use https"
    assert parsed.netloc == "registry.npmjs.org", "path-to-regexp must resolve from npm registry"
    assert parsed.path.startswith(
        "/path-to-regexp/"
    ), "path-to-regexp lock resolution path mismatch"


def test_root_lock_tracks_path_to_regexp_under_agentguard_runtime_path() -> None:
    """RU/EN: Runtime chain must keep the express router path-to-regexp dependency visible."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    mcp_sdk_pkg = package_lock.get("packages", {}).get("node_modules/@modelcontextprotocol/sdk", {})
    express_pkg = package_lock.get("packages", {}).get("node_modules/express", {})
    router_pkg = package_lock.get("packages", {}).get("node_modules/router", {})

    mcp_sdk_dependencies = mcp_sdk_pkg.get("dependencies", {})
    express_dependencies = express_pkg.get("dependencies", {})
    router_dependencies = router_pkg.get("dependencies", {})

    express_range = mcp_sdk_dependencies.get("express")
    router_range = express_dependencies.get("router")
    path_to_regexp_range = router_dependencies.get("path-to-regexp")

    assert (
        isinstance(express_range, str) and express_range.strip()
    ), "package-lock.json: MCP SDK express dependency missing"
    assert (
        isinstance(router_range, str) and router_range.strip()
    ), "package-lock.json: express router dependency missing"
    assert (
        isinstance(path_to_regexp_range, str) and path_to_regexp_range.strip()
    ), "package-lock.json: router path-to-regexp dependency missing"
