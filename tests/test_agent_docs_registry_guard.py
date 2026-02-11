"""Documentation registry guards for agent surfaces.

Goal: prevent drift between canonical agent specs and the documented indexes/maps.

This is a guard-style test (deterministic, repo-local) similar in spirit to
`tests/test_repo_policy_guards.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AgentSpec:
    file_relpath: str
    name: str


def _read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8", errors="replace")


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _parse_frontmatter_name(content: str) -> str | None:
    """Return `name:` from YAML frontmatter, or None if absent."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    # Parse until the closing `---` (frontmatter end).
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        m = re.match(r"^\s*name:\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def _is_markdown_table_separator_row(line: str) -> bool:
    """Return True for markdown separator rows like: |---|, |:---|, |---:|, |:---:|."""
    core = line.replace("|", "").strip()
    if not core:
        return False
    core_no_ws = core.replace(" ", "")
    # Must contain at least one dash, and only use '-' / ':' for alignment.
    return "-" in core_no_ws and set(core_no_ws) <= {"-", ":"}


def _load_agent_specs() -> tuple[list[AgentSpec], list[str]]:
    """Return (agent_specs, non_agent_files) from `.cursor/agents/*.md`."""
    agent_dir = REPO_ROOT / ".cursor/agents"
    specs: list[AgentSpec] = []
    non_agent: list[str] = []

    for path in sorted(agent_dir.glob("*.md")):
        rel = _rel(path)
        name = _parse_frontmatter_name(path.read_text(encoding="utf-8", errors="replace"))
        if name is None:
            non_agent.append(rel)
            continue
        specs.append(AgentSpec(file_relpath=rel, name=name))

    return specs, non_agent


def _parse_agent_index_names(index_md: str) -> list[str]:
    """Parse agent `name` values from the '## Available Agents' table in `docs/agents/index.md`."""
    names: list[str] = []

    in_available_agents_section = False
    in_agent_table = False

    for raw in index_md.splitlines():
        line = raw.strip()

        if line.startswith("## "):
            if line == "## Available Agents":
                in_available_agents_section = True
                in_agent_table = False
                continue
            if in_available_agents_section:
                break

        if not in_available_agents_section:
            continue

        if not line.startswith("|"):
            # Stop once we've left the agent table (prevents misparsing other content).
            if in_agent_table:
                break
            continue

        if line.startswith("| Agent |"):
            in_agent_table = True
            continue
        if _is_markdown_table_separator_row(line):
            in_agent_table = True
            continue

        in_agent_table = True
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        if first:
            names.append(first)

    return names


def _parse_context_map_agent_names(context_map_md: str) -> list[str]:
    """Extract agent names from headings like: `### X (`agent-name`)`."""
    names: list[str] = []
    heading_re = re.compile(r"^### .*\(`(?P<name>[a-z0-9-]+)`\)\s*$")
    for raw in context_map_md.splitlines():
        m = heading_re.match(raw.strip())
        if m:
            names.append(m.group("name"))
    return names


def test_agent_specs_are_registered_in_index_and_context_map() -> None:
    specs, non_agent_files = _load_agent_specs()
    non_agent_set = set(non_agent_files)
    assert non_agent_set <= {".cursor/agents/AGENTS.md"}, (
        "Unexpected .cursor/agents/*.md without frontmatter `name:`. "
        f"Allowed: .cursor/agents/AGENTS.md. Found: {sorted(non_agent_set)}"
    )

    spec_names = sorted({s.name for s in specs})
    assert len(spec_names) == len(specs), "Duplicate agent `name:` values in .cursor/agents/*.md"

    index_names = _parse_agent_index_names(_read("docs/agents/index.md"))
    assert len(index_names) == len(
        set(index_names)
    ), "Duplicate agent names in docs/agents/index.md"

    context_names = _parse_context_map_agent_names(_read("docs/orchestration/AGENT_CONTEXT_MAP.md"))
    assert len(context_names) == len(
        set(context_names)
    ), "Duplicate agent headings in docs/orchestration/AGENT_CONTEXT_MAP.md"

    missing_in_index = sorted(set(spec_names) - set(index_names))
    extra_in_index = sorted(set(index_names) - set(spec_names))
    assert not missing_in_index and not extra_in_index, (
        "Agent index drift detected.\n"
        f"- missing_in_index: {missing_in_index}\n"
        f"- extra_in_index: {extra_in_index}\n"
        "Fix: update docs/agents/index.md to match .cursor/agents/*.md"
    )

    missing_in_context = sorted(set(spec_names) - set(context_names))
    extra_in_context = sorted(set(context_names) - set(spec_names))
    assert not missing_in_context and not extra_in_context, (
        "Agent context map drift detected.\n"
        f"- missing_in_context: {missing_in_context}\n"
        f"- extra_in_context: {extra_in_context}\n"
        "Fix: update docs/orchestration/AGENT_CONTEXT_MAP.md to match .cursor/agents/*.md"
    )


def test_canonical_workflow_surfaces_reference_research_protocols() -> None:
    """Prevent accidental removal of canonical protocol links."""
    agents_md = _read("AGENTS.md")
    workflow_md = _read("docs/orchestration/workflow.md")

    required = [
        "docs/orchestration/AGENT_MESSAGE_PROTOCOL.md",
        "docs/orchestration/RESEARCH_TRACK_PROTOCOL.md",
        "docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md",
        "docs/orchestration/AGENT_REFLECTION_PROTOCOL.md",
    ]

    missing_agents = [p for p in required if p not in agents_md]
    assert not missing_agents, f"AGENTS.md missing canonical protocol refs: {missing_agents}"

    missing_workflow = [p for p in required if p not in workflow_md]
    assert not missing_workflow, (
        "docs/orchestration/workflow.md missing canonical protocol refs: " f"{missing_workflow}"
    )
