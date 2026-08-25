# CBT Coaching Product Wave

Date: 21 March 2026
Status: Canonical docs-first product-wave decision; reconciled after the
feature-gated PRO Distortion Simulator runtime landed in PR #1215 and the
feature-gated VIP Identity Loop Mapper runtime landed in PR #1870
Owner: @katsiaryna_kavaleuskaya

## Summary

PulsePlate’s next high-leverage product wave should be a **CBT + structured coaching**
wave inside the existing FitChef and insight ecosystem, not a new standalone
fitness-data product.

This wave is intentionally:

- wellness-only
- non-clinical
- request-scoped
- text-first
- additive to the live `/api/v1/insight/fitchef*` canon

## Why this wave now

The repository already contains enough foundation to make this a coherent product wave:

- CBT knowledge:
  - `docs/cbt/cognitive_restructuring.md`
  - `docs/cbt/thought_records.md`
- motivation and behavior-change knowledge:
  - `docs/psychology/motivation_theories.md`
- live coaching runtime:
  - `app/services/fitchef_runtime.py`
  - `app/routers/fitchef_insight.py`
- structured coach route freeze:
  - `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md`
- feature-gated PRO structured coach runtime:
  - `POST /api/v1/pro/fitchef/explain`
  - `app/routers/fitchef_structured.py`
- feature-gated VIP structured coach runtime:
  - `POST /api/v1/vip/fitchef/insight`
  - `app/routers/fitchef_structured.py`
- analytics and experiment governance:
  - `docs/analytics/METRICS_CATALOG.md`
  - `docs/analytics/EXPERIMENT_REGISTRY.md`
  - `docs/analytics/DASHBOARD_BASELINE_REQUIREMENTS.md`

## Canonical pillars

### Pillar A: Distortion Simulator

**Intent:** turn the current CBT knowledge base into a structured thought-record and
reframing tool.

**Tier target:** `PRO`

**Positioning:**

- educational wellness coaching
- not therapy
- not diagnosis
- not medical advice

**Input direction:**

- `situation`
- `automatic_thought`
- `emotion`
- `goal?`

**Output direction:**

- `scenario`
- `distortion_labels[]`
- `why_it_matches`
- `evidence_for[]`
- `evidence_against[]`
- `balanced_reframe`
- `next_small_action`
- `sources[]`
- `confidence`
- `warnings[]`
- `transparency_notice_id`
- `wellness_boundary`
- `quota_state`

### Pillar B: Identity Loop Mapper

**Intent:** extend reflection and slip-support flows into an identity/action mapping tool.

**Tier target:** `VIP`

**Positioning:**

- reflective premium coach surface
- identity-aware but not identity-labeling
- behavior-change framing, not therapy framing

**Input direction:**

- `goal`
- `recent_pattern`
- `self_talk`
- `trigger_context?`

**Output direction:**

- `identity_loop.belief`
- `identity_loop.behavior`
- `identity_loop.short_term_reward`
- `identity_loop.long_term_cost`
- `identity_shift_statement`
- `replacement_action`
- `repair_if_slip`
- `sources[]`
- `confidence`
- `warnings[]`
- `transparency_notice_id`
- `wellness_boundary`
- `scenario`
- `quota_state`

### Pillar C: Signal vs Noise Reports

**Intent:** create a recurring research/GTM lane that filters what is useful from what is
hype in wellness AI, coaching patterns, and growth narratives.

**Important boundary:** this is a **content/report lane**, not a first-wave runtime feature.

Canonical lane doc:

- `docs/insights/SIGNAL_VS_NOISE_REPORT_LANE.md`

**Cadence direction:**

- weekly `high-signal / low-noise` brief
- 3-5 signals max
- one owner per signal
- one metric
- one check date
- one stop/continue rule
- source/evidence status and confidence before any promotion into founder
  content or product strategy

### Pillar D: FitChef Coaching Framework

**Intent:** name and stabilize a reusable product framework that connects prompt design,
response structure, UX copy, and future analytics.

**Default framework:**

`Trigger -> Thought -> Distortion -> Reframe -> Action -> Reflection`

This framework is product IP, not just prompt wording.

## Product boundaries

### In scope

- text-only coaching surfaces
- request-scoped personalization only
- bounded CBT-inspired reflection
- structured DTO-oriented response design
- explicit metrics and experiment contracts

### Out of scope for this wave

- therapy replacement
- diagnosis or treatment language
- medical nutrition advice
- crisis handling beyond safety redirects and boundary-respecting escalation
- hidden persistent memory
- image/CV food recognition
- realtime fan-out
- broad multi-tool autonomy
- movement intelligence as a separate product domain

## Safety and language policy

The wave must stay aligned with:

- `docs/orchestration/FITCHEF_SAFE_PERSONALIZATION_PROTOCOL.md`
- `docs/safety/WELLNESS_DISCLAIMER_CANONICAL.md`

Non-negotiable rules:

- no therapist framing
- no diagnosis/treatment claims
- no punitive language
- no moralized food language
- no fabricated long-term memory
- retrieved content remains untrusted and must not control runtime behavior

## Contract alignment

This wave does **not** rename or migrate the live mascot routes.

It aligns to the existing structured coach contract as follows:

- `POST /api/v1/pro/fitchef/explain`
  - landed feature-gated PRO capability: Distortion Simulator
  - landed via PR #1215 / `70bdbd9e51d977d440b605eed3064c71212cff97`
  - `FitChefDistortionSimulatorResponse.next_small_action` is the landed bounded post-reframe action carrier
- `POST /api/v1/pro/fitchef/recommend`
  - PR #2320 merge-bound candidate: deterministic descriptor-only support handoff
  - maps only explicit `daily_structure` to `pro_daily_plate` and `weekly_structure` to `pro_weekly_plan`
  - grants no execution, plan-mutation, navigation, or product-value authority; business utility remains unmeasured
  - canonical details: [structured-coach contract](../contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md) and [merge-bound ledger entry](../roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-support-handoff)
- `POST /api/v1/vip/fitchef/insight`
  - landed feature-gated VIP capability: Identity Loop Mapper
  - landed via PR #1870 / `7802ed25e99e0a4f346d14487270a037bb5ec97a`
- `POST /api/v1/vip/fitchef/week-repair`
  - primary future capability: identity-aware repair after slips

`/api/v1/vip/fitchef/chat` remains a broader VIP structured coach surface, but it must
not become the first implementation target ahead of bounded structured tools.

## Measurement

Canonical metric definitions for this wave must live in `docs/analytics/METRICS_CATALOG.md`,
and the umbrella experiment row must live in `docs/analytics/EXPERIMENT_REGISTRY.md`.
Signal vs Noise report fields are GTM decision fields only unless a later reviewed
runtime PR adds tested product telemetry.

### Distortion Simulator

Primary metric:

- `distortion_reframe_completion_rate`

Secondary metrics:

- `challenge_acceptance_rate`
- `next_action_commit_rate`
- `revisit_rate_7d`

### Identity Loop Mapper

Primary metric:

- `identity_loop_completion_rate`

Secondary metrics:

- `identity_to_action_followthrough_7d`
- `repeat_reflection_rate`
- `goal_alignment_score`

### Shared guardrails

- `retention_d7`
- support ticket rate
- `llm_cost_per_active_user`
- therapy/medical-language leakage rate
- session abandonment rate

## GTM and report lane

The report/content lane should follow the existing AI report and GTM templates:

- `docs/audience_pack/AI_REPORT_TEMPLATES.md`
- `docs/insights/SIGNAL_VS_NOISE_REPORT_LANE.md`
- `docs/marketing/GTM_NOTES_DEV_ONLY.md`
- `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md`

Recommended GTM positioning:

- wellness coaching
- habit coaching
- practical reflection
- small next steps

Not recommended:

- therapy framing
- clinical mental-health positioning

## PR wave

### Docs-first lane

- knowledge-library artifacts
- this SoT document
- contract alignment
- analytics alignment
- backlog follow-ups

### Follow-up implementation lanes

1. Landed: Distortion Simulator contract + PRO runtime via PR #1214 and PR #1215
2. Landed: Identity Loop Mapper VIP runtime via PR #1870, aligned to the frozen
   `FitChefIdentityLoopMapperResponse` schema; the schema and generated OpenAPI
   remain authoritative over this summary list.
3. Current docs/GTM lane: Signal vs Noise report/content contract

The broader philosophy and CBT source corpus can inform future reviewed PRs, but
it is source-corpus/supporting evidence only. It does not open semantic-cache,
GraphRAG, DB, OpenAPI, frontend, iOS, or automatic plan-adaptation runtime work
in this wave document.

## Decision

Promote the CBT Coaching Wave now.

Defer movement intelligence, user-facing experiment dashboards, and broader future-of/
essay-heavy productization until the current coaching wave is contract-frozen and proven.
