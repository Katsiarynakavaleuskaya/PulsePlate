#!/usr/bin/env python3
"""Qoder dispatch manifest generator.

Reads a governance packet's role order (or explicit CLI role slugs), loads
agent definitions from ``.cursor/agents/<slug>.md``, resolves context maps
and routing metadata, and outputs a JSON dispatch manifest suitable for
Qoder multi-agent orchestration.

Usage examples::

    # From a governance packet
    python3 scripts/orchestration/qoder_dispatch_bridge.py \\
        --packet docs/orchestration/packets/my_task.md

    # Explicit roles
    python3 scripts/orchestration/qoder_dispatch_bridge.py \\
        --roles agent-coordinator architecture-specialist philosophy-agent \\
        --mode analysis --pretty
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Optional imports with graceful fallback
# ---------------------------------------------------------------------------

_routing_graph: Optional[Dict[str, Any]] = None
_routing_loader_available = False

try:
    from scripts.orchestration.routing_graph_loader import load_routing_graph

    _routing_loader_available = True
except Exception:  # pragma: no cover – optional dependency
    _routing_loader_available = False


def _ensure_routing_graph() -> Dict[str, Any]:
    """Lazy-load the routing graph, caching the result."""
    global _routing_graph
    if _routing_graph is not None:
        return _routing_graph

    if _routing_loader_available:
        try:
            _routing_graph = {
                domain: {
                    "cluster": route.cluster,
                    "primary": route.primary,
                    "secondary": route.secondary,
                    "reviewer": route.reviewer,
                }
                for domain, route in load_routing_graph().items()
            }
            return _routing_graph
        except Exception:
            _routing_graph = None  # fall through to markdown fallback

    # Fallback: parse the markdown table directly
    _routing_graph = _parse_routing_graph_fallback()
    return _routing_graph


def _primary_slugs_from_routing(routing: Dict[str, Any]) -> set[str]:
    """Collect agent slugs that appear as domain primary or secondary."""
    slugs: set[str] = set()
    for route_info in routing.values():
        for key in ("primary", "secondary"):
            agent = route_info.get(key)
            if not agent:
                continue
            slug = str(agent).strip()
            if slug:
                slugs.add(slug)
    return slugs


def _reviewer_slugs_from_routing(routing: Dict[str, Any]) -> set[str]:
    """Collect agent slugs that appear in the ``reviewer`` column."""
    slugs: set[str] = set()
    for route_info in routing.values():
        agent = route_info.get("reviewer")
        if not agent:
            continue
        slug = str(agent).strip()
        if slug:
            slugs.add(slug)
    return slugs


def _dispatch_is_reviewer_slot(
    slug: str,
    order_idx: int,
    total_roles: int,
    *,
    primary_slugs: set[str],
    reviewer_slugs: set[str],
) -> bool:
    """Infer whether this position should use Qoder ``CodeReview`` typing.

    - Any graph **reviewer** that never appears as primary/secondary is always
      a reviewer slot (e.g. ``architecture-specialist``).
    - Agents that are both primary-capable and reviewers are treated as
      reviewers only when they are the **last** role in a multi-role dispatch
      (typical merge / security review tail), not when solo lead.
    """
    # Explicit routing-graph reviewer (not primary-capable) -> always reviewer
    if slug in reviewer_slugs and slug not in primary_slugs:
        return True

    # Name-based detection: slugs containing auditor/reviewer/review keywords
    _REVIEWER_KEYWORDS = ("auditor", "reviewer", "review")
    is_reviewer_by_name = any(kw in slug for kw in _REVIEWER_KEYWORDS)

    # Graph-aware or name-based reviewer in tail position
    if slug in reviewer_slugs or is_reviewer_by_name:
        return total_roles >= 2 and order_idx == total_roles and order_idx > 1

    return False


def _depends_on_previous(
    slug: str,
    agent_def: Dict[str, Any],
    previous_slug: Optional[str],
    chained_successors: Optional[set[str]] = None,
) -> bool:
    """Return whether this dispatch item must wait for the previous item."""
    if previous_slug is None:
        return False
    if chained_successors and slug in chained_successors:
        return True
    if agent_def.get("depends_on_previous"):
        return True
    # The mandatory post-open review pass is sequential:
    # qa-engineer-agent -> bug-hunter -> security-auditor.
    if slug == "bug-hunter":
        return previous_slug in {"qa-engineer-agent", "bug-hunter"}
    if slug == "security-auditor":
        return previous_slug in {"bug-hunter", "security-auditor"}
    return False


def _parse_routing_graph_fallback() -> Dict[str, Any]:
    """Standalone parser for AGENT_ROUTING_GRAPH.md § 4 table."""
    graph_path = REPO_ROOT / "docs" / "orchestration" / "AGENT_ROUTING_GRAPH.md"
    if not graph_path.is_file():
        return {}

    lines = graph_path.read_text(encoding="utf-8").splitlines()
    routes: Dict[str, Any] = {}
    in_section = False
    header_found = False

    for line in lines:
        stripped = line.strip()
        if "4. Domains" in stripped and stripped.startswith("##"):
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if not in_section:
            continue
        if not stripped.startswith("|"):
            continue
        # Skip delimiter rows
        content = stripped.replace("|", "").strip()
        if content and set(content) <= {"-", ":", " "}:
            header_found = True
            continue
        if not header_found:
            # This is the header row – skip it
            header_found = False
            continue
        cols = [c.strip() for c in stripped.split("|") if c.strip()]
        if len(cols) < 5:
            continue
        domain, cluster, primary, secondary, reviewer = (
            cols[0].lower(),
            cols[1],
            cols[2],
            cols[3],
            cols[4],
        )
        if domain.startswith("-"):
            continue
        routes[domain] = {
            "cluster": cluster,
            "primary": primary,
            "secondary": secondary or None,
            "reviewer": reviewer,
        }

    return routes


# ---------------------------------------------------------------------------
# YAML frontmatter parser (no hard dependency on PyYAML)
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from agent markdown.

    Returns (metadata_dict, markdown_body).
    Falls back to manual key:value parsing if ``yaml`` is unavailable.
    """
    if not text.startswith("---"):
        return {}, text

    end_idx = text.find("---", 3)
    if end_idx == -1:
        return {}, text

    raw_fm = text[3:end_idx].strip()
    body = text[end_idx + 3 :].strip()

    # Try PyYAML first without creating a hard typed dependency.
    try:
        yaml_module = import_module("yaml")
        meta = yaml_module.safe_load(raw_fm)
        if isinstance(meta, dict):
            return meta, body
    except Exception:
        meta = None  # yaml unavailable or parse failed; use manual fallback

    # Manual fallback
    meta = {}  # noqa: F841 – reassignment for fallback path
    for line in raw_fm.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.lower() == "true":
            meta[key] = True
        elif value.lower() == "false":
            meta[key] = False
        else:
            meta[key] = value

    return meta, body


# ---------------------------------------------------------------------------
# Agent definition loader
# ---------------------------------------------------------------------------


def _load_agent_definition(slug: str) -> Optional[Dict[str, Any]]:
    """Load and parse a single agent definition from ``.cursor/agents/<slug>.md``."""
    agent_path = REPO_ROOT / ".cursor" / "agents" / f"{slug}.md"
    if not agent_path.is_file():
        return None

    text = agent_path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    return {
        "slug": slug,
        "name": meta.get("name", slug),
        "model": meta.get("model", ""),
        "description": meta.get("description", ""),
        "readonly": bool(meta.get("readonly", False)),
        "readonly_explicit": "readonly" in meta,
        "depends_on_previous": bool(meta.get("depends_on_previous", False)),
        "body": body,
        "definition_path": str(agent_path.relative_to(REPO_ROOT)),
    }


# ---------------------------------------------------------------------------
# Context-map parser
# ---------------------------------------------------------------------------

_CONTEXT_AGENT_HEADER_RE = re.compile(
    r"^###\s+.*\(`([a-z][a-z0-9-]+)`\)",
    re.IGNORECASE,
)


def _parse_context_map() -> Dict[str, List[str]]:
    """Parse ``docs/orchestration/AGENT_CONTEXT_MAP.md`` for per-agent context paths."""
    context_map_path = REPO_ROOT / "docs" / "orchestration" / "AGENT_CONTEXT_MAP.md"
    if not context_map_path.is_file():
        return {}

    lines = context_map_path.read_text(encoding="utf-8").splitlines()
    result: Dict[str, List[str]] = {}
    current_slug: Optional[str] = None

    for line in lines:
        m = _CONTEXT_AGENT_HEADER_RE.match(line.strip())
        if m:
            current_slug = m.group(1)
            result.setdefault(current_slug, [])
            continue
        if current_slug is None:
            continue
        if line.strip().startswith("##") and not line.strip().startswith("###"):
            current_slug = None
            continue
        # Capture backtick-quoted paths
        for path_match in re.finditer(r"`([^`]+(?:\.\w+|/\w+)[^`]*)`", line):
            candidate = path_match.group(1)
            # Keep path-shaped backtick tokens (repo paths and markdown/python refs).
            if "/" in candidate or candidate.endswith(".md") or candidate.endswith(".py"):
                # Strip line-range suffixes like :12-24
                cleaned = re.sub(r":\d+(-\d+)?$", "", candidate)
                if cleaned not in result[current_slug]:
                    result[current_slug].append(cleaned)

    return result


# ---------------------------------------------------------------------------
# Qoder subagent type resolution
# ---------------------------------------------------------------------------


def resolve_qoder_type(agent_def: Dict[str, Any], mode: str, is_reviewer: bool) -> str:
    """Map an agent definition + task mode to a Qoder subagent type.

    Type mapping:
    - ``CodeReview`` — reviewers
    - ``Research``   — readonly agents, analysis/docs-only modes
    - ``Verify``     — QA/bug-hunting agents
    - ``Coding``     — implementation agents in runtime mode
    - ``Browser``    — frontend in runtime mode (UI validation)
    """
    # mode=review forces CodeReview for all agents
    if mode == "review":
        return "CodeReview"

    slug = agent_def.get("slug") or agent_def.get("name", "")

    if slug in ("qa-engineer-agent", "bug-hunter"):
        return "Verify"

    if is_reviewer:
        return "CodeReview"

    if agent_def.get("readonly") or mode in ("analysis", "docs-only"):
        return "Research"

    # Specific mode-dependent check first (frontend runtime → Browser)
    if slug == "frontend-engineer" and mode == "runtime":
        return "Browser"

    # Then generic implementation roles
    if slug in ("backend-engineer", "frontend-engineer", "dev-operator"):
        return "Coding"

    return "Research"  # Safe fallback


# ---------------------------------------------------------------------------
# Packet parser – extract role order from governance packet markdown
# ---------------------------------------------------------------------------

_ROLE_SLUG_RE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
_BRACKET_GROUP_RE = re.compile(r"\[([^\]]+)\]")
_ROLE_ORDER_FIELD_RE = re.compile(
    r"\b(?:required\s+)?(?:role|agent|dispatch)\s+order\b",
    re.IGNORECASE,
)


def _strip_inline_code_token(value: str) -> str:
    """Normalize Markdown inline-code role tokens."""
    return value.strip().strip("`").strip()


def _known_role_slugs_from_text(text: str, known: set[str]) -> List[str]:
    """Extract known role slugs from text while preserving order."""
    slugs: List[str] = []
    for candidate in _ROLE_SLUG_RE.findall(text):
        if candidate in known and (not slugs or slugs[-1] != candidate):
            slugs.append(candidate)
    return slugs


def _parse_json_packet_roles(payload: Dict[str, Any]) -> List[str]:
    """Extract ordered role slugs from a task_bootstrap JSON packet."""
    bridge = payload.get("native_subagent_bridge")
    if not isinstance(bridge, dict):
        return []

    ordered: List[str] = []

    def binding_is_spawnable(value: Any, *, default_when_unspecified: bool) -> bool:
        if not isinstance(value, dict):
            return False
        dispatch_contract = value.get("dispatch_contract")
        if dispatch_contract is None:
            return default_when_unspecified
        if not isinstance(dispatch_contract, dict):
            return False
        return not (
            dispatch_contract.get("advisory_only")
            or dispatch_contract.get("spawn_with_native_subagent") is False
        )

    def add_slug(value: Any, *, default_when_unspecified: bool = True) -> None:
        if not binding_is_spawnable(value, default_when_unspecified=default_when_unspecified):
            return
        slug = str(value.get("repo_agent_slug", "")).strip()
        if slug:
            ordered.append(slug)

    primary = bridge.get("primary")
    if not isinstance(primary, dict):
        return []
    if not binding_is_spawnable(primary, default_when_unspecified=True):
        return []
    if not str(primary.get("repo_agent_slug", "")).strip():
        return []
    add_slug(primary)
    secondary_items = bridge.get("secondary")
    if isinstance(secondary_items, list):
        for item in secondary_items:
            add_slug(item)
    advisory_items = bridge.get("advisory")
    if isinstance(advisory_items, list):
        for item in advisory_items:
            add_slug(item, default_when_unspecified=False)
    add_slug(bridge.get("reviewer"))
    if not ordered:
        return []
    requested_agents = payload.get("requested_agents")
    if isinstance(requested_agents, list):
        available_counts: Dict[str, int] = {}
        for slug in ordered:
            available_counts[slug] = available_counts.get(slug, 0) + 1

        requested_ordered: List[str] = []
        for value in requested_agents:
            slug = str(value).strip()
            if available_counts.get(slug, 0) > 0:
                requested_ordered.append(slug)
                available_counts[slug] -= 1

        if requested_ordered:
            remaining_counts = dict(available_counts)
            remaining_ordered: List[str] = []
            for slug in ordered:
                if remaining_counts.get(slug, 0) > 0:
                    remaining_ordered.append(slug)
                    remaining_counts[slug] -= 1
            ordered = [*requested_ordered, *remaining_ordered]
    if ordered[0] == "agent-coordinator":
        return ordered
    if "agent-coordinator" in ordered:
        coordinator_index = ordered.index("agent-coordinator")
        return [
            "agent-coordinator",
            *ordered[:coordinator_index],
            *ordered[coordinator_index + 1 :],
        ]
    return ["agent-coordinator", *ordered]


def _load_json_packet(packet_path: Path) -> Optional[Dict[str, Any]]:
    """Return JSON packet payload when the packet is a JSON object."""
    try:
        payload = json.loads(packet_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _json_packet_has_requested_order(packet_path: Path) -> bool:
    """Return whether a JSON packet carries an explicit requested role order."""

    try:
        resolved_packet_path = packet_path.resolve(strict=True)
        resolved_packet_path.relative_to(REPO_ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    payload = _load_json_packet(resolved_packet_path)
    if payload is None:
        return False
    requested_agents = payload.get("requested_agents")
    if not isinstance(requested_agents, list):
        return False
    return any(str(agent).strip() for agent in requested_agents)


def _json_payload_requested_order_preserves_mandatory_tail(payload: Dict[str, Any]) -> bool:
    """Return whether requested_agents explicitly keeps the canonical post-open tail."""

    requested_agents = payload.get("requested_agents")
    if not isinstance(requested_agents, list):
        return False
    requested_order = [str(agent).strip() for agent in requested_agents if str(agent).strip()]
    try:
        qa_index = requested_order.index("qa-engineer-agent")
        bug_index = requested_order.index("bug-hunter")
        security_index = requested_order.index("security-auditor")
    except ValueError:
        return False
    return bug_index == qa_index + 1 and security_index == bug_index + 1


def _json_packet_requested_order_preserves_mandatory_tail(packet_path: Path) -> bool:
    """Return whether a JSON packet can safely override mandatory tail normalization."""

    try:
        resolved_packet_path = packet_path.resolve(strict=True)
        resolved_packet_path.relative_to(REPO_ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    payload = _load_json_packet(resolved_packet_path)
    if payload is None:
        return False
    return _json_payload_requested_order_preserves_mandatory_tail(payload)


def _parse_packet_roles(packet_path: Path) -> List[str]:
    """Extract ordered role slugs from a governance packet.

    Looks for:
    1. A task_bootstrap JSON packet with ``native_subagent_bridge``.
    2. A ``## Coordinator Role Order`` section with numbered/bulleted slugs.
    3. Fallback: any numbered list containing agent slugs.
    """
    if not packet_path.is_file():
        print(f"FAIL: Packet file not found: {packet_path}", file=sys.stderr)
        sys.exit(1)
    try:
        resolved_packet_path = packet_path.resolve(strict=True)
        resolved_packet_path.relative_to(REPO_ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        print(
            f"FAIL: Packet file must stay under repo root: {packet_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    json_payload = _load_json_packet(resolved_packet_path)
    if json_payload is not None:
        return _parse_json_packet_roles(json_payload)

    text = resolved_packet_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Strategy 1: dedicated section
    slugs = _extract_roles_from_section(lines, "Coordinator Role Order")
    if slugs:
        return slugs

    # Strategy 2: look for "Role Order" or "Agent Order" sections
    for heading_fragment in ("Role Order", "Agent Order", "Dispatch Order"):
        slugs = _extract_roles_from_section(lines, heading_fragment)
        if slugs:
            return slugs

    # Strategy 3: scan for numbered list items containing agent slugs
    known_agents = _list_known_agent_slugs()
    ordered: List[str] = []
    in_fence = False
    capture_continuation = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            capture_continuation = False
            continue
        if in_fence:
            continue
        if not stripped or stripped.startswith("##"):
            capture_continuation = False
            continue
        is_list_item = bool(re.match(r"^\d+\.\s+", stripped) or stripped.startswith("- "))
        if capture_continuation and not is_list_item:
            for slug in _known_role_slugs_from_text(stripped, known_agents):
                if not ordered or ordered[-1] != slug:
                    ordered.append(slug)
            continue
        capture_continuation = False
        if is_list_item and _ROLE_ORDER_FIELD_RE.search(stripped):
            capture_continuation = True
        if is_list_item:
            for slug in _known_role_slugs_from_text(stripped, known_agents):
                if not ordered or ordered[-1] != slug:
                    ordered.append(slug)

    return ordered


def _extract_roles_from_section(lines: List[str], heading_fragment: str) -> List[str]:
    """Extract role slugs from a markdown section matching the heading fragment."""
    in_section = False
    in_fence = False
    slugs: List[str] = []
    known = _list_known_agent_slugs()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("##") and heading_fragment.lower() in stripped.lower():
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if not in_section:
            continue
        for candidate in _known_role_slugs_from_text(stripped, known):
            if not slugs or slugs[-1] != candidate:
                slugs.append(candidate)

    return slugs


def _extract_chain_successors(lines: List[str]) -> set[str]:
    """Extract slugs that are successors in explicit ``a -> b`` chain notation."""
    known = _list_known_agent_slugs()
    successors: set[str] = set()
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or "->" not in stripped:
            continue
        slugs = _known_role_slugs_from_text(stripped, known)
        if len(slugs) >= 2:
            successors.update(slugs[1:])

    return successors


def _list_known_agent_slugs() -> set[str]:
    """Return the set of agent slugs that have definition files."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    if not agents_dir.is_dir():
        return set()
    return {p.stem for p in agents_dir.glob("*.md") if p.stem != "AGENTS"}


def _extract_bracket_groups(lines: List[str]) -> List[List[str]]:
    """Extract parallelizable groups from bracket notation ``[slug-a, slug-b]``.

    Returns a list of groups, where each group is a list of slugs that should
    run in parallel.
    """
    known = _list_known_agent_slugs()
    groups: List[List[str]] = []
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in _BRACKET_GROUP_RE.finditer(stripped):
            inner = match.group(1)
            slugs = [_strip_inline_code_token(s) for s in inner.split(",")]
            valid_slugs = [s for s in slugs if s in known]
            if len(valid_slugs) >= 2:
                groups.append(valid_slugs)

    return groups


# ---------------------------------------------------------------------------
# Parallelization heuristic
# ---------------------------------------------------------------------------


def _detect_parallel_groups(
    dispatch_items: List[Dict[str, Any]],
    routing: Dict[str, Any],
) -> List[List[str]]:
    """Detect groups of agents that can run in parallel.

    Heuristic: readonly agents with different domains can be parallelized.
    """
    # Build a slug -> domain map
    slug_domain: Dict[str, str] = {}
    for domain, route_info in routing.items():
        for role_key in ("primary", "secondary", "reviewer"):
            agent = route_info.get(role_key)
            if agent:
                slug_domain.setdefault(agent, domain)

    readonly_items = [
        item
        for item in dispatch_items
        if item.get("readonly")
        and not item.get("depends_on_previous")
        and item.get("role_slug") != "agent-coordinator"
        and item.get("qoder_subagent_type") != "Verify"
    ]
    slug_counts: Dict[str, int] = {}
    for item in readonly_items:
        slug = item["role_slug"]
        slug_counts[slug] = slug_counts.get(slug, 0) + 1
    readonly_items = [item for item in readonly_items if slug_counts[item["role_slug"]] == 1]

    if len(readonly_items) < 2:
        return []

    # Group by domain
    domain_groups: Dict[str, List[str]] = {}
    for item in readonly_items:
        domain = slug_domain.get(item["role_slug"], "unknown")
        domain_groups.setdefault(domain, []).append(item["role_slug"])

    # Agents in different domains can be parallelized
    if len(domain_groups) >= 2:
        parallel_group = [slug for slugs in domain_groups.values() for slug in slugs]
        return [parallel_group] if len(parallel_group) >= 2 else []

    return []


def _validated_bracket_groups(
    bracket_groups: List[List[str]],
    dispatch_items: List[Dict[str, Any]],
) -> List[List[str]]:
    """Keep only packet bracket groups that match runnable independent dispatch items."""
    dispatch_by_slug = {item["role_slug"]: item for item in dispatch_items}
    ambiguous_slugs = {
        item["role_slug"]
        for item in dispatch_items
        if sum(1 for candidate in dispatch_items if candidate["role_slug"] == item["role_slug"]) > 1
    }
    validated: List[List[str]] = []

    for group in bracket_groups:
        if len(set(group)) != len(group):
            continue
        unique_group = list(dict.fromkeys(group))
        if len(unique_group) < 2:
            continue
        if any(slug in ambiguous_slugs for slug in unique_group):
            continue
        group_items = [dispatch_by_slug.get(slug) for slug in unique_group]
        if any(item is None for item in group_items):
            continue
        if any(item.get("depends_on_previous") for item in group_items if item is not None):
            continue
        if any(not item.get("readonly") for item in group_items if item is not None):
            continue
        if any(
            item.get("qoder_subagent_type") == "Verify" for item in group_items if item is not None
        ):
            continue
        if any(
            item.get("role_slug") == "agent-coordinator" for item in group_items if item is not None
        ):
            continue
        validated.append(unique_group)

    return validated


# ---------------------------------------------------------------------------
# Skill recommendation (simple heuristic)
# ---------------------------------------------------------------------------

_SKILL_MAP: Dict[str, List[str]] = {
    "agent-coordinator": ["pulseplate-workflow"],
    "architecture-specialist": ["pulseplate-workflow"],
    "backend-engineer": ["pulseplate-workflow"],
    "frontend-engineer": ["pulseplate-workflow", "vercel-react-best-practices"],
    "security-auditor": ["pulseplate-workflow", "pulseplate-pr-review"],
    "qa-engineer-agent": ["pulseplate-workflow", "pulseplate-pr-review"],
    "bug-hunter": ["pulseplate-workflow", "pulseplate-pr-review"],
}


def _recommend_skills(slug: str) -> List[str]:
    """Return recommended skills for an agent slug."""
    return list(_SKILL_MAP.get(slug, ["pulseplate-workflow"]))


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------

MANDATORY_POST_OPEN_ORDER: tuple[str, ...] = (
    "qa-engineer-agent",
    "bug-hunter",
    "security-auditor",
)


def _enforce_mandatory_post_open_order(role_slugs: List[str]) -> List[str]:
    """Keep the canonical post-open QA -> bug-hunter -> security pass adjacent."""

    if "qa-engineer-agent" not in role_slugs or "bug-hunter" not in role_slugs:
        return role_slugs

    mandatory_tail = ("bug-hunter", "security-auditor")
    ordered = [slug for slug in role_slugs if slug not in mandatory_tail]
    insert_at = ordered.index("qa-engineer-agent") + 1
    ordered[insert_at:insert_at] = [
        *["bug-hunter"] * role_slugs.count("bug-hunter"),
        *["security-auditor"] * role_slugs.count("security-auditor"),
    ]
    return ordered


def build_dispatch_manifest(
    *,
    role_slugs: List[str],
    mode: str,
    packet_source: Optional[str] = None,
    bracket_groups: Optional[List[List[str]]] = None,
    chained_successors: Optional[set[str]] = None,
    enforce_mandatory_post_open_tail: bool = True,
) -> Dict[str, Any]:
    """Build the full JSON dispatch manifest for the given role order."""
    context_map = _parse_context_map()
    routing = _ensure_routing_graph()
    primary_slugs = _primary_slugs_from_routing(routing)
    reviewer_slugs = _reviewer_slugs_from_routing(routing)

    dispatch_sequence: List[Dict[str, Any]] = []
    missing_agents: List[str] = []
    loaded_agents: List[Tuple[str, Dict[str, Any]]] = []
    if enforce_mandatory_post_open_tail:
        role_slugs = _enforce_mandatory_post_open_order(role_slugs)

    for slug in role_slugs:
        agent_def = _load_agent_definition(slug)
        if agent_def is None:
            missing_agents.append(slug)
            continue
        loaded_agents.append((slug, agent_def))

    total_roles = len(loaded_agents)
    previous_slug: Optional[str] = None

    for order_idx, (slug, agent_def) in enumerate(loaded_agents, start=1):
        is_reviewer = _dispatch_is_reviewer_slot(
            slug,
            order_idx,
            total_roles,
            primary_slugs=primary_slugs,
            reviewer_slugs=reviewer_slugs,
        )
        qoder_type = resolve_qoder_type(agent_def, mode, is_reviewer)
        context_paths = context_map.get(slug, [])
        skills = _recommend_skills(slug)

        # Derive readonly: use agent frontmatter if explicitly set, else infer from Qoder type
        if agent_def.get("readonly_explicit"):
            readonly = agent_def["readonly"]
        else:
            readonly = qoder_type in ("Research", "CodeReview", "Verify")

        # System prompt excerpt: first 500 chars of body
        body_excerpt = agent_def["body"][:500] if agent_def["body"] else ""

        item: Dict[str, Any] = {
            "order": order_idx,
            "role_slug": slug,
            "qoder_subagent_type": qoder_type,
            "agent_definition_path": agent_def["definition_path"],
            "required_context_paths": context_paths,
            "recommended_skills": skills,
            "mode": mode,
            "system_prompt_excerpt": body_excerpt,
            "description": agent_def["description"],
            "readonly": readonly,
            "constraints": [],
            "depends_on_previous": _depends_on_previous(
                slug, agent_def, previous_slug, chained_successors
            ),
        }
        dispatch_sequence.append(item)
        previous_slug = slug

    if missing_agents:
        print(
            f"WARNING: Agent definitions not found for: {', '.join(missing_agents)}",
            file=sys.stderr,
        )

    parallel_groups = _detect_parallel_groups(dispatch_sequence, routing)
    # Merge bracket groups from packet notation [slug-a, slug-b]
    if bracket_groups:
        for bg in _validated_bracket_groups(bracket_groups, dispatch_sequence):
            if bg not in parallel_groups:
                parallel_groups.append(bg)

    manifest: Dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "packet_source": packet_source or "",
        "mode": mode,
        "dispatch_sequence": dispatch_sequence,
        "parallelizable_groups": parallel_groups,
        "mandatory_post_open": list(MANDATORY_POST_OPEN_ORDER),
        "missing_agents": missing_agents,
    }

    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="qoder_dispatch_bridge",
        description=(
            "Generate a JSON dispatch manifest for Qoder from a governance "
            "packet or explicit role list."
        ),
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--packet",
        type=str,
        default=None,
        help="Path to governance packet markdown file.",
    )
    source.add_argument(
        "--roles",
        nargs="+",
        metavar="SLUG",
        default=None,
        help="Explicit ordered list of role slugs.",
    )

    parser.add_argument(
        "--mode",
        choices=("analysis", "docs-only", "runtime", "review"),
        default="analysis",
        help="Task mode (default: analysis).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=False,
        help="Pretty-print JSON output.",
    )

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint."""
    args = _parse_args(argv)

    # Resolve role slugs
    packet_source: Optional[str] = None
    packet_bracket_groups: Optional[List[List[str]]] = None
    packet_chained_successors: Optional[set[str]] = None
    enforce_mandatory_post_open_tail = True
    if args.packet:
        packet_path = Path(args.packet)
        if not packet_path.is_absolute():
            packet_path = (REPO_ROOT / packet_path).resolve()
        enforce_mandatory_post_open_tail = not (
            _json_packet_requested_order_preserves_mandatory_tail(packet_path)
        )
        role_slugs = _parse_packet_roles(packet_path)
        # Extract bracket-notation parallelizable groups from packet
        packet_lines = packet_path.read_text(encoding="utf-8").splitlines()
        packet_bracket_groups = _extract_bracket_groups(packet_lines) or None
        packet_chained_successors = _extract_chain_successors(packet_lines) or None
        try:
            packet_source = str(packet_path.relative_to(REPO_ROOT))
        except ValueError:
            packet_source = str(packet_path)
        if not role_slugs:
            print(
                f"FAIL: No agent role slugs found in packet: {packet_path}",
                file=sys.stderr,
            )
            return 1
    else:
        role_slugs = list(args.roles)

    if not role_slugs:
        print("FAIL: No role slugs provided.", file=sys.stderr)
        return 1

    # Build manifest
    manifest = build_dispatch_manifest(
        role_slugs=role_slugs,
        mode=args.mode,
        packet_source=packet_source,
        bracket_groups=packet_bracket_groups,
        chained_successors=packet_chained_successors,
        enforce_mandatory_post_open_tail=enforce_mandatory_post_open_tail,
    )
    if manifest.get("missing_agents"):
        print(
            "FAIL: Agent definitions not found for: "
            + ", ".join(str(slug) for slug in manifest["missing_agents"]),
            file=sys.stderr,
        )
        return 1

    # Output
    indent = 2 if args.pretty else None
    json_output = json.dumps(manifest, ensure_ascii=False, indent=indent, sort_keys=False)

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = (REPO_ROOT / out_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_output + "\n", encoding="utf-8")
        print(f"Manifest written to: {out_path}", file=sys.stderr)
    else:
        print(json_output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
