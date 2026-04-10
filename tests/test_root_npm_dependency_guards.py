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

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_PACKAGE_JSON = REPO_ROOT / "package.json"
ROOT_LOCK_JSON = REPO_ROOT / "package-lock.json"


def _load_json(path: Path) -> dict[str, Any]:
    """RU/EN: Read a UTF-8 JSON file and return the decoded object."""
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_root_lock_removes_hono_runtime_path() -> None:
    """RU/EN: Root lockfile must not carry a stale hono runtime path anymore."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    packages = package_lock.get("packages", {})

    assert isinstance(packages, dict), "package-lock.json: 'packages' must be a dict"
    assert (
        "node_modules/hono" not in packages
    ), "package-lock.json: stale hono path must stay absent"


def test_root_lock_removes_mcp_sdk_runtime_path() -> None:
    """RU/EN: Root lockfile must not keep stale MCP SDK runtime packages after graph cleanup."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    packages = package_lock.get("packages", {})

    assert isinstance(packages, dict), "package-lock.json: 'packages' must be a dict"
    assert (
        "node_modules/@modelcontextprotocol/sdk" not in packages
    ), "package-lock.json: stale @modelcontextprotocol/sdk path must stay absent"


def test_root_manifest_removes_external_agentguard_runtime_dependency() -> None:
    """RU/EN: Root manifest must not reintroduce the unresolved AgentGuard npm path."""
    package_manifest = _load_json(ROOT_PACKAGE_JSON)
    dependencies = package_manifest.get("dependencies", {})
    overrides = package_manifest.get("overrides", {})

    assert isinstance(dependencies, dict), "package.json: dependencies section missing"
    assert isinstance(overrides, dict), "package.json: overrides section missing"
    assert (
        "@goplus/agentguard" not in dependencies
    ), "package.json: external @goplus/agentguard dependency must stay removed"
    assert (
        "@goplus/agentguard" not in overrides
    ), "package.json: stale @goplus/agentguard override block must stay removed"


def test_root_lock_removes_external_agentguard_and_axios_runtime_path() -> None:
    """RU/EN: Root lockfile must not carry the unresolved AgentGuard -> axios path."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    packages = package_lock.get("packages", {})

    assert isinstance(packages, dict), "package-lock.json: 'packages' must be a dict"
    assert (
        "node_modules/@goplus/agentguard" not in packages
    ), "package-lock.json: @goplus/agentguard entry must stay removed"
    assert not any(
        isinstance(package_path, str) and package_path.endswith("/axios")
        for package_path in packages
    ), "package-lock.json: axios runtime path must stay absent after agentguard removal"


def test_root_lock_removes_brace_expansion_runtime_path() -> None:
    """RU/EN: Root lockfile must not carry historical brace-expansion runtime paths."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    packages = package_lock.get("packages", {})

    assert isinstance(packages, dict), "package-lock.json: 'packages' must be a dict"
    assert not any(
        isinstance(package_path, str) and package_path.endswith("/brace-expansion")
        for package_path in packages
    ), "package-lock.json: brace-expansion runtime path must stay absent"


def test_root_lock_removes_path_to_regexp_runtime_path() -> None:
    """RU/EN: Root lockfile must not carry path-to-regexp after graph cleanup."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    packages = package_lock.get("packages", {})

    assert isinstance(packages, dict), "package-lock.json: 'packages' must be a dict"
    assert (
        "node_modules/path-to-regexp" not in packages
    ), "package-lock.json: path-to-regexp runtime path must stay absent"


def test_root_lock_tracks_current_cspell_runtime_chain() -> None:
    """RU/EN: Keep the current cspell runtime chain explicit and free of stale path-to-regexp deps."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    cspell_pkg = package_lock.get("packages", {}).get("node_modules/cspell", {})
    cspell_glob_pkg = package_lock.get("packages", {}).get("node_modules/cspell-glob", {})
    tinyglobby_pkg = package_lock.get("packages", {}).get("node_modules/tinyglobby", {})

    cspell_dependencies = cspell_pkg.get("dependencies", {})
    cspell_glob_dependencies = cspell_glob_pkg.get("dependencies", {})
    tinyglobby_dependencies = tinyglobby_pkg.get("dependencies", {})

    cspell_glob_range = cspell_dependencies.get("cspell-glob")
    tinyglobby_range = cspell_dependencies.get("tinyglobby")
    picomatch_from_cspell_glob = cspell_glob_dependencies.get("picomatch")
    picomatch_from_tinyglobby = tinyglobby_dependencies.get("picomatch")
    fdir_from_tinyglobby = tinyglobby_dependencies.get("fdir")

    assert (
        isinstance(cspell_glob_range, str) and cspell_glob_range.strip()
    ), "package-lock.json: cspell cspell-glob dependency missing"
    assert (
        isinstance(tinyglobby_range, str) and tinyglobby_range.strip()
    ), "package-lock.json: cspell tinyglobby dependency missing"
    assert (
        isinstance(picomatch_from_cspell_glob, str) and picomatch_from_cspell_glob.strip()
    ), "package-lock.json: cspell-glob picomatch dependency missing"
    assert (
        isinstance(picomatch_from_tinyglobby, str) and picomatch_from_tinyglobby.strip()
    ), "package-lock.json: tinyglobby picomatch dependency missing"
    assert (
        isinstance(fdir_from_tinyglobby, str) and fdir_from_tinyglobby.strip()
    ), "package-lock.json: tinyglobby fdir dependency missing"
    assert (
        "path-to-regexp" not in tinyglobby_dependencies
    ), "package-lock.json: tinyglobby must not reintroduce path-to-regexp"
