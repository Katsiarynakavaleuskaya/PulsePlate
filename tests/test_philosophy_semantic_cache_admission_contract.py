from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import scripts.ci.check_docs_phase1_gates as docs_phase1
from scripts.ci.check_semantic_cache_gate import (
    PHILOSOPHY_ADMISSION_CLASSES,
    PHILOSOPHY_ADMISSION_FORBIDDEN_PATTERNS,
    PHILOSOPHY_FORBIDDEN_CLAIM_PATTERN_LABELS,
    PHILOSOPHY_SC_G5_LABEL_DUPLICATION_PATTERN_LABELS,
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


def _copy_machine_state() -> dict[str, object]:
    return json.loads(json.dumps(_machine_state()))


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


def test_phase1_docs_gate_rejects_downstream_forbidden_philosophy_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Downstream Philosophy docs cannot bypass PR-1 forbidden-claim checks."""
    relpath = "docs/orchestration/PHILOSOPHY_EPIC_V2_PR1_PACKET_2026-05-17.md"

    def fake_read_text(path: str) -> str:
        if path == relpath:
            return "## Forbidden Claims\n\nphilosophical semantic-cache is live"
        return (REPO_ROOT / path).read_text(encoding="utf-8", errors="replace")

    monkeypatch.setattr(docs_phase1, "_read_text", fake_read_text)

    errors = docs_phase1.check_docs_phase1_guards(markdown_files=[relpath])

    assert (
        f"{relpath}: forbidden philosophy admission contract claim: "
        "philosophical semantic cache live"
    ) in errors


def test_phase1_docs_gate_does_not_scan_review_mapping_for_forbidden_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review artifacts may quote bot findings without becoming downstream product docs."""
    relpath = "docs/review/PR_1761_FIXED_MAPPING.md"

    def fake_read_text(path: str) -> str:
        if path == relpath:
            return "philosophical semantic-cache is live"
        return (REPO_ROOT / path).read_text(encoding="utf-8", errors="replace")

    monkeypatch.setattr(docs_phase1, "_read_text", fake_read_text)

    errors = docs_phase1.check_docs_phase1_guards(markdown_files=[relpath])

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
    assert "write_or_mutate_knowledge_records" in verification_surfaces
    assert "philosophical_outputs_as_canonical_facts" not in verification_surfaces


def test_forbidden_claim_classes_cover_active_detectors() -> None:
    """Every active Philosophy detector must be owned by a governed claim class."""
    active_labels = {
        label
        for label, _pattern in PHILOSOPHY_ADMISSION_FORBIDDEN_PATTERNS
        if label not in PHILOSOPHY_SC_G5_LABEL_DUPLICATION_PATTERN_LABELS
        and not label.startswith("SC-G5 ")
    }
    mapped_labels = {
        label for labels in PHILOSOPHY_FORBIDDEN_CLAIM_PATTERN_LABELS.values() for label in labels
    }

    assert active_labels <= mapped_labels


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


def test_runtime_exclusion_anchors_are_scoped_to_runtime_section() -> None:
    """Runtime-only guardrails must be present in the Runtime-Only Default section."""
    mutated = _contract_text().replace("No Redis imports.", "Runtime imports stay blocked.", 1)
    mutated = mutated.replace(
        "PR-1 and downstream docs must not claim:",
        "PR-1 and downstream docs must not claim:\n\nNo Redis imports.",
        1,
    )

    errors = validate_philosophy_semantic_cache_admission_contract(mutated)

    assert (
        "philosophy admission contract runtime section missing anchor: no Redis imports"
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


def test_schema_validator_requires_governed_array_enums() -> None:
    """All non-empty governed array fields must stay enum-backed."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    verification = properties["verification_bundle_required_surfaces"]
    assert isinstance(verification, dict)
    items = verification["items"]
    assert isinstance(items, dict)
    del items["enum"]

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert (
        "philosophy admission schema enum missing for verification_bundle_required_surfaces"
    ) in errors


def test_schema_validator_rejects_root_constraints_excluding_payload() -> None:
    """Root schema constraints cannot drift beyond the exact contract payload."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    schema["minProperties"] = 99
    schema["maxProperties"] = 1
    schema["allOf"] = [{"required": ["not_present"]}]

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert "philosophy admission schema unsupported root constraint: allOf" in errors
    assert "philosophy admission schema unsupported root constraint: maxProperties" in errors
    assert "philosophy admission schema unsupported root constraint: minProperties" in errors


def test_schema_validator_allows_root_annotations() -> None:
    """Non-validating JSON Schema annotations are allowed at the schema root."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    schema["description"] = "Philosophy admission machine-state schema."
    schema["examples"] = [{}]
    schema["default"] = {}

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert not any("unsupported root constraint" in error for error in errors)


def test_schema_validator_rejects_duplicate_schema_keys() -> None:
    """Raw schema JSON cannot hide a stricter value behind a duplicate key."""
    mutated_schema = SCHEMA.read_text(encoding="utf-8").replace(
        '  "type": "object",',
        '  "type": "array",\n  "type": "object",',
        1,
    )

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=mutated_schema,
        contract_text=_contract_text(),
    )

    assert "philosophy admission schema duplicate key: type" in errors


def test_checker_rejects_duplicate_machine_state_keys() -> None:
    """Duplicate JSON object keys cannot hide an earlier gate-open value."""
    mutated = _contract_text().replace(
        '  "gate_status": "closed",',
        '  "gate_status": "open",\n  "gate_status": "closed",',
        1,
    )

    errors = validate_philosophy_semantic_cache_admission_contract(mutated)

    assert "philosophy admission contract JSON duplicate key: gate_status" in errors


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


def test_schema_validator_rejects_duplicate_required_keys() -> None:
    """Validator rejects duplicate schema required keys before set conversion."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    required = schema["required"]
    assert isinstance(required, list)
    required.append(required[0])

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert "philosophy admission schema required contains duplicates" in errors


def test_schema_validator_rejects_duplicate_enum_values() -> None:
    """Enum-backed admission lists must keep schema enum values unique."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    blocked = properties["blocked_surfaces"]
    assert isinstance(blocked, dict)
    items = blocked["items"]
    assert isinstance(items, dict)
    enum = items["enum"]
    assert isinstance(enum, list)
    enum.append(enum[0])

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert "philosophy admission schema enum contains duplicates for blocked_surfaces" in errors


def test_schema_validator_rejects_non_object_property_schema() -> None:
    """Governed property schemas cannot be boolean schemas."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    properties["gate_status"] = True

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert "philosophy admission schema property must be an object for gate_status" in errors


def test_schema_validator_rejects_scalar_constraints_excluding_payload() -> None:
    """Const scalar fields cannot gain extra schema constraints that reject payload."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    gate_status = properties["gate_status"]
    assert isinstance(gate_status, dict)
    gate_status["minLength"] = 10
    gate_status["pattern"] = "^open$"

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert (
        "philosophy admission schema unsupported scalar constraint for gate_status: minLength"
    ) in errors
    assert (
        "philosophy admission schema unsupported scalar constraint for gate_status: pattern"
    ) in errors


def test_schema_validator_allows_scalar_annotations() -> None:
    """Non-validating JSON Schema annotations do not exclude the contract payload."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    gate_status = properties["gate_status"]
    assert isinstance(gate_status, dict)
    gate_status["description"] = "Closed Philosophy PR-1 admission gate status."
    gate_status["$comment"] = "Operator-facing context only."

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert not any("unsupported scalar constraint for gate_status" in error for error in errors)


def test_schema_validator_rejects_array_constraints_excluding_payload() -> None:
    """Array fields cannot gain unsupported constraints that reject current payload."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    references = properties["references"]
    assert isinstance(references, dict)
    references["contains"] = {"const": "not-present"}
    references["minContains"] = 1

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert (
        "philosophy admission schema unsupported array constraint for references: contains"
        in errors
    )
    assert (
        "philosophy admission schema unsupported array constraint for references: minContains"
    ) in errors


def test_schema_validator_rejects_array_item_constraints_excluding_payload() -> None:
    """Array item schemas cannot gain constraints that reject current payload values."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    references = properties["references"]
    assert isinstance(references, dict)
    items = references["items"]
    assert isinstance(items, dict)
    items["const"] = "not-present"
    items["pattern"] = "^not-present$"
    items["minLength"] = 99
    items["format"] = "uri"

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert (
        "philosophy admission schema unsupported array item constraint for references: const"
    ) in errors
    assert (
        "philosophy admission schema unsupported array item constraint for references: format"
    ) in errors
    assert (
        "philosophy admission schema unsupported array item constraint for references: minLength"
    ) in errors
    assert (
        "philosophy admission schema unsupported array item constraint for references: pattern"
    ) in errors


def test_schema_validator_allows_array_annotations() -> None:
    """Non-validating JSON Schema annotations are allowed on array fields."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    references = properties["references"]
    assert isinstance(references, dict)
    items = references["items"]
    assert isinstance(items, dict)
    references["description"] = "Reference-only upstream evidence paths."
    references["$comment"] = "Operator-facing context only."
    items["description"] = "Reference path value."
    items["$comment"] = "Operator-facing item context only."

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert not any("unsupported array constraint for references" in error for error in errors)
    assert not any("unsupported array item constraint for references" in error for error in errors)


def test_schema_validator_rejects_empty_list_item_constraints() -> None:
    """Empty gate-closed arrays still need item-schema keyword validation."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    deferred = properties["future_cache_candidate_deferred_surfaces"]
    assert isinstance(deferred, dict)
    items = deferred["items"]
    assert isinstance(items, dict)
    items["pattern"] = ".*"

    errors = validate_philosophy_semantic_cache_admission_schema(
        schema_text=json.dumps(schema),
        contract_text=_contract_text(),
    )

    assert (
        "philosophy admission schema unsupported array item constraint for "
        "future_cache_candidate_deferred_surfaces: pattern"
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
    state = _copy_machine_state()
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
    state = _copy_machine_state()
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
    state = _copy_machine_state()
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
    state = _copy_machine_state()
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
    cases = (
        "philosophy admission opens semantic-cache gate",
        "philosophy admission opens semantic cache gate",
        "philosophy pr-1 admission opens the semantic-cache gate",
        "philosophy pr-1 admission opens the semantic cache gate",
        "philosophy pr-1 opens the semantic-cache gate",
        "philosophy pr-1 opens the semantic cache gate",
        "philosophy admission opens the global gate",
        "philosophy pr-1 admission opens the global gate",
        "pr-1 opens the global gate",
        "philosophy admission is equivalent to opening the global gate",
        "philosophy pr-1 is equivalent to opening the global gate",
        "philosophy pr-1 admission is equivalent to opening the global gate",
        "philosophy pr-1 admission is equivalent to opening the semantic-cache gate",
        "philosophy admission is equivalent to opening the semantic cache gate",
        "pr-1 is equivalent to opening the global gate",
        "pr-1 admission is equivalent to opening the global gate",
        "pr-1 admission is equivalent to opening the semantic-cache gate",
        "the semantic-cache gate is open for Philosophy PR-1",
        "Philosophy PR-1 admission can open the semantic-cache gate",
        "the global gate is open for Philosophy PR-1",
        "Philosophy PR-1 admission can open the global gate",
        "Philosophy PR-1 admission may open the global gate",
        "philosophy admission can open the global gate",
        "the semantic-cache gate is open for Philosophy admission",
        "the semantic-cache gate may be opened for Philosophy admission",
        "the global gate can be opened for Philosophy admission",
        "the semantic-cache gate opens for Philosophy admission",
        "the global gate opens for Philosophy admission",
        "the semantic-cache gate is opened for Philosophy admission",
        "the global gate is opened for Philosophy admission",
        "the semantic-cache gate opened for Philosophy admission",
        "the global gate opened for Philosophy admission",
    )

    for claim in cases:
        # Inject forbidden phrase into assertive prose (outside Machine-Readable State
        # and Forbidden Claims sections which are excluded from assertion scanning).
        mutated = _contract_text().replace(
            "does not open the semantic-cache gate",
            f"does not open the semantic-cache gate\n\n{claim}",
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert any("forbidden" in e and "philosophy admission opens gate" in e for e in errors)


def test_runtime_exclusion_anchors_require_local_negation() -> None:
    """Runtime-exclusion anchors require explicit local no/blocked wording."""
    cases = (
        ("No vector search.", "No unrelated prose mentions vector search.", "no vector search"),
        (
            "No connection strings.",
            "No unrelated prose mentions connection strings.",
            "no connection strings",
        ),
        ("No cache adapters.", "No unrelated prose mentions cache adapters.", "no cache adapters"),
    )

    for original, replacement, error_label in cases:
        pattern = re.escape(original).replace(r"\ ", r"\s+")
        mutated = re.sub(pattern, replacement, _contract_text(), count=1)

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert f"philosophy admission contract missing anchor: {error_label}" in errors


def test_forbidden_claims_section_requires_negative_polarity() -> None:
    """Forbidden examples may be excluded only while the section remains prohibitive."""
    cases = (
        "PR-1 and downstream docs may claim:",
        "PR-1 and downstream docs may now claim:",
        "PR-1 and downstream docs are now allowed to claim:",
        "PR-1 and downstream docs must not claim:\n\nPR-1 and downstream docs may claim:",
        "PR-1 and downstream docs must not claim:\n\nAllowed claim: "
        "philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n\nClaim allowed: "
        "philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n\nClaim is allowed: "
        "philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n\nClaim is now allowed: "
        "philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n\nClaims are now allowed: "
        "philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n\nAllowed runtime claim: "
        "philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n\nAllowed runtime claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "- Allowed runtime claim: philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "- Claim is allowed: philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "- PR-1 and downstream docs may claim: philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "* Allowed runtime claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "+ Allowed runtime claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "1. Allowed runtime claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "1) Allowed runtime claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "2) PR-1 and downstream docs may claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "10) Claim is allowed:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "> Allowed runtime claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "- > Allowed runtime claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "* > PR-1 and downstream docs may claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "1) > Claim is allowed:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "- > - Allowed runtime claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "- > [ ] Allowed runtime claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "* > 1) PR-1 and downstream docs may claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "### Allowed runtime claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "#### PR-1 and downstream docs may claim:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "### Claim is allowed:\n"
        "- philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "- [ ] Allowed runtime claim: philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "- [x] Allowed runtime claim: philosophical semantic-cache is live.",
        "PR-1 and downstream docs must not claim:\n"
        "* [ ] PR-1 and downstream docs may claim: philosophical semantic-cache is live.",
    )

    for replacement in cases:
        mutated = _contract_text().replace(
            "PR-1 and downstream docs must not claim:",
            replacement,
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert (
            "philosophy admission contract Forbidden Claims section must retain "
            "negative must-not-claim polarity"
        ) in errors


def test_forbidden_claims_section_allows_additional_negative_polarity() -> None:
    """Additional negative lead-ins should not be treated as permissive drift."""
    cases = (
        "PR-1 and downstream docs must never claim:",
        "PR-1 and downstream docs are not allowed to claim:",
        "PR-1 and downstream docs are never allowed to claim:",
        "Not allowed runtime claim:",
        "Not permitted runtime claim:",
        "Never approved runtime claim:",
        "No approved runtime claim:",
        "Not currently allowed runtime claim:",
        "Never actually approved runtime claim:",
        "Claim is not allowed:",
        "Claims are never allowed:",
        "Claim is no longer allowed:",
        "Claims are no longer permitted:",
        "Claim is no longer enabled:",
    )

    for extra_negative in cases:
        mutated = _contract_text().replace(
            "PR-1 and downstream docs must not claim:",
            f"PR-1 and downstream docs must not claim:\n\n{extra_negative}",
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert not any("negative must-not-claim polarity" in error for error in errors)


def test_forbidden_runtime_live_claim_rejected() -> None:
    """Validator catches a forbidden 'philosophical semantic cache is live' claim."""
    cases = (
        ("philosophical semantic cache is live", "philosophical semantic cache live"),
        ("philosophical semantic-cache is live", "philosophical semantic cache live"),
        (
            "production-live philosophical cache-key behavior",
            "production-live philosophical cache-key behavior",
        ),
        ("philosophical semantic-cache serving is approved", "philosophical semantic cache live"),
        ("philosophical semantic-cache serving is live", "philosophical semantic cache live"),
        ("philosophical semantic-cache serving is open", "philosophical semantic cache live"),
        (
            "philosophical semantic-cache paths are approved for serving",
            "philosophical semantic cache live",
        ),
        ("philosophical semantic-cache paths are live", "philosophical semantic cache live"),
        ("philosophical semantic-cache paths are open", "philosophical semantic cache live"),
    )

    for claim, error_label in cases:
        mutated = _contract_text().replace(
            "gate remains closed",
            f"gate remains closed\n\n{claim}",
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert any("forbidden" in e and error_label in e for e in errors)


def test_forbidden_claim_after_machine_state_json_rejected() -> None:
    """Machine-state JSON is exempt from claim scanning, but nearby prose is not."""
    mutated = _contract_text().replace(
        "The deferred list is intentionally empty until a future reviewed gate-open PR",
        (
            "philosophical semantic-cache is live.\n\n"
            "The deferred list is intentionally empty until a future reviewed gate-open PR"
        ),
        1,
    )

    errors = validate_philosophy_semantic_cache_admission_contract(mutated)

    assert any("forbidden" in e and "philosophical semantic cache live" in e for e in errors)


def test_forbidden_provider_approval_claim_rejected() -> None:
    """Validator catches Redis/GPTCache approval claims for philosophy cache paths."""
    cases = (
        ("redis is approved for philosophical cache paths", "redis philosophical cache approved"),
        (
            "redis is approved for philosophical semantic-cache paths",
            "redis philosophical cache approved",
        ),
        ("redis is enabled for philosophical cache paths", "redis philosophical cache approved"),
        (
            "redis rollout is approved for philosophical cache paths",
            "redis philosophical cache approved",
        ),
        (
            "redis rollout is approved for the philosophical cache paths",
            "redis philosophical cache approved",
        ),
        (
            "gptcache is approved for philosophical cache paths",
            "gptcache philosophical cache approved",
        ),
        (
            "gptcache is approved for philosophical semantic-cache paths",
            "gptcache philosophical cache approved",
        ),
        (
            "gptcache is enabled for philosophical cache paths",
            "gptcache philosophical cache approved",
        ),
        (
            "gptcache rollout is approved for philosophical cache paths",
            "gptcache philosophical cache approved",
        ),
        (
            "gptcache rollout is approved for the philosophical cache paths",
            "gptcache philosophical cache approved",
        ),
    )

    for claim, error_label in cases:
        mutated = _contract_text().replace(
            "gate remains closed",
            f"gate remains closed\n\n{claim}",
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert any("forbidden" in e and error_label in e for e in errors)


def test_forbidden_pr1_runtime_expansion_claim_rejected() -> None:
    """Validator catches affirmative PR-1 runtime expansion claims."""
    cases = (
        ("redis imports are allowed in PR-1", "redis imports allowed in pr-1"),
        ("redis imports are allowed for Philosophy admission", "redis imports allowed in pr-1"),
        ("redis imports are approved for Philosophy admission", "redis imports allowed in pr-1"),
        ("redis imports are enabled for Philosophy admission", "redis imports allowed in pr-1"),
        ("redis import is approved for Philosophy admission", "redis imports allowed in pr-1"),
        ("GPTCache imports are permitted in PR-1", "gptcache imports allowed in pr-1"),
        (
            "GPTCache imports are permitted for Philosophy admission",
            "gptcache imports allowed in pr-1",
        ),
        (
            "GPTCache imports are enabled for Philosophy admission",
            "gptcache imports allowed in pr-1",
        ),
        (
            "GPTCache import is enabled for Philosophy admission",
            "gptcache imports allowed in pr-1",
        ),
        ("embeddings are permitted in PR-1", "embeddings allowed in pr-1"),
        ("embeddings are permitted for Philosophy admission", "embeddings allowed in pr-1"),
        ("embeddings are approved for Philosophy admission", "embeddings allowed in pr-1"),
        ("embedding is approved for Philosophy admission", "embeddings allowed in pr-1"),
        ("/insight cache wiring is permitted in PR-1", "insight cache wiring allowed in pr-1"),
        (
            "/insight cache wiring is permitted for Philosophy admission",
            "insight cache wiring allowed in pr-1",
        ),
        (
            "/insight cache wiring is enabled for Philosophy admission",
            "insight cache wiring allowed in pr-1",
        ),
        ("vector search is permitted in PR-1", "vector search allowed in pr-1"),
        ("vector search is permitted for Philosophy admission", "vector search allowed in pr-1"),
        ("vector search is enabled for Philosophy admission", "vector search allowed in pr-1"),
        ("connection strings are permitted in PR-1", "connection strings allowed in pr-1"),
        (
            "connection strings are permitted for Philosophy admission",
            "connection strings allowed in pr-1",
        ),
        (
            "connection string is enabled for Philosophy admission",
            "connection strings allowed in pr-1",
        ),
        ("cache adapters are permitted in PR-1", "cache adapters allowed in pr-1"),
        ("cache adapters are permitted for Philosophy admission", "cache adapters allowed in pr-1"),
        (
            "cache adapter is approved for Philosophy admission",
            "cache adapters allowed in pr-1",
        ),
        (
            "cache adaptor is approved for Philosophy admission",
            "cache adapters allowed in pr-1",
        ),
        (
            "cache adaptors are enabled for Philosophy admission",
            "cache adapters allowed in pr-1",
        ),
        ("runtime is enabled for Philosophy admission", "runtime allowed in pr-1"),
        ("runtime is approved for Philosophy admission", "runtime allowed in pr-1"),
        ("runtime behavior is enabled for Philosophy admission", "runtime allowed in pr-1"),
        ("runtime paths are approved for Philosophy admission", "runtime allowed in pr-1"),
    )

    for claim, error_label in cases:
        mutated = _contract_text().replace(
            "gate remains closed",
            f"gate remains closed\n\n{claim}",
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert any("forbidden" in e and error_label in e for e in errors)


def test_negated_pr1_runtime_expansion_guardrails_allowed() -> None:
    """Validator permits negated PR-1 runtime guardrail wording."""
    cases = (
        "No Redis imports are allowed in PR-1.",
        "No GPTCache imports are permitted in PR-1.",
        "No embeddings are permitted in PR-1.",
        "No /insight cache wiring is permitted in PR-1.",
        "No vector search is permitted in PR-1.",
        "No connection strings are permitted in PR-1.",
        "No cache adapters are permitted in PR-1.",
        "No runtime is enabled for Philosophy admission.",
        "No runtime behavior is approved for Philosophy admission.",
    )

    for claim in cases:
        mutated = _contract_text().replace(
            "gate remains closed",
            f"gate remains closed\n\n{claim}",
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert not any("allowed in pr-1" in e for e in errors)


def test_provider_approval_exclusion_wording_avoids_philosophy_path_detector() -> None:
    """Provider approval exclusions must not trip the philosophy-path detector."""
    cases = (
        "redis rollout is approved by SC-G5, but not for philosophical cache paths",
        "redis is approved for non-philosophical cache paths only",
        "gptcache rollout is approved by SC-G5, but not for philosophical cache paths",
        "gptcache is approved for non-philosophical cache paths only",
    )

    for claim in cases:
        mutated = _contract_text().replace(
            "gate remains closed",
            f"gate remains closed\n\n{claim}",
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert not any("philosophical cache approved" in e for e in errors)


def test_forbidden_verification_optional_claim_rejected() -> None:
    """Validator catches a forbidden 'verification bundles optional for cache' claim."""
    cases = (
        "verification bundles are optional for cache",
        "verification bundle requirement is skipped for cache admission",
        "verification-bundle requirement may be skipped for cache admission",
        "verification-bundle requirement can be skipped for cache admission",
        "verification-bundle requirements may be skipped for cache admission",
        "verification bundle requirements can be skipped for cache admission",
        "verification-bundle requirements are skipped for cache admission",
        "skipped verification-bundle requirement for cache admission",
        "skipped verification-bundle requirements for cache admission",
    )

    for claim in cases:
        mutated = _contract_text().replace(
            "gate remains closed",
            f"gate remains closed\n\n{claim}",
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert any("forbidden" in e and "verification bundle optional" in e for e in errors)


def test_forbidden_design_intake_override_claim_rejected() -> None:
    """Validator catches claims that PDF/design intake can override repo gates."""
    cases = ("PDF/design intake overrides repo gate markers",)

    for claim in cases:
        mutated = _contract_text().replace(
            "gate remains closed",
            f"gate remains closed\n\n{claim}",
            1,
        )

        errors = validate_philosophy_semantic_cache_admission_contract(mutated)

        assert any("forbidden" in e and "design intake overrides gate markers" in e for e in errors)


def test_checker_requires_admission_classes_complete() -> None:
    """Validator rejects contract when an admission class is missing from JSON."""
    mutated = re.sub(
        r',\s*"future_cache_candidate_deferred"',
        "",
        _contract_text(),
    )

    errors = validate_philosophy_semantic_cache_admission_contract(mutated)

    assert "philosophy admission contract JSON admission_classes set mismatch" in errors
