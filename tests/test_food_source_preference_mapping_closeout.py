"""Tests for the deterministic PR16 preference mapping closeout gate."""

from __future__ import annotations

import copy
from dataclasses import replace
import functools
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources.preference_mapping_closeout import (
    PreferenceMappingCloseoutError,
    build_preference_mapping_closeout_report,
    load_preference_mapping_closeout_governance,
    parse_preference_mapping_closeout_governance,
)
from core.food_sources.preference_recipe_mapping import (
    PreferenceRecipeMappingGovernance,
    load_preference_recipe_mapping_governance,
)
from core.food_sources.recipe_dish_corpus import load_recipe_dish_corpus_governance
from core.food_sources.recipe_dish_corpus import RecipeDishCorpusGovernance
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
_CLOSEOUT_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_PREFERENCE_RECIPE_MAPPING_CLOSEOUT_PR16_2026-05-19.json"
)
_CLI_MODULE = "scripts.food_source_preference_mapping_closeout"
_CLI_TIMEOUT_SECONDS = 30


@functools.cache
def _catalog() -> SourceCatalog:
    return load_source_catalog(_CATALOG_PATH)


@functools.cache
def _onboarding() -> SourceOnboarding:
    return load_source_onboarding(
        _ONBOARDING_PATH,
        catalog=_catalog(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
    )


@functools.cache
def _coverage() -> SourceGapAudit:
    return load_source_gap_audit(
        _COVERAGE_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
    )


@functools.cache
def _recipe_dish_corpus() -> RecipeDishCorpusGovernance:
    return load_recipe_dish_corpus_governance(
        _RECIPE_DISH_CORPUS_PATH,
        onboarding=_onboarding(),
        coverage=_coverage(),
    )


@functools.cache
def _preference_mapping() -> PreferenceRecipeMappingGovernance:
    return load_preference_recipe_mapping_governance(
        _PREFERENCE_MAPPING_PATH,
        coverage=_coverage(),
        recipe_dish_corpus=_recipe_dish_corpus(),
        expected_coverage_ref="docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json",
        expected_recipe_dish_corpus_ref=(
            "docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json"
        ),
    )


@functools.cache
def _closeout_payload_template() -> dict[str, object]:
    payload = json.loads(_CLOSEOUT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _closeout_payload() -> dict[str, object]:
    return copy.deepcopy(_closeout_payload_template())


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _coverage_with_regional_domain(
    *,
    coverage_decision: str | None = None,
    primary_sources: tuple[str, ...] | None = None,
    auxiliary_sources: tuple[str, ...] | None = None,
    gap_status: str | None = None,
    authority_decision: str | None = None,
    next_action: str | None = None,
    approved_ingest: bool | None = None,
    approved_runtime_authority: bool | None = None,
    notes: str | None = None,
) -> SourceGapAudit:
    coverage = copy.deepcopy(_coverage())
    domains = tuple(
        (
            replace(
                domain,
                coverage_decision=(
                    domain.coverage_decision if coverage_decision is None else coverage_decision
                ),
                primary_sources=(
                    domain.primary_sources if primary_sources is None else primary_sources
                ),
                auxiliary_sources=(
                    domain.auxiliary_sources if auxiliary_sources is None else auxiliary_sources
                ),
                gap_status=domain.gap_status if gap_status is None else gap_status,
                authority_decision=(
                    domain.authority_decision if authority_decision is None else authority_decision
                ),
                next_action=domain.next_action if next_action is None else next_action,
                approved_ingest=(
                    domain.approved_ingest if approved_ingest is None else approved_ingest
                ),
                approved_runtime_authority=(
                    domain.approved_runtime_authority
                    if approved_runtime_authority is None
                    else approved_runtime_authority
                ),
                notes=domain.notes if notes is None else notes,
            )
            if domain.domain == "regional_local_products"
            else domain
        )
        for domain in coverage.coverage_domains
    )
    return replace(coverage, coverage_domains=domains)


def _coverage_with_domain(
    domain_name: str,
    *,
    coverage_decision: str | None = None,
    gap_status: str | None = None,
    next_action: str | None = None,
    authority_decision: str | None = None,
    approved_ingest: bool | None = None,
    approved_runtime_authority: bool | None = None,
    auxiliary_sources: tuple[str, ...] | None = None,
) -> SourceGapAudit:
    coverage = copy.deepcopy(_coverage())
    domains = tuple(
        (
            replace(
                domain,
                coverage_decision=(
                    domain.coverage_decision if coverage_decision is None else coverage_decision
                ),
                gap_status=domain.gap_status if gap_status is None else gap_status,
                next_action=domain.next_action if next_action is None else next_action,
                authority_decision=(
                    domain.authority_decision if authority_decision is None else authority_decision
                ),
                approved_ingest=(
                    domain.approved_ingest if approved_ingest is None else approved_ingest
                ),
                approved_runtime_authority=(
                    domain.approved_runtime_authority
                    if approved_runtime_authority is None
                    else approved_runtime_authority
                ),
                auxiliary_sources=(
                    domain.auxiliary_sources if auxiliary_sources is None else auxiliary_sources
                ),
            )
            if domain.domain == domain_name
            else domain
        )
        for domain in coverage.coverage_domains
    )
    return replace(coverage, coverage_domains=domains)


def _coverage_with_regional_source(
    *,
    blocking_reasons: tuple[str, ...] | None = None,
    paid_source_use_allowed: bool | None = None,
    approved_ingest: bool | None = None,
    approved_runtime_authority: bool | None = None,
    api_calls_allowed: bool | None = None,
    scraping_allowed: bool | None = None,
    notes: str | None = None,
) -> SourceGapAudit:
    coverage = copy.deepcopy(_coverage())
    sources = tuple(
        (
            replace(
                source,
                paid_source_use_allowed=(
                    source.paid_source_use_allowed
                    if paid_source_use_allowed is None
                    else paid_source_use_allowed
                ),
                approved_ingest=(
                    source.approved_ingest if approved_ingest is None else approved_ingest
                ),
                approved_runtime_authority=(
                    source.approved_runtime_authority
                    if approved_runtime_authority is None
                    else approved_runtime_authority
                ),
                api_calls_allowed=(
                    source.api_calls_allowed if api_calls_allowed is None else api_calls_allowed
                ),
                scraping_allowed=(
                    source.scraping_allowed if scraping_allowed is None else scraping_allowed
                ),
                blocking_reasons=(
                    source.blocking_reasons if blocking_reasons is None else blocking_reasons
                ),
                notes=source.notes if notes is None else notes,
            )
            if source.source == "regional_catalogs"
            else source
        )
        for source in coverage.source_gap_decisions
    )
    return replace(coverage, source_gap_decisions=sources)


def _coverage_with_source(
    source_name: str,
    *,
    decision: str | None = None,
    source_family: str | None = None,
    allowed_role: str | None = None,
    approved_ingest: bool | None = None,
    approved_runtime_authority: bool | None = None,
    api_calls_allowed: bool | None = None,
    scraping_allowed: bool | None = None,
    paid_source_use_allowed: bool | None = None,
) -> SourceGapAudit:
    coverage = copy.deepcopy(_coverage())
    sources = tuple(
        (
            replace(
                source,
                decision=source.decision if decision is None else decision,
                source_family=source.source_family if source_family is None else source_family,
                allowed_role=source.allowed_role if allowed_role is None else allowed_role,
                approved_ingest=(
                    source.approved_ingest if approved_ingest is None else approved_ingest
                ),
                approved_runtime_authority=(
                    source.approved_runtime_authority
                    if approved_runtime_authority is None
                    else approved_runtime_authority
                ),
                api_calls_allowed=(
                    source.api_calls_allowed if api_calls_allowed is None else api_calls_allowed
                ),
                scraping_allowed=(
                    source.scraping_allowed if scraping_allowed is None else scraping_allowed
                ),
                paid_source_use_allowed=(
                    source.paid_source_use_allowed
                    if paid_source_use_allowed is None
                    else paid_source_use_allowed
                ),
            )
            if source.source == source_name
            else source
        )
        for source in coverage.source_gap_decisions
    )
    return replace(coverage, source_gap_decisions=sources)


def test_load_preference_mapping_closeout_accepts_canonical_artifact() -> None:
    closeout = load_preference_mapping_closeout_governance(
        _CLOSEOUT_PATH,
        preference_mapping=_preference_mapping(),
        coverage=_coverage(),
    )

    assert closeout.pr15_merged_pr == 1747
    assert closeout.pr15_next_recommended_lane == (
        "preference_recipe_mapping_contract_review_closeout"
    )
    assert closeout.external_research_evidence_role == ("review_context_only_not_source_authority")
    assert closeout.next_substantive_lane == "regional_catalog_identity_license_review"


def test_preference_mapping_closeout_report_is_deterministic_json_contract() -> None:
    report = build_preference_mapping_closeout_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        closeout_path=_CLOSEOUT_PATH,
    )

    assert report == {
        "success": True,
        "dry_run": True,
        "source": "preference_recipe_mapping_contract_review_closeout",
        "source_classification": "governance_closeout_only",
        "source_family": "food_data_source_governance",
        "evidence_policy": "external_research_evidence_only_no_source_authority",
        "blocked_methods": [
            "scraping",
            "automated_collection",
            "api_call",
            "download",
            "paid_api_use",
            "seller_api_use",
            "partner_api_use",
            "cache_authority",
            "redistribution",
            "runtime_authority",
            "public_dataset_claim",
            "digitalocean_postgres_load",
            "recipe_text_authority",
            "user_preference_text_authority",
            "llm_output_authority",
            "nutrition_authority",
            "provider_integration",
            "product_display",
        ],
        "pr15_merged_pr": 1747,
        "pr15_next_recommended_lane": "preference_recipe_mapping_contract_review_closeout",
        "next_substantive_lane": "regional_catalog_identity_license_review",
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "network_allowed": False,
        "db_writes_allowed": False,
        "api_calls_allowed": False,
        "source_download_allowed": False,
        "scraping_allowed": False,
        "paid_source_use_allowed": False,
        "seller_api_use_allowed": False,
        "partner_api_use_allowed": False,
        "cache_authority_allowed": False,
        "redistribution_allowed": False,
        "public_dataset_claim_allowed": False,
        "automation_allowed": False,
        "provider_integration_allowed": False,
        "product_display_allowed": False,
        "nutrition_authority_allowed": False,
        "file_only": True,
        "final_gate_decision": "preference_mapping_closeout_only_no_ingest",
        "validation_errors": [],
        "pr15_ref": "docs/architecture/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_2026-05-13.json",
        "coverage_ref": "docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json",
        "recipe_dish_corpus_ref": (
            "docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json"
        ),
        "external_research_evidence_role": "review_context_only_not_source_authority",
        "deferred_followups": [
            "regional_catalog_identity_license_review",
            "paid_restaurant_menu_snapshot_provider_governance",
            "paid_api_or_scraper_provider_contract_review",
            "runtime_postgresql_cutover_packet",
        ],
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
        "seller_api_use_allowed",
        "partner_api_use_allowed",
        "cache_authority_allowed",
        "redistribution_allowed",
        "public_dataset_claim_allowed",
        "automation_allowed",
        "provider_integration_allowed",
        "product_display_allowed",
        "nutrition_authority_allowed",
    ),
)
def test_preference_mapping_closeout_rejects_top_level_unsafe_flags(
    flag_name: str,
) -> None:
    payload = _closeout_payload()
    payload[flag_name] = True

    with pytest.raises(PreferenceMappingCloseoutError, match="flags must be false"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    "bad_notes",
    (
        "Seller API use approved for PR16 closeout.",
        "Partner API use allowed for PR16 closeout.",
        "Provider API approved for PR16 closeout.",
        "Seller account access allowed for PR16 closeout.",
        "Partner menu access allowed for PR16 closeout.",
    ),
)
def test_preference_mapping_closeout_rejects_seller_partner_api_notes(
    bad_notes: str,
) -> None:
    payload = _closeout_payload()
    payload["notes"] = bad_notes

    with pytest.raises(PreferenceMappingCloseoutError, match="notes"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
        )


def test_preference_mapping_closeout_rejects_file_only_false() -> None:
    payload = _closeout_payload()
    payload["file_only"] = False

    with pytest.raises(PreferenceMappingCloseoutError, match="file_only must be true"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    "payload",
    (
        [],
        {1: "bad-key"},
    ),
)
def test_preference_mapping_closeout_rejects_non_mapping_payloads(
    payload: object,
) -> None:
    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("schema_version", "", "non-empty string"),
        ("pr15_merged_pr", True, "integer"),
        ("api_calls_allowed", "false", "boolean"),
        ("blocked_methods", "api_call", "list of strings"),
        ("blocked_methods", ["api_call"], "exactly"),
        ("generated_on", "2026/05/19", "YYYY-MM-DD"),
    ),
)
def test_preference_mapping_closeout_rejects_typed_field_malformed_values(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _closeout_payload()
    payload[field_name] = bad_value

    with pytest.raises(PreferenceMappingCloseoutError, match=match):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
        )


def test_preference_mapping_closeout_report_rejects_external_catalog_ref_mismatch(
    tmp_path: Path,
) -> None:
    outside_catalog = tmp_path / "catalog.json"
    outside_catalog.write_text(_CATALOG_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    report = build_preference_mapping_closeout_report(
        catalog_path=outside_catalog,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        closeout_path=_CLOSEOUT_PATH,
    )

    assert report["success"] is False
    assert str(outside_catalog.resolve()) in str(report["validation_errors"][0])


def test_preference_mapping_closeout_rejects_invalid_calendar_date() -> None:
    payload = _closeout_payload()
    payload["generated_on"] = "2026-99-19"

    with pytest.raises(PreferenceMappingCloseoutError, match="valid calendar date"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("pr15_merged_pr", 0),
        ("pr15_next_recommended_lane", "paid_provider_ingest"),
        ("external_research_evidence_role", "source_authority"),
        ("next_substantive_lane", "paid_api_provider_integration"),
        ("final_gate_decision", "closeout_allows_ingest"),
    ),
)
def test_preference_mapping_closeout_rejects_handoff_or_lane_drift(
    field_name: str,
    bad_value: object,
) -> None:
    payload = _closeout_payload()
    payload[field_name] = bad_value

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("schema_version", "bad.v1"),
        ("source", "paid_provider_source"),
        ("source_classification", "runtime_source"),
        ("source_family", "paid_provider"),
        ("evidence_policy", "source_authority_allowed"),
    ),
)
def test_preference_mapping_closeout_rejects_top_level_identity_drift(
    field_name: str,
    bad_value: str,
) -> None:
    payload = _closeout_payload()
    payload[field_name] = bad_value

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    ("expected_kwargs", "match"),
    (
        ({"expected_pr15_ref": "docs/architecture/WRONG_PR15.json"}, "pr15_ref"),
        ({"expected_coverage_ref": "docs/architecture/WRONG_PR11.json"}, "coverage_ref"),
        (
            {"expected_recipe_dish_corpus_ref": "docs/architecture/WRONG_PR14.json"},
            "recipe_dish_corpus_ref",
        ),
    ),
)
def test_preference_mapping_closeout_rejects_expected_reference_mismatch(
    expected_kwargs: dict[str, str],
    match: str,
) -> None:
    with pytest.raises(PreferenceMappingCloseoutError, match=match):
        parse_preference_mapping_closeout_governance(
            _closeout_payload(),
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
            **expected_kwargs,
        )


def test_preference_mapping_closeout_rejects_pr15_handoff_drift() -> None:
    payload = _closeout_payload()
    preference_mapping = replace(_preference_mapping(), next_recommended_lane="provider_runtime")

    with pytest.raises(PreferenceMappingCloseoutError, match="PR15 must recommend"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=preference_mapping,
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    "preference_mapping",
    (
        replace(_preference_mapping(), coverage_ref="docs/architecture/WRONG_PR11.json"),
        replace(_preference_mapping(), recipe_dish_corpus_ref="docs/architecture/WRONG_PR14.json"),
        replace(_preference_mapping(), pr11_landed_pr=0),
        replace(_preference_mapping(), pr14_landed_pr=0),
    ),
)
def test_preference_mapping_closeout_rejects_pr15_identity_handoff_drift(
    preference_mapping: PreferenceRecipeMappingGovernance,
) -> None:
    payload = _closeout_payload()

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=preference_mapping,
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    "preference_mapping",
    (
        replace(_preference_mapping(), source="provider_runtime"),
        replace(_preference_mapping(), source_classification="runtime_source"),
        replace(_preference_mapping(), source_family="paid_provider"),
        replace(_preference_mapping(), blocked_methods=("api_call",)),
        replace(_preference_mapping(), final_gate_decision="mapping_contract_allows_ingest"),
    ),
)
def test_preference_mapping_closeout_rejects_pr15_source_policy_drift(
    preference_mapping: PreferenceRecipeMappingGovernance,
) -> None:
    payload = _closeout_payload()

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=preference_mapping,
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    "preference_mapping",
    (
        replace(_preference_mapping(), evidence_policy="source_authority_allowed"),
        replace(_preference_mapping(), notes="api calls are allowed"),
        replace(
            _preference_mapping(),
            mapping_contracts=(
                replace(_preference_mapping().mapping_contracts[0], notes="source use allowed"),
                *_preference_mapping().mapping_contracts[1:],
            ),
        ),
    ),
)
def test_preference_mapping_closeout_rejects_pr15_authority_handoff_drift(
    preference_mapping: PreferenceRecipeMappingGovernance,
) -> None:
    payload = _closeout_payload()

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=preference_mapping,
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    "preference_mapping",
    (
        replace(
            _preference_mapping(),
            mapping_contracts=(
                replace(
                    _preference_mapping().mapping_contracts[0],
                    contract_status="mapping_contract_approved",
                ),
                *_preference_mapping().mapping_contracts[1:],
            ),
        ),
        replace(
            _preference_mapping(),
            mapping_contracts=(
                replace(
                    _preference_mapping().mapping_contracts[0],
                    allowed_role="recipe_source_authority",
                ),
                *_preference_mapping().mapping_contracts[1:],
            ),
        ),
        replace(
            _preference_mapping(),
            mapping_contracts=tuple(reversed(_preference_mapping().mapping_contracts)),
        ),
    ),
)
def test_preference_mapping_closeout_rejects_pr15_mapping_contract_drift(
    preference_mapping: PreferenceRecipeMappingGovernance,
) -> None:
    payload = _closeout_payload()

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=preference_mapping,
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    "coverage",
    (
        replace(_coverage(), schema_version="wrong.v1"),
        replace(_coverage(), next_recommended_lane="paid_provider_lane"),
        replace(_coverage(), final_gate_decision="coverage_gap_allows_ingest"),
        replace(_coverage(), notes="source use allowed"),
    ),
)
def test_preference_mapping_closeout_rejects_pr11_top_level_handoff_drift(
    coverage: SourceGapAudit,
) -> None:
    payload = _closeout_payload()

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=coverage,
        )


@pytest.mark.parametrize(
    "coverage",
    (
        replace(_coverage(), catalog_ref="docs/architecture/WRONG_CATALOG.json"),
        replace(_coverage(), onboarding_ref="docs/architecture/WRONG_ONBOARDING.json"),
        replace(_coverage(), pr10_landed_pr=0),
    ),
)
def test_preference_mapping_closeout_rejects_pr11_identity_handoff_drift(
    coverage: SourceGapAudit,
) -> None:
    payload = _closeout_payload()

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=coverage,
        )


@pytest.mark.parametrize(
    "coverage",
    (
        _coverage_with_domain("restaurant_chain_menus", approved_ingest=True),
        _coverage_with_domain("recipe_dish_corpora", approved_runtime_authority=True),
        _coverage_with_domain("restaurant_chain_menus", authority_decision="approved"),
        _coverage_with_domain("recipe_dish_corpora", auxiliary_sources=("nutritionix",)),
        _coverage_with_domain("restaurant_chain_menus", coverage_decision="adequate_baseline"),
        _coverage_with_domain("restaurant_chain_menus", gap_status="resolved"),
        _coverage_with_domain("restaurant_chain_menus", next_action="paid_provider_runtime_review"),
    ),
)
def test_preference_mapping_closeout_rejects_nonregional_domain_authority_drift(
    coverage: SourceGapAudit,
) -> None:
    payload = _closeout_payload()

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=coverage,
        )


@pytest.mark.parametrize(
    "coverage",
    (
        _coverage_with_source("nutritionix", api_calls_allowed=True),
        _coverage_with_source("nutritionix", approved_ingest=True),
        _coverage_with_source("nutritionix", paid_source_use_allowed=True),
        _coverage_with_source("edamam_food_database", scraping_allowed=True),
        _coverage_with_source("nutritionix", decision="approved_contract_review"),
        _coverage_with_source("nutritionix", source_family="commercial_runtime_api"),
        _coverage_with_source("nutritionix", allowed_role="runtime_source_authority"),
    ),
)
def test_preference_mapping_closeout_rejects_nonregional_source_authority_drift(
    coverage: SourceGapAudit,
) -> None:
    payload = _closeout_payload()

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=coverage,
        )


def test_preference_mapping_closeout_rejects_duplicate_nonregional_domain() -> None:
    payload = _closeout_payload()
    coverage = _coverage()
    duplicate_domain = next(
        domain
        for domain in coverage.coverage_domains
        if domain.domain == "branded_barcode_products"
    )
    mutated = replace(
        coverage,
        coverage_domains=(duplicate_domain, *coverage.coverage_domains[1:]),
    )

    with pytest.raises(PreferenceMappingCloseoutError, match="coverage_domains"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=mutated,
        )


def test_preference_mapping_closeout_rejects_regional_domain_drift() -> None:
    payload = _closeout_payload()
    coverage = _coverage_with_regional_domain(next_action="paid_restaurant_menu_snapshot")

    with pytest.raises(PreferenceMappingCloseoutError, match="regional_local_products"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=coverage,
        )


@pytest.mark.parametrize(
    "coverage",
    (
        _coverage_with_regional_domain(coverage_decision="adequate_baseline"),
        _coverage_with_regional_domain(primary_sources=("regional_catalogs",)),
        _coverage_with_regional_domain(auxiliary_sources=()),
        _coverage_with_regional_domain(gap_status="baseline_covered"),
        _coverage_with_regional_domain(authority_decision="approved"),
    ),
)
def test_preference_mapping_closeout_rejects_regional_domain_authority_drift(
    coverage: SourceGapAudit,
) -> None:
    payload = _closeout_payload()

    with pytest.raises(PreferenceMappingCloseoutError, match="regional_local_products"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=coverage,
        )


@pytest.mark.parametrize(
    "coverage",
    (
        _coverage_with_regional_source(paid_source_use_allowed=True),
        _coverage_with_regional_source(approved_ingest=True),
        _coverage_with_regional_source(approved_runtime_authority=True),
        _coverage_with_regional_source(api_calls_allowed=True),
        _coverage_with_regional_source(scraping_allowed=True),
    ),
)
def test_preference_mapping_closeout_rejects_regional_source_approval(
    coverage: SourceGapAudit,
) -> None:
    payload = _closeout_payload()

    with pytest.raises(PreferenceMappingCloseoutError, match="must not approve source use"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=coverage,
        )


def test_preference_mapping_closeout_rejects_regional_source_blocking_reason_drift() -> None:
    payload = _closeout_payload()
    coverage = _coverage_with_regional_source(
        blocking_reasons=("source identity is verified and redistribution allowed",)
    )

    with pytest.raises(PreferenceMappingCloseoutError, match="blocking_reasons"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=coverage,
        )


def test_preference_mapping_closeout_rejects_duplicate_regional_domain() -> None:
    payload = _closeout_payload()
    coverage = _coverage()
    regional_domain = next(
        domain for domain in coverage.coverage_domains if domain.domain == "regional_local_products"
    )
    duplicated = replace(
        coverage,
        coverage_domains=(*coverage.coverage_domains, replace(regional_domain)),
    )

    with pytest.raises(PreferenceMappingCloseoutError, match="coverage_domains"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=duplicated,
        )


def test_preference_mapping_closeout_rejects_duplicate_regional_source() -> None:
    payload = _closeout_payload()
    coverage = _coverage()
    regional_source = next(
        source for source in coverage.source_gap_decisions if source.source == "regional_catalogs"
    )
    duplicated = replace(
        coverage,
        source_gap_decisions=(
            *coverage.source_gap_decisions,
            replace(regional_source, api_calls_allowed=True),
        ),
    )

    with pytest.raises(PreferenceMappingCloseoutError, match="source_gap_decisions"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=duplicated,
        )


@pytest.mark.parametrize(
    "coverage",
    (
        _coverage_with_regional_domain(notes="api calls are allowed for regional catalogs"),
        _coverage_with_regional_source(notes="api calls are allowed for regional catalogs"),
    ),
)
def test_preference_mapping_closeout_rejects_regional_handoff_authority_notes(
    coverage: SourceGapAudit,
) -> None:
    payload = _closeout_payload()

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=coverage,
        )


@pytest.mark.parametrize(
    "bad_notes",
    (
        "Attached spreadsheet is authority for source decisions.",
        "The report is authority for paid provider use.",
        "The docx is authority and api calls allowed.",
        "The image is authority for product display.",
        "Attached spreadsheet approves paid APIs for source decisions.",
        "Attached reports are approved for source decisions.",
        "The report authorizes provider snapshots for the next lane.",
        "The image permits scrapers for restaurant menu evidence.",
        "Cache authority allowed.",
        "Database writes allowed.",
        "Redistribution allowed.",
        "Ingest allowed.",
        "Source use allowed.",
        "Provider snapshots are source authority for regional catalog decisions.",
        "Edamam is source authority for regional catalog decisions.",
        "Spoonacular becomes source authority for regional catalog decisions.",
        "Nutritionix is nutrition authority for this closeout.",
        "TheMealDB is runtime authority for recipes.",
        "No api calls approved. Scraping allowed.",
        "No provider snapshots approved. Edamam is source authority.",
        "No api calls allowed. API calls allowed for regional source decisions.",
        "Paid API use allowed.",
        "Paid API use is allowed.",
        "Automated collection allowed.",
        "DigitalOcean Postgres load allowed.",
        "Public dataset claim allowed.",
        "The report does not approve source use; api calls are allowed for next lane.",
        "API calls enabled.",
        "Paid API use granted.",
        "Cache authority is enabled.",
        "The report grants provider snapshots for the next lane.",
        "Network access allowed for source checks.",
        "Paid provider use allowed.",
        "Paid plans allowed.",
        "API calls may be used.",
        "Paid APIs may be used.",
        "Provider snapshots may be used.",
        "API calls may be relied on for source checks.",
        "Paid APIs are usable for source checks.",
        "Scraping is okay for source checks.",
        "Provider snapshots can be relied on for the next lane.",
        "Network access is available for source checks.",
    ),
)
def test_preference_mapping_closeout_rejects_external_evidence_authority_notes(
    bad_notes: str,
) -> None:
    payload = _closeout_payload()
    payload["notes"] = bad_notes

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
        )


@pytest.mark.parametrize(
    "safe_notes",
    (
        "No paid source approved for PR16 closeout.",
        "No api calls approved by this evidence packet.",
        "No api calls allowed in PR16.",
        "The report does not approve provider snapshots.",
        "Edamam is not source authority for PR16 closeout.",
        "Spoonacular does not become source authority for PR16 closeout.",
    ),
)
def test_preference_mapping_closeout_allows_negated_blocked_approval_notes(
    safe_notes: str,
) -> None:
    payload = _closeout_payload()
    payload["notes"] = safe_notes

    parsed = parse_preference_mapping_closeout_governance(
        payload,
        preference_mapping=_preference_mapping(),
        coverage=_coverage(),
    )

    assert parsed.notes == safe_notes


@pytest.mark.parametrize(
    "bad_budget_policy",
    (
        "USDA + Open Food Facts remain baseline, but paid APIs approved for use.",
        "USDA + Open Food Facts remain baseline, and provider snapshots are allowed.",
        "USDA + Open Food Facts remain baseline, and this report permits scrapers.",
        "USDA + Open Food Facts are deprecated and no longer the baseline.",
    ),
)
def test_preference_mapping_closeout_rejects_budget_policy_authority_promotion(
    bad_budget_policy: str,
) -> None:
    payload = _closeout_payload()
    payload["budget_first_policy"] = bad_budget_policy

    with pytest.raises(PreferenceMappingCloseoutError):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
        )


def test_preference_mapping_closeout_rejects_missing_provider_deferrals() -> None:
    payload = _closeout_payload()
    payload["deferred_followups"] = ["regional_catalog_identity_license_review"]

    with pytest.raises(PreferenceMappingCloseoutError, match="deferred_followups"):
        parse_preference_mapping_closeout_governance(
            payload,
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
        )


def test_preference_mapping_closeout_rejects_malformed_artifact(tmp_path: Path) -> None:
    malformed_path = tmp_path / "closeout.json"
    malformed_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(PreferenceMappingCloseoutError, match="Cannot read"):
        load_preference_mapping_closeout_governance(
            malformed_path,
            preference_mapping=_preference_mapping(),
            coverage=_coverage(),
        )


def test_preference_mapping_closeout_report_returns_validation_errors_for_bad_closeout(
    tmp_path: Path,
) -> None:
    payload = _closeout_payload()
    payload["schema_version"] = "bad.v1"
    bad_path = _write_payload(tmp_path / "bad-closeout.json", payload)

    report = build_preference_mapping_closeout_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        preference_mapping_path=_PREFERENCE_MAPPING_PATH,
        closeout_path=bad_path,
    )

    assert report["success"] is False
    assert report["validation_errors"]


def test_preference_mapping_closeout_cli_success_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--json",
        ],
        cwd=_REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=_CLI_TIMEOUT_SECONDS,
        check=True,
    )

    report = json.loads(completed.stdout)
    assert report["success"] is True
    assert report["next_substantive_lane"] == "regional_catalog_identity_license_review"


def test_preference_mapping_closeout_cli_failure_json(tmp_path: Path) -> None:
    payload = _closeout_payload()
    payload["api_calls_allowed"] = True
    bad_path = _write_payload(tmp_path / "bad-closeout.json", payload)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--closeout",
            str(bad_path),
            "--json",
        ],
        cwd=_REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=_CLI_TIMEOUT_SECONDS,
        check=False,
    )

    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report["success"] is False
    assert "api_calls_allowed flags must be false" in report["validation_errors"][0]
