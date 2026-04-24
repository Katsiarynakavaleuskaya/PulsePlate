# Design Runtime System Web+iOS PR-3 Product Token Expansion Packet

**Version:** 2026-04-24 (`America/New_York`)
**Epic Slug:** `epic/design-runtime-system-web-ios-v1`
**Slice:** `PR-3`
**PR:** `#1519`
**Worktree:** `worktrees/design-runtime-system-pr3`
**Branch:** `codex/design-product-token-expansion`
**PR Phase:** `post_open_review`
**Design Lane Mode:** `execution`
**Title:** `feat(tokens): add product-level token layer for planning and premium surfaces`

## Summary

This packet is the branch-scoped field contract for `PR-3` of the design
runtime system web+iOS epic line.

`PR-0`, `PR-1`, and `PR-2` are treated as merged baseline. This slice activates
the narrow product-token color layer in `/tokens`, then regenerates the web and
iOS runtime mirrors through the canonical token build pipeline.

Execution started under an explicit operator override while current-head
`main` CI was still in progress. PR `#1519` remains in the post-open review
cycle until review-thread dispositions, current-head truth, and the strict
merge-readiness wrapper are coherent.

Evidence:
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR_SERIES_RUNBOOK.md`
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR0_BOOTSTRAP_PACKET_2026-04-22.md`
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR1_MISSING_GOVERNED_PRIMITIVES_PACKET_2026-04-23.md`
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR2_SPECIALIZED_FAMILIES_NORMALIZATION_PACKET_2026-04-23.md`
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-runtime-system-web-ios-epic`

## Scope

### IN
- add a product token authoring layer under `/tokens`
- include product color aliases for:
  - `paywall`
  - `premium`
  - `plate`
  - `progress`
  - `plan`
  - `coaching`
  - `status/feedback`
- extend `frontend/scripts/build-tokens.mjs` so product tokens generate into:
  - `frontend/src/styles/tokens.css`
  - `frontend/src/styles/tokens.ts`
  - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
- update token parity coverage for `/tokens`, CSS, TS, and Swift mirrors
- update token governance docs and the design epic backlog anchor

### OUT
- product screen migration or shell convergence
- iOS screen adoption
- Figma manifest lock or Figma mutation authority
- Storybook parity-wide expansion
- backend, OpenAPI, billing, entitlement, provider, deploy, Canva, Remotion,
  Life Science Research, or macOS work
- manual edits to generated token mirrors outside the build pipeline

## Files

- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR3_PRODUCT_TOKEN_EXPANSION_PACKET_2026-04-24.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `tokens/20_product/color.json`
- `frontend/scripts/build-tokens.mjs`
- `frontend/src/styles/tokens.css`
- `frontend/src/styles/tokens.ts`
- `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
- `tests/test_design_token_parity.py`
- `docs/review/PR_1519_FIXED_MAPPING.md`

## Role Order

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. advisory `build-ios-apps` for generated Swift mirror validation
5. advisory `cursor-specialist-agent`
6. reviewer `architecture-specialist`
7. post-open mandatory `qa-engineer-agent -> bug-hunter`

This order is fixed for the lane unless a later packet explicitly updates it.

## Plugin Policy

- `GitHub`: required for draft PR open, current-head checks, review disposition
  sync, and merge-readiness verification
- `Build Web Apps`: required for token build and frontend mirror validation
- `Build iOS Apps`: advisory for generated Swift mirror validation only
- `CodeRabbit`: required as post-open review input
- `Figma`: optional read-only design-intent reference only
- `Browser Use` and `Computer Use`: optional only if visual evidence becomes
  necessary; not expected for this token-only slice
- `Canva`, `Build macOS Apps`, `Cloudflare`, `Netlify`, `Expo`, `Life Science
  Research`, and `Remotion`: not used in `PR-3`

## Implementation Contract

- create `tokens/20_product/color.json` as the only new product-token authoring
  source in this slice
- keep product tokens as semantic aliases over the existing foundation and base
  semantic palette
- use stable product-family names that can be consumed later by PR-4 and PR-5
  without requiring screen migration in this PR
- emit web CSS variables with the `--product-color-<family>-<role>` prefix
- emit a typed TS mirror as `productColors`
- emit a generated Swift product color namespace without changing iOS screens
  or the stable public iOS facade
- preserve deterministic generation and do not hand-edit generated files after
  regeneration

## Validation Bundle

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `make tokens-check`
- `python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json`
- `cd frontend && npm run tokens:check`
- `cd frontend && npm run build`
- `pre-commit run --all-files`
- `make verify` before any merge-ready claim on the latest head

## Review Path

- keep PR `#1519` in review governance until all blockers are dispositioned
- create canonical artifact `docs/review/PR_1519_FIXED_MAPPING.md`
- sync the PR body mirror after review dispositions
- use GitHub current-head truth plus CodeRabbit/Sourcery review input; do not
  rely on stale historical runs

## Merge Path

- keep the lane in draft while current-head `main` or PR checks are pending
- move the lane to `post_open_review` after draft PR creation
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
  - remove only `worktrees/design-runtime-system-pr3`, the local branch
    `codex/design-product-token-expansion`, and slice-local temp artifacts
  - run `git worktree prune`

## DoD

- product color token layer exists under `/tokens`
- web CSS mirror includes generated `--product-*` variables
- TS mirror exposes generated `productColors`
- generated Swift mirror exposes product color tokens
- token parity tests cover source-to-runtime product-token mirrors
- token governance docs describe product-token activation
- backlog anchor records PR-2 merged and PR-3 active
- no product screen, iOS adoption, Figma manifest, backend, billing, or deploy
  scope was introduced
