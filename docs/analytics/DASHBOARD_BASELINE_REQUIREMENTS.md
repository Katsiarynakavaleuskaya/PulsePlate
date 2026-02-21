# Dashboard Baseline Requirements (Wave 1)

**Purpose:** Define baseline requirements for Wave 1 analytics dashboards so that goals, segments, data sources, and KPI are explicit and reviewable.

**Status:** Canonical (docs-only). Vendor-agnostic.

**Related:** `ANALYTICS_INDEX.md` (dashboard list), `METRICS_CATALOG.md` (metric definitions).

---

## Goals

1. **Funnel visibility** — Product and Growth can monitor onboarding → paywall → trial → paid conversion in one place.
2. **Retention visibility** — Product and Data can monitor D1/D7/D30 retention by cohort.
3. **Cost visibility** — Platform and Finance can monitor LLM/API spend and cost per active user.

---

## Segments and dimensions

| Segment / dimension | Use case | SoT / notes |
|--------------------|----------|-------------|
| Tier (FREE / PRO / VIP) | Funnel and retention by tier | Backend `app/middleware/api_tiers.py` |
| Cohort (activation date) | Retention by cohort | First success / activation date |
| Placement (paywall placement id) | Paywall performance by placement | Event property `placement` |
| Source (entry point) | Attribution (onboarding, paywall, CTA) | Event property `source` |

---

## Data sources

| Dashboard | Primary data | Secondary / derived |
|-----------|--------------|----------------------|
| Funnel | Client events (onboarding_*, paywall_*, trial_started), Billing (trial/paid) | Primary DB (users, subscriptions) for eligibility |
| Retention | Client events (retention_heartbeat, activation), Primary DB (cohort definition) | — |
| Cost | Platform spend (LLM/API), Primary DB or usage logs (active users) | — |

Schema and field semantics: `DATA_CATALOG.md`. Event taxonomy: `METRICS_CATALOG.md` → "Event taxonomy (growth funnel)".

---

## KPI and update frequency

| KPI | Owner | Update frequency | Definition |
|-----|-------|------------------|------------|
| Onboarding completion rate | Product + Growth | Daily | `METRICS_CATALOG.md` |
| Activation (first_success) | Product + Data | Daily | `METRICS_CATALOG.md` |
| Soft paywall view rate | Growth | Daily | `METRICS_CATALOG.md` |
| Trial start rate | Growth | Daily | `METRICS_CATALOG.md` |
| Trial → Paid conversion | Growth + Finance | Daily | `METRICS_CATALOG.md` |
| Retention D7 | Product + Data | Daily | `METRICS_CATALOG.md` |
| Retention D30 | Product + Data | Weekly | `METRICS_CATALOG.md` |
| LLM cost per active user | Platform + Finance | Daily | `METRICS_CATALOG.md` |

---

## Guardrails and rollback

- Dashboards must not expose raw PII (user_id only in trusted contexts; anonymize in exports).
- Experiment guardrails (retention, churn, cost) are defined per experiment in `EXPERIMENT_REGISTRY.md`; dashboard alerts may reference those guardrail metrics for active experiments.
