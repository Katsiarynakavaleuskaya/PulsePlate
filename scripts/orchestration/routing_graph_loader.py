"""Load canonical routing graph from docs/orchestration/AGENT_ROUTING_GRAPH.md.

Parses the cluster definition table plus the Domains -> Agents table and returns
Dict[str, DomainRoute]. Used by route_with_telemetry.py as baseline fallback
(telemetry is advisory).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROUTING_GRAPH = REPO_ROOT / "docs" / "orchestration" / "AGENT_ROUTING_GRAPH.md"

_TABLE_ROW_RE = re.compile(r"^\|\s*(?P<cols>.+?)\s*\|\s*$")
_CLUSTER_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class DomainRoute:
    """Canonical route for a domain: primary, optional secondary, reviewer."""

    cluster: str
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


def _find_table_header(
    lines: list[str], required_columns: tuple[str, ...]
) -> tuple[int, Tuple[str, ...]]:
    """Locate the first markdown table header that contains the required columns."""

    for index, line in enumerate(lines):
        cols = _split_md_row(line)
        if not cols:
            continue
        normalized = tuple(col.strip().lower() for col in cols)
        if all(any(required in column for column in normalized) for required in required_columns):
            return index, cols
    required = ", ".join(required_columns)
    raise ValueError(f"Routing graph table header not found for columns: {required}")


def _parse_cluster_definitions(lines: list[str]) -> Set[str]:
    """Parse canonical cluster definitions from the routing graph SoT."""

    try:
        header_idx, header_cols = _find_table_header(lines, ("cluster", "purpose"))
    except ValueError as exc:
        raise ValueError("Cluster definitions table is missing or empty") from exc
    start = header_idx + 1
    if start < len(lines) and _is_delimiter_row(lines[start]):
        start += 1

    header_norm = [col.strip().lower() for col in header_cols]

    def idx_of(key: str) -> int:
        for position, column in enumerate(header_norm):
            if key in column:
                return position
        raise ValueError(f"Required column missing: {key}")

    i_cluster = idx_of("cluster")
    i_purpose = idx_of("purpose")
    declared_clusters: Set[str] = set()

    for line in lines[start:]:
        stripped = line.strip()
        if stripped == "---" or stripped.startswith("##"):
            break
        cols = _split_md_row(line)
        if not cols:
            if declared_clusters:
                break
            continue
        if len(cols) <= max(i_cluster, i_purpose):
            continue

        cluster = cols[i_cluster].strip()
        purpose = cols[i_purpose].strip()
        if not cluster or cluster.startswith("-"):
            continue
        if not purpose:
            continue
        if not _CLUSTER_SLUG_RE.fullmatch(cluster):
            raise ValueError(f"Invalid cluster slug in cluster definitions: {cluster}")
        if cluster in declared_clusters:
            raise ValueError(f"Duplicate cluster definition in routing graph: {cluster}")
        declared_clusters.add(cluster)

    if not declared_clusters:
        raise ValueError("Cluster definitions table is missing or empty")

    return declared_clusters


def load_declared_clusters(path: Path = DEFAULT_ROUTING_GRAPH) -> Set[str]:
    """Return the canonical cluster set declared in the routing graph SoT."""

    if not path.is_file():
        raise FileNotFoundError(f"Routing graph not found: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    return _parse_cluster_definitions(lines)


def load_routing_graph(path: Path = DEFAULT_ROUTING_GRAPH) -> Dict[str, DomainRoute]:
    """
    Parse canonical routing table from AGENT_ROUTING_GRAPH.md.

    Expects table format:
    | Domain   | Cluster | Primary Agent | Secondary | Reviewer |
    |----------|---------|---------------|-----------|----------|
    | safety   | safety  | philosophy-agent | logic-agent | agent-coordinator |

    Returns:
        Dict mapping domain -> DomainRoute(primary, secondary, reviewer).
        Secondary is first agent when comma-separated (e.g. "a, b" -> "a").
    """
    if not path.is_file():
        raise FileNotFoundError(f"Routing graph not found: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()
    declared_clusters = _parse_cluster_definitions(lines)

    header_idx, header_cols = _find_table_header(
        lines, ("domain", "cluster", "primary", "reviewer")
    )

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
    i_cluster = idx_of("cluster")
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
            if routes:
                break
            continue
        if len(cols) <= max(i_domain, i_cluster, i_primary, i_reviewer):
            continue

        domain = cols[i_domain].strip().lower()
        cluster = cols[i_cluster].strip()
        primary = cols[i_primary].strip()
        reviewer = cols[i_reviewer].strip()
        secondary_raw = (
            cols[i_secondary].strip() if i_secondary is not None and i_secondary < len(cols) else ""
        )

        if not domain or domain.startswith("-"):
            continue
        if not cluster or not primary or not reviewer:
            continue
        if not _CLUSTER_SLUG_RE.fullmatch(cluster):
            raise ValueError(f"Invalid cluster slug in routing graph: {cluster}")
        if cluster not in declared_clusters:
            raise ValueError(f"Routing domain references undefined cluster: {domain} -> {cluster}")

        secondary: Optional[str] = None
        if secondary_raw:
            first = secondary_raw.split(",")[0].strip()
            secondary = first if first else None

        if domain in routes:
            raise ValueError(f"Duplicate domain in routing graph: {domain}")
        routes[domain] = DomainRoute(
            cluster=cluster,
            primary=primary,
            secondary=secondary,
            reviewer=reviewer,
        )

    if not routes:
        raise ValueError("No routing rows parsed from routing graph")
    unused_clusters = declared_clusters - {route.cluster for route in routes.values()}
    if unused_clusters:
        unused = ", ".join(sorted(unused_clusters))
        raise ValueError(f"Declared clusters unused in routing graph: {unused}")

    return routes
