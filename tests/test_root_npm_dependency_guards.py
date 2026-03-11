"""Deterministic root npm dependency security guards.

RU: Проверяем, что root package-lock.json держит hono на безопасной версии.
EN: Ensure the root package-lock.json keeps hono at a safe npm release.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_LOCK_JSON = REPO_ROOT / "package-lock.json"
MIN_HONO_VERSION = Version("4.12.7")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_root_lock_resolves_hono_to_safe_npm_release() -> None:
    """RU/EN: Root lockfile must resolve hono from npm registry at secure floor version."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    hono_pkg = package_lock.get("packages", {}).get("node_modules/hono", {})
    lock_version = hono_pkg.get("version")
    resolved = hono_pkg.get("resolved", "")

    assert isinstance(lock_version, str), "package-lock.json: hono version missing"
    assert Version(lock_version) >= MIN_HONO_VERSION
    assert isinstance(resolved, str) and resolved, "package-lock.json: hono resolved missing"

    parsed = urlparse(resolved)
    assert parsed.scheme == "https", "hono lock resolution must use https"
    assert parsed.netloc == "registry.npmjs.org", "hono must resolve from npm registry"
    assert parsed.path.startswith("/hono/"), "hono lock resolution path mismatch"


def test_root_lock_tracks_hono_as_mcp_sdk_transitive_dependency() -> None:
    """RU/EN: Dependency path should still show hono under @modelcontextprotocol/sdk."""
    package_lock = _load_json(ROOT_LOCK_JSON)
    mcp_sdk_pkg = package_lock.get("packages", {}).get("node_modules/@modelcontextprotocol/sdk", {})
    dependencies = mcp_sdk_pkg.get("dependencies", {})

    hono_range = dependencies.get("hono")
    assert isinstance(hono_range, str), "package-lock.json: MCP SDK hono dependency missing"
    assert hono_range.startswith("^4."), "package-lock.json: unexpected hono semver range"
