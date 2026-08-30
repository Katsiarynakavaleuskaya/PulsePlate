# Dashboard Baseline Requirements (Wave 1)

**Purpose:** Define vendor-agnostic dashboard requirements without claiming that
a channel emits or stores every cataloged event.

**Status:** Canonical (docs-only).

**Related:** `ANALYTICS_INDEX.md`, `METRICS_CATALOG.md`, and
`EXPERIMENT_REGISTRY.md`.

---

## Current public-Web applicability

Current public-Web paywall/trial measurement: **UNAVAILABLE / NOT EMITTED**.

This is the intended current posture, not an outage.

It must not be represented as `0`, `0%`, or any other zero-valued metric.

Apple-device, backend, billing, or subscription observations must not fill a
public-Web numerator or denominator.

Repeated event rows do not establish unique-user counts.

A dashboard must preserve this state as unavailable. It must not render a
zero-valued Web paywall rate, trial-start rate, or trial-to-paid conversion and
must not borrow another channel’s data.

## Goals

1. Show only source-bound metrics whose channel, cohort, and attribution window
   are explicit.
2. Keep unavailable cells visibly distinct from a measured zero.
3. Preserve retention and cost views only where their source contracts exist.
4. Admit coaching or experiment views only with separate runtime and data proof.

## Segments and dimensions

| Segment / dimension | Use case | Applicability rule |
|--------------------|----------|--------------------|
| Channel | Prevent cross-channel substitution | Required for acquisition metrics |
| Tier (FREE / PRO / VIP) | General product segmentation | Backend tier truth does not prove Web acquisition |
| Cohort (activation date) | Retention analysis | Requires a source-bound activation event |
| Placement | Paywall analysis on admitted channels | Current public Web has no placement dataset |
| Source | Attribution | Must name the emitting production caller and channel |
| Scenario | Bounded coaching analysis | Requires separately admitted coaching telemetry |
| Variant | Experiment comparison | Requires a registry state proving the experiment ran |

## Data sources

| Dashboard | Primary data | Current public-Web rule |
|-----------|--------------|-------------------------|
| Funnel | Explicit client events plus channel-matched billing | Paywall/trial cells are UNAVAILABLE / NOT EMITTED |
| Retention | Source-bound activation and activity data | Do not infer activity from acquisition vocabulary |
| Cost | Source-bound spend and usage logs | Do not imply current public-Web AI |
| Coaching | Separately admitted coaching events | No dataset is implied by catalog entries |

Event schemas and field semantics live in `DATA_CATALOG.md` and
`METRICS_CATALOG.md`. A type, helper, test call, backend row, or feature flag
is not delivery or storage evidence.

## KPI and update frequency

| KPI | Owner | General cadence | Current public-Web applicability |
|-----|-------|-----------------|----------------------------------|
| Onboarding completion rate | Product + Growth | Daily when admitted | Independently source-bound |
| Activation (first_success) | Product + Data | Daily when admitted | Independently source-bound |
| Soft paywall view rate | Growth | Daily when admitted | UNAVAILABLE / NOT EMITTED |
| Trial start rate | Growth | Daily when admitted | UNAVAILABLE / NOT EMITTED |
| Trial → Paid conversion | Growth + Finance | Daily when admitted | UNAVAILABLE / NOT EMITTED |
| Retention D7 / D30 | Product + Data | Daily / Weekly when admitted | Independently source-bound |
| LLM cost per active user | Platform + Finance | Daily when admitted | Not evidence of current public-Web AI |
| Coaching metrics | Product + Data | Daily when admitted | Separate admission required |

## Guardrails and rollback

- Dashboards must not expose raw PII.
- Unique-user metrics require a stable deduplication key and explicit
  attribution window; event-row counts are not a substitute.
- A future public-Web monetization dashboard requires a new external product,
  legal, architecture, runtime, and data admission.
- Experiment guardrails apply only to experiments that the registry proves
  reached a running state.
