# CTA Review Packet — `web.home.open_setup`

- Status: Review-ready
- Date: 2026-03-07
- Owner: @katsiaryna_kavaleuskaya

## 1. CTA Summary

- CTA ID: `web.home.open_setup`
- UI label: `Configure Setup`
- Runtime intent: move the user from Home quick actions into the Nutrition Setup flow

## 2. Runtime Ownership

- Component: `frontend/src/components/cta/HomeOpenSetupCta.tsx:9`
- Screen/page: `frontend/src/pages/Home.tsx:95`
- Route / downstream flow: `/setup` -> `frontend/src/pages/NutritionSetup/index.tsx:19`

## 3. Storybook Review Surface

- Story: `frontend/src/components/cta/HomeOpenSetupCta.stories.tsx:6`
- Storybook title: `PulsePlate/Patterns/HomeOpenSetupCta`
- Notes: canonical review surface for the primary Home CTA without relying on page-level screenshots

## 4. Repo Evidence

- Tests:
  - `frontend/src/pages/__tests__/Home.test.tsx:39`
- Runtime evidence:
  - Home route renders the CTA and navigation resolves to `/setup`
    (`frontend/src/pages/__tests__/Home.test.tsx:39`)
  - CTA uses canonical button tokens through `buttonClasses`
    (`frontend/src/components/cta/HomeOpenSetupCta.tsx:13`)

## 5. Design Review Reference

- Packet: this document
- Penpot workspace: `https://design.penpot.app/#/dashboard/recent?team-id=ff0898e1-835b-80ff-8007-ac98b669a273`
- Penpot page/frame: pending first explicit Home CTA board capture in the registered team workspace
- Optional Figma: legacy capture exists but is non-canonical for this bridge path

## 6. Token + Variant Alignment

- Variant family: `V1`
- Token source:
  - `frontend/src/styles/tokens.css:8`
  - `frontend/src/styles/tokens.ts:12`
- Visual notes:
  - primary CTA
  - large full-width treatment
  - calm trust emphasis, no premium/paywall semantics

## 7. Known Gaps

- Downstream submit flow still needs a broader integration test beyond route handoff
- Penpot frame reference is not materialized yet inside the user workspace

## 8. Release Decision

- Decision: acceptable as pilot review packet for Storybook-first + Penpot bridge
- Follow-up: add explicit Penpot frame link when the first Home CTA review board is created
