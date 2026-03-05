"""Load canonical routing graph from docs/orchestration/AGENT_ROUTING_GRAPH.md.

Parses the Domains → Agents table and returns Dict[str, DomainRoute].
Used by route_with_telemetry.py as baseline fallback (telemetry is advisory).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROUTING_GRAPH = REPO_ROOT / "docs" / "orchestration" / "AGENT_ROUTING_GRAPH.md"

_TABLE_ROW_RE = re.compile(r"^\|\s*(?P<cols>.+?)\s*\|\s*$")


@dataclass(frozen=True)
class DomainRoute:
    """Canonical route for a domain: primary, optional secondary, reviewer."""

    primary: str
    secondary: Optional[str]
    reviewer: str


def _split_md_row(row: str) -> Tuple[str, ...]:
    """Parse markdown table row: | a | b | c | -> ('a','b','c')."""
    m = _TABLE_ROW_RE.match(row.strip())
    if not m:
        return ()
    parts = [p.strip() for p in m.group("cols").split("|")]
    return tuple(parts)


def _is_delimiter_row(line: str) -> bool:
    """True if line is a markdown table delimiter (|---|---|)."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    content = stripped.replace("|", "").strip()
    return bool(content and set(content) <= {"-", ":", " "})


def load_routing_graph(path: Path = DEFAULT_ROUTING_GRAPH) -> Dict[str, DomainRoute]:
    """
    Parse canonical routing table from AGENT_ROUTING_GRAPH.md.

    Expects table format:
    | Domain   | Primary Agent            | Secondary                | Reviewer                |
    |----------|--------------------------|--------------------------|-------------------------|
    | safety   | philosophy-agent         | logic-agent             | agent-coordinator       |

    Returns:
        Dict mapping domain -> DomainRoute(primary, secondary, reviewer).
        Secondary is first agent when comma-separated (e.g. "a, b" -> "a").
    """
    if not path.exists():
        raise FileNotFoundError(f"Routing graph not found: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()

    header_idx: Optional[int] = None
    header_cols: Tuple[str, ...] = ()
    for i, line in enumerate(lines):
        cols = _split_md_row(line)
        if not cols:
            continue
        norm = [c.lower() for c in cols]
        joined = " ".join(norm)
        if "domain" in norm and "primary" in joined and "reviewer" in joined:
            header_idx = i
            header_cols = cols
            break

    if header_idx is None:
        raise ValueError("Routing graph table header not found")

    start = header_idx + 1
    if start < len(lines) and _is_delimiter_row(lines[start]):
        start += 1

    header_norm = [c.strip().lower() for c in header_cols]

    def idx_of(key: str) -> int:
        for j, h in enumerate(header_norm):
            if key in h:
                return j
        raise ValueError(f"Required column missing: {key}")

    i_domain = idx_of("domain")
    i_primary = idx_of("primary")
    i_reviewer = idx_of("reviewer")

    i_secondary: Optional[int] = None
    for j, h in enumerate(header_norm):
        if "secondary" in h:
            i_secondary = j
            break

    routes: Dict[str, DomainRoute] = {}

    for line in lines[start:]:
        stripped = line.strip()
        if stripped == "---" or stripped.startswith("##"):
            break
        cols = _split_md_row(line)
        if not cols:
            continue
        if len(cols) <= max(i_domain, i_primary, i_reviewer):
            continue

        domain = cols[i_domain].strip().lower()
        primary = cols[i_primary].strip()
        reviewer = cols[i_reviewer].strip()
        secondary_raw = (
            cols[i_secondary].strip() if i_secondary is not None and i_secondary < len(cols) else ""
        )

        if not domain or domain.startswith("-"):
            continue
        if not primary or not reviewer:
            continue

        secondary: Optional[str] = None
        if secondary_raw:
            first = secondary_raw.split(",")[0].strip()
            secondary = first if first else None

        routes[domain] = DomainRoute(
            primary=primary,
            secondary=secondary,
            reviewer=reviewer,
        )

    if not routes:
        raise ValueError("No routing rows parsed from routing graph")

    return routes
