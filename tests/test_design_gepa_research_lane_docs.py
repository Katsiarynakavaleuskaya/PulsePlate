from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]

RESEARCH_DOC = REPO_ROOT / "docs/research/DESIGN_GEPA_PROMPT_RUBRIC_EVOLUTION_LANE.md"
PACKET = REPO_ROOT / "docs/orchestration/DESIGN_INTELLIGENCE_PR8_GEPA_PACKET_2026-05-07.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _combined_docs() -> str:
    return "\n".join([_read(RESEARCH_DOC), _read(PACKET)])


def _bash_blocks(text: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)```", text, flags=re.DOTALL)


def _assert_no_forbidden_patterns(text: str, patterns: list[str]) -> None:
    for pattern in patterns:
        assert re.search(pattern, text, flags=re.IGNORECASE) is None, pattern


def test_gepa_research_lane_required_sections() -> None:
    text = _read(RESEARCH_DOC)

    required_sections = [
        "## Summary",
        "## Why PR-8 Exists Now After PR-7",
        "## Scope",
        "## Non-Goals",
        "## Source-Of-Truth Hierarchy",
        "## GEPA-Compatible Lane Definition",
        "## Allowed Mutation Units",
        "## Forbidden Mutation Units",
        "## Curated Eval Fixture Policy",
        "## Prompt/Rubric Candidate Schema",
        "## Eval Trace Schema",
        "## Safety Gates",
        "## Promotion Rules",
        "## Rollback Model",
    ]

    for section in required_sections:
        assert section in text

    positions = [text.index(section) for section in required_sections]
    assert all(positions[index] < positions[index + 1] for index in range(len(positions) - 1))


def test_gepa_research_lane_preserves_source_truth_boundaries() -> None:
    combined = _combined_docs()

    required_claims = [
        "Repo code/docs/tests",
        "`/tokens` as token authoring truth",
        "Generated mirrors as derived artifacts",
        "Reference and evidence layers remain non-canonical:",
        "Prompt outputs, evolved rubrics, eval summaries, and GEPA-inspired traces are never runtime or design truth by themselves.",
        "Any runtime implementation work requires a separate non-PR-8 packet",
        "GEPA remains research/eval/process-only.",
    ]

    for claim in required_claims:
        assert claim in combined

    _assert_no_forbidden_patterns(
        combined,
        [
            r"figma\s+is\s+(the\s+)?source\s+of\s+truth",
            r"canva\s+is\s+(the\s+)?source\s+of\s+truth",
            r"prompt\s+outputs?\s+(are|is)\s+(?!not\b|never\b).*source\s+of\s+truth",
            r"prompt\s+outputs?\s+(become|becomes)\s+.*source\s+of\s+truth",
            r"generated\s+mirrors?\s+(may|can|should)\s+be\s+edited\s+(by\s+hand|manually)",
            r"automatic\s+adoption\s+is\s+allowed",
            r"self[-\s]?promotion\s+is\s+allowed",
            r"live\s+product\s+flow\s+mutation\s+is\s+allowed",
        ],
    )


def test_gepa_research_lane_blocks_runtime_and_design_tool_writes() -> None:
    combined = _combined_docs()

    required_boundaries = [
        "No runtime web, iOS, backend, OpenAPI",
        "No `/tokens` changes.",
        "No manual generated mirror edits.",
        "No Figma writes.",
        "No Canva writes.",
        "No Storybook config changes.",
        "No screenshots, videos, runtime/product traces, binary assets, or external infrastructure.",
    ]

    for boundary in required_boundaries:
        assert boundary in combined

    _assert_no_forbidden_patterns(
        combined,
        [
            r"figma\s+writes?\s+(are|is)\s+allowed",
            r"canva\s+writes?\s+(are|is)\s+allowed",
            r"write\s+to\s+figma",
            r"write\s+to\s+canva",
            r"update\s+figma",
            r"update\s+canva",
            r"runtime\s+mutation\s+is\s+allowed",
            r"online\s+optimization\s+against\s+live\s+users\s+is\s+allowed",
            r"(web|ios|backend|openapi|tokens?)\s+mutation\s+is\s+allowed",
        ],
    )


def test_gepa_research_lane_uses_repo_venv_for_command_examples() -> None:
    combined = _combined_docs()
    bash_blocks = "\n".join(_bash_blocks(combined))

    assert ".venv/bin/python" in combined
    assert "DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python" in combined
    assert "python3" not in combined
    assert "python3 " not in bash_blocks
    assert "\npython " not in bash_blocks
    assert " python " not in bash_blocks


def test_gepa_research_lane_requires_premortem_fix_before_mapping() -> None:
    combined = _combined_docs()

    required_phrases = [
        "Premortem must inspect the actual docs/test diff and fix real defects before mapping.",
        "Does mapping attempt to substitute for fixing docs/test defects?",
        "Premortem and bug-hunter findings are fixed before mapping.",
        "docs/review/PR_<N>_FIXED_MAPPING.md",
        "root `AGENTS.md` machine-heavy exception",
        "current-head CI parity is complete",
    ]

    for phrase in required_phrases:
        assert phrase in combined
