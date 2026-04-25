"""Tests for the deterministic food source catalog contract."""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from core.food_sources import source_catalog
from core.food_sources.source_catalog import (
    SourceCatalogError,
    load_source_catalog,
    parse_source_catalog,
)

_CATALOG_PATH = (
    Path(__file__).parents[1]
    / "docs"
    / "architecture"
    / "FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json"
)


def _catalog_payload() -> dict[str, object]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def test_food_source_catalog_accepts_pr3_contract() -> None:
    catalog = load_source_catalog(_CATALOG_PATH)

    sources = {entry.source: entry for entry in catalog.sources}
    expected_sources = {
        "usda_foundation",
        "usda_branded",
        "usda_fndds",
        "open_food_facts",
        "menustat",
        "nutritionix",
        "fatsecret_platform",
        "spoonacular",
        "edamam_food_database",
        "chain_public_nutrition_pages",
        "jptn_food_facts",
        "regional_catalogs",
    }
    assert catalog.runtime_cutover is False
    assert catalog.digitalocean_postgres_load is False
    assert catalog.bulk_ingest is False
    assert set(sources) == expected_sources
    assert all(entry.manifest_required for entry in catalog.sources)
    assert all(entry.preflight_required for entry in catalog.sources)
    assert sources["open_food_facts"].source_classification == "current"
    assert sources["menustat"].source_classification == "legacy_static"
    assert sources["menustat"].active_update_source is False
    assert sources["jptn_food_facts"].source_classification == "unresolved"
    assert sources["jptn_food_facts"].status == "blocked_unresolved"


def test_food_source_catalog_requires_menustat_replacement_candidates() -> None:
    catalog = load_source_catalog(_CATALOG_PATH)

    replacements = [
        entry.source for entry in catalog.sources if entry.replacement_for == "menustat"
    ]
    assert replacements == [
        "nutritionix",
        "fatsecret_platform",
        "spoonacular",
        "chain_public_nutrition_pages",
    ]


@pytest.mark.parametrize(
    "flag_name",
    ("runtime_cutover", "digitalocean_postgres_load", "bulk_ingest"),
)
def test_food_source_catalog_rejects_safety_flag_cutovers(flag_name: str) -> None:
    payload = _catalog_payload()
    payload[flag_name] = True

    with pytest.raises(SourceCatalogError, match="must be false"):
        parse_source_catalog(payload)


@pytest.mark.parametrize("field_name", ("manifest_required", "preflight_required"))
def test_food_source_catalog_rejects_disabled_preflight_gates(field_name: str) -> None:
    payload = _catalog_payload()
    sources = copy.deepcopy(payload["sources"])
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == "open_food_facts":
            source[field_name] = False
    payload["sources"] = sources

    with pytest.raises(SourceCatalogError, match="must be true"):
        parse_source_catalog(payload)


def test_food_source_catalog_rejects_active_menustat() -> None:
    payload = _catalog_payload()
    sources = copy.deepcopy(payload["sources"])
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == "menustat":
            source["active_update_source"] = True
    payload["sources"] = sources

    with pytest.raises(SourceCatalogError, match="legacy_static sources cannot be active"):
        parse_source_catalog(payload)


def test_food_source_catalog_rejects_duplicate_sources() -> None:
    payload = _catalog_payload()
    sources = copy.deepcopy(payload["sources"])
    assert isinstance(sources, list)
    sources.append(copy.deepcopy(sources[0]))
    payload["sources"] = sources

    with pytest.raises(SourceCatalogError, match="duplicate sources"):
        parse_source_catalog(payload)


def test_food_source_catalog_rejects_unresolved_non_blocked_status() -> None:
    payload = _catalog_payload()
    sources = copy.deepcopy(payload["sources"])
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == "jptn_food_facts":
            source["status"] = "candidate"
    payload["sources"] = sources

    with pytest.raises(SourceCatalogError, match="unresolved sources must use"):
        parse_source_catalog(payload)


def test_food_source_catalog_rejects_unresolved_non_unresolved_review() -> None:
    payload = _catalog_payload()
    sources = copy.deepcopy(payload["sources"])
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == "jptn_food_facts":
            source["license_review"] = "public_review_required"
    payload["sources"] = sources

    with pytest.raises(SourceCatalogError, match="unresolved_required"):
        parse_source_catalog(payload)


def test_food_source_catalog_rejects_commercial_non_contract_review() -> None:
    payload = _catalog_payload()
    sources = copy.deepcopy(payload["sources"])
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == "nutritionix":
            source["license_review"] = "public_review_required"
    payload["sources"] = sources

    with pytest.raises(SourceCatalogError, match="commercial_contract_required"):
        parse_source_catalog(payload)


def test_food_source_catalog_rejects_replacement_self_loop() -> None:
    payload = _catalog_payload()
    sources = copy.deepcopy(payload["sources"])
    assert isinstance(sources, list)
    for source in sources:
        if not isinstance(source, dict):
            continue
        if source.get("source") == "nutritionix":
            source["replacement_for"] = "nutritionix"
    payload["sources"] = sources

    with pytest.raises(SourceCatalogError, match="replacement candidate for itself"):
        parse_source_catalog(payload)


def test_food_source_catalog_rejects_replacement_cycle() -> None:
    payload = _catalog_payload()
    sources = copy.deepcopy(payload["sources"])
    assert isinstance(sources, list)
    for source in sources:
        if not isinstance(source, dict):
            continue
        if source.get("source") == "nutritionix":
            source["replacement_for"] = "fatsecret_platform"
        if source.get("source") == "fatsecret_platform":
            source["replacement_for"] = "nutritionix"
    payload["sources"] = sources

    with pytest.raises(SourceCatalogError, match="replacement_for cycle detected"):
        parse_source_catalog(payload)


def test_food_source_catalog_rejects_invalid_replacement_classification() -> None:
    payload = _catalog_payload()
    sources = copy.deepcopy(payload["sources"])
    assert isinstance(sources, list)
    for source in sources:
        if not isinstance(source, dict):
            continue
        if source.get("source") == "nutritionix":
            source["source_classification"] = "legacy_static"
    payload["sources"] = sources

    with pytest.raises(SourceCatalogError, match="legacy_static sources cannot"):
        parse_source_catalog(payload)


def test_food_source_catalog_rejects_missing_replacement_target() -> None:
    payload = _catalog_payload()
    sources = copy.deepcopy(payload["sources"])
    assert isinstance(sources, list)
    for source in sources:
        if not isinstance(source, dict):
            continue
        if source.get("source") == "nutritionix":
            source["replacement_for"] = "non_existent_source"
    payload["sources"] = sources

    with pytest.raises(SourceCatalogError, match="replacement_for target missing"):
        parse_source_catalog(payload)


def test_food_source_catalog_has_no_runtime_ingest_dependencies() -> None:
    source_text = Path(source_catalog.__file__).read_text(encoding="utf-8")
    syntax_tree = ast.parse(source_text)

    blocked_modules = (
        "requests",
        "httpx",
        "urllib.request",
        "psycopg",
        "sqlalchemy",
        "digitalocean",
        "subprocess",
    )
    imported_modules: set[str] = set()
    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
    assert imported_modules.isdisjoint(blocked_modules)
