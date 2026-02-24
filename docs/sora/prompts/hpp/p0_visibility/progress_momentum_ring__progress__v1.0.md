<!-- markdownlint-disable MD013 -->
# Progress Momentum Ring Prompt Pack

Version: v1.0
Priority: P0
Surface: Web Progress (`/progress`)
Target components:
- `frontend/src/pages/Progress.tsx`
- `frontend/src/features/progress/LiveProgressIndicator.tsx`

## 1) Purpose

Add a modern momentum signal that reinforces progress without clinical tone.

## 2) Master Prompt (Sora)

```text
Create a premium flat-style progress ring visual pack for wellness app UI.
Mood: calm confidence, trustworthy analytics, not medical.
Palette lock: navy/blue/green with tiny red accent only when needed.
Generate 4 variants for progress states with identical geometry base.
Output transparent PNG sprites and one subtle ring pulse animation idea.
```

## 3) Layout Prompt (Figma)

```text
Design a momentum ring component plus compact weekly streak badge.
Component must fit existing Progress cards and preserve hierarchy.
Use tokenized levels: primary progress, secondary label, helper text.
Provide states: default, improving, stable, recovering.
Keep icons legible at small size and avoid clinical semantics.
```

## 4) Negative Prompt

```text
no gamified casino look, no warning-heavy red dominance,
no tiny unreadable numbers, no generic fitness tracker clone
```

## 5) Controlled Variations

### Variant A - Precision Analytics

```text
Use stricter geometry with minimal gradients and stronger ring edge clarity.
```

### Variant B - Gentle Momentum

```text
Add soft inner glow equivalent using token-safe tone with low amplitude pulse.
```

### Variant C - Streak Emphasis

```text
Keep ring identical, add compact streak badge with non-color status marker.
```

## 6) QA Gate

- Pass `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- Ring readable at 24/32 px preview
- State meaning distinguishable without color-only encoding
- No medical or diagnostic visual cues
