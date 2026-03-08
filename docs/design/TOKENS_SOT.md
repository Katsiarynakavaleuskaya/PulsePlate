# Tokens Source Of Truth

This document defines the canonical split between token authoring and runtime
for PulsePlate.

Policy references:

- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`

## Canonical split

### 1. Authoring lane

- Repo token authoring source: `/tokens`
- `Figma Design` remains the canonical design-intent lane for token decisions.
- `Tokens Studio` is approved only as subordinate tooling inside the Figma lane
  for drafting, grouping, or exporting token sets that are later promoted into
  `/tokens`.
- Tokens Studio does not create a separate source-precedence lane and does not
  override repo runtime artifacts on its own.

### 2. Runtime lane

- Repo token authoring tree:
  - `tokens/00_core/`
  - `tokens/10_semantic/`
  - `tokens/30_platform/`
- Web runtime token SoT: `frontend/src/styles/tokens.css`
- Web typed mirror: `frontend/src/styles/tokens.ts`
- iOS runtime mirror stack:
  - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
  - `ios/PulsePlate/DesignSystem/DesignTokens.swift`
  - `ios/PulsePlate/Assets.xcassets/`
  - `ios/PulsePlate/Extensions/Color+Assets.swift`

If a token meaning or value conflicts between authoring notes and runtime code,
the repo runtime artifacts win until a reviewed promotion changes them.

### 3. Review lane

- Storybook in `frontend/package.json` and `frontend/src/**/*.stories.tsx`
  exists as the web implementation review/documentation lane.
- Storybook is not the token authoring lane and not a replacement SoT for
  runtime tokens.

## Current token scope

### Foundation and base semantic tokens

- `TOKEN_SOT`: `frontend/src/styles/tokens.css`
- `GOLD`: approved as premium/accent semantic token

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
  consumers, parity checks, and implementation ergonomics.
- `frontend/tailwind.config.ts` consumes runtime token intent and must not be
  treated as an authoring source.
- `docs/design/figma-manifest.json` is currently an informative bootstrap
  artifact, not the canonical runtime schema.

## Active pipeline

The governed token pipeline is:

1. Capture or revise token intent in the design lane (`Figma Design`,
   optionally `Tokens Studio`)
2. Promote the approved token change into `/tokens`
3. Build runtime mirrors from `/tokens`
4. Verify runtime parity in implementation/review lanes (`Storybook`, tests,
   platform mirrors)

This means PulsePlate does have a token pipeline today, but it is a governed
promotion pipeline rather than an autonomous bi-directional sync system.

## Migration policy

- PR-1 (bridge): introduce canonical `--pp-*` brand tokens and keep legacy
  aliases.
- PR-2 (palette switch): update canonical token values to Guidelines palette.
- PR-3 (guard): ban raw hex in frontend runtime paths with explicit allowlist.

Legacy aliases are kept only for soft migration and should not be used in new
code:

- `--pp-primary` -> `--pp-blue`
- `--pp-accent` -> `--pp-green`

## Hard rules

- Do not treat `tokens.ts`, Storybook stories, or Tailwind config as the web
  token SoT.
- Do not treat Figma or Tokens Studio exports as active runtime contract until
  the change is promoted into `/tokens` and generated into runtime artifacts.
- Do not introduce a second hidden token schema without updating
  `docs/design/TOKEN_PIPELINE_GOVERNANCE.md` and the backlog when work is
  deferred.
