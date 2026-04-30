"""Contracts for iOS permission purpose strings and release capability truth."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IOS_APP_ROOT = REPO_ROOT / "ios/PulsePlate"
INFO_PLIST_LOCALES = ("en.lproj", "es.lproj", "ru.lproj")

PURPOSE_STRING_PATTERN = re.compile(r'"(?P<key>[^"]+)"\s*=\s*"(?P<value>(?:[^"\\]|\\.)*)";')

ALLOWED_RELEASE_PURPOSE_STRINGS = {"NSHealthShareUsageDescription"}

SENSITIVE_PURPOSE_STRINGS = {
    "NSCameraUsageDescription": ("AVFoundation", "AVCapture"),
    "NSLocationWhenInUseUsageDescription": ("CoreLocation", "CLLocation"),
    "NSPhotoLibraryUsageDescription": ("Photos", "PHPhoto", "PhotosPicker"),
    "NSMicrophoneUsageDescription": ("AVAudio", "SFSpeech", "NSSpeech"),
    "NSContactsUsageDescription": ("Contacts", "CNContact"),
    "NSFaceIDUsageDescription": ("LocalAuthentication", "LAContext"),
    "NSUserTrackingUsageDescription": ("AppTrackingTransparency", "ATTrackingManager"),
}


def _parse_strings(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for match in PURPOSE_STRING_PATTERN.finditer(path.read_text(encoding="utf-8")):
        entries[match.group("key")] = match.group("value")
    return entries


def _swift_source_text() -> str:
    swift_files = sorted(IOS_APP_ROOT.rglob("*.swift"))
    assert swift_files, "Expected iOS Swift sources for permission runtime checks"
    return "\n".join(path.read_text(encoding="utf-8") for path in swift_files)


def test_release_localizations_keep_only_supported_sensitive_purpose_strings() -> None:
    for locale in INFO_PLIST_LOCALES:
        strings_path = IOS_APP_ROOT / locale / "InfoPlist.strings"
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


def test_sensitive_purpose_strings_require_runtime_capability_evidence() -> None:
    swift_text = _swift_source_text()

    for locale in INFO_PLIST_LOCALES:
        entries = _parse_strings(IOS_APP_ROOT / locale / "InfoPlist.strings")
        for purpose_key, runtime_markers in SENSITIVE_PURPOSE_STRINGS.items():
            if purpose_key not in entries:
                continue

            assert any(marker in swift_text for marker in runtime_markers), (
                f"{purpose_key} is present in {locale} without matching runtime "
                f"capability evidence: {runtime_markers}"
            )


def test_tracking_purpose_string_is_forbidden_without_att_runtime() -> None:
    swift_text = _swift_source_text()
    has_att_runtime = "AppTrackingTransparency" in swift_text or "ATTrackingManager" in swift_text

    for locale in INFO_PLIST_LOCALES:
        entries = _parse_strings(IOS_APP_ROOT / locale / "InfoPlist.strings")
        assert "NSUserTrackingUsageDescription" not in entries or has_att_runtime, (
            f"NSUserTrackingUsageDescription in {locale} requires ATT runtime "
            "implementation and release review"
        )
