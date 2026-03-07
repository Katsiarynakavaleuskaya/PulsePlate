# Wellness Explainers + Learning Cycles (Mini-PRD)

**Status:** Proposed
**Last updated:** 7 March 2026
**Scope:** Product specification for a rules-first MVP

---

## Summary

PulsePlate should adopt the strongest product patterns from modern interactive learning
platforms without turning into an ML school. The fit is not "200 algorithms" or
"architecture recreations". The fit is:

- interactive explainers for user-facing wellness logic,
- progression through learning cycles instead of fragile streaks,
- science-backed framing that improves trust, retention, and upsell clarity.

This MVP must remain consistent with PulsePlate's existing product contract:

- FREE = orientation,
- PRO = interpretation,
- VIP = daily action support.

The MVP is explicitly scoped to existing product entities, deterministic rules, and
existing backend data. It must not introduce a new heavy LLM surface.

---

## Problem

PulsePlate already has meaningful calculations, tier progression, and adherence signals,
but the user journey still has a comprehension gap:

- FREE tells the user where they are, but not always why the result is limited.
- PRO adds interpretation, but the learning value is not packaged as a progressive system.
- VIP adds action, but the app can explain the "why this plan" layer more clearly.

This creates three product risks:

1. Trust is lower than it could be because the app computes more than it teaches.
2. Retention depends too much on utility alone and not enough on self-understanding.
3. Upsell can drift toward generic conversion copy instead of educational progression.

---

## Goal

Create a compact product layer that explains the user's current result, turns repeated
use into visible learning progress, and strengthens the trust-based funnel.

### Primary goals

- Increase comprehension of BMI / risk / adherence / plan outputs.
- Reframe progress around learning cycles, not "success vs failure".
- Improve FREE -> PRO and PRO -> VIP progression with educational, wellness-safe logic.

### Non-goals

- No ML curriculum, algorithm catalog, or external educational track.
- No clinical or curative positioning.
- No new public heavy LLM endpoint for explainers.
- No leaderboard, social pressure, or anxiety-producing streak mechanics in MVP.
- No client-side business logic duplication.

---

## Product Principles

### 1. Wellness-only language

Explainers must stay educational and wellness-safe. They must not use clinical,
curative, or guaranteed-outcome framing.
Use the canonical disclaimer in `docs/safety/WELLNESS_DISCLAIMER_CANONICAL.md`.

### 2. Scientific clarity without false precision

The product should explain limits, uncertainty, and contributing factors instead of
pretending to know more than it does.

### 3. Learning cycles over streaks

The user should feel "I am learning what works for me", not "I broke my streak".

### 4. Rules-first MVP

For the first release, explainer assembly should be deterministic and sourced from
existing payloads and rules. If AI-assisted copy is ever added later, it must remain
optional and guarded.

### 5. Thin-client delivery

The backend owns explainer logic; frontend and iOS remain presentation adapters.

---

## User Outcomes

### FREE outcome

"I understand what this result means and what it does not mean."

### PRO outcome

"I understand why my risk/interpretation looks this way for me."

### VIP outcome

"I understand why the app recommends these actions and what pattern I am improving."

---

## MVP Scope

### Surface A: Context Explainers

Add short, structured explanations on top of existing outputs:

- FREE: explain BMI as a starting point and state what is missing.
- PRO: explain which factors increase or reduce interpretation depth.
- VIP: explain why this plan/target/action is suggested and what pattern it supports.

### Surface B: Learning Cycles

Introduce a lightweight progression model based on repeated understanding and behavior:

- Cycle 1: Baseline
- Cycle 2: Risk Context
- Cycle 3: Consistency Pattern
- Cycle 4: Plan Adjustment

Each cycle should answer:

- what the user learned,
- which existing signals unlocked the cycle,
- what the next useful action is.

### Learning cycle rule table

| Cycle ID | Label | Required signals | Deterministic unlock rule |
| --- | --- | --- | --- |
| `baseline` | Baseline | BMI result rendered | Unlock when a valid FREE result is produced. |
| `risk_context` | Risk Context | BMI interpretation plus at least one PRO context field | Unlock when `interpretation_v1` or `waist_risk` is present. |
| `consistency_pattern` | Consistency Pattern | Adherence event history or weekly adherence score | Unlock when adherence data exists and confidence is not marked as low-data only. |
| `plan_adjustment` | Plan Adjustment | VIP weekly-plan output plus plan-fit explanation | Unlock when a weekly plan and its explainer payload are both available. |

### Surface C: Progress Signals

Represent progress as:

- completed explainers,
- unlocked learning cycles,
- repeated evidence of adherence or plan understanding,
- next recommended educational action.

MVP progress must be local to the product journey. No public ranking and no social comparison.

---

## Entity Mapping To Existing Product Objects

| Product surface | Existing entity or signal | Current source |
| --- | --- | --- |
| FREE explainer | `bmi`, `category`, `interpretation_v1`, `soft_paywall` | `app/schemas/bmi.py` |
| PRO explainer | `waist_risk`, `notes`, combined interpretation fields | `app/schemas/bmi.py`, BMI Pro contract |
| Adherence explainer | `adherence_score`, slip risk, confidence | `app/schemas/nutrition_log.py`, `core/bayes/adherence_model.py` |
| Weekly plan explainer | weekly `adherence_score`, nutrient target fit | `core/menu_engine.py`, `core/weekly_plan_new.py` |
| CBT reframing copy | existing CBT insight and wellness-safe messaging direction | `app/routers/cbt_insight.py`, `docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md` |

### Binding notes

#### FREE

- Use current BMI result fields to explain "what this number captures" and "what it omits".
- Reuse soft-paywall logic as an educational continuation, not as a sales interruption.

#### PRO

- Use current interpretation and waist-risk data to explain why the user sees a broader
  risk picture than BMI alone.
- Package this as understanding, not fear.

#### VIP

- Use current weekly plan and adherence signals to explain why a recommendation exists.
- The learning unit is not "perfect compliance". The learning unit is "pattern detection
  and adjustment".

#### Adherence

- Use the existing Beta-Binomial adherence model and current adherence score fields as
  the first source of "consistency pattern" messaging.
- Confidence should be surfaced carefully: low-confidence states should say "needs more
  data", not imply certainty.

#### Score normalization rule

- Event-level adherence from `app/schemas/nutrition_log.py` uses a `0.0..1.0` scale.
- Weekly-plan adherence from `core/menu_engine.py` and `core/weekly_plan_new.py` uses a
  `0..100` scale.
- Any shared explainer or learning-cycle threshold must normalize these sources before
  comparison. Canonical MVP rule: convert weekly-plan scores to `0.0..1.0` before using
  shared progression logic.

---

## Rules-First MVP Contract

### Allowed data sources

- Existing backend response fields
- Existing domain models and deterministic rules
- Existing adherence signals
- Existing plan-generation outputs

### Forbidden in MVP

- New external datasets
- New vector search / RAG requirement for explainers
- New always-on LLM endpoint for educational copy
- Copy that depends on hidden client-side heuristics

### Optional future extension

If a future version uses AI-assisted rewriting for tone or personalization, it must:

- sit behind the existing tier model,
- pass wellness-safe validation,
- obey quota / rate-limit / cost guardrails,
- degrade safely to deterministic copy.

### Minimal explainer payload example

```json
{
  "entity": "bmi_result",
  "tier": "free",
  "title": "BMI is a starting point",
  "what_this_means": "This result gives a broad orientation based on height and weight.",
  "what_is_missing": [
    "fat_distribution",
    "muscle_context"
  ],
  "next_step": "pro",
  "learning_cycle_id": "baseline",
  "signals": {
    "bmi": 26.4,
    "category": "overweight"
  }
}
```

---

## UX Shape

### Explainer card

Each explainer card should contain:

- `title`
- `what_this_means`
- `what_is_missing` or `why_this_matters`
- `next_step`
- `learning_cycle_id` (optional)

### Learning cycle card

Each learning cycle should contain:

- `cycle_id`
- `label`
- `unlocked_by`
- `what_you_learned`
- `next_action`

### Tone

- calm,
- educational,
- non-judgmental,
- specific,
- not salesy.

### Default behavior

- If required source data is missing, do not invent an explanation. Show a short neutral
  fallback and omit the learning-cycle unlock.
- If confidence is low, say "needs more data" rather than implying certainty.
- If a tier does not expose the needed entity, do not emulate it on the client.

---

## Acceptance Criteria

- A deterministic explainer payload is defined for at least one FREE and one PRO or VIP surface.
- Every explainer field maps to an existing backend entity or rule already present in the repo.
- MVP logic does not require a new public LLM or RAG endpoint.
- Copy remains wellness-safe and compatible with the canonical disclaimer.
- Frontend and iOS are specified as render-only consumers of backend explainer payloads.
- Learning-cycle progression uses non-coercive rules and does not depend on streak-shame.

---

## Success Metrics

### Product metrics

- Increased interaction rate with explainers after result screens
- Increased return usage for users who unlocked at least one learning cycle
- Higher conversion from FREE -> PRO and/or PRO -> VIP on educational surfaces

### Safety metrics

- Zero medical-claim regressions in explainer copy
- Zero new expensive AI calls on the MVP path
- No business-logic drift into frontend or iOS

---

## Deferred Follow-Ups

- Richer progress memory across sessions
- Additional entity types beyond BMI / risk / adherence / weekly plan
- Optional AI-assisted tone rewriting with explicit safety/economics gates
- More advanced personalization beyond existing deterministic and Bayesian signals
- Any standalone endpoint/runtime expansion for explainers

---

## Delivery Plan

### Phase 1: Contract + copy system

- Define deterministic explainer payload shape
- Define learning cycle IDs and unlock conditions
- Approve wellness-safe copy patterns

### Phase 2: Backend assembly

- Assemble explainer payloads from existing BMI / risk / adherence / plan data
- Keep logic in backend/domain layer
- No new public heavy AI endpoints

### Phase 3: Frontend surfaces

- Render explainer cards on existing result and progress surfaces
- Render learning-cycle progress using backend payloads only

---

## Explicit Guardrails

- Do not turn PulsePlate into an ML education product.
- Do not promise better health outcomes because a cycle was unlocked.
- Do not use streak-shame or "failure recovery" framing.
- Do not add implementation that requires a new expensive provider call on every result.
- Do not bypass the current tier progression contract.

---

## Open Questions

- Should the first shipping surface be BMI result only, or BMI + Progress together?
- Should learning cycles unlock passively from usage, or require explicit "mark as understood" events?
- Should CBT insight remain separate from explainers in MVP to keep cost and complexity low?

Current recommendation: ship BMI + PRO interpretation explainers first, then extend to
adherence and weekly-plan flows.
