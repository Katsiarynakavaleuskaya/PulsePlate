"""Deterministic frontend dependency security guards.

RU: Проверяем frontend security overrides.
EN: Ensure frontend security overrides are pinned to safe npm releases.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"
FRONTEND_LOCK_JSON = REPO_ROOT / "frontend" / "package-lock.json"
NPM_REGISTRY_HOST = "registry.npmjs.org"
MIN_DOMPURIFY_VERSION = Version("3.4.11")
MIN_JS_YAML_VERSION = Version("4.2.0")
MIN_UNDICI_VERSION = Version("7.28.0")
MIN_WS_VERSION = Version("8.21.0")
BRACE_EXPANSION_BASE_OUTPUTS = {2: "2.0.3", 5: "5.0.6"}
BRACE_EXPANSION_APPROVED_OUTPUTS = {2: "2.1.3", 5: "5.0.8"}
BRACE_EXPANSION_VARIANT_FLOORS = {
    major: Version(output) for major, output in BRACE_EXPANSION_APPROVED_OUTPUTS.items()
}
BRACE_EXPANSION_OVERRIDE_CARRIERS = {
    2: "minimatch@3",
    5: "minimatch@10",
}
BRACE_EXPANSION_LOCK_PATHS = {
    2: "node_modules/brace-expansion",
    5: "node_modules/glob/node_modules/brace-expansion",
}
BRACE_EXPANSION_LOCK_SNAPSHOTS = {
    "base": {
        "node_modules/brace-expansion": {
            "version": "2.0.3",
            "resolved": ("https://registry.npmjs.org/brace-expansion/-/brace-expansion-2.0.3.tgz"),
            "integrity_sha256": "".join(
                (
                    "2e68800c",
                    "2b65f95b",
                    "f8986a21",
                    "f6105f93",
                    "3e13f44f",
                    "e6f53f4a",
                    "1793d034",
                    "1f800c4e",
                )
            ),
            "dev": True,
            "license": "MIT",
            "dependencies": {"balanced-match": "^1.0.0"},
        },
        "node_modules/glob/node_modules/brace-expansion": {
            "version": "5.0.6",
            "resolved": ("https://registry.npmjs.org/brace-expansion/-/brace-expansion-5.0.6.tgz"),
            "integrity_sha256": "".join(
                (
                    "277cbc9a",
                    "033d49c7",
                    "879edfc7",
                    "860ca172",
                    "aafbb8ae",
                    "e5aadedb",
                    "fb536939",
                    "16da3fc1",
                )
            ),
            "dev": True,
            "license": "MIT",
            "dependencies": {"balanced-match": "^4.0.2"},
            "engines": {"node": "18 || 20 || >=22"},
        },
    },
    "head": {
        "node_modules/brace-expansion": {
            "version": "2.1.3",
            "resolved": ("https://registry.npmjs.org/brace-expansion/-/brace-expansion-2.1.3.tgz"),
            "integrity_sha256": "".join(
                (
                    "19c80f96",
                    "f0698328",
                    "96b90980",
                    "368ddb6a",
                    "145a49a2",
                    "7bf589df",
                    "4d5dc451",
                    "1263acf2",
                )
            ),
            "dev": True,
            "license": "MIT",
            "dependencies": {"balanced-match": "^1.0.0"},
        },
        "node_modules/glob/node_modules/brace-expansion": {
            "version": "5.0.8",
            "resolved": ("https://registry.npmjs.org/brace-expansion/-/brace-expansion-5.0.8.tgz"),
            "integrity_sha256": "".join(
                (
                    "a8307831",
                    "bb57dfe2",
                    "e8c5f8b5",
                    "b5759460",
                    "6c648d7c",
                    "f84ec64c",
                    "3613e70f",
                    "d8a8584d",
                )
            ),
            "dev": True,
            "license": "MIT",
            "dependencies": {"balanced-match": "^4.0.2"},
            "engines": {"node": "20 || >=22"},
        },
    },
}
BRACE_EXPANSION_ADVISORY_RANGES = {
    "GHSA-3jxr-9vmj-r5cp": (
        SpecifierSet("<1.1.16"),
        SpecifierSet(">=2.0.0,<2.1.2"),
        SpecifierSet(">=3.0.0,<5.0.7"),
    ),
    "GHSA-832h-xg76-4gv6": (SpecifierSet("<1.1.7"),),
    "GHSA-f886-m6hf-6m8v": (
        SpecifierSet("<1.1.13"),
        SpecifierSet(">=2.0.0,<2.0.3"),
        SpecifierSet(">=3.0.0,<3.0.2"),
        SpecifierSet(">=4.0.0,<5.0.5"),
    ),
    "GHSA-jxxr-4gwj-5jf2": (SpecifierSet(">=5.0.0,<5.0.6"),),
    "GHSA-mh99-v99m-4gvg": (
        SpecifierSet("<1.1.17"),
        SpecifierSet(">=2.0.0,<2.1.3"),
        SpecifierSet(">=3.0.0,<3.0.3"),
        SpecifierSet(">=4.0.0,<5.0.8"),
    ),
    "GHSA-v6h2-p8h4-qcjw": (
        SpecifierSet(">=1.0.0,<=1.1.11"),
        SpecifierSet(">=2.0.0,<=2.0.1"),
        SpecifierSet("==3.0.0"),
        SpecifierSet("==4.0.0"),
    ),
}
BRACE_EXPANSION_CUTOFF_ADVISORIES = frozenset(
    {
        "GHSA-3jxr-9vmj-r5cp",
        "GHSA-832h-xg76-4gv6",
        "GHSA-f886-m6hf-6m8v",
        "GHSA-jxxr-4gwj-5jf2",
        "GHSA-mh99-v99m-4gvg",
        "GHSA-v6h2-p8h4-qcjw",
    }
)
BRACE_EXPANSION_APPLICABLE_ADVISORIES = frozenset({"GHSA-3jxr-9vmj-r5cp", "GHSA-mh99-v99m-4gvg"})
EXPECTED_REPO_NPM_SURFACES = frozenset(
    {
        "frontend/package-lock.json",
        "frontend/package.json",
        "package-lock.json",
        "package.json",
        "scripts/business_collateral/package.json",
    }
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


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_npm_registry_resolution(*, package_name: str, resolved: str) -> None:
    """Assert npm registry provenance for the unscoped package names guarded here."""
    assert isinstance(resolved, str) and resolved, f"{package_name} resolved URL missing"
    parsed = urlparse(resolved.removeprefix("git+"))
    assert parsed.scheme == "https", f"{package_name} lock resolution must use https"
    assert parsed.netloc == NPM_REGISTRY_HOST, f"{package_name} must resolve from npm registry"
    assert parsed.path.startswith(
        f"/{package_name}/"
    ), f"{package_name} lock resolution path mismatch"
    assert not resolved.startswith(
        "git+"
    ), f"{package_name} lock resolution must not use git override"


def _parse_version(*, value: object, source: str) -> Version:
    assert isinstance(value, str) and value, f"{source}: version missing"
    try:
        return Version(value)
    except InvalidVersion as exc:
        raise AssertionError(f"{source}: malformed version {value!r}") from exc


def _is_brace_expansion_lock_path(path: object) -> bool:
    if not isinstance(path, str):
        return False
    normalized = path.replace("\\", "/")
    return PurePosixPath(normalized).parts[-2:] == (
        "node_modules",
        "brace-expansion",
    )


def _has_brace_expansion_tarball_path_signal(value: object) -> bool:
    """Discover a candidate by package pathname before validating its origin."""

    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.path.startswith("/brace-expansion/-/brace-expansion-") and parsed.path.endswith(
        ".tgz"
    )


def _find_override_key_paths(
    node: object,
    *,
    target: str,
    path: tuple[str, ...] = (),
) -> dict[tuple[str, ...], object]:
    found: dict[tuple[str, ...], object] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            child_path = (*path, str(key))
            if key == target:
                found[child_path] = value
            found.update(_find_override_key_paths(value, target=target, path=child_path))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.update(_find_override_key_paths(value, target=target, path=(*path, f"[{index}]")))
    return found


def _discover_brace_expansion_lock_entries(packages: object) -> dict[str, dict]:
    """Enumerate the finite lockfile candidate universe independently of validity."""

    assert isinstance(packages, dict), "frontend/package-lock.json: packages must be an object"
    entries: dict[str, dict] = {}
    for raw_path, package in packages.items():
        canonical_path_signal = _is_brace_expansion_lock_path(raw_path)
        name_signal = isinstance(package, dict) and package.get("name") == "brace-expansion"
        url_signal = isinstance(package, dict) and _has_brace_expansion_tarball_path_signal(
            package.get("resolved")
        )
        if not (canonical_path_signal or name_signal or url_signal):
            continue
        assert isinstance(raw_path, str)
        assert (
            canonical_path_signal
        ), f"{raw_path}: brace-expansion alias/noncanonical installed path"
        path = PurePosixPath(raw_path)
        assert "\\" not in raw_path, f"{raw_path}: lock path must use POSIX separators"
        assert not path.is_absolute(), f"{raw_path}: lock path must be relative"
        assert ".." not in path.parts, f"{raw_path}: lock path must not contain traversal segments"
        assert path.as_posix() == raw_path, f"{raw_path}: lock path must be canonical"
        assert path.parts[-2:] == (
            "node_modules",
            "brace-expansion",
        ), f"{raw_path}: malformed brace-expansion lock path"
        assert isinstance(package, dict), f"{raw_path}: package entry must be an object"
        if "name" in package:
            assert (
                package["name"] == "brace-expansion"
            ), f"{raw_path}: package name conflicts with brace-expansion path"
        entries[raw_path] = package
    return entries


def _normalize_brace_expansion_lock_entries(entries: dict[str, dict]) -> dict[str, dict]:
    """Replace raw npm integrity material with its stable evidence digest."""

    normalized: dict[str, dict] = {}
    for path, package in entries.items():
        integrity = package.get("integrity")
        assert isinstance(integrity, str) and integrity.strip(), f"{path}: integrity missing"
        record = {key: value for key, value in package.items() if key != "integrity"}
        record["integrity_sha256"] = hashlib.sha256(integrity.encode("utf-8")).hexdigest()
        normalized[path] = record
    return normalized


def _version_is_affected(*, version: Version, advisory: str) -> bool:
    ranges = BRACE_EXPANSION_ADVISORY_RANGES[advisory]
    return any(version in affected_range for affected_range in ranges)


def _derive_applicable_advisories(versions: set[Version]) -> frozenset[str]:
    return frozenset(
        advisory
        for advisory in BRACE_EXPANSION_ADVISORY_RANGES
        if any(_version_is_affected(version=version, advisory=advisory) for version in versions)
    )


def _assert_brace_expansion_head_postcondition(versions: set[Version]) -> None:
    assert set(BRACE_EXPANSION_ADVISORY_RANGES) == BRACE_EXPANSION_CUTOFF_ADVISORIES
    for advisory in BRACE_EXPANSION_CUTOFF_ADVISORIES:
        assert all(
            not _version_is_affected(version=version, advisory=advisory) for version in versions
        ), f"{advisory}: governed head occurrence remains affected"


def _brace_expansion_manifest_snapshot(outputs: dict[int, str]) -> dict:
    return {
        "overrides": {
            BRACE_EXPANSION_OVERRIDE_CARRIERS[major]: {"brace-expansion": output}
            for major, output in outputs.items()
        }
    }


def _freeze_transition_value(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _lock_field_transitions(
    base_entries: dict[str, dict],
    head_entries: dict[str, dict],
) -> set[tuple[str, str, str, str]]:
    transitions: set[tuple[str, str, str, str]] = set()
    assert set(base_entries) == set(head_entries), "brace-expansion lock surface delta"
    for path in base_entries:
        base_entry = base_entries[path]
        head_entry = head_entries[path]
        for field in set(base_entry) | set(head_entry):
            base_value = base_entry.get(field)
            head_value = head_entry.get(field)
            if base_value != head_value:
                transitions.add(
                    (
                        path,
                        field,
                        _freeze_transition_value(base_value),
                        _freeze_transition_value(head_value),
                    )
                )
    return transitions


def _enumerate_repo_npm_surfaces() -> frozenset[str]:
    surfaces: set[str] = set()
    for path in REPO_ROOT.rglob("package*.json"):
        relative = path.relative_to(REPO_ROOT)
        if set(relative.parts) & IGNORED_NPM_SURFACE_PARTS:
            continue
        surfaces.add(relative.as_posix())
    return frozenset(surfaces)


def _assert_brace_expansion_security_class(
    *,
    package_json: dict,
    package_lock: dict,
) -> None:
    """Validate every 2.x/5.x output variant of one brace-expansion class."""

    overrides = package_json.get("overrides")
    assert isinstance(overrides, dict), "frontend/package.json: overrides must be an object"
    assert (
        "brace-expansion" not in overrides
    ), "frontend/package.json: blanket brace-expansion override is forbidden"

    expected_override_outputs = {
        (carrier, "brace-expansion"): BRACE_EXPANSION_APPROVED_OUTPUTS[major]
        for major, carrier in BRACE_EXPANSION_OVERRIDE_CARRIERS.items()
    }
    discovered_override_outputs = _find_override_key_paths(
        overrides,
        target="brace-expansion",
    )
    assert (
        discovered_override_outputs == expected_override_outputs
    ), "frontend/package.json: brace-expansion override target/output set is not approved"

    for major, carrier in BRACE_EXPANSION_OVERRIDE_CARRIERS.items():
        exact_output = discovered_override_outputs[(carrier, "brace-expansion")]
        parsed_output = _parse_version(
            value=exact_output,
            source=f"frontend/package.json: overrides.{carrier}.brace-expansion",
        )
        assert parsed_output.major == major, f"{carrier}: brace-expansion major mismatch"
        assert (
            parsed_output >= BRACE_EXPANSION_VARIANT_FLOORS[major]
        ), f"{carrier}: brace-expansion below secure floor"
        assert (
            exact_output == BRACE_EXPANSION_APPROVED_OUTPUTS[major]
        ), f"{carrier}: brace-expansion manifest output is not approved"

    packages = package_lock.get("packages")
    discovered_entries = _discover_brace_expansion_lock_entries(packages)
    entries: list[tuple[str, dict, Version]] = []
    for raw_path, package in discovered_entries.items():
        parsed_version = _parse_version(value=package.get("version"), source=raw_path)
        resolved = package.get("resolved")
        expected_resolved = (
            "https://registry.npmjs.org/brace-expansion/-/" f"brace-expansion-{parsed_version}.tgz"
        )
        assert resolved == expected_resolved, f"{raw_path}: brace-expansion provenance mismatch"
        integrity = package.get("integrity")
        assert isinstance(integrity, str) and integrity.strip(), f"{raw_path}: integrity missing"
        entries.append((raw_path, package, parsed_version))

    assert entries, "frontend/package-lock.json: brace-expansion package entries missing"
    found_majors = {version.major for _, _, version in entries}
    assert found_majors == set(
        BRACE_EXPANSION_VARIANT_FLOORS
    ), "frontend/package-lock.json: brace-expansion major set must be exactly {2, 5}"

    for path, package, parsed_version in entries:
        major = parsed_version.major
        assert (
            parsed_version >= BRACE_EXPANSION_VARIANT_FLOORS[major]
        ), f"{path}: brace-expansion below secure floor"
        raw_version = package["version"]
        assert (
            raw_version == BRACE_EXPANSION_APPROVED_OUTPUTS[major]
        ), f"{path}: brace-expansion lock output is not approved"


def _brace_entry(version: str) -> dict[str, str]:
    return {
        "version": version,
        "resolved": (
            "https://registry.npmjs.org/brace-expansion/-/" f"brace-expansion-{version}.tgz"
        ),
        "integrity": "sha512-fixture",
    }


def _brace_expansion_guard_fixture() -> tuple[dict, dict]:
    return (
        {
            "overrides": {
                "minimatch@3": {"brace-expansion": "2.1.3"},
                "minimatch@10": {"brace-expansion": "5.0.8"},
            }
        },
        {
            "packages": {
                "node_modules/brace-expansion": _brace_entry("2.1.3"),
                "node_modules/glob/node_modules/brace-expansion": _brace_entry("5.0.8"),
            }
        },
    )


def test_frontend_brace_expansion_class_covers_all_lock_variants() -> None:
    """All current 2.x/5.x carrier outputs share one invariant."""

    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    _assert_brace_expansion_security_class(
        package_json=package_json,
        package_lock=package_lock,
    )


def test_frontend_brace_expansion_class_reconciles_surfaces_and_transitions() -> None:
    """Derive A, partition I_R/C_R, and enforce P over all cutoff candidates."""

    base_package = _brace_expansion_manifest_snapshot(BRACE_EXPANSION_BASE_OUTPUTS)
    base_lock = {"packages": BRACE_EXPANSION_LOCK_SNAPSHOTS["base"]}
    head_package = _load_json(FRONTEND_PACKAGE_JSON)
    head_lock = _load_json(FRONTEND_LOCK_JSON)

    base_overrides = _find_override_key_paths(base_package["overrides"], target="brace-expansion")
    head_overrides = _find_override_key_paths(head_package["overrides"], target="brace-expansion")
    base_entries = _discover_brace_expansion_lock_entries(base_lock["packages"])
    raw_head_entries = _discover_brace_expansion_lock_entries(head_lock["packages"])
    head_entries = _normalize_brace_expansion_lock_entries(raw_head_entries)

    base_surfaces = {
        "frontend/package.json": base_overrides,
        "frontend/package-lock.json": base_entries,
    }
    head_surfaces = {
        "frontend/package.json": head_overrides,
        "frontend/package-lock.json": head_entries,
    }
    assert all(base_surfaces.values()) and all(head_surfaces.values())
    assert set(base_surfaces) == set(head_surfaces), "brace-expansion surface delta"

    expected_base_overrides = {
        (carrier, "brace-expansion"): BRACE_EXPANSION_BASE_OUTPUTS[major]
        for major, carrier in BRACE_EXPANSION_OVERRIDE_CARRIERS.items()
    }
    expected_head_overrides = {
        (carrier, "brace-expansion"): BRACE_EXPANSION_APPROVED_OUTPUTS[major]
        for major, carrier in BRACE_EXPANSION_OVERRIDE_CARRIERS.items()
    }
    assert base_overrides == expected_base_overrides
    assert head_overrides == expected_head_overrides
    assert base_entries == BRACE_EXPANSION_LOCK_SNAPSHOTS["base"]
    assert head_entries == BRACE_EXPANSION_LOCK_SNAPSHOTS["head"]

    base_versions = {
        _parse_version(value=entry["version"], source=path) for path, entry in base_entries.items()
    }
    head_versions = {
        _parse_version(value=entry["version"], source=path) for path, entry in head_entries.items()
    }
    applicable = _derive_applicable_advisories(base_versions)
    assert applicable == BRACE_EXPANSION_APPLICABLE_ADVISORIES
    non_applicable = set(BRACE_EXPANSION_ADVISORY_RANGES) - set(applicable)
    assert non_applicable
    for advisory in non_applicable:
        assert all(
            not _version_is_affected(version=version, advisory=advisory)
            for version in base_versions
        ), f"{advisory}: non-applicable-at-base disposition is false"
    _assert_brace_expansion_head_postcondition(head_versions)

    intent_transitions = {
        (path, base_overrides[path], head_overrides[path]) for path in base_overrides
    }
    expected_intent_transitions = {
        (
            (BRACE_EXPANSION_OVERRIDE_CARRIERS[major], "brace-expansion"),
            BRACE_EXPANSION_BASE_OUTPUTS[major],
            BRACE_EXPANSION_APPROVED_OUTPUTS[major],
        )
        for major in BRACE_EXPANSION_OVERRIDE_CARRIERS
    }
    assert intent_transitions == expected_intent_transitions
    assert all(base != head for _, base, head in intent_transitions)

    expected_solver_closure = _lock_field_transitions(
        BRACE_EXPANSION_LOCK_SNAPSHOTS["base"],
        BRACE_EXPANSION_LOCK_SNAPSHOTS["head"],
    )
    actual_solver_closure = _lock_field_transitions(base_entries, head_entries)
    assert actual_solver_closure == expected_solver_closure
    assert {(path, field) for path, field, _, _ in actual_solver_closure} == {
        (BRACE_EXPANSION_LOCK_PATHS[2], "version"),
        (BRACE_EXPANSION_LOCK_PATHS[2], "resolved"),
        (BRACE_EXPANSION_LOCK_PATHS[2], "integrity_sha256"),
        (BRACE_EXPANSION_LOCK_PATHS[5], "version"),
        (BRACE_EXPANSION_LOCK_PATHS[5], "resolved"),
        (BRACE_EXPANSION_LOCK_PATHS[5], "integrity_sha256"),
        (BRACE_EXPANSION_LOCK_PATHS[5], "engines"),
    }


def test_brace_expansion_is_absent_from_other_repo_npm_surfaces() -> None:
    """The frontend class must not silently absorb another repository npm graph."""

    surfaces = _enumerate_repo_npm_surfaces()
    assert surfaces == EXPECTED_REPO_NPM_SURFACES
    for relative in surfaces - {"frontend/package.json", "frontend/package-lock.json"}:
        document = _load_json(REPO_ROOT / relative)
        assert not _find_override_key_paths(
            document, target="brace-expansion"
        ), f"{relative}: brace-expansion belongs to a separate surface/class"


def test_brace_expansion_postcondition_includes_base_non_applicable_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A candidate outside A still blocks an affected governed head occurrence."""

    monkeypatch.setitem(
        BRACE_EXPANSION_ADVISORY_RANGES,
        "GHSA-f886-m6hf-6m8v",
        (SpecifierSet("==2.1.3"),),
    )
    with pytest.raises(AssertionError, match="GHSA-f886-m6hf-6m8v"):
        _assert_brace_expansion_head_postcondition({Version("2.1.3"), Version("5.0.8")})


@pytest.mark.parametrize(
    ("case", "message"),
    (
        ("below-floor", "below secure floor"),
        ("safe-nonexact", "lock output is not approved"),
        ("coordinated-safe-2", "override target/output set is not approved"),
        ("coordinated-safe-5", "override target/output set is not approved"),
        ("extra-override-carrier", "override target/output set is not approved"),
        ("missing-major", "major set must be exactly"),
        ("unexpected-major", "major set must be exactly"),
        ("schema", "packages must be an object"),
        ("path", "lock path must be relative"),
        ("traversal", "traversal segments"),
        ("name-alias", "alias/noncanonical installed path"),
        ("url-alias", "alias/noncanonical installed path"),
        ("query-alias", "alias/noncanonical installed path"),
        ("fragment-alias", "alias/noncanonical installed path"),
        ("params-alias", "alias/noncanonical installed path"),
        ("foreign-host-alias", "alias/noncanonical installed path"),
        ("http-alias", "alias/noncanonical installed path"),
        ("userinfo-alias", "alias/noncanonical installed path"),
        ("contradictory-name", "package name conflicts"),
        ("version", "malformed version"),
        ("provenance", "provenance mismatch"),
        ("integrity", "integrity missing"),
        ("manifest-lock", "override target/output set is not approved"),
        ("blanket", "blanket brace-expansion override is forbidden"),
    ),
)
def test_frontend_brace_expansion_class_fails_closed(case: str, message: str) -> None:
    """Falsify the class invariant rather than enumerating carrier names."""

    package_json, package_lock = _brace_expansion_guard_fixture()
    packages = package_lock["packages"]
    root = packages["node_modules/brace-expansion"]
    if case == "below-floor":
        packages["node_modules/future-carrier/node_modules/brace-expansion"] = _brace_entry("2.0.3")
    elif case == "safe-nonexact":
        root.update(_brace_entry("2.1.4"))
    elif case == "coordinated-safe-2":
        package_json["overrides"]["minimatch@3"]["brace-expansion"] = "2.1.4"
        root.update(_brace_entry("2.1.4"))
    elif case == "coordinated-safe-5":
        package_json["overrides"]["minimatch@10"]["brace-expansion"] = "5.0.9"
        packages["node_modules/glob/node_modules/brace-expansion"].update(_brace_entry("5.0.9"))
    elif case == "extra-override-carrier":
        package_json["overrides"]["future-carrier"] = {"nested": {"brace-expansion": "2.1.3"}}
    elif case == "missing-major":
        del packages["node_modules/glob/node_modules/brace-expansion"]
    elif case == "unexpected-major":
        packages["node_modules/other/node_modules/brace-expansion"] = _brace_entry("6.0.0")
    elif case == "schema":
        package_lock["packages"] = []
    elif case == "path":
        packages["/node_modules/brace-expansion"] = packages.pop("node_modules/brace-expansion")
    elif case == "traversal":
        packages["../node_modules/brace-expansion"] = packages.pop("node_modules/brace-expansion")
    elif case == "name-alias":
        packages["node_modules/brace-alias"] = {
            **_brace_entry("2.1.3"),
            "name": "brace-expansion",
            "resolved": "https://example.invalid/brace-expansion-2.1.3.tgz",
        }
    elif case == "url-alias":
        packages["node_modules/url-alias"] = _brace_entry("2.1.3")
    elif case in {
        "query-alias",
        "fragment-alias",
        "params-alias",
        "foreign-host-alias",
        "http-alias",
        "userinfo-alias",
    }:
        alias = _brace_entry("2.1.3")
        canonical = alias["resolved"]
        if case == "query-alias":
            alias["resolved"] = f"{canonical}?download=1"
        elif case == "fragment-alias":
            alias["resolved"] = f"{canonical}#fragment"
        elif case == "params-alias":
            alias["resolved"] = canonical.replace(".tgz", ".tgz;download")
        elif case == "foreign-host-alias":
            alias["resolved"] = canonical.replace(NPM_REGISTRY_HOST, "example.invalid")
        elif case == "http-alias":
            alias["resolved"] = canonical.replace("https://", "http://")
        else:
            alias["resolved"] = canonical.replace("https://", "https://user@")
        packages[f"node_modules/{case}"] = alias
    elif case == "contradictory-name":
        root["name"] = "not-brace-expansion"
    elif case == "version":
        root["version"] = "invalid"
    elif case == "provenance":
        root["resolved"] = "https://example.invalid/brace-expansion-2.1.3.tgz"
    elif case == "integrity":
        root["integrity"] = ""
    elif case == "manifest-lock":
        package_json["overrides"]["minimatch@3"]["brace-expansion"] = "2.1.4"
    elif case == "blanket":
        package_json["overrides"]["brace-expansion"] = "5.0.8"
    else:
        raise AssertionError(f"unhandled brace-expansion falsification case: {case}")

    with pytest.raises(AssertionError, match=message):
        _assert_brace_expansion_security_class(
            package_json=package_json,
            package_lock=package_lock,
        )


def test_frontend_package_has_dompurify_override_floor() -> None:
    """RU/EN: package.json override must keep dompurify at secure floor version."""
    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    overrides = package_json.get("overrides", {})
    dompurify_override = overrides.get("dompurify")
    assert isinstance(dompurify_override, str), "frontend/package.json: overrides.dompurify missing"
    assert Version(dompurify_override) >= MIN_DOMPURIFY_VERSION


def test_frontend_package_has_js_yaml_override_floor() -> None:
    """RU/EN: package.json override must keep js-yaml at secure floor version."""
    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    overrides = package_json.get("overrides", {})
    js_yaml_override = overrides.get("js-yaml")
    assert isinstance(js_yaml_override, str), "frontend/package.json: overrides.js-yaml missing"
    assert Version(js_yaml_override) >= MIN_JS_YAML_VERSION


def test_frontend_package_has_undici_override_floor() -> None:
    """RU/EN: package.json override must keep undici at secure floor version."""
    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    overrides = package_json.get("overrides", {})
    undici_override = overrides.get("undici")
    assert isinstance(undici_override, str), "frontend/package.json: overrides.undici missing"
    assert Version(undici_override) >= MIN_UNDICI_VERSION


def test_frontend_package_has_ws_override_floor() -> None:
    """RU/EN: package.json override must keep ws at secure floor version."""
    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    overrides = package_json.get("overrides", {})
    ws_override = overrides.get("ws")
    assert isinstance(ws_override, str), "frontend/package.json: overrides.ws missing"
    assert Version(ws_override) >= MIN_WS_VERSION


def test_frontend_lock_resolves_dompurify_to_safe_npm_release() -> None:
    """RU/EN: package-lock must resolve dompurify from npm registry."""
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    dompurify_pkg = package_lock.get("packages", {}).get("node_modules/dompurify", {})
    lock_version = dompurify_pkg.get("version")
    resolved = dompurify_pkg.get("resolved", "")

    assert isinstance(lock_version, str), "frontend/package-lock.json: dompurify version missing"
    assert Version(lock_version) >= MIN_DOMPURIFY_VERSION
    _assert_npm_registry_resolution(package_name="dompurify", resolved=resolved)


def test_frontend_lock_resolves_undici_to_safe_npm_release() -> None:
    """RU/EN: package-lock must resolve undici from npm registry."""
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    undici_pkg = package_lock.get("packages", {}).get("node_modules/undici", {})
    lock_version = undici_pkg.get("version")
    resolved = undici_pkg.get("resolved", "")

    assert isinstance(lock_version, str), "frontend/package-lock.json: undici version missing"
    assert Version(lock_version) >= MIN_UNDICI_VERSION
    _assert_npm_registry_resolution(package_name="undici", resolved=resolved)


def test_frontend_lock_resolves_ws_to_safe_npm_release() -> None:
    """RU/EN: package-lock must resolve ws from npm registry."""
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    ws_pkg = package_lock.get("packages", {}).get("node_modules/ws", {})
    lock_version = ws_pkg.get("version")
    resolved = ws_pkg.get("resolved", "")

    assert isinstance(lock_version, str), "frontend/package-lock.json: ws version missing"
    assert Version(lock_version) >= MIN_WS_VERSION
    _assert_npm_registry_resolution(package_name="ws", resolved=resolved)


def test_frontend_lock_resolves_all_js_yaml_entries_to_safe_npm_release() -> None:
    """RU/EN: every js-yaml package entry must use the secure npm release."""
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    packages = package_lock.get("packages", {})
    js_yaml_entries = {
        path: package
        for path, package in packages.items()
        if path == "node_modules/js-yaml" or path.endswith("/node_modules/js-yaml")
    }

    assert js_yaml_entries, "frontend/package-lock.json: js-yaml package entries missing"
    for path, package in js_yaml_entries.items():
        lock_version = package.get("version")
        resolved = package.get("resolved", "")
        assert isinstance(lock_version, str), f"{path}: js-yaml version missing"
        assert Version(lock_version) >= MIN_JS_YAML_VERSION, f"{path}: js-yaml below secure floor"
        _assert_npm_registry_resolution(package_name="js-yaml", resolved=resolved)
