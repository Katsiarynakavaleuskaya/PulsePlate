"""
Deterministic food-source catalog validation for pre-ingest planning.

RU: Проверка каталога источников до загрузки данных.
EN: Source catalog validation before any data ingest.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlparse

from core.food_sources.source_preflight import (
    ALLOWED_SOURCE_CLASSIFICATIONS,
    SourceClassification,
)

SourceFamily = Literal[
    "food_composition",
    "barcode_branded",
    "restaurant_menu",
    "recipe_corpus",
    "regional_catalog",
    "commercial_api",
    "unresolved",
]

CatalogStatus = Literal[
    "candidate",
    "legacy_baseline",
    "deferred",
    "blocked_unresolved",
]

LicenseReviewStatus = Literal[
    "public_review_required",
    "odbl_obligations",
    "commercial_contract_required",
    "unresolved_required",
    "legacy_file_review_required",
]

ALLOWED_SOURCE_FAMILIES: tuple[SourceFamily, ...] = (
    "food_composition",
    "barcode_branded",
    "restaurant_menu",
    "recipe_corpus",
    "regional_catalog",
    "commercial_api",
    "unresolved",
)

ALLOWED_CATALOG_STATUSES: tuple[CatalogStatus, ...] = (
    "candidate",
    "legacy_baseline",
    "deferred",
    "blocked_unresolved",
)

ALLOWED_LICENSE_REVIEW_STATUSES: tuple[LicenseReviewStatus, ...] = (
    "public_review_required",
    "odbl_obligations",
    "commercial_contract_required",
    "unresolved_required",
    "legacy_file_review_required",
)

_CATALOG_SCHEMA_RE = re.compile(r"^food-source-catalog\.v\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SourceCatalogError(ValueError):
    """Raised when the source catalog contract is invalid."""


@dataclass(frozen=True)
class SourceCatalogEntry:
    """One source candidate or legacy baseline entry in the catalog."""

    source: str
    source_classification: SourceClassification
    source_family: SourceFamily
    status: CatalogStatus
    source_url: str
    license_review: LicenseReviewStatus
    active_update_source: bool
    manifest_required: bool
    preflight_required: bool
    replacement_required: bool
    replacement_for: str | None
    notes: str


@dataclass(frozen=True)
class SourceCatalog:
    """Validated source catalog with explicit no-cutover safety flags."""

    schema_version: str
    generated_on: date
    runtime_cutover: bool
    digitalocean_postgres_load: bool
    bulk_ingest: bool
    sources: tuple[SourceCatalogEntry, ...]


def _catalog_error(context: str, detail: str) -> SourceCatalogError:
    return SourceCatalogError(f"Invalid source catalog {context}: {detail}")


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _catalog_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _catalog_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _catalog_error(context, f"missing non-empty string '{key}'")
    return value.strip()


def _require_bool(data: dict[str, object], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _catalog_error(context, f"'{key}' must be a boolean")
    return value


def _optional_string(data: dict[str, object], key: str, context: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise _catalog_error(context, f"'{key}' must be null or a non-empty string")
    return value.strip()


def _parse_date(value: str, context: str) -> date:
    if not _DATE_RE.fullmatch(value):
        raise _catalog_error(context, "generated_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _catalog_error(context, "generated_on must use YYYY-MM-DD") from exc


def _validate_url(value: str, context: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise _catalog_error(context, "source_url must be an absolute http(s) URL")
    return value


def _parse_choice(
    value: str,
    allowed: tuple[str, ...],
    key: str,
    context: str,
) -> str:
    if value not in allowed:
        joined = ", ".join(allowed)
        raise _catalog_error(context, f"{key} must be one of: {joined}")
    return value


def _parse_source_catalog_entry(value: object, context: str) -> SourceCatalogEntry:
    data = _require_mapping(value, context)
    classification = cast(
        SourceClassification,
        _parse_choice(
            _require_string(data, "source_classification", context),
            ALLOWED_SOURCE_CLASSIFICATIONS,
            "source_classification",
            context,
        ),
    )
    family = cast(
        SourceFamily,
        _parse_choice(
            _require_string(data, "source_family", context),
            ALLOWED_SOURCE_FAMILIES,
            "source_family",
            context,
        ),
    )
    status = cast(
        CatalogStatus,
        _parse_choice(
            _require_string(data, "status", context),
            ALLOWED_CATALOG_STATUSES,
            "status",
            context,
        ),
    )
    license_review = cast(
        LicenseReviewStatus,
        _parse_choice(
            _require_string(data, "license_review", context),
            ALLOWED_LICENSE_REVIEW_STATUSES,
            "license_review",
            context,
        ),
    )
    entry = SourceCatalogEntry(
        source=_require_string(data, "source", context),
        source_classification=classification,
        source_family=family,
        status=status,
        source_url=_validate_url(_require_string(data, "source_url", context), context),
        license_review=license_review,
        active_update_source=_require_bool(data, "active_update_source", context),
        manifest_required=_require_bool(data, "manifest_required", context),
        preflight_required=_require_bool(data, "preflight_required", context),
        replacement_required=_require_bool(data, "replacement_required", context),
        replacement_for=_optional_string(data, "replacement_for", context),
        notes=_require_string(data, "notes", context),
    )
    _validate_catalog_entry_policy(entry, context)
    return entry


def _validate_catalog_entry_policy(entry: SourceCatalogEntry, context: str) -> None:
    if not entry.manifest_required or not entry.preflight_required:
        raise _catalog_error(context, "manifest_required and preflight_required must be true")
    if entry.source_classification == "legacy_static" and entry.active_update_source:
        raise _catalog_error(context, "legacy_static sources cannot be active update sources")
    if entry.source_classification == "unresolved" and entry.status != "blocked_unresolved":
        raise _catalog_error(context, "unresolved sources must use blocked_unresolved status")
    if entry.source_classification == "unresolved" and (
        entry.license_review != "unresolved_required"
    ):
        raise _catalog_error(
            context,
            "unresolved sources require unresolved_required license review",
        )
    if entry.source_classification == "commercial_contract" and (
        entry.license_review != "commercial_contract_required"
    ):
        raise _catalog_error(
            context,
            "commercial_contract sources require commercial_contract_required license review",
        )
    if entry.source == "menustat":
        if entry.source_classification != "legacy_static":
            raise _catalog_error(context, "menustat must remain legacy_static")
        if entry.active_update_source:
            raise _catalog_error(context, "menustat cannot be an active update source")
        if not entry.replacement_required:
            raise _catalog_error(context, "menustat requires a replacement decision")


def parse_source_catalog(payload: object, *, context: str = "<catalog>") -> SourceCatalog:
    """Parse and validate the deterministic source catalog contract."""
    data = _require_mapping(payload, context)
    schema_version = _require_string(data, "schema_version", context)
    if not _CATALOG_SCHEMA_RE.fullmatch(schema_version):
        raise _catalog_error(context, "schema_version must look like food-source-catalog.vN")

    runtime_cutover = _require_bool(data, "runtime_cutover", context)
    digitalocean_postgres_load = _require_bool(data, "digitalocean_postgres_load", context)
    bulk_ingest = _require_bool(data, "bulk_ingest", context)
    if runtime_cutover or digitalocean_postgres_load or bulk_ingest:
        raise _catalog_error(
            context, "runtime_cutover, digitalocean_postgres_load, and bulk_ingest must be false"
        )

    raw_sources = data.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise _catalog_error(context, "sources must be a non-empty list")
    entries = tuple(
        _parse_source_catalog_entry(item, f"{context}.sources[{index}]")
        for index, item in enumerate(raw_sources)
    )
    _validate_catalog_policy(entries, context)
    return SourceCatalog(
        schema_version=schema_version,
        generated_on=_parse_date(_require_string(data, "generated_on", context), context),
        runtime_cutover=runtime_cutover,
        digitalocean_postgres_load=digitalocean_postgres_load,
        bulk_ingest=bulk_ingest,
        sources=entries,
    )


def _validate_catalog_policy(entries: tuple[SourceCatalogEntry, ...], context: str) -> None:
    names = [entry.source for entry in entries]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise _catalog_error(context, f"duplicate sources: {', '.join(duplicates)}")

    entry_names = set(names)
    replacement_targets = {
        entry.replacement_for for entry in entries if entry.replacement_for is not None
    }
    missing_targets = sorted(target for target in replacement_targets if target not in entry_names)
    if missing_targets:
        raise _catalog_error(
            context, f"replacement_for target missing: {', '.join(missing_targets)}"
        )

    if "menustat" in entry_names and not any(
        entry.source != "menustat" and entry.replacement_for == "menustat" for entry in entries
    ):
        raise _catalog_error(context, "menustat requires at least one replacement candidate")


def load_source_catalog(path: Path | str) -> SourceCatalog:
    """Load and validate a source catalog JSON file."""
    catalog_path = Path(path)
    try:
        with catalog_path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SourceCatalogError(f"Cannot read source catalog {catalog_path}: {exc}") from exc
    return parse_source_catalog(payload, context=str(catalog_path))
