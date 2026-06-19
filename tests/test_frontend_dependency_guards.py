"""Deterministic frontend dependency security guards.

RU: Проверяем frontend security overrides.
EN: Ensure frontend security overrides are pinned to safe npm releases.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"
FRONTEND_LOCK_JSON = REPO_ROOT / "frontend" / "package-lock.json"
NPM_REGISTRY_HOST = "registry.npmjs.org"
MIN_DOMPURIFY_VERSION = Version("3.4.11")
MIN_JS_YAML_VERSION = Version("4.2.0")
MIN_UNDICI_VERSION = Version("7.28.0")
MIN_WS_VERSION = Version("8.21.0")


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
