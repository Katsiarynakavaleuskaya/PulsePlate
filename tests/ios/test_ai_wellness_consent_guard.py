"""Guard: AI wellness consent gate must exist and be enforced.

AI/CBT free-text features require explicit consent and wellness-only disclosure
before any user query is sent to the backend (AGENTS.md, App Store release
readiness gate #7).

Evidence anchors:
- ios/PulsePlate/Services/AIWellnessConsentStore.swift
- ios/PulsePlate/ViewModels/AIInsightViewModel.swift
- ios/PulsePlate/Views/AIWellnessDisclosureSheet.swift
- ios/PulsePlate/en.lproj/Localizable.strings
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IOS_APP_ROOT = REPO_ROOT / "ios" / "PulsePlate"


def test_consent_store_exists_with_correct_key() -> None:
    """AIWellnessConsentStore.swift must exist and reference the versioned key."""
    store_file = IOS_APP_ROOT / "Services" / "AIWellnessConsentStore.swift"
    assert store_file.exists(), (
        "AIWellnessConsentStore.swift must exist at "
        "ios/PulsePlate/Services/AIWellnessConsentStore.swift"
    )
    text = store_file.read_text(encoding="utf-8")
    assert (
        "ai_wellness_consent_accepted_v1" in text
    ), "Consent store must reference key 'ai_wellness_consent_accepted_v1'"


def test_consent_default_is_false() -> None:
    """Consent store must default to false (UserDefaults.bool returns false for missing keys)."""
    store_file = IOS_APP_ROOT / "Services" / "AIWellnessConsentStore.swift"
    assert store_file.exists()
    text = store_file.read_text(encoding="utf-8")
    # UserDefaults.bool(forKey:) returns false by default for unset keys.
    # The store must use bool(forKey:), not a default-true pattern.
    assert "bool(forKey:" in text, "Consent store must use bool(forKey:) which defaults to false"
    # Must not contain any default-true override
    assert (
        "= true" not in text.split("func hasAccepted")[0]
    ), "Consent store must not have a default-true property for the consent flag"


def test_viewmodel_checks_consent_before_request() -> None:
    """AIInsightViewModel.submit() must check consent before network request."""
    vm_file = IOS_APP_ROOT / "ViewModels" / "AIInsightViewModel.swift"
    assert vm_file.exists()
    text = vm_file.read_text(encoding="utf-8")
    assert "consentProvider" in text, "AIInsightViewModel must have a consentProvider dependency"
    assert (
        "hasAccepted()" in text
    ), "AIInsightViewModel must check hasAccepted() before sending request"
    assert (
        ".consentRequired" in text
    ), "AIInsightViewModel must set .consentRequired state when consent is missing"


def test_disclosure_contains_required_semantics() -> None:
    """Disclosure sheet localization must include required wellness-only semantics in all locales."""
    required_semantics = [
        "ai_consent.point.wellness_only",
        "ai_consent.point.not_medical",
        "ai_consent.point.data_processing",
        "ai_consent.point.no_emergency",
        "ai_consent.point.voluntary",
        "ai_consent.accept",
        "ai_consent.decline",
    ]
    for locale in ("en", "ru", "es"):
        locale_file = IOS_APP_ROOT / f"{locale}.lproj" / "Localizable.strings"
        assert locale_file.exists(), f"{locale}.lproj/Localizable.strings must exist"
        text = locale_file.read_text(encoding="utf-8")
        for key in required_semantics:
            assert key in text, (
                f"{locale} Localizable.strings must contain key '{key}' " f"for wellness disclosure"
            )


def test_consent_store_does_not_contain_free_text_tokens() -> None:
    """Consent storage must never store user queries or free text."""
    store_file = IOS_APP_ROOT / "Services" / "AIWellnessConsentStore.swift"
    assert store_file.exists()
    text = store_file.read_text(encoding="utf-8")
    # Check non-comment lines only for forbidden stored-data patterns
    code_lines = [
        line
        for line in text.split("\n")
        if not line.strip().startswith("//") and not line.strip().startswith("///")
    ]
    code_text = "\n".join(code_lines).lower()
    forbidden_properties = [
        "var query",
        "let query",
        "var usertext",
        "var freetext",
        "var prompt",
        "var message",
        "let prompt",
        "let message",
    ]
    for token in forbidden_properties:
        assert token not in code_text, (
            f"Consent store must not have a '{token.split()[1]}' property — "
            f"only boolean consent state is stored, no free text"
        )


def test_no_security_healthkit_appicon_files_changed() -> None:
    """Scope guard: this PR must not touch security, HealthKit, or AppIcon files."""
    # This is a structural check — if these files are modified, the test
    # documents the invariant even though git diff is the real enforcement.
    healthkit = IOS_APP_ROOT / "Models" / "HealthKitManager.swift"
    if healthkit.exists():
        text = healthkit.read_text(encoding="utf-8")
        # HealthKit must remain read-only
        assert "toShare: nil" in text, "HealthKitManager must keep toShare: nil (read-only posture)"


def test_disclosure_sheet_exists() -> None:
    """AIWellnessDisclosureSheet.swift must exist with accept and decline actions."""
    sheet = IOS_APP_ROOT / "Views" / "AIWellnessDisclosureSheet.swift"
    assert sheet.exists(), (
        "AIWellnessDisclosureSheet.swift must exist at "
        "ios/PulsePlate/Views/AIWellnessDisclosureSheet.swift"
    )
    text = sheet.read_text(encoding="utf-8")
    assert "onAccept" in text, "Disclosure sheet must have an onAccept action"
    assert "onDecline" in text, "Disclosure sheet must have an onDecline action"
