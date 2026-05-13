"""Tests for the deterministic PR14 recipe/dish corpus governance gate."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources.recipe_dish_corpus import (
    RecipeDishCorpusGovernanceError,
    build_recipe_dish_corpus_report,
    load_recipe_dish_corpus_governance,
    parse_recipe_dish_corpus_governance,
    _parse_date,
    _relative_repo_path,
    _require_bool,
    _require_int,
    _require_mapping,
    _require_string,
    _require_string_tuple,
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
_PER_CHAIN_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_PER_CHAIN_LEGAL_ANTI_SCRAPING_PR13_2026-04-30.json"
)
_GOVERNANCE_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json"
)
_CLI_MODULE = "scripts.food_source_recipe_dish_corpus"


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
    payload = json.loads(_GOVERNANCE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _review_row(payload: dict[str, object], source: str) -> dict[str, object]:
    rows = payload["recipe_corpus_reviews"]
    assert isinstance(rows, list)
    for row in rows:
        if isinstance(row, dict) and row.get("source") == source:
            return row
    raise AssertionError(f"missing recipe corpus review {source}")


def test_load_recipe_dish_corpus_accepts_canonical_artifact() -> None:
    governance = load_recipe_dish_corpus_governance(
        _GOVERNANCE_PATH,
        onboarding=_onboarding(),
        coverage=_coverage(),
        expected_per_chain_legal_ref=(
            "docs/architecture/FOOD_DATA_PER_CHAIN_LEGAL_ANTI_SCRAPING_PR13_2026-04-30.json"
        ),
        pr13_next_recommended_lane="recipe_dish_corpus_governance",
    )

    assert governance.pr13_landed_pr == 1613
    assert governance.source == "recipe_dish_corpora"
    assert governance.source_family == "recipe_corpus"
    assert governance.next_recommended_lane == "preference_recipe_mapping_contract"
    assert [review.source for review in governance.recipe_corpus_reviews] == [
        "edamam_food_database",
        "spoonacular",
    ]


def test_recipe_dish_corpus_report_is_deterministic_json_contract() -> None:
    report = build_recipe_dish_corpus_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        chain_public_nutrition_path=_CHAIN_PUBLIC_PATH,
        per_chain_legal_path=_PER_CHAIN_PATH,
        governance_path=_GOVERNANCE_PATH,
    )

    assert report == {
        "success": True,
        "dry_run": True,
        "source": "recipe_dish_corpora",
        "source_classification": "commercial_contract_review_only",
        "source_family": "recipe_corpus",
        "evidence_policy": "recipe_dish_corpus_governance_only_no_source_use",
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
        ],
        "recipe_sources": ["edamam_food_database", "spoonacular"],
        "next_recommended_lane": "preference_recipe_mapping_contract",
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
        "file_only": True,
        "final_gate_decision": "recipe_dish_corpus_governance_only_no_ingest",
        "validation_errors": [],
        "per_chain_legal_ref": (
            "docs/architecture/FOOD_DATA_PER_CHAIN_LEGAL_ANTI_SCRAPING_PR13_2026-04-30.json"
        ),
        "pr13_landed_pr": 1613,
        "legal_review_status": {
            "edamam_food_database": "required_not_approved",
            "spoonacular": "required_not_approved",
        },
        "contract_review_status": {
            "edamam_food_database": "required_not_approved",
            "spoonacular": "required_not_approved",
        },
        "cache_decisions": {
            "edamam_food_database": "blocked_contract_required",
            "spoonacular": "blocked_contract_required",
        },
        "redistribution_decisions": {
            "edamam_food_database": "contract_required",
            "spoonacular": "contract_required",
        },
        "allowed_roles": {
            "edamam_food_database": "adjacent_recipe_food_db_review_only",
            "spoonacular": "deferred_recipe_experiment_candidate_only",
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
    ),
)
def test_recipe_dish_corpus_rejects_top_level_unsafe_flags(flag_name: str) -> None:
    payload = _governance_payload()
    payload[flag_name] = True

    with pytest.raises(
        RecipeDishCorpusGovernanceError, match="must be false; file_only must be true"
    ):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )


def test_recipe_dish_corpus_rejects_file_only_false() -> None:
    payload = _governance_payload()
    payload["file_only"] = False

    with pytest.raises(RecipeDishCorpusGovernanceError, match="file_only must be true"):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
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
        "paid_source_use_allowed",
        "cache_authority_allowed",
        "redistribution_allowed",
    ),
)
def test_recipe_dish_corpus_rejects_per_source_unsafe_flags(flag_name: str) -> None:
    payload = _governance_payload()
    _review_row(payload, "edamam_food_database")[flag_name] = True

    with pytest.raises(RecipeDishCorpusGovernanceError, match="cannot approve ingest"):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )


def test_recipe_dish_corpus_rejects_pr13_lane_drift() -> None:
    payload = _governance_payload()

    with pytest.raises(RecipeDishCorpusGovernanceError, match="PR13 must recommend"):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="source_ingest",
        )


def test_recipe_dish_corpus_rejects_missing_review_row() -> None:
    payload = _governance_payload()
    rows = payload["recipe_corpus_reviews"]
    assert isinstance(rows, list)
    payload["recipe_corpus_reviews"] = rows[:1]

    with pytest.raises(
        RecipeDishCorpusGovernanceError, match="recipe_corpus_reviews must be exactly"
    ):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )


@pytest.mark.parametrize(
    ("field_name", "unsafe_value", "expected_error"),
    (
        ("legal_review_status", "approved", "legal_review_status must be required_not_approved"),
        (
            "contract_review_status",
            "approved",
            "contract_review_status must be required_not_approved",
        ),
        ("cache_decision", "approved", "cache_decision must be blocked_contract_required"),
        ("display_decision", "approved", "display_decision must be blocked_contract_required"),
        ("attribution_decision", "approved", "attribution_decision must be required_not_approved"),
        (
            "redistribution_decision",
            "approved",
            "redistribution_decision must be contract_required",
        ),
        (
            "freshness_review_status",
            "approved",
            "freshness_review_status must be required_not_approved",
        ),
        ("schema_review_status", "approved", "schema_review_status must be required_not_approved"),
    ),
)
def test_recipe_dish_corpus_rejects_unsafe_review_decisions(
    field_name: str, unsafe_value: str, expected_error: str
) -> None:
    payload = _governance_payload()
    _review_row(payload, "edamam_food_database")[field_name] = unsafe_value

    with pytest.raises(RecipeDishCorpusGovernanceError, match=expected_error):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )


def test_recipe_dish_corpus_rejects_source_identity_drift() -> None:
    payload = _governance_payload()
    _review_row(payload, "edamam_food_database")["source_classification"] = "current"

    with pytest.raises(RecipeDishCorpusGovernanceError, match="source_classification must match"):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )

    payload = _governance_payload()
    _review_row(payload, "edamam_food_database")["source_family"] = "restaurant_menu"

    with pytest.raises(
        RecipeDishCorpusGovernanceError, match="source_family must be recipe_corpus"
    ):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )


@pytest.mark.parametrize(
    ("payload_path", "unsafe_note"),
    (
        ("top_level", "approved API use for recipe source"),
        ("edamam_food_database", "approved for ingest and runtime use"),
        ("spoonacular", "cache approved for product display"),
        ("top_level", "API calls are allowed for recipe source use"),
        ("edamam_food_database", "source use is allowed for this candidate"),
        ("spoonacular", "paid source use allowed after contract review"),
        ("top_level", "downloads allowed for corpus fixtures"),
        ("edamam_food_database", "DB writes allowed for recipe candidates"),
        ("spoonacular", "product display allowed from cached recipe corpus"),
    ),
)
def test_recipe_dish_corpus_rejects_notes_that_contradict_no_use_policy(
    payload_path: str, unsafe_note: str
) -> None:
    payload = _governance_payload()
    if payload_path == "top_level":
        payload["notes"] = unsafe_note
    else:
        _review_row(payload, payload_path)["notes"] = unsafe_note

    with pytest.raises(RecipeDishCorpusGovernanceError, match="notes must not contradict"):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )


def test_recipe_dish_corpus_rejects_schema_reference_and_next_lane_drift() -> None:
    payload = _governance_payload()
    payload["schema_version"] = "food-data-recipe-dish-corpus-governance"
    with pytest.raises(RecipeDishCorpusGovernanceError, match="must look like"):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )

    payload = _governance_payload()
    payload["per_chain_legal_ref"] = "docs/architecture/other.json"
    with pytest.raises(RecipeDishCorpusGovernanceError, match="per_chain_legal_ref"):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )

    payload = _governance_payload()
    payload["next_recommended_lane"] = "api_integration"
    with pytest.raises(RecipeDishCorpusGovernanceError, match="next_recommended_lane"):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )


def test_recipe_dish_corpus_rejects_bad_blocked_methods_payload() -> None:
    payload = _governance_payload()
    payload["blocked_methods"] = ["scraping", "scraping"]

    with pytest.raises(RecipeDishCorpusGovernanceError, match="contains duplicate value"):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )

    payload = _governance_payload()
    payload["blocked_methods"] = ["scraping"]

    with pytest.raises(RecipeDishCorpusGovernanceError, match="must be exactly"):
        parse_recipe_dish_corpus_governance(
            payload,
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )


def test_recipe_dish_corpus_requires_mapping_payload_and_valid_helpers(tmp_path: Path) -> None:
    with pytest.raises(RecipeDishCorpusGovernanceError, match="must be an object"):
        parse_recipe_dish_corpus_governance(
            payload=[1, 2, 3],
            onboarding=_onboarding(),
            coverage=_coverage(),
            pr13_next_recommended_lane="recipe_dish_corpus_governance",
        )

    assert isinstance(_require_mapping({"a": 1}, "<test>"), dict)
    with pytest.raises(RecipeDishCorpusGovernanceError, match="all object keys must be strings"):
        _require_mapping({1: 1}, "<test>")
    assert _require_string({"x": "  y "}, "x", "<test>") == "y"
    assert _require_bool({"x": True}, "x", "<test>") is True
    assert _require_int({"x": 3}, "x", "<test>") == 3
    with pytest.raises(RecipeDishCorpusGovernanceError, match="'x' must be an integer"):
        _require_int({"x": True}, "x", "<test>")
    assert _parse_date("2026-05-13", "<test>").year == 2026
    with pytest.raises(RecipeDishCorpusGovernanceError, match="generated_on must use YYYY-MM-DD"):
        _parse_date("2026-99-99", "<test>")

    blocked_methods = _governance_payload()["blocked_methods"]
    assert isinstance(blocked_methods, list)
    assert all(isinstance(method, str) for method in blocked_methods)
    methods = list(blocked_methods)
    assert _require_string_tuple(
        {"methods": methods}, "methods", "<test>", expected=tuple(methods)
    ) == tuple(methods)
    outside = tmp_path / "outside.json"
    outside.touch()
    assert "outside.json" in _relative_repo_path(outside)


def test_recipe_dish_corpus_report_returns_validation_errors_for_bad_artifact(
    tmp_path: Path,
) -> None:
    payload = copy.deepcopy(_governance_payload())
    payload["paid_source_use_allowed"] = True
    bad_path = _write_payload(tmp_path / "bad_recipe_governance.json", payload)

    report = build_recipe_dish_corpus_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        coverage_path=_COVERAGE_PATH,
        chain_public_nutrition_path=_CHAIN_PUBLIC_PATH,
        per_chain_legal_path=_PER_CHAIN_PATH,
        governance_path=bad_path,
    )

    assert report["success"] is False
    assert report["validation_errors"]


def test_recipe_dish_corpus_cli_outputs_json_report() -> None:
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
            "--per-chain-legal",
            str(_PER_CHAIN_PATH),
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
    assert report["recipe_sources"] == ["edamam_food_database", "spoonacular"]
    assert report["api_calls_allowed"] is False
    assert report["paid_source_use_allowed"] is False


def test_recipe_dish_corpus_cli_reports_failure(tmp_path: Path) -> None:
    payload = _governance_payload()
    _review_row(payload, "spoonacular")["api_calls_allowed"] = True
    bad_path = _write_payload(tmp_path / "bad_recipe_governance.json", payload)

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
            "--per-chain-legal",
            str(_PER_CHAIN_PATH),
            "--governance",
            str(bad_path),
        ],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "food_source_recipe_dish_corpus: FAIL" in result.stdout
    assert "cannot approve ingest" in result.stdout
