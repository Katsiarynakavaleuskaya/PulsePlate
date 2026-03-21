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

## 7d revisit rate (`7d_revisit_rate`)

#### Definition

Percent of users who complete a Distortion Simulator session and return to any
CBT coaching surface within 7 days.

#### Formula

```text
7d_revisit_rate =
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
