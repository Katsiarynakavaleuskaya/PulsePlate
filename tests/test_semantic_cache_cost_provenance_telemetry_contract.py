from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_COST_PROVENANCE_TELEMETRY.md"
)
SCHEMA = CONTRACT.with_suffix(".schema.json")


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
