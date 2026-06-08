"""Tests for the file-only USDA/FDC manifest emitter."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from core.food_sources.source_preflight import validate_manifest_source_contract
from core.food_sources.usda_fdc_manifest import (
    USDA_FDC_DOWNLOADS_URL,
    USDAFDCSource,
    build_usda_fdc_manifest,
    source_manifest_to_json_dict,
)

_REPO_ROOT = Path(__file__).parents[1]
_SCRIPT = _REPO_ROOT / "scripts" / "food_source_usda_fdc_manifest.py"
_CATALOG = _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json"
_ONBOARDING = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json"
)


def _write_csv(tmp_path: Path, name: str, header: list[str], rows: list[list[str]]) -> Path:
    path = tmp_path / name
    line_items = [",".join(header), *((",".join(row) for row in rows))]
    path.write_text("\n".join(line_items) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("source", "version", "header", "rows", "dedupe_fields", "resolution"),
    (
        (
            "usda_foundation",
            "fdc-foundation-2026-04",
            ["fdc_id", "description", "food_category_id", "publication_date", "data_type"],
            [["1101", "Apple, raw", "900", "2026-04-01", "Foundation"]],
            ("fdc_id",),
            "reject",
        ),
        (
            "usda_branded",
            "fdc-branded-2026-04",
            [
                "fdc_id",
                "gtin_upc",
                "description",
                "brand_owner",
                "publication_date",
                "data_type",
            ],
            [["2202", "000111222333", "Yogurt", "Example Brand", "2026-04-01", "Branded"]],
            ("gtin_upc",),
            "quarantine",
        ),
        (
            "usda_fndds",
            "fdc-fndds-2021-2023-2024-10",
            ["fdc_id", "food_code", "description", "data_type", "start_date", "end_date"],
            [["3303", "12345678", "Rice, cooked", "Survey (FNDDS)", "2021-01-01", "2023-12-31"]],
            ("food_code",),
            "reject",
        ),
    ),
)
def test_build_usda_fdc_manifest_uses_existing_source_preflight_contract(
    tmp_path: Path,
    source: str,
    version: str,
    header: list[str],
    rows: list[list[str]],
    dedupe_fields: tuple[str, ...],
    resolution: str,
) -> None:
    artifact = _write_csv(tmp_path, f"{source}.csv", header, rows)

    manifest = build_usda_fdc_manifest(
        source=cast(USDAFDCSource, source),
        artifact_path=artifact,
        source_version=version,
        retrieved_on="2026-06-08",
    )

    assert manifest.source == source
    assert manifest.source_version == version
    assert manifest.source_url == USDA_FDC_DOWNLOADS_URL
    assert manifest.artifact.record_count == len(rows)
    assert manifest.artifact.size_bytes == artifact.stat().st_size
    assert manifest.schema.primary_keys == ("fdc_id",)
    assert manifest.collision_policy.dedupe_fields == dedupe_fields
    assert manifest.collision_policy.collision_resolution == resolution
    assert (
        validate_manifest_source_contract(
            manifest,
            catalog_path=_CATALOG,
            onboarding_path=_ONBOARDING,
        )
        == []
    )


def test_build_usda_fdc_manifest_rejects_schema_missing_required_fields(tmp_path: Path) -> None:
    artifact = _write_csv(
        tmp_path,
        "branded.csv",
        ["fdc_id", "description", "publication_date", "data_type"],
        [["2202", "Yogurt", "2026-04-01", "Branded"]],
    )

    with pytest.raises(ValueError, match="missing required fields: brand_owner, gtin_upc"):
        build_usda_fdc_manifest(
            source="usda_branded",
            artifact_path=artifact,
            source_version="fdc-branded-2026-04",
            retrieved_on="2026-06-08",
        )


def test_usda_fdc_manifest_cli_is_file_only_and_independent_of_demo_key(
    tmp_path: Path,
) -> None:
    artifact = _write_csv(
        tmp_path,
        "foundation.csv",
        ["fdc_id", "description", "food_category_id", "publication_date", "data_type"],
        [["1101", "Apple, raw", "900", "2026-04-01", "Foundation"]],
    )
    before = {path.name for path in tmp_path.iterdir()}
    env = os.environ.copy()
    env.pop("USDA_API_KEY", None)
    env["DATABASE_URL"] = "postgresql://invalid.invalid/pulseplate"

    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--source",
            "usda_foundation",
            "--artifact-path",
            str(artifact),
            "--source-version",
            "fdc-foundation-2026-04",
            "--retrieved-on",
            "2026-06-08",
            "--json",
        ],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["source"] == "usda_foundation"
    assert payload["source_version"] == "fdc-foundation-2026-04"
    assert payload["source_url"] == USDA_FDC_DOWNLOADS_URL
    assert payload["artifact"]["record_count"] == 1
    assert {path.name for path in tmp_path.iterdir()} == before
    assert not (tmp_path / "data").exists()


def test_source_manifest_serialization_round_trips_to_json_contract(tmp_path: Path) -> None:
    artifact = _write_csv(
        tmp_path,
        "fndds.csv",
        ["fdc_id", "food_code", "description", "data_type", "start_date", "end_date"],
        [["3303", "12345678", "Rice, cooked", "Survey (FNDDS)", "2021-01-01", "2023-12-31"]],
    )

    manifest = build_usda_fdc_manifest(
        source="usda_fndds",
        artifact_path=artifact,
        source_version="fdc-fndds-2021-2023-2024-10",
        retrieved_on="2026-06-08",
    )

    payload = source_manifest_to_json_dict(manifest)

    assert payload["retrieved_on"] == "2026-06-08"
    assert payload["schema"] == {
        "fields": ["fdc_id", "food_code", "description", "data_type", "start_date", "end_date"],
        "primary_keys": ["fdc_id"],
    }
