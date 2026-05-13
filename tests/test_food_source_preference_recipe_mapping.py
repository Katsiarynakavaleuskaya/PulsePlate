"""Tests for the deterministic PR15 preference recipe mapping contract gate."""

from __future__ import annotations

import copy
from dataclasses import replace
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources.preference_recipe_mapping import (
    BLOCKED_METHODS,
    PreferenceRecipeMappingError,
    build_preference_recipe_mapping_report,
    load_preference_recipe_mapping_governance,
    parse_preference_recipe_mapping_governance,
    _parse_date,
    _require_existing_entry,
    _relative_repo_path,
    _require_bool,
    _require_int,
    _require_mapping,
    _require_string,
    _require_string_tuple,
)
from core.food_sources.recipe_dish_corpus import (
    RecipeDishCorpusGovernance,
    load_recipe_dish_corpus_governance,
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
_GOVERNANCE_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_2026-05-13.json"
)
_CLI_MODULE = "scripts.food_source_preference_recipe_mapping"
_CLI_TIMEOUT_SECONDS = 30


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


def _recipe_dish_corpus() -> RecipeDishCorpusGovernance:
    return load_recipe_dish_corpus_governance(
        _RECIPE_DISH_CORPUS_PATH,
        onboarding=_onboarding(),
        coverage=_coverage(),
    )


def _governance_payload() -> dict[str, object]:
    payload = json.loads(_GOVERNANCE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _mapping_row(payload: dict[str, object], mapping_key: str) -> dict[str, object]:
    rows = payload["mapping_contracts"]
    assert isinstance(rows, list)
    for row in rows:
        if isinstance(row, dict) and row.get("mapping_key") == mapping_key:
            return row
    raise AssertionError(f"missing mapping contract {mapping_key}")


def _coverage_with_preference_domain(
    *,
    coverage_decision: str | None = None,
    gap_status: str | None = None,
    authority_decision: str | None = None,
    next_action: str | None = None,
    notes: str | None = None,
) -> SourceGapAudit:
    return _coverage_with_domain_decision(
        "preference_menu_planning",
        coverage_decision=coverage_decision,
        gap_status=gap_status,
        authority_decision=authority_decision,
        next_action=next_action,
        notes=notes,
    )


def _coverage_with_domain_decision(
    domain_name: str,
    **updates: object,
) -> SourceGapAudit:
    coverage_payload = copy.deepcopy(_coverage())
    domains = tuple(
        (
            replace(
                domain,
                **{key: value for key, value in updates.items() if value is not None},
            )
            if domain.domain == domain_name
            else domain
        )
        for domain in coverage_payload.coverage_domains
    )
    return replace(coverage_payload, coverage_domains=domains)


def _coverage_with_source_gap_decision(source: str, **updates: object) -> SourceGapAudit:
    coverage_payload = copy.deepcopy(_coverage())
    source_gap_decisions = tuple(
        replace(source_gap, **updates) if source_gap.source == source else source_gap
        for source_gap in coverage_payload.source_gap_decisions
    )
    return replace(coverage_payload, source_gap_decisions=source_gap_decisions)


def _recipe_dish_corpus_with_first_review(**updates: object) -> RecipeDishCorpusGovernance:
    recipe_governance = _recipe_dish_corpus()
    first_review = replace(recipe_governance.recipe_corpus_reviews[0], **updates)
    return replace(
        recipe_governance,
        recipe_corpus_reviews=(first_review, *recipe_governance.recipe_corpus_reviews[1:]),
    )


def test_load_preference_recipe_mapping_accepts_canonical_artifact() -> None:
    governance = load_preference_recipe_mapping_governance(
        _GOVERNANCE_PATH,
        coverage=_coverage(),
        recipe_dish_corpus=_recipe_dish_corpus(),
        expected_coverage_ref="docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json",
        expected_recipe_dish_corpus_ref=(
            "docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json"
        ),
    )

    assert governance.pr11_landed_pr == 1601
    assert governance.pr14_landed_pr == 1743
    assert governance.source == "preference_menu_planning"
    assert governance.source_family == "preference_recipe_mapping"
    assert [contract.mapping_key for contract in governance.mapping_contracts] == [
        "mediterranean_pattern",
        "gluten_free_constraint",
        "high_protein_preference",
    ]


def test_preference_recipe_mapping_report_is_deterministic_json_contract() -> None:
    report = build_preference_recipe_mapping_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        governance_path=_GOVERNANCE_PATH,
    )

    assert report == {
        "success": True,
        "dry_run": True,
        "source": "preference_menu_planning",
        "source_classification": "planning_contract_governance_only",
        "source_family": "preference_recipe_mapping",
        "evidence_policy": "preference_recipe_mapping_contract_only_no_source_use",
        "blocked_methods": [
            "scraping",
            "automated_collection",
            "api_call",
            "download",
            "paid_api_use",
            "cache_authority",
            "redistribution",
            "runtime_authority",
            "public_dataset_claim",
            "digitalocean_postgres_load",
            "recipe_text_authority",
            "user_preference_text_authority",
            "llm_output_authority",
            "nutrition_authority",
        ],
        "mapping_keys": [
            "mediterranean_pattern",
            "gluten_free_constraint",
            "high_protein_preference",
        ],
        "next_recommended_lane": "preference_recipe_mapping_contract_review_closeout",
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "network_allowed": False,
        "db_writes_allowed": False,
        "api_calls_allowed": False,
        "source_download_allowed": False,
        "scraping_allowed": False,
        "paid_source_use_allowed": False,
        "cache_authority_allowed": False,
        "redistribution_allowed": False,
        "public_dataset_claim_allowed": False,
        "automation_allowed": False,
        "recipe_text_authority_allowed": False,
        "user_preference_text_authority_allowed": False,
        "llm_output_authority_allowed": False,
        "nutrition_authority_allowed": False,
        "file_only": True,
        "final_gate_decision": "preference_recipe_mapping_contract_only_no_ingest",
        "validation_errors": [],
        "coverage_ref": "docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json",
        "recipe_dish_corpus_ref": (
            "docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json"
        ),
        "pr11_landed_pr": 1601,
        "pr14_landed_pr": 1743,
        "contract_status": {
            "mediterranean_pattern": "mapping_contract_required_not_approved",
            "gluten_free_constraint": "mapping_contract_required_not_approved",
            "high_protein_preference": "mapping_contract_required_not_approved",
        },
        "allowed_roles": {
            "mediterranean_pattern": "preference_category_contract_only",
            "gluten_free_constraint": "constraint_mapping_contract_only",
            "high_protein_preference": "macro_preference_contract_only",
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
        "cache_authority_allowed",
        "redistribution_allowed",
        "public_dataset_claim_allowed",
        "automation_allowed",
        "recipe_text_authority_allowed",
        "user_preference_text_authority_allowed",
        "llm_output_authority_allowed",
        "nutrition_authority_allowed",
    ),
)
def test_preference_recipe_mapping_rejects_top_level_unsafe_flags(flag_name: str) -> None:
    payload = _governance_payload()
    payload[flag_name] = True

    with pytest.raises(PreferenceRecipeMappingError, match="flags must be false"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rejects_file_only_false() -> None:
    payload = _governance_payload()
    payload["file_only"] = False

    with pytest.raises(PreferenceRecipeMappingError, match="file_only must be true"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


@pytest.mark.parametrize(
    "flag_name",
    (
        "approved_ingest",
        "approved_runtime_authority",
        "source_use_allowed",
        "db_writes_allowed",
        "cache_authority_allowed",
        "recipe_text_authority_allowed",
        "user_preference_text_authority_allowed",
        "llm_output_authority_allowed",
    ),
)
def test_preference_recipe_mapping_rejects_per_mapping_unsafe_flags(flag_name: str) -> None:
    payload = _governance_payload()
    _mapping_row(payload, "mediterranean_pattern")[flag_name] = True

    with pytest.raises(PreferenceRecipeMappingError, match="cannot approve source use"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rejects_pr11_lane_drift() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage_with_preference_domain(next_action="some_other_lane")

    with pytest.raises(PreferenceRecipeMappingError, match="PR11 preference_menu_planning"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("next_recommended_lane", "runtime_source_cutover"),
        ("final_gate_decision", "coverage_gap_audit_allows_ingest"),
    ),
)
def test_preference_recipe_mapping_rejects_pr11_top_level_handoff_drift(
    field_name: str,
    bad_value: str,
) -> None:
    payload = _governance_payload()
    coverage_payload = replace(_coverage(), **{field_name: bad_value})

    with pytest.raises(PreferenceRecipeMappingError, match=f"PR11 .*{field_name}"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("coverage_decision", "approved_source_mapping"),
        ("gap_status", "planner_gap_as_source_authority"),
        ("authority_decision", "source_authority"),
    ),
)
def test_preference_recipe_mapping_rejects_pr11_authority_decision_drift(
    field_name: str,
    bad_value: str,
) -> None:
    payload = _governance_payload()
    if field_name == "coverage_decision":
        coverage_payload = _coverage_with_preference_domain(coverage_decision=bad_value)
    elif field_name == "gap_status":
        coverage_payload = _coverage_with_preference_domain(gap_status=bad_value)
    else:
        coverage_payload = _coverage_with_preference_domain(authority_decision=bad_value)

    with pytest.raises(
        PreferenceRecipeMappingError, match=f"PR11 preference_menu_planning .*{field_name}"
    ):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "expected_message"),
    (
        ("schema_version", "wrong", "PR11 schema_version"),
        ("catalog_ref", "wrong.json", "PR11 catalog_ref"),
        ("onboarding_ref", "wrong.json", "PR11 onboarding_ref"),
        ("pr10_landed_pr", 0, "PR11 pr10_landed_pr"),
    ),
)
def test_preference_recipe_mapping_rechecks_pr11_provenance_for_handoff(
    field_name: str,
    bad_value: object,
    expected_message: str,
) -> None:
    payload = _governance_payload()
    coverage_payload = replace(_coverage(), **{field_name: bad_value})

    with pytest.raises(PreferenceRecipeMappingError, match=expected_message):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rechecks_all_pr11_coverage_domain_flags() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage_with_domain_decision(
        "restaurant_chain_menus",
        approved_ingest=True,
    )

    with pytest.raises(
        PreferenceRecipeMappingError,
        match="PR11 restaurant_chain_menus coverage_domains",
    ):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("coverage_decision", "approved_source"),
        ("gap_status", "runtime_ready"),
        ("authority_decision", "approved"),
        ("next_action", "runtime_ingest"),
    ),
)
def test_preference_recipe_mapping_rechecks_all_pr11_coverage_domain_decisions(
    field_name: str,
    bad_value: str,
) -> None:
    payload = _governance_payload()
    coverage_payload = _coverage_with_domain_decision(
        "restaurant_chain_menus",
        **{field_name: bad_value},
    )

    with pytest.raises(
        PreferenceRecipeMappingError,
        match=f"PR11 restaurant_chain_menus coverage_domains {field_name}",
    ):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rechecks_all_pr11_coverage_domain_notes() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage_with_domain_decision(
        "restaurant_chain_menus",
        notes="source use approved",
    )

    with pytest.raises(PreferenceRecipeMappingError, match="notes must not approve"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rechecks_pr11_coverage_domain_source_refs() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage_with_domain_decision(
        "preference_menu_planning",
        primary_sources=("approved_api_source",),
    )

    with pytest.raises(
        PreferenceRecipeMappingError,
        match="PR11 preference_menu_planning coverage_domains primary_sources",
    ):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("decision", "approved_recipe_source"),
        ("source_family", "commercial_api"),
        ("allowed_role", "source_authority"),
        ("approved_ingest", True),
        ("approved_runtime_authority", True),
        ("api_calls_allowed", True),
        ("scraping_allowed", True),
        ("paid_source_use_allowed", True),
    ),
)
def test_preference_recipe_mapping_rechecks_pr11_recipe_source_gap_rows_for_handoff(
    field_name: str,
    bad_value: object,
) -> None:
    payload = _governance_payload()
    coverage_payload = _coverage_with_source_gap_decision(
        "edamam_food_database", **{field_name: bad_value}
    )

    with pytest.raises(
        PreferenceRecipeMappingError, match="PR11 edamam_food_database source_gap_decisions"
    ):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("decision", "approved_current_source"),
        ("source_family", "approved_api"),
        ("allowed_role", "nutrition_authority"),
    ),
)
def test_preference_recipe_mapping_rechecks_all_pr11_source_gap_decision_fields(
    field_name: str,
    bad_value: str,
) -> None:
    payload = _governance_payload()
    coverage_payload = _coverage_with_source_gap_decision(
        "nutritionix",
        **{field_name: bad_value},
    )

    with pytest.raises(
        PreferenceRecipeMappingError,
        match=f"PR11 nutritionix source_gap_decisions {field_name}",
    ):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rechecks_pr11_source_gap_blocking_reasons() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage_with_source_gap_decision(
        "nutritionix",
        blocking_reasons=(),
    )

    with pytest.raises(
        PreferenceRecipeMappingError,
        match="PR11 nutritionix source_gap_decisions blocking_reasons",
    ):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rechecks_all_pr11_source_gap_flags() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage_with_source_gap_decision(
        "nutritionix",
        api_calls_allowed=True,
    )

    with pytest.raises(
        PreferenceRecipeMappingError,
        match="PR11 nutritionix source_gap_decisions",
    ):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rechecks_all_pr11_source_gap_notes() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage_with_source_gap_decision(
        "nutritionix",
        notes="api calls are allowed",
    )

    with pytest.raises(PreferenceRecipeMappingError, match="notes must not approve"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rejects_duplicate_pr11_source_gap_rows() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage()
    first_row = coverage_payload.source_gap_decisions[0]
    duplicate_row = replace(
        next(
            row
            for row in coverage_payload.source_gap_decisions
            if row.source == "edamam_food_database"
        ),
        approved_ingest=True,
    )
    coverage_payload = replace(
        coverage_payload,
        source_gap_decisions=(first_row, duplicate_row, *coverage_payload.source_gap_decisions[1:]),
    )

    with pytest.raises(PreferenceRecipeMappingError, match="source_gap_decisions.*duplicates"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rejects_extra_pr11_source_gap_rows() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage()
    extra_row = replace(
        coverage_payload.source_gap_decisions[0],
        source="unreviewed_recipe_api",
        decision="approved_recipe_api",
        approved_ingest=True,
    )
    coverage_payload = replace(
        coverage_payload,
        source_gap_decisions=(*coverage_payload.source_gap_decisions, extra_row),
    )

    with pytest.raises(PreferenceRecipeMappingError, match="source_gap_decisions must be exactly"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rejects_duplicate_pr11_coverage_domain_rows() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage()
    preference_domain = next(
        domain
        for domain in coverage_payload.coverage_domains
        if domain.domain == "preference_menu_planning"
    )
    duplicate_domain = replace(preference_domain, approved_ingest=True)
    coverage_payload = replace(
        coverage_payload,
        coverage_domains=(duplicate_domain, *coverage_payload.coverage_domains),
    )

    with pytest.raises(PreferenceRecipeMappingError, match="coverage_domains must be exactly"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rejects_extra_pr11_coverage_domain_rows() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage()
    extra_domain = replace(
        coverage_payload.coverage_domains[0],
        domain="unreviewed_preference_source",
        approved_ingest=True,
        notes="api calls are allowed",
    )
    coverage_payload = replace(
        coverage_payload,
        coverage_domains=(*coverage_payload.coverage_domains, extra_domain),
    )

    with pytest.raises(PreferenceRecipeMappingError, match="coverage_domains must be exactly"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rechecks_pr11_source_gap_notes_for_handoff() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage_with_source_gap_decision(
        "edamam_food_database", notes="source use approved"
    )

    with pytest.raises(PreferenceRecipeMappingError, match="notes must not approve"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rechecks_pr11_top_level_notes_for_handoff() -> None:
    payload = _governance_payload()
    coverage_payload = replace(_coverage(), notes="api calls are allowed")

    with pytest.raises(PreferenceRecipeMappingError, match="notes must not approve"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rechecks_pr11_preference_domain_notes_for_handoff() -> None:
    payload = _governance_payload()
    coverage_payload = _coverage_with_preference_domain(notes="source use approved")

    with pytest.raises(PreferenceRecipeMappingError, match="notes must not approve"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rejects_pr14_lane_drift() -> None:
    payload = _governance_payload()
    recipe_governance = _recipe_dish_corpus()
    recipe_governance = replace(recipe_governance, next_recommended_lane="some_other_lane")

    with pytest.raises(PreferenceRecipeMappingError, match="PR14 must recommend"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=recipe_governance,
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "expected_message"),
    (
        ("schema_version", "wrong", "PR14 schema_version"),
        ("per_chain_legal_ref", "wrong.json", "PR14 per_chain_legal_ref"),
        ("pr13_landed_pr", 0, "PR14 pr13_landed_pr"),
    ),
)
def test_preference_recipe_mapping_rechecks_pr14_provenance_for_direct_handoff(
    field_name: str,
    bad_value: object,
    expected_message: str,
) -> None:
    payload = _governance_payload()
    recipe_governance = replace(_recipe_dish_corpus(), **{field_name: bad_value})

    with pytest.raises(PreferenceRecipeMappingError, match=expected_message):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=recipe_governance,
        )


def test_preference_recipe_mapping_rechecks_pr14_blocked_methods_for_direct_handoff() -> None:
    payload = _governance_payload()
    recipe_governance = replace(_recipe_dish_corpus(), blocked_methods=())

    with pytest.raises(PreferenceRecipeMappingError, match="PR14 blocked_methods"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=recipe_governance,
        )


def test_preference_recipe_mapping_rechecks_pr14_review_source_order() -> None:
    payload = _governance_payload()
    recipe_governance = _recipe_dish_corpus()
    recipe_governance = replace(
        recipe_governance,
        recipe_corpus_reviews=tuple(reversed(recipe_governance.recipe_corpus_reviews)),
    )

    with pytest.raises(PreferenceRecipeMappingError, match="recipe_corpus_reviews sources"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=recipe_governance,
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("source", "spoonacular"),
        ("source_classification", "approved_source"),
        ("source_family", "commercial_api"),
    ),
)
def test_preference_recipe_mapping_rejects_pr14_top_level_identity_drift(
    field_name: str,
    bad_value: str,
) -> None:
    payload = _governance_payload()
    recipe_governance = replace(_recipe_dish_corpus(), **{field_name: bad_value})

    with pytest.raises(PreferenceRecipeMappingError, match=f"PR14 .*{field_name}"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=recipe_governance,
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("evidence_policy", "recipe_dish_corpus_governance_allows_source_use"),
        ("final_gate_decision", "recipe_dish_corpus_ingest_ready"),
    ),
)
def test_preference_recipe_mapping_rejects_pr14_no_ingest_handoff_drift(
    field_name: str,
    bad_value: str,
) -> None:
    payload = _governance_payload()
    if field_name == "evidence_policy":
        recipe_governance = replace(_recipe_dish_corpus(), evidence_policy=bad_value)
    else:
        recipe_governance = replace(_recipe_dish_corpus(), final_gate_decision=bad_value)

    with pytest.raises(PreferenceRecipeMappingError, match=f"PR14 .*{field_name}"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=recipe_governance,
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("legal_review_status", "approved"),
        ("contract_review_status", "approved"),
        ("cache_decision", "approved"),
        ("display_decision", "approved"),
        ("attribution_decision", "approved"),
        ("redistribution_decision", "approved"),
        ("freshness_review_status", "approved"),
        ("schema_review_status", "approved"),
        ("rollback_requirement", "not_required"),
        ("allowed_role", "source_authority"),
    ),
)
def test_preference_recipe_mapping_rechecks_pr14_review_rows_for_direct_handoff(
    field_name: str,
    bad_value: str,
) -> None:
    payload = _governance_payload()
    if field_name == "legal_review_status":
        recipe_governance = _recipe_dish_corpus_with_first_review(legal_review_status=bad_value)
    elif field_name == "contract_review_status":
        recipe_governance = _recipe_dish_corpus_with_first_review(contract_review_status=bad_value)
    elif field_name == "cache_decision":
        recipe_governance = _recipe_dish_corpus_with_first_review(cache_decision=bad_value)
    elif field_name == "display_decision":
        recipe_governance = _recipe_dish_corpus_with_first_review(display_decision=bad_value)
    elif field_name == "attribution_decision":
        recipe_governance = _recipe_dish_corpus_with_first_review(attribution_decision=bad_value)
    elif field_name == "redistribution_decision":
        recipe_governance = _recipe_dish_corpus_with_first_review(redistribution_decision=bad_value)
    elif field_name == "freshness_review_status":
        recipe_governance = _recipe_dish_corpus_with_first_review(freshness_review_status=bad_value)
    elif field_name == "schema_review_status":
        recipe_governance = _recipe_dish_corpus_with_first_review(schema_review_status=bad_value)
    elif field_name == "rollback_requirement":
        recipe_governance = _recipe_dish_corpus_with_first_review(rollback_requirement=bad_value)
    else:
        recipe_governance = _recipe_dish_corpus_with_first_review(allowed_role=bad_value)

    with pytest.raises(PreferenceRecipeMappingError, match=f"PR14 .*{field_name}"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=recipe_governance,
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("source_classification", "approved_source"),
        ("source_family", "approved_api"),
    ),
)
def test_preference_recipe_mapping_rechecks_pr14_review_identity_for_direct_handoff(
    field_name: str,
    bad_value: str,
) -> None:
    payload = _governance_payload()
    recipe_governance = _recipe_dish_corpus_with_first_review(**{field_name: bad_value})

    with pytest.raises(PreferenceRecipeMappingError, match=f"PR14 .*{field_name}"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=recipe_governance,
        )


def test_preference_recipe_mapping_rechecks_pr14_review_notes_for_direct_handoff() -> None:
    payload = _governance_payload()
    recipe_governance = _recipe_dish_corpus_with_first_review(notes="api calls are allowed")

    with pytest.raises(PreferenceRecipeMappingError, match="notes must not approve"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=recipe_governance,
        )


def test_preference_recipe_mapping_rechecks_pr14_top_level_notes_for_direct_handoff() -> None:
    payload = _governance_payload()
    recipe_governance = replace(_recipe_dish_corpus(), notes="api calls are allowed")

    with pytest.raises(PreferenceRecipeMappingError, match="notes must not approve"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=recipe_governance,
        )


@pytest.mark.parametrize(
    "note",
    (
        "recipe text authority is now available",
        "user preference text authority approved",
        "LLM output authority allowed",
        "nutrition authority approved",
        "api approved",
        "approved api",
        "allowed api",
        "api allowed",
        "approved ingest",
        "allowed ingest",
        "approved cache",
        "allowed cache",
        "approved source use",
        "source use is approved",
        "source use allowed",
        "source use is allowed",
        "api calls approved",
        "api calls are allowed",
        "runtime authority allowed",
        "db writes allowed",
        "paid API use is approved",
        "downloads allowed",
        "scraping allowed",
        "redistribution allowed",
        "public dataset claim is allowed",
        "automation allowed",
        "api calls permitted",
        "source use is permitted",
        "ingest granted",
        "runtime authority granted",
        "api calls enabled",
        "not only are api calls allowed",
        "not only api calls allowed but downloads enabled",
        "api calls: allowed",
        "source use: approved",
        "downloads now enabled",
        "allow api calls",
        "allows source use",
        "api calls authorized",
        "source use authorized",
        "nutrition authority authorized",
        "recipe text allowed",
        "user preference text allowed",
        "llm output enabled",
        "approved for api calls",
        "allowed for source use",
        "approved for recipe text",
        "api calls; allowed",
        "source use [approved]",
        "downloads / enabled",
        "no only api calls allowed",
        "paid plans allowed",
        "paid plan approved",
        "edamam allowed",
        "spoonacular approved",
        "public menu pages approved",
        "chain evidence authorized",
    ),
)
def test_preference_recipe_mapping_rejects_notes_that_contradict_policy(note: str) -> None:
    payload = _governance_payload()
    payload["notes"] = note

    with pytest.raises(PreferenceRecipeMappingError, match="notes must not approve"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


@pytest.mark.parametrize("method", BLOCKED_METHODS)
@pytest.mark.parametrize("approval", ("approved", "is approved", "allowed", "is allowed"))
def test_preference_recipe_mapping_rejects_blocked_method_note_approvals(
    method: str,
    approval: str,
) -> None:
    payload = _governance_payload()
    payload["notes"] = f"{method} {approval}"

    with pytest.raises(PreferenceRecipeMappingError, match="notes must not approve"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


@pytest.mark.parametrize(
    "note",
    (
        "we approve source use",
        "this approves API calls",
        "operators approve paid API use",
        "policy approves cache authority",
    ),
)
def test_preference_recipe_mapping_rejects_present_tense_note_approvals(note: str) -> None:
    payload = _governance_payload()
    payload["notes"] = note

    with pytest.raises(PreferenceRecipeMappingError, match="notes must not approve"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rejects_later_positive_note_after_negated_match() -> None:
    payload = _governance_payload()
    payload["notes"] = "this does not approve API calls; api approved"

    with pytest.raises(PreferenceRecipeMappingError, match="notes must not approve"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rejects_contrastive_approval_after_negation() -> None:
    payload = _governance_payload()
    payload["notes"] = "no api calls or downloads allowed but source use allowed"

    with pytest.raises(PreferenceRecipeMappingError, match="notes must not approve"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


@pytest.mark.parametrize(
    "note",
    (
        "we do not approve source use",
        "this does not approve API calls",
        "operators never approve paid API use",
    ),
)
def test_preference_recipe_mapping_allows_negated_present_tense_notes(note: str) -> None:
    payload = _governance_payload()
    payload["notes"] = note

    governance = parse_preference_recipe_mapping_governance(
        payload,
        coverage=_coverage(),
        recipe_dish_corpus=_recipe_dish_corpus(),
    )

    assert governance.notes == note


@pytest.mark.parametrize(
    "note",
    (
        "no api calls or downloads allowed",
        "api calls not allowed",
        "allowed not api calls",
        "runtime remains blocked but we do not approve source use",
        "no api calls allowed but no source use allowed",
    ),
)
def test_preference_recipe_mapping_allows_explicitly_negated_note_approvals(
    note: str,
) -> None:
    payload = _governance_payload()
    payload["notes"] = note

    governance = parse_preference_recipe_mapping_governance(
        payload,
        coverage=_coverage(),
        recipe_dish_corpus=_recipe_dish_corpus(),
    )

    assert governance.notes == note


def test_preference_recipe_mapping_notes_guard_does_not_reject_substrings() -> None:
    payload = _governance_payload()
    payload["notes"] = "PR15 keeps non-authoritative recipe text paths blocked."

    governance = parse_preference_recipe_mapping_governance(
        payload,
        coverage=_coverage(),
        recipe_dish_corpus=_recipe_dish_corpus(),
    )

    assert "non-authoritative recipe text" in governance.notes


def test_preference_recipe_mapping_rejects_schema_reference_and_next_lane_drift() -> None:
    payload = _governance_payload()
    payload["schema_version"] = "wrong.v1"
    with pytest.raises(PreferenceRecipeMappingError, match="schema_version"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    payload["unexpected"] = "runtime"
    with pytest.raises(PreferenceRecipeMappingError, match="unexpected keys"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    payload["coverage_ref"] = "wrong.json"
    with pytest.raises(PreferenceRecipeMappingError, match="coverage_ref"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    payload["recipe_dish_corpus_ref"] = "wrong.json"
    with pytest.raises(PreferenceRecipeMappingError, match="recipe_dish_corpus_ref"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    payload["pr11_landed_pr"] = 0
    with pytest.raises(PreferenceRecipeMappingError, match="pr11_landed_pr"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    payload["pr14_landed_pr"] = 0
    with pytest.raises(PreferenceRecipeMappingError, match="pr14_landed_pr"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    payload["source"] = "runtime_source"
    with pytest.raises(PreferenceRecipeMappingError, match="source must be"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    payload["source_classification"] = "runtime_authority"
    with pytest.raises(PreferenceRecipeMappingError, match="source_classification"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    payload["source_family"] = "provider"
    with pytest.raises(PreferenceRecipeMappingError, match="source_family"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    payload["evidence_policy"] = "allows_source_use"
    with pytest.raises(PreferenceRecipeMappingError, match="evidence_policy"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    payload["next_recommended_lane"] = "runtime_ingest"
    with pytest.raises(PreferenceRecipeMappingError, match="next_recommended_lane"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    payload["final_gate_decision"] = "runtime_ready"
    with pytest.raises(PreferenceRecipeMappingError, match="final_gate_decision"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rejects_bad_blocked_methods_payload() -> None:
    payload = _governance_payload()
    blocked_methods = payload["blocked_methods"]
    assert isinstance(blocked_methods, list)
    payload["blocked_methods"] = list(blocked_methods) + ["extra"]

    with pytest.raises(PreferenceRecipeMappingError, match="blocked_methods"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    rows = payload["mapping_contracts"]
    assert isinstance(rows, list)
    payload["mapping_contracts"] = list(reversed(rows))
    with pytest.raises(PreferenceRecipeMappingError, match="mapping_contracts must be exactly"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    payload["mapping_contracts"] = "not-a-list"
    with pytest.raises(PreferenceRecipeMappingError, match="mapping_contracts must be a list"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rejects_bad_mapping_contract_rows() -> None:
    payload = _governance_payload()
    _mapping_row(payload, "mediterranean_pattern")["unexpected"] = "runtime"
    with pytest.raises(PreferenceRecipeMappingError, match="unexpected mapping keys"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    _mapping_row(payload, "mediterranean_pattern")["mapping_key"] = "runtime_mapping"
    with pytest.raises(PreferenceRecipeMappingError, match="unknown mapping_key"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    _mapping_row(payload, "mediterranean_pattern")["contract_status"] = "approved_for_runtime"
    with pytest.raises(PreferenceRecipeMappingError, match="contract_status"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    payload = _governance_payload()
    _mapping_row(payload, "mediterranean_pattern")["allowed_role"] = "source_authority"
    with pytest.raises(PreferenceRecipeMappingError, match="allowed_role"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_requires_mapping_payload_and_valid_helpers(
    tmp_path: Path,
) -> None:
    with pytest.raises(PreferenceRecipeMappingError, match="must be an object"):
        parse_preference_recipe_mapping_governance(
            [],
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )

    with pytest.raises(PreferenceRecipeMappingError, match="missing non-empty string"):
        _require_string({}, "missing", "helper")
    with pytest.raises(PreferenceRecipeMappingError, match="must be a boolean"):
        _require_bool({"flag": "false"}, "flag", "helper")
    with pytest.raises(PreferenceRecipeMappingError, match="must be an integer"):
        _require_int({"number": True}, "number", "helper")
    with pytest.raises(PreferenceRecipeMappingError, match="must be a list"):
        _require_string_tuple({"items": "x"}, "items", "helper", expected=("x",))
    with pytest.raises(PreferenceRecipeMappingError, match="non-empty string"):
        _require_string_tuple({"items": [" "]}, "items", "helper", expected=("x",))
    with pytest.raises(PreferenceRecipeMappingError, match="contains duplicate"):
        _require_string_tuple({"items": ["x", "x"]}, "items", "helper", expected=("x",))
    with pytest.raises(PreferenceRecipeMappingError, match="all object keys"):
        _require_mapping({1: "bad"}, "helper")
    with pytest.raises(PreferenceRecipeMappingError, match="YYYY-MM-DD"):
        _parse_date("not-a-date", "helper")
    with pytest.raises(PreferenceRecipeMappingError, match="YYYY-MM-DD"):
        _parse_date("2026-13-99", "helper")
    with pytest.raises(PreferenceRecipeMappingError, match="PR11 coverage_domains is missing"):
        _require_existing_entry({}, "preference_menu_planning", "helper", "coverage_domains")

    outside = tmp_path / "outside.json"
    outside.touch()
    assert "outside.json" in _relative_repo_path(outside)


def test_preference_recipe_mapping_report_returns_validation_errors_for_bad_artifact(
    tmp_path: Path,
) -> None:
    payload = copy.deepcopy(_governance_payload())
    payload["nutrition_authority_allowed"] = True
    bad_path = _write_payload(tmp_path / "bad_preference_mapping.json", payload)

    report = build_preference_recipe_mapping_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        recipe_dish_corpus_path=_RECIPE_DISH_CORPUS_PATH,
        governance_path=bad_path,
    )

    assert report["success"] is False
    assert report["validation_errors"]


def test_preference_recipe_mapping_load_reports_unreadable_json(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad_preference_mapping.json"
    bad_path.write_text("{", encoding="utf-8")

    with pytest.raises(PreferenceRecipeMappingError, match="Cannot read"):
        load_preference_recipe_mapping_governance(
            bad_path,
            coverage=_coverage(),
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_cli_outputs_json_report() -> None:
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
            "--governance",
            str(_GOVERNANCE_PATH),
            "--json",
        ],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=_CLI_TIMEOUT_SECONDS,
    )

    report = json.loads(result.stdout)
    assert report["success"] is True
    assert report["mapping_keys"] == [
        "mediterranean_pattern",
        "gluten_free_constraint",
        "high_protein_preference",
    ]
    assert report["nutrition_authority_allowed"] is False


def test_preference_recipe_mapping_cli_reports_failure(tmp_path: Path) -> None:
    payload = _governance_payload()
    _mapping_row(payload, "gluten_free_constraint")["llm_output_authority_allowed"] = True
    bad_path = _write_payload(tmp_path / "bad_preference_mapping.json", payload)

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
            "--governance",
            str(bad_path),
        ],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_CLI_TIMEOUT_SECONDS,
    )

    assert result.returncode == 1
    assert "food_source_preference_recipe_mapping: FAIL" in result.stdout
    assert "cannot approve source use" in result.stdout
