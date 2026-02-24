<!-- markdownlint-disable MD013 -->
# Home Hero Ambient Prompt Pack

Version: v1.0
Priority: P0
Surface: Web Home (`/`)
Target component: `frontend/src/pages/Home.tsx`

## 1) Purpose

Create a premium ambient hero layer that increases first-screen visibility
without reducing CTA readability.

## 2) Master Prompt (Sora)

```text
PulsePlate style lock: minimal, cozy, intelligent, luxury-clean.
Create a subtle ambient hero background loop for wellness dashboard.
Soft navy depth, quiet blue gradient flow, tiny green accent spark,
single focal center, no text, no character faces, no medical symbols.
Motion: very slow 6-8 second breathing gradient, reduced-motion safe static frame.
Output: clean PNG keyframe + optional short MP4 loop.
```

## 3) Layout Prompt (Figma)

```text
Design a Home hero ambient background for PulsePlate web.
Use one dominant focal area behind title and subtitle, luxury-clean, low clutter.
Use token semantics: --pp-navy base, --pp-blue support gradient,
--pp-green minimal accent. Keep CTA readability as first priority.
Include desktop and mobile variants. Return reduced-motion fallback notes.
```

## 4) Negative Prompt

```text
no neon, no cyberpunk, no purple/gold drift, no glossy 3d blobs,
no visual noise, no dramatic contrast spikes, no hospital mood
```

## 5) Controlled Variations

### Variant A - Calm Depth

```text
Increase navy depth and reduce accent count to one subtle highlight point.
```

### Variant B - Soft Gradient Flow

```text
Keep same composition, add one low-amplitude curved gradient trail behind heading area.
```

### Variant C - Conversion Focus

```text
Keep center clean near primary CTA zone, reduce background texture by 20-30 percent.
```

## 6) QA Gate

- Pass `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- Pass `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- Keep CTA text contrast readable in mobile preview
- Keep reduced-motion static fallback
