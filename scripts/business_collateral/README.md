# Business Collateral Builders

## Purpose

Generate local-only business collateral from repo-managed markdown specs.

## Canonical inputs

- `docs/audience_pack/B2B_PARTNERSHIP_PROPOSAL_SPEC.md`
- `docs/audience_pack/B2B_PITCH_DECK_SPEC.md`
- `docs/audience_pack/BUSINESS_COLLATERAL_AUTOMATION.md`

## Commands

- `npm run build:b2b-proposal`
- `npm run build:b2b-pitch-deck`
- `npm run build:business-collateral`

## Output location

- Default output root: `tmp/business_collateral/`

## Rules

- Builders must not invent missing business values.
- Generated files remain untracked.
- Markdown remains the source of truth.
