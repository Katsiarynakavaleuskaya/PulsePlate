from __future__ import annotations

import json
import re
from pathlib import Path

import scripts.ci.check_docs_phase1_gates as docs_phase1
from scripts.ci.check_semantic_cache_gate import (
    PHILOSOPHY_ADMISSION_CLASSES,
    PHILOSOPHY_SC_G5_MERGE_SHA,
    PHILOSOPHY_SC_G5_CONTRACT_PATH,
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


def _contract_text_with_state(state: dict[str, object]) -> str:
    text = _contract_text()
    anchor = "## Machine-Readable State"
    assert anchor in text
    section_start = text.index(anchor)
    section = text[section_start:]
    match = re.search(r"```json\n(.*?)\n```", section, re.DOTALL)
    assert match is not None
    payload_start = section_start + match.start(1)
    payload_end = section_start + match.end(1)
    return text[:payload_start] + json.dumps(state, indent=2) + text[payload_end:]


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
    expected = sorted(PHILOSOPHY_ADMISSION_CLASSES)
    assert len(classes) == len(expected)
    assert sorted(classes) == expected
    assert state["gate_status"] == "closed"
    assert state["sc_g5_merge_commit"] == PHILOSOPHY_SC_G5_MERGE_SHA
    assert state["does_not_duplicate_sc_g5_backend_selection"] is True
    verification_surfaces = state["verification_bundle_required_surfaces"]
    assert isinstance(verification_surfaces, list)
    assert "philosophical_outputs_presentation_risk_canonical_facts" in verification_surfaces
    assert "philosophical_outputs_as_canonical_facts" not in verification_surfaces


def test_upstream_contract_prose_uses_exact_machine_references() -> None:
    """Upstream prose paths must not drift beyond the exact reference set."""
    text = _contract_text()
    section = text.split("## Upstream Contracts (Reference Only)", maxsplit=1)[1]
    section = section.split("## Admission Classes", maxsplit=1)[0]
    prose_paths = {item for item in re.findall(r"`([^`]+)`", section) if "/" in item}
    references = _machine_state()["references"]
    assert isinstance(references, list)

    assert prose_paths == set(references)


def test_checker_requires_blocked_truth_surfaces() -> None:
    mutated = re.sub(
        r'\s*"medical_or_therapy_routing"\s*,?\s*\n?',
        "",
        _contract_text(),
    )

    errors = validate_philosophy_semantic_cache_admission_contract(mutated)

    assert (
        "philosophy admission contract JSON blocked_surfaces: " "missing medical_or_therapy_routing"
    ) in errors


def test_schema_validator_rejects_missing_blocked_surface_enum() -> None:
    mutated_schema = re.sub(
        r'\s*"medical_or_therapy_routing"\s*,?\s*\n?',
        "",
        SCHEMA.read_text(encoding="utf-8"),
    )

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=mutated_schema,
        contract_text=_contract_text(),
    )

    assert (
        "philosophy admission schema enum mismatch for blocked_surfaces: "
        "'medical_or_therapy_routing'"
    ) in errors


def test_schema_validator_requires_explicit_array_max_items() -> None:
    """Validator requires enum-backed admission lists to state exact cardinality."""
    mutated_schema = re.sub(
        r',\n      "maxItems": 4',
        "",
        SCHEMA.read_text(encoding="utf-8"),
        count=1,
    )

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=mutated_schema,
        contract_text=_contract_text(),
    )

    assert (
        "philosophy admission schema maxItems mismatch for admission_classes: expected 4"
    ) in errors


def test_schema_validator_requires_required_properties_parity() -> None:
    """Validator keeps required keys, properties, and contract JSON in exact sync."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    del properties["rollout_phase"]

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert (
        "philosophy admission schema required key missing from properties: rollout_phase" in errors
    )
    assert (
        "philosophy admission contract JSON key missing from schema properties: rollout_phase"
    ) in errors


def test_schema_validator_requires_deferred_candidates_to_stay_closed_gate_empty() -> None:
    """Validator rejects schema drift that would allow deferred cache candidates now."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    deferred = properties["future_cache_candidate_deferred_surfaces"]
    assert isinstance(deferred, dict)
    deferred["maxItems"] = 1

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert (
        "philosophy admission schema maxItems mismatch for "
        "future_cache_candidate_deferred_surfaces: expected 0"
    ) in errors


def test_schema_validator_rejects_deferred_candidate_min_items_drift() -> None:
    """An empty gate-closed deferred list cannot gain a positive minItems floor."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    deferred = properties["future_cache_candidate_deferred_surfaces"]
    assert isinstance(deferred, dict)
    deferred["minItems"] = 1

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert (
        "philosophy admission schema minItems mismatch for "
        "future_cache_candidate_deferred_surfaces: expected 0"
    ) in errors


def test_schema_validator_rejects_boolean_deferred_candidate_cardinality() -> None:
    """Boolean cardinality values are invalid even though bool subclasses int."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    deferred = properties["future_cache_candidate_deferred_surfaces"]
    assert isinstance(deferred, dict)
    deferred["minItems"] = False
    deferred["maxItems"] = False

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert (
        "philosophy admission schema minItems mismatch for "
        "future_cache_candidate_deferred_surfaces: expected 0"
    ) in errors
    assert (
        "philosophy admission schema maxItems mismatch for "
        "future_cache_candidate_deferred_surfaces: expected 0"
    ) in errors


def test_checker_rejects_duplicate_machine_state_lists() -> None:
    """Machine-state lists must stay duplicate-free, including references."""
    state = json.loads(json.dumps(_machine_state()))
    blocked = state["blocked_surfaces"]
    references = state["references"]
    assert isinstance(blocked, list)
    assert isinstance(references, list)
    blocked[0] = blocked[1]
    references.append(references[0])

    errors = validate_philosophy_semantic_cache_admission_contract(_contract_text_with_state(state))

    assert "philosophy admission contract JSON blocked_surfaces: contains duplicates" in errors
    assert "philosophy admission contract JSON references contains duplicates" in errors


def test_checker_rejects_non_string_machine_state_lists() -> None:
    """Machine-state lists must contain only strings."""
    state = json.loads(json.dumps(_machine_state()))
    references = state["references"]
    runtime_only = state["runtime_only_surfaces"]
    assert isinstance(references, list)
    assert isinstance(runtime_only, list)
    references[0] = 123
    runtime_only[0] = 123

    errors = validate_philosophy_semantic_cache_admission_contract(_contract_text_with_state(state))

    assert "philosophy admission contract JSON references must be a string list" in errors
    assert "philosophy admission contract JSON runtime_only_surfaces: expected list" in errors


def test_checker_rejects_unallowlisted_runtime_adapter_references() -> None:
    """Closed-gate references cannot smuggle provider/cache adapter surfaces."""
    state = json.loads(json.dumps(_machine_state()))
    references = state["references"]
    assert isinstance(references, list)
    references.append("providers/semantic_cache/runtime_adapter.py")

    errors = validate_philosophy_semantic_cache_admission_contract(_contract_text_with_state(state))

    assert (
        "philosophy admission contract JSON references unexpected "
        "providers/semantic_cache/runtime_adapter.py"
    ) in errors


def test_schema_validator_requires_references_exact_enum() -> None:
    """Schema must keep references enum-backed with exact closed-gate cardinality."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    references = properties["references"]
    assert isinstance(references, dict)
    references["items"] = {"type": "string", "minLength": 1}

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert "philosophy admission schema enum missing for references" in errors


def test_checker_requires_deferred_candidates_to_stay_closed_gate_empty() -> None:
    """The closed gate cannot name future cache candidates yet."""
    state = json.loads(json.dumps(_machine_state()))
    state["future_cache_candidate_deferred_surfaces"] = ["meaning_as_use_cache_key_enrichment"]

    errors = validate_philosophy_semantic_cache_admission_contract(_contract_text_with_state(state))

    assert (
        "philosophy admission contract JSON future_cache_candidate_deferred_surfaces: "
        "must stay empty while gate closed"
    ) in errors


def test_forbidden_sc_g5_label_duplication_rejected() -> None:
    """Philosophy admission prose must not duplicate SC-G5 backend labels."""
    cases = (
        ("in_memory_label", "SC-G5 in-memory label duplicated"),
        ("redis_label", "SC-G5 redis label duplicated"),
        ("gptcache_label", "SC-G5 gptcache label duplicated"),
    )

    for backend_label, error_label in cases:
        mutated = _contract_text().replace(
            "This contract does not open the semantic-cache gate.",
            (
                "This contract does not open the semantic-cache gate.\n\n"
                f"{backend_label} is listed here."
            ),
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert any("forbidden" in e and error_label in e for e in errors)


def test_forbidden_sc_g5_label_assertive_verbs_rejected() -> None:
    """Assertive prose cannot document, name, or enumerate SC-G5 backend labels."""
    cases = (
        ("in_memory_label", "SC-G5 in-memory label duplicated"),
        ("redis_label", "SC-G5 redis label duplicated"),
        ("gptcache_label", "SC-G5 gptcache label duplicated"),
    )

    for backend_label, error_label in cases:
        for verb in ("documents", "names", "enumerates"):
            mutated = _contract_text().replace(
                "This contract does not open the semantic-cache gate.",
                (
                    "This contract does not open the semantic-cache gate.\n\n"
                    f"This contract {verb} {backend_label} here."
                ),
                1,
            )

            errors = validate_philosophy_semantic_cache_admission_contract(mutated)

            assert any("forbidden" in e and error_label in e for e in errors)


def test_negative_sc_g5_label_non_duplication_prose_allowed() -> None:
    """Negative guardrail prose can name an SC-G5 label without duplicating it."""
    cases = (
        ("in_memory_label", "SC-G5 in-memory label duplicated"),
        ("redis_label", "SC-G5 redis label duplicated"),
        ("gptcache_label", "SC-G5 gptcache label duplicated"),
    )

    for backend_label, error_label in cases:
        mutated = _contract_text().replace(
            "This contract does not open the semantic-cache gate.",
            (
                "This contract does not open the semantic-cache gate.\n\n"
                f"It must never duplicate `{backend_label}` from SC-G5."
            ),
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert not any(error_label in e for e in errors)


def test_contracted_negative_sc_g5_label_non_duplication_prose_allowed() -> None:
    """Contracted negations before duplication verbs stay allowed guardrails."""
    cases = (
        ("in_memory_label", "can't list", "SC-G5 in-memory label duplicated"),
        ("redis_label", "won't document", "SC-G5 redis label duplicated"),
        ("gptcache_label", "shouldn't enumerate", "SC-G5 gptcache label duplicated"),
    )

    for backend_label, negative_phrase, error_label in cases:
        mutated = _contract_text().replace(
            "This contract does not open the semantic-cache gate.",
            (
                "This contract does not open the semantic-cache gate.\n\n"
                f"PR-1 {negative_phrase} `{backend_label}` from SC-G5."
            ),
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert not any(error_label in e for e in errors)


def test_contracted_negative_sc_g5_label_with_adverb_allowed() -> None:
    """Negation can include a short modifier before the duplication verb."""
    cases = (
        ("in_memory_label", "can't safely list", "SC-G5 in-memory label duplicated"),
        ("redis_label", "won't intentionally document", "SC-G5 redis label duplicated"),
        (
            "gptcache_label",
            "shouldn't accidentally enumerate",
            "SC-G5 gptcache label duplicated",
        ),
    )

    for backend_label, negative_phrase, error_label in cases:
        mutated = _contract_text().replace(
            "This contract does not open the semantic-cache gate.",
            (
                "This contract does not open the semantic-cache gate.\n\n"
                f"PR-1 {negative_phrase} `{backend_label}` from SC-G5."
            ),
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert not any(error_label in e for e in errors)


def test_assertive_sc_g5_label_duplication_with_negation_words_rejected() -> None:
    """Negation words cannot hide assertive duplication claims."""
    cases = (
        ("redis_label", "not only lists", "SC-G5 redis label duplicated"),
        ("gptcache_label", "does not merely document", "SC-G5 gptcache label duplicated"),
    )

    for backend_label, phrase, error_label in cases:
        mutated = _contract_text().replace(
            "This contract does not open the semantic-cache gate.",
            (
                "This contract does not open the semantic-cache gate.\n\n"
                f"PR-1 {phrase} `{backend_label}` from SC-G5."
            ),
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert any(error_label in e for e in errors)


def test_forbidden_gate_open_claim_rejected() -> None:
    """Validator catches a forbidden gate-open assertion in prose."""
    text = _contract_text()
    # Inject forbidden phrase into assertive prose (outside Machine-Readable State
    # and Forbidden Claims sections which are excluded from assertion scanning).
    mutated = text.replace(
        "does not open the semantic-cache gate",
        "does not open the semantic-cache gate\n\nphilosophy admission opens semantic-cache gate",
        1,
    )

    errors = validate_philosophy_semantic_cache_admission_contract(mutated)

    assert any("forbidden" in e and "philosophy admission opens gate" in e for e in errors)


def test_forbidden_runtime_live_claim_rejected() -> None:
    """Validator catches a forbidden 'philosophical semantic cache is live' claim."""
    text = _contract_text()
    mutated = text.replace(
        "gate remains closed",
        "gate remains closed\n\nphilosophical semantic cache is live",
        1,
    )

    errors = validate_philosophy_semantic_cache_admission_contract(mutated)

    assert any("forbidden" in e and "philosophical semantic cache live" in e for e in errors)


def test_forbidden_verification_optional_claim_rejected() -> None:
    """Validator catches a forbidden 'verification bundles optional for cache' claim."""
    text = _contract_text()
    mutated = text.replace(
        "gate remains closed",
        "gate remains closed\n\nverification bundles are optional for cache",
        1,
    )

    errors = validate_philosophy_semantic_cache_admission_contract(mutated)

    assert any("forbidden" in e and "verification bundle optional" in e for e in errors)


def test_checker_requires_admission_classes_complete() -> None:
    """Validator rejects contract when an admission class is missing from JSON."""
    mutated = re.sub(
        r',\s*"future_cache_candidate_deferred"',
        "",
        _contract_text(),
    )

    errors = validate_philosophy_semantic_cache_admission_contract(mutated)

    assert "philosophy admission contract JSON admission_classes set mismatch" in errors
