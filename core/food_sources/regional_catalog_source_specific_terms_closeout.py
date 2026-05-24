"""Deterministic file-only PR20 source-specific terms closeout gate."""

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
    FINAL_GATE_DECISION as PR19_FINAL_GATE_DECISION,
    NEXT_RECOMMENDED_LANE as PR19_NEXT_RECOMMENDED_LANE,
    RegionalCatalogSourceSpecificTermsError,
    RegionalCatalogSourceSpecificTermsGovernance,
    build_regional_catalog_source_specific_terms_report,
    load_regional_catalog_source_specific_terms_governance,
)
from core.food_sources.source_catalog import SourceCatalogError, load_source_catalog
from core.food_sources.source_gap_audit import SourceGapAuditError, load_source_gap_audit
from core.food_sources.source_onboarding import SourceOnboardingError, load_source_onboarding

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_RE = re.compile(r"^food-data-regional-catalog-source-specific-terms-closeout\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PR19_REF = (
    "docs/architecture/"
    "FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_REVIEW_PR19_2026-05-21.json"
)
PR19_MERGED_PR = 1793
PR19_MERGE_MARKER = "PR #1793 merged before PR20 scope lock"
SOURCE = "regional_catalogs"
SOURCE_CLASSIFICATION = "governance_closeout_only"
SOURCE_FAMILY = "regional_catalog"
EVIDENCE_POLICY = "evidence_only_no_provider_use"
EXTERNAL_RESEARCH_EVIDENCE_ROLE = "review_context_only_not_source_authority"
FINAL_GATE_DECISION = "regional_catalog_source_specific_terms_closeout_only_no_provider_use"
NEXT_RECOMMENDED_LANE = "regional_catalog_dedicated_legal_contract_review"

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
        "pr19_source_specific_terms_ref",
        "pr19_merged_pr",
        "pr19_merge_marker",
        "pr19_next_recommended_lane",
        "source",
        "source_classification",
        "source_family",
        "evidence_policy",
        "external_research_evidence_role",
        "blocked_methods",
        "closeout_decision",
        "candidate_closeout_terms",
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
        "blocking_reasons",
        "closeout_status",
        "legal_contract_review_status",
    }
)

_EXPECTED_ALLOWED_ROLE = "review_only_no_provider_use"
_EXPECTED_NEXT_REVIEW = "dedicated_legal_contract_review_required"
_EXPECTED_CLOSEOUT_STATUS = "pr19_closed_review_only_no_provider_use"
_EXPECTED_LEGAL_CONTRACT_STATUS = "required_before_any_source_or_provider_use"
_EXPECTED_BLOCKING_REASON = (
    "PR19 left terms-document identity, account access, retrieval contract, "
    "license, cache, redistribution, display, attribution, product authority, "
    "and nutrition authority unverified or blocked."
)
_EXPECTED_CLOSEOUT_DECISION = (
    "PR20 closes PR19 source-specific terms review as file-only governance. "
    "Every inherited regional catalog candidate remains review-only with no "
    "provider use, API calls, scraping, downloads, account access, database "
    "writes, cache authority, redistribution, product display, source "
    "authority, or nutrition authority."
)
_EXPECTED_NOTES = (
    "PR20 is a closeout packet only. Attached reports, spreadsheets, documents, "
    "images, browser findings, public references, and connector outputs remain "
    "review context only and do not become source, terms, license, product, "
    "or nutrition authority."
)
_EXPECTED_PREMORTEM_DISPOSITIONS = (
    "PM-PR20-001 authority-escalation wording fixed by unsafe flag and prose rejection",
    "PM-PR20-002 PR19 legal-contract blockers fixed by exact candidate invariant checks",
    "PM-PR20-003 role-agent under-dispatch fixed by captured full role sequence",
    "PM-PR20-004 typecheck gap fixed by targeted mypy gate",
)
_EXPECTED_ROLE_AGENT_DISPATCH_STATUS = (
    "pre_open_full_requested_role_sequence_captured_before_implementation"
)
_EXPECTED_EXPERIMENT_RUNNER_POLICY = (
    "mandatory_after_real_diff_before_pr_open_recorded_in_pr_body_and_fixed_mapping"
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

_AUTHORITY_TERMS = (
    r"network|api calls?|api use|scraping|downloads?|account access|"
    r"paid (?:source|provider|plan)|seller access|seller api|partner access|"
    r"partner api|provider use|provider integration|db writes?|database writes?|"
    r"cache authority|redistribution|runtime authority|product display|"
    r"nutrition authority|source authority|source use|public dataset authority"
)
_UNSAFE_PROSE_RE = re.compile(
    rf"\b("
    rf"(?:{_AUTHORITY_TERMS})\s+(?:is\s+)?(?:allowed|approved|authorized|enabled|permitted|granted)|"
    rf"(?:allowed|approved|authorized|enabled|permitted|granted)\s+(?:{_AUTHORITY_TERMS})|"
    r"may scrape|may download|may call (?:the )?api|"
    r"report is authority|spreadsheet is authority|docx is authority|image is authority|"
    r"browser finding is authority|connector output is authority|"
    r"public references are source authority|dedicated legal review complete"
    r")\b",
    re.IGNORECASE,
)


class RegionalCatalogSourceSpecificTermsCloseoutError(ValueError):
    """Raised when the PR20 source-specific terms closeout gate is invalid."""


@dataclass(frozen=True)
class RegionalCatalogSourceSpecificTermsCloseoutCandidate:
    """Validated PR20 closeout row for an inherited PR19 candidate."""

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
    blocking_reasons: tuple[str, ...]
    closeout_status: str
    legal_contract_review_status: str


@dataclass(frozen=True)
class RegionalCatalogSourceSpecificTermsCloseoutGovernance:
    """Validated PR20 source-specific terms closeout artifact."""

    schema_version: str
    generated_on: date
    pr19_source_specific_terms_ref: str
    pr19_merged_pr: int
    pr19_merge_marker: str
    pr19_next_recommended_lane: str
    source: str
    source_classification: str
    source_family: str
    evidence_policy: str
    external_research_evidence_role: str
    blocked_methods: tuple[str, ...]
    closeout_decision: str
    candidate_closeout_terms: tuple[RegionalCatalogSourceSpecificTermsCloseoutCandidate, ...]
    premortem_dispositions: tuple[str, ...]
    role_agent_dispatch_status: str
    experiment_runner_policy: str
    next_recommended_lane: str
    final_gate_decision: str
    notes: str


def _closeout_error(context: str, detail: str) -> RegionalCatalogSourceSpecificTermsCloseoutError:
    return RegionalCatalogSourceSpecificTermsCloseoutError(
        f"Invalid regional catalog source-specific terms closeout {context}: {detail}"
    )


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _closeout_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _closeout_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _closeout_error(context, f"missing non-empty string '{key}'")
    result = value.strip()
    if _UNSAFE_PROSE_RE.search(result):
        raise _closeout_error(context, f"'{key}' must not approve source/provider use")
    return result


def _require_exact_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise _closeout_error(context, f"missing non-empty string '{key}'")
    if _UNSAFE_PROSE_RE.search(value):
        raise _closeout_error(context, f"'{key}' must not approve source/provider use")
    return value


def _require_int(data: dict[str, object], key: str, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _closeout_error(context, f"'{key}' must be an integer")
    return value


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _closeout_error(context, f"'{key}' must be a boolean")
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
        raise _closeout_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _closeout_error(context, f"'{key}[{index}]' must be a non-empty string")
        normalized = item.strip()
        if _UNSAFE_PROSE_RE.search(normalized):
            raise _closeout_error(context, f"'{key}[{index}]' must not approve source/provider use")
        if normalized in seen:
            raise _closeout_error(context, f"'{key}' contains duplicate value {normalized!r}")
        seen.add(normalized)
        items.append(normalized)
    result = tuple(items)
    if not result:
        raise _closeout_error(context, f"'{key}' must not be empty")
    if expected is not None and result != expected:
        raise _closeout_error(context, f"'{key}' must be exactly: {', '.join(expected)}")
    return result


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _closeout_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _closeout_error(context, "generated_on must use YYYY-MM-DD") from exc


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
        raise _closeout_error(
            context,
            "all unsafe flags must be false and file_only must be true: " + ", ".join(mismatches),
        )


def _validate_pr19_report(report: dict[str, object], context: str) -> None:
    if report.get("success") is not True:
        raise _closeout_error(context, "PR19 source-specific terms report must succeed")
    if report.get("next_recommended_lane") != PR19_NEXT_RECOMMENDED_LANE:
        raise _closeout_error(context, "PR19 next_recommended_lane drifted")
    if report.get("final_gate_decision") != PR19_FINAL_GATE_DECISION:
        raise _closeout_error(context, "PR19 final_gate_decision drifted")
    if report.get("candidate_ids") != list(EXPECTED_CANDIDATE_IDS):
        raise _closeout_error(context, "PR19 candidate_ids drifted")
    for flag_name in _SAFETY_FLAG_TEMPLATE:
        if flag_name == "file_only":
            if report.get(flag_name) is not True:
                raise _closeout_error(context, "PR19 file_only flag drifted")
        elif report.get(flag_name) is not False:
            raise _closeout_error(context, f"PR19 unsafe flag drifted: {flag_name}")


def _derive_next_lane(gate: RegionalCatalogSourceSpecificTermsGovernance, context: str) -> str:
    if (
        tuple(row.candidate_id for row in gate.candidate_source_specific_terms)
        != EXPECTED_CANDIDATE_IDS
    ):
        raise _closeout_error(context, "PR19 candidate order drifted")
    for row in gate.candidate_source_specific_terms:
        if row.allowed_role != _EXPECTED_ALLOWED_ROLE:
            raise _closeout_error(context, f"PR19 allowed_role drifted: {row.candidate_id}")
        if row.next_required_review != _EXPECTED_NEXT_REVIEW:
            raise _closeout_error(context, f"PR19 next_required_review drifted: {row.candidate_id}")
        for field_name, expected_value in _BLOCKED_STATUS_FIELDS.items():
            observed_value = getattr(row, field_name)
            if observed_value != expected_value:
                raise _closeout_error(context, f"PR19 {field_name} drifted: {row.candidate_id}")
    return NEXT_RECOMMENDED_LANE


def _candidate_closeout_terms(
    data: dict[str, object],
    *,
    pr19_gate: RegionalCatalogSourceSpecificTermsGovernance,
    context: str,
) -> tuple[RegionalCatalogSourceSpecificTermsCloseoutCandidate, ...]:
    value = data.get("candidate_closeout_terms")
    if not isinstance(value, list):
        raise _closeout_error(context, "candidate_closeout_terms must be a list")
    pr19_candidates = {row.candidate_id: row for row in pr19_gate.candidate_source_specific_terms}
    rows: list[RegionalCatalogSourceSpecificTermsCloseoutCandidate] = []
    seen: set[str] = set()
    for index, raw_candidate in enumerate(value):
        candidate_context = f"{context}.candidate_closeout_terms[{index}]"
        candidate = _require_mapping(raw_candidate, candidate_context)
        unexpected = sorted(set(candidate) - _CANDIDATE_KEYS)
        if unexpected:
            raise _closeout_error(
                candidate_context, "unexpected candidate keys: " + ", ".join(unexpected)
            )
        candidate_id = _require_string(candidate, "candidate_id", candidate_context)
        if candidate_id not in EXPECTED_CANDIDATE_IDS:
            raise _closeout_error(candidate_context, f"unknown candidate_id {candidate_id!r}")
        if candidate_id in seen:
            raise _closeout_error(
                context, f"candidate_closeout_terms contains duplicate {candidate_id}"
            )
        seen.add(candidate_id)
        pr19_candidate = pr19_candidates[candidate_id]
        _validate_candidate_against_pr19(candidate, pr19_candidate, candidate_context)
        blocking_reasons = _require_string_tuple(candidate, "blocking_reasons", candidate_context)
        if blocking_reasons != (_EXPECTED_BLOCKING_REASON,):
            raise _closeout_error(candidate_context, "blocking_reasons drifted")
        closeout_status = _require_string(candidate, "closeout_status", candidate_context)
        if closeout_status != _EXPECTED_CLOSEOUT_STATUS:
            raise _closeout_error(candidate_context, "closeout_status drifted")
        legal_contract_review_status = _require_string(
            candidate, "legal_contract_review_status", candidate_context
        )
        if legal_contract_review_status != _EXPECTED_LEGAL_CONTRACT_STATUS:
            raise _closeout_error(candidate_context, "legal_contract_review_status drifted")
        rows.append(
            RegionalCatalogSourceSpecificTermsCloseoutCandidate(
                candidate_id=candidate_id,
                candidate_name=pr19_candidate.candidate_name,
                provider_route_classification=pr19_candidate.provider_route_classification,
                allowed_role=pr19_candidate.allowed_role,
                next_required_review=pr19_candidate.next_required_review,
                evidence_confidence=pr19_candidate.evidence_confidence,
                terms_document_identity_status=pr19_candidate.terms_document_identity_status,
                account_access_status=pr19_candidate.account_access_status,
                retrieval_contract_status=pr19_candidate.retrieval_contract_status,
                license_status=pr19_candidate.license_status,
                cache_terms_status=pr19_candidate.cache_terms_status,
                redistribution_terms_status=pr19_candidate.redistribution_terms_status,
                display_terms_status=pr19_candidate.display_terms_status,
                attribution_terms_status=pr19_candidate.attribution_terms_status,
                nutrition_authority_status=pr19_candidate.nutrition_authority_status,
                product_authority_status=pr19_candidate.product_authority_status,
                blocking_reasons=blocking_reasons,
                closeout_status=closeout_status,
                legal_contract_review_status=legal_contract_review_status,
            )
        )
    observed_ids = tuple(row.candidate_id for row in rows)
    if observed_ids != EXPECTED_CANDIDATE_IDS:
        raise _closeout_error(
            context,
            "candidate_closeout_terms must preserve PR19 candidate order: "
            + ", ".join(EXPECTED_CANDIDATE_IDS),
        )
    return tuple(rows)


def _validate_candidate_against_pr19(
    candidate: dict[str, object],
    pr19_candidate: object,
    context: str,
) -> None:
    inherited_fields = {
        "candidate_name": getattr(pr19_candidate, "candidate_name"),
        "provider_route_classification": getattr(pr19_candidate, "provider_route_classification"),
        "allowed_role": getattr(pr19_candidate, "allowed_role"),
        "next_required_review": getattr(pr19_candidate, "next_required_review"),
        "evidence_confidence": getattr(pr19_candidate, "evidence_confidence"),
        "terms_document_identity_status": getattr(pr19_candidate, "terms_document_identity_status"),
        "account_access_status": getattr(pr19_candidate, "account_access_status"),
        "retrieval_contract_status": getattr(pr19_candidate, "retrieval_contract_status"),
        "license_status": getattr(pr19_candidate, "license_status"),
        "cache_terms_status": getattr(pr19_candidate, "cache_terms_status"),
        "redistribution_terms_status": getattr(pr19_candidate, "redistribution_terms_status"),
        "display_terms_status": getattr(pr19_candidate, "display_terms_status"),
        "attribution_terms_status": getattr(pr19_candidate, "attribution_terms_status"),
        "nutrition_authority_status": getattr(pr19_candidate, "nutrition_authority_status"),
        "product_authority_status": getattr(pr19_candidate, "product_authority_status"),
    }
    for field_name, expected_value in inherited_fields.items():
        if _require_string(candidate, field_name, context) != expected_value:
            raise _closeout_error(context, f"{field_name} must match PR19")


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


def parse_regional_catalog_source_specific_terms_closeout_governance(
    payload: object,
    *,
    pr19_report: dict[str, object],
    pr19_gate: RegionalCatalogSourceSpecificTermsGovernance,
    expected_pr19_source_specific_terms_ref: str | None = None,
    context: str = "<regional-catalog-source-specific-terms-closeout>",
) -> RegionalCatalogSourceSpecificTermsCloseoutGovernance:
    """Parse and validate the PR20 source-specific terms closeout artifact."""

    _validate_pr19_report(pr19_report, context)
    derived_next_lane = _derive_next_lane(pr19_gate, context)
    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _GOVERNANCE_KEYS)
    if unexpected_keys:
        raise _closeout_error(context, f"unexpected keys: {', '.join(unexpected_keys)}")

    schema_version = _require_string(data, "schema_version", context)
    if not _SCHEMA_RE.fullmatch(schema_version):
        raise _closeout_error(
            context,
            "schema_version must look like "
            "food-data-regional-catalog-source-specific-terms-closeout.vN",
        )
    generated_on = _parse_date(_require_string(data, "generated_on", context), context)
    pr19_ref = _require_string(data, "pr19_source_specific_terms_ref", context)
    if expected_pr19_source_specific_terms_ref is not None and pr19_ref != (
        expected_pr19_source_specific_terms_ref
    ):
        raise _closeout_error(
            context,
            f"pr19_source_specific_terms_ref must be {expected_pr19_source_specific_terms_ref!r}",
        )
    if _require_int(data, "pr19_merged_pr", context) != PR19_MERGED_PR:
        raise _closeout_error(context, f"pr19_merged_pr must be {PR19_MERGED_PR}")
    if _require_string(data, "pr19_merge_marker", context) != PR19_MERGE_MARKER:
        raise _closeout_error(context, "pr19_merge_marker drifted")
    if _require_string(data, "pr19_next_recommended_lane", context) != PR19_NEXT_RECOMMENDED_LANE:
        raise _closeout_error(context, "pr19_next_recommended_lane drifted")
    if _require_string(data, "source", context) != SOURCE:
        raise _closeout_error(context, f"source must be {SOURCE}")
    if _require_string(data, "source_classification", context) != SOURCE_CLASSIFICATION:
        raise _closeout_error(context, f"source_classification must be {SOURCE_CLASSIFICATION}")
    if _require_string(data, "source_family", context) != SOURCE_FAMILY:
        raise _closeout_error(context, f"source_family must be {SOURCE_FAMILY}")
    if _require_string(data, "evidence_policy", context) != EVIDENCE_POLICY:
        raise _closeout_error(context, f"evidence_policy must be {EVIDENCE_POLICY}")
    external_role = _require_string(data, "external_research_evidence_role", context)
    if external_role != EXTERNAL_RESEARCH_EVIDENCE_ROLE:
        raise _closeout_error(
            context,
            "external_research_evidence_role must be review_context_only_not_source_authority",
        )
    blocked_methods = _require_string_tuple(
        data, "blocked_methods", context, expected=BLOCKED_METHODS
    )
    closeout_decision = _require_exact_string(data, "closeout_decision", context)
    if closeout_decision != _EXPECTED_CLOSEOUT_DECISION:
        raise _closeout_error(context, "closeout_decision must use controlled text")
    _require_safety_flags(data, context)
    candidate_closeout_terms = _candidate_closeout_terms(
        data,
        pr19_gate=pr19_gate,
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
        raise _closeout_error(context, "role_agent_dispatch_status drifted")
    experiment_runner_policy = _require_string(data, "experiment_runner_policy", context)
    if experiment_runner_policy != _EXPECTED_EXPERIMENT_RUNNER_POLICY:
        raise _closeout_error(context, "experiment_runner_policy drifted")
    if _require_string(data, "next_recommended_lane", context) != derived_next_lane:
        raise _closeout_error(
            context, f"next_recommended_lane must be derived as {derived_next_lane}"
        )
    if _require_string(data, "final_gate_decision", context) != FINAL_GATE_DECISION:
        raise _closeout_error(context, f"final_gate_decision must be {FINAL_GATE_DECISION}")
    notes = _require_exact_string(data, "notes", context)
    if notes != _EXPECTED_NOTES:
        raise _closeout_error(context, "notes must use controlled text")

    return RegionalCatalogSourceSpecificTermsCloseoutGovernance(
        schema_version=schema_version,
        generated_on=generated_on,
        pr19_source_specific_terms_ref=pr19_ref,
        pr19_merged_pr=PR19_MERGED_PR,
        pr19_merge_marker=PR19_MERGE_MARKER,
        pr19_next_recommended_lane=PR19_NEXT_RECOMMENDED_LANE,
        source=SOURCE,
        source_classification=SOURCE_CLASSIFICATION,
        source_family=SOURCE_FAMILY,
        evidence_policy=EVIDENCE_POLICY,
        external_research_evidence_role=external_role,
        blocked_methods=blocked_methods,
        closeout_decision=closeout_decision,
        candidate_closeout_terms=candidate_closeout_terms,
        premortem_dispositions=premortem_dispositions,
        role_agent_dispatch_status=role_agent_dispatch_status,
        experiment_runner_policy=experiment_runner_policy,
        next_recommended_lane=derived_next_lane,
        final_gate_decision=FINAL_GATE_DECISION,
        notes=notes,
    )


def load_regional_catalog_source_specific_terms_closeout_governance(
    closeout_path: Path | str,
    *,
    pr19_report: dict[str, object],
    pr19_gate: RegionalCatalogSourceSpecificTermsGovernance,
    expected_pr19_source_specific_terms_ref: str | None = None,
) -> RegionalCatalogSourceSpecificTermsCloseoutGovernance:
    """Load and validate a PR20 source-specific terms closeout artifact."""

    path = Path(closeout_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RegionalCatalogSourceSpecificTermsCloseoutError(
            f"Cannot read regional catalog source-specific terms closeout {path}: {exc}"
        ) from exc
    return parse_regional_catalog_source_specific_terms_closeout_governance(
        payload,
        pr19_report=pr19_report,
        pr19_gate=pr19_gate,
        expected_pr19_source_specific_terms_ref=expected_pr19_source_specific_terms_ref,
        context=str(path),
    )


def build_regional_catalog_source_specific_terms_closeout_report(
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
    closeout_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR20 closeout gate."""

    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    expected_coverage_ref = _relative_repo_path(coverage_path)
    expected_pr16_ref = _relative_repo_path(pr16_closeout_path)
    expected_pr17_ref = _relative_repo_path(pr17_identity_path)
    expected_pr18_ref = _relative_repo_path(pr18_provider_terms_path)
    expected_pr19_ref = _relative_repo_path(pr19_source_specific_terms_path)
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
    report.update(_observed_safety_flags(closeout_path))
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
        gate = load_regional_catalog_source_specific_terms_closeout_governance(
            closeout_path,
            pr19_report=pr19_report,
            pr19_gate=pr19_gate,
            expected_pr19_source_specific_terms_ref=expected_pr19_ref,
        )
    except (
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
            "pr19_source_specific_terms_ref": gate.pr19_source_specific_terms_ref,
            "pr19_merged_pr": gate.pr19_merged_pr,
            "pr19_merge_marker": gate.pr19_merge_marker,
            "pr19_next_recommended_lane": gate.pr19_next_recommended_lane,
            "evidence_policy": gate.evidence_policy,
            "external_research_evidence_role": gate.external_research_evidence_role,
            "closeout_decision": gate.closeout_decision,
            "candidate_decisions": {
                row.candidate_id: row.allowed_role for row in gate.candidate_closeout_terms
            },
            "candidate_next_required_review": {
                row.candidate_id: row.next_required_review for row in gate.candidate_closeout_terms
            },
            "candidate_evidence_confidence": {
                row.candidate_id: row.evidence_confidence for row in gate.candidate_closeout_terms
            },
            "candidate_closeout_status": {
                row.candidate_id: row.closeout_status for row in gate.candidate_closeout_terms
            },
            "candidate_legal_contract_review_status": {
                row.candidate_id: row.legal_contract_review_status
                for row in gate.candidate_closeout_terms
            },
            "role_agent_dispatch_status": gate.role_agent_dispatch_status,
            "experiment_runner_policy": gate.experiment_runner_policy,
        }
    )
    return report
