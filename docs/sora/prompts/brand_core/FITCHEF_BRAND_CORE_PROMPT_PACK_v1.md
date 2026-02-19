<!-- markdownlint-disable MD013 -->
# FitChef Brand-Core Prompt Pack (v1.0)

Version: v1.0
Scope: Brand core wave (`character`, `logo_icon`, `micro_motion`)
Mode: Hybrid (`ui-flat` for product, `marketing-hybrid` for campaigns)

## 1) Canonical Constraint Block (SoT)

Use these constraints in every prompt family below.

### Style and tone lock (mandatory)

- Mood: minimal + cozy + intelligent + luxury-clean
- Palette lock (canonical): `#0F172A` `#339FFF` `#20C997` `#FF5D5D` (accent only)
- Rendering: flat forms + soft shadows + subtle gradients
- Composition: one focal center, low clutter, high small-size readability
- Mascot semantics: FitChef is lifestyle-friendly, non-clinical, trust-first
- Safety semantics: no diagnosis/cure framing, no fear/shame manipulation

### Product token mapping (web/iOS alignment)

- Web token SoT: `frontend/src/styles/tokens.ts`, `frontend/src/styles/tokens.css`
- iOS token SoT: `ios/PulsePlate/Assets.xcassets/*`, `ios/PulsePlate/Extensions/Color+Assets.swift`
- Do not replace canonical brand lock with local token aliases inside prompts.

### Global negative clauses (mandatory)

```text
No neon cyberpunk, no purple-gold luxury drift, no glossy 3D blobs, no hospital equipment, no diagnosis/cure implication, no fear/shame framing, no copycat competitor style, no noisy micro-textures, no unreadable tiny details.
```

## 2) FitChef Identity SoT (for likeness stability)

Canonical identity rules live in:

- `docs/sora/prompts/brand_core/FITCHEF_IDENTITY_PROFILE_v1.md`

Use this pack as execution guidance only. Do not redefine morphology or expression rules here.

## 3) Prompt Family A - Image: FitChef Character System

### Goal A

Create primary mascot visuals for product screens and marketing surfaces while preserving high likeness to the real FitChef prototype.

### Master prompt A

```text
Create a PulsePlate FitChef mascot image in hybrid style: UI-flat precision with natural tabby-cat likeness. Keep strict palette lock (#0F172A #339FFF #20C997 with #FF5D5D accent only). Mood: cozy, intelligent, luxury-clean. FitChef must look like a real tabby with white chest and white paws, warm amber eyes, pink nose, clean striped mask, compact friendly silhouette. Composition: single focal center, low clutter, high readability at small size, clean negative space. Render with flat forms, soft shadows, subtle gradients, and stable line simplification. Tone must be supportive and non-clinical wellness.
```

### Negative prompt A

```text
No neon palette, no purple-gold drift, no hyper-real gritty fur noise, no glossy 3D plastic look, no hospital or medical context, no fear/shame messaging, no distorted cat anatomy, no inconsistent eye shape or fur pattern, no tiny unreadable details.
```

### Variation 1 - `ui-flat`

```text
Create FitChef as a UI anchor avatar for app cards: front-facing bust, simplified geometry, crisp silhouette, minimal background, strong 24px/32px readability, non-clinical and calm.
```

### Variation 2 - `marketing-hybrid`

```text
Create FitChef hero portrait for social/launch card: slightly richer fur texture while keeping flat visual language, warm confident expression, navy-first background, premium-clean composition, no visual noise.
```

### Variation 3 - `hero-trust-anchor`

```text
Create FitChef in a trust-anchor scene: seated posture, subtle head tilt, gentle eye contact, one soft accent element only, generous negative space for optional copy overlay.
```

### QA checks A (pass/fail)

- PASS if cat morphology matches identity profile (eyes/chest/paws/mask/silhouette)
- PASS if palette remains canonical and accent red is sparse
- PASS if output works at small avatar size without detail collapse
- FAIL if mascot resembles a different species/style family
- FAIL if visual tone becomes clinical, manipulative, or noisy

## 4) Prompt Family B - Image: PulsePlate Logo/Icon Core

### Goal B

Generate icon/logo candidates that keep continuity with current plate-based logo reference and FitChef brand DNA.

### Master prompt B

```text
Create a PulsePlate app icon/logo concept derived from the existing plate-heart pulse idea, with optional FitChef integration in a clean iOS-first style. Keep strict palette lock (#0F172A #339FFF #20C997 and #FF5D5D accent only). Prioritize one dominant symbol, clean geometry, strong border contrast, and recognition at 60/120/1024 sizes. Keep composition centered and uncluttered. If FitChef appears, keep the same character identity rules (tabby + white chest/paws + amber eyes) and avoid over-detail.
```

### Negative prompt B

```text
No text labels, no tiny ornaments, no copycat of existing competitor icons, no metallic chrome effects, no purple/gold drift, no medical cross or diagnostic monitor motifs, no chaotic multi-symbol composition.
```

### Variation 1 - `icon-1024-hero`

```text
Create a 1024 master icon with plate + pulse core symbol as dominant element and subtle FitChef cue; maximize premium clarity and immediate brand recognition.
```

### Variation 2 - `icon-120-mid`

```text
Create a 120-size optimized icon variant with simplified contours and stronger silhouette separation for App Store list readability.
```

### Variation 3 - `icon-60-compact`

```text
Create a compact 60-size icon variant prioritizing bold shape recognition, minimal inner detail, and clean edge definition.
```

### QA checks B (pass/fail)

- PASS if the symbol remains recognizable at 60/120/1024 previews
- PASS if visual hierarchy is single-center and uncluttered
- PASS if plate/pulse meaning stays clear without medical framing
- FAIL if icon needs text to be understood
- FAIL if small-size preview loses symbol integrity

## 5) Prompt Family C - Animation: FitChef Micro-Motions (Short Clips)

### Goal C

Generate short mascot micro-motions for iOS/web surfaces that feel calm, premium, and accessibility-safe.

### Master prompt C

```text
Create a short PulsePlate FitChef micro-animation with smooth, calm motion and stable mascot identity. Keep palette lock (#0F172A #339FFF #20C997 with #FF5D5D accent only), flat forms, soft shadows, subtle gradients, low clutter background, and one focal subject. Motion must be gentle, no flashing, no jitter, no abrupt cuts, and reduced-motion-friendly by design. FitChef likeness must remain consistent frame-to-frame (tabby mask, white chest/paws, amber eyes, compact silhouette). Tone: supportive wellness, never medical.
```

### Negative prompt C

```text
No rapid strobe, no aggressive zoom shake, no hyperactive loops, no clinical monitor scenes, no fear-shock expressions, no anatomy drift between frames, no oversaturated neon.
```

### Variation 1 - `blink`

```text
Create a 2-4 second loop: FitChef gentle blink with minimal head movement, smooth easing, clean idle pose, and stable expression.
```

### Variation 2 - `paw-wave`

```text
Create a 3-5 second loop: FitChef small friendly paw-wave, restrained amplitude, smooth in/out timing, no exaggerated cartoon bounce.
```

### Variation 3 - `calm-breath-pulse`

```text
Create a 3-6 second loop: FitChef subtle breathing rhythm with faint pulse-ring accent in background, slow and soothing, reduced-motion-safe variant implied.
```

### QA checks C (pass/fail)

- PASS if motion is smooth and calm (no jitter/flash)
- PASS if mascot identity is consistent across keyframes
- PASS if animation supports comprehension, not distraction
- FAIL if loop feels intrusive near CTA/data contexts
- FAIL if reduced-motion fallback cannot be derived from asset

## 6) Fixed-vs-Variable Matrix

| Layer | Fixed (must not change) | Variable (controlled) |
| --- | --- | --- |
| Palette | `#0F172A #339FFF #20C997 #FF5D5D(accent)` | Accent intensity within safe limits |
| Mascot morphology | Tabby mask, white chest/paws, amber eyes, pink nose, compact silhouette | Pose, camera angle, micro-expression |
| Tone | Calm, supportive, wellness-not-medical | Scene context (product vs marketing) |
| Style | Flat + soft shadow + subtle gradient | Texture richness (only in marketing-hybrid) |
| Composition | One focal center, low clutter | Negative space amount, background depth |
| Motion | Smooth, no flash, no jitter | Loop length and amplitude within comfort band |

## 7) Failure Tag SoT

Use canonical failure tags from:

- `docs/sora/SORA_STYLE_QA_CHECKLIST.md`

Do not introduce local tag aliases in this file.

## 8) Release-Ready Gate

Candidate is release-ready only if all checks pass:

1. Passes `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
2. Passes `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
3. Keeps FitChef likeness stable versus provided photo references
4. No policy violations (medical, manipulative, copycat, secret leak)
5. Icon and mascot remain readable in target deployment sizes
