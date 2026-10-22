"""Deterministic root npm dependency security guards.

RU: Проверяем, что npm-граф удерживает исправленные security postconditions.
EN: Ensure the npm graph keeps the remediated security postconditions without
freezing an individual PR's historical dependency delta.
"""

from __future__ import annotations

import base64
import binascii
import gzip
import hashlib
import hmac
import io
import json
import math
import os
import posixpath
import re
import shutil
import ssl
import subprocess
import tarfile
import tempfile
import time
import zlib
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast
from urllib.parse import unquote, urlparse
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_PACKAGE_JSON = REPO_ROOT / "package.json"
ROOT_LOCK_JSON = REPO_ROOT / "package-lock.json"
NPM_SURFACE_BASENAMES = frozenset({"package.json", "package-lock.json", "npm-shrinkwrap.json"})
NPM_LOCK_SURFACE_BASENAMES = frozenset({"package-lock.json", "npm-shrinkwrap.json"})
SUPPORTED_NPM_JSON_LOCKFILE_VERSION = 3
NANOID_AFFECTED_RANGES = (
    SpecifierSet("<3.3.18"),
    SpecifierSet(">=4,<5.1.16"),
)
SMOL_TOML_AFFECTED_RANGES = (
    SpecifierSet("<=1.8.0"),  # GHSA-r4xh-jqrq-34v2
    SpecifierSet("<=1.7.0"),  # GHSA-7w5x-hrqm-74c2
    SpecifierSet("<1.6.1"),  # GHSA-v3rj-xjv7-4jmq
    SpecifierSet("<=1.3.0"),  # GHSA-pqhp-25j4-6hq9
)
REACT_ROUTER_AFFECTED_RANGES = (
    SpecifierSet(">=7.12,<7.18.2"),
    SpecifierSet(">=8,<8.3.0"),
)
_NPM_SEMVER_MAX_LENGTH = 256
_NPM_SEMVER_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_EXACT_NPM_SEMVER_RE = re.compile(
    r"^(?P<core>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))"
    r"(?P<prerelease>-(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_NPM_REGISTRY_SPEC_CLASSIFIER_JS = r"""
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");

const npmCli = fs.realpathSync(path.resolve(process.argv[1]));
const repoRoot = fs.realpathSync(path.resolve(process.argv[2]));
const npmRoot = path.dirname(path.dirname(npmCli));
const npmNodeModules = fs.realpathSync(path.join(npmRoot, "node_modules"));
const npmRequire = createRequire(npmCli);

function requireFromInstalledNpm(packageName) {
  const entry = fs.realpathSync(npmRequire.resolve(packageName));
  const relative = path.relative(npmNodeModules, entry);
  const escapesNpmTree =
    relative === ".." ||
    relative.startsWith(`..${path.sep}`) ||
    path.isAbsolute(relative);
  if (!relative || escapesNpmTree || relative.split(path.sep)[0] !== packageName) {
    throw new Error(`${packageName} must resolve from the installed npm tree: ${entry}`);
  }
  return npmRequire(entry);
}

const packageArg = requireFromInstalledNpm("npm-package-arg");
const semver = requireFromInstalledNpm("semver");
const specs = JSON.parse(fs.readFileSync(0, "utf8"));
if (
  !Array.isArray(specs) ||
  specs.some(
    (spec) =>
      typeof spec !== "string" ||
      spec.length === 0 ||
      spec.trim() !== spec ||
      !/^[\x00-\x7F]+$/.test(spec),
  )
) {
  throw new TypeError("npm registry specs must be normalized ASCII strings");
}
const classifications = specs.map((spec) => {
  try {
    const parsed = packageArg.resolve("pulseplate-guard", spec, repoRoot);
    const isRegistrySelector = parsed.type === "version" || parsed.type === "range";
    return isRegistrySelector && semver.validRange(spec, { loose: false }) !== null;
  } catch (_error) {
    return false;
  }
});
process.stdout.write(JSON.stringify(classifications));
"""


def _load_json(path: Path) -> dict[str, Any]:
    """RU/EN: Read one governed UTF-8 JSON object or fail closed."""
    try:
        document = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_npm_json_duplicates
        )
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


def _canonical_registry_tarball_identity(value: object) -> tuple[str, str] | None:
    """Return exact package identity/version for one canonical npm tarball URL."""
    if not isinstance(value, str) or not value.isascii():
        return None
    candidate = value.strip()
    if (
        not candidate
        or candidate != value
        or any(ord(character) <= 0x20 or ord(character) == 0x7F for character in candidate)
        or "\\" in candidate
        or "%" in candidate
    ):
        return None
    parsed = urlparse(candidate)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "registry.npmjs.org"
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        return None
    path_parts = parsed.path.split("/")
    if len(path_parts) == 4 and path_parts[0] == "":
        package_name, separator, filename = path_parts[1:]
        if not package_name or package_name.startswith("@"):
            return None
        identity = package_name
        basename = package_name
    elif len(path_parts) == 5 and path_parts[0] == "":
        scope, package_name, separator, filename = path_parts[1:]
        if not scope.startswith("@") or len(scope) == 1 or not package_name:
            return None
        identity = f"{scope}/{package_name}"
        basename = package_name
    else:
        return None
    if separator != "-" or not filename.startswith(f"{basename}-") or not filename.endswith(".tgz"):
        return None
    raw_version = filename[len(basename) + 1 : -len(".tgz")]
    parsed_version = _parse_exact_npm_semver(raw_version)
    if parsed_version is None:
        return None
    return identity, raw_version


def _tarball_identity_matches(value: object, *, target: str) -> bool:
    """Match a target only through exact canonical npm-registry identity."""
    parsed_identity = _canonical_registry_tarball_identity(value)
    return parsed_identity is not None and parsed_identity[0] == target


def _normalized_npm_registry_spec(value: object) -> str | None:
    """Normalize one eligible manifest leaf before npm owns its selector grammar."""
    if not isinstance(value, str) or not value.isascii():
        return None
    candidate = value.strip()
    return candidate or None


def _resolve_current_npm_registry_parser_runtime() -> tuple[str, str]:
    """Resolve the physical Node executable and installed npm CLI or fail closed."""
    node_binary = shutil.which("node")
    npm_binary = shutil.which("npm")
    assert node_binary is not None, "node is required for npm registry-spec guards"
    assert npm_binary is not None, "npm is required for npm registry-spec guards"
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
        resolved_node = node_path.resolve(strict=True)
        resolved_npm_cli = npm_path.resolve(strict=True)
    except OSError as exc:
        raise AssertionError("npm registry-spec toolchain must resolve to regular files") from exc
    assert resolved_node.is_file() and os.access(
        resolved_node, os.X_OK
    ), "resolved node binary must be an executable file"
    assert resolved_npm_cli.is_file(), "resolved npm CLI must be a regular file"
    return str(resolved_node), str(resolved_npm_cli)


def _classify_current_npm_registry_specs(
    values: Iterable[object], *, root: Path = REPO_ROOT, timeout: float = 30
) -> dict[str, bool]:
    """Batch version/range admission through parser modules owned by installed npm."""
    specs = sorted(
        {
            candidate
            for value in values
            if (candidate := _normalized_npm_registry_spec(value)) is not None
        }
    )
    if not specs:
        return {}
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise AssertionError("npm registry-spec classifier root must resolve") from exc
    assert resolved_root.is_dir(), "npm registry-spec classifier root must be a directory"
    node_binary, npm_cli = _resolve_current_npm_registry_parser_runtime()
    parser_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key not in {"NODE_OPTIONS", "NODE_PATH"}
    }
    try:
        result = subprocess.run(
            [
                node_binary,
                "-e",
                _NPM_REGISTRY_SPEC_CLASSIFIER_JS,
                npm_cli,
                str(resolved_root),
            ],
            check=True,
            input=json.dumps(specs, ensure_ascii=True).encode("utf-8"),
            capture_output=True,
            env=parser_env,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise AssertionError("npm registry-spec classifier execution failed") from exc
    try:
        classifications = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AssertionError("npm registry-spec classifier returned invalid UTF-8 JSON") from exc
    assert isinstance(classifications, list), "npm registry-spec classifier must return a list"
    assert len(classifications) == len(specs), "npm registry-spec classifier result count drift"
    assert all(
        type(value) is bool for value in classifications
    ), "npm registry-spec classifier results must be booleans"
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
            if _override_key_matches(key=key, target=target):
                if isinstance(child, dict):
                    if "." in child:
                        occurrences[(*child_path, ".")] = child["."]
                else:
                    occurrences[child_path] = child
            elif _dependency_identity_matches(key=key, value=child, target=target):
                occurrences[child_path] = child
            walk_overrides(child, child_path)

    walk_overrides(document.get("overrides"), ("overrides",))
    for field in ("bundleDependencies", "bundledDependencies"):
        bundled = document.get(field)
        if isinstance(bundled, list) and target in bundled:
            occurrences[(field, str(bundled.index(target)))] = target
    return occurrences


def _find_opaque_npm_dependency_source_occurrences(
    document: dict[str, Any],
    *,
    timeout: float | None = None,
) -> dict[tuple[str, ...], object]:
    """Find dependency sources whose identity/provenance is opaque to package.json."""
    occurrences: dict[tuple[str, ...], object] = {}
    candidates: dict[tuple[str, ...], object] = {}
    if "workspaces" in document:
        occurrences[("workspaces",)] = document["workspaces"]
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
            if isinstance(child, dict):
                walk_overrides(child, child_path)
            else:
                candidates[child_path] = child

    walk_overrides(document.get("overrides"), ("overrides",))
    classifications = (
        _classify_current_npm_registry_specs(candidates.values())
        if timeout is None
        else _classify_current_npm_registry_specs(candidates.values(), timeout=timeout)
    )
    occurrences.update(
        {
            path: value
            for path, value in candidates.items()
            if (candidate := _normalized_npm_registry_spec(value)) is None
            or not classifications.get(candidate, False)
        }
    )
    return occurrences


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
    prerelease = match.group("prerelease")
    if prerelease is not None and any(
        len(identifier) > 1 and identifier.startswith("0") and identifier.isdigit()
        for identifier in prerelease[1:].split(".")
    ):
        return None
    return Version(core), prerelease is not None


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
    parsed_identity = _canonical_registry_tarball_identity(value)
    if parsed_identity is None or parsed_identity[0] != target:
        return None
    return parsed_identity[1]


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


def _require_supported_lock_packages(document: dict[str, Any], *, surface: str) -> dict[str, Any]:
    """Admit only v3's complete packages tree, never an unchecked legacy tree."""
    lockfile_version = document.get("lockfileVersion")
    assert (
        type(lockfile_version) is int and lockfile_version == SUPPORTED_NPM_JSON_LOCKFILE_VERSION
    ), f"{surface}: lockfileVersion must be exact integer 3"
    assert "dependencies" not in document, f"{surface}: top-level legacy dependencies are forbidden"
    return _require_dict_field(document, "packages", ctx=surface)


def _find_lock_occurrences(document: dict[str, Any], *, target: str) -> dict[str, dict[str, Any]]:
    """Find installed target entries by path, name, or canonical tarball identity."""
    packages = _require_supported_lock_packages(document, surface="npm lock surface")
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


def _assert_registry_lock_surface_provenance(*, surface: str, document: dict[str, Any]) -> None:
    """Require canonical provenance for every non-root package in one npm lock."""
    packages = _require_supported_lock_packages(document, surface=surface)
    for raw_path, raw_entry in packages.items():
        assert isinstance(raw_path, str), f"{surface}: package path must be text"
        if raw_path == "":
            continue
        assert isinstance(raw_entry, dict), f"{surface}:{raw_path}: package entry must be an object"
        path_identity = _lock_path_package_identity(raw_path)
        assert (
            path_identity is not None
        ), f"{surface}:{raw_path}: package path identity is malformed"
        raw_version = raw_entry.get("version")
        assert isinstance(raw_version, str), f"{surface}:{raw_path}: version must be text"
        parsed_version = _parse_exact_npm_semver(raw_version)
        assert parsed_version is not None, f"{surface}:{raw_path}: version must be exact npm SemVer"
        tarball_identity = _canonical_registry_tarball_identity(raw_entry.get("resolved"))
        assert (
            tarball_identity is not None
        ), f"{surface}:{raw_path}: resolved must be an exact canonical npm registry tarball"
        resolved_identity, resolved_version = tarball_identity
        assert (
            resolved_version == raw_version
        ), f"{surface}:{raw_path}: resolved tarball version must equal package version"
        explicit_name = raw_entry.get("name")
        if explicit_name is None:
            assert (
                resolved_identity == path_identity
            ), f"{surface}:{raw_path}: resolved identity must equal package path identity"
        else:
            assert (
                isinstance(explicit_name, str) and explicit_name
            ), f"{surface}:{raw_path}: package name must be non-empty text"
            assert (
                resolved_identity == explicit_name
            ), f"{surface}:{raw_path}: resolved identity must equal explicit package name"
        integrity = raw_entry.get("integrity")
        assert (
            isinstance(integrity, str) and integrity.strip()
        ), f"{surface}:{raw_path}: integrity must be non-empty"


def _assert_manifest_dependency_container_shapes(*, document: dict, surface: str) -> None:
    """Keep JSON structure local while npm owns dependency-source semantics."""

    for field in (
        "dependencies",
        "devDependencies",
        "optionalDependencies",
        "peerDependencies",
        "overrides",
    ):
        if field in document:
            assert isinstance(document[field], dict), f"{surface}:{field} must be an object"
    for field in ("bundleDependencies", "bundledDependencies"):
        if field not in document:
            continue
        bundled = document[field]
        if type(bundled) is bool:
            continue
        assert isinstance(bundled, list), f"{surface}:{field} must be an array"
        assert all(
            isinstance(value, str) and value for value in bundled
        ), f"{surface}:{field} entries must be non-empty package names"
    peer_metadata = document.get("peerDependenciesMeta", {})
    assert isinstance(peer_metadata, dict), f"{surface}: peerDependenciesMeta must be an object"
    for peer, metadata in peer_metadata.items():
        assert isinstance(peer, str) and peer, f"{surface}: peer metadata name must be text"
        assert isinstance(metadata, dict), f"{surface}:{peer}: peer metadata must be an object"
        assert set(metadata) <= {"optional"}, f"{surface}:{peer}: unknown peer metadata field"
        assert (
            type(metadata.get("optional", False)) is bool
        ), f"{surface}:{peer}: peer optional must be an exact boolean"


def _assert_sha512_integrity(*, value: object, source: str) -> None:
    """Require one syntactically valid 64-byte sha512 SRI digest."""

    assert isinstance(value, str) and value.startswith(
        "sha512-"
    ), f"{source}: integrity must use sha512 SRI"
    encoded = value.removeprefix("sha512-")
    try:
        digest = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AssertionError(f"{source}: integrity must contain valid base64") from exc
    assert len(digest) == 64, f"{source}: integrity sha512 digest must be 64 bytes"


# One closed archive class in the existing provenance owner. These are byte/shape
# limits, not package/version/path allowlists or persisted approval receipts.
_NPM_BUNDLE_COMPRESSED_LIMIT = 16 * 1024 * 1024
_NPM_BUNDLE_UNPACKED_LIMIT = 32 * 1024 * 1024
_NPM_BUNDLE_MEMBER_LIMIT = 4096
_NPM_BUNDLE_JSON_LIMIT = 128
_NPM_BUNDLE_JSON_BYTES_LIMIT = 1024 * 1024
_NPM_BUNDLE_DEPTH_LIMIT = 32
# Ephemeral raw bytes only; each hit is revalidated and the total stays within
# the existing compressed-byte bound. No parsed metadata or proof is cached.
_NPM_BUNDLE_RAW_CACHE: dict[tuple[str, str], bytes] = {}
_NPM_PUBLISHED_KEYS = frozenset(
    {
        "name",
        "version",
        "description",
        "main",
        "module",
        "types",
        "typings",
        "jsnext:main",
        "type",
        "sideEffects",
        "exports",
        "browser",
        "files",
        "engines",
        "cpu",
        "os",
        "license",
        "author",
        "repository",
        "bugs",
        "homepage",
        "publishConfig",
        "keywords",
        "funding",
        "scripts",
        "dependencies",
        "devDependencies",
        "optionalDependencies",
        "peerDependencies",
        "peerDependenciesMeta",
        "overrides",
        "bundleDependencies",
        "bundledDependencies",
    }
)
_NPM_BUNDLE_ACTUAL_GRAPH_JS = r"""
const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');
const [npmArgument, root] = process.argv.slice(1);
const npmCli = fs.realpathSync(npmArgument);
const npmRoot = fs.realpathSync(path.dirname(path.dirname(npmCli)));
const nativeRequire = createRequire(npmCli);
const npmNodeModules = fs.realpathSync(path.join(npmRoot, 'node_modules'));
const npmScope = fs.realpathSync(path.join(npmRoot, 'node_modules/@npmcli'));
const arboristRoot = fs.realpathSync(path.join(npmRoot, 'node_modules/@npmcli/arborist'));
for (const ownedRoot of [npmNodeModules, npmScope, arboristRoot]) {
  const relative = path.relative(npmRoot, ownedRoot);
  if (!relative || relative === '..' || relative.startsWith('..' + path.sep) || path.isAbsolute(relative) || !fs.statSync(ownedRoot).isDirectory()) {
    throw new Error('Arborist must be physically owned by installed npm');
  }
}
const arboristEntry = fs.realpathSync(nativeRequire.resolve('@npmcli/arborist'));
for (const owner of [npmRoot, arboristRoot]) {
  const relative = path.relative(owner, arboristEntry);
  if (!relative || relative === '..' || relative.startsWith('..' + path.sep) || path.isAbsolute(relative)) {
    throw new Error('Arborist must be physically owned by installed npm');
  }
}
const Arborist = nativeRequire(arboristEntry);
(async () => {
  const tree = await new Arborist({path: root, offline: true, ignoreScripts: true,
    registry: 'https://127.0.0.1:9'}).loadActual();
  const nodes = [...tree.inventory.values()].map(n => ({
    location: n.location, name: n.package.name, version: n.package.version,
    isRoot: n.isRoot, isLink: n.isLink,
    errors: n.errors.map(e => ({code: e.code || null, message: e.message || String(e)})),
    edges: [...n.edgesOut.values()].map(e => ({name: e.name, type: e.type, spec: e.spec,
      valid: e.valid, error: e.error || null, to: e.to ? e.to.location : null})),
  }));
  process.stdout.write(JSON.stringify({node: process.version, arboristEntry, nodes}));
})().catch(error => { process.stderr.write(String(error.stack || error)); process.exitCode = 1; });
"""


@dataclass(frozen=True)
class _NpmLockMaterial:
    """Ephemeral current data, never an approval flag or reusable verdict."""

    packages: dict[str, dict[str, Any]]
    published_manifests: dict[str, dict[str, Any]]
    parent_owned: dict[str, str]


def _reject_npm_json_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        assert key not in result, f"duplicate npm JSON key: {key}"
        result[key] = value
    return result


def _decode_npm_json(raw: bytes, *, source: str) -> Any:
    def reject_constant(value: str) -> None:
        raise AssertionError(f"{source}: non-JSON numeric constant {value}")

    try:
        document = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_npm_json_duplicates,
            parse_constant=reject_constant,
        )
        pending = [(document, 0)]
        while pending:
            value, depth = pending.pop()
            assert depth <= _NPM_BUNDLE_DEPTH_LIMIT, f"{source}: npm JSON depth limit"
            if isinstance(value, dict):
                pending.extend((child, depth + 1) for child in value.values())
            elif isinstance(value, list):
                pending.extend((child, depth + 1) for child in value)
        return document
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AssertionError(f"{source}: readable UTF-8 JSON required") from exc


def _npm_bundle_remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    assert math.isfinite(remaining) and remaining > 0, "npm bundle deadline exhausted"
    return remaining


def _bundle_names(document: dict[str, Any], *, source: str) -> tuple[str, ...]:
    variants: list[tuple[str, ...]] = []
    for field in ("bundleDependencies", "bundledDependencies"):
        if field not in document:
            continue
        value = document[field]
        if value is False:
            variants.append(())
            continue
        assert isinstance(
            value, list
        ), f"{source}: published bundled dependencies need explicit array"
        assert all(
            isinstance(name, str) and _lock_path_package_identity("node_modules/" + name) == name
            for name in value
        ), f"{source}: malformed bundle identity"
        assert len(value) == len(set(value)), f"{source}: duplicate bundled dependency"
        variants.append(tuple(value))
    if len(variants) == 2:
        assert set(variants[0]) == set(
            variants[1]
        ), f"{source}: published bundled dependencies have conflicting bundle declarations"
    return variants[0] if variants else ()


class _NoNpmBundleRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        raise AssertionError("npm bundle redirects are forbidden")


def _verify_npm_bundle_sri(raw: bytes, *, integrity: object, source: str) -> None:
    assert (
        type(raw) is bytes and len(raw) <= _NPM_BUNDLE_COMPRESSED_LIMIT
    ), f"{source}: compressed npm bundle limit/type"
    _assert_sha512_integrity(value=integrity, source=source)
    assert isinstance(integrity, str)
    digest = base64.b64decode(integrity[7:], validate=True)
    assert hmac.compare_digest(
        hashlib.sha512(raw).digest(), digest
    ), f"{source}: npm bundle SRI mismatch"


def _read_npm_bundle_archive(
    *,
    url: str,
    integrity: str,
    deadline: float,
    raw_cache: dict[tuple[str, str], bytes],
) -> bytes:
    """One anonymous official fetch or SRI-revalidated raw-byte reuse; no verdict cache."""
    assert _canonical_registry_tarball_identity(url) is not None, "noncanonical bundle URL"
    key = (url, integrity)
    if key in raw_cache:
        raw = raw_cache[key]
    else:
        opener = build_opener(
            ProxyHandler({}),
            _NoNpmBundleRedirect(),
            HTTPSHandler(context=ssl.create_default_context()),
        )
        request = Request(
            url, headers={"Accept-Encoding": "identity", "User-Agent": "PulsePlate-npm-guard"}
        )
        try:
            with opener.open(request, timeout=min(10, _npm_bundle_remaining(deadline))) as response:
                assert (
                    response.status == 200 and response.geturl() == url
                ), "npm bundle HTTP/source mismatch"
                assert (
                    response.headers.get("Content-Encoding", "identity") == "identity"
                ), "encoded HTTP bundle"
                chunks: list[bytes] = []
                total = 0
                while total <= _NPM_BUNDLE_COMPRESSED_LIMIT:
                    _npm_bundle_remaining(deadline)
                    chunk = response.read1(min(65536, _NPM_BUNDLE_COMPRESSED_LIMIT + 1 - total))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                raw = b"".join(chunks)
        except (OSError, TimeoutError) as exc:
            raise AssertionError("anonymous npm bundle acquisition failed") from exc
        _npm_bundle_remaining(deadline)
        _verify_npm_bundle_sri(raw, integrity=integrity, source=url)
        if raw_cache is _NPM_BUNDLE_RAW_CACHE and (
            sum(len(value) for value in raw_cache.values()) + len(raw)
            > _NPM_BUNDLE_COMPRESSED_LIMIT
        ):
            raw_cache.clear()
        raw_cache[key] = raw
    _verify_npm_bundle_sri(raw, integrity=integrity, source=url)
    return raw


def _inspect_npm_bundle_archive(
    raw: bytes, *, deadline: float
) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Retain all bounded members; strictly decode every exact-basename package.json."""
    try:
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        unpacked = decoder.decompress(raw, _NPM_BUNDLE_UNPACKED_LIMIT + 1)
        assert len(unpacked) <= _NPM_BUNDLE_UNPACKED_LIMIT, "unpacked npm bundle limit"
        assert (
            decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
        ), "truncated/concatenated npm bundle gzip"
        files: dict[str, bytes] = {}
        documents: dict[str, Any] = {}
        seen: set[str] = set()
        next_offset = 0
        with tarfile.open(fileobj=io.BytesIO(unpacked), mode="r:") as archive:
            for member in archive:
                _npm_bundle_remaining(deadline)
                assert len(seen) < _NPM_BUNDLE_MEMBER_LIMIT, "npm bundle member limit"
                name = member.name
                path = PurePosixPath(name)
                assert (
                    name
                    and name.isascii()
                    and "\\" not in name
                    and not path.is_absolute()
                    and path.as_posix() == name.rstrip("/")
                    and all(part not in {"", ".", ".."} for part in name.rstrip("/").split("/"))
                    and path.parts[0] == "package"
                    and len(path.parts) <= _NPM_BUNDLE_DEPTH_LIMIT
                ), "unsafe npm bundle path/depth"
                canonical = path.as_posix()
                assert name == canonical or (
                    member.isdir() and name == canonical + "/"
                ), "npm member path alias"
                assert canonical not in seen, "duplicate npm bundle member"
                seen.add(canonical)
                assert (
                    member.offset == next_offset and member.offset_data - member.offset == 512
                ), "unsupported npm tar extension/header"
                assert not member.pax_headers and not member.sparse, "unsupported npm tar metadata"
                assert member.type in {
                    tarfile.REGTYPE,
                    tarfile.AREGTYPE,
                    tarfile.DIRTYPE,
                }, "unsafe npm member type"
                assert not (member.mode & 0o7000), "unsafe npm member permissions"
                assert path.parts.count("node_modules") <= 1, "nested npm bundle topology"
                if "node_modules" in path.parts:
                    assert path.parts.index("node_modules") == 1, "nonflat npm bundle topology"
                assert path.name not in {
                    "npm-shrinkwrap.json",
                    "package-lock.json",
                    ".package-lock.json",
                }, "published npm shrinkwrap/lock is unsupported"
                next_offset = member.offset_data + ((member.size + 511) // 512) * 512
                if member.isdir():
                    assert member.size == 0, "npm directory carries bytes"
                    continue
                stream = archive.extractfile(member)
                assert stream is not None, "npm member data missing"
                value = stream.read(member.size + 1)
                assert len(value) == member.size, "truncated npm member"
                files[canonical] = value
                if path.name == "package.json":
                    assert len(documents) < _NPM_BUNDLE_JSON_LIMIT, "npm JSON count limit"
                    assert len(value) <= _NPM_BUNDLE_JSON_BYTES_LIMIT, "npm JSON byte limit"
                    documents[canonical] = _decode_npm_json(value, source=canonical)
        assert len(unpacked) - next_offset >= 1024 and not any(
            unpacked[next_offset:]
        ), "npm tar missing terminal zero blocks or trailing material"
        _npm_bundle_remaining(deadline)
        return files, documents
    except (OSError, EOFError, tarfile.TarError, zlib.error) as exc:
        raise AssertionError("malformed/truncated npm bundle archive") from exc


def _assert_published_npm_manifest(
    document: dict[str, Any], *, source: str, deadline: float
) -> None:
    assert set(document) <= _NPM_PUBLISHED_KEYS, f"{source}: unknown published manifest key"
    assert "workspaces" not in document, f"{source}: workspaces unsupported"
    _assert_manifest_dependency_container_shapes(document=document, surface=source)
    assert (
        _parse_exact_npm_semver(document.get("version")) is not None
    ), f"{source}: exact version required"
    name = document.get("name")
    assert (
        isinstance(name, str) and _lock_path_package_identity("node_modules/" + name) == name
    ), f"{source}: canonical published identity required"
    for field in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        for identity in document.get(field, {}):
            assert (
                isinstance(identity, str)
                and _lock_path_package_identity("node_modules/" + identity) == identity
            ), f"{source}: malformed dependency identity"
    opaque = _find_opaque_npm_dependency_source_occurrences(
        document, timeout=min(30, _npm_bundle_remaining(deadline))
    )
    assert not opaque, f"{source}: opaque published dependency source"


def _native_npm_bundle_graph(
    *,
    files: dict[str, bytes],
    manifests: dict[str, dict[str, Any]],
    parent_name: str,
    deadline: float,
) -> dict[str, Any]:
    """Read actual metadata with Arborist physically bound to installed npm; never reify."""
    node, cli = _resolve_current_npm_registry_parser_runtime()
    npm_root = Path(cli).parent.parent.resolve(strict=True)
    npm_node_modules = (npm_root / "node_modules").resolve(strict=True)
    npm_scope = (npm_root / "node_modules/@npmcli").resolve(strict=True)
    arborist_root = (npm_root / "node_modules/@npmcli/arborist").resolve(strict=True)
    for owned_root in (npm_node_modules, npm_scope, arborist_root):
        assert (
            owned_root != npm_root and owned_root.is_relative_to(npm_root) and owned_root.is_dir()
        ), "Arborist must be physically owned by installed npm"
    api = _load_json(arborist_root / "package.json")
    assert isinstance(api.get("main"), str), "Arborist entry metadata missing"
    entry = (arborist_root / api["main"]).resolve(strict=True)
    assert (
        entry.is_relative_to(npm_root) and entry.is_relative_to(arborist_root) and entry.is_file()
    ), "Arborist entry outside npm"
    bound_paths = [
        Path(node),
        Path(cli),
        npm_root / "package.json",
        arborist_root / "package.json",
        entry,
    ]
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in bound_paths]
    parent = manifests["package/package.json"]
    with tempfile.TemporaryDirectory(prefix="pulseplate-npm-bundle-") as directory:
        temporary = Path(directory).resolve(strict=True)
        tree = temporary / "tree"
        tree.mkdir(mode=0o700)
        wrapper = {
            "name": "synthetic-archive-graph-inspection",
            "version": "0.0.0",
            "dependencies": {parent_name: parent["version"]},
        }
        (tree / "package.json").write_text(json.dumps(wrapper), encoding="utf-8")
        destination = tree / "node_modules" / parent_name
        destination.mkdir(mode=0o700, parents=True)
        for name, value in files.items():
            path = destination.joinpath(*PurePosixPath(name).parts[1:])
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with path.open("xb") as output:
                output.write(value)
        home = temporary / "home"
        home.mkdir(mode=0o700)
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(home),
            "TMPDIR": str(temporary),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "npm_config_offline": "true",
            "npm_config_ignore_scripts": "true",
        }
        try:
            result = subprocess.run(
                [node, "--input-type=commonjs", "-e", _NPM_BUNDLE_ACTUAL_GRAPH_JS, cli, str(tree)],
                check=False,
                capture_output=True,
                env=env,
                cwd=temporary,
                timeout=min(30, _npm_bundle_remaining(deadline)),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise AssertionError("npm bundle native metadata execution failed") from exc
        assert result.returncode == 0 and not result.stderr, "npm bundle native metadata failed"
        assert (
            len(result.stdout) <= 4 * 1024 * 1024 and len(result.stderr) <= 64 * 1024
        ), "native npm report byte limit"
        graph = _decode_npm_json(result.stdout, source="native npm bundle graph")
    assert before == [
        hashlib.sha256(path.read_bytes()).hexdigest() for path in bound_paths
    ], "physical npm/Arborist material changed"
    assert isinstance(graph, dict) and set(graph) == {
        "node",
        "arboristEntry",
        "nodes",
    }, "native npm graph shape"
    assert graph["node"] == "v" + (REPO_ROOT / ".nvmrc").read_text().strip().removeprefix(
        "v"
    ), "native npm Node binding drift"
    assert (
        Path(graph["arboristEntry"]).resolve(strict=True) == entry
    ), "native Arborist binding drift"
    _npm_bundle_remaining(deadline)
    return graph


def _assert_npm_bundle_native_inventory(
    graph: dict[str, Any],
    *,
    manifests: dict[str, dict[str, Any]],
    parent_name: str,
) -> None:
    parent_location = "node_modules/" + parent_name
    expected = {
        "": {
            "name": "synthetic-archive-graph-inspection",
            "version": "0.0.0",
            "dependencies": {parent_name: manifests["package/package.json"]["version"]},
        }
    }
    expected.update(
        {
            parent_location + name[len("package") : -len("/package.json")]: document
            for name, document in manifests.items()
        }
    )
    nodes = graph.get("nodes")
    assert isinstance(nodes, list) and all(
        isinstance(row, dict) for row in nodes
    ), "native npm node inventory"
    locations = [row.get("location") for row in nodes]
    assert all(isinstance(value, str) for value in locations), "native npm location must be text"
    assert len(locations) == len(set(locations)) and set(locations) == set(
        expected
    ), "native npm installed-root inventory mismatch/duplicate"
    for row in nodes:
        assert set(row) == {
            "location",
            "name",
            "version",
            "isRoot",
            "isLink",
            "errors",
            "edges",
        }, "native npm node fields incomplete"
        location = row["location"]
        document = expected[location]
        assert (
            row["name"] == document["name"] and row["version"] == document["version"]
        ), "native npm identity/version drift"
        assert (
            row["isRoot"] is (location == "") and row["isLink"] is False and row["errors"] == []
        ), "native npm link/root/parse error"
        declarations: dict[str, tuple[str, str]] = {}
        for field, edge_type in (
            ("dependencies", "prod"),
            ("optionalDependencies", "optional"),
            ("peerDependencies", "peer"),
        ):
            for name, spec in document.get(field, {}).items():
                assert (
                    name not in declarations
                ), "overlapping installed dependency classes unsupported"
                selected_type = edge_type
                if field == "peerDependencies" and document.get("peerDependenciesMeta", {}).get(
                    name, {}
                ).get("optional", False):
                    selected_type = "peerOptional"
                declarations[name] = (selected_type, spec)
        edges = row["edges"]
        assert isinstance(edges, list) and all(
            isinstance(edge, dict) for edge in edges
        ), "native npm edge inventory"
        names = [edge.get("name") for edge in edges]
        assert all(isinstance(name, str) for name in names), "native npm edge name"
        assert len(names) == len(set(names)) and set(names) == set(
            declarations
        ), "native npm edge inventory incomplete/duplicate"
        for edge in edges:
            assert set(edge) == {
                "name",
                "type",
                "spec",
                "valid",
                "error",
                "to",
            }, "native npm edge fields incomplete"
            assert (edge["type"], edge["spec"]) == declarations[
                edge["name"]
            ], "native npm declaration drift"
            assert (
                edge["valid"] is True and edge["error"] is None and edge["to"] in expected
            ), "native npm edge invalid/unresolved"
            assert expected[edge["to"]]["name"] == edge["name"], "native npm alias edge unsupported"


def _assert_lock_surface_canonical_provenance(
    *,
    surface: str,
    document: dict[str, Any],
    archive_cache: dict[tuple[str, str], bytes] | None = None,
) -> _NpmLockMaterial:
    """One current ordinary/closed-flat provenance producer for every lock record."""
    binding = json.dumps(document, sort_keys=True, ensure_ascii=True)
    current = deepcopy(document)
    packages = _require_supported_lock_packages(current, surface=surface)
    parents: dict[str, tuple[str, ...]] = {}
    bundled: set[str] = set()
    for path, package in packages.items():
        assert isinstance(path, str), f"{surface}: package path must be text"
        assert isinstance(package, dict), f"{surface}:{path}: package entry must be an object"
        _assert_manifest_dependency_container_shapes(document=package, surface=f"{surface}:{path}")
        assert (
            "link" not in package
        ), f"{surface}:{path}: symbolic link lock occurrence is forbidden"
        shrinkwrap = package.get("hasShrinkwrap", False)
        assert type(shrinkwrap) is bool, f"{surface}:{path}: hasShrinkwrap must be an exact boolean"
        assert not shrinkwrap, f"{surface}:{path}: published nested shrinkwrap blocks admission"
        in_bundle = package.get("inBundle", False)
        assert type(in_bundle) is bool, f"{surface}:{path}: inBundle must be boolean"
        names = _bundle_names(package, source=f"{surface}:{path}")
        if names:
            assert path and not in_bundle, "nested bundled parent unsupported"
            parents[path] = names
        if in_bundle:
            bundled.add(path)
    parent_owned: dict[str, str] = {}
    for path in bundled:
        owners = [
            parent
            for parent in parents
            if path.startswith(parent + "/node_modules/")
            and _lock_path_package_identity(path[len(parent) + 1 :])
            == path[len(parent + "/node_modules/") :]
        ]
        assert (
            len(owners) == 1
        ), f"{surface}:{path}: bundled lock occurrence is forbidden without one flat owner"
        parent_owned[path] = owners[0]
        assert (
            "resolved" not in packages[path] and "integrity" not in packages[path]
        ), "parent-owned leaf must not fabricate independent registry provenance"
    ordinary = {path: package for path, package in packages.items() if path not in parent_owned}
    _assert_registry_lock_surface_provenance(
        surface=surface, document={**current, "packages": ordinary}
    )
    published: dict[str, dict[str, Any]] = {}
    deadline = time.monotonic() + 90
    raw_cache = archive_cache if archive_cache is not None else _NPM_BUNDLE_RAW_CACHE
    for parent_path, declared in parents.items():
        parent_entry = packages[parent_path]
        identity = _lock_path_package_identity(parent_path)
        assert (
            identity is not None and parent_entry.get("name", identity) == identity
        ), "bundle parent alias unsupported"
        owned = {
            path[len(parent_path + "/node_modules/") :]: path
            for path, owner in parent_owned.items()
            if owner == parent_path
        }
        assert set(owned) == set(
            declared
        ), "published bundled dependencies require complete flat lock inventory"
        raw = _read_npm_bundle_archive(
            url=parent_entry["resolved"],
            integrity=parent_entry["integrity"],
            deadline=deadline,
            raw_cache=raw_cache,
        )
        _verify_npm_bundle_sri(raw, integrity=parent_entry["integrity"], source=parent_path)
        files, json_documents = _inspect_npm_bundle_archive(raw, deadline=deadline)
        archive_manifests = {
            name: value
            for name, value in json_documents.items()
            if PurePosixPath(name).name == "package.json"
        }
        assert "package/package.json" in archive_manifests, "bundle outer package manifest missing"
        outer = archive_manifests["package/package.json"]
        assert isinstance(outer, dict), "bundle outer manifest must be object"
        _assert_published_npm_manifest(outer, source=parent_path, deadline=deadline)
        assert (
            outer["name"] == identity and outer["version"] == parent_entry["version"]
        ), "bundle outer identity/version mismatch"
        assert set(_bundle_names(outer, source=parent_path)) == set(
            declared
        ), "archive/lock bundle declarations differ"
        roots: dict[str, dict[str, Any]] = {"package/package.json": outer}
        for leaf_name, lock_path in owned.items():
            name = "package/node_modules/" + leaf_name + "/package.json"
            leaf = archive_manifests.get(name)
            assert isinstance(leaf, dict), "bundle archive leaf missing"
            _assert_published_npm_manifest(leaf, source=name, deadline=deadline)
            assert not _bundle_names(leaf, source=name), "nested published bundle unsupported"
            assert (
                packages[lock_path].get("name", leaf_name) == leaf_name
            ), "parent-owned lock leaf explicit identity drift"
            assert (
                leaf["name"] == leaf_name and leaf["version"] == packages[lock_path]["version"]
            ), "archive/lock leaf identity/version drift"
            for field in (
                "dependencies",
                "optionalDependencies",
                "peerDependencies",
                "peerDependenciesMeta",
            ):
                assert leaf.get(field, {}) == packages[lock_path].get(
                    field, {}
                ), "archive/lock dependency metadata drift"
            if "devDependencies" in packages[lock_path]:
                assert packages[lock_path]["devDependencies"] == leaf.get(
                    "devDependencies", {}
                ), "published dev metadata drift"
            roots[name] = leaf
            published[lock_path] = leaf
        for name, metadata in archive_manifests.items():
            if name in roots:
                continue
            owners = [
                leaf_name
                for leaf_name in owned
                if name.startswith("package/node_modules/" + leaf_name + "/")
            ]
            assert (
                len(owners) == 1 and metadata == {"type": "module"} and set(metadata) == {"type"}
            ), "unsupported nested package metadata/unknown key"
            published[parent_path + "::" + name] = metadata
        for field in (
            "dependencies",
            "optionalDependencies",
            "peerDependencies",
            "peerDependenciesMeta",
        ):
            assert outer.get(field, {}) == parent_entry.get(
                field, {}
            ), "outer archive/lock dependency drift"
        published[parent_path] = outer
        graph = _native_npm_bundle_graph(
            files=files, manifests=roots, parent_name=identity, deadline=deadline
        )
        _assert_npm_bundle_native_inventory(graph, manifests=roots, parent_name=identity)
        _verify_npm_bundle_sri(raw, integrity=parent_entry["integrity"], source=parent_path)
        _npm_bundle_remaining(deadline)
    assert (
        json.dumps(document, sort_keys=True, ensure_ascii=True) == binding
    ), "lock material changed during provenance"
    return _NpmLockMaterial(packages, published, parent_owned)


def _assert_parent_owned_occurrence(
    *, material: _NpmLockMaterial, path: str, entry: dict[str, Any], target: str
) -> None:
    """Consume returned current data, never synthesize a registry URL or SRI."""
    assert (
        path in material.parent_owned and material.packages[path] == entry
    ), "parent-owned material/entry drift"
    manifest = material.published_manifests[path]
    assert (
        manifest["name"] == target and manifest["version"] == entry["version"]
    ), "parent-owned identity/version drift"


def _assert_occurrences_outside_ranges(
    *,
    surface: str,
    target: str,
    occurrences: dict[str, dict[str, Any]],
    affected_ranges: tuple[SpecifierSet, ...],
    material: _NpmLockMaterial | None = None,
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
        if material is not None and package_path in material.parent_owned:
            _assert_parent_owned_occurrence(
                material=material, path=package_path, entry=entry, target=target
            )
        else:
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


def test_tracked_npm_manifests_reject_opaque_dependency_sources() -> None:
    """Every current dependency stays an identity-transparent registry selector."""
    surfaces = _load_tracked_npm_surfaces()
    for relative, document in surfaces.items():
        if PurePosixPath(relative).name != "package.json":
            continue
        opaque_occurrences = _find_opaque_npm_dependency_source_occurrences(document)
        nanoid_occurrences = _find_governed_manifest_occurrences(
            surface=relative,
            document=document,
            surfaces=surfaces,
            target="nanoid",
        )
        _assert_manifest_occurrences_outside_ranges(
            surface=relative,
            target="nanoid",
            occurrences=nanoid_occurrences,
            affected_ranges=NANOID_AFFECTED_RANGES,
        )
        for occurrence_path in nanoid_occurrences:
            if occurrence_path in {
                ("dependencies", "nanoid"),
                ("devDependencies", "nanoid"),
                ("optionalDependencies", "nanoid"),
                ("peerDependencies", "nanoid"),
            }:
                opaque_occurrences.pop(occurrence_path, None)
        assert (
            not opaque_occurrences
        ), f"{relative}: opaque dependency source requires separate provenance"


def test_tracked_npm_locks_require_canonical_registry_provenance() -> None:
    """Every tracked lock package has one exact canonical provenance owner."""
    surfaces = _load_tracked_npm_surfaces()
    for relative, document in surfaces.items():
        if PurePosixPath(relative).name not in NPM_LOCK_SURFACE_BASENAMES:
            continue
        _assert_lock_surface_canonical_provenance(surface=relative, document=document)


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
        material = _assert_lock_surface_canonical_provenance(surface=relative, document=document)
        for published_path, published in material.published_manifests.items():
            assert not _find_manifest_occurrences(
                published, target="pptxgenjs"
            ), f"{relative}:{published_path}: retired pptxgenjs published request"
        for published_path, published in material.published_manifests.items():
            assert not _find_manifest_occurrences(
                published, target="image-size"
            ), f"{relative}:{published_path}: retired image-size published request"
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
            _assert_manifest_occurrences_outside_ranges(
                surface=relative,
                target="nanoid",
                occurrences=_find_governed_manifest_occurrences(
                    surface=relative,
                    document=document,
                    surfaces=surfaces,
                    target="nanoid",
                ),
                affected_ranges=NANOID_AFFECTED_RANGES,
            )
            continue
        assert basename in NPM_LOCK_SURFACE_BASENAMES
        material = _assert_lock_surface_canonical_provenance(surface=relative, document=document)
        for published_path, published in material.published_manifests.items():
            _assert_manifest_occurrences_outside_ranges(
                surface=f"{relative}:{published_path}",
                target="nanoid",
                occurrences=_find_manifest_occurrences(published, target="nanoid"),
                affected_ranges=NANOID_AFFECTED_RANGES,
            )
        _assert_occurrences_outside_ranges(
            surface=relative,
            target="nanoid",
            material=material,
            occurrences=_find_lock_occurrences(document, target="nanoid"),
            affected_ranges=NANOID_AFFECTED_RANGES,
        )


def test_smol_toml_occurrences_stay_outside_all_reconciled_affected_ranges() -> None:
    """Every tracked smol-toml carrier stays outside all four advisory ranges."""
    surfaces = _load_tracked_npm_surfaces()
    for relative, document in surfaces.items():
        basename = PurePosixPath(relative).name
        if basename == "package.json":
            _assert_manifest_occurrences_outside_ranges(
                surface=relative,
                target="smol-toml",
                occurrences=_find_governed_manifest_occurrences(
                    surface=relative,
                    document=document,
                    surfaces=surfaces,
                    target="smol-toml",
                ),
                affected_ranges=SMOL_TOML_AFFECTED_RANGES,
            )
            continue
        assert basename in NPM_LOCK_SURFACE_BASENAMES
        material = _assert_lock_surface_canonical_provenance(surface=relative, document=document)
        for published_path, published in material.published_manifests.items():
            _assert_manifest_occurrences_outside_ranges(
                surface=f"{relative}:{published_path}",
                target="smol-toml",
                occurrences=_find_manifest_occurrences(published, target="smol-toml"),
                affected_ranges=SMOL_TOML_AFFECTED_RANGES,
            )
        _assert_occurrences_outside_ranges(
            surface=relative,
            target="smol-toml",
            material=material,
            occurrences=_find_lock_occurrences(document, target="smol-toml"),
            affected_ranges=SMOL_TOML_AFFECTED_RANGES,
        )


def test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges() -> None:
    """Every Router install and direct DOM carrier remains outside affected ranges."""
    surfaces = _load_tracked_npm_surfaces()
    for relative, document in surfaces.items():
        basename = PurePosixPath(relative).name
        if basename == "package.json":
            _assert_manifest_occurrences_outside_ranges(
                surface=relative,
                target="react-router",
                occurrences=_find_governed_manifest_occurrences(
                    surface=relative,
                    document=document,
                    surfaces=surfaces,
                    target="react-router",
                ),
                affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
            )
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
        material = _assert_lock_surface_canonical_provenance(surface=relative, document=document)
        for published_path, published in material.published_manifests.items():
            _assert_manifest_occurrences_outside_ranges(
                surface=f"{relative}:{published_path}",
                target="react-router",
                occurrences=_find_manifest_occurrences(published, target="react-router"),
                affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
            )
        for published_path, published in material.published_manifests.items():
            _assert_manifest_occurrences_outside_ranges(
                surface=f"{relative}:{published_path}",
                target="react-router-dom",
                occurrences=_find_manifest_occurrences(published, target="react-router-dom"),
                affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
            )
        router_occurrences = _find_lock_occurrences(document, target="react-router")
        dom_occurrences = _find_lock_occurrences(document, target="react-router-dom")
        _assert_occurrences_outside_ranges(
            surface=relative,
            target="react-router",
            material=material,
            occurrences=router_occurrences,
            affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
        )
        _assert_occurrences_outside_ranges(
            surface=relative,
            target="react-router-dom",
            material=material,
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
        ("dependencies", "nanoid", "3.3.18", "nanoid"),
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


def test_current_npm_registry_classifier_accepts_version_and_range_grammar() -> None:
    """Installed npm owns exact, comparator, partial, wildcard, and union selectors."""
    values = (
        "1.2.3",
        "^1.2.3",
        "~1.2.3",
        "^5.1.0-rc.0",
        ">=1.0.0",
        "1.2.x",
        ">=1 <2",
        "1 || >=2",
        "*",
        "1.2.3 - 2.3.4",
        "  7.18.2  ",
    )

    assert _classify_current_npm_registry_specs(values) == {
        value.strip(): True for value in sorted(values)
    }


def test_current_npm_registry_classifier_rejects_non_registry_and_malformed_specs() -> None:
    """Tags, aliases, transports, paths, and malformed SemVer stay opaque."""
    values = (
        "git+https://github.com/acme/repo.git#main",
        "github:acme/repo#main",
        "acme/repo#v1",
        "git@example.invalid:acme/repo.git",
        "https://example.invalid/pkg.tgz",
        "file:../vendor/pkg",
        "../vendor/pkg",
        "workspace:*",
        "npm:other@1.2.3",
        r"ssh:/\github.com/acme/repo",
        r"git+ssh://\github.com/acme/repo",
        "latest",
        "1.2.3-01",
        "^1.2.3-01",
        "~1.2.3-alpha.01",
        "1.2.3 || latest",
    )

    assert _classify_current_npm_registry_specs(values) == {
        value: False for value in sorted(values)
    }


def test_opaque_source_discovery_rejects_ineligible_manifest_leaf_shapes() -> None:
    """Empty, Unicode, and non-string leaves never reach or bypass npm admission."""
    values: tuple[object, ...] = (
        "",
        " \t ",
        "^1.2.3١",
        "\N{NO-BREAK SPACE}1.2.3\N{NO-BREAK SPACE}",
        "\N{FIGURE SPACE}1.2.3\N{FIGURE SPACE}",
        "\N{NARROW NO-BREAK SPACE}^1.2.3\N{NARROW NO-BREAK SPACE}",
        123,
        None,
    )
    document = {"dependencies": {f"package-{index}": value for index, value in enumerate(values)}}

    assert _find_opaque_npm_dependency_source_occurrences(document) == {
        ("dependencies", f"package-{index}"): value for index, value in enumerate(values)
    }


def test_current_npm_registry_classifier_uses_one_resolved_sanitized_batch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """One absolute installed-npm parser call owns all normalized unique leaves."""
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

    calls: list[dict[str, object]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append({"args": args, **kwargs})
        return subprocess.CompletedProcess(args, 0, stdout=b"[true,true]", stderr=b"")

    monkeypatch.setattr(shutil, "which", fake_which)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "outer.index"))
    monkeypatch.setenv("GIT_CUSTOM_PROBE", "must-not-leak")
    monkeypatch.setenv("NODE_OPTIONS", "--require=must-not-leak")
    monkeypatch.setenv("NODE_PATH", str(tmp_path / "must-not-leak"))

    classifications = _classify_current_npm_registry_specs(
        ("  >=1.0.0  ", "1.2.x", ">=1.0.0", "1.2.x"),
        root=tmp_path,
    )

    assert classifications == {"1.2.x": True, ">=1.0.0": True}
    assert len(calls) == 1
    call = calls[0]
    args = cast(list[str], call["args"])
    assert args == [
        str(node_path.resolve()),
        "-e",
        _NPM_REGISTRY_SPEC_CLASSIFIER_JS,
        str(npm_cli_path.resolve()),
        str(tmp_path.resolve()),
    ]
    assert call["input"] == b'["1.2.x", ">=1.0.0"]'
    assert call["check"] is True
    assert call["capture_output"] is True
    assert call["timeout"] == 30
    parser_env = cast(dict[str, str], call["env"])
    assert not any(key.startswith("GIT_") for key in parser_env)
    assert "NODE_OPTIONS" not in parser_env
    assert "NODE_PATH" not in parser_env


@pytest.mark.parametrize(
    ("stdout", "message"),
    (
        (b"\xff", "invalid UTF-8 JSON"),
        (b"{", "invalid UTF-8 JSON"),
        (b"{}", "must return a list"),
        (b"[true]", "result count drift"),
        (b"[true,1]", "results must be booleans"),
    ),
)
def test_current_npm_registry_classifier_rejects_invalid_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stdout: bytes,
    message: str,
) -> None:
    """Invalid encoding, JSON root, cardinality, and result types fail closed."""
    monkeypatch.setitem(
        globals(),
        "_resolve_current_npm_registry_parser_runtime",
        lambda: ("/absolute/node", "/absolute/npm-cli.js"),
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 0, stdout=stdout, stderr=b""),
    )

    with pytest.raises(AssertionError, match=message):
        _classify_current_npm_registry_specs(("1.0.0", "2.0.0"), root=tmp_path)


@pytest.mark.parametrize(
    "failure",
    (
        OSError("cannot execute"),
        subprocess.TimeoutExpired("node", 30),
        subprocess.CalledProcessError(1, ["node", "-e"]),
    ),
)
def test_current_npm_registry_classifier_rejects_execution_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: BaseException,
) -> None:
    """Execution, timeout, and npm module-resolution failures fail closed."""
    monkeypatch.setitem(
        globals(),
        "_resolve_current_npm_registry_parser_runtime",
        lambda: ("/absolute/node", "/absolute/npm-cli.js"),
    )

    def fail_run(*args: object, **kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(subprocess, "run", fail_run)

    with pytest.raises(AssertionError, match="classifier execution failed"):
        _classify_current_npm_registry_specs((">=1.0.0",), root=tmp_path)


@pytest.mark.parametrize(
    ("missing", "message"),
    (("node", "node is required"), ("npm", "npm is required")),
)
def test_current_npm_registry_classifier_rejects_missing_toolchain(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    missing: str,
    message: str,
) -> None:
    """Neither parser executable may be inferred when PATH cannot resolve it."""
    executable = tmp_path / "tool"
    executable.write_text("tool fixture", encoding="utf-8")
    executable.chmod(0o755)
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name: None if name == missing else str(executable),
    )

    with pytest.raises(AssertionError, match=message):
        _resolve_current_npm_registry_parser_runtime()


def test_current_npm_registry_classifier_rejects_untrusted_relative_toolchain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PATH resolution must yield absolute executable identities."""
    monkeypatch.setattr(shutil, "which", lambda name: name)

    with pytest.raises(AssertionError, match="node binary must resolve to an absolute path"):
        _resolve_current_npm_registry_parser_runtime()


@pytest.mark.parametrize(
    "document",
    (
        {"dependencies": {"renamed-image": "git+file:///tmp/image-size"}},
        {"devDependencies": {"renamed-image": "https://example.invalid/pkg.tgz"}},
        {
            "optionalDependencies": {
                "renamed-scoped": "https://registry.npmjs.org/@scope%2fpkg/-/pkg-2.0.0.tgz"
            }
        },
        {
            "peerDependencies": {
                "renamed-local": "file:../cache/%2569mage-size/-/image-size-1.2.1.tgz"
            }
        },
        {"optionalDependencies": {"renamed-image": "gist:101a11beef#main"}},
        {"peerDependencies": {"renamed-image": "acme/repo#v1"}},
        {"overrides": {"carrier": {"renamed-image": "sourcehut:~acme/repo"}}},
        {"overrides": {"carrier": {"renamed-image": 123}}},
        {"dependencies": {"renamed-image": "^1.2.3-01"}},
        {"dependencies": {"renamed-image": "^1.2.3١"}},
        {"dependencies": {"renamed-image": "\N{NO-BREAK SPACE}1.2.3\N{NO-BREAK SPACE}"}},
    ),
)
def test_opaque_source_owner_rejects_each_governed_manifest_position(
    monkeypatch: pytest.MonkeyPatch,
    document: dict[str, object],
) -> None:
    """Every named carrier field reaches the executable opaque-source owner."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"scripts/business_collateral/package.json": document},
    )

    with pytest.raises(AssertionError, match="opaque dependency source"):
        test_tracked_npm_manifests_reject_opaque_dependency_sources()


@pytest.mark.parametrize("workspaces", ([], "1.2.3"))
def test_opaque_source_owner_rejects_workspace_topology(
    monkeypatch: pytest.MonkeyPatch,
    workspaces: object,
) -> None:
    """Any workspace field needs a separate executable-identity owner."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"scripts/business_collateral/package.json": {"workspaces": workspaces}},
    )

    with pytest.raises(AssertionError, match="opaque dependency source"):
        test_tracked_npm_manifests_reject_opaque_dependency_sources()


@pytest.mark.parametrize("value", ("1.2.3-01", "1.2.3-alpha.01", "1.2.3-00.beta"))
def test_exact_npm_semver_rejects_leading_zero_numeric_prerelease(value: str) -> None:
    """Numeric prerelease identifiers follow SemVer's no-leading-zero rule."""
    assert _parse_exact_npm_semver(value) is None


@pytest.mark.parametrize("value", ("1.2.3١", "1.2.٣", "١.2.3"))
def test_exact_npm_semver_rejects_non_ascii_core_digits(value: str) -> None:
    """npm SemVer core identifiers accept ASCII digits only."""
    assert _parse_exact_npm_semver(value) is None


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

    with pytest.raises(AssertionError, match="opaque dependency source"):
        test_tracked_npm_manifests_reject_opaque_dependency_sources()


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


def test_opaque_scoped_path_tarball_fails_generic_provenance() -> None:
    """An opaque scoped-looking path is rejected without inventing identity."""
    resolved = "https://evil.example/@carrier/image-size/-/image-size-1.2.1.tgz"
    manifest = {"dependencies": {"renamed-carrier": resolved}}
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "node_modules/renamed-carrier": {
                "version": "1.2.1",
                "resolved": resolved,
                "integrity": "sha512-test",
            }
        },
    }

    assert _find_opaque_npm_dependency_source_occurrences(manifest)
    assert not _find_lock_occurrences(lock, target="image-size")
    with pytest.raises(AssertionError, match="exact canonical npm registry tarball"):
        _assert_lock_surface_canonical_provenance(surface="package-lock.json", document=lock)


@pytest.mark.parametrize(
    ("package_path", "entry"),
    (
        (
            "node_modules/nanoid",
            {
                "version": "3.3.18",
                "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz",
                "integrity": "sha512-test",
            },
        ),
        (
            "node_modules/gensync",
            {
                "version": "1.0.0-beta.2",
                "resolved": "https://registry.npmjs.org/gensync/-/gensync-1.0.0-beta.2.tgz",
                "integrity": "sha512-test",
            },
        ),
        (
            "node_modules/@acme/pkg",
            {
                "version": "1.2.3",
                "resolved": "https://registry.npmjs.org/@acme/pkg/-/pkg-1.2.3.tgz",
                "integrity": "sha512-test",
            },
        ),
        (
            "node_modules/renamed-pkg",
            {
                "name": "@acme/pkg",
                "version": "1.2.3",
                "resolved": "https://registry.npmjs.org/@acme/pkg/-/pkg-1.2.3.tgz",
                "integrity": "sha512-test",
            },
        ),
    ),
)
def test_generic_lock_provenance_accepts_exact_canonical_records(
    package_path: str, entry: dict[str, str]
) -> None:
    """Canonical unscoped, scoped, alias, and prerelease records remain valid."""
    document = {"lockfileVersion": 3, "packages": {package_path: entry}}

    _assert_lock_surface_canonical_provenance(surface="package-lock.json", document=document)


@pytest.mark.parametrize(
    "resolved",
    (
        "https://evil.example/nanoid/-/nanoid-3.3.18.tgz",
        "http://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz",
        "https://registry.npmjs.org:443/nanoid/-/nanoid-3.3.18.tgz",
        "https://user@registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz",
        "https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz?download=1",
        "https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz#fragment",
        "https://registry.npmjs.org/%6eanoid/-/nanoid-3.3.18.tgz",
        r"https://registry.npmjs.org\nanoid\-\nanoid-3.3.18.tgz",
        "https://registry.npmjs.org/other/../nanoid/-/nanoid-3.3.18.tgz",
        " https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz",
        "https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz ",
        "https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz\n",
        "\thttps://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz",
        "https://registry.npmjs.org/na\nnoid/-/nanoid-3.3.18.tgz",
        "https://registry.npmjs.org/na\rnoid/-/nanoid-3.3.18.tgz",
        "https://registry.npmjs.org/na\tnoid/-/nanoid-3.3.18.tgz",
        "https://registry.npmjs.org/na\u0000noid/-/nanoid-3.3.18.tgz",
        "",
    ),
)
def test_generic_lock_provenance_rejects_noncanonical_sources(resolved: str) -> None:
    """No alternate authority or path spelling gains canonical provenance."""
    document = {
        "lockfileVersion": 3,
        "packages": {
            "node_modules/nanoid": {
                "version": "3.3.18",
                "resolved": resolved,
                "integrity": "sha512-test",
            }
        },
    }

    with pytest.raises(AssertionError, match="exact canonical npm registry tarball"):
        _assert_lock_surface_canonical_provenance(surface="package-lock.json", document=document)


@pytest.mark.parametrize(
    ("package_path", "entry", "message"),
    (
        (
            "node_modules/renamed-pkg",
            {
                "version": "3.3.18",
                "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz",
                "integrity": "sha512-test",
            },
            "resolved identity must equal package path identity",
        ),
        (
            "node_modules/renamed-pkg",
            {
                "name": "other",
                "version": "3.3.18",
                "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz",
                "integrity": "sha512-test",
            },
            "resolved identity must equal explicit package name",
        ),
        (
            "node_modules/nanoid",
            {
                "version": "3.3.18",
                "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.17.tgz",
                "integrity": "sha512-test",
            },
            "resolved tarball version must equal package version",
        ),
        (
            "node_modules/nanoid",
            {
                "version": "3.3.18",
                "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz",
                "integrity": "",
            },
            "integrity must be non-empty",
        ),
        (
            "node_modules/nanoid",
            {
                "version": "latest",
                "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-latest.tgz",
                "integrity": "sha512-test",
            },
            "version must be exact npm SemVer",
        ),
    ),
)
def test_generic_lock_provenance_rejects_identity_version_and_integrity_drift(
    package_path: str, entry: dict[str, str], message: str
) -> None:
    """Every canonical record keeps identity, version, and integrity aligned."""
    document = {"lockfileVersion": 3, "packages": {package_path: entry}}

    with pytest.raises(AssertionError, match=message):
        _assert_lock_surface_canonical_provenance(surface="package-lock.json", document=document)


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
        (
            {"overrides": {"pptxgenjs@4": {".": "4.0.1", "image-size": "2.0.2"}}},
            "pptxgenjs",
        ),
        (
            {"overrides": {"@scope/pkg@^1": {".": "1.2.0", "dependency": "2.0.0"}}},
            "@scope/pkg",
        ),
    ),
)
def test_manifest_discovery_rejects_version_qualified_override_keys(
    document: dict[str, object], target: str
) -> None:
    """Version-qualified override selectors cannot hide an owned identity."""
    assert _find_manifest_occurrences(document, target=target)


def test_manifest_full_object_override_validates_dot_and_walks_children() -> None:
    """A target-qualified full object owns `.` without hiding nested overrides."""
    document = {
        "overrides": {
            "react-router-dom@<=7.18.1": {
                ".": "7.18.2",
                "carrier": {"react-router-dom": "8.3.0"},
            }
        }
    }
    occurrences = _find_manifest_occurrences(document, target="react-router-dom")

    assert occurrences == {
        ("overrides", "react-router-dom@<=7.18.1", "."): "7.18.2",
        (
            "overrides",
            "react-router-dom@<=7.18.1",
            "carrier",
            "react-router-dom",
        ): "8.3.0",
    }
    _assert_manifest_occurrences_outside_ranges(
        surface="package.json",
        target="react-router-dom",
        occurrences=occurrences,
        affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
    )


def test_manifest_full_object_override_rejects_affected_dot() -> None:
    """The `.` replacement remains subject to the target's affected ranges."""
    occurrences = _find_manifest_occurrences(
        {"overrides": {"react-router-dom@<=7.18.1": {".": "7.18.1"}}},
        target="react-router-dom",
    )

    with pytest.raises(AssertionError, match="remains inside a reconciled affected range"):
        _assert_manifest_occurrences_outside_ranges(
            surface="package.json",
            target="react-router-dom",
            occurrences=occurrences,
            affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
        )


def test_manifest_full_object_without_dot_only_walks_children() -> None:
    """A nested-only full object does not claim to replace its parent package."""
    document = {
        "overrides": {
            "react-router-dom@<=7.18.1": {
                "react-router": "8.3.0",
            }
        }
    }

    assert not _find_manifest_occurrences(document, target="react-router-dom")
    assert _find_manifest_occurrences(document, target="react-router") == {
        ("overrides", "react-router-dom@<=7.18.1", "react-router"): "8.3.0"
    }


def test_lock_discovery_and_provenance_accept_canonical_v3() -> None:
    """The exact v3 packages tree remains the sole admitted lock authority."""
    entry = {
        "version": "1.9.0",
        "resolved": "https://registry.npmjs.org/smol-toml/-/smol-toml-1.9.0.tgz",
        "integrity": "sha512-test",
    }
    document = {
        "lockfileVersion": 3,
        "packages": {"node_modules/smol-toml": entry},
    }

    assert _find_lock_occurrences(document, target="smol-toml") == {"node_modules/smol-toml": entry}
    _assert_lock_surface_canonical_provenance(surface="package-lock.json", document=document)


@pytest.mark.parametrize(
    ("lockfile_version", "legacy_dependencies", "message"),
    (
        (2, None, "lockfileVersion must be exact integer 3"),
        (2, {"smol-toml": {"version": "1.6.1"}}, "lockfileVersion must be exact integer 3"),
        (3, {}, "top-level legacy dependencies are forbidden"),
        (3, {"smol-toml": {"version": "1.6.1"}}, "top-level legacy dependencies are forbidden"),
    ),
)
def test_lock_shape_rejects_legacy_tree_before_target_or_provenance_check(
    lockfile_version: int, legacy_dependencies: dict[str, Any] | None, message: str
) -> None:
    """A safe packages entry cannot conceal a vulnerable compatibility tree."""
    entry = {
        "version": "1.9.0",
        "resolved": "https://registry.npmjs.org/smol-toml/-/smol-toml-1.9.0.tgz",
        "integrity": "sha512-test",
    }
    document: dict[str, Any] = {
        "lockfileVersion": lockfile_version,
        "packages": {"node_modules/smol-toml": entry},
    }
    if legacy_dependencies is not None:
        document["dependencies"] = legacy_dependencies

    with pytest.raises(AssertionError, match=message):
        _find_lock_occurrences(document, target="smol-toml")
    with pytest.raises(AssertionError, match=message):
        _assert_lock_surface_canonical_provenance(surface="package-lock.json", document=document)


@pytest.mark.parametrize("lockfile_version", (None, 1, 2, 4, "3", 2.0, True))
def test_lock_discovery_rejects_unsupported_json_lock_versions(
    lockfile_version: object,
) -> None:
    """Missing, legacy, future, and malformed lock versions fail closed."""
    document = {"lockfileVersion": lockfile_version, "packages": {}}
    with pytest.raises(AssertionError, match="lockfileVersion must be exact integer 3"):
        _find_lock_occurrences(document, target="nanoid")
    with pytest.raises(AssertionError, match="lockfileVersion must be exact integer 3"):
        _assert_lock_surface_canonical_provenance(surface="package-lock.json", document=document)


@pytest.mark.parametrize("packages", (None, [], "not-an-object"))
def test_lock_shape_requires_packages_object_for_both_callers(packages: object) -> None:
    """No alternate packages shape bypasses target discovery or provenance."""
    document = {"lockfileVersion": 3, "packages": packages}
    with pytest.raises(AssertionError, match="'packages' must be a dict"):
        _find_lock_occurrences(document, target="smol-toml")
    with pytest.raises(AssertionError, match="'packages' must be a dict"):
        _assert_lock_surface_canonical_provenance(surface="package-lock.json", document=document)


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
def test_generic_provenance_rejects_foreign_target_shaped_tarballs(
    target: str,
    version: str,
    encoded_target: str,
    encoded: bool,
) -> None:
    """A mirror URL is rejected without becoming package-identity authority."""
    path_target = encoded_target if encoded else target
    entry = {
        "version": version,
        "resolved": (f"https://mirror.example.invalid/{path_target}/-/" f"{target}-{version}.tgz"),
        "integrity": "sha512-test",
    }
    package_path = "node_modules/renamed-carrier"
    document = {"lockfileVersion": 3, "packages": {package_path: entry}}

    assert not _find_lock_occurrences(document, target=target)
    with pytest.raises(AssertionError, match="exact canonical npm registry tarball"):
        _assert_lock_surface_canonical_provenance(surface="package-lock.json", document=document)


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
def test_generic_provenance_rejects_whatwg_backslash_tarball_paths(
    target: str,
    version: str,
    carrier_template: str,
) -> None:
    """WHATWG-style separators cannot gain canonical provenance."""
    entry = {
        "version": version,
        "resolved": carrier_template.format(target=target, version=version),
        "integrity": "sha512-test",
    }
    package_path = "node_modules/renamed-carrier"
    document = {"lockfileVersion": 3, "packages": {package_path: entry}}

    assert not _find_lock_occurrences(document, target=target)
    with pytest.raises(AssertionError, match="exact canonical npm registry tarball"):
        _assert_lock_surface_canonical_provenance(surface="package-lock.json", document=document)


@pytest.mark.parametrize(
    ("target", "version"),
    (
        ("nanoid", "5.1.7"),
        ("react-router", "7.18.1"),
    ),
)
def test_generic_provenance_rejects_foreign_tarball_before_target_postcondition(
    target: str,
    version: str,
) -> None:
    """Universal provenance rejects a foreign source before target policy."""
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
    assert not _find_lock_occurrences(document, target=target)
    with pytest.raises(AssertionError, match="exact canonical npm registry tarball"):
        _assert_lock_surface_canonical_provenance(surface="package-lock.json", document=document)


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
        ("nanoid", "3.3.18-0", NANOID_AFFECTED_RANGES),
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
        ("nanoid", "3.3.18", NANOID_AFFECTED_RANGES),
        ("nanoid", "3.3.18+build.1", NANOID_AFFECTED_RANGES),
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
        "https://registry.npmjs.org/react-router-dom/-/react-router-dom-{version}.tgz",
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


@pytest.mark.parametrize(
    "value",
    ("3.3.18", "npm:nanoid@3.3.18", "5.1.16", "npm:nanoid@5.1.16"),
)
def test_nanoid_guards_allow_safe_exact_manifest_carrier(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """A safe exact-key carrier is validated without freezing topology."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"scripts/business_collateral/package.json": {"dependencies": {"nanoid": value}}},
    )

    test_tracked_npm_manifests_reject_opaque_dependency_sources()
    test_nanoid_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize(
    ("target", "value", "affected_ranges"),
    (
        ("nanoid", ">=5.1.16", NANOID_AFFECTED_RANGES),
        ("react-router-dom", ">=7.18.2", REACT_ROUTER_AFFECTED_RANGES),
    ),
)
def test_security_target_open_range_stays_under_exact_advisory_owner(
    target: str,
    value: str,
    affected_ranges: tuple[SpecifierSet, ...],
) -> None:
    """Generic registry admission cannot replace exact advisory comparison."""
    document = {"dependencies": {target: value}}
    occurrences = _find_manifest_occurrences(document, target=target)

    assert not _find_opaque_npm_dependency_source_occurrences(document)
    with pytest.raises(AssertionError, match="must use an exact advisory-comparable version"):
        _assert_manifest_occurrences_outside_ranges(
            surface="package.json",
            target=target,
            occurrences=occurrences,
            affected_ranges=affected_ranges,
        )


def test_opaque_source_owner_rejects_renamed_safe_nanoid_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only an exact NanoID key can delegate its npm alias to the range owner."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "scripts/business_collateral/package.json": {
                "dependencies": {"renamed-id": "npm:nanoid@5.1.16"}
            }
        },
    )

    with pytest.raises(AssertionError, match="opaque dependency source"):
        test_tracked_npm_manifests_reject_opaque_dependency_sources()


@pytest.mark.parametrize(
    ("key", "value"),
    (
        ("nanoid", "3.3.17"),
        ("nanoid", "5.1.7"),
        ("renamed-nanoid", "npm:nanoid@3.3.12"),
    ),
)
def test_nanoid_guard_rejects_affected_manifest_carrier(
    monkeypatch: pytest.MonkeyPatch, key: str, value: str
) -> None:
    """Direct and identity-bound alias carriers remain inside the same range owner."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"scripts/business_collateral/package.json": {"dependencies": {key: value}}},
    )

    with pytest.raises(AssertionError, match="remains inside a reconciled affected range"):
        test_nanoid_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize(
    "manifest",
    (
        {"overrides": {"smol-toml": "1.7.1"}},
        {"overrides": {"smol-toml": "1.8.0"}},
        {"overrides": {"cspell-config-lib": {"smol-toml": "1.8.0"}}},
        {"devDependencies": {"renamed-toml": "npm:smol-toml@1.8.0"}},
    ),
)
def test_smol_toml_guard_rejects_affected_manifest_carrier(
    monkeypatch: pytest.MonkeyPatch, manifest: dict[str, Any]
) -> None:
    """An old floor, nested override, or renamed alias cannot hide an affected version."""
    monkeypatch.setitem(globals(), "_load_tracked_npm_surfaces", lambda: {"package.json": manifest})

    with pytest.raises(AssertionError, match="remains inside a reconciled affected range"):
        test_smol_toml_occurrences_stay_outside_all_reconciled_affected_ranges()


def test_smol_toml_safe_alias_still_requires_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A renamed manifest alias is opaque even when its target version is safe."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"package.json": {"devDependencies": {"renamed": "npm:smol-toml@1.9.0"}}},
    )

    with pytest.raises(AssertionError, match="opaque dependency source"):
        test_tracked_npm_manifests_reject_opaque_dependency_sources()


@pytest.mark.parametrize(
    ("package_path", "explicit_name"),
    (
        ("node_modules/cspell-config-lib/node_modules/smol-toml", None),
        ("node_modules/renamed-toml", "smol-toml"),
    ),
)
def test_smol_toml_guard_rejects_affected_nested_or_alias_lock_carrier(
    monkeypatch: pytest.MonkeyPatch, package_path: str, explicit_name: str | None
) -> None:
    """Both nested installs and lock aliases remain under the universal postcondition."""
    entry: dict[str, Any] = {
        "version": "1.8.0",
        "resolved": "https://registry.npmjs.org/smol-toml/-/smol-toml-1.8.0.tgz",
        "integrity": "sha512-test",
    }
    if explicit_name is not None:
        entry["name"] = explicit_name
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {"package-lock.json": {"lockfileVersion": 3, "packages": {package_path: entry}}},
    )

    with pytest.raises(AssertionError, match="remains inside a reconciled affected range"):
        test_smol_toml_occurrences_stay_outside_all_reconciled_affected_ranges()


@pytest.mark.parametrize(
    ("version", "resolved", "message"),
    (
        (
            "1.9",
            "https://registry.npmjs.org/smol-toml/-/smol-toml-1.9.tgz",
            "version must be exact npm SemVer",
        ),
        (
            "1.9.0",
            "https://evil.example/smol-toml/-/smol-toml-1.9.0.tgz",
            "resolved must be the canonical smol-toml registry tarball",
        ),
        (
            "1.9.0",
            "https://registry.npmjs.org/smol-toml/-/smol-toml-1.8.0.tgz",
            "resolved tarball version must equal package version",
        ),
    ),
)
def test_smol_toml_guard_rejects_malformed_or_unproven_lock_carrier(
    version: str, resolved: str, message: str
) -> None:
    """A safe-looking path cannot stand in for comparable, provenanced lock data."""
    occurrences = {
        "node_modules/smol-toml": {
            "version": version,
            "resolved": resolved,
            "integrity": "sha512-test",
        }
    }

    with pytest.raises(AssertionError, match=message):
        _assert_occurrences_outside_ranges(
            surface="package-lock.json",
            target="smol-toml",
            occurrences=occurrences,
            affected_ranges=SMOL_TOML_AFFECTED_RANGES,
        )


def test_smol_toml_guard_allows_exact_safe_current_carriers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 1.9.0 override and matching canonical lock artifact satisfy the current guard."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "package.json": {"overrides": {"smol-toml": "1.9.0"}},
            "package-lock.json": {
                "lockfileVersion": 3,
                "packages": {
                    "node_modules/smol-toml": {
                        "version": "1.9.0",
                        "resolved": "https://registry.npmjs.org/smol-toml/-/smol-toml-1.9.0.tgz",
                        "integrity": "sha512-test",
                    }
                },
            },
        },
    )

    test_smol_toml_occurrences_stay_outside_all_reconciled_affected_ranges()


def test_react_router_guard_allows_safe_exact_direct_manifest_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A safe direct Router carrier is checked without pinning transitive topology."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "scripts/business_collateral/package.json": {"dependencies": {"react-router": "7.18.2"}}
        },
    )

    test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


def test_react_router_guard_rejects_affected_alias_in_any_tracked_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An affected Router alias remains subject to the same manifest range owner."""
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "scripts/business_collateral/package.json": {
                "overrides": {"renamed-router": "npm:react-router@7.18.1"}
            }
        },
    )

    with pytest.raises(AssertionError, match="remains inside a reconciled affected range"):
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
            "https://registry.npmjs.org/react-router-dom/-/react-router-dom-7.18.1.tgz",
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


def test_react_router_guard_rejects_manifest_tarball_without_lock_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A safe-looking manifest archive cannot substitute for lock integrity."""
    url = "https://registry.npmjs.org/react-router-dom/-/react-router-dom-7.18.2.tgz"
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "scripts/business_collateral/package.json": {"dependencies": {"react-router-dom": url}}
        },
    )

    with pytest.raises(AssertionError, match="lack lockfile provenance and integrity"):
        test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges()


def test_manifest_foreign_tarball_is_rejected_by_opaque_source_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign archive fails the generic manifest provenance boundary."""
    url = "https://attacker.invalid/react-router-dom/-/react-router-dom-7.18.2.tgz"
    monkeypatch.setitem(
        globals(),
        "_load_tracked_npm_surfaces",
        lambda: {
            "scripts/business_collateral/package.json": {"dependencies": {"react-router-dom": url}}
        },
    )

    with pytest.raises(AssertionError, match="opaque dependency source"):
        test_tracked_npm_manifests_reject_opaque_dependency_sources()


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
                    "https://registry.npmjs.org/react-router-dom/-/" "react-router-dom-7.18.2-0.tgz"
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


def _synthetic_npm_bundle_archive(files: list[tuple[str, bytes]]) -> bytes:
    """Small deterministic SRI-bound fixture; never fetch published material."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:", format=tarfile.USTAR_FORMAT) as archive:
        for name, value in files:
            member = tarfile.TarInfo(name)
            member.size = len(value)
            member.mode = 0o644
            archive.addfile(member, io.BytesIO(value))
    return gzip.compress(output.getvalue(), mtime=0)


def _synthetic_npm_bundle_sri(raw: bytes) -> str:
    return "sha512-" + base64.b64encode(hashlib.sha512(raw).digest()).decode("ascii")


@pytest.fixture
def npm_flat_bundle_material(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Qualify a real native positive first; negatives reuse its observed graph."""
    parent = {
        "name": "fixture-parent",
        "version": "1.0.0",
        "dependencies": {"leaf-a": "1.0.0", "leaf-b": "1.0.0"},
        "devDependencies": {"unused-tool": "^1.0.0"},
        "bundleDependencies": ["leaf-a", "leaf-b"],
    }
    leaf_a = {"name": "leaf-a", "version": "1.0.0", "optionalDependencies": {"leaf-b": "1.0.0"}}
    leaf_b = {
        "name": "leaf-b",
        "version": "1.0.0",
        "peerDependencies": {"leaf-a": "1.0.0"},
        "peerDependenciesMeta": {"leaf-a": {"optional": True}},
    }
    documents = {
        "package/package.json": parent,
        "package/node_modules/leaf-a/package.json": leaf_a,
        "package/node_modules/leaf-b/package.json": leaf_b,
        "package/node_modules/leaf-a/dist/cjs/package.json": {"type": "module"},
    }
    files = [
        (name, json.dumps(value, sort_keys=True).encode()) for name, value in documents.items()
    ]
    files.append(
        (
            "package/node_modules/leaf-a/dist/metadata.json",
            b'// arbitrary payload comment\n{"metadataVersion":1}\n',
        )
    )
    raw = _synthetic_npm_bundle_archive(files)
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "fixture-wrapper", "version": "1.0.0"},
            "node_modules/fixture-parent": {
                **parent,
                "resolved": "https://registry.npmjs.org/fixture-parent/-/fixture-parent-1.0.0.tgz",
                "integrity": _synthetic_npm_bundle_sri(raw),
            },
            "node_modules/fixture-parent/node_modules/leaf-a": {**leaf_a, "inBundle": True},
            "node_modules/fixture-parent/node_modules/leaf-b": {**leaf_b, "inBundle": True},
        },
    }
    state: dict[str, Any] = {
        "lock": lock,
        "files": files,
        "raw": raw,
        "documents": documents,
        "reader": _read_npm_bundle_archive,
        "native": _native_npm_bundle_graph,
    }

    def no_network(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("synthetic bundle fixture attempted real network")

    def archive_bytes(**kwargs: Any) -> bytes:
        return state["raw"]

    native = _native_npm_bundle_graph

    def observe_native(**kwargs: Any) -> dict[str, Any]:
        graph = native(**kwargs)
        state["graph"] = deepcopy(graph)
        return graph

    monkeypatch.setattr(__name__ + ".build_opener", no_network)
    monkeypatch.setattr(__name__ + "._read_npm_bundle_archive", archive_bytes)
    monkeypatch.setattr(__name__ + "._native_npm_bundle_graph", observe_native)
    state["material"] = _assert_lock_surface_canonical_provenance(
        surface="synthetic/package-lock.json", document=lock
    )
    assert len(state["graph"]["nodes"]) == 4
    assert len(state["material"].parent_owned) == 2
    # Subsequent independent mutations use the actual complete native result.
    monkeypatch.setattr(
        __name__ + "._native_npm_bundle_graph", lambda **kwargs: deepcopy(state["graph"])
    )
    return state


def test_closed_bundle_positive_uses_parent_owned_data(
    npm_flat_bundle_material: dict[str, Any],
) -> None:
    state = npm_flat_bundle_material
    material = state["material"]
    path = "node_modules/fixture-parent/node_modules/leaf-a"
    _assert_occurrences_outside_ranges(
        surface="synthetic",
        target="leaf-a",
        occurrences={path: state["lock"]["packages"][path]},
        affected_ranges=(SpecifierSet("<1.0.0"),),
        material=material,
    )
    assert "integrity" not in material.packages[path]
    assert material.published_manifests["node_modules/fixture-parent"]["devDependencies"] == {
        "unused-tool": "^1.0.0"
    }


@pytest.mark.parametrize(
    "mutation,diagnostic",
    [
        ("leaf-name", "explicit identity drift"),
        ("compressed-oversized", "compressed npm bundle limit"),
        ("marker-name", "unsupported nested package metadata"),
        ("marker-deps", "unsupported nested package metadata"),
        ("marker-unknown", "unsupported nested package metadata"),
        ("marker-duplicate", "duplicate npm JSON key"),
        ("manifest-duplicate", "duplicate npm JSON key"),
        ("manifest-malformed", "readable UTF-8 JSON"),
        ("non-json-number", "non-JSON numeric constant"),
        ("deep-json", "npm JSON depth limit"),
        ("missing-leaf", "bundle archive leaf missing"),
        ("extra-leaf", "unsupported nested package metadata"),
        ("duplicate-leaf", "duplicate npm bundle member"),
        ("unsafe-path", "unsafe npm bundle path"),
        ("truncated", "truncated"),
        ("oversized", "unpacked npm bundle limit"),
        ("wrong-sri", "npm bundle SRI mismatch"),
        ("wrong-url", "canonical npm registry tarball"),
        ("second-bundle", "complete flat lock inventory"),
    ],
)
def test_closed_bundle_rejects_independent_archive_mutations(
    npm_flat_bundle_material: dict[str, Any],
    mutation: str,
    diagnostic: str,
) -> None:
    state = npm_flat_bundle_material
    files = list(state["files"])
    marker = "package/node_modules/leaf-a/dist/cjs/package.json"
    if mutation == "leaf-name":
        state["lock"]["packages"]["node_modules/fixture-parent/node_modules/leaf-a"][
            "name"
        ] = "braces"
    elif mutation == "compressed-oversized":
        state["raw"] = b"x" * (_NPM_BUNDLE_COMPRESSED_LIMIT + 1)
    elif mutation.startswith("marker-"):
        values = {
            "marker-name": b'{"type":"module","name":"braces"}',
            "marker-deps": b'{"type":"module","devDependencies":{"hidden":"npm:braces@1.0.0"}}',
            "marker-unknown": b'{"type":"module","unknown":true}',
            "marker-duplicate": b'{"type":"module","type":"module"}',
        }
        files = [(name, values[mutation] if name == marker else value) for name, value in files]
    elif mutation == "deep-json":
        files.append(("package/extra/package.json", b"[" * 33 + b"0" + b"]" * 33))
    elif mutation == "non-json-number":
        files.append(("package/extra/package.json", b'{"value":NaN}'))
    elif mutation == "manifest-malformed":
        files.append(("package/extra/package.json", b"{"))
    elif mutation == "manifest-duplicate":
        files.append(("package/extra/package.json", b'{"key":1,"key":2}'))
    elif mutation == "missing-leaf":
        files = [
            (name, value)
            for name, value in files
            if name != "package/node_modules/leaf-b/package.json"
        ]
    elif mutation == "extra-leaf":
        files.append(
            (
                "package/node_modules/leaf-extra/package.json",
                b'{"name":"leaf-extra","version":"1.0.0"}',
            )
        )
    elif mutation == "duplicate-leaf":
        files.append(files[1])
    elif mutation == "unsafe-path":
        files.append(("package/../escape.json", b"{}"))
    elif mutation == "oversized":
        state["raw"] = gzip.compress(b"0" * (_NPM_BUNDLE_UNPACKED_LIMIT + 1), mtime=0)
    elif mutation == "wrong-url":
        state["lock"]["packages"]["node_modules/fixture-parent"][
            "resolved"
        ] = "https://example.invalid/package.tgz"
    elif mutation == "second-bundle":
        state["lock"]["packages"]["node_modules/second-parent"] = {
            "version": "1.0.0",
            "bundleDependencies": ["unproved"],
            "resolved": "https://registry.npmjs.org/second-parent/-/second-parent-1.0.0.tgz",
            "integrity": _synthetic_npm_bundle_sri(state["raw"]),
        }
    if mutation not in {"oversized", "compressed-oversized", "wrong-url", "second-bundle"}:
        state["raw"] = _synthetic_npm_bundle_archive(files)
    if mutation == "truncated":
        state["raw"] = state["raw"][:-5]
    parent = state["lock"]["packages"]["node_modules/fixture-parent"]
    parent["integrity"] = _synthetic_npm_bundle_sri(state["raw"])
    if mutation == "wrong-sri":
        parent["integrity"] = _synthetic_npm_bundle_sri(b"other")
    with pytest.raises(AssertionError, match=diagnostic):
        _assert_lock_surface_canonical_provenance(surface="synthetic", document=state["lock"])


@pytest.mark.parametrize(
    "mutation,diagnostic",
    [
        ("native-error", "native npm link/root/parse error"),
        ("partial", "installed-root inventory"),
        ("duplicate-node", "installed-root inventory"),
        ("extra-node", "installed-root inventory"),
        ("missing-edge", "edge inventory"),
        ("duplicate-edge", "edge inventory"),
        ("malformed", "node inventory"),
    ],
)
def test_closed_bundle_rejects_native_inventory_mutations(
    npm_flat_bundle_material: dict[str, Any],
    mutation: str,
    diagnostic: str,
) -> None:
    state = npm_flat_bundle_material
    graph = state["graph"]
    if mutation == "native-error":
        graph["nodes"][0]["errors"] = [{"code": "SYNTHETIC", "message": "bad metadata"}]
    elif mutation == "partial":
        graph["nodes"].pop()
    elif mutation == "duplicate-node":
        graph["nodes"].append(deepcopy(graph["nodes"][0]))
    elif mutation == "extra-node":
        extra = deepcopy(graph["nodes"][0])
        extra["location"] = "node_modules/extra"
        graph["nodes"].append(extra)
    elif mutation in {"missing-edge", "duplicate-edge"}:
        row = next(row for row in graph["nodes"] if row["edges"])
        if mutation == "missing-edge":
            row["edges"].pop()
        else:
            row["edges"].append(deepcopy(row["edges"][0]))
    else:
        graph["nodes"] = "malformed"
    with pytest.raises(AssertionError, match=diagnostic):
        _assert_lock_surface_canonical_provenance(surface="synthetic", document=state["lock"])


def test_closed_bundle_preserves_input_binding(
    npm_flat_bundle_material: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = npm_flat_bundle_material

    def mutate(**kwargs: Any) -> dict[str, Any]:
        state["lock"]["packages"][""]["devDependencies"] = {"braces": "1.0.0"}
        return deepcopy(state["graph"])

    monkeypatch.setattr(__name__ + "._native_npm_bundle_graph", mutate)
    with pytest.raises(AssertionError, match="lock material changed"):
        _assert_lock_surface_canonical_provenance(surface="synthetic", document=state["lock"])


def test_closed_bundle_raw_cache_revalidates_sri(npm_flat_bundle_material: dict[str, Any]) -> None:
    state = npm_flat_bundle_material
    parent = state["lock"]["packages"]["node_modules/fixture-parent"]
    # Call the actual reader, bypassing only this fixture's archive-byte adapter.
    with pytest.raises(AssertionError, match="npm bundle SRI mismatch"):
        state["reader"](
            url=parent["resolved"],
            integrity=parent["integrity"],
            deadline=time.monotonic() + 5,
            raw_cache={(parent["resolved"], parent["integrity"]): b"mutated"},
        )


@pytest.mark.parametrize("outcome", ("nonzero", "non-json", "partial-report"))
def test_closed_bundle_native_transport_fails_closed(
    npm_flat_bundle_material: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    state = npm_flat_bundle_material
    raw = b"not-json" if outcome == "non-json" else b"{}"
    result = subprocess.CompletedProcess(
        args=[], returncode=1 if outcome == "nonzero" else 0, stdout=raw, stderr=b""
    )
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: result)
    roots = {
        name: value
        for name, value in state["documents"].items()
        if isinstance(value, dict) and "name" in value
    }
    with pytest.raises(
        AssertionError, match="native metadata failed|readable UTF-8 JSON|native npm graph shape"
    ):
        state["native"](
            files=dict(state["files"]),
            manifests=roots,
            parent_name="fixture-parent",
            deadline=time.monotonic() + 5,
        )


def _synthetic_arborist_escape(tmp_path: Path, component: str) -> tuple[Path, Path]:
    """An intact external package records any accidental require before rejection."""
    npm_root = tmp_path / "npm"
    (npm_root / "bin").mkdir(parents=True)
    cli = npm_root / "bin/npm-cli.js"
    cli.write_text("// synthetic CLI identity; never executed\n", encoding="utf-8")
    external_modules = tmp_path / "external/node_modules"
    external_scope = external_modules / "@npmcli"
    external_package = external_scope / "arborist"
    (external_package / "lib").mkdir(parents=True)
    (external_package / "package.json").write_text(
        json.dumps({"name": "@npmcli/arborist", "version": "0.0.0", "main": "lib/index.js"}),
        encoding="utf-8",
    )
    marker = tmp_path / "external-module-loaded"
    (external_package / "lib/index.js").write_text(
        "require('node:fs').writeFileSync(" + json.dumps(str(marker)) + ", 'loaded');\n"
        "module.exports = class { async loadActual() { throw new Error('external module loaded'); } };\n",
        encoding="utf-8",
    )
    if component == "package":
        (npm_root / "node_modules/@npmcli").mkdir(parents=True)
        (npm_root / "node_modules/@npmcli/arborist").symlink_to(
            external_package, target_is_directory=True
        )
    elif component == "scope":
        (npm_root / "node_modules").mkdir()
        (npm_root / "node_modules/@npmcli").symlink_to(external_scope, target_is_directory=True)
    else:
        assert component == "node_modules"
        (npm_root / "node_modules").symlink_to(external_modules, target_is_directory=True)
    return cli, marker


@pytest.mark.parametrize("component", ("package", "scope", "node_modules"))
def test_closed_bundle_python_rejects_physical_arborist_escape_before_metadata(
    npm_flat_bundle_material: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    component: str,
) -> None:
    state = npm_flat_bundle_material  # Existing genuine native positive must complete first.
    node, _ = _resolve_current_npm_registry_parser_runtime()
    cli, marker = _synthetic_arborist_escape(tmp_path, component)
    monkeypatch.setattr(
        __name__ + "._resolve_current_npm_registry_parser_runtime", lambda: (node, str(cli))
    )

    def forbid_metadata(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Arborist metadata read before ownership rejection")

    def forbid_native(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("native execution before ownership rejection")

    monkeypatch.setattr(__name__ + "._load_json", forbid_metadata)
    monkeypatch.setattr(subprocess, "run", forbid_native)
    with pytest.raises(AssertionError, match="Arborist must be physically owned by installed npm"):
        state["native"](
            files={}, manifests={}, parent_name="fixture-parent", deadline=time.monotonic() + 5
        )
    assert not marker.exists()


@pytest.mark.parametrize("component", ("package", "scope", "node_modules"))
def test_closed_bundle_javascript_rejects_physical_arborist_escape_before_require(
    npm_flat_bundle_material: dict[str, Any],
    tmp_path: Path,
    component: str,
) -> None:
    assert npm_flat_bundle_material["graph"]["nodes"]  # Genuine internal npm positive.
    node, _ = _resolve_current_npm_registry_parser_runtime()
    cli, marker = _synthetic_arborist_escape(tmp_path, component)
    result = subprocess.run(
        [node, "--input-type=commonjs", "-e", _NPM_BUNDLE_ACTUAL_GRAPH_JS, str(cli), str(tmp_path)],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode != 0
    assert b"Arborist must be physically owned by installed npm" in result.stderr
    assert not marker.exists()


@pytest.fixture
def npm_bundle_reader_cache(
    npm_flat_bundle_material: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    """The actual reader with synthetic transport and an isolated process cache."""
    state = npm_flat_bundle_material
    state.update(cache={}, fetches=[], native_calls=[], archive_calls=[], transport_error=False)
    monkeypatch.setattr(__name__ + "._NPM_BUNDLE_RAW_CACHE", state["cache"])
    monkeypatch.setattr(__name__ + "._read_npm_bundle_archive", state["reader"])

    class Response(io.BytesIO):
        status = 200
        headers: dict[str, str] = {}

        def __init__(self, url: str, raw: bytes) -> None:
            super().__init__(raw)
            self.url = url

        def geturl(self) -> str:
            return self.url

    class Opener:
        def open(self, request: Request, *, timeout: float) -> Response:
            state["fetches"].append(request.full_url)
            if state["transport_error"]:
                raise OSError("synthetic cold acquisition failure")
            return Response(request.full_url, state["raw"])

    monkeypatch.setattr(__name__ + ".build_opener", lambda *args: Opener())
    inspect = _inspect_npm_bundle_archive

    def inspect_fresh(raw: bytes, *, deadline: float) -> tuple[dict[str, bytes], dict[str, Any]]:
        state["archive_calls"].append(raw)
        return inspect(raw, deadline=deadline)

    def native_fresh(**kwargs: Any) -> dict[str, Any]:
        state["native_calls"].append(kwargs["manifests"])
        return deepcopy(state["graph"])

    monkeypatch.setattr(__name__ + "._inspect_npm_bundle_archive", inspect_fresh)
    monkeypatch.setattr(__name__ + "._native_npm_bundle_graph", native_fresh)
    return state


def test_closed_bundle_default_raw_cache_reuses_bytes_with_fresh_proofs(
    npm_bundle_reader_cache: dict[str, Any],
) -> None:
    state = npm_bundle_reader_cache
    first = _assert_lock_surface_canonical_provenance(surface="synthetic", document=state["lock"])
    second = _assert_lock_surface_canonical_provenance(surface="synthetic", document=state["lock"])
    assert first is not second
    assert len(state["fetches"]) == 1
    assert len(state["archive_calls"]) == len(state["native_calls"]) == 2
    parent = state["lock"]["packages"]["node_modules/fixture-parent"]
    assert state["cache"] == {(parent["resolved"], parent["integrity"]): state["raw"]}


def test_closed_bundle_explicit_raw_cache_stays_isolated(
    npm_bundle_reader_cache: dict[str, Any],
) -> None:
    state = npm_bundle_reader_cache
    _assert_lock_surface_canonical_provenance(surface="synthetic", document=state["lock"])
    explicit: dict[tuple[str, str], bytes] = {}
    _assert_lock_surface_canonical_provenance(
        surface="synthetic", document=state["lock"], archive_cache=explicit
    )
    _assert_lock_surface_canonical_provenance(
        surface="synthetic", document=state["lock"], archive_cache=explicit
    )
    assert explicit is not state["cache"] and explicit == state["cache"]
    assert len(state["fetches"]) == 2
    assert len(state["archive_calls"]) == len(state["native_calls"]) == 3


@pytest.mark.parametrize("mutation", ("sri", "oversize"))
def test_closed_bundle_default_raw_cache_rejects_mutation(
    npm_bundle_reader_cache: dict[str, Any],
    mutation: str,
) -> None:
    state = npm_bundle_reader_cache
    _assert_lock_surface_canonical_provenance(surface="synthetic", document=state["lock"])
    key = next(iter(state["cache"]))
    state["cache"][key] = (
        b"mutated" if mutation == "sri" else b"x" * (_NPM_BUNDLE_COMPRESSED_LIMIT + 1)
    )
    with pytest.raises(AssertionError, match="npm bundle SRI mismatch|compressed npm bundle limit"):
        _assert_lock_surface_canonical_provenance(surface="synthetic", document=state["lock"])
    assert len(state["fetches"]) == len(state["native_calls"]) == 1


def test_closed_bundle_default_raw_cache_keeps_cold_failure_explicit(
    npm_bundle_reader_cache: dict[str, Any],
) -> None:
    state = npm_bundle_reader_cache
    state["transport_error"] = True
    with pytest.raises(AssertionError, match="anonymous npm bundle acquisition failed"):
        _assert_lock_surface_canonical_provenance(surface="synthetic", document=state["lock"])
    assert len(state["fetches"]) == 1 and not state["cache"]
    assert not state["archive_calls"] and not state["native_calls"]


def test_closed_bundle_default_raw_cache_retains_only_bounded_bytes(
    npm_bundle_reader_cache: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = npm_bundle_reader_cache
    monkeypatch.setattr(__name__ + "._NPM_BUNDLE_COMPRESSED_LIMIT", len(state["raw"]))
    parent = state["lock"]["packages"]["node_modules/fixture-parent"]
    second_url = "https://registry.npmjs.org/second-cache-fixture/-/second-cache-fixture-1.0.0.tgz"
    for url in (parent["resolved"], second_url):
        state["reader"](
            url=url,
            integrity=parent["integrity"],
            deadline=time.monotonic() + 5,
            raw_cache=state["cache"],
        )
    assert state["cache"] == {(second_url, parent["integrity"]): state["raw"]}
    assert len(state["fetches"]) == 2
