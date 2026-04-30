"""
Deterministic food coverage/source-gap audit gate.

RU: Файловая проверка PR11: достаточно ли USDA + OFF для продуктовой базы и
какие gaps остаются до ресторанных меню, рецептов и preference planning.
EN: File-only PR11 audit: whether USDA + OFF cover the product DB baseline and
which gaps remain for restaurant menus, recipes, and preference planning.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from core.food_sources.source_catalog import (
    SourceCatalog,
    SourceCatalogEntry,
    SourceCatalogError,
    load_source_catalog,
)
from core.food_sources.source_onboarding import (
    SourceOnboarding,
    SourceOnboardingEntry,
    SourceOnboardingError,
    load_source_onboarding,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AUDIT_SCHEMA_RE = re.compile(r"^food-data-coverage-source-gap-audit\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

REQUIRED_COVERAGE_DOMAINS = (
    "generic_food_composition",
    "branded_barcode_products",
    "restaurant_chain_menus",
    "recipe_dish_corpora",
    "preference_menu_planning",
    "regional_local_products",
    "user_manual_evidence",
)

FINAL_GATE_DECISION = "coverage_gap_audit_complete_no_ingest"
NEXT_RECOMMENDED_LANE = "chain_public_nutrition_pages_governance_or_recipe_corpus_governance"

_SAFETY_FLAG_TEMPLATE: dict[str, bool] = {
    "runtime_cutover": False,
    "digitalocean_postgres_load": False,
    "bulk_ingest": False,
    "network_allowed": False,
    "db_writes_allowed": False,
    "api_calls_allowed": False,
    "source_download_allowed": False,
    "scraping_allowed": False,
    "paid_source_use_allowed": False,
    "file_only": True,
}

_AUDIT_KEYS = frozenset(
    {
        "schema_version",
        "generated_on",
        "catalog_ref",
        "onboarding_ref",
        "pr10_landed_pr",
        "coverage_domains",
        "source_gap_decisions",
        "next_recommended_lane",
        "runtime_cutover",
        "digitalocean_postgres_load",
        "bulk_ingest",
        "network_allowed",
        "db_writes_allowed",
        "api_calls_allowed",
        "source_download_allowed",
        "scraping_allowed",
        "paid_source_use_allowed",
        "file_only",
        "final_gate_decision",
        "notes",
    }
)

_DOMAIN_KEYS = frozenset(
    {
        "domain",
        "coverage_decision",
        "primary_sources",
        "auxiliary_sources",
        "gap_status",
        "authority_decision",
        "approved_ingest",
        "approved_runtime_authority",
        "next_action",
        "notes",
    }
)

_GAP_DECISION_KEYS = frozenset(
    {
        "source",
        "decision",
        "source_family",
        "allowed_role",
        "approved_ingest",
        "approved_runtime_authority",
        "api_calls_allowed",
        "scraping_allowed",
        "paid_source_use_allowed",
        "blocking_reasons",
        "notes",
    }
)

_EXPECTED_DOMAIN_DECISIONS: dict[str, dict[str, object]] = {
    "generic_food_composition": {
        "coverage_decision": "adequate_baseline",
        "gap_status": "baseline_covered",
        "authority_decision": "usda_first",
        "next_action": "no_new_source_before_usda_schema_review",
    },
    "branded_barcode_products": {
        "coverage_decision": "adequate_with_auxiliary",
        "gap_status": "covered_with_schema_review_needed",
        "authority_decision": "usda_branded_primary_off_auxiliary",
        "next_action": "off_schema_postgres_review_before_any_new_product_source",
    },
    "restaurant_chain_menus": {
        "coverage_decision": "unresolved_gap",
        "gap_status": "not_covered_by_usda_or_off",
        "authority_decision": "not_approved",
        "next_action": "chain_public_nutrition_pages_governance",
    },
    "recipe_dish_corpora": {
        "coverage_decision": "unresolved_gap",
        "gap_status": "not_covered_by_food_nutrient_sources",
        "authority_decision": "not_approved",
        "next_action": "recipe_corpus_governance",
    },
    "preference_menu_planning": {
        "coverage_decision": "requires_dish_mapping",
        "gap_status": "planner_gap_not_source_authority",
        "authority_decision": "not_approved",
        "next_action": "preference_recipe_mapping_contract",
    },
    "regional_local_products": {
        "coverage_decision": "deferred_unresolved",
        "gap_status": "locale_gap_unresolved",
        "authority_decision": "not_approved",
        "next_action": "regional_catalog_identity_license_review",
    },
    "user_manual_evidence": {
        "coverage_decision": "internal_evidence_only",
        "gap_status": "manual_evidence_not_dataset_authority",
        "authority_decision": "not_approved",
        "next_action": "manual_evidence_policy_only",
    },
}

_EXPECTED_SOURCE_GAP_DECISIONS: dict[str, dict[str, object]] = {
    "usda_foundation": {
        "decision": "core_authority_for_generic_composition",
        "source_family": "food_composition",
        "allowed_role": "primary_product_food_baseline",
    },
    "usda_branded": {
        "decision": "primary_branded_barcode_source",
        "source_family": "barcode_branded",
        "allowed_role": "primary_product_food_baseline",
    },
    "usda_fndds": {
        "decision": "supporting_food_composition_source",
        "source_family": "food_composition",
        "allowed_role": "supporting_food_composition",
    },
    "open_food_facts": {
        "decision": "auxiliary_barcode_branded_source",
        "source_family": "barcode_branded",
        "allowed_role": "auxiliary_product_food_source",
    },
    "menustat": {
        "decision": "archival_reference_only",
        "source_family": "restaurant_menu",
        "allowed_role": "historical_schema_reference",
    },
    "chain_public_nutrition_pages": {
        "decision": "preferred_research_lane_blocked",
        "source_family": "restaurant_menu",
        "allowed_role": "manual_evidence_governance_candidate",
    },
    "edamam_food_database": {
        "decision": "adjacent_recipe_food_db_review_only",
        "source_family": "recipe_corpus",
        "allowed_role": "under_20_review_candidate_only",
    },
    "spoonacular": {
        "decision": "deferred_recipe_experiments_only",
        "source_family": "recipe_corpus",
        "allowed_role": "deferred_experiment_candidate_only",
    },
    "nutritionix": {
        "decision": "deferred_contract_review",
        "source_family": "restaurant_menu",
        "allowed_role": "deferred_contract_candidate_only",
    },
    "fatsecret_platform": {
        "decision": "not_project_source",
        "source_family": "commercial_api",
        "allowed_role": "rejected_for_project_use",
    },
    "regional_catalogs": {
        "decision": "deferred_unresolved",
        "source_family": "regional_catalog",
        "allowed_role": "identity_license_review_candidate",
    },
    "jptn_food_facts": {
        "decision": "blocked_unresolved",
        "source_family": "unresolved",
        "allowed_role": "blocked_until_identity_license_verified",
    },
}

_KNOWN_SOURCE_IDS = frozenset(_EXPECTED_SOURCE_GAP_DECISIONS)


class SourceGapAuditError(ValueError):
    """Raised when the PR11 coverage/source-gap audit artifact is invalid."""


@dataclass(frozen=True)
class CoverageDomainDecision:
    """One PR11 product coverage-domain decision."""

    domain: str
    coverage_decision: str
    primary_sources: tuple[str, ...]
    auxiliary_sources: tuple[str, ...]
    gap_status: str
    authority_decision: str
    approved_ingest: bool
    approved_runtime_authority: bool
    next_action: str
    notes: str


@dataclass(frozen=True)
class SourceGapDecision:
    """One source-level gap decision row."""

    source: str
    decision: str
    source_family: str
    allowed_role: str
    approved_ingest: bool
    approved_runtime_authority: bool
    api_calls_allowed: bool
    scraping_allowed: bool
    paid_source_use_allowed: bool
    blocking_reasons: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class SourceGapAudit:
    """Validated PR11 source-gap audit artifact."""

    schema_version: str
    generated_on: date
    catalog_ref: str
    onboarding_ref: str
    pr10_landed_pr: int
    coverage_domains: tuple[CoverageDomainDecision, ...]
    source_gap_decisions: tuple[SourceGapDecision, ...]
    next_recommended_lane: str
    final_gate_decision: str
    notes: str


def _audit_error(context: str, detail: str) -> SourceGapAuditError:
    return SourceGapAuditError(f"Invalid food source-gap audit {context}: {detail}")


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _audit_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _audit_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _audit_error(context, f"missing non-empty string '{key}'")
    return value.strip()


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _audit_error(context, f"'{key}' must be a boolean")
    return value


def _require_int(data: dict[str, object], key: str, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _audit_error(context, f"'{key}' must be an integer")
    return value


def _require_string_tuple(
    data: dict[str, object],
    key: str,
    context: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list):
        raise _audit_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _audit_error(context, f"'{key}[{index}]' must be a non-empty string")
        normalized = item.strip()
        if normalized in seen:
            raise _audit_error(context, f"'{key}' contains duplicate value {normalized!r}")
        seen.add(normalized)
        items.append(normalized)
    if not items and not allow_empty:
        raise _audit_error(context, f"'{key}' must not be empty")
    return tuple(items)


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _audit_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _audit_error(context, "generated_on must use YYYY-MM-DD") from exc


def _relative_repo_path(path: Path | str) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _catalog_by_source(catalog: SourceCatalog) -> dict[str, SourceCatalogEntry]:
    return {entry.source: entry for entry in catalog.sources}


def _onboarding_by_source(onboarding: SourceOnboarding) -> dict[str, SourceOnboardingEntry]:
    return {entry.source: entry for entry in onboarding.sources}


def _require_safety_flags(data: dict[str, object], context: str) -> None:
    safety_flags = {key: _require_bool(data, key, context) for key in _SAFETY_FLAG_TEMPLATE}
    if safety_flags != _SAFETY_FLAG_TEMPLATE:
        raise _audit_error(
            context,
            "runtime_cutover, digitalocean_postgres_load, bulk_ingest, network_allowed, "
            "db_writes_allowed, api_calls_allowed, source_download_allowed, scraping_allowed, "
            "and paid_source_use_allowed must be false; file_only must be true",
        )


def _validate_catalog_and_onboarding(catalog: SourceCatalog, onboarding: SourceOnboarding) -> None:
    catalog_entries = _catalog_by_source(catalog)
    onboarding_entries = _onboarding_by_source(onboarding)

    required_catalog = {
        "usda_foundation",
        "usda_branded",
        "usda_fndds",
        "open_food_facts",
        "menustat",
        "chain_public_nutrition_pages",
        "edamam_food_database",
        "spoonacular",
        "nutritionix",
        "fatsecret_platform",
        "regional_catalogs",
        "jptn_food_facts",
    }
    missing = sorted(required_catalog - set(catalog_entries))
    if missing:
        raise _audit_error("<catalog>", f"missing required source(s): {', '.join(missing)}")
    missing_onboarding = sorted(required_catalog - set(onboarding_entries))
    if missing_onboarding:
        raise _audit_error(
            "<onboarding>", f"missing required source(s): {', '.join(missing_onboarding)}"
        )

    for source in ("usda_foundation", "usda_branded", "usda_fndds", "open_food_facts"):
        entry = catalog_entries[source]
        if entry.source_classification != "current" or not entry.active_update_source:
            raise _audit_error("<catalog>", f"{source} must remain a current update source")

    off_onboarding = onboarding_entries["open_food_facts"]
    if off_onboarding.provider_policy_ref != "docs/legal/ODbL_COMPLIANCE.md":
        raise _audit_error("<onboarding>", "Open Food Facts must retain ODbL policy ref")

    menustat = catalog_entries["menustat"]
    if (
        menustat.source_classification != "legacy_static"
        or menustat.active_update_source
        or not menustat.replacement_required
    ):
        raise _audit_error(
            "<catalog>", "MenuStat must remain legacy_static and replacement_required"
        )

    fatsecret = catalog_entries["fatsecret_platform"]
    if fatsecret.source_classification != "commercial_contract":
        raise _audit_error("<catalog>", "FatSecret must not become a current project source")


def _parse_domain_decision(value: object, context: str) -> CoverageDomainDecision:
    data = _require_mapping(value, context)
    unexpected_keys = sorted(set(data) - _DOMAIN_KEYS)
    if unexpected_keys:
        raise _audit_error(context, f"unexpected domain keys: {', '.join(unexpected_keys)}")
    decision = CoverageDomainDecision(
        domain=_require_string(data, "domain", context),
        coverage_decision=_require_string(data, "coverage_decision", context),
        primary_sources=_require_string_tuple(data, "primary_sources", context, allow_empty=True),
        auxiliary_sources=_require_string_tuple(
            data,
            "auxiliary_sources",
            context,
            allow_empty=True,
        ),
        gap_status=_require_string(data, "gap_status", context),
        authority_decision=_require_string(data, "authority_decision", context),
        approved_ingest=_require_bool(data, "approved_ingest", context),
        approved_runtime_authority=_require_bool(data, "approved_runtime_authority", context),
        next_action=_require_string(data, "next_action", context),
        notes=_require_string(data, "notes", context),
    )
    expected = _EXPECTED_DOMAIN_DECISIONS.get(decision.domain)
    if expected is None:
        raise _audit_error(context, f"unknown coverage domain: {decision.domain}")
    mismatches = [
        key for key, expected_value in expected.items() if getattr(decision, key) != expected_value
    ]
    if mismatches:
        raise _audit_error(context, f"{decision.domain} decision mismatch: {', '.join(mismatches)}")
    if decision.approved_ingest or decision.approved_runtime_authority:
        raise _audit_error(context, f"{decision.domain} cannot approve ingest or runtime authority")
    _validate_domain_source_ids(decision, context)
    return decision


def _validate_domain_source_ids(decision: CoverageDomainDecision, context: str) -> None:
    for field_name, source_ids in (
        ("primary_sources", decision.primary_sources),
        ("auxiliary_sources", decision.auxiliary_sources),
    ):
        unknown_sources = sorted(set(source_ids) - _KNOWN_SOURCE_IDS)
        if unknown_sources:
            raise _audit_error(
                context,
                f"{decision.domain} {field_name} contains unknown source id(s): "
                f"{', '.join(unknown_sources)}",
            )


def _parse_source_gap_decision(value: object, context: str) -> SourceGapDecision:
    data = _require_mapping(value, context)
    unexpected_keys = sorted(set(data) - _GAP_DECISION_KEYS)
    if unexpected_keys:
        raise _audit_error(context, f"unexpected source gap keys: {', '.join(unexpected_keys)}")
    decision = SourceGapDecision(
        source=_require_string(data, "source", context),
        decision=_require_string(data, "decision", context),
        source_family=_require_string(data, "source_family", context),
        allowed_role=_require_string(data, "allowed_role", context),
        approved_ingest=_require_bool(data, "approved_ingest", context),
        approved_runtime_authority=_require_bool(data, "approved_runtime_authority", context),
        api_calls_allowed=_require_bool(data, "api_calls_allowed", context),
        scraping_allowed=_require_bool(data, "scraping_allowed", context),
        paid_source_use_allowed=_require_bool(data, "paid_source_use_allowed", context),
        blocking_reasons=_require_string_tuple(data, "blocking_reasons", context),
        notes=_require_string(data, "notes", context),
    )
    expected = _EXPECTED_SOURCE_GAP_DECISIONS.get(decision.source)
    if expected is None:
        raise _audit_error(context, f"unknown source gap decision: {decision.source}")
    mismatches = [
        key for key, expected_value in expected.items() if getattr(decision, key) != expected_value
    ]
    if mismatches:
        raise _audit_error(
            context, f"{decision.source} source-gap mismatch: {', '.join(mismatches)}"
        )
    if (
        decision.approved_ingest
        or decision.approved_runtime_authority
        or decision.api_calls_allowed
        or decision.scraping_allowed
        or decision.paid_source_use_allowed
    ):
        raise _audit_error(
            context,
            f"{decision.source} cannot approve ingest, runtime authority, API calls, scraping, or paid source use",
        )
    return decision


def parse_source_gap_audit(
    payload: object,
    *,
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    expected_catalog_ref: str | None = None,
    expected_onboarding_ref: str | None = None,
    context: str = "<source-gap-audit>",
) -> SourceGapAudit:
    """Parse and validate the PR11 food coverage/source-gap audit artifact."""

    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _AUDIT_KEYS)
    if unexpected_keys:
        raise _audit_error(context, f"unexpected keys: {', '.join(unexpected_keys)}")
    schema_version = _require_string(data, "schema_version", context)
    if not _AUDIT_SCHEMA_RE.fullmatch(schema_version):
        raise _audit_error(
            context,
            "schema_version must look like food-data-coverage-source-gap-audit.vN",
        )
    catalog_ref = _require_string(data, "catalog_ref", context)
    if expected_catalog_ref is not None and catalog_ref != expected_catalog_ref:
        raise _audit_error(context, f"catalog_ref must be {expected_catalog_ref!r}")
    onboarding_ref = _require_string(data, "onboarding_ref", context)
    if expected_onboarding_ref is not None and onboarding_ref != expected_onboarding_ref:
        raise _audit_error(context, f"onboarding_ref must be {expected_onboarding_ref!r}")
    pr10_landed_pr = _require_int(data, "pr10_landed_pr", context)
    if pr10_landed_pr != 1597:
        raise _audit_error(context, "pr10_landed_pr must be 1597")
    _require_safety_flags(data, context)
    _validate_catalog_and_onboarding(catalog, onboarding)

    rows = data.get("coverage_domains")
    if not isinstance(rows, list):
        raise _audit_error(context, "coverage_domains must be a list")
    coverage_domains = tuple(
        _parse_domain_decision(row, f"{context}.coverage_domains[{index}]")
        for index, row in enumerate(rows)
    )
    domain_order = tuple(decision.domain for decision in coverage_domains)
    if domain_order != REQUIRED_COVERAGE_DOMAINS:
        raise _audit_error(
            context,
            "coverage_domains must be exactly: " + ", ".join(REQUIRED_COVERAGE_DOMAINS),
        )

    source_rows = data.get("source_gap_decisions")
    if not isinstance(source_rows, list):
        raise _audit_error(context, "source_gap_decisions must be a list")
    source_gap_decisions = tuple(
        _parse_source_gap_decision(row, f"{context}.source_gap_decisions[{index}]")
        for index, row in enumerate(source_rows)
    )
    source_order = tuple(decision.source for decision in source_gap_decisions)
    expected_source_order = tuple(_EXPECTED_SOURCE_GAP_DECISIONS)
    if source_order != expected_source_order:
        raise _audit_error(
            context,
            "source_gap_decisions must be exactly: " + ", ".join(expected_source_order),
        )

    next_recommended_lane = _require_string(data, "next_recommended_lane", context)
    if next_recommended_lane != NEXT_RECOMMENDED_LANE:
        raise _audit_error(context, f"next_recommended_lane must be {NEXT_RECOMMENDED_LANE}")
    final_gate_decision = _require_string(data, "final_gate_decision", context)
    if final_gate_decision != FINAL_GATE_DECISION:
        raise _audit_error(context, f"final_gate_decision must be {FINAL_GATE_DECISION}")

    return SourceGapAudit(
        schema_version=schema_version,
        generated_on=_parse_date(_require_string(data, "generated_on", context), context),
        catalog_ref=catalog_ref,
        onboarding_ref=onboarding_ref,
        pr10_landed_pr=pr10_landed_pr,
        coverage_domains=coverage_domains,
        source_gap_decisions=source_gap_decisions,
        next_recommended_lane=next_recommended_lane,
        final_gate_decision=final_gate_decision,
        notes=_require_string(data, "notes", context),
    )


def load_source_gap_audit(
    coverage_path: Path | str,
    *,
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    expected_catalog_ref: str | None = None,
    expected_onboarding_ref: str | None = None,
) -> SourceGapAudit:
    """Load and validate a PR11 coverage/source-gap audit JSON artifact."""

    path = Path(coverage_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SourceGapAuditError(f"Cannot read source-gap audit {path}: {exc}") from exc
    return parse_source_gap_audit(
        payload,
        catalog=catalog,
        onboarding=onboarding,
        expected_catalog_ref=expected_catalog_ref,
        expected_onboarding_ref=expected_onboarding_ref,
        context=str(path),
    )


def build_source_gap_audit_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    coverage_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR11 source-gap audit gate."""

    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    report: dict[str, object] = {
        "success": False,
        "dry_run": True,
        "coverage_domains": list(REQUIRED_COVERAGE_DOMAINS),
        "source_gap_decisions": {},
        "next_recommended_lane": NEXT_RECOMMENDED_LANE,
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "network_allowed": False,
        "db_writes_allowed": False,
        "api_calls_allowed": False,
        "source_download_allowed": False,
        "scraping_allowed": False,
        "paid_source_use_allowed": False,
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
        audit = load_source_gap_audit(
            coverage_path,
            catalog=catalog,
            onboarding=onboarding,
            expected_catalog_ref=expected_catalog_ref,
            expected_onboarding_ref=expected_onboarding_ref,
        )
    except (SourceGapAuditError, SourceCatalogError, SourceOnboardingError) as exc:
        report["validation_errors"] = [str(exc)]
        return report

    report.update(
        {
            "success": True,
            "catalog_ref": audit.catalog_ref,
            "onboarding_ref": audit.onboarding_ref,
            "pr10_landed_pr": audit.pr10_landed_pr,
            "coverage_domain_decisions": {
                domain.domain: domain.coverage_decision for domain in audit.coverage_domains
            },
            "coverage_gap_status": {
                domain.domain: domain.gap_status for domain in audit.coverage_domains
            },
            "source_gap_decisions": {
                source.source: source.decision for source in audit.source_gap_decisions
            },
        }
    )
    return report
