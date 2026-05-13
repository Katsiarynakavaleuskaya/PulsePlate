"""Tests for the deterministic PR15 preference recipe mapping contract gate."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources.preference_recipe_mapping import (
    PreferenceRecipeMappingError,
    build_preference_recipe_mapping_report,
    load_preference_recipe_mapping_governance,
    parse_preference_recipe_mapping_governance,
    _parse_date,
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
    coverage_payload = copy.deepcopy(_coverage())
    wrong_domains = []
    for domain in coverage_payload.coverage_domains:
        if domain.domain == "preference_menu_planning":
            wrong_domains.append(
                type(domain)(
                    domain=domain.domain,
                    coverage_decision=domain.coverage_decision,
                    primary_sources=domain.primary_sources,
                    auxiliary_sources=domain.auxiliary_sources,
                    gap_status=domain.gap_status,
                    authority_decision=domain.authority_decision,
                    approved_ingest=domain.approved_ingest,
                    approved_runtime_authority=domain.approved_runtime_authority,
                    next_action="some_other_lane",
                    notes=domain.notes,
                )
            )
        else:
            wrong_domains.append(domain)
    coverage_payload = type(coverage_payload)(
        schema_version=coverage_payload.schema_version,
        generated_on=coverage_payload.generated_on,
        catalog_ref=coverage_payload.catalog_ref,
        onboarding_ref=coverage_payload.onboarding_ref,
        pr10_landed_pr=coverage_payload.pr10_landed_pr,
        coverage_domains=tuple(wrong_domains),
        source_gap_decisions=coverage_payload.source_gap_decisions,
        next_recommended_lane=coverage_payload.next_recommended_lane,
        final_gate_decision=coverage_payload.final_gate_decision,
        notes=coverage_payload.notes,
    )

    with pytest.raises(PreferenceRecipeMappingError, match="PR11 preference_menu_planning"):
        parse_preference_recipe_mapping_governance(
            payload,
            coverage=coverage_payload,
            recipe_dish_corpus=_recipe_dish_corpus(),
        )


def test_preference_recipe_mapping_rejects_pr14_lane_drift() -> None:
    payload = _governance_payload()
    recipe_governance = _recipe_dish_corpus()
    recipe_governance = type(recipe_governance)(
        schema_version=recipe_governance.schema_version,
        generated_on=recipe_governance.generated_on,
        per_chain_legal_ref=recipe_governance.per_chain_legal_ref,
        pr13_landed_pr=recipe_governance.pr13_landed_pr,
        source=recipe_governance.source,
        source_classification=recipe_governance.source_classification,
        source_family=recipe_governance.source_family,
        evidence_policy=recipe_governance.evidence_policy,
        blocked_methods=recipe_governance.blocked_methods,
        recipe_corpus_reviews=recipe_governance.recipe_corpus_reviews,
        next_recommended_lane="some_other_lane",
        final_gate_decision=recipe_governance.final_gate_decision,
        notes=recipe_governance.notes,
    )

    with pytest.raises(PreferenceRecipeMappingError, match="PR14 must recommend"):
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
        "source use allowed",
        "api calls approved",
        "runtime authority allowed",
        "db writes allowed",
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
    payload["next_recommended_lane"] = "runtime_ingest"
    with pytest.raises(PreferenceRecipeMappingError, match="next_recommended_lane"):
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
    with pytest.raises(PreferenceRecipeMappingError, match="contains duplicate"):
        _require_string_tuple({"items": ["x", "x"]}, "items", "helper", expected=("x",))
    with pytest.raises(PreferenceRecipeMappingError, match="all object keys"):
        _require_mapping({1: "bad"}, "helper")
    with pytest.raises(PreferenceRecipeMappingError, match="YYYY-MM-DD"):
        _parse_date("2026-13-99", "helper")

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
    )

    assert result.returncode == 1
    assert "food_source_preference_recipe_mapping: FAIL" in result.stdout
    assert "cannot approve source use" in result.stdout
