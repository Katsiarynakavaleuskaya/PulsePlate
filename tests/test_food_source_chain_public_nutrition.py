"""Tests for the deterministic PR12 chain public nutrition governance gate."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources.chain_public_nutrition import (
    ChainPublicNutritionGovernanceError,
    build_chain_public_nutrition_governance_report,
    load_chain_public_nutrition_governance,
    parse_chain_public_nutrition_governance,
)
from core.food_sources.source_catalog import SourceCatalog, load_source_catalog
from core.food_sources.source_gap_audit import SourceGapAudit, load_source_gap_audit
from core.food_sources.source_onboarding import SourceOnboarding, load_source_onboarding

_REPO_ROOT = Path(__file__).parents[1]
_CATALOG_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json"
)
_ONBOARDING_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json"
)
_COVERAGE_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json"
)
_GOVERNANCE_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_CHAIN_PUBLIC_NUTRITION_PR12_2026-04-30.json"
)
_CLI_MODULE = "scripts.food_source_chain_public_nutrition"


def _catalog() -> SourceCatalog:
    return load_source_catalog(_CATALOG_PATH)


def _onboarding() -> SourceOnboarding:
    return load_source_onboarding(
        _ONBOARDING_PATH,
        catalog=_catalog(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
    )


def _coverage() -> SourceGapAudit:
    catalog = _catalog()
    onboarding = load_source_onboarding(
        _ONBOARDING_PATH,
        catalog=catalog,
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
    )
    return load_source_gap_audit(
        _COVERAGE_PATH,
        catalog=catalog,
        onboarding=onboarding,
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
    )


def _governance_payload() -> dict[str, object]:
    return json.loads(_GOVERNANCE_PATH.read_text(encoding="utf-8"))


def _catalog_payload() -> dict[str, object]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _onboarding_payload() -> dict[str, object]:
    return json.loads(_ONBOARDING_PATH.read_text(encoding="utf-8"))


def _coverage_payload() -> dict[str, object]:
    return json.loads(_COVERAGE_PATH.read_text(encoding="utf-8"))


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _chain_page(payload: dict[str, object], chain_id: str) -> dict[str, object]:
    pages = payload["representative_chain_pages"]
    assert isinstance(pages, list)
    for page in pages:
        if isinstance(page, dict) and page.get("chain_id") == chain_id:
            return page
    raise AssertionError(f"missing chain page {chain_id}")


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


def _mutate_coverage_decision(source_name: str, key: str, value: object, tmp_path: Path) -> Path:
    payload = _coverage_payload()
    decisions = payload["source_gap_decisions"]
    assert isinstance(decisions, list)
    for decision in decisions:
        if isinstance(decision, dict) and decision.get("source") == source_name:
            decision[key] = value
            break
    else:
        raise AssertionError(f"missing coverage decision {source_name}")
    return _write_payload(tmp_path / "coverage.json", payload)


def test_load_chain_public_nutrition_governance_accepts_canonical_artifact() -> None:
    governance = load_chain_public_nutrition_governance(
        _GOVERNANCE_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        coverage=_coverage(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
        expected_coverage_ref="docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json",
    )

    assert governance.pr11_landed_pr == 1601
    assert governance.source == "chain_public_nutrition_pages"
    assert governance.source_classification == "unresolved"
    assert governance.next_recommended_lane == "per_chain_legal_anti_scraping_review"
    assert [page.chain_id for page in governance.representative_chain_pages] == [
        "mcdonalds_us",
        "chipotle_us",
        "starbucks_us",
    ]


def test_chain_public_nutrition_report_is_deterministic_json_contract() -> None:
    report = build_chain_public_nutrition_governance_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        governance_path=_GOVERNANCE_PATH,
    )

    assert report == {
        "success": True,
        "dry_run": True,
        "source": "chain_public_nutrition_pages",
        "source_classification": "unresolved",
        "evidence_policy": "manual_evidence_only_legal_review_required",
        "allowed_evidence_types": [
            "official_public_url_citation",
            "manual_screenshot_internal_review",
        ],
        "blocked_evidence_types": [
            "scraping",
            "automated_collection",
            "api_call",
            "download",
            "social_media_harvest",
            "login_or_paywall_bypass",
            "cache_authority",
            "redistribution",
            "runtime_authority",
            "public_dataset_claim",
        ],
        "chain_page_ids": [
            "mcdonalds_us",
            "chipotle_us",
            "starbucks_us",
        ],
        "next_recommended_lane": "per_chain_legal_anti_scraping_review",
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "network_allowed": False,
        "db_writes_allowed": False,
        "api_calls_allowed": False,
        "source_download_allowed": False,
        "scraping_allowed": False,
        "paid_source_use_allowed": False,
        "redistribution_allowed": False,
        "public_dataset_claim_allowed": False,
        "automation_allowed": False,
        "file_only": True,
        "final_gate_decision": "chain_public_nutrition_governance_only_no_ingest",
        "validation_errors": [],
        "catalog_ref": "docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        "onboarding_ref": "docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
        "coverage_ref": "docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json",
        "pr11_landed_pr": 1601,
        "chain_page_decisions": {
            "mcdonalds_us": "manual_evidence_only_not_authority",
            "chipotle_us": "manual_evidence_only_not_authority",
            "starbucks_us": "manual_evidence_only_not_authority",
        },
        "official_urls": {
            "mcdonalds_us": "https://www.mcdonalds.com/us/en-us/about-our-food/nutrition-calculator.html",
            "chipotle_us": "https://www.chipotle.com/nutrition-calculator",
            "starbucks_us": "https://www.starbucks.com/menu/nutrition-info",
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
        "redistribution_allowed",
        "public_dataset_claim_allowed",
        "automation_allowed",
    ),
)
def test_chain_public_nutrition_rejects_unsafe_flags(flag_name: str) -> None:
    payload = _governance_payload()
    payload[flag_name] = True

    with pytest.raises(
        ChainPublicNutritionGovernanceError,
        match="must be false; file_only must be true",
    ):
        parse_chain_public_nutrition_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
        )


def test_chain_public_nutrition_rejects_missing_chain_page() -> None:
    payload = _governance_payload()
    pages = payload["representative_chain_pages"]
    assert isinstance(pages, list)
    pages.pop()

    with pytest.raises(
        ChainPublicNutritionGovernanceError,
        match="representative_chain_pages must be exactly",
    ):
        parse_chain_public_nutrition_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
        )


def test_chain_public_nutrition_rejects_duplicate_chain_page() -> None:
    payload = _governance_payload()
    pages = payload["representative_chain_pages"]
    assert isinstance(pages, list)
    pages[-1] = copy.deepcopy(pages[0])

    with pytest.raises(
        ChainPublicNutritionGovernanceError,
        match="representative_chain_pages must be exactly",
    ):
        parse_chain_public_nutrition_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
        )


def test_chain_public_nutrition_rejects_unknown_chain_page() -> None:
    payload = _governance_payload()
    _chain_page(payload, "chipotle_us")["chain_id"] = "wendys_us"

    with pytest.raises(ChainPublicNutritionGovernanceError, match="unknown chain page id"):
        parse_chain_public_nutrition_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
        )


def test_chain_public_nutrition_rejects_social_media_url() -> None:
    payload = _governance_payload()
    _chain_page(payload, "mcdonalds_us")["official_url"] = "https://instagram.com/mcdonalds"

    with pytest.raises(ChainPublicNutritionGovernanceError, match="social-media URLs"):
        parse_chain_public_nutrition_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
        )


def test_chain_public_nutrition_rejects_host_drift() -> None:
    payload = _governance_payload()
    _chain_page(payload, "chipotle_us")["official_url"] = "https://example.com/nutrition"

    with pytest.raises(ChainPublicNutritionGovernanceError, match="official_url host"):
        parse_chain_public_nutrition_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
        )


def test_chain_public_nutrition_rejects_same_host_non_nutrition_page() -> None:
    payload = _governance_payload()
    _chain_page(payload, "mcdonalds_us")["official_url"] = "https://www.mcdonalds.com/"

    with pytest.raises(ChainPublicNutritionGovernanceError, match="official_url must be"):
        parse_chain_public_nutrition_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "approved_ingest",
        "approved_runtime_authority",
        "scraping_allowed",
        "api_calls_allowed",
        "redistribution_allowed",
        "automation_allowed",
    ),
)
def test_chain_public_nutrition_rejects_chain_page_approval(field_name: str) -> None:
    payload = _governance_payload()
    _chain_page(payload, "starbucks_us")[field_name] = True

    with pytest.raises(ChainPublicNutritionGovernanceError, match="cannot approve"):
        parse_chain_public_nutrition_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
        )


def test_chain_public_nutrition_rejects_catalog_current_source_drift(tmp_path: Path) -> None:
    catalog_path = _mutate_catalog_source(
        "chain_public_nutrition_pages",
        "source_classification",
        "current",
        tmp_path,
    )
    report = build_chain_public_nutrition_governance_report(
        catalog_path=catalog_path,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        governance_path=_GOVERNANCE_PATH,
    )

    assert report["success"] is False
    assert "current sources must be active update sources" in str(report["validation_errors"])


def test_chain_public_nutrition_rejects_onboarding_ingest_path_drift(tmp_path: Path) -> None:
    onboarding_path = _mutate_onboarding_source(
        "chain_public_nutrition_pages",
        "ingestion_path",
        "manifest_preflight_only",
        tmp_path,
    )
    report = build_chain_public_nutrition_governance_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=onboarding_path,
        coverage_path=_COVERAGE_PATH,
        governance_path=_GOVERNANCE_PATH,
    )

    assert report["success"] is False
    assert "policy mismatch for chain_public_nutrition_pages: ingestion_path" in str(
        report["validation_errors"]
    )


def test_chain_public_nutrition_rejects_coverage_approval_drift(tmp_path: Path) -> None:
    coverage_path = _mutate_coverage_decision(
        "chain_public_nutrition_pages",
        "api_calls_allowed",
        True,
        tmp_path,
    )
    report = build_chain_public_nutrition_governance_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=coverage_path,
        governance_path=_GOVERNANCE_PATH,
    )

    assert report["success"] is False
    assert "cannot approve ingest, runtime authority, API calls" in str(report["validation_errors"])


def test_chain_public_nutrition_cli_json_smoke() -> None:
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
            str(_COVERAGE_PATH),
            "--governance",
            str(_GOVERNANCE_PATH),
            "--json",
        ],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)
    assert report["success"] is True
    assert report["network_allowed"] is False
    assert report["scraping_allowed"] is False
    assert report["api_calls_allowed"] is False
    assert report["db_writes_allowed"] is False


def test_chain_public_nutrition_cli_plain_text_failure(tmp_path: Path) -> None:
    payload = _governance_payload()
    payload["automation_allowed"] = True
    governance_path = _write_payload(tmp_path / "governance.json", payload)

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
            str(_COVERAGE_PATH),
            "--governance",
            str(governance_path),
        ],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "food_source_chain_public_nutrition: FAIL" in result.stdout
    assert "automation_allowed must be false" in result.stdout


def test_chain_public_nutrition_module_avoids_network_db_and_subprocess_imports() -> None:
    module_path = _REPO_ROOT / "core" / "food_sources" / "chain_public_nutrition.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.split(".")[0])

    assert {"requests", "httpx", "urllib3", "socket", "subprocess", "sqlalchemy"}.isdisjoint(
        imported_modules
    )
