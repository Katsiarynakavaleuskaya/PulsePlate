<!-- markdownlint-disable MD013 -->
# Export Success Celebration Chip Prompt Pack

Version: v1.0
Priority: P2
Surface: Web Progress export
Target component:
- `frontend/src/features/progress/ProgressCharts.tsx`

## 1) Purpose

Add compact success feedback after export actions to reinforce completion
without celebratory noise.

## 2) Master Prompt (Sora)

```text
Create a tiny celebratory success accent pack for PDF export completion.
Mood: calm achievement, not confetti party.
Generate 2 icon accents and 1 subtle background swash,
all token-safe and small-size legible.
```

## 3) Layout Prompt (Figma)

```text
Design a compact success chip/toast for export completion.
Use positive but restrained emphasis and fast dismissal behavior.
Include icon, short copy area, and optional open-file action affordance.
Keep mobile-safe width and avoid overlap with key charts.
```

## 4) Negative Prompt

```text
no fireworks/confetti overload, no loud gradients,
no intrusive full-screen celebration
```

## 5) Controlled Variations

### Variant A - Quiet Toast

```text
Minimal toast with icon + one-line success copy zone.
```

### Variant B - Action Toast

```text
Success chip with optional secondary action affordance.
```

### Variant C - Inline Badge

```text
Inline compact success badge aligned near export control.
```

## 6) QA Gate

- Pass `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- Legible in narrow mobile viewport
- No overlap with chart critical content
- Tone remains professional and unobtrusive
