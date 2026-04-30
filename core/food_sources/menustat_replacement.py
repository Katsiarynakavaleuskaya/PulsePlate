"""
Deterministic MenuStat replacement-source decision gate.

RU: Файловая проверка решения по замене MenuStat до restaurant-menu ingest.
EN: File-only MenuStat replacement decision gate before restaurant-menu ingest.
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
from core.food_sources.source_onboarding import (
    SourceOnboarding,
    SourceOnboardingEntry,
    SourceOnboardingError,
    load_source_onboarding,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DECISION_SCHEMA_RE = re.compile(r"^food-data-menustat-replacement\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SAFETY_FLAG_TEMPLATE: dict[str, bool] = {
    "runtime_cutover": False,
    "digitalocean_postgres_load": False,
    "bulk_ingest": False,
    "file_only": True,
    "network_allowed": False,
    "db_writes_allowed": False,
}
_DECISION_KEYS = frozenset(
    {
        "schema_version",
        "generated_on",
        "legacy_source",
        "catalog_ref",
        "onboarding_ref",
        "runtime_cutover",
        "digitalocean_postgres_load",
        "bulk_ingest",
        "file_only",
        "network_allowed",
        "db_writes_allowed",
        "final_gate_decision",
        "candidate_sources",
        "notes",
    }
)
_CANDIDATE_KEYS = frozenset(
    {
        "source",
        "replacement_for",
        "source_classification",
        "source_family",
        "onboarding_status",
        "candidate_gate_decision",
        "authority_decision",
        "evidence_status",
        "contract_status",
        "cache_policy_status",
        "display_policy_status",
        "redistribution_policy_status",
        "freshness_status",
        "source_evidence_refs",
        "blocking_reasons",
        "notes",
    }
)
_EXPECTED_CANDIDATES = (
    "nutritionix",
    "fatsecret_platform",
    "spoonacular",
    "chain_public_nutrition_pages",
)
_EXPECTED_CANDIDATE_POLICY: dict[str, dict[str, object]] = {
    "nutritionix": {
        "source_classification": "commercial_contract",
        "source_family": "restaurant_menu",
        "onboarding_status": "contract_review_blocked",
        "candidate_gate_decision": "blocked_contract_review_required",
        "authority_decision": "not_approved",
    },
    "fatsecret_platform": {
        "source_classification": "commercial_contract",
        "source_family": "commercial_api",
        "onboarding_status": "contract_review_blocked",
        "candidate_gate_decision": "blocked_contract_review_required",
        "authority_decision": "not_approved",
    },
    "spoonacular": {
        "source_classification": "commercial_contract",
        "source_family": "recipe_corpus",
        "onboarding_status": "contract_review_blocked",
        "candidate_gate_decision": "blocked_contract_review_required",
        "authority_decision": "not_approved",
    },
    "chain_public_nutrition_pages": {
        "source_classification": "unresolved",
        "source_family": "restaurant_menu",
        "onboarding_status": "unresolved_blocked",
        "candidate_gate_decision": "blocked_unresolved_review_required",
        "authority_decision": "not_approved",
    },
}
_BLOCKED_STATUS_FIELDS = (
    "evidence_status",
    "contract_status",
    "cache_policy_status",
    "display_policy_status",
    "redistribution_policy_status",
    "freshness_status",
)

MENUSTAT_SOURCE = "menustat"
BLOCKED_GATE_DECISION = "blocked_until_replacement_approved"


class MenuStatReplacementError(ValueError):
    """Raised when the MenuStat replacement decision gate is invalid."""


@dataclass(frozen=True)
class MenuStatReplacementCandidate:
    """One blocked replacement-source candidate decision."""

    source: str
    replacement_for: str
    source_classification: str
    source_family: str
    onboarding_status: str
    candidate_gate_decision: str
    authority_decision: str
    evidence_status: str
    contract_status: str
    cache_policy_status: str
    display_policy_status: str
    redistribution_policy_status: str
    freshness_status: str
    source_evidence_refs: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class MenuStatReplacementDecision:
    """Validated MenuStat replacement-source decision artifact."""

    schema_version: str
    generated_on: date
    legacy_source: str
    catalog_ref: str
    onboarding_ref: str
    runtime_cutover: bool
    digitalocean_postgres_load: bool
    bulk_ingest: bool
    file_only: bool
    network_allowed: bool
    db_writes_allowed: bool
    final_gate_decision: str
    candidate_sources: tuple[MenuStatReplacementCandidate, ...]
    notes: str


def _replacement_error(context: str, detail: str) -> MenuStatReplacementError:
    """Build a stable validation error for the current decision artifact."""
    return MenuStatReplacementError(f"Invalid MenuStat replacement gate {context}: {detail}")


def _require_mapping(value: object, context: str) -> dict[str, object]:
    """Return an object mapping or fail closed on malformed JSON payloads."""
    if not isinstance(value, dict):
        raise _replacement_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _replacement_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    """Read a required non-empty string field from a validated object."""
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _replacement_error(context, f"missing non-empty string '{key}'")
    return value.strip()


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    """Read a required boolean field without truthy/falsy coercion."""
    value = data.get(key)
    if not isinstance(value, bool):
        raise _replacement_error(context, f"'{key}' must be a boolean")
    return value


def _require_string_tuple(
    data: dict[str, object],
    key: str,
    context: str,
) -> tuple[str, ...]:
    """Read a required non-empty string list and reject duplicate values."""
    value = data.get(key)
    if not isinstance(value, list):
        raise _replacement_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _replacement_error(context, f"'{key}[{index}]' must be a non-empty string")
        normalized = item.strip()
        if normalized in seen:
            raise _replacement_error(context, f"'{key}' contains duplicate value {normalized!r}")
        seen.add(normalized)
        items.append(normalized)
    if not items:
        raise _replacement_error(context, f"'{key}' must not be empty")
    return tuple(items)


def _require_url_tuple(
    data: dict[str, object],
    key: str,
    context: str,
) -> tuple[str, ...]:
    """Read a required non-empty URL list and reject malformed references."""
    urls = _require_string_tuple(data, key, context)
    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise _replacement_error(context, f"'{key}' must contain absolute http(s) URLs")
    return urls


def _parse_date(value: str, context: str) -> date:
    """Parse the canonical YYYY-MM-DD artifact date format."""
    if not _DATE_RE.fullmatch(value):
        raise _replacement_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _replacement_error(context, "generated_on must use YYYY-MM-DD") from exc


def _require_safety_flags(data: dict[str, object], context: str) -> dict[str, bool]:
    """Extract all safety flags before comparing them with the gate template."""
    return {key: _require_bool(data, key, context) for key in _SAFETY_FLAG_TEMPLATE}


def _relative_repo_path(path: Path | str) -> str:
    """Normalize a path to the repo-relative form used by canonical artifacts."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _entry_by_source(entries: tuple[object, ...]) -> dict[str, object]:
    """Index catalog or onboarding entries by their source field."""
    return {getattr(entry, "source"): entry for entry in entries}


def _menustat_catalog_entry(catalog: SourceCatalog, context: str) -> SourceCatalogEntry:
    """Find and validate the legacy MenuStat catalog entry."""
    entry = _entry_by_source(catalog.sources).get(MENUSTAT_SOURCE)
    if not isinstance(entry, SourceCatalogEntry):
        raise _replacement_error(context, "catalog must include menustat")
    if entry.source_classification != "legacy_static":
        raise _replacement_error(
            context, "menustat must remain source_classification=legacy_static"
        )
    if entry.status != "legacy_baseline":
        raise _replacement_error(context, "menustat must remain legacy_baseline")
    if entry.active_update_source:
        raise _replacement_error(context, "menustat cannot be an active update source")
    if not entry.replacement_required:
        raise _replacement_error(context, "menustat must remain replacement_required")
    return entry


def _menustat_onboarding_entry(
    onboarding: SourceOnboarding,
    context: str,
) -> SourceOnboardingEntry:
    """Find and validate the legacy MenuStat onboarding entry."""
    entry = _entry_by_source(onboarding.sources).get(MENUSTAT_SOURCE)
    if not isinstance(entry, SourceOnboardingEntry):
        raise _replacement_error(context, "onboarding must include menustat")
    if entry.onboarding_status != "legacy_baseline_blocked":
        raise _replacement_error(context, "menustat onboarding must remain legacy_baseline_blocked")
    if entry.ingestion_path != "legacy_snapshot_review_only":
        raise _replacement_error(
            context, "menustat ingestion path must stay legacy_snapshot_review_only"
        )
    return entry


def _parse_candidate(value: object, context: str) -> MenuStatReplacementCandidate:
    """Parse one replacement candidate row from the decision artifact."""
    data = _require_mapping(value, context)
    unexpected_keys = sorted(set(data) - _CANDIDATE_KEYS)
    if unexpected_keys:
        joined = ", ".join(unexpected_keys)
        raise _replacement_error(context, f"unexpected candidate keys: {joined}")
    candidate = MenuStatReplacementCandidate(
        source=_require_string(data, "source", context),
        replacement_for=_require_string(data, "replacement_for", context),
        source_classification=_require_string(data, "source_classification", context),
        source_family=_require_string(data, "source_family", context),
        onboarding_status=_require_string(data, "onboarding_status", context),
        candidate_gate_decision=_require_string(data, "candidate_gate_decision", context),
        authority_decision=_require_string(data, "authority_decision", context),
        evidence_status=_require_string(data, "evidence_status", context),
        contract_status=_require_string(data, "contract_status", context),
        cache_policy_status=_require_string(data, "cache_policy_status", context),
        display_policy_status=_require_string(data, "display_policy_status", context),
        redistribution_policy_status=_require_string(data, "redistribution_policy_status", context),
        freshness_status=_require_string(data, "freshness_status", context),
        source_evidence_refs=_require_url_tuple(data, "source_evidence_refs", context),
        blocking_reasons=_require_string_tuple(data, "blocking_reasons", context),
        notes=_require_string(data, "notes", context),
    )
    if candidate.replacement_for != MENUSTAT_SOURCE:
        raise _replacement_error(context, f"{candidate.source} must replace menustat")
    if candidate.source not in _EXPECTED_CANDIDATES:
        raise _replacement_error(
            context, f"unknown MenuStat replacement candidate: {candidate.source}"
        )
    if candidate.authority_decision in {"active_authority", "approved_ingest"}:
        raise _replacement_error(context, f"{candidate.source} cannot be approved in PR9")
    if candidate.candidate_gate_decision == "approved_ingest":
        raise _replacement_error(context, f"{candidate.source} cannot be approved in PR9")
    if candidate.candidate_gate_decision == "eligible_preflight":
        raise _replacement_error(context, f"{candidate.source} cannot become eligible in PR9")
    for field_name in _BLOCKED_STATUS_FIELDS:
        if not getattr(candidate, field_name).startswith("blocked_"):
            raise _replacement_error(
                context,
                f"{candidate.source} {field_name} must remain blocked",
            )
    return candidate


def _validate_candidate_contract(
    candidate: MenuStatReplacementCandidate,
    catalog_entries: dict[str, object],
    onboarding_entries: dict[str, object],
    context: str,
) -> None:
    """Cross-check a decision row against PR3 catalog and PR5 onboarding."""
    catalog_entry = catalog_entries.get(candidate.source)
    if not isinstance(catalog_entry, SourceCatalogEntry):
        raise _replacement_error(context, f"catalog missing candidate {candidate.source}")
    onboarding_entry = onboarding_entries.get(candidate.source)
    if not isinstance(onboarding_entry, SourceOnboardingEntry):
        raise _replacement_error(context, f"onboarding missing candidate {candidate.source}")
    expected = _EXPECTED_CANDIDATE_POLICY[candidate.source]
    actual: dict[str, object] = {
        "source_classification": candidate.source_classification,
        "source_family": candidate.source_family,
        "onboarding_status": candidate.onboarding_status,
        "candidate_gate_decision": candidate.candidate_gate_decision,
        "authority_decision": candidate.authority_decision,
    }
    mismatches = [key for key, value in expected.items() if actual[key] != value]
    if mismatches:
        joined = ", ".join(mismatches)
        raise _replacement_error(context, f"{candidate.source} policy mismatch: {joined}")
    if catalog_entry.replacement_for != MENUSTAT_SOURCE:
        raise _replacement_error(
            context, f"{candidate.source} must be cataloged as replacing menustat"
        )
    if catalog_entry.source_classification != candidate.source_classification:
        raise _replacement_error(context, f"{candidate.source} classification differs from catalog")
    if catalog_entry.source_family != candidate.source_family:
        raise _replacement_error(context, f"{candidate.source} family differs from catalog")
    if onboarding_entry.onboarding_status != candidate.onboarding_status:
        raise _replacement_error(context, f"{candidate.source} onboarding status differs from PR5")
    if onboarding_entry.onboarding_status == "eligible_preflight":
        raise _replacement_error(
            context, f"{candidate.source} must not be eligible_preflight in PR9"
        )


def parse_menustat_replacement_decision(
    payload: object,
    *,
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    expected_catalog_ref: str | None = None,
    expected_onboarding_ref: str | None = None,
    context: str = "<menustat-replacement>",
) -> MenuStatReplacementDecision:
    """Parse and validate the MenuStat replacement-source decision gate."""
    data = _require_mapping(payload, context)
    unexpected_keys = sorted(set(data) - _DECISION_KEYS)
    if unexpected_keys:
        joined = ", ".join(unexpected_keys)
        raise _replacement_error(context, f"unexpected keys: {joined}")

    schema_version = _require_string(data, "schema_version", context)
    if not _DECISION_SCHEMA_RE.fullmatch(schema_version):
        raise _replacement_error(
            context,
            "schema_version must look like food-data-menustat-replacement.vN",
        )
    legacy_source = _require_string(data, "legacy_source", context)
    if legacy_source != MENUSTAT_SOURCE:
        raise _replacement_error(context, "legacy_source must be menustat")

    catalog_ref = _require_string(data, "catalog_ref", context)
    if expected_catalog_ref is not None and catalog_ref != expected_catalog_ref:
        raise _replacement_error(context, f"catalog_ref must be {expected_catalog_ref!r}")
    onboarding_ref = _require_string(data, "onboarding_ref", context)
    if expected_onboarding_ref is not None and onboarding_ref != expected_onboarding_ref:
        raise _replacement_error(context, f"onboarding_ref must be {expected_onboarding_ref!r}")

    safety_flags = _require_safety_flags(data, context)
    if safety_flags != _SAFETY_FLAG_TEMPLATE:
        raise _replacement_error(
            context,
            "runtime_cutover, digitalocean_postgres_load, bulk_ingest, "
            "network_allowed, and db_writes_allowed must be false; file_only must be true",
        )

    candidate_rows = data.get("candidate_sources")
    if not isinstance(candidate_rows, list):
        raise _replacement_error(context, "candidate_sources must be a list")
    candidates = tuple(
        _parse_candidate(candidate, f"{context}.candidate_sources[{index}]")
        for index, candidate in enumerate(candidate_rows)
    )
    candidate_names = tuple(candidate.source for candidate in candidates)
    if candidate_names != _EXPECTED_CANDIDATES:
        expected = ", ".join(_EXPECTED_CANDIDATES)
        actual = ", ".join(candidate_names)
        raise _replacement_error(
            context, f"candidate_sources must be exactly: {expected}; got: {actual}"
        )

    final_gate_decision = _require_string(data, "final_gate_decision", context)
    if final_gate_decision != BLOCKED_GATE_DECISION:
        raise _replacement_error(context, f"final_gate_decision must be {BLOCKED_GATE_DECISION}")

    _menustat_catalog_entry(catalog, context)
    _menustat_onboarding_entry(onboarding, context)
    catalog_entries = _entry_by_source(catalog.sources)
    onboarding_entries = _entry_by_source(onboarding.sources)
    for candidate in candidates:
        _validate_candidate_contract(candidate, catalog_entries, onboarding_entries, context)

    return MenuStatReplacementDecision(
        schema_version=schema_version,
        generated_on=_parse_date(_require_string(data, "generated_on", context), context),
        legacy_source=legacy_source,
        catalog_ref=catalog_ref,
        onboarding_ref=onboarding_ref,
        runtime_cutover=safety_flags["runtime_cutover"],
        digitalocean_postgres_load=safety_flags["digitalocean_postgres_load"],
        bulk_ingest=safety_flags["bulk_ingest"],
        file_only=safety_flags["file_only"],
        network_allowed=safety_flags["network_allowed"],
        db_writes_allowed=safety_flags["db_writes_allowed"],
        final_gate_decision=final_gate_decision,
        candidate_sources=candidates,
        notes=_require_string(data, "notes", context),
    )


def load_menustat_replacement_decision(
    decision_path: Path | str,
    *,
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    expected_catalog_ref: str | None = None,
    expected_onboarding_ref: str | None = None,
) -> MenuStatReplacementDecision:
    """Load and validate a MenuStat replacement decision JSON artifact."""
    path = Path(decision_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MenuStatReplacementError(
            f"Cannot read MenuStat replacement gate {path}: {exc}"
        ) from exc
    return parse_menustat_replacement_decision(
        payload,
        catalog=catalog,
        onboarding=onboarding,
        expected_catalog_ref=expected_catalog_ref,
        expected_onboarding_ref=expected_onboarding_ref,
        context=str(path),
    )


def build_menustat_replacement_report(
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
    decision_path: Path | str,
) -> dict[str, object]:
    """Build a deterministic JSON report for the MenuStat replacement gate."""
    expected_catalog_ref = _relative_repo_path(catalog_path)
    expected_onboarding_ref = _relative_repo_path(onboarding_path)
    report: dict[str, object] = {
        "success": False,
        "dry_run": True,
        "legacy_source": MENUSTAT_SOURCE,
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "file_only": True,
        "network_allowed": False,
        "db_writes_allowed": False,
        "final_gate_decision": BLOCKED_GATE_DECISION,
        "validation_errors": [],
    }
    try:
        catalog = load_source_catalog(catalog_path)
        onboarding = load_source_onboarding(
            onboarding_path,
            catalog=catalog,
            expected_catalog_ref=expected_catalog_ref,
        )
        decision = load_menustat_replacement_decision(
            decision_path,
            catalog=catalog,
            onboarding=onboarding,
            expected_catalog_ref=expected_catalog_ref,
            expected_onboarding_ref=expected_onboarding_ref,
        )
    except (MenuStatReplacementError, SourceCatalogError, SourceOnboardingError) as exc:
        report["validation_errors"] = [str(exc)]
        return report

    report.update(
        {
            "success": True,
            "catalog_ref": decision.catalog_ref,
            "onboarding_ref": decision.onboarding_ref,
            "candidate_count": len(decision.candidate_sources),
            "candidate_sources": [candidate.source for candidate in decision.candidate_sources],
            "authority_decisions": {
                candidate.source: candidate.authority_decision
                for candidate in decision.candidate_sources
            },
            "candidate_gate_decisions": {
                candidate.source: candidate.candidate_gate_decision
                for candidate in decision.candidate_sources
            },
        }
    )
    return report
