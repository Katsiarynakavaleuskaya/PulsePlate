"""Tests for the deterministic PR20 source-specific terms closeout gate."""

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
    RegionalCatalogSourceSpecificTermsCloseoutError,
    build_regional_catalog_source_specific_terms_closeout_report,
    load_regional_catalog_source_specific_terms_closeout_governance,
    parse_regional_catalog_source_specific_terms_closeout_governance,
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
_CLI_MODULE = "scripts.food_source_regional_catalog_source_specific_terms_closeout"


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
def _closeout_payload_template() -> dict[str, object]:
    payload = json.loads(_PR20_CLOSEOUT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _closeout_payload() -> dict[str, object]:
    return copy.deepcopy(_closeout_payload_template())


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _candidate(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    candidates = payload["candidate_closeout_terms"]
    assert isinstance(candidates, list)
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
            return candidate
    raise AssertionError(f"missing candidate {candidate_id}")


def test_load_regional_catalog_source_specific_terms_closeout_accepts_artifact() -> None:
    gate = load_regional_catalog_source_specific_terms_closeout_governance(
        _PR20_CLOSEOUT_PATH,
        pr19_report=_pr19_report(),
        pr19_gate=_pr19_gate(),
        expected_pr19_source_specific_terms_ref=_pr19_ref(),
    )

    assert gate.source == "regional_catalogs"
    assert gate.source_classification == "governance_closeout_only"
    assert gate.pr19_merged_pr == 1793
    assert gate.pr19_next_recommended_lane == "regional_catalog_source_specific_terms_closeout"
    assert gate.next_recommended_lane == "regional_catalog_dedicated_legal_contract_review"
    assert [candidate.candidate_id for candidate in gate.candidate_closeout_terms] == [
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


def test_regional_catalog_source_specific_terms_closeout_report_contract() -> None:
    report = build_regional_catalog_source_specific_terms_closeout_report(
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

    assert report["success"] is True
    assert report["validation_errors"] == []
    assert report["pr19_merged_pr"] == 1793
    assert report["pr19_next_recommended_lane"] == "regional_catalog_source_specific_terms_closeout"
    assert report["network_allowed"] is False
    assert report["api_calls_allowed"] is False
    assert report["provider_use_allowed"] is False
    assert report["source_authority_allowed"] is False
    assert report["nutrition_authority_allowed"] is False
    assert report["next_recommended_lane"] == "regional_catalog_dedicated_legal_contract_review"
    candidate_decisions = report["candidate_decisions"]
    assert isinstance(candidate_decisions, dict)
    assert set(candidate_decisions.values()) == {"review_only_no_provider_use"}
    evidence_confidence = report["candidate_evidence_confidence"]
    assert isinstance(evidence_confidence, dict)
    assert set(evidence_confidence.values()) == {"low_unverified"}


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
def test_regional_catalog_source_specific_terms_closeout_rejects_unsafe_flags(
    flag_name: str,
) -> None:
    payload = _closeout_payload()
    payload[flag_name] = True

    with pytest.raises(RegionalCatalogSourceSpecificTermsCloseoutError, match="unsafe flags"):
        parse_regional_catalog_source_specific_terms_closeout_governance(
            payload,
            pr19_report=_pr19_report(),
            pr19_gate=_pr19_gate(),
        )


def test_regional_catalog_source_specific_terms_closeout_rejects_file_only_false() -> None:
    payload = _closeout_payload()
    payload["file_only"] = False

    with pytest.raises(RegionalCatalogSourceSpecificTermsCloseoutError, match="file_only"):
        parse_regional_catalog_source_specific_terms_closeout_governance(
            payload,
            pr19_report=_pr19_report(),
            pr19_gate=_pr19_gate(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("schema_version", "food-data-source-closeout.v1", "schema_version"),
        ("generated_on", "2026/05/24", "YYYY-MM-DD"),
        ("generated_on", "2026-99-24", "YYYY-MM-DD"),
        ("pr19_source_specific_terms_ref", "docs/architecture/other.json", "pr19_source"),
        ("pr19_merged_pr", True, "integer"),
        ("pr19_merged_pr", 9999, "pr19_merged_pr"),
        ("pr19_merge_marker", "bad", "pr19_merge_marker"),
        ("pr19_next_recommended_lane", "provider_integration", "pr19_next"),
        ("blocked_methods", ["api_call"], "exactly"),
        ("closeout_decision", "Provider use approved.", "approve"),
        ("notes", "report is authority", "approve"),
        ("role_agent_dispatch_status", "listed_only", "role_agent_dispatch_status"),
        ("experiment_runner_policy", "not_applicable", "experiment_runner_policy"),
        ("next_recommended_lane", "runtime_provider_integration", "next_recommended_lane"),
        ("final_gate_decision", "provider_use_approved", "final_gate_decision"),
    ),
)
def test_regional_catalog_source_specific_terms_closeout_rejects_malformed_fields(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _closeout_payload()
    payload[field_name] = bad_value

    with pytest.raises(RegionalCatalogSourceSpecificTermsCloseoutError, match=match):
        parse_regional_catalog_source_specific_terms_closeout_governance(
            payload,
            pr19_report=_pr19_report(),
            pr19_gate=_pr19_gate(),
            expected_pr19_source_specific_terms_ref=_pr19_ref(),
        )


def test_regional_catalog_source_specific_terms_closeout_rejects_unexpected_keys() -> None:
    payload = _closeout_payload()
    payload["provider_use_approved"] = True

    with pytest.raises(RegionalCatalogSourceSpecificTermsCloseoutError, match="unexpected keys"):
        parse_regional_catalog_source_specific_terms_closeout_governance(
            payload,
            pr19_report=_pr19_report(),
            pr19_gate=_pr19_gate(),
        )


@pytest.mark.parametrize("payload", ([], {1: "bad-key"}))
def test_regional_catalog_source_specific_terms_closeout_rejects_non_mapping(
    payload: object,
) -> None:
    with pytest.raises(RegionalCatalogSourceSpecificTermsCloseoutError):
        parse_regional_catalog_source_specific_terms_closeout_governance(
            payload,
            pr19_report=_pr19_report(),
            pr19_gate=_pr19_gate(),
        )


def test_regional_catalog_source_specific_terms_closeout_rejects_candidate_order_drift() -> None:
    payload = _closeout_payload()
    candidates = payload["candidate_closeout_terms"]
    assert isinstance(candidates, list)
    candidates.reverse()

    with pytest.raises(RegionalCatalogSourceSpecificTermsCloseoutError, match="candidate order"):
        parse_regional_catalog_source_specific_terms_closeout_governance(
            payload,
            pr19_report=_pr19_report(),
            pr19_gate=_pr19_gate(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("candidate_id", "unknown", "unknown candidate_id"),
        ("candidate_name", "Wrong", "candidate_name must match PR19"),
        (
            "provider_route_classification",
            "runtime_provider",
            "provider_route_classification must match PR19",
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
        ("blocking_reasons", ["API calls allowed."], "approve"),
        ("closeout_status", "provider_use_approved", "closeout_status"),
        ("legal_contract_review_status", "complete", "legal_contract_review_status"),
    ),
)
def test_regional_catalog_source_specific_terms_closeout_rejects_candidate_drift(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _closeout_payload()
    _candidate(payload, "kroger")[field_name] = bad_value

    with pytest.raises(RegionalCatalogSourceSpecificTermsCloseoutError, match=match):
        parse_regional_catalog_source_specific_terms_closeout_governance(
            payload,
            pr19_report=_pr19_report(),
            pr19_gate=_pr19_gate(),
        )


def test_regional_catalog_source_specific_terms_closeout_validates_pr19_report() -> None:
    report = _pr19_report()
    report["next_recommended_lane"] = "runtime_provider_integration"

    with pytest.raises(RegionalCatalogSourceSpecificTermsCloseoutError, match="PR19 next"):
        parse_regional_catalog_source_specific_terms_closeout_governance(
            _closeout_payload(),
            pr19_report=report,
            pr19_gate=_pr19_gate(),
        )


def test_regional_catalog_source_specific_terms_closeout_derives_next_lane_from_pr19() -> None:
    gate = _pr19_gate()
    first = gate.candidate_source_specific_terms[0]
    bad_first = replace(first, next_required_review="provider_integration")
    bad_gate = replace(
        gate,
        candidate_source_specific_terms=(bad_first, *gate.candidate_source_specific_terms[1:]),
    )

    with pytest.raises(RegionalCatalogSourceSpecificTermsCloseoutError, match="PR19 next"):
        parse_regional_catalog_source_specific_terms_closeout_governance(
            _closeout_payload(),
            pr19_report=_pr19_report(),
            pr19_gate=bad_gate,
        )


def test_regional_catalog_source_specific_terms_closeout_cli_success_json() -> None:
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
    assert payload["next_recommended_lane"] == "regional_catalog_dedicated_legal_contract_review"


def test_regional_catalog_source_specific_terms_closeout_cli_failure(tmp_path: Path) -> None:
    payload = _closeout_payload()
    payload["network_allowed"] = True
    bad_path = _write_payload(tmp_path / "bad-pr20.json", payload)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--closeout",
            str(bad_path),
        ],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "food_source_regional_catalog_source_specific_terms_closeout: FAIL" in (completed.stdout)
    assert "network_allowed" in completed.stdout
