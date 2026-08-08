"""Deterministic root npm dependency security guards.

RU: Проверяем, что npm-граф удерживает исправленные security postconditions.
EN: Ensure the npm graph keeps the remediated security postconditions without
freezing an individual PR's historical dependency delta.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, cast

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_PACKAGE_JSON = REPO_ROOT / "package.json"
ROOT_LOCK_JSON = REPO_ROOT / "package-lock.json"
NPM_SURFACE_BASENAMES = frozenset({"package.json", "package-lock.json", "npm-shrinkwrap.json"})
NPM_LOCK_SURFACE_BASENAMES = frozenset({"package-lock.json", "npm-shrinkwrap.json"})
IGNORED_NPM_SURFACE_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "artifacts",
        "build",
        "dist",
        "node_modules",
        "worktrees",
    }
)
NANOID_AFFECTED_RANGES = (
    SpecifierSet("<3.3.17"),
    SpecifierSet(">=4,<5.1.16"),
)
REACT_ROUTER_AFFECTED_RANGES = (
    SpecifierSet(">=7.12,<7.18.2"),
    SpecifierSet(">=8,<8.3.0"),
)


def _load_json(path: Path) -> dict[str, Any]:
    """RU/EN: Read one governed UTF-8 JSON object or fail closed."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssertionError(f"{path}: npm surface must be readable UTF-8 JSON") from exc
    assert isinstance(document, dict), f"{path}: npm surface must be an object"
    return cast(dict[str, Any], document)


def _require_dict_field(container: dict[str, Any], key: str, *, ctx: str) -> dict[str, Any]:
    """RU/EN: Fail closed when an expected JSON object field is missing or malformed."""
    value = container.get(key)
    assert isinstance(value, dict), f"{ctx}: '{key}' must be a dict"
    return cast(dict[str, Any], value)


def _carrier_leaf_paths(packages: dict[str, Any], leaf_name: str) -> list[str]:
    """RU/EN: Collect AgentGuard-scoped transitive paths ending in one leaf."""
    carrier_prefix = "node_modules/@goplus/agentguard/"
    return [
        package_path
        for package_path in packages
        if isinstance(package_path, str)
        and package_path.startswith(carrier_prefix)
        and package_path.endswith(f"/{leaf_name}")
    ]


def _git_stdout(*args: str) -> bytes:
    """Read tracked-path evidence through the resolved absolute Git executable."""
    git_binary = shutil.which("git")
    assert git_binary is not None, "git is required for tracked npm-surface guards"
    git_path = Path(git_binary)
    assert git_path.is_absolute(), "git binary must resolve to an absolute path"
    assert git_path.is_file() and os.access(
        git_path, os.X_OK
    ), "git binary must be an available executable file"
    git_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    result = subprocess.run(
        [git_binary, "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        env=git_env,
        timeout=30,
    )
    return result.stdout


def _is_governed_npm_surface(relative: PurePosixPath) -> bool:
    return (
        relative.name in NPM_SURFACE_BASENAMES
        and not set(relative.parts) & IGNORED_NPM_SURFACE_PARTS
    )


def _load_tracked_npm_surfaces() -> dict[str, dict[str, Any]]:
    """Discover every current tracked npm manifest/lock without pinning a PR base."""
    tracked_paths = _git_stdout("ls-files", "--cached", "-z").decode("utf-8")
    surfaces: dict[str, dict[str, Any]] = {}
    for raw_path in tracked_paths.split("\0"):
        if not raw_path:
            continue
        relative = PurePosixPath(raw_path)
        if not _is_governed_npm_surface(relative):
            continue
        surface_path = REPO_ROOT.joinpath(*relative.parts)
        assert (
            surface_path.is_file() and not surface_path.is_symlink()
        ), f"{relative.as_posix()}: tracked npm surface must be a regular file"
        surfaces[relative.as_posix()] = _load_json(surface_path)
    assert surfaces, "tracked npm surface universe must be non-empty"
    return surfaces


def _dependency_identity_matches(*, key: object, value: object, target: str) -> bool:
    if key == target:
        return True
    if not isinstance(value, str):
        return False
    return value == f"npm:{target}" or value.startswith(f"npm:{target}@")


def _find_manifest_occurrences(
    document: dict[str, Any], *, target: str
) -> dict[tuple[str, ...], object]:
    """Find direct, optional, peer, bundled, override, and npm-alias declarations."""
    occurrences: dict[tuple[str, ...], object] = {}
    for field in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        values = document.get(field)
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            if _dependency_identity_matches(key=key, value=value, target=target):
                occurrences[(field, str(key))] = value

    def walk_overrides(value: object, path: tuple[str, ...]) -> None:
        if not isinstance(value, dict):
            return
        for key, child in value.items():
            child_path = (*path, str(key))
            if _dependency_identity_matches(key=key, value=child, target=target):
                occurrences[child_path] = child
            walk_overrides(child, child_path)

    walk_overrides(document.get("overrides"), ("overrides",))
    for field in ("bundleDependencies", "bundledDependencies"):
        bundled = document.get(field)
        if isinstance(bundled, list) and target in bundled:
            occurrences[(field, str(bundled.index(target)))] = target
    return occurrences


def _resolved_registry_identity(value: object, *, target: str) -> bool:
    if not isinstance(value, str):
        return False
    prefix = f"https://registry.npmjs.org/{target}/-/{target}-"
    return value.startswith(prefix) and value.endswith(".tgz")


def _find_lock_occurrences(document: dict[str, Any], *, target: str) -> dict[str, dict[str, Any]]:
    """Find installed target entries by path, name, or canonical registry identity."""
    assert document.get("lockfileVersion") == 3, "npm lock surface: lockfileVersion must be 3"
    packages = _require_dict_field(document, "packages", ctx="npm lock surface")
    occurrences: dict[str, dict[str, Any]] = {}
    for raw_path, raw_entry in packages.items():
        assert isinstance(raw_path, str), "npm lock surface: package path must be text"
        assert isinstance(
            raw_entry, dict
        ), f"npm lock surface: package entry must be an object: {raw_path}"
        package_path = PurePosixPath(raw_path)
        path_matches = bool(package_path.parts) and package_path.name == target
        name_matches = raw_entry.get("name") == target
        resolved_matches = _resolved_registry_identity(raw_entry.get("resolved"), target=target)
        if path_matches or name_matches or resolved_matches:
            occurrences[raw_path] = cast(dict[str, Any], raw_entry)
    return occurrences


def _assert_occurrences_outside_ranges(
    *,
    surface: str,
    occurrences: dict[str, dict[str, Any]],
    affected_ranges: tuple[SpecifierSet, ...],
) -> None:
    for package_path, entry in occurrences.items():
        raw_version = entry.get("version")
        assert isinstance(raw_version, str), f"{surface}:{package_path}: version must be text"
        try:
            version = Version(raw_version)
        except InvalidVersion as exc:
            raise AssertionError(
                f"{surface}:{package_path}: version must be advisory-comparable"
            ) from exc
        assert not any(
            version in affected for affected in affected_ranges
        ), f"{surface}:{package_path}: {version} remains inside a reconciled affected range"


def test_root_lock_removes_hono_runtime_path() -> None:
    """RU/EN: Root lockfile must not carry a stale hono runtime path anymore."""
    packages = _require_dict_field(_load_json(ROOT_LOCK_JSON), "packages", ctx="package-lock.json")
    assert "node_modules/hono" not in packages


def test_root_lock_removes_mcp_sdk_runtime_path() -> None:
    """RU/EN: Root lockfile must not keep stale MCP SDK runtime packages."""
    packages = _require_dict_field(_load_json(ROOT_LOCK_JSON), "packages", ctx="package-lock.json")
    assert "node_modules/@modelcontextprotocol/sdk" not in packages


def test_root_manifest_removes_external_agentguard_runtime_dependency() -> None:
    """RU/EN: Root manifest must not reintroduce the unresolved AgentGuard path."""
    package_manifest = _load_json(ROOT_PACKAGE_JSON)
    dependencies = _require_dict_field(package_manifest, "dependencies", ctx="package.json")
    overrides = _require_dict_field(package_manifest, "overrides", ctx="package.json")
    assert "@goplus/agentguard" not in dependencies
    assert "@goplus/agentguard" not in overrides


def test_root_lock_removes_external_agentguard_and_axios_runtime_path() -> None:
    """RU/EN: Root lockfile must not carry the unresolved AgentGuard -> axios path."""
    packages = _require_dict_field(_load_json(ROOT_LOCK_JSON), "packages", ctx="package-lock.json")
    assert "node_modules/@goplus/agentguard" not in packages
    assert not _carrier_leaf_paths(packages, "axios")


def test_root_lock_removes_brace_expansion_runtime_path() -> None:
    """RU/EN: Root lockfile must not carry historical AgentGuard brace-expansion paths."""
    packages = _require_dict_field(_load_json(ROOT_LOCK_JSON), "packages", ctx="package-lock.json")
    assert not _carrier_leaf_paths(packages, "brace-expansion")


def test_root_lock_removes_path_to_regexp_runtime_path() -> None:
    """RU/EN: Root lockfile must not carry path-to-regexp after graph cleanup."""
    packages = _require_dict_field(_load_json(ROOT_LOCK_JSON), "packages", ctx="package-lock.json")
    assert "node_modules/path-to-regexp" not in packages


def test_root_lock_tracks_current_cspell_runtime_chain() -> None:
    """RU/EN: Keep the cspell chain explicit and free of path-to-regexp."""
    packages = _require_dict_field(_load_json(ROOT_LOCK_JSON), "packages", ctx="package-lock.json")
    cspell_pkg = _require_dict_field(packages, "node_modules/cspell", ctx="packages")
    cspell_glob_pkg = _require_dict_field(packages, "node_modules/cspell-glob", ctx="packages")
    tinyglobby_pkg = _require_dict_field(packages, "node_modules/tinyglobby", ctx="packages")
    cspell_dependencies = _require_dict_field(cspell_pkg, "dependencies", ctx="cspell")
    cspell_glob_dependencies = _require_dict_field(
        cspell_glob_pkg, "dependencies", ctx="cspell-glob"
    )
    tinyglobby_dependencies = _require_dict_field(tinyglobby_pkg, "dependencies", ctx="tinyglobby")
    for dependency_name, value in (
        ("cspell-glob", cspell_dependencies.get("cspell-glob")),
        ("tinyglobby", cspell_dependencies.get("tinyglobby")),
        ("cspell-glob/picomatch", cspell_glob_dependencies.get("picomatch")),
        ("tinyglobby/picomatch", tinyglobby_dependencies.get("picomatch")),
        ("tinyglobby/fdir", tinyglobby_dependencies.get("fdir")),
    ):
        assert isinstance(value, str) and value.strip(), f"missing dependency: {dependency_name}"
    assert "path-to-regexp" not in tinyglobby_dependencies


def test_retired_pptx_graph_stays_absent_from_all_tracked_npm_surfaces() -> None:
    """The retired pptxgenjs/image-size executable graph cannot silently return."""
    for relative, document in _load_tracked_npm_surfaces().items():
        basename = PurePosixPath(relative).name
        if basename == "package.json":
            for target in ("pptxgenjs", "image-size"):
                assert not _find_manifest_occurrences(
                    document, target=target
                ), f"{relative}: retired {target} declaration or alias reintroduced"
            continue
        assert basename in NPM_LOCK_SURFACE_BASENAMES
        for target in ("pptxgenjs", "image-size"):
            assert not _find_lock_occurrences(
                document, target=target
            ), f"{relative}: retired {target} lock occurrence reintroduced"


def test_nanoid_occurrences_stay_outside_all_reconciled_affected_ranges() -> None:
    """Every installed nanoid remains outside both known affected range families."""
    for relative, document in _load_tracked_npm_surfaces().items():
        if PurePosixPath(relative).name not in NPM_LOCK_SURFACE_BASENAMES:
            continue
        _assert_occurrences_outside_ranges(
            surface=relative,
            occurrences=_find_lock_occurrences(document, target="nanoid"),
            affected_ranges=NANOID_AFFECTED_RANGES,
        )


def test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges() -> None:
    """Every installed React Router remains outside both known affected ranges."""
    for relative, document in _load_tracked_npm_surfaces().items():
        if PurePosixPath(relative).name not in NPM_LOCK_SURFACE_BASENAMES:
            continue
        _assert_occurrences_outside_ranges(
            surface=relative,
            occurrences=_find_lock_occurrences(document, target="react-router"),
            affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
        )
