# Token Pipeline Governance

<!-- markdownlint-disable MD013 -->

This document is the governance source for the PulsePlate design-token
pipeline.

Use it with:

- `docs/design/TOKENS_SOT.md`
- `docs/design/COLOR_PROFILE_GOVERNANCE.md`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
- `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
- `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md`

## 1. Purpose

Define one repo-grounded token pipeline so design authoring, runtime code, and
review tooling do not drift into competing sources of truth.

## 2. Source precedence

1. Repo code, docs, and tests remain the final project SoT.
2. `docs/design/TOKENS_SOT.md` defines canonical token ownership.
3. `/tokens` is the canonical repo authoring source for design tokens.
4. `Figma Design` is the canonical design-intent lane for token decisions.
5. `Tokens Studio` is allowed only as subordinate tooling inside the Figma
   lane.
6. Storybook is a review/documentation lane for implemented web components.

Hard rule: no tool outside repo runtime artifacts may override token behavior in
shipped web or iOS surfaces without reviewed promotion into git.

## 3. Authoring/runtime split

### Authoring layer

- Primary repo authoring surface: `/tokens`
- Upstream design-intent inputs: approved Figma design files
- Optional subordinate tool: Tokens Studio inside that Figma lane
- Allowed upstream outputs: draft token sets, token grouping proposals, export
  previews, audit diffs

### Runtime layer

- Web runtime SoT: `frontend/src/styles/tokens.css`
- Web typed mirror/helper: `frontend/src/styles/tokens.ts`
- iOS generated mirror: `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
- iOS runtime mirror: `ios/PulsePlate/DesignSystem/DesignTokens.swift`
- iOS asset-backed color bridge:
  - `ios/PulsePlate/Assets.xcassets/`
  - `ios/PulsePlate/Extensions/Color+Assets.swift`

### Review layer

- Storybook scripts in `frontend/package.json`
- Story files under `frontend/src/**/*.stories.tsx`
- HPP token guidance doc: `frontend/src/stories/HppTokenGuidelines.mdx`

Review tooling validates implemented consumers. It does not define token canon.

Color-profile rule:

- Token artifacts define semantic color meaning and runtime ownership.
- `docs/design/COLOR_PROFILE_GOVERNANCE.md` defines the runtime/export profile
  baseline (`sRGB`) and the optional `Display P3` asset lane above this token
  pipeline.

## 4. Artifact roles

| Artifact | Role | Governance meaning |
| --- | --- | --- |
| `/tokens/**` | Repo authoring source | Canonical promoted token inputs |
| `frontend/src/styles/tokens.css` | Web runtime token contract | Canonical shipped token values for web |
| `frontend/src/styles/tokens.ts` | Typed mirror/helper | Must mirror runtime intent; loses on conflict |
| `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift` | Generated iOS mirror | Machine-written Swift token payload |
| `ios/PulsePlate/DesignSystem/DesignTokens.swift` | iOS token mirror | Canonical Swift token grouping for app surfaces |
| `ios/PulsePlate/Assets.xcassets/` + `Color+Assets.swift` | iOS runtime color bridge | Asset-backed color delivery and semantic lookup |
| `docs/design/figma-manifest.json` | Informational bootstrap manifest | Not a canonical schema contract today |
| Storybook scripts/stories | Review lane | Visual validation and documentation only |

## 5. Governed pipeline

1. Open a design/task packet with the target surface and token scope.
2. Author the token change in Figma.
3. If helpful, use Tokens Studio inside the same Figma lane to organize token
   sets or generate draft exports.
4. Promote the approved token decision into `/tokens`.
5. Generate runtime mirrors from `/tokens`.
6. Verify the implementation in Storybook and/or platform-specific tests.
7. If the work is partial, record the remainder in
   `docs/roadmap/BACKLOG_LEDGER.md`.

This is the active PulsePlate token pipeline. It is governed and promotion-based
rather than a fully automated export/import chain.

## 6. Change classes

### Foundation tokens

Examples: brand colors, spacing scale, radius, typography primitives, elevation.

Requirements:

- Update runtime SoT/mirrors
- Update `docs/design/TOKENS_SOT.md` when token meaning changes
- Re-check web/iOS parity if the change crosses platforms

### Semantic tokens

Examples: `surface`, `text`, `success`, `warning`, premium accents.

Requirements:

- Keep semantic names stable across Figma intent and runtime implementation
- Update Storybook consumers or review surfaces when the change is user-visible

### Product tokens

Examples: screen-, feature-, or tier-specific aliases.

Current status:

- Product-token expansion is not fully activated yet.
- Any new product-token layer that goes beyond current base semantic/runtime
  tokens must be tracked in the backlog if not completed in the same task.

## 7. Tokens Studio policy

- Allowed: authoring support within approved Figma files
- Not allowed: treating Tokens Studio JSON/export as a deployed runtime contract
  without promotion into `/tokens`
- Not allowed: introducing a second schema registry that silently competes with
  `/tokens`, `tokens.css`, or iOS runtime mirrors

If Tokens Studio activation expands beyond authoring support, the activation
scope, export format, validation path, and owner must be documented first.

## 8. Storybook policy

- Storybook exists in this repo and is part of the web review lane.
- Storybook stories may validate token consumption, state coverage, and visual
  regressions for primitives and page shells.
- Storybook does not replace Figma as authoring lane and does not replace
  runtime token files as SoT.

## 9. Figma manifest policy

`docs/design/figma-manifest.json` currently points to the web runtime token
source and can be used as a bootstrap reference.

Current rule:

- Do not treat `figma-manifest.json` as the governing pipeline schema.
- Optional schema unification with token pipeline governance is deferred until
  explicitly activated and tracked.

## 10. Related docs

- `docs/design/TOKENS_SOT.md`
- `docs/design/COLOR_PROFILE_GOVERNANCE.md`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
- `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
- `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md`
- `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
