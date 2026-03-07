"""Tests for routing graph loader (canonical docs/orchestration/AGENT_ROUTING_GRAPH.md)."""

from pathlib import Path

import pytest

from scripts.orchestration.routing_graph_loader import (
    DomainRoute,
    load_declared_clusters,
    load_routing_graph,
)
from scripts.orchestration.route_with_telemetry import route

_MINIMAL_CLUSTER_DEFINITIONS = (
    "| Cluster | Purpose |\n"
    "|---------|---------|\n"
    "| ops     | Operations routing. |\n"
    "| growth  | Growth routing. |\n"
    "\n"
)

_MINIMAL_TABLE = (
    "| Domain   | Cluster | Primary Agent   | Secondary | Reviewer |\n"
    "|----------|---------|-----------------|-----------|----------|\n"
)


def test_parses_safety_domain() -> None:
    """Safety domain must exist with non-empty primary and reviewer."""
    routes = load_routing_graph()
    assert "safety" in routes
    assert routes["safety"].cluster == "safety"
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
        + _MINIMAL_CLUSTER_DEFINITIONS
        + "Some introductory text, but no routing table header.\n\n"
        + "| something | else |\n"
        + "| --------- | ---- |\n"
        + "| foo       | bar  |\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Routing graph table header not found"):
        load_routing_graph(bad_path)


def test_no_routing_rows_raises(tmp_path: Path) -> None:
    """ValueError when header exists but no routing rows are parsed."""
    empty_table_path = tmp_path / "no_rows.md"
    empty_table_path.write_text(
        "# Routing Graph\n\n"
        + _MINIMAL_CLUSTER_DEFINITIONS
        + "| domain | cluster | primary | secondary | reviewer |\n"
        + "| ------ | ------- | ------- | --------- | -------- |\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="No routing rows parsed from routing graph"):
        load_routing_graph(empty_table_path)


def test_secondary_empty_yields_none(tmp_path: Path) -> None:
    """Empty secondary cell must yield None; non-empty yields agent name."""
    table_path = tmp_path / "secondary_test.md"
    table_path.write_text(
        _MINIMAL_CLUSTER_DEFINITIONS
        + _MINIMAL_TABLE
        + "| foo | ops | agent-a |           | reviewer-a |\n"
        + "| bar | growth | agent-b | agent-c    | reviewer-b |\n",
        encoding="utf-8",
    )
    routes = load_routing_graph(table_path)
    assert routes["foo"].cluster == "ops"
    assert routes["foo"].secondary is None
    assert routes["bar"].secondary == "agent-c"


def test_duplicate_domain_raises(tmp_path: Path) -> None:
    """ValueError when same domain appears twice in routing table."""
    dup_path = tmp_path / "duplicate.md"
    dup_path.write_text(
        "# Routing Graph\n\n"
        + "| Cluster | Purpose |\n"
        + "|---------|---------|\n"
        + "| safety  | Safety routing. |\n"
        + "| backend | Backend routing. |\n\n"
        + _MINIMAL_TABLE
        + "| safety | safety | philosophy-agent | logic-agent | agent-coordinator |\n"
        + "| safety | backend | backend-engineer  |             | bug-hunter         |\n",
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


def test_load_declared_clusters_parses_cluster_definition_table() -> None:
    """Declared cluster table should be readable as its own canonical set."""

    declared = load_declared_clusters()
    assert declared == {"backend", "platform", "ops", "ml", "safety", "growth"}


def test_duplicate_cluster_definition_raises(tmp_path: Path) -> None:
    """Duplicate cluster rows must fail cluster SoT validation."""

    dup_cluster_path = tmp_path / "duplicate_cluster.md"
    dup_cluster_path.write_text(
        "# Routing Graph\n\n"
        + "| Cluster | Purpose |\n"
        + "|---------|---------|\n"
        + "| ops     | Operations routing. |\n"
        + "| ops     | Duplicate operations routing. |\n\n"
        + _MINIMAL_TABLE
        + "| docs | ops | agent-a | | reviewer-a |\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate cluster definition in routing graph: ops"):
        load_routing_graph(dup_cluster_path)


def test_undefined_cluster_reference_raises(tmp_path: Path) -> None:
    """Routing rows must reference a declared cluster slug."""

    undefined_cluster_path = tmp_path / "undefined_cluster.md"
    undefined_cluster_path.write_text(
        "# Routing Graph\n\n"
        + _MINIMAL_CLUSTER_DEFINITIONS
        + _MINIMAL_TABLE
        + "| docs | safety | agent-a | | reviewer-a |\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Routing domain references undefined cluster: docs -> safety",
    ):
        load_routing_graph(undefined_cluster_path)


def test_missing_cluster_definitions_section_raises(tmp_path: Path) -> None:
    """Cluster definitions are mandatory before parsing routed domains."""

    missing_clusters_path = tmp_path / "missing_clusters.md"
    missing_clusters_path.write_text(
        "# Routing Graph\n\n" + _MINIMAL_TABLE + "| docs | ops | agent-a | | reviewer-a |\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Cluster definitions table is missing or empty"):
        load_routing_graph(missing_clusters_path)


def test_unused_declared_cluster_raises(tmp_path: Path) -> None:
    """Every declared cluster must be referenced by at least one routed domain."""

    unused_cluster_path = tmp_path / "unused_cluster.md"
    unused_cluster_path.write_text(
        "# Routing Graph\n\n"
        + _MINIMAL_CLUSTER_DEFINITIONS
        + _MINIMAL_TABLE
        + "| docs | ops | agent-a | | reviewer-a |\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Declared clusters unused in routing graph: growth"):
        load_routing_graph(unused_cluster_path)


def test_route_normalizes_domain_lookup() -> None:
    """route() must resolve 'Safety' and 'safety' to same canonical route."""
    routing = load_routing_graph()
    d1 = route("Safety", "test", telemetry=None, routing=routing)
    d2 = route("safety", "test", telemetry=None, routing=routing)
    assert d1.primary == d2.primary == "philosophy-agent"
    assert d1.cluster == d2.cluster == "safety"


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


def test_route_enforces_independent_safety_reviewer() -> None:
    """Safety routing must keep reviewer independent from the primary agent."""
    routing = load_routing_graph()
    telemetry = {
        "domains": {"safety": {"primary_suggested": "philosophy-agent"}},
        "agents": {
            "philosophy-agent": {
                "stability": "STABLE",
                "avg_score": 0.3,
                "meta": {"runs": 8, "decision_REWRITE_REQUIRED": 1},
            }
        },
    }
    d = route("safety", "test", telemetry=telemetry, routing=routing)
    assert d.primary == "philosophy-agent"
    assert d.reviewer == "logic-agent"
    assert d.reviewer != d.primary


def test_route_uses_canonical_safety_secondary_for_reviewer() -> None:
    """Safety reviewer should come from canonical routing, not hardcoded agent names."""

    routing = {
        "safety": DomainRoute(
            cluster="safety",
            primary="philosophy-agent",
            secondary="safety-reviewer-agent",
            reviewer="agent-coordinator",
        )
    }
    telemetry = {
        "domains": {"safety": {"primary_suggested": "philosophy-agent"}},
        "agents": {
            "philosophy-agent": {
                "stability": "STABLE",
                "avg_score": 0.95,
                "meta": {"runs": 12, "decision_REWRITE_REQUIRED": 0},
            }
        },
    }

    d = route("safety", "test", telemetry=telemetry, routing=routing)
    assert d.reviewer == "safety-reviewer-agent"
    assert d.rationale["reviewer_reason"] == "domain_safety_independent_review"


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
    assert d.reviewer == "security-auditor"
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
    assert d.reviewer == "security-auditor"
    assert d.rationale["reviewer_reason"] == "primary_rewrite_rate_high"


def test_route_keeps_unknown_domain_coordinator_fallback_when_telemetry_missing_domain() -> None:
    """Unknown domains should keep canonical coordinator fallback untouched."""

    routing = load_routing_graph()
    telemetry = {
        "domains": {
            "backend": {"primary_suggested": "architecture-specialist"},
        },
        "agents": {
            "architecture-specialist": {
                "stability": "STABLE",
                "avg_score": 0.99,
                "meta": {"runs": 5, "decision_REWRITE_REQUIRED": 0},
            }
        },
    }

    d = route("unknown-domain", "test", telemetry=telemetry, routing=routing)
    assert d.cluster == "ops"
    assert d.primary == "agent-coordinator"
    assert d.reviewer == "agent-coordinator"
    assert d.rationale == {"source": "canonical_only"}


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
