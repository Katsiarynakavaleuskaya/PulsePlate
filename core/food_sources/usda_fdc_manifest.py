"""File-only USDA FoodData Central manifest emitter."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

from core.food_sources.source_preflight import SourceManifest, parse_source_manifest

USDA_FDC_DOWNLOADS_URL = "https://fdc.nal.usda.gov/download-datasets"

USDAFDCSource = Literal["usda_foundation", "usda_branded", "usda_fndds"]


class USDAFDCSchemaStats(TypedDict):
    """CSV-derived local schema metadata."""

    fields: list[str]
    record_count: int


@dataclass(frozen=True)
class USDAFDCManifestContract:
    """Stable manifest defaults for a USDA/FDC source family."""

    source: USDAFDCSource
    primary_keys: tuple[str, ...]
    dedupe_fields: tuple[str, ...]
    mapping_fields: tuple[str, ...]
    collision_resolution: Literal["reject", "quarantine"]
    required_schema_fields: tuple[str, ...]


USDA_FDC_MANIFEST_CONTRACTS: dict[USDAFDCSource, USDAFDCManifestContract] = {
    "usda_foundation": USDAFDCManifestContract(
        source="usda_foundation",
        primary_keys=("fdc_id",),
        dedupe_fields=("fdc_id",),
        mapping_fields=("fdc_id", "description"),
        collision_resolution="reject",
        required_schema_fields=("fdc_id", "description", "data_type", "publication_date"),
    ),
    "usda_branded": USDAFDCManifestContract(
        source="usda_branded",
        primary_keys=("fdc_id",),
        dedupe_fields=("gtin_upc",),
        mapping_fields=("fdc_id", "gtin_upc", "description"),
        collision_resolution="quarantine",
        required_schema_fields=(
            "fdc_id",
            "gtin_upc",
            "description",
            "brand_owner",
            "data_type",
            "publication_date",
        ),
    ),
    "usda_fndds": USDAFDCManifestContract(
        source="usda_fndds",
        primary_keys=("fdc_id",),
        dedupe_fields=("food_code",),
        mapping_fields=("fdc_id", "food_code", "description"),
        collision_resolution="reject",
        required_schema_fields=(
            "fdc_id",
            "food_code",
            "description",
            "data_type",
            "start_date",
            "end_date",
        ),
    ),
}


def _checksum_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv_schema(path: Path) -> USDAFDCSchemaStats:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
            reader = csv.reader(file_obj)
            try:
                header = next(reader)
            except StopIteration as exc:
                raise ValueError(f"schema CSV is empty: {path}") from exc
            fields = [field.strip() for field in header if field.strip()]
            if not fields:
                raise ValueError(f"schema CSV has no non-empty header fields: {path}")
            return {"fields": fields, "record_count": sum(1 for _ in reader)}
    except UnicodeDecodeError as exc:
        raise ValueError(f"schema CSV must be UTF-8 compatible: {path}") from exc


def build_usda_fdc_manifest(
    *,
    source: USDAFDCSource,
    artifact_path: Path | str,
    source_version: str,
    retrieved_on: str,
    schema_csv_path: Path | str | None = None,
) -> SourceManifest:
    """Build and validate a USDA/FDC manifest from caller-provided local files only."""
    contract = USDA_FDC_MANIFEST_CONTRACTS[source]
    artifact = Path(artifact_path)
    if not artifact.is_file():
        raise ValueError(f"artifact_path must point to a local file: {artifact}")

    schema_path = Path(schema_csv_path) if schema_csv_path is not None else artifact
    if not schema_path.is_file():
        raise ValueError(f"schema_csv_path must point to a local file: {schema_path}")

    schema_stats = _read_csv_schema(schema_path)
    schema_fields = schema_stats["fields"]
    missing_required = sorted(set(contract.required_schema_fields) - set(schema_fields))
    if missing_required:
        missing = ", ".join(missing_required)
        raise ValueError(f"{source} schema is missing required fields: {missing}")

    payload = {
        "source": source,
        "source_classification": "current",
        "source_version": source_version,
        "source_url": USDA_FDC_DOWNLOADS_URL,
        "retrieved_on": retrieved_on,
        "artifact": {
            "path": artifact.as_posix(),
            "checksum_sha256": _checksum_sha256(artifact),
            "size_bytes": artifact.stat().st_size,
            "record_count": schema_stats["record_count"],
        },
        "schema": {
            "fields": schema_fields,
            "primary_keys": list(contract.primary_keys),
        },
        "collision_policy": {
            "dedupe_fields": list(contract.dedupe_fields),
            "mapping_fields": list(contract.mapping_fields),
            "collision_resolution": contract.collision_resolution,
        },
    }
    return parse_source_manifest(payload, context=f"generated:{source}")


def source_manifest_to_json_dict(manifest: SourceManifest) -> dict[str, object]:
    """Serialize a source manifest into its public JSON contract shape."""
    return {
        "source": manifest.source,
        "source_classification": manifest.source_classification,
        "source_version": manifest.source_version,
        "source_url": manifest.source_url,
        "retrieved_on": manifest.retrieved_on.isoformat(),
        "artifact": {
            "path": manifest.artifact.path,
            "checksum_sha256": manifest.artifact.checksum_sha256,
            "size_bytes": manifest.artifact.size_bytes,
            "record_count": manifest.artifact.record_count,
        },
        "schema": {
            "fields": list(manifest.schema.fields),
            "primary_keys": list(manifest.schema.primary_keys),
        },
        "collision_policy": {
            "dedupe_fields": list(manifest.collision_policy.dedupe_fields),
            "mapping_fields": list(manifest.collision_policy.mapping_fields),
            "collision_resolution": manifest.collision_policy.collision_resolution,
        },
    }
