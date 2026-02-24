<!-- markdownlint-disable MD013 -->
# Tab Bar Active Trail Micro-Motion Prompt Pack

Version: v1.0
Priority: P2
Surface: Web navigation
Target component:
- `frontend/src/components/TabBar.tsx`

## 1) Purpose

Add subtle active-tab motion polish that improves perceived responsiveness
without distracting from content.

## 2) Master Prompt (Sora)

```text
Create a minimal motion concept for active tab transition in premium app.
Smooth, soft, low-amplitude movement, no bounce exaggeration.
Visual language must remain clean and professional.
Provide storyboard frames only, not flashy animation.
```

## 3) Layout Prompt (Figma)

```text
Design active tab trail micro-motion spec for bottom navigation.
Motion should be subtle, under 220ms equivalent, reduced-motion fallback required.
Define active, inactive, pressed, and focus-visible states.
Do not use glow/neon effects.
```

## 4) Negative Prompt

```text
no jitter, no strobe, no elastic overshoot, no gaming HUD look
```

## 5) Controlled Variations

### Variant A - Soft Slide

```text
A short lateral trail with smooth easing and low visual amplitude.
```

### Variant B - Underline Drift

```text
A minimal underline drift animation with consistent timing and no glow.
```

### Variant C - Dot Track

```text
A compact active dot movement with static label/icon clarity.
```

## 6) QA Gate

- Pass `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- Pass `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- Reduced-motion fallback must be explicitly defined
- Active state remains clear in static mode
- Motion must not compete with primary content reading
