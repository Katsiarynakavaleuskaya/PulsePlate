"""Deterministic skill routing helpers for coordinator bootstrap.

RU: Подбирает project-fit skills для task packet без ручного вызова.
EN: Selects project-fit skills for task packets without manual invocation.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Any

from scripts.orchestration.context_pack import normalize_text, repo_relative_paths
from scripts.orchestration.requested_agents import normalize_requested_agents

ROUTING_POLICY_VERSION = "2026-03-27"
SELECTION_MODE = "deterministic-weighted"
FIGMA_DESIGN_SOURCES: frozenset[str] = frozenset({"figma_design", "figma_make"})
DESIGN_ACTIVATION_SOURCES: frozenset[str] = frozenset(
    {
        "code_native_brief",
        "figma_design",
        "figma_make",
        "notion",
        "airweave",
        "penpot",
        "stitch_reference",
    }
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
RESEARCH_CONDITIONAL_SKILLS: frozenset[str] = frozenset(
    {
        "pulseplate-ai-reports",
        "notion-research-documentation",
        "notion-knowledge-capture",
        "linear",
    }
)
CI_CONDITIONAL_SKILLS: frozenset[str] = frozenset({"ci-fix", "gh-fix-ci"})

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

SCRAPING_BLOCK_PATTERNS: tuple[tuple[str, str], ...] = (
    ("tiktok", "TikTok scraping is not an approved default for PulsePlate."),
    ("google maps", "Google Maps scraping is not approved for the current repo."),
    ("scrape any site", "Universal scraping is out of scope for PulsePlate."),
    ("entire internet", "Broad internet scraping is outside project-fit boundaries."),
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
        domain_weights={"docs": 2, "orchestration": 2, "research": 1, "ml": 1, "cv": 1},
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
        min_score=6,
        domain_weights={"qa": 1},
        keywords=("gh", "github actions", "pr checks", "ci log", "workflow run"),
    ),
    SkillRule(
        skill="create-pr",
        category="global",
        rationale="PR preparation should use the dedicated PR packaging workflow.",
        min_score=3,
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
        min_score=4,
        domain_weights={"release": 2, "docs": 1},
        keywords=("release notes", "changelog"),
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
        keywords=("review comment", "review thread", "address comments", "github comment"),
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
    if skill in RESEARCH_CONDITIONAL_SKILLS and task_classification_label != "creative_research":
        return "Enable when the task requires a report/research deliverable or durable knowledge capture."
    return None


def _build_conditional_skills(
    *,
    scored: list[dict[str, Any]],
    selected_skills: set[str],
    task_classification: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return deterministic conditional skills for partial or out-of-lane signals."""

    conditional: list[dict[str, Any]] = []
    for item in sorted(scored, key=lambda entry: entry["skill"]):
        if item["skill"] in selected_skills:
            continue
        if not item["reasons"]:
            continue
        when = _conditional_when_for_skill(
            skill=item["skill"],
            task_classification_label=task_classification["label"],
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


def _normalize_optional_text(value: str | None) -> str:
    """Return a stripped optional string."""

    if value is None:
        return ""
    return value.strip()


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

    return any(
        (
            _normalize_optional_text(design_source),
            _normalize_optional_text(source_url),
            _normalize_optional_text(file_key_or_workspace),
            _normalize_optional_text(node_id_or_frame_id),
            _normalize_optional_text(target_surface),
            _normalize_optional_text(task_mode),
            _normalize_optional_text(figma_lane_tool),
            _normalize_optional_text(code_native_design_brief_path),
            explicit_creation_mode,
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
    if task_classification["label"] in {"pr_governance", "creative_research", "experiment"}:
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
) -> dict[str, Any]:
    """Return deterministic skill routing decision with evidence."""

    normalized_paths = repo_relative_paths(candidate_paths)
    normalized_text = normalize_text(goal, task_class, *normalized_paths)
    normalized_request_text = normalize_text(goal, task_class)
    normalized_requested_agents = tuple(normalize_requested_agents(requested_agents))
    normalized_design_source = _normalize_optional_text(design_source)
    explicit_design_metadata = _has_explicit_design_activation_data(
        design_source=design_source,
        source_url=source_url,
        file_key_or_workspace=file_key_or_workspace,
        node_id_or_frame_id=node_id_or_frame_id,
        target_surface=target_surface,
        task_mode=task_mode,
        figma_lane_tool=figma_lane_tool,
        code_native_design_brief_path=code_native_design_brief_path,
        explicit_creation_mode=explicit_creation_mode,
    )
    task_classification = _classify_task(
        normalized_paths=normalized_paths,
        normalized_text=normalized_text,
        domain=domain,
    )
    task_classification = _promote_task_classification_for_explicit_design_metadata(
        task_classification=task_classification,
        design_source=normalized_design_source,
        explicit_design_metadata=explicit_design_metadata,
    )

    blocked = [
        {"label": pattern, "reason": reason, "kind": "pattern"}
        for pattern, reason in SCRAPING_BLOCK_PATTERNS
        if pattern in normalized_request_text
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
    required = _build_required_skills(task_classification=task_classification)
    required_skill_names = {item["skill"] for item in required}

    selected = [
        result
        for result, rule in zip(scored, SKILL_RULES)
        if (result["score"] >= rule.min_score or rule.skill in ALWAYS_ON_SKILLS)
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

    selected = list(selected_by_skill.values())
    if explicit_design_metadata and normalized_design_source in DESIGN_ACTIVATION_SOURCES:
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
    )

    return {
        "policy_version": ROUTING_POLICY_VERSION,
        "selection_mode": SELECTION_MODE,
        "requested_agents": list(normalized_requested_agents),
        "task_classification": task_classification,
        "required": required,
        "recommended": selected,
        "conditional": conditional,
        "blocked": blocked,
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
