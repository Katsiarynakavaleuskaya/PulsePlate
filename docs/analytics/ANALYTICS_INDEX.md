# Analytics Index (Catalog)

**Purpose:** A vendor-agnostic catalog of what we measure and where it lives.

**Status:** Canonical (docs-only). Runtime telemetry is out of scope here.

---

## Core funnel semantics

Canonical funnel: **onboarding → paywall → conversion → retention**.

| Stage | Owner | Update cadence | SoT |
|-------|-------|-----------------|-----|
| Onboarding | Product + Growth | Daily | `METRICS_CATALOG.md` (Onboarding completion rate) |
| Paywall | Growth | Daily | `METRICS_CATALOG.md` (Soft paywall view rate, Trial start rate) |
| Conversion | Growth + Finance | Daily | `METRICS_CATALOG.md` (Trial → Paid conversion) |
| Retention | Product + Data | Daily / Weekly | `METRICS_CATALOG.md` (Retention D7, Retention D30) |

Event taxonomy (names, required fields): `METRICS_CATALOG.md` → "Event taxonomy (growth funnel)".

---

## Coaching loop semantics

Canonical coaching loop: **start → structured reflection → next action → revisit**.

| Stage | Owner | Update cadence | SoT |
|-------|-------|-----------------|-----|
| Coaching entry | Product + Data | Daily | `METRICS_CATALOG.md` (`coaching_session_started`) |
| Structured completion | Product + Data | Daily | `METRICS_CATALOG.md` (`Distortion reframe completion rate`, `Identity loop completion rate`) |
| Action commitment | Product + Growth | Daily | `METRICS_CATALOG.md` (`Next action commit rate`) |
| Followthrough / revisit | Product + Data | Daily | `METRICS_CATALOG.md` (`Identity to action followthrough D7`, `coaching_revisit`) |

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
| Distortion reframe completion rate | % Distortion Simulator sessions completing a balanced reframe | Product + Data | `METRICS_CATALOG.md` | Daily |
| Identity loop completion rate | % Identity Loop Mapper sessions completing a structured loop | Product + Data | `METRICS_CATALOG.md` | Daily |
| Next action commit rate | % completed coaching sessions with one explicit next-step commitment | Product + Growth | `METRICS_CATALOG.md` | Daily |
| Identity to action followthrough D7 | % completed identity maps that lead to action within 7 days | Product + Data | `METRICS_CATALOG.md` | Daily |

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
| Coaching dashboard | Vendor-agnostic BI | Product + Data | Daily | scenario -> completion -> next action -> revisit |

Dashboard baseline requirements (goals, segments, data sources, KPI): `DASHBOARD_BASELINE_REQUIREMENTS.md`.

## Event Taxonomy Anchor (Wave 1)

Canonical funnel event families:

- `onboarding_*` (entry/completion/skip)
- `paywall_*` (view/dismiss/cta_click)
- `trial_*` (start/cancel/convert)
- `retention_*` (weekly activity heartbeat)
- `coaching_*` (bounded coaching loop signals)

Runtime event implementation should remain aligned with:

- `frontend/src/lib/telemetry/eventRegistry.ts`
- `frontend/src/lib/telemetry.ts`
