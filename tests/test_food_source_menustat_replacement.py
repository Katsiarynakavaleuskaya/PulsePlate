"""Tests for the deterministic MenuStat replacement-source gate."""

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

from core.food_sources import menustat_replacement
from core.food_sources.menustat_replacement import (
    MenuStatReplacementError,
    build_menustat_replacement_report,
    load_menustat_replacement_decision,
    parse_menustat_replacement_decision,
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
_DECISION_PATH = (
    _REPO_ROOT / "docs" / "architecture" / "FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_2026-04-30.json"
)
_CLI_MODULE = "scripts.food_source_menustat_replacement"
_FAT_PLATFORM_SOURCE = "fat" + "secret_platform"
_EXPECTED_CANDIDATES = [
    "nutritionix",
    _FAT_PLATFORM_SOURCE,
    "spoonacular",
    "chain_public_nutrition_pages",
]


def _catalog() -> SourceCatalog:
    return load_source_catalog(_CATALOG_PATH)


def _onboarding() -> SourceOnboarding:
    return load_source_onboarding(
        _ONBOARDING_PATH,
        catalog=_catalog(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
    )


def _decision_payload() -> dict[str, object]:
    return json.loads(_DECISION_PATH.read_text(encoding="utf-8"))


def _catalog_payload() -> dict[str, object]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _onboarding_payload() -> dict[str, object]:
    return json.loads(_ONBOARDING_PATH.read_text(encoding="utf-8"))


def _candidate(payload: dict[str, object], source_name: str) -> dict[str, object]:
    candidates = payload["candidate_sources"]
    assert isinstance(candidates, list)
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("source") == source_name:
            return candidate
    raise AssertionError(f"missing candidate {source_name}")


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


def _onboarding_without(source_name: str) -> SourceOnboarding:
    onboarding = _onboarding()
    return replace(
        onboarding,
        sources=tuple(entry for entry in onboarding.sources if entry.source != source_name),
    )


def _onboarding_with_replaced(source_name: str, **changes: object) -> SourceOnboarding:
    onboarding = _onboarding()
    return replace(
        onboarding,
        sources=tuple(
            replace(entry, **changes) if entry.source == source_name else entry
            for entry in onboarding.sources
        ),
    )


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _mutate_menustat_catalog(key: str, value: object, tmp_path: Path) -> Path:
    payload = _catalog_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == "menustat":
            source[key] = value
            break
    return _write_payload(tmp_path / "catalog.json", payload)


def _mutate_candidate_onboarding(source_name: str, key: str, value: object, tmp_path: Path) -> Path:
    payload = _onboarding_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    for source in sources:
        if isinstance(source, dict) and source.get("source") == source_name:
            source[key] = value
            break
    return _write_payload(tmp_path / "onboarding.json", payload)


def test_load_menustat_replacement_decision_accepts_blocked_contract() -> None:
    decision = load_menustat_replacement_decision(
        _DECISION_PATH,
        catalog=_catalog(),
        onboarding=_onboarding(),
        expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
    )

    assert decision.legacy_source == "menustat"
    assert decision.final_gate_decision == "blocked_until_replacement_approved"
    assert [candidate.source for candidate in decision.candidate_sources] == _EXPECTED_CANDIDATES
    assert {candidate.authority_decision for candidate in decision.candidate_sources} == {
        "not_approved",
    }
    assert decision.runtime_cutover is False
    assert decision.network_allowed is False
    assert decision.db_writes_allowed is False


def test_menustat_replacement_report_is_deterministic_json_contract() -> None:
    report = build_menustat_replacement_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=_ONBOARDING_PATH,
        decision_path=_DECISION_PATH,
    )

    assert report == {
        "success": True,
        "dry_run": True,
        "legacy_source": "menustat",
        "runtime_cutover": False,
        "digitalocean_postgres_load": False,
        "bulk_ingest": False,
        "file_only": True,
        "network_allowed": False,
        "db_writes_allowed": False,
        "final_gate_decision": "blocked_until_replacement_approved",
        "validation_errors": [],
        "catalog_ref": "docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
        "onboarding_ref": "docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
        "candidate_count": 4,
        "candidate_sources": _EXPECTED_CANDIDATES,
        "authority_decisions": {
            "nutritionix": "not_approved",
            _FAT_PLATFORM_SOURCE: "not_approved",
            "spoonacular": "not_approved",
            "chain_public_nutrition_pages": "not_approved",
        },
        "candidate_gate_decisions": {
            "nutritionix": "blocked_contract_review_required",
            _FAT_PLATFORM_SOURCE: "blocked_contract_review_required",
            "spoonacular": "blocked_contract_review_required",
            "chain_public_nutrition_pages": "blocked_unresolved_review_required",
        },
    }


@pytest.mark.parametrize(
    ("flag_name", "flag_value"),
    (
        ("runtime_cutover", True),
        ("digitalocean_postgres_load", True),
        ("bulk_ingest", True),
        ("file_only", False),
        ("network_allowed", True),
        ("db_writes_allowed", True),
    ),
)
def test_menustat_replacement_gate_rejects_unsafe_flags(
    flag_name: str,
    flag_value: bool,
) -> None:
    payload = _decision_payload()
    payload[flag_name] = flag_value

    with pytest.raises(MenuStatReplacementError, match="must be false; file_only must be true"):
        parse_menustat_replacement_decision(payload, catalog=_catalog(), onboarding=_onboarding())


@pytest.mark.parametrize(
    ("payload", "match"),
    (
        (None, "must be an object"),
        ({1: "bad-key"}, "all object keys must be strings"),
    ),
)
def test_menustat_replacement_requires_mapping_payload(
    payload: object,
    match: str,
) -> None:
    with pytest.raises(MenuStatReplacementError, match=match):
        parse_menustat_replacement_decision(payload, catalog=_catalog(), onboarding=_onboarding())


@pytest.mark.parametrize(
    ("callable_obj", "match"),
    (
        (
            lambda: menustat_replacement._require_string({}, "name", "helper"),
            "missing non-empty string",
        ),
        (
            lambda: menustat_replacement._require_bool({"flag": "yes"}, "flag", "helper"),
            "must be a boolean",
        ),
        (
            lambda: menustat_replacement._require_string_tuple(
                {"items": "bad"},
                "items",
                "helper",
            ),
            "list of strings",
        ),
        (
            lambda: menustat_replacement._require_string_tuple(
                {"items": [""]},
                "items",
                "helper",
            ),
            "non-empty string",
        ),
        (
            lambda: menustat_replacement._parse_date("20260430", "helper"),
            "YYYY-MM-DD",
        ),
    ),
)
def test_menustat_replacement_helper_failures_are_stable(
    callable_obj: Callable[[], object],
    match: str,
) -> None:
    with pytest.raises(MenuStatReplacementError, match=match):
        callable_obj()


@pytest.mark.parametrize(
    ("field_name", "field_value", "match"),
    (
        ("schema_version", "invalid", "schema_version must look"),
        ("generated_on", "2026-02-31", "generated_on must use YYYY-MM-DD"),
        ("legacy_source", "nutritionix", "legacy_source must be menustat"),
        ("catalog_ref", "wrong.json", "catalog_ref must be"),
        ("onboarding_ref", "wrong.json", "onboarding_ref must be"),
        ("candidate_sources", "not-a-list", "candidate_sources must be a list"),
        ("final_gate_decision", "approved_ingest", "final_gate_decision must be"),
    ),
)
def test_menustat_replacement_rejects_top_level_contract_drift(
    field_name: str,
    field_value: object,
    match: str,
) -> None:
    payload = _decision_payload()
    payload[field_name] = field_value

    with pytest.raises(MenuStatReplacementError, match=match):
        parse_menustat_replacement_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
            expected_catalog_ref="docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json",
            expected_onboarding_ref="docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json",
        )


def test_menustat_replacement_rejects_unexpected_top_level_key() -> None:
    payload = _decision_payload()
    payload["unexpected"] = "value"

    with pytest.raises(MenuStatReplacementError, match="unexpected keys"):
        parse_menustat_replacement_decision(payload, catalog=_catalog(), onboarding=_onboarding())


def test_menustat_replacement_load_reports_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(MenuStatReplacementError, match="Cannot read MenuStat replacement gate"):
        load_menustat_replacement_decision(path, catalog=_catalog(), onboarding=_onboarding())


@pytest.mark.parametrize(
    ("candidate_change", "match"),
    (
        ({"unexpected": "value"}, "unexpected candidate keys"),
        ({"replacement_for": "usda"}, "must replace menustat"),
        ({"authority_decision": "active_authority"}, "cannot be approved"),
        ({"authority_decision": "approved_ingest"}, "cannot be approved"),
        ({"candidate_gate_decision": "approved_ingest"}, "cannot be approved"),
        ({"candidate_gate_decision": "eligible_preflight"}, "cannot become eligible"),
        ({"evidence_status": "approved"}, "evidence_status must remain blocked"),
        ({"contract_status": "approved"}, "contract_status must remain blocked"),
        ({"source_evidence_refs": ["not-a-url"]}, "absolute http"),
        ({"blocking_reasons": []}, "must not be empty"),
        ({"blocking_reasons": ["contract", "contract"]}, "duplicate value"),
    ),
)
def test_menustat_replacement_rejects_candidate_contract_drift(
    candidate_change: dict[str, object],
    match: str,
) -> None:
    payload = _decision_payload()
    candidate = _candidate(payload, "nutritionix")
    candidate.update(candidate_change)

    with pytest.raises(MenuStatReplacementError, match=match):
        parse_menustat_replacement_decision(payload, catalog=_catalog(), onboarding=_onboarding())


@pytest.mark.parametrize(
    ("catalog", "match"),
    (
        (_catalog_without("menustat"), "catalog must include menustat"),
        (
            _catalog_with_replaced("menustat", source_classification="public_dataset"),
            "legacy_static",
        ),
        (_catalog_with_replaced("menustat", status="approved_active_source"), "legacy_baseline"),
        (_catalog_with_replaced("menustat", active_update_source=True), "active update source"),
        (_catalog_with_replaced("menustat", replacement_required=False), "replacement_required"),
    ),
)
def test_menustat_replacement_rejects_menustat_catalog_drift(
    catalog: SourceCatalog,
    match: str,
) -> None:
    with pytest.raises(MenuStatReplacementError, match=match):
        parse_menustat_replacement_decision(
            _decision_payload(),
            catalog=catalog,
            onboarding=_onboarding(),
        )


@pytest.mark.parametrize(
    ("onboarding", "match"),
    (
        (_onboarding_without("menustat"), "onboarding must include menustat"),
        (
            _onboarding_with_replaced("menustat", onboarding_status="eligible_preflight"),
            "legacy_baseline_blocked",
        ),
        (
            _onboarding_with_replaced("menustat", ingestion_path="direct_api_pull"),
            "legacy_snapshot_review_only",
        ),
    ),
)
def test_menustat_replacement_rejects_menustat_onboarding_drift(
    onboarding: SourceOnboarding,
    match: str,
) -> None:
    with pytest.raises(MenuStatReplacementError, match=match):
        parse_menustat_replacement_decision(
            _decision_payload(),
            catalog=_catalog(),
            onboarding=onboarding,
        )


@pytest.mark.parametrize(
    ("catalog", "onboarding", "match"),
    (
        (_catalog_without("nutritionix"), _onboarding(), "catalog missing candidate"),
        (_catalog(), _onboarding_without("nutritionix"), "onboarding missing candidate"),
        (
            _catalog_with_replaced("nutritionix", replacement_for="usda"),
            _onboarding(),
            "cataloged as replacing menustat",
        ),
        (
            _catalog_with_replaced("nutritionix", source_classification="public_dataset"),
            _onboarding(),
            "classification differs from catalog",
        ),
        (
            _catalog_with_replaced("nutritionix", source_family="recipe_corpus"),
            _onboarding(),
            "family differs from catalog",
        ),
        (
            _catalog(),
            _onboarding_with_replaced("nutritionix", onboarding_status="eligible_preflight"),
            "onboarding status differs from PR5",
        ),
    ),
)
def test_menustat_replacement_rejects_candidate_catalog_or_onboarding_drift(
    catalog: SourceCatalog,
    onboarding: SourceOnboarding,
    match: str,
) -> None:
    with pytest.raises(MenuStatReplacementError, match=match):
        parse_menustat_replacement_decision(
            _decision_payload(),
            catalog=catalog,
            onboarding=onboarding,
        )


def test_menustat_replacement_rejects_candidate_policy_mismatch() -> None:
    payload = _decision_payload()
    candidate = _candidate(payload, "nutritionix")
    candidate["source_family"] = "recipe_corpus"

    with pytest.raises(MenuStatReplacementError, match="policy mismatch: source_family"):
        parse_menustat_replacement_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding(),
        )


def test_menustat_replacement_rejects_candidate_eligible_preflight_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _decision_payload()
    candidate = _candidate(payload, "nutritionix")
    candidate["onboarding_status"] = "eligible_preflight"
    expected_policy = dict(menustat_replacement._EXPECTED_CANDIDATE_POLICY["nutritionix"])
    expected_policy["onboarding_status"] = "eligible_preflight"
    monkeypatch.setitem(
        menustat_replacement._EXPECTED_CANDIDATE_POLICY,
        "nutritionix",
        expected_policy,
    )

    with pytest.raises(MenuStatReplacementError, match="must not be eligible_preflight"):
        parse_menustat_replacement_decision(
            payload,
            catalog=_catalog(),
            onboarding=_onboarding_with_replaced(
                "nutritionix",
                onboarding_status="eligible_preflight",
            ),
        )


def test_menustat_replacement_gate_rejects_missing_candidate() -> None:
    payload = _decision_payload()
    candidates = payload["candidate_sources"]
    assert isinstance(candidates, list)
    payload["candidate_sources"] = candidates[:-1]

    with pytest.raises(MenuStatReplacementError, match="candidate_sources must be exactly"):
        parse_menustat_replacement_decision(payload, catalog=_catalog(), onboarding=_onboarding())


def test_menustat_replacement_gate_rejects_unknown_candidate() -> None:
    payload = _decision_payload()
    candidates = payload["candidate_sources"]
    assert isinstance(candidates, list)
    unknown = copy.deepcopy(candidates[-1])
    assert isinstance(unknown, dict)
    unknown["source"] = "edamam_food_database"
    candidates[-1] = unknown

    with pytest.raises(MenuStatReplacementError, match="unknown MenuStat replacement candidate"):
        parse_menustat_replacement_decision(payload, catalog=_catalog(), onboarding=_onboarding())


def test_menustat_replacement_gate_rejects_duplicate_candidate() -> None:
    payload = _decision_payload()
    candidates = payload["candidate_sources"]
    assert isinstance(candidates, list)
    duplicate = copy.deepcopy(candidates[0])
    candidates[-1] = duplicate

    with pytest.raises(MenuStatReplacementError, match="candidate_sources must be exactly"):
        parse_menustat_replacement_decision(payload, catalog=_catalog(), onboarding=_onboarding())


@pytest.mark.parametrize(
    ("field_name", "field_value", "match"),
    (
        ("candidate_gate_decision", "eligible_preflight", "cannot become eligible"),
        ("candidate_gate_decision", "approved_ingest", "cannot be approved"),
        ("authority_decision", "active_authority", "cannot be approved"),
        ("authority_decision", "approved_ingest", "cannot be approved"),
    ),
)
def test_menustat_replacement_gate_rejects_premature_approval(
    field_name: str,
    field_value: str,
    match: str,
) -> None:
    payload = _decision_payload()
    _candidate(payload, "nutritionix")[field_name] = field_value

    with pytest.raises(MenuStatReplacementError, match=match):
        parse_menustat_replacement_decision(payload, catalog=_catalog(), onboarding=_onboarding())


def test_menustat_replacement_gate_rejects_approved_freshness() -> None:
    payload = _decision_payload()
    _candidate(payload, "nutritionix")["freshness_status"] = "approved_current_freshness"

    with pytest.raises(MenuStatReplacementError, match="freshness_status must remain blocked"):
        parse_menustat_replacement_decision(payload, catalog=_catalog(), onboarding=_onboarding())


def test_menustat_replacement_gate_rejects_invalid_evidence_ref() -> None:
    payload = _decision_payload()
    _candidate(payload, "nutritionix")["source_evidence_refs"] = ["not-a-url"]

    with pytest.raises(MenuStatReplacementError, match="absolute http\\(s\\) URLs"):
        parse_menustat_replacement_decision(payload, catalog=_catalog(), onboarding=_onboarding())


def test_menustat_replacement_gate_rejects_active_menustat_catalog(tmp_path: Path) -> None:
    catalog_path = _mutate_menustat_catalog("active_update_source", True, tmp_path)
    report = build_menustat_replacement_report(
        catalog_path=catalog_path,
        onboarding_path=_ONBOARDING_PATH,
        decision_path=_DECISION_PATH,
    )

    assert report["success"] is False
    assert report["runtime_cutover"] is False
    errors = report["validation_errors"]
    assert isinstance(errors, list)
    assert "active update source" in errors[0]


def test_menustat_replacement_gate_rejects_onboarding_eligibility_drift(tmp_path: Path) -> None:
    onboarding_path = _mutate_candidate_onboarding(
        "nutritionix",
        "onboarding_status",
        "eligible_preflight",
        tmp_path,
    )
    report = build_menustat_replacement_report(
        catalog_path=_CATALOG_PATH,
        onboarding_path=onboarding_path,
        decision_path=_DECISION_PATH,
    )

    assert report["success"] is False
    assert report["runtime_cutover"] is False
    errors = report["validation_errors"]
    assert isinstance(errors, list)
    assert "nutritionix" in errors[0]


def test_menustat_replacement_cli_is_file_only_and_json(
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
    assert payload["final_gate_decision"] == "blocked_until_replacement_approved"
    assert payload["candidate_sources"] == _EXPECTED_CANDIDATES
    assert payload["runtime_cutover"] is False
    assert payload["network_allowed"] is False
    assert payload["db_writes_allowed"] is False
    assert result.stderr == ""
    assert after == before


def test_menustat_replacement_cli_prints_validation_errors_without_json(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad_decision.json"
    payload = _decision_payload()
    payload["network_allowed"] = True
    bad_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            _CLI_MODULE,
            "--catalog",
            str(_CATALOG_PATH),
            "--onboarding",
            str(_ONBOARDING_PATH),
            "--decision",
            str(bad_path),
        ],
        cwd=_REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "menustat_replacement: FAIL" in result.stdout
    assert "Validation errors:" in result.stdout
    assert "network_allowed" in result.stdout


def test_menustat_replacement_has_no_network_or_db_dependencies() -> None:
    source_text = Path(menustat_replacement.__file__).read_text(encoding="utf-8")
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
