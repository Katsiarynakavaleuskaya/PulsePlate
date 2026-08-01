"""Documentation registry guards for agent surfaces.

Goal: prevent drift between canonical agent specs and the documented indexes/maps.

This is a guard-style test (deterministic, repo-local) similar in spirit to
`tests/test_repo_policy_guards.py`.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

LESSON_33_HEADING = "## 33) Scope dependency remediation by invariant class, not advisory variant"
APPLICATION_POLICY_HEADING = "**Security: Dependency CVE bumps (application deps):**"
APPLICATION_POLICY_END = "**Security: Yanked packages on PyPI:**"
LESSON_33_END = "## Repo Commands Reference"
SECURITY_PARENT_START = "## Security: Unfixed Distro CVE Policy"
SECURITY_PARENT_END = "## CI: GitHub Container Registry (GHCR) Policy"
ADMISSION_AUTHORITY_START = "<!-- dependency-remediation-admission:v1:start -->"
ADMISSION_AUTHORITY_END = "<!-- dependency-remediation-admission:v1:end -->"


@dataclass(frozen=True)
class AgentSpec:
    file_relpath: str
    name: str


def _read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8", errors="replace")


def _exact_bounded_section(document: str, *, start_line: str, end_line: str) -> str:
    """Return content between unique, ordered, exact standalone boundary lines."""
    lines = document.splitlines()
    start_matches = [index for index, line in enumerate(lines) if line == start_line]
    end_matches = [index for index, line in enumerate(lines) if line == end_line]

    assert len(start_matches) == 1, (
        f"Expected one exact standalone start line {start_line!r}; " f"found {len(start_matches)}"
    )
    assert (
        len(end_matches) == 1
    ), f"Expected one exact standalone end line {end_line!r}; found {len(end_matches)}"

    start_index = start_matches[0]
    end_index = end_matches[0]
    assert (
        start_index < end_index
    ), f"Section boundaries are out of order: {start_line!r} must precede {end_line!r}"
    return "\n".join(lines[start_index + 1 : end_index])


def _extract_dependency_security_sections(agents_md: str, lessons_md: str) -> tuple[str, str, str]:
    """Return exact application, lesson, and closed Security-parent regions."""
    remediation = _exact_bounded_section(
        agents_md,
        start_line=APPLICATION_POLICY_HEADING,
        end_line=APPLICATION_POLICY_END,
    )
    lesson = _exact_bounded_section(
        lessons_md,
        start_line=LESSON_33_HEADING,
        end_line=LESSON_33_END,
    )
    security_parent = _exact_bounded_section(
        agents_md,
        start_line=SECURITY_PARENT_START,
        end_line=SECURITY_PARENT_END,
    )
    return remediation, lesson, security_parent


# SHA-256 binds the whitespace-normalized content of each bounded canonical block.
# A reviewed normative change must update its document and this digest together.
_EXPECTED_SECTION_DIGESTS = {
    "AGENTS Security parent region": "10b7cdcd82c3dee44245231f6cc93a5bc27820ed77f5d3992c77c1a6a45a73c4",  # pragma: allowlist secret
    "engineering lesson 33": "09b0e31c1aef3fae96a68d786270b414a4da611fbfa82397bfc3b7c081160a04",  # pragma: allowlist secret
}
_EXPECTED_ADMISSION_AUTHORITY = {
    "schema": "pulseplate.dependency_remediation_admission.v1",
    "dependency_identities": 1,
    "ecosystems": 1,
    "surfaces": "complete_mechanically_enumerated",
    "advisory_inventory": "finite_reconciled_at_recorded_cutoff",
    "occurrences": "all_resolved_outside_each_affected_range_or_executable_absence",
    "unparseable_or_unresolved": "fail",
    "same_floor_required": False,
    "evidence_owner": "exactly_one_docs_security_document",
    "per_advisory_evidence": "required",
    "suppression_may_mix": False,
}


def _normalized(document: str) -> str:
    return " ".join(document.split())


def _section_digest(document: str) -> str:
    return hashlib.sha256(_normalized(document).encode()).hexdigest()


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for key, value in pairs:
        if key in parsed:
            raise ValueError(f"duplicate JSON key {key!r}")
        parsed[key] = value
    return parsed


def _parse_dependency_remediation_authority(
    agents_md: str, remediation_section: str
) -> dict[str, object]:
    authority_block = _exact_bounded_section(
        agents_md,
        start_line=ADMISSION_AUTHORITY_START,
        end_line=ADMISSION_AUTHORITY_END,
    )
    assert remediation_section.splitlines().count(ADMISSION_AUTHORITY_START) == 1
    assert remediation_section.splitlines().count(ADMISSION_AUTHORITY_END) == 1

    fenced = authority_block.strip()
    assert fenced.startswith("```json\n"), "Admission authority must start with exact ```json fence"
    assert fenced.endswith("\n```"), "Admission authority must end with exact ``` fence"
    payload = fenced.removeprefix("```json\n").removesuffix("\n```")
    try:
        parsed = json.loads(payload, object_pairs_hook=_reject_duplicate_json_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise AssertionError(f"Admission authority contains invalid JSON: {exc}") from exc
    assert isinstance(parsed, dict), "Admission authority JSON must be an object"

    actual_keys = set(parsed)
    expected_keys = set(_EXPECTED_ADMISSION_AUTHORITY)
    assert actual_keys == expected_keys, (
        "Admission authority key set mismatch: "
        f"missing={sorted(expected_keys - actual_keys)}, "
        f"unexpected={sorted(actual_keys - expected_keys)}"
    )
    for key, expected in _EXPECTED_ADMISSION_AUTHORITY.items():
        actual = parsed[key]
        assert type(actual) is type(expected), (
            f"Admission authority field {key!r} type mismatch: "
            f"expected {type(expected).__name__}, got {type(actual).__name__}"
        )
        assert actual == expected, (
            f"Admission authority field {key!r} value mismatch: "
            f"expected {expected!r}, got {actual!r}"
        )
    return parsed


def _validate_dependency_security_policy(agents_md: str, lessons_md: str) -> None:
    """Validate the structured authority and its closed, content-bound parent regions."""
    remediation, lesson, security_parent = _extract_dependency_security_sections(
        agents_md, lessons_md
    )
    authority = _parse_dependency_remediation_authority(agents_md, remediation)
    assert authority == _EXPECTED_ADMISSION_AUTHORITY, (
        "Dependency remediation admission authority changed: "
        f"expected {_EXPECTED_ADMISSION_AUTHORITY}, got {authority}"
    )

    sections = (
        ("AGENTS Security parent region", security_parent),
        ("engineering lesson 33", lesson),
    )
    for section_name, section in sections:
        actual_digest = _section_digest(section)
        assert actual_digest == _EXPECTED_SECTION_DIGESTS[section_name], (
            f"{section_name} changed outside the exact reviewed canonical block; "
            f"expected {_EXPECTED_SECTION_DIGESTS[section_name]}, got {actual_digest}"
        )


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


def test_agent_coordinator_uses_packet_dispatch_manifest_command() -> None:
    """Coordinator docs must not flatten packet runtime-owner dispatch flags."""

    coordinator_md = _read(".cursor/agents/agent-coordinator.md")

    assert "role_agent_dispatch_contract.dispatch_manifest_command" in coordinator_md
    assert "`--mode runtime --implementation-owner ...`" in coordinator_md
    assert "Do not reconstruct a generic bridge command" in coordinator_md
    assert (
        "python scripts/orchestration/role_dispatch_bridge.py --packet <packet> --pretty"
        not in coordinator_md
    )


_SUPPRESSION_MUTATIONS = (
    pytest.param("must be CVE-scoped", "may be CVE-scoped", id="optional-suppression"),
    pytest.param(
        "one PR per CVE (doc + policy rule)",
        "one PR may cover multiple CVEs with one policy rule",
        id="multi-CVE-suppression",
    ),
    pytest.param(
        "no suppression additions required",
        "suppression additions are allowed",
        id="changed-base-image-exception",
    ),
)
_AUTHORITY_FIELD_MUTATIONS = (
    pytest.param(
        "pulseplate.dependency_remediation_admission.v1",
        "pulseplate.dependency_remediation_admission.v2",
        id="wrong-schema",
    ),
    pytest.param('"dependency_identities": 1', '"dependency_identities": 2', id="plural-D"),
    pytest.param('"ecosystems": 1', '"ecosystems": 2', id="plural-ecosystems"),
    pytest.param(
        '"surfaces": "complete_mechanically_enumerated"',
        '"surfaces": "representative_sample"',
        id="partial-surfaces",
    ),
    pytest.param(
        '"advisory_inventory": "finite_reconciled_at_recorded_cutoff"',
        '"advisory_inventory": "declared_without_reconciliation"',
        id="unreconciled-inventory",
    ),
    pytest.param(
        '"occurrences": "all_resolved_outside_each_affected_range_or_executable_absence"',
        '"occurrences": "one_representative_resolution"',
        id="partial-occurrences",
    ),
    pytest.param(
        '"unparseable_or_unresolved": "fail"',
        '"unparseable_or_unresolved": "allow"',
        id="allow-unresolved",
    ),
    pytest.param('"same_floor_required": false', '"same_floor_required": true', id="same-floor"),
    pytest.param(
        '"evidence_owner": "exactly_one_docs_security_document"',
        '"evidence_owner": "pr_body_or_issue"',
        id="evidence-owner-escape",
    ),
    pytest.param(
        '"per_advisory_evidence": "required"',
        '"per_advisory_evidence": "shared_aggregate"',
        id="shared-evidence",
    ),
    pytest.param(
        '"suppression_may_mix": false',
        '"suppression_may_mix": true',
        id="mix-suppression",
    ),
)
_STRICT_JSON_MUTATIONS = (
    pytest.param(
        '"dependency_identities": 1',
        '"dependency_identities": true',
        r"dependency_identities.*expected int, got bool",
        id="identity-bool",
    ),
    pytest.param(
        '"dependency_identities": 1',
        '"dependency_identities": 1.0',
        r"dependency_identities.*expected int, got float",
        id="identity-float",
    ),
    pytest.param(
        '"same_floor_required": false',
        '"same_floor_required": 0',
        r"same_floor_required.*expected bool, got int",
        id="same-floor-int",
    ),
    pytest.param(
        '"suppression_may_mix": false',
        '"suppression_may_mix": 0',
        r"suppression_may_mix.*expected bool, got int",
        id="suppression-int",
    ),
    pytest.param(
        '"dependency_identities": 1,',
        '"dependency_identities": 2,\n  "dependency_identities": 1,',
        r"duplicate JSON key 'dependency_identities'",
        id="duplicate-identity-last-expected",
    ),
    pytest.param(
        '"same_floor_required": false,',
        '"same_floor_required": true,\n  "same_floor_required": false,',
        r"duplicate JSON key 'same_floor_required'",
        id="duplicate-bool-last-expected",
    ),
    pytest.param(
        '  "per_advisory_evidence": "required",\n',
        "",
        r"key set mismatch",
        id="missing-key",
    ),
    pytest.param(
        '"suppression_may_mix": false',
        '"unexpected": true,\n  "suppression_may_mix": false',
        r"key set mismatch",
        id="unexpected-key",
    ),
)
_MARKER_MUTATIONS = (
    pytest.param(ADMISSION_AUTHORITY_START, "", id="missing-start"),
    pytest.param(ADMISSION_AUTHORITY_END, "", id="missing-end"),
    pytest.param(
        ADMISSION_AUTHORITY_START,
        f"{ADMISSION_AUTHORITY_START}\n{ADMISSION_AUTHORITY_START}",
        id="duplicate-start",
    ),
    pytest.param(
        ADMISSION_AUTHORITY_END,
        f"{ADMISSION_AUTHORITY_END}\n{ADMISSION_AUTHORITY_END}",
        id="duplicate-end",
    ),
)
_OUTSIDE_ENGLISH_VARIANTS = (
    "Sharing the same minimum fixed version does not authorize or justify batching.",
    "Identical advisory remediation floors are not required for batching.",
    "Advisories may batch only when they have the same minimum fixed version.",
    "A common patched release is necessary before advisories can share a PR.",
)


def _current_dependency_policy_docs() -> tuple[str, str]:
    return _read("AGENTS.md"), _read("docs/ENGINEERING_LESSONS.md")


def _insert_before_unique(document: str, boundary: str, statement: str) -> str:
    assert document.count(boundary) == 1
    return document.replace(boundary, f"{statement}\n\n{boundary}", 1)


def _replace_unique(document: str, old: str, new: str) -> str:
    assert document.count(old) == 1
    return document.replace(old, new, 1)


def test_dependency_security_policy_scopes_remediation_by_dsp_class() -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    remediation, _lesson, _parent = _extract_dependency_security_sections(agents_md, lessons_md)
    assert (
        _parse_dependency_remediation_authority(agents_md, remediation)
        == _EXPECTED_ADMISSION_AUTHORITY
    )
    _validate_dependency_security_policy(agents_md, lessons_md)


def test_dependency_security_policy_rejects_lesson_region_change() -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    mutated = _insert_before_unique(
        lessons_md,
        LESSON_33_END,
        "## 34) Future dependency policy\n\nSentence variants redefine the admission relation.",
    )
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(agents_md, mutated)


@pytest.mark.parametrize(("old", "new"), _AUTHORITY_FIELD_MUTATIONS)
def test_dependency_security_policy_rejects_structured_authority_mutations(
    old: str, new: str
) -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(_replace_unique(agents_md, old, new), lessons_md)


@pytest.mark.parametrize(("old", "new", "diagnostic"), _STRICT_JSON_MUTATIONS)
def test_dependency_security_policy_rejects_json_coercion_and_duplicate_keys(
    old: str, new: str, diagnostic: str
) -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    mutated = _replace_unique(agents_md, old, new)
    with pytest.raises(AssertionError, match=diagnostic):
        _validate_dependency_security_policy(mutated, lessons_md)


@pytest.mark.parametrize(("old", "new"), _MARKER_MUTATIONS)
def test_dependency_security_policy_rejects_missing_or_duplicate_authority_markers(
    old: str, new: str
) -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(_replace_unique(agents_md, old, new), lessons_md)


def test_dependency_security_policy_rejects_invalid_authority_json() -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    invalid = _replace_unique(agents_md, '"dependency_identities": 1', '"dependency_identities": ,')
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(invalid, lessons_md)


# English variants are not admission logic. The exact JSON relation is the sole
# machine-readable authority; parent-region digests close surrounding policy prose.
@pytest.mark.parametrize("statement", _OUTSIDE_ENGLISH_VARIANTS)
def test_dependency_security_policy_ignores_english_variants_outside_authority(
    statement: str,
) -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    _validate_dependency_security_policy(f"{agents_md}\n{statement}", lessons_md)


@pytest.mark.parametrize(("old", "new"), _SUPPRESSION_MUTATIONS)
def test_dependency_security_policy_preserves_suppression_scope(old: str, new: str) -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    assert agents_md.count(old) == 1
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(agents_md.replace(old, new, 1), lessons_md)


def test_dependency_security_policy_rejects_fenced_decoy() -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    decoy = "```markdown\n**Security: Retired dependency policy:**\nRetired policy wording.\n```"
    mutated = _insert_before_unique(agents_md, APPLICATION_POLICY_END, decoy)
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(mutated, lessons_md)


def test_dependency_security_policy_rejects_duplicate_expected_end() -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    duplicate = agents_md.replace(
        APPLICATION_POLICY_END,
        f"{APPLICATION_POLICY_END}\n\n{APPLICATION_POLICY_END}",
        1,
    )
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(duplicate, lessons_md)


def test_dependency_security_policy_rejects_post_application_parent_change() -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    contradiction = "`P` may ignore unresolved occurrences after the application section."
    mutated = _replace_unique(
        agents_md,
        APPLICATION_POLICY_END,
        f"{APPLICATION_POLICY_END}\n\n{contradiction}",
    )
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(mutated, lessons_md)
