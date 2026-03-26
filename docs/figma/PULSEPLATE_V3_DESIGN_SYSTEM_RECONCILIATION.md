# PulsePlate_v3 Design System Reconciliation

**Date:** March 26, 2026
**Scope:** `Foundations + Components + Welcome Gate`
**Status:** Canonical file-specific reconciliation packet
**File Identity:** `qJBtE5J6efmavcHCm6SF0O` (`PulsePlate_v3`)
**Clean Canonical Figma File:** `2JDwOByQIbcPgp93FDzHii`
**Clean Canonical Figma URL:** <https://www.figma.com/design/2JDwOByQIbcPgp93FDzHii>

## 1. Purpose

This document is the canonical repo packet for reconciling the existing
`PulsePlate_v3` design file with the PulsePlate repo-native design system.

It exists to prevent three failure modes:

1. treating Figma as a hidden source of truth
2. mixing legacy `H+P+Pr` governance with a new file scope
3. promoting visually strong but contract-breaking prototypes into the runtime lane

This packet governs the first clean-file phase only:

- `00_Foundation_Tokens`
- `01_Components`
- `02_Brand_Assets`
- `10_Welcome_Gate`
- `11_Welcome_Gate_States`
- `90_Audit_Archive`

## 2. File Status Lock

### 2.1 Current `PulsePlate_v3` file is audit/reference only

The current file `qJBtE5J6efmavcHCm6SF0O` is not trusted as the canonical
execution target for this phase.

Reasons:

- public link target `node-id=16:11` resolved through MCP as an empty/invalid
  target and returned a blank screenshot during validation on March 26, 2026
- valid child frames in the same file do resolve, for example `35:148`
  (`PP_iOS_Foundation_Tokens_v1`)
- the file contains useful design intent, but not a stable enough node-level
  structure to serve as the canonical clean build surface

Decision:

- `PulsePlate_v3` stays `audit/reference only`
- the clean file `2JDwOByQIbcPgp93FDzHii` is the execution lane for this phase

### 2.2 Code Connect is explicitly out of scope for Phase 1

Direct Code Connect activation is not required for this package.

For this phase:

- repo-native design system and bridge workflow are primary
- Storybook/component inventory remain the canonical web review lane
- any future Code Connect work must be handled in a separate follow-up packet

## 3. Canonical Source Precedence

Use this precedence order whenever repo, Figma, prompts, or external tools
disagree.

1. repo code, docs, tests, and governance contracts
2. `/tokens`
3. runtime mirrors
   - `frontend/src/styles/tokens.css`
   - `frontend/src/styles/tokens.ts`
   - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
   - `ios/PulsePlate/DesignSystem/DesignTokens.swift`
   - `ios/PulsePlate/Assets.xcassets/`
   - `ios/PulsePlate/Extensions/Color+Assets.swift`
4. Storybook and governed component inventory
5. clean Figma file `2JDwOByQIbcPgp93FDzHii` as design-intent execution lane
6. current `PulsePlate_v3` as audit/reference only
7. FIGR AI as optional read-only ideation lane only

Hard rule:

- if repo and Figma disagree, repo SoT wins until a reviewed promotion changes it

## 4. Primary Repo Sources

### 4.1 Token SoT

- `/tokens`
- `frontend/src/styles/tokens.css`
- `frontend/src/styles/tokens.ts`
- iOS token mirrors listed above
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`

### 4.2 Component SoT

- `frontend/src/components/ui/*`
- `frontend/src/components/design-system/*`
- `frontend/src/components/brand/*`
- `frontend/src/components/cta/*`
- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/design/ui_component_vocabulary.json`
- `frontend/src/stories/PulsePlateDesignSystemGuidelines.mdx`

### 4.3 Visual / Brand SoT

- `docs/sora/VISUAL_GOVERNANCE_INDEX.md`
- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- `docs/design/WELCOME_GATE_VISUAL_PHILOSOPHY.md`
- `docs/sora/prompts/brand_core/FITCHEF_IDENTITY_PROFILE_v1.md`
- `docs/design/FITCHEF_MASCOT_ASSET_CANON.md`

## 5. Transfer Contract

### 5.1 Allowed Figma namespaces

The clean file may only introduce governed names under these namespaces:

- `PP/Brand/*`
- `PP/Scale/*`
- `PP/Semantic/*`
- `PP/Spacing/*`
- `PP/Radius/*`
- `PP/Shadow/*`
- `PP/Motion/*`
- `PP/Shared/*`
- `PP/Web/*`
- `PP/iOS/*`
- `PP/State/*`
- `PP/Branding/*`

### 5.2 Forbidden drift patterns

The following are fail conditions unless explicitly approved and documented as
exceptions:

- unmanaged local colors, effects, text styles, or spacing values
- purple, neon, acid, glossy-blob, or cyberpunk drift
- medical or diagnostic framing
- Figma-only component inventions that bypass repo vocabulary
- local mascot variants not grounded in the repo asset canon
- replacing semantic tokens with hard-coded page-local values
- using FIGR AI output directly without normalization through repo vocabulary/tokens

### 5.3 Naming convention

All Figma components, frames, and variants in the clean file must follow:

- `PP/<Platform>/<Screen>/<Component>/<State>`
- `PP/Shared/<Primitive>/<Variant>`
- `PP/Branding/<Asset>/<Variant>`

### 5.4 No local style invention rule

No new local style may be introduced unless all of the following are true:

1. the value is absent from the current token/component system
2. the need is documented in this packet under `Needs vocabulary decision`
3. the local style is marked temporary and reviewable
4. a follow-up repo promotion path is stated

## 6. Primitive-to-Component Mapping

Use repo primitives first. Do not start with page-level frames.

| Figma lane target | Repo source | Status |
| --- | --- | --- |
| `PP/Shared/Button/*` | `frontend/src/components/ui/Button.tsx` | canonical |
| `PP/Shared/Input/*` | `frontend/src/components/ui/Input.tsx` | canonical |
| `PP/Shared/FormField/*` | `frontend/src/components/ui/FormField.tsx` | canonical |
| `PP/Shared/Card/*` | `frontend/src/components/ui/Card.tsx` | canonical |
| `PP/Shared/Dialog/*` | `frontend/src/components/ui/Dialog.tsx` | canonical |
| `PP/Shared/Toggle/*` | `frontend/src/components/ui/Toggle.tsx` | canonical |
| `PP/Shared/SegmentedControl/*` | `frontend/src/components/ui/SegmentedControl.tsx` | canonical |
| `PP/State/Empty/*` | `frontend/src/components/ui/EmptyState.tsx` | canonical |
| `PP/State/Skeleton/*` | `frontend/src/components/ui/Skeleton.tsx` | canonical |
| `PP/Web/Navigation/TabBar/*` | `frontend/src/components/TabBar.tsx` | canonical |
| `PP/Web/Paywall/PremiumGate/*` | `frontend/src/components/PremiumGate.tsx` | drift in code |
| `PP/Branding/PulsePlateLogo/*` | `frontend/src/components/brand/PulsePlateLogo.tsx` | canonical |
| `PP/Branding/FitChef/*` | `frontend/src/components/brand/FitChefMascot.tsx` + mascot canon docs | canonical |
| `PP/Shared/Select/*` | no governed primitive yet | missing in repo |
| `PP/Shared/Textarea/*` | no governed primitive yet | missing in repo |
| `PP/Shared/Checkbox/*` | no governed primitive yet | missing in repo |
| `PP/Shared/RadioGroup/*` | no governed primitive yet | missing in repo |
| `PP/Shared/Alert/*` | no governed primitive yet | missing in repo |
| `PP/Shared/Tooltip/*` | no governed primitive yet | missing in repo |
| `PP/Shared/StepRail/*` | vocabulary decision required | needs decision |

## 7. Welcome Gate / Pulse Membrane Rules

The `Welcome Gate` pilot screen must inherit the `Pulse Membrane` philosophy as
a system contract, not as a loose moodboard.

Required composition rules:

- rectilinear frames and thin boundary lines must imply passage, not spectacle
- asymmetry may exist only on top of an underlying disciplined grid
- accents are annotations, not dominant fill language
- typography must separate structural headings from whisper-label marginalia
- rhythm is expressed via spacing, steps, ticks, rails, and line-work
- interface must feel restrained, meticulous, and calm rather than dramatic

Fail conditions:

- ornamental decoration with no semantic role
- generic AI blobs or trend-chasing “luxury” treatments
- noisy multi-accent palette behavior
- mascot dominance that competes with the gate decision

## 8. Mascot Provenance Rules

- FitChef assets come from repo canon only
- Figma may place, crop, size, or annotate approved assets
- Figma must not mint new mascot identities or “close enough” variants
- any new mascot visual must be promoted through repo asset canon first

## 9. Alignment Matrix

### 9.1 Aligned

- repo token pipeline is governed and explicit
- Storybook is already the canonical web review lane
- repo component vocabulary exists and is usable for clean-file mapping
- `PulsePlate_v3` contains at least one trustworthy foundations frame (`35:148`)

### 9.2 Drift in Figma

- public node target `16:11` is not execution-safe
- current file lacks clean page structure for this phase
- node-level readiness is inconsistent inside the current file

### 9.3 Drift in code

- `frontend/src/components/PremiumGate.tsx` still carries legacy styling debt
- `frontend/src/components/VipBadge.tsx` includes purple drift that conflicts
  with current palette governance

### 9.4 Missing in Figma

- governed clean-file page structure
- governed component-library page built from repo primitives
- explicit audit/archive lane for legacy references and broken nodes
- clean Welcome Gate state variants

### 9.5 Missing in repo

- governed primitives for select, textarea, checkbox, radio-group, alert,
  tooltip, dropdown-menu, tabs, and a reusable step/progress rail primitive

### 9.6 Needs vocabulary decision

- Welcome Gate step rail / progress indicator naming and ownership
- membrane annotation blocks and index markers
- archive treatment for `PulsePlate_v3` reference frames

## 10. Blocker Classes

Use these blocker labels in review notes, Figma audit pages, and follow-up PRs:

- `invalid_or_stale_node_target`
- `missing_component_archetype`
- `token_parity_mismatch`
- `visual_drift`
- `unresolved_ownership`

## 11. Clean File Page Structure

The clean Figma file `2JDwOByQIbcPgp93FDzHii` must contain only these pages in
Phase 1:

1. `00_Foundation_Tokens`
2. `01_Components`
3. `02_Brand_Assets`
4. `10_Welcome_Gate`
5. `11_Welcome_Gate_States`
6. `90_Audit_Archive`

## 12. Pilot Build Sequence

Execute in this order:

1. audit current `PulsePlate_v3` and keep only trustworthy frames/tokens as reference
2. rebuild foundation tokens in the clean file from repo token SoT
3. rebuild shared components from repo primitives first
4. rebuild brand assets and approved FitChef placements
5. rebuild Welcome Gate as the pilot flow
6. add state variants and review notes
7. only then decide whether follow-up surfaces should be added

## 13. FIGR AI Lane Policy

FIGR AI is allowed only as an optional read-only ideation lane.

Approved uses:

- exploring onboarding/welcome prototype variations
- gathering alternative layout ideas
- comparing conceptual gate compositions

Forbidden uses:

- replacing repo or Figma SoT
- generating authoritative tokens/components directly
- bypassing repo review by pasting FIGR output into production lanes unchanged

Reference URLs:

- <https://docs.figr.design/docs/design-intelligence/figr-mcp>
- <https://mcp.figr.design/mcp>
- <https://docs.figr.design/changelog>

## 14. Review and Validation Contract

The clean file passes Phase 1 only when all are true:

- MCP validation succeeds for known-good clean-file frames
- no unmanaged local Figma styles remain
- each governed component maps to a repo primitive or documented missing primitive
- Storybook/component docs remain the canonical web review surface
- Welcome Gate hierarchy matches `Pulse Membrane` rules
- mascot provenance rules pass
- target-size and accessibility rules are explicit
- old `H+P+Pr` docs remain intact and are not silently repurposed

## 15. Follow-up Split

Follow-up work is intentionally split:

- PR A: docs + reconciliation packet + indices
- PR B: repo token/component parity cleanup
- PR C: clean Figma foundations/components/welcome-gate execution
- PR D: optional mapping annex or future bridge readiness only if needed

The follow-up execution package is tracked in:

- `docs/roadmap/BACKLOG_LEDGER.md`
