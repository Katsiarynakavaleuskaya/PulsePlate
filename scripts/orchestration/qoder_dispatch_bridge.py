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
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Optional imports with graceful fallback
# ---------------------------------------------------------------------------

_routing_graph: Optional[Dict[str, Any]] = None
_routing_loader_available = False

try:
    from scripts.orchestration.routing_graph_loader import (
        DomainRoute,
        load_routing_graph,
    )

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

    # Try yaml first
    try:
        import yaml  # type: ignore[import-untyped]

        meta = yaml.safe_load(raw_fm)
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
            # Filter out things that look like file paths or doc references
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
    if is_reviewer:
        return "CodeReview"

    if agent_def.get("readonly") or mode in ("analysis", "docs-only"):
        return "Research"

    slug = agent_def.get("name", agent_def.get("slug", ""))

    if slug in ("qa-engineer-agent", "bug-hunter"):
        return "Verify"

    if slug in ("backend-engineer", "frontend-engineer", "dev-operator"):
        return "Coding"

    if slug == "frontend-engineer" and mode == "runtime":
        return "Browser"

    return "Research"  # Safe fallback


# ---------------------------------------------------------------------------
# Packet parser – extract role order from governance packet markdown
# ---------------------------------------------------------------------------

_ROLE_SLUG_RE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")


def _parse_packet_roles(packet_path: Path) -> List[str]:
    """Extract ordered role slugs from a governance packet markdown file.

    Looks for:
    1. A ``## Coordinator Role Order`` section with numbered/bulleted slugs.
    2. Fallback: any numbered list containing agent slugs.
    """
    if not packet_path.is_file():
        print(f"FAIL: Packet file not found: {packet_path}", file=sys.stderr)
        sys.exit(1)

    text = packet_path.read_text(encoding="utf-8")
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
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d+\.\s+", stripped) or stripped.startswith("- "):
            for slug in _ROLE_SLUG_RE.findall(stripped):
                if slug in known_agents and slug not in ordered:
                    ordered.append(slug)

    return ordered


def _extract_roles_from_section(lines: List[str], heading_fragment: str) -> List[str]:
    """Extract role slugs from a markdown section matching the heading fragment."""
    in_section = False
    slugs: List[str] = []
    known = _list_known_agent_slugs()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("##") and heading_fragment.lower() in stripped.lower():
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if not in_section:
            continue
        for candidate in _ROLE_SLUG_RE.findall(stripped):
            if candidate in known and candidate not in slugs:
                slugs.append(candidate)

    return slugs


def _list_known_agent_slugs() -> set[str]:
    """Return the set of agent slugs that have definition files."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    if not agents_dir.is_dir():
        return set()
    return {p.stem for p in agents_dir.glob("*.md") if p.stem != "AGENTS"}


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
        if item.get("readonly") and not item.get("depends_on_previous")
    ]

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


def build_dispatch_manifest(
    *,
    role_slugs: List[str],
    mode: str,
    packet_source: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the full JSON dispatch manifest for the given role order."""
    context_map = _parse_context_map()
    routing = _ensure_routing_graph()

    dispatch_sequence: List[Dict[str, Any]] = []
    missing_agents: List[str] = []

    for order_idx, slug in enumerate(role_slugs, start=1):
        agent_def = _load_agent_definition(slug)
        if agent_def is None:
            missing_agents.append(slug)
            continue

        # In a dispatch sequence, no agent is pre-flagged as reviewer;
        # the Qoder type is driven by readonly + mode. The caller can
        # override if a specific agent is designated as the reviewer.
        is_reviewer = False
        qoder_type = resolve_qoder_type(agent_def, mode, is_reviewer)
        context_paths = context_map.get(slug, [])
        skills = _recommend_skills(slug)

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
            "readonly": agent_def["readonly"],
            "constraints": [],
            "depends_on_previous": order_idx > 1,
        }
        dispatch_sequence.append(item)

    if missing_agents:
        print(
            f"WARNING: Agent definitions not found for: {', '.join(missing_agents)}",
            file=sys.stderr,
        )

    parallel_groups = _detect_parallel_groups(dispatch_sequence, routing)

    manifest: Dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "packet_source": packet_source or "",
        "mode": mode,
        "dispatch_sequence": dispatch_sequence,
        "parallelizable_groups": parallel_groups,
        "mandatory_post_open": ["qa-engineer-agent", "bug-hunter"],
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
        choices=("analysis", "docs-only", "runtime"),
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
    if args.packet:
        packet_path = Path(args.packet)
        if not packet_path.is_absolute():
            packet_path = (REPO_ROOT / packet_path).resolve()
        role_slugs = _parse_packet_roles(packet_path)
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
    )

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
