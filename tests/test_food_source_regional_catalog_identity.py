"""Tests for the deterministic PR17 regional catalog identity/license gate."""

from __future__ import annotations

import ast
import copy
from dataclasses import replace
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources import regional_catalog_identity
from core.food_sources.preference_mapping_closeout import build_preference_mapping_closeout_report
from core.food_sources.regional_catalog_identity import (
    RegionalCatalogIdentityError,
    build_regional_catalog_identity_report,
    load_regional_catalog_identity_governance,
    parse_regional_catalog_identity_governance,
)
from core.food_sources.source_catalog import SourceCatalog, SourceCatalogEntry, load_source_catalog
from core.food_sources.source_gap_audit import (
    CoverageDomainDecision,
    SourceGapAudit,
    SourceGapDecision,
    load_source_gap_audit,
)
from core.food_sources.source_onboarding import (
    SourceOnboarding,
    SourceOnboardingEntry,
    load_source_onboarding,
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
_REGIONAL_IDENTITY_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_REGIONAL_CATALOG_IDENTITY_LICENSE_PR17_2026-05-19.json"
)
_CLI_MODULE = "scripts.food_source_regional_catalog_identity"


def _catalog() -> SourceCatalog:
    return load_source_catalog(_CATALOG_PATH)


def _onboarding() -> SourceOnboarding:
    return load_source_onboarding(
        _ONBOARDING_PATH,
        catalog=_catalog(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
    )


def _coverage() -> SourceGapAudit:
    return load_source_gap_audit(
        _COVERAGE_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
    )


def _replace_regional_catalog_entry(**changes: object) -> SourceCatalog:
    catalog = _catalog()
    sources: list[SourceCatalogEntry] = []
    for source in catalog.sources:
        if source.source == "regional_catalogs":
            sources.append(replace(source, **changes))
        else:
            sources.append(source)
    return replace(catalog, sources=tuple(sources))


def _replace_regional_onboarding_entry(**changes: object) -> SourceOnboarding:
    onboarding = _onboarding()
    sources: list[SourceOnboardingEntry] = []
    for source in onboarding.sources:
        if source.source == "regional_catalogs":
            sources.append(replace(source, **changes))
        else:
            sources.append(source)
    return replace(onboarding, sources=tuple(sources))


def _replace_regional_coverage_domain(**changes: object) -> SourceGapAudit:
    coverage = _coverage()
    domains: list[CoverageDomainDecision] = []
    for domain in coverage.coverage_domains:
        if domain.domain == "regional_local_products":
            domains.append(replace(domain, **changes))
        else:
            domains.append(domain)
    return replace(coverage, coverage_domains=tuple(domains))


def _replace_regional_source_gap(**changes: object) -> SourceGapAudit:
    coverage = _coverage()
    decisions: list[SourceGapDecision] = []
    for decision in coverage.source_gap_decisions:
        if decision.source == "regional_catalogs":
            decisions.append(replace(decision, **changes))
        else:
            decisions.append(decision)
    return replace(coverage, source_gap_decisions=tuple(decisions))


def _pr16_report() -> dict[str, object]:
    return build_preference_mapping_closeout_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        closeout_path=_PR16_CLOSEOUT_PATH,
    )


def _identity_payload() -> dict[str, object]:
    return json.loads(_REGIONAL_IDENTITY_PATH.read_text(encoding="utf-8"))


def _catalog_payload() -> dict[str, object]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _onboarding_payload() -> dict[str, object]:
    return json.loads(_ONBOARDING_PATH.read_text(encoding="utf-8"))


def _coverage_payload() -> dict[str, object]:
    return json.loads(_COVERAGE_PATH.read_text(encoding="utf-8"))


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _candidate(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    candidates = payload["candidate_reviews"]
    assert isinstance(candidates, list)
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
            return candidate
    raise AssertionError(f"missing candidate {candidate_id}")


def _mutate_catalog_source(key: str, value: object, tmp_path: Path) -> Path:
    payload = _catalog_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == "regional_catalogs":
            source[key] = value
            break
    return _write_payload(tmp_path / "catalog.json", payload)


def _mutate_onboarding_source(key: str, value: object, tmp_path: Path) -> Path:
    payload = _onboarding_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == "regional_catalogs":
            source[key] = value
            break
    return _write_payload(tmp_path / "onboarding.json", payload)


def _mutate_coverage_domain(key: str, value: object, tmp_path: Path) -> Path:
    payload = _coverage_payload()
    domains = payload["coverage_domains"]
    assert isinstance(domains, list)
    for domain in domains:
        if isinstance(domain, dict) and domain.get("domain") == "regional_local_products":
            domain[key] = value
            break
    return _write_payload(tmp_path / "coverage.json", payload)


def _mutate_coverage_source(key: str, value: object, tmp_path: Path) -> Path:
    payload = _coverage_payload()
    decisions = payload["source_gap_decisions"]
    assert isinstance(decisions, list)
    for decision in decisions:
        if isinstance(decision, dict) and decision.get("source") == "regional_catalogs":
            decision[key] = value
            break
    return _write_payload(tmp_path / "coverage.json", payload)


def test_load_regional_catalog_identity_accepts_canonical_artifact() -> None:
    gate = load_regional_catalog_identity_governance(
        _REGIONAL_IDENTITY_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        coverage=_coverage(),
        pr16_report=_pr16_report(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
        expected_coverage_ref="docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json",
        expected_pr16_closeout_ref=(
            "docs/architecture/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_CLOSEOUT_PR16_2026-05-19.json"
        ),
    )

    assert gate.source == "regional_catalogs"
    assert gate.source_classification == "unresolved"
    assert gate.next_recommended_lane == "regional_catalog_provider_terms_matrix"
    assert [candidate.candidate_id for candidate in gate.candidate_reviews] == [
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


def test_regional_catalog_identity_report_is_deterministic_json_contract() -> None:
    report = build_regional_catalog_identity_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        regional_identity_path=_REGIONAL_IDENTITY_PATH,
    )

    assert report["success"] is True
    assert report["source"] == "regional_catalogs"
    assert report["network_allowed"] is False
    assert report["api_calls_allowed"] is False
    assert report["seller_api_use_allowed"] is False
    assert report["partner_api_use_allowed"] is False
    assert report["nutrition_authority_allowed"] is False
    assert report["validation_errors"] == []
    assert report["next_recommended_lane"] == "regional_catalog_provider_terms_matrix"
    assert report["candidate_decisions"] == {
        "data_europa_national_portals": "open_data_portal_review_candidate_only",
        "kroger": "regional_price_catalog_candidate_only",
        "walmart": "regional_price_catalog_candidate_only",
        "pepesto_grocery": "commercial_eu_catalog_candidate_only",
        "pricesapi": "global_price_aggregator_candidate_only",
        "yandex_eda": "partner_menu_candidate_only",
        "wildberries": "seller_terms_candidate_only",
        "ozon": "seller_terms_candidate_only",
        "apify_scraping_providers": "blocked_for_pr17",
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
def test_regional_catalog_identity_rejects_unsafe_flags(flag_name: str) -> None:
    payload = _identity_payload()
    payload[flag_name] = True

    with pytest.raises(RegionalCatalogIdentityError, match="unsafe flags"):
        parse_regional_catalog_identity_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr16_report=_pr16_report(),
        )


def test_regional_catalog_identity_rejects_file_only_false() -> None:
    payload = _identity_payload()
    payload["file_only"] = False

    with pytest.raises(RegionalCatalogIdentityError, match="file_only"):
        parse_regional_catalog_identity_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr16_report=_pr16_report(),
        )


def test_regional_catalog_identity_rejects_unexpected_keys() -> None:
    payload = _identity_payload()
    payload["api_use_approved"] = True

    with pytest.raises(RegionalCatalogIdentityError, match="unexpected keys"):
        parse_regional_catalog_identity_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr16_report=_pr16_report(),
        )


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    (
        ("license_status", "approved"),
        ("retrieval_contract_status", "approved"),
        ("attribution_decision", "approved"),
        ("cache_decision", "approved"),
        ("redistribution_decision", "approved"),
        ("nutrient_schema_status", "approved"),
        ("candidate_name", "Different Provider"),
        ("country_or_market", "Different Market"),
        ("source_url", "https://example.invalid/changed"),
    ),
)
def test_regional_catalog_identity_rejects_candidate_approval_drift(
    field_name: str,
    field_value: str,
) -> None:
    payload = _identity_payload()
    _candidate(payload, "data_europa_national_portals")[field_name] = field_value

    with pytest.raises(RegionalCatalogIdentityError, match=field_name):
        parse_regional_catalog_identity_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr16_report=_pr16_report(),
        )


def test_regional_catalog_identity_rejects_duplicate_candidate_ids() -> None:
    payload = _identity_payload()
    candidates = payload["candidate_reviews"]
    assert isinstance(candidates, list)
    duplicate = copy.deepcopy(candidates[0])
    candidates[-1] = duplicate

    with pytest.raises(RegionalCatalogIdentityError, match="candidate_reviews"):
        parse_regional_catalog_identity_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr16_report=_pr16_report(),
        )


@pytest.mark.parametrize(
    "bad_notes",
    (
        "API calls allowed for regional catalog checks.",
        "Seller API use may be used for Ozon.",
        "Partner API access can be used for Yandex EDA.",
        "Data portal is source authority for product display.",
        "Marketplace terms approved for runtime authority.",
        "Cache authority enabled for regional catalogs.",
        "Nutrition authority granted to Kroger.",
        "Public dataset claim approved for regional catalogs.",
        "Automated collection allowed for regional catalogs.",
        "DigitalOcean Postgres load enabled for regional catalogs.",
        "Seller API is not blocked and approved for catalog enrichment.",
        "Automated collection is never forbidden and allowed.",
        "API calls are not approved but allowed for regional catalog checks.",
        "Seller API use is not authorized but permitted for Ozon.",
        "Partner API access is not approved but can be used for Yandex EDA.",
        "Public dataset claim is unapproved but usable for regional catalogs.",
        "DigitalOcean Postgres load is not approved but enabled for regional catalogs.",
        "Seller API is not approved but available for testing.",
        "Seller API use is blocked for PR17 governance evidence and provider terms but still approved for limited staging sync.",
        "Seller APIs approved for regional catalog checks.",
        "Partner APIs allowed for regional catalog checks.",
        "May be used seller api for testing.",
        "Relied on seller api only.",
        "We approve seller api use for tests.",
        "We allow seller api use for tests.",
        "We will use seller api for tests.",
        "API approved for testing.",
        "API may be used for testing.",
        "Seller account access allowed for testing.",
        "Partner menu access allowed for testing.",
        "Provider API allowed for testing.",
        "Seller api is used for tests.",
        "Seller API use is blocked for PR17 but okay for manual testing.",
        "Seller API access receives approval for staging.",
        "Ozon Seller API can be queried manually.",
        "Regional catalogs may call provider APIs for license discovery.",
        "Seller API use has approval for Ozon.",
        "Source authority: data portal.",
        "Data portal equals source authority.",
        "data.europa.eu is the source authority.",
        "Data portal is not source authority but becomes product display.",
        "Data portal is not source authority and is product display.",
        "Data portal is not source authority but equals nutrition authority.",
        "Data portal is not a source authority but serves as product display.",
        "Partner access allowed for Yandex EDA.",
        "Seller access approved for Ozon.",
        "Seller or partner access allowed for tests.",
        "Seller API has the green light for testing.",
        "Partner access gets a green light for staging.",
        "Regional catalogs have the go ahead for product display.",
        "Seller API is cleared for tests.",
        "Seller API use is blocked for PR17 governance evidence, legal review, provider terms, license review, identity review, source family review, cache review, attribution review, data quality review, freshness review, locale review, unit normalization review, nutrient schema review, internal routing review, but approved for staging.",
        "Data portal is not source authority for PR17, but after exact dataset review and country terms mapping it becomes product display.",
        "Seller API is blocked for PR17. It is approved for staging.",
        "Regional catalog candidates remain review context only. This candidate is approved for staging.",
        "Candidate is approved for staging after manual review.",
        "This can be used for staging after manual review.",
        "Seller account access remains unapproved. It is approved for manual tests.",
        "Seller APIs remain blocked for PR17. They are approved for staging.",
        "Regional catalog candidates remain review context only. They are approved for staging.",
        "Ozon and Wildberries remain seller terms evidence. They can be used for staging.",
        "The providers remain unapproved. They have approval for manual tests.",
        "Those providers can be used for staging.",
    ),
)
def test_regional_catalog_identity_rejects_authority_prose(bad_notes: str) -> None:
    payload = _identity_payload()
    payload["notes"] = bad_notes

    with pytest.raises(RegionalCatalogIdentityError, match="notes"):
        parse_regional_catalog_identity_governance(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr16_report=_pr16_report(),
        )


@pytest.mark.parametrize(
    "safe_notes",
    (
        "API calls are not approved for regional catalog checks.",
        "Public dataset claim remains unapproved for regional catalogs.",
        "Automated collection is blocked for regional catalogs.",
        "DigitalOcean Postgres load is not allowed for PR17.",
        "Data portal is not source authority for PR17.",
        "Data portal is not a source authority for PR17.",
        "Data portal is never a source authority for PR17.",
        "Data portal is not source authority for product display.",
        "Nutrition authority for regional catalogs is not approved.",
        "API calls are not approved for ingestion; documentation is available in appendix.",
    ),
)
def test_regional_catalog_identity_allows_negated_authority_prose(safe_notes: str) -> None:
    payload = _identity_payload()
    payload["notes"] = safe_notes

    gate = parse_regional_catalog_identity_governance(
        payload,
        catalog=_catalog(),
        onboarding=_onboarding(),
        coverage=_coverage(),
        pr16_report=_pr16_report(),
    )

    assert gate.notes == safe_notes


@pytest.mark.parametrize(
    ("key", "value"),
    (
        ("source_classification", "current"),
        ("status", "active"),
        ("license_review", "approved"),
        ("active_update_source", True),
    ),
)
def test_regional_catalog_identity_report_rejects_catalog_drift(
    key: str,
    value: object,
    tmp_path: Path,
) -> None:
    report = build_regional_catalog_identity_report(
        catalog_path=_mutate_catalog_source(key, value, tmp_path),
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        regional_identity_path=_REGIONAL_IDENTITY_PATH,
    )

    assert report["success"] is False
    assert report["validation_errors"]


def test_regional_catalog_identity_rejects_pr3_catalog_policy_drift_directly() -> None:
    with pytest.raises(RegionalCatalogIdentityError, match="regional catalog catalog policy drift"):
        parse_regional_catalog_identity_governance(
            _identity_payload(),
            catalog=_replace_regional_catalog_entry(status="deferred"),
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr16_report=_pr16_report(),
        )


@pytest.mark.parametrize(
    ("key", "value"),
    (
        ("onboarding_status", "eligible_preflight"),
        ("cache_decision", "approved"),
        ("redistribution_decision", "approved"),
        ("display_decision", "approved"),
    ),
)
def test_regional_catalog_identity_report_rejects_onboarding_drift(
    key: str,
    value: object,
    tmp_path: Path,
) -> None:
    report = build_regional_catalog_identity_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_mutate_onboarding_source(key, value, tmp_path),
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        regional_identity_path=_REGIONAL_IDENTITY_PATH,
    )

    assert report["success"] is False
    assert report["validation_errors"]


def test_regional_catalog_identity_rejects_pr5_onboarding_policy_drift_directly() -> None:
    with pytest.raises(
        RegionalCatalogIdentityError,
        match="regional catalog onboarding policy drift",
    ):
        parse_regional_catalog_identity_governance(
            _identity_payload(),
            catalog=_catalog(),
            onboarding=_replace_regional_onboarding_entry(cache_decision="legacy_review_only"),
            coverage=_coverage(),
            pr16_report=_pr16_report(),
        )


@pytest.mark.parametrize(
    ("key", "value"),
    (
        ("coverage_decision", "adequate_baseline"),
        ("authority_decision", "approved"),
        ("next_action", "runtime_catalog_review"),
        ("approved_ingest", True),
        ("approved_runtime_authority", True),
    ),
)
def test_regional_catalog_identity_report_rejects_pr11_domain_drift(
    key: str,
    value: object,
    tmp_path: Path,
) -> None:
    report = build_regional_catalog_identity_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_mutate_coverage_domain(key, value, tmp_path),
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        regional_identity_path=_REGIONAL_IDENTITY_PATH,
    )

    assert report["success"] is False
    assert "regional_local_products" in str(report["validation_errors"][0])


def test_regional_catalog_identity_rejects_pr11_domain_handoff_drift_directly() -> None:
    with pytest.raises(
        RegionalCatalogIdentityError,
        match="PR11 regional_local_products next_action",
    ):
        parse_regional_catalog_identity_governance(
            _identity_payload(),
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_replace_regional_coverage_domain(next_action="runtime_catalog_review"),
            pr16_report=_pr16_report(),
        )


def test_regional_catalog_identity_rejects_pr11_domain_authority_drift_directly() -> None:
    with pytest.raises(
        RegionalCatalogIdentityError,
        match="regional_local_products must stay unapproved",
    ):
        parse_regional_catalog_identity_governance(
            _identity_payload(),
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_replace_regional_coverage_domain(approved_ingest=True),
            pr16_report=_pr16_report(),
        )


@pytest.mark.parametrize(
    ("key", "value"),
    (
        ("decision", "approved"),
        ("allowed_role", "runtime_source_authority"),
        ("api_calls_allowed", True),
        ("scraping_allowed", True),
        ("paid_source_use_allowed", True),
        ("approved_ingest", True),
    ),
)
def test_regional_catalog_identity_report_rejects_pr11_source_drift(
    key: str,
    value: object,
    tmp_path: Path,
) -> None:
    report = build_regional_catalog_identity_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_mutate_coverage_source(key, value, tmp_path),
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        pr16_closeout_path=_PR16_CLOSEOUT_PATH,
        regional_identity_path=_REGIONAL_IDENTITY_PATH,
    )

    assert report["success"] is False
    assert "regional_catalogs" in str(report["validation_errors"][0])


def test_regional_catalog_identity_rejects_pr11_source_handoff_drift_directly() -> None:
    with pytest.raises(
        RegionalCatalogIdentityError,
        match="PR11 regional_catalogs blocking_reasons",
    ):
        parse_regional_catalog_identity_governance(
            _identity_payload(),
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_replace_regional_source_gap(blocking_reasons=("provider terms approved",)),
            pr16_report=_pr16_report(),
        )


def test_regional_catalog_identity_rejects_pr11_source_role_drift_directly() -> None:
    with pytest.raises(
        RegionalCatalogIdentityError,
        match="PR11 regional_catalogs must remain identity/license review",
    ):
        parse_regional_catalog_identity_governance(
            _identity_payload(),
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_replace_regional_source_gap(decision="approved"),
            pr16_report=_pr16_report(),
        )


def test_regional_catalog_identity_rejects_pr11_source_authority_drift_directly() -> None:
    with pytest.raises(
        RegionalCatalogIdentityError,
        match="PR11 regional_catalogs must not approve source use",
    ):
        parse_regional_catalog_identity_governance(
            _identity_payload(),
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_replace_regional_source_gap(api_calls_allowed=True),
            pr16_report=_pr16_report(),
        )


def test_regional_catalog_identity_rejects_pr16_handoff_drift() -> None:
    pr16_report = _pr16_report()
    pr16_report["next_substantive_lane"] = "paid_provider_runtime_review"

    with pytest.raises(RegionalCatalogIdentityError, match="PR16 next_substantive_lane"):
        parse_regional_catalog_identity_governance(
            _identity_payload(),
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr16_report=pr16_report,
        )


@pytest.mark.parametrize(
    "flag_name",
    (
        "network_allowed",
        "automation_allowed",
        "provider_integration_allowed",
        "public_dataset_claim_allowed",
        "seller_api_use_allowed",
        "partner_api_use_allowed",
    ),
)
def test_regional_catalog_identity_rejects_incomplete_pr16_safety_report(
    flag_name: str,
) -> None:
    pr16_report = _pr16_report()
    del pr16_report[flag_name]

    with pytest.raises(RegionalCatalogIdentityError, match=f"PR16 report {flag_name}"):
        parse_regional_catalog_identity_governance(
            _identity_payload(),
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr16_report=pr16_report,
        )


@pytest.mark.parametrize(
    "flag_name",
    (
        "automation_allowed",
        "provider_integration_allowed",
        "public_dataset_claim_allowed",
        "seller_api_use_allowed",
        "partner_api_use_allowed",
    ),
)
def test_regional_catalog_identity_rejects_unsafe_pr16_safety_report(
    flag_name: str,
) -> None:
    pr16_report = _pr16_report()
    pr16_report[flag_name] = True

    with pytest.raises(RegionalCatalogIdentityError, match=f"PR16 report {flag_name}"):
        parse_regional_catalog_identity_governance(
            _identity_payload(),
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr16_report=pr16_report,
        )


@pytest.mark.parametrize(
    ("flag_name", "flag_value"),
    (
        ("file_only", 1),
        ("network_allowed", 0),
        ("seller_api_use_allowed", 0),
        ("partner_api_use_allowed", 0),
    ),
)
def test_regional_catalog_identity_rejects_non_bool_pr16_safety_report(
    flag_name: str,
    flag_value: int,
) -> None:
    pr16_report = _pr16_report()
    pr16_report[flag_name] = flag_value

    with pytest.raises(RegionalCatalogIdentityError, match=f"PR16 report {flag_name}"):
        parse_regional_catalog_identity_governance(
            _identity_payload(),
            catalog=_catalog(),
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr16_report=pr16_report,
        )


def test_regional_catalog_identity_cli_is_file_only_and_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://must-not-be-used.invalid/db")
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
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
            "--recipe-dish-corpus",
            str(_RECIPE_DISH_CORPUS_PATH),
            "--preference-mapping",
            str(_PREFERENCE_MAPPING_PATH),
            "--pr16-closeout",
            str(_PR16_CLOSEOUT_PATH),
            "--regional-identity",
            str(_REGIONAL_IDENTITY_PATH),
            "--json",
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(_REPO_ROOT)},
        check=True,
        text=True,
        capture_output=True,
    )
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["source"] == "regional_catalogs"
    assert payload["api_calls_allowed"] is False
    assert payload["seller_api_use_allowed"] is False
    assert payload["validation_errors"] == []
    assert result.stderr == ""
    assert after == before


def test_regional_catalog_identity_cli_returns_nonzero_for_invalid_payload(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad_identity.json"
    payload = _identity_payload()
    payload["api_calls_allowed"] = True
    bad_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--regional-identity",
            str(bad_path),
            "--json",
        ],
        cwd=_REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["success"] is False
    assert payload["api_calls_allowed"] is False


def test_regional_catalog_identity_cli_prints_validation_errors_without_json(
    tmp_path: Path,
) -> None:
    bad_path = tmp_path / "bad_identity.json"
    payload = _identity_payload()
    payload["seller_api_use_allowed"] = True
    bad_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", _CLI_MODULE, "--regional-identity", str(bad_path)],
        cwd=_REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "food_source_regional_catalog_identity: FAIL" in result.stdout
    assert "Validation errors:" in result.stdout
    assert "seller_api_use_allowed" in result.stdout


def test_regional_catalog_identity_has_no_network_db_provider_or_subprocess_imports() -> None:
    source_text = Path(regional_catalog_identity.__file__).read_text(encoding="utf-8")
    syntax_tree = ast.parse(source_text)

    blocked_roots = {
        "requests",
        "httpx",
        "psycopg",
        "sqlalchemy",
        "digitalocean",
        "subprocess",
        "socket",
    }
    blocked_full_imports = {"urllib.request", "sqlite3"}
    imported_roots: set[str] = set()
    imported_full: set[str] = set()
    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_full.add(alias.name)
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_full.add(node.module)
            imported_roots.add(node.module.split(".")[0])
            imported_full.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert imported_roots.isdisjoint(blocked_roots)
    assert imported_full.isdisjoint(blocked_full_imports)
