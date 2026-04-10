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


def _require_dict_field(container: dict[str, Any], key: str, *, ctx: str) -> dict[str, Any]:
    """RU/EN: Fail closed when an expected JSON object field is missing or malformed."""
    value = container.get(key)
    assert isinstance(value, dict), f"{ctx}: '{key}' must be a dict"
    return cast(dict[str, Any], value)


def _carrier_leaf_paths(packages: dict[str, Any], leaf_name: str) -> list[str]:
    """RU/EN: Collect agentguard-scoped transitive paths that end with the requested leaf package."""
    carrier_prefix = "node_modules/@goplus/agentguard/"
    return [
        package_path
        for package_path in packages
        if isinstance(package_path, str)
        and package_path.startswith(carrier_prefix)
        and package_path.endswith(f"/{leaf_name}")
    ]


def test_root_lock_removes_hono_runtime_path() -> None:
    """RU/EN: Root lockfile must not carry a stale hono runtime path anymore."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    packages = _require_dict_field(package_lock, "packages", ctx="package-lock.json")
    assert (
        "node_modules/hono" not in packages
    ), "package-lock.json: stale hono path must stay absent"


def test_root_lock_removes_mcp_sdk_runtime_path() -> None:
    """RU/EN: Root lockfile must not keep stale MCP SDK runtime packages after graph cleanup."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    packages = _require_dict_field(package_lock, "packages", ctx="package-lock.json")
    assert (
        "node_modules/@modelcontextprotocol/sdk" not in packages
    ), "package-lock.json: stale @modelcontextprotocol/sdk path must stay absent"


def test_root_manifest_removes_external_agentguard_runtime_dependency() -> None:
    """RU/EN: Root manifest must not reintroduce the unresolved AgentGuard npm path."""
    package_manifest = _load_json(ROOT_PACKAGE_JSON)
    dependencies = _require_dict_field(package_manifest, "dependencies", ctx="package.json")
    overrides = _require_dict_field(package_manifest, "overrides", ctx="package.json")
    assert (
        "@goplus/agentguard" not in dependencies
    ), "package.json: external @goplus/agentguard dependency must stay removed"
    assert (
        "@goplus/agentguard" not in overrides
    ), "package.json: stale @goplus/agentguard override block must stay removed"


def test_root_lock_removes_external_agentguard_and_axios_runtime_path() -> None:
    """RU/EN: Root lockfile must not carry the unresolved AgentGuard -> axios path."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    packages = _require_dict_field(package_lock, "packages", ctx="package-lock.json")
    assert (
        "node_modules/@goplus/agentguard" not in packages
    ), "package-lock.json: @goplus/agentguard entry must stay removed"
    assert not _carrier_leaf_paths(
        packages, "axios"
    ), "package-lock.json: @goplus/agentguard/.../axios runtime path must stay absent"


def test_root_lock_removes_brace_expansion_runtime_path() -> None:
    """RU/EN: Root lockfile must not carry historical AgentGuard-scoped brace-expansion paths."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    packages = _require_dict_field(package_lock, "packages", ctx="package-lock.json")
    assert not _carrier_leaf_paths(
        packages, "brace-expansion"
    ), "package-lock.json: @goplus/agentguard/.../brace-expansion runtime path must stay absent"


def test_root_lock_removes_path_to_regexp_runtime_path() -> None:
    """RU/EN: Root lockfile must not carry path-to-regexp after graph cleanup."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    packages = _require_dict_field(package_lock, "packages", ctx="package-lock.json")
    assert (
        "node_modules/path-to-regexp" not in packages
    ), "package-lock.json: path-to-regexp runtime path must stay absent"


def test_root_lock_tracks_current_cspell_runtime_chain() -> None:
    """RU/EN: Keep the current cspell runtime chain explicit and free of stale path-to-regexp deps."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    packages = _require_dict_field(package_lock, "packages", ctx="package-lock.json")
    cspell_pkg = _require_dict_field(
        packages, "node_modules/cspell", ctx="package-lock.json packages"
    )
    cspell_glob_pkg = _require_dict_field(
        packages, "node_modules/cspell-glob", ctx="package-lock.json packages"
    )
    tinyglobby_pkg = _require_dict_field(
        packages, "node_modules/tinyglobby", ctx="package-lock.json packages"
    )

    cspell_dependencies = _require_dict_field(
        cspell_pkg, "dependencies", ctx="package-lock.json node_modules/cspell"
    )
    cspell_glob_dependencies = _require_dict_field(
        cspell_glob_pkg, "dependencies", ctx="package-lock.json node_modules/cspell-glob"
    )
    tinyglobby_dependencies = _require_dict_field(
        tinyglobby_pkg, "dependencies", ctx="package-lock.json node_modules/tinyglobby"
    )

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
