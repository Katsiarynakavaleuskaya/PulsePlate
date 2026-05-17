from __future__ import annotations

import json
import re
from pathlib import Path

import scripts.ci.check_docs_phase1_gates as docs_phase1
from scripts.ci.check_semantic_cache_gate import (
    validate_philosophy_semantic_cache_admission_contract,
    validate_philosophy_semantic_cache_admission_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md"
)
SCHEMA = CONTRACT.with_suffix(".schema.json")
REL_CONTRACT = "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md"


def _contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def _machine_state() -> dict[str, object]:
    text = _contract_text()
    anchor = "## Machine-Readable State"
    assert anchor in text
    section = text.split(anchor, maxsplit=1)[1]
    match = re.search(r"```json\n(.*?)\n```", section, re.DOTALL)
    assert match is not None
    state = json.loads(match.group(1))
    assert isinstance(state, dict)
    return state


def test_contract_exists_and_keeps_gate_closed() -> None:
    text = _contract_text().lower()

    assert "philosophy epic v2 pr-1" in text
    assert "does not open the semantic-cache gate" in text
    assert "gate remains closed" in text
    assert "runtime allowed: false" in text
    assert "implementation allowed: false" in text
    assert "does not duplicate" in text and "sc-g5" in text


def test_checker_passes_current_philosophy_admission_contract() -> None:
    assert validate_philosophy_semantic_cache_admission_contract(_contract_text()) == []


def test_schema_matches_machine_state() -> None:
    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=SCHEMA.read_text(encoding="utf-8"),
        contract_text=_contract_text(),
    )
    assert errors == []


def test_phase1_docs_gate_wires_philosophy_admission_contract() -> None:
    errors = docs_phase1.check_docs_phase1_guards(markdown_files=[REL_CONTRACT])
    assert errors == []


def test_machine_state_admission_classes_are_complete() -> None:
    state = _machine_state()
    classes = state["admission_classes"]
    assert isinstance(classes, list)
    assert set(classes) == {
        "runtime_only",
        "blocked_from_cache",
        "verification_bundle_required",
        "future_cache_candidate_deferred",
    }
    assert state["gate_status"] == "closed"
    assert state["sc_g5_merge_commit"] == "cb1db8b40"
    assert state["does_not_duplicate_sc_g5_backend_selection"] is True
    verification_surfaces = state["verification_bundle_required_surfaces"]
    assert isinstance(verification_surfaces, list)
    assert "philosophical_outputs_presentation_risk_canonical_facts" in verification_surfaces
    assert "philosophical_outputs_as_canonical_facts" not in verification_surfaces


def test_checker_requires_blocked_truth_surfaces() -> None:
    mutated = _contract_text().replace(
        '    "medical_or_therapy_routing",\n',
        "",
    )

    errors = validate_philosophy_semantic_cache_admission_contract(mutated)

    assert (
        "philosophy admission contract JSON blocked_surfaces: " "missing medical_or_therapy_routing"
    ) in errors


def test_schema_validator_rejects_missing_blocked_surface_enum() -> None:
    mutated_schema = SCHEMA.read_text(encoding="utf-8").replace(
        '          "medical_or_therapy_routing",\n',
        "",
    )

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=mutated_schema,
        contract_text=_contract_text(),
    )

    assert (
        "philosophy admission schema enum mismatch for blocked_surfaces: "
        "'medical_or_therapy_routing'"
    ) in errors
