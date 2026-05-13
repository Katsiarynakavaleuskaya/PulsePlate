"""
Deterministic preference-to-recipe mapping contract gate.

RU: Файловая проверка PR15: preference mapping stays contract-only.
EN: File-only PR15 validation: preference-to-recipe mapping stays contract-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from core.food_sources.recipe_dish_corpus import (
    EVIDENCE_POLICY as PR14_EVIDENCE_POLICY,
    FINAL_GATE_DECISION as PR14_FINAL_GATE_DECISION,
    NEXT_RECOMMENDED_LANE as PR14_NEXT_RECOMMENDED_LANE,
    RecipeDishCorpusGovernance,
    RecipeDishCorpusGovernanceError,
    load_recipe_dish_corpus_governance,
)
from core.food_sources.source_catalog import SourceCatalogError, load_source_catalog
from core.food_sources.source_gap_audit import (
    SourceGapAudit,
    SourceGapAuditError,
    load_source_gap_audit,
)
from core.food_sources.source_onboarding import SourceOnboardingError, load_source_onboarding

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_RE = re.compile(r"^food-data-preference-recipe-mapping-contract\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SOURCE = "preference_menu_planning"
SOURCE_CLASSIFICATION = "planning_contract_governance_only"
SOURCE_FAMILY = "preference_recipe_mapping"
EVIDENCE_POLICY = "preference_recipe_mapping_contract_only_no_source_use"
FINAL_GATE_DECISION = "preference_recipe_mapping_contract_only_no_ingest"
NEXT_RECOMMENDED_LANE = "preference_recipe_mapping_contract_review_closeout"
EXPECTED_MAPPING_KEYS = (
    "mediterranean_pattern",
    "gluten_free_constraint",
    "high_protein_preference",
)
EXPECTED_ALLOWED_ROLES = {
    "mediterranean_pattern": "preference_category_contract_only",
    "gluten_free_constraint": "constraint_mapping_contract_only",
    "high_protein_preference": "macro_preference_contract_only",
}
EXPECTED_COVERAGE_REF = "docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json"
EXPECTED_RECIPE_DISH_CORPUS_REF = (
    "docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json"
)
EXPECTED_PR11_PREFERENCE_COVERAGE_DECISION = "requires_dish_mapping"
EXPECTED_PR11_PREFERENCE_GAP_STATUS = "planner_gap_not_source_authority"
EXPECTED_PR11_PREFERENCE_AUTHORITY_DECISION = "not_approved"
EXPECTED_PR11_PREFERENCE_NEXT_ACTION = "preference_recipe_mapping_contract"

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
    "recipe_text_authority",
    "user_preference_text_authority",
    "llm_output_authority",
    "nutrition_authority",
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
    "recipe_text_authority_allowed": False,
    "user_preference_text_authority_allowed": False,
    "llm_output_authority_allowed": False,
    "nutrition_authority_allowed": False,
    "file_only": True,
}

_MAPPING_FLAG_KEYS = (
    "approved_ingest",
    "approved_runtime_authority",
    "source_use_allowed",
    "db_writes_allowed",
    "cache_authority_allowed",
    "recipe_text_authority_allowed",
    "user_preference_text_authority_allowed",
    "llm_output_authority_allowed",
)

_EXTRA_FORBIDDEN_NOTE_PHRASES = (
    "approved recipe text",
    "recipe text approved",
    "recipe text authority",
    "recipe text is authority",
    "user preference text authority",
    "preference text authority",
    "llm output authority",
    "llm output is authority",
    "nutrition authority approved",
    "nutrition authority allowed",
    "nutrition authority is approved",
    "nutrition authority is allowed",
    "approved nutrition authority",
    "allowed nutrition authority",
    "approved source use",
    "source use approved",
    "source use is approved",
    "source use allowed",
    "source use is allowed",
    "api calls allowed",
    "api calls are allowed",
    "api calls approved",
    "api calls are approved",
    "ingest approved",
    "ingest allowed",
    "ingest is allowed",
    "runtime authority allowed",
    "runtime authority is allowed",
    "runtime approved",
    "cache authority allowed",
    "cache authority is allowed",
    "db writes allowed",
    "db writes are allowed",
    "database writes allowed",
    "database writes are allowed",
    "paid api use approved",
    "paid api use is approved",
    "paid api use allowed",
    "paid api use is allowed",
    "paid source use approved",
    "paid source use is approved",
    "paid source use allowed",
    "paid source use is allowed",
    "downloads allowed",
    "download allowed",
    "source downloads allowed",
    "source download allowed",
    "scraping allowed",
    "scraping is allowed",
    "redistribution allowed",
    "redistribution is allowed",
    "public dataset claim allowed",
    "public dataset claim is allowed",
    "automation allowed",
    "automation is allowed",
    "product display allowed",
    "product display is allowed",
)


def _blocked_method_note_phrases() -> tuple[str, ...]:
    phrases: list[str] = []
    seen: set[str] = set()
    for method in BLOCKED_METHODS:
        normalized = method.replace("_", " ")
        variants = {normalized}
        if normalized == "api call":
            variants.add("api calls")
        elif normalized == "download":
            variants.update({"downloads", "source download", "source downloads"})
        elif normalized == "paid api use":
            variants.add("paid source use")
        elif normalized == "digitalocean postgres load":
            variants.add("postgres load")
        elif normalized == "automated collection":
            variants.add("automation")
        for variant in sorted(variants):
            for phrase in (
                f"{variant} approved",
                f"{variant} is approved",
                f"approved {variant}",
                f"{variant} allowed",
                f"{variant} is allowed",
                f"allowed {variant}",
            ):
                if phrase not in seen:
                    seen.add(phrase)
                    phrases.append(phrase)
    return tuple(phrases)


_FORBIDDEN_NOTE_PHRASES = _EXTRA_FORBIDDEN_NOTE_PHRASES + _blocked_method_note_phrases()

_GOVERNANCE_KEYS = frozenset(
    {
        "schema_version",
        "generated_on",
        "coverage_ref",
        "recipe_dish_corpus_ref",
        "pr11_landed_pr",
        "pr14_landed_pr",
        "source",
        "source_classification",
        "source_family",
        "evidence_policy",
        "blocked_methods",
        "mapping_contracts",
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
        "recipe_text_authority_allowed",
        "user_preference_text_authority_allowed",
        "llm_output_authority_allowed",
        "nutrition_authority_allowed",
        "file_only",
        "next_recommended_lane",
        "final_gate_decision",
        "notes",
    }
)

_MAPPING_KEYS = frozenset(
    {
        "mapping_key",
        "contract_status",
        "allowed_role",
        "approved_ingest",
        "approved_runtime_authority",
        "source_use_allowed",
        "db_writes_allowed",
        "cache_authority_allowed",
        "recipe_text_authority_allowed",
        "user_preference_text_authority_allowed",
        "llm_output_authority_allowed",
        "notes",
    }
)


class PreferenceRecipeMappingError(ValueError):
    """Raised when the PR15 preference recipe mapping contract is invalid."""


@dataclass(frozen=True)
class PreferenceMappingContract:
    """One preference mapping contract placeholder."""

    mapping_key: str
    contract_status: str
    allowed_role: str
    notes: str


@dataclass(frozen=True)
class PreferenceRecipeMappingGovernance:
    """Validated PR15 preference recipe mapping governance artifact."""

    schema_version: str
    generated_on: date
    coverage_ref: str
    recipe_dish_corpus_ref: str
    pr11_landed_pr: int
    pr14_landed_pr: int
    source: str
    source_classification: str
    source_family: str
    evidence_policy: str
    blocked_methods: tuple[str, ...]
    mapping_contracts: tuple[PreferenceMappingContract, ...]
    next_recommended_lane: str
    final_gate_decision: str
    notes: str


def _mapping_error(context: str, detail: str) -> PreferenceRecipeMappingError:
    return PreferenceRecipeMappingError(
        f"Invalid preference recipe mapping governance {context}: {detail}"
    )


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _mapping_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _mapping_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _mapping_error(context, f"missing non-empty string '{key}'")
    return value.strip()


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _mapping_error(context, f"'{key}' must be a boolean")
    return value


def _require_int(data: dict[str, object], key: str, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _mapping_error(context, f"'{key}' must be an integer")
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
        raise _mapping_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _mapping_error(context, f"'{key}[{index}]' must be a non-empty string")
        normalized = item.strip()
        if normalized in seen:
            raise _mapping_error(context, f"'{key}' contains duplicate value {normalized!r}")
        seen.add(normalized)
        items.append(normalized)
    result = tuple(items)
    if result != expected:
        raise _mapping_error(context, f"'{key}' must be exactly: {', '.join(expected)}")
    return result


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _mapping_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _mapping_error(context, "generated_on must use YYYY-MM-DD") from exc


def _relative_repo_path(path: Path | str) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _require_safety_flags(data: dict[str, object], context: str) -> None:
    safety_flags = {key: _require_bool(data, key, context) for key in _SAFETY_FLAG_TEMPLATE}
    if safety_flags != _SAFETY_FLAG_TEMPLATE:
        raise _mapping_error(
            context,
            "runtime, network, DB, API, download, scraping, paid source, cache, "
            "redistribution, public dataset, automation, recipe text authority, "
            "user preference text authority, LLM output authority, and nutrition authority "
            "flags must be false; file_only must be true",
        )


def _require_safe_notes(value: str, context: str) -> str:
    normalized = " ".join(value.lower().replace("-", " ").replace("_", " ").split())
    for phrase in _FORBIDDEN_NOTE_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", normalized):
            raise _mapping_error(
                context,
                "notes must not approve recipe text, preference text, LLM output, "
                "source use, ingest, runtime, cache, DB writes, display, or nutrition authority",
            )
    return value


def _coverage_domain_by_name(coverage: SourceGapAudit) -> dict[str, object]:
    return {entry.domain: entry for entry in coverage.coverage_domains}


def _require_pr14_handoff(
    recipe_dish_corpus: RecipeDishCorpusGovernance,
    context: str,
) -> None:
    if recipe_dish_corpus.next_recommended_lane != PR14_NEXT_RECOMMENDED_LANE:
        raise _mapping_error(context, "PR14 must recommend preference_recipe_mapping_contract")
    if recipe_dish_corpus.evidence_policy != PR14_EVIDENCE_POLICY:
        raise _mapping_error(context, f"PR14 evidence_policy must be {PR14_EVIDENCE_POLICY}")
    if recipe_dish_corpus.final_gate_decision != PR14_FINAL_GATE_DECISION:
        raise _mapping_error(
            context, f"PR14 final_gate_decision must be {PR14_FINAL_GATE_DECISION}"
        )


def _require_pr11_preference_handoff(coverage: SourceGapAudit, context: str) -> None:
    domains = _coverage_domain_by_name(coverage)
    preference_domain = domains.get(SOURCE)
    if preference_domain is None:
        raise _mapping_error(context, "PR11 must include preference_menu_planning")
    if (
        getattr(preference_domain, "coverage_decision")
        != EXPECTED_PR11_PREFERENCE_COVERAGE_DECISION
    ):
        raise _mapping_error(
            context,
            "PR11 preference_menu_planning coverage_decision must be "
            f"{EXPECTED_PR11_PREFERENCE_COVERAGE_DECISION}",
        )
    if getattr(preference_domain, "gap_status") != EXPECTED_PR11_PREFERENCE_GAP_STATUS:
        raise _mapping_error(
            context,
            f"PR11 preference_menu_planning gap_status must be {EXPECTED_PR11_PREFERENCE_GAP_STATUS}",
        )
    if (
        getattr(preference_domain, "authority_decision")
        != EXPECTED_PR11_PREFERENCE_AUTHORITY_DECISION
    ):
        raise _mapping_error(
            context,
            "PR11 preference_menu_planning authority_decision must be "
            f"{EXPECTED_PR11_PREFERENCE_AUTHORITY_DECISION}",
        )
    if getattr(preference_domain, "next_action") != EXPECTED_PR11_PREFERENCE_NEXT_ACTION:
        raise _mapping_error(
            context,
            "PR11 preference_menu_planning must recommend preference_recipe_mapping_contract",
        )
    if getattr(preference_domain, "approved_ingest") or getattr(
        preference_domain, "approved_runtime_authority"
    ):
        raise _mapping_error(
            context, "PR11 preference_menu_planning must not approve ingest/runtime authority"
        )


def _parse_mapping_contract(value: object, *, context: str) -> PreferenceMappingContract:
    data = _require_mapping(value, context)
    unexpected_keys = sorted(set(data) - _MAPPING_KEYS)
    if unexpected_keys:
        raise _mapping_error(context, f"unexpected mapping keys: {', '.join(unexpected_keys)}")
    mapping_key = _require_string(data, "mapping_key", context)
    if mapping_key not in EXPECTED_MAPPING_KEYS:
        raise _mapping_error(context, f"unknown mapping_key: {mapping_key}")
    if any(_require_bool(data, key, context) for key in _MAPPING_FLAG_KEYS):
        raise _mapping_error(
            context,
            f"{mapping_key} cannot approve source use, ingest, runtime authority, DB writes, "
            "cache authority, recipe text authority, user preference text authority, or LLM output authority",
        )
    contract_status = _require_string(data, "contract_status", context)
    if contract_status != "mapping_contract_required_not_approved":
        raise _mapping_error(
            context, f"{mapping_key} contract_status must be mapping_contract_required_not_approved"
        )
    allowed_role = _require_string(data, "allowed_role", context)
    if allowed_role != EXPECTED_ALLOWED_ROLES[mapping_key]:
        raise _mapping_error(context, f"{mapping_key} allowed_role is not allowed")
    return PreferenceMappingContract(
        mapping_key=mapping_key,
        contract_status=contract_status,
        allowed_role=allowed_role,
        notes=_require_safe_notes(_require_string(data, "notes", context), context),
    )


def parse_preference_recipe_mapping_governance(
    payload: object,
    *,
    coverage: SourceGapAudit,
    recipe_dish_corpus: RecipeDishCorpusGovernance,
    expected_coverage_ref: str | None = None,
    expected_recipe_dish_corpus_ref: str | None = None,
    context: str = "<preference-recipe-mapping-governance>",
) -> PreferenceRecipeMappingGovernance:
    """Parse and validate the PR15 preference recipe mapping contract artifact."""

    _require_pr14_handoff(recipe_dish_corpus, context)
    _require_pr11_preference_handoff(coverage, context)

    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _GOVERNANCE_KEYS)
    if unexpected_keys:
        raise _mapping_error(context, f"unexpected keys: {', '.join(unexpected_keys)}")
    schema_version = _require_string(data, "schema_version", context)
    if not _SCHEMA_RE.fullmatch(schema_version):
        raise _mapping_error(
            context, "schema_version must look like food-data-preference-recipe-mapping-contract.vN"
        )
    coverage_ref = _require_string(data, "coverage_ref", context)
    expected_cov_ref = expected_coverage_ref or EXPECTED_COVERAGE_REF
    if coverage_ref != expected_cov_ref:
        raise _mapping_error(context, f"coverage_ref must be {expected_cov_ref!r}")
    recipe_dish_corpus_ref = _require_string(data, "recipe_dish_corpus_ref", context)
    expected_recipe_ref = expected_recipe_dish_corpus_ref or EXPECTED_RECIPE_DISH_CORPUS_REF
    if recipe_dish_corpus_ref != expected_recipe_ref:
        raise _mapping_error(context, f"recipe_dish_corpus_ref must be {expected_recipe_ref!r}")
    pr11_landed_pr = _require_int(data, "pr11_landed_pr", context)
    if pr11_landed_pr != 1601:
        raise _mapping_error(context, "pr11_landed_pr must be 1601")
    pr14_landed_pr = _require_int(data, "pr14_landed_pr", context)
    if pr14_landed_pr != 1743:
        raise _mapping_error(context, "pr14_landed_pr must be 1743")
    source = _require_string(data, "source", context)
    if source != SOURCE:
        raise _mapping_error(context, f"source must be {SOURCE}")
    source_classification = _require_string(data, "source_classification", context)
    if source_classification != SOURCE_CLASSIFICATION:
        raise _mapping_error(context, f"source_classification must be {SOURCE_CLASSIFICATION}")
    source_family = _require_string(data, "source_family", context)
    if source_family != SOURCE_FAMILY:
        raise _mapping_error(context, f"source_family must be {SOURCE_FAMILY}")
    evidence_policy = _require_string(data, "evidence_policy", context)
    if evidence_policy != EVIDENCE_POLICY:
        raise _mapping_error(context, f"evidence_policy must be {EVIDENCE_POLICY}")
    blocked_methods = _require_string_tuple(
        data, "blocked_methods", context, expected=BLOCKED_METHODS
    )
    _require_safety_flags(data, context)

    rows = data.get("mapping_contracts")
    if not isinstance(rows, list):
        raise _mapping_error(context, "mapping_contracts must be a list")
    mapping_contracts = tuple(
        _parse_mapping_contract(row, context=f"{context}.mapping_contracts[{index}]")
        for index, row in enumerate(rows)
    )
    mapping_order = tuple(contract.mapping_key for contract in mapping_contracts)
    if mapping_order != EXPECTED_MAPPING_KEYS:
        raise _mapping_error(
            context, "mapping_contracts must be exactly: " + ", ".join(EXPECTED_MAPPING_KEYS)
        )

    next_recommended_lane = _require_string(data, "next_recommended_lane", context)
    if next_recommended_lane != NEXT_RECOMMENDED_LANE:
        raise _mapping_error(context, f"next_recommended_lane must be {NEXT_RECOMMENDED_LANE}")
    final_gate_decision = _require_string(data, "final_gate_decision", context)
    if final_gate_decision != FINAL_GATE_DECISION:
        raise _mapping_error(context, f"final_gate_decision must be {FINAL_GATE_DECISION}")

    return PreferenceRecipeMappingGovernance(
        schema_version=schema_version,
        generated_on=_parse_date(_require_string(data, "generated_on", context), context),
        coverage_ref=coverage_ref,
        recipe_dish_corpus_ref=recipe_dish_corpus_ref,
        pr11_landed_pr=pr11_landed_pr,
        pr14_landed_pr=pr14_landed_pr,
        source=source,
        source_classification=source_classification,
        source_family=source_family,
        evidence_policy=evidence_policy,
        blocked_methods=blocked_methods,
        mapping_contracts=mapping_contracts,
        next_recommended_lane=next_recommended_lane,
        final_gate_decision=final_gate_decision,
        notes=_require_safe_notes(_require_string(data, "notes", context), context),
    )


def load_preference_recipe_mapping_governance(
    governance_path: Path | str,
    *,
    coverage: SourceGapAudit,
    recipe_dish_corpus: RecipeDishCorpusGovernance,
    expected_coverage_ref: str | None = None,
    expected_recipe_dish_corpus_ref: str | None = None,
) -> PreferenceRecipeMappingGovernance:
    """Load and validate a PR15 preference recipe mapping contract JSON artifact."""

    path = Path(governance_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PreferenceRecipeMappingError(
            f"Cannot read preference recipe mapping governance {path}: {exc}"
        ) from exc
    return parse_preference_recipe_mapping_governance(
        payload,
        coverage=coverage,
        recipe_dish_corpus=recipe_dish_corpus,
        expected_coverage_ref=expected_coverage_ref,
        expected_recipe_dish_corpus_ref=expected_recipe_dish_corpus_ref,
        context=str(path),
    )


def build_preference_recipe_mapping_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    coverage_path: Path | str,
    recipe_dish_corpus_path: Path | str,
    governance_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the PR15 governance gate."""

    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    expected_coverage_ref = _relative_repo_path(coverage_path)
    expected_recipe_ref = _relative_repo_path(recipe_dish_corpus_path)
    report: dict[str, object] = {
        "success": False,
        "dry_run": True,
        "source": SOURCE,
        "source_classification": SOURCE_CLASSIFICATION,
        "source_family": SOURCE_FAMILY,
        "evidence_policy": EVIDENCE_POLICY,
        "blocked_methods": list(BLOCKED_METHODS),
        "mapping_keys": list(EXPECTED_MAPPING_KEYS),
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
        recipe_dish_corpus = load_recipe_dish_corpus_governance(
            recipe_dish_corpus_path,
            onboarding=onboarding,
            coverage=coverage,
        )
        governance = load_preference_recipe_mapping_governance(
            governance_path,
            coverage=coverage,
            recipe_dish_corpus=recipe_dish_corpus,
            expected_coverage_ref=expected_coverage_ref,
            expected_recipe_dish_corpus_ref=expected_recipe_ref,
        )
    except (
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
            "coverage_ref": governance.coverage_ref,
            "recipe_dish_corpus_ref": governance.recipe_dish_corpus_ref,
            "pr11_landed_pr": governance.pr11_landed_pr,
            "pr14_landed_pr": governance.pr14_landed_pr,
            "contract_status": {
                contract.mapping_key: contract.contract_status
                for contract in governance.mapping_contracts
            },
            "allowed_roles": {
                contract.mapping_key: contract.allowed_role
                for contract in governance.mapping_contracts
            },
        }
    )
    return report
