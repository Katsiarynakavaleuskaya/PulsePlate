"""Tests for the deterministic PR19 regional catalog source-specific terms gate."""

from __future__ import annotations

import copy
from dataclasses import replace
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
from core.food_sources.regional_catalog_provider_terms import (
    RegionalCatalogProviderTermsGovernance,
    build_regional_catalog_provider_terms_report,
    load_regional_catalog_provider_terms_governance,
)
from core.food_sources.regional_catalog_source_specific_terms import (
    RegionalCatalogSourceSpecificTermsError,
    build_regional_catalog_source_specific_terms_report,
    load_regional_catalog_source_specific_terms_governance,
    parse_regional_catalog_source_specific_terms_governance,
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
_PR18_PROVIDER_TERMS_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_REGIONAL_CATALOG_PROVIDER_TERMS_MATRIX_PR18_2026-05-21.json"
)
_SOURCE_SPECIFIC_TERMS_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_REVIEW_PR19_2026-05-21.json"
)
_CLI_MODULE = "scripts.food_source_regional_catalog_source_specific_terms"


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


def _pr18_ref() -> str:
    return (
        "docs/architecture/" "FOOD_DATA_REGIONAL_CATALOG_PROVIDER_TERMS_MATRIX_PR18_2026-05-21.json"
    )


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


def _pr16_report() -> dict[str, object]:
    return build_preference_mapping_closeout_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        closeout_path=_PR16_CLOSEOUT_PATH,
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


def _pr18_report() -> dict[str, object]:
    return build_regional_catalog_provider_terms_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        pr17_identity_path=_PR17_IDENTITY_PATH,
        provider_terms_path=_PR18_PROVIDER_TERMS_PATH,
    )


def _pr18_gate() -> RegionalCatalogProviderTermsGovernance:
    return load_regional_catalog_provider_terms_governance(
        _PR18_PROVIDER_TERMS_PATH,
        pr17_report=_pr17_report(),
        pr17_gate=_pr17_gate(),
        expected_pr17_identity_ref=_pr17_ref(),
    )


def _source_specific_terms_payload() -> dict[str, object]:
    payload = json.loads(_SOURCE_SPECIFIC_TERMS_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _candidate(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    candidates = payload["candidate_source_specific_terms"]
    assert isinstance(candidates, list)
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
            return candidate
    raise AssertionError(f"missing candidate {candidate_id}")


def test_load_regional_catalog_source_specific_terms_accepts_canonical_artifact() -> None:
    gate = load_regional_catalog_source_specific_terms_governance(
        _SOURCE_SPECIFIC_TERMS_PATH,
        pr18_report=_pr18_report(),
        pr18_gate=_pr18_gate(),
        expected_pr18_provider_terms_ref=_pr18_ref(),
    )

    assert gate.source == "regional_catalogs"
    assert gate.source_classification == "unresolved"
    assert gate.final_gate_decision == (
        "regional_catalog_source_specific_terms_review_only_no_provider_use"
    )
    assert [candidate.candidate_id for candidate in gate.candidate_source_specific_terms] == [
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
    assert {candidate.allowed_role for candidate in gate.candidate_source_specific_terms} == {
        "review_only_no_provider_use"
    }


def test_regional_catalog_source_specific_terms_report_is_deterministic_json_contract() -> None:
    report = build_regional_catalog_source_specific_terms_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        pr17_identity_path=_PR17_IDENTITY_PATH,
        pr18_provider_terms_path=_PR18_PROVIDER_TERMS_PATH,
        source_specific_terms_path=_SOURCE_SPECIFIC_TERMS_PATH,
    )

    assert report["success"] is True
    assert report["source"] == "regional_catalogs"
    assert report["network_allowed"] is False
    assert report["api_calls_allowed"] is False
    assert report["account_access_allowed"] is False
    assert report["seller_api_use_allowed"] is False
    assert report["partner_api_use_allowed"] is False
    assert report["provider_use_allowed"] is False
    assert report["nutrition_authority_allowed"] is False
    assert report["source_authority_allowed"] is False
    assert report["validation_errors"] == []
    assert report["next_recommended_lane"] == "regional_catalog_source_specific_terms_closeout"
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
    evidence_confidence = report["candidate_evidence_confidence"]
    assert isinstance(evidence_confidence, dict)
    assert set(evidence_confidence.values()) == {"low_unverified"}
    assert report["candidate_route_classifications"] == {
        "data_europa_national_portals": "public_open_data_portal_umbrella",
        "kroger": "commercial_grocery_api_candidate",
        "walmart": "commercial_grocery_api_candidate",
        "pepesto_grocery": "commercial_grocery_api_candidate",
        "pricesapi": "commercial_price_aggregator_candidate",
        "yandex_eda": "partner_menu_api_candidate",
        "wildberries": "seller_marketplace_api_candidate",
        "ozon": "seller_marketplace_api_candidate",
        "apify_scraping_providers": "scraping_provider_candidate",
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
        "account_access_allowed",
        "paid_source_use_allowed",
        "seller_api_use_allowed",
        "partner_api_use_allowed",
        "provider_use_allowed",
        "cache_authority_allowed",
        "redistribution_allowed",
        "provider_integration_allowed",
        "public_dataset_claim_allowed",
        "product_display_allowed",
        "nutrition_authority_allowed",
        "source_authority_allowed",
    ),
)
def test_regional_catalog_source_specific_terms_rejects_unsafe_flags(
    flag_name: str,
) -> None:
    payload = _source_specific_terms_payload()
    payload[flag_name] = True

    with pytest.raises(RegionalCatalogSourceSpecificTermsError, match="unsafe flags"):
        parse_regional_catalog_source_specific_terms_governance(
            payload,
            pr18_report=_pr18_report(),
            pr18_gate=_pr18_gate(),
        )


def test_regional_catalog_source_specific_terms_rejects_file_only_false() -> None:
    payload = _source_specific_terms_payload()
    payload["file_only"] = False

    with pytest.raises(RegionalCatalogSourceSpecificTermsError, match="file_only"):
        parse_regional_catalog_source_specific_terms_governance(
            payload,
            pr18_report=_pr18_report(),
            pr18_gate=_pr18_gate(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("schema_version", "", "non-empty string"),
        ("schema_version", "food-data-source-specific-terms.v1", "schema_version"),
        ("generated_on", "2026/05/21", "YYYY-MM-DD"),
        ("generated_on", "2026-99-21", "YYYY-MM-DD"),
        ("pr18_merged_pr", True, "integer"),
        ("pr18_merged_pr", 9999, "pr18_merged_pr"),
        ("pr18_provider_terms_ref", "docs/architecture/other.json", "pr18_provider_terms_ref"),
        ("blocked_methods", "api_call", "list of strings"),
        ("blocked_methods", [], "must not be empty"),
        ("blocked_methods", ["api_call", "api_call"], "duplicate"),
        ("blocked_methods", ["api_call"], "exactly"),
        ("source_specific_terms_decision", "API calls allowed.", "approve"),
        ("notes", "Provider use approved.", "approve"),
        ("next_recommended_lane", "runtime_provider_integration", "next_recommended_lane"),
        ("final_gate_decision", "provider_use_approved", "final_gate_decision"),
    ),
)
def test_regional_catalog_source_specific_terms_rejects_malformed_top_level_fields(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _source_specific_terms_payload()
    payload[field_name] = bad_value

    with pytest.raises(RegionalCatalogSourceSpecificTermsError, match=match):
        parse_regional_catalog_source_specific_terms_governance(
            payload,
            pr18_report=_pr18_report(),
            pr18_gate=_pr18_gate(),
            expected_pr18_provider_terms_ref=_pr18_ref(),
        )


def test_regional_catalog_source_specific_terms_rejects_unexpected_top_level_keys() -> None:
    payload = _source_specific_terms_payload()
    payload["provider_use_approved"] = True

    with pytest.raises(RegionalCatalogSourceSpecificTermsError, match="unexpected keys"):
        parse_regional_catalog_source_specific_terms_governance(
            payload,
            pr18_report=_pr18_report(),
            pr18_gate=_pr18_gate(),
        )


@pytest.mark.parametrize("payload", ([], {1: "bad-key"}))
def test_regional_catalog_source_specific_terms_rejects_non_mapping_payloads(
    payload: object,
) -> None:
    with pytest.raises(RegionalCatalogSourceSpecificTermsError):
        parse_regional_catalog_source_specific_terms_governance(
            payload,
            pr18_report=_pr18_report(),
            pr18_gate=_pr18_gate(),
        )


def test_regional_catalog_source_specific_terms_rejects_non_list_candidates() -> None:
    payload = _source_specific_terms_payload()
    payload["candidate_source_specific_terms"] = "not-a-list"

    with pytest.raises(
        RegionalCatalogSourceSpecificTermsError,
        match="candidate_source_specific_terms must be a list",
    ):
        parse_regional_catalog_source_specific_terms_governance(
            payload,
            pr18_report=_pr18_report(),
            pr18_gate=_pr18_gate(),
        )


def test_regional_catalog_source_specific_terms_rejects_duplicate_candidate_ids() -> None:
    payload = _source_specific_terms_payload()
    candidates = payload["candidate_source_specific_terms"]
    assert isinstance(candidates, list)
    candidates[-1] = copy.deepcopy(candidates[0])

    with pytest.raises(RegionalCatalogSourceSpecificTermsError, match="duplicate"):
        parse_regional_catalog_source_specific_terms_governance(
            payload,
            pr18_report=_pr18_report(),
            pr18_gate=_pr18_gate(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("candidate_id", "unknown", "unknown candidate_id"),
        ("candidate_name", "Wrong", "candidate_name must match PR18"),
        ("region_scope", "wrong", "region_scope must match PR18"),
        ("country_or_market", "wrong", "country_or_market must match PR18"),
        ("source_url", "https://example.com/other", "source_url must match PR18"),
        (
            "upstream_evidence_type",
            "manual_override",
            "upstream_evidence_type must match PR18",
        ),
        (
            "provider_route_classification",
            "runtime_provider",
            "provider_route_classification must match PR18",
        ),
        ("pr18_allowed_role", "provider_use_approved", "pr18_allowed_role"),
        (
            "public_terms_reference",
            "https://example.com/terms",
            "public_terms_reference must match PR18 source_url",
        ),
        (
            "public_terms_reference_role",
            "runtime_terms_authority",
            "public_terms_reference_role",
        ),
        ("terms_document_identity_status", "verified", "terms_document_identity_status"),
        ("account_access_status", "verified", "account_access_status"),
        ("retrieval_contract_status", "verified", "retrieval_contract_status"),
        ("license_status", "verified", "license_status"),
        ("cache_terms_status", "approved", "cache_terms_status"),
        ("redistribution_terms_status", "approved", "redistribution_terms_status"),
        ("display_terms_status", "approved", "display_terms_status"),
        ("attribution_terms_status", "approved", "attribution_terms_status"),
        ("nutrition_authority_status", "approved", "nutrition_authority_status"),
        ("product_authority_status", "approved", "product_authority_status"),
        ("evidence_confidence", "high_verified", "evidence_confidence"),
        ("uncertainty_notes", "Account access allowed.", "approve"),
        ("blocking_reasons", ["Provider use approved."], "approve"),
        ("allowed_role", "provider_use_approved", "allowed_role"),
        ("next_required_review", "provider_integration", "next_required_review"),
    ),
)
def test_regional_catalog_source_specific_terms_rejects_malformed_candidate_fields(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _source_specific_terms_payload()
    _candidate(payload, "kroger")[field_name] = bad_value

    with pytest.raises(RegionalCatalogSourceSpecificTermsError, match=match):
        parse_regional_catalog_source_specific_terms_governance(
            payload,
            pr18_report=_pr18_report(),
            pr18_gate=_pr18_gate(),
        )


def test_regional_catalog_source_specific_terms_rejects_candidate_order_drift() -> None:
    payload = _source_specific_terms_payload()
    candidates = payload["candidate_source_specific_terms"]
    assert isinstance(candidates, list)
    candidates.reverse()

    with pytest.raises(RegionalCatalogSourceSpecificTermsError, match="candidate order"):
        parse_regional_catalog_source_specific_terms_governance(
            payload,
            pr18_report=_pr18_report(),
            pr18_gate=_pr18_gate(),
        )


@pytest.mark.parametrize(
    ("report_update", "match"),
    (
        ({"success": False}, "PR18 provider terms report must succeed"),
        (
            {"next_recommended_lane": "runtime_provider_integration"},
            "PR18 next_recommended_lane",
        ),
        ({"candidate_ids": ["kroger"]}, "PR18 candidate_ids drifted"),
        ({"network_allowed": True}, "PR18 unsafe flag drifted: network_allowed"),
        ({"file_only": False}, "PR18 file_only flag drifted"),
    ),
)
def test_regional_catalog_source_specific_terms_validates_pr18_report_contract(
    report_update: dict[str, object],
    match: str,
) -> None:
    report = _pr18_report()
    report.update(report_update)

    with pytest.raises(RegionalCatalogSourceSpecificTermsError, match=match):
        parse_regional_catalog_source_specific_terms_governance(
            _source_specific_terms_payload(),
            pr18_report=report,
            pr18_gate=_pr18_gate(),
        )


def test_regional_catalog_source_specific_terms_validates_pr18_candidate_review_gate() -> None:
    pr18_gate = _pr18_gate()
    first_candidate = pr18_gate.candidate_terms[0]
    bad_candidate = replace(first_candidate, next_required_review="provider_integration")
    bad_gate = replace(
        pr18_gate,
        candidate_terms=(bad_candidate, *pr18_gate.candidate_terms[1:]),
    )

    with pytest.raises(RegionalCatalogSourceSpecificTermsError, match="next_required_review"):
        parse_regional_catalog_source_specific_terms_governance(
            _source_specific_terms_payload(),
            pr18_report=_pr18_report(),
            pr18_gate=bad_gate,
        )


def test_regional_catalog_source_specific_terms_cli_success_json() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", _CLI_MODULE, "--json"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["success"] is True
    assert payload["validation_errors"] == []
    assert payload["source_authority_allowed"] is False


def test_regional_catalog_source_specific_terms_cli_failure(tmp_path: Path) -> None:
    payload = _source_specific_terms_payload()
    payload["network_allowed"] = True
    bad_path = _write_payload(tmp_path / "bad-pr19.json", payload)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--source-specific-terms",
            str(bad_path),
        ],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "food_source_regional_catalog_source_specific_terms: FAIL" in completed.stdout
    assert "network_allowed" in completed.stdout
