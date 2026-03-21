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

## Distortion reframe completion rate

#### Definition

Percent of Distortion Simulator sessions that reach a completed reframe state with at least
one accepted balanced reframe.

#### Formula

```text
distortion_reframe_completion_rate =
  completed_distortion_reframe_sessions / distortion_simulator_starts
```

#### Owner

Product + Data

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial CBT Coaching Wave definition

---

## Identity loop completion rate

#### Definition

Percent of Identity Loop Mapper sessions that complete the identity-loop structure and
produce an explicit replacement action.

#### Formula

```text
identity_loop_completion_rate =
  completed_identity_loop_sessions / identity_loop_mapper_starts
```

#### Owner

Product + Data

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial CBT Coaching Wave definition

---

## Next action commit rate

#### Definition

Percent of completed CBT coaching sessions where the user explicitly commits to one small
next action.

#### Formula

```text
next_action_commit_rate =
  sessions_with_next_action_commit / completed_coaching_sessions
```

#### Owner

Product + Growth

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial CBT Coaching Wave definition

---

## Identity to action followthrough D7

#### Definition

Percent of users who complete an Identity Loop Mapper session and then record the mapped
replacement action within 7 days.

#### Formula

```text
identity_to_action_followthrough_d7 =
  users_with_identity_loop_and_followthrough_by_day_7 /
  users_with_completed_identity_loop
```

#### Owner

Product + Data

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial CBT Coaching Wave definition

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

## Correctness pass rate

#### Definition

Percent of replay cases where an answer includes every required fact from the immutable offline oracle.

#### Formula

```text
correctness_pass_rate =
  cases_with_all_required_facts / total_replay_cases
```

#### Owner

AI Quality + Orchestration

#### Update frequency

Per offline replay run

#### Change history

- 2026-03-14: initial definition for the logic + philosophy replay contract

---

## Unsupported claim rate

#### Definition

Share of extracted answer claims that do not match any supported oracle snippet for the replay case.

#### Formula

```text
unsupported_claim_rate =
  unsupported_claims / total_extracted_claims
```

#### Owner

AI Quality + Orchestration

#### Update frequency

Per offline replay run

#### Change history

- 2026-03-14: initial definition for the logic + philosophy replay contract

---

## Contradiction rate

#### Definition

Percent of replay cases whose answer contains at least one deterministic contradiction detected by the offline checker.

#### Formula

```text
contradiction_rate =
  replay_cases_with_contradiction / total_replay_cases
```

#### Owner

AI Quality + Orchestration

#### Update frequency

Per offline replay run

#### Change history

- 2026-03-14: initial definition for the logic + philosophy replay contract

---

## First-pass readiness proxy

#### Definition

Percent of replay cases that pass the full offline readiness bundle on the first scored answer: correctness pass, zero unsupported claims, zero contradictions, and usefulness floor met.

#### Formula

```text
first_pass_readiness_proxy =
  replay_cases_ready_on_first_score / total_replay_cases
```

#### Owner

AI Quality + Orchestration

#### Update frequency

Per offline replay run

#### Change history

- 2026-03-14: initial definition for the logic + philosophy replay contract

---

## Event taxonomy (growth funnel + coaching)

Canonical event families and payload contracts for the growth funnel
(onboarding → paywall → conversion → retention) plus the planned coaching loop
contract targets (start → structured reflection → next action → revisit).
Runtime implementation today remains limited to the growth-funnel registry in
`frontend/src/lib/telemetry/eventRegistry.ts`; coaching events below stay
contract-frozen until the registry ships in a runtime lane. This section is the
doc SoT for semantics and planned names, but planned coaching events must not be
treated as emitted runtime telemetry yet.

### Funnel stages and owners

| Stage | Owner | Cadence | Key events |
|-------|-------|---------|------------|
| Onboarding | Product + Growth | Daily | onboarding_started, onboarding_completed |
| Paywall | Growth | Daily | paywall_viewed, paywall_cta_clicked, vip_paywall_* |
| Conversion (trial) | Growth + Finance | Daily | trial_started |
| Retention | Product + Data | Daily / Weekly | retention_heartbeat (d1/d7/d30) |
| Coaching | Product + Data | Daily | planned: coaching_session_started, coaching_reframe_completed, coaching_identity_map_completed, coaching_next_action_committed, coaching_revisit |

### Growth funnel events (required fields)

| Event | Required fields | Context |
|-------|------------------|---------|
| onboarding_started | source, variant | First-run entry |
| onboarding_completed | source; optional: durationSec | Completion within session |
| paywall_viewed | source, placement, tierContext (free/pro/vip) | Soft/hard paywall impression |
| paywall_cta_clicked | source, ctaId, tierContext | CTA click for upgrade/trial |
| trial_started | source, planType | User started trial |
| retention_heartbeat | dayBucket (d1/d7/d30), source | Cohort activity signal |
| coaching_session_started | scenario, source, variant, tier, sessionId | Planned coaching loop entry for one bounded surface |
| coaching_reframe_completed | scenario, source, variant, tier, sessionId | Planned Distortion Simulator completion signal |
| coaching_identity_map_completed | scenario, source, variant, tier, sessionId | Planned Identity Loop Mapper completion signal |
| coaching_next_action_committed | scenario, source, variant, tier, sessionId, goalId? | Planned explicit next-step commitment after coaching |
| coaching_revisit | scenario, source, variant, tier, sessionId | Planned return signal for coaching continuity |

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
