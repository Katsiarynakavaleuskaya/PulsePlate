"""Contracts for the iOS required-reason privacy manifest."""

from __future__ import annotations

import plistlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVACY_MANIFEST = REPO_ROOT / "ios/PulsePlate/PrivacyInfo.xcprivacy"
XCODE_PROJECT = REPO_ROOT / "ios/PulsePlate.xcodeproj/project.pbxproj"


def _read_manifest() -> dict[str, object]:
    with PRIVACY_MANIFEST.open("rb") as manifest_file:
        return plistlib.load(manifest_file)


def test_privacy_manifest_exists_and_disables_tracking() -> None:
    assert PRIVACY_MANIFEST.is_file()

    manifest = _read_manifest()

    assert manifest["NSPrivacyTracking"] is False


def test_privacy_manifest_declares_user_defaults_required_reason() -> None:
    manifest = _read_manifest()
    accessed_api_types = manifest["NSPrivacyAccessedAPITypes"]
    expected_user_defaults_entry = {
        "NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryUserDefaults",
        "NSPrivacyAccessedAPITypeReasons": ["CA92.1"],
    }

    assert isinstance(accessed_api_types, list)
    assert expected_user_defaults_entry in accessed_api_types


def test_privacy_manifest_is_not_excluded_from_pulseplate_target() -> None:
    project = XCODE_PROJECT.read_text(encoding="utf-8")
    membership_exception_blocks = re.findall(
        r"membershipExceptions = \((.*?)\);",
        project,
        flags=re.DOTALL,
    )

    assert "path = PulsePlate;" in project
    assert "PBXFileSystemSynchronizedRootGroup" in project
    assert membership_exception_blocks
    assert all("PrivacyInfo.xcprivacy" not in block for block in membership_exception_blocks)
