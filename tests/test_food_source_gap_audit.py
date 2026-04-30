"""Tests for the deterministic PR11 food coverage/source-gap audit gate."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources import source_gap_audit
from core.food_sources.source_catalog import SourceCatalog, load_source_catalog
from core.food_sources.source_gap_audit import (
    SourceGapAuditError,
    build_source_gap_audit_report,
    load_source_gap_audit,
    parse_source_gap_audit,
)
from core.food_sources.source_onboarding import SourceOnboarding, load_source_onboarding

_REPO_ROOT = Path(__file__).parents[1]
_CATALOG_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json"
)
_ONBOARDING_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json"
)
_AUDIT_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json"
)
_CLI_MODULE = "scripts.food_source_gap_audit"
_FAT_PLATFORM_SOURCE = "fat" + "secret_platform"


def _catalog() -> SourceCatalog:
    return load_source_catalog(_CATALOG_PATH)


def _onboarding() -> SourceOnboarding:
    return load_source_onboarding(
        _ONBOARDING_PATH,
        catalog=_catalog(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
    )


def _audit_payload() -> dict[str, object]:
    return json.loads(_AUDIT_PATH.read_text(encoding="utf-8"))


def _catalog_payload() -> dict[str, object]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _onboarding_payload() -> dict[str, object]:
    return json.loads(_ONBOARDING_PATH.read_text(encoding="utf-8"))


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _domain(payload: dict[str, object], domain_name: str) -> dict[str, object]:
    domains = payload["coverage_domains"]
    assert isinstance(domains, list)
    for domain in domains:
        if isinstance(domain, dict) and domain.get("domain") == domain_name:
            return domain
    raise AssertionError(f"missing coverage domain {domain_name}")


def _source_decision(payload: dict[str, object], source_name: str) -> dict[str, object]:
    decisions = payload["source_gap_decisions"]
    assert isinstance(decisions, list)
    for decision in decisions:
        if isinstance(decision, dict) and decision.get("source") == source_name:
            return decision
    raise AssertionError(f"missing source decision {source_name}")


def _mutate_catalog_source(source_name: str, key: str, value: object, tmp_path: Path) -> Path:
    payload = _catalog_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == source_name:
            source[key] = value
            break
    else:
        raise AssertionError(f"missing catalog source {source_name}")
    return _write_payload(tmp_path / "catalog.json", payload)


def _mutate_onboarding_source(source_name: str, key: str, value: object, tmp_path: Path) -> Path:
    payload = _onboarding_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == source_name:
            source[key] = value
            break
    else:
        raise AssertionError(f"missing onboarding source {source_name}")
    return _write_payload(tmp_path / "onboarding.json", payload)


def test_load_source_gap_audit_accepts_canonical_artifact() -> None:
    audit = load_source_gap_audit(
        _AUDIT_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
    )

    assert audit.pr10_landed_pr == 1597
    assert audit.next_recommended_lane == (
        "chain_public_nutrition_pages_governance_or_recipe_corpus_governance"
    )
    assert [domain.domain for domain in audit.coverage_domains] == [
        "generic_food_composition",
        "branded_barcode_products",
        "restaurant_chain_menus",
        "recipe_dish_corpora",
        "preference_menu_planning",
        "regional_local_products",
        "user_manual_evidence",
    ]
    source_decisions = {row.source: row.decision for row in audit.source_gap_decisions}
    assert source_decisions["open_food_facts"] == "auxiliary_barcode_branded_source"
    assert source_decisions[_FAT_PLATFORM_SOURCE] == "not_project_source"


def test_source_gap_audit_report_is_deterministic_json_contract() -> None:
    report = build_source_gap_audit_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_AUDIT_PATH,
    )

    assert report == {
        "success": True,
        "dry_run": True,
        "coverage_domains": [
            "generic_food_composition",
            "branded_barcode_products",
            "restaurant_chain_menus",
            "recipe_dish_corpora",
            "preference_menu_planning",
            "regional_local_products",
            "user_manual_evidence",
        ],
        "source_gap_decisions": {
            "usda_foundation": "core_authority_for_generic_composition",
            "usda_branded": "primary_branded_barcode_source",
            "usda_fndds": "supporting_food_composition_source",
            "open_food_facts": "auxiliary_barcode_branded_source",
            "menustat": "archival_reference_only",
            "chain_public_nutrition_pages": "preferred_research_lane_blocked",
            "edamam_food_database": "adjacent_recipe_food_db_review_only",
            "spoonacular": "deferred_recipe_experiments_only",
            "nutritionix": "deferred_contract_review",
            _FAT_PLATFORM_SOURCE: "not_project_source",
            "regional_catalogs": "deferred_unresolved",
            "jptn_food_facts": "blocked_unresolved",
        },
        "next_recommended_lane": (
            "chain_public_nutrition_pages_governance_or_recipe_corpus_governance"
        ),
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "network_allowed": False,
        "db_writes_allowed": False,
        "api_calls_allowed": False,
        "source_download_allowed": False,
        "scraping_allowed": False,
        "paid_source_use_allowed": False,
        "file_only": True,
        "final_gate_decision": "coverage_gap_audit_complete_no_ingest",
        "validation_errors": [],
        "catalog_ref": "docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        "onboarding_ref": "docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
        "pr10_landed_pr": 1597,
        "coverage_domain_decisions": {
            "generic_food_composition": "adequate_baseline",
            "branded_barcode_products": "adequate_with_auxiliary",
            "restaurant_chain_menus": "unresolved_gap",
            "recipe_dish_corpora": "unresolved_gap",
            "preference_menu_planning": "requires_dish_mapping",
            "regional_local_products": "deferred_unresolved",
            "user_manual_evidence": "internal_evidence_only",
        },
        "coverage_gap_status": {
            "generic_food_composition": "baseline_covered",
            "branded_barcode_products": "covered_with_schema_review_needed",
            "restaurant_chain_menus": "not_covered_by_usda_or_off",
            "recipe_dish_corpora": "not_covered_by_food_nutrient_sources",
            "preference_menu_planning": "planner_gap_not_source_authority",
            "regional_local_products": "locale_gap_unresolved",
            "user_manual_evidence": "manual_evidence_not_dataset_authority",
        },
    }


@pytest.mark.parametrize(
    "flag_name",
    (
        "runtime_cutover",
        "digitalocean_postgres_load",
        "bulk_ingest",
        "network_allowed",
        "db_writes_allowed",
        "api_calls_allowed",
        "source_download_allowed",
        "scraping_allowed",
        "paid_source_use_allowed",
    ),
)
def test_source_gap_audit_rejects_unsafe_flags(flag_name: str) -> None:
    payload = _audit_payload()
    payload[flag_name] = True

    with pytest.raises(SourceGapAuditError, match="must be false; file_only must be true"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_rejects_missing_domain() -> None:
    payload = _audit_payload()
    domains = payload["coverage_domains"]
    assert isinstance(domains, list)
    domains.pop()

    with pytest.raises(SourceGapAuditError, match="coverage_domains must be exactly"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_rejects_duplicate_domain() -> None:
    payload = _audit_payload()
    domains = payload["coverage_domains"]
    assert isinstance(domains, list)
    domains[-1] = copy.deepcopy(domains[0])

    with pytest.raises(SourceGapAuditError, match="coverage_domains must be exactly"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_rejects_unknown_domain() -> None:
    payload = _audit_payload()
    _domain(payload, "restaurant_chain_menus")["domain"] = "social_media_restaurant_feeds"

    with pytest.raises(SourceGapAuditError, match="unknown coverage domain"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_rejects_domain_ingest_approval() -> None:
    payload = _audit_payload()
    _domain(payload, "restaurant_chain_menus")["approved_ingest"] = True

    with pytest.raises(SourceGapAuditError, match="cannot approve ingest"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_rejects_off_as_primary_authority() -> None:
    payload = _audit_payload()
    _domain(payload, "branded_barcode_products")["authority_decision"] = "off_primary"

    with pytest.raises(SourceGapAuditError, match="branded_barcode_products decision mismatch"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_rejects_source_gap_approval() -> None:
    payload = _audit_payload()
    _source_decision(payload, "chain_public_nutrition_pages")["scraping_allowed"] = True

    with pytest.raises(SourceGapAuditError, match="cannot approve ingest"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_rejects_fatsecret_project_source() -> None:
    payload = _audit_payload()
    _source_decision(payload, _FAT_PLATFORM_SOURCE)["decision"] = "deferred_contract_review"

    with pytest.raises(SourceGapAuditError, match="fatsecret_platform source-gap mismatch"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_rejects_edamam_api_calls() -> None:
    payload = _audit_payload()
    _source_decision(payload, "edamam_food_database")["api_calls_allowed"] = True

    with pytest.raises(SourceGapAuditError, match="edamam_food_database cannot approve"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_rejects_jptn_or_regional_eligibility() -> None:
    payload = _audit_payload()
    _source_decision(payload, "jptn_food_facts")["decision"] = "auxiliary_barcode_branded_source"

    with pytest.raises(SourceGapAuditError, match="jptn_food_facts source-gap mismatch"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_rejects_menustat_current_catalog(tmp_path: Path) -> None:
    catalog_path = _mutate_catalog_source("menustat", "source_classification", "current", tmp_path)
    report = build_source_gap_audit_report(
        catalog_path=catalog_path,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_AUDIT_PATH,
    )

    assert report["success"] is False
    errors = report["validation_errors"]
    assert isinstance(errors, list)
    assert any("current sources must be active update sources" in str(error) for error in errors)


def test_source_gap_audit_rejects_off_missing_odbl_ref(tmp_path: Path) -> None:
    onboarding_path = _mutate_onboarding_source(
        "open_food_facts",
        "provider_policy_ref",
        None,
        tmp_path,
    )
    report = build_source_gap_audit_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=onboarding_path,
        coverage_path=_AUDIT_PATH,
    )

    assert report["success"] is False
    errors = report["validation_errors"]
    assert isinstance(errors, list)
    assert any("policy mismatch for open_food_facts" in str(error) for error in errors)


def test_source_gap_audit_rejects_missing_source_decision() -> None:
    payload = _audit_payload()
    decisions = payload["source_gap_decisions"]
    assert isinstance(decisions, list)
    decisions.pop()

    with pytest.raises(SourceGapAuditError, match="source_gap_decisions must be exactly"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_rejects_unknown_source_decision() -> None:
    payload = _audit_payload()
    _source_decision(payload, "nutritionix")["source"] = "unknown_restaurant_api"

    with pytest.raises(SourceGapAuditError, match="unknown source gap decision"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_rejects_unknown_domain_source_id() -> None:
    payload = _audit_payload()
    _domain(payload, "generic_food_composition")["primary_sources"] = ["not_a_source"]

    with pytest.raises(SourceGapAuditError, match="primary_sources contains unknown source"):
        parse_source_gap_audit(payload, catalog=_catalog(), onboarding=_onboarding())


def test_source_gap_audit_cli_is_file_only_and_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid.invalid/pulseplate")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--catalog",
            str(_CATALOG_PATH),
            "--onboarding",
            str(_ONBOARDING_PATH),
            "--coverage",
            str(_AUDIT_PATH),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)

    assert result.stderr == ""
    assert report["success"] is True
    assert report["network_allowed"] is False
    assert report["db_writes_allowed"] is False
    assert report["api_calls_allowed"] is False
    assert report["scraping_allowed"] is False


def test_source_gap_audit_cli_plain_text_success() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--catalog",
            str(_CATALOG_PATH),
            "--onboarding",
            str(_ONBOARDING_PATH),
            "--coverage",
            str(_AUDIT_PATH),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert "food_source_gap_audit: PASS" in result.stdout


def test_source_gap_audit_cli_returns_nonzero_for_invalid_artifact(tmp_path: Path) -> None:
    payload = _audit_payload()
    payload["runtime_cutover"] = True
    audit_path = _write_payload(tmp_path / "audit.json", payload)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--catalog",
            str(_CATALOG_PATH),
            "--onboarding",
            str(_ONBOARDING_PATH),
            "--coverage",
            str(audit_path),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)

    assert result.returncode == 1
    assert report["success"] is False
    assert report["validation_errors"]


def test_source_gap_audit_cli_plain_text_failure(tmp_path: Path) -> None:
    payload = _audit_payload()
    payload["network_allowed"] = True
    audit_path = _write_payload(tmp_path / "audit.json", payload)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--catalog",
            str(_CATALOG_PATH),
            "--onboarding",
            str(_ONBOARDING_PATH),
            "--coverage",
            str(audit_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stderr == ""
    assert "food_source_gap_audit: FAIL" in result.stdout
    assert "Validation errors:" in result.stdout
    assert "network_allowed" in result.stdout
    assert "must be false" in result.stdout


def test_source_gap_audit_core_has_no_network_or_db_imports() -> None:
    tree = ast.parse(Path(source_gap_audit.__file__).read_text(encoding="utf-8"))
    forbidden = {
        "requests",
        "httpx",
        "psycopg",
        "sqlalchemy",
        "digitalocean",
        "sqlite3",
        "subprocess",
    }
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    assert forbidden.isdisjoint(imports)
    assert "urllib" not in imports
