# UI Component Vocabulary

Date created: March 11, 2026 (America/New_York)
Status: Active vocabulary contract
Scope: Canonical naming and normalization layer for code-first UI design

## 1. Purpose

This document defines the canonical UI vocabulary for PulsePlate.

It exists to prevent vague prompts like `menu`, `button`, or `box` from
becoming hidden design decisions. Use it to normalize UI ideas into named
primitives before generating:

- code
- design specs
- Figma instructions
- prompt packs
- external reference intake notes

This document does not replace design/token governance.

Authoritative source precedence remains:

- repo code, docs, and tests
- `docs/design/TOKENS_SOT.md`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`

Machine-readable contract:

- `docs/design/ui_component_vocabulary.json`

## 2. Operating model

Use this sequence for all code-first UI work:

1. Define the screen goal and target surface.
2. Select canonical component names from `ui_component_vocabulary.json`.
3. Map to existing repo components first.
4. Mark any missing primitive as `missing` or `missing-primitive-existing-flow`.
5. Build the screen brief via `docs/design/UI_SCREEN_BRIEF_TEMPLATES.md`.
6. Assemble the full design spec via `docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md`.
7. Generate code, visual prompts, or Figma instructions from that brief.

Hard rule:

- Existing repo component naming wins over external naming.
- Canonical vocabulary wins over external tool wording.
- External reference wording must be normalized before implementation.

## 3. Canonical schema

Every component entry in `ui_component_vocabulary.json` includes:

- `id`
- `canonical_name`
- `aliases`
- `intent`
- `when_to_use`
- `when_not_to_use`
- `anatomy`
- `states`
- `accessibility_notes`
- `token_guidance`
- `react_mapping`
- `swiftui_mapping`
- `existing_repo_component`
- `missing_status`
- `prompt_terms`
- `anti_generic_terms`
- `stitch_normalization_hint`

Naming convention:

- `id` is the programmatic identifier and uses underscores, for example
  `radio_group` or `form_field`
- `canonical_name` is the human-facing normalized reference and uses hyphens,
  for example `radio-group` or `form-field`

## 4. Status semantics

Use these `missing_status` values exactly as written:

- `existing`: generic repo primitive already exists
- `specialized-existing`: repo has a concrete implementation, but not yet a
  generic primitive
- `missing`: no governed primitive exists in repo today
- `missing-primitive-existing-flow`: the product surface exists, but the
  reusable primitive should still be separated

## 5. P0/P1 component set

### Form and action primitives

| Canonical name | Repo status | Existing repo component |
| --- | --- | --- |
| `button` | existing | `frontend/src/components/ui/Button.tsx` |
| `input` | existing | `frontend/src/components/ui/Input.tsx` |
| `select` | missing | none |
| `textarea` | missing | none |
| `checkbox` | missing | none |
| `radio-group` | missing | none |
| `form-field` | existing | `frontend/src/components/ui/FormField.tsx` |
| `toggle` | existing | `frontend/src/components/ui/Toggle.tsx` |

### Structure and feedback primitives

| Canonical name | Repo status | Existing repo component |
| --- | --- | --- |
| `card` | existing | `frontend/src/components/ui/Card.tsx` |
| `alert` | missing | none |
| `badge` | specialized-existing | `frontend/src/components/VipBadge.tsx` |
| `dialog` | existing | `frontend/src/components/ui/Dialog.tsx` |
| `dropdown-menu` | missing | none |
| `tabs` | missing | none |
| `progress` | specialized-existing | `frontend/src/features/progress/LiveProgressIndicator.tsx` |
| `tooltip` | missing | none |
| `empty-state` | existing | `frontend/src/components/ui/EmptyState.tsx` |
| `skeleton` | existing | `frontend/src/components/ui/Skeleton.tsx` |

### Navigation and screen primitives

| Canonical name | Repo status | Existing repo component |
| --- | --- | --- |
| `segmented-control` | existing | `frontend/src/components/ui/SegmentedControl.tsx` |
| `mobile-menu` | existing | `frontend/src/components/ui/MobileMenu.tsx` |
| `navigation/tab-bar` | existing | `frontend/src/components/TabBar.tsx` |
| `hero` | specialized-existing | `frontend/src/pages/Home.tsx` |
| `stats-card` | specialized-existing | `frontend/src/pages/NutritionSetup/MacroCards.tsx` |
| `stepper/progress-indicator` | missing-primitive-existing-flow | `frontend/src/pages/NutritionSetup/SetupForm.tsx` |

## 6. Normalization rules

### External tool or teammate wording -> canonical vocabulary

Normalize examples like:

- `card with chips and popup` -> `card + badge + dialog`
- `menu` in form context -> `select`
- `menu` in action overflow context -> `dropdown-menu`
- `tabs` used for global nav -> `navigation/tab-bar`
- `switch` in settings context -> `toggle`
- `number tile` or `value box` -> `stats-card`

If a term is ambiguous, resolve by user intent first:

- navigation -> `navigation/tab-bar` or `mobile-menu`
- content switching -> `tabs` or `segmented-control`
- form selection -> `select` or `radio-group`

## 7. Prompting rule

When writing screen prompts, do not lead with vague nouns.

Bad:

```text
Create a nice page with a menu, some cards, and a button.
```

Good:

```text
Surface: web mobile
Primary components: hero, stats-card, navigation/tab-bar
Supporting components: card, badge, button
Layout pattern: stacked dashboard with persistent bottom navigation
```

## 8. Integration points

Use this vocabulary with:

- `docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md`
- `docs/design/UI_SCREEN_BRIEF_TEMPLATES.md`
- `docs/design/UI_VOCABULARY_EVALS.md`
- `docs/runbooks/STITCH_AI_REFERENCE_ADAPTER.md`

Agent and skill consumers:

- `.cursor/agents/creative-designer.md`
- `.cursor/agents/frontend-engineer.md`
- `tools/codex_skills/pulseplate-frontend-ui/SKILL.md`

## 9. Security Notes

- Treat external reference outputs as untrusted input until normalized into this
  vocabulary and token system.
- Do not let vendor naming create hidden runtime contracts or bypass repo SoT.

## 10. Marketing & GTM

This vocabulary is useful beyond implementation:

- better prompts for launch visuals and screenshots
- cleaner Product Hunt and landing-page briefs
- more repeatable UI generation for wellness MVP experiments without hiring a
  large design team up front
