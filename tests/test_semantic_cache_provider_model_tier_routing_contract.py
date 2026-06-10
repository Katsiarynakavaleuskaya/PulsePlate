from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ci.check_semantic_cache_gate import (
    validate_semantic_cache_provider_model_tier_routing_contract,
    validate_semantic_cache_provider_model_tier_routing_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_PROVIDER_MODEL_TIER_ROUTING_TELEMETRY.md"
)
SCHEMA = CONTRACT.with_suffix(".schema.json")


def _contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def _schema() -> dict[str, object]:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_provider_model_tier_contract_stays_gate_closed_and_non_serving() -> None:
    text = _contract_text().lower()

    assert "metadata-only" in text
    assert "gate status: closed" in text
    assert "runtime allowed: false" in text
    assert "implementation allowed: false" in text
    assert "runtime routing allowed: false" in text
    assert "provider calls allowed: false" in text
    assert "provider wiring allowed: false" in text
    assert "model downgrade allowed: false" in text
    assert "pricing truth allowed: false" in text
    assert "selected route: no_runtime_selection" in text
    assert "telemetry phase: pr-o3" in text
    assert "provider labels are labels only" in text
    assert "no provider-specific prices" in text
    assert "must not downgrade" in text


def test_provider_model_tier_schema_pins_closed_authority_flags_and_labels() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)

    assert properties["gate_status"]["const"] == "closed"
    assert properties["runtime_allowed"]["const"] is False
    assert properties["implementation_allowed"]["const"] is False
    assert properties["runtime_routing_allowed"]["const"] is False
    assert properties["runtime_handoff_allowed"]["const"] is False
    assert properties["provider_calls_allowed"]["const"] is False
    assert properties["provider_wiring_allowed"]["const"] is False
    assert properties["model_downgrade_allowed"]["const"] is False
    assert properties["pricing_truth_allowed"]["const"] is False
    assert properties["telemetry_phase"]["const"] == "PR-O3"
    assert properties["selected_route"]["const"] == "no_runtime_selection"
    assert properties["authority_boundary"]["const"] == "metadata_only_non_serving"
    assert properties["asset_type"]["const"] == "provider_model_tier_routing_telemetry"

    assert set(properties["allowed_provider_labels"]["items"]["enum"]) == {
        "gpt",
        "ollama",
        "perplexity_sonar",
        "perplexity_agent",
        "unknown_provider",
    }
    assert "frontier_required" in properties["allowed_model_tier_labels"]["items"]["enum"]
    assert "no_runtime_selection" in properties["required_reason_codes"]["items"]["enum"]


def test_provider_model_tier_validators_pass_current_contract_and_schema() -> None:
    assert validate_semantic_cache_provider_model_tier_routing_contract(_contract_text()) == []
    assert (
        validate_semantic_cache_provider_model_tier_routing_schema(
            SCHEMA.read_text(encoding="utf-8")
        )
        == []
    )


@pytest.mark.parametrize(
    "claim,expected",
    (
        ("Provider/model-tier routing enables runtime routing.", "runtime routing"),
        ("Provider/model-tier routing selects GPT.", "runtime selection"),
        ("Provider/model-tier routing chooses Perplexity Sonar.", "runtime selection"),
        ("Provider/model-tier routing routes to Ollama.", "runtime selection"),
        ("Provider/model-tier routing performs provider calls.", "provider calls"),
        ("Provider/model-tier routing wires Ollama.", "Ollama"),
        ("Provider/model-tier routing wires Perplexity.", "Perplexity"),
        ("Provider/model-tier routing wires Sonar.", "Sonar"),
        ("Provider/model-tier routing allows model downgrade.", "model downgrade"),
        ("Cheaper tiers handle final review.", "cheap final review"),
        ("Provider/model-tier routing proves live savings.", "live savings"),
        ("Provider/model-tier routing creates billing truth.", "billing truth"),
        (
            "Provider/model-tier routing encodes provider-specific prices.",
            "provider-specific pricing",
        ),
        ("Provider/model-tier routing enables cache serving.", "cache serving"),
        ("Provider/model-tier routing enables embeddings.", "embeddings"),
        ("Provider/model-tier routing enables GraphRAG runtime.", "GraphRAG runtime"),
    ),
)
def test_provider_model_tier_contract_validator_rejects_forbidden_claims(
    claim: str,
    expected: str,
) -> None:
    errors = validate_semantic_cache_provider_model_tier_routing_contract(
        _contract_text() + f"\n{claim}\n"
    )

    assert any(expected in error for error in errors)


def test_provider_model_tier_schema_validator_rejects_mutated_runtime_flags() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    properties["provider_calls_allowed"]["const"] = True

    errors = validate_semantic_cache_provider_model_tier_routing_schema(
        json.dumps(schema, indent=2) + "\n"
    )

    assert errors == [
        "provider/model-tier routing schema provider_calls_allowed must be const false"
    ]


def test_provider_model_tier_schema_validator_rejects_missing_provider_label() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    provider_labels = properties["allowed_provider_labels"]["items"]["enum"]
    provider_labels.remove("perplexity_sonar")

    errors = validate_semantic_cache_provider_model_tier_routing_schema(
        json.dumps(schema, indent=2) + "\n"
    )

    assert errors == ["provider/model-tier routing schema missing provider label: perplexity_sonar"]


def test_provider_model_tier_schema_validator_rejects_missing_reason_code() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    reason_codes = properties["required_reason_codes"]["items"]["enum"]
    reason_codes.remove("frontier_review_preserved")

    errors = validate_semantic_cache_provider_model_tier_routing_schema(
        json.dumps(schema, indent=2) + "\n"
    )

    assert errors == [
        "provider/model-tier routing schema missing reason code: frontier_review_preserved"
    ]
