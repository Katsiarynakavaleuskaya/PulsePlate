"""Guard: Release Info.plist must contain explicit HTTPS BASE_URL.

Operator decision (PR-7): canonical_release_base_url = https://pulseplate.app

This guard prevents regression to the pre-PR-7 state where AppConfig.swift
silently fell back to a hardcoded ``https://api.pulseplate.com`` when
``BASE_URL`` was missing from ``Info-Release.plist``.
"""

from __future__ import annotations

import plistlib
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
INFO_RELEASE_PLIST = REPO_ROOT / "ios/PulsePlate/Info-Release.plist"
APP_CONFIG_SWIFT = REPO_ROOT / "ios/PulsePlate/Services/AppConfig.swift"

CANONICAL_HOST = "pulseplate.app"


def _load_release_plist() -> dict[str, object]:
    assert INFO_RELEASE_PLIST.exists(), f"Missing {INFO_RELEASE_PLIST}"
    with INFO_RELEASE_PLIST.open("rb") as fh:
        return plistlib.load(fh)


def test_release_plist_contains_explicit_base_url() -> None:
    """Info-Release.plist must have a BASE_URL key with a non-empty value."""
    plist = _load_release_plist()
    assert "BASE_URL" in plist, (
        "Info-Release.plist must contain an explicit BASE_URL key " "(not commented out)"
    )
    base_url = plist["BASE_URL"]
    assert (
        isinstance(base_url, str) and base_url.strip()
    ), "BASE_URL in Info-Release.plist must be a non-empty string"


def test_release_base_url_is_https() -> None:
    """Release BASE_URL must use HTTPS scheme (parsed, not string prefix)."""
    plist = _load_release_plist()
    base_url: str = plist.get("BASE_URL", "")  # type: ignore[assignment]
    parsed = urlparse(base_url)
    assert parsed.scheme == "https", (
        f"Release BASE_URL must have scheme 'https', got: '{parsed.scheme}' "
        f"(full URL: {base_url})"
    )
    assert parsed.netloc, f"Release BASE_URL must have a host component, got: {base_url}"


def test_release_base_url_is_canonical_host() -> None:
    """Release BASE_URL must point to the exact canonical host."""
    plist = _load_release_plist()
    base_url: str = plist.get("BASE_URL", "")  # type: ignore[assignment]
    parsed = urlparse(base_url)
    # Exact match or subdomain match (e.g. api.pulseplate.app)
    assert parsed.hostname is not None and (
        parsed.hostname == CANONICAL_HOST or parsed.hostname.endswith(f".{CANONICAL_HOST}")
    ), (
        f"Release BASE_URL must use canonical host {CANONICAL_HOST} "
        f"(or a subdomain), got hostname: '{parsed.hostname}' (full URL: {base_url})"
    )


def test_appconfig_has_no_silent_production_fallback() -> None:
    """AppConfig.swift must not silently fall back to a hardcoded production URL."""
    assert APP_CONFIG_SWIFT.exists(), f"Missing {APP_CONFIG_SWIFT}"
    source = APP_CONFIG_SWIFT.read_text(encoding="utf-8")
    assert "api.pulseplate.com" not in source, (
        "AppConfig.swift must not contain hardcoded fallback to api.pulseplate.com. "
        "Release builds must fail fast if BASE_URL is missing or invalid."
    )
