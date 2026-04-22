# Design Runtime System Web+iOS PR Series Runbook

**Version:** 2026-04-22 (`America/New_York`)
**Scope:** Coordinator-first design runtime system series launched from synced
`origin/main` after the merged design-runtime and design-bridge baselines.
**Execution surface:** One dedicated worktree per PR from synced `origin/main`
(`worktrees/design-runtime-system-pr*` or equivalent).

## Purpose

This runbook is the canonical operating contract for the design runtime system
web+iOS epic line.

This line is downstream of the merged repo baselines and must not reopen them:
- design-agent runtime baseline / realignment bridge on `main`
- design-bridge operationalization baseline on `main`
- post-bridge UI execution baseline on `main`

This runbook adds one new coordinator-owned PR train that closes the remaining
design-system productization gaps without creating a second source of truth,
without widening backend/UI contracts, and without consuming reserved future
design-agent slots.

Overlapping product surfaces already sequenced by the post-bridge UI epic stay
owned by that lane unless a later packet or ledger update records an explicit
handoff or supersede decision.

## Contract Boundaries

### IN
- coordinator-first PR train governance for the design runtime system web+iOS
  epic
- one docs-only bootstrap slice (`PR-0`) for runbook, packet, backlog anchor,
  role order, validation matrix, merge path, and cleanup path
- governed missing primitive completion for web runtime slices
- normalization of specialized-existing families into shared governed patterns
- product-token expansion through `/tokens -> generated runtime mirrors`
- bounded web shell convergence on governed tokens and primitives after any
  overlapping UI-epic ownership is explicitly transferred
- bounded iOS adoption on generated tokens and shared design grammar after any
  overlapping UI-epic ownership is explicitly transferred
- accessibility / state / motion contract work for critical web+iOS flows
- future export-lock hardening for `docs/design/figma-manifest.json`
- future Storybook parity expansion as a review surface only

### OUT
- reopening merged design-runtime realignment or bridge-closeout work
- Figma writes, pushes, or execution authority in this bootstrap slice
- Tokens Studio export automation or schema-registry promotion
- full `figma-manifest` schema unification in this wave
- backend, OpenAPI, contract, billing, entitlement, pricing, or provider
  modernization changes
- Cloudflare preview or deploy as merge truth
- Liquid Glass migration claims
- new `/api/v1/ui/state` or any second backend UI rail
- reopening or overtaking UI-epic-owned `Home`, `Plate`, `Progress`,
  `Weekly Plan`, `Profile`, or `Paywall` surfaces without an explicit
  handoff/supersede packet
- implementation work for later PR slices hidden inside `PR-0`

## Source Of Truth

- Coordinator workflow: `docs/orchestration/workflow.md`
- PR governance contract: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
- Design tooling source precedence:
  `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
- Token governance:
  `docs/design/TOKENS_SOT.md`,
  `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- UI vocabulary contract:
  `docs/design/UI_COMPONENT_VOCABULARY.md`
- Code-native design runtime:
  `docs/design/CODE_NATIVE_DESIGN_RUNTIME.md`
- Docs-only PR policy:
  `docs/policy/DOCS_ONLY_PR_POLICY.md`
- Worktree isolation policy:
  `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`
- Existing UI/bridge baselines for coexistence only:
  `docs/orchestration/UI_EPIC_PR_SERIES_RUNBOOK.md`,
  `docs/orchestration/DESIGN_BRIDGE_OPERATIONALIZATION_PACKET_2026-04-11.md`,
  `docs/design/DESIGN_AGENT_RUNTIME_PR_CHAIN.md`
- Deferred / follow-on tracking:
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-runtime-system-web-ios-epic`

## Design Source Precedence

The full source-precedence ladder for this series is fixed as a general
governance ladder:

1. `repo/docs/tests/code`
2. code-native design runtime
3. `Figma Design + Code Connect` secondary lane
4. `/tokens` authoring source
5. Storybook review-only lane
6. external/reference tools in `read_only`

Hard rules:
- `/tokens` remains the canonical authoring source for design tokens.
- For design-token conflicts, `/tokens` authoring plus
  `frontend/src/styles/tokens.css` as the web runtime token SoT override
  code-native design runtime, `Figma Design + Code Connect`, Storybook
  review-only surfaces, and external/reference tools even though the general
  governance ladder still lists those lanes separately.
- `frontend/src/styles/tokens.css` remains the web runtime token SoT.
- `frontend/src/styles/tokens.ts` is a typed mirror and loses on conflict.
- `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift` and
  `ios/PulsePlate/DesignSystem/DesignTokens.swift` remain derived runtime
  mirrors, not authoring sources.
- Storybook validates implemented consumers only. It does not author tokens,
  replace Figma as design intent, or replace runtime token files as SoT.
- `docs/design/figma-manifest.json` stays bootstrap metadata until the dedicated
  export-lock slice hardens it; it is not merge truth or schema canon in
  `PR-0`.

## Review Surfaces And Evidence

- `PR-0` is docs-only. Its evidence is repo-artifact validation, governance
  review, and current-head PR truth only. Screenshots, Figma frames, and
  product-route demos are non-governing for this bootstrap slice.
- Later web implementation slices are Storybook-first review only.
- Later iOS implementation slices are simulator-first.
- Product routes remain implementation mirrors, not design canon.

## Figma Metadata Rule

Any future Figma-backed slice must fail closed until its active packet records:
- `design_source`
- `source_url`
- `file_key_or_workspace`
- `node_id_or_frame_id`
- `target_surface`
- `task_mode`
- required `code_native_design_brief_path`

If any required metadata is missing, the lane remains `read_only`.

## Downstream Ownership Rule

- `docs/orchestration/UI_EPIC_PR_SERIES_RUNBOOK.md` retains ownership of the
  post-bridge UI surfaces and ordering it already sequences.
- This train may extend design-system governance beneath those surfaces, but it
  must not reopen or reorder the UI epic's active scope by implication.
- Any later slice that touches overlapping `Home`, `Plate`, `Progress`,
  `Weekly Plan`, `Profile`, or `Paywall` surfaces must first record one of:
  - explicit handoff from the UI epic line
  - explicit supersede decision in a later packet
  - carve-out that narrows the slice to non-overlapping shell/token work only

## PR Series

### PR-0: Bootstrap governance slice

- Branch: `codex/design-runtime-system-v1-packet`
- Title: `docs(design): add coordinator-first design runtime system web-ios runbook`
- Scope:
  - add this runbook
  - add the branch-scoped bootstrap packet
  - add one explicit backlog anchor for the series
  - freeze PR order, role order, source precedence, validation, merge path, and
    cleanup path

### PR-1: Missing governed primitives

- Branch: `codex/design-missing-primitives-v1`
- Scope:
  - `select`
  - `textarea`
  - `checkbox`
  - `radio-group`
  - `alert`
  - `dropdown-menu`
  - `tabs`
  - `tooltip`

### PR-2: Specialized family normalization

- Branch: `codex/design-specialized-families-normalization`
- Scope:
  - normalize `badge`, `progress`, `hero`, `stats-card`,
    `stepper/progress-indicator`
  - keep current product consumers stable through thin adapters where needed

### PR-3: Product token expansion

- Branch: `codex/design-product-token-expansion`
- Scope:
  - add product token layer for paywall, premium, plate, progress, plan,
    coaching, and status/feedback
  - regenerate web+iOS runtime mirrors

### PR-4: Web shell convergence

- Branch: `codex/frontend-product-shell-convergence`
- Scope:
  - converge shared web shell anatomy onto governed primitives/tokens
  - stay downstream of the UI epic line for any overlapping `Home`, Nutrition
    Setup / Plate, Progress, Weekly Plan, Profile / Settings, and Paywall
    surfaces
  - require an explicit handoff/supersede record before claiming ownership of
    those overlapping product screens

### PR-5: iOS design-system adoption

- Branch: `codex/ios-design-system-adoption-v1`
- Scope:
  - adopt generated design tokens and shared patterns on bounded core screens
  - stay downstream of the UI epic's iOS coherence and semantic-surface slices
    for any overlapping `Home`, `Plate`, and `Progress` ownership
  - require an explicit handoff/supersede record before claiming those iOS
    product surfaces

### PR-6: Accessibility / motion / state contract

- Branch: `codex/design-accessibility-motion-state-contract`
- Scope:
  - empty/loading/error states
  - focus / keyboard
  - reduced motion
  - touch targets
  - non-color-only semantics

### PR-7: Export lock and manifest hardening

- Branch: `codex/design-export-lock-and-manifest-hardening`
- Scope:
  - move `docs/design/figma-manifest.json` from `bootstrap` to `locked`
  - lock the governed export set only

### PR-8: Storybook parity

- Branch: `codex/storybook-design-review-parity`
- Scope:
  - expand Storybook so core primitives, states, and product review surfaces are
    visible as implemented review-only surfaces

## Routing Card

- Decision question: How should PulsePlate execute a coordinator-first design
  runtime system train without reopening merged design-bridge/runtime baselines
  or widening product/backend scope?
- Primary agent: `agent-coordinator`
- Default role order:
  1. `agent-coordinator`
  2. `creative-designer`
  3. `frontend-engineer`
  4. advisory `cursor-specialist-agent`
  5. reviewer `architecture-specialist`
  6. mandatory post-open `qa-engineer-agent -> bug-hunter`
- iOS-bearing implementation slices must additionally load the relevant
  `build-ios-apps:*` skills and carry simulator evidence, but that does not
  replace the canonical repo-agent role order.

## Sync Points

1. **Bootstrap locked**
   - runbook merged
   - packet merged
   - backlog anchor merged
   - PR order, role order, and boundaries fixed
2. **Primitives locked**
   - missing governed primitives exist with stories/tests/a11y
3. **Families locked**
   - specialized families normalize without consumer drift
4. **Tokens locked**
   - product token layer regenerates deterministic web+iOS mirrors
5. **Shells locked**
   - bounded product shells converge on governed primitives/tokens
6. **Cross-platform contract locked**
   - iOS adoption plus a11y/state/motion slices stabilize
7. **Export lock locked**
   - manifest hardening lands without schema-canon widening
8. **Review parity locked**
   - Storybook surfaces cover implemented review-only system

## Hard Rules

- One PR equals one dedicated worktree from synced `origin/main`.
- Do not edit the dirty root tree.
- Do not reuse colleague worktrees or branches.
- Do not replace the declared role order with an ad hoc internal role stack.
- The canonical post-open lane remains `qa-engineer-agent -> bug-hunter`.
- Web stays renderer-only and must not open a second UI/API rail.
- No direct `fetch()` outside `frontend/src/api/client.ts`.
- No business logic migration into web or iOS under design/runtime wording.
- No raw hex in runtime consumers outside the documented allowlist.
- No Figma write/push authority in `PR-0`.
- No Cloudflare merge truth in this line.
- No design-bridge/runtime baseline reopen without a separate bounded packet.
- `design-agent PR4` remains reserved and unconsumed by this train.

## Validation Matrix

Every PR in this series runs:
- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make verify`

`PR-0` additionally remains docs-only and must satisfy:

```bash
git diff --name-only origin/main...HEAD \
  | rg -v "\\.md$|README\\.md$|AGENTS\\.md$|RUNBOOK_AGENT\\.md$|DEPLOYMENT\\.md$"
```

Expected result: empty output.

`PR-1`, `PR-2`, `PR-4`, and `PR-8` additionally run:
- `cd frontend && npm run build`
- `cd frontend && npm run build-storybook` where Storybook surface changes
- relevant frontend tests

`PR-3` additionally runs:
- token regeneration determinism checks
- `make tokens-check`
- `python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json`

`PR-5` and `PR-6` additionally run:
- targeted iOS xcodebuild / simulator validation
- any relevant shared web checks when cross-platform surfaces move together

`PR-7` additionally runs:
- locked-state manifest checks
- export integrity validation via `scripts/design_guard.py`

## Merge And Cleanup

Before any merge-ready claim:
- current-head checks only
- zero unresolved review threads
- canonical review artifact up-to-date
- PR body mirror aligned after artifact updates
- strict merge wrapper passes

After merge:
1. `git checkout main`
2. `git fetch --prune origin`
3. `git merge --ff-only origin/main`
4. verify current-head `main` health
5. verify PR state is `MERGED`
6. delete only the finished slice branch / worktree / temporary artifacts
7. `git worktree prune`
8. only then open the next slice from synced `origin/main`
