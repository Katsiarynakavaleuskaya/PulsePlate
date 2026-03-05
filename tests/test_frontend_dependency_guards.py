"""Deterministic frontend dependency security guards.

RU: Проверяем, что dompurify закреплен на безопасной версии без git-override.
EN: Ensure dompurify is pinned to a safe npm release without git overrides.
"""

from __future__ import annotations

import json
from pathlib import Path

from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"
FRONTEND_LOCK_JSON = REPO_ROOT / "frontend" / "package-lock.json"
MIN_DOMPURIFY_VERSION = Version("3.3.2")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_frontend_package_has_dompurify_override_floor() -> None:
    """RU/EN: package.json override must keep dompurify at secure floor version."""
    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    overrides = package_json.get("overrides", {})
    dompurify_override = overrides.get("dompurify")
    assert isinstance(dompurify_override, str), "frontend/package.json: overrides.dompurify missing"
    assert Version(dompurify_override) >= MIN_DOMPURIFY_VERSION


def test_frontend_lock_resolves_dompurify_to_safe_npm_release() -> None:
    """RU/EN: package-lock must resolve dompurify from npm registry at secure floor version."""
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    dompurify_pkg = package_lock.get("packages", {}).get("node_modules/dompurify", {})
    lock_version = dompurify_pkg.get("version")
    resolved = dompurify_pkg.get("resolved", "")

    assert isinstance(lock_version, str), "frontend/package-lock.json: dompurify version missing"
    assert Version(lock_version) >= MIN_DOMPURIFY_VERSION
    assert isinstance(resolved, str) and "registry.npmjs.org/dompurify" in resolved
    assert not resolved.startswith("git+"), "dompurify lock resolution must not use git override"
