from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ci.check_semantic_cache_gate import (
    validate_semantic_cache_context_compression_contract,
    validate_semantic_cache_context_compression_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_CONTEXT_COMPRESSION_TELEMETRY.md"
)
SCHEMA = CONTRACT.with_suffix(".schema.json")
ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"


def _contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def _schema() -> dict[str, object]:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_context_compression_contract_stays_gate_closed_and_non_serving() -> None:
    text = _contract_text().lower()

    assert "metadata-only" in text
    assert "does not open the" in text
    assert "gate status: closed" in text
    assert "runtime allowed: false" in text
    assert "implementation allowed: false" in text
    assert "runtime handoff allowed: false" in text
    assert "cache read allowed: false" in text
    assert "cache write allowed: false" in text
    assert "serving allowed: false" in text
    assert "provider calls allowed: false" in text
    assert "does not provide cache hit rate" in text
    assert "does not implement semantic cache" in text


def test_context_compression_contract_blocks_runtime_raw_payloads_and_quality_loss() -> None:
    text = _contract_text().lower()

    for phrase in (
        "raw prompts",
        "raw queries",
        "normalized queries",
        "raw context snippets",
        "raw model responses",
        "provider payloads",
        "redis",
        "gptcache",
        "embeddings",
        "semantic similarity",
        "vector search",
        "graphrag runtime output",
        "runtime handoff",
        "production cost",
        "roi",
        "merge-readiness evidence",
        "downgrade the review model",
    ):
        assert phrase in text


def test_context_compression_schema_pins_closed_authority_flags_and_fields() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)

    assert properties["gate_status"]["const"] == "closed"
    assert properties["runtime_allowed"]["const"] is False
    assert properties["implementation_allowed"]["const"] is False
    assert properties["runtime_handoff_allowed"]["const"] is False
    assert properties["cache_read_allowed"]["const"] is False
    assert properties["cache_write_allowed"]["const"] is False
    assert properties["serving_allowed"]["const"] is False
    assert properties["provider_calls_allowed"]["const"] is False
    assert properties["telemetry_phase"]["const"] == "PR-O2"
    assert properties["authority_boundary"]["const"] == "metadata_only_non_serving"
    assert properties["asset_type"]["const"] == "orchestration_context_compression_telemetry"

    required = schema["required"]
    assert "upstream_assets" in required
    assert "blocked_payloads" in required
    assert "blocked_backends" in required
    assert "blocked_policy_decisions" in required
    assert "required_followups" in required

    compressed_fields = properties["compressed_context_pack_fields"]["items"]["enum"]
    assert "context_pack_id" in compressed_fields
    assert "selected_context_refs" in compressed_fields
    assert "omitted_duplicate_refs" in compressed_fields

    estimate_fields = properties["context_compression_estimate_fields"]["items"]["enum"]
    assert "baseline_context_tokens_estimate" in estimate_fields
    assert "candidate_context_tokens_estimate" in estimate_fields
    assert "tokens_saved_estimate" in estimate_fields
    assert "fanout_tokens_saved_estimate" in estimate_fields

    assert properties["required_followups"]["minItems"] == 1
    assert properties["required_followups"]["uniqueItems"] is True


def test_context_compression_schema_blocks_runtime_and_policy_decisions() -> None:
    properties = _schema()["properties"]
    assert isinstance(properties, dict)

    blocked_payloads = properties["blocked_payloads"]["items"]["enum"]
    for item in (
        "raw_prompts",
        "raw_queries",
        "normalized_queries",
        "raw_context_snippets",
        "provider_payloads",
        "local_paths",
        "health_sensitive_payloads",
    ):
        assert item in blocked_payloads

    blocked_backends = properties["blocked_backends"]["items"]["enum"]
    for item in (
        "provider_calls",
        "DB",
        "cache_backend",
        "Redis",
        "GPTCache",
        "embeddings",
        "semantic_similarity",
        "vector_search",
        "GraphRAG_runtime",
        "runtime_handoff",
    ):
        assert item in blocked_backends

    policy_decisions = properties["blocked_policy_decisions"]["items"]["enum"]
    for item in (
        "production_cost_claims",
        "production_roi_claims",
        "latency_improvement_claims",
        "quota_improvement_claims",
        "cache_hit_rate_claims",
        "merge_readiness_claims",
        "model_downgrade_decisions",
    ):
        assert item in policy_decisions


def test_context_compression_validators_pass_current_contract_and_schema() -> None:
    assert validate_semantic_cache_context_compression_contract(_contract_text()) == []
    assert (
        validate_semantic_cache_context_compression_schema(SCHEMA.read_text(encoding="utf-8")) == []
    )


@pytest.mark.parametrize(
    "claim,expected",
    (
        ("Context compression enables semantic cache serving.", "runtime serving"),
        ("Context compression stores raw prompts.", "raw prompt"),
        ("Context compression stores raw responses.", "raw response"),
        ("Context compression performs provider calls.", "provider calls"),
        ("Context compression supports provider calls.", "provider calls"),
        ("Context compression approves Redis rollout.", "Redis"),
        ("Context compression supports Redis rollout.", "Redis"),
        ("Context compression approves GPTCache rollout.", "GPTCache"),
        ("Context compression enables embeddings.", "embeddings"),
        ("Context compression supports semantic similarity.", "semantic similarity"),
        ("Context compression supports vector search.", "vector search"),
        ("Context compression supports GraphRAG runtime.", "GraphRAG runtime"),
        ("Context compression proves production ROI.", "production ROI"),
        ("Context compression allows model downgrade.", "model downgrade"),
        ("Context compression supports model downgrade.", "model downgrade"),
    ),
)
def test_context_compression_contract_validator_rejects_forbidden_claims(
    claim: str,
    expected: str,
) -> None:
    errors = validate_semantic_cache_context_compression_contract(_contract_text() + f"\n{claim}\n")

    assert any(expected in error for error in errors)


def test_context_compression_schema_validator_rejects_mutated_runtime_flags() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    properties["provider_calls_allowed"]["const"] = True

    errors = validate_semantic_cache_context_compression_schema(json.dumps(schema, indent=2) + "\n")

    assert errors == ["context compression schema provider_calls_allowed must be const false"]


def test_context_compression_schema_validator_rejects_missing_root_type() -> None:
    schema = _schema()
    schema.pop("type")

    errors = validate_semantic_cache_context_compression_schema(json.dumps(schema, indent=2) + "\n")

    assert errors == ["context compression schema root type must be object"]


def test_context_compression_schema_validator_rejects_missing_required_field() -> None:
    schema = _schema()
    required = schema["required"]
    assert isinstance(required, list)
    required.remove("provider_calls_allowed")

    errors = validate_semantic_cache_context_compression_schema(json.dumps(schema, indent=2) + "\n")

    assert errors == ["context compression schema missing required field: provider_calls_allowed"]


def test_context_compression_schema_validator_rejects_missing_node_type_enum() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    allowed_node_types = properties["allowed_node_types"]["items"]["enum"]
    allowed_node_types.remove("agent_rule")

    errors = validate_semantic_cache_context_compression_schema(json.dumps(schema, indent=2) + "\n")

    assert errors == ["context compression schema missing allowed node type: agent_rule"]


def test_context_compression_schema_validator_rejects_missing_estimate_field_enum() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    estimate_fields = properties["context_compression_estimate_fields"]["items"]["enum"]
    estimate_fields.remove("baseline_context_chars_estimate")

    errors = validate_semantic_cache_context_compression_schema(json.dumps(schema, indent=2) + "\n")

    assert errors == [
        "context compression schema missing estimate field: baseline_context_chars_estimate"
    ]


def test_context_compression_schema_validator_rejects_missing_blocked_payloads() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    blocked_payloads = properties["blocked_payloads"]["items"]["enum"]
    blocked_payloads.remove("raw_context_snippets")

    errors = validate_semantic_cache_context_compression_schema(json.dumps(schema, indent=2) + "\n")

    assert errors == ["context compression schema missing blocked payload: raw_context_snippets"]


def test_context_compression_contract_does_not_change_gate_markers() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")

    assert "<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->" in roadmap
    assert "<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->" in roadmap
    assert "<!-- SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: false -->" in roadmap
    assert "<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: true -->" in roadmap
