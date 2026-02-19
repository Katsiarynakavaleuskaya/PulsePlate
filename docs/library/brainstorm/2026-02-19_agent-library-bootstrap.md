# Brainstorm: Agent Library Bootstrap

- Date: 2026-02-19
- Coordinator: `agent-coordinator`
- Status: in_progress

## Decision question

How should we bootstrap a reusable project knowledge library so agents can
enrich knowledge deterministically and ship PRs from brainstorm artifacts?

## Success criteria

- One canonical library tree exists under `docs/library/`.
- First-cycle artifacts exist: brainstorm, research evidence, promotion log.
- Workflow references are clickable and point to SoT docs.
- Evidence and anti-drift rules are explicit.
- PR-ready checklist is available for future cycles.

## Constraints

- No hidden model memory as canonical knowledge.
- Promotion is artifact-based only (KPP).
- Deferred items must be ledgered immediately.
- Keep scope docs/process only.

## Routing Card

- Decision question:
  - bootstrap deterministic knowledge library and promotion flow
- Success criteria (3-7):
  - see section above
- Constraints:
  - KPP + anti-drift + evidence contract
- Primary agents (from capability matrix):
  - `agent-coordinator`, `architecture-specialist`
- Advisory agents:
  - `web-research-agent`, `security-auditor`
- Tracks to run in parallel:
  - architecture/process track, research/evidence track
- Formal reviewer(s):
  - `architecture-specialist`

## Options considered

1. Minimal scaffold first, expand per cycle.
2. Full templates for all domains immediately.

## Chosen direction

Option 1. Start minimal and deterministic, then promote additional templates
when recurring patterns appear.

## Risks

- Drift if multiple docs duplicate policy wording.
- Empty rituals if evidence contract is not enforced.

## Next artifact links

- Research evidence:
  [`docs/library/research/2026-02-19_agent-library-bootstrap_evidence.md`](../research/2026-02-19_agent-library-bootstrap_evidence.md)
- Promotion log:
  [`docs/library/promotion/2026-02-19_agent-library-bootstrap_promotion-log.md`](../promotion/2026-02-19_agent-library-bootstrap_promotion-log.md)
