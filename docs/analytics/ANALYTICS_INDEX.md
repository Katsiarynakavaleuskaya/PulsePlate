# Analytics Index (Catalog)

**Purpose:** A vendor-agnostic catalog of metric semantics and their applicability.

**Status:** Canonical (docs-only). Runtime telemetry is out of scope here.

---

## Current public-Web applicability

Current public-Web paywall/trial measurement: **UNAVAILABLE / NOT EMITTED**.

This is the intended current posture, not an outage.

It must not be represented as `0`, `0%`, or any other zero-valued metric.

Apple-device, backend, billing, or subscription observations must not fill a
public-Web numerator or denominator.

Repeated event rows do not establish unique-user counts.

The event enums, helpers, schemas, tests, backend records, and Apple-product
vocabulary retained in the repository are compatibility or cross-channel
vocabulary. Their presence does not prove a current public-Web production call,
delivery, storage, queryable dataset, acquisition attribution, or entitlement
change.

## Core funnel semantics

The general product funnel remains **onboarding → paywall → conversion →
retention** for channels that have separately admitted runtime and data sources.
It is not a claim that every stage is active on the current public Web.

| Stage | Owner | General cadence | Current public-Web applicability | SoT |
|-------|-------|-----------------|----------------------------------|-----|
| Onboarding | Product + Growth | Daily when admitted | Independently source-bound | `METRICS_CATALOG.md` |
| Paywall | Growth | Daily when admitted | UNAVAILABLE / NOT EMITTED | `METRICS_CATALOG.md` |
| Conversion | Growth + Finance | Daily when admitted | UNAVAILABLE / NOT EMITTED | `METRICS_CATALOG.md` |
| Retention | Product + Data | Daily / Weekly when admitted | Independently source-bound | `METRICS_CATALOG.md` |

Event names and required fields are defined in `METRICS_CATALOG.md`. Definitions
do not establish emission.

## Coaching loop semantics

Canonical coaching-loop vocabulary remains **start → structured reflection →
next action → revisit** for a separately admitted coaching surface.

| Stage | Owner | General cadence | SoT |
|-------|-------|-----------------|-----|
| Coaching entry | Product + Data | Daily when admitted | `METRICS_CATALOG.md` |
| Structured completion | Product + Data | Daily when admitted | `METRICS_CATALOG.md` |
| Action commitment | Product + Growth | Daily when admitted | `METRICS_CATALOG.md` |
| Followthrough / revisit | Product + Data | Daily when admitted | `METRICS_CATALOG.md` |

## Metric catalog

| Metric | Scope | Current public-Web applicability |
|--------|-------|----------------------------------|
| Onboarding completion rate | General product definition | Independently source-bound |
| Activation (first_success) | General product definition | Independently source-bound |
| Soft paywall view rate | Cross-channel definition | UNAVAILABLE / NOT EMITTED |
| Trial start rate | Cross-channel definition | UNAVAILABLE / NOT EMITTED |
| Trial → Paid conversion | Cross-channel definition | UNAVAILABLE / NOT EMITTED |
| Retention D7 / D30 | General cohort definitions | Independently source-bound |
| LLM cost per active user | Platform definition | Not evidence of current public-Web AI |
| Coaching metrics | Separately admitted surfaces only | Not implied by this index |

“Source of truth” means semantic definition in `METRICS_CATALOG.md`, not a
dashboard and not proof that a dataset currently exists.

## Data sources

| Source | Type | Schema/contract location | Applicability rule |
|--------|------|--------------------------|--------------------|
| Primary DB | Transactional | `DATA_CATALOG.md` | Use only for the channel and cohort it records |
| Client events | Telemetry vocabulary | `DATA_CATALOG.md` | Require an explicit production caller and delivered dataset |
| Billing | Payments/subscriptions | `DATA_CATALOG.md` | Never substitute for a public-Web acquisition event |
| Feature flags | Experiment state | `EXPERIMENT_REGISTRY.md` | A flag or registry row does not prove an experiment ran |

## Dashboard catalog

| Dashboard | Owner | Applicability |
|-----------|-------|---------------|
| Funnel dashboard | Product + Growth | General/cross-channel design; current Web paywall/trial cells stay unavailable |
| Retention dashboard | Product + Data | Only for source-bound cohorts |
| Cost dashboard | Platform + Finance | Only for source-bound spend and usage |
| Coaching dashboard | Product + Data | Only after separate runtime and data admission |

Baseline requirements live in `DASHBOARD_BASELINE_REQUIREMENTS.md`.

## Event taxonomy anchor

The following families remain bounded compatibility vocabulary:

- `onboarding_*`
- `paywall_*`
- `trial_*`
- `retention_*`
- `coaching_*`

Definitions may exist in `frontend/src/lib/telemetry/eventRegistry.ts` and
`frontend/src/lib/telemetry.ts`. Defined, callable, or test-called does not
mean production-called, delivered, stored, queryable, or attributable.
