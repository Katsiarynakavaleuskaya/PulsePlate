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
from typing import Mapping, TypeVar

from core.food_sources.recipe_dish_corpus import (
    BLOCKED_METHODS as PR14_BLOCKED_METHODS,
    EVIDENCE_POLICY as PR14_EVIDENCE_POLICY,
    FINAL_GATE_DECISION as PR14_FINAL_GATE_DECISION,
    NEXT_RECOMMENDED_LANE as PR14_NEXT_RECOMMENDED_LANE,
    PER_CHAIN_LEGAL_REF as PR14_PER_CHAIN_LEGAL_REF,
    RecipeDishCorpusGovernance,
    RecipeDishCorpusGovernanceError,
    load_recipe_dish_corpus_governance,
)
from core.food_sources.source_catalog import SourceCatalogError, load_source_catalog
from core.food_sources.source_gap_audit import (
    FINAL_GATE_DECISION as PR11_FINAL_GATE_DECISION,
    NEXT_RECOMMENDED_LANE as PR11_NEXT_RECOMMENDED_LANE,
    REQUIRED_COVERAGE_DOMAINS as PR11_REQUIRED_COVERAGE_DOMAINS,
    SourceGapAudit,
    SourceGapAuditError,
    _EXPECTED_DOMAIN_DECISIONS as PR11_EXPECTED_DOMAIN_DECISIONS,
    _EXPECTED_SOURCE_GAP_DECISIONS as PR11_EXPECTED_SOURCE_GAP_DECISIONS,
    load_source_gap_audit,
)
from core.food_sources.source_onboarding import SourceOnboardingError, load_source_onboarding

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_RE = re.compile(r"^food-data-preference-recipe-mapping-contract\.v\d+$")
_PR11_SCHEMA_RE = re.compile(r"^food-data-coverage-source-gap-audit\.v\d+$")
_PR14_SCHEMA_RE = re.compile(r"^food-data-recipe-dish-corpus-governance\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EntryT = TypeVar("_EntryT")

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
EXPECTED_PR11_CATALOG_REF = "docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json"
EXPECTED_PR11_ONBOARDING_REF = "docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json"
EXPECTED_RECIPE_DISH_CORPUS_REF = (
    "docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json"
)
EXPECTED_PR14_RECIPE_ALLOWED_ROLES = {
    "edamam_food_database": "adjacent_recipe_food_db_review_only",
    "spoonacular": "deferred_recipe_experiment_candidate_only",
}
EXPECTED_PR14_RECIPE_REVIEW_CLASSIFICATION = "commercial_contract"
EXPECTED_PR14_RECIPE_REVIEW_FAMILY = "recipe_corpus"
EXPECTED_PR11_SOURCE_GAP_ORDER = (
    "usda_foundation",
    "usda_branded",
    "usda_fndds",
    "open_food_facts",
    "menustat",
    "chain_public_nutrition_pages",
    "edamam_food_database",
    "spoonacular",
    "nutritionix",
    "fatsecret_platform",
    "regional_catalogs",
    "jptn_food_facts",
)
EXPECTED_PR11_DOMAIN_SOURCE_REFS: dict[str, dict[str, tuple[str, ...]]] = {
    "generic_food_composition": {
        "primary_sources": ("usda_foundation",),
        "auxiliary_sources": ("usda_fndds",),
    },
    "branded_barcode_products": {
        "primary_sources": ("usda_branded",),
        "auxiliary_sources": ("open_food_facts",),
    },
    "restaurant_chain_menus": {
        "primary_sources": (),
        "auxiliary_sources": ("menustat",),
    },
    "recipe_dish_corpora": {
        "primary_sources": (),
        "auxiliary_sources": ("edamam_food_database", "spoonacular"),
    },
    "preference_menu_planning": {
        "primary_sources": (),
        "auxiliary_sources": (
            "chain_public_nutrition_pages",
            "edamam_food_database",
            "spoonacular",
        ),
    },
    "regional_local_products": {
        "primary_sources": (),
        "auxiliary_sources": ("regional_catalogs",),
    },
    "user_manual_evidence": {
        "primary_sources": (),
        "auxiliary_sources": ("chain_public_nutrition_pages",),
    },
}
EXPECTED_PR11_SOURCE_GAP_BLOCKING_REASONS: dict[str, tuple[str, ...]] = {
    "usda_foundation": (
        "Source-specific manifest, checksum, row, schema, and rollback gates still precede ingest.",
    ),
    "usda_branded": (
        "Source-specific manifest, checksum, row, schema, and rollback gates still precede ingest.",
    ),
    "usda_fndds": (
        "FNDDS must remain separated from Foundation and Branded until schema/PK review.",
    ),
    "open_food_facts": (
        "ODbL attribution and derivative-database obligations remain mandatory.",
        "OFF schema/PostgreSQL review is future work before refreshed snapshot authority.",
    ),
    "menustat": (
        "MenuStat does not provide active freshness coverage and requires validation before use.",
    ),
    "chain_public_nutrition_pages": (
        "Per-chain legal, anti-scraping, cache, attribution, schema, freshness, "
        "screenshot/evidence, and rollback review is missing.",
    ),
    "edamam_food_database": (
        "Contract, cache, attribution, redistribution, and rollback terms are not approved.",
    ),
    "spoonacular": (
        "Recipe/menu experiments are separate from database authority and need contract/cache review.",
    ),
    "nutritionix": (
        "Commercial contract, cache, attribution, redistribution, and rollback terms remain unapproved.",
    ),
    "fatsecret_platform": (
        "User decision: FatSecret Platform is not used as a PulsePlate project source.",
    ),
    "regional_catalogs": (
        "Locale-specific source identity, license, language, unit, schema, "
        "and redistribution terms are missing.",
    ),
    "jptn_food_facts": (
        "Provider identity, license, schema, retrieval, attribution, and redistribution "
        "evidence are unresolved.",
    ),
}

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
    "approved api",
    "api approved",
    "allowed api",
    "api allowed",
    "approved ingest",
    "allowed ingest",
    "approved runtime",
    "allowed runtime",
    "approved cache",
    "allowed cache",
    "approved redistribution",
    "allowed redistribution",
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
    "approve source use",
    "approves source use",
    "approved source use",
    "source use approved",
    "source use is approved",
    "source use allowed",
    "source use is allowed",
    "source use permitted",
    "source use is permitted",
    "source use granted",
    "source use is granted",
    "source use enabled",
    "source use is enabled",
    "api calls allowed",
    "api calls are allowed",
    "api calls approved",
    "api calls are approved",
    "api calls permitted",
    "api calls are permitted",
    "api calls granted",
    "api calls are granted",
    "api calls enabled",
    "api calls are enabled",
    "ingest approved",
    "ingest allowed",
    "ingest is allowed",
    "ingest permitted",
    "ingest is permitted",
    "ingest granted",
    "ingest is granted",
    "ingest enabled",
    "ingest is enabled",
    "runtime authority allowed",
    "runtime authority is allowed",
    "runtime authority permitted",
    "runtime authority is permitted",
    "runtime authority granted",
    "runtime authority is granted",
    "runtime authority enabled",
    "runtime authority is enabled",
    "runtime approved",
    "runtime permitted",
    "runtime granted",
    "runtime enabled",
    "cache authority allowed",
    "cache authority is allowed",
    "cache authority permitted",
    "cache authority is permitted",
    "cache authority granted",
    "cache authority is granted",
    "cache authority enabled",
    "cache authority is enabled",
    "db writes allowed",
    "db writes are allowed",
    "db writes permitted",
    "db writes are permitted",
    "db writes granted",
    "db writes are granted",
    "db writes enabled",
    "db writes are enabled",
    "database writes allowed",
    "database writes are allowed",
    "database writes permitted",
    "database writes are permitted",
    "database writes granted",
    "database writes are granted",
    "database writes enabled",
    "database writes are enabled",
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
    "downloads permitted",
    "download permitted",
    "source downloads permitted",
    "source download permitted",
    "downloads granted",
    "download granted",
    "source downloads granted",
    "source download granted",
    "downloads enabled",
    "download enabled",
    "source downloads enabled",
    "source download enabled",
    "scraping allowed",
    "scraping is allowed",
    "scraping permitted",
    "scraping is permitted",
    "scraping granted",
    "scraping is granted",
    "scraping enabled",
    "scraping is enabled",
    "redistribution allowed",
    "redistribution is allowed",
    "redistribution permitted",
    "redistribution is permitted",
    "redistribution granted",
    "redistribution is granted",
    "redistribution enabled",
    "redistribution is enabled",
    "public dataset claim allowed",
    "public dataset claim is allowed",
    "public dataset claim permitted",
    "public dataset claim is permitted",
    "public dataset claim granted",
    "public dataset claim is granted",
    "public dataset claim enabled",
    "public dataset claim is enabled",
    "automation allowed",
    "automation is allowed",
    "automation permitted",
    "automation is permitted",
    "automation granted",
    "automation is granted",
    "automation enabled",
    "automation is enabled",
    "product display allowed",
    "product display is allowed",
    "product display permitted",
    "product display is permitted",
    "product display granted",
    "product display is granted",
    "product display enabled",
    "product display is enabled",
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
                f"approve {variant}",
                f"approves {variant}",
                f"allow {variant}",
                f"allows {variant}",
                f"authorize {variant}",
                f"authorizes {variant}",
                f"{variant} approved",
                f"{variant} is approved",
                f"approved {variant}",
                f"approved for {variant}",
                f"{variant} allowed",
                f"{variant} is allowed",
                f"allowed {variant}",
                f"allowed for {variant}",
                f"{variant} authorized",
                f"{variant} is authorized",
                f"authorized {variant}",
                f"authorized for {variant}",
                f"{variant} permitted",
                f"{variant} is permitted",
                f"permitted {variant}",
                f"permitted for {variant}",
                f"{variant} granted",
                f"{variant} is granted",
                f"granted {variant}",
                f"granted for {variant}",
                f"{variant} enabled",
                f"{variant} is enabled",
                f"enabled {variant}",
                f"enabled for {variant}",
            ):
                if phrase not in seen:
                    seen.add(phrase)
                    phrases.append(phrase)
    return tuple(phrases)


_FORBIDDEN_NOTE_PHRASES = _EXTRA_FORBIDDEN_NOTE_PHRASES + _blocked_method_note_phrases()
_FORBIDDEN_NOTE_PATTERNS = tuple(
    (phrase, re.compile(rf"\b{re.escape(phrase)}\b")) for phrase in _FORBIDDEN_NOTE_PHRASES
)
_NEGATED_APPROVAL_PREFIXES = ("not ", "never ", "no ", "do not ", "does not ")
_NEGATION_BOUNDARY_TERMS = (
    " but ",
    " however ",
    " yet ",
    " although ",
    " though ",
    " even though ",
    " whereas ",
    " while ",
    " despite ",
    " unless ",
    " even if ",
    " except ",
    " notwithstanding ",
)
_NOTE_APPROVAL_TERMS = (
    "approve",
    "approves",
    "approved",
    "allow",
    "allows",
    "allowed",
    "permit",
    "permits",
    "permitted",
    "grant",
    "grants",
    "granted",
    "enable",
    "enables",
    "enabled",
    "authorize",
    "authorizes",
    "authorized",
)
_NOTE_NEGATION_WORDS = frozenset({"no", "not", "never"})
_FORBIDDEN_NOTE_SUBJECTS = tuple(
    sorted(
        {
            "api",
            "api calls",
            "automation",
            "cache authority",
            "database writes",
            "db writes",
            "download",
            "downloads",
            "ingest",
            "llm output",
            "paid api use",
            "paid plan",
            "paid plans",
            "paid source use",
            "product display",
            "public dataset claim",
            "public menu page",
            "public menu pages",
            "redistribution",
            "recipe text",
            "runtime",
            "runtime authority",
            "scraping",
            "chain evidence",
            "edamam",
            "spoonacular",
            "source download",
            "source downloads",
            "source use",
            "user preference text",
            "preference text",
            *(method.replace("_", " ") for method in BLOCKED_METHODS),
        },
        key=len,
        reverse=True,
    )
)
_NOTE_APPROVAL_PATTERN = "|".join(re.escape(term) for term in _NOTE_APPROVAL_TERMS)
_SUBJECT_THEN_APPROVAL_PATTERNS = tuple(
    (
        subject,
        re.compile(
            rf"\b{re.escape(subject)}\b(?P<middle>(?:\s+\w+){{0,3}})"
            rf"\s+(?P<approval>{_NOTE_APPROVAL_PATTERN})\b"
        ),
    )
    for subject in _FORBIDDEN_NOTE_SUBJECTS
)
_APPROVAL_THEN_SUBJECT_PATTERNS = tuple(
    (
        subject,
        re.compile(
            rf"\b(?P<approval>{_NOTE_APPROVAL_PATTERN})\b"
            rf"(?P<middle>(?:\s+\w+){{0,3}})\s+\b{re.escape(subject)}\b"
        ),
    )
    for subject in _FORBIDDEN_NOTE_SUBJECTS
)

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
    normalized = " ".join(
        value.lower()
        .replace("-", " ")
        .replace("_", " ")
        .replace(":", " ")
        .replace(",", " ")
        .replace(";", " ")
        .replace("/", " ")
        .replace("\\", " ")
        .replace("[", " ")
        .replace("]", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace("{", " ")
        .replace("}", " ")
        .split()
    )
    for phrase, pattern in _FORBIDDEN_NOTE_PATTERNS:
        for match in pattern.finditer(normalized):
            if _is_negated_approval_phrase(normalized, phrase, match.start()):
                continue
            raise _mapping_error(
                context,
                "notes must not approve recipe text, preference text, LLM output, "
                "source use, ingest, runtime, cache, DB writes, display, or nutrition authority",
            )
    _require_no_bounded_approval_windows(normalized, context)
    return value


def _is_negated_approval_phrase(normalized: str, phrase: str, start: int) -> bool:
    guarded_terms = (
        "approve",
        "approves",
        "approved",
        "allow",
        "allows",
        "allowed",
        "authorize",
        "authorizes",
        "authorized",
        "permit",
        "permits",
        "permitted",
        "grant",
        "grants",
        "granted",
        "enable",
        "enables",
        "enabled",
    )
    if not any(term in phrase for term in guarded_terms):
        return False
    prefix_tail = normalized[max(0, start - 72) : start]
    segment_start = max(prefix_tail.rfind(separator) for separator in (".", ";", ":", "?", "!"))
    if segment_start >= 0:
        prefix_tail = prefix_tail[segment_start + 1 :]
    stripped_prefix = prefix_tail.strip()
    bounded_prefix = stripped_prefix
    padded_prefix = f" {stripped_prefix} "
    boundary_end = max(
        (
            padded_prefix.rfind(boundary) + len(boundary)
            for boundary in _NEGATION_BOUNDARY_TERMS
            if boundary in padded_prefix
        ),
        default=0,
    )
    if boundary_end:
        bounded_prefix = padded_prefix[boundary_end:-1].strip()
    no_index = bounded_prefix.rfind(" no ")
    if bounded_prefix.startswith("no "):
        no_index = 0
    if no_index >= 0:
        negated_span = bounded_prefix[no_index:].strip()
        words = negated_span.split()
        if len(words) <= 8 and len(words) > 1 and words[1] != "only" and "or" in words:
            return True
    return any(
        bounded_prefix.endswith(negation.strip()) for negation in _NEGATED_APPROVAL_PREFIXES
    ) or (
        bounded_prefix.startswith("no ")
        and (" or " in bounded_prefix or bounded_prefix.endswith(" or"))
    )


def _require_no_bounded_approval_windows(normalized: str, context: str) -> None:
    for _subject, pattern in _SUBJECT_THEN_APPROVAL_PATTERNS:
        for match in pattern.finditer(normalized):
            middle_words = frozenset(match.group("middle").split())
            if middle_words & _NOTE_NEGATION_WORDS:
                continue
            if _is_negated_approval_phrase(normalized, match.group("approval"), match.start()):
                continue
            raise _mapping_error(
                context,
                "notes must not approve recipe text, preference text, LLM output, "
                "source use, ingest, runtime, cache, DB writes, display, or nutrition authority",
            )
    for _subject, pattern in _APPROVAL_THEN_SUBJECT_PATTERNS:
        for match in pattern.finditer(normalized):
            middle_words = frozenset(match.group("middle").split())
            if middle_words & _NOTE_NEGATION_WORDS:
                continue
            if _is_negated_approval_phrase(normalized, match.group("approval"), match.start()):
                continue
            raise _mapping_error(
                context,
                "notes must not approve recipe text, preference text, LLM output, "
                "source use, ingest, runtime, cache, DB writes, display, or nutrition authority",
            )


def _coverage_domain_by_name(coverage: SourceGapAudit, context: str) -> dict[str, object]:
    domain_order = tuple(entry.domain for entry in coverage.coverage_domains)
    if domain_order != PR11_REQUIRED_COVERAGE_DOMAINS:
        raise _mapping_error(
            context,
            "PR11 coverage_domains must be exactly: " + ", ".join(PR11_REQUIRED_COVERAGE_DOMAINS),
        )
    return {entry.domain: entry for entry in coverage.coverage_domains}


def _require_existing_entry(
    entries: Mapping[str, _EntryT],
    key: str,
    context: str,
    label: str,
) -> _EntryT:
    try:
        return entries[key]
    except KeyError as exc:
        raise _mapping_error(context, f"PR11 {label} is missing {key}") from exc


def _require_pr14_handoff(
    recipe_dish_corpus: RecipeDishCorpusGovernance,
    context: str,
) -> None:
    if recipe_dish_corpus.source != "recipe_dish_corpora":
        raise _mapping_error(context, "PR14 source must be recipe_dish_corpora")
    if recipe_dish_corpus.source_classification != "commercial_contract_review_only":
        raise _mapping_error(
            context, "PR14 source_classification must be commercial_contract_review_only"
        )
    if recipe_dish_corpus.source_family != "recipe_corpus":
        raise _mapping_error(context, "PR14 source_family must be recipe_corpus")
    if not _PR14_SCHEMA_RE.fullmatch(recipe_dish_corpus.schema_version):
        raise _mapping_error(
            context,
            "PR14 schema_version must look like food-data-recipe-dish-corpus-governance.vN",
        )
    if recipe_dish_corpus.per_chain_legal_ref != PR14_PER_CHAIN_LEGAL_REF:
        raise _mapping_error(
            context,
            f"PR14 per_chain_legal_ref must be {PR14_PER_CHAIN_LEGAL_REF!r}",
        )
    if recipe_dish_corpus.pr13_landed_pr != 1613:
        raise _mapping_error(context, "PR14 pr13_landed_pr must be 1613")
    if recipe_dish_corpus.next_recommended_lane != PR14_NEXT_RECOMMENDED_LANE:
        raise _mapping_error(context, "PR14 must recommend preference_recipe_mapping_contract")
    if recipe_dish_corpus.evidence_policy != PR14_EVIDENCE_POLICY:
        raise _mapping_error(context, f"PR14 evidence_policy must be {PR14_EVIDENCE_POLICY}")
    if recipe_dish_corpus.blocked_methods != PR14_BLOCKED_METHODS:
        raise _mapping_error(
            context,
            "PR14 blocked_methods must be exactly: " + ", ".join(PR14_BLOCKED_METHODS),
        )
    if recipe_dish_corpus.final_gate_decision != PR14_FINAL_GATE_DECISION:
        raise _mapping_error(
            context, f"PR14 final_gate_decision must be {PR14_FINAL_GATE_DECISION}"
        )
    _require_safe_notes(recipe_dish_corpus.notes, f"{context}.PR14.notes")
    review_sources = tuple(review.source for review in recipe_dish_corpus.recipe_corpus_reviews)
    if review_sources != tuple(EXPECTED_PR14_RECIPE_ALLOWED_ROLES):
        raise _mapping_error(context, "PR14 recipe_corpus_reviews sources are not allowed")
    for review in recipe_dish_corpus.recipe_corpus_reviews:
        source = review.source
        if review.source_classification != EXPECTED_PR14_RECIPE_REVIEW_CLASSIFICATION:
            raise _mapping_error(
                context,
                f"PR14 {source} source_classification must be "
                f"{EXPECTED_PR14_RECIPE_REVIEW_CLASSIFICATION}",
            )
        if review.source_family != EXPECTED_PR14_RECIPE_REVIEW_FAMILY:
            raise _mapping_error(
                context,
                f"PR14 {source} source_family must be {EXPECTED_PR14_RECIPE_REVIEW_FAMILY}",
            )
        if review.legal_review_status != "required_not_approved":
            raise _mapping_error(
                context, f"PR14 {source} legal_review_status must be required_not_approved"
            )
        if review.contract_review_status != "required_not_approved":
            raise _mapping_error(
                context, f"PR14 {source} contract_review_status must be required_not_approved"
            )
        if review.cache_decision != "blocked_contract_required":
            raise _mapping_error(
                context, f"PR14 {source} cache_decision must be blocked_contract_required"
            )
        if review.display_decision != "blocked_contract_required":
            raise _mapping_error(
                context, f"PR14 {source} display_decision must be blocked_contract_required"
            )
        if review.attribution_decision != "required_not_approved":
            raise _mapping_error(
                context, f"PR14 {source} attribution_decision must be required_not_approved"
            )
        if review.redistribution_decision != "contract_required":
            raise _mapping_error(
                context, f"PR14 {source} redistribution_decision must be contract_required"
            )
        if review.freshness_review_status != "required_not_approved":
            raise _mapping_error(
                context, f"PR14 {source} freshness_review_status must be required_not_approved"
            )
        if review.schema_review_status != "required_not_approved":
            raise _mapping_error(
                context, f"PR14 {source} schema_review_status must be required_not_approved"
            )
        if (
            review.rollback_requirement
            != "required_before_any_future_source_use_ingest_or_runtime_lane"
        ):
            raise _mapping_error(context, f"PR14 {source} rollback_requirement is not allowed")
        if review.allowed_role != EXPECTED_PR14_RECIPE_ALLOWED_ROLES[source]:
            raise _mapping_error(context, f"PR14 {source} allowed_role is not allowed")
        _require_safe_notes(review.notes, f"{context}.PR14.{source}.notes")


def _require_pr11_preference_handoff(coverage: SourceGapAudit, context: str) -> None:
    if not _PR11_SCHEMA_RE.fullmatch(coverage.schema_version):
        raise _mapping_error(
            context,
            "PR11 schema_version must look like food-data-coverage-source-gap-audit.vN",
        )
    if coverage.catalog_ref != EXPECTED_PR11_CATALOG_REF:
        raise _mapping_error(
            context,
            f"PR11 catalog_ref must be {EXPECTED_PR11_CATALOG_REF!r}",
        )
    if coverage.onboarding_ref != EXPECTED_PR11_ONBOARDING_REF:
        raise _mapping_error(
            context,
            f"PR11 onboarding_ref must be {EXPECTED_PR11_ONBOARDING_REF!r}",
        )
    if coverage.pr10_landed_pr != 1597:
        raise _mapping_error(context, "PR11 pr10_landed_pr must be 1597")
    if coverage.next_recommended_lane != PR11_NEXT_RECOMMENDED_LANE:
        raise _mapping_error(
            context,
            f"PR11 next_recommended_lane must be {PR11_NEXT_RECOMMENDED_LANE}",
        )
    if coverage.final_gate_decision != PR11_FINAL_GATE_DECISION:
        raise _mapping_error(
            context,
            f"PR11 final_gate_decision must be {PR11_FINAL_GATE_DECISION}",
        )
    _require_safe_notes(coverage.notes, f"{context}.PR11.notes")
    domains = _coverage_domain_by_name(coverage, context)
    preference_domain = _require_existing_entry(domains, SOURCE, context, "coverage_domains")
    for domain in coverage.coverage_domains:
        expected = PR11_EXPECTED_DOMAIN_DECISIONS[domain.domain]
        for field_name, expected_value in expected.items():
            if getattr(domain, field_name) != expected_value:
                raise _mapping_error(
                    context,
                    f"PR11 {domain.domain} coverage_domains {field_name} must be "
                    f"{expected_value}",
                )
        expected_refs = EXPECTED_PR11_DOMAIN_SOURCE_REFS[domain.domain]
        for field_name, expected_value in expected_refs.items():
            if getattr(domain, field_name) != expected_value:
                raise _mapping_error(
                    context,
                    f"PR11 {domain.domain} coverage_domains {field_name} must be "
                    f"{', '.join(expected_value) if expected_value else 'empty'}",
                )
        if domain.approved_ingest or domain.approved_runtime_authority:
            raise _mapping_error(
                context,
                f"PR11 {domain.domain} coverage_domains must not approve ingest/runtime authority",
            )
        _require_safe_notes(domain.notes, f"{context}.PR11.{domain.domain}.notes")
    _require_safe_notes(
        getattr(preference_domain, "notes"),
        f"{context}.PR11.preference_menu_planning.notes",
    )
    source_gap_order = tuple(entry.source for entry in coverage.source_gap_decisions)
    if len(source_gap_order) != len(set(source_gap_order)):
        raise _mapping_error(context, "PR11 source_gap_decisions must not contain duplicates")
    if source_gap_order != EXPECTED_PR11_SOURCE_GAP_ORDER:
        raise _mapping_error(
            context,
            "PR11 source_gap_decisions must be exactly: "
            + ", ".join(EXPECTED_PR11_SOURCE_GAP_ORDER),
        )
    for source_gap in coverage.source_gap_decisions:
        if (
            source_gap.approved_ingest
            or source_gap.approved_runtime_authority
            or source_gap.api_calls_allowed
            or source_gap.scraping_allowed
            or source_gap.paid_source_use_allowed
        ):
            raise _mapping_error(
                context,
                f"PR11 {source_gap.source} source_gap_decisions must not approve ingest, "
                "runtime, API, scraping, or paid source use",
            )
    source_gap_decisions = {entry.source: entry for entry in coverage.source_gap_decisions}
    for source, expected in PR11_EXPECTED_SOURCE_GAP_DECISIONS.items():
        source_gap = _require_existing_entry(
            source_gap_decisions,
            source,
            context,
            "source_gap_decisions",
        )
        for field_name, expected_value in expected.items():
            if getattr(source_gap, field_name) != expected_value:
                raise _mapping_error(
                    context,
                    f"PR11 {source} source_gap_decisions {field_name} must be {expected_value}",
                )
        expected_blocking_reasons = EXPECTED_PR11_SOURCE_GAP_BLOCKING_REASONS[source]
        if source_gap.blocking_reasons != expected_blocking_reasons:
            raise _mapping_error(
                context,
                f"PR11 {source} source_gap_decisions blocking_reasons must preserve PR11 evidence",
            )
        _require_safe_notes(source_gap.notes, f"{context}.PR11.{source}.notes")


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
