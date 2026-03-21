<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# PR Portfolio Brief for Directors

Version: 2026-03-21 (`America/New_York`)
Status: Thin executive layer over `docs/audience_pack/*`

## Purpose

This brief packages the current business-line PR wave for director and board-style review
without creating a second fact source of truth.

Canonical facts remain in:
- `docs/audience_pack/FACTS_CANONICAL.md`
- `docs/audience_pack/INVESTOR_PUBLIC_OVERVIEW.md`
- `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md`
- `docs/audience_pack/PROOF_PACK.md`

## Executive Summary

PulsePlate already has the repo-level foundation for a wellness-first product:
- shared backend for web and iOS,
- tiered monetization structure,
- policy-driven engineering gates,
- audience-pack documentation for external narrative control.

The current business-line wave does not change runtime behavior first.
It builds the operating layer required to commercialize the product more reliably:
- director-level business orchestration through the existing coordinator pattern,
- canonical B2B proposal and pitch-deck specs in repo markdown,
- deterministic generation of partner-facing collateral from repo-managed sources.

## What This PR Wave Is Solving

### Problem

Business communication exists, but board-ready and partner-ready collateral is still too manual.
That creates three risks:
- drift between repo truth and external materials,
- slow turnaround for pilots and partner conversations,
- duplicated strategic language across scattered documents.

### Solution

Use a governance-first PR sequence:
1. Create the worktree-scoped runbook, decision packet, evidence log, and executive brief.
2. Upgrade `business-strategist-agent` to director-level business ownership rather than adding a duplicate role.
3. Add markdown-first B2B specs and builders that generate `.docx` and `.pptx` outputs locally.
4. Run the normal bug-hunter, CI, and merge-readiness loop before merge.

## Why This Matters Now

- PulsePlate already has enough product substance to support partner and pilot conversations.
- The gap is operational packaging, not another round of fact invention.
- A deterministic collateral system lowers response time for business development without weakening governance.

## Scope In

- Orchestration runbook for the business PR wave
- Director-level business agent contract
- B2B proposal and pitch-deck specification docs
- Local-only collateral builders and smoke tests

## Scope Out

- New runtime/API features for the business analyzer
- Any second fact canon outside `docs/audience_pack/*`
- Generated binary deliverables tracked in git

## Director-Level Decision Frame

| Decision Area | Current Direction | Why |
|---|---|---|
| Business ownership | Extend `business-strategist-agent` | Avoid duplicate roles and routing ambiguity |
| Canonical business truth | Keep `docs/audience_pack/*` | Existing repo SoT already fits the need |
| Executive packaging | Add thin `docs/executive/*` layer only | Board-ready framing without fact duplication |
| Partner collateral | Generate from markdown specs | Faster, repeatable, less drift |
| Runtime follow-through | Defer to later PR | Governance/docs layer should land first |

## Measurable Outcomes

- Faster generation of partner-ready collateral
- Lower drift risk between product truth and business narrative
- Cleaner routing for strategy, GTM, and director-level review work
- Safer review path because generated outputs stay local-only

## Dependencies

- `docs/orchestration/BUSINESS_WAVE_PR_SERIES_RUNBOOK.md`
- `docs/library/brainstorm/2026-03-21_business-wave-b2b-collateral.md`
- `docs/library/research/2026-03-21_business-wave-b2b-collateral_evidence.md`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-business-wave-runtime-follow-through`

## Security Notes

- PulsePlate remains a wellness product; this brief does not authorize medical claims.
- Any external-facing number without repo evidence must remain a placeholder until verified.
- Generated documents must be reviewed before external distribution.

## Marketing & GTM

- Best first-loop channels remain low-capex and proof-friendly: B2B API pilots, corporate wellness outreach, founder-led outreach, and controlled ASO/SEO narrative alignment.
- The deck/proposal system should optimize for repeatable pilot conversion, not vanity collateral.
- Executive communication should keep one line of truth: capability -> partner value -> proof.
