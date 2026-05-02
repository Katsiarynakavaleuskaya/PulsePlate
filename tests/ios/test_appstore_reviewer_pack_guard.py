"""Guard: App Store reviewer pack must stay aligned with release runtime truth.

Deterministic checks that reviewer notes, metadata descriptions, and release
notes are consistent with current release posture.  No network, no mocks,
no dynamic imports — pure file-content scanning.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NOTES_PATH = REPO_ROOT / "ios/fastlane/metadata/review_information/notes.txt"
APP_PRIVACY_PATH = REPO_ROOT / "ios/fastlane/app_privacy_details.json"
LOCALES = ("en-US", "ru-RU", "es-ES")
METADATA_ROOT = REPO_ROOT / "ios/fastlane/metadata"

# --- Forbidden patterns (positive medical/pricing claims) ---

# These match positive claims; negation-form disclaimers are NOT matched.
MEDICAL_CLAIM_RE = re.compile(
    r"\b(?:we\s+(?:diagnos|treat|cure|prescrib))"
    r"|(?:(?:will|can|does)\s+(?:diagnos|treat|cure|prescrib))"
    r"|(?:medical[\s-]*grade)"
    r"|(?:guaranteed\s+(?:weight\s+loss|health\s+outcome))"
    r"|(?:crisis\s+support)"
    r"|(?:replaces?\s+(?:your\s+)?doctor)",
    re.IGNORECASE,
)

HARDCODED_PRICE_RE = re.compile(
    r"\$\d+(?:\.\d{2})?"
    r"|€\d+(?:\.\d{2})?"
    r"|(?:per\s+month\s+\$)"
    r"|(?:free\s+trial\s+(?:for\s+)?\d+\s+days)",
    re.IGNORECASE,
)

SECRET_RE = re.compile(
    r"(?:password|secret|token|api[_-]?key)\s*[:=]\s*\S+",
    re.IGNORECASE,
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── Reviewer Notes ────────────────────────────────────────────────


class TestReviewerNotesWellnessPositioning:
    """Reviewer notes must state wellness-only positioning."""

    def test_notes_mention_no_medical_advice(self) -> None:
        text = _read(NOTES_PATH).lower()
        assert "does not diagnose" in text or "not medical" in text

    def test_notes_mention_no_therapy(self) -> None:
        text = _read(NOTES_PATH).lower()
        assert "not therapy" in text or "not a substitute" in text


class TestReviewerNotesAIDisclosure:
    """Reviewer notes must disclose AI consent and third-party provider."""

    def test_notes_mention_ai_consent(self) -> None:
        text = _read(NOTES_PATH).lower()
        assert "consent" in text and "ai" in text

    def test_notes_mention_third_party_provider(self) -> None:
        text = _read(NOTES_PATH).lower()
        assert "provider" in text or "third-party" in text or "external" in text

    def test_notes_mention_data_sent(self) -> None:
        text = _read(NOTES_PATH).lower()
        assert "query" in text or "user data" in text or "free-text" in text


class TestReviewerNotesHealthKit:
    """Reviewer notes must confirm HealthKit read-only posture."""

    def test_notes_mention_read_only(self) -> None:
        text = _read(NOTES_PATH).lower()
        assert "read-only" in text or "read only" in text

    def test_notes_mention_optional(self) -> None:
        text = _read(NOTES_PATH).lower()
        assert "optional" in text

    def test_notes_mention_revocable(self) -> None:
        text = _read(NOTES_PATH).lower()
        assert "revoke" in text or "revocable" in text


class TestReviewerNotesNoPricingSecrets:
    """Reviewer notes must not contain hardcoded pricing or secrets."""

    def test_no_hardcoded_pricing(self) -> None:
        text = _read(NOTES_PATH)
        match = HARDCODED_PRICE_RE.search(text)
        assert match is None, f"Hardcoded pricing found: {match.group()!r}"

    def test_no_secrets(self) -> None:
        text = _read(NOTES_PATH)
        match = SECRET_RE.search(text)
        assert match is None, f"Secret-like pattern found: {match.group()!r}"


class TestReviewerNotesFeatureLimitations:
    """Reviewer notes must disclose features that are not submission-ready."""

    def test_notes_mention_implementation_required(self) -> None:
        text = _read(NOTES_PATH).lower()
        assert (
            "implementation_required" in text
            or "not included in public" in text
            or "not release-enabled" in text
        )


# ── Metadata Descriptions ────────────────────────────────────────


class TestDescriptionsCompliance:
    """App Store descriptions must not contain forbidden claims."""

    @pytest.mark.parametrize("locale", LOCALES)
    def test_no_forbidden_medical_claims(self, locale: str) -> None:
        path = METADATA_ROOT / locale / "description.txt"
        text = _read(path)
        match = MEDICAL_CLAIM_RE.search(text)
        assert (
            match is None
        ), f"{locale}/description.txt contains forbidden claim: {match.group()!r}"

    @pytest.mark.parametrize("locale", LOCALES)
    def test_no_hardcoded_pricing(self, locale: str) -> None:
        path = METADATA_ROOT / locale / "description.txt"
        text = _read(path)
        match = HARDCODED_PRICE_RE.search(text)
        assert (
            match is None
        ), f"{locale}/description.txt contains hardcoded pricing: {match.group()!r}"


# ── Release Notes ─────────────────────────────────────────────────


class TestReleaseNotesExistAndNonEmpty:
    """Release notes must exist and be non-empty for all locales."""

    @pytest.mark.parametrize("locale", LOCALES)
    def test_release_notes_exist_and_nonempty(self, locale: str) -> None:
        path = METADATA_ROOT / locale / "release_notes.txt"
        assert path.is_file(), f"Missing: {locale}/release_notes.txt"
        text = _read(path).strip()
        assert len(text) > 10, f"{locale}/release_notes.txt is too short"

    @pytest.mark.parametrize("locale", LOCALES)
    def test_release_notes_no_medical_claims(self, locale: str) -> None:
        path = METADATA_ROOT / locale / "release_notes.txt"
        text = _read(path)
        match = MEDICAL_CLAIM_RE.search(text)
        assert (
            match is None
        ), f"{locale}/release_notes.txt contains forbidden claim: {match.group()!r}"


# ── App Privacy Cross-Check ───────────────────────────────────────


class TestAppPrivacyCrossCheck:
    """App Privacy must not contradict reviewer notes."""

    def test_app_privacy_does_not_claim_data_not_collected(self) -> None:
        data = json.loads(_read(APP_PRIVACY_PATH))
        protections = set()
        for entry in data:
            for prot in entry.get("data_protections", []):
                protections.add(prot)
        assert "DATA_NOT_COLLECTED" not in protections, (
            "app_privacy_details.json claims DATA_NOT_COLLECTED "
            "but HEALTH/PURCHASE_HISTORY/OTHER_USER_CONTENT are declared"
        )

    def test_app_privacy_declares_known_categories(self) -> None:
        data = json.loads(_read(APP_PRIVACY_PATH))
        categories = {entry["category"] for entry in data}
        expected = {"HEALTH", "PURCHASE_HISTORY", "OTHER_USER_CONTENT"}
        assert expected <= categories, f"Missing App Privacy categories: {expected - categories}"
