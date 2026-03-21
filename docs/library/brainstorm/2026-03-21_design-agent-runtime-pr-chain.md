# Brainstorm: Design-Agent Runtime PR Chain

- Date: 2026-03-21
- Coordinator: `agent-coordinator`
- Status: promoted

## Decision question

How should PulsePlate extend the existing code-native design runtime so agents
can generate, visualize, and adapt governed presentation layers without
creating a second source of truth or allowing design logic to override domain
logic?

## Success criteria

- One initiative document defines the PR1-PR4 chain, scope, and acceptance
  rules.
- PR1 artifacts exist in the project knowledge library with explicit routing,
  synthesis, and promotion logs.
- Existing backlog items for adapter seam, layout archetypes, prompt-to-canvas,
  HTML preview, and Phase 2 env/API automation are linked under one umbrella
  initiative.
- Runtime contracts gain additive adaptive-presentation semantics only.
- Preview rendering remains internal, deterministic, and read-only.
- `bug-hunter` is mandatory as a post-open fix lane for every PR in this
  initiative.

## Constraints

- Repo-first source precedence remains canonical.
- `/tokens -> vocabulary -> instruction contract -> pulseplate_canvas_v1`
  remains the only topology and presentation source-of-truth chain.
- No new public FastAPI or iOS thin-client contracts in the first wave.
- No live self-modifying product UI.
- Creative research stays bounded and internal until after runtime and preview
  contracts stabilize.

## Routing Card

- Decision question:
  - extend the governed design runtime into adaptive semantics and internal
    preview without displacing repo truth
- Success criteria (3-7):
  - see section above
- Constraints:
  - tooling-first, web/browser-first, HITL-governed, no new public endpoints
- Primary agents (from capability matrix):
  - `agent-coordinator`, `creative-designer`, `frontend-engineer`,
    `qa-engineer-agent`
- Advisory agents:
  - `architecture-specialist`, `cursor-specialist-agent`,
    `designer-artist-agent`
- Tracks to run in parallel:
  - PR1 docs/scope track
  - PR2 runtime-contract track
  - PR3 HTML-preview track
- Formal reviewer(s):
  - `qa-engineer-agent`, `bug-hunter`

## Options considered

1. Treat the work as a brand-new design-agent platform with its own mutable
   runtime and tool graph.
2. Extend the existing code-native design runtime with additive contracts,
   explicit preview rendering, and bounded orchestration rules.

## Chosen direction

Option 2. The repo already has a governed design runtime with reusable layout
templates, executable instructions, adapter seams, and `pulseplate_canvas_v1`.
The correct move is to extend that lane with adaptive presentation semantics
and deterministic HTML preview instead of introducing a parallel design system.

## Risks

- Contract drift if `interaction_contract` is added in instructions but not
  enforced in canvas artifacts, manifest metadata, and verification.
- Preview drift if HTML rendering starts inventing topology rather than
  consuming `pulseplate_canvas_v1`.
- Workflow drift if `bug-hunter` is implied informally rather than explicitly
  documented as a required post-open lane.
- Governance drift if creative research begins before runtime boundaries and
  immutable oracles are locked.

## Next artifact links

- Evidence:
  [`docs/library/research/2026-03-21_design-agent-runtime-pr-chain_evidence.md`](../research/2026-03-21_design-agent-runtime-pr-chain_evidence.md)
- Synthesis:
  [`docs/library/decisions/ADR_DESIGN_AGENT_RUNTIME_PR_CHAIN_2026-03-21.md`](../decisions/ADR_DESIGN_AGENT_RUNTIME_PR_CHAIN_2026-03-21.md)
- Promotion log:
  [`docs/library/promotion/2026-03-21_design-agent-runtime-pr-chain_promotion-log.md`](../promotion/2026-03-21_design-agent-runtime-pr-chain_promotion-log.md)
