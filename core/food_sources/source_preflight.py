"""
Deterministic food-source manifest validation and dry-run diff contracts.

RU: Строгая валидация манифеста источника до ingest/cutover.
EN: Strict source manifest validation before ingest/cutover.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

SourceClassification = Literal[
    "current",
    "legacy_static",
    "commercial_contract",
    "unresolved",
]

CollisionResolution = Literal["reject", "quarantine", "skip"]

ALLOWED_SOURCE_CLASSIFICATIONS: tuple[SourceClassification, ...] = (
    "current",
    "legacy_static",
    "commercial_contract",
    "unresolved",
)
ALLOWED_COLLISION_RESOLUTIONS: tuple[CollisionResolution, ...] = (
    "reject",
    "quarantine",
    "skip",
)

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_RETRIEVED_ON_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class SourceManifestError(ValueError):
    """Raised when a source preflight manifest is invalid."""


@dataclass(frozen=True)
class SourceArtifact:
    """Immutable artifact metadata declared by a source manifest."""

    path: str
    checksum_sha256: str
    size_bytes: int
    record_count: int


@dataclass(frozen=True)
class SourceSchema:
    """Declared field and stable identifier contract for a source artifact."""

    fields: tuple[str, ...]
    primary_keys: tuple[str, ...]


@dataclass(frozen=True)
class SourceCollisionPolicy:
    """Collision and dedupe contract for incoming source snapshots."""

    dedupe_fields: tuple[str, ...]
    mapping_fields: tuple[str, ...]
    collision_resolution: CollisionResolution


@dataclass(frozen=True)
class SourceManifest:
    """Strict PR2 source manifest contract."""

    source: str
    source_classification: SourceClassification
    source_version: str
    source_url: str
    retrieved_on: date
    artifact: SourceArtifact
    schema: SourceSchema
    collision_policy: SourceCollisionPolicy


def _schema_error(context: str, detail: str) -> SourceManifestError:
    """Build a stable manifest validation error."""
    return SourceManifestError(f"Invalid source manifest {context}: {detail}")


def _require_mapping(value: object, context: str) -> dict[str, object]:
    """Return an object mapping with string keys."""
    if not isinstance(value, dict):
        raise _schema_error(context, "must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise _schema_error(context, "all object keys must be strings")
        result[key] = item
    return result


def _require_string(data: dict[str, object], key: str, context: str) -> str:
    """Return a required non-empty string field."""
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _schema_error(context, f"missing non-empty string '{key}'")
    return value.strip()


def _require_non_negative_int(data: dict[str, object], key: str, context: str) -> int:
    """Return a required non-negative integer field."""
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise _schema_error(context, f"'{key}' must be a non-negative int")
    return value


def _require_string_tuple(data: dict[str, object], key: str, context: str) -> tuple[str, ...]:
    """Return a required unique non-empty string list as a tuple."""
    value = data.get(key)
    if not isinstance(value, list):
        raise _schema_error(context, f"'{key}' must be a list of strings")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise _schema_error(context, f"'{key}[{index}]' must be a non-empty string")
        normalized = item.strip()
        if normalized in seen:
            raise _schema_error(context, f"'{key}' contains duplicate value {normalized!r}")
        seen.add(normalized)
        items.append(normalized)
    if not items:
        raise _schema_error(context, f"'{key}' must not be empty")
    return tuple(items)


def _parse_classification(value: str, context: str) -> SourceClassification:
    """Validate and return a source classification literal."""
    for classification in ALLOWED_SOURCE_CLASSIFICATIONS:
        if value == classification:
            return classification
    allowed = ", ".join(ALLOWED_SOURCE_CLASSIFICATIONS)
    raise _schema_error(context, f"source_classification must be one of: {allowed}")


def _validate_url(value: str, context: str) -> str:
    """Validate an absolute HTTP(S) source URL."""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise _schema_error(context, "source_url must be an absolute http(s) URL")
    return value


def _parse_iso_date(value: str, context: str) -> date:
    """Parse a strict YYYY-MM-DD date field."""
    if not _RETRIEVED_ON_RE.fullmatch(value):
        raise _schema_error(context, "retrieved_on must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _schema_error(context, "retrieved_on must use YYYY-MM-DD") from exc


def _parse_artifact(value: object, context: str) -> SourceArtifact:
    """Parse immutable artifact metadata."""
    artifact = _require_mapping(value, f"{context}.artifact")
    checksum = _require_string(artifact, "checksum_sha256", f"{context}.artifact")
    if not _SHA256_RE.fullmatch(checksum):
        raise _schema_error(f"{context}.artifact", "'checksum_sha256' must be 64 hex chars")
    return SourceArtifact(
        path=_require_string(artifact, "path", f"{context}.artifact"),
        checksum_sha256=checksum.lower(),
        size_bytes=_require_non_negative_int(artifact, "size_bytes", f"{context}.artifact"),
        record_count=_require_non_negative_int(artifact, "record_count", f"{context}.artifact"),
    )


def _parse_schema(value: object, context: str) -> SourceSchema:
    """Parse source schema and primary-key metadata."""
    schema = _require_mapping(value, f"{context}.schema")
    fields = _require_string_tuple(schema, "fields", f"{context}.schema")
    primary_keys = _require_string_tuple(schema, "primary_keys", f"{context}.schema")
    missing_keys = sorted(set(primary_keys) - set(fields))
    if missing_keys:
        joined = ", ".join(missing_keys)
        raise _schema_error(f"{context}.schema", f"primary_keys missing from fields: {joined}")
    return SourceSchema(fields=fields, primary_keys=primary_keys)


def _parse_collision_policy(
    value: object,
    schema: SourceSchema,
    context: str,
) -> SourceCollisionPolicy:
    """Parse immutable dedupe/mapping collision policy."""
    collision = _require_mapping(value, f"{context}.collision_policy")
    dedupe_fields = _require_string_tuple(
        collision,
        "dedupe_fields",
        f"{context}.collision_policy",
    )
    mapping_fields = _require_string_tuple(
        collision,
        "mapping_fields",
        f"{context}.collision_policy",
    )
    resolution = _require_string(collision, "collision_resolution", f"{context}.collision_policy")
    if resolution not in ALLOWED_COLLISION_RESOLUTIONS:
        raise _schema_error(
            f"{context}.collision_policy",
            "collision_resolution must be one of: reject, quarantine, skip",
        )
    if resolution == "reject":
        collision_resolution: CollisionResolution = "reject"
    elif resolution == "quarantine":
        collision_resolution = "quarantine"
    else:
        collision_resolution = "skip"

    allowed_fields = set(schema.fields)
    out_of_schema_dedupe = sorted(set(dedupe_fields) - allowed_fields)
    if out_of_schema_dedupe:
        joined = ", ".join(out_of_schema_dedupe)
        raise _schema_error(
            f"{context}.collision_policy",
            f"dedupe_fields must reference schema fields: {joined}",
        )

    out_of_schema_mapping = sorted(set(mapping_fields) - allowed_fields)
    if out_of_schema_mapping:
        joined = ", ".join(out_of_schema_mapping)
        raise _schema_error(
            f"{context}.collision_policy",
            f"mapping_fields must reference schema fields: {joined}",
        )

    return SourceCollisionPolicy(
        dedupe_fields=dedupe_fields,
        mapping_fields=mapping_fields,
        collision_resolution=collision_resolution,
    )


def parse_source_manifest(payload: object, *, context: str = "<manifest>") -> SourceManifest:
    """Parse and validate a source preflight manifest payload."""
    data = _require_mapping(payload, context)
    classification = _parse_classification(
        _require_string(data, "source_classification", context),
        context,
    )
    source_url = _validate_url(_require_string(data, "source_url", context), context)
    schema = _parse_schema(data.get("schema"), context)
    return SourceManifest(
        source=_require_string(data, "source", context),
        source_classification=classification,
        source_version=_require_string(data, "source_version", context),
        source_url=source_url,
        retrieved_on=_parse_iso_date(_require_string(data, "retrieved_on", context), context),
        artifact=_parse_artifact(data.get("artifact"), context),
        schema=schema,
        collision_policy=_parse_collision_policy(
            value=data.get("collision_policy"),
            schema=schema,
            context=context,
        ),
    )


def load_source_manifest(path: Path | str) -> SourceManifest:
    """Load and validate a source preflight manifest from JSON."""
    manifest_path = Path(path)
    try:
        with manifest_path.open("r", encoding="utf-8") as file_obj:
            payload: object = json.load(file_obj)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SourceManifestError(f"Cannot read source manifest {manifest_path}: {exc}") from exc
    return parse_source_manifest(payload, context=str(manifest_path))


def _string_delta(current: str, incoming: str) -> dict[str, object]:
    """Return deterministic string delta metadata."""
    return {
        "current": current,
        "incoming": incoming,
        "changed": current != incoming,
    }


def _integer_delta(current: int, incoming: int) -> dict[str, object]:
    """Return deterministic integer delta metadata."""
    return {
        "current": current,
        "incoming": incoming,
        "delta": incoming - current,
        "changed": current != incoming,
    }


def _set_delta(current: tuple[str, ...], incoming: tuple[str, ...]) -> dict[str, list[str]]:
    """Return sorted set additions and removals."""
    current_set = set(current)
    incoming_set = set(incoming)
    return {
        "added": sorted(incoming_set - current_set),
        "removed": sorted(current_set - incoming_set),
    }


def build_source_diff_report(
    current: SourceManifest,
    incoming: SourceManifest,
) -> dict[str, object]:
    """
    Build the deterministic dry-run report for two already-validated manifests.

    The report is intentionally side-effect free and always declares
    ``runtime_cutover=false`` for PR2.
    """
    errors: list[str] = []
    if current.source != incoming.source:
        errors.append(
            "source mismatch: " f"current={current.source!r} incoming={incoming.source!r}"
        )

    schema_delta = _set_delta(current.schema.fields, incoming.schema.fields)
    primary_key_delta = _set_delta(current.schema.primary_keys, incoming.schema.primary_keys)
    dedupe_delta = _set_delta(
        current.collision_policy.dedupe_fields,
        incoming.collision_policy.dedupe_fields,
    )
    mapping_delta = _set_delta(
        current.collision_policy.mapping_fields,
        incoming.collision_policy.mapping_fields,
    )
    collision_resolution_delta = _string_delta(
        current.collision_policy.collision_resolution,
        incoming.collision_policy.collision_resolution,
    )

    return {
        "success": not errors,
        "dry_run": True,
        "runtime_cutover": False,
        "source": _string_delta(current.source, incoming.source),
        "source_classification": incoming.source_classification,
        "source_url": incoming.source_url,
        "retrieved_on": incoming.retrieved_on.isoformat(),
        "version": _string_delta(current.source_version, incoming.source_version),
        "checksum": _string_delta(
            current.artifact.checksum_sha256,
            incoming.artifact.checksum_sha256,
        ),
        "row_count": _integer_delta(
            current.artifact.record_count,
            incoming.artifact.record_count,
        ),
        "size_bytes": _integer_delta(
            current.artifact.size_bytes,
            incoming.artifact.size_bytes,
        ),
        "schema": schema_delta,
        "primary_keys": primary_key_delta,
        "collision_policy": {
            "dedupe_fields": dedupe_delta,
            "mapping_fields": mapping_delta,
            "collision_resolution": collision_resolution_delta,
        },
        "validation_errors": errors,
    }


def build_source_preflight_report(
    current_manifest: Path | str,
    incoming_manifest: Path | str,
) -> dict[str, object]:
    """Load manifests and return a dry-run report with validation errors."""
    errors: list[str] = []
    current: SourceManifest | None = None
    incoming: SourceManifest | None = None

    try:
        current = load_source_manifest(current_manifest)
    except SourceManifestError as exc:
        errors.append(f"current_manifest: {exc}")

    try:
        incoming = load_source_manifest(incoming_manifest)
    except SourceManifestError as exc:
        errors.append(f"incoming_manifest: {exc}")

    if errors or current is None or incoming is None:
        return {
            "success": False,
            "dry_run": True,
            "runtime_cutover": False,
            "validation_errors": errors,
        }

    return build_source_diff_report(current, incoming)


def validate_manifest_source_contract(
    manifest: SourceManifest,
    *,
    catalog_path: Path | str,
    onboarding_path: Path | str,
) -> list[str]:
    """
    Validate a manifest against the governed catalog/onboarding preflight contract.

    RU: Проверка только файлового допуска preflight, без ingest/сети/БД.
    EN: File-only preflight eligibility check, with no ingest/network/database side effects.
    """
    from core.food_sources.source_catalog import SourceCatalogError, load_source_catalog
    from core.food_sources.source_onboarding import (
        SourceOnboardingError,
        load_source_onboarding,
    )

    errors: list[str] = []
    try:
        catalog = load_source_catalog(catalog_path)
    except SourceCatalogError as exc:
        return [f"catalog: {exc}"]

    expected_catalog_ref = _expected_catalog_ref(catalog_path)
    try:
        onboarding = load_source_onboarding(
            onboarding_path,
            catalog=catalog,
            expected_catalog_ref=expected_catalog_ref,
        )
    except SourceOnboardingError as exc:
        return [f"onboarding: {exc}"]

    catalog_entries = {entry.source: entry for entry in catalog.sources}
    catalog_entry = catalog_entries.get(manifest.source)
    if catalog_entry is None:
        errors.append(f"catalog: unknown source {manifest.source!r}")
    else:
        if manifest.source_classification != catalog_entry.source_classification:
            errors.append(
                "catalog: source_classification mismatch for "
                f"{manifest.source!r}: manifest={manifest.source_classification!r} "
                f"catalog={catalog_entry.source_classification!r}"
            )
        if manifest.source_url != catalog_entry.source_url:
            errors.append(
                "catalog: source_url mismatch for "
                f"{manifest.source!r}: manifest={manifest.source_url!r} "
                f"catalog={catalog_entry.source_url!r}"
            )
        if not catalog_entry.manifest_required:
            errors.append(f"catalog: {manifest.source!r} must require a manifest")
        if not catalog_entry.preflight_required:
            errors.append(f"catalog: {manifest.source!r} must require preflight")
        if not catalog_entry.active_update_source:
            errors.append(f"catalog: {manifest.source!r} must be an active update source")

    onboarding_entries = {entry.source: entry for entry in onboarding.sources}
    onboarding_entry = onboarding_entries.get(manifest.source)
    if onboarding_entry is None:
        errors.append(f"onboarding: missing source {manifest.source!r}")
    else:
        if onboarding_entry.onboarding_status != "eligible_preflight":
            errors.append(
                "onboarding: "
                f"{manifest.source!r} must be eligible_preflight, got "
                f"{onboarding_entry.onboarding_status!r}"
            )
        if onboarding_entry.ingestion_path != "manifest_preflight_only":
            errors.append(
                "onboarding: "
                f"{manifest.source!r} must use manifest_preflight_only, got "
                f"{onboarding_entry.ingestion_path!r}"
            )

    if onboarding.runtime_cutover:
        errors.append("onboarding: runtime_cutover must remain false")
    if onboarding.digitalocean_postgres_load:
        errors.append("onboarding: digitalocean_postgres_load must remain false")
    if onboarding.bulk_ingest:
        errors.append("onboarding: bulk_ingest must remain false")
    if not onboarding.file_only:
        errors.append("onboarding: file_only must remain true")
    if onboarding.network_allowed:
        errors.append("onboarding: network_allowed must remain false")
    if onboarding.db_writes_allowed:
        errors.append("onboarding: db_writes_allowed must remain false")

    return errors


def _expected_catalog_ref(catalog_path: Path | str) -> str:
    """Return the repository-relative catalog ref used by onboarding snapshots."""
    path = Path(catalog_path)
    try:
        return path.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
