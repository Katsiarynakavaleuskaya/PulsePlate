"""Deterministic skill routing helpers for coordinator bootstrap.

RU: Подбирает project-fit skills для task packet без ручного вызова.
EN: Selects project-fit skills for task packets without manual invocation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scripts.orchestration.context_pack import repo_relative_paths

ROUTING_POLICY_VERSION = "2026-03-08"
SELECTION_MODE = "deterministic-weighted"

ALWAYS_ON_SKILLS: tuple[str, ...] = ("pulseplate-workflow",)

SCRAPING_BLOCK_PATTERNS: tuple[tuple[str, str], ...] = (
    ("tiktok", "TikTok scraping is not an approved default for PulsePlate."),
    ("google maps", "Google Maps scraping is not approved for the current repo."),
    ("scrape any site", "Universal scraping is out of scope for PulsePlate."),
    ("entire internet", "Broad internet scraping is outside project-fit boundaries."),
)


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
    negative_keywords: tuple[str, ...] = ()


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
        domain_weights={"docs": 2, "orchestration": 2, "research": 1},
        path_prefixes=("docs/", "README.md", ".cursor/agents/"),
        keywords=("doc", "docs", "runbook", "policy", "readme", "audit"),
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
        domain_weights={"backend": 1, "frontend": 1, "orchestration": 1, "qa": 2},
        path_prefixes=("app/", "core/", "frontend/", "tests/", "scripts/", "docs/orchestration/"),
        keywords=("test", "verify", "gate", "coverage", "diff-cover", "lint", "mypy"),
    ),
    SkillRule(
        skill="pulseplate-guards",
        category="repo-tracked",
        rationale="Handle architecture guards, fail-closed policy checks, and security-oriented invariants.",
        min_score=3,
        domain_weights={"security": 2, "qa": 2, "orchestration": 1},
        path_prefixes=("app/security/", "tests/guards/", "scripts/orchestration/"),
        keywords=("guard", "policy", "invariant", "fail-closed", "rate limit", "quota"),
    ),
    SkillRule(
        skill="pulseplate-backend-endpoints",
        category="repo-tracked",
        rationale="Backend/API tasks should follow endpoint skill constraints and deterministic tests.",
        min_score=3,
        domain_weights={"backend": 3, "ml": 2},
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
        min_score=5,
        domain_weights={"qa": 1, "orchestration": 1},
        keywords=("review", "code review"),
    ),
    SkillRule(
        skill="ci-fix",
        category="global",
        rationale="CI failures should trigger the dedicated CI remediation workflow.",
        min_score=5,
        domain_weights={"qa": 2},
        keywords=("ci", "github actions", "workflow run", "checks", "failing check"),
    ),
    SkillRule(
        skill="gh-fix-ci",
        category="global",
        rationale="GitHub-based CI debugging is useful when the task explicitly references PR checks.",
        min_score=6,
        domain_weights={"qa": 1},
        keywords=("gh", "github actions", "pr checks", "ci log", "workflow run"),
    ),
    SkillRule(
        skill="create-pr",
        category="global",
        rationale="PR preparation should use the dedicated PR packaging workflow.",
        min_score=5,
        domain_weights={"orchestration": 1, "docs": 1},
        keywords=("open pr", "create pr", "pull request", "prepare pr"),
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
        min_score=5,
        domain_weights={"release": 2, "docs": 1},
        keywords=("release notes", "changelog"),
    ),
    SkillRule(
        skill="openai-docs",
        category="global",
        rationale="OpenAI product/API questions should use official docs-first guidance.",
        min_score=5,
        domain_weights={"ml": 1},
        keywords=("openai", "chatgpt", "responses api", "realtime api", "codex api"),
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
        skill="linear",
        category="global",
        rationale="Linear-linked work should use the dedicated issue/project integration skill.",
        min_score=5,
        domain_weights={"business": 1, "orchestration": 1},
        keywords=("linear", "ticket", "issue", "project"),
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
        domain_weights={"security": 3},
        keywords=("security", "hardening", "appsec"),
    ),
    SkillRule(
        skill="security-threat-model",
        category="global",
        rationale="Threat modeling should be explicit, not implicit.",
        min_score=6,
        domain_weights={"security": 3},
        keywords=("threat model", "abuse path", "trust boundary"),
    ),
)


def _normalize_text(goal: str, task_class: str, normalized_paths: list[str]) -> str:
    """Return one normalized string for lexical matching."""

    raw = " ".join([goal.strip(), task_class.strip(), *normalized_paths]).lower()
    for token in ("/", "_", "-", ".", ":", "(", ")", ","):
        raw = raw.replace(token, " ")
    return " ".join(raw.split())


def _has_prefix(path: str, prefix: str) -> bool:
    return path == prefix.rstrip("/") or path.startswith(prefix)


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

    matched_prefixes = [
        prefix
        for prefix in rule.path_prefixes
        if any(_has_prefix(path, prefix) for path in normalized_paths)
    ]
    if matched_prefixes:
        prefix_score = len(matched_prefixes) * 2
        score += prefix_score
        reasons.append(f"path:{', '.join(matched_prefixes)}(+{prefix_score})")

    matched_keywords = [keyword for keyword in rule.keywords if keyword in normalized_text]
    if matched_keywords:
        keyword_score = min(len(matched_keywords), 3) * 2
        score += keyword_score
        reasons.append(f"lexeme:{', '.join(matched_keywords[:3])}(+{keyword_score})")

    matched_negative = [keyword for keyword in rule.negative_keywords if keyword in normalized_text]
    if matched_negative:
        penalty = len(matched_negative) * 2
        score -= penalty
        reasons.append(f"negative:{', '.join(matched_negative[:3])}(-{penalty})")

    return {
        "skill": rule.skill,
        "score": score,
        "category": rule.category,
        "rationale": rule.rationale,
        "reasons": reasons,
    }


def route_skills(
    *,
    goal: str,
    task_class: str,
    candidate_paths: list[str] | tuple[str, ...],
    domain: str,
) -> dict[str, Any]:
    """Return deterministic skill routing decision with evidence."""

    normalized_paths = repo_relative_paths(candidate_paths)
    normalized_text = _normalize_text(
        goal=goal, task_class=task_class, normalized_paths=normalized_paths
    )

    blocked = [
        {"label": pattern, "reason": reason}
        for pattern, reason in SCRAPING_BLOCK_PATTERNS
        if pattern in normalized_text
    ]

    scored = [
        _score_rule(
            rule=rule,
            normalized_paths=normalized_paths,
            normalized_text=normalized_text,
            domain=domain,
        )
        for rule in SKILL_RULES
    ]
    selected = [
        result
        for result, rule in zip(scored, SKILL_RULES)
        if result["score"] >= rule.min_score or rule.skill in ALWAYS_ON_SKILLS
    ]
    selected.sort(key=lambda item: (-int(item["score"]), item["skill"]))

    return {
        "policy_version": ROUTING_POLICY_VERSION,
        "selection_mode": SELECTION_MODE,
        "recommended": selected,
        "blocked": blocked,
    }


def select_recommended_skills(
    *,
    goal: str,
    task_class: str,
    candidate_paths: list[str] | tuple[str, ...],
    domain: str,
) -> list[str]:
    """Backward-compatible helper returning only the ordered skill names."""

    decision = route_skills(
        goal=goal,
        task_class=task_class,
        candidate_paths=candidate_paths,
        domain=domain,
    )
    return [item["skill"] for item in decision["recommended"]]
