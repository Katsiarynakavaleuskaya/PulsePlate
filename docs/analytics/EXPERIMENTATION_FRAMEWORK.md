# Experimentation Framework (Wave 2)

**Date:** 2026-02-21
**Status:** Active policy (Wave 2)
**Exit Criteria:** This policy becomes permanent when: (1) first A/B experiment completes full lifecycle, (2) guardrail metrics are automated in analytics pipeline
**Purpose:** Establish repeatable A/B lifecycle with measurable guardrails for onboarding and paywall conversion optimization

---

## Experiment Lifecycle States

Every experiment follows a deterministic state machine:

```text
PROPOSED -> APPROVED -> RUNNING -> ANALYZING -> DECIDED
                |                       |
                v                       v
            REJECTED               ROLLBACK
```

### State Definitions

| State | Description | Entry Criteria | Exit Criteria | Owner |
|-------|-------------|----------------|---------------|-------|
| **PROPOSED** | Hypothesis documented, awaiting review | Experiment doc created with all required fields | Product + Growth approval | Experiment owner |
| **APPROVED** | Ready to launch, awaiting implementation | Hypothesis, metrics, guardrails, sample size defined | Implementation complete, feature flag ready | Product |
| **RUNNING** | Experiment live, collecting data | Feature flag enabled, telemetry verified | Sample size reached OR guardrail breach | Growth |
| **ANALYZING** | Data collection complete, awaiting decision | Minimum runtime elapsed, sample size met | Statistical analysis complete | Data |
| **DECIDED** | Final decision made (ship/revert/iterate) | Analysis reviewed by stakeholders | Decision documented with evidence | Product + Growth |
| **REJECTED** | Experiment not approved (hypothesis weak, guardrails insufficient) | Review identified blocking issues | Revised proposal OR explicit closure | Product |
| **ROLLBACK** | Experiment stopped early due to guardrail breach | Guardrail metric breached threshold | Rollback complete, incident documented | Growth |

---

## Required Fields for Experiment Proposal

Every experiment MUST include before moving to APPROVED state:

### 1. Hypothesis (Falsifiable)

```text
[Action/Change] will [improve/increase/decrease] [primary metric]
by at least [minimum detectable effect] for [target population]
without [guardrail metric] degrading by more than [threshold].
```

### 2. Primary Metric

- Single metric that determines success/failure
- Must be measurable within experiment window
- Must have baseline value documented

### 3. Guardrail Metrics (Non-negotiable)

| Guardrail | Threshold | Breach Action |
|-----------|-----------|---------------|
| D7 Retention | Drop > 2pp | Immediate rollback |
| App crash rate | Increase > 0.5% | Immediate rollback |
| Support ticket rate | Increase > 10% | Review within 24h |
| LLM cost per user | Increase > 15% | Review within 24h |

### 4. Sample Size and Runtime

- Minimum sample size calculated for 80% power at MDE
- Minimum runtime: 14 days (to capture weekly patterns)
- Maximum runtime: 45 days (prevent indefinite experiments)

### 5. Segmentation and Allocation

- Target population defined (all users, new users, specific tier)
- Allocation ratio documented (default: 50/50)
- Randomization method documented (user_id hash)

---

## Experiment Decision Framework

### Ship Criteria (Promote to 100%)

All of the following must be true:

- [x] Primary metric improved by at least MDE
- [x] Statistical significance reached (p < 0.05)
- [x] No guardrail metric breached threshold
- [x] Qualitative review shows no UX regressions
- [x] Implementation is production-ready (no temporary hacks)

### Revert Criteria (Roll back to control)

Any of the following triggers revert:

- [ ] Primary metric did not reach MDE
- [ ] Guardrail metric breached threshold
- [ ] Implementation has unacceptable technical debt
- [ ] Business context changed (experiment no longer relevant)

### Iterate Criteria (Run new variant)

Consider iteration when:

- Primary metric showed directional improvement but below MDE
- Qualitative feedback suggests variant hypothesis is partially correct
- Technical implementation revealed optimization opportunities

---

## Paywall Optimization Loop (Wave 2 Focus)

### Current State (Baseline)

| Metric | Baseline Value | Target (Wave 2) | Owner |
|--------|----------------|-----------------|-------|
| Soft paywall view rate | ~15% | ≥25% | Growth |
| Trial start rate | ~8% | ≥12% | Growth |
| Trial → Paid conversion | ~35% | ≥40% | Growth + Finance |

### Optimization Sequence

1. **Timing Optimization** (EXP-PWL-001): When to show paywall
2. **CTA Optimization** (EXP-PWL-002): How to frame the value proposition
3. **Friction Reduction** (EXP-PWL-003): Reduce steps to trial start

### Guardrails for Paywall Experiments

| Guardrail | Threshold | Rationale |
|-----------|-----------|-----------|
| D7 Retention | Drop ≤ 1pp | Aggressive paywall timing hurts retention |
| Onboarding completion | Drop ≤ 2pp | Early paywall blocks core value discovery |
| Support tickets (paywall-related) | Increase ≤ 5% | Confusion or perceived bait-and-switch |

---

## Onboarding Optimization Loop (Wave 2 Focus)

### Current State (Baseline)

| Metric | Baseline Value | Target (Wave 2) | Owner |
|--------|----------------|-----------------|-------|
| Onboarding completion rate | ~72% | ≥80% | Product + Growth |
| First success rate | ~45% | ≥55% | Product |
| D1 Retention | ~40% | ≥50% | Product + Data |

### Optimization Sequence

1. **Copy Clarity** (EXP-ONB-001): Value proposition messaging
2. **Flow Simplification** (EXP-ONB-002): Reduce onboarding steps
3. **Personalization** (EXP-ONB-003): Tailor flow to user intent

---

## Governance and Accountability

### Weekly Experiment Review (Every Tuesday)

1. **Active Experiments:** Status check, guardrail review
2. **Analyzing Experiments:** Decision readiness assessment
3. **Pipeline Health:** Telemetry verification, sample size tracking

### Experiment Documentation Requirements

- Proposal doc in `docs/experiments/EXP-XXX-NNN.md`
- Results summary in `docs/analytics/EXPERIMENT_REGISTRY.md`
- Decision rationale with evidence links

### Escalation Path

1. **Guardrail breach detected:** Experiment owner + Growth lead (same day)
2. **Statistical anomaly:** Data team review (within 24h)
3. **Business context change:** Product review (within 48h)

---

## References

- Experiment Registry: `docs/analytics/EXPERIMENT_REGISTRY.md`
- Metrics Catalog: `docs/analytics/METRICS_CATALOG.md`
- Analytics Index: `docs/analytics/ANALYTICS_INDEX.md`
- Event Taxonomy: `frontend/src/lib/telemetry/eventRegistry.ts`

---

## KPIs (Wave 2 Target)

- **Experiment velocity:** ≥3 experiments shipped per quarter
- **Decision turnaround:** ≤5 days from analysis complete to decision
- **Guardrail breach rate:** 0 undetected breaches

---

**Last updated:** 2026-02-21
# Experimentation Framework (Wave 2)

**Date:** 2026-02-21
**Status:** Active policy (Wave 2)
**Exit Criteria:** This policy becomes permanent when: (1) first A/B experiment completes full lifecycle, (2) guardrail metrics are automated in analytics pipeline
**Purpose:** Establish repeatable A/B lifecycle with measurable guardrails for onboarding and paywall conversion optimization

---

## Experiment Lifecycle States

Every experiment follows a deterministic state machine:

```text
PROPOSED -> APPROVED -> RUNNING -> ANALYZING -> DECIDED
                |                       |
                v                       v
            REJECTED               ROLLBACK
```

### State Definitions

| State | Description | Entry Criteria | Exit Criteria | Owner |
|-------|-------------|----------------|---------------|-------|
| **PROPOSED** | Hypothesis documented, awaiting review | Experiment doc created with all required fields | Product + Growth approval | Experiment owner |
| **APPROVED** | Ready to launch, awaiting implementation | Hypothesis, metrics, guardrails, sample size defined | Implementation complete, feature flag ready | Product |
| **RUNNING** | Experiment live, collecting data | Feature flag enabled, telemetry verified | Sample size reached OR guardrail breach | Growth |
| **ANALYZING** | Data collection complete, awaiting decision | Minimum runtime elapsed, sample size met | Statistical analysis complete | Data |
| **DECIDED** | Final decision made (ship/revert/iterate) | Analysis reviewed by stakeholders | Decision documented with evidence | Product + Growth |
| **REJECTED** | Experiment not approved (hypothesis weak, guardrails insufficient) | Review identified blocking issues | Revised proposal OR explicit closure | Product |
| **ROLLBACK** | Experiment stopped early due to guardrail breach | Guardrail metric breached threshold | Rollback complete, incident documented | Growth |

---

## Required Fields for Experiment Proposal

Every experiment MUST include before moving to APPROVED state:

### 1. Hypothesis (Falsifiable)

```text
[Action/Change] will [improve/increase/decrease] [primary metric]
by at least [minimum detectable effect] for [target population]
without [guardrail metric] degrading by more than [threshold].
```

### 2. Primary Metric

- Single metric that determines success/failure
- Must be measurable within experiment window
- Must have baseline value documented

### 3. Guardrail Metrics (Non-negotiable)

| Guardrail | Threshold | Breach Action |
|-----------|-----------|---------------|
| D7 Retention | Drop > 2pp | Immediate rollback |
| App crash rate | Increase > 0.5% | Immediate rollback |
| Support ticket rate | Increase > 10% | Review within 24h |
| LLM cost per user | Increase > 15% | Review within 24h |

### 4. Sample Size and Runtime

- Minimum sample size calculated for 80% power at MDE
- Minimum runtime: 14 days (to capture weekly patterns)
- Maximum runtime: 45 days (prevent indefinite experiments)

### 5. Segmentation and Allocation

- Target population defined (all users, new users, specific tier)
- Allocation ratio documented (default: 50/50)
- Randomization method documented (user_id hash)

---

## Experiment Decision Framework

### Ship Criteria (Promote to 100%)

All of the following must be true:

- [x] Primary metric improved by at least MDE
- [x] Statistical significance reached (p < 0.05)
- [x] No guardrail metric breached threshold
- [x] Qualitative review shows no UX regressions
- [x] Implementation is production-ready (no temporary hacks)

### Revert Criteria (Roll back to control)

Any of the following triggers revert:

- [ ] Primary metric did not reach MDE
- [ ] Guardrail metric breached threshold
- [ ] Implementation has unacceptable technical debt
- [ ] Business context changed (experiment no longer relevant)

### Iterate Criteria (Run new variant)

Consider iteration when:

- Primary metric showed directional improvement but below MDE
- Qualitative feedback suggests variant hypothesis is partially correct
- Technical implementation revealed optimization opportunities

---

## Paywall Optimization Loop (Wave 2 Focus)

### Current State (Baseline)

| Metric | Baseline Value | Target (Wave 2) | Owner |
|--------|----------------|-----------------|-------|
| Soft paywall view rate | ~15% | ≥25% | Growth |
| Trial start rate | ~8% | ≥12% | Growth |
| Trial → Paid conversion | ~35% | ≥40% | Growth + Finance |

### Optimization Sequence

1. **Timing Optimization** (EXP-PWL-001): When to show paywall
2. **CTA Optimization** (EXP-PWL-002): How to frame the value proposition
3. **Friction Reduction** (EXP-PWL-003): Reduce steps to trial start

### Guardrails for Paywall Experiments

| Guardrail | Threshold | Rationale |
|-----------|-----------|-----------|
| D7 Retention | Drop ≤ 1pp | Aggressive paywall timing hurts retention |
| Onboarding completion | Drop ≤ 2pp | Early paywall blocks core value discovery |
| Support tickets (paywall-related) | Increase ≤ 5% | Confusion or perceived bait-and-switch |

---

## Onboarding Optimization Loop (Wave 2 Focus)

### Current State (Baseline)

| Metric | Baseline Value | Target (Wave 2) | Owner |
|--------|----------------|-----------------|-------|
| Onboarding completion rate | ~72% | ≥80% | Product + Growth |
| First success rate | ~45% | ≥55% | Product |
| D1 Retention | ~40% | ≥50% | Product + Data |

### Optimization Sequence

1. **Copy Clarity** (EXP-ONB-001): Value proposition messaging
2. **Flow Simplification** (EXP-ONB-002): Reduce onboarding steps
3. **Personalization** (EXP-ONB-003): Tailor flow to user intent

---

## Governance and Accountability

### Weekly Experiment Review (Every Tuesday)

1. **Active Experiments:** Status check, guardrail review
2. **Analyzing Experiments:** Decision readiness assessment
3. **Pipeline Health:** Telemetry verification, sample size tracking

### Experiment Documentation Requirements

- Proposal doc in `docs/experiments/EXP-XXX-NNN.md`
- Results summary in `docs/analytics/EXPERIMENT_REGISTRY.md`
- Decision rationale with evidence links

### Escalation Path

1. **Guardrail breach detected:** Experiment owner + Growth lead (same day)
2. **Statistical anomaly:** Data team review (within 24h)
3. **Business context change:** Product review (within 48h)

---

## References

- Experiment Registry: `docs/analytics/EXPERIMENT_REGISTRY.md`
- Metrics Catalog: `docs/analytics/METRICS_CATALOG.md`
- Analytics Index: `docs/analytics/ANALYTICS_INDEX.md`
- Event Taxonomy: `frontend/src/lib/telemetry/eventRegistry.ts`

---

## KPIs (Wave 2 Target)

- **Experiment velocity:** ≥3 experiments shipped per quarter
- **Decision turnaround:** ≤5 days from analysis complete to decision
- **Guardrail breach rate:** 0 undetected breaches

---

**Last updated:** 2026-02-21
