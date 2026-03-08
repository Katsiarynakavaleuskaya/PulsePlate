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
