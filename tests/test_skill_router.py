"""Tests for deterministic skill routing."""

from __future__ import annotations

from scripts.orchestration.skill_router import route_skills, select_recommended_skills


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

    skills = [item["skill"] for item in decision["recommended"]]
    assert decision["policy_version"] == "2026-03-08"
    assert decision["selection_mode"] == "deterministic-weighted"
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
    """Direct code-review intent should reach the dedicated review skill."""

    skills = select_recommended_skills(
        goal="Need a code review for this frontend PR",
        task_class="Frontend",
        candidate_paths=["frontend/src/App.tsx"],
        domain="frontend",
    )

    assert "code-review-expert" in skills


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


def test_skill_router_treats_review_mapping_docs_as_privileged_surfaces() -> None:
    """Review-mapping docs should also trigger the privileged-surface security skill."""

    skills = select_recommended_skills(
        goal="Refresh merge-readiness review mapping guidance",
        task_class="QA",
        candidate_paths=["docs/review/PR_999_FIXED_MAPPING.md"],
        domain="qa",
    )

    assert "security-best-practices" in skills


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
