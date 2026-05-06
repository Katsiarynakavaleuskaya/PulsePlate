<!-- markdownlint-disable MD013 -->
# PulsePlate DESIGN.md

**Status:** Generated or drift-checked semantic wrapper
**Generator:** `scripts/design/generate_design_md.py`

> DESIGN.md is generated or drift-checked from repo token/component contracts. It is an agent-readable semantic wrapper, not a source of truth. If it conflicts with `/tokens`, generated mirrors, UI vocabulary, backend/OpenAPI contracts, or runtime code, repo truth wins.

## Source List

This file is generated from repo-owned contracts:

- `/tokens`
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/design/ui_component_vocabulary.json`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
- `docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md`
- `docs/design/REFERENCE_MANIFEST_SCHEMA.md`
- `docs/design/REFERENCE_SCORECARD.md`

## Brand Intent

PulsePlate is a planning-first wellness and meal-planning product. Its design intent is premium-clean, calm, trust-safe, and practical for repeated planning work.

PulsePlate is not a medical diagnosis, treatment, therapy, crisis-support, emergency-care, or guaranteed-outcome product. Design copy and screen grammar must stay wellness-only and evidence-careful.

## Source Precedence

1. Repo code, docs, tests, backend contracts, OpenAPI contracts, and merge governance.
2. `/tokens` as the design-token authoring source.
3. Generated runtime mirrors derived from `/tokens`:
   - `frontend/src/styles/tokens.css`
   - `frontend/src/styles/tokens.ts`
   - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
4. UI vocabulary and component contracts:
   - `docs/design/UI_COMPONENT_VOCABULARY.md`
   - `docs/design/ui_component_vocabulary.json`
5. Implemented web and iOS clients as thin presentation layers over backend truth.
6. Storybook as review and documentation only.
7. Figma as design-intent and review evidence only.
8. External references as read-only benchmark inputs only.

DESIGN.md does not override any source above.

## Tokens

`/tokens` remains the token authoring source. Runtime mirrors are generated outputs and must not be edited manually.

Generated mirrors:

- `frontend/src/styles/tokens.css`
- `frontend/src/styles/tokens.ts`
- `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`

Do not promote raw hex values from prompts, Figma, screenshots, external references, Storybook stories, or DESIGN.md into implementation. Token changes must go through `/tokens`, deterministic regeneration, and token parity gates.

## Components

Canonical component vocabulary comes from `docs/design/ui_component_vocabulary.json`. Agents must use existing ids and names; do not invent component vocabulary in prompts, DESIGN.md edits, external reference notes, or implementation briefs.

Canonical component ids:

`alert`, `badge`, `button`, `card`, `checkbox`, `dialog`, `dropdown_menu`, `empty_state`, `form_field`, `hero`, `input`, `mobile_menu`, `navigation_tab_bar`, `progress`, `radio_group`, `segmented_control`, `select`, `skeleton`, `stats_card`, `stepper_progress_indicator`, `tabs`, `textarea`, `toggle`, `tooltip`

| Id | Canonical name | Status | Repo component |
| --- | --- | --- | --- |
| alert | alert | missing | `none` |
| badge | badge | specialized-existing | `frontend/src/components/VipBadge.tsx` |
| button | button | existing | `frontend/src/components/ui/Button.tsx` |
| card | card | existing | `frontend/src/components/ui/Card.tsx` |
| checkbox | checkbox | missing | `none` |
| dialog | dialog | existing | `frontend/src/components/ui/Dialog.tsx` |
| dropdown_menu | dropdown-menu | missing | `none` |
| empty_state | empty-state | existing | `frontend/src/components/ui/EmptyState.tsx` |
| form_field | form-field | existing | `frontend/src/components/ui/FormField.tsx` |
| hero | hero | specialized-existing | `frontend/src/pages/Home.tsx` |
| input | input | existing | `frontend/src/components/ui/Input.tsx` |
| mobile_menu | mobile-menu | existing | `frontend/src/components/ui/MobileMenu.tsx` |
| navigation_tab_bar | navigation/tab-bar | existing | `frontend/src/components/TabBar.tsx` |
| progress | progress | specialized-existing | `frontend/src/features/progress/LiveProgressIndicator.tsx` |
| radio_group | radio-group | missing | `none` |
| segmented_control | segmented-control | existing | `frontend/src/components/ui/SegmentedControl.tsx` |
| select | select | missing | `none` |
| skeleton | skeleton | existing | `frontend/src/components/ui/Skeleton.tsx` |
| stats_card | stats-card | specialized-existing | `frontend/src/pages/NutritionSetup/MacroCards.tsx` |
| stepper_progress_indicator | stepper/progress-indicator | missing-primitive-existing-flow | `frontend/src/pages/NutritionSetup/SetupForm.tsx` |
| tabs | tabs | missing | `none` |
| textarea | textarea | missing | `none` |
| toggle | toggle | existing | `frontend/src/components/ui/Toggle.tsx` |
| tooltip | tooltip | missing | `none` |

## Screen Grammar

Backend and OpenAPI contracts remain product and runtime truth. Web and iOS clients are thin presentation clients and cannot invent pricing, billing, entitlement, nutrition, medical, compliance, App Store, or backend-derived state.

Future implementation briefs must map screen structure to repo-owned routes, contracts, tokens, and component vocabulary before code changes begin.

## Accessibility

Design work must preserve:

- contrast and readable hierarchy,
- visible focus states,
- keyboard access,
- touch target comfort,
- non-color-only state communication,
- reduced-motion-safe behavior.

Motion must not carry required product meaning by itself.

## External Reference Policy

External references are read-only. They may provide derived metadata only after normalization into PulsePlate vocabulary.

Do not copy external screenshots, assets, brands, exact layouts, proprietary components, visual identity, or marketing copy. Future references require the manifest and scorecard controls before they can inform a brief:

- `docs/design/REFERENCE_MANIFEST_SCHEMA.md`
- `docs/design/REFERENCE_SCORECARD.md`

## Design Automation Modules

Design automation items are modules inside the existing PulsePlate Design Intelligence / Design Runtime system, not standalone plugins and not a separate source of truth.

- Icon Asset Validator -> release/design asset guard module
- Design Evidence Harvester -> Design Intelligence PR-3 screen evidence pack module
- Button / Component Drift Inspector -> Design Intelligence PR-4 deterministic scorecard + Storybook/vocabulary parity module
- Marketing Asset Pack Compiler -> late GTM compiler over approved design/copy truth
- Launch Copy Compliance Linter -> marketing/release copy guard aligned with wellness/compliance rules

This PR records classification only. These modules are not implemented by DESIGN.md generation.

## Do / Don't

Do:

- use repo tokens, UI vocabulary, reviewed components, and backend contracts,
- cite evidence links when producing design briefs,
- keep Storybook in the review/documentation lane,
- keep Figma in the design-intent lane,
- keep external references read-only until a later manifest and scorecard approve normalized use.

Don't:

- create a second source of truth,
- manually edit generated token mirrors,
- move backend, OpenAPI, billing, auth, nutrition, compliance, or App Store truth into clients,
- copy external assets, brands, exact layouts, screenshots, proprietary components, or marketing copy,
- treat DESIGN.md as runtime, token, Figma, Storybook, or product authority.

## Evidence Links

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md`
- `docs/orchestration/DESIGN_INTELLIGENCE_PR0_PACKET_2026-05-05.md`
- `docs/design/PULSEPLATE_DESIGN_MD_BOOTSTRAP.md`
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/design/ui_component_vocabulary.json`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
- `docs/design/REFERENCE_MANIFEST_SCHEMA.md`
- `docs/design/REFERENCE_SCORECARD.md`
