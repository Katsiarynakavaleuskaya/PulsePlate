"""Contracts for App Privacy truth against current iOS network flows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_PRIVACY_DETAILS = REPO_ROOT / "ios/fastlane/app_privacy_details.json"
IOS_ROOT = REPO_ROOT / "ios/PulsePlate"

NETWORK_FLOW_CATEGORIES = {
    "HEALTH_AND_FITNESS": {
        "paths": [
            "Services/ProDailyNutritionService.swift",
            "Services/ProfileProvider.swift",
        ],
        "needles": [
            "/api/v1/pro/nutrition/daily",
            "sex",
            "height_cm",
            "weight_kg",
            "activity",
            "goal",
            "lang",
        ],
    },
    "USER_CONTENT": {
        "paths": ["Services/CBTInsightService.swift"],
        "needles": ["/api/v1/pro/cbt/insight", "query"],
    },
    "PURCHASES": {
        "paths": ["Services/SubscriptionBillingService.swift"],
        "needles": [
            "/api/v1/billing/apple/verify-receipt",
            "/api/v1/pro/payments/activate",
            "/api/v1/pro/payments/activations/",
        ],
    },
}


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


def _source_text(paths: list[str]) -> str:
    return "\n".join((IOS_ROOT / path).read_text(encoding="utf-8") for path in paths)


def test_app_privacy_no_longer_claims_nothing_collected() -> None:
    entries = _privacy_entries()

    assert entries
    assert all("DATA_NOT_COLLECTED" not in entry.get("data_protections", []) for entry in entries)


def test_app_privacy_declares_profile_ai_and_billing_data_flows() -> None:
    entries = _entry_by_category()

    for category in NETWORK_FLOW_CATEGORIES:
        assert category in entries
        assert entries[category]["purposes"] == ["APP_FUNCTIONALITY"]
        assert entries[category]["data_protections"] == ["DATA_LINKED_TO_YOU"]


def test_app_privacy_contract_tracks_current_ios_network_flows() -> None:
    entries = _entry_by_category()

    for category, flow in NETWORK_FLOW_CATEGORIES.items():
        source = _source_text(flow["paths"])
        for needle in flow["needles"]:
            assert needle in source
        assert category in entries


def test_app_privacy_does_not_enable_tracking_disclosures() -> None:
    entries = _privacy_entries()

    assert all(
        "DATA_USED_TO_TRACK_YOU" not in entry.get("data_protections", []) for entry in entries
    )
