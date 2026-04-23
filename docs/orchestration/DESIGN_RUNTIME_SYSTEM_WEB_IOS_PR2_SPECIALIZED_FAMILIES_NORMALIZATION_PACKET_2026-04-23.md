# Design Runtime System Web+iOS PR-2 Specialized Families Normalization Packet

**Version:** 2026-04-23 (`America/New_York`)
**Epic Slug:** `epic/design-runtime-system-web-ios-v1`
**Slice:** `PR-2`
**PR:** `#1510`
**Worktree:** `worktrees/design-runtime-system-pr2`
**Branch:** `codex/design-specialized-families-normalization`
**PR Phase:** `post_open_review`
**Design Lane Mode:** `execution`
**Title:** `feat(frontend): normalize specialized design families into shared governed patterns`

## Summary

This packet is the branch-scoped field contract for `PR-2` of the design
runtime system web+iOS epic line.

`PR-0` and `PR-1` are already merged. This slice normalizes the current
specialized web families into shared governed components while keeping current
product consumers stable through thin adapters. Draft PR `#1510` is now open
for the post-open review cycle.

Evidence:
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR_SERIES_RUNBOOK.md`
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR0_BOOTSTRAP_PACKET_2026-04-22.md`
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR1_MISSING_GOVERNED_PRIMITIVES_PACKET_2026-04-23.md`
- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/design/ui_component_vocabulary.json`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-runtime-system-web-ios-epic`

## Scope

### IN
- normalize current specialized-existing families into shared governed web
  components for:
  - `badge`
  - `progress`
  - `hero`
  - `stats-card`
  - `stepper/progress-indicator`
- keep route-level and feature-level product consumers source-compatible through
  thin adapters
- expose the normalized families inside the existing Storybook-first
  design-system review surface
- add targeted Vitest and accessibility coverage for the shared family layer and
  its thin adapters

### OUT
- `/tokens` authoring or generated token mirror changes
- iOS runtime, simulator, or `build-ios-apps` execution
- product-shell convergence beyond the existing consumers already carrying these
  families
- backend, OpenAPI, billing, entitlement, provider, or deploy changes
- `figma-manifest` hardening or Figma mutation authority
- Storybook parity-wide expansion beyond the existing design-system review lane

## Files

- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR2_SPECIALIZED_FAMILIES_NORMALIZATION_PACKET_2026-04-23.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `frontend/src/components/ui/**`
- `frontend/src/components/design-system/**`
- `frontend/src/components/VipBadge.tsx`
- `frontend/src/features/progress/LiveProgressIndicator.tsx`
- `frontend/src/pages/Home.tsx`
- `frontend/src/pages/NutritionSetup/**`
- `docs/review/PR_<N>_FIXED_MAPPING.md`

## Role Order

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. advisory `cursor-specialist-agent`
5. reviewer `architecture-specialist`
6. post-open mandatory `qa-engineer-agent -> bug-hunter`

This order is fixed for the lane unless a later packet explicitly updates it.

## Plugin Policy

- `GitHub`: required for draft PR open, current-head checks, review disposition
  sync, and merge-readiness verification
- `Build Web Apps`: required for frontend implementation and Storybook/test
  workflow
- `CodeRabbit`: required as a post-open review input
- `Computer Use`: optional only when visual Storybook/browser evidence is
  needed
- `Figma`: optional read-only reference only
- `Build iOS Apps`, `Build macOS Apps`, `Cloudflare`, `Netlify`, `Expo`,
  `Life Science Research`, and `Remotion`: not used in `PR-2`

## Implementation Contract

- add shared governed families under `frontend/src/components/ui/` for:
  - `Badge`
  - `ProgressIndicator`
  - `Hero`
  - `StatsCard`
  - `Stepper`
- keep shared families presentation-first; move product logic to thin adapters:
  - `VipBadge` keeps feature gating and telemetry, then renders through
    governed `Badge`
  - `LiveProgressIndicator` keeps live-status logic and telemetry, then renders
    through governed `ProgressIndicator`
  - `Home` extracts the calm hero shell into governed `Hero`
  - `MacroCards` composes governed `StatsCard`
- introduce the first governed `Stepper` on the existing two-state Nutrition
  Setup flow:
  - `Profile`
  - `Results`
- `Stepper` current state is derived from the existing `values === null`
  container seam; no new wizard or additional flow state is introduced
- Storybook remains review-only; no second review surface is created

## Validation Bundle

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `cd frontend && npm run build`
- targeted Vitest coverage for the new shared families and thin adapters
- targeted accessibility assertions through the existing `jest-axe` harness
- `make verify` before any merge-ready claim on the latest head

## Review Path

- draft PR `#1510` is open
- create canonical artifact `docs/review/PR_<N>_FIXED_MAPPING.md`
- sync the PR body mirror after review dispositions
- use GitHub current-head truth plus CodeRabbit review input; do not rely on
  stale historical runs

## Merge Path

- move the lane to `post_open_review` after the draft PR is opened
- move the lane to `merge_ready` only on current head after local validation,
  review artifact sync, and required current-head checks are coherent
- run:
  - `make verify`
  - `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`

## Cleanup Path

- after merge:
  - `git checkout main`
  - `git fetch --prune origin`
  - `git merge --ff-only origin/main`
  - confirm `gh pr view <N> --json state` returns `MERGED`
  - remove only `worktrees/design-runtime-system-pr2`, the local branch
    `codex/design-specialized-families-normalization`, and slice-local temp
    artifacts
  - run `git worktree prune`

## DoD

- shared governed web families exist for `badge`, `progress`, `hero`,
  `stats-card`, and `stepper/progress-indicator`
- existing route-level consumers remain behaviorally stable through thin
  adapters
- Storybook design-system review surface shows the normalized families without
  creating a second review lane
- targeted tests cover accessibility- and contract-critical behavior
- the slice introduces no token-authoring, iOS, or product-shell ownership
  drift
