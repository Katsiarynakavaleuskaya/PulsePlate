<!-- markdownlint-disable MD013 -->
# Setup Completion Step Rail Prompt Pack

Version: v1.0
Priority: P1
Surface: Web Nutrition Setup (`/setup`)
Target components:
- `frontend/src/pages/NutritionSetup/SetupForm.tsx`
- `frontend/src/pages/NutritionSetup/ResultView.tsx`

## 1) Purpose

Add a modern, clear progress rail to reduce cognitive load across setup and result flow.

## 2) Master Prompt (Sora)

```text
Create a clean UI accent pack for setup progress steps in a wellness app.
Flat geometry, token-safe palette, low noise, strong hierarchy.
Generate micro-illustrative markers for 4 steps with consistent family style.
```

## 3) Layout Prompt (Figma)

```text
Design a horizontal/vertical step rail for Nutrition Setup flow.
Steps: Profile Input -> Validation -> Targets -> Result.
Show current step emphasis and completed steps with non-color indicators.
Keep compact mobile behavior and avoid breaking existing form rhythm.
```

## 4) Negative Prompt

```text
no cartoon overload, no emoji style, no rainbow palette,
no complex gradients that reduce label clarity
```

## 5) Controlled Variations

### Variant A - Horizontal Rail

```text
Desktop-first horizontal rail with concise labels and compact completion markers.
```

### Variant B - Vertical Rail

```text
Mobile-first vertical rail with clear active step and lightweight connectors.
```

### Variant C - Minimal Rail

```text
Ultra-minimal marker system with emphasis on current step and helper tooltip zone.
```

## 6) QA Gate

- Pass `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- Pass `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- Current step readable without color-only signals
- Compact mobile layout remains uncluttered
