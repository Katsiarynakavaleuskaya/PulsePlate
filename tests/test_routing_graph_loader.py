"""Tests for routing graph loader (canonical docs/orchestration/AGENT_ROUTING_GRAPH.md)."""

from pathlib import Path

import pytest

from scripts.orchestration.routing_graph_loader import load_routing_graph
from scripts.orchestration.route_with_telemetry import route

_MINIMAL_TABLE = (
    "| Domain   | Primary Agent   | Secondary | Reviewer |\n"
    "|----------|-----------------|-----------|----------|\n"
)


def test_parses_safety_domain() -> None:
    """Safety domain must exist with non-empty primary and reviewer."""
    routes = load_routing_graph()
    assert "safety" in routes
    assert routes["safety"].primary
    assert routes["safety"].reviewer
    assert routes["safety"].primary == "philosophy-agent"
    assert routes["safety"].reviewer == "agent-coordinator"


def test_secondary_optional_supported() -> None:
    """Empty secondary in table must yield None in DomainRoute."""
    routes = load_routing_graph()
    for domain, dr in routes.items():
        assert isinstance(dr.secondary, (str, type(None)))
        if dr.secondary is not None:
            assert len(dr.secondary) > 0


def test_secondary_comma_separated_takes_first() -> None:
    """When secondary column has 'a, b', we take first agent."""
    routes = load_routing_graph()
    backend = routes.get("backend")
    assert backend is not None
    assert backend.secondary == "backend-engineer"


def test_missing_file_raises(tmp_path: Path) -> None:
    """FileNotFoundError when path does not exist."""
    with pytest.raises(FileNotFoundError, match="Routing graph not found"):
        load_routing_graph(tmp_path / "nope.md")


def test_directory_raises_file_not_found(tmp_path: Path) -> None:
    """FileNotFoundError when path is a directory (is_file rejects dirs)."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    with pytest.raises(FileNotFoundError, match="Routing graph not found"):
        load_routing_graph(subdir)


def test_missing_header_raises(tmp_path: Path) -> None:
    """ValueError when the routing table header row is missing."""
    bad_path = tmp_path / "no_header.md"
    bad_path.write_text(
        "# Routing Graph\n\n"
        "Some introductory text, but no routing table header.\n\n"
        "| something | else |\n"
        "| --------- | ---- |\n"
        "| foo       | bar  |\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Routing graph table header not found"):
        load_routing_graph(bad_path)


def test_no_routing_rows_raises(tmp_path: Path) -> None:
    """ValueError when header exists but no routing rows are parsed."""
    empty_table_path = tmp_path / "no_rows.md"
    empty_table_path.write_text(
        "# Routing Graph\n\n"
        "| domain | primary | secondary | reviewer |\n"
        "| ------ | ------- | --------- | -------- |\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="No routing rows parsed from routing graph"):
        load_routing_graph(empty_table_path)


def test_secondary_empty_yields_none(tmp_path: Path) -> None:
    """Empty secondary cell must yield None; non-empty yields agent name."""
    table_path = tmp_path / "secondary_test.md"
    table_path.write_text(
        _MINIMAL_TABLE
        + "| foo | agent-a |           | reviewer-a |\n"
        + "| bar | agent-b | agent-c    | reviewer-b |\n",
        encoding="utf-8",
    )
    routes = load_routing_graph(table_path)
    assert routes["foo"].secondary is None
    assert routes["bar"].secondary == "agent-c"


def test_duplicate_domain_raises(tmp_path: Path) -> None:
    """ValueError when same domain appears twice in routing table."""
    dup_path = tmp_path / "duplicate.md"
    dup_path.write_text(
        _MINIMAL_TABLE
        + "| safety | philosophy-agent | logic-agent | agent-coordinator |\n"
        + "| safety | backend-engineer  |             | bug-hunter         |\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate domain in routing graph: safety"):
        load_routing_graph(dup_path)


def test_parses_all_known_domains() -> None:
    """All domains from AGENT_ROUTING_GRAPH section 3 must be present."""
    routes = load_routing_graph()
    expected = {
        "backend",
        "ios",
        "frontend",
        "infra",
        "security",
        "ml",
        "docs",
        "design",
        "research",
        "safety",
    }
    assert expected.issubset(set(routes.keys()))


def test_domain_normalized_to_lowercase() -> None:
    """Domain keys must be lowercase for consistent lookup."""
    routes = load_routing_graph()
    for key in routes.keys():
        assert key == key.lower(), f"Domain key must be lowercase: {key!r}"


def test_route_normalizes_domain_lookup() -> None:
    """route() must resolve 'Safety' and 'safety' to same canonical route."""
    routing = load_routing_graph()
    d1 = route("Safety", "test", telemetry=None, routing=routing)
    d2 = route("safety", "test", telemetry=None, routing=routing)
    assert d1.primary == d2.primary == "philosophy-agent"


def test_route_keeps_canonical_primary_when_suggested_primary_not_stable() -> None:
    """When suggested_primary exists but telemetry is not STABLE, use canonical."""
    routing = load_routing_graph()
    telemetry = {
        "domains": {
            "safety": {"primary_suggested": "logic-agent", "secondary_suggested": None},
        },
        "agents": {"logic-agent": {"stability": "LOW_DATA"}},
    }
    d = route("safety", "test", telemetry=telemetry, routing=routing)
    assert d.primary == "philosophy-agent"
    assert d.rationale["primary_reason"] == "telemetry_primary_low_data_fallback_canonical"


def test_route_uses_telemetry_secondary_only_when_stable() -> None:
    """Secondary override only when suggested_secondary has STABLE telemetry."""
    routing = load_routing_graph()
    telemetry = {
        "domains": {
            "safety": {"primary_suggested": None, "secondary_suggested": "logic-agent"},
        },
        "agents": {"logic-agent": {"stability": "STABLE"}},
    }
    d = route("safety", "test", telemetry=telemetry, routing=routing)
    assert d.secondary == "logic-agent"
    assert d.rationale["secondary_reason"] == "telemetry_secondary_stable"


def test_route_fallback_canonical_secondary_when_suggested_not_stable() -> None:
    """When suggested_secondary exists but not STABLE, use canonical secondary."""
    routing = load_routing_graph()
    telemetry = {
        "domains": {
            "safety": {"primary_suggested": None, "secondary_suggested": "backend-engineer"},
        },
        "agents": {"backend-engineer": {"stability": "LOW_DATA"}},
    }
    d = route("safety", "test", telemetry=telemetry, routing=routing)
    assert d.secondary == "logic-agent"
    assert d.rationale["secondary_reason"] == "telemetry_secondary_low_data_fallback_canonical"


def test_route_escalates_reviewer_on_low_avg_score() -> None:
    """Reviewer escalates when primary avg_score < 0.70 and stable."""
    routing = load_routing_graph()
    telemetry = {
        "domains": {"backend": {"primary_suggested": "architecture-specialist"}},
        "agents": {
            "architecture-specialist": {
                "stability": "STABLE",
                "avg_score": 0.5,
                "meta": {"runs": 10, "decision_REWRITE_REQUIRED": 0},
            },
        },
    }
    d = route("backend", "test", telemetry=telemetry, routing=routing)
    assert d.reviewer == "architecture-specialist"
    assert d.rationale["reviewer_reason"] == "primary_avg_score_low"


def test_route_escalates_reviewer_on_high_rewrite_rate() -> None:
    """Reviewer escalates when primary rewrite_rate > 0.25 and stable."""
    routing = load_routing_graph()
    telemetry = {
        "domains": {"backend": {"primary_suggested": "architecture-specialist"}},
        "agents": {
            "architecture-specialist": {
                "stability": "STABLE",
                "avg_score": 0.9,
                "meta": {"runs": 10, "decision_REWRITE_REQUIRED": 4},
            },
        },
    }
    d = route("backend", "test", telemetry=telemetry, routing=routing)
    assert d.reviewer == "architecture-specialist"
    assert d.rationale["reviewer_reason"] == "primary_rewrite_rate_high"


def test_route_ignores_non_numeric_rewrite_meta_without_crashing() -> None:
    """Malformed meta (non-numeric runs/rewrites) must not crash; fallback to 0."""
    routing = load_routing_graph()
    telemetry = {
        "domains": {"backend": {"primary_suggested": "architecture-specialist"}},
        "agents": {
            "architecture-specialist": {
                "stability": "STABLE",
                "avg_score": 0.9,
                "meta": {"runs": "N/A", "decision_REWRITE_REQUIRED": "invalid"},
            },
        },
    }
    d = route("backend", "test", telemetry=telemetry, routing=routing)
    assert d.primary == "architecture-specialist"
    assert d.rationale["primary_stats"]["rewrite_rate"] == 0.0
