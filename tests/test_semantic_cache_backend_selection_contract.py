from __future__ import annotations

import json
import re
from pathlib import Path

import scripts.ci.check_docs_phase1_gates as docs_phase1
from scripts.ci.check_semantic_cache_gate import (
    validate_semantic_cache_backend_selection_contract,
)
from tests.helpers.semantic_cache_import_guard import (
    assert_no_forbidden_semantic_cache_calls,
    assert_no_forbidden_semantic_cache_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md"
)
SCHEMA = CONTRACT.with_suffix(".schema.json")
REL_CONTRACT = "docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md"
CHECKER = REPO_ROOT / "scripts" / "ci" / "check_semantic_cache_gate.py"


def _contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def _machine_state() -> dict[str, object]:
    match = re.search(r"```json\n(.*?)\n```", _contract_text(), re.DOTALL)
    assert match is not None
    state = json.loads(match.group(1))
    assert isinstance(state, dict)
    return state


def test_contract_exists_and_keeps_gate_closed() -> None:
    text = _contract_text().lower()

    assert "sc-g5 backend selection" in text
    assert "does not open the semantic-cache gate" in text
    assert "gate remains closed" in text
    assert "runtime allowed: false" in text
    assert "implementation allowed: false" in text


def test_checker_passes_current_backend_selection_contract() -> None:
    assert validate_semantic_cache_backend_selection_contract(_contract_text()) == []


def test_checker_rejects_gate_open_or_serving_claims() -> None:
    bad_text = (
        _contract_text()
        + "\nSC-G5 opens the gate.\n"
        + "Semantic-cache serving is ready.\n"
        + "Backend selected for serving.\n"
    )

    errors = validate_semantic_cache_backend_selection_contract(bad_text)

    assert any("SC-G5 opens gate" in error for error in errors)
    assert any("semantic cache serving ready" in error for error in errors)
    assert any("backend selected for serving" in error for error in errors)


def test_checker_rejects_redis_gptcache_runtime_approval_claims() -> None:
    bad_text = (
        _contract_text()
        + "\nRedis is supported.\n"
        + "GPTCache is approved.\n"
        + "Redis/GPTCache are supported.\n"
        + "Redis and GPTCache are approved.\n"
        + "SC-G5 enables Redis.\n"
        + "SC-G5 supports GPTCache.\n"
        + "REDIS_URL is configured.\n"
        + "GPTCACHE_BACKEND is configured.\n"
    )

    errors = validate_semantic_cache_backend_selection_contract(bad_text)

    assert any("Redis approved" in error for error in errors)
    assert any("GPTCache approved" in error for error in errors)
    assert any("Redis/GPTCache approved" in error for error in errors)
    assert any("SC-G5 approves Redis" in error for error in errors)
    assert any("SC-G5 approves GPTCache" in error for error in errors)
    assert any("Redis URL" in error for error in errors)
    assert any("GPTCache env" in error for error in errors)


def test_checker_rejects_missing_required_safety_anchors() -> None:
    required_phrases = (
        "Safety is a hard gate",
        "current-head CI governance proof",
        "kill switch proof",
        "purge/invalidation proof",
        "SC-G2 contract and lineage evidence",
        "SC-G3 audit, negative-control, metric, stop-rule, and kill-switch evidence",
        "SC-G4 bounded `/insight` metadata-only decision evidence",
    )

    for phrase in required_phrases:
        broken = _contract_text().replace(phrase, "")
        errors = validate_semantic_cache_backend_selection_contract(broken)
        assert any("backend selection contract missing anchor" in error for error in errors)


def test_schema_required_keys_and_consts_match_contract_state() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    state = _machine_state()

    required = set(schema["required"])
    for key in (
        "gate_status",
        "runtime_allowed",
        "implementation_allowed",
        "rollout_phase",
        "selection_mode",
        "candidate_backend_labels",
        "label_only_backends",
        "blocked_runtime_dependencies",
        "required_evidence",
        "required_rollback_proof",
        "forbidden_claims",
        "acceptance_criteria",
    ):
        assert key in required
        assert key in state
    assert schema["additionalProperties"] is False
    assert schema["properties"]["gate_status"]["const"] == "closed"
    assert schema["properties"]["runtime_allowed"]["const"] is False
    assert schema["properties"]["implementation_allowed"]["const"] is False
    assert schema["properties"]["rollout_phase"]["const"] == "SC-G5"
    assert state["candidate_backend_labels"] == [
        "in_memory_label",
        "redis_label",
        "gptcache_label",
    ]


def test_checker_rejects_machine_state_drift_even_when_prose_is_safe() -> None:
    bad_text = _contract_text().replace('"runtime_allowed": false', '"runtime_allowed": true')
    errors = validate_semantic_cache_backend_selection_contract(bad_text)

    assert any("JSON runtime_allowed" in error for error in errors)

    bad_text = _contract_text().replace('"Redis imports or clients"', '"Redis client enabled"')
    errors = validate_semantic_cache_backend_selection_contract(bad_text)

    assert any(
        "blocked_runtime_dependencies: missing Redis imports or clients" in error
        for error in errors
    )


def test_docs_phase1_runs_backend_selection_validator() -> None:
    errors = docs_phase1.check_docs_phase1_guards(markdown_files=[REL_CONTRACT])

    assert errors == []


def test_checker_and_contract_have_no_forbidden_imports_or_calls() -> None:
    assert_no_forbidden_semantic_cache_imports(CHECKER)
    assert_no_forbidden_semantic_cache_calls(CHECKER)
