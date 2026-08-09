"""Deterministic root npm dependency security guards.

RU: Проверяем, что npm-граф удерживает исправленные security postconditions.
EN: Ensure the npm graph keeps the remediated security postconditions without
freezing an individual PR's historical dependency delta.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any, cast
from urllib.parse import unquote, urlparse

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_PACKAGE_JSON = REPO_ROOT / "package.json"
ROOT_LOCK_JSON = REPO_ROOT / "package-lock.json"
NPM_SURFACE_BASENAMES = frozenset({"package.json", "package-lock.json", "npm-shrinkwrap.json"})
NPM_LOCK_SURFACE_BASENAMES = frozenset({"package-lock.json", "npm-shrinkwrap.json"})
NANOID_AFFECTED_RANGES = (
    SpecifierSet("<3.3.17"),
    SpecifierSet(">=4,<5.1.16"),
)
REACT_ROUTER_AFFECTED_RANGES = (
    SpecifierSet(">=7.12,<7.18.2"),
    SpecifierSet(">=8,<8.3.0"),
)
_NPM_SEMVER_MAX_LENGTH = 256
_NPM_SEMVER_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_EXACT_NPM_SEMVER_RE = re.compile(
    r"^(?P<core>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))"
    r"(?P<prerelease>-(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_NPM_PACKAGE_ARG_GIT_CLASSIFIER_JS = r"""
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");

const npmCli = path.resolve(process.argv[1]);
const repoRoot = path.resolve(process.argv[2]);
const npmRoot = path.dirname(path.dirname(npmCli));
const npmRequire = createRequire(npmCli);
const packageArgEntry = path.resolve(npmRequire.resolve("npm-package-arg"));
const packageArgRoot = path.join(npmRoot, "node_modules", "npm-package-arg") + path.sep;
if (!packageArgEntry.startsWith(packageArgRoot)) {
  throw new Error(`npm-package-arg must resolve from the installed npm tree: ${packageArgEntry}`);
}
const packageArg = npmRequire("npm-package-arg");
const specs = JSON.parse(fs.readFileSync(0, "utf8"));
if (!Array.isArray(specs) || specs.some((spec) => typeof spec !== "string")) {
  throw new TypeError("npm dependency specs must be a JSON string array");
}
const classifications = specs.map((spec) => {
  try {
    return packageArg.resolve("pulseplate-guard", spec, repoRoot).type === "git";
  } catch (_error) {
    return false;
  }
});
process.stdout.write(JSON.stringify(classifications));
"""


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


def _git_stdout(*args: str, root: Path = REPO_ROOT) -> bytes:
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
        [git_binary, "-C", str(root), *args],
        check=True,
        capture_output=True,
        env=git_env,
        timeout=30,
    )
    return result.stdout


def _is_governed_npm_surface(relative: PurePosixPath) -> bool:
    return relative.name in NPM_SURFACE_BASENAMES


def _load_tracked_npm_surfaces(*, root: Path = REPO_ROOT) -> dict[str, dict[str, Any]]:
    """Discover every current tracked npm manifest/lock without pinning a PR base."""
    tracked_paths = _git_stdout("ls-files", "--cached", "-z", root=root).decode("utf-8")
    surfaces: dict[str, dict[str, Any]] = {}
    for raw_path in tracked_paths.split("\0"):
        if not raw_path:
            continue
        relative = PurePosixPath(raw_path)
        if not _is_governed_npm_surface(relative):
            continue
        surface_path = root.joinpath(*relative.parts)
        assert (
            surface_path.is_file() and not surface_path.is_symlink()
        ), f"{relative.as_posix()}: tracked npm surface must be a regular file"
        surfaces[relative.as_posix()] = _load_json(surface_path)
    assert surfaces, "tracked npm surface universe must be non-empty"
    return surfaces


def _fully_decode_url_path(path: str) -> str:
    """Decode a URL path to a finite fixed point and normalize separators."""
    decoded = path.replace("\\", "/")
    for _ in range(len(decoded) + 1):
        next_value = unquote(decoded).replace("\\", "/")
        if next_value == decoded:
            return decoded
        decoded = next_value
    raise AssertionError("URL path percent-decoding did not converge")


def _tarball_identity_matches(value: object, *, target: str) -> bool:
    """Discover a target-shaped tarball independently of its provenance."""
    if not isinstance(value, str):
        return False
    normalized_carrier = value.strip().replace("\\", "/")
    parsed = urlparse(normalized_carrier)
    decoded_path = _fully_decode_url_path(parsed.path)
    normalized_path = f"/{posixpath.normpath(decoded_path).lstrip('/')}"
    path_parts = PurePosixPath(normalized_path).parts
    target_parts = PurePosixPath(target).parts
    package_basename = target.rsplit("/", maxsplit=1)[-1]
    suffix_width = len(target_parts) + 2
    if len(path_parts) < suffix_width:
        return False
    target_start = len(path_parts) - suffix_width
    if len(target_parts) == 1 and target_start > 0 and path_parts[target_start - 1].startswith("@"):
        return False
    return (
        tuple(path_parts[-suffix_width:-2]) == target_parts
        and path_parts[-2] == "-"
        and path_parts[-1].startswith(f"{package_basename}-")
        and path_parts[-1].endswith(".tgz")
    )


def _resolve_current_npm_package_arg_runtime() -> tuple[str, str]:
    """Resolve the absolute Node executable and installed npm CLI or fail closed."""
    node_binary = shutil.which("node")
    npm_binary = shutil.which("npm")
    assert node_binary is not None, "node is required for npm dependency-source guards"
    assert npm_binary is not None, "npm is required for npm dependency-source guards"
    node_path = Path(node_binary)
    npm_path = Path(npm_binary)
    assert node_path.is_absolute(), "node binary must resolve to an absolute path"
    assert npm_path.is_absolute(), "npm binary must resolve to an absolute path"
    assert node_path.is_file() and os.access(
        node_path, os.X_OK
    ), "node binary must be an available executable file"
    assert npm_path.is_file() and os.access(
        npm_path, os.X_OK
    ), "npm binary must be an available executable file"
    try:
        npm_cli_path = npm_path.resolve(strict=True)
    except OSError as exc:
        raise AssertionError("npm CLI symlink must resolve to a regular file") from exc
    assert npm_cli_path.is_file(), "resolved npm CLI must be a regular file"
    return str(node_path), str(npm_cli_path)


def _classify_current_npm_git_specs(
    values: Iterable[object], *, root: Path = REPO_ROOT
) -> dict[str, bool]:
    """Delegate Git-source classification to the npm installation used by this checkout."""
    specs = sorted({value for value in values if isinstance(value, str)})
    if not specs:
        return {}
    node_binary, npm_cli = _resolve_current_npm_package_arg_runtime()
    parser_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key not in {"NODE_OPTIONS", "NODE_PATH"}
    }
    result = subprocess.run(
        [
            node_binary,
            "-e",
            _NPM_PACKAGE_ARG_GIT_CLASSIFIER_JS,
            npm_cli,
            str(root.resolve()),
        ],
        check=True,
        input=json.dumps(specs, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        env=parser_env,
        timeout=30,
    )
    try:
        classifications = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AssertionError("npm-package-arg classifier returned invalid JSON") from exc
    assert isinstance(classifications, list), "npm-package-arg classifier must return a list"
    assert len(classifications) == len(specs), "npm-package-arg classifier result count drift"
    assert all(
        type(value) is bool for value in classifications
    ), "npm-package-arg classifier results must be booleans"
    return dict(zip(specs, classifications, strict=True))


def _dependency_identity_matches(*, key: object, value: object, target: str) -> bool:
    if key == target:
        return True
    if not isinstance(value, str):
        return False
    candidate = value.strip()
    return (
        candidate == f"npm:{target}"
        or candidate.startswith(f"npm:{target}@")
        or _tarball_identity_matches(candidate, target=target)
    )


def _override_key_matches(*, key: object, target: str) -> bool:
    """Match npm override selectors, including scoped package names."""
    return isinstance(key, str) and (key == target or key.startswith(f"{target}@"))


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
            if _override_key_matches(key=key, target=target) or _dependency_identity_matches(
                key=key, value=child, target=target
            ):
                occurrences[child_path] = child
            walk_overrides(child, child_path)

    walk_overrides(document.get("overrides"), ("overrides",))
    for field in ("bundleDependencies", "bundledDependencies"):
        bundled = document.get(field)
        if isinstance(bundled, list) and target in bundled:
            occurrences[(field, str(bundled.index(target)))] = target
    return occurrences


def _find_current_npm_git_dependency_occurrences(
    document: dict[str, Any],
) -> dict[tuple[str, ...], object]:
    """Find Git sources by delegating named manifest values to current npm."""
    candidates: dict[tuple[str, ...], object] = {}
    for field in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        values = document.get(field)
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            candidates[(field, str(key))] = value

    def walk_overrides(value: object, path: tuple[str, ...]) -> None:
        if not isinstance(value, dict):
            return
        for key, child in value.items():
            child_path = (*path, str(key))
            candidates[child_path] = child
            walk_overrides(child, child_path)

    walk_overrides(document.get("overrides"), ("overrides",))
    classifications = _classify_current_npm_git_specs(candidates.values())
    return {
        path: value
        for path, value in candidates.items()
        if isinstance(value, str) and classifications[value]
    }


def _tracked_local_manifest_path(*, surface: str, value: object) -> str | None:
    """Resolve one repository-relative local dependency to its tracked manifest path."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().replace("\\", "/")
    parsed = urlparse(normalized)
    if parsed.scheme:
        if parsed.scheme != "file" or parsed.netloc:
            return None
        local_path = parsed.path
    elif normalized.startswith(("./", "../")):
        local_path = parsed.path
    else:
        return None
    decoded_path = _fully_decode_url_path(local_path)
    if not decoded_path or decoded_path.startswith("/"):
        return None
    manifest_parent = PurePosixPath(surface).parent
    resolved = PurePosixPath(posixpath.normpath((manifest_parent / decoded_path).as_posix()))
    if resolved.is_absolute() or ".." in resolved.parts:
        return None
    return (resolved / "package.json").as_posix()


def _find_tracked_local_manifest_occurrences(
    *,
    surface: str,
    document: dict[str, Any],
    surfaces: dict[str, dict[str, Any]],
    target: str,
) -> dict[tuple[str, ...], object]:
    """Find renamed local-path carriers whose tracked manifest owns the target name."""
    occurrences: dict[tuple[str, ...], object] = {}

    def record_if_target(path: tuple[str, ...], value: object) -> None:
        target_surface = _tracked_local_manifest_path(surface=surface, value=value)
        target_document = surfaces.get(target_surface) if target_surface is not None else None
        if isinstance(target_document, dict) and target_document.get("name") == target:
            occurrences[path] = value

    for field in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        values = document.get(field)
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            record_if_target((field, str(key)), value)

    def walk_overrides(value: object, path: tuple[str, ...]) -> None:
        if not isinstance(value, dict):
            return
        for key, child in value.items():
            child_path = (*path, str(key))
            record_if_target(child_path, child)
            walk_overrides(child, child_path)

    walk_overrides(document.get("overrides"), ("overrides",))
    return occurrences


def _find_governed_manifest_occurrences(
    *,
    surface: str,
    document: dict[str, Any],
    surfaces: dict[str, dict[str, Any]],
    target: str,
) -> dict[tuple[str, ...], object]:
    """Combine intrinsic carriers with tracked local-package identity evidence."""
    occurrences = _find_manifest_occurrences(document, target=target)
    occurrences.update(
        _find_tracked_local_manifest_occurrences(
            surface=surface,
            document=document,
            surfaces=surfaces,
            target=target,
        )
    )
    return occurrences


def _parse_exact_npm_semver(value: object) -> tuple[Version, bool] | None:
    """Parse exact Node-semver-bounded npm SemVer and retain its prerelease bit."""
    if not isinstance(value, str):
        return None
    if len(value) > _NPM_SEMVER_MAX_LENGTH:
        return None
    candidate = value.strip()
    match = _EXACT_NPM_SEMVER_RE.fullmatch(candidate)
    if match is None:
        return None
    core = match.group("core")
    if any(int(component) > _NPM_SEMVER_MAX_SAFE_INTEGER for component in core.split(".")):
        return None
    return Version(core), match.group("prerelease") is not None


def _exact_manifest_version(value: object, *, target: str) -> tuple[Version, bool] | None:
    """Extract exact npm SemVer from a direct, alias, or target-tarball carrier."""
    if not isinstance(value, str):
        return None
    normalized_carrier = value.strip()
    candidate = value
    alias_prefix = f"npm:{target}@"
    if normalized_carrier.startswith(alias_prefix):
        candidate = normalized_carrier[len(alias_prefix) :]
    elif _tarball_identity_matches(normalized_carrier, target=target):
        decoded_path = _fully_decode_url_path(urlparse(normalized_carrier).path)
        filename = PurePosixPath(posixpath.normpath(decoded_path)).name
        package_basename = target.rsplit("/", maxsplit=1)[-1]
        filename_prefix = f"{package_basename}-"
        if not filename.startswith(filename_prefix) or not filename.endswith(".tgz"):
            return None
        candidate = filename[len(filename_prefix) : -len(".tgz")]
    return _parse_exact_npm_semver(candidate)


def _assert_manifest_occurrences_outside_ranges(
    *,
    surface: str,
    target: str,
    occurrences: dict[tuple[str, ...], object],
    affected_ranges: tuple[SpecifierSet, ...],
) -> None:
    """Require exact stable manifest carriers outside every affected range."""
    for occurrence_path, raw_value in occurrences.items():
        location = "/".join(occurrence_path)
        assert not _tarball_identity_matches(raw_value, target=target), (
            f"{surface}:{location}: {target} manifest tarball carriers lack "
            "lockfile provenance and integrity"
        )
        parsed_version = _exact_manifest_version(raw_value, target=target)
        assert (
            parsed_version is not None
        ), f"{surface}:{location}: {target} must use an exact advisory-comparable version"
        version, is_prerelease = parsed_version
        assert not is_prerelease, f"{surface}:{location}: {target} prerelease versions fail closed"
        assert not any(
            version in affected for affected in affected_ranges
        ), f"{surface}:{location}: {version} remains inside a reconciled affected range"


def _resolved_registry_version(value: object, *, target: str) -> str | None:
    if not isinstance(value, str):
        return None
    prefix = f"https://registry.npmjs.org/{target}/-/{target}-"
    suffix = ".tgz"
    if not value.startswith(prefix) or not value.endswith(suffix):
        return None
    version = value[len(prefix) : -len(suffix)]
    return version or None


def _lock_path_package_identity(raw_path: str) -> str | None:
    """Parse one complete package identity after the final node_modules segment."""
    if "\\" in raw_path:
        return None
    package_path = PurePosixPath(raw_path)
    if package_path.is_absolute() or ".." in package_path.parts:
        return None
    if package_path.as_posix() != raw_path:
        return None
    node_modules_indices = [
        index for index, component in enumerate(package_path.parts) if component == "node_modules"
    ]
    if not node_modules_indices:
        return None
    identity_parts = package_path.parts[node_modules_indices[-1] + 1 :]
    if len(identity_parts) == 1 and identity_parts[0] and not identity_parts[0].startswith("@"):
        return identity_parts[0]
    if (
        len(identity_parts) == 2
        and identity_parts[0].startswith("@")
        and len(identity_parts[0]) > 1
        and identity_parts[1]
        and not identity_parts[1].startswith("@")
    ):
        return "/".join(identity_parts)
    return None


def _find_lock_occurrences(document: dict[str, Any], *, target: str) -> dict[str, dict[str, Any]]:
    """Find installed target entries by path, name, or origin-neutral tarball identity."""
    assert document.get("lockfileVersion") == 3, "npm lock surface: lockfileVersion must be 3"
    packages = _require_dict_field(document, "packages", ctx="npm lock surface")
    occurrences: dict[str, dict[str, Any]] = {}
    for raw_path, raw_entry in packages.items():
        assert isinstance(raw_path, str), "npm lock surface: package path must be text"
        assert isinstance(
            raw_entry, dict
        ), f"npm lock surface: package entry must be an object: {raw_path}"
        path_matches = _lock_path_package_identity(raw_path) == target
        name_matches = raw_entry.get("name") == target
        resolved_matches = _tarball_identity_matches(raw_entry.get("resolved"), target=target)
        if path_matches or name_matches or resolved_matches:
            occurrences[raw_path] = cast(dict[str, Any], raw_entry)
    return occurrences


def _assert_occurrences_outside_ranges(
    *,
    surface: str,
    target: str,
    occurrences: dict[str, dict[str, Any]],
    affected_ranges: tuple[SpecifierSet, ...],
) -> None:
    for package_path, entry in occurrences.items():
        raw_version = entry.get("version")
        assert isinstance(raw_version, str), f"{surface}:{package_path}: version must be text"
        parsed_version = _parse_exact_npm_semver(raw_version)
        assert (
            parsed_version is not None
        ), f"{surface}:{package_path}: version must be exact npm SemVer and advisory-comparable"
        version, is_prerelease = parsed_version
        assert (
            not is_prerelease
        ), f"{surface}:{package_path}: prerelease target versions fail closed"
        resolved_version = _resolved_registry_version(entry.get("resolved"), target=target)
        assert (
            resolved_version is not None
        ), f"{surface}:{package_path}: resolved must be the canonical {target} registry tarball"
        assert (
            resolved_version == raw_version
        ), f"{surface}:{package_path}: resolved tarball version must equal package version"
        integrity = entry.get("integrity")
        assert (
            isinstance(integrity, str) and integrity.strip()
        ), f"{surface}:{package_path}: integrity must be non-empty"
        assert not any(
            version in affected for affected in affected_ranges
        ), f"{surface}:{package_path}: {version} remains inside a reconciled affected range"


def _npm_dependency_resolution_paths(*, package_path: str, target: str) -> tuple[str, ...]:
    """Return nearest-first npm lock paths able to resolve one dependency."""
    assert "\\" not in package_path, f"{package_path}: npm lock path must use POSIX separators"
    path = PurePosixPath(package_path)
    assert not path.is_absolute(), f"{package_path}: npm lock path must be relative"
    assert ".." not in path.parts, f"{package_path}: npm lock path must not traverse"
    node_modules_indices = [
        index for index, component in enumerate(path.parts) if component == "node_modules"
    ]
    assert (
        node_modules_indices
    ), f"{package_path}: installed npm dependency path must include node_modules"
    candidates = [
        (path / "node_modules" / target).as_posix(),
        *(
            PurePosixPath(*path.parts[: index + 1], target).as_posix()
            for index in reversed(node_modules_indices)
        ),
    ]
    return tuple(dict.fromkeys(candidates))


def _assert_react_router_dom_dependency_edges(
    *,
    surface: str,
    dom_occurrences: dict[str, dict[str, Any]],
    router_occurrences: dict[str, dict[str, Any]],
) -> None:
    """Bind every Router DOM artifact to its exact validated Router dependency."""
    for package_path, entry in dom_occurrences.items():
        dependencies = entry.get("dependencies")
        assert isinstance(
            dependencies, dict
        ), f"{surface}:{package_path}: react-router-dom dependencies must be an object"
        raw_edge = dependencies.get("react-router")
        parsed_edge = _parse_exact_npm_semver(raw_edge)
        assert parsed_edge is not None, (
            f"{surface}:{package_path}: react-router-dom must declare an exact "
            "react-router dependency"
        )
        edge_version, edge_is_prerelease = parsed_edge
        assert (
            not edge_is_prerelease
        ), f"{surface}:{package_path}: react-router dependency must be a stable release"
        for affected_range in REACT_ROUTER_AFFECTED_RANGES:
            assert edge_version not in affected_range, (
                f"{surface}:{package_path}: react-router dependency {edge_version} "
                "remains inside a reconciled affected range"
            )
        dom_version = entry.get("version")
        assert raw_edge == dom_version, (
            f"{surface}:{package_path}: react-router dependency must equal "
            "react-router-dom package version"
        )
        resolution_paths = _npm_dependency_resolution_paths(
            package_path=package_path,
            target="react-router",
        )
        resolved_path = next(
            (candidate for candidate in resolution_paths if candidate in router_occurrences),
            None,
        )
        assert resolved_path is not None, (
            f"{surface}:{package_path}: react-router dependency has no corresponding "
            "nested or hoisted installed occurrence"
        )
        resolved_version = router_occurrences[resolved_path].get("version")
        assert raw_edge == resolved_version, (
            f"{surface}:{package_path}: react-router dependency must equal corresponding "
            f"installed occurrence {resolved_path}"
        )


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


def test_tracked_npm_manifests_reject_current_npm_git_dependency_sources() -> None:
    """Opaque specs classified as Git by current npm cannot hide package identity."""
    surfaces = _load_tracked_npm_surfaces()
    for relative, document in surfaces.items():
        if PurePosixPath(relative).name != "package.json":
            continue
        assert not _find_current_npm_git_dependency_occurrences(
            document
        ), f"{relative}: npm-classified Git dependency source requires separate provenance"


def test_retired_pptx_graph_stays_absent_from_all_tracked_npm_surfaces() -> None:
    """The retired pptxgenjs/image-size executable graph cannot silently return."""
    surfaces = _load_tracked_npm_surfaces()
    for relative, document in surfaces.items():
        basename = PurePosixPath(relative).name
        if basename == "package.json":
            for target in ("pptxgenjs", "image-size"):
                assert not _find_governed_manifest_occurrences(
                    surface=relative,
                    document=document,
                    surfaces=surfaces,
                    target=target,
                ), f"{relative}: retired {target} declaration or alias reintroduced"
            continue
        assert basename in NPM_LOCK_SURFACE_BASENAMES
        for target in ("pptxgenjs", "image-size"):
            assert not _find_lock_occurrences(
                document, target=target
            ), f"{relative}: retired {target} lock occurrence reintroduced"


def test_nanoid_occurrences_stay_outside_all_reconciled_affected_ranges() -> None:
    """Every installed nanoid remains outside both known affected range families."""
    surfaces = _load_tracked_npm_surfaces()
    for relative, document in surfaces.items():
        basename = PurePosixPath(relative).name
        if basename == "package.json":
            assert not _find_governed_manifest_occurrences(
                surface=relative,
                document=document,
                surfaces=surfaces,
                target="nanoid",
            ), f"{relative}: nanoid must remain transitive, not direct intent"
            continue
        assert basename in NPM_LOCK_SURFACE_BASENAMES
        _assert_occurrences_outside_ranges(
            surface=relative,
            target="nanoid",
            occurrences=_find_lock_occurrences(document, target="nanoid"),
            affected_ranges=NANOID_AFFECTED_RANGES,
        )


def test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges() -> None:
    """Every Router install and direct DOM carrier remains outside affected ranges."""
    surfaces = _load_tracked_npm_surfaces()
    for relative, document in surfaces.items():
        basename = PurePosixPath(relative).name
        if basename == "package.json":
            assert not _find_governed_manifest_occurrences(
                surface=relative,
                document=document,
                surfaces=surfaces,
                target="react-router",
            ), f"{relative}: react-router must remain transitive, not direct intent"
            _assert_manifest_occurrences_outside_ranges(
                surface=relative,
                target="react-router-dom",
                occurrences=_find_governed_manifest_occurrences(
                    surface=relative,
                    document=document,
                    surfaces=surfaces,
                    target="react-router-dom",
                ),
                affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
            )
            continue
        assert basename in NPM_LOCK_SURFACE_BASENAMES
        router_occurrences = _find_lock_occurrences(document, target="react-router")
        dom_occurrences = _find_lock_occurrences(document, target="react-router-dom")
        _assert_occurrences_outside_ranges(
            surface=relative,
            target="react-router",
            occurrences=router_occurrences,
            affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
        )
        _assert_occurrences_outside_ranges(
            surface=relative,
            target="react-router-dom",
            occurrences=dom_occurrences,
            affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
        )
        _assert_react_router_dom_dependency_edges(
            surface=relative,
            dom_occurrences=dom_occurrences,
            router_occurrences=router_occurrences,
        )


@pytest.mark.parametrize(
    ("field", "key", "value", "target"),
    (
        ("dependencies", "image-size", "2.0.2", "image-size"),
        ("devDependencies", "renamed-image", "npm:image-size@2.0.2", "image-size"),
        ("optionalDependencies", "pptxgenjs", "4.0.1", "pptxgenjs"),
        ("peerDependencies", "renamed-pptx", "npm:pptxgenjs@4.0.1", "pptxgenjs"),
        ("overrides", "renamed-image", "npm:image-size", "image-size"),
        (
            "dependencies",
            "renamed-image-tarball",
            "https://registry.npmjs.org/image-size/-/image-size-1.2.1.tgz",
            "image-size",
        ),
        (
            "overrides",
            "renamed-pptx-tarball",
            "https://registry.npmjs.org/pptxgenjs/-/pptxgenjs-4.0.1.tgz",
            "pptxgenjs",
        ),
        (
            "peerDependencies",
            "foreign-image-tarball",
            "https://example.invalid/image-size/-/image-size-1.2.1.tgz",
            "image-size",
        ),
        (
            "optionalDependencies",
            "renamed-scoped-tarball",
            "https://registry.npmjs.org/@scope%2fpkg/-/pkg-2.0.0.tgz",
            "@scope/pkg",
        ),
        (
            "dependencies",
            "renamed-local-image-tarball",
            "file:../cache/%2569mage-size/-/image-size-1.2.1.tgz?x=1#y",
            "image-size",
        ),
        (
            "overrides",
            "renamed-local-pptx-tarball",
            "../cache/other/../pptxgenjs/-/pptxgenjs-4.0.1.tgz",
            "pptxgenjs",
        ),
        (
            "peerDependencies",
            "renamed-local-scoped-tarball",
            "file:../cache/@scope%2fpkg/-/pkg-2.0.0.tgz",
            "@scope/pkg",
        ),
        ("dependencies", "nanoid", "3.3.17", "nanoid"),
    ),
)
def test_retired_graph_manifest_discovery_rejects_direct_and_alias_reintroduction(
    field: str, key: str, value: str, target: str
) -> None:
    """Direct, override, and npm-alias declarations remain visible to the guard."""
    assert _find_manifest_occurrences({field: {key: value}}, target=target)


@pytest.mark.parametrize(
    "value",
    (
        "https://registry.npmjs.org/image-sizes/-/image-sizes-1.2.1.tgz",
        "https://registry.npmjs.org/other/-/image-size-1.2.1.tgz",
        "https://registry.npmjs.org/image-size",
        "file:../cache/other/-/image-size-1.2.1.tgz",
        "file:../cache/image-size/other/image-size-1.2.1.tgz",
        "file:../cache/image-size/-/nested/image-size-1.2.1.tgz",
        "file:../cache/other/-/other-1.0.0.tgz?target=/image-size/-/image-size-1.2.1.tgz",
    ),
)
def test_manifest_tarball_discovery_ignores_package_identity_near_misses(
    value: str,
) -> None:
    """Package-identity near misses must not be misclassified as the target."""
    assert not _find_manifest_occurrences(
        {"dependencies": {"renamed-image": value}},
        target="image-size",
    )


def test_current_npm_git_classifier_matches_repository_runtime() -> None:
    """The installed npm parser, rather than a frozen Python grammar, owns Git syntax."""
    values = (
        "git+https://github.com/acme/repo.git#main",
        "git+http://example.invalid/acme/repo.git",
        "git+ssh://git@example.invalid/acme/repo.git#v1",
        "git+file:///tmp/image-size",
        "git+rsync://example.invalid/acme/repo.git",
        "git+rsync:example.invalid/acme/repo.git",
        "git+ftp://example.invalid/acme/repo.git",
        "git://example.invalid/acme/repo.git",
        "git:example.invalid/acme/repo.git",
        "alice@www.github.com:acme/repo.git",
        "git@github.com:acme/repo.git#main",
        "git@gitlab.com:acme/repo.git",
        "git@bitbucket.org:acme/repo.git",
        "git@gist.github.com:101a11beef.git",
        "git@git.sr.ht:~acme/repo.git",
        "alice:pw@github.com:/abs/repo.git",
        "alice:pw@gitlab.com:/abs/repo.git",
        "github:acme/repo#main",
        "github:acme/subgroup/repo",
        "gitlab:acme/repo",
        "gitlab:acme/subgroup/repo",
        "bitbucket:acme/repo#v1",
        "gist:101a11beef",
        "gist:user/101a11beef",
        "gist:101a11beef#main",
        "sourcehut:~acme/repo",
        "sourcehut:~acme/subgroup/repo",
        "sourcehut:acme/repo#main",
        "acme/repo#semver:^1.0.0",
        "acme/repo#branch with space",
        "https://github.com/acme/repo.git?download=1#main",
        "https://www.github.com/acme/repo",
        "https://github%2ecom/acme/repo",
        "https://github。com/acme/repo",
        "https://github.com/acme/placeholder/../repo",
        "https://github.com/acme/placeholder/%2e%2e/repo",
        r"https:\github.com/acme/repo",
        "https:/github.com/acme/repo",
        "https:github.com/acme/repo",
        r"https:\gitlab.com/acme/repo",
        "http://github.com/acme/repo",
        "ssh://git@github.com/acme/repo%2egit#main",
        "https://gitlab.com/acme/group/repo",
        "https://bitbucket.org/acme/repo",
        "https://gist.github.com/101a11beef",
        "https://gist.github.com/user/101a11beef",
        "https://gist.github.com/user/101a11beef/edit",
        "https://git.sr.ht/~acme/repo",
        "https://github.com/acme/repo/tree/main",
        "https://gitlab.com/acme/group/repo/tree/main",
        "https://gitlab.com/acme/repo/-",
        "https://bitbucket.org/acme/repo/src/main",
        "https://git.sr.ht/~acme/repo/tree/main",
    )
    classifications = _classify_current_npm_git_specs(values)

    assert classifications == {value: True for value in sorted(set(values))}


def test_current_npm_git_classifier_preserves_non_git_and_invalid_specs() -> None:
    """Local, registry, remote-tarball, and invalid npm specs remain outside Git."""
    values = (
        "file:../vendor/repo.git",
        "../vendor/repo.git",
        "./vendor/repo.git",
        "npm:image-size@1.2.1",
        "1.2.3",
        "https://registry.npmjs.org/image-size/-/image-size-1.2.1.tgz",
        "workspace:*",
        "link:../vendor/repo.git",
        "https://example.invalid/acme/repo.git.tgz",
        "https://example.invalid/acme/repo.git/README",
        "https://example.invalid/acme/repo.tgz?source=repo.git",
        "https://example.invalid/acme/repo.git",
        "git@example.invalid:acme/repo.git",
        "git@127.0.0.1:acme/repo.git",
        "git@example.com:/abs/repo.git",
        "https://example%2einvalid/acme/repo",
        "https://github%2fcom/acme/repo",
        "ssh://github%2ecom/acme/repo",
        "https://example。invalid/acme/repo",
        "https://\u200d.example/acme/repo",
        "ssh://git@example.invalid/acme/repo.git",
        "http://gitlab.com/acme/repo.git",
        "http://gist.github.com/101a11beef",
        "http://git.sr.ht/~acme/repo",
        "ssh://git@git.sr.ht/~acme/repo",
        r"ssh:\github.com/acme/repo",
        "git+git://example.invalid/acme/repo.git",
        "git+foo://example.invalid/acme/repo.git",
        "https://github.com/acme/repo/blob/main/package.json",
        "https://gitlab.com/acme/repo/-/tree/main",
        "https://gitlab.com/acme/repo/archive.tar.gz",
        "https://gitlab.com/acme/repo/archive.tar.gz.backup",
        "https://bitbucket.org/acme/repo/get/main.tar.gz",
        "https://git.sr.ht/~acme/repo/archive/main.tar.gz",
        "https://gist.github.com/user/101a11beef/raw",
        "https://github.com/acme/repo/tree/branch/../../blob/main",
        "@scope/pkg",
        "./acme/repo",
        "~/acme/repo",
        r"~\acme\repo",
        r"ssh:/\github.com/acme/repo",
        r"ssh:\/github.com/acme/repo",
        r"ssh:\\github.com/acme/repo",
        r"git+ssh://\github.com/acme/repo",
    )
    classifications = _classify_current_npm_git_specs(values)

    assert classifications == {value: False for value in sorted(set(values))}


def test_current_npm_git_classifier_uses_resolved_toolchain_and_sanitized_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The parser subprocess is absolute, npm-bundled, batched, and environment-isolated."""
    node_path = tmp_path / "bin" / "node"
    npm_cli_path = tmp_path / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js"
    npm_path = tmp_path / "bin" / "npm"
    node_path.parent.mkdir(parents=True)
    npm_cli_path.parent.mkdir(parents=True)
    node_path.write_text("node fixture", encoding="utf-8")
    npm_cli_path.write_text("npm fixture", encoding="utf-8")
    node_path.chmod(0o755)
    npm_cli_path.chmod(0o755)
    npm_path.symlink_to(npm_cli_path)

    def fake_which(name: str) -> str | None:
        return {"node": str(node_path), "npm": str(npm_path)}.get(name)

    captured: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        captured["args"] = args
        captured.update(kwargs)
        return subprocess.CompletedProcess(args, 0, stdout=b"[false,true]", stderr=b"")

    monkeypatch.setattr(shutil, "which", fake_which)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "outer.index"))
    monkeypatch.setenv("GIT_CUSTOM_PROBE", "must-not-leak")
    monkeypatch.setenv("NODE_OPTIONS", "--require=must-not-leak")
    monkeypatch.setenv("NODE_PATH", str(tmp_path / "must-not-leak"))

    classifications = _classify_current_npm_git_specs(
        ("1.2.3", "git+https://example.invalid/repo.git"),
        root=tmp_path,
    )

    assert classifications == {
        "1.2.3": False,
        "git+https://example.invalid/repo.git": True,
    }
    args = cast(list[str], captured["args"])
    assert args[0] == str(node_path)
    assert args[1] == "-e"
    assert args[2] == _NPM_PACKAGE_ARG_GIT_CLASSIFIER_JS
    assert args[3] == str(npm_cli_path)
    assert args[4] == str(tmp_path.resolve())
    parser_env = cast(dict[str, str], captured["env"])
    assert not any(key.startswith("GIT_") for key in parser_env)
    assert "NODE_OPTIONS" not in parser_env
    assert "NODE_PATH" not in parser_env
    assert captured["check"] is True
    assert captured["capture_output"] is True
    assert captured["timeout"] == 30


@pytest.mark.parametrize(
    "value",
    (
        "git@example.invalid:acme/repo.git",
        "git@127.0.0.1:acme/repo.git",
        "git@example.com:/abs/repo.git",
    ),
)
def test_git_source_owner_does_not_reclassify_npm_local_scp_near_misses(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    """Dependency-value SCP near-misses keep npm local-directory precedence."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"tools/fixture/package.json": {"dependencies": {"renamed": value}}},
    )

    test_tracked_npm_manifests_reject_current_npm_git_dependency_sources()


@pytest.mark.parametrize(
    "document",
    (
        {"dependencies": {"renamed-image": "git+file:///tmp/image-size"}},
        {"dependencies": {"renamed-image": r"https:\github.com/acme/repo"}},
        {"devDependencies": {"renamed-image": "git+ftp://example.invalid/repo.git"}},
        {"optionalDependencies": {"renamed-image": "gist:101a11beef#main"}},
        {"peerDependencies": {"renamed-image": "acme/repo#v1"}},
        {"overrides": {"carrier": {"renamed-image": "sourcehut:~acme/repo"}}},
    ),
)
def test_git_source_owner_rejects_each_governed_manifest_position(
    monkeypatch: pytest.MonkeyPatch,
    document: dict[str, object],
) -> None:
    """Every named carrier field reaches the executable current-index owner."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"scripts/business_collateral/package.json": document},
    )

    with pytest.raises(AssertionError, match="npm-classified Git dependency source"):
        test_tracked_npm_manifests_reject_current_npm_git_dependency_sources()


def test_retired_graph_guard_rejects_repository_relative_target_tarball(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A renamed local tarball cannot bypass the retired-graph owner guard."""
    carrier = "file:../cache/%2569mage-size/-/image-size-1.2.1.tgz?x=1#y"
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "scripts/business_collateral/package.json": {"dependencies": {"renamed-image": carrier}}
        },
    )

    with pytest.raises(AssertionError, match="retired image-size declaration"):
        test_retired_pptx_graph_stays_absent_from_all_tracked_npm_surfaces()


@pytest.mark.parametrize(
    "local_spec",
    (
        "file:../vendor/image-size",
        "../vendor/image-size",
        r"file:..\vendor\image-size",
        "file:../vendor/%69mage-size",
    ),
)
def test_manifest_discovery_resolves_renamed_tracked_local_package_carrier(
    local_spec: str,
) -> None:
    """A renamed local dependency inherits identity from its tracked manifest."""
    surface = "scripts/business_collateral/package.json"
    target_surface = "scripts/vendor/image-size/package.json"
    document = {"dependencies": {"renamed-image": local_spec}}
    surfaces = {
        surface: document,
        target_surface: {"name": "image-size", "version": "1.2.1"},
    }

    assert _find_governed_manifest_occurrences(
        surface=surface,
        document=document,
        surfaces=surfaces,
        target="image-size",
    ) == {("dependencies", "renamed-image"): local_spec}


@pytest.mark.parametrize(
    ("local_spec", "target_document"),
    (
        ("file:../vendor/image-size", {"name": "other", "version": "1.0.0"}),
        ("file:../vendor/missing", None),
        ("https://example.invalid/vendor/image-size", {"name": "image-size"}),
        ("file://remote.example/image-size", {"name": "image-size"}),
    ),
)
def test_manifest_local_carrier_ignores_untracked_or_non_target_near_miss(
    local_spec: str,
    target_document: dict[str, str] | None,
) -> None:
    """Only a repository-relative tracked target manifest supplies identity."""
    surface = "scripts/business_collateral/package.json"
    document = {"dependencies": {"renamed-image": local_spec}}
    surfaces = {surface: document}
    if target_document is not None:
        surfaces["scripts/vendor/image-size/package.json"] = target_document

    assert not _find_governed_manifest_occurrences(
        surface=surface,
        document=document,
        surfaces=surfaces,
        target="image-size",
    )


@pytest.mark.parametrize(
    ("raw_path", "expected"),
    (
        ("node_modules/nanoid", "nanoid"),
        ("node_modules/carrier/node_modules/nanoid", "nanoid"),
        ("node_modules/@scope/pkg", "@scope/pkg"),
        ("node_modules/carrier/node_modules/@scope/pkg", "@scope/pkg"),
        ("node_modules/@acme/nanoid", "@acme/nanoid"),
        ("node_modules/other/nanoid", None),
        ("node_modules/nanoid/extra", None),
        ("node_modules/@scope", None),
        ("node_modules/@/pkg", None),
        ("/node_modules/nanoid", None),
        (r"node_modules\nanoid", None),
        ("node_modules/../node_modules/nanoid", None),
        ("", None),
    ),
)
def test_lock_path_identity_uses_complete_post_node_modules_package_name(
    raw_path: str,
    expected: str | None,
) -> None:
    """Scoped packages retain their scope and unrelated basenames stay unrelated."""
    assert _lock_path_package_identity(raw_path) == expected


def test_nanoid_owner_allows_unrelated_scoped_package_with_same_basename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A legitimate @scope/nanoid artifact is not the unscoped security target."""
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "node_modules/@acme/nanoid": {
                "version": "1.0.0",
                "resolved": "https://registry.npmjs.org/@acme/nanoid/-/nanoid-1.0.0.tgz",
                "integrity": "sha512-scoped",
            }
        },
    }
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"package-lock.json": lock},
    )

    test_nanoid_occurrences_stay_outside_all_reconciled_affected_ranges()
    assert not _find_lock_occurrences(lock, target="nanoid")
    assert set(_find_lock_occurrences(lock, target="@acme/nanoid")) == {"node_modules/@acme/nanoid"}


@pytest.mark.parametrize("field", ("bundleDependencies", "bundledDependencies"))
def test_retired_graph_manifest_discovery_rejects_bundled_reintroduction(
    field: str,
) -> None:
    """Bundled dependency declarations cannot hide a retired identity."""
    assert _find_manifest_occurrences({field: ["image-size"]}, target="image-size")


@pytest.mark.parametrize(
    ("document", "target"),
    (
        ({"overrides": {"image-size@<=2.0.2": "2.0.2"}}, "image-size"),
        ({"overrides": {"pptxgenjs@4": {"image-size": "2.0.2"}}}, "pptxgenjs"),
        ({"overrides": {"@scope/pkg@^1": {"dependency": "2.0.0"}}}, "@scope/pkg"),
    ),
)
def test_manifest_discovery_rejects_version_qualified_override_keys(
    document: dict[str, object], target: str
) -> None:
    """Version-qualified override selectors cannot hide an owned identity."""
    assert _find_manifest_occurrences(document, target=target)


@pytest.mark.parametrize(
    ("package_path", "entry"),
    (
        ("node_modules/image-size", {"version": "2.0.2"}),
        ("node_modules/renamed-image", {"name": "image-size", "version": "2.0.2"}),
        (
            "node_modules/renamed-image",
            {
                "version": "2.0.2",
                "resolved": "https://registry.npmjs.org/image-size/-/image-size-2.0.2.tgz",
            },
        ),
    ),
)
def test_retired_graph_lock_discovery_rejects_path_name_and_resolution_aliases(
    package_path: str, entry: dict[str, str]
) -> None:
    """Path, package name, and canonical registry identity are all detected."""
    document = {"lockfileVersion": 3, "packages": {package_path: entry}}
    assert _find_lock_occurrences(document, target="image-size") == {package_path: entry}


@pytest.mark.parametrize(
    ("target", "version", "encoded_target"),
    (
        ("image-size", "1.2.1", "%69mage-size"),
        ("pptxgenjs", "4.0.1", "%70ptxgenjs"),
        ("nanoid", "5.1.7", "%6eanoid"),
        ("react-router", "7.18.1", "%72eact-router"),
    ),
)
@pytest.mark.parametrize("encoded", (False, True))
def test_lock_discovery_finds_foreign_target_tarballs_before_provenance_validation(
    target: str,
    version: str,
    encoded_target: str,
    encoded: bool,
) -> None:
    """Renamed lock entries cannot hide target identity behind a mirror URL."""
    path_target = encoded_target if encoded else target
    entry = {
        "version": version,
        "resolved": (f"https://mirror.example.invalid/{path_target}/-/" f"{target}-{version}.tgz"),
        "integrity": "sha512-test",
    }
    package_path = "node_modules/renamed-carrier"
    document = {"lockfileVersion": 3, "packages": {package_path: entry}}

    assert _find_lock_occurrences(document, target=target) == {package_path: entry}


@pytest.mark.parametrize(
    ("target", "version"),
    (
        ("image-size", "1.2.1"),
        ("pptxgenjs", "4.0.1"),
        ("nanoid", "5.1.7"),
        ("react-router", "7.18.1"),
    ),
)
@pytest.mark.parametrize(
    "carrier_template",
    (
        r"https://mirror.example.invalid\{target}\-\{target}-{version}.tgz",
        r"https://mirror.example.invalid\\{target}\\-\\{target}-{version}.tgz",
        r"https://mirror.example.invalid\{target}/-\{target}-{version}.tgz",
        r"https://registry.npmjs.org\{target}\-\{target}-{version}.tgz",
    ),
)
def test_lock_discovery_normalizes_whatwg_backslash_tarball_paths(
    target: str,
    version: str,
    carrier_template: str,
) -> None:
    """WHATWG-style special-scheme separators cannot hide a lock identity."""
    entry = {
        "version": version,
        "resolved": carrier_template.format(target=target, version=version),
        "integrity": "sha512-test",
    }
    package_path = "node_modules/renamed-carrier"
    document = {"lockfileVersion": 3, "packages": {package_path: entry}}

    assert _find_lock_occurrences(document, target=target) == {package_path: entry}


@pytest.mark.parametrize(
    ("target", "version", "affected_ranges"),
    (
        ("nanoid", "5.1.7", NANOID_AFFECTED_RANGES),
        ("react-router", "7.18.1", REACT_ROUTER_AFFECTED_RANGES),
    ),
)
def test_target_postcondition_rejects_foreign_tarball_after_identity_discovery(
    target: str,
    version: str,
    affected_ranges: tuple[SpecifierSet, ...],
) -> None:
    """Origin-neutral discovery remains separate from canonical provenance."""
    package_path = "node_modules/renamed-carrier"
    document = {
        "lockfileVersion": 3,
        "packages": {
            package_path: {
                "version": version,
                "resolved": (
                    f"https://mirror.example.invalid/{target}/-/" f"{target}-{version}.tgz"
                ),
                "integrity": "sha512-test",
            }
        },
    }
    occurrences = _find_lock_occurrences(document, target=target)

    with pytest.raises(AssertionError, match="resolved must be the canonical"):
        _assert_occurrences_outside_ranges(
            surface="package-lock.json",
            target=target,
            occurrences=occurrences,
            affected_ranges=affected_ranges,
        )


@pytest.mark.parametrize(
    "resolved",
    (
        "https://mirror.example.invalid/other/-/react-router-7.18.1.tgz",
        "https://mirror.example.invalid/react-routers/-/react-routers-7.18.1.tgz",
        "https://mirror.example.invalid/react-router/react-router-7.18.1.tgz",
        (
            "https://react-router.example.invalid/other/-/other-1.0.0.tgz?"
            "target=/react-router/-/react-router-7.18.1.tgz"
        ),
        (
            "https://mirror.example.invalid/other/-/other-1.0.0.tgz#"
            "/react-router/-/react-router-7.18.1.tgz"
        ),
    ),
)
def test_lock_discovery_ignores_foreign_tarball_identity_near_misses(resolved: str) -> None:
    """Foreign provenance alone cannot turn an unrelated path into the target."""
    document = {
        "lockfileVersion": 3,
        "packages": {
            "node_modules/renamed-carrier": {
                "version": "7.18.1",
                "resolved": resolved,
                "integrity": "sha512-test",
            }
        },
    }

    assert not _find_lock_occurrences(document, target="react-router")


def test_retired_graph_lock_discovery_rejects_malformed_scalar_entry() -> None:
    """A malformed package entry fails closed before it can evade discovery."""
    document = {
        "lockfileVersion": 3,
        "packages": {"node_modules/image-size": "npm:pptxgenjs@4.0.1"},
    }
    with pytest.raises(AssertionError, match="package entry must be an object"):
        _find_lock_occurrences(document, target="image-size")


@pytest.mark.parametrize(
    ("target", "version", "resolved", "affected_ranges", "message"),
    (
        (
            "nanoid",
            "5.1.16",
            "https://registry.npmjs.org/nanoid/-/nanoid-5.1.7.tgz",
            NANOID_AFFECTED_RANGES,
            "resolved tarball version must equal package version",
        ),
        (
            "react-router",
            "7.18.2",
            "https://registry.npmjs.org/react-router/-/react-router-7.18.1.tgz",
            REACT_ROUTER_AFFECTED_RANGES,
            "resolved tarball version must equal package version",
        ),
    ),
)
def test_target_postcondition_rejects_affected_tarball_behind_safe_version(
    target: str,
    version: str,
    resolved: str,
    affected_ranges: tuple[SpecifierSet, ...],
    message: str,
) -> None:
    """A safe version label cannot hide an older affected registry artifact."""
    occurrences = {
        f"node_modules/{target}": {
            "version": version,
            "resolved": resolved,
            "integrity": "sha512-test",
        }
    }
    with pytest.raises(AssertionError, match=message):
        _assert_occurrences_outside_ranges(
            surface="package-lock.json",
            target=target,
            occurrences=occurrences,
            affected_ranges=affected_ranges,
        )


@pytest.mark.parametrize("integrity", (None, ""))
def test_target_postcondition_rejects_missing_integrity(integrity: str | None) -> None:
    """A retained target package without usable integrity evidence fails closed."""
    occurrences = {
        "node_modules/nanoid": {
            "version": "5.1.16",
            "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-5.1.16.tgz",
            "integrity": integrity,
        }
    }
    with pytest.raises(AssertionError, match="integrity must be non-empty"):
        _assert_occurrences_outside_ranges(
            surface="package-lock.json",
            target="nanoid",
            occurrences=occurrences,
            affected_ranges=NANOID_AFFECTED_RANGES,
        )


@pytest.mark.parametrize(
    ("target", "version", "affected_ranges"),
    (
        ("nanoid", "3.3.17-0", NANOID_AFFECTED_RANGES),
        ("nanoid", "5.1.16-rc.1", NANOID_AFFECTED_RANGES),
        ("react-router", "7.18.2-0", REACT_ROUTER_AFFECTED_RANGES),
        ("react-router", "8.3.0-rc.1", REACT_ROUTER_AFFECTED_RANGES),
    ),
)
def test_target_postcondition_rejects_prerelease_versions(
    target: str,
    version: str,
    affected_ranges: tuple[SpecifierSet, ...],
) -> None:
    """Prerelease targets fail closed instead of bypassing stable advisory floors."""
    occurrences = {
        f"node_modules/{target}": {
            "version": version,
            "resolved": f"https://registry.npmjs.org/{target}/-/{target}-{version}.tgz",
            "integrity": "sha512-test",
        }
    }
    with pytest.raises(AssertionError, match="prerelease target versions fail closed"):
        _assert_occurrences_outside_ranges(
            surface="package-lock.json",
            target=target,
            occurrences=occurrences,
            affected_ranges=affected_ranges,
        )


@pytest.mark.parametrize(
    ("target", "version", "affected_ranges"),
    (
        ("nanoid", "3.3.17", NANOID_AFFECTED_RANGES),
        ("nanoid", "5.1.16+build.1", NANOID_AFFECTED_RANGES),
        ("react-router", "7.18.2+build.1", REACT_ROUTER_AFFECTED_RANGES),
        ("react-router", "8.3.0", REACT_ROUTER_AFFECTED_RANGES),
    ),
)
def test_target_postcondition_allows_exact_stable_npm_semver(
    target: str,
    version: str,
    affected_ranges: tuple[SpecifierSet, ...],
) -> None:
    """Exact stable npm versions remain admissible at or above fixed floors."""
    occurrences = {
        f"node_modules/{target}": {
            "version": version,
            "resolved": f"https://registry.npmjs.org/{target}/-/{target}-{version}.tgz",
            "integrity": "sha512-test",
        }
    }

    _assert_occurrences_outside_ranges(
        surface="package-lock.json",
        target=target,
        occurrences=occurrences,
        affected_ranges=affected_ranges,
    )


@pytest.mark.parametrize(
    "version",
    ("7.18", "07.18.2", "7.018.2", "7.18.02", "v7.18.2", "7.18.2rc1"),
)
def test_target_postcondition_rejects_non_exact_npm_semver(version: str) -> None:
    """Non-SemVer and PEP-style version spellings fail before range comparison."""
    occurrences = {
        "node_modules/react-router": {
            "version": version,
            "resolved": (
                "https://registry.npmjs.org/react-router/-/" f"react-router-{version}.tgz"
            ),
            "integrity": "sha512-test",
        }
    }

    with pytest.raises(AssertionError, match="version must be exact npm SemVer"):
        _assert_occurrences_outside_ranges(
            surface="package-lock.json",
            target="react-router",
            occurrences=occurrences,
            affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
        )


@pytest.mark.parametrize(
    "version",
    (
        "9007199254740992.1.1",
        "1.9007199254740992.1",
        "1.1.9007199254740992",
        f"1.1.1+{'a' * 251}",
    ),
)
def test_target_postcondition_rejects_node_semver_bound_violations(version: str) -> None:
    """Lock entries outside Node semver numeric or length bounds fail closed."""
    occurrences = {
        "node_modules/react-router": {
            "version": version,
            "resolved": (
                "https://registry.npmjs.org/react-router/-/" f"react-router-{version}.tgz"
            ),
            "integrity": "sha512-test",
        }
    }

    with pytest.raises(AssertionError, match="version must be exact npm SemVer"):
        _assert_occurrences_outside_ranges(
            surface="package-lock.json",
            target="react-router",
            occurrences=occurrences,
            affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
        )


def test_exact_npm_semver_allows_node_boundary_and_max_length_build() -> None:
    """The exact Node semver limits remain admissible, including build metadata."""
    max_component = str(_NPM_SEMVER_MAX_SAFE_INTEGER)
    max_length_version = f"1.1.1+{'a' * 250}"

    assert len(max_length_version) == _NPM_SEMVER_MAX_LENGTH
    assert _parse_exact_npm_semver(f"{max_component}.1.1") == (
        Version(f"{max_component}.1.1"),
        False,
    )
    assert _parse_exact_npm_semver(max_length_version) == (Version("1.1.1"), False)


@pytest.mark.parametrize("padding", (" ", "\t"))
def test_exact_npm_semver_rejects_raw_overlength_before_trimming(padding: str) -> None:
    """Node semver measures raw text before trimming surrounding whitespace."""
    max_length_version = f"1.1.1+{'a' * 250}"

    assert len(max_length_version) == _NPM_SEMVER_MAX_LENGTH
    assert _parse_exact_npm_semver(f"{padding}{max_length_version}") is None
    assert _parse_exact_npm_semver(f"{max_length_version}{padding}") is None


def test_manifest_and_lock_reject_raw_overlength_direct_version() -> None:
    """Direct manifest and lock values share the raw Node-semver length boundary."""
    raw_version = f"8.3.0+{'a' * 250} "
    assert len(raw_version) == _NPM_SEMVER_MAX_LENGTH + 1

    with pytest.raises(AssertionError, match="must use an exact advisory-comparable version"):
        _assert_manifest_occurrences_outside_ranges(
            surface="package.json",
            target="react-router-dom",
            occurrences={("dependencies", "react-router-dom"): raw_version},
            affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
        )

    with pytest.raises(AssertionError, match="version must be exact npm SemVer"):
        _assert_occurrences_outside_ranges(
            surface="package-lock.json",
            target="react-router",
            occurrences={
                "node_modules/react-router": {
                    "version": raw_version,
                    "resolved": (
                        "https://registry.npmjs.org/react-router/-/"
                        f"react-router-{raw_version}.tgz"
                    ),
                    "integrity": "sha512-test",
                }
            },
            affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
        )


@pytest.mark.parametrize(
    "carrier",
    (
        "npm:react-router-dom@{version}",
        "https://example.invalid/react-router-dom/-/react-router-dom-{version}.tgz",
    ),
)
def test_manifest_alias_and_tarball_bound_the_extracted_version_token(carrier: str) -> None:
    """Carrier framing is excluded from the Node-semver version-token length."""
    max_length_version = f"8.3.0+{'a' * 250}"
    overlength_version = f"{max_length_version}a"

    assert _exact_manifest_version(
        carrier.format(version=max_length_version), target="react-router-dom"
    ) == (Version("8.3.0"), False)
    assert (
        _exact_manifest_version(
            carrier.format(version=overlength_version), target="react-router-dom"
        )
        is None
    )


def _init_indexed_npm_surface_repo(root: Path, *, package_json: str = "{}\n") -> None:
    """Create a disposable Git index containing one governed npm surface."""
    root.mkdir()
    (root / ".gitignore").write_text("tmp/\n", encoding="utf-8")
    (root / "package.json").write_text(package_json, encoding="utf-8")
    _git_stdout("init", "--quiet", root=root)
    _git_stdout("add", "--", ".gitignore", "package.json", root=root)


def test_tracked_surface_inventory_ignores_untracked_tmp_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ignored scratch manifests cannot expand or poison the indexed universe."""
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "outer-hook.index"))
    repo = tmp_path / "repo"
    _init_indexed_npm_surface_repo(repo)
    scratch_manifest = repo / "tmp" / "scratch" / "package.json"
    scratch_manifest.parent.mkdir(parents=True)
    scratch_manifest.write_text("not-json\n", encoding="utf-8")

    _git_stdout("check-ignore", "--quiet", "tmp/scratch/package.json", root=repo)
    assert set(_load_tracked_npm_surfaces(root=repo)) == {"package.json"}


def test_tracked_surface_inventory_includes_nested_build_manifest(tmp_path: Path) -> None:
    """A tracked manifest remains governed under an otherwise local-looking directory."""
    repo = tmp_path / "repo"
    _init_indexed_npm_surface_repo(repo)
    nested_manifest = repo / "tools" / "build" / "package.json"
    nested_manifest.parent.mkdir(parents=True)
    nested_manifest.write_text(
        json.dumps({"dependencies": {"image-size": "2.0.2"}}) + "\n",
        encoding="utf-8",
    )
    _git_stdout("add", "--", "tools/build/package.json", root=repo)

    surfaces = _load_tracked_npm_surfaces(root=repo)

    assert set(surfaces) == {"package.json", "tools/build/package.json"}
    assert _find_manifest_occurrences(
        surfaces["tools/build/package.json"], target="image-size"
    ) == {("dependencies", "image-size"): "2.0.2"}


def test_tracked_surface_inventory_rejects_missing_indexed_file(tmp_path: Path) -> None:
    """An indexed npm surface cannot disappear from the checkout."""
    repo = tmp_path / "repo"
    _init_indexed_npm_surface_repo(repo)
    (repo / "package.json").unlink()

    with pytest.raises(AssertionError, match="tracked npm surface must be a regular file"):
        _load_tracked_npm_surfaces(root=repo)


def test_tracked_surface_inventory_rejects_non_regular_indexed_file(tmp_path: Path) -> None:
    """An indexed npm surface cannot be replaced by a directory."""
    repo = tmp_path / "repo"
    _init_indexed_npm_surface_repo(repo)
    (repo / "package.json").unlink()
    (repo / "package.json").mkdir()

    with pytest.raises(AssertionError, match="tracked npm surface must be a regular file"):
        _load_tracked_npm_surfaces(root=repo)


def test_tracked_surface_inventory_rejects_unparseable_indexed_json(tmp_path: Path) -> None:
    """An indexed npm surface must remain a readable JSON object."""
    repo = tmp_path / "repo"
    _init_indexed_npm_surface_repo(repo, package_json="not-json\n")

    with pytest.raises(AssertionError, match="npm surface must be readable UTF-8 JSON"):
        _load_tracked_npm_surfaces(root=repo)


def test_git_stdout_executes_resolved_binary_and_sanitizes_git_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use the resolved executable verbatim without leaking outer Git state."""
    resolved_git = tmp_path / "resolved-git"
    resolved_git.write_text(
        """#!/bin/sh
if [ -n "${GIT_DIR+x}" ] || [ -n "${GIT_INDEX_FILE+x}" ] || [ -n "${GIT_CUSTOM_PROBE+x}" ]; then
  exit 91
fi
printf '%s\\n' "$0"
printf '%s\\n' "$@"
""",
        encoding="utf-8",
    )
    resolved_git.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda command: str(resolved_git))
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "outer.git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "outer.index"))
    monkeypatch.setenv("GIT_CUSTOM_PROBE", "must-not-leak")

    output = _git_stdout("status", "--porcelain", root=tmp_path)

    assert output.decode("utf-8").splitlines() == [
        str(resolved_git),
        "-C",
        str(tmp_path),
        "status",
        "--porcelain",
    ]


def test_nanoid_guard_rejects_declaration_in_any_tracked_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-frontend tracked manifest cannot bypass the transitive-only invariant."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "scripts/business_collateral/package.json": {
                "dependencies": {"renamed-nanoid": "npm:nanoid@3.3.12"}
            }
        },
    )

    with pytest.raises(
        AssertionError,
        match="scripts/business_collateral/package.json: nanoid must remain transitive",
    ):
        test_nanoid_occurrences_stay_outside_all_reconciled_affected_ranges()


def test_react_router_guard_rejects_declaration_in_any_tracked_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A nested tracked manifest cannot bypass the transitive Router invariant."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "scripts/business_collateral/package.json": {
                "overrides": {"renamed-router": "npm:react-router@7.18.1"}
            }
        },
    )

    with pytest.raises(
        AssertionError,
        match="scripts/business_collateral/package.json: react-router must remain transitive",
    ):
        test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize(
    ("field", "key", "value", "message"),
    (
        (
            "dependencies",
            "react-router-dom",
            "7.18.1",
            "remains inside a reconciled affected range",
        ),
        (
            "optionalDependencies",
            "router-carrier",
            "npm:react-router-dom@7.18.1",
            "remains inside a reconciled affected range",
        ),
        (
            "peerDependencies",
            "router-carrier",
            "https://example.invalid/react-router-dom/-/react-router-dom-7.18.1.tgz",
            "lack lockfile provenance and integrity",
        ),
    ),
)
def test_react_router_guard_rejects_affected_carrier_in_any_tracked_manifest(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    key: str,
    value: str,
    message: str,
) -> None:
    """A lockless affected Router DOM carrier cannot bypass the universal guard."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "scripts/business_collateral/package.json": {field: {key: value}},
        },
    )

    with pytest.raises(AssertionError, match=message):
        test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize(
    "url",
    (
        "https://attacker.invalid/react-router-dom/-/react-router-dom-7.18.2.tgz",
        "https://registry.npmjs.org/react-router-dom/-/react-router-dom-7.18.2.tgz",
    ),
)
def test_react_router_guard_rejects_manifest_tarball_without_lock_provenance(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
) -> None:
    """A safe-looking manifest archive cannot substitute for lock integrity."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "scripts/business_collateral/package.json": {"dependencies": {"react-router-dom": url}}
        },
    )

    with pytest.raises(AssertionError, match="lack lockfile provenance and integrity"):
        test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize(
    ("dom_version", "dom_tarball_version", "message"),
    (
        ("7.18.2", "7.18.1", "resolved tarball version must equal package version"),
        ("8.3.0", "8.3.0", "must equal corresponding installed occurrence"),
    ),
)
def test_react_router_guard_validates_dom_lock_artifact_and_alignment(
    monkeypatch: pytest.MonkeyPatch,
    dom_version: str,
    dom_tarball_version: str,
    message: str,
) -> None:
    """Router DOM lock provenance and version must stay aligned with Router."""
    manifest = {"dependencies": {"react-router-dom": "7.18.2"}}
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "node_modules/react-router": {
                "version": "7.18.2",
                "resolved": ("https://registry.npmjs.org/react-router/-/react-router-7.18.2.tgz"),
                "integrity": "sha512-router",
            },
            "node_modules/react-router-dom": {
                "version": dom_version,
                "resolved": (
                    "https://registry.npmjs.org/react-router-dom/-/"
                    f"react-router-dom-{dom_tarball_version}.tgz"
                ),
                "integrity": "sha512-dom",
                "dependencies": {"react-router": dom_version},
            },
        },
    }
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"frontend/package.json": manifest, "frontend/package-lock.json": lock},
    )

    with pytest.raises(AssertionError, match=message):
        test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize(
    ("edge", "message"),
    (
        (None, "must declare an exact react-router dependency"),
        ("^7.18.2", "must declare an exact react-router dependency"),
        ("7.18.1", "remains inside a reconciled affected range"),
        ("8.3.0", "must equal react-router-dom package version"),
    ),
)
def test_react_router_guard_rejects_invalid_dom_router_dependency_edge(
    monkeypatch: pytest.MonkeyPatch,
    edge: str | None,
    message: str,
) -> None:
    """A safe DOM artifact cannot retain a missing, open, affected, or divergent edge."""
    dom_dependencies = {} if edge is None else {"react-router": edge}
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "node_modules/react-router": {
                "version": "7.18.2",
                "resolved": ("https://registry.npmjs.org/react-router/-/react-router-7.18.2.tgz"),
                "integrity": "sha512-router",
            },
            "node_modules/react-router-dom": {
                "version": "7.18.2",
                "resolved": (
                    "https://registry.npmjs.org/react-router-dom/-/" "react-router-dom-7.18.2.tgz"
                ),
                "integrity": "sha512-dom",
                "dependencies": dom_dependencies,
            },
        },
    }
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"frontend/package-lock.json": lock},
    )

    with pytest.raises(AssertionError, match=message):
        test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize(
    "router_path",
    (
        "node_modules/carrier/node_modules/react-router-dom/node_modules/react-router",
        "node_modules/carrier/node_modules/react-router",
        "node_modules/react-router",
    ),
)
def test_react_router_guard_allows_nested_or_hoisted_future_aligned_dependency_edge(
    monkeypatch: pytest.MonkeyPatch,
    router_path: str,
) -> None:
    """Future stable DOM edges may resolve a nested or hoisted aligned Router."""
    version = "8.3.0"
    lock = {
        "lockfileVersion": 3,
        "packages": {
            router_path: {
                "version": version,
                "resolved": ("https://registry.npmjs.org/react-router/-/react-router-8.3.0.tgz"),
                "integrity": "sha512-router",
            },
            "node_modules/carrier/node_modules/react-router-dom": {
                "version": version,
                "resolved": (
                    "https://registry.npmjs.org/react-router-dom/-/" "react-router-dom-8.3.0.tgz"
                ),
                "integrity": "sha512-dom",
                "dependencies": {"react-router": version},
            },
        },
    }
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"frontend/package-lock.json": lock},
    )

    test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


def test_react_router_guard_prefers_package_local_dependency_over_hoisted_occurrence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The first reachable Router wins without freezing one lockfile topology."""
    dom_version = "8.3.0"
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "node_modules/react-router": {
                "version": "7.18.2",
                "resolved": ("https://registry.npmjs.org/react-router/-/react-router-7.18.2.tgz"),
                "integrity": "sha512-hoisted-router",
            },
            "node_modules/carrier/node_modules/react-router-dom": {
                "version": dom_version,
                "resolved": (
                    "https://registry.npmjs.org/react-router-dom/-/" "react-router-dom-8.3.0.tgz"
                ),
                "integrity": "sha512-dom",
                "dependencies": {"react-router": dom_version},
            },
            ("node_modules/carrier/node_modules/react-router-dom/" "node_modules/react-router"): {
                "version": dom_version,
                "resolved": ("https://registry.npmjs.org/react-router/-/react-router-8.3.0.tgz"),
                "integrity": "sha512-package-local-router",
            },
        },
    }
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"frontend/package-lock.json": lock},
    )

    test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


def test_react_router_guard_does_not_skip_divergent_package_local_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mismatched nearest artifact cannot fall through to a matching hoisted one."""
    dom_version = "8.3.0"
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "node_modules/react-router": {
                "version": dom_version,
                "resolved": ("https://registry.npmjs.org/react-router/-/react-router-8.3.0.tgz"),
                "integrity": "sha512-hoisted-router",
            },
            "node_modules/carrier/node_modules/react-router-dom": {
                "version": dom_version,
                "resolved": (
                    "https://registry.npmjs.org/react-router-dom/-/" "react-router-dom-8.3.0.tgz"
                ),
                "integrity": "sha512-dom",
                "dependencies": {"react-router": dom_version},
            },
            ("node_modules/carrier/node_modules/react-router-dom/" "node_modules/react-router"): {
                "version": "9.0.0",
                "resolved": ("https://registry.npmjs.org/react-router/-/react-router-9.0.0.tgz"),
                "integrity": "sha512-package-local-router",
            },
        },
    }
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"frontend/package-lock.json": lock},
    )

    with pytest.raises(AssertionError, match="must equal corresponding installed occurrence"):
        test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize(
    ("package_path", "message"),
    (
        ("/node_modules/react-router-dom", "must be relative"),
        (r"node_modules\\react-router-dom", "must use POSIX separators"),
        ("node_modules/../react-router-dom", "must not traverse"),
    ),
)
def test_router_dependency_resolution_rejects_malformed_package_paths(
    package_path: str,
    message: str,
) -> None:
    """Malformed lock paths cannot participate in dependency resolution."""
    with pytest.raises(AssertionError, match=message):
        _npm_dependency_resolution_paths(package_path=package_path, target="react-router")


def test_react_router_guard_rejects_unreachable_same_version_router_occurrence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A safe Router in a sibling subtree cannot satisfy an unreachable DOM edge."""
    version = "8.3.0"
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "node_modules/other/node_modules/react-router": {
                "version": version,
                "resolved": ("https://registry.npmjs.org/react-router/-/react-router-8.3.0.tgz"),
                "integrity": "sha512-router",
            },
            "node_modules/carrier/node_modules/react-router-dom": {
                "version": version,
                "resolved": (
                    "https://registry.npmjs.org/react-router-dom/-/" "react-router-dom-8.3.0.tgz"
                ),
                "integrity": "sha512-dom",
                "dependencies": {"react-router": version},
            },
        },
    }
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"frontend/package-lock.json": lock},
    )

    with pytest.raises(AssertionError, match="no corresponding nested or hoisted"):
        test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize("value", ("^7.18.2", "npm:react-router-dom@~7.18.2"))
def test_react_router_guard_rejects_non_exact_carrier_range(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    """An open manifest range cannot stand in for one comparable safe carrier."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "scripts/business_collateral/package.json": {
                "dependencies": {"react-router-dom": value}
            },
        },
    )

    with pytest.raises(AssertionError, match="must use an exact advisory-comparable version"):
        test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize(
    "document",
    (
        {"dependencies": {"react-router-dom": "9007199254740992.1.1"}},
        {"devDependencies": {"router-carrier": "npm:react-router-dom@9007199254740992.1.1"}},
    ),
)
def test_react_router_guard_rejects_node_semver_bound_carrier_shape(
    monkeypatch: pytest.MonkeyPatch,
    document: dict[str, object],
) -> None:
    """Direct and npm-alias carriers share Node semver bounds."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"scripts/business_collateral/package.json": document},
    )

    with pytest.raises(AssertionError, match="must use an exact advisory-comparable version"):
        test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize(
    "document",
    (
        {"dependencies": {"react-router-dom": "7.18.2-0"}},
        {"devDependencies": {"router-carrier": "npm:react-router-dom@7.18.2-0"}},
        {
            "optionalDependencies": {
                "router-carrier": (
                    "https://example.invalid/react-router-dom/-/" "react-router-dom-7.18.2-0.tgz"
                )
            }
        },
        {"peerDependencies": {"react-router-dom": "7.18.2-rc.1"}},
        {"overrides": {"react-router-dom": "7.18.2-0"}},
        {"bundledDependencies": ["react-router-dom"]},
    ),
)
def test_react_router_guard_rejects_prerelease_or_unversioned_carrier_shape(
    monkeypatch: pytest.MonkeyPatch,
    document: dict[str, object],
) -> None:
    """Every governed carrier shape rejects npm prereleases or no-version bundles."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"scripts/business_collateral/package.json": document},
    )

    with pytest.raises(AssertionError, match="react-router-dom"):
        test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize(
    "value",
    ("7.18.3", "npm:react-router-dom@8.3.0", "7.18.2+build.1"),
)
def test_react_router_guard_allows_future_exact_safe_carrier(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    """Future exact stable carriers stay admissible outside reconciled ranges."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "scripts/business_collateral/package.json": {
                "dependencies": {"react-router-dom": value}
            },
        },
    )

    test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()
