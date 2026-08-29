<!-- markdownlint-disable MD013 -->
# Apple Product Information Boundary Prompt Pack

Version: v1.1
Priority: P0
Surface: Web Plate + `/pro` compatibility information route
Target components:

- `frontend/src/components/PremiumGate.tsx`
- `frontend/src/components/AppleProductInfoDialog.tsx`

The filename is retained as compatibility metadata for existing design tooling.
It grants no current behavior, label, prompt, route, telemetry, Store, or entitlement authority.

## 1) Purpose

Review the existing information boundary for clarity, trust, and accessible
handoff to free Web tools and Apple-product marketing. Reuse the current Card,
Button, Link, focus-trap, tokens, and FitChef asset treatment. Do not create a
new asset, token, component family, image, illustration, or media output.

## 2) Exact Runtime Contract

- Stable Home ID: `web.home.open_pro`
- Stable Plate ID: `web.plate.premium_gate_cta`
- Label: `Learn about PulsePlate for Apple devices`
- Intent: `Open the information-only Apple product handoff`
- Variant: `V3` / secondary
- Home destination: `/marketing`
- Plate result: opens the existing `AppleProductInfoDialog`
- Prompt stub: `stub://cta/information/apple-product`
- Home node: `PP/Web/Home/GuidedPlanning/AppleProductInfo/Button/Default (TBD)`
- Plate node: `PP/Web/Plate/PremiumGate/AppleProductInfo/Button/Default (TBD)`

The stable identifier substrings are not action authority. Historical values
must not reappear as labels, destinations, state names, telemetry, or prompt meaning.

## 3) Composition Review Prompt

```text
Review the existing PulsePlate Apple-product information card and dialog.
Keep the composition luxury-clean, calm, text-first, and easy to scan.
Reuse the current semantic tokens, shared Card, shared Button/Link styling,
and existing focus behavior. Preserve one clear primary free-BMI action,
one secondary internal marketing action, and one neutral dialog dismissal.
Do not create or request any new image, illustration, icon family, token,
component family, external destination, async state, or artificial urgency.
Return implementation-review notes only; produce no media asset.
```

## 4) Layout Contract

- Keep the information card within the existing responsive max width.
- Keep the two internal links visible without relying on color alone.
- Keep the dialog close action at least 44 CSS px in both dimensions.
- Preserve initial focus on the free BMI link, keyboard containment, Escape,
  explicit dismissal, body-scroll restoration, and opener-focus return.
- Exact Web information state set: `default`, `hover`, `pressed`, `focus-visible`, `disabled`.

## 5) Negative Contract

```text
no countdown or urgency pattern
no external Store badge or unverified release claim
no price, trial, renewal, eligibility, or download claim
no async spinner, artificial latency, processing state, or error state
no fear, shame, transformation, clinical, or cure framing
no new media, token, component, icon family, or decorative asset
```

## 6) QA Gate

- Pass `docs/sora/SORA_STYLE_QA_CHECKLIST.md`.
- Pass `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`.
- Exact label, intent, V3 hierarchy, nodes, stub, and safe destinations match
  `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`.
- `/pro` remains an information card with internal `/bmi` and `/marketing` links.
- The Plate trigger opens the existing dialog and preserves all keyboard,
  screen-reader, focus-return, and scroll-restoration behavior.
- No external destination or acquisition telemetry is introduced.

<!-- markdownlint-enable MD013 -->
