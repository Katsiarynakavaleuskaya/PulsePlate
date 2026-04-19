# ADR: UI Semantic Surface Seam (2026-04-19)

- Status: Accepted (temporary seam)
- Date: 2026-04-19
- Owner: @katsiaryna_kavaleuskaya
- Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ui-epic-post-bridge-series`

## Context

The post-bridge UI epic intentionally starts with visible-copy coherence before
it introduces any reusable surface abstraction. The next planned iOS slice adds
one semantic surface seam for `Home`, `Plate`, and `Progress`, but that seam is
temporary governance work, not a product-flow rewrite.

Evidence:
- `docs/orchestration/UI_EPIC_PR_SERIES_RUNBOOK.md:104-142`
- `docs/orchestration/MONETIZATION_PLANNING_WAVE_PR_SERIES_RUNBOOK.md:95-103`
- `frontend/src/api/__tests__/thin-client-guards.test.ts:7-19`
- `frontend/AGENTS.md:27-38`
- `ios/AGENTS.md:86-92`

## Decision

Keep the UI semantic surface seam explicitly temporary and bounded:

1. The seam is allowed only for the PR-3 lane that covers `Home`, `Plate`, and
   `Progress`.
2. The seam must remain presentation-only; it cannot introduce local business
   logic, entitlement inference, or a second backend UI rail.
3. PR-3 must carry simulator evidence and targeted tests that prove the seam did
   not widen product flow or thin-client scope.

## Exit Criteria

Retire this seam only when ALL are true:

1. The governed surfaces (`Home`, `Plate`, `Progress`) share one stable surface
   vocabulary with no remaining one-off fallback styling rules.
2. PR-4 Storybook parity and PR-5 hint-consumption work both reuse the seam
   without widening it into business-logic computation.
3. No open blocker remains in
   `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ui-epic-post-bridge-series`.
4. The follow-on lane can delete the temporary seam wording from the runbook and
   close this ADR as superseded or retired.

## Blockers

- Missing targeted iOS evidence for the seam-bound surfaces on the PR-3 head.
- Any proposal that turns the seam into a new UI decision rail or local logic
  engine.
- Missing Storybook/simulator evidence that the seam stays presentation-only
  across the later PR-4 / PR-5 slices.

## Consequences

- The runbook can reference a governed seam without pretending it is permanent.
- Reviewers have one explicit place to verify why the seam exists and how it
  must be removed.
- The backlog item remains the operational SoT for blockers and DoD, while this
  ADR owns the temporary-architecture contract.
