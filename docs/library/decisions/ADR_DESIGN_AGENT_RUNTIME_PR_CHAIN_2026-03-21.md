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
4. design-agent PR4: optional bounded creative-research lane after runtime and
   preview contracts stabilize. Evidence: `scripts/design/contracts.py:206`,
   `scripts/design/canvas_artifact.py:153`, `scripts/design/html_preview.py:67`

`bug-hunter` is required as a post-open fix lane for every PR in this
initiative before review-ready status can be claimed. Evidence:
`.cursor/agents/bug-hunter.md:1`, `docs/orchestration/AGENT_ROUTING_GRAPH.md:71`

## Current-state interpretation after merged baseline

The original staged rollout remains historically accurate as the accepted
implementation direction, but the current repo state has moved forward:

- baseline PR1 artifact publishing is already realized in `main`
- baseline PR2 adaptive runtime semantics are already realized in `main`
- baseline PR3 deterministic preview semantics are already realized in `main`
- no design-agent-specific PR4 follow-up has been opened yet

Current-state tracking now belongs to:

- `docs/design/DESIGN_AGENT_RUNTIME_PR_CHAIN.md`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-agent-runtime-pr-chain`

This ADR remains part of the historical evidence pack and accepted direction;
it is not the primary status tracker for whether baseline stages are already
merged.

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

## Exit criteria

This ADR is considered realized when all bounded rollout gates below are true:

1. PR1, PR2, and PR3 from the initiative chain are merged; design-agent PR4
   remains optional and only proceeds if runtime and preview contracts stay
   bounded. Evidence:
   `docs/design/DESIGN_AGENT_RUNTIME_PR_CHAIN.md:20`,
   `docs/roadmap/BACKLOG_LEDGER.md:499`
2. Each merged initiative PR completed its post-open `bug-hunter` fix pass
   before review-ready status was claimed. Evidence:
   `.cursor/agents/bug-hunter.md:1`,
   `docs/roadmap/BACKLOG_LEDGER.md:509`
3. Automated verification stays green for the runtime seam: instruction and
   manifest semantics are covered by the governed contract tests, and the
   deterministic browser preview remains validated on top of
   `pulseplate_canvas_v1`. Evidence: `scripts/design/contracts.py:206`,
   `scripts/design/html_preview.py:67`,
   `tests/test_design_generation_pipeline.py:723`,
   `tests/test_design_generation_pipeline.py:902`
4. Promotion artifacts and backlog linkage remain published and current for the
   initiative umbrella item until the ledger item is closed. Evidence:
   `docs/library/promotion/2026-03-21_design-agent-runtime-pr-chain_promotion-log.md:1`,
   `docs/roadmap/BACKLOG_LEDGER.md:495`

## Promotion targets

- Initiative SoT:
  [`docs/design/DESIGN_AGENT_RUNTIME_PR_CHAIN.md`](../../design/DESIGN_AGENT_RUNTIME_PR_CHAIN.md)
- Backlog umbrella item:
  [`docs/roadmap/BACKLOG_LEDGER.md`](../../roadmap/BACKLOG_LEDGER.md)
- Supporting artifacts:
  - [`docs/library/brainstorm/2026-03-21_design-agent-runtime-pr-chain.md`](../brainstorm/2026-03-21_design-agent-runtime-pr-chain.md)
  - [`docs/library/research/2026-03-21_design-agent-runtime-pr-chain_evidence.md`](../research/2026-03-21_design-agent-runtime-pr-chain_evidence.md)
  - [`docs/library/promotion/2026-03-21_design-agent-runtime-pr-chain_promotion-log.md`](../promotion/2026-03-21_design-agent-runtime-pr-chain_promotion-log.md)
