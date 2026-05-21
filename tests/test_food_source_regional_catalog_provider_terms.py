"""Tests for the deterministic PR18 regional catalog provider terms matrix gate."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources.preference_mapping_closeout import build_preference_mapping_closeout_report
from core.food_sources.regional_catalog_identity import (
    RegionalCatalogIdentityGovernance,
    build_regional_catalog_identity_report,
    load_regional_catalog_identity_governance,
)
from core.food_sources.source_catalog import SourceCatalog, load_source_catalog
from core.food_sources.source_gap_audit import SourceGapAudit, load_source_gap_audit
from core.food_sources.source_onboarding import SourceOnboarding, load_source_onboarding
from core.food_sources.regional_catalog_provider_terms import (
    RegionalCatalogProviderTermsError,
    build_regional_catalog_provider_terms_report,
    load_regional_catalog_provider_terms_governance,
    parse_regional_catalog_provider_terms_governance,
)

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
_RECIPE_DISH_CORPUS_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json"
)
_PREFERENCE_MAPPING_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_2026-05-13.json"
)
_PR16_CLOSEOUT_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_PREFERENCE_RECIPE_MAPPING_CLOSEOUT_PR16_2026-05-19.json"
)
_PR17_IDENTITY_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_REGIONAL_CATALOG_IDENTITY_LICENSE_PR17_2026-05-19.json"
)
_PROVIDER_TERMS_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_REGIONAL_CATALOG_PROVIDER_TERMS_MATRIX_PR18_2026-05-21.json"
)
_CLI_MODULE = "scripts.food_source_regional_catalog_provider_terms"


def _catalog_ref() -> str:
    return "docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json"


def _onboarding_ref() -> str:
    return "docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json"


def _coverage_ref() -> str:
    return "docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json"


def _pr16_ref() -> str:
    return "docs/architecture/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_CLOSEOUT_PR16_2026-05-19.json"


def _pr17_ref() -> str:
    return "docs/architecture/FOOD_DATA_REGIONAL_CATALOG_IDENTITY_LICENSE_PR17_2026-05-19.json"


def _catalog() -> SourceCatalog:
    return load_source_catalog(_CATALOG_PATH)


def _onboarding() -> SourceOnboarding:
    return load_source_onboarding(
        _ONBOARDING_PATH,
        catalog=_catalog(),
        expected_catalog_ref=_catalog_ref(),
    )


def _coverage() -> SourceGapAudit:
    return load_source_gap_audit(
        _COVERAGE_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        expected_catalog_ref=_catalog_ref(),
        expected_onboarding_ref=_onboarding_ref(),
    )


def _pr17_report() -> dict[str, object]:
    return build_regional_catalog_identity_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        regional_identity_path=_PR17_IDENTITY_PATH,
    )


def _pr16_report() -> dict[str, object]:
    return build_preference_mapping_closeout_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        closeout_path=_PR16_CLOSEOUT_PATH,
    )


def _pr17_gate() -> RegionalCatalogIdentityGovernance:
    return load_regional_catalog_identity_governance(
        _PR17_IDENTITY_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        coverage=_coverage(),
        pr16_report=_pr16_report(),
        expected_catalog_ref=_catalog_ref(),
        expected_onboarding_ref=_onboarding_ref(),
        expected_coverage_ref=_coverage_ref(),
        expected_pr16_closeout_ref=_pr16_ref(),
    )


def _provider_terms_payload() -> dict[str, object]:
    payload = json.loads(_PROVIDER_TERMS_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _candidate(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    candidates = payload["candidate_terms"]
    assert isinstance(candidates, list)
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
            return candidate
    raise AssertionError(f"missing candidate {candidate_id}")


def test_load_regional_catalog_provider_terms_accepts_canonical_artifact() -> None:
    gate = load_regional_catalog_provider_terms_governance(
        _PROVIDER_TERMS_PATH,
        pr17_report=_pr17_report(),
        pr17_gate=_pr17_gate(),
        expected_pr17_identity_ref=_pr17_ref(),
    )

    assert gate.source == "regional_catalogs"
    assert gate.source_classification == "unresolved"
    assert gate.next_recommended_lane == "regional_catalog_source_specific_terms_review"
    assert [candidate.candidate_id for candidate in gate.candidate_terms] == [
        "data_europa_national_portals",
        "kroger",
        "walmart",
        "pepesto_grocery",
        "pricesapi",
        "yandex_eda",
        "wildberries",
        "ozon",
        "apify_scraping_providers",
    ]


def test_regional_catalog_provider_terms_report_is_deterministic_json_contract() -> None:
    report = build_regional_catalog_provider_terms_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        pr17_identity_path=_PR17_IDENTITY_PATH,
        provider_terms_path=_PROVIDER_TERMS_PATH,
    )

    assert report["success"] is True
    assert report["source"] == "regional_catalogs"
    assert report["network_allowed"] is False
    assert report["api_calls_allowed"] is False
    assert report["seller_api_use_allowed"] is False
    assert report["partner_api_use_allowed"] is False
    assert report["nutrition_authority_allowed"] is False
    assert report["validation_errors"] == []
    assert report["next_recommended_lane"] == "regional_catalog_source_specific_terms_review"
    assert report["candidate_decisions"] == {
        "data_europa_national_portals": "review_only_no_provider_use",
        "kroger": "review_only_no_provider_use",
        "walmart": "review_only_no_provider_use",
        "pepesto_grocery": "review_only_no_provider_use",
        "pricesapi": "review_only_no_provider_use",
        "yandex_eda": "review_only_no_provider_use",
        "wildberries": "review_only_no_provider_use",
        "ozon": "review_only_no_provider_use",
        "apify_scraping_providers": "review_only_no_provider_use",
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
        "automation_allowed",
        "paid_source_use_allowed",
        "seller_api_use_allowed",
        "partner_api_use_allowed",
        "cache_authority_allowed",
        "redistribution_allowed",
        "provider_integration_allowed",
        "public_dataset_claim_allowed",
        "product_display_allowed",
        "nutrition_authority_allowed",
    ),
)
def test_regional_catalog_provider_terms_rejects_unsafe_flags(flag_name: str) -> None:
    payload = _provider_terms_payload()
    payload[flag_name] = True

    with pytest.raises(RegionalCatalogProviderTermsError, match="unsafe flags"):
        parse_regional_catalog_provider_terms_governance(
            payload,
            pr17_report=_pr17_report(),
            pr17_gate=_pr17_gate(),
        )


def test_regional_catalog_provider_terms_rejects_file_only_false() -> None:
    payload = _provider_terms_payload()
    payload["file_only"] = False

    with pytest.raises(RegionalCatalogProviderTermsError, match="file_only"):
        parse_regional_catalog_provider_terms_governance(
            payload,
            pr17_report=_pr17_report(),
            pr17_gate=_pr17_gate(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("schema_version", "", "non-empty string"),
        ("schema_version", "food-data-regional-provider-terms.v1", "schema_version"),
        ("generated_on", "2026/05/21", "YYYY-MM-DD"),
        ("generated_on", "2026-99-21", "YYYY-MM-DD"),
        ("pr17_merged_pr", True, "integer"),
        ("pr17_merged_pr", 9999, "pr17_merged_pr"),
        ("pr17_identity_ref", "docs/architecture/other.json", "pr17_identity_ref"),
        ("blocked_methods", "api_call", "list of strings"),
        ("blocked_methods", [], "must not be empty"),
        ("blocked_methods", ["api_call", "api_call"], "duplicate"),
        ("blocked_methods", ["api_call"], "exactly"),
        ("provider_terms_decision", "Provider use approved.", "approve"),
        ("notes", "API calls allowed for provider terms checks.", "approve"),
        ("next_recommended_lane", "runtime_provider_integration", "next_recommended_lane"),
        ("final_gate_decision", "provider_use_approved", "final_gate_decision"),
    ),
)
def test_regional_catalog_provider_terms_rejects_malformed_top_level_fields(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _provider_terms_payload()
    payload[field_name] = bad_value

    with pytest.raises(RegionalCatalogProviderTermsError, match=match):
        parse_regional_catalog_provider_terms_governance(
            payload,
            pr17_report=_pr17_report(),
            pr17_gate=_pr17_gate(),
            expected_pr17_identity_ref=_pr17_ref(),
        )


def test_regional_catalog_provider_terms_rejects_unexpected_top_level_keys() -> None:
    payload = _provider_terms_payload()
    payload["provider_use_approved"] = True

    with pytest.raises(RegionalCatalogProviderTermsError, match="unexpected keys"):
        parse_regional_catalog_provider_terms_governance(
            payload,
            pr17_report=_pr17_report(),
            pr17_gate=_pr17_gate(),
        )


@pytest.mark.parametrize(
    "payload",
    (
        [],
        {1: "bad-key"},
    ),
)
def test_regional_catalog_provider_terms_rejects_non_mapping_payloads(payload: object) -> None:
    with pytest.raises(RegionalCatalogProviderTermsError):
        parse_regional_catalog_provider_terms_governance(
            payload,
            pr17_report=_pr17_report(),
            pr17_gate=_pr17_gate(),
        )


def test_regional_catalog_provider_terms_rejects_non_list_candidate_terms() -> None:
    payload = _provider_terms_payload()
    payload["candidate_terms"] = "not-a-list"

    with pytest.raises(RegionalCatalogProviderTermsError, match="candidate_terms must be a list"):
        parse_regional_catalog_provider_terms_governance(
            payload,
            pr17_report=_pr17_report(),
            pr17_gate=_pr17_gate(),
        )


def test_regional_catalog_provider_terms_rejects_duplicate_candidate_ids() -> None:
    payload = _provider_terms_payload()
    candidates = payload["candidate_terms"]
    assert isinstance(candidates, list)
    candidates[-1] = copy.deepcopy(candidates[0])

    with pytest.raises(RegionalCatalogProviderTermsError, match="candidate_terms"):
        parse_regional_catalog_provider_terms_governance(
            payload,
            pr17_report=_pr17_report(),
            pr17_gate=_pr17_gate(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("candidate_id", "unknown_provider", "unknown candidate_id"),
        ("candidate_name", "Changed Provider", "candidate_name"),
        ("source_url", "https://example.invalid/changed", "source_url"),
        ("upstream_evidence_type", "live_provider_api", "upstream_evidence_type"),
        ("pr17_allowed_role", "source_authority", "pr17_allowed_role"),
        ("provider_route_classification", "runtime_provider", "provider_route_classification"),
        ("terms_status", "approved", "terms_status"),
        ("account_access_status", "approved", "account_access_status"),
        ("cache_terms_status", "approved", "cache_terms_status"),
        ("redistribution_terms_status", "approved", "redistribution_terms_status"),
        ("display_terms_status", "approved", "display_terms_status"),
        ("nutrition_authority_status", "approved", "nutrition_authority_status"),
        ("allowed_role", "provider_use_allowed", "allowed_role"),
        ("blocking_reasons", ["identity and license verified"], "blocking_reasons"),
        ("next_required_review", "api_ingest", "next_required_review"),
        ("notes", "Seller API approved for Ozon.", "approve"),
    ),
)
def test_regional_catalog_provider_terms_rejects_candidate_matrix_drift(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _provider_terms_payload()
    _candidate(payload, "ozon")[field_name] = bad_value

    with pytest.raises(RegionalCatalogProviderTermsError, match=match):
        parse_regional_catalog_provider_terms_governance(
            payload,
            pr17_report=_pr17_report(),
            pr17_gate=_pr17_gate(),
        )


@pytest.mark.parametrize(
    "bad_notes",
    (
        "API calls allowed for regional provider terms.",
        "May scrape Wildberries for terms evidence.",
        "Download approved for Kroger product data.",
        "Paid provider approved for PricesAPI.",
        "Seller access allowed for Ozon.",
        "Partner API approved for Yandex EDA.",
        "Cache authority approved for regional catalogs.",
        "Redistribution allowed for Walmart.",
        "Runtime authority allowed for provider integration.",
        "Product display approved for data.europa.eu.",
        "Nutrition authority approved for Kroger.",
        "Provider integration approved for Pepesto.",
        "DB writes allowed for the matrix.",
        "DigitalOcean Postgres load approved for regional catalogs.",
    ),
)
def test_regional_catalog_provider_terms_rejects_unsafe_prose(bad_notes: str) -> None:
    payload = _provider_terms_payload()
    payload["notes"] = bad_notes

    with pytest.raises(RegionalCatalogProviderTermsError, match="approve"):
        parse_regional_catalog_provider_terms_governance(
            payload,
            pr17_report=_pr17_report(),
            pr17_gate=_pr17_gate(),
        )


def test_regional_catalog_provider_terms_rejects_pr17_handoff_drift() -> None:
    report = dict(_pr17_report())
    report["next_recommended_lane"] = "other_lane"

    with pytest.raises(RegionalCatalogProviderTermsError, match="PR17 next_recommended_lane"):
        parse_regional_catalog_provider_terms_governance(
            _provider_terms_payload(),
            pr17_report=report,
            pr17_gate=_pr17_gate(),
        )


def test_regional_catalog_provider_terms_report_fails_on_malformed_artifact(
    tmp_path: Path,
) -> None:
    payload = _provider_terms_payload()
    payload["api_calls_allowed"] = True
    bad_path = _write_payload(tmp_path / "provider_terms.json", payload)

    report = build_regional_catalog_provider_terms_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        pr17_identity_path=_PR17_IDENTITY_PATH,
        provider_terms_path=bad_path,
    )

    assert report["success"] is False
    assert report["api_calls_allowed"] is True
    assert "api_calls_allowed" in str(report["validation_errors"])


def test_regional_catalog_provider_terms_cli_success_json_smoke() -> None:
    result = subprocess.run(
        [sys.executable, "-m", _CLI_MODULE, "--json"],
        cwd=_REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    report = json.loads(result.stdout)
    assert report["success"] is True
    assert report["next_recommended_lane"] == "regional_catalog_source_specific_terms_review"


def test_regional_catalog_provider_terms_cli_failure(tmp_path: Path) -> None:
    payload = _provider_terms_payload()
    payload["scraping_allowed"] = True
    bad_path = _write_payload(tmp_path / "bad_provider_terms.json", payload)

    result = subprocess.run(
        [sys.executable, "-m", _CLI_MODULE, "--provider-terms", str(bad_path)],
        cwd=_REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "food_source_regional_catalog_provider_terms: FAIL" in result.stdout
    assert "scraping_allowed" in result.stdout
