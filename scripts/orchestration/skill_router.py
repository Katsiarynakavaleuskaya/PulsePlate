"""Deterministic skill routing helpers for coordinator bootstrap.

RU: Подбирает project-fit skills для task packet без ручного вызова.
EN: Selects project-fit skills for task packets without manual invocation.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Any

from scripts.orchestration.bootstrap_sync_policy import (
    DOCS_ONLY_ENVELOPE_MODE,
    resolve_analysis_envelope_mode,
)
from scripts.orchestration.context_pack import normalize_text, repo_relative_paths
from scripts.orchestration.design_lane_contract import (
    DESIGN_EXECUTION_TASK_MODES,
    design_trigger_present,
    figma_packet_is_execution_ready,
    normalize_design_blockers,
    normalize_optional_text,
)
from scripts.orchestration.requested_agents import normalize_requested_agents

ROUTING_POLICY_VERSION = "2026-03-27"
SELECTION_MODE = "deterministic-weighted"
ROUTING_EXPLANATION_SCHEMA_VERSION = "1.0"
RESEARCH_CONNECTOR_POLICY_VERSION = "2026-04-18"
RESEARCH_POLICY_BUCKET_APPROVED = "approved"
RESEARCH_POLICY_BUCKET_CONDITIONAL = "conditional"
RESEARCH_POLICY_BUCKET_DISALLOWED = "disallowed"
RESEARCH_POLICY_BUCKETS: tuple[str, ...] = (
    RESEARCH_POLICY_BUCKET_APPROVED,
    RESEARCH_POLICY_BUCKET_CONDITIONAL,
    RESEARCH_POLICY_BUCKET_DISALLOWED,
)

ALWAYS_ON_SKILLS: tuple[str, ...] = ("pulseplate-workflow",)
PR_GOVERNANCE_REQUIRED_SKILLS: tuple[str, ...] = (
    "pulseplate-workflow",
    "docs-sync",
    "pulseplate-gates",
)
CLASSIFICATION_PRECEDENCE: tuple[str, ...] = (
    "pr_governance",
    "design",
    "creative_research",
    "experiment",
    "review",
    "bugfix",
    "implementation",
)
PR_GOVERNANCE_CONDITIONAL_SKILLS: frozenset[str] = frozenset(
    {
        "create-pr",
        "commit-work",
        "release-notes",
        "gh-address-comments",
        "gh-fix-ci",
        "ci-fix",
    }
)
DESIGN_CONDITIONAL_SKILLS: frozenset[str] = frozenset(
    {
        "figma",
        "figma-implement-design",
    }
)
LAUNCH_GOVERNANCE_CONDITIONAL_SKILLS: frozenset[str] = frozenset(
    {
        "pulseplate-design-launch-system",
    }
)
RESEARCH_CONDITIONAL_SKILLS: frozenset[str] = frozenset(
    {
        "pulseplate-ai-reports",
        "pulseplate-monetization-gtm",
        "notion-research-documentation",
        "notion-knowledge-capture",
        "linear",
    }
)
CI_CONDITIONAL_SKILLS: frozenset[str] = frozenset({"ci-fix", "gh-fix-ci"})
TRIAGE_CLASSIFICATION_SKILL_BUNDLES: dict[str, tuple[str, ...]] = {
    "review": ("code-review-expert",),
    "bugfix": ("bug-triage",),
}

REQUESTED_AGENT_SKILL_BUNDLES: dict[str, tuple[str, ...]] = {
    "agent-coordinator": ("docs-sync", "agents-md", "pulseplate-gates"),
    "bug-hunter": ("bug-triage", "pulseplate-gates", "pulseplate-guards"),
    "security-auditor": ("security-best-practices", "security-threat-model", "pulseplate-guards"),
    "backend-engineer": (
        "pulseplate-backend-endpoints",
        "pulseplate-openapi-sync",
        "pulseplate-gates",
    ),
    "qa-engineer-agent": ("bug-triage", "pulseplate-gates", "code-review-expert"),
    "frontend-engineer": (
        "pulseplate-frontend-ui",
        "pulseplate-gates",
        "vercel-react-best-practices",
    ),
    "ml-engineer-agent": ("pulseplate-gates", "docs-sync", "openai-docs"),
    "data-scientist-agent": ("docs-sync", "pulseplate-gates", "pulseplate-ai-reports"),
    "web-research-agent": (
        "docs-sync",
        "pulseplate-ai-reports",
        "notion-research-documentation",
    ),
}

REQUESTED_AGENT_COMPANION_SKILL_BUNDLES: dict[str, tuple[str, ...]] = {
    "security-auditor": ("cybersecurity-skills",),
}

PRIVILEGED_SURFACE_PREFIXES: tuple[str, ...] = (
    ".github/workflows/",
    "ios/fastlane/",
    "scripts/orchestration/",
    "scripts/ci/",
    "docs/orchestration/",
    "docs/review/",
)

PRIVILEGED_SURFACE_SKILL_BUNDLES: dict[str, int] = {
    "security-best-practices": 4,
    "pulseplate-guards": 4,
}

# Skills that must not appear in recommended/conditional when the canonical bootstrap
# envelope mode is docs_only (aligned with AGENTS.md docs-only PR rule).
DOCS_ONLY_EXCLUDED_ROUTING_SKILLS: frozenset[str] = frozenset(
    {
        "pulseplate-backend-endpoints",
        "pulseplate-openapi-sync",
        "pulseplate-frontend-ui",
        "pulseplate-app-store-release",
        "vercel-react-best-practices",
        "build-web-apps:frontend-skill",
        "build-web-apps:web-design-guidelines",
        "build-web-apps:react-best-practices",
        "build-ios-apps:swiftui-ui-patterns",
        "build-ios-apps:swiftui-view-refactor",
        "build-ios-apps:ios-debugger-agent",
        "build-ios-apps:swiftui-performance-audit",
        "build-web-apps:stripe-best-practices",
        "pulseplate-playwright-e2e",
        "playwright",
        "figma-implement-design",
        "pulseplate-design-launch-system",
        "notion-spec-to-implementation",
    }
)

SCRAPING_BLOCK_PATTERNS: tuple[tuple[str, str], ...] = (
    ("tiktok", "TikTok scraping is not an approved default for PulsePlate."),
    ("google maps", "Google Maps scraping is not approved for the current repo."),
    ("scrape any site", "Universal scraping is out of scope for PulsePlate."),
    ("entire internet", "Broad internet scraping is outside project-fit boundaries."),
)

# Shared keyword sources keep semantic-group boosts and connector-policy matching in lockstep.
YOUTUBE_RESEARCH_KEYWORDS: tuple[str, ...] = (
    "youtube transcript",
    "youtube transcripts",
    "youtube channel",
    "youtube channels",
)
X_TWITTER_RESEARCH_KEYWORDS: tuple[str, ...] = (
    "x/twitter",
    "x twitter",
    "twitter official api",
    "twitter api",
    "compliant exports",
)
GOOGLE_TRENDS_RESEARCH_KEYWORDS: tuple[str, ...] = (
    "google trends",
    "search-intent datasets",
    "search intent datasets",
    "search intent data",
)
REDDIT_FORUM_RESEARCH_KEYWORDS: tuple[str, ...] = ("reddit", "forum mining", "forum research")
APP_STORE_REVIEW_MINING_KEYWORDS: tuple[str, ...] = (
    "app store reviews",
    "play store reviews",
    "review mining",
)
COMPETITOR_LANDING_PAGE_MONITORING_KEYWORDS: tuple[str, ...] = (
    "competitor landing page",
    "landing page monitoring",
)
TIKTOK_SCRAPING_KEYWORDS: tuple[str, ...] = ("tiktok",)
GOOGLE_MAPS_SCRAPING_KEYWORDS: tuple[str, ...] = ("google maps",)
UNIVERSAL_SCRAPING_KEYWORDS: tuple[str, ...] = ("scrape any site", "entire internet")


@dataclass(frozen=True)
class SemanticLexemeGroup:
    """Deterministic ontology-style semantic group for routing explanations."""

    group_id: str
    label: str
    rationale: str
    keywords: tuple[str, ...]
    skill_boosts: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class ResearchConnectorRule:
    """Deterministic research-only connector policy entry."""

    connector: str
    label: str
    policy_bucket: str
    rationale: str
    keywords: tuple[str, ...]


SEMANTIC_LEXEME_GROUPS: tuple[SemanticLexemeGroup, ...] = (
    SemanticLexemeGroup(
        group_id="orchestration.explainability",
        label="Routing explainability",
        rationale=(
            "Requests about explanation schemas and evidence should strengthen "
            "orchestration explainability surfaces without changing execution authority."
        ),
        keywords=(
            "explanation schema",
            "explainability",
            "per-skill evidence",
            "routing evidence",
            "skill-routing explanation",
        ),
        skill_boosts=(("docs-sync", 2), ("agents-md", 1)),
    ),
    SemanticLexemeGroup(
        group_id="research.connector.youtube",
        label="YouTube transcript research",
        rationale=(
            "YouTube transcript and channel monitoring requests stay inside the approved "
            "research-only founder/trend workflow."
        ),
        keywords=YOUTUBE_RESEARCH_KEYWORDS,
        skill_boosts=(
            ("pulseplate-ai-reports", 3),
            ("notion-research-documentation", 2),
        ),
    ),
    SemanticLexemeGroup(
        group_id="research.connector.x_twitter",
        label="X/Twitter official research",
        rationale=(
            "X/Twitter requests are allowed only through official APIs or compliant exports "
            "inside research-only workflows."
        ),
        keywords=X_TWITTER_RESEARCH_KEYWORDS,
        skill_boosts=(
            ("pulseplate-ai-reports", 3),
            ("notion-research-documentation", 2),
        ),
    ),
    SemanticLexemeGroup(
        group_id="research.connector.google_trends",
        label="Google Trends research",
        rationale=(
            "Google Trends is approved for bounded research and search-intent analysis only."
        ),
        keywords=GOOGLE_TRENDS_RESEARCH_KEYWORDS,
        skill_boosts=(
            ("pulseplate-ai-reports", 3),
            ("notion-research-documentation", 2),
        ),
    ),
)

RESEARCH_CONNECTOR_RULES: tuple[ResearchConnectorRule, ...] = (
    ResearchConnectorRule(
        connector="youtube_transcripts",
        label="YouTube transcripts",
        policy_bucket=RESEARCH_POLICY_BUCKET_APPROVED,
        rationale=(
            "Approved for founder research and trend tracking as a research-only connector."
        ),
        keywords=YOUTUBE_RESEARCH_KEYWORDS,
    ),
    ResearchConnectorRule(
        connector="x_twitter_official_exports",
        label="X/Twitter official API or compliant exports",
        policy_bucket=RESEARCH_POLICY_BUCKET_APPROVED,
        rationale=("Approved for research-only use via official APIs or compliant exports."),
        keywords=X_TWITTER_RESEARCH_KEYWORDS,
    ),
    ResearchConnectorRule(
        connector="google_trends",
        label="Google Trends and search-intent datasets",
        policy_bucket=RESEARCH_POLICY_BUCKET_APPROVED,
        rationale=("Approved for narrow research-only search-intent and trend analysis."),
        keywords=GOOGLE_TRENDS_RESEARCH_KEYWORDS,
    ),
    ResearchConnectorRule(
        connector="reddit_forum_mining",
        label="Reddit or forum mining",
        policy_bucket=RESEARCH_POLICY_BUCKET_CONDITIONAL,
        rationale="Conditionally allowed later after a future explicit governance promotion.",
        keywords=REDDIT_FORUM_RESEARCH_KEYWORDS,
    ),
    ResearchConnectorRule(
        connector="app_store_review_mining",
        label="App Store / Play Store review mining",
        policy_bucket=RESEARCH_POLICY_BUCKET_CONDITIONAL,
        rationale="Conditionally allowed later after an explicit governance promotion.",
        keywords=APP_STORE_REVIEW_MINING_KEYWORDS,
    ),
    ResearchConnectorRule(
        connector="competitor_landing_page_monitoring",
        label="Competitor landing page monitoring",
        policy_bucket=RESEARCH_POLICY_BUCKET_CONDITIONAL,
        rationale="Conditionally allowed later after an explicit governance promotion.",
        keywords=COMPETITOR_LANDING_PAGE_MONITORING_KEYWORDS,
    ),
    ResearchConnectorRule(
        connector="tiktok_scraping",
        label="TikTok scraping",
        policy_bucket=RESEARCH_POLICY_BUCKET_DISALLOWED,
        rationale="Not approved for the current repo.",
        keywords=TIKTOK_SCRAPING_KEYWORDS,
    ),
    ResearchConnectorRule(
        connector="google_maps_scraping",
        label="Google Maps scraping",
        policy_bucket=RESEARCH_POLICY_BUCKET_DISALLOWED,
        rationale="Not approved for the current repo.",
        keywords=GOOGLE_MAPS_SCRAPING_KEYWORDS,
    ),
    ResearchConnectorRule(
        connector="universal_free_form_scrapers",
        label="Universal free-form scrapers for arbitrary sites",
        policy_bucket=RESEARCH_POLICY_BUCKET_DISALLOWED,
        rationale="Broad arbitrary-site scraping is outside the PulsePlate contract.",
        keywords=UNIVERSAL_SCRAPING_KEYWORDS,
    ),
)


@dataclass(frozen=True)
class TaskClassificationRule:
    """Deterministic scoring rule for the task-intent classifier."""

    label: str
    domain_weights: dict[str, int]
    path_prefixes: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()


TASK_CLASSIFICATION_RULES: tuple[TaskClassificationRule, ...] = (
    TaskClassificationRule(
        label="pr_governance",
        domain_weights={"orchestration": 2, "qa": 1, "release": 1},
        path_prefixes=(
            ".github/workflows/",
            "scripts/ci/",
            "docs/review/",
        ),
        keywords=(
            "pull request",
            "open pr",
            "create pr",
            "review thread",
            "review comment",
            "merge",
            "merge readiness",
            "fixed mapping",
            "disposition",
            "code rabbit",
            "sourcery",
            "cubic",
            "gh pr checks",
            "governance",
        ),
    ),
    TaskClassificationRule(
        label="design",
        domain_weights={"design": 3, "frontend": 1},
        path_prefixes=("docs/design/",),
        keywords=(
            "figma",
            "node-id",
            "node id",
            "design system",
            "design fidelity",
            "ui fidelity",
            "prototype",
            "screen",
            "frame",
        ),
    ),
    TaskClassificationRule(
        label="creative_research",
        domain_weights={"research": 3, "business": 2, "wellness": 2},
        path_prefixes=("docs/reports/", "docs/insights/", "docs/audience_pack/"),
        keywords=(
            "weekly",
            "monthly",
            "quarterly",
            "trend",
            "report",
            "research brief",
            "gtm",
            "aso",
            "seo",
        ),
    ),
    TaskClassificationRule(
        label="experiment",
        domain_weights={"ml": 3, "cv": 3},
        path_prefixes=("core/rag/", "core/insight/", "docs/orchestration/CV_"),
        keywords=(
            "experiment",
            "benchmark",
            "eval",
            "evaluation",
            "reliability",
            "optimization",
            "ablation",
            "offline eval",
            "confidence drift",
        ),
    ),
    TaskClassificationRule(
        label="review",
        domain_weights={"qa": 2, "orchestration": 1},
        path_prefixes=("docs/review/",),
        keywords=(
            "review",
            "code review",
            "audit",
            "comments",
            "thread",
        ),
    ),
    TaskClassificationRule(
        label="bugfix",
        domain_weights={"qa": 1, "backend": 1, "frontend": 1},
        path_prefixes=("tests/",),
        keywords=(
            "bug",
            "fix",
            "failure",
            "failing",
            "regression",
            "flaky",
            "broken",
            "error",
        ),
    ),
    TaskClassificationRule(
        label="implementation",
        domain_weights={
            "backend": 1,
            "frontend": 1,
            "orchestration": 1,
            "docs": 1,
            "design": 1,
            "research": 1,
            "business": 1,
            "wellness": 1,
            "release": 1,
            "security": 1,
            "ml": 1,
            "cv": 1,
            "qa": 1,
        },
        path_prefixes=("app/", "core/", "frontend/", "scripts/", "ios/"),
        keywords=("implement", "add", "build", "wire", "update", "refactor"),
    ),
)


def _validate_task_classification_contract() -> None:
    """Fail fast when classifier precedence and rule labels diverge."""

    precedence_labels = tuple(dict.fromkeys(CLASSIFICATION_PRECEDENCE))
    if precedence_labels != CLASSIFICATION_PRECEDENCE:
        raise ValueError("CLASSIFICATION_PRECEDENCE must not contain duplicate labels")

    rule_labels = tuple(rule.label for rule in TASK_CLASSIFICATION_RULES)
    if len(set(rule_labels)) != len(rule_labels):
        raise ValueError("TASK_CLASSIFICATION_RULES must not contain duplicate labels")

    missing_labels = tuple(label for label in CLASSIFICATION_PRECEDENCE if label not in rule_labels)
    extra_labels = tuple(label for label in rule_labels if label not in CLASSIFICATION_PRECEDENCE)
    if missing_labels or extra_labels:
        raise ValueError(
            "Task classification labels are out of sync: "
            f"missing={missing_labels}, extra={extra_labels}"
        )


_validate_task_classification_contract()


def _strip_skills_for_docs_only_envelope(
    *,
    envelope_mode: str,
    recommended: list[dict[str, Any]],
    conditional: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Remove implementation-skills from routing when bootstrap envelope is docs_only.

    RU: Согласовано с `bootstrap_sync_policy.resolve_analysis_envelope_mode`.
    EN: Keeps skill routing aligned with the canonical message envelope derivation.
    """

    if envelope_mode != DOCS_ONLY_ENVELOPE_MODE:
        return recommended, conditional

    excluded = DOCS_ONLY_EXCLUDED_ROUTING_SKILLS
    filtered_recommended = [item for item in recommended if item["skill"] not in excluded]
    filtered_conditional = [item for item in conditional if item["skill"] not in excluded]
    return filtered_recommended, filtered_conditional


def _match_lexeme_terms(*, normalized_request_text: str, keywords: tuple[str, ...]) -> list[str]:
    """Return matched lexeme terms in stable order."""

    matches: list[str] = []
    for keyword in keywords:
        normalized_keyword = _normalize_lexeme(keyword)
        if (
            normalized_keyword
            and normalized_keyword not in matches
            and re.search(rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)", normalized_request_text)
        ):
            matches.append(normalized_keyword)
    return matches


def _match_semantic_groups(*, normalized_request_text: str) -> list[dict[str, Any]]:
    """Return matched ontology-style semantic groups for explainability."""

    matched_groups: list[dict[str, Any]] = []
    for group in SEMANTIC_LEXEME_GROUPS:
        matched_terms = _match_lexeme_terms(
            normalized_request_text=normalized_request_text,
            keywords=group.keywords,
        )
        if not matched_terms:
            continue
        matched_groups.append(
            {
                "group_id": group.group_id,
                "label": group.label,
                "matched_terms": matched_terms,
                "rationale": group.rationale,
            }
        )
    return matched_groups


def _build_research_connector_policy(*, normalized_request_text: str) -> dict[str, Any]:
    """Return deterministic research-only connector policy metadata."""

    catalog: dict[str, list[dict[str, Any]]] = {bucket: [] for bucket in RESEARCH_POLICY_BUCKETS}
    matches: dict[str, list[dict[str, Any]]] = {bucket: [] for bucket in RESEARCH_POLICY_BUCKETS}

    for rule in RESEARCH_CONNECTOR_RULES:
        entry = {
            "connector": rule.connector,
            "label": rule.label,
            "rationale": rule.rationale,
        }
        catalog[rule.policy_bucket].append(entry)
        matched_terms = _match_lexeme_terms(
            normalized_request_text=normalized_request_text,
            keywords=rule.keywords,
        )
        if matched_terms:
            matches[rule.policy_bucket].append(
                {
                    "connector": rule.connector,
                    "label": rule.label,
                    "matched_terms": matched_terms,
                }
            )

    return {
        "policy_version": RESEARCH_CONNECTOR_POLICY_VERSION,
        RESEARCH_POLICY_BUCKET_APPROVED: catalog[RESEARCH_POLICY_BUCKET_APPROVED],
        RESEARCH_POLICY_BUCKET_CONDITIONAL: catalog[RESEARCH_POLICY_BUCKET_CONDITIONAL],
        RESEARCH_POLICY_BUCKET_DISALLOWED: catalog[RESEARCH_POLICY_BUCKET_DISALLOWED],
        "matches": matches,
    }


def _build_blocked_patterns(*, research_connector_policy: dict[str, Any]) -> list[dict[str, str]]:
    """Derive blocked-pattern metadata from the same disallowed connector matches."""

    disallowed_reasons = {
        rule.connector: rule.rationale
        for rule in RESEARCH_CONNECTOR_RULES
        if rule.policy_bucket == RESEARCH_POLICY_BUCKET_DISALLOWED
    }
    blocked: list[dict[str, str]] = []
    seen_labels: set[str] = set()

    for match in research_connector_policy["matches"][RESEARCH_POLICY_BUCKET_DISALLOWED]:
        reason = disallowed_reasons.get(
            match["connector"],
            "Disallowed research connector pattern for the current repo.",
        )
        for matched_term in match.get("matched_terms", []):
            if matched_term in seen_labels:
                continue
            blocked.append({"label": matched_term, "reason": reason, "kind": "pattern"})
            seen_labels.add(matched_term)

    return blocked


def _apply_semantic_group_boosts(
    *,
    selected_by_skill: dict[str, dict[str, Any]],
    matched_semantic_groups: list[dict[str, Any]],
    task_classification: dict[str, Any],
    domain: str,
    required_skill_names: set[str],
) -> None:
    """Apply deterministic semantic-group boosts where the lane allows it."""

    research_lane = task_classification["label"] == "creative_research" or domain in {
        "research",
        "business",
        "wellness",
    }
    orchestration_lane = domain == "orchestration"

    for group in SEMANTIC_LEXEME_GROUPS:
        matched = next(
            (item for item in matched_semantic_groups if item["group_id"] == group.group_id),
            None,
        )
        if matched is None:
            continue
        group_is_research_connector = group.group_id.startswith("research.connector.")
        if group_is_research_connector and not research_lane:
            continue
        if group.group_id == "orchestration.explainability" and not orchestration_lane:
            continue
        for skill, boost in group.skill_boosts:
            if skill in required_skill_names:
                continue
            _apply_bundle_reason(
                selected_by_skill=selected_by_skill,
                skill=skill,
                boost=boost,
                reason=f"semantic-group:{group.group_id}(+{boost})",
                fallback_rationale=group.rationale,
            )


def _build_explanation_schema(
    *,
    required: list[dict[str, Any]],
    recommended: list[dict[str, Any]],
    conditional: list[dict[str, Any]],
    matched_semantic_groups: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return stable explanation metadata with compact per-skill evidence."""

    per_skill_evidence: list[dict[str, Any]] = []
    for bucket_name, items in (
        ("required", required),
        ("recommended", recommended),
        ("conditional", conditional),
    ):
        for item in items:
            evidence = {
                "skill": item["skill"],
                "bucket": bucket_name,
                "reasons": list(item.get("reasons", [])),
            }
            if "score" in item:
                evidence["score"] = int(item["score"])
            per_skill_evidence.append(evidence)

    return {
        "schema_version": ROUTING_EXPLANATION_SCHEMA_VERSION,
        "evidence_axes": [
            "domain_prior",
            "path_evidence",
            "lexical_cue",
            "semantic_group",
            "requested_agent",
            "privileged_surface",
            "policy_block",
        ],
        "semantic_groups": matched_semantic_groups,
        "per_skill_evidence": per_skill_evidence,
    }


@dataclass(frozen=True)
class SkillRule:
    """Weighted routing rule for one skill."""

    skill: str
    category: str
    rationale: str
    min_score: int
    domain_weights: dict[str, int]
    path_prefixes: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()


SKILL_RULES: tuple[SkillRule, ...] = (
    SkillRule(
        skill="pulseplate-workflow",
        category="repo-tracked",
        rationale="Mandatory entry skill for all PulsePlate tasks.",
        min_score=0,
        domain_weights={},
    ),
    SkillRule(
        skill="docs-sync",
        category="global",
        rationale="Keep orchestration, runbooks, and product docs aligned with the implementation.",
        min_score=3,
        domain_weights={
            "docs": 2,
            "orchestration": 2,
            "research": 1,
            "business": 1,
            "ml": 1,
            "cv": 1,
        },
        path_prefixes=("docs/", "README.md", ".cursor/agents/"),
        keywords=(
            "doc",
            "docs",
            "runbook",
            "policy",
            "readme",
            "audit",
            "experiment",
            "benchmark",
            "eval",
            "optimization",
            "reliability",
            "cv",
        ),
    ),
    SkillRule(
        skill="agents-md",
        category="global",
        rationale="Update AGENTS and agent workflow guidance when orchestration surfaces change.",
        min_score=4,
        domain_weights={"orchestration": 2},
        path_prefixes=(".cursor/agents/",),
        keywords=("agent", "agents.md", "coordinator", "skill routing", "workflow"),
    ),
    SkillRule(
        skill="pulseplate-gates",
        category="repo-tracked",
        rationale="Run PulsePlate quality gates for code, docs, and contract-safe changes.",
        min_score=2,
        domain_weights={"backend": 1, "frontend": 1, "orchestration": 1, "qa": 2, "cv": 1},
        path_prefixes=("app/", "core/", "frontend/", "tests/", "scripts/", "docs/orchestration/"),
        keywords=(
            "test",
            "verify",
            "gate",
            "coverage",
            "diff-cover",
            "lint",
            "mypy",
            "experiment",
            "benchmark",
            "eval",
            "optimization",
            "reliability",
            "cv",
        ),
    ),
    SkillRule(
        skill="pulseplate-guards",
        category="repo-tracked",
        rationale="Handle architecture guards, fail-closed policy checks, and security-oriented invariants.",
        min_score=3,
        domain_weights={"security": 2, "qa": 2, "orchestration": 1, "backend": 1},
        path_prefixes=(
            "app/security/",
            "tests/",
            "tests/guards/",
            *PRIVILEGED_SURFACE_PREFIXES,
        ),
        keywords=(
            "guard",
            "policy",
            "invariant",
            "fail-closed",
            "rate limit",
            "quota",
            "workflow",
            "fastlane",
        ),
    ),
    SkillRule(
        skill="pulseplate-backend-endpoints",
        category="repo-tracked",
        rationale="Backend/API tasks should follow endpoint skill constraints and deterministic tests.",
        min_score=3,
        domain_weights={"backend": 3, "ml": 2, "cv": 2},
        path_prefixes=("app/", "core/", "providers/", "legacy_app.py"),
        keywords=("endpoint", "api", "router", "schema", "fastapi", "provider"),
    ),
    SkillRule(
        skill="pulseplate-openapi-sync",
        category="repo-tracked",
        rationale="Contract changes must keep backend OpenAPI and generated frontend types in sync.",
        min_score=4,
        domain_weights={"backend": 1, "frontend": 1},
        path_prefixes=("frontend/src/api/", "app/static/openapi.json"),
        keywords=("openapi", "client types", "schema.ts", "api types", "contract"),
    ),
    SkillRule(
        skill="pulseplate-frontend-ui",
        category="repo-tracked",
        rationale="Frontend tasks should stay inside PulsePlate thin-client and token-driven UI constraints.",
        min_score=3,
        domain_weights={"frontend": 3, "design": 1},
        path_prefixes=("frontend/",),
        keywords=("frontend", "ui", "tsx", "page", "component", "web ui"),
    ),
    SkillRule(
        skill="build-web-apps:frontend-skill",
        category="global",
        rationale="Strong web UI and landing-page work should use the curated web frontend skill.",
        min_score=4,
        domain_weights={"frontend": 2, "design": 2},
        path_prefixes=("frontend/", "docs/design/"),
        keywords=(
            "ui ux",
            "landing page",
            "website",
            "hero section",
            "marketing site",
            "launch site",
            "web ui",
        ),
    ),
    SkillRule(
        skill="build-web-apps:web-design-guidelines",
        category="global",
        rationale="UI/UX review and design audit work should use the web design guideline skill.",
        min_score=5,
        domain_weights={"frontend": 1, "design": 2, "qa": 1},
        path_prefixes=("frontend/", "docs/design/"),
        keywords=(
            "design audit",
            "design fidelity",
            "ux audit",
            "ui review",
            "review ui",
            "brand alignment",
            "design tokens",
            "token alignment",
            "check accessibility",
            "web design",
            "design guidelines",
        ),
    ),
    SkillRule(
        skill="build-web-apps:react-best-practices",
        category="global",
        rationale="React performance and architecture work should use the dedicated web React guidance.",
        min_score=5,
        domain_weights={"frontend": 2},
        path_prefixes=("frontend/",),
        keywords=(
            "react performance",
            "next.js",
            "bundle optimization",
            "react compiler",
            "deferred value",
        ),
    ),
    SkillRule(
        skill="pulseplate-ai-reports",
        category="repo-tracked",
        rationale="Research, wellness, and GTM tasks should use the bounded report workflow instead of generic scraping.",
        min_score=4,
        domain_weights={"research": 3, "business": 2, "wellness": 3},
        path_prefixes=("docs/audience_pack/", "docs/reports/", "docs/insights/"),
        keywords=(
            "report",
            "trend",
            "weekly",
            "monthly",
            "quarterly",
            "gtm",
            "aso",
            "seo",
            "wellness",
        ),
    ),
    SkillRule(
        skill="pulseplate-monetization-gtm",
        category="repo-tracked",
        rationale=(
            "Paywall, subscription pricing, billing-flow, and wellness-safe "
            "growth-channel work should use the dedicated PulsePlate monetization skill."
        ),
        min_score=6,
        domain_weights={"business": 2, "wellness": 1, "research": 1},
        path_prefixes=(
            "docs/marketing/",
            "docs/analytics/",
            "docs/product/FREE_PRO_CONTRACT.md",
            "docs/product/FREE_PRO_SOFT_PAYWALL.md",
            "app/services/payments_activation.py",
            "core/billing_policy.py",
        ),
        keywords=(
            "paywall",
            "subscription",
            "pricing",
            "billing flow",
            "trial",
            "restore",
            "conversion",
            "product hunt",
            "aso",
            "seo",
            "gtm",
            "monetization",
        ),
    ),
    SkillRule(
        skill="bug-triage",
        category="global",
        rationale="Use the bug-triage workflow when the task is framed as a failure, regression, or fix.",
        min_score=4,
        domain_weights={"qa": 2, "backend": 1, "frontend": 1},
        path_prefixes=("tests/",),
        keywords=("bug", "fix", "failure", "regression", "flaky", "triage"),
    ),
    SkillRule(
        skill="code-review-expert",
        category="global",
        rationale="Explicit review tasks should use the dedicated review skill.",
        min_score=4,
        domain_weights={"qa": 1, "orchestration": 1},
        keywords=("review", "code review"),
    ),
    SkillRule(
        skill="ci-fix",
        category="global",
        rationale="CI failures should trigger the dedicated CI remediation workflow.",
        min_score=4,
        domain_weights={"qa": 2},
        keywords=("ci", "github actions", "workflow run", "checks", "failing check"),
    ),
    SkillRule(
        skill="gh-fix-ci",
        category="global",
        rationale="GitHub-based CI debugging is useful when the task explicitly references PR checks.",
        min_score=4,
        domain_weights={"qa": 1},
        keywords=(
            "gh pr checks",
            "gh run",
            "gh workflow",
            "github actions",
            "pr checks",
            "pull request checks",
            "github pr checks",
            "failing pr checks",
            "ci log",
            "workflow run",
        ),
    ),
    SkillRule(
        skill="create-pr",
        category="global",
        rationale="PR preparation should use the dedicated PR packaging workflow.",
        min_score=3,
        domain_weights={"orchestration": 1, "docs": 1},
        keywords=(
            "open pr",
            "create pr",
            "pull request",
            "prepare pr",
            "prepare pull request",
            "prepare the pull request",
        ),
    ),
    SkillRule(
        skill="commit-work",
        category="global",
        rationale="Commit structuring should be explicit and separate from normal code changes.",
        min_score=5,
        domain_weights={"orchestration": 1},
        keywords=("commit", "stage", "conventional commit"),
    ),
    SkillRule(
        skill="release-notes",
        category="global",
        rationale="Release-note generation should stay in the dedicated release workflow.",
        min_score=4,
        domain_weights={"release": 2, "docs": 1},
        keywords=("release notes", "changelog"),
    ),
    SkillRule(
        skill="build-ios-apps:swiftui-ui-patterns",
        category="global",
        rationale="SwiftUI UI work should use the dedicated iOS UI patterns skill.",
        min_score=4,
        domain_weights={"release": 1},
        path_prefixes=("ios/",),
        keywords=(
            "swiftui",
            "ios ui",
            "iphone",
            "ipad",
            "app store screen",
            "swiftui view",
        ),
    ),
    SkillRule(
        skill="build-ios-apps:swiftui-view-refactor",
        category="global",
        rationale="SwiftUI restructuring work should use the focused iOS refactor guidance.",
        min_score=5,
        domain_weights={"ios": 1, "release": 1},
        path_prefixes=("ios/",),
        keywords=(
            "refactor",
            "swiftui refactor",
            "view refactor",
            "observation",
            "binding",
            "split long swiftui view",
        ),
    ),
    SkillRule(
        skill="build-ios-apps:ios-debugger-agent",
        category="global",
        rationale="Simulator, Xcode, and runtime iOS debugging should use the dedicated debugger workflow.",
        min_score=5,
        domain_weights={"release": 1, "qa": 1},
        path_prefixes=("ios/",),
        keywords=(
            "ios debug",
            "xcode",
            "simulator",
            "launch ios app",
            "run ios app",
            "debug swiftui",
            "app store screenshot",
            "app store screenshots",
            "fastlane screenshots",
        ),
    ),
    SkillRule(
        skill="pulseplate-app-store-release",
        category="repo-tracked",
        rationale=(
            "App Store metadata, screenshot packs, App Privacy uploads, and "
            "release-evidence work should use the dedicated PulsePlate release skill."
        ),
        min_score=6,
        domain_weights={"release": 2, "qa": 1},
        path_prefixes=("ios/fastlane/", "docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md"),
        keywords=(
            "app store metadata",
            "app store screenshot",
            "app store screenshots",
            "app store connect",
            "app privacy",
            "review information",
            "review notes",
            "fastlane metadata",
            "fastlane screenshots",
            "app store submission",
            "release evidence",
        ),
    ),
    SkillRule(
        skill="build-ios-apps:swiftui-performance-audit",
        category="global",
        rationale="SwiftUI performance and rendering issues should use the dedicated audit skill.",
        min_score=5,
        domain_weights={"qa": 1, "release": 1},
        path_prefixes=("ios/",),
        keywords=(
            "swiftui performance",
            "jank",
            "stutter",
            "rendering",
            "scroll performance",
            "memory spike",
        ),
    ),
    SkillRule(
        skill="openai-docs",
        category="global",
        rationale="OpenAI product/API questions should use official docs-first guidance.",
        min_score=5,
        domain_weights={"ml": 1, "cv": 1, "backend": 1},
        keywords=(
            "openai",
            "chatgpt",
            "responses api",
            "realtime api",
            "codex api",
            "llm",
            "assistant",
        ),
    ),
    SkillRule(
        skill="playwright",
        category="global",
        rationale="Browser automation should use the explicit Playwright workflow.",
        min_score=5,
        domain_weights={"frontend": 1, "qa": 1},
        keywords=("playwright", "browser", "e2e", "ui flow", "visual regression"),
    ),
    SkillRule(
        skill="pulseplate-playwright-e2e",
        category="repo-tracked",
        rationale="PulsePlate browser flows should use the controlled E2E wrapper.",
        min_score=5,
        domain_weights={"frontend": 1, "qa": 2},
        keywords=("playwright", "e2e", "browser", "pulseplate ui"),
        path_prefixes=("frontend/", "docs/dev/PLAYWRIGHT_E2E_RUNBOOK.md"),
    ),
    SkillRule(
        skill="figma",
        category="global",
        rationale="Figma-linked implementation tasks should use the design-context workflow.",
        min_score=5,
        domain_weights={"design": 2, "frontend": 1},
        keywords=("figma", "node-id", "design-to-code", "design system"),
    ),
    SkillRule(
        skill="figma-implement-design",
        category="global",
        rationale="Design implementation should use the dedicated Figma-to-code skill when fidelity matters.",
        min_score=6,
        domain_weights={"design": 2, "frontend": 1},
        keywords=("implement design", "design fidelity", "figma", "node-id"),
    ),
    SkillRule(
        skill="pulseplate-design-launch-system",
        category="repo-tracked",
        rationale=(
            "PulsePlate launch-asset governance, token/brand consistency, and "
            "design-system readiness work should use the dedicated passive "
            "design launch system skill."
        ),
        min_score=6,
        domain_weights={"design": 2, "frontend": 1, "docs": 1},
        path_prefixes=(
            "docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md",
            "docs/design/",
            "tokens/",
        ),
        keywords=(
            "launch asset",
            "launch assets",
            "launch readiness",
            "launch kit",
            "asset bundle",
            "asset bundles",
            "brand consistency",
            "brand alignment",
            "token consistency",
            "design system readiness",
        ),
    ),
    SkillRule(
        skill="linear",
        category="global",
        rationale="Linear-linked work should use the dedicated issue/project integration skill.",
        min_score=5,
        domain_weights={"business": 1, "orchestration": 1},
        keywords=("linear", "ticket", "issue", "project"),
    ),
    SkillRule(
        skill="build-web-apps:stripe-best-practices",
        category="global",
        rationale="Billing, subscription, and paywall work should use the dedicated Stripe integration guidance when applicable.",
        min_score=6,
        domain_weights={"business": 1, "backend": 1, "release": 1},
        path_prefixes=("app/services/", "core/"),
        keywords=(
            "stripe",
            "subscription",
            "paywall",
            "billing",
            "checkout",
            "pricing",
            "monetization",
        ),
    ),
    SkillRule(
        skill="notion-research-documentation",
        category="global",
        rationale="Notion research capture is useful for report and strategy tasks.",
        min_score=5,
        domain_weights={"research": 2, "business": 1, "wellness": 1},
        keywords=("notion", "research note", "wiki", "brief"),
    ),
    SkillRule(
        skill="notion-knowledge-capture",
        category="global",
        rationale="Structured Notion capture is useful when the task explicitly asks for durable knowledge storage.",
        min_score=6,
        domain_weights={"docs": 1, "research": 1},
        keywords=("knowledge capture", "notion page", "wiki update"),
    ),
    SkillRule(
        skill="notion-spec-to-implementation",
        category="global",
        rationale="Spec-driven implementation planning should use the dedicated Notion skill.",
        min_score=6,
        domain_weights={"orchestration": 1, "business": 1},
        keywords=("spec", "implementation plan", "notion spec"),
    ),
    SkillRule(
        skill="security-best-practices",
        category="global",
        rationale="Explicit security hardening work should use the security review skill.",
        min_score=5,
        domain_weights={"security": 3, "orchestration": 1, "backend": 1, "release": 1},
        path_prefixes=(
            "app/security/",
            *PRIVILEGED_SURFACE_PREFIXES,
        ),
        keywords=(
            "security",
            "hardening",
            "appsec",
            "auth",
            "token",
            "cve",
            "workflow",
            "fastlane",
            "secret",
            "merge-readiness",
            "review mapping",
        ),
    ),
    SkillRule(
        skill="security-threat-model",
        category="global",
        rationale="Threat modeling should be explicit, not implicit.",
        min_score=5,
        domain_weights={"security": 3},
        keywords=("threat model", "abuse path", "trust boundary"),
    ),
    SkillRule(
        skill="gh-address-comments",
        category="global",
        rationale="GitHub review-thread handling should use the dedicated comment workflow.",
        min_score=4,
        domain_weights={"qa": 2, "orchestration": 1},
        keywords=(
            "review comment",
            "review thread",
            "address comments",
            "github comment",
            "github review",
        ),
    ),
    SkillRule(
        skill="vercel-react-best-practices",
        category="global",
        rationale="React and Vercel performance guidance should support frontend implementation work.",
        min_score=4,
        domain_weights={"frontend": 2, "design": 1},
        path_prefixes=("frontend/",),
        keywords=("react", "tsx", "component", "frontend", "web ui", "performance"),
    ),
)

SKILL_RULES_BY_SKILL: dict[str, SkillRule] = {rule.skill: rule for rule in SKILL_RULES}


def _normalize_lexeme(value: str) -> str:
    """Normalize keyword phrases with the same rules as task text."""

    normalized = normalize_text(value)
    if not isinstance(normalized, str):  # pragma: no cover - defensive typing guard
        raise TypeError("normalize_text must return a string")
    return normalized


def _has_prefix(path: str, prefix: str) -> bool:
    normalized_path = os.path.normpath(path)
    normalized_prefix = os.path.normpath(prefix.rstrip("/"))
    if normalized_path == normalized_prefix:
        return True
    return normalized_path.startswith(f"{normalized_prefix}{os.sep}")


def _match_keywords(keywords: tuple[str, ...], normalized_text: str) -> list[str]:
    """Return keywords whose normalized phrases match on token boundaries."""

    matched: list[str] = []
    for keyword in keywords:
        normalized_keyword = _normalize_lexeme(keyword)
        if normalized_keyword and re.search(
            rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)", normalized_text
        ):
            matched.append(keyword)
    return matched


def _match_path_prefixes(
    prefixes: tuple[str, ...],
    normalized_paths: list[str],
) -> list[str]:
    """Return matched normalized prefixes for the provided repo-relative paths."""

    return [
        prefix for prefix in prefixes if any(_has_prefix(path, prefix) for path in normalized_paths)
    ]


def _score_rule(
    *,
    rule: SkillRule,
    normalized_paths: list[str],
    normalized_text: str,
    domain: str,
) -> dict[str, Any]:
    """Return score + evidence for one rule."""

    score = 0
    reasons: list[str] = []

    if rule.skill in ALWAYS_ON_SKILLS:
        reasons.append("always-on")
        return {
            "skill": rule.skill,
            "score": 100,
            "category": rule.category,
            "rationale": rule.rationale,
            "reasons": reasons,
        }

    if domain in rule.domain_weights:
        weight = rule.domain_weights[domain]
        score += weight
        reasons.append(f"domain:{domain}(+{weight})")

    matched_prefixes = _match_path_prefixes(rule.path_prefixes, normalized_paths)
    if matched_prefixes:
        prefix_score = len(matched_prefixes) * 2
        score += prefix_score
        reasons.append(f"path:{', '.join(matched_prefixes)}(+{prefix_score})")

    matched_keywords = _match_keywords(rule.keywords, normalized_text)
    if matched_keywords:
        keyword_score = min(len(matched_keywords), 3) * 2
        score += keyword_score
        reasons.append(f"lexeme:{', '.join(matched_keywords[:3])}(+{keyword_score})")

    return {
        "skill": rule.skill,
        "score": score,
        "category": rule.category,
        "rationale": rule.rationale,
        "reasons": reasons,
    }


def _apply_bundle_reason(
    *,
    selected_by_skill: dict[str, dict[str, Any]],
    skill: str,
    boost: int,
    reason: str,
    fallback_rationale: str,
) -> None:
    """Apply deterministic bundle/privileged boost without duplicating entries."""

    existing = selected_by_skill.get(skill)
    if existing is None:
        rule = SKILL_RULES_BY_SKILL.get(skill)
        category = rule.category if rule is not None else "bundle"
        rationale = rule.rationale if rule is not None else fallback_rationale
        selected_by_skill[skill] = {
            "skill": skill,
            "score": boost,
            "category": category,
            "rationale": rationale,
            "reasons": [reason],
        }
        return

    existing["score"] = int(existing["score"]) + boost
    if reason not in existing["reasons"]:
        existing["reasons"].append(reason)


def _score_task_classification(
    *,
    rule: TaskClassificationRule,
    normalized_paths: list[str],
    normalized_text: str,
    domain: str,
) -> dict[str, Any]:
    """Return score and evidence for one task-classification rule."""

    score = 0
    reasons: list[str] = []

    if domain in rule.domain_weights:
        weight = rule.domain_weights[domain]
        score += weight
        reasons.append(f"domain:{domain}(+{weight})")

    matched_prefixes = _match_path_prefixes(rule.path_prefixes, normalized_paths)
    if matched_prefixes:
        prefix_score = len(matched_prefixes) * 3
        score += prefix_score
        reasons.append(f"path:{', '.join(matched_prefixes)}(+{prefix_score})")

    matched_keywords = _match_keywords(rule.keywords, normalized_text)
    if matched_keywords:
        keyword_score = min(len(matched_keywords), 3) * 2
        score += keyword_score
        reasons.append(f"lexeme:{', '.join(matched_keywords[:3])}(+{keyword_score})")

    return {"label": rule.label, "score": score, "reasons": reasons}


def _classify_task(
    *,
    normalized_paths: list[str],
    normalized_text: str,
    domain: str,
) -> dict[str, Any]:
    """Return deterministic task classification metadata."""

    scored = [
        _score_task_classification(
            rule=rule,
            normalized_paths=normalized_paths,
            normalized_text=normalized_text,
            domain=domain,
        )
        for rule in TASK_CLASSIFICATION_RULES
    ]
    scored_by_label = {item["label"]: item for item in scored}
    winning_label = "implementation"
    winning_score = -1
    minimum_score_by_label = {"creative_research": 4}

    for label in CLASSIFICATION_PRECEDENCE:
        candidate = scored_by_label.get(label)
        if candidate is None:
            continue
        candidate_score = int(candidate["score"])
        if candidate_score < minimum_score_by_label.get(label, 1):
            continue
        if candidate_score > winning_score:
            winning_label = label
            winning_score = candidate_score

    winner = scored_by_label.get(winning_label)
    if winning_score <= 0:
        return {
            "label": "implementation",
            "score": 0,
            "reasons": ["fallback:default-implementation"],
        }

    tied_labels = [
        label
        for label in CLASSIFICATION_PRECEDENCE
        if (
            scored_by_label.get(label) is not None
            and int(scored_by_label[label]["score"]) == winning_score
        )
    ]
    reasons = list(winner["reasons"]) if winner is not None else []
    if len(tied_labels) > 1:
        reasons.append(
            f"tie-break:{winning_label}>{', '.join(label for label in tied_labels if label != winning_label)}"
        )
    return {"label": winning_label, "score": winning_score, "reasons": reasons}


def _build_required_skills(
    *,
    task_classification: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return deterministic required skills for the classified lane."""

    if task_classification["label"] == "pr_governance":
        required_skills = PR_GOVERNANCE_REQUIRED_SKILLS
    else:
        required_skills = ALWAYS_ON_SKILLS

    required: list[dict[str, Any]] = []
    for skill in required_skills:
        rule = SKILL_RULES_BY_SKILL.get(skill)
        rationale = (
            rule.rationale
            if rule is not None
            else f"Required for the `{task_classification['label']}` lane."
        )
        reasons = (
            ["always-on"]
            if skill in ALWAYS_ON_SKILLS
            else [f"classification:{task_classification['label']}-required"]
        )
        required.append(
            {
                "skill": skill,
                "rationale": rationale,
                "reasons": reasons,
            }
        )
    return required


def _conditional_when_for_skill(*, skill: str, task_classification_label: str) -> str | None:
    """Return a deterministic conditional explanation for supported helper families."""

    if skill in CI_CONDITIONAL_SKILLS and task_classification_label not in {
        "bugfix",
        "pr_governance",
    }:
        return "Enable when a failing CI job, workflow run, or check log is explicitly in scope."
    if skill in PR_GOVERNANCE_CONDITIONAL_SKILLS and task_classification_label != "pr_governance":
        return "Enable when the task explicitly enters PR/review/merge-governance execution."
    if skill in DESIGN_CONDITIONAL_SKILLS and task_classification_label != "design":
        return (
            "Enable when a concrete Figma/design node-id or fidelity requirement becomes explicit."
        )
    if skill in LAUNCH_GOVERNANCE_CONDITIONAL_SKILLS:
        return (
            "Enable when launch-asset work includes explicit design packet metadata, "
            "concrete source anchors, and token/brand governance intent."
        )
    if skill in RESEARCH_CONDITIONAL_SKILLS and task_classification_label != "creative_research":
        return "Enable when the task requires a report/research deliverable or durable knowledge capture."
    return None


def _conditional_when_for_skill_with_design_state(
    *,
    skill: str,
    task_classification_label: str,
    explicit_design_metadata: bool,
    figma_execution_ready: bool,
) -> str | None:
    """Return conditional guidance while preserving fail-closed design semantics."""

    if skill in DESIGN_CONDITIONAL_SKILLS:
        if figma_execution_ready:
            return None
        if task_classification_label == "design" and explicit_design_metadata:
            return (
                "Enable when the design packet becomes execution-ready with concrete "
                "Figma source metadata, node/frame capture, and fidelity intent."
            )
        if task_classification_label == "design":
            return (
                "Enable when a concrete Figma/design node-id or fidelity requirement "
                "becomes explicit."
            )
    if skill in LAUNCH_GOVERNANCE_CONDITIONAL_SKILLS:
        if explicit_design_metadata:
            return None
        return (
            "Enable when launch-asset governance work includes "
            "design packet metadata, source anchors, and explicit token/brand scope."
        )
    return _conditional_when_for_skill(
        skill=skill,
        task_classification_label=task_classification_label,
    )


def _build_conditional_skills(
    *,
    scored: list[dict[str, Any]],
    selected_skills: set[str],
    task_classification: dict[str, Any],
    explicit_design_metadata: bool = False,
    figma_execution_ready: bool = False,
) -> list[dict[str, Any]]:
    """Return deterministic conditional skills for partial or out-of-lane signals."""

    conditional: list[dict[str, Any]] = []
    for item in sorted(scored, key=lambda entry: entry["skill"]):
        if item["skill"] in selected_skills:
            continue
        if not item["reasons"]:
            continue
        when = _conditional_when_for_skill_with_design_state(
            skill=item["skill"],
            task_classification_label=task_classification["label"],
            explicit_design_metadata=explicit_design_metadata,
            figma_execution_ready=figma_execution_ready,
        )
        if when is None:
            continue
        conditional.append(
            {
                "skill": item["skill"],
                "when": when,
                "rationale": item["rationale"],
                "reasons": list(item["reasons"]),
            }
        )
    return conditional


def _has_explicit_design_activation_data(
    *,
    design_source: str | None,
    source_url: str | None,
    file_key_or_workspace: str | None,
    node_id_or_frame_id: str | None,
    target_surface: str | None,
    task_mode: str | None,
    figma_lane_tool: str | None,
    code_native_design_brief_path: str | None,
    explicit_creation_mode: bool,
) -> bool:
    """Return True when the caller explicitly supplied design-lane metadata."""

    return bool(
        design_trigger_present(
            design_source=normalize_optional_text(design_source),
            source_url=normalize_optional_text(source_url),
            file_key_or_workspace=normalize_optional_text(file_key_or_workspace),
            node_id_or_frame_id=normalize_optional_text(node_id_or_frame_id),
            target_surface=normalize_optional_text(target_surface),
            task_mode=normalize_optional_text(task_mode),
            figma_lane_tool=normalize_optional_text(figma_lane_tool),
            code_native_design_brief_path=normalize_optional_text(code_native_design_brief_path),
            explicit_creation_mode=explicit_creation_mode,
        )
    )


def _promote_task_classification_for_explicit_design_metadata(
    *,
    task_classification: dict[str, Any],
    design_source: str,
    explicit_design_metadata: bool,
) -> dict[str, Any]:
    """Promote explicit design packets into the canonical design lane."""

    if not explicit_design_metadata or not design_source:
        return task_classification
    if task_classification["label"] in {
        "pr_governance",
        "creative_research",
        "experiment",
        "review",
        "bugfix",
    }:
        return task_classification
    if task_classification["label"] == "design":
        updated = dict(task_classification)
        updated["reasons"] = [
            *updated["reasons"],
            f"explicit-design-source:{design_source}(+packet)",
        ]
        return updated
    return {
        "label": "design",
        "score": max(int(task_classification["score"]), 1),
        "reasons": [
            *task_classification["reasons"],
            f"explicit-design-source:{design_source}(+packet)",
        ],
    }


def _preserve_triage_lane_for_explicit_design_metadata(
    *,
    task_classification: dict[str, Any],
    normalized_paths: list[str],
    normalized_text: str,
    domain: str,
    explicit_design_metadata: bool,
) -> dict[str, Any]:
    """Keep review/bugfix classification when explicit design packets carry triage intent."""

    if not explicit_design_metadata:
        return task_classification
    if task_classification["label"] in {"pr_governance", "creative_research", "experiment"}:
        return task_classification
    if task_classification["label"] in {"review", "bugfix"}:
        return task_classification

    scored_by_label = {
        rule.label: _score_task_classification(
            rule=rule,
            normalized_paths=normalized_paths,
            normalized_text=normalized_text,
            domain=domain,
        )
        for rule in TASK_CLASSIFICATION_RULES
        if rule.label in {"review", "bugfix"}
    }
    review_score = int(scored_by_label["review"]["score"])
    bugfix_score = int(scored_by_label["bugfix"]["score"])

    if review_score >= 2:
        return {
            "label": "review",
            "score": review_score,
            "reasons": [
                *scored_by_label["review"]["reasons"],
                "explicit-design-metadata:preserve-review",
            ],
        }
    if bugfix_score >= 2:
        return {
            "label": "bugfix",
            "score": bugfix_score,
            "reasons": [
                *scored_by_label["bugfix"]["reasons"],
                "explicit-design-metadata:preserve-bugfix",
            ],
        }
    return task_classification


def route_skills(
    *,
    goal: str,
    task_class: str,
    candidate_paths: list[str] | tuple[str, ...],
    domain: str,
    requested_agents: list[str] | tuple[str, ...] = (),
    design_source: str | None = None,
    source_url: str | None = None,
    file_key_or_workspace: str | None = None,
    node_id_or_frame_id: str | None = None,
    target_surface: str | None = None,
    task_mode: str | None = None,
    figma_lane_tool: str | None = None,
    code_native_design_brief_path: str | None = None,
    explicit_creation_mode: bool = False,
    design_lane_mode: str | None = None,
    design_blockers: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return deterministic skill routing decision with evidence."""

    normalized_paths = repo_relative_paths(candidate_paths)
    normalized_text = normalize_text(goal, task_class, *normalized_paths)
    normalized_request_text = normalize_text(goal, task_class)
    normalized_requested_agents = tuple(normalize_requested_agents(requested_agents))
    normalized_design_source = normalize_optional_text(design_source)
    normalized_source_url = normalize_optional_text(source_url)
    normalized_file_key_or_workspace = normalize_optional_text(file_key_or_workspace)
    normalized_node_id_or_frame_id = normalize_optional_text(node_id_or_frame_id)
    normalized_target_surface = normalize_optional_text(target_surface)
    normalized_task_mode = normalize_optional_text(task_mode)
    normalized_figma_lane_tool = normalize_optional_text(figma_lane_tool)
    normalized_code_native_design_brief_path = normalize_optional_text(
        code_native_design_brief_path
    )
    normalized_design_lane_mode = normalize_optional_text(design_lane_mode)
    normalized_design_blockers = normalize_design_blockers(design_blockers)
    explicit_design_metadata = _has_explicit_design_activation_data(
        design_source=normalized_design_source,
        source_url=normalized_source_url,
        file_key_or_workspace=normalized_file_key_or_workspace,
        node_id_or_frame_id=normalized_node_id_or_frame_id,
        target_surface=normalized_target_surface,
        task_mode=normalized_task_mode,
        figma_lane_tool=normalized_figma_lane_tool,
        code_native_design_brief_path=normalized_code_native_design_brief_path,
        explicit_creation_mode=explicit_creation_mode,
    )
    figma_execution_ready = figma_packet_is_execution_ready(
        design_source=normalized_design_source,
        source_url=normalized_source_url,
        file_key_or_workspace=normalized_file_key_or_workspace,
        node_id_or_frame_id=normalized_node_id_or_frame_id,
        target_surface=normalized_target_surface,
        task_mode=normalized_task_mode,
        figma_lane_tool=normalized_figma_lane_tool,
        code_native_design_brief_path=normalized_code_native_design_brief_path,
        explicit_creation_mode=explicit_creation_mode,
    )
    if normalized_design_lane_mode:
        figma_execution_ready = figma_execution_ready and (
            normalized_design_lane_mode in DESIGN_EXECUTION_TASK_MODES
        )
    if normalized_design_blockers:
        figma_execution_ready = False
    task_classification = _classify_task(
        normalized_paths=normalized_paths,
        normalized_text=normalized_text,
        domain=domain,
    )
    task_classification = _preserve_triage_lane_for_explicit_design_metadata(
        task_classification=task_classification,
        normalized_paths=normalized_paths,
        normalized_text=normalized_text,
        domain=domain,
        explicit_design_metadata=explicit_design_metadata,
    )
    task_classification = _promote_task_classification_for_explicit_design_metadata(
        task_classification=task_classification,
        design_source=normalized_design_source,
        explicit_design_metadata=explicit_design_metadata,
    )
    matched_semantic_groups = _match_semantic_groups(
        normalized_request_text=normalized_request_text
    )
    research_connector_policy = _build_research_connector_policy(
        normalized_request_text=normalized_request_text
    )
    blocked = _build_blocked_patterns(research_connector_policy=research_connector_policy)

    scored = [
        _score_rule(
            rule=rule,
            normalized_paths=normalized_paths,
            normalized_text=normalized_text,
            domain=domain,
        )
        for rule in SKILL_RULES
    ]
    required = _build_required_skills(task_classification=task_classification)
    required_skill_names = {item["skill"] for item in required}

    selected = [
        result
        for result, rule in zip(scored, SKILL_RULES)
        if (result["score"] >= rule.min_score or rule.skill in ALWAYS_ON_SKILLS)
        and (result["skill"] not in DESIGN_CONDITIONAL_SKILLS or figma_execution_ready)
        and (
            result["skill"] not in LAUNCH_GOVERNANCE_CONDITIONAL_SKILLS or explicit_design_metadata
        )
        and result["skill"] not in required_skill_names
    ]

    selected_by_skill = {item["skill"]: item for item in selected}
    privileged_surface_matches = _match_path_prefixes(PRIVILEGED_SURFACE_PREFIXES, normalized_paths)
    for privileged_surface in privileged_surface_matches:
        for skill, boost in PRIVILEGED_SURFACE_SKILL_BUNDLES.items():
            _apply_bundle_reason(
                selected_by_skill=selected_by_skill,
                skill=skill,
                boost=boost,
                reason=f"privileged-surface:{privileged_surface}(+{boost})",
                fallback_rationale=(
                    "Privileged automation and merge-governance surfaces require "
                    "deterministic security skill coverage."
                ),
            )

    for requested_agent in normalized_requested_agents:
        bundle = REQUESTED_AGENT_SKILL_BUNDLES.get(requested_agent, ())
        for bundled_skill in bundle:
            if bundled_skill in required_skill_names:
                continue
            boost = 6 if bundled_skill not in selected_by_skill else 2
            _apply_bundle_reason(
                selected_by_skill=selected_by_skill,
                skill=bundled_skill,
                boost=boost,
                reason=f"requested-agent:{requested_agent}(+{boost})",
                fallback_rationale=(
                    f"Default skill bundle for requested agent `{requested_agent}`."
                ),
            )

    for bundled_skill in TRIAGE_CLASSIFICATION_SKILL_BUNDLES.get(
        str(task_classification["label"]), ()
    ):
        if bundled_skill in required_skill_names:
            continue
        boost = 6 if bundled_skill not in selected_by_skill else 2
        _apply_bundle_reason(
            selected_by_skill=selected_by_skill,
            skill=bundled_skill,
            boost=boost,
            reason=f"classification:{task_classification['label']}(+{boost})",
            fallback_rationale=(
                "Review and bugfix lanes require deterministic triage-helper coverage."
            ),
        )
    _apply_semantic_group_boosts(
        selected_by_skill=selected_by_skill,
        matched_semantic_groups=matched_semantic_groups,
        task_classification=task_classification,
        domain=domain,
        required_skill_names=required_skill_names,
    )
    selected = list(selected_by_skill.values())

    if figma_execution_ready:
        for bundled_skill in DESIGN_CONDITIONAL_SKILLS:
            if bundled_skill in required_skill_names:
                continue
            boost = 6 if bundled_skill not in selected_by_skill else 2
            _apply_bundle_reason(
                selected_by_skill=selected_by_skill,
                skill=bundled_skill,
                boost=boost,
                reason=f"design-metadata:{normalized_design_source}(+{boost})",
                fallback_rationale=(
                    "Explicit design activation metadata upgrades the design lane from advisory to actionable."
                ),
            )
        selected = list(selected_by_skill.values())
    selected.sort(key=lambda item: (-int(item["score"]), item["skill"]))
    conditional = _build_conditional_skills(
        scored=scored,
        selected_skills=required_skill_names.union(item["skill"] for item in selected),
        task_classification=task_classification,
        explicit_design_metadata=explicit_design_metadata,
        figma_execution_ready=figma_execution_ready,
    )

    envelope_mode = resolve_analysis_envelope_mode(normalized_paths)
    selected, conditional = _strip_skills_for_docs_only_envelope(
        envelope_mode=envelope_mode,
        recommended=selected,
        conditional=conditional,
    )
    explanation = _build_explanation_schema(
        required=required,
        recommended=selected,
        conditional=conditional,
        matched_semantic_groups=matched_semantic_groups,
    )

    return {
        "policy_version": ROUTING_POLICY_VERSION,
        "selection_mode": SELECTION_MODE,
        "requested_agents": list(normalized_requested_agents),
        "task_classification": task_classification,
        "envelope_mode_hint": envelope_mode,
        "required": required,
        "recommended": selected,
        "conditional": conditional,
        "blocked": blocked,
        "explanation": explanation,
        "research_connector_policy": research_connector_policy,
    }


def select_recommended_skills(
    *,
    goal: str,
    task_class: str,
    candidate_paths: list[str] | tuple[str, ...],
    domain: str,
    requested_agents: list[str] | tuple[str, ...] = (),
    design_source: str | None = None,
    source_url: str | None = None,
    file_key_or_workspace: str | None = None,
    node_id_or_frame_id: str | None = None,
    target_surface: str | None = None,
    task_mode: str | None = None,
    figma_lane_tool: str | None = None,
    code_native_design_brief_path: str | None = None,
    explicit_creation_mode: bool = False,
    design_lane_mode: str | None = None,
    design_blockers: list[str] | tuple[str, ...] = (),
) -> list[str]:
    """Backward-compatible helper returning only the ordered skill names."""

    decision = route_skills(
        goal=goal,
        task_class=task_class,
        candidate_paths=candidate_paths,
        domain=domain,
        requested_agents=requested_agents,
        design_source=design_source,
        source_url=source_url,
        file_key_or_workspace=file_key_or_workspace,
        node_id_or_frame_id=node_id_or_frame_id,
        target_surface=target_surface,
        task_mode=task_mode,
        figma_lane_tool=figma_lane_tool,
        code_native_design_brief_path=code_native_design_brief_path,
        explicit_creation_mode=explicit_creation_mode,
        design_lane_mode=design_lane_mode,
        design_blockers=design_blockers,
    )
    return flatten_recommended_skills(decision)


def flatten_recommended_skills(decision: dict[str, Any]) -> list[str]:
    """Return the backward-compatible ordered skill slug list.

    RU: Flatten required + recommended без conditional lanes.
    EN: Flatten required + recommended while excluding conditional suggestions.
    """

    ordered: list[str] = []
    for bucket in ("required", "recommended"):
        for item in decision.get(bucket, []):
            skill = item["skill"]
            if skill not in ordered:
                ordered.append(skill)
    return ordered
