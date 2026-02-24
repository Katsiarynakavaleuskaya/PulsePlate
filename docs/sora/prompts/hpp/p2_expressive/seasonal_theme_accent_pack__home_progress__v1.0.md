<!-- markdownlint-disable MD013 -->
# Seasonal Theme Accent Pack Prompt Pack

Version: v1.0
Priority: P2
Surface: Web Home + Progress
Target components:
- `frontend/src/pages/Home.tsx`
- `frontend/src/pages/Progress.tsx`

## 1) Purpose

Enable campaign freshness with optional seasonal accents while preserving
PulsePlate core brand identity and token semantics.

## 2) Master Prompt (Sora)

```text
Create four subtle seasonal ambient accent concepts for wellness app cards.
Each concept must preserve PulsePlate style DNA and token-safe hierarchy.
No holiday clichés, no mascot distortion, no palette override.
Output static accents that can be toggled per campaign.
```

## 3) Layout Prompt (Figma)

```text
Design a seasonal accent pack that overlays existing PulsePlate UI
without changing core token identities.
Create spring/summer/autumn/winter accent suggestions using token semantics,
not raw custom palette drift. Keep all accents optional and removable.
```

## 4) Negative Prompt

```text
no holiday costume clichés, no palette replacement,
no excessive decorative objects, no brand identity drift
```

## 5) Controlled Variations

### Variant A - Spring Clarity

```text
Fresh but restrained accent geometry with high readability retention.
```

### Variant B - Summer Energy

```text
Slightly warmer accent rhythm while preserving baseline card hierarchy.
```

### Variant C - Autumn Depth / Winter Calm

```text
Two low-intensity depth variants with identical component spacing behavior.
```

## 6) QA Gate

- Pass `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- Base UI remains clearly recognizable as PulsePlate
- Accents are feature-toggle friendly and removable with zero layout shift
- No token drift beyond approved SoT semantics
