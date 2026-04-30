"""
Deterministic MenuStat source-decision cleanup gate.

RU: Файловая проверка решения PR10: MenuStat архивный источник, FatSecret не
является проектной опорой, chain public pages только research lane.
EN: File-only PR10 decision gate: MenuStat is archival, FatSecret is not a
project source, and chain public pages remain a research-only lane.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from core.food_sources.menustat_replacement import (
    MENUSTAT_SOURCE,
    MenuStatReplacementDecision,
    MenuStatReplacementError,
    load_menustat_replacement_decision,
)
from core.food_sources.source_catalog import (
    SourceCatalog,
    SourceCatalogEntry,
    SourceCatalogError,
    load_source_catalog,
)
from core.food_sources.source_onboarding import (
    SourceOnboarding,
    SourceOnboardingError,
    load_source_onboarding,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DECISION_SCHEMA_RE = re.compile(r"^food-data-menustat-source-decision\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FAT_PLATFORM_SOURCE = "fat" + "secret_platform"
_CHAIN_PUBLIC_SOURCE = "chain_public_nutrition_pages"
_EXPECTED_SOURCE_ORDER = (
    "nutritionix",
    _FAT_PLATFORM_SOURCE,
    "spoonacular",
    _CHAIN_PUBLIC_SOURCE,
)
_SAFETY_FLAG_TEMPLATE: dict[str, bool] = {
    "runtime_cutover": False,
    "digitalocean_postgres_load": False,
    "bulk_ingest": False,
    "network_allowed": False,
    "db_writes_allowed": False,
    "api_calls_allowed": False,
    "source_download_allowed": False,
    "scraping_allowed": False,
    "file_only": True,
}
_DECISION_KEYS = frozenset(
    {
        "schema_version",
        "generated_on",
        "catalog_ref",
        "onboarding_ref",
        "menustat_replacement_ref",
        "legacy_source",
        "menustat_archival_policy",
        "preferred_research_lane",
        "budget_api_review",
        "public_web_evidence_policy",
        "source_decisions",
        "runtime_cutover",
        "digitalocean_postgres_load",
        "bulk_ingest",
        "network_allowed",
        "db_writes_allowed",
        "api_calls_allowed",
        "source_download_allowed",
        "scraping_allowed",
        "file_only",
        "final_gate_decision",
        "notes",
    }
)
_BUDGET_API_REVIEW_KEYS = frozenset(
    {
        "source",
        "source_family",
        "review_lane_decision",
        "starter_budget_usd_per_month",
        "pricing_evidence_ref",
        "authority_decision",
        "api_calls_allowed",
        "cache_policy_status",
        "attribution_status",
        "notes",
    }
)
_PUBLIC_WEB_POLICY_KEYS = frozenset(
    {
        "policy_decision",
        "allowed_surfaces",
        "allowed_capture_methods",
        "blocked_methods",
        "legal_review_required",
        "anti_scraping_review_required",
        "copyright_review_required",
        "automation_allowed",
        "redistribution_allowed",
        "public_claim_allowed",
        "notes",
    }
)
_ARCHIVAL_POLICY_KEYS = frozenset(
    {
        "source",
        "source_classification",
        "archival_reference_only",
        "freshness_authority",
        "active_update_source",
        "replacement_required",
        "validation_required_before_use",
        "allowed_use",
        "blocked_use",
        "notes",
    }
)
_SOURCE_DECISION_KEYS = frozenset(
    {
        "source",
        "project_source_decision",
        "research_lane_decision",
        "authority_decision",
        "automation_approved",
        "eligible_preflight",
        "approved_ingest",
        "blocking_reasons",
        "notes",
    }
)
_EXPECTED_PROJECT_DECISIONS: dict[str, dict[str, object]] = {
    "nutritionix": {
        "project_source_decision": "deferred_contract_review",
        "research_lane_decision": "not_preferred_for_budget_first_lane",
    },
    _FAT_PLATFORM_SOURCE: {
        "project_source_decision": "not_project_source",
        "research_lane_decision": "rejected_for_project_use",
    },
    "spoonacular": {
        "project_source_decision": "deferred_recipe_experiments_only",
        "research_lane_decision": "not_restaurant_authority",
    },
    _CHAIN_PUBLIC_SOURCE: {
        "project_source_decision": "preferred_research_lane",
        "research_lane_decision": "chain_public_pages_governance_first",
    },
}

FINAL_GATE_DECISION = "source_decision_locked_no_ingest"


class MenuStatSourceDecisionError(ValueError):
    """Raised when the PR10 MenuStat source-decision gate is invalid."""


@dataclass(frozen=True)
class MenuStatArchivalPolicy:
    """Validated archival policy for MenuStat."""

    source: str
    source_classification: str
    archival_reference_only: bool
    freshness_authority: bool
    active_update_source: bool
    replacement_required: bool
    validation_required_before_use: bool
    allowed_use: tuple[str, ...]
    blocked_use: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class SourceDecision:
    """One PR10 source decision row."""

    source: str
    project_source_decision: str
    research_lane_decision: str
    authority_decision: str
    automation_approved: bool
    eligible_preflight: bool
    approved_ingest: bool
    blocking_reasons: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class BudgetApiReview:
    """Adjacent under-budget API review lane, not a source approval."""

    source: str
    source_family: str
    review_lane_decision: str
    starter_budget_usd_per_month: int
    pricing_evidence_ref: str
    authority_decision: str
    api_calls_allowed: bool
    cache_policy_status: str
    attribution_status: str
    notes: str


@dataclass(frozen=True)
class PublicWebEvidencePolicy:
    """Manual public-web evidence policy before any automated collection."""

    policy_decision: str
    allowed_surfaces: tuple[str, ...]
    allowed_capture_methods: tuple[str, ...]
    blocked_methods: tuple[str, ...]
    legal_review_required: bool
    anti_scraping_review_required: bool
    copyright_review_required: bool
    automation_allowed: bool
    redistribution_allowed: bool
    public_claim_allowed: bool
    notes: str


@dataclass(frozen=True)
class MenuStatSourceDecision:
    """Validated PR10 source-decision artifact."""

    schema_version: str
    generated_on: date
    catalog_ref: str
    onboarding_ref: str
    menustat_replacement_ref: str
    legacy_source: str
    menustat_archival_policy: MenuStatArchivalPolicy
    preferred_research_lane: str
    budget_api_review: BudgetApiReview
    public_web_evidence_policy: PublicWebEvidencePolicy
    source_decisions: tuple[SourceDecision, ...]
    final_gate_decision: str
    notes: str


def _decision_error(context: str, detail: str) -> MenuStatSourceDecisionError:
    return MenuStatSourceDecisionError(f"Invalid MenuStat source decision {context}: {detail}")


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _decision_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _decision_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _decision_error(context, f"missing non-empty string '{key}'")
    return value.strip()


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _decision_error(context, f"'{key}' must be a boolean")
    return value


def _require_int(data: dict[str, object], key: str, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _decision_error(context, f"'{key}' must be an integer")
    return value


def _require_string_tuple(
    data: dict[str, object],
    key: str,
    context: str,
) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list):
        raise _decision_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _decision_error(context, f"'{key}[{index}]' must be a non-empty string")
        normalized = item.strip()
        if normalized in seen:
            raise _decision_error(context, f"'{key}' contains duplicate value {normalized!r}")
        seen.add(normalized)
        items.append(normalized)
    if not items:
        raise _decision_error(context, f"'{key}' must not be empty")
    return tuple(items)


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _decision_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _decision_error(context, "generated_on must use YYYY-MM-DD") from exc


def _relative_repo_path(path: Path | str) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _entry_by_source(catalog: SourceCatalog) -> dict[str, SourceCatalogEntry]:
    return {entry.source: entry for entry in catalog.sources}


def _require_safety_flags(data: dict[str, object], context: str) -> None:
    safety_flags = {key: _require_bool(data, key, context) for key in _SAFETY_FLAG_TEMPLATE}
    if safety_flags != _SAFETY_FLAG_TEMPLATE:
        raise _decision_error(
            context,
            "runtime_cutover, digitalocean_postgres_load, bulk_ingest, network_allowed, "
            "db_writes_allowed, api_calls_allowed, source_download_allowed, and "
            "scraping_allowed must be false; file_only must be true",
        )


def _parse_archival_policy(
    value: object,
    catalog: SourceCatalog,
    context: str,
) -> MenuStatArchivalPolicy:
    data = _require_mapping(value, context)
    unexpected_keys = sorted(set(data) - _ARCHIVAL_POLICY_KEYS)
    if unexpected_keys:
        raise _decision_error(
            context, f"unexpected archival policy keys: {', '.join(unexpected_keys)}"
        )
    policy = MenuStatArchivalPolicy(
        source=_require_string(data, "source", context),
        source_classification=_require_string(data, "source_classification", context),
        archival_reference_only=_require_bool(data, "archival_reference_only", context),
        freshness_authority=_require_bool(data, "freshness_authority", context),
        active_update_source=_require_bool(data, "active_update_source", context),
        replacement_required=_require_bool(data, "replacement_required", context),
        validation_required_before_use=_require_bool(
            data, "validation_required_before_use", context
        ),
        allowed_use=_require_string_tuple(data, "allowed_use", context),
        blocked_use=_require_string_tuple(data, "blocked_use", context),
        notes=_require_string(data, "notes", context),
    )
    if policy.source != MENUSTAT_SOURCE:
        raise _decision_error(context, "archival policy source must be menustat")
    if policy.source_classification != "legacy_static":
        raise _decision_error(context, "MenuStat must remain legacy_static")
    if not policy.archival_reference_only:
        raise _decision_error(context, "MenuStat must be archival_reference_only")
    if policy.freshness_authority:
        raise _decision_error(context, "MenuStat cannot be freshness authority")
    if policy.active_update_source:
        raise _decision_error(context, "MenuStat cannot be an active update source")
    if not policy.replacement_required:
        raise _decision_error(context, "MenuStat must remain replacement_required")
    if not policy.validation_required_before_use:
        raise _decision_error(context, "MenuStat data requires validation before use")

    menustat = _entry_by_source(catalog).get(MENUSTAT_SOURCE)
    if menustat is None:
        raise _decision_error(context, "catalog must include menustat")
    if menustat.source_classification != "legacy_static":
        raise _decision_error(context, "catalog MenuStat classification drifted")
    if menustat.active_update_source:
        raise _decision_error(context, "catalog MenuStat cannot be active_update_source")
    if not menustat.replacement_required:
        raise _decision_error(context, "catalog MenuStat must remain replacement_required")
    return policy


def _parse_budget_api_review(value: object, context: str) -> BudgetApiReview:
    data = _require_mapping(value, context)
    unexpected_keys = sorted(set(data) - _BUDGET_API_REVIEW_KEYS)
    if unexpected_keys:
        raise _decision_error(context, f"unexpected budget API keys: {', '.join(unexpected_keys)}")
    review = BudgetApiReview(
        source=_require_string(data, "source", context),
        source_family=_require_string(data, "source_family", context),
        review_lane_decision=_require_string(data, "review_lane_decision", context),
        starter_budget_usd_per_month=_require_int(data, "starter_budget_usd_per_month", context),
        pricing_evidence_ref=_require_string(data, "pricing_evidence_ref", context),
        authority_decision=_require_string(data, "authority_decision", context),
        api_calls_allowed=_require_bool(data, "api_calls_allowed", context),
        cache_policy_status=_require_string(data, "cache_policy_status", context),
        attribution_status=_require_string(data, "attribution_status", context),
        notes=_require_string(data, "notes", context),
    )
    if review.source != "edamam_food_database":
        raise _decision_error(context, "budget API review source must be edamam_food_database")
    if review.source_family != "recipe_corpus":
        raise _decision_error(context, "budget API review must stay recipe_corpus")
    if review.review_lane_decision != "adjacent_recipe_food_db_review_only":
        raise _decision_error(context, "budget API review must stay adjacent review only")
    if review.starter_budget_usd_per_month > 20:
        raise _decision_error(context, "budget API review must stay at or below 20 USD/month")
    if review.authority_decision != "not_approved" or review.api_calls_allowed:
        raise _decision_error(context, "budget API review cannot approve authority or API calls")
    if review.cache_policy_status != "blocked_terms_review_required":
        raise _decision_error(context, "budget API cache policy must require terms review")
    if review.attribution_status != "blocked_attribution_review_required":
        raise _decision_error(context, "budget API attribution must require review")
    return review


def _parse_public_web_policy(value: object, context: str) -> PublicWebEvidencePolicy:
    data = _require_mapping(value, context)
    unexpected_keys = sorted(set(data) - _PUBLIC_WEB_POLICY_KEYS)
    if unexpected_keys:
        raise _decision_error(
            context, f"unexpected public web policy keys: {', '.join(unexpected_keys)}"
        )
    policy = PublicWebEvidencePolicy(
        policy_decision=_require_string(data, "policy_decision", context),
        allowed_surfaces=_require_string_tuple(data, "allowed_surfaces", context),
        allowed_capture_methods=_require_string_tuple(data, "allowed_capture_methods", context),
        blocked_methods=_require_string_tuple(data, "blocked_methods", context),
        legal_review_required=_require_bool(data, "legal_review_required", context),
        anti_scraping_review_required=_require_bool(data, "anti_scraping_review_required", context),
        copyright_review_required=_require_bool(data, "copyright_review_required", context),
        automation_allowed=_require_bool(data, "automation_allowed", context),
        redistribution_allowed=_require_bool(data, "redistribution_allowed", context),
        public_claim_allowed=_require_bool(data, "public_claim_allowed", context),
        notes=_require_string(data, "notes", context),
    )
    if policy.policy_decision != "manual_evidence_only_legal_review_required":
        raise _decision_error(context, "public web policy must stay manual evidence only")
    required_surfaces = {"official_restaurant_website", "official_restaurant_social_account"}
    if not required_surfaces.issubset(set(policy.allowed_surfaces)):
        raise _decision_error(
            context, "public web policy must include official website/social surfaces"
        )
    required_methods = {"url_citation", "manual_screenshot_for_internal_review"}
    if not required_methods.issubset(set(policy.allowed_capture_methods)):
        raise _decision_error(context, "public web policy must include URL citation and screenshot")
    if not (
        policy.legal_review_required
        and policy.anti_scraping_review_required
        and policy.copyright_review_required
    ):
        raise _decision_error(context, "public web policy must require legal reviews")
    if policy.automation_allowed or policy.redistribution_allowed or policy.public_claim_allowed:
        raise _decision_error(
            context, "public web policy cannot approve automation or redistribution"
        )
    return policy


def _parse_source_decision(value: object, context: str) -> SourceDecision:
    data = _require_mapping(value, context)
    unexpected_keys = sorted(set(data) - _SOURCE_DECISION_KEYS)
    if unexpected_keys:
        raise _decision_error(
            context, f"unexpected source decision keys: {', '.join(unexpected_keys)}"
        )
    decision = SourceDecision(
        source=_require_string(data, "source", context),
        project_source_decision=_require_string(data, "project_source_decision", context),
        research_lane_decision=_require_string(data, "research_lane_decision", context),
        authority_decision=_require_string(data, "authority_decision", context),
        automation_approved=_require_bool(data, "automation_approved", context),
        eligible_preflight=_require_bool(data, "eligible_preflight", context),
        approved_ingest=_require_bool(data, "approved_ingest", context),
        blocking_reasons=_require_string_tuple(data, "blocking_reasons", context),
        notes=_require_string(data, "notes", context),
    )
    expected = _EXPECTED_PROJECT_DECISIONS.get(decision.source)
    if expected is None:
        raise _decision_error(context, f"unknown source decision: {decision.source}")
    mismatches = [
        key for key, expected_value in expected.items() if getattr(decision, key) != expected_value
    ]
    if mismatches:
        raise _decision_error(
            context, f"{decision.source} decision mismatch: {', '.join(mismatches)}"
        )
    if decision.authority_decision != "not_approved":
        raise _decision_error(context, f"{decision.source} cannot be source authority in PR10")
    if decision.automation_approved or decision.eligible_preflight or decision.approved_ingest:
        raise _decision_error(
            context, f"{decision.source} cannot be approved for automation or ingest"
        )
    return decision


def _validate_against_pr9(
    decisions: tuple[SourceDecision, ...],
    replacement: MenuStatReplacementDecision,
    context: str,
) -> None:
    pr9_by_source = {candidate.source: candidate for candidate in replacement.candidate_sources}
    for decision in decisions:
        candidate = pr9_by_source.get(decision.source)
        if candidate is None:
            raise _decision_error(context, f"PR9 replacement artifact missing {decision.source}")
        if candidate.authority_decision != "not_approved":
            raise _decision_error(context, f"PR9 candidate {decision.source} became approved")
        if candidate.replacement_for != MENUSTAT_SOURCE:
            raise _decision_error(context, f"PR9 candidate {decision.source} must replace menustat")


def parse_menustat_source_decision(
    payload: object,
    *,
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    replacement: MenuStatReplacementDecision,
    expected_catalog_ref: str | None = None,
    expected_onboarding_ref: str | None = None,
    expected_replacement_ref: str | None = None,
    context: str = "<menustat-source-decision>",
) -> MenuStatSourceDecision:
    """Parse and validate the PR10 MenuStat source-decision cleanup gate."""
    del onboarding  # PR5 is loaded for deterministic ref parity; no runtime behavior is used.
    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _DECISION_KEYS)
    if unexpected_keys:
        raise _decision_error(context, f"unexpected keys: {', '.join(unexpected_keys)}")

    schema_version = _require_string(data, "schema_version", context)
    if not _DECISION_SCHEMA_RE.fullmatch(schema_version):
        raise _decision_error(
            context,
            "schema_version must look like food-data-menustat-source-decision.vN",
        )
    catalog_ref = _require_string(data, "catalog_ref", context)
    if expected_catalog_ref is not None and catalog_ref != expected_catalog_ref:
        raise _decision_error(context, f"catalog_ref must be {expected_catalog_ref!r}")
    onboarding_ref = _require_string(data, "onboarding_ref", context)
    if expected_onboarding_ref is not None and onboarding_ref != expected_onboarding_ref:
        raise _decision_error(context, f"onboarding_ref must be {expected_onboarding_ref!r}")
    replacement_ref = _require_string(data, "menustat_replacement_ref", context)
    if expected_replacement_ref is not None and replacement_ref != expected_replacement_ref:
        raise _decision_error(
            context, f"menustat_replacement_ref must be {expected_replacement_ref!r}"
        )

    legacy_source = _require_string(data, "legacy_source", context)
    if legacy_source != MENUSTAT_SOURCE:
        raise _decision_error(context, "legacy_source must be menustat")
    _require_safety_flags(data, context)

    archival_policy = _parse_archival_policy(
        data.get("menustat_archival_policy"),
        catalog,
        f"{context}.menustat_archival_policy",
    )
    preferred_research_lane = _require_string(data, "preferred_research_lane", context)
    if preferred_research_lane != _CHAIN_PUBLIC_SOURCE:
        raise _decision_error(
            context, "preferred_research_lane must be chain_public_nutrition_pages"
        )
    budget_api_review = _parse_budget_api_review(
        data.get("budget_api_review"),
        f"{context}.budget_api_review",
    )
    public_web_policy = _parse_public_web_policy(
        data.get("public_web_evidence_policy"),
        f"{context}.public_web_evidence_policy",
    )

    rows = data.get("source_decisions")
    if not isinstance(rows, list):
        raise _decision_error(context, "source_decisions must be a list")
    source_decisions = tuple(
        _parse_source_decision(row, f"{context}.source_decisions[{index}]")
        for index, row in enumerate(rows)
    )
    source_order = tuple(decision.source for decision in source_decisions)
    if source_order != _EXPECTED_SOURCE_ORDER:
        raise _decision_error(
            context,
            "source_decisions must be exactly: " + ", ".join(_EXPECTED_SOURCE_ORDER),
        )
    _validate_against_pr9(source_decisions, replacement, context)

    final_gate_decision = _require_string(data, "final_gate_decision", context)
    if final_gate_decision != FINAL_GATE_DECISION:
        raise _decision_error(context, f"final_gate_decision must be {FINAL_GATE_DECISION}")

    return MenuStatSourceDecision(
        schema_version=schema_version,
        generated_on=_parse_date(_require_string(data, "generated_on", context), context),
        catalog_ref=catalog_ref,
        onboarding_ref=onboarding_ref,
        menustat_replacement_ref=replacement_ref,
        legacy_source=legacy_source,
        menustat_archival_policy=archival_policy,
        preferred_research_lane=preferred_research_lane,
        budget_api_review=budget_api_review,
        public_web_evidence_policy=public_web_policy,
        source_decisions=source_decisions,
        final_gate_decision=final_gate_decision,
        notes=_require_string(data, "notes", context),
    )


def load_menustat_source_decision(
    decision_path: Path | str,
    *,
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    replacement: MenuStatReplacementDecision,
    expected_catalog_ref: str | None = None,
    expected_onboarding_ref: str | None = None,
    expected_replacement_ref: str | None = None,
) -> MenuStatSourceDecision:
    """Load and validate a PR10 MenuStat source-decision JSON artifact."""
    path = Path(decision_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MenuStatSourceDecisionError(
            f"Cannot read MenuStat source decision gate {path}: {exc}"
        ) from exc
    return parse_menustat_source_decision(
        payload,
        catalog=catalog,
        onboarding=onboarding,
        replacement=replacement,
        expected_catalog_ref=expected_catalog_ref,
        expected_onboarding_ref=expected_onboarding_ref,
        expected_replacement_ref=expected_replacement_ref,
        context=str(path),
    )


def build_menustat_source_decision_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    replacement_path: Path | str,
    decision_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR10 source-decision gate."""
    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    expected_replacement_ref = _relative_repo_path(replacement_path)
    report: dict[str, object] = {
        "success": False,
        "dry_run": True,
        "legacy_source": MENUSTAT_SOURCE,
        "menustat_archival_reference_only": True,
        "menustat_validation_required_before_use": True,
        "preferred_research_lane": _CHAIN_PUBLIC_SOURCE,
        "budget_api_review_source": "edamam_food_database",
        "budget_api_review_max_usd_per_month": 20,
        "public_web_evidence_policy": "manual_evidence_only_legal_review_required",
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "network_allowed": False,
        "db_writes_allowed": False,
        "api_calls_allowed": False,
        "source_download_allowed": False,
        "scraping_allowed": False,
        "file_only": True,
        "final_gate_decision": FINAL_GATE_DECISION,
        "validation_errors": [],
    }
    try:
        catalog = load_source_catalog(catalog_path)
        onboarding = load_source_onboarding(
            onboarding_path,
            catalog=catalog,
            expected_catalog_ref=expected_catalog_ref,
        )
        replacement = load_menustat_replacement_decision(
            replacement_path,
            catalog=catalog,
            onboarding=onboarding,
            expected_catalog_ref=expected_catalog_ref,
            expected_onboarding_ref=expected_onboarding_ref,
        )
        decision = load_menustat_source_decision(
            decision_path,
            catalog=catalog,
            onboarding=onboarding,
            replacement=replacement,
            expected_catalog_ref=expected_catalog_ref,
            expected_onboarding_ref=expected_onboarding_ref,
            expected_replacement_ref=expected_replacement_ref,
        )
    except (
        MenuStatSourceDecisionError,
        MenuStatReplacementError,
        SourceCatalogError,
        SourceOnboardingError,
    ) as exc:
        report["validation_errors"] = [str(exc)]
        return report

    report.update(
        {
            "success": True,
            "catalog_ref": decision.catalog_ref,
            "onboarding_ref": decision.onboarding_ref,
            "menustat_replacement_ref": decision.menustat_replacement_ref,
            "project_source_decisions": {
                source_decision.source: source_decision.project_source_decision
                for source_decision in decision.source_decisions
            },
            "research_lane_decisions": {
                source_decision.source: source_decision.research_lane_decision
                for source_decision in decision.source_decisions
            },
            "budget_api_review_source": decision.budget_api_review.source,
            "budget_api_review_max_usd_per_month": (
                decision.budget_api_review.starter_budget_usd_per_month
            ),
            "public_web_evidence_policy": decision.public_web_evidence_policy.policy_decision,
        }
    )
    return report
