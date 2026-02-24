<!-- markdownlint-disable MD013 -->
# PulsePlate Visual Element Prompt Catalog

**Date:** February 24, 2026 (America/New_York)
**Status:** Proposed
**Scope:** Web frontend visibility and modernity uplift based on current app structure

## 1) Purpose

This catalog proposes new visual elements that can be added without violating
current PulsePlate visual governance.

Goals:

- increase first-screen visibility and modern product perception
- keep wellness-safe, trust-first communication
- provide ready prompts for design and generation workflow

Canonical references:

- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- `docs/design/TOKENS_SOT.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- `docs/sora/SORA_STYLE_QA_CHECKLIST.md`

## 2) App Structure Mapping (Current)

Main web routes in runtime:

- `/` Home
- `/plate` Plate
- `/progress` Progress
- `/setup` Nutrition Setup
- `/bmi` BMI Calculate
- `/pro` Pro Paywall
- `/enter-key` Onboarding (Enter API key)

Primary implementation anchors:

- `frontend/src/pages/Home.tsx`
- `frontend/src/pages/Plate.tsx`
- `frontend/src/pages/Progress.tsx`
- `frontend/src/pages/NutritionSetup/index.tsx`
- `frontend/src/pages/BMI/BMICalculatePage.tsx`
- `frontend/src/pages/Pro/ProPaywallPage.tsx`
- `frontend/src/pages/Onboarding/EnterKey.tsx`

## 3) Proposed Visual Additions (Priority)

### P0: High visibility / high impact

1. Home Hero Ambient Layer
2. Progress Momentum Ring + Weekly Streak Badge
3. Premium Gate Value Frame (Plate + Pro)
4. Onboarding Trust Canvas (EnterKey)

### P1: Medium effort / modern polish

5. Setup Completion Step Rail (Nutrition Setup)
6. BMI Result Confidence Card
7. Smart Empty States (Plate/Progress)

### P2: Optional expressive layer

8. Tab Bar Active Trail Micro-Motion
9. Export Success Celebration Chip (Progress PDF)
10. Seasonal Theme Accent Pack (token-safe)

## 4) Prompt Packs by Visual Element

Template per element:

- Why this helps visibility
- Placement
- Figma Prompt (layout/system)
- Sora Prompt (asset/motion)
- Negative Prompt (anti-drift)
- QA checks

---

## Element 01: Home Hero Ambient Layer (P0)

Why:

- makes first screen look premium and modern without adding clutter

Placement:

- `frontend/src/pages/Home.tsx` hero section

Figma Prompt:

```text
Design a Home hero ambient background for PulsePlate web.
Use one dominant focal area behind title and subtitle, luxury-clean, low clutter.
Use only token semantics: --pp-navy base, --pp-blue supportive gradient,
--pp-green tiny accent, no raw hex in final implementation specs.
Include desktop and mobile variants. Keep CTA readability highest priority.
Return layer structure, spacing rhythm, and reduced-motion fallback notes.
```

Sora Prompt:

```text
PulsePlate style lock: minimal, cozy, intelligent, luxury-clean.
Create a subtle ambient hero background loop for wellness dashboard.
Soft navy depth, quiet blue gradient flow, tiny green accent spark,
single focal center, no text, no character faces, no medical symbols.
Motion: very slow 6-8s breathing gradient, reduced-motion safe static frame.
Output: clean PNG keyframe + optional short MP4 loop.
```

Negative Prompt:

```text
no neon, no cyberpunk, no purple/gold drift, no glossy 3d blobs,
no visual noise, no dramatic contrast spikes, no hospital mood
```

QA:

- text contrast in hero remains AA-level readable
- motion does not compete with primary CTA

---

## Element 02: Progress Momentum Ring + Weekly Streak Badge (P0)

Why:

- gives instant "forward motion" signal, increases perceived product intelligence

Placement:

- `frontend/src/pages/Progress.tsx`
- `frontend/src/features/progress/LiveProgressIndicator.tsx`

Figma Prompt:

```text
Design a momentum ring component plus compact weekly streak badge.
Component must work inside existing Progress cards and preserve card hierarchy.
Use tokenized visual levels (primary progress, secondary label, helper text).
Provide states: default, improving, stable, recovering.
Keep iconography legible at small size and avoid clinical semantics.
```

Sora Prompt:

```text
Create a premium flat-style progress ring visual pack for wellness app UI.
Mood: calm confidence, trustworthy analytics, not medical.
Palette lock: navy/blue/green with tiny red accent only when needed.
Generate 4 variants for progress states with identical geometry base.
Output transparent PNG sprites and one subtle ring pulse animation idea.
```

Negative Prompt:

```text
no gamified casino look, no warning-heavy red dominance,
no tiny unreadable numbers, no generic fitness tracker clone
```

QA:

- ring remains clear at 24/32 px mini-size preview
- state differences are visible not only by color

---

## Element 03: Premium Gate Value Frame (P0)

Why:

- improves conversion visibility while keeping calm, non-manipulative tone

Placement:

- `frontend/src/components/PremiumGate.tsx`
- `frontend/src/components/Paywall/BeforeAfter.tsx`

Figma Prompt:

```text
Design a premium value frame module for locked content surfaces.
Structure: title, value bullets, trust microcopy, primary and secondary actions.
Tone must be confident and respectful, no urgency pressure pattern.
Use existing button hierarchy from PulsePlate button visual system.
Return desktop/mobile frame with spacing, typography, and focus states.
```

Sora Prompt:

```text
Create a premium wellness paywall hero visual for a modern app modal.
Style: luxury-clean flat depth, soft shadow, subtle gradient, low clutter.
Scene should communicate capability unlock and personal guidance confidence,
never fear or deficiency. No text baked into image.
Output 3 controlled variants for A/B testing.
```

Negative Prompt:

```text
no countdown urgency, no fear body imagery, no miracle transformation,
no aggressive sales style, no medical cure implication
```

QA:

- visual does not reduce readability of CTA labels
- emotional tone remains supportive and non-pressuring

---

## Element 04: Onboarding Trust Canvas (P0)

Why:

- boosts first-impression quality on `/enter-key`

Placement:

- `frontend/src/pages/Onboarding/EnterKey.tsx`

Figma Prompt:

```text
Design an onboarding trust canvas behind API key entry flow.
Must feel secure, premium, and simple.
Composition: one calm visual anchor, clear form focus, no decorative overload.
Include states: initial, validation in progress, success, invalid key.
Provide accessibility notes for focus order and contrast.
```

Sora Prompt:

```text
Create onboarding trust background artwork for wellness app key setup.
Mood: calm, intelligent, privacy-safe, premium minimal.
No literal locks or cliché cybersecurity icons; use abstract trust geometry.
Use token-safe navy/blue base with minimal green confirmation accents.
Produce static hero plus optional ultra-subtle motion variant.
```

Negative Prompt:

```text
no hacker visuals, no matrix code rain, no fear security aesthetics,
no clinical cross symbols, no heavy texture noise
```

QA:

- form field remains primary focal element
- success/invalid states can be distinguished without flashing effects

---

## Element 05: Setup Completion Step Rail (P1)

Why:

- adds modern guidance and reduces cognitive load in Nutrition Setup

Placement:

- `frontend/src/pages/NutritionSetup/SetupForm.tsx`
- `frontend/src/pages/NutritionSetup/ResultView.tsx`

Figma Prompt:

```text
Design a horizontal/vertical step rail for Nutrition Setup flow.
Steps: Profile Input -> Validation -> Targets -> Result.
Show current step emphasis and completed steps with non-color indicators.
Keep compact mobile behavior and avoid breaking existing form rhythm.
```

Sora Prompt:

```text
Create a clean UI accent pack for setup progress steps in a wellness app.
Flat geometry, token-safe palette, low noise, strong hierarchy.
Generate micro-illustrative markers for 4 steps with consistent family style.
```

Negative Prompt:

```text
no cartoon overload, no emoji style, no rainbow palette,
no complex gradients that reduce label clarity
```

QA:

- each step marker is recognizable in grayscale preview
- current step is obvious in both desktop and mobile

---

## Element 06: BMI Result Confidence Card (P1)

Why:

- improves trust and readability of BMI result surface without medical drift

Placement:

- `frontend/src/pages/BMI/BMICalculatePage.tsx`

Figma Prompt:

```text
Design a BMI result confidence card with clear metric hierarchy.
Sections: primary value, range context, lifestyle-safe recommendation block,
optional next action to setup/progression pages.
Must not imply diagnosis. Keep language and visuals wellness-oriented.
```

Sora Prompt:

```text
Create lightweight visual motifs for BMI result card background accents.
Style: precise, calm analytics, not clinical.
Use restrained token palette and geometric cues for confidence.
No text in image. Provide 3 low-intensity variants.
```

Negative Prompt:

```text
no medical chart aesthetics, no hospital iconography,
no red-alert visual panic, no shame-based body framing
```

QA:

- card remains readable under long translated strings
- no symbol can be interpreted as medical diagnosis indicator

---

## Element 07: Smart Empty States Pack (P1)

Why:

- improves perceived product quality when data is missing or gated

Placement:

- `frontend/src/pages/Plate.tsx`
- `frontend/src/pages/Progress.tsx`
- `frontend/src/components/ui/EmptyState.tsx`

Figma Prompt:

```text
Design a unified empty-state family for Plate and Progress contexts.
Need variants: no data yet, locked by premium, temporary error/retry.
Keep same visual DNA and spacing system across all states.
Include primary and secondary action placement guidance.
```

Sora Prompt:

```text
Create a 3-variant empty-state illustration family for wellness app.
Variant A: no data baseline, Variant B: premium locked preview,
Variant C: temporary retry state. Keep one visual family and low clutter.
Token-safe palette, calm supportive emotion, no fear cues.
```

Negative Prompt:

```text
no sad-face clichés, no failure drama, no aggressive warning visuals,
no medical emergency motifs
```

QA:

- user can immediately understand action next step
- visual style continuity across A/B/C variants is preserved

---

## Element 08: Tab Bar Active Trail Micro-Motion (P2)

Why:

- adds modern polish and perceived responsiveness to navigation

Placement:

- `frontend/src/components/TabBar.tsx`

Figma Prompt:

```text
Design active tab trail micro-motion spec for bottom navigation.
Motion should be subtle, under 220ms equivalent, reduced-motion fallback required.
Define active, inactive, pressed, and focus-visible states.
Do not use glow/neon effects.
```

Sora Prompt:

```text
Create a minimal motion concept for active tab transition in premium app.
Smooth, soft, low-amplitude movement, no bounce exaggeration.
Visual language must remain clean and professional.
Provide storyboard frames only, not flashy animation.
```

Negative Prompt:

```text
no jitter, no strobe, no elastic overshoot, no gaming HUD look
```

QA:

- transition does not distract from page content
- reduced-motion static alternative is clearly defined

---

## Element 09: Export Success Celebration Chip (P2)

Why:

- reinforces successful action in Progress export flow

Placement:

- `frontend/src/features/progress/ProgressCharts.tsx`

Figma Prompt:

```text
Design a compact success chip/toast for export completion.
Use positive but restrained emphasis and fast dismissal behavior.
Include icon, short copy area, and optional open-file action affordance.
Keep mobile-safe width and avoid overlap with key charts.
```

Sora Prompt:

```text
Create a tiny celebratory success accent pack for PDF export completion.
Mood: calm achievement, not confetti party.
Generate 2 icon accents and 1 subtle background swash,
all token-safe and small-size legible.
```

Negative Prompt:

```text
no fireworks/confetti overload, no loud gradients,
no intrusive full-screen celebration
```

QA:

- toast/chip readable in small mobile viewport
- success tone remains professional and unobtrusive

---

## Element 10: Seasonal Theme Accent Pack (P2)

Why:

- enables campaign freshness without breaking core design system

Placement:

- token-compliant overlays across Home/Progress cards only

Figma Prompt:

```text
Design a seasonal accent pack that overlays existing PulsePlate UI
without changing core token identities.
Create spring/summer/autumn/winter accent suggestions using token semantics,
not raw custom palette drift. Keep all accents optional and removable.
```

Sora Prompt:

```text
Create four subtle seasonal ambient accent concepts for wellness app cards.
Each concept must preserve PulsePlate style DNA and token-safe hierarchy.
No holiday clichés, no mascot distortion, no palette override.
Output static accents that can be toggled per campaign.
```

Negative Prompt:

```text
no holiday costume clichés, no palette replacement,
no excessive decorative objects, no brand identity drift
```

QA:

- base UI remains recognizable as PulsePlate
- accents can be disabled with zero layout changes

## 5) Execution Sequence

1. Implement P0 prompts first (Elements 01-04).
Prompt files:
- `docs/sora/prompts/hpp/p0_visibility/home_hero_ambient__home__v1.0.md`
- `docs/sora/prompts/hpp/p0_visibility/progress_momentum_ring__progress__v1.0.md`
- `docs/sora/prompts/hpp/p0_visibility/premium_gate_value_frame__plate_pro__v1.0.md`
- `docs/sora/prompts/hpp/p0_visibility/onboarding_trust_canvas__enter_key__v1.0.md`
2. Validate with `docs/sora/SORA_STYLE_QA_CHECKLIST.md`.
3. Map approved assets to relevant frontend component PRs.
4. Add P1 only after P0 visual consistency pass.
P1 prompt files:
- `docs/sora/prompts/hpp/p1_polish/setup_completion_step_rail__setup__v1.0.md`
- `docs/sora/prompts/hpp/p1_polish/bmi_result_confidence_card__bmi__v1.0.md`
- `docs/sora/prompts/hpp/p1_polish/smart_empty_states_pack__plate_progress__v1.0.md`
5. Keep P2 behind feature/campaign toggles.
P2 prompt files:
- `docs/sora/prompts/hpp/p2_expressive/tab_bar_active_trail_micro_motion__tabbar__v1.0.md`
- `docs/sora/prompts/hpp/p2_expressive/export_success_celebration_chip__progress__v1.0.md`
- `docs/sora/prompts/hpp/p2_expressive/seasonal_theme_accent_pack__home_progress__v1.0.md`

## 6) Security Notes

- Never include API keys, internal URLs, secrets, or credentials in prompts.
- Keep all generated visuals wellness-safe and non-clinical.
- Do not produce medical diagnosis/cure implication in image or copy.

## 7) Marketing and GTM Notes

Fast rollout path:

- ASO: use Elements 01, 03, 04 for screenshots and app-preview sequence.
- Product Hunt: publish before/after sets for Elements 02 and 07.
- Social short-form: reuse Element 01 ambient + Element 09 success chip loops.

Low-cost, no-license opportunities:

- visual wellness dashboard templates
- premium onboarding packs for other wellness creators
- prompt-based UI theme kits for lifestyle apps

## 8) Decision Log

- Proposals were derived from current route/component structure in
  `frontend/src/pages/*` and shared UI components.
- Priority favors visibility and perceived modernity with low risk to core UX.
- Prompt design follows current PulsePlate style lock and anti-drift policy.

## 9) Next Actions

- Convert P0 prompts into versioned prompt IDs in `docs/sora/prompts/`.
- Produce first candidate batch (3 variants each) for Elements 01-04.
- Run design QA checklist and attach accepted variants to implementation PRs.
- Use `docs/design/VISUAL_PR_DESCRIPTION_TEMPLATES.md` for per-visual PR body drafting.
