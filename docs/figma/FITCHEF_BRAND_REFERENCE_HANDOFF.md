# FitChef Brand Reference Handoff

Status: `Reference Only`
Scope: `FitChef mascot/logo pack for site and Figma composition`

## Canonical Input

Use the repo mascot canon first:

- `docs/design/FITCHEF_MASCOT_ASSET_CANON.md`
- `frontend/src/assets/brand/fitchef-portrait-neutral-v1.png`
- `frontend/src/assets/brand/fitchef-portrait-wink-v1.png`
- `frontend/src/assets/brand/fitchef-portrait-thinking-v1.png`
- `frontend/src/assets/brand/fitchef-portrait-sleepy-v1.png`
- `frontend/src/assets/brand/fitchef-portrait-surprised-v1.png`
- `frontend/src/assets/brand/fitchef-onboarding-welcome-v1.png`

## Rules

1. Figma is a placement and layout lane, not the source of truth for mascot PNGs.
2. Do not replace repo mascot files from Figma export without a reviewed PR.
3. Keep website, onboarding, and campaign compositions aligned to the named
   variant contract in `docs/design/FITCHEF_MASCOT_ASSET_CANON.md`.
4. Treat new Figma-only variations as drafts until they are promoted back into
   repo asset canon with explicit filenames and version suffixes.

## Current Canonical Figma Boards

The current governed Figma reference boards for the FitChef mascot lane live in
file `2JDwOByQIbcPgp93FDzHii`
(`https://www.figma.com/design/2JDwOByQIbcPgp93FDzHii/PulsePlate_v3_Canonical_Foundations_Welcome_Gate`).

- Page `02_Brand_Assets`:
  - `72:2` `FitChef Mascot Asset Register / Canonical`
  - `82:2` `FitChef Canonical Variant Gallery`
  - `72:131` `FitChef Usage and Promotion Rules`
  - `1473:2` `FitChef Mascot Asset Inventory — Intake 2026-04-28`
    - GTM classification keys (`fitchef-candidate-001`…`030`): `docs/figma/FITCHEF_INTAKE_1473_2_GTM_CLASSIFICATION_GUIDANCE.md`
- Page `10_Welcome_Gate`:
  - `82:66` `FitChef Placement Studies / Approved`
- Page `11_Welcome_Gate_States`:
  - `85:32` `FitChef Mascot State Coverage / Approved`

These boards are reference-only.

They document:

- the approved six-asset repo-backed canon
- placement studies for the current Welcome Gate lane
- state coverage that is safe relative to the current preview/runtime canon
- a candidate intake board that tracks reference-only audit status:
  - current batch: `30` assets
  - `6` `APPROVED-SEED` (matches `docs/design/FITCHEF_MASCOT_ASSET_CANON.md`)
  - `20` `CANDIDATE`
  - `3` `REFERENCE-ONLY`
  - `1` `NEEDS-REWORK`

For `11_Welcome_Gate_States`, treat `85:32` `FitChef Mascot State Coverage / Approved`
as the active board. Earlier state-board variants on that page are legacy audit material,
not parallel live canon.

They do not authorize:

- mascot asset promotion from Figma into repo canon
- runtime route or onboarding flow changes
- mutation of canonical Welcome Gate frames to match exploratory compositions
- runtime promotion from `1473:2` without a separate repo PR

## Deferred Follow-ups

- Website brand rollout: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-web-brand-rollout`
- Figma production sync: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-figma-production-sync`
