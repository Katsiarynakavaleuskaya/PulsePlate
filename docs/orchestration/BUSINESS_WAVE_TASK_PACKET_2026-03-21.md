# Business Wave Task Packet

**Date:** 2026-03-21 (`America/New_York`)
**Mode:** Governance-first, worktree-isolated, documentation-first
**Worktree:** `worktrees/business_wave_bootstrap`
**Branch:** `feat/business-wave-bootstrap`

## Decision Question

How should PulsePlate operationalize a business-line wave that expands director-level business orchestration and automates B2B collateral generation without introducing runtime drift or duplicate source-of-truth layers?

## Success Criteria

1. Business-line execution starts in a clean worktree off `origin/main`.
2. The business role is upgraded to director-level responsibilities without creating a duplicate agent.
3. B2B proposal and pitch-deck inputs live in repo markdown under existing audience-pack canon.
4. Builders generate `.docx` and `.pptx` from repo-managed specs.
5. Generated binaries remain local-only and untracked.
6. Merge/readiness cadence is explicit for the PR series.

## Constraints

- No edits to the dirty local branch.
- No new runtime/product APIs in the first wave by default.
- Wellness-safe wording only; no medical claims.
- Unsourced numbers must remain placeholders.

## Routing

- Primary: `business-strategist-agent`
- Secondary: `marketing-strategist`
- Reviewer: `agent-coordinator`
- Additional review path: `bug-hunter`, `qa-engineer-agent`

## Recommended Skills

- `plan-work`
- `agents-md`
- `docs-sync`
- `doc`
- `slides`

## Artifact Set

### PR-1

- `docs/orchestration/BUSINESS_WAVE_PR_SERIES_RUNBOOK.md`
- `docs/orchestration/BUSINESS_WAVE_TASK_PACKET_2026-03-21.md`
- `docs/library/brainstorm/2026-03-21_business-wave-b2b-collateral.md`
- `docs/library/research/2026-03-21_business-wave-b2b-collateral_evidence.md`
- `docs/library/promotion/2026-03-21_business-wave-b2b-collateral_promotion-log.md`
- `docs/executive/PR_PORTFOLIO_BRIEF_DIRECTORS_2026-03.md`
- `docs/roadmap/BACKLOG_LEDGER.md`

### PR-2

- `.cursor/agents/business-strategist-agent.md`
- `.cursor/agents/agent-coordinator.md`
- `.cursor/agents/AGENTS.md`
- `docs/orchestration/AGENT_CONTEXT_MAP.md`
- `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
- `docs/agents/index.md`

### PR-3

- `docs/audience_pack/B2B_PARTNERSHIP_PROPOSAL_SPEC.md`
- `docs/audience_pack/B2B_PITCH_DECK_SPEC.md`
- `docs/audience_pack/BUSINESS_COLLATERAL_AUTOMATION.md`
- `scripts/business_collateral/*`
- `tests/test_business_collateral_builders.py`

## Risks

- Drift between audience-pack docs and builders
- Placeholder leakage into generated external materials
- Agent-role drift if routing/context/index files are not updated together
- Generated artifact sprawl if local-only outputs are not contained under ignored paths
