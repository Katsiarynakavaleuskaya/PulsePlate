"""Tests for the deterministic PR10 MenuStat source-decision gate."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources import menustat_source_decision
from core.food_sources.menustat_replacement import load_menustat_replacement_decision
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


def _replacement():
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


def _mutate_menustat_catalog(key: str, value: object, tmp_path: Path) -> Path:
    payload = _catalog_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == "menustat":
            source[key] = value
            break
    return _write_payload(tmp_path / "catalog.json", payload)


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

    with pytest.raises(MenuStatSourceDecisionError, match="at or below 20 USD"):
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
