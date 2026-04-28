"""Tests for the deterministic food source onboarding gate."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources import source_onboarding
from core.food_sources.source_catalog import load_source_catalog
from core.food_sources.source_catalog import parse_source_catalog
from core.food_sources.source_onboarding import (
    SourceOnboardingError,
    build_source_onboarding_report,
    load_source_onboarding,
    parse_source_onboarding,
)

_REPO_ROOT = Path(__file__).parents[1]
_CATALOG_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json"
)
_ONBOARDING_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json"
)
_SCRIPT = _REPO_ROOT / "scripts" / "food_source_onboarding.py"


def _catalog():
    return load_source_catalog(_CATALOG_PATH)


def _onboarding_payload() -> dict[str, object]:
    return json.loads(_ONBOARDING_PATH.read_text(encoding="utf-8"))


def _mutate_source(
    payload: dict[str, object],
    source_name: str,
    key: str,
    value: object,
) -> dict[str, object]:
    updated = copy.deepcopy(payload)
    sources = updated["sources"]
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == source_name:
            source[key] = value
            break
    return updated


def test_food_source_onboarding_accepts_pr5_contract() -> None:
    onboarding = load_source_onboarding(_ONBOARDING_PATH, catalog=_catalog())

    sources = {entry.source: entry for entry in onboarding.sources}
    assert onboarding.runtime_cutover is False
    assert onboarding.digitalocean_postgres_load is False
    assert onboarding.bulk_ingest is False
    assert onboarding.file_only is True
    assert onboarding.network_allowed is False
    assert onboarding.db_writes_allowed is False
    assert sources["open_food_facts"].provider_policy_ref == "docs/legal/ODbL_COMPLIANCE.md"
    assert sources["open_food_facts"].redistribution_decision == "odbl_obligations_required"
    assert sources["menustat"].onboarding_status == "legacy_baseline_blocked"
    assert sources["nutritionix"].onboarding_status == "contract_review_blocked"
    assert sources["jptn_food_facts"].onboarding_status == "unresolved_blocked"


@pytest.mark.parametrize(
    ("flag_name", "flag_value"),
    (
        ("runtime_cutover", True),
        ("digitalocean_postgres_load", True),
        ("bulk_ingest", True),
        ("file_only", False),
        ("network_allowed", True),
        ("db_writes_allowed", True),
    ),
)
def test_food_source_onboarding_rejects_unsafe_flags(
    flag_name: str,
    flag_value: bool,
) -> None:
    payload = _onboarding_payload()
    payload[flag_name] = flag_value

    with pytest.raises(SourceOnboardingError, match="must be false; file_only must be true"):
        parse_source_onboarding(payload, catalog=_catalog())


def test_food_source_onboarding_rejects_missing_catalog_source() -> None:
    payload = _onboarding_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    payload["sources"] = [
        source
        for source in sources
        if not (isinstance(source, dict) and source.get("source") == "regional_catalogs")
    ]

    with pytest.raises(SourceOnboardingError, match="missing catalog sources"):
        parse_source_onboarding(payload, catalog=_catalog())


def test_food_source_onboarding_rejects_unknown_source() -> None:
    payload = _onboarding_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    unknown = copy.deepcopy(sources[0])
    assert isinstance(unknown, dict)
    unknown["source"] = "unknown_food_source"
    sources.append(unknown)

    with pytest.raises(SourceOnboardingError, match="unknown onboarding sources"):
        parse_source_onboarding(payload, catalog=_catalog())


def test_food_source_onboarding_rejects_duplicate_source() -> None:
    payload = _onboarding_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    sources.append(copy.deepcopy(sources[0]))

    with pytest.raises(SourceOnboardingError, match="duplicate sources"):
        parse_source_onboarding(payload, catalog=_catalog())


def test_food_source_onboarding_rejects_catalog_classification_drift() -> None:
    payload = _mutate_source(
        _onboarding_payload(),
        "open_food_facts",
        "source_classification",
        "commercial_contract",
    )

    with pytest.raises(SourceOnboardingError, match="source_classification must match catalog"):
        parse_source_onboarding(payload, catalog=_catalog())


def test_food_source_onboarding_rejects_catalog_ref_mismatch() -> None:
    payload = _onboarding_payload()
    payload["catalog_ref"] = "docs/architecture/stale-catalog.json"

    with pytest.raises(SourceOnboardingError, match="catalog_ref must be"):
        parse_source_onboarding(
            payload,
            catalog=_catalog(),
            expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        )


def test_food_source_onboarding_rejects_generic_legacy_static_without_replacement_gate() -> None:
    catalog_payload = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    catalog_sources = catalog_payload["sources"]
    assert isinstance(catalog_sources, list)
    extra_catalog_source = copy.deepcopy(catalog_sources[4])
    assert isinstance(extra_catalog_source, dict)
    extra_catalog_source["source"] = "legacy_restaurant_archive"
    extra_catalog_source["replacement_required"] = False
    catalog_sources.append(extra_catalog_source)
    catalog = parse_source_catalog(catalog_payload)

    onboarding_payload = _onboarding_payload()
    onboarding_sources = onboarding_payload["sources"]
    assert isinstance(onboarding_sources, list)
    unsafe_onboarding = copy.deepcopy(onboarding_sources[4])
    assert isinstance(unsafe_onboarding, dict)
    unsafe_onboarding["source"] = "legacy_restaurant_archive"
    onboarding_sources.append(unsafe_onboarding)

    with pytest.raises(
        SourceOnboardingError,
        match="legacy_static sources must remain replacement_required",
    ):
        parse_source_onboarding(onboarding_payload, catalog=catalog)


def test_food_source_onboarding_rejects_missing_off_odbl_policy() -> None:
    payload = _mutate_source(
        _onboarding_payload(),
        "open_food_facts",
        "provider_policy_ref",
        None,
    )

    with pytest.raises(SourceOnboardingError, match="policy mismatch for open_food_facts"):
        parse_source_onboarding(payload, catalog=_catalog())


def test_food_source_onboarding_rejects_commercial_contractless_cache() -> None:
    payload = _mutate_source(
        _onboarding_payload(),
        "nutritionix",
        "cache_decision",
        "allowed_reviewed_snapshot",
    )

    with pytest.raises(SourceOnboardingError, match="policy mismatch for nutritionix"):
        parse_source_onboarding(payload, catalog=_catalog())


def test_food_source_onboarding_rejects_unresolved_activation() -> None:
    payload = _mutate_source(
        _onboarding_payload(),
        "jptn_food_facts",
        "onboarding_status",
        "eligible_preflight",
    )

    with pytest.raises(SourceOnboardingError, match="policy mismatch for jptn_food_facts"):
        parse_source_onboarding(payload, catalog=_catalog())


def test_food_source_onboarding_rejects_menustat_fresh_update() -> None:
    payload = _mutate_source(
        _onboarding_payload(),
        "menustat",
        "onboarding_status",
        "eligible_preflight",
    )

    with pytest.raises(SourceOnboardingError, match="policy mismatch for menustat"):
        parse_source_onboarding(payload, catalog=_catalog())


def test_build_source_onboarding_report_is_deterministic_json_contract() -> None:
    report = build_source_onboarding_report(_CATALOG_PATH, _ONBOARDING_PATH)

    assert report == {
        "success": True,
        "dry_run": True,
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "file_only": True,
        "network_allowed": False,
        "db_writes_allowed": False,
        "catalog_ref": "docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        "source_count": 12,
        "blocked_sources": [
            "chain_public_nutrition_pages",
            "edamam_food_database",
            "fatsecret_platform",
            "jptn_food_facts",
            "menustat",
            "nutritionix",
            "regional_catalogs",
            "spoonacular",
        ],
        "eligible_preflight_sources": [
            "open_food_facts",
            "usda_branded",
            "usda_fndds",
            "usda_foundation",
        ],
        "validation_errors": [],
    }


def test_food_source_onboarding_cli_is_file_only_and_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://must-not-be-used.invalid/db")
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--catalog",
            str(_CATALOG_PATH),
            "--onboarding",
            str(_ONBOARDING_PATH),
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
    assert payload["network_allowed"] is False
    assert payload["db_writes_allowed"] is False
    assert result.stderr == ""
    assert after == before


def test_food_source_onboarding_cli_returns_nonzero_for_invalid_payload(
    tmp_path: Path,
) -> None:
    bad_path = tmp_path / "bad_onboarding.json"
    payload = _onboarding_payload()
    payload["network_allowed"] = True
    bad_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--catalog",
            str(_CATALOG_PATH),
            "--onboarding",
            str(bad_path),
            "--json",
        ],
        cwd=tmp_path,
        check=False,
        text=True,
        capture_output=True,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["success"] is False
    assert payload["network_allowed"] is False


def test_food_source_onboarding_has_no_network_or_db_dependencies() -> None:
    source_text = Path(source_onboarding.__file__).read_text(encoding="utf-8")
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
