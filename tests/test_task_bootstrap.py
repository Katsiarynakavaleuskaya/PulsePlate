"""Tests for deterministic coordinator task bootstrap packets."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from core.judgment import (
    CLAIM_EVIDENCE_FIELDS,
    CLAIM_TYPES,
    EVIDENCE_MODES,
    JUDGMENT_FLOW,
    PROMOTION_LABELS,
    SUPPORT_STATUSES,
    UNCERTAINTY_FIELDS,
)
from scripts.orchestration.bootstrap_sync_policy import (
    matches_any_prefix,
    resolve_analysis_envelope_mode,
)
from scripts.orchestration.context_pack import repo_relative_paths
from scripts.orchestration.design_lane_contract import canonicalize_design_blockers
from scripts.orchestration.context_pack import REPO_ROOT, normalize_repo_path
from scripts.orchestration.routing_graph_loader import (
    BootstrapLaneActivation,
    REQUIRED_BOOTSTRAP_LANE,
)
from scripts.orchestration.skill_router import RESEARCH_POLICY_BUCKET_APPROVED
from scripts.orchestration.task_bootstrap import (
    REQUESTED_AGENT_STATUS_ADVISORY_DOMAIN_MISMATCH,
    REQUESTED_AGENT_STATUS_ADVISORY_NON_ROUTABLE,
    REQUESTED_AGENT_STATUS_HONORED_PRIMARY,
    REQUESTED_AGENT_STATUS_PROMOTED,
    REQUESTED_AGENT_STATUS_REJECTED_UNKNOWN,
    _apply_pr_lifecycle_review_path,
    _normalize_secondary_review_path,
    _resolve_output_path,
    build_task_packet,
    main,
)


def test_task_bootstrap_resolves_orchestration_domain() -> None:
    """Scripts/docs orchestration work should resolve to ops/orchestration."""

    packet = build_task_packet(
        goal="Harden orchestration preflight",
        task_class="Orchestration",
        candidate_paths=[
            "scripts/orchestration/check_preflight.py",
            "docs/orchestration/workflow.md",
        ],
    )

    assert packet["schema_version"] == "2.0"
    assert packet["domain"] == "orchestration"
    assert packet["cluster"] == "ops"
    assert packet["primary_agent"]
    assert "AGENTS.md" in packet["required_context"]
    assert "docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md" in packet["required_context"]
    assert "scripts/AGENTS.md" in packet["required_context"]
    assert packet["skill_routing"]["selection_mode"] == "deterministic-weighted"
    assert "pulseplate-workflow" in packet["recommended_skills"]
    assert "docs-sync" in packet["recommended_skills"]
    assert "agents-md" in packet["recommended_skills"]
    assert packet["decision_contract"] == {
        "mode": "standard",
        "judgment_enabled": False,
        "claim_taxonomy": [],
        "flow": [],
    }
    assert packet["judgment_budget"] == {
        "skeptic_pass_required": False,
        "verifier_pass_required": False,
        "max_provider_calls": 0,
        "uncertainty_split_required": False,
    }
    assert packet["result_adjudication"] == {
        "claim_evidence_fields": [],
        "support_statuses": [],
        "evidence_modes": [],
        "uncertainty_fields": [],
        "promotion_labels": [],
    }
    assert packet["native_subagent_bridge"]["primary"]["repo_agent_slug"] == "agent-coordinator"
    assert packet["native_subagent_bridge"]["reviewer"]["repo_agent_slug"] == (
        "architecture-specialist"
    )


def test_task_bootstrap_adds_automation_metadata_defaults() -> None:
    """Generic task packets should include additive automation metadata with safe defaults."""

    packet = build_task_packet(
        goal="Refresh engineering lessons docs",
        task_class="Documentation",
        candidate_paths=["docs/ENGINEERING_LESSONS.md"],
    )

    assert packet["automation_flags"] == {
        "coordinator_first_required": True,
        "skill_routing_applied": True,
        "native_subagent_bridge_available": True,
        "security_review_required": False,
        "judgment_lane_enabled": False,
        "pr_lifecycle_enabled": False,
        "design_lane_enabled": False,
    }
    assert packet["pr_phase"] == "none"
    assert packet["pr_lifecycle_contract"] == {
        "requires_pr": False,
        "post_open_review_required": False,
        "review_lane": [],
        "artifact_template": "",
        "current_head_required": False,
        "current_head_truth": "not-applicable",
        "merge_readiness_entrypoint": "",
    }
    assert packet["design_lane_mode"] == "disabled"
    assert packet["design_lane_contract"] == {
        "design_source": "",
        "source_url": "",
        "file_key_or_workspace": "",
        "node_id_or_frame_id": "",
        "target_surface": "",
        "task_mode": "",
        "figma_lane_tool": "",
        "blockers": ["missing_design_trigger"],
        "code_native_design_brief_required": False,
        "code_native_design_brief_path": "",
        "explicit_creation_mode": False,
    }
    assert packet["message_envelope"] == {
        "protocol_version": "1.0",
        "derived_view": "TASK_PACKET_V1",
        "mode": "docs-only",
        "output_requirements": {
            "must_return": ["AGENT_RESULT_V1 envelope only (no preamble)"],
        },
    }
    assert packet["skill_routing"]["envelope_mode_hint"] == "docs_only"
    _docs_paths = ["docs/ENGINEERING_LESSONS.md"]
    _norm_docs = repo_relative_paths([p.strip() for p in _docs_paths if p.strip()])
    assert packet["skill_routing"]["envelope_mode_hint"] == resolve_analysis_envelope_mode(
        _norm_docs
    )
    implementation_skills = {
        "pulseplate-backend-endpoints",
        "pulseplate-openapi-sync",
        "pulseplate-frontend-ui",
        "vercel-react-best-practices",
    }
    recommended = {item["skill"] for item in packet["skill_routing"]["recommended"]}
    assert implementation_skills.isdisjoint(recommended)
    assert packet["needs_backlog_update"] is False
    assert packet["needs_docs_sync"] is False
    assert packet["needs_agents_sync"] is False


def test_task_bootstrap_exposes_skill_routing_explanation_and_connector_policy() -> None:
    """Bootstrap packets should carry the wave 2 explanation and connector contract."""

    packet = build_task_packet(
        goal=(
            "Prepare founder research using YouTube transcripts and Google Trends "
            "with a stable skill-routing explanation schema"
        ),
        task_class="Research",
        candidate_paths=["docs/audience_pack/ENGINEERING_OVERVIEW.md"],
    )

    explanation = packet["skill_routing"]["explanation"]
    connector_policy = packet["skill_routing"]["research_connector_policy"]
    assert explanation["schema_version"] == "1.0"
    assert "semantic_group" in explanation["evidence_axes"]
    assert connector_policy["policy_version"] == "2026-04-18"
    matched_connectors = {
        item["connector"] for item in connector_policy["matches"][RESEARCH_POLICY_BUCKET_APPROVED]
    }
    assert matched_connectors == {"youtube_transcripts", "google_trends"}


def test_task_bootstrap_sets_read_only_design_lane_for_incomplete_figma_packet() -> None:
    """Explicit Figma packets should fail closed into read-only until metadata is complete."""

    packet = build_task_packet(
        goal="Prepare Figma activation packet",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        design_source="figma_design",
        target_surface="web.hero",
        task_mode="implement",
        figma_lane_tool="figma_native",
        code_native_design_brief_path="docs/design/HERO_BRIEF.md",
    )

    assert packet["automation_flags"]["design_lane_enabled"] is True
    assert packet["design_lane_mode"] == "read_only"
    assert packet["design_lane_contract"]["design_source"] == "figma_design"
    assert packet["design_lane_contract"]["blockers"] == ["blocked_by_design_url"]
    assert packet["design_lane_contract"]["code_native_design_brief_required"] is True


def test_task_bootstrap_keeps_coordinator_primary_for_requested_orchestration_lane() -> None:
    """Coordinator-owned orchestration lanes must not demote agent-coordinator from primary."""

    packet = build_task_packet(
        goal="Implement wave 2 routing policy and explanation schema",
        task_class="Orchestration",
        candidate_paths=[
            "scripts/orchestration/skill_router.py",
            "scripts/orchestration/task_bootstrap.py",
        ],
        requested_agents=[
            "agent-coordinator",
            "architecture-specialist",
            "security-auditor",
        ],
        pr_phase="pre_open",
    )

    assert packet["primary_agent"] == "agent-coordinator"
    dispositions = {item["agent"]: item for item in packet["requested_agent_disposition"]}
    assert dispositions["agent-coordinator"]["status"] == REQUESTED_AGENT_STATUS_HONORED_PRIMARY
    assert dispositions["architecture-specialist"]["status"] == "honored_reviewer"
    assert "security-auditor" in packet["secondary_agents"]


def test_task_bootstrap_enables_code_native_design_lane_with_valid_packet() -> None:
    """Code-native design packets should activate without Figma-specific blockers."""

    packet = build_task_packet(
        goal="Implement code-native design brief",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        design_source="code_native_brief",
        target_surface="web.hero",
        task_mode="implement",
        code_native_design_brief_path="docs/design/HERO_BRIEF.md",
    )

    assert packet["automation_flags"]["design_lane_enabled"] is True
    assert packet["design_lane_mode"] == "implement"
    assert packet["design_lane_contract"]["blockers"] == []
    assert packet["design_lane_contract"]["design_source"] == "code_native_brief"
    assert packet["design_lane_contract"]["code_native_design_brief_required"] is True


def test_task_bootstrap_enables_figma_design_lane_with_complete_packet() -> None:
    """Complete Figma packets should activate the requested task mode."""

    packet = build_task_packet(
        goal="Sync Figma-backed design packet",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        design_source="figma_design",
        source_url="https://www.figma.com/design/demo/File?node-id=42-7",
        file_key_or_workspace="demo",
        node_id_or_frame_id="42:7",
        target_surface="web.hero",
        task_mode="sync",
        figma_lane_tool="figma_native",
        code_native_design_brief_path="docs/design/HERO_BRIEF.md",
    )

    assert packet["automation_flags"]["design_lane_enabled"] is True
    assert packet["design_lane_mode"] == "sync"
    assert packet["design_lane_contract"]["blockers"] == []
    assert packet["design_lane_contract"]["node_id_or_frame_id"] == "42:7"


def test_task_bootstrap_allows_explicit_figma_creation_mode_without_existing_node() -> None:
    """Explicit creation mode should unlock Figma activation without existing URL/node metadata."""

    packet = build_task_packet(
        goal="Create a new Figma design surface from the canonical brief",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        design_source="figma_design",
        target_surface="web.hero",
        task_mode="implement",
        figma_lane_tool="figma_native",
        code_native_design_brief_path="docs/design/HERO_BRIEF.md",
        explicit_creation_mode=True,
    )

    assert packet["automation_flags"]["design_lane_enabled"] is True
    assert packet["design_lane_mode"] == "implement"
    assert packet["design_lane_contract"]["blockers"] == []
    assert packet["design_lane_contract"]["explicit_creation_mode"] is True


def test_task_bootstrap_requires_existing_figma_metadata_for_non_implement_creation_mode() -> None:
    """Creation-mode bypass must not skip URL/node checks for verify or sync flows."""

    packet = build_task_packet(
        goal="Verify an existing Figma design surface from the canonical brief",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        design_source="figma_design",
        target_surface="web.hero",
        task_mode="sync",
        figma_lane_tool="figma_native",
        code_native_design_brief_path="docs/design/HERO_BRIEF.md",
        explicit_creation_mode=True,
    )

    assert packet["automation_flags"]["design_lane_enabled"] is True
    assert packet["design_lane_mode"] == "read_only"
    assert packet["design_lane_contract"]["blockers"] == ["blocked_by_design_url"]
    assert packet["design_lane_contract"]["explicit_creation_mode"] is True


def test_task_bootstrap_enables_post_open_review_lane_for_pr_phase() -> None:
    """Post-open review packets must synthesize the canonical QA -> bug-hunter lane."""

    packet = build_task_packet(
        goal="Prepare post-open PR review loop for orchestration automation",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        pr_phase="post_open_review",
    )

    assert packet["automation_flags"]["pr_lifecycle_enabled"] is True
    assert packet["pr_phase"] == "post_open_review"
    assert packet["pr_lifecycle_contract"] == {
        "requires_pr": True,
        "post_open_review_required": True,
        "review_lane": ["qa-engineer-agent", "bug-hunter"],
        "artifact_template": "docs/review/PR_<N>_FIXED_MAPPING.md",
        "current_head_required": True,
        "current_head_truth": "latest-current-head",
        "merge_readiness_entrypoint": "",
    }
    assert packet["reviewer"] == "qa-engineer-agent"
    assert "bug-hunter" in packet["secondary_agents"]
    assert "bug-hunter" in {
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["secondary"]
    }


def test_task_bootstrap_fails_closed_to_analysis_envelope_for_mixed_scope() -> None:
    """Mixed runtime plus docs scope must not downshift to docs-only envelope mode."""

    packet = build_task_packet(
        goal="Reconcile bootstrap seam and protocol docs",
        task_class="Orchestration",
        candidate_paths=[
            "scripts/orchestration/task_bootstrap.py",
            "docs/orchestration/AGENT_MESSAGE_PROTOCOL.md",
        ],
    )

    assert packet["message_envelope"] == {
        "protocol_version": "1.0",
        "derived_view": "TASK_PACKET_V1",
        "mode": "analysis",
        "output_requirements": {
            "must_return": ["AGENT_RESULT_V1 envelope only (no preamble)"],
        },
    }


def test_task_bootstrap_fails_closed_to_analysis_for_privileged_docs() -> None:
    """Privileged orchestration docs stay in analysis mode while forcing security review."""

    packet = build_task_packet(
        goal="Tighten agent message protocol wording",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"],
    )

    assert packet["message_envelope"]["mode"] == "analysis"
    assert packet["automation_flags"]["security_review_required"] is True


def test_task_bootstrap_normalizes_whitespace_padded_privileged_docs() -> None:
    """Whitespace-padded privileged docs must still force analysis mode."""

    packet = build_task_packet(
        goal="Tighten agent message protocol wording",
        task_class="Documentation",
        candidate_paths=["  docs/orchestration/AGENT_MESSAGE_PROTOCOL.md  "],
    )

    assert packet["message_envelope"]["mode"] == "analysis"
    assert packet["automation_flags"]["security_review_required"] is True


def test_task_bootstrap_keeps_requested_bug_hunter_executable_in_post_open_lane() -> None:
    """Requested bug-hunter must stay runnable in the canonical post-open lane."""

    packet = build_task_packet(
        goal="Run post-open review with explicit bug hunter request",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["bug-hunter"],
        pr_phase="post_open_review",
    )

    assert "bug-hunter" in packet["secondary_agents"]
    assert "bug-hunter" in {
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["secondary"]
    }
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "bug-hunter",
            "status": "honored_secondary",
            "reason": (
                "Requested agent is required for the PR lifecycle review path and stays "
                "executable in secondary."
            ),
        }
    ]


def test_task_bootstrap_preserves_qa_then_bug_hunter_order_in_qa_post_open_lane() -> None:
    """QA-domain post-open packets must not allow bug-hunter to remain primary."""

    packet = build_task_packet(
        goal="Run qa post-open review with explicit bug hunter request",
        task_class="QA",
        candidate_paths=["tests/test_task_bootstrap.py"],
        requested_agents=["bug-hunter"],
        pr_phase="post_open_review",
    )

    assert packet["primary_agent"] == "qa-engineer-agent"
    assert packet["reviewer"] == "agent-coordinator"
    assert packet["secondary_agents"] == ["bug-hunter"]
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "bug-hunter",
            "status": "honored_secondary",
            "reason": "Requested agent stayed honored in secondary after PR lifecycle synthesis.",
        }
    ]


def test_post_open_review_path_keeps_bug_hunter_executable_when_primary_was_bug_hunter() -> None:
    """Helper-level regression: reviewer independence must not drop bug-hunter from secondary."""

    primary_agent, secondary_agents, reviewer = _apply_pr_lifecycle_review_path(
        pr_phase="post_open_review",
        primary_agent="bug-hunter",
        secondary_agents=[],
        reviewer="qa-engineer-agent",
    )

    normalized_secondary_agents = _normalize_secondary_review_path(
        primary_agent=primary_agent,
        secondary_agents=secondary_agents,
        reviewer=reviewer,
    )

    assert primary_agent == "qa-engineer-agent"
    assert reviewer == "agent-coordinator"
    assert normalized_secondary_agents == ["bug-hunter"]


def test_task_bootstrap_deduplicates_reviewer_from_secondary_in_post_open_lane() -> None:
    """Canonical packet identities must not list the reviewer twice."""

    packet = build_task_packet(
        goal="Run post-open review with explicit QA request",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["qa-engineer-agent"],
        pr_phase="post_open_review",
    )

    assert packet["reviewer"] == "qa-engineer-agent"
    assert "qa-engineer-agent" not in packet["secondary_agents"]
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "qa-engineer-agent",
            "status": "honored_reviewer",
            "reason": "Requested agent stayed honored as reviewer after PR lifecycle synthesis.",
        }
    ]


def test_task_bootstrap_keeps_non_routable_requested_agent_advisory_in_post_open_lane() -> None:
    """Lifecycle reconciliation must keep advisory agents as required role passes."""

    packet = build_task_packet(
        goal="Prepare ML post-open review packet with advisory collaborator",
        task_class="AI / ML",
        candidate_paths=["docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md"],
        requested_agents=["ml-engineer-agent"],
        pr_phase="post_open_review",
    )

    assert "ml-engineer-agent" in packet["secondary_agents"]
    advisory_bindings = packet["native_subagent_bridge"]["advisory"]
    assert [binding["repo_agent_slug"] for binding in advisory_bindings] == ["ml-engineer-agent"]
    assert advisory_bindings[0]["execution_mode"] == "advisory_review"
    assert advisory_bindings[0]["dispatch_contract"]["spawn_with_native_subagent"] is True
    assert advisory_bindings[0]["dispatch_contract"]["required_role_pass"] is True
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "ml-engineer-agent",
            "status": "advisory_non_routable",
            "reason": "Agent is canonical but non-routable; kept as an advisory collaborator.",
        }
    ]


def test_task_bootstrap_keeps_unknown_requested_agent_rejected_in_post_open_lane() -> None:
    """Post-open synthesis must not upgrade unknown requested agents into runnable roles."""

    packet = build_task_packet(
        goal="Prepare post-open review packet with unknown collaborator request",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["unknown-agent"],
        pr_phase="post_open_review",
    )

    assert packet["requested_agents"] == ["unknown-agent"]
    assert "unknown-agent" not in packet["secondary_agents"]
    assert not [
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["advisory"]
    ]
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "unknown-agent",
            "status": "rejected_unknown_agent",
            "reason": "Agent is not registered in the canonical inventory.",
        }
    ]


def test_task_bootstrap_keeps_domain_mismatch_requested_agent_advisory_in_post_open_lane() -> None:
    """Post-open synthesis must preserve domain-mismatched requests as required advisory."""

    packet = build_task_packet(
        goal="Prepare post-open review packet with frontend collaborator request",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["frontend-engineer"],
        pr_phase="post_open_review",
    )

    assert "frontend-engineer" in packet["secondary_agents"]
    advisory_bindings = packet["native_subagent_bridge"]["advisory"]
    assert [binding["repo_agent_slug"] for binding in advisory_bindings] == ["frontend-engineer"]
    assert advisory_bindings[0]["execution_mode"] == "advisory_review"
    assert advisory_bindings[0]["dispatch_contract"]["spawn_with_native_subagent"] is True
    assert advisory_bindings[0]["dispatch_contract"]["required_role_pass"] is True
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "frontend-engineer",
            "status": "advisory_domain_mismatch",
            "reason": "Requested agent stays advisory because it is outside the routed domain slot set.",
        }
    ]


def test_task_bootstrap_sets_merge_ready_contract_without_post_open_lane() -> None:
    """Merge-ready packets should keep lifecycle prep explicit without re-adding QA loop."""

    packet = build_task_packet(
        goal="Prepare merge readiness packet for orchestration automation",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        pr_phase="merge_ready",
    )

    assert packet["automation_flags"]["pr_lifecycle_enabled"] is True
    assert packet["pr_phase"] == "merge_ready"
    assert packet["pr_lifecycle_contract"] == {
        "requires_pr": True,
        "post_open_review_required": False,
        "review_lane": [],
        "artifact_template": "docs/review/PR_<N>_FIXED_MAPPING.md",
        "current_head_required": True,
        "current_head_truth": "latest-current-head",
        "merge_readiness_entrypoint": "scripts/orchestration/check_merge_ready.py",
    }
    assert packet["reviewer"] != "qa-engineer-agent"
    assert "bug-hunter" not in packet["secondary_agents"]


def test_task_bootstrap_enables_judgment_lane_for_relevant_work() -> None:
    """Judgment metadata should activate only for adjudication-oriented tasks."""

    packet = build_task_packet(
        goal="Add judgment adjudication protocol and shared evidence contract",
        task_class="Documentation",
        candidate_paths=[
            "docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md",
            "core/judgment.py",
        ],
    )

    assert packet["decision_contract"]["mode"] == "verification_first"
    assert packet["decision_contract"]["judgment_enabled"] is True
    assert packet["decision_contract"]["claim_taxonomy"] == list(CLAIM_TYPES)
    assert packet["decision_contract"]["flow"] == list(JUDGMENT_FLOW)
    assert packet["judgment_budget"] == {
        "skeptic_pass_required": True,
        "verifier_pass_required": True,
        "max_provider_calls": 0,
        "uncertainty_split_required": True,
    }
    assert packet["automation_flags"]["judgment_lane_enabled"] is True
    assert packet["result_adjudication"]["claim_evidence_fields"] == list(CLAIM_EVIDENCE_FIELDS)
    assert packet["result_adjudication"]["support_statuses"] == list(SUPPORT_STATUSES)
    assert packet["result_adjudication"]["evidence_modes"] == list(EVIDENCE_MODES)
    assert packet["result_adjudication"]["uncertainty_fields"] == list(UNCERTAINTY_FIELDS)
    assert packet["result_adjudication"]["promotion_labels"] == list(PROMOTION_LABELS)


def test_task_bootstrap_enables_judgment_lane_for_underscore_triggers() -> None:
    """Underscore-separated trigger terms must activate the judgment lane."""

    packet = build_task_packet(
        goal="Prepare evidence_reconciliation follow-up",
        task_class="verification_first",
        candidate_paths=["docs/orchestration/EVIDENCE_RECONCILIATION_PROTOCOL.md"],
    )

    assert packet["decision_contract"]["mode"] == "verification_first"
    assert packet["decision_contract"]["judgment_enabled"] is True
    assert packet["judgment_budget"]["max_provider_calls"] == 0


def test_task_bootstrap_uses_loader_backed_judgment_activation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Judgment-lane enablement must follow routing-graph loader metadata."""

    monkeypatch.setattr(
        "scripts.orchestration.task_bootstrap.load_bootstrap_lane_activations",
        lambda: {
            REQUIRED_BOOTSTRAP_LANE: BootstrapLaneActivation(
                lane=REQUIRED_BOOTSTRAP_LANE,
                signal_terms=("custom-lane-trigger",),
                decision_mode="verification_first",
            )
        },
    )

    packet = build_task_packet(
        goal="Prepare custom-lane-trigger follow-up",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/AGENT_ROUTING_GRAPH.md"],
    )

    assert packet["decision_contract"]["mode"] == "verification_first"
    assert packet["decision_contract"]["judgment_enabled"] is True


def test_task_bootstrap_does_not_fall_back_to_removed_hardcoded_terms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Custom loader metadata should fully replace legacy hardcoded trigger terms."""

    monkeypatch.setattr(
        "scripts.orchestration.task_bootstrap.load_bootstrap_lane_activations",
        lambda: {
            REQUIRED_BOOTSTRAP_LANE: BootstrapLaneActivation(
                lane=REQUIRED_BOOTSTRAP_LANE,
                signal_terms=("custom-lane-trigger",),
                decision_mode="verification_first",
            )
        },
    )

    packet = build_task_packet(
        goal="Prepare evidence_reconciliation follow-up",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/AGENT_ROUTING_GRAPH.md"],
    )

    assert packet["decision_contract"]["mode"] == "standard"
    assert packet["decision_contract"]["judgment_enabled"] is False


def test_task_bootstrap_requires_canonical_judgment_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bootstrap must fail fast if the required judgment lane disappears from the SoT."""

    monkeypatch.setattr(
        "scripts.orchestration.task_bootstrap.load_bootstrap_lane_activations",
        lambda: {
            "research": BootstrapLaneActivation(
                lane="research",
                signal_terms=("custom-lane-trigger",),
                decision_mode="verification_first",
            )
        },
    )

    with pytest.raises(
        ValueError,
        match=f"Required bootstrap lane activation missing: {REQUIRED_BOOTSTRAP_LANE}",
    ):
        build_task_packet(
            goal="Prepare custom-lane-trigger follow-up",
            task_class="Documentation",
            candidate_paths=["docs/orchestration/AGENT_ROUTING_GRAPH.md"],
        )


def test_task_bootstrap_rejects_unsupported_judgment_decision_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Judgment packets must reject loader modes that drift from supported semantics."""

    monkeypatch.setattr(
        "scripts.orchestration.task_bootstrap.load_bootstrap_lane_activations",
        lambda: {
            REQUIRED_BOOTSTRAP_LANE: BootstrapLaneActivation(
                lane=REQUIRED_BOOTSTRAP_LANE,
                signal_terms=("custom-lane-trigger",),
                decision_mode="standard",
            )
        },
    )

    with pytest.raises(
        ValueError,
        match="Unsupported judgment lane decision mode: standard. Supported: verification_first",
    ):
        build_task_packet(
            goal="Prepare custom-lane-trigger follow-up",
            task_class="Documentation",
            candidate_paths=["docs/orchestration/AGENT_ROUTING_GRAPH.md"],
        )


def test_task_bootstrap_adds_judgment_context_for_single_file_trigger() -> None:
    """Single-file judgment triggers must still receive judgment SoT context."""

    packet = build_task_packet(
        goal="Refactor judgment helper docstrings",
        task_class="Backend API",
        candidate_paths=["core/judgment.py"],
    )

    assert packet["decision_contract"]["judgment_enabled"] is True
    assert "docs/orchestration/AGENT_ROUTING_GRAPH.md" in packet["required_context"]
    assert (
        "docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md" in packet["required_context"]
    )
    assert "docs/orchestration/EVIDENCE_RECONCILIATION_PROTOCOL.md" in packet["required_context"]


def test_task_bootstrap_includes_scoped_agents_only_once() -> None:
    """Context pack must be deterministic and de-duplicated."""

    packet = build_task_packet(
        goal="Update frontend release workflow",
        task_class="Release",
        candidate_paths=[
            "frontend/src/components/Button.tsx",
            "frontend/src/config/routes.ts",
        ],
    )

    required_context = packet["required_context"]
    assert required_context == sorted(required_context)
    assert required_context.count("frontend/AGENTS.md") == 1
    assert packet["skill_routing"]["recommended"]
    assert "pulseplate-workflow" in packet["recommended_skills"]
    assert "pulseplate-frontend-ui" in packet["recommended_skills"]


def test_task_bootstrap_routes_cv_tasks_to_cv_domain() -> None:
    """CV-first tasks should route to the graph-primary CV domain under ML."""

    packet = build_task_packet(
        goal="Evaluate food image recognition reliability for offline CV review",
        task_class="AI / ML",
        candidate_paths=[
            ".cursor/agents/cv-agent.md",
            "docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md",
        ],
    )

    assert packet["domain"] == "cv"
    assert packet["cluster"] == "ml"
    assert packet["primary_agent"] == "cv-agent"
    assert packet["secondary_agents"] == ["data-scientist-agent"]
    assert packet["reviewer"] == "security-auditor"
    assert "docs-sync" in packet["recommended_skills"]
    assert "pulseplate-gates" in packet["recommended_skills"]
    assert packet["native_subagent_bridge"]["primary"]["native_agent_type"] == "default"
    assert packet["native_subagent_bridge"]["reviewer"]["native_agent_type"] == "explorer"


def test_task_bootstrap_promotes_requested_routable_agent() -> None:
    """Requested agents already present in the routed slot set may become primary."""

    packet = build_task_packet(
        goal="Implement backend entitlement routing",
        task_class="Backend API",
        candidate_paths=["app/middleware/api_tiers.py"],
        requested_agents=["backend-engineer"],
    )

    assert packet["domain"] == "backend"
    assert packet["primary_agent"] == "backend-engineer"
    assert "architecture-specialist" in packet["secondary_agents"]
    assert packet["requested_agents"] == ["backend-engineer"]
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "backend-engineer",
            "status": "honored_primary",
            "reason": "Requested agent already matches the routed primary.",
        }
    ]


def test_task_bootstrap_keeps_non_routable_requested_agent_as_advisory() -> None:
    """Non-routable specialists should be preserved as required advisory passes."""

    packet = build_task_packet(
        goal="Design AI reliability experiment packet",
        task_class="AI / ML",
        candidate_paths=["docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md"],
        requested_agents=["ml-engineer-agent"],
    )

    assert packet["domain"] == "ml"
    assert packet["primary_agent"] == "ai-innovation-specialist"
    assert "ml-engineer-agent" in packet["secondary_agents"]
    assert {
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["secondary"]
    } == {"rag-systems-agent", "security-auditor"}
    advisory_bindings = packet["native_subagent_bridge"]["advisory"]
    assert [binding["repo_agent_slug"] for binding in advisory_bindings] == ["ml-engineer-agent"]
    assert advisory_bindings[0]["execution_mode"] == "advisory_review"
    assert advisory_bindings[0]["dispatch_contract"]["advisory_only"] is False
    assert advisory_bindings[0]["dispatch_contract"]["required_role_pass"] is True
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "ml-engineer-agent",
            "status": "advisory_non_routable",
            "reason": "Agent is canonical but non-routable; kept as an advisory collaborator.",
        }
    ]


def test_task_bootstrap_rejects_unknown_requested_agent_with_explicit_rationale() -> None:
    """Unknown requested agents must stay visible in packet metadata with rejection rationale."""

    packet = build_task_packet(
        goal="Implement backend entitlement routing",
        task_class="Backend API",
        candidate_paths=["app/middleware/api_tiers.py"],
        requested_agents=[" Unknown-Agent ", "unknown-agent"],
    )

    assert packet["requested_agents"] == ["unknown-agent"]
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "unknown-agent",
            "status": "rejected_unknown_agent",
            "reason": "Agent is not registered in the canonical inventory.",
        }
    ]
    assert "unknown-agent" not in packet["secondary_agents"]
    assert not [
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["advisory"]
    ]


def test_task_bootstrap_keeps_domain_mismatch_requested_agent_as_advisory() -> None:
    """Routable-but-mismatched requested agents stay required advisory passes."""

    packet = build_task_packet(
        goal="Implement backend entitlement routing",
        task_class="Backend API",
        candidate_paths=["app/middleware/api_tiers.py"],
        requested_agents=["frontend-engineer"],
    )

    assert packet["requested_agents"] == ["frontend-engineer"]
    assert "frontend-engineer" in packet["secondary_agents"]
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "frontend-engineer",
            "status": "advisory_domain_mismatch",
            "reason": "Requested agent stays advisory because it is outside the routed domain slot set.",
        }
    ]
    assert {
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["secondary"]
    } == {"architecture-specialist"}
    advisory_bindings = packet["native_subagent_bridge"]["advisory"]
    assert [binding["repo_agent_slug"] for binding in advisory_bindings] == ["frontend-engineer"]
    assert advisory_bindings[0]["execution_mode"] == "advisory_review"
    assert advisory_bindings[0]["dispatch_contract"]["spawn_with_native_subagent"] is True
    assert advisory_bindings[0]["dispatch_contract"]["required_role_pass"] is True


def test_task_bootstrap_requested_agents_change_packet_id() -> None:
    """Requested agents should contribute to the deterministic packet identity."""

    baseline = build_task_packet(
        goal="Implement backend entitlement routing",
        task_class="Backend API",
        candidate_paths=["app/middleware/api_tiers.py"],
    )
    with_requested = build_task_packet(
        goal="Implement backend entitlement routing",
        task_class="Backend API",
        candidate_paths=["app/middleware/api_tiers.py"],
        requested_agents=["backend-engineer"],
    )

    assert baseline["task_packet_id"] != with_requested["task_packet_id"]


def test_task_bootstrap_keeps_security_auditor_in_privileged_review_path() -> None:
    """Privileged orchestration paths must retain security review after overrides."""

    packet = build_task_packet(
        goal="Update privileged orchestration workflow",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["agent-coordinator"],
    )

    review_path = {
        packet["primary_agent"],
        packet["reviewer"],
        *packet["secondary_agents"],
    }
    assert "security-auditor" in review_path
    assert packet["automation_flags"]["security_review_required"] is True
    assert "security-auditor" in {
        packet["native_subagent_bridge"]["reviewer"]["repo_agent_slug"],
        *[binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["secondary"]],
    }
    assert "security-auditor" not in {
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["advisory"]
    }


@pytest.mark.parametrize(
    "candidate_path",
    (
        "scripts/ci/check_pr_merge_readiness.py",
        "docs/orchestration/workflow.md",
        "docs/review/PR_1254_FIXED_MAPPING.md",
    ),
)
def test_task_bootstrap_marks_merge_governance_paths_as_privileged(
    candidate_path: str,
) -> None:
    """Merge-governance docs/scripts must force the security review path."""

    packet = build_task_packet(
        goal="Refresh merge-governance automation contract",
        task_class="Documentation",
        candidate_paths=[candidate_path],
        requested_agents=["agent-coordinator"],
    )

    review_path = {
        packet["primary_agent"],
        packet["reviewer"],
        *packet["secondary_agents"],
    }

    assert packet["automation_flags"]["security_review_required"] is True
    assert "security-auditor" in review_path
    assert "security-auditor" in {
        packet["native_subagent_bridge"]["reviewer"]["repo_agent_slug"],
        *[binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["secondary"]],
    }


def test_task_bootstrap_forces_requested_security_auditor_into_executable_bridge() -> None:
    """Privileged review must keep an explicitly requested security auditor runnable."""

    packet = build_task_packet(
        goal="Audit privileged orchestration workflow",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["security-auditor"],
    )

    assert "security-auditor" in packet["secondary_agents"]
    assert "security-auditor" in {
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["secondary"]
    }
    assert "security-auditor" not in {
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["advisory"]
    }
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "security-auditor",
            "status": "honored_secondary",
            "reason": (
                "Requested agent is required for the privileged review path and stays "
                "executable in secondary."
            ),
        }
    ]


def test_task_bootstrap_preserves_coordinator_primary_for_requested_orchestration_lane() -> None:
    """Coordinator-owned orchestration lanes should keep agent-coordinator as primary."""

    packet = build_task_packet(
        goal="Update privileged orchestration workflow",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["agent-coordinator", "architecture-specialist"],
    )

    assert packet["primary_agent"] == "agent-coordinator"
    assert "agent-coordinator" not in packet["secondary_agents"]
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "agent-coordinator",
            "status": "honored_primary",
            "reason": "Requested agent already matches the routed primary.",
        },
        {
            "agent": "architecture-specialist",
            "status": "honored_reviewer",
            "reason": (
                "Coordinator-owned lane keeps `agent-coordinator` as primary; "
                "requested reviewer stays honored in reviewer."
            ),
        },
    ]


def test_task_bootstrap_keeps_displaced_requested_reviewer_required_post_open() -> None:
    """Post-open QA synthesis must not drop a requested reviewer role pass."""

    packet = build_task_packet(
        goal="Update privileged orchestration workflow",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["agent-coordinator", "architecture-specialist"],
        pr_phase="post_open_review",
    )

    assert packet["primary_agent"] == "agent-coordinator"
    assert packet["reviewer"] == "qa-engineer-agent"
    assert "architecture-specialist" in packet["secondary_agents"]
    assert "architecture-specialist" in {
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["secondary"]
    }
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "agent-coordinator",
            "status": "honored_primary",
            "reason": "Requested agent already matches the routed primary.",
        },
        {
            "agent": "architecture-specialist",
            "status": "honored_secondary",
            "reason": (
                "Requested reviewer remains a required role pass after PR lifecycle synthesis."
            ),
        },
    ]


def test_task_bootstrap_does_not_treat_cve_or_cvss_as_cv_domain() -> None:
    """Security acronyms must not trigger the CV routing domain."""

    packet = build_task_packet(
        goal="Audit CVE and CVSS handling for auth failures",
        task_class="Security",
        candidate_paths=["app/security/auth.py"],
    )

    assert packet["domain"] == "security"


def test_task_bootstrap_preserves_explicit_security_task_class_over_cv_goal_hint() -> None:
    """Explicit non-CV task classes must win over generic CV goal wording."""

    packet = build_task_packet(
        goal="Audit CV controls for image upload abuse paths",
        task_class="Security",
        candidate_paths=["app/security/auth.py"],
    )

    assert packet["domain"] == "security"


def test_task_bootstrap_routes_cv_path_hints_for_cv_routable_task_class() -> None:
    """CV-specific paths should route to CV for ML/CV-class tasks."""

    packet = build_task_packet(
        goal="Refresh CV protocol references",
        task_class="AI / ML",
        candidate_paths=[
            "docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md",
            ".cursor/agents/cv-agent.md",
        ],
    )

    assert packet["domain"] == "cv"
    assert packet["cluster"] == "ml"
    assert packet["primary_agent"] == "cv-agent"


def test_task_bootstrap_preserves_docs_task_class_over_cv_path_hint() -> None:
    """Explicit docs tasks must not be re-routed by CV-specific candidate paths."""

    packet = build_task_packet(
        goal="Refresh CV protocol references",
        task_class="Documentation",
        candidate_paths=[
            "docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md",
            ".cursor/agents/cv-agent.md",
        ],
    )

    assert packet["domain"] == "docs"
    assert packet["cluster"] == "ops"


def test_task_bootstrap_marks_backlog_sync_triggers() -> None:
    """Backlog-oriented inputs should set the deterministic backlog sync flag."""

    packet = build_task_packet(
        goal="Prepare roadmap follow-up for deferred orchestration hardening",
        task_class="Documentation",
        candidate_paths=["docs/roadmap/BACKLOG_LEDGER.md"],
    )

    assert packet["needs_backlog_update"] is True


def test_task_bootstrap_marks_backlog_sync_for_roadmap_marker() -> None:
    """Roadmap markers are part of the explicit PR2 backlog-sync contract."""

    packet = build_task_packet(
        goal="Refresh roadmap sequencing for orchestration follow-ups",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/workflow.md"],
    )

    assert packet["needs_backlog_update"] is True


def test_task_bootstrap_marks_backlog_sync_for_follow_up_variant() -> None:
    """Non-hyphenated follow-up wording should still trigger backlog sync."""

    packet = build_task_packet(
        goal="Track follow up items for orchestration hardening",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/workflow.md"],
    )

    assert packet["needs_backlog_update"] is True


def test_task_bootstrap_marks_docs_sync_for_code_only_paths() -> None:
    """Implementation-only tasks should request docs sync when docs paths are absent."""

    packet = build_task_packet(
        goal="Tighten auth middleware behavior",
        task_class="Backend API",
        candidate_paths=["app/security/auth.py"],
    )

    assert packet["needs_docs_sync"] is True


def test_task_bootstrap_marks_agents_sync_for_agent_contract_paths() -> None:
    """Agent and skill contract paths should request agent-doc synchronization."""

    packet = build_task_packet(
        goal="Refresh coordinator contract guidance",
        task_class="Documentation",
        candidate_paths=[
            "AGENTS.md",
            "frontend/AGENTS.md",
            ".cursor/agents/agent-coordinator.md",
            "SKILL.md",
            "skills/coordination/SKILL.md",
        ],
    )

    assert packet["needs_agents_sync"] is True


def test_task_bootstrap_does_not_mark_agents_sync_for_non_contract_paths() -> None:
    """Non-contract docs should not trigger agent synchronization."""

    packet = build_task_packet(
        goal="Refresh orchestration docs",
        task_class="Documentation",
        candidate_paths=["docs/AGENTS-guide.md", "docs/orchestration/workflow.md"],
    )

    assert packet["needs_agents_sync"] is False


def test_task_bootstrap_keeps_packet_id_stable_for_identical_inputs() -> None:
    """Additive metadata must remain derivable without perturbing packet identity."""

    first_packet = build_task_packet(
        goal="Refresh docs sync guidance",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"],
    )
    second_packet = build_task_packet(
        goal="Refresh docs sync guidance",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"],
    )

    assert first_packet["task_packet_id"] == second_packet["task_packet_id"]
    assert first_packet["automation_flags"] == second_packet["automation_flags"]
    assert first_packet["pr_phase"] == second_packet["pr_phase"]
    assert first_packet["design_lane_mode"] == second_packet["design_lane_mode"]
    assert first_packet["design_lane_contract"] == second_packet["design_lane_contract"]
    assert first_packet["message_envelope"] == second_packet["message_envelope"]
    assert first_packet["needs_backlog_update"] == second_packet["needs_backlog_update"]
    assert first_packet["needs_docs_sync"] == second_packet["needs_docs_sync"]
    assert first_packet["needs_agents_sync"] == second_packet["needs_agents_sync"]


def test_task_bootstrap_changes_packet_id_when_pr_phase_changes() -> None:
    """Lifecycle phase must affect packet identity to avoid artifact collisions."""

    baseline_packet = build_task_packet(
        goal="Refresh docs sync guidance",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"],
    )
    review_packet = build_task_packet(
        goal="Refresh docs sync guidance",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"],
        pr_phase="post_open_review",
    )

    assert baseline_packet["task_packet_id"] != review_packet["task_packet_id"]


def test_task_bootstrap_changes_packet_id_when_design_contract_changes() -> None:
    """Design metadata must participate in packet identity."""

    baseline_packet = build_task_packet(
        goal="Refresh docs sync guidance",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"],
    )
    design_packet = build_task_packet(
        goal="Refresh docs sync guidance",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"],
        design_source="code_native_brief",
        target_surface="web.hero",
        task_mode="implement",
        code_native_design_brief_path="docs/design/HERO_BRIEF.md",
    )

    assert baseline_packet["task_packet_id"] != design_packet["task_packet_id"]


def test_task_bootstrap_canonicalizes_design_blocker_order_for_packet_identity() -> None:
    """Design blocker ordering must not perturb deterministic packet identity."""

    first_packet = build_task_packet(
        goal="Refresh docs sync guidance",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"],
        design_source="code_native_brief",
        target_surface="web.hero",
        task_mode="implement",
        code_native_design_brief_path="docs/design/HERO_BRIEF.md",
        design_blockers=("stale", "blocked_by_plan"),
    )
    second_packet = build_task_packet(
        goal="Refresh docs sync guidance",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"],
        design_source="code_native_brief",
        target_surface="web.hero",
        task_mode="implement",
        code_native_design_brief_path="docs/design/HERO_BRIEF.md",
        design_blockers=("blocked_by_plan", "stale"),
    )

    assert first_packet["task_packet_id"] == second_packet["task_packet_id"]
    assert first_packet["design_lane_contract"]["blockers"] == [
        "blocked_by_plan",
        "stale",
    ]
    assert second_packet["design_lane_contract"]["blockers"] == [
        "blocked_by_plan",
        "stale",
    ]


def test_canonicalize_design_blockers_keeps_unknown_entries_deterministic() -> None:
    """Unknown blockers must not crash direct canonicalization helpers."""

    assert canonicalize_design_blockers(
        ("custom_blocker", "blocked_by_plan", "custom_alpha"),
    ) == [
        "blocked_by_plan",
        "custom_alpha",
        "custom_blocker",
    ]


def test_matches_any_prefix_covers_exact_and_nested_paths() -> None:
    """Prefix matcher must honor exact directory roots and nested repo paths."""

    prefixes = ("scripts/", "docs/orchestration/")

    assert matches_any_prefix("scripts", prefixes) is True
    assert matches_any_prefix("scripts/orchestration/task_bootstrap.py", prefixes) is True
    assert matches_any_prefix("docs/orchestration/workflow.md", prefixes) is True
    assert matches_any_prefix("tests/test_task_bootstrap.py", prefixes) is False


def test_normalize_repo_path_preserves_dot_cursor_prefix() -> None:
    """Leading './' removal must not strip the '.cursor' directory name."""

    assert normalize_repo_path("./.cursor/agents/agent-coordinator.md") == (
        ".cursor/agents/agent-coordinator.md"
    )


def test_normalize_repo_path_keeps_absolute_outside_repo() -> None:
    """Absolute paths outside repo should not raise and stay absolute."""

    outside = Path("/tmp/pulseplate-outside/task.json")
    assert normalize_repo_path(outside) == outside.as_posix()


def test_resolve_output_path_anchors_relative_paths_to_repo_root() -> None:
    """Relative --output should resolve within the repository root."""

    out_path = _resolve_output_path("tmp/task-packet.json", "ignored")
    assert out_path == (REPO_ROOT / "tmp/task-packet.json").resolve()


def test_main_rejects_output_outside_repo(tmp_path, capsys) -> None:
    """CLI should fail cleanly when --output targets a path outside the repo."""

    outside = tmp_path / "task-packet.json"
    exit_code = main(
        [
            "--goal",
            "Harden orchestration bootstrap",
            "--task-class",
            "Orchestration",
            "--path",
            "scripts/orchestration/task_bootstrap.py",
            "--output",
            str(outside),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL: --output must stay within the repository root" in captured.out


def test_main_writes_relative_output_inside_repo(monkeypatch, capsys) -> None:
    """CLI should write relative --output under repo root and report repo-relative path."""

    # Unique path avoids xdist races on a shared repo-local tmp file.
    relative_output = Path(f"tmp/task-packet-{uuid.uuid4().hex}.json")
    repo_output = (REPO_ROOT / relative_output).resolve()
    if repo_output.exists():
        repo_output.unlink()

    packet = {
        "schema_version": "2.0",
        "task_packet_id": "abc123def456",
        "goal": "Test bootstrap write",
        "task_class": "Orchestration",
        "domain": "orchestration",
        "cluster": "ops",
        "candidate_paths": ["scripts/orchestration/task_bootstrap.py"],
        "primary_agent": "agent-coordinator",
        "secondary_agents": [],
        "reviewer": "architecture-specialist",
        "requested_agents": [],
        "requested_agent_disposition": [],
        "required_context": ["AGENTS.md"],
        "recommended_skills": ["pulseplate-workflow"],
        "skill_routing": {
            "policy_version": "2026-03-27",
            "selection_mode": "deterministic-weighted",
            "requested_agents": [],
            "task_classification": {
                "label": "implementation",
                "score": 0,
                "reasons": ["fallback:default-implementation"],
            },
            "required": [
                {
                    "skill": "pulseplate-workflow",
                    "rationale": "Mandatory entry skill for all PulsePlate tasks.",
                    "reasons": ["always-on"],
                }
            ],
            "recommended": [],
            "conditional": [],
            "blocked": [],
        },
        "decision_contract": {
            "mode": "verification_first",
            "claim_taxonomy": list(CLAIM_TYPES),
            "flow": list(JUDGMENT_FLOW),
        },
        "judgment_budget": {
            "skeptic_pass_required": True,
            "verifier_pass_required": True,
            "max_provider_calls": 1,
            "uncertainty_split_required": True,
        },
        "result_adjudication": {
            "claim_evidence_fields": list(CLAIM_EVIDENCE_FIELDS),
            "support_statuses": list(SUPPORT_STATUSES),
            "evidence_modes": list(EVIDENCE_MODES),
            "uncertainty_fields": list(UNCERTAINTY_FIELDS),
            "promotion_labels": list(PROMOTION_LABELS),
        },
        "native_subagent_bridge": {
            "protocol_version": "1.0",
            "transport": "codex-native-subagents",
            "primary": {"native_agent_type": "default"},
            "secondary": [],
            "reviewer": {"native_agent_type": "explorer"},
        },
        "routing_rationale": {"source": "canonical_only"},
    }
    monkeypatch.setattr(
        "scripts.orchestration.task_bootstrap.build_task_packet",
        lambda **_: packet,
    )

    try:
        exit_code = main(
            [
                "--goal",
                "ignored",
                "--task-class",
                "ignored",
                "--output",
                str(relative_output),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        written = json.loads(repo_output.read_text(encoding="utf-8"))
        assert written["task_packet_id"] == "abc123def456"
        assert written["decision_contract"]["claim_taxonomy"] == list(CLAIM_TYPES)
        assert written["result_adjudication"]["support_statuses"] == list(SUPPORT_STATUSES)
        assert written["result_adjudication"]["evidence_modes"] == list(EVIDENCE_MODES)
        assert json.loads(captured.out)["output"] == relative_output.as_posix()
        assert json.loads(captured.out)["primary_native_agent_type"] == "default"
    finally:
        if repo_output.exists():
            repo_output.unlink()


def test_main_writes_repo_root_output_as_relative_path(monkeypatch, capsys) -> None:
    """Direct children of the repo root should still be reported repo-relative."""

    relative_output = Path(f"task-packet-root-{uuid.uuid4().hex}.json")
    repo_output = (REPO_ROOT / relative_output).resolve()
    if repo_output.exists():
        repo_output.unlink()

    packet = {
        "schema_version": "2.0",
        "task_packet_id": "rootpacket123",
        "goal": "Test root output write",
        "task_class": "Orchestration",
        "domain": "orchestration",
        "cluster": "ops",
        "candidate_paths": ["scripts/orchestration/task_bootstrap.py"],
        "primary_agent": "agent-coordinator",
        "secondary_agents": [],
        "reviewer": "architecture-specialist",
        "requested_agents": [],
        "requested_agent_disposition": [],
        "required_context": ["AGENTS.md"],
        "recommended_skills": ["pulseplate-workflow"],
        "skill_routing": {
            "policy_version": "2026-03-27",
            "selection_mode": "deterministic-weighted",
            "requested_agents": [],
            "task_classification": {
                "label": "implementation",
                "score": 0,
                "reasons": ["fallback:default-implementation"],
            },
            "required": [
                {
                    "skill": "pulseplate-workflow",
                    "rationale": "Mandatory entry skill for all PulsePlate tasks.",
                    "reasons": ["always-on"],
                }
            ],
            "recommended": [],
            "conditional": [],
            "blocked": [],
        },
        "decision_contract": {
            "mode": "verification_first",
            "claim_taxonomy": list(CLAIM_TYPES),
            "flow": list(JUDGMENT_FLOW),
        },
        "judgment_budget": {
            "skeptic_pass_required": True,
            "verifier_pass_required": True,
            "max_provider_calls": 1,
            "uncertainty_split_required": True,
        },
        "result_adjudication": {
            "claim_evidence_fields": list(CLAIM_EVIDENCE_FIELDS),
            "support_statuses": list(SUPPORT_STATUSES),
            "evidence_modes": list(EVIDENCE_MODES),
            "uncertainty_fields": list(UNCERTAINTY_FIELDS),
            "promotion_labels": list(PROMOTION_LABELS),
        },
        "native_subagent_bridge": {
            "protocol_version": "1.0",
            "transport": "codex-native-subagents",
            "primary": {"native_agent_type": "default"},
            "secondary": [],
            "reviewer": {"native_agent_type": "explorer"},
        },
        "routing_rationale": {"source": "canonical_only"},
    }
    monkeypatch.setattr(
        "scripts.orchestration.task_bootstrap.build_task_packet",
        lambda **_: packet,
    )

    try:
        exit_code = main(
            [
                "--goal",
                "ignored",
                "--task-class",
                "ignored",
                "--output",
                str(relative_output),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        assert repo_output.exists()
        written = json.loads(repo_output.read_text(encoding="utf-8"))
        assert written["result_adjudication"]["promotion_labels"] == list(PROMOTION_LABELS)
        assert json.loads(captured.out)["output"] == relative_output.as_posix()
        assert json.loads(captured.out)["reviewer_native_agent_type"] == "explorer"
    finally:
        if repo_output.exists():
            repo_output.unlink()


def test_main_passes_requested_agent_flags(monkeypatch, capsys) -> None:
    """CLI should propagate repeated --requested-agent values into the packet builder."""

    observed: dict[str, object] = {}

    def _fake_build_task_packet(**kwargs: object) -> dict[str, object]:
        observed.update(kwargs)
        return {
            "schema_version": "2.0",
            "task_packet_id": "req-agent-packet",
            "goal": "Use requested agents",
            "task_class": "Orchestration",
            "domain": "orchestration",
            "cluster": "ops",
            "candidate_paths": ["scripts/orchestration/task_bootstrap.py"],
            "primary_agent": "agent-coordinator",
            "secondary_agents": ["security-auditor"],
            "reviewer": "architecture-specialist",
            "requested_agents": ["agent-coordinator", "security-auditor"],
            "requested_agent_disposition": [],
            "required_context": ["AGENTS.md"],
            "recommended_skills": ["pulseplate-workflow"],
            "skill_routing": {
                "policy_version": "2026-03-27",
                "selection_mode": "deterministic-weighted",
                "requested_agents": ["agent-coordinator", "security-auditor"],
                "task_classification": {
                    "label": "implementation",
                    "score": 0,
                    "reasons": ["fallback:default-implementation"],
                },
                "required": [
                    {
                        "skill": "pulseplate-workflow",
                        "rationale": "Mandatory entry skill for all PulsePlate tasks.",
                        "reasons": ["always-on"],
                    }
                ],
                "recommended": [],
                "conditional": [],
                "blocked": [],
            },
            "native_subagent_bridge": {
                "protocol_version": "1.0",
                "transport": "codex-native-subagents",
                "primary": {"native_agent_type": "default"},
                "secondary": [{"native_agent_type": "worker"}],
                "reviewer": {"native_agent_type": "explorer"},
            },
            "routing_rationale": {"source": "canonical_only"},
        }

    monkeypatch.setattr(
        "scripts.orchestration.task_bootstrap.build_task_packet",
        _fake_build_task_packet,
    )

    exit_code = main(
        [
            "--goal",
            "Use explicit requested agents",
            "--task-class",
            "Orchestration",
            "--requested-agent",
            "agent-coordinator",
            "--requested-agent",
            "security-auditor",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert observed["requested_agents"] == ["agent-coordinator", "security-auditor"]
    assert json.loads(captured.out)["requested_agents"] == [
        "agent-coordinator",
        "security-auditor",
    ]
    assert json.loads(captured.out)["primary_native_agent_type"] == "default"


def test_main_passes_pr_phase_flag(monkeypatch, capsys) -> None:
    """CLI should propagate --pr-phase into the packet builder."""

    observed: dict[str, object] = {}

    def _fake_build_task_packet(**kwargs: object) -> dict[str, object]:
        observed.update(kwargs)
        return {
            "schema_version": "2.0",
            "task_packet_id": "pr-phase-packet",
            "goal": "Use explicit PR phase",
            "task_class": "Orchestration",
            "domain": "orchestration",
            "cluster": "ops",
            "candidate_paths": ["scripts/orchestration/task_bootstrap.py"],
            "primary_agent": "agent-coordinator",
            "secondary_agents": ["bug-hunter"],
            "reviewer": "qa-engineer-agent",
            "requested_agents": [],
            "requested_agent_disposition": [],
            "required_context": ["AGENTS.md"],
            "recommended_skills": ["pulseplate-workflow"],
            "skill_routing": {
                "policy_version": "2026-03-27",
                "selection_mode": "deterministic-weighted",
                "requested_agents": [],
                "task_classification": {
                    "label": "implementation",
                    "score": 0,
                    "reasons": ["fallback:default-implementation"],
                },
                "required": [
                    {
                        "skill": "pulseplate-workflow",
                        "rationale": "Mandatory entry skill for all PulsePlate tasks.",
                        "reasons": ["always-on"],
                    }
                ],
                "recommended": [],
                "conditional": [],
                "blocked": [],
            },
            "native_subagent_bridge": {
                "protocol_version": "1.0",
                "transport": "codex-native-subagents",
                "primary": {"native_agent_type": "default"},
                "secondary": [{"native_agent_type": "worker"}],
                "reviewer": {"native_agent_type": "explorer"},
            },
            "routing_rationale": {"source": "canonical_only"},
        }

    monkeypatch.setattr(
        "scripts.orchestration.task_bootstrap.build_task_packet",
        _fake_build_task_packet,
    )

    exit_code = main(
        [
            "--goal",
            "Run post-open review phase",
            "--task-class",
            "Orchestration",
            "--pr-phase",
            "post_open_review",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert observed["pr_phase"] == "post_open_review"
    assert json.loads(captured.out)["task_packet_id"] == "pr-phase-packet"


def test_main_passes_native_bridge_transport_flag(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should propagate --native-bridge-transport into the packet builder."""

    observed: dict[str, object] = {}

    def _fake_build_task_packet(**kwargs: object) -> dict[str, object]:
        observed.update(kwargs)
        return {
            "schema_version": "2.0",
            "task_packet_id": "bridge-transport-packet",
            "goal": "Use kimi native transport",
            "task_class": "Orchestration",
            "domain": "orchestration",
            "cluster": "ops",
            "candidate_paths": ["scripts/orchestration/task_bootstrap.py"],
            "primary_agent": "agent-coordinator",
            "secondary_agents": ["bug-hunter"],
            "reviewer": "qa-engineer-agent",
            "requested_agents": [],
            "requested_agent_disposition": [],
            "required_context": ["AGENTS.md"],
            "recommended_skills": ["pulseplate-workflow"],
            "skill_routing": {
                "policy_version": "2026-03-27",
                "selection_mode": "deterministic-weighted",
                "requested_agents": [],
                "task_classification": {
                    "label": "implementation",
                    "score": 0,
                    "reasons": ["fallback:default-implementation"],
                },
                "required": [
                    {
                        "skill": "pulseplate-workflow",
                        "rationale": "Mandatory entry skill for all PulsePlate tasks.",
                        "reasons": ["always-on"],
                    }
                ],
                "recommended": [],
                "conditional": [],
                "blocked": [],
            },
            "native_subagent_bridge": {
                "protocol_version": "1.0",
                "transport": "kimi-native-subagents",
                "primary": {"native_agent_type": "default"},
                "secondary": [{"native_agent_type": "worker"}],
                "reviewer": {"native_agent_type": "explorer"},
            },
            "routing_rationale": {"source": "canonical_only"},
        }

    monkeypatch.setattr(
        "scripts.orchestration.task_bootstrap.build_task_packet",
        _fake_build_task_packet,
    )

    exit_code = main(
        [
            "--goal",
            "Use Kimi bridge transport",
            "--task-class",
            "Orchestration",
            "--native-bridge-transport",
            "kimi-native-subagents",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert observed["native_bridge_transport"] == "kimi-native-subagents"
    assert json.loads(captured.out)["task_packet_id"] == "bridge-transport-packet"


def test_build_task_packet_defaults_native_bridge_transport_to_codex() -> None:
    """Direct packet builder calls should preserve Codex as the default transport."""

    packet = build_task_packet(
        goal="Harden orchestration bootstrap",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
    )

    assert packet["native_subagent_bridge"]["transport"] == "codex-native-subagents"


def test_build_task_packet_passes_explicit_kimi_native_bridge_transport() -> None:
    """Direct packet builder calls should propagate explicit Kimi transport."""

    packet = build_task_packet(
        goal="Harden orchestration bootstrap",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        native_bridge_transport="kimi-native-subagents",
    )

    assert packet["native_subagent_bridge"]["transport"] == "kimi-native-subagents"


def test_build_task_packet_rejects_unknown_native_bridge_transport() -> None:
    """Direct packet builder calls must reject unsupported transport labels."""

    with pytest.raises(ValueError, match="Unsupported native_bridge_transport"):
        build_task_packet(
            goal="Harden orchestration bootstrap",
            task_class="Orchestration",
            candidate_paths=["scripts/orchestration/task_bootstrap.py"],
            native_bridge_transport="unknown-native-subagents",
        )


def test_main_passes_design_lane_flags(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should propagate additive design-lane arguments into the packet builder."""

    observed: dict[str, object] = {}

    def _fake_build_task_packet(**kwargs: object) -> dict[str, object]:
        observed.update(kwargs)
        return {
            "schema_version": "2.0",
            "task_packet_id": "design-packet",
            "goal": "Use explicit design packet",
            "task_class": "Frontend",
            "domain": "frontend",
            "cluster": "product",
            "candidate_paths": ["frontend/src/components/Hero.tsx"],
            "primary_agent": "agent-coordinator",
            "secondary_agents": [],
            "reviewer": "architecture-specialist",
            "requested_agents": [],
            "requested_agent_disposition": [],
            "required_context": ["AGENTS.md"],
            "recommended_skills": ["pulseplate-workflow"],
            "skill_routing": {
                "policy_version": "2026-03-27",
                "selection_mode": "deterministic-weighted",
                "requested_agents": [],
                "task_classification": {
                    "label": "design",
                    "score": 1,
                    "reasons": ["explicit-design-source:figma_design(+packet)"],
                },
                "required": [
                    {
                        "skill": "pulseplate-workflow",
                        "rationale": "Mandatory entry skill for all PulsePlate tasks.",
                        "reasons": ["always-on"],
                    }
                ],
                "recommended": [],
                "conditional": [],
                "blocked": [],
            },
            "automation_flags": {
                "coordinator_first_required": True,
                "skill_routing_applied": True,
                "native_subagent_bridge_available": True,
                "security_review_required": False,
                "judgment_lane_enabled": False,
                "pr_lifecycle_enabled": False,
                "design_lane_enabled": True,
            },
            "pr_phase": "none",
            "pr_lifecycle_contract": {
                "requires_pr": False,
                "post_open_review_required": False,
                "review_lane": [],
                "artifact_template": "",
                "current_head_required": False,
                "current_head_truth": "not-applicable",
                "merge_readiness_entrypoint": "",
            },
            "design_lane_mode": "implement",
            "design_lane_contract": {
                "design_source": "figma_design",
                "source_url": "",
                "file_key_or_workspace": "",
                "node_id_or_frame_id": "",
                "target_surface": "web.hero",
                "task_mode": "implement",
                "figma_lane_tool": "figma_native",
                "blockers": [],
                "code_native_design_brief_required": True,
                "code_native_design_brief_path": "docs/design/HERO_BRIEF.md",
                "explicit_creation_mode": True,
            },
            "needs_backlog_update": False,
            "needs_docs_sync": False,
            "needs_agents_sync": False,
            "decision_contract": {
                "mode": "standard",
                "judgment_enabled": False,
                "claim_taxonomy": [],
                "flow": [],
            },
            "judgment_budget": {
                "skeptic_pass_required": False,
                "verifier_pass_required": False,
                "max_provider_calls": 0,
                "uncertainty_split_required": False,
            },
            "result_adjudication": {
                "claim_evidence_fields": [],
                "support_statuses": [],
                "evidence_modes": [],
                "uncertainty_fields": [],
                "promotion_labels": [],
            },
            "native_subagent_bridge": {
                "protocol_version": "1.0",
                "transport": "codex-native-subagents",
                "primary": {"native_agent_type": "default"},
                "secondary": [],
                "reviewer": {"native_agent_type": "explorer"},
            },
            "routing_rationale": {"source": "canonical_only"},
        }

    monkeypatch.setattr(
        "scripts.orchestration.task_bootstrap.build_task_packet",
        _fake_build_task_packet,
    )

    exit_code = main(
        [
            "--goal",
            "Run design activation packet",
            "--task-class",
            "Frontend",
            "--design-source",
            "figma_design",
            "--target-surface",
            "web.hero",
            "--task-mode",
            "implement",
            "--figma-lane-tool",
            "figma_native",
            "--code-native-design-brief-path",
            "docs/design/HERO_BRIEF.md",
            "--explicit-creation-mode",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert observed["design_source"] == "figma_design"
    assert observed["target_surface"] == "web.hero"
    assert observed["task_mode"] == "implement"
    assert observed["figma_lane_tool"] == "figma_native"
    assert observed["code_native_design_brief_path"] == "docs/design/HERO_BRIEF.md"
    assert observed["explicit_creation_mode"] is True
    assert json.loads(captured.out)["task_packet_id"] == "design-packet"


def _disposition_map(packet: dict[str, object]) -> dict[str, dict[str, str]]:
    """Map agent slug -> disposition row for requested-agent assertions."""

    rows = packet["requested_agent_disposition"]
    assert isinstance(rows, list)
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        assert isinstance(row, dict)
        agent = str(row["agent"])
        out[agent] = {str(k): str(v) for k, v in row.items()}
    return out


def test_build_task_packet_rejects_unknown_requested_agent() -> None:
    """Unknown slugs must record rejected_unknown with explicit rationale."""

    packet = build_task_packet(
        goal="Orchestration hygiene",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["totally-unknown-agent-slug-xyz"],
    )
    dm = _disposition_map(packet)
    assert dm["totally-unknown-agent-slug-xyz"]["status"] == REQUESTED_AGENT_STATUS_REJECTED_UNKNOWN
    assert "not registered" in dm["totally-unknown-agent-slug-xyz"]["reason"].lower()
    assert "totally-unknown-agent-slug-xyz" not in packet["secondary_agents"]


def test_build_task_packet_non_routable_requested_agent_stays_advisory() -> None:
    """Non-routable specialists outside domain slots stay required advisory passes."""

    packet = build_task_packet(
        goal="Harden task bootstrap",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["ml-engineer-agent"],
    )
    dm = _disposition_map(packet)
    assert dm["ml-engineer-agent"]["status"] == REQUESTED_AGENT_STATUS_ADVISORY_NON_ROUTABLE
    assert "non-routable" in dm["ml-engineer-agent"]["reason"].lower()
    assert "ml-engineer-agent" in packet["secondary_agents"]
    secondary_slugs = {b["repo_agent_slug"] for b in packet["native_subagent_bridge"]["secondary"]}
    assert "ml-engineer-agent" not in secondary_slugs
    advisory_slugs = {b["repo_agent_slug"] for b in packet["native_subagent_bridge"]["advisory"]}
    assert "ml-engineer-agent" in advisory_slugs
    advisory_binding = packet["native_subagent_bridge"]["advisory"][0]
    assert advisory_binding["execution_mode"] == "advisory_review"
    assert advisory_binding["dispatch_contract"]["spawn_with_native_subagent"] is True
    assert advisory_binding["dispatch_contract"]["required_role_pass"] is True


def test_build_task_packet_promotes_requested_agent_in_domain_slot_set() -> None:
    """Requested agent listed in graph primary/secondary/reviewer may be promoted."""

    packet = build_task_packet(
        goal="Tune retrieval quality",
        task_class="AI / ML",
        candidate_paths=["core/ai/insight_runtime.py"],
        requested_agents=["rag-systems-agent"],
    )
    assert packet["domain"] == "ml"
    dm = _disposition_map(packet)
    assert dm["rag-systems-agent"]["status"] == REQUESTED_AGENT_STATUS_PROMOTED
    assert packet["primary_agent"] == "rag-systems-agent"
    assert "ai-innovation-specialist" in packet["secondary_agents"]


def test_build_task_packet_routable_agent_domain_mismatch_stays_advisory() -> None:
    """Routable agent outside routed domain slots becomes a required advisory pass."""

    packet = build_task_packet(
        goal="Docs routing only",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["backend-engineer"],
    )
    dm = _disposition_map(packet)
    assert dm["backend-engineer"]["status"] == REQUESTED_AGENT_STATUS_ADVISORY_DOMAIN_MISMATCH
    assert "slot" in dm["backend-engineer"]["reason"].lower()
    assert packet["primary_agent"] == "agent-coordinator"
    advisory_binding = packet["native_subagent_bridge"]["advisory"][0]
    assert advisory_binding["repo_agent_slug"] == "backend-engineer"
    assert advisory_binding["execution_mode"] == "advisory_review"
    assert advisory_binding["dispatch_contract"]["spawn_with_native_subagent"] is True
    assert advisory_binding["dispatch_contract"]["required_role_pass"] is True


def test_build_task_packet_graph_slot_precedes_non_routable_specialist_list() -> None:
    """Specialists listed as non-routable but present on graph slots are promoted, not advisory."""

    packet = build_task_packet(
        goal="Refine CV metrics export",
        task_class="Computer Vision",
        candidate_paths=["README.md"],
        requested_agents=["data-scientist-agent"],
    )
    assert packet["domain"] == "cv"
    dm = _disposition_map(packet)
    assert dm["data-scientist-agent"]["status"] == REQUESTED_AGENT_STATUS_PROMOTED
    assert packet["primary_agent"] == "data-scientist-agent"
    assert "cv-agent" in packet["secondary_agents"]


def test_build_task_packet_honored_primary_when_requested_matches_routed_primary() -> None:
    """Explicit request for the default primary must record honored_primary."""

    packet = build_task_packet(
        goal="Coordinator bootstrap",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["agent-coordinator"],
    )
    dm = _disposition_map(packet)
    assert dm["agent-coordinator"]["status"] == REQUESTED_AGENT_STATUS_HONORED_PRIMARY
    assert packet["primary_agent"] == "agent-coordinator"
