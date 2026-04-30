<!-- markdownlint-disable MD013 -->
# Synthesis Decision

**Date:** 2026-04-30

## Decision

Keep `MrztJU3CQtxhADBbtAsWJ6` as `reference_only` and use it to shape a
repo-first design handoff. Do not implement runtime web/iOS changes in this PR.
Do not write to Figma or Canva in this PR.

## Design Direction To Carry Forward

- Web launch: use the luxury-clean composition, but rebuild from repo routes,
  repo components, and repo token mirrors.
- Home: carry forward the premium but practical product framing and dashboard
  preview idea.
- Plate: carry forward the daily summary + meal timeline hierarchy.
- Progress: carry forward segmented range control and chart-forward layout.
- iOS: carry forward card, tab, and touch-target grammar only after SwiftUI
  lane opens.
- GTM: carry forward privacy/cancel-anytime/wellness-safe trust notes, not
  unsupported social proof.

## Blockers

- Missing canonical Figma Design URL/node IDs for Make-to-Design promotion.
- Make screenshot unsupported by available MCP screenshot tool.
- Computer Use not callable in this session.
- Runtime implementation intentionally deferred.

## Follow-Up PR Order

1. web launch shell/design polish
2. iOS bounded design polish for Home / Plate / Progress
3. Figma Design promotion and node capture
4. Canva launch asset kit

## Security Notes

No external reference tool is trusted as runtime authority. No new data capture,
billing, auth, API, or deployment behavior is authorized.

## Marketing And GTM

Future launch copy must avoid unsupported proof claims and medical framing.
Use wellness lifestyle language and verified store/billing truth only.
