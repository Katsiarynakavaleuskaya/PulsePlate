# Metrics Catalog (Definitions)

**Purpose:** Prevent metric drift by making metric **semantics** explicit and reviewable.

**Status:** Canonical (docs-only). This file is the SoT for metric definitions.

---

## Metric template (copy/paste)

### <Metric Name>

#### Definition

1–2 sentences, unambiguous.

#### Formula

Provide a reproducible query or pseudocode (vendor-agnostic is fine):

```sql
-- Replace with the canonical query/pseudocode.
-- Include time window, cohort definition, and exclusions explicitly.
SELECT 1;
```

#### Owner

Who owns this metric definition and approves changes (team or person).

#### Update frequency

Real-time / daily / weekly (and when it is computed).

#### Change history

- YYYY-MM-DD: what changed and why (link PR/ADR if applicable)

---

## Activation (first_success)

#### Definition

Percent of new users who complete the first core success action within a defined time window after first launch.

#### Formula

```text
activation = users_with_first_success_within_window / eligible_new_users
```

#### Owner

Product + Data

#### Update frequency

Daily

#### Change history

- 2026-02-11: initial placeholder definition (vendor-agnostic)
- 2026-02-20: owner and update frequency defined for Wave 1 baseline

---

## Onboarding completion rate

#### Definition

Percent of first-launch sessions that complete onboarding in the same or subsequent session within the attribution window.

#### Formula

```text
onboarding_completion_rate =
  users_with_onboarding_completed / users_with_onboarding_started
```

#### Owner

Product + Growth

#### Update frequency

Daily

#### Change history

- 2026-02-20: initial Wave 1 definition

---

## Trial -> Paid conversion

#### Definition

Percent of users who start a trial and become paid subscribers within the configured conversion window.

#### Formula

```text
trial_to_paid_conversion =
  users_paid_after_trial / users_started_trial
```

#### Owner

Growth + Finance

#### Update frequency

Daily

#### Change history

- 2026-02-20: initial Wave 1 definition

---

## Retention D30

#### Definition

Percent of activated users who are active on day 30 after activation.

#### Formula

```text
retention_d30 =
  activated_users_active_on_day_30 / activated_users
```

#### Owner

Product + Data

#### Update frequency

Weekly

#### Change history

- 2026-02-20: initial Wave 1 definition

---

## LLM cost per active user

#### Definition

Total LLM/API inference spend divided by active users in the same aggregation window.

#### Formula

```text
llm_cost_per_active_user =
  total_llm_cost_window / active_users_window
```

#### Owner

Platform + Finance

#### Update frequency

Daily

#### Change history

- 2026-02-20: initial Wave 1 definition

---

## Soft paywall view rate

#### Definition

Percent of active users (within attribution window) who see the soft paywall trigger at least once.

#### Formula

```text
soft_paywall_view_rate =
  users_who_saw_soft_paywall / active_users_window
```

#### Owner

Growth

#### Update frequency

Daily

#### Change history

- 2026-02-21: initial Wave 1 definition (P0 Growth telemetry canon)

---

## Trial start rate

#### Definition

Percent of users eligible for trial (e.g. saw paywall, not already subscribed) who start a trial within the attribution window.

#### Formula

```text
trial_start_rate =
  users_started_trial / users_eligible_for_trial
```

#### Owner

Growth

#### Update frequency

Daily

#### Change history

- 2026-02-21: initial Wave 1 definition (P0 Growth telemetry canon)

---

## Retention D7

#### Definition

Percent of activated users who are active on day 7 after activation.

#### Formula

```text
retention_d7 =
  activated_users_active_on_day_7 / activated_users
```

#### Owner

Product + Data

#### Update frequency

Daily

#### Change history

- 2026-02-21: initial Wave 1 definition (P0 Growth telemetry canon)

---

## Event taxonomy (growth funnel)

Canonical event families and payload contracts for the growth funnel (onboarding → paywall → conversion → retention). Runtime implementation: `frontend/src/lib/telemetry/eventRegistry.ts`. This section is the doc SoT for semantics; code must stay aligned.

### Funnel stages and owners

| Stage | Owner | Cadence | Key events |
|-------|-------|---------|------------|
| Onboarding | Product + Growth | Daily | onboarding_started, onboarding_completed |
| Paywall | Growth | Daily | paywall_viewed, paywall_cta_clicked, vip_paywall_* |
| Conversion (trial) | Growth + Finance | Daily | trial_started |
| Retention | Product + Data | Daily / Weekly | retention_heartbeat (d1/d7/d30) |

### Growth funnel events (required fields)

| Event | Required fields | Context |
|-------|------------------|---------|
| onboarding_started | source, variant | First-run entry |
| onboarding_completed | source; optional: durationSec | Completion within session |
| paywall_viewed | source, placement, tierContext (free/pro/vip) | Soft/hard paywall impression |
| paywall_cta_clicked | source, ctaId, tierContext | CTA click for upgrade/trial |
| trial_started | source, planType | User started trial |
| retention_heartbeat | dayBucket (d1/d7/d30), source | Cohort activity signal |

### VIP / paywall UX events (required fields)

| Event | Required fields | Context |
|-------|------------------|---------|
| vip_module_viewed | source, vipEnabled | VIP module impression |
| vip_feature_clicked | featureName, source, isVip | Feature click behind gate |
| vip_paywall_viewed | source, context; optional: isRetry | VIP paywall view |
| vip_paywall_dismissed | source, dismissMethod; optional: viewDuration | Dismiss without converting |
| vip_upgrade_clicked | source, context; optional: isRetry | Upgrade CTA click |
| vip_gate_interacted | featureName, interactionType, isVip | Gate interaction |
| vip_badge_viewed | component, variant, isVip | Badge/upsell component view |

### Base payload (optional on all events)

- timestamp (number)
- sessionId (string)
- featureFlags (Record<string, boolean>)
