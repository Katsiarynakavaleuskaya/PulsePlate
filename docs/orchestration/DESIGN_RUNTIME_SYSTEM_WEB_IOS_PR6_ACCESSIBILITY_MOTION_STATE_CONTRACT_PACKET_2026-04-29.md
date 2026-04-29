# PR-6 Accessibility / Motion / State Contract Packet

## Coordinator Start

- Date: 2026-04-29
- Branch: `codex/design-accessibility-motion-state-contract`
- Worktree: `worktrees/design-runtime-system-pr6`
- Base: `origin/main` rebased to `2266d37b2026098e970cec365f28e5f5a9930bc5`
- First tracked artifact: this packet
- Coordinator bootstrap:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
  - `python3 scripts/orchestration/task_bootstrap.py --goal "PR-6 Accessibility / motion / state contract for governed shared web and iOS primitives" ...`

## Base Gate State

Fresh local `main` was fetched and ff-only synced before worktree creation.
`HEAD...origin/main` reported `0 0` at `c022929ad6173c2995e597953546ea9ba28cfd4a`.

The canonical `CI` workflow on `main` for `c022929ad6173c2995e597953546ea9ba28cfd4a`
was still `in_progress` at PR-6 execution time (`run 25112649730`) and later
completed `success`. During PR preparation, `origin/main` advanced to
`2266d37b2026098e970cec365f28e5f5a9930bc5`; this branch was rebased onto that
current base before push. Live `main` canonical `CI` for
`2266d37b2026098e970cec365f28e5f5a9930bc5` was `failure` at draft-open time,
while specialized workflows observed in the same window were green. The operator
explicitly approved opening PR-6 as a draft while watching `main`. This is not a
green-current claim; merge readiness remains blocked until current-head `main`
and PR CI are settled green and the strict merge wrapper passes.

## Role Order

The lane follows the coordinator-owned order:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. advisory `build-ios-apps`
5. advisory `cursor-specialist-agent`
6. reviewer `architecture-specialist`
7. post-open `qa-engineer-agent`
8. post-open `bug-hunter`

No role may be skipped without updating this packet or a successor runbook note.

## Skills And Plugins

Explicit PulsePlate skills:

- `pulseplate-workflow`
- `pulseplate-design-launch-system`
- `pulseplate-frontend-ui`
- `pulseplate-gates`
- `pulseplate-guards`
- `pulseplate-ledger`
- `pulseplate-pr-review`

Advisory or discovery-only if touched:

- `pulseplate-agent-product`
- `pulseplate-graphmap`
- `pulseplate-playwright-e2e`

Plugin use stays bounded:

- GitHub: PR, current-head checks, review lifecycle.
- CodeRabbit: review disposition lifecycle after PR opens.
- Build iOS Apps: iOS shared primitive validation and simulator evidence.
- Figma: read-only design intent only.

Out of scope unless the coordinator records an explicit handoff:

- `pulseplate-openapi-sync`
- `pulseplate-backend-endpoints`
- `pulseplate-app-store-release`
- `pulseplate-web-launch-site`
- `pulseplate-monetization-gtm`
- `pulseplate-ai-reports`
- Canva, Cloudflare, Remotion, LaTeX, macOS, Life Science.

Duplicate skill locations under `tools/codex_skills/` and `.agents/skills/` are
treated as the same named repo-local skills. Repo skill docs are the source of truth.

## Scope

PR-6 locks the shared accessibility, motion, and state contract for governed web
and iOS primitives:

- empty, loading, and error state semantics
- focus and keyboard visibility
- reduced-motion behavior
- minimum touch targets
- non-color-only status semantics

Governed contract document:

- `docs/design/ACCESSIBILITY_MOTION_STATE_CONTRACT.md`

This is a shared contract and primitive slice, not a product screen migration.

## Implementation Plan

Web shared primitives:

- Normalize `Button` focus-visible styling, reduced-motion behavior, loading
  semantics, and minimum touch target contract.
- Normalize `Skeleton` so decorative skeletons are hidden from assistive
  technology by default, while explicit status skeletons can be labeled.
- Normalize `EmptyState` built-in retry/start actions onto governed `Button`
  with explicit empty/error/loading semantics.

iOS shared primitives:

- Add a small design-system accessibility/motion helper for minimum touch
  targets and reduce-motion-aware animation selection.
- Update `PPButton` and `PPInput` to use the helper, keep a 44 pt minimum target,
  and disable press/focus animation when reduce motion is enabled.

## Out Of Scope

- Home, Plate, Progress, Weekly Plan, Profile, Paywall product screen migrations
- backend, billing, OpenAPI, token generation, Figma manifest, App Store assets
- new public API contracts or iOS public surface changes

## Validation

Start gates:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`

Local PR gates before push:

- `pytest -q tests/test_repo_policy_guards.py`
- `python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json`
- targeted frontend primitive/accessibility tests
- `cd frontend && npm run build`
- `make ios-test` with canonical simulator evidence
- `pre-commit run --all-files`
- `make verify`

`make verify` remains mandatory before merge readiness unless it is
machine-blocked. If blocked, work stops for an explicit operator exception.

## PR Lifecycle

- Open as draft first.
- After the PR number exists, create `docs/review/PR_<N>_FIXED_MAPPING.md`.
- Run CodeRabbit/review disposition workflow.
- Run mandatory `qa-engineer-agent -> bug-hunter` after opening.
- Mark ready only after local gates pass, current-head CI is green, review
  actionables are mapped/resolved, strict merge wrapper passes, and the
  wait-window is observed.

## Merge And Cleanup

After merge:

1. checkout root `main`
2. `git fetch --prune origin`
3. `git merge --ff-only origin/main`
4. confirm PR state `MERGED`
5. confirm `HEAD...origin/main = 0 0`
6. remove only PR-6 worktree, local branch, and PR-6 temp artifacts
7. `git worktree prune`

Next design epic slice: PR-7 `codex/design-export-lock-and-manifest-hardening`,
gated on stable post-merge `main`.
