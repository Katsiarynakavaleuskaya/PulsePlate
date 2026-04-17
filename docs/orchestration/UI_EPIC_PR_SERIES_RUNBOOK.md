# UI Epic PR Series Runbook

**Version:** 2026-04-18 (`America/New_York`)
**Scope:** Post-bridge UI/UX series launched from synced `origin/main` after the
merged design-bridge baseline.
**Execution surface:** `worktrees/ui-epic-pr1-runbook`

## Purpose

This runbook is the canonical operating contract for the post-bridge UI epic
line.

The bridge baseline is already merged on `main`:
- PR `#1386` `docs(ledger): close design-agent bridge drift`
- PR `#1391` `feat(design-ops): operationalize bridge preflight, capture, and first parity pack`

This lane follows that merged baseline and does not reopen bridge-closeout work.
Its job is to move from design-ops parity into the first product-facing UI
coherence slices on current `main`.

## Contract Boundaries

- This runbook owns process, PR order, role order, sync points, and hard rules
  for the UI epic line.
- Branch-scoped packets, handoffs, and session artifacts own the exact
  deliverable inventory and evidence capture for each PR.
- This runbook stays pointer-only. It must not duplicate per-PR evidence tables
  that belong in the active packet or handoff.

**IN**
- iOS visible coherence and localization work for `RootTabs`, `ProgressView`,
  and the remaining visible-copy debt in `PlateView`
- one governed semantic surface seam for iOS `Home`, `Plate`, and `Progress`
- Storybook-backed web parity expansion only after the iOS coherence slices are
  stabilized
- late-phase thin-client consumption of the already existing backend
  `next_best_action` contract

**OUT**
- reopening merged design-bridge operationalization or parity-closeout work
- billing, entitlement, checkout, provider modernization, or pricing changes
- deploy/runtime infrastructure changes
- Cloudflare preview as merge truth
- a new universal `/api/v1/ui/state` endpoint or any second backend UI rail
- product-flow rewrites under the cover of UI polish

## Source of Truth

- Coordinator workflow: `docs/orchestration/workflow.md`
- Canonical orchestration governance contract:
  `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
- Bridge baseline packet:
  `docs/orchestration/DESIGN_BRIDGE_OPERATIONALIZATION_PACKET_2026-04-11.md`
- Bridge parity evidence:
  `docs/design/DESIGN_BRIDGE_FIRST_PARITY_PACK_2026-04-11.md`
- Design tooling operating model:
  `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
- Worktree isolation policy:
  `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`
- Canonical web review entrypoint:
  `frontend/src/stories/PulsePlateDesignSystemGuidelines.mdx`
- iOS execution surface:
  `ios/PulsePlate.xcworkspace` with scheme `PulsePlate`
- Deferred/series tracking:
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ui-epic-post-bridge-series`

## Wave Objective

Stabilize the first visible UI gaps on current `main` without reopening backend
contract work or the merged design-bridge lane:
- remove the most obvious iOS copy and localization drift,
- introduce one governed semantic surface seam for the mature iOS surfaces,
- expand governed Storybook review only after iOS coherence is in place,
- keep clients thin when they later consume the already existing backend
  `next_best_action` contract.

## Review Surfaces and Evidence

- Web review is Storybook-first. Product routes remain implementation surfaces,
  not design canon.
- iOS review is simulator-first on `ios/PulsePlate.xcworkspace` and scheme
  `PulsePlate`.
- Screen captures, previews, and ad hoc screenshots are supporting evidence
  only. They do not replace Storybook or simulator verification.
- Every PR in this lane must store its exact evidence path in the active packet,
  handoff, or session artifact rather than extending this runbook.

## PR Series

### PR-1: Lane bootstrap

- Branch: `codex/ui-epic-runbook-bootstrap`
- Title: `docs(ui-ux): add post-bridge UI epic runbook and lane packet`
- Scope:
  - add this runbook,
  - add one explicit backlog anchor for the post-bridge UI epic line,
  - lock PR order, role order, worktree isolation, and evidence rules.

### PR-2: iOS visible coherence

- Branch: `codex/ui-ios-visible-coherence`
- Title: `fix(ios): localize root tabs, progress, and plate visible copy`
- Scope:
  - remove mixed-language tab labels from `RootTabs`,
  - localize hardcoded visible copy in `ProgressView`,
  - localize remaining visible copy in `PlateView`, `MealEntryView`, and
    `NutritionDetailsView`,
  - preserve existing product behavior.

### PR-3: iOS semantic surface seam

- Branch: `codex/ui-ios-surface-seam`
- Title: `feat(ios): add semantic surface roles for home plate and progress`
- Scope:
  - introduce one semantic surface role abstraction,
  - move `Home`, `Plate`, and `Progress` onto that seam,
  - keep the change bounded to surface governance, not product flow redesign.

### PR-4: Web Storybook parity expansion

- Branch: `codex/ui-web-storybook-parity-pack`
- Title: `feat(web): expand storybook parity for plate progress and paywall review surfaces`
- Scope:
  - expand governed Storybook review for real runtime surfaces already on
    `main`,
  - keep product routes as implementation surfaces,
  - reuse existing design tokens and `GlassCard`.

### PR-5: Thin-client hint consumption

- Branch: `codex/ui-consume-next-best-action`
- Title: `feat(clients): consume existing next_best_action hints on selected UI surfaces`
- Scope:
  - consume the already existing backend `next_best_action` contract on bounded
    web and iOS surfaces,
  - keep clients renderer-only,
  - do not introduce a new UI API rail.

## Routing Card

- Decision question: How should PulsePlate execute the post-bridge UI line on
  `main` without reopening design-ops baseline work or mixing in backend
  monetization/runtime scope?
- Primary agent: `agent-coordinator`
- Default role order:
  1. `agent-coordinator`
  2. `creative-designer`
  3. `frontend-engineer`
  4. advisory `cursor-specialist-agent`
  5. optional `architecture-specialist`
  6. mandatory post-open `qa-engineer-agent -> bug-hunter`
- Architecture-heavy exception:
  - for the iOS surface-seam PR, move `architecture-specialist` before
    implementation.
- Recommended skills:
  - `pulseplate-workflow`
  - `plan-work`
  - `pulseplate-frontend-ui` when implementation starts
  - `build-ios-apps:swiftui-ui-patterns`
  - `build-ios-apps:swiftui-view-refactor`
  - `build-web-apps:react-best-practices` only when PR-4 starts

## Sync Points

1. **Bootstrap locked**
   - Runbook merged
   - Backlog anchor merged
   - PR order and boundaries are fixed
2. **iOS coherence locked**
   - `RootTabs`, `Progress`, and `Plate` visible copy is localized
   - simulator sanity captured on current head
3. **Surface seam locked**
   - one semantic surface seam exists for `Home`, `Plate`, and `Progress`
   - no product-flow drift introduced
4. **Web parity locked**
   - Storybook surfaces exist for `Plate`, `Progress`, and paywall review
   - build and Storybook build pass locally
5. **Hint consumption locked**
   - clients consume `next_best_action`
   - clients do not compute business logic
6. **Merge-ready evidence**
   - current-head checks are green
   - disposition artifact is up to date
   - mandatory post-open review lane is complete

## Hard Rules

- One PR equals one dedicated worktree from synced `origin/main`.
- Do not edit the dirty root tree.
- Do not reuse colleague branches or worktrees.
- Do not replace the declared role order with an ad hoc internal role stack.
- The canonical post-open lane remains `qa-engineer-agent -> bug-hunter`.
- Web review remains Storybook-first for this line.
- iOS evidence remains simulator-first for this line.
- Cloudflare preview/deploy is advisory only and not merge truth.
- Do not claim a full Liquid Glass migration in the iOS surface-seam PR.
- Do not add `/api/v1/ui/state` or any second backend UI rail in this series.
- Any deferred UI gap discovered during execution must be recorded immediately in
  `docs/roadmap/BACKLOG_LEDGER.md`.

## Validation

Every PR in this line runs:
- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`

PR-2 additionally runs:
- targeted iOS tests for visible localized surfaces,
- simulator sanity for workspace `ios/PulsePlate.xcworkspace` and scheme
  `PulsePlate`,
- `make verify`

PR-3 additionally runs:
- targeted iOS unit, snapshot, or view-level tests for surface-role mapping,
- simulator sanity,
- `make verify`

PR-4 additionally runs:
- `cd frontend && npm run build`
- `cd frontend && npm run build-storybook`
- relevant frontend tests,
- `make verify`

PR-5 additionally runs:
- targeted frontend and iOS rendering tests,
- contract-safe verification that clients consume hints without computing them,
- `make verify`

## Deferred from This Wave

- Any new backend-owned universal UI decision rail
- Any experimentation contract or runtime UI variant system beyond existing
  repo contracts
- Billing, entitlement, and provider modernization work
- Deploy/runtime infrastructure changes
