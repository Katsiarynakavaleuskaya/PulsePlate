"""Tests for the deterministic PR22 dedicated legal-contract review closeout gate."""

from __future__ import annotations

import ast
import copy
import functools
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.food_sources.regional_catalog_dedicated_legal_contract_review import (
    build_regional_catalog_dedicated_legal_contract_review_report,
)
from core.food_sources.regional_catalog_dedicated_legal_contract_review_closeout import (
    BLOCKED_METHODS,
    RegionalCatalogDedicatedLegalContractReviewCloseoutError,
    build_regional_catalog_dedicated_legal_contract_review_closeout_report,
    load_regional_catalog_dedicated_legal_contract_review_closeout_governance,
    parse_regional_catalog_dedicated_legal_contract_review_closeout_governance,
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
_PR22_CLOSEOUT_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "FOOD_DATA_REGIONAL_CATALOG_DEDICATED_LEGAL_CONTRACT_REVIEW_CLOSEOUT_PR22_2026-05-25.json"
)
_CLI_MODULE = "scripts.food_source_regional_catalog_dedicated_legal_contract_review_closeout"
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
_SAFETY_FLAGS = (
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
)


def _pr21_ref() -> str:
    return (
        "docs/architecture/"
        "FOOD_DATA_REGIONAL_CATALOG_DEDICATED_LEGAL_CONTRACT_REVIEW_PR21_2026-05-25.json"
    )


@functools.cache
def _pr21_report() -> dict[str, object]:
    return build_regional_catalog_dedicated_legal_contract_review_report(
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


@functools.cache
def _pr21_payload_template() -> dict[str, object]:
    payload = json.loads(_PR21_LEGAL_REVIEW_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _pr21_payload() -> dict[str, object]:
    return copy.deepcopy(_pr21_payload_template())


@functools.cache
def _closeout_payload_template() -> dict[str, object]:
    payload = json.loads(_PR22_CLOSEOUT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _closeout_payload() -> dict[str, object]:
    return copy.deepcopy(_closeout_payload_template())


def _write_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _candidate(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    candidates = payload["candidate_legal_contract_closeouts"]
    assert isinstance(candidates, list)
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
            return candidate
    raise AssertionError(f"missing candidate {candidate_id}")


def _report(closeout_path: Path | str = _PR22_CLOSEOUT_PATH) -> dict[str, object]:
    return build_regional_catalog_dedicated_legal_contract_review_closeout_report(
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
        pr21_legal_review_path=_PR21_LEGAL_REVIEW_PATH,
        closeout_path=closeout_path,
    )


def test_load_regional_catalog_dedicated_legal_contract_review_closeout_accepts_artifact() -> None:
    gate = load_regional_catalog_dedicated_legal_contract_review_closeout_governance(
        _PR22_CLOSEOUT_PATH,
        pr21_report=_pr21_report(),
        pr21_payload=_pr21_payload(),
        expected_pr21_legal_review_ref=_pr21_ref(),
    )

    assert gate.source == "regional_catalogs"
    assert gate.source_classification == "governance_dedicated_legal_contract_review_closeout_only"
    assert gate.pr21_merged_pr == 1829
    assert gate.pr21_next_recommended_lane == (
        "regional_catalog_dedicated_legal_contract_review_closeout"
    )
    assert gate.next_recommended_lane == "regional_catalog_legal_contract_packet_handoff"
    assert [candidate.candidate_id for candidate in gate.candidate_legal_contract_closeouts] == (
        _EXPECTED_CANDIDATE_IDS
    )
    assert {
        candidate.evidence_confidence for candidate in gate.candidate_legal_contract_closeouts
    } == {"low_unverified"}
    assert {
        candidate.source_authority_status for candidate in gate.candidate_legal_contract_closeouts
    } == {"blocked_not_authority"}


def test_regional_catalog_dedicated_legal_contract_review_closeout_report_contract() -> None:
    report = _report()

    assert report["success"] is True
    assert report["validation_errors"] == []
    assert report["pr21_merged_pr"] == 1829
    assert (
        report["pr21_next_recommended_lane"]
        == "regional_catalog_dedicated_legal_contract_review_closeout"
    )
    assert report["blocked_methods"] == list(BLOCKED_METHODS)
    assert report["candidate_ids"] == _EXPECTED_CANDIDATE_IDS
    assert report["network_allowed"] is False
    assert report["api_calls_allowed"] is False
    assert report["provider_use_allowed"] is False
    assert report["source_authority_allowed"] is False
    assert report["nutrition_authority_allowed"] is False
    assert report["file_only"] is True
    assert report["next_recommended_lane"] == "regional_catalog_legal_contract_packet_handoff"
    candidate_decisions = report["candidate_decisions"]
    assert isinstance(candidate_decisions, dict)
    assert set(candidate_decisions.values()) == {
        "remain_review_only_no_source_or_provider_use_until_dedicated_legal_contract_packet"
    }
    closeout_status = report["candidate_legal_contract_review_closeout_status"]
    assert isinstance(closeout_status, dict)
    assert set(closeout_status.values()) == {"closed_without_legal_approval_or_source_provider_use"}


@pytest.mark.parametrize("flag_name", _SAFETY_FLAGS)
def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_unsafe_flags(
    flag_name: str,
) -> None:
    payload = _closeout_payload()
    payload[flag_name] = True

    with pytest.raises(
        RegionalCatalogDedicatedLegalContractReviewCloseoutError,
        match="unsafe flags",
    ):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            payload,
            pr21_report=_pr21_report(),
            pr21_payload=_pr21_payload(),
        )


def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_file_only_false() -> (
    None
):
    payload = _closeout_payload()
    payload["file_only"] = False

    with pytest.raises(
        RegionalCatalogDedicatedLegalContractReviewCloseoutError,
        match="file_only",
    ):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            payload,
            pr21_report=_pr21_report(),
            pr21_payload=_pr21_payload(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("schema_version", "food-data-source-closeout.v1", "schema_version"),
        ("generated_on", "2026/05/25", "YYYY-MM-DD"),
        ("generated_on", "2026-99-25", "YYYY-MM-DD"),
        ("pr21_dedicated_legal_contract_review_ref", "docs/architecture/other.json", "pr21"),
        ("pr21_merged_pr", True, "integer"),
        ("pr21_merged_pr", 9999, "pr21_merged_pr"),
        ("pr21_merge_marker", "bad", "pr21_merge_marker"),
        ("pr21_next_recommended_lane", "provider_integration", "pr21_next"),
        ("pr21_final_gate_decision", "provider_use_approved", "pr21_final"),
        ("source", "runtime_provider", "source"),
        ("source_classification", "runtime_authority", "source_classification"),
        ("source_family", "provider_runtime", "source_family"),
        ("evidence_policy", "source_authority", "evidence_policy"),
        ("external_research_evidence_role", "source_authority", "external_research"),
        ("legal_review_authority", "legal approval granted", "approve"),
        ("blocked_methods", ["api_call"], "exactly"),
        ("closeout_decision", "Provider use approved.", "approve"),
        ("notes", "browser finding is authority", "approve"),
        ("role_agent_dispatch_status", "listed_only", "role_agent_dispatch_status"),
        ("experiment_runner_policy", "not_applicable", "experiment_runner_policy"),
        ("experiment_runner_status", "not_run", "experiment_runner_status"),
        ("next_recommended_lane", "runtime_provider_integration", "next_recommended_lane"),
        ("final_gate_decision", "provider_use_approved", "final_gate_decision"),
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_malformed_fields(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _closeout_payload()
    payload[field_name] = bad_value

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewCloseoutError, match=match):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            payload,
            pr21_report=_pr21_report(),
            pr21_payload=_pr21_payload(),
            expected_pr21_legal_review_ref=_pr21_ref(),
        )


@pytest.mark.parametrize(
    ("mutator_key", "bad_value", "match"),
    (
        ("closeout_decision", "API calls approved.", "approve"),
        ("notes", "Experiment Runner artifact is authority.", "approve"),
        ("premortem_dispositions", ["PM-PR22-001 legal review complete"], "approve"),
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_unsafe_prose(
    mutator_key: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _closeout_payload()
    payload[mutator_key] = bad_value

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewCloseoutError, match=match):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            payload,
            pr21_report=_pr21_report(),
            pr21_payload=_pr21_payload(),
        )


def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_unexpected_keys() -> (
    None
):
    payload = _closeout_payload()
    payload["provider_use_approved"] = True

    with pytest.raises(
        RegionalCatalogDedicatedLegalContractReviewCloseoutError, match="unexpected"
    ):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            payload,
            pr21_report=_pr21_report(),
            pr21_payload=_pr21_payload(),
        )


@pytest.mark.parametrize("payload", ([], {1: "bad-key"}))
def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_non_mapping(
    payload: object,
) -> None:
    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewCloseoutError):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            payload,
            pr21_report=_pr21_report(),
            pr21_payload=_pr21_payload(),
        )


def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_missing_key() -> None:
    payload = _closeout_payload()
    del payload["pr21_merged_pr"]

    with pytest.raises(
        RegionalCatalogDedicatedLegalContractReviewCloseoutError,
        match="pr21_merged_pr",
    ):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            payload,
            pr21_report=_pr21_report(),
            pr21_payload=_pr21_payload(),
        )


def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_candidate_order_drift() -> (
    None
):
    payload = _closeout_payload()
    candidates = payload["candidate_legal_contract_closeouts"]
    assert isinstance(candidates, list)
    candidates.reverse()

    with pytest.raises(
        RegionalCatalogDedicatedLegalContractReviewCloseoutError,
        match="candidate order",
    ):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            payload,
            pr21_report=_pr21_report(),
            pr21_payload=_pr21_payload(),
        )


def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_candidate_unexpected_key() -> (
    None
):
    payload = _closeout_payload()
    _candidate(payload, "kroger")["legal_approval_url"] = "https://example.invalid"

    with pytest.raises(
        RegionalCatalogDedicatedLegalContractReviewCloseoutError, match="unexpected"
    ):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            payload,
            pr21_report=_pr21_report(),
            pr21_payload=_pr21_payload(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("candidate_id", "unknown", "unknown candidate_id"),
        ("candidate_name", "Wrong", "candidate_name must match PR21"),
        (
            "provider_route_classification",
            "runtime_provider",
            "provider_route_classification must match PR21",
        ),
        ("allowed_role", "provider_use_approved", "allowed_role"),
        ("evidence_confidence", "high_verified", "evidence_confidence"),
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
        ("nutrition_authority_status", "approved", "nutrition_authority_status"),
        ("product_authority_status", "approved", "product_authority_status"),
        ("closeout_status", "provider_use_approved", "closeout_status"),
        ("legal_contract_review_closeout_status", "approved", "legal_contract_review_closeout"),
        ("final_candidate_decision", "source use authorized", "approve"),
        ("next_required_review", "provider_integration", "next_required_review"),
        ("blocking_reasons", ["API calls allowed."], "approve"),
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_candidate_drift(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    payload = _closeout_payload()
    _candidate(payload, "kroger")[field_name] = bad_value

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewCloseoutError, match=match):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            payload,
            pr21_report=_pr21_report(),
            pr21_payload=_pr21_payload(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("success", False, "PR21 dedicated legal-contract review report must succeed"),
        ("next_recommended_lane", "runtime_provider_integration", "PR21 next"),
        ("final_gate_decision", "provider_use_approved", "PR21 final_gate_decision"),
        ("candidate_ids", list(reversed(_EXPECTED_CANDIDATE_IDS)), "PR21 candidate_ids"),
        ("network_allowed", True, "PR21 safety flag drifted"),
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_pr21_report_drift(
    field_name: str,
    bad_value: object,
    match: str,
) -> None:
    report = copy.deepcopy(_pr21_report())
    report[field_name] = bad_value

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewCloseoutError, match=match):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            _closeout_payload(),
            pr21_report=report,
            pr21_payload=_pr21_payload(),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    (
        ("next_recommended_lane", "runtime_provider_integration", "PR21 artifact next"),
        ("final_gate_decision", "provider_use_approved", "PR21 artifact final"),
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_pr21_payload_drift(
    field_name: str,
    bad_value: str,
    match: str,
) -> None:
    pr21_payload = _pr21_payload()
    pr21_payload[field_name] = bad_value

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewCloseoutError, match=match):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            _closeout_payload(),
            pr21_report=_pr21_report(),
            pr21_payload=pr21_payload,
        )


def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_pr21_candidate_order_drift() -> (
    None
):
    pr21_payload = _pr21_payload()
    candidates = pr21_payload["candidate_legal_contract_reviews"]
    assert isinstance(candidates, list)
    candidates.reverse()

    with pytest.raises(RegionalCatalogDedicatedLegalContractReviewCloseoutError, match="order"):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            _closeout_payload(),
            pr21_report=_pr21_report(),
            pr21_payload=pr21_payload,
        )


def test_regional_catalog_dedicated_legal_contract_review_closeout_rejects_pr21_blocking_reason_drift() -> (
    None
):
    pr21_payload = _pr21_payload()
    candidates = pr21_payload["candidate_legal_contract_reviews"]
    assert isinstance(candidates, list)
    first_candidate = candidates[0]
    assert isinstance(first_candidate, dict)
    first_candidate["blocking_reasons"] = ["PR22 closeout text is not PR21 text"]

    with pytest.raises(
        RegionalCatalogDedicatedLegalContractReviewCloseoutError,
        match="PR21 blocking_reasons",
    ):
        parse_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            _closeout_payload(),
            pr21_report=_pr21_report(),
            pr21_payload=pr21_payload,
        )


def test_regional_catalog_dedicated_legal_contract_review_closeout_report_failure_captures_flags(
    tmp_path: Path,
) -> None:
    payload = _closeout_payload()
    payload["network_allowed"] = True
    bad_path = _write_payload(tmp_path / "bad-pr22.json", payload)

    report = _report(bad_path)

    assert report["success"] is False
    assert report["network_allowed"] is True
    assert report["validation_errors"]


def test_regional_catalog_dedicated_legal_contract_review_closeout_report_failure_preserves_malformed_flags(
    tmp_path: Path,
) -> None:
    payload = _closeout_payload()
    payload["network_allowed"] = "true"
    bad_path = _write_payload(tmp_path / "bad-pr22.json", payload)

    report = _report(bad_path)

    assert report["success"] is False
    assert report["network_allowed"] == "true"
    assert "network_allowed" in json.dumps(report["validation_errors"])


@pytest.mark.parametrize("file_contents", ("{not-json", "[]"))
def test_regional_catalog_dedicated_legal_contract_review_closeout_report_failure_captures_bad_paths(
    tmp_path: Path,
    file_contents: str,
) -> None:
    bad_path = tmp_path / "bad-pr22.json"
    bad_path.write_text(file_contents, encoding="utf-8")

    report = _report(bad_path)

    assert report["success"] is False
    assert report["validation_errors"]


def test_regional_catalog_dedicated_legal_contract_review_closeout_report_failure_captures_missing_path(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path / "missing-pr22.json")

    assert report["success"] is False
    assert report["validation_errors"]


def test_regional_catalog_dedicated_legal_contract_review_closeout_load_rejects_unreadable_json(
    tmp_path: Path,
) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(
        RegionalCatalogDedicatedLegalContractReviewCloseoutError, match="Cannot read"
    ):
        load_regional_catalog_dedicated_legal_contract_review_closeout_governance(
            bad_path,
            pr21_report=_pr21_report(),
            pr21_payload=_pr21_payload(),
        )


def test_regional_catalog_dedicated_legal_contract_review_closeout_cli_success_json() -> None:
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
    assert payload["next_recommended_lane"] == "regional_catalog_legal_contract_packet_handoff"


def test_regional_catalog_dedicated_legal_contract_review_closeout_cli_success_text() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", _CLI_MODULE],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert "food_source_regional_catalog_dedicated_legal_contract_review_closeout: PASS" in (
        completed.stdout
    )


def test_regional_catalog_dedicated_legal_contract_review_closeout_cli_failure(
    tmp_path: Path,
) -> None:
    payload = _closeout_payload()
    payload["network_allowed"] = True
    bad_path = _write_payload(tmp_path / "bad-pr22.json", payload)

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
        timeout=30,
    )

    assert completed.returncode == 1
    assert "food_source_regional_catalog_dedicated_legal_contract_review_closeout: FAIL" in (
        completed.stdout
    )
    assert "network_allowed" in completed.stdout


@pytest.mark.parametrize(
    "path",
    (
        _REPO_ROOT
        / "core"
        / "food_sources"
        / "regional_catalog_dedicated_legal_contract_review_closeout.py",
        _REPO_ROOT
        / "scripts"
        / "food_source_regional_catalog_dedicated_legal_contract_review_closeout.py",
    ),
)
def test_regional_catalog_dedicated_legal_contract_review_closeout_import_surface_is_file_only(
    path: Path,
) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_roots = {
        "app",
        "fastapi",
        "google",
        "httpx",
        "requests",
        "slack_sdk",
        "sqlalchemy",
        "supabase",
    }
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert imported_roots.isdisjoint(forbidden_roots)
