"""Load agent name sets from AGENT_INVENTORY, AGENT_CAPABILITY_MATRIX, and routing graph.

Used by check_agent_consistency.py to enforce: routing ⊆ inventory ⊆ capability.
Canonical paths: docs/orchestration/AGENT_INVENTORY.md, AGENT_CAPABILITY_MATRIX.md, AGENT_ROUTING_GRAPH.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = REPO_ROOT / "docs" / "orchestration" / "AGENT_INVENTORY.md"
CAPABILITY_PATH = REPO_ROOT / "docs" / "orchestration" / "AGENT_CAPABILITY_MATRIX.md"

_TABLE_ROW_RE = re.compile(r"^\|\s*(?P<cols>.+?)\s*\|\s*$")

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
    """Three agent sets: inventory (reference), capability (matrix), routing (graph)."""

    inventory: Set[str]
    capability: Set[str]
    routing: Set[str]


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
    """Extract agent slugs from AGENT_INVENTORY.md (all tables with Agent/Type column)."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing inventory file: {path}")
    text = path.read_text(encoding="utf-8")
    agents: Set[str] = set()
    for line in text.splitlines():
        cols = _split_md_row(line)
        if not cols:
            continue
        if cols[0].lower() in {"agent", "type"}:
            continue
        candidate = _normalize_slug(cols[0])
        if candidate and re.fullmatch(r"[a-z0-9][a-z0-9\-]*", candidate):
            agents.add(candidate)
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


def load_agent_sets() -> AgentConsistencySets:
    """Load all three sets. Invariant: routing ⊆ inventory ⊆ capability."""
    inventory = load_inventory_agents()
    capability = load_capability_agents()
    routing = load_routing_agents()
    return AgentConsistencySets(inventory=inventory, capability=capability, routing=routing)
