"""Guards for the post-PR-8 design automation lane decision docs."""

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]

DECISION = REPO_ROOT / "docs/design/NEXT_DESIGN_AUTOMATION_MODULE_DECISION.md"
PACKET = REPO_ROOT / "docs/orchestration/DESIGN_AUTOMATION_NEXT_LANE_PACKET_2026-05-08.md"
CANONICAL_PROMPT = (
    REPO_ROOT / "docs/orchestration/PULSEPLATE_CANONICAL_PR_EXECUTION_PROMPT_2026_05_08.md"
)
WORKFLOW = REPO_ROOT / "docs/orchestration/DESIGN_AGENT_WORKFLOW.md"
TEMPLATE = REPO_ROOT / "docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md"
LEDGER = REPO_ROOT / "docs/roadmap/BACKLOG_LEDGER.md"


def _read(path: Path) -> str:
    """Read a UTF-8 markdown fixture from the repository."""
    return path.read_text(encoding="utf-8")


def _combined() -> str:
    """Return the decision, packet, and ledger text as one searchable corpus."""
    return "\n".join([_read(DECISION), _read(PACKET), _read(LEDGER)])


def _prompt_corpus() -> str:
    """Return the prompt-governance corpus that must not drift."""
    return "\n".join([_read(CANONICAL_PROMPT), _read(PACKET), _read(WORKFLOW), _read(TEMPLATE)])


def _command_blocks(text: str) -> str:
    """Extract shell-like command blocks from markdown."""
    return "\n".join(re.findall(r"```(?:bash|sh|shell|zsh)\n(.*?)```", text, flags=re.DOTALL))


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
        "It does not implement the selected lane",
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


def test_canonical_pr_execution_prompt_required_sections() -> None:
    """Keep the canonical PR execution prompt contract complete."""
    text = _read(CANONICAL_PROMPT)

    required = [
        "# PulsePlate Canonical PR Execution Prompt v2026-05-08",
        "## Prompt Canon",
        "## Required Startup Flow",
        "## Required Execution Chain",
        "## Required Skills And Plugins",
        "## Premortem Requirement",
        "## Post-Open And Bot-Review Chain",
        "## Bounded Validation Prompt",
        "## Review Governance",
        "## Operator Boundary",
        "python3.13 -m venv .venv --copies",
        "make validate-changed",
        "agent-coordinator",
        "cursor-specialist-agent",
        "architecture-specialist",
        "creative-designer",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
        "Codex Security plugin",
    ]

    for phrase in required:
        assert phrase in text


def test_canonical_pr_prompt_rejects_old_prompt_commands() -> None:
    """Reject old generated-prompt command patterns from the prompt corpus."""
    corpus = _prompt_corpus()
    commands = _command_blocks(corpus)

    forbidden_commands = [
        r"(?m)^\s*git\s+checkout\s+main\b",
        r"(?m)^\s*git\s+merge\s+--ff-only\s+origin/main\b",
        r"(?m)^\s*make\s+verify\b",
        r"(?m)^\s*DEV_PYTHON=.*\bmake\s+(?!validate-changed\b)[A-Za-z0-9_-]+\b",
    ]

    for pattern in forbidden_commands:
        assert re.search(pattern, commands) is None, pattern

    assert "draft PR" not in corpus
    assert "open as draft" not in corpus.lower()


def test_canonical_pr_prompt_allows_only_validate_changed_make_target() -> None:
    """Generated PR prompt command blocks may name only the approved default make target."""
    corpus = _prompt_corpus()
    commands = _command_blocks(corpus)
    targets = set(re.findall(r"\bmake\s+([A-Za-z0-9_-]+)", commands))

    assert targets == {"validate-changed"}


def test_canonical_pr_prompt_requires_premortem_and_review_chains() -> None:
    """Require premortem execution on the real diff and both review chains."""
    corpus = _prompt_corpus()

    required = [
        "Premortem is mandatory before PR opening and again after the first bot-review cycle.",
        "The premortem must inspect the actual diff",
        "If `task_bootstrap.py` or `agent-coordinator` expands the role order, the expanded order becomes mandatory",
        "Post-open review must include `qa-engineer-agent`, `bug-hunter`, `security-auditor`, and Codex Security.",
        "After the first bot review, repeat `agent-coordinator`, `qa-engineer-agent`, `bug-hunter`, `security-auditor`, and premortem on the updated diff.",
        "Post-merge local main synchronization is operator-owned",
    ]

    for phrase in required:
        assert phrase in corpus
