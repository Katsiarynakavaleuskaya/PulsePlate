from __future__ import annotations

import json
from pathlib import Path
import re

from scripts.ci.check_docs_phase1_gates import check_docs_phase1_guards
from scripts.ci.check_semantic_cache_gate import (
    validate_semantic_cache_observability_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md"
)
SCHEMA = CONTRACT.with_suffix(".schema.json")
REL_CONTRACT = "docs/orchestration/contracts/SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md"


def _contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def test_sc_g3_contract_exists_and_stays_offline_non_serving_gate_closed() -> None:
    text = _contract_text().lower()

    assert "offline only" in text
    assert "non-serving" in text
    assert "gate remains closed" in text
    assert "runtime allowed: false" in text
    assert "implementation allowed: false" in text
    assert "/insight" in text
    assert "does not enable `/insight` serving" in text


def test_checker_passes_current_observability_contract() -> None:
    assert validate_semantic_cache_observability_contract(_contract_text()) == []


def test_checker_fails_if_contract_implies_live_serving_or_gate_open() -> None:
    bad_text = _contract_text() + "\nSC-G3 opens the gate.\n"
    errors = validate_semantic_cache_observability_contract(bad_text)

    assert any("SC-G3 opens gate" in error for error in errors)

    bad_text = _contract_text() + "\nSemantic cache serving is enabled.\n"
    errors = validate_semantic_cache_observability_contract(bad_text)
    assert any("semantic cache serving enabled" in error for error in errors)


def test_checker_fails_if_required_harness_anchors_are_missing() -> None:
    text = _contract_text()
    for phrase in ("negative controls", "stop rules", "rollback thresholds", "blocked surfaces"):
        broken = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
        errors = validate_semantic_cache_observability_contract(broken)
        assert errors, phrase


def test_checker_fails_if_blocked_backends_are_approved() -> None:
    bad_text = _contract_text() + "\nSC-G3 allows embeddings.\nSC-G3 approves Redis/GPTCache.\n"
    errors = validate_semantic_cache_observability_contract(bad_text)

    assert any("SC-G3 allows embeddings" in error for error in errors)
    assert any("SC-G3 approves Redis/GPTCache" in error for error in errors)


def test_schema_required_keys_match_sc_g3_intent() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert schema["required"] == [
        "gate_status",
        "runtime_allowed",
        "implementation_allowed",
        "scaffold_phase",
        "audit_event_fields",
        "risk_classes",
        "negative_controls",
        "required_metrics",
        "stop_rules",
        "kill_switch_snapshot",
        "blocked_surfaces",
        "blocked_backends",
        "required_followups",
    ]
    assert schema["properties"]["gate_status"]["const"] == "closed"
    assert schema["properties"]["runtime_allowed"]["const"] is False
    assert schema["properties"]["implementation_allowed"]["const"] is False
    assert schema["properties"]["scaffold_phase"]["const"] == "SC-G3"


def test_docs_phase1_gate_includes_sc_g3_contract() -> None:
    assert check_docs_phase1_guards([REL_CONTRACT]) == []
