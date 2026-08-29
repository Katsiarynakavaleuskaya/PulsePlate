# Metrics Catalog (Definitions)

**Purpose:** Prevent metric drift by making metric **semantics** explicit and reviewable.

**Status:** Canonical (docs-only). This file is the SoT for metric definitions.

---

## Current public-Web applicability

Current public-Web paywall/trial measurement: **UNAVAILABLE / NOT EMITTED**.

This is the intended current posture, not an outage.

It must not be represented as `0`, `0%`, or any other zero-valued metric.

Apple-device, backend, billing, or subscription observations must not fill a
public-Web numerator or denominator.

Repeated event rows do not establish unique-user counts.

Event enums, payload schemas, callable helpers, unit-test calls, backend rows,
and Apple-product vocabulary are not proof of a public-Web production caller,
delivery, storage, queryable data, attribution, or entitlement acquisition.

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

## FitChef support outcome writes

#### Definition

`fitchef_support_outcome_writes_total{support_need,outcome,result}` counts only
schema-valid, authenticated, feature-admitted support-outcome write decisions.
Its closed vocabulary is two needs (`daily_structure`, `weekly_structure`), two
outcomes (`acknowledged`, `dismissed`), and three results (`recorded`,
`replayed`, `rejected`), for at most 12 series. `rejected` means only a
divergent idempotency replay (`409`); auth, validation, rate-limit, disabled,
and store-unavailable responses remain in generic HTTP metrics.

#### Formula

```text
increment exactly one closed labelset after recorded/replayed,
or after a schema-valid divergent replay; emit no subject, event id, raw path,
timestamp, goal, plan, credential, or error label
```

#### Owner

Backend + Product Analytics + Privacy

#### Update frequency

Real-time, best-effort per accepted write decision

#### Change history

- 2026-08-27: added the privacy-bounded FitChef support-outcome counter

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

For a separately admitted channel, the percent of distinct users who start a
trial and become paid subscribers within the configured conversion window.
The channel, eligibility policy, and attribution window must be explicit.

#### Formula

```text
trial_to_paid_conversion =
  distinct_users_paid_after_trial / distinct_users_started_trial
```

For the current public Web this metric is **UNAVAILABLE / NOT EMITTED** and is
not computed. A billing or Apple-device observation cannot supply either side
of the public-Web ratio.

#### Owner

Growth + Finance

#### Update frequency

Daily only for a separately admitted, source-bound channel; not computed for
the current public Web.

#### Change history

- 2026-02-20: initial Wave 1 definition
- 2026-08-29: bounded the definition by channel and marked current public-Web data unavailable

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

For a separately admitted channel, the percent of distinct active users who see
an admitted soft-paywall surface at least once within the attribution window.

#### Formula

```text
soft_paywall_view_rate =
  distinct_users_who_saw_soft_paywall / distinct_active_users_window
```

For the current public Web this metric is **UNAVAILABLE / NOT EMITTED** and is
not computed. Defined event vocabulary and repeated rows do not prove a unique
user or a production impression.

#### Owner

Growth

#### Update frequency

Daily only for a separately admitted, source-bound channel; not computed for
the current public Web.

#### Change history

- 2026-02-21: initial Wave 1 definition (P0 Growth telemetry canon)
- 2026-08-29: bounded the definition by channel and marked current public-Web data unavailable

---

## Trial start rate

#### Definition

For a separately admitted channel, the percent of distinct trial-eligible users
who start a trial within the explicit attribution window.

#### Formula

```text
trial_start_rate =
  distinct_users_started_trial / distinct_users_eligible_for_trial
```

For the current public Web this metric is **UNAVAILABLE / NOT EMITTED** and is
not computed. Backend eligibility, billing, or Apple-device activity cannot
substitute for a public-Web trial-start caller.

#### Owner

Growth

#### Update frequency

Daily only for a separately admitted, source-bound channel; not computed for
the current public Web.

#### Change history

- 2026-02-21: initial Wave 1 definition (P0 Growth telemetry canon)
- 2026-08-29: bounded the definition by channel and marked current public-Web data unavailable

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

## Distortion reframe completion rate (`distortion_reframe_completion_rate`)

#### Definition

Percent of started Distortion Simulator sessions that reach a completed balanced
reframe output in the same attribution window.

#### Formula

```text
distortion_reframe_completion_rate =
  completed_distortion_reframe_sessions / started_distortion_reframe_sessions
```

#### Owner

Product + Wellness AI

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial definition for the CBT Coaching Wave docs-first contract

---

## Challenge acceptance rate (`challenge_acceptance_rate`)

#### Definition

Percent of completed Distortion Simulator sessions where the user explicitly
accepts or keeps the suggested challenge/reframe step.

#### Formula

```text
challenge_acceptance_rate =
  sessions_with_accepted_challenge / completed_distortion_reframe_sessions
```

#### Owner

Product + Wellness AI

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial definition for the CBT Coaching Wave docs-first contract

---

## Next action commit rate (`next_action_commit_rate`)

#### Definition

Percent of completed Distortion Simulator sessions where the user commits to one
explicit next small action.

#### Formula

```text
next_action_commit_rate =
  sessions_with_next_action_commit / completed_distortion_reframe_sessions
```

#### Owner

Product + Wellness AI

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial definition for the CBT Coaching Wave docs-first contract

---

## 7d revisit rate (`revisit_rate_7d`)

#### Definition

Percent of users who complete a Distortion Simulator session and return to any
CBT coaching surface within 7 days.

#### Formula

```text
revisit_rate_7d =
  users_who_revisit_cbt_surface_within_7d / users_who_completed_distortion_reframe
```

#### Owner

Product + Data

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial definition for the CBT Coaching Wave docs-first contract

---

## Identity loop completion rate (`identity_loop_completion_rate`)

#### Definition

Percent of started Identity Loop Mapper sessions that return the full
identity-loop response envelope within the attribution window.

#### Formula

```text
identity_loop_completion_rate =
  completed_identity_loop_sessions / started_identity_loop_sessions
```

#### Owner

Product + Wellness AI

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial definition for the CBT Coaching Wave docs-first contract

---

## Identity to action followthrough 7d (`identity_to_action_followthrough_7d`)

#### Definition

Percent of completed Identity Loop Mapper sessions where the recommended
replacement action is completed or explicitly confirmed within 7 days.

#### Formula

```text
identity_to_action_followthrough_7d =
  sessions_with_followthrough_within_7d / completed_identity_loop_sessions
```

#### Owner

Product + Data

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial definition for the CBT Coaching Wave docs-first contract

---

## Repeat reflection rate (`repeat_reflection_rate`)

#### Definition

Percent of users who complete one Identity Loop Mapper session and complete at
least one additional reflection session inside the attribution window.

#### Formula

```text
repeat_reflection_rate =
  users_with_repeat_identity_reflection / users_who_completed_identity_loop
```

#### Owner

Product + Wellness AI

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial definition for the CBT Coaching Wave docs-first contract

---

## Goal alignment score (`goal_alignment_score`)

#### Definition

Canonical scored measure of how well the returned action plan aligns with the
user-stated goal and the structured coaching context for the same session.

#### Formula

```text
goal_alignment_score =
  aligned_goal_checks_passed / total_goal_alignment_checks
```

#### Owner

Product + AI Quality

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial definition for the CBT Coaching Wave docs-first contract

---

## Support ticket rate (`support_ticket_rate`)

#### Definition

Percent of active users in the aggregation window who create a support ticket
linked to the relevant product surface or experiment.

#### Formula

```text
support_ticket_rate =
  users_with_support_ticket_window / active_users_window
```

#### Owner

Support + Product

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial definition for the CBT Coaching Wave docs-first contract

---

## Therapy or medical language leakage rate (`therapy_medical_language_leakage_rate`)

#### Definition

Percent of sampled CBT coaching responses in the aggregation window that breach
the wellness-only language boundary by introducing therapy, diagnosis, or
medical-advice phrasing.

#### Formula

```text
therapy_medical_language_leakage_rate =
  responses_flagged_for_boundary_leakage / sampled_cbt_coaching_responses
```

#### Owner

AI Quality + Safety

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial definition for the CBT Coaching Wave docs-first contract

---

## Session abandonment rate (`session_abandonment_rate`)

#### Definition

Percent of started CBT coaching sessions that end before a usable coaching
result or explicit dismissal event is produced.

#### Formula

```text
session_abandonment_rate =
  abandoned_cbt_coaching_sessions / started_cbt_coaching_sessions
```

#### Owner

Product + Data

#### Update frequency

Daily

#### Change history

- 2026-03-21: initial definition for the CBT Coaching Wave docs-first contract

---

## Event taxonomy (growth funnel + coaching)

Canonical event families and payload contracts for the growth funnel
(onboarding → paywall → conversion → retention) plus the planned coaching loop
contract targets (start → structured reflection → next action → revisit).
The registry in `frontend/src/lib/telemetry/eventRegistry.ts` defines
compatibility vocabulary only. A defined enum, schema, callable helper, or test
call does not prove a production call, delivery, storage, queryable dataset, or
attribution. Coaching events below stay contract-frozen until a separate
runtime lane admits them. Current public-Web paywall and trial events are
**UNAVAILABLE / NOT EMITTED**.

### Funnel stages and owners

| Stage | Owner | Cadence | Key events |
|-------|-------|---------|------------|
| Onboarding | Product + Growth | Daily | onboarding_started, onboarding_completed |
| Paywall | Growth | When separately admitted | compatibility: paywall_viewed, paywall_cta_clicked, vip_paywall_* |
| Conversion (trial) | Growth + Finance | When separately admitted | compatibility: trial_started |
| Retention | Product + Data | Daily / Weekly | retention_heartbeat (d1/d7/d30) |
| Coaching | Product + Data | Daily | planned: coaching_session_started, coaching_reframe_completed, coaching_identity_map_completed, coaching_next_action_committed, coaching_revisit |

### Growth funnel events (required fields)

| Event | Required fields | Context |
|-------|------------------|---------|
| onboarding_started | source, variant | First-run entry |
| onboarding_completed | source; optional: durationSec | Completion within session |
| paywall_viewed | source, placement, tierContext (free/pro/vip) | Compatibility payload; not emitted by current public Web |
| paywall_cta_clicked | source, ctaId, tierContext | Compatibility payload; not emitted by current public Web |
| trial_started | source, planType | Compatibility payload; not emitted by current public Web |
| retention_heartbeat | dayBucket (d1/d7/d30), source | Cohort activity signal |
| coaching_session_started | scenario, source, variant, tier, sessionId | Planned coaching loop entry for one bounded surface |
| coaching_reframe_completed | scenario, source, variant, tier, sessionId | Planned Distortion Simulator completion signal |
| coaching_identity_map_completed | scenario, source, variant, tier, sessionId | Planned Identity Loop Mapper completion signal |
| coaching_next_action_committed | scenario, source, variant, tier, sessionId, goalId? | Planned explicit next-step commitment after coaching |
| coaching_revisit | scenario, source, variant, tier, sessionId | Planned return signal for coaching continuity |

### VIP / paywall UX events (required fields)

These rows define compatibility payloads. They do not establish current
public-Web callers or acquisition attribution.

| Event | Required fields | Context |
|-------|------------------|---------|
| vip_module_viewed | source, vipEnabled | VIP module impression |
| vip_feature_clicked | featureName, source, isVip | Feature click behind gate |
| vip_paywall_viewed | source, context; optional: isRetry | VIP paywall view |
| vip_paywall_dismissed | source, dismissMethod; optional: viewDuration | Dismiss without converting |
| vip_upgrade_clicked | source, context; optional: isRetry | Upgrade CTA click |
| vip_gate_interacted | featureName, interactionType, isVip | Gate interaction |
| vip_badge_viewed | component, variant, isVip | Badge/upsell component view |

Planning paywall ledger note:
- Historical backend planning records map `source_surface` / `trigger_reason`
  inputs at `app/routers/paywall_analytics.py:89-90` and store those fields at
  `app/models/paywall_analytics.py:47-48`. They cannot fill a current public-Web
  numerator or denominator or prove a browser event was emitted.
- Compatibility vocabulary retained in the repository:
  - `bmi_soft_paywall` is historical/test compatibility vocabulary; no current
    frontend owner is asserted here.
  - `post_bmi` is current backend trigger-reason vocabulary at
    `app/services/intervention_trigger_engine.py:29` and
    `app/schemas/intervention.py:12`.
  - `pro_daily_plate` / `targets_ready` (see `app/services/intervention_trigger_engine.py:41`, `app/services/intervention_trigger_engine.py:43`, `app/schemas/intervention.py:11`, `app/schemas/intervention.py:12`)

### Base payload (optional on all events)

- timestamp (number)
- sessionId (string)
- featureFlags (Record<string, boolean>)
