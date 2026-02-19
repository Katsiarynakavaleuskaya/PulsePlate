# Sora Style QA Checklist (Pass/Fail)

Version: v1.1
Scope: PulsePlate HPP + Brand Core asset candidates (images + micro-motions)

Use this checklist before approving any generated visual.

## Brand and Style

- [ ] PASS if only canonical palette tokens are used
- [ ] PASS if hierarchy is clear (primary action > metric > decoration)
- [ ] PASS if FitChef style remains consistent and non-clinical
- [ ] FAIL if visual drifts into generic AI aesthetics (neon/cyberpunk/purple-gold)

## Safety and Compliance

- [ ] PASS if no medical diagnosis/cure implication appears
- [ ] PASS if tone is wellness-safe and trust-first
- [ ] FAIL if fear/shame manipulation is present
- [ ] FAIL if internal secrets/URLs appear in text overlays or metadata

## Usability and Accessibility

- [ ] PASS if CTA region is visually readable at small-size preview
- [ ] PASS if contrast appears sufficient for core text/CTA
- [ ] FAIL if micro-detail makes information unreadable in app contexts
- [ ] FAIL if key affordances are visually ambiguous

## Motion Comfort (for animated assets)

- [ ] PASS if motion is smooth and purposeful (no jitter/strobe/harsh cuts)
- [ ] PASS if reduced-motion-safe fallback is possible
- [ ] FAIL if loop distracts from primary CTA or key metric reading
- [ ] FAIL if frame-to-frame mascot identity drifts

## Variation Control

- [ ] PASS if fixed elements remain fixed across A/B/C variants
- [ ] PASS if only declared variation axes changed
- [ ] FAIL if variant introduces undocumented style or token drift

## Evidence and Decision

- [ ] PASS if prompt id and version are recorded
- [ ] PASS if decision rationale is captured (`approved` / `rejected`)
- [ ] PASS if rejected artifacts include failure reason tags

## Failure Reason Tags

Use one or more:

- `palette_drift`
- `mascot_drift`
- `safety_violation`
- `readability_failure`
- `hierarchy_failure`
- `undocumented_variation`
- `motion_discomfort`
- `small_size_failure`
- `logo_semantic_drift`
