"""
Deterministic recipe/dish corpus governance gate.

RU: Файловая проверка PR14: recipe/dish corpus candidates stay review-only.
EN: File-only PR14 validation: recipe/dish corpus candidates stay review-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from core.food_sources.chain_public_nutrition import (
    ChainPublicNutritionGovernanceError,
    load_chain_public_nutrition_governance,
)
from core.food_sources.per_chain_legal_review import (
    NEXT_RECOMMENDED_LANE as PR13_NEXT_RECOMMENDED_LANE,
    PerChainLegalReviewError,
    load_per_chain_legal_review_governance,
)
from core.food_sources.source_catalog import SourceCatalogError, load_source_catalog
from core.food_sources.source_gap_audit import (
    SourceGapAudit,
    SourceGapAuditError,
    load_source_gap_audit,
)
from core.food_sources.source_onboarding import (
    SourceOnboarding,
    SourceOnboardingError,
    load_source_onboarding,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_RE = re.compile(r"^food-data-recipe-dish-corpus-governance\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

RECIPE_DISH_CORPUS_SOURCE = "recipe_dish_corpora"
EXPECTED_RECIPE_SOURCES = ("edamam_food_database", "spoonacular")
EVIDENCE_POLICY = "recipe_dish_corpus_governance_only_no_source_use"
FINAL_GATE_DECISION = "recipe_dish_corpus_governance_only_no_ingest"
NEXT_RECOMMENDED_LANE = "preference_recipe_mapping_contract"
PER_CHAIN_LEGAL_REF = (
    "docs/architecture/FOOD_DATA_PER_CHAIN_LEGAL_ANTI_SCRAPING_PR13_2026-04-30.json"
)

BLOCKED_METHODS = (
    "scraping",
    "automated_collection",
    "api_call",
    "download",
    "paid_api_use",
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
    "paid_source_use_allowed": False,
    "cache_authority_allowed": False,
    "redistribution_allowed": False,
    "public_dataset_claim_allowed": False,
    "automation_allowed": False,
    "file_only": True,
}

_FORBIDDEN_NOTE_PHRASES = (
    "approved api",
    "api approved",
    "api calls approved",
    "approved for api",
    "allowed api",
    "api allowed",
    "api calls allowed",
    "api calls are allowed",
    "allowed for api",
    "allowed api calls",
    "approved for ingest",
    "ingest approved",
    "ingest is approved",
    "approved ingest",
    "allowed for ingest",
    "ingest allowed",
    "allowed ingest",
    "approved for runtime",
    "runtime approved",
    "runtime use approved",
    "runtime use is approved",
    "approved runtime",
    "allowed for runtime",
    "runtime allowed",
    "runtime use allowed",
    "runtime use is allowed",
    "allowed runtime",
    "runtime authority allowed",
    "approved for cache",
    "cache approved",
    "approved cache",
    "allowed for cache",
    "cache allowed",
    "allowed cache",
    "cache authority allowed",
    "approved for redistribution",
    "redistribution approved",
    "approved redistribution",
    "allowed for redistribution",
    "redistribution allowed",
    "allowed redistribution",
    "paid source approved",
    "approved paid source",
    "paid source allowed",
    "allowed paid source",
    "paid source use allowed",
    "paid api use allowed",
    "paid api use is allowed",
    "source use approved",
    "approved source use",
    "source use allowed",
    "source use is allowed",
    "allowed source use",
    "download allowed",
    "downloads allowed",
    "source download allowed",
    "db writes allowed",
    "database writes allowed",
    "product display allowed",
)

_REVIEW_FLAG_KEYS = (
    "approved_ingest",
    "approved_runtime_authority",
    "scraping_allowed",
    "automation_allowed",
    "api_calls_allowed",
    "source_download_allowed",
    "db_writes_allowed",
    "paid_source_use_allowed",
    "cache_authority_allowed",
    "redistribution_allowed",
)

_GOVERNANCE_KEYS = frozenset(
    {
        "schema_version",
        "generated_on",
        "per_chain_legal_ref",
        "pr13_landed_pr",
        "source",
        "source_classification",
        "source_family",
        "evidence_policy",
        "blocked_methods",
        "recipe_corpus_reviews",
        "runtime_cutover",
        "digitalocean_postgres_load",
        "bulk_ingest",
        "network_allowed",
        "db_writes_allowed",
        "api_calls_allowed",
        "source_download_allowed",
        "scraping_allowed",
        "paid_source_use_allowed",
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
        "source",
        "source_classification",
        "source_family",
        "legal_review_status",
        "contract_review_status",
        "cache_decision",
        "display_decision",
        "attribution_decision",
        "redistribution_decision",
        "freshness_review_status",
        "schema_review_status",
        "rollback_requirement",
        "allowed_role",
        "approved_ingest",
        "approved_runtime_authority",
        "scraping_allowed",
        "automation_allowed",
        "api_calls_allowed",
        "source_download_allowed",
        "db_writes_allowed",
        "paid_source_use_allowed",
        "cache_authority_allowed",
        "redistribution_allowed",
        "notes",
    }
)


class RecipeDishCorpusGovernanceError(ValueError):
    """Raised when the PR14 recipe/dish corpus governance artifact is invalid."""


@dataclass(frozen=True)
class RecipeCorpusReview:
    """One recipe/dish corpus source review placeholder."""

    source: str
    source_classification: str
    source_family: str
    legal_review_status: str
    contract_review_status: str
    cache_decision: str
    display_decision: str
    attribution_decision: str
    redistribution_decision: str
    freshness_review_status: str
    schema_review_status: str
    rollback_requirement: str
    allowed_role: str
    notes: str


@dataclass(frozen=True)
class RecipeDishCorpusGovernance:
    """Validated PR14 recipe/dish corpus governance artifact."""

    schema_version: str
    generated_on: date
    per_chain_legal_ref: str
    pr13_landed_pr: int
    source: str
    source_classification: str
    source_family: str
    evidence_policy: str
    blocked_methods: tuple[str, ...]
    recipe_corpus_reviews: tuple[RecipeCorpusReview, ...]
    next_recommended_lane: str
    final_gate_decision: str
    notes: str


def _governance_error(context: str, detail: str) -> RecipeDishCorpusGovernanceError:
    return RecipeDishCorpusGovernanceError(
        f"Invalid recipe/dish corpus governance {context}: {detail}"
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
    expected: tuple[str, ...],
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
    if result != expected:
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


def _require_safety_flags(data: dict[str, object], context: str) -> None:
    safety_flags = {key: _require_bool(data, key, context) for key in _SAFETY_FLAG_TEMPLATE}
    if safety_flags != _SAFETY_FLAG_TEMPLATE:
        raise _governance_error(
            context,
            "runtime_cutover, digitalocean_postgres_load, bulk_ingest, network_allowed, "
            "db_writes_allowed, api_calls_allowed, source_download_allowed, scraping_allowed, "
            "paid_source_use_allowed, cache_authority_allowed, redistribution_allowed, "
            "public_dataset_claim_allowed, and automation_allowed must be false; file_only must be true",
        )


def _require_safe_notes(value: str, context: str) -> str:
    normalized = " ".join(value.lower().replace("-", " ").replace("_", " ").split())
    for phrase in _FORBIDDEN_NOTE_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", normalized):
            raise _governance_error(
                context,
                "notes must not contradict no-use governance by approving API, ingest, "
                "runtime, cache, redistribution, paid source, or source use",
            )
    return value


def _onboarding_by_source(onboarding: SourceOnboarding) -> dict[str, object]:
    return {entry.source: entry for entry in onboarding.sources}


def _coverage_gap_sources(coverage: SourceGapAudit) -> dict[str, object]:
    return {entry.source: entry for entry in coverage.source_gap_decisions}


def _parse_recipe_review(
    value: object,
    *,
    onboarding_sources: dict[str, object],
    coverage_sources: dict[str, object],
    context: str,
) -> RecipeCorpusReview:
    data = _require_mapping(value, context)
    unexpected_keys = sorted(set(data) - _REVIEW_KEYS)
    if unexpected_keys:
        raise _governance_error(
            context, f"unexpected recipe review keys: {', '.join(unexpected_keys)}"
        )
    source = _require_string(data, "source", context)
    if source not in EXPECTED_RECIPE_SOURCES:
        raise _governance_error(context, f"unknown recipe/dish corpus source: {source}")
    onboarding_entry = onboarding_sources.get(source)
    coverage_entry = coverage_sources.get(source)
    if onboarding_entry is None or coverage_entry is None:
        raise _governance_error(context, f"{source} must exist in onboarding and coverage audits")
    if any(_require_bool(data, key, context) for key in _REVIEW_FLAG_KEYS):
        raise _governance_error(
            context,
            f"{source} cannot approve ingest, runtime authority, scraping, automation, API calls, "
            "downloads, DB writes, paid source use, cache authority, or redistribution",
        )

    source_classification = _require_string(data, "source_classification", context)
    source_family = _require_string(data, "source_family", context)
    if source_classification != getattr(onboarding_entry, "source_classification"):
        raise _governance_error(context, f"{source} source_classification must match onboarding")
    if source_family != "recipe_corpus":
        raise _governance_error(context, f"{source} source_family must be recipe_corpus")
    if source_family != getattr(onboarding_entry, "source_family"):
        raise _governance_error(context, f"{source} source_family must match onboarding")
    if getattr(onboarding_entry, "onboarding_status") != "contract_review_blocked":
        raise _governance_error(
            context, f"{source} onboarding_status must remain contract_review_blocked"
        )
    if getattr(onboarding_entry, "ingestion_path") != "commercial_contract_required":
        raise _governance_error(
            context, f"{source} ingestion_path must remain commercial_contract_required"
        )
    if getattr(onboarding_entry, "cache_decision") != "blocked_contract_required":
        raise _governance_error(context, f"{source} onboarding cache_decision must remain blocked")
    if getattr(onboarding_entry, "display_decision") != "blocked_contract_required":
        raise _governance_error(
            context, f"{source} onboarding display_decision must remain blocked"
        )
    if getattr(onboarding_entry, "redistribution_decision") != "contract_required":
        raise _governance_error(
            context, f"{source} onboarding redistribution_decision must require contract"
        )
    if getattr(coverage_entry, "approved_ingest") or getattr(
        coverage_entry, "approved_runtime_authority"
    ):
        raise _governance_error(
            context, f"{source} coverage audit must not approve ingest/runtime authority"
        )
    if getattr(coverage_entry, "api_calls_allowed") or getattr(
        coverage_entry, "paid_source_use_allowed"
    ):
        raise _governance_error(
            context, f"{source} coverage audit must not approve API or paid source use"
        )

    review = RecipeCorpusReview(
        source=source,
        source_classification=source_classification,
        source_family=source_family,
        legal_review_status=_require_string(data, "legal_review_status", context),
        contract_review_status=_require_string(data, "contract_review_status", context),
        cache_decision=_require_string(data, "cache_decision", context),
        display_decision=_require_string(data, "display_decision", context),
        attribution_decision=_require_string(data, "attribution_decision", context),
        redistribution_decision=_require_string(data, "redistribution_decision", context),
        freshness_review_status=_require_string(data, "freshness_review_status", context),
        schema_review_status=_require_string(data, "schema_review_status", context),
        rollback_requirement=_require_string(data, "rollback_requirement", context),
        allowed_role=_require_string(data, "allowed_role", context),
        notes=_require_safe_notes(_require_string(data, "notes", context), context),
    )
    if review.legal_review_status != "required_not_approved":
        raise _governance_error(
            context, f"{source} legal_review_status must be required_not_approved"
        )
    if review.contract_review_status != "required_not_approved":
        raise _governance_error(
            context, f"{source} contract_review_status must be required_not_approved"
        )
    if review.cache_decision != "blocked_contract_required":
        raise _governance_error(
            context, f"{source} cache_decision must be blocked_contract_required"
        )
    if review.display_decision != "blocked_contract_required":
        raise _governance_error(
            context, f"{source} display_decision must be blocked_contract_required"
        )
    if review.attribution_decision != "required_not_approved":
        raise _governance_error(
            context, f"{source} attribution_decision must be required_not_approved"
        )
    if review.redistribution_decision != "contract_required":
        raise _governance_error(
            context, f"{source} redistribution_decision must be contract_required"
        )
    if review.freshness_review_status != "required_not_approved":
        raise _governance_error(
            context, f"{source} freshness_review_status must be required_not_approved"
        )
    if review.schema_review_status != "required_not_approved":
        raise _governance_error(
            context, f"{source} schema_review_status must be required_not_approved"
        )
    if (
        review.rollback_requirement
        != "required_before_any_future_source_use_ingest_or_runtime_lane"
    ):
        raise _governance_error(context, f"{source} rollback_requirement is not allowed")
    allowed_roles = {
        "edamam_food_database": "adjacent_recipe_food_db_review_only",
        "spoonacular": "deferred_recipe_experiment_candidate_only",
    }
    if review.allowed_role != allowed_roles[source]:
        raise _governance_error(context, f"{source} allowed_role is not allowed")
    return review


def parse_recipe_dish_corpus_governance(
    payload: object,
    *,
    onboarding: SourceOnboarding,
    coverage: SourceGapAudit,
    expected_per_chain_legal_ref: str | None = None,
    pr13_next_recommended_lane: str = PR13_NEXT_RECOMMENDED_LANE,
    context: str = "<recipe-dish-corpus-governance>",
) -> RecipeDishCorpusGovernance:
    """Parse and validate the PR14 recipe/dish corpus governance artifact."""

    if pr13_next_recommended_lane != "recipe_dish_corpus_governance":
        raise _governance_error(context, "PR13 must recommend recipe_dish_corpus_governance")
    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _GOVERNANCE_KEYS)
    if unexpected_keys:
        raise _governance_error(context, f"unexpected keys: {', '.join(unexpected_keys)}")
    schema_version = _require_string(data, "schema_version", context)
    if not _SCHEMA_RE.fullmatch(schema_version):
        raise _governance_error(
            context, "schema_version must look like food-data-recipe-dish-corpus-governance.vN"
        )
    per_chain_legal_ref = _require_string(data, "per_chain_legal_ref", context)
    expected_ref = expected_per_chain_legal_ref or PER_CHAIN_LEGAL_REF
    if per_chain_legal_ref != expected_ref:
        raise _governance_error(context, f"per_chain_legal_ref must be {expected_ref!r}")
    pr13_landed_pr = _require_int(data, "pr13_landed_pr", context)
    if pr13_landed_pr != 1613:
        raise _governance_error(context, "pr13_landed_pr must be 1613")
    source = _require_string(data, "source", context)
    if source != RECIPE_DISH_CORPUS_SOURCE:
        raise _governance_error(context, f"source must be {RECIPE_DISH_CORPUS_SOURCE}")
    source_classification = _require_string(data, "source_classification", context)
    if source_classification != "commercial_contract_review_only":
        raise _governance_error(
            context, "source_classification must be commercial_contract_review_only"
        )
    source_family = _require_string(data, "source_family", context)
    if source_family != "recipe_corpus":
        raise _governance_error(context, "source_family must be recipe_corpus")
    evidence_policy = _require_string(data, "evidence_policy", context)
    if evidence_policy != EVIDENCE_POLICY:
        raise _governance_error(context, f"evidence_policy must be {EVIDENCE_POLICY}")
    blocked_methods = _require_string_tuple(
        data, "blocked_methods", context, expected=BLOCKED_METHODS
    )
    _require_safety_flags(data, context)

    rows = data.get("recipe_corpus_reviews")
    if not isinstance(rows, list):
        raise _governance_error(context, "recipe_corpus_reviews must be a list")
    onboarding_sources = _onboarding_by_source(onboarding)
    coverage_sources = _coverage_gap_sources(coverage)
    recipe_corpus_reviews = tuple(
        _parse_recipe_review(
            row,
            onboarding_sources=onboarding_sources,
            coverage_sources=coverage_sources,
            context=f"{context}.recipe_corpus_reviews[{index}]",
        )
        for index, row in enumerate(rows)
    )
    source_order = tuple(review.source for review in recipe_corpus_reviews)
    if source_order != EXPECTED_RECIPE_SOURCES:
        raise _governance_error(
            context, "recipe_corpus_reviews must be exactly: " + ", ".join(EXPECTED_RECIPE_SOURCES)
        )

    next_recommended_lane = _require_string(data, "next_recommended_lane", context)
    if next_recommended_lane != NEXT_RECOMMENDED_LANE:
        raise _governance_error(context, f"next_recommended_lane must be {NEXT_RECOMMENDED_LANE}")
    final_gate_decision = _require_string(data, "final_gate_decision", context)
    if final_gate_decision != FINAL_GATE_DECISION:
        raise _governance_error(context, f"final_gate_decision must be {FINAL_GATE_DECISION}")

    return RecipeDishCorpusGovernance(
        schema_version=schema_version,
        generated_on=_parse_date(_require_string(data, "generated_on", context), context),
        per_chain_legal_ref=per_chain_legal_ref,
        pr13_landed_pr=pr13_landed_pr,
        source=source,
        source_classification=source_classification,
        source_family=source_family,
        evidence_policy=evidence_policy,
        blocked_methods=blocked_methods,
        recipe_corpus_reviews=recipe_corpus_reviews,
        next_recommended_lane=next_recommended_lane,
        final_gate_decision=final_gate_decision,
        notes=_require_safe_notes(_require_string(data, "notes", context), context),
    )


def load_recipe_dish_corpus_governance(
    governance_path: Path | str,
    *,
    onboarding: SourceOnboarding,
    coverage: SourceGapAudit,
    expected_per_chain_legal_ref: str | None = None,
    pr13_next_recommended_lane: str = PR13_NEXT_RECOMMENDED_LANE,
) -> RecipeDishCorpusGovernance:
    """Load and validate a PR14 recipe/dish corpus governance JSON artifact."""

    path = Path(governance_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RecipeDishCorpusGovernanceError(
            f"Cannot read recipe/dish corpus governance {path}: {exc}"
        ) from exc
    return parse_recipe_dish_corpus_governance(
        payload,
        onboarding=onboarding,
        coverage=coverage,
        expected_per_chain_legal_ref=expected_per_chain_legal_ref,
        pr13_next_recommended_lane=pr13_next_recommended_lane,
        context=str(path),
    )


def build_recipe_dish_corpus_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    coverage_path: Path | str,
    chain_public_nutrition_path: Path | str,
    per_chain_legal_path: Path | str,
    governance_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR14 governance gate."""

    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    expected_coverage_ref = _relative_repo_path(coverage_path)
    expected_chain_ref = _relative_repo_path(chain_public_nutrition_path)
    expected_per_chain_ref = _relative_repo_path(per_chain_legal_path)
    report: dict[str, object] = {
        "success": False,
        "dry_run": True,
        "source": RECIPE_DISH_CORPUS_SOURCE,
        "source_classification": "commercial_contract_review_only",
        "source_family": "recipe_corpus",
        "evidence_policy": EVIDENCE_POLICY,
        "blocked_methods": list(BLOCKED_METHODS),
        "recipe_sources": list(EXPECTED_RECIPE_SOURCES),
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
        chain_public_nutrition = load_chain_public_nutrition_governance(
            chain_public_nutrition_path,
            catalog=catalog,
            onboarding=onboarding,
            coverage=coverage,
            expected_catalog_ref=expected_catalog_ref,
            expected_onboarding_ref=expected_onboarding_ref,
            expected_coverage_ref=expected_coverage_ref,
        )
        per_chain_legal = load_per_chain_legal_review_governance(
            per_chain_legal_path,
            chain_public_nutrition=chain_public_nutrition,
            expected_chain_public_nutrition_ref=expected_chain_ref,
        )
        governance = load_recipe_dish_corpus_governance(
            governance_path,
            onboarding=onboarding,
            coverage=coverage,
            expected_per_chain_legal_ref=expected_per_chain_ref,
            pr13_next_recommended_lane=per_chain_legal.next_recommended_lane,
        )
    except (
        ChainPublicNutritionGovernanceError,
        PerChainLegalReviewError,
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
            "per_chain_legal_ref": governance.per_chain_legal_ref,
            "pr13_landed_pr": governance.pr13_landed_pr,
            "legal_review_status": {
                review.source: review.legal_review_status
                for review in governance.recipe_corpus_reviews
            },
            "contract_review_status": {
                review.source: review.contract_review_status
                for review in governance.recipe_corpus_reviews
            },
            "cache_decisions": {
                review.source: review.cache_decision for review in governance.recipe_corpus_reviews
            },
            "redistribution_decisions": {
                review.source: review.redistribution_decision
                for review in governance.recipe_corpus_reviews
            },
            "allowed_roles": {
                review.source: review.allowed_role for review in governance.recipe_corpus_reviews
            },
        }
    )
    return report
