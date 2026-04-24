"""Tests for the deterministic food source catalog contract."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

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
    assert catalog.runtime_cutover is False
    assert catalog.digitalocean_postgres_load is False
    assert catalog.bulk_ingest is False
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


def test_food_source_catalog_rejects_runtime_cutover_flag() -> None:
    payload = _catalog_payload()
    payload["runtime_cutover"] = True

    with pytest.raises(SourceCatalogError, match="must be false"):
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
