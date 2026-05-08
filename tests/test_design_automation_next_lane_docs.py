"""Guards for the post-PR-8 design automation lane decision docs."""

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]

DECISION = REPO_ROOT / "docs/design/NEXT_DESIGN_AUTOMATION_MODULE_DECISION.md"
PACKET = REPO_ROOT / "docs/orchestration/DESIGN_AUTOMATION_NEXT_LANE_PACKET_2026-05-08.md"
PROTOCOL = REPO_ROOT / "docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md"
PR9_PACKET = (
    REPO_ROOT
    / "docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR9_DESIGN_SYSTEM_AUTOMATION_PACKET_2026-05-08.md"
)
PR9_SPEC = REPO_ROOT / "docs/design/DESIGN_SYSTEM_AUTOMATION_SPEC.md"
PR9_REGISTRY = REPO_ROOT / "docs/orchestration/contracts/DESIGN_COMPONENT_CONTRACT_REGISTRY.md"
WORKFLOW = REPO_ROOT / "docs/orchestration/DESIGN_AGENT_WORKFLOW.md"
TEMPLATE = REPO_ROOT / "docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md"
LEDGER = REPO_ROOT / "docs/roadmap/BACKLOG_LEDGER.md"


def _read(path: Path) -> str:
    """Read a UTF-8 markdown fixture from the repository."""
    return path.read_text(encoding="utf-8")


def _combined() -> str:
    """Return the decision, packet, and ledger text as one searchable corpus."""
    return "\n".join([_read(DECISION), _read(PACKET), _read(LEDGER)])


def _future_prompt_corpus() -> str:
    """Return docs that govern future design-epic PR prompts."""
    return "\n".join([_read(PROTOCOL), _read(TEMPLATE)])


def _active_prompt_packet_corpus() -> str:
    """Return future prompt docs plus active lane packets that agents may copy."""
    return "\n".join([_read(PROTOCOL), _read(TEMPLATE), _read(PACKET), _read(PR9_PACKET)])


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


def test_design_epic_pr_prompt_protocol_required_sections() -> None:
    """Require the design-epic prompt protocol to stay complete."""
    text = _read(PROTOCOL)

    required = [
        "# Design Epic PR Prompt Protocol v2026-05-08",
        "## Prompt Contract",
        "## Required Startup Flow",
        "## Required Execution Chain",
        "## Premortem Requirement",
        "## Post-Open And Bot-Review Chain",
        "## Bounded Validation Prompt",
        "## Review Governance",
        "## Design-Epic Boundary",
        "python3.13 -m venv .venv --copies",
        "make venv-sync",
        "make validate-changed",
        "agent-coordinator",
        "cursor-specialist-agent",
        "architecture-specialist",
        "security-auditor",
        "creative-designer",
        "qa-engineer-agent",
        "bug-hunter",
        "Codex Security plugin",
    ]

    for phrase in required:
        assert phrase in text


def test_design_epic_pr_prompt_protocol_is_referenced_by_workflow_and_template() -> None:
    """Require workflow and template to point future design-epic prompts at the protocol."""
    protocol_path = "docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md"

    assert protocol_path in _read(WORKFLOW)
    assert protocol_path in _read(TEMPLATE)


def test_design_workflow_general_gates_do_not_replace_prompt_protocol() -> None:
    """Keep generic design gates separate from generated prompt commands."""
    workflow = _read(WORKFLOW)

    assert "general merge-readiness evidence for design-impacting PRs" in workflow
    assert "future design-epic PR prompts use the narrower bounded prompt bundle" in workflow
    assert "DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make design-guard" in workflow
    assert "DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make tokens-check" in workflow


def test_design_epic_pr_prompt_protocol_rejects_stale_prompt_commands() -> None:
    """Reject stale generated-prompt command patterns from future prompt docs."""
    corpus = _active_prompt_packet_corpus()
    commands = _command_blocks(corpus)

    forbidden_commands = [
        r"(?m)^\s*git\s+checkout\s+main\b",
        r"(?m)^\s*git\s+merge\s+--ff-only\s+origin/main\b",
        r"(?m)^\s*make\s+verify\b",
        r"(?m)^\s*DEV_PYTHON=.*\bmake\s+(?!(?:venv-sync|validate-changed)\b)[A-Za-z0-9_-]+\b",
    ]

    for pattern in forbidden_commands:
        assert re.search(pattern, commands) is None, pattern

    assert "draft PR" not in corpus
    assert "open as draft" not in corpus.lower()


def test_design_epic_pr_prompt_protocol_allows_only_default_make_target() -> None:
    """Generated future prompt command blocks may name only setup plus validate-changed."""
    commands = _command_blocks(_active_prompt_packet_corpus())
    targets = set(re.findall(r"\bmake\s+([A-Za-z0-9_-]+)", commands))

    assert targets == {"venv-sync", "validate-changed"}


def test_design_epic_pr_prompt_protocol_requires_execute_mode_preflight() -> None:
    """Require execute-mode preflight before final pre-open validation."""
    text = _read(PROTOCOL)

    assert (
        "check_preflight.py --mode execute --primary <primary-agent> --reviewer <reviewer-agent> --path <path>"
        in text
    )
    assert (
        "Include `--secondary <agent>` when the coordinator packet declares secondary agents."
        in text
    )
    assert "Environment setup target `make venv-sync` is allowed in startup only" in text


def test_design_epic_pr_prompt_protocol_requires_review_chains() -> None:
    """Require actual-diff premortem and both post-open review chains."""
    corpus = _future_prompt_corpus()

    required = [
        "Premortem is mandatory before PR opening and again after the first bot-review cycle.",
        "The premortem must inspect the actual diff",
        "If `task_bootstrap.py` or `agent-coordinator` expands the role order, the expanded order becomes mandatory",
        "post-open review must include `qa-engineer-agent`, `bug-hunter`, `security-auditor`, and Codex Security.",
        "After the first bot review, repeat `agent-coordinator`, `qa-engineer-agent`, `bug-hunter`, `security-auditor`, and premortem on the updated diff.",
        "mapping only after the underlying fix or formal decision exists",
    ]

    for phrase in required:
        assert phrase in corpus

    assert "separate repo-reviewed contract promotes a narrower authority" in corpus
    assert "coordinator packet explicitly scopes stronger authority" not in corpus


def test_design_epic_pr_prompt_protocol_keeps_next_lane_truth_historical() -> None:
    """Keep the merged post-PR-8 next-lane decision as the design-epic vector."""
    combined = _combined()
    protocol = _read(PROTOCOL)

    assert "docs/design-automation-next-lane-decision-v1" in combined
    assert "Icon Asset Validator / App Store asset guard lane" in combined
    assert "Icon Asset Validator / App Store asset guard lane" in protocol
    assert "does not replace `docs/design/NEXT_DESIGN_AUTOMATION_MODULE_DECISION.md`" in protocol


def test_pr9_design_system_automation_docs_exist_and_are_docs_only() -> None:
    """Require PR-9 to remain an implementation-opening docs/governance lane."""
    packet = _read(PR9_PACKET)
    spec = _read(PR9_SPEC)
    registry = _read(PR9_REGISTRY)
    corpus = "\n".join([packet, spec, registry, _read(WORKFLOW), _read(TEMPLATE), _read(LEDGER)])

    required = [
        "PR-9 opens a docs-only design-system automation lane for web+iOS runtime parity.",
        "machine-readable design infrastructure",
        "PR-9 does not make Figma, Canva, Penpot, Storybook, or Code Connect a source of truth.",
        "PR-9 does not implement runtime.",
        "PR-9 Design-System Automation -> docs-only web+iOS runtime parity lane",
        "PR-9 design-system automation docs lane tracking",
    ]

    for phrase in required:
        assert phrase in corpus

    forbidden = [
        r"PR-9\s+implements\s+web\s+runtime",
        r"PR-9\s+implements\s+iOS\s+runtime",
        r"Code\s+Connect\s+activation\s+is\s+complete",
        r"Figma\s+writes?\s+(are|is)\s+allowed",
        r"Canva\s+writes?\s+(are|is)\s+allowed",
        r"Penpot\s+writes?\s+(are|is)\s+allowed",
    ]

    for pattern in forbidden:
        assert re.search(pattern, corpus, flags=re.IGNORECASE) is None, pattern


def test_pr9_design_system_automation_sequence_is_locked() -> None:
    """Require the PR-9 packet/spec to lock the implementation order."""
    corpus = "\n".join([_read(PR9_PACKET), _read(PR9_SPEC), _read(LEDGER), _read(WORKFLOW)])

    sequence = [
        "Component contract registry",
        "Bridge coverage inventory",
        "Visual regression lane",
        "Accessibility regression lane",
        "Token/runtime parity boundary",
        "Later web+iOS implementation slices",
    ]

    for phrase in sequence:
        assert phrase in corpus

    ordered = _read(PR9_PACKET)
    positions = [
        ordered.index(f"{index}. {phrase}") for index, phrase in enumerate(sequence, start=1)
    ]
    assert all(positions[index] < positions[index + 1] for index in range(len(positions) - 1))


def test_pr9_component_contract_registry_requires_unspecified_for_unknowns() -> None:
    """Prevent registry docs from inventing bridge/component values."""
    registry = _read(PR9_REGISTRY)

    required_fields = [
        "`component_id`",
        "`canonical_name`",
        "`repo_vocabulary_anchor`",
        "`web_runtime_anchor`",
        "`ios_runtime_anchor`",
        "`token_dependencies`",
        "`storybook_review_anchor`",
        "`figma_reference_anchor`",
        "`penpot_reference_anchor`",
        "`code_connect_anchor`",
        "`accessibility_contract`",
        "`visual_regression_contract`",
        "`status`",
    ]

    for field in required_fields:
        assert field in registry

    assert (
        "Do not invent values. If repo truth does not confirm a value, write `unspecified`."
        in registry
    )
    assert (
        "The registry is a repo-governed contract index. It is not a design-tool authority."
        in registry
    )


def test_pr9_visual_and_accessibility_decisions_fail_closed() -> None:
    """Require visual and a11y regression decisions before implementation."""
    corpus = "\n".join([_read(PR9_PACKET), _read(PR9_SPEC), _read(PR9_REGISTRY)])

    required = [
        "Visual and accessibility regression decisions are mandatory fail-closed gates",
        "if no visual regression lane exists for a component, future implementation must stop",
        "if no accessibility regression lane exists for a component, future implementation must stop",
        "a screenshot, Storybook story, Figma node, or prompt review is not a substitute",
        "If either is missing, the implementation PR must fail closed",
    ]

    for phrase in required:
        assert phrase in corpus


def test_pr9_agent_execution_records_and_review_chains_are_required() -> None:
    """Require execution records, post-open chain, and post-bot chain for PR-9."""
    corpus = "\n".join([_read(PR9_PACKET), _read(WORKFLOW), _read(TEMPLATE)])

    required = [
        "Every role must produce an execution record or pass/finding note before PR open.",
        "Required pre-open skill passes:",
        "Post-open pass, immediately after PR creation:",
        "After the first bot review, rerun on current head:",
        "Codex Security plugin diff scan",
        "Before merge readiness, a local Agent Run Summary must exist under `artifacts/agent_runs/`",
        "The artifact is local only and must never be committed.",
    ]

    for phrase in required:
        assert phrase in corpus

    for agent in [
        "agent-coordinator",
        "creative-designer",
        "frontend-engineer",
        "cursor-specialist-agent",
        "architecture-specialist",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
    ]:
        assert agent in corpus


def test_pr9_preserves_token_runtime_and_bridge_authority_boundaries() -> None:
    """Require PR-9 to preserve repo/token/runtime authority boundaries."""
    corpus = "\n".join([_read(PR9_PACKET), _read(PR9_SPEC), _read(PR9_REGISTRY)])

    required = [
        "`/tokens` remains token authoring truth.",
        "`frontend/src/styles/tokens.css` remains web runtime token truth.",
        "`frontend/src/styles/tokens.ts` remains a typed mirror/helper.",
        "`ios/PulsePlate/DesignSystem/DesignTokens.generated.swift` remains generated output.",
        "`ios/PulsePlate/DesignSystem/DesignTokens.swift` remains iOS runtime token grouping.",
        "Web and iOS implementation slices must stay thin over repo/backend truth.",
        "Code Connect activation status is `unspecified`.",
    ]

    for phrase in required:
        assert phrase in corpus
