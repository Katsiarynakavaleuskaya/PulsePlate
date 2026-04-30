<!-- markdownlint-disable MD013 -->
# Design Implementation Notes: Web Launch Design Polish V1

**Date:** 2026-04-30
**Branch:** `codex/web-launch-design-polish-v1`

## Reference Inputs

- Approved reference packet: `docs/figma/PULSEPLATE_WEB_MAKE_PROTOTYPE_DESIGN_PACKET_2026-04-30.md`
- Runtime surface: `frontend/src/pages/Marketing/PulsePlateMarketingPage.tsx`
- Runtime components: `frontend/src/components/marketing/*`
- Runtime token CSS: `frontend/src/components/marketing/marketing-tokens.css`

## Accepted Direction

- Carry forward the Figma Make launch hierarchy: brand lockup, clear hero,
  product preview, tier framing, trust boundaries, and final CTA.
- Rebuild with repo components and CSS tokens, not generated Make source.
- Keep launch copy wellness-only and cautious: planning, habit support, privacy
  boundaries, and preview language are allowed; proof, diagnosis, medical
  treatment, ranking, or guaranteed outcome claims are not.

## QA Focus

- `/` and `/marketing` continue to render the launch page.
- Primary/secondary CTAs use existing app routes.
- Copy remains wellness-safe and billing-safe.
- Reduced-motion CSS prevents hover translation for users who request reduced motion.
- Focus-visible styling remains present for links and buttons.
- Mobile layout stacks without text overlap or hidden CTAs.

## Visual Evidence

Local preview:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 4178
```

Browser Use did not surface a callable navigation/screenshot tool in this
session. Computer Use surfaced only keyboard input. Visual capture therefore
used Playwright against the local Vite preview without Figma Make generation or
Figma writes.

Captured evidence:

- `docs/figma/orchestration/sessions/2026-04-30_web_launch_design_polish_v1/evidence/root_desktop.png`
- `docs/figma/orchestration/sessions/2026-04-30_web_launch_design_polish_v1/evidence/marketing_mobile.png`

Validation notes:

- Desktop `/` renders brand, hero, CTAs, product preview, launch actions, and
  guidance boundary copy without visible overlap in the captured viewport.
- Mobile `/marketing` stacks hero copy, CTAs, trust pills, and product preview
  vertically with full-width CTA touch targets.
- Playwright browser cache had to be installed locally with
  `npx playwright install chromium`; this is host-local evidence setup and not a
  repo/runtime change.

## Local Validation

Passed:

```bash
python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json
npm test -- --run src/__tests__/App.test.tsx src/components/marketing/__tests__/MarketingLaunchPage.test.tsx
npm run build
```

Not run locally:

- full `make verify` by operator-approved machine-heavy deferral for this lane
