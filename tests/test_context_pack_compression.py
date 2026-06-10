from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import cast

import pytest

from scripts.orchestration.context_pack_compression import (
    CONTEXT_COMPRESSION_AUTHORITY_BOUNDARY,
    EDGE_REQUIRES,
    CompressedContextPack,
    ContextCompressionEstimate,
    ContextGraphEdge,
    ContextGraphNode,
    JsonValue,
    build_context_pack_compression,
    to_stable_mapping,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE = REPO_ROOT / "scripts" / "orchestration" / "context_pack_compression.py"


def _pack() -> CompressedContextPack:
    return build_context_pack_compression(
        candidate_paths=(
            "scripts/orchestration/task_bootstrap.py",
            "tests/test_task_bootstrap.py",
        ),
        required_context=(
            "RUNBOOK_AGENT.md",
            "AGENTS.md",
            "docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md",
            "AGENTS.md",
        ),
        pr_phase="pre_open",
        domain="ml",
        cluster="ml",
        primary_agent="architecture-specialist",
        reviewer="rag-systems-agent",
        secondary_agents=("security-auditor", "qa-engineer-agent"),
        requested_agents=("agent-coordinator", "security-auditor"),
        orchestration_fanout_multiplier=4,
    )


def test_context_pack_compression_is_deterministic_metadata_only() -> None:
    first = _pack()
    second = build_context_pack_compression(
        candidate_paths=(
            "tests/test_task_bootstrap.py",
            "scripts/orchestration/task_bootstrap.py",
        ),
        required_context=(
            "AGENTS.md",
            "docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md",
            "RUNBOOK_AGENT.md",
            "AGENTS.md",
        ),
        pr_phase="pre_open",
        domain="ml",
        cluster="ml",
        primary_agent="architecture-specialist",
        reviewer="rag-systems-agent",
        secondary_agents=("qa-engineer-agent", "security-auditor"),
        requested_agents=("security-auditor", "agent-coordinator"),
        orchestration_fanout_multiplier=4,
    )

    assert first.context_pack_id == second.context_pack_id
    assert first.authority_boundary == CONTEXT_COMPRESSION_AUTHORITY_BOUNDARY
    assert first.required_context == (
        "AGENTS.md",
        "RUNBOOK_AGENT.md",
        "docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md",
    )
    serialized = json.dumps(dict(to_stable_mapping(first)), sort_keys=True)
    assert "private prompt text" not in serialized
    assert "raw_prompt" not in serialized
    assert "raw_response" not in serialized
    assert "/Users/" not in serialized
    assert "tokens_saved_estimate" in serialized
    assert first.estimate.tokens_saved_estimate >= 0
    assert first.estimate.fanout_tokens_saved_estimate == (first.estimate.tokens_saved_estimate * 4)


def test_context_pack_compression_preserves_required_context_and_tracks_duplicates() -> None:
    pack = _pack()
    stable = dict(to_stable_mapping(pack))

    assert stable["required_context"] == [
        "AGENTS.md",
        "RUNBOOK_AGENT.md",
        "docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md",
    ]
    assert [ref["path"] for ref in stable["selected_context_refs"]] == [
        "AGENTS.md",
        "RUNBOOK_AGENT.md",
        "docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md",
    ]
    agents_node = next(node for node in pack.graph_nodes if node.path == "AGENTS.md")
    assert stable["omitted_duplicate_refs"] == [
        {
            "node_id": agents_node.node_id,
            "path": "AGENTS.md",
            "path_fingerprint": agents_node.path_fingerprint,
            "reason_code": "duplicate_context_reference",
            "status": "duplicate_reference",
            "token_estimate": agents_node.token_estimate,
        }
    ]


def test_context_pack_compression_allows_safe_prompt_engineering_role_slug() -> None:
    pack = build_context_pack_compression(
        candidate_paths=("scripts/orchestration/task_bootstrap.py",),
        required_context=("AGENTS.md",),
        pr_phase="pre_open",
        domain="ml",
        cluster="ml",
        primary_agent="architecture-specialist",
        reviewer="rag-systems-agent",
        secondary_agents=("prompt-engineering-eval-agent",),
        requested_agents=("prompt-engineering-eval-agent",),
    )

    stable = dict(to_stable_mapping(pack))
    assert stable["authority_boundary"] == CONTEXT_COMPRESSION_AUTHORITY_BOUNDARY
    assert stable["metadata"]["secondary_agent_count"] == 1
    assert stable["metadata"]["requested_agent_count"] == 1
    assert stable["context_pack_id"].startswith("ctx-pack:")


def test_context_pack_compression_estimates_without_reading_raw_file_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("context compression must not read raw file text")

    def fail_bytes(*_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("context compression must not read raw file bytes")

    monkeypatch.setattr(Path, "read_text", fail_read)
    monkeypatch.setattr(Path, "read_bytes", fail_bytes)

    pack = build_context_pack_compression(
        candidate_paths=("scripts/orchestration/task_bootstrap.py",),
        required_context=("AGENTS.md",),
        pr_phase="pre_open",
        domain="ml",
        cluster="ml",
        primary_agent="architecture-specialist",
        reviewer="rag-systems-agent",
    )

    assert pack.estimate.baseline_context_chars_estimate > 0
    assert pack.estimate.baseline_context_tokens_estimate > 0
    assert pack.estimate.candidate_context_chars_estimate > sum(
        len(str(value))
        for ref in dict(to_stable_mapping(pack))["selected_context_refs"]
        for value in cast(dict[str, JsonValue], ref).values()
    )


def test_context_compression_estimate_rejects_inconsistent_fanout_total() -> None:
    with pytest.raises(ValueError, match="fanout_tokens_saved_estimate"):
        ContextCompressionEstimate(
            estimate_id="ctx-estimate:" + "1" * 24,
            baseline_context_chars_estimate=100,
            candidate_context_chars_estimate=40,
            baseline_context_tokens_estimate=25,
            candidate_context_tokens_estimate=10,
            tokens_saved_estimate=15,
            orchestration_fanout_multiplier=3,
            fanout_tokens_saved_estimate=44,
            token_estimate_version="heuristic-chars-div4-v1",
            reason_codes=("estimate_only",),
        )


def test_context_pack_compression_uses_bounded_non_authority_graph_enums() -> None:
    pack = _pack()
    stable = dict(to_stable_mapping(pack))

    assert {node["node_type"] for node in stable["graph_nodes"]} <= {
        "agent_rule",
        "contract",
        "test",
        "changed_file",
    }
    assert {edge["edge_type"] for edge in stable["graph_edges"]} <= {
        "requires",
        "validates",
        "constrains",
        "documents",
        "reviews",
    }
    assert len({node["node_id"] for node in stable["graph_nodes"]}) == len(stable["graph_nodes"])
    assert len({edge["edge_id"] for edge in stable["graph_edges"]}) == len(stable["graph_edges"])


@pytest.mark.parametrize(
    "bad_path",
    (
        "/Users/name/project/secret.md",
        "~/secret.md",
        "file:///tmp/x",
        "C:\\Users\\x",
        "../outside.md",
        "docs/../.env",
        ".env",
    ),
)
def test_context_pack_compression_rejects_unsafe_paths_without_echoing(
    bad_path: str,
) -> None:
    with pytest.raises(ValueError) as excinfo:
        build_context_pack_compression(
            candidate_paths=(bad_path,),
            required_context=("AGENTS.md",),
            pr_phase="pre_open",
            domain="ml",
            cluster="ml",
            primary_agent="architecture-specialist",
            reviewer="rag-systems-agent",
        )

    assert bad_path not in str(excinfo.value)


@pytest.mark.parametrize(
    "metadata",
    (
        {"raw_prompt": "unsafe"},
        {"nested": {"raw_query": "unsafe"}},
        {"items": ["Authorization: Bearer secret"]},
        {"provider_payload": "unsafe"},
        {"path": "/Users/name/private.txt"},
        {"github": "ghs_header.payload.signature"},
        {"slack": "xoxb-secret"},
        {"contact": "user@example.com"},
        {"phone": "+1 555 123 4567"},
        {"health": "HealthKit diagnosis"},
        {"model": "downgraded_model"},
        {"claim": "production_cost_saved"},
    ),
)
def test_context_graph_metadata_rejects_unsafe_values(
    metadata: dict[str, JsonValue],
) -> None:
    with pytest.raises(ValueError, match="unsafe metadata"):
        ContextGraphNode(
            node_id="ctx-node:" + "1" * 24,
            node_type="changed_file",
            path="AGENTS.md",
            path_fingerprint="sha256:" + "2" * 64,
            token_estimate=1,
            required=False,
            metadata=metadata,
        )


def test_context_graph_edge_rejects_authority_edge_types() -> None:
    with pytest.raises(ValueError, match="edge_type"):
        ContextGraphEdge(
            edge_id="ctx-edge:" + "1" * 24,
            source="ctx-node:" + "2" * 24,
            target="ctx-node:" + "3" * 24,
            edge_type="merge_ready",
            metadata={},
        )


def test_context_graph_constructor_rejects_bool_numeric_fields() -> None:
    with pytest.raises(ValueError, match="integer"):
        ContextGraphNode(
            node_id="ctx-node:" + "1" * 24,
            node_type="changed_file",
            path="AGENTS.md",
            path_fingerprint="sha256:" + "2" * 64,
            token_estimate=cast(int, True),
            required=False,
            metadata={},
        )


def test_context_pack_compression_has_no_provider_or_runtime_imports() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_roots = {
        "app",
        "embedding",
        "graphrag",
        "gptcache",
        "httpx",
        "openai",
        "providers",
        "redis",
        "requests",
        "vector_rag",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any(
                alias.name.split(".", maxsplit=1)[0].lower() in forbidden_roots
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            assert node.module.split(".", maxsplit=1)[0].lower() not in forbidden_roots


def test_context_pack_compression_degrades_on_unbounded_graph_sizes() -> None:
    required = tuple(f"docs/orchestration/context_{index}.md" for index in range(201))

    pack = build_context_pack_compression(
        candidate_paths=(),
        required_context=required,
        pr_phase="pre_open",
        domain="ml",
        cluster="ml",
        primary_agent="architecture-specialist",
        reviewer="rag-systems-agent",
    )

    stable = dict(to_stable_mapping(pack))
    assert len(stable["required_context"]) == 201
    assert len(stable["selected_context_refs"]) == 201
    assert len(stable["graph_nodes"]) == 200
    assert stable["selected_context_refs"][-1]["node_id"] is None
    assert "graph_limit_truncated" in stable["reason_codes"]
    assert "compression_limit_exceeded" in stable["reason_codes"]


def test_context_pack_compression_preserves_dual_required_and_candidate_role() -> None:
    pack = build_context_pack_compression(
        candidate_paths=("AGENTS.md",),
        required_context=("AGENTS.md", "RUNBOOK_AGENT.md"),
        pr_phase="pre_open",
        domain="ml",
        cluster="ml",
        primary_agent="architecture-specialist",
        reviewer="rag-systems-agent",
    )

    agents_node = next(
        node for node in dict(to_stable_mapping(pack))["graph_nodes"] if node["path"] == "AGENTS.md"
    )

    assert agents_node["required"] is True
    assert agents_node["metadata"] == {
        "candidate": True,
        "status": "required_and_candidate",
    }


def test_context_pack_compression_degrades_on_unbounded_edge_sizes() -> None:
    candidates = tuple(f"scripts/orchestration/candidate_{index}.py" for index in range(126))
    required = tuple(f"docs/orchestration/context_{index}.md" for index in range(9))

    pack = build_context_pack_compression(
        candidate_paths=candidates,
        required_context=required,
        pr_phase="pre_open",
        domain="ml",
        cluster="ml",
        primary_agent="architecture-specialist",
        reviewer="rag-systems-agent",
    )

    stable = dict(to_stable_mapping(pack))
    assert len(stable["required_context"]) == 9
    assert len(stable["graph_edges"]) == 1000
    assert "compression_limit_exceeded" in stable["reason_codes"]


def test_context_pack_compression_serialization_is_json_ready() -> None:
    serialized = json.dumps(dict(to_stable_mapping(_pack())), sort_keys=True)

    assert '"authority_boundary": "metadata_only_non_serving"' in serialized
    assert '"provider_calls_allowed"' not in serialized
