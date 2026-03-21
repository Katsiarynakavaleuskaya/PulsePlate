# ADR: Design-Agent Runtime PR Chain

- Date: 2026-03-21
- Status: accepted
- Coordinator: `agent-coordinator`

## Context

PulsePlate already has a governed code-native design runtime, but the current
lane stops at instruction generation, local adapter execution, and canonical
`pulseplate_canvas_v1` emission. The next wave must add adaptive presentation
semantics and browser-visible preview without letting design/runtime tooling
become a second source of truth.

## Decision

PulsePlate will implement the design-agent initiative as a coordinator-led PR
chain with four bounded stages:

1. PR1: brainstorm, routing, synthesis, promotion, and backlog linkage
2. PR2: additive adaptive-presentation semantics via `interaction_contract`
3. PR3: deterministic HTML/browser preview on top of `pulseplate_canvas_v1`
4. PR4: optional bounded creative-research lane after runtime and preview
   contracts stabilize

`bug-hunter` is required as a post-open fix lane for every PR in this
initiative before review-ready status can be claimed.

## Why this direction

- It preserves the existing repo-first runtime rather than introducing a
  parallel design platform.
- It keeps domain truth upstream of presentation truth.
- It allows progressive productization of design execution without committing to
  live self-modifying UI.
- It fits existing backlog items and orchestration governance instead of
  redefining them.

## Consequences

### Positive

- Adaptive UX semantics become explicit and testable.
- Browser-visible previews become possible without Figma as a hard dependency.
- The coordinator can route design/runtime work through existing agent roles
  with deterministic review and bug-fix loops.

### Negative / Costs

- Manifest and verification semantics must expand, not just instruction
  generation.
- HTML preview becomes another governed artifact lane to test and maintain.
- PR cadence is intentionally slower because post-open `bug-hunter` review is
  mandatory.

## Promotion targets

- Initiative SoT:
  [`docs/design/DESIGN_AGENT_RUNTIME_PR_CHAIN.md`](../../design/DESIGN_AGENT_RUNTIME_PR_CHAIN.md)
- Backlog umbrella item:
  [`docs/roadmap/BACKLOG_LEDGER.md`](../../roadmap/BACKLOG_LEDGER.md)
- Supporting artifacts:
  - [`docs/library/brainstorm/2026-03-21_design-agent-runtime-pr-chain.md`](../brainstorm/2026-03-21_design-agent-runtime-pr-chain.md)
  - [`docs/library/research/2026-03-21_design-agent-runtime-pr-chain_evidence.md`](../research/2026-03-21_design-agent-runtime-pr-chain_evidence.md)
  - [`docs/library/promotion/2026-03-21_design-agent-runtime-pr-chain_promotion-log.md`](../promotion/2026-03-21_design-agent-runtime-pr-chain_promotion-log.md)
