"""Contracts for iOS permission purpose strings and release capability truth."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IOS_APP_ROOT = REPO_ROOT / "ios/PulsePlate"
IOS_PROJECT_FILE = REPO_ROOT / "ios/PulsePlate.xcodeproj/project.pbxproj"

PURPOSE_STRING_PATTERN = re.compile(r'"(?P<key>[^"]+)"\s*=\s*"(?P<value>(?:[^"\\]|\\.)*)";')
INFOPLIST_BUILD_SETTING_PATTERN = re.compile(
    r"INFOPLIST_KEY_(?P<key>NS[A-Za-z0-9]+UsageDescription)\s*="
)

ALLOWED_RELEASE_PURPOSE_STRINGS = {"NSHealthShareUsageDescription"}

SENSITIVE_PURPOSE_STRINGS = {
    "NSHealthShareUsageDescription": ("HealthKit", "HKHealthStore"),
    "NSCameraUsageDescription": ("AVFoundation", "AVCapture"),
    "NSLocationWhenInUseUsageDescription": ("CoreLocation", "CLLocation"),
    "NSPhotoLibraryUsageDescription": ("Photos", "PHPhoto", "PhotosPicker"),
    "NSMicrophoneUsageDescription": ("AVAudio", "SFSpeech", "NSSpeech"),
    "NSContactsUsageDescription": ("Contacts", "CNContact"),
    "NSFaceIDUsageDescription": ("LocalAuthentication", "LAContext"),
    "NSUserTrackingUsageDescription": ("AppTrackingTransparency", "ATTrackingManager"),
}


def _info_plist_strings_paths() -> tuple[Path, ...]:
    paths = tuple(sorted(IOS_APP_ROOT.glob("*.lproj/InfoPlist.strings")))
    assert paths, "Expected localized InfoPlist.strings under ios/PulsePlate/*.lproj"
    return paths


def _parse_strings(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for match in PURPOSE_STRING_PATTERN.finditer(path.read_text(encoding="utf-8")):
        entries[match.group("key")] = match.group("value")
    return entries


def _project_build_setting_purpose_keys() -> set[str]:
    text = IOS_PROJECT_FILE.read_text(encoding="utf-8")
    return {match.group("key") for match in INFOPLIST_BUILD_SETTING_PATTERN.finditer(text)}


def _swift_source_text() -> str:
    swift_files = sorted(IOS_APP_ROOT.rglob("*.swift"))
    assert swift_files, "Expected iOS Swift sources for permission runtime checks"
    return "\n".join(path.read_text(encoding="utf-8") for path in swift_files)


def test_release_localizations_keep_only_supported_sensitive_purpose_strings() -> None:
    for strings_path in _info_plist_strings_paths():
        entries = _parse_strings(strings_path)
        sensitive_keys = {
            key for key in entries if key.startswith("NS") and key.endswith("UsageDescription")
        }

        assert sensitive_keys == ALLOWED_RELEASE_PURPOSE_STRINGS, (
            f"{strings_path} must only declare release-backed sensitive purpose "
            f"strings: {sorted(sensitive_keys)}"
        )
        assert entries[
            "NSHealthShareUsageDescription"
        ].strip(), f"{strings_path} must keep HealthKit read-only consent copy"


def test_built_info_plist_settings_keep_only_supported_sensitive_purpose_strings() -> None:
    sensitive_keys = _project_build_setting_purpose_keys()

    assert sensitive_keys == ALLOWED_RELEASE_PURPOSE_STRINGS, (
        f"{IOS_PROJECT_FILE} must only inject release-backed sensitive purpose "
        f"strings into the built Info.plist: {sorted(sensitive_keys)}"
    )


def test_sensitive_purpose_strings_require_runtime_capability_evidence() -> None:
    swift_text = _swift_source_text()

    for strings_path in _info_plist_strings_paths():
        entries = _parse_strings(strings_path)
        for purpose_key, runtime_markers in SENSITIVE_PURPOSE_STRINGS.items():
            if purpose_key not in entries:
                continue

            assert any(marker in swift_text for marker in runtime_markers), (
                f"{purpose_key} is present in {strings_path.parent.name} without "
                f"matching runtime capability evidence: {runtime_markers}"
            )

    for purpose_key in _project_build_setting_purpose_keys():
        runtime_markers = SENSITIVE_PURPOSE_STRINGS.get(purpose_key)
        assert runtime_markers is not None, (
            f"{purpose_key} is injected by {IOS_PROJECT_FILE} without a permission "
            "runtime evidence contract"
        )
        assert any(marker in swift_text for marker in runtime_markers), (
            f"{purpose_key} is injected by {IOS_PROJECT_FILE} without matching "
            f"runtime capability evidence: {runtime_markers}"
        )


def test_tracking_purpose_string_is_forbidden_without_att_runtime() -> None:
    swift_text = _swift_source_text()
    has_att_runtime = "AppTrackingTransparency" in swift_text or "ATTrackingManager" in swift_text

    for strings_path in _info_plist_strings_paths():
        entries = _parse_strings(strings_path)
        assert "NSUserTrackingUsageDescription" not in entries or has_att_runtime, (
            f"NSUserTrackingUsageDescription in {strings_path.parent.name} requires "
            "ATT runtime implementation and release review"
        )

    project_keys = _project_build_setting_purpose_keys()
    assert "NSUserTrackingUsageDescription" not in project_keys or has_att_runtime, (
        f"NSUserTrackingUsageDescription in {IOS_PROJECT_FILE} requires ATT runtime "
        "implementation and release review"
    )
