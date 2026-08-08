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
from html.parser import HTMLParser
from pathlib import Path

import pytest
from markdown_it import MarkdownIt
from markdown_it.token import Token

REPO_ROOT = Path(__file__).resolve().parents[1]

LESSON_33_HEADING = (
    "## 33) Keep one dependency identity by default; batch only an exact scanner snapshot"
)
APPLICATION_POLICY_HEADING = "**Security: Dependency CVE bumps (application deps):**"
APPLICATION_POLICY_END = "**Security: Yanked packages on PyPI:**"
LESSON_33_END = "## Repo Commands Reference"
SECURITY_PARENT_START = "## Security: Unfixed Distro CVE Policy"
SECURITY_PARENT_END = "## CI: GitHub Container Registry (GHCR) Policy"
ADMISSION_AUTHORITY_START = "<!-- dependency-remediation-admission:v2:start -->"
ADMISSION_AUTHORITY_END = "<!-- dependency-remediation-admission:v2:end -->"
EVIDENCE_STATUS_START = "<!-- dependency-remediation-evidence-status:v1:start -->"
EVIDENCE_STATUS_END = "<!-- dependency-remediation-evidence-status:v1:end -->"
HISTORICAL_TITLE = (
    "# CVE-2026-4926 / CVE-2026-4923 / CVE-2026-33750 — npm transitive override remediation"
)
HISTORICAL_SUMMARY_START = "## Summary"
HISTORICAL_SUMMARY_END = "## Why this remediation exists"
HISTORICAL_EVIDENCE_PATH = (
    "docs/security/CVE-2026-4926-path-to-regexp-and-CVE-2026-33750-brace-expansion.md"
)

APPLICATION_POLICY_TEXT = "Security: Dependency CVE bumps (application deps):"
LESSON_33_TEXT = LESSON_33_HEADING.removeprefix("## ")
LESSON_33_END_TEXT = LESSON_33_END.removeprefix("## ")
SECURITY_PARENT_TEXT = SECURITY_PARENT_START.removeprefix("## ")
SECURITY_PARENT_END_TEXT = SECURITY_PARENT_END.removeprefix("## ")
HISTORICAL_TITLE_TEXT = HISTORICAL_TITLE.removeprefix("# ")
HISTORICAL_SUMMARY_TEXT = HISTORICAL_SUMMARY_START.removeprefix("## ")
HISTORICAL_SUMMARY_END_TEXT = HISTORICAL_SUMMARY_END.removeprefix("## ")

_MARKDOWN = MarkdownIt(
    "commonmark",
    {
        "html": True,
        "xhtmlOut": True,
    },
)


@dataclass(frozen=True)
class AgentSpec:
    file_relpath: str
    name: str


def _read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8")


def _normalized_line_endings(document: str) -> str:
    return document.replace("\r\n", "\n").replace("\r", "\n")


def _platform_lines(document: str) -> list[str]:
    """Split only on CommonMark/platform endings: LF, CRLF, and lone CR."""
    return _normalized_line_endings(document).split("\n")


@dataclass(frozen=True)
class MarkdownSpan:
    start: int
    stop: int


@dataclass
class _RenderedCapture:
    tag: str
    parents: tuple[str, ...]
    parts: list[str]


_HTML_VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


class _RenderedAncestryProbe(HTMLParser):
    """Record rendered target ancestry without requiring unrelated XHTML validity."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.captures: list[_RenderedCapture] = []
        self.nodes: dict[str, list[tuple[str, tuple[str, ...]]]] = {
            "h1": [],
            "h2": [],
            "strong": [],
        }
        self.comments: list[tuple[str, tuple[str, ...]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        tag = tag.lower()
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p"} and self.stack[-1:] == ["p"]:
            self.stack.pop()
        if tag in self.nodes:
            self.captures.append(_RenderedCapture(tag, tuple(self.stack), []))
        if tag not in _HTML_VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.captures) - 1, -1, -1):
            capture = self.captures[index]
            if capture.tag == tag:
                del self.captures[index]
                self.nodes[tag].append(("".join(capture.parts), capture.parents))
                break
        if tag in self.stack:
            index = len(self.stack) - 1 - self.stack[::-1].index(tag)
            del self.stack[index:]

    def handle_data(self, data: str) -> None:
        for capture in self.captures:
            capture.parts.append(data)

    def handle_comment(self, data: str) -> None:
        self.comments.append((data, tuple(self.stack)))


def _token_source(lines: list[str], token: Token) -> str:
    assert token.map is not None
    start, stop = token.map
    return "\n".join(lines[start:stop])


def _unique_top_level_block(
    tokens: list[Token],
    lines: list[str],
    *,
    token_type: str,
    source: str,
    tag: str | None = None,
    markup: str | None = None,
) -> MarkdownSpan:
    matches = [
        index
        for index, token in enumerate(tokens)
        if token.type == token_type
        and token.level == 0
        and token.map is not None
        and (tag is None or token.tag == tag)
        and (markup is None or token.markup == markup)
        and _token_source(lines, token) == source
    ]
    assert len(matches) == 1, f"Expected one exact top-level Markdown block {source!r}"
    index = matches[0]
    if token_type in {"heading_open", "paragraph_open"}:
        expected_close = token_type.removesuffix("_open") + "_close"
        assert tokens[index + 2].type == expected_close
        return MarkdownSpan(index, index + 3)
    return MarkdownSpan(index, index + 1)


def _unique_top_level_json_triplet(
    tokens: list[Token],
    lines: list[str],
    *,
    start_marker: str,
    end_marker: str,
) -> MarkdownSpan:
    start = _unique_top_level_block(
        tokens,
        lines,
        token_type="html_block",
        source=start_marker,
    )
    end = _unique_top_level_block(
        tokens,
        lines,
        token_type="html_block",
        source=end_marker,
    )
    assert end.start == start.stop + 1
    fence = tokens[start.stop]
    assert fence.type == "fence"
    assert fence.level == 0
    assert fence.markup == "```"
    assert fence.info.strip() == "json"
    assert fence.map is not None
    fence_lines = _token_source(lines, fence).splitlines()
    assert fence_lines[0] == "```json"
    assert fence_lines[-1] == "```"
    assert tokens[start.start].map is not None
    assert tokens[end.start].map is not None
    assert tokens[start.start].map[1] == fence.map[0]
    assert fence.map[1] == tokens[end.start].map[0]
    return MarkdownSpan(start.start, end.stop)


def _assert_next_top_level_section_heading(
    tokens: list[Token], *, start_index: int, expected_index: int
) -> None:
    peer_indices = [
        index
        for index, token in enumerate(tokens)
        if token.type == "heading_open" and token.level == 0 and token.tag in {"h1", "h2"}
    ]
    later_peers = [index for index in peer_indices if index > start_index]
    assert later_peers and later_peers[0] == expected_index


def _assert_rendered_root_targets(
    tokens: list[Token],
    *,
    through: int,
    h1_texts: tuple[str, ...] = (),
    h2_texts: tuple[str, ...] = (),
    strong_texts: tuple[str, ...] = (),
    comment_markers: tuple[str, ...] = (),
) -> None:
    rendered = _MARKDOWN.renderer.render(tokens[:through], _MARKDOWN.options, {})
    probe = _RenderedAncestryProbe()
    probe.feed(rendered)
    probe.close()
    for text in h1_texts:
        matches = [parents for content, parents in probe.nodes["h1"] if content == text]
        assert matches == [()], f"Rendered H1 {text!r} is not one direct-root node"
    for text in h2_texts:
        matches = [parents for content, parents in probe.nodes["h2"] if content == text]
        assert matches == [()], f"Rendered H2 {text!r} is not one direct-root node"
    for text in strong_texts:
        matches = [parents for content, parents in probe.nodes["strong"] if content == text]
        assert matches == [("p",)], f"Rendered strong block {text!r} is not in one root paragraph"
    for marker in comment_markers:
        content = marker.removeprefix("<!--").removesuffix("-->")
        matches = [parents for comment, parents in probe.comments if comment == content]
        assert matches == [()], f"Rendered marker {marker!r} is not one direct-root comment"


def _assert_only_canonical_raw_html(
    tokens: list[Token], *, through: int, allowed_block_sources: tuple[str, ...]
) -> None:
    """Fail closed before protected regions instead of approximating HTML5 repair."""
    html_blocks: list[str] = []
    for token in tokens[:through]:
        assert token.type != "html_inline", "Non-canonical raw HTML precedes protected Markdown"
        if token.type == "html_block":
            html_blocks.append(token.content)
        for child in token.children or ():
            assert child.type != "html_inline", "Non-canonical raw HTML precedes protected Markdown"

    expected_blocks = [f"{source}\n" for source in allowed_block_sources]
    assert html_blocks == expected_blocks, (
        "Protected Markdown prefix contains non-canonical raw HTML blocks: "
        f"expected {expected_blocks!r}, got {html_blocks!r}"
    )


def _assert_dependency_policy_markdown_structure(agents_md: str, lessons_md: str) -> None:
    """Prove canonical policy anchors are exact top-level blocks outside HTML ancestors."""
    agents_lines = _platform_lines(agents_md)
    lesson_lines = _platform_lines(lessons_md)
    agents_tokens = _MARKDOWN.parse("\n".join(agents_lines))
    lesson_tokens = _MARKDOWN.parse("\n".join(lesson_lines))

    security = _unique_top_level_block(
        agents_tokens,
        agents_lines,
        token_type="heading_open",
        tag="h2",
        markup="##",
        source=SECURITY_PARENT_START,
    )
    application = _unique_top_level_block(
        agents_tokens,
        agents_lines,
        token_type="paragraph_open",
        tag="p",
        source=APPLICATION_POLICY_HEADING,
    )
    authority = _unique_top_level_json_triplet(
        agents_tokens,
        agents_lines,
        start_marker=ADMISSION_AUTHORITY_START,
        end_marker=ADMISSION_AUTHORITY_END,
    )
    security_end = _unique_top_level_block(
        agents_tokens,
        agents_lines,
        token_type="heading_open",
        tag="h2",
        markup="##",
        source=SECURITY_PARENT_END,
    )
    assert security.start < application.start < authority.start < security_end.start
    _assert_next_top_level_section_heading(
        agents_tokens,
        start_index=security.start,
        expected_index=security_end.start,
    )
    _assert_only_canonical_raw_html(
        agents_tokens,
        through=security_end.stop,
        allowed_block_sources=(ADMISSION_AUTHORITY_START, ADMISSION_AUTHORITY_END),
    )
    _assert_rendered_root_targets(
        agents_tokens,
        through=security_end.stop,
        h2_texts=(SECURITY_PARENT_TEXT, SECURITY_PARENT_END_TEXT),
        strong_texts=(APPLICATION_POLICY_TEXT,),
        comment_markers=(ADMISSION_AUTHORITY_START, ADMISSION_AUTHORITY_END),
    )

    lesson = _unique_top_level_block(
        lesson_tokens,
        lesson_lines,
        token_type="heading_open",
        tag="h2",
        markup="##",
        source=LESSON_33_HEADING,
    )
    lesson_end = _unique_top_level_block(
        lesson_tokens,
        lesson_lines,
        token_type="heading_open",
        tag="h2",
        markup="##",
        source=LESSON_33_END,
    )
    assert lesson.start < lesson_end.start
    _assert_next_top_level_section_heading(
        lesson_tokens,
        start_index=lesson.start,
        expected_index=lesson_end.start,
    )
    _assert_only_canonical_raw_html(
        lesson_tokens,
        through=lesson_end.stop,
        allowed_block_sources=(),
    )
    _assert_rendered_root_targets(
        lesson_tokens,
        through=lesson_end.stop,
        h2_texts=(LESSON_33_TEXT, LESSON_33_END_TEXT),
    )


def _exact_bounded_section(document: str, *, start_line: str, end_line: str) -> str:
    """Return content between unique, ordered, exact standalone boundary lines."""
    lines = _platform_lines(document)
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


# SHA-256 binds the Markdown-significant structure of each bounded canonical block.
# Only platform line-ending differences are normalized. A reviewed normative change
# must update its document and this digest together.
_EXPECTED_SECTION_DIGESTS = {
    "AGENTS Security parent region": "ae55676b8b2d9d7d99ceae7910665c491f5acba992da36b3ef119f7ab32c1fb8",  # pragma: allowlist secret
    "engineering lesson 33": "538729c57c7c927a8418a231d79a340f790f8f55767ca55e9eebce152bbe9653",  # pragma: allowlist secret
    "historical evidence authority summary": "1f0975a81cc4ddd2e262854ac103e1f8aacbba4deff674ec6540a83c08cbb5a8",  # pragma: allowlist secret
}
_EXPECTED_ADMISSION_AUTHORITY = {
    "schema": "pulseplate.dependency_remediation_admission.v2",
    "default_dependency_identities": 1,
    "ecosystems": 1,
    "batch_exception": "external_operator_exact_immutable_scanner_snapshot_only",
    "policy_effect": "prospective_after_merge",
    "policy_transition_authority": (
        "external_direct_operator_instruction_outside_candidate_diff_exact_transition_only"
    ),
    "policy_transition_grants_future_authority": False,
    "candidate_self_authorization": "forbidden",
    "candidate_authorization_authentication": "forbidden",
    "batch_identity_set": "exact_finite_complete_snapshot_derived_unresolved_set",
    "batch_identity_omission_or_addition": "fail",
    "per_identity_authored_actions": 1,
    "per_identity_action_kinds": "replacement_or_removal",
    "operator_intent_delta_per_identity": "non_empty",
    "literal_target_versions": "parameters_not_classes",
    "material_transition_partition": "per_identity_authored_action_or_deterministic_solver_closure",
    "solver_closure": "exact_canonical_replay_from_exact_base_per_authored_action",
    "solver_closure_independent_intent": "forbidden",
    "manual_unclassified_or_unreplayable_delta": "fail",
    "aggregate_goal_is_postcondition_not_intent": True,
    "surfaces": "non_empty_complete_mechanically_enumerated_base_and_head_per_identity",
    "scanner_snapshot": "one_immutable_external_run_and_analysis",
    "candidate_advisory_inventory": "finite_reconciled_per_identity_at_recorded_snapshot",
    "applicable_advisory_inventory": (
        "non_empty_exactly_all_candidates_with_affected_comparable_base_witness_per_identity"
    ),
    "advisory_applicability_quantifier": (
        "for_every_advisory_exists_affected_comparable_governed_base_occurrence_or_disposition"
    ),
    "non_applicable_candidates": (
        "base_non_applicable_disposition_and_universal_head_safety_check"
    ),
    "disposition_only_lane": ("separate_non_mutating_when_per_identity_applicable_inventory_empty"),
    "remediation_postcondition_inventory": (
        "every_candidate_advisory_in_each_per_identity_F_cutoff"
    ),
    "occurrences": (
        "for_every_F_cutoff_advisory_all_head_occurrences_outside_affected_range_or_"
        "executable_absence"
    ),
    "base_only_surfaces": "reconciled_by_operator_intent_or_solver_closure_or_fail",
    "postcondition": "conjunction_all_per_identity_universal_head_postconditions",
    "partial_success": "fail",
    "unparseable_unresolved_omitted_or_unclassified": "fail",
    "same_floor_required": False,
    "obsolete_suppression_deletion": (
        "only_exact_target_suppression_for_remediated_batch_identity"
    ),
    "suppression_addition_broadening_replacement_or_other_deletion": "forbidden",
    "evidence_owner": "exactly_one_docs_security_batch_document",
    "per_advisory_evidence": "required",
}
_EXPECTED_HISTORICAL_EVIDENCE_STATUS = {
    "schema": "pulseplate.dependency_remediation_evidence_status.v1",
    "evidence_status": "historical",
    "current_scoping_authority": False,
    "future_multi_dependency_batching_authority": False,
    "current_authority_ref": "AGENTS.md::dependency-remediation-admission:v2",
}


def _section_digest(document: str) -> str:
    return hashlib.sha256(_normalized_line_endings(document).encode()).hexdigest()


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
    remediation_lines = _platform_lines(remediation_section)
    assert remediation_lines.count(ADMISSION_AUTHORITY_START) == 1
    assert remediation_lines.count(ADMISSION_AUTHORITY_END) == 1

    fenced = authority_block
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


def _parse_historical_evidence_status(document: str) -> dict[str, object]:
    status_block = _exact_bounded_section(
        document,
        start_line=EVIDENCE_STATUS_START,
        end_line=EVIDENCE_STATUS_END,
    )
    assert ADMISSION_AUTHORITY_START not in document
    assert ADMISSION_AUTHORITY_END not in document
    assert status_block.startswith("```json\n")
    assert status_block.endswith("\n```")
    payload = status_block.removeprefix("```json\n").removesuffix("\n```")
    try:
        parsed = json.loads(payload, object_pairs_hook=_reject_duplicate_json_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise AssertionError(f"Historical evidence status contains invalid JSON: {exc}") from exc
    assert isinstance(parsed, dict)
    assert set(parsed) == set(_EXPECTED_HISTORICAL_EVIDENCE_STATUS)
    for key, expected in _EXPECTED_HISTORICAL_EVIDENCE_STATUS.items():
        actual = parsed[key]
        assert type(actual) is type(expected)
        assert actual == expected
    return parsed


def _validate_historical_evidence_status(document: str) -> None:
    parsed = _parse_historical_evidence_status(document)
    assert parsed == _EXPECTED_HISTORICAL_EVIDENCE_STATUS

    document_lines = _platform_lines(document)
    assert document_lines[0] == HISTORICAL_TITLE
    title_to_summary = _exact_bounded_section(
        document,
        start_line=HISTORICAL_TITLE,
        end_line=HISTORICAL_SUMMARY_START,
    )
    assert title_to_summary == "", (
        "Historical evidence title must be followed directly by its sole "
        "authority-status Summary"
    )
    authority_summary = _exact_bounded_section(
        document,
        start_line=HISTORICAL_SUMMARY_START,
        end_line=HISTORICAL_SUMMARY_END,
    )
    summary_lines = _platform_lines(authority_summary)
    assert summary_lines.count(EVIDENCE_STATUS_START) == 1
    assert summary_lines.count(EVIDENCE_STATUS_END) == 1
    actual_digest = _section_digest(authority_summary)
    assert actual_digest == _EXPECTED_SECTION_DIGESTS["historical evidence authority summary"], (
        "historical evidence authority summary changed outside the exact reviewed "
        "canonical block; expected "
        f"{_EXPECTED_SECTION_DIGESTS['historical evidence authority summary']}, "
        f"got {actual_digest}"
    )

    lines = _platform_lines(document)
    tokens = _MARKDOWN.parse("\n".join(lines))
    title = _unique_top_level_block(
        tokens,
        lines,
        token_type="heading_open",
        tag="h1",
        markup="#",
        source=HISTORICAL_TITLE,
    )
    summary = _unique_top_level_block(
        tokens,
        lines,
        token_type="heading_open",
        tag="h2",
        markup="##",
        source=HISTORICAL_SUMMARY_START,
    )
    status = _unique_top_level_json_triplet(
        tokens,
        lines,
        start_marker=EVIDENCE_STATUS_START,
        end_marker=EVIDENCE_STATUS_END,
    )
    summary_end = _unique_top_level_block(
        tokens,
        lines,
        token_type="heading_open",
        tag="h2",
        markup="##",
        source=HISTORICAL_SUMMARY_END,
    )
    peer_indices = [
        index
        for index, token in enumerate(tokens)
        if token.type == "heading_open" and token.level == 0 and token.tag in {"h1", "h2"}
    ]
    assert peer_indices and peer_indices[0] == title.start
    assert title.start < summary.start < status.start < summary_end.start
    _assert_next_top_level_section_heading(
        tokens,
        start_index=title.start,
        expected_index=summary.start,
    )
    _assert_next_top_level_section_heading(
        tokens,
        start_index=summary.start,
        expected_index=summary_end.start,
    )
    _assert_only_canonical_raw_html(
        tokens,
        through=summary_end.stop,
        allowed_block_sources=(EVIDENCE_STATUS_START, EVIDENCE_STATUS_END),
    )
    _assert_rendered_root_targets(
        tokens,
        through=summary_end.stop,
        h1_texts=(HISTORICAL_TITLE_TEXT,),
        h2_texts=(HISTORICAL_SUMMARY_TEXT, HISTORICAL_SUMMARY_END_TEXT),
        comment_markers=(EVIDENCE_STATUS_START, EVIDENCE_STATUS_END),
    )


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
    _assert_dependency_policy_markdown_structure(agents_md, lessons_md)


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
    pytest.param("schema", "pulseplate.dependency_remediation_admission.v1", id="schema"),
    pytest.param("default_dependency_identities", 2, id="plural-default-D"),
    pytest.param("ecosystems", 2, id="plural-ecosystems"),
    pytest.param("batch_exception", "candidate_declared_batch", id="candidate-batch"),
    pytest.param("policy_effect", "candidate_effective_before_merge", id="early-effect"),
    pytest.param(
        "policy_transition_authority", "candidate_policy_text", id="transition-self-authority"
    ),
    pytest.param(
        "policy_transition_grants_future_authority", True, id="transition-future-authority"
    ),
    pytest.param("candidate_self_authorization", "allowed", id="self-authorization"),
    pytest.param(
        "candidate_authorization_authentication", "allowed", id="candidate-authentication"
    ),
    pytest.param("batch_identity_set", "selected_subset", id="selected-subset"),
    pytest.param("batch_identity_omission_or_addition", "allow", id="set-drift"),
    pytest.param("per_identity_authored_actions", 0, id="missing-action"),
    pytest.param("per_identity_authored_actions", 2, id="plural-actions"),
    pytest.param("per_identity_action_kinds", "aggregate_make_safe", id="goal-as-action"),
    pytest.param("operator_intent_delta_per_identity", "empty_allowed", id="empty-intent"),
    pytest.param("literal_target_versions", "different_classes", id="target-variant-split"),
    pytest.param("material_transition_partition", "unclassified_allowed", id="partial-delta"),
    pytest.param("solver_closure", "unreplayed_claim", id="unreplayed-closure"),
    pytest.param("solver_closure_independent_intent", "allowed", id="closure-intent"),
    pytest.param("manual_unclassified_or_unreplayable_delta", "allow", id="manual-delta"),
    pytest.param("aggregate_goal_is_postcondition_not_intent", False, id="goal-as-intent"),
    pytest.param("surfaces", "representative_sample", id="partial-S"),
    pytest.param("scanner_snapshot", "mutable_latest", id="mutable-snapshot"),
    pytest.param("candidate_advisory_inventory", "unreconciled", id="unreconciled-advisories"),
    pytest.param("applicable_advisory_inventory", "empty_allowed", id="empty-applicable"),
    pytest.param(
        "advisory_applicability_quantifier", "exists_one_advisory", id="existential-applicable"
    ),
    pytest.param("non_applicable_candidates", "ignored", id="head-only-advisory-escape"),
    pytest.param("disposition_only_lane", "may_mutate", id="disposition-mutation"),
    pytest.param(
        "remediation_postcondition_inventory", "base_applicable_only", id="partial-inventory"
    ),
    pytest.param("occurrences", "one_representative_head", id="partial-occurrences"),
    pytest.param("base_only_surfaces", "ignored", id="base-only-surface"),
    pytest.param("postcondition", "any_identity_safe", id="disjunctive-postcondition"),
    pytest.param("partial_success", "allow", id="partial-success"),
    pytest.param("unparseable_unresolved_omitted_or_unclassified", "allow", id="allow-unresolved"),
    pytest.param("same_floor_required", True, id="same-floor"),
    pytest.param("obsolete_suppression_deletion", "any_suppression", id="broad-deletion"),
    pytest.param(
        "suppression_addition_broadening_replacement_or_other_deletion",
        "allowed",
        id="suppression-escape",
    ),
    pytest.param("evidence_owner", "pr_body_or_issue", id="evidence-owner"),
    pytest.param("per_advisory_evidence", "shared_aggregate", id="shared-evidence"),
)
_STRICT_JSON_MUTATIONS = (
    pytest.param(
        '"default_dependency_identities": 1',
        '"default_dependency_identities": true',
        r"default_dependency_identities.*expected int, got bool",
        id="identity-bool",
    ),
    pytest.param(
        '"default_dependency_identities": 1',
        '"default_dependency_identities": 1.0',
        r"default_dependency_identities.*expected int, got float",
        id="identity-float",
    ),
    pytest.param(
        '"per_identity_authored_actions": 1',
        '"per_identity_authored_actions": true',
        r"per_identity_authored_actions.*expected int, got bool",
        id="action-bool",
    ),
    pytest.param(
        '"per_identity_authored_actions": 1',
        '"per_identity_authored_actions": 1.0',
        r"per_identity_authored_actions.*expected int, got float",
        id="action-float",
    ),
    pytest.param(
        '"policy_transition_grants_future_authority": false',
        '"policy_transition_grants_future_authority": 0',
        r"policy_transition_grants_future_authority.*expected bool, got int",
        id="transition-authority-int",
    ),
    pytest.param(
        '"default_dependency_identities": 1,',
        '"default_dependency_identities": 2,\n  "default_dependency_identities": 1,',
        r"duplicate JSON key 'default_dependency_identities'",
        id="duplicate-identity-last-expected",
    ),
    pytest.param(
        '"same_floor_required": false',
        '"same_floor_required": true,\n  "same_floor_required": false',
        r"duplicate JSON key 'same_floor_required'",
        id="duplicate-bool-last-expected",
    ),
    pytest.param(
        '  "scanner_snapshot": "one_immutable_external_run_and_analysis",\n',
        "",
        r"key set mismatch",
        id="missing-key",
    ),
    pytest.param(
        '"per_advisory_evidence": "required"',
        '"unexpected": true,\n  "per_advisory_evidence": "required"',
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
_PLATFORM_LINE_ENDINGS = (
    pytest.param("\n", id="lf"),
    pytest.param("\r", id="cr"),
    pytest.param("\r\n", id="crlf"),
)
_PYTHON_ONLY_LINE_SEPARATORS = (
    pytest.param("\v", id="vertical-tab"),
    pytest.param("\f", id="form-feed"),
    pytest.param("\x1c", id="file-separator"),
    pytest.param("\x1d", id="group-separator"),
    pytest.param("\x1e", id="record-separator"),
    pytest.param("\x85", id="next-line"),
    pytest.param("\u2028", id="line-separator"),
    pytest.param("\u2029", id="paragraph-separator"),
)
_PYTHON_ONLY_SEPARATOR_CARRIERS = (
    pytest.param("marker-adjacent", id="marker-adjacent"),
    pytest.param("fence-padding", id="fence-padding"),
    pytest.param("json-field-boundary", id="json-field-boundary"),
)
_MARKDOWN_CONTAINER_WRAPPERS = (
    pytest.param("````markdown\n", "\n````", id="backtick-fence"),
    pytest.param("~~~~markdown\n", "\n~~~~", id="tilde-fence"),
    pytest.param("<details>\n\n", "\n\n</details>", id="raw-html-ancestor"),
)
_PROTECTED_MARKDOWN_REGIONS = (
    pytest.param("agents", id="agents-security-parent"),
    pytest.param("lessons", id="engineering-lesson-33"),
    pytest.param("historical", id="historical-evidence-status"),
)
_HISTORICAL_STATUS_MUTATIONS = (
    pytest.param(
        '"evidence_status": "historical"',
        '"evidence_status": "current"',
        id="historical-promoted-to-current",
    ),
    pytest.param(
        '"current_scoping_authority": false',
        '"current_scoping_authority": true',
        id="historical-claims-current-authority",
    ),
    pytest.param(
        '"future_multi_dependency_batching_authority": false',
        '"future_multi_dependency_batching_authority": true',
        id="historical-claims-future-batching-authority",
    ),
    pytest.param(
        '"current_authority_ref": "AGENTS.md::dependency-remediation-admission:v2"',
        '"current_authority_ref": "this-document"',
        id="historical-self-authority",
    ),
)


def _current_dependency_policy_docs() -> tuple[str, str]:
    return _read("AGENTS.md"), _read("docs/ENGINEERING_LESSONS.md")


def _insert_before_unique(document: str, boundary: str, statement: str) -> str:
    assert document.count(boundary) == 1
    return document.replace(boundary, f"{statement}\n\n{boundary}", 1)


def _replace_unique(document: str, old: str, new: str) -> str:
    assert old != new
    assert document.count(old) == 1
    mutated = document.replace(old, new, 1)
    assert mutated != document
    return mutated


def _mutate_authority_value(document: str, key: str, value: object) -> str:
    block = _exact_bounded_section(
        document,
        start_line=ADMISSION_AUTHORITY_START,
        end_line=ADMISSION_AUTHORITY_END,
    )
    payload = block.removeprefix("```json\n").removesuffix("\n```")
    parsed = json.loads(payload, object_pairs_hook=_reject_duplicate_json_keys)
    assert isinstance(parsed, dict)
    assert key in parsed
    assert parsed[key] != value
    parsed[key] = value
    replacement = f"```json\n{json.dumps(parsed, indent=2, ensure_ascii=False)}\n```"
    return _replace_unique(document, block, replacement)


def _wrap_unique_region(
    document: str,
    *,
    start_line: str,
    end_line: str,
    opener: str,
    closer: str,
) -> str:
    mutated = _replace_unique(document, start_line, f"{opener}{start_line}")
    return _replace_unique(mutated, end_line, f"{end_line}{closer}")


def test_dependency_security_policy_scopes_remediation_by_invariant_class() -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    remediation, _lesson, _parent = _extract_dependency_security_sections(agents_md, lessons_md)
    assert (
        _parse_dependency_remediation_authority(agents_md, remediation)
        == _EXPECTED_ADMISSION_AUTHORITY
    )
    _validate_dependency_security_policy(agents_md, lessons_md)


def test_dependency_security_policy_models_exact_conjunctive_scanner_batch() -> None:
    """Positive v2 model: exact snapshot set plus all-member success is admitted."""
    scanner_identities = frozenset({"npm:image-size", "npm:nanoid", "npm:react-router"})
    authorized_identities = frozenset({"npm:image-size", "npm:nanoid", "npm:react-router"})
    per_identity_safe = {
        "npm:image-size": True,
        "npm:nanoid": True,
        "npm:react-router": True,
    }
    assert authorized_identities == scanner_identities
    assert all(per_identity_safe[identity] for identity in authorized_identities)

    agents_md, lessons_md = _current_dependency_policy_docs()
    remediation, _lesson, _parent = _extract_dependency_security_sections(agents_md, lessons_md)
    authority = _parse_dependency_remediation_authority(agents_md, remediation)
    assert (
        authority["batch_identity_set"] == "exact_finite_complete_snapshot_derived_unresolved_set"
    )
    assert authority["candidate_self_authorization"] == "forbidden"
    assert authority["postcondition"].startswith("conjunction_all_per_identity")


def test_dependency_security_policy_rejects_base_only_head_safety_escape() -> None:
    """A base-inapplicable known advisory must still reject an affected head."""
    candidates = {
        "ADV-base": ((1, 0), (2, 0)),
        "ADV-head-only": ((2, 0), (3, 0)),
    }
    base = (1, 5)
    head = (2, 5)

    def affected(
        version: tuple[int, int],
        advisory: tuple[tuple[int, int], tuple[int, int]],
    ) -> bool:
        lower, upper = advisory
        return lower <= version < upper

    applicable_at_base = tuple(
        advisory_id
        for advisory_id, affected_range in candidates.items()
        if affected(base, affected_range)
    )
    assert applicable_at_base == ("ADV-base",)
    assert all(not affected(head, candidates[item]) for item in applicable_at_base)
    assert not all(not affected(head, affected_range) for affected_range in candidates.values())

    agents_md, lessons_md = _current_dependency_policy_docs()
    remediation, _lesson, _parent = _extract_dependency_security_sections(agents_md, lessons_md)
    authority = _parse_dependency_remediation_authority(agents_md, remediation)
    assert (
        authority["remediation_postcondition_inventory"]
        == "every_candidate_advisory_in_each_per_identity_F_cutoff"
    )
    assert "universal_head_safety" in str(authority["non_applicable_candidates"])


def test_dependency_security_historical_batch_is_not_current_scope_authority() -> None:
    _validate_historical_evidence_status(_read(HISTORICAL_EVIDENCE_PATH))


@pytest.mark.parametrize(("old", "new"), _HISTORICAL_STATUS_MUTATIONS)
def test_dependency_security_historical_status_rejects_authority_mutations(
    old: str, new: str
) -> None:
    historical = _read(HISTORICAL_EVIDENCE_PATH)
    mutated = _replace_unique(historical, old, new)
    with pytest.raises(AssertionError):
        _validate_historical_evidence_status(mutated)


def test_dependency_security_historical_status_rejects_duplicate_or_extra_authority() -> None:
    historical = _read(HISTORICAL_EVIDENCE_PATH)
    duplicate_key = _replace_unique(
        historical,
        '"evidence_status": "historical",',
        '"evidence_status": "current",\n  "evidence_status": "historical",',
    )
    with pytest.raises(AssertionError, match="invalid JSON"):
        _validate_historical_evidence_status(duplicate_key)

    admission_marker = _insert_before_unique(
        historical,
        EVIDENCE_STATUS_START,
        ADMISSION_AUTHORITY_START,
    )
    with pytest.raises(AssertionError):
        _validate_historical_evidence_status(admission_marker)


def test_dependency_security_historical_status_rejects_contradictory_authority_prose() -> None:
    historical = _read(HISTORICAL_EVIDENCE_PATH)
    mutated = _replace_unique(
        historical,
        "  its version, audit, and alert statements are not current claims. It is not\n"
        "  current scoping authority and does not authorize future multi-dependency\n"
        "  batching.",
        "  its version, audit, and alert statements are current claims. It is the\n"
        "  current scoping authority and authorizes future multi-dependency\n"
        "  batching.",
    )
    with pytest.raises(AssertionError, match="authority summary changed"):
        _validate_historical_evidence_status(mutated)


def test_dependency_security_historical_status_rejects_markdown_authority_prefix() -> None:
    historical = _read(HISTORICAL_EVIDENCE_PATH)
    mutated = _insert_before_unique(
        historical,
        HISTORICAL_SUMMARY_START,
        "## Current dependency remediation authority\n\n"
        "This document authorizes future multi-dependency batching.",
    )
    with pytest.raises(AssertionError, match="followed directly"):
        _validate_historical_evidence_status(mutated)


def test_dependency_security_historical_status_ignores_non_ancestor_suffix_html() -> None:
    historical = _read(HISTORICAL_EVIDENCE_PATH)
    mutated = f"{historical}\n<div><input disabled>unrelated suffix"
    _validate_historical_evidence_status(mutated)


@pytest.mark.parametrize("region", _PROTECTED_MARKDOWN_REGIONS)
def test_dependency_security_policy_rejects_noncanonical_raw_html_prefix(
    region: str,
) -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    carrier = "<b><div></b>"
    if region == "agents":
        mutated_agents = _insert_before_unique(agents_md, SECURITY_PARENT_START, carrier)
        with pytest.raises(AssertionError, match="Non-canonical raw HTML"):
            _validate_dependency_security_policy(mutated_agents, lessons_md)
    elif region == "lessons":
        mutated_lessons = _insert_before_unique(lessons_md, LESSON_33_HEADING, carrier)
        with pytest.raises(AssertionError, match="Non-canonical raw HTML"):
            _validate_dependency_security_policy(agents_md, mutated_lessons)
    else:
        historical = _insert_before_unique(
            _read(HISTORICAL_EVIDENCE_PATH), HISTORICAL_SUMMARY_START, carrier
        )
        with pytest.raises(AssertionError, match="followed directly"):
            _validate_historical_evidence_status(historical)


@pytest.mark.parametrize("line_ending", _PLATFORM_LINE_ENDINGS)
def test_dependency_security_policy_accepts_platform_line_endings(line_ending: str) -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    _validate_dependency_security_policy(
        agents_md.replace("\n", line_ending),
        lessons_md.replace("\n", line_ending),
    )


def test_dependency_security_policy_preserves_platform_compound_boundaries() -> None:
    assert _platform_lines("a\r\nb\rc\nd") == ["a", "b", "c", "d"]
    assert _platform_lines("a\n\rb\r\r\nc\r\n\nd") == [
        "a",
        "",
        "b",
        "",
        "c",
        "",
        "d",
    ]


@pytest.mark.parametrize("region", _PROTECTED_MARKDOWN_REGIONS)
@pytest.mark.parametrize(("opener", "closer"), _MARKDOWN_CONTAINER_WRAPPERS)
def test_dependency_security_policy_requires_top_level_markdown_structure(
    region: str,
    opener: str,
    closer: str,
) -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    if region == "agents":
        mutated_agents = _wrap_unique_region(
            agents_md,
            start_line=SECURITY_PARENT_START,
            end_line=SECURITY_PARENT_END,
            opener=opener,
            closer=closer,
        )
        mutated_lessons = lessons_md
    elif region == "lessons":
        mutated_agents = agents_md
        mutated_lessons = _wrap_unique_region(
            lessons_md,
            start_line=LESSON_33_HEADING,
            end_line=LESSON_33_END,
            opener=opener,
            closer=closer,
        )
    else:
        historical = _wrap_unique_region(
            _read(HISTORICAL_EVIDENCE_PATH),
            start_line=EVIDENCE_STATUS_START,
            end_line=EVIDENCE_STATUS_END,
            opener=opener,
            closer=closer,
        )
        with pytest.raises(AssertionError):
            _validate_historical_evidence_status(historical)
        return

    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(mutated_agents, mutated_lessons)


@pytest.mark.parametrize("separator", _PYTHON_ONLY_LINE_SEPARATORS)
def test_dependency_security_policy_rejects_python_only_separator_in_prose(
    separator: str,
) -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    canonical = (
        "- **Policy-transition boundary:** this v2 policy has prospective repository\n"
        "  effect only after merge. A direct operator instruction issued outside the\n"
        "  candidate diff may separately authorize the exact transition that changes\n"
        "  this policy and its exact bounded dependency material. That instruction does\n"
        "  not make candidate text effective early and grants no general or future batch\n"
        "  authority. Candidate code, docs, tests, labels, scanners, agents, or PR text\n"
        "  cannot create, infer, widen, authenticate, or substitute that instruction.\n"
        "  Without direct external instruction, the one-identity default remains."
    )
    mutated = canonical.replace("\n", separator)
    mutated_agents = _replace_unique(agents_md, canonical, mutated)

    with pytest.raises(AssertionError, match="AGENTS Security parent region changed"):
        _validate_dependency_security_policy(mutated_agents, lessons_md)


@pytest.mark.parametrize("separator", _PYTHON_ONLY_LINE_SEPARATORS)
@pytest.mark.parametrize("carrier", _PYTHON_ONLY_SEPARATOR_CARRIERS)
def test_dependency_security_policy_rejects_python_only_separator_in_authority(
    separator: str,
    carrier: str,
) -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    if carrier == "marker-adjacent":
        mutated = _replace_unique(
            agents_md,
            f"{ADMISSION_AUTHORITY_START}\n",
            f"{ADMISSION_AUTHORITY_START}{separator}",
        )
    elif carrier == "fence-padding":
        mutated = _replace_unique(
            agents_md,
            f"{ADMISSION_AUTHORITY_START}\n```json",
            f"{ADMISSION_AUTHORITY_START}\n{separator}\n```json",
        )
    else:
        mutated = _replace_unique(
            agents_md,
            '"default_dependency_identities": 1,\n  "ecosystems": 1',
            f'"default_dependency_identities": 1,{separator}  "ecosystems": 1',
        )

    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(mutated, lessons_md)


def test_dependency_security_policy_rejects_markdown_significant_indentation() -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    canonical_rule = (
        "- **Suppression deletion boundary:** a batch may delete only the exact obsolete\n"
        "  suppression for an identity remediated by that same batch. Adding, broadening,\n"
        "  replacing, or deleting any other suppression remains forbidden and cannot be\n"
        "  solver closure."
    )
    indented_rule = (
        "\n      - **Suppression deletion boundary:** a batch may delete only the exact obsolete\n"
        "        suppression for an identity remediated by that same batch. Adding, broadening,\n"
        "        replacing, or deleting any other suppression remains forbidden and cannot be\n"
        "        solver closure."
    )
    mutated_agents = _replace_unique(agents_md, canonical_rule, indented_rule)

    with pytest.raises(AssertionError, match="AGENTS Security parent region changed"):
        _validate_dependency_security_policy(mutated_agents, lessons_md)


def test_dependency_security_policy_rejects_lesson_region_change() -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    mutated = _insert_before_unique(
        lessons_md,
        LESSON_33_END,
        "## 34) Future dependency policy\n\nSentence variants redefine the admission relation.",
    )
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(agents_md, mutated)


@pytest.mark.parametrize(("key", "value"), _AUTHORITY_FIELD_MUTATIONS)
def test_dependency_security_policy_rejects_structured_authority_mutations(
    key: str, value: object
) -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    mutated_agents = _mutate_authority_value(agents_md, key, value)
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(mutated_agents, lessons_md)


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
    mutated_agents = _replace_unique(agents_md, old, new)
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(mutated_agents, lessons_md)


def test_dependency_security_policy_rejects_invalid_authority_json() -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    invalid = _replace_unique(
        agents_md,
        '"default_dependency_identities": 1',
        '"default_dependency_identities": ,',
    )
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(invalid, lessons_md)


# Prose outside the closed region is not admission logic. The exact JSON relation
# is the sole machine-readable authority; parent-region digests bind its mirror.
def test_dependency_security_policy_ignores_non_authority_prose_outside_region() -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    _validate_dependency_security_policy(
        f"{agents_md}\nUnrelated prose outside the closed policy region.\n",
        lessons_md,
    )


@pytest.mark.parametrize(("old", "new"), _SUPPRESSION_MUTATIONS)
def test_dependency_security_policy_preserves_suppression_scope(old: str, new: str) -> None:
    agents_md, lessons_md = _current_dependency_policy_docs()
    mutated_agents = _replace_unique(agents_md, old, new)
    with pytest.raises(AssertionError):
        _validate_dependency_security_policy(mutated_agents, lessons_md)


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
