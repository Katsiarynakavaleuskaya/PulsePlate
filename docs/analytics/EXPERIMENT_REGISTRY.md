# Experiment Registry

**Purpose:** Track experiments end-to-end and prevent “zombie experiments” or p-hacking by making hypotheses and
success criteria explicit.

**Status:** Canonical (docs-only). Vendor-agnostic.

**Framework:** See `EXPERIMENTATION_FRAMEWORK.md` for lifecycle states, guardrails, and decision criteria.

---

## Active Experiments

| Experiment | Hypothesis (falsifiable) | Start date | End date | Owner | Status |
|-----------|---------------------------|------------|----------|-------|--------|
| EXP-AIR-001: Logic + philosophy replay | Combined `A3` offline replay answers improve correctness pass rate and first-pass readiness proxy over `A0` without increasing unsupported claim rate, contradiction rate, or known-good false positives | 2026-03-14 | 2026-03-28 | AI Quality + Orchestration | Planned |
| EXP-CBT-001: CBT coaching wave activation baseline | The first bounded CBT coaching rollout improves `distortion_reframe_completion_rate` and `identity_loop_completion_rate` without `retention_d7` dropping by more than 2pp, `llm_cost_per_active_user` increasing by more than 15%, or `therapy_medical_language_leakage_rate` exceeding the wellness-safe threshold | 2026-04-01 | 2026-04-22 | Product + Wellness AI + Data | Planned |
| EXP-ONB-001: Onboarding copy clarity | Reworded first-run value proposition increases onboarding completion by at least 5% relative | 2026-03-01 | 2026-03-21 | Product + Growth | Planned |
| EXP-ONB-002: Flow simplification | Reducing onboarding to 2 screens increases completion by at least 8% without D1 retention drop >2pp | 2026-04-01 | 2026-04-21 | Product | Planned |

---

## Rejected / Not Admitted Experiments

These historical public-Web proposals did not run and produced no result. A
future monetization experiment requires a new external product, legal, and
architecture admission; this table grants no runtime or data authority.

| Experiment | Status | Execution | Result | Reason |
|-----------|--------|-----------|--------|--------|
| EXP-PWL-001: Soft paywall timing | REJECTED / NOT ADMITTED | Did not run | No result | Current public Web is free and information-only |
| EXP-PWL-002: CTA framing | REJECTED / NOT ADMITTED | Did not run | No result | Current public Web offers no acquisition CTA |
| EXP-PWL-003: Friction reduction | REJECTED / NOT ADMITTED | Did not run | No result | Current public Web offers no trial-start flow |

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
