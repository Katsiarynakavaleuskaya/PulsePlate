"""Deterministic file-only PR18 regional catalog provider terms matrix gate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from core.food_sources.preference_mapping_closeout import build_preference_mapping_closeout_report
from core.food_sources.regional_catalog_identity import (
    EXPECTED_CANDIDATE_IDS,
    NEXT_RECOMMENDED_LANE as PR17_NEXT_RECOMMENDED_LANE,
    RegionalCatalogCandidateReview,
    RegionalCatalogIdentityError,
    RegionalCatalogIdentityGovernance,
    build_regional_catalog_identity_report,
    load_regional_catalog_identity_governance,
)
from core.food_sources.source_catalog import SourceCatalogError, load_source_catalog
from core.food_sources.source_gap_audit import SourceGapAuditError, load_source_gap_audit
from core.food_sources.source_onboarding import SourceOnboardingError, load_source_onboarding

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_RE = re.compile(r"^food-data-regional-catalog-provider-terms-matrix\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SOURCE = "regional_catalogs"
SOURCE_CLASSIFICATION = "unresolved"
SOURCE_FAMILY = "regional_catalog"
PR17_MERGED_PR = 1771
FINAL_GATE_DECISION = "regional_catalog_provider_terms_review_only_no_provider_use"
NEXT_RECOMMENDED_LANE = "regional_catalog_source_specific_terms_review"

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
        "pr17_identity_ref",
        "pr17_merged_pr",
        "source",
        "source_classification",
        "source_family",
        "evidence_policy",
        "external_research_evidence_role",
        "blocked_methods",
        "provider_terms_decision",
        "candidate_terms",
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
        "pr17_allowed_role",
        "provider_route_classification",
        "identity_status",
        "terms_status",
        "account_access_status",
        "retrieval_contract_status",
        "license_status",
        "cache_terms_status",
        "redistribution_terms_status",
        "display_terms_status",
        "attribution_terms_status",
        "nutrition_authority_status",
        "product_authority_status",
        "allowed_role",
        "blocking_reasons",
        "next_required_review",
        "notes",
    }
)

_EXPECTED_ROUTE_CLASSIFICATIONS = {
    "data_europa_national_portals": "public_open_data_portal_umbrella",
    "kroger": "commercial_grocery_api_candidate",
    "walmart": "commercial_grocery_api_candidate",
    "pepesto_grocery": "commercial_grocery_api_candidate",
    "pricesapi": "commercial_price_aggregator_candidate",
    "yandex_eda": "partner_menu_api_candidate",
    "wildberries": "seller_marketplace_api_candidate",
    "ozon": "seller_marketplace_api_candidate",
    "apify_scraping_providers": "scraping_provider_candidate",
}

_EXPECTED_ALLOWED_ROLE = "review_only_no_provider_use"
_EXPECTED_BLOCKING_REASON = (
    "Provider terms, account access, retrieval contract, license, cache, "
    "redistribution, attribution, product display, and nutrition authority "
    "remain unapproved."
)
_EXPECTED_NEXT_REVIEW = "source_specific_terms_packet_required"
_EXPECTED_PROVIDER_TERMS_DECISION = (
    "All PR17 regional catalog candidates remain evidence-only. PR18 records "
    "provider terms review status only and does not approve provider use."
)
_EXPECTED_TOP_LEVEL_NOTES = (
    "PR18 turns the PR17 regional catalog candidate list into a provider terms "
    "matrix. It keeps every candidate review-only and blocks API calls, scraping, "
    "downloads, paid source activity, seller or partner access, cache authority, "
    "redistribution, ingest, database writes, runtime authority, product display, "
    "and nutrition authority."
)
_EXPECTED_CANDIDATE_NOTES = {
    "data_europa_national_portals": (
        "Portal umbrella remains review-only until exact dataset terms, license, "
        "schema, attribution, and redistribution are verified in a source-specific packet."
    ),
    "kroger": (
        "Kroger remains review-only until developer terms, OAuth or account access, "
        "display, cache, attribution, and redistribution are verified in a "
        "source-specific packet."
    ),
    "walmart": (
        "Walmart remains review-only until developer terms, account access, display, "
        "cache, attribution, and redistribution are verified in a source-specific packet."
    ),
    "pepesto_grocery": (
        "Pepesto Grocery remains review-only until commercial terms, cost, display, "
        "cache, attribution, and redistribution are verified in a source-specific packet."
    ),
    "pricesapi": (
        "PricesAPI remains review-only until aggregator provenance, terms, display, "
        "cache, attribution, and redistribution are verified in a source-specific packet."
    ),
    "yandex_eda": (
        "Yandex EDA remains review-only until partner terms, account access, display, "
        "cache, attribution, and redistribution are verified in a source-specific packet."
    ),
    "wildberries": (
        "Wildberries remains review-only until seller terms, account access, display, "
        "cache, attribution, and redistribution are verified in a source-specific packet."
    ),
    "ozon": (
        "Ozon remains review-only until seller terms, account access, display, "
        "cache, attribution, and redistribution are verified in a source-specific packet."
    ),
    "apify_scraping_providers": (
        "Scraping-style providers remain blocked for this lane and require a later "
        "dedicated legal and anti-scraping packet."
    ),
}

_BLOCKED_STATUS_FIELDS = {
    "identity_status": "inherited_from_pr17_unverified",
    "terms_status": "unverified",
    "account_access_status": "unverified",
    "retrieval_contract_status": "unverified",
    "license_status": "unverified",
    "cache_terms_status": "blocked_unresolved",
    "redistribution_terms_status": "blocked_unresolved",
    "display_terms_status": "blocked_unresolved",
    "attribution_terms_status": "blocked_unresolved",
    "nutrition_authority_status": "blocked_not_authority",
    "product_authority_status": "blocked_not_authority",
}

_UNSAFE_PROSE_RE = re.compile(
    r"\b("
    r"api calls? allowed|api use approved|approved for api|may scrape|scraping allowed|"
    r"download approved|downloads? allowed|paid provider approved|paid source approved|"
    r"seller access allowed|seller api approved|partner access allowed|partner api approved|"
    r"cache authority approved|cache authority allowed|redistribution allowed|"
    r"runtime authority approved|runtime authority allowed|product display approved|"
    r"nutrition authority approved|provider integration approved|provider use approved|"
    r"source authority approved|data extraction approved|ingest approved|db writes allowed|"
    r"database writes allowed|digitalocean postgres load approved"
    r")\b",
    re.IGNORECASE,
)


class RegionalCatalogProviderTermsError(ValueError):
    """Raised when the PR18 regional catalog provider terms gate is invalid."""


@dataclass(frozen=True)
class RegionalCatalogProviderTermsCandidate:
    """Validated PR18 provider terms matrix row."""

    candidate_id: str
    candidate_name: str
    region_scope: str
    country_or_market: str
    source_url: str
    upstream_evidence_type: str
    pr17_allowed_role: str
    provider_route_classification: str
    identity_status: str
    terms_status: str
    account_access_status: str
    retrieval_contract_status: str
    license_status: str
    cache_terms_status: str
    redistribution_terms_status: str
    display_terms_status: str
    attribution_terms_status: str
    nutrition_authority_status: str
    product_authority_status: str
    allowed_role: str
    blocking_reasons: tuple[str, ...]
    next_required_review: str
    notes: str


@dataclass(frozen=True)
class RegionalCatalogProviderTermsGovernance:
    """Validated PR18 regional catalog provider terms matrix artifact."""

    schema_version: str
    generated_on: date
    pr17_identity_ref: str
    pr17_merged_pr: int
    source: str
    source_classification: str
    source_family: str
    evidence_policy: str
    external_research_evidence_role: str
    blocked_methods: tuple[str, ...]
    provider_terms_decision: str
    candidate_terms: tuple[RegionalCatalogProviderTermsCandidate, ...]
    next_recommended_lane: str
    final_gate_decision: str
    notes: str


def _provider_terms_error(context: str, detail: str) -> RegionalCatalogProviderTermsError:
    return RegionalCatalogProviderTermsError(
        f"Invalid regional catalog provider terms gate {context}: {detail}"
    )


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _provider_terms_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _provider_terms_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _provider_terms_error(context, f"missing non-empty string '{key}'")
    result = value.strip()
    if _UNSAFE_PROSE_RE.search(result):
        raise _provider_terms_error(context, f"'{key}' must not approve provider/source use")
    return result


def _require_exact_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise _provider_terms_error(context, f"missing non-empty string '{key}'")
    if _UNSAFE_PROSE_RE.search(value):
        raise _provider_terms_error(context, f"'{key}' must not approve provider/source use")
    return value


def _require_int(data: dict[str, object], key: str, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _provider_terms_error(context, f"'{key}' must be an integer")
    return value


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _provider_terms_error(context, f"'{key}' must be a boolean")
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
        raise _provider_terms_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _provider_terms_error(context, f"'{key}[{index}]' must be a non-empty string")
        normalized = item.strip()
        if _UNSAFE_PROSE_RE.search(normalized):
            raise _provider_terms_error(context, f"'{key}[{index}]' must not approve source use")
        if normalized in seen:
            raise _provider_terms_error(context, f"'{key}' contains duplicate value {normalized!r}")
        seen.add(normalized)
        items.append(normalized)
    result = tuple(items)
    if not result:
        raise _provider_terms_error(context, f"'{key}' must not be empty")
    if expected is not None and result != expected:
        raise _provider_terms_error(context, f"'{key}' must be exactly: {', '.join(expected)}")
    return result


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _provider_terms_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _provider_terms_error(context, "generated_on must use YYYY-MM-DD") from exc


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
        raise _provider_terms_error(
            context,
            "all unsafe flags must be false and file_only must be true: " + ", ".join(mismatches),
        )


def _validate_pr17_report(report: dict[str, object], context: str) -> None:
    if report.get("success") is not True:
        raise _provider_terms_error(context, "PR17 identity/license report must succeed")
    if report.get("next_recommended_lane") != "regional_catalog_provider_terms_matrix":
        raise _provider_terms_error(
            context,
            "PR17 next_recommended_lane must be regional_catalog_provider_terms_matrix",
        )
    candidate_ids = report.get("candidate_ids")
    if candidate_ids != list(EXPECTED_CANDIDATE_IDS):
        raise _provider_terms_error(context, "PR17 candidate_ids drifted")
    for flag_name, expected in _SAFETY_FLAG_TEMPLATE.items():
        if flag_name == "file_only":
            continue
        if report.get(flag_name) is not expected:
            raise _provider_terms_error(context, f"PR17 unsafe flag drifted: {flag_name}")


def _candidate_terms(
    data: dict[str, object],
    *,
    pr17_candidates: dict[str, RegionalCatalogCandidateReview],
    context: str,
) -> tuple[RegionalCatalogProviderTermsCandidate, ...]:
    value = data.get("candidate_terms")
    if not isinstance(value, list):
        raise _provider_terms_error(context, "candidate_terms must be a list")
    rows: list[RegionalCatalogProviderTermsCandidate] = []
    seen: set[str] = set()
    for index, raw_candidate in enumerate(value):
        candidate_context = f"{context}.candidate_terms[{index}]"
        candidate = _require_mapping(raw_candidate, candidate_context)
        unexpected = sorted(set(candidate) - _CANDIDATE_KEYS)
        if unexpected:
            raise _provider_terms_error(
                candidate_context, "unexpected candidate keys: " + ", ".join(unexpected)
            )
        candidate_id = _require_string(candidate, "candidate_id", candidate_context)
        if candidate_id not in EXPECTED_CANDIDATE_IDS:
            raise _provider_terms_error(candidate_context, f"unknown candidate_id {candidate_id!r}")
        if candidate_id in seen:
            raise _provider_terms_error(
                context, f"candidate_terms contains duplicate {candidate_id}"
            )
        seen.add(candidate_id)
        pr17_candidate = pr17_candidates[candidate_id]
        candidate_name = _require_string(candidate, "candidate_name", candidate_context)
        if candidate_name != pr17_candidate.candidate_name:
            raise _provider_terms_error(candidate_context, "candidate_name must match PR17")
        region_scope = _require_string(candidate, "region_scope", candidate_context)
        if region_scope != pr17_candidate.region_scope:
            raise _provider_terms_error(candidate_context, "region_scope must match PR17")
        country_or_market = _require_string(candidate, "country_or_market", candidate_context)
        if country_or_market != pr17_candidate.country_or_market:
            raise _provider_terms_error(candidate_context, "country_or_market must match PR17")
        source_url = _require_string(candidate, "source_url", candidate_context)
        if source_url != pr17_candidate.source_url:
            raise _provider_terms_error(candidate_context, "source_url must match PR17")
        upstream_evidence_type = _require_string(
            candidate, "upstream_evidence_type", candidate_context
        )
        if upstream_evidence_type != pr17_candidate.upstream_evidence_type:
            raise _provider_terms_error(candidate_context, "upstream_evidence_type must match PR17")
        pr17_allowed_role = _require_string(candidate, "pr17_allowed_role", candidate_context)
        if pr17_allowed_role != pr17_candidate.allowed_role:
            raise _provider_terms_error(candidate_context, "pr17_allowed_role must match PR17")
        if (
            _require_string(candidate, "provider_route_classification", candidate_context)
            != _EXPECTED_ROUTE_CLASSIFICATIONS[candidate_id]
        ):
            raise _provider_terms_error(candidate_context, "provider_route_classification drift")
        for field_name, expected_value in _BLOCKED_STATUS_FIELDS.items():
            if _require_string(candidate, field_name, candidate_context) != expected_value:
                raise _provider_terms_error(candidate_context, f"{field_name} must stay blocked")
        if _require_string(candidate, "allowed_role", candidate_context) != _EXPECTED_ALLOWED_ROLE:
            raise _provider_terms_error(candidate_context, "allowed_role must remain review-only")
        blocking_reasons = _require_string_tuple(candidate, "blocking_reasons", candidate_context)
        if blocking_reasons != (_EXPECTED_BLOCKING_REASON,):
            raise _provider_terms_error(candidate_context, "blocking_reasons drifted")
        if (
            _require_string(candidate, "next_required_review", candidate_context)
            != _EXPECTED_NEXT_REVIEW
        ):
            raise _provider_terms_error(candidate_context, "next_required_review drifted")
        notes = _require_exact_string(candidate, "notes", candidate_context)
        if notes != _EXPECTED_CANDIDATE_NOTES[candidate_id]:
            raise _provider_terms_error(candidate_context, "notes must use controlled text")
        rows.append(
            RegionalCatalogProviderTermsCandidate(
                candidate_id=candidate_id,
                candidate_name=pr17_candidate.candidate_name,
                region_scope=pr17_candidate.region_scope,
                country_or_market=pr17_candidate.country_or_market,
                source_url=pr17_candidate.source_url,
                upstream_evidence_type=pr17_candidate.upstream_evidence_type,
                pr17_allowed_role=pr17_candidate.allowed_role,
                provider_route_classification=_EXPECTED_ROUTE_CLASSIFICATIONS[candidate_id],
                identity_status=_BLOCKED_STATUS_FIELDS["identity_status"],
                terms_status=_BLOCKED_STATUS_FIELDS["terms_status"],
                account_access_status=_BLOCKED_STATUS_FIELDS["account_access_status"],
                retrieval_contract_status=_BLOCKED_STATUS_FIELDS["retrieval_contract_status"],
                license_status=_BLOCKED_STATUS_FIELDS["license_status"],
                cache_terms_status=_BLOCKED_STATUS_FIELDS["cache_terms_status"],
                redistribution_terms_status=_BLOCKED_STATUS_FIELDS["redistribution_terms_status"],
                display_terms_status=_BLOCKED_STATUS_FIELDS["display_terms_status"],
                attribution_terms_status=_BLOCKED_STATUS_FIELDS["attribution_terms_status"],
                nutrition_authority_status=_BLOCKED_STATUS_FIELDS["nutrition_authority_status"],
                product_authority_status=_BLOCKED_STATUS_FIELDS["product_authority_status"],
                allowed_role=_EXPECTED_ALLOWED_ROLE,
                blocking_reasons=blocking_reasons,
                next_required_review=_EXPECTED_NEXT_REVIEW,
                notes=notes,
            )
        )
    observed_ids = tuple(row.candidate_id for row in rows)
    if observed_ids != EXPECTED_CANDIDATE_IDS:
        raise _provider_terms_error(
            context,
            "candidate_terms must preserve PR17 candidate order: "
            + ", ".join(EXPECTED_CANDIDATE_IDS),
        )
    return tuple(rows)


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


def parse_regional_catalog_provider_terms_governance(
    payload: object,
    *,
    pr17_report: dict[str, object],
    pr17_gate: RegionalCatalogIdentityGovernance,
    expected_pr17_identity_ref: str | None = None,
    context: str = "<regional-catalog-provider-terms>",
) -> RegionalCatalogProviderTermsGovernance:
    """Parse and validate the PR18 regional catalog provider terms matrix artifact."""

    _validate_pr17_report(pr17_report, context)
    if pr17_gate.next_recommended_lane != PR17_NEXT_RECOMMENDED_LANE:
        raise _provider_terms_error(context, "PR17 gate did not hand off to PR18")
    pr17_candidates = {
        candidate.candidate_id: candidate for candidate in pr17_gate.candidate_reviews
    }
    if tuple(pr17_candidates) != EXPECTED_CANDIDATE_IDS:
        raise _provider_terms_error(context, "PR17 candidate order drifted")

    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _GOVERNANCE_KEYS)
    if unexpected_keys:
        raise _provider_terms_error(context, f"unexpected keys: {', '.join(unexpected_keys)}")

    schema_version = _require_string(data, "schema_version", context)
    if not _SCHEMA_RE.fullmatch(schema_version):
        raise _provider_terms_error(
            context,
            "schema_version must look like " "food-data-regional-catalog-provider-terms-matrix.vN",
        )
    generated_on = _parse_date(_require_string(data, "generated_on", context), context)
    pr17_identity_ref = _require_string(data, "pr17_identity_ref", context)
    if expected_pr17_identity_ref is not None and pr17_identity_ref != expected_pr17_identity_ref:
        raise _provider_terms_error(
            context, f"pr17_identity_ref must be {expected_pr17_identity_ref!r}"
        )
    if _require_int(data, "pr17_merged_pr", context) != PR17_MERGED_PR:
        raise _provider_terms_error(context, f"pr17_merged_pr must be {PR17_MERGED_PR}")
    if _require_string(data, "source", context) != SOURCE:
        raise _provider_terms_error(context, f"source must be {SOURCE}")
    if _require_string(data, "source_classification", context) != SOURCE_CLASSIFICATION:
        raise _provider_terms_error(
            context, f"source_classification must be {SOURCE_CLASSIFICATION}"
        )
    if _require_string(data, "source_family", context) != SOURCE_FAMILY:
        raise _provider_terms_error(context, f"source_family must be {SOURCE_FAMILY}")
    if _require_string(data, "evidence_policy", context) != "evidence_only_no_provider_use":
        raise _provider_terms_error(
            context, "evidence_policy must be evidence_only_no_provider_use"
        )
    external_role = _require_string(data, "external_research_evidence_role", context)
    if external_role != "review_context_only_not_source_authority":
        raise _provider_terms_error(
            context,
            "external_research_evidence_role must be review_context_only_not_source_authority",
        )
    blocked_methods = _require_string_tuple(
        data, "blocked_methods", context, expected=BLOCKED_METHODS
    )
    provider_terms_decision = _require_exact_string(data, "provider_terms_decision", context)
    if provider_terms_decision != _EXPECTED_PROVIDER_TERMS_DECISION:
        raise _provider_terms_error(context, "provider_terms_decision must use controlled text")
    _require_safety_flags(data, context)
    candidate_terms = _candidate_terms(data, pr17_candidates=pr17_candidates, context=context)
    if _require_string(data, "next_recommended_lane", context) != NEXT_RECOMMENDED_LANE:
        raise _provider_terms_error(
            context, f"next_recommended_lane must be {NEXT_RECOMMENDED_LANE}"
        )
    if _require_string(data, "final_gate_decision", context) != FINAL_GATE_DECISION:
        raise _provider_terms_error(context, f"final_gate_decision must be {FINAL_GATE_DECISION}")
    notes = _require_exact_string(data, "notes", context)
    if notes != _EXPECTED_TOP_LEVEL_NOTES:
        raise _provider_terms_error(context, "notes must use controlled text")

    return RegionalCatalogProviderTermsGovernance(
        schema_version=schema_version,
        generated_on=generated_on,
        pr17_identity_ref=pr17_identity_ref,
        pr17_merged_pr=PR17_MERGED_PR,
        source=SOURCE,
        source_classification=SOURCE_CLASSIFICATION,
        source_family=SOURCE_FAMILY,
        evidence_policy="evidence_only_no_provider_use",
        external_research_evidence_role=external_role,
        blocked_methods=blocked_methods,
        provider_terms_decision=provider_terms_decision,
        candidate_terms=candidate_terms,
        next_recommended_lane=NEXT_RECOMMENDED_LANE,
        final_gate_decision=FINAL_GATE_DECISION,
        notes=notes,
    )


def load_regional_catalog_provider_terms_governance(
    provider_terms_path: Path | str,
    *,
    pr17_report: dict[str, object],
    pr17_gate: object,
    expected_pr17_identity_ref: str | None = None,
) -> RegionalCatalogProviderTermsGovernance:
    """Load and validate a PR18 regional catalog provider terms JSON artifact."""

    path = Path(provider_terms_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RegionalCatalogProviderTermsError(
            f"Cannot read regional catalog provider terms gate {path}: {exc}"
        ) from exc
    return parse_regional_catalog_provider_terms_governance(
        payload,
        pr17_report=pr17_report,
        pr17_gate=pr17_gate,
        expected_pr17_identity_ref=expected_pr17_identity_ref,
        context=str(path),
    )


def build_regional_catalog_provider_terms_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    coverage_path: Path | str,
    recipe_dish_corpus_path: Path | str,
    preference_mapping_path: Path | str,
    pr16_closeout_path: Path | str,
    pr17_identity_path: Path | str,
    provider_terms_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR18 provider terms matrix gate."""

    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    expected_coverage_ref = _relative_repo_path(coverage_path)
    expected_pr16_ref = _relative_repo_path(pr16_closeout_path)
    expected_pr17_ref = _relative_repo_path(pr17_identity_path)
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
    report.update(_observed_safety_flags(provider_terms_path))
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
        gate = load_regional_catalog_provider_terms_governance(
            provider_terms_path,
            pr17_report=pr17_report,
            pr17_gate=pr17_gate,
            expected_pr17_identity_ref=expected_pr17_ref,
        )
    except (
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
            "pr17_identity_ref": gate.pr17_identity_ref,
            "pr17_merged_pr": gate.pr17_merged_pr,
            "evidence_policy": gate.evidence_policy,
            "external_research_evidence_role": gate.external_research_evidence_role,
            "provider_terms_decision": gate.provider_terms_decision,
            "candidate_decisions": {
                row.candidate_id: row.allowed_role for row in gate.candidate_terms
            },
            "provider_route_classifications": {
                row.candidate_id: row.provider_route_classification for row in gate.candidate_terms
            },
        }
    )
    return report
