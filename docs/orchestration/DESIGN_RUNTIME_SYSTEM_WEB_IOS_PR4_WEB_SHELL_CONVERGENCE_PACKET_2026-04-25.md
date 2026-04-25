# Design Runtime System Web+iOS PR-4 Web Shell Convergence Packet

**Version:** 2026-04-25 (`America/New_York`)
**Epic Slug:** `epic/design-runtime-system-web-ios-v1`
**Slice:** `PR-4`
**PR:** `#1527`
**Worktree:** `worktrees/design-runtime-system-pr4`
**Branch:** `codex/frontend-product-shell-convergence`
**PR Phase:** `post_open_review`
**Design Lane Mode:** `execution`
**Title:** `feat(frontend): converge web shell onto governed tokens`

## Summary

This packet is the branch-scoped field contract for `PR-4` of the design
runtime system web+iOS epic line.

`PR-0`, `PR-1`, `PR-2`, and `PR-3` are treated as merged baseline. This slice
converges the shared web shell anatomy onto governed primitives and runtime
tokens without taking ownership of UI-epic product screens.

Execution starts from synced `origin/main` after current-head `main` health was
confirmed. Full local `make verify` remains operator-deferred for this
machine-heavy lane; PR-scoped local gates plus GitHub current-head CI are the
heavy readiness signal.

Evidence:
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR_SERIES_RUNBOOK.md`
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR0_BOOTSTRAP_PACKET_2026-04-22.md`
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR1_MISSING_GOVERNED_PRIMITIVES_PACKET_2026-04-23.md`
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR2_SPECIALIZED_FAMILIES_NORMALIZATION_PACKET_2026-04-23.md`
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR3_PRODUCT_TOKEN_EXPANSION_PACKET_2026-04-24.md`
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-runtime-system-web-ios-epic`

## Scope

### IN
- converge shared web shell anatomy onto governed primitives and runtime tokens
- keep route rendering, auth gating, tab-bar visibility, offline state, and
  toast wiring behaviorally stable
- preserve renderer-only frontend boundaries and thin HTTP adapter policy
- update the design epic backlog anchor so `PR-3` is recorded as merged and
  `PR-4` is active

### OUT
- product screen migration or ownership claims for `Home`, Nutrition Setup /
  Plate, Progress, Weekly Plan, Profile / Settings, or Paywall
- backend, OpenAPI, billing, entitlement, provider, or deploy changes
- iOS runtime or screen adoption
- `/tokens` authoring changes or generated token mirror regeneration
- Figma writes, manifest lock, Canva, Cloudflare, Remotion, Life Science,
  macOS, or Storybook parity-wide expansion

## Files

- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR4_WEB_SHELL_CONVERGENCE_PACKET_2026-04-25.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `frontend/src/App.tsx`
- `frontend/src/components/TabBar.tsx`
- `frontend/src/components/TabBar.helpers.ts`
- `frontend/src/__tests__/App.test.tsx`
- `frontend/src/components/__tests__/TabBar.test.tsx`
- `frontend/src/components/__tests__/TabBar.helpers.test.ts`
- `docs/review/PR_<N>_FIXED_MAPPING.md` after PR creation

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
- `Build Web Apps`: required for frontend implementation and test/build
  workflow
- `CodeRabbit`: required as post-open review input
- `Browser Use`: optional for local app/browser verification if runtime visual
  evidence is needed
- `Figma`: read-only design-intent reference only
- `Build iOS Apps`: advisory only if accidental generated iOS drift appears
- `Canva`, `Cloudflare`, `Remotion`, `Build macOS Apps`, `Netlify`, `Expo`,
  and `Life Science Research`: not used in `PR-4`

## Implementation Contract

- add or reuse a narrow shared shell primitive only for application-level
  anatomy, not for product screen ownership
- move shell-level hardcoded layout styling toward runtime CSS variables and
  governed vocabulary (`navigation/tab-bar`, `card`, `badge`, `button`, and
  existing shell anatomy as applicable)
- keep `TabBar` navigation labels, active-state matching, disabled-auth
  behavior, and VIP route filtering stable
- do not introduce direct `fetch()`, DTO changes, product business logic, or
  API rail changes
- do not edit generated token mirrors or `/tokens`

## Validation Bundle

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json`
- `cd frontend && npm test -- --run src/__tests__/App.test.tsx src/components/__tests__/TabBar.test.tsx`
- `cd frontend && npm run build`
- `cd frontend && npm run build-storybook` only if Storybook surfaces change
- `pre-commit run --all-files`

Full local `make verify` is intentionally not run by default for this
machine-heavy lane under the operator-approved exception. The PR body and
review mapping must document that deferral before any merge-ready claim.

## Review Path

- open the PR as draft first
- create canonical artifact `docs/review/PR_<N>_FIXED_MAPPING.md` after PR
  number assignment
- sync the PR body mirror after review dispositions
- use GitHub current-head truth plus CodeRabbit/Sourcery/Cubic review input;
  do not rely on stale historical runs
- run the mandatory `qa-engineer-agent -> bug-hunter` lane post-open

## Merge Path

- move the lane to `post_open_review` after draft PR creation
- move the lane to `merge_ready` only on current head after local PR-scoped
  validation, review artifact sync, review-thread disposition, and required
  current-head checks are coherent
- run:
  - `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`

## Cleanup Path

- after merge:
  - `git checkout main`
  - `git fetch --prune origin`
  - `git merge --ff-only origin/main`
  - confirm `gh pr view <N> --json state` returns `MERGED`
  - remove only `worktrees/design-runtime-system-pr4`, the local branch
    `codex/frontend-product-shell-convergence`, and slice-local temp artifacts
  - run `git worktree prune`

## DoD

- shared web shell anatomy consumes governed runtime tokens and stable
  primitives
- route rendering, auth gating, tab-bar visibility, disabled tab behavior, and
  product screens remain behaviorally stable
- backlog anchor records `PR-3` merged and `PR-4` active
- targeted frontend tests and `npm run build` pass
- Storybook build is run only if Storybook surfaces change
- no backend, OpenAPI, iOS, `/tokens`, generated mirrors, Figma writes, or
  product-screen ownership drift was introduced
