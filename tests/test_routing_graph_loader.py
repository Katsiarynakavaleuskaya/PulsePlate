"""Tests for routing graph loader (canonical docs/orchestration/AGENT_ROUTING_GRAPH.md)."""

from pathlib import Path

import pytest

from scripts.orchestration.routing_graph_loader import load_routing_graph


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
