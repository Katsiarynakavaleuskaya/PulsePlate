"""
Deterministic PR16 preference recipe mapping closeout gate.

EN: File-only PR16 validation: close PR15 governance and choose the next
food-data lane without approving provider, ingest, or runtime authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from core.food_sources.preference_recipe_mapping import (
    BLOCKED_METHODS as PR15_BLOCKED_METHODS,
    EVIDENCE_POLICY as PR15_EVIDENCE_POLICY,
    EXPECTED_ALLOWED_ROLES as PR15_EXPECTED_ALLOWED_ROLES,
    EXPECTED_PR11_CATALOG_REF,
    EXPECTED_PR11_DOMAIN_SOURCE_REFS,
    EXPECTED_PR11_ONBOARDING_REF,
    EXPECTED_PR11_SOURCE_GAP_BLOCKING_REASONS,
    EXPECTED_PR11_SOURCE_GAP_ORDER,
    EXPECTED_MAPPING_KEYS as PR15_EXPECTED_MAPPING_KEYS,
    FINAL_GATE_DECISION as PR15_FINAL_GATE_DECISION,
    NEXT_RECOMMENDED_LANE as PR15_NEXT_RECOMMENDED_LANE,
    PreferenceRecipeMappingError,
    PreferenceRecipeMappingGovernance,
    SOURCE as PR15_SOURCE,
    SOURCE_CLASSIFICATION as PR15_SOURCE_CLASSIFICATION,
    SOURCE_FAMILY as PR15_SOURCE_FAMILY,
    load_preference_recipe_mapping_governance,
)
from core.food_sources.recipe_dish_corpus import (
    RecipeDishCorpusGovernanceError,
    load_recipe_dish_corpus_governance,
)
from core.food_sources.source_catalog import SourceCatalogError, load_source_catalog
from core.food_sources.source_gap_audit import (
    FINAL_GATE_DECISION as PR11_FINAL_GATE_DECISION,
    NEXT_RECOMMENDED_LANE as PR11_NEXT_RECOMMENDED_LANE,
    REQUIRED_COVERAGE_DOMAINS as PR11_REQUIRED_COVERAGE_DOMAINS,
    SourceGapAudit,
    SourceGapAuditError,
    load_source_gap_audit,
)
from core.food_sources.source_onboarding import SourceOnboardingError, load_source_onboarding

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_RE = re.compile(r"^food-data-preference-recipe-mapping-closeout\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PR15_MERGED_PR = 1747
PR15_REF = "docs/architecture/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_2026-05-13.json"
PR11_REF = "docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json"
PR14_REF = "docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json"
SOURCE = "preference_recipe_mapping_contract_review_closeout"
SOURCE_CLASSIFICATION = "governance_closeout_only"
SOURCE_FAMILY = "food_data_source_governance"
EVIDENCE_POLICY = "external_research_evidence_only_no_source_authority"
FINAL_GATE_DECISION = "preference_mapping_closeout_only_no_ingest"
NEXT_SUBSTANTIVE_LANE = "regional_catalog_identity_license_review"

BLOCKED_METHODS = (
    "scraping",
    "automated_collection",
    "api_call",
    "download",
    "paid_api_use",
    "seller_api_use",
    "partner_api_use",
    "cache_authority",
    "redistribution",
    "runtime_authority",
    "public_dataset_claim",
    "digitalocean_postgres_load",
    "recipe_text_authority",
    "user_preference_text_authority",
    "llm_output_authority",
    "nutrition_authority",
    "provider_integration",
    "product_display",
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
    "paid_source_use_allowed": False,
    "seller_api_use_allowed": False,
    "partner_api_use_allowed": False,
    "cache_authority_allowed": False,
    "redistribution_allowed": False,
    "public_dataset_claim_allowed": False,
    "automation_allowed": False,
    "provider_integration_allowed": False,
    "product_display_allowed": False,
    "nutrition_authority_allowed": False,
    "file_only": True,
}

_GOVERNANCE_KEYS = frozenset(
    {
        "schema_version",
        "generated_on",
        "pr15_ref",
        "pr15_merged_pr",
        "pr15_next_recommended_lane",
        "coverage_ref",
        "recipe_dish_corpus_ref",
        "source",
        "source_classification",
        "source_family",
        "evidence_policy",
        "external_research_evidence_role",
        "blocked_methods",
        "budget_first_policy",
        "deferred_followups",
        "runtime_cutover",
        "digitalocean_postgres_load",
        "bulk_ingest",
        "network_allowed",
        "db_writes_allowed",
        "api_calls_allowed",
        "source_download_allowed",
        "scraping_allowed",
        "paid_source_use_allowed",
        "seller_api_use_allowed",
        "partner_api_use_allowed",
        "cache_authority_allowed",
        "redistribution_allowed",
        "public_dataset_claim_allowed",
        "automation_allowed",
        "provider_integration_allowed",
        "product_display_allowed",
        "nutrition_authority_allowed",
        "file_only",
        "next_substantive_lane",
        "final_gate_decision",
        "notes",
    }
)

_FORBIDDEN_NOTE_PHRASES = (
    "api calls approved",
    "api calls allowed",
    "scraping approved",
    "scraping allowed",
    "download approved",
    "download allowed",
    "paid source approved",
    "paid source allowed",
    "provider approved",
    "provider integration approved",
    "runtime authority approved",
    "runtime authority allowed",
    "nutrition authority approved",
    "nutrition authority allowed",
    "product display approved",
    "product display allowed",
    "source authority approved",
    "source authority allowed",
    "spreadsheet is authority",
    "report is authority",
    "docx is authority",
    "image is authority",
)

_APPROVAL_VERBS = r"approves?|authorizes?|permits?|allows?|grants?|enables?"
_APPROVAL_STATES = r"approved|authorized|permitted|allowed|granted|enabled"
_EXTERNAL_EVIDENCE_TERMS = (
    r"reports?|spreadsheets?|docx|documents?|images?|charts?|artifacts?|research"
)
_BLOCKED_PROVIDER_TERMS = (
    r"edamam|spoonacular|nutritionix|themealdb|mealdb|fatsecret|menustat|"
    r"recipe api|spike api|spike|apify|kitchenhub|pepesto|pricesapi|prices api|"
    r"yandex eda|ozon|wildberries|walmart api|kroger api"
)
_BLOCKED_AUTHORITY_TERMS = (
    rf"{_BLOCKED_PROVIDER_TERMS}|"
    r"paid apis?|paid api use|paid source use|paid providers?|provider snapshots?|provider integration|"
    r"paid provider use|paid plans?|seller apis?|seller api use|partner apis?|partner api use|"
    r"network access|network|"
    r"scrapers?|scraping|api calls?|source downloads?|downloads?|runtime authority|"
    r"cache authority|database writes?|db writes?|redistribution|ingests?|source use|"
    r"automated collection|digitalocean postgres load|public dataset claim|"
    r"recipe text authority|user preference text authority|llm output authority|"
    r"source authority|nutrition authority|product display"
)
_BLOCKED_AUTHORITY_USE_STATES = r"used|relied on|usable|okay|available"
_PR15_MAPPING_CONTRACT_STATUS = "mapping_contract_required_not_approved"
_PR15_PR11_LANDED_PR = 1601
_PR15_PR14_LANDED_PR = 1743
_PR11_PR10_LANDED_PR = 1597
_PR11_DOMAIN_AUTHORITY_DECISIONS = {
    "generic_food_composition": "usda_first",
    "branded_barcode_products": "usda_branded_primary_off_auxiliary",
    "restaurant_chain_menus": "not_approved",
    "recipe_dish_corpora": "not_approved",
    "preference_menu_planning": "not_approved",
    "regional_local_products": "not_approved",
    "user_manual_evidence": "not_approved",
}
_PR11_DOMAIN_DECISIONS = {
    "generic_food_composition": {
        "coverage_decision": "adequate_baseline",
        "gap_status": "baseline_covered",
        "next_action": "no_new_source_before_usda_schema_review",
    },
    "branded_barcode_products": {
        "coverage_decision": "adequate_with_auxiliary",
        "gap_status": "covered_with_schema_review_needed",
        "next_action": "off_schema_postgres_review_before_any_new_product_source",
    },
    "restaurant_chain_menus": {
        "coverage_decision": "unresolved_gap",
        "gap_status": "not_covered_by_usda_or_off",
        "next_action": "chain_public_nutrition_pages_governance",
    },
    "recipe_dish_corpora": {
        "coverage_decision": "unresolved_gap",
        "gap_status": "not_covered_by_food_nutrient_sources",
        "next_action": "recipe_corpus_governance",
    },
    "preference_menu_planning": {
        "coverage_decision": "requires_dish_mapping",
        "gap_status": "planner_gap_not_source_authority",
        "next_action": "preference_recipe_mapping_contract",
    },
    "regional_local_products": {
        "coverage_decision": "deferred_unresolved",
        "gap_status": "locale_gap_unresolved",
        "next_action": "regional_catalog_identity_license_review",
    },
    "user_manual_evidence": {
        "coverage_decision": "internal_evidence_only",
        "gap_status": "manual_evidence_not_dataset_authority",
        "next_action": "manual_evidence_policy_only",
    },
}
_PR11_SOURCE_GAP_DECISIONS = {
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
_REGIONAL_DOMAIN_EXPECTED = {
    "coverage_decision": "deferred_unresolved",
    "primary_sources": (),
    "auxiliary_sources": ("regional_catalogs",),
    "gap_status": "locale_gap_unresolved",
    "authority_decision": "not_approved",
}
_REGIONAL_SOURCE_BLOCKING_REASONS = (
    "Locale-specific source identity, license, language, unit, schema, and redistribution terms are missing.",
)
_FORBIDDEN_NOTE_PATTERNS = (
    re.compile(
        rf"\b(?:{_BLOCKED_PROVIDER_TERMS})\b"
        rf"(?:\W+\w+){{0,3}}\W+\b(?:is|are|as|become|becomes|serve as|serves as|treated as)\b"
        rf"\W+\b(?:source|nutrition|runtime|cache)?\s*authority\b"
    ),
    re.compile(rf"\b(?:{_EXTERNAL_EVIDENCE_TERMS})\b(?:\W+\w+){{0,8}}\W+\b(?:{_APPROVAL_VERBS})\b"),
    re.compile(
        rf"\b(?:{_EXTERNAL_EVIDENCE_TERMS})\b"
        rf"(?:\W+\b(?:is|are|be|been|being)\b)?\W+\b(?:{_APPROVAL_STATES})\b"
    ),
    re.compile(rf"\b(?:{_APPROVAL_VERBS})\b(?:\W+\w+){{0,8}}\W+\b(?:{_EXTERNAL_EVIDENCE_TERMS})\b"),
    re.compile(
        rf"\b(?:{_BLOCKED_AUTHORITY_TERMS})\b"
        rf"(?:\W+\b(?:is|are|be|been|being)\b)?\W+\b(?:{_APPROVAL_STATES})\b"
    ),
    re.compile(rf"\b(?:{_APPROVAL_VERBS})\b\W+\b(?:{_BLOCKED_AUTHORITY_TERMS})\b"),
    re.compile(
        rf"\b(?:{_BLOCKED_AUTHORITY_TERMS}|{_EXTERNAL_EVIDENCE_TERMS})\b"
        rf"(?:\W+\w+){{0,3}}\W+\b(?:is|are|as|become|becomes|serve as|serves as|treated as)\b"
        rf"\W+\b(?:source|nutrition|runtime|cache)?\s*authority\b"
    ),
    re.compile(
        rf"\b(?:{_BLOCKED_AUTHORITY_TERMS})\b" rf"(?:\W+\w+){{0,3}}\W+\b(?:may|can)\s+be\s+used\b"
    ),
    re.compile(
        rf"\b(?:{_BLOCKED_AUTHORITY_TERMS})\b"
        rf"(?:\W+\w+){{0,3}}\W+\b(?:may|can)\s+be\s+(?:{_BLOCKED_AUTHORITY_USE_STATES})\b"
    ),
    re.compile(
        rf"\b(?:{_BLOCKED_AUTHORITY_TERMS})\b"
        rf"(?:\W+\b(?:is|are|be|been|being)\b)?\W+\b(?:{_BLOCKED_AUTHORITY_USE_STATES})\b"
    ),
)


@dataclass(frozen=True)
class PreferenceMappingCloseoutGovernance:
    """Validated PR16 preference mapping closeout artifact."""

    schema_version: str
    generated_on: date
    pr15_ref: str
    pr15_merged_pr: int
    pr15_next_recommended_lane: str
    coverage_ref: str
    recipe_dish_corpus_ref: str
    source: str
    source_classification: str
    source_family: str
    evidence_policy: str
    external_research_evidence_role: str
    blocked_methods: tuple[str, ...]
    budget_first_policy: str
    deferred_followups: tuple[str, ...]
    next_substantive_lane: str
    final_gate_decision: str
    notes: str


class PreferenceMappingCloseoutError(ValueError):
    """Raised when the PR16 closeout artifact is invalid."""


def _closeout_error(context: str, detail: str) -> PreferenceMappingCloseoutError:
    return PreferenceMappingCloseoutError(
        f"Invalid preference mapping closeout governance {context}: {detail}"
    )


def _relative_repo_path(path: Path | str) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _closeout_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _closeout_error(context, "all keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _closeout_error(context, f"{key} must be a non-empty string")
    return value


def _require_int(data: dict[str, object], key: str, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _closeout_error(context, f"{key} must be an integer")
    return value


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _closeout_error(context, f"{key} must be a boolean")
    return value


def _require_string_tuple(
    data: dict[str, object],
    key: str,
    context: str,
    *,
    expected: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise _closeout_error(context, f"{key} must be a list of strings")
    result = tuple(value)
    if expected is not None and result != expected:
        raise _closeout_error(context, f"{key} must be exactly: {', '.join(expected)}")
    return result


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _closeout_error(context, "generated_on must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _closeout_error(context, "generated_on must be a valid calendar date") from exc


def _require_safe_notes(value: str, context: str) -> str:
    normalized = re.sub(r"[\s_\-/;:,.()[\]{}]+", " ", value.lower()).strip()
    for phrase in _FORBIDDEN_NOTE_PHRASES:
        for match in re.finditer(re.escape(phrase), normalized):
            if not _is_negated_approval_match(phrase, normalized, match.start()):
                raise _closeout_error(context, "notes must not approve blocked source authority")
    for pattern in _FORBIDDEN_NOTE_PATTERNS:
        for match in pattern.finditer(normalized):
            if not _is_negated_approval_match(match.group(0), normalized, match.start()):
                raise _closeout_error(context, "notes must not approve blocked source authority")
    return value


def _is_negated_approval_match(text: str, normalized: str, start: int) -> bool:
    text = text.strip()
    prefix = normalized[max(0, start - 16) : start]
    window = normalized[max(0, start - 32) : start + len(text)].strip()
    return bool(
        re.search(
            rf"\b(?:do|does|did|must|may|can|should|is|are)?\s*not\s+(?:{_APPROVAL_VERBS})\b",
            text,
        )
        or (
            re.match(rf"\b(?:{_APPROVAL_VERBS})\b", text) is not None
            and re.search(r"\bnot\W+$", prefix) is not None
        )
        or re.search(r"(?:^|\W)no\W+$", prefix)
        or re.search(r"\bno\b(?:\W+\w+){0,4}\W+\b(?:or|and)\W+$", prefix)
        or re.search(
            r"\b(?:do|does|did|must|may|can|should|is|are)?\s*not\b"
            r"(?:\W+\w+){0,4}\W+\b(?:become|becomes|serve as|serves as|treated as)\b",
            window,
        )
        or re.search(
            r"\b(?:do|does|did|must|may|can|should|is|are)?\s*not\b"
            r"(?:\W+\w+){0,4}\W+\b(?:source|nutrition|runtime|cache)?\s*authority\b",
            window,
        )
    )


def _require_safety_flags(data: dict[str, object], context: str) -> None:
    for key, expected_value in _SAFETY_FLAG_TEMPLATE.items():
        value = _require_bool(data, key, context)
        if value is not expected_value:
            if expected_value:
                raise _closeout_error(context, f"{key} must be true")
            raise _closeout_error(context, f"{key} flags must be false")


def _require_budget_first_policy(value: str, context: str) -> str:
    if "USDA + Open Food Facts remain the canonical" not in value:
        raise _closeout_error(
            context,
            "budget_first_policy must preserve USDA + Open Food Facts as canonical baseline",
        )
    _require_safe_notes(value, context)
    return value


def _require_pr15_handoff(
    preference_mapping: PreferenceRecipeMappingGovernance,
    context: str,
) -> None:
    if preference_mapping.coverage_ref != PR11_REF:
        raise _closeout_error(context, f"PR15 coverage_ref must be {PR11_REF}")
    if preference_mapping.recipe_dish_corpus_ref != PR14_REF:
        raise _closeout_error(context, f"PR15 recipe_dish_corpus_ref must be {PR14_REF}")
    if preference_mapping.pr11_landed_pr != _PR15_PR11_LANDED_PR:
        raise _closeout_error(context, f"PR15 pr11_landed_pr must be {_PR15_PR11_LANDED_PR}")
    if preference_mapping.pr14_landed_pr != _PR15_PR14_LANDED_PR:
        raise _closeout_error(context, f"PR15 pr14_landed_pr must be {_PR15_PR14_LANDED_PR}")
    if preference_mapping.source != PR15_SOURCE:
        raise _closeout_error(context, f"PR15 source must be {PR15_SOURCE}")
    if preference_mapping.source_classification != PR15_SOURCE_CLASSIFICATION:
        raise _closeout_error(
            context, f"PR15 source_classification must be {PR15_SOURCE_CLASSIFICATION}"
        )
    if preference_mapping.source_family != PR15_SOURCE_FAMILY:
        raise _closeout_error(context, f"PR15 source_family must be {PR15_SOURCE_FAMILY}")
    if preference_mapping.evidence_policy != PR15_EVIDENCE_POLICY:
        raise _closeout_error(context, f"PR15 evidence_policy must be {PR15_EVIDENCE_POLICY}")
    if preference_mapping.blocked_methods != PR15_BLOCKED_METHODS:
        raise _closeout_error(context, "PR15 blocked_methods drifted")
    if preference_mapping.next_recommended_lane != PR15_NEXT_RECOMMENDED_LANE:
        raise _closeout_error(context, "PR15 must recommend preference mapping closeout")
    if preference_mapping.final_gate_decision != PR15_FINAL_GATE_DECISION:
        raise _closeout_error(context, "PR15 final_gate_decision must remain no-ingest")
    mapping_keys = tuple(contract.mapping_key for contract in preference_mapping.mapping_contracts)
    if mapping_keys != PR15_EXPECTED_MAPPING_KEYS:
        raise _closeout_error(
            context,
            "PR15 mapping_contracts must be exactly: " + ", ".join(PR15_EXPECTED_MAPPING_KEYS),
        )
    _require_safe_notes(preference_mapping.notes, context)
    for mapping_contract in preference_mapping.mapping_contracts:
        if mapping_contract.contract_status != _PR15_MAPPING_CONTRACT_STATUS:
            raise _closeout_error(
                context,
                f"PR15 {mapping_contract.mapping_key} contract_status must be "
                f"{_PR15_MAPPING_CONTRACT_STATUS}",
            )
        expected_role = PR15_EXPECTED_ALLOWED_ROLES[mapping_contract.mapping_key]
        if mapping_contract.allowed_role != expected_role:
            raise _closeout_error(
                context, f"PR15 {mapping_contract.mapping_key} allowed_role must be {expected_role}"
            )
        _require_safe_notes(mapping_contract.notes, context)


def _require_regional_handoff(coverage: SourceGapAudit, context: str) -> None:
    if coverage.catalog_ref != EXPECTED_PR11_CATALOG_REF:
        raise _closeout_error(context, f"PR11 catalog_ref must be {EXPECTED_PR11_CATALOG_REF}")
    if coverage.onboarding_ref != EXPECTED_PR11_ONBOARDING_REF:
        raise _closeout_error(
            context, f"PR11 onboarding_ref must be {EXPECTED_PR11_ONBOARDING_REF}"
        )
    if coverage.pr10_landed_pr != _PR11_PR10_LANDED_PR:
        raise _closeout_error(context, f"PR11 pr10_landed_pr must be {_PR11_PR10_LANDED_PR}")
    if coverage.schema_version != "food-data-coverage-source-gap-audit.v1":
        raise _closeout_error(
            context, "PR11 schema_version must be food-data-coverage-source-gap-audit.v1"
        )
    if coverage.next_recommended_lane != PR11_NEXT_RECOMMENDED_LANE:
        raise _closeout_error(
            context, f"PR11 next_recommended_lane must be {PR11_NEXT_RECOMMENDED_LANE}"
        )
    if coverage.final_gate_decision != PR11_FINAL_GATE_DECISION:
        raise _closeout_error(
            context, f"PR11 final_gate_decision must be {PR11_FINAL_GATE_DECISION}"
        )
    _require_safe_notes(coverage.notes, context)
    domain_order = tuple(domain.domain for domain in coverage.coverage_domains)
    if domain_order != PR11_REQUIRED_COVERAGE_DOMAINS:
        raise _closeout_error(
            context,
            "PR11 coverage_domains must be exactly: " + ", ".join(PR11_REQUIRED_COVERAGE_DOMAINS),
        )
    for domain in coverage.coverage_domains:
        expected_refs = EXPECTED_PR11_DOMAIN_SOURCE_REFS.get(domain.domain)
        expected_decisions = _PR11_DOMAIN_DECISIONS.get(domain.domain)
        expected_authority = _PR11_DOMAIN_AUTHORITY_DECISIONS.get(domain.domain)
        if expected_refs is None or expected_decisions is None or expected_authority is None:
            raise _closeout_error(context, f"PR11 unknown coverage domain: {domain.domain}")
        for field_name, expected_value in expected_decisions.items():
            if getattr(domain, field_name) != expected_value:
                raise _closeout_error(
                    context, f"PR11 {domain.domain} {field_name} must be {expected_value}"
                )
        if domain.primary_sources != expected_refs["primary_sources"]:
            raise _closeout_error(
                context, f"PR11 {domain.domain} primary_sources must stay canonical"
            )
        if domain.auxiliary_sources != expected_refs["auxiliary_sources"]:
            raise _closeout_error(
                context, f"PR11 {domain.domain} auxiliary_sources must stay canonical"
            )
        if domain.authority_decision != expected_authority:
            raise _closeout_error(
                context,
                f"PR11 {domain.domain} authority_decision must be {expected_authority}",
            )
        if domain.approved_ingest or domain.approved_runtime_authority:
            raise _closeout_error(context, f"PR11 {domain.domain} must not approve source use")
        _require_safe_notes(domain.notes, context)
    source_order = tuple(source.source for source in coverage.source_gap_decisions)
    if source_order != EXPECTED_PR11_SOURCE_GAP_ORDER:
        raise _closeout_error(
            context,
            "PR11 source_gap_decisions must be exactly: "
            + ", ".join(EXPECTED_PR11_SOURCE_GAP_ORDER),
        )
    for source in coverage.source_gap_decisions:
        expected_blocking_reasons = EXPECTED_PR11_SOURCE_GAP_BLOCKING_REASONS.get(source.source)
        expected_decisions = _PR11_SOURCE_GAP_DECISIONS.get(source.source)
        if expected_blocking_reasons is None or expected_decisions is None:
            raise _closeout_error(context, f"PR11 unknown source decision: {source.source}")
        for field_name, expected_value in expected_decisions.items():
            if getattr(source, field_name) != expected_value:
                raise _closeout_error(
                    context, f"PR11 {source.source} {field_name} must be {expected_value}"
                )
        if source.blocking_reasons != expected_blocking_reasons:
            raise _closeout_error(
                context, f"PR11 {source.source} blocking_reasons must stay canonical"
            )
        if (
            source.approved_ingest
            or source.approved_runtime_authority
            or source.api_calls_allowed
            or source.scraping_allowed
            or source.paid_source_use_allowed
        ):
            raise _closeout_error(context, f"PR11 {source.source} must not approve source use")
        _require_safe_notes(source.notes, context)
    regional_domains = tuple(
        domain for domain in coverage.coverage_domains if domain.domain == "regional_local_products"
    )
    if len(regional_domains) != 1:
        raise _closeout_error(
            context, "PR11 regional_local_products domain must appear exactly once"
        )
    regional_domain = regional_domains[0]
    if regional_domain.next_action != NEXT_SUBSTANTIVE_LANE:
        raise _closeout_error(
            context,
            f"PR11 regional_local_products next_action must be {NEXT_SUBSTANTIVE_LANE}",
        )
    for field_name in _REGIONAL_DOMAIN_EXPECTED:
        regional_expected_value: object = _REGIONAL_DOMAIN_EXPECTED[field_name]
        if getattr(regional_domain, field_name) != regional_expected_value:
            raise _closeout_error(
                context,
                f"PR11 regional_local_products {field_name} must be {regional_expected_value!r}",
            )
    if regional_domain.approved_ingest or regional_domain.approved_runtime_authority:
        raise _closeout_error(context, "PR11 regional_local_products must stay unapproved")
    _require_safe_notes(regional_domain.notes, context)

    regional_sources = tuple(
        source for source in coverage.source_gap_decisions if source.source == "regional_catalogs"
    )
    if len(regional_sources) != 1:
        raise _closeout_error(
            context, "PR11 regional_catalogs source decision must appear exactly once"
        )
    regional_source = regional_sources[0]
    if (
        regional_source.decision != "deferred_unresolved"
        or regional_source.source_family != "regional_catalog"
        or regional_source.allowed_role != "identity_license_review_candidate"
    ):
        raise _closeout_error(context, "PR11 regional_catalogs must remain identity/license review")
    _require_safe_notes(regional_source.notes, context)
    if (
        regional_source.approved_ingest
        or regional_source.approved_runtime_authority
        or regional_source.api_calls_allowed
        or regional_source.scraping_allowed
        or regional_source.paid_source_use_allowed
    ):
        raise _closeout_error(context, "PR11 regional_catalogs must not approve source use")
    if regional_source.blocking_reasons != _REGIONAL_SOURCE_BLOCKING_REASONS:
        raise _closeout_error(
            context,
            "PR11 regional_catalogs blocking_reasons must preserve unresolved identity/license evidence",
        )


def parse_preference_mapping_closeout_governance(
    payload: object,
    *,
    preference_mapping: PreferenceRecipeMappingGovernance,
    coverage: SourceGapAudit,
    expected_pr15_ref: str | None = None,
    expected_coverage_ref: str | None = None,
    expected_recipe_dish_corpus_ref: str | None = None,
    context: str = "<preference-mapping-closeout-governance>",
) -> PreferenceMappingCloseoutGovernance:
    """Parse and validate the PR16 closeout artifact."""

    _require_pr15_handoff(preference_mapping, context)
    _require_regional_handoff(coverage, context)

    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _GOVERNANCE_KEYS)
    if unexpected_keys:
        raise _closeout_error(context, f"unexpected keys: {', '.join(unexpected_keys)}")

    schema_version = _require_string(data, "schema_version", context)
    if not _SCHEMA_RE.fullmatch(schema_version):
        raise _closeout_error(
            context, "schema_version must look like food-data-preference-recipe-mapping-closeout.vN"
        )
    pr15_ref = _require_string(data, "pr15_ref", context)
    expected_pr15 = expected_pr15_ref or PR15_REF
    if pr15_ref != expected_pr15:
        raise _closeout_error(context, f"pr15_ref must be {expected_pr15!r}")
    coverage_ref = _require_string(data, "coverage_ref", context)
    expected_cov = expected_coverage_ref or PR11_REF
    if coverage_ref != expected_cov:
        raise _closeout_error(context, f"coverage_ref must be {expected_cov!r}")
    recipe_dish_corpus_ref = _require_string(data, "recipe_dish_corpus_ref", context)
    expected_recipe = expected_recipe_dish_corpus_ref or PR14_REF
    if recipe_dish_corpus_ref != expected_recipe:
        raise _closeout_error(context, f"recipe_dish_corpus_ref must be {expected_recipe!r}")

    pr15_merged_pr = _require_int(data, "pr15_merged_pr", context)
    if pr15_merged_pr != PR15_MERGED_PR:
        raise _closeout_error(context, f"pr15_merged_pr must be {PR15_MERGED_PR}")
    pr15_next_recommended_lane = _require_string(data, "pr15_next_recommended_lane", context)
    if pr15_next_recommended_lane != PR15_NEXT_RECOMMENDED_LANE:
        raise _closeout_error(
            context, f"pr15_next_recommended_lane must be {PR15_NEXT_RECOMMENDED_LANE}"
        )

    source = _require_string(data, "source", context)
    if source != SOURCE:
        raise _closeout_error(context, f"source must be {SOURCE}")
    source_classification = _require_string(data, "source_classification", context)
    if source_classification != SOURCE_CLASSIFICATION:
        raise _closeout_error(context, f"source_classification must be {SOURCE_CLASSIFICATION}")
    source_family = _require_string(data, "source_family", context)
    if source_family != SOURCE_FAMILY:
        raise _closeout_error(context, f"source_family must be {SOURCE_FAMILY}")
    evidence_policy = _require_string(data, "evidence_policy", context)
    if evidence_policy != EVIDENCE_POLICY:
        raise _closeout_error(context, f"evidence_policy must be {EVIDENCE_POLICY}")
    external_research_evidence_role = _require_string(
        data, "external_research_evidence_role", context
    )
    if external_research_evidence_role != "review_context_only_not_source_authority":
        raise _closeout_error(
            context,
            "external_research_evidence_role must be review_context_only_not_source_authority",
        )
    blocked_methods = _require_string_tuple(
        data, "blocked_methods", context, expected=BLOCKED_METHODS
    )
    budget_first_policy = _require_string(data, "budget_first_policy", context)
    _require_budget_first_policy(budget_first_policy, context)
    deferred_followups = _require_string_tuple(data, "deferred_followups", context)
    required_followups = {
        "paid_restaurant_menu_snapshot_provider_governance",
        "paid_api_or_scraper_provider_contract_review",
        "runtime_postgresql_cutover_packet",
    }
    if not required_followups <= set(deferred_followups):
        raise _closeout_error(
            context, "deferred_followups must include paid/provider/cutover lanes"
        )
    _require_safety_flags(data, context)

    next_substantive_lane = _require_string(data, "next_substantive_lane", context)
    if next_substantive_lane != NEXT_SUBSTANTIVE_LANE:
        raise _closeout_error(context, f"next_substantive_lane must be {NEXT_SUBSTANTIVE_LANE}")
    final_gate_decision = _require_string(data, "final_gate_decision", context)
    if final_gate_decision != FINAL_GATE_DECISION:
        raise _closeout_error(context, f"final_gate_decision must be {FINAL_GATE_DECISION}")

    return PreferenceMappingCloseoutGovernance(
        schema_version=schema_version,
        generated_on=_parse_date(_require_string(data, "generated_on", context), context),
        pr15_ref=pr15_ref,
        pr15_merged_pr=pr15_merged_pr,
        pr15_next_recommended_lane=pr15_next_recommended_lane,
        coverage_ref=coverage_ref,
        recipe_dish_corpus_ref=recipe_dish_corpus_ref,
        source=source,
        source_classification=source_classification,
        source_family=source_family,
        evidence_policy=evidence_policy,
        external_research_evidence_role=external_research_evidence_role,
        blocked_methods=blocked_methods,
        budget_first_policy=budget_first_policy,
        deferred_followups=deferred_followups,
        next_substantive_lane=next_substantive_lane,
        final_gate_decision=final_gate_decision,
        notes=_require_safe_notes(_require_string(data, "notes", context), context),
    )


def load_preference_mapping_closeout_governance(
    governance_path: Path | str,
    *,
    preference_mapping: PreferenceRecipeMappingGovernance,
    coverage: SourceGapAudit,
    expected_pr15_ref: str | None = None,
    expected_coverage_ref: str | None = None,
    expected_recipe_dish_corpus_ref: str | None = None,
) -> PreferenceMappingCloseoutGovernance:
    """Load and validate a PR16 closeout JSON artifact."""

    path = Path(governance_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PreferenceMappingCloseoutError(
            f"Cannot read preference mapping closeout governance {path}: {exc}"
        ) from exc
    return parse_preference_mapping_closeout_governance(
        payload,
        preference_mapping=preference_mapping,
        coverage=coverage,
        expected_pr15_ref=expected_pr15_ref,
        expected_coverage_ref=expected_coverage_ref,
        expected_recipe_dish_corpus_ref=expected_recipe_dish_corpus_ref,
        context=str(path),
    )


def build_preference_mapping_closeout_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    coverage_path: Path | str,
    recipe_dish_corpus_path: Path | str,
    preference_mapping_path: Path | str,
    closeout_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR16 closeout gate."""

    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    expected_coverage_ref = _relative_repo_path(coverage_path)
    expected_recipe_ref = _relative_repo_path(recipe_dish_corpus_path)
    expected_pr15_ref = _relative_repo_path(preference_mapping_path)
    report: dict[str, object] = {
        "success": False,
        "dry_run": True,
        "source": SOURCE,
        "source_classification": SOURCE_CLASSIFICATION,
        "source_family": SOURCE_FAMILY,
        "evidence_policy": EVIDENCE_POLICY,
        "blocked_methods": list(BLOCKED_METHODS),
        "pr15_merged_pr": PR15_MERGED_PR,
        "pr15_next_recommended_lane": PR15_NEXT_RECOMMENDED_LANE,
        "next_substantive_lane": NEXT_SUBSTANTIVE_LANE,
        **_SAFETY_FLAG_TEMPLATE,
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
        coverage = load_source_gap_audit(
            coverage_path,
            catalog=catalog,
            onboarding=onboarding,
            expected_catalog_ref=expected_catalog_ref,
            expected_onboarding_ref=expected_onboarding_ref,
        )
        recipe_dish_corpus = load_recipe_dish_corpus_governance(
            recipe_dish_corpus_path,
            onboarding=onboarding,
            coverage=coverage,
        )
        preference_mapping = load_preference_recipe_mapping_governance(
            preference_mapping_path,
            coverage=coverage,
            recipe_dish_corpus=recipe_dish_corpus,
            expected_coverage_ref=expected_coverage_ref,
            expected_recipe_dish_corpus_ref=expected_recipe_ref,
        )
        closeout = load_preference_mapping_closeout_governance(
            closeout_path,
            preference_mapping=preference_mapping,
            coverage=coverage,
            expected_pr15_ref=expected_pr15_ref,
            expected_coverage_ref=expected_coverage_ref,
            expected_recipe_dish_corpus_ref=expected_recipe_ref,
        )
    except (
        PreferenceMappingCloseoutError,
        PreferenceRecipeMappingError,
        RecipeDishCorpusGovernanceError,
        SourceCatalogError,
        SourceOnboardingError,
        SourceGapAuditError,
    ) as exc:
        report["validation_errors"] = [str(exc)]
        return report

    report.update(
        {
            "success": True,
            "pr15_ref": closeout.pr15_ref,
            "coverage_ref": closeout.coverage_ref,
            "recipe_dish_corpus_ref": closeout.recipe_dish_corpus_ref,
            "external_research_evidence_role": closeout.external_research_evidence_role,
            "deferred_followups": list(closeout.deferred_followups),
        }
    )
    return report
