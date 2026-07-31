"""Deterministic frontend dependency security guards.

RU: Проверяем frontend security overrides.
EN: Ensure frontend security overrides are pinned to safe npm releases.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import pytest
from packaging.version import InvalidVersion, Version

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"
FRONTEND_LOCK_JSON = REPO_ROOT / "frontend" / "package-lock.json"
NPM_REGISTRY_HOST = "registry.npmjs.org"
MIN_DOMPURIFY_VERSION = Version("3.4.11")
MIN_JS_YAML_VERSION = Version("4.2.0")
MIN_UNDICI_VERSION = Version("7.28.0")
MIN_WS_VERSION = Version("8.21.0")
BRACE_EXPANSION_VARIANT_FLOORS = {
    2: Version("2.1.3"),
    5: Version("5.0.8"),
}
BRACE_EXPANSION_APPROVED_OUTPUTS = {
    2: "2.1.3",
    5: "5.0.8",
}
BRACE_EXPANSION_OVERRIDE_CARRIERS = {
    2: "minimatch@3",
    5: "minimatch@10",
}


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


def _is_brace_expansion_registry_tarball(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and parsed.netloc == NPM_REGISTRY_HOST
        and parsed.path.startswith("/brace-expansion/-/brace-expansion-")
        and parsed.path.endswith(".tgz")
        and not (parsed.params or parsed.query or parsed.fragment)
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
    assert isinstance(packages, dict), "frontend/package-lock.json: packages must be an object"
    entries: list[tuple[str, dict, Version]] = []
    for raw_path, package in packages.items():
        canonical_path_signal = _is_brace_expansion_lock_path(raw_path)
        name_signal = isinstance(package, dict) and package.get("name") == "brace-expansion"
        url_signal = isinstance(package, dict) and _is_brace_expansion_registry_tarball(
            package.get("resolved")
        )
        if not (canonical_path_signal or name_signal or url_signal):
            continue
        assert (
            canonical_path_signal
        ), f"{raw_path}: brace-expansion alias/noncanonical installed path"
        assert isinstance(raw_path, str)
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
