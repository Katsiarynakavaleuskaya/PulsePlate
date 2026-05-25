"""Deterministic file-only PR22 dedicated legal-contract review closeout gate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from core.food_sources.regional_catalog_dedicated_legal_contract_review import (
    FINAL_GATE_DECISION as PR21_FINAL_GATE_DECISION,
    NEXT_RECOMMENDED_LANE as PR21_NEXT_RECOMMENDED_LANE,
    RegionalCatalogDedicatedLegalContractReviewError,
    build_regional_catalog_dedicated_legal_contract_review_report,
)
from core.food_sources.regional_catalog_identity import EXPECTED_CANDIDATE_IDS

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_RE = re.compile(
    r"^food-data-regional-catalog-dedicated-legal-contract-review-closeout\.v\d+$"
)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PR21_REF = (
    "docs/architecture/"
    "FOOD_DATA_REGIONAL_CATALOG_DEDICATED_LEGAL_CONTRACT_REVIEW_PR21_2026-05-25.json"
)
PR21_MERGED_PR = 1829
PR21_MERGE_MARKER = "PR #1829 merged before PR22 scope lock"
SOURCE = "regional_catalogs"
SOURCE_CLASSIFICATION = "governance_dedicated_legal_contract_review_closeout_only"
SOURCE_FAMILY = "regional_catalog"
EVIDENCE_POLICY = "evidence_only_no_provider_use"
EXTERNAL_RESEARCH_EVIDENCE_ROLE = "review_context_only_not_source_authority"
LEGAL_REVIEW_AUTHORITY = "not_legal_advice_not_source_authority"
TERMS_EVIDENCE_ROLE = "review_context_only_not_terms_or_source_authority"
FINAL_GATE_DECISION = (
    "regional_catalog_dedicated_legal_contract_review_closeout_only_no_source_or_provider_use"
)
NEXT_RECOMMENDED_LANE = "regional_catalog_legal_contract_packet_handoff"

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
        "pr21_dedicated_legal_contract_review_ref",
        "pr21_merged_pr",
        "pr21_merge_marker",
        "pr21_next_recommended_lane",
        "pr21_final_gate_decision",
        "source",
        "source_classification",
        "source_family",
        "evidence_policy",
        "external_research_evidence_role",
        "legal_review_authority",
        "blocked_methods",
        "closeout_decision",
        "candidate_legal_contract_closeouts",
        "premortem_dispositions",
        "role_agent_dispatch_status",
        "experiment_runner_policy",
        "experiment_runner_status",
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
        "evidence_confidence",
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
        "nutrition_authority_status",
        "product_authority_status",
        "closeout_status",
        "legal_contract_review_closeout_status",
        "final_candidate_decision",
        "next_required_review",
        "blocking_reasons",
    }
)

_EXPECTED_ALLOWED_ROLE = "review_only_no_provider_use"
_EXPECTED_PR21_DECISION = "review_only_no_source_or_provider_use"
_EXPECTED_LEGAL_REVIEW_STATUS = "required_not_approved"
_EXPECTED_CONTRACT_REVIEW_STATUS = "required_not_approved"
_EXPECTED_LEGAL_APPROVAL_STATUS = "not_approved"
_EXPECTED_PROVIDER_ACCOUNT_ACCESS_STATUS = "unverified"
_EXPECTED_BLOCKED_UNRESOLVED = "blocked_unresolved"
_EXPECTED_BLOCKED_NOT_APPROVED = "blocked_not_approved"
_EXPECTED_BLOCKED_NOT_AUTHORITY = "blocked_not_authority"
_EXPECTED_CLOSEOUT_STATUS = "pr21_closed_review_only_no_source_or_provider_use"
_EXPECTED_LEGAL_CONTRACT_REVIEW_CLOSEOUT_STATUS = (
    "closed_without_legal_approval_or_source_provider_use"
)
_EXPECTED_FINAL_CANDIDATE_DECISION = (
    "remain_review_only_no_source_or_provider_use_until_dedicated_legal_contract_packet"
)
_EXPECTED_NEXT_REVIEW = "legal_contract_packet_handoff_required"
_EXPECTED_CLOSEOUT_DECISION = (
    "PR22 closes PR21 dedicated legal-contract review as file-only governance. "
    "Every inherited regional catalog candidate remains review-only with no "
    "legal approval, source use, provider use, API calls, scraping, downloads, "
    "account access, paid use, database writes, cache authority, redistribution, "
    "runtime authority, product display, nutrition authority, source authority, "
    "or connector writes."
)
_EXPECTED_NOTES = (
    "PR22 is a closeout packet only. Attached reports, spreadsheets, documents, "
    "images, browser findings, public references, connector outputs, and "
    "Experiment Runner artifacts remain review context only and do not become "
    "source, provider, terms, license, product, runtime, or nutrition authority."
)
_EXPECTED_PR21_BLOCKING_REASON = (
    "Dedicated legal-contract review is required before any source use, provider use, "
    "API access, scraping, downloads, account access, paid use, cache authority, "
    "redistribution, product display, nutrition authority, source authority, "
    "runtime authority, or database write can be approved."
)
_EXPECTED_CLOSEOUT_BLOCKING_REASON = (
    "PR21 did not grant legal approval, source use, provider use, API access, "
    "scraping, downloads, account access, paid use, cache authority, "
    "redistribution, product display, nutrition authority, source authority, "
    "runtime authority, database writes, or connector writes."
)
_EXPECTED_PREMORTEM_DISPOSITIONS = (
    "PM-PR22-001 stale PR21 handoff fixed by exact PR21 lane, merge, final-gate, and candidate-order validation",
    "PM-PR22-002 closeout approval drift fixed by controlled closeout text and unsafe prose rejection",
    "PM-PR22-003 missing-field false-green fixed by required closeout fields and malformed-artifact tests",
    "PM-PR22-004 Experiment Runner evidence drift fixed by explicit local-result status in artifact, PR body, and fixed mapping",
    "PM-PR22-005 local artifact leakage fixed by gitignored artifact boundary and status checks",
    "PM-PR22-006 pre-gate worktree provenance drift fixed by explicit operator approval to reuse existing untracked PR22 files before staging",
)
_EXPECTED_ROLE_AGENT_DISPATCH_STATUS = (
    "pre_open_full_dispatch_sequence_completed_with_operator_approved_existing_worktree_reuse"
)
_EXPECTED_EXPERIMENT_RUNNER_POLICY = (
    "mandatory_oracle_only_after_real_diff_before_pr_open_recorded_in_pr_body_and_fixed_mapping"
)
_EXPECTED_EXPERIMENT_RUNNER_STATUS = "completed_oracle_only_reviewed_no_commit_decision_change"

_INHERITED_FIELDS = {
    "candidate_name": None,
    "provider_route_classification": None,
    "allowed_role": _EXPECTED_ALLOWED_ROLE,
    "evidence_confidence": "low_unverified",
    "legal_contract_decision": _EXPECTED_PR21_DECISION,
    "legal_review_status": _EXPECTED_LEGAL_REVIEW_STATUS,
    "contract_review_status": _EXPECTED_CONTRACT_REVIEW_STATUS,
    "legal_approval_status": _EXPECTED_LEGAL_APPROVAL_STATUS,
    "terms_evidence_role": TERMS_EVIDENCE_ROLE,
    "legal_review_authority": LEGAL_REVIEW_AUTHORITY,
    "provider_account_access_status": _EXPECTED_PROVIDER_ACCOUNT_ACCESS_STATUS,
    "contract_permission_status": _EXPECTED_BLOCKED_UNRESOLVED,
    "api_use_permission_status": _EXPECTED_BLOCKED_NOT_APPROVED,
    "scraping_permission_status": _EXPECTED_BLOCKED_NOT_APPROVED,
    "download_permission_status": _EXPECTED_BLOCKED_NOT_APPROVED,
    "cache_permission_status": _EXPECTED_BLOCKED_UNRESOLVED,
    "redistribution_permission_status": _EXPECTED_BLOCKED_UNRESOLVED,
    "product_display_permission_status": _EXPECTED_BLOCKED_UNRESOLVED,
    "attribution_requirement_status": _EXPECTED_BLOCKED_UNRESOLVED,
    "source_authority_status": _EXPECTED_BLOCKED_NOT_AUTHORITY,
    "nutrition_authority_status": _EXPECTED_BLOCKED_NOT_AUTHORITY,
    "product_authority_status": _EXPECTED_BLOCKED_NOT_AUTHORITY,
}

_AUTHORITY_TERMS = (
    r"network|api calls?|api use|scraping|downloads?|account access|"
    r"paid (?:source|provider|plan)|seller access|seller api|partner access|"
    r"partner api|provider use|provider integration|db writes?|database writes?|"
    r"cache authority|redistribution|runtime authority|product display|"
    r"nutrition authority|source authority|source use|public dataset authority|"
    r"legal review|legal approval|legal contract review|contract review|"
    r"contract permission|terms permission|connector writes?"
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
    r"experiment runner artifact is authority|public references are source authority|"
    r"terms authorize|license permits|legal review complete|contract review complete"
    r")\b",
    re.IGNORECASE,
)


class RegionalCatalogDedicatedLegalContractReviewCloseoutError(ValueError):
    """Raised when the PR22 dedicated legal-contract review closeout is invalid."""


@dataclass(frozen=True)
class RegionalCatalogDedicatedLegalContractReviewCloseoutCandidate:
    """Validated PR22 closeout row for one inherited PR21 candidate."""

    candidate_id: str
    candidate_name: str
    provider_route_classification: str
    allowed_role: str
    evidence_confidence: str
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
    nutrition_authority_status: str
    product_authority_status: str
    closeout_status: str
    legal_contract_review_closeout_status: str
    final_candidate_decision: str
    next_required_review: str
    blocking_reasons: tuple[str, ...]


@dataclass(frozen=True)
class RegionalCatalogDedicatedLegalContractReviewCloseoutGovernance:
    """Validated PR22 dedicated legal-contract review closeout artifact."""

    schema_version: str
    generated_on: date
    pr21_dedicated_legal_contract_review_ref: str
    pr21_merged_pr: int
    pr21_merge_marker: str
    pr21_next_recommended_lane: str
    pr21_final_gate_decision: str
    source: str
    source_classification: str
    source_family: str
    evidence_policy: str
    external_research_evidence_role: str
    legal_review_authority: str
    blocked_methods: tuple[str, ...]
    closeout_decision: str
    candidate_legal_contract_closeouts: tuple[
        RegionalCatalogDedicatedLegalContractReviewCloseoutCandidate, ...
    ]
    premortem_dispositions: tuple[str, ...]
    role_agent_dispatch_status: str
    experiment_runner_policy: str
    experiment_runner_status: str
    next_recommended_lane: str
    final_gate_decision: str
    notes: str


def _closeout_error(
    context: str,
    detail: str,
) -> RegionalCatalogDedicatedLegalContractReviewCloseoutError:
    return RegionalCatalogDedicatedLegalContractReviewCloseoutError(
        f"Invalid regional catalog dedicated legal-contract review closeout {context}: {detail}"
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
            raise _closeout_error(context, f"'{key}[{index}]' must not approve source use")
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


def _observed_safety_flags(path: Path | str) -> dict[str, object]:
    try:
        with Path(path).open("r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {key: payload[key] for key in _SAFETY_FLAG_TEMPLATE if key in payload}


def _validate_pr21_report(report: dict[str, object], context: str) -> None:
    if report.get("success") is not True:
        raise _closeout_error(context, "PR21 dedicated legal-contract review report must succeed")
    if report.get("next_recommended_lane") != PR21_NEXT_RECOMMENDED_LANE:
        raise _closeout_error(context, "PR21 next_recommended_lane drifted")
    if report.get("final_gate_decision") != PR21_FINAL_GATE_DECISION:
        raise _closeout_error(context, "PR21 final_gate_decision drifted")
    if report.get("candidate_ids") != list(EXPECTED_CANDIDATE_IDS):
        raise _closeout_error(context, "PR21 candidate_ids drifted")
    for flag_name, expected_value in _SAFETY_FLAG_TEMPLATE.items():
        if report.get(flag_name) is not expected_value:
            raise _closeout_error(context, f"PR21 safety flag drifted: {flag_name}")


def _candidate_rows_from_pr21(
    pr21_payload: object,
    context: str,
) -> dict[str, dict[str, object]]:
    data = _require_mapping(pr21_payload, f"{context}.pr21")
    if _require_string(data, "next_recommended_lane", f"{context}.pr21") != (
        PR21_NEXT_RECOMMENDED_LANE
    ):
        raise _closeout_error(context, "PR21 artifact next_recommended_lane drifted")
    if _require_string(data, "final_gate_decision", f"{context}.pr21") != PR21_FINAL_GATE_DECISION:
        raise _closeout_error(context, "PR21 artifact final_gate_decision drifted")
    value = data.get("candidate_legal_contract_reviews")
    if not isinstance(value, list):
        raise _closeout_error(context, "PR21 candidate_legal_contract_reviews must be a list")
    rows: dict[str, dict[str, object]] = {}
    observed_ids: list[str] = []
    for index, raw_candidate in enumerate(value):
        candidate_context = f"{context}.pr21.candidate_legal_contract_reviews[{index}]"
        candidate = _require_mapping(raw_candidate, candidate_context)
        candidate_id = _require_string(candidate, "candidate_id", candidate_context)
        observed_ids.append(candidate_id)
        rows[candidate_id] = candidate
        _validate_pr21_candidate(candidate, candidate_context)
    if tuple(observed_ids) != EXPECTED_CANDIDATE_IDS:
        raise _closeout_error(context, "PR21 candidate order drifted")
    return rows


def _validate_pr21_candidate(candidate: dict[str, object], context: str) -> None:
    for field_name, expected_value in _INHERITED_FIELDS.items():
        observed = _require_string(candidate, field_name, context)
        if expected_value is not None and observed != expected_value:
            raise _closeout_error(context, f"PR21 {field_name} drifted")
    blocking_reasons = _require_string_tuple(candidate, "blocking_reasons", context)
    if blocking_reasons != (_EXPECTED_PR21_BLOCKING_REASON,):
        raise _closeout_error(context, "PR21 blocking_reasons drifted")


def _require_expected_candidate_string(
    candidate: dict[str, object],
    field_name: str,
    expected_value: str,
    context: str,
) -> str:
    observed = _require_string(candidate, field_name, context)
    if observed != expected_value:
        raise _closeout_error(context, f"{field_name} drifted")
    return observed


def _validate_candidate_against_pr21(
    candidate: dict[str, object],
    pr21_candidate: dict[str, object],
    context: str,
) -> None:
    for field_name in _INHERITED_FIELDS:
        if _require_string(candidate, field_name, context) != _require_string(
            pr21_candidate,
            field_name,
            f"{context}.pr21",
        ):
            raise _closeout_error(context, f"{field_name} must match PR21")


def _candidate_legal_contract_closeouts(
    data: dict[str, object],
    *,
    pr21_candidates: dict[str, dict[str, object]],
    context: str,
) -> tuple[RegionalCatalogDedicatedLegalContractReviewCloseoutCandidate, ...]:
    value = data.get("candidate_legal_contract_closeouts")
    if not isinstance(value, list):
        raise _closeout_error(context, "candidate_legal_contract_closeouts must be a list")
    rows: list[RegionalCatalogDedicatedLegalContractReviewCloseoutCandidate] = []
    seen: set[str] = set()
    for index, raw_candidate in enumerate(value):
        candidate_context = f"{context}.candidate_legal_contract_closeouts[{index}]"
        candidate = _require_mapping(raw_candidate, candidate_context)
        unexpected = sorted(set(candidate) - _CANDIDATE_KEYS)
        if unexpected:
            raise _closeout_error(
                candidate_context,
                "unexpected candidate keys: " + ", ".join(unexpected),
            )
        candidate_id = _require_string(candidate, "candidate_id", candidate_context)
        if candidate_id not in EXPECTED_CANDIDATE_IDS:
            raise _closeout_error(candidate_context, f"unknown candidate_id {candidate_id!r}")
        if candidate_id in seen:
            raise _closeout_error(
                context,
                f"candidate_legal_contract_closeouts contains duplicate {candidate_id}",
            )
        seen.add(candidate_id)
        pr21_candidate = pr21_candidates[candidate_id]
        _validate_candidate_against_pr21(candidate, pr21_candidate, candidate_context)
        blocking_reasons = _require_string_tuple(candidate, "blocking_reasons", candidate_context)
        if blocking_reasons != (_EXPECTED_CLOSEOUT_BLOCKING_REASON,):
            raise _closeout_error(candidate_context, "blocking_reasons drifted")
        rows.append(
            RegionalCatalogDedicatedLegalContractReviewCloseoutCandidate(
                candidate_id=candidate_id,
                candidate_name=_require_string(candidate, "candidate_name", candidate_context),
                provider_route_classification=_require_string(
                    candidate,
                    "provider_route_classification",
                    candidate_context,
                ),
                allowed_role=_require_string(candidate, "allowed_role", candidate_context),
                evidence_confidence=_require_string(
                    candidate,
                    "evidence_confidence",
                    candidate_context,
                ),
                legal_contract_decision=_require_string(
                    candidate,
                    "legal_contract_decision",
                    candidate_context,
                ),
                legal_review_status=_require_string(
                    candidate,
                    "legal_review_status",
                    candidate_context,
                ),
                contract_review_status=_require_string(
                    candidate,
                    "contract_review_status",
                    candidate_context,
                ),
                legal_approval_status=_require_string(
                    candidate,
                    "legal_approval_status",
                    candidate_context,
                ),
                terms_evidence_role=_require_string(
                    candidate,
                    "terms_evidence_role",
                    candidate_context,
                ),
                legal_review_authority=_require_string(
                    candidate,
                    "legal_review_authority",
                    candidate_context,
                ),
                provider_account_access_status=_require_string(
                    candidate,
                    "provider_account_access_status",
                    candidate_context,
                ),
                contract_permission_status=_require_string(
                    candidate,
                    "contract_permission_status",
                    candidate_context,
                ),
                api_use_permission_status=_require_string(
                    candidate,
                    "api_use_permission_status",
                    candidate_context,
                ),
                scraping_permission_status=_require_string(
                    candidate,
                    "scraping_permission_status",
                    candidate_context,
                ),
                download_permission_status=_require_string(
                    candidate,
                    "download_permission_status",
                    candidate_context,
                ),
                cache_permission_status=_require_string(
                    candidate,
                    "cache_permission_status",
                    candidate_context,
                ),
                redistribution_permission_status=_require_string(
                    candidate,
                    "redistribution_permission_status",
                    candidate_context,
                ),
                product_display_permission_status=_require_string(
                    candidate,
                    "product_display_permission_status",
                    candidate_context,
                ),
                attribution_requirement_status=_require_string(
                    candidate,
                    "attribution_requirement_status",
                    candidate_context,
                ),
                source_authority_status=_require_string(
                    candidate,
                    "source_authority_status",
                    candidate_context,
                ),
                nutrition_authority_status=_require_string(
                    candidate,
                    "nutrition_authority_status",
                    candidate_context,
                ),
                product_authority_status=_require_string(
                    candidate,
                    "product_authority_status",
                    candidate_context,
                ),
                closeout_status=_require_expected_candidate_string(
                    candidate,
                    "closeout_status",
                    _EXPECTED_CLOSEOUT_STATUS,
                    candidate_context,
                ),
                legal_contract_review_closeout_status=_require_expected_candidate_string(
                    candidate,
                    "legal_contract_review_closeout_status",
                    _EXPECTED_LEGAL_CONTRACT_REVIEW_CLOSEOUT_STATUS,
                    candidate_context,
                ),
                final_candidate_decision=_require_expected_candidate_string(
                    candidate,
                    "final_candidate_decision",
                    _EXPECTED_FINAL_CANDIDATE_DECISION,
                    candidate_context,
                ),
                next_required_review=_require_expected_candidate_string(
                    candidate,
                    "next_required_review",
                    _EXPECTED_NEXT_REVIEW,
                    candidate_context,
                ),
                blocking_reasons=blocking_reasons,
            )
        )
    observed_ids = tuple(row.candidate_id for row in rows)
    if observed_ids != EXPECTED_CANDIDATE_IDS:
        raise _closeout_error(
            context,
            "candidate_legal_contract_closeouts must preserve PR21 candidate order: "
            + ", ".join(EXPECTED_CANDIDATE_IDS),
        )
    return tuple(rows)


def parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
    payload: object,
    *,
    pr21_report: dict[str, object],
    pr21_payload: object,
    expected_pr21_legal_review_ref: str | None = None,
    context: str = "<regional-catalog-dedicated-legal-contract-review-closeout>",
) -> RegionalCatalogDedicatedLegalContractReviewCloseoutGovernance:
    """Parse and validate the PR22 dedicated legal-contract review closeout artifact."""

    _validate_pr21_report(pr21_report, context)
    pr21_candidates = _candidate_rows_from_pr21(pr21_payload, context)
    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _GOVERNANCE_KEYS)
    if unexpected_keys:
        raise _closeout_error(context, f"unexpected keys: {', '.join(unexpected_keys)}")

    schema_version = _require_string(data, "schema_version", context)
    if not _SCHEMA_RE.fullmatch(schema_version):
        raise _closeout_error(
            context,
            "schema_version must look like "
            "food-data-regional-catalog-dedicated-legal-contract-review-closeout.vN",
        )
    generated_on = _parse_date(_require_string(data, "generated_on", context), context)
    pr21_ref = _require_string(data, "pr21_dedicated_legal_contract_review_ref", context)
    if expected_pr21_legal_review_ref is not None and pr21_ref != expected_pr21_legal_review_ref:
        raise _closeout_error(
            context,
            f"pr21_dedicated_legal_contract_review_ref must be {expected_pr21_legal_review_ref!r}",
        )
    if _require_int(data, "pr21_merged_pr", context) != PR21_MERGED_PR:
        raise _closeout_error(context, f"pr21_merged_pr must be {PR21_MERGED_PR}")
    if _require_string(data, "pr21_merge_marker", context) != PR21_MERGE_MARKER:
        raise _closeout_error(context, "pr21_merge_marker drifted")
    if _require_string(data, "pr21_next_recommended_lane", context) != PR21_NEXT_RECOMMENDED_LANE:
        raise _closeout_error(context, "pr21_next_recommended_lane drifted")
    if _require_string(data, "pr21_final_gate_decision", context) != PR21_FINAL_GATE_DECISION:
        raise _closeout_error(context, "pr21_final_gate_decision drifted")
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
    legal_review_authority = _require_string(data, "legal_review_authority", context)
    if legal_review_authority != LEGAL_REVIEW_AUTHORITY:
        raise _closeout_error(context, "legal_review_authority drifted")
    blocked_methods = _require_string_tuple(
        data,
        "blocked_methods",
        context,
        expected=BLOCKED_METHODS,
    )
    closeout_decision = _require_exact_string(data, "closeout_decision", context)
    if closeout_decision != _EXPECTED_CLOSEOUT_DECISION:
        raise _closeout_error(context, "closeout_decision must use controlled text")
    _require_safety_flags(data, context)
    candidate_legal_contract_closeouts = _candidate_legal_contract_closeouts(
        data,
        pr21_candidates=pr21_candidates,
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
    experiment_runner_status = _require_string(data, "experiment_runner_status", context)
    if experiment_runner_status != _EXPECTED_EXPERIMENT_RUNNER_STATUS:
        raise _closeout_error(context, "experiment_runner_status drifted")
    if _require_string(data, "next_recommended_lane", context) != NEXT_RECOMMENDED_LANE:
        raise _closeout_error(context, f"next_recommended_lane must be {NEXT_RECOMMENDED_LANE}")
    if _require_string(data, "final_gate_decision", context) != FINAL_GATE_DECISION:
        raise _closeout_error(context, f"final_gate_decision must be {FINAL_GATE_DECISION}")
    notes = _require_exact_string(data, "notes", context)
    if notes != _EXPECTED_NOTES:
        raise _closeout_error(context, "notes must use controlled text")

    return RegionalCatalogDedicatedLegalContractReviewCloseoutGovernance(
        schema_version=schema_version,
        generated_on=generated_on,
        pr21_dedicated_legal_contract_review_ref=pr21_ref,
        pr21_merged_pr=PR21_MERGED_PR,
        pr21_merge_marker=PR21_MERGE_MARKER,
        pr21_next_recommended_lane=PR21_NEXT_RECOMMENDED_LANE,
        pr21_final_gate_decision=PR21_FINAL_GATE_DECISION,
        source=SOURCE,
        source_classification=SOURCE_CLASSIFICATION,
        source_family=SOURCE_FAMILY,
        evidence_policy=EVIDENCE_POLICY,
        external_research_evidence_role=external_role,
        legal_review_authority=legal_review_authority,
        blocked_methods=blocked_methods,
        closeout_decision=closeout_decision,
        candidate_legal_contract_closeouts=candidate_legal_contract_closeouts,
        premortem_dispositions=premortem_dispositions,
        role_agent_dispatch_status=role_agent_dispatch_status,
        experiment_runner_policy=experiment_runner_policy,
        experiment_runner_status=experiment_runner_status,
        next_recommended_lane=NEXT_RECOMMENDED_LANE,
        final_gate_decision=FINAL_GATE_DECISION,
        notes=notes,
    )


def load_regional_catalog_dedicated_legal_contract_review_closeout_governance(
    closeout_path: Path | str,
    *,
    pr21_report: dict[str, object],
    pr21_payload: object,
    expected_pr21_legal_review_ref: str | None = None,
) -> RegionalCatalogDedicatedLegalContractReviewCloseoutGovernance:
    """Load and validate a PR22 dedicated legal-contract review closeout artifact."""

    path = Path(closeout_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RegionalCatalogDedicatedLegalContractReviewCloseoutError(
            f"Cannot read regional catalog dedicated legal-contract review closeout {path}: {exc}"
        ) from exc
    return parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
        payload,
        pr21_report=pr21_report,
        pr21_payload=pr21_payload,
        expected_pr21_legal_review_ref=expected_pr21_legal_review_ref,
        context=str(path),
    )


def _load_json_payload(path: Path | str) -> object:
    with Path(path).open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def build_regional_catalog_dedicated_legal_contract_review_closeout_report(
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
    pr21_legal_review_path: Path | str,
    closeout_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR22 closeout gate."""

    expected_pr21_ref = _relative_repo_path(pr21_legal_review_path)
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
        pr21_report = build_regional_catalog_dedicated_legal_contract_review_report(
            catalog_path=catalog_path,
            onboarding_path=onboarding_path,
            coverage_path=coverage_path,
            recipe_dish_corpus_path=recipe_dish_corpus_path,
            preference_mapping_path=preference_mapping_path,
            pr16_closeout_path=pr16_closeout_path,
            pr17_identity_path=pr17_identity_path,
            pr18_provider_terms_path=pr18_provider_terms_path,
            pr19_source_specific_terms_path=pr19_source_specific_terms_path,
            pr20_closeout_path=pr20_closeout_path,
            legal_review_path=pr21_legal_review_path,
        )
        pr21_payload = _load_json_payload(pr21_legal_review_path)
        gate = load_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            closeout_path,
            pr21_report=pr21_report,
            pr21_payload=pr21_payload,
            expected_pr21_legal_review_ref=expected_pr21_ref,
        )
    except (
        RegionalCatalogDedicatedLegalContractReviewCloseoutError,
        RegionalCatalogDedicatedLegalContractReviewError,
        OSError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as exc:
        report["validation_errors"] = [str(exc)]
        return report

    report.update(
        {
            "success": True,
            "pr21_dedicated_legal_contract_review_ref": (
                gate.pr21_dedicated_legal_contract_review_ref
            ),
            "pr21_merged_pr": gate.pr21_merged_pr,
            "pr21_merge_marker": gate.pr21_merge_marker,
            "pr21_next_recommended_lane": gate.pr21_next_recommended_lane,
            "pr21_final_gate_decision": gate.pr21_final_gate_decision,
            "evidence_policy": gate.evidence_policy,
            "external_research_evidence_role": gate.external_research_evidence_role,
            "legal_review_authority": gate.legal_review_authority,
            "closeout_decision": gate.closeout_decision,
            "candidate_decisions": {
                row.candidate_id: row.final_candidate_decision
                for row in gate.candidate_legal_contract_closeouts
            },
            "candidate_next_required_review": {
                row.candidate_id: row.next_required_review
                for row in gate.candidate_legal_contract_closeouts
            },
            "candidate_evidence_confidence": {
                row.candidate_id: row.evidence_confidence
                for row in gate.candidate_legal_contract_closeouts
            },
            "candidate_closeout_status": {
                row.candidate_id: row.closeout_status
                for row in gate.candidate_legal_contract_closeouts
            },
            "candidate_legal_contract_review_closeout_status": {
                row.candidate_id: row.legal_contract_review_closeout_status
                for row in gate.candidate_legal_contract_closeouts
            },
            "role_agent_dispatch_status": gate.role_agent_dispatch_status,
            "experiment_runner_policy": gate.experiment_runner_policy,
            "experiment_runner_status": gate.experiment_runner_status,
        }
    )
    return report
