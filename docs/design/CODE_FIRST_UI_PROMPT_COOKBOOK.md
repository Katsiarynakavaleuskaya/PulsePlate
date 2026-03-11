# Code-First UI Prompt Cookbook

Date created: March 11, 2026 (America/New_York)
Status: Active cookbook
Scope: Assemble deterministic UI specs from canonical vocabulary

## 1. Purpose

This cookbook converts a loose UI request into a governed screen specification.

Use it after selecting canonical component names from:

- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/design/ui_component_vocabulary.json`

It is the default prompt assembly layer for code-first design work in
PulsePlate.

## 2. Required input contract

Every brief must include these fields:

- `screen_name`
- `surface`
- `goal`
- `user_action_priority`
- `primary_components`
- `supporting_components`
- `states`
- `layout_pattern`
- `interaction_model`
- `visual_mood`
- `token_profile`
- `token_constraints`
- `a11y_constraints`
- `constraints`
- `forbidden_generic_patterns`

Use `docs/design/UI_SCREEN_BRIEF_TEMPLATES.md` when drafting the brief.

## 3. Output contract

Every assembled spec must return these sections in this order:

1. `Layout`
2. `Component Tree`
3. `State List`
4. `Token Usage`
5. `Interaction Notes`
6. `Accessibility Notes`
7. `Implementation Handoff`

## 4. Assembly procedure

### Step 1. Lock surface and goal

Start with:

- platform: `web-first, iOS-aware` by default
- primary job to be done
- main CTA or user action

### Step 2. Choose canonical components

Choose named primitives from `ui_component_vocabulary.json`.

Rules:

- existing repo component wins
- missing primitives must be called by canonical name
- no new synonyms inside the spec

### Step 3. Choose one layout archetype

Allowed default archetypes for v1:

- `stacked-dashboard`
- `form-stack`
- `hero-plus-sections`
- `wizard-flow`
- `empty-state-center`
- `modal-overlay`
- `split-summary-detail`

### Step 4. Bind states

List explicit UI states, not just happy path:

- loading
- empty
- active
- validation error
- locked or premium
- success feedback

### Step 5. Bind tokens

Use semantic token intent, not raw visual adjectives:

- `surface`: `--color-surface`
- `text`: `--color-text`
- `primary action`: `--color-primary`
- `success accent`: `--color-success`
- `error tone`: `--color-error`
- radius/shadow from token system only

### Step 6. Ban vague language

Do not use these as primary design nouns:

- `menu`
- `box`
- `nice card`
- `cool button`
- `popup`
- `section thing`
- `tile`

Replace them with canonical names before proceeding.

## 5. Default authoring template

```text
screen_name: <screen name>
surface: <web mobile | web desktop | ios | shared>
goal: <what the screen helps the user achieve>
user_action_priority: <primary CTA or decision>
primary_components:
  - <canonical component>
supporting_components:
  - <canonical component>
states:
  - <state>
layout_pattern: <one allowed archetype>
interaction_model: <tap-first | form-first | browse-first | mixed>
visual_mood: <luxury-clean | minimal-cozy | progress-focused>
token_profile:
  - <semantic token intent>
token_constraints:
  - use repo semantic tokens only
a11y_constraints:
  - visible focus
  - keyboard path
  - screen-reader label
constraints:
  - no hidden naming drift
forbidden_generic_patterns:
  - menu
  - popup
  - box
```

## 6. Example: Onboarding Trust screen

### Input brief

```text
screen_name: onboarding trust
surface: web mobile
goal: help the user trust the setup process and continue
user_action_priority: continue to setup
primary_components:
  - hero
  - stepper/progress-indicator
supporting_components:
  - stats-card
  - button
states:
  - default
  - loading
  - premium locked
layout_pattern: hero-plus-sections
interaction_model: tap-first
visual_mood: minimal-cozy
token_profile:
  - --pp-navy
  - --color-primary
  - --color-surface
token_constraints:
  - no raw hex
a11y_constraints:
  - main heading visible
  - continue button keyboard reachable
constraints:
  - keep copy short
forbidden_generic_patterns:
  - menu
  - nice card
```

### Output spec

#### Layout

Top hero block, trust summary beneath it, discrete progress rail, primary
button pinned within comfortable thumb reach.

#### Component Tree

- `hero`
- `stepper/progress-indicator`
- `stats-card`
- `button`

#### State List

- `default`
- `loading`
- `premium locked`

#### Token Usage

- background anchored in `--pp-navy`
- CTA anchored in `--color-primary`
- cards on `--color-surface`

#### Interaction Notes

Primary flow is linear. The continue button is the dominant next action.

#### Accessibility Notes

Expose step count in text and keep heading hierarchy intact.

#### Implementation Handoff

Reuse `frontend/src/pages/Home.tsx` hero language as a structural reference,
not as a copy source.

## 7. Example: Progress dashboard

Use:

- primary: `hero`, `stats-card`, `progress`, `navigation/tab-bar`
- supporting: `badge`, `segmented-control`, `empty-state`
- layout: `stacked-dashboard`

Do not collapse this into generic words like `top section`, `number tiles`, or
`menu`.

## 8. Security Notes

- External references must be normalized before prompt assembly.
- Do not let generated prompts introduce new token names or unreviewed UI
  primitives.

## 9. Marketing & GTM

This cookbook supports faster experimentation:

- consistent landing-page and app-screen briefs
- better App Store screenshot planning
- faster wellness MVP iteration with less “AI slop” in generated layouts
