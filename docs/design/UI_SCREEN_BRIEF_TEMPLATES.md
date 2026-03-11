# UI Screen Brief Templates

Date created: March 11, 2026 (America/New_York)
Status: Active templates
Scope: Canonical input briefs for code-first UI work

## 1. Purpose

Use these templates before invoking:

- `docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md`
- `docs/design/UI_COMPONENT_VOCABULARY.md`

Every new screen brief should start from this structure instead of raw prose.

## 2. Base template

```text
screen_name:
surface:
goal:
user_action_priority:
primary_components:
  -
supporting_components:
  -
states:
  -
layout_pattern:
interaction_model:
visual_mood:
token_profile:
  -
constraints:
  -
```

## 3. Control briefs

### Onboarding trust screen

```text
screen_name: onboarding trust
surface: web mobile
goal: increase trust and move the user into setup
user_action_priority: continue setup
primary_components:
  - hero
  - stepper/progress-indicator
supporting_components:
  - stats-card
  - button
states:
  - default
  - loading
layout_pattern: hero-plus-sections
interaction_model: tap-first
visual_mood: minimal-cozy
token_profile:
  - --pp-navy
  - --color-primary
```

### BMI result screen

```text
screen_name: bmi result
surface: web mobile
goal: explain the result and point to the next action
user_action_priority: continue to next health-safe step
primary_components:
  - stats-card
  - alert
supporting_components:
  - button
states:
  - default
  - warning
layout_pattern: split-summary-detail
interaction_model: read-first
visual_mood: progress-focused
token_profile:
  - --color-text
  - --color-success
  - --color-warning
```

### Premium/paywall screen

```text
screen_name: premium paywall
surface: web mobile
goal: communicate value and unlock premium
user_action_priority: unlock premium
primary_components:
  - hero
  - card
  - button
supporting_components:
  - badge
  - dialog
states:
  - default
  - locked
layout_pattern: hero-plus-sections
interaction_model: tap-first
visual_mood: luxury-clean
token_profile:
  - --pp-navy
  - --pp-gold
  - --color-primary
```

### Progress dashboard

```text
screen_name: progress dashboard
surface: web mobile
goal: show momentum and keep the user engaged
user_action_priority: inspect progress details
primary_components:
  - hero
  - stats-card
  - progress
supporting_components:
  - segmented-control
  - navigation/tab-bar
states:
  - default
  - empty
  - loading
layout_pattern: stacked-dashboard
interaction_model: browse-first
visual_mood: progress-focused
token_profile:
  - --color-surface
  - --color-primary
  - --color-success
```

### Setup form

```text
screen_name: setup form
surface: web mobile
goal: collect setup inputs with low friction
user_action_priority: submit the current step
primary_components:
  - form-field
  - input
  - select
supporting_components:
  - button
  - stepper/progress-indicator
states:
  - default
  - error
  - loading
layout_pattern: form-stack
interaction_model: form-first
visual_mood: minimal-cozy
token_profile:
  - --color-border
  - --color-text
  - --radius-md
```

### Empty state

```text
screen_name: progress empty state
surface: web mobile
goal: help the user recover from no data and start the right action
user_action_priority: start tracking
primary_components:
  - empty-state
supporting_components:
  - button
  - badge
states:
  - default
  - retry
layout_pattern: empty-state-center
interaction_model: tap-first
visual_mood: minimal-cozy
token_profile:
  - --color-surface
  - --color-text-muted
```

### Mobile menu and navigation

```text
screen_name: mobile navigation
surface: web mobile
goal: keep primary navigation persistent and secondary nav compact
user_action_priority: move to another top-level destination
primary_components:
  - navigation/tab-bar
  - mobile-menu
supporting_components:
  - button
states:
  - default
  - open
  - active
layout_pattern: modal-overlay
interaction_model: tap-first
visual_mood: minimal-cozy
token_profile:
  - --color-surface
  - --color-text
```

### Export success feedback

```text
screen_name: export success feedback
surface: web mobile
goal: confirm the export and offer the next action
user_action_priority: share or continue
primary_components:
  - alert
supporting_components:
  - badge
  - button
states:
  - success
layout_pattern: stacked-dashboard
interaction_model: tap-first
visual_mood: progress-focused
token_profile:
  - --color-success
  - --color-surface
```

## 4. Security Notes

- Use these templates only after normalizing external references into canonical
  vocabulary.
- Do not let raw vendor wording bypass the brief structure.

## 5. Marketing & GTM

These briefs are reusable for:

- in-product surfaces
- screenshot planning
- landing-page sections
- lightweight wellness MVP experiments
