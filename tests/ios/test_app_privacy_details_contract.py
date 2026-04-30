"""Contracts for App Privacy truth against current iOS network flows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_PRIVACY_DETAILS = REPO_ROOT / "ios/fastlane/app_privacy_details.json"
IOS_ROOT = REPO_ROOT / "ios/PulsePlate"

APP_FUNCTIONALITY = ["APP_FUNCTIONALITY"]
DATA_LINKED_TO_YOU = ["DATA_LINKED_TO_YOU"]
FASTLANE_APP_PRIVACY_CATEGORIES = {
    "ADVERTISING_DATA",
    "AUDIO",
    "BROWSING_HISTORY",
    "COARSE_LOCATION",
    "CONTACTS",
    "CREDIT_AND_FRAUD",
    "CUSTOMER_SUPPORT",
    "DEVICE_ID",
    "EMAIL_ADDRESS",
    "EMAILS_OR_TEXT_MESSAGES",
    "FITNESS",
    "GAMEPLAY_CONTENT",
    "HEALTH",
    "NAME",
    "OTHER_CONTACT_INFO",
    "OTHER_DATA",
    "OTHER_DIAGNOSTIC_DATA",
    "OTHER_FINANCIAL_INFO",
    "OTHER_USAGE_DATA",
    "OTHER_USER_CONTENT",
    "PAYMENT_INFORMATION",
    "PERFORMANCE_DATA",
    "PHONE_NUMBER",
    "PHOTOS_OR_VIDEOS",
    "PHYSICAL_ADDRESS",
    "PRECISE_LOCATION",
    "PRODUCT_INTERACTION",
    "PURCHASE_HISTORY",
    "SEARCH_HISTORY",
    "SENSITIVE_INFO",
    "USER_ID",
}


@dataclass(frozen=True)
class AppPrivacyRuntimeFlow:
    category: str
    source_paths: tuple[str, ...]
    source_markers: tuple[str, ...]
    purposes: list[str]
    data_protections: list[str]


RUNTIME_FLOW_DISCLOSURES = (
    AppPrivacyRuntimeFlow(
        category="HEALTH",
        source_paths=(
            "Services/ProDailyNutritionService.swift",
            "Services/ProfileProvider.swift",
        ),
        source_markers=(
            "/api/v1/pro/nutrition/daily",
            "sex",
            "height_cm",
            "weight_kg",
            "activity",
            "goal",
            "lang",
        ),
        purposes=APP_FUNCTIONALITY,
        data_protections=DATA_LINKED_TO_YOU,
    ),
    AppPrivacyRuntimeFlow(
        category="OTHER_USER_CONTENT",
        source_paths=("Services/CBTInsightService.swift",),
        source_markers=("/api/v1/pro/cbt/insight", "query"),
        purposes=APP_FUNCTIONALITY,
        data_protections=DATA_LINKED_TO_YOU,
    ),
    AppPrivacyRuntimeFlow(
        category="PURCHASE_HISTORY",
        source_paths=("Services/SubscriptionBillingService.swift",),
        source_markers=(
            "/api/v1/billing/apple/verify-receipt",
            "/api/v1/pro/payments/activate",
            "/api/v1/pro/payments/activations/",
        ),
        purposes=APP_FUNCTIONALITY,
        data_protections=DATA_LINKED_TO_YOU,
    ),
)


def _privacy_entries() -> list[dict[str, Any]]:
    with APP_PRIVACY_DETAILS.open(encoding="utf-8") as privacy_file:
        entries = json.load(privacy_file)

    assert isinstance(entries, list)
    return entries


def _entry_by_category() -> dict[str, dict[str, Any]]:
    entries = _privacy_entries()
    return {
        entry["category"]: entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("category"), str)
    }


def _source_text(paths: tuple[str, ...]) -> str:
    return "\n".join((IOS_ROOT / path).read_text(encoding="utf-8") for path in paths)


def _data_protections(entry: dict[str, Any]) -> list[str]:
    assert "data_protections" in entry
    data_protections = entry["data_protections"]
    assert isinstance(data_protections, list)
    assert all(isinstance(item, str) for item in data_protections)
    return data_protections


def test_app_privacy_no_longer_claims_nothing_collected() -> None:
    entries = _privacy_entries()

    assert entries
    assert all("DATA_NOT_COLLECTED" not in _data_protections(entry) for entry in entries)


def test_app_privacy_uses_fastlane_category_identifiers() -> None:
    entries = _privacy_entries()

    assert entries
    for entry in entries:
        assert entry["category"] in FASTLANE_APP_PRIVACY_CATEGORIES


def test_app_privacy_declares_profile_ai_and_billing_data_flows() -> None:
    entries = _entry_by_category()

    for flow in RUNTIME_FLOW_DISCLOSURES:
        assert flow.category in entries
        assert entries[flow.category]["purposes"] == flow.purposes
        assert _data_protections(entries[flow.category]) == flow.data_protections


def test_app_privacy_contract_tracks_current_ios_network_flows() -> None:
    entries = _entry_by_category()

    for flow in RUNTIME_FLOW_DISCLOSURES:
        source = _source_text(flow.source_paths)
        for marker in flow.source_markers:
            assert marker in source
        assert flow.category in entries


def test_app_privacy_does_not_enable_tracking_disclosures() -> None:
    entries = _privacy_entries()

    assert all("DATA_USED_TO_TRACK_YOU" not in _data_protections(entry) for entry in entries)
