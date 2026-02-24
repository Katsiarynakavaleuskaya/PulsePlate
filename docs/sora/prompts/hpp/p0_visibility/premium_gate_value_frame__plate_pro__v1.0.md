<!-- markdownlint-disable MD013 -->
# Premium Gate Value Frame Prompt Pack

Version: v1.0
Priority: P0
Surface: Web Plate + Pro Paywall (`/plate`, `/pro`)
Target components:
- `frontend/src/components/PremiumGate.tsx`
- `frontend/src/components/Paywall/BeforeAfter.tsx`

## 1) Purpose

Improve premium conversion visibility while preserving calm, trust-first tone.

## 2) Master Prompt (Sora)

```text
Create a premium wellness paywall hero visual for a modern app modal.
Style: luxury-clean flat depth, soft shadow, subtle gradient, low clutter.
Scene should communicate capability unlock and personal guidance confidence,
never fear or deficiency. No text baked into image.
Output 3 controlled variants for A/B testing.
```

## 3) Layout Prompt (Figma)

```text
Design a premium value frame for locked content surfaces.
Structure: title, value bullets, trust microcopy, primary and secondary actions.
Tone: confident and respectful, no urgency pressure pattern.
Use existing PulsePlate button hierarchy and spacing rhythm.
Return desktop/mobile frame with focus-visible states.
```

## 4) Negative Prompt

```text
no countdown urgency, no fear body imagery, no miracle transformation,
no aggressive sales style, no medical cure implication
```

## 5) Controlled Variations

### Variant A - Trust Anchor

```text
Use one central trust object and minimal decorative gradients.
```

### Variant B - Capability Unlock

```text
Increase visual emphasis on unlock metaphor without literal lock icons.
```

### Variant C - Calm Premium

```text
Lower contrast accents, stronger whitespace around CTA area.
```

## 6) QA Gate

- Pass `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- Primary CTA remains dominant and readable
- Emotional tone remains supportive (no pressure/fear)
- No manipulative language in paired UI copy
