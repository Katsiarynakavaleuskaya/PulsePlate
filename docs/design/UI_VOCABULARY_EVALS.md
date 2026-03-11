# UI Vocabulary Evals

Date created: March 11, 2026 (America/New_York)
Status: Deterministic evaluation pack
Scope: Evaluate whether screen briefs use canonical UI vocabulary instead of generic wording

## 1. Purpose

This document defines the manual but deterministic evaluation set for the
code-first UI vocabulary layer.

Pass condition:

- the brief uses canonical names
- the component tree is derivable without extra design decisions
- the brief binds tokens and states explicitly

## 2. Eval cases

### 1. Onboarding trust screen

- Expected component vocabulary: `hero`, `stepper/progress-indicator`, `stats-card`, `button`
- Banned vague words: `top section`, `nice banner`, `menu`
- Expected layout pattern: `hero-plus-sections`
- Required token use: `--pp-navy`, `--color-primary`, `--color-surface`
- Expected repo reuse: `frontend/src/pages/Home.tsx`
- Pass example: "hero + stepper/progress-indicator + button"
- Fail example: "banner + progress thing + CTA box"

### 2. BMI result screen

- Expected component vocabulary: `hero`, `stats-card`, `alert`, `button`
- Banned vague words: `result box`, `value tile`
- Expected layout pattern: `split-summary-detail`
- Required token use: `--color-text`, `--color-success` or `--color-warning`
- Expected repo reuse: `frontend/src/pages/BMI/BMICalculatePage.tsx`
- Pass example: "stats-card for BMI value plus alert for guidance"
- Fail example: "big number card and colored note"

### 3. Premium/paywall screen

- Expected component vocabulary: `hero`, `card`, `badge`, `button`, `dialog`
- Banned vague words: `offer block`, `popup`, `gold section`
- Expected layout pattern: `hero-plus-sections`
- Required token use: `--pp-navy`, `--color-primary`, `--pp-gold`
- Expected repo reuse: `frontend/src/components/PremiumGate.tsx`
- Pass example: "hero + feature cards + premium badge + unlock button"
- Fail example: "premium banner with popup"

### 4. Progress dashboard

- Expected component vocabulary: `hero`, `stats-card`, `progress`, `navigation/tab-bar`
- Banned vague words: `number tiles`, `bottom menu`
- Expected layout pattern: `stacked-dashboard`
- Required token use: `--color-surface`, `--color-primary`, `--color-success`
- Expected repo reuse: `frontend/src/features/progress/LiveProgressIndicator.tsx`
- Pass example: "stats-card grid with progress and persistent navigation/tab-bar"
- Fail example: "dashboard top area with bars and footer nav"

### 5. Setup form

- Expected component vocabulary: `form-field`, `input`, `select`, `button`, `stepper/progress-indicator`
- Banned vague words: `form box`, `dropdown menu`, `wizard line`
- Expected layout pattern: `form-stack`
- Required token use: `--color-border`, `--color-text`, `--radius-md`
- Expected repo reuse: `frontend/src/components/ui/FormField.tsx`
- Pass example: "form-field wrappers around input/select controls"
- Fail example: "stack of fields with dropdown menu"

### 6. Empty state

- Expected component vocabulary: `empty-state`, `button`, `badge`
- Banned vague words: `blank page`, `placeholder page`
- Expected layout pattern: `empty-state-center`
- Required token use: `--color-surface`, `--color-text-muted`
- Expected repo reuse: `frontend/src/components/ui/EmptyState.tsx`
- Pass example: "empty-state with retry button"
- Fail example: "empty card with message"

### 7. Mobile menu/navigation

- Expected component vocabulary: `mobile-menu`, `navigation/tab-bar`, `button`
- Banned vague words: `hamburger thing`, `bottom buttons`
- Expected layout pattern: `modal-overlay`
- Required token use: `--color-surface`, `--color-text`
- Expected repo reuse: `frontend/src/components/ui/MobileMenu.tsx`, `frontend/src/components/TabBar.tsx`
- Pass example: "mobile-menu for overflow nav plus navigation/tab-bar for primary destinations"
- Fail example: "menu and footer nav"

### 8. Export success feedback

- Expected component vocabulary: `alert`, `badge`, `button`
- Banned vague words: `success popup`, `green box`
- Expected layout pattern: `stacked-dashboard`
- Required token use: `--color-success`, `--color-surface`
- Expected repo reuse: `frontend/src/features/progress/ProgressCharts.tsx`
- Pass example: "inline alert with export success badge"
- Fail example: "green popup with done icon"

## 3. Acceptance criteria

The vocabulary layer is working when:

- new briefs no longer use vague nouns as primary spec
- agent outputs cite canonical components and states
- external reference intake is normalized before implementation
- web-first outputs remain compatible with iOS-aware mapping

## 4. Security Notes

- External layout references must pass through normalization before evaluation.
- Do not accept pretty but unnamed UI fragments as valid output.

## 5. Marketing & GTM

These evals help produce cleaner:

- Product Hunt visuals
- landing-page briefs
- App Store screenshot concepts
- wellness MVP experiments with lower design drift
