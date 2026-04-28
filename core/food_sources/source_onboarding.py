"""
Deterministic food-source onboarding validation.

RU: Файловая проверка допуска внешних food/menu источников до ingest.
EN: File-only external food/menu source onboarding gate before ingest.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, cast

from core.food_sources.source_catalog import (
    SourceCatalog,
    SourceCatalogError,
    SourceFamily,
    load_source_catalog,
)
from core.food_sources.source_preflight import SourceClassification

_REPO_ROOT = Path(__file__).resolve().parents[2]

OnboardingStatus = Literal[
    "eligible_preflight",
    "legacy_baseline_blocked",
    "contract_review_blocked",
    "unresolved_blocked",
]

IngestionPath = Literal[
    "manifest_preflight_only",
    "legacy_snapshot_review_only",
    "commercial_contract_required",
    "unresolved_identity_required",
]

CacheDecision = Literal[
    "allowed_reviewed_snapshot",
    "legacy_review_only",
    "blocked_contract_required",
    "blocked_unresolved",
]

RedistributionDecision = Literal[
    "source_terms_review_required",
    "odbl_obligations_required",
    "not_allowed_by_default",
    "contract_required",
    "blocked_unresolved",
]

DisplayDecision = Literal[
    "allowed_with_attribution",
    "legacy_review_only",
    "blocked_contract_required",
    "blocked_unresolved",
]

CommercialRisk = Literal[
    "medium",
    "high",
    "medium_high",
    "unresolved",
]

ALLOWED_ONBOARDING_STATUSES: tuple[OnboardingStatus, ...] = (
    "eligible_preflight",
    "legacy_baseline_blocked",
    "contract_review_blocked",
    "unresolved_blocked",
)
ALLOWED_INGESTION_PATHS: tuple[IngestionPath, ...] = (
    "manifest_preflight_only",
    "legacy_snapshot_review_only",
    "commercial_contract_required",
    "unresolved_identity_required",
)
ALLOWED_CACHE_DECISIONS: tuple[CacheDecision, ...] = (
    "allowed_reviewed_snapshot",
    "legacy_review_only",
    "blocked_contract_required",
    "blocked_unresolved",
)
ALLOWED_REDISTRIBUTION_DECISIONS: tuple[RedistributionDecision, ...] = (
    "source_terms_review_required",
    "odbl_obligations_required",
    "not_allowed_by_default",
    "contract_required",
    "blocked_unresolved",
)
ALLOWED_DISPLAY_DECISIONS: tuple[DisplayDecision, ...] = (
    "allowed_with_attribution",
    "legacy_review_only",
    "blocked_contract_required",
    "blocked_unresolved",
)
ALLOWED_COMMERCIAL_RISKS: tuple[CommercialRisk, ...] = (
    "medium",
    "high",
    "medium_high",
    "unresolved",
)

_ONBOARDING_SCHEMA_RE = re.compile(r"^food-source-onboarding\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SourceOnboardingError(ValueError):
    """Raised when a food-source onboarding contract is invalid."""


@dataclass(frozen=True)
class SourceOnboardingEntry:
    """One source onboarding gate decision."""

    source: str
    source_classification: SourceClassification
    source_family: SourceFamily
    onboarding_status: OnboardingStatus
    ingestion_path: IngestionPath
    cache_decision: CacheDecision
    redistribution_decision: RedistributionDecision
    display_decision: DisplayDecision
    attribution_required: bool
    commercial_risk: CommercialRisk
    provider_policy_ref: str | None
    source_specific_policy_required: bool
    notes: str


@dataclass(frozen=True)
class SourceOnboarding:
    """Validated PR5 source-onboarding gate snapshot."""

    schema_version: str
    generated_on: date
    catalog_ref: str
    runtime_cutover: bool
    digitalocean_postgres_load: bool
    bulk_ingest: bool
    file_only: bool
    network_allowed: bool
    db_writes_allowed: bool
    sources: tuple[SourceOnboardingEntry, ...]


def _onboarding_error(context: str, detail: str) -> SourceOnboardingError:
    return SourceOnboardingError(f"Invalid source onboarding {context}: {detail}")


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _onboarding_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _onboarding_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _onboarding_error(context, f"missing non-empty string '{key}'")
    return value.strip()


def _optional_string(data: dict[str, object], key: str, context: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise _onboarding_error(context, f"'{key}' must be null or a non-empty string")
    return value.strip()


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _onboarding_error(context, f"'{key}' must be a boolean")
    return value


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _onboarding_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _onboarding_error(context, "generated_on must use YYYY-MM-DD") from exc


def _parse_choice(
    value: str,
    allowed: tuple[str, ...],
    key: str,
    context: str,
) -> str:
    if value not in allowed:
        joined = ", ".join(allowed)
        raise _onboarding_error(context, f"{key} must be one of: {joined}")
    return value


def _parse_onboarding_entry(value: object, context: str) -> SourceOnboardingEntry:
    data = _require_mapping(value, context)
    return SourceOnboardingEntry(
        source=_require_string(data, "source", context),
        source_classification=cast(
            SourceClassification,
            _parse_choice(
                _require_string(data, "source_classification", context),
                ("current", "legacy_static", "commercial_contract", "unresolved"),
                "source_classification",
                context,
            ),
        ),
        source_family=cast(
            SourceFamily,
            _parse_choice(
                _require_string(data, "source_family", context),
                (
                    "food_composition",
                    "barcode_branded",
                    "restaurant_menu",
                    "recipe_corpus",
                    "regional_catalog",
                    "commercial_api",
                    "unresolved",
                ),
                "source_family",
                context,
            ),
        ),
        onboarding_status=cast(
            OnboardingStatus,
            _parse_choice(
                _require_string(data, "onboarding_status", context),
                ALLOWED_ONBOARDING_STATUSES,
                "onboarding_status",
                context,
            ),
        ),
        ingestion_path=cast(
            IngestionPath,
            _parse_choice(
                _require_string(data, "ingestion_path", context),
                ALLOWED_INGESTION_PATHS,
                "ingestion_path",
                context,
            ),
        ),
        cache_decision=cast(
            CacheDecision,
            _parse_choice(
                _require_string(data, "cache_decision", context),
                ALLOWED_CACHE_DECISIONS,
                "cache_decision",
                context,
            ),
        ),
        redistribution_decision=cast(
            RedistributionDecision,
            _parse_choice(
                _require_string(data, "redistribution_decision", context),
                ALLOWED_REDISTRIBUTION_DECISIONS,
                "redistribution_decision",
                context,
            ),
        ),
        display_decision=cast(
            DisplayDecision,
            _parse_choice(
                _require_string(data, "display_decision", context),
                ALLOWED_DISPLAY_DECISIONS,
                "display_decision",
                context,
            ),
        ),
        attribution_required=_require_bool(data, "attribution_required", context),
        commercial_risk=cast(
            CommercialRisk,
            _parse_choice(
                _require_string(data, "commercial_risk", context),
                ALLOWED_COMMERCIAL_RISKS,
                "commercial_risk",
                context,
            ),
        ),
        provider_policy_ref=_optional_string(data, "provider_policy_ref", context),
        source_specific_policy_required=_require_bool(
            data,
            "source_specific_policy_required",
            context,
        ),
        notes=_require_string(data, "notes", context),
    )


def _validate_exact_catalog_coverage(
    catalog: SourceCatalog,
    entries: tuple[SourceOnboardingEntry, ...],
    context: str,
) -> None:
    catalog_sources = [entry.source for entry in catalog.sources]
    onboarding_sources = [entry.source for entry in entries]
    duplicates = sorted({name for name in onboarding_sources if onboarding_sources.count(name) > 1})
    if duplicates:
        raise _onboarding_error(context, f"duplicate sources: {', '.join(duplicates)}")

    missing = sorted(set(catalog_sources) - set(onboarding_sources))
    if missing:
        raise _onboarding_error(context, f"missing catalog sources: {', '.join(missing)}")

    unknown = sorted(set(onboarding_sources) - set(catalog_sources))
    if unknown:
        raise _onboarding_error(context, f"unknown onboarding sources: {', '.join(unknown)}")


def _validate_source_policy(
    catalog: SourceCatalog,
    entry: SourceOnboardingEntry,
    context: str,
) -> None:
    catalog_entries = {catalog_entry.source: catalog_entry for catalog_entry in catalog.sources}
    catalog_entry = catalog_entries[entry.source]
    if entry.source_classification != catalog_entry.source_classification:
        raise _onboarding_error(context, "source_classification must match catalog")
    if entry.source_family != catalog_entry.source_family:
        raise _onboarding_error(context, "source_family must match catalog")

    if entry.source == "open_food_facts":
        _require_policy(
            entry,
            context,
            onboarding_status="eligible_preflight",
            ingestion_path="manifest_preflight_only",
            cache_decision="allowed_reviewed_snapshot",
            redistribution_decision="odbl_obligations_required",
            display_decision="allowed_with_attribution",
            attribution_required=True,
            commercial_risk="medium",
            provider_policy_ref="docs/legal/ODbL_COMPLIANCE.md",
            source_specific_policy_required=True,
        )
        return

    if entry.source == "menustat":
        _require_policy(
            entry,
            context,
            onboarding_status="legacy_baseline_blocked",
            ingestion_path="legacy_snapshot_review_only",
            cache_decision="legacy_review_only",
            redistribution_decision="not_allowed_by_default",
            display_decision="legacy_review_only",
            attribution_required=True,
            commercial_risk="medium",
            provider_policy_ref=None,
            source_specific_policy_required=True,
        )
        if not catalog_entry.replacement_required:
            raise _onboarding_error(context, "menustat must remain replacement_required")
        return

    if entry.source_classification == "legacy_static":
        if not catalog_entry.replacement_required:
            raise _onboarding_error(
                context,
                "legacy_static sources must remain replacement_required",
            )
        _require_policy(
            entry,
            context,
            onboarding_status="legacy_baseline_blocked",
            ingestion_path="legacy_snapshot_review_only",
            cache_decision="legacy_review_only",
            redistribution_decision="not_allowed_by_default",
            display_decision="legacy_review_only",
            attribution_required=True,
            commercial_risk="medium",
            provider_policy_ref=None,
            source_specific_policy_required=True,
        )
        return

    if entry.source_classification == "current":
        _require_policy(
            entry,
            context,
            onboarding_status="eligible_preflight",
            ingestion_path="manifest_preflight_only",
            cache_decision="allowed_reviewed_snapshot",
            redistribution_decision="source_terms_review_required",
            display_decision="allowed_with_attribution",
            attribution_required=True,
            commercial_risk="medium",
            provider_policy_ref=None,
            source_specific_policy_required=True,
        )
        return

    if entry.source_classification == "commercial_contract":
        _require_policy(
            entry,
            context,
            onboarding_status="contract_review_blocked",
            ingestion_path="commercial_contract_required",
            cache_decision="blocked_contract_required",
            redistribution_decision="contract_required",
            display_decision="blocked_contract_required",
            attribution_required=True,
            commercial_risk="high",
            provider_policy_ref=None,
            source_specific_policy_required=True,
        )
        return

    if entry.source_classification == "unresolved":
        _require_policy(
            entry,
            context,
            onboarding_status="unresolved_blocked",
            ingestion_path="unresolved_identity_required",
            cache_decision="blocked_unresolved",
            redistribution_decision="blocked_unresolved",
            display_decision="blocked_unresolved",
            attribution_required=True,
            commercial_risk="unresolved",
            provider_policy_ref=None,
            source_specific_policy_required=True,
        )
        return


def _require_policy(
    entry: SourceOnboardingEntry,
    context: str,
    *,
    onboarding_status: OnboardingStatus,
    ingestion_path: IngestionPath,
    cache_decision: CacheDecision,
    redistribution_decision: RedistributionDecision,
    display_decision: DisplayDecision,
    attribution_required: bool,
    commercial_risk: CommercialRisk,
    provider_policy_ref: str | None,
    source_specific_policy_required: bool,
) -> None:
    expected: dict[str, object] = {
        "onboarding_status": onboarding_status,
        "ingestion_path": ingestion_path,
        "cache_decision": cache_decision,
        "redistribution_decision": redistribution_decision,
        "display_decision": display_decision,
        "attribution_required": attribution_required,
        "commercial_risk": commercial_risk,
        "provider_policy_ref": provider_policy_ref,
        "source_specific_policy_required": source_specific_policy_required,
    }
    actual: dict[str, object] = {
        "onboarding_status": entry.onboarding_status,
        "ingestion_path": entry.ingestion_path,
        "cache_decision": entry.cache_decision,
        "redistribution_decision": entry.redistribution_decision,
        "display_decision": entry.display_decision,
        "attribution_required": entry.attribution_required,
        "commercial_risk": entry.commercial_risk,
        "provider_policy_ref": entry.provider_policy_ref,
        "source_specific_policy_required": entry.source_specific_policy_required,
    }
    mismatches = [key for key, value in expected.items() if actual[key] != value]
    if mismatches:
        joined = ", ".join(mismatches)
        raise _onboarding_error(context, f"policy mismatch for {entry.source}: {joined}")


def parse_source_onboarding(
    payload: object,
    *,
    catalog: SourceCatalog,
    expected_catalog_ref: str | None = None,
    context: str = "<onboarding>",
) -> SourceOnboarding:
    """Parse and validate a source-onboarding payload against the catalog."""
    data = _require_mapping(payload, context)
    schema_version = _require_string(data, "schema_version", context)
    if not _ONBOARDING_SCHEMA_RE.fullmatch(schema_version):
        raise _onboarding_error(context, "schema_version must look like food-source-onboarding.vN")
    catalog_ref = _require_string(data, "catalog_ref", context)
    if expected_catalog_ref is not None and catalog_ref != expected_catalog_ref:
        raise _onboarding_error(
            context,
            f"catalog_ref must be {expected_catalog_ref!r}",
        )
    generated_on = _parse_date(_require_string(data, "generated_on", context), context)
    if generated_on != catalog.generated_on:
        raise _onboarding_error(
            context,
            f"generated_on must match catalog.generated_on ({catalog.generated_on.isoformat()})",
        )

    runtime_cutover = _require_bool(data, "runtime_cutover", context)
    digitalocean_postgres_load = _require_bool(data, "digitalocean_postgres_load", context)
    bulk_ingest = _require_bool(data, "bulk_ingest", context)
    file_only = _require_bool(data, "file_only", context)
    network_allowed = _require_bool(data, "network_allowed", context)
    db_writes_allowed = _require_bool(data, "db_writes_allowed", context)
    if (
        runtime_cutover
        or digitalocean_postgres_load
        or bulk_ingest
        or not file_only
        or network_allowed
        or db_writes_allowed
    ):
        raise _onboarding_error(
            context,
            "runtime_cutover, digitalocean_postgres_load, bulk_ingest, "
            "network_allowed, and db_writes_allowed must be false; file_only must be true",
        )

    raw_sources = data.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise _onboarding_error(context, "sources must be a non-empty list")
    entries = tuple(
        _parse_onboarding_entry(item, f"{context}.sources[{index}]")
        for index, item in enumerate(raw_sources)
    )
    _validate_exact_catalog_coverage(catalog, entries, context)
    for entry in entries:
        _validate_source_policy(catalog, entry, context)

    return SourceOnboarding(
        schema_version=schema_version,
        generated_on=generated_on,
        catalog_ref=catalog_ref,
        runtime_cutover=runtime_cutover,
        digitalocean_postgres_load=digitalocean_postgres_load,
        bulk_ingest=bulk_ingest,
        file_only=file_only,
        network_allowed=network_allowed,
        db_writes_allowed=db_writes_allowed,
        sources=entries,
    )


def load_source_onboarding(
    onboarding_path: Path | str,
    *,
    catalog: SourceCatalog,
    expected_catalog_ref: str | None = None,
) -> SourceOnboarding:
    """Load and validate a source-onboarding JSON file."""
    path = Path(onboarding_path)
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SourceOnboardingError(f"Cannot read source onboarding {path}: {exc}") from exc
    return parse_source_onboarding(
        payload,
        catalog=catalog,
        expected_catalog_ref=expected_catalog_ref,
        context=str(path),
    )


def _expected_catalog_ref(catalog_path: Path | str) -> str:
    """Return the canonical catalog ref embedded in PR5 onboarding snapshots."""
    path = Path(catalog_path)
    try:
        return path.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build_source_onboarding_report(
    catalog_path: Path | str,
    onboarding_path: Path | str,
) -> dict[str, object]:
    """Return a deterministic file-only onboarding report."""
    errors: list[str] = []
    onboarding: SourceOnboarding | None = None

    try:
        catalog = load_source_catalog(catalog_path)
    except SourceCatalogError as exc:
        errors.append(f"catalog: {exc}")
        catalog = None

    if catalog is not None:
        try:
            onboarding = load_source_onboarding(
                onboarding_path,
                catalog=catalog,
                expected_catalog_ref=_expected_catalog_ref(catalog_path),
            )
        except SourceOnboardingError as exc:
            errors.append(f"onboarding: {exc}")

    if errors or onboarding is None:
        return {
            "success": False,
            "dry_run": True,
            "runtime_cutover": False,
            "digitalocean_postgres_load": False,
            "bulk_ingest": False,
            "file_only": True,
            "network_allowed": False,
            "db_writes_allowed": False,
            "validation_errors": errors,
        }

    return {
        "success": True,
        "dry_run": True,
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "file_only": True,
        "network_allowed": False,
        "db_writes_allowed": False,
        "catalog_ref": onboarding.catalog_ref,
        "source_count": len(onboarding.sources),
        "blocked_sources": sorted(
            entry.source
            for entry in onboarding.sources
            if entry.onboarding_status != "eligible_preflight"
        ),
        "eligible_preflight_sources": sorted(
            entry.source
            for entry in onboarding.sources
            if entry.onboarding_status == "eligible_preflight"
        ),
        "validation_errors": [],
    }
