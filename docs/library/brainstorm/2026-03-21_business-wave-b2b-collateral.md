# Brainstorm: Business Wave B2B Collateral Automation

**Date:** 2026-03-21 (`America/New_York`)
**Protocol:** `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`

## Routing Card

- Decision question: How should PulsePlate automate B2B proposal/deck generation while keeping business governance under coordinator-first repo canon?
- Success criteria:
  - markdown remains canonical,
  - audience-pack remains the fact/narrative root,
  - builders stay deterministic,
  - generated binaries stay out of git,
  - business agent role stays non-duplicated,
  - wave remains mergeable through normal PR governance.
- Constraints:
  - no runtime/API changes by default,
  - no medical claims,
  - no unsourced numbers,
  - no changes in the dirty current branch.
- Primary agents: `agent-coordinator`, `business-strategist-agent`
- Advisory agents: `marketing-strategist`, `cursor-specialist-agent`
- Tracks to run in parallel:
  - agent-governance sync,
  - audience-pack collateral spec,
  - collateral builder automation
- Formal reviewer(s): `bug-hunter`, `qa-engineer-agent`

## Option A: Docs-Only Collateral

Keep business materials in markdown only.

### Strengths

- Lowest implementation cost
- No new JS dependencies
- Minimal CI surface

### Weaknesses

- Manual copy/paste into partner-facing formats
- Weak reusability for B2B outreach
- Slower generation of external-ready assets

## Option B: Markdown SoT + JS Builders

Keep specs and facts in markdown, then generate `.docx` and `.pptx` from structured spec blocks inside the markdown.

### Strengths

- Preserves markdown as canonical SoT
- Supports repeatable external outputs
- Keeps generated binaries local-only
- Matches the requested B2B automation outcome

### Weaknesses

- Adds root Node dependencies
- Requires smoke coverage and output discipline
- Needs sync with audience-pack ownership protocol

## Option C: Separate Executive Canon

Create a parallel `docs/executive/*` fact/narrative stack and generate all collateral from it.

### Strengths

- Clear board-level packaging

### Weaknesses

- High duplication risk against audience-pack
- Harder to keep facts fresh
- Violates the current repo’s existing audience-pack SoT orientation

## Decision

Choose **Option B**.

## Why

- It preserves `docs/audience_pack/*` as the canonical business/narrative layer.
- It supports external-ready business development assets.
- It stays compatible with coordinator-first and worktree-based promotion.

## What to Measure

- Builder smoke test pass rate
- No `[VERIFY_*]` placeholders leaking into generated files unless intentionally allowed
- No tracked generated binaries
- Agent-document consistency after the role upgrade
- Executive brief remains thin and points back to `docs/audience_pack/*` instead of duplicating facts
