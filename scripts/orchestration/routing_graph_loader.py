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


def _normalize_header_tokens(column: str) -> set[str]:
    """Normalize a markdown header cell into lowercase word tokens."""

    text = re.sub(r"[^\w\s]", " ", column.strip().lower())
    return {token for token in text.split() if token}


def _find_section_bounds(lines: list[str], section_title: str) -> tuple[int, int]:
    """Return the line slice for a markdown section body."""

    header = f"## {section_title}"
    start_index: Optional[int] = None
    for index, line in enumerate(lines):
        if line.strip() == header:
            start_index = index + 1
            break

    if start_index is None:
        raise ValueError(f"Routing graph section not found: {section_title}")

    end_index = len(lines)
    for index in range(start_index, len(lines)):
        if lines[index].startswith("## "):
            end_index = index
            break

    return start_index, end_index


def _find_table_header(
    lines: list[str],
    required_columns: tuple[str, ...],
    start_index: int = 0,
    end_index: Optional[int] = None,
) -> tuple[int, Tuple[str, ...]]:
    """Locate a markdown table header using whole-token column matching."""

    required_token_sets = tuple(_normalize_header_tokens(column) for column in required_columns)
    stop_index = len(lines) if end_index is None else end_index

    for index in range(start_index, stop_index):
        line = lines[index]
        cols = _split_md_row(line)
        if not cols:
            continue
        header_tokens = tuple(_normalize_header_tokens(column) for column in cols)
        if all(required in header_tokens for required in required_token_sets):
            return index, cols
    required = ", ".join(required_columns)
    raise ValueError(f"Routing graph table header not found for columns: {required}")


def _header_index(header_cols: Tuple[str, ...], required_header: str) -> int:
    """Return the exact header index for a required column token set."""

    required_tokens = _normalize_header_tokens(required_header)
    matches = [
        position
        for position, column in enumerate(header_cols)
        if _normalize_header_tokens(column) == required_tokens
    ]
    if not matches:
        raise ValueError(f"Required column missing: {required_header}")
    if len(matches) > 1:
        matched_headers = [header_cols[position] for position in matches]
        raise ValueError(
            f"Ambiguous column '{required_header}' matched multiple headers: {matched_headers}"
        )
    return matches[0]


def _parse_cluster_definitions(lines: list[str]) -> Set[str]:
    """Parse canonical cluster definitions from the routing graph SoT."""

    try:
        section_start, section_end = _find_section_bounds(lines, "3. Cluster Definitions")
        header_idx, header_cols = _find_table_header(
            lines,
            ("cluster", "purpose"),
            start_index=section_start,
            end_index=section_end,
        )
    except ValueError as exc:
        raise ValueError("Cluster definitions table is missing or empty") from exc
    start = header_idx + 1
    if start < len(lines) and _is_delimiter_row(lines[start]):
        start += 1

    i_cluster = _header_index(header_cols, "cluster")
    i_purpose = _header_index(header_cols, "purpose")
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


def load_routing_clusters_raw(path: Path = DEFAULT_ROUTING_GRAPH) -> Set[str]:
    """Return clusters referenced by routed domains without declared-cluster validation."""

    if not path.is_file():
        raise FileNotFoundError(f"Routing graph not found: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()
    section_start, section_end = _find_section_bounds(lines, "4. Domains → Agents")
    header_idx, header_cols = _find_table_header(
        lines,
        ("domain", "cluster", "primary agent", "reviewer"),
        start_index=section_start,
        end_index=section_end,
    )

    start = header_idx + 1
    if start < len(lines) and _is_delimiter_row(lines[start]):
        start += 1

    i_cluster = _header_index(header_cols, "cluster")
    routing_clusters: Set[str] = set()

    for line in lines[start:]:
        stripped = line.strip()
        if stripped == "---" or stripped.startswith("##"):
            break
        cols = _split_md_row(line)
        if not cols:
            if routing_clusters:
                break
            continue
        if len(cols) <= i_cluster:
            continue

        cluster = cols[i_cluster].strip()
        if cluster and not cluster.startswith("-"):
            routing_clusters.add(cluster)

    return routing_clusters


def load_routing_graph(path: Path = DEFAULT_ROUTING_GRAPH) -> Dict[str, DomainRoute]:
    """
    Parse canonical routing table from AGENT_ROUTING_GRAPH.md.

    Expects table format:
    | Domain   | Cluster | Primary Agent | Secondary | Reviewer |
    |----------|---------|---------------|-----------|----------|
    | safety   | safety  | philosophy-agent | logic-agent | agent-coordinator |

    Returns:
        Dict mapping domain -> DomainRoute(primary, secondary, reviewer).
        Canonical routing graph defines zero or one secondary agent only.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Routing graph not found: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()
    declared_clusters = _parse_cluster_definitions(lines)
    section_start, section_end = _find_section_bounds(lines, "4. Domains → Agents")

    header_idx, header_cols = _find_table_header(
        lines,
        ("domain", "cluster", "primary agent", "reviewer"),
        start_index=section_start,
        end_index=section_end,
    )

    start = header_idx + 1
    if start < len(lines) and _is_delimiter_row(lines[start]):
        start += 1

    i_domain = _header_index(header_cols, "domain")
    i_cluster = _header_index(header_cols, "cluster")
    i_primary = _header_index(header_cols, "primary agent")
    i_reviewer = _header_index(header_cols, "reviewer")

    i_secondary: Optional[int] = None
    for j, header in enumerate(header_cols):
        if _normalize_header_tokens(header) == _normalize_header_tokens("secondary"):
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

        if domain.startswith("-"):
            continue
        populated_fields = [domain, cluster, primary, reviewer, secondary_raw]
        required_fields = [domain, cluster, primary, reviewer]
        if any(populated_fields) and not all(required_fields):
            raise ValueError(
                "Incomplete routing row: "
                f"domain={domain!r}, cluster={cluster!r}, "
                f"primary={primary!r}, reviewer={reviewer!r}"
            )
        if not domain:
            continue
        if not _CLUSTER_SLUG_RE.fullmatch(cluster):
            raise ValueError(f"Invalid cluster slug in routing graph: {cluster}")
        if cluster not in declared_clusters:
            raise ValueError(f"Routing domain references undefined cluster: {domain} -> {cluster}")

        secondary: Optional[str] = None
        if secondary_raw:
            if "," in secondary_raw:
                raise ValueError(
                    "Routing domain declares multiple secondary agents: "
                    f"{domain} -> {secondary_raw}"
                )
            secondary = secondary_raw

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
