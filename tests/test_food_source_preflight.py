"""Tests for deterministic food source preflight manifests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources.source_preflight import (
    SourceManifestError,
    build_source_preflight_report,
    load_source_manifest,
)

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "food_source_preflight"
_SCRIPT = Path(__file__).parents[1] / "scripts" / "food_source_preflight.py"


def _fixture(name: str) -> Path:
    return _FIXTURE_DIR / name


def test_load_source_manifest_accepts_current_source_classification() -> None:
    manifest = load_source_manifest(_fixture("current_off_manifest.json"))

    assert manifest.source == "open_food_facts"
    assert manifest.source_classification == "current"
    assert manifest.artifact.checksum_sha256 == "a" * 64
    assert manifest.schema.primary_keys == ("code",)


def test_load_source_manifest_accepts_legacy_static_menustat() -> None:
    manifest = load_source_manifest(_fixture("legacy_menustat_manifest.json"))

    assert manifest.source == "menustat"
    assert manifest.source_classification == "legacy_static"
    assert manifest.source_version == "2022"


def test_load_source_manifest_rejects_invalid_source_classification() -> None:
    with pytest.raises(SourceManifestError, match="source_classification must be one of"):
        load_source_manifest(_fixture("invalid_classification_manifest.json"))


def test_load_source_manifest_rejects_primary_key_outside_schema(tmp_path: Path) -> None:
    manifest_path = tmp_path / "bad_pk.json"
    manifest_path.write_text(
        json.dumps(
            {
                "artifact": {
                    "checksum_sha256": "e" * 64,
                    "path": "raw/usda/foundation.json",
                    "record_count": 1,
                    "size_bytes": 1,
                },
                "retrieved_on": "2026-04-24",
                "schema": {"fields": ["fdc_id"], "primary_keys": ["missing_id"]},
                "source": "usda_foundation",
                "source_classification": "current",
                "source_url": "https://fdc.nal.usda.gov/download-datasets",
                "source_version": "2025-12",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SourceManifestError, match="primary_keys missing from fields"):
        load_source_manifest(manifest_path)


def test_build_source_preflight_report_diff_contract() -> None:
    report = build_source_preflight_report(
        _fixture("current_off_manifest.json"),
        _fixture("incoming_off_manifest.json"),
    )

    assert report["success"] is True
    assert report["dry_run"] is True
    assert report["runtime_cutover"] is False
    assert report["source_classification"] == "current"
    assert report["version"] == {
        "current": "2026-04-24",
        "incoming": "2026-04-25",
        "changed": True,
    }
    assert report["checksum"] == {
        "current": "a" * 64,
        "incoming": "b" * 64,
        "changed": True,
    }
    assert report["row_count"] == {
        "current": 100,
        "incoming": 120,
        "delta": 20,
        "changed": True,
    }
    assert report["schema"] == {"added": ["quantity"], "removed": ["brands"]}
    assert report["primary_keys"] == {"added": [], "removed": []}


def test_build_source_preflight_report_surfaces_validation_errors() -> None:
    report = build_source_preflight_report(
        _fixture("current_off_manifest.json"),
        _fixture("invalid_classification_manifest.json"),
    )

    assert report["success"] is False
    assert report["runtime_cutover"] is False
    assert report["dry_run"] is True
    assert "source_classification must be one of" in str(report["validation_errors"])


def test_food_source_preflight_cli_is_file_only_and_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://must-not-be-used.invalid/db")
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--current-manifest",
            str(_fixture("current_off_manifest.json")),
            "--incoming-manifest",
            str(_fixture("incoming_off_manifest.json")),
            "--dry-run",
            "--json",
        ],
        cwd=Path(__file__).parents[1],
        check=True,
        text=True,
        capture_output=True,
    )
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["runtime_cutover"] is False
    assert result.stderr == ""
    assert after == before


def test_food_source_preflight_cli_returns_nonzero_for_invalid_manifest() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--current-manifest",
            str(_fixture("current_off_manifest.json")),
            "--incoming-manifest",
            str(_fixture("invalid_classification_manifest.json")),
            "--dry-run",
            "--json",
        ],
        cwd=Path(__file__).parents[1],
        check=False,
        text=True,
        capture_output=True,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["success"] is False
    assert payload["runtime_cutover"] is False
