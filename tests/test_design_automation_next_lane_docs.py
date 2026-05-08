"""Guards for the post-PR-8 design automation lane decision docs."""

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]

DECISION = REPO_ROOT / "docs/design/NEXT_DESIGN_AUTOMATION_MODULE_DECISION.md"
PACKET = REPO_ROOT / "docs/orchestration/DESIGN_AUTOMATION_NEXT_LANE_PACKET_2026-05-08.md"
LEDGER = REPO_ROOT / "docs/roadmap/BACKLOG_LEDGER.md"


def _read(path: Path) -> str:
    """Read a UTF-8 markdown fixture from the repository."""
    return path.read_text(encoding="utf-8")


def _combined() -> str:
    """Return the decision, packet, and ledger text as one searchable corpus."""
    return "\n".join([_read(DECISION), _read(PACKET), _read(LEDGER)])


def test_next_design_automation_decision_required_sections() -> None:
    """Require the decision doc to keep the canonical section order."""
    text = _read(DECISION)

    sections = [
        "## Summary",
        "## Current Repo Truth",
        "## Candidate Modules",
        "## Comparison Matrix",
        "## Selected Next Lane",
        "## Why This Lane Is Next",
        "## Deferred Lanes",
        "## Future Implementation Boundary",
        "## Risks",
        "## Rollback / If Selection Changes Later",
    ]

    for section in sections:
        assert section in text

    positions = [text.index(section) for section in sections]
    assert all(positions[index] < positions[index + 1] for index in range(len(positions) - 1))


def test_next_design_automation_lane_selection_is_explicit() -> None:
    """Require the selected lane and deferred lanes to be explicit."""
    combined = _combined()

    required = [
        "Icon Asset Validator / App Store asset guard lane",
        "This PR does not implement the selected lane.",
        "does not create an undocumented PR-9 implementation train",
        "Launch Copy Compliance Linter",
        "Marketing Asset Pack Compiler",
        "Button / Component Drift Inspector expansion",
        "Adjacent design-agent research lane",
        "separate future packet and PR",
        "SoT drift risk",
    ]

    for phrase in required:
        assert phrase in combined


def test_next_design_automation_preserves_source_truth_boundaries() -> None:
    """Prevent the decision packet from creating a second source of truth."""
    combined = _combined()

    required = [
        "Repo code/docs/tests",
        "`/tokens` as token authoring truth",
        "Generated mirrors as derived artifacts",
        "remain evidence/reference/process layers only",
        "This packet must not create a second source of truth.",
    ]

    for phrase in required:
        assert phrase in combined

    forbidden_patterns = [
        r"Figma\s+is\s+(the\s+)?source\s+of\s+truth",
        r"Canva\s+is\s+(the\s+)?source\s+of\s+truth",
        r"Storybook\s+is\s+(the\s+)?source\s+of\s+truth",
        r"prompt\s+outputs?\s+(are|is)\s+(?!never\b|not\b).*source\s+of\s+truth",
        r"generated\s+mirrors?\s+(may|can|should)\s+be\s+edited\s+(by\s+hand|manually)",
    ]

    for pattern in forbidden_patterns:
        assert re.search(pattern, combined, flags=re.IGNORECASE) is None, pattern


def test_next_design_automation_blocks_runtime_and_external_tool_writes() -> None:
    """Keep this decision PR out of runtime code and external design writes."""
    combined = _combined()

    required_boundaries = [
        "does not mutate runtime web, runtime iOS, backend, OpenAPI, `/tokens`, generated mirrors, Figma, Canva, Storybook config",
        "Runtime web or iOS UI.",
        "Backend, OpenAPI, billing, auth, StoreKit, HealthKit, or product logic.",
        "No Figma/Canva writes",
        "no external write authority",
        "no live design-tool mutation",
    ]

    for boundary in required_boundaries:
        assert boundary in combined

    forbidden_patterns = [
        r"Figma\s+writes?\s+(are|is)\s+allowed",
        r"Canva\s+writes?\s+(are|is)\s+allowed",
        r"write\s+to\s+Figma",
        r"write\s+to\s+Canva",
        r"runtime\s+mutation\s+is\s+allowed",
        r"implement\s+the\s+Icon\s+Asset\s+Validator\s+in\s+this\s+PR",
    ]

    for pattern in forbidden_patterns:
        assert re.search(pattern, combined, flags=re.IGNORECASE) is None, pattern


def test_next_design_automation_uses_repo_venv_and_no_tracked_symlink_assumption() -> None:
    """Require repo-local Python commands and forbid symlink assumptions."""
    packet = _read(PACKET)

    assert ".venv/bin/python" in packet
    assert "DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python" in packet
    assert "Do not claim green main" in packet
    assert "tracked symlink" in packet

    command_block = "\n".join(
        re.findall(r"```(?:bash|sh|shell|zsh)\n(.*?)```", packet, flags=re.DOTALL)
    )
    assert re.search(r"(?m)^\s*python3(?:\s|$)", command_block) is None
    assert re.search(r"(?m)^\s*python(?:\s|$)", command_block) is None


def test_next_design_automation_requires_premortem_fix_before_mapping() -> None:
    """Require premortem and bug-hunter findings to be fixed before mapping."""
    packet = _read(PACKET)

    required = [
        "Premortem must inspect the actual docs/test diff.",
        "Real findings must be fixed in docs/tests before mapping.",
        "fix the document or test first",
        "docs/review/PR_<N>_FIXED_MAPPING.md",
        "Bug-hunter must inspect the actual diff.",
        "Codex Security review is diff-scoped.",
    ]

    for phrase in required:
        assert phrase in packet
