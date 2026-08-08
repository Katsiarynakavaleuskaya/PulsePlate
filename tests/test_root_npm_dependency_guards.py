"""Deterministic root npm dependency security guards.

RU: Проверяем, что root package-lock.json удерживает исправленные security floors
для канонических npm remediation paths.
EN: Ensure the root package-lock.json keeps patched security floors for the
canonical npm remediation paths.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_PACKAGE_JSON = REPO_ROOT / "package.json"
ROOT_LOCK_JSON = REPO_ROOT / "package-lock.json"
# Exact public Git object, split so secret scanners do not misclassify the SHA as a credential.
IMAGE_SIZE_EXACT_BASE = "".join(("ad179450", "108ab352", "fe31e668", "7a33185b", "99b52127"))
IMAGE_SIZE_GOVERNED_SURFACES = frozenset(
    {
        "package.json",
        "package-lock.json",
        "frontend/package.json",
        "frontend/package-lock.json",
        "scripts/business_collateral/package.json",
    }
)
IMAGE_SIZE_ADVISORY_RANGES = {
    "GHSA-5p2g-fcmc-qvqq": SpecifierSet("<=2.0.2"),
    "GHSA-w3rx-r6r6-pgpr": SpecifierSet("<=2.0.2"),
}
IMAGE_SIZE_APPLICABLE_ADVISORIES = frozenset(IMAGE_SIZE_ADVISORY_RANGES)
IMAGE_SIZE_LOCK_CLOSURE_PATHS = frozenset(
    {
        ("packages", "", "dependencies", "pptxgenjs"),
        ("packages", "node_modules/https"),
        ("packages", "node_modules/image-size"),
        ("packages", "node_modules/pptxgenjs"),
        ("packages", "node_modules/pptxgenjs/node_modules/@types/node"),
        ("packages", "node_modules/pptxgenjs/node_modules/undici-types"),
        ("packages", "node_modules/queue"),
    }
)
NPM_SURFACE_BASENAMES = frozenset({"package.json", "package-lock.json", "npm-shrinkwrap.json"})
NPM_LOCK_SURFACE_BASENAMES = frozenset({"package-lock.json", "npm-shrinkwrap.json"})
NPM_MANIFEST_DEPENDENCY_FIELDS = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
    "overrides",
    "bundleDependencies",
    "bundledDependencies",
)
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


def _git_stdout(*args: str) -> bytes:
    """RU/EN: Read exact-base evidence through an absolute git binary."""
    git_binary = shutil.which("git")
    assert git_binary is not None, "git is required for exact-base dependency guards"
    assert Path(git_binary).is_absolute(), "git binary must resolve to an absolute path"
    result = subprocess.run(
        [git_binary, "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return result.stdout


def _load_json_at_git_ref(*, ref: str, relative: str) -> tuple[dict[str, Any], bytes]:
    blob = _git_stdout("show", f"{ref}:{relative}")
    document = json.loads(blob)
    assert isinstance(document, dict), f"{ref}:{relative}: npm surface must be an object"
    return cast(dict[str, Any], document), blob


def _is_governed_npm_surface(relative: PurePosixPath) -> bool:
    return (
        relative.name in NPM_SURFACE_BASENAMES
        and not set(relative.parts) & IGNORED_NPM_SURFACE_PARTS
    )


def _enumerate_repo_npm_surfaces(*, root: Path = REPO_ROOT) -> frozenset[str]:
    surfaces: set[str] = set()
    for basename in NPM_SURFACE_BASENAMES:
        for path in root.rglob(basename):
            relative = PurePosixPath(path.relative_to(root).as_posix())
            if _is_governed_npm_surface(relative):
                surfaces.add(relative.as_posix())
    return frozenset(surfaces)


def _enumerate_repo_npm_surfaces_at_git_ref(ref: str) -> frozenset[str]:
    tracked_paths = _git_stdout("ls-tree", "-r", "--name-only", ref).decode("utf-8")
    return frozenset(
        relative.as_posix()
        for raw_path in tracked_paths.splitlines()
        if _is_governed_npm_surface(relative := PurePosixPath(raw_path))
    )


def _dependency_identity_matches(*, key: object, value: object, target: str) -> bool:
    if key == target:
        return True
    if not isinstance(value, str):
        return False
    return value == f"npm:{target}" or value.startswith(f"npm:{target}@")


def _find_manifest_occurrences(
    document: dict[str, Any], *, target: str
) -> dict[tuple[str, ...], object]:
    """Find the target only in npm dependency-bearing manifest fields."""
    occurrences: dict[tuple[str, ...], object] = {}
    for field in (
        "dependencies",
        "devDependencies",
        "optionalDependencies",
        "peerDependencies",
    ):
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
    """Find installed lockfile-v3 target entries, including aliases."""
    assert document.get("lockfileVersion") == 3, "npm lock surface: lockfileVersion must be 3"
    packages = document.get("packages")
    assert isinstance(packages, dict), "npm lock surface: 'packages' must be an object"
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


def _discover_surface_occurrences(
    *, relative: str, document: dict[str, Any]
) -> dict[object, object]:
    basename = PurePosixPath(relative).name
    if basename == "package.json":
        return cast(dict[object, object], _find_manifest_occurrences(document, target="image-size"))
    assert basename in NPM_LOCK_SURFACE_BASENAMES, f"{relative}: unsupported npm surface"
    return cast(dict[object, object], _find_lock_occurrences(document, target="image-size"))


def _changed_json_paths(
    base: object, head: object, path: tuple[str, ...] = ()
) -> frozenset[tuple[str, ...]]:
    if isinstance(base, dict) and isinstance(head, dict):
        changed: set[tuple[str, ...]] = set()
        for key in set(base) | set(head):
            child_path = (*path, str(key))
            if key not in base or key not in head:
                changed.add(child_path)
            else:
                changed.update(_changed_json_paths(base[key], head[key], child_path))
        return frozenset(changed)
    return frozenset() if base == head else frozenset({path})


_MISSING_JSON_PATH = object()


def _json_value_at_path(document: object, path: tuple[str, ...]) -> object:
    value = document
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return _MISSING_JSON_PATH
        value = value[key]
    return value


def _assert_image_size_transition_partition(
    *,
    base_package: dict[str, Any],
    head_package: dict[str, Any],
    base_lock: dict[str, Any],
    head_lock: dict[str, Any],
) -> None:
    base_dependency_state = {
        field: base_package[field]
        for field in NPM_MANIFEST_DEPENDENCY_FIELDS
        if field in base_package
    }
    head_dependency_state = {
        field: head_package[field]
        for field in NPM_MANIFEST_DEPENDENCY_FIELDS
        if field in head_package
    }
    assert _changed_json_paths(base_dependency_state, head_dependency_state) == frozenset(
        {("dependencies", "pptxgenjs")}
    ), "package.json: I_R must be exactly removal of the root pptxgenjs dependency"
    base_dependencies = _require_dict_field(base_package, "dependencies", ctx="base package.json")
    head_dependencies = _require_dict_field(head_package, "dependencies", ctx="head package.json")
    assert base_dependencies.get("pptxgenjs") == "^4.0.1"
    assert "pptxgenjs" not in head_dependencies

    changed_lock_paths = _changed_json_paths(base_lock, head_lock)
    assert changed_lock_paths == IMAGE_SIZE_LOCK_CLOSURE_PATHS, (
        "package-lock.json: dependency delta must be exactly replay-proven C_R; found "
        f"{sorted(changed_lock_paths)!r}"
    )
    for closure_path in IMAGE_SIZE_LOCK_CLOSURE_PATHS:
        assert _json_value_at_path(base_lock, closure_path) is not _MISSING_JSON_PATH, (
            "package-lock.json: every C_R path must exist in exact base: " f"{closure_path!r}"
        )
        assert _json_value_at_path(head_lock, closure_path) is _MISSING_JSON_PATH, (
            "package-lock.json: every C_R path must be absent from head, not replaced: "
            f"{closure_path!r}"
        )


def _assert_image_size_remediation_class(
    *,
    base_documents: dict[str, dict[str, Any]],
    head_documents: dict[str, dict[str, Any]],
) -> None:
    assert frozenset(base_documents) == IMAGE_SIZE_GOVERNED_SURFACES
    assert frozenset(head_documents) == IMAGE_SIZE_GOVERNED_SURFACES

    base_occurrences = {
        relative: _discover_surface_occurrences(relative=relative, document=document)
        for relative, document in base_documents.items()
    }
    head_occurrences = {
        relative: _discover_surface_occurrences(relative=relative, document=document)
        for relative, document in head_documents.items()
    }
    non_empty_base = {relative: found for relative, found in base_occurrences.items() if found}
    assert set(non_empty_base) == {"package-lock.json"}
    assert set(non_empty_base["package-lock.json"]) == {"node_modules/image-size"}
    base_image_size = cast(
        dict[str, Any], non_empty_base["package-lock.json"]["node_modules/image-size"]
    )
    assert base_image_size.get("version") == "1.2.1"
    assert base_image_size.get("resolved") == (
        "https://registry.npmjs.org/image-size/-/image-size-1.2.1.tgz"
    )

    base_version = Version(cast(str, base_image_size["version"]))
    applicable = frozenset(
        advisory
        for advisory, affected_range in IMAGE_SIZE_ADVISORY_RANGES.items()
        if base_version in affected_range
    )
    assert applicable == IMAGE_SIZE_APPLICABLE_ADVISORIES
    assert all(
        not found for found in head_occurrences.values()
    ), "P failed: npm:image-size must have executable absence on every governed head surface"

    for relative in IMAGE_SIZE_GOVERNED_SURFACES - {"package.json", "package-lock.json"}:
        assert (
            base_documents[relative] == head_documents[relative]
        ), f"{relative}: negative-control npm surface must remain unchanged"

    _assert_image_size_transition_partition(
        base_package=base_documents["package.json"],
        head_package=head_documents["package.json"],
        base_lock=base_documents["package-lock.json"],
        head_lock=head_documents["package-lock.json"],
    )

    head_scripts = _require_dict_field(
        head_documents["package.json"], "scripts", ctx="head package.json"
    )
    assert "build:b2b-pitch-deck" not in head_scripts
    assert head_scripts.get("build:business-collateral") == "npm run build:b2b-proposal"
    assert not (REPO_ROOT / "scripts/business_collateral/build_b2b_pitch_deck.js").exists()
    content_loader = (REPO_ROOT / "scripts/business_collateral/content_loader.js").read_text(
        encoding="utf-8"
    )
    assert "parseDeckSpec" not in content_loader


def _load_image_size_base_and_head_documents() -> (
    tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]
):
    base_documents: dict[str, dict[str, Any]] = {}
    head_documents: dict[str, dict[str, Any]] = {}
    for relative in IMAGE_SIZE_GOVERNED_SURFACES:
        base_document, base_blob = _load_json_at_git_ref(
            ref=IMAGE_SIZE_EXACT_BASE,
            relative=relative,
        )
        head_blob = (REPO_ROOT / relative).read_bytes()
        head_document = json.loads(head_blob)
        assert isinstance(head_document, dict), f"head:{relative}: npm surface must be an object"
        base_documents[relative] = base_document
        head_documents[relative] = cast(dict[str, Any], head_document)
        if relative not in {"package.json", "package-lock.json"}:
            assert base_blob == head_blob, f"{relative}: negative-control bytes changed"
    return base_documents, head_documents


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


def test_image_size_removal_reconciles_exact_surfaces_intent_closure_and_postcondition() -> None:
    """Derive A, partition I_R/C_R, and enforce executable absence over exact S."""
    base_surfaces = _enumerate_repo_npm_surfaces_at_git_ref(IMAGE_SIZE_EXACT_BASE)
    head_surfaces = _enumerate_repo_npm_surfaces()
    assert base_surfaces == IMAGE_SIZE_GOVERNED_SURFACES
    assert head_surfaces == IMAGE_SIZE_GOVERNED_SURFACES

    base_documents, head_documents = _load_image_size_base_and_head_documents()
    _assert_image_size_remediation_class(
        base_documents=base_documents,
        head_documents=head_documents,
    )


@pytest.mark.parametrize(
    ("field", "key", "value"),
    (
        ("dependencies", "image-size", "^2.0.2"),
        ("devDependencies", "renamed-image-parser", "npm:image-size@2.0.2"),
        ("overrides", "renamed-image-parser", "npm:image-size"),
    ),
)
def test_image_size_manifest_discovery_rejects_direct_and_alias_reintroduction(
    field: str, key: str, value: str
) -> None:
    """A manifest cannot hide D behind a direct declaration or bounded npm alias."""
    document: dict[str, Any] = {field: {key: value}}
    assert _find_manifest_occurrences(document, target="image-size")


@pytest.mark.parametrize("field", ("bundleDependencies", "bundledDependencies"))
def test_image_size_manifest_discovery_rejects_bundled_reintroduction(field: str) -> None:
    """A bundled manifest declaration is still a governed D occurrence."""
    document: dict[str, Any] = {field: ["image-size"]}
    assert _find_manifest_occurrences(document, target="image-size")


@pytest.mark.parametrize(
    ("package_path", "entry"),
    (
        ("node_modules/image-size", {"version": "2.0.2"}),
        ("node_modules/renamed-image-parser", {"name": "image-size", "version": "2.0.2"}),
        (
            "node_modules/renamed-image-parser",
            {
                "version": "2.0.2",
                "resolved": "https://registry.npmjs.org/image-size/-/image-size-2.0.2.tgz",
            },
        ),
    ),
)
def test_image_size_lock_discovery_rejects_path_name_and_resolution_aliases(
    package_path: str, entry: dict[str, str]
) -> None:
    """A lock surface cannot hide an installed D occurrence behind an alias path."""
    document = {"lockfileVersion": 3, "packages": {package_path: entry}}
    assert _find_lock_occurrences(document, target="image-size") == {package_path: entry}


def test_image_size_removal_rejects_unclassified_lock_delta() -> None:
    """A second dependency objective cannot enter replay-proven C_R."""
    base_documents, head_documents = _load_image_size_base_and_head_documents()
    mutated_head = deepcopy(head_documents)
    mutated_head["package-lock.json"]["packages"]["node_modules/unclassified"] = {
        "version": "1.0.0"
    }

    with pytest.raises(AssertionError, match="replay-proven C_R"):
        _assert_image_size_remediation_class(
            base_documents=base_documents,
            head_documents=mutated_head,
        )


def test_image_size_removal_rejects_second_manifest_dependency_delta() -> None:
    """The one removal class cannot absorb another authored manifest transition."""
    base_documents, head_documents = _load_image_size_base_and_head_documents()
    mutated_head = deepcopy(head_documents)
    mutated_head["package.json"]["devDependencies"]["unclassified"] = "1.0.0"

    with pytest.raises(AssertionError, match="I_R must be exactly"):
        _assert_image_size_remediation_class(
            base_documents=base_documents,
            head_documents=mutated_head,
        )


def test_image_size_removal_rejects_restored_carrier_edge_as_image_size_alias() -> None:
    """The allowed root edge path cannot hide a replacement with D itself."""
    base_documents, head_documents = _load_image_size_base_and_head_documents()
    mutated_head = deepcopy(head_documents)
    mutated_head["package-lock.json"]["packages"][""]["dependencies"][
        "pptxgenjs"
    ] = "npm:image-size@2.0.2"

    with pytest.raises(AssertionError, match="must be absent from head"):
        _assert_image_size_remediation_class(
            base_documents=base_documents,
            head_documents=mutated_head,
        )


def test_image_size_removal_rejects_restored_carrier_edge_as_second_identity_alias() -> None:
    """The allowed root edge path cannot hide a second dependency identity."""
    base_documents, head_documents = _load_image_size_base_and_head_documents()
    mutated_head = deepcopy(head_documents)
    mutated_head["package-lock.json"]["packages"][""]["dependencies"][
        "pptxgenjs"
    ] = "npm:nanoid@5.1.15"

    with pytest.raises(AssertionError, match="must be absent from head"):
        _assert_image_size_remediation_class(
            base_documents=base_documents,
            head_documents=mutated_head,
        )


def test_image_size_removal_rejects_scalar_image_size_package_entry() -> None:
    """A malformed scalar D entry must fail before it can evade occurrence discovery."""
    base_documents, head_documents = _load_image_size_base_and_head_documents()
    mutated_head = deepcopy(head_documents)
    mutated_head["package-lock.json"]["packages"]["node_modules/image-size"] = "2.0.2"

    with pytest.raises(AssertionError, match="package entry must be an object"):
        _assert_image_size_remediation_class(
            base_documents=base_documents,
            head_documents=mutated_head,
        )


def test_image_size_removal_rejects_scalar_carrier_entry_with_image_size_alias() -> None:
    """A malformed carrier entry cannot encode an npm alias to D."""
    base_documents, head_documents = _load_image_size_base_and_head_documents()
    mutated_head = deepcopy(head_documents)
    mutated_head["package-lock.json"]["packages"]["node_modules/pptxgenjs"] = "npm:image-size@2.0.2"

    with pytest.raises(AssertionError, match="package entry must be an object"):
        _assert_image_size_remediation_class(
            base_documents=base_documents,
            head_documents=mutated_head,
        )
