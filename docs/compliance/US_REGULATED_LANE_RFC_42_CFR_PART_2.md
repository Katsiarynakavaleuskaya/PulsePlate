# US Regulated Lane RFC: Clinical / Provider Expansion Boundary

**Status:** Future-state RFC
**Last updated:** 2026-03-08
**Current decision:** Not active in the wellness runtime

## Goal

Define the boundary for any future PulsePlate expansion into:

- provider-integrated workflows
- clinical notes or care coordination
- substance-use-disorder records
- 42 CFR Part 2 or similar redisclosure-restricted data

## Hard Separation Requirements

Any future regulated lane must have:

- separate consent and notice workflow
- separate storage segregation from the wellness runtime
- explicit redisclosure controls
- role-based access controls suited to provider use
- separate retention and deletion policy
- legal/compliance sign-off before activation

## What Is Explicitly Out of Scope Today

- storing or processing SUD records in the current wellness runtime
- mixing provider/EHR data with consumer wellness feedback tables
- reusing the existing AI insight surfaces for regulated clinical workflows
- representing the current product as HIPAA-ready or 42 CFR Part 2 compliant

## Trigger to Re-open This RFC

Re-open only when PulsePlate takes an explicit step toward:

- B2B/provider deployment
- clinical or care-team workflows
- regulated notes, records, or redisclosure-sensitive data

Until then, the canonical product posture remains: **consumer wellness, EU-first privacy control plane, regulated US lane blocked**.
