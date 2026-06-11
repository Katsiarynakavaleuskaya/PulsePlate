from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from scripts.orchestration.provider_model_tier_policy import (
    PROVIDER_MODEL_TIER_AUTHORITY_BOUNDARY,
    ProviderModelRoutingTelemetry,
    ProviderModelTierRecord,
    build_provider_model_routing_policy_snapshot,
    build_provider_model_routing_telemetry,
    to_stable_mapping,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE = REPO_ROOT / "scripts" / "orchestration" / "provider_model_tier_policy.py"


def test_policy_snapshot_is_deterministic_metadata_only() -> None:
    first = build_provider_model_routing_policy_snapshot()
    second = build_provider_model_routing_policy_snapshot(records=tuple(reversed(first.records)))

    assert first.policy_id == second.policy_id
    assert first.authority_boundary == PROVIDER_MODEL_TIER_AUTHORITY_BOUNDARY
    stable = dict(to_stable_mapping(first))
    assert stable["policy_version"] == "provider-model-tier-routing-o3-v1"
    assert stable["authority_boundary"] == "metadata_only_non_serving"
    assert {record["provider_label"] for record in stable["records"]} == {
        "gpt",
        "ollama",
        "perplexity_sonar",
        "perplexity_agent",
        "unknown_provider",
    }
    serialized = json.dumps(stable, sort_keys=True)
    assert "raw_prompt" not in serialized
    assert "provider_payload" not in serialized
    assert "/Users/" not in serialized


def test_routing_telemetry_preserves_frontier_review_and_selects_no_runtime_route() -> None:
    telemetry = build_provider_model_routing_telemetry(
        requested_agents=(
            "agent-coordinator",
            "rag-systems-agent",
            "prompt-engineering-eval-agent",
            "architecture-specialist",
            "security-auditor",
            "qa-engineer-agent",
        ),
        primary_agent="architecture-specialist",
        reviewer="rag-systems-agent",
        secondary_agents=("security-auditor", "qa-engineer-agent"),
        token_economy_estimate_ids=("token-economy:" + "a" * 24,),
    )

    stable = dict(to_stable_mapping(telemetry))
    assert stable["telemetry_phase"] == "PR-O3"
    assert stable["selected_route"] == "no_runtime_selection"
    assert "frontier_required" in stable["model_tier_labels"]
    assert "security-auditor" in stable["required_frontier_roles"]
    assert "qa-engineer-agent" in stable["required_frontier_roles"]
    assert "pulseplate-pr-review" in stable["required_frontier_roles"]
    assert set(stable["candidate_pre_synthesis_roles"]) == {
        "prompt-engineering-eval-agent",
    }
    assert "security-auditor" not in stable["candidate_pre_synthesis_roles"]
    assert "qa-engineer-agent" not in stable["candidate_pre_synthesis_roles"]
    assert "final-synthesis" not in stable["candidate_pre_synthesis_roles"]
    assert stable["token_economy_estimate_ids"] == ["token-economy:" + "a" * 24]
    for reason in (
        "gate_closed",
        "metadata_only",
        "provider_labels_only",
        "no_runtime_selection",
        "frontier_review_preserved",
        "no_provider_call",
        "no_cache_serving",
        "no_embeddings",
        "no_graphrag_runtime",
        "estimate_only",
    ):
        assert reason in stable["reason_codes"]


@pytest.mark.parametrize(
    "provider_label,model_tier_label",
    (
        ("openai_live", "frontier_required"),
        ("ollama", "cheap_final_review"),
    ),
)
def test_tier_record_rejects_unsupported_provider_or_tier(
    provider_label: str,
    model_tier_label: str,
) -> None:
    with pytest.raises(ValueError):
        ProviderModelTierRecord(
            record_id="provider-tier:" + "1" * 24,
            provider_label=provider_label,
            model_tier_label=model_tier_label,
            allowed_advisory_roles=(),
            blocked_runtime_roles=("security-auditor",),
            quality_floor="frontier_required",
            relative_cost_rank=1,
            metadata={},
        )


@pytest.mark.parametrize(
    "metadata",
    (
        {"raw_prompt": "unsafe"},
        {"payload": "provider_payload"},
        {"path": "/Users/name/private.txt"},
        {"auth_marker": "authorization"},
        {"pricing": "provider_price"},
        {"claim": "live_savings"},
        {"route": "runtime_route"},
        {"tier": "model_downgrade"},
    ),
)
def test_tier_record_rejects_unsafe_metadata(metadata: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="unsafe metadata"):
        ProviderModelTierRecord(
            record_id="provider-tier:" + "1" * 24,
            provider_label="ollama",
            model_tier_label="local_preprocess_advisory",
            allowed_advisory_roles=("prompt-engineering-eval-agent",),
            blocked_runtime_roles=("security-auditor",),
            quality_floor="advisory_only",
            relative_cost_rank=1,
            metadata=metadata,
        )


def test_routing_telemetry_rejects_runtime_selection() -> None:
    snapshot = build_provider_model_routing_policy_snapshot()

    with pytest.raises(ValueError, match="selected_route"):
        ProviderModelRoutingTelemetry(
            telemetry_id="provider-routing:" + "1" * 24,
            telemetry_phase="PR-O3",
            policy_snapshot_id=snapshot.policy_id,
            selected_route="ollama",
            required_frontier_roles=("security-auditor",),
            candidate_pre_synthesis_roles=(),
            blocked_runtime_roles=("security-auditor",),
            provider_labels=("ollama",),
            model_tier_labels=("frontier_required",),
            token_economy_estimate_ids=(),
            reason_codes=("no_runtime_selection",),
            metadata={},
        )


def test_routing_telemetry_rejects_frontier_advisory_overlap() -> None:
    snapshot = build_provider_model_routing_policy_snapshot()

    with pytest.raises(ValueError, match="must not overlap frontier roles"):
        ProviderModelRoutingTelemetry(
            telemetry_id="provider-routing:" + "1" * 24,
            telemetry_phase="PR-O3",
            policy_snapshot_id=snapshot.policy_id,
            selected_route="no_runtime_selection",
            required_frontier_roles=("security-auditor",),
            candidate_pre_synthesis_roles=("security-auditor",),
            blocked_runtime_roles=("security-auditor",),
            provider_labels=("ollama",),
            model_tier_labels=("frontier_required",),
            token_economy_estimate_ids=(),
            reason_codes=("no_runtime_selection",),
            metadata={},
        )


@pytest.mark.parametrize(
    "metadata",
    (
        {"selected_route": "ollama"},
        {"provider_selection": "perplexity_sonar"},
        {"runtime_model_selection": "standard_advisory"},
        {"route_decision": "provider"},
    ),
)
def test_routing_telemetry_rejects_metadata_that_implies_runtime_selection(
    metadata: dict[str, str],
) -> None:
    snapshot = build_provider_model_routing_policy_snapshot()

    with pytest.raises(ValueError, match="unsafe metadata"):
        ProviderModelRoutingTelemetry(
            telemetry_id="provider-routing:" + "1" * 24,
            telemetry_phase="PR-O3",
            policy_snapshot_id=snapshot.policy_id,
            selected_route="no_runtime_selection",
            required_frontier_roles=("security-auditor",),
            candidate_pre_synthesis_roles=(),
            blocked_runtime_roles=("security-auditor",),
            provider_labels=("ollama",),
            model_tier_labels=("frontier_required",),
            token_economy_estimate_ids=(),
            reason_codes=("no_runtime_selection",),
            metadata=metadata,
        )


def test_provider_model_tier_policy_has_no_runtime_provider_cache_or_network_imports() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    forbidden_roots = {
        "app",
        "fastapi",
        "httpx",
        "openai",
        "providers",
        "redis",
        "requests",
        "sqlalchemy",
    }
    forbidden_modules = {"core.ai.insight_runtime", "core.insight.llm_provider_loader"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any(
                alias.name.split(".", maxsplit=1)[0].lower() in forbidden_roots
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            assert node.module not in forbidden_modules
            assert node.module.split(".", maxsplit=1)[0].lower() not in forbidden_roots
