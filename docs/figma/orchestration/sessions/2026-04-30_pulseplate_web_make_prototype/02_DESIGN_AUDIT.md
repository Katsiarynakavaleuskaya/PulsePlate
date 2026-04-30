<!-- markdownlint-disable MD013 -->
# Design Audit: Figma Make PulsePlate_Web

**Date:** 2026-04-30
**Source:** `https://www.figma.com/make/MrztJU3CQtxhADBbtAsWJ6/PulsePlate_Web?p=f&t=5PkAftKeomh11x3R-0&fullscreen=1`

## Evidence Captured

Figma MCP `get_design_context` succeeded for:

```text
fileKey=MrztJU3CQtxhADBbtAsWJ6
nodeId=0:1
```

It returned Make source resources, including application shell, landing, Home,
Plate, Progress, iOS demo views, token CSS, design guide, and governance notes.

Figma MCP `get_screenshot` did not support the Make root. The packet therefore
uses source-context evidence rather than screenshot evidence for this pass.

## Useful Design Direction

- Keep the launch composition idea: hero, trust strip, feature grid,
  how-it-works, dashboard preview, pricing, FAQ, and final CTA.
- Preserve the clear Home / Plate / Progress product spine.
- Use Plate as a dense but scannable data surface: day header, summary,
  macros, meal timeline, add-meal affordance, and contextual tip.
- Use Progress as a chart-forward surface with a visible range control and
  consistent state framing.
- Use iOS prototype surfaces only to inform SwiftUI card/tab/spacing grammar.
- Use FitChef as a wellness assistant, not as a medical or therapy agent.

## Drift Findings

| Finding | Evidence | Required handling |
| --- | --- | --- |
| Prototype shell uses view toggles and localStorage BMI bootstrap | `src/app/App.tsx` | Do not copy runtime architecture |
| Unsupported public proof claims appear in landing copy | `src/app/components/landing-page.tsx` | Rewrite or verify before launch |
| Touch target guidance may conflict with repo web sizing decisions | Make design guide and historical Make audit | Resolve in implementation packet before UI edits |
| Make token aliases are not runtime SoT | `src/styles/tokens.css` | Repo token mirrors win |
| Pricing and feature lists are draft copy | `landing-page.tsx` | Check monetization contracts before use |
| Figma Design node IDs are missing | Make-only URL | Keep blocked by Design URL/node capture |

## Canva Direction

Canva can support:

- launch moodboard
- Product Hunt/social tile direction
- App Store screenshot storyboard reference
- campaign copy/layout exploration

Canva must not define runtime UI, pricing, billing truth, App Store privacy
truth, or production visuals without a future asset PR.
