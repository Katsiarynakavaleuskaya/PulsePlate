"""Deterministic App Store submission readiness validator.

Checks repo-local evidence for iOS App Store release truth without
network calls, App Store Connect credentials, or protected secrets.

Exit 0 = all checks pass.
Exit 1 = at least one check failed.

Usage:
    python3 scripts/release/check_ios_appstore_verify.py
"""

from __future__ import annotations

import json
import pathlib
import plistlib
import re
import struct
import sys
from typing import List, Tuple

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# --- Paths ---

INFO_RELEASE_PLIST = REPO_ROOT / "ios" / "PulsePlate" / "Info-Release.plist"
APPCONFIG_SWIFT = REPO_ROOT / "ios" / "PulsePlate" / "Services" / "AppConfig.swift"
APPICON_CONTENTS = (
    REPO_ROOT / "ios" / "PulsePlate" / "Assets.xcassets" / "AppIcon.appiconset" / "Contents.json"
)
PRIVACY_MANIFEST = REPO_ROOT / "ios" / "PulsePlate" / "PrivacyInfo.xcprivacy"
APP_PRIVACY_JSON = REPO_ROOT / "ios" / "fastlane" / "app_privacy_details.json"
HEALTHKIT_MANAGER = REPO_ROOT / "ios" / "PulsePlate" / "Models" / "HealthKitManager.swift"
CONSENT_STORE = REPO_ROOT / "ios" / "PulsePlate" / "Services" / "AIWellnessConsentStore.swift"
DISCLOSURE_SHEET = REPO_ROOT / "ios" / "PulsePlate" / "Views" / "AIWellnessDisclosureSheet.swift"
REVIEWER_NOTES = REPO_ROOT / "ios" / "fastlane" / "metadata" / "review_information" / "notes.txt"
SCREENSHOT_GATE = REPO_ROOT / "docs" / "release" / "APPSTORE_SCREENSHOT_ASSET_GATE.md"

LOCALES = ("en-US", "es-ES", "ru-RU")
METADATA_DIR = REPO_ROOT / "ios" / "fastlane" / "metadata"
LPROJ_DIR = REPO_ROOT / "ios" / "PulsePlate"

CANONICAL_BASE_URL = "https://pulseplate.app"
FORBIDDEN_HOSTS = ("api.pulseplate.com", "api.pulseplate.app")
EXPECTED_PRIVACY_CATEGORIES = {"HEALTH", "PURCHASE_HISTORY", "OTHER_USER_CONTENT"}

# Pricing patterns that should NOT appear in metadata (hardcoded prices/trials).
PRICING_PATTERNS = [
    re.compile(r"\$\d"),
    re.compile(r"\d+\s*USD", re.IGNORECASE),
    re.compile(r"\d+\s*EUR", re.IGNORECASE),
    re.compile(r"\d+\s*RUB", re.IGNORECASE),
    re.compile(r"\d+[\s-]*day\s+(?:free\s+)?trial", re.IGNORECASE),
    re.compile(r"\d+[\s-]*month\s+(?:free\s+)?trial", re.IGNORECASE),
    re.compile(r"(?:free|бесплатн)\s+(?:for|на)\s+\d+", re.IGNORECASE),
    re.compile(r"(?:7|14|30)[\s-]*day\s+trial", re.IGNORECASE),
]

# --- Helpers ---

Results = List[Tuple[bool, str, str]]


def _read_png_dimensions(path: pathlib.Path) -> Tuple[int, int]:
    """Read width/height from PNG IHDR chunk (no external deps)."""
    with open(path, "rb") as fh:
        sig = fh.read(8)
        if sig[:4] != b"\x89PNG":
            raise ValueError(f"Not a PNG file: {path}")
        # IHDR is always first chunk after signature.
        fh.read(4)  # chunk length (not needed for IHDR)
        chunk_type = fh.read(4)
        if chunk_type != b"IHDR":
            raise ValueError(f"Missing IHDR chunk: {path}")
        data = fh.read(8)
        width, height = struct.unpack(">II", data)
    return width, height


# --- Check functions ---


def check_release_base_url() -> Results:
    """Verify Info-Release.plist contains canonical HTTPS BASE_URL."""
    results: Results = []
    tag = "release_base_url"

    if not INFO_RELEASE_PLIST.exists():
        results.append((False, tag, f"File missing: {INFO_RELEASE_PLIST}"))
        return results

    with open(INFO_RELEASE_PLIST, "rb") as fh:
        plist = plistlib.load(fh)

    base_url = plist.get("BASE_URL", "")
    if not base_url:
        results.append((False, tag, "BASE_URL key missing or empty in Info-Release.plist"))
        return results

    if not base_url.startswith("https://"):
        results.append((False, tag, f"BASE_URL is not HTTPS: {base_url}"))
        return results

    if base_url.rstrip("/") != CANONICAL_BASE_URL:
        results.append(
            (False, tag, f"BASE_URL is not canonical: {base_url} (expected {CANONICAL_BASE_URL})")
        )
        return results

    for host in FORBIDDEN_HOSTS:
        if host in base_url:
            results.append((False, tag, f"BASE_URL contains forbidden host {host}: {base_url}"))
            return results

    # Check AppConfig.swift for silent production fallback.
    if APPCONFIG_SWIFT.exists():
        content = APPCONFIG_SWIFT.read_text(encoding="utf-8")
        for host in FORBIDDEN_HOSTS:
            if host in content:
                results.append(
                    (False, tag, f"AppConfig.swift contains forbidden fallback host: {host}")
                )
                return results

    results.append((True, tag, f"BASE_URL = {base_url}"))
    return results


def check_appicon_marketing() -> Results:
    """Verify AppIcon has exactly one ios-marketing entry at 1024x1024."""
    results: Results = []
    tag = "appicon_marketing"

    if not APPICON_CONTENTS.exists():
        results.append((False, tag, f"File missing: {APPICON_CONTENTS}"))
        return results

    data = json.loads(APPICON_CONTENTS.read_text(encoding="utf-8"))
    images = data.get("images", [])
    marketing = [img for img in images if img.get("idiom") == "ios-marketing"]

    if len(marketing) != 1:
        results.append(
            (False, tag, f"Expected exactly 1 ios-marketing entry, found {len(marketing)}")
        )
        return results

    entry = marketing[0]
    if entry.get("size") != "1024x1024":
        results.append(
            (False, tag, f"ios-marketing size is {entry.get('size')}, expected 1024x1024")
        )
        return results

    filename = entry.get("filename", "")
    if not filename:
        results.append((False, tag, "ios-marketing entry has no filename"))
        return results

    png_path = APPICON_CONTENTS.parent / filename
    if not png_path.exists():
        results.append((False, tag, f"ios-marketing PNG missing: {png_path}"))
        return results

    try:
        w, h = _read_png_dimensions(png_path)
    except (ValueError, struct.error) as exc:
        results.append((False, tag, f"Cannot read PNG dimensions: {exc}"))
        return results

    if (w, h) != (1024, 1024):
        results.append((False, tag, f"PNG dimensions {w}x{h}, expected 1024x1024"))
        return results

    results.append((True, tag, f"AppIcon ios-marketing 1024x1024 OK ({filename})"))
    return results


def check_privacy_manifest() -> Results:
    """Verify PrivacyInfo.xcprivacy exists and has valid structure."""
    results: Results = []
    tag = "privacy_manifest"

    if not PRIVACY_MANIFEST.exists():
        results.append((False, tag, f"File missing: {PRIVACY_MANIFEST}"))
        return results

    with open(PRIVACY_MANIFEST, "rb") as fh:
        try:
            plist = plistlib.load(fh)
        except Exception as exc:
            results.append((False, tag, f"Cannot parse PrivacyInfo.xcprivacy: {exc}"))
            return results

    tracking = plist.get("NSPrivacyTracking")
    if tracking is not False:
        results.append((False, tag, f"NSPrivacyTracking is {tracking!r}, expected False"))
        return results

    api_types = plist.get("NSPrivacyAccessedAPITypes")
    if not api_types:
        results.append((False, tag, "NSPrivacyAccessedAPITypes missing or empty"))
        return results

    results.append((True, tag, "PrivacyInfo.xcprivacy valid (tracking=False, API types declared)"))
    return results


def check_app_privacy_details() -> Results:
    """Verify app_privacy_details.json is valid and covers expected categories."""
    results: Results = []
    tag = "app_privacy_details"

    if not APP_PRIVACY_JSON.exists():
        results.append((False, tag, f"File missing: {APP_PRIVACY_JSON}"))
        return results

    try:
        data = json.loads(APP_PRIVACY_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        results.append((False, tag, f"Invalid JSON: {exc}"))
        return results

    if not isinstance(data, list) or len(data) == 0:
        results.append((False, tag, "app_privacy_details.json is empty or not an array"))
        return results

    categories = {entry.get("category") for entry in data if isinstance(entry, dict)}

    # Must not claim DATA_NOT_COLLECTED.
    for entry in data:
        if isinstance(entry, dict):
            protections = entry.get("data_protections", [])
            if "DATA_NOT_COLLECTED" in protections:
                results.append(
                    (
                        False,
                        tag,
                        f"DATA_NOT_COLLECTED found for category {entry.get('category')}",
                    )
                )
                return results

    missing = EXPECTED_PRIVACY_CATEGORIES - categories
    if missing:
        results.append((False, tag, f"Missing expected privacy categories: {sorted(missing)}"))
        return results

    results.append((True, tag, f"App Privacy details valid ({len(data)} categories declared)"))
    return results


def check_permission_strings() -> Results:
    """Verify only allowed sensitive permission strings are present."""
    results: Results = []
    tag = "permission_strings"

    forbidden_key = "NSHealthUpdateUsageDescription"
    allowed_key = "NSHealthShareUsageDescription"

    for locale in ("en", "ru", "es"):
        strings_file = LPROJ_DIR / f"{locale}.lproj" / "InfoPlist.strings"
        if not strings_file.exists():
            continue
        content = strings_file.read_text(encoding="utf-8", errors="replace")
        if forbidden_key in content:
            results.append(
                (
                    False,
                    tag,
                    f"Forbidden {forbidden_key} found in {locale}.lproj/InfoPlist.strings",
                )
            )
            return results

    # Verify allowed key exists in at least en locale.
    en_strings = LPROJ_DIR / "en.lproj" / "InfoPlist.strings"
    if en_strings.exists():
        content = en_strings.read_text(encoding="utf-8", errors="replace")
        if allowed_key not in content:
            results.append(
                (
                    False,
                    tag,
                    f"{allowed_key} missing from en.lproj/InfoPlist.strings",
                )
            )
            return results

    results.append((True, tag, "Permission strings OK (read-only HealthKit, no write)"))
    return results


def check_healthkit_readonly() -> Results:
    """Verify HealthKit is read-only (no write operations)."""
    results: Results = []
    tag = "healthkit_readonly"

    if not HEALTHKIT_MANAGER.exists():
        results.append((False, tag, f"File missing: {HEALTHKIT_MANAGER}"))
        return results

    content = HEALTHKIT_MANAGER.read_text(encoding="utf-8")

    if "toShare: nil" not in content and "toShare:nil" not in content:
        results.append((False, tag, "HealthKitManager does not declare toShare: nil"))
        return results

    write_patterns = [".save(", "deleteObjects", "deleteObject", ".delete("]
    for pat in write_patterns:
        if pat in content:
            results.append((False, tag, f"HealthKit write operation found: {pat}"))
            return results

    results.append((True, tag, "HealthKit is read-only (toShare: nil, no write ops)"))
    return results


def check_ai_wellness_consent() -> Results:
    """Verify AI wellness consent gate exists and reviewer notes mention it."""
    results: Results = []
    tag = "ai_wellness_consent"

    if not CONSENT_STORE.exists():
        results.append((False, tag, f"File missing: {CONSENT_STORE}"))
        return results

    if not DISCLOSURE_SHEET.exists():
        results.append((False, tag, f"File missing: {DISCLOSURE_SHEET}"))
        return results

    # Reviewer notes should mention AI consent.
    if REVIEWER_NOTES.exists():
        notes = REVIEWER_NOTES.read_text(encoding="utf-8").lower()
        # Check for mentions of the AI consent or wellness disclosure topic.
        consent_keywords = ["ai", "consent", "wellness", "diagnos", "treat", "medical"]
        found = sum(1 for kw in consent_keywords if kw in notes)
        if found < 2:
            results.append(
                (
                    False,
                    tag,
                    "Reviewer notes do not sufficiently mention AI consent / wellness posture",
                )
            )
            return results

    results.append(
        (True, tag, "AI consent store + disclosure sheet exist, reviewer notes cover topic")
    )
    return results


def check_reviewer_pack() -> Results:
    """Verify reviewer notes exist and contain required posture markers."""
    results: Results = []
    tag = "reviewer_pack"

    if not REVIEWER_NOTES.exists():
        results.append((False, tag, f"File missing: {REVIEWER_NOTES}"))
        return results

    content = REVIEWER_NOTES.read_text(encoding="utf-8")
    lower = content.lower()

    # Required posture markers.
    required_markers = {
        "read-only": ["read-only", "read only"],
        "wellness_posture": ["does not diagnose", "does not treat", "not medical"],
        "healthkit_mention": ["healthkit", "health kit", "health access"],
    }

    for label, patterns in required_markers.items():
        if not any(p in lower for p in patterns):
            results.append((False, tag, f"Reviewer notes missing required marker: {label}"))
            return results

    # No real credentials pattern.
    credential_patterns = [
        re.compile(r"password\s*[:=]\s*\S+", re.IGNORECASE),
        re.compile(r"secret\s*[:=]\s*\S+", re.IGNORECASE),
        re.compile(r"api[_-]?key\s*[:=]\s*[A-Za-z0-9]{16,}", re.IGNORECASE),
    ]
    for pat in credential_patterns:
        if pat.search(content):
            results.append((False, tag, f"Reviewer notes may contain credentials: {pat.pattern}"))
            return results

    results.append((True, tag, "Reviewer notes present with required posture markers"))
    return results


def check_screenshot_policy() -> Results:
    """Verify screenshot asset gate exists and has no submission overclaims."""
    results: Results = []
    tag = "screenshot_policy"

    if not SCREENSHOT_GATE.exists():
        results.append((False, tag, f"File missing: {SCREENSHOT_GATE}"))
        return results

    content = SCREENSHOT_GATE.read_text(encoding="utf-8")

    # Collect scenario-to-classification mappings from markdown table rows.
    # Each row looks like: | `scenario_name` | ... | `CLASSIFICATION` | ...
    # The classification can appear in any column.
    scenario_classifications: dict[str, set[str]] = {}
    row_re = re.compile(r"^\|(.+)\|$", re.MULTILINE)
    for row_match in row_re.finditer(content):
        cells = [c.strip().strip("`") for c in row_match.group(1).split("|")]
        # Identify scenario name (first cell that looks like a snake_case identifier).
        scenario = None
        for cell in cells:
            if re.fullmatch(r"[a-z][a-z0-9_]*", cell):
                scenario = cell
                break
        if not scenario:
            continue
        # Identify classification in this row.
        for cell in cells:
            upper = cell.upper()
            if upper in ("SUBMIT_READY", "IMPLEMENTATION_REQUIRED", "INTERNAL_REVIEW_ONLY"):
                scenario_classifications.setdefault(scenario, set()).add(upper)

    submit_ready = {s for s, cl in scenario_classifications.items() if "SUBMIT_READY" in cl}
    impl_required = {
        s for s, cl in scenario_classifications.items() if "IMPLEMENTATION_REQUIRED" in cl
    }

    overclaimed = submit_ready & impl_required
    if overclaimed:
        results.append(
            (
                False,
                tag,
                f"Scenarios claimed as both SUBMIT_READY and IMPLEMENTATION_REQUIRED: {overclaimed}",
            )
        )
        return results

    results.append(
        (True, tag, f"Screenshot policy OK ({len(submit_ready)} SUBMIT_READY, no overclaims)")
    )
    return results


def check_storekit_pricing_truth() -> Results:
    """Verify metadata does not hardcode prices or trial claims."""
    results: Results = []
    tag = "storekit_pricing_truth"

    files_to_scan = []
    for locale in LOCALES:
        locale_dir = METADATA_DIR / locale
        if not locale_dir.is_dir():
            continue
        for name in (
            "description.txt",
            "release_notes.txt",
            "promotional_text.txt",
            "subtitle.txt",
        ):
            p = locale_dir / name
            if p.exists():
                files_to_scan.append(p)

    if not files_to_scan:
        results.append((False, tag, "No metadata files found to scan"))
        return results

    for path in files_to_scan:
        content = path.read_text(encoding="utf-8")
        for pat in PRICING_PATTERNS:
            match = pat.search(content)
            if match:
                rel = path.relative_to(REPO_ROOT)
                results.append(
                    (
                        False,
                        tag,
                        f"Hardcoded pricing found in {rel}: '{match.group()}'",
                    )
                )
                return results

    results.append((True, tag, f"No hardcoded pricing in {len(files_to_scan)} metadata files"))
    return results


# --- Runner ---

ALL_CHECKS = [
    check_release_base_url,
    check_appicon_marketing,
    check_privacy_manifest,
    check_app_privacy_details,
    check_permission_strings,
    check_healthkit_readonly,
    check_ai_wellness_consent,
    check_reviewer_pack,
    check_screenshot_policy,
    check_storekit_pricing_truth,
]


def main() -> int:
    """Run all checks and print results."""
    all_results: Results = []
    for check_fn in ALL_CHECKS:
        results = check_fn()
        all_results.extend(results)

    passes = 0
    failures = 0
    for ok, tag, msg in all_results:
        status = "PASS" if ok else "FAIL"
        print(f"  {status}: {tag}: {msg}")
        if ok:
            passes += 1
        else:
            failures += 1

    print()
    print(f"Results: {passes} passed, {failures} failed")

    if failures > 0:
        print("FAILED: App Store submission readiness check did not pass.")
        return 1

    print("OK: All App Store submission readiness checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
