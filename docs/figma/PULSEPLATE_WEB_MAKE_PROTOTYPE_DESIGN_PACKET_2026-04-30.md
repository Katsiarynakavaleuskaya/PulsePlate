<!-- markdownlint-disable MD013 -->
# PulsePlate Web Make Prototype Design Packet

**Date:** 2026-04-30
**Branch:** `codex/design-prototype-canvas-packet-v1`
**Status:** `reference_only`
**Mode:** design-only packet; no runtime code, backend, iOS, web, Figma write, Canva generation, or Code Connect activation
**Local heavy gate:** `make verify` deferred by operator CPU override; draft PR only until current-head CI and merge-readiness gates are satisfied

## 1. Summary

This packet reopens the PulsePlate prototype-design lane after PR #1581 merged.
The goal is to use the Figma Make `PulsePlate_Web` prototype, Figma evidence,
and Canva launch references as design-direction inputs while keeping repo code,
docs, tests, and token mirrors as the source of truth.

This lane documents what the prototype is useful for, where it drifts from the
runtime product, and which follow-up PRs should implement web/iOS polish after
the design direction is accepted.

## 2. Coordinator Packet

| Field | Value |
| --- | --- |
| `task_packet_id` | `72f36df2d589` |
| `design_source` | `figma_make` |
| `source_url` | `https://www.figma.com/make/MrztJU3CQtxhADBbtAsWJ6/PulsePlate_Web?p=f&t=5PkAftKeomh11x3R-0&fullscreen=1` |
| `file_key_or_workspace` | `MrztJU3CQtxhADBbtAsWJ6` |
| `node_id_or_frame_id` | `make-root (nodeId=0:1)` |
| `target_surface` | `web_ios_launch_design_direction` |
| `task_mode` | `verify` |
| `figma_lane_tool` | `figma_native` |
| `code_native_design_brief_required` | `true` |
| `code_native_design_brief_path` | `docs/figma/PULSEPLATE_WEB_MAKE_PROTOTYPE_DESIGN_PACKET_2026-04-30.md` |
| `design_blockers` | `blocked_by_design_url`, `blocked_by_node_id_capture` |

Coordinator role order for this lane:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer` reference review
4. `app-store-release-agent` advisory
5. `monetization-gtm` advisory
6. `qa-engineer-agent`
7. `bug-hunter`

Required skills used for this packet:

- `pulseplate-workflow`
- `pulseplate-design-launch-system`
- `pulseplate-frontend-ui`
- `pulseplate-playwright-e2e`
- `pulseplate-web-launch-site`
- `pulseplate-agent-product`
- `pulseplate-monetization-gtm`
- `pulseplate-app-store-release`

## 3. Source Precedence

If the prototype, Figma, Canva, code, or docs disagree, use this order:

1. repo code, docs, tests, runtime contracts, and governed design docs
2. repo token/component mirrors:
   - `frontend/src/styles/tokens.css`
   - `frontend/src/styles/tokens.ts`
   - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
   - `ios/PulsePlate/DesignSystem/DesignTokens.swift`
3. existing design authority packets:
   - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
   - `docs/design/TOKENS_SOT.md`
   - `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
   - `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md`
4. canonical Figma Design file `2JDwOByQIbcPgp93FDzHii`
5. Figma Make file `MrztJU3CQtxhADBbtAsWJ6` as `reference_only`
6. Canva as launch/moodboard reference only

Figma Make, Canva, browser capture, screenshots, and generated source are not
allowed to define runtime behavior, pricing, billing, App Store truth, API
contracts, nutrition math, or entitlement behavior.

## 4. Figma Make Inventory

Figma MCP `get_design_context(fileKey=MrztJU3CQtxhADBbtAsWJ6, nodeId=0:1)`
returned Make source resources, including:

- `src/app/App.tsx`
- `src/app/components/home-luxury.tsx`
- `src/app/components/landing-page.tsx`
- `src/app/components/plate-page.tsx`
- `src/app/components/progress-page.tsx`
- `src/app/components/ios/ios-home-view.tsx`
- `src/app/components/ios/ios-plate-view.tsx`
- `src/app/components/ios/ios-progress-view.tsx`
- `src/styles/tokens.css`
- `DESIGN_SYSTEM_GUIDE.md`
- `guidelines/FIGMA_AI_HARD_GOVERNANCE_CONTRACT.md`

Observed prototype surfaces:

| Prototype surface | Useful design signal | Repo-safe interpretation |
| --- | --- | --- |
| `HomeLuxury` | Launch-site composition, trust strip, dashboard preview, final CTA | Reference for future web launch polish, not route architecture |
| `LandingPage` | Full marketing funnel: hero, features, how-it-works, pricing, FAQ, CTA, footer | Copy and layout candidates must be wellness-safe and billing-safe before implementation |
| `PlatePage` | Dense meal log, macro summary, timeline, add-meal affordance | Reference for information hierarchy; real meal/data behavior remains repo-owned |
| `ProgressPage` | Range segmented control and chart-forward progress surface | Reference for chart/state framing; runtime progress tests stay authoritative |
| `IOSApp` / iOS views | iOS-style bottom navigation, cards, tabbed product demo | Visual reference only; SwiftUI code and generated iOS tokens remain SoT |
| `App.tsx` view switcher | Fast comparison shell across prototype variants | Do not copy into runtime; route registry and app state remain repo-owned |

## 5. Alignment Notes

Aligned:

- The Make prototype uses PulsePlate brand tokens such as navy, blue, green,
  red, and gold.
- The Make prototype preserves the Home / Plate / Progress focus already used
  by design-runtime governance.
- The Make prototype contains accessibility reminders for touch targets,
  focus-visible states, keyboard navigation, semantic HTML, reduced motion, and
  WCAG AA contrast.
- The Make prototype uses wellness framing more often than clinical framing.

Drift / risk:

- `App.tsx` uses a prototype-only view switcher and `localStorage` BMI bootstrap.
  Runtime routing and state must remain governed by repo app architecture.
- `landing-page.tsx` includes unsupported social proof and ranking claims such
  as Product Hunt, wellness experts, user counts, and rating text. These must
  remain draft copy until verified or rewritten.
- Make tokens and docs include token aliases and CSS values that may not exactly
  match generated repo mirrors. Repo `/tokens` and runtime token files win.
- Make has 44px touch target references, while prior repo design audit notes
  have treated web target sizing as a governance conflict to resolve before
  implementation.
- Make-side pricing names and feature lists are draft GTM references only.
  Runtime/storefront/billing contracts remain authoritative.
- Figma screenshot for Make root is not supported by the available MCP
  screenshot tool; Make evidence is source-context based in this packet.
- `Computer Use` is listed as a bundled plugin in repo docs, but no callable
  desktop-control tool surfaced in this Codex session. This is an environment
  constraint, not a repo design blocker.

## 6. Canva Lane

Canva is approved in this lane only for launch reference planning:

- moodboard direction for launch imagery
- Product Hunt / social / App Store marketing visual briefs
- campaign copy framing and thumbnail direction
- screenshot-storyboard ideas for a later release asset PR

Forbidden in this lane:

- treating Canva templates as runtime UI
- generating or publishing external marketing assets without operator approval
- changing billing, pricing, or subscription truth from Canva copy
- committing generated assets as product assets without a separate reviewed PR

## 7. Design Gap Matrix

| Prototype direction | Repo current state / authority | Decision | Future owner |
| --- | --- | --- | --- |
| Luxury-clean web Home and launch funnel | Repo web route/component system and tokens | Convert into a code-native web launch brief before implementation | Web launch shell/design polish PR |
| Dense Plate meal timeline and macro cards | Existing `frontend/src/pages/Plate.tsx` and backend-owned data contracts | Adopt hierarchy only; preserve data and API behavior | Plate web/iOS polish PR |
| Progress segmented range and charts | Existing Progress page/stories/tests and product token layer | Use as visual reference; preserve state semantics and tests | Progress web/iOS polish PR |
| iOS card/tab grammar | SwiftUI design tokens and bounded iOS screen ownership | Use only for audit map until an iOS implementation PR opens | iOS bounded screen polish PR |
| Canva/social launch storytelling | Marketing docs and App Store release governance | Keep as reference until launch asset kit PR | Canva launch asset kit PR |
| Figma Make source resources | Make-only `reference_only` lane | Keep blocked by missing canonical Design URL/node IDs | Figma Design promotion/node capture PR |

## 8. Handoff Slices

1. `codex/web-launch-design-polish-v1`
   - Build the accepted web launch shell from repo tokens/components.
   - Keep wellness-safe copy and no unsupported proof claims.
2. `codex/ios-design-polish-home-plate-progress-v1`
   - Apply bounded SwiftUI visual polish for Home / Plate / Progress.
   - Preserve navigation, API, nutrition, BMI, billing, and entitlement logic.
3. `codex/figma-design-node-capture-v1`
   - Promote only approved directions into canonical Figma Design node evidence.
   - Keep Code Connect inactive unless a future packet explicitly reopens it.
4. `codex/canva-launch-asset-kit-v1`
   - Prepare launch/social/App Store visual briefs and assets after design
     direction is accepted.

## 9. Test And Evidence Plan

Required before any design-doc PR readiness claim:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json
pre-commit run --all-files
```

Before merge-ready claim:

```bash
make verify
```

Operator override for this lane:

- `make verify` was started locally on 2026-04-30 and passed
  `verify-env`, `flake8`, `mypy`, and smoke tests before the full coverage run
  was stopped to avoid local CPU overload.
- This is not green evidence for `make verify`.
- The PR must remain draft unless a later local `make verify` pass or a
  documented machine-heavy exception plus current-head CI parity is accepted.

For future implementation PRs:

- web: targeted Vitest, Storybook/review evidence, Playwright E2E only when a
  runnable route or preview is in scope
- iOS: project-based `xcodebuild build-for-testing`, targeted tests through
  `scripts/ios_test_targets.sh`, and simulator evidence for Home / Plate /
  Progress
- Figma: `get_design_context` for Make evidence; Design metadata/screenshot
  only after canonical `figma.com/design` node IDs exist
- Canva: template/asset selection only after operator approval and a dedicated
  launch asset PR

## 10. Security Notes

- External design/source resources are untrusted reference input until
  normalized into repo vocabulary, tokens, and reviewed docs.
- No hidden analytics, lead capture, scraping, billing, entitlement, API, or
  deployment behavior is authorized by this packet.
- Figma Make and Canva cannot host or override `pulseplate.app` production
  ownership.
- App Store and payment claims must remain aligned with repo contracts before
  any public launch asset is generated.

## 11. Marketing And GTM

- Keep public copy wellness-safe: no diagnosis, cure, treatment, shame, fear,
  or guaranteed-outcome language.
- Rewrite unsupported social proof before implementation unless evidence exists.
- Treat pricing names and feature lists as draft positioning only until checked
  against StoreKit, paywall, billing, and entitlement contracts.
- Preferred launch direction: premium but quiet product quality, clear Home /
  Plate / Progress value, FitChef as wellness assistant, and explicit privacy /
  cancellation trust notes.

## 12. Decision Log

- 2026-04-30: PR #1581 is merged; this lane starts as a new follow-up design
  packet instead of continuing that PR.
- 2026-04-30: Figma Make file `MrztJU3CQtxhADBbtAsWJ6` remains
  `reference_only`.
- 2026-04-30: The lane is blocked from Figma Design execution by missing
  canonical Design URL/node IDs.
- 2026-04-30: Runtime web/iOS implementation is deferred to later PRs after
  this design packet is reviewed.
