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

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

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


def _dependency_identity_matches(*, key: object, value: object, target: str) -> bool:
    if key == target:
        return True
    if not isinstance(value, str):
        return False
    return value == f"npm:{target}" or value.startswith(f"npm:{target}@")


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


def _resolved_registry_version(value: object, *, target: str) -> str | None:
    if not isinstance(value, str):
        return None
    prefix = f"https://registry.npmjs.org/{target}/-/{target}-"
    suffix = ".tgz"
    if not value.startswith(prefix) or not value.endswith(suffix):
        return None
    version = value[len(prefix) : -len(suffix)]
    return version or None


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
        resolved_matches = (
            _resolved_registry_version(raw_entry.get("resolved"), target=target) is not None
        )
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
        try:
            version = Version(raw_version)
        except InvalidVersion as exc:
            raise AssertionError(
                f"{surface}:{package_path}: version must be advisory-comparable"
            ) from exc
        assert (
            not version.is_prerelease
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
        basename = PurePosixPath(relative).name
        if basename == "package.json":
            assert not _find_manifest_occurrences(
                document, target="nanoid"
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
    """Every installed React Router remains outside both known affected ranges."""
    for relative, document in _load_tracked_npm_surfaces().items():
        basename = PurePosixPath(relative).name
        if basename == "package.json":
            assert not _find_manifest_occurrences(
                document, target="react-router"
            ), f"{relative}: react-router must remain transitive, not direct intent"
            continue
        assert basename in NPM_LOCK_SURFACE_BASENAMES
        _assert_occurrences_outside_ranges(
            surface=relative,
            target="react-router",
            occurrences=_find_lock_occurrences(document, target="react-router"),
            affected_ranges=REACT_ROUTER_AFFECTED_RANGES,
        )


@pytest.mark.parametrize(
    ("field", "key", "value", "target"),
    (
        ("dependencies", "image-size", "2.0.2", "image-size"),
        ("devDependencies", "renamed-image", "npm:image-size@2.0.2", "image-size"),
        ("optionalDependencies", "pptxgenjs", "4.0.1", "pptxgenjs"),
        ("peerDependencies", "renamed-pptx", "npm:pptxgenjs@4.0.1", "pptxgenjs"),
        ("overrides", "renamed-image", "npm:image-size", "image-size"),
        ("dependencies", "nanoid", "3.3.17", "nanoid"),
    ),
)
def test_retired_graph_manifest_discovery_rejects_direct_and_alias_reintroduction(
    field: str, key: str, value: str, target: str
) -> None:
    """Direct, override, and npm-alias declarations remain visible to the guard."""
    assert _find_manifest_occurrences({field: {key: value}}, target=target)


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
        ("nanoid", "3.3.16rc1", NANOID_AFFECTED_RANGES),
        ("nanoid", "5.1.15rc1", NANOID_AFFECTED_RANGES),
        ("react-router", "7.18.1rc1", REACT_ROUTER_AFFECTED_RANGES),
        ("react-router", "8.2.9rc1", REACT_ROUTER_AFFECTED_RANGES),
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
