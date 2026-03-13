"""Shared orchestration context-pack helpers.

RU: Общие helper-утилиты для deterministic context packs и path routing.
EN: Shared helpers for deterministic context packs and path-based routing.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CORE_CONTEXT_FILES = (
    "AGENTS.md",
    "RUNBOOK_AGENT.md",
)

ORCHESTRATION_CONTEXT_FILES = (
    "docs/orchestration/workflow.md",
    "docs/orchestration/AGENT_CONTEXT_MAP.md",
    "docs/orchestration/AGENT_CAPABILITY_MATRIX.md",
    "docs/orchestration/AGENT_ROUTING_GRAPH.md",
    "docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md",
)

TASK_CLASS_DOMAIN_HINTS: dict[str, str] = {
    "backend api": "backend",
    "web ui": "frontend",
    "ios ui": "ios",
    "infrastructure": "infra",
    "security": "security",
    "ai / ml": "ml",
    "ai/ml": "ml",
    "computer vision": "cv",
    "cv": "cv",
    "design": "design",
    "documentation": "docs",
    "research": "research",
    "safety / philosophy / logic": "safety",
    "qa": "qa",
    "release": "release",
    "wellness": "wellness",
    "business": "business",
    "orchestration": "orchestration",
    "agent enablement": "orchestration",
}

CV_ROUTABLE_TASK_CLASSES = frozenset({"ai / ml", "ai/ml", "computer vision", "cv"})

CV_PATH_DOMAIN_HINTS: tuple[str, ...] = (
    ".cursor/agents/cv-agent.md",
    "docs/orchestration/cv_",
    "docs/orchestration/contracts/cv_",
    "core/insight/cv_",
    "core/rag/cv_",
    "core/cv_",
    "core/cv/",
    "providers/cv_",
    "providers/cv/",
    "tests/test_cv_",
)

CV_GOAL_PHRASES: tuple[str, ...] = (
    "computer vision",
    "food image",
    "food images",
    "food photo",
    "food photos",
    "image recognition",
    "photo recognition",
    "vision model",
    "vision eval",
)

PATH_DOMAIN_HINTS: tuple[tuple[str, str], ...] = (
    (".cursor/agents/", "orchestration"),
    ("scripts/", "orchestration"),
    ("docs/orchestration/", "orchestration"),
    ("docs/review/", "docs"),
    ("docs/", "docs"),
    ("frontend/", "frontend"),
    ("ios/", "ios"),
    ("providers/", "ml"),
    ("core/", "backend"),
    ("app/", "backend"),
    ("tests/", "qa"),
)


def normalize_text(*parts: str) -> str:
    """Normalize free text for deterministic lexical matching."""

    raw = " ".join(part.strip().lower() for part in parts if part.strip())
    for token in ("/", "_", "-", ".", ":", "(", ")", ","):
        raw = raw.replace(token, " ")
    return " ".join(raw.split())


def normalize_repo_path(raw_path: str | Path) -> str:
    """Return repo-relative normalized POSIX path."""

    candidate = Path(raw_path)
    if candidate.is_absolute():
        absolute_candidate = candidate.expanduser()
        resolved = absolute_candidate.resolve()
        try:
            return resolved.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return absolute_candidate.as_posix()

    normalized = candidate.as_posix()
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def repo_relative_paths(raw_paths: list[str] | tuple[str, ...]) -> list[str]:
    """Normalize and sort unique repo-relative paths."""

    seen = {normalize_repo_path(path) for path in raw_paths if str(path).strip()}
    return sorted(seen)


def find_nearest_agents_file(raw_path: str | Path) -> str | None:
    """Return nearest scoped AGENTS.md for a repo-relative path."""

    rel_path = normalize_repo_path(raw_path)
    if Path(rel_path).is_absolute():
        return None
    candidate = REPO_ROOT / rel_path
    current = candidate if candidate.is_dir() else candidate.parent

    while True:
        maybe_agents = current / "AGENTS.md"
        if maybe_agents.is_file():
            return maybe_agents.relative_to(REPO_ROOT).as_posix()
        if current == REPO_ROOT or current.parent == current:
            return None
        current = current.parent


def collect_scoped_agents(raw_paths: list[str] | tuple[str, ...]) -> list[str]:
    """Collect nearest scoped AGENTS files for candidate paths."""

    agents = {
        agents_path
        for path in repo_relative_paths(raw_paths)
        if (agents_path := find_nearest_agents_file(path)) is not None
    }
    return sorted(agents)


def collect_context_pack(
    raw_paths: list[str] | tuple[str, ...],
    *,
    include_orchestration: bool = True,
) -> list[str]:
    """Build deterministic context-pack file list for a task."""

    context = set(CORE_CONTEXT_FILES)
    context.update(collect_scoped_agents(raw_paths))
    if include_orchestration:
        context.update(ORCHESTRATION_CONTEXT_FILES)
    return sorted(context)


def resolve_domain(
    *,
    task_class: str,
    candidate_paths: list[str] | tuple[str, ...],
    goal: str | None = None,
) -> str:
    """Resolve dominant domain from task_class and candidate paths."""

    normalized_paths = repo_relative_paths(candidate_paths)
    normalized_goal = normalize_text(goal or "")
    normalized_task_class = task_class.strip().lower()

    if _has_cv_path_hint(normalized_paths):
        return "cv"
    if (
        normalized_task_class in TASK_CLASS_DOMAIN_HINTS
        and normalized_task_class not in CV_ROUTABLE_TASK_CLASSES
    ):
        return TASK_CLASS_DOMAIN_HINTS[normalized_task_class]
    if _is_cv_goal_hint(normalized_goal):
        return "cv"
    if normalized_task_class in TASK_CLASS_DOMAIN_HINTS:
        return TASK_CLASS_DOMAIN_HINTS[normalized_task_class]

    counts: dict[str, int] = {}
    for path in normalized_paths:
        lowered_path = path.lower()
        for prefix, domain in PATH_DOMAIN_HINTS:
            lowered_prefix = prefix.lower()
            if lowered_path == lowered_prefix.rstrip("/") or lowered_path.startswith(
                lowered_prefix
            ):
                counts[domain] = counts.get(domain, 0) + 1
                break

    if counts:
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return "orchestration"


def _has_cv_path_hint(normalized_paths: list[str] | tuple[str, ...]) -> bool:
    """Return True when candidate paths clearly belong to the CV routing seam."""

    for path in normalized_paths:
        lowered_path = path.lower()
        for prefix in CV_PATH_DOMAIN_HINTS:
            if lowered_path == prefix.rstrip("/") or lowered_path.startswith(prefix):
                return True
    return False


def _is_cv_goal_hint(normalized_goal: str) -> bool:
    """Return True when goal text uses boundary-safe CV wording."""

    if re.search(r"(?<!\w)cv(?!\w)", normalized_goal):
        return True
    return any(
        re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalized_goal)
        for phrase in CV_GOAL_PHRASES
    )


def compute_task_packet_id(
    *,
    goal: str,
    task_class: str,
    domain: str,
    candidate_paths: list[str] | tuple[str, ...],
) -> str:
    """Return deterministic short task packet id."""

    payload = "\n".join(
        [
            goal.strip(),
            task_class.strip(),
            domain.strip(),
            *repo_relative_paths(candidate_paths),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
