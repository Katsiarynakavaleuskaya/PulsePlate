"""Deterministic file-only PR21 dedicated legal-contract review gate."""

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
    RegionalCatalogProviderTermsError,
    build_regional_catalog_provider_terms_report,
    load_regional_catalog_provider_terms_governance,
)
from core.food_sources.regional_catalog_source_specific_terms import (
    RegionalCatalogSourceSpecificTermsError,
    build_regional_catalog_source_specific_terms_report,
    load_regional_catalog_source_specific_terms_governance,
)
from core.food_sources.regional_catalog_source_specific_terms_closeout import (
    FINAL_GATE_DECISION as PR20_FINAL_GATE_DECISION,
    NEXT_RECOMMENDED_LANE as PR20_NEXT_RECOMMENDED_LANE,
    RegionalCatalogSourceSpecificTermsCloseoutError,
    RegionalCatalogSourceSpecificTermsCloseoutGovernance,
    build_regional_catalog_source_specific_terms_closeout_report,
    load_regional_catalog_source_specific_terms_closeout_governance,
)
from core.food_sources.source_catalog import SourceCatalogError, load_source_catalog
from core.food_sources.source_gap_audit import SourceGapAuditError, load_source_gap_audit
from core.food_sources.source_onboarding import SourceOnboardingError, load_source_onboarding

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_RE = re.compile(r"^food-data-regional-catalog-dedicated-legal-contract-review\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PR20_REF = (
    "docs/architecture/"
    "FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_CLOSEOUT_PR20_2026-05-24.json"
)
PR20_MERGED_PR = 1815
PR20_MERGE_MARKER = "PR #1815 merged before PR21 scope lock"
SOURCE = "regional_catalogs"
SOURCE_CLASSIFICATION = "governance_dedicated_legal_contract_review_only"
SOURCE_FAMILY = "regional_catalog"
EVIDENCE_POLICY = "evidence_only_no_provider_use"
EXTERNAL_RESEARCH_EVIDENCE_ROLE = "review_context_only_not_source_authority"
LEGAL_REVIEW_AUTHORITY = "not_legal_advice_not_source_authority"
TERMS_EVIDENCE_ROLE = "review_context_only_not_terms_or_source_authority"
FINAL_GATE_DECISION = (
    "regional_catalog_dedicated_legal_contract_review_only_no_source_or_provider_use"
)
NEXT_RECOMMENDED_LANE = "regional_catalog_dedicated_legal_contract_review_closeout"

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

_GOVERNANCE_KEYS = frozenset(
    {
        "schema_version",
        "generated_on",
        "pr20_source_specific_terms_closeout_ref",
        "pr20_merged_pr",
        "pr20_merge_marker",
        "pr20_next_recommended_lane",
        "source",
        "source_classification",
        "source_family",
        "evidence_policy",
        "external_research_evidence_role",
        "legal_review_authority",
        "blocked_methods",
        "review_decision",
        "candidate_legal_contract_reviews",
        "premortem_dispositions",
        "role_agent_dispatch_status",
        "experiment_runner_policy",
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
        "provider_route_classification",
        "allowed_role",
        "next_required_review",
        "evidence_confidence",
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
        "legal_contract_decision",
        "legal_review_status",
        "contract_review_status",
        "legal_approval_status",
        "terms_evidence_role",
        "legal_review_authority",
        "provider_account_access_status",
        "contract_permission_status",
        "api_use_permission_status",
        "scraping_permission_status",
        "download_permission_status",
        "cache_permission_status",
        "redistribution_permission_status",
        "product_display_permission_status",
        "attribution_requirement_status",
        "source_authority_status",
        "blocking_reasons",
    }
)

_EXPECTED_INHERITED_ALLOWED_ROLE = "review_only_no_provider_use"
_EXPECTED_PR21_DECISION = "review_only_no_source_or_provider_use"
_EXPECTED_NEXT_REVIEW = "dedicated_legal_contract_review_required"
_EXPECTED_LEGAL_REVIEW_STATUS = "required_not_approved"
_EXPECTED_CONTRACT_REVIEW_STATUS = "required_not_approved"
_EXPECTED_LEGAL_APPROVAL_STATUS = "not_approved"
_EXPECTED_PROVIDER_ACCOUNT_ACCESS_STATUS = "unverified"
_EXPECTED_BLOCKED_UNRESOLVED = "blocked_unresolved"
_EXPECTED_BLOCKED_NOT_APPROVED = "blocked_not_approved"
_EXPECTED_BLOCKED_NOT_AUTHORITY = "blocked_not_authority"
_EXPECTED_REVIEW_DECISION = (
    "PR21 records dedicated legal-contract review requirements only. Every "
    "regional catalog candidate remains review-only with no source use, "
    "provider use, API calls, scraping, downloads, account access, paid use, "
    "database writes, cache authority, redistribution, runtime authority, "
    "product display, nutrition authority, source authority, or legal approval."
)
_EXPECTED_NOTES = (
    "PR21 is not legal advice and does not approve any external source, "
    "provider, API, account, cache, redistribution, product display, or "
    "nutrition authority. Public references, browser findings, connector "
    "outputs, documents, spreadsheets, reports, and images remain review "
    "context only."
)
_EXPECTED_BLOCKING_REASON = (
    "Dedicated legal-contract review is required before any source use, "
    "provider use, API access, scraping, downloads, account access, paid use, "
    "cache authority, redistribution, product display, nutrition authority, "
    "source authority, runtime authority, or database write can be approved."
)
_EXPECTED_PREMORTEM_DISPOSITIONS = (
    "PM-PR21-001 legal-review wording fixed by fail-closed decision vocabulary and unsafe prose rejection",
    "PM-PR21-002 candidate handoff drift fixed by exact PR20 candidate-order and status validation",
    "PM-PR21-003 evidence overreach fixed by review-context-only evidence fields and authority rejection",
    "PM-PR21-004 provenance false-green fixed by role-agent dispatch and Experiment Runner evidence requirements",
    "PM-PR21-005 type and coverage false-green fixed by focused tests, targeted mypy, and full make verify",
)
_EXPECTED_ROLE_AGENT_DISPATCH_STATUS = (
    "pre_open_full_dispatch_sequence_completed_before_implementation"
)
_EXPECTED_EXPERIMENT_RUNNER_POLICY = (
    "mandatory_oracle_only_after_real_diff_before_pr_open_recorded_in_pr_body_and_fixed_mapping"
)

_INHERITED_BLOCKED_STATUS_FIELDS = {
    "evidence_confidence": "low_unverified",
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
}

_AUTHORITY_TERMS = (
    r"network|api calls?|api use|scraping|downloads?|account access|"
    r"paid (?:source|provider|plan)|seller access|seller api|partner access|"
    r"partner api|provider use|provider integration|db writes?|database writes?|"
    r"cache authority|redistribution|runtime authority|product display|"
    r"nutrition authority|source authority|source use|public dataset authority|"
    r"legal review|legal approval|legal contract review|contract review|"
    r"contract permission|terms permission"
)
_UNSAFE_PROSE_RE = re.compile(
    rf"\b("
    rf"(?:{_AUTHORITY_TERMS})\s+(?:is\s+)?"
    rf"(?:allowed|approved|authorized|enabled|permitted|granted|complete|cleared)|"
    rf"(?:allowed|approved|authorized|enabled|permitted|granted|complete|cleared)"
    rf"\s+(?:{_AUTHORITY_TERMS})|"
    r"may scrape|may download|may call (?:the )?api|"
    r"report is authority|spreadsheet is authority|docx is authority|image is authority|"
    r"browser finding is authority|connector output is authority|"
    r"public references are source authority|terms authorize|license permits"
    r")\b",
    re.IGNORECASE,
)


class RegionalCatalogDedicatedLegalContractReviewError(ValueError):
    """Raised when the PR21 dedicated legal-contract review gate is invalid."""


@dataclass(frozen=True)
class RegionalCatalogDedicatedLegalContractReviewCandidate:
    """Validated PR21 legal-contract review row for one inherited candidate."""

    candidate_id: str
    candidate_name: str
    provider_route_classification: str
    allowed_role: str
    next_required_review: str
    evidence_confidence: str
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
    legal_contract_decision: str
    legal_review_status: str
    contract_review_status: str
    legal_approval_status: str
    terms_evidence_role: str
    legal_review_authority: str
    provider_account_access_status: str
    contract_permission_status: str
    api_use_permission_status: str
    scraping_permission_status: str
    download_permission_status: str
    cache_permission_status: str
    redistribution_permission_status: str
    product_display_permission_status: str
    attribution_requirement_status: str
    source_authority_status: str
    blocking_reasons: tuple[str, ...]


@dataclass(frozen=True)
class RegionalCatalogDedicatedLegalContractReviewGovernance:
    """Validated PR21 dedicated legal-contract review artifact."""

    schema_version: str
    generated_on: date
    pr20_source_specific_terms_closeout_ref: str
    pr20_merged_pr: int
    pr20_merge_marker: str
    pr20_next_recommended_lane: str
    source: str
    source_classification: str
    source_family: str
    evidence_policy: str
    external_research_evidence_role: str
    legal_review_authority: str
    blocked_methods: tuple[str, ...]
    review_decision: str
    candidate_legal_contract_reviews: tuple[
        RegionalCatalogDedicatedLegalContractReviewCandidate, ...
    ]
    premortem_dispositions: tuple[str, ...]
    role_agent_dispatch_status: str
    experiment_runner_policy: str
    next_recommended_lane: str
    final_gate_decision: str
    notes: str


def _legal_review_error(
    context: str,
    detail: str,
) -> RegionalCatalogDedicatedLegalContractReviewError:
    return RegionalCatalogDedicatedLegalContractReviewError(
        f"Invalid regional catalog dedicated legal-contract review {context}: {detail}"
    )


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _legal_review_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _legal_review_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _legal_review_error(context, f"missing non-empty string '{key}'")
    result = value.strip()
    if _UNSAFE_PROSE_RE.search(result):
        raise _legal_review_error(context, f"'{key}' must not approve source/provider use")
    return result


def _require_exact_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise _legal_review_error(context, f"missing non-empty string '{key}'")
    if _UNSAFE_PROSE_RE.search(value):
        raise _legal_review_error(context, f"'{key}' must not approve source/provider use")
    return value


def _require_int(data: dict[str, object], key: str, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _legal_review_error(context, f"'{key}' must be an integer")
    return value


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _legal_review_error(context, f"'{key}' must be a boolean")
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
        raise _legal_review_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _legal_review_error(context, f"'{key}[{index}]' must be a non-empty string")
        normalized = item.strip()
        if _UNSAFE_PROSE_RE.search(normalized):
            raise _legal_review_error(context, f"'{key}[{index}]' must not approve source use")
        if normalized in seen:
            raise _legal_review_error(context, f"'{key}' contains duplicate value {normalized!r}")
        seen.add(normalized)
        items.append(normalized)
    result = tuple(items)
    if not result:
        raise _legal_review_error(context, f"'{key}' must not be empty")
    if expected is not None and result != expected:
        raise _legal_review_error(context, f"'{key}' must be exactly: {', '.join(expected)}")
    return result


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _legal_review_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _legal_review_error(context, "generated_on must use YYYY-MM-DD") from exc


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
        raise _legal_review_error(
            context,
            "all unsafe flags must be false and file_only must be true: " + ", ".join(mismatches),
        )


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


def _validate_pr20_report(report: dict[str, object], context: str) -> None:
    if report.get("success") is not True:
        raise _legal_review_error(context, "PR20 closeout report must succeed")
    if report.get("next_recommended_lane") != PR20_NEXT_RECOMMENDED_LANE:
        raise _legal_review_error(context, "PR20 next_recommended_lane drifted")
    if report.get("final_gate_decision") != PR20_FINAL_GATE_DECISION:
        raise _legal_review_error(context, "PR20 final_gate_decision drifted")
    if report.get("candidate_ids") != list(EXPECTED_CANDIDATE_IDS):
        raise _legal_review_error(context, "PR20 candidate_ids drifted")
    for flag_name, expected_value in _SAFETY_FLAG_TEMPLATE.items():
        if report.get(flag_name) is not expected_value:
            raise _legal_review_error(context, f"PR20 safety flag drifted: {flag_name}")


def _derive_next_lane(
    gate: RegionalCatalogSourceSpecificTermsCloseoutGovernance,
    context: str,
) -> str:
    if tuple(row.candidate_id for row in gate.candidate_closeout_terms) != (EXPECTED_CANDIDATE_IDS):
        raise _legal_review_error(context, "PR20 candidate order drifted")
    for row in gate.candidate_closeout_terms:
        if row.allowed_role != _EXPECTED_INHERITED_ALLOWED_ROLE:
            raise _legal_review_error(context, f"PR20 allowed_role drifted: {row.candidate_id}")
        if row.next_required_review != _EXPECTED_NEXT_REVIEW:
            raise _legal_review_error(
                context,
                f"PR20 next_required_review drifted: {row.candidate_id}",
            )
        for field_name, expected_value in _INHERITED_BLOCKED_STATUS_FIELDS.items():
            if getattr(row, field_name) != expected_value:
                raise _legal_review_error(
                    context,
                    f"PR20 {field_name} drifted: {row.candidate_id}",
                )
    return NEXT_RECOMMENDED_LANE


def _candidate_legal_contract_reviews(
    data: dict[str, object],
    *,
    pr20_gate: RegionalCatalogSourceSpecificTermsCloseoutGovernance,
    context: str,
) -> tuple[RegionalCatalogDedicatedLegalContractReviewCandidate, ...]:
    value = data.get("candidate_legal_contract_reviews")
    if not isinstance(value, list):
        raise _legal_review_error(context, "candidate_legal_contract_reviews must be a list")
    pr20_candidates = {row.candidate_id: row for row in pr20_gate.candidate_closeout_terms}
    rows: list[RegionalCatalogDedicatedLegalContractReviewCandidate] = []
    seen: set[str] = set()
    for index, raw_candidate in enumerate(value):
        candidate_context = f"{context}.candidate_legal_contract_reviews[{index}]"
        candidate = _require_mapping(raw_candidate, candidate_context)
        unexpected = sorted(set(candidate) - _CANDIDATE_KEYS)
        if unexpected:
            raise _legal_review_error(
                candidate_context,
                "unexpected candidate keys: " + ", ".join(unexpected),
            )
        candidate_id = _require_string(candidate, "candidate_id", candidate_context)
        if candidate_id not in EXPECTED_CANDIDATE_IDS:
            raise _legal_review_error(candidate_context, f"unknown candidate_id {candidate_id!r}")
        if candidate_id in seen:
            raise _legal_review_error(
                context,
                f"candidate_legal_contract_reviews contains duplicate {candidate_id}",
            )
        seen.add(candidate_id)
        pr20_candidate = pr20_candidates[candidate_id]
        _validate_candidate_against_pr20(candidate, pr20_candidate, candidate_context)
        legal_contract_decision = _require_expected_candidate_string(
            candidate,
            "legal_contract_decision",
            _EXPECTED_PR21_DECISION,
            candidate_context,
        )
        legal_review_status = _require_expected_candidate_string(
            candidate,
            "legal_review_status",
            _EXPECTED_LEGAL_REVIEW_STATUS,
            candidate_context,
        )
        contract_review_status = _require_expected_candidate_string(
            candidate,
            "contract_review_status",
            _EXPECTED_CONTRACT_REVIEW_STATUS,
            candidate_context,
        )
        legal_approval_status = _require_expected_candidate_string(
            candidate,
            "legal_approval_status",
            _EXPECTED_LEGAL_APPROVAL_STATUS,
            candidate_context,
        )
        terms_evidence_role = _require_expected_candidate_string(
            candidate,
            "terms_evidence_role",
            TERMS_EVIDENCE_ROLE,
            candidate_context,
        )
        legal_review_authority = _require_expected_candidate_string(
            candidate,
            "legal_review_authority",
            LEGAL_REVIEW_AUTHORITY,
            candidate_context,
        )
        provider_account_access_status = _require_expected_candidate_string(
            candidate,
            "provider_account_access_status",
            _EXPECTED_PROVIDER_ACCOUNT_ACCESS_STATUS,
            candidate_context,
        )
        contract_permission_status = _require_expected_candidate_string(
            candidate,
            "contract_permission_status",
            _EXPECTED_BLOCKED_UNRESOLVED,
            candidate_context,
        )
        api_use_permission_status = _require_expected_candidate_string(
            candidate,
            "api_use_permission_status",
            _EXPECTED_BLOCKED_NOT_APPROVED,
            candidate_context,
        )
        scraping_permission_status = _require_expected_candidate_string(
            candidate,
            "scraping_permission_status",
            _EXPECTED_BLOCKED_NOT_APPROVED,
            candidate_context,
        )
        download_permission_status = _require_expected_candidate_string(
            candidate,
            "download_permission_status",
            _EXPECTED_BLOCKED_NOT_APPROVED,
            candidate_context,
        )
        cache_permission_status = _require_expected_candidate_string(
            candidate,
            "cache_permission_status",
            _EXPECTED_BLOCKED_UNRESOLVED,
            candidate_context,
        )
        redistribution_permission_status = _require_expected_candidate_string(
            candidate,
            "redistribution_permission_status",
            _EXPECTED_BLOCKED_UNRESOLVED,
            candidate_context,
        )
        product_display_permission_status = _require_expected_candidate_string(
            candidate,
            "product_display_permission_status",
            _EXPECTED_BLOCKED_UNRESOLVED,
            candidate_context,
        )
        attribution_requirement_status = _require_expected_candidate_string(
            candidate,
            "attribution_requirement_status",
            _EXPECTED_BLOCKED_UNRESOLVED,
            candidate_context,
        )
        source_authority_status = _require_expected_candidate_string(
            candidate,
            "source_authority_status",
            _EXPECTED_BLOCKED_NOT_AUTHORITY,
            candidate_context,
        )
        blocking_reasons = _require_string_tuple(candidate, "blocking_reasons", candidate_context)
        if blocking_reasons != (_EXPECTED_BLOCKING_REASON,):
            raise _legal_review_error(candidate_context, "blocking_reasons drifted")
        rows.append(
            RegionalCatalogDedicatedLegalContractReviewCandidate(
                candidate_id=candidate_id,
                candidate_name=pr20_candidate.candidate_name,
                provider_route_classification=pr20_candidate.provider_route_classification,
                allowed_role=pr20_candidate.allowed_role,
                next_required_review=pr20_candidate.next_required_review,
                evidence_confidence=pr20_candidate.evidence_confidence,
                terms_document_identity_status=pr20_candidate.terms_document_identity_status,
                account_access_status=pr20_candidate.account_access_status,
                retrieval_contract_status=pr20_candidate.retrieval_contract_status,
                license_status=pr20_candidate.license_status,
                cache_terms_status=pr20_candidate.cache_terms_status,
                redistribution_terms_status=pr20_candidate.redistribution_terms_status,
                display_terms_status=pr20_candidate.display_terms_status,
                attribution_terms_status=pr20_candidate.attribution_terms_status,
                nutrition_authority_status=pr20_candidate.nutrition_authority_status,
                product_authority_status=pr20_candidate.product_authority_status,
                legal_contract_decision=legal_contract_decision,
                legal_review_status=legal_review_status,
                contract_review_status=contract_review_status,
                legal_approval_status=legal_approval_status,
                terms_evidence_role=terms_evidence_role,
                legal_review_authority=legal_review_authority,
                provider_account_access_status=provider_account_access_status,
                contract_permission_status=contract_permission_status,
                api_use_permission_status=api_use_permission_status,
                scraping_permission_status=scraping_permission_status,
                download_permission_status=download_permission_status,
                cache_permission_status=cache_permission_status,
                redistribution_permission_status=redistribution_permission_status,
                product_display_permission_status=product_display_permission_status,
                attribution_requirement_status=attribution_requirement_status,
                source_authority_status=source_authority_status,
                blocking_reasons=blocking_reasons,
            )
        )
    observed_ids = tuple(row.candidate_id for row in rows)
    if observed_ids != EXPECTED_CANDIDATE_IDS:
        raise _legal_review_error(
            context,
            "candidate_legal_contract_reviews must preserve PR20 candidate order: "
            + ", ".join(EXPECTED_CANDIDATE_IDS),
        )
    return tuple(rows)


def _require_expected_candidate_string(
    candidate: dict[str, object],
    field_name: str,
    expected_value: str,
    context: str,
) -> str:
    observed = _require_string(candidate, field_name, context)
    if observed != expected_value:
        raise _legal_review_error(context, f"{field_name} drifted")
    return observed


def _validate_candidate_against_pr20(
    candidate: dict[str, object],
    pr20_candidate: object,
    context: str,
) -> None:
    inherited_fields = {
        "candidate_name": getattr(pr20_candidate, "candidate_name"),
        "provider_route_classification": getattr(pr20_candidate, "provider_route_classification"),
        "allowed_role": getattr(pr20_candidate, "allowed_role"),
        "next_required_review": getattr(pr20_candidate, "next_required_review"),
        "evidence_confidence": getattr(pr20_candidate, "evidence_confidence"),
        "terms_document_identity_status": getattr(pr20_candidate, "terms_document_identity_status"),
        "account_access_status": getattr(pr20_candidate, "account_access_status"),
        "retrieval_contract_status": getattr(pr20_candidate, "retrieval_contract_status"),
        "license_status": getattr(pr20_candidate, "license_status"),
        "cache_terms_status": getattr(pr20_candidate, "cache_terms_status"),
        "redistribution_terms_status": getattr(pr20_candidate, "redistribution_terms_status"),
        "display_terms_status": getattr(pr20_candidate, "display_terms_status"),
        "attribution_terms_status": getattr(pr20_candidate, "attribution_terms_status"),
        "nutrition_authority_status": getattr(pr20_candidate, "nutrition_authority_status"),
        "product_authority_status": getattr(pr20_candidate, "product_authority_status"),
    }
    for field_name, expected_value in inherited_fields.items():
        if _require_string(candidate, field_name, context) != expected_value:
            raise _legal_review_error(context, f"{field_name} must match PR20")


def parse_regional_catalog_dedicated_legal_contract_review_governance(
    payload: object,
    *,
    pr20_report: dict[str, object],
    pr20_gate: RegionalCatalogSourceSpecificTermsCloseoutGovernance,
    expected_pr20_closeout_ref: str | None = None,
    context: str = "<regional-catalog-dedicated-legal-contract-review>",
) -> RegionalCatalogDedicatedLegalContractReviewGovernance:
    """Parse and validate the PR21 dedicated legal-contract review artifact."""

    _validate_pr20_report(pr20_report, context)
    derived_next_lane = _derive_next_lane(pr20_gate, context)
    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _GOVERNANCE_KEYS)
    if unexpected_keys:
        raise _legal_review_error(context, f"unexpected keys: {', '.join(unexpected_keys)}")

    schema_version = _require_string(data, "schema_version", context)
    if not _SCHEMA_RE.fullmatch(schema_version):
        raise _legal_review_error(
            context,
            "schema_version must look like "
            "food-data-regional-catalog-dedicated-legal-contract-review.vN",
        )
    generated_on = _parse_date(_require_string(data, "generated_on", context), context)
    pr20_ref = _require_string(data, "pr20_source_specific_terms_closeout_ref", context)
    if expected_pr20_closeout_ref is not None and pr20_ref != expected_pr20_closeout_ref:
        raise _legal_review_error(
            context,
            f"pr20_source_specific_terms_closeout_ref must be {expected_pr20_closeout_ref!r}",
        )
    if _require_int(data, "pr20_merged_pr", context) != PR20_MERGED_PR:
        raise _legal_review_error(context, f"pr20_merged_pr must be {PR20_MERGED_PR}")
    if _require_string(data, "pr20_merge_marker", context) != PR20_MERGE_MARKER:
        raise _legal_review_error(context, "pr20_merge_marker drifted")
    if _require_string(data, "pr20_next_recommended_lane", context) != (PR20_NEXT_RECOMMENDED_LANE):
        raise _legal_review_error(context, "pr20_next_recommended_lane drifted")
    if _require_string(data, "source", context) != SOURCE:
        raise _legal_review_error(context, f"source must be {SOURCE}")
    if _require_string(data, "source_classification", context) != SOURCE_CLASSIFICATION:
        raise _legal_review_error(context, f"source_classification must be {SOURCE_CLASSIFICATION}")
    if _require_string(data, "source_family", context) != SOURCE_FAMILY:
        raise _legal_review_error(context, f"source_family must be {SOURCE_FAMILY}")
    if _require_string(data, "evidence_policy", context) != EVIDENCE_POLICY:
        raise _legal_review_error(context, f"evidence_policy must be {EVIDENCE_POLICY}")
    external_role = _require_string(data, "external_research_evidence_role", context)
    if external_role != EXTERNAL_RESEARCH_EVIDENCE_ROLE:
        raise _legal_review_error(
            context,
            "external_research_evidence_role must be review_context_only_not_source_authority",
        )
    legal_review_authority = _require_string(data, "legal_review_authority", context)
    if legal_review_authority != LEGAL_REVIEW_AUTHORITY:
        raise _legal_review_error(context, "legal_review_authority drifted")
    blocked_methods = _require_string_tuple(
        data,
        "blocked_methods",
        context,
        expected=BLOCKED_METHODS,
    )
    review_decision = _require_exact_string(data, "review_decision", context)
    if review_decision != _EXPECTED_REVIEW_DECISION:
        raise _legal_review_error(context, "review_decision must use controlled text")
    _require_safety_flags(data, context)
    candidate_legal_contract_reviews = _candidate_legal_contract_reviews(
        data,
        pr20_gate=pr20_gate,
        context=context,
    )
    premortem_dispositions = _require_string_tuple(
        data,
        "premortem_dispositions",
        context,
        expected=_EXPECTED_PREMORTEM_DISPOSITIONS,
    )
    role_agent_dispatch_status = _require_string(data, "role_agent_dispatch_status", context)
    if role_agent_dispatch_status != _EXPECTED_ROLE_AGENT_DISPATCH_STATUS:
        raise _legal_review_error(context, "role_agent_dispatch_status drifted")
    experiment_runner_policy = _require_string(data, "experiment_runner_policy", context)
    if experiment_runner_policy != _EXPECTED_EXPERIMENT_RUNNER_POLICY:
        raise _legal_review_error(context, "experiment_runner_policy drifted")
    if _require_string(data, "next_recommended_lane", context) != derived_next_lane:
        raise _legal_review_error(
            context,
            f"next_recommended_lane must be derived as {derived_next_lane}",
        )
    if _require_string(data, "final_gate_decision", context) != FINAL_GATE_DECISION:
        raise _legal_review_error(context, f"final_gate_decision must be {FINAL_GATE_DECISION}")
    notes = _require_exact_string(data, "notes", context)
    if notes != _EXPECTED_NOTES:
        raise _legal_review_error(context, "notes must use controlled text")

    return RegionalCatalogDedicatedLegalContractReviewGovernance(
        schema_version=schema_version,
        generated_on=generated_on,
        pr20_source_specific_terms_closeout_ref=pr20_ref,
        pr20_merged_pr=PR20_MERGED_PR,
        pr20_merge_marker=PR20_MERGE_MARKER,
        pr20_next_recommended_lane=PR20_NEXT_RECOMMENDED_LANE,
        source=SOURCE,
        source_classification=SOURCE_CLASSIFICATION,
        source_family=SOURCE_FAMILY,
        evidence_policy=EVIDENCE_POLICY,
        external_research_evidence_role=external_role,
        legal_review_authority=legal_review_authority,
        blocked_methods=blocked_methods,
        review_decision=review_decision,
        candidate_legal_contract_reviews=candidate_legal_contract_reviews,
        premortem_dispositions=premortem_dispositions,
        role_agent_dispatch_status=role_agent_dispatch_status,
        experiment_runner_policy=experiment_runner_policy,
        next_recommended_lane=derived_next_lane,
        final_gate_decision=FINAL_GATE_DECISION,
        notes=notes,
    )


def load_regional_catalog_dedicated_legal_contract_review_governance(
    legal_review_path: Path | str,
    *,
    pr20_report: dict[str, object],
    pr20_gate: RegionalCatalogSourceSpecificTermsCloseoutGovernance,
    expected_pr20_closeout_ref: str | None = None,
) -> RegionalCatalogDedicatedLegalContractReviewGovernance:
    """Load and validate a PR21 dedicated legal-contract review artifact."""

    path = Path(legal_review_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RegionalCatalogDedicatedLegalContractReviewError(
            f"Cannot read regional catalog dedicated legal-contract review {path}: {exc}"
        ) from exc
    return parse_regional_catalog_dedicated_legal_contract_review_governance(
        payload,
        pr20_report=pr20_report,
        pr20_gate=pr20_gate,
        expected_pr20_closeout_ref=expected_pr20_closeout_ref,
        context=str(path),
    )


def build_regional_catalog_dedicated_legal_contract_review_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    coverage_path: Path | str,
    recipe_dish_corpus_path: Path | str,
    preference_mapping_path: Path | str,
    pr16_closeout_path: Path | str,
    pr17_identity_path: Path | str,
    pr18_provider_terms_path: Path | str,
    pr19_source_specific_terms_path: Path | str,
    pr20_closeout_path: Path | str,
    legal_review_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR21 legal-contract review gate."""

    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    expected_coverage_ref = _relative_repo_path(coverage_path)
    expected_pr16_ref = _relative_repo_path(pr16_closeout_path)
    expected_pr17_ref = _relative_repo_path(pr17_identity_path)
    expected_pr18_ref = _relative_repo_path(pr18_provider_terms_path)
    expected_pr19_ref = _relative_repo_path(pr19_source_specific_terms_path)
    expected_pr20_ref = _relative_repo_path(pr20_closeout_path)
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
    report.update(_observed_safety_flags(legal_review_path))
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
        pr19_report = build_regional_catalog_source_specific_terms_report(
            catalog_path=catalog_path,
            onboarding_path=onboarding_path,
            coverage_path=coverage_path,
            recipe_dish_corpus_path=recipe_dish_corpus_path,
            preference_mapping_path=preference_mapping_path,
            pr16_closeout_path=pr16_closeout_path,
            pr17_identity_path=pr17_identity_path,
            pr18_provider_terms_path=pr18_provider_terms_path,
            source_specific_terms_path=pr19_source_specific_terms_path,
        )
        pr19_gate = load_regional_catalog_source_specific_terms_governance(
            pr19_source_specific_terms_path,
            pr18_report=pr18_report,
            pr18_gate=pr18_gate,
            expected_pr18_provider_terms_ref=expected_pr18_ref,
        )
        pr20_report = build_regional_catalog_source_specific_terms_closeout_report(
            catalog_path=catalog_path,
            onboarding_path=onboarding_path,
            coverage_path=coverage_path,
            recipe_dish_corpus_path=recipe_dish_corpus_path,
            preference_mapping_path=preference_mapping_path,
            pr16_closeout_path=pr16_closeout_path,
            pr17_identity_path=pr17_identity_path,
            pr18_provider_terms_path=pr18_provider_terms_path,
            pr19_source_specific_terms_path=pr19_source_specific_terms_path,
            closeout_path=pr20_closeout_path,
        )
        pr20_gate = load_regional_catalog_source_specific_terms_closeout_governance(
            pr20_closeout_path,
            pr19_report=pr19_report,
            pr19_gate=pr19_gate,
            expected_pr19_source_specific_terms_ref=expected_pr19_ref,
        )
        gate = load_regional_catalog_dedicated_legal_contract_review_governance(
            legal_review_path,
            pr20_report=pr20_report,
            pr20_gate=pr20_gate,
            expected_pr20_closeout_ref=expected_pr20_ref,
        )
    except (
        RegionalCatalogDedicatedLegalContractReviewError,
        RegionalCatalogSourceSpecificTermsCloseoutError,
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
            "pr20_source_specific_terms_closeout_ref": (
                gate.pr20_source_specific_terms_closeout_ref
            ),
            "pr20_merged_pr": gate.pr20_merged_pr,
            "pr20_merge_marker": gate.pr20_merge_marker,
            "pr20_next_recommended_lane": gate.pr20_next_recommended_lane,
            "evidence_policy": gate.evidence_policy,
            "external_research_evidence_role": gate.external_research_evidence_role,
            "legal_review_authority": gate.legal_review_authority,
            "review_decision": gate.review_decision,
            "candidate_decisions": {
                row.candidate_id: row.legal_contract_decision
                for row in gate.candidate_legal_contract_reviews
            },
            "candidate_next_required_review": {
                row.candidate_id: row.next_required_review
                for row in gate.candidate_legal_contract_reviews
            },
            "candidate_evidence_confidence": {
                row.candidate_id: row.evidence_confidence
                for row in gate.candidate_legal_contract_reviews
            },
            "candidate_legal_review_status": {
                row.candidate_id: row.legal_review_status
                for row in gate.candidate_legal_contract_reviews
            },
            "candidate_legal_approval_status": {
                row.candidate_id: row.legal_approval_status
                for row in gate.candidate_legal_contract_reviews
            },
            "role_agent_dispatch_status": gate.role_agent_dispatch_status,
            "experiment_runner_policy": gate.experiment_runner_policy,
        }
    )
    return report
