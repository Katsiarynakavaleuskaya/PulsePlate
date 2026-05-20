"""Deterministic file-only regional catalog identity/license gate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from core.food_sources.preference_mapping_closeout import (
    NEXT_SUBSTANTIVE_LANE as PR16_NEXT_SUBSTANTIVE_LANE,
    build_preference_mapping_closeout_report,
)
from core.food_sources.source_catalog import (
    SourceCatalog,
    SourceCatalogEntry,
    SourceCatalogError,
    load_source_catalog,
)
from core.food_sources.source_gap_audit import (
    CoverageDomainDecision,
    SourceGapAudit,
    SourceGapAuditError,
    SourceGapDecision,
    load_source_gap_audit,
)
from core.food_sources.source_onboarding import (
    SourceOnboarding,
    SourceOnboardingEntry,
    SourceOnboardingError,
    load_source_onboarding,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_RE = re.compile(r"^food-data-regional-catalog-identity-license\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SOURCE = "regional_catalogs"
SOURCE_CLASSIFICATION = "unresolved"
SOURCE_FAMILY = "regional_catalog"
FINAL_GATE_DECISION = "regional_catalog_identity_review_only_no_ingest"
NEXT_RECOMMENDED_LANE = "regional_catalog_provider_terms_matrix"
PR16_MERGED_PR = 1768

BLOCKED_METHODS = (
    "api_call",
    "scraping",
    "automated_collection",
    "download",
    "paid_source_use",
    "seller_api_use",
    "partner_api_use",
    "cache_authority",
    "redistribution",
    "runtime_authority",
    "public_dataset_claim",
    "provider_integration",
    "product_display",
    "nutrition_authority",
    "database_write",
    "digitalocean_postgres_load",
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
    "automation_allowed": False,
    "paid_source_use_allowed": False,
    "seller_api_use_allowed": False,
    "partner_api_use_allowed": False,
    "cache_authority_allowed": False,
    "redistribution_allowed": False,
    "provider_integration_allowed": False,
    "public_dataset_claim_allowed": False,
    "product_display_allowed": False,
    "nutrition_authority_allowed": False,
    "file_only": True,
}

_GOVERNANCE_KEYS = frozenset(
    {
        "schema_version",
        "generated_on",
        "catalog_ref",
        "onboarding_ref",
        "coverage_ref",
        "pr16_closeout_ref",
        "pr16_merged_pr",
        "source",
        "source_classification",
        "source_family",
        "evidence_policy",
        "external_research_evidence_role",
        "blocked_methods",
        "budget_first_policy",
        "candidate_reviews",
        "next_recommended_lane",
        "final_gate_decision",
        "notes",
        *tuple(_SAFETY_FLAG_TEMPLATE),
    }
)

_CANDIDATE_KEYS = frozenset(
    {
        "candidate_id",
        "candidate_name",
        "region_scope",
        "country_or_market",
        "source_url",
        "upstream_evidence_type",
        "provider_identity_status",
        "license_status",
        "retrieval_contract_status",
        "language_locale_status",
        "unit_normalization_status",
        "nutrient_schema_status",
        "attribution_decision",
        "cache_decision",
        "redistribution_decision",
        "freshness_review_status",
        "allowed_role",
        "blocking_reasons",
        "notes",
    }
)

EXPECTED_CANDIDATE_IDS = (
    "data_europa_national_portals",
    "kroger",
    "walmart",
    "pepesto_grocery",
    "pricesapi",
    "yandex_eda",
    "wildberries",
    "ozon",
    "apify_scraping_providers",
)

_EXPECTED_ALLOWED_ROLES = {
    "data_europa_national_portals": "open_data_portal_review_candidate_only",
    "kroger": "regional_price_catalog_candidate_only",
    "walmart": "regional_price_catalog_candidate_only",
    "pepesto_grocery": "commercial_eu_catalog_candidate_only",
    "pricesapi": "global_price_aggregator_candidate_only",
    "yandex_eda": "partner_menu_candidate_only",
    "wildberries": "seller_terms_candidate_only",
    "ozon": "seller_terms_candidate_only",
    "apify_scraping_providers": "blocked_for_pr17",
}

_EXPECTED_EVIDENCE_TYPES = {
    "data_europa_national_portals": "attached_report_and_repo_sot_only",
    "kroger": "attached_report_only",
    "walmart": "attached_report_only",
    "pepesto_grocery": "attached_report_only",
    "pricesapi": "attached_report_only",
    "yandex_eda": "attached_report_only",
    "wildberries": "attached_report_only",
    "ozon": "attached_report_only",
    "apify_scraping_providers": "attached_report_only",
}

_EXPECTED_CANDIDATE_IDENTITY_FIELDS = {
    "data_europa_national_portals": {
        "candidate_name": "data.europa.eu and national open-data portals",
        "region_scope": "europe",
        "country_or_market": "EU and national markets",
        "source_url": "https://data.europa.eu/en",
    },
    "kroger": {
        "candidate_name": "Kroger Products API",
        "region_scope": "usa",
        "country_or_market": "USA",
        "source_url": "https://developer.kroger.com/",
    },
    "walmart": {
        "candidate_name": "Walmart API",
        "region_scope": "usa",
        "country_or_market": "USA",
        "source_url": "https://developer.walmart.com/",
    },
    "pepesto_grocery": {
        "candidate_name": "Pepesto Grocery API",
        "region_scope": "europe",
        "country_or_market": "EU",
        "source_url": "https://www.pepesto.com/",
    },
    "pricesapi": {
        "candidate_name": "PricesAPI",
        "region_scope": "global",
        "country_or_market": "Global",
        "source_url": "https://www.pricesapi.com/",
    },
    "yandex_eda": {
        "candidate_name": "Yandex EDA Vendor API",
        "region_scope": "cis",
        "country_or_market": "CIS",
        "source_url": "https://yandex.com/dev/eda/doc/en/",
    },
    "wildberries": {
        "candidate_name": "Wildberries Seller API",
        "region_scope": "cis",
        "country_or_market": "Russia/CIS",
        "source_url": "https://dev.wildberries.ru/",
    },
    "ozon": {
        "candidate_name": "Ozon Seller API",
        "region_scope": "cis",
        "country_or_market": "Russia/CIS",
        "source_url": "https://docs.ozon.ru/api/seller/",
    },
    "apify_scraping_providers": {
        "candidate_name": "Apify and scraping-style catalog providers",
        "region_scope": "global",
        "country_or_market": "Global",
        "source_url": "https://apify.com/",
    },
}

_BLOCKED_STATUS_FIELDS = {
    "provider_identity_status": "not_verified",
    "license_status": "unverified",
    "retrieval_contract_status": "unverified",
    "language_locale_status": "unverified",
    "unit_normalization_status": "unverified",
    "nutrient_schema_status": "unverified",
    "attribution_decision": "blocked_pending_license",
    "cache_decision": "blocked_unresolved",
    "redistribution_decision": "blocked_unresolved",
    "freshness_review_status": "unverified",
}

_CANDIDATE_BLOCKING_REASON = (
    "Exact source identity, license, retrieval contract, language/locale, unit "
    "normalization, nutrient schema, attribution, cache, freshness, and "
    "redistribution evidence remain unapproved."
)

_REGIONAL_DOMAIN_EXPECTED = {
    "coverage_decision": "deferred_unresolved",
    "gap_status": "locale_gap_unresolved",
    "authority_decision": "not_approved",
    "next_action": "regional_catalog_identity_license_review",
    "primary_sources": (),
    "auxiliary_sources": ("regional_catalogs",),
}

_REGIONAL_SOURCE_BLOCKING_REASONS = (
    "Locale-specific source identity, license, language, unit, schema, and redistribution terms are missing.",
)

_APPROVAL_TERMS = (
    r"approve|approves|approved|allow|allows|allowed|authorize|authorizes|authorized|"
    r"permit|permits|permitted|grant|grants|granted|enable|enables|enabled|usable|available|"
    r"cleared|greenlit|green light|go ahead|ok|okay"
)
_APPROVAL_NOUNS = r"approval|permission|authorization|clearance|greenlight|green light"
_USE_TERMS = (
    r"may(?:\W+\w+){0,3}\W+be used|can(?:\W+\w+){0,3}\W+be used|"
    r"could(?:\W+\w+){0,3}\W+be used|is used|are used|used|queried|"
    r"may call|can call|could call|relied on"
)
_EQUIVALENCE_TERMS = r"becomes?|serves as|treated as|equals"
_BLOCKED_NOTE_TERMS = (
    r"regional catalogs?|data europa eu|api calls?|scraping|scrapers?|downloads?|"
    r"paid source|paid provider|seller apis?|seller api access|seller access|"
    r"partner apis?|partner access|seller or partner access|"
    r"apis?|seller account access|partner menu access|provider apis?|"
    r"provider integration|cache authority|redistribution|runtime authority|product display|"
    r"nutrition authority|source authority|public dataset claim|automated collection|"
    r"digitalocean postgres(?:ql)? load|postgres(?:ql)? load|database writes?|db writes?|"
    r"data portal|marketplace terms?"
)
_FORBIDDEN_NOTE_PATTERNS = (
    re.compile(rf"\b(?:{_BLOCKED_NOTE_TERMS})\b(?:\W+\w+){{0,14}}\W+\b(?:{_APPROVAL_TERMS})\b"),
    re.compile(rf"\b(?:{_BLOCKED_NOTE_TERMS})\b(?:\W+\w+){{0,14}}\W+\b(?:{_APPROVAL_NOUNS})\b"),
    re.compile(
        rf"(?<!not )(?<!never )\b(?:{_APPROVAL_TERMS})\b"
        rf"(?:\W+\w+){{0,14}}\W+\b(?:{_BLOCKED_NOTE_TERMS})\b"
    ),
    re.compile(
        rf"(?<!without )(?<!no )(?<!not )(?<!never )\b(?:{_APPROVAL_NOUNS})\b"
        rf"(?:\W+\w+){{0,14}}\W+\b(?:{_BLOCKED_NOTE_TERMS})\b"
    ),
    re.compile(rf"\b(?:{_BLOCKED_NOTE_TERMS})\b(?:\W+\w+){{0,14}}\W+\b(?:{_USE_TERMS})\b"),
    re.compile(
        rf"\b(?:will\s+use|use|used|uses|using|queried|may\s+call|can\s+call|could\s+call|relied\s+on)\b"
        rf"(?:\W+\w+){{0,14}}\W+\b(?:{_BLOCKED_NOTE_TERMS})\b"
    ),
    re.compile(
        r"\b(?:data portal|data europa eu)\b(?:\W+\w+){0,4}\W+\b"
        r"(?:is|becomes|serves as|treated as|equals)\b"
        r"(?:\W+\w+){0,4}\W+\b(?:source authority|nutrition authority|product display)\b"
    ),
    re.compile(
        r"\b(?:source authority|nutrition authority|product display)\b"
        r"(?:\W+\w+){0,4}\W+\b(?:data portal|data europa eu)\b"
    ),
)
_BLOCKED_NOTE_RE = re.compile(rf"\b(?:{_BLOCKED_NOTE_TERMS})\b")
_NEGATED_APPROVAL_RE = re.compile(
    rf"\b(?:no|not|never)\s+(?:{_APPROVAL_TERMS})\b|"
    r"\bwithout\s+(?:approval|authorization|permission)\b|"
    r"\bunapproved\b"
)
_AUTHORITY_LANGUAGE_RE = re.compile(
    rf"\b(?:{_APPROVAL_TERMS})\b|\b(?:{_APPROVAL_NOUNS})\b|"
    rf"\b(?:{_USE_TERMS})\b|\b(?:{_EQUIVALENCE_TERMS})\b"
)
_NEGATED_DIRECT_AUTHORITY_RE = re.compile(
    r"\b(?:no|not|never)\s+(?:become\s+)?(?:a\s+|an\s+)?"
    r"(?:source authority|nutrition authority|product display)\b|"
    r"\b(?:is|are|be|becomes?|serves as|treated as)\s+"
    r"(?:no|not|never)\s+(?:a\s+|an\s+)?"
    r"(?:source authority|nutrition authority|product display)\b"
)


class RegionalCatalogIdentityError(ValueError):
    """Raised when the PR17 regional catalog identity/license gate is invalid."""


@dataclass(frozen=True)
class RegionalCatalogCandidateReview:
    """Validated regional catalog candidate review row."""

    candidate_id: str
    candidate_name: str
    region_scope: str
    country_or_market: str
    source_url: str
    upstream_evidence_type: str
    provider_identity_status: str
    license_status: str
    retrieval_contract_status: str
    language_locale_status: str
    unit_normalization_status: str
    nutrient_schema_status: str
    attribution_decision: str
    cache_decision: str
    redistribution_decision: str
    freshness_review_status: str
    allowed_role: str
    blocking_reasons: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class RegionalCatalogIdentityGovernance:
    """Validated PR17 regional catalog identity/license artifact."""

    schema_version: str
    generated_on: date
    catalog_ref: str
    onboarding_ref: str
    coverage_ref: str
    pr16_closeout_ref: str
    pr16_merged_pr: int
    source: str
    source_classification: str
    source_family: str
    evidence_policy: str
    external_research_evidence_role: str
    blocked_methods: tuple[str, ...]
    budget_first_policy: str
    candidate_reviews: tuple[RegionalCatalogCandidateReview, ...]
    next_recommended_lane: str
    final_gate_decision: str
    notes: str


def _identity_error(context: str, detail: str) -> RegionalCatalogIdentityError:
    return RegionalCatalogIdentityError(
        f"Invalid regional catalog identity gate {context}: {detail}"
    )


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _identity_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _identity_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _identity_error(context, f"missing non-empty string '{key}'")
    return value.strip()


def _require_int(data: dict[str, object], key: str, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _identity_error(context, f"'{key}' must be an integer")
    return value


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _identity_error(context, f"'{key}' must be a boolean")
    return value


def _require_string_tuple(
    data: dict[str, object],
    key: str,
    context: str,
    *,
    expected: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list):
        raise _identity_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _identity_error(context, f"'{key}[{index}]' must be a non-empty string")
        normalized = item.strip()
        if normalized in seen:
            raise _identity_error(context, f"'{key}' contains duplicate value {normalized!r}")
        seen.add(normalized)
        items.append(normalized)
    result = tuple(items)
    if not result:
        raise _identity_error(context, f"'{key}' must not be empty")
    if expected is not None and result != expected:
        raise _identity_error(context, f"'{key}' must be exactly: {', '.join(expected)}")
    return result


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _identity_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _identity_error(context, "generated_on must use YYYY-MM-DD") from exc


def _relative_repo_path(path: Path | str) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _require_safe_notes(value: str, context: str) -> str:
    segments = [
        re.sub(r"[\s_\-/;:,.()[\]{}]+", " ", segment).strip()
        for segment in re.split(r"[;\n]+|(?<=[.!?])\s+", value.lower())
    ]
    for normalized in (segment for segment in segments if segment):
        sanitized = _NEGATED_DIRECT_AUTHORITY_RE.sub(" ", normalized)
        remaining_authority_text = _NEGATED_APPROVAL_RE.sub(" ", sanitized)
        if _BLOCKED_NOTE_RE.search(remaining_authority_text) and _AUTHORITY_LANGUAGE_RE.search(
            remaining_authority_text
        ):
            raise _identity_error(context, "notes must not approve regional catalog source use")
        for pattern in _FORBIDDEN_NOTE_PATTERNS:
            for match in pattern.finditer(sanitized):
                match_text = match.group(0)
                if not _AUTHORITY_LANGUAGE_RE.search(match_text):
                    raise _identity_error(
                        context, "notes must not approve regional catalog source use"
                    )
                remaining_authority_text = _NEGATED_APPROVAL_RE.sub(" ", match_text)
                if not _AUTHORITY_LANGUAGE_RE.search(remaining_authority_text):
                    continue
                raise _identity_error(context, "notes must not approve regional catalog source use")
    return value


def _require_safety_flags(data: dict[str, object], context: str) -> None:
    flags = {key: _require_bool(data, key, context) for key in _SAFETY_FLAG_TEMPLATE}
    if flags != _SAFETY_FLAG_TEMPLATE:
        mismatches = [
            key
            for key, expected_value in _SAFETY_FLAG_TEMPLATE.items()
            if flags[key] != expected_value
        ]
        raise _identity_error(
            context,
            "all unsafe flags must be false and file_only must be true: " + ", ".join(mismatches),
        )


def _regional_catalog_entry(catalog: SourceCatalog, context: str) -> SourceCatalogEntry:
    entries = {entry.source: entry for entry in catalog.sources}
    entry = entries.get(SOURCE)
    if entry is None:
        raise _identity_error(context, f"catalog must include {SOURCE}")
    return entry


def _regional_onboarding_entry(
    onboarding: SourceOnboarding,
    context: str,
) -> SourceOnboardingEntry:
    entries = {entry.source: entry for entry in onboarding.sources}
    entry = entries.get(SOURCE)
    if entry is None:
        raise _identity_error(context, f"onboarding must include {SOURCE}")
    return entry


def _validate_catalog_policy(entry: SourceCatalogEntry, context: str) -> None:
    expected: dict[str, object] = {
        "source_classification": SOURCE_CLASSIFICATION,
        "source_family": SOURCE_FAMILY,
        "status": "blocked_unresolved",
        "license_review": "unresolved_required",
        "active_update_source": False,
    }
    actual: dict[str, object] = {
        "source_classification": entry.source_classification,
        "source_family": entry.source_family,
        "status": entry.status,
        "license_review": entry.license_review,
        "active_update_source": entry.active_update_source,
    }
    mismatches = [key for key, expected_value in expected.items() if actual[key] != expected_value]
    if mismatches:
        raise _identity_error(
            context, "regional catalog catalog policy drift: " + ", ".join(mismatches)
        )


def _validate_onboarding_policy(entry: SourceOnboardingEntry, context: str) -> None:
    expected: dict[str, object] = {
        "source_classification": SOURCE_CLASSIFICATION,
        "source_family": SOURCE_FAMILY,
        "onboarding_status": "unresolved_blocked",
        "ingestion_path": "unresolved_identity_required",
        "cache_decision": "blocked_unresolved",
        "redistribution_decision": "blocked_unresolved",
        "display_decision": "blocked_unresolved",
        "attribution_required": True,
        "commercial_risk": "unresolved",
        "provider_policy_ref": None,
        "source_specific_policy_required": True,
    }
    actual: dict[str, object] = {
        "source_classification": entry.source_classification,
        "source_family": entry.source_family,
        "onboarding_status": entry.onboarding_status,
        "ingestion_path": entry.ingestion_path,
        "cache_decision": entry.cache_decision,
        "redistribution_decision": entry.redistribution_decision,
        "display_decision": entry.display_decision,
        "attribution_required": entry.attribution_required,
        "commercial_risk": entry.commercial_risk,
        "provider_policy_ref": entry.provider_policy_ref,
        "source_specific_policy_required": entry.source_specific_policy_required,
    }
    mismatches = [key for key, expected_value in expected.items() if actual[key] != expected_value]
    if mismatches:
        raise _identity_error(
            context, "regional catalog onboarding policy drift: " + ", ".join(mismatches)
        )


def _validate_regional_domain(domain: CoverageDomainDecision, context: str) -> None:
    for field_name, expected_value in _REGIONAL_DOMAIN_EXPECTED.items():
        if getattr(domain, field_name) != expected_value:
            raise _identity_error(
                context,
                f"PR11 regional_local_products {field_name} must be {expected_value!r}",
            )
    if domain.approved_ingest or domain.approved_runtime_authority:
        raise _identity_error(context, "PR11 regional_local_products must stay unapproved")
    _require_safe_notes(domain.notes, context)


def _validate_regional_source(source: SourceGapDecision, context: str) -> None:
    if (
        source.decision != "deferred_unresolved"
        or source.source_family != SOURCE_FAMILY
        or source.allowed_role != "identity_license_review_candidate"
    ):
        raise _identity_error(context, "PR11 regional_catalogs must remain identity/license review")
    if source.blocking_reasons != _REGIONAL_SOURCE_BLOCKING_REASONS:
        raise _identity_error(
            context,
            "PR11 regional_catalogs blocking_reasons must preserve unresolved identity/license evidence",
        )
    if (
        source.approved_ingest
        or source.approved_runtime_authority
        or source.api_calls_allowed
        or source.scraping_allowed
        or source.paid_source_use_allowed
    ):
        raise _identity_error(context, "PR11 regional_catalogs must not approve source use")
    _require_safe_notes(source.notes, context)


def _validate_pr11_handoff(coverage: SourceGapAudit, context: str) -> None:
    regional_domains = tuple(
        domain for domain in coverage.coverage_domains if domain.domain == "regional_local_products"
    )
    if len(regional_domains) != 1:
        raise _identity_error(context, "PR11 regional_local_products must appear exactly once")
    _validate_regional_domain(regional_domains[0], context)

    regional_sources = tuple(
        source for source in coverage.source_gap_decisions if source.source == SOURCE
    )
    if len(regional_sources) != 1:
        raise _identity_error(context, "PR11 regional_catalogs source must appear exactly once")
    _validate_regional_source(regional_sources[0], context)


def _validate_pr16_report(report: dict[str, object], context: str) -> None:
    if report.get("success") is not True:
        raise _identity_error(context, "PR16 closeout report must validate before PR17")
    if report.get("next_substantive_lane") != PR16_NEXT_SUBSTANTIVE_LANE:
        raise _identity_error(
            context,
            f"PR16 next_substantive_lane must be {PR16_NEXT_SUBSTANTIVE_LANE}",
        )
    pr16_expected_flags = {
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "network_allowed": False,
        "db_writes_allowed": False,
        "api_calls_allowed": False,
        "source_download_allowed": False,
        "scraping_allowed": False,
        "automation_allowed": False,
        "paid_source_use_allowed": False,
        "seller_api_use_allowed": False,
        "partner_api_use_allowed": False,
        "cache_authority_allowed": False,
        "redistribution_allowed": False,
        "provider_integration_allowed": False,
        "public_dataset_claim_allowed": False,
        "product_display_allowed": False,
        "nutrition_authority_allowed": False,
        "file_only": True,
    }
    for flag_name, expected_value in pr16_expected_flags.items():
        if report.get(flag_name) is not expected_value:
            raise _identity_error(context, f"PR16 report {flag_name} must remain {expected_value}")


def _candidate_review(data: dict[str, object], context: str) -> RegionalCatalogCandidateReview:
    unexpected_keys = sorted(set(data) - _CANDIDATE_KEYS)
    if unexpected_keys:
        raise _identity_error(context, f"unexpected candidate keys: {', '.join(unexpected_keys)}")
    candidate_id = _require_string(data, "candidate_id", context)
    if candidate_id not in EXPECTED_CANDIDATE_IDS:
        raise _identity_error(context, f"unknown candidate_id {candidate_id!r}")
    expected_role = _EXPECTED_ALLOWED_ROLES[candidate_id]
    allowed_role = _require_string(data, "allowed_role", context)
    if allowed_role != expected_role:
        raise _identity_error(context, f"{candidate_id} allowed_role must be {expected_role}")
    evidence_type = _require_string(data, "upstream_evidence_type", context)
    if evidence_type != _EXPECTED_EVIDENCE_TYPES[candidate_id]:
        raise _identity_error(
            context, f"{candidate_id} upstream_evidence_type must stay review-only"
        )
    for field_name, expected_value in _EXPECTED_CANDIDATE_IDENTITY_FIELDS[candidate_id].items():
        if _require_string(data, field_name, context) != expected_value:
            raise _identity_error(context, f"{candidate_id} {field_name} must be {expected_value}")
    for field_name, expected_value in _BLOCKED_STATUS_FIELDS.items():
        if _require_string(data, field_name, context) != expected_value:
            raise _identity_error(context, f"{candidate_id} {field_name} must be {expected_value}")
    blocking_reasons = _require_string_tuple(data, "blocking_reasons", context)
    if blocking_reasons != (_CANDIDATE_BLOCKING_REASON,):
        raise _identity_error(context, f"{candidate_id} blocking_reasons must stay unresolved")
    return RegionalCatalogCandidateReview(
        candidate_id=candidate_id,
        candidate_name=_EXPECTED_CANDIDATE_IDENTITY_FIELDS[candidate_id]["candidate_name"],
        region_scope=_EXPECTED_CANDIDATE_IDENTITY_FIELDS[candidate_id]["region_scope"],
        country_or_market=_EXPECTED_CANDIDATE_IDENTITY_FIELDS[candidate_id]["country_or_market"],
        source_url=_EXPECTED_CANDIDATE_IDENTITY_FIELDS[candidate_id]["source_url"],
        upstream_evidence_type=evidence_type,
        provider_identity_status=_require_string(data, "provider_identity_status", context),
        license_status=_require_string(data, "license_status", context),
        retrieval_contract_status=_require_string(data, "retrieval_contract_status", context),
        language_locale_status=_require_string(data, "language_locale_status", context),
        unit_normalization_status=_require_string(data, "unit_normalization_status", context),
        nutrient_schema_status=_require_string(data, "nutrient_schema_status", context),
        attribution_decision=_require_string(data, "attribution_decision", context),
        cache_decision=_require_string(data, "cache_decision", context),
        redistribution_decision=_require_string(data, "redistribution_decision", context),
        freshness_review_status=_require_string(data, "freshness_review_status", context),
        allowed_role=allowed_role,
        blocking_reasons=blocking_reasons,
        notes=_require_safe_notes(_require_string(data, "notes", context), context),
    )


def _candidate_reviews(
    data: dict[str, object], context: str
) -> tuple[RegionalCatalogCandidateReview, ...]:
    value = data.get("candidate_reviews")
    if not isinstance(value, list):
        raise _identity_error(context, "candidate_reviews must be a list")
    reviews = tuple(
        _candidate_review(_require_mapping(item, f"{context}.candidate_reviews[{index}]"), context)
        for index, item in enumerate(value)
    )
    candidate_ids = tuple(review.candidate_id for review in reviews)
    if candidate_ids != EXPECTED_CANDIDATE_IDS:
        raise _identity_error(
            context,
            "candidate_reviews must be exactly: " + ", ".join(EXPECTED_CANDIDATE_IDS),
        )
    return reviews


def parse_regional_catalog_identity_governance(
    payload: object,
    *,
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    coverage: SourceGapAudit,
    pr16_report: dict[str, object],
    expected_catalog_ref: str | None = None,
    expected_onboarding_ref: str | None = None,
    expected_coverage_ref: str | None = None,
    expected_pr16_closeout_ref: str | None = None,
    context: str = "<regional-catalog-identity>",
) -> RegionalCatalogIdentityGovernance:
    """Parse and validate the PR17 regional catalog identity/license artifact."""

    _validate_catalog_policy(_regional_catalog_entry(catalog, context), context)
    _validate_onboarding_policy(_regional_onboarding_entry(onboarding, context), context)
    _validate_pr11_handoff(coverage, context)
    _validate_pr16_report(pr16_report, context)

    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _GOVERNANCE_KEYS)
    if unexpected_keys:
        raise _identity_error(context, f"unexpected keys: {', '.join(unexpected_keys)}")

    schema_version = _require_string(data, "schema_version", context)
    if not _SCHEMA_RE.fullmatch(schema_version):
        raise _identity_error(
            context, "schema_version must look like food-data-regional-catalog-identity-license.vN"
        )
    catalog_ref = _require_string(data, "catalog_ref", context)
    if expected_catalog_ref is not None and catalog_ref != expected_catalog_ref:
        raise _identity_error(context, f"catalog_ref must be {expected_catalog_ref!r}")
    onboarding_ref = _require_string(data, "onboarding_ref", context)
    if expected_onboarding_ref is not None and onboarding_ref != expected_onboarding_ref:
        raise _identity_error(context, f"onboarding_ref must be {expected_onboarding_ref!r}")
    coverage_ref = _require_string(data, "coverage_ref", context)
    if expected_coverage_ref is not None and coverage_ref != expected_coverage_ref:
        raise _identity_error(context, f"coverage_ref must be {expected_coverage_ref!r}")
    pr16_closeout_ref = _require_string(data, "pr16_closeout_ref", context)
    if expected_pr16_closeout_ref is not None and pr16_closeout_ref != expected_pr16_closeout_ref:
        raise _identity_error(context, f"pr16_closeout_ref must be {expected_pr16_closeout_ref!r}")
    if _require_int(data, "pr16_merged_pr", context) != PR16_MERGED_PR:
        raise _identity_error(context, f"pr16_merged_pr must be {PR16_MERGED_PR}")
    if _require_string(data, "source", context) != SOURCE:
        raise _identity_error(context, f"source must be {SOURCE}")
    if _require_string(data, "source_classification", context) != SOURCE_CLASSIFICATION:
        raise _identity_error(context, f"source_classification must be {SOURCE_CLASSIFICATION}")
    if _require_string(data, "source_family", context) != SOURCE_FAMILY:
        raise _identity_error(context, f"source_family must be {SOURCE_FAMILY}")
    if _require_string(data, "evidence_policy", context) != "evidence_only_no_source_authority":
        raise _identity_error(context, "evidence_policy must be evidence_only_no_source_authority")
    external_role = _require_string(data, "external_research_evidence_role", context)
    if external_role != "review_context_only_not_source_authority":
        raise _identity_error(
            context,
            "external_research_evidence_role must be review_context_only_not_source_authority",
        )
    blocked_methods = _require_string_tuple(
        data, "blocked_methods", context, expected=BLOCKED_METHODS
    )
    budget_first_policy = _require_safe_notes(
        _require_string(data, "budget_first_policy", context),
        context,
    )
    _require_safety_flags(data, context)
    candidate_reviews = _candidate_reviews(data, context)
    if _require_string(data, "next_recommended_lane", context) != NEXT_RECOMMENDED_LANE:
        raise _identity_error(context, f"next_recommended_lane must be {NEXT_RECOMMENDED_LANE}")
    if _require_string(data, "final_gate_decision", context) != FINAL_GATE_DECISION:
        raise _identity_error(context, f"final_gate_decision must be {FINAL_GATE_DECISION}")

    return RegionalCatalogIdentityGovernance(
        schema_version=schema_version,
        generated_on=_parse_date(_require_string(data, "generated_on", context), context),
        catalog_ref=catalog_ref,
        onboarding_ref=onboarding_ref,
        coverage_ref=coverage_ref,
        pr16_closeout_ref=pr16_closeout_ref,
        pr16_merged_pr=PR16_MERGED_PR,
        source=SOURCE,
        source_classification=SOURCE_CLASSIFICATION,
        source_family=SOURCE_FAMILY,
        evidence_policy="evidence_only_no_source_authority",
        external_research_evidence_role=external_role,
        blocked_methods=blocked_methods,
        budget_first_policy=budget_first_policy,
        candidate_reviews=candidate_reviews,
        next_recommended_lane=NEXT_RECOMMENDED_LANE,
        final_gate_decision=FINAL_GATE_DECISION,
        notes=_require_safe_notes(_require_string(data, "notes", context), context),
    )


def load_regional_catalog_identity_governance(
    identity_path: Path | str,
    *,
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    coverage: SourceGapAudit,
    pr16_report: dict[str, object],
    expected_catalog_ref: str | None = None,
    expected_onboarding_ref: str | None = None,
    expected_coverage_ref: str | None = None,
    expected_pr16_closeout_ref: str | None = None,
) -> RegionalCatalogIdentityGovernance:
    """Load and validate a PR17 regional catalog identity/license JSON artifact."""

    path = Path(identity_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RegionalCatalogIdentityError(
            f"Cannot read regional catalog identity gate {path}: {exc}"
        ) from exc
    return parse_regional_catalog_identity_governance(
        payload,
        catalog=catalog,
        onboarding=onboarding,
        coverage=coverage,
        pr16_report=pr16_report,
        expected_catalog_ref=expected_catalog_ref,
        expected_onboarding_ref=expected_onboarding_ref,
        expected_coverage_ref=expected_coverage_ref,
        expected_pr16_closeout_ref=expected_pr16_closeout_ref,
        context=str(path),
    )


def build_regional_catalog_identity_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    coverage_path: Path | str,
    recipe_dish_corpus_path: Path | str,
    preference_mapping_path: Path | str,
    pr16_closeout_path: Path | str,
    regional_identity_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR17 regional catalog gate."""

    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    expected_coverage_ref = _relative_repo_path(coverage_path)
    expected_pr16_ref = _relative_repo_path(pr16_closeout_path)
    report: dict[str, object] = {
        "success": False,
        "dry_run": True,
        "source": SOURCE,
        "source_classification": SOURCE_CLASSIFICATION,
        "source_family": SOURCE_FAMILY,
        "blocked_methods": list(BLOCKED_METHODS),
        "candidate_ids": list(EXPECTED_CANDIDATE_IDS),
        "next_recommended_lane": NEXT_RECOMMENDED_LANE,
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
        pr16_report = build_preference_mapping_closeout_report(
            catalog_path=catalog_path,
            onboarding_path=onboarding_path,
            coverage_path=coverage_path,
            recipe_dish_corpus_path=recipe_dish_corpus_path,
            preference_mapping_path=preference_mapping_path,
            closeout_path=pr16_closeout_path,
        )
        gate = load_regional_catalog_identity_governance(
            regional_identity_path,
            catalog=catalog,
            onboarding=onboarding,
            coverage=coverage,
            pr16_report=pr16_report,
            expected_catalog_ref=expected_catalog_ref,
            expected_onboarding_ref=expected_onboarding_ref,
            expected_coverage_ref=expected_coverage_ref,
            expected_pr16_closeout_ref=expected_pr16_ref,
        )
    except (
        RegionalCatalogIdentityError,
        SourceCatalogError,
        SourceOnboardingError,
        SourceGapAuditError,
    ) as exc:
        report["validation_errors"] = [str(exc)]
        return report

    report.update(
        {
            "success": True,
            "catalog_ref": gate.catalog_ref,
            "onboarding_ref": gate.onboarding_ref,
            "coverage_ref": gate.coverage_ref,
            "pr16_closeout_ref": gate.pr16_closeout_ref,
            "pr16_merged_pr": gate.pr16_merged_pr,
            "evidence_policy": gate.evidence_policy,
            "external_research_evidence_role": gate.external_research_evidence_role,
            "candidate_decisions": {
                review.candidate_id: review.allowed_role for review in gate.candidate_reviews
            },
        }
    )
    return report
