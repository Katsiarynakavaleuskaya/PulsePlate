# Brainstorming: Home/Plate/Progress CTA Runtime Remediation

<!-- markdownlint-disable MD013 -->

**Date:** 2026-02-18
**Scope:** Runtime remediation options for CTA parity and paywall execution quality.

---

## Problem Frame

The CTA matrix documents intended Home/Plate/Progress behavior, but runtime still carries gaps:

- iOS placeholder CTA destinations in critical paths,
- web paywall CTA flow still callback-oriented rather than production purchase wiring,
- deterministic CTA-level tests missing/incomplete for cross-surface parity.

Evidence anchors:

- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:1`
- `docs/roadmap/BACKLOG_LEDGER.md:479`

---

## Candidate Solution Tracks

1. **Parity-first track (recommended):**
   - Close iOS placeholder destinations first.
   - Then wire web paywall CTA to production purchase path.
   - Add deterministic tests per slice.

2. **Paywall-first track:**
   - Prioritize revenue path first (web purchase wiring + result handling).
   - Backfill iOS parity in second commit.

3. **Test-first contract track:**
   - Write CTA-level contract tests from matrix expectations.
   - Implement runtime until tests pass for each CTA.

4. **Feature-flag safety track:**
   - Ship paywall wiring behind a controlled runtime flag.
   - Remove flag after deterministic test and rollout confidence.

---

## Option Scoring (quick)

| Option | Delivery speed | Risk control | Review clarity | Recommendation |
| --- | --- | --- | --- | --- |
| Parity-first | High | High | High | ✅ Primary |
| Paywall-first | High | Medium | Medium | Conditional |
| Test-first contract | Medium | High | High | ✅ Co-primary with parity-first |
| Feature-flag safety | Medium | High | Medium | Use if risk increases |

---

## Guarded Decisions

- Keep all client behavior within thin-adapter boundaries.
- Avoid broad navigation refactors during CTA remediation.
- Treat matrix as execution SoT and update status only with evidence.
- Close bot/reviewer loops with explicit fixed-in-commit mapping.

---

## Next-Step Bundle

1. Create CTA destination mapping table (Now vs Target vs Test).
2. Implement iOS destination fixes in one scoped commit.
3. Implement web paywall purchase wiring in one scoped commit.
4. Add deterministic CTA tests and run required gates.
5. Update matrix + audit + PR body mapping.
