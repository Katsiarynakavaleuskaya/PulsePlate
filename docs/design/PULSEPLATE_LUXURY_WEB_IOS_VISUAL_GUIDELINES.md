# PulsePlate Luxury Visual Guidelines (iOS + Web)

## Purpose

This document extends PulsePlate design documentation with practical, modern,
and usability-safe rules for building a premium ("luxury-clean") product look
on iOS and Web.

The objective is not "decorative luxury", but a trusted premium visual system:

- clear hierarchy
- calm and confident composition
- high accessibility
- consistent brand recognition across surfaces

## Canonical Brand Baseline

Use PulsePlate core style as the default:

- Mood: minimalism + cozy + intelligent + luxury-clean
- Palette:
  - Navy `#0F172A`
  - Blue `#339FFF`
  - Accent Green `#20C997`
  - Heart Red `#FF5D5D` (accent only)
- Visual style: flat forms, soft shadows, subtle gradients
- Mascot policy: FitChef is lifestyle and encouragement, never clinical

## Authoritative Sources (What to Apply)

### iOS / Apple

1. Apple Human Interface Guidelines
   - Link: [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines)
   - Apply: prioritize clarity, deference, and depth; design around native
     interaction expectations before adding visual effects.

2. Apple Design Resources
   - Link: [Apple Design Resources](https://developer.apple.com/design/resources)
   - Apply: keep component spacing/rhythm aligned with Apple references to
     avoid "almost native" visual mismatch.

3. Apple's "What's New" Design updates
   - Link: [Apple Design - What's New](https://developer.apple.com/design/whats-new)
   - Apply: review typography, color, and motion updates before major visual
     refreshes to keep the app modern on current iOS.

### Web / Accessibility / UX

1. web.dev Color and Contrast Accessibility
   - Link: [web.dev Color and Contrast Accessibility](https://web.dev/articles/color-and-contrast-accessibility)
   - Apply: keep text/background contrast at least WCAG AA and use color as a
     support signal, not the only signal.

2. web.dev Motion Accessibility
   - Link: [web.dev Motion Accessibility](https://web.dev/learn/accessibility/motion)
   - Apply: respect reduced motion preferences; avoid decorative motion that
     harms comfort or comprehension.

3. web.dev Accessibility Tips
   - Link: [web.dev Accessibility Tips](https://web.dev/articles/a11y-tips-for-web-dev)
   - Apply: ensure keyboard and screen-reader compatibility for all actionable
     UI elements.

4. W3C WCAG
   - Link: [W3C WCAG](https://www.w3.org/WAI/standards-guidelines/wcag/)
   - Apply: map key screens to perceivable/operable/understandable principles,
     especially onboarding, paywall, and metrics cards.

## Practical Rules for Premium Segment

### 1) Typography

- Use a restrained hierarchy: one display level, one section heading level,
  one body level, one meta level.
- Avoid dense uppercase and decorative type for core UX content.
- Keep premium tone through spacing and weight contrast, not font noise.
- iOS: respect Dynamic Type scaling; no clipped labels in compact widths.
- Web: define stable scale tokens and lock line-height per text role.

### 2) Color and Material

- Navy should carry depth and trust; Blue/Green should carry action and progress.
- Heart Red should be sparse and meaningful (critical state/emphasis only).
- Use gradients as subtle depth signals, never as dominant decoration.
- Keep shadow softness consistent across cards, dialogs, and navigation surfaces.

### 3) Composition and Spacing

- Prefer one dominant focal area per screen.
- Use controlled negative space to signal confidence and "premium calm."
- Do not fill every gap with icons, badges, or decorative labels.
- Keep card rhythm consistent (title -> value -> helper text -> action).

### 4) Motion

- Motion communicates hierarchy/state change, not "show."
- Cap duration for micro-interactions; avoid heavy choreography in task flows.
- Respect `prefers-reduced-motion` on web and equivalent comfort behavior on iOS.
- No distracting loops near primary CTA or result values.

### 5) Iconography

- Icon style must stay uniform by stroke, corner radius, and simplification level.
- Every icon must remain legible at small sizes (24/32 px web, compact iOS use).
- Avoid mixed visual families (outline + filled + pseudo-3D in same context).
- Do not use ambiguous medical symbols in wellness-only contexts.

### 6) Accessibility as Luxury Multiplier

- High contrast and clean hierarchy are premium signals, not compromises.
- Support larger text and assistive navigation from the start.
- Ensure all key states are distinguishable without color dependency.
- Verify touch/click targets remain generous in dense screens.

## Screen-Specific Guidance

### Onboarding

- One message per screen, one visual anchor, one clear CTA.
- FitChef may provide warmth, but must not compete with onboarding objective.
- Avoid generic stock-like wellness scenes; keep branded geometry/palette cues.

### Paywall

- Premium tone should communicate confidence, not pressure.
- Highlight value with structural clarity (tiers/benefits), not bright noise.
- Keep legal/plan details readable and calm.

### Home / Progress Cards

- Keep data first, decoration second.
- Use color to reinforce meaning (progress/state), not to maximize saturation.
- Maintain consistent card anatomy across modules for cognitive ease.

## Negative UX Prevention Matrix

Use this matrix during design review and prompt planning.

- **Neon/acid palette drift**
  - Design rule: Keep only canonical palette and muted gradients.
  - Prompt guard: `no neon, no acid colors, palette locked`
- **Visual clutter**
  - Design rule: One focal object and controlled negative space.
  - Prompt guard: `single focal center, low clutter`
- **Generic AI "slop" look**
  - Design rule: Prefer clean geometry and stable depth cues.
  - Prompt guard: `no generic ai slop, no glossy blobs`
- **Clinical/medical vibe**
  - Design rule: Wellness lifestyle framing only.
  - Prompt guard: `wellness lifestyle, not medical`
- **Overly dramatic imagery**
  - Design rule: Calm, confident, supportive emotional tone.
  - Prompt guard: `no fear, no panic, no dramatic hospital mood`
- **Unreadable icons**
  - Design rule: Enforce small-size silhouette clarity.
  - Prompt guard: `high small-size readability, clear silhouette`
- **Inconsistent mascot**
  - Design rule: Keep FitChef shape/mood continuity.
  - Prompt guard: `consistent FitChef style and expression`
- **Motion discomfort**
  - Design rule: Limit motion intensity and duration.
  - Prompt guard: `slow smooth motion, no jitter, no flashes`
- **Color-only status meaning**
  - Design rule: Add structure, labels, and icon support.
  - Prompt guard: `status must be clear without color dependency`
- **Tiny touch targets**
  - Design rule: Keep platform minimum interaction areas.
  - Prompt guard: `large tappable controls, avoid tiny UI elements`
- **Social ad manipulation tone**
  - Design rule: Use informative and respectful value messaging.
  - Prompt guard: `no manipulative urgency or miracle framing`
- **Competitor-like visuals**
  - Design rule: Preserve distinctive PulsePlate visual identity.
  - Prompt guard: `no copycat look, no brand imitation`

## Social Promotion Visual Safeguards

### Creative intent rules

- Visuals must educate or motivate, not pressure users emotionally.
- Avoid body-shaming, miracle transformation narratives, and fear framing.
- Keep wellness language grounded in lifestyle habits, not treatment claims.

### Platform-ready quality rules

- First frame must communicate value in less than 2 seconds.
- CTA clarity is required but must remain calm and non-aggressive.
- Validate visual legibility in mobile feed conditions before release.

### Consistency rules (product -> social)

- Social creatives must map to in-app visual DNA (palette, tone, icon style).
- If FitChef is used, personality must match product behavior.
- Do not publish social visuals that could not pass in-app quality gates.

## Quality Gate Checklist (Design Review)

Mark release candidate pass only when all are true:

1. Brand palette lock preserved
2. Typographic hierarchy clear at first glance
3. Small-size icon legibility confirmed
4. Motion supports understanding and respects reduced-motion preference
5. Contrast and accessibility checks pass for core screens
6. Onboarding and paywall visuals feel premium but not manipulative
7. No clinical/diagnostic implication in wellness visuals
8. Negative UX matrix risks are reviewed and mitigated
9. Social promotion safeguards are satisfied for campaign creatives

## Integration Notes

- Sora prompt process and anti-drift controls:
  `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- Sora skill specification:
  `docs/sora/SKILL_PULSEPLATE_SORA_PROMPT_ENGINEERING.md`

Use this document for visual governance decisions in iOS/Web feature PRs that
impact perceived product quality.
