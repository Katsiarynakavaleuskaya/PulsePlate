"""Tests for deterministic coordinator task bootstrap packets."""

from __future__ import annotations

import json
from pathlib import Path

from core.judgment import (
    CLAIM_EVIDENCE_FIELDS,
    CLAIM_TYPES,
    EVIDENCE_MODES,
    JUDGMENT_FLOW,
    PROMOTION_LABELS,
    SUPPORT_STATUSES,
    UNCERTAINTY_FIELDS,
)
from scripts.orchestration.context_pack import REPO_ROOT, normalize_repo_path
from scripts.orchestration.task_bootstrap import (
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
        "max_provider_calls": 1,
        "uncertainty_split_required": True,
    }
    assert packet["result_adjudication"]["claim_evidence_fields"] == list(CLAIM_EVIDENCE_FIELDS)
    assert packet["result_adjudication"]["support_statuses"] == list(SUPPORT_STATUSES)
    assert packet["result_adjudication"]["evidence_modes"] == list(EVIDENCE_MODES)
    assert packet["result_adjudication"]["uncertainty_fields"] == list(UNCERTAINTY_FIELDS)
    assert packet["result_adjudication"]["promotion_labels"] == list(PROMOTION_LABELS)


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
    """Non-routable specialists should be preserved as advisory collaborators."""

    packet = build_task_packet(
        goal="Design AI reliability experiment packet",
        task_class="AI / ML",
        candidate_paths=["docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md"],
        requested_agents=["ml-engineer-agent"],
    )

    assert packet["domain"] == "ml"
    assert packet["primary_agent"] == "ai-innovation-specialist"
    assert "ml-engineer-agent" in packet["secondary_agents"]
    assert [
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["secondary"]
    ] == ["rag-systems-agent"]
    assert [
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["advisory"]
    ] == ["ml-engineer-agent"]
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "ml-engineer-agent",
            "status": "advisory_non_routable",
            "reason": "Agent is canonical but non-routable; kept as an advisory collaborator.",
        }
    ]


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
    assert "security-auditor" in {
        packet["native_subagent_bridge"]["reviewer"]["repo_agent_slug"],
        *[binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["secondary"]],
    }
    assert "security-auditor" not in {
        binding["repo_agent_slug"] for binding in packet["native_subagent_bridge"]["advisory"]
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


def test_task_bootstrap_updates_honored_primary_after_later_promotion() -> None:
    """Earlier honored-primary dispositions must stay aligned with final routing."""

    packet = build_task_packet(
        goal="Update privileged orchestration workflow",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=["agent-coordinator", "architecture-specialist"],
    )

    assert packet["primary_agent"] == "architecture-specialist"
    assert "agent-coordinator" in packet["secondary_agents"]
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "agent-coordinator",
            "status": "honored_secondary",
            "reason": "Requested agent stayed honored but moved to secondary after a later promotion.",
        },
        {
            "agent": "architecture-specialist",
            "status": "promoted_requested_agent",
            "reason": "Requested agent is compatible with the routed domain and was promoted.",
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


def test_main_writes_relative_output_inside_repo(tmp_path, monkeypatch, capsys) -> None:
    """CLI should write relative --output under repo root and report repo-relative path."""

    relative_output = Path("tmp/task-packet.json")
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
            "policy_version": "2026-03-08",
            "selection_mode": "deterministic-weighted",
            "requested_agents": [],
            "recommended": [{"skill": "pulseplate-workflow", "score": 100}],
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

    relative_output = Path("task-packet-root.json")
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
            "policy_version": "2026-03-08",
            "selection_mode": "deterministic-weighted",
            "requested_agents": [],
            "recommended": [{"skill": "pulseplate-workflow", "score": 100}],
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
                "policy_version": "2026-03-08",
                "selection_mode": "deterministic-weighted",
                "requested_agents": ["agent-coordinator", "security-auditor"],
                "recommended": [{"skill": "pulseplate-workflow", "score": 100}],
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
