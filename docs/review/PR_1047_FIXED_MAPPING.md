# PR 1047 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902379824 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `frontend/scripts/build-tokens.mjs` now regenerates destructive compatibility aliases consumed by `frontend/src/components/ui/Button.tsx:19`; see generated output in `frontend/src/styles/tokens.css`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902381889 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `Makefile` `tokens-check` now preserves failure status instead of masking errors behind shell chaining.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902381895 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `frontend/src/styles/tokens.css` again contains `--color-destructive-*` and `--shadow-destructive` after generator rebuild.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902381896 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md` refresh commands now include `/tokens` and `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902381897 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `tests/test_design_token_parity.py` now snapshots both consecutive runs and asserts determinism across `before`, `run1`, and `run2`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902381901 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md` hard-rule range now targets tools `4-7`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902381902 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md` now points to `frontend/src/assets/brand/` as the canonical brand-asset folder.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385558 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `docs/design/TOKENS_SOT.md` section renamed to `Build and runtime lane` so `/tokens/*` is no longer presented as runtime-only output.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385559 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: deferred token-expansion item moved under `docs/roadmap/BACKLOG_LEDGER.md` `## Open Items` → `### P1` with anchor `ledger-p1-token-expansion-activation`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385562 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md` now instructs contributors to change `/tokens` first and regenerate `tokens.css`/`tokens.ts`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385563 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `frontend/scripts/build-tokens.mjs` `--check` mode now fails on stale committed mirrors and separately verifies second-run determinism.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385564 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `tests/test_design_token_parity.py` resolves `node` via `shutil.which(...)` and skips determinism only when the frontend toolchain is absent in Python-only jobs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385565 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `tokens/00_core/radius.json` now uses unit-bearing `0px` for `radius.none`; generated web mirror updated accordingly.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385568 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: `tokens/30_platform/web.json` now maps `radiusXl` to `var(--radius-xl)` so the generated `--pp-radius-xl` alias references the canonical radius token without self-reference recursion.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#pullrequestreview-3911994492 -> a5adeaa7
Disposition: FIXED
Commit: a5adeaa7
Evidence: Cubic's summary review aggregates the concrete findings already fixed in `a5adeaa7` across `Makefile`, `frontend/scripts/build-tokens.mjs`, `tests/test_design_token_parity.py`, `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`, `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`, and `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#pullrequestreview-3911997283
Disposition: NOT-A-BUG
Evidence: `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md:126` already directs web token edits to `/tokens`; `.github/workflows/ci.yml:17` already includes `pull_request.types` with `edited` for the governance workflow that reruns PR-body gates; `.github/workflows/ci.yml:340` already runs `tests/test_openapi_determinism.py`.
Reason: This CodeRabbit review object is an aggregate summary over inline/outside-diff findings, not an additional unresolved issue; fixed findings are mapped above and remaining notes are optional nits or already-satisfied contracts.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902462078 -> 04df1621
Disposition: FIXED
Commit: 04df1621
Evidence: `docs/design/TOKENS_SOT.md` now anchors canonical claims with direct repo evidence, including `/tokens`, generated web mirrors, Storybook review lane, iOS mirrors, and `figma-manifest.json`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902462080 -> 04df1621
Disposition: FIXED
Commit: 04df1621
Evidence: `frontend/src/styles/__tests__/tokens.test.ts` now resolves the CSS fixture path through `fileURLToPath(new NodeURL(..., import.meta.url))`, removing the invalid `__dirname` pattern in Vitest ESM tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902462083 -> 04df1621
Disposition: FIXED
Commit: 04df1621
Evidence: `frontend/scripts/build-tokens.mjs` now emits a blank line before `accent-color`, and regenerated `frontend/src/styles/tokens.css` includes the stylelint-clean separation between breakpoint vars and the native control declaration.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#pullrequestreview-3912061781 -> 04df1621
Disposition: FIXED
Commit: 04df1621
Evidence: `04df1621` fixes every actionable item from this aggregate CodeRabbit review: evidence anchors in `docs/design/TOKENS_SOT.md`, ESM-safe fixture loading in `frontend/src/styles/__tests__/tokens.test.ts`, generator-owned blank-line output in `frontend/scripts/build-tokens.mjs`/`frontend/src/styles/tokens.css`, and `pull_request.types` with `edited` in `.github/workflows/frontend-ci.yml`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902473949 -> 24f2f375
Disposition: FIXED
Commit: 24f2f375
Evidence: `docs/design/TOKENS_SOT.md` now explicitly delegates authoritative web token governance (SoT, staged migration, raw-hex allowlists) to `docs/sora/SORA_STYLE_QA_CHECKLIST.md:8-14` and keeps this file as an implementation-summary/runtime-mirror reference.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902473951 -> 24f2f375
Disposition: FIXED
Commit: 24f2f375
Evidence: `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md` precedence rule 4 now names `docs/sora/SORA_STYLE_QA_CHECKLIST.md` as authoritative for web token governance while preserving the current `tokens.css`/`tokens.ts`/iOS runtime-contract split.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902473952 -> 24f2f375
Disposition: FIXED
Commit: 24f2f375
Evidence: `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md` now adds direct `file:line` evidence anchors for `/tokens`, `Tokens Studio`, `Notion`, `Airweave`, `Penpot`, plus the token authoring/runtime split and review lane assertions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902473953 -> 24f2f375
Disposition: FIXED
Commit: 24f2f375
Evidence: `Makefile` `tokens-check` now runs the diff gate, `design_guard.py`, and parity pytest in a single shell sequence with `&&` short-circuiting and an `EXIT` trap that always cleans the temp diff files.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902473955 -> 24f2f375
Disposition: FIXED
Commit: 24f2f375
Evidence: `frontend/scripts/build-tokens.mjs` now builds the full public iOS semantic surface from token sources/platform tokens, and `tests/test_design_token_parity.py` validates every public semantic token exported through `ios/PulsePlate/DesignSystem/DesignTokens.swift` instead of only the four status colors.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#pullrequestreview-3912070621 -> 24f2f375
Disposition: FIXED
Commit: 24f2f375
Evidence: `24f2f375` fixes the aggregate CodeRabbit wave from `2026-03-08T21:48:36Z`: delegated token-governance authority in `docs/design/TOKENS_SOT.md`, authoritative SORA checklist precedence in `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`, evidence-backed source-precedence rules in `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`, a single-shell `tokens-check` flow in `Makefile`, and expanded public semantic parity coverage in `tests/test_design_token_parity.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902481694 -> a71a4659
Disposition: FIXED
Commit: a71a4659
Evidence: `docs/review/PR_1047_FIXED_MAPPING.md` now includes the required `## Merge Readiness` heading and checklist after the fixed-mapping section, satisfying the canonical artifact contract raised in the inline review comment.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#pullrequestreview-3912077481 -> a71a4659
Disposition: FIXED
Commit: a71a4659
Evidence: The only actionable item in this aggregate CodeRabbit review was the missing `## Merge Readiness` section in `docs/review/PR_1047_FIXED_MAPPING.md`, fixed by `a71a4659`; the remaining suggestions in that review are non-blocking nitpicks.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902496104 -> 79673954
Disposition: FIXED
Commit: 79673954
Evidence: `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md` now moves `docs/sora/SORA_STYLE_QA_CHECKLIST.md` ahead of `docs/design/TOKENS_SOT.md` and `docs/design/TOKEN_PIPELINE_GOVERNANCE.md` in the required reading order so the authoritative web-token governance doc is read first.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902496106 -> 79673954
Disposition: FIXED
Commit: 79673954
Evidence: `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md` now includes `docs/sora/SORA_STYLE_QA_CHECKLIST.md` in the token source-contract section and explicitly marks it as authoritative for token SoT, staged migration, and raw-hex allowlist rules.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#pullrequestreview-3912089482 -> 79673954
Disposition: FIXED
Commit: 79673954
Evidence: `79673954` fixes the two actionable doc-precedence findings from this aggregate CodeRabbit review by reordering the Figma runbook reading list and adding the SORA checklist to the token source-contract section; the duplicate merge-readiness note was already satisfied by `a71a4659`, and the remaining suggestions are non-blocking nitpicks.

## Merge Readiness
- [ ] All required checks are PASS
- [x] Fixed in Commit Mapping artifact updated
- [ ] No unresolved review threads remain
- [ ] No actionable bot comments remain
- [ ] Final wait-cycle completed after latest review/bot activity
