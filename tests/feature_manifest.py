"""
tests/feature_manifest.py

Single source of truth for optional-feature availability in runtime SKIPPED suites.

RU: Edinyi manifest optsionalnykh fich dlia testov. Liubye SKIPPED vida
"module not available" dolzhny idti cherez require_feature(...), a ne cherez ad-hoc
stroki v testakh.

EN: A single manifest to standardize skip reasons for optional modules/features.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import FrozenSet, NoReturn

import pytest

ENV_FEATURES = "PULSEPLATE_FEATURES"
FEATURE_REASON = "Feature not implemented yet; see BACKLOG_LEDGER (Target PR: PR-738+)."


@dataclass(frozen=True)
class FeatureManifest:
    """Feature availability manifest controlled via env.

    RU: Upravliaetsia peremennoi okruzheniia PULSEPLATE_FEATURES:
      - "all" -> vkliuchit vse fichi (dlia budushchego CI job)
      - ""/unset -> vkliuchit tolko bazovye (po umolchaniiu pochti nichego)
      - "a,b,c" -> vkliuchit konkretnye kliuchi
    """

    enabled: FrozenSet[str]

    @staticmethod
    def from_env() -> "FeatureManifest":
        raw = (os.getenv(ENV_FEATURES) or "").strip()
        if raw.lower() == "all":
            return FeatureManifest(enabled=frozenset(FEATURE_TODO_KEYS))
        if not raw:
            return FeatureManifest(enabled=frozenset())
        parts = [part.strip() for part in raw.split(",") if part.strip()]
        return FeatureManifest(enabled=frozenset(parts))

    def is_enabled(self, key: str) -> bool:
        return key in self.enabled


# Canonical feature TODO keys (must match BACKLOG_LEDGER item; one-to-one mapping).
FEATURE_TODO_KEYS: FrozenSet[str] = frozenset(
    {
        "coverage_boost_main_entrypoint",
        "core_db",
        "food_apis",
        "food_apis_error_injection",
        "main_entrypoint",
        "unified_db",
        "unified_db_language",
        "update_scheduler",
        "update_manager",
        "update_manager_path_attrs",
        "planner_engines",
        "premium_week_planner",
        "premium_week_router_mocking",
        "i18n_advanced",
        "rag",
        "region_catalog",
        "shoplist_helpers",
        "shoplist_weekly_helpers",
        "targets_fixture_data",
        "ui_labels_contract",
        "utils_pack",
        "weekly_plan_helpers",
        "exports_recipes_products",
        "sports_disclaimers_lifestage",
        "legacy_bmi_removed",
        "nutrient_recommendations",
    }
)


def require_feature(key: str, reason: str, *, manifest: FeatureManifest | None = None) -> None:
    """Skip test if optional feature isn't enabled.

    RU: Zapreshcheny ad-hoc skip-stroki v high-noise suites. Ispolzui tolko eto.

    Args:
        key: canonical feature TODO key (must be in FEATURE_TODO_KEYS).
        reason: human-readable reason; should reference BACKLOG_LEDGER + target PR.
        manifest: optional injected manifest (mainly for testing).
    """
    if key not in FEATURE_TODO_KEYS:
        raise AssertionError(
            f"Unknown feature key: {key!r}. Must be one of: {sorted(FEATURE_TODO_KEYS)}"
        )

    active_manifest = manifest or FeatureManifest.from_env()
    if active_manifest.is_enabled(key):
        return

    standardized = f"feature_disabled:{key} (enable via {ENV_FEATURES}=all or CSV). " f"{reason}"
    pytest.skip(standardized)


def fail_feature_gated_test(key: str, reason: str) -> NoReturn:
    """Fail fast when a feature gate is enabled but canonical assertions are not implemented.

    RU: Edinyi fail-shablon dlia intentional fail pod feature gate.
    EN: Canonical fail pattern for intentional feature-gated test failures.
    """
    if key not in FEATURE_TODO_KEYS:
        raise AssertionError(
            f"Unknown feature key: {key!r}. Must be one of: {sorted(FEATURE_TODO_KEYS)}"
        )

    exc = AssertionError(reason)
    pytest.fail(f"[feature_gate:{key}] {exc!r}")


def require_feature_or_raise(
    exc: ImportError,
    key: str,
    reason: str,
    *,
    manifest: FeatureManifest | None = None,
) -> None:
    """Skip only when feature is disabled, otherwise re-raise ImportError.

    RU: Esli feature vkliuchena v manifest, ImportError ne dolzhen byt skryt.
    EN: If feature is enabled, preserve failure signal by re-raising ImportError.
    """
    active_manifest = manifest or FeatureManifest.from_env()
    if active_manifest.is_enabled(key):
        raise exc
    require_feature(key, reason, manifest=active_manifest)
