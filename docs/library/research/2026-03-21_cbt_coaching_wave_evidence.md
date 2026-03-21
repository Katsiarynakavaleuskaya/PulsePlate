# Evidence Log: CBT Coaching Wave

Date: 2026-03-21
Status: repo-grounded evidence only

## Inputs used

- User-supplied article idea list from the task prompt
- Repo contracts, insight docs, analytics docs, and scoped agent docs
- No external web/OSS research was required for this promotion lane

## Repo evidence summary

### 1. CBT knowledge already exists

- `docs/cbt/cognitive_restructuring.md` already defines the canonical five distortion
  patterns:
  - all-or-nothing thinking
  - catastrophizing
  - emotional reasoning
  - should statements
  - mental filtering
- `docs/cbt/thought_records.md` already supports a structured thought-record shape.
- `docs/psychology/motivation_theories.md` already provides autonomy, competence,
  relatedness, habit loops, and implementation-intention patterns for identity/action
  mapping.

### 2. Coaching runtime already exists

- `app/services/fitchef_runtime.py` already runs request-scoped CBT-informed coaching with
  explicit non-therapy boundaries.
- `app/routers/fitchef_insight.py` already exposes live VIP mascot routes:
  - `/api/v1/insight/fitchef`
  - `/api/v1/insight/fitchef/weekly-reflection`
  - `/api/v1/insight/fitchef/slip-support`
- `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md` already freezes the current public
  mascot canon as text-only and additive.

### 3. Structured coach contract already exists

- `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md` already freezes additive future
  route families for PRO and VIP structured coach surfaces.
- This makes the article ideas mappable to an existing contract lane rather than a new
  route family.

### 4. Safety and personalization boundaries already exist

- `docs/orchestration/FITCHEF_SAFE_PERSONALIZATION_PROTOCOL.md` forbids hidden memory,
  therapist drift, punitive language, and fabricated personal history.
- `docs/safety/WELLNESS_DISCLAIMER_CANONICAL.md` is the single source of truth for the
  public wellness disclaimer.

### 5. GTM/report scaffolding already exists

- `docs/audience_pack/AI_REPORT_TEMPLATES.md` already defines daily/weekly/monthly/
  quarterly report structure.
- `docs/marketing/GTM_NOTES_DEV_ONLY.md` already sets safe positioning for wellness-only
  copy.
- `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md` already enforces KPI-driven GTM
  hypotheses rather than activity lists.

### 6. Analytics scaffolding already exists

- `docs/analytics/METRICS_CATALOG.md` defines canonical metric semantics.
- `docs/analytics/EXPERIMENT_REGISTRY.md` already tracks planned experiments.
- `docs/analytics/DASHBOARD_BASELINE_REQUIREMENTS.md` already defines goals, segments, and
  KPI visibility.
- `docs/analytics/EXPERIMENTATION_FRAMEWORK.md` already defines falsifiable hypotheses and
  guardrails such as retention, support tickets, and LLM cost per user.

## Agent synthesis highlights

### Wellness scope

- Build the next wave as text-only, wellness-only, request-scoped coaching.
- Defer clinical, crisis, medical, hidden-memory, CV/image, realtime, and high-autonomy
  expansions.

### CBT structure

- Distortion Simulator should be a structured thought-record tool.
- Identity Loop Mapper should be a structured motivation/habit/identity tool.
- Both must keep the canonical five distortion labels and a non-clinical tone.

### GTM lane

- `Signal vs Noise` should stay a report/content lane, not a runtime feature.
- Founder content should be generated from weekly report synthesis rather than creating a
  parallel content framework.

### Measurement

- Distortion Simulator primary metric:
  `distortion_reframe_completion_rate`
- Identity Loop Mapper primary metric:
  `identity_loop_completion_rate`
- Both surfaces should use existing experiment guardrails plus wellness-safe language
  leakage checks.

## Final evidence-based decision

Promote one umbrella product wave now:

- `Distortion Simulator`
- `Identity Loop Mapper`
- `Signal vs Noise Reports`
- `FitChef Coaching Framework`

Defer:

- Movement Intelligence Library
- Personal Experiment Dashboard
- broader performance/essay-heavy productization outside the CBT coaching lane
