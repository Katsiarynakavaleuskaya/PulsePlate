from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "data/evals/pulseplate_selective_graph_eval_schema.json"
FIXTURE_PATH = REPO_ROOT / "data/evals/pulseplate_selective_graph_eval_sample.jsonl"
CONTRACT_DOC_PATH = REPO_ROOT / "docs/evals/PULSEPLATE_SELECTIVE_GRAPH_EVAL_CONTRACT.md"

REQUIRED_TOP_LEVEL_FIELDS = {
    "id",
    "surface",
    "question",
    "reference_answer",
    "graph_context",
    "expected_claims",
    "reasoning_expectation",
}
ALLOWED_SURFACES = {
    "corpus_level_nutrition_summarization",
    "multi_hop_contraindication_reasoning",
    "plan_explainability",
}
ALLOWED_NODE_TYPES = {
    "foods",
    "nutrients",
    "conditions",
    "restrictions",
    "meal_templates",
    "guideline_concepts",
}
ALLOWED_EDGE_RELATIONS = {
    "contains",
    "rich_in",
    "contraindicated_for",
    "recommended_for",
    "substitutable_with",
}
ALLOWED_REASONING_KINDS = {
    "global_summary",
    "multi_hop",
    "comparative_explanation",
}
EXPECTED_KIND_BY_SURFACE = {
    "corpus_level_nutrition_summarization": "global_summary",
    "multi_hop_contraindication_reasoning": "multi_hop",
    "plan_explainability": "comparative_explanation",
}
FORBIDDEN_RUNTIME_OR_GATE_FIELDS = {
    "thresholds",
    "threshold_results",
    "gate_checks",
    "release_decision",
    "provider_output",
    "runtime_trace",
    "graph_execution_trace",
    "semantic_cache",
    "semantic_cache_key",
    "semantic_cache_enabled",
    "cache_hit",
    "score",
    "scores",
}
FORBIDDEN_RUNTIME_OR_GATE_VALUES = {"PASS", "NO-GO"}


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_fixture_rows() -> list[dict[str, Any]]:
    rows = []
    for line in FIXTURE_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _find_keys(payload: Any) -> set[str]:
    if isinstance(payload, dict):
        keys = set(payload)
        for value in payload.values():
            keys.update(_find_keys(value))
        return keys
    if isinstance(payload, list):
        keys: set[str] = set()
        for item in payload:
            keys.update(_find_keys(item))
        return keys
    return set()


def _find_string_values(payload: Any) -> set[str]:
    if isinstance(payload, dict):
        values: set[str] = set()
        for value in payload.values():
            values.update(_find_string_values(value))
        return values
    if isinstance(payload, list):
        values = set()
        for item in payload:
            values.update(_find_string_values(item))
        return values
    if isinstance(payload, str):
        return {payload}
    return set()


def _bullets_after_marker(text: str, marker: str) -> list[str]:
    lines = text.splitlines()
    assert marker in lines
    marker_index = lines.index(marker)
    bullets: list[str] = []
    for line in lines[marker_index + 1 :]:
        if line.startswith("## "):
            break
        if line.startswith("- "):
            bullets.append(line)
    return bullets


def test_schema_contract_enums_are_bounded_to_selective_graph_eval() -> None:
    schema = _load_schema()

    assert set(EXPECTED_KIND_BY_SURFACE) == ALLOWED_SURFACES
    assert set(schema["required"]) == REQUIRED_TOP_LEVEL_FIELDS
    assert schema["additionalProperties"] is False

    properties = schema["properties"]
    assert set(properties) == REQUIRED_TOP_LEVEL_FIELDS
    assert set(properties["surface"]["enum"]) == ALLOWED_SURFACES

    graph_context = properties["graph_context"]
    assert graph_context["additionalProperties"] is False
    assert set(graph_context["required"]) == {"nodes", "edges"}
    assert set(graph_context["properties"]) == {"nodes", "edges"}

    node_schema = graph_context["properties"]["nodes"]["items"]
    assert node_schema["additionalProperties"] is False
    assert set(node_schema["required"]) == {"id", "type", "label"}
    assert set(node_schema["properties"]) == {"id", "type", "label"}
    assert set(node_schema["properties"]["type"]["enum"]) == ALLOWED_NODE_TYPES

    edge_schema = graph_context["properties"]["edges"]["items"]
    assert edge_schema["additionalProperties"] is False
    assert set(edge_schema["required"]) == {"source", "relation", "target"}
    assert set(edge_schema["properties"]) == {"source", "relation", "target"}
    assert set(edge_schema["properties"]["relation"]["enum"]) == ALLOWED_EDGE_RELATIONS

    reasoning_schema = properties["reasoning_expectation"]
    assert reasoning_schema["additionalProperties"] is False
    assert set(reasoning_schema["required"]) == {"kind"}
    assert set(reasoning_schema["properties"]) == {"kind"}
    assert set(reasoning_schema["properties"]["kind"]["enum"]) == ALLOWED_REASONING_KINDS


def test_fixture_contains_exactly_one_record_per_allowed_surface() -> None:
    records = _load_fixture_rows()

    assert len(records) == 3
    assert Counter(record["surface"] for record in records) == Counter(
        {surface: 1 for surface in ALLOWED_SURFACES}
    )
    assert len({record["id"] for record in records}) == len(records)


def test_fixture_rows_match_offline_graph_eval_contract() -> None:
    for record in _load_fixture_rows():
        assert set(record) == REQUIRED_TOP_LEVEL_FIELDS
        assert record["surface"] in ALLOWED_SURFACES

        for field_name in ("id", "question", "reference_answer"):
            assert isinstance(record[field_name], str)
            assert record[field_name].strip()

        expected_claims = record["expected_claims"]
        assert isinstance(expected_claims, list)
        assert expected_claims
        assert all(isinstance(claim, str) and claim.strip() for claim in expected_claims)

        graph_context = record["graph_context"]
        assert set(graph_context) == {"nodes", "edges"}

        nodes = graph_context["nodes"]
        edges = graph_context["edges"]
        assert isinstance(nodes, list)
        assert isinstance(edges, list)
        assert nodes
        assert edges

        node_ids = {node["id"] for node in nodes}
        assert len(node_ids) == len(nodes)

        for node in nodes:
            assert set(node) == {"id", "type", "label"}
            assert isinstance(node["id"], str)
            assert node["id"].strip()
            assert node["type"] in ALLOWED_NODE_TYPES
            assert isinstance(node["label"], str)
            assert node["label"].strip()

        for edge in edges:
            assert set(edge) == {"source", "relation", "target"}
            assert edge["source"] in node_ids
            assert edge["target"] in node_ids
            assert edge["relation"] in ALLOWED_EDGE_RELATIONS

        reasoning_expectation = record["reasoning_expectation"]
        assert set(reasoning_expectation) == {"kind"}
        assert reasoning_expectation["kind"] == EXPECTED_KIND_BY_SURFACE[record["surface"]]


def test_fixture_rows_do_not_contain_runtime_gate_or_cache_fields() -> None:
    for record in _load_fixture_rows():
        leaked_keys = _find_keys(record) & FORBIDDEN_RUNTIME_OR_GATE_FIELDS
        leaked_values = _find_string_values(record) & FORBIDDEN_RUNTIME_OR_GATE_VALUES
        assert leaked_keys == set()
        assert leaked_values == set()


def test_contract_doc_keeps_graph_eval_offline_and_subordinate() -> None:
    contract_doc = CONTRACT_DOC_PATH.read_text(encoding="utf-8")

    assert set(_bullets_after_marker(contract_doc, "It does not introduce:")) == {
        "- runtime GraphRAG rollout",
        "- semantic cache widening",
        "- provider behavior changes",
        "- a graph runner",
        "- graph-specific CI thresholds",
        "- a second canonical evaluation rail",
    }
    assert (
        "- [`PULSEPLATE_RAG_RELEASE_GATES.md`](./PULSEPLATE_RAG_RELEASE_GATES.md)" in contract_doc
    )
    assert "owns threshold vocabulary, gate checks" in contract_doc
    assert "must not create a second evaluation source of truth" in contract_doc
