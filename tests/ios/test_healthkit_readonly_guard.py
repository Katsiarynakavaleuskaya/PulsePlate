"""Guard: HealthKit must remain read-only (no write authorization, no write samples).

This test enforces the repo-wide invariant from AGENTS.md:
  "HealthKit must remain read-only unless a separate reviewed PR changes
   entitlement posture."

Evidence anchors:
  - ios/PulsePlate/Models/HealthKitManager.swift (toShare: nil)
  - ios/PulsePlate/en.lproj/InfoPlist.strings (NSHealthShareUsageDescription)
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HEALTHKIT_MANAGER = REPO_ROOT / "ios" / "PulsePlate" / "Models" / "HealthKitManager.swift"
EN_INFOPLIST = REPO_ROOT / "ios" / "PulsePlate" / "en.lproj" / "InfoPlist.strings"
RU_INFOPLIST = REPO_ROOT / "ios" / "PulsePlate" / "ru.lproj" / "InfoPlist.strings"
ES_INFOPLIST = REPO_ROOT / "ios" / "PulsePlate" / "es.lproj" / "InfoPlist.strings"


def test_healthkit_authorization_is_read_only() -> None:
    """Verify requestAuthorization uses toShare: nil (read-only)."""
    text = HEALTHKIT_MANAGER.read_text(encoding="utf-8")
    assert "toShare: nil" in text, (
        "HealthKitManager must use toShare: nil for read-only authorization. "
        "Write authorization requires a separate reviewed PR."
    )


def test_no_write_permission_string_in_infoplist() -> None:
    """No NSHealthUpdateUsageDescription in any locale (write permission)."""
    for plist in (EN_INFOPLIST, RU_INFOPLIST, ES_INFOPLIST):
        if plist.exists():
            content = plist.read_text(encoding="utf-8")
            assert "NSHealthUpdateUsageDescription" not in content, (
                f"{plist.name} must not contain NSHealthUpdateUsageDescription "
                f"(write permission) while HealthKit posture is read-only."
            )


def test_read_permission_string_present() -> None:
    """NSHealthShareUsageDescription must be present in en and ru locales."""
    for plist in (EN_INFOPLIST, RU_INFOPLIST):
        content = plist.read_text(encoding="utf-8")
        assert "NSHealthShareUsageDescription" in content, (
            f"{plist.name} must contain NSHealthShareUsageDescription "
            f"(read permission string for HealthKit)."
        )


def test_healthkit_manager_does_not_write_samples() -> None:
    """HealthKitManager must not contain write operations."""
    text = HEALTHKIT_MANAGER.read_text(encoding="utf-8")
    forbidden_tokens = [
        ".save(",
        "deleteObjects",
        "HKWorkout(",
        "HKWorkoutBuilder",
        "toShare: Set",
        "toShare: [",
    ]
    for token in forbidden_tokens:
        assert token not in text, (
            f"HealthKitManager.swift must not contain '{token}'. "
            f"Write operations are forbidden while HealthKit posture is read-only."
        )


def test_no_local_function_in_fetch_daily_totals() -> None:
    """fetchDailyTotals must not contain a nested local function (Swift 6 fix).

    The original code had ``func sum(_ id:)`` nested inside
    ``fetchDailyTotals``, which caused sendability warnings in Swift 6.
    After the fix, the helper is a private instance method ``fetchSum``.
    """
    text = HEALTHKIT_MANAGER.read_text(encoding="utf-8")
    # Find the fetchDailyTotals method body
    start_marker = "func fetchDailyTotals("
    end_marker = "private func fetchSum("
    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker)
    assert start_idx != -1, "fetchDailyTotals method must exist"
    assert end_idx != -1, "fetchSum private method must exist (Swift 6 extraction)"
    # The body between fetchDailyTotals start and fetchSum should NOT contain
    # a nested function definition
    body = text[start_idx:end_idx]
    # Check no "func sum(" or "func " inside the method body (after first line)
    lines = body.split("\n")[1:]  # skip the method signature line
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("func "):
            raise AssertionError(
                f"Local function found inside fetchDailyTotals: '{stripped}'. "
                f"Nested functions cause Swift 6 sendability warnings. "
                f"Use private instance methods instead."
            )
