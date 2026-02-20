# Analytics Index (Catalog)

**Purpose:** A vendor-agnostic catalog of what we measure and where it lives.

**Status:** Canonical (docs-only). Runtime telemetry is out of scope here.

---

## Tracked Metrics

| Metric | Definition (short) | Owner | Source of truth | Update frequency |
|--------|---------------------|-------|-----------------|------------------|
| Onboarding completion rate | % users that complete onboarding after first launch | Product + Growth | `METRICS_CATALOG.md` | Daily |
| Activation (first_success) | % users who complete first core success action | Product + Data | `METRICS_CATALOG.md` | Daily |
| Soft paywall view rate | % active users who see soft paywall trigger | Growth | `METRICS_CATALOG.md` | Daily |
| Trial start rate | % eligible users starting trial after paywall | Growth | `METRICS_CATALOG.md` | Daily |
| Trial → Paid conversion | % trials converting to paid within policy window | Growth + Finance | `METRICS_CATALOG.md` | Daily |
| Retention D7 | % users active on day 7 after activation | Product + Data | `METRICS_CATALOG.md` | Daily |
| Retention D30 | % users active on day 30 after activation | Product + Data | `METRICS_CATALOG.md` | Weekly |
| LLM cost per active user | AI spend normalized by active users | Platform + Finance | `METRICS_CATALOG.md` | Daily |

Notes:
- “Source of truth” for metric semantics is `METRICS_CATALOG.md` (not dashboards).

---

## Data Sources

| Source | Type | Schema/contract location | Access control | Notes |
|--------|------|---------------------------|----------------|-------|
| Primary DB | transactional | `DATA_CATALOG.md` | service account (read-only) | Source for retention, activation cohorts |
| Client events | telemetry/events | `DATA_CATALOG.md` | analytics pipeline role | Event taxonomy is defined in `METRICS_CATALOG.md` |
| Billing | payments/subscriptions | `DATA_CATALOG.md` | finance-limited role | Source for trial/paid conversion |
| Feature flags | experiment state | `EXPERIMENT_REGISTRY.md` | product + growth | Used for A/B segmentation |

---

## Dashboards (Wave 1 baseline)

| Dashboard | Tool | Owner | Update frequency | Notes |
|----------|------|-------|------------------|------|
| Funnel dashboard | Vendor-agnostic BI | Product + Growth | Daily | onboarding -> paywall -> trial -> paid |
| Retention dashboard | Vendor-agnostic BI | Product + Data | Daily | D1/D7/D30 by cohort |
| Cost dashboard | Vendor-agnostic BI | Platform + Finance | Daily | LLM/API spend anomalies |

## Event Taxonomy Anchor (Wave 1)

Canonical funnel event families:

- `onboarding_*` (entry/completion/skip)
- `paywall_*` (view/dismiss/cta_click)
- `trial_*` (start/cancel/convert)
- `retention_*` (weekly activity heartbeat)

Runtime event implementation should remain aligned with:

- `frontend/src/lib/telemetry/eventRegistry.ts`
- `frontend/src/lib/telemetry.ts`
