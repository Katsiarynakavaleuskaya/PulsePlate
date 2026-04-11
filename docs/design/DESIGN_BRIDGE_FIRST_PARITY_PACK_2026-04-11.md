# Design Bridge First Parity Pack

- Status: Partial evidence captured
- Date: 2026-04-11
- Owner: @katsiaryna_kavaleuskaya
- Packet source: `docs/orchestration/DESIGN_BRIDGE_OPERATIONALIZATION_PACKET_2026-04-11.md`

## 1. Summary

This parity pack is the first governed operational evidence bundle for the
design bridge after the merged realignment baseline.

It is intentionally limited to already-realized representative surfaces:

- `ios.home`
- `web.plate`
- `web.progress`

This artifact is not a runtime change request and does not consume the
reserved `design-agent PR4` slot.

## 2. Review Surfaces

### Web

- Canonical review source:
  - `frontend/src/stories/PulsePlateDesignSystemGuidelines.mdx`
- Evidence lane:
  - Storybook-first review
- Representative target surfaces:
  - `web.plate`
  - `web.progress`
- Representative storybook paths:
  - `frontend/src/pages/Plate.stories.tsx`
  - `frontend/src/pages/Progress.stories.tsx`

### iOS

- Canonical verification source:
  - `ios/PulsePlate.xcworkspace`
- Scheme:
  - `PulsePlate`
- Evidence lane:
  - simulator-based sanity
- Representative target surface:
  - `ios.home`

## 3. Packet Fields

This artifact reuses the CTA review packet structure from
`docs/design/PENPOT_CTA_REVIEW_PACKET_TEMPLATE.md`, but widens the same field
contract from one CTA to three representative baseline surfaces for the parity
lane. It remains template-compatible at the field level even though the
sections are grouped by surface instead of by a single CTA.

1. `surface_id`
2. `runtime ownership path`
3. `storybook review path` or `ios verification path`
4. `repo test evidence`
5. `token/variant reference`
6. `design review reference`
7. `known gaps`
8. `release decision`

## 4. Representative Surfaces

### Surface: `ios.home`

- Runtime ownership path:
  - `ios/PulsePlate.xcworkspace`
- iOS verification path:
  - simulator sanity under scheme `PulsePlate`
- Repo test evidence:
  - `build_sim` attempted through Build iOS Apps tooling on simulator
    `iPhone 17`
- Token/variant reference:
  - PulsePlate runtime design tokens
- Design review reference:
  - `docs/runbooks/sessions/DESIGN_TOOLING_SESSION_2026-04-11_design-bridge-ops-parity-pack.md`
- Known gaps:
  - screenshot/snapshot evidence blocked by existing compile errors:
    - `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:307`
    - `ios/PulsePlate/Extensions/Color+Assets.swift:39`
    - `ios/PulsePlate/Extensions/Color+Assets.swift:78`
- Release decision:
  - blocked_by_existing_ios_compile_errors

### Surface: `web.plate`

- Runtime ownership path:
  - `frontend/src/pages/Plate.tsx`
- Storybook review path:
  - `frontend/src/pages/Plate.stories.tsx`
- Repo test evidence:
  - `npm run test -- src/pages/__tests__/Plate.test.tsx`
  - `npm run build`
  - `npm run build-storybook`
- Token/variant reference:
  - `frontend/src/styles/tokens.css`
  - `frontend/src/styles/tokens.ts`
- Design review reference:
  - `docs/runbooks/sessions/DESIGN_TOOLING_SESSION_2026-04-11_design-bridge-ops-parity-pack.md`
- Known gaps:
  - Storybook surface uses deterministic session/fetch harness and does not
    prove backend availability
- Release decision:
  - evidence_ready_for_review

### Surface: `web.progress`

- Runtime ownership path:
  - `frontend/src/pages/Progress.tsx`
- Storybook review path:
  - `frontend/src/pages/Progress.stories.tsx`
- Repo test evidence:
  - `npm run test -- src/pages/__tests__/Progress.test.tsx`
  - `npm run build`
  - `npm run build-storybook`
- Token/variant reference:
  - `frontend/src/styles/tokens.css`
  - `frontend/src/styles/tokens.ts`
- Design review reference:
  - `docs/runbooks/sessions/DESIGN_TOOLING_SESSION_2026-04-11_design-bridge-ops-parity-pack.md`
- Known gaps:
  - Storybook surface verifies the current static chart baseline only; no live
    data source is exercised in this lane
- Release decision:
  - evidence_ready_for_review

## 5. Guardrails

- Storybook remains the canonical web review surface
- iOS verification remains simulator-based only for this lane
- Cloudflare preview/deploy is advisory and not merge-blocking
- Any runtime gap discovered while collecting evidence must move to a separate
  follow-up item and separate PR

## 6. Current Lane Decision

The first evidence bundle exists and is sufficient to open the operational
draft PR only:

- `web.plate` evidence captured
- `web.progress` evidence captured
- `ios.home` evidence attempted and blocked by current iOS compile drift

This means the lane may open as a draft operational evidence/governance PR with
the iOS blocker explicitly declared, but it is not allowed to claim:

- review-ready status
- full cross-platform parity
- completed iOS capture evidence

until the iOS compile blockers are fixed in a separate follow-up or in this
branch before merge.
