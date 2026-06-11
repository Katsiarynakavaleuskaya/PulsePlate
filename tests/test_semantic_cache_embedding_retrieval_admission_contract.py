from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ci.check_semantic_cache_gate import (
    validate_semantic_cache_embedding_retrieval_admission_contract,
    validate_semantic_cache_embedding_retrieval_admission_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_EMBEDDING_RETRIEVAL_ADMISSION_TELEMETRY.md"
)
SCHEMA = CONTRACT.with_suffix(".schema.json")


def _contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def _schema() -> dict[str, object]:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_embedding_retrieval_admission_contract_stays_gate_closed() -> None:
    text = _contract_text().lower()

    assert "metadata-only" in text
    assert "gate status: closed" in text
    assert "runtime allowed: false" in text
    assert "implementation allowed: false" in text
    assert "admission allowed: false" in text
    assert "embedding allowed: false" in text
    assert "retrieval runtime allowed: false" in text
    assert "semantic similarity allowed: false" in text
    assert "vector search allowed: false" in text
    assert "provider calls allowed: false" in text
    assert "cache read allowed: false" in text
    assert "cache write allowed: false" in text
    assert "serving allowed: false" in text
    assert "selected embedding backend: none" in text
    assert "selected retrieval runtime: none" in text
    assert "telemetry phase: pr-o4" in text
    assert "dedicated gate-open pr required: true" in text


def test_embedding_retrieval_admission_schema_pins_closed_authority_flags() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)

    assert properties["gate_status"]["const"] == "closed"
    assert properties["runtime_allowed"]["const"] is False
    assert properties["implementation_allowed"]["const"] is False
    assert properties["admission_allowed"]["const"] is False
    assert properties["embedding_allowed"]["const"] is False
    assert properties["retrieval_runtime_allowed"]["const"] is False
    assert properties["semantic_similarity_allowed"]["const"] is False
    assert properties["vector_search_allowed"]["const"] is False
    assert properties["provider_calls_allowed"]["const"] is False
    assert properties["provider_wiring_allowed"]["const"] is False
    assert properties["cache_read_allowed"]["const"] is False
    assert properties["cache_write_allowed"]["const"] is False
    assert properties["serving_allowed"]["const"] is False
    assert properties["model_downgrade_allowed"]["const"] is False
    assert properties["pricing_truth_allowed"]["const"] is False
    assert properties["telemetry_phase"]["const"] == "PR-O4"
    assert properties["authority_boundary"]["const"] == "metadata_only_non_serving"
    assert properties["asset_type"]["const"] == "embedding_retrieval_admission_telemetry"
    assert properties["selected_embedding_backend"]["const"] == "none"
    assert properties["selected_retrieval_runtime"]["const"] == "none"
    assert "admission_deferred" in properties["required_reason_codes"]["items"]["enum"]
    assert "embedding_vectors" in properties["blocked_payloads"]["items"]["enum"]
    assert "vector_search" in properties["blocked_backends"]["items"]["enum"]


def test_embedding_retrieval_admission_validators_pass_current_contract_and_schema() -> None:
    assert validate_semantic_cache_embedding_retrieval_admission_contract(_contract_text()) == []
    assert (
        validate_semantic_cache_embedding_retrieval_admission_schema(
            SCHEMA.read_text(encoding="utf-8")
        )
        == []
    )


@pytest.mark.parametrize(
    "claim,expected",
    (
        ("Embedding/retrieval admission enables embeddings.", "embeddings"),
        ("Embedding/retrieval admission uses semantic similarity.", "semantic similarity"),
        ("Embedding/retrieval admission uses vector search.", "vector search"),
        ("Embedding/retrieval admission runs retrieval runtime.", "retrieval runtime"),
        ("Embedding/retrieval admission performs provider calls.", "provider calls"),
        ("Embedding/retrieval admission admits runtime.", "runtime admission"),
        ("Embedding/retrieval admission selects backend.", "backend selection"),
        ("Embedding/retrieval admission enables cache serving.", "cache serving"),
        ("Embedding/retrieval admission enables cache reads.", "cache read"),
        ("Embedding/retrieval admission enables cache writes.", "cache write"),
        ("Embedding/retrieval admission wires Ollama.", "provider wiring"),
        ("Embedding/retrieval admission stores raw prompts.", "raw prompt"),
        ("Embedding/retrieval admission stores normalized queries.", "normalized query"),
        ("Embedding/retrieval admission proves live savings.", "live savings"),
        ("Embedding/retrieval admission proves retrieval quality.", "retrieval quality"),
        ("Embedding/retrieval admission allows model downgrade.", "model downgrade"),
        ("PR-O4 uses vector search.", "vector search"),
        ("This contract performs provider calls.", "provider calls"),
        ("The telemetry stores raw prompts.", "raw prompt"),
        ("This PR enables retrieval runtime.", "retrieval runtime"),
        ("This contract proves live savings.", "live savings"),
    ),
)
def test_embedding_retrieval_contract_validator_rejects_forbidden_claims(
    claim: str,
    expected: str,
) -> None:
    errors = validate_semantic_cache_embedding_retrieval_admission_contract(
        _contract_text() + f"\n{claim}\n"
    )

    assert any(expected in error for error in errors)


def test_embedding_retrieval_schema_validator_rejects_mutated_runtime_flags() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    properties["embedding_allowed"]["const"] = True

    errors = validate_semantic_cache_embedding_retrieval_admission_schema(
        json.dumps(schema, indent=2) + "\n"
    )

    assert errors == ["embedding/retrieval admission schema embedding_allowed must be const false"]


def test_embedding_retrieval_schema_validator_rejects_missing_reason_code() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    reason_codes = properties["required_reason_codes"]["items"]["enum"]
    reason_codes.remove("future_gate_required")

    errors = validate_semantic_cache_embedding_retrieval_admission_schema(
        json.dumps(schema, indent=2) + "\n"
    )

    assert errors == [
        "embedding/retrieval admission schema missing reason code: future_gate_required"
    ]


def test_embedding_retrieval_schema_validator_rejects_missing_backend_block() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    backends = properties["blocked_backends"]["items"]["enum"]
    backends.remove("vector_search")

    errors = validate_semantic_cache_embedding_retrieval_admission_schema(
        json.dumps(schema, indent=2) + "\n"
    )

    assert errors == ["embedding/retrieval admission schema missing blocked backend: vector_search"]
