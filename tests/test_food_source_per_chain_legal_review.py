"""Tests for the deterministic PR13 per-chain legal review gate."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources.chain_public_nutrition import (
    ChainPublicNutritionGovernance,
    load_chain_public_nutrition_governance,
)
from core.food_sources.per_chain_legal_review import (
    PerChainLegalReviewError,
    build_per_chain_legal_review_report,
    load_per_chain_legal_review_governance,
    parse_per_chain_legal_review_governance,
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
_CHAIN_PUBLIC_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_CHAIN_PUBLIC_NUTRITION_PR12_2026-04-30.json"
)
_GOVERNANCE_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_PER_CHAIN_LEGAL_ANTI_SCRAPING_PR13_2026-04-30.json"
)
_CLI_MODULE = "scripts.food_source_per_chain_legal_review"


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


def _chain_public_nutrition() -> ChainPublicNutritionGovernance:
    return load_chain_public_nutrition_governance(
        _CHAIN_PUBLIC_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        coverage=_coverage(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
        expected_coverage_ref="docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json",
    )


def _governance_payload() -> dict[str, object]:
    return json.loads(_GOVERNANCE_PATH.read_text(encoding="utf-8"))


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _review_row(payload: dict[str, object], chain_id: str) -> dict[str, object]:
    rows = payload["per_chain_reviews"]
    assert isinstance(rows, list)
    for row in rows:
        if isinstance(row, dict) and row.get("chain_id") == chain_id:
            return row
    raise AssertionError(f"missing per-chain review {chain_id}")


def test_load_per_chain_legal_review_accepts_canonical_artifact() -> None:
    governance = load_per_chain_legal_review_governance(
        _GOVERNANCE_PATH,
        chain_public_nutrition=_chain_public_nutrition(),
        expected_chain_public_nutrition_ref=(
            "docs/architecture/FOOD_DATA_CHAIN_PUBLIC_NUTRITION_PR12_2026-04-30.json"
        ),
    )

    assert governance.pr12_landed_pr == 1609
    assert governance.source == "chain_public_nutrition_pages"
    assert governance.source_classification == "unresolved"
    assert governance.next_recommended_lane == "recipe_dish_corpus_governance"
    assert [review.chain_id for review in governance.per_chain_reviews] == [
        "mcdonalds_us",
        "chipotle_us",
        "starbucks_us",
    ]


def test_per_chain_legal_review_report_is_deterministic_json_contract() -> None:
    report = build_per_chain_legal_review_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        chain_public_nutrition_path=_CHAIN_PUBLIC_PATH,
        governance_path=_GOVERNANCE_PATH,
    )

    assert report == {
        "success": True,
        "dry_run": True,
        "source": "chain_public_nutrition_pages",
        "source_classification": "unresolved",
        "evidence_policy": "manual_evidence_only_pending_per_chain_legal_review",
        "blocked_methods": [
            "scraping",
            "automated_collection",
            "api_call",
            "download",
            "login_or_paywall_bypass",
            "cache_authority",
            "redistribution",
            "runtime_authority",
            "public_dataset_claim",
            "digitalocean_postgres_load",
        ],
        "chain_page_ids": [
            "mcdonalds_us",
            "chipotle_us",
            "starbucks_us",
        ],
        "next_recommended_lane": "recipe_dish_corpus_governance",
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "network_allowed": False,
        "db_writes_allowed": False,
        "api_calls_allowed": False,
        "source_download_allowed": False,
        "scraping_allowed": False,
        "cache_authority_allowed": False,
        "redistribution_allowed": False,
        "public_dataset_claim_allowed": False,
        "automation_allowed": False,
        "file_only": True,
        "final_gate_decision": "per_chain_legal_anti_scraping_review_only_no_ingest",
        "validation_errors": [],
        "chain_public_nutrition_ref": (
            "docs/architecture/FOOD_DATA_CHAIN_PUBLIC_NUTRITION_PR12_2026-04-30.json"
        ),
        "pr12_landed_pr": 1609,
        "legal_review_status": {
            "mcdonalds_us": "required_not_approved",
            "chipotle_us": "required_not_approved",
            "starbucks_us": "required_not_approved",
        },
        "anti_scraping_review_status": {
            "mcdonalds_us": "required_not_approved",
            "chipotle_us": "required_not_approved",
            "starbucks_us": "required_not_approved",
        },
        "cache_decisions": {
            "mcdonalds_us": "blocked_not_approved",
            "chipotle_us": "blocked_not_approved",
            "starbucks_us": "blocked_not_approved",
        },
        "redistribution_decisions": {
            "mcdonalds_us": "blocked_not_approved",
            "chipotle_us": "blocked_not_approved",
            "starbucks_us": "blocked_not_approved",
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
        "cache_authority_allowed",
        "redistribution_allowed",
        "public_dataset_claim_allowed",
        "automation_allowed",
    ),
)
def test_per_chain_legal_review_rejects_top_level_unsafe_flags(flag_name: str) -> None:
    payload = _governance_payload()
    payload[flag_name] = True

    with pytest.raises(PerChainLegalReviewError, match="must be false; file_only must be true"):
        parse_per_chain_legal_review_governance(
            payload,
            chain_public_nutrition=_chain_public_nutrition(),
        )


@pytest.mark.parametrize(
    "flag_name",
    (
        "approved_ingest",
        "approved_runtime_authority",
        "scraping_allowed",
        "automation_allowed",
        "api_calls_allowed",
        "source_download_allowed",
        "db_writes_allowed",
        "cache_authority_allowed",
        "redistribution_allowed",
        "public_dataset_claim_allowed",
    ),
)
def test_per_chain_legal_review_rejects_per_chain_unsafe_flags(flag_name: str) -> None:
    payload = _governance_payload()
    _review_row(payload, "mcdonalds_us")[flag_name] = True

    with pytest.raises(PerChainLegalReviewError, match="cannot approve ingest"):
        parse_per_chain_legal_review_governance(
            payload,
            chain_public_nutrition=_chain_public_nutrition(),
        )


def test_per_chain_legal_review_rejects_pr12_url_drift() -> None:
    payload = _governance_payload()
    _review_row(payload, "chipotle_us")["official_url"] = "https://www.chipotle.com"

    with pytest.raises(PerChainLegalReviewError, match="chipotle_us official_url must match PR12"):
        parse_per_chain_legal_review_governance(
            payload,
            chain_public_nutrition=_chain_public_nutrition(),
        )


def test_per_chain_legal_review_rejects_missing_review_row() -> None:
    payload = _governance_payload()
    rows = payload["per_chain_reviews"]
    assert isinstance(rows, list)
    payload["per_chain_reviews"] = rows[:2]

    with pytest.raises(PerChainLegalReviewError, match="per_chain_reviews must be exactly"):
        parse_per_chain_legal_review_governance(
            payload,
            chain_public_nutrition=_chain_public_nutrition(),
        )


def test_per_chain_legal_review_rejects_allowed_legal_status() -> None:
    payload = _governance_payload()
    _review_row(payload, "starbucks_us")["legal_review_status"] = "approved"

    with pytest.raises(
        PerChainLegalReviewError,
        match="starbucks_us legal_review_status must be required_not_approved",
    ):
        parse_per_chain_legal_review_governance(
            payload,
            chain_public_nutrition=_chain_public_nutrition(),
        )


def test_per_chain_legal_review_rejects_cache_approval() -> None:
    payload = _governance_payload()
    _review_row(payload, "mcdonalds_us")["cache_decision"] = "approved"

    with pytest.raises(PerChainLegalReviewError, match="cache_decision must be blocked"):
        parse_per_chain_legal_review_governance(
            payload,
            chain_public_nutrition=_chain_public_nutrition(),
        )


@pytest.mark.parametrize(
    ("field_name", "unsafe_value", "expected_error"),
    (
        (
            "display_decision",
            "blocked_not_approved",
            "display_decision must be internal_review_only_not_product_display",
        ),
        (
            "attribution_decision",
            "approved",
            "attribution_decision must be required_not_approved",
        ),
        (
            "freshness_review_status",
            "approved",
            "freshness_review_status must be required_not_approved",
        ),
        (
            "schema_review_status",
            "approved",
            "schema_review_status must be required_not_approved",
        ),
    ),
)
def test_per_chain_legal_review_rejects_unsafe_review_decisions(
    field_name: str, unsafe_value: str, expected_error: str
) -> None:
    payload = _governance_payload()
    _review_row(payload, "mcdonalds_us")[field_name] = unsafe_value

    with pytest.raises(PerChainLegalReviewError, match=expected_error):
        parse_per_chain_legal_review_governance(
            payload,
            chain_public_nutrition=_chain_public_nutrition(),
        )


def test_per_chain_legal_review_rejects_wrong_next_lane() -> None:
    payload = _governance_payload()
    payload["next_recommended_lane"] = "digitalocean_postgres_load"

    with pytest.raises(PerChainLegalReviewError, match="next_recommended_lane"):
        parse_per_chain_legal_review_governance(
            payload,
            chain_public_nutrition=_chain_public_nutrition(),
        )


def test_per_chain_legal_review_cli_outputs_json_report() -> None:
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
            "--chain-public-nutrition",
            str(_CHAIN_PUBLIC_PATH),
            "--governance",
            str(_GOVERNANCE_PATH),
            "--json",
        ],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["next_recommended_lane"] == "recipe_dish_corpus_governance"
    assert payload["scraping_allowed"] is False


def test_per_chain_legal_review_cli_returns_failure_for_invalid_artifact(tmp_path: Path) -> None:
    payload = _governance_payload()
    payload["automation_allowed"] = True
    invalid_path = _write_payload(tmp_path / "invalid-pr13.json", payload)

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
            "--chain-public-nutrition",
            str(_CHAIN_PUBLIC_PATH),
            "--governance",
            str(invalid_path),
        ],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "food_source_per_chain_legal_review: FAIL" in result.stdout
    assert "automation_allowed must be false" in result.stdout


def test_per_chain_legal_review_report_surfaces_invalid_json(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{not json", encoding="utf-8")

    report = build_per_chain_legal_review_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        chain_public_nutrition_path=_CHAIN_PUBLIC_PATH,
        governance_path=invalid_path,
    )

    assert report["success"] is False
    errors = report["validation_errors"]
    assert isinstance(errors, list)
    assert "Cannot read per-chain legal review" in errors[0]


def test_per_chain_legal_review_requires_pr12_recommended_lane() -> None:
    chain_public_nutrition = copy.copy(_chain_public_nutrition())
    object.__setattr__(chain_public_nutrition, "next_recommended_lane", "bulk_ingest")

    with pytest.raises(PerChainLegalReviewError, match="PR12 must recommend"):
        parse_per_chain_legal_review_governance(
            _governance_payload(),
            chain_public_nutrition=chain_public_nutrition,
        )


def test_per_chain_legal_review_cli_has_no_sys_path_mutation() -> None:
    script_path = _REPO_ROOT / "scripts" / "food_source_per_chain_legal_review.py"
    tree = ast.parse(script_path.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "path":
            assert not (
                isinstance(node.value, ast.Name) and node.value.id == "sys"
            ), "CLI must not mutate sys.path; use python -m scripts.food_source_per_chain_legal_review"
