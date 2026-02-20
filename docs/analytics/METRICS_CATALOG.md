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
