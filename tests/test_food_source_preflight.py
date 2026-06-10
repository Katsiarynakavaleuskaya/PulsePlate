"""Tests for deterministic food source preflight manifests."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Callable, cast

import pytest

from core.food_sources.source_catalog import SourceCatalog, SourceCatalogEntry, SourceCatalogError
from core.food_sources.source_onboarding import (
    IngestionPath,
    OnboardingStatus,
    SourceOnboarding,
    SourceOnboardingEntry,
    SourceOnboardingError,
)
from core.food_sources.source_preflight import (
    SourceManifestError,
    build_source_preflight_report,
    load_source_manifest,
    parse_source_manifest,
    validate_manifest_source_contract,
)

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "food_source_preflight"
_SCRIPT = Path(__file__).parents[1] / "scripts" / "food_source_preflight.py"
_CATALOG = (
    Path(__file__).parents[1]
    / "docs"
    / "architecture"
    / "FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json"
)
_ONBOARDING = (
    Path(__file__).parents[1]
    / "docs"
    / "architecture"
    / "FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json"
)
_USDA_MANIFEST_PAIRS = (
    ("current_usda_foundation_manifest.json", "incoming_usda_foundation_manifest.json"),
    ("current_usda_branded_manifest.json", "incoming_usda_branded_manifest.json"),
    ("current_usda_fndds_manifest.json", "incoming_usda_fndds_manifest.json"),
)
_USDA_CURRENT_RELEASE_VERSIONS = {
    "usda_foundation": "fdc-foundation-2026-04",
    "usda_branded": "fdc-branded-2026-04",
    "usda_fndds": "fdc-fndds-2021-2023-2024-10",
}
_OFF_MANIFEST_PAIRS = (
    ("current_off_manifest.json", "incoming_off_manifest.json"),
    ("current_off_manifest.json", "incoming_off_delta_manifest.json"),
)


def _fixture(name: str) -> Path:
    return _FIXTURE_DIR / name


def _write_onboarding_variant(
    tmp_path: Path,
    *,
    top_level_flag: str | None = None,
    top_level_value: object | None = None,
    off_field: str | None = None,
    off_value: object | None = None,
) -> Path:
    payload = json.loads(_ONBOARDING.read_text(encoding="utf-8"))
    if top_level_flag is not None:
        payload[top_level_flag] = top_level_value
    if off_field is not None:
        found_off_entry = False
        for entry in payload["sources"]:
            if entry["source"] == "open_food_facts":
                entry[off_field] = off_value
                found_off_entry = True
                break
        if not found_off_entry:
            raise AssertionError("open_food_facts onboarding entry is missing")
    path = tmp_path / "onboarding_variant.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _valid_manifest_payload() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(_fixture("incoming_off_manifest.json").read_text(encoding="utf-8")),
    )


def _set_payload_value(payload: dict[str, object], key: str, value: object) -> None:
    payload[key] = value


def _set_nested_payload_value(
    payload: dict[str, object],
    section: str,
    key: str,
    value: object,
) -> None:
    nested = payload[section]
    assert isinstance(nested, dict)
    nested[key] = value


def _valid_catalog_entry(
    *,
    source_url: str = "https://world.openfoodfacts.org/data",
    active_update_source: bool = True,
    manifest_required: bool = True,
    preflight_required: bool = True,
) -> SourceCatalogEntry:
    return SourceCatalogEntry(
        source="open_food_facts",
        source_classification="current",
        source_family="barcode_branded",
        status="candidate",
        source_url=source_url,
        license_review="odbl_obligations",
        active_update_source=active_update_source,
        manifest_required=manifest_required,
        preflight_required=preflight_required,
        replacement_required=False,
        replacement_for=None,
        notes="Open Food Facts reviewed snapshot.",
    )


def _catalog_with_entry(entry: SourceCatalogEntry) -> SourceCatalog:
    return SourceCatalog(
        schema_version="food-source-catalog.v1",
        generated_on=date(2026, 4, 24),
        runtime_cutover=False,
        digitalocean_postgres_load=False,
        bulk_ingest=False,
        sources=(entry,),
    )


def _valid_onboarding_entry(
    *,
    onboarding_status: OnboardingStatus = "eligible_preflight",
    ingestion_path: IngestionPath = "manifest_preflight_only",
) -> SourceOnboardingEntry:
    return SourceOnboardingEntry(
        source="open_food_facts",
        source_classification="current",
        source_family="barcode_branded",
        onboarding_status=onboarding_status,
        ingestion_path=ingestion_path,
        cache_decision="allowed_reviewed_snapshot",
        redistribution_decision="odbl_obligations_required",
        display_decision="allowed_with_attribution",
        attribution_required=True,
        commercial_risk="medium",
        provider_policy_ref="docs/legal/OPEN_FOOD_FACTS_ODBL_POLICY.md",
        source_specific_policy_required=True,
        notes="Eligible for file-only manifest preflight.",
    )


def _onboarding_with_entry(
    entry: SourceOnboardingEntry,
    *,
    runtime_cutover: bool = False,
    digitalocean_postgres_load: bool = False,
    bulk_ingest: bool = False,
    file_only: bool = True,
    network_allowed: bool = False,
    db_writes_allowed: bool = False,
) -> SourceOnboarding:
    return SourceOnboarding(
        schema_version="food-source-onboarding.v1",
        generated_on=date(2026, 4, 28),
        catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        runtime_cutover=runtime_cutover,
        digitalocean_postgres_load=digitalocean_postgres_load,
        bulk_ingest=bulk_ingest,
        file_only=file_only,
        network_allowed=network_allowed,
        db_writes_allowed=db_writes_allowed,
        sources=(entry,),
    )


def test_load_source_manifest_accepts_current_source_classification() -> None:
    manifest = load_source_manifest(_fixture("current_off_manifest.json"))

    assert manifest.source == "open_food_facts"
    assert manifest.source_classification == "current"
    assert manifest.artifact.checksum_sha256 == "a" * 64
    assert manifest.schema.primary_keys == ("code",)
    assert manifest.collision_policy.dedupe_fields == ("code",)
    assert manifest.collision_policy.mapping_fields == ("code", "product_name", "brands")
    assert manifest.collision_policy.collision_resolution == "quarantine"


@pytest.mark.parametrize("current_fixture,incoming_fixture", _OFF_MANIFEST_PAIRS)
def test_load_source_manifest_accepts_off_current_fixtures(
    current_fixture: str,
    incoming_fixture: str,
) -> None:
    current = load_source_manifest(_fixture(current_fixture))
    incoming = load_source_manifest(_fixture(incoming_fixture))

    assert current.source == incoming.source == "open_food_facts"
    assert incoming.source_classification == "current"
    assert incoming.source_url == "https://world.openfoodfacts.org/data"
    assert incoming.schema.primary_keys == ("code",)
    assert incoming.collision_policy.dedupe_fields == ("code",)
    assert incoming.collision_policy.collision_resolution == "quarantine"


def test_load_source_manifest_accepts_legacy_static_menustat() -> None:
    manifest = load_source_manifest(_fixture("legacy_menustat_manifest.json"))

    assert manifest.source == "menustat"
    assert manifest.source_classification == "legacy_static"
    assert manifest.source_version == "2022"
    assert manifest.collision_policy.collision_resolution == "quarantine"


def test_parse_source_manifest_accepts_skip_collision_resolution() -> None:
    payload = _valid_manifest_payload()
    collision_policy = payload["collision_policy"]
    assert isinstance(collision_policy, dict)
    collision_policy["collision_resolution"] = "skip"

    manifest = parse_source_manifest(payload)

    assert manifest.collision_policy.collision_resolution == "skip"


@pytest.mark.parametrize(
    ("payload", "expected_error"),
    (
        (["not-a-mapping"], "must be an object"),
        ({1: "non-string-key"}, "all object keys must be strings"),
    ),
)
def test_parse_source_manifest_rejects_non_object_payloads(
    payload: object,
    expected_error: str,
) -> None:
    with pytest.raises(SourceManifestError, match=expected_error):
        parse_source_manifest(payload)


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    (
        (
            lambda payload: _set_payload_value(payload, "source", " "),
            "missing non-empty string 'source'",
        ),
        (
            lambda payload: _set_payload_value(payload, "source_url", "ftp://example.test/data"),
            "http",
        ),
        (
            lambda payload: _set_payload_value(payload, "retrieved_on", "2026-02-31"),
            "YYYY-MM-DD",
        ),
        (
            lambda payload: _set_nested_payload_value(payload, "schema", "fields", "code"),
            "list of strings",
        ),
        (
            lambda payload: _set_nested_payload_value(
                payload,
                "schema",
                "fields",
                ["code", "code"],
            ),
            "duplicate",
        ),
        (
            lambda payload: _set_nested_payload_value(payload, "schema", "fields", []),
            "must not be empty",
        ),
        (
            lambda payload: _set_nested_payload_value(
                payload,
                "artifact",
                "checksum_sha256",
                "not-a-sha",
            ),
            "64 hex chars",
        ),
        (
            lambda payload: _set_nested_payload_value(payload, "artifact", "record_count", True),
            "non-negative int",
        ),
        (
            lambda payload: _set_nested_payload_value(
                payload,
                "collision_policy",
                "collision_resolution",
                "merge",
            ),
            "collision_resolution must be one of",
        ),
        (
            lambda payload: _set_nested_payload_value(
                payload,
                "collision_policy",
                "mapping_fields",
                ["missing_schema_field"],
            ),
            "mapping_fields must reference schema fields",
        ),
    ),
)
def test_parse_source_manifest_rejects_malformed_fields(
    mutation: Callable[[dict[str, object]], None],
    expected_error: str,
) -> None:
    payload = _valid_manifest_payload()
    mutation(payload)

    with pytest.raises(SourceManifestError, match=expected_error):
        parse_source_manifest(payload)


@pytest.mark.parametrize("current_fixture,incoming_fixture", _USDA_MANIFEST_PAIRS)
def test_load_source_manifest_accepts_usda_current_fixtures(
    current_fixture: str,
    incoming_fixture: str,
) -> None:
    current = load_source_manifest(_fixture(current_fixture))
    incoming = load_source_manifest(_fixture(incoming_fixture))

    assert current.source == incoming.source
    assert current.source.startswith("usda_")
    assert incoming.source_classification == "current"
    assert incoming.source_url == "https://fdc.nal.usda.gov/download-datasets"
    assert incoming.source_version == _USDA_CURRENT_RELEASE_VERSIONS[incoming.source]
    assert incoming.schema.primary_keys == ("fdc_id",)
    assert "data_type" in incoming.schema.fields
    if incoming.source == "usda_branded":
        assert {"gtin_upc", "brand_owner"}.issubset(incoming.schema.fields)


@pytest.mark.parametrize("current_fixture,incoming_fixture", _USDA_MANIFEST_PAIRS)
def test_build_source_preflight_report_accepts_usda_dry_run_pairs(
    current_fixture: str,
    incoming_fixture: str,
) -> None:
    report = build_source_preflight_report(
        _fixture(current_fixture),
        _fixture(incoming_fixture),
    )

    assert report["success"] is True
    assert report["dry_run"] is True
    assert report["runtime_cutover"] is False
    assert report["source_classification"] == "current"
    assert report["source_url"] == "https://fdc.nal.usda.gov/download-datasets"
    row_count = report["row_count"]
    checksum = report["checksum"]
    assert isinstance(row_count, dict)
    assert isinstance(checksum, dict)
    assert row_count["changed"] is True
    assert checksum["changed"] is True


@pytest.mark.parametrize("_,incoming_fixture", _USDA_MANIFEST_PAIRS)
def test_validate_manifest_source_contract_accepts_usda_onboarding_gate(
    _: str,
    incoming_fixture: str,
) -> None:
    manifest = load_source_manifest(_fixture(incoming_fixture))

    errors = validate_manifest_source_contract(
        manifest,
        catalog_path=_CATALOG,
        onboarding_path=_ONBOARDING,
    )

    assert errors == []


@pytest.mark.parametrize("_,incoming_fixture", _OFF_MANIFEST_PAIRS)
def test_validate_manifest_source_contract_accepts_off_onboarding_gate(
    _: str,
    incoming_fixture: str,
) -> None:
    manifest = load_source_manifest(_fixture(incoming_fixture))

    errors = validate_manifest_source_contract(
        manifest,
        catalog_path=_CATALOG,
        onboarding_path=_ONBOARDING,
    )

    assert errors == []


def test_validate_manifest_source_contract_rejects_unknown_source(tmp_path: Path) -> None:
    payload = json.loads(_fixture("incoming_usda_foundation_manifest.json").read_text())
    payload["source"] = "usda_unknown"
    manifest_path = tmp_path / "unknown_usda_manifest.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    manifest = load_source_manifest(manifest_path)

    errors = validate_manifest_source_contract(
        manifest,
        catalog_path=_CATALOG,
        onboarding_path=_ONBOARDING,
    )

    assert errors == [
        "catalog: unknown source 'usda_unknown'",
        "onboarding: missing source 'usda_unknown'",
    ]


def test_validate_manifest_source_contract_rejects_classification_mismatch(
    tmp_path: Path,
) -> None:
    payload = json.loads(_fixture("incoming_usda_foundation_manifest.json").read_text())
    payload["source_classification"] = "legacy_static"
    manifest_path = tmp_path / "classification_mismatch_manifest.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    manifest = load_source_manifest(manifest_path)

    errors = validate_manifest_source_contract(
        manifest,
        catalog_path=_CATALOG,
        onboarding_path=_ONBOARDING,
    )

    assert errors == [
        "catalog: source_classification mismatch for 'usda_foundation': "
        "manifest='legacy_static' catalog='current'"
    ]


def test_validate_manifest_source_contract_surfaces_catalog_loader_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = load_source_manifest(_fixture("incoming_off_manifest.json"))

    def raise_catalog_error(path: Path | str) -> SourceCatalog:
        raise SourceCatalogError(f"broken catalog {path}")

    monkeypatch.setattr(
        "core.food_sources.source_catalog.load_source_catalog",
        raise_catalog_error,
    )

    errors = validate_manifest_source_contract(
        manifest,
        catalog_path=_CATALOG,
        onboarding_path=_ONBOARDING,
    )

    assert errors == [f"catalog: broken catalog {_CATALOG}"]


def test_validate_manifest_source_contract_surfaces_onboarding_loader_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = load_source_manifest(_fixture("incoming_off_manifest.json"))

    def load_catalog(path: Path | str) -> SourceCatalog:
        return _catalog_with_entry(_valid_catalog_entry())

    def raise_onboarding_error(
        path: Path | str,
        *,
        catalog: SourceCatalog,
        expected_catalog_ref: str,
    ) -> SourceOnboarding:
        assert catalog.sources[0].source == "open_food_facts"
        assert expected_catalog_ref.endswith("FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json")
        raise SourceOnboardingError(f"broken onboarding {path}")

    monkeypatch.setattr("core.food_sources.source_catalog.load_source_catalog", load_catalog)
    monkeypatch.setattr(
        "core.food_sources.source_onboarding.load_source_onboarding",
        raise_onboarding_error,
    )

    errors = validate_manifest_source_contract(
        manifest,
        catalog_path=_CATALOG,
        onboarding_path=_ONBOARDING,
    )

    assert errors == [f"onboarding: broken onboarding {_ONBOARDING}"]


def test_validate_manifest_source_contract_rejects_catalog_gate_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = load_source_manifest(_fixture("incoming_off_manifest.json"))
    catalog_entry = _valid_catalog_entry(
        source_url="https://example.test/off",
        manifest_required=False,
        preflight_required=False,
        active_update_source=False,
    )

    monkeypatch.setattr(
        "core.food_sources.source_catalog.load_source_catalog",
        lambda path: _catalog_with_entry(catalog_entry),
    )
    monkeypatch.setattr(
        "core.food_sources.source_onboarding.load_source_onboarding",
        lambda path, *, catalog, expected_catalog_ref: _onboarding_with_entry(
            _valid_onboarding_entry(),
        ),
    )

    errors = validate_manifest_source_contract(
        manifest,
        catalog_path=_CATALOG,
        onboarding_path=_ONBOARDING,
    )

    assert errors == [
        "catalog: source_url mismatch for 'open_food_facts': "
        "manifest='https://world.openfoodfacts.org/data' catalog='https://example.test/off'",
        "catalog: 'open_food_facts' must require a manifest",
        "catalog: 'open_food_facts' must require preflight",
        "catalog: 'open_food_facts' must be an active update source",
    ]


def test_validate_manifest_source_contract_rejects_onboarding_gate_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = load_source_manifest(_fixture("incoming_off_manifest.json"))
    onboarding_entry = _valid_onboarding_entry(
        onboarding_status="legacy_baseline_blocked",
        ingestion_path="legacy_snapshot_review_only",
    )

    monkeypatch.setattr(
        "core.food_sources.source_catalog.load_source_catalog",
        lambda path: _catalog_with_entry(_valid_catalog_entry()),
    )
    monkeypatch.setattr(
        "core.food_sources.source_onboarding.load_source_onboarding",
        lambda path, *, catalog, expected_catalog_ref: _onboarding_with_entry(
            onboarding_entry,
            runtime_cutover=True,
            digitalocean_postgres_load=True,
            bulk_ingest=True,
            file_only=False,
            network_allowed=True,
            db_writes_allowed=True,
        ),
    )

    errors = validate_manifest_source_contract(
        manifest,
        catalog_path=tmp_path / "catalog-outside-repo.json",
        onboarding_path=_ONBOARDING,
    )

    assert errors == [
        "onboarding: 'open_food_facts' must be eligible_preflight, "
        "got 'legacy_baseline_blocked'",
        "onboarding: 'open_food_facts' must use manifest_preflight_only, "
        "got 'legacy_snapshot_review_only'",
        "onboarding: runtime_cutover must remain false",
        "onboarding: digitalocean_postgres_load must remain false",
        "onboarding: bulk_ingest must remain false",
        "onboarding: file_only must remain true",
        "onboarding: network_allowed must remain false",
        "onboarding: db_writes_allowed must remain false",
    ]


def test_build_source_preflight_report_enforces_strict_source_contract(
    tmp_path: Path,
) -> None:
    payload = json.loads(_fixture("incoming_usda_foundation_manifest.json").read_text())
    payload["source"] = "usda_unknown"
    incoming_manifest = tmp_path / "incoming_unknown_usda_manifest.json"
    incoming_manifest.write_text(json.dumps(payload), encoding="utf-8")

    report = build_source_preflight_report(
        _fixture("current_usda_foundation_manifest.json"),
        incoming_manifest,
        catalog_path=_CATALOG,
        onboarding_path=_ONBOARDING,
    )

    assert report["success"] is False
    assert report["runtime_cutover"] is False
    assert report["validation_errors"] == [
        "source mismatch: current='usda_foundation' incoming='usda_unknown'",
        "source_contract: catalog: unknown source 'usda_unknown'",
        "source_contract: onboarding: missing source 'usda_unknown'",
    ]


def test_build_source_preflight_report_requires_catalog_and_onboarding_together() -> None:
    report = build_source_preflight_report(
        _fixture("current_off_manifest.json"),
        _fixture("incoming_off_manifest.json"),
        catalog_path=_CATALOG,
    )

    assert report["success"] is False
    assert report["validation_errors"] == [
        "source_contract: catalog_path and onboarding_path must be provided together"
    ]


def test_build_source_preflight_report_surfaces_unreadable_manifests(tmp_path: Path) -> None:
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{not json", encoding="utf-8")
    missing_manifest = tmp_path / "missing.json"

    report = build_source_preflight_report(missing_manifest, invalid_json)

    assert report["success"] is False
    assert report["dry_run"] is True
    assert report["runtime_cutover"] is False
    errors = report["validation_errors"]
    assert isinstance(errors, list)
    assert str(missing_manifest) in str(errors[0])
    assert str(invalid_json) in str(errors[1])


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


def test_load_source_manifest_rejects_collision_fields_outside_schema(tmp_path: Path) -> None:
    manifest_path = tmp_path / "bad_collision.json"
    manifest_path.write_text(
        json.dumps(
            {
                "artifact": {
                    "checksum_sha256": "e" * 64,
                    "path": "raw/off/faulty.csv",
                    "record_count": 1,
                    "size_bytes": 1,
                },
                "collision_policy": {
                    "dedupe_fields": ["missing_pk"],
                    "mapping_fields": ["missing_pk"],
                    "collision_resolution": "reject",
                },
                "retrieved_on": "2026-04-24",
                "schema": {"fields": ["code"], "primary_keys": ["code"]},
                "source": "open_food_facts",
                "source_classification": "current",
                "source_url": "https://world.openfoodfacts.org/data",
                "source_version": "2026-04-24",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SourceManifestError, match="must reference schema fields"):
        load_source_manifest(manifest_path)


def test_load_source_manifest_rejects_compact_retrieved_on_date(tmp_path: Path) -> None:
    manifest_path = tmp_path / "bad_date.json"
    manifest_path.write_text(
        json.dumps(
            {
                "artifact": {
                    "checksum_sha256": "f" * 64,
                    "path": "raw/off/products.csv.gz",
                    "record_count": 1,
                    "size_bytes": 1,
                },
                "retrieved_on": "20260424",
                "schema": {"fields": ["code"], "primary_keys": ["code"]},
                "source": "open_food_facts",
                "source_classification": "current",
                "source_url": "https://world.openfoodfacts.org/data",
                "source_version": "2026-04-24",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SourceManifestError, match="retrieved_on must use YYYY-MM-DD"):
        load_source_manifest(manifest_path)


def test_build_source_preflight_report_diff_contract() -> None:
    report = build_source_preflight_report(
        _fixture("current_off_manifest.json"),
        _fixture("incoming_off_manifest.json"),
    )

    assert report["success"] is True
    assert report["dry_run"] is True
    assert report["runtime_cutover"] is False
    assert report["source"] == {
        "current": "open_food_facts",
        "incoming": "open_food_facts",
        "changed": False,
    }
    assert report["source_classification"] == "current"
    assert report["version"] == {
        "current": "2026-04-29",
        "incoming": "2026-04-30",
        "changed": True,
    }
    assert report["checksum"] == {
        "current": "a" * 64,
        "incoming": "b" * 64,
        "changed": True,
    }
    assert report["row_count"] == {
        "current": 100000,
        "incoming": 101500,
        "delta": 1500,
        "changed": True,
    }
    assert report["schema"] == {"added": ["nutriscore_grade", "quantity"], "removed": []}
    assert report["primary_keys"] == {"added": [], "removed": []}
    assert report["collision_policy"] == {
        "dedupe_fields": {"added": [], "removed": []},
        "mapping_fields": {"added": [], "removed": []},
        "collision_resolution": {
            "changed": False,
            "current": "quarantine",
            "incoming": "quarantine",
        },
    }


@pytest.mark.parametrize("current_fixture,incoming_fixture", _OFF_MANIFEST_PAIRS)
def test_build_source_preflight_report_accepts_off_dry_run_pairs(
    current_fixture: str,
    incoming_fixture: str,
) -> None:
    report = build_source_preflight_report(
        _fixture(current_fixture),
        _fixture(incoming_fixture),
        catalog_path=_CATALOG,
        onboarding_path=_ONBOARDING,
    )

    assert report["success"] is True
    assert report["dry_run"] is True
    assert report["runtime_cutover"] is False
    assert report["source_classification"] == "current"
    assert report["source_url"] == "https://world.openfoodfacts.org/data"
    assert report["validation_errors"] == []
    row_count = report["row_count"]
    checksum = report["checksum"]
    assert isinstance(row_count, dict)
    assert isinstance(checksum, dict)
    assert row_count["changed"] is True
    assert checksum["changed"] is True


@pytest.mark.parametrize(
    ("flag", "value"),
    (
        ("network_allowed", True),
        ("db_writes_allowed", True),
        ("digitalocean_postgres_load", True),
        ("runtime_cutover", True),
    ),
)
def test_validate_manifest_source_contract_rejects_off_unsafe_safety_flags(
    tmp_path: Path,
    flag: str,
    value: object,
) -> None:
    onboarding = _write_onboarding_variant(
        tmp_path,
        top_level_flag=flag,
        top_level_value=value,
    )
    manifest = load_source_manifest(_fixture("incoming_off_manifest.json"))

    errors = validate_manifest_source_contract(
        manifest,
        catalog_path=_CATALOG,
        onboarding_path=onboarding,
    )

    assert len(errors) == 1
    assert errors[0].startswith("onboarding: Invalid source onboarding ")
    assert (
        "runtime_cutover, digitalocean_postgres_load, bulk_ingest, "
        "network_allowed, and db_writes_allowed must be false; file_only must be true"
    ) in errors[0]


def test_validate_manifest_source_contract_rejects_off_odbl_policy_drift(
    tmp_path: Path,
) -> None:
    onboarding = _write_onboarding_variant(
        tmp_path,
        off_field="provider_policy_ref",
        off_value=None,
    )
    manifest = load_source_manifest(_fixture("incoming_off_manifest.json"))

    errors = validate_manifest_source_contract(
        manifest,
        catalog_path=_CATALOG,
        onboarding_path=onboarding,
    )

    assert errors == [
        "onboarding: Invalid source onboarding "
        f"{onboarding}: policy mismatch for open_food_facts: provider_policy_ref"
    ]


def test_build_source_preflight_report_surfaces_validation_errors() -> None:
    report = build_source_preflight_report(
        _fixture("current_off_manifest.json"),
        _fixture("invalid_classification_manifest.json"),
    )

    assert report["success"] is False
    assert report["runtime_cutover"] is False
    assert report["dry_run"] is True
    assert "source_classification must be one of" in str(report["validation_errors"])


def test_build_source_preflight_report_surfaces_collision_policy_drift() -> None:
    report = build_source_preflight_report(
        _fixture("current_off_manifest.json"),
        _fixture("collision_policy_drift_manifest.json"),
    )

    assert report["collision_policy"] == {
        "dedupe_fields": {"added": ["product_name"], "removed": []},
        "mapping_fields": {"added": [], "removed": ["brands", "product_name"]},
        "collision_resolution": {"changed": True, "current": "quarantine", "incoming": "reject"},
    }


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
        cwd=tmp_path,
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


@pytest.mark.parametrize("current_fixture,incoming_fixture", _OFF_MANIFEST_PAIRS)
def test_food_source_preflight_cli_accepts_off_fixture_pair_with_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    current_fixture: str,
    incoming_fixture: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://must-not-be-used.invalid/db")
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--current-manifest",
            str(_fixture(current_fixture)),
            "--incoming-manifest",
            str(_fixture(incoming_fixture)),
            "--dry-run",
            "--json",
            "--catalog",
            str(_CATALOG),
            "--onboarding",
            str(_ONBOARDING),
        ],
        cwd=tmp_path,
        check=True,
        text=True,
        capture_output=True,
    )
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["runtime_cutover"] is False
    assert payload["source"]["incoming"] == "open_food_facts"
    assert payload["validation_errors"] == []
    assert result.stderr == ""
    assert after == before


def test_food_source_preflight_cli_accepts_usda_fixture_pair(
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
            str(_fixture("current_usda_foundation_manifest.json")),
            "--incoming-manifest",
            str(_fixture("incoming_usda_foundation_manifest.json")),
            "--dry-run",
            "--json",
            "--catalog",
            str(_CATALOG),
            "--onboarding",
            str(_ONBOARDING),
        ],
        cwd=tmp_path,
        check=True,
        text=True,
        capture_output=True,
    )
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["runtime_cutover"] is False
    assert payload["source"]["incoming"] == "usda_foundation"
    assert payload["validation_errors"] == []
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
