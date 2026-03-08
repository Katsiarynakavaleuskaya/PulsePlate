# PR 1047 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902379824 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `frontend/scripts/build-tokens.mjs` now regenerates destructive compatibility aliases consumed by `frontend/src/components/ui/Button.tsx:19`; see generated output in `frontend/src/styles/tokens.css`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902381889 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `Makefile` `tokens-check` now preserves failure status instead of masking errors behind shell chaining.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902381895 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `frontend/src/styles/tokens.css` again contains `--color-destructive-*` and `--shadow-destructive` after generator rebuild.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902381896 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md` refresh commands now include `/tokens` and `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902381897 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `tests/test_design_token_parity.py` now snapshots both consecutive runs and asserts determinism across `before`, `run1`, and `run2`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902381901 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md` hard-rule range now targets tools `4-7`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902381902 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md` now points to `frontend/src/assets/brand/` as the canonical brand-asset folder.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385558 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `docs/design/TOKENS_SOT.md` section renamed to `Build and runtime lane` so `/tokens/*` is no longer presented as runtime-only output.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385559 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: deferred token-expansion item moved under `docs/roadmap/BACKLOG_LEDGER.md` `## Open Items` → `### P1` with anchor `ledger-p1-token-expansion-activation`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385562 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md` now instructs contributors to change `/tokens` first and regenerate `tokens.css`/`tokens.ts`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385563 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `frontend/scripts/build-tokens.mjs` `--check` mode now fails on stale committed mirrors and separately verifies second-run determinism.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385564 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `tests/test_design_token_parity.py` resolves `node` via `shutil.which(...)` and skips determinism only when the frontend toolchain is absent in Python-only jobs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385565 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `tokens/00_core/radius.json` now uses unit-bearing `0px` for `radius.none`; generated web mirror updated accordingly.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047#discussion_r2902385568 -> a5adeaa7
  - Disposition: FIXED
  - Evidence: `tokens/30_platform/web.json` now maps `radiusXl` to `var(--radius-xl)` so the generated `--pp-radius-xl` alias references the canonical radius token without self-reference recursion.
