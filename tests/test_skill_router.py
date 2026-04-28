"""Tests for deterministic skill routing."""

from __future__ import annotations

from pathlib import Path
import pytest
import scripts.orchestration.skill_router as skill_router_module

from scripts.orchestration.bootstrap_sync_policy import DOCS_ONLY_ENVELOPE_MODE
from scripts.orchestration.skill_router import (
    CLASSIFICATION_PRECEDENCE,
    DOCS_ONLY_EXCLUDED_ROUTING_SKILLS,
    PRIVILEGED_SURFACE_PREFIXES,
    RESEARCH_POLICY_BUCKET_APPROVED,
    RESEARCH_POLICY_BUCKET_DISALLOWED,
    REQUESTED_AGENT_COMPANION_SKILL_BUNDLES,
    REQUESTED_AGENT_SKILL_BUNDLES,
    ROUTING_POLICY_VERSION,
    TASK_CLASSIFICATION_RULES,
    TIER4_DOC_PREFIX,
    _match_path_prefixes,
    flatten_recommended_skills,
    route_skills,
    select_recommended_skills,
)

POLICY_DOC_PATH = (
    Path(__file__).resolve().parents[1] / "docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md"
)
MESSAGE_PROTOCOL_DOC_PATH = (
    Path(__file__).resolve().parents[1] / "docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"
)

EXPECTED_REQUESTED_AGENT_POLICY_ROWS: tuple[str, ...] = (
    "| `agent-coordinator` | `docs-sync`, `agents-md`, `pulseplate-gates` |",
    "| `bug-hunter` | `bug-triage`, `pulseplate-gates`, `pulseplate-guards` |",
    "| `security-auditor` | Auto-routed: `security-best-practices`, `security-threat-model`, `pulseplate-guards`; companion/manual-only: `cybersecurity-skills` (~734 skills, approximate; see `tools/cybersecurity_skills/index.json`) |",
    "| `backend-engineer` | `pulseplate-backend-endpoints`, `pulseplate-openapi-sync`, `pulseplate-gates` |",
    "| `qa-engineer-agent` | `bug-triage`, `pulseplate-gates`, `code-review-expert` |",
    "| `frontend-engineer` | `pulseplate-frontend-ui`, `pulseplate-gates`, `vercel-react-best-practices` |",
    "| `ml-engineer-agent` | `pulseplate-gates`, `docs-sync`, `openai-docs` |",
    "| `data-scientist-agent` | `docs-sync`, `pulseplate-gates`, `pulseplate-ai-reports` |",
    "| `web-research-agent` | `docs-sync`, `pulseplate-ai-reports`, `notion-research-documentation` |",
)
EXPECTED_REQUESTED_AGENT_NAMES: frozenset[str] = frozenset(
    row.split("`")[1] for row in EXPECTED_REQUESTED_AGENT_POLICY_ROWS
)

EXPECTED_PRIVILEGED_SURFACE_POLICY_LINES: tuple[str, ...] = (
    "- `.github/workflows/**`",
    "- `ios/fastlane/**`",
    "- `scripts/orchestration/**`",
    "- merge-governance scripts under `scripts/ci/**`",
    "- merge-governance docs under `docs/orchestration/**` and `docs/review/**`",
)
EXPECTED_CLASSIFICATION_POLICY_LINES: tuple[str, ...] = (
    "- `implementation`",
    "- `bugfix`",
    "- `review`",
    "- `design`",
    "- `creative_research`",
    "- `experiment`",
    "- `pr_governance`",
)
EXPECTED_ROUTING_BUCKET_POLICY_LINES: tuple[str, ...] = (
    "- `required`: non-optional skills for the classified lane. `pulseplate-workflow`",
    "- `recommended`: deterministic ranked helpers that are safe to auto-promote into",
    "- `conditional`: task-fit helpers that need a stronger trigger before promotion.",
    "- `blocked`: deterministic low-fit or disallowed patterns. Pattern-based blocks",
    "- `explanation`: stable schema describing evidence axes, matched semantic groups,",
    "- `research_connector_policy`: explicit catalog of approved / conditional /",
)


def _read_policy_doc() -> str:
    """Load the canonical policy markdown for doc-to-implementation parity checks."""

    return POLICY_DOC_PATH.read_text(encoding="utf-8")


def _read_message_protocol_doc() -> str:
    """Load the canonical message protocol markdown."""

    return MESSAGE_PROTOCOL_DOC_PATH.read_text(encoding="utf-8")


def test_skill_router_prefers_orchestration_docs_skills() -> None:
    """Orchestration work should auto-select policy and doc maintenance skills."""

    decision = route_skills(
        goal="Wire skill routing into agent orchestration and update AGENTS guidance",
        task_class="Orchestration",
        candidate_paths=[
            "docs/orchestration/workflow.md",
            ".cursor/agents/agent-coordinator.md",
            "scripts/orchestration/task_bootstrap.py",
        ],
        domain="orchestration",
    )

    required_skills = [item["skill"] for item in decision["required"]]
    skills = flatten_recommended_skills(decision)
    assert decision["policy_version"] == ROUTING_POLICY_VERSION
    assert decision["selection_mode"] == "deterministic-weighted"
    assert decision["task_classification"]["label"] == "implementation"
    assert required_skills == ["pulseplate-workflow"]
    assert skills[0] == "pulseplate-workflow"
    assert "docs-sync" in skills
    assert "agents-md" in skills
    assert "pulseplate-gates" in skills
    assert "pulseplate-guards" in skills


def test_skill_router_applies_requested_agent_default_bundle() -> None:
    """Requested agents should boost their documented default helper bundles."""

    skills = select_recommended_skills(
        goal="Refine frontend settings page",
        task_class="Frontend",
        candidate_paths=["frontend/src/pages/Settings.tsx"],
        domain="frontend",
        requested_agents=["frontend-engineer"],
    )

    assert "pulseplate-frontend-ui" in skills
    assert "pulseplate-gates" in skills
    assert "vercel-react-best-practices" in skills


@pytest.mark.parametrize(
    ("goal", "task_class", "candidate_paths", "domain", "expected_label"),
    (
        (
            "Implement backend endpoint contract for nutrition insights",
            "Backend API",
            ["app/routers/insight.py"],
            "backend",
            "implementation",
        ),
        (
            "Fix flaky regression in frontend dashboard chart",
            "Frontend",
            ["frontend/src/pages/Dashboard.tsx", "tests/test_dashboard.py"],
            "frontend",
            "bugfix",
        ),
        (
            "Perform code review for this frontend change",
            "Frontend",
            ["frontend/src/App.tsx"],
            "frontend",
            "review",
        ),
        (
            "Implement design fidelity from Figma node-id 42-7",
            "Frontend",
            ["frontend/src/components/Hero.tsx"],
            "frontend",
            "design",
        ),
        (
            "Prepare weekly wellness AI trend report and GTM brief",
            "Research",
            ["docs/audience_pack/ENGINEERING_OVERVIEW.md"],
            "research",
            "creative_research",
        ),
        (
            "Run benchmark eval for RAG reliability optimization",
            "Experimentation",
            ["core/rag/vector_rag.py"],
            "ml",
            "experiment",
        ),
        (
            "Update merge readiness review thread mapping for the pull request",
            "QA",
            ["docs/review/PR_999_FIXED_MAPPING.md"],
            "qa",
            "pr_governance",
        ),
    ),
)
def test_task_classifier_supports_all_canonical_labels(
    goal: str,
    task_class: str,
    candidate_paths: list[str],
    domain: str,
    expected_label: str,
) -> None:
    """Classifier should deterministically cover the canonical label set."""

    decision = route_skills(
        goal=goal,
        task_class=task_class,
        candidate_paths=candidate_paths,
        domain=domain,
    )

    assert decision["task_classification"]["label"] == expected_label
    assert isinstance(decision["task_classification"]["score"], int)
    assert decision["task_classification"]["reasons"]


def test_task_classifier_uses_documented_precedence_order() -> None:
    """Classifier precedence list should remain explicit and stable."""

    assert CLASSIFICATION_PRECEDENCE == (
        "pr_governance",
        "design",
        "creative_research",
        "experiment",
        "review",
        "bugfix",
        "implementation",
    )


def test_task_classifier_rule_labels_match_precedence_contract() -> None:
    """Rule labels should stay in lockstep with the precedence contract."""

    rule_labels = tuple(rule.label for rule in TASK_CLASSIFICATION_RULES)

    assert len(rule_labels) == len(set(rule_labels))
    assert set(rule_labels) == set(CLASSIFICATION_PRECEDENCE)


def test_task_classifier_skips_unknown_precedence_labels_without_key_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown precedence labels should not crash the classifier during routing."""

    monkeypatch.setattr(
        skill_router_module,
        "CLASSIFICATION_PRECEDENCE",
        ("unknown_lane", *CLASSIFICATION_PRECEDENCE),
    )

    decision = route_skills(
        goal="Implement backend endpoint contract for nutrition insights",
        task_class="Backend API",
        candidate_paths=["app/routers/insight.py"],
        domain="backend",
    )

    assert decision["task_classification"]["label"] == "implementation"


def test_task_classifier_prioritizes_pr_governance_over_review() -> None:
    """PR governance should win when review-thread and merge signals are both present."""

    decision = route_skills(
        goal="Address review thread mapping before merge readiness pass",
        task_class="QA",
        candidate_paths=["docs/review/PR_999_FIXED_MAPPING.md"],
        domain="qa",
    )

    assert decision["task_classification"]["label"] == "pr_governance"


def test_task_classifier_prioritizes_pr_governance_for_docs_review_updates() -> None:
    """Docs-review mapping updates should stay in the PR-governance lane."""

    decision = route_skills(
        goal="Update fixed mapping notes",
        task_class="Documentation",
        candidate_paths=["docs/review/PR_999_FIXED_MAPPING.md"],
        domain="docs",
    )

    assert decision["task_classification"]["label"] == "pr_governance"
    assert [item["skill"] for item in decision["required"]] == [
        "pulseplate-workflow",
        "docs-sync",
        "pulseplate-gates",
    ]


def test_task_classifier_prioritizes_design_over_implementation() -> None:
    """Design signals should override generic implementation wording."""

    decision = route_skills(
        goal="Implement Figma node-id fidelity for the dashboard hero",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        domain="frontend",
    )

    assert decision["task_classification"]["label"] == "design"


def test_task_classifier_prioritizes_experiment_over_implementation() -> None:
    """Experiment signals should override generic implementation wording."""

    decision = route_skills(
        goal="Implement benchmark eval harness for reliability optimization",
        task_class="Experimentation",
        candidate_paths=["core/rag/vector_rag.py"],
        domain="ml",
    )

    assert decision["task_classification"]["label"] == "experiment"


def test_task_classifier_requires_review_signals_to_dominate_bugfix() -> None:
    """Review should only beat bugfix when review evidence is stronger."""

    review_dominant = route_skills(
        goal="Review bugfix comments and code review disposition",
        task_class="QA",
        candidate_paths=["docs/review/PR_999_FIXED_MAPPING.md"],
        domain="qa",
    )
    bugfix_dominant = route_skills(
        goal="Fix failing flaky regression in the dashboard chart",
        task_class="Frontend",
        candidate_paths=["frontend/src/pages/Dashboard.tsx", "tests/test_dashboard.py"],
        domain="frontend",
    )

    assert review_dominant["task_classification"]["label"] == "review"
    assert bugfix_dominant["task_classification"]["label"] == "bugfix"


@pytest.mark.parametrize(
    ("requested_agent", "expected_bundle"),
    sorted(REQUESTED_AGENT_SKILL_BUNDLES.items()),
)
def test_requested_agent_bundle_parity_is_covered(
    requested_agent: str,
    expected_bundle: tuple[str, ...],
) -> None:
    """Every documented requested-agent bundle should appear in required or recommended lanes."""

    decision = route_skills(
        goal="Need deterministic agent bundle parity coverage",
        task_class="Orchestration",
        candidate_paths=["docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md"],
        domain="orchestration",
        requested_agents=[requested_agent],
    )

    required_by_skill = {item["skill"]: item for item in decision["required"]}
    recommended_by_skill = {item["skill"]: item for item in decision["recommended"]}
    routed_skill_names = set(required_by_skill) | set(recommended_by_skill)

    assert decision["requested_agents"] == [requested_agent]
    for skill in expected_bundle:
        assert skill in routed_skill_names
        if skill in recommended_by_skill:
            assert any(
                reason.startswith(f"requested-agent:{requested_agent}(+")
                for reason in recommended_by_skill[skill]["reasons"]
            )
        else:
            assert skill in required_by_skill


def test_requested_agent_companion_guidance_stays_manual_only() -> None:
    """Companion/manual-only skills must not leak into deterministic recommendations."""

    decision = route_skills(
        goal="Review privileged orchestration update",
        task_class="Security",
        candidate_paths=["scripts/orchestration/skill_router.py"],
        domain="security",
        requested_agents=["security-auditor"],
    )

    recommended_skills = {item["skill"] for item in decision["recommended"]}
    assert recommended_skills.issuperset(REQUESTED_AGENT_SKILL_BUNDLES["security-auditor"])
    assert not recommended_skills.intersection(
        REQUESTED_AGENT_COMPANION_SKILL_BUNDLES["security-auditor"]
    )


def test_required_lane_always_contains_pulseplate_workflow() -> None:
    """Every routed task must keep pulseplate-workflow in required lane metadata."""

    decision = route_skills(
        goal="Implement backend endpoint contract for nutrition insights",
        task_class="Backend API",
        candidate_paths=["app/routers/insight.py"],
        domain="backend",
    )

    assert [item["skill"] for item in decision["required"]] == ["pulseplate-workflow"]


def test_pr_governance_required_lane_adds_governance_baseline() -> None:
    """PR-governance tasks should require the minimal governance baseline."""

    decision = route_skills(
        goal="Prepare pull request merge readiness and fixed mapping governance pass",
        task_class="QA",
        candidate_paths=["docs/review/PR_999_FIXED_MAPPING.md"],
        domain="qa",
    )

    assert [item["skill"] for item in decision["required"]] == [
        "pulseplate-workflow",
        "docs-sync",
        "pulseplate-gates",
    ]
    assert flatten_recommended_skills(decision)[:3] == [
        "pulseplate-workflow",
        "docs-sync",
        "pulseplate-gates",
    ]


def test_pr_governance_requested_agent_bundle_keeps_required_skills_out_of_recommended() -> None:
    """Requested-agent boosts must not duplicate required governance skills."""

    decision = route_skills(
        goal="Prepare pull request merge readiness and fixed mapping governance pass",
        task_class="QA",
        candidate_paths=["docs/review/PR_999_FIXED_MAPPING.md"],
        domain="qa",
        requested_agents=["agent-coordinator"],
    )

    required_skill_names = {item["skill"] for item in decision["required"]}
    recommended_skill_names = {item["skill"] for item in decision["recommended"]}

    assert required_skill_names == {
        "pulseplate-workflow",
        "docs-sync",
        "pulseplate-gates",
    }
    assert "agents-md" in recommended_skill_names
    assert required_skill_names.isdisjoint(recommended_skill_names)


@pytest.mark.parametrize("expected_row", EXPECTED_REQUESTED_AGENT_POLICY_ROWS)
def test_requested_agent_policy_rows_stay_in_sync(expected_row: str) -> None:
    """Canonical policy rows should stay explicit so router parity tests have a stable contract."""

    assert expected_row in _read_policy_doc()


def test_requested_agent_policy_agent_set_stays_in_sync() -> None:
    """Documented requested-agent names should match the implementation exactly."""

    assert EXPECTED_REQUESTED_AGENT_NAMES == frozenset(REQUESTED_AGENT_SKILL_BUNDLES.keys())


@pytest.mark.parametrize("expected_line", EXPECTED_CLASSIFICATION_POLICY_LINES)
def test_classification_policy_lines_stay_in_sync(expected_line: str) -> None:
    """Canonical classifier labels must remain locked between docs and implementation."""

    assert expected_line in _read_policy_doc()


@pytest.mark.parametrize("expected_line", EXPECTED_ROUTING_BUCKET_POLICY_LINES)
def test_routing_bucket_policy_lines_stay_in_sync(expected_line: str) -> None:
    """Routing bucket semantics must remain explicit in the policy doc."""

    assert expected_line in _read_policy_doc()


def test_message_protocol_example_mentions_expanded_skill_routing_contract() -> None:
    """Message protocol should document the nested skill_routing fields."""

    doc = _read_message_protocol_doc()
    assert '"task_classification": {' in doc
    assert "envelope_mode_hint" in doc
    assert '"required": [' in doc
    assert '"recommended": [' in doc
    assert '"conditional": [' in doc
    assert '"explanation": {' in doc
    assert '"research_connector_policy": {' in doc


def test_requested_agent_bundle_boosts_existing_skill_without_duplication() -> None:
    """Requested bundles should boost existing skills without duplicating entries."""

    baseline = route_skills(
        goal="Open PR for the frontend settings page review",
        task_class="Frontend",
        candidate_paths=["frontend/src/pages/Settings.tsx"],
        domain="frontend",
    )
    with_requested = route_skills(
        goal="Open PR for the frontend settings page review",
        task_class="Frontend",
        candidate_paths=["frontend/src/pages/Settings.tsx"],
        domain="frontend",
        requested_agents=["frontend-engineer"],
    )

    baseline_skill = next(
        item for item in baseline["recommended"] if item["skill"] == "pulseplate-gates"
    )
    requested_skill = next(
        item for item in with_requested["recommended"] if item["skill"] == "pulseplate-gates"
    )

    assert (
        len([item for item in with_requested["recommended"] if item["skill"] == "pulseplate-gates"])
        == 1
    )
    assert requested_skill["score"] == baseline_skill["score"] + 2
    assert "requested-agent:frontend-engineer(+2)" in requested_skill["reasons"]


def test_route_skills_echoes_normalized_requested_agents() -> None:
    """Router output should echo requested agents in normalized deduplicated form."""

    decision = route_skills(
        goal="Refine frontend settings page",
        task_class="Frontend",
        candidate_paths=["frontend/src/pages/Settings.tsx"],
        domain="frontend",
        requested_agents=[
            "frontend-engineer",
            "Frontend-Engineer",
            "   FRONTEND-ENGINEER  ",
            "backend-engineer",
            "BACKEND-ENGINEER",
        ],
    )

    assert decision["requested_agents"] == ["frontend-engineer", "backend-engineer"]


def test_requested_agent_duplicates_do_not_stack_bundle_boosts() -> None:
    """Duplicate requested agents should not apply extra bundle boosts."""

    single_requested = route_skills(
        goal="Open PR for the frontend settings page review",
        task_class="Frontend",
        candidate_paths=["frontend/src/pages/Settings.tsx"],
        domain="frontend",
        requested_agents=["frontend-engineer"],
    )
    duplicate_requested = route_skills(
        goal="Open PR for the frontend settings page review",
        task_class="Frontend",
        candidate_paths=["frontend/src/pages/Settings.tsx"],
        domain="frontend",
        requested_agents=["frontend-engineer", "Frontend-Engineer", " frontend-engineer "],
    )

    single_skill = next(
        item for item in single_requested["recommended"] if item["skill"] == "pulseplate-gates"
    )
    duplicate_skill = next(
        item for item in duplicate_requested["recommended"] if item["skill"] == "pulseplate-gates"
    )

    assert duplicate_requested["requested_agents"] == ["frontend-engineer"]
    assert duplicate_skill["score"] == single_skill["score"]
    assert duplicate_skill["reasons"].count("requested-agent:frontend-engineer(+2)") == 1


def test_skill_router_selects_backend_contract_skills() -> None:
    """Backend contract changes should pull endpoint and OpenAPI skills."""

    skills = select_recommended_skills(
        goal="Add backend endpoint and regenerate OpenAPI client types",
        task_class="Backend API",
        candidate_paths=[
            "app/routers/example.py",
            "frontend/src/api/schema.ts",
        ],
        domain="backend",
    )

    assert "pulseplate-backend-endpoints" in skills
    assert "pulseplate-openapi-sync" in skills
    assert "pulseplate-gates" in skills


def test_skill_router_selects_openai_docs_for_backend_ai_contracts() -> None:
    """Backend AI/runtime work should be able to reach OpenAI docs guidance."""

    skills = select_recommended_skills(
        goal="Update OpenAI assistant contract for backend LLM endpoint",
        task_class="Backend API",
        candidate_paths=["app/routers/insight.py"],
        domain="backend",
    )

    assert "openai-docs" in skills


def test_skill_router_matches_punctuated_keywords_after_normalization() -> None:
    """Punctuated lexemes should survive normalization and still route skills."""

    skills = select_recommended_skills(
        goal="Refresh AGENTS.md guidance and regenerate schema.ts after a Figma node-id review",
        task_class="Orchestration",
        candidate_paths=[
            ".cursor/agents/agent-coordinator.md",
            "frontend/src/api/schema.ts",
        ],
        domain="orchestration",
    )

    assert "agents-md" in skills
    assert "pulseplate-openapi-sync" in skills


def test_skill_router_does_not_match_partial_keyword_substrings() -> None:
    """Short lexemes should not match inside unrelated larger words."""

    decision = route_skills(
        goal="Document docker entrypoint behavior for onboarding",
        task_class="Docs",
        candidate_paths=["README.md"],
        domain="docs",
    )

    docs_sync = next(item for item in decision["recommended"] if item["skill"] == "docs-sync")
    joined_reasons = " ".join(docs_sync["reasons"])
    assert "lexeme:doc(" not in joined_reasons
    assert "lexeme:doc," not in joined_reasons


def test_skill_router_selects_report_stack_for_research() -> None:
    """Research/report work should use the report pipeline instead of generic scraping."""

    skills = select_recommended_skills(
        goal="Prepare weekly wellness AI report with a Notion research note",
        task_class="Research",
        candidate_paths=[
            "docs/audience_pack/ENGINEERING_OVERVIEW.md",
        ],
        domain="research",
    )

    assert "pulseplate-ai-reports" in skills
    assert "docs-sync" in skills
    assert "notion-research-documentation" in skills


def test_skill_router_selects_web_ui_skill_stack() -> None:
    """Strong web UI/UX tasks should route the curated web skill stack."""

    skills = select_recommended_skills(
        goal="Build a launch site landing page hero section with strong UI UX and design audit coverage",
        task_class="Frontend",
        candidate_paths=["frontend/src/pages/LandingPage.tsx"],
        domain="frontend",
    )

    assert "pulseplate-frontend-ui" in skills
    assert "build-web-apps:frontend-skill" in skills
    assert "build-web-apps:web-design-guidelines" in skills


def test_skill_router_selects_web_launch_site_stack() -> None:
    """Launch-site work should route the PulsePlate launch-site helper."""

    skills = select_recommended_skills(
        goal=(
            "Build a public launch site landing page with waitlist CTA, "
            "lead capture, SEO landing copy, and Product Hunt handoff"
        ),
        task_class="Frontend",
        candidate_paths=["frontend/src/pages/LaunchSite.tsx", "docs/marketing/LAUNCH.md"],
        domain="frontend",
    )

    assert "pulseplate-web-launch-site" in skills
    assert "pulseplate-frontend-ui" in skills
    assert "build-web-apps:frontend-skill" in skills


def test_skill_router_selects_ios_app_store_skill_stack() -> None:
    """iOS and App Store work should route the dedicated SwiftUI/iOS helpers."""

    skills = select_recommended_skills(
        goal="Refactor a SwiftUI subscription screen, debug it in Simulator, and prepare App Store screenshots",
        task_class="iOS",
        candidate_paths=[
            "ios/PulsePlate/Features/Paywall/PaywallView.swift",
            "ios/fastlane/Fastfile",
        ],
        domain="release",
    )

    assert "build-ios-apps:swiftui-ui-patterns" in skills
    assert "build-ios-apps:swiftui-view-refactor" in skills
    assert "build-ios-apps:ios-debugger-agent" in skills
    assert "pulseplate-app-store-release" in skills
    assert "build-web-apps:stripe-best-practices" not in skills


def test_skill_router_selects_swiftui_refactor_for_ios_domain() -> None:
    """Pure iOS SwiftUI refactor tasks should still activate the refactor skill."""

    skills = select_recommended_skills(
        goal="Refactor a SwiftUI subscription screen",
        task_class="iOS",
        candidate_paths=["ios/PulsePlate/Features/Paywall/PaywallView.swift"],
        domain="ios",
    )

    assert "build-ios-apps:swiftui-view-refactor" in skills
    assert "pulseplate-app-store-release" not in skills


def test_skill_router_selects_ios_app_store_screenshot_lane() -> None:
    """App Store screenshot and Fastlane tasks should still route the iOS release helpers."""

    skills = select_recommended_skills(
        goal="Prepare App Store screenshots for onboarding via Fastlane screenshots",
        task_class="iOS",
        candidate_paths=["ios/fastlane/Fastfile"],
        domain="release",
    )

    assert "build-ios-apps:ios-debugger-agent" in skills
    assert "pulseplate-app-store-release" in skills


def test_skill_router_does_not_double_count_fastlane_prefixes() -> None:
    """Generic Fastlane release work should not route the debugger skill without debugger cues."""

    skills = select_recommended_skills(
        goal="Refresh Fastlane metadata and release notes for App Store submission",
        task_class="iOS",
        candidate_paths=["ios/fastlane/Fastfile"],
        domain="release",
    )

    assert "build-ios-apps:ios-debugger-agent" not in skills
    assert "pulseplate-app-store-release" in skills


def test_skill_router_selects_swiftui_performance_audit_skill() -> None:
    """SwiftUI performance audit requests should route the dedicated audit helper."""

    skills = select_recommended_skills(
        goal="Audit SwiftUI scroll performance, rendering jank, and memory spike on the paywall screen",
        task_class="iOS",
        candidate_paths=["ios/PulsePlate/Features/Paywall/PaywallView.swift"],
        domain="qa",
    )

    assert "build-ios-apps:swiftui-performance-audit" in skills


def test_skill_router_selects_design_figma_brand_stack() -> None:
    """Design fidelity and brand implementation tasks should route Figma + web design helpers."""

    skills = select_recommended_skills(
        goal="Implement Figma design fidelity for the branded hero with token and brand alignment",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        domain="frontend",
        design_source="figma_design",
        source_url="https://figma.com/design/FILEKEY/Hero?node-id=1-2",
        file_key_or_workspace="FILEKEY",
        node_id_or_frame_id="1:2",
        target_surface="frontend-hero",
        task_mode="implement",
        figma_lane_tool="figma_native",
        code_native_design_brief_path="docs/figma/briefs/frontend-hero.md",
    )

    assert "figma" in skills
    assert "figma-implement-design" in skills
    assert "build-web-apps:web-design-guidelines" in skills


def test_skill_router_selects_design_launch_system_for_explicit_launch_asset_metadata() -> None:
    """Explicit launch-asset design packets should route the dedicated governance skill."""

    skills = select_recommended_skills(
        goal="Prepare Figma launch asset bundle with token consistency and brand alignment",
        task_class="Frontend",
        candidate_paths=["tokens/10_semantic/color.json", "docs/design/UI_COMPONENT_VOCABULARY.md"],
        domain="frontend",
        design_source="figma_design",
        source_url="https://figma.com/design/FILEKEY/LaunchAssets?node-id=7-4",
        file_key_or_workspace="FILEKEY",
        node_id_or_frame_id="7:4",
        target_surface="launch-assets.hero-pack",
        task_mode="implement",
        figma_lane_tool="figma_native",
        code_native_design_brief_path="docs/design/LAUNCH_ASSET_BRIEF.md",
    )

    assert "pulseplate-design-launch-system" in skills
    assert "figma" in skills


def test_skill_router_keeps_design_launch_system_out_of_generic_figma_execution_packets() -> None:
    """Generic Figma execution packets should not auto-bundle the launch governance skill."""

    skills = select_recommended_skills(
        goal="Implement a Figma dashboard screen with high-fidelity frontend parity",
        task_class="Frontend",
        candidate_paths=[
            "frontend/src/pages/dashboard.tsx",
            "frontend/src/components/metrics-card.tsx",
        ],
        domain="frontend",
        design_source="figma_design",
        source_url="https://figma.com/design/FILEKEY/Dashboard?node-id=11-22",
        file_key_or_workspace="FILEKEY",
        node_id_or_frame_id="11:22",
        target_surface="dashboard.metrics-grid",
        task_mode="implement",
        figma_lane_tool="figma_native",
        code_native_design_brief_path="docs/figma/briefs/dashboard-screen.md",
    )

    assert "figma" in skills
    assert "figma-implement-design" in skills
    assert "pulseplate-design-launch-system" not in skills


def test_skill_router_selects_monetization_and_gtm_stack() -> None:
    """Monetization, subscriptions, and GTM tasks should route billing + report helpers."""

    skills = select_recommended_skills(
        goal="Define subscription pricing, paywall copy, billing flow, and GTM plan for monetization",
        task_class="Business",
        candidate_paths=["core/billing_policy.py", "app/services/payments_activation.py"],
        domain="business",
    )

    assert "pulseplate-monetization-gtm" in skills
    assert "build-web-apps:stripe-best-practices" in skills
    assert "pulseplate-ai-reports" in skills
    assert "docs-sync" in skills


def test_skill_router_selects_agent_product_stack() -> None:
    """Agent-product work should route the product helper without replacing workflow."""

    skills = select_recommended_skills(
        goal=(
            "Productize agent workflow into an operator console with HITL "
            "approval and native subagent bridge boundaries"
        ),
        task_class="Orchestration",
        candidate_paths=[
            "docs/orchestration/AGENT_MESSAGE_PROTOCOL.md",
            "docs/product/AGENT_PRODUCT_SURFACE.md",
        ],
        domain="orchestration",
    )

    assert "pulseplate-workflow" in skills
    assert "pulseplate-agent-product" in skills
    assert "docs-sync" in skills


def test_skill_router_keeps_monetization_skill_out_of_pure_ios_refactor_lane() -> None:
    """Pure iOS subscription-screen cleanup should not force the monetization skill."""

    skills = select_recommended_skills(
        goal="Refactor a SwiftUI subscription screen and polish the paywall animation",
        task_class="iOS",
        candidate_paths=["ios/PulsePlate/Features/Paywall/PaywallView.swift"],
        domain="ios",
    )

    assert "pulseplate-monetization-gtm" not in skills


def test_skill_router_selects_github_review_ci_pr_stack() -> None:
    """GitHub review, CI, and PR intent should route the dedicated GitHub helpers."""

    skills = select_recommended_skills(
        goal="Address GitHub review comments, fix failing PR checks, and prepare the pull request",
        task_class="QA",
        candidate_paths=["docs/review/PR_999_FIXED_MAPPING.md", ".github/workflows/ci.yml"],
        domain="qa",
    )

    assert "gh-address-comments" in skills
    assert "gh-fix-ci" in skills
    assert "create-pr" in skills


def test_task_classifier_keeps_generic_market_wellness_language_out_of_creative_research() -> None:
    """Generic wellness/market wording without a research deliverable must not trigger the lane."""

    decision = route_skills(
        goal="Document wellness market positioning notes for later UI discussion",
        task_class="Documentation",
        candidate_paths=["docs/ENGINEERING_LESSONS.md"],
        domain="docs",
    )

    assert decision["task_classification"]["label"] != "creative_research"


def test_match_path_prefixes_tier4_requires_tier4_md_basename() -> None:
    """Tier 4 packet contract is `docs/orchestration/TIER4_*.md`; other prefixes must not match."""

    prefixes = (TIER4_DOC_PREFIX,)
    assert TIER4_DOC_PREFIX in _match_path_prefixes(
        prefixes, ["docs/orchestration/TIER4_SCIENTIFIC_CREATIVE_CELL_PR0_PACKET_2026-04-27.md"]
    )
    assert TIER4_DOC_PREFIX not in _match_path_prefixes(
        prefixes, ["docs/orchestration/TIER4_BACKUP.txt"]
    )
    assert TIER4_DOC_PREFIX not in _match_path_prefixes(prefixes, ["docs/orchestration/OTHER.md"])


def test_skill_router_tier4_packet_path_classifies_creative_research() -> None:
    """Tier 4 PR0 orchestration docs must score `creative_research` (org lane, not a new label)."""

    decision = route_skills(
        goal="Land Tier 4 scientific creative cell governance packet and AGENTS lane",
        task_class="Orchestration",
        candidate_paths=[
            "docs/orchestration/TIER4_SCIENTIFIC_CREATIVE_CELL_PR0_PACKET_2026-04-27.md",
        ],
        domain="orchestration",
    )

    assert decision["task_classification"]["label"] == "creative_research"
    joined = " ".join(decision["task_classification"]["reasons"])
    assert "TIER4_" in joined


def test_skill_router_tier4_goal_lexemes_classify_creative_research() -> None:
    """Lexical Tier 4 / hypothesis cues without TIER4_* paths must still reach `creative_research` minimum."""

    decision = route_skills(
        goal="Coordinator: Tier 4 scientific cell — draft falsifiable hypothesis for wellness GTM brief",
        task_class="Orchestration",
        candidate_paths=["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"],
        domain="orchestration",
    )

    assert decision["task_classification"]["label"] == "creative_research"


def test_skill_router_selects_create_pr_for_explicit_pr_intent() -> None:
    """Explicit PR-prep tasks should cross the dedicated create-pr threshold."""

    skills = select_recommended_skills(
        goal="Open PR for the orchestration routing follow-up",
        task_class="Orchestration",
        candidate_paths=["docs/orchestration/workflow.md"],
        domain="orchestration",
    )

    assert "create-pr" in skills


def test_skill_router_matches_keywords_adjacent_to_question_mark() -> None:
    """Keyword phrases should still match when user text ends with punctuation."""

    skills = select_recommended_skills(
        goal="Open PR?",
        task_class="Orchestration",
        candidate_paths=["docs/orchestration/workflow.md"],
        domain="orchestration",
    )

    assert "create-pr" in skills


def test_skill_router_selects_release_notes_for_release_tasks() -> None:
    """Explicit release-note work should select the dedicated release skill."""

    skills = select_recommended_skills(
        goal="Generate release notes for the next wellness launch",
        task_class="Release",
        candidate_paths=["docs/dev/CODEX_SKILLS.md"],
        domain="release",
    )

    assert "release-notes" in skills


def test_skill_router_selects_explicit_review_skill_at_lower_threshold() -> None:
    """Direct code-review intent should reach both review helper skills."""

    skills = select_recommended_skills(
        goal="Need a code review for this frontend PR",
        task_class="Frontend",
        candidate_paths=["frontend/src/App.tsx"],
        domain="frontend",
    )

    assert "code-review-expert" in skills
    assert "pulseplate-pr-review" in skills


def test_skill_router_selects_ci_fix_for_explicit_ci_failure() -> None:
    """Direct CI-failure intent should reach the dedicated CI fix skill."""

    skills = select_recommended_skills(
        goal="Fix failing CI checks on this workflow run",
        task_class="QA",
        candidate_paths=[".github/workflows/test.yml"],
        domain="qa",
    )

    assert "ci-fix" in skills


def test_skill_router_selects_github_comment_skill_for_review_threads() -> None:
    """Review-thread remediation should select the dedicated GitHub comments skill."""

    skills = select_recommended_skills(
        goal="Address review comments and resolve GitHub review thread mappings",
        task_class="QA",
        candidate_paths=["docs/review/PR_999_FIXED_MAPPING.md"],
        domain="qa",
    )

    assert "gh-address-comments" in skills
    assert "pulseplate-pr-review" in skills


def test_skill_router_selects_pulseplate_pr_review_for_pr_governance() -> None:
    """PR governance lanes should recommend the repo-native PR review skill."""

    decision = route_skills(
        goal="Prepare pull request review governance and fixed mapping for merge readiness",
        task_class="PR governance",
        candidate_paths=["docs/review/PR_999_FIXED_MAPPING.md"],
        domain="qa",
    )

    skills = flatten_recommended_skills(decision)
    assert decision["task_classification"]["label"] == "pr_governance"
    assert "pulseplate-pr-review" in skills
    assert "code-review-expert" in skills


def test_skill_router_keeps_gh_fix_ci_out_of_generic_github_cli_tasks() -> None:
    """Generic gh CLI usage should not route into the CI-specific GitHub helper."""

    skills = select_recommended_skills(
        goal="Use gh issue list to inspect open product backlog issues",
        task_class="Documentation",
        candidate_paths=["docs/roadmap/BACKLOG_LEDGER.md"],
        domain="docs",
    )

    assert "gh-fix-ci" not in skills


def test_skill_router_keeps_pr_helpers_conditional_outside_pr_governance() -> None:
    """PR helper skills should stay conditional when the task is not in PR lane yet."""

    decision = route_skills(
        goal="Implement backend contract and open PR later when execution is ready",
        task_class="Backend API",
        candidate_paths=["app/routers/example.py"],
        domain="backend",
    )

    conditional_by_skill = {item["skill"]: item for item in decision["conditional"]}
    assert "create-pr" in conditional_by_skill
    assert (
        conditional_by_skill["create-pr"]["when"]
        == "Enable when the task explicitly enters PR/review/merge-governance execution."
    )
    assert "create-pr" not in [item["skill"] for item in decision["recommended"]]


def test_skill_router_keeps_design_helpers_conditional_for_partial_signals() -> None:
    """Partial design language should not force design helpers into recommended lane."""

    decision = route_skills(
        goal="Review component polish for the dashboard hero",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        domain="frontend",
    )

    assert "figma" not in [item["skill"] for item in decision["recommended"]]

    partial_design = route_skills(
        goal="Refresh screen polish before design handoff",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        domain="frontend",
    )

    conditional_by_skill = {item["skill"]: item for item in partial_design["conditional"]}
    assert "figma" in conditional_by_skill
    assert (
        conditional_by_skill["figma"]["when"]
        == "Enable when a concrete Figma/design node-id or fidelity requirement becomes explicit."
    )


def test_skill_router_keeps_design_classified_tasks_conditional_without_explicit_metadata() -> None:
    """Design-labeled tasks still need conditional helper guidance when metadata is absent."""

    decision = route_skills(
        goal="Apply figma-level design fidelity for hero",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        domain="frontend",
    )

    conditional_by_skill = {item["skill"]: item for item in decision["conditional"]}
    assert decision["task_classification"]["label"] == "design"
    assert "figma" in conditional_by_skill
    assert "figma-implement-design" in conditional_by_skill
    assert (
        conditional_by_skill["figma"]["when"]
        == "Enable when a concrete Figma/design node-id or fidelity requirement becomes explicit."
    )


def test_skill_router_keeps_design_launch_system_conditional_for_partial_launch_signals() -> None:
    """Launch-asset governance language should stay conditional until design metadata is execution-ready."""

    decision = route_skills(
        goal="Review launch asset bundle for brand consistency and token alignment",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        domain="frontend",
    )

    recommended = {item["skill"] for item in decision["recommended"]}
    conditional_by_skill = {item["skill"]: item for item in decision["conditional"]}
    assert "pulseplate-design-launch-system" not in recommended
    assert "pulseplate-design-launch-system" in conditional_by_skill


def test_skill_router_promotes_design_lane_for_explicit_design_metadata() -> None:
    """Explicit design packet metadata should upgrade design helpers into recommended lane."""

    decision = route_skills(
        goal="Refresh hero implementation",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        domain="frontend",
        design_source="figma_design",
        target_surface="web.hero",
        task_mode="implement",
        figma_lane_tool="figma_native",
        code_native_design_brief_path="docs/design/HERO_BRIEF.md",
        explicit_creation_mode=True,
    )

    assert decision["task_classification"]["label"] == "design"
    recommended = [item["skill"] for item in decision["recommended"]]
    assert "figma" in recommended
    assert "figma-implement-design" in recommended


def test_skill_router_keeps_figma_helpers_conditional_until_packet_is_execution_ready() -> None:
    """Explicit but incomplete Figma packets must fail closed into conditional helpers."""

    decision = route_skills(
        goal="Refresh hero implementation",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        domain="frontend",
        design_source="figma_design",
        target_surface="web.hero",
        task_mode="implement",
        figma_lane_tool="figma_native",
        code_native_design_brief_path="docs/design/HERO_BRIEF.md",
    )

    recommended = {item["skill"] for item in decision["recommended"]}
    conditional_by_skill = {item["skill"]: item for item in decision["conditional"]}
    assert decision["task_classification"]["label"] == "design"
    assert "figma" not in recommended
    assert "figma-implement-design" not in recommended
    assert "figma" in conditional_by_skill
    assert "figma-implement-design" in conditional_by_skill
    assert (
        conditional_by_skill["figma"]["when"]
        == "Enable when the design packet becomes execution-ready with concrete "
        "Figma source metadata, node/frame capture, and fidelity intent."
    )


def test_skill_router_keeps_figma_helpers_conditional_when_packet_has_blockers() -> None:
    """Resolved blocker state must keep execution helpers out of the recommended lane."""

    decision = route_skills(
        goal="Refresh hero implementation",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        domain="frontend",
        design_source="figma_design",
        target_surface="web.hero",
        task_mode="implement",
        figma_lane_tool="figma_native",
        code_native_design_brief_path="docs/design/HERO_BRIEF.md",
        explicit_creation_mode=True,
        design_lane_mode="implement",
        design_blockers=("blocked_by_plan",),
    )

    recommended = {item["skill"] for item in decision["recommended"]}
    conditional_by_skill = {item["skill"] for item in decision["conditional"]}
    assert "figma" not in recommended
    assert "figma-implement-design" not in recommended
    assert "figma" in conditional_by_skill
    assert "figma-implement-design" in conditional_by_skill


def test_skill_router_keeps_non_figma_reference_sources_out_of_figma_execution_bundle() -> None:
    """Read-only external design sources must not auto-promote Figma execution skills."""

    decision = route_skills(
        goal="Sync read-only reference notes for the hero",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        domain="frontend",
        design_source="notion",
        source_url="https://www.notion.so/workspace/hero-reference",
        target_surface="web.hero",
        task_mode="read_only",
    )

    recommended = {item["skill"] for item in decision["recommended"]}
    assert decision["task_classification"]["label"] == "design"
    assert "figma" not in recommended
    assert "figma-implement-design" not in recommended


def test_skill_router_applies_triage_bundle_without_figma_activation() -> None:
    """Review lanes must keep triage helpers even without Figma promotion."""

    decision = route_skills(
        goal="Review hero patch",
        task_class="Frontend",
        candidate_paths=["frontend/src/components/Hero.tsx"],
        domain="frontend",
        design_source="notion",
        source_url="https://www.notion.so/workspace/hero-review",
        target_surface="web.hero",
        task_mode="read_only",
    )

    recommended = {item["skill"] for item in decision["recommended"]}
    assert decision["task_classification"]["label"] == "review"
    assert "pulseplate-pr-review" in recommended
    assert "code-review-expert" in recommended


@pytest.mark.parametrize(
    ("goal", "task_class", "candidate_paths", "domain", "expected_label", "expected_skill"),
    (
        (
            "Review bug in figma-backed hero",
            "Frontend",
            ["frontend/src/components/Hero.tsx"],
            "frontend",
            "review",
            "code-review-expert",
        ),
        (
            "Fix bug in figma-backed hero",
            "Frontend",
            ["frontend/src/components/Hero.tsx", "tests/test_dashboard.py"],
            "frontend",
            "bugfix",
            "bug-triage",
        ),
    ),
)
def test_skill_router_preserves_review_and_bugfix_lanes_with_explicit_design_metadata(
    goal: str,
    task_class: str,
    candidate_paths: list[str],
    domain: str,
    expected_label: str,
    expected_skill: str,
) -> None:
    """Explicit design metadata must not overwrite review or bugfix routing semantics."""

    decision = route_skills(
        goal=goal,
        task_class=task_class,
        candidate_paths=candidate_paths,
        domain=domain,
        design_source="figma_design",
        source_url="https://www.figma.com/design/demo/File?node-id=42-7",
        file_key_or_workspace="demo",
        node_id_or_frame_id="42:7",
        target_surface="web.hero",
        task_mode="implement",
        figma_lane_tool="figma_native",
        code_native_design_brief_path="docs/design/HERO_BRIEF.md",
    )

    recommended = {item["skill"] for item in decision["recommended"]}
    assert decision["task_classification"]["label"] == expected_label
    assert expected_skill in recommended


def test_skill_router_keeps_research_helpers_conditional_for_weak_research_intent() -> None:
    """Weak research/report signals should stay conditional until the deliverable is explicit."""

    decision = route_skills(
        goal="Capture a quick report note for later",
        task_class="Documentation",
        candidate_paths=["docs/ENGINEERING_LESSONS.md"],
        domain="docs",
    )

    conditional_by_skill = {item["skill"]: item for item in decision["conditional"]}
    assert "pulseplate-ai-reports" in conditional_by_skill
    assert (
        conditional_by_skill["pulseplate-ai-reports"]["when"]
        == "Enable when the task requires a report/research deliverable or durable knowledge capture."
    )


def test_skill_router_keeps_ci_helpers_conditional_without_explicit_failure_scope() -> None:
    """CI repair helpers should stay conditional unless failure scope is explicit."""

    decision = route_skills(
        goal="Document a CI note for later workflow follow-up",
        task_class="Documentation",
        candidate_paths=["docs/orchestration/workflow.md"],
        domain="docs",
    )

    conditional_by_skill = {item["skill"]: item for item in decision["conditional"]}
    assert "ci-fix" in conditional_by_skill
    assert (
        conditional_by_skill["ci-fix"]["when"]
        == "Enable when a failing CI job, workflow run, or check log is explicitly in scope."
    )


def test_skill_router_selects_threat_model_for_explicit_security_intent() -> None:
    """Threat-model requests should cross the explicit security threshold."""

    skills = select_recommended_skills(
        goal="Create a threat model for this auth boundary",
        task_class="Security",
        candidate_paths=["app/security/auth.py"],
        domain="security",
    )

    assert "security-threat-model" in skills


def test_skill_router_boosts_security_skills_for_privileged_surfaces() -> None:
    """Privilege-sensitive workflow and release paths should trigger security helpers."""

    skills = select_recommended_skills(
        goal="Tighten App Store workflow session handling",
        task_class="Release",
        candidate_paths=[
            ".github/workflows/ios-appstore-assets.yml",
            "ios/fastlane/Fastfile",
        ],
        domain="release",
    )

    assert "security-best-practices" in skills
    assert "pulseplate-guards" in skills


@pytest.mark.parametrize(
    ("candidate_path", "domain", "expected_reason_prefix"),
    (
        (".github/workflows/test.yml", "release", ".github/workflows/"),
        ("ios/fastlane/Fastfile", "release", "ios/fastlane/"),
        ("scripts/orchestration/skill_router.py", "orchestration", "scripts/orchestration/"),
        ("scripts/ci/check_pr_merge_readiness.py", "qa", "scripts/ci/"),
        ("docs/orchestration/AGENT_ROUTING_GRAPH.md", "orchestration", "docs/orchestration/"),
        ("docs/review/PR_999_FIXED_MAPPING.md", "qa", "docs/review/"),
    ),
)
def test_privileged_surface_parity_emits_stable_security_metadata(
    candidate_path: str,
    domain: str,
    expected_reason_prefix: str,
) -> None:
    """Privileged surfaces should deterministically emit stable security routing reasons."""

    decision = route_skills(
        goal="Refresh privileged merge-governance handling",
        task_class="QA",
        candidate_paths=[candidate_path],
        domain=domain,
    )

    recommended_by_skill = {item["skill"]: item for item in decision["recommended"]}

    assert "security-best-practices" in recommended_by_skill
    assert "pulseplate-guards" in recommended_by_skill
    assert (
        f"privileged-surface:{expected_reason_prefix}(+4)"
        in recommended_by_skill["security-best-practices"]["reasons"]
    )
    assert (
        f"privileged-surface:{expected_reason_prefix}(+4)"
        in recommended_by_skill["pulseplate-guards"]["reasons"]
    )


def test_privileged_surface_prefixes_stay_in_sync_with_policy_coverage() -> None:
    """Policy-critical privileged surface prefixes should remain explicit and finite."""

    assert len(PRIVILEGED_SURFACE_PREFIXES) == len(set(PRIVILEGED_SURFACE_PREFIXES))
    assert set(PRIVILEGED_SURFACE_PREFIXES) == {
        ".github/workflows/",
        "ios/fastlane/",
        "scripts/orchestration/",
        "scripts/ci/",
        "docs/orchestration/",
        "docs/review/",
    }


@pytest.mark.parametrize(
    "expected_line",
    EXPECTED_PRIVILEGED_SURFACE_POLICY_LINES,
)
def test_privileged_surface_policy_lines_stay_in_sync(expected_line: str) -> None:
    """Canonical privileged-surface bullets should stay locked to deterministic tests."""

    assert expected_line in _read_policy_doc()


def test_skill_router_prefix_match_is_boundary_aware() -> None:
    """Filename prefixes must not match unrelated longer filenames."""

    decision = route_skills(
        goal="Document routing rules",
        task_class="Docs",
        candidate_paths=["README.mdx"],
        domain="docs",
    )

    docs_sync = next(item for item in decision["recommended"] if item["skill"] == "docs-sync")
    joined_reasons = " ".join(docs_sync["reasons"])
    assert "path:README.md" not in joined_reasons


def test_skill_router_records_blocked_scraping_patterns() -> None:
    """Low-fit scraping requests should be explicitly blocked in routing metadata."""

    decision = route_skills(
        goal="Scrape the entire internet, TikTok, and Google Maps for wellness trends",
        task_class="Research",
        candidate_paths=["docs/audience_pack/ENGINEERING_OVERVIEW.md"],
        domain="research",
    )

    blocked_labels = {item["label"] for item in decision["blocked"]}
    assert "tiktok" in blocked_labels
    assert "google maps" in blocked_labels
    assert "entire internet" in blocked_labels
    assert all(item["kind"] == "pattern" for item in decision["blocked"])
    disallowed_matches = decision["research_connector_policy"]["matches"][
        RESEARCH_POLICY_BUCKET_DISALLOWED
    ]
    disallowed = {item["connector"] for item in disallowed_matches}
    assert "tiktok_scraping" in disallowed
    assert "google_maps_scraping" in disallowed
    assert "universal_free_form_scrapers" in disallowed
    matched_terms = {term for item in disallowed_matches for term in item.get("matched_terms", [])}
    assert blocked_labels == matched_terms


def test_skill_router_normalizes_blocked_patterns_with_disallowed_matches() -> None:
    """Blocked patterns should reuse the disallowed connector matcher contract."""

    decision = route_skills(
        goal="Research TikTok, Google-Maps, and scrape any-site competitor data",
        task_class="Research",
        candidate_paths=["docs/audience_pack/ENGINEERING_OVERVIEW.md"],
        domain="research",
    )

    blocked_labels = {item["label"] for item in decision["blocked"]}
    assert blocked_labels == {"tiktok", "google maps", "scrape any site"}
    disallowed = {
        item["connector"]
        for item in decision["research_connector_policy"]["matches"][
            RESEARCH_POLICY_BUCKET_DISALLOWED
        ]
    }
    assert disallowed == {
        "tiktok_scraping",
        "google_maps_scraping",
        "universal_free_form_scrapers",
    }


def test_skill_router_ignores_scraping_tokens_from_candidate_paths() -> None:
    """Blocked scraping patterns must come from request text, not touched files."""

    decision = route_skills(
        goal="Update the research docs and workflow guidance",
        task_class="Docs",
        candidate_paths=[
            "docs/tiktok.md",
            "app/google_maps_adapter.py",
        ],
        domain="docs",
    )

    assert decision["blocked"] == []
    assert decision["research_connector_policy"]["matches"][RESEARCH_POLICY_BUCKET_DISALLOWED] == []


def test_skill_router_exposes_stable_explanation_schema() -> None:
    """Skill routing should expose compact explanation metadata and semantic-group evidence."""

    decision = route_skills(
        goal="Update skill-routing explanation schema and per-skill evidence",
        task_class="Orchestration",
        candidate_paths=[
            "scripts/orchestration/skill_router.py",
            "docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md",
        ],
        domain="orchestration",
    )

    explanation = decision["explanation"]
    assert explanation["schema_version"] == "1.0"
    assert "semantic_group" in explanation["evidence_axes"]
    assert any(
        item["group_id"] == "orchestration.explainability"
        for item in explanation["semantic_groups"]
    )
    per_skill = {item["skill"]: item for item in explanation["per_skill_evidence"]}
    assert per_skill["pulseplate-workflow"]["bucket"] == "required"
    assert per_skill["docs-sync"]["bucket"] == "recommended"


def test_match_lexeme_terms_requires_token_boundaries() -> None:
    """Lexeme matching should not trigger on connector names embedded in larger tokens."""

    matches = skill_router_module._match_lexeme_terms(
        normalized_request_text="audit myyoutubeapp packaging notes",
        keywords=("youtube", "google trends"),
    )

    assert matches == []


def test_match_lexeme_terms_normalizes_keywords_before_matching() -> None:
    """Lexeme matching should use normalized keywords against normalized request text."""

    matches = skill_router_module._match_lexeme_terms(
        normalized_request_text="compare x twitter exports with search intent datasets",
        keywords=("x/twitter", "search-intent datasets"),
    )

    assert matches == ["x twitter", "search intent datasets"]


def test_skill_router_matches_approved_research_connectors_deterministically() -> None:
    """Approved research-only connectors should be explicit in the routing metadata."""

    decision = route_skills(
        goal=(
            "Prepare founder research using YouTube transcripts, Twitter official API "
            "exports, and Google Trends"
        ),
        task_class="Research",
        candidate_paths=["docs/audience_pack/ENGINEERING_OVERVIEW.md"],
        domain="research",
    )

    matched = {
        item["connector"]
        for item in decision["research_connector_policy"]["matches"][
            RESEARCH_POLICY_BUCKET_APPROVED
        ]
    }
    assert matched == {
        "youtube_transcripts",
        "x_twitter_official_exports",
        "google_trends",
    }
    assert any(
        item["group_id"] == "research.connector.youtube"
        for item in decision["explanation"]["semantic_groups"]
    )
    recommended = {item["skill"] for item in decision["recommended"]}
    assert "pulseplate-ai-reports" in recommended


def test_skill_router_selects_experimentation_lane_skills() -> None:
    """Experimentation intent should route the experiment-friendly default stack."""

    skills = select_recommended_skills(
        goal="Bootstrap experiment packet for RAG reliability benchmark",
        task_class="Experimentation",
        candidate_paths=["core/rag/vector_rag.py"],
        domain="ml",
    )

    assert "pulseplate-workflow" in skills
    assert "pulseplate-gates" in skills
    assert "docs-sync" in skills


def test_skill_router_selects_experimentation_lane_skills_for_cv_eval() -> None:
    """CV evaluation wording should still select the experimentation lane stack."""

    skills = select_recommended_skills(
        goal="Run CV eval for image reliability and benchmark confidence drift",
        task_class="Experimentation",
        candidate_paths=["core/insight/cv_adapter.py"],
        domain="ml",
    )

    assert "pulseplate-workflow" in skills
    assert "pulseplate-gates" in skills
    assert "docs-sync" in skills


def test_skill_router_selects_default_cv_routing_stack() -> None:
    """First-class CV domain should still receive the default orchestration stack."""

    skills = select_recommended_skills(
        goal="Review CV food image confidence drift for governed offline eval",
        task_class="AI / ML",
        candidate_paths=[
            ".cursor/agents/cv-agent.md",
            "docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md",
        ],
        domain="cv",
    )

    assert "pulseplate-workflow" in skills
    assert "pulseplate-gates" in skills
    assert "docs-sync" in skills


def test_skill_router_keeps_backend_endpoint_lane_for_cv_domain() -> None:
    """CV backend/provider work should still inherit the backend endpoint skill lane."""

    skills = select_recommended_skills(
        goal="Add provider-backed CV endpoint contract for food image analysis",
        task_class="AI / ML",
        candidate_paths=[
            "providers/cv_adapter.py",
            "app/routers/cv.py",
        ],
        domain="cv",
    )

    assert "pulseplate-backend-endpoints" in skills


def test_docs_only_envelope_strips_implementation_skills() -> None:
    """docs_only envelope must not recommend code-implementation skills (AGENTS docs-only PR rule)."""

    decision = route_skills(
        goal="Refresh documentation copy and glossary",
        task_class="Documentation",
        candidate_paths=["README.md", "docs/runbooks/QUICKSTART.md"],
        domain="docs",
        requested_agents=["frontend-engineer"],
    )

    assert decision["envelope_mode_hint"] == DOCS_ONLY_ENVELOPE_MODE
    recommended = {item["skill"] for item in decision["recommended"]}
    conditional = {item["skill"] for item in decision["conditional"]}
    for skill in DOCS_ONLY_EXCLUDED_ROUTING_SKILLS:
        assert skill not in recommended
        assert skill not in conditional


def test_docs_only_envelope_keeps_web_launch_site_planning_skill() -> None:
    """Launch-site skill supports planning/copy docs and should survive docs-only mode."""

    decision = route_skills(
        goal="Plan launch site SEO landing copy, waitlist CTA, and Product Hunt handoff",
        task_class="Documentation",
        candidate_paths=["docs/marketing/LAUNCH_SITE_PLAN.md"],
        domain="business",
    )

    assert decision["envelope_mode_hint"] == DOCS_ONLY_ENVELOPE_MODE
    recommended = {item["skill"] for item in decision["recommended"]}
    assert "pulseplate-web-launch-site" in recommended


def test_docs_only_app_store_runbook_updates_do_not_route_release_skill() -> None:
    """docs_only App Store runbook edits must not surface release implementation helpers."""

    decision = route_skills(
        goal="Refresh App Store metadata and review notes wording in the rollout runbook",
        task_class="Documentation",
        candidate_paths=["docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md"],
        domain="docs",
    )

    assert decision["envelope_mode_hint"] == DOCS_ONLY_ENVELOPE_MODE
    recommended = {item["skill"] for item in decision["recommended"]}
    conditional = {item["skill"] for item in decision["conditional"]}
    assert "pulseplate-app-store-release" not in recommended
    assert "pulseplate-app-store-release" not in conditional


def test_privileged_docs_paths_use_analysis_envelope_for_routing() -> None:
    """Privileged orchestration docs stay in analysis envelope; implementation skills remain eligible."""

    decision = route_skills(
        goal="Adjust orchestration workflow wording",
        task_class="Orchestration",
        candidate_paths=["docs/orchestration/workflow.md"],
        domain="orchestration",
    )

    assert decision["envelope_mode_hint"] == "analysis"
    recommended = {item["skill"] for item in decision["recommended"]}
    assert "pulseplate-guards" in recommended
