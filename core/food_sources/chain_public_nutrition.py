"""
Deterministic chain public nutrition pages governance gate.

RU: Файловая проверка PR12: публичные страницы сетей ресторанов являются
только ручным evidence lane, а не источником ingest/runtime authority.
EN: File-only PR12 validation: public chain nutrition pages are manual
evidence only, not ingest/runtime authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from core.food_sources.source_catalog import (
    SourceCatalog,
    SourceCatalogEntry,
    SourceCatalogError,
    load_source_catalog,
)
from core.food_sources.source_gap_audit import (
    SourceGapAudit,
    SourceGapAuditError,
    load_source_gap_audit,
)
from core.food_sources.source_onboarding import (
    SourceOnboarding,
    SourceOnboardingEntry,
    SourceOnboardingError,
    load_source_onboarding,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GOVERNANCE_SCHEMA_RE = re.compile(r"^food-data-chain-public-nutrition-governance\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

CHAIN_PUBLIC_SOURCE = "chain_public_nutrition_pages"
EXPECTED_CHAIN_PAGE_IDS = ("mcdonalds_us", "chipotle_us", "starbucks_us")
FINAL_GATE_DECISION = "chain_public_nutrition_governance_only_no_ingest"
NEXT_RECOMMENDED_LANE = "per_chain_legal_anti_scraping_review"
EVIDENCE_POLICY = "manual_evidence_only_legal_review_required"

ALLOWED_EVIDENCE_TYPES = (
    "official_public_url_citation",
    "manual_screenshot_internal_review",
)

BLOCKED_EVIDENCE_TYPES = (
    "scraping",
    "automated_collection",
    "api_call",
    "download",
    "social_media_harvest",
    "login_or_paywall_bypass",
    "cache_authority",
    "redistribution",
    "runtime_authority",
    "public_dataset_claim",
)

_EXPECTED_CHAIN_HOSTS: dict[str, str] = {
    "mcdonalds_us": "www.mcdonalds.com",
    "chipotle_us": "www.chipotle.com",
    "starbucks_us": "www.starbucks.com",
}

_SOCIAL_MEDIA_HOST_FRAGMENTS = (
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "linkedin.com",
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
    "redistribution_allowed": False,
    "public_dataset_claim_allowed": False,
    "automation_allowed": False,
    "file_only": True,
}

_GOVERNANCE_KEYS = frozenset(
    {
        "schema_version",
        "generated_on",
        "catalog_ref",
        "onboarding_ref",
        "coverage_ref",
        "pr11_landed_pr",
        "source",
        "source_classification",
        "source_family",
        "evidence_policy",
        "allowed_evidence_types",
        "blocked_evidence_types",
        "representative_chain_pages",
        "runtime_cutover",
        "digitalocean_postgres_load",
        "bulk_ingest",
        "network_allowed",
        "db_writes_allowed",
        "api_calls_allowed",
        "source_download_allowed",
        "scraping_allowed",
        "paid_source_use_allowed",
        "redistribution_allowed",
        "public_dataset_claim_allowed",
        "automation_allowed",
        "file_only",
        "next_recommended_lane",
        "final_gate_decision",
        "notes",
    }
)

_CHAIN_PAGE_KEYS = frozenset(
    {
        "chain_id",
        "chain_name",
        "official_url",
        "evidence_type",
        "page_access",
        "js_required",
        "authority_decision",
        "approved_ingest",
        "approved_runtime_authority",
        "scraping_allowed",
        "api_calls_allowed",
        "redistribution_allowed",
        "automation_allowed",
        "notes",
    }
)


class ChainPublicNutritionGovernanceError(ValueError):
    """Raised when the PR12 chain public nutrition governance artifact is invalid."""


@dataclass(frozen=True)
class RepresentativeChainPage:
    """One official chain page recorded as manual evidence only."""

    chain_id: str
    chain_name: str
    official_url: str
    evidence_type: str
    page_access: str
    js_required: bool
    authority_decision: str
    approved_ingest: bool
    approved_runtime_authority: bool
    scraping_allowed: bool
    api_calls_allowed: bool
    redistribution_allowed: bool
    automation_allowed: bool
    notes: str


@dataclass(frozen=True)
class ChainPublicNutritionGovernance:
    """Validated PR12 chain public nutrition governance artifact."""

    schema_version: str
    generated_on: date
    catalog_ref: str
    onboarding_ref: str
    coverage_ref: str
    pr11_landed_pr: int
    source: str
    source_classification: str
    source_family: str
    evidence_policy: str
    allowed_evidence_types: tuple[str, ...]
    blocked_evidence_types: tuple[str, ...]
    representative_chain_pages: tuple[RepresentativeChainPage, ...]
    next_recommended_lane: str
    final_gate_decision: str
    notes: str


def _governance_error(context: str, detail: str) -> ChainPublicNutritionGovernanceError:
    return ChainPublicNutritionGovernanceError(
        f"Invalid chain public nutrition governance {context}: {detail}"
    )


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _governance_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _governance_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _governance_error(context, f"missing non-empty string '{key}'")
    return value.strip()


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _governance_error(context, f"'{key}' must be a boolean")
    return value


def _require_int(data: dict[str, object], key: str, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _governance_error(context, f"'{key}' must be an integer")
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
        raise _governance_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _governance_error(context, f"'{key}[{index}]' must be a non-empty string")
        normalized = item.strip()
        if normalized in seen:
            raise _governance_error(context, f"'{key}' contains duplicate value {normalized!r}")
        seen.add(normalized)
        items.append(normalized)
    result = tuple(items)
    if expected is not None and result != expected:
        raise _governance_error(context, f"'{key}' must be exactly: {', '.join(expected)}")
    return result


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _governance_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _governance_error(context, "generated_on must use YYYY-MM-DD") from exc


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
        raise _governance_error(
            context,
            "runtime_cutover, digitalocean_postgres_load, bulk_ingest, network_allowed, "
            "db_writes_allowed, api_calls_allowed, source_download_allowed, scraping_allowed, "
            "paid_source_use_allowed, redistribution_allowed, public_dataset_claim_allowed, "
            "and automation_allowed must be false; file_only must be true",
        )


def _validate_upstream_contracts(
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    coverage: SourceGapAudit,
) -> None:
    catalog_entry = _catalog_by_source(catalog).get(CHAIN_PUBLIC_SOURCE)
    if catalog_entry is None:
        raise _governance_error("<catalog>", f"missing {CHAIN_PUBLIC_SOURCE}")
    if (
        catalog_entry.source_classification != "unresolved"
        or catalog_entry.source_family != "restaurant_menu"
        or catalog_entry.active_update_source
        or catalog_entry.status != "blocked_unresolved"
        or catalog_entry.replacement_for != "menustat"
    ):
        raise _governance_error(
            "<catalog>",
            "chain_public_nutrition_pages must remain unresolved, blocked, and inactive",
        )

    onboarding_entry = _onboarding_by_source(onboarding).get(CHAIN_PUBLIC_SOURCE)
    if onboarding_entry is None:
        raise _governance_error("<onboarding>", f"missing {CHAIN_PUBLIC_SOURCE}")
    if (
        onboarding_entry.source_classification != "unresolved"
        or onboarding_entry.onboarding_status != "unresolved_blocked"
        or onboarding_entry.ingestion_path != "unresolved_identity_required"
        or onboarding_entry.cache_decision != "blocked_unresolved"
        or onboarding_entry.redistribution_decision != "blocked_unresolved"
    ):
        raise _governance_error(
            "<onboarding>",
            "chain_public_nutrition_pages must stay unresolved_blocked with no ingest path",
        )

    if coverage.pr10_landed_pr != 1597:
        raise _governance_error(
            "<coverage>", "PR11 coverage baseline must remain downstream of PR10 #1597"
        )
    coverage_by_source = {row.source: row for row in coverage.source_gap_decisions}
    gap_decision = coverage_by_source.get(CHAIN_PUBLIC_SOURCE)
    if gap_decision is None:
        raise _governance_error("<coverage>", f"missing {CHAIN_PUBLIC_SOURCE}")
    if (
        gap_decision.decision != "preferred_research_lane_blocked"
        or gap_decision.allowed_role != "manual_evidence_governance_candidate"
        or gap_decision.approved_ingest
        or gap_decision.approved_runtime_authority
        or gap_decision.api_calls_allowed
        or gap_decision.scraping_allowed
        or gap_decision.paid_source_use_allowed
    ):
        raise _governance_error(
            "<coverage>",
            "chain_public_nutrition_pages must stay blocked manual evidence in PR11 coverage",
        )


def _validate_official_url(chain_id: str, official_url: str, context: str) -> None:
    parsed = urlparse(official_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise _governance_error(context, "official_url must be an https URL")
    host = parsed.netloc.lower()
    if any(fragment in host for fragment in _SOCIAL_MEDIA_HOST_FRAGMENTS):
        raise _governance_error(context, "social-media URLs cannot be official nutrition evidence")
    expected_host = _EXPECTED_CHAIN_HOSTS.get(chain_id)
    if expected_host is None:
        raise _governance_error(context, f"unknown chain page id: {chain_id}")
    if host != expected_host:
        raise _governance_error(context, f"{chain_id} official_url host must be {expected_host}")


def _parse_chain_page(value: object, context: str) -> RepresentativeChainPage:
    data = _require_mapping(value, context)
    unexpected_keys = sorted(set(data) - _CHAIN_PAGE_KEYS)
    if unexpected_keys:
        raise _governance_error(
            context, f"unexpected chain page keys: {', '.join(unexpected_keys)}"
        )
    page = RepresentativeChainPage(
        chain_id=_require_string(data, "chain_id", context),
        chain_name=_require_string(data, "chain_name", context),
        official_url=_require_string(data, "official_url", context),
        evidence_type=_require_string(data, "evidence_type", context),
        page_access=_require_string(data, "page_access", context),
        js_required=_require_bool(data, "js_required", context),
        authority_decision=_require_string(data, "authority_decision", context),
        approved_ingest=_require_bool(data, "approved_ingest", context),
        approved_runtime_authority=_require_bool(data, "approved_runtime_authority", context),
        scraping_allowed=_require_bool(data, "scraping_allowed", context),
        api_calls_allowed=_require_bool(data, "api_calls_allowed", context),
        redistribution_allowed=_require_bool(data, "redistribution_allowed", context),
        automation_allowed=_require_bool(data, "automation_allowed", context),
        notes=_require_string(data, "notes", context),
    )
    _validate_official_url(page.chain_id, page.official_url, context)
    if page.evidence_type not in ALLOWED_EVIDENCE_TYPES:
        raise _governance_error(context, f"{page.chain_id} evidence_type is not allowed")
    if page.page_access not in {"public_web_page", "js_required_public_web_page"}:
        raise _governance_error(context, f"{page.chain_id} page_access is not allowed")
    if page.authority_decision != "manual_evidence_only_not_authority":
        raise _governance_error(context, f"{page.chain_id} cannot become source authority")
    if (
        page.approved_ingest
        or page.approved_runtime_authority
        or page.scraping_allowed
        or page.api_calls_allowed
        or page.redistribution_allowed
        or page.automation_allowed
    ):
        raise _governance_error(
            context,
            f"{page.chain_id} cannot approve ingest, runtime authority, scraping, API calls, redistribution, or automation",
        )
    return page


def parse_chain_public_nutrition_governance(
    payload: object,
    *,
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    coverage: SourceGapAudit,
    expected_catalog_ref: str | None = None,
    expected_onboarding_ref: str | None = None,
    expected_coverage_ref: str | None = None,
    context: str = "<chain-public-nutrition-governance>",
) -> ChainPublicNutritionGovernance:
    """Parse and validate the PR12 chain public nutrition governance artifact."""

    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _GOVERNANCE_KEYS)
    if unexpected_keys:
        raise _governance_error(context, f"unexpected keys: {', '.join(unexpected_keys)}")
    schema_version = _require_string(data, "schema_version", context)
    if not _GOVERNANCE_SCHEMA_RE.fullmatch(schema_version):
        raise _governance_error(
            context,
            "schema_version must look like food-data-chain-public-nutrition-governance.vN",
        )
    catalog_ref = _require_string(data, "catalog_ref", context)
    if expected_catalog_ref is not None and catalog_ref != expected_catalog_ref:
        raise _governance_error(context, f"catalog_ref must be {expected_catalog_ref!r}")
    onboarding_ref = _require_string(data, "onboarding_ref", context)
    if expected_onboarding_ref is not None and onboarding_ref != expected_onboarding_ref:
        raise _governance_error(context, f"onboarding_ref must be {expected_onboarding_ref!r}")
    coverage_ref = _require_string(data, "coverage_ref", context)
    if expected_coverage_ref is not None and coverage_ref != expected_coverage_ref:
        raise _governance_error(context, f"coverage_ref must be {expected_coverage_ref!r}")
    pr11_landed_pr = _require_int(data, "pr11_landed_pr", context)
    if pr11_landed_pr != 1601:
        raise _governance_error(context, "pr11_landed_pr must be 1601")
    source = _require_string(data, "source", context)
    if source != CHAIN_PUBLIC_SOURCE:
        raise _governance_error(context, f"source must be {CHAIN_PUBLIC_SOURCE}")
    source_classification = _require_string(data, "source_classification", context)
    if source_classification != "unresolved":
        raise _governance_error(context, "source_classification must remain unresolved")
    source_family = _require_string(data, "source_family", context)
    if source_family != "restaurant_menu":
        raise _governance_error(context, "source_family must be restaurant_menu")
    evidence_policy = _require_string(data, "evidence_policy", context)
    if evidence_policy != EVIDENCE_POLICY:
        raise _governance_error(context, f"evidence_policy must be {EVIDENCE_POLICY}")
    allowed_evidence_types = _require_string_tuple(
        data,
        "allowed_evidence_types",
        context,
        expected=ALLOWED_EVIDENCE_TYPES,
    )
    blocked_evidence_types = _require_string_tuple(
        data,
        "blocked_evidence_types",
        context,
        expected=BLOCKED_EVIDENCE_TYPES,
    )
    _require_safety_flags(data, context)
    _validate_upstream_contracts(catalog, onboarding, coverage)

    rows = data.get("representative_chain_pages")
    if not isinstance(rows, list):
        raise _governance_error(context, "representative_chain_pages must be a list")
    representative_chain_pages = tuple(
        _parse_chain_page(row, f"{context}.representative_chain_pages[{index}]")
        for index, row in enumerate(rows)
    )
    chain_page_order = tuple(page.chain_id for page in representative_chain_pages)
    if chain_page_order != EXPECTED_CHAIN_PAGE_IDS:
        raise _governance_error(
            context,
            "representative_chain_pages must be exactly: " + ", ".join(EXPECTED_CHAIN_PAGE_IDS),
        )

    next_recommended_lane = _require_string(data, "next_recommended_lane", context)
    if next_recommended_lane != NEXT_RECOMMENDED_LANE:
        raise _governance_error(context, f"next_recommended_lane must be {NEXT_RECOMMENDED_LANE}")
    final_gate_decision = _require_string(data, "final_gate_decision", context)
    if final_gate_decision != FINAL_GATE_DECISION:
        raise _governance_error(context, f"final_gate_decision must be {FINAL_GATE_DECISION}")

    return ChainPublicNutritionGovernance(
        schema_version=schema_version,
        generated_on=_parse_date(_require_string(data, "generated_on", context), context),
        catalog_ref=catalog_ref,
        onboarding_ref=onboarding_ref,
        coverage_ref=coverage_ref,
        pr11_landed_pr=pr11_landed_pr,
        source=source,
        source_classification=source_classification,
        source_family=source_family,
        evidence_policy=evidence_policy,
        allowed_evidence_types=allowed_evidence_types,
        blocked_evidence_types=blocked_evidence_types,
        representative_chain_pages=representative_chain_pages,
        next_recommended_lane=next_recommended_lane,
        final_gate_decision=final_gate_decision,
        notes=_require_string(data, "notes", context),
    )


def load_chain_public_nutrition_governance(
    governance_path: Path | str,
    *,
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    coverage: SourceGapAudit,
    expected_catalog_ref: str | None = None,
    expected_onboarding_ref: str | None = None,
    expected_coverage_ref: str | None = None,
) -> ChainPublicNutritionGovernance:
    """Load and validate a PR12 chain public nutrition governance JSON artifact."""

    path = Path(governance_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ChainPublicNutritionGovernanceError(
            f"Cannot read chain public nutrition governance {path}: {exc}"
        ) from exc
    return parse_chain_public_nutrition_governance(
        payload,
        catalog=catalog,
        onboarding=onboarding,
        coverage=coverage,
        expected_catalog_ref=expected_catalog_ref,
        expected_onboarding_ref=expected_onboarding_ref,
        expected_coverage_ref=expected_coverage_ref,
        context=str(path),
    )


def build_chain_public_nutrition_governance_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    coverage_path: Path | str,
    governance_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR12 governance gate."""

    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    expected_coverage_ref = _relative_repo_path(coverage_path)
    report: dict[str, object] = {
        "success": False,
        "dry_run": True,
        "source": CHAIN_PUBLIC_SOURCE,
        "source_classification": "unresolved",
        "evidence_policy": EVIDENCE_POLICY,
        "allowed_evidence_types": list(ALLOWED_EVIDENCE_TYPES),
        "blocked_evidence_types": list(BLOCKED_EVIDENCE_TYPES),
        "chain_page_ids": list(EXPECTED_CHAIN_PAGE_IDS),
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
        governance = load_chain_public_nutrition_governance(
            governance_path,
            catalog=catalog,
            onboarding=onboarding,
            coverage=coverage,
            expected_catalog_ref=expected_catalog_ref,
            expected_onboarding_ref=expected_onboarding_ref,
            expected_coverage_ref=expected_coverage_ref,
        )
    except (
        ChainPublicNutritionGovernanceError,
        SourceCatalogError,
        SourceOnboardingError,
        SourceGapAuditError,
    ) as exc:
        report["validation_errors"] = [str(exc)]
        return report

    report.update(
        {
            "success": True,
            "catalog_ref": governance.catalog_ref,
            "onboarding_ref": governance.onboarding_ref,
            "coverage_ref": governance.coverage_ref,
            "pr11_landed_pr": governance.pr11_landed_pr,
            "chain_page_decisions": {
                page.chain_id: page.authority_decision
                for page in governance.representative_chain_pages
            },
            "official_urls": {
                page.chain_id: page.official_url for page in governance.representative_chain_pages
            },
        }
    )
    return report
