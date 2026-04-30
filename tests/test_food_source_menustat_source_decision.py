"""Tests for the deterministic PR10 MenuStat source-decision gate."""

from __future__ import annotations

import ast
from collections.abc import Callable
import copy
from dataclasses import replace
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources import menustat_source_decision
from core.food_sources.menustat_replacement import (
    MenuStatReplacementDecision,
    load_menustat_replacement_decision,
)
from core.food_sources.menustat_source_decision import (
    MenuStatSourceDecisionError,
    build_menustat_source_decision_report,
    load_menustat_source_decision,
    parse_menustat_source_decision,
)
from core.food_sources.source_catalog import SourceCatalog, load_source_catalog
from core.food_sources.source_onboarding import SourceOnboarding, load_source_onboarding

_REPO_ROOT = Path(__file__).parents[1]
_CATALOG_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json"
)
_ONBOARDING_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json"
)
_REPLACEMENT_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_2026-04-30.json"
)
_DECISION_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_MENUSTAT_SOURCE_DECISION_PR10_2026-04-30.json"
)
_CLI_MODULE = "scripts.food_source_menustat_source_decision"
_FAT_PLATFORM_SOURCE = "fat" + "secret_platform"
_CHAIN_PUBLIC_SOURCE = "chain_public_nutrition_pages"


def _catalog() -> SourceCatalog:
    return load_source_catalog(_CATALOG_PATH)


def _onboarding() -> SourceOnboarding:
    return load_source_onboarding(
        _ONBOARDING_PATH,
        catalog=_catalog(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
    )


def _replacement() -> MenuStatReplacementDecision:
    return load_menustat_replacement_decision(
        _REPLACEMENT_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
    )


def _decision_payload() -> dict[str, object]:
    return json.loads(_DECISION_PATH.read_text(encoding="utf-8"))


def _catalog_payload() -> dict[str, object]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _source_decision(payload: dict[str, object], source_name: str) -> dict[str, object]:
    decisions = payload["source_decisions"]
    assert isinstance(decisions, list)
    for decision in decisions:
        if isinstance(decision, dict) and decision.get("source") == source_name:
            return decision
    raise AssertionError(f"missing source decision {source_name}")


def _replacement_without(source_name: str) -> MenuStatReplacementDecision:
    replacement = _replacement()
    return replace(
        replacement,
        candidate_sources=tuple(
            candidate
            for candidate in replacement.candidate_sources
            if candidate.source != source_name
        ),
    )


def _replacement_with_candidate(
    source_name: str,
    **changes: object,
) -> MenuStatReplacementDecision:
    replacement = _replacement()
    return replace(
        replacement,
        candidate_sources=tuple(
            replace(candidate, **changes) if candidate.source == source_name else candidate
            for candidate in replacement.candidate_sources
        ),
    )


def _mutate_menustat_catalog(key: str, value: object, tmp_path: Path) -> Path:
    payload = _catalog_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == "menustat":
            source[key] = value
            break
    return _write_payload(tmp_path / "catalog.json", payload)


def _catalog_without(source_name: str) -> SourceCatalog:
    catalog = _catalog()
    return replace(
        catalog,
        sources=tuple(entry for entry in catalog.sources if entry.source != source_name),
    )


def _catalog_with_replaced(source_name: str, **changes: object) -> SourceCatalog:
    catalog = _catalog()
    return replace(
        catalog,
        sources=tuple(
            replace(entry, **changes) if entry.source == source_name else entry
            for entry in catalog.sources
        ),
    )


def test_load_menustat_source_decision_accepts_locked_cleanup() -> None:
    decision = load_menustat_source_decision(
        _DECISION_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        replacement=_replacement(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
        expected_replacement_ref=(
            "docs/architecture/FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_2026-04-30.json"
        ),
    )

    assert decision.legacy_source == "menustat"
    assert decision.preferred_research_lane == _CHAIN_PUBLIC_SOURCE
    assert decision.menustat_archival_policy.archival_reference_only is True
    assert decision.menustat_archival_policy.freshness_authority is False
    assert decision.menustat_archival_policy.validation_required_before_use is True
    assert decision.budget_api_review.source == "edamam_food_database"
    assert decision.budget_api_review.starter_budget_usd_per_month == 14
    assert decision.budget_api_review.api_calls_allowed is False
    assert decision.public_web_evidence_policy.automation_allowed is False
    assert decision.public_web_evidence_policy.redistribution_allowed is False
    decisions = {row.source: row.project_source_decision for row in decision.source_decisions}
    assert decisions[_FAT_PLATFORM_SOURCE] == "not_project_source"
    assert decisions[_CHAIN_PUBLIC_SOURCE] == "preferred_research_lane"


def test_menustat_source_decision_report_is_deterministic_json_contract() -> None:
    report = build_menustat_source_decision_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        replacement_path=_REPLACEMENT_PATH,
        decision_path=_DECISION_PATH,
    )

    assert report == {
        "success": True,
        "dry_run": True,
        "legacy_source": "menustat",
        "menustat_archival_reference_only": True,
        "menustat_validation_required_before_use": True,
        "preferred_research_lane": _CHAIN_PUBLIC_SOURCE,
        "budget_api_review_source": "edamam_food_database",
        "budget_api_review_max_usd_per_month": 14,
        "public_web_evidence_policy": "manual_evidence_only_legal_review_required",
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "network_allowed": False,
        "db_writes_allowed": False,
        "api_calls_allowed": False,
        "source_download_allowed": False,
        "scraping_allowed": False,
        "file_only": True,
        "final_gate_decision": "source_decision_locked_no_ingest",
        "validation_errors": [],
        "catalog_ref": "docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        "onboarding_ref": "docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
        "menustat_replacement_ref": (
            "docs/architecture/FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_2026-04-30.json"
        ),
        "project_source_decisions": {
            "nutritionix": "deferred_contract_review",
            _FAT_PLATFORM_SOURCE: "not_project_source",
            "spoonacular": "deferred_recipe_experiments_only",
            _CHAIN_PUBLIC_SOURCE: "preferred_research_lane",
        },
        "research_lane_decisions": {
            "nutritionix": "not_preferred_for_budget_first_lane",
            _FAT_PLATFORM_SOURCE: "rejected_for_project_use",
            "spoonacular": "not_restaurant_authority",
            _CHAIN_PUBLIC_SOURCE: "chain_public_pages_governance_first",
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
    ),
)
def test_menustat_source_decision_rejects_unsafe_flags(flag_name: str) -> None:
    payload = _decision_payload()
    payload[flag_name] = True

    with pytest.raises(MenuStatSourceDecisionError, match="must be false; file_only must be true"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


@pytest.mark.parametrize(
    ("payload", "match"),
    (
        (None, "must be an object"),
        ({1: "bad-key"}, "all object keys must be strings"),
    ),
)
def test_menustat_source_decision_requires_mapping_payload(
    payload: object,
    match: str,
) -> None:
    with pytest.raises(MenuStatSourceDecisionError, match=match):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


@pytest.mark.parametrize(
    ("callable_obj", "match"),
    (
        (
            lambda: menustat_source_decision._require_string({}, "name", "helper"),
            "missing non-empty string",
        ),
        (
            lambda: menustat_source_decision._require_bool({"flag": "yes"}, "flag", "helper"),
            "must be a boolean",
        ),
        (
            lambda: menustat_source_decision._parse_date("20260430", "helper"),
            "YYYY-MM-DD",
        ),
    ),
)
def test_menustat_source_decision_helper_failures_are_stable(
    callable_obj: Callable[[], object],
    match: str,
) -> None:
    with pytest.raises(MenuStatSourceDecisionError, match=match):
        callable_obj()


@pytest.mark.parametrize(
    ("catalog", "match"),
    (
        (_catalog_without("menustat"), "catalog must include menustat"),
        (
            _catalog_with_replaced("menustat", source_classification="public_dataset"),
            "classification",
        ),
        (_catalog_with_replaced("menustat", active_update_source=True), "active_update_source"),
        (_catalog_with_replaced("menustat", replacement_required=False), "replacement_required"),
    ),
)
def test_menustat_source_decision_rejects_catalog_archival_drift(
    catalog: SourceCatalog,
    match: str,
) -> None:
    with pytest.raises(MenuStatSourceDecisionError, match=match):
        parse_menustat_source_decision(
            _decision_payload(),
            catalog=catalog,
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


@pytest.mark.parametrize(
    ("field_name", "field_value", "match"),
    (
        ("schema_version", "invalid", "schema_version must look"),
        ("generated_on", "2026-02-31", "generated_on must use YYYY-MM-DD"),
        ("catalog_ref", "wrong.json", "catalog_ref must be"),
        ("onboarding_ref", "wrong.json", "onboarding_ref must be"),
        ("menustat_replacement_ref", "wrong.json", "menustat_replacement_ref must be"),
        ("legacy_source", "nutritionix", "legacy_source must be menustat"),
        ("source_decisions", "not-a-list", "source_decisions must be a list"),
        ("final_gate_decision", "approved_ingest", "final_gate_decision must be"),
    ),
)
def test_menustat_source_decision_rejects_top_level_contract_drift(
    field_name: str,
    field_value: object,
    match: str,
) -> None:
    payload = _decision_payload()
    payload[field_name] = field_value

    with pytest.raises(MenuStatSourceDecisionError, match=match):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
            expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
            expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
            expected_replacement_ref=(
                "docs/architecture/FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_2026-04-30.json"
            ),
        )


def test_menustat_source_decision_rejects_unexpected_top_level_key() -> None:
    payload = _decision_payload()
    payload["unexpected"] = "value"

    with pytest.raises(MenuStatSourceDecisionError, match="unexpected keys"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_rejects_source_decision_order_drift() -> None:
    payload = _decision_payload()
    rows = payload["source_decisions"]
    assert isinstance(rows, list)
    payload["source_decisions"] = list(reversed(rows))

    with pytest.raises(MenuStatSourceDecisionError, match="source_decisions must be exactly"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_load_reports_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(MenuStatSourceDecisionError, match="Cannot read MenuStat source decision"):
        load_menustat_source_decision(
            path,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


@pytest.mark.parametrize(
    ("policy_change", "match"),
    (
        ({"unexpected": "value"}, "unexpected archival policy keys"),
        ({"source": "nutritionix"}, "archival policy source must be menustat"),
        ({"source_classification": "public_dataset"}, "legacy_static"),
        ({"archival_reference_only": False}, "archival_reference_only"),
        ({"freshness_authority": True}, "freshness authority"),
        ({"active_update_source": True}, "active update source"),
        ({"replacement_required": False}, "replacement_required"),
        ({"validation_required_before_use": False}, "requires validation"),
        ({"allowed_use": []}, "must not be empty"),
        ({"blocked_use": ["bulk_ingest", "bulk_ingest"]}, "duplicate value"),
    ),
)
def test_menustat_source_decision_rejects_archival_policy_drift(
    policy_change: dict[str, object],
    match: str,
) -> None:
    payload = _decision_payload()
    policy = payload["menustat_archival_policy"]
    assert isinstance(policy, dict)
    policy.update(policy_change)

    with pytest.raises(MenuStatSourceDecisionError, match=match):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


@pytest.mark.parametrize(
    ("review_change", "match"),
    (
        ({"unexpected": "value"}, "unexpected budget API keys"),
        ({"source": "nutritionix"}, "budget API review source"),
        ({"source_family": "restaurant_menu"}, "recipe_corpus"),
        ({"review_lane_decision": "approved"}, "adjacent review only"),
        ({"starter_budget_usd_per_month": "14"}, "must be an integer"),
        ({"starter_budget_usd_per_month": 21}, "between 0 and 20"),
        ({"authority_decision": "approved"}, "cannot approve authority"),
        ({"api_calls_allowed": True}, "cannot approve authority"),
        ({"cache_policy_status": "approved"}, "cache policy"),
        ({"attribution_status": "approved"}, "attribution"),
    ),
)
def test_menustat_source_decision_rejects_budget_api_drift(
    review_change: dict[str, object],
    match: str,
) -> None:
    payload = _decision_payload()
    review = payload["budget_api_review"]
    assert isinstance(review, dict)
    review.update(review_change)

    with pytest.raises(MenuStatSourceDecisionError, match=match):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


@pytest.mark.parametrize(
    ("policy_change", "match"),
    (
        ({"unexpected": "value"}, "unexpected public web policy keys"),
        ({"policy_decision": "automation_allowed"}, "manual evidence only"),
        ({"allowed_surfaces": ["official_restaurant_website"]}, "surfaces must match"),
        ({"allowed_capture_methods": ["url_citation"]}, "capture methods"),
        ({"legal_review_required": False}, "must require legal reviews"),
        ({"anti_scraping_review_required": False}, "must require legal reviews"),
        ({"copyright_review_required": False}, "must require legal reviews"),
        ({"automation_allowed": True}, "cannot approve automation"),
        ({"redistribution_allowed": True}, "cannot approve automation"),
        ({"public_claim_allowed": True}, "cannot approve automation"),
    ),
)
def test_menustat_source_decision_rejects_public_web_policy_drift(
    policy_change: dict[str, object],
    match: str,
) -> None:
    payload = _decision_payload()
    policy = payload["public_web_evidence_policy"]
    assert isinstance(policy, dict)
    policy.update(policy_change)

    with pytest.raises(MenuStatSourceDecisionError, match=match):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


@pytest.mark.parametrize(
    ("decision_change", "match"),
    (
        ({"unexpected": "value"}, "unexpected source decision keys"),
        ({"source": "edamam_food_database"}, "unknown source decision"),
        ({"research_lane_decision": "approved"}, "decision mismatch"),
        ({"authority_decision": "approved"}, "cannot be source authority"),
        ({"automation_approved": True}, "cannot be approved for automation"),
        ({"eligible_preflight": True}, "cannot be approved for automation"),
        ({"approved_ingest": True}, "cannot be approved for automation"),
        ({"blocking_reasons": "not-a-list"}, "must be a list of strings"),
        ({"blocking_reasons": ["", "contract"]}, "must be a non-empty string"),
    ),
)
def test_menustat_source_decision_rejects_source_decision_drift(
    decision_change: dict[str, object],
    match: str,
) -> None:
    payload = _decision_payload()
    decision = _source_decision(payload, "nutritionix")
    decision.update(decision_change)

    with pytest.raises(MenuStatSourceDecisionError, match=match):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


@pytest.mark.parametrize(
    ("replacement", "match"),
    (
        (_replacement_without("nutritionix"), "PR9 replacement artifact missing"),
        (
            _replacement_with_candidate("nutritionix", authority_decision="approved"),
            "PR9 candidate nutritionix became approved",
        ),
        (
            _replacement_with_candidate("nutritionix", replacement_for="usda"),
            "PR9 candidate nutritionix must replace menustat",
        ),
    ),
)
def test_menustat_source_decision_rejects_pr9_replacement_drift(
    replacement: MenuStatReplacementDecision,
    match: str,
) -> None:
    with pytest.raises(MenuStatSourceDecisionError, match=match):
        parse_menustat_source_decision(
            _decision_payload(),
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=replacement,
        )


def test_menustat_source_decision_requires_fatsecret_rejection() -> None:
    payload = _decision_payload()
    _source_decision(payload, _FAT_PLATFORM_SOURCE)[
        "project_source_decision"
    ] = "deferred_contract_review"

    with pytest.raises(MenuStatSourceDecisionError, match="decision mismatch"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_requires_chain_pages_preferred_lane() -> None:
    payload = _decision_payload()
    payload["preferred_research_lane"] = "nutritionix"

    with pytest.raises(MenuStatSourceDecisionError, match="preferred_research_lane"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_rejects_budget_api_calls() -> None:
    payload = _decision_payload()
    budget_review = payload["budget_api_review"]
    assert isinstance(budget_review, dict)
    budget_review["api_calls_allowed"] = True

    with pytest.raises(MenuStatSourceDecisionError, match="cannot approve authority or API calls"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_rejects_over_budget_api_lane() -> None:
    payload = _decision_payload()
    budget_review = payload["budget_api_review"]
    assert isinstance(budget_review, dict)
    budget_review["starter_budget_usd_per_month"] = 29

    with pytest.raises(MenuStatSourceDecisionError, match="between 0 and 20 USD"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_rejects_negative_budget_api_lane() -> None:
    payload = _decision_payload()
    budget_review = payload["budget_api_review"]
    assert isinstance(budget_review, dict)
    budget_review["starter_budget_usd_per_month"] = -5

    with pytest.raises(MenuStatSourceDecisionError, match="between 0 and 20 USD"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_rejects_public_web_automation() -> None:
    payload = _decision_payload()
    web_policy = payload["public_web_evidence_policy"]
    assert isinstance(web_policy, dict)
    web_policy["automation_allowed"] = True

    with pytest.raises(MenuStatSourceDecisionError, match="cannot approve automation"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_requires_public_web_legal_review() -> None:
    payload = _decision_payload()
    web_policy = payload["public_web_evidence_policy"]
    assert isinstance(web_policy, dict)
    web_policy["legal_review_required"] = False

    with pytest.raises(MenuStatSourceDecisionError, match="must require legal reviews"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_rejects_public_web_surface_broadening() -> None:
    payload = _decision_payload()
    web_policy = payload["public_web_evidence_policy"]
    assert isinstance(web_policy, dict)
    allowed_surfaces = web_policy["allowed_surfaces"]
    assert isinstance(allowed_surfaces, list)
    allowed_surfaces.append("third_party_blog")

    with pytest.raises(MenuStatSourceDecisionError, match="approved official-only list"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_rejects_public_web_capture_broadening() -> None:
    payload = _decision_payload()
    web_policy = payload["public_web_evidence_policy"]
    assert isinstance(web_policy, dict)
    allowed_capture_methods = web_policy["allowed_capture_methods"]
    assert isinstance(allowed_capture_methods, list)
    allowed_capture_methods.append("bulk_scraping")

    with pytest.raises(MenuStatSourceDecisionError, match="approved manual methods"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_rejects_automation_approval() -> None:
    payload = _decision_payload()
    _source_decision(payload, _CHAIN_PUBLIC_SOURCE)["automation_approved"] = True

    with pytest.raises(MenuStatSourceDecisionError, match="cannot be approved"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_requires_archival_menustat() -> None:
    payload = _decision_payload()
    archival_policy = payload["menustat_archival_policy"]
    assert isinstance(archival_policy, dict)
    archival_policy["archival_reference_only"] = False

    with pytest.raises(MenuStatSourceDecisionError, match="archival_reference_only"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_requires_validation_before_menustat_use() -> None:
    payload = _decision_payload()
    archival_policy = payload["menustat_archival_policy"]
    assert isinstance(archival_policy, dict)
    archival_policy["validation_required_before_use"] = False

    with pytest.raises(MenuStatSourceDecisionError, match="requires validation"):
        parse_menustat_source_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            replacement=_replacement(),
        )


def test_menustat_source_decision_rejects_active_menustat_catalog(tmp_path: Path) -> None:
    catalog_path = _mutate_menustat_catalog("active_update_source", True, tmp_path)
    report = build_menustat_source_decision_report(
        catalog_path=catalog_path,
        onboarding_path=_ONBOARDING_PATH,
        replacement_path=_REPLACEMENT_PATH,
        decision_path=_DECISION_PATH,
    )

    assert report["success"] is False
    errors = report["validation_errors"]
    assert isinstance(errors, list)
    assert "active update sources" in errors[0]


def test_menustat_source_decision_cli_is_file_only_and_json(
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
            "--replacement",
            str(_REPLACEMENT_PATH),
            "--decision",
            str(_DECISION_PATH),
            "--json",
        ],
        cwd=_REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["project_source_decisions"][_FAT_PLATFORM_SOURCE] == "not_project_source"
    assert payload["preferred_research_lane"] == _CHAIN_PUBLIC_SOURCE
    assert payload["scraping_allowed"] is False
    assert payload["runtime_cutover"] is False
    assert result.stderr == ""
    assert after == before


def test_menustat_source_decision_has_no_network_or_db_dependencies() -> None:
    source_text = Path(menustat_source_decision.__file__).read_text(encoding="utf-8")
    syntax_tree = ast.parse(source_text)

    blocked_roots = {
        "requests",
        "httpx",
        "psycopg",
        "sqlalchemy",
        "digitalocean",
        "subprocess",
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
