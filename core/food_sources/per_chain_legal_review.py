"""
Deterministic per-chain legal and anti-scraping governance gate.

RU: Файловая проверка PR13: публичные страницы сетей остаются ручным
evidence lane до отдельного legal/anti-scraping approval.
EN: File-only PR13 validation: public chain pages stay manual evidence only
until a separate legal and anti-scraping approval exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from core.food_sources.chain_public_nutrition import (
    ChainPublicNutritionGovernance,
    ChainPublicNutritionGovernanceError,
    load_chain_public_nutrition_governance,
)
from core.food_sources.source_catalog import SourceCatalogError, load_source_catalog
from core.food_sources.source_gap_audit import SourceGapAuditError, load_source_gap_audit
from core.food_sources.source_onboarding import SourceOnboardingError, load_source_onboarding

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_RE = re.compile(r"^food-data-per-chain-legal-anti-scraping\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

CHAIN_PUBLIC_SOURCE = "chain_public_nutrition_pages"
EXPECTED_CHAIN_IDS = ("mcdonalds_us", "chipotle_us", "starbucks_us")
EVIDENCE_POLICY = "manual_evidence_only_pending_per_chain_legal_review"
FINAL_GATE_DECISION = "per_chain_legal_anti_scraping_review_only_no_ingest"
NEXT_RECOMMENDED_LANE = "recipe_dish_corpus_governance"
CHAIN_PUBLIC_NUTRITION_REF = (
    "docs/architecture/FOOD_DATA_CHAIN_PUBLIC_NUTRITION_PR12_2026-04-30.json"
)

BLOCKED_METHODS = (
    "scraping",
    "automated_collection",
    "api_call",
    "download",
    "login_or_paywall_bypass",
    "cache_authority",
    "redistribution",
    "runtime_authority",
    "public_dataset_claim",
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
    "cache_authority_allowed": False,
    "redistribution_allowed": False,
    "public_dataset_claim_allowed": False,
    "automation_allowed": False,
    "file_only": True,
}

_REVIEW_FLAG_KEYS = (
    "approved_ingest",
    "approved_runtime_authority",
    "scraping_allowed",
    "automation_allowed",
    "api_calls_allowed",
    "source_download_allowed",
    "db_writes_allowed",
    "cache_authority_allowed",
    "redistribution_allowed",
    "public_dataset_claim_allowed",
)

_GOVERNANCE_KEYS = frozenset(
    {
        "schema_version",
        "generated_on",
        "chain_public_nutrition_ref",
        "pr12_landed_pr",
        "source",
        "source_classification",
        "source_family",
        "evidence_policy",
        "blocked_methods",
        "per_chain_reviews",
        "runtime_cutover",
        "digitalocean_postgres_load",
        "bulk_ingest",
        "network_allowed",
        "db_writes_allowed",
        "api_calls_allowed",
        "source_download_allowed",
        "scraping_allowed",
        "cache_authority_allowed",
        "redistribution_allowed",
        "public_dataset_claim_allowed",
        "automation_allowed",
        "file_only",
        "next_recommended_lane",
        "final_gate_decision",
        "notes",
    }
)

_REVIEW_KEYS = frozenset(
    {
        "chain_id",
        "chain_name",
        "official_url",
        "upstream_evidence_type",
        "legal_review_status",
        "anti_scraping_review_status",
        "cache_decision",
        "display_decision",
        "attribution_decision",
        "redistribution_decision",
        "freshness_review_status",
        "schema_review_status",
        "manual_evidence_policy",
        "screenshot_policy",
        "rollback_requirement",
        "allowed_role",
        "approved_ingest",
        "approved_runtime_authority",
        "scraping_allowed",
        "automation_allowed",
        "api_calls_allowed",
        "source_download_allowed",
        "db_writes_allowed",
        "cache_authority_allowed",
        "redistribution_allowed",
        "public_dataset_claim_allowed",
        "notes",
    }
)


class PerChainLegalReviewError(ValueError):
    """Raised when the PR13 per-chain legal review artifact is invalid."""


@dataclass(frozen=True)
class PerChainReview:
    """One chain's legal and anti-scraping review placeholder."""

    chain_id: str
    chain_name: str
    official_url: str
    upstream_evidence_type: str
    legal_review_status: str
    anti_scraping_review_status: str
    cache_decision: str
    display_decision: str
    attribution_decision: str
    redistribution_decision: str
    freshness_review_status: str
    schema_review_status: str
    manual_evidence_policy: str
    screenshot_policy: str
    rollback_requirement: str
    allowed_role: str
    notes: str


@dataclass(frozen=True)
class PerChainLegalReviewGovernance:
    """Validated PR13 per-chain legal and anti-scraping governance artifact."""

    schema_version: str
    generated_on: date
    chain_public_nutrition_ref: str
    pr12_landed_pr: int
    source: str
    source_classification: str
    source_family: str
    evidence_policy: str
    blocked_methods: tuple[str, ...]
    per_chain_reviews: tuple[PerChainReview, ...]
    next_recommended_lane: str
    final_gate_decision: str
    notes: str


def _review_error(context: str, detail: str) -> PerChainLegalReviewError:
    return PerChainLegalReviewError(f"Invalid per-chain legal review {context}: {detail}")


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _review_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _review_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _review_error(context, f"missing non-empty string '{key}'")
    return value.strip()


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _review_error(context, f"'{key}' must be a boolean")
    return value


def _require_int(data: dict[str, object], key: str, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _review_error(context, f"'{key}' must be an integer")
    return value


def _require_string_tuple(
    data: dict[str, object],
    key: str,
    context: str,
    *,
    expected: tuple[str, ...],
) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list):
        raise _review_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _review_error(context, f"'{key}[{index}]' must be a non-empty string")
        normalized = item.strip()
        if normalized in seen:
            raise _review_error(context, f"'{key}' contains duplicate value {normalized!r}")
        seen.add(normalized)
        items.append(normalized)
    result = tuple(items)
    if result != expected:
        raise _review_error(context, f"'{key}' must be exactly: {', '.join(expected)}")
    return result


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _review_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _review_error(context, "generated_on must use YYYY-MM-DD") from exc


def _relative_repo_path(path: Path | str) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _require_safety_flags(data: dict[str, object], context: str) -> None:
    safety_flags = {key: _require_bool(data, key, context) for key in _SAFETY_FLAG_TEMPLATE}
    if safety_flags != _SAFETY_FLAG_TEMPLATE:
        raise _review_error(
            context,
            "runtime_cutover, digitalocean_postgres_load, bulk_ingest, network_allowed, "
            "db_writes_allowed, api_calls_allowed, source_download_allowed, scraping_allowed, "
            "cache_authority_allowed, redistribution_allowed, public_dataset_claim_allowed, "
            "and automation_allowed must be false; file_only must be true",
        )


def _pr12_reviews_by_chain(
    chain_public_nutrition: ChainPublicNutritionGovernance,
) -> dict[str, tuple[str, str, str]]:
    if chain_public_nutrition.next_recommended_lane != "per_chain_legal_anti_scraping_review":
        raise _review_error(
            "<chain-public-nutrition>",
            "PR12 must recommend per_chain_legal_anti_scraping_review",
        )
    return {
        page.chain_id: (page.chain_name, page.official_url, page.evidence_type)
        for page in chain_public_nutrition.representative_chain_pages
    }


def _parse_per_chain_review(
    value: object,
    *,
    pr12_chain_map: dict[str, tuple[str, str, str]],
    context: str,
) -> PerChainReview:
    data = _require_mapping(value, context)
    unexpected_keys = sorted(set(data) - _REVIEW_KEYS)
    if unexpected_keys:
        raise _review_error(
            context, f"unexpected per-chain review keys: {', '.join(unexpected_keys)}"
        )
    chain_id = _require_string(data, "chain_id", context)
    expected = pr12_chain_map.get(chain_id)
    if expected is None:
        raise _review_error(context, f"unknown PR12 chain id: {chain_id}")
    expected_name, expected_url, expected_evidence_type = expected
    chain_name = _require_string(data, "chain_name", context)
    official_url = _require_string(data, "official_url", context)
    upstream_evidence_type = _require_string(data, "upstream_evidence_type", context)
    if chain_name != expected_name:
        raise _review_error(context, f"{chain_id} chain_name must match PR12")
    if official_url != expected_url:
        raise _review_error(context, f"{chain_id} official_url must match PR12")
    if upstream_evidence_type != expected_evidence_type:
        raise _review_error(context, f"{chain_id} upstream_evidence_type must match PR12")
    if any(_require_bool(data, key, context) for key in _REVIEW_FLAG_KEYS):
        raise _review_error(
            context,
            f"{chain_id} cannot approve ingest, runtime authority, scraping, automation, "
            "API calls, downloads, DB writes, cache authority, redistribution, or dataset claims",
        )

    review = PerChainReview(
        chain_id=chain_id,
        chain_name=chain_name,
        official_url=official_url,
        upstream_evidence_type=upstream_evidence_type,
        legal_review_status=_require_string(data, "legal_review_status", context),
        anti_scraping_review_status=_require_string(data, "anti_scraping_review_status", context),
        cache_decision=_require_string(data, "cache_decision", context),
        display_decision=_require_string(data, "display_decision", context),
        attribution_decision=_require_string(data, "attribution_decision", context),
        redistribution_decision=_require_string(data, "redistribution_decision", context),
        freshness_review_status=_require_string(data, "freshness_review_status", context),
        schema_review_status=_require_string(data, "schema_review_status", context),
        manual_evidence_policy=_require_string(data, "manual_evidence_policy", context),
        screenshot_policy=_require_string(data, "screenshot_policy", context),
        rollback_requirement=_require_string(data, "rollback_requirement", context),
        allowed_role=_require_string(data, "allowed_role", context),
        notes=_require_string(data, "notes", context),
    )
    if review.legal_review_status != "required_not_approved":
        raise _review_error(
            context, f"{chain_id} legal_review_status must be required_not_approved"
        )
    if review.anti_scraping_review_status != "required_not_approved":
        raise _review_error(
            context, f"{chain_id} anti_scraping_review_status must be required_not_approved"
        )
    if review.cache_decision != "blocked_not_approved":
        raise _review_error(context, f"{chain_id} cache_decision must be blocked_not_approved")
    if review.redistribution_decision != "blocked_not_approved":
        raise _review_error(
            context, f"{chain_id} redistribution_decision must be blocked_not_approved"
        )
    if review.allowed_role != "manual_evidence_internal_review_only":
        raise _review_error(context, f"{chain_id} allowed_role is not allowed")
    if review.manual_evidence_policy != "official_url_and_internal_screenshot_only":
        raise _review_error(context, f"{chain_id} manual_evidence_policy is not allowed")
    if review.screenshot_policy != "internal_review_only_not_redistributable":
        raise _review_error(context, f"{chain_id} screenshot_policy is not allowed")
    if review.rollback_requirement != "required_before_any_future_ingest_or_runtime_lane":
        raise _review_error(context, f"{chain_id} rollback_requirement is not allowed")
    return review


def parse_per_chain_legal_review_governance(
    payload: object,
    *,
    chain_public_nutrition: ChainPublicNutritionGovernance,
    expected_chain_public_nutrition_ref: str | None = None,
    context: str = "<per-chain-legal-review>",
) -> PerChainLegalReviewGovernance:
    """Parse and validate the PR13 per-chain legal review artifact."""

    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _GOVERNANCE_KEYS)
    if unexpected_keys:
        raise _review_error(context, f"unexpected keys: {', '.join(unexpected_keys)}")
    schema_version = _require_string(data, "schema_version", context)
    if not _SCHEMA_RE.fullmatch(schema_version):
        raise _review_error(
            context, "schema_version must look like food-data-per-chain-legal-anti-scraping.vN"
        )
    chain_public_nutrition_ref = _require_string(data, "chain_public_nutrition_ref", context)
    expected_ref = expected_chain_public_nutrition_ref or CHAIN_PUBLIC_NUTRITION_REF
    if chain_public_nutrition_ref != expected_ref:
        raise _review_error(context, f"chain_public_nutrition_ref must be {expected_ref!r}")
    pr12_landed_pr = _require_int(data, "pr12_landed_pr", context)
    if pr12_landed_pr != 1609:
        raise _review_error(context, "pr12_landed_pr must be 1609")
    source = _require_string(data, "source", context)
    if source != CHAIN_PUBLIC_SOURCE:
        raise _review_error(context, f"source must be {CHAIN_PUBLIC_SOURCE}")
    source_classification = _require_string(data, "source_classification", context)
    if source_classification != "unresolved":
        raise _review_error(context, "source_classification must remain unresolved")
    source_family = _require_string(data, "source_family", context)
    if source_family != "restaurant_menu":
        raise _review_error(context, "source_family must be restaurant_menu")
    evidence_policy = _require_string(data, "evidence_policy", context)
    if evidence_policy != EVIDENCE_POLICY:
        raise _review_error(context, f"evidence_policy must be {EVIDENCE_POLICY}")
    blocked_methods = _require_string_tuple(
        data, "blocked_methods", context, expected=BLOCKED_METHODS
    )
    _require_safety_flags(data, context)

    pr12_chain_map = _pr12_reviews_by_chain(chain_public_nutrition)
    rows = data.get("per_chain_reviews")
    if not isinstance(rows, list):
        raise _review_error(context, "per_chain_reviews must be a list")
    per_chain_reviews = tuple(
        _parse_per_chain_review(
            row,
            pr12_chain_map=pr12_chain_map,
            context=f"{context}.per_chain_reviews[{index}]",
        )
        for index, row in enumerate(rows)
    )
    chain_order = tuple(review.chain_id for review in per_chain_reviews)
    if chain_order != EXPECTED_CHAIN_IDS:
        raise _review_error(
            context, "per_chain_reviews must be exactly: " + ", ".join(EXPECTED_CHAIN_IDS)
        )

    next_recommended_lane = _require_string(data, "next_recommended_lane", context)
    if next_recommended_lane != NEXT_RECOMMENDED_LANE:
        raise _review_error(context, f"next_recommended_lane must be {NEXT_RECOMMENDED_LANE}")
    final_gate_decision = _require_string(data, "final_gate_decision", context)
    if final_gate_decision != FINAL_GATE_DECISION:
        raise _review_error(context, f"final_gate_decision must be {FINAL_GATE_DECISION}")

    return PerChainLegalReviewGovernance(
        schema_version=schema_version,
        generated_on=_parse_date(_require_string(data, "generated_on", context), context),
        chain_public_nutrition_ref=chain_public_nutrition_ref,
        pr12_landed_pr=pr12_landed_pr,
        source=source,
        source_classification=source_classification,
        source_family=source_family,
        evidence_policy=evidence_policy,
        blocked_methods=blocked_methods,
        per_chain_reviews=per_chain_reviews,
        next_recommended_lane=next_recommended_lane,
        final_gate_decision=final_gate_decision,
        notes=_require_string(data, "notes", context),
    )


def load_per_chain_legal_review_governance(
    governance_path: Path | str,
    *,
    chain_public_nutrition: ChainPublicNutritionGovernance,
    expected_chain_public_nutrition_ref: str | None = None,
) -> PerChainLegalReviewGovernance:
    """Load and validate a PR13 per-chain legal review JSON artifact."""

    path = Path(governance_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PerChainLegalReviewError(f"Cannot read per-chain legal review {path}: {exc}") from exc
    return parse_per_chain_legal_review_governance(
        payload,
        chain_public_nutrition=chain_public_nutrition,
        expected_chain_public_nutrition_ref=expected_chain_public_nutrition_ref,
        context=str(path),
    )


def build_per_chain_legal_review_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    coverage_path: Path | str,
    chain_public_nutrition_path: Path | str,
    governance_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR13 governance gate."""

    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    expected_coverage_ref = _relative_repo_path(coverage_path)
    expected_chain_ref = _relative_repo_path(chain_public_nutrition_path)
    report: dict[str, object] = {
        "success": False,
        "dry_run": True,
        "source": CHAIN_PUBLIC_SOURCE,
        "source_classification": "unresolved",
        "evidence_policy": EVIDENCE_POLICY,
        "blocked_methods": list(BLOCKED_METHODS),
        "chain_page_ids": list(EXPECTED_CHAIN_IDS),
        "next_recommended_lane": NEXT_RECOMMENDED_LANE,
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "network_allowed": False,
        "db_writes_allowed": False,
        "api_calls_allowed": False,
        "source_download_allowed": False,
        "scraping_allowed": False,
        "cache_authority_allowed": False,
        "redistribution_allowed": False,
        "public_dataset_claim_allowed": False,
        "automation_allowed": False,
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
        coverage = load_source_gap_audit(
            coverage_path,
            catalog=catalog,
            onboarding=onboarding,
            expected_catalog_ref=expected_catalog_ref,
            expected_onboarding_ref=expected_onboarding_ref,
        )
        chain_public_nutrition = load_chain_public_nutrition_governance(
            chain_public_nutrition_path,
            catalog=catalog,
            onboarding=onboarding,
            coverage=coverage,
            expected_catalog_ref=expected_catalog_ref,
            expected_onboarding_ref=expected_onboarding_ref,
            expected_coverage_ref=expected_coverage_ref,
        )
        governance = load_per_chain_legal_review_governance(
            governance_path,
            chain_public_nutrition=chain_public_nutrition,
            expected_chain_public_nutrition_ref=expected_chain_ref,
        )
    except (
        ChainPublicNutritionGovernanceError,
        PerChainLegalReviewError,
        SourceCatalogError,
        SourceOnboardingError,
        SourceGapAuditError,
    ) as exc:
        report["validation_errors"] = [str(exc)]
        return report

    report.update(
        {
            "success": True,
            "chain_public_nutrition_ref": governance.chain_public_nutrition_ref,
            "pr12_landed_pr": governance.pr12_landed_pr,
            "legal_review_status": {
                review.chain_id: review.legal_review_status
                for review in governance.per_chain_reviews
            },
            "anti_scraping_review_status": {
                review.chain_id: review.anti_scraping_review_status
                for review in governance.per_chain_reviews
            },
            "cache_decisions": {
                review.chain_id: review.cache_decision for review in governance.per_chain_reviews
            },
            "redistribution_decisions": {
                review.chain_id: review.redistribution_decision
                for review in governance.per_chain_reviews
            },
            "official_urls": {
                review.chain_id: review.official_url for review in governance.per_chain_reviews
            },
        }
    )
    return report
