# Experiment Registry

**Purpose:** Track experiments end-to-end and prevent “zombie experiments” or p-hacking by making hypotheses and
success criteria explicit.

**Status:** Canonical (docs-only). Vendor-agnostic.

---

## Active Experiments

| Experiment | Hypothesis (falsifiable) | Start date | End date | Owner | Status |
|-----------|---------------------------|------------|----------|-------|--------|
| EXP-ONB-001: Onboarding copy clarity | Reworded first-run value proposition increases onboarding completion by at least 5% relative | 2026-03-01 | 2026-03-21 | Product + Growth | Planned |
| EXP-PWL-001: Soft paywall timing | Showing soft paywall after first_success improves trial starts without D7 retention drop >1pp | 2026-03-08 | 2026-03-29 | Growth | Planned |
| EXP-PWL-002: CTA framing | Changing CTA from generic upgrade to goal-based CTA improves paywall CTR by at least 7% | 2026-03-15 | 2026-04-05 | Growth + Design | Planned |

---

## Completed Experiments

| Experiment | Result (summary) | Decision | Date | Evidence |
|-----------|-------------------|----------|------|----------|
| TBD | TBD | TBD | TBD | PR/ADR link |

---

## Experiment governance rules

- Every experiment must define:
  - primary metric,
  - guardrail metrics (retention, churn, cost),
  - rollback condition,
  - explicit owner.
- Promotion to default behavior requires:
  - statistically and product-meaningful gain,
  - no guardrail breach,
  - documented decision with evidence.
