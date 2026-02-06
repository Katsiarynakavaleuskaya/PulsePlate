# Welcome Gate Experiment Plan (iOS-only, no backend required)

**Date:** 6 February 2026
**Scope:** client-side cohorts for copy + timing; extendable later to backend analytics
**Constraint:** must remain iOS-only unless a separate backend PR is planned

---

## 1) Cohort assignment (deterministic, local)

- Assign a variant once per install (store in UserDefaults).
- Keep a **versioned key** for experiment assignment to avoid sticky migrations.

Example keys:
- `welcome_copy_variant_v1` = `A|B`
- `welcome_paywall_timing_variant_v1` = `A|B`

---

## 2) Experiment E1 — Welcome copy (A vs B)

**Hypothesis:** tighter, more concrete copy improves completion and first action.

- **Variant A:** uses “track / plan / privacy” framing (trust-first)
- **Variant B:** uses “start small / stay consistent” framing (momentum-first)

**Primary metric (manual for now):**
- % of testers who complete welcome and reach the main app screen

**Secondary metric:**
- Time from launch → first core action (BMI calculate / first meaningful tap)

---

## Variant Mapping (Single Reference)

| Variant key                | Copy block | UI behavior |
|---------------------------|------------|-------------|
| welcome_copy_variant_v1_A | Copy A     | Standard welcome flow, CTA = Continue |
| welcome_copy_variant_v1_B | Copy B     | Same flow, CTA emphasizes speed/value |

## 3) Experiment E2 — Upgrade prompt timing (after value)

**Hypothesis:** delaying upgrade messaging until after 1–3 value moments increases conversion quality.

- **Variant A:** soft hook after first value moment
- **Variant B:** soft hook after third value moment

**Primary metric:**
- Tap-through rate on soft hook

**Guardrail metric:**
- D1 retention proxy (TestFlight qualitative feedback)

---

## 4) Experiment E3 — CTA wording on paywall entry

**Hypothesis:** benefit-first CTA increases intent without pressure.

- **Variant A:** “Unlock advanced insights”
- **Variant B:** “Get PRO features”

**Primary metric:**
- CTA tap-through

---

## 5) How we measure without backend (TestFlight stage)

For the first iteration:
- Use **TestFlight tester feedback** + a simple checklist (“did you see X? did you tap Y?”).
- Prefer **small cohorts** (20–50 users) and fast iteration over fake precision.
  - See canonical visibility loop: `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md#visibility-loop-single-source-of-truth`

When backend analytics is ready (separate scope):
- Add server-side event ingestion + dashboards.
