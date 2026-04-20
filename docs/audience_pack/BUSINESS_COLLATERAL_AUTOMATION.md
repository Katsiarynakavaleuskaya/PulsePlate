<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Business Collateral Automation

Version: 2026-03-21 (`America/New_York`)
Change note: Added markdown-first collateral generation contract for B2B proposal and pitch deck outputs.
Decision reference: `docs/executive/PR_PORTFOLIO_BRIEF_DIRECTORS_2026-03.md`

## Purpose

This document defines how PulsePlate generates partner-facing business collateral
without creating a second business source of truth.

## Canonical Inputs

- `docs/audience_pack/FACTS_CANONICAL.md`
- `docs/audience_pack/INVESTOR_PUBLIC_OVERVIEW.md`
- `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md`
- `docs/audience_pack/PROOF_PACK.md`
- `docs/audience_pack/B2B_PARTNERSHIP_PROPOSAL_SPEC.md`
- `docs/audience_pack/B2B_PITCH_DECK_SPEC.md`

## Derived Outputs

- `.docx` proposal files
- `.pptx` pitch decks

Derived outputs are local-only artifacts and must not be committed.

## Builder Commands

- `npm run build:b2b-proposal`
- `npm run build:b2b-pitch-deck`
- `npm run build:business-collateral`

## Output Policy

- Default output root: `tmp/business_collateral/`
- Generated files may be reviewed locally or attached externally after human review.
- Generated files must not be treated as canonical truth; the markdown specs remain authoritative.

## Placeholder Hygiene

- Verified repo facts may appear directly.
- Unknown or unverified numbers must remain as `[VERIFY_*]` placeholders inside specs until an owner validates them.
- Builders must not inject invented values or hidden defaults for missing business data.

## Review Rules

1. Review the markdown spec first.
2. Generate the collateral locally.
3. Verify the generated material still uses wellness-safe language.
4. Remove or replace unresolved placeholders before external distribution when evidence is available.

## Security Notes

- No medical claims.
- No PII in generated materials.
- No unsourced metrics should be silently converted into factual-looking statements.

## Marketing & GTM

- The system is optimized for fast pilot outreach, partner packaging, and founder-led sales support.
- The goal is repeatable conversion-ready collateral, not decorative slideware.
