# Tokens Source Of Truth

This document is the implementation summary for the current token pipeline in
PulsePlate. Authoritative web token governance for token SoT, staged migration,
and raw-hex allowlist rules lives in `docs/sora/SORA_STYLE_QA_CHECKLIST.md:8`
through `docs/sora/SORA_STYLE_QA_CHECKLIST.md:14`; this file summarizes how the
current repo/runtime mirrors implement that policy.

Policy references:

- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`

## Canonical split

### 1. Authoring lane

- Repo token authoring source: `/tokens` (`frontend/style-dictionary.config.mjs:9`, `frontend/style-dictionary.config.mjs:11`, `tokens/00_core/color.json:1`, `tokens/10_semantic/color.json:1`, `tokens/30_platform/web.json:1`)
- `Figma Design` remains the canonical design-intent lane for token decisions (`docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:15`).
- `Tokens Studio` is approved only as subordinate tooling inside the Figma lane
  for drafting, grouping, or exporting token sets that are later promoted into
  `/tokens` (`docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:16`, `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:18`).
- Tokens Studio does not create a separate source-precedence lane and does not
  override repo runtime artifacts on its own (`docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:23`, `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:24`).

### 2. Build and runtime lane

- Runtime mirrors are generated from:
  - `tokens/00_core/`
  - `tokens/10_semantic/`
  - `tokens/30_platform/`
- Web runtime token SoT: `frontend/src/styles/tokens.css` (`frontend/scripts/build-tokens.mjs:744`, `frontend/src/styles/tokens.css:1`, `frontend/src/styles/tokens.css:7`)
- Web typed mirror: `frontend/src/styles/tokens.ts` (`frontend/scripts/build-tokens.mjs:748`, `frontend/src/styles/tokens.ts:1`, `frontend/src/styles/tokens.ts:7`)
- iOS runtime mirror stack:
  - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift` (`frontend/scripts/build-tokens.mjs:752`, `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift:3`, `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift:5`)
  - `ios/PulsePlate/DesignSystem/DesignTokens.swift` (`ios/PulsePlate/DesignSystem/DesignTokens.swift:3`, `ios/PulsePlate/DesignSystem/DesignTokens.swift:5`)
  - `ios/PulsePlate/Assets.xcassets/` (`ios/PulsePlate/Assets.xcassets/Navy.colorset/Contents.json:1`)
  - `ios/PulsePlate/Extensions/Color+Assets.swift` (`ios/PulsePlate/Extensions/Color+Assets.swift:4`, `ios/PulsePlate/Extensions/Color+Assets.swift:14`)

If a token meaning or value conflicts between authoring notes and runtime code,
the repo runtime artifacts win until a reviewed promotion changes them (`frontend/src/styles/tokens.css:1`, `frontend/src/styles/tokens.css:7`, `ios/PulsePlate/DesignSystem/DesignTokens.swift:3`, `ios/PulsePlate/DesignSystem/DesignTokens.swift:5`).

### 3. Review lane

- Storybook in `frontend/package.json` and `frontend/src/**/*.stories.tsx`
  exists as the web implementation review/documentation lane (`frontend/package.json:14`, `frontend/package.json:15`, `frontend/src/components/design-system/DesignSystemOverview.stories.tsx:1`).
- Storybook is not the token authoring lane and not a replacement SoT for
  runtime tokens (`frontend/package.json:12`, `frontend/package.json:14`, `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:37`, `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:46`).

## Current token scope

### Foundation and base semantic tokens

- Web runtime contract currently resolves through `frontend/src/styles/tokens.css`
  as implemented output (`frontend/src/styles/tokens.css:73`, `frontend/src/styles/tokens.css:95`); the authoritative web-governance statement remains `docs/sora/SORA_STYLE_QA_CHECKLIST.md:8`.
- `GOLD` remains part of the approved runtime palette as generated brand output
  (`frontend/src/styles/tokens.css:14`, `frontend/src/styles/tokens.ts:6`).

Canonical brand tokens:

- `--pp-navy`
- `--pp-blue`
- `--pp-green`
- `--pp-red`
- `--pp-gold`

Base semantic runtime tokens currently live in `tokens.css`, including:

- `--color-primary`
- `--color-surface`
- `--color-border`
- `--color-text`
- `--color-success`
- `--color-warning`
- `--color-error`
- `--color-info`

### Derived helpers

- `frontend/src/styles/tokens.ts` is a typed mirror/helper for TypeScript
  consumers, parity checks, and implementation ergonomics (`frontend/src/styles/tokens.ts:15`, `frontend/src/styles/tokens.ts:24`, `tests/test_design_token_parity.py:255`).
- `frontend/tailwind.config.ts` consumes runtime token intent and must not be
  treated as an authoring source (`frontend/tailwind.config.ts:11`, `frontend/tailwind.config.ts:24`).
- `docs/design/figma-manifest.json` is currently an informative bootstrap
  artifact, not the canonical runtime schema (`docs/design/figma-manifest.json:3`, `docs/design/figma-manifest.json:4`).

## Active pipeline

The governed token pipeline is:

1. Capture or revise token intent in the design lane (`Figma Design`,
   optionally `Tokens Studio`) (`docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:16`, `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:18`)
2. Promote the approved token change into `/tokens` (`frontend/style-dictionary.config.mjs:9`, `frontend/style-dictionary.config.mjs:11`)
3. Build runtime mirrors from `/tokens` (`frontend/scripts/build-tokens.mjs:740`, `frontend/scripts/build-tokens.mjs:746`, `frontend/scripts/build-tokens.mjs:750`, `frontend/scripts/build-tokens.mjs:754`)
4. Verify runtime parity in implementation/review lanes (`Storybook`, tests,
   platform mirrors) (`frontend/package.json:14`, `frontend/package.json:15`, `tests/test_design_token_parity.py:255`, `tests/test_design_token_parity.py:273`)

This means PulsePlate does have a token pipeline today, but it is a governed
promotion pipeline rather than an autonomous bi-directional sync system.

## Governance delegation

For authoritative web token governance, defer to
`docs/sora/SORA_STYLE_QA_CHECKLIST.md:8` through
`docs/sora/SORA_STYLE_QA_CHECKLIST.md:14`.

Legacy aliases remain in runtime output as compatibility shims for the staged
web migration referenced there:

- `--pp-primary` -> `--pp-blue`
- `--pp-accent` -> `--pp-green`

## Implementation reminders

These notes describe the current implementation shape and do not replace the
authoritative web-governance rules in `docs/sora/SORA_STYLE_QA_CHECKLIST.md:8`
through `docs/sora/SORA_STYLE_QA_CHECKLIST.md:14`.

- `tokens.ts`, Storybook stories, and Tailwind config remain mirrors/consumers,
  not the runtime web token contract (`frontend/src/styles/tokens.ts:1`, `frontend/src/styles/tokens.ts:24`, `frontend/src/components/design-system/PalettePanel.stories.tsx:1`, `frontend/src/components/design-system/PalettePanel.stories.tsx:18`, `frontend/tailwind.config.ts:11`, `frontend/tailwind.config.ts:24`).
- Figma and Tokens Studio outputs become runtime only after promotion into
  `/tokens` and regeneration of runtime artifacts (`docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:16`, `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:24`, `frontend/scripts/build-tokens.mjs:740`, `frontend/scripts/build-tokens.mjs:754`).
- Any new token schema or deferred expansion still routes through
  `docs/design/TOKEN_PIPELINE_GOVERNANCE.md` plus the backlog contract
  (`docs/design/TOKEN_PIPELINE_GOVERNANCE.md:15`, `docs/design/TOKEN_PIPELINE_GOVERNANCE.md:24`, `docs/roadmap/BACKLOG_LEDGER.md:121`, `docs/roadmap/BACKLOG_LEDGER.md:122`).
