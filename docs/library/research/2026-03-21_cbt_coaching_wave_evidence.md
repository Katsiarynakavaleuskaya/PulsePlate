# Evidence Log: CBT Coaching Wave

Date: 2026-03-21
Status: repo-grounded evidence only

## Inputs used

- User-supplied article idea list from the task prompt
- Repo contracts, insight docs, analytics docs, and scoped agent docs
- No external web/OSS research was required for this promotion lane

## Repo evidence summary

All repo-grounded claims below use explicit `path:line-line` anchors so the
promotion is auditable under the docs evidence contract.

### 1. CBT knowledge already exists

- `docs/cbt/cognitive_restructuring.md:9-49` defines the canonical five
  distortion patterns:
  - all-or-nothing thinking
  - catastrophizing
  - emotional reasoning
  - should statements
  - mental filtering
- `docs/cbt/thought_records.md:15-89` supports a structured thought-record
  shape with situation, automatic thoughts, emotions, evidence, balanced
  thought, and outcome.
- `docs/psychology/motivation_theories.md:5-37` and
  `docs/psychology/motivation_theories.md:125-163` provide autonomy,
  competence, relatedness, habit loops, and implementation-intention patterns
  for identity/action mapping.

### 2. Coaching runtime already exists

- `app/services/fitchef_runtime.py:85-118` runs request-scoped CBT-informed
  coaching with explicit non-therapy and non-medical boundaries.
- `app/routers/fitchef_insight.py:45-75`,
  `app/routers/fitchef_insight.py:133-150`, and
  `app/routers/fitchef_insight.py:214-230` expose the live VIP mascot routes:
  - `/api/v1/insight/fitchef`
  - `/api/v1/insight/fitchef/weekly-reflection`
  - `/api/v1/insight/fitchef/slip-support`
- `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md:21-33` and
  `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md:56-69` freeze the current
  public mascot canon as text-only and additive.

### 3. Structured coach contract already exists

- `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md:17-24` and
  `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md:39-53` freeze additive
  future route families for PRO and VIP structured coach surfaces.
- This makes the article ideas mappable to an existing contract lane rather than a new
  route family.

### 4. Safety and personalization boundaries already exist

- `docs/orchestration/FITCHEF_SAFE_PERSONALIZATION_PROTOCOL.md:20-58` and
  `docs/orchestration/FITCHEF_SAFE_PERSONALIZATION_PROTOCOL.md:103-149`
  forbid hidden memory, therapist drift, punitive language, and fabricated
  personal history.
- `docs/safety/WELLNESS_DISCLAIMER_CANONICAL.md:9-25` is the single source of
  truth for the public wellness disclaimer.

### 5. GTM/report scaffolding already exists

- `docs/audience_pack/AI_REPORT_TEMPLATES.md:7-17`,
  `docs/audience_pack/AI_REPORT_TEMPLATES.md:67-77`, and
  `docs/audience_pack/AI_REPORT_TEMPLATES.md:147-157` define the
  daily/weekly/monthly/quarterly report structure plus action-driven GTM
  expectations.
- `docs/marketing/GTM_NOTES_DEV_ONLY.md:8-20` and
  `docs/marketing/GTM_NOTES_DEV_ONLY.md:40-42` set safe positioning for
  wellness-only copy.
- `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md:13-17`,
  `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md:25-33`, and
  `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md:93-97` enforce KPI-driven
  GTM hypotheses rather than activity lists.

### 6. Analytics scaffolding already exists

- `docs/analytics/METRICS_CATALOG.md:365-670` defines canonical metric
  semantics for the CBT coaching wave metrics and guardrails.
- `docs/analytics/EXPERIMENT_REGISTRY.md:12-44` tracks the umbrella CBT coaching
  experiment row alongside the broader experiment registry.
- `docs/analytics/DASHBOARD_BASELINE_REQUIREMENTS.md:11-60` defines dashboard
  goals, segments, and KPI visibility.
- `docs/analytics/EXPERIMENTATION_FRAMEWORK.md:35-104` defines falsifiable
  hypotheses and guardrails such as retention, support tickets, and LLM cost
  per user.

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
