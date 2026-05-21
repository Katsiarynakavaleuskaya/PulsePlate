"""Deterministic file-only PR19 regional catalog source-specific terms gate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from core.food_sources.preference_mapping_closeout import build_preference_mapping_closeout_report
from core.food_sources.regional_catalog_identity import (
    EXPECTED_CANDIDATE_IDS,
    RegionalCatalogIdentityError,
    build_regional_catalog_identity_report,
    load_regional_catalog_identity_governance,
)
from core.food_sources.regional_catalog_provider_terms import (
    NEXT_RECOMMENDED_LANE as PR18_NEXT_RECOMMENDED_LANE,
    RegionalCatalogProviderTermsCandidate,
    RegionalCatalogProviderTermsError,
    RegionalCatalogProviderTermsGovernance,
    build_regional_catalog_provider_terms_report,
    load_regional_catalog_provider_terms_governance,
)
from core.food_sources.source_catalog import SourceCatalogError, load_source_catalog
from core.food_sources.source_gap_audit import SourceGapAuditError, load_source_gap_audit
from core.food_sources.source_onboarding import SourceOnboardingError, load_source_onboarding

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_RE = re.compile(r"^food-data-regional-catalog-source-specific-terms-review\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SOURCE = "regional_catalogs"
SOURCE_CLASSIFICATION = "unresolved"
SOURCE_FAMILY = "regional_catalog"
PR18_MERGED_PR = 1783
FINAL_GATE_DECISION = "regional_catalog_source_specific_terms_review_only_no_provider_use"
NEXT_RECOMMENDED_LANE = "regional_catalog_source_specific_terms_closeout"

BLOCKED_METHODS = (
    "api_call",
    "scraping",
    "automated_collection",
    "download",
    "account_access",
    "paid_source_use",
    "seller_api_use",
    "partner_api_use",
    "provider_use",
    "cache_authority",
    "redistribution",
    "runtime_authority",
    "public_dataset_claim",
    "provider_integration",
    "product_display",
    "nutrition_authority",
    "source_authority",
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
    "account_access_allowed": False,
    "paid_source_use_allowed": False,
    "seller_api_use_allowed": False,
    "partner_api_use_allowed": False,
    "provider_use_allowed": False,
    "cache_authority_allowed": False,
    "redistribution_allowed": False,
    "provider_integration_allowed": False,
    "public_dataset_claim_allowed": False,
    "product_display_allowed": False,
    "nutrition_authority_allowed": False,
    "source_authority_allowed": False,
    "file_only": True,
}

_PR18_UNSAFE_FLAGS = (
    "runtime_cutover",
    "digitalocean_postgres_load",
    "bulk_ingest",
    "network_allowed",
    "db_writes_allowed",
    "api_calls_allowed",
    "source_download_allowed",
    "scraping_allowed",
    "automation_allowed",
    "paid_source_use_allowed",
    "seller_api_use_allowed",
    "partner_api_use_allowed",
    "cache_authority_allowed",
    "redistribution_allowed",
    "provider_integration_allowed",
    "public_dataset_claim_allowed",
    "product_display_allowed",
    "nutrition_authority_allowed",
)

_GOVERNANCE_KEYS = frozenset(
    {
        "schema_version",
        "generated_on",
        "pr18_provider_terms_ref",
        "pr18_merged_pr",
        "source",
        "source_classification",
        "source_family",
        "evidence_policy",
        "external_research_evidence_role",
        "blocked_methods",
        "source_specific_terms_decision",
        "candidate_source_specific_terms",
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
        "provider_route_classification",
        "pr18_allowed_role",
        "public_terms_reference",
        "public_terms_reference_role",
        "terms_document_identity_status",
        "account_access_status",
        "retrieval_contract_status",
        "license_status",
        "cache_terms_status",
        "redistribution_terms_status",
        "display_terms_status",
        "attribution_terms_status",
        "nutrition_authority_status",
        "product_authority_status",
        "evidence_confidence",
        "uncertainty_notes",
        "blocking_reasons",
        "allowed_role",
        "next_required_review",
    }
)

_EXPECTED_ALLOWED_ROLE = "review_only_no_provider_use"
_EXPECTED_PR18_NEXT_REVIEW = "source_specific_terms_packet_required"
_EXPECTED_NEXT_REVIEW = "dedicated_legal_contract_review_required"
_EXPECTED_PUBLIC_TERMS_REFERENCE_ROLE = (
    "candidate_public_reference_only_not_terms_or_source_authority"
)
_EXPECTED_BLOCKING_REASON = (
    "Public terms reference, terms-document identity, account access, retrieval "
    "contract, license, cache, redistribution, display, attribution, product "
    "authority, and nutrition authority remain unverified or blocked."
)
_EXPECTED_SOURCE_SPECIFIC_TERMS_DECISION = (
    "PR19 records source-specific terms review requirements only. It does not "
    "approve provider use, account access, API calls, scraping, downloads, "
    "database writes, cache authority, redistribution, product display, source "
    "authority, or nutrition authority."
)
_EXPECTED_TOP_LEVEL_NOTES = (
    "PR19 keeps every PR18 regional catalog candidate review-only. Public "
    "references are recorded as evidence pointers only and do not become terms "
    "truth, provider approval, runtime source authority, product display "
    "permission, cache authority, redistribution permission, or nutrition "
    "authority."
)

_BLOCKED_STATUS_FIELDS = {
    "terms_document_identity_status": "not_verified",
    "account_access_status": "unverified",
    "retrieval_contract_status": "unverified",
    "license_status": "unverified",
    "cache_terms_status": "blocked_unresolved",
    "redistribution_terms_status": "blocked_unresolved",
    "display_terms_status": "blocked_unresolved",
    "attribution_terms_status": "blocked_unresolved",
    "nutrition_authority_status": "blocked_not_authority",
    "product_authority_status": "blocked_not_authority",
    "evidence_confidence": "low_unverified",
}

_EXPECTED_UNCERTAINTY_NOTES = {
    "data_europa_national_portals": (
        "Portal umbrella may contain many datasets with different licenses; exact "
        "dataset terms remain unverified."
    ),
    "kroger": (
        "Developer reference does not establish permitted PulsePlate account access, "
        "cache, display, attribution, or redistribution."
    ),
    "walmart": (
        "Developer reference does not establish permitted PulsePlate account access, "
        "cache, display, attribution, or redistribution."
    ),
    "pepesto_grocery": (
        "Commercial catalog reference does not establish permitted PulsePlate "
        "contract terms, cache, display, attribution, or redistribution."
    ),
    "pricesapi": (
        "Aggregator reference does not establish upstream provenance, source-specific "
        "terms, cache, display, attribution, or redistribution."
    ),
    "yandex_eda": (
        "Partner menu reference does not establish PulsePlate partner authorization, "
        "cache, display, attribution, or redistribution."
    ),
    "wildberries": (
        "Seller API reference does not establish PulsePlate seller-account terms, "
        "cache, display, attribution, or redistribution."
    ),
    "ozon": (
        "Seller API reference does not establish PulsePlate seller-account terms, "
        "cache, display, attribution, or redistribution."
    ),
    "apify_scraping_providers": (
        "Scraping-style provider reference remains blocked pending dedicated legal "
        "and anti-scraping review."
    ),
}

_UNSAFE_PROSE_RE = re.compile(
    r"\b("
    r"(?:network|api calls?|api use|scraping|downloads?|account access|"
    r"paid (?:source|provider|plan)|seller access|seller api|partner access|"
    r"partner api|provider use|provider integration|db writes?|database writes?|"
    r"cache authority|redistribution|runtime authority|product display|"
    r"nutrition authority|source authority|source use)"
    r"\s+(?:is\s+)?(?:allowed|approved|authorized|enabled|permitted|granted)|"
    r"(?:allowed|approved|authorized|enabled|permitted|granted)\s+"
    r"(?:network|api calls?|api use|scraping|downloads?|account access|"
    r"paid (?:source|provider|plan)|seller access|seller api|partner access|"
    r"partner api|provider use|provider integration|db writes?|database writes?|"
    r"cache authority|redistribution|runtime authority|product display|"
    r"nutrition authority|source authority|source use)|"
    r"may scrape|may download|may call (?:the )?api|source authority approved|"
    r"provider use approved|product display approved|nutrition authority approved|"
    r"digitalocean postgres load approved"
    r")\b",
    re.IGNORECASE,
)


class RegionalCatalogSourceSpecificTermsError(ValueError):
    """Raised when the PR19 regional catalog source-specific terms gate is invalid."""


@dataclass(frozen=True)
class RegionalCatalogSourceSpecificTermsCandidate:
    """Validated PR19 source-specific terms review row."""

    candidate_id: str
    candidate_name: str
    region_scope: str
    country_or_market: str
    source_url: str
    upstream_evidence_type: str
    provider_route_classification: str
    pr18_allowed_role: str
    public_terms_reference: str
    public_terms_reference_role: str
    terms_document_identity_status: str
    account_access_status: str
    retrieval_contract_status: str
    license_status: str
    cache_terms_status: str
    redistribution_terms_status: str
    display_terms_status: str
    attribution_terms_status: str
    nutrition_authority_status: str
    product_authority_status: str
    evidence_confidence: str
    uncertainty_notes: str
    blocking_reasons: tuple[str, ...]
    allowed_role: str
    next_required_review: str


@dataclass(frozen=True)
class RegionalCatalogSourceSpecificTermsGovernance:
    """Validated PR19 regional catalog source-specific terms artifact."""

    schema_version: str
    generated_on: date
    pr18_provider_terms_ref: str
    pr18_merged_pr: int
    source: str
    source_classification: str
    source_family: str
    evidence_policy: str
    external_research_evidence_role: str
    blocked_methods: tuple[str, ...]
    source_specific_terms_decision: str
    candidate_source_specific_terms: tuple[RegionalCatalogSourceSpecificTermsCandidate, ...]
    next_recommended_lane: str
    final_gate_decision: str
    notes: str


def _source_specific_terms_error(
    context: str, detail: str
) -> RegionalCatalogSourceSpecificTermsError:
    return RegionalCatalogSourceSpecificTermsError(
        f"Invalid regional catalog source-specific terms gate {context}: {detail}"
    )


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _source_specific_terms_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _source_specific_terms_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _source_specific_terms_error(context, f"missing non-empty string '{key}'")
    result = value.strip()
    if _UNSAFE_PROSE_RE.search(result):
        raise _source_specific_terms_error(context, f"'{key}' must not approve source/provider use")
    return result


def _require_exact_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise _source_specific_terms_error(context, f"missing non-empty string '{key}'")
    if _UNSAFE_PROSE_RE.search(value):
        raise _source_specific_terms_error(context, f"'{key}' must not approve source/provider use")
    return value


def _require_int(data: dict[str, object], key: str, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _source_specific_terms_error(context, f"'{key}' must be an integer")
    return value


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _source_specific_terms_error(context, f"'{key}' must be a boolean")
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
        raise _source_specific_terms_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _source_specific_terms_error(
                context, f"'{key}[{index}]' must be a non-empty string"
            )
        normalized = item.strip()
        if _UNSAFE_PROSE_RE.search(normalized):
            raise _source_specific_terms_error(
                context, f"'{key}[{index}]' must not approve source/provider use"
            )
        if normalized in seen:
            raise _source_specific_terms_error(
                context, f"'{key}' contains duplicate value {normalized!r}"
            )
        seen.add(normalized)
        items.append(normalized)
    result = tuple(items)
    if not result:
        raise _source_specific_terms_error(context, f"'{key}' must not be empty")
    if expected is not None and result != expected:
        raise _source_specific_terms_error(
            context, f"'{key}' must be exactly: {', '.join(expected)}"
        )
    return result


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _source_specific_terms_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _source_specific_terms_error(context, "generated_on must use YYYY-MM-DD") from exc


def _relative_repo_path(path: Path | str) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _require_safety_flags(data: dict[str, object], context: str) -> None:
    flags = {key: _require_bool(data, key, context) for key in _SAFETY_FLAG_TEMPLATE}
    if flags != _SAFETY_FLAG_TEMPLATE:
        mismatches = [
            key
            for key, expected_value in _SAFETY_FLAG_TEMPLATE.items()
            if flags[key] != expected_value
        ]
        raise _source_specific_terms_error(
            context,
            "all unsafe flags must be false and file_only must be true: " + ", ".join(mismatches),
        )


def _validate_pr18_report(report: dict[str, object], context: str) -> None:
    if report.get("success") is not True:
        raise _source_specific_terms_error(context, "PR18 provider terms report must succeed")
    if report.get("next_recommended_lane") != PR18_NEXT_RECOMMENDED_LANE:
        raise _source_specific_terms_error(
            context,
            "PR18 next_recommended_lane must be regional_catalog_source_specific_terms_review",
        )
    candidate_ids = report.get("candidate_ids")
    if candidate_ids != list(EXPECTED_CANDIDATE_IDS):
        raise _source_specific_terms_error(context, "PR18 candidate_ids drifted")
    for flag_name in _PR18_UNSAFE_FLAGS:
        if report.get(flag_name) is not False:
            raise _source_specific_terms_error(context, f"PR18 unsafe flag drifted: {flag_name}")
    if report.get("file_only") is not True:
        raise _source_specific_terms_error(context, "PR18 file_only flag drifted")


def _validate_pr18_gate(
    gate: RegionalCatalogProviderTermsGovernance, context: str
) -> dict[str, RegionalCatalogProviderTermsCandidate]:
    if gate.next_recommended_lane != PR18_NEXT_RECOMMENDED_LANE:
        raise _source_specific_terms_error(context, "PR18 gate did not hand off to PR19")
    candidates = {candidate.candidate_id: candidate for candidate in gate.candidate_terms}
    if tuple(candidates) != EXPECTED_CANDIDATE_IDS:
        raise _source_specific_terms_error(context, "PR18 candidate order drifted")
    for candidate in gate.candidate_terms:
        if candidate.allowed_role != _EXPECTED_ALLOWED_ROLE:
            raise _source_specific_terms_error(
                context, f"PR18 allowed_role drifted: {candidate.candidate_id}"
            )
        if candidate.next_required_review != _EXPECTED_PR18_NEXT_REVIEW:
            raise _source_specific_terms_error(
                context, f"PR18 next_required_review drifted: {candidate.candidate_id}"
            )
    return candidates


def _candidate_source_specific_terms(
    data: dict[str, object],
    *,
    pr18_candidates: dict[str, RegionalCatalogProviderTermsCandidate],
    context: str,
) -> tuple[RegionalCatalogSourceSpecificTermsCandidate, ...]:
    value = data.get("candidate_source_specific_terms")
    if not isinstance(value, list):
        raise _source_specific_terms_error(
            context, "candidate_source_specific_terms must be a list"
        )
    rows: list[RegionalCatalogSourceSpecificTermsCandidate] = []
    seen: set[str] = set()
    for index, raw_candidate in enumerate(value):
        candidate_context = f"{context}.candidate_source_specific_terms[{index}]"
        candidate = _require_mapping(raw_candidate, candidate_context)
        unexpected = sorted(set(candidate) - _CANDIDATE_KEYS)
        if unexpected:
            raise _source_specific_terms_error(
                candidate_context, "unexpected candidate keys: " + ", ".join(unexpected)
            )
        candidate_id = _require_string(candidate, "candidate_id", candidate_context)
        if candidate_id not in EXPECTED_CANDIDATE_IDS:
            raise _source_specific_terms_error(
                candidate_context, f"unknown candidate_id {candidate_id!r}"
            )
        if candidate_id in seen:
            raise _source_specific_terms_error(
                context, f"candidate_source_specific_terms contains duplicate {candidate_id}"
            )
        seen.add(candidate_id)
        pr18_candidate = pr18_candidates[candidate_id]
        _validate_inherited_candidate_fields(candidate, pr18_candidate, candidate_context)
        public_terms_reference = _require_string(
            candidate, "public_terms_reference", candidate_context
        )
        if public_terms_reference != pr18_candidate.source_url:
            raise _source_specific_terms_error(
                candidate_context, "public_terms_reference must match PR18 source_url"
            )
        public_terms_reference_role = _require_string(
            candidate, "public_terms_reference_role", candidate_context
        )
        if public_terms_reference_role != _EXPECTED_PUBLIC_TERMS_REFERENCE_ROLE:
            raise _source_specific_terms_error(
                candidate_context, "public_terms_reference_role drifted"
            )
        for field_name, expected_value in _BLOCKED_STATUS_FIELDS.items():
            if _require_string(candidate, field_name, candidate_context) != expected_value:
                raise _source_specific_terms_error(candidate_context, f"{field_name} drifted")
        uncertainty_notes = _require_exact_string(candidate, "uncertainty_notes", candidate_context)
        if uncertainty_notes != _EXPECTED_UNCERTAINTY_NOTES[candidate_id]:
            raise _source_specific_terms_error(
                candidate_context, "uncertainty_notes must use controlled text"
            )
        blocking_reasons = _require_string_tuple(candidate, "blocking_reasons", candidate_context)
        if blocking_reasons != (_EXPECTED_BLOCKING_REASON,):
            raise _source_specific_terms_error(candidate_context, "blocking_reasons drifted")
        allowed_role = _require_string(candidate, "allowed_role", candidate_context)
        if allowed_role != _EXPECTED_ALLOWED_ROLE:
            raise _source_specific_terms_error(
                candidate_context, "allowed_role must remain review-only"
            )
        next_required_review = _require_string(candidate, "next_required_review", candidate_context)
        if next_required_review != _EXPECTED_NEXT_REVIEW:
            raise _source_specific_terms_error(candidate_context, "next_required_review drifted")
        rows.append(
            RegionalCatalogSourceSpecificTermsCandidate(
                candidate_id=candidate_id,
                candidate_name=pr18_candidate.candidate_name,
                region_scope=pr18_candidate.region_scope,
                country_or_market=pr18_candidate.country_or_market,
                source_url=pr18_candidate.source_url,
                upstream_evidence_type=pr18_candidate.upstream_evidence_type,
                provider_route_classification=pr18_candidate.provider_route_classification,
                pr18_allowed_role=pr18_candidate.allowed_role,
                public_terms_reference=public_terms_reference,
                public_terms_reference_role=public_terms_reference_role,
                terms_document_identity_status=_BLOCKED_STATUS_FIELDS[
                    "terms_document_identity_status"
                ],
                account_access_status=_BLOCKED_STATUS_FIELDS["account_access_status"],
                retrieval_contract_status=_BLOCKED_STATUS_FIELDS["retrieval_contract_status"],
                license_status=_BLOCKED_STATUS_FIELDS["license_status"],
                cache_terms_status=_BLOCKED_STATUS_FIELDS["cache_terms_status"],
                redistribution_terms_status=_BLOCKED_STATUS_FIELDS["redistribution_terms_status"],
                display_terms_status=_BLOCKED_STATUS_FIELDS["display_terms_status"],
                attribution_terms_status=_BLOCKED_STATUS_FIELDS["attribution_terms_status"],
                nutrition_authority_status=_BLOCKED_STATUS_FIELDS["nutrition_authority_status"],
                product_authority_status=_BLOCKED_STATUS_FIELDS["product_authority_status"],
                evidence_confidence=_BLOCKED_STATUS_FIELDS["evidence_confidence"],
                uncertainty_notes=uncertainty_notes,
                blocking_reasons=blocking_reasons,
                allowed_role=allowed_role,
                next_required_review=next_required_review,
            )
        )
    observed_ids = tuple(row.candidate_id for row in rows)
    if observed_ids != EXPECTED_CANDIDATE_IDS:
        raise _source_specific_terms_error(
            context,
            "candidate_source_specific_terms must preserve PR18 candidate order: "
            + ", ".join(EXPECTED_CANDIDATE_IDS),
        )
    return tuple(rows)


def _validate_inherited_candidate_fields(
    candidate: dict[str, object],
    pr18_candidate: RegionalCatalogProviderTermsCandidate,
    context: str,
) -> None:
    inherited_fields = {
        "candidate_name": pr18_candidate.candidate_name,
        "region_scope": pr18_candidate.region_scope,
        "country_or_market": pr18_candidate.country_or_market,
        "source_url": pr18_candidate.source_url,
        "upstream_evidence_type": pr18_candidate.upstream_evidence_type,
        "provider_route_classification": pr18_candidate.provider_route_classification,
        "pr18_allowed_role": pr18_candidate.allowed_role,
    }
    for field_name, expected_value in inherited_fields.items():
        if _require_string(candidate, field_name, context) != expected_value:
            raise _source_specific_terms_error(context, f"{field_name} must match PR18")


def _observed_safety_flags(path: Path | str) -> dict[str, object]:
    try:
        with Path(path).open("r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        key: payload.get(key)
        for key in _SAFETY_FLAG_TEMPLATE
        if key in payload and isinstance(payload.get(key), bool)
    }


def parse_regional_catalog_source_specific_terms_governance(
    payload: object,
    *,
    pr18_report: dict[str, object],
    pr18_gate: RegionalCatalogProviderTermsGovernance,
    expected_pr18_provider_terms_ref: str | None = None,
    context: str = "<regional-catalog-source-specific-terms>",
) -> RegionalCatalogSourceSpecificTermsGovernance:
    """Parse and validate the PR19 regional catalog source-specific terms artifact."""

    _validate_pr18_report(pr18_report, context)
    pr18_candidates = _validate_pr18_gate(pr18_gate, context)
    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _GOVERNANCE_KEYS)
    if unexpected_keys:
        raise _source_specific_terms_error(
            context, f"unexpected keys: {', '.join(unexpected_keys)}"
        )

    schema_version = _require_string(data, "schema_version", context)
    if not _SCHEMA_RE.fullmatch(schema_version):
        raise _source_specific_terms_error(
            context,
            "schema_version must look like "
            "food-data-regional-catalog-source-specific-terms-review.vN",
        )
    generated_on = _parse_date(_require_string(data, "generated_on", context), context)
    pr18_provider_terms_ref = _require_string(data, "pr18_provider_terms_ref", context)
    if (
        expected_pr18_provider_terms_ref is not None
        and pr18_provider_terms_ref != expected_pr18_provider_terms_ref
    ):
        raise _source_specific_terms_error(
            context,
            f"pr18_provider_terms_ref must be {expected_pr18_provider_terms_ref!r}",
        )
    if _require_int(data, "pr18_merged_pr", context) != PR18_MERGED_PR:
        raise _source_specific_terms_error(context, f"pr18_merged_pr must be {PR18_MERGED_PR}")
    if _require_string(data, "source", context) != SOURCE:
        raise _source_specific_terms_error(context, f"source must be {SOURCE}")
    if _require_string(data, "source_classification", context) != SOURCE_CLASSIFICATION:
        raise _source_specific_terms_error(
            context, f"source_classification must be {SOURCE_CLASSIFICATION}"
        )
    if _require_string(data, "source_family", context) != SOURCE_FAMILY:
        raise _source_specific_terms_error(context, f"source_family must be {SOURCE_FAMILY}")
    if _require_string(data, "evidence_policy", context) != "evidence_only_no_provider_use":
        raise _source_specific_terms_error(
            context, "evidence_policy must be evidence_only_no_provider_use"
        )
    external_role = _require_string(data, "external_research_evidence_role", context)
    if external_role != "review_context_only_not_source_authority":
        raise _source_specific_terms_error(
            context,
            "external_research_evidence_role must be review_context_only_not_source_authority",
        )
    blocked_methods = _require_string_tuple(
        data, "blocked_methods", context, expected=BLOCKED_METHODS
    )
    source_specific_terms_decision = _require_exact_string(
        data, "source_specific_terms_decision", context
    )
    if source_specific_terms_decision != _EXPECTED_SOURCE_SPECIFIC_TERMS_DECISION:
        raise _source_specific_terms_error(
            context, "source_specific_terms_decision must use controlled text"
        )
    _require_safety_flags(data, context)
    candidate_source_specific_terms = _candidate_source_specific_terms(
        data,
        pr18_candidates=pr18_candidates,
        context=context,
    )
    if _require_string(data, "next_recommended_lane", context) != NEXT_RECOMMENDED_LANE:
        raise _source_specific_terms_error(
            context, f"next_recommended_lane must be {NEXT_RECOMMENDED_LANE}"
        )
    if _require_string(data, "final_gate_decision", context) != FINAL_GATE_DECISION:
        raise _source_specific_terms_error(
            context, f"final_gate_decision must be {FINAL_GATE_DECISION}"
        )
    notes = _require_exact_string(data, "notes", context)
    if notes != _EXPECTED_TOP_LEVEL_NOTES:
        raise _source_specific_terms_error(context, "notes must use controlled text")

    return RegionalCatalogSourceSpecificTermsGovernance(
        schema_version=schema_version,
        generated_on=generated_on,
        pr18_provider_terms_ref=pr18_provider_terms_ref,
        pr18_merged_pr=PR18_MERGED_PR,
        source=SOURCE,
        source_classification=SOURCE_CLASSIFICATION,
        source_family=SOURCE_FAMILY,
        evidence_policy="evidence_only_no_provider_use",
        external_research_evidence_role=external_role,
        blocked_methods=blocked_methods,
        source_specific_terms_decision=source_specific_terms_decision,
        candidate_source_specific_terms=candidate_source_specific_terms,
        next_recommended_lane=NEXT_RECOMMENDED_LANE,
        final_gate_decision=FINAL_GATE_DECISION,
        notes=notes,
    )


def load_regional_catalog_source_specific_terms_governance(
    source_specific_terms_path: Path | str,
    *,
    pr18_report: dict[str, object],
    pr18_gate: RegionalCatalogProviderTermsGovernance,
    expected_pr18_provider_terms_ref: str | None = None,
) -> RegionalCatalogSourceSpecificTermsGovernance:
    """Load and validate a PR19 regional catalog source-specific terms artifact."""

    path = Path(source_specific_terms_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RegionalCatalogSourceSpecificTermsError(
            f"Cannot read regional catalog source-specific terms gate {path}: {exc}"
        ) from exc
    return parse_regional_catalog_source_specific_terms_governance(
        payload,
        pr18_report=pr18_report,
        pr18_gate=pr18_gate,
        expected_pr18_provider_terms_ref=expected_pr18_provider_terms_ref,
        context=str(path),
    )


def build_regional_catalog_source_specific_terms_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    coverage_path: Path | str,
    recipe_dish_corpus_path: Path | str,
    preference_mapping_path: Path | str,
    pr16_closeout_path: Path | str,
    pr17_identity_path: Path | str,
    pr18_provider_terms_path: Path | str,
    source_specific_terms_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR19 source-specific terms gate."""

    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    expected_coverage_ref = _relative_repo_path(coverage_path)
    expected_pr16_ref = _relative_repo_path(pr16_closeout_path)
    expected_pr17_ref = _relative_repo_path(pr17_identity_path)
    expected_pr18_ref = _relative_repo_path(pr18_provider_terms_path)
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
    report.update(_observed_safety_flags(source_specific_terms_path))
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
        pr17_report = build_regional_catalog_identity_report(
            catalog_path=catalog_path,
            onboarding_path=onboarding_path,
            coverage_path=coverage_path,
            recipe_dish_corpus_path=recipe_dish_corpus_path,
            preference_mapping_path=preference_mapping_path,
            pr16_closeout_path=pr16_closeout_path,
            regional_identity_path=pr17_identity_path,
        )
        pr16_report = build_preference_mapping_closeout_report(
            catalog_path=catalog_path,
            onboarding_path=onboarding_path,
            coverage_path=coverage_path,
            recipe_dish_corpus_path=recipe_dish_corpus_path,
            preference_mapping_path=preference_mapping_path,
            closeout_path=pr16_closeout_path,
        )
        pr17_gate = load_regional_catalog_identity_governance(
            pr17_identity_path,
            catalog=catalog,
            onboarding=onboarding,
            coverage=coverage,
            pr16_report=pr16_report,
            expected_catalog_ref=expected_catalog_ref,
            expected_onboarding_ref=expected_onboarding_ref,
            expected_coverage_ref=expected_coverage_ref,
            expected_pr16_closeout_ref=expected_pr16_ref,
        )
        pr18_report = build_regional_catalog_provider_terms_report(
            catalog_path=catalog_path,
            onboarding_path=onboarding_path,
            coverage_path=coverage_path,
            recipe_dish_corpus_path=recipe_dish_corpus_path,
            preference_mapping_path=preference_mapping_path,
            pr16_closeout_path=pr16_closeout_path,
            pr17_identity_path=pr17_identity_path,
            provider_terms_path=pr18_provider_terms_path,
        )
        pr18_gate = load_regional_catalog_provider_terms_governance(
            pr18_provider_terms_path,
            pr17_report=pr17_report,
            pr17_gate=pr17_gate,
            expected_pr17_identity_ref=expected_pr17_ref,
        )
        gate = load_regional_catalog_source_specific_terms_governance(
            source_specific_terms_path,
            pr18_report=pr18_report,
            pr18_gate=pr18_gate,
            expected_pr18_provider_terms_ref=expected_pr18_ref,
        )
    except (
        RegionalCatalogSourceSpecificTermsError,
        RegionalCatalogProviderTermsError,
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
            "pr18_provider_terms_ref": gate.pr18_provider_terms_ref,
            "pr18_merged_pr": gate.pr18_merged_pr,
            "evidence_policy": gate.evidence_policy,
            "external_research_evidence_role": gate.external_research_evidence_role,
            "source_specific_terms_decision": gate.source_specific_terms_decision,
            "candidate_decisions": {
                row.candidate_id: row.allowed_role for row in gate.candidate_source_specific_terms
            },
            "candidate_next_required_review": {
                row.candidate_id: row.next_required_review
                for row in gate.candidate_source_specific_terms
            },
            "candidate_evidence_confidence": {
                row.candidate_id: row.evidence_confidence
                for row in gate.candidate_source_specific_terms
            },
            "candidate_route_classifications": {
                row.candidate_id: row.provider_route_classification
                for row in gate.candidate_source_specific_terms
            },
        }
    )
    return report
