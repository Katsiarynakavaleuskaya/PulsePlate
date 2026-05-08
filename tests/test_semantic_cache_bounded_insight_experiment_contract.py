from __future__ import annotations

import json
from pathlib import Path
import re

from scripts.ci.check_docs_phase1_gates import check_docs_phase1_guards
from scripts.ci.check_semantic_cache_gate import (
    validate_semantic_cache_bounded_insight_experiment_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_BOUNDED_INSIGHT_EXPERIMENT.md"
)
SCHEMA = CONTRACT.with_suffix(".schema.json")
REL_CONTRACT = "docs/orchestration/contracts/SEMANTIC_CACHE_BOUNDED_INSIGHT_EXPERIMENT.md"


def _contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def test_sc_g4_contract_exists_and_keeps_gate_closed_off_by_default() -> None:
    text = _contract_text().lower()

    assert "sc-g4 bounded `/insight` semantic-cache experiment" in text
    assert "does not open the semantic-cache gate" in text
    assert "does not enable runtime caching" in text
    assert "does not enable `/insight` serving" in text
    assert "gate remains closed" in text
    assert "runtime allowed: false" in text
    assert "implementation allowed: false" in text
    assert "off by default" in text


def test_checker_passes_current_bounded_insight_contract() -> None:
    assert validate_semantic_cache_bounded_insight_experiment_contract(_contract_text()) == []


def test_checker_fails_if_contract_implies_live_serving_or_gate_open() -> None:
    bad_text = _contract_text() + "\nSC-G4 opens the gate.\n"
    errors = validate_semantic_cache_bounded_insight_experiment_contract(bad_text)
    assert any("SC-G4 opens gate" in error for error in errors)

    bad_text = _contract_text() + "\nSC-G4 enables /insight serving.\n"
    errors = validate_semantic_cache_bounded_insight_experiment_contract(bad_text)
    assert any("SC-G4 enables insight serving" in error for error in errors)

    bad_text = _contract_text() + "\nSemantic cache can serve /insight responses.\n"
    errors = validate_semantic_cache_bounded_insight_experiment_contract(bad_text)
    assert any("semantic cache can serve insight" in error for error in errors)


def test_checker_fails_if_required_fail_closed_anchors_are_missing() -> None:
    text = _contract_text()
    for phrase in (
        "off by default",
        "request disable",
        "kill switch snapshot",
        "source fingerprints",
        "admission decision ID",
        "response fingerprint",
        "SC-G5 backend selection remains future",
    ):
        broken = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
        errors = validate_semantic_cache_bounded_insight_experiment_contract(broken)
        assert errors


def test_checker_fails_if_backends_or_raw_payloads_are_approved() -> None:
    bad_text = (
        _contract_text()
        + "\nSC-G4 allows embeddings.\n"
        + "SC-G4 enables vector search.\n"
        + "SC-G4 approves Redis/GPTCache.\n"
        + "SC-G4 allows Redis.\n"
        + "SC-G4 permits GPTCache.\n"
        + "SC-G4 allows provider calls.\n"
        + "SC-G4 caches raw prompts.\n"
        + "SC-G4 caches raw responses.\n"
        + "SC-G4 may store raw prompts.\n"
        + "Redis is allowed.\n"
        + "GPTCache is supported.\n"
        + "provider payloads for replay.\n"
        + "Raw answers are allowed.\n"
        + "Advisory wiki may seed product cache.\n"
    )
    errors = validate_semantic_cache_bounded_insight_experiment_contract(bad_text)

    assert any("SC-G4 allows embeddings" in error for error in errors)
    assert any("SC-G4 allows vector search" in error for error in errors)
    assert any("SC-G4 approves Redis/GPTCache" in error for error in errors)
    assert any("SC-G4 allows provider calls" in error for error in errors)
    assert any("cache raw prompts" in error for error in errors)
    assert any("cache raw responses" in error for error in errors)
    assert any("SC-G4 may store raw payloads" in error for error in errors)
    assert any("Redis allowed" in error for error in errors)
    assert any("GPTCache supported" in error for error in errors)
    assert any("provider payloads for replay" in error for error in errors)
    assert any("raw payload allowed" in error for error in errors)
    assert any("advisory wiki seeds product cache" in error for error in errors)


def test_schema_required_keys_match_sc_g4_intent() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert schema["required"] == [
        "gate_status",
        "runtime_allowed",
        "implementation_allowed",
        "rollout_phase",
        "allowed_surface",
        "default_state",
        "feature_flag_sources",
        "required_evidence_linkage_fields",
        "required_decision_fields",
        "blocked_payload_fields",
        "blocked_surfaces",
        "blocked_backends",
        "acceptance_criteria",
    ]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["gate_status"]["const"] == "closed"
    assert schema["properties"]["runtime_allowed"]["const"] is False
    assert schema["properties"]["implementation_allowed"]["const"] is False
    assert schema["properties"]["rollout_phase"]["const"] == "SC-G4"
    assert schema["properties"]["default_state"]["const"] == "off"
    assert "Redis" in schema["properties"]["blocked_backends"]["items"]["enum"]
    assert (
        "response_fingerprint" in schema["properties"]["required_decision_fields"]["items"]["enum"]
    )


def test_docs_phase1_gate_includes_sc_g4_contract() -> None:
    assert check_docs_phase1_guards([REL_CONTRACT]) == []


def test_closed_gate_blocks_runtime_side_door_imports() -> None:
    forbidden_fragments = (
        "core.ai.exact_fuzzy_cache",
        "core.ai.cache_observability",
        "core.ai.bounded_insight_semantic_cache",
    )
    scanned_paths = [
        *(REPO_ROOT / "app").rglob("*.py"),
        REPO_ROOT / "legacy_app.py",
    ]
    offenders: list[str] = []
    for path in scanned_paths:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            if fragment in content:
                offenders.append(f"{path.relative_to(REPO_ROOT)} imports {fragment}")

    assert offenders == []
