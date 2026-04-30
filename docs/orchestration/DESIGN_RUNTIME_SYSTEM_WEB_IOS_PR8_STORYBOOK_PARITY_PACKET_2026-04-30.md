# PR-8 Storybook Parity Packet

- Date: 2026-04-30
- Branch: `codex/storybook-design-review-parity`
- Worktree: `worktrees/design-runtime-system-pr8`
- PR series: Design Runtime System Web+iOS
- Phase: PR-8 Storybook parity

## Summary

PR-8 expands Storybook as the repo-native review-only lane for implemented web
design-system surfaces. It does not migrate product screens, alter backend
contracts, regenerate tokens, or change iOS runtime code.

The lane starts from synced `origin/main` after PR-7 merged in #1595. Operator
override permits implementation while the user monitors fresh `main` health;
merge-ready still requires current-head CI green and strict review governance.

## Coordinator Scope Lock

Role order:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. advisory `cursor-specialist-agent`
5. reviewer `architecture-specialist`
6. mandatory post-open `qa-engineer-agent -> bug-hunter`

In scope:

- Storybook-only review surfaces for governed primitives and implemented web
  routes.
- Deterministic local Storybook harnesses for session/API state.
- Backlog and review-governance artifacts for this PR slice.

Out of scope:

- Product screen migration or route behavior redesign.
- Backend, OpenAPI, billing, entitlement, iOS, token generation, Cloudflare,
  deploy, App Store, Figma writes, or design asset export work.
- Reintroducing Storybook addon-actions, addon-interactions, addon-essentials,
  or widening to Storybook 9.

## Skills And Plugins

Required PulsePlate skills:

- `pulseplate-workflow`
- `pulseplate-design-launch-system`
- `pulseplate-frontend-ui`
- `pulseplate-gates`
- `pulseplate-guards`
- `pulseplate-ledger`
- `pulseplate-pr-review`

Required external capabilities:

- GitHub for PR creation, current-head checks, review threads, and merge.
- CodeRabbit for post-open review input and disposition lifecycle.
- Build Web Apps / React best practices for Storybook and React review quality.

Optional only if evidence is needed:

- Browser Use for local Storybook visual smoke.
- Figma read-only provenance only.

Explicitly not used for this PR:

- Canva, Cloudflare, Netlify, Remotion, LaTeX, Hugging Face, Jam, Life Science,
  Expo, Build iOS Apps, Build macOS Apps.

## Implementation Plan

- Add Storybook parity stories for `Home`, `Nutrition Setup`, `Pro Paywall`,
  and locked/unlocked `Plate`.
- Add missing governed primitive state stories for `Skeleton` and `EmptyState`;
  expand `Button` with disabled and full-width review states.
- Add a Storybook-only deterministic API/session support harness under
  `frontend/src/stories/`.
- Keep all live product route code behavior stable and use existing primitives,
  API client dependency injection, `MemoryRouter`, and i18n bootstrap.
- Update Storybook guidance docs and backlog ledger to mark PR-8 active.

## Validation

Start gates:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- coordinator bootstrap via `scripts/orchestration/task_bootstrap.py`

Local scoped gates before push:

- `cd frontend && npm test -- --run src/stories/__tests__/storybookParity.test.ts src/pages/__tests__/Plate.storyHarness.test.tsx src/components/ui/__tests__/Button.test.tsx src/components/ui/__tests__/Skeleton.test.tsx src/components/ui/__tests__/EmptyState.test.tsx`
- `cd frontend && npm run build`
- `cd frontend && npm run build-storybook`
- `python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json`
- `pytest -q tests/test_repo_policy_guards.py`
- `pre-commit run --all-files`

Operator-approved machine-heavy deferral:

- Do not run full local `make verify`.
- Document the deferral in the PR body and `docs/review/PR_<N>_FIXED_MAPPING.md`.
- Use GitHub current-head CI as the heavy signal before merge-ready claim.

## Review Governance

Open PR as draft first. After PR number exists:

- create `docs/review/PR_<N>_FIXED_MAPPING.md`
- update PR body with local scoped gates, current-head CI, and deferral note
- run CodeRabbit disposition workflow
- run mandatory `qa-engineer-agent -> bug-hunter`
- mark ready only after strict merge wrapper passes, actionables are resolved or
  mapped, and the wait-window is observed

## Merge And Cleanup

After merge:

1. checkout root `main`
2. `git fetch --prune origin`
3. `git merge --ff-only origin/main`
4. confirm PR state `MERGED`
5. confirm `HEAD...origin/main = 0 0`
6. remove only PR-8 worktree, local PR-8 branch, and PR-8 temp artifacts
7. run `git worktree prune`
8. determine the next design epic step from live backlog/runbook truth
