"""Load agent name sets from docs, routing graph, and actual agent files.

Used by consistency guards to enforce:
- routing ⊆ inventory
- index == actual agent files
- inventory ⊆ capability
- inventory ⊆ context map
- routable agents must exist in docs layers or explicit allowlist
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = REPO_ROOT / "docs" / "orchestration" / "AGENT_INVENTORY.md"
CAPABILITY_PATH = REPO_ROOT / "docs" / "orchestration" / "AGENT_CAPABILITY_MATRIX.md"
INDEX_PATH = REPO_ROOT / "docs" / "agents" / "index.md"
AGENTS_DIR = REPO_ROOT / ".cursor" / "agents"
NON_ROUTABLE_PATH = REPO_ROOT / "docs" / "orchestration" / "AGENT_NON_ROUTABLE_SPECIALISTS.md"
CONTEXT_MAP_PATH = REPO_ROOT / "docs" / "orchestration" / "AGENT_CONTEXT_MAP.md"
SYSTEM_AGENT_EXCEPTIONS = frozenset({"generalpurpose", "explore", "shell", "ci-watcher"})

_TABLE_ROW_RE = re.compile(r"^\|\s*(?P<cols>.+?)\s*\|\s*$")
_AGENT_NAME_RE = re.compile(r"^name:\s*(?P<name>[a-z0-9][a-z0-9\-]*)\s*$")

# Map capability matrix first-column display names to canonical slugs (inventory/routing).
_CAPABILITY_DISPLAY_TO_SLUG: dict[str, str] = {
    "coordinator": "agent-coordinator",
    "architecture": "architecture-specialist",
    "bug hunter": "bug-hunter",
    "ai innovation": "ai-innovation-specialist",
    "security": "security-auditor",
    "marketing": "marketing-strategist",
    "creative designer": "creative-designer",
    "philosophy agent": "philosophy-agent",
    "logic agent": "logic-agent",
    "bayesian / uq agent": "bayesian-uq-agent",
    "rag systems agent": "rag-systems-agent",
    "web research agent": "web-research-agent",
    "cv agent": "cv-agent",
    "ai app architect": "ai-app-architect",
    "data scientist": "data-scientist-agent",
    "ml engineer": "ml-engineer-agent",
    "nutritionist agent": "nutritionist-agent",
    "cbt psychologist agent": "cbt-psychologist-agent",
    "epistemology / discovery agent": "epistemology-discovery-agent",
    "physics / sensor agent": "physics-sensor-agent",
}


@dataclass(frozen=True)
class AgentConsistencySets:
    """Canonical agent sets used by repo guards."""

    files: Set[str]
    index: Set[str]
    inventory: Set[str]
    capability: Set[str]
    context: Set[str]
    routing: Set[str]
    non_routable: Set[str]
    system_exceptions: Set[str]


def _split_md_row(line: str) -> Tuple[str, ...]:
    m = _TABLE_ROW_RE.match(line.strip())
    if not m:
        return ()
    parts = [p.strip() for p in m.group("cols").split("|")]
    return tuple(parts)


def _normalize_slug(token: str) -> str:
    return token.strip().strip("*").lower()


def _is_table_delimiter_row(line: str) -> bool:
    if not line.strip().startswith("|"):
        return False
    core = line.replace("|", "").strip()
    return bool(core and set(core) <= {"-", ":", " "})


def load_inventory_agents(path: Path = INVENTORY_PATH) -> Set[str]:
    """Extract canonical agent slugs from AGENT_INVENTORY.md.

    Utility `mcp_task` rows under the `Type` table are not canonical Cursor agents
    and are intentionally excluded from the consistency set.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Missing inventory file: {path}")
    text = path.read_text(encoding="utf-8")
    agents: Set[str] = set()
    in_agent_table = False
    for line in text.splitlines():
        cols = _split_md_row(line)
        if not cols:
            continue
        header = cols[0].lower()
        if header == "agent":
            in_agent_table = True
            continue
        if header == "type":
            in_agent_table = False
            continue
        if not in_agent_table or _is_table_delimiter_row(line):
            continue
        candidate = _normalize_slug(cols[0])
        if candidate and re.fullmatch(r"[a-z0-9][a-z0-9\-]*", candidate):
            agents.add(candidate)
    return agents


def load_agent_file_slugs(path: Path = AGENTS_DIR) -> Set[str]:
    """Extract canonical slugs from frontmatter-backed agent docs only."""

    if not path.is_dir():
        raise FileNotFoundError(f"Missing agent directory: {path}")

    agents: Set[str] = set()
    for agent_doc in path.glob("*.md"):
        if agent_doc.name == "AGENTS.md":
            continue
        slug = _load_agent_frontmatter_name(agent_doc)
        if slug:
            agents.add(slug)
    return agents


def _load_agent_frontmatter_name(path: Path) -> str | None:
    """Return canonical slug from agent frontmatter or None for non-agent docs."""

    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            return None
        match = _AGENT_NAME_RE.match(stripped)
        if match:
            return match.group("name")
    return None


def load_index_agents(path: Path = INDEX_PATH) -> Set[str]:
    """Extract agent slugs from docs/agents/index.md first column."""

    if not path.is_file():
        raise FileNotFoundError(f"Missing agent index: {path}")
    text = path.read_text(encoding="utf-8")
    agents: Set[str] = set()
    header_found = False
    for line in text.splitlines():
        cols = _split_md_row(line)
        if not cols:
            if header_found:
                break
            continue
        first = cols[0].strip().lower()
        if first == "agent":
            header_found = True
            continue
        if header_found and _is_table_delimiter_row(line):
            continue
        if not header_found:
            continue
        slug = _normalize_slug(cols[0])
        if slug:
            agents.add(slug)
    return agents


def _capability_display_to_slug(display: str) -> str:
    """Map capability matrix first-column value to canonical slug."""
    normalized = display.strip().strip("*").lower()
    # Extract English part from "RU (`English`)"
    if "(`" in normalized and "`)" in normalized:
        idx = normalized.find("(`") + 2
        end = normalized.find("`)", idx)
        if end != -1:
            normalized = normalized[idx:end].strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return _CAPABILITY_DISPLAY_TO_SLUG.get(normalized, normalized.replace(" ", "-"))


def load_capability_agents(path: Path = CAPABILITY_PATH) -> Set[str]:
    """Extract agent slugs from AGENT_CAPABILITY_MATRIX.md (first table, Agent column)."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing capability matrix: {path}")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    agents: Set[str] = set()
    header_found = False
    for line in lines:
        cols = _split_md_row(line)
        if not cols:
            if header_found:
                break
            continue
        first_lower = cols[0].strip().lower()
        if first_lower == "agent":
            header_found = True
            continue
        if header_found and _is_table_delimiter_row(line):
            continue
        if not header_found:
            continue
        display = cols[0].strip().strip("*")
        if not display:
            continue
        slug = _capability_display_to_slug(display)
        if slug:
            agents.add(slug)
    return agents


def load_routing_agents() -> Set[str]:
    """Extract agent slugs from routing graph (primary, secondary, reviewer) via existing loader."""
    from scripts.orchestration.routing_graph_loader import load_routing_graph

    routing = load_routing_graph()
    out: Set[str] = set()
    for dr in routing.values():
        out.add(dr.primary.lower())
        if dr.secondary:
            out.add(dr.secondary.lower())
        out.add(dr.reviewer.lower())
    return out


def load_non_routable_agents(path: Path = NON_ROUTABLE_PATH) -> Set[str]:
    """Extract explicit non-routable agent slugs from markdown list."""

    if not path.is_file():
        raise FileNotFoundError(f"Missing non-routable allowlist: {path}")
    out: Set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- `") and stripped.endswith("`"):
            out.add(stripped[3:-1])
    return out


def load_context_agents(path: Path = CONTEXT_MAP_PATH) -> Set[str]:
    """Extract canonical agent slugs from AGENT_CONTEXT_MAP.md headings."""

    if not path.is_file():
        raise FileNotFoundError(f"Missing context map: {path}")

    agents: Set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^### .*?`(?P<slug>[a-z0-9][a-z0-9\-]*)`", line.strip())
        if match:
            agents.add(match.group("slug"))
    return agents


def load_agent_sets() -> AgentConsistencySets:
    """Load canonical agent sets for consistency checks."""
    files = load_agent_file_slugs()
    index = load_index_agents()
    inventory = load_inventory_agents()
    capability = load_capability_agents()
    context = load_context_agents()
    routing = load_routing_agents()
    non_routable = load_non_routable_agents()
    return AgentConsistencySets(
        files=files,
        index=index,
        inventory=inventory,
        capability=capability,
        context=context,
        routing=routing,
        non_routable=non_routable,
        system_exceptions=set(SYSTEM_AGENT_EXCEPTIONS),
    )
