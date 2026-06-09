from __future__ import annotations

import json
from collections.abc import MutableMapping
from pathlib import Path
from typing import cast

import pytest

from core.ai.prompt_modules import (
    JsonValue,
    PromptModuleRecord,
    PromptModuleRegistry,
    build_prompt_module_record,
    build_prompt_module_registry,
    prompt_module_fingerprints,
    to_stable_mapping,
)
from core.evidence.fingerprints import fingerprint_provenance_envelope

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_COST_PROVENANCE_TELEMETRY.md"
)
SCHEMA = CONTRACT.with_suffix(".schema.json")
TEXT_FINGERPRINT = "sha256:" + "1" * 64
REQ_FINGERPRINT = "sha256:" + "2" * 64
CTX_FINGERPRINT = "sha256:" + "3" * 64
SOURCE_FINGERPRINT = "sha256:" + "4" * 64


def _prompt_record(module_id: str = "system-prompt") -> PromptModuleRecord:
    return build_prompt_module_record(
        module_id=module_id,
        module_version="prompt-module-v1",
        surface="orchestration",
        text_fingerprint=TEXT_FINGERPRINT,
        char_count=120,
        token_estimate=30,
        token_estimate_version="heuristic-tokens-v1",
        policy_version="semantic-cache-cost-o1-v1",
        metadata={"nested": {"safe": ["label"]}, "profile_ref": "profile://safe-label"},
    )


def _contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def test_cost_provenance_contract_stays_gate_closed_and_non_serving() -> None:
    text = _contract_text().lower()

    assert "metadata-only" in text
    assert "does not open the" in text
    assert "gate status: closed" in text
    assert "runtime allowed: false" in text
    assert "implementation allowed: false" in text
    assert "cache read allowed: false" in text
    assert "cache write allowed: false" in text
    assert "serving allowed: false" in text
    assert "provider calls allowed: false" in text
    assert "does not provide cache hit rate" in text


def test_cost_provenance_contract_blocks_runtime_and_raw_payloads() -> None:
    text = _contract_text().lower()

    for phrase in (
        "raw prompts",
        "raw queries",
        "normalized queries",
        "raw model responses",
        "provider payloads",
        "redis",
        "gptcache",
        "embeddings",
        "semantic similarity",
        "vector search",
        "graphrag runtime output",
        "production cost or roi claims",
    ):
        assert phrase in text


def test_cost_provenance_schema_pins_closed_authority_flags_and_fields() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert schema["properties"]["gate_status"]["const"] == "closed"
    assert schema["properties"]["runtime_allowed"]["const"] is False
    assert schema["properties"]["implementation_allowed"]["const"] is False
    assert schema["properties"]["cache_read_allowed"]["const"] is False
    assert schema["properties"]["cache_write_allowed"]["const"] is False
    assert schema["properties"]["serving_allowed"]["const"] is False
    assert schema["properties"]["provider_calls_allowed"]["const"] is False
    assert schema["properties"]["telemetry_phase"]["const"] == "PR-O1"
    assert (
        "tokens_saved_estimate"
        in schema["properties"]["token_economy_estimate_fields"]["items"]["enum"]
    )
    assert (
        "cost_saved_microunits"
        in schema["properties"]["token_economy_estimate_fields"]["items"]["enum"]
    )
    assert (
        "text_fingerprint" in schema["properties"]["prompt_module_record_fields"]["items"]["enum"]
    )


def test_prompt_module_contract_is_metadata_only_and_stable() -> None:
    record = _prompt_record()
    registry = build_prompt_module_registry(
        policy_version=" semantic-cache-cost-o1-v1 ",
        records=(_prompt_record("b-module"), record),
    )
    serialized_record = json.dumps(dict(to_stable_mapping(record)), sort_keys=True)
    serialized_registry = json.dumps(dict(to_stable_mapping(registry)), sort_keys=True)

    assert record.module_id == "system-prompt"
    assert record.module_version == "prompt-module-v1"
    assert registry.policy_version == "semantic-cache-cost-o1-v1"
    assert tuple(item.module_id for item in registry.records) == ("b-module", "system-prompt")
    assert prompt_module_fingerprints(registry.records) == (TEXT_FINGERPRINT,)
    assert "private prompt text" not in serialized_record
    assert "profile://safe-label" in serialized_record
    assert registry.registry_id in serialized_registry
    assert to_stable_mapping(record)["metadata"] == {
        "nested": {"safe": ["label"]},
        "profile_ref": "profile://safe-label",
    }


def test_prompt_module_metadata_is_deep_frozen_and_rejects_unsafe_values() -> None:
    record = _prompt_record()
    nested = cast(MutableMapping[str, JsonValue], record.metadata["nested"])
    safe_values = cast(list[JsonValue], nested["safe"])

    with pytest.raises(TypeError):
        nested["raw_prompt"] = "unsafe"
    with pytest.raises(AttributeError):
        safe_values.append("unsafe")

    unsafe_metadata: list[dict[str, JsonValue]] = [
        {"raw_prompt": "unsafe"},
        {"nested": {"answer": "unsafe"}},
        {"items": ["Bearer secret"]},
        {"path": "/Users/name/private.txt"},
        {"wrapped_path": "see(/Users/name/private.txt)"},
        {"github": "ghs_header.payload.signature"},
        {"slack": "xoxb-secret"},
        {"contact": "user@example.com"},
        {"phone": "+1 555 123 4567"},
        {"health": "HealthKit diagnosis"},
    ]
    for metadata in unsafe_metadata:
        with pytest.raises(ValueError):
            build_prompt_module_record(
                module_id="system-prompt",
                module_version="prompt-module-v1",
                surface="orchestration",
                text_fingerprint=TEXT_FINGERPRINT,
                char_count=120,
                token_estimate=30,
                token_estimate_version="heuristic-tokens-v1",
                policy_version="semantic-cache-cost-o1-v1",
                metadata=metadata,
            )


def test_prompt_module_registry_and_record_validation_fail_closed() -> None:
    with pytest.raises(ValueError, match="sha256 fingerprint"):
        build_prompt_module_record(
            module_id="system-prompt",
            module_version="prompt-module-v1",
            surface="orchestration",
            text_fingerprint="not-a-fingerprint",
            char_count=120,
            token_estimate=30,
            token_estimate_version="heuristic-tokens-v1",
            policy_version="semantic-cache-cost-o1-v1",
        )
    with pytest.raises(ValueError, match="non-negative"):
        build_prompt_module_record(
            module_id="system-prompt",
            module_version="prompt-module-v1",
            surface="orchestration",
            text_fingerprint=TEXT_FINGERPRINT,
            char_count=-1,
            token_estimate=30,
            token_estimate_version="heuristic-tokens-v1",
            policy_version="semantic-cache-cost-o1-v1",
        )
    with pytest.raises(ValueError, match="unsupported value"):
        build_prompt_module_record(
            module_id="system-prompt",
            module_version="prompt-module-v1",
            surface="orchestration",
            text_fingerprint=TEXT_FINGERPRINT,
            char_count=120,
            token_estimate=30,
            token_estimate_version="heuristic-tokens-v1",
            policy_version="semantic-cache-cost-o1-v1",
            metadata=cast(dict[str, JsonValue], {"bad": 1.2}),
        )
    with pytest.raises(ValueError, match="duplicate prompt module"):
        build_prompt_module_registry(
            policy_version="semantic-cache-cost-o1-v1",
            records=(_prompt_record("same-module"), _prompt_record("same-module")),
        )
    with pytest.raises(ValueError, match="non-empty"):
        build_prompt_module_registry(policy_version="semantic-cache-cost-o1-v1", records=())
    with pytest.raises(ValueError, match="PromptModuleRecord"):
        build_prompt_module_registry(
            policy_version="semantic-cache-cost-o1-v1",
            records=cast(tuple[PromptModuleRecord, ...], ("not-a-record",)),
        )
    with pytest.raises(ValueError, match="PromptModuleRecord"):
        PromptModuleRegistry(
            registry_id="pm-registry:bad",
            policy_version="semantic-cache-cost-o1-v1",
            records=cast(tuple[PromptModuleRecord, ...], ("not-a-record",)),
        )
    with pytest.raises(ValueError, match="metadata must be a mapping"):
        PromptModuleRecord(
            module_id="system-prompt",
            module_version="prompt-module-v1",
            surface="orchestration",
            text_fingerprint=TEXT_FINGERPRINT,
            char_count=120,
            token_estimate=30,
            token_estimate_version="heuristic-tokens-v1",
            policy_version="semantic-cache-cost-o1-v1",
            metadata=cast(dict[str, JsonValue], ["not-a-mapping"]),
        )
    integer_metadata_record = build_prompt_module_record(
        module_id="system-prompt",
        module_version="prompt-module-v1",
        surface="orchestration",
        text_fingerprint=TEXT_FINGERPRINT,
        char_count=120,
        token_estimate=30,
        token_estimate_version="heuristic-tokens-v1",
        policy_version="semantic-cache-cost-o1-v1",
        metadata={"count": 1, "items": ["safe-label"]},
    )
    assert integer_metadata_record.metadata["count"] == 1
    with pytest.raises(ValueError, match="non-empty"):
        build_prompt_module_record(
            module_id="",
            module_version="prompt-module-v1",
            surface="orchestration",
            text_fingerprint=TEXT_FINGERPRINT,
            char_count=120,
            token_estimate=30,
            token_estimate_version="heuristic-tokens-v1",
            policy_version="semantic-cache-cost-o1-v1",
        )
    with pytest.raises(ValueError, match="whitespace"):
        build_prompt_module_record(
            module_id="system prompt",
            module_version="prompt-module-v1",
            surface="orchestration",
            text_fingerprint=TEXT_FINGERPRINT,
            char_count=120,
            token_estimate=30,
            token_estimate_version="heuristic-tokens-v1",
            policy_version="semantic-cache-cost-o1-v1",
        )
    with pytest.raises(ValueError, match="unsupported stable mapping"):
        to_stable_mapping(object())


def test_provenance_envelope_contract_normalizes_and_rejects_unsafe_inputs() -> None:
    baseline = fingerprint_provenance_envelope(
        surface="orchestration",
        request_fingerprint=REQ_FINGERPRINT,
        context_fingerprint=CTX_FINGERPRINT,
        source_fingerprints=(SOURCE_FINGERPRINT,),
        policy_version="semantic-cache-cost-o1-v1",
        model_key="model:gpt-family",
        user_tier="internal",
        transparency_notice_id="notice:internal",
        prompt_module_fingerprints=(TEXT_FINGERPRINT,),
    )
    repeated = fingerprint_provenance_envelope(
        surface="orchestration",
        request_fingerprint=REQ_FINGERPRINT,
        context_fingerprint=CTX_FINGERPRINT,
        source_fingerprints=(SOURCE_FINGERPRINT, SOURCE_FINGERPRINT),
        policy_version="semantic-cache-cost-o1-v1",
        model_key="model:gpt-family",
        user_tier="internal",
        transparency_notice_id="notice:internal",
        prompt_module_fingerprints=(TEXT_FINGERPRINT, TEXT_FINGERPRINT),
    )

    assert baseline == repeated
    with pytest.raises(ValueError, match="fingerprint"):
        fingerprint_provenance_envelope(
            surface="orchestration",
            request_fingerprint="private prompt text",
            context_fingerprint=None,
            source_fingerprints=(SOURCE_FINGERPRINT,),
            policy_version="semantic-cache-cost-o1-v1",
            model_key="model:gpt-family",
            user_tier=None,
            transparency_notice_id="notice:internal",
        )
    with pytest.raises(ValueError, match="non-empty"):
        fingerprint_provenance_envelope(
            surface="",
            request_fingerprint=REQ_FINGERPRINT,
            context_fingerprint=None,
            source_fingerprints=(SOURCE_FINGERPRINT,),
            policy_version="semantic-cache-cost-o1-v1",
            model_key="model:gpt-family",
            user_tier=None,
            transparency_notice_id="notice:internal",
        )
    with pytest.raises(ValueError, match="whitespace"):
        fingerprint_provenance_envelope(
            surface="orchestration review",
            request_fingerprint=REQ_FINGERPRINT,
            context_fingerprint=None,
            source_fingerprints=(SOURCE_FINGERPRINT,),
            policy_version="semantic-cache-cost-o1-v1",
            model_key="model:gpt-family",
            user_tier=None,
            transparency_notice_id="notice:internal",
        )
