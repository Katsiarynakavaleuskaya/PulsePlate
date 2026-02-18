<!-- markdownlint-disable MD013 -->
# PulsePlate Figma AI Governance Index (Home + Plate + Progress)

**Date:** February 18, 2026
**Scope:** Figma AI personalization for `Home + Plate + Progress` across Web + iOS
**Language mode:** EN primary, RU notes for critical constraints

## 1) Purpose

This document is a governance SoT for Figma AI (`Guidelines.md` in Figma Make)
and a structured index for design execution.

Operational runbook (mandatory):

- `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
- `docs/figma/FIGMA_GIT_PACKS_INDEX.md`

It aligns Figma AI output with project visual SoT and button-level behavior SoT:

- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`

Operational anchors:

- Root visual references: `AGENTS.md:499`, `AGENTS.md:502`
- Frontend scoped reference: `frontend/AGENTS.md:21`
- iOS scoped reference: `ios/AGENTS.md:23`
- Figma page blueprint baseline: `docs/audit/PR_781_HOME_PLATE_PROGRESS_AUDIT_RUNBOOK_2026-02-17.md:162`

## 2) Paste-Ready Figma AI Instructions (for `guidelines/Guidelines.md`)

Use this block as the canonical instruction payload for Figma AI in the current slice.

```md
# PulsePlate Figma AI Rules (H+P+Pr)

## Scope lock
- Work only on Home, Plate, Progress (Web + iOS) and directly linked CTA downstream flows (setup/paywall/retry/edit).
- Do not introduce unrelated feature surfaces in this pass.

## Brand and tone lock (non-negotiable)
- Mood: minimal + cozy + intelligent + luxury-clean.
- Palette lock: #0F172A, #339FFF, #20C997, #FF5D5D (accent only).
- Visual style: flat forms, soft shadows, subtle gradients, clear small-size silhouettes.
- Tone: wellness lifestyle; never medical or diagnostic.
- RU: без медицинских обещаний, без клинического фрейминга.

## Anti-drift lock (always apply)
- No generic AI slop.
- No neon drift, no glossy 3D blobs, no purple/gold drift.
- No copycat competitor look.
- No manipulative fear/shame visuals.

## Token lock (implementation parity)
- Web token source: frontend/src/styles/tokens.css, frontend/src/styles/tokens.ts, frontend/tailwind.config.ts.
- iOS token source: ios/PulsePlate/Assets.xcassets/*.colorset, ios/PulsePlate/Extensions/Color+Assets.swift.
- Use semantic tokens first, avoid ad-hoc color literals.

## Naming lock
- Component and frame naming convention:
  PP/<Platform>/<Screen>/<Component>/<State>

## CTA lock (button-level SoT)
- Every CTA must map to an existing Button/CTA ID from the matrix document.
- For each CTA, define these states when applicable:
  default, hover/pressed, focus-visible, disabled/locked, loading, error.
- Keep CTA hierarchy consistent: primary > secondary > utility.

## Accessibility lock
- WCAG AA minimum contrast for text and actionable controls.
- Keep interaction targets generous (web clickable, iOS tappable).
- Respect reduced-motion preferences.

## Safety lock
- No medical claims, no diagnosis framing, no cure language.
- No proprietary secrets or internal URLs in prompt text.

## Delivery lock
- Output should be design-system-friendly and code-handoff-ready.
- Use structured sections: Foundation Tokens, Components, Screens, CTA States, QA Notes.
```

## 3) Figma Structure Index (to fill in file)

Use this page index (from current audit blueprint) as fixed skeleton:

1. `00_Foundation_Tokens`
2. `01_Components`
3. `10_iOS_Home`
4. `11_iOS_Plate`
5. `12_iOS_Progress`
6. `20_Web_Parity`

Reference: `docs/audit/PR_781_HOME_PLATE_PROGRESS_AUDIT_RUNBOOK_2026-02-17.md:169`.

### 3.1 `00_Foundation_Tokens`

Required sections:

- Core palette (locked values)
- Semantic color mapping (success/warning/error/info)
- Type scale and spacing scale
- Radius and shadow scale
- Motion and reduced-motion notes
- Cross-surface token mapping (Web token name <-> iOS asset name)

### 3.2 `01_Components`

Required component sets:

- Top bar
- Tab bar
- Glass card
- KPI card
- Progress ring
- Segment chip
- CTA button states
- Empty/Error/Loading blocks
- Mascot block
- Section header

Reference: `docs/audit/PR_781_HOME_PLATE_PROGRESS_AUDIT_RUNBOOK_2026-02-17.md:178`.

## 4) CTA Registry Index (H+P+Pr)

This list is the baseline set to register in Figma as components/variants.

### 4.1 Web

- `web.home.open_setup`
- `web.home.open_plate`
- `web.home.open_progress`
- `web.home.open_pro`
- `web.plate.open_setup`
- `web.plate.open_progress`
- `web.plate.premium_gate_cta`
- `web.progress.export_pdf`
- `web.paywall.modal.cta`
- `web.paywall.modal.cancel`
- `web.setup.submit_calculate`
- `web.setup.result.retry`
- `web.setup.result.edit`

### 4.2 iOS

- `ios.home.bmi_calculator`
- `ios.home.profile_setup`
- `ios.home.open_plate`
- `ios.home.weekly_plan_reader` (flagged)
- `ios.home.shopping_list_generator` (flagged)
- `ios.plate.add_meal` (partial)
- `ios.plate.view_details` (partial)
- `ios.plate.issue_action_dynamic`
- `ios.progress.refresh`
- `ios.progress.issue_action_dynamic`

Canonical source: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:59`.

## 5) Prompt Stub Index for Figma AI

Use prompt stubs as structured placeholders (not final marketing prompts):

- `ICON_STUB_V1`
- `CTA_PRIMARY_STUB_V1`
- `CTA_SECONDARY_STUB_V1`
- `CTA_DISABLED_STUB_V1`
- `CTA_LOADING_STUB_V1`
- `CTA_ERROR_STUB_V1`

Canonical templates: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:85`.

Mandatory guard clause block (attach to each prompt family):

- no medical claims
- no diagnostic framing
- no body-shaming or fear pressure
- no copycat brand imitation
- no generic AI slop

Prompt governance source: `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:290`.

## 6) Figma QA Gate (Pass/Fail)

Before accepting generated visuals/components:

- Brand lock preserved (palette/style)
- One clear focal hierarchy
- Text/icon legibility at target sizes
- Motion comfort + reduced-motion safe
- WCAG AA baseline and focus visibility
- Wellness-safe (no clinical/diagnostic framing)
- Cross-surface consistency (iOS/Web/social)

Reference checklist: `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md:13`.

## 7) Handoff Contract (Design -> Sora -> FE/iOS)

Required output fields per CTA/component:

- `Button/CTA ID`
- `Figma Node ID` (or `TBD` if not assigned yet)
- `State` (default/hover/focus/disabled/loading/error)
- `Sora Prompt Stub ID`
- `Status` (`Implemented`, `Partial`, `Missing`, `Blocked by flag`)
- `Implement Needed`

Status legend source: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:49`.

## 8) Security Notes

- Do not include secrets, API keys, internal URLs, or proprietary identifiers in Figma AI prompt text.
- Keep all generated content wellness-safe and non-diagnostic.
- Any prompt change must preserve anti-drift constraints.

## 9) Marketing & GTM Notes

- This index supports ASO/social creative consistency at button and state level.
- The same CTA vocabulary should be reused across product surfaces and launch creatives.
- Priority is trust-first premium UX, not aggressive conversion aesthetics.

## 10) Decision Log

- 2026-02-18: Consolidated visual SoT + button matrix into one Figma AI governance index.
- 2026-02-18: Preserved H+P+Pr fixed scope and PP naming contract.
- 2026-02-18: Prompt stubs kept template-level by design; no mass final-prompt generation in this phase.
- 2026-02-18: Added operational runbook + Git packs index as mandatory context layer.
<!-- markdownlint-enable MD013 -->
