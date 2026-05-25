"""Tests for the deterministic PR21 dedicated legal-contract review gate."""

from __future__ import annotations

import copy
from dataclasses import replace
import functools
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources.preference_mapping_closeout import build_preference_mapping_closeout_report
from core.food_sources.regional_catalog_dedicated_legal_contract_review import (
    RegionalCatalogDedicatedLegalContractReviewError,
    build_regional_catalog_dedicated_legal_contract_review_report,
    load_regional_catalog_dedicated_legal_contract_review_governance,
    parse_regional_catalog_dedicated_legal_contract_review_governance,
)
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
    RegionalCatalogSourceSpecificTermsGovernance,
    build_regional_catalog_source_specific_terms_report,
    load_regional_catalog_source_specific_terms_governance,
)
from core.food_sources.regional_catalog_source_specific_terms_closeout import (
    RegionalCatalogSourceSpecificTermsCloseoutGovernance,
    build_regional_catalog_source_specific_terms_closeout_report,
    load_regional_catalog_source_specific_terms_closeout_governance,
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
_PR19_SOURCE_SPECIFIC_TERMS_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_REVIEW_PR19_2026-05-21.json"
)
_PR20_CLOSEOUT_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_CLOSEOUT_PR20_2026-05-24.json"
)
_PR21_LEGAL_REVIEW_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_REGIONAL_CATALOG_DEDICATED_LEGAL_CONTRACT_REVIEW_PR21_2026-05-25.json"
)
_CLI_MODULE = "scripts.food_source_regional_catalog_dedicated_legal_contract_review"
_EXPECTED_CANDIDATE_IDS = [
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


def _pr19_ref() -> str:
    return (
        "docs/architecture/"
        "FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_REVIEW_PR19_2026-05-21.json"
    )


def _pr20_ref() -> str:
    return (
        "docs/architecture/"
        "FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_CLOSEOUT_PR20_2026-05-24.json"
    )


@functools.cache
def _catalog() -> SourceCatalog:
    return load_source_catalog(_CATALOG_PATH)


@functools.cache
def _onboarding() -> SourceOnboarding:
    return load_source_onboarding(
        _ONBOARDING_PATH,
        catalog=_catalog(),
        expected_catalog_ref=_catalog_ref(),
    )


@functools.cache
def _coverage() -> SourceGapAudit:
    return load_source_gap_audit(
        _COVERAGE_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        expected_catalog_ref=_catalog_ref(),
        expected_onboarding_ref=_onboarding_ref(),
    )


@functools.cache
def _pr16_report() -> dict[str, object]:
    return build_preference_mapping_closeout_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        closeout_path=_PR16_CLOSEOUT_PATH,
    )


@functools.cache
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


@functools.cache
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


@functools.cache
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


@functools.cache
def _pr18_gate() -> RegionalCatalogProviderTermsGovernance:
    return load_regional_catalog_provider_terms_governance(
        _PR18_PROVIDER_TERMS_PATH,
        pr17_report=_pr17_report(),
        pr17_gate=_pr17_gate(),
        expected_pr17_identity_ref=_pr17_ref(),
    )


@functools.cache
def _pr19_report() -> dict[str, object]:
    return build_regional_catalog_source_specific_terms_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        pr17_identity_path=_PR17_IDENTITY_PATH,
        pr18_provider_terms_path=_PR18_PROVIDER_TERMS_PATH,
        source_specific_terms_path=_PR19_SOURCE_SPECIFIC_TERMS_PATH,
    )


@functools.cache
def _pr19_gate() -> RegionalCatalogSourceSpecificTermsGovernance:
    return load_regional_catalog_source_specific_terms_governance(
        _PR19_SOURCE_SPECIFIC_TERMS_PATH,
        pr18_report=_pr18_report(),
        pr18_gate=_pr18_gate(),
        expected_pr18_provider_terms_ref=_pr18_ref(),
    )


@functools.cache
def _pr20_report() -> dict[str, object]:
    return build_regional_catalog_source_specific_terms_closeout_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        pr17_identity_path=_PR17_IDENTITY_PATH,
        pr18_provider_terms_path=_PR18_PROVIDER_TERMS_PATH,
        pr19_source_specific_terms_path=_PR19_SOURCE_SPECIFIC_TERMS_PATH,
        closeout_path=_PR20_CLOSEOUT_PATH,
    )


@functools.cache
def _pr20_gate() -> RegionalCatalogSourceSpecificTermsCloseoutGovernance:
    return load_regional_catalog_source_specific_terms_closeout_governance(
        _PR20_CLOSEOUT_PATH,
        pr19_report=_pr19_report(),
        pr19_gate=_pr19_gate(),
        expected_pr19_source_specific_terms_ref=_pr19_ref(),
    )


@functools.cache
def _legal_review_payload_template() -> dict[str, object]:
    payload = json.loads(_PR21_LEGAL_REVIEW_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _legal_review_payload() -> dict[str, object]:
    return copy.deepcopy(_legal_review_payload_template())


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _candidate(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    candidates = payload["candidate_legal_contract_reviews"]
    assert isinstance(candidates, list)
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
            return candidate
    raise AssertionError(f"missing candidate {candidate_id}")


def test_load_regional_catalog_dedicated_legal_contract_review_accepts_artifact() -> None:
    gate = load_regional_catalog_dedicated_legal_contract_review_governance(
        _PR21_LEGAL_REVIEW_PATH,
        pr20_report=_pr20_report(),
        pr20_gate=_pr20_gate(),
        expected_pr20_closeout_ref=_pr20_ref(),
    )

    assert gate.source == "regional_catalogs"
    assert gate.source_classification == "governance_dedicated_legal_contract_review_only"
    assert gate.pr20_merged_pr == 1815
    assert gate.pr20_next_recommended_lane == "regional_catalog_dedicated_legal_contract_review"
    assert gate.next_recommended_lane == "regional_catalog_dedicated_legal_contract_review_closeout"
    assert [candidate.candidate_id for candidate in gate.candidate_legal_contract_reviews] == (
        _EXPECTED_CANDIDATE_IDS
    )
    assert {
        candidate.legal_approval_status for candidate in gate.candidate_legal_contract_reviews
    } == {"not_approved"}
    assert {
        candidate.source_authority_status for candidate in gate.candidate_legal_contract_reviews
    } == {"blocked_not_authority"}


def test_regional_catalog_dedicated_legal_contract_review_report_contract() -> None:
    report = build_regional_catalog_dedicated_legal_contract_review_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        pr17_identity_path=_PR17_IDENTITY_PATH,
        pr18_provider_terms_path=_PR18_PROVIDER_TERMS_PATH,
        pr19_source_specific_terms_path=_PR19_SOURCE_SPECIFIC_TERMS_PATH,
        pr20_closeout_path=_PR20_CLOSEOUT_PATH,
        legal_review_path=_PR21_LEGAL_REVIEW_PATH,
    )

    assert report["success"] is True
    assert report["validation_errors"] == []
    assert report["pr20_merged_pr"] == 1815
    assert (
        report["pr20_next_recommended_lane"] == "regional_catalog_dedicated_legal_contract_review"
    )
    assert report["network_allowed"] is False
    assert report["api_calls_allowed"] is False
    assert report["provider_use_allowed"] is False
    assert report["source_authority_allowed"] is False
    assert report["nutrition_authority_allowed"] is False
    assert (
        report["next_recommended_lane"]
        == "regional_catalog_dedicated_legal_contract_review_closeout"
    )
    candidate_decisions = report["candidate_decisions"]
    assert isinstance(candidate_decisions, dict)
    assert set(candidate_decisions.values()) == {"review_only_no_source_or_provider_use"}
    evidence_confidence = report["candidate_evidence_confidence"]
    assert isinstance(evidence_confidence, dict)
    assert set(evidence_confidence.values()) == {"low_unverified"}
    legal_status = report["candidate_legal_review_status"]
    assert isinstance(legal_status, dict)
    assert set(legal_status.values()) == {"required_not_approved"}


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("source", "   ", "source"),
        ("source_family", "regional_catalog_wrong", "source_family"),
        ("review_decision", "", "review_decision"),
        ("legal_review_authority", "review_only_not_authority", "legal_review_authority"),
        ("notes", "review-only legal facts remain blocked", "notes"),
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_rejects_controlled_text_drift(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _legal_review_payload()
    payload[field_name] = bad_value

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match=match):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


@pytest.mark.parametrize(
    ("bad_value", "match"),
    (
        ("api_call", "list of strings"),
        (["api_call", ""], "blocked_methods\\[1\\]"),
        (["api_call", "api_call"], "duplicate"),
        ([], "must not be empty"),
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_rejects_blocked_methods_shape(
    bad_value: object,
    match: str,
) -> None:
    payload = _legal_review_payload()
    payload["blocked_methods"] = bad_value

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match=match):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


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
def test_regional_catalog_dedicated_legal_contract_review_rejects_unsafe_flags(
    flag_name: str,
) -> None:
    payload = _legal_review_payload()
    payload[flag_name] = True

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match="unsafe flags"):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


def test_regional_catalog_dedicated_legal_contract_review_rejects_file_only_false() -> None:
    payload = _legal_review_payload()
    payload["file_only"] = False

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match="file_only"):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("schema_version", "food-data-source-review.v1", "schema_version"),
        ("generated_on", "2026/05/25", "YYYY-MM-DD"),
        ("generated_on", "2026-99-25", "YYYY-MM-DD"),
        ("pr20_source_specific_terms_closeout_ref", "docs/architecture/other.json", "pr20_source"),
        ("pr20_merged_pr", True, "integer"),
        ("pr20_merged_pr", 9999, "pr20_merged_pr"),
        ("pr20_merge_marker", "bad", "pr20_merge_marker"),
        ("pr20_next_recommended_lane", "provider_integration", "pr20_next"),
        ("source_classification", "runtime_authority", "source_classification"),
        ("evidence_policy", "source_authority", "evidence_policy"),
        ("external_research_evidence_role", "source_authority", "external_research"),
        ("legal_review_authority", "legal review approved", "approve"),
        ("blocked_methods", ["api_call"], "exactly"),
        ("review_decision", "Provider use approved.", "approve"),
        ("notes", "public references are source authority", "approve"),
        ("role_agent_dispatch_status", "listed_only", "role_agent_dispatch_status"),
        ("experiment_runner_policy", "not_applicable", "experiment_runner_policy"),
        ("next_recommended_lane", "runtime_provider_integration", "next_recommended_lane"),
        ("final_gate_decision", "provider_use_approved", "final_gate_decision"),
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_rejects_malformed_fields(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _legal_review_payload()
    payload[field_name] = bad_value

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match=match):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
            expected_pr20_closeout_ref=_pr20_ref(),
        )


def test_regional_catalog_dedicated_legal_contract_review_rejects_unexpected_keys() -> None:
    payload = _legal_review_payload()
    payload["provider_use_approved"] = True

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match="unexpected keys"):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


@pytest.mark.parametrize("payload", ([], {1: "bad-key"}))
def test_regional_catalog_dedicated_legal_contract_review_rejects_non_mapping(
    payload: object,
) -> None:
    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


def test_regional_catalog_dedicated_legal_contract_review_rejects_candidate_order_drift() -> None:
    payload = _legal_review_payload()
    candidates = payload["candidate_legal_contract_reviews"]
    assert isinstance(candidates, list)
    candidates.reverse()

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match="candidate order"):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


def test_regional_catalog_dedicated_legal_contract_review_rejects_candidate_unexpected_key() -> (
    None
):
    payload = _legal_review_payload()
    _candidate(payload, "kroger")["legal_approval_url"] = "https://example.invalid"

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match="unexpected"):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("candidate_id", "unknown", "unknown candidate_id"),
        ("candidate_name", "Wrong", "candidate_name must match PR20"),
        (
            "provider_route_classification",
            "runtime_provider",
            "provider_route_classification must match PR20",
        ),
        ("allowed_role", "provider_use_approved", "allowed_role"),
        ("next_required_review", "provider_integration", "next_required_review"),
        ("evidence_confidence", "high_verified", "evidence_confidence"),
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
        ("legal_contract_decision", "provider_use_approved", "legal_contract_decision"),
        ("legal_review_status", "legal review approved", "approve"),
        ("contract_review_status", "contract review complete", "approve"),
        ("legal_approval_status", "approved", "legal_approval_status"),
        ("terms_evidence_role", "source_authority", "terms_evidence_role"),
        ("legal_review_authority", "legal approval granted", "approve"),
        ("provider_account_access_status", "verified", "provider_account_access_status"),
        ("contract_permission_status", "approved", "contract_permission_status"),
        ("api_use_permission_status", "api use approved", "approve"),
        ("scraping_permission_status", "scraping allowed", "approve"),
        ("download_permission_status", "downloads approved", "approve"),
        ("cache_permission_status", "approved", "cache_permission_status"),
        ("redistribution_permission_status", "approved", "redistribution_permission_status"),
        ("product_display_permission_status", "approved", "product_display_permission_status"),
        ("attribution_requirement_status", "approved", "attribution_requirement_status"),
        ("source_authority_status", "source authority approved", "approve"),
        ("blocking_reasons", ["API calls allowed."], "approve"),
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_rejects_candidate_drift(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _legal_review_payload()
    _candidate(payload, "kroger")[field_name] = bad_value

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match=match):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


def test_regional_catalog_dedicated_legal_contract_review_validates_pr20_report() -> None:
    report = copy.deepcopy(_pr20_report())
    report["next_recommended_lane"] = "runtime_provider_integration"

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match="PR20 next"):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            _legal_review_payload(),
            pr20_report=report,
            pr20_gate=_pr20_gate(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("success", False, "PR20 closeout report must succeed"),
        ("final_gate_decision", "provider_use_approved", "PR20 final_gate_decision"),
        ("candidate_ids", list(reversed(_EXPECTED_CANDIDATE_IDS)), "PR20 candidate_ids"),
        ("network_allowed", True, "PR20 safety flag drifted"),
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_rejects_pr20_report_drift(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    report = copy.deepcopy(_pr20_report())
    report[field_name] = bad_value

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match=match):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            _legal_review_payload(),
            pr20_report=report,
            pr20_gate=_pr20_gate(),
        )


def test_regional_catalog_dedicated_legal_contract_review_derives_next_lane_from_pr20() -> None:
    gate = _pr20_gate()
    first = gate.candidate_closeout_terms[0]
    bad_first = replace(first, next_required_review="provider_integration")
    bad_gate = replace(
        gate,
        candidate_closeout_terms=(bad_first, *gate.candidate_closeout_terms[1:]),
    )

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match="PR20 next"):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            _legal_review_payload(),
            pr20_report=_pr20_report(),
            pr20_gate=bad_gate,
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("allowed_role", "review_only_provider_use_allowed", "allowed_role"),
        ("terms_document_identity_status", "verified", "terms_document_identity_status"),
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_rejects_pr20_candidate_drift(
    field_name: str,
    bad_value: str,
    match: str,
) -> None:
    gate = _pr20_gate()
    first = gate.candidate_closeout_terms[0]
    if field_name == "allowed_role":
        bad_first = replace(first, allowed_role=bad_value)
    else:
        bad_first = replace(first, terms_document_identity_status=bad_value)
    bad_gate = replace(
        gate,
        candidate_closeout_terms=(bad_first, *gate.candidate_closeout_terms[1:]),
    )

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match=match):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            _legal_review_payload(),
            pr20_report=_pr20_report(),
            pr20_gate=bad_gate,
        )


def test_regional_catalog_dedicated_legal_contract_review_rejects_candidate_list_shape() -> None:
    payload = _legal_review_payload()
    payload["candidate_legal_contract_reviews"] = "not-a-list"

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match="must be a list"):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


def test_regional_catalog_dedicated_legal_contract_review_rejects_duplicate_candidate_id() -> None:
    payload = _legal_review_payload()
    candidates = payload["candidate_legal_contract_reviews"]
    assert isinstance(candidates, list)
    second = copy.deepcopy(candidates[1])
    assert isinstance(second, dict)
    first = candidates[0]
    assert isinstance(first, dict)
    second["candidate_id"] = first["candidate_id"]
    candidates[1] = second

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match="duplicate"):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


def test_regional_catalog_dedicated_legal_contract_review_rejects_blocking_reason_drift() -> None:
    payload = _legal_review_payload()
    _candidate(payload, "kroger")["blocking_reasons"] = ["dedicated review remains incomplete"]

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match="blocking_reasons"):
        parse_regional_catalog_dedicated_legal_contract_review_governance(
            payload,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


def test_regional_catalog_dedicated_legal_contract_review_report_failure_captures_flags(
    tmp_path: Path,
) -> None:
    payload = _legal_review_payload()
    payload["network_allowed"] = True
    bad_path = _write_payload(tmp_path / "bad-pr21.json", payload)

    report = build_regional_catalog_dedicated_legal_contract_review_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        pr17_identity_path=_PR17_IDENTITY_PATH,
        pr18_provider_terms_path=_PR18_PROVIDER_TERMS_PATH,
        pr19_source_specific_terms_path=_PR19_SOURCE_SPECIFIC_TERMS_PATH,
        pr20_closeout_path=_PR20_CLOSEOUT_PATH,
        legal_review_path=bad_path,
    )

    assert report["success"] is False
    assert report["network_allowed"] is True
    assert report["validation_errors"]


def test_regional_catalog_dedicated_legal_contract_review_report_failure_preserves_malformed_flags(
    tmp_path: Path,
) -> None:
    payload = _legal_review_payload()
    payload["network_allowed"] = "true"
    bad_path = _write_payload(tmp_path / "bad-pr21.json", payload)

    report = build_regional_catalog_dedicated_legal_contract_review_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        pr17_identity_path=_PR17_IDENTITY_PATH,
        pr18_provider_terms_path=_PR18_PROVIDER_TERMS_PATH,
        pr19_source_specific_terms_path=_PR19_SOURCE_SPECIFIC_TERMS_PATH,
        pr20_closeout_path=_PR20_CLOSEOUT_PATH,
        legal_review_path=bad_path,
    )

    assert report["success"] is False
    assert report["network_allowed"] == "true"
    assert "network_allowed" in json.dumps(report["validation_errors"])


@pytest.mark.parametrize(
    ("file_contents", "expected_path"),
    (
        ("{not-json", "bad-pr21.json"),
        ("[]", "outside-pr21.json"),
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_report_failure_captures_bad_paths(
    tmp_path: Path,
    file_contents: str,
    expected_path: str,
) -> None:
    bad_path = (tmp_path / expected_path).resolve()
    bad_path.write_text(file_contents, encoding="utf-8")

    report = build_regional_catalog_dedicated_legal_contract_review_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        pr17_identity_path=_PR17_IDENTITY_PATH,
        pr18_provider_terms_path=_PR18_PROVIDER_TERMS_PATH,
        pr19_source_specific_terms_path=_PR19_SOURCE_SPECIFIC_TERMS_PATH,
        pr20_closeout_path=_PR20_CLOSEOUT_PATH,
        legal_review_path=bad_path,
    )

    assert report["success"] is False
    assert report["validation_errors"]


def test_regional_catalog_dedicated_legal_contract_review_report_uses_absolute_outside_repo_path(
    tmp_path: Path,
) -> None:
    outside_catalog_path = (tmp_path / "outside-catalog.json").resolve()
    outside_catalog_path.write_text("[]", encoding="utf-8")

    report = build_regional_catalog_dedicated_legal_contract_review_report(
        catalog_path=outside_catalog_path,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        pr17_identity_path=_PR17_IDENTITY_PATH,
        pr18_provider_terms_path=_PR18_PROVIDER_TERMS_PATH,
        pr19_source_specific_terms_path=_PR19_SOURCE_SPECIFIC_TERMS_PATH,
        pr20_closeout_path=_PR20_CLOSEOUT_PATH,
        legal_review_path=_PR21_LEGAL_REVIEW_PATH,
    )

    assert report["success"] is False
    assert outside_catalog_path.as_posix() in json.dumps(report["validation_errors"])


def test_regional_catalog_dedicated_legal_contract_review_report_failure_captures_missing_path(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing-pr21.json"

    report = build_regional_catalog_dedicated_legal_contract_review_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        pr17_identity_path=_PR17_IDENTITY_PATH,
        pr18_provider_terms_path=_PR18_PROVIDER_TERMS_PATH,
        pr19_source_specific_terms_path=_PR19_SOURCE_SPECIFIC_TERMS_PATH,
        pr20_closeout_path=_PR20_CLOSEOUT_PATH,
        legal_review_path=missing_path,
    )

    assert report["success"] is False
    assert report["validation_errors"]


def test_regional_catalog_dedicated_legal_contract_review_load_rejects_unreadable_json(
    tmp_path: Path,
) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewError, match="Cannot read"):
        load_regional_catalog_dedicated_legal_contract_review_governance(
            bad_path,
            pr20_report=_pr20_report(),
            pr20_gate=_pr20_gate(),
        )


def test_regional_catalog_dedicated_legal_contract_review_cli_success_json() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", _CLI_MODULE, "--json"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(completed.stdout)

    assert payload["success"] is True
    assert payload["validation_errors"] == []
    assert (
        payload["next_recommended_lane"]
        == "regional_catalog_dedicated_legal_contract_review_closeout"
    )


def test_regional_catalog_dedicated_legal_contract_review_cli_success_text() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", _CLI_MODULE],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert "food_source_regional_catalog_dedicated_legal_contract_review: PASS" in (
        completed.stdout
    )


def test_regional_catalog_dedicated_legal_contract_review_cli_failure(tmp_path: Path) -> None:
    payload = _legal_review_payload()
    payload["network_allowed"] = True
    bad_path = _write_payload(tmp_path / "bad-pr21.json", payload)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--legal-review",
            str(bad_path),
        ],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 1
    assert "food_source_regional_catalog_dedicated_legal_contract_review: FAIL" in (
        completed.stdout
    )
    assert "network_allowed" in completed.stdout
