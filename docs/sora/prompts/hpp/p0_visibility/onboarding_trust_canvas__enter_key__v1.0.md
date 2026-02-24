<!-- markdownlint-disable MD013 -->
# Onboarding Trust Canvas Prompt Pack

Version: v1.0
Priority: P0
Surface: Web Enter Key (`/enter-key`)
Target component: `frontend/src/pages/Onboarding/EnterKey.tsx`

## 1) Purpose

Strengthen onboarding trust impression for key-entry flow with a modern premium canvas.

## 2) Master Prompt (Sora)

```text
Create onboarding trust background artwork for wellness app key setup.
Mood: calm, intelligent, privacy-safe, premium minimal.
No literal locks or cliché cybersecurity icons; use abstract trust geometry.
Use token-safe navy/blue base with minimal green confirmation accents.
Produce static hero plus optional ultra-subtle motion variant.
```

## 3) Layout Prompt (Figma)

```text
Design an onboarding trust canvas behind API key entry flow.
Must feel secure, premium, and simple.
Composition: one calm visual anchor, clear form focus, no decorative overload.
Include states: initial, validation in progress, success, invalid key.
Provide accessibility notes for focus order and contrast.
```

## 4) Negative Prompt

```text
no hacker visuals, no matrix code rain, no fear security aesthetics,
no clinical cross symbols, no heavy texture noise
```

## 5) Controlled Variations

### Variant A - Minimal Trust Geometry

```text
Abstract geometric trust motif with low-contrast navy layers.
```

### Variant B - Validation Flow Accent

```text
Add subtle green confirmation path that does not compete with form field focus.
```

### Variant C - Static Comfort Mode

```text
No motion, static composition optimized for reduced-motion mode.
```

## 6) QA Gate

- Pass `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- Form field remains first focal object
- Validation states remain clear without flashing/motion stress
- No security fear framing in artwork
