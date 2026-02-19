<!-- markdownlint-disable MD013 -->
# PulsePlate HPP Prompt Pack (P2)

Version: v1.0
Scope: Home + Plate + Progress visual assets

## 1) Style Lock (fixed across variants)

- Mood: minimal + cozy + intelligent + luxury-clean
- Palette:
  - Navy `#0F172A`
  - Blue `#339FFF`
  - Accent Green `#20C997`
  - Heart Red `#FF5D5D` (accent only)
- Mascot: FitChef is lifestyle-friendly, non-clinical
- Rendering: flat + soft shadow + subtle gradient

## 2) Master Prompt Template

Use this for release candidates:

```text
Create a PulsePlate visual for {surface} in a minimalist iOS-first wellness style.
Keep strict palette tokens: Navy #0F172A, Blue #339FFF, Accent Green #20C997,
Heart Red #FF5D5D as accent only. The mood is cozy, intelligent, and premium-clean.
Use flat forms, soft shadows, and subtle gradients. Preserve clear visual hierarchy:
primary action first, supporting metric second, background calm and low-noise.
FitChef mascot, if present, must appear friendly and lifestyle-oriented, never clinical.
Output ratio: {ratio}. Focus: {goal}. Keep text-safe regions and no micro-details.
```

## 3) Nano Prompt Template

Use this for rapid iteration:

```text
PulsePlate {surface}, minimalist cozy wellness, palette-locked (#0F172A #339FFF #20C997 #FF5D5D accent), flat + soft shadow, premium-clean hierarchy, FitChef non-clinical.
```

## 4) Negative Prompt (mandatory)

```text
No neon cyberpunk, no purple-gold luxury drift, no medical diagnosis imagery,
no hospital devices, no fear/shame framing, no unreadable micro-textures,
no inconsistent mascot style.
```

## 5) Controlled Variations

What stays fixed:

- palette tokens
- hierarchy and tone
- safety constraints

What changes:

- composition density
- CTA emphasis
- background texture level

### Variation A: Compact Utility

```text
Create a compact utility-focused card visual for {surface}, with minimal decorative
noise, strong CTA readability, and calm metric support.
```

### Variation B: Emphasized Conversion

```text
Create an emphasized conversion-oriented visual for {surface}, where primary action
is visually dominant and metric context remains secondary but clear.
```

### Variation C: Balanced Trust

```text
Create a balanced trust-oriented visual for {surface}, blending calm data context
with a gentle premium feel and accessible CTA prominence.
```

## 6) Required QA Link

Before release, validate output with:

- `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
