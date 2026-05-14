from __future__ import annotations

import json
import re
from pathlib import Path

import scripts.ci.check_docs_phase1_gates as docs_phase1
from scripts.ci.check_semantic_cache_gate import (
    validate_semantic_cache_backend_selection_contract,
    validate_semantic_cache_backend_selection_schema,
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


def _string_list(value: object) -> list[str]:
    assert isinstance(value, list)
    assert all(isinstance(item, str) for item in value)
    return value


def test_contract_exists_and_keeps_gate_closed() -> None:
    text = _contract_text().lower()

    assert "sc-g5 backend selection" in text
    assert "does not open the semantic-cache gate" in text
    assert "gate remains closed" in text
    assert "runtime allowed: false" in text
    assert "implementation allowed: false" in text


def test_checker_passes_current_backend_selection_contract() -> None:
    assert validate_semantic_cache_backend_selection_contract(_contract_text()) == []


def test_checker_binds_json_validation_to_machine_state_block() -> None:
    decoy = """```json
{"gate_status":"open"}
```

"""
    text = decoy + _contract_text()

    assert validate_semantic_cache_backend_selection_contract(text) == []

    broken = _contract_text().replace("## Machine-Readable State", "## Machine State", 1)
    errors = validate_semantic_cache_backend_selection_contract(broken)

    assert any("Machine-Readable State heading" in error for error in errors)


def test_checker_rejects_multiple_machine_state_json_blocks() -> None:
    text = _contract_text().replace(
        "## Premortem Closure",
        """```json
{"gate_status":"closed"}
```

## Premortem Closure""",
        1,
    )

    errors = validate_semantic_cache_backend_selection_contract(text)

    assert any("multiple machine-readable JSON states" in error for error in errors)


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
    assert required == set(state)
    for key in required:
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


def test_machine_state_blocks_every_payload_class_from_contract_prose() -> None:
    state = _machine_state()

    assert set(_string_list(state["blocked_payload_fields"])) >= {
        "raw prompts",
        "raw queries",
        "normalized queries",
        "raw model responses",
        "raw answers",
        "provider payloads",
        "secrets",
        "credentials",
        "authorization headers",
        "cookies",
        "API keys",
        "private keys",
        "local paths",
        "HealthKit-derived sensitive payloads",
        "diagnosis-like health data",
        "highly personalized coaching state",
        "user-account truth",
        "billing/auth/entitlement truth",
        "legal/compliance output truth",
    }


def test_checker_requires_explicit_workforce_memory_blocking_language() -> None:
    bad_text = (
        _contract_text()
        .replace(
            "SC-G5 must not use advisory wiki, workforce memory",
            "SC-G5 mentions advisory wiki and workforce memory",
        )
        .replace('"workforce memory",\n', "")
    )

    errors = validate_semantic_cache_backend_selection_contract(bad_text)

    assert any("workforce memory blocked" in error for error in errors)


def test_checker_validates_backend_selection_schema_against_machine_state() -> None:
    errors = validate_semantic_cache_backend_selection_schema(
        schema_text=SCHEMA.read_text(encoding="utf-8"),
        contract_text=_contract_text(),
    )

    assert errors == []


def test_checker_rejects_schema_drift_from_machine_state() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    schema["type"] = "string"
    schema_text = json.dumps(schema, sort_keys=True)
    errors = validate_semantic_cache_backend_selection_schema(
        schema_text=schema_text,
        contract_text=_contract_text(),
    )
    assert any("root type must be object" in error for error in errors)

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    schema["required"].remove("blocked_payload_fields")
    schema_text = json.dumps(schema, sort_keys=True)

    errors = validate_semantic_cache_backend_selection_schema(
        schema_text=schema_text,
        contract_text=_contract_text(),
    )

    assert any("blocked_payload_fields" in error for error in errors)

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    schema["properties"]["candidate_backend_labels"]["items"]["enum"].append("unsafe_backend")
    schema_text = json.dumps(schema, sort_keys=True)
    errors = validate_semantic_cache_backend_selection_schema(
        schema_text=schema_text,
        contract_text=_contract_text(),
    )
    assert any("enum set mismatch for candidate_backend_labels" in error for error in errors)

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    schema["properties"]["blocked_payload_fields"] = {"type": "string"}
    schema_text = json.dumps(schema, sort_keys=True)
    errors = validate_semantic_cache_backend_selection_schema(
        schema_text=schema_text,
        contract_text=_contract_text(),
    )
    assert any("array type missing for blocked_payload_fields" in error for error in errors)
    assert any("minItems missing for blocked_payload_fields" in error for error in errors)
    assert any("uniqueItems missing for blocked_payload_fields" in error for error in errors)

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    schema["properties"]["runtime_enabled"] = {"type": "boolean"}
    schema_text = json.dumps(schema, sort_keys=True)
    errors = validate_semantic_cache_backend_selection_schema(
        schema_text=schema_text,
        contract_text=_contract_text(),
    )
    assert any("runtime_enabled" in error for error in errors)

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    del schema["properties"]["runtime_allowed"]["const"]
    schema_text = json.dumps(schema, sort_keys=True)
    errors = validate_semantic_cache_backend_selection_schema(
        schema_text=schema_text,
        contract_text=_contract_text(),
    )
    assert any("const missing for runtime_allowed" in error for error in errors)


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

    for required_runtime_block in (
        '"FastAPI"',
        '"OpenAPI"',
        '"DB writes"',
        '"migrations"',
        '"provider calls"',
        '"environment reads"',
        '"network calls"',
        '"file writes"',
        '"Redis imports or clients"',
        '"GPTCache imports or clients"',
        '"cache backend adapters"',
        '"connection strings"',
        '"availability probes"',
        '"vector search"',
        '"embeddings"',
        '"semantic similarity backends"',
        '"dependency additions"',
    ):
        bad_text = _contract_text().replace(required_runtime_block + ",\n", "")
        bad_text = bad_text.replace(",\n    " + required_runtime_block + "\n", "\n")
        errors = validate_semantic_cache_backend_selection_contract(bad_text)
        assert any(required_runtime_block.strip('"') in error for error in errors)

    for required_truth_source in (
        '"advisory wiki"',
        '"workforce memory"',
        '"local support plane"',
        '"GraphRAG"',
        '"knowledge graph runtime output"',
        '"plugin/control-plane output"',
        '"second source of truth"',
    ):
        bad_text = _contract_text().replace(required_truth_source + ",\n", "")
        bad_text = bad_text.replace(",\n    " + required_truth_source + "\n", "\n")
        errors = validate_semantic_cache_backend_selection_contract(bad_text)
        assert any(required_truth_source.strip('"') in error for error in errors)

    for required_evidence in (
        '"source fingerprints"',
        '"eval event IDs"',
        '"admission decision ID"',
        '"promotion IDs"',
        '"replay entry IDs"',
        '"evidence fingerprints"',
    ):
        bad_text = _contract_text().replace(required_evidence + ",\n", "")
        errors = validate_semantic_cache_backend_selection_contract(bad_text)
        assert any(required_evidence.strip('"') in error for error in errors)

    for required_rollback_proof in (
        '"kill switch proof"',
        '"request bypass proof"',
        '"no-cache fallback proof"',
        '"purge/invalidation proof"',
        '"disabled-state test IDs"',
        '"stop-rule replay IDs"',
        '"rollback runbook ID"',
        '"rollback blast radius basis points"',
    ):
        bad_text = _contract_text().replace(required_rollback_proof + ",\n", "")
        bad_text = bad_text.replace(",\n    " + required_rollback_proof + "\n", "\n")
        bad_text = bad_text.replace(required_rollback_proof + "\n", "")
        errors = validate_semantic_cache_backend_selection_contract(bad_text)
        assert any(required_rollback_proof.strip('"') in error for error in errors)

    bad_text = _contract_text().replace('"human approval record"\n', '"human approval"\n')
    errors = validate_semantic_cache_backend_selection_contract(bad_text)
    assert any("human approval record" in error for error in errors)

    for required_forbidden_claim in (
        '"active semantic-cache claim"',
        '"enabled semantic-cache claim"',
        '"open semantic-cache claim"',
        '"approved Redis rollout claim"',
        '"approved GPTCache rollout claim"',
        '"serving backend selection claim"',
        '"production readiness claim"',
        '"raw prompt caching claim"',
        '"raw response caching claim"',
    ):
        bad_text = _contract_text().replace(required_forbidden_claim + ",\n", "")
        bad_text = bad_text.replace(",\n    " + required_forbidden_claim + "\n", "\n")
        errors = validate_semantic_cache_backend_selection_contract(bad_text)
        assert any(required_forbidden_claim.strip('"') in error for error in errors)

    bad_text = _contract_text().replace(
        '"blocked_payload_fields": [',
        '"blocked_payload_fields_removed": [',
    )
    errors = validate_semantic_cache_backend_selection_contract(bad_text)

    assert any("missing required key: blocked_payload_fields" in error for error in errors)
    assert any("unexpected key: blocked_payload_fields_removed" in error for error in errors)

    bad_text = _contract_text().replace('"acceptance_criteria": [', '"acceptance": [')
    errors = validate_semantic_cache_backend_selection_contract(bad_text)

    assert any("missing required key: acceptance_criteria" in error for error in errors)
    assert any("unexpected key: acceptance" in error for error in errors)


def test_docs_phase1_runs_backend_selection_validator() -> None:
    errors = docs_phase1.check_docs_phase1_guards(markdown_files=[REL_CONTRACT])

    assert errors == []


def test_checker_and_contract_have_no_forbidden_imports_or_calls() -> None:
    assert_no_forbidden_semantic_cache_imports(CHECKER)
    assert_no_forbidden_semantic_cache_calls(CHECKER)
